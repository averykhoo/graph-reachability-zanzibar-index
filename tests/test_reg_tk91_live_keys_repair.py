"""TK91 (boolean spec 5.5): the leading ``rel`` in ``_live_keys_of``'s ``preds`` is the
REPAIR affordance -- the only branch that finds an object whose derived state OUTLIVED
the leaf that produced it -- and losing it is a live authorization FAIL-OPEN.

WHAT IS PINNED
--------------
``index_v4/processor.py::DeltaProcessor._live_keys_of`` opens with

    preds = [rel] + [spec.predicate for spec in plan.leaves
                     if spec.positive and spec.kind in ('closure', 'derived-userset')]

The leading ``rel`` is the object's own PUBLIC family. On a CONSISTENT store it adds
nothing: any object with derived state also has positive-leaf state, so the second term
already names it. It earns its place only on an INCONSISTENT store -- one where a leaf
retraction landed and its cascade did not -- and there it is the ONLY thing that finds
the object, so it is the only reason ``backfill()`` can repair the store at all.

(!) THIS MUTATION WAS MEASURED **INERT** ACROSS FOUR WHOLE MODULES BEFORE THIS FILE
EXISTED. Deleting ``[rel] +`` (2026-09-20 sweep, both copies of the enumerator, byte-level
edit, whole-module re-runs) left all of these green:

    tests/test_backfill_enumeration.py            green   <- INERT
    tests/test_bulk_build.py                      green   <- INERT
    tests/test_invariants_derived.py              green   <- INERT
    formal/conformance/test_conformance_bulk_state.py  green   <- INERT

The mechanism was measured twice over, not guessed: (i) over 26 conformance corpora x 5
seeds the mutated line returns a BYTE-IDENTICAL key set on every key reached (dumped and
``diff``ed, 18 distinct ``(arm, type, rel)`` keys, 536 enumerated names, both runs); and
(ii) the bulk arm never executes this copy at all -- ``index_v4/bulk_backfill.py`` carries
its own mirror. Those corpora are all driven through a path that cascades in the same
transaction, so the store is never inconsistent and there is nothing to see.
``tests/test_backfill_enumeration.py``'s docstring reports the same result and hands the
branch to this item by name.

(!) I9 CANNOT BE THE PIN, BECAUSE I9 IS BLIND TO THIS. ``DeltaProcessor.audit_fixpoint``
enumerates its candidate keys THROUGH ``_live_keys_of``. Cripple the enumerator and the
audit stops looking at the very object that went stale, so it reports OK on a store that
is serving a revoked grant -- an assurance step that fails by PASSING, this repo's house
failure mode (``docs/sabotage-procedure.md``). So the pins below assert on ``check`` and
on the repaired STATE, off the primitive the mutation touches, and never take
``audit_fixpoint``'s word for anything.
``test_i9_reports_the_stale_key_at_all`` states I9's side of it as a POSITIVE claim (it
must RAISE on the stale store) rather than trusting a silent OK.

THE FIXTURE, AND WHY IT STAYS LOAD-BEARING
------------------------------------------
``viewer: editor but not banned``; ``u1`` is an editor of ``d1``, ``u3`` of ``d2``. The
REMOVE of ``u1 editor d1`` is routed onto the leaf families with the cascade SKIPPED (a
crashed or missed cascade -- the synchronous v1 write path always cascades in the same
transaction, which is exactly why no add/remove-driven test can reach this state). ``d1``
then has NO positive-leaf row left and lives only in the public ``viewer`` family, while
``d2`` still rides the ordinary ``closure`` leaf.
``test_fixture_keeps_the_public_family_the_only_route`` refuses a future edit that gives
``d1`` a positive-leaf route back: the correct repair on a failure there is to restore the
fixture, never to relax the test.

OBSERVED, LITERALLY (``.scratch`` probe, 2026-09-20; the sabotage run is below)::

    CLEAN                                          MUTATED (`preds = [] + ...`)
      live_keys_of(doc, viewer) = ['d1', 'd2']       live_keys_of(doc, viewer) = ['d2']
      after backfill(): check(u1,viewer,d1)=False    after backfill(): check(u1,viewer,d1)=True
      backfill CHANGED state = True                  backfill repairs nothing
      repaired == reference : True                   repaired == reference : False
      stale audit_fixpoint() = InvariantViolation    stale audit_fixpoint() = OK
        "I9: reconcile of (doc, viewer, d1) was
         not a fixpoint -- derived state was stale"

The ``repaired == reference`` clause is the strongest one and its diff is not empty --
measured, the stale-vs-reference difference is a surviving public-family node plus the
closure edge that serves the revoked grant::

    node_diff = {('...', 'user', 'u1', '', True, 1): 1,
                 ('viewer', 'doc', 'd1', '', False, 1): 1}
    edge_diff = {(('...', 'user', 'u1', ''), ('viewer', 'doc', 'd1', ''), 1, 1): 1}
    residue_diff = {}

so ``_state_diff`` below prints node/edge/residue separately and the failure explains
itself instead of printing an empty dict.

The reference arm is a fresh index grown by the LIVE cascade from the surviving tuples.
That is deliberate: live maintenance reaches objects by dependents-invalidation and never
calls ``_live_keys_of`` (measured over the same 26-corpus sweep: every one of the 170
calls came from ``audit_fixpoint``, zero from cascade maintenance), so the reference
cannot be corrupted by the mutation it is being used to catch.
``test_repaired_state_equals_a_fresh_bulk_build`` adds the production bootstrap path
(``connectedstore.build_index(bulk=True)``) as a second, independent reference.

SABOTAGE (``docs/sabotage-procedure.md``), 2026-09-20, byte-level edit of
``index_v4/processor.py``, original bytes saved and restored, ``git status --porcelain``
clean afterwards. Baseline is this module unmutated::

    BASELINE                                                   5 passed
    S1  `preds = [rel] + [...]` -> `preds = [] + [...]`        4 failed, 1 passed
          ::test_live_keys_of_finds_state_that_outlived_its_leaf
            AssertionError: _live_keys_of(doc, viewer) lost 'd1' -- the object's derived
            state outlived its leaf and only the public family can still find it; got
            ['d2']
          ::test_backfill_repairs_the_stale_grant
            AssertionError: backfill() changed nothing on a store it must repair: u1
            still passes check(viewer, d1) after the grant was retracted -- FAIL-OPEN
          ::test_repaired_state_equals_a_fresh_bulk_build
            AssertionError: repaired state != fresh bulk build; nodes: +[('...', 'user',
            'u1', '', True, 1), ('viewer', 'doc', 'd1', '', False, 1)] -[]; edges:
            +[(('...', 'user', 'u1', ''), ('viewer', 'doc', 'd1', ''), 1, 1)] -[];
            residues: []
          ::test_i9_reports_the_stale_key_at_all
            Failed: DID NOT RAISE InvariantViolation
    S2  CONTROL, instrument check: on UNMUTATED source, flip
        ::test_backfill_repairs_the_stale_grant's own post-repair expectation
        `assert not still_granted` -> `assert still_granted`         1 failed, 4 passed
            AssertionError: backfill() ran but the revoked grant still passes check
            -- FAIL-OPEN

S1 is the mutation this module exists for; the surviving test is the fixture guard, which
reads the plan rather than the enumerator and is correctly indifferent to it. S2 confirms
the instrument fails when it should.

(!) THE DUPLICATE IS STILL UNPINNED, DELIBERATELY. ``index_v4/bulk_backfill.py:811``
carries its own ``preds = [rel] + [...]`` mirror. Measured first-hand 2026-09-20: the same
byte-level deletion applied to the MIRROR leaves this module plus
``tests/test_backfill_enumeration.py``, ``tests/test_bulk_build.py`` and
``tests/test_invariants_derived.py`` at ``29 passed``. That is NOT an oversight here --
REASONED from ``connectedstore/build.py::build_index``, which "refuses to run on an index
that already has state", the bulk path only ever backfills a pre-backfill state it
constructed itself, so its ``[rel]`` term has no inconsistent store to repair and may be
unreachable by construction. UNVERIFIED: nobody has proved that. Do not delete the mirror's
term on the strength of this paragraph, and do not assume it is guarded because this file
exists.
"""

