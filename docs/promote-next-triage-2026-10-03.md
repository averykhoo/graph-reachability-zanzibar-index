# Which LATER row most raises confidence that the Python is correct? (2026-10-03c)

**ACTIVE-PLAN** (`docs/README.md` sec 3). Corrections are appended **dated at the top** of sec 1.
Freeze when the promotion decision it feeds is made and recorded on the rows.

**2026-10-06 (`TK120`):** the code moved into the `src/zanzibar/` package and lost its version suffixes after this doc was written; its paths and class names are the OLD ones. Key: `docs/architecture/overview.md` § "Renamed in TK120".

## 1. Question, method, provenance

**Question (user, 2026-10-03c):** which `LATER` row, promoted to `NEXT`, would most increase
confidence that the Python is correct -- graph index = set engine = oracle, and the parsers
refuse and accept the same schemas.

**Method.** One `Workflow` run, `wf_f60df09d-6c7` (2026-10-03c). Six triage agents, one themed
batch each (oracle/parser, coverage/grid, runtime/async, Lean, perf, process/docs), covered
all `LATER` rows. Each read the row with `task.py show`, checked the cited `file::symbol` in
the live tree, and scored the likelihood of an undetected bug (`p`, 0-3) and how directly
doing the task would surface or remove it (`det`, 0-3). The four top scorers then each got a
skeptic told to REFUTE the case (already closed? already covered by an existing test?
unreachable from a checked parse? size underestimated?).

**Provenance.** Everything in secs 3-4 is AGENT-REPORTED. Several agents ran probes. Their
probe scripts sat in the gitignored `.scratch/promote-next/` and are not preserved, so the
probe RESULTS recorded here are the only copy. The session did not re-run any probe
first-hand. Before acting on a row, re-verify its cited witness. The skeptics checked only
the top four; `TK109` and `TK114` (sec 2) were triaged but NOT adversarially verified.

## 2. Synthesis (REASONED, by the session, from secs 3-4)

**No row in `LATER` describes a known live wrong-answer bug.** Every probed defect is an
availability failure, a silent widening upstream of all evaluators, or a spot where the
referee is not independent. All four verified rows came back WEAKENED, and none was refuted
outright on whether the gap exists.

Ranked recommendation for `NEXT` (cap 3):

1. **`P23` + `TK109` (+ `TK105`, subsumed by `TK109`): one parser-agreement push, size S+S.**
   `P23` is the only row with a reproduced consequence in shipped `ConnectedStore`.
   A schema both parsers accept, for example `define *: viewer but not blocked`, makes a
   VALID write refuse on sync, and stalls the index permanently on async. Answers stay
   correct, so this is a backend accept/reject split, not a divergence. `TK109` has the
   oracle parser accept 7 shapes production refuses, so the oracle cannot referee
   refusals. Both close with a `_validate_*` refusal in each parser, pinned
   both-refuse. This is the cheapest direct hit on "the parsers refuse and accept the
   same schemas".
2. **`TK114`: a non-stratifiable negation cycle through a TTU target.** The set engine and
   the oracle agree on answers that are NOT models of the schema, because they share the
   in-progress=>False convention. On this shape the oracle is not an independent referee,
   which is the deeper confidence leak. Exposure is a standalone `SetEngine`
   (`ConnectedStore` refuses it). NOT adversarially verified.
3. **`TK117`, scoped to its part (c) only: a deterministic write-local floor in
   `tests/parity.py::ParityEngine._grid`.** The skeptic measured sub-gaps (a)/(b) as
   already covered elsewhere. It measured (c) as real but modest: about 12% of grid builds
   exceed the cap, and those keep about two thirds of the pool (AGENT-REPORTED, 2026-10-03c).
   It is cheap, and it raises the sensitivity of the default integration engine everywhere.

**Not recommended, with reasons:**
- `TK110`: the skeptic called it near-refuted. Three sabotages, including `TK71`'s S1, all
  went red through the parity drivers. Keep it at `LATER` as hygiene (narrow the bare
  `except ValueError`).
- `TK115`: a real fail-open in a public API. `"wildcard": false` renders `[user:*]`.
  But it sits upstream of all three evaluators, and nothing in the product calls it. It is
  off-question for equivalence, but worth a separate look as a security-shaped bug.
- The perf, process/docs and Lean rows scored 0-1: no concrete Python-correctness consequence.

## 3. Triage table, all LATER rows (AGENT-REPORTED 2026-10-03c, workflow `wf_f60df09d-6c7`)

Score = `p_undetected_bug x detection_power` (each 0-3), minus 3 if the agent could not confirm the gap is still live. Sorted by score. `live?` = the triage agent confirmed the gap in the live tree. Only the top four were adversarially verified (sec 4).

