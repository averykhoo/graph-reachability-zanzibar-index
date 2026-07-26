# CORRESPONDENCE.md — the Lean-model ↔ Python-implementation map

Phase 6 item 2 (plan C2/C3; HANDOFF "The next task"). This is the auditable
backbone of the claim "the Python implementations are pinned to the Lean models
by the conformance harness": every load-bearing Lean definition, the Python
mechanism it models, and the harness gate that observes the two agreeing.

**What this table is NOT** (plan §7 honesty): a proof about the Python code.
The theorems are about the Lean models; the pin to Python is *empirical*
(`verify.sh` step 5). **Nothing here says, or may be read as saying, that the
Python is verified.** Where a spec and the code disagree on a name, the code wins.

---

## 0. How to read a row (anchor convention — rebuilt 2026-07-26, ZT-P4-1)

**Rows are keyed on SYMBOLS, not line numbers.** The previous revision of this
file stamped its Python citations "as of 2026-07-12" as `file.py:319-342`. By
2026-07-26 the zero-trust review measured **4 of ~45 Python citations accurate and
~35 pointing at unrelated code**, with §5 (the cascade) 100% wrong — an auditor
following it landed in `_write_derived`, `_gc_subject_node` and
`_keys_referencing`. The drift rate is ~3,000 lines per two weeks; during the
few hours of *this rebuild alone* `index_v4/invariants.py` went from 414 to 652
lines under a concurrently-running fix. **No manually-maintained line number
survives that.** So:

* A Python anchor is <code>path/file.py&#58;&#58;Qualified.Symbol</code>, using Python's
  `__qualname__` nesting (`Oracle.check.direct_leaf` is the closure `direct_leaf`
  defined inside the method `Oracle.check`). This resolves by `ast` parse, is
  stable under insertion/deletion anywhere else in the file, and *fails loudly*
  when the symbol is renamed — which is the fact an auditor actually needs.
* A Lean anchor is <code>Path/File.lean&#58;&#58;Decl</code> with the declaration's full name
  (`GraphIndex/ReconcileStars.lean::GraphState.reconcileResidueKey`).
* **No line numbers appear in the tables.** Where a row needs positional detail
  it names an inner step by its in-code comment marker (e.g. `_reconcile` step
  (2c)), which travels with the code.
* Renames are recorded explicitly rather than silently repaired — a rename tells
  an auditor more than a corrected offset. See the rename ledger at the end of §5.
* §9 is a **design proposal, not yet wired**, for a script that mechanically
  asserts every anchor in this file resolves. Until it lands, this file is
  human-maintained and can rot again; treat its freshness date as its warranty.

**Anchors below were re-derived against the working tree on 2026-07-26** — after
the same day's `ZT-P0-1` (N3-elision withdrawal), `ZT-P1-1`/`ZT-P1-2`/`ZT-P1-7`
guard hardening, and `verify.sh` gate-floor changes — and then **verified
mechanically** with a throwaway prototype of the §9 checker: **239 Python
anchors + 102 Lean anchors, 0 unresolved.** That is a claim about
*navigability only* (every named symbol exists, in the named file); it says
nothing about whether a row's correspondence claim is true. §2's `check` row is
the standing proof that a resolvable anchor can still head a wrong claim.

### Conformance gates (`formal/verify.sh` step 5, `formal/conformance/`)

