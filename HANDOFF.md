# HANDOFF — the one-hop note

LIVING. What is true now, the next session's first steps, and facts not derivable from the code.
**The board is the record engine's** (`context-engine task list`; adopted 2026-11-03, context-engine
CE-167), and this note keeps no copy of it. Formal execution state is in
[`formal/HANDOFF.md`](formal/HANDOFF.md); durable rules and the gate in [`CLAUDE.md`](CLAUDE.md); doc
conventions in [`docs/README.md`](docs/README.md). The pre-engine note, with its banner history, is
[`docs/archive/HANDOFF.md`](docs/archive/HANDOFF.md).

**A user-assigned task overrides the ranking.** Do not re-rank at session start: work the task,
then re-rank once at the close (`context-engine task promote <id> <pri>`).

## Banner (2026-11-03a)

- The record engine (context-engine @ 309641b) is adopted on branch `ce-cutover` (off `4826a01`): the board,
  the decisions and the session ledger go through `context-engine`. Not merged, not pushed, no tag.
- Board: each task.py record is an engine record (`TK185` is `TK-185`; P, R6, ZT and the rest took
  `TK-186` up; old ids are aliases). NOW: TK-185, the decided 0.1.3 batch; tag 0.1.3 only on the user's word.
- Owed to the owner: the call on merging `ce-cutover`, the go to push (the gate first, then a CI watcher),
  and the charter and criteria (templates unfilled).

## Facts

- 0.1.2 is the newest release (tag `v0.1.2` on `b743587`, on PyPI). A tag is a release
  (`.github/workflows/publish.yml`): tag 0.1.3 only on the user's word.
- Do not mirror a future `[Unreleased]` heading into `userdocs/reference/changelog.md` under that word.
- Gate: ask `python scripts/gate_status.py`, never this note. `t2c` includes `tasks/` and this note,
  so an engine op on a task or a note edit after the tiles stales them; `context.toml` and
  `docs/ledger/` do not.

## Still owed

Nothing.

## Next session

- `context-engine orient` (the hook prints it), `context-engine session start`, then
  `context-engine task show <id>` for what it ranks first.
- Formal item? Read [`formal/HANDOFF.md`](formal/HANDOFF.md) first.
- End of session: the engine's clean close (`docs/runbooks/procedures.md` § Clean close): the gate
  (CLAUDE.md § Gate), `session close`, `banner set`, commit by path.
