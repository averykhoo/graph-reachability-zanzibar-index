"""TK78 (boolean spec 5.5): backfill reaches BY ENUMERATION what the live cascade
reaches by dependents-invalidation -- pinned on a fixture where the enumeration is
load-bearing.

WHY THIS MODULE EXISTS (docs/tk78-offline-bootstrap-audit-2026-09-20.md 5-6).
``DeltaProcessor.backfill`` visits exactly the keys ``_live_keys_of`` enumerates and
discards ``self._bumped`` on the way out, so its own docstring states the whole
correctness argument of the offline path:

    "Live maintenance reaches those objects via dependents-invalidation; backfill must
     reach them by ENUMERATION."

Measured 2026-09-20: ``grep -rn '_bumped|_live_keys_of' tests/ formal/ --include=*.py``
returned ZERO -- the property was named nowhere. What the sweep below then measured is
that it was not UNGUARDED, only guarded by accident and in two halves: no single
existing module sees all four leaf kinds.

(!) THE FIXTURE IS THE POINT, AND IT IS GUARDED MECHANICALLY.
``_live_keys_of`` starts from the object's own positive storage families
(``preds = [rel] + closure/derived-userset predicates``) and only then recurses through
the three derived leaf kinds. On a schema where every derived relation has a positive
leaf of its own -- e.g. ``tests/test_invariants_derived.py::_SCHEMA``, whose ``viewer``
is ``(public but not blocked) or editor`` -- the recursion never has to fire and a pin
written over it is VACUOUS. ``_SCHEMA`` below gives ``access`` / ``alias`` a
single positive leaf each, of kind ``derived-ttu`` / ``derived-computed`` respectively,
so the branch under test is the only way those objects can be found. (A third,
``deep: ok from liveparent`` over ``liveparent: [folder] but not dead``, carried the
``derived-tupleset-ttu`` kind until 2026-09-26, when TK106 made a non-direct tupleset a
parse refusal. That recursion branch is unreachable from a checked parse now; dead-code
follow-up on the TK106 row.) ``test_fixture_keeps_the_enumeration_load_bearing`` refuses a
future edit that gives any of them a storage family -- do not "fix" a failure there by
relaxing it.

GROUND TRUTH is "every key the live cascade's ``reconcile`` actually CHANGED", not
"every key it scheduled". The cascade over-schedules: measured here 2026-09-20, the live
run reconciled ``('doc', 'deep', 'f1')`` -- a FOLDER name under a doc relation, mapped in
by ``_map_deltas_to_keys`` off the ``folder#ok`` derived edge (``deep`` left the fixture
with TK106). That reconcile is a no-op
and demanding the enumerator reach it would be wrong. The same asymmetry is recorded
from the other side in ``DeltaProcessor._check_cascade_fixpoint``'s docstring.

The corpus is ADD-ONLY on purpose. Backfill builds from SURVIVING tuples while the live
arm replays a HISTORY, so remove histories are where the two constructions may
legitimately diverge -- that is a separate item (TK91), not this one, and a key whose
object has gone dead is exactly the case where the cascade's scheduled set legitimately
exceeds the enumeration.

SWEEP (docs/sabotage-procedure.md), run 2026-09-20 over BOTH copies of the enumerator at
once unless marked. The harness was throwaway and gitignored, per that procedure -- THIS
TABLE is the evidence, and it is also in the TK78 doc. RED = caught, green = missed.
`inv_derived` is tests/test_invariants_derived.py and was green on every row, so it is
omitted.

    mutation (both copies)        this module   test_bulk_build   conformance_bulk_state
    drop derived-computed         RED           green             RED [star_two_strata_churn,
                                                                   taint_computed_root_over_boolean,
                                                                   two_stratum_cascade]
    drop derived-ttu              RED           RED [boolean,     green
                                                     demorgan]
    drop derived-tupleset-ttu     RED           RED [rc2_star_    green
                                                     tupleset]
      (row VACUOUS since TK106, 2026-09-26: the kind is unreachable, `deep` is gone,
       and `rc2_star_tupleset` now runs on the `derived-ttu` path)
    drop derived-userset from     RED           RED [derived_     green
      the preds list                                 member]
    drop `rel` from preds         green         green             green   <- INERT
    recurse through NEGATIVE      green         green             green   <- inverse
      leaves too                                                             control
    M0: flip this module's own    RED           green             green   <- control
      `missing == {}` claim         (attributed to the one test that carries the claim)

(!) A PREDICTION OF THE TK78 AUDIT DOC IS WRONG AND THIS IS THE CORRECTION. Doc sec 5
reasoned that since bulk_backfill.py carries its own copy of the enumerator,
tests/test_bulk_build.py "compares copy A against copy B and a shared under-enumeration
cancels on both arms". MEASURED: it does not cancel -- three of the four kind-drops
redden ``test_bulk_build_identical_to_incremental`` ITSELF with both copies mutated.
REASONED, not verified: the two copies read different substrates -- processor.py
re-queries `node` rows mid-backfill while bulk_backfill.py reads an in-memory
`family_names` index seeded at load and grown through the bulk phases -- so the same
textual edit does not delete the same keys. What survives is the split: test_bulk_build
misses `derived-computed` entirely, the conformance module misses the other three, and
which one catches what is an accident of each module's corpora.

(!) ONE BRANCH IS INERT UNDER THIS CORPUS AND THIS MODULE DOES NOT PIN IT. Dropping
`rel` from `preds` leaves all four modules green. That entry is for objects enumerable
only by their PUBLIC family -- state that outlives the leaf which produced it, i.e. a
REMOVE. The corpus here is add-only by design (above), so the branch cannot move, and an
inert mutation is reported as inert rather than read as a clean pin. It is measured
evidence for TK91 (remove histories), not a hole this module should have closed.

(!) CORRECTION 2026-09-21 (TK92): the paragraph directly above gives the right verdict
for the wrong reason, and the reason matters. "The corpus here is add-only, so the branch
cannot move" treats a REMOVE as the only way an object lands in its public family. It is
not. A stored USERSET SUBJECT ``group:eng#member`` interns ``(member, group, eng)`` at
LOAD time, on an add-only corpus, and where ``member`` is itself derived the ``rel`` entry
is then the only thing that enumerates ``eng`` -- measured 2026-09-21,
``_live_keys_of('group','member')`` returns ``['eng','ops']`` against ``['ops']`` for the
rest of ``preds``. The actual reason this corpus cannot move the branch is narrower: as
censused 2026-09-21, NO schema in ``formal/conformance/corpus.py::SCHEMAS`` THEN paired a
derived relation with a userset subject. The branch is reached but INERT there -- a
rel-exclusive name has no positive-leaf state, so it reconciles to nothing.

(!) **THAT SENTENCE IS NO LONGER TRUE OF `SCHEMAS`, and the change is the point.**
``TK94`` added ``SCHEMAS['derived_userset_subject']`` on 2026-09-22, the first corpus of
the class, so the conformance bulk arm now DOES reach the branch rel-exclusively -- and,
measured over all 27 corpora that day, it is the only one that does
(``formal/probes/tk94_new_arm_reach_2026-09-22.py``). Nothing about THIS module's own
fixture or its conclusions changed; what changed is the claim about the corpus next door,
which is why it is corrected here rather than left to read as current forever. See
``tests/test_reg_tk92_bulk_rel_term.py``, ``docs/tk92-bulk-rel-term-2026-09-21.md`` and
``docs/tk94-derived-userset-corpus-2026-09-22.md``.
"""

