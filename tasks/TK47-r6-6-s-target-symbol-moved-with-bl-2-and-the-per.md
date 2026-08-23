---
id: TK47
title: R6-6's target symbol moved with BL-2 and the perf audit still names ::check (both resolve)
pri: LATER
size: S
deps: []
related: []
parent: R6
labels: [docs]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed:
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
