---
id: TK33
title: store-level rebuild-instead-of-K-deltas IVM amortisation, measured crossover K* ~ 30-40
brief:
pri: HOLD
size: L
deps: []
related: []
parent:
labels: [perf]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-09-10
updated: 2026-09-10
closed:
---

The evaluated proposal (*"if we detect a DoS-causing fan-out, do a bulk rebuild instead of adding the thing the usual way"*) was **refuted as stated** — the measurement table at `docs/spec-deviations.md:805-816` separates three costs it conflated. But the same entry records a different idea that survived: **store-level rebuild instead of applying K pending deltas is a sound IVM amortisation with a measured crossover at K\* ≈ 30-40**, described as *a better idea than the per-write version and composable with async*. It was recorded and not adopted.

`HOLD`: it inherits the same blockers 2-4 as the refuted version — mid-stream rebuild refusal, the quiescence requirement, and reintroducing a lock — and none of those has been adjudicated.

## Traps

⚠ **The neighbouring proposal in the same entry is REFUTED, and they read alike.** Quote the K\* line (`:859`), not the entry's headline; landing the wrong half means implementing something the repo already measured and rejected.

⚠ **A rebuild that can refuse mid-stream is a fail-open shape.** The repo's standing rule for the closure fan-out cap is that removals are EXEMPT because a cap that can refuse a revocation is a fail-open (`CLAUDE.md`, `ZANZIBAR_MAX_CLOSURE_FANOUT`). Any amortisation that can decline to apply pending deltas owes the same argument.

## Read first

- [`docs/spec-deviations.md`](docs/spec-deviations.md)`:855-862` — the surviving idea and its measured crossover; `:801-816` — the refuted proposal and the measurement table that killed it
- `connectedstore/apply.py::advance_index` — the apply step any amortisation replaces
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the reopening rule

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-18 (`SD-C6`, tier 3, sweep-c only); anchor re-resolved by COVERAGE.md §C4. The crossover figure is at docs/spec-deviations.md:859; the proposal it grew out of is at :801-804 with the measurement table at :805-816.

### 2026-09-10

TK53 disposition 2026-09-10: NOT an append. Both the verify and the adversarial pass agree the statement is ALREADY CARRIED in the named destination, `docs/spec-deviations.md` -- the rebuild-outbox entry's blocker 4 (zero REMOVED rows, the fail-open direction), the cap note that `index_v4/core.py` "already exempts removals" (grepped live), and the later "it inherits blockers 2-4" sentence that binds mid-stream refusal, quiescence and the REMOVED fail-open together.

I confirmed the two anchor phrases exist first-hand; I did not re-derive the whole store-level-quota argument. Deliberately citing them by PHRASE, not line: this session appended three dated entries to the top of that file, so every line number recorded for it before 2026-09-10 has shifted.

No prose was written. The row stays open as work (the amortisation question is undecided); what it is no longer is a statement that exists only in `tasks/`.
