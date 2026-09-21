"""TK92: the bulk mirror's ``[rel]`` term is REACHABLE — and the corpus could never
show it, because no conformance schema uses a DERIVED relation as a userset subject.

WHAT THIS MODULE SETTLES
------------------------
``index_v4/bulk_backfill.py::_BulkBackfill._live_keys_of`` mirrors
``index_v4/processor.py::DeltaProcessor._live_keys_of``, including the leading ``rel`` in

    preds = [rel] + [spec.predicate for spec in plan.leaves
                     if spec.positive and spec.kind in ('closure', 'derived-userset')]

On the PROCESSOR side that term is a repair affordance and deleting it is a live
authorization fail-open (``TK91``, ``tests/test_reg_tk91_live_keys_repair.py``). On the
BULK side ``TK91`` left a hypothesis behind, explicitly labelled UNVERIFIED: that
``connectedstore/build.py::build_index`` "refuses to run on an index that already has
state", so the bulk backfill only ever sees a store it built itself and its ``[rel]`` term
might be **unreachable by construction**.

(!) **THAT HYPOTHESIS IS REFUTED, and this module is the refutation.** The defence is
about INCONSISTENT stores; it says nothing about the other way ``family_names[(t, rel)]``
can be non-empty at enumeration time. A stored USERSET SUBJECT ``group:eng#member``
interns the node ``(member, group, eng)`` during the bulk LOAD, before any backfill runs —
and if ``eng`` has no positive-leaf state, the ``[rel]`` term is the ONLY thing that
enumerates it. Measured 2026-09-21: ``_live_keys_of('group', 'member')`` returns
``['eng', 'ops']`` where the non-``rel`` half returns ``['ops']`` alone.

WHY FOUR WHOLE MODULES MEASURED IT INERT
----------------------------------------
Census over all 26 entries of ``formal/conformance/corpus.py::SCHEMAS`` (2026-09-21),
crossing each schema's compiled ``plans`` keys against the ``[type#pred]`` userset
subjects in its text: four corpora use a userset subject at all (``group_userset``,
``wildcard_group_member``, ``taint_union_userset_arm``, ``residue_rich``) and in **every
one** the referenced ``group.member`` is a plain direct relation. **The intersection is
empty across all 26.** The corpora cannot reach the branch, so their green never said
anything about it — and the bulk-vs-incremental identity gate has never run on this input
class at all. ``test_bulk_matches_incremental_on_a_derived_userset_schema`` is that gap.

AND YET THE TERM IS INERT HERE — WHICH IS WHY IT STAYS, AND IS NOT PINNED AS LOAD-BEARING
------------------------------------------------------------------------------------------
Reached is not the same as load-bearing. ``preds``' second term looks only at POSITIVE
leaves, so the sharp case is an object whose only state sits on a SUBTRAHEND. Measured
2026-09-21 over three arms — ``eng`` with ``blocked``-only state and a userset subject;
``blocked``-only without one; no state with one — the built state is byte-identical with
and without the ``[rel]`` term, and identical to ``bulk=False`` in all three.

REASONED (``docs/tk92-bulk-rel-term-2026-09-21.md`` §3.4), and labelled as such: a
rel-exclusive name is by definition one with no positive-leaf state of any of the five
``LeafSpec.kind`` values, positive leaves are the only candidate generators in
``_reconcile``, so such a name reconciles to the empty membership and writes nothing.

(!) **SO DO NOT "FIX" THIS BY DELETING THE MIRROR'S TERM.** It is reached, so it is not
dead code; it writes nothing, so it is not a fail-open; and the mirror's stated contract
is to track ``DeltaProcessor`` step for step. The pins below assert what is TRUE — that
the term is reached and rel-exclusive, and that the two constructors agree on this input
class — not that the mutation is inert. A test whose claim is "this mutation changes
nothing" is a test that cannot be sabotaged.

SABOTAGE (2026-09-21, ``docs/sabotage-procedure.md``), literal observed output. Each run
is ``pytest tests/test_reg_tk92_bulk_rel_term.py -q`` with one byte-level edit to
``index_v4/bulk_backfill.py``:

  * CLEAN: ``4 passed in 0.38s``

  * S1 — delete the leading ``rel`` from the bulk mirror's ``preds``
    (``preds = [rel] + [...]`` -> ``preds = [...]``), the mutation this row exists for::

        AssertionError: the bulk [rel] term did not enumerate 'eng' -- TK92's
          refutation has stopped holding. _live_keys_of('group', 'member') = ['ops']
        AssertionError: the shipped preds no longer equals rel_term | other_terms at
          ('group', 'member'): shipped=['ops'] rel_term=['eng', 'ops'] other=['ops']
        FAILED ...::test_bulk_rel_term_is_reached_and_exclusive
        FAILED ...::test_instrument_models_the_shipped_preds
        2 failed, 2 passed in 0.44s

    Two reds, each naming its own claim: the refutation, and the instrument's model of
    the body. The identity arm stays GREEN and correctly so — the term is inert, so
    removing it does not move the built state. That green is the reason this module
    does not route its pin through state comparison (the 2026-09-13e lesson: assert off
    the primitive the mutation touches, never through a helper that cannot see it).

  * S2 — the instrument control: flip
    ``test_bulk_rel_term_is_reached_and_exclusive``'s own claim to ``'eng' not in got``::

        FAILED ...::test_bulk_rel_term_is_reached_and_exclusive
        1 failed, 3 passed in 0.42s

    S2 confirms the pin fails when it should; without it a green S1 arm would be
    unreadable.

MODULE MUTATION SWEEP (2026-09-21) — a sabotage certifies ONE test, so the whole
enumerator was swept: 11 runtime monkeypatches, each a copy of the shipped body with one
named line changed. Full table in ``docs/tk92-bulk-rel-term-2026-09-21.md`` §6.

  * ``M_ID``, the FIDELITY CONTROL — the reconstruction with NOTHING changed — is
    ``4 passed``. Without it a red anywhere below could be the harness dying rather than
    a pin firing (the ``GL-1`` lesson).
  * **5 of 10 caught**: ``M1`` drop ``[rel]``; ``M2`` keep only ``[rel]``; ``M3`` drop
    the ``spec.positive`` filter; ``M4`` narrow the kinds to ``('closure',)``;
    ``M8`` look the family up by ``rel`` instead of ``pred``.
  * **4 are UNREACHABLE on this fixture and are NOT reported as inert pins** — the
    mutated branch never executes, which is a statement about the fixture, not the
    module. Verified by reading the plans: ``member``'s leaves are
    ``[('member.0','closure',True), ('member.1','closure',False)]`` and ``viewer``'s are
    ``[('viewer.0','closure',True), ('viewer.1','derived-userset',True)]``, so there is
    no ``derived-computed`` (``M5``), ``derived-ttu`` (``M6``) or
    ``derived-tupleset-ttu`` (``M7``) leaf to drop, and the seed set holds zero
    ``wild != ''`` nodes (``M9``; measured ``[]``).
  * **1 is REACHED and MASKED, measured and DELIBERATELY NOT PINNED**: ``M10``, dropping
    ``::_intern``'s ``family_names`` update. ``_intern`` added ``2`` nodes on this
    fixture, so the line runs — but a family populated DURING the run is only observable
    if a later enumeration reads it, and across two strata nothing does. Unmasking it
    needs a schema where one relation's from-chain interning lands in a family that a
    later stratum enumerates; that is a bigger fixture than this row bought.

(!) ``M3`` was GREEN until the fixture gained ``qa`` (see ``_TUPLES``). It was reached
the whole time — the subtrahend family was simply a SUBSET of the positive one, so
dropping the filter enumerated the same names. A masked mutation reads exactly like a
clean pin, which is why the sweep classifies by REACHED, not by colour.

Map: ``docs/tk92-bulk-rel-term-2026-09-21.md``. The processor-side story is
``tests/test_reg_tk91_live_keys_repair.py`` and
``docs/tk91-tk80-removal-coverage-2026-09-20.md`` §4.2; nothing here weakens either.
"""

