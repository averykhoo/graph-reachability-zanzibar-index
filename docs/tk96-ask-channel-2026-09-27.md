# `TK96`: the `ASK-*` channel -- `asks`, the board line, and the `asked:` receipt

**ACTIVE-PLAN 2026-09-27d.** Written FIRST, before the edit it was made for (CLAUDE.md
"SCOUTING IS A DELIVERABLE"). Corrections are appended at the top with a date, never edited
into the body. FROZEN when `TK96` closes. Figures were measured on `2026-09-27` against
master `d4ea804` in a workflow worktree.

Provenance labels: **READ** (first-hand, this session), **REASONED**, **MEASURED** (a run
whose output is quoted), **UNVERIFIED**. No subagents were used.

## § 0 The row, restated as three deliverables

`tasks/TK96-...md` (READ) asks for:

1. `task.py asks` -- open `ASK-*` rows, oldest first, with age in days.
2. One bounded footer line on `board`, matching the `ready ...` line:
   `asks   3 open, oldest 12 days   (python scripts/task.py asks)`.
3. `handoff_lint.py::check_session_receipt` requires a third literal line --
   `asked: ASK-3` or `asked: none` -- in the newest session-log entry whenever any `ASK-*`
   sits at `NEXT`. The row's Traps: steps 1-2 alone are a doc warning; step 3 is what makes
   the nag fail-red; sabotage must show an `ASK-*` at `NEXT` with no `asked:` line turns
   the check (and so `verify.sh lean`) RED; the sweep covers the new code, not one case.

## § 1 Map (READ 2026-09-27, line numbers dated and will rot)

| where | what | provenance |
|---|---|---|
| `scripts/task.py::op_board` (`:1979`) | prints the `ready  N open task(s) ...` line, then `open ...`, then `footer_lines` | READ |
| `scripts/task.py::NEXT_COMMANDS` (`:2065`) | `('show <id>', 'ready', 'list --pri LATER', 'lint')`; `test_board_footer_names_every_advertised_verb` asserts every verb the board BODY advertises is in it | READ |
| `scripts/task.py::BOARD_MAX_LINES` (`:643`) | `50`; pinned by `tests/test_tasktool.py::test_board_stays_under_its_size_ceiling` against a worst-case corpus | READ |
| `scripts/task.py::build_parser` / `::OPS` | `read_op(name, help)` adds `--json`; `OPS` maps verb -> function | READ |
| `scripts/task.py::op_ready` | the shape `asks` mirrors (plain rows, `--json`, an explicit empty-state line) | READ |
| `scripts/handoff_lint.py::check_session_receipt` (`:860`) | reads the newest entry via `_newest_entry_lines(ROOT_LEDGER, _ROOT_ENTRY)`, normalises each line (strip, drop backticks and `**`), SEARCHES two regexes (`_LINT_RECEIPT`, `_READ_RECEIPT`) | READ |
| `scripts/handoff_lint.py::_tree_open_pris` | `(pri, filename)` harvest of OPEN task files, frontmatter first 20 lines; `None` = no tree | READ |
| `scripts/handoff_lint.py::_tree_ids` | every id open + closed + retired | READ |
| `tests/test_handoff_lint_b_prime.py` | the receipt tests: `_write_ledger`, `_write_tasks`, shapes parametrised, `test_the_two_checks_are_in_the_list_and_nothing_was_inserted` pins `CHECKS` positions (receipt at index 10, 12 checks) | READ |
| `tests/test_tasktool.py::writepath_sabotage` | permanent sabotage harness: patch a COPY of task.py, re-run the guarding test, assert it FAILS | READ |

Measured on the live tree (MEASURED 2026-09-27, before any edit):

```
task.py board        -> 33 lines, rc=0; footer wraps to 3 lines
task lint: clean (13 checks, 227 task file(s) parsed), 33 warning(s)
handoff_lint: clean (12 checks)
```

Live `ASK-*` rows (READ): `ASK-2` open at `LATER` (created `2026-09-26b`); `ASK-1` closed.
So the new receipt requirement is NOT triggered by the live tree today, and `ASK-2`'s
priority is not to be touched (orchestrator instruction).

## § 2 Decisions (REASONED; the user delegated engineering calls, CLAUDE.md "Who decides")

* **D1 -- what is an ASK row.** An id matching `^ASK-\d+$`. `task.py::ASK_ID` and a
  duplicated `handoff_lint.py::_ASK_ID` (handoff_lint imports nothing from task.py -- the
  independence rule already stated at `TASKS_NON_TASK_MD`).
