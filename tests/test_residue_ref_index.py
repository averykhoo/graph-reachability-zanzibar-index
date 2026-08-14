"""The ``ResidueRefV1`` reverse index -- correctness, maintenance, and its detector.

The node-release guards (``_gc_subject_node`` / ``_gc_public_node`` /
``_demote_released_node``) ask "does ANY residue reference this node id?". That used to
be a complete ``ResidueV1`` scan with a per-row JSON decode, measured at ~15 us/residue
row and quadratic under churn (``docs/spec-deviations.md`` 2026-07-29b). It is now an
indexed seek on ``ResidueRefV1``, the index ``ZT-P0-1``'s own note prescribed.

**The property these tests guard:** the indexed lookups answer EXACTLY what the old
full scan answered -- i.e. ``ResidueRefV1`` is a faithful reverse index of the
authoritative ``ResidueV1.neg | upos`` JSON, on every write path, after every
maintenance operation. Under-coverage is an authorization escalation (a guard that
believes nothing references a node deletes it, dangling the recording -- ZT-P0-1);
over-coverage pins nodes alive forever and drifts the state-functional canonical form.

**Why the reference here decodes JSON instead of calling the processor.** An expectation
derived from the index would be a *mirror* of its own subject (``docs/sabotage-procedure.md``,
"the mirror instrument"): it would stay green precisely when the index is the thing that
is wrong. ``_reference_keys_referencing`` below is the pre-index implementation, kept
deliberately as an independent oracle.

**The instrument trap this file is built around** (recorded 2026-07-29b, after two
versions of that benchmark measured an empty table and printed a plausible result):
``neg`` records subjects excluded from a WILDCARD-covered population, so a schema whose
grants are all concrete produces **no residue rows at all**. A test here that forgot the
wildcard would compare empty against empty and pass. Every test below therefore asserts
its own non-vacuity, and ``test_the_fixture_populates_all_three_residue_fields`` pins
the fixture's scope so the population cannot silently degrade.

SABOTAGE EVIDENCE -- literal observed output, per docs/sabotage-procedure.md. Each was
performed against the SOURCE (not by corrupting rows) and restored. Two of the three
predicted outcomes were WRONG; the corrections are the useful part and are kept.

  (S1) neutralize the ``(2c)`` reverse-index write in ``bulk_build.py`` -- the
       plausible "I added the table and forgot the offline path" omission.
       ★ PREDICTED: the bulk differential gate stays green (it compares
       ``snapshot_rows``, i.e. nodes and edges only), leaving this file as the only
       witness. OBSERVED: it does NOT stay green, because ``test_bulk_build.py``
       calls ``check_invariants`` and the new I6 clause fires inside it --
           5 failed, 2 passed in 4.32s
           index_v4.invariants.InvariantViolation: I6: residue_ref index disagrees
           with neg|upos on store_id='demorgan1_bulk' type='doc' wildcard=''
           implicit=False id=62 predicate='non_labels' name='d1' reference_count=0:
           indexed=[] recorded=[37, 39]
       This file fires too, with the message that names the actual cause:
           1 failed, 10 passed
           AssertionError: bulk build populated 0 reverse-index rows for 6 recorded
           subject id(s) -- the offline path does not maintain the index

  (S2) drop the delete half of ``_sync_residue_refs`` (keep only the inserts) -- the
       "an index only ever grows" refactor:
           2 failed, 9 passed in 1.40s
           AssertionError: the index did not shrink (6 -> 6) after a recording was dropped
           AssertionError: reverse-index rows survived the residues they index

  (S3) skip ``_sync_residue_refs`` on the residue-DELETE branch only -- the narrowest
       of the three, and the one that mattered.
       ★ PREDICTED: caught by the teardown test. OBSERVED: this entire file was
       **GREEN** -- `11 passed` -- while ``tests/test_matrix.py`` caught it via
       paranoia (`3 failed, 9 passed in 18.34s`). The reason is worth keeping: an
       orphan is observable only when a residue goes from ref-bearing straight to
       fully empty in ONE reconcile, and every ordering in this file emptied
       ``neg``/``upos`` while ``stars`` was still present -- which clears the index
       through the UPDATE branch and leaves nothing to orphan.
       ``test_residue_emptied_in_one_step_takes_its_index_rows_with_it`` was written
       to construct that ordering, and with S3 still applied it fires:
           1 failed, 11 passed
           AssertionError: index rows outlived the residue they index (the delete
           branch skipped reverse-index maintenance)
"""

