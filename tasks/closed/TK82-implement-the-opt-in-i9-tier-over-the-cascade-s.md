---
id: TK82
title: implement the opt-in I9 tier over the cascade's SCHEDULED-key union
brief: TK74's answer: per-cascade fixpoint check, default OFF; the union must come from the SCHEDULING side
pri: NOW
size: M
deps: []
related: [TK74]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-18b
moved: 2026-09-19
updated: 2026-09-19
closed: 2026-09-19
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-09-18c

UNBLOCKED AND SPECIFIED. The section 9.10 measurement round is done; the tier prerequisite (its false-positive rate on unmutated traffic) is CLOSED. Map: docs/tk74-staleness-net-2026-09-18.md section 10.3 (the doc is now FROZEN; read section 10 before anything above it).

THE NUMBERS (agent-measured, 8 seeds x 40 ops, the 9 fixtures that HAVE derived predicates):
  FP RATE = 0 / 2853 cascades, 3358 scheduled-union keys re-reconciled, bumped_grew=0
  CONTROL  : proposed tier raised on 43 / 43 genuinely-oracle-wrong arms
  SABOTAGE : reconciled-union tier raised on 0 / 43 of those same arms
So the design answer holds and nothing about false positives blocks shipping it.

(!) THE CONSTRAINT THAT CHANGES HOW THIS IS BUILT. On unmutated traffic the SCHEDULED union and the RECONCILED (dispatched) set are BYTE-IDENTICAL -- union_minus_dispatched = 0 and never_dispatched = 0 across 3744 clean cascades. The right design and the sabotaged design are therefore indistinguishable by ANY clean-traffic measurement: same cost, same FP rate, same union size. The scheduled-vs-reconciled choice can be justified ONLY by a fault-injection arm. So the sabotage is not a one-time check to run before landing -- it must ship as a PERMANENT test, or the next refactor silently swaps the union source and every benchmark stays green.

(!) TRAP -- do NOT write "the tier is a subset of audit_fixpoint". The per-cascade ratio of union size to audit_fixpoint scope EXCEEDS 1 (max 2.0 on four fixtures): the union is scheduled from deltas, so it can hold keys whose object has just gone dead and left _live_keys_of enumeration (:1671), which audit_fixpoint (:1732) would never visit. Aggregate ratio 0.242 over 1429 cascades, 2026-09-18c, on 40-op toy stores -- quote it only with that caveat. The durable claim stays REASONED: tier is O(cascade work), audit_fixpoint is O(live derived keys), unbounded by write size.

(!) INSTRUMENT CAVEAT. The measurement wrapped the PUBLIC run_cascade (:1544), so its re-reconciles ran OUTSIDE _node_cache_scope() + _stored_cache_scope(). That is the stronger question, but a tier shipped INSIDE those scopes is not what was measured -- RE-MEASURE if it lands inside them.

NO CONTROL COVERAGE on two fixtures; do not count them as passing: owc_star_ttu (1 stratum, so "non-final stratum" is empty by definition) and demorgans_law_1 (0 productive non-final-stratum reconciles in 16 ops).

SCOPE NOTE, from section 10.8: the settle pass is blind WITHIN the skipping cascade but catches skips opportunistically ACROSS cascades (8 of 2179 arms placed the key; the 1 genuinely stale one raised). That is a ~0.4% placement rate on fault-injected traffic -- it is not a net and does not reduce the case for this tier.

NEXT ACTION: implement it. Default OFF, union taken from the SCHEDULING side, per-cascade fixpoint check.

### 2026-09-19

IMPLEMENTED AND GATED-PENDING. Map: docs/tk82-cascade-fixpoint-tier-2026-09-19.md (now FROZEN).