* **D2 -- "oldest first", "age".** Oldest by `created` (the date part, first 10 chars of
  the session key); ties by id. Age = today minus that date, in whole days. `moved` is not
  used: an ASK re-ranked yesterday is still a question that has waited since it was filed.
* **D3 -- `asks` also shows what each ASK blocks** (open tasks whose `deps` name it). The
  row's own composition argument is that an ASK WITH dependents is a hard blocker; the
  view that lists asks is where that distinction pays. Cheap: one pass over open tasks.
  NEXT rows are marked, since those are the ones this session must raise in chat.
* **D4 -- the board line is ALWAYS printed, including at zero** (`asks   0 open   (...)`).
  A line that vanishes at zero is indistinguishable from a board that lost the feature --
  the house failure mode. It also keeps the size arithmetic a constant (+1 line). When any
  ASK is at NEXT the line says so (`K at NEXT -- raise in chat`), because the lint receipt
  that enforces it runs at commit time, and the board is where a session learns it owes it.
* **D5 -- `asks` joins `NEXT_COMMANDS`**, and `test_board_footer_names_every_advertised_verb`
  grows `asks` in its body-advertised tuple -- the same rule that put `ready` there.
* **D6 -- the receipt must NAME EVERY NEXT ASK**, and `asked: none` is RED while any ASK sits
  at NEXT. The user's rule is "must raise it ... at least once that session" -- a MUST,
  unlike the lint receipt (which accepts `N violation(s)` because lint itself reddens
  elsewhere). Nothing else enforces the ask, so an honest `none` is a recorded failure and
  must be loud. `asked: none` is accepted (and the line optional) when no ASK is at NEXT.
* **D7 -- a named id the tree does not know is RED** (typo guard: `ASK-3` for `ASK-8` would
  otherwise pass whenever the real one is also named). Closed ids are KNOWN (a session may
  ask and close in one go), so the lookup uses `_tree_ids`. Mixing `none` with ids is
  malformed -> RED. Several `asked:` lines are unioned.
* **D8 -- no receipt requirement when there is no tree** (`_tree_open_rows() is None`), same
  None-vs-empty convention as `_tree_open_pris`.

**D7 amended during implementation (REASONED):** `asked: none, ASK-3` is not a separate
"malformed" failure. The regex reads it as `none`, so while an ask sits at NEXT it is RED
for being `none`, and with no ask at NEXT it does no harm. The unknown-id check runs
whenever a tree exists, NEXT ask or not: a line that IS written must still name real ids.

## § 3 What landed (READ, the diff of this commit)

| piece | where |
|---|---|
| 1. `asks` op | `scripts/task.py::op_asks`, `::open_asks`, `::ask_age_days`, `::days_text`, `::ASK_ID`; registered in `::build_parser` / `::OPS` |
| 2. board line | `scripts/task.py::asks_line`, emitted by `::op_board` directly under `ready`; `--json` keys `asks` / `asks_next`; `asks` appended to `::NEXT_COMMANDS` (ordered so the `scripts/task.py` footer stays 3 lines) |
| 3. receipt | `scripts/handoff_lint.py::check_session_receipt` (third, conditional block), `::_tree_next_asks`, `::_ASK_ID`, `::_ASKED_RECEIPT`, `::_ASKED_ID`, `::_ask_order` |
| tests | `tests/test_tasktool.py`: `test_asks_lists_open_asks_oldest_first_with_age_and_blockers`, `test_board_prints_one_asks_line_under_ready`, `test_asks_line_is_printed_at_zero_too`, `test_ask_age_is_whole_days_from_created_and_honest_when_malformed`, permanent sabotages `test_sabotage_ask_sort_keyed_on_moved` / `test_sabotage_ask_age_from_moved` (counted in `test_the_sabotage_record_is_complete`), plus `asks` added to `test_board_footer_names_every_advertised_verb` and an `asks` line asserted in `test_board_stays_under_its_size_ceiling`. `tests/test_handoff_lint_b_prime.py`: `test_asked_receipt_is_red_until_every_next_ask_is_named`, `test_asked_receipt_accepts_the_shapes_the_other_receipts_accept` (6 shapes), `test_asked_receipt_refuses_near_misses` (7 shapes), `test_asked_receipt_is_optional_without_a_next_ask`, `test_asked_receipt_refuses_an_id_the_tree_does_not_know` |
| docs | `tasks/README.md` "The `ASK-*` series" (two bullets), `docs/README.md` sec 4 + sec 7 step 1, `docs/tasktool-spec.md` read-ops table (`asks` row, `board` row), `CLAUDE.md` receipt bullet |