import json

from sqlmodel import select

from zanzibar.graphindex.models import Node, Residue
from zanzibar.graphindex.invariants import snapshot_rows
from zanzibar.graphindex.outbox import outbox_watermark
from zanzibar.graphindex.processor import DeltaProcessor
from tests.wildcard_helpers import make_wildcard_index
from zanzibar.schema import Entity, RelationalTriple, parse_openfga_schema


# `access` and `alias` each have EXACTLY ONE positive leaf, and it is a
# recursive kind -- see the module docstring. `shared` is the `derived-userset` case,
# which rides the `preds` list rather than the recursion.
_SCHEMA = '''
    type user
    type group
      relations
        define gblocked: [user]
        define member: [user] but not gblocked
    type folder
      relations
        define blocked: [user]
        define viewer: [user]
        define ok: viewer but not blocked
    type doc
      relations
        define parent: [folder]
        define access: ok from parent
        define alias: access
        define shared: [group#member]
'''

# add-only (see docstring). (`liveparent` / `dead` tuples on d3 / d4 left with `deep`,
# TK106 2026-09-26.)
_OPS = [
    ('...', 'user', 'alice', 'viewer', 'folder', 'f1'),
    ('...', 'user', 'bob', 'viewer', 'folder', 'f1'),
    ('...', 'user', 'bob', 'blocked', 'folder', 'f1'),
    ('...', 'user', 'carol', 'viewer', 'folder', 'f2'),
    ('...', 'folder', 'f1', 'parent', 'doc', 'd1'),
    ('...', 'folder', 'f2', 'parent', 'doc', 'd2'),
    ('...', 'user', 'dave', 'member', 'group', 'g1'),
    ('member', 'group', 'g1', 'shared', 'doc', 'd5'),
]