**Measured 2026-07-26:** `corpus.SCHEMAS` = **20** corpora, `corpus.GRAPH_FRAGMENT`
= **19** of them (`object_wildcard` is the one excluded); `formal/conformance/`
holds **13 test files** collecting **356 tests** (the earlier "6 files / 17 corpora
/ 15 in-fragment / 330 tests" figures in this file were all stale). The three
files marked ✚ below were entirely undeclared here, and one of them
(`test_conformance_remove.py`) *is* the whole legacy `conf-heavy` phase.

| gate | compares | corpora | n |
|---|---|---|--:|
| `test_conformance_spec.py` | Lean `sem` (zcli) vs `tests/oracle.py` vs real `SetEngine` | all 20 | 75 |
| `test_conformance_random.py` | same, randomized stores | random | 20 |
| ✚ `test_conformance_generated.py` | same, over GENERATED schema shapes outside the curated corpora (seeded re-implementation of the hypothesis generator) | generated | 40 |
| `test_conformance_graph.py` | Lean **operational graph model** (zcli mode `"graph"`) vs real `WildcardIndex`+`DeltaProcessor`, and vs `sem` | the 19 `GRAPH_FRAGMENT` | 38 |
| `test_conformance_state.py` | Lean graph model **FINAL STATE** (zcli mode `"graph-state"`) vs the Python index's final SQL rows (`EdgeV4`/`ResidueV1` via `NodeV4`), projections per `extractor.py` | the 19 `GRAPH_FRAGMENT` | 19 |
| ✚ `test_conformance_remove.py` | **the entire legacy `conf-heavy` phase.** Interleaved add/remove streams DRIVEN through the real `SetEngine` (not a rebuild) vs `sem` on the final store vs oracle | remove streams | 80 |
| `test_conformance_remove_graph.py` | zcli `"ops"` streams (`graphRunOps`) vs the real graph index vs oracle, ANSWER level | `GRAPH_FRAGMENT` minus `direct_arm_exclusion` | 17 |
| ✚ `test_conformance_direct_arm.py` | Python-only (no zcli) both-`SetOps` 3-backend differential + exhaustive small-store attack on the Direct-arm-under-exclusion corpus | `direct_arm_exclusion` | 4 |
| `test_conformance_enum.py` | **exhaustive small-scope enumeration**: spec vs oracle vs set engine vs real graph index on ALL stores ≤ K tuples | **6** fragment shapes, **1021** stores, per-shape **K = 3 or 4** (counts + tuple-space sizes asserted) | 6 |
| ✚ `test_conformance_enum_state.py` | STATE-level analog of the enumeration, on a deterministic sample, same P1–P6 projections | same 6 shapes | 6 |
| `test_cli_mode.py` | zcli mode dispatch fails closed | minimal | 5 |
| `test_runner_retry.py` (gate tooling) | `runner.invoke_zcli`'s pre-`main` retry never masks a real fault | — | 7 |
| `test_sorry_scan.py` (gate tooling) | `sorry_scan.py` catches `sorry`/`admit`/`sorryAx`/`native_decide`/`axiom` (post-`ZT-P2-3`) | — | 39 |

**zcli exit codes (measured from `Cli.lean`'s header + dispatch):** `0` answers or
state printed · `1` usage / JSON parse / decode error · `2` a graph op failed its
gate (write admission or remove guard) · `3` graph state not drained · `4`
unrecognized mode · **`5` an `"ops"` stream passed in spec mode**. The previous
revision listed only 0–4 in this section while §6 described rc 5 — the file
contradicted itself; both places now say 0–5.

All answer-comparing suites share ONE query grid
(`formal/conformance/grid.py::grid`): targets are the stored-tuple cross product
PLUS every schema-DECLARED `(type, relation)` paired type-aware with that type's
stored objects (so derived/boolean roots are queried on every corpus), and
subjects include userset-shaped `(relation, type, name)` over a bounded pool
(first 2 concrete names + a ghost per type). Star subjects stay bare-predicate;
the concrete-named userset queries sit inside the proved graph query scope
(`hqs` constrains only star-NAMED subjects).

---

## 1. The specification `sem` (Phase 0/2 — `Spec/`, `Core/`)

The spec is transcribed from the repository's INDEPENDENT oracle (which shares
no code with either backend).

**Independence caveat (ZT-P4-6, recorded here, fix owned elsewhere):** the
"three genuinely independent corners" phrasing this section used to carry is
**2-of-3 at the schema-reading layer**. `formal/conformance/encode.py` and
`formal/conformance/grid.py` both import `parse_schema_ast` from
`tests/oracle.py`, so the Lean corner is fed by the oracle's parser *and* the
query grid's targets come from that same parse — a misparse propagates to two
corners and simultaneously deletes the query that would expose it. (Demonstrated
divergence: on a duplicate `define`, `oracle.py` silently keeps the last while
`zanzibar_utils_v1.py` raises.) `encode.py`'s own docstring is honest about
this. What remains genuinely independent is the *evaluation* code on each side.

| Lean (`lean/ZanzibarProofs/`) | models | Python |
|---|---|---|
| `Core/Refs.lean::SubjectRef`/`::ObjectRef`/`::Tuple` | tuple/query layout | `tests/oracle.py::OracleTuple`; `zanzibar_utils_v1.py::RelationalTriple` |
| `Core/Schema.lean::Expr`/`::Schema` (binary `union`/`inter`) | the parsed DSL AST (n-ary ops left-folded) | `tests/oracle.py::ODirect`/`::OComputed`/`::OTTU`/`::OUnion`/`::OIntersection`/`::OExclusion`; the fold is `formal/conformance/encode.py::_fold_binary` |
| `Core/Store.lean::universeNames` | the query universe | `tests/oracle.py::Oracle._universe`, plus the per-query closures `::Oracle.check.universe` and `::Oracle.check.instances` |
| `Spec/Semantics.lean::restrictionMatches`/`::grantsOf` | direct-grant matching | `tests/oracle.py::Oracle.check._matching_objects` and `::Oracle.check.direct_leaf.restriction_matches` |
| `Spec/Semantics.lean::memberOfGranted` | transitive userset membership (∀⇒∃) | `tests/oracle.py::Oracle.check._member_of_granted` |
| `Spec/Semantics.lean::directLeaf` | `Direct` leaf evaluation (star + userset branches) | `tests/oracle.py::Oracle.check.direct_leaf` |
| `Spec/Semantics.lean::ttuLeaf` | stored-parent TTU rule | `tests/oracle.py::Oracle.check.ttu_leaf` |
| `Spec/Semantics.lean::evalE`/`::sem` (fuel `fuelBound`, multiplicative) | the oracle's recursive evaluation | `tests/oracle.py::Oracle.check.sat` / `::Oracle.check.sat_expr` |
| `Spec/WellDef.lean::sem_fuel_stable` (T0a), `Spec/Stratify.lean::stratify_*` (T0b) | fuel-independence; stratification = no derived cycle | `zanzibar_utils_v1.py::compile_boolean_schema` → `::_stratify`, raising `::CyclicDerivedDependency` (a `ValueError` subclass) |
| `Spec/Confine.lean::StoreDeclared` | the **type-restriction clause** of write admission, carried as a PREMISE (not an algorithm twin) | `setengine/engine.py::SetEngine._validate` step (2) |

*Note:* every `oracle.py` citation in the previous revision was uniformly ~7
lines low (the file gained a header block); all seven are re-anchored above by
symbol, and `matching_objects` is really the nested `_matching_objects`.

## 2. The set-engine model (Phase 3, T1 — `SetEngine/`)

| Lean | models | Python |
|---|---|---|
| `SetEngine/MemberSet.lean::MemberSet` (`pos`/`stars`/`neg`) | the star-closed member-set algebra | `setengine/memberset.py::MemberSet`, with `::union` / `::intersect` / `::subtract` (and `::_normalize`, `::_starpop`, `::_ext`) |
| `SetEngine/Eval.lean::SetEngineModel.expandDirect` | direct expansion | `setengine/engine.py::SetEngine.expand.direct_expand` — a closure **nested inside `expand`** |
| `SetEngine/Eval.lean::SetEngineModel.expandTtu` | tupleset walk | `setengine/engine.py::SetEngine.expand.ttu_expand` — likewise nested inside `expand` |
| `SetEngine/Eval.lean::SetEngineModel.expandStep`/`::expandAux` | the fuel-bounded expander | `setengine/engine.py::SetEngine.expand.do` / `::SetEngine.expand.do_expr` |
| **`SetEngine/Eval.lean::SetEngineModel.check`** | **NOT an algorithm twin — see the row note below** | answer-for-answer against `setengine/engine.py::SetEngine.check`; the shape-level twin is `::SetEngine.expand` |
| `SetEngine/Correct.lean::setEngine_correct` (T1) | — the theorem: model `check` = `sem` | pinned empirically by `test_conformance_spec.py` (`sem` vs real `SetEngine`), `test_conformance_random.py`, `test_conformance_generated.py`, `test_conformance_enum.py`, `test_conformance_remove.py` |

**The `check` row, stated honestly (rewritten 2026-07-26, ZT-P4-2a).** The
previous revision's row read "`SetEngineModel.check` | `SetEngine.check`", which
asserted an algorithm-twin relationship that **does not hold**:

* Lean's `SetEngineModel.check` builds the query node's **entire `MemberSet` by
  pure fuel recursion** (`expandAux` to `fuelBound S T`) and then probes it once
  with `containsShape`. `Eval.lean`'s own header says so — *"Like `sem` (and
  unlike the real engine's Tarjan-lowlink memo), the model is **pure fuel
  recursion** — agreement with the memoized engine is asserted by conformance,
  not by matching control flow"*. **The Lean file declared this; this table did
  not.**
* Python's `SetEngine.check` is a **short-circuiting boolean DFS** with a
  Tarjan-lowlink memo (`setengine/engine.py::SetEngine.check.sat`,
  `::SetEngine.check.sat_expr`, `::SetEngine.check.direct_leaf`,
  `::SetEngine.check.member_via_usersets`, `::SetEngine.check.ttu_leaf`). It
  never materializes a `MemberSet` at all.
* The Python function that *is* the shape twin of the Lean definition is
  **`SetEngine.expand`** — same set-at-a-time algebra, same `union`/`intersect`/
  `subtract` folds, same direct/TTU leaves. **No conformance gate drives
  `expand`.** (`SetEngine.lookup_reverse` renders `expand`, and
  `tests/test_lookup_oracle.py` pins it against the brute-force oracle — but that
  is a Python↔Python differential inside `tests/`, not part of `verify.sh`'s
  Lean-facing conformance.)

So what T1 + the gates actually earn is: **answer-for-answer equality across an
algorithm boundary, netted empirically.** The theorem says the *model's* answers
equal `sem`; the harness observes that the *shipped, differently-structured*
evaluator returns the same booleans on the corpora. That is a real and useful
pin — it is what would catch a memoization bug — but it is not "the Lean
definition describes the code that runs", and it is weaker than the
correspondence the graph side has for `reconcile`/`cascade`. Two consequences
worth an auditor's attention: (a) a bug reachable only through the *expansion*
path and invisible at `check` answers is out of the net; (b) the fuel bound is
modeled, the memo is not, so a memo-induced early exit is caught only if it
changes an answer on a corpus query.

**Also unmapped on this side (see §7 for the full list):** set-engine write
admission (`setengine/engine.py::SetEngine._validate` steps (1) and (3),
`::SetEngine._would_cycle`, `::SetEngine._ensure_flow_graph`,
`::SetEngine._flow_reaches`) and the `::Interner` id-recycling
layer.

## 3. The graph-index state and reads (T2 — `GraphIndex/State.lean`)

| Lean | models | Python |
|---|---|---|
| `GraphIndex/State.lean::GraphState` (nodes/edges/residue/outbox/watermark) | materialized closure + residue + delta stream | `index_v4/models.py::NodeV4` (identity/keying), `::EdgeV4`, `::ResidueV1` (symbolic `(stars, neg)` — plus a `version` column with **no Lean counterpart**, §7), `::DeltaOutboxV1`; helpers in `index_v4/outbox.py` |
| `GraphIndex/State.lean::GraphState.reach` / `::reachB` (fuel = node count) | the O(1) closure probe | `index_v4/core.py::ReachabilityIndex.check_reachable_by_id` / `::ReachabilityIndex.check_reachable` (`indirect_edge_count > 0`) |
| `GraphIndex/Closure.lean::DirectGraph`, `::pathCount`, **`::pathCount_addEdge` / `::pathCount_removeEdge` (T4)** | ref-counted path-count closure maintenance — **the hottest correctness surface, and it had NO row until 2026-07-26** | `index_v4/core.py::ReachabilityIndex._add_direct_edge_unsafe` → `::ReachabilityIndex._add_direct_edge_unsafe_impl`, `::ReachabilityIndex._add_db_edges_unsafe`, `::ReachabilityIndex._add_indirect_edges_batch_unsafe`, `::ReachabilityIndex._remove_edge_locked`. **Honest caveat:** T4 is proved on `DirectGraph` — a bare `structure DirectGraph where dcount : V → V → Nat`. `DirectGraph` occurs in **exactly one file** (`Closure.lean`) and that file mentions `GraphState` **zero times**; there is **no theorem connecting `pathCount` to `GraphState.edges`**. So the ref-counted closure arithmetic is **inspection-pinned to the closed form, not chain-integrated**: the chain's own theorems never invoke T4 |
| `GraphIndex/State.lean::GraphModel.probeNonDerived` (≤4 probes) | untainted read | `index_v4/wildcard.py::WildcardIndex.check` — the probe assembly (`::WildcardIndex.check.key`, probes 1–4 into one row-value `IN`) |
| `GraphIndex/State.lean::GraphModel.probeDerived` (edge probe → `stars`∖`neg`, `upos`; edge hit skips `neg` — I6) | derived read path | `index_v4/wildcard.py::WildcardIndex._check_derived`, reading `::WildcardIndex._residue_state` |
| `GraphIndex/State.lean::GraphModel.check` (route by `isDerived`) | `WildcardIndex.check` | `index_v4/wildcard.py::WildcardIndex.check` (routes `(o_type, relation) ∈ schema_info.derived_families` to `::WildcardIndex._check_derived`) |
| `GraphIndex/State.lean::GraphAccepts` | decision-15 compile-scope rejection | `zanzibar_utils_v1.py::_reject_object_wildcard_scope` (object wildcards on derived + wildcard usersets over derived) and `::_reject_doubly_bridged_shapes` (a literal `T:*#p` userset restriction that is also an object-wildcard shape), raising `::UnsupportedByGraphIndex` / `::DoublyBridgedShapeError` (F1/F2, spec-deviations 2026-07-17). Each only NARROWS the admissible schema space — no modeled algorithm change (`GraphState.admitEdge` untouched) |
| `GraphIndex/State.lean::Quiescent` | outbox drained at the commit boundary (I10) | `index_v4/processor.py::DeltaProcessor.audit_fixpoint`; `index_v4/invariants.py::_check_outbox_sanity` |
| **`GraphIndex/State.lean::Inv`** | **8 named clauses — relabeled below; the old "I1–I3 structural + I6 ×4" label overclaimed** | `index_v4/invariants.py::check_invariants` + `::_check_derived_invariants` + `::_check_residue_rows` |

**The `Inv` row, stated honestly (rewritten 2026-07-26, ZT-P4-2b).** The previous
revision labeled `Inv` *"8 clauses: I1–I3 structural + I6 residue hygiene ×4"*.
Its eight fields are `schemaEq`, `nodeEnc`, `edgesClosed`, `acyclic`,
`negStarCovered`, `negEdgeFree`, `uposEdgeFree`, `uposNegDisjoint`. Mapping them
onto the Python I-series:

| Lean clause | Python invariant | coverage |
|---|---|---|
| `schemaEq` | — | modeling bookkeeping (the state was built for `S`) |
| `nodeEnc` | node encoding (`name == '*' ⟺ variant ≠ plain`) | full |
| `edgesClosed` | I1, **endpoint existence only** | partial — I1's *count algebra* (`indirect ≥ direct`, `indirect > 0`, no negative direct) is NOT modeled |
| `acyclic` | I2 | **full — the only fully-modeled invariant** |
| `negStarCovered` / `negEdgeFree` / `uposEdgeFree` / `uposNegDisjoint` | 4 of I6's sub-clauses | partial (see below) |
| — | **I3 (bridge hygiene/completeness)** | **not a clause at all.** Lean's own `Inv` docstring concedes: *"The path-count algebra (I1's `p ≥ d`), refcounts (I13), and the full bridge completeness (I3) … are not restated here"* |

