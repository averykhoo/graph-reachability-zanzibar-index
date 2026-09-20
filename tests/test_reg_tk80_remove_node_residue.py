"""TK80: ``WildcardIndex.remove_node`` REFUSES a residue-recorded node.

``remove_node`` runs no cascade, so nothing prunes a residue that records the node it
deletes. Before this pin, the facade happily deleted such a node and the transaction
COMMITTED, leaving a residue vouching for a node id that no longer exists -- the
ZT-P0-1 escalation class (under SQLite rowid reuse the dead id can later repoint at an
unrelated principal, which is exactly what ``tests/test_reg14_residue_gc_elision.py``
exists to catch one layer down).

WITNESS -- the literal observed output on the pre-fix tree (2026-09-20), produced by
``WildcardIndex.remove_node`` + ``session.commit()`` at the PRODUCTION paranoia default
(``off``, asserted not assumed), then checked in a FRESH session against COMMITTED
state, per ``docs/sabotage-procedure.md``:

    remove_node returned without raising
    commit returned without raising
    victim node in COMMITTED state: None
    check_residue_hygiene (tier `residue`): InvariantViolation: I6: residue neg holds a
        dead node id 8 on node id=3 doc:x#viewer implicit=False
    check_invariants (tier `full`): InvariantViolation: I6: residue neg holds a dead
        node id 8 on id=3 type='doc' wildcard='' reference_count=0 store_id='tk80'
        predicate='viewer' name='x' implicit=False
    RESULT: I6 VIOLATION ON COMMITTED STATE

The hazard is ``neg | upos``, not ``neg`` alone. The same arm with victim node 6, a
``upos`` subject that was ``implicit=False`` with ``reference_count=3`` -- so neither
an implicit-only guard nor a refcount guard would have stopped it:

    check_residue_hygiene (tier `residue`): InvariantViolation: I6: residue upos holds
        a dead node id 6 on node id=3 doc:x#viewer implicit=False

And the third victim, the derived-public node that OWNS the residue row (reachable
here whenever ``processor_writes`` is on), which trips a DIFFERENT I6 clause:

    check_residue_hygiene: InvariantViolation: I6: residue row 1 references a missing
        node 3

NON-VACUITY -- the control that makes the refusal CONDITIONAL rather than a blanket
break of ``remove_node``. On the same pre-fix tree, through the same unguarded core
branch, an UNREFERENCED node removes and commits clean:

    C3 non-vacuity: victim NOT in any residue  (paranoia=False)
      VICTIM id=14 group:g3#member implicit=True rc=2
      remove_node: returned
      commit: returned
      residue-tier check: PASSED
      full check: PASSED

``test_an_unreferenced_node_is_still_removable_and_commits_clean`` below is that
control, kept as a permanent test: a guard that refused every ``remove_node`` on a
boolean store would pass every other test in this file.

Scope: the refusal is in the FACADE (``index_v4/wildcard.py``) only. ``index_v4/core.py``
is untouched, so every ``formal/CORRESPONDENCE.md`` anchor still resolves and no modelled
algorithm changed; the placement is BEFORE ``_strip_bridges``, which can implicit-GC the
node and take the early ``return`` (a check after it is reached too late).

SABOTAGE EVIDENCE -- literal observed output, 2026-09-20, each mutation applied to
``index_v4/wildcard.py`` by bytes and the exact original bytes restored (never
``git checkout``). The whole module passes 9/9 unsabotaged.

  (S1) delete the refusal entirely -- i.e. the pre-fix facade:
           5 failed, 4 passed in 1.68s
       (both recorded victims, the residue owner, the state-untouched pin and the
       ordering pin; the four survivors are the fixture/control/mirror tests, which
       is correct -- they do not test the refusal.)

  (S2) drop the OWNER clause from ``_residue_records_node``, keeping only the
       ``ResidueRefV1`` clause -- the "the reverse index already answers this"
       simplification. This is the one that proves the clause is EXERCISED:
           2 failed, 7 passed in 1.71s
           AssertionError: guard disagrees with the processor on node 3
           FAILED ::test_removing_the_node_that_owns_a_residue_row_is_refused

  (S3) make the refusal unconditional (``if True:``) -- the plausible over-broad fix:
           2 failed, 7 passed in 1.78s
           FAILED ::test_an_unreferenced_node_is_still_removable_and_commits_clean
           FAILED ::test_the_sanctioned_path_removes_the_recording_then_the_node

  (S4) move the refusal BELOW ``_strip_bridges``, keeping it otherwise identical --
       the narrowest weakening there is, and the instructive one.
       ★ PREDICTED: caught by the state-untouched pin. OBSERVED, on the first pass:
       **8 passed** -- the whole module was GREEN. ``_strip_bridges`` writes nothing
       for ANY node of the main fixture (measured over all 14: ``strip=no-write``
       every time), so the ordering was simply not observable there.
       ``test_the_refusal_runs_before_the_bridge_strip`` and its second, bridged
       fixture were written for exactly this, and with S4 re-applied it fires:
           1 failed, 8 passed in 1.91s
           AssertionError: the refusal fired AFTER a write -- the check moved below
           _strip_bridges

A follow-up MUTATION SWEEP of ``_residue_records_node`` (2026-09-20, 12 narrow
weakenings) found two more that this module did NOT catch -- both GREEN at ``9
passed``, and both PROVEN BY PROBE to move the guard's answer, so genuine holes
rather than scope-honest inerts. The two tests at the bottom of this file were
written for them; re-applied by bytes against the restored file, each is now RED:

  (M2) drop the liveness filter in the reverse-index loop --
       ``if s.get(NodeV4, r.object_node_id) is not None: return True`` becomes an
       unconditional ``return True``:
           was 9 passed -- now  1 failed, 10 passed in 1.28s
           FAILED ::test_a_dangling_residue_ref_does_not_count_as_a_recording
           AssertionError: a DANGLING reverse-index row was counted as a live
           recording -- the liveness filter is gone, and the guard now over-reports
           where the processor does not
           assert True is False  +  where True = _residue_records_node(6)

  (M2b) the NARROWER form -- keep the filter, but probe the SUBJECT node instead of
       the recording OBJECT node (the subject is alive by construction, so the filter
       stays in the source and never says no):
           1 failed, 10 passed in 1.24s   (same test, same assertion)

  (M10) delete BOTH ``.where(... .store_id == sid)`` clauses:
           was 9 passed -- now  1 failed, 10 passed in 1.35s
           FAILED ::test_the_guard_is_scoped_to_its_own_store
           AssertionError: store tk80_xstore's guard sees store tk80's reverse-index
           rows -- the ResidueRefV1 query lost its store_id filter
       Each clause is pinned SEPARATELY, so neither half rides on the other:
           M10a (``ResidueV1.store_id`` only):   1 failed, 10 passed in 1.27s
               AssertionError: store tk80_xstore's guard sees store tk80's residue
               ROWS -- the ResidueV1 query lost its store_id filter
           M10b (``ResidueRefV1.store_id`` only): 1 failed, 10 passed in 1.26s

SCOPE -- adjudicated 2026-09-20, and it is a DEFENSIBLE BOUNDARY, not a gap this
module should close. The guard reads the DERIVED ``ResidueRefV1`` index, not the
``ResidueV1.neg``/``upos`` JSON that is the source of truth, so if a reverse-index
row is ever missing while the JSON still records the node, ``remove_node`` allows the
removal and the original I6 corruption returns verbatim (probed: ``remove_node +
commit: SUCCEEDED``, then ``I6: residue neg holds a dead node id 8``). The boundary
holds for two reasons. First, ``DeltaProcessor._keys_referencing`` -- THE node-release
guard, the one whose elision caused ZT-P0-1 -- reads the same index under the same
liveness rule, so a guard that read the JSON instead would answer differently from the
processor, breaking the agreement this module pins and making the facade's rule a
second, divergent definition of "referenced". Second, a ``ResidueRefV1`` row out of
sync with its ``ResidueV1`` JSON is ALREADY an invariant violation that an existing
check owns, in both directions, and that check does not read ``processor.py`` at all:
``index_v4/invariants.py::_check_residue_rows`` (fed by ``::_load_residue_refs`` from
BOTH ``::check_invariants`` and ``::check_residue_hygiene``) decodes ``neg``/``upos``
straight from the JSON and fails on any disagreement. Verified first-hand on exactly
the stale-index state above, BEFORE any removal:

    residue tier: InvariantViolation: I6: residue_ref index disagrees with neg|upos on
        node id=3 doc:x#viewer implicit=False: indexed=[6, 7] recorded=[6, 7, 8]
    full tier:    InvariantViolation: I6: residue_ref index disagrees with neg|upos on
        type='doc' id=3 ... predicate='viewer' name='x' ...

So the premise of the residual risk is a state the `residue` tier refuses inside every
commit it runs in; making the admission guard decode the JSON would buy nothing the
checker does not already own, at the cost of the processor agreement. Recorded rather
than fixed.
"""

