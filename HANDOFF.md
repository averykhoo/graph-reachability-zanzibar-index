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

> 2026-10-07d -- **`TK127` is `NOW` (user): fix what the fresh-user install trial of the published `zanzibar-index` 0.0.2 found broken (`TK126`, `TK124`, `TK125`), then release 0.0.3 on the user's word only.** Order, release procedure, traps, trial and the `TK126` design doc: `task.py show TK127` / `show TK126`. Naming and ergonomics are parked in `TK123`. ANOTHER SESSION works in this repo: commit by path, never `git add -A` / `git stash`.
> Gate: ask `python scripts/gate_status.py`, never this note. `t2c` includes `tasks/*.md` and `HANDOFF.md`, so a tree op or a note edit after the tiles stales them too.

## Still owed

- (2026-10-05, re-stamped 2026-10-06: `TK120` has landed, so it is now actionable) `docs/architecture/derived-predicates.md` and `docs/architecture/r4bf-bulk-backfill-design.md` still name symbols `TK107` deleted; so does `docs/tk106-triage-2026-09-26.md` (`PDerivedTuplesetTTU`), now cited as `src/zanzibar/schema/::PDerivedTuplesetTTU`.

A session that runs short lists its skipped Rhythm steps here verbatim
(`docs/README.md` § 7), **stamped with its own session key**, and the next session
executes them before its own work. A bullet that survives two sessions is not a baton,
it is backlog, and it belongs in the tree — `TK97` is the check that makes that
mechanical.

## Next session

- `python scripts/task.py board`, then `show <id>` for whatever it ranks first; `ready` lists
  unblocked work.
- Formal item? Read [`formal/HANDOFF.md`](formal/HANDOFF.md) first.
- End of session, in this order (`docs/README.md` §7): ledger entry in
  [`docs/history/session-log.md`](docs/history/session-log.md) with the receipt lines (+ `asked:` if an ask is at `NEXT`/`NOW`),
  rewrite the banner above (first line = your session key), tree ops with `--session`,
  `python scripts/task.py lint` + `python scripts/handoff_lint.py`, then `lean`, then commit.
