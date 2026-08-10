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
* §9's mechanical anchor check **LANDED 2026-07-27** as
  `formal/conformance/anchor_check.py`, run by `formal/verify.sh` in the `lean`
  phase (step 4c). Every `file::symbol` anchor below is asserted to resolve on
  every gate run, and the anchor COUNT is floored so deleting rows fails too. It
  keeps this file *navigable*, not *true* — a resolvable anchor can still head a
  wrong claim (see §2's `check` row), so the freshness date still governs the
  CLAIMS; it no longer governs the pointers.

**Anchors below were re-derived against the working tree on 2026-07-26** — after
the same day's `ZT-P0-1` (N3-elision withdrawal), `ZT-P1-1`/`ZT-P1-2`/`ZT-P1-7`
guard hardening, and `verify.sh` gate-floor changes — and are now **verified
mechanically on every gate run** by the §9 checker (`anchor_check.py`, landed
2026-07-27): every anchor parsed and resolved, with floored counts — the live tally
is printed by each `lean`-phase gate run and echoed in `FINAL_REVIEW.md`'s generated
counts block (when measured 2026-07-29: 397 anchors, 0 unresolved). That is a claim about
*navigability only* (every named symbol exists, in the named file); it says
nothing about whether a row's correspondence claim is true. §2's `check` row is
the standing proof that a resolvable anchor can still head a wrong claim.

### Conformance gates (`formal/verify.sh` step 5, `formal/conformance/`)

**The inventory counts are GENERATED, not restated here** — `corpus.SCHEMAS`,
`corpus.GRAPH_FRAGMENT` (`object_wildcard` is still the one excluded), the
spec-scope total across the FOUR dicts (`SCHEMAS` + `TTU_USERSET_SCHEMAS` +
`SELF_REFERENTIAL_SCHEMAS` + `MULTI_STRATUM_SCHEMAS`, the last being
`three_strata_chain`, spec-side ONLY — the Lean operational model's cascade is a fixed
two rounds, so a 3-stratum corpus can never enter `GRAPH_FRAGMENT`), and the
per-file test counts all live in `FINAL_REVIEW.md`'s generated counts block,
re-checked by `verify.sh` step 4e. This paragraph kept its own copies, and by
2026-08-09 they had gone stale three times (a "6 files / 17 corpora / 15
in-fragment / 330 tests" set, then "2026-07-26: 20 / 19 / 13 files / 356 tests",
then the 2026-07-29 re-measurement — 24 / 23 / 33 / 15 files / 465 tests — which
later corpus additions falsified as well). The three
files marked ✚ below were entirely undeclared here before 2026-07-29, and one of them
(`test_conformance_remove.py`) *is* the whole legacy `conf-heavy` phase.

| gate | compares | corpora |
|---|---|---|
| `test_conformance_spec.py` | Lean `sem` (zcli) vs `tests/oracle.py` vs real `SetEngine` | all spec-scope (four dicts) |
| `test_conformance_random.py` | same, randomized stores | random |
| ✚ `test_conformance_generated.py` | same, over GENERATED schema shapes outside the curated corpora (seeded re-implementation of the hypothesis generator) | generated |
| `test_conformance_graph.py` | Lean **operational graph model** (zcli mode `"graph"`) vs real `WildcardIndex`+`DeltaProcessor`, and vs `sem` | every `GRAPH_FRAGMENT` corpus |
| `test_conformance_state.py` | Lean graph model **FINAL STATE** (zcli mode `"graph-state"`) vs the Python index's final SQL rows (`EdgeV4`/`ResidueV1` via `NodeV4`), projections per `extractor.py` | every `GRAPH_FRAGMENT` corpus |
| ✚ `test_conformance_remove.py` | **the entire legacy `conf-heavy` phase.** Interleaved add/remove streams DRIVEN through the real `SetEngine` (not a rebuild) vs `sem` on the final store vs oracle | remove streams |
| `test_conformance_remove_graph.py` | zcli `"ops"` streams (`graphRunOps`) vs the real graph index vs oracle, ANSWER level | `GRAPH_FRAGMENT` minus `direct_arm_exclusion` |
| ✚ `test_conformance_direct_arm.py` | Python-only (no zcli) both-`SetOps` 3-backend differential + exhaustive small-store attack on the Direct-arm-under-exclusion corpus | `direct_arm_exclusion` |
| `test_conformance_nary_strata.py` | Python-only (no zcli) `>= 3`-stratum graph differential + the `wildcard_userset` bridge pins — the shapes the Lean operational model cannot reach | `MULTI_STRATUM_SCHEMAS` / `TTU_USERSET_SCHEMAS` |
| `test_grid_independence.py` | the shared grid is read off the PRODUCTION parser, not the encoder's oracle parse (incl. a sabotage test) | every curated corpus + every generated schema |
| `test_conformance_enum.py` | **exhaustive small-scope enumeration**: spec vs oracle vs set engine vs real graph index on ALL stores ≤ K tuples | **6** fragment shapes, **1021** stores, per-shape **K = 3 or 4** (counts + tuple-space sizes asserted) |
| ✚ `test_conformance_enum_state.py` | STATE-level analog of the enumeration, on a deterministic sample, same P1–P7 projections | same 6 shapes |
| `test_cli_mode.py` | zcli mode dispatch fails closed | minimal |
| `test_runner_retry.py` (gate tooling) | `runner.invoke_zcli`'s pre-`main` retry never masks a real fault | — |
| `test_sorry_scan.py` (gate tooling) | `sorry_scan.py` catches `sorry`/`admit`/`sorryAx`/`native_decide`/`axiom` (post-`ZT-P2-3`) | — |

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

**Independence — exactly what is and is not independent (ZT-P4-6; the grid half
FIXED 2026-07-27).** The blanket "three genuinely independent corners" phrasing
this section used to carry was **false at the schema-READING layer**. State it
per layer instead:

| layer | independent? | why |
|---|---|---|
| **evaluation** — Lean `sem` / `tests/oracle.py` / `SetEngine` / `WildcardIndex` | **YES** | four separately written evaluators sharing no code; this is the property the differentials actually rest on |
| **query grid** — which queries get asked | **YES, since 2026-07-27** | `formal/conformance/grid.py` now derives declared targets from `zanzibar_utils_v1.py::parse_schema_ast` (the PRODUCTION parser), not the oracle's. Pinned by `formal/conformance/test_grid_independence.py` (incl. a sabotage test: patching the oracle's parser must not move a grid) |
| **schema reading into Lean** — `formal/conformance/encode.py` | **NO** | `formal/conformance/encode.py::schema_to_json` still parses via `tests/oracle.py::parse_schema_ast`, so the Lean corner is fed by the ORACLE's parse. `encode.py`'s own docstring is honest about it; this is the residual |

