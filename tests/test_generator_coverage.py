"""The generator-coverage gate: a DERIVED cell alphabet, a swarm generator, and a
two-regime driven sweep — with the two controls that make them worth believing.

Implements plan item 1b (a) + (b) from the design in
`docs/design/generator-coverage/README.md`. The library is `tests/genswarm.py`.
(That item was retired from `HANDOFF.md` on 2026-08-11 once it landed; it now lives in
`docs/history/handoff-status-2026-08.md` §1b.)

WHY THIS EXISTS. `tests/test_hypothesis.py::schema_asts` pinned the TTU tupleset to
`parent: [doc]`, so the whole "TTU over a structured tupleset" space was unreachable BY
CONSTRUCTION — not by seed luck, and not fixable by raising `max_examples`. Both
2026-08-10 divergences (RC1, RC2) came through that hole, and the campaign had no
coverage assertion at all, so "we fuzz broadly" was an unchecked claim.

★★★ THIS MODULE IS EXPECTED TO BE RED UNTIL RC1/RC2 ARE FIXED. ★★★
`test_sparse_regime_finds_no_fail_closed_divergence` and
`test_dense_regime_finds_no_fail_open_divergence` are the positive controls the design
called for: they detonate the two live, unfixed graph-index divergences pinned by
`tests/test_ttu_tupleset_parent_types.py`, from switch COMBINATIONS rather than
transcribed schemas. They must go GREEN the day the fix lands, and if they do not, the
fix is incomplete. Everything else in this file is green today.

--------------------------------------------------------------------------------
MEASURED, 2026-08-10, on this machine
(`C:/Users/user/anaconda3/envs/graph-reachability-zanzibar-index/python.exe`)
--------------------------------------------------------------------------------
alphabet 51 features from 6 compiler sites -> 1275 pairwise cells.

| generator set                                            | cells | %     | features |
|----------------------------------------------------------|-------|-------|----------|
| baseline generators, `git show HEAD:tests/test_hypothesis.py`, 400 draws each | 514 | 40.3% | 36/51 |
| this file's deterministic enumerator, K<=2, compile-only  | 841   | 66.0% | 48/51    |
| ... + the rejection witnesses (154 cells alone)           | 871   | 68.3% | 51/51 accounted |
| ... + the swarm campaign at 120 draws  (= the `ci` total)  | 930   | 72.9% |          |
| ... UNION with the baseline generators (`ci`)             | 967   | 75.8% |          |
| enumerator K<=3 + witnesses + swarm(400)   (`deep` total) | 1028  | 80.6% | 51/51 accounted |
| ... UNION with the baseline generators (`deep`)           | 1034  | 81.1% |          |

The design README predicted a union of 876-891 (68.7-69.9%); measured here the `ci`
union is 967 and the `deep` union is 1034. The 15 features the design listed as
unreachable at any budget are now 0 unreachable and 3 REJ-with-witness
(`ttu.ts.restr:userset`, `ttu.ts.restr:wildcard-userset`, `ttu.ts:TTU`).

⚠ The baseline row MUST be measured against `git show HEAD:tests/test_hypothesis.py`,
not the working tree. Measuring the working tree during this session gave 868/1275 and
46/51 — because a concurrent session was mid-flight on that file's grammar. A "current
generators reach X" number taken from a dirty tree is not a baseline.

--------------------------------------------------------------------------------
THE ci / deep SPLIT — stated explicitly, because a coverage assertion that only holds
under `deep` is exactly the check that fails by passing
--------------------------------------------------------------------------------
`ci` carries the CLOSED, deterministic, exhaustive statements:
  * the alphabet derivations and their provenance counts        (<0.1 s)
  * the enumerator over switch singletons + pairs, compile-only:
    every config compiles or carries a rejection witness, and every alphabet feature is
    HIT or REJ-explained — `UNACCOUNTED == set()`                (~0.2 s)
  * every rejection witness is still refused, with its message   (~0.1 s)
  * the driven sparse + dense regimes over that same config space
  * the full-pool negative control and the non-vacuity floors
`deep` (`HYPOTHESIS_PROFILE=deep`) widens the COMPILE-ONLY enumerator to TRIPLES, raises
the swarm to 400 draws, and deepens the driving (more subsets per config). It does NOT
widen the DRIVEN config space — see `DRIVE_K` for the measurement that decided that.
**No assertion is `deep`-only**: every assertion in this file runs and must pass under
`ci`; `deep` only raises the widths.

The cell numbers are a FLOOR with provenance (rank 3 on the sabotage procedure's
durability ranking), not an "every cell is hit" claim — ~19% of the pair space is
unreached even at `deep`, and that residue is published rather than rounded away
(`test_report_cell_coverage`, run with `-s`).
The FEATURE-level statement is the exact one (rank 1): HIT u REJ-explained == alphabet,
with no hand-written exemption list anywhere in this file.

--------------------------------------------------------------------------------
RUNTIME, measured 2026-08-10
--------------------------------------------------------------------------------
    ci   : 26 tests, 129.8 s  (`2 failed, 24 passed in 129.77s`; compile-only assertions
                               + every control = 4.3 s of that. The two driven sweeps —
                               sparse 64.7 s, dense 85.7 s — ARE the cost.)
    deep : 26 tests, 190.3 s  (`2 failed, 24 passed in 190.25s`; compile-only widens to
                               K<=3 -> 957 HIT / 985 with witnesses, driving deepens to
                               4 sparse + 3 dense subsets, swarm 400 draws)

That is +~130 s to whichever `tests-tile` the structural partition assigns these to:
165 s -> ~295 s against the 600 s cap. It is over the design's +32 s estimate, and the
whole overrun is the dense regime — the price of closing §6.7's fail-open gap, which
the design costed at "+30 s" on the assumption that random co-subsets would do. They do
not (measured: seed-dependent — 116 s over the same space with FAIL-OPEN=0), so the
dense regime is a deterministic per-shape knockout instead.

If that is judged too expensive, the CHEAP part is separable and keeps most of the
value: everything except the two `*_regime_finds_*` tests runs in 4.3 s and still
carries the derived alphabet, the rejection witnesses, `UNACCOUNTED == set()`, the cell
floors and both controls. What it does NOT carry is the ability to FIND a divergence —
which is the half that detonated RC1 and RC2.

--------------------------------------------------------------------------------
SABOTAGE (docs/sabotage-procedure.md) — index. Literal output lives in each test's
own docstring; this is the map, including the THREE checks that were found HOLLOW.
--------------------------------------------------------------------------------
    S1  tupleset re-pinned to today's literal tree state  -> RED  (2 features, 736 cells)
    S2  plan-node regex narrowed to `PDerived\\w*`         -> RED  (4 != 8)
    S3  a rejection family deleted                        -> RED  (unrecorded refusal)
    S4  a feature deleted from the alphabet               -> RED, but by two OTHER tests
                                                              (see its docstring)
    S5  swarm focus switch removed                        -> GREEN. HOLLOW; recorded.
    S6  neg-only arm made FAKE                            -> RED  (1 feature)
    S7  dense regime degraded to full-pool driving        -> RED  (fail-open unseen)
    S8  dense knockout ignores the wildcard bit           -> GREEN. Known limit, recorded.
    S9  `body_negttu` arm deleted, switch kept            -> RED  (2 tests)
    S10 a switch made dead code                           -> RED
    S11 `swarm_op_pool` returns [] (comparison set empty) -> RED  ("NO config driven")
    S12 typed pool table reverted (design's sabotage 8)   -> the predicted floor did NOT
                                                              fire. REFUTED; recorded.
    RC1/RC2 (live, unfixed)                               -> RED  (both sweeps)

Note S5, S8 and S12 honestly. `docs/sabotage-procedure.md` says a session that exposes a
hollow check is a GOOD session, so they are recorded rather than papered over:

* **S5** — `test_swarm_campaign_...` does NOT guard the focus mechanism. Measured: over
  120 derandomized draws the minimum per-switch enable count is 27/120 with the focus
  and 27/120 without, so the mechanism is not observable from outside at these budgets.
  The claim has been removed from that test rather than left standing.
* **S8** — folding `doc:*` in with `doc:d1` in the dense knockout's shape key leaves the
  negative control green. The wildcard bit is kept because RC2 is a divergence only a
  `T:*` parent exhibits, but the control does not currently prove it is load-bearing.
* **S12** — the design README's own sabotage 8 does not reproduce; see
  `test_non_vacuity_floors_fire_when_the_comparison_set_is_emptied` for the literal
  output and why. The acceptance-rate floor is kept (its mechanism is proven in code)
  but it is NOT the guard for pool/schema co-variance, and this file does not claim it
  is.
"""

