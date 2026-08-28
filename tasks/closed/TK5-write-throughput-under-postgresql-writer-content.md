---
id: TK5
title: write throughput under PostgreSQL writer contention remains untested, and no row owns it
pri: LATER
size: M
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-29b
updated: 2026-08-29b
closed: 2026-08-29b
---

[`docs/architecture/correctness.md`](docs/architecture/correctness.md)`:125-140` argues multi-writer admission is correct by construction and that the `FOR UPDATE` semantics are now *observed* on PostgreSQL — lock ordering, contiguous exactly-once log rows under 4 concurrent writers, an index identical to a single-writer replay — and then ends: *"Throughput under contention remains untested beyond the retry-on-busy convergence tests."* An explicit gap in a LIVING architecture doc with no owning row.

Correctness under contention is covered; what is not measured is whether the lock ordering (source lock, then store lock, with an evaluator catch-up inside the section) degrades usefully or pathologically as writers are added. The deliverable is a measurement and a recorded number, not necessarily a fix.

## Traps

⚠ **The default CI run cannot answer this.** SQLite renders `_lock_store` to a no-op and serializes writers itself, so a green local run exercises a different path entirely. This needs the opt-in leg: `bash scripts/pg_local.sh start`, export the DSN as `ZANZIBAR_TEST_DSN`, and consider `ZANZIBAR_PG_REQUIRED=1` so a missing DSN is a hard error rather than a silent green.

⚠ **The PostgreSQL leg has a history of falsifying assumptions in this very document** — it *falsified three things this document used to assume* (`docs/spec-deviations.md` 2026-07-27) and found three real bugs its first day. Expect the measurement to change the prose, and budget for that rather than for a rubber stamp.

## Read first

- [`docs/architecture/correctness.md`](docs/architecture/correctness.md)`:125-140` — the claim and its own caveat (LIVING)
- `connectedstore/source.py::TupleSource._lock_source` and `index_v4/core.py::ReachabilityIndex._lock_store` — the two locks, in ordering
- `tests/test_postgres_ha.py` — the existing correctness leg to extend
- [`scripts/pg_local.sh`](scripts/pg_local.sh) — how to get a server

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-5 (`NG-2`, tier 1, sweep-n only); CONFIRMED OPEN by COVERAGE.md §C3; the sentence survives verbatim at docs/architecture/correctness.md:139-140 (LIVING).

### 2026-08-29b

APPENDED to docs/architecture/correctness.md, extending the multi-writer bullet in place rather than adding a second home. The write-off proposed for this id was REFUTED and the refutation was right: :139-140 sits in section 4 'Known gaps (documented, not defended)', whose sibling bullets are permanent accepted limitations ('Paranoia off = most runtime checking off', 'Freshness tokens lower-bound, never upper-bound'), so the sentence read as a scope disclaimer and a reader learned the limitation without learning a deliverable was owed. The appended clause is 'owed rather than accepted' plus the three things that were unique to tasks/: the deliverable is a MEASUREMENT not a fix; the reason it is a live question (the critical section runs an evaluator catch-up inside itself, so its length grows with the replica delta); and the target, tests/test_postgres_ha.py on the opt-in leg.
