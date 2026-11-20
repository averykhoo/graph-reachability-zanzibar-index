---
type: Question
id: ASK-6
title: Merge TK-67 (FoldAdmits lockstep correction) into TK-277 as a trap?
brief: 'recommend merge: TK-277 is its only consumer (2026-10-04g sweep)'
pri: LATER
state: open
deps: []
source: session 2026-11-20a
created: 2026-11-20
moved: 2026-11-20a
updated: 2026-11-20a
last_asked: 2026-11-20a
---

**Question:** Merge TK-67 (the FoldAdmits "lockstep" correction) into TK-277 as a trap?

**Context:** TK-67 records that two live documents say `FoldAdmits` sites move "in lockstep", while the frozen correction says 21 sites move and 3 must stay. Both live sites were annotated 2026-09-07b with a pointer to the correction, which stopped the immediate hazard. The remaining work is re-checking the three sites against the current Lean tree, and that matters only to whoever widens ttuStarFree. The 2026-10-04g sweep found its only consumer is P6, which is TK-277; it suggested folding it into P6 as a trap and closing it as merged. TK-277 went to SOMEDAY at the 2026-11-20a re-rank (parked by the owner 2026-09-15d). TK-67 stays LATER until this is answered.

**Why owner-only:** closing a row as merged removes it from the board, which is the owner's call (procedures § Rerank step 4).

**Options:**

- A. Merge: copy TK-67's correction into TK-277's `## Traps`, then close TK-67 as merged into TK-277.
- B. Keep TK-67 as its own row at LATER.

**Recommendation:** A. The trap matters only to the session that does TK-277's work, so it belongs in TK-277's Traps, where that session reads it first.

**Blocks:** none

## Log