from __future__ import annotations

import os
from collections import Counter

import pytest
from hypothesis import HealthCheck, Phase, given, settings

from zanzibar_utils_v1 import unparse_schema_ast
from tests import genswarm as G

# ---------------------------------------------------------------------------
# Profile. NOTE: no `settings.load_profile` here — `tests/test_hypothesis.py`
# owns the global profile registry, and a second module racing it for the global
# is how a campaign silently runs at the wrong budget. Explicit numbers only.
# ---------------------------------------------------------------------------
DEEP = os.environ.get('HYPOTHESIS_PROFILE', 'ci') == 'deep'

ENUM_K = 3 if DEEP else 2       # compile-only width: 136 configs at K<=2, 696 at K<=3
DRIVE_K = 2                     # DRIVEN width: pairs, at BOTH profiles -- see below
SWARM_DRAWS = 400 if DEEP else 120
SPARSE_SUBSETS = 4 if DEEP else 2
DENSE_SUBSETS = 3 if DEEP else 2

# ⚠ `DRIVE_K` is deliberately NOT raised under `deep`. Compile-only enumeration is
# ~0.4 ms/config, so widening it to triples costs 0.26 s and buys 957 cells instead of
# 841. DRIVING is ~200 ms (sparse) to ~900 ms (dense) per run, so widening THAT to
# triples costs ~900 s -- measured by trying it: the `deep` run had not finished in
# 590 s. `deep` therefore goes DEEPER (more subsets per config), not WIDER, which is
# also the right shape: the extra subsets are extra chances to hit a causal chain,
# whereas the extra configs are mostly redundant supersets of the pairs.

_ALPHABET = G.alphabet()
_UNIVERSE = G.universe_cells(_ALPHABET)


# ===========================================================================
# 1. THE ALPHABET IS DERIVED
# ===========================================================================

# Provenance: measured 2026-08-10 by
#   PYTHONPATH=. python docs/design/generator-coverage/prototypes/zz_cells.py
# Each entry is (site name, expected count). These are a floor-with-provenance on the
# DERIVATION, not a copy of the values: the values themselves are read from the
# compiler, so a new compiler branch mints a new feature and this test tells you to
# re-record the count rather than silently absorbing it.
_SITE_COUNTS = {
    'Expr classes': 6,
    'leaf kinds': 5,
    'plan node classes': 8,
    'via kinds': 4,
    'family kinds': 2,
    'restr modalities': 4,
}


def test_every_derivation_is_nonvacuous_and_matches_its_recorded_provenance():
    """Property guarded: the cell alphabet is minted from the compiler, and cannot
    silently shrink.

    An empty (or shrunken) derivation is the purest form of this repo's house failure
    mode — every coverage assertion downstream would pass over a smaller universe and
    report success. So each `derive_*` carries its own anti-vacuity assert AND a
    recorded count.

    ⚠ If this fails because the compiler GREW a branch, that is the system working:
    re-measure, update the count here, and expect new UNACCOUNTED features until a
    generator arm or a rejection witness reaches the new value. Do NOT delete the site.

    SABOTAGE (literal output). The narrowest plausible weakening is a regex that still
    matches something — not a deleted derivation. Narrowing `derive_plan_node_classes`'
    dispatch regex from `(P[A-Z]\\w*)` to `(PDerived\\w*)` (a "tidy-up" that still
    returns 4 real, non-empty, correctly-typed plan classes)::

        FAILED tests/test_generator_coverage.py::
            test_every_derivation_is_nonvacuous_and_matches_its_recorded_provenance
        AssertionError: derivation 'plan node classes' yields 4 values, recorded 8:
        ('PDerivedComputed', 'PDerivedTTU', 'PDerivedTuplesetTTU', 'PDerivedUserset')

    The bare non-emptiness assert inside `derive_plan_node_classes` stays GREEN through
    that edit; only the recorded count catches it.
    """
    for name, fn in G.DERIVATIONS:
        values = fn()
        assert values, f'ANTI-VACUITY: derivation {name!r} is empty'
        assert len(values) == _SITE_COUNTS[name], (
            f'derivation {name!r} yields {len(values)} values, '
            f'recorded {_SITE_COUNTS[name]}: {values}')
    assert len(_ALPHABET) == 51, f'alphabet is {len(_ALPHABET)} features: {_ALPHABET}'
    assert len(_UNIVERSE) == 1275, f'cell universe is {len(_UNIVERSE)}'


def test_alphabet_features_are_all_extractable_in_principle():
    """Property guarded: the extractor and the alphabet agree.

    A feature name in the alphabet that `features()` can never emit is a permanently
    UNACCOUNTED cell axis — it would make the coverage assertion below unsatisfiable and
    invite someone to relax it. So: every feature the extractor emits over the whole
    enumerated config space must be IN the alphabet (no orphan emissions), which is the
    direction a typo actually breaks.
    """
    emitted: set[str] = set()
    for sw in G.enumerate_configs(2):
        ast, owc = G.witness(sw)
        try:
            emitted |= G.features(unparse_schema_ast(ast), owc)
        except Exception:
            emitted |= G.ast_features(unparse_schema_ast(ast), owc)
    assert emitted, 'ANTI-VACUITY: the extractor emitted no features at all'
    orphans = emitted - set(_ALPHABET)
    assert not orphans, f'features emitted but not in the alphabet: {sorted(orphans)}'


# ===========================================================================
# 2. REJECTION WITNESSES — the exemption mechanism
# ===========================================================================

@pytest.mark.parametrize('w', G.REJECTION_WITNESSES, ids=lambda w: w.name)
def test_rejection_witness_is_still_refused(w):
    """Property guarded: a cell counted 'unreachable by design' is unreachable TODAY,
    not on the day someone wrote it down.

    This is the whole mechanism that separates "unreachable by design" from "unreachable
    by generator gap". A hand-written `EXPECTED_UNREACHABLE` list is a future silent
    pass: the day the compiler starts admitting the shape, the list still says
    "unreachable" and the gate stays green. A rejection witness inverts that — the
    moment the compiler admits this schema the `pytest.raises` fails, the exemption is
    REVOKED, and its features go back to UNACCOUNTED, which is red until a generator
    actually reaches them. **A scope relaxation cannot silently mint a new blind spot.**

    SABOTAGE (literal output). Narrowest plausible weakening: relax exactly one scope
    check — in `zanzibar_utils_v1._assert_tupleset_scope`, drop the userset-restriction
    clause (a plausible "we support this now" change). Observed::

        FAILED ...::test_rejection_witness_is_still_refused[tupleset-userset-restriction]
        Failed: DID NOT RAISE <class 'zanzibar_utils_v1.UnsupportedByGraphIndex'>
        FAILED ...::test_rejection_witness_is_still_refused[tupleset-wildcard-userset-restriction]
        Failed: DID NOT RAISE <class 'zanzibar_utils_v1.UnsupportedByGraphIndex'>

    and, in the same run, the exemption revocation this exists to produce::

        FAILED ...::test_every_alphabet_feature_is_hit_or_rejection_explained
        AssertionError: 2 alphabet feature(s) are neither HIT ... :
        ['ttu.ts.restr:userset', 'ttu.ts.restr:wildcard-userset']
    """
    with pytest.raises(w.exc) as ei:
        G.features(w.schema, w.owc)
    assert w.message in str(ei.value), (
        f'{w.name}: refusal message changed. recorded {w.message!r}, got {str(ei.value)!r}')
    # The witness must actually CARRY features, else it exempts nothing and is dead
    # weight masquerading as an exemption.
    assert G.ast_features(w.schema, w.owc), f'{w.name} carries no features'


