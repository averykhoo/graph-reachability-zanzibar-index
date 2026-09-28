---
id: TK119
title: keyLeafRewrites row: the 50/50 schemas leaf-rule claim is unbacked; make it a test or drop it
brief: CORRESPONDENCE keyLeafRewrites 50/50 claim has no test behind it; test it or delete the number
pri: LATER
size: S
deps: []
related: []
parent:
labels: [formal]
source: docs/p13-claim-rot-gate-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-09-27d
updated: 2026-09-27d
closed:
---

Filed 2026-09-27d from the P13 build (docs/p13-claim-rot-gate-2026-09-27.md). The new prose-number lint (formal/conformance/claim_rot.py, verify.sh step 4d3) found seven uncited ratio claims in formal/CORRESPONDENCE.md on its first run; each was marked past (dated + pastness word) so the lint passes. One of them, the keyLeafRewrites row's "50/50 schemas" leaf-rule comparison, came from a one-off 2026-08-16 probe that NO test re-runs, so nobody knows whether it still holds. Either turn the comparison into a test (and cite it in the row's sentence, which the lint accepts) or delete the number and say what was checked. Do not just leave it marked past -- that is the lint's escape hatch, not a verification.

## Log
