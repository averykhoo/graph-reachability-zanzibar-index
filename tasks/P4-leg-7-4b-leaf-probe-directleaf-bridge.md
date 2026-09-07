---
id: P4
title: leg 7 4b -- leaf-probe <-> directLeaf bridge
brief: Unblocked 2026-09-05b (P3 closed; deps swept); bridge target is the live leaf-routed write path
pri: LATER
size: M
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 015e6dd88c0d
created: 2026-08-16
moved: 2026-09-06b
updated: 2026-09-06b
closed:
---

leg 7 **4b** — leaf-probe ↔ `directLeaf` bridge. Unblocked 2026-09-05b (`P3` closed; deps
swept): the whole leaf-routed write path is live in the model (`Cascade.lean:190-191`,
`:340-341`, `affectedKeys` `:542-546`), so the bridge target is the landed leg, not a plan.

## Traps

⚠ **Do not cancel `P4` without reading why it must not be cancelled first.** Two frozen
records say so, and neither is reachable from this row's title or brief:

- `formal/history/leaf-family-split-scope-2026-08-05.md:1099` — under Route B, σ/σ0 reach
  agreement is **no longer supplied at leaf-node targets**. Nothing probes those today; the
  post-4b derived read path will, and that surface is this row. "Do not cancel `P4` without
  revisiting this."
- `formal/history/PROOF_STATUS.md:5146` — the same narrowing from the proof side: "If P4
  were ever cancelled, this narrowing is where the loss would surface."

The warning is reproduced here as a POINTER, not a copy: `formal/history/` is append-only
and frozen as-of-then, so a second copy of the sentence would be a second home for a claim
nothing updates (`docs/README.md`, one-home rule). Read the lines; do not trust this
summary of them.

⚠ **The general case is bigger than `P4`, and is filed as `TK66`.** The board-to-tree
migration could only carry what the board held, so ANY directive that lived only in
`formal/history/` is in this same position. `P4` is the instance that was measured; a
2026-09-07b sweep found sixteen more candidates. Do not read "P4 is fixed" as "the class is
fixed".

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule — stated there, and since 2026-09-07b enforced by nothing: this line used to cite `migrate.py::check_formal_pointer`, which was deleted with `.scratch/tasktool/` on 2026-09-07. `TK61` is the same defect elsewhere.)
- [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §7 — and §11.10 at `:1099` for the do-not-cancel warning above

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-09-05b

2026-09-05b: dep P3 swept (landed). Re-scope before starting: the leaf-probe <-> directLeaf bridge now has the whole leaf-routed write path live in the model (Cascade.lean:190-191, :340-341, affectedKeys :542-546), and the toolkit it was going to bridge to is the one CascadeStrataSettle.lean:3721 rawWriteRels_ne_nil_of_exprDirectsAll already walks (persistedLeaves/unionSpineLeaves/atomLeaves/pureLeaves/splitPure vs exprDirectsAll).

### 2026-09-06b

Board cell appended 2026-09-05b: 'Unblocked 2026-09-05b (P3 closed; deps swept)'. Task summary + brief now carry it (the 2026-09-05b Log entry already had the re-scope detail). Diff source: git 51642dc -> HEAD.