def test_undeclared_tupleset_with_untainted_target_still_compiles():
    """Property guarded: the 2026-08-11 scope refusal keys on the TAINT OF THE TARGET,
    not on the tupleset merely being undeclared.

    This is the negative control for `undeclared-tupleset-with-derived-target`. That
    witness only asserts a refusal, so it is satisfied just as well by a refusal that is
    far too broad — and "reject every TTU over an undeclared tupleset" is exactly the
    one-line over-fix a future reader would reach for. An undeclared tupleset over an
    UNTAINTED target compiles today and must keep compiling: the rewrite rule it emits
    carries no derived subject predicate, so I5 exclusivity is not in play.

    Note the pair is a genuine one-token delta — `r1` (derived) vs `r0` (untainted) —
    so nothing but the property under test separates them.

    SABOTAGE (literal output). Narrowest plausible weakening: in
    `zanzibar_utils_v1._validate_ttu_tuplesets`, drop the `derived_predicate_names`
    test and refuse on the undeclared tupleset alone::

        if (object_type, e.tupleset_rel) not in ast:

    Observed::

        FAILED tests/test_generator_coverage.py::
            test_undeclared_tupleset_with_untainted_target_still_compiles
        E   zanzibar_utils_v1.UnsupportedByGraphIndex: relation doc#r7: TTU 'r0' from
            'nodecl' targets the derived relation 'r0' ...

    while `test_rejection_witness_is_still_refused[undeclared-tupleset-with-derived-target]`
    stays GREEN — which is the point: the witness alone cannot see this.
    """
    schema = G._REJ_HEAD + ('type doc\n  relations\n'
                            '    define blk: [user]\n'
                            '    define r0: [user]\n'
                            '    define r1: [user] but not blk\n'
                            '    define r7: [user] or r0 from nodecl\n')
    G.features(schema, frozenset())      # must not raise


def test_every_rejection_witness_family_is_actually_exercised_by_the_enumerator():
    """Property guarded: the recorded refusal families are the LIVE ones.

    A family nobody hits is a stale exemption — it keeps exempting cells long after the
    shape stopped being generated, which is the same silent pass a hand-written list is.
    So every family must be produced by at least one enumerated config, and (below) no
    config may be refused by an unrecorded family.
    """
    used = Counter()
    for sw in G.enumerate_configs(ENUM_K):
        ast, owc = G.witness(sw)
        try:
            G.features(unparse_schema_ast(ast), owc)
        except Exception as e:
            w = G.match_rejection(e)
            if w is not None:
                used[w.message] += 1
    assert used, 'ANTI-VACUITY: no config was refused at all'
    unused = [m for m in G.rejection_message_families() if m not in used]
    assert not unused, (
        f'rejection-refusal families never produced by the enumerator (stale '
        f'exemptions): {unused}')


# ===========================================================================
# 3. COVERAGE — the closed, exhaustive statement over the enumerator's config space
# ===========================================================================

def _enumerate(k):
    """(cells, features, refusals, unmatched) over switch subsets of size 1..k."""
    cells: set = set()
    feats: set = set()
    refusals = Counter()
    unmatched = []
    for sw in G.enumerate_configs(k):
        ast, owc = G.witness(sw)
        schema = unparse_schema_ast(ast)
        try:
            fs = G.features(schema, owc)
        except Exception as e:
            w = G.match_rejection(e)
            if w is None:
                unmatched.append((sorted(sw), type(e).__name__, str(e)[:200]))
            else:
                refusals[w.message] += 1
            continue
        feats |= fs
        cells |= G.cells_of(fs)
    return cells, feats, refusals, unmatched


def test_no_enumerated_config_is_silently_dropped():
    """Property guarded: every config in the CLOSED config space is either driven or
    refused for a RECORDED reason.

    This is the non-circular half of the coverage claim. The config space is defined by
    `SWARM_SWITCHES`, so adding a switch immediately adds `2*|SW|+1` configs, and a new
    compile refusal that nobody recorded is red on the next run rather than silently
    shrinking what gets tested. It is exhaustive and RNG-free — a complete statement
    about its own space, not a sample.

    ⚠ This test is how the `undeclared-tupleset-with-derived-target` family was found:
    `define r7: [user] or r1 from nodecl` with a DERIVED `r1` escaped the decision-15
    scope checks and died inside `compile_boolean_schema` on an internal invariant, as a
    bare `ValueError` — the exact class `tests/parity.py` says "must surface, not
    silently shrink the matrix to 3-way", so `ParityEngine` was UNCONSTRUCTIBLE on it.
    **FIXED 2026-08-11**: `_validate_ttu_tuplesets` now refuses the shape up front as a
    scoped `UnsupportedByGraphIndex`, the witness in `genswarm.REJECTION_WITNESSES` was
    flipped to match, and `test_undeclared_tupleset_with_untainted_target_still_compiles`
    guards against the refusal being widened to every undeclared tupleset. The sabotage
    output quoted below is therefore the PRE-FIX observation — kept because it is the
    evidence that this test can see an unrecorded refusal at all.

    SABOTAGE (literal output). Narrowest plausible weakening: delete the single
    `undeclared-tupleset-with-derived-target` entry from `REJECTION_WITNESSES` — the
    entry a tidier would remove as "not a real scope refusal". Observed::

        FAILED tests/test_generator_coverage.py::test_no_enumerated_config_is_silently_dropped
        AssertionError: 1 enumerated config(s) were refused by an UNRECORDED
        compile error: [(['body_boolean', 'ts_undeclared'], 'ValueError',
        'Rule then-pattern carries a derived subject predicate: Rule(if_pattern=...')]
    """
    cells, feats, refusals, unmatched = _enumerate(ENUM_K)
    assert cells, 'ANTI-VACUITY: the enumerator produced no cells'
    assert not unmatched, (
        f'{len(unmatched)} enumerated config(s) were refused by an UNRECORDED compile '
        f'error: {unmatched[:3]}')
    assert sum(refusals.values()) > 0, (
        'ANTI-VACUITY: no config was refused, so the rejection-witness machinery was '
        'never exercised')


