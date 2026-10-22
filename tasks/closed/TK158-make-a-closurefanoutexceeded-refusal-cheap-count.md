---
id: TK158
title: Make a ClosureFanoutExceeded refusal cheap: count before loading, undo instead of rebuild
brief: 0.1.0 BLOCKER: a refused 1M-member grant costs 91 s / 3.8 GB (TK150 sec 4); count first, undo one tuple
pri: NEXT
size: M
deps: []
related: [TK150]
parent:
labels: []
source: docs/closure-fanout-cost-2026-10-14.md
source_hash:
created: 2026-10-16
moved: 2026-10-22
updated: 2026-10-22
closed: 2026-10-22
---

Filed 2026-10-16 from TK150 (proposed text in `docs/closure-fanout-cost-2026-10-14.md` § Correction 2026-10-16 (e) item 1, verbatim below).

Measured in `docs/closure-fanout-cost-2026-10-14.md` sec 4: the cap bounds what
is written, not what a refusal costs. Two causes (READ 2026-10-16, still open):
`core.py::ReachabilityIndex._add_direct_edge_unsafe_impl` loads the ancestor and descendant
sets as full ORM `Edge` rows before counting; and `src/zanzibar/store/_store.py::Store._write`'s
error arm calls `self.source.refresh_evaluator()` (a whole set-engine rebuild, 39.8 s at
1M tuples) because admission already put the tuple into the evaluator. Proposed: count |A|
and |D| with `SELECT count(*)` and refuse before loading; on `IndexResourceLimit`, undo
the one admitted tuple in the evaluator instead of rebuilding. Acceptance: re-run
`point --shape userset --n 1000000 --mode refuse` and show the refusal well under 1 s;
a test that the evaluator matches a fresh rebuild after a refusal. Changes no modelled
algorithm (the count precedes the modelled expansion), but check `formal/CORRESPONDENCE.md`.
Run the PostgreSQL leg (locking path).

## Read first

- `docs/closure-fanout-cost-2026-10-14.md` sec 4 (the refusal path) and § Correction 2026-10-16

## Log

### 2026-10-20b

0.1.0 BLOCKER (user, 2026-10-20b, in chat). Anyone who sets ZANZIBAR_MAX_CLOSURE_FANOUT hits this: the cap correctly refuses a grant through a 1M-member group, but the refusal costs 91 s and 3.8 GB (docs/closure-fanout-cost-2026-10-14.md sec 4), because the edge add loads full ORM Edge rows before counting and Store._write then rebuilds the whole set engine. A refusal that expensive is a user-facing bug, not perf tuning, so it is not covered by the perf deprioritization. Plan unchanged from the body: count first, undo the one admitted tuple instead of rebuilding. No modelled algorithm changes, so no Lean work expected (confirm against formal/CORRESPONDENCE.md). Run the PostgreSQL leg.

### 2026-10-22

PLAN stage done (lane TK158, no product edits). Plan: docs/tk158-cheap-fanout-refusal-2026-10-22.md (ACTIVE-PLAN). LANDED: census of both sites + a THIRD cost (lazy set-engine flow-graph build, SetEngine._ensure_flow_graph, O(store), 21.07 s at 1M, paid by the first write after open and re-armed by every refresh_evaluator); before figures 2026-10-22: 1M userset refusal 78.89 s / 3,827 MB cold; count(*) of A = 1,000,000 in 0.180 s vs ORM load 26.86 s. DESIGN: D1 two indexed count(*) before the loads, refuse before loading (cycle point lookup first to keep precedence), runtime-assert len(A)/len(D) equal the counts on admitted writes; D2 TupleSource records the last admission + prior watermark, Store._write gets an except IndexResourceLimit arm that undoes via engine.apply_logged(inverse op) and restores the watermark (rebuild only as fallback). Acceptance is measured WARM (cold first write still pays the flow-graph build; out of scope, D4). Lean: no modelled algorithm change, but the anchor content pin for _add_direct_edge_unsafe_impl goes red and CORRESPONDENCE sec 7.3 resource-refusal bullet needs a dated correction, then claim_rot.py --generate (orchestrator, once, after TK3). NEXT: IMPLEMENT stage per plan sec 2/4/6.

