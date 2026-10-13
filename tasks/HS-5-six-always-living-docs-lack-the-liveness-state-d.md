---
id: HS-5
title: always-living docs declare no liveness state; enumeration+method now in docs/README.md sec 2
brief:
pri: NOW
size: S
deps: []
related: []
parent:
labels: [docs]
source: board
source_hash: 31c0d00522ce
created: 2026-08-20b
moved: 2026-10-13b
updated: 2026-10-13b
closed:
---

always-living docs declare no liveness state, though [`docs/README.md`](docs/README.md) §2 requires one in the first lines. **The count is method-sensitive and does NOT live here — it lives in `TK49`.**

The deliverable is not the count: it is adjudicating which of the measured docs are *deliberately* exempt from §2. That half is untouched.

## Traps

⚠ **Do not restate the count in this row.** It read six, then nine, then eleven across three days, so any figure written into this title or body rots again — which is why `TK49` (the child) owns it and this row points there. Corrected 2026-08-24b: the body still said "six" after the 2026-08-24 retitle fixed only the title, so the retracted figure survived one layer down. That is the same one-summary-row-contradicting-its-own-child disease the A/B recorded as finding `P4`.

## Read first

- `python scripts/task.py show TK49` — the child that owns the measured count and its method
- ledger `2026-08-20`, then `2026-08-24` (the retitle and the reason for it)

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-20b`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer. The title is RE-WORDED (not clipped) to fit the 100-char cap without weakening the claim; the board cell survives verbatim above.

### 2026-08-24b

Body drift, and it was a WRONG FIGURE, not a formatting difference. The 2026-08-24 retitle fixed the title and left the body asserting 'six always-living docs' -- the exact retracted count TK49 corrects. Body rewritten to mirror the board cell (no count here; TK49 owns it), a trap added against restating it, and the read-first now points at TK49. source_hash re-stamped to the current board block.

### 2026-08-29b

Row rewritten 2026-08-29b: it used to read 'count is method-sensitive, it lives in TK49, not here' -- the board delegating its substance by id into the tasks/ tree, a dangling referent if the trial verdict is DELETE. The enumeration and the measuring method now live in docs/README.md sec 2 itself; the row points there and carries no count, and neither does sec 2. What remains open on this row is the adjudication: which of those docs are deliberately exempt. Child TK49 closed the same session, its scope correction having landed.

Second re-stamp this session: the row was edited again while trimming HANDOFF.md to its line ceiling. Content unchanged in substance -- it still points at docs/README.md sec 2 for the enumeration and method, still carries no count, and the open adjudication (which docs are deliberately exempt) is unchanged.

Third re-stamp this session, all mechanical: the row was compressed while trimming HANDOFF.md back to its 260-line ceiling. Substance unchanged -- it still points at docs/README.md sec 2 for the enumeration and method, still carries no count, and the open adjudication is unchanged.

### 2026-10-13

2026-10-13 (lane L5, assurance batch). LANDED: the two TK106 companion docs are FROZEN. `docs/tk106-triage-2026-09-26.md` and `docs/tk106-agent-reports-2026-09-26.md` said 'FROZEN with it when `TK106` closes' (TK106 closed 2026-09-26b) but carried no banner, which broke docs/README.md sec 2 'Freeze at landing'. Each now opens with the sec 3 blockquote banner, dated 2026-10-13 and stating that it was applied late. Each also has a dated correction saying its tainted-tupleset names are historical (TK107 deleted them, census `docs/tk107-tainted-tupleset-removal-2026-10-05.md` sec 1) and that TK120 rewrote its body paths to `src/zanzibar/...` mechanically. No check was added, so there was no sabotage to run.

REMAINING SCOPE (evidence: assurance triage agent-B, 2026-10-13, re-checked first-hand where marked READ):
(a) READ: the docs/README.md sec 2 'Not yet adjudicated' list is incomplete. By sec 2's own method (a bolded LIVING/FROZEN/ACTIVE-PLAN in the first 8 lines) over the candidate set docs/*.md + docs/architecture/*.md + docs/specs/*.md + formal/*.md, these undeclared docs are NOT in the list: `docs/README.md` itself, `docs/subagent-fanout-runbook.md`, `docs/architecture/{overview,derived-predicates,graph-index,system,theory,verification,bulk-merge-design}.md`, and `formal/REFERENCES.md`. Also, `docs/specs/` now holds four specs (incl. `connected-store-spec.md`), not 'the three'. And sec 2's 'two benchmarks/results/ profiles' is ambiguous: `PERF_ANALYSIS.md` and `STMT_BASELINE_2026-07-14.md` DO declare LIVING. Per the row trap, no count is given here.
(b) READ: `scripts/handoff_lint.py::check_frozen_banners` scans only `HISTORY_DIRS = ('docs/history', 'formal/history')`, so nothing checks docs/, docs/architecture/, docs/specs/ or formal/*.md.
(c) NEW, a Freeze-at-landing class the row did not name. REASONED: a filename-prefix heuristic matched against `tasks/closed/`, with the first declaration in the first 8 lines read. These docs are still headed ACTIVE-PLAN although their row is in tasks/closed/: `docs/tk106-boolean-tuplesets-2026-09-26.md` (the parent of the two docs just frozen), `docs/tk108-userset-tuplesets-2026-09-27.md`, `docs/tk126-ttu-target-boolean-name-2026-10-07.md`, `docs/tk70-detonation-2026-09-17.md`, `docs/tk73-cascade-quiesce-gc-2026-09-17.md`, `docs/tk78-offline-bootstrap-audit-2026-09-20.md`, `docs/tk83-star-intersection-fixture-2026-09-20.md`, `docs/tk87-swarm-churn-2026-09-19.md`, `docs/tk89-census-reproducibility-2026-09-20.md`, `docs/tk91-tk80-removal-coverage-2026-09-20.md`, `docs/tk92-bulk-rel-term-2026-09-21.md`, `docs/tk93-ensure-raw-seed-dependence-2026-09-21.md`. (`docs/r6-sizing-census-2026-09-22.md` also matched, but only because the closed R6-* sub-rows share its prefix. UNVERIFIED which row it belongs to.) A mechanical check for this is cheap: an ACTIVE-PLAN doc named `<id>-...` whose row is in tasks/closed/ is RED.
(d) READ, same TK107 residue class as the HANDOFF Still-owed bullet but outside its three docs: `formal/SEMANTICS.md` sec 5.5 (~l.356, 2026-10-13) cites `processor.py` `_ts_leaf_predicates` as live, and `formal/ARCHITECTURE.md` (~l.277) cites `processor.py::_EvalContext.tupleset_ttu_check`. Both symbols have 0 hits under src/ (grep -w, 2026-10-13). Also comment-only: src/zanzibar/schema/boolean.py (PClosureLeaf docstring; plan-builder comment ~l.474) still gives the pre-TK107 reason for storage leaves.

SIZE: M, not S. SINGLE NEXT ACTION: freeze the ACTIVE-PLAN docs in (c) whose rows are closed, using the same sec 3 banner. Then extend `handoff_lint.py::check_frozen_banners` (or add a sibling) to RED on an ACTIVE-PLAN doc whose row id is closed, with a sabotage test. Only after that, adjudicate (a) and write the exemption rule into docs/README.md sec 2.