| score | id | kind | live? | p | det | size | title |
|---|---|---|---|---|---|---|---|
| 6 | `TK117` | detect-python-divergence | y | 2 | 3 | M | ParityEngine._grid never asks object-* targets or star from-chain subjects; cap sample gaps |
| 4 | `P23` | refuse-silent-acceptance | y | 2 | 2 | S | declared-name charset asymmetry between the oracle parser and zanzibar_utils_v1 |
| 4 | `TK115` | fix-python-latent-bug | y | 2 | 2 | M | JSON front-end fidelity: openfga_json_to_dsl can render a different schema than the JSON declared |
| 4 | `TK110` | refuse-silent-acceptance | y | 2 | 2 | M | census tests/ for drivers that absorb an admission refusal into a smaller compared store |
| 2 | `TK109` | detect-python-divergence | y | 1 | 2 | S | oracle parser silently accepts 7 schema shapes the product parser refuses |
| 2 | `TK114` | refuse-silent-acceptance | y | 1 | 2 | M | refuse non-stratifiable negation: a derived cycle through a TTU target with a but-not subtrahend |
| 2 | `TK116` | detect-python-divergence | y | 1 | 2 | M | oracle-only SetEngine mode: set-vs-oracle differential with removes for every decision-15 family |
| 2 | `TK101` | detect-python-divergence | y | 1 | 2 | M | object-wildcard WRITES are unenumerable: _tuple_space emits '*' only as a subject |
| 1 | `TK105` | detect-python-divergence | y | 1 | 1 | S | oracle parser silently keeps the last duplicate define; production refuses it |
| 1 | `TK119` | lean-proof | y | 1 | 1 | S | keyLeafRewrites row: the 50/50 schemas leaf-rule claim is unbacked; make it a test or drop it |
| 1 | `TK3` | other | y | 1 | 1 | M | I9 fixpoint audit is test-only and 'writes always cascade' is convention, not a check |
| 1 | `TK44` | detect-python-divergence | y | 1 | 1 | M | ~30% of the generator pair-cell space is unreached even at deep budget, with UNKNOWN residue |
| 1 | `P16` | detect-python-divergence | y | 1 | 1 | M | widen the enumeration/state bounds |
| 1 | `TK102` | detect-python-divergence | y | 1 | 1 | M | take the derived-userset corpus into test_conformance_enum._SHAPES |
| 1 | `TK79` | detect-python-divergence | y | 1 | 1 | S | late-GC outbox rows' 'a drain_deltas replica must see them' justification is pinned by nothing |
| 1 | `TK121` | other | y | 1 | 1 | S | async poison row (path-count bound) has no documented recovery; pin rebuild-from-snapshot |
| 1 | `TK118` | other | y | 1 | 1 | M | should ZANZIBAR_PARANOIA=residue carry the I14 crossing-middle check? |
| 1 | `P15` | lean-proof | y | 1 | 1 | L | remaining fragment leaves -- PDerivedTTU/PDerivedUserset arms, twoStrata cap |
| 1 | `P9` | lean-proof | y | 1 | 1 | M | lift the remove-gate exclusion (direct_arm_exclusion) |
| 1 | `P6` | lean-proof | y | 1 | 1 | L | ttuStarFree (ii) -- bridge on the leaf-routed write path (parked) |
| 1 | `P7` | lean-proof | y | 1 | 1 | M | ttuStarFree (iii)+(iv) -- re-prove the 5 consumed sites, widen the gate |
| 0 | `TK107` | other | y | 0 | 1 | M | remove (or mark) the tainted-tupleset code path TK106 made unreachable |
| 0 | `TK6` | lean-proof | y | 0 | 0 | S | leaf-family split: is storage=True/False modellable as one leaf? unresolved at 4 dates |
| 0 | `TK99` | process-docs | y | 0 | 1 | S | MIN_TESTS_ALL is ratcheted by hand; min_tasks_parsed already solved this mechanically |
| 0 | `P11` | other | y | 0 | 0 | S | the fixture-TRIPLE question for 5 subsumed .fga fixtures |
| 0 | `TK85` | other | y | 1 | 0 | S | give audit_fixpoint (I9) a production-reachable entry point (repair/diagnosis) |
| 0 | `TK11` | lean-proof | y | 0 | 0 | M | ResidueV1.version (I7) is modelled by nothing formal |
| 0 | `TK62` | process-docs | y | 0 | 0 | M | nothing checks the R6-N transcribed figures against the audit they came from |
| 0 | `TK34` | perf | y | 0 | 0 | M | benchmarks/canary.py nightly perf tripwire |
| 0 | `TK120` | other | y | 0 | 0 | L | Repo restructure: drop version suffixes and re-lay-out the code |
| 0 | `P8` | lean-proof | y | 1 | 0 | S | write W4WitnessSelfRef (board B2) |
| 0 | `TK54` | process-docs | y | 0 | 0 | S | Scratch4cii.lean is a tracked module inside the gated proof tree -- delete or justify |
| 0 | `TK103` | process-docs | y | 0 | 0 | S | audited Lean names vs headline dependency closure |
| 0 | `TK67` | process-docs | y | 0 | 0 | S | FoldAdmits lockstep 21/24 correction not carried by live docs |
| 0 | `TK66` | process-docs | y | 0 | 0 | M | directives that live only in formal/history/ are invisible to the tree |
| 0 | `AW-1` | process-docs | y | 0 | 0 | S | FINAL_REVIEW.md sec 4(d) under-claims after the remove leg |
| 0 | `B2` | other | y | 0 | 0 | ? | historical grouping of P8 + P9 (container, not work) |
| 0 | `R6` | perf | y | 0 | 0 | L | perf round 6 parent |
| 0 | `R6-1` | perf | y | 0 | 0 | L | set-engine lookup fresh memo per candidate |
| 0 | `R6-4` | perf | y | 0 | 0 | L | boolean graph lookup full-scans residue rows |
| 0 | `R6-5` | perf | y | 0 | 0 | ? | lookup builds full ORM rows |
| 0 | `R6-7` | perf | y | 1 | 0 | S | I10 outbox sanity rescans whole outbox |
| 0 | `R6-8` | perf | y | 1 | 0 | S | delta verifier one BFS per pair |
| 0 | `R6-9` | perf | y | 0 | 0 | S | write-tail refcount re-SELECTs nodes |
| 0 | `R6-11` | perf | y | 0 | 0 | S | residue cache torn down per reconcile_subject |
| 0 | `R6-16` | perf | y | 1 | 0 | L | outbox row per closure flip without boolean consumer |
| 0 | `R6-18` | perf | y | 0 | 0 | M | EdgeV4 surrogate PK |
| 0 | `R6-19` | perf | y | 0 | 0 | ? | bulk edge audit ~139 plan evals |
| 0 | `GC-1` | process-docs | y | 0 | 0 | M | check_restated_counts sees neither percentages nor .py files |
| 0 | `HS-5` | process-docs | y | 0 | 0 | S | always-living docs declare no liveness state |
| 0 | `TK100` | process-docs | y | 0 | 0 | S | fence inside banner section is unpinned behaviour |
| 0 | `TK86` | process-docs | y | 0 | 0 | S | HANDOFF trap-badge budget counts one glyph; (!) evades it |
| 0 | `TK97` | process-docs | y | 0 | 0 | M | lint check 15: Still-owed bullet may not survive two sessions |
| 0 | `TK98` | process-docs | y | 0 | 0 | S | receipt vocabulary cannot express 'entered via show' |
| -3 | `P25` | lean-proof | n | 0 | 0 | M | Star tupleset over a DERIVED through-relation: Python handles it, the fragment excludes it, unproved |
| -3 | `P21` | lean-proof | n | 0 | 0 | S | a fourth zcli mode so a fragment predicate can be DIFFERENTIALLY checked, not mirrored |
| -3 | `TK81` | process-docs | n | 0 | 0 | S | skipped-reconcile staleness is TRANSIENT, so any periodic audit is worth about zero |
| -3 | `TK84` | process-docs | n | 0 | 0 | S | two scratch census probes have a non-deduping generator |

Missing verdicts: none

### 3.1 Bug class and reasoning for every row scored >= 1

