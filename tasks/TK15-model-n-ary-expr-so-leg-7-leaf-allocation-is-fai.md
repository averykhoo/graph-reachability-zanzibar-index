---
id: TK15
title: model n-ary Expr so leg-7 leaf allocation is faithful to nested-union parenthesization
brief:
pri: SOMEDAY
size: L
deps: []
related: []
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-09-10
updated: 2026-09-10
closed:
---

Lean's `Expr` is binary where Python's compiler flattens n-ary unions, so leaf allocation under leg 7 is faithful only up to parenthesization. `CORRESPONDENCE.md:807-851` declares it not-fixed with a stated reason: it is a `Core/` **trust-root** change touching every downstream proof, *"far outside leg 7's scope"*.

`SOMEDAY` is the honest pri: this is not deferred pending a decision (that would be `HOLD`) — the decision was made and recorded. It is revisited only on concrete need, e.g. if a corpus is found where the parenthesization actually changes leaf allocation observably.

## Traps

⚠ **A trust-root edit invalidates every proof beneath it.** Anything that touches `Core/` re-runs the whole Lean phase and can strand in-flight legs. Do not start this while leg 7 is executing.

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (the corpus convention. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md)`:807-851` — the DECLARED-not-fixed entry and its scope argument
- `zanzibar_utils_v1.py::compile_ruleset` — the Python side that flattens

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-15 (`CD-3`, tier 2, sweep-d only); anchor re-resolved by COVERAGE.md §C4 at formal/CORRESPONDENCE.md:807-851.

### 2026-09-10

TK53 disposition 2026-09-10: NOT an append. Both passes agree the statement is ALREADY CARRIED in `formal/CORRESPONDENCE.md` -- the binary-`Expr`-vs-`_fold_binary`-left-fold-vs-`_build_plan_tree` entry, together with its declared-not-fixed note placing a `Core/` change far outside leg 7's scope.

Honest scope note: this is the one row of the fifteen whose carrier I did NOT re-read first-hand -- it rests on the verify pass plus an adversarial pass that tried to refute it and instead strengthened it. The adversarial pass did correct its location: the entry is in sec 7.2, not sec 7.1 as the verify pass reported (the file's own cross-reference at :319 points at "sec 7.2's n-ary-allocation" note). Line numbers for this file recorded before 2026-09-10 are stale by about 22 lines -- this session inserted into sec 7.1 twice.

No prose was written. Row stays open as modelling work.
