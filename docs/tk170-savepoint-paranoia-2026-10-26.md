# `TK170` — a savepoint release ran the paranoia guard's post-commit check

> **FROZEN 2026-10-26 — provenance, not a living document.** Status lines below are
> as-of-then and several may now be false; live state: `HANDOFF.md` + the session
> ledger. Corrections are appended dated at the top, never edited into the body.

Frozen at `TK170`'s close (session `2026-10-26e`, release-0.1.0 workflow). Found by the
TK3 fix stage (`docs/tk3-cascade-ran-mark-2026-10-22.md`); the row's 2026-10-22 text is
the first report.

## 1. Repro (first-hand PROBE, 2026-10-26)

Probe: the N13 / N4d scenarios of `tests/test_tk3_cascade_mark.py` run at each paranoia
level before the fix (a ban written and not cascaded; `begin_nested()`, `run_cascade(wm)`,
`sp.commit()`, root commit; `check user:alice viewer doc:d1`, truth False). Observed:

```
off inside sp after cascade False
off after release False
off after commit False
off N4d ok, owed []
residue inside sp after cascade False
residue after release False
residue after commit False
residue N4d ok, owed []
full inside sp after cascade False
full after release True
full after commit True
full N4d raised OperationalError (sqlite3.OperationalError) no such savepoint: sa_savepoint_1
```

So `residue` was NOT affected (its `after_commit` returned before opening a session), and
`full` (hence `fixpoint`) lost the savepoint's writes: a stale ALLOW against the set engine.

## 2. Cause (first-hand READ)

- SQLAlchemy 2.0.51 `sqlalchemy/orm/session.py::SessionTransaction.commit` dispatches
  `after_commit` when `self._parent is None or self.nested`, i.e. on a savepoint RELEASE
  too, and does so BEFORE `self.close()`, so `session.in_nested_transaction()` is still True
  during the event for a release and False for the root commit.
- `src/zanzibar/graphindex/invariants.py::ParanoiaGuard.after_commit` (full tier) opened
  `Session(sess.get_bind())`. On in-memory SQLite (`SingletonThreadPool`) that is the
  caller's own DBAPI connection; the fresh session's close issues a rollback, which ends
  the WHOLE open transaction, savepoints included (REASONED from the observed output: the
  ban and the cascade both vanished, the committed grant survived). On a pooled bind
  (PostgreSQL, file SQLite) the re-check would merely read pre-transaction state (REASONED,
  not probed).
- The release also emptied the cheap tier's I14 sets, which the guard's own `__init__`
  comment says only a COMMIT may empty (first-hand READ).

## 3. Fix

`ParanoiaGuard.after_commit` returns immediately while `sess.in_nested_transaction()`.
The root commit's behaviour is unchanged. `before_commit` still runs on a release (it
checks the live transaction, does not open a session, and `test_n4c` pins that a release
is not refused); no change there. No other `after_commit` listener exists in `src/`
(first-hand grep 2026-10-26).

## 4. Pins and sabotage (first-hand, 2026-10-26)

- New `tests/test_tk170_savepoint_paranoia.py` (9 tests, `off`/`residue`/`full`): a
  released savepoint keeps its cascade; an outer rollback after an inner release works;
  the post-commit re-check runs on the root commit only and a release keeps the I14 sets.
- `tests/test_tk3_cascade_mark.py` N13, N4d, W7b, W7c, which ran at `off` only because of
  this bug, are now parametrized over `off` and `full` (44 tests, all pass).
- Sabotage 1, early return deleted: `5 failed, 4 passed` (stale ALLOW after the release;
  `no such savepoint: sa_savepoint_1`; release ran the re-check; release emptied the I14
  sets). Sabotage 2, guard widened to `sess.in_transaction()` (skips the root commit too):
  `3 failed, 6 passed` (`the root commit did not empty the I14 sets`). Literal output in
  the new module's docstring.
- Ran: every `tests/test_*.py` mentioning `savepoint` or `paranoia` (see the row's close
  note for the count). Not the full gate; a later workflow stage runs it.
