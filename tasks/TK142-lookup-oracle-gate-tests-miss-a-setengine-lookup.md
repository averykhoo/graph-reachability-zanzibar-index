---
id: TK142
title: lookup-oracle gate_* tests miss a SetEngine.lookup_reverse that drops excluded_node_ids (TK139 gap)
brief: lookup-oracle gates stay green with lookup_reverse exclusions dropped; only scripted pins catch it
pri: NOW
size: M
deps: []
related: [TK139]
parent:
labels: []
source: docs/tk139-lookup-reverse-exclusions-2026-10-13.md
source_hash:
created: 2026-10-13d
moved: 2026-10-14
updated: 2026-10-14
closed:
---

Filed by the TK139 review (session 2026-10-13d). The broad lookup-oracle gates in
`tests/test_lookup_oracle.py` do NOT catch a `SetEngine.lookup_reverse` that drops
`excluded_node_ids`, although their S3 check (`_check_set_reverse`) is two-sided on it.

RUN first-hand 2026-10-13d (fix lead): the TK139 fix line
`result.excluded_node_ids = set(m.neg)` in `src/zanzibar/setengine/engine.py::SetEngine.lookup_reverse`
replaced by `pass`, then `pytest tests/test_lookup_oracle.py -k gate`: `9 passed, 38
deselected` (rc 0). Every `test_lookup_oracle_gate_*` stayed green: `_gate_wildcards`,
`_gate_boolean`, `_gate_demorgans_reverse`, `_gate_owc_star_ttu` and the generated-schema
gates. Only the scripted `test_lookup_oracle_dense_boolean`, the tamper test
`test_tamper_set_reverse_is_caught` and the TK139 pins
(`tests/test_tk139_lookup_reverse_exclusions.py`) catch it.

Cause (REASONED, not yet measured): no gate fixture/pool reaches a reverse lookup whose
`expand` has a non-empty `neg`, i.e. a `but not` / `and` under a SUBJECT wildcard
(`[user:*]`) with an interned refused subject. The generated pool rarely builds that shape.

Done when: at least one broad gate (a seeded fixture walk or the generated-schema gate)
goes RED under the same sabotage, with the observed output recorded in its docstring; and
a coverage tripwire (count of reverse lookups with non-empty `neg` seen by the gate,
asserted > 0) so the gate cannot silently lose the shape again.

Map: `docs/tk139-lookup-reverse-exclusions-2026-10-13.md` sec 5 and its dated correction.

## Log

### 2026-10-13d

Why NOW (fix lead decision, 2026-10-13d): closing TK141 left no NOW row, so lint was red. TK142 is a gate that PASSES under a known regression, the house failure mode, and is on the current goal (an honest assurance surface). The only other NEXT row, HS-5, is a doc-liveness tidy. The coordinator or the next session may re-rank with promote --demote.

### 2026-10-14

Scout + challenge + build, 2026-10-14. Map: docs/tk142-lookup-oracle-exclusion-gap-2026-10-14.md (ACTIVE-PLAN; challenge corrections at the top).

MEASURED (scout PROBE, re-measured by challenge c1_census): on the fixed gates as of HEAD 0b09687, S3 calls with a non-empty neg and graph lookup_reverse results with a non-empty excluded_node_ids are 0 in every config (wildcards, boolean, demorgans 6 steps, owc_star_ttu). Proposed parameters reach the shape: demorgans_reverse 12 steps s3=8/1120 g34=4/560 (31.7s); boolean seed 4 s3=6/896 g34=3/448 (24.1s).
Challenge corrections: C1 the set-side mutant M1 WAS already caught by a broad gate, by seed luck, in another module (tests/test_tk116_oracle_only_setengine.py::test_generated_refused_schemas_run_the_set_only_lookup_gate, set-only, s3=10), so the true uncaught regression was G1 (graph side) in every seeded broad gate. C2 TestLookupSurfaceMachine is a coin flip, not blind (G1 caught 4/8). C3 hypothesis Phase.reuse can replay a stored failure under a sabotage. C4 the forward SetEngine.lookup exclusion channel (F1) has the same gap. C5 plan deltas (tripwire on the existing TK116 catch, witness test pointed at graph-joined seeds, count from the set-side instrument, keep walk_steps 6 for drain states, run doc_counts once last).

BUILT (worktree-wf_9a094007-20b-11 @69080d4, tests only, 2 files: tests/test_lookup_oracle.py, tests/test_tk116_oracle_only_setengine.py; reviewer APPROVE): _Gate counters set_reverse_neg / set_reverse_neg_graph_joined / graph_reverse_excl / set_forward_excl (last one counted only); gate_boolean seeds [0,1,4] with tripwire on seed 4; gate_demorgans_reverse walk_steps [6,12] with tripwire on 12; new test_lookup_oracle_gate_generated_schemas_exclusion_witness (>= 2 graph-joined witnesses, seeds 11 and 28, plus refused seed 4); summed set_reverse_neg > 0 tripwire on the TK116 walk. Sabotage observed in the commit message: M1 4 failed/3 passed, M2 same 4 via the oracle half, G1 3 failed/4 passed, the row's original M1 as a src edit 3 failed/9 passed/38 deselected (was 9 passed), each tripwire red on its own message. Done-when met on both sides. Not run there: full phased gate; doc_counts --generate left to the coordinator (run once, last, after TK137/TK138 land: C5(e)).

OPEN, filed as rows (LATER; the requested label tests is not in tasks/config.json vocabulary, so filed unlabelled): TK148 forward lookup exclusion channel caught only by scripted pins (C4, F1); TK145 TestLookupSurfaceMachine catches G1 about half the time (C2); TK146 hypothesis Phase.reuse / example DB can fake a sabotage catch (C3).
Next action: coordinator merges 69080d4, runs the phased gate, then closes TK142. Not closed here.