import json

import pytest
from sqlmodel import Session, select

from index_v4 import ReachabilityIndex, Store, WildcardIndex
from index_v4.invariants import check_invariants, check_residue_hygiene
from index_v4.models import NodeV4, ResidueRefV1, ResidueV1
from index_v4.outbox import outbox_watermark
from index_v4.processor import DeltaProcessor
from tests.wildcard_helpers import make_wildcard_index, snapshot
from zanzibar_utils_v1 import (AdmissionRejected, Entity, RelationalTriple,
                               parse_openfga_schema)

# Verbatim from ``tests/test_residue_ref_index.py::SCHEMA`` / ``::SETUP`` -- the only
# in-tree fixture that populates `stars`, `neg` AND `upos`. `neg` exists only under a
# WILDCARD grant (the 2026-07-29b trap), which is why the `[user:*]` tuple is written
# and not merely declared; `test_the_fixture_records_both_neg_and_upos` pins that.
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
    ('...', 'user', '*', 'viewer', 'doc', 'x'),
    ('...', 'user', '*', 'viewer', 'doc', 'y'),
    ('member', 'group', 'g2', 'viewer', 'doc', 'x'),
    ('member', 'group', 'g2', 'viewer', 'doc', 'y'),
    ('member', 'group', 'g1', 'member', 'group', 'g2'),
    ('...', 'user', 'alice', 'blocked', 'doc', 'x'),
    ('...', 'user', 'bob', 'blocked', 'doc', 'y'),
    ('member', 'group', 'g3', 'blocked', 'doc', 'y'),
]