import json

from sqlmodel import Session, SQLModel, create_engine, select

from connectedstore import TupleSource, build_index, save_schema
from index_v4 import bulk_backfill
from index_v4.invariants import snapshot_rows
from index_v4.models import ResidueV1
from zanzibar_utils_v1 import parse_openfga_schema

# `member` is DERIVED (`allowed but not blocked`) *and* is the subject predicate of a
# stored userset on `viewer`. That pairing is what no conformance corpus has.
_SCHEMA = '''
    type user
    type group
      relations
        define allowed: [user]
        define blocked: [user]
        define member: allowed but not blocked
    type doc
      relations
        define viewer: [user, group#member]
'''

# `ops` carries `member` leaf state, so the positive-leaf half of `preds` names it.
# `eng` carries NONE -- it exists only because `group:eng#member` is a stored subject --
# so it is enumerated by the leading `rel` and by nothing else.
#
# `qa` carries SUBTRAHEND-only state and is not a userset subject, so nothing enumerates
# it. It is not decoration: it is what makes the `spec.positive` filter load-bearing.
# Without it the `blocked` family is a SUBSET of the `allowed` family, and dropping the
# filter altogether (sweep M3) enumerates the same names and stays green -- a masked
# mutation that reads exactly like a clean pin (`docs/sabotage-procedure.md`, the
# P6 step-2 lesson). With `qa` present, M3 is caught.
_TUPLES = [
    ('...', 'user', 'u1', 'allowed', 'group', 'ops'),
    ('...', 'user', 'u2', 'blocked', 'group', 'ops'),
    ('...', 'user', 'u9', 'blocked', 'group', 'qa'),
    ('member', 'group', 'ops', 'viewer', 'doc', 'd1'),
    ('member', 'group', 'eng', 'viewer', 'doc', 'd2'),
]
_KEY = ('group', 'member')
_EXCLUSIVE = 'eng'
_LEAF_BACKED = 'ops'


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _preds_without_rel(bf, o_type, rel, enumerate_sub):
    """The half of ``_live_keys_of``'s enumeration that is NOT the leading ``rel``.

    Kept in lockstep with ``index_v4/bulk_backfill.py::_BulkBackfill._live_keys_of``;
    ``test_instrument_models_the_shipped_preds`` is the mechanical check that it still
    is. ``enumerate_sub`` is the shipped (unwrapped) enumerator, used for the recursive
    leaf kinds so the model recurses exactly as the body does.
    """
    plan = bf.compiled.plans[(o_type, rel)]
    names = set()
    for spec in plan.leaves:
        if spec.positive and spec.kind in ('closure', 'derived-userset'):
            names |= set(bf.family_names.get((o_type, spec.predicate), ()))
    for spec in plan.leaves:
        if not spec.positive or spec.kind in ('closure', 'derived-userset'):
            continue
        if spec.kind == 'derived-computed':
            names |= enumerate_sub(bf, o_type, spec.predicate)
        elif spec.kind == 'derived-ttu':
            node = bf._find_leaf_node(spec)
            names |= set(bf.family_names.get((o_type, node.tupleset_rel), ()))
        elif spec.kind == 'derived-tupleset-ttu':
            node = bf._find_leaf_node(spec)
            names |= enumerate_sub(bf, o_type, node.tupleset_rel)
    return names