Board size (MEASURED 2026-09-27): live board 33 -> 34 lines (+1, the `asks` line; the
footer still wraps to 3 lines). The worst-case corpus of
`test_board_stays_under_its_size_ceiling`, run by the harness with an absolute
`task.py` path so every footer command wraps to its own line, is **42 lines** against
`BOARD_MAX_LINES` 50 (probe: the test body with `out_lines` spied).

## § 4 Sabotage and mutation evidence (MEASURED 2026-09-27d, literal output)

**End to end, the step that makes the nag fail-red.** `scripts/handoff_lint.py` -- the
exact script `verify.sh lean` step 4f runs -- on a full copy of this worktree (`.git`,
`.scratch`, `.claude` excluded) with the newest ledger entry's text edited in place:

```
E1 copy as-is                                                    rc=0  handoff_lint: clean (12 checks)
E2 ASK-2 flipped to NEXT, no asked: line                         rc=1  handoff_lint: 1 violation(s)
   FAIL: docs/history/session-log.md: the newest entry (## 2026-09-27c ? `TK95` CLOSED: a refused
   fan-out leaves no trace in any order, ) -- it has no `asked:` line, but ASK-2 sit(s) at NEXT.
   A NEXT ask is a question only the user can answer, and the session must raise it with them
   in chat at least once (TK96; tasks/README.md, "The ASK-* series"). Ask, then write
   `asked: ASK-2`. To stop the nag, demote the row to LATER instead -- `none` is not accepted
   while an ask is at NEXT.
E3 E2 + `asked: none` in the newest entry                        rc=1  ... -- it says `asked: none`, but ASK-2 sit(s) at NEXT. ...
E4 E2 + `asked: ASK-2` in the newest entry                       rc=0  handoff_lint: clean (12 checks)
E5 E2 with the new block disabled (next_asks = None: SABOTAGE)   rc=0  handoff_lint: clean (12 checks)
```