STORE = 'tk80'

# `user:alice` is star-covered but excluded  => recorded in `neg` of doc:x#viewer.
NEG_VICTIM = ('...', 'user', 'alice')
# `group:g2#member` is an edge-free userset membership => recorded in `upos` of both.
UPOS_VICTIM = ('member', 'group', 'g2')
# `group:g3#member` is blocked on doc:y, and a userset subject is NOT star-covered,
# so it lands in neither `neg` nor `upos`: the non-vacuity control.
UNREFERENCED = ('member', 'group', 'g3')

MESSAGE = 'recorded by a derived relation'

# --------------------------------------------------------------------------- #
# A SECOND fixture, for the refuse-BEFORE-strip ordering only. The fixture above
# cannot pin it: `_strip_bridges` writes nothing for any of its nodes (measured
# 2026-09-20 over all 14 -- `strip=no-write` for every one), so moving the refusal
# after the strip leaves every test above green. This schema adds a WILDCARD USERSET
# restriction (`group:*#member`, the `bridged_in` shape, borrowed from
# `tests/test_wildcard_remove_node.py::_SCHEMA`) on a separate untainted relation, so
# `group:g2#member` is BOTH bridged and recorded in the derived relation's `upos`.
# --------------------------------------------------------------------------- #
BRIDGED_SCHEMA = """
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define blocked: [user, group#member]
    define peer: [group#member, group:*#member]
    define viewer: [user:*, user, group#member] but not blocked
"""

BRIDGED_SETUP = [
    ('...', 'user', '*', 'viewer', 'doc', 'x'),
    ('member', 'group', 'g2', 'viewer', 'doc', 'x'),
    ('member', 'group', 'g1', 'member', 'group', 'g2'),
    ('...', 'user', 'alice', 'blocked', 'doc', 'x'),
    ('member', 'group', 'g2', 'peer', 'doc', 'z'),   # materialises g2#member's bridge
]

BRIDGED_STORE = 'tk80_bridged'

# A THIRD store id, co-tenant with STORE on ONE session, for the store-scoping pin
# (`test_the_guard_is_scoped_to_its_own_store`). It needs the same engine, not just
# the same schema: `NodeV4.id` is a global primary key, so only a shared table can
# hand one store's facade an id that belongs to another store.
XSTORE = 'tk80_xstore'