def _build(tuples, *, bulk):
    """A fresh index built by the production bootstrap over a tuple snapshot."""
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    save_schema(session, 'src', _SCHEMA, frozenset())
    src = TupleSource(session, 'src')
    for raw in tuples:
        src.add(*raw)
    session.commit()
    _, widx, _ = build_index(session, 'src', 'idx', bulk=bulk)
    return session, widx


def _enumerations(tuples):
    """Run a real ``bulk=True`` build, recording for every ``_live_keys_of`` call what
    the shipped body returned and what each half of ``preds`` held AT THAT MOMENT.

    The snapshot has to be taken inside the call: ``family_names`` grows during the run
    as ``_intern`` adds public and from-chain nodes, so reading it afterwards would
    answer a different question than the one the enumerator asked.
    """
    rec: dict = {}
    orig = bulk_backfill._BulkBackfill._live_keys_of

    def wrapped(self, o_type, rel):
        got = orig(self, o_type, rel)
        rec.setdefault((o_type, rel), {
            'got': set(got),
            'rel_term': set(self.family_names.get((o_type, rel), ())),
            'other': _preds_without_rel(self, o_type, rel, orig),
        })
        return got

    bulk_backfill._BulkBackfill._live_keys_of = wrapped
    try:
        session, widx = _build(tuples, bulk=True)
    finally:
        bulk_backfill._BulkBackfill._live_keys_of = orig
    return rec, session, widx


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


# --------------------------------------------------------------------------- #
# (0) the fixture guard -- a mechanical refusal of a vacuous module
# --------------------------------------------------------------------------- #

def test_fixture_puts_a_derived_relation_behind_a_userset_subject():
    """Property guarded: ``group.member`` is DERIVED *and* is reached through a userset
    subject of ``doc.viewer``.

    Every other test here is vacuous without both halves. Lose the boolean operator and
    ``member`` has no plan, so ``_live_keys_of`` is never called for it and the
    refutation below tests nothing; lose the ``group#member`` subject restriction and no
    node is ever interned under the public ``member`` predicate, so the ``[rel]`` term
    goes back to enumerating nothing. On a failure here the repair is to restore the
    fixture, never to relax the test.
    """
    rs = parse_openfga_schema(_SCHEMA, frozenset())
    plans = rs.compiled.plans
    assert _KEY in plans, (
        f'{_KEY} is no longer a derived relation -- the fixture has lost the boolean '
        f'operator that gives it a plan. plans={sorted(plans)}')

    viewer_leaves = plans[('doc', 'viewer')].leaves
    reaches_member = [spec for spec in viewer_leaves
                      if spec.kind == 'derived-userset' and spec.positive]
    assert reaches_member, (
        "doc.viewer no longer reaches group.member through a userset leaf; "
        f"leaves={[(s.predicate, s.kind, s.positive) for s in viewer_leaves]}")


