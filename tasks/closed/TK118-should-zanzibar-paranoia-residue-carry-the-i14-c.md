---
id: TK118
title: should ZANZIBAR_PARANOIA=residue carry the I14 crossing-middle check? decide after a cost probe
brief: measured: paranoia=residue (the recommended production level) does not catch an I14 regression
pri: NOW
size: M
deps: []
related: []
parent:
labels: []
source: docs/p12-severity-sign-revert-probe-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-10-12b
updated: 2026-10-12b
closed: 2026-10-12b
---

Filed 2026-09-27d from the P12 build (docs/p12-severity-sign-revert-probe-2026-09-27.md; pinned by tests/test_p12_severity_sign.py::test_which_paranoia_level_catches_the_simulated_revert). MEASURED: under a simulated revert of the 2026-08-09 I14 fix, ZANZIBAR_PARANOIA=off and =residue both serve the fail-OPEN answer (negated oracle=False graph=True); only full and fixpoint abort with InvariantViolation I14. CLAUDE.md recommends residue for production as the runtime detector for the ZT-P0-1 escalation class, so a regression of that fix would be silent in production. The question is an ENGINEERING call (model decides, CLAUDE.md "Who decides"): add the I14 crossing-middle check to the residue tier, or document that residue does not cover it. Needs a cost measurement first -- residue is sold as about +5% on writes, and I14 is a whole-store scan today (src/zanzibar/graphindex/invariants.py::check_invariants), so it probably needs a delta-scoped form.

## Log

### 2026-10-04g

PROMOTED LATER -> NEXT 2026-10-04g (user pick: NEXT raised to 5). Why (READ by triage agent 2026-10-04g): tests/test_p12_severity_sign.py::test_which_paranoia_level_catches_the_simulated_revert shows ZANZIBAR_PARANOIA=residue, the RECOMMENDED production level, misses an I14 regression; the gate catches it under full paranoia. So this is production runtime detection, not test certainty: cost-probe the I14 crossing-middle check under residue first, then decide.

### 2026-10-12b

Re-ranked 2026-10-12b (user approved the order in chat): TK118 NOW, then TK79, then TK102 (NEXT); TK97 and TK44 down to LATER (process tooling / coverage research with no known bug); TK134+TK135 stay LATER, user says no rush to release 0.0.4. Why TK118 first: it is the only row about a fail-OPEN, and it bears on what we tell production users about residue today.

CLOSED 2026-10-12b. Decision (model, per CLAUDE.md "Who decides"): ADD a delta-scoped I14 to the residue tier rather than only documenting the gap. Doc (FROZEN): docs/tk118-residue-i14-2026-10-12.md.
LANDED: src/zanzibar/graphindex/invariants.py::check_i14_delta, which reuses the full checker's clause via _check_i14 (shared, so the tiers cannot drift). ParanoiaGuard.note_flush is an after_flush listener that records the touched (type, name) entities, plus a crossable type whenever one of its wildcard nodes is created or deleted. It returns immediately when the schema has no crossable shape.
PINS: tests/test_tk118_residue_i14.py (10 tests). The P12 residue row is flipped from fail-OPEN to abort.
SWEEP: M0-M8 all red except the control (literal output in the doc, section 3.1).
COST (benchmarks/probe_tk118_residue_i14.py, section 3.2): noise on a plain schema; on owc_star_ttu the I14 share is +12.0% at 160 writes and +5.7% at 480, shrinking with store size.
BOUNDARY: an untouched entity's I14 state and I13 refcount corruption remain full-tier only (test_the_tier_is_delta_scoped_not_whole_store).
Side observation, UNVERIFIED: residue itself read +14% to +19% over off at 160 writes, vs the +4.3% recorded 2026-07-26; the instrument noise is too wide to call it a regression.
