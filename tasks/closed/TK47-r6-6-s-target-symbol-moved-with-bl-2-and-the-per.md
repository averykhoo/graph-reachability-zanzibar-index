---
id: TK47
title: R6-6's target symbol moved with BL-2 and the perf audit still names ::check (both resolve)
pri: LATER
size: S
deps: []
related: [R6-6]
parent: R6
labels: [docs]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-24d
updated: 2026-08-24d
closed: 2026-08-24d
---

Fixing `BL-2` split `index_v4/wildcard.py::WildcardIndex.check` into a public leaf-family DENY fence plus `::WildcardIndex._check_internal`, which carries the old body verbatim. So the four sequential point SELECTs `R6-6` is about now live in `_check_internal` — and `docs/perf-round6-audit-2026-08.md` still names `::check` in its verdict table (`:218`) and throughout its `### R6-6` entry (`:375`, `:387`, `:391`, `:395`), including an instruction to *"preserve the `WildcardIndex.check.key` closure name for the `CORRESPONDENCE.md` anchor gate"* — a closure that has since moved to `::WildcardIndex._check_internal.key`. `formal/CORRESPONDENCE.md` WAS re-anchored the same day (`:265`, `:267`, `:494-507`); the audit was not.

The task-file corpus already warns about this inside `R6-6`'s `## Traps`. Nothing owns fixing the source document, which is what this row is for — and the audit is the doc the next perf session reads first.

## Traps

⚠ **A `file::symbol` anchor check CANNOT catch this class, structurally.** Two independent reasons, and both matter: (1) `formal/conformance/anchor_check.py` reads **only** `formal/CORRESPONDENCE.md` (`anchor_check.py:39`) — `docs/*.md` is outside its scope entirely; and (2) even inside its scope it would pass, because **both symbols exist**: `check` is still a real public method. The gate proves the pointer RESOLVES, never that it points at the code the claim is about. `CORRESPONDENCE.md` §9.2 says so in its own words: the check keeps the map *navigable, not true*.

⚠ **Fix the symbol, do not rewrite the measurement.** The 4.75 → 1.75 statements/round-trip figures were measured 2026-08-17 against the code now called `_check_internal`; they are still valid. Re-point the name, add a dated note, and leave the numbers alone — `CLAUDE.md`: never edit a measured result to make a refactor pass.

⚠ **Check the SIBLING entries while you are in there.** `:805` (appendix lead A4) and `:925` (lead A14) also name `WildcardIndex.check`; at least one of them means the probe that moved. Do not fix `### R6-6` alone and declare the doc clean.

## Read first

- `index_v4/wildcard.py::WildcardIndex.check` (`:627-647`, the BL-2 fence) and `::WildcardIndex._check_internal` (`:649-...`, the moved body) — the code, which is the authority
- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md)`:218` and its `### R6-6` entry at `:375-395` — the stale names
- [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md)`:265`, `:267` and `:494-507` — how the same drift was recorded correctly on the formal side
- `formal/conformance/anchor_check.py:39` — the scope that makes this class uncatchable
- `python task.py show R6-6` — the row whose target this is

## Log

### 2026-08-21b

**Provenance.** Found by this project's own work while migrating `R6-6`; the corpus already carries it as a dated trap inside R6-6's body, but no row owns the DOC fix. Verified this pass by reading index_v4/wildcard.py:627-700 and grepping the audit doc.

### 2026-08-24b

related-edge sweep (trial finding F1): added `related: [R6-6]`. R6-6 carries the moved-symbol trap but does not name the row that owns fixing the audit DOC (verified: 'TK47' does not appear in R6-6), so a session could fix the code and leave the source document stale.

### 2026-08-24d

DONE, and the site list in this row was INCOMPLETE -- it named five, there are NINE. docs/perf-round6-audit-2026-08.md names WildcardIndex.check at :218 (full findings table), :375 (### R6-6 entry header), :387/:391/:395 (the R6-6 verbatim blocks), :669/:673/:677/:685 (the ### R6-18 verbatim blocks -- the select(EdgeV4.id) existence probe, which moved with the same BL-2 split) and :805/:925 (appendix leads A4, A14). Re-grep; do not trust a site list in a task row. FIXED IN PLACE: only the doc's OWN non-verbatim claims -- the R6-6 read-path verdict row, the R6-6 full-findings row, the ### R6-6 entry header -- all now name ::WildcardIndex._check_internal. LEFT VERBATIM, deliberately: every >-quoted finder/verifier block. Those are the record of what was said on 2026-08-15/17; editing quoted evidence to match today's tree is how provenance is destroyed. A dated symbol-correction note under the file's status banner covers all of them at once and states why a file::symbol anchor gate is structurally blind to this class (anchor_check.py reads only CORRESPONDENCE.md, and both names exist anyway). The audit's ### R6-6 entry also gained a LANDED note, since R6-6 landed in the same session. SECOND DEFECT FOUND, NOT FIXED HERE: the status banner's 'Nothing here is landed' is now false twice over (R6-10 2026-08-20b, R6-6 2026-08-24d). TK48 owns that banner and its trap says to correct it from the body -- recorded in TK48 so both clauses are fixed in one reviewed edit. Also corrected, en route: benchmarks/profile_r6.py's Run block told readers to size the two GRAPH targets with --scale, which those targets do not take (they read --graph-scale), so '--target graph-check --scale 400' silently ran the default 200. No recorded R6 figure is affected -- the statement counts are scale-invariant -- and the R6-6 landing measurement states the scale it actually ran at. And tests/test_reads.py:54's 'warm the w-id cache' comment, untrue since W2.