class _Harness:
    """Synchronous-v1 graph backend: route the raw tuple, run the cascade, commit --
    one transaction (the ``GraphBackend.apply`` discipline, I5). Mirrors
    ``tests/test_residue_ref_index.py::_Harness``.

    NOT ``tests/test_reg14_residue_gc_elision.py::_Harness``: that one always runs the
    cascade and hardcodes its own store id, and the state under test here is precisely
    a ``remove_node`` with NO cascade in the transaction.
    """

    def __init__(self, paranoia=False, store_id=STORE, schema=SCHEMA, setup=SETUP,
                 session=None):
        self.store_id = store_id
        self.setup = setup
        self.rs = parse_openfga_schema(schema, enable_boolean=True)
        self._borrowed = session is not None
        if session is None:
            self.session, self.widx = make_wildcard_index(
                self.rs.schema_info, store_id=store_id, paranoia=paranoia)
        else:
            # CO-TENANT mode: a second store on an EXISTING session, i.e. the same
            # engine and the same `NodeV4` table, drawing ids from one sequence.
            # `make_wildcard_index` cannot do this -- it builds its own in-memory
            # engine per call, and two isolated databases would prove nothing about
            # `store_id` scoping. Nothing is installed in `session.info`, which is the
            # `paranoia=False` state `assert_paranoia_is_off` checks for.
            assert paranoia is False, 'the co-tenant store installs no paranoia guard'
            self.session = session
            session.add(Store(id=store_id))
            session.flush()
            self.widx = WildcardIndex(
                ReachabilityIndex(session, store_id=store_id), self.rs.schema_info)
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
        for raw in self.setup:
            self.apply(raw, 'add')
        self.assert_paranoia_is_off()
        return self

    # -- instrument control -------------------------------------------------- #
    def assert_paranoia_is_off(self):
        """⚠ ASSERT the installed tier, never trust the argument.

        At any non-``off`` tier the checker refuses the write PRE-COMMIT and every
        refusal test below would be green for the wrong reason -- it would be pinning
        paranoia mode, not the admission guard. The historical form of this bug (the
        tier silently dropped so every value installed ``'full'``) is pinned by
        ``tests/test_paranoia_wiring.py::test_helper_forwards_the_tier``; this is the
        same read-back probe that test uses.
        """
        guard = self.session.info.get('paranoia_guards', {}).get(self.store_id)
        assert guard is None, f'paranoia tier is not off: {guard!r}'

    # -- state accessors ----------------------------------------------------- #
    def node(self, predicate, e_type, name):
        return self.widx.idx.cached_concrete_node(predicate, e_type, name)

    def residue_rows(self, session=None):
        s = self.session if session is None else session
        return s.exec(select(ResidueV1)
                      .where(ResidueV1.store_id == self.store_id)).all()

    def residue_state(self, session=None):
        """``{object_node_id: (stars, sorted(neg), sorted(upos))}`` from the JSON."""
        return {r.object_node_id: (r.stars, sorted(json.loads(r.neg)),
                                   sorted(json.loads(r.upos)))
                for r in self.residue_rows(session)}

    def ref_index(self, session=None):
        s = self.session if session is None else session
        return sorted((r.object_node_id, r.subject_node_id) for r in s.exec(
            select(ResidueRefV1).where(ResidueRefV1.store_id == self.store_id)).all())

    def node_ids(self):
        return sorted(n.id for n in self.session.exec(
            select(NodeV4).where(NodeV4.store_id == self.store_id)).all())

    def committed_check(self):
        """Run BOTH invariant tiers against COMMITTED state in a FRESH session.

        A check on the writing session can read uncommitted identity-map state; the
        witness above only became visible because it was checked this way.
        """
        fresh = Session(self.session.get_bind())
        try:
            check_residue_hygiene(fresh, self.store_id, self.rs.schema_info)
            check_invariants(fresh, self.store_id, self.rs.schema_info)
            return {n.id for n in fresh.exec(
                select(NodeV4).where(NodeV4.store_id == self.store_id)).all()}
        finally:
            fresh.close()

    def close(self):
        # A BORROWED session belongs to the harness that made it: closing it here
        # would detach the owner's state mid-test.
        if not self._borrowed:
            self.session.close()


# --------------------------------------------------------------------------- #
# Non-vacuity of the fixture itself
# --------------------------------------------------------------------------- #

def test_the_fixture_records_both_neg_and_upos():
    """Every refusal below is vacuous if the fixture stops producing recordings.

    ``neg`` needs the WILDCARD grant to exist at all (docs/spec-deviations.md
    2026-07-29b); ``upos`` needs the userset grants. Assert both, and assert that the
    three named victims are the shapes this module claims they are.
    """
    g = _Harness().seed()
    try:
        rows = g.residue_rows()
        assert rows, 'no residue rows at all -- every test in this module is vacuous'
        neg = {n for r in rows for n in json.loads(r.neg)}
        upos = {n for r in rows for n in json.loads(r.upos)}
        assert neg, 'no `neg`: the exclusion stopped recording star-covered exclusions'
        assert upos, 'no `upos`: the userset grants stopped recording memberships'

        neg_node = g.node(*NEG_VICTIM)
        upos_node = g.node(*UPOS_VICTIM)
        free_node = g.node(*UNREFERENCED)
        assert neg_node is not None and upos_node is not None and free_node is not None
        assert neg_node.id in neg, f'{NEG_VICTIM} is no longer a `neg` subject'
        assert upos_node.id in upos, f'{UPOS_VICTIM} is no longer a `upos` subject'
        assert free_node.id not in (neg | upos), \
            f'{UNREFERENCED} became recorded -- the non-vacuity control is now vacuous'
    finally:
        g.close()