**Python additionally enforces, with nothing modeling it:** I3 (bridge
justification, completeness AND exclusivity, both directions), I4 (namespace
classification of `'.'`-predicate leaf families), I5 (derived-flag exclusivity),
I7 (residue-version monotonicity), I10 (outbox sanity), I13 (`reference_count`
== direct-edge degree), and **eight further I6 sub-clauses** the model does not
carry: residue→missing-node, residue on a non-derived relation, `residue.relation`
vs its node, empty-row-persisted, stars outside declared subject shapes, dead
node id in `neg`, wildcard node in `neg`, userset `neg` subject implicit — plus
the `upos` mirrors (dead id, non-userset node, star-covered, implicit).
**The `upos` dead-node-id clause is precisely the one that catches `ZT-P0-1`.**

So the correct label is: **`Inv` = node encoding + I1-endpoints + I2 + four of
I6's twelve-odd sub-clauses.** Roughly one-and-a-bit of the eleven invariants
Python runs. The omissions are now listed in §7 rather than left implicit.

## 4. The write path (`GraphIndex/Write.lean`, `ObjStarWrite.lean`, `UsStarWrite.lean`, `RulesWrite.lean`, `Cascade.lean`)

| Lean | models | Python |
|---|---|---|
| `GraphIndex/Write.lean::GraphState.admitEdge` (`a ≠ b` ∧ no back-path) | cycle rejection | `index_v4/core.py::ReachabilityIndex._add_edge_locked` (self-edge `ValueError`, then the reverse-reachability `ValueError`), reached under `::ReachabilityIndex._lock_store` + `::ReachabilityIndex._require_live_nodes` via `::ReachabilityIndex.add_edge_by_id` / `::ReachabilityIndex.add_edge` |
| `GraphIndex/Write.lean::GraphState.writeDirect` | one guarded closure-edge insert | `index_v4/wildcard.py::WildcardIndex.add_tuple` → `::WildcardIndex._add_tuple_trusted` → `index_v4/core.py::ReachabilityIndex.add_edge` / `::ReachabilityIndex.add_edge_by_id` |
| **`GraphIndex/ObjStarWrite.lean::GraphState.bridgedConcrete` / `::GraphState.ensureBridges` / `::GraphState.writeWild`** | **object-wildcard (out-)bridge materialization — an EXISTING Lean model that this file never listed** | `index_v4/wildcard.py::WildcardIndex._ensure_bridges` (out-bridge half), `::WildcardIndex._bridge_degree`, `::WildcardIndex._concrete_nodes_of_shape`; shapes from `zanzibar_utils_v1.py::SchemaInfo.bridged_out_shapes` |
| **`GraphIndex/UsStarWrite.lean::GraphState.bridgedInConcrete` / `::GraphState.ensureInBridges` / `::GraphState.writeUsStar`, `::Schema.isSubjectWildcardUserset`** | **wildcard-userset (in-)bridge materialization — likewise previously unlisted** | `index_v4/wildcard.py::WildcardIndex._ensure_bridges` (in-bridge half), teardown via `::WildcardIndex._strip_bridges` / `::WildcardIndex._maybe_remove_bridges`; shapes from `zanzibar_utils_v1.py::SchemaInfo.bridged_in_shapes` and `::SchemaInfo.subject_wildcard_shapes` |
| `GraphIndex/RulesWrite.lean::RRule` / `::exprArms` / `::schemaRewrites` (**taint-filtered** — derived keys emit no arms) | compiled Computed/TTU rewrite rules, fanned out ONLY for untainted keys | `zanzibar_utils_v1.py::_rewrite_rule`, `::_emit_expr`; the taint routing is the `if (object_type, relation_name) not in tainted: _emit_expr(...)` loop in `::compile_ruleset`, mirrored by `S.defs.filter (!isDerived …)` in `schemaRewrites` (added 2026-07-17 — see §7) |
| `GraphIndex/RulesWrite.lean::rewriteClosure` | the write fan-out worklist | `zanzibar_utils_v1.py::RuleSet.apply` (dispatch built by `::RuleSet._build_dispatch`, candidates by `::RuleSet._candidates`) |
| `GraphIndex/Cascade.lean::GraphState.writeLoggedOne` / `::GraphState.removeLoggedOne` / `::GraphState.writeLoggedRules` | routed write + delta row per accepted flip | `zanzibar_utils_v1.py::RuleSet.apply` + per-triple `index_v4/wildcard.py::WildcardIndex.add_tuple` / `::WildcardIndex.remove_tuple`; delta rows emitted by `index_v4/core.py::ReachabilityIndex._emit` (buffered) and `::ReachabilityIndex._flush_outbox` |
| `GraphIndex/Cascade.lean::GraphState.nextDeltaId` / `::GraphState.pushDelta` / `::GraphState.maxOutboxId` | outbox append / autoincrement cursor | `index_v4/models.py::DeltaOutboxV1` + `index_v4/outbox.py::outbox_watermark` / `::outbox_rows` / `::drain_deltas` |

*Renames/moves found in this section:* `_add_edge_locked` was cited at
`core.py:319-342`; that range is now inside
`index_v4/core.py::ReachabilityIndex._add_indirect_edges_batch_unsafe`
(a different function entirely — the P2 batching landed between). `_emit` was
cited at `core.py:31`; that is inside `::ReachabilityIndex.__init__`.

## 5. The delta processor / cascade (T2 reconcile half + T5 — `ReconcileStars.lean`, `ReconcileDiff.lean`, `Cascade.lean`, `CascadeStrata.lean`)

**This whole section was 100% wrong in the previous revision** (`ZT-P4-1`) and is
rebuilt from the current source. `index_v4/processor.py` has grown ~469 lines
since the citations were stamped and was rewritten again on 2026-07-26.

| Lean | models | Python |
|---|---|---|
| `GraphIndex/ReconcileStars.lean::wildcardShapes` | declared wildcard shapes → candidate stars | `index_v4/processor.py::DeltaProcessor.__init__` (`self.subject_shapes = sorted(widx.schema_info.subject_wildcard_shapes)`), consumed by `::_EvalContext.leaf_stars` |
| `GraphIndex/ReconcileStars.lean::GraphState.coveredFn` | star-subject coverage read | `index_v4/processor.py::_EvalContext.leaf_stars` (probes each declared shape with `'*'` as the subject NAME) and `::DeltaProcessor.member_stars` / `::DeltaProcessor.residue_stars` |
| `GraphIndex/ReconcileStars.lean::GraphState.reconcileResidueKey` (wholesale `stars`/`neg`/`upos` recompute) | the full-object recompute | `index_v4/processor.py::DeltaProcessor._reconcile` steps (1) stars fold via `plan.stars_fn`, (2)/(2a) neg candidates incl. from-chain (`::DeltaProcessor._leaf_concretes`, `::DeltaProcessor._derived_leaf_neg_ids`, `::DeltaProcessor._from_chain_keys`), (2c) `upos` wholesale |
| `GraphIndex/ReconcileStars.lean::GraphState.reconcileKeyC` / `::GraphState.reconcileStarsKey` (residue-THEN-edges) | the ORDER: residue written before the edge audit | `index_v4/processor.py::DeltaProcessor._reconcile` — step (3) `::DeltaProcessor._store_residue` upsert precedes the step-(4) edge audit |
| **`GraphIndex/ReconcileDiff.lean::GraphState.reconcileStarsKeyD`** (and `::GraphState.reconcileKeyD`) — the DIFFING pass (stale-edge retraction) | want/have edge diff | `index_v4/processor.py::DeltaProcessor._reconcile` step (4) fans each bare-entity audit member into `::DeltaProcessor._reconcile_subject`, whose bare-entity tail computes `want_edge = should and not covered`, compares against `index_v4/core.py::ReachabilityIndex.direct_edge_exists_by_id`, and adds/removes via `index_v4/processor.py::DeltaProcessor._write_derived`. **The definition lives in `ReconcileDiff.lean`, which this file never named** |
| `GraphIndex/CascadeStrata.lean::GraphModel.graphRecR` / `::GraphState.checkFnR` / `::GraphState.coveredFnR` — the ROUTED operand read | untainted → closure probe; derived → residue read | `index_v4/processor.py::_EvalContext` (`::_EvalContext.leaf_check` → `WildcardIndex.check`; `::_EvalContext.derived_check`/`::_EvalContext.derived_stars` → `::DeltaProcessor.derived_check` → `WildcardIndex._check_derived`; `::userset_*`, `::ttu_*`, `::tupleset_ttu_*` for the other leaf kinds), plus `::DeltaProcessor.member_check` |
| `GraphIndex/Cascade.lean::affectedKeys` (**two branches**) | delta → dirty derived keys | `index_v4/processor.py::DeltaProcessor._map_deltas_to_keys` — the `isinstance(fam, LeafFamily)` own-key branch (with its `raise InvariantViolation` on a wildcard-object delta) — and `::DeltaProcessor._fan_out`'s `edge.via == 'computed'` arm. **Models 2 of ~6 Python channels — see §7** |
| `GraphIndex/State.lean::Delta.leaf` | the outbox row's LeafFamily-vs-DerivedFamily provenance | in Python the family type `self.compiled.namespace.get((o_type, o_pred))` decides the branch inside `index_v4/processor.py::DeltaProcessor._map_deltas_to_keys` — there is no stored provenance column; the Lean tag is a modeling device for a collapsed state space |
| `GraphIndex/Cascade.lean::GraphState.frontierRows`, `GraphIndex/CascadeStrata.lean::GraphState.frontierRowsAbove` / `::GraphState.frontierMax` | per-round outbox read + cursor | `index_v4/processor.py::DeltaProcessor._run_cascade` (`rows = outbox_rows(...)`, then `frontier_start = max((r.id for r in rows), default=frontier_start)`), reading `index_v4/outbox.py::outbox_rows` |
| `GraphIndex/CascadeStrata.lean::runCascade2` (two rounds + quiescence check; reject branch) | the in-transaction cascade | `index_v4/processor.py::DeltaProcessor.run_cascade` (a thin `idx._node_cache_scope()` wrapper) → `::DeltaProcessor._run_cascade` (`rounds = len(self.compiled.strata)`; leftover ⇒ `raise InvariantViolation`) |
| **T5** `GraphIndex/CascadeStrata.lean::runCascade2_no_abort` / `::cascade2_drains` | — the abort is dead code at ≤2 strata | `index_v4/processor.py::DeltaProcessor._run_cascade`'s leftover raise. **The Lean abort condition is STRICTLY WEAKER than Python's — see the `_bumped` entry in §7** |
| `GraphIndex/CascadeStrataAssemble.lean::enumJobs2R1` / `::enumJobs2R2` | per-round key enumeration off the state | `index_v4/processor.py::DeltaProcessor._run_cascade`'s per-round `::DeltaProcessor._map_deltas_to_keys` + the `stratum_of` sort |