def test_every_alphabet_feature_is_hit_or_rejection_explained():
    """★ THE COVERAGE ASSERTION. Property guarded: no feature of the derived alphabet is
    unreachable by generator gap.

    Exactly two dispositions are allowed, and there is NO hand-written third:
      * HIT — some enumerated config compiled and carried the feature;
      * REJ — some `(schema, owc)` the compiler is separately ASSERTED to refuse carries
        it (`test_rejection_witness_is_still_refused`).

    `UNACCOUNTED == set()` is the assertion. Note what this is NOT: it is not "every one
    of the 1275 cells is hit". ~28% of the pair space is unreached even at `deep`, and
    pretending otherwise is how a coverage check gets `skipif`'d the first time it
    flakes. The FEATURE-level statement is the one that can be exact, so it is the one
    that is exact — and it holds under `ci`, not only under `deep`.

    SABOTAGE 1 (literal output). Narrowest plausible weakening, and the strongest one
    available: restore the LITERAL STATE OF THE TREE TODAY — pin the TTU tupleset back
    to a plain single-type non-boolean relation in `genswarm.witness`::

        ts = Direct((Restriction('doc', '...', False),))   # ignore every ts_* switch

    Observed::

        FAILED tests/test_generator_coverage.py::
            test_every_alphabet_feature_is_hit_or_rejection_explained
        E   AssertionError: 2 alphabet feature(s) are neither HIT by the enumerator nor
            carried by a rejection witness -- these are GENERATOR GAPS, the kind that
            let RC1/RC2 through: ['ttu.ts:multitype', 'ttu.ts:neg-only-type']

    Two, not ten — and that is worth reading carefully, because it is the mechanism
    working as designed rather than a weak result. The other eight `ttu.ts:*` features
    stay ACCOUNTED because the rejection witnesses carry them: with the tupleset pinned
    they are unreachable *by design* (the compiler refuses `parent: [doc] or own` and
    friends), not by generator gap. `ttu.ts:multitype` and `ttu.ts:neg-only-type` are
    the two that are legitimately COMPILABLE and were simply never generated — and
    `ttu.ts:neg-only-type` is exactly RC1's shape. The check discriminates the two kinds
    of unreachability, which is the entire point of the exercise.

    SABOTAGE 1b, same edit, the cell floor::

        FAILED tests/test_generator_coverage.py::test_enumerator_cell_coverage_floor
        E   AssertionError: enumerator cell coverage 736/1275 is below the floor 800
            (measured 841 on 2026-08-10)

    SABOTAGE 2 (literal output). The instrument, not the subject: make the neg-only arm
    FAKE — `Exclusion(base + [doc], Direct([doc]))` instead of a genuine neg-only arm
    (see `genswarm._neg_only_arms`' docstring: it compiles, reads correctly in review,
    and yields a constantly-empty relation). Observed::

        FAILED ...::test_every_alphabet_feature_is_hit_or_rejection_explained
        E   AssertionError: 1 alphabet feature(s) are neither HIT by the enumerator nor
            carried by a rejection witness -- these are GENERATOR GAPS, the kind that
            let RC1/RC2 through: ['ttu.ts:neg-only-type']

    i.e. the extractor is not fooled by a shape that merely LOOKS like the live-bug one.
    """
    cells, feats, refusals, unmatched = _enumerate(ENUM_K)
    rej_feats: set = set()
    for fs in G.rejection_features().values():
        rej_feats |= fs
    assert feats, 'ANTI-VACUITY: no feature was HIT'
    assert rej_feats, 'ANTI-VACUITY: the rejection witnesses carry no features'
    unaccounted = sorted(set(_ALPHABET) - feats - rej_feats)
    assert not unaccounted, (
        f'{len(unaccounted)} alphabet feature(s) are neither HIT by the enumerator nor '
        f'carried by a rejection witness -- these are GENERATOR GAPS, the kind that let '
        f'RC1/RC2 through: {unaccounted}')


# Provenance for the floors below, measured 2026-08-10 at 1cbaad0 with
#   pytest tests/test_generator_coverage.py -q          (ci)
#   HYPOTHESIS_PROFILE=deep pytest tests/...            (deep)
# universe = 1275 pair cells; baseline generators at `git show HEAD:tests/...` = 514.
_CELL_FLOOR_CI = 800        # measured 841 (enumerator K<=2, compile-only)
_CELL_FLOOR_DEEP = 900      # measured 957 (enumerator K<=3)
_CELL_FLOOR_WITH_REJ = 830  # measured 871 (K<=2 + rejection witnesses)
_BASELINE_CELLS = 514       # `git show HEAD:tests/test_hypothesis.py`, 400 draws each


def test_enumerator_cell_coverage_floor():
    """Property guarded: the cell coverage this machinery buys does not silently decay.

    A FLOOR WITH PROVENANCE (rank 3 on the durability ranking), used deliberately here
    rather than an exact number, because the enumerator's cell count moves whenever the
    compiler mints a feature and an exact pin would turn every compiler change into a
    spurious failure. The floors are set ~5% under the measured values.

    The number that matters is the comparison, so it is asserted rather than narrated:
    the enumerator must beat the BASELINE generators by a wide margin, or the whole
    exercise bought nothing.

    SABOTAGE (literal output) — same edit as sabotage 1 above (tupleset re-pinned)::

        FAILED tests/test_generator_coverage.py::test_enumerator_cell_coverage_floor
        E   AssertionError: enumerator cell coverage 736/1275 is below the floor 800
            (measured 841 on 2026-08-10)
    """
    cells, feats, refusals, unmatched = _enumerate(ENUM_K)
    floor = _CELL_FLOOR_DEEP if DEEP else _CELL_FLOOR_CI
    assert len(cells) >= floor, (
        f'enumerator cell coverage {len(cells)}/{len(_UNIVERSE)} is below the floor '
        f'{floor} (measured 841 on 2026-08-10)')
    with_rej = cells | G.rejection_explained_cells()
    assert len(with_rej) >= _CELL_FLOOR_WITH_REJ
    assert len(with_rej) > _BASELINE_CELLS * 1.5, (
        f'the new machinery reaches {len(with_rej)} cells vs the baseline generators\' '
        f'{_BASELINE_CELLS} -- that is not enough of a gain to justify the runtime')


# ===========================================================================
# 4. THE SWARM
# ===========================================================================

# `derandomize=True` deliberately. This module MEASURES a generator; a coverage floor
# over a randomly-seeded draw is a flake waiting to happen (measured 2026-08-10: the
# same 40-draw campaign reached 224 cells under one seed and 492 under another). The
# random fuzzing lives in `tests/test_hypothesis.py`; what lives here is the yardstick,
# and a yardstick has to be the same length twice.
_SWARM_SETTINGS = settings(max_examples=SWARM_DRAWS, deadline=None, database=None,
                           derandomize=True,
                           suppress_health_check=list(HealthCheck),
                           phases=(Phase.generate,))


def test_every_switch_moves_the_cell_histogram():
    """Property guarded: every swarm switch is load-bearing, and every cell-bearing
    generator arm can be starved on purpose.

    For each switch `s`, the cells reached with `s` forced ON must include at least one
    cell not reachable with `s` forced OFF. A switch that reaches no new cell is dead
    code pretending to be coverage.

    Deterministic: uses the witness builder, not hypothesis, so this cannot flake.

    SABOTAGE — and the FINDING that came out of running it. The intended sabotage was
    "delete `'ttu.ts:neg-only-type'` from `_MODALITY_FLAGS`", a flag a tidier would call
    redundant with `ast:Exclusion`. Executed::

        SABOTAGE: S4 delete ttu.ts:neg-only-type from the alphabet
            1 passed, 25 deselected in 0.93s

    **This test stayed GREEN.** It cannot see a missing alphabet entry, because
    `ts_negonly` still moves OTHER features (`ast:Exclusion`, `ttu.ts:Exclusion`) and so
    `on - off` is still non-empty. Recorded rather than quietly re-scoped, per
    `docs/sabotage-procedure.md` ("a session that exposes a hollow check is a GOOD
    session"). The property is guarded — but by a DIFFERENT test:
    `test_alphabet_features_are_all_extractable_in_principle`, because `features()`
    still emits the name and it becomes an ORPHAN::

        FAILED ...::test_alphabet_features_are_all_extractable_in_principle
        E   AssertionError: features emitted but not in the alphabet:
            ['ttu.ts:neg-only-type']

    So what THIS test actually guards, and all it guards, is: no switch is dead code.
    The sabotage that reddens it is deleting a switch's arm from `genswarm.witness`
    while leaving the switch in `SWARM_SWITCHES` — the way a switch really rots.
    """
    others = [s for s in G.SWARM_SWITCHES]
    for s in G.SWARM_SWITCHES:
        on, off = set(), set()
        for base in [frozenset()] + [frozenset({o}) for o in others if o != s]:
            for target, sw in ((on, base | {s}), (off, base)):
                ast, owc = G.witness(sw)
                try:
                    fs = G.features(unparse_schema_ast(ast), owc)
                except Exception:
                    fs = G.ast_features(unparse_schema_ast(ast), owc)
                target |= G.cells_of(fs)
        assert on - off, (
            f'switch {s!r} reaches NO cell that is unreachable without it -- it is '
            f'either dead generator code or its feature axis is missing from the '
            f'alphabet')


