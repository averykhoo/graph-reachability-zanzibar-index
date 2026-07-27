# Widening the Lean operational graph model beyond TWO cascade rounds — an executable plan

**Status:** DESIGN ONLY. Nothing in `formal/lean/**` was touched producing this
document. The tree was green throughout (`verify.sh lean PASSED`, audits 457,
holes 0 — command in §5).

**Predecessor:** [`nary-strata-coverage-2026-07-27.md`](nary-strata-coverage-2026-07-27.md)
§2/§5, which recorded the gap in one line ("needs a `runCascadeN` plus a re-proof
of the whole W3d-2 layer, multi-session"). This document turns that into an
inventory, a shape decision, legs, and a cost/value call — and **contradicts the
predecessor on two points of fact** (§0).

Every claim about the Lean tree below comes from a command that was run. The
command is quoted at the point of use. Where a claim is *argued* rather than
*measured*, it is marked **[ARGUED]**; where it is unknown, **[UNKNOWN]**.

---

## 0. Three findings that change the picture before you read the plan

### 0.1 Python does NOT loop to quiescence. It runs `len(strata)` rounds.

```
grep -n "def _run_cascade" -A 45 index_v4/processor.py
```

```python
def _run_cascade(self, txn_start_watermark: int) -> None:
    self.session.flush()
    frontier_start = txn_start_watermark
    rounds = len(self.compiled.strata)          # <-- the round count
    for _ in range(rounds):
        rows = outbox_rows(self.session, self.store_id, frontier_start)
        frontier_start = max((r.id for r in rows), default=frontier_start)
        keys = self._map_deltas_to_keys(rows)
        ...
        if not keys:
            break
    # quiescence (§5.1): stratification guarantees the cascade drains
    rows = outbox_rows(self.session, self.store_id, frontier_start)
    leftover = self._map_deltas_to_keys(rows)
    ...
    if leftover:
        raise InvariantViolation(...)
```

So the honest correspondence statement is **not** "Python iterates to a fixpoint
and Lean truncates at 2". It is:

> Python's cascade is a **fixed `N`-round loop with `N = len(compiled.strata)`,
> plus a runtime quiescence assertion**. Lean's `runCascade2` is *that same
> algorithm instantiated at `N = 2`* — the count is a literal in the Lean term
> rather than a parameter read off the schema.

That is a much better position than a fixpoint-vs-fixed-count mismatch would be:
the Lean model is the **N=2 slice of the real algorithm**, not a different
algorithm. It also kills the fuel/quiescence formulation as the *faithful* choice
(§2.3) — a fuel formulation would model something Python does not do.

The early `break` on `not keys` is unmodelled but inert: it exits a loop whose
remaining iterations would read an empty frontier. **[ARGUED]**

### 0.2 The Lean model at ≥3 strata FAILS CLOSED (measured rc 3), it does not answer wrongly.

The predecessor said putting a 3-stratum corpus into `GRAPH_FRAGMENT` "would
**not** fail loudly", because `Cli.lean` gates only on write admission (rc 2) and
drained-ness (rc 3), never on `W4Fragment`. The first half of that reasoning is
right; the conclusion is wrong **for this particular gap**, because the round-2
reject leaves the state *undrained*, which is exactly what rc 3 tests.

Measured (repo root, repo conda interpreter, zcli built by the `lean` phase):

```
python - <<'EOF'   # builds the shared grid, restricted to hqo, and invokes zcli
from formal.conformance.corpus import MULTI_STRATUM_SCHEMAS, SCHEMAS
from formal.conformance.encode import build_request
from formal.conformance.runner import invoke_zcli
from formal.conformance.grid import grid
... build_request(schema_text, tuples, queries, obj_wild, mode=mode) ...
EOF
```

```
three_strata_chain queries: 161
=== mode=spec  rc=0     [false,false,...]                       (161 answers)
=== mode=graph rc=3     stderr: graph mode: final state not drained
                                (outside the proved read scope)
=== CONTROL two_stratum_cascade graph rc=0
```

**Consequence for this arc.** There is no soundness exposure being carried at ≥3
strata: the operational model *refuses to answer*. `runCascade2` returns the
pre-state (`CascadeStrata.lean:380-389`, the `else σ` branch), so `cascadeKeys ≠
[]`, so `drainedB` is false, so `Cli.lean:293-296` exits 3. This arc therefore
buys **coverage**, not **safety**. It also means the wall is *visible* — a future
author who adds a 3-stratum corpus to `GRAPH_FRAGMENT` gets a red test with a
comprehensible message, not a silent bad comparison. (Contrast
`direct_arm_exclusion`, the ZT-P3-3 case, where the model *did* answer.)

### 0.3 The headline STATEMENT pin cannot see this widening.

```
grep -n "graph_correct" formal/headline_statements.txt
```

```
Zanzibar.graph_correct	{S : Schema} {T : Store} {σ : GraphState} (q : Query)
  (hA : GraphAdmission S T) (hF : W4Fragment S T) (h : ReachedBy σ S T)
  (hq : Drained S σ) (hqs : ...) (hqo : ...) : GraphModel.check σ q = sem S T q
```

The pin records `(hF : W4Fragment S T)` **by name**. Weakening, renaming, or
deleting `W4Fragment.twoStrata` changes what `graph_correct` *claims* while
leaving this line byte-identical. `verify.sh` step 4b therefore **will not fire**
on the most important change this arc makes. The audit-identity pin (4a) won't
either — it pins names, and no name changes.

**This is a gate blind spot and it must be handled explicitly in the plan** (Leg
0 / Leg 6, §3). It is also worth reporting to whoever owns `verify.sh`
independently of whether this arc is ever executed: the same hole exists for
`GraphAdmission`, and for every other structure-valued hypothesis in the 26
pinned statements.

---

## 1. Inventory of the two-round assumption

### 1.1 Method

Two mechanical passes over `formal/lean/ZanzibarProofs/**` (scripts in the session
scratchpad, not committed):

1. Split each `.lean` file into top-level declarations by a regex on
   `^(@[...])?(private|protected|noncomputable|partial)* (theorem|lemma|def|inductive|structure|abbrev|instance) NAME`.
2. For each declaration, classify the *body* and (separately) the text before the
   first `:=`/`:= by` (the *statement*) against marker groups:
   `runCascade2` · `hLU2`/`twoStrata` · `jobs1`/`jobs2` · `ReachedByW3d2*` ·
   `frontierMax`/`frontierRowsAbove`/`cascadeKeysAbove` · `round1`/`round2` ·
   the routed single-pass names (`reconcileJobsLR`, `checkFnR`, …).

Raw totals:

```
=== W3d-2 layer files: total top-level decls ===
   91  GraphIndex/CascadeStrata.lean
   19  GraphIndex/CascadeStrataAssemble.lean
   13  GraphIndex/CascadeStrataEdge.lean
   29  GraphIndex/CascadeStrataEnum.lean
   31  GraphIndex/CascadeStrataInv.lean
   26  GraphIndex/CascadeStrataResettle.lean
  115  GraphIndex/CascadeStrataSettle.lean
  324  TOTAL W3d-2 layer

FLAGGED (touch a round-binding marker anywhere in the tree): 129 decls, 5,829 lines
```

The mechanical split is a *screen*, not the answer — it over-flags (a decl that
merely threads `hLU2` through to a callee is flagged) and its decl boundaries are
approximate for `where`-blocks. The classification below is the **hand audit** of
the 129, done by reading each statement.

### 1.2 (a) GENUINELY round-count-dependent — 31 declarations, ~2,580 proof lines

"Genuinely" = the statement quantifies over exactly two rounds/batches, or the
proof performs a two-round case analysis that has no `N`-round analogue without a
new induction. Line counts are the decl spans from the scan.

#### (a-i) The scheduler — 21 decls, ~1,894 lines

| file | symbol | lines | how it depends on "2" |
|---|---|--:|---|
| `CascadeStrata.lean` | `runCascade2` (def) | 19 | **two literal nested `reconcileJobsLR` applications** + one quiescence check; the count is not a parameter |
| `CascadeStrata.lean` | `ReachedByW3d2` (inductive) | 31 | `cascade` constructor takes `jobs1 jobs2` and **two** cover/scope pairs at **two** cursors (`σ.watermark`, `σ.frontierMax σ.watermark`) |
| `CascadeStrata.lean` | `runCascade2_no_abort` | 165 | the whole argument is "a round-**2** leftover row is a `jobs2` emission at a derived R-node ⇒ its reader would be a third stratum ⇒ `hLU2` contradiction". Depth-2 case analysis, no induction |
| `CascadeStrata.lean` | `cascade2_drains` | 31 | corollary of the above; `Quiescent` earned at exactly 2 rounds |
| `CascadeStrata.lean` | `hLU2_of_hLU` | 21 | the depth-1 ⇒ depth-2 conservativity lemma; the shape `hLU → hLU2` becomes `hLU_k → hLU_{k+1}` |
| `CascadeStrataSettle.lean` | `round2_key_reads_derived` | 89 | statement is literally "a key in **round-2** scope reads a derived operand"; proof splits on "original rows sit at or below the round-2 cursor" |
| `CascadeStrataSettle.lean` | `round1_emission_dirties` | 26 | "round-1 operand passes provably re-dirty stratum-2 readers" — round-indexed, though near-generic in substance |
| `CascadeStrataSettle.lean` | `writeLeg_sem_stable2` | 106 | the "**stratum-2**" form: `sem` stable at a key unmapped *and* whose **derived operands** are unmapped. At depth N the hypothesis must become *transitive* operand-unmappedness |
| `CascadeStrataSettle.lean` | `writeLeg_sem_stable2_d` | 117 | Direct-arm clone of the above |
| `CascadeStrataSettle.lean` | `removeLeg_sem_stable2` | 125 | remove-leg dual |
| `CascadeStrataSettle.lean` | `removeLeg_sem_stable2_d` | 142 | Direct-arm clone |
| `CascadeStrataSettle.lean` | `ReachedByW3d2C` (inductive) | 36 | coverage chain with **per-round** conditional coverage `hcovg1`/`hcovg2` relative to leg-start and MID |
| `CascadeStrataResettle.lean` | `settledComplete_cascade2_targeted` | 190 | **the hard one.** Explicit Case A ("some round-**2** job targets the key") / Case B ("the last targeting job is in round 1"), with the stratum fence in between. There is no third case because there is no third round |
| `CascadeStrataResettle.lean` | `settledComplete_cascade2_targeted_d` | 203 | Direct-arm clone of the above |
| `CascadeStrataResettle.lean` | `reachedByW3d2C_settled` | 200 | the **THREE**-disjunct invariant `settled ∨ dirty ∨ operand-dirty`. At depth N the third disjunct must become "some *transitively* derived operand is dirty" — a different predicate |
| `CascadeStrataResettle.lean` | `reachedByW3d2C_settled_d` | 195 | Direct-arm clone |
| `CascadeStrataAssemble.lean` | `enumJobs2R1` (def) | ~5 | "the round-**1** enumerated jobs … at the leg-start state" |
| `CascadeStrataAssemble.lean` | `enumJobs2R2` (def) | 11 | "the round-**2** enumerated jobs … at the MID state" |
| `CascadeStrataAssemble.lean` | `ReachedByW3d2E` (inductive) | 29 | `cascade` constructor hard-wires `runCascade2 S T σ (enumJobs2R1 …) (enumJobs2R2 …)` |
| `CascadeStrataAssemble.lean` | `reachedByW3d2E_toC` | 137 | discharges the C-chain's coverage per round, in two literal cases (round-1 at leg start, round-2 at the transported MID state) |
| `FullScope.lean` | `W4Fragment.twoStrata` (field) | 16 | the depth-2 dependency hypothesis itself; threaded into `graph_correct` / `graph_reached_inv` / `Exec.graphRun_check_eq_sem` |

#### (a-ii) The READ side — 10 decls, ~687 lines — **the finding the prior assessment missed**

The prior one-line assessment located the problem in the *scheduler*. It is also
in the *read bridge*, and that half is arguably harder.

```
sed -n '1533,1612p' formal/lean/ZanzibarProofs/GraphIndex/CascadeStrataSettle.lean
```

`checkFnR_eq_sem_settled` takes

```lean
(hLU2 : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
   ∀ e', S.lookup (dt, r') = some e' →
     ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
```

and uses it *load-bearingly* in the derived-operand branch:

```lean
have hleafUnt' : ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false :=
  hLU2 r' hr' hd' e' hlk'
...
rw [checkFn_eq_sem_bs hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm
      (ReachedByW3aAdmitted.base h0) hlk' hco' hleafUnt' (fun _ => hshb) hon]
```

i.e. **the routed read's recursion bottoms out at depth 2 by falling back to the
UNROUTED W3a/W3c lemmas** (`checkFn_eq_sem_bs`, `coveredFn_declared`) at the
operand. At depth N that fallback is unavailable: the operand's operands may
themselves be derived. Generalizing requires a **strong induction on stratum
index** with routed, stratum-indexed forms of the W3c linchpin `coveredFn_declared`
and of `checkFn_eq_sem_bs`.

| file | symbol | lines | how |
|---|---|--:|---|
| `CascadeStrataSettle.lean` | `checkFnR_eq_sem_settled` | 69 | as above — depth-2 fallback to unrouted lemmas |
| `CascadeStrataSettle.lean` | `checkFnR_eq_sem_settled_d` | 84 | Direct-arm clone, same fallback |
| `CascadeStrataSettle.lean` | `checkFnR_eq_sem_settled_d_filt` | 96 | `T↾U`-σ0 clone, same fallback |
| `CascadeStrataResettle.lean` | `settledComplete_jobsLR_targeted` | 260 | *per-batch, round-agnostic* — see §1.4 — **but** carries `hLU2e` and inherits the depth-2 fallback through the read bridge and `computedRefs_ne_self` |
| `CascadeStrataEnum.lean` | `w3d2_leg_context` / `_d` / `_d_filt` | 34/31/31 | rebuild the read bridge + coverage-declaredness at a W3d2 state; carry `hLU2` into the bridge |
| `CascadeStrataEnum.lean` | `w3dJobCoverage_enumJob2_state` | 48 | discharges round-1 coverage from state; consumes the bridge |
| `CascadeStrataResettle.lean` | `graph_correct_w3d2` / `_d` | 120/149 | T2b at the drained two-round state; statement carries `hLU2` |
| `CascadeStrataAssemble.lean` | `graph_correct_w3d2E` | 25 | ditto over the operational chain |

(`settledComplete_jobsLR_targeted` is listed here rather than in (a-i) because its
*round* structure is generic and only its *depth* structure is not. It is the
single most valuable asset in the tree for this arc — see §1.4.)

### 1.3 (b) MERELY stated at 2 — 98 declarations, ~3,250 proof lines

Everything else in the flagged set. These fall into three mechanical shapes:

1. **"apply the per-batch lemma twice"** — `structInv_runCascade2`,
   `residueHygienic_runCascade2`, `residueDeclared_runCascade2`,
   `edgeHyg1_runCascade2`, `untaintedShadow_cascade2` (+`_d`),
   `count_runCascade2_of_ne`, `count_runCascade2_of_src`, `runCascade2_cases`.
   Under a `List.foldl`-shaped `runCascadeN` these become **one** fold induction
   each — strictly *shorter* than what is there now.
2. **Chain inductions whose `cascade` case is (1)** — the whole
   `reachedByW3d2_*` structural family (`_schema`, `_edgesClosed`,
   `_edge_target_ne_bare` (+`_d`), `_bareNode_no_inedge` (+`_d`),
   `_edges_target_plain`, `_Rnode_source_bare` (+`_d`), `_reach_collapse_root`
   (+`_d`), `_shadow` (+`_d`), `_structInv`, `_residueHygienic`,
   `_residueDeclared`, `_untOccCount`, `_srcOccCount`, `_residueStarFree`,
   `_Rnode_source_name_ne_star`, `reachedByW3d2C_toW3d2`, …).
3. **Threading-only consumers** — all 9 flagged `Exec.lean` decls
   (`cascadeLeg`, `graphRun_reached`, `graphRun_check_eq_sem`, `graphRunOps*`,
   `foldAdmitsB_iff`, `htermB_iff`, `GraphOp`), all 8 flagged `Equiv.lean`
   corollaries, `FullScope.lean`'s `graph_correct` / `graph_reached_inv` /
   `w4Fragment_of_untainted` / the two `W4Witness*.fragment`s / `within_scope` /
   `correct_applies`, plus `RemoveConfluence.lean` (4) and `RemoveOccCount.lean` (2).

### 1.4 THE RATIO — the number this document exists to produce

```
genuinely round/depth-count dependent :  31 decls  (~2,580 lines)
merely stated at 2, round-generic     :  98 decls  (~3,250 lines)
                                        ---------
total flagged                         : 129 decls  (~5,830 lines)
```

**≈ 24 % of touched declarations (≈ 44 % of touched proof lines) are genuinely
dependent. ≈ 76 % of declarations are re-statement, not re-proof.**

Read that number carefully in both directions:

* **Optimistic reading.** Three quarters of the surface is mechanical. And the
  per-round engine already exists and is round-agnostic:
  `settledComplete_jobsLR_targeted` (260 lines) settles a key across **one**
  arbitrary `jobs` batch at **one** arbitrary state. A `runCascadeN` induction
  consumes it once per round. **That lemma is the reason this is a plan and not a
  rewrite.**
* **Pessimistic reading.** The 24 % contains *every* proof over 100 lines in the
  layer — six of them between 106 and 203 lines, plus the 165-line
  `runCascade2_no_abort` and the 137-line `reachedByW3d2E_toC`. The `_d`
  (Direct-arm) clones **double** the cost of the hardest four. The line ratio
  (44 %) is the honest one for effort estimation, and even it understates,
  because the (a) lines are the hardest lines in the repository.

---

## 2. Pressure-testing the shape

### 2.1 `runCascade3` — one more literal round

**The question that decides it: is the stratum count bounded?** It is not.

```
python -c "... parse_openfga_schema(chain of depth N) ; len(rs.compiled.strata) ..."
```

```
chain depth  2 -> 2 strata      chain depth  8 ->  8 strata
chain depth  3 -> 3 strata      chain depth 12 -> 12 strata
chain depth  5 -> 5 strata
```

`zanzibar_utils_v1.py::_stratify` is plain Kahn over the tainted `plans` dict with
no cap; the only bound is `len(plans)`, i.e. the number of derived relations in
the schema. A schema author writes 12 strata by writing 12 chained boolean
relations. **The ceiling is a schema-authoring decision, not a language limit.**

What the project's *corpora* actually reach (measured, same session):

```
curated corpora (28 across the four dicts):  {0:10, 1:9, 2:11, 3:1}
   the single 3 is MULTI_STRATUM_SCHEMAS::three_strata_chain
generated seeds (40): {0:4, 1:8, 2:16, 3:12}
   seeds >=3: [3, 7, 8, 11, 12, 15, 17, 18, 34, 35, 36, 39]  (12 of 40)
GRAPH_FRAGMENT (23 corpora): {0:7, 1:8, 2:8}   -- max 2, as the fragment requires
```

**Verdict: NO.** `runCascade3` costs essentially the full (a) re-proof (every
Case A/Case B analysis becomes Case A/B/C; the read bridge's depth-2 fallback
becomes a depth-3 fallback, i.e. one more hand-written layer) and buys a wall at
4 instead of 3. It would let `three_strata_chain` into `GRAPH_FRAGMENT` and would
cover 12 of the 40 generated seeds — but it would be *the same finding again* the
first time someone writes a 4-chain, and the next author would inherit
`runCascade3_no_abort`, `round3_key_reads_derived`, a FOUR-disjunct
`reachedByW3d3C_settled`, and `_d` clones of all of it. **It is the worst option:
almost all the cost, none of the generality, and it entrenches the pattern.**

### 2.2 `runCascadeN` with induction over rounds — RECOMMENDED

Shape: `runCascadeN (S T σ) (jobss : List (List W3cJob)) : GraphState`, a
`List.foldl (reconcileJobsLR S T) σ jobss` with the same single quiescence check
at the end, and `runCascade2 S T σ j1 j2 = runCascadeN S T σ [j1, j2]` as a
`rfl`-or-near-`rfl` bridge theorem.

Why this is the right shape:

* **It is what Python does** (§0.1). `rounds = len(self.compiled.strata)` is
  literally `jobss.length = |strata|`. The correspondence comment in
  `CascadeStrata.lean:374-379` already says so ("`_run_cascade` at
  `rounds = len(self.compiled.strata) = 2`") — the model is the N=2 instance and
  the doc comment admits it.
* **It makes the (b) 76 % strictly cheaper.** Every "apply the batch lemma twice"
  proof becomes one `List.foldl` induction. Several get *shorter*.
* **It preserves additivity.** `runCascade2` can stay as a definition with a
  proved unfolding to `runCascadeN … [j1,j2]`, so every audited statement stays
  byte-identical until a leg deliberately changes one (§3, and cf. the 2026-07-19h
  precedent where audited originals were refactored into byte-identical wrappers).
* **The stratum-index induction has a substrate already proved.**
  `Spec/Stratify.lean::stratify` + `Spec/WellDef.lean::stratify_topo_strict` /
  `stratify_topological` (T0b) give a Kahn layering with strict topological
  ordering over `depEdges S`. That is exactly the well-founded order the
  `N`-round settledness induction needs.

The two real costs:

* `hLU2` must become `hLUN` — "no derived-dependency chain longer than `N`", or
  better, `stratify S = some L ∧ L.length ≤ N`, or best, drop the bound entirely
  and index the induction by stratum. **[UNKNOWN]** whether the dependency-wise
  form can be generalized without going through `stratify`; `hLU2`'s in-file note
  (`CascadeStrata.lean:1188-1194`) says it was *deliberately* stated
  dependency-wise so that `hLU` is literally the special case. A `stratify`-indexed
  `hLUN` needs a bridge lemma "dependency depth ≤ layer index", which
  `stratify_topo_strict` should give but which does not exist today
  (`grep -rn "depEdges" formal/lean/ZanzibarProofs/GraphIndex/` returns nothing —
  the graph layer has never touched `depEdges`).
* The read bridge (§1.2 (a-ii)) must be re-founded as a strong induction on
  stratum, dragging routed forms of `coveredFn_declared` and `checkFn_eq_sem_bs`
  into existence. **This is the true schedule risk, not the scheduler.**

### 2.3 A fixpoint / fuel formulation — REJECTED on faithfulness

Iterate `reconcileJobsLR` to quiescence with a fuel bound. Superficially the
"most general" choice, and the prompt correctly flags it as the one closest to a
loop-to-quiescence implementation.

**But Python does not loop to quiescence** (§0.1). It runs a fixed `len(strata)`
rounds and then *asserts* quiescence, raising `InvariantViolation` if the
assertion fails. A fuel/fixpoint model would:

* prove a theorem about an algorithm the code does not run — precisely the
  failure mode `CORRESPONDENCE.md` §8 and house rule 5 exist to prevent;
* **delete the modelled abort branch**, which is the one place the Lean model
  currently earns something real (`runCascade2_no_abort` proves Python's
  `raise InvariantViolation` is dead code *at the modelled stratum count*). A
  fixpoint model makes that branch unstatable, weakening the claim while
  appearing to strengthen it;
* still need a termination/fuel-sufficiency argument that is *the same*
  stratum-index induction as (2.2), so it saves nothing on the hard half.

Note also `CORRESPONDENCE.md` §7 already records that Python's leftover set
absorbs the pending `self._bumped` residue-version fan-out, so Python's abort
condition is *strictly stronger* than the Lean one — an existing, declared
divergence in this exact code. A fixpoint model would make that divergence
harder, not easier, to state.

### 2.4 RECOMMENDATION

> **If this arc is executed at all, execute it as `runCascadeN` (§2.2) with the
> round count supplied by the schema's own stratification, and treat the READ
> bridge — not the scheduler — as the critical path.**
>
> But see §4: the recommended action for the project *today* is **not to execute
> it**. The recommendation above is conditional on someone deciding the coverage
> is worth ~6 sessions.

Ranking, with the reason in one line each:

1. **`runCascadeN`** — faithful to `rounds = len(strata)`, makes 76 % of the
   surface cheaper, has a proved stratification substrate, and generalizes once
   instead of per-N.
2. **Do nothing; document the wall** (§4) — the wall is fail-closed (§0.2),
   Python is differentially tested at 3 strata, and the effort has better homes.
3. **`runCascade3`** — the same cost profile as (1) with none of the generality.
4. **Fuel/fixpoint** — unfaithful to the implementation; deletes the abort proof.

---

## 3. The legs

House style: each leg **additive**, each leg independently gate-green
(`verify.sh lean PASSED`, audit count **never drops** — it is a `-ge` floor, so
adding is free and removing fails), audited statements byte-identical unless the
leg's whole purpose is to change one, and the arc abandonable at any leg
boundary. Sizes are in "sessions" of the granularity used across
`history/PROOF_STATUS.md`.

### Leg 0 — the gate hole, first (½ session)

**Proves:** nothing. **Files:** `formal/verify.sh` (or
`formal/conformance/statement_pin.py`), `formal/headline_statements.txt`.
**What:** make the statement pin see through structure-valued hypotheses — pin
the *fields* of `W4Fragment` and `GraphAdmission` alongside the headline
statements (a `#print` of the structure, or a second pin file).
**Why first:** §0.3. Every later leg changes what `graph_correct` claims without
tripping any existing gate. Without Leg 0 the arc is unauditable by its own
gate, and a partially-executed arc is *worse* than no arc — it can leave
`W4Fragment` weakened with the pin still green.
**Unblocks:** honest review of Legs 3–6.
**Risk:** none. This leg is worth doing **even if the rest is abandoned** — and
it is the only leg with that property.

### Leg 1 — `runCascadeN` as a conservative extension (1 session)

**Proves:** `runCascadeN S T σ jobss` (fold + one quiescence check) and
`runCascade2_eq_runCascadeN : runCascade2 S T σ j1 j2 = runCascadeN S T σ [j1,j2]`;
plus fold versions of the (b)-class bookkeeping:
`structInv_runCascadeN`, `residueHygienic_runCascadeN`,
`residueDeclared_runCascadeN`, `edgeHyg1_runCascadeN`,
`untaintedShadow_cascadeN` (+`_d`), `count_runCascadeN_of_ne`/`_of_src`,
`runCascadeN_cases`.
**Files:** `CascadeStrata.lean`, `CascadeStrataInv.lean`, `CascadeStrataEdge.lean`,
`CascadeStrataSettle.lean` (the `untaintedShadow_cascade2` pair).
**Unblocks:** everything. Nothing existing changes: the `runCascade2` versions
become one-line corollaries via the bridge, byte-identically stated.
**Size:** ~400 lines added, ~150 lines of existing proof replaced by corollaries.
**Risk:** LOW. This is the leg to do first if you want to find out cheaply
whether the arc is tractable — if the fold formulation does not collapse the
bookkeeping proofs, stop here and abandon.

### Leg 2 — `hLUN` and the stratum index (1 session)

**Proves:** a depth predicate `DerivedDepthLE S n` (dependency-wise, generalizing
`hLU`/`hLU2` — `hLU = DerivedDepthLE S 0`, `hLU2 = DerivedDepthLE S 1`), the
conservativity ladder `derivedDepthLE_succ` (generalizing `hLU2_of_hLU`), and the
bridge to the proved stratification: `stratify S = some L → DerivedDepthLE S L.length`
via `stratify_topo_strict`.
**Files:** new `GraphIndex/CascadeStrataDepth.lean`; `Spec/WellDef.lean` untouched
(consumed only).
**Unblocks:** Legs 3–5.
**Size:** ~250 lines.
**Risk:** MEDIUM. `depEdges S` (`Spec/Stratify.lean:88`) is over `refsOf S a`
filtered to tainted keys, whereas `hLU2` is over `computedRefs e` at a fixed
object type `dt`. **[UNKNOWN]** whether those coincide on the fragment; if they
do not, the bridge lemma needs a `ComputedOnly`-scoped comparison. Check this
*before* committing to Leg 2 — it is a 30-minute `#eval`/read, and it is the
cheapest place in the arc to discover a mismatch.

### Leg 3 — the READ bridge by stratum induction (2 sessions) — **THE RISK LEG**

**Proves:** `checkFnR_eq_sem_settled_n` — the routed guard equals `sem` at a
derived key of stratum `k`, by strong induction on `k`, given settledness at all
lower strata. Requires routed, stratum-indexed forms of the two lemmas the
current proof falls back to at depth 2: `coveredFn_declared` (the W3c linchpin,
`ReconcileStarsComplete.lean`) and `checkFn_eq_sem_bs` (`ReconcileComplete.lean`).
Then the `_d` and `_d_filt` clones.
**Files:** `CascadeStrataSettle.lean`, `CascadeStrataEnum.lean`, and — the part
that makes this expensive — probably `ReconcileStarsComplete.lean` /
`ReconcileComplete.lean`, i.e. **outside** the W3d-2 layer, in W3c/W3a code that
has been stable since 2026-07-11.
**Unblocks:** Legs 4–5. Nothing else can proceed without it.
**Size:** ~800–1,200 lines. The three `checkFnR_eq_sem_settled*` variants are
69+84+96 = 249 lines today and each will grow.
**Risk:** **HIGH — this is where the arc realistically goes wrong.** Two named
hazards:
* `coveredFn_declared` is described in `HANDOFF.md` as "the LINCHPIN" and its
  proof runs through the materialised-closure star seed. A routed version must
  hold at a derived operand whose `stars` row is itself maintained by the
  cascade — i.e. the "no ghost star coverage" argument must be re-founded
  *inside* the induction, which is exactly the shape that has been
  attack-refuted before (kill #6, the "round-1 keys are stratum-1" refutation).
* **ATTACK FIRST (house rule 2).** Before writing a line of Leg 3, `#eval` the
  proposed `checkFnR_eq_sem_settled_n` statement at depth 3 against the real
  `check`/`sem` on `three_strata_chain` and on a 3-chain with a star grant on the
  middle stratum. The prior arc killed seven statements this way; this one has
  the same smell.
**Fallback if Leg 3 fails:** stop. Legs 0–2 are additive, green, and independently
useful (Leg 0 fixes a real gate hole; Legs 1–2 leave the tree strictly more
general with no claim changed). Record the kill in `PROOF_STATUS.md` and close
the arc as "attempted, refuted at the read bridge" — which by house rule 2 is a
*good* session.

### Leg 4 — the settledness induction over rounds (1½ sessions)

**Proves:** `settledComplete_cascadeN_targeted` — replacing the Case A/Case B
analysis of `settledComplete_cascade2_targeted` with an induction over `jobss`
whose IH is "after round `k`, every targeted key of stratum ≤ `k` is
settled+complete". Consumes `settledComplete_jobsLR_targeted` unchanged (§1.4)
plus the stratum fence generalized from `round2_key_reads_derived` to
`roundSucc_key_reads_lower`. Then `reachedByW3d2C_settled_n` with the third
disjunct widened to *transitive* operand-dirtiness, and the `_d` clones of both.
**Files:** `CascadeStrataResettle.lean`, `CascadeStrataSettle.lean`.
**Unblocks:** Leg 5.
**Size:** ~900 lines (the four originals total 788 and the `_d` clones must
track).
**Risk:** MEDIUM-HIGH. The three-disjunct invariant becoming transitive is a
genuine statement change; attack it before proving it.

### Leg 5 — the operational chain and `no_abort` at N (1 session)

**Proves:** `enumJobs2RK` (round `k` enumerated at the state round `k-1` left),
`ReachedByW3dNE`, `reachedByW3dNE_toC`, `runCascadeN_no_abort` under `hLUN`,
`cascadeN_drains`, and `graph_correct_w3dNE`.
**Files:** `CascadeStrataAssemble.lean`, `CascadeStrata.lean`.
**Unblocks:** Leg 6.
**Size:** ~600 lines.
**Risk:** MEDIUM. `runCascade2_no_abort` (165 lines) becomes an induction with
the cursor arithmetic re-done per round; `outbox_le_frontierMax` should carry.

### Leg 6 — retarget the headline, widen the corpus (1 session)

**Proves:** nothing new. **Does:** `W4Fragment.twoStrata` → the `hLUN` field
(**deliberate claim change** — regenerate `headline_statements.txt` *and* the Leg-0
structure pin, and say why in the commit message); `FullScope.lean::ReachedBy`
retargeted; `Exec.lean::cascadeLeg` reads the round count off the schema; move
`three_strata_chain` into `GRAPH_FRAGMENT` and classify it `_THEOREM_BACKED` with
the per-field argument in `corpus.py`; add a ≥4-stratum corpus; re-run the
graph-state conformance mode.
**Size:** ~200 lines Lean + conformance work.
**Risk:** LOW-MEDIUM. The known operational cliff (`nary-strata-coverage` §5:
"2 subj 0.1 s → 5 subj 115 s" in the round-2 job enumeration) will get *worse*
with more rounds — keep the new corpora at 2–3 distinct subjects.

### Leg count and size

**7 legs (0–6), ~8 sessions, ~3,000–3,500 net new Lean lines.** The prior
one-line estimate ("multi-session") was right in direction and roughly a factor
of two optimistic in magnitude, chiefly because it did not account for the read
bridge (Leg 3) or the `_d` clone tax (Legs 3–4).

---

## 4. The honest cost/value call

### What the project GAINS

1. `W4Fragment.twoStrata` deleted → `graph_correct` / `graph_reached_inv` /
   `Exec.graphRun_check_eq_sem` cover arbitrary stratum counts. One of the six
   honest-gap carries in `W4Fragment` is closed.
2. `three_strata_chain` (and a ≥4 successor) can enter `GRAPH_FRAGMENT` as
   theorem-backed, adding real Lean-model-vs-Python operational coverage where
   today there is none.
3. 12 of 40 generated seeds gain graph-side coverage they currently cannot have.
4. The `runCascadeN` fold makes ~76 % of the W3d-2 bookkeeping shorter and makes
   *any* future round-count change free.

### What it does NOT gain

* **It does not fix a bug.** Python's ≥3-stratum cascade is differentially tested
  three ways today (`test_conformance_nary_strata::test_multi_stratum_three_way`
  runs the real `WildcardIndex`+`DeltaProcessor` against the independent oracle
  and the real `SetEngine` over the full grid under **both** `SetOps`;
  `test_conformance_spec.py` runs Lean `sem` × oracle × set engine on
  `three_strata_chain`; 12 generated seeds do the same). No divergence has been
  found at 3 strata by any of them.
* **It does not remove a live risk.** §0.2 measured that the Lean model at 3
  strata exits rc 3 rather than answering. There is no wrong answer being
  produced, and no wrong claim being made — `W4Fragment.twoStrata` is a
  *declared* carry with an attack note in the source.
* **It does not unblock any other open item.** Cross-checked against
  `HANDOFF.md`'s board: the E-chain Direct-arm widening, the `hNoUD` lift,
  Direct-arm operands, `PDerivedTuplesetTTU`, wildcard usersets, and the
  `w3cJobValid_enumJob2D` star-freeness decision are all independent of the round
  count.

### The call

> **This is assurance-widening with bounded value, and ~8 sessions is a poor
> price for it.** The gap is a *proof-scope* gap over an algorithm that is (i)
> already differentially tested at the uncovered depth, (ii) fail-closed rather
> than fail-open in the Lean model, and (iii) honestly declared in three places
> (`W4Fragment`'s doc comment, `runCascade2_no_abort`'s attack note,
> `nary-strata-coverage-2026-07-27.md` §5).
>
> **Recommended disposition: do Leg 0 (½ session, fixes a real gate blind spot
> that exists independently of this arc), then STOP** and leave Legs 1–6 on the
> board as a costed, shaped option. If a future session wants to spend on the
> Lean tree, `HANDOFF.md`'s option (a) — the E-chain Direct-arm widening — closes
> a gap on the *canonical Zanzibar boolean shape* (`can_view: [user] but not
> blocked`) where the final theorems are currently **VACUOUS**, not merely
> narrow. That is strictly more valuable per session than round-count generality,
> and `HANDOFF.md` already ranks it first.

### What this arc would incidentally fix or expose

* **The statement-pin blind spot (§0.3)** — found only because this arc forces
  the question "what stops me from silently weakening `graph_correct`?". Answer
  today: nothing. This is the single most valuable thing in this document and it
  is *free* (Leg 0).
* **`depEdges` vs `computedRefs`** — the graph layer has never used the Spec
  layer's dependency graph (`grep -rn "depEdges" formal/lean/ZanzibarProofs/GraphIndex/`
  → no hits). Leg 2 would connect T0b's proved stratification to the operational
  model for the first time. Whether they agree is **[UNKNOWN]** and worth knowing
  regardless.
* **The `_d` clone tax** — Legs 3–4 would make it painfully concrete that
  `CascadeStrataResettle.lean` and `CascadeStrataSettle.lean` carry four
  near-duplicate proof families (plain / `_d` / `_filt` / `_d_filt`, 2,692 + 4,420
  lines). Any future widening pays this tax. A refactor that parameterizes the
  fragment instead of cloning it may be worth more than either widening.
* **`CORRESPONDENCE.md` §7's `_bumped` divergence** — Leg 5 touches the abort
  branch and would force a decision on whether to model Python's stronger abort
  condition.

---

## 5. Resume block

### Read first, in this order

1. `formal/HANDOFF.md` — "State of the world" + "THE NEXT TASK" (the board ranks
   the E-chain Direct-arm widening above this arc; §4 agrees).
2. `formal/history/nary-strata-coverage-2026-07-27.md` — the finding this plan
   costs out. **Note the two corrections in §0 above: Python runs `len(strata)`
   rounds (not a quiescence loop), and the Lean model fails closed at 3 strata
   (rc 3, measured).**
3. **This file** §1.4 (the ratio), §2.4 (the recommendation), §4 (the call).
4. `formal/lean/ZanzibarProofs/GraphIndex/CascadeStrata.lean` lines 374-470
   (`runCascade2` + `ReachedByW3d2`) and 1188-1400 (`hLU2`, `runCascade2_no_abort`
   with its in-file attack note at 453-461).
5. `formal/lean/ZanzibarProofs/GraphIndex/CascadeStrataSettle.lean:1538-1612`
   (`checkFnR_eq_sem_settled` — the depth-2 fallback, §1.2 (a-ii)).
6. `formal/lean/ZanzibarProofs/FullScope.lean:107-146` (`W4Fragment`, the
   `twoStrata` field and its doc comment).
7. `index_v4/processor.py::DeltaProcessor._run_cascade` (the `rounds =
   len(self.compiled.strata)` loop).

### Commands to re-establish the current state

```bash
# the gate (measured 2026-07-27: PASSED, holes=0, audits=457, pinned=457)
export ZANZIBAR_PY=/c/Users/user/anaconda3/envs/graph-reachability-zanzibar-index/python.exe
export PATH="$HOME/.elan/bin:$PATH"
bash formal/verify.sh lean

# the two-round inventory (§1) -- decl-level scan of the Lean tree
grep -rn "runCascade2" --include=*.lean formal/lean/          # 96 hits, 12 files
grep -rn "hLU2"        --include=*.lean formal/lean/          # 193 hits, 9 files
grep -rn "twoStrata"   --include=*.lean formal/lean/          # 7 hits, FullScope.lean only

# the stratum-count bound (§2.1)
PY=/c/Users/user/anaconda3/envs/graph-reachability-zanzibar-index/python.exe
"$PY" -c "import zanzibar_utils_v1 as z; \
  s='type user\ntype doc\n  relations\n    define x: [user]\n    define y: [user]\n' \
    '    define a5: x but not y\n' + ''.join('    define a%d: a%d and x\n'%(i,i+1) for i in (4,3,2,1)); \
  print(len(z.parse_openfga_schema(s).compiled.strata))"        # -> 5

# the fail-closed measurement (§0.2) -- needs zcli built by the lean phase
#   build the shared grid for MULTI_STRATUM_SCHEMAS['three_strata_chain'],
#   drop star-object targets (hqo), then:
#     invoke_zcli(build_request(..., mode='spec'))   -> rc 0, 161 answers
#     invoke_zcli(build_request(..., mode='graph'))  -> rc 3, "final state not drained"
#     control two_stratum_cascade, mode='graph'      -> rc 0
```

### If you execute anything

Do **Leg 0 only** (§3), unless someone has decided the ~8-session price in §4 is
worth paying. Leg 0 is `formal/verify.sh` + `formal/headline_statements.txt`,
touches no proof, and closes a hole that exists whether or not this arc is ever
started.