### Rename ledger for §5 (what an auditor should grep for)

| previously cited | now |
|---|---|
| `processor.py` `reconcile` | `DeltaProcessor._reconcile` — the public `DeltaProcessor.reconcile` survives as a two-line `with self._residue_cache_scope():` wrapper |
| `processor.py` `reconcile_subject` | `DeltaProcessor._reconcile_subject` — likewise, `index_v4/processor.py::DeltaProcessor.reconcile_subject` is now the cache-scope wrapper |
| `processor.py` `run_cascade` | `DeltaProcessor._run_cascade` — `index_v4/processor.py::DeltaProcessor.run_cascade` is now the `_node_cache_scope()` wrapper (perf N15) |
| `processor.py:135` `__init__` `subject_shapes` | `DeltaProcessor.__init__` (the whole ctor moved) |
| `processor.py:58-62` `leaf_stars` | `_EvalContext.leaf_stars` |
| `processor.py:989-1027` `_map_deltas_to_keys` | `DeltaProcessor._map_deltas_to_keys` (still that name; the range now spans other code) |
| `processor.py:316` `_keys_referencing` / `:684` `_gc_subject_node` | `index_v4/processor.py::DeltaProcessor._keys_referencing` / `::DeltaProcessor._gc_subject_node` — **and neither has ever had a Lean counterpart** (§8.1, 2026-07-26) |

**The same stale line numbers were copied into the Lean docstrings**
(`ReconcileStars.lean`, `ReconcileDiff.lean`, `GraphIndex/Cascade.lean::affectedKeys` cites
`processor.py:989-1027`/`:991-1011`/`:993`/`:604-605`, `FullScope.lean`,
`UsStarWrite.lean`), so cross-checking the two artifacts could not detect the
drift — they drifted together. Those docstrings are **not** corrected here (this
rebuild deliberately touches no `.lean` file); treat a Python line number
appearing in a Lean docstring as unmaintained, and use this file's symbol
anchors instead. Fixing them is a separate, Lean-owning task.

## 6. The operational closure and the driver (W4 + Phase 6 — `FullScope.lean`, `CascadeStrataAssemble.lean`, `Exec.lean`, `Equiv.lean`)

| Lean | models | Python |
|---|---|---|
| `GraphIndex/CascadeStrataAssemble.lean::ReachedByW3d2E` = **`ReachedBy`** | the write path as *admitted write + same-transaction cascade* | `connectedstore/apply.py::advance_index` → `index_v4/processor.py::DeltaProcessor.run_cascade`; `tests/test_matrix.py` `GraphBackend.apply`. **"interleaved" is true of ONE of Python's two schedules — see the row note below** |
| `FullScope.lean::Drained` (`cascadeKeys S σ = []`) | outbox fully drained at commit boundary | boolean spec §7.8 / I9 `index_v4/processor.py::DeltaProcessor.audit_fixpoint` |
| `FullScope.lean::GraphAdmission` (`wf`/`nodup`/`strat`/`ttuDirect`/`matchDecl`/`ranked`/`objWild`/`storeValid`) | what compile+write admission guarantees | see field docs; e.g. `ttuDirect` ↔ `zanzibar_utils_v1.py::_validate_ttu_tuplesets`, `matchDecl` ↔ `zanzibar_utils_v1.py::RuleSet.apply`'s raise on a raw write matching no declared restriction, `objWild` ↔ `::_reject_object_wildcard_scope` |
| `FullScope.lean::W4Fragment` (`computedOnly`/`twoStrata`/`wsBare`/`bareStar`/`ttuStarFree`/`term` — **six** fields; `rootB` was deleted 2026-07-17) | — the HONEST carries: restrictions Python does NOT impose | `history/ROADMAP.md` "W4 — honest gaps" |
| `GraphIndex/Exec.lean::graphRun` + `::graphRun_reached` / `::graphRun_check_eq_sem` | the conformance driver IS the chain (theorem, not analogy) | driven against `WildcardIndex` by `test_conformance_graph.py` (verdicts) and `test_conformance_state.py` (final state, zcli mode `"graph-state"`; the dump code in `Cli.lean` is driver-level, its projections documented in the mode header + `formal/conformance/extractor.py`) |
| `GraphIndex/Exec.lean::GraphOp` + `::graphRunOps` + `::removeGateB` + `::graphRunOps_reached` / `::graphRunOps_store` / `::graphRunOps_check_eq_sem` | the op-stream driver over the chain, add/remove **interleaved per op** | zcli graph/graph-state modes take an optional `"ops"` stream (absent ⇒ the legacy add-only `graphRun`, byte-identical; spec mode rejects `"ops"` with **rc 5**, `test_cli_mode.py`); driven against the real graph index by `test_conformance_remove_graph.py` (ANSWER level, differential vs oracle on the erased store) |
| `Equiv.lean::backend_equivalence_direct` … `::backend_equivalence_w3d2` (+ `exclusion_effective_*`, `no_ghost_grant_*`), and the unsuffixed `FullScope.lean::backend_equivalence` | **the entire "the two backends agree" claim — T3/T6. This file listed NEITHER until 2026-07-26** | pinned empirically by the 4-way validation matrix (`tests/test_matrix.py`) and the ParityEngine (`tests/parity.py`); on the Lean-facing side by every gate that compares `sem` against both backends. `Equiv.lean` is a per-stage LADDER kept deliberately (each rung is separately axiom-audited, so removing one changes the gate's report count); the CURRENT claim is the `FullScope.lean` pair |

**The `ReachedByW3d2E` row, stated honestly (rewritten 2026-07-26, `ZT-P4-2c`).**
The previous revision described this as "the synchronous v1 write path: admitted
write + same-txn cascade, **interleaved**". Python has **two schedules**, and the
proof covers only the first:

* **Interleaved (sync, `ConnectedStore(sync=True)` — the default).**
  `connectedstore/store.py` inlines the apply step into every write, so
  `connectedstore/apply.py::advance_index` receives a one-row `rows_hint`: one
  op, then one cascade. **This is the modeled schedule.**
* **Batched (async, `ConnectedStore(sync=False)` → `connectedstore/store.py::ConnectedStore.catch_up`,
  and `build_index`).** `advance_index` runs `for row in rows: _apply_row(...)`
  over the **whole batch** and only THEN calls `proc.run_cascade(wm)` — one
  cascade for N log rows. A `remove` at batch position 2 therefore executes
  against a state that is **provably NOT drained** (rows 0–1's outbox deltas are
  still above the watermark, unreconciled).

`GraphIndex/Exec.lean::removeGateB` gates the remove constructor on, among other things,
`cascadeKeys S σ = []` — i.e. **a drained prior state** — which is exactly what
the batched schedule does not provide. So: **the proved execution schedule is
not the one production runs under the async/bulk paths**, and
`GraphIndex/Exec.lean::graphRunOps` drives only the interleaved schedule.

**Do not overstate this.** It is a **model-scope gap, not a known bug.** Python's
cascade is written to consume a whole batch's frontier in one run
(`_run_cascade` reads `outbox_rows(session, store, frontier_start)` from the
pre-batch watermark and loops `len(strata)` rounds over everything above it), and
the batched path is netted empirically by `tests/test_connectedstore*.py` and the
hypothesis add/remove-restoration campaign. What is missing is a *proof* for that
schedule: nothing in the Lean tree quantifies over "apply N ops, then one
cascade". Widening `ReachedByW3d2E` (or adding a batched constructor) is the
honest fix; until then this row's "interleaved" is a scope statement, not a
description of every deployment.

**Related §7 correction:** §7's "Scoped removes" bullet claimed the remove scope
is *"exactly Python's behavior (`TupleSource.remove` rejects a not-present
tuple)"*. That justifies the `t ∈ T` conjunct only. `removeGateB`'s **other**
conjunct, `cascadeKeys = []` (drained-ness), has **no** counterpart in
`TupleSource.remove` — tuple PRESENCE and DRAINED-NESS are different properties.
The bullet is corrected in place below.

## 7. Known intentional divergences (model ≠ code, by design)

### 7.1 Cascade-model gaps (three added 2026-07-26 — they were previously undeclared)

