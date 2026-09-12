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

> 2026-09-12 — **`P6` is BLOCKED ON A USER DECISION, not on proof effort.** `TtuStarFreeW` (`GraphIndex/TtuStarWide.lean:72-76`) carries no `isDerived … = false` conjunct, so it admits a TTU through-shape that is DERIVED — and the probe measured that no node on the leaf-routed write list can be bridged there (`leafBridged := false`, `bridgesOnLeafRouted := 0` vs `bridgesOnPublicKeyed := 1`, `legEdgesIntoLeaf := 1`). The only bridgeable node is the PUBLIC one, which `P6` forbids. **So part (ii) cannot inhabit the predicate part (iv) already landed and audit-pinned**; (iv) was scheduled on decidability alone. Second blocker: the remove leg provably cannot retract a bridge and NO retraction machinery exists tree-wide. Evidence: `task.py show P6` (two `2026-09-12` entries) + `formal/probes/p6_inbridge_stability_2026-09-12.lean` (tracked, re-run first-hand, `rc=0`).
> 🟢 Gate: ask `python scripts/gate_status.py` (re-run `lean` after any `*.md` edit, and `t2c` INCLUDES `tasks/*.md` + `HANDOFF.md`, so a tree op after the tiles stales them too).
> ⚠ **Writing a figure into a live doc now needs one of four escapes** — a fenced block, a backticked/quoted span, a `YYYY-MM-DD` key on the line, or a file whose banner declares its body provenance. The remedy on a red is to **DELETE the number and point at its home**, never to update it. Out of scope: `docs/history/`, `docs/specs/`, `docs/architecture/`, `formal/`, and a task file's `## Log`.
> ⚠ **A sabotage certifies ONE test; sweep the whole module with mutations.** Now THREE consecutive additions whose sweep found what the single sabotage missed: `TT-8` (7 of 12 weakenings left everything green — the clause guarded one fence shape, not the fence *grammar*) and `GL-1` (10 of 11 caught; the 11th, stealing a stale lock by `unlink` instead of `rename`, was **INERT** — no behavioural test could see it). `GL-1` also caught its own INSTRUMENT: one mutation appeared to redden until it turned out to be dying of a `TypeError`, not of the property. `docs/sabotage-procedure.md` §"Sweep the TEST MODULE with mutations".
> ⚠ **`FoldAdmits`: 21 of 24 sites move, THREE MUST STAY** (`PROOF_STATUS.md:4895`). **2026-09-12 narrowed `TK67`:** the trap is SOUND and the symbol EXISTS — `ReachedByRulesAdmitted.step` is `RulesComplete.lean:113` with `hadm` at `:115` (used at 8+ sites); only the recorded line `:91` is stale, and a subagent that reported "there is no `step` constructor" would have deleted a valid trap. Stay-sites: `RulesComplete.lean:115`, `RestrictBase.lean:470`, `:531`.
> ⚠ **Two gate runs at once make a PASSING phase report `EXIT=0` under another run's failing log** — via a loop that leaves an orphan (2026-09-08b, `25 failed`) or via plain overlap (2026-09-10, `60 failed`). Both need only two writers and one filename. `verify.sh` now REFUSES a second concurrent run (ledger: `FAILED … rc=1 refused=lock-held`) and the recipe uses `mktemp`, never a fixed path — but still **one phase per command**. `docs/gate-runbook.md` §"The recipe".
> 🧭 `TK66`: a sweep found **17 forward-binding directives that live only in `formal/history/`** and no live file surfaces (`P4`'s was one). The table on that row is a subagent's, explicitly UNVERIFIED — read the line before acting. Now probably an EXTENSION of check 14 rather than its own mechanism (noted on the row).
> → **`P6` stays `NOW` but is NOT startable** — it needs the Wall-1 scope call first (narrow `TtuStarFreeW` to untainted through-shapes / model the entity-middle half / teach minted leaves), each with its audited-pin cost on the row. `R6` is `NEXT` and IS startable. `TK57`–`TK65` and `TK53` are DONE; `TK62` stays DECLINED.
> → To undo the whole cutover: `git revert` the 2026-09-06d commit (its message carries the line). Nothing else moved.
> 🧭 Still live from before: `P22` (the I14 crossable-middle loop in `bulk_build.py` is unpinned — a GREEN sabotage) and `P23` (declared-name charset asymmetry between the parsers) are the newest rows; `P24` is Lean `bulk = replay`. ⚠ **A counting-unit reminder, earned twice on 2026-09-12:** `P6`'s cone is ONE graph with three honest numbers — union of the six reverse cones excl. the root aggregator = **42**, minus all six targets = **38**, together WITH the targets = **44**. State the unit or the figure is meaningless.
> "Known live correctness bugs: 0" — ask `gate_status.py`, not this line.
> ⚠ A `close -m` / `comment -m` message with backticks inside DOUBLE quotes is command-substituted by the shell and the fragments vanish silently — single-quote it, or a heredoc, or a file (bit 2026-09-06c).
> ⚠ On a red gate, snapshot with a TEMP INDEX, never `git stash` / `git checkout --` — autocrlf rewrites LF → CRLF (trap (ee), scope doc §11.13).
> ⚠ **`docs/specs/` is frozen at landing and NOTHING walks it** (`docs/README.md` §3), so a dated append into a spec body looks legal and is not — implementation divergences go to `docs/spec-deviations.md`. That is why `TK35`/`TK36` were re-homed on 2026-09-10 rather than written where the adjudication pointed.

## Still owed

- **The ledger receipt vocabulary still has no token for "entered via `show`"** (carried
  from 2026-09-07b, when a session entered at `show TK57` and had to write the nearest
  false token with a caveat). Unfiled; file it or extend
  `handoff_lint.py::check_session_receipt`'s vocabulary.
- **A percentage still has no mechanical guard** — now FILED as `GC-1`. The four
  contradictory copies are deleted and point at `test_report_cell_coverage`; the check that
  would have caught them is still owed, and the row records why widening is not free.
- **`MIN_TESTS_ALL` is ratcheted BY HAND, and the third consecutive raise again found
  pre-existing headroom** — i.e. tests that could have been deleted green. Size and
  provenance are in the floor's own comment in `formal/verify.sh`. `tasks/config.json`
  solved this mechanically; the gate has no equivalent, and a session that only ADDS
  tests never sees a red to remind it. Unfiled.
- **`TT-8` left one behaviour observed but unpinned:** a fence *inside* the banner section
  now counts as banner content, so such a corpus fails the line cap rather than truncating.

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
