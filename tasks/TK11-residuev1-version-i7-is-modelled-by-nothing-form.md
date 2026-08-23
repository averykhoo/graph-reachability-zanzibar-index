---
id: TK11
title: ResidueV1.version (I7) is modelled by nothing formal; ZT-P4-5 declared it and never refiled
pri: LATER
size: M
deps: []
related: []
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed:
---

`index_v4/models.py::ResidueV1` carries a `version` column, incremented in `index_v4/processor.py::DeltaProcessor._store_residue` and checked by **I7** (monotonicity per residue row) in `index_v4/invariants.py::_check_residue_rows`. Lean's `Residue` has no version field, so I7 is pinned only by `tests/` paranoia runs. `CORRESPONDENCE.md` calls it *a MODELLING GAP, not a representation difference*, and declares it as projection `P7` (`ZT-P4-5(b)`, 2026-07-27).

The reason it needs an id: the closed record `ZT-P4-5` is titled *"residual declared: I7 ungated by formal"* — **the residual was declared AT CLOSURE and never re-filed as an open row.** A declared residual with no open carrier is indistinguishable, six months later, from a closed one.

## Traps

⚠ **The `P7` collision is real and it is how this looks captured when it is not.** Lean's projection `P7` (in `FINAL_REVIEW.md` prose) is not board id `P7` (`ttuStarFree (iii)+(iv)`). Sweep-i flagged exactly this. Do not resolve "P7" by grep.

⚠ **Version is about to become load-bearing for a read path.** Appendix lead A14 (`docs/perf-round6-audit-2026-08.md:919`) proposes a persistent derived-check cache validated by `ResidueV1.version`. If that lands, every derived read's correctness rests on I7 — which is this gap. Adjudicate them together.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (the corpus convention; `migrate.py::check_formal_pointer` enforces it for the generated rows and 18/18 formal tasks satisfy it)
- [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md)`:515-534` — the declared gap, and [`formal/FINAL_REVIEW.md`](formal/FINAL_REVIEW.md)`:443-448` — the same gap in the second document
- `index_v4/invariants.py::_check_residue_rows` — I7, the only thing pinning it
- `python task.py show ZT-P4-5` — the closure that declared the residual

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-11 (`CD-1` = `NEW-3`, tier 2) — one of only four items found by two buckets (sweep-d + sweep-i) in two documents, and independently inventory-formal.md MISS #2. Anchor re-read at formal/CORRESPONDENCE.md:515-534.
