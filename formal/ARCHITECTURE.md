# ARCHITECTURE.md — the formal-verification development, by subject

This is the durable, topical map of the Lean 4 formal development: the trust root, the
two backend models, the theorems and their scopes, how the Python code is pinned to the
models, and the honest residual surface. It is organized by **subject**, not by the
timeline in which the work was done. Stage names from that timeline (`W1`…`W4`,
`T0`…`T6`, dated session tags) appear only where explicitly labelled *(historical
staging — see `history/`)*; the `T`-labels are the durable theorem IDs and do survive.

**Companion docs.** [`SEMANTICS.md`](./SEMANTICS.md) is the human-readable spec (the
trust root). [`CORRESPONDENCE.md`](./CORRESPONDENCE.md) is the Lean-def ↔ Python-file:line
map. [`FINAL_REVIEW.md`](./FINAL_REVIEW.md) is the authoritative, clause-checked claim.
[`HANDOFF.md`](./HANDOFF.md) is the state-of-the-world entry point. The provenance
archive — the session ledger, the staged-widening designs, and the early digest — lives
under [`history/`](./history/README.md).

---

## 1. What this proves (and what it does not)

The set-engine and graph-index **algorithms**, as modeled in Lean at the level of
`CORRESPONDENCE.md`, are **proven** to compute the stratified-Datalog¬ Zanzibar
semantics `sem`, and hence to be equivalent — machine-checked and axiom-audited. The
set-engine result holds at **full scope**; the graph-index result holds at a
**documented fragment** (`GraphAdmission ∧ W4Fragment`), not everything the Python code
admits. The **Python implementations** are pinned to those models empirically: by the
`CORRESPONDENCE.md` structural review, by five-corner differential conformance including
state-level equality under six documented projections, and by exhaustive small-scope
enumeration up to tiny documented bounds. `FINAL_REVIEW.md` is the exact clause-by-clause
statement and governs; nothing in this document may claim more than it does.

**This never rounds up.** "The algorithms are proven" is not "the code is formally
verified": the interner/bitmap layer, the SQL/transaction/concurrency layer, the
compiler artifacts, the fragment carries, and the fidelity of the model-to-code
correspondence itself are all unverified surface (§6).

---

## 2. The trust root — the specification `sem`

Everything downstream is proved **about `sem`**, the executable stratified perfect-model
evaluator defined in `SEMANTICS.md` and Lean's `Spec/` + `Core/`. `sem` is transcribed
from the repository's **independent oracle** (`tests/oracle.py`), which shares no code
with either backend — so the conformance triangle (spec · oracle · backend) has three
genuinely independent corners and one parser bug cannot corrupt two of them.

- **Domain** (`Core/`): schema AST (`Expr`/`Schema`, binary `union`/`inter` left-folded
  from the n-ary DSL), tuples/queries (`Refs.lean`), the store and its query universe
  (`Store.lean`), opaque valid identifiers (`Ident.lean`).
- **The store as a Datalog¬ program** (`SEMANTICS.md` §3): each `(schema, store)` denotes
  a stratified Datalog-with-negation program; `sem` is its perfect model.
- **Well-formedness** `WF S` (`Core/Schema.lean`, §4.2) and **stratifiability**
  `Stratifiable S` (`Spec/Stratify.lean`, §4.4): the verified envelope. Non-stratifiable
  schemas are rejected upstream and out of scope.
- **The evaluator** (`Spec/Semantics.lean`): `directLeaf` (star + userset branches),
  `ttuLeaf` (stored-parent TTU — TTU parents are STORED tupleset tuples, never computed
  membership), boolean composition, and `evalE`/`sem` — a **fuel-bounded primitive
  recursion** mirroring the oracle's depth-bounded provisional-false recursion. Faithful
  and total.

Two well-definedness theorems anchor the root, both full-scope, sorry-free, axiom-audited:

- **T0a** `sem_fuel_stable` (`Spec/WellDef.lean`): over declared stores (`StoreDeclared`)
  and stratifiable schemas, the evaluator is **fuel-stable** — for any fuel `≥ fuelBound
  S T`, `semAux … = sem S T q`. (`StoreDeclared` is load-bearing, not decoration: without
  it the statement is machine-checked FALSE — `Spec/Counterexample.lean`. There is no
  separate relational `Sem`; the Phase-0 "relational ≡ executable" form was never built.)
- **T0b** `stratify_none_iff_cycle` / `stratify_topological` (`Spec/WellDef.lean`):
  `stratify` fails **exactly** on a derived-dependency cycle, and on success the stratum
  assignment is topological.

---

## 3. The two backend models

Both models are **concrete Lean definitions** (not opaque postulates), each mapped to a
Python module by `CORRESPONDENCE.md`.

### 3.1 The set-engine model (`SetEngine/`)

The star-closed `MemberSet` algebra (`pos`/`stars`/`neg`, `MemberSet.lean`) plus
on-the-fly expansion (`expandDirect`, `expandTtu`, `SetEngineModel.check` in `Eval.lean`).
It stores raw tuples and computes memberships on demand with set algebra — the model of
`setengine/`. No materialized closure.

### 3.2 The operational graph-index model (`GraphIndex/`, `FullScope.lean`)

A concrete state machine `GraphState` (nodes / path-counted closure edges / residues /
outbox / watermark, `State.lean`) with reads via `GraphModel.check` (route by
`isDerived`; ≤ 4 probes for untainted, edge-probe + `stars`∖`neg` / `upos` residue for
derived). The model of `index_v4/`.

The load-bearing object is the **operational closure** `ReachedBy` (`:=
ReachedByW3d2E`, `FullScope.lean` / `CascadeStrataAssemble.lean`) — the set of states
reachable from empty by the **synchronous v1 Python write path**, modeled as a chain of:

> admitted logged **rule-routed writes** → the **reconcile diffing pass** (stale-edge
> retraction + residue recompute) → the **per-stratum two-round cascade** over the
> outbox → **drain** to quiescence,

interleaved as Python interleaves them (`connectedstore.advance_index` →
`DeltaProcessor.run_cascade`). The chain is **add-only** by construction: it has no
remove legs (a property of the chain, not a hypothesis). `CORRESPONDENCE.md` §4–6 maps
every step (`reconcileStarsKeyD`, `graphRecR`/`checkFnR`, `affectedKeys`, `runCascade2`)
to `processor.py` line ranges.

---

## 4. The theorem structure

All theorems are in `formal/lean/ZanzibarProofs/`, all **sorry-free**, all
**axiom-audited** (each depends only on `[propext, Classical.choice, Quot.sound]`). They
quantify over a schema `S`, a finite store `T`, and a query `q`.

| topic | ID | Lean name (file) | scope |
|---|---|---|---|
| well-definedness | T0a | `sem_fuel_stable` (`Spec/WellDef.lean`) | full |
| well-definedness | T0b | `stratify_none_iff_cycle` / `stratify_topological` (`Spec/WellDef.lean`) | full |
| set-engine correctness | T1 | `setEngine_correct` (`SetEngine/Correct.lean`) | **full** |
| graph invariant | T2a | `graph_reached_inv` (`FullScope.lean`) | GraphAdmission ∧ W4Fragment |
| graph correctness | T2b | `graph_correct` (`FullScope.lean`) | GraphAdmission ∧ W4Fragment, drained |
| backend equivalence | T3 | `backend_equivalence` (`FullScope.lean`) | = T2b |
| path-count maintenance | T4 | `pathCount_addEdge` / `pathCount_removeEdge` (`GraphIndex/Closure.lean`) | full (acyclic) |
| cascade termination | T5 | `runCascade2_no_abort` / `cascade2_drains` (`GraphIndex/CascadeStrata.lean`) | ≤ 2 strata |
| security: exclusion | T6a | `exclusion_effective` (`FullScope.lean`) | = T2b |
| security: no ghost grant | T6b | `no_ghost_grant` (`FullScope.lean`) | = T2b |
| security: wildcard scoping | T6c | `wildcard_scoping` (`Equiv.lean`) | full |