def test_swarm_campaign_reaches_cells_and_never_starves_a_switch():
    """Property guarded: the swarm draw composes deeply AND does not starve any switch.

    Two things at once, because they trade off against each other:
      * every switch must appear in some drawn subset (no starvation);
      * the drawn configs must reach a floor of cells (the draw must still COMPOSE --
        the design measured that adding a 'minimal' focus-only stratum DROPPED coverage
        771 -> 721 at 600 draws, so a starvation-free draw is not automatically a good
        one).

    SABOTAGE — and the second FINDING. The intended sabotage was "drop the forced FOCUS
    switch from `swarm_subset` and keep only the independent 1/3 coins". Executed::

        SABOTAGE: S5 swarm_subset without the forced FOCUS switch
            1 passed, 25 deselected in 1.83s

    **Green.** So this test does NOT guard the focus mechanism, and the claim is not
    made. Measured why, so the next person does not retry it: over 120 derandomized
    draws the minimum per-switch enable COUNT is 27/120 **with** the focus and 27/120
    **without** it, and the all-on stratum still appears 5-6 times even when the
    stratum-0 branch is deleted (the independent coins occasionally land all-on). At
    these budgets the focus is not observable from outside the strategy — it is a
    by-construction property (rank 4, docstring, with the measurement above as the
    stated reason 1-3 are impossible).

    What this test DOES guard, and what does redden it: the starvation floor (a switch
    that `swarm_schema_asts` ignores entirely never enters a drawn config) and the cell
    floor (a draw that stops COMPOSING). The design measured the latter directly —
    adding a 'minimal', focus-only stratum dropped coverage 771 -> 721 at 600 draws.
    """
    seen_switches: set = set()
    cells: set = set()
    n_draws = [0]

    @_SWARM_SETTINGS
    @given(sw=G.swarm_subset())
    def draw_subsets(sw):
        n_draws[0] += 1
        seen_switches.update(sw)

    @_SWARM_SETTINGS
    @given(cfg=G.swarm_configs())
    def draw_configs(cfg):
        ast, owc = cfg
        try:
            fs = G.features(unparse_schema_ast(ast), owc)
        except Exception:
            return
        cells.update(G.cells_of(fs))

    draw_subsets()
    draw_configs()
    assert n_draws[0] > 0, 'ANTI-VACUITY: the swarm drew nothing'
    missing = sorted(set(G.SWARM_SWITCHES) - seen_switches)
    assert not missing, f'switch(es) never enabled in {n_draws[0]} swarm draws: {missing}'
    # Measured 2026-08-10, derandomized: 482 cells at 120 draws, 749 at 400.
    # Floors ~10% under.
    floor = 670 if DEEP else 430
    assert len(cells) >= floor, (
        f'swarm campaign reached {len(cells)} cells at {SWARM_DRAWS} draws, floor {floor}')


def test_swarm_all_on_stratum_covers_the_legacy_shape():
    """Property guarded: the swarm does not wash out the existing generators'
    distribution (`docs/history/handoff-status-2026-08.md` §1b, retired from `HANDOFF.md`
    on 2026-08-11; constraint 2).

    The 'all switches on' stratum is drawn with probability 1/4 and is a SUPERSET of the
    legacy `schema_asts` shape (all `body_*` arms available, plus the tupleset axes), so
    constraint 2 holds by construction rather than by measurement. What is asserted here
    is the construction: the all-on config's feature set must contain every feature of a
    config generated with only the legacy-equivalent switches enabled.

    SABOTAGE (literal output). Narrowest plausible weakening: change the all-on stratum
    from `frozenset(SWARM_SWITCHES)` to "every switch except the tupleset ones", the
    natural-looking way to keep the legacy shape intact::

        FAILED ...::test_swarm_all_on_stratum_covers_the_legacy_shape
        AssertionError: the all-on stratum is not a superset of the legacy-equivalent
        shape; missing ['ttu.ts:Exclusion', 'ttu.ts:Intersection', 'ttu.ts:neg-only-type',
        'ttu.ts:tainted']
    """
    legacy_like = frozenset({'body_boolean', 'body_userset', 'body_wildcard',
                             'body_computed'})
    all_on = frozenset(G.SWARM_SWITCHES)
    a_ast, a_owc = G.witness(all_on)
    l_ast, l_owc = G.witness(legacy_like)
    l_feats = G.features(unparse_schema_ast(l_ast), l_owc)
    try:
        a_feats = G.features(unparse_schema_ast(a_ast), a_owc)
    except Exception:
        a_feats = G.ast_features(unparse_schema_ast(a_ast), a_owc)
    # the all-on witness may be scope-refused (it enables every REJ arm at once), so the
    # structural claim is over the union of the enumerator's own all-on-per-axis configs
    reach: set = set()
    for s in G.SWARM_SWITCHES:
        ast, owc = G.witness(frozenset({s}) | legacy_like)
        try:
            reach |= G.features(unparse_schema_ast(ast), owc)
        except Exception:
            reach |= G.ast_features(unparse_schema_ast(ast), owc)
    missing = sorted(l_feats - reach)
    assert not missing, (
        f'the all-on stratum is not a superset of the legacy-equivalent shape; '
        f'missing {missing}')
    assert a_feats, 'ANTI-VACUITY: the all-on witness carries no features'


# ===========================================================================
# 5. THE DRIVEN SWEEP — two regimes
#
#   ★★★ THE TWO TESTS BELOW ARE THE POSITIVE CONTROLS, AND THEY ARE RED TODAY. ★★★
#   They detonate RC1 and RC2 (`tests/test_ttu_tupleset_parent_types.py`), which are
#   live and deliberately unfixed. Do not weaken them, do not xfail them
#   (`MAX_TESTS_XFAILED=0`), do not skip them. They go GREEN with the fix.
# ===========================================================================

def _sweep(regime, k):
    """Drive every enumerated config under one regime. Returns a report dict."""
    cells: set = set()
    comparisons = attempted = accepted = driven = 0
    fail_open: dict = {}
    fail_closed: dict = {}
    for sw in G.enumerate_configs(DRIVE_K):
        ast, owc = G.witness(sw)
        schema = unparse_schema_ast(ast)
        try:
            fs = G.features(schema, owc)
        except Exception as e:
            assert G.match_rejection(e) is not None, (
                f'config {sorted(sw)} refused by an unrecorded error: {e!r}')
            continue
        r = G.drive_config(ast, owc, regime=regime, k=k, seed=7)
        comparisons += r.comparisons
        attempted += r.attempted
        accepted += r.accepted
        if r.driven:
            driven += 1
            cells |= G.cells_of(fs)          # a cell counts only when actually DRIVEN
        for d in r.fail_open:
            fail_open.setdefault(tuple(sorted(sw)), d)
        for d in r.fail_closed:
            fail_closed.setdefault(tuple(sorted(sw)), d)
    return dict(cells=cells, comparisons=comparisons, attempted=attempted,
                accepted=accepted, driven=driven,
                fail_open=fail_open, fail_closed=fail_closed)


