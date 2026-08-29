---
id: TK46
title: handoff_lint's _ROW_ID truncates R6-99 to R6, so an invented ledger id passes as real
brief:
pri: LATER
size: S
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-24c
updated: 2026-08-24c
closed: 2026-08-24c
---

`scripts/handoff_lint.py:245` is

```
_ROW_ID = re.compile(r'\b([A-Z]{1,3}-?\d+|ZT-[A-Z0-9-]+)\b')
```

On the citation `R6-99` the first alternative matches `R6` and stops at the word boundary before the hyphen. `R6` **is** a real board id, so `check_ledger_row_ids` compares the truncated prefix, finds it, and passes — a session-log citation that resolves to nothing is reported clean. **Every `R6-N` id sits in that blind spot**, i.e. a sixth of the live id space; the same hole is in the shipped board-table version, so it is a bug, not a port artefact.

**The fix already exists**, in `.scratch/tasktool/handoff_lint_new.py:372`: try the compound form FIRST

```
_ROW_ID = re.compile(r'\b(ZT-[A-Z0-9]+(?:-[A-Z0-9]+)*|[A-Z]{1,3}\d+(?:-\d+)?|[A-Z]{1,3}-\d+)\b')
```

This row can therefore be closed by porting one line, independently of whether the rest of that file ever graduates.

## Traps

⚠ **Demonstrate it with the id shape that is actually blind, not with a bogus one.** Sabotaging with `P99` proves the COMPARISON works; it does not prove the regex SEES the id being compared. The reproduction is: cite an invented `R6-99` in `docs/history/session-log.md`, run the linter with each regex, and diff. Observed — inherited: `handoff_lint: clean (7 checks)`, rc=0; ported: `FAIL: ... cites board id 'R6-99', which is on neither the task tree nor tasks/retired-ids.txt`, rc=1. Extracted token lists on the same line: inherited `['R6', 'R6', 'ZT-P5', 'AW-1', 'P3', 'B2', 'R6']` vs ported `['R6-99', 'R6-19', 'ZT-P5', 'AW-1', 'P3', 'B2', 'R6']`.

⚠ **Do not read an exit code through a pipe.** `cmd > /tmp/p.log 2>&1; rc=$?` and branch on `$rc` — standing footgun 1 in `CLAUDE.md`, and it has already produced one false green while measuring this very file.

⚠ **Widening a regex can go the other way.** Confirm the new form still parses the `ZT-*` compound ids (`ZT-P1-8b`, `ZT-P5-NEW`) and does not start matching prose. The non-vacuity floor on the id count is what keeps a fix from silently extracting nothing.

## Read first

- `scripts/handoff_lint.py:245` — the regex, and `::check_ledger_row_ids` (`:502`) — the check it defeats
- `.scratch/tasktool/handoff_lint_new.py:372` — the fix, and its `check_ledger_row_ids` docstring (`:690-710`) — the measurement that found the hole
- `.scratch/tasktool/PROOF.md` §2d — an independent reproduction by regex swap
- [`docs/gate-runbook.md`](docs/gate-runbook.md) §4 — where step 4f runs this linter in the gate

## Log

### 2026-08-21b

**Provenance.** Found by this project's own work, not by the sweep: the ported linter's instrument-control pass (`handoff_lint_new.py::check_ledger_row_ids` docstring, "THE EXTRACTOR IS THE FRAGILE HALF") and reproduced independently in PROOF.md §2d by swapping the inherited regex back under an identical sabotage. Regex re-read at scripts/handoff_lint.py:245 this pass.

### 2026-08-24c

Fixed in `scripts/handoff_lint.py`, and it was NOT the one-line port this row predicted.

**Half 1, the extractor** (as filed): `_ROW_ID` now tries the compound form first,
ported from `.scratch/tasktool/handoff_lint_new.py:372`.

**Half 2, unfiled and load-bearing:** porting the regex ALONE was run against the live
tree and false-redded a REAL id --

    FAIL: docs/history/session-log.md:388 cites board id 'R6-10', which is on neither
    the board nor its retired-ids line.

`R6-10` landed 2026-08-20b; the board names it in the `### R6` item block and gives it
no table row, because sub-items are not ranked, and a ledger legitimately cites it. So
`check_ledger_row_ids` now harvests `known` from the WHOLE board, with the non-vacuity
floor kept on the TABLE harvest specifically -- on the whole-file harvest, a broken row
parser would coast on prose. This row's own third trap ("widening a regex can go the
other way") is what predicted it; the trap was right and the "port one line" estimate
was wrong.

**Sabotage, per this row's prescribed reproduction** -- an invented `R6-99` at
`session-log.md:123` of the real corpus, both regexes over the identical sabotaged tree:

    inherited -> 0 violation(s); tokens ['R6', 'R6', 'P3', 'P6']
    ported    -> 1 violation(s); tokens ['R6-99', 'R6', 'P3', 'P6']

The token lists are the evidence: the inherited regex never had `R6-99` in hand, so its
silence was not a judgement. Controls on the same corpus: `P99` -> 1 (invented top-level,
the 2026-08-16 behaviour survives), `R6-10` / `R6-19` -> 0 (real, prose-only), `HS-5` -> 0
(real row, so the check is not firing on line shape).

**Durability rank 1, not a docstring:** `tests/test_handoff_lint_row_ids.py`, 9 tests.
Suite-level sabotage run per `docs/sabotage-procedure.md`, both halves reinstalled
separately, and the red is ATTRIBUTABLE both times:

    inherited regex reinstalled       -> 3 failed, 6 passed  (the 3 extractor pins)
    whole-board harvest removed       -> 1 failed, 8 passed  (the false-red control)

Restored: `9 passed`, `handoff_lint: clean (10 checks)`.

**Known limit, recorded rather than speculatively fixed** (see the check's docstring):
the retired line ends "the whole `ZT-*` series" instead of listing them, so a `rows:`
line citing a specific `ZT-` id would false-red. Equally true before this fix, the series
is closed, and no `rows:` line cites one.