What each says, in English:

- **T1** — for every WF, stratifiable schema and identifier-valid store, the set-engine
  model's `check` equals `sem`. Full scope. (The three hypotheses are retained to match
  the equivalence route but the equality is unconditional.)
- **T2a** — the 8-clause graph invariant `Inv` (structural I1–I3 + the four I6
  residue-hygiene clauses) holds at **every** operationally-reached state — dirty keys
  and mid-drain included. (There is **no** `materialized = materialize …` state-equality
  theorem; state-level agreement is pinned empirically, §5.)
- **T2b** — at every **fully drained** reached state, `GraphModel.check σ q = sem S T q`,
  for derived and untainted queries with a concrete object and bare-predicate star
  subjects.
- **T3** — `SetEngineModel.check S T q = GraphModel.check σ q` (T1 ∘ T2b, transitivity
  through `sem`; same scope as T2b, never wider).
- **T4** — under acyclicity, adding/removing one direct edge preserves the path count
  `p = #paths` (the counting theorem — the basis of exact reference-counted removal).
- **T5** — the two-round cascade drains every dirty key; the scheduler's abort branch is
  provably **dead** at ≤ 2 derived strata (and provably **live** at 3 — attack-confirmed,
  which is exactly why `twoStrata` is an honest carry, below).
- **T6a/T6b/T6c** — real exclusion content (a subject removed by a `but not` operand is
  denied by both backends, incl. under a `T:*` grant); no stale edge/residue survives a
  drain to grant a `sem`-false query; a `T:*` grant never leaks across subject types.

### 4.1 The graph-side scope split — two bundles, by provenance

The graph theorems (T2a/T2b/T3/T6a/T6b) carry two hypothesis bundles, split by where the
restriction comes from (`FullScope.lean`):

- **`GraphAdmission S T`** — the **Python-admission mirror**: what the Python compiler +
  write admission already guarantee for every accepted schema/store. Fields (each
  docstring cites the enforcing Python mechanism): `wf`, `nodup`, `strat`, `ttuDirect`
  (untainted TTU tuplesets direct-only), `matchDecl`, `ranked`, `objWild` (object-wildcard
  shapes never on derived relations), `storeValid`. This bundle imposes **nothing Python
  does not already impose**.
- **`W4Fragment S T`** — the **honest carries**: scope restrictions the current proof
  needs that Python admission does **not** imply. Fields: `rootB` (derived defs
  boolean-ROOTED — Python taints through `union`/`computed` roots too), `computedOnly`
  (derived defs read only computed operands), `twoStrata` (≤ 2 derived strata —
  attack-confirmed load-bearing), `wsBare` (declared wildcard restrictions all bare
  `[T:*]`), `bareStar` (stored star subjects bare, objects concrete), `ttuStarFree` (no
  stored star subject feeds a TTU tupleset), `term` (derived relations never TTU targets
  nor stored userset-subject predicates). Every field is a documented gap (§6).

`w4_within_scope` (`FullScope.lean`) proves `GraphAdmission ∧ W4Fragment → GraphAccepts`
— the proved fragment sits **inside** the decision-15 accepted class. The converse is
false: `GraphAccepts` admits schemas outside `W4Fragment`, and no theorem covers that
surplus. **Non-vacuity**: `W4Witness` machine-checks that both bundles are inhabited by a
real compiled boolean schema, so the final theorems are not vacuous. (Honesty caveat,
per `FINAL_REVIEW.md` §2: what is kernel-checked is inhabitation of the hypothesis
*bundles*; joint inhabitation of a drained, non-trivially-reached state is demonstrated
empirically via the conformance driver plus the proved `cascade2_drains`, not as a single
kernel-checked term.)