import json

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from connectedstore import TupleSource, build_index, save_schema
from index_v4.invariants import InvariantViolation, snapshot_rows
from index_v4.models import NodeV4, ResidueV1
from index_v4.outbox import outbox_watermark
from index_v4.processor import DeltaProcessor
from tests.wildcard_helpers import make_wildcard_index
from zanzibar_utils_v1 import Entity, RelationalTriple, parse_openfga_schema

# `viewer` has exactly one positive leaf and it is a *storage* leaf, so after the victim
# tuple is retracted `d1` has no positive-leaf row at all -- see the module docstring.
_SCHEMA = '''
    type user
    type doc
      relations
        define editor: [user]
        define banned: [user]
        define viewer: editor but not banned
'''

_OPS = [
    ('...', 'user', 'u1', 'editor', 'doc', 'd1'),
    ('...', 'user', 'u2', 'banned', 'doc', 'd1'),
    ('...', 'user', 'u3', 'editor', 'doc', 'd2'),   # the control object: keeps its leaf
]
_VICTIM = _OPS[0]
_SURVIVORS = [op for op in _OPS if op != _VICTIM]
_KEY = ('doc', 'viewer')


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _route(rs, widx, raw, op='add'):
    """Fan one raw write onto the leaf families (`RuleSet.apply`), no cascade."""
    sp = Ellipsis if raw[0] == '...' else raw[0]
    triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
    fn = widx.add_tuple if op == 'add' else widx.remove_tuple
    for d in rs.apply(triple):
        fn('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
           d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)


