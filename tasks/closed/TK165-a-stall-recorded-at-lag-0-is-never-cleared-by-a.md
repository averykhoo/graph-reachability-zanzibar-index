---
id: TK165
title: a stall recorded at lag 0 is never cleared by a catch_up that applies nothing
brief: contradicts the IndexStalled docstring; only an applied write or rebuild_index clears it
pri: LATER
size: S
deps: []
related: [TK151]
parent:
labels: []
source: docs/tk151-repros-2026-10-20/README.md
source_hash:
created: 2026-10-20b
moved: 2026-10-26e
updated: 2026-10-26e
closed: 2026-10-26e
---

If catch_up fails on an idle store (lag 0; e.g. a transient lock error while taking the store lock before finding no rows) it records stalled_after == applied_log_id. Later successful catch_up calls return 0 and leave the stall, so untokened lookups keep raising IndexStalled until some write is applied. Agent fix: on a zero-row successful batch with stalled_after == applied_log_id, clear the stall.

Repro and first-hand output: `docs/tk151-repros-2026-10-20/README.md` section B3 (`docs/tk151-repros-2026-10-20/B3.py`). Found by the TK151 docs pass 2026-10-20b; the user docs describe the CURRENT behaviour as a caveat, so fixing this means updating the pages that section lists.

## Read first

- `docs/tk151-repros-2026-10-20/README.md`

## Log

### 2026-10-26e

LANDED: src/zanzibar/store/_store.py::Store._catch_up zero-row branch clears stalled_after/stall_error and COMMITS when stalled_after == applied_log_id (index proven at log head under the store lock); poison-row stalls cannot reach it. IndexStalled docstring updated; message unchanged (its advice is now true). Tests: tests/test_tk165_idle_stall_clears.py (3: zero-row clear, clear committed for a replica, PathCountExceeded stall survives). Sabotage S1 (branch off) and S2 (rollback) -> 2 failed; S3 (_record_stall no-op, instrument control) -> 3 failed. B3.py re-run before/after. Related modules (all catch_up tests + tk123/tk153) 801 passed; doc tests 60 passed; PG leg (postgres_ha, multi_instance, concurrency, tk111) 39 passed 3 skipped (SQLite-WAL-only). Docs: userdocs consistency.md, stall-recovery.md, async-tokens.md, reference/exceptions.md caveats rewritten; CHANGELOG [Unreleased] Fixed. Record: docs/tk165-idle-stall-clear-2026-10-26.md (FROZEN). Not run: full gate (later stage). Next: none.

Repair round 1 (review): BLOCKING fixed -- `catch_up(batch=0)` cleared a PathCountExceeded stall (log_rows(limit=0) == [] looked like "at head"; reviewer probe: stalled False, lookup SERVED stale, check MALLORY True vs set-engine False). Two guards in src/zanzibar/store/_store.py: `Store.catch_up` refuses batch not None / int >= 1 (ValueError/TypeError) before reading the log; `Store._catch_up` clears only after a head probe `not log_rows(..., applied_log_id, limit=1)`, independent of batch. New pins in tests/test_tk165_idle_stall_clears.py (batch 0/-1/True/1.5/str refused + stall survives incl. batch=1 onto the failing row; zero-row branch with poison pending via _catch_up(0) and a 0-returning advance_index). Sabotage S4 (validation no-op) 2 failed/8 passed, S5 (probe -> True) 2 failed/8 passed; literal output in the dated correction at the top of docs/tk165-idle-stall-clear-2026-10-26.md (safety-argument precondition stated there). userdocs/how-to/async-tokens.md notes the batch contract. RAN: tk165+tk111+tk121+connectedstore_async+tk123+tk170 75 passed; userdocs build/examples/prose 41 passed. Not gated, not committed. Next: full gate by the commit stage.