# --------------------------------------------------------------------------- #
# The positive pins
# --------------------------------------------------------------------------- #

def test_a_neg_recorded_node_cannot_be_removed():
    """The witness arm: the `neg` subject, paranoia OFF, no cascade in the txn."""
    g = _Harness().seed()
    try:
        assert g.node(*NEG_VICTIM) is not None
        with pytest.raises(AdmissionRejected, match=MESSAGE):
            g.widx.remove_node(*NEG_VICTIM)
    finally:
        g.session.rollback()
        g.close()


def test_a_upos_recorded_node_cannot_be_removed():
    """The second witness: a ``upos`` subject that is EXPLICIT with a non-zero
    reference count (``implicit=False``, ``reference_count=3`` when observed), so
    neither an implicit-only nor a refcount-based guard would have caught it. The
    guard keys on the residue REFERENCE, which is what ``ResidueRefV1`` indexes."""
    g = _Harness().seed()
    try:
        victim = g.node(*UPOS_VICTIM)
        assert victim is not None and victim.implicit is False, \
            'the upos subject must be EXPLICIT -- state-functional canonical form'
        assert victim.reference_count > 0, \
            'a refcount-keyed guard would be enough if this were 0 -- premise drifted'
        with pytest.raises(AdmissionRejected, match=MESSAGE):
            g.widx.remove_node(*UPOS_VICTIM)
    finally:
        g.session.rollback()
        g.close()


def test_removing_the_node_that_owns_a_residue_row_is_refused():
    """The OWNER clause of the guard (``ResidueV1.object_node_id``), which covers a
    different I6 clause than the reverse-index clause: ``residue row 1 references a
    missing node 3``, observed pre-fix on committed state.

    Reachability is honest, and both halves are asserted here: an ordinary caller is
    stopped earlier by I5 exclusivity (a plain ``ValueError``, deliberately not an
    ``AdmissionRejected`` -- a routing bug, not an inadmissible write), while with
    ``processor_writes`` ON -- a shipped public property, set exactly this way in
    ``tests/test_wildcard_remove_node.py::test_remove_node_respects_derived_exclusivity``
    -- ``_assert_derived_exclusivity`` returns early and this guard is the only thing
    left between the call and the delete.
    """
    g = _Harness().seed()
    try:
        row = g.residue_rows()[0]
        owner = g.session.get(NodeV4, row.object_node_id)
        assert owner is not None and (owner.type, owner.predicate) in \
            g.rs.schema_info.derived_families

        with pytest.raises(ValueError, match='processor') as i5:
            g.widx.remove_node(owner.predicate, owner.type, owner.name)
        assert not isinstance(i5.value, AdmissionRejected), \
            'I5 exclusivity must stay an unclassified ValueError (ZT-P4-7)'

        g.widx.processor_writes = True
        try:
            with pytest.raises(AdmissionRejected, match=MESSAGE):
                g.widx.remove_node(owner.predicate, owner.type, owner.name)
        finally:
            g.widx.processor_writes = False
        assert g.session.get(NodeV4, owner.id) is not None
    finally:
        g.session.rollback()
        g.close()


# --------------------------------------------------------------------------- #
# The refusal is CONDITIONAL (non-vacuity control C3), and clean
# --------------------------------------------------------------------------- #

def test_an_unreferenced_node_is_still_removable_and_commits_clean():
    """⚠ THE LOAD-BEARING CONTROL. A blanket refusal would pass every other test in
    this module while breaking ordinary ``remove_node`` traffic on any boolean store.

    ``group:g3#member`` is a userset subject and therefore NOT star-covered, so it is
    recorded in neither ``neg`` nor ``upos``; it must still remove, and the committed
    state must pass both invariant tiers (observed pre-fix as control C3: `remove_node:
    returned` / `commit: returned` / `residue-tier check: PASSED`).
    """
    g = _Harness().seed()
    try:
        victim = g.node(*UNREFERENCED)
        assert victim is not None
        assert g.widx._residue_records_node(victim.id) is False, \
            'the control node became recorded -- this test would prove nothing'

        g.widx.remove_node(*UNREFERENCED)
        g.session.commit()

        live = g.committed_check()
        assert victim.id not in live, 'the unreferenced node was not actually removed'
    finally:
        g.close()


