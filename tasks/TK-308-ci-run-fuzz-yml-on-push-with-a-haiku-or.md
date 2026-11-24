---
type: Task
id: TK-308
title: 'CI: run fuzz.yml on push with a haiku or scripted babysitter, never scheduled (DEC-22)'
brief: CI config change of its own; push trigger, no schedule; the watcher covers the fuzz run (DEC-22)
pri: NEXT
state: open
deps: []
source: session 2026-11-24a
created: 2026-11-24
moved: 2026-11-24a
updated: 2026-11-24b
---

Run `.github/workflows/fuzz.yml` (the multi-seed hypothesis sweep) on every push, watched by a babysitter, and never on a schedule. Decided by the owner: DEC-22 (2026-11-24): "Fuzz on demand is a side effect of me not watching cicd pipelines and never acting on them, and Claude will usually only see the repo and won't check all historical runs, so there's no point running fuzz on a schedule, it's easier to just run on push with a haiku or scripted babysitter". This supersedes the 2026-10-07 "on demand and before a release only" rule in the workflow's header comment.

- Add a `push` trigger to `fuzz.yml` (keep `workflow_dispatch` and `workflow_call`); add no `schedule`.
- Rewrite the workflow's header comment so it states the DEC-22 rule, not the 2026-10-07 one.
- The babysitter: the push procedure's CI watcher (haiku agent or a script) covers the fuzz run as well as gate.yml, keyed on the pushed SHA (`docs/runbooks/procedures.md`, `~/.claude/CLAUDE.md` CI watcher rule).
- Update `CLAUDE.md` § Running things (the GitHub Actions bullet) and `docs/gate-runbook.md` sec 3 to drop "pending" once it lands.
- A CI config change of its own, kept off feature branches.

Done when: `fuzz.yml` has a `push` trigger and no `schedule`; one push has shown a fuzz run appear for its SHA and the watcher reporting its verdict; the header comment, `CLAUDE.md` and `docs/gate-runbook.md` say "on push, babysat, never scheduled" and cite DEC-22.

## Traps
- A sweep of six seeds per push costs runner minutes; if it is too slow, cut seeds per push rather than reverting to on-demand (the owner's point is that on-demand runs never happen).
- `HYPOTHESIS_SEED` does nothing; seeds go through `--hypothesis-seed=N` only.

## Read first
- `.github/workflows/fuzz.yml`
- `docs/decisions/DEC-22-charter-goals-anti-goals-mandates-and.md`
- `docs/gate-runbook.md` sec 3

## Log

- 2026-11-24b (claude-code/claude-opus-5-5): DEC-23 (owner, 2026-11-24) relaxes this: fuzz and hypothesis may also run locally before push; CI on push, local before push, or both are acceptable ("since GitHub minutes are free for public projects it doesn't really matter"); still never scheduled. The push trigger stays a valid way to close this row; the Done-when wording should accept either route.
