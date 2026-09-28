---
id: TK118
title: should ZANZIBAR_PARANOIA=residue carry the I14 crossing-middle check? decide after a cost probe
brief: measured: paranoia=residue (the recommended production level) does not catch an I14 regression
pri: LATER
size: M
deps: []
related: []
parent:
labels: []
source: docs/p12-severity-sign-revert-probe-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-09-27d
updated: 2026-09-27d
closed:
---

Filed 2026-09-27d from the P12 build (docs/p12-severity-sign-revert-probe-2026-09-27.md; pinned by tests/test_p12_severity_sign.py::test_which_paranoia_level_catches_the_simulated_revert). MEASURED: under a simulated revert of the 2026-08-09 I14 fix, ZANZIBAR_PARANOIA=off and =residue both serve the fail-OPEN answer (negated oracle=False graph=True); only full and fixpoint abort with InvariantViolation I14. CLAUDE.md recommends residue for production as the runtime detector for the ZT-P0-1 escalation class, so a regression of that fix would be silent in production. The question is an ENGINEERING call (model decides, CLAUDE.md "Who decides"): add the I14 crossing-middle check to the residue tier, or document that residue does not cover it. Needs a cost measurement first -- residue is sold as about +5% on writes, and I14 is a whole-store scan today (index_v4/invariants.py::check_invariants), so it probably needs a delta-scoped form.

## Log
