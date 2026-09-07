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

> 2026-09-06d — Phase B-prime cutover LANDED (user go): the tree is sole authority, this file is a one-hop note, `sync` / `ack` / lint check 13 retired.
> 🟢 Gate: ask `python scripts/gate_status.py` (all ten phases on the committed tree; re-run `lean` after any `*.md` edit, and `t2c` INCLUDES `tasks/*.md` + `HANDOFF.md`, so a tree op after the tiles stales them too).
> → What changed for you: `task.py board` opens with THIS section (`tasks/BANNER.md` is a tombstone — lint check 12 fails if it reappears); `sync` / `ack` REFUSE (rc 2) and name `comment <id> -m ...`; the ledger receipt vocabulary is `read: board only` / `read: board + note`; every re-rank and close goes through an op with `--session`.
> → To undo the whole cutover: `git revert` the 2026-09-06d commit (its message carries the line). Nothing else moved.
> 🧭 Still live from before: `P6` stays `NOW` mechanically (`ttuStarFree` part (ii), a user-owned call); `TK53` 15 appends remain; `P22` (the I14 crossable-middle loop in `bulk_build.py` is unpinned — a GREEN sabotage) and `P23` (declared-name charset asymmetry between the parsers) are the newest rows; `P24` is Lean `bulk = replay`.
> "Known live correctness bugs: 0" — ask `gate_status.py`, not this line.
> ⚠ A `close -m` / `comment -m` message with backticks inside DOUBLE quotes is command-substituted by the shell and the fragments vanish silently — single-quote it, or a heredoc, or a file (bit 2026-09-06c).
> ⚠ On a red gate, snapshot with a TEMP INDEX, never `git stash` / `git checkout --` — autocrlf rewrites LF → CRLF (trap (ee), scope doc §11.13).
> 🧭 `.scratch/tasktool/` DELETED 2026-09-07 (the `migrate.py --rebuild` landmine went with it); its record is `docs/history/tasktool-scratch-archive-2026-09-07.md`, and the nine findings it carried that were never fixed are filed as `TK57`-`TK65`.

## Still owed

Nothing. A session that runs short lists its skipped Rhythm steps here verbatim
(`docs/README.md` §7), and the next session executes them before its own work.

## Next session

- `python scripts/task.py board`, then `show <id>` for whatever it ranks first; `ready` lists
  unblocked work.
- Formal item? Read [`formal/HANDOFF.md`](formal/HANDOFF.md) first.
- End of session, in this order (`docs/README.md` §7): ledger entry in
  [`docs/history/session-log.md`](docs/history/session-log.md) with the two receipt lines,
  rewrite the banner above (first line = your session key), tree ops with `--session`,
  `python scripts/task.py lint` + `python scripts/handoff_lint.py`, then `lean`, then commit.