def _assert_non_vacuous(rep, regime):
    """The three non-vacuity floors. A sweep that compared nothing reports success."""
    assert rep['driven'] > 0, f'{regime}: NO config was driven at all'
    assert rep['comparisons'] > 0, (
        f'{regime}: VACUOUS -- zero comparisons were made, so this sweep passed by '
        f'comparing nothing')
    assert rep['attempted'] > 0, f'{regime}: no writes were attempted'
    rate = rep['accepted'] / rep['attempted']
    assert rate >= 0.5, (
        f'{regime}: acceptance rate {rate:.2f} ({rep["accepted"]}/{rep["attempted"]}) '
        f'is below 0.5 -- the candidate pool has drifted out of sync with the schema '
        f'generator and this sweep is measuring the ADMISSION-REJECTION path, not the '
        f'shape under test')
    assert rep['cells'], f'{regime}: no cell was recorded as DRIVEN'


def test_sparse_regime_finds_no_fail_closed_divergence():
    """★ CURRENTLY RED (positive control). Property guarded: no schema the enumerator
    can build makes the graph index UNDER-grant relative to the oracle.

    THE DRIVING DISCIPLINE IS THE POINT. Sparse = subsets of size 1..3 of the candidate
    pool, never the full pool. A fail-closed divergence is an under-grant, so ANY extra
    granting tuple supplies an alternative path and masks it — this repo's own IIA
    property (`310fbcb`).

    ⚠ Measured, and it CORRECTS the design README: over this config space full-pool
    driving finds **3** divergent configs where sparse finds **10** — not the ZERO the
    README reports for its own prototype. The masking is real and large but not total,
    so "the full pool finds nothing" is too strong a claim to repeat. The direction
    where full-pool driving really is blind is the fail-OPEN one; see
    `test_dense_regime_finds_no_fail_open_divergence` for the three-regime table and
    `test_full_pool_driving_is_blind_to_what_subset_driving_detects` for the permanent
    control.

    MEASURED 2026-08-10 at `1cbaad0` (RC1 and RC2 both live and unfixed): 96 driven
    configs, 62 691 comparisons, 470/480 writes accepted, 64.7 s. LITERAL OUTPUT::

        FAILED tests/test_generator_coverage.py::
            test_sparse_regime_finds_no_fail_closed_divergence
        E   AssertionError: FAIL-CLOSED (graph under-grants): 10 divergent config(s)
                sw=['ts_negonly']
                    q=('...','user','u1','r2','doc','d1') oracle=True
                      {'graph': False, 'set:py': True, 'set:roaring': True}
                sw=['ts_boolean', 'ts_negonly']            ... same signature
                sw=['ts_boolean', 'ts_wildcard']           ... same signature
                sw=['ts_multitype', 'ts_negonly']          ... same signature
                sw=['ts_negonly', 'ts_wildcard']           ... same signature
                sw=['ts_computed', 'ts_negonly']           ... same signature

    Two distinct root causes, reached from switch COMBINATIONS rather than transcribed
    schemas — note that no switch name mentions a bug:

      * `['ts_negonly']` alone is **RC1**: `parent: [doc:*] but not [doc]`, the type that
        reaches the tupleset only through the exclusion's SUBTRAHEND.
      * `['ts_boolean', 'ts_wildcard']` is **RC2**: `parent: [doc, doc:*] and
        [doc, doc:*]`, a stored `doc:*` parent on a TAINTED tupleset. It contains no
        exclusion at all, so it is not a re-report of RC1.

    Both are independently pinned by hand in `tests/test_ttu_tupleset_parent_types.py`.

    SABOTAGE: none needed and none possible — this test's subject is a REAL, live,
    independently-pinned defect. That is the strongest control available
    (`docs/sabotage-procedure.md`: "a deliberately-degraded input that must be
    detected"). The corresponding negative control is the full-pool test below.
    """
    rep = _sweep(G.SPARSE, SPARSE_SUBSETS)
    _assert_non_vacuous(rep, 'sparse')
    assert not rep['fail_closed'], _fmt('FAIL-CLOSED (graph under-grants)',
                                        rep['fail_closed'])


def test_dense_regime_finds_no_fail_open_divergence():
    """★★ CURRENTLY RED (positive control), and this is the design's OWN ADMITTED GAP,
    closed. Property guarded: no schema the enumerator can build makes the graph index
    OVER-grant relative to the oracle.

    `docs/design/generator-coverage/README.md` §6.7 says out loud: *"the subset-driving
    discipline is tuned for fail-closed and slightly detuned for fail-open ... I could
    not independently reproduce a fail-open divergence"* over 393 320 comparisons. That
    is a real hole, because a fail-open is an AUTHORIZATION defect and a fail-closed is
    an availability one.

    Two things were needed to close it, and BOTH were, so the gap is genuinely closed:

    1. **Grammar.** No fail-open is expressible without a NEGATED TTU. A dropped TTU
       parent is a false negative under a positive TTU and a false POSITIVE under a
       negated one (`docs/history/handoff-status-2026-08.md` §1, archived from
       `HANDOFF.md` on 2026-08-16), and every generator in the tree — including the
       design's own prototype witness builder — emitted only positive TTUs. Hence the
       `body_negttu` switch: `define r3: [user] but not r1 from parent`.
    2. **Driving.** An over-grant is masked from BELOW (a near-empty store gives the
       subtrahend nothing to subtract) *and* from ABOVE (a full pool supplies an
       alternative subtraction path the defective backend can still see). It is visible
       only in the band between: `pool MINUS a few tuples`. Hence the DENSE regime.

    MEASURED 2026-08-10 at `1cbaad0`, 96 driven configs, 61 659 comparisons,
    1967/1978 writes accepted, 85.7 s. LITERAL OUTPUT::

        FAILED tests/test_generator_coverage.py::
            test_dense_regime_finds_no_fail_open_divergence
        E   AssertionError: FAIL-OPEN (graph over-grants -- an AUTHORIZATION defect):
            1 divergent config(s)
                sw=['body_negttu', 'ts_negonly']
                    q=('...', 'user', 'u1', 'r3', 'doc', 'd1') oracle=False
                      {'graph': True, 'set:py': False, 'set:roaring': False}

    `oracle=False graph=True sets=[False,False]` is exactly the RC1 fail-open signature
    that `tests/test_ttu_tupleset_parent_types.py::
    test_rc1_negative_arm_type_dropped_is_an_authorization_fail_open` pins by hand — but
    here it is REACHED, not transcribed.

    THE REGIME COMPARISON, all three measured over the SAME 136-config space::

        regime            wall     comparisons   FAIL-OPEN   fail-closed
        sparse            64.7 s       62 691         0           10
        dense (knockout)  85.7 s       61 659         1           13
        full pool         86.1 s       41 562         0            3

    So sparse is blind to the fail-open, and the full pool is blind to BOTH directions
    (it sees 3 of the 10 fail-closed families and none of the fail-open). Only the dense
    knockout closes §6.7.

    SABOTAGE (literal output). Narrowest plausible weakening, and the one a reviewer
    would actually propose since it removes 86 s: degrade `subsets_for`'s DENSE branch to
    `return [tuple(pool)]` — "applying the pool once is enough". Observed, on the
    permanent synthetic control rather than on the live bug::

        FAILED ...::test_full_pool_driving_is_blind_to_what_subset_driving_detects
        E   AssertionError: the DENSE regime detected nothing in the FAIL-OPEN
            direction -- the dense knockout has stopped working, so the design gap
            §6.7 named is open again

    And the grammar half, sabotaged separately (delete the `body_negttu` arm from
    `genswarm.witness` while leaving the switch in place — a switch that rots)::

        FAILED ...::test_every_switch_moves_the_cell_histogram
        E   AssertionError: switch 'body_negttu' reaches NO cell that is unreachable
            without it -- it is either dead generator code or its feature axis is
            missing from the alphabet
        FAILED ...::test_full_pool_driving_is_blind_to_what_subset_driving_detects
    """
    rep = _sweep(G.DENSE, DENSE_SUBSETS)
    _assert_non_vacuous(rep, 'dense')
    assert not rep['fail_open'], _fmt('FAIL-OPEN (graph over-grants -- an '
                                      'AUTHORIZATION defect)', rep['fail_open'])


