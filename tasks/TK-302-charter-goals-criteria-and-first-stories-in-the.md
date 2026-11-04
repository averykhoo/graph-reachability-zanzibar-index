---
type: Task
id: TK-302
title: Charter goals, criteria and first stories in the owner's own words
brief: Owner words only, verbatim (DEC-15); the body's G-1..G-4 are agent drafts to put to the owner
pri: SOMEDAY
state: open
deps: []
source: session 2026-11-04a
created: 2026-11-04
moved: 2026-11-04a
updated: 2026-11-04a
---

Fill `docs/charter.md` (goals) and `docs/criteria.md`, and record the first stories, in the owner's own words, in a zanzibar engine session (procedures § Intake). Decided by the owner: DEC-15 (answering context-engine `ASK-31`, "31 yes we should do that eventually"). Until then both stay the kit's templates, which lint accepts; orient lists them under "Templates still unfilled".

**AGENT DRAFTS, NOT OWNER WORDS.** The candidate goals below were reconstructed by the CE-167 survey agent (context-engine `.scratch/ce-167/survey-records.md` § 5, 2026-11-03) from existing repo text. They are a starting point to put to the owner, never to be recorded as `actor: owner` without the owner's own words:
- G-1 (draft): equivalence of the graph index and the set engine, with the oracle as referee (nearest source: `CLAUDE.md` § Who decides, "The primary consideration is EQUIVALENCE", user 2026-09-12b).
- G-2 (draft): honest, legible assurance, not wider (nearest source: `docs/architecture/decision-log.md` § "The project goal", user 2026-09-22c; `docs/goal-census-2026-09-22.md`).
- G-3 (draft): public release hygiene (PyPI 0.1.x, a tag only on the user's word).
- G-4 (draft): a stranger-proof public API and docs (TK179, TK151, the install trials).

## Traps
- Owner words are recorded verbatim with `actor=owner`; an agent's paraphrase of these drafts is not owner words.
- `[guards] task_goals` is off in `context.toml`: turning it on once goals exist makes every open task name one.

## Read first
- `docs/charter.md`
- `docs/criteria.md`
- `docs/architecture/decision-log.md` § "The project goal"

## Log