The final theorems are **unsuffixed** in `FullScope.lean`; the pure-direct starter
versions survive under `*_direct` names *(historical staging — the W1→W4 widening, see
`history/`)*.

---

## 5. Pinning the Python to the models

The theorems are about the Lean models. The tie to Python is the `CORRESPONDENCE.md`
review plus the **conformance harness** (`formal/conformance/`), gated by the
one-command `formal/verify.sh`. The gate is **fail-closed** and currently green:

> `lake build` + **0 sorries** (`formal/conformance/sorry_scan.py`) + `zcli` preflight +
> **axiom audit** (412 observed reports = 412 `#print axioms` commands, exactly one per
> command, only `[propext, Classical.choice, Quot.sound]`) + **214 conformance tests, 0
> skips** (the conformance step fails on any skipped test or zero passes).

Because the Lean spec is executable, the same artifact is both proof subject and the CLI
oracle `zcli`. The 214 tests are **194 differential-conformance comparisons** (the seven
items below) plus **20 gate-tooling unit tests** (not Lean-vs-Python comparisons: 13 for
the sorry-scanner, `test_sorry_scan.py`; 7 for the zcli-runner transient-init retry,
`test_runner_retry.py`). The 194 break down as:

- **Answer conformance — the five corners.** Over a shared query grid, `check` verdicts
  are compared five ways: Lean `sem` (zcli) × the independent oracle × the real
  `SetEngine` × the Lean **operational graph model** (zcli mode `"graph"`) × the real
  Python `WildcardIndex`+`DeltaProcessor`. The Lean graph model's verdicts are covered by
  T2b *by proof, not analogy*: `Exec.lean`'s driver folds the `ReachedBy` constructors
  (`graphRun_reached`), its runtime gates decide the theorem's side conditions
  (`foldAdmitsB_iff`, `drainedB_iff`), and under the W4 bundles every printed verdict is
  `sem` (`graphRun_check_eq_sem`). Suites: `test_conformance_spec.py` (all 17 corpora),
  `test_conformance_random.py` (25-seed randomized substores), `test_conformance_graph.py`
  (the 15 in-fragment corpora, incl. two designed attack corpora — stale-edge cross-stratum
  re-settle, star churn over two strata).
- **The shared grid** (`formal/conformance/grid.py`): targets are the stored-tuple cross
  product **plus** every schema-**DECLARED** `(type, relation)` unioned type-aware — so
  derived/boolean roots are queried on every corpus (previously derived-only boolean roots
  went unqueried and that evidence was vacuous exactly there); subjects include bounded
  userset-shaped subjects. The concrete-named userset queries sit inside the proved graph
  query scope (`hqs` constrains only star-NAMED subjects).
- **Mode-dispatch fail-closure** (`test_cli_mode.py`): an unknown / non-string zcli
  `"mode"` returns rc 4 (rc enumeration: 0 answers-or-state / 1 usage-parse / 2 admission
  / 3 not-drained / 4 unknown mode), so spec answers can never masquerade as graph answers.
- **State-level graph conformance** (`test_conformance_state.py`, **15 corpora**): the
  Lean graph model's FINAL MATERIALIZED STATE (zcli mode `"graph-state"` — same
  `graphRun` fold, same admission/drain gates, emitting canonical direct edges + residue
  triples) is diffed against the real Python graph index's final SQL state
  (`EdgeV4`/`ResidueV1` decoded through `NodeV4`). Compared under **six documented
  projections** P1–P6, each justified in `formal/conformance/extractor.py`: P1 closure
  rows (a function of the direct set), P2 wildcard bridges (currently inert), P3 edge
  multiplicity, P4 all-empty residue rows, P5 node GC, P6 leaf-family closure-leaf copies
  (evaluation output compared exactly). Attack-first: the gate's first run FOUND the P6
  divergence under full check-parity; a deliberately corrupted extraction fails with the
  symmetric-difference message.
