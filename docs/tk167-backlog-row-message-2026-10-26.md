# `TK167` — a sync write blocked by another writer's backlog row names it (2026-10-26)

> **FROZEN 2026-10-26 — provenance, not a living document.** Status lines below are
> as-of-then and several may now be false; live state: `HANDOFF.md` + the session
> ledger. Corrections are appended dated at the top, never edited into the body.

## Correction 2026-10-26e (repair round 1, after review) -- first-hand READ + run

The guard below ("`exc.failing_log_row[0] != token`") was WRONG for a duplicate add. A
duplicate `add` appends no log row and returns the log HEAD as its token; with the
blocking row at the head (as in B6) the token equals its id, so the backlog row read as
the caller's own and the bare message came back. Reviewer's first-hand repro: B6 setup +
a duplicate `s.add_tuple('user:alice','member','group:a0')` raised "PathCountExceeded:
path count bound exceeded: this edge would give closure row user:alice ->
group:a32#member ..." with `failing_log_row` (254, ...), head = 254.

Fix: `_name_blocking_backlog_row(exc, own_row_id, store_id)` now takes the id of the
row THIS call appended (from the pending-rows hint in `Store._write`, `None` on a
duplicate add) instead of the token; with `None` the message starts "this write (a
duplicate add, which appends no log row) was rolled back ...". New test:
`tests/test_tk167_backlog_row_named.py::test_sync_duplicate_add_names_the_backlog_row`
(parametrized: an unrelated duplicate and a duplicate of the poison tuple; it asserts the
poison row IS the log head first). Module: 7 passed.

Sabotage (run 2026-10-26e, `_store.py` copied aside, restored by cp, cmp-identical):

```text
S3 (reviewer) `if isinstance(exc, ClosureFanoutExceeded):` -> `if False:`
  1 failed, 4 passed (test_fanout_cap_type_is_covered_too)   [pre-repair module]
S4 the call passes `token` again instead of `own_row_id`
FAILED tests/test_tk167_backlog_row_named.py::test_sync_duplicate_add_names_the_backlog_row[unrelated-duplicate]
FAILED tests/test_tk167_backlog_row_named.py::test_sync_duplicate_add_names_the_backlog_row[poison-duplicate]
2 failed, 5 passed in 3.23s
restored: 7 passed in 3.55s
```

S2 below names the old `row[0] != token` guard; the guard is now
`own_row_id is not None and row[0] == own_row_id`.

Session `2026-10-26e` (workflow wf-rel010, TK167 stage). Row: `task.py show TK167`.

## What changed

- `src/zanzibar/store/_store.py::_name_blocking_backlog_row`, called from the
  `IndexResourceLimit` arm of `Store._write` (after the rollback and the admission undo).
  When `exc.failing_log_row[0] != token` (the failing row is not the caller's own log
  row), the SAME exception instance gets a new `args[0]`: "this write (log row N) was
  rolled back because the index backlog of store '<id>' holds an earlier log row it
  cannot apply: row M (<row>). Every sync=True write on this store id, removals included,
  is refused <until ...>. Recovery: <...>. The index refused row M with: <original>".
  Recovery text is type-aware: `PathCountExceeded` -> `sync=False` removal then
  `zanzibar.store.rebuild_index`; `ClosureFanoutExceeded` -> `Store.catch_up()` (it runs
  with the cap suspended). Type, `failing_log_row` and the traceback note are unchanged;
  an own-row refusal is untouched. No new exception type (REASONED: a new type would
  break `except PathCountExceeded` handlers for no gain; the message is what was wrong).
- Not done (REASONED, deliberately): recording a stall on this sync path. The write
  transaction is rolled back; the async instance's `catch_up` already records it, and
  `IndexStalled` semantics are unchanged by TK167.
- Equivalence: unaffected. The refusal path is the existing one; the new test asserts the
  refused write is absent from both backends (`check` and `source.check`).

## Repro, first-hand READ (`docs/tk151-repros-2026-10-20/B6.py`, 2026-10-26e)

Before (identical to README §B6):

```text
sync add unrelated tuple: PathCountExceeded: path count bound exceeded: this edge would give closure row user:alice -> group:a32#member 2147483648 distinct derivation paths, over the storage limit of 21474
sync remove existing tuple: PathCountExceeded: path count bound exceeded: this edge would give closure row user:alice -> group:a32#member ...
sync remove of the poison tuple itself: PathCountExceeded: path count bound exceeded: this edge would give closure row user:alice -> group:a32#member ...
```

After (first fix revision; the recovery wording was later made type-aware, the PathCount
text is unchanged):

```text
sync add unrelated tuple: PathCountExceeded: this write (log row 255) was rolled back because the index backlog of store 'my-app' holds an earlier log row it cannot apply: row 254 (ADD group:b31#member mem
sync remove existing tuple: PathCountExceeded: this write (log row 255) was rolled back because the index backlog of store 'my-app' holds an earlier log row it cannot apply: row 254 (ADD group:b31#member mem
sync remove of the poison tuple itself: PathCountExceeded: this write (log row 255) was rolled back because the index backlog of store 'my-app' holds an earlier log row it cannot apply: row 254 (ADD group:b31#member mem
sync add on other store id: OK -> 255
rebuild_index: OK -> 'BuildReport'
sync add after rebuild: OK -> 257
bob in zz after rebuild: True
```

## Tests and sabotage, first-hand READ (2026-10-26e)

`tests/test_tk167_backlog_row_named.py`: 5 passed. Related modules (test_tk111_*,
test_tk121, test_tk123_safety_messages, test_tk123_top_level, test_tk158, test_tk165):
115 passed. `test_userdocs_examples.py` + `test_userdocs_prerelease_prose.py` +
`test_tk123_pypi_page.py` + TK167: 53 passed (the new fanout-cap.md / stall-recovery.md
example lines are executed there).

Sabotage (mutation script applied to `_store.py`, restored and byte-checked after):

```text
S1 rc= 1   (helper returns at once)
FAILED tests/test_tk167_backlog_row_named.py::test_unrelated_sync_add_names_the_backlog_row
FAILED tests/test_tk167_backlog_row_named.py::test_sync_remove_of_the_poison_tuple_names_it_too
FAILED tests/test_tk167_backlog_row_named.py::test_fanout_cap_type_is_covered_too
3 failed, 2 passed in 2.13s
S2 rc= 1   (guard inverted to row[0] != token)
FAILED tests/test_tk167_backlog_row_named.py::test_unrelated_sync_add_names_the_backlog_row
FAILED tests/test_tk167_backlog_row_named.py::test_sync_remove_of_the_poison_tuple_names_it_too
FAILED tests/test_tk167_backlog_row_named.py::test_own_row_refusal_message_is_unchanged
FAILED tests/test_tk167_backlog_row_named.py::test_fanout_cap_type_is_covered_too
4 failed, 1 passed in 2.34s
restored
```

## Docs touched

`userdocs/how-to/fanout-cap.md` (section `sync-writers-blocked-by-backlog` + example now
prints the new message checks), `userdocs/how-to/stall-recovery.md` ("Writes through a sync
instance fail too"), `userdocs/how-to/errors.md`, `userdocs/reference/exceptions.md`
(`PathCountExceeded`), `userdocs/explanation/consistency.md` (stall table row),
`CHANGELOG.md` [Unreleased] Changed. `userdocs/reference/api/store.md` and
`userdocs/how-to/async-tokens.md` already described the behaviour correctly (TK151 pass)
and mention no message text: unchanged. `PYPI_README.md`: no hit for the old text.