* **★ NEW — the `_bumped` residue-version channel is a SECOND dirty-key source
  with no model (`ZT-P4-3a`).** `index_v4/processor.py::DeltaProcessor` carries
  `self._bumped`, appended by **`::DeltaProcessor._store_residue`** on every
  residue upsert/delete, fanned out per round in `::DeltaProcessor._run_cascade`
  (`bumped, self._bumped = self._bumped, []`, then `_fan_out(..., lambda k:
  keys.__setitem__(k, None))` — note this uses **`_fan_out`'s full via-set**,
  not just `'computed'`), and **folded into the post-loop quiescence check**
  before the `leftover` raise. It emits **no outbox rows at all**. On the Lean
  side, `GraphIndex/Cascade.lean::cascadeKeys` derives every key from `σ.frontierRows`
  (outbox rows above the watermark) and `GraphIndex/State.lean::Residue` has **no `version`
  field** — grep for `bumped` or `.version` across `lean/ZanzibarProofs/` returns
  **zero hits**.
  **The consequence, stated plainly: T5 (`runCascade2_no_abort` /
  `cascade2_drains`, "the abort is dead code at ≤2 strata") is a claim about a
  WEAKER abort condition than the one Python ships.** `runCascade2`'s reject
  branch fires iff `(frontierRowsAbove …).all (affectedKeys … = [])`; Python's
  fires iff *that* is empty **AND** the pending `_bumped` fan-out is empty. A
  version bump that dirties a key with no corresponding outbox row is invisible
  to the theorem and would abort the real transaction. T5 therefore does not
  entail "Python's abort is dead code".
* **★ CORRECTED — `affectedKeys` models 2 of ~6 delta→key channels
  (`ZT-P4-3b`).** The 2026-07-20c bullet below said `affectedKeys` *"now carries
  **BOTH** Python branches"*, which an auditor would take at face value. It
  carries both branches **of the two channels it models**. Reading
  `index_v4/processor.py::DeltaProcessor._map_deltas_to_keys` +
  `::DeltaProcessor._fan_out` today, the
  full channel list is:
  1. LeafFamily **own-key** (modeled), 2. `_fan_out` **`via='computed'`**
  (modeled), 3. the **subject-GC residue scan** (`{r.subject_node_id for r in
  rows}` → `::DeltaProcessor._keys_referencing` → `full(...)`), 4. **tupleset-ttu dependents**
  of a LeafFamily object (`compiled.dependents` with `edge.via ==
  'tupleset-ttu'`), 5. **`compiled.tupleset_feeders`**, 6.
  **`compiled.target_feeders`** (both `'ttu'` and `'tupleset-ttu'` arms, the
  latter walking `::DeltaProcessor._stored_parent_objects_of_entity`), plus `_fan_out`'s own
  `'ttu'` / `'userset'` / `'tupleset-ttu'` arms.
  All four unmodeled channels are **out of `W4Fragment`** (`computedOnly` leaves
  admit no TTU/userset/tupleset dependency edges), so this is **scope-honest in
  substance** — no in-fragment run reaches them. The correction is to the
  *wording*, not the disposition.
* **★ NEW — the subject-level cheap path is unmodeled, and has twice gained real
  logic.** `index_v4/processor.py::DeltaProcessor._reconcile_subject` is Python's per-subject
  invalidation path (chosen whenever `_map_deltas_to_keys` yields a subject set
  rather than `None`). Lean models only the full-object reconcile
  (`reconcileStarsKey` / `reconcileStarsKeyD`); there is no per-subject
  constructor anywhere in the chain. This was recorded only in
  `formal/history/` until 2026-07-26. It is no longer a thin fast path:
  * **2026-07-17 (Fix B)** added **promote-on-record** to its userset branch (a
    recorded userset subject must be made explicit or core's implicit-GC drops it
    at rc-0 and dangles the residue reference) — a state-functional rule mirroring
    `_reconcile` step (2d).
  * **2026-07-26 (`ZT-P0-1`/`ZT-P0-2`)** added an **escalation to the full
    reconcile**: when the userset branch finds `s_node is None` it now returns
    `self._reconcile(object_type, rel, obj_name)` instead of silently no-oping.
    (The same day corrected the branch's "UNREACHABLE" comment, which was false —
    closure leaves DO store userset subjects.)
  A per-subject path that can escalate to a full reconcile and can mutate node
  flags is a real algorithm, and none of it is in the model.

### 7.2 Residue/state gaps

* **★ NEW — `ResidueV1.version` is gated by nothing formal.**
  `index_v4/models.py::ResidueV1` carries a `version` column, incremented in
  `index_v4/processor.py::DeltaProcessor._store_residue` and checked by I7 (monotonicity per residue
  row) in `index_v4/invariants.py::_check_residue_rows`.
  `formal/conformance/extractor.py::lean_graph_state` and `::python_graph_state`
  compare only `(stars, neg, upos)` — **`version` is dropped, and that drop is
  NOT one of the documented P1–P6 projections.** So the state-level conformance
  gate is silent about it, `Inv` has no clause for it, and Lean's `Residue`
  structure has no such field. I7 is pinned only by `tests/` paranoia runs, and
  `install_paranoia` is not wired into `ConnectedStore` (`ZT-P1-3`). Either
  document it as P7 or model it; today it is an undeclared projection.
* **State-gate thinness (`ZT-P4-5`, recorded for completeness).** Of 422 raw edge
  rows across the 19 in-fragment corpora, 231 are dropped by P1, 55 by P6, 136
  actually compared; **all `NodeV4` rows are dropped by P5** (nodes are not
  compared at all); only 5 of 19 corpora produce ANY residue row (11 rows total),
  so 14 corpora compare two empty dicts. The 2026-07-17 note below already
  conceded node-flag behavior is "invisible to the gate by construction"; this is
  the quantified version.

### 7.3 Load-bearing Python surfaces with NO Lean model (added 2026-07-26)

These were neither mapped nor declared. None is a bug; each is a place where an
auditor must know the pin is a Python↔Python differential, not a Lean twin.

* **Set-engine WRITE ADMISSION — and it decides which stores the gates can
  enumerate.** `setengine/engine.py::SetEngine._validate` step (1)
  (object-wildcard gating) and step (3) (cycle rejection) →
  `::SetEngine._would_cycle` → `::SetEngine._flow_reaches` over the bridge-aware
  flow graph built by `::SetEngine._ensure_flow_graph` / `::SetEngine._flow_add_edge` /
  `::SetEngine._flow_remove_edge` / `::SetEngine._flow_pair` / `::SetEngine._shape_node_ref`. Only step (2)
  has any Lean counterpart, and even that is a **premise**
  (`Spec/Confine.lean::StoreDeclared`), not an algorithm twin. **This is
  load-bearing for the gates themselves:** `test_conformance_enum.py` enumerates
  all stores ≤ K tuples and this code decides which are admission-valid (its
  docstring records 132 of `two_stratum_cascade`'s 299 stores being rejected). A
  bug here silently shrinks the enumerated space — and nothing formal watches it.
* **`index_v4/processor.py::DeltaProcessor.backfill` and `::DeltaProcessor.audit_fixpoint`.**
  `backfill()` is the bootstrap/repair path (and the `bulk=False` reference side
  of the bulk gate); `audit_fixpoint` is the I9 "a second reconcile changes
  nothing" check. The Lean chain models only incremental write+cascade;
  `Quiescent` states the drained condition but nothing models the audit sweep.
  `::DeltaProcessor._live_keys_of` (the key enumeration both use) is likewise
  unmodeled.
* **Graph-side `lookup` / `lookup_reverse` and the `_collect_*` family.**
  `index_v4/wildcard.py::WildcardIndex.lookup`, `::WildcardIndex.lookup_reverse`,
  `::WildcardIndex._collect_residue_memberships`, `::WildcardIndex._collect_reachable`, `::WildcardIndex._collect_reverse`,
  `::WildcardIndex._classify_ids`; `index_v4/core.py::ReachabilityIndex.lookup_reachable` /
  `::ReachabilityIndex.lookup_reverse`. **`lookup_reachable` is NOT read-only cosmetic:** the
  cascade calls it to compute invalidations —
  `index_v4/processor.py::DeltaProcessor._fan_out` uses it for the `'ttu'` and
  `'userset'` arms and `::DeltaProcessor._map_deltas_to_keys` for the
  `target_feeders` `'ttu'` arm. And `index_v4/core.py::ReachabilityIndex.lookup_reverse`
  is how `index_v4/processor.py::DeltaProcessor._incoming_concretes`
  resolves closure-leaf candidates — the very fact that made the withdrawn N3
  elision unsound (§8.1). A `lookup_reachable` bug is a *write-path* bug.
  Pinned only by `tests/test_lookup_oracle.py` + the matrix.
* **Node GC + flag lifecycle AS AN ALGORITHM.** The 2026-07-17 note below
  declares the `implicit`-flag *rule*; the *collection algorithm* is separate and
  unmodeled: `index_v4/processor.py::DeltaProcessor._gc_subject_node`,
  `::DeltaProcessor._gc_public_node`,
  `::DeltaProcessor._demote_released_node`, `::DeltaProcessor._any_residue_reference`,
  `::DeltaProcessor._keys_referencing`, `::DeltaProcessor._residue_references`,
  `::DeltaProcessor._has_incoming_direct_edge`, plus
  `index_v4/core.py::ReachabilityIndex.remove_node` / `::ReachabilityIndex._evict_node`. Lean
  states the opposite explicitly — `ReconcileDiff.lean` and `Cascade.lean` both
  say *"node GC is a modeled-away optimization"*. `ZT-P0-1` was a bug **inside
  this unmodeled region**.
* **The `Interner` / int32 id-recycling layer.** `setengine/engine.py::Interner`
  (`::Interner.acquire`, `::Interner.release`, `::Interner.get`, `::Interner.key`) with `::NodeSets`. Ids are
  recycled int32; the stable surrogate is the `(type, name, predicate)` key. The
  Lean set-engine model uses `Id := SubjectRef` — subjects **are** their own ids,
  so recycling cannot be expressed. Netted by a 4,000-op randomized
  incremental-vs-rebuild differential and by `::SetEngine.rebuild` parity.
* **The compiled `check_fn` / `stars_fn` closures — which ARE the boolean
  semantics reconcile executes.** `zanzibar_utils_v1.py::_compile_check_fn`,
  `::_compile_stars_fn`, `::_build_plan_tree`, `::_plan_leaves`,
  `::_emit_leaf_expr`, `::_plan_deps_and_fanout`, `::_stratify`, producing
  `::Plan` / `::CompiledBooleans`. Lean's reconcile evaluates an `Expr` directly
  via `checkFnR`/`coveredFnR`; Python evaluates a **compiled closure tree over
  split leaf families**. The correspondence is "same boolean semantics", pinned
  by the differential matrix and the snapshot gate
  (`tests/snapshots/`, byte-identity for untainted compilation) — not by any
  theorem about the compiler.

### 7.4 Pre-existing entries (carried forward)

* **~~`affectedKeys` omits the LeafFamily own-key branch~~ — RESOLVED 2026-07-20c.**
  `affectedKeys` (`Cascade.lean`) carries BOTH branches **of the two channels it
  models** (wording corrected 2026-07-26, §7.1): the **LeafFamily own-key
  branch** (a `leaf=true` raw write/remove on a derived key dirties its OWN key)
  and the **DerivedFamily fan-out** (`_fan_out via='computed'` — a `leaf=false`
  reconcile emission fans out to computed-operand readers only, never
  re-dirtying its own key: the fence that lets the cascade quiesce). The
  discriminator is the `Delta.leaf` tag, because the collapsed model lands both a
  raw Direct-arm seed write and a reconcile emission at the same `objNode ⟨o⟩ R`.
  **★ House-rule-2 finding (2026-07-20c):** the earlier session's proposed naive
  branch (`isDerived ⇒ dirty own key`, keyed on ANY delta) was ATTACK-KILLED as
  unfaithful — it would re-dirty reconcile emissions' own keys (which Python's
  `_fan_out` never does), breaking quiescence (`runCascade_no_abort`/
  `cascade2_drains` empirically fail). The faithful fix is the provenance tag.
  The ComputedOnly scope is unaffected. This unblocked the Direct-arm widening
  (`reachedByW3d2C_settled_d`/`graph_correct_w3d2_d`).