- **Exhaustive small-scope enumeration** (`test_conformance_enum.py`): ALL stores of ≤ 3
  tuples over a 2-names-per-type pool, for four representative fragment shapes —
  boolean_exclusion (93 stores), boolean_intersection (93), two_stratum_cascade (299),
  boolean_star_exclusion (42); **527 stores total, counts asserted** so the bounds cannot
  silently drift. spec × oracle × set engine over the shared grid; zero disagreements. The
  graph backend is deliberately not enumerated (it stays pinned by the curated-corpora
  graph + state gates), and the bounds are deliberately tiny.
- **Remove-path conformance** (`test_conformance_remove.py`, 34 tests, 2026-07-12): the
  REAL `SetEngine` driven through seeded interleaved add/remove/re-add sequences (all 17
  spec-scope corpora × 5 seeds) equals `sem` (zcli) × the oracle on the FINAL store — the
  first ANSWER-LEVEL pin on Python's remove path — plus two Python-internal convergence
  pins: the driven engine equals a fresh `rebuild()` over the grid AND at id-free
  state-fingerprint granularity (interner keys/refcounts, population masks,
  node_sets/member_of, flow-graph edges), and a full add-all/remove-all/re-add churn test
  asserts complete state emptiness mid-cycle. Scope honesty: spec × oracle × set engine
  only — the Lean chain stays add-only, the GRAPH-side remove legs remain open (§6), and
  the fingerprint comparison is driven-vs-rebuild Python-internal, never vs Lean.
- **Generated-schema conformance** (`test_conformance_generated.py`, 40 tests,
  2026-07-12): a seeded deterministic re-implementation of the hypothesis `schema_asts`
  generator (NO hypothesis dependency — the formal/ convention; inside
  `formal/conformance/` so `verify.sh` gates it fail-closed) produces schemas + stores
  OUTSIDE the 17 curated corpora, asserting zcli `sem` == oracle == real `SetEngine` over
  the shared grid. This closes the disjoint-pools gap — a `sem`/model-fidelity divergence
  on non-curated schema shapes was previously invisible to every gate (§6 item 1).
  Answer-level, spec-side only; the graph backend stays pinned by the curated corpora.

Separately, the repository-wide **validation matrix** (`tests/test_matrix.py`) pins
Python-graph × Python-set × oracle on every push, and the **compiled-RuleSet snapshot
tests** (`tests/snapshots/`, `tests/test_compile_snapshot.py`) are the byte-identity gate
on untainted compilation — the pin on the compiler artifacts the Lean model does not
cover (§6). The **lookup-surface oracle gate** (`tests/test_lookup_oracle.py`,
2026-07-12) pins `lookup`/`lookup_reverse`/`expand` on both Python backends by composing
`oracle.check` into brute-force reference lookups; the four genuine divergences it found
(X1–X4) were fixed 2026-07-13 Python-side and stand as plain regression pins (§6 note,
`docs/spec-deviations.md` 2026-07-13).

---

## 6. Honest scope + residual unverified surface

Mirroring `FINAL_REVIEW.md` §3/§4. The current honest claim is §1's, with **one explicit
subtraction and two scope qualifiers**: the graph-side theorems hold at `W4Fragment`
scope (not everything Python admits); state-level equality holds under the six documented
projections (a divergence *inside* a projected class is pinned elsewhere, not here);
enumeration is exhaustive only up to its tiny documented bounds. Never round these up.

The residual unverified surface, in full:

1. **Model-to-code fidelity itself** — the theorems are about the Lean models; the tie to
   Python is `CORRESPONDENCE.md` + empirical conformance. A Python behavior outside the
   corpora/grids could diverge without failing the gate. *Narrowed 2026-07-12:* the
   schema-SHAPE half of this risk is closed at answer level, spec-side, by the
   generated-schema gate (`test_conformance_generated.py`, §5); behaviors outside the
   generated envelope, and the graph backend on non-curated shapes, remain unpinned.
