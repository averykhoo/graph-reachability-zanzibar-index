# `tasks/` — the priority tree

**LIVING.** Rules that outlive any one session. State of play is in
[`BANNER.md`](BANNER.md); the ranked view is a QUERY, `python scripts/task.py board`.

Full schema and operation contract: [`../docs/tasktool-spec.md`](../docs/tasktool-spec.md).
Trial protocol and friction log: [`../docs/tasktool-trial-protocol.md`](../docs/tasktool-trial-protocol.md).

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
* **`ack` must be a session's LAST step.** It stamps `source_hash` with what the source
  says AT ACK TIME, so acking and then editing the source records an acknowledgement of
  text nobody reviewed. Pass `--since <digest>` (the digest the drift report showed) and
  a mismatch is announced. The flag is opt-in; the rule is not.
* **`brief` is a constraint, not a summary.** It earns its place on the board by carrying
  the thing a reader is hurt by missing — "NOT parallel-safe with `P3`" — and it is
  capped at 120 chars for exactly that reason. If it reads like a title, delete it:
  `set <id> brief ""`.

## Layout — and why `ls tasks/` undercounts

```
tasks/
  BANNER.md          <- not a task: the must-read session state
  README.md          <- not a task: this file
  config.json        <- id_prefix, label vocabulary, budgets, min_tasks_parsed
  retired-ids.txt    <- spent ids, never reused, never re-minted
  <id>-<slug>.md     <- the OPEN tasks
  closed/
    <id>-<slug>.md   <- the CLOSED tasks (a `close` MOVES the file here)
```

**`ls tasks/` shows only the open half**, and about two thirds of this corpus is closed.
It also counts `BANNER.md` and `README.md`, which are not tasks — `Store.md_paths` and
`disk_md_count` both skip them by exact name at the top level (`NON_TASK_MD`), and
`closed/` is deliberately *not* exempt, because an exemption that survives the archive
move would hide a real record.

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