# the derived leaf kinds the enumerator RECURSES through, one relation each.
_LOAD_BEARING = {
    ('doc', 'access'): 'derived-ttu',
    ('doc', 'alias'): 'derived-computed',
}


def _route(rs, widx, raw, op='add'):
    sp = Ellipsis if raw[0] == '...' else raw[0]
    triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
    fn = widx.add_tuple if op == 'add' else widx.remove_tuple
    for d in rs.apply(triple):
        fn('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
           d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)


def _live_arm():
    """Per-write cascade, recording every key whose ``reconcile`` returned True."""
    rs = parse_openfga_schema(_SCHEMA, enable_boolean=True)
    session, widx = make_wildcard_index(rs.schema_info)
    proc = DeltaProcessor(widx, rs.compiled)

    changed = set()
    inner = proc.reconcile

    def recording(object_type, rel, obj_name, *a, **kw):
        out = inner(object_type, rel, obj_name, *a, **kw)
        if out:
            changed.add((object_type, rel, obj_name))
        return out

    proc.reconcile = recording
    for raw in _OPS:
        wm = outbox_watermark(session, 'test')
        _route(rs, widx, raw)
        proc.run_cascade(wm)
        session.commit()
    proc.reconcile = inner
    proc.audit_fixpoint()
    return rs, session, widx, proc, changed


def _bootstrap_arm(rs):
    """Raw leaf writes, NO cascade -- the state ``build_index`` hands to backfill."""
    session, widx = make_wildcard_index(rs.schema_info)
    for raw in _OPS:
        _route(rs, widx, raw)
    session.flush()
    return session, widx, DeltaProcessor(widx, rs.compiled)


def _preds_only(proc, object_type, rel):
    """The part of ``_live_keys_of`` that does NOT recurse: the object's own positive
    storage families. Kept in lockstep with ``processor.py::_live_keys_of``'s `preds`."""
    plan = proc.compiled.plans[(object_type, rel)]
    preds = [rel] + [spec.predicate for spec in plan.leaves
                     if spec.positive and spec.kind in ('closure', 'derived-userset')]
    names = set()
    for pred in preds:
        rows = proc.session.exec(
            select(Node).where(Node.store_id == proc.store_id)
            .where(Node.type == object_type).where(Node.predicate == pred)
            .where(Node.wildcard == '')
        ).all()
        names.update(n.name for n in rows)
    return names


def _residues_by_name(session, widx):
    out = {}
    for r in session.exec(select(Residue)).all():
        node = widx._node_by_id(r.object_node_id)
        neg = frozenset((n.predicate, n.type, n.name)
                        for n in (widx._node_by_id(i) for i in json.loads(r.neg))
                        if n is not None)
        out[(node.type, node.name, r.relation)] = (r.stars, neg)
    return out


# ---------------------------------------------------------------------------
# (0) the fixture guard -- a mechanical refusal of a vacuous pin
# ---------------------------------------------------------------------------