(The `?` is the headline's em dash through the cp1252 console.) E5 is the row's Trap
made literal: steps 1-2 alone are green on a tree whose NEXT ask was never raised.
**Instrument note:** the first E3/E4 run inserted the `asked:` line into the ledger's
HEADER, whose rules paragraph quotes `` `read: board only` `` too, and E4 read rc=1. The
probe now asserts its insertion point lies between the first and second `## 20` entry
headings; the numbers above are from the fixed probe.

**Mutation sweep** (`.scratch/tk96/mut.py`, gitignored; results transcribed here). Each
mutant was written into a FRESH temp dir holding only the mutated module, a copy of its
test module and an empty `pytest.ini` -- the worktree was never mutated, so no outer
timeout could leave a mutant behind. Every anchor was asserted to match exactly once.

`scripts/handoff_lint.py`, `pytest tests/test_handoff_lint_b_prime.py -k "asked or receipt"`:

| id | mutant | verdict | last line | killed by |
|---|---|---|---|---|
| H0 | control: no change | green | `42 passed, 5 deselected` | -- |
| H1 | the asked: block disabled (steps 1-2 only) | KILLED | `10 failed, 32 passed` | `test_asked_receipt_is_red_until_every_next_ask_is_named` (+ every near-miss) |
| H2 | `is None` -> `not next_asks` (skips the unknown-id check) | KILLED | `1 failed, 41 passed` | `..._is_optional_without_a_next_ask` |
| H3 | `none` not recognised | KILLED | `1 failed, 41 passed` | `..._is_red_until_every_next_ask_is_named` |
| H4 | any one name satisfies all | KILLED | `1 failed, 41 passed` | `..._is_red_until_every_next_ask_is_named` |
| H5 | `_ASK_ID` loses `$` | KILLED | `1 failed, 41 passed` | `..._is_optional_without_a_next_ask` (`ASK-8b`) |
| H6 | LATER asks harvested too | KILLED | `2 failed, 40 passed` | both NEXT/optional tests |
| H7 | trailing guard `[\w-]` -> `\w` | KILLED | `1 failed, 41 passed` | near-miss `asked: ASK-3-x` |
| H8 | leading `(?:^|\W)` dropped | KILLED | `1 failed, 41 passed` | near-miss `unasked: ASK-3` |
| H9 | comma list not read | KILLED | `2 failed, 40 passed` | `..._red_until...`, `..._unknown...` |
| H10 | unknown ids checked against NEXT asks only | KILLED | `3 failed, 39 passed` | three tests (closed `ASK-7` flagged) |
| H11 | unknown-id check disabled | KILLED | `2 failed, 40 passed` | `..._optional...`, `..._unknown...` |
| H12 | raw lines searched, not normalised | KILLED | `1 failed, 41 passed` | shape `` asked: `ASK-3` `` |

H1 on the headline test alone, literal: `E       AssertionError: []` / `1 failed`.

`scripts/task.py`, `pytest tests/test_tasktool.py -k "<the six tests above that exercise asks>"`:

| id | mutant | verdict | last line | killed by |
|---|---|---|---|---|
| T0 | control: no change | green | `6 passed, 96 deselected` | -- |
| T1 | `ASK_ID` loses `$` | KILLED | `3 failed, 3 passed` | list, board, unit |
| T2 | sort keyed on `moved` | KILLED | `2 failed, 4 passed` | list, board |
| T3 | tie broken by id STRING | KILLED | `2 failed, 4 passed` | list, board |
| T4 | closed asks included | KILLED | `2 failed, 4 passed` | list, board |
| T5 | age from `moved` | KILLED | `3 failed, 3 passed` | list, board, unit |
| T6 | singular `1 day` lost | KILLED | `2 failed, 4 passed` | zero-line, unit |
| T7 | board line suppressed at zero | KILLED | `3 failed, 3 passed` | footer, ceiling, zero-line |
| T8 | `at NEXT` clause dropped | KILLED | `1 failed, 5 passed` | board |
| T9 | "oldest" read from the newest | KILLED | `1 failed, 5 passed` | board |
| T10 | `blocks` never built | KILLED | `1 failed, 5 passed` | list |
| T11 | NEXT flag line dropped | KILLED | `1 failed, 5 passed` | list |
| T12 | `asks` dropped from `NEXT_COMMANDS` | KILLED | `1 failed, 5 passed` | footer |
| T13 | asks line moved below `open` | KILLED | `1 failed, 5 passed` | board |
| T14 | `--json` `age_days` None | KILLED | `1 failed, 5 passed` | list |
| T15 | board `asks_next` unfiltered | KILLED | `1 failed, 5 passed` | board |
| T16 | malformed-`created` guard removed | KILLED | `1 failed, 5 passed` | unit |
| T17 | `asks` missing from `OPS` | KILLED | `2 failed, 4 passed` | list, zero-line |

**29/29 non-control mutants killed; both controls green.** T2 and T5 are ALSO permanent
tests (`test_sabotage_ask_*` via `writepath_sabotage`), observed:
`asks are not oldest-first by `created`, id number breaking ties:` and
`AssertionError: ASK-2    NEXT    0 days    ask two`.

**Not swept (REASONED):** `_tree_next_asks` reading only the top-level `tasks/` (a closed
file at NEXT is ignored) has no single-anchor mutation -- its loop text is shared with
`_tree_open_pris` -- but `test_asked_receipt_is_optional_without_a_next_ask` places a
closed `ASK-7` at NEXT and asserts green, so a harvester that walked `closed/` would red.

## § 5 Status and what is NOT done

* MEASURED 2026-09-27d/28 in the worktree: `pytest tests/test_tasktool.py
  tests/test_handoff_lint_b_prime.py tests/test_handoff_lint_count_guard.py
  tests/test_handoff_lint_row_ids.py` -> `183 passed`; `verify.sh tests-tile:1/4` ..
  `4/4` each `=== verify.sh: phase 'tests-tile:N/4' PASSED ===`, each `tests phase PASSED
  (362 passed ...; floor 362)`. `scripts/handoff_lint.py` -> `handoff_lint: clean (12
  checks)`; `task.py lint` -> `task lint: clean (13 checks, 227 task file(s) parsed), 33
  warning(s)`. `lean` and the `conf-tile`s were NOT run here (no `.lake` in a worktree);
  the orchestrator runs them on the main tree after merge -- `lean` is the phase whose
  step 4f runs the new receipt against the live ledger.
* `docs/history/session-log.md`'s own header rules still say "Two literal receipt lines";
  this worker may not edit that file. The orchestrator's write-back should add the
  conditional `asked:` line there.
* `ASK-2` stays at LATER (not touched), so the live tree does not trigger the receipt.