* **Scoped removes (decision 6 — resolved/scoped 2026-07-19; scope statement
  corrected 2026-07-26).** The chain carries a `remove` constructor on
  `ReachedByW3d2`/`C`/`E` (2026-07-19f), gated by `GraphIndex/Exec.lean::removeGateB` on
  removing a validly-stored tuple (`t ∈ T`) **from a drained prior state
  (`cascadeKeys = []`)** with the pre-remove store's `StoreValidRules` /
  `BareStarStore` / `TtuStarFree` / `htermT` disciplines carried. T2a/T2b
  (`graph_reached_inv`/`graph_correct`) cover retraction at that scope, and the
  driver DRIVES removes end-to-end via `graphRunOps` / zcli `"ops"` (2026-07-19,
  `5a35ec3`); its honesty theorems make every printed verdict equal `sem` over
  the op stream, differential-gated at answer level by
  `test_conformance_remove_graph.py`.
  **Correction (2026-07-26, `ZT-P4-2c`):** this bullet used to claim the scope is
  *"exactly Python's behavior (`TupleSource.remove` rejects a not-present
  tuple)"*. That argument covers the `t ∈ T` conjunct **only**. The
  drained-prior-state conjunct is a genuinely stronger requirement that
  `TupleSource.remove` does not impose, and the **batched** apply schedule
  (`connectedstore/apply.py::advance_index` under `ConnectedStore.catch_up` /
  `build_index`) routinely violates it. Presence ≠ drained-ness. See the §6 row
  note.
* **Fixed two rounds.** `runCascade2` always runs 2 rounds; Python runs
  `len(self.compiled.strata)`. Same drained fixpoint at ≤2 strata (T5, modulo the
  `_bumped` caveat in §7.1); ≥3 strata are outside the fragment (`hLU2`
  attack-confirmed load-bearing). Note `ZT-P4-4`: **no corpus in this harness
  exceeds 2 strata**, so Python's ≥3-stratum path is exercised by nothing here.
* **Fragment surplus.** Python accepts more than `W4Fragment` (non-`ComputedOnly`
  derived leaves — `Direct`/TTU arms under a boolean, object-wildcard tuples,
  wildcard usersets over untainted relations, arbitrary strata). Union- and
  computed-ROOTED derived defs are NO LONGER surplus — they entered the fragment
  2026-07-17 (next bullet). The Phase 6 attack probe (2026-07-12k) found NO
  behavioral divergence on the object-wildcard corpus — that exclusion is
  proof-scope, not observed disagreement (`corpus.py` note). **Caveat kept
  visible (`ZT-P5`):** that same inference — "fragment exclusions are proof-scope,
  not behavioral" — was drawn from CHECK-level evidence in 2026-07-12k and then
  **failed at STATE level on 2026-07-17** (next bullet). The object-wildcard
  corpus has never been probed at state level.
* **Root-boolean fragment widening + the taint-filter faithfulness fix
  (2026-07-17).** `W4Fragment.rootB`/`RootBoolean` (which restricted derived defs
  to an `inter`/`excl` ROOT) was DELETED — the shape condition is `ComputedOnly`
  alone, so union- and computed-rooted derived defs (`approver := viewer or
  admin`, `approver := viewer`) are inside the proved scope. **No Python change.**
  Landed with a **model-faithfulness fix**: `schemaRewrites` was unfiltered, so at
  a union-rooted derived R-node the union arm materialized a transient fanout
  edge; with a USERSET-subject stored tuple matching that arm the stale fanout
  edge SURVIVED to the drained Lean state — a real Lean-model-vs-Python state
  divergence (found by probe). The taint filter (`S.defs.filter (!isDerived …)`,
  `GraphIndex/RulesWrite.lean::schemaRewrites`) is the faithful mirror of the tainted-key
  skip in `zanzibar_utils_v1.py::compile_ruleset` (§4 row), and the
  `taint_union_userset_arm` state corpus pins the stale edge's absence.
* **No leaf-family split.** The model reads raw boolean defs (`ComputedOnly`
  leaves); Python's compiler splits derived storage onto `<relation>.<index>`
  leaf families. **State-gate correction (2026-07-12):** an earlier note claimed
  "on ComputedOnly defs there are no storage leaves, so the shapes coincide" —
  that holds only for `storage=True` leaves. Even on ComputedOnly defs the
  compiler creates `storage=False` CLOSURE leaves and `RuleSet.apply` routes
  copies of the untainted operand writes onto them (an `editor` write also lands
  on `viewer.0`), so the SQL edge state carries `<rel>.<i>` rows the model never
  has. The read shapes still coincide, and the state gate projects the class out
  explicitly (`extractor.py` P6, keyed on the reserved `'.'`). Schemas needing
  genuine storage leaves (`Direct`/TTU arms under a boolean) remain outside
  `computedOnly`.
* **Out-of-fragment `upos`-lift and node-flag lifecycle (2026-07-17).** Two
  processor changes added paths the Lean reconcile model (`ReconcileStars.lean`,
  §5) does not describe, both **outside `W4Fragment`**.
  (a) The reconcile audit-set builder
  `index_v4/processor.py::DeltaProcessor._leaf_concretes` lifts a
  referenced tainted relation's residue `upos` (edge-free userset-shaped
  memberships, P4/D2) for the `derived-computed` and `derived-userset` leaf kinds,
  extending the X4b TTU lift (2026-07-13) via
  `index_v4/processor.py::DeltaProcessor._ttu_target_upos_nodes`. The lift only *widens* the candidate
  set (membership still decided by `plan.check_fn`) and reads strictly-lower-stratum
  residues — no new cascade rounds. In-fragment runs never produce the activating
  state.
  (b) The **node-flag lifecycle** gained a state-functional `implicit`-flag rule —
  promote-on-record (`_reconcile` step 2d, and since Fix B also in
  `_reconcile_subject`) + a demote-on-release exception to core's "explicit is
  sticky" (`index_v4/processor.py::DeltaProcessor._demote_released_node` on the
  survive paths of `::DeltaProcessor._gc_subject_node` /
  `::DeltaProcessor._gc_public_node`). Node `implicit` flags are
  **projected out** of the state gate by the extractor (P5), so this convergence
  is invisible to the gate by construction — the differential matrix + hypothesis
  add/remove-restoration net it instead. Both mirrored into
  `index_v4/bulk_backfill.py`. Details: `docs/spec-deviations.md` 2026-07-17.
  (Same-session reg13: `RuleSet.apply` now raises on a raw write matching no
  declared restriction instead of silently dropping it — this only *tightens*
  admission toward the `matchDecl` guarantee `GraphAdmission` already assumes; no
  §3 row change.)
* **Multi-instance scheduling is OUT-OF-MODEL (2026-07-23).** HA support added
  instance-local set engines synced by tailing the log — locks
  (`connectedstore/source.py::TupleSource._lock_source`), per-`Session` state, and
  catch-up cadence (`::TupleSource.catch_up_evaluator` /
  `setengine/engine.py::SetEngine.apply_logged`). **No Lean change needed**, for
  three reasons. (a) The set-engine Lean layer (§2) models the evaluator as a
  **pure function of a store**, and a lagging replica's state is the fold of an
  admission-validated log **PREFIX**; every such prefix is itself a valid store,
  so T1 applies pointwise per prefix — "correct as of log id W". (b)
  `apply_logged` replays the exact `::SetEngine._apply_add`/`::SetEngine._apply_remove` sequence
  `::rebuild()` performs, so **no modeled algorithm changed**. (c) The source-lock
  write discipline is precisely what **PRESERVES the formal layer's standing
  premise** that a store's log is a single serial admitted-op sequence.
  **Caveat kept visible (`ZT-P5`):** the 2026-07-23 fix closes an explicitly
  **PostgreSQL-only** hazard; CI runs SQLite, so every mechanism it relies on is
  reasoned about, not CI-tested, and Phase 7 (TLA+ for concurrency) is not
  started.

## 8. Keeping the model in sync when optimizing the Python (READ THIS before perf work)

The theorems are about the **Lean models**, which are *algorithm-twins* of the
Python (this whole table). A proof only means something if the Lean definition
still describes the algorithm the Python actually runs. So, when optimizing:

* A **behavior-preserving micro-optimization** (same algorithm, faster) needs no
  Lean change — the differential matrix / hypothesis / conformance gates are the
  net that it didn't change observable answers.
* An optimization that **changes the modeled algorithm** (a new candidate-pruning
  rule, a different cascade order, a restructured closure/residue update, a new
  fast path with its own logic) means the Lean definition it maps to (see the
  rows above) now describes *dead code*. **Update the corresponding Lean model to
  match, and re-run `formal/verify.sh`** (phased per
  [`docs/gate-runbook.md`](../docs/gate-runbook.md) §2; the one-shot blows the
  agent command cap) — otherwise the proof silently verifies an algorithm you no
  longer ship. If the new algorithm is hard to model, that is a signal to keep
  the old one behind the model, or to widen the model deliberately (a real formal
  task, not a silent drift). Either way: never let the code and the model diverge
  unrecorded — if you must ship ahead of the model, log it in §7.
* **A correctness fix can also move Python TOWARD the model.** When it does, say
  so and say why nothing became dead code (see the `ZT-P0-1` entry that opens
  §8.1) — that is the same bookkeeping obligation, discharged in the other
  direction.

### 8.1 Logged changes with no Lean impact (each with its reason)

* **★ `ZT-P0-1` — the N3 `_keys_referencing` elision WITHDRAWN as unsound
  (`index_v4/processor.py`, 2026-07-26). A correctness fix that REDUCES model
  divergence.** The processor used to short-circuit
  `::DeltaProcessor._keys_referencing` to `[]` on schemas whose every leaf kind
  sat in a `_RESIDUE_LOCAL_LEAF_KINDS = {'closure', 'derived-computed'}`
  whitelist (via a `_cross_object_recordings_possible` flag), so
  `::DeltaProcessor._residue_references` returned `False` unconditionally and
  `::DeltaProcessor._gc_subject_node`'s guard stopped protecting recorded nodes. That was an
  **authorization escalation** (a dangling residue `upos` id surviving rowid
  recycling ⇒ a false ALLOW). **Both the flag and the constant are gone;
  `_keys_referencing` now always scans**, and a "N3 WITHDRAWN — DO NOT
  RE-INTRODUCE" block at the top of `processor.py` records the precise property
  (P) a future whitelist would have to re-establish, and why the safe residual
  set is empty.
  **Formal disposition (verified, not assumed): nothing is owed to the Lean
  side.** Grepping `lean/ZanzibarProofs/` for `_keys_referencing` /
  `keysReferencing` / `residue_references` / node-GC surfaces returns **zero
  definitions** — `ReconcileDiff.lean` and `Cascade.lean` state outright that
  *"node GC is a modeled-away optimization"*. So **no Lean definition ever
  described the elided code**. The model has never had an elision; removing
  Python's moves the implementation **toward** the model, not away from it.
  Consequently: no Lean definition became dead code, no widening is owed, and no
  §7 divergence closes (the *unmodeled node-GC region* itself remains a
  divergence — now listed explicitly in §7.3, since the bug lived inside it).
  **Regression pin: `tests/test_reg14_residue_gc_elision.py`** (the reproduction
  plus the elision-disabled control, ported from the session scratchpad's
  `n3_FINAL.py`). Related: `ZT-P0-2` corrected the false "UNREACHABLE" comment on
  `index_v4/processor.py::DeltaProcessor._reconcile_subject`'s `sp != '...'`
  branch and gave that branch an
  escalation to the full reconcile — see the cheap-path entry in §7.1, which is
  where that change is recorded as a model gap.
* **★ Same-day guard hardening — admission/guard level, below the model's
  abstraction (2026-07-26).** Three fixes from the same review changed no modeled
  algorithm and need no Lean change:
  * **`ZT-P1-2`** — the load-bearing safety `assert`s in `index_v4/core.py` and
    `index_v4/processor.py` became explicit `raise InvariantViolation` (so they
    survive `python -O`); `core.py` now imports `InvariantViolation`. The
    conditions checked are unchanged; only their survival under `-O` changed.
    Modeled write admission (`GraphIndex/Write.lean::GraphState.admitEdge`) is a *decision
    procedure* — it says which writes are accepted, not by which Python
    statement form the rejection is raised.
  * **`ZT-P1-1`** — `zanzibar_utils_v1.py::is_valid_identifier` anchors with `\Z`
    + `fullmatch` instead of `$` (which matched before a trailing `\n`, admitting
    `'alice\n'` and a 257-char `'a'*256 + '\n'`). This **narrows** the admissible
    identifier set. `Core/Ident.lean` treats names as opaque strings and no
    theorem quantifies over the charset, so nothing is affected; the narrowing is
    in the same class as the §3 `GraphAccepts` scope rejections (admission-only).
  * **`ZT-P1-7`** — `ReachabilityIndex._lock_store` / `TupleSource._lock_source`
    memos are now keyed on `(get_transaction(), get_nested_transaction())` rather
    than the root transaction alone, so a caller `begin_nested()` can no longer
    silently disable both locks. Locking/concurrency is **explicitly unmodeled**
    (see the P12a entry below and the multi-instance bullet in §7.4): the chain
    models *what* is applied and *that* it is one transaction.
  None of these touches a row above. They are logged here so the "every change
  gets a disposition" discipline is visibly unbroken.

#### 8.1 (continued) — logged behavior-preserving perf optimizations (no Lean change)

*(This is the original §8.1 list, unchanged in substance; the correctness/guard
entries above were prepended 2026-07-26 so the section covers every logged
no-Lean-impact change, not perf only.)*

* **P2 — batched closure-region access (`index_v4/core.py`, 2026-07-14).**
  `_add_direct_edge_unsafe`'s three expansion loops previously called
  `_add_db_edges_unsafe` once per closure pair, each a point `SELECT` + write
  (N+1). They now gather the whole `(from, to, indirect_delta)` region and apply
  it via `::ReachabilityIndex._add_indirect_edges_batch_unsafe`: one chunked
  row-value `IN` `SELECT`, in-memory increments, one flush. **Below the model's
  abstraction level; no Lean change.** The T4 model (`GraphIndex/Closure.lean::pathCount_addEdge`
  / `::pathCount_removeEdge`, §3 `GraphState.reach`) states the closed-form
  *final* path counts per pair; the batched code applies the identical per-pair
  arithmetic (`phat a u · phat v b` products), so the final `EdgeV4` state is
  unchanged — `DirectGraph` is a pure `V → V → Nat`, with no notion of a DB
  round-trip to restructure. The outbox model (§4 `pushDelta` /
  `writeLoggedRules`) is likewise preserved: the loops enumerate **distinct**
  pairs, so each pair already flipped at most once, and the batch emits the same
  action per pair in the same loop order. Netted by the differential matrix, the
  outbox/processor tests, the remove-path and hypothesis add/remove-restoration
  gates, and `test_conformance_state.py`.
* **P1 — set-engine forward `lookup`: O(store) sweep → O(reachable) reverse walk
  (`setengine/engine.py`, 2026-07-14).** The forward `lookup` surface is **not
  modeled in Lean.** §2 models the set-engine *semantics*;
  `::SetEngine.lookup_reverse` is `expand` rendered and rides on the `expand`
  model — **both unchanged by P1.** `lookup` itself was a Python-only composition:
  `check` over every interned key. P1 replaced the candidate sweep with a reverse
  BFS (`::SetEngine._reverse_neighbors` / `::SetEngine._reverse_neighbors_key`), verifying
  every surfaced candidate with the unchanged `check`. **Hybrid:**
  object-wildcard schemas kept the exact O(store) sweep (`::SetEngine._lookup_sweep`) — a
  hypothesis-deep finding. Observable output identical (same `node_ids` +
  `markers`); no modeled definition describes `lookup`'s candidate generation.
  Pinned **exact two-sided** by `tests/test_lookup_oracle.py` (S4) against the
  independent brute-force oracle. **Superseded by N17:** the hybrid/fallback is
  removed; `lookup` now walks on every schema.
* **N17 — set-engine forward `lookup`: O(store) sweep fully removed
  (`setengine/engine.py`, 2026-07-15).** Same disposition as P1. N17 deletes P1's
  object-wildcard `_lookup_sweep` fallback so the O(reachable) reverse walk runs
  for **every** schema. Candidate generation is **widened**, the observable output
  unchanged: (a) inline *wildcard-bridge seeding* on dequeuing a star node of an
  object-wildcard type; (b) an H3 *star-bare fold* in `::SetEngine._reverse_neighbors` plus
  a subject-shape walk seed. `::SetEngine._lookup_sweep` is retained only as the
  **differential test reference**. Pinned exact two-sided by
  `tests/test_lookup_oracle.py` (S4, incl. the `owc_star_ttu` corpus + 8
  handwritten regressions) and a **walk == sweep** differential property test
  (`test_owc_bridge_walk_vs_sweep`, both `SetOps`).
  **Commit-1 completeness bug (no Lean impact):** the pre-existing candidate
  generation was *incomplete*, not the modeled semantics — the H3 TTU from-chain
  folded only the concrete bare parent, dropping the STAR bare parent; and the
  walk seed skipped uninterned userset subjects whose reachability is a
  from-chain star identity. Both are candidate-generation completeness fixes on
  an unmodeled surface.