def test_the_refusal_leaves_the_state_untouched():
    """I12 rejection cleanliness: the guard runs before ANY write (the store lock plus
    two reads), so a refused ``remove_node`` must leave the session with nothing
    pending, the row multisets identical, the residues and their reverse index
    byte-identical -- and the state must still commit clean afterwards."""
    g = _Harness().seed()
    try:
        before_rows = snapshot(g.widx)
        before_residue = g.residue_state()
        before_refs = g.ref_index()
        before_ids = g.node_ids()

        with pytest.raises(AdmissionRejected, match=MESSAGE):
            g.widx.remove_node(*NEG_VICTIM)

        assert not g.session.new and not g.session.deleted and not g.session.dirty, \
            ('the refusal left pending work in the session: '
             f'new={g.session.new} deleted={g.session.deleted} dirty={g.session.dirty}')
        assert snapshot(g.widx) == before_rows
        assert g.residue_state() == before_residue
        assert g.ref_index() == before_refs
        assert g.node_ids() == before_ids

        # Committing after a refusal is a no-op that must not corrupt anything.
        g.session.commit()
        live = g.committed_check()
        assert set(before_ids) == live
    finally:
        g.close()


# --------------------------------------------------------------------------- #
# The sanctioned path the refusal message names
# --------------------------------------------------------------------------- #

def test_the_sanctioned_path_removes_the_recording_then_the_node():
    """End-to-end for the alternative the message names: remove the tuples that record
    the node (which the cascade prunes out of ``neg``/``upos``), THEN remove the node.

    This is what makes the refusal a routing instruction rather than a dead end.
    """
    g = _Harness().seed()
    try:
        victim = g.node(*UPOS_VICTIM)
        assert victim is not None
        victim_id = victim.id
        assert g.widx._residue_records_node(victim_id) is True

        # The recordings are the two `viewer` grants that lift g2 into `upos`.
        g.apply(('member', 'group', 'g2', 'viewer', 'doc', 'x'), 'remove')
        g.apply(('member', 'group', 'g2', 'viewer', 'doc', 'y'), 'remove')

        recorded = {n for r in g.residue_rows()
                    for n in json.loads(r.neg) + json.loads(r.upos)}
        assert victim_id not in recorded, \
            'the cascade did not prune the recording -- the sanctioned path is broken'

        still_there = g.session.get(NodeV4, victim_id)
        assert still_there is not None, \
            'the reconcile GC already collected the node; this arm needs it alive'
        g.widx.remove_node(*UPOS_VICTIM)
        g.session.commit()

        live = g.committed_check()
        assert victim_id not in live
    finally:
        g.close()


# --------------------------------------------------------------------------- #
# The refusal runs BEFORE the bridge strip (the load-bearing ordering)
# --------------------------------------------------------------------------- #

def test_the_refusal_runs_before_the_bridge_strip():
    """⚠ THE ORDERING PIN. ``remove_node`` calls ``_strip_bridges`` before the core
    removal, and ``_strip_bridges`` both WRITES (``remove_edge_by_id``) and can
    implicit-GC the node outright, in which case the facade takes an early ``return``
    and the rest of the method never runs. A refusal placed after it is therefore
    reached too late and, worse, refuses a transaction that has already written.

    This needs its own fixture: the main one has no bridged node, so moving the check
    after the strip leaves every other test here GREEN (observed 2026-09-20, sabotage
    S4: ``8 passed``). Here ``group:g2#member`` is bridged AND recorded, so a refusal
    that fires late leaves the stripped bridge edge behind and the snapshot moves.
    """
    g = _Harness(store_id=BRIDGED_STORE, schema=BRIDGED_SCHEMA, setup=BRIDGED_SETUP).seed()
    try:
        victim = g.node(*UPOS_VICTIM)
        assert victim is not None
        assert g.widx._residue_records_node(victim.id) is True

        # Premise, mechanical: exactly the condition under which `_strip_bridges`
        # issues a `remove_edge_by_id`. Without it this test re-tests the fixture
        # above instead of the ordering.
        shape = (victim.type, victim.predicate)
        assert shape in g.widx.schema_info.bridged_in_shapes
        w_any = g.widx._w_node(victim.type, victim.predicate, 'any', create=False)
        assert w_any is not None, 'no w node -- nothing to strip, ordering unpinned'
        assert g.widx.idx.direct_edge_exists_by_id(victim.id, w_any.id),             'the victim holds no bridge edge -- `_strip_bridges` would write nothing'

        before = snapshot(g.widx)
        with pytest.raises(AdmissionRejected, match=MESSAGE):
            g.widx.remove_node(*UPOS_VICTIM)
        assert snapshot(g.widx) == before,             'the refusal fired AFTER a write -- the check moved below _strip_bridges'
        assert not g.session.new and not g.session.deleted and not g.session.dirty
    finally:
        g.session.rollback()
        g.close()