def test_fixture_keeps_the_enumeration_load_bearing():
    """Property guarded: the three recursive branches of ``_live_keys_of`` are the ONLY
    way this fixture's derived objects can be enumerated at bootstrap.

    Reds if a future schema edit gives `access` / `alias` a storage family of
    its own, which would make every other test in this module pass without ever entering
    the branch it claims to pin. The correct repair is to restore the fixture, never to
    relax this test.
    """
    rs = parse_openfga_schema(_SCHEMA, enable_boolean=True)
    session, widx, proc = _bootstrap_arm(rs)

    for key, kind in _LOAD_BEARING.items():
        plan = rs.compiled.plans[key]
        positive = [s for s in plan.leaves if s.positive]
        assert [s.kind for s in positive] == [kind], (key, [s.kind for s in positive])
        assert _preds_only(proc, *key) == set(), (
            f'{key} is reachable without recursing: the pin over its {kind} branch '
            f'would be vacuous')
        assert proc._live_keys_of(*key), f'{key} enumerates nothing -- fixture is empty'

    # and the `derived-userset` kind, which rides `preds` rather than the recursion
    shared = [s for s in rs.compiled.plans[('doc', 'shared')].leaves if s.positive]
    assert [s.kind for s in shared] == ['derived-userset']
    assert proc._live_keys_of('doc', 'shared') == {'d5'}
    session.close()


# ---------------------------------------------------------------------------
# (1) THE PIN
# ---------------------------------------------------------------------------

def test_live_keys_of_reaches_every_key_the_live_cascade_wrote():
    """Property guarded: for every derived key the LIVE cascade wrote state for,
    ``_live_keys_of`` enumerates that object name from the BOOTSTRAP state (raw leaf
    tuples, no derived state yet). Backfill visits nothing else, so an object missing
    here is an object the offline path silently never reconciles.

    This is the only assertion in the tree that names the ``_live_keys_of`` ==
    ``_fan_out`` correspondence, and the only one that covers all four leaf kinds at
    once; the two modules that catch a drop in practice each miss some of them and
    report it as an opaque state diff several layers away (module docstring).
    """
    rs, live_session, live_widx, live_proc, changed = _live_arm()
    boot_session, boot_widx, boot_proc = _bootstrap_arm(rs)

    assert changed, 'the live arm wrote no derived state -- corpus is inert'
    by_rel = {}
    for (object_type, rel, name) in changed:
        by_rel.setdefault((object_type, rel), set()).add(name)

    missing = {}
    for key, names in sorted(by_rel.items()):
        gap = names - boot_proc._live_keys_of(*key)
        if gap:
            missing[key] = sorted(gap)
    assert missing == {}, (
        f'backfill would never reconcile {missing} -- the live cascade wrote state '
        f'there, and _live_keys_of does not enumerate it')

    # the branches this fixture exists for are each carrying real keys, not empty sets
    for key in _LOAD_BEARING:
        assert by_rel.get(key), f'{key} carries no live state -- the pin is vacuous'

    live_session.close()
    boot_session.close()


# ---------------------------------------------------------------------------
# (2) what the enumeration BUYS: the end state, on the load-bearing fixture
# ---------------------------------------------------------------------------

def test_backfill_equals_live_on_the_load_bearing_fixture():
    """``tests/test_invariants_derived.py::test_backfill_vs_live_equivalence`` asserts
    this shape already, but over a schema whose every derived relation has a storage
    family -- measured 2026-09-20, it stays GREEN under every one of the six mutations
    in the module docstring's table, including all three recursive-branch drops. Same
    comparison, on a fixture that needs them."""
    rs, live_session, live_widx, live_proc, _ = _live_arm()
    boot_session, boot_widx, boot_proc = _bootstrap_arm(rs)

    boot_proc.backfill()
    boot_session.commit()
    boot_proc.audit_fixpoint()

    assert snapshot_rows(live_session, 'test') == snapshot_rows(boot_session, 'test')
    assert _residues_by_name(live_session, live_widx) == _residues_by_name(
        boot_session, boot_widx)

    for q in [('...', 'user', 'alice', 'access', 'doc', 'd1'),
              ('...', 'user', 'bob', 'access', 'doc', 'd1'),
              ('...', 'user', 'carol', 'access', 'doc', 'd2'),
              ('...', 'user', 'alice', 'alias', 'doc', 'd1'),
              ('...', 'user', 'bob', 'alias', 'doc', 'd1'),
              ('...', 'user', 'dave', 'shared', 'doc', 'd5'),
              ('...', 'user', 'ghost', 'alias', 'doc', 'd2')]:
        assert live_widx.check(*q) == boot_widx.check(*q), q

    live_session.close()
    boot_session.close()
