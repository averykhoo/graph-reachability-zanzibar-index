---
id: TK16
title: joint inhabitation of a drained, non-trivially-reached state is empirical, not kernel-checked
pri: SOMEDAY
size: M
deps: []
related: []
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-29b
updated: 2026-08-29b
closed: 2026-08-29b
---

`W4Witness` machine-checks that both hypothesis BUNDLES are inhabited by a real compiled boolean schema, so the final theorems are not vacuous. The honesty caveat (`formal/FINAL_REVIEW.md` §2, restated at `formal/ARCHITECTURE.md:208-213`) is that **joint** inhabitation of a drained, non-trivially-reached state is demonstrated *empirically* — the conformance driver plus the proved `cascade2_drains` — rather than as a single kernel-checked term.

This is published honesty about a residual, already stated in two places, with a real empirical net underneath it. Filed at `SOMEDAY` so it has an address, not because it is queued.

## Traps

⚠ **Do not read the caveat as "the theorems might be vacuous".** Bundle inhabitation IS kernel-checked; it is the conjunction that is not. Overstating this is how a fair caveat becomes a false alarm.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (the corpus convention; `migrate.py::check_formal_pointer` enforces it for the generated rows and 18/18 formal tasks satisfy it)
- [`formal/ARCHITECTURE.md`](formal/ARCHITECTURE.md)`:208-213` — the caveat
- [`formal/FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §2 — its home
- `formal/lean/ZanzibarProofs/GraphIndex/CascadeStrata.lean::cascade2_drains` — the proved half

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-16 (`ARCH-H-12`, tier 2, sweep-h only); anchor re-read this pass at formal/ARCHITECTURE.md:208-213.

### 2026-08-29b

WRITTEN OFF against a living carrier; survived refutation. formal/FINAL_REVIEW.md:181-188 carries the honesty caveat verbatim, including the part that matters most and is easiest to overstate: bundle inhabitation IS kernel-checked and only the CONJUNCTION is empirical. A reader of the carrier learns the residual and its correct severity. Disposition recorded in the adjudication file.