# --------------------------------------------------------------------------- #
# The guard is a faithful mirror of the processor's own rule
# --------------------------------------------------------------------------- #

def test_the_guard_agrees_with_the_processor_on_every_node():
    """``WildcardIndex._residue_records_node`` duplicates
    ``DeltaProcessor._residue_references`` (plus the owner clause) because
    ``core -> processor -> wildcard -> core`` is a real import cycle. Duplicated logic
    drifts, so pin the agreement over EVERY node in the store -- so an over-reporting
    guard (which would break ordinary removals) is caught as well as an
    under-reporting one (which would re-open the corruption).

    ``owns`` is computed straight from ``ResidueV1.object_node_id`` here, not from the
    guard, so the two sides are independent.
    """
    g = _Harness().seed()
    try:
        owners = {r.object_node_id for r in g.residue_rows()}
        ids = g.node_ids()
        assert ids, 'no nodes -- the comparison below would run zero times'

        recorded_hits = 0
        for nid in ids:
            expected = (nid in owners) or g.proc._residue_references(nid)
            assert g.widx._residue_records_node(nid) is expected, \
                f'guard disagrees with the processor on node {nid}'
            recorded_hits += bool(expected)

        # Scope, not just execution: a store where nothing is recorded would satisfy
        # every assertion above by answering False on both sides, every time.
        assert recorded_hits >= 3, \
            f'only {recorded_hits} recorded node(s) -- the comparison saw no real state'
        assert len(ids) - recorded_hits >= 1, \
            'every node is recorded -- the False direction was never exercised'
        assert g.widx._residue_records_node(-1) is False, \
            'an id no node holds must answer False (the lookup is real, not stubbed)'
    finally:
        g.close()


# --------------------------------------------------------------------------- #
# The two clauses the 2026-09-20 mutation sweep found UNPINNED
# --------------------------------------------------------------------------- #

def test_a_dangling_residue_ref_does_not_count_as_a_recording():
    """⚠ THE LIVENESS FILTER (sweep M2). ``_residue_records_node``'s second clause
    keeps a ``ResidueRefV1`` row only if the RECORDING OBJECT node still exists, and
    deleting that filter -- ``if s.get(NodeV4, r.object_node_id) is not None`` ->
    an unconditional ``return True`` -- left this module GREEN at ``9 passed``.

    The agreement pinned by ``test_the_guard_agrees_with_the_processor_on_every_node``
    is trivially satisfiable: on a store whose every reverse-index row points at a live
    object the filter changes no answer, so "every node" never reaches the one state
    where the guard and ``DeltaProcessor._keys_referencing`` can differ. This test IS
    that state. A dangling row yields no reconcile key for the processor, so it must
    not refuse a removal either -- otherwise the facade refuses a LEGAL
    ``remove_node`` (fail-closed on an admin API) on state the processor considers
    unreferenced.

    The state is built deliberately corrupt (a residue row whose object node is gone,
    itself the I6 clause ``residue row N references a missing node M``) and is NEVER
    committed: it is the input the liveness filter exists to interpret, not a state
    the system is allowed to reach.
    """
    g = _Harness().seed()
    try:
        victim = g.node(*UPOS_VICTIM)
        assert victim is not None
        rows = g.session.exec(
            select(ResidueRefV1)
            .where(ResidueRefV1.store_id == g.store_id)
            .where(ResidueRefV1.subject_node_id == victim.id)).all()
        assert rows, 'the victim holds no reverse-index row -- nothing to dangle'
        # The answers MOVE (True -> False) across the corruption below. Without this,
        # a fixture that stopped recording the victim would satisfy the assertions at
        # the bottom by answering False all along.
        assert g.widx._residue_records_node(victim.id) is True
        assert g.proc._residue_references(victim.id) is True
        assert victim.id not in {r.object_node_id for r in g.residue_rows()}, \
            'the victim OWNS a residue row -- the first clause, not the filter, answers'

        # MECHANICAL PREMISE: delete the recording OBJECT nodes, then read the premise
        # back out of the database. Do not assume the delete reached the state needed:
        # if the reverse-index rows went with the nodes, nothing dangles and every
        # assertion below is vacuous.
        for r in rows:
            obj = g.session.get(NodeV4, r.object_node_id)
            assert obj is not None, 'the recording object node is already gone'
            g.session.delete(obj)
        g.session.flush()
        dangling = g.session.exec(
            select(ResidueRefV1)
            .where(ResidueRefV1.store_id == g.store_id)
            .where(ResidueRefV1.subject_node_id == victim.id)).all()
        assert dangling, \
            'the reverse-index rows went with the node rows -- nothing dangles'
        assert all(g.session.get(NodeV4, r.object_node_id) is None for r in dangling), \
            ('a recording object node survived -- those rows are still LIVE and the '
             'liveness filter is not being exercised')

        assert g.widx._residue_records_node(victim.id) is False, \
            ('a DANGLING reverse-index row was counted as a live recording -- the '
             'liveness filter is gone, and the guard now over-reports where the '
             'processor does not')
        assert g.proc._residue_references(victim.id) is False, \
            'the processor changed its liveness rule; the guard must follow it'

        # Behaviour, not only the predicate: the removal is legal and must go through.
        g.widx.remove_node(*UPOS_VICTIM)
        assert g.session.get(NodeV4, victim.id) is None
    finally:
        g.session.rollback()
        g.close()