import json

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from connectedstore import TupleSource, build_index, save_schema
from index_v4.invariants import (InvariantViolation, check_invariants,
                                 check_residue_hygiene)
from index_v4.models import NodeV4, ResidueRefV1, ResidueV1
from index_v4.outbox import outbox_watermark
from index_v4.processor import DeltaProcessor
from tests.wildcard_helpers import make_wildcard_index
from zanzibar_utils_v1 import Entity, RelationalTriple, parse_openfga_schema

# Wildcard grant (=> `stars`, and `neg` for the excluded), userset grants (=> `upos`),
# and an exclusion to drive both. All three residue fields are populated -- pinned by
# `test_the_fixture_populates_all_three_residue_fields`, because a schema drift that
# emptied `neg` would silently reduce this whole file to testing `upos`.
SCHEMA = """
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define blocked: [user, group#member]
    define viewer: [user:*, user, group#member] but not blocked
"""

SETUP = [
    # The wildcard GRANT itself. Declaring `[user:*]` in the schema is not enough --
    # `stars` (and therefore `neg`) exist only once a `user:*` tuple is actually
    # written. Omitting this is precisely the 2026-07-29b trap, and it is how the
    # first draft of this fixture was in fact wrong: `test_the_fixture_populates_all
    # _three_residue_fields` caught it with "no `stars`: the [user:*] grant stopped
    # producing wildcard coverage".
    ('...', 'user', '*', 'viewer', 'doc', 'x'),
    ('...', 'user', '*', 'viewer', 'doc', 'y'),
    ('member', 'group', 'g2', 'viewer', 'doc', 'x'),
    ('member', 'group', 'g2', 'viewer', 'doc', 'y'),
    ('member', 'group', 'g1', 'member', 'group', 'g2'),
    ('...', 'user', 'alice', 'blocked', 'doc', 'x'),
    ('...', 'user', 'bob', 'blocked', 'doc', 'y'),
    ('member', 'group', 'g3', 'blocked', 'doc', 'y'),
]

STORE = 'residue_ref'


