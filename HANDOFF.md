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

> 2026-10-23d -- TK151: 13 light/dark SVG diagrams on four explanation pages (graph-index, boolean-operators, two-backends, consistency) (`userdocs/_diagrams/make_diagrams.py`; regenerate, never hand-edit; pinned by `tests/test_userdocs_diagrams.py`).
> 2026-10-23b -- `TK166` (foreign token -> `ForeignToken`) and `TK164` (exceptions only from `zanzibar`; refusals are `ValueError`s; schema types public) CLOSED via ultracode; TK151 docs updated, fable-reviewed (`docs/tk151-fable-review-2026-10-23.md`, "ship after small fixes") and the review applied. **0.1.0 left: TK162 (another session), then TK151 lands last** (user); cut held, version stays 0.0.5 under `[Unreleased]`. At the cut, delete the pre-release prose `tests/test_userdocs_prerelease_prose.py` lists. Commit by path, never `git add -A` / `git stash`.
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
