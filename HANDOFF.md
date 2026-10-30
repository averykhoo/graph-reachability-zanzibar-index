# HANDOFF — the one-hop note

**The task tree is the sole authority on open work** (since the 2026-09-06 cutover, Phase B′).
Start with `python scripts/task.py board`, which prints the banner below and then the ranked
open items as a query; `show <id>` is the per-item read. This file is one hop: the banner, what
is still owed, and where to go next — no row table, no item blocks. Formal execution state is
in [`formal/HANDOFF.md`](formal/HANDOFF.md); durable rules and the gate in
[`CLAUDE.md`](CLAUDE.md); doc conventions and the end-of-session Rhythm in
[`docs/README.md`](docs/README.md) §7 (where things live: §8).

**A user-assigned task overrides the ranking.** Do not re-rank at session start: work the
task, then re-rank once at write-back (`task.py promote <id> <pri> --session <key>`).

## Banner

> 2026-10-30c -- **0.1.2 cut prepared** (`__version__` 0.1.2, CHANGELOG `[0.1.2] - 2026-10-30`, userdocs release notes) and pushed for CI. `TK178` (NOW): tag `v0.1.2` ONLY on the user's word, then babysit, PyPI, install trial.
> 2026-10-30b -- **0.1.1 released** (tag `v0.1.1` on `047bc0b`, on PyPI; `TK174` closed): `TK172` lag fix, all five `TK173` doc gaps, and the gate-found `TK175` self-parent crash. The 0.1.1 install trial found one BROKEN, `TK176` (`Store(sync=None)` silently async): **fixed on master under `[Unreleased]`, not released**. Before 0.1.2 (user): strict public args `TK179`, ruff+mypy in the gate `TK182`, messages `TK177`, stranger tests `TK180`/`TK181` -- all CLOSED. `TK178` (NOW) = cut 0.1.2 and tag on the user's word.
> 2026-10-30 -- **0.1.0 released** (tag `v0.1.0` on `556011e`, on PyPI; `TK171` closed). The pre-tag publish dry run caught a broken wheel smoke step (fixed + pinned). The install trial found one low-severity bug, `TK172` (`Store.lag()` stale across instances): **fixed on master under `[Unreleased]`, not yet released**. `TK174` (NOW) = cut 0.1.1 and tag on the user's word. Doc gaps: `TK173`.
> 2026-10-28 -- **`TK163` and `TK169` closed and folded into 0.1.0 (user: "nice to have" before the tag)**. A post-commit `InvariantViolation` now reaches the caller as itself and the `Store` stays usable; public docstrings are leak-free and guarded (`tests/test_tk169_public_docstrings.py`).
> 2026-10-26e -- 0.1.0 prepared; `TK170` / `TK165` / `TK167` / `TK161` / `TK151` closed. Do not mirror a future `[Unreleased]` heading into `userdocs/reference/changelog.md` under that word.
> 2026-10-23d -- TK151: 13 light/dark SVG diagrams on four explanation pages (graph-index, boolean-operators, two-backends, consistency) (`userdocs/_diagrams/make_diagrams.py`; regenerate, never hand-edit; pinned by `tests/test_userdocs_diagrams.py`).
> 2026-10-23b -- `TK166` (foreign token -> `ForeignToken`) and `TK164` (exceptions only from `zanzibar`; refusals are `ValueError`s; schema types public) CLOSED via ultracode; TK151 docs updated, fable-reviewed (`docs/tk151-fable-review-2026-10-23.md`, "ship after small fixes") and the review applied. 0.1.0 was then: TK162, then TK151 last (TK162 closed 2026-10-26); cut held, version stays 0.0.5 under `[Unreleased]`. At the cut, delete the pre-release prose `tests/test_userdocs_prerelease_prose.py` lists. Commit by path, never `git add -A` / `git stash`.
> Gate: ask `python scripts/gate_status.py`, never this note. `t2c` includes `tasks/*.md` and `HANDOFF.md`, so a tree op or a note edit after the tiles stales them too.

## Still owed

Nothing.

A session that runs short lists its skipped Rhythm steps here verbatim
(`docs/README.md` § 7), **stamped with its own session key**, and the next session
executes them before its own work. A bullet that survives two sessions is not a baton,
it is backlog, and it belongs in the tree. `handoff_lint.py::check_still_owed_fresh`
(`TK97`) makes that mechanical: a bullet older than the previous ledger entry is RED, and
re-stamping does not reset its age.

## Next session

- `python scripts/task.py board`, then `show <id>` for whatever it ranks first; `ready` lists
  unblocked work.
- Formal item? Read [`formal/HANDOFF.md`](formal/HANDOFF.md) first.
- End of session, in this order (`docs/README.md` §7): ledger entry in
  [`docs/history/session-log.md`](docs/history/session-log.md) with the receipt lines (+ `asked:` if an ask is at `NEXT`/`NOW`),
  rewrite the banner above (first line = your session key), tree ops with `--session`,
  `python scripts/task.py lint` + `python scripts/handoff_lint.py`, then `lean`, then commit.