2. **The Python COMPILER artifacts are trusted, not modeled** — `compile_ruleset`'s taint
   computation, strata assignment, derived-predicate plans, fan-out tables, and
   leaf-family routing have no Lean counterpart (the Lean model reads the RAW boolean defs
   and derives taint/strata/jobs itself). Pinned by the snapshot tests + the conformance
   corpora; a compiler bug on an unexercised shape would not fail any Lean gate.
3. **Fragment carries** — the `W4Fragment` gaps (§4.1): > 2 derived strata; non-root
   booleans (union/computed-rooted taint); `PDerivedTTU`/`PDerivedUserset` plan leaves;
   declared wildcard-userset restrictions anywhere; stored object-wildcard tuples; stored
   userset-star tuples; **removes** (the chain is add-only — the Python SET-ENGINE remove
   path is now pinned at answer level + rebuild state-fingerprint by
   `test_conformance_remove.py`; the Lean remove legs and the graph-side remove path stay
   open); star-subject queries with non-bare predicates; star-object queries on the graph
   side. *(Empirical note: the union-rooted-taint and object-wildcard corpora were probed
   anyway — zero check-level divergence observed; the exclusions are proof-scope, not
   known disagreements. Inside the `PDerivedTTU` gap a REAL check-level divergence WAS
   found (2026-07-12, by `tests/test_lookup_oracle.py`: the graph index answered False
   on userset-shaped subjects flowing through a stored tupleset parent of a derived TTU
   where the oracle and both set engines answer True) and FIXED 2026-07-13 Python-side
   (processor from-chain rule + `upos` lift; xfails flipped to regression pins, matrix
   grids widened) — the shape stays outside `W4Fragment` (`computedOnly` bans `ttu`
   leaves in derived defs), so the theorems and the `formal/` gates were and remain
   untouched; see `FINAL_REVIEW.md` §3's resolved note and `docs/spec-deviations.md`
   2026-07-13.)*
4. **The state-gate projections** — state-level conformance IS implemented, but a
   divergence strictly inside a projected class (P6 leaf-family edge content, P3 edge
   multiplicity, P2 bridge edges, P5 node GC) would not fail it; each is pinned elsewhere
   and documented in `extractor.py`. Two artifacts sit outside the canonical form
   entirely: the `EdgeV4.derived` flag and the outbox rows/watermark (drained-ness is
   gated as a boolean, not row equality) — pinned only by Python-internal I5/I10 + the
   §8.3 verifier, never against Lean.
5. **The representation layers** — interner/bitmap (`setengine`), SQL rows / ref-counted
   closure storage (`index_v4`), sessions/transactions/concurrency (`_lock_store`),
   `rebuild()` / crash recovery.
6. **Non-stratifiable schemas** (rejected upstream; the model assumes stratifiability) and
   the `expand` / `lookup` / `list-objects` read surfaces.
7. **The toolchain trust base** — the Lean 4 kernel + pinned Mathlib, and the conformance
   harness's own encoder (`encode.py` reuses the independent oracle's parser precisely so
   one parser bug cannot corrupt both sides).

