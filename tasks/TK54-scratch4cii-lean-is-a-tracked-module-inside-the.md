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
source: hand
source_hash:
created: 2026-09-05b
moved: 2026-09-05b
updated: 2026-09-05b
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
