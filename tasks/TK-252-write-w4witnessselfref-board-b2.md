---
type: Task
id: TK-252
aliases: [P8]
title: write W4WitnessSelfRef (board B2)
brief:
pri: LATER
state: closed
size: S
deps: []
related: []
parent: B2
labels: [formal]
source: board
source_hash: aa0f13958849
created: 2026-08-16
taskpy_moved: 2026-10-04g
taskpy_updated: 2026-10-04g
updated: 2026-11-25a
status: deprecated
closed: 2026-11-25a
moved: 2026-11-25a
---

write `W4WitnessSelfRef` (board `B2`)

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- [`PROOF_STATUS.md`](formal/history/PROOF_STATUS.md) 2026-08-08 §6

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-10-04g

Closability sweep 2026-10-04g (agent report, UNVERIFIED first-hand unless marked; the session did not act on it): PREMISE SUPERSEDED. The W4WitnessSelfRef proof was only a means to make self_flag theorem-backed; both premise bundles are now decided by Lean deciders (corpus.py ~:1273-1278 says INSIDE W4Fragment, DW-1) and _EXPECTED_ADMISSION_FAILURES omits SELF_REF:self_flag so test (G) pins it admitted (TK104). The witness was never written (0 hits in formal/lean). corpus.py ~:1277 GraphAdmission-half-still-unargued note predates TK104 and is stale. Residual: move self_flag (and ttu_fromchain/_group) into GRAPH_FRAGMENT, then close; caveat (REASONED): a zcli decider run is compiled code, not a kernel proof. B2 (the container) becomes closable when this resolves.
- 2026-11-25a (claude-code/claude-opus-5-5): rerank 2026-11-25a, first-hand verification (READ, claude-code/claude-opus-5-5) of the 2026-10-04g PREMISE SUPERSEDED report, CONFIRMED: grep W4WitnessSelfRef formal --include=*.lean = 0 hits (never written). W4Fragment half: corpus.py comment above SELF_REFERENTIAL_SCHEMAS (DW-1, 2026-09-23d) says FragmentDecide.lean::w4FragmentB puts self_flag INSIDE on all ten fields, and test_conformance_fragment.py::_EXPECTED_FAILURES has no SELF_REF:self_flag key, so (B) pins zero failures. GraphAdmission half: test_conformance_fragment.py::_EXPECTED_ADMISSION_FAILURES has no SELF_REF:self_flag key and test_lean_admission_verdict_matches_the_prediction (G) runs over REPORTED_INPUTS (SELF_REF family included), so it pins Lean admitting it (TK104; AdmissionDecide.lean::graphAdmissionB_iff, headlinePremiseB_iff = GraphAdmission and W4Fragment). The hand witness was only the means to theorem-back self_flag; both halves are now decided by deciders proved exact. Residual, cosmetic/conservative: self_flag is not in corpus.py::GRAPH_FRAGMENT nor test_conformance_graph.py::_THEOREM_BACKED, and the corpus.py sentence "The GraphAdmission half is still unargued" is stale since TK104. Closed on the owner yes (ASK-13).
- 2026-11-25a (claude-code/claude-opus-5-5): closed: Premise superseded: self_flag W4Fragment and GraphAdmission halves are both decided by exact Lean deciders (w4FragmentB_iff, graphAdmissionB_iff; pinned in test_conformance_fragment.py (B),(G)); the witness was only the means. Verified first-hand 2026-11-25a. Owner yes, ASK-13.
  residual risk: none