def _residues_by_name(session, widx):
    out = {}
    for r in session.exec(select(ResidueV1)).all():
        node = widx._node_by_id(r.object_node_id)
        neg = frozenset((n.predicate, n.type, n.name)
                        for n in (widx._node_by_id(i) for i in json.loads(r.neg))
                        if n is not None)
        out[(node.type, node.name, r.relation)] = (r.stars, neg)
    return out


def _state(session, widx):
    """Id-independent logical state: (node rows, edge rows, residues by name)."""
    nodes, edges = snapshot_rows(session, widx.idx.store_id)
    return nodes, edges, _residues_by_name(session, widx)


def _state_diff(got, want) -> str:
    """A diff that can explain its own failure: node, edge and residue components
    are reported SEPARATELY, because the three carry different parts of the state and
    a single combined `!=` would hide which one moved."""
    (gn, ge, gr), (wn, we, wr) = got, want
    nodes = f'+{sorted(gn - wn)} -{sorted(wn - gn)}'
    edges = f'+{sorted(ge - we)} -{sorted(we - ge)}'
    res = sorted((k, gr.get(k), wr.get(k)) for k in set(gr) | set(wr) if gr.get(k) != wr.get(k))
    return f'nodes: {nodes}; edges: {edges}; residues: {res}'


def _assert_state_equal(got, want, what: str) -> None:
    """``pytest.fail`` with the component diff rather than a bare ``assert a == b``.

    A raw ``==`` on two three-tuples of Counters prints a truncated dump of the whole
    state, which is an assertion that cannot explain its own failure; the interesting
    part here is three rows wide.
    """
    if got != want:
        pytest.fail(f'{what}; {_state_diff(got, want)}')


def _live_arm(rs, ops):
    """Grow an index the production synchronous-v1 way: route + cascade, same txn.

    The live cascade reaches its work by dependents-invalidation and never calls
    ``_live_keys_of``, which is what makes this usable as the reference arm.
    """
    session, widx = make_wildcard_index(rs.schema_info)
    proc = DeltaProcessor(widx, rs.compiled)
    for raw in ops:
        wm = outbox_watermark(session, 'test')
        _route(rs, widx, raw)
        proc.run_cascade(wm)
        session.commit()
    return session, widx, proc


