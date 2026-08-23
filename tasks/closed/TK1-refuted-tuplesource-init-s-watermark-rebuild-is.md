---
id: TK1
title: REFUTED: TupleSource.__init__'s watermark+rebuild is atomic (_consistent_rebuild, 2026-07-27)
pri: LATER
size: S
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed: 2026-08-21b
---

Filed as a **CLOSED record, not as work.** The sweep's only tier-1 "live correctness" finding was already fixed three weeks before it was read. It gets an id anyway, and that is what an id that carries forward forever is FOR: the next reader who greps `docs/spec-deviations.md` for *"There is no one-line fix"* lands here instead of re-deriving the same dead defect a third time.

The claim was that `TupleSource.__init__`'s watermark read and evaluator rebuild are non-atomic under PostgreSQL `READ COMMITTED`. `connectedstore/source.py::TupleSource._consistent_rebuild` is the fix: an optimistic re-read loop bounded by `SNAPSHOT_ATTEMPTS = 3` (`source.py:92`) and then a terminating fallback that takes the shared source lock. `__init__` uses it at `source.py:272`; the rebuild path uses it too.

## Traps

⚠ **This is the sweep-wide lesson, not a one-off.** A dated entry in `docs/spec-deviations.md` states the PROBLEM in the present tense and the FIX in the next paragraph, and the same session shipped both. Grepping the problem sentence finds a solved defect that reads as live. Any item sourced from a dated ledger entry must be checked against the CODE before it is filed as open — exactly what the re-validation pass was for, and it demoted this item from "the highest-ranked open defect" to nothing.

⚠ **Do not "fix" `spec-deviations.md` by editing the historical entry.** It is a dated record and it is correct as history. If anything is owed there it is a forward pointer, and that is a separate, reviewed docs edit.

## Read first

- `connectedstore/source.py::TupleSource._consistent_rebuild` — the fix, and `source.py:253-254`, which states the atomicity requirement outright
- [`docs/spec-deviations.md`](docs/spec-deviations.md) `## 2026-07-27` — the entry whose PROBLEM paragraph the sweep quoted as current state
- `tests/test_postgres_ha.py:21-26` — the xfails converted to positive pins once `_consistent_rebuild` landed; `:630` and `:681` assert `snapshot_attempts >= 2`
- `tests/test_zt_p1_8.py:300-323` — drives both arms directly

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-1 (`SD-C1`, tier 1, sweep-c only); REFUTED by COVERAGE.md §C2 (2026-08-21b re-validation) and re-confirmed against the code this pass.

CLOSED ON ARRIVAL as a disproof record. COVERAGE.md's U-1 (`SD-C1`), its only tier-1 correctness finding, describes a defect that was FIXED ON 2026-07-27, three weeks before the sweep read it. Evidence, re-checked against the live tree 2026-08-21: connectedstore/source.py::TupleSource._consistent_rebuild is an optimistic re-read loop with SNAPSHOT_ATTEMPTS = 3 (source.py:92) plus a terminating shared-source-lock fallback; __init__ calls it at source.py:272 and the rebuild path at :638; source.py:253-254 states the requirement outright ("The watermark read and the rebuild must be ATOMIC with respect to other instances' commits"); git log -S'_consistent_rebuild' -> 49b97a5, 2026-07-27, i.e. the very commit the quoted doc entry documents; tests/test_postgres_ha.py:21-26 records the xfails converted to positive pins once it landed, with :630/:681 asserting snapshot_attempts >= 2, and tests/test_zt_p1_8.py:300-323 driving both arms. Root cause of the false finding: sweep-c quoted the PROBLEM paragraph (including its "There is no one-line fix") out of a DATED historical entry in docs/spec-deviations.md and read it as current state. No work is owed. Reopen only if _consistent_rebuild is removed.