Why the grid half mattered more than it looks: with a shared parse, a misparse
propagated into the Lean corner **and simultaneously deleted the query that
would expose it** (a relation the oracle fails to see is a relation nobody
queries). With the grid on the production parser, an oracle misparse now yields
a query that *can* expose it. The two parsers really are different code — on a
duplicate `define`, `tests/oracle.py` silently keeps the last while
`zanzibar_utils_v1.py` raises
(`formal/conformance/test_grid_independence.py::test_the_two_parsers_are_really_different_code`
pins that divergence live). Re-measured 2026-07-29 over the **33** curated corpora
then present + 40 generated schemas: the two parsers' declared-key sets were identical, so the
swap changed **zero** grids (byte-identical `(subjects, targets)` on all **73**
cases) — that agreement is itself now gated
(`::test_declared_keys_agree_on_every_corpus` /
`::test_declared_keys_agree_on_every_generated_schema`), so a future divergence
surfaces as a named finding instead of a silently shrunken grid.
**Residual, unclosed:** `encode.py`. Closing it means re-encoding from the
production AST (a different `Expr` type: `zanzibar_utils_v1.py::Direct` /
`::Computed` / `::TTU` / `::Union` / `::Intersection` / `::Exclusion`), which is
a real port, not a swap — the Lean corner would then be fed by the production
parser and the ORACLE would become the only reader of its own parse.

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
| `GraphIndex/RulesWrite.lean::rewriteClosureRaw` | the write fan-out worklist, before dedup | `zanzibar_utils_v1.py::RuleSet.apply`'s expansion (dispatch built by `::RuleSet._build_dispatch`, candidates by `::RuleSet._candidates`) |
| `GraphIndex/RulesWrite.lean::rewriteClosure` | the write fan-out worklist **incl. the dedup** (2026-08-08, §7.2 item 6) | `zanzibar_utils_v1.py::RuleSet.apply` in full — its `processed` set is the dedup AND the termination mechanism, so this is not an optional mirror |
| `GraphIndex/RulesWrite.lean::mem_rewriteClosure_iff` | dedup is membership-transparent | — (model-internal bridge; no Python counterpart) |
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
| `GraphIndex/CascadeStrataEnum.lean::storedDirectSubjects` (**star-filtered 2026-07-28**) | the Direct-arm audit candidates read from the FIXED store, wildcard subjects excluded | `index_v4/processor.py::DeltaProcessor._incoming_concretes` (`return [n for n in nodes if n.wildcard == '']`) and the `n.wildcard != ''` skip in `::DeltaProcessor._reconcile`'s `upos` loop. Lean already mirrored this in `GraphIndex/CascadeEnum.lean::leafConcretes` (`u.name != STAR`); `storedDirectSubjects` was the outlier until leg 1 of the E-chain arc. **Consumed by the operational E-chain since leg 2 (2026-08-04)** — `enumJobs2At` runs `enumJob2D`; see `history/echain-widening-plan-2026-07-28.md` |
| `GraphIndex/CascadeStrataEnum.lean::freshDirectCands` | the CANDIDATE-level presence diff: a stored Direct-arm subject enters `cands` only if it is not already one (∉ `enum2Base`, ∉ `GraphIndex/CascadeEnum.lean::edgeHolders`) | `index_v4/processor.py::DeltaProcessor._reconcile` builds `candidates` as a `dict[int, NodeV4]` keyed on node id, so re-contributing a present node is a no-op. **Distinct from the EDGE-level presence diff** (`::DeltaProcessor._reconcile_subject`'s `want_edge and not has_edge`), which the model still does not mirror — §7.2 item 6 |
| `GraphIndex/CascadeStrataEnum.lean::enumJob2D` (run by `GraphIndex/CascadeStrataAssemble.lean::enumJobs2At` since leg 2) | the Direct-arm-widened per-key audit enumeration, and the per-round job list that now runs it | `index_v4/processor.py::DeltaProcessor._reconcile`'s candidate/audit assembly. **Behaviourally identical to the pre-leg-2 `enumJob2` on the `ComputedOnly` scope** — `GraphIndex/CascadeStrataEnum.lean::enumJob2D_eq_enumJob2`, a theorem, which is why no graph-state golden moved when it landed |
| `GraphIndex/ReconcileCorrect.lean::DirectArmsConcrete` | **no Python counterpart — a declared PROOF-SIDE scope carry** | Python ADMITS what this excludes: `define approver: [user, user:*] but not banned` compiles (`zanzibar_utils_v1.py::derive_schema_info` collects the wildcard shape regardless of the enclosing boolean), and oracle == set engine == real graph index over the full grid. It is a **vacuity** boundary for the widened fragment, not a restriction on the implementation — the full argument is in the declaration's own docstring |

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
| `FullScope.lean::GraphAdmission` (`wf`/`nodup`/`strat`/`ttuDirect`/`matchDecl`/`ranked`/`objWild`/`storeValid` — the last WIDENED to `StoreValidRulesD` by E-chain leg 5, 2026-08-05, mirroring `RuleSet.apply` routing a public-name write onto a derived def's Direct leaf family) | what compile+write admission guarantees | see field docs; e.g. `ttuDirect` ↔ `zanzibar_utils_v1.py::_validate_ttu_tuplesets`, `matchDecl` ↔ `zanzibar_utils_v1.py::RuleSet.apply`'s raise on a raw write matching no declared restriction, `objWild` ↔ `::_reject_object_wildcard_scope` |
| `FullScope.lean::W4Fragment` (`computedOrDirect`/`directArmsBare`/`directArmsConcrete`/`computedOnlyOperands`/`noUnionDirects`/`twoStrata`/`wsBare`/`bareStar`/`ttuStarFree`/`term` — **TEN** fields since E-chain leg 5, 2026-08-05, split `computedOnly` into the first five; `rootB` was deleted 2026-07-17). Plus `FullScope.lean::W4NarrowT2a` (`computedOnly`/`storeValid`), which **T2a `graph_reached_inv` alone** takes IN ADDITION — the widening's declared asymmetry, counterexampled at a real store by `W4WitnessDirect.outside_narrow_t2a` | — the HONEST carries: restrictions Python does NOT impose | `history/ROADMAP.md` "W4 — honest gaps" |
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

* **`ResidueV1.version` is gated by nothing formal — now DECLARED as projection
  P7 (`ZT-P4-5(b)`, 2026-07-27).**
  `index_v4/models.py::ResidueV1` carries a `version` column, incremented in
  `index_v4/processor.py::DeltaProcessor._store_residue` and checked by I7 (monotonicity per residue
  row) in `index_v4/invariants.py::_check_residue_rows`.
  `formal/conformance/extractor.py::lean_graph_state` and `::python_graph_state`
  compare only `(stars, neg, upos)`. Until 2026-07-27 `version` was dropped
  **silently** — not one of the documented projections; it is now **P7**, stated
  with its reason in `formal/conformance/extractor.py`'s module docstring and at
  the drop site in `::extract_sql_state`.
  **The disposition is a MODELLING GAP, not a representation difference.**
  `GraphIndex/State.lean::Residue` is `⟨stars, neg, upos⟩` and has no version
  field (its own doc comment says so); `grep -rn 'version'
  lean/ZanzibarProofs/GraphIndex/` returns only that comment. So unlike P1–P6,
  where an argument recovers the dropped information from what remains, there is
  simply nothing on the Lean side to compare against. Consequence, stated
  plainly: **I7 is pinned only by `tests/` paranoia runs**, `Inv` has no clause
  for it, and `install_paranoia` is not wired into `ConnectedStore`
  (`ZT-P1-3`). Modelling it (a monotone counter on `Residue` plus an `Inv`
  clause) remains open and is a real, if small, widening.
* **State-gate thinness (`ZT-P4-5(a)`, RE-MEASURED 2026-07-27; the numbers below
  replace the stale 2026-07-26 ones — 422/231/55/136 over 19 corpora).** The
  in-fragment corpus set had grown to **21** (`nary_union`, `nary_intersection`
  landed 2026-07-26). Driving `formal/conformance/backends.py::graphindex_drive`
  over `sorted(GRAPH_FRAGMENT)` and applying
  `formal/conformance/extractor.py::extract_sql_state`'s own filters:
  of **447** raw `EdgeV4` rows, **231** are dropped by P1 (closure-only), **0** by
  P2 (which still never fires), **62** by P6 (leaf-family copies), and **154** are
  actually compared. **All 235 `NodeV4` rows are dropped by P5** — nodes are not
  compared at all; of those 235, 194 are endpoints/references of the compared
  state (hence implicitly pinned) and **41 are invisible to the gate entirely**.
  Only **5 of 21** corpora produced ANY residue row (**11** rows total), so 16
  corpora compared two empty residue dicts — and every one of those 11 rows had
  `|stars| == 1` and `|neg| == 1`.
  > **★ SUPERSEDED 2026-08-05 — every figure in the paragraph above is STALE, and
  > the whole class is now GENERATED instead of narrated.** The live numbers are in
  > `FINAL_REVIEW.md`'s generated counts block ("State-gate projection ledger"),
  > produced by `formal/conformance/extractor.py::graph_fragment_ledger` and checked
  > by `verify.sh` step 4e. **Read them there; do not restate them here.** For the
  > record, the drift: 21 → **23** corpora, 447 → **477** raw rows, 231 → **233**
  > P1, 62 → **73** P6, 154 → **171** compared, 235 → **266** `NodeV4`, 11-over-5 →
  > **13-over-6** residue rows. Only the P2 zero survived. The residue claim above
  > is now false in the right direction — `residue_rich` contributes `(2,2,1)` and
  > `(2,2,0)` and `taint_union_userset_arm` a `(1,1,1)`, so 11 of 13 rows are
  > `|stars|=|neg|=1`, not all of them.
  > The **194/41** `NodeV4` endpoint split re-derives as **217/49**, but it is
  > deliberately NOT under the pin: unlike the edge ledger it has no in-repo
  > implementation to reuse, so "referenced" had to be reconstructed (edge endpoints
  > ∪ residue object nodes ∪ residue `neg`/`upos` subject nodes) and the number is
  > method-sensitive. Treat **266** as solid and 217/49 as provisional; pinning it
  > needs the definition written down first.
  **Partly closed 2026-07-27:** the
  `residue_rich` corpus (in `GRAPH_FRAGMENT`, pinned by
  `formal/conformance/test_conformance_state.py::test_residue_rich_corpus_is_really_rich`)
  is the first with a multi-shape `stars`, a multi-subject `neg` and a `upos`
  member on two derived keys, so the residue comparison is no longer
  singleton-only; and
  `::test_python_nodes_are_all_justified` adds the one node-level property that
  is checkable at all (no orphan node rows, Python-side — 0 measured). The
  2026-07-17 note below conceded node-flag behavior is "invisible to the gate by
  construction"; that concession is now quantified here, in
  `formal/conformance/extractor.py`'s P5 paragraph, in `FINAL_REVIEW.md` §3 and
  in `ARCHITECTURE.md` §6.
  **P2 alone RE-MEASURED 2026-07-29** over the then-current **23**-corpus in-fragment
  set (`nary_union_derived4`, `residue_rich` landed since 2026-07-27): **477** raw
  `EdgeV4` rows, still **0** dropped by P2, and the compiled `bridged_in_shapes` /
  `bridged_out_shapes` sets were EMPTY on every one of the 23 — so the "P2 never
  fires" claim was measured against the corpus set as it stood then, not an
  older and smaller one (the generated ledger's P2 row now keeps the zero current). ~~The P1/P6/P5/residue figures above remain the 2026-07-27
  measurement over 21 corpora and are NOT re-measured here.~~ **All legs were
  re-measured 2026-08-05 and put under the pin — see the superseded-notice above.
  This sentence is why the pin exists: it correctly flagged the other legs as
  un-re-measured, and they then stayed that way for a week because flagging is not
  enforcing.**

* **★ ADJUDICATED 2026-07-29 — derived-edge MULTIPLICITY diverges: the model's
  cascade enumeration re-adds an edge it already holds, Python dedupes by node
  id. The verdict is below; the finding as filed on 2026-07-28 follows it
  verbatim, for provenance.**

  **Verdict: REAL, model-side, and confined EXACTLY to the derived arm. The gate
  hole is closed — not by fixing the model, but by splitting P3 so that the half
  which corresponds is now CHECKED and the half which does not is now MEASURED.**

  **1. What Python actually does — the filed finding understated it.** The filed
  text says Python "dedupes by node id", citing the `candidates`/`audit` dicts.
  True but not the operative fact: the operative fact is that
  `index_v4/processor.py::DeltaProcessor._reconcile_subject` writes a derived edge through a
  **presence diff** (`want_edge and not has_edge`, over
  `index_v4/core.py::ReachabilityIndex.direct_edge_exists_by_id`), so re-deriving an
  already-present derived edge is a total no-op — no row touched, no count
  bumped, `changed` stays False. Python's `EdgeV4.direct_edge_count` on a
  processor-written derived row is therefore **always 0 or 1**, structurally.
  Measured 2026-07-29, over the 23 corpora then in `GRAPH_FRAGMENT`: all 18 such
  rows were exactly 1 (the live per-corpus figures are golden-pinned by the
  derived-arm multiplicity ledger, item 5 below).

  **2. The correspondence claim that is FALSE.** `GraphIndex/ReconcileDiff.lean`'s
  header states *"`GraphState.edges : List (NodeKey × NodeKey)` is ALREADY a
  multiset (list multiplicity == `direct_edge_count`)"*, and `Cli.lean`'s header
  used to justify the dump's edge de-duplication the same way. That equation
  **holds on the untainted arm and fails on the derived arm**, where Python is
  capped at 1 by (1) and the model compounds. It was stated without the split.
  Both docstrings are corrected.

  **3. Measured shape (2026-07-29, over the 23 corpora then in `GRAPH_FRAGMENT`).** Of 171
  compared edges: **153 untainted-arm, agreeing EXACTLY** — including the one
  genuinely non-unit case, `nary_union`'s three-arm fan-in onto the untainted
  `any_of`, where both sides say 3 — and **18 derived-arm, all diverging**,
  Python uniformly 1 against Lean 4 … **1013** (`two_stratum_cascade`). Note
  **the filed `1 → 2 → 4 → 8` understates the growth**: that is the shape with a
  single candidate at the key; with several it compounds superlinearly. There is
  **zero set-level asymmetry**, so the pre-existing equality gate was honestly
  green.

  **4. Does it affect a removal's drained state? NO — but by assembly, not by a
  theorem.** Derived edges are retracted only by `GraphIndex/ReconcileDiff.lean::GraphState.removeEdgePair`
  (filter-ALL), the else-branch of `GraphIndex/CascadeStrata.lean::reconcileKeyDR`, so a
  stacked derived edge is zeroed in one step — `ReconcileDiff.lean`'s header says
  the filter-all was chosen *as the compensation* for the stacking. The erase-ONE
  primitive `GraphIndex/ReconcileDiff.lean::GraphState.removeEdgeOne` is used only by
  `GraphIndex/Cascade.lean::removeLoggedOne`, whose targets are untainted under
  `StoreValidRules` + `ComputedOnly`
  (`GraphIndex/CascadeStrataSettle.lean::reachedByRulesAdmitted_edge_target_untainted`), a
  conjunct `GraphIndex/Exec.lean::removeGateB` decides at runtime. So multiplicity is
  inert for removal. **Caveat worth carrying: no single theorem states this** —
  it is assembled from filter-all + the erase-one domain restriction + the
  untainted count law `GraphIndex/RemoveOccCount.lean::reachedByW3d2E_untOccCount`. Reads are
  inert by construction (`GraphIndex/State.lean::reachB` is an `any` over the
  list, and `reach`'s fuel is `nodes.length + 1`, untouched by duplicate edges).

  **5. What was done about the gate.** `P3` is narrowed rather than dropped:
  * `Cli.lean` gained an **`edgeCounts`** field (`Cli.lean::edgeCountsJson`) —
    multiplicity previously died at `Cli.lean::canonJsonArr` *inside the Lean
    binary*, so before this the Python side could not have observed it even as a
    multiset. The `edges` array is unchanged.
  * `formal/conformance/extractor.py::diff_states` now compares
    `direct_edge_count`-weighted multiplicity **exactly on the untainted arm**,
    in both `test_conformance_state.py` (every `GRAPH_FRAGMENT` corpus) and
    `test_conformance_enum_state.py` (~257 sampled enumerated stores). This is
    net-new assurance: those 153 edges' multiplicity had never been compared.
  * the derived arm is pinned per corpus against a golden
    (`formal/conformance/derived_arm_multiplicity.json`, gated by
    `formal/conformance/test_conformance_state.py::test_derived_arm_multiplicity_ledger`), so the
    artifact's shape is a checked quantity. **This supersedes the E-chain plan's
    §D.6 probe** — Leg 2 is *expected* to move these numbers, and the ledger will
    say so and by how much, automatically.
  * the exemption boundary is computed from the SCHEMA
    (`formal/conformance/extractor.py::derived_relations`), and cross-checked
    against `EdgeV4.derived`
    (`formal/conformance/extractor.py::_classify_edges`), so a corrupted flag
    cannot move it silently.

  **5b. Update 2026-08-04 (E-chain Leg 2) — the ARC-LOCAL half is discharged, and the
  ledger did not move.** The `n ↦ 2n+1` growth the filed text below attributes to
  `enumJob2D` is closed by
  `GraphIndex/CascadeStrataEnum.lean::freshDirectCands`, a presence diff on the
  Direct-arm contribution to `cands` — NOT by the `.dedup` the E-chain plan prescribed,
  which sits in the wrong place (the duplicate is between `storedDirectSubjects` and
  `GraphIndex/CascadeEnum.lean::edgeHolders`, not inside
  `GraphIndex/CascadeStrataEnum.lean::enum2BaseD`). It mirrors Python's id-keyed
  `candidates` dict at the CANDIDATE level, and leaves the edge-level question in item 6
  exactly where it was. Consequence for the ledger: **unmoved.** With the filter defeated
  as a control, one corpus moves — `direct_arm_exclusion`, `golden=[16, 1]
  observed=[31, 1]` — so the ledger does observe the leg; the widening is simply
  state-inert with the filter in place, on every in-fragment corpus. (It is the only
  corpus that could move: the other 22 are `ComputedOnly`, where
  `GraphIndex/CascadeStrataEnum.lean::enumJob2D_eq_enumJob2` makes the change an
  identity.) This also supersedes the E-chain plan's §D.6 expectation that Leg 2 would
  break the golden "by construction" — see that file's §C.2.

  **6. Still open, deliberately.** The faithful model fix is to mirror Python's
  presence diff — add a `¬ hasEdge` conjunct to `reconcileKeyDR`'s fold guard.
  Not attempted here: it ripples through `reconcileStarsKeyDR_edge_char`,
  `count_reconcileKeyDR_of_ne` and the settledness stack, and the filter-all
  removal was designed around the stacking. **Do NOT instead "fix" it by making
  `GraphIndex/Write.lean::GraphState.admitEdge` reject a present edge** — that is
  the tempting global version and it would break the untainted arm, where
  multiplicity is load-bearing and now checked (`nary_union` would go 3 → 1). A
  second, opposite untainted-arm divergence is recorded in
  `GraphIndex/RemoveOccCount.lean`'s header (the model's `rewriteClosure` does
  not dedupe where `RuleSet.apply` does, so on a reconvergent schema the model
  over-counts); ~~**no corpus exercises it today**~~ — measured, all 153 untainted
  comparisons agree — and the new untainted compare is exactly the check that
  would catch it if one ever did.

  **★★ CLOSED 2026-08-08 — the dedup LANDED and the divergence is gone.**
  `GraphIndex\RulesWrite.lean::rewriteClosure` is now
  `(rewriteClosureRaw S t).dedup`, mirroring `RuleSet.apply`'s `processed`
  worklist per stored tuple; `GraphIndex\RulesWrite.lean::rewriteClosureRaw`
  is the old body under its old name and
  `GraphIndex\RulesWrite.lean::mem_rewriteClosure_iff` is the bridge every
  membership-level consumer routes through. **Two corpora now exercise the
  shape** (`reconvergent_diamond`, `reconvergent_derived`), added in their own
  commit BEFORE the fix so the red was attributable; both now report
  `diff_states -> None`.
  Measured outcomes worth keeping:
  * The count stack needed **zero** proof rework, exactly as sized — 16 sites
    repaired (the pre-measured 15, plus `rewriteClosure_subset_restrict`, which
    consumed the definition through term-level defeq and so was invisible to a
    grep for the *tactic*; grep the identifier, not `unfold`).
  * **All 18 pre-existing derived-arm ledger rows are byte-identical**, because
    `.dedup` is the identity on a duplicate-free list. The change is surgical,
    and that was verified rather than assumed.
  * `nary_union`'s cross-tuple multiplicity **survives at 3** — the dedup is
    per-closure, never over the assembled edge list.
  * ★ Not predicted anywhere: the over-count was a real RUNTIME cost, not just a
    ledger inaccuracy. `reconvergent_derived` exceeded zcli's 120 s remove-stream
    budget before the fix and passes after it (derived-arm multiplicity
    `185 -> 52` at that corpus).
  * The self-contradiction that decided the adjudication is repaired in place:
    `GraphIndex/RemoveOccCount.lean`'s header now says the unit sentence was
    false when written and is true as of this leg, and its attack bullet is
    marked RESOLVED rather than deleted.

  *[The adjudication that produced the fix, retained.]*
  **★ ADJUDICATED 2026-08-08 — that second divergence is MODEL-side, and the
  disposition is to FIX THE MODEL (add a dedup to `rewriteClosure`), not to
  narrow a projection again.** Measured end-to-end through the real `zcli` for the
  first time: on `a := b or c ; b := d ; c := d ; d := [user]` with one write,
  `alice -> doc:d1#a` is `lean=2 python=1`, and `diff_states` emits the
  untainted-arm multiplicity line. **It is a UNIT divergence, not a retirement
  bug** — both sides retire correctly in a five-sequence add/remove battery, and
  answer parity is clean. Python counts LIVE RAW TUPLES; the model counts
  DERIVATION PATHS, which grows with schema shape (measured `1 → 2 → 4` for
  zero/one/two chained diamonds, fuel-stable).
  **Why model-side, decisively:** `GraphIndex/RemoveOccCount.lean`'s header
  *asserts Python's unit* — "`List.count (a,b)` IS the model's
  `direct_edge_count`" — and that sentence is FALSE on any reconvergent schema,
  while the same file's attack bullet already says so. The file contradicts
  itself and R3/R4's faithfulness claim rests on the wrong half (house rule 5).
  Fixing Python is not an option: its `processed` worklist dedup is the
  TERMINATION mechanism (`a: [user] or b ; b: a` compiles — only *derived* cycles
  raise — and would loop forever without it).
  **Why not the 2026-07-29 narrow-the-projection move that worked for the derived
  arm:** that was right *because* no honest edit made the derived arm green. Here
  `.dedup` matches Python element-for-element (verified on three schemas), and the
  count stack is **list-generic** (`count_removeLoggedRules` opens with
  `generalize rewriteClosure S t = us`), so `untOccCount`/R3/R4 need no proof
  rework. Narrowing again would also force the extractor to compute a
  path-weighted expectation — i.e. re-implement `rewriteClosure` in Python,
  destroying the harness's independence.
  **Sizing:** ~17 declarations — 15 mechanical `unfold rewriteClosure` sites via
  one `mem_rewriteClosure_iff` bridge, 2 list-equality sites; one session.
  ⚠ `List.dedup` keeps the LAST occurrence, so write order shifts; measured
  topological on the probes but not proved — first-occurrence dedup is the
  fallback. Full adjudication + corpus design + predicted red:
  `history/leaf-family-split-scope-2026-08-05.md` §10.5.

  *[Filed 2026-07-28, retained verbatim below.]*
  Found by the E-chain Leg-0 attack sweep (`history/PROOF_STATUS.md` 2026-07-28,
  probe D.1) while probing something else; it is **independent of that arc** and
  is recorded here on its own footing.
  **Mechanism (model side).** `GraphIndex/CascadeEnum.lean::edgeHolders` decodes
  the candidate set from the *existing* in-edges at the key, so every already-present
  copy is re-enumerated; `GraphIndex/CascadeStrata.lean::reconcileKeyDR` then folds
  `writeDirect` once per candidate; `GraphIndex/Write.lean::admitEdge` is
  `(a != b) && !reach b a` and does **not** reject an already-present `a→b`; and
  `GraphIndex/State.lean::addEdge` conses onto a `List`. Net: a derived edge's
  multiplicity **doubles per cascade leg** — measured `1 → 2 → 4 → 8` under the
  landed `enumJob2`. (Under the not-yet-landed `enumJob2D` it is `n ↦ 2n+1`,
  `1 → 3 → 7 → 15`, because `enum2BaseD` appends `storedDirectSubjects` without
  deduping — that half is an arc-local obligation, not a live divergence.)
  **Python side.** `index_v4/processor.py::DeltaProcessor._reconcile` builds both
  `candidates` and `audit` as `dict[int, NodeV4]`, keyed by node id — deduplicated
  by construction. So the counts genuinely differ.
  **Why no gate sees it.** `formal/conformance/extractor.py::lean_graph_state` and
  `::python_graph_state` accumulate edges into a `set` (projection **P3**), so the
  state gate compares edge *presence*, never *multiplicity*. This is the one
  projection where the usual "an argument recovers the dropped information"
  justification does **not** apply to a quantity the model actually varies.
  **Disposition: UNADJUDICATED, and deliberately not closed in the same pass that
  found it.** It is answer-benign as far as anything measured goes — `check` reads
  membership, not count, and every `check = sem` comparison run over this shape
  agreed — but "answer-benign" is exactly the class of claim this repo has had to
  retract before (the 2026-07-17 STATE-level divergence found in a situation
  previously dismissed as CHECK-level-safe). The two things it touches are
  `GraphIndex/RemoveOccCount.lean`'s occurrence-count invariant (verified to
  SURVIVE — `count_reconcileKeyDR_of_ne` is universally quantified over `cands`,
  and the D analogue of `enumJobs2At_Rnode_ne` was machine-checked) and the
  ref-counted edge representation the removal path depends on. **Open questions
  for whoever takes it:** does the model's multiplicity affect any *removal*
  sequence's drained state, and should P3 be upgraded to a multiset compare (which
  would make this fail loudly rather than be discovered by probe)?

  *[End of the 2026-07-28 filing. Both open questions are answered in the
  2026-07-29 verdict above: removal — no, by assembly (§4); multiset compare —
  yes on the untainted arm, golden-pinned on the derived arm (§5). A plain
  whole-set multiset compare was assessed and REJECTED: it goes red on 18 of 171
  edges for a declared model artifact, and no honest edit makes it green short of
  the §6 model change.]*

### 7.3 Load-bearing Python surfaces with NO Lean model (added 2026-07-26)

These were neither mapped nor declared. None is a bug; each is a place where an
auditor must know the pin is a Python↔Python differential, not a Lean twin.

* **★ The CROSSABLE-SHAPE class, and the Lean wildcard leg could not have caught the
  2026-08-09 bug (added 2026-08-09).** Python's bridged-in set is WIDER than Lean's.
  `zanzibar_utils_v1.py::SchemaInfo.bridged_in_shapes` folds in **star-tupleset
  through-shapes** — a `[S:*]` bare tupleset used by a TTU derives the through-shape
  `(S, target)` (`::wildcard_userset_restriction_shapes`'s docstring is where that
  distinction is drawn). Lean's in-bridge test
  `GraphIndex/UsStarWrite.lean::Schema.isSubjectWildcardUserset` keys on a **literal**
  `T:*#p` restriction only. Consequence:

  > Lean's crossable set (`bridgedInConcrete ∩ bridgedConcrete`) is exactly
  > wildcard-userset ∩ object-wildcard — precisely the set
  > `zanzibar_utils_v1.py::_reject_doubly_bridged_shapes` refuses at compile time. So
  > among admissible schemas Lean's crossable set is EMPTY, and the star-tupleset arm
  > where the divergence lived has **no Lean counterpart at all**.

  This is a fragment boundary, not model drift: nothing in `ObjStarWrite`/`UsStarWrite`
  became unfaithful when `index_v4/wildcard.py::WildcardIndex._ensure_bridges` grew its
  entity-middle half (`::WildcardIndex._ensure_entity_middles` / `::WildcardIndex._sync_entity_middles`, invariant
  **I14**), because the model never reached the shapes that half is about. Recorded
  because the *inference* an auditor would otherwise draw — "the wildcard write path has
  a Lean twin, so it is covered" — is false exactly where it mattered: the live
  under-report of 2026-08-09 (`docs/spec-deviations.md`) was invisible to the formal
  layer by construction, and was found by the Python hypothesis campaign instead.
  Closing it would mean modelling star-tupleset through-shapes in `UsStarWrite` — not
  scheduled, and no other claim depends on it.

* **★ The STAR TUPLESET PARENT on the derived read path (RC2, fixed 2026-08-11) — the
  graph chain excludes it by TWO standing hypotheses, so no Lean change is owed.**
  `index_v4/processor.py::DeltaProcessor.tupleset_parents` used to drop a stored `T:*`
  tupleset parent (`n.wildcard == ''`); it now splits the two subject shapes
  (`::DeltaProcessor._stored_tupleset_subjects`) and gives the star one the shape rule
  (`::DeltaProcessor.tupleset_star_types`, `::DeltaProcessor.derived_stored_star_types`)
  plus an ∃-expansion over instances, with the bulk twin in
  `index_v4/bulk_backfill.py::_BulkBackfill._stored_tupleset_subjects`. Neither half has a
  graph-side Lean counterpart, and the exclusions are explicit rather than accidental:

  > `GraphIndex/RulesBareStar.lean::TtuStarFree` fences out **every stored star-subject
  > tuple matching a TTU rewrite arm**, and `GraphIndex/RulesCorrect.lean::TtuTuplesetsDirect`
  > additionally requires every TTU's tupleset relation to be `directsOnly` — so a
  > *derived* tupleset relation, which is the whole of RC2's `tupleset-ttu` half, is not
  > expressible in the fragment at all. Both are carried as hypotheses on every
  > equivalence theorem in `Equiv.lean`.

  So nothing became dead code: `GraphIndex/RulesWrite.lean::applyRRule`'s `.ttu` case has
  no star arm and never claimed one.
  **★ The near-miss worth recording, stated carefully.** `TtuStarFree`'s own header
  records an attack-first `#eval` from 2026-07-11 on exactly this shape
  (`folder:* → doc:d6#parent`) finding `sem = true` against a rule-routed graph answer of
  `false` — the same *sign* as RC2's positive-TTU direction. That was a property of the
  LEAN write model (`writeRules` materialises no bridges at all) and is **not** evidence
  anyone had observed the Python defect: Python's UNTAINTED star-tupleset path was and is
  correct, via `index_v4/wildcard.py`'s materialised bridges, and is pinned green by
  `tests/test_ttu_tupleset_parent_types.py::test_rc2_positive_control_star_parent_on_untainted_tupleset`.
  What went unnoticed for four months is that the *derived* path reaches the same shape
  through the delta processor, which likewise materialises no bridge for it. **The
  transferable point: a shape fenced out of the model as "not covered here" is a standing
  hint about where the implementation is least watched** — the fence records where the
  easy argument fails, on both sides.

  **Direction of the fix: Python moved TOWARD the models, not away.**
  `_stored_tupleset_subjects`'s split is structurally
  `SetEngine/Eval.lean::parentMS` — star parent ⇒ `MemberSet.star (pt, targetRel)` unioned
  with the expansion over `instances` — and `Spec/Semantics.lean::ttuLeaf`'s `else` branch
  is the same rule. The `n.wildcard == ''` filter that was removed had no Lean counterpart
  on any side. This is the §8 "a correctness fix can also move Python toward the model"
  case, discharged here rather than in §8.1 because the region is fragment-excluded.

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
  * **`ZT-P5-NEW`** — `index_v4/wildcard.py::WildcardIndex._reject_star_self_edge`
    refuses a routed `w_any(T,p) → w_all(T,p)` edge when the shape lies in
    `bridged_in_shapes ∩ bridged_out_shapes`. That is a cycle **by construction**:
    bridges are schematic, not data-dependent, so every present *and future*
    concrete `T:x#p` closes `w_any → w_all → concrete → w_any`. This **narrows**
    graph WRITE admission into parity with the set engine's
    `setengine/engine.py::SetEngine._would_cycle` raw-level `u == v` rule — the
    same rule on the UNSPLIT node key. The divergence existed only because the
    graph's position-split wildcard encoding turns that self-loop into two
    distinct `node_v4` rows, so the core cycle check never fired; one
    `folder:* parent folder:*` write was graph-accepted / set-rejected and then
    detonated (every later innocent concrete grant permanently graph-rejected,
    oracle disagreeing, I1–I13 green). Pin:
    `tests/test_zt_p5_readjudication.py`.
    **Deliberately NOT a §3 `GraphAccepts` scope rejection.** A compile-time
    criterion cannot express it: the dangerous schema IS reg11's schema, so
    rejecting it would delete the legal reg11 / `owc_star_ttu` class. `GraphState
    .admitEdge` is untouched and the §3 row's claim stands as written.
    **Inert on every modeled fragment**, so no Lean definition describes dead
    code: `GraphIndex/UsStarWrite.lean::writeUsStar` states in its own header that
    on its (object-wildcard-free) fragment the out-bridges are inert, so no shape
    there is in `bridged_out`; `GraphIndex/ObjStarWrite.lean::writeWild` has no
    in-bridge step at all, so no shape there is in `bridged_in`; and
    `GraphIndex/UsStarWrite.lean::Schema.isSubjectWildcardUserset` explicitly scopes out the
    star-tupleset TTU through-shape this bug rides. The guard's precondition
    `bridged_in ∩ bridged_out ≠ ∅` is therefore unsatisfiable in both fragments.
  * **`ZT-P4-7`** — `zanzibar_utils_v1.py::AdmissionRejected` (a `ValueError`
    subclass, re-exported from `index_v4/core.py` and the `index_v4` package)
    now types the ~20 genuine write-admission REFUSAL sites across
    `index_v4/core.py`, `index_v4/wildcard.py`, `zanzibar_utils_v1.py` and
    `setengine/engine.py`, so a refusal is distinguishable from an internal
    `ValueError`. Same disposition as `ZT-P1-2` and for the same stated reason:
    `GraphIndex/Write.lean::GraphState.admitEdge` is a **decision procedure** —
    it says which writes are accepted, not by which Python statement form a
    rejection is raised. **No admission decision changed**, proved rather than
    asserted: an 854-entry probe (5 schemas × 29 writes × 5 drivers plus the raw
    `ReachabilityIndex` path) recording per-write accept/reject and the EXACT
    message but deliberately NOT the exception class was re-run against a tree
    with the rename mechanically inverted — 0 differences over 608 rejections /
    246 accepts / 58 distinct messages. The gate value is downstream:
    `formal/conformance/backends.py::GraphDriver.apply` no longer allow-lists
    exception MESSAGE SUBSTRINGS (`_ADMISSION_REJECTION_MARKERS` deleted); an
    unclassified `ValueError` now propagates and fails the comparison instead of
    being absorbed as "rejected", which had let a spurious raise silently shrink
    BOTH the driven store and the oracle built from it.
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

## 9. The mechanical anchor check (LANDED 2026-07-27 — this section is now its spec)

**Status: IMPLEMENTED** as `formal/conformance/anchor_check.py`, wired into
`formal/verify.sh`'s `lean` phase as step 4c (~1 s, no Lean toolchain, no imports).
When measured on 2026-07-29 it parsed **397 anchors (272 Python + 125 Lean), 0
unresolved**, with floors `MIN_PY_ANCHORS = 250` / `MIN_LEAN_ANCHORS = 100` (the live
tally is printed by every gate run and echoed in `FINAL_REVIEW.md`'s generated counts
block). It found two live defects
when first run: `Schema.isSubjectWildcardUserset` was anchored to `Core/Schema.lean`
when it is declared in `GraphIndex/UsStarWrite.lean` (fixed), and the `_fan_out` /
`reconcileResidueKey` rows were verified to fail loudly under a simulated rename.
The subsections below are the spec it was built to; two deltas from the design as
written: (a) the bare <code>&#58;&#58;Symbol</code> continuation also inherits a **plain** backticked
file mention (`` `index_v4/processor.py` ``), which §8's prose bullets rely on, and
the inheritance scope resets at each list item, not only at blank lines; (b) Lean
names are matched on any dotted SUFFIX of the namespace-qualified declaration, since
`def GraphState.foo` inside `namespace Zanzibar` and `def foo` inside `namespace
Zanzibar.GraphState` are both legitimately anchored `GraphState.foo`.

**Original proposal text follows.** This section exists because §0's premise — "no manually-maintained line
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