# --------------------------------------------------------------------------- #
# (1) the refutation
# --------------------------------------------------------------------------- #

def test_bulk_rel_term_is_reached_and_exclusive():
    """``TK92``'s whole question: the bulk mirror's leading ``rel`` contributes a name
    that no other term in ``preds`` does.

    Asserted directly on what the enumerator RETURNED, not on any consequence of it.
    The consequence is nothing at all -- the name reconciles to the empty membership --
    so a state-comparison pin here would be green under the mutation and would read
    exactly like a clean pin.
    """
    rec, _session, _widx = _enumerations(_TUPLES)
    assert _KEY in rec, (
        f'_live_keys_of was never called for {_KEY}; the bulk path did not run or the '
        f'fixture lost its plan. called for: {sorted(rec)}')
    seen = rec[_KEY]

    assert _EXCLUSIVE in seen['got'], (
        f"the bulk [rel] term did not enumerate {_EXCLUSIVE!r} -- TK92's refutation has "
        f"stopped holding. _live_keys_of{_KEY} = {sorted(seen['got'])}")
    assert _EXCLUSIVE not in seen['other'], (
        f"{_EXCLUSIVE!r} is now reachable through a positive leaf, so it no longer "
        f"witnesses the [rel] term. other terms = {sorted(seen['other'])}")
    assert _LEAF_BACKED in seen['other'], (
        f'the fixture lost its leaf-backed control {_LEAF_BACKED!r}; without it a green '
        f'above cannot distinguish "the rel term works" from "nothing else ran". '
        f"other terms = {sorted(seen['other'])}")


def test_instrument_models_the_shipped_preds():
    """CEILING CONTROL for the test above: the model of ``preds`` used by
    ``_preds_without_rel`` plus the ``rel`` family must equal what the shipped function
    actually returned, on EVERY call the build made.

    Without this, ``_EXCLUSIVE not in other`` could pass because the model silently
    stopped covering a leaf kind rather than because the name is genuinely rel-exclusive
    -- a green that means the instrument broke. ``LeafSpec.kind`` is one of five values
    (``zanzibar_utils_v1.py::LeafSpec``) and both this model and the shipped body handle
    all five; this is what holds that in lockstep as either changes.
    """
    rec, _session, _widx = _enumerations(_TUPLES)
    assert rec, 'no _live_keys_of call was recorded; the instrument saw nothing'
    for key, seen in sorted(rec.items()):
        assert seen['rel_term'] | seen['other'] == seen['got'], (
            f'the shipped preds no longer equals rel_term | other_terms at {key}: '
            f"shipped={sorted(seen['got'])} "
            f"rel_term={sorted(seen['rel_term'])} other={sorted(seen['other'])}")


# --------------------------------------------------------------------------- #
# (2) the coverage the corpus never had
# --------------------------------------------------------------------------- #

def test_bulk_matches_incremental_on_a_derived_userset_schema():
    """P13's correctness bar -- ``bulk=True`` state is identical to ``bulk=False`` --
    on an input class no conformance corpus contains: a DERIVED relation reached through
    a stored userset subject.

    Census 2026-09-21: of the 26 ``SCHEMAS``, four use a userset subject and in all four
    the referenced relation is plain-direct, so the intersection with the derived
    relations is empty. This arm is the only thing in the tree that drives the bulk
    constructor over a public-family node interned by the LOAD rather than by the
    backfill.
    """
    s_bulk, w_bulk = _build(_TUPLES, bulk=True)
    s_ref, w_ref = _build(_TUPLES, bulk=False)

    got, want = _state(s_bulk, w_bulk), _state(s_ref, w_ref)
    if got != want:
        (gn, ge, gr), (wn, we, wr) = got, want
        raise AssertionError(
            'bulk and incremental constructors disagree on a derived-userset schema; '
            f'nodes: +{sorted(gn - wn)} -{sorted(wn - gn)}; '
            f'edges: +{sorted(ge - we)} -{sorted(we - ge)}; '
            f'residues: {sorted((k, gr.get(k), wr.get(k)) for k in set(gr) | set(wr) if gr.get(k) != wr.get(k))}')