def _stale_store(rs):
    """Build the full corpus live, then retract the victim's leaf WITHOUT cascading.

    Leaves the store inconsistent on purpose: ``d1``'s public ``viewer`` family still
    carries the derived edge minted for a grant that no longer exists.
    """
    session, widx, proc = _live_arm(rs, _OPS)
    assert widx.check('...', 'user', 'u1', 'viewer', 'doc', 'd1'), \
        'fixture never granted the permission it is about to revoke'
    _route(rs, widx, _VICTIM, 'remove')
    session.commit()
    return session, widx, proc


def _preds_without_rel(proc, object_type, rel) -> set:
    """The half of ``_live_keys_of``'s ``preds`` that is NOT the leading ``rel``.

    Kept in lockstep with ``index_v4/processor.py::DeltaProcessor._live_keys_of``.
    """
    plan = proc.compiled.plans[(object_type, rel)]
    preds = [spec.predicate for spec in plan.leaves
             if spec.positive and spec.kind in ('closure', 'derived-userset')]
    names = set()
    for pred in preds:
        rows = proc.session.exec(
            select(NodeV4).where(NodeV4.store_id == proc.store_id)
            .where(NodeV4.type == object_type).where(NodeV4.predicate == pred)
            .where(NodeV4.wildcard == '')
        ).all()
        names.update(n.name for n in rows)
    return names


def _bulk_reference(tuples):
    """Fresh index built OFFLINE from a tuple snapshot through the production
    bootstrap (`connectedstore.build_index(bulk=True)`)."""
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    save_schema(session, 'src', _SCHEMA, frozenset())
    src = TupleSource(session, 'src')
    for raw in tuples:
        src.add(*raw)
    session.commit()
    _, widx, _ = build_index(session, 'src', 'bulk', bulk=True)
    return session, widx


# --------------------------------------------------------------------------- #
# (0) the fixture guard -- a mechanical refusal of a vacuous pin
# --------------------------------------------------------------------------- #

def test_fixture_keeps_the_public_family_the_only_route():
    """Property guarded: on the stale store, ``d1`` is reachable ONLY through the public
    family -- the rest of ``preds`` does not name it -- while ``d2`` still is reachable
    through its ordinary storage leaf.

    Without the first half every pin in this module would pass with ``[rel]`` deleted;
    without the second half the enumerator could be returning nothing at all and the
    comparison would still look clean. Reds if a future schema edit gives ``viewer`` a
    second positive leaf that survives the retraction. The correct repair is to restore
    the fixture, never to relax this test.
    """
    rs = parse_openfga_schema(_SCHEMA, enable_boolean=True)
    session, widx, proc = _stale_store(rs)

    plan = rs.compiled.plans[_KEY]
    assert [(s.predicate, s.kind, s.positive) for s in plan.leaves] == [
        ('viewer.0', 'closure', True), ('viewer.1', 'closure', False)], \
        f'fixture drifted: {[(s.predicate, s.kind, s.positive) for s in plan.leaves]}'

    without_rel = _preds_without_rel(proc, *_KEY)
    assert 'd1' not in without_rel, (
        f"d1 is reachable without the public family ({sorted(without_rel)}) -- this "
        f"module's pins would be vacuous")
    assert 'd2' in without_rel, (
        f'd2 lost its storage leaf ({sorted(without_rel)}) -- the enumerator could now '
        f'be returning nothing and the comparisons would still look clean')
    session.close()


# --------------------------------------------------------------------------- #
# (1) THE PIN, on the primitive itself
# --------------------------------------------------------------------------- #

def test_live_keys_of_finds_state_that_outlived_its_leaf():
    """Property guarded: ``_live_keys_of`` still enumerates an object whose ONLY
    remaining state is in its public family.

    ``backfill()`` visits exactly these names and nothing else, so an object missing
    here is an object the repair path silently never reconciles.
    """
    rs = parse_openfga_schema(_SCHEMA, enable_boolean=True)
    session, widx, proc = _stale_store(rs)

    keys = proc._live_keys_of(*_KEY)
    assert 'd1' in keys, (
        f"_live_keys_of{_KEY} lost 'd1' -- the object's derived state outlived its leaf "
        f'and only the public family can still find it; got {sorted(keys)}')
    assert keys == {'d1', 'd2'}, sorted(keys)
    session.close()