**`TK117`** (score 6). *Bug class:* A graph or set-engine wrong answer on an object-* target, on a star from-chain userset subject, or on the last write's own queries when the grid exceeds grid_cap passes the default integration engine (and the hypothesis stateful machine built on it).

*Evidence the agent read:* tests/parity.py::ParityEngine._note_names skips '*' for objects; ::_grid builds Layer A objects from _names_by_type + GHOST only (no '*'), subject_shapes come only from _iter_directs restrictions, and `self._rng.sample(queries, self.grid_cap)` has no write-local floor. Layer B covers leaf families only. All three gaps were read first-hand. The row's sabotage witnesses (object-* lie stays green on test_parity_engine.py; a lie on the last write escapes cap=600 on 8/20 seeds) were PROBED 2026-09-28 by others and not re-run by me.

*Reasoning:* ParityEngine is the default 4-way differential behind most integration and stateful hypothesis tests, so widening its grid and adding a deterministic write-local floor raises sensitivity across many tests at once. It turns probabilistic detection into deterministic detection. No divergence has been found yet, but the planted-lie probe gives the fix a concrete red-to-green criterion. Best candidate in this batch.

**`P23`** (score 4). *Bug class:* Shipped product accepts a schema it cannot serve. A valid write is refused (sync), or the async index stalls on a logged row, when a derived relation has an out-of-charset declared name. The oracle also accepts '.' names that production refuses.

*Evidence the agent read:* PROBED .scratch/promote-next/probeP23.py + probeP23cs.py. zanzibar_utils_v1.py::parse_schema_ast and tests/oracle.py::parse_schema_ast both accept the declared names '*', 'a#b', a non-ASCII name, a 257-character name and a tab; only '.' and empty are refused, and the oracle does not even refuse '.'. With `define <bad>: viewer` (plain or boolean), ParityEngine raises 'accept/reject disagreement {graph: False, set:py: True, set:roaring: True}' on a valid write to viewer. ConnectedStore (sqlite) accepts the schema at construction. In the boolean sync case a valid viewer write raises AdmissionRejected "invalid relation '*'". In the boolean async case the write is logged, then catch_up raises AdmissionRejected and the index stalls. In the plain sync case the production graph accepts and answers True, while tests/parity.py::_GraphSide.apply routes through the validating widx.add_tuple and refuses. So the harness graph is stricter than the shipped one (REASONED).

*Reasoning:* Best in this batch. It is the only row with a first-hand reproduced consequence in shipped ConnectedStore: an availability failure and a backend accept/reject split on a schema both parsers admit. The row does not record that consequence. The fix is a parse-time refusal in both parsers, pinned like TK55. That eliminates the class and naturally folds in TK109/TK105. No wrong ALLOW was observed.

**`TK115`** (score 4). *Bug class:* The JSON front end silently widens access (wildcard false becomes [T:*]) or declares relations the JSON never had. Duplicate keys are resolved last-wins.

*Evidence the agent read:* READ zanzibar_utils_v1.py::parse_openfga_json: json.loads is called with no object_pairs_hook, and declared names are only checked for '.'. READ ::_json_restrictions: `wildcard = 'wildcard' in e and e['wildcard'] is not None`. READ ::openfga_json_to_dsl: it never re-parses its own output. PROBED: {type: user, wildcard: False} renders 'define viewer: [user:*]' (a fail-open widening), and the relation name 'x: [user]\n    define secret' renders a DSL that declares the keys [owner, secret, x]. A grep finds no product caller outside tests/ and one conformance test.

*Reasoning:* A real fail-open in a public API, but not a graph-vs-set divergence, because both backends read the rendered DSL. connectedstore has no in-repo caller of it. The round-trip refusal closes the class cheaply.

**`TK110`** (score 4). *Bug class:* An over-eager admission refusal (or a non-refusal engine bug that raises ValueError) shrinks the compared store, and the gate stays green while testing less. TK71 measured this class in formal/conformance: the generated gate stayed green on 38 of 40 seeds under a broad over-reject.