def test_the_guard_is_scoped_to_its_own_store():
    """⚠ THE STORE SCOPING (sweep M10). Both queries in ``_residue_records_node``
    filter on ``store_id``; deleting BOTH ``.where(... .store_id == sid)`` clauses left
    this module GREEN at ``9 passed``, because a single-store fixture cannot tell a
    scoped query from an unscoped one.

    Latent is not harmless. ``NodeV4.id`` is a GLOBAL primary key backed by a plain
    SQLite rowid, so ids are recycled -- the very ZT-P0-1 hazard this refusal exists
    for. An unscoped guard hands one store's answer to another, and the direction is
    fail-closed: a legal ``remove_node`` refused because an unrelated store's residue
    happens to name the same integer.

    The fixture is two stores CO-TENANT on one session (one engine, one ``NodeV4``
    table, one id sequence), seeded identically, with the premises asserted
    mechanically: the sessions are the same object, the id sets are disjoint, each
    victim id resolves to a node of the store that owns it, and each store's guard
    answers True for its OWN victim -- so a False below is scoping, not a dead
    instrument.
    """
    a = _Harness().seed()
    b = _Harness(store_id=XSTORE, session=a.session).seed()
    try:
        # MECHANICAL PREMISE 1: one session, one table -- not two isolated databases.
        assert b.widx.idx.session is a.session, \
            'the two facades do not share a session; this proves nothing about scoping'
        # MECHANICAL PREMISE 2: a single GLOBAL id sequence, disjoint per store.
        a_ids, b_ids = a.node_ids(), b.node_ids()
        assert a_ids and b_ids, 'a store has no nodes -- the comparison is vacuous'
        assert not (set(a_ids) & set(b_ids)), \
            'the stores share node ids; then a cross-store read is not observable'

        a_victim = a.node(*UPOS_VICTIM)
        b_victim = b.node(*UPOS_VICTIM)
        assert a_victim is not None and b_victim is not None
        assert a_victim.id != b_victim.id
        assert a.session.get(NodeV4, a_victim.id).store_id == a.store_id
        assert a.session.get(NodeV4, b_victim.id).store_id == b.store_id

        a_owner = a.residue_rows()[0].object_node_id
        b_owner = b.residue_rows()[0].object_node_id
        assert a_owner != b_owner

        # MECHANICAL PREMISE 3: there is something to leak, and both instruments work.
        assert a.widx._residue_records_node(a_victim.id) is True
        assert b.widx._residue_records_node(b_victim.id) is True
        assert a.widx._residue_records_node(a_owner) is True
        assert b.widx._residue_records_node(b_owner) is True

        # THE PINS -- both clauses, both directions.
        assert b.widx._residue_records_node(a_victim.id) is False, \
            ("store %s's guard sees store %s's reverse-index rows -- the ResidueRefV1 "
             'query lost its store_id filter' % (b.store_id, a.store_id))
        assert a.widx._residue_records_node(b_victim.id) is False, \
            'the reverse-index query is unscoped in the other direction too'
        assert b.widx._residue_records_node(a_owner) is False, \
            ("store %s's guard sees store %s's residue ROWS -- the ResidueV1 query "
             'lost its store_id filter' % (b.store_id, a.store_id))
        assert a.widx._residue_records_node(b_owner) is False, \
            'the residue-row query is unscoped in the other direction too'
    finally:
        b.close()
        a.session.rollback()
        a.close()


if __name__ == '__main__':          # pragma: no cover
    pytest.main([__file__, '-q'])
