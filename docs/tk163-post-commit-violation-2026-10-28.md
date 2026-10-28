# TK163: post-commit InvariantViolation reaches the caller as itself (2026-10-28)

> **FROZEN 2026-10-28 — provenance, not a living document.** Status lines below are
> as-of-then and several may now be false; live state: `HANDOFF.md` + the session
> ledger. Corrections are appended dated at the top, never edited into the body.

**Correction 2026-10-28 (orchestrator, RAN):** the review found that a violation parked
by a commit that bypasses `Store` on its session (`zanzibar.store.rebuild_index(store.session, ...)`,
the recovery the stall message names) stayed parked and surfaced on the next `Store` call.
`src/zanzibar/store/build.py::build_index` / `rebuild_index` now call
`raise_post_commit_violation(session)` after their commit. Pin:
`tests/test_tk163_post_commit_violation.py::test_rebuild_index_on_a_store_session_raises_its_own_violation`;
sabotage (both calls -> `pass`): `1 failed, 6 passed`, `DID NOT RAISE InvariantViolation`.
A direct `store.session.commit()` by the caller is still not re-raised until the next
`Store` commit (REASONED: not a supported path; the session belongs to the Store).

Provenance labels: **READ** = read first-hand in the tree; **RAN** = run first-hand with
the output quoted; **REASONED** = inference not separately executed.

## 1. Repro (RAN, 2026-10-28)

`docs/tk151-repros-2026-10-20/B1.py`, run unchanged against the pre-fix tree
(`PYTHONPATH=src`, SQLAlchemy 2.0.51), reproduced the TK151 B1 finding exactly:

```text
caller type: sqlalchemy.exc.InvalidRequestError
caller msg : This session is in 'committed' state; no further SQL can be emitted within this transaction.
isinstance InvariantViolation: False
__cause__  : None
__context__: InvariantViolation | store='s' [post-commit] SABOTAGE post-commit
session state: in_transaction = True | _transaction._state = SessionTransactionState.COMMITTED
check b RAISED InvalidRequestError: This session is in 'committed' state; no further SQL can be emitted within this transaction.
add c RAISED InvalidRequestError: This session is in 'committed' state; no further SQL can be emitted within this transaction.
refresh RAISED InvalidRequestError: This session is in 'committed' state; no further SQL can be emitted within this transaction.
fresh Store sees b: True | a: True
control pre-commit caller type: InvariantViolation | store='s2' [pre-commit] SABOTAGE pre-commit
control: b stored? False | store usable, add c -> 3
```

After the fix, same script:

```text
caller type: zanzibar.graphindex.invariants.InvariantViolation
caller msg : store='s' [post-commit] SABOTAGE post-commit -- found AFTER the commit: the transaction IS committed (tuple log and index); nothing was rolled back
isinstance InvariantViolation: True
__cause__  : InvariantViolation("store='s' [post-commit] SABOTAGE post-commit")
session state: in_transaction = False | _transaction._state = None
check b -> True
add c -> 3
refresh -> None
fresh Store sees b: True | a: True
```

(The script's later `st.session.close()` probe now raises `DetachedInstanceError`: closing
the session under a live `Store` is not a supported operation and was only a workaround
probe for the old bug. REASONED, not pursued.)

## 2. Root cause (READ)

- `src/zanzibar/graphindex/invariants.py::install_paranoia` registers
  `_post_commit_check` on the session's `after_commit` event; it is the ONLY
  `after_commit` listener in `src/zanzibar` (grep, 2026-10-28).
- `src/zanzibar/graphindex/invariants.py::ParanoiaGuard.after_commit` ran
  `check_invariants` in a fresh session and let the tagged `InvariantViolation` escape
  from inside SQLAlchemy's hook. SQLAlchemy sets the transaction to COMMITTED, dispatches
  `after_commit`, and only then closes it, so the raise left the session stuck in
  COMMITTED.
- `src/zanzibar/store/_store.py::Store._write` (second `except Exception` arm) then called
  `session.rollback()`, which SQLAlchemy refuses in COMMITTED state: the new
  `InvalidRequestError` replaced the violation (which survived only as `__context__`),
  and every later SQL on that session raised the same.
- The same pattern sat at `Store._catch_up`'s two commits and at the bootstrap commit in
  `Store.__init__` (reachable when a guard from an earlier `Store` on the same session
  exists). `Store._record_stall` commits too, inside its own `except`.

**Residue is NOT affected (READ + RAN):** `ParanoiaGuard.after_commit` returns before
any check unless `paranoia_at_least(level, PARANOIA_FULL)`; pinned by
`tests/test_tk163_post_commit_violation.py::test_residue_runs_no_post_commit_recheck`.

