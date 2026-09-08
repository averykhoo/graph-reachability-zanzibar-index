---
id: TK66
title: directives that live only in formal/history/ are invisible to the tree; P4 was one of 17
brief:
pri: LATER
size: M
deps: []
related: [TT-1, TK63, TK59]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-07b
moved: 2026-09-08
updated: 2026-09-08
closed:
---

`TK63` fixed the ONE measured instance (`P4`). This is the class it warned about, now
measured: a 2026-09-07b sweep of `formal/history/` and `docs/history/` for forward-binding
directives — "do not cancel", "must stay", "never commit", "do NOT land" — found **17
candidates that no live file surfaces**, against 5 that are already restated live.

The cause is structural and was never a bug in the migration: the board-to-tree migration's
INPUT was the board, so a directive that never had a board row could not be carried. Since
the 2026-09-06 cutover the tree is the SOLE authority on open work, so a session that trusts
`task.py show <id>` as self-sufficient — exactly what the cutover tells it to do — will not
see any of them. Status lines in `formal/history/` are frozen as-of-then and nothing
surfaces them.

## The sweep result (evidence, NOT yet findings)

Produced by a read-only subagent, 2026-09-07b. **Two of its rows were spot-checked
first-hand and one of its line numbers corrected**; the rest are UNVERIFIED and must be
re-checked at the line before anything is acted on or copied. `TK63` itself cited
`PROOF_STATUS.md:247` for the `P4` warning, which is wrong — the real line is `:5146` — so
this table's line numbers are exactly the thing most likely to have rotted.

Confirmed unsurfaced (17):

| file:line | binds | directive |
|---|---|---|
| `leaf-family-split-scope-2026-08-05.md:1099` + `PROOF_STATUS.md:5146` | `P4` | do not cancel without revisiting — **VERIFIED 2026-09-07b, fixed in `tasks/P4-*.md`** |
| `PROOF_STATUS.md:4897` + `leaf-family-split-scope:1204` | `FoldAdmits` / 4c-ii | 21 sites move, 3 must stay — **VERIFIED 2026-09-07b; live docs carry the SUPERSEDED claim. Split out as `TK67`** |
| `PROOF_STATUS.md:6096` (= `leaf-family-split-scope:155`) | leg-7 4c / `S.defs` | leaf preds must stay OUT of `S.defs` |
| `PROOF_STATUS.md:10617` | W3a inertness / `hag` | do NOT land an inertness lemma without settling the R-node-source question |
| `PROOF_STATUS.md:581` | branch `p3-flip-red-2026-09-05` | must not be deleted merely because it is red |
| `p3-flip-red-snapshot-2026-09-05.md:178` + `PROOF_STATUS.md:297` | `d6d2dfc` | lives off `68f2c69`, must not reach master |
| `leaf-family-split-scope:1598` | `W4WitnessDirect` | do NOT extend its flat conjunction |
| `leaf-family-split-scope:1557` | `StoreValidRulesD` | quantify over `exprDirectsAll`, never `exprDirects` |
| `leaf-family-split-scope:1773` | 4c-ii re-point | the control must be the STATE GATE, never the pin trio |
| `leaf-family-split-scope:1270` | 4c-ii cone | never commit a partial cone to "save progress" |
| `leaf-family-split-scope:927` | 4c-ii `LeafRules.lean` cone | the cone is paid once — do not budget it twice |
| `leaf-family-split-scope:1449` | Class-B spike | DONE; do not re-scope it |
| `leaf-family-split-scope:1325` | §11.13 (c) sizing | do not re-cite 42 / ~136 / 24 / 125 |
| `PROOF_STATUS.md:1027` | `RulesCorrect.lean:135` | matches the grep and must NOT move |
| `optional-widening-2026-07.md:272` | leg-5c / leg-4 | do NOT weaken the audited full-`T` ones |
| `handoff-dated-blocks-2026-08-17.md:42` | leg 7 §4 | do not fork `writeDirect`; fork the TUPLE |
| `PROOF_STATUS.md:3664` | Class-B / `headline_statements.txt:27` | no step may rename or delete a pinned name |

Four were classified AMBIGUOUS and are probably discharged or superseded rather than
unsurfaced — `PROOF_STATUS.md:7438` (an audit count that has since moved), `:12123` (T2b now
proved), `leaf-family-split-scope:407`, `handoff-status-2026-08-16.md:225`. ~15 weaker hits
were dropped as generic house rules already in `CLAUDE.md` or as past-tense records.

## Traps

- ⚠ **Do not bulk-copy these into task files.** `formal/history/` is append-only and frozen,
  so a copy is a second home for a statement nothing will update — the exact thing
  `docs/README.md`'s one-home rule forbids, and the reason `TK63` was fixed with a POINTER.
  The `P4` fix is the form to follow.
- ⚠ **A subagent's report is evidence, not a finding** (`CLAUDE.md`). Every row above needs
  the line read before it is acted on. One line number in the source task was already wrong.
- Several rows bind items that are closed or superseded. Verify the BINDING is still live
  before surfacing a directive; surfacing a discharged one costs a future session real time.
- The durable fix is probably mechanical, not editorial: something that resolves a
  `formal/history/` pointer from the tree, in the shape of `TK59`'s read-first resolver.
  Consider doing `TK59` first and extending it.

## Read first

- [`docs/README.md`](../docs/README.md) — the one-home rule, before choosing any form
- `tasks/P4-leg-7-4b-leaf-probe-directleaf-bridge.md` — the worked instance
- [`docs/history/tasktool-scratch-archive-2026-09-07.md`](../docs/history/tasktool-scratch-archive-2026-09-07.md) section 5 item 9 — where `TK63` came from

## Log

### 2026-09-08

Re-read this row before starting it. `TK59` LANDED 2026-09-08: lint check 14
(`task.py::check_read_first`) now resolves markdown links, backticked paths and
`file::symbol` anchors in every OPEN task's `## Read first`, gated via `verify.sh` 4g.

This row is probably an EXTENSION of check 14 rather than its own mechanism -- the
tokeniser, the either-root resolution rule and the symbol lookup are already written and
sabotaged. What is NOT covered and is what this row is actually about: a directive that
lives only in `formal/history/` and is surfaced by no live file. Check 14 proves a pointer
RESOLVES; it says nothing about whether a live file should have carried the statement in
the first place.

Also still true and worth carrying: the table on this row is a subagent's and is marked
UNVERIFIED. `TK59` re-measured two of its neighbours' claims this session and both moved,
so re-verify before acting on any row of it.
