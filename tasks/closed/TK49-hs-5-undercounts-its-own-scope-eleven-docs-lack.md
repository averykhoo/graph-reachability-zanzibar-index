---
id: TK49
title: HS-5 undercounts its own scope: eleven docs lack a liveness banner, its title says six
brief:
pri: LATER
size: S
deps: []
related: []
parent: HS-5
labels: [docs]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-29b
updated: 2026-08-29b
closed: 2026-08-29b
---

`HS-5`'s title and body both say **six** always-living docs declare no liveness state. The measured count is **eleven**:

`formal/CORRESPONDENCE.md`, `formal/ARCHITECTURE.md`, `formal/FINAL_REVIEW.md`, `formal/SEMANTICS.md`, `formal/HANDOFF.md`, `docs/gate-runbook.md`, `docs/specs/wildcard-materialization-spec.md`, `docs/specs/set-engine-spec.md`, `docs/specs/graph-boolean-ivm-spec.md`, `benchmarks/results/BASELINE_2026-07-13.md`, `benchmarks/results/R6_PROFILE_2026-08-17.md`.

That is `ZT-P3-5` (a stale figure in a durable place) recurring inside a board row filed the day before it was measured. The row is a child of `HS-5` because it is a scope correction to it, not separate work.

**Two deliverables, in order.** (1) Adjudicate: some of the eleven may be deliberately exempt from `docs/README.md` §2 — that adjudication IS the work and it has not been done. (2) Re-title `HS-5` so it stops carrying a count: `task.py set HS-5 title "..."`. The parent row's own defect is that it restates a number in a durable place; replacing six with eleven repeats it, and the correct title names the class and points at the measurement.

## Traps

⚠ **Do not just change six to eleven.** The measured figure was six-then-nine-then-eleven across three readings on three days. A title that carries a count will rot again; a title that names the RULE will not.

⚠ **The sweeps' "at least nine" and this "eleven" are different measurements.** The sweeps named docs they happened to open; this is a direct read of the first 8 lines of a candidate list. Re-measure before quoting either, and say which method you used — the count is method-sensitive, exactly like the `NodeV4` 217/49 split.

⚠ **Exempt is a real verdict, and it must be recorded where the exemption is readable.** "This file needs no banner" written only in a task Log is a fact with no home; `docs/README.md` §2 is the home.

## Read first

- `python task.py show HS-5` — the parent row this corrects
- [`docs/README.md`](docs/README.md) §2-§3 — the liveness states, the banner form, and where an exemption would be recorded
- `.scratch/tasktool/COVERAGE.md` §C5 — the measurement and the eleven paths

## Log

### 2026-08-21b

**Provenance.** Surfaced and MEASURED by this project's own work: COVERAGE.md §C5 read the first 8 lines of each candidate and found eleven with no LIVING/FROZEN/ACTIVE-PLAN state. Re-measured independently this pass over the same eleven paths: 11/11 still banner-less.

### 2026-08-24

Deliverable (2) DONE 2026-08-24: HS-5 retitled to 'always-living docs lack the liveness state docs/README.md sec 2 requires; count lives in TK49', and the HANDOFF.md row edited to match. The retitle followed this row's own trap -- the count was NOT copied into the new title, because six-then-nine-then-eleven across three readings is exactly what a title carrying a count does. Deliverable (1), the adjudication of which of the measured docs are deliberately exempt, is STILL OPEN and is the actual work here. Found during the task-tool trial: 9 of 9 BOARD-arm agents answered 'six' from the board row, and the tree agents answered 'six' too, because they stopped at HS-5's title rather than following 'children: TK49' one hop.

### 2026-08-29b

Scope correction LANDED, which is all this child was filed to carry. The enumeration and the measuring method now live in docs/README.md section 2 (re-measured 2026-08-29b: bolded LIVING/FROZEN/ACTIVE-PLAN within the first 8 lines), and HANDOFF.md's HS-5 row was repointed there in the same edit -- it previously read 'count lives in TK49', i.e. the board delegated its own substance by id into a tree that may be deleted, a dangling referent. Neither doc carries a count: the figure has read six/nine/eleven/this-list across four readings by four methods. The remaining ADJUDICATION (which docs are deliberately exempt) stays open on HS-5, where it belongs.
