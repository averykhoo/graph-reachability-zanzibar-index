---
id: TT-2
title: port sync's 14 sabotage cases + 57 assertions out of .scratch into the gate
brief: The only task.py surface with zero gated coverage; 'sync retires at cutover' expired when the window was extended
pri: LATER
size: M
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-08-30
moved: 2026-08-30
updated: 2026-08-30
closed:
---

`sync` is the only `task.py` surface whose test suite is still in gitignored `.scratch/`:
`sync_sabotage.py` (14 sabotage cases) and `sync_accept.py` (57 assertions). Phase A
(2026-08-29d) rescued everything else into `tests/test_tasktool.py` and skipped these two
on one explicit ground -- that `sync` retires at the Phase-B cutover, and porting a suite
for a verb with a scheduled expiry is work with a known short life.

**That ground weakened on 2026-08-30.** The trial was extended to 2026-09-06 and DELETE
was taken off the table, so `sync` is in live use for at least another week, and the
cutover that would retire it is not scheduled -- it needs a user go and may not come. The
gap is therefore live, not pending: the verb that reconciles the corpus against
`HANDOFF.md`, whose whole safety story is "no delete path and no `--force`", has zero
coverage inside the gate.

What the two scratch suites cover, per `docs/history/tasktool-proof-2026-08.md`: the
no-delete guarantee proved four independent ways (every sync mode against a deleted row;
active attempts to make it delete; an AST audit; call-graph reachability to every
`os.remove`), the six drift buckets, `--create-new` minting under the row's id, and the
`NEW-REFUSED` path for a retired id.

## Traps

⚠ **Do not port these by copying the scratch files.** They target `.scratch/tasktool/
task.py` and the `sandbox-migrated` corpus; `tests/test_tasktool.py` already established
the adaptation pattern (tmp-rooted corpora, the tracked `tasks/` as the live tree, a
missing corpus FAILS rather than skips). Follow it.

⚠ **The gate asserts zero skipped / xfailed / xpassed / deselected.** No marks.

⚠ **`ack` changed on 2026-08-29d** -- it refuses any source but `board` and takes
`--since`. Any ported case that acks a `hand`-sourced task will now hit a refusal.

## Read first

- [`docs/history/tasktool-proof-2026-08.md`](docs/history/tasktool-proof-2026-08.md) -- what the two suites proved, and the "Known limits" section that records this exact gap
- `.scratch/tasktool/sync_sabotage.py`, `.scratch/tasktool/sync_accept.py` -- the sources
- [`tests/test_tasktool.py`](tests/test_tasktool.py) -- the porting pattern, especially `sync_tree` / `seed_hashes`
- [`docs/tasktool-spec.md`](docs/tasktool-spec.md) section 4 "The reconciliation op"

## Log