* **P12a/P12b — composition write-path round-trip elision
  (`index_v4/core.py::ReachabilityIndex._lock_store`, `connectedstore/`,
  2026-07-14).** Both below the model's abstraction; no Lean def describes them.
  `ReachedByW3d2E` (§6) models the sync write path as *admitted write +
  same-transaction cascade* — WHAT is applied and THAT it is one transaction.
  P12a memoizes the `SELECT…FOR UPDATE` store-lock re-take per transaction
  (locking/concurrency is unmodeled; the lock is still taken, once, before the
  cursor read — and see the `ZT-P1-7` entry above, which fixed that memo's key).
  P12b hands `connectedstore/apply.py::advance_index` the just-flushed
  `TupleLogV1` row instead of
  re-SELECTing it, guarded by `cursor.applied_log_id == rows_hint[0].id - 1` plus
  strict contiguity, with an exact `log_rows` fallback — the same rows in the
  same order reach the same apply loop. Netted by the full differential suite +
  `tests/test_connectedstore_*` + graph conformance (verdict + state).
* **P13 — bulk closure builder for `build_index`
  (`index_v4/bulk_build.py`, `connectedstore/build.py`, 2026-07-15).** The
  offline bootstrap can construct the pre-backfill graph state directly: route
  the tuple snapshot to a natural-key direct multigraph, topo-sort, compute
  per-pair path counts by sparse integer DP (`P(a,b) = m(a,b) + Σ_v
  m(a,v)·P(v,b)` — **T4's closed form computed directly**), bulk-write
  nodes/edges/outbox. The modeled algorithm (incremental `pathCount_addEdge`
  maintenance) is unchanged and remains the default for every online write; the
  bulk path is an **alternative constructor of the same state** behind
  `build_index(..., bulk=True)`. **The net is the differential identity gate**
  (`tests/test_bulk_build.py`): same snapshot built both ways, compared on
  id-independent canonical projections, plus the I1–I13 checker and an oracle
  read-parity grid. No modeled definition describes dead code.
* **R4-BF — bulk boolean backfill for `build_index`
  (`index_v4/bulk_backfill.py`, `index_v4/bulk_build.py`,
  `connectedstore/build.py`, 2026-07-15).** Same disposition as P13, one layer
  out. The **incremental backfill/cascade is the modeled algorithm** — the
  per-flip reconcile + per-stratum cascade (§4/§5) still runs for every online
  write, and `::DeltaProcessor.backfill()` itself is unchanged (it survives as
  the repair path and the `bulk=False` reference side). The bulk backfill is an
  **alternative constructor of the same modeled state**, reusing the compiled plan
  closures (`plan.check_fn` / `plan.stars_fn` via a `_BulkEvalContext` matching
  the `_EvalContext` callback protocol). **The net is the extended differential
  identity gate** (`tests/test_bulk_build.py`, 6 corpora, each guarded by
  anti-vacuity assertions), plus the I1–I13 checker and an oracle read-parity
  grid. *Note (`ZT-P3-6`): bulk build/backfill is the DEFAULT `build_index` path
  and an entirely separate constructor of index state with no Lean model, pinned
  only by a Python↔Python differential — it is documented here but was missing
  from `FINAL_REVIEW.md` §3 / `ARCHITECTURE.md` §6's residual-surface lists.*
* **N18 — stream the bulk builder's Phase-W writes + Phase-R snapshot read
  (`index_v4/bulk_build.py`, 2026-07-16).** A pure RAM-ceiling optimization on
  the same alternative constructor; **no rows, no state, and no modeled algorithm
  change**. The Phase-P DP is untouched. What changed is *how* the
  already-computed rows reach the DB: (a) Phase W builds/executes/frees the edge,
  residue and outbox row dicts in bounded `_WRITE_CHUNK` chunks in the identical
  order, so per-table auto-increment ids are assigned exactly as the old single
  INSERT; (b) Phase R streams the snapshot with `yield_per` over the six routed
  columns in the same `order_by(TupleV1.id)` order; (c) flushed `NodeV4`
  instances are expunged after `node_id` capture. The written multiset is
  byte-identical — pinned by the same differential identity gate.

---

## 9. PROPOSAL (design only — NOT implemented): a mechanical anchor check

**Status: a concrete proposal. Nothing below is wired. Someone else owns landing
it.** This section exists because §0's premise — "no manually-maintained line
number survives" — applies equally to manually-maintained *symbol* names. The
anchors above are correct on 2026-07-26 and will rot without a machine check.

**This design is not speculative.** A throwaway prototype of exactly the
algorithm below was run against this file during the rebuild; it found **~50
genuine anchor defects in the first draft** (bare anchors inheriting the wrong
file across a paragraph boundary, missing class qualifiers, Lean names missing
their `GraphState.`/`GraphModel.` namespace, `.lean` paths missing their
`GraphIndex/` directory), all of which are now fixed. Final state: **239 Python
anchors + 102 Lean anchors, 0 unresolved.** The prototype was deliberately not
checked in — this section is the spec, and whoever lands it should write it
properly with tests. The counts above are the honest starting floors.

### 9.1 What it checks

One script, `formal/conformance/anchor_check.py`, that:

1. **Parses anchors out of this file.** Two regexes over `CORRESPONDENCE.md`:
   * Python: `` `([A-Za-z0-9_./-]+\.py)::([A-Za-z_][A-Za-z0-9_.]*)` `` — plus the
     continuation form <code>&#58;&#58;Symbol</code> (bare, no file), which inherits the most
     recent file named in the **same table cell or prose paragraph**. (Rows above
     use the bare form heavily
     for readability; resolving them by row is what keeps the prose usable.)
   * Lean: `` `([A-Za-z0-9_/]+\.lean)::([A-Za-z_][A-Za-z0-9_.']*)` ``.
2. **Resolves each Python anchor by `ast` parse, never by import.** Walk the
   file's `ast`, building the set of `__qualname__`-style dotted names from
   `FunctionDef` / `AsyncFunctionDef` / `ClassDef` nesting (exactly the walker
   used to rebuild this file). **Also collect class-body `AnnAssign`/`Assign`
   targets** — several rows anchor on dataclass/SQLModel *fields*
   (`SchemaInfo.subject_wildcard_shapes`, `EdgeV4.derived`), which a
   def-only walker rejects. Restrict that collection to `ClassDef` bodies, or
   function locals leak into the symbol set and weaken the check (the prototype
   hit exactly this). No import means no side effects, no DB, no `sys.path`
   games, and it works on `tests/` and `formal/conformance/` files identically.
3. **Resolves each Lean anchor by declaration scan.** Regex for
   `^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+|partial\s+)*(?:def|theorem|lemma|abbrev|structure|inductive|instance|opaque)\s+([A-Za-z_][A-Za-z0-9_.']*)`
   per file, plus `namespace`/`end` tracking so `namespace GraphModel` + `def
   check` resolves the anchor `GraphModel.check`, **and structure-field capture**
   (an indented `field : Type` line under the last declaration) so `Delta.leaf`
   and the `Inv` clause names resolve. Note most graph-side definitions are
   written `def GraphState.foo` *inside* `namespace Zanzibar`, so both
   `GraphState.foo` and `Zanzibar.GraphState.foo` are valid — accept the
   shortest. Deliberately a scanner, not an elaborator: it must run in ~1 s
   without a Lean toolchain, so it can gate cheaply and can't itself become a
   build dependency.
4. **Asserts a non-vacuity floor.** `ZT-P2-1`/`ZT-P2-2` showed the failure mode
   where a gate's expected count is derived from the artifact it audits. So:
   hardcode `MIN_PY_ANCHORS` / `MIN_LEAN_ANCHORS` (start at **230 / 95**, just
   under the measured 239 / 102) and fail if fewer are *found*, independently of
   how many resolve. Deleting rows must break the gate; that is the whole point.
5. **Reports, per failure, the closest surviving symbol** (`difflib.get_close_matches`
   over the file's symbol set). A rename then produces
   `processor.py::DeltaProcessor.reconcile → did you mean
   DeltaProcessor._reconcile?`, which is the fix, not just the alarm.
6. **Fails on a file that does not exist** (a moved module is the loudest signal
   of all) and on an anchor whose file is outside the repo.

### 9.2 What it deliberately does NOT check

* **Semantic correctness of a row.** It cannot tell you `SetEngineModel.check` ↔
  `SetEngine.check` was a false twin claim (§2) — that took reading both. It
  keeps the map *navigable*, not *true*. Say so in its docstring, or the next
  reviewer will over-trust it exactly the way the previous revision of this file
  was over-trusted.
* **Lean docstring citations.** The stale `processor.py:989-1027` strings inside
  `Cascade.lean` etc. are a separate cleanup; a v2 could add "no `\.py:\d` in any
  `.lean` docstring" as a lint once those are purged.
* **Prose that names a symbol without anchoring it.** Plain backticked
  `WildcardIndex.check` (no `::`) is invisible to the check by design — the
  anchor form is opt-in. That is the escape hatch for illustrative text, and §0's
  convention examples deliberately use it. The cost is that an author can dodge
  the check by dropping the `::`; the mitigation is the count floor in step 4.

### 9.3 Where it hooks into the gate

Add it as a **pytest module**, `formal/conformance/test_anchor_check.py`, not as
a raw `verify.sh` step:

* It then rides the existing `MIN_CONF_*` floors and the zero-tolerance
  skip/xfail parsing that `verify.sh` already applies to the conformance
  directory — no new bespoke shell arithmetic, and no chance of the new check
  passing vacuously the way `ZT-P2-1` did.
* It lands in the **`conf-rest`** tile (it is milliseconds; `conf-heavy` is
  `test_conformance_remove.py`). With the 2026-07-26 `conf-tile:I/K` tiling it
  simply joins the collection.
* It needs no zcli binary and no Lean build, so it also runs under plain
  `pytest formal/conformance/ -k anchor` during a docs-only session — which is
  when this file is most likely to be edited.
* Suggested shape: one parametrized test per anchor (so the failure names the
  broken row), plus two floor tests. Roughly `2 + N` node ids; bump
  `MIN_CONF_ALL` accordingly when landing.

### 9.4 Migration note

Landing this will require normalizing a handful of anchors above that name a
*concept* rather than a symbol (e.g. rows that point at "the `if … not in
tainted` loop in `zanzibar_utils_v1.py::compile_ruleset`"). Those already carry a
resolvable symbol
(`compile_ruleset`) — the prose is the extra. Keep that convention: **every
backticked `file::symbol` must resolve; free prose around it may describe the
step.**