class _Harness:
    """Synchronous-v1 graph backend: route the raw tuple, run the cascade, commit --
    one transaction (the ``GraphBackend.apply`` discipline, I5). Mirrors
    ``tests/test_reg14_residue_gc_elision.py::_Harness``."""

    def __init__(self, paranoia=False, store_id=STORE):
        self.store_id = store_id
        self.rs = parse_openfga_schema(SCHEMA, enable_boolean=True)
        self.session, self.widx = make_wildcard_index(
            self.rs.schema_info, store_id=store_id, paranoia=paranoia)
        self.proc = DeltaProcessor(self.widx, self.rs.compiled)

    def apply(self, raw, op):
        wm = outbox_watermark(self.session, self.store_id)
        sp = Ellipsis if raw[0] == '...' else raw[0]
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
        fn = self.widx.add_tuple if op == 'add' else self.widx.remove_tuple
        for d in self.rs.apply(triple):
            fn('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
               d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
        self.proc.run_cascade(wm)
        self.session.commit()

    def seed(self):
        for raw in SETUP:
            self.apply(raw, 'add')
        return self


# --------------------------------------------------------------------------- #
# Independent reference: the pre-index implementation. Decodes the authoritative
# JSON and never touches ResidueRefV1 -- see the module docstring on mirroring.
# --------------------------------------------------------------------------- #

def _recorded_subject_ids(session, store_id) -> dict[int, set[int]]:
    """``object_node_id -> {subject node ids in neg | upos}``, straight from the JSON."""
    out: dict[int, set[int]] = {}
    for r in session.exec(
            select(ResidueV1).where(ResidueV1.store_id == store_id)).all():
        out[r.object_node_id] = set(json.loads(r.neg)) | set(json.loads(r.upos))
    return out


def _reference_keys_referencing(session, store_id, node_id) -> list:
    """Verbatim behaviour of the scan ``_keys_referencing`` replaced, including its
    liveness filter (a recording whose object node row is gone yields no key)."""
    out = []
    for r in session.exec(
            select(ResidueV1).where(ResidueV1.store_id == store_id)).all():
        if node_id in json.loads(r.neg) or node_id in json.loads(r.upos):
            obj = session.get(NodeV4, r.object_node_id)
            if obj is not None:
                out.append((obj.type, obj.predicate, obj.name))
    return out


def _reference_any_reference(session, store_id, node_id) -> bool:
    """Verbatim behaviour of the scan ``_any_residue_reference`` replaced: membership
    only, with NO liveness filter (the conservative direction for a demotion guard)."""
    for r in session.exec(
            select(ResidueV1).where(ResidueV1.store_id == store_id)).all():
        if node_id in json.loads(r.neg) or node_id in json.loads(r.upos):
            return True
    return False


def _index_contents(session, store_id) -> dict[int, set[int]]:
    out: dict[int, set[int]] = {}
    for row in session.exec(
            select(ResidueRefV1).where(ResidueRefV1.store_id == store_id)).all():
        out.setdefault(row.object_node_id, set()).add(row.subject_node_id)
    return out


def _all_node_ids(session, store_id) -> list[int]:
    return [n.id for n in session.exec(
        select(NodeV4).where(NodeV4.store_id == store_id)).all()]


# --------------------------------------------------------------------------- #

def test_the_fixture_populates_all_three_residue_fields():
    """Non-vacuity for every other test in this file, and the documented trap
    (2026-07-29b): ``neg`` only exists under a WILDCARD grant, so an all-concrete
    schema produces no residue rows and every comparison here would pass on empty
    input. Assert the fixture reaches ``stars``, ``neg`` AND ``upos``."""
    g = _Harness().seed()
    try:
        rows = g.session.exec(
            select(ResidueV1).where(ResidueV1.store_id == STORE)).all()
        assert rows, 'no residue rows at all -- every test in this file is vacuous'
        stars = {tuple(s) for r in rows for s in json.loads(r.stars)}
        neg = {n for r in rows for n in json.loads(r.neg)}
        upos = {n for r in rows for n in json.loads(r.upos)}
        assert stars, 'no `stars`: the [user:*] grant stopped producing wildcard coverage'
        assert neg, 'no `neg`: the exclusion stopped recording star-covered exclusions'
        assert upos, 'no `upos`: the userset grants stopped recording edge-free memberships'
    finally:
        g.session.close()


def test_index_answers_exactly_what_the_full_scan_answered():
    """The headline property, checked against the independent JSON reference over
    EVERY node id in the store -- not just the ones expected to be referenced, so a
    lookup that over-reports is caught as well as one that under-reports."""
    g = _Harness().seed()
    try:
        ids = _all_node_ids(g.session, STORE)
        assert ids, 'no nodes -- the comparison below would run zero times'

        hits = 0
        for nid in ids:
            expected = sorted(_reference_keys_referencing(g.session, STORE, nid))
            assert sorted(g.proc._keys_referencing(nid)) == expected, \
                f'_keys_referencing disagrees with the full scan on node {nid}'
            assert (g.proc._any_residue_reference(nid)
                    is _reference_any_reference(g.session, STORE, nid)), \
                f'_any_residue_reference disagrees with the full scan on node {nid}'
            hits += bool(expected)

        # Scope, not just execution: a store where NOTHING is referenced would satisfy
        # every assertion above by answering [] on both sides, every time.
        assert hits >= 2, \
            f'only {hits} referenced node(s) -- the comparison never saw a real recording'
        # And an id that exists in no residue still answers empty (the lookup is real).
        assert g.proc._keys_referencing(-1) == []
        assert g.proc._any_residue_reference(-1) is False
    finally:
        g.session.close()


def test_index_matches_the_authoritative_json():
    """The index equals ``neg | upos`` exactly, in both directions, with no orphans."""
    g = _Harness().seed()
    try:
        recorded = {o: s for o, s in _recorded_subject_ids(g.session, STORE).items() if s}
        assert recorded, 'no recorded subjects -- vacuous'
        assert _index_contents(g.session, STORE) == recorded
    finally:
        g.session.close()


def test_index_shrinks_when_a_recording_is_dropped():
    """SABOTAGE (S2) MADE PERMANENT -- the "an index only ever grows" refactor.

    Dropping the delete half of ``_sync_residue_refs`` leaves stale rows that keep a
    released node pinned alive forever. Removing the chain grant drops ``group:g1#member``
    from both residues, so the index MUST shrink; the invariant then catches any
    residual disagreement."""
    g = _Harness().seed()
    try:
        chain = g.widx.idx.cached_concrete_node('member', 'group', 'g1')
        assert chain is not None
        before = sum(len(v) for v in _index_contents(g.session, STORE).values())
        assert g.proc._any_residue_reference(chain.id) is True, \
            'setup: the chain userset must be recorded before it can be dropped'

        g.apply(('member', 'group', 'g1', 'member', 'group', 'g2'), 'remove')

        after = sum(len(v) for v in _index_contents(g.session, STORE).values())
        assert after < before, \
            f'the index did not shrink ({before} -> {after}) after a recording was dropped'
        assert _index_contents(g.session, STORE) == {
            o: s for o, s in _recorded_subject_ids(g.session, STORE).items() if s}
        check_invariants(g.session, STORE, g.rs.schema_info)
    finally:
        g.session.close()


def test_residue_emptied_in_one_step_takes_its_index_rows_with_it():
    """The ONE ordering that catches sabotage (S3), and the reason this test exists
    separately from the teardown below.

    ``_sync_residue_refs`` is skipped only on the residue-DELETE branch, so an orphan
    is observable *only* when a residue goes from ref-bearing straight to fully empty
    in a single reconcile. Any ordering that empties ``neg``/``upos`` while ``stars``
    is still present clears the index on the way through the UPDATE branch and leaves
    nothing to orphan -- which is why ``reversed(SETUP)`` teardown, and every other
    test in this file, stayed GREEN under S3 (measured: `11 passed`).

    So: drop the wildcard grant FIRST (``stars`` and ``neg`` go, ``upos`` survives),
    then the userset grant -- which empties the residue in one step while the index
    still holds rows for it."""
    g = _Harness().seed()
    try:
        g.apply(('...', 'user', '*', 'viewer', 'doc', 'x'), 'remove')
        doc_x = g.widx.idx.cached_concrete_node('viewer', 'doc', 'x')
        assert doc_x is not None
        staged = _index_contents(g.session, STORE).get(doc_x.id, set())
        assert staged, \
            'setup: doc:x must still carry index rows (upos) after the wildcard grant ' \
            'is dropped, or the one-step emptying below orphans nothing'

        g.apply(('member', 'group', 'g2', 'viewer', 'doc', 'x'), 'remove')

        assert g.session.exec(
            select(ResidueV1)
            .where(ResidueV1.store_id == STORE)
            .where(ResidueV1.object_node_id == doc_x.id)).first() is None, \
            'setup: the residue should have been emptied and deleted in one step'
        assert doc_x.id not in _index_contents(g.session, STORE), \
            'index rows outlived the residue they index (the delete branch skipped ' \
            'reverse-index maintenance)'
        check_residue_hygiene(g.session, STORE, g.rs.schema_info)
    finally:
        g.session.close()


def test_index_is_maintained_across_a_full_teardown():
    """Remove every tuple: residues go empty and are deleted, so the index must end
    completely empty. Catches both a leaked delete and an orphan."""
    g = _Harness().seed()
    try:
        assert _index_contents(g.session, STORE), 'setup: the index must be non-empty'
        for raw in reversed(SETUP):
            g.apply(raw, 'remove')
        assert g.session.exec(
            select(ResidueV1).where(ResidueV1.store_id == STORE)).all() == [], \
            'setup drifted: an empty store should hold no residue rows'
        assert _index_contents(g.session, STORE) == {}, \
            'reverse-index rows survived the residues they index'
        check_invariants(g.session, STORE, g.rs.schema_info)
    finally:
        g.session.close()


# --------------------------------------------------------------------------- #
# The detector. These corrupt ResidueRefV1 directly -- the state a maintenance bug
# produces -- and assert I6 fires. Paranoia is off so the corruption can be staged.
# --------------------------------------------------------------------------- #

def test_a_dropped_index_row_is_caught():
    """The DANGEROUS direction: a missing row makes a node-release guard believe
    nothing references the node, which is the ZT-P0-1 escalation class re-opened."""
    g = _Harness().seed()
    try:
        row = g.session.exec(
            select(ResidueRefV1).where(ResidueRefV1.store_id == STORE)).first()
        assert row is not None, 'setup: nothing to drop'
        g.session.delete(row)
        g.session.flush()

        with pytest.raises(InvariantViolation, match='residue_ref index disagrees'):
            check_invariants(g.session, STORE, g.rs.schema_info)
        # ...and the CHEAP paranoia tier catches it too: this is the tier that runs in
        # production (`ZANZIBAR_PARANOIA=residue`), so it is the one that matters.
        with pytest.raises(InvariantViolation, match='residue_ref index disagrees'):
            check_residue_hygiene(g.session, STORE, g.rs.schema_info)
    finally:
        g.session.close()


def test_a_stale_index_row_is_caught():
    """The other direction: a row for a subject the residue no longer records."""
    g = _Harness().seed()
    try:
        obj = next(iter(_index_contents(g.session, STORE)))
        g.session.add(ResidueRefV1(store_id=STORE, subject_node_id=999_999,
                                   object_node_id=obj))
        g.session.flush()
        with pytest.raises(InvariantViolation, match='residue_ref index disagrees'):
            check_residue_hygiene(g.session, STORE, g.rs.schema_info)
    finally:
        g.session.close()


def test_orphaned_index_rows_are_caught():
    """SABOTAGE (S3) MADE PERMANENT: index rows for an object with NO residue row --
    what skipping ``_sync_residue_refs`` on the residue-delete branch leaves behind."""
    g = _Harness().seed()
    try:
        rows = g.session.exec(
            select(ResidueV1).where(ResidueV1.store_id == STORE)).all()
        assert rows, 'setup: need a residue to orphan'
        victim = rows[0].object_node_id
        g.session.delete(rows[0])
        g.session.flush()
        with pytest.raises(InvariantViolation, match='have no residue row'):
            check_residue_hygiene(g.session, STORE, g.rs.schema_info)
        assert victim in _index_contents(g.session, STORE), \
            'the orphan rows must still be present -- otherwise the clause proved nothing'
    finally:
        g.session.close()


def test_orphans_are_caught_even_when_every_residue_is_gone():
    """The cheap tier early-returns on ``not rows``. "All residues deleted, index rows
    left behind" is exactly the state a broken delete produces, so the early return
    must not make the tier blind to it -- this pins that it does not."""
    g = _Harness().seed()
    try:
        for r in g.session.exec(
                select(ResidueV1).where(ResidueV1.store_id == STORE)).all():
            g.session.delete(r)
        g.session.flush()
        assert _index_contents(g.session, STORE), 'setup: index rows must remain'
        with pytest.raises(InvariantViolation, match='have no residue row'):
            check_residue_hygiene(g.session, STORE, g.rs.schema_info)
    finally:
        g.session.close()


# --------------------------------------------------------------------------- #
# The offline path. bulk_build bypasses _store_residue entirely.
# --------------------------------------------------------------------------- #

@pytest.fixture
def bulk_session():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.mark.parametrize('bulk', [False, True])
def test_bulk_built_store_has_a_correct_reverse_index(bulk_session, bulk):
    """SABOTAGE (S1) MADE PERMANENT -- and the reason it is worth a test of its own:
    ``bulk_build`` writes ``ResidueV1`` rows directly, bypassing ``_store_residue``,
    and the existing bulk differential gate compares ``snapshot_rows`` (nodes and
    edges only). Omitting the offline path's index population is therefore invisible
    to every other test in the tree while producing a store whose node-release guards
    believe nothing is referenced. Both constructors are checked so the assertion
    cannot be satisfied by the incremental one alone."""
    src, dst = 'src', ('bulk' if bulk else 'inc')
    save_schema(bulk_session, src, SCHEMA, ())
    source = TupleSource(bulk_session, src)
    for raw in SETUP:
        source.add(*raw)
    bulk_session.commit()

    _, widx, rs = build_index(bulk_session, src, dst, bulk=bulk)
    bulk_session.commit()

    recorded = {o: s for o, s in _recorded_subject_ids(bulk_session, dst).items() if s}
    n_recorded = sum(len(v) for v in recorded.values())
    assert n_recorded >= 2, \
        f'only {n_recorded} recorded subject id(s) -- nothing for the index to get wrong'

    indexed = _index_contents(bulk_session, dst)
    assert sum(len(v) for v in indexed.values()) > 0, (
        f'{"bulk" if bulk else "incremental"} build populated 0 reverse-index rows for '
        f'{n_recorded} recorded subject id(s) -- the offline path does not maintain the index')
    assert indexed == recorded
    check_invariants(bulk_session, dst, rs.schema_info)
    assert widx is not None


if __name__ == '__main__':          # pragma: no cover
    pytest.main([__file__, '-q'])
