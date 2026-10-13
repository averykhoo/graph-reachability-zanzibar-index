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

> 2026-10-13 -- **Assurance batch: 10 rows closed** (`TK99`, `AW-1`, `TK62`, `TK66`, `TK97`, `TK98`, `TK86`, `TK100`, `TK110`, `GC-1`). Floors now ratchet in `doc_counts --generate`; `handoff_lint` checks Still-owed age and accepts `read: show <id>`. `TK3` narrowed (cascade-ran mark wanted, unbuilt; census next); `TK85` -> SOMEDAY; `HS-5` next: freeze closed-row ACTIVE-PLAN docs. Next: `TK134` (NOW). ANOTHER SESSION may work in this repo: commit by path, never `git add -A` / `git stash`.
> Gate: ask `python scripts/gate_status.py`, never this note. `t2c` includes `tasks/*.md` and `HANDOFF.md`, so a tree op or a note edit after the tiles stales them too.

## Still owed

- (2026-10-13) `CLAUDE.md` "Start here" lists only `read: board only` / `read: board + note`; add
  `/ read: show <id>` (`TK98`; mind the `CLAUDE.md` byte cap). Left by the records subagent.

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
