---
id: TK67
title: formal/HANDOFF.md and P6 say FoldAdmits moves in lockstep; the correction says 3 sites must stay
brief:
pri: LATER
size: S
deps: []
related: [TT-1, TK66, P6, P4]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-07b
moved: 2026-10-04g
updated: 2026-10-04g
closed:
---

**VERIFIED FIRST-HAND 2026-09-07b.** Two live navigation documents instruct a session to
move `FoldAdmits` sites "in lockstep", and the frozen record says that instruction is
superseded and names three sites that must NOT move.

The correction, `formal/history/PROOF_STATUS.md:4897`:

> **`FoldAdmits` lockstep: 21 sites MOVE, 3 MUST STAY** on the σ0 side —
> `RulesComplete.lean:91` (`ReachedByRulesAdmitted.step`), `RestrictBase.lean:470` and
> `:531`. This CORRECTS the previously recorded "all 24 in lockstep" (scope doc §11.10's
> trap keeps its warning; only the count is superseded).

The two live sites still carrying the superseded form:

- `formal/HANDOFF.md:227` — "`foldAdmitsB`/`FoldAdmits` move in lockstep", inside the
  revised 4c-i → 4c-ii order. This is the file `P4`'s own read-first calls "**first, for
  any formal item**".
- `tasks/P6-ttustarfree-ii-*.md:49-50` — "both move `FoldAdmits` + `Exec.lean::foldAdmitsB`
  in lockstep", in the paragraph explaining why `P6` and `P3` collide textually.

Neither carries the qualifier. A session that follows either one moves all 24 and takes
three sites off the σ0 side that the correction says must stay. This is not a navigation
inconvenience like the rest of `TK66` — it is a live instruction that is wrong.

Both live sites were annotated 2026-09-07b with a pointer to the correction, which stops
the immediate hazard. What is NOT done, and is the actual work here: confirming against the
current Lean tree that the three named sites still exist at those symbols and still must
stay. The correction is dated and frozen; `RestrictBase.lean:470`/`:531` are LINE numbers
in a file that has been edited since, and `P3` landed on 2026-09-05b.

## Traps

- ⚠ **Do not "fix" this by deleting the word lockstep.** The lockstep claim is 21/24 true
  and it is the reason `P3` and `P6` collide. Removing it loses the collision argument;
  qualifying it is the fix.
- ⚠ The three sites are cited by LINE (`RestrictBase.lean:470`, `:531`). Resolve them by
  SYMBOL before trusting them — `CLAUDE.md`'s rule is that a trap must cite a symbol that
  exists, and a bare line number in a frozen doc is the weakest possible citation.
- Editing `formal/HANDOFF.md` stales the `lean` verdict (`t2a` includes `*.md`). Records
  first, then re-run `lean`, then commit.

## Read first

- `formal/history/PROOF_STATUS.md:4897` — the correction itself, quoted above
- `formal/history/leaf-family-split-scope-2026-08-05.md:1204` — the same correction from the scope side, and §11.10 whose trap is explicitly NOT superseded
- `formal/HANDOFF.md` — the live site that matters most, since every formal item is told to read it first

## Log

### 2026-09-19f

TRANSCRIBED FROM THE `HANDOFF.md` BANNER 2026-09-19f, not re-verified here. The banner line
carrying this was demoted into this row because the banner was over its trap-badge budget
(11 of 10) and `docs/README.md` names the defined move: put the trap on its item and leave a
pointer. The content below is the 2026-09-12 session's first-hand narrowing; treat it as that
session's evidence, dated, and resolve the line numbers by SYMBOL before acting (this row's
own trap says so).

> `FoldAdmits`: 21 of 24 sites move, THREE MUST STAY (`PROOF_STATUS.md:4895`). 2026-09-12
> narrowed `TK67`: the trap is SOUND and the symbol EXISTS -- `ReachedByRulesAdmitted.step`
> is `RulesComplete.lean:113` with `hadm` at `:115` (used at 8+ sites); only the recorded
> line `:91` is stale, and a subagent that reported "there is no `step` constructor" would
> have deleted a valid trap. Stay-sites: `RulesComplete.lean:115`, `RestrictBase.lean:470`,
> `:531`.

That narrowing answers most of what the body calls "the actual work here" for ONE of the
three sites (the `step` constructor exists, at a different line than recorded). The two
`RestrictBase.lean` sites are still line-cited and still unresolved by symbol.

### 2026-10-04g

Closability sweep 2026-10-04g (agent report, UNVERIFIED first-hand unless marked; the session did not act on it): PARTLY DONE. Qualifier now on the P6 task file and the RulesComplete.lean stay-site exists; the two RestrictBase.lean stay-sites are still cited by line only (FoldAdmits now at several later lines). P6 is the only consumer: fold this into P6 as a trap and close as merged.
