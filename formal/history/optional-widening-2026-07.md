# Optional assurance-widening — design briefs & resume points (2026-07-18)

**Purpose.** The formal-verification arc is COMPLETE (T1 + T2a/T2b + T3/T6 over
`ReachedBy`, Phase 6, conformance — all sorry-free, axiom-clean, gate green). What
remains is the OPTIONAL assurance-widening ranked in `FINAL_REVIEW.md §4`. This file
is the durable design + resume state for that work, so a fresh-context session can
pick up ANY of the four targets without re-doing recon. Read `formal/HANDOFF.md`
first, then the target's section here.

Each target was scoped by a read-only recon + (for #1) attack-first `#eval` probes.
House rules unchanged (honesty; attack-first; green `verify.sh`; commit per green
increment; subagents don't parallelize proof-closing — one Lean-editing leg at a time).

Working order chosen (2026-07-18): **interleave** — bank the tractable targets (#3
state/enum, #4 remove) then return to the deep grinds (#1 Direct-arm leg 4+, #1
TTU/userset, #2 strata). Ordering is the orchestrator's call; adjust freely.

---

## Target #1 — Leaf fragment widening (`W4Fragment.computedOnly` → Direct/TTU arms)

Goal: let derived (tainted/boolean) defs carry `Direct` and TTU operand leaves
(`PDerivedTTU`/`PDerivedUserset`), not just `computed`. `computedOnly` is STRUCTURAL —
it powers two workhorse lemmas that are literally FALSE for Direct/TTU leaves. Genuine
proof effort. Split **Direct-arm-first, then TTU/userset**.

Attack-first ground truth (all backends agree; NO live Python divergence):
- Tainting needs an exclusion/intersection ROOT or a reference to an already-derived
  relation — a plain `or` of a Direct/TTU arm compiles UNTAINTED. Real Direct-arm shape:
  `approver = [user] but not banned` (raw `excl (direct [user]) (computed banned)`).
- A Direct arm compiles to a `PClosureLeaf(storage=True)` family `<rel>.<index>`; a raw
  write on the public derived key is admission-accepted and routed onto that storage leaf
  (I5 preserved). So the write-half "no stored tuple on a derived key" must be reformulated.
- Python has NO 2-stratum cap; `twoStrata` is proof-scope only (see #2).

### Direct-arm sub-legs — progress
- **Leg 1 DONE (commit `98773d3`)** — read-half workhorse. Added (additive, `ReconcileCorrect.lean`):
  `ComputedOrDirect`, `DirectArmsBare`, `computedOnly_computedOrDirect`/`_directArmsBare`,
  `grantsOf_bare_subjects`, `memberOfGranted_of_bareGrants`, `directLeaf_bare_indep`,
  **`evalE_computedOrDirect`** (generalized READ congruence; subject/store/rel SHARED —
  varying-subject congruence is attack-refuted for `.direct` — query free).
- **Leg 2 DONE (commit `0dd8d7b`)** — write-half admission + diffing retraction crux.
  `ReconcileCorrect.lean`: `exprDirectsAll` (recurses inter/excl), `StoreValidRulesD`
  (isDerived partitions disjuncts; derived-key tuple must be BARE subject on an
  `exprDirectsAll` leaf), `storeValidRulesD_of_storeValidRules`, `reachedByW3a_*_d`
  (reach-collapse admits stored base seed edges, sources stay BARE).
  `ReconcileDiff.lean`: `reconcileKeyD_edge_char_cd`, **`reconcileKeyD_retracts_excluded`**
  (THE CRUX — excluded bare candidate's derived pair absent after the diffing pass even if
  it pre-existed as a stored base edge; attack-`#eval`-confirmed sound).
- **Leg 3 DONE (commit `8a9bee1`)** — base-equation WALL characterized (green checkpoint).
  Attack-first: the widened `graphRec_base_eq_d` is FALSE without a `NoStoreSubjectR`
  hypothesis (userset-over-derived flow → graph=true/sem=false), TRUE with it (faithfully
  available downstream via `reachedByW3d2E_toC`'s `hterm`). Landed additive
  `storeValidRules_untaintedFilter` (restrict-T entry). NOTE: `graphRec_base_eq` is at the
  ADMITTED base state where the derived-key seed edge is a harmless DEAD-END; item 1 leans
  on a dead-end/reach-invariance argument gated by `NoStoreSubjectR`, NOT on leg-2's
  drained-read retraction.

### Direct-arm — RESUME (leg 4 = the wall; details in commit `8a9bee1` message)
Start from `graphRec_base_eq` (`RestrictBase.lean:516`) / `_bs` (`:631`). Add hypothesis
`∀ dt R, isDerived S (dt,R) → NoStoreSubjectR T R`; replace `hStoreUnt`/`hSVU` with the
restrict-T route using `storeValidRules_untaintedFilter`. Prove three NEW lemmas:
- **A (dead-end seed):** `rewriteClosure` of a derived-key tuple is the seed alone — via
  `exprArms`-matchRel ⊆ `exprRefs` + heredity (`untainted_closed`) + `TtuTuplesetsDirect`.
- **B (untainted-read reach-invariance):** `probeNonDerived σ0 q' = probeNonDerived σ0_U q'`
  for untainted `q'` (σ0_U drops derived seed edges; given `NoStoreSubjectR` the derived
  node is never a path source).
- **C (sem store-restriction):** `sem S (T↾U) q' = sem S T q'` on untainted reads (store
  analog of `semAux_restrict`).
Then build/obtain an admitted state over `T↾U` (or generalize `sem_of_rules_reach` to
`StoreValidRulesD`+`NoStoreSubjectR`); thread `StoreValidRulesD` through
`reachedByW3d2E_toC` (`CascadeStrataAssemble.lean:342-355`); ensure `enumJobs2*`
(`CascadeStrataEnum.lean`) includes stored-on-R BARE subjects.
**Leg 5:** migrate subject-varying consumers (`checkFn_eq_coveredFn_of_no_extra`
`CascadeEnum.lean:66`, `coveredFn`/star machinery `ReconcileStars.lean:483`,
`CascadeStrataEnum.lean:185` — FALSE as-is for a concrete Direct grant, need a
star/concrete split gated on `DirectArmsBare`); widen `W4Fragment.computedOnly` to
`ComputedOrDirect ∧ DirectArmsBare`; re-prove `w4_within_scope` (`FullScope.lean:165-174`;
`directsOnly_of_computedOnly` needs a `directsOnly (excl …) = false` variant); add witness
`W4WitnessDirect` (`approver := excl (direct [user]) (computed banned)` + a store granting
`user:alice`) to `Audit.lean`; conformance: move a Direct-arm corpus INTO `GRAPH_FRAGMENT`
(`corpus.py`) + a state pin. Keep derived-TTU-userset shapes OUT of the graph leg.

### TTU/userset half — NOT STARTED (deeper; after Direct arm)
`PDerivedTTU` (TTU arm, store-state dependent, +1 stratum) and `PDerivedUserset`
(cross-object `upos`/`_leaf_concretes` lift — the X4 shape fixed Python-side 2026-07-13,
NEVER modeled in Lean). Hardest sub-lemma: completeness for the userset/TTU-arm read (analog
of `checkFn_eq_semStep`/`evalE_computedOrDirect` for a tree with a `ttu`/userset leaf,
including from-chain userset + cross-object-membership lift). Expect the userset half to
dominate. `computedRefs`/`ComputedOrDirect` `.ttu ↦ False` must be lifted; `evalE`
congruence must account for the TTU parent tuples (store-dependent) and the residue lift.

---

## Target #2 — Strata widening (>2 derived strata)

Goal: lift the `twoStrata`/`hLU2` cap (scheduler `runCascade2`, rounds=2) to N strata.
Attack-confirmed: Python has NO cap and is correct at ≥3 strata; the Lean round-2 reject
FIRES at 3 strata (`CascadeStrata.lean:419-429` attack schema `a:=b∨y, b:=c∨x, c:=x∖y`).
So `twoStrata` is proof-scope only, not a Python invariant. Recon verdict: a **partial
scheduler re-architecture then a clean-ish induction**; ~8–12 lemmas have intrinsically
two-round proof content (438 mechanical `runCascade2`/`jobs1 jobs2` occurrences follow the
fold once the core changes); Python known-correct at N ⇒ no algorithmic discovery risk.

Key files (all `GraphIndex/`): `CascadeStrata.lean` (scheduler + T5),
`CascadeStrataSettle/Resettle/Enum/Assemble.lean`, `CascadeStrataInv/Edge.lean`,
`Exec.lean:58` (driver wires `runCascade2`+`enumJobs2R1/R2`).

### Design / resume
- **`runCascade2`** (`CascadeStrata.lean:361-369`) bakes in "2" four ways: fixed 2-deep
  `reconcileJobsLR` nesting, two job-list params, a two-step frontier cursor chain, one
  post-round-2 leftover/reject check. Generalize to `runCascadeN S T σ (jobss : List (List
  W3cJob))` as a `foldl` over `(state, cursor)` threading the cursor computed on each
  round's PRE-apply state (preserve the advance-cursor-then-apply order EXACTLY or the
  leftover check moves). `enumJobs2R1/R2` (`CascadeStrataAssemble.lean:309-317`) → an
  indexed `enumJobs2At` per round.
- **`hLU2`** (`CascadeStrata.lean:740-743`): every computed operand of a derived def is
  untainted OR a derived key whose own computed operands are ALL untainted (chain stops
  after 1 hop). Generalize to `hLUN` — every derived-dependency chain length ≤ N, most
  cleanly via `stratify` producing ≤ N strata (T0b topological order) rather than an
  N-deep quantifier nest.
- **REUSES cleanly (stratum-agnostic):** the conditional-coverage design
  (`W3dJobOpsSettled` + `covg_of_opsSettled`, `CascadeStrataSettle.lean:1461-1495` — the
  kill-#6 "coverage must stay conditional" absorption), per-stratum read-inertness
  (`check_reconcileStarsKeyDR_other`, "whatever its stratum"), `settledComplete_jobsLR_targeted`.
- **HARD-CODED to 2 (need real re-proof, ~8-12):** `runCascade2` (def), `runCascade2_no_abort`
  (whole two-level case split `:762-889`), `cascade2_drains`, `round2_key_reads_derived`
  (`CascadeStrataSettle.lean:883-891`, one-hop), `settledComplete_cascade2_targeted`
  (binary Case A/B `CascadeStrataResettle.lean:855-869`), `writeLeg_sem_stable2`,
  `reachedByW3d2C_settled`, and the assembly quartet `enumJobs2R1`/`enumJobs2R2`/
  `ReachedByW3d2E`/`reachedByW3d2E_toC` + T2a re-assembly (`reachedByW3d2E_inv`,
  `graph_reached_inv` edge legs).
- **Proof strategy:** two nested inductions — outer on the `ReachedBy` chain (unchanged),
  inner on the round index (fold prefix). Prefer round-index induction over well-founded
  recursion on the DAG (matches the `foldl`/cursor definitionally). **Hardest lemma:** the
  N-round stratum fence / no-abort induction — generalize one-hop `round2_key_reads_derived`
  + `hLU2` to "a row above cursor cur_k came from a round-≤k emission ⇒ its reader is at
  stratum k+1", discharging `runCascadeN_no_abort`. Attack probes: within-round order at 3
  strata; a stratum-k→k−2 skip edge (kill-#6 at depth 3 — coverage must stay CONDITIONAL);
  future-residue re-read at depth 3; cursor monotonicity under out-of-order outbox ids;
  `hLUN` exactly-N-dead / N+1-live boundary.

---

## Target #3 — State/enum conformance bounds widening (mostly Python; land FIRST)

Goal (`FINAL_REVIEW.md §4(e)`): widen the exhaustive small-scope enumeration
`formal/conformance/test_conformance_enum.py` (currently k≤3, 2 names/type, 4 boolean
shapes, 527 stores; spec×oracle×set-engine pointwise over a shared grid, store-counts
asserted; ~90s, runs in the `conf-rest` phase). Four axes: (a) graph backend inside the
enumeration, (b) k=4, (c) userset/TTU shape, (d) state-level gate over enumerated stores.
Reusable driver `graphindex_answers` ALREADY EXISTS (`formal/conformance/backends.py:94-105`,
mirrors `tests/test_matrix.py::GraphBackend`; I5 leaf-routing + cascade).

### Recommended order (each an independent green increment)
1. **(c) userset/TTU shape** — ✅ **DONE (2026-07-18b, commit pending push at write time).**
   `_POOL` +`group`/`folder`; `_SHAPES` +`wildcard_group_member` (10-tuple space, 176
   stores — the existing acyclic `viewer:[group#member]`+`user:*` shape) +`ttu`
   (`viewer: viewer from parent`, 8-tuple space, 93 stores), asserted counts empirical.
   **Attack-first finding:** the brief's `group_userset` (self-referential
   `member:[user,group#member]`) is admission-INVALID for the set engine on 132/299 stores
   (cycle guard `engine.py:770`) — an admission-domain difference, not a check divergence;
   NOT used (docstring records it). Spec==oracle==set-engine on every enumerated store; no
   graph leg (that's (a)). Gate green incl. conf phases (290 conf, +2 params).
2. **(a) graph-in-enum, answer level** — ⭐ NEXT. — ~2 lines on top of `graphindex_answers` + two
   mismatch asserts, BUT copy the query-scope filter `_graph_queries_for`
   (`test_conformance_graph.py:47-57`: concrete objects only, star subjects bare) or it
   compares out-of-scope garbage. Confirm no enumerated store trips a rejected-write
   `ValueError`. Fits cap at k=3 (~+3 min in `conf-rest`, → ~7 min, ok).
3. **(b) k=4** — `_K=4` + re-assert counts. ~2.23× blow-up (527→1177; `two_stratum_cascade`
   dominates, N=12). Fits ALONE (~200s) but NOT alongside graph-in-enum in one phase (~10
   min). Shard by shape (already a `parametrize` axis) across `conf-heavy`/`conf-rest`, or
   cap `two_stratum_cascade` at k=3. No within-file sharding pattern exists today.
4. **(d) state gate over enumerated stores** — highest cost (a `graph-state` zcli run per
   store). Reuse `extractor.py` P1-P6 unchanged; almost certainly must SAMPLE/shard to fit
   the cap. Land last.

**Findings, not failures (house rule 2).** Exhaustively driving the real graph index over
all sub-stores exercises write-order/partial-store interleavings never before driven —
the class that found the P6 leaf-family and 2026-07-17 stale-fanout divergences. A store
where graph `check` ≠ `sem` on an in-fragment shape is a genuine adjudication event —
record it, never edit oracle/golden.

---

## Target #4 — Remove legs in Lean (bounded — Route 1 confluence)

Goal (`FINAL_REVIEW.md §4 item 2`, "biggest lift, highest ceiling"): the Lean chain
`ReachedBy = ReachedByW3d2E` (`CascadeStrataAssemble.lean:325-333`) is ADD-ONLY
(`empty`/`write`/`cascade`); model chain-level REMOVE. Per-key retraction ALREADY exists
(`ReconcileDiff.lean` `reconcileStarsKeyD`; T4 `pathCount_removeEdge` `Closure.lean:473`;
`removeEdgePair` `ReconcileDiff.lean:52`; `structInv_removeEdgePair` `CascadeInv.lean:48`;
`reconcileStarsKeyD_edge_char` `:922-942`). Python remove paths already pinned empirically
(`test_conformance_remove.py`). OPEN = the Lean CHAIN-level legs only.

### Design / resume — Route 1 (recommended: reuse, near-zero re-proof)
1. Add a **`remove` constructor** to `ReachedByW3d2E` (4th, retract-mirror of `write`):
   `(σ, t::T) → (σ.removeLoggedRules S t, T.erase t)` with a `RemoveAdmits`-style guard
   (mirror `TupleSource.remove` `connectedstore/source.py:104-112` — reject absent tuple).
2. Define **`removeLoggedRules`** (retract-mirror of `writeLoggedRules` `Cascade.lean:161`):
   fold a ref-counted decrement of the rewrite-closure edges (`removeEdgePair`) then
   re-cascade affected keys through the diffing pass. Mirror `core.py:687-704` +
   `processor.reconcile_subject:445-516` (removal branch `:514-515`).
3. **The ONE hard lemma — confluence:** `remove + drain == fresh add-only rebuild of the
   surviving store`. Because `sem` is a pure function of the FINAL store and the read/inv
   theorems fire at ANY drained closure state, proving this makes EVERY existing T2a/T2b/
   T3/T6 theorem apply unchanged (zero re-proof). This is the Lean form of what
   `test_conformance_remove.py` pins empirically (driven==rebuild). Induction on the
   extended chain; `write`/`cascade`/`empty` cases trivial; `remove` case = the confluence
   lemma. Under the SAME `twoStrata`/`hLU2` bound (cross-stratum re-settlement of a
   guard-flipped-down edge).
- **Risk (probe FIRST):** the model has NO edge ref-count — `removeEdgePair` filters ALL
  copies vs Python decrements by 1. Sound on DERIVED families (I5 ⇒ rc≡1); a stored-edge
  remove shared by two derivations may force adding edge multiplicity to `GraphState`
  (would ripple). Probes: remove-then-readd exact-state (ref-count/multiplicity);
  remove-a-needed-operand cross-stratum retraction (mid-drain staleness); I6 residue-version
  regression on a remove that makes a `neg`/`upos` subject edge-unreachable; node-GC
  divergence on full drain (Python reaps, Lean keeps nodes monotone — read-safe, confirm
  for state equivalence); non-present-remove admission (Python raises).
- Route 2 (direct preservation — extend every chain-inducting proof with a `remove` case)
  is the fallback if confluence fails; more local but touches `CascadeStrataEdge/Inv/
  Assemble.lean`.

**Lift:** structurally bounded (one constructor + one state op + `RemoveAdmits`); the
invariant-preservation primitives all exist; the entire content is the ONE confluence
lemma + the ref-count decision. Comparable to one W3d sub-stage — between #1-leaf (medium)
and #2-strata (largest).
