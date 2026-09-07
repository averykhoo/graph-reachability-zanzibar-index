---
id: TK63
title: the do-not-cancel-P4 warning is one hop away and the tree cannot see it
brief:
pri: LATER
size: S
deps: []
related: [TT-1]
parent:
labels: [formal]
source: docs/history/tasktool-scratch-archive-2026-09-07.md
source_hash:
created: 2026-09-07
moved: 2026-09-07b
updated: 2026-09-07b
closed: 2026-09-07b
---

`AUDIT.md` finding F6, confirmed still true on 2026-09-07.

The "do not cancel `P4`" warning lives at
`formal/history/leaf-family-split-scope-2026-08-05.md:1082` and
`formal/history/PROOF_STATUS.md:247`. It was never on the `HANDOFF.md` board, so the
migration to the task tree could not carry it -- the migration's input was the board.

`tasks/P4-*.md` reads, under `## Traps`: "None recorded. This row sits below `NEXT`, so it
never had an item block; traps for it, if any, live at the pointer below."

That sentence is honest, and it is still a hole. Since the 2026-09-06 cutover the tree is
the SOLE authority on open work, so a session that trusts `task.py show P4` as
self-sufficient -- which is exactly what the cutover tells it to do -- will not see the
warning. The status lines in `formal/history/` are frozen as-of-then and nothing surfaces
them.

This was never intended to be fixed by the migration. It is filed now because the record
naming it as a KNOWN residue was in the deleted directory, and without this row the hole
has no home at all.

## Traps

- Do not copy the warning's text into the task and call it done: `formal/history/` is
  append-only and frozen, so a copy is a second home for a statement that will not be
  updated together. Read `docs/README.md`'s one-home rule before choosing a form.
- The general case matters more than `P4`: the board-to-tree migration could only carry
  what the board held, so any trap that lived only in `formal/history/` is in the same
  position. `P4` is the one instance that was actually measured.

## Read first

- [`docs/history/tasktool-scratch-archive-2026-09-07.md`](../docs/history/tasktool-scratch-archive-2026-09-07.md) section 5 item 9
- `formal/history/PROOF_STATUS.md:247` -- the warning itself

## Log

### 2026-09-07b

LANDED for the P4 instance; the general case is now TK66, which is the bigger half.

tasks/P4 Traps replaced "None recorded" with the do-not-cancel warning as a POINTER, not a
copy -- formal/history/ is append-only and frozen, so a copy would be a second home for a
statement nothing updates (docs/README.md one-home rule).

BOTH LINE CITATIONS ON THIS ROW WERE WRONG and were corrected by reading them:
  * leaf-family-split-scope-2026-08-05.md:1082 is really :1099
  * PROOF_STATUS.md:247 is really :5146
That is worth more than the fix. A row filed to say "a trap must cite something that
exists" cited two lines that did not, which is why the read-first resolver planned on TK59
now checks the PATH only and never the line number.

Also fixed in the same file: P4 read-first cited migrate.py::check_formal_pointer as
enforcing the formal-pointer rule. Dead since 2026-09-07 (TK61, same class).

THE GENERAL CASE IS NOT CLOSED. A read-only sweep of formal/history/ and docs/history/ this
session found 17 directives no live file surfaces, one of which (FoldAdmits lockstep) is not
merely unsurfaced but actively CONTRADICTED by two live docs. Filed as TK66 (the class, with
the sweep table as evidence, explicitly marked unverified) and TK67 (the contradiction,
verified first-hand and annotated at both live sites). Do not read this close as closing the
class -- P4 was one of 17.
