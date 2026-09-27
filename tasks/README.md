# `tasks/` — the priority tree

**LIVING.** Rules that outlive any one session. **This tree is the sole authority on
what is open and how it ranks** (since the 2026-09-06 cutover, Phase B′ of
[`../docs/tree-sole-authority-spec-2026-08-29.md`](../docs/tree-sole-authority-spec-2026-08-29.md)).
State of play is the `## Banner` section of [`../HANDOFF.md`](../HANDOFF.md), the one-hop
note; the ranked view is a QUERY, `python scripts/task.py board`, which prints that banner
above the rows.

Full schema and operation contract: [`../docs/tasktool-spec.md`](../docs/tasktool-spec.md).
End-of-session write-back (the Rhythm): [`../docs/README.md`](../docs/README.md) §7.
Trial protocol and friction log, now FROZEN: [`../docs/tasktool-trial-protocol.md`](../docs/tasktool-trial-protocol.md).

## What this is

One file per task, unbounded, nothing ever dropped and nothing ever deleted. `close` is a
MOVE into `closed/`, never a delete; ids are never reused. The *session view* is the
output of `task.py board` — printed, never committed, at constant context cost no matter
how big the backlog gets. There is deliberately no `BOARD.md`: a committed view is a
second copy of a fact, and a second copy rots.

## Reading protocol

1. `python scripts/task.py board` — banner, the NOW item, the NEXT rows, each with its
   `brief`. This is the whole session-start read.
2. `python scripts/task.py show <id>` — the full item: traps, read-first list, log.
3. Then the item's own read-first list, which is the only thing that sends you into
   other documents.

`ready` lists unblocked work; `list` is capped and **says so** when it caps; `counts`
is the one home for a live corpus figure.

## Rules this tool cannot enforce

* **A user-assigned task overrides the ranking.** `pri` is the answer to "what should a
  session pick up if nobody said" — it is not an instruction that outranks the person
  asking. Nothing here checks this, so it is written down here.
* **`lint` does not know whether a task is TRUE, useful, current, or correctly ranked.**
  It converts *silently violated* into *loudly must-look*, and that is all it does. A
  green tree is not a well-ranked tree.
* **Every re-rank, close and progress goes through an op, in the session that made it.**
  `promote` / `close -m` / `touch` / `comment` / `set brief`, each with `--session <key>`
  (the ledger key). Nothing reconciles the tree against a second copy any more -- `sync`
  and `ack` retired with the board -- so a change made only in your head, or only in the
  ledger, is simply lost. `moved` is never edited by hand: `board` reads it to warn about
  neglected `NOW`/`NEXT` rows, and a hand edit is how that warning stops firing.
* **`brief` is a constraint, not a summary.** It earns its place on the board by carrying
  the thing a reader is hurt by missing — "NOT parallel-safe with `P3`" — and it is
  capped at 120 chars for exactly that reason. If it reads like a title, delete it:
  `set <id> brief ""`.

## Layout — and why `ls tasks/` undercounts

```
tasks/
  README.md          <- not a task: this file
  config.json        <- id_prefix, label vocabulary, budgets, min_tasks_parsed
  retired-ids.txt    <- spent ids, never reused, never re-minted
  <id>-<slug>.md     <- the OPEN tasks
  closed/
    <id>-<slug>.md   <- the CLOSED tasks (a `close` MOVES the file here)
```

**`ls tasks/` shows only the open half**, and about two thirds of this corpus is closed.
It also counts `README.md`, which is not a task — `Store.md_paths` and `disk_md_count`
both skip it by exact name at the top level (`NON_TASK_MD`), and `closed/` is
deliberately *not* exempt, because an exemption that survives the archive move would
hide a real record. `BANNER.md` is still in that skip list but is a TOMBSTONE: the banner
moved into `../HANDOFF.md` at the cutover, and lint check 12 fails if a `tasks/BANNER.md`
reappears (two copies drift within days).

**The only census is `python scripts/task.py counts`.** It prints open, closed, distinct
ids, retired, an independent disk recount, and the measured value `min_tasks_parsed`
should carry. Do not count files by hand and do not restate the number anywhere: lint
check 10 exists because a scanner that has gone blind reports `clean` forever.

## Filing a task

`task.py new "<title>"` allocates the next id in the `id_prefix` series by SCANNING
(open + closed + retired), never from a counter. Pass **`--id <ID>`** when the task
should not join that series — a piece of build work minted as `TK<n>` is filed forever
in the series everything else cites as a *finding*, and the id is the address, so the
miscategory is permanent.

Ids are never reused. If `new` refuses one as retired, that is the registry working:
re-filing a dead id merges two items' histories under one address.

## The `ASK-*` series — questions only the user can answer

**`ASK-<n>` is the id series for work only the USER can do**: a fact to find, a requirement
to gather, a priority call. File it with `task.py new --id ASK-1 "<question>"`. It is not a
schema feature — it is the `--id` escape above used deliberately, exactly as `P` / `R6` /
`HS` / `ZT` are. Decided with the user 2026-09-22; the build work is `TK96`.

* **`LATER` by default; `NEXT` means "remind me every session."** A session that sees an
  `ASK-*` at `NEXT` must raise it with the user, in chat, at least once that session.
  `NEXT` is capped at 3, so there are at most three standing nags.
* **The nag is mechanical (`TK96`, 2026-09-27).** While any open `ASK-*` sits at `NEXT`,
  the newest session-log entry must carry `asked: ASK-<n>[, ASK-<m>]` naming EVERY one of
  them, or `handoff_lint.py::check_session_receipt` turns `verify.sh lean` red. `asked:
  none` is red then (an honest "did not ask" is exactly what the receipt refuses); to stop
  the nag, demote the row to `LATER`. With no ask at `NEXT` the line is optional.
* **Where to see them.** `python scripts/task.py asks` lists the open ones oldest first
  (by `created`), with age in days, what each one blocks, and a flag on the `NEXT` ones.
  `board` always prints one line under `ready`: `asks   N open, oldest D days` (plus
  `K at NEXT -- raise in chat` when K is nonzero).
* **Keep it narrow.** An engineering call the model should simply take — "mechanise this
  ratchet or not" — is a plain `TK` row. [`../CLAUDE.md`](../CLAUDE.md) § "Who decides" is
  the test. A series that accepts everything is a series nobody reads.
* **A blocked row declares `deps: [ASK-<n>]`.** `ready` then excludes it automatically, and
  `close` sweeps the id out of every `deps` cell — so answering the question unblocks the
  work in one op. An ASK with no dependents is just a question; one with dependents is a
  hard blocker, and the dep graph tells them apart with no new field.
* **Never a `## Still owed` bullet.** A question for the user is durable by nature; that
  section of [`../HANDOFF.md`](../HANDOFF.md) is a depth-one baton, not a backlog (`TK97`).
