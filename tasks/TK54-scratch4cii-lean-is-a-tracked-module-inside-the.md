---
id: TK54
title: Scratch4cii.lean is a tracked module inside the gated proof tree -- delete or justify
brief: found 2026-09-05b while landing P3; sorry-free, source of the linter warnings; pre-existing, untouched
pri: LATER
size: S
deps: []
related: [P5]
parent:
labels: [formal]
source: board
source_hash: 746043b9a68a
created: 2026-09-05b
moved: 2026-09-06b
updated: 2026-09-06b
closed:
---

`formal/lean/ZanzibarProofs/GraphIndex/Scratch4cii.lean` is a TRACKED module INSIDE the gated
lake package (committed at `a55a433`; sorry-free; it is the source of the build's linter
warnings). Found 2026-09-05b while landing `P3`, left untouched. Decide: delete it (its
content is either already in `LeafRules.lean`/`Leaf.lean` or belongs in `formal/history/`),
or rename it to say what it pins and give it a docstring that justifies its place in the
build. Whichever: the job count (1089) and `MIN_SCANNED_LEAN_FILES` move — re-measure, do not
difference. Related: `P3` (closed), `formal/history/PROOF_STATUS.md` `2026-09-05b` §9.5.

## Log

### 2026-09-06b

source: hand -> board by HAND EDIT 2026-09-06b, the route docs/tasktool-spec.md sec 3.1 prescribes for a wrong source value ('a hand edit plus a Log entry saying so'). Reason: this task was filed by hand AND given a board row in the same session under the dual-update contract, so sync reconciles it against the board (it reported BODY drift '(never reconciled)') while ack REFUSED it as hand-sourced (rc 2, task.py::op_ack:3175) -- a permanent red with no verb to clear it (trial friction A7 item 1). The tool's own remedy (delete the file, new --id --source board) would delete a committed task file, which sec 4 forbids, and would reset created. Body left as-is: it already matches the board cell.

First reconciliation against the board row filed 2026-09-05b: cell and task body agree (Scratch4cii.lean tracked inside the gated package since a55a433; delete or justify; job count and MIN_SCANNED_LEAN_FILES move -- re-measure).