**Where the next marginal assurance is** (`FINAL_REVIEW.md` §4; state-level + enumeration
+ the remove-path and generated-schema answer gates are DONE): (c) widening `W4Fragment`
(union roots first — the probe suggests the model is already faithful there and only the
proof is missing); (d) remove legs on the Lean side and the graph backend (the diffing
pass models retraction but the chain is add-only; the set engine's remove path is now
pinned, the graph's is not); (e) widening the state/enumeration bounds (graph backend in
the enumeration, k = 4, a userset/TTU shape, state gate over enumerated stores). Item
(f) — fixing the derived-TTU userset-subject divergence and flipping its strict xfails —
is **DONE** (2026-07-13, Python-side; `FINAL_REVIEW.md` §3's resolved note).

---

## 7. Map of the `formal/` tree

```
formal/
  ARCHITECTURE.md    -- this file: the durable topical map
  SEMANTICS.md       -- the trust root: sem, WF, both models, theorem hypotheses
  CORRESPONDENCE.md  -- Lean def <-> Python file:line map (the audit backbone)
  FINAL_REVIEW.md    -- the authoritative, clause-checked claim (governs)
  HANDOFF.md         -- state-of-the-world entry point + house rules + build/verify
  README.md          -- one-page orientation
  REFERENCES.md      -- external references
  verify.sh          -- the one-command fail-closed green gate
  history/           -- provenance archive (ledger, staged designs, early digest)
                        PROOF_STATUS.md · ROADMAP.md · REVIEW.md · README.md
  lean/ZanzibarProofs/
    Core/            -- domain: Ident, Refs, Schema, Store
    Spec/            -- sem + well-definedness: Semantics, Stratify, WellDef (T0),
                        Confine, Stabilize, FuelStable, Counterexample
    SetEngine/       -- the set-engine model + T1: MemberSet, Algebra, Eval, Correct
    GraphIndex/      -- the operational graph model + T2/T4/T5: State, Closure (T4),
                        Cascade/CascadeStrata* (T5 + the two-round scheduler),
                        Reconcile*/Rules* (the staged write/read layers),
                        Exec (the conformance driver honesty theorems)
    FullScope.lean   -- the final unsuffixed T2a/T2b/T3/T6 over ReachedBy; the
                        GraphAdmission / W4Fragment split; non-vacuity witnesses
    Equiv.lean       -- T3/T6 corollaries (incl. T6c wildcard_scoping)
    Audit.lean       -- the #print-axioms audit surface
    Cli.lean         -- the zcli JSON conformance endpoint (modes: spec/graph/graph-state)
  conformance/       -- the pytest harness: encode, grid, corpus, backends, extractor,
                        runner, sorry_scan, and the test_conformance_*/test_cli_mode suites
```

---

## 8. The attack-first method

The effort ran under a hard, owner-adjudicated **honesty norm**: never fake a proof,
never postulate the thing being proved (no `check := sem` models, no
invariant-as-postcondition), never edit a golden/oracle/snapshot to make something pass,
and never round scope up. Where a doc and the code disagree on a name, the code wins.

Its central discipline was **attack-first**: before proving any new theorem *statement*,
try to REFUTE it with concrete `#eval` scenarios against the real `check`/`sem`. Six
false statements were killed this way before any proof effort was spent on them
*(historical staging — the stage names are explained in `history/`)*:

1. **additive `fuelBound`** — the recursion depth is bounded by the `(entity × relation)`
   state space, a **product**, not a sum. The additive bound `|keys| + 2|T| + 4` cut deep
   TTU-linked chains off early, so `sem` returned **false** where the oracle returns
   **true** (depth ~64 at a shallow-looking schema). Fixed to the multiplicative
   `|keys| · (2|T| + 4)` — the load-bearing sizing rationale, and the original reason the
   "validate before proving" phase exists.
2. **abstract write-step closure** — the abstract reached-state closure admitted junk
   states; the graph theorems were re-proved over the concrete operational chain instead.
3. **T0a without `StoreDeclared`** — an admission-invalid tupleset tuple closes a
   consultation cycle stratification never sees, and `semAux` oscillates; T0a is false
   without the declared-store precondition (`Spec/Counterexample.lean`).
4. **the naive-W2 TTU fragment** — the first TTU fragment shape was refuted before proving.
5. **the W3a single-edge collapse without `NoRuleOutputs`** — the collapse fails unless
   the derived key emits no rule outputs.
6. **W3d-2 "round-1 keys are stratum-1"** — false: a write to a direct untainted leaf of a
   stratum-2 def dirties it at the watermark, where the leg-start enumeration misses a
   fresh grant living only in the dirty operand's future residue. The two-round coverage
   was made conditional on the job's operand baseline and discharged from state instead.

A session that killed a false statement was a good session. Each kill is recorded in the
`history/PROOF_STATUS.md` ledger; none of the six was quietly reconciled, and no
adjudication event (spec vs oracle vs backend disagreement) remains open.