## 3. Decision and reasoning (REASONED)

**The Store stays usable after a post-commit violation; the caller gets
`InvariantViolation` once `commit()` has returned.** Refusing later calls was considered
and rejected:

1. Nothing a refusal could protect is protected: the state is committed, any other
   `Store`/session serves it already, and no rollback can undo it.
2. Under `full`/`fixpoint` the next write's PRE-commit pass re-checks the whole store
   (`check_invariants` + `verify_outbox_deltas`), so a state that is still broken refuses
   that write with the ordinary fail-closed path. Writes are already gated; a second gate
   would only add a state machine (and a way to un-brick it) for no extra protection.
3. The previous "unusable" state was an accident of SQLAlchemy's session machinery, not a
   design; the userdocs had to teach a workaround helper for it.

**The deferral is opt-in per session** (`defer_post_commit_violations`, set by `Store`
before its bootstrap commit). A raw session with a guard and no opt-in keeps the old
raise-from-`commit()`: an unconditional deferral would park the violation where no caller
ever pops it, silently weakening every raw-session (test) user of paranoia. Pinned by
`test_a_raw_session_that_did_not_opt_in_still_raises_from_commit`.

**Async (`catch_up`)**: the re-raise runs inside `_catch_up`'s `try`, so the existing
arm rolls back (a no-op on the clean session) and records a stall, as for any
`catch_up` failure; the batch IS applied, so the next `catch_up` at the head clears the
stall (TK165 branch). Consistent with "any catch_up failure records a stall"; pinned in
`test_async_catch_up_raises_invariantviolation_and_stays_usable`.

**`self.wm` is advanced even on a violation**: the rows are committed, and leaving the
delta verifier's baseline behind would make every later pre-commit pass re-verify this
transaction's range.

## 4. The fix (READ, as landed)

- `src/zanzibar/graphindex/invariants.py`: `defer_post_commit_violations(session)`,
  `raise_post_commit_violation(session)` (pop the parked list, raise the first, later ones
  as notes); `ParanoiaGuard.after_commit` parks a re-worded violation (`... found AFTER the
  commit: the transaction IS committed (tuple log and index); nothing was rolled back`,
  `__cause__` = the tagged original) when the session opted in, else re-raises as before.
- `src/zanzibar/store/_store.py`: `Store._commit` (commit + re-raise), used at the bootstrap
  commit and both `_catch_up` commits; `Store._write` re-raises AFTER its `try` so neither
  the rollback nor the evaluator rebuild runs for a committed write;
  `Store._record_stall` attaches a late violation to the original exception as a note;
  `Store.__init__` docstring "Fail-closed" paragraph extended to the post-commit case.
- userdocs: `how-to/runtime-checks.md` (When a check fails: known-limitation text and the
  `is_invariant_violation` helper removed, fixed behaviour described),
  `reference/configuration.md`, `reference/exceptions.md`, `explanation/assurance.md`,
  `how-to/errors.md`.

## 5. Sabotage (RAN, 2026-10-28)

Each mutation edited into `invariants.py`, the new module run, then reverted
(restored: `6 passed`):

| mutation | result |
|---|---|
| deferral removed (`if not sess.info.get(...)` -> `if True:`) | `4 failed, 2 passed`; each failure chains `InvariantViolation: store='s' [post-commit] SABOTAGE post-commit` -> `sqlalchemy.exc.InvalidRequestError: This session is in 'committed' state; ...` |
| deferral unconditional (`-> if False:`) | `1 failed, 5 passed`: the raw-session control, `Failed: DID NOT RAISE InvariantViolation` |
| parked violation swallowed (`pending = ... and None`) | `4 failed, 2 passed`, each `Failed: DID NOT RAISE InvariantViolation` |

## 6. Test results (RAN, 2026-10-28)

- `tests/test_tk163_post_commit_violation.py`: `6 passed`.
- With `test_userdocs_examples`, `test_userdocs_prerelease_prose`, `test_userdocs_diagrams`,
  `test_userdocs_refused_shapes`, `test_tk123_pypi_page`: `61 passed`.
- Store / paranoia / invariants / stall / savepoint modules plus `test_userdocs_build`
  (27 modules, listed in the worker report): `424 passed`.
- The full gate (`formal/verify.sh`) is NOT run here; the orchestrator runs it.

## 7. Next action

Orchestrator: CHANGELOG "Fixed" line, gate, close TK163 naming this file.
