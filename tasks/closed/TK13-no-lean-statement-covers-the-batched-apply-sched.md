---
id: TK13
title: no Lean statement covers the BATCHED apply schedule (async catch_up / build_index)
brief:
pri: HOLD
size: M
deps: []
related: [P18]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-29b
updated: 2026-08-29b
closed: 2026-08-29b
---

*"Nothing in the Lean tree quantifies over 'apply N ops, then one cascade'."* The model covers the synchronous per-write schedule; the async `catch_up` / offline `build_index` schedules — where many ops are applied and then a single cascade drains — have no statement.

**Distinct from `P18`** (the concurrency / multi-instance layer): this is SINGLE-WRITER batching, and it is what production actually runs on the async path. `HOLD` because the exclusion is declared and the sizing question (does this need a new schedule inductive, or does an existing drainedness theorem generalize?) has not been asked.

## Traps

⚠ **Appendix lead A13 would change the default batch size on exactly this path.** `ConnectedStore.catch_up` defaults to one unbounded batch today; if that becomes bounded, the batched schedule stops being an opt-in shape and becomes the normal one. Worth knowing which order those two land in.

⚠ **`advance_index`'s docstring is an ARGUMENT, not a proof.** It argues batch size *"affects only latency/granularity, not the final materialized state or any semantic guarantee"*. That is exactly the claim this row observes has no Lean statement; do not cite it as one.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (the corpus convention; `migrate.py::check_formal_pointer` enforces it for the generated rows and 18/18 formal tasks satisfy it)
- [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md)`:392-423` — the apply-step map and the missing quantification
- `connectedstore/apply.py::advance_index` — THE apply step, and its docstring's batch-size argument
- `python task.py show P18` — the adjacent concurrency row this is NOT

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-13 (`CD-2`, tier 2, sweep-d only); anchor re-resolved by COVERAGE.md §C4 at formal/CORRESPONDENCE.md:392-423.

### 2026-08-24b

related-edge sweep (trial finding F1): added `related: [P18]`. This row is the adjacent concurrency gap P18 is NOT; P18 did not name it back.

### 2026-08-29b

NARROWED, and the finding's premise was half wrong. Verification: CORRESPONDENCE.md sec 6 (:393-424) already OWNS the batched-schedule gap AND marks it open in as many words -- ':420-424' says 'nothing in the Lean tree quantifies over apply N ops, then one cascade' and names 'widening ReachedByW3d2E (or adding a batched constructor)' as the honest fix. So the gap needed no new carrier. What no file recorded is the COLLISION: connectedstore/apply.py:104-105's docstring asserts the exact safety claim sec 6 says is unproved, and sec 6 discusses advance_index without ever mentioning it. That trap is what was appended to docs/latent-gaps.md.
