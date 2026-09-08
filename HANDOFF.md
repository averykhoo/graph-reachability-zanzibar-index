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

> 2026-09-08b — `TK58` LANDED: **`handoff_lint.py::check_restated_counts` refuses a restated corpus count** (`N checks` / `N open tasks` / `N tests`) in `CLAUDE.md`, `HANDOFF.md`, top-level `docs/*.md` and `tasks/*.md`, riding 4f. `ZT-P3-5` finally has a mechanism, and six live rotted figures were swept before it landed.
> 🟢 Gate: ask `python scripts/gate_status.py` (re-run `lean` after any `*.md` edit, and `t2c` INCLUDES `tasks/*.md` + `HANDOFF.md`, so a tree op after the tiles stales them too).
> ⚠ **Writing a figure into a live doc now needs one of four escapes** — a fenced block, a backticked/quoted span, a `YYYY-MM-DD` key on the line, or a file whose banner declares its body provenance. The remedy on a red is to **DELETE the number and point at its home**, never to update it. Out of scope: `docs/history/`, `docs/specs/`, `docs/architecture/`, `formal/`, and a task file's `## Log`.
> ⚠ **A sabotage certifies ONE test; sweep the whole module with mutations.** Ten weakenings of the new check: nine reddened the test that claimed to guard them, and the tenth broke the check with every test still green (one property, three patterns, one asserted). The rule is `docs/sabotage-procedure.md` §"Sweep the TEST MODULE with mutations" — apply it to the next check anyone adds.
> ⚠ **`formal/HANDOFF.md` and `tasks/P6` said `FoldAdmits` moves "in lockstep"; the correction (`PROOF_STATUS.md:4897`) says 21 of 24 sites move and THREE MUST STAY.** Both live sites annotated 2026-09-07b; verifying the three against the current Lean tree is `TK67`. A session following the formal note would have moved sites that must not move.
> ⚠ **Never loop gate phases in one command.** The harness kills the SHELL at the cap, not its `pytest` child; the next phase then overlaps with the orphan, shares its log file, and a PASSING phase reports `EXIT=0` under a log ending `25 failed`. Full trap in `docs/gate-runbook.md` §"The recipe" (hit 2026-09-08b).
> 🧭 `TK66`: a sweep found **17 forward-binding directives that live only in `formal/history/`** and no live file surfaces (`P4`'s was one). The table on that row is a subagent's, explicitly UNVERIFIED — read the line before acting. Now probably an EXTENSION of check 14 rather than its own mechanism (noted on the row).
> → The `TK57`–`TK65` sweep is DONE; `TK62` (figure-equality) stays DECLINED, reasons on its row. Next ranked work is what the board ranks: `P6` is `NOW`, `R6`/`TK53` are `NEXT`.
> → To undo the whole cutover: `git revert` the 2026-09-06d commit (its message carries the line). Nothing else moved.
> 🧭 Still live from before: `P6` stays `NOW` mechanically (`ttuStarFree` part (ii), a user-owned call); `TK53` 15 appends remain; `P22` (the I14 crossable-middle loop in `bulk_build.py` is unpinned — a GREEN sabotage) and `P23` (declared-name charset asymmetry between the parsers) are the newest rows; `P24` is Lean `bulk = replay`.
> "Known live correctness bugs: 0" — ask `gate_status.py`, not this line.
> ⚠ A `close -m` / `comment -m` message with backticks inside DOUBLE quotes is command-substituted by the shell and the fragments vanish silently — single-quote it, or a heredoc, or a file (bit 2026-09-06c).
> ⚠ On a red gate, snapshot with a TEMP INDEX, never `git stash` / `git checkout --` — autocrlf rewrites LF → CRLF (trap (ee), scope doc §11.13).
> 🧭 `.scratch/tasktool/` DELETED 2026-09-07 (the `migrate.py --rebuild` landmine went with it); its record is `docs/history/tasktool-scratch-archive-2026-09-07.md`, and the nine findings it carried that were never fixed are filed as `TK57`-`TK65`.

## Still owed

- **The ledger receipt vocabulary still has no token for "entered via `show`"** (carried
  from 2026-09-07b, when a session entered at `show TK57` and had to write the nearest
  false token with a caveat). Unfiled; file it or extend
  `handoff_lint.py::check_session_receipt`'s vocabulary.

A session that runs short lists its skipped Rhythm steps here verbatim
(`docs/README.md` §7), and the next session executes them before its own work.

## Next session

- `python scripts/task.py board`, then `show <id>` for whatever it ranks first; `ready` lists
  unblocked work.
- Formal item? Read [`formal/HANDOFF.md`](formal/HANDOFF.md) first.
- End of session, in this order (`docs/README.md` §7): ledger entry in
  [`docs/history/session-log.md`](docs/history/session-log.md) with the two receipt lines,
  rewrite the banner above (first line = your session key), tree ops with `--session`,
  `python scripts/task.py lint` + `python scripts/handoff_lint.py`, then `lean`, then commit.
