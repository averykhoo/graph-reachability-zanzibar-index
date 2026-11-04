---
type: Task
id: TK-301
title: 'CI: an engine-install-and-lint job in gate.yml, pinned to the engine ref'
brief: Own change, CI config only; pin the same engine ref CLAUDE.md names; sabotage it red first (DEC-14)
pri: LATER
state: open
deps: []
source: session 2026-11-04a
created: 2026-11-04
moved: 2026-11-04a
updated: 2026-11-04a
---

Add an engine-install-and-lint job to zanzibar's CI (`.github/workflows/gate.yml`), as its own change. Decided by the owner: DEC-14 (answering context-engine `ASK-30`, "30 ok").

Since the 2026-11-03 adoption (context-engine CE-167), `context-engine lint` checks this repo's records (tasks, decisions, ledger, the contract, the routes), but CI neither installs the engine nor runs it, so a red record is only caught by a local gate run.

- The job installs the engine into its own env, never this repo's (the contract's § Environment), pinned to the same ref `CLAUDE.md` § The record engine names (today `309641bd84837277ef9ddc7251b851a4e815dbe5`), then runs `python -m context_engine lint` from the repo root.
- One change of its own: a CI config change, kept off feature branches (`~/.claude/CLAUDE.md` § Git).
- Sabotage it (`CLAUDE.md` / contract: no guard is believed until seen red): corrupt a record on a scratch branch and watch the job fail for the right reason.

## Traps
- The pinned ref is written in two places once this lands (`CLAUDE.md` and gate.yml); an engine upgrade must move both, or a test should hold them equal.
- A Linux runner and this Windows machine can disagree (line endings, paths): run the job's steps on Linux before trusting a green local lint.

## Read first
- `.github/workflows/gate.yml`
- `CLAUDE.md` § The record engine
- `docs/framework/contract.md` § Gate

## Log
