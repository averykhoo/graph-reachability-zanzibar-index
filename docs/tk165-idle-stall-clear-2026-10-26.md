# `TK165` — a lag-0 stall is cleared by a zero-row catch_up (2026-10-26)

> **FROZEN 2026-10-26 — provenance, not a living document.** Status lines below are
> as-of-then and several may now be false; live state: `HANDOFF.md` + the session
> ledger. Corrections are appended dated at the top, never edited into the body.

## Correction 2026-10-26e (gate fix): the edit moved the `Store.catch_up` anchor pin

The first gate run after this item went RED in two places with ONE cause (first-hand
READ of `.gate-runs/20261026-*-lean.log` and the tests-tile 1/4 and 2/4 logs):
`lean` step 4d2 printed `src/zanzibar/store/_store.py::Store.catch_up: BODY CHANGED
(py:function 845d20dc3e693d25 -> 9d752e89b1bd14f7)`, and
`tests/test_claim_rot_gate.py::test_B_python_body_edit_moves_the_pin` failed
`assert (2 == 1)` because the stale pin showed up beside its own sabotage. The three
`formal/CORRESPONDENCE.md` rows citing `Store.catch_up` (batched schedule, stall marker,
`fanout_cap_suspended` window) were re-read: all still hold. A dated TK165 note went on
the stall-marker row, and `formal/conformance/claim_rot.py --generate` re-pinned
(`545 anchors (1 changed, 0 added, 0 removed)`, changed: `Store.catch_up`). After that,
`test_claim_rot_gate.py` gave 42 passed, `claim_rot.py --check` printed `545/545 bodies
match`, and `verify.sh lean` PASSED (`.gate-runs/20261026-220457-lean.log`).
Tile 2/4 (run on the pre-fix tree) also had 6 `tests/test_userdocs_examples.py`
failures in which the child interpreter exited `3221225794` (0xC0000142,
STATUS_DLL_INIT_FAILED) with empty stdout and stderr. Another repo's heavy jobs were
loading the machine at the time. Re-run alone, the module gave `37 passed in 59.50s`.
REASONED: this was a failure to start the child process, not a docs or code defect.
On the fixed tree, tests-tile 1/4 and 2/4 PASSED (777 each). Tile 3/4 found a REAL
leak from this item: `tests/test_tk123_no_internal_refs.py::test_public_docstrings_carry_no_internal_refs`
failed with `store/_store.py IndexStalled [doc] 'TK165'`. The public `IndexStalled`
docstring had cited the task id. The id was dropped from the docstring, and the
provenance stays in the code comment inside `Store.catch_up`. The module was re-run
directly and gave `3 passed`. `claim_rot.py --check` still printed `545/545`.

## Correction 2026-10-26e (repair round 1): "zero rows" did NOT mean "at the head"