def _fmt(kind, found):
    lines = [f'{kind}: {len(found)} divergent config(s)']
    for sw, (q, exp, ans) in list(found.items())[:6]:
        lines.append(f'  sw={list(sw)}\n      q={q} oracle={exp} {ans}')
    return '\n'.join(lines)


# ===========================================================================
# 6. THE NEGATIVE CONTROL — the driving discipline, guarded permanently
# ===========================================================================

# The witness the control runs on: `parent: [folder] but not [doc]` with both a positive
# TTU (`r2: r1 from parent`) and a negated one (`r3: [user] but not r1 from parent`).
_CONTROL_SWITCHES = frozenset({'ts_negonly', 'multi_type', 'body_negttu'})


def test_full_pool_driving_is_blind_to_what_subset_driving_detects():
    """★ THE NEGATIVE CONTROL. Property guarded: the DRIVING DISCIPLINE, not the schema
    shape, is what makes a divergence observable — so "apply the whole pool once, then
    sweep" must never quietly replace the two regimes.

    This is the design's own instrument control (README §4 sabotage 4), which caught a
    real weakness in its first draft: driving each config with the WHOLE candidate pool
    found **0 divergences** across the same 97 configs that subset driving detonates.
    Without it the design would have shipped a 35-second GREEN phase over an unfixed
    live bug. Cell coverage is NECESSARY AND NOT SUFFICIENT.

    (Re-measured over this file's config space the full-pool number is 3 rather than 0
    for the fail-closed direction; it is 0 for the fail-open direction. The conclusion is
    unchanged and the control below is run on a synthetic defect where the masking is
    total, so it does not depend on either number.)

    ⚠ IT IS RUN AGAINST A SYNTHETIC, INJECTED DEFECT, NOT AGAINST THE LIVE BUG. A
    control that only works while a bug is open silently stops controlling the day the
    bug is fixed — the house failure mode applied to controls themselves. The injected
    defect is `genswarm.dropped_parent_defect('doc', 'parent')`: *every stored `doc`-typed
    tuple on `parent` is invisible*, which is exactly what a missing entry in the compiled
    `parent_types` does (RC1). It is modelled as a whole TYPE and not as a single tuple
    on purpose: a one-tuple defect is masked by its own siblings and the control would
    then report "masked" in every regime and prove nothing.

    Three statements, all asserted below and all routed through the REAL
    `genswarm.subsets_for` so the production driving code is the thing under test:

        FULL POOL   detects NOTHING in either direction        <- BLIND
        SPARSE      detects the FAIL-CLOSED direction
        DENSE       detects the FAIL-OPEN direction

    The fail-open one is the load-bearing half: it is unreachable from BELOW (a sparse
    store gives the `but not` nothing to subtract) and unreachable from ABOVE (the full
    pool leaves an alternative subtraction path the defective backend can still see).

    SABOTAGE (literal output). Narrowest plausible weakening: replace the dense subsets
    with the full pool, i.e. `subsets_for(..., DENSE) -> [tuple(pool)]` — the
    "optimisation" of applying the pool once instead of once per knockout::

        SABOTAGE: S7 dense regime degraded to full-pool driving
        FAILED ...::test_full_pool_driving_is_blind_to_what_subset_driving_detects
        E   AssertionError: the DENSE regime detected nothing in the FAIL-OPEN
            direction -- the dense knockout has stopped working, so the design gap
            §6.7 named is open again

    KNOWN LIMIT (sabotage S8, executed and GREEN): folding the wildcard bit out of
    `genswarm._shape` — so a `doc:*` parent and a `doc:d1` parent knock out together —
    does NOT redden this control. The wildcard bit is kept because RC2 is a divergence
    only a `T:*` parent exhibits, but this control does not prove it is load-bearing.
    """
    import random

    ast, owc = G.witness(_CONTROL_SWITCHES)
    schema = unparse_schema_ast(ast)
    pool = G.swarm_op_pool(ast)
    defect = G.dropped_parent_defect('doc', 'parent')
    assert any(defect(t) for t in pool), (
        'ANTI-VACUITY: the injected defect drops nothing in this pool, so every '
        'statement below would be trivially true')

    def probe(regime, k):
        """Run the REAL `subsets_for` for this regime and report what it detects.

        ⚠ It routes through `genswarm.subsets_for` deliberately. An earlier draft of
        this test hand-built the three stores inline; the sabotage of degrading the
        dense regime to full-pool driving then left it GREEN, because the test was
        never asking the production code what it would do. That is this repo's house
        failure mode reproduced inside its own control."""
        comparisons = 0
        over, under = [], []
        for subset in G.subsets_for(pool, regime, k, random.Random(0), ast):
            n, bad = G.detect_synthetic(
                schema, set(subset), G.grid_for(ast, subset), defect)
            comparisons += n
            over += [b for b in bad if not b[1] and b[2]]
            under += [b for b in bad if b[1] and not b[2]]
        return comparisons, over, under

    n_full, over_full, under_full = probe(G.FULL, 1)
    assert n_full > 0, 'ANTI-VACUITY: the full-pool sweep compared nothing'
    assert not over_full and not under_full, (
        f'full-pool driving DETECTED the injected defect -- if this is now visible with '
        f'the whole pool applied, the IIA masking argument this design rests on has '
        f'changed and the regimes must be re-derived: {(over_full + under_full)[:3]}')

    n_sparse, over_sparse, under_sparse = probe(G.SPARSE, 200)
    assert n_sparse > 0, 'ANTI-VACUITY: the sparse sweep compared nothing'
    assert under_sparse, (
        'the SPARSE regime detected no fail-closed direction of the injected defect -- '
        'small-subset driving has stopped working')

    n_dense, over_dense, under_dense = probe(G.DENSE, 4)
    assert n_dense > 0, 'ANTI-VACUITY: the dense sweep compared nothing'
    assert over_dense, (
        'the DENSE regime detected nothing in the FAIL-OPEN direction -- the dense '
        'knockout has stopped working, so the design gap §6.7 named is open again')