# --------------------------------------------------------------------------- #
# (2) WHAT IT BUYS: the fail-open closes
# --------------------------------------------------------------------------- #

def test_backfill_repairs_the_stale_grant():
    """Property guarded: ``backfill()`` on the inconsistent store revokes the stale
    grant and lands on the state a fresh live build would have.

    Asserted on ``check`` and on the state directly -- never through
    ``audit_fixpoint``, which enumerates through the same primitive and goes blind with
    it (module docstring).
    """
    rs = parse_openfga_schema(_SCHEMA, enable_boolean=True)
    session, widx, proc = _stale_store(rs)

    assert widx.check('...', 'user', 'u1', 'viewer', 'doc', 'd1'), \
        'fixture is not stale: the uncascaded retraction already revoked the grant'
    before = _state(session, widx)

    proc.backfill()
    session.commit()
    after = _state(session, widx)

    backfill_changed_state = after != before
    assert backfill_changed_state, (
        'backfill() changed nothing on a store it must repair: u1 still passes '
        'check(viewer, d1) after the grant was retracted -- FAIL-OPEN')
    still_granted = bool(widx.check('...', 'user', 'u1', 'viewer', 'doc', 'd1'))
    assert not still_granted, \
        'backfill() ran but the revoked grant still passes check -- FAIL-OPEN'
    # the control object is untouched by the repair
    assert widx.check('...', 'user', 'u3', 'viewer', 'doc', 'd2'), \
        'backfill() revoked the grant it was not asked about'

    ref_session, ref_widx, _ = _live_arm(rs, _SURVIVORS)
    reference = _state(ref_session, ref_widx)
    assert before != reference, 'the fixture was never stale -- nothing to repair'
    _assert_state_equal(after, reference, 'repaired state != fresh live build')
    session.close()
    ref_session.close()


def test_repaired_state_equals_a_fresh_bulk_build():
    """Second, independent reference: the production OFFLINE bootstrap
    (``connectedstore.build_index(bulk=True)``) over the surviving tuples.

    ``index_v4/bulk_backfill.py`` carries its own mirror of ``_live_keys_of``, so this
    arm crosses the two copies; on a consistent store both agree, which is what makes
    the bulk build usable as a reference for a repair of an INCONSISTENT one.
    """
    rs = parse_openfga_schema(_SCHEMA, enable_boolean=True)
    session, widx, proc = _stale_store(rs)
    proc.backfill()
    session.commit()
    repaired = _state(session, widx)

    bulk_session, bulk_widx = _bulk_reference(_SURVIVORS)
    reference = _state(bulk_session, bulk_widx)
    assert reference[0], 'bulk reference built an EMPTY index -- the comparison is vacuous'
    _assert_state_equal(repaired, reference, 'repaired state != fresh bulk build')
    session.close()
    bulk_session.close()


# --------------------------------------------------------------------------- #
# (3) I9's side, stated POSITIVELY
# --------------------------------------------------------------------------- #

def test_i9_reports_the_stale_key_at_all():
    """Property guarded: ``audit_fixpoint`` RAISES on the stale store, naming the key.

    Stated as a positive requirement precisely because the failure mode here is a
    silent OK: I9 enumerates its candidates through ``_live_keys_of``, so a crippled
    enumerator makes the audit skip the one object that is stale and report success on
    a store serving a revoked grant. ``audit_fixpoint`` reconciles as it goes, so this
    runs on its own store.
    """
    rs = parse_openfga_schema(_SCHEMA, enable_boolean=True)
    session, widx, proc = _stale_store(rs)
    with pytest.raises(InvariantViolation) as exc:
        proc.audit_fixpoint()
    assert 'I9' in str(exc.value) and 'd1' in str(exc.value), str(exc.value)
    session.close()