The safety argument below ("A poison-row stall cannot reach the branch ... the batch
returns rows") was **FALSE for `catch_up(batch=0)`**: `log_rows(limit=0)` returns `[]`
with the poison row still pending, so the branch cleared a `PathCountExceeded` stall.
It held only for `batch=None` or `batch >= 1`. Found by the TK165 review; reviewer probe
`.scratch/wf-rel010/rev165/batch0.py`, output (RAN by the reviewer, first-hand):

```text
before: stalled True lag 125
catch_up(batch=0) -> 0
after: stalled False lag 125 stall_error None
lookup SERVED (stale)
check MALLORY -> True (set engine truth: False)
```

That is the TK111 stale-ALLOW class. Before TK165 that path rolled back and the stall
stayed. **Repair (READ, `src/zanzibar/store/_store.py`), two independent guards:**

1. `Store.catch_up` refuses `batch` that is not `None` or an `int >= 1`
   (`ValueError` for `< 1`, `TypeError` for a bool or non-int) before the log is read.
2. `Store._catch_up` clears only after a **head probe**:
   `not log_rows(session, cursor.source_store_id, cursor.applied_log_id, limit=1)`,
   under the same store lock and snapshot. So the clear no longer depends on the batch
   limit or on why `advance_index` returned 0.

New pins in `tests/test_tk165_idle_stall_clears.py` (RAN 2026-10-26e, 10 passed):
`test_catch_up_refuses_a_batch_below_one_and_the_poison_stall_survives` (batch
0/-1/True/1.5/'1', then `batch=1` up to and onto the failing row, the stall stays)
and `test_a_zero_row_batch_with_a_poison_row_pending_does_not_clear` (zero-row branch
driven with the poison row pending: internal `_catch_up(0)`, and an `advance_index`
stubbed to return 0). Sabotage (RAN 2026-10-26e, `.scratch/wf-rel010/rev165/sab.py`,
byte-restore asserted `restored True`):

```text
===== S4 rc 1        (the batch < 1 check made a no-op)
FAILED ...::test_catch_up_refuses_a_batch_below_one_and_the_poison_stall_survives[0-ValueError]
FAILED ...::test_catch_up_refuses_a_batch_below_one_and_the_poison_stall_survives[-1-ValueError]
2 failed, 8 passed in 57.02s
  [0-ValueError]:  Failed: DID NOT RAISE ValueError   (the head probe still kept the stall)
  [-1-ValueError]: PathCountExceeded raised instead   (SQLite reads LIMIT -1 as no limit)
===== S5 rc 1        (the head probe replaced by True)
FAILED ...::test_a_zero_row_batch_with_a_poison_row_pending_does_not_clear[inner_batch0]
FAILED ...::test_a_zero_row_batch_with_a_poison_row_pending_does_not_clear[zero_rows_for_any_reason]
2 failed, 8 passed in 58.98s
```

Was ACTIVE-PLAN until TK165 closed the same session. Session key `2026-10-26e` (workflow wf-rel010).
Provenance labels: **READ** = first-hand reading of the tree, **RAN** = first-hand run in
this session, **REASONED** = argument, not measured.

## The defect (RAN)

`docs/tk151-repros-2026-10-20/B3.py`, re-run 2026-10-26e BEFORE the fix, matched the
2026-10-20b output in `docs/tk151-repros-2026-10-20/README.md` §B3. Part A (injected
lost connection on an idle poll):

```text
  [after failed idle poll] lag=0 applied=1 stalled_after=1 index_stalled=True
  catch_up() #1 (healthy, nothing pending) -> 0
  catch_up() #2 (healthy, nothing pending) -> 0
  catch_up() #3 (healthy, nothing pending) -> 0
  [after 3 successful zero-row catch_ups] lag=0 applied=1 stalled_after=1 index_stalled=True
  lookup -> IndexStalled: lookup() cannot be served: the index for store 'my-app' is STALLED at log id 1 (lag 0): ...
```

Part B (real SQLite lock held by a second connection, no library code patched):
`catch_up() raised OperationalError after 44.5s: (sqlite3.OperationalError) database is
locked`, then `[after zero-row catch_up] ... stalled_after=1 index_stalled=True`.

## The fix (READ)

`src/zanzibar/store/_store.py::Store._catch_up`, zero-row branch: when `advance_index`
returns 0 and `cursor.stalled_after == cursor.applied_log_id`, clear `stalled_after` and
`stall_error` and COMMIT (the other zero-row case still rolls back, blind-audit X2).
`IndexStalled`'s docstring now says a zero-row `catch_up()` at the log head clears it. The
`IndexStalled` message is unchanged: its advice "a successful catch_up()" is now true.

Why it is safe (REASONED): `advance_index` takes `widx.idx._lock_store()` and refreshes
the cursor under it before reading the log (`src/zanzibar/store/apply.py::advance_index`),
so "zero rows" means nothing past `applied_log_id` was visible under the store lock; the
staleness bound is restored. A poison-row stall cannot reach the branch: its failing row
is still past the cursor, so the batch returns rows and fails again (`_record_stall`
re-records). No classifier was added to `_record_stall` (its docstring's fail-open
warning). Not in the Lean model: the stall marker is Store-level, not in
`formal/CORRESPONDENCE.md`'s modelled `advance_index`.

## After the fix (RAN)

Same `B3.py`, 2026-10-26e: Part A `[after 3 successful zero-row catch_ups] lag=0 applied=1
stalled_after=None index_stalled=False` and `lookup -> LookupResult(node_ids={2}, ...)`;
Part B `[after zero-row catch_up] lag=0 applied=1 stalled_after=None index_stalled=False`.

## Pins and sabotage (RAN)

`tests/test_tk165_idle_stall_clears.py`: zero-row clear; the clear is committed (a
replica's `refresh()` sees it); a `PathCountExceeded` stall survives three later
`catch_up()` calls (negative pin). Sabotage via `.scratch/wf-rel010/tk165/sabotage.py`
(byte-restore asserted), literal tails:

```text
## S1 rc=1   (elif branch disabled)
...test_tk165_idle_stall_clears.py:67: assert not True
...test_tk165_idle_stall_clears.py:91: assert not True
2 failed, 1 passed in 14.19s
## S2 rc=1   (rollback() instead of commit() in the branch)
...test_tk165_idle_stall_clears.py:67: assert not True
...test_tk165_idle_stall_clears.py:91: assert not True
2 failed, 1 passed in 11.65s
## S3 rc=1   (instrument control: _record_stall records nothing)
...test_tk165_idle_stall_clears.py:53: assert False
...test_tk165_idle_stall_clears.py:53: assert False
...test_tk165_idle_stall_clears.py:112: assert False
3 failed in 5.00s
```

PostgreSQL leg (RAN, 2026-10-26e): `scripts/pg_local.sh start`, then
`tests/test_postgres_ha.py`, `tests/test_connectedstore_multi_instance.py`,
`tests/test_connectedstore_concurrency.py`, `tests/test_tk111_stall_aware_freshness.py`
with `ZANZIBAR_TEST_DSN` + `ZANZIBAR_PG_REQUIRED=1`: `39 passed, 3 skipped` (the three
skips are the documented SQLite-WAL-only tests). The TK165 pins themselves are SQLite
only; no PostgreSQL variant of the zero-row clear exists (UNVERIFIED there beyond the
reasoning above).

## Docs updated

The pages `docs/tk151-repros-2026-10-20/README.md` §B3 lists as describing the old
behaviour: `userdocs/explanation/consistency.md` ("How a stall ends"),
`userdocs/how-to/stall-recovery.md` ("Transient"), `userdocs/how-to/async-tokens.md`
(worker-loop notes), `userdocs/reference/exceptions.md` (`IndexStalled`). The others it
lists (`limits.md`, `two-backends.md`, `errors.md`, `bulk-load-adopt.md`,
`reference/api/store.md`) were marked "not affected" there; a grep of `userdocs/`,
`README.md` and `PYPI_README.md` for "applies nothing" / "at least one row" / "lag 0" /
"idle" found no other caveat text. `CHANGELOG.md` [Unreleased] Fixed has the entry.