WHAT LANDED. A fourth paranoia level, PARANOIA_FIXPOINT = 'fixpoint', appended ABOVE 'full'
in index_v4/invariants.py::PARANOIA_LEVELS, arming
index_v4/processor.py::DeltaProcessor._check_cascade_fixpoint once per cascade over the
SCHEDULED-key union collected by ::_tier_schedule. Verdict recorded on ::FixpointTier so a
test can see the tier RAN (reconcile is a repairing mutator; a post-hoc call cannot).
16 tests: tests/test_cascade_fixpoint_tier.py.

TWO DECISIONS THE SPEC LEFT OPEN, both taken here (doc sec 1 and sec 2):
 (1) LADDER PLACEMENT. The ladder is a TOTAL ORDER (_LEVEL_RANK enumerates PARANOIA_LEVELS,
     raise_to keeps the higher rank), so a tier placed BELOW 'full' would be implied by it --
     install_paranoia defaults to 'full' and make_wildcard_index to paranoia=True, so the
     whole suite would have started paying a doubled cascade. Placed ABOVE 'full'. Price,
     stated: an operator cannot buy the cascade tier without full's O(store) checker. Both
     are diagnosis tiers, so that is acceptable.
 (2) THE TIER RUNS OUTSIDE _node_cache_scope + _stored_cache_scope. Stronger question (no
     memo can mask a divergence), matches what sec 10.3 measured, and one call site covers
     all three of _run_cascade's normal exits. Bound: under advance_index an OUTER node-cache
     scope still spans it.

(!) A TRAP THE PLACEMENT CREATED, found and fixed in the same edit: ParanoiaGuard's listeners
branched on `level == PARANOIA_FULL`, so appending a rank above 'full' routed the STRONGEST
tier into the RESIDUE branch -- it would have shipped WEAKER than 'full'. Now rank-based via
::paranoia_at_least. Pinned behaviourally by ::test_fixpoint_tier_is_at_least_full (I13).

MEASURED FIRST-HAND, on shipped code:
 * detection 4/4 skips at non-final strata; the skip is genuinely oracle-wrong (4 of 49 grid
   queries, reaching the top stratum).
 * SABOTAGE (reconciled union) blind on the same arms, with a NON-EMPTY union -- shipped as a
   permanent test, per sec 10.3's finding that clean traffic cannot distinguish the designs.
 * FP sweep, whole tests/ tree with every 'full' store forced to 'fixpoint':
   tier_cascades=1612 keys_rereconciled=1912 tier_raises=5, and ALL FIVE attributed by nodeid
   to this module's own fault injection -> 0 false positives on 1607 unmutated cascades.
 * MUTATION SWEEP of the new module: 13 mutations, 12 RED, 1 INERT, M0 control attributing.
   Two INERT rows were not believed and earned new tests (the leftover half of the union, and
   the outside-the-cache-scopes placement); M12 stays INERT with its mechanism written down.
 * ZANZIBAR_PARANOIA=fixpoint arms it end to end through ConnectedStore (pinned).

(!) INSTRUMENT FINDING, and it reads exactly like a clean result: leaving the reconcile
suppression armed while the tier runs suppresses the tier's OWN re-reconcile, and all four
detection arms come back NO RAISE. A second form wrapped reconcile but not reconcile_subject,
which silently halves the injection.

FOUND IN PASSING AND FIXED: docs/architecture/verification.md and correctness.md both said
ConnectedStore never calls install_paranoia and exposes no flag, so production runs dark.
False since ZT-P1-3 -- store.py:193 installs it and __init__ takes paranoia=. Corrected.

STILL OWED (sec 8.8's rider, demoted by sec 9.9 AMENDMENT 1 to "if only one ships, ship the
tier"): audit_fixpoint still has no production-reachable entry point.

SHIPPED. The opt-in fixpoint tier is implemented, swept and documented; the scheduled-vs-reconciled choice ships as a permanent fault-injection test because no clean-traffic signal can justify it. Map docs/tk82-cascade-fixpoint-tier-2026-09-19.md (FROZEN). Not closed by this item: audit_fixpoint still has no production-reachable entry point (sec 8.8 rider, demoted by sec 9.9 AMENDMENT 1).