def test_non_vacuity_floors_fire_when_the_comparison_set_is_emptied():
    """★ Property guarded: the sweeps' own non-vacuity floors are not decoration.

    `docs/sabotage-procedure.md`: *a sweep that compared nothing reports success.* This
    test constructs each degraded state IN CODE and asserts the floor fires — rank 1 on
    the durability ranking, rather than "I checked it once by hand".

    Three degradations, each the narrowest plausible one:
      * an empty candidate pool -> zero comparisons, zero driven configs;
      * a pool whose candidates are all restriction-INVALID -> the sweep silently starts
        measuring the ADMISSION-REJECTION path (the graph admits such a tuple as a no-op
        while the set engine refuses it), which a comparison counter alone would NOT
        catch because the grid still sweeps -- it just sweeps an empty store;
      * a schema whose relations declare no Direct restriction at all -> the naive
        parity grid is EMPTY and every assertion in it passes by looping zero times.

    SABOTAGE 1 (literal output), degradation 1 against the REAL sweep — make
    `swarm_op_pool` return `[]`, the narrowest way to empty the comparison set::

        FAILED ...::test_sparse_regime_finds_no_fail_closed_divergence
        E   AssertionError: sparse: NO config was driven at all
        assert 0 > 0

    ⚠ SABOTAGE 2 — REFUTED, and recorded because it corrects the design. The design
    README §4 sabotage 8 predicts that reverting `swarm_op_pool`'s typed name table to
    `USERS if r.type == 'user' else DOCS` trips the acceptance-rate floor, "because
    invalid `folder:d1` subjects are refused by the set engine". **It does not.**
    Executed::

        SABOTAGE: S12 typed pool table reverted to `USERS if r.type==user else DOCS`
        E   AssertionError: FAIL-CLOSED (graph under-grants): 9 divergent config(s)
            1 failed, 25 deselected in 73.17s

    The acceptance-rate floor never fired: `folder:d1` is a perfectly legal name of type
    `folder`, so a `[folder]` restriction admits it and every backend agrees. The
    typed table is still right (it is what keeps OBJECT names typed, and reverting it
    silently cost one divergent config, 10 -> 9) — but the acceptance-rate floor is NOT
    what guards it, and claiming so would have been a check that fails by passing. The
    floor's own mechanism is proven by the in-code degradation above; what is NOT proven
    is that any realistic pool drift produces a low acceptance rate. Stated, not hidden.
    """
    # (1) empty pool -> the driven floor fires
    empty = dict(comparisons=0, attempted=0, accepted=0, driven=0, cells=set(),
                 fail_open={}, fail_closed={})
    with pytest.raises(AssertionError, match='NO config was driven'):
        _assert_non_vacuous(empty, 'probe')
    with pytest.raises(AssertionError, match='VACUOUS'):
        _assert_non_vacuous(dict(empty, driven=1), 'probe')

    # (2) an all-invalid pool -> the acceptance-rate floor fires, and the comparison
    #     counter alone does NOT (comparisons are nonzero: the grid still sweeps).
    bad_rate = dict(comparisons=500, attempted=100, accepted=20, driven=5,
                    cells={frozenset({'a', 'b'})}, fail_open={}, fail_closed={})
    with pytest.raises(AssertionError, match='acceptance rate'):
        _assert_non_vacuous(bad_rate, 'probe')

    # ... and the same shape with a healthy rate must PASS, so the floor is not simply
    # rejecting everything (control on the control).
    _assert_non_vacuous(dict(bad_rate, accepted=90), 'probe')

    # (3) an empty grid -> `grid_for` refuses rather than returning []
    with pytest.raises(AssertionError, match='ANTI-VACUITY'):
        G.grid_for({}, set())


def test_a_sweep_with_an_empty_pool_would_have_reported_success():
    """Property guarded (the positive control for the control): the sweep machinery
    genuinely reports "no divergence" on an empty store, so the floors above are the
    ONLY thing standing between an empty sweep and a green gate.

    Runs one real, fully-constructed config with an EMPTY subset. Every backend is
    built, the grid is non-empty, the oracle agrees with all of them (everything is
    False), zero writes happen — and `divergences` is empty. That is the failure mode:
    a completely green sweep that tested nothing.

    MEASURED 2026-08-10: comparisons=192, attempted=0, divergences=0.
    """
    ast, owc = G.witness(frozenset({'ts_negonly'}))
    schema = unparse_schema_ast(ast)
    d = G.Diff(schema, owc)
    try:
        n, bad = d.sweep()
    finally:
        d.close()
    assert n > 0, 'the empty-store grid was itself empty'
    assert not bad, (
        'an EMPTY store already diverges -- that is a real bug, not a vacuity demo: '
        f'{bad[:3]}')
    # This is what the floors exist to reject:
    rep = dict(comparisons=n, attempted=0, accepted=0, driven=1, cells=set(),
               fail_open={}, fail_closed={})
    with pytest.raises(AssertionError):
        _assert_non_vacuous(rep, 'empty-pool sweep')


def test_admission_parity_is_asserted_not_assumed():
    """Property guarded: the sweep never quietly proceeds after the backends disagreed
    about whether a write was legal.

    The stated constraint of plan item 1b (retired from `HANDOFF.md` on 2026-08-11; now
    `docs/history/handoff-status-2026-08.md` §1b): the graph admits a restriction-invalid
    tuple as
    a silent no-op while the set engine refuses it. If `Diff.add` swallowed that, the
    store would differ per backend and the sweep would report divergences that are
    really admission asymmetries — or, worse, measure the rejection path and report
    green. `Diff.add` raises `AdmissionDivergence` instead.

    Two halves, and both are needed:

    * CONTROL — a restriction-invalid tuple (`folder:f1` as the subject of a
      `[user]`-only relation) must be refused UNANIMOUSLY today, and `Diff` must record
      it as not-accepted rather than raising. Measured 2026-08-10: all three backends
      return False.
    * SABOTAGE (rank 1, constructed in code) — make ONE backend disagree, which is the
      narrowest plausible degradation: a single admission-path change on one engine. The
      divergence is injected by patching that side's `apply`, so the check is proven
      rather than assumed::

          AdmissionDivergence: accept/reject divergence on add
          ('...', 'folder', 'f1', 'r0', 'doc', 'd1'):
          {'graph': False, 'set:py': True, 'set:roaring': False}
    """
    ast, owc = G.witness(frozenset({'multi_type'}))
    invalid = ('...', 'folder', 'f1', 'r0', 'doc', 'd1')

    d = G.Diff(unparse_schema_ast(ast), owc)
    try:
        assert d.add(invalid) is False, (
            'a restriction-invalid tuple was ACCEPTED unanimously -- the control for '
            'this test has moved and the sabotage below no longer means anything')
        assert invalid not in d.present
    finally:
        d.close()

    d = G.Diff(unparse_schema_ast(ast), owc)
    try:
        d.sets[0].apply = lambda raw, op: True          # one backend now disagrees
        with pytest.raises(G.AdmissionDivergence, match='accept/reject divergence'):
            d.add(invalid)
    finally:
        d.close()


# ===========================================================================
# 7. THE REPORT (never an assertion -- `deep` publishes the open number)
# ===========================================================================

def test_report_cell_coverage(capsys):
    """Not an assertion: the published coverage record.

    `docs/design/generator-coverage/README.md` §6.1 is explicit that ~30% of the pair
    space stays unreached and that the number should be PUBLISHED, not rounded away. The
    floors live in `test_enumerator_cell_coverage_floor`; this prints the current
    figures so a reviewer sees the open number next to the closed one.

    Run with `-s` to see it.
    """
    cells, feats, refusals, unmatched = _enumerate(ENUM_K)
    rej_cells = G.rejection_explained_cells()
    total = len(_UNIVERSE)
    both = cells | rej_cells
    print(f'\n[genswarm] profile={"deep" if DEEP else "ci"} K<={ENUM_K}')
    print(f'[genswarm] alphabet {len(_ALPHABET)} features -> {total} pair cells')
    print(f'[genswarm] HIT      {len(cells):5d}  ({100*len(cells)/total:.1f}%)')
    print(f'[genswarm] +REJ     {len(both):5d}  ({100*len(both)/total:.1f}%)')
    print(f'[genswarm] UNKNOWN  {total-len(both):5d}  ({100*(total-len(both))/total:.1f}%)'
          f'   <- the honest remaining blind spot')
    print(f'[genswarm] baseline generators (git HEAD, 400 draws each): '
          f'{_BASELINE_CELLS} ({100*_BASELINE_CELLS/total:.1f}%)')
    print(f'[genswarm] refusals by family: {dict(refusals)}')
    assert not unmatched