*Evidence the agent read:* Re-measured 2026-10-03: 19 files with refusal catches (the row says 17). Read first-hand: tests/test_hypothesis.py:471,881,889,913,945,1003 use a bare `except ValueError` that rolls back, calls assume(False), or skips; tests/test_wildcard_property.py:146,528 do `continue` with only a majority floor (len(history) >= STEPS//2); tests/test_lookup_hypothesis.py:193 does `continue`; tests/test_matrix.py:544 does present.discard. tests/parity.py::ParityEngine._apply asserts that all backends accept or reject alike, but the oracle has no admission step, so an over-reject that both backends share is invisible.

*Reasoning:* The same bug class has already been observed in the sibling harness (TK71), and tests/ was never censused. Narrowing bare `except ValueError` to AdmissionRejected also removes a channel that swallows real engine bugs. Pinning absorber counts exactly is mechanical and can be sabotaged. Second-best candidate.

**`TK109`** (score 2). *Bug class:* The oracle cannot referee parser refusals. A corpus or test schema in one of these shapes silently tests a different schema in the oracle (and in conformance encode.py, which reads the oracle parser) than in production.

*Evidence the agent read:* PROBED .scratch/promote-next/probeA.py. All 7 shapes reproduce: prod=REFUSE (ValueError with a named message) and oracle=accept. The oracle merges duplicate types into one, turns 'type doc extra' into type 'doc extra', silently drops an unrecognised line, keeps the last duplicate define, and accepts [] / [user,] / a '.' declared name. tests/oracle.py::parse_schema_ast has no twin checks for these.

*Reasoning:* Directly serves the 'parsers refuse/accept the same schemas' leg by adding a both-parsers-refuse differential. There is no product exposure, because production refuses each shape. Its value is restoring oracle independence. It subsumes TK105, and is best done together with P23.

**`TK114`** (score 2). *Bug class:* Set engine and oracle agree on answers that are not models of the schema, because both use the same in-progress=>False convention. On this shape the oracle is not an independent referee.

*Evidence the agent read:* PROBED .scratch/promote-next/probeTK114.py. The schema `viewer: [user] but not viewer from parent` parses in both parsers. The graph compile raises CyclicDerivedDependency. A standalone SetEngine has _ruleset None and accepts the cycle-closing parent write. Self-parent case: set {a: True} = oracle {a: True}, which is not a model. 2-cycle case: set = oracle = {a: False, b: False}, which is not a fixpoint. This matches the row's witness exactly.

*Reasoning:* A real silent-acceptance path, and a spot where the oracle shares a convention with the evaluator. Exposure is limited: ConnectedStore refuses it (graph refusal PROBED; the save_schema path is the row's claim), and the row says no generator reaches it (UNVERIFIED). A parse-time refusal in both parsers removes it cleanly.

**`TK116`** (score 2). *Bug class:* Set-vs-oracle divergence under removes, on schemas the graph refuses, in standalone SetEngine (oracle-only mode with data-cycle rejection off).

*Evidence the agent read:* READ setengine/engine.py::SetEngine.__init__: it sets _ruleset=None on UnsupportedByGraphIndex or CyclicDerivedDependency. ::_would_cycle returns False in that case, and its stale 'Boolean schemas have no graph partner' comment is still present. The row overstates the gap, though: tests/test_hypothesis.py's stateful machine (setup near :1256) and the bool-star-bridge machine (near :2069) already fuzz graph-refused schemas 3-way (oracle + 2 set engines) with remove rules, gated by _assert_recorded_scope_rejection. I did not verify whether the row's four specific families are reached.

*Reasoning:* Adds deterministic differential coverage. However, part of it already exists via hypothesis, exposure is standalone SetEngine only (ConnectedStore refuses these schemas), and the row reports no divergence found.

**`TK101`** (score 2). *Bug class:* Partial-store write-order divergences on object-wildcard materialization (index_v4/wildcard.py '*' bridges), which no exhaustive small-scope argument covers.

*Evidence the agent read:* formal/conformance/test_conformance_enum.py::_tuple_space always takes the object name from _POOL and puts '*' only in the subject slot. ::_graph_query_filter also drops object-* targets. Mitigation also read first-hand: object-wildcard writes are driven differentially elsewhere, in tests/test_hypothesis.py (ParityEngine with object_wildcard_shapes), tests/test_wildcard_property.py OBJECT_WC, tests/genswarm.py, tests/test_owc_star_parent_cross.py and test_matrix union_wildcard.

*Reasoning:* The gap is real but narrow: object-* writes are already covered by randomized differentials. Only the exhaustive arm is missing. The cheaper, broader fix for object-* query coverage is TK117(a), so do TK117 first. The cost here multiplies against the conf-tile runtime cap.

**`TK105`** (score 1). *Bug class:* The oracle tests a different schema than production on a duplicate define (affects oracle independence and the conformance encoder).

*Evidence the agent read:* PROBED probeA.py. For a duplicate define, prod raises 'duplicate relation definition: doc#viewer'. tests/oracle.py::parse_schema_ast accepts and keeps the last definition: OUnion(ODirect(user), OComputed('editor')).

*Reasoning:* Strict subset of TK109 (one of its 7 shapes). Production refuses the input, so there is no product exposure. Fold it into TK109 rather than promoting it separately.

**`TK119`** (score 1). *Bug class:* Lean leaf-rule model drifts from Python's _emit_leaf_expr output, so the proof describes code that is not shipped.

*Evidence the agent read:* READ formal/CORRESPONDENCE.md near :370 (line dated 2026-10-03): 'Reported 2026-08-16 from a one-off probe that was never made a test ... 50/50 schemas'. The nearest test, formal/conformance/test_leaf_namespace_correspondence.py::test_no_corpus_rule_mints_a_leaf_named_ttu_target, only checks the leaf names of TTU targets. Its own docstring says it is vacuous on the leaf layer.

*Reasoning:* This is about model-to-code correspondence, not answers. The oracle already referees Python leaf-rule semantics end to end in the 4-way matrix and hypothesis runs.

**`TK3`** (score 1). *Bug class:* A write path that skips run_cascade leaves derived edges stale, giving a wrong ALLOW or DENY in production.

*Evidence the agent read:* The row is partly stale. index_v4/invariants.py now defines PARANOIA_FIXPOINT='fixpoint' (:116, docstring :48-63), which wires a per-cascade I9 check (index_v4/processor.py::DeltaProcessor._check_cascade_fixpoint :1735, gated :1602; added under TK74). The global ::audit_fixpoint (:1838) is still called only from tests/. I found no structural must-cascade check, but the product path has a single cascade choke point, connectedstore/apply.py::advance_index (:158-160).

*Reasoning:* This would be a production runtime detector. It would not find divergences the test harness misses, because ParityEngine and GraphBackend already cascade and run audit_fixpoint on every op. What remains is mostly an adjudication plus a tier-cost question.

**`TK44`** (score 1). *Bug class:* A bug that only shows up when two specific compiler features interact (an unreached feature pair) is never driven.

*Evidence the agent read:* tests/test_generator_coverage.py module docstring (:84-97, GC-1 2026-09-10): the conflicting percentages were deleted and ::test_report_cell_coverage is the single home for the figure. Feature-level HIT plus REJ-explained equals the 51-feature alphabet exactly, and the universe is 1275 cells (:253). The unexplained residue of pair cells is still unadjudicated.

*Reasoning:* The doc-drift half is closed. What remains is a decision (attack the residue or publish it). Every individual feature is already hit or has a refusal witness, and no witness of a pair-interaction bug exists. Attacking the cells would be L-sized with uncertain yield.

**`P16`** (score 1). *Bug class:* A divergence that appears only at store size 4 on the two capped shapes, or in state rows outside the 25% sample.

*Evidence the agent read:* formal/FINAL_REVIEW.md sec 4(e) (~:783-788) lists the remainder as: graph backend in the ANSWER enumeration, K=4 on the two capped shapes, and state coverage beyond the 25% sample. The first item is stale: formal/conformance/test_conformance_enum.py::test_exhaustive_small_scope already runs the real graph leg (run_graph / graphindex_answers). The live remainder is that two_stratum_cascade and wildcard_group_member stay capped at K=3, and test_conformance_enum_state.py samples stride-4.

*Reasoning:* The gain is marginal: one more size stratum on two shapes whose smaller strata already agree, and the phase runtime cap limits it. The row is an undifferentiated migrated cell with no first action. Side finding: FINAL_REVIEW:135 and sec 4(e) wrongly say the graph backend is absent from the answer enumeration.

**`TK102`** (score 1). *Bug class:* Partial-store divergence for a userset subject over a derived relation.

*Evidence the agent read:* test_conformance_enum.py::_SHAPES has six names and not derived_userset_subject (defined at corpus.py:765). test_conformance_fragment.py:122 shows it failing W4Fragment 'term', so it is outside GRAPH_FRAGMENT and the enum graph leg (run_graph) would be skipped. The row says nothing reaches this class today, but tests/test_hypothesis.py draws derived-userset leaves by default (:247-262, :924-929, test_pderived_userset_* pins) through the 4-way ParityEngine with the graph included.

*Reasoning:* Adding it buys only the spec, oracle and set-engine legs. The graph leg would be skipped, and the graph is where this class historically diverged. Randomized partial-store 4-way coverage already exists in hypothesis. It also costs runtime against the phase cap.

**`TK79`** (score 1). *Bug class:* unbalanced or missing outbox delta rows around reconcile-time GC, so an external consumer replaying the outbox ends up at the wrong membership

*Evidence the agent read:* index_v4/processor.py:1649-1651 carries the claim (row's :1611 is stale). drain_deltas callers are only tests/test_outbox.py, tests/test_index_v4.py:41-45 and tests/test_boolean_compile.py:470-476, and none of them replays deltas into a replica. connectedstore/ and setengine/ have no outbox reader. The only internal readers are processor.py:1613/:1668/:1693 (cascade frontier) and invariants.py:702.

*Reasoning:* This would be a real differential test, but it covers an export contract that nothing in the tree consumes. Check, lookup and expand answers are read from index tables, and the processor's own use of the outbox is already audited per op by I9/fixpoint in tests. It is the strongest of a weak batch but peripheral to graph==set==oracle.

**`TK121`** (score 1). *Bug class:* a fresh index rebuilt from a snapshot after a poison row disagrees with the set engine, or leaves a stale stall marker behind

*Evidence the agent read:* index_v4/core.py::MAX_PATH_COUNT (:87) with the refusal at :686-697. connectedstore/build.py:112/:119 refuses a store that already has a cursor. tests/test_tk111_stall_aware_freshness.py:74 pins that the stall happens and that reads fall back correctly. No test in that file or in tests/test_tk111_path_count_bound.py performs a recovery.

*Reasoning:* This is an availability and operations item. Reads are already correct while the index is stalled (pinned), and build_index equivalence is exercised elsewhere (test_both_build_index_constructors_apply_the_same_bound). It is only reachable with a K>=31 diamond. The recovery test would mostly re-exercise build_index.

**`TK118`** (score 1). *Bug class:* an I14 crossing-middle regression served as a fail-open ALLOW in production at paranoia=residue

*Evidence the agent read:* index_v4/invariants.py: the I14 check lives only in check_invariants (:324-371), which runs at 'full' and above (:781). The residue branch (:785) skips it. tests/test_p12_severity_sign.py::test_which_paranoia_level_catches_the_simulated_revert pins residue/off as fail-open under the simulated revert.

*Reasoning:* This is a production runtime-monitoring decision. Tests run at paranoia=full by default (tests/wildcard_helpers.py::make_wildcard_index paranoia=True), so an I14 regression in the shipped Python is already caught at test time. Doing this would not raise confidence in the code's correctness, only harden production detection.

**`P15`** (score 1). *Bug class:* Lean model infidelity in derived-TTU/userset arms or N-strata cascade that would also hide a matching Python divergence

*Evidence the agent read:* formal/FINAL_REVIEW.md:745 lists (ii) PDerivedTTU/PDerivedUserset 'still False under ComputedOrDirect' and >2 strata; zanzibar_utils_v1.py::PDerivedTTU (:1975) is still emitted at :2336. Python side is already reached: formal/conformance/test_conformance_nary_strata.py::test_every_plan_leaf_kind_is_reached_by_some_corpus and ::test_zero_coverage_shapes_three_way, tests/test_generator_coverage.py (found by grep, not read in full)

*Reasoning:* This widens the Lean proof over shapes the Python differential tests and generators already exercise. The only Python yield is indirect: attack-first #eval during widening has found model infidelities before (FINAL_REVIEW.md sec 3.1, 2026-07-20b). It is the best of a weak batch, but it is not a Python-confidence task.

**`P9`** (score 1). *Bug class:* Python graph remove divergence on Direct-arm-under-exclusion schemas

*Evidence the agent read:* formal/conformance/test_conformance_remove_graph.py::_REMOVE_EXCLUDED = frozenset({'direct_arm_exclusion'}) at :125. Per its comment (:97-124), the only remaining reason is the Lean removeGateB deciding plain storeValidRulesB. The same comment says the Python remove path over this corpus is already gated by test_conformance_remove.py (not re-run here)

*Reasoning:* This adds the Lean model as a third voter on one corpus. Python graph removes over boolean schemas are already compared with the oracle (test_conformance_remove.py, plus tests/ matrix and hypothesis add/remove restoration). Real work is needed on the Lean side: a storeValidRulesDB decider, its soundness proof and a widened remove constructor.

**`P6`** (score 1). *Bug class:* graph vs set-engine divergence on star-tupleset TTU through-shapes (an ASK-2 extension beyond OpenFGA)

*Evidence the agent read:* FullScope.lean::W4Fragment field ttuStarFree (:381) is unchanged; CORRESPONDENCE.md:359 says part (iv) widening is still owed. Python star-tupleset coverage already exists: tests/test_hypothesis.py star-tupleset family (sabotage at :733), tests/genswarm.py:540/768, tests/test_zt_p5_readjudication.py::test_zt_p5_star_subject_star_object_tupleset_write_parity

*Reasoning:* This widens the Lean proof over a region Python hypothesis fuzzing already reaches. It was parked by user decision on 2026-09-15d, and the tree goes red from step 8 until step 6' of the plan. That is a high cost for little gain in Python confidence.

**`P7`** (score 1). *Bug class:* same as P6 (star-tupleset through-shapes)

*Evidence the agent read:* Depends on P6 (deps [P6]). FullScope.lean:381 ttuStarFree is unchanged, so part (iv) has not been done. The Lean source was not otherwise read for this row

*Reasoning:* It is blocked on P6 and Lean-only. Its only Python-relevant output would be widening the conformance gate to star-tupleset corpora, which Python fuzzing already covers.

## 4. Adversarial verification of the top four (AGENT-REPORTED 2026-10-03c, one skeptic per row, told to refute)

### `TK117` -- WEAKENED (gap still exists: True; revised size M)

- **Already covered by:** Partly covered. (a) Object-* check: test_matrix.py union_wildcard plus the test_hypothesis star-bridge machines (_sb_grid). (b) From-chain star materialization: test_lookup_oracle.py::_subject_candidates in the fixed gates and the G4 generated-schema gate (lookup surfaces only). (c) Cap sampling: nothing deterministic, but a divergence that persists in state is resampled on every later op.
- **Concrete failure:** There is no natural escaping input. All three witnesses on the row are PLANTED lies: a check-only lie on object '*', a check-only lie on a from-chain star subject, and a lie confined to the last write's own query. Such a lie escapes only because it does not touch the shared edges that the lookup gate and the matrix read. The only class with a realistic escape route is (c): a wrong answer created by the LAST op of a test, confined to queries outside the sample. That happens on about 12% of ParityEngine grid builds, which drop about a third of the pool; elsewhere the sampled pool would catch it. A divergence that persists past later ops is very likely caught on the next sample. The best concrete witness is still the row's own: github.fga, last write ('...','user','hank','maintainer','repo','docs'), cap=600, escaping on 8/20 seeds. That lie was planted, not a real defect.
- **First step if promoted:** Do only part (c): in tests/parity.py::ParityEngine._grid, append an rng-free write-local floor after the cap (the last op's own (subject, rel, object) plus its object's declared relations against all subjects). Plant the row's witness-9 lie and confirm it goes GREEN -> RED with an M0 control. Measure the change in tile runtime before folding in (a) and (b).
- **Notes:** The gap is real and still open; no later work closed it. The case for promotion is overstated, though. Sub-gaps (a) and (b) are already covered elsewhere: the matrix and the star-bridge machines exercise object-* on the graph check, and the lookup gate exercises from-chain star subjects on the same materialized edges. The graph's check path for star endpoints is generic (wildcard.py::_check_internal), so lies that affect check alone are mostly an instrument artefact. Sub-gap (c) is the real one, but my probe measured it as modest: 12.4% of grid builds exceed the cap, and those keep about 67% of the pool. Suggested rescore: p_undetected_bug 1 (not 2), detection_power 2 (not 3). The size stays M because of the change in the sampled pool, which can surface latent findings, the extra runtime in the conf/tests tiles (each with a ~10-min cap), the grid_for/_grid mirrors in genswarm.py and test_hypothesis.py, and the spec-deviations reconcile. Notes file: C:/Users/user/PycharmProjects/graph-reachability-zanzibar-index/.scratch/promote-next/verify-TK117.md. I left the probe plugin and its output in .scratch/promote-next/tk117probe/ (capprobe.py, cap.out). The orchestrator owns cleanup and should transcribe the 12.4% and 67% figures, dated 2026-10-03, onto the TK117 row if it promotes it.
- **Evidence:**
  - tests/parity.py::ParityEngine._note_names / ::_grid: unchanged since 38aef9c (BL-2, 2026-08-21). Object '*' is dropped, subject_shapes come from Direct restrictions only, and Layer A is reduced with an unfloored self._rng.sample. All three gaps are live (first-hand READ, 2026-10-03).
  - tests/genswarm.py::grid_for and tests/test_hypothesis.py::_grid: same construction. Neither has object '*' or from-chain subjects (READ).
  - formal/conformance/grid.py::grid: queries stored (ot,'*') objects, but only on the set/oracle leg. test_conformance_enum.py::_graph_query_filter drops on=='*' for the graph. Userset subjects there are concrete-named only (READ).
  - Object-* on graph check is already covered outside ParityEngine. test_matrix union_wildcard went red under the row's own object-* sabotage. The test_hypothesis star-bridge machines build their grid with _sb_grid(pool), whose objects include (T,'*'), and assert pe.check unanimity. test_owc_star_parent_cross.py::_OBJECT_WILDCARD_GRANT pins one case (READ).
  - From-chain star subjects: test_lookup_oracle.py::_subject_candidates includes TTU from-chain shapes over '*', in the fixed gates and the G4 generated-schema gate. That covers lookup/expand only, not check(). test_matrix.py::_from_chain_userset_subjects explicitly skips wildcard parents (READ).
  - index_v4/wildcard.py::WildcardIndex._check_internal: a star subject or star object maps to a generic '*'/'any'/'all' node and goes through the same 4-probe edge query as every other star (non-derived relations); derived relations go to _check_derived. A from-chain-star check has no read path of its own, so a real bug there would be in materialization, and the lookup gate reads those same edges (REASONED).
  - PROBED 2026-10-03 with .scratch/promote-next/tk117probe/capprobe.py, a plugin wrapping ParityEngine._grid that computes the uncapped pool first and uses no rng. Ran over every ParityEngine-using module plus test_hypothesis (ci): 205 passed. 669 grid builds, 83 over cap (12.4%). Over-cap pools summed to 25055 against a cap sum of 16690, so about 67% was sampled. Over-cap calls by module: test_hypothesis 71, test_schema_shapes 10, test_parity_engine 2.
  - Who passes object_wildcard_shapes to ParityEngine: test_parity_engine (3 sites) and test_hypothesis (4 sites, all star-bridge, which already check object '*' through _sb_grid). The stateful ParityMachine (grid_cap=150) passes none, so fix (a) has almost no marginal reach (READ).

### `P23` -- WEAKENED (gap still exists: True; revised size S)

- **Already covered by:** Nothing pins this at the schema level. ParityEngine's per-op accept/reject check (tests/parity.py) would catch it, but only if a test fed it such a schema, and no generator or fixture does. The oracle's '.' half is already TK109.
- **Concrete failure:** Schema: `type user` / `type doc` / relations `define viewer: [user]`, `define blocked: [user]`, `define *: viewer but not blocked`. Both parsers accept it. With ConnectedStore(sync=True), the valid write add_tuple('...','user','alice','viewer','doc','d1') raises AdmissionRejected "invalid relation '*'". With sync=False the row is logged and the index stalls permanently, and untokened checks fall back to the set engine. Nothing in tests/ catches this today. It is a loud availability failure on a schema that is not legal OpenFGA. It is NOT a wrong ALLOW or DENY: every probed read returned the correct answer.
- **First step if promoted:** Add a parse-time refusal of declared names that fail zanzibar_utils_v1.py::_IDENTIFIER_RE, in a _validate_* function, in the DSL and JSON front-ends of zanzibar_utils_v1.py and independently in tests/oracle.py. Each refusal needs a REFUSED SHAPE / WHY / INSTEAD block, and the MIN_HEADERS floors in tests/test_refused_shape_comments.py need bumping. Pin it with a test modelled on tests/test_reg_empty_relation_name.py, covering '*', 'a#b', non-ASCII, a 257-char name and a tab. Then sabotage each parser's check and watch the pin go red.
- **Notes:** The gap is real and reproduced, but its confidence value is lower than the triage scored it. (1) No answer divergence is reachable. The boolean sync refusal is atomic and the backends agree. The boolean async stall is not served (since TK111) and falls back to a correct answer. The plain path works in production on both sync and async. So this is an admission-contract / availability hole, not an equivalence bug. TK55, the precedent, did have a wrong-answer split; this one does not. (2) The triggering names ('*', '#', tab, non-ASCII, 257 chars) are not legal OpenFGA identifiers, so real-world reach is low. (3) The oracle '.'-lock half duplicates TK109, which also covers more oracle-leniency shapes. (4) One triage sub-observation was a probe artifact: the plain-async 'TypeError' came from calling the index_stalled property. The triage's actual claims (boolean sync refusal, boolean async stall, ParityEngine split, harness stricter than product on the plain case) all reproduce. Promoting it is cheap and closes the class mechanically. It is a reasonable S-sized hygiene win, but I would not rank it as the best confidence-raiser. A task that can detect a silent wrong answer should outrank it. Findings are persisted at .scratch/promote-next/verify-P23.md and the probe at .scratch/promote-next/probeP23v.py, both gitignored and owned by the orchestrator for cleanup.
- **Evidence:**
  - zanzibar_utils_v1.py::parse_schema_ast (DSL define branch): refuses only an empty name (TK55) and a name containing '.'. The comment there says 'the full identifier charset is deliberately NOT imposed on declared names here'. The JSON front-end in the same file (around line 2700 as of 2026-10-03) refuses '.' only.
  - tests/oracle.py::parse_schema_ast: refuses an empty name only. There is no '.'-lock, but that half is already on TK109's brief ('oracle accepts ... '.' in name').
  - tests/test_reg_empty_relation_name.py covers only empty and whitespace-only names. No test in tests/ or formal/conformance pins an out-of-charset declared name. The generators name relations r{i} (tests/genswarm.py:420, tests/test_hypothesis.py:273), so no fuzz campaign reaches this region.
  - PROBED .scratch/promote-next/probeP23v.py (this agent), with `define *: viewer but not blocked` (and the same with a#b). Boolean sync: add raises AdmissionRejected, watermark 0, check is False on both relations, so the refusal is atomic and the backends agree. Boolean async: the add is logged, catch_up raises AdmissionRejected, index_stalled is True, and the untokened check falls back to the set engine and returns True, the correct answer (TK111 fallback).
  - PROBED: with plain `define *: viewer`, production ConnectedStore works on both sync and async. catch_up returns 1, the index is not stalled, and check is True on both viewer and '*'. The triage probe's 'catch_up RAISE TypeError' in the plain async case was a probe bug: connectedstore/store.py::ConnectedStore.index_stalled is a property.
  - PROBED .scratch/promote-next/probeP23.py: ParityEngine raises an accept/reject disagreement in both the plain and boolean cases. So tests/parity.py's graph side is stricter than the shipped graph on the plain case. Reproduced.
  - Repo scan of every `define <name>:` in *.py/*.fga/*.json/*.yaml: no real fixture uses an out-of-charset name, so a parse refusal breaks no corpus or golden.

### `TK115` -- WEAKENED (gap still exists: True; revised size M)

- **Already covered by:** none found. No test feeds malformed JSON names, duplicate keys or a non-object wildcard. The existing round-trip test (tests/test_openfga_json.py::test_json_to_dsl_round_trips) uses well-formed fixtures only.
- **Concrete failure:** parse_openfga_json({"schema_version":"1.1","type_definitions":[{"type":"user"},{"type":"doc","relations":{"viewer":{"this":{}}},"metadata":{"relations":{"viewer":{"directly_related_user_types":[{"type":"user","wildcard":false}]}}}}]}) yields Direct([user:*]), and openfga_json_to_dsl renders 'define viewer: [user:*]'. The model intended a plain [user] and silently gets a public grant. Nothing catches it today. The row's own round-trip refusal would not catch it either, because the AST round-trips equal. Only fix (4), a dict-only wildcard, catches it. It is NOT a graph/set/oracle divergence: all three evaluate the same rendered DSL and agree.
- **First step if promoted:** In _json_restrictions, refuse a `wildcard` value that is not a dict, and in parse_openfga_json, refuse duplicate keys with object_pairs_hook. Do both before the round-trip check, because the probe shows the round-trip check misses V2 and V3. Then pin V1 to V4 in tests/test_openfga_json.py and sabotage each pin.
- **Notes:** The gap is real and reproduces first-hand, but it ranks low on the question asked (confidence that graph ≡ set ≡ oracle): (a) Every witness is an input-fidelity bug upstream of all three evaluators, so it can never show up as a backend divergence. (b) No product code path consumes the JSON front end. Its only callers are tests. (c) Real-world reach is small. Real OpenFGA emits `"wildcard": {}` and never `false`, and names containing newlines are operator error, not a likely accident. (d) The row overstates its own fix. It says "(1) refuse unless round-trip equal ... closes the class", but V2 (wildcard false widening) and V3 (duplicate key, last wins) both round-trip EQUAL. So the size stays M: four separate refusals, each with a REFUSED SHAPE / WHY / INSTEAD block and MIN_HEADERS bumps. One cheap check is not enough. (e) V6 ('can view' is accepted by the DSL parser itself) and V8 (an empty name is accepted on the JSON path) overlap P23 and TK55. For the user's goal of making the parsers refuse and accept the same schemas, P23 (declared names the graph refuses but the set engine accepts) and TK109 (the oracle parser accepts 7 shapes the product parser refuses) are better-aimed candidates than TK115. Scratch: .scratch/promote-next/verify-TK115.md and tk115_probe.py.
- **Evidence:**
  - READ zanzibar_utils_v1.py::parse_openfga_json: still calls json.loads with no object_pairs_hook and checks declared names only for '.'. git log shows no later commit touched these sites for fidelity; TK106, TK108 and ASK-1 only added validators.
  - READ zanzibar_utils_v1.py::_json_restrictions: `wildcard = 'wildcard' in e and e['wildcard'] is not None` is unchanged.
  - PROBED .scratch/promote-next/tk115_probe.py (2026-10-03). V1: the relation name 'x: [user]\n    define secret' does not round-trip; the reparse declares keys owner, secret and x. V4: a newline in a type name reparses as (folder2, viewer). Both reproduce on the live tree.
  - PROBED: V2 `"wildcard": false` renders [user:*], and the AST round-trips EQUAL. V3: a duplicate JSON key resolves last-wins, and that AST also round-trips equal. So the row's fix (1) does NOT close the class, contrary to the row.
  - PROBED: V8 empty relation name is accepted by parse_openfga_json, which lacks the TK55 empty-name refusal. Only the DSL reparse raises. V6: 'can view' renders DSL that the DSL parser itself accepts and round-trips. That is the P23 charset issue and not specific to JSON.
  - GREP connectedstore/ index_v4/ setengine/ scripts/: there is no product caller of openfga_json_to_dsl or parse_openfga_json. The callers are tests/test_openfga_json.py, tests/test_schema_self_consistency.py and tests/test_tupleset_must_be_direct.py, plus a docstring in formal/conformance/test_leaf_namespace_correspondence.py.
  - READ tests/test_openfga_json.py: there are round-trip tests on well-formed fixtures only. Nothing feeds a newline, space, duplicate key or `wildcard: false`.
  - task.py show P23 / TK109: open LATER rows about the oracle parser and the product parser refusing or accepting different declared names and shapes. That is directly on the stated goal, while TK115 is not.

### `TK110` -- WEAKENED (gap still exists: True; revised size M)

- **Already covered by:** Admission refusals are already guarded at three levels. (1) Every backend must accept or reject alike, in tests/parity.py::ParityEngine._apply and tests/test_matrix.py::MultiBackend.apply, including the hypothesis stateful ParityEngine machine. (2) Explicit scripted tests require each write to be accepted, for example tests/test_lookup_oracle.py::_run_scripted, and many unit tests write tuples outside any try. (3) Majority anti-vacuity floors sit in test_wildcard_property and the test_matrix walks. All three sabotages I tried went RED.
- **Concrete failure:** I could not build one. The only remaining blind spot is narrow: a SHARED (Filter- or pattern-level) over-reject of a schema shape that only the random generators produce (hypothesis schema_asts, genswarm) and that no scripted test writes. Two of these did not fit it. Shared wildcard-userset and shared same-type-userset over-rejects were both caught, and TK71's set-only S1 went red in 4.6 s. The TK71 finding ("generated gate green on 38 of 40 seeds") came from formal/conformance drivers that had no second backend deciding admission. That premise does not hold for the parity drivers in tests/.
- **First step if promoted:** If it is promoted anyway, narrow the bare `except ValueError` to `except AdmissionRejected` in the absorbing drivers. The sites are test_hypothesis.py:881,889,913,945,1003, test_wildcard_property.py:146,528, test_lookup_hypothesis.py:193, test_reads.py:488, test_setengine_check.py:48, test_setengine_eval.py:61, test_setengine_storage.py:69, test_connectedstore.py:72, test_bulk_build.py:525 and test_zt_p5_readjudication.py:654. That stops them swallowing non-refusal engine bugs. Exact count pins should go only on the seeded non-hypothesis walks, because the @given draws are not stable enough to pin.
- **Notes:** My verdict is weakened, close to refuted, and I would not promote TK110 as a confidence-raiser. It is worth keeping as hygiene at LATER.  The row's premise copies TK71, but TK71's absorbers were single-backend Lean-comparison drivers. In tests/, the parity drivers check that every backend accepts or rejects alike, and many explicit tests require each write to be accepted. Three sabotages all went RED quickly: - the S1 sabotage that was GREEN in formal/conformance; - a shared wildcard-userset over-reject; - a shared same-type-userset over-reject.  Size stays M. The site count is about 15 real absorbers in 12 files. The exact-pin method does not carry over to the hypothesis @given sites, so part of the work is design, not mechanical. The triage also misclassified test_hypothesis.py:471, which is a no-over-reject pin.  Files left behind (gitignored, for the orchestrator to clean up): - C:/Users/user/PycharmProjects/graph-reachability-zanzibar-index/.scratch/promote-next/verify-TK110.md (my report) - C:/Users/user/PycharmProjects/graph-reachability-zanzibar-index/.scratch/promote-next/tk110probe/ (the sab_tk110.py plugin, ctl.py, and the wc_a, wc_full, st_full and s1_full logs)  No tracked file was modified, and no background process is still running.
- **Evidence:**
  - tests/parity.py::ParityEngine._apply and tests/test_matrix.py::MultiBackend.apply (READ): both assert that every backend accepts or rejects alike, across graph, set(Py), set(Roaring) and, in the matrix, ConnectedStore. In formal/conformance the TK71 absorbers had a single backend deciding admission. tests/ is different, so a single-backend over-reject turns into a parity failure here whenever a parity pool generates that shape.
  - PROBE s1 (MEASURED 2026-10-03, no tracked edit, monkeypatch plugin .scratch/promote-next/tk110probe/sab_tk110.py): TK71's own headline sabotage S1 (SetEngine._would_cycle returns True when s_type==o_type) was GREEN in formal/conformance. Over tests/ with -x it gives `1 failed, 25 passed in 4.58s`, FAILED tests/test_blind_audit_regressions.py::test_setengine_memo_not_poisoned_by_revisit_guard[py].
  - PROBE wcuserset (MEASURED 2026-10-03): this is the class the triage named as invisible, a SHARED over-reject. zanzibar_utils_v1.Filter.apply (used by SetEngine._validate step 2 and by RuleSet.apply) is patched to refuse wildcard-userset subjects. A control showed ParityEngine.add_tuple('member','group','*','viewer','doc','d1') silently returning False. Over tests/ -x: `1 failed, 629 passed in 442.48s`, caught by tests/test_lookup_oracle.py::test_lookup_oracle_dense_wildcards (`_run_scripted` asserts every scripted step is accepted).
  - PROBE selftype (MEASURED 2026-10-03): a shared Filter over-reject of userset subjects where the subject type equals the object type. Over tests/ -x: `1 error in 0.93s` (AdmissionRejected at module import).
  - tests/test_hypothesis.py:471 (READ): this site is a no-over-reject PIN, not an absorber (`assert not refused` over the whole candidate pool). The triage counted it as an absorber.
  - tests/test_hypothesis.py:881/889/913/945/1003 (READ): these are graph-only metamorphic @given properties. The hypothesis draws differ from run to run, so TK71's exact-count pin (the `_assert_poisoned` shape) cannot be copied onto them. All the row could do there is narrow `except ValueError` to AdmissionRejected.
  - tests/test_wildcard_property.py:146,528 and the test_matrix 4-way walks (READ): they already carry majority anti-vacuity floors (len(history) >= STEPS//2, and >=7/14), which catch a broad over-reject.
  - tests/test_reads.py:488 (READ): the one truly lopsided absorber. The graph decides admission, and a write the graph refuses is never offered to the set engine, so this driver alone cannot see a graph-only over-reject. A ParityEngine or matrix pool that covers the same shape would still catch it.