BUILD stage (not committed, gate not run by this lane). LANDED: D1 count-first in src/zanzibar/graphindex/core.py (::_closure_region_counts, ::_reverse_edge_present, ::_raise_closure_fanout; runtime count==load assertion on admitted capped writes); D2 undo in src/zanzibar/store/source.py::TupleSource.undo_last_admission + Store._write except IndexResourceLimit arm (rebuild only as fallback); benchmarks/fanout_cost_bench.py point --warm. TESTS: tests/test_tk158_cheap_refusal.py 16 green on SQLite and PostgreSQL; sabotage M1-M8 all RED, literal output in its docstring. ACCEPTANCE (SQLite 1M userset refuse, 2026-10-22): before 78.89 s / 3827 MB cold; after cold 15.82 s (15.63 s = first-write flow-graph build, D4), warm refusal 0.199 s then 0.146 s, 0 MB. PG 100k warm 0.044 s. RED: tests/test_postgres_ha.py::test_tk154_* (2) fail on PG, pre-existing at HEAD 78b935a. NEXT: orchestrator gate + CORRESPONDENCE sec 7.3 correction and claim_rot.py --generate, CHANGELOG Fixed line, userdocs limits.md rewrite. Body: docs/tk158-cheap-fanout-refusal-2026-10-22.md Correction 2026-10-22.

REVIEW (assurance, 2026-10-22): reviewer mutants S1 undo-skips-REMOVE-inverse, S2 count-block > to >=, S3 D-count drops store_id, S5 reverse lookup direction swapped all go RED; S4 (count==load mismatch guard disabled) stays GREEN 35/35, so the runtime guard is unpinned although a probe shows it is reachable (planted zero-indirect row: count (4,0) vs loaded (3,0)). tests/test_tk158_cheap_refusal.py::_old_lengths uses a set len, not the old MultiSet len, so it is not verbatim. Fix both before close. Raw: .scratch/tk158-tk3/tk158-review.md

FIX stage: all six review findings fixed, see docs/tk158-cheap-fanout-refusal-2026-10-22.md Correction (FIX stage). LANDED (uncommitted): count block skipped while the cap is suspended (core.py); pg_local.sh destroy removes only the cluster dir, refuses a non-cluster; tests 8-10 in tests/test_tk158_cheap_refusal.py (mismatch guard, suspended path, PathCountExceeded undo) + MultiSet _old_lengths; new tests/test_pg_local_destroy.py; CORRESPONDENCE 7.3 dated correction. Sabotage F1-F4, P1-P2 all RED then restored. RED: claim_rot pin (regenerate once after both lanes); tk123 docstring test red on TK3 cascade_mark.py I5. Next: orchestrator gate + integrations.

LANDED 2026-10-22 (ultracode wf_2c9dfdfc-f9c: plan, build, 2 adversarial reviewers, fix; plan doc docs/tk158-cheap-fanout-refusal-2026-10-22.md). core.py::ReachabilityIndex._closure_region_counts counts |A|/|D| with two indexed count(*) before any load (cycle still reported first via _reverse_edge_present; skipped on the suspended path); store/source.py::TupleSource.undo_last_admission undoes the one admitted tuple, called from Store._write on IndexResourceLimit (rebuild only if the undo fails). Acceptance: 1M-member refusal 78.9 s / 3.8 GB cold before -> 0.15-0.20 s warm, 15.8 s cold (15.6 s is the first-write flow-graph build, out of scope D4); PG 100k warm 0.044 s. tests/test_tk158_cheap_refusal.py (20) incl. evaluator == fresh rebuild after a refusal, PathCountExceeded undo, count==load guard; sabotage outputs in its docstring. PG leg: those + HA modules green 2026-10-22 (orchestrator, first-hand). Also: scripts/pg_local.sh destroy no longer deletes the parent of ZANZIBAR_PG_DATA (it erased the session scratchpad during this run), tests/test_pg_local_destroy.py. No modelled algorithm changed; CORRESPONDENCE 7.3 corrected in place, anchor pin regenerated. Kept by decision: an over-cap write on an I1-corrupt store reports ClosureFanoutExceeded, not the corruption.
