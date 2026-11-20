---
type: Question
id: ASK-5
title: Retire TK-36 (symbolic wildcard delta expansion, a spec non-goal with no consumer)?
brief: 'recommend retire: the spec lists it as a non-goal and no consumer exists'
pri: LATER
state: open
deps: []
source: session 2026-11-20a
created: 2026-11-20
moved: 2026-11-20a
updated: 2026-11-20a
last_asked:
---

**Question:** Retire TK-36 (a layer that expands symbolic wildcard PermissionDeltas)?

**Context:** `docs/specs/wildcard-materialization-spec.md` (line 259, and §10 at line 324) lists the expansion of symbolic wildcard deltas as a non-goal: deltas that mention a wildcard pass through untouched. The pass-through shipped. The row's own text says a consumer that needs expanded deltas is what would justify the layer, and none exists. Found in the 2026-11-20a re-rank, which cites no goal this row serves.

**Why owner-only:** removing work from the board is the owner's call (procedures § Rerank step 4).

**Options:**

- A. Retire it: close TK-36; the spec's non-goal and `docs/spec-deviations.md` keep the record, and a future consumer would file a fresh row.
- B. Keep it at SOMEDAY, as now.

**Recommendation:** A. The spec already records it as a non-goal with no consumer, so the row adds nothing the spec does not hold, and it would also cut against the spec's own "never enumerate a marker into concretes" invariant.

**Blocks:** none

## Log
