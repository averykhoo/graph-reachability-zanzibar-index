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
moved: 2026-09-18c
updated: 2026-09-18c
closed:
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
