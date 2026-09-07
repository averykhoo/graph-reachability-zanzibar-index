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
moved: 2026-09-07b
updated: 2026-09-07b
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
