# `task.py` — the adversarial verification record, August 2026

**FROZEN 2026-08-29 — provenance, not a living document.** Status lines below are
as-of-then and several may now be false; live state: `HANDOFF.md` + the session ledger.
Corrections are appended dated at the top, never edited into the body.

**Provenance.** Transcribed 2026-08-29d from `.scratch/tasktool/PROOF4.md` (658 lines) and
`.scratch/tasktool/sabotage-log.txt` (137 lines), which are gitignored and therefore
already-lost evidence by this repo's own rule (`CLAUDE.md`: *"if a run is evidence, it
goes in a tracked file the same hour"*). This file is the load-bearing extract, not the
whole transcript: the parts kept are the ones a later reader needs in order to decide
whether an assurance step here is real. The suite itself is no longer in scratch —
it is `tests/test_tasktool.py`, inside the gate.

## Why this exists at all

The tool exists to keep a corpus of ~150 task files honest, and its entire value rests on
`lint` going RED when something is wrong. A lint that has gone blind reports `clean`
forever on exactly the corpus it exists to police — this repo's declared house failure
mode. So the tool's checks were not merely tested; each was **sabotaged**, and the
sabotage was required to produce a red *attributable to that check* (`docs/sabotage-procedure.md`).

Three of the cases below sabotage the **instrument** rather than the subject, and those
are the ones that earn the record: a control that only breaks the data proves the check
runs, not that it can see.

## The results, as recorded 2026-08-21e (`PROOF4.md` §9.6, verbatim)

| check | result |
|---|---|
| `python test_task.py` | **rc=0**, `40 test(s), 0 failed` |
| `python test_task.py --sabotage` | **rc=0**, `22/22 sabotages produced an attributable red`, `LIVE-CORPUS PASS: 4/4` |
| `python sync_sabotage.py` | **rc=0**, `14 sabotage(s), 0 failed to redden` |
| `python sync_accept.py` | **rc=0**, `57 assertion(s), 0 failed` |
| `task.py --dir sandbox-migrated lint` | **rc=0**, clean, 11 checks [dated: 2026-08-21] |
| `task.py --dir sandbox-migrated sync --check` | **rc=0**, `sync   CLEAN` |
| round-trip over the corpus | **150/150 byte-identical** |
| `git status --porcelain` | **rc=0, 0 lines** |

The two summary lines from `sabotage-log.txt`, verbatim:

```
22/22 sabotages produced an attributable red.
LIVE-CORPUS PASS: 4/4 produced an attributable red.
```

⚠ **Do not re-cite the `40 test(s)` or `11 checks` figures as current.** They were true on
2026-08-21e against the scratch tree. The suite gained a test the same week; the port to
`tests/test_tasktool.py` on 2026-08-29d added the sabotage cases as permanent tests and a
twelfth lint check. Live figures come from `pytest --collect-only` and from `lint`'s own
output line, never from this file — which is the exact rot this record is quarantined to
avoid spreading.

## The three instrument controls, which are the reason to trust the rest

1. **A DISABLED floor.** `min_tasks_parsed: 0` — the config value that switches the
   corpus-size control off — was accepted by `int(...)` and printed clean. Observed before
   the fix, on the live 99-file corpus:

   ```
   min_tasks_parsed=0    -> task lint: clean (10 checks, 99 ...)  TRUE rc=0
   min_tasks_parsed='99' -> task lint: clean (10 checks, 99 ...)  TRUE rc=0
   ```

   After: `FAIL: .../tasks/config.json has min_tasks_parsed = 0; expected a positive
   integer. A value of 0 or less is not a LOWERED floor, it is a DISABLED one`.

2. **A BLIND PARSER.** A patched copy of the tool whose `Store.md_paths` never descends
   into `closed/`, run against a tree rearranged so a third of the corpus lives there. The
   case asserts not merely a red but **exactly two `FAIL:` lines** — the floor and the
   independent recount (`scan offered`) — and nothing else. A single red would not
   distinguish "the control fired" from "something else happened to break".

3. **A SHIPPED EXAMPLE VALUE.** `id_prefix: "T"` came from the spec's own example block
   and minted `T1`, which is already the name of the set-engine correctness theorem (162
   first-party occurrences in 33 files). Measured, not guessed: `"T"` scores 686
   first-party hits for `\bT\d+\b`, `"TK"` scores 0. An id that is already a name is
   unresolvable by grep, and ids are addresses.

The floor's own history is the argument for zero headroom: it shipped at `5`, which left
94 files of slack, and `rm -rf tasks/closed` destroyed 58% of the corpus while lint printed
`clean (10 checks, 42 task file(s) parsed)`, exit 0.

## What the write-path pass proved that an exit code cannot

Four cases patch the tool and then re-run the **guarding test** rather than checking a
process exit code. The subject is the test: a test that still passes against a weakened
tool guards nothing.

| weakening | test that must go red |
|---|---|
| `MAX_PARENT_DEPTH = 2` → `99` | `test_parent_depth_warns_and_stays_green` |
| `ack` calls `stamp_and_render(..., True)` (bumps `moved`) | `test_the_moved_updated_split_survives_automation` |
| `--mechanical` ignored (`return True`) | `test_the_moved_updated_split_survives_automation` |
| `source_problem()` short-circuited to `return None` | `test_source_is_written_once_and_never_again` |

The second and third are the anti-laundering guarantee: if an automated housekeeping pass
could bump `moved`, every NOW row would look permanently fresh and `board`'s staleness
warning would be unfireable — a check that fails by passing.

## The no-delete guarantee (`PROOF4.md` §1)

`sync` has no delete path and no `--force`, which is why it replaced `migrate.py --rebuild`.
Verified four independent ways rather than by reading the code: deleting a board row and
running every sync mode; actively trying to make it delete; an independent AST audit
(not the shipped token-stream check); and call-graph reachability from `sync`'s entry to
every `os.remove` / `shutil` call site. The strongest observation:

```
| board with header but ZERO data rows | rc=1, all 25 board-sourced open tasks reported
  CORPUS-ONLY, none touched | 152/152 identical |
| retired id re-added to the board | NEW-REFUSED, no file minted | only my own edit |
```

⚠ **`.scratch/tasktool/migrate.py` must not be run.** Its `--rebuild` destroys 51
hand-filed tasks that no source document contains. This is repeated in `CLAUDE.md` and in
`docs/tasktool-spec.md` §7 because it is the one irreversible operation in the toolchain.

## Known limits of this record

* The original transcripts embed absolute Windows paths and CRLF artifacts, so they were
  **not** copied verbatim wholesale — a transcript that only reproduces on one machine
  rots the moment anyone else reads it. The claims kept here are the ones the ported
  pytest suite re-derives on every gate run.
* `sync_sabotage.py` (14 cases) and `sync_accept.py` (57 assertions) were **not** ported;
  only their result is recorded above. They cover `sync`, which retires at the Phase-B
  cutover (`docs/tree-sole-authority-spec-2026-08-29.md` §2), and porting a suite for a
  verb scheduled for retirement is work with a known expiry. **If the cutover does not
  happen, that gap is real and should be closed.**
