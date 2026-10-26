---
id: TK170
title: paranoia full: a savepoint release fires ParanoiaGuard.after_commit and loses its writes
brief: stale ALLOW under ZANZIBAR_PARANOIA=full + savepoint on SQLite; reproduced 2026-10-22; skip after_commit when nested
pri: LATER
size: S
deps: []
related: [TK3]
parent:
labels: []
source: hand
source_hash:
created: 2026-10-22
moved: 2026-10-26e
updated: 2026-10-26e
closed: 2026-10-26e
---

Found 2026-10-22 by the TK3 fix stage (docs/tk3-cascade-ran-mark-2026-10-22.md, FIX-stage correction); re-run FIRST-HAND by the orchestrating session 2026-10-22.

With paranoia `full` on an in-memory SQLite store, RELEASING a savepoint fires `src/zanzibar/graphindex/invariants.py::ParanoiaGuard.after_commit`. That opens a fresh `Session`, which shares the `SingletonThreadPool` connection, and the writes made inside the savepoint are lost. The result is a stale ALLOW: a banned user still has `viewer`, which the set engine denies.

Observed (probe `n13.py`, from `tests/test_tk3_cascade_mark.py::G`; write a ban, then `begin_nested()`, `run_cascade(wm)`, `sp.commit()`, then the root commit; check is `user:alice viewer doc:d1`, expected False):
```
off inside sp after cascade False
off after release False
off after commit False
off fresh session False
full inside sp after cascade False
full after release True
full after commit True
full fresh session True
full control root False
```
Replacing `after_commit` with a no-op gives False after release (agent report, UNVERIFIED first-hand), so it is the cause. It probably also explains the 'no such savepoint: sa_savepoint_1' the TK3 build stage saw (REASONED).

Likely fix (REASONED): return early from `after_commit` when `sess.in_nested_transaction()`, or key it on the ROOT transaction's end. First check whether the `residue` tier's hook has the same shape. `tests/test_tk3_cascade_mark.py` N13 runs with paranoia 'off' because of this bug; switch it to 'full' once fixed. Fix the Python, never the expectation: this is an equivalence break, even though only an opt-in mode reaches it.

## Log

### 2026-10-26e

Fixed: src/zanzibar/graphindex/invariants.py::ParanoiaGuard.after_commit returns early while sess.in_nested_transaction() (SQLAlchemy dispatches after_commit on a savepoint RELEASE; the fresh Session on SingletonThreadPool rolled back the whole open txn). Repro first-hand 2026-10-26: full gave True after release (stale ALLOW) and N4d "no such savepoint"; residue/off unaffected. Pins: new tests/test_tk170_savepoint_paranoia.py (9 pass, off/residue/full); tests/test_tk3_cascade_mark.py N13, N4d, W7b, W7c now parametrized off+full (44 pass). Sabotage: early return deleted -> 5 failed 4 passed; widened to in_transaction() -> 3 failed 6 passed; literal output in the module docstring. Ran the 9 modules using install_paranoia/begin_nested/after_commit (166 passed); a wider 30-module subset run was still in progress at close (first attempt killed by the 30-min background cap at 40% with no failure). Docs: CHANGELOG [Unreleased] Fixed; userdocs/how-to/runtime-checks.md; plan doc docs/tk170-savepoint-paranoia-2026-10-26.md (FROZEN). Next: the full gate (later workflow stage).
