# ROADMAP — the staged path to the verified model (0 `sorry`s left, was 9)

**A fresh session reads `formal/HANDOFF.md` FIRST** (compact entry point + the next
task); this file holds the per-stage designs and post-mortems — read the section for
the stage you're working. The plan of record toward the END GOAL: **a formally
verified Zanzibar/OpenFGA model tied to the Python implementation.** Read alongside
`PROOF_STATUS.md` (ledger) and `SEMANTICS.md` (the spec).

## The architecture (how the pieces add up to the goal)

1. **`sem` (Lean) is the normative spec.** It is tied to the Python
   implementation *executably*: the conformance harness (`zcli` +
   `formal/conformance/`, 60 tests) checks `sem` = oracle = real Python set
   engine over 15 schema corpora. This is the model↔implementation bridge and
   it is already load-bearing (it caught the `fuelBound` spec bug).
2. **T1 (set engine = `sem`): ✅ DONE, axiom-clean.**
3. **T2 (graph index = `sem`): the remaining core.** Stated over an
   **operational write-closure** that grows in stages (below) until it covers
   the full `GraphAccepts` scope. Current scope: star-free pure-direct
   (`graph_correct_direct`, ✅ proved end-to-end).
4. **T3/T6 (equivalence + security): ✅ proved at the current T2 scope**; they
   are one-line corollaries that widen automatically with each T2 stage.
5. **T0a (spec well-definedness): ✅ DONE (2026-07-10)** — found FALSE as
   stated (machine-checked, `Spec/Counterexample.lean`), restated over
   `StoreDeclared` (the documented write-validity precondition), then fully
   proved: confinement (`Spec/Confine.lean`) + taint-fixpoint / untainted
   counting (`Spec/Stabilize.lean`) + strict-Kahn rank induction
   (`Spec/WellDef.lean`). Axiom-clean.
6. **Phase 6 hardening** closes the loop: sorries = 0, axiom audit as a hard
   gate, and a **graph-model conformance extension** (drive the Lean
   `writeDirect`/`check` model against the Python graph index over the fragment
   corpora) so the *graph* side of the verified model is also executably tied
   to the implementation, like `sem` already is.

Original 9 sorries; ✅ CLOSED by proof: T4, T0b, T1, and (at fragment scope,
restated) T2a/T2b/T3/T5/T6. ⚠ 2 sorries were **DELETED as false-as-stated, not
proved** (2026-07-10, user-directed — see the FINDING below): the abstract
`graph_correct` / `graph_reached_inv` quantified over a junk-admitting closure.
Their obligations are NOT gone — they return as the full-scope restatements in
stage W4 below. The last tracked `sorry` (`semAux_fuel_stable_step`, T0a) was
closed 2026-07-10 — **the tree is sorry-free**; what remains is scope widening
(W1–W4) and Phase 6 hardening.

## The staged T2 plan (write-model growth → theorem scope growth)

Each stage extends the concrete write model, widens the operational closure,
and re-proves/widens the same named theorems. Every stage must keep
`verify.sh` green and axiom-clean. No stage postulates its invariant.

- **W1 — wildcard bridges.** Materialize `*` semantics in the write model:
  concrete→`wAny` bridge edges (on both star-grant arrival and new-instance
  arrival), `wAll` object-wildcard arrivals. Widen `graph_correct_direct` to
  star data/queries (the read-side `wAny`/`wAll` promotion only covers the
  first hop today; interior hops need the materialized bridges). Key new proof
  content: bridge-completeness (every `instances` witness has its bridge) and
  the `instances`-branch of `memberOfGranted` in both correspondence directions.

  **Sub-staging (designed 2026-07-10, grounded in wildcard-spec §1.1/§3.2 —
  do W1a first):**
  - **W1a — bare star grants, ZERO bridges. ✅ DONE (2026-07-10)** —
    `graph_correct_bareStar` (`GraphIndex/BareStarCorrect.lean`, sorry-free,
    axiom-clean). Attack-first confirmed the statement (no refutation) on concrete
    bare-star scenarios, then proved: `BareStarStore` (weaker than `StarFreeStore`,
    star subjects must be bare), `directLeaf_elim_bs` (3-way: exact | bare-star |
    flow), `Covers` + `semAux_of_chainN_bs` (soundness with the leading bare-star
    hop), `reach_of_semAux_bs` (completeness = probe-1 ∨ probe-2 disjunction),
    `admitted_edge_source_char` (userset-`wAny` never an edge source ⇒ probe 2 dead
    for usersets). The design below was executed exactly. **Next: W1b.**
    (original design:) Widen `StarFreeStore` to allow
    subject `(T, *, BARE)` tuples (plain OpenFGA `[user:*]`). Wildcard-spec
    §3.2's bare-shape rule: bare shapes never need in-bridges — a bare concrete
    subject node has **no in-edges**, so any semantic path through the star is a
    *leading* instance-hop, which is exactly probe 2's `wAny` endpoint
    substitution; no interior hops exist to materialize. Semantic side matches:
    `sem`'s bare-star branch of `directLeaf` is a pure type-match (no
    `instances` recursion), and `memberOfGranted` *skips* BARE grants. So W1a =
    `writeDirect` already-correct node mapping (`subjNode` sends `(T,*,BARE)` to
    `wAny (T,BARE)`) + probe 1∨2 correspondence; no bridge machinery, no
    `instances`. The chain lemmas need: an edge out of `wAny(T,BARE)` matches
    `sem`'s "bare-star covers u" disjunct for every subject u of type T.
  - **W1b — object wildcards (`wAll` + out-bridges). IN PROGRESS (2026-07-10):
    write model done, correspondence next.**
    - **Attack-first finding (machine-checked): bridges are MANDATORY** — W1b is
      NOT bridge-free (the optimistic "maybe symmetric to W1a" is refuted). A
      `w_all` node is never an edge *source*, so one might hope probe 3 absorbs it
      as a pure trailing hop; but an object-wildcard grant flowing into a *further*
      userset hop needs the wildcard membership to reach the **concrete** object
      node — only a `w_all → concrete` bridge provides it (wildcard-spec §3.4,
      `subject → w_all(S) → concrete → …`). Refuted against real `check`/`sem`; see
      PROOF_STATUS "W1b STARTED" for the exact scenario.
    - **Write model DONE** (`GraphIndex/ObjStarWrite.lean`, axiom-clean): the
      faithful `wildcard.py:222-259` `add_tuple` — bridge-before-grant
      (`ensureBridges` per endpoint, `w_all` lazily created, guarded bridge edge)
      then the cycle-rejected grant. Wildcard-own-shape cycles reject at the grant
      (`wildcard.py:250-256`), so acyclicity holds. `structInv_writeWild` +
      `WildReached`/`wildReached_structInv` give `StructInv` at every reachable
      state.
    - **Correspondence: BOTH SEMANTIC CORES DONE** (`GraphIndex/ObjStarCorrect.lean`,
      sorry-free, axiom-clean). The read reduces to probe 1 ∨ probe 3 (subjects
      star-free ⇒ probes 2,4 dead, mirror of W1a).
      * *Soundness* (graph path ⇒ `sem`) via the **bridge-absorbing chain
        `GrantReach`**: each grant-into-`w_all` + bridge-out pair is one hop against
        a *concrete* object, keyed through `matchingObjects on = [on, STAR]` (a
        STAR-object grant is in `grantsOf` for concrete `o`). Delivered: the
        **grant-or-bridge edge characterization** (`wildReached_grant_or_bridge`),
        `GrantReach ⇒ sem` (`semAux_of_grantReach`, via `semAux_lift_os`), and
        `trail ⇒ GrantReach` (`grantReach_of_trail`). Needs neither
        bridge-completeness nor the admitted refinement (soundness only reads edges).
      * *Completeness* (`sem ⇒ probe 1 ∨ probe 3`) via `reach_of_semAux_os` (analog
        of `reach_of_semAux_bs`, disjunction on the OBJECT side): a direct match on a
        `T:*` grant hits probe 3; a flow-through threads a bridge hop when the
        recursion reached the userset via its own `w_all` node. Stated over `hEC`
        (edge-completeness) + `hbr` (the bridge hypothesis). Needs no fuel bound.
    - **Correspondence: COMPLETENESS CLOSED operationally** (2026-07-10,
      `GraphIndex/ObjStarClosure.lean`, sorry-free, axiom-clean). The admitted,
      bridge-complete write-closure `WildReachedAdmitted` (grant edge AND
      subject-endpoint bridge cycle-admitted — the "no wildcard-own-shape cycle on
      subjects" fragment) discharges **both** operational hypotheses of the
      completeness core: `hEC` via `wildReachedAdmitted_edge_complete`, and `hbr` via
      **Lemma A** (`wall_reach_isObjectWildcard`: a reachable `w_all` node forces a
      declared object-wildcard shape, using `ObjStarValid`) + **bridge-completeness**
      (`wildReachedAdmitted_bridge_complete`). Result: `graph_complete_objStar`
      (`sem` @ `fuelBound` ⇒ probe 1 ∨ probe 3), operationally closed.
    - **Correspondence CLOSED — `graph_correct_objStar` (full `check = sem`). ✅ DONE
      (2026-07-10)** (`GraphIndex/ObjStarClosure.lean`, sorry-free, axiom-clean
      `[propext, Classical.choice, Quot.sound]`). The remaining SOUNDNESS side +
      top-level glue were delivered exactly as designed below:
      (1) the **fuel-bounded soundness assembly** — the tight `m ≤ 2|T|+1 ≤ fuelBound`
      bound. `trail_compress_nodup` (State.lean) compresses to a **nodup** trail;
      `grantReach_of_trail` was strengthened to bound `m ≤ (subjNode s :: l).countP
      NodeKey.isPlain` (every `GrantReach` hop's *source* is a `plain` node — `w_all`
      nodes are consumed mid-hop by a grant+bridge pair, never a source); the
      plain-node accounting (`ensureBridges_plainCount` / `writeWild_plainCount_le` /
      `wildReachedAdmitted_plainNodes`) gives `plain-nodes ≤ 2|T|`; `nodup_countP_le`
      + `NodeKey.isPlain` glue the count of a nodup trail's plain vertices to `2|T|`.
      (2) the **top-level `check = sem` glue** — route the read to `probeNonDerived`
      (pure-direct), kill probes 2,4 (`w_any` subject never an edge source,
      `wildReached_edge_source_ne_wAny`), glue probe 1 ∨ probe 3 via `reach ↔ NReaches`
      to `graph_complete_objStar` (backward) and the fuel-bounded `GrantReach` chain
      (forward). Mirror of `graph_correct_direct` / `graph_correct_bareStar`. **W1b is
      now closed end-to-end (soundness + completeness). Next: W1c.**
  - **W1c — userset stars (in-bridges + `instances`). ✅ DONE (2026-07-10)** —
    `graph_correct_usStar` (`GraphIndex/UsStarClosure.lean`, sorry-free, axiom-clean
    `[propext, Classical.choice, Quot.sound]`): full `check = sem` on the userset-star
    fragment. The three remaining pieces were delivered as designed:
    (1) **fuel-bounded soundness assembly — SIDESTEPPED via T0a stability.** The W1b
    plain-node count does NOT transfer (a userset-star grant's source is a `w_any` node,
    an in-bridge consumes a `w_any` target, and the chain over-counts an in-bridge the
    `sem` derivation absorbs). Instead `sem_of_usStar_probe` discharges the fuel
    obligation via `sem_fuel_stable`: the chain gives `semAux` at fuel `m` for SOME `m`,
    and `sem = semAux (max m fuelBound) = true` by `semAux_mono` then stability — no
    tight `m ≤ fuelBound` bound needed. Reusable for later W-stages.
    (2) **the admitted bridge-complete closure** `UsStarReachedAdmitted` (grant +
    guarded per-endpoint in-bridge admission) discharges `hEC`
    (`usStarReachedAdmitted_edge_complete`) and `hib`
    (`usStarReachedAdmitted_hib`) via the **liveness invariant**
    `usStarReachedAdmitted_inbridge_live` (every live bridged-in node has its in-bridge —
    it entered `nodes` as a write endpoint, so `ensureInBridges` ran on it) +
    `isSWU_of_storeValid`.
    (3) **top-level glue** `graph_correct_usStar` (probe 1 ∨ probe 2, probe 2 LIVE for
    usersets / dead for bare via `usStarReached_edge_source_char`; probes 3,4 dead via
    `usStarReached_edge_target_ne_wAll`). Mirror of `graph_correct_bareStar`.
    **Correctness fix:** `reach_of_semAux_us`'s `hib` was reformulated to be GUARDED by
    the concrete instance node having an in-edge — the prior unconditional form is FALSE
    (a name in `instances T q T` may occur only with a predicate ≠ P, so `⟨T,inst,P⟩` is
    never bridged; `sem` only flows through `inst` when `rec T inst P = true`, which
    forces a stored P-grant → the in-edge). T3/T6 widened
    (`backend_equivalence_usStar` / `exclusion_effective_usStar` /
    `no_ghost_grant_usStar`). **W1 (wildcard bridges) is now complete across all three
    sub-stages. Next: W2.** (prior-increment notes below.)
  - **(prior) W1c — userset stars. BOTH SEMANTIC CORES CLOSED; write model + edge
    characterization done.**
    - **Correspondence: BOTH SEMANTIC CORES DONE** (`GraphIndex/UsStarCorrect.lean`,
      sorry-free, axiom-clean). The read reduces to probe 1 ∨ probe 2 (objects star-free
      ⇒ probes 3,4 dead; probe 2 LIVE — a userset query subject's `wAny(s.shape)` sees
      userset-star direct grants, unlike W1b).
      * *Completeness* (`reach_of_semAux_us`, `sem ⇒ probe 1 ∨ probe 2`): fuses W1a's
        probe-2 disjunction with the `concrete → w_any` in-bridge threading. Stated over
        `hEC` (edge-completeness) + `hib` (in-bridge completeness). New leaf elims
        `directLeaf_elim_us` / `mog_elim_us` admit the userset-star direct-match and
        `instances`-branch disjuncts; `instances_ne_star` supports the flow-through.
      * *Soundness* (`UsStarReach` + `semAux_of_usStarReach` + `usStarReach_of_trail`):
        the in-bridge-absorbing chain. **KEY FINDING: an in-bridge hop needs NO instance
        witness for soundness** — a concrete reaching a userset-star grant via its
        in-bridge matches the grant *directly* in `sem` (a shape-match, unconditional),
        so the chain carries no `instances` and the trail lemma needs no in-bridge
        soundness. The genuinely-new lift `semAux_lift_us` absorbs a userset-star
        intermediate via the outer subject's `instances`-branch flow-through (witness
        discharged by `objectName_mem_instances` — every intermediate is a tuple object).
    - **Remaining (the assembly + closure, sharply isolated):** (1) fuel-bounded
      soundness assembly — `usStarReach_of_trail` gives existence; the `isPlain`-source
      count (W1b) needs ADAPTING since a userset-star grant's source is `w_any` not plain;
      (2) the admitted bridge-complete closure discharging `hEC`/`hib` — `hib` (in-bridge
      completeness = `instances`-coverage) is the contentful part; (3) top-level glue.
      Detail in PROOF_STATUS "W1c BOTH SEMANTIC CORES CLOSED".
    - **(prior) attack-first done + write model + edge characterization:**
    - **Attack-first (machine-checked, no surprise):** `check = sem` verified on 12
      userset-star scenarios incl. the sharp endpoint-exclusion cases. Finding: a
      group name is in `sem`'s `instances` iff it appears in a TUPLE (not merely as a
      query endpoint), which is EXACTLY when the store-built graph has that concrete's
      in-bridge — so store-bridges ↔ `instances` agree by construction. No refutation
      (unlike W1b's bridges-mandatory finding — the W1c design was confirmed as-is).
      The one apparent divergence was an admission-invalid tuple, re-confirming
      StoreValid is load-bearing. See PROOF_STATUS "W1c STARTED".
    - **Write model DONE** (`GraphIndex/UsStarWrite.lean`, axiom-clean): the faithful
      `concrete → w_any` in-bridge for declared subject-wildcard userset shapes
      (`Schema.isSubjectWildcardUserset` = `bridged_in_shapes`), `writeUsStar`
      (out-bridges then in-bridges then cycle-rejected grant), `structInv_writeUsStar`,
      and the `UsStarReached` closure with `usStarReached_structInv`.
    - **Edge characterization DONE** (`GraphIndex/UsStarCorrect.lean`, axiom-clean):
      `usStarReached_grant_or_bridge` — every edge is a grant, a `w_all → concrete`
      out-bridge, or a `concrete → w_any` in-bridge.
    - **Remaining (the genuinely hard core):** the in-bridge-absorbing chain (a
      `concrete → w_any` in-bridge + the userset-star grant out of `w_any` = one
      generalized hop, keyed through `instances`), the `instances`-branch of
      `memberOfGranted`, probe 4 (star userset query subject), bridge-completeness
      (= `instances`-coverage), and the fuel-bounded assembly — NB the `isPlain`-source
      argument needs re-checking, a userset-star grant's source is `w_any` not plain.
      Detail in PROOF_STATUS "W1c STARTED".
  - **Attack first (house move):** before proving, try to refute the widened
    statement on W1a — e.g. a star query subject (`s.name = STAR`) mixes
    probe 1 (exact star tuple) with flow-through `memberOfGranted`; check the
    intensional D1 branch against the probes on a concrete example via `zcli`
    or `#eval` before trusting the statement.
- **W2 — rule routing (untainted boolean-free structure).** `computed`, `union`
  of untainted operands, and TTU defs: writes route onto rule-derived families
  (the Python `RuleSet.apply` / leaf-routing semantics), materializing the
  extra closure edges. Widens the fragment to the full *untainted*
  `GraphAccepts` scope. Key content: rule-edge soundness/completeness vs
  `evalE`'s `computed`/`ttu`/`union` cases (TTU parents are STORED tupleset
  tuples — the storage-leaf/rule-leaf split).

  **STARTED (2026-07-10): attack-first + write model DONE.** The modeling
  discovery (from `RuleSet.apply` / `_rewrite_rule` / `_emit_expr`): the untainted
  graph does NOT add edges *between* relation nodes — **a raw write is expanded into
  its rewrite-closure** (Computed/TTU rewrites, fan-in through unions, iterated to a
  fixpoint) and each resulting triple is a plain direct edge; the ≤4-probe read is
  unchanged. Attack-first (machine-checked `#eval` vs `sem`, deleted after) confirmed
  the design on a computed / chained-computed / ttu(±) / union / userset-flow corpus —
  no refutation. **Write model:** `GraphIndex/RulesWrite.lean` (sorry-free,
  axiom-clean) — `RRule`/`exprArms`/`schemaRewrites` (rule extraction), `rewriteStep`/
  `rewriteClosure` (the bounded fixpoint), **`writeRules`** (fold `writeDirect` over the
  closure), full-`Inv`/residue-free/quiescence preservation (`inv_writeRules` etc.), and
  the W2 write-closure `ReachedByRules` + `reachedByRules_inv`. Reuses ALL W1
  `writeDirect` machinery. **Remaining (the read correspondence — deferred next
  increment):** (1) fragment predicate `UntaintedSchema` (⇒ `taintedKeys=[]` ⇒ route to
  `probeNonDerived`) + `StoreValid` analog; (2) **`TupleChain over T* ↔ sem over T`** —
  the rewrite-closure ↔ `computed`/`ttu`/`union` recursion (soundness: a rewrite hop is
  absorbed by the matching `evalE` case, TTU via the userset-flow lift; completeness: the
  recursion is a rewrite chain; fuel via the W1c T0a-stability sidestep); (3) top-level
  `graph_correct_rules` + T3/T6 widening. See PROOF_STATUS "W2 STARTED".

  **ATTACK-FIRST FINDING (2026-07-10, machine-checked): the naive W2 fragment is
  UNSOUND — `check ≠ sem` without a storage-only tupleset condition.** A TTU whose
  tupleset relation is `computed` (untainted but NOT directs-only) makes the graph
  rewrite-fanout fire the TTU rule on a *rewrite-produced* triple, while `sem`'s
  `ttuLeaf` reads only STORED tuplesets → divergence (counterexample + agreeing
  control in PROOF_STATUS "W2 — attack-first KILLS the naive fragment"). This is
  exactly `zanzibar_utils_v1.py:_validate_ttu_tuplesets`; **`GraphAccepts` clause (3)
  does NOT catch it** (a computed tupleset is untainted, `isDerived = false`), so the
  W2 fragment needs the *stronger* directs-only condition. Landed axiom-clean
  (`GraphIndex/RulesCorrect.lean`): **`directsOnly` / `TtuTuplesetsDirect`** (faithful
  `_validate_ttu_tuplesets`), `exprArms_directsOnly` (directs-only ⇒ no rewrite arms),
  `no_rewrite_outputs_tupleset`, rewrite-closure structure (`rewriteClosure_object`
  object-preservation, `rewriteClosure_seed`), and the payoff **`closure_tupleset_is_
  seed`** (a closure tuple on a tupleset relation is the raw seed — the storage-only
  semantics `ttuLeaf` needs). The W2 fragment predicate is now
  `UntaintedSchema ∧ TtuTuplesetsDirect`. Resume → the reachability↔`sem` core above
  (fragment pinned); attack-first the computed-case closure-saturation first.

  **SOUNDNESS CORE DONE (2026-07-10, `GraphIndex/RulesSound.lean`, sorry-free,
  axiom-clean).** The heart of the W2 soundness half:
  **`semAux_of_rewriteClosure`** — every rewrite-closure tuple `u ∈ rewriteClosure S t`
  of a stored `t` is a `sem` membership `u.subject ∈ (u.object, u.relation)` at some
  fuel, i.e. **the rewrite-closure realises `evalE`'s computed/ttu/union recursion**. A
  generalise-over-`cur` closure induction: seed = direct self-grant (`semAux_seed`);
  computed = the predecessor's membership under the `computed` arm, fuel `+1`; ttu =
  `ttuLeaf`'s stored-tupleset **direct disjunct** on the seed (`closure_tupleset_is_seed`
  forces the tupleset predecessor to be the raw `t ∈ T` — where `TtuTuplesetsDirect`
  earns its keep); union = a true arm makes the OR-tree true (`evalE_{direct,computed,
  ttu}_arm`). **New faithful hypothesis `NodupKeys S`** (declared keys distinct — the
  Python schema is a dict; `lookup_of_mem` is the payoff, `WF` doesn't give it) — carry
  it into W4. Fragment consequence lemmas: `untainted_noExclAll` (⇒ `semAux_mono`),
  `stratifiable_untainted` + `storeDeclared_of_validRules` (⇒ `sem_fuel_stable`).
  **SOUNDNESS DIRECTION CLOSED (2026-07-10, `GraphIndex/RulesChain.lean`, sorry-free,
  axiom-clean).** The stated blocker — `semAux_lift` GENERALISED to `UntaintedSchema`
  (`semAux_lift_untainted`, via `evalE_lift`: direct = DirectCorrect logic, computed =
  fuel IH, ttu = `ttuLeaf_elim`/`_intro_rec` stored-parent loop, union = OR) — plus chain
  composition (`semAux_of_ruleChain`, base = `semAux_of_rewriteClosure`, step = the lift,
  fuel existential) + preservation lemmas (`rewriteClosure_subjectName`/`_rel_ne_bare`) +
  **`sem_of_rules_reach`** (graph reachability ⇒ `sem`, fuel via the T0a-stability
  sidestep).

  **W2 FULLY CLOSED — `graph_correct_rules` (full `check = sem`). ✅ DONE (2026-07-10)**
  (`GraphIndex/RulesComplete.lean` + `RulesSaturate.lean`, sorry-free, axiom-clean
  `[propext, Classical.choice, Quot.sound]`). The completeness direction + assembly were
  delivered as designed:
  - **Attack-first (machine-checked, deleted): closure-saturation HOLDS at the `|keys|+1`
    bound** — stressed against mutual-`ttu` cycles + predicate-ratcheting unions whose
    *distinct* reachable count exceeds `|keys|+1` (`schemaRatchet2`: 6 > 4). The **rewrite
    DEPTH**, not the count, is bounded by `|keys|`; no refutation. Saturation held even for
    cyclic schemas (which `RewriteRanked` excludes — so it is sufficient, not necessary).
  - **`RulesComplete.lean` increment A** (admitted W2 closure): `FoldAdmits` +
    `foldl_writeDirect_edge_complete`, `ReachedByRulesAdmitted`,
    `reachedByRulesAdmitted_edge_complete` (every closure tuple's edge present) +
    `_seed_edge`.
  - **`RulesSaturate.lean`** (increment B): `RewriteRanked` (faithful rewrite-acyclicity /
    stratification) + the rewrite-layer algebra (`stepN`, `mem_aux_of_stepN`,
    `stepN_of_mem_aux`) + rank bound (`rwKey_rank_lt`, `stepN_rank_ge`) →
    **`rewriteClosure_saturated`**.
  - **`RulesComplete.lean` increment C** (core + assembly): `nreaches_of_semAux_rules`
    (`sem ⇒ reach`, fuel × def-expr induction; `computed` via the last-edge surgery
    `nreaches_relation_rewrite`/`nreaches_last` + saturation; `ttu` via the depth-1
    `rewriteStep_mem_closure`; direct/union verbatim). **Completeness needs NO
    `TtuTuplesetsDirect`** (soundness-only). Assembly **`graph_correct_rules`** (route +
    probes 2–4 dead via `reachedByRulesAdmitted_edges_plain` + glue).
  - **T3/T6 widened** (`Equiv.lean`): `backend_equivalence_rules` /
    `exclusion_effective_rules` / `no_ghost_grant_rules`.
  W2 fragment: `WF ∧ UntaintedSchema ∧ TtuTuplesetsDirect ∧ NodupKeys ∧ RewriteRanked ∧
  StoreValidRules ∧ StarFreeStore`. **W1 + W2 now both closed; next: W3** (derived
  reconcile / residue path). Combined generality lands at W4.
- **W3 — derived reconcile (the residue path).** Faithful `reconcile` output
  per derived key (residue `(stars, neg, upos)` = the §7.6 semantics), the
  in-transaction cascade over the outbox, and the cross-key hazard (an edge
  write re-reaching an existing residue key re-reconciles it). Closes full
  T2a (`Inv` incl. I6 across reachability-affected keys) and the derived-read
  half of T2b (residue = `sem` via the T1 MemberSet algebra + `negEdgeFree`
  edge-hit disjointness). T5 becomes contentful (non-empty outbox drained).

  **Sub-staging (designed 2026-07-10):** W3a star-free bare booleans → W3b
  userset subjects (`upos`) → W3c star data (`stars`/`neg`) → W3d multi-stratum
  cascade (cross-key re-reconcile hazard + contentful T5 drain). W3a is the
  "zero residue content" analog of W1a's "zero bridges".

  **W3d — the multi-stratum cascade. DESIGN COMMITTED (2026-07-11e); W3d-1a first.**
  Model source: `run_cascade` (`processor.py:694-740`), `_map_deltas_to_keys`
  (`:585-652`), `_fan_out` (`:654-692`), `_emit` (`core.py:31-44` — one outbox row per
  materialized closure-pair flip, inside the writing transaction, endpoints
  denormalized at emission), `outbox.py`, `advance_index` (`connectedstore/apply.py:
  79-87`: `wm` read BEFORE the row loop, `run_cascade(wm)` after — so the next txn's
  frontier starts past everything this txn emitted, including the processor's own
  rows); boolean spec §5.1–5.2.

  **Modeling decisions (each with its faithfulness note):**
  1. **Delta coalescing — one outbox row per ACCEPTED ROUTED EDGE, carrying the edge's
     object node.** Python emits per closure-pair flip; the model materializes no
     closure. For a routed edge `a→b` the Python rows' object ends are `{y : b ⇝ y}`,
     which the model recovers at CASCADE time as `{d.node} ∪ {v ∈ σ.nodes : reach
     d.node v}` — a superset of the write-time set (edges are add-only inside a txn),
     and extra keys only trigger idempotent reconciles. **Per-SEED coalescing is WRONG
     (design-phase attack finding, analytic):** a computed rewrite routes the seed onto
     sibling family nodes (`editor@doc:1` also lands `viewer@doc:1` when
     `viewer := editor or …`) with NO graph edge from the seed's object node to the
     sibling node — the seed-node reach cone misses the sibling operand key. So
     `writeLoggedRules` = W2's `writeRules` fold with a `pushDelta (objNode u.object
     u.relation) u.relation` per accepted rewrite-closure member `u`.
  2. **Fresh ids**: `nextDeltaId σ = max (maxOutboxId σ) σ.watermark + 1` — strictly
     above BOTH existing rows and the watermark (plain `maxId+1` could mint a
     born-drained row if the outbox were ever compacted below the watermark).
  3. **Processor emission IS modeled**: a reconcile pass pushes ONE row at its derived
     key (`objNode ⟨dt,on⟩ R`, `R`) — coalescing its per-flip rows, which all share
     that object end by R-node terminality (`reachedByW3c_Rnode_not_source` under
     `hterm`). This is what makes the leftover check contentful (decision 5).
  4. **The key mapping** `affectedKeys S σ d`: over candidate object nodes
     `v ∈ {d.node} ∪ reach-cone σ (d.node)`, plain ∧ `name ≠ '*'`, emit `(v.type, R,
     v.name)` for every derived `(v.type, R) = some e` with `v.pred ∈ computedRefs e`.
     = `_map_deltas_to_keys`'s LeafFamily branch + `_fan_out`'s `via='computed'`
     branch, restricted to the fragment (`hLU`: operands are untainted computed refs;
     the ttu/userset/tupleset-ttu dependent branches are out of fragment by
     `hterm`/`hRootB`). The subject-level cheap path (`keys[key] = subject set`,
     `reconcile_subject`) is NOT modeled — the model always full-object reconciles
     (Python's general path; the cheap path is an optimization with its own §5.4
     escalations to full).
  5. **The loop**: single stratum ⇒ `rounds = len(strata) = 1`: one round (read rows
     above the watermark, map to keys, one full-object `W3cJob` per key), then the
     QUIESCENCE CHECK — Python re-maps the rows above the round frontier and RAISES
     on any leftover key (`:729-739`). Model the raise as a REJECT branch (state
     unchanged, like `writeDirect`'s cycle reject): `runCascade` advances the
     watermark past everything iff the post-round leftover maps to no keys, else
     identity. **T5 then has two halves:** (a) `runCascade_no_abort` — on the fragment
     the reject NEVER fires (a pass-emitted row's object end is a terminal derived
     R-node: empty reach cone by terminality, own pred derived ⇒ not an operand ⇒
     `affectedKeys = []`); (b) post-cascade `Quiescent` — the watermark advance is
     JUSTIFIED by (a), not asserted (the old `cascade_converges` sin). `_bumped`
     fan-out is a single-stratum no-op (no derived dependents under `hLU`) — arrives
     with W3d-2.
  6. **Add-only STORE**: the model has no store removes; the remove-side hazards
     (operand removal re-reconcile, `neg` pruning after subject-node GC `:616-620`,
     REMOVED deltas) are OUT OF SCOPE for all of W3d-1 and recorded as fragment
     conditions.
  7. **The W3d pass is the DIFFING edge audit (added 2026-07-11f — attack finding).**
     The naive W3d-1b read statement over the add-only pass was REFUTED by `#eval`:
     `viewer := member ∖ banned` with NO star grants — write member(alice) → cascade
     (edge materialised, alice uncovered) → write banned(alice) → cascade (key
     re-mapped, pass ran) leaves the edge STALE: `check = true ≠ sem = false` at a
     fully-drained state. An add-only fold cannot retract an edge whose guard flipped
     down; Python does (`reconcile_subject`: `¬want_edge ∧ has_edge ⇒
     _write_derived(add=False)`, `processor.py:359-367`). W3d's pass is
     `reconcileStarsKeyD` (`GraphIndex/ReconcileDiff.lean`): residue recompute, then
     per candidate `want ⇒ writeDirect`, `¬want ⇒ removeEdgePair` (ALL copies — the
     refcount reaching zero; node GC modeled away, read-safe). W3a–W3c keep the
     add-only pass — their chains hold the store fixed, so `checkFn = sem` at every
     pass start makes the removal branch provably dead there. NB the W3a SHADOW does
     not extend over diffing passes, so the W3c `checkFn = sem` bridge does NOT
     transfer pointwise to W3d states — 1b re-derives its read bridge over the
     interleaved closure.

  **Sub-staging:**
  - **W3d-1a — the scheduling layer. ✅ DONE (2026-07-11e)** (`GraphIndex/Cascade.lean`,
    sorry-free, axiom-clean): `pushDelta`/`nextDeltaId`/`writeLoggedRules`/
    `affectedObjects`/`affectedKeys`/`frontierRows`/`runCascade` (jobs parametric per
    key: `W3cJobValid` + two-sided key coverage); the INTERLEAVED closure
    `ReachedByW3d` (empty → logged writes → cascades, any order — note: the W3a–W3c
    base-then-passes chain shape could NOT express a write after a pass, so the W3c
    master/`Inv` do NOT transfer pointwise; the W3d replacement is 1b's settledness);
    `EvalEq` (schema/edges/nodes/residue — the read-relevant core) + the full
    congruence spine (logged write core = `writeRules`, logged batch core =
    `reconcileJobsC`); T5 halves (a) `runCascade_no_abort` (the reject branch is dead
    at one stratum: pass rows sit at terminal derived R-nodes — terminality re-proved
    by direct induction over the interleaved closure — and derived preds are not
    operands by `hLU`) + (b) `cascade_drains` (earned `Quiescent`). Attack-first
    `#eval` (recorded in the file header): full-grid `check = sem` at cascaded states,
    live cross-key hazard remap, PRE-cascade staleness (`check ≠ sem` mid-txn —
    fixing the 1b claim scope to cascaded states), pass-row leftover ↦ `[]`. The
    deferred `reachedByW3d_inv` (T2a carry) lands with 1b settledness. Detail:
    PROOF_STATUS 2026-07-11e.
  - **W3d-1b — fan-out completeness (the cross-key re-reconcile hazard as a
    THEOREM).** A logged write whose new edges semantically change an EXISTING
    derived key maps to that key: a `sem` flip ⇒ some operand's `graphRec` changed ⇒
    a new reachability pair into an operand node ⇒ that pair's head lies in some
    routed delta's reach cone ⇒ `affectedKeys ∋ key`. Converts `W3cComplete`'s
    row-existence and ∃-covering clauses from batch HYPOTHESES into consequences of
    the cascade construction.
    **STARTED (2026-07-11f):** the attack pass killed the add-only model (decision 7,
    the diffing pass landed, Cascade re-greened, T5 re-earned), and the cascade-leg
    settledness core is PROVED: `graphRec_reconcileKeyD_inert` (the diffing fold is
    operand-read-inert both directions off its terminal R-node — removals are
    in-edges of a non-source, `nreaches_remove_terminal`), guard fold-invariance
    (`wantEdge_reconcileKeyD_inert`), and **per-key edge EXACTNESS**
    (`reconcileStarsKeyD_edge_char`): one full-object pass makes the key's derived
    edge set exactly `{c ∈ cands : checkFn ∧ shape ∉ fresh stars}` plus untouched
    non-candidate edges — candidate history erased, the wholesale re-settle as a
    theorem.
    **CORE DONE (2026-07-11g, `GraphIndex/CascadeStable.lean`):** fan-out completeness
    PROVED in contrapositive form (`writeLeg_checkFn_stable`: an unmapped key's operand
    reads/guard are unchanged by a logged write — route `nreaches_factor` →
    `writeLoggedRules_edge_delta` → `mem_affectedKeys`; attack found the OUT-of-fragment
    refutation: object-star writes flip probe 3 at every object while mapping no keys,
    so plain edge targets / `BareStarStore` are load-bearing,
    `reachedByW3d_edges_target_plain`). The W3d READ BRIDGE proved at EVERY state
    (`UntaintedShadow` — a rules-admitted state on the CURRENT store differing only in
    edges into terminal `DerNode`s; the write-leg ADMISSION transfer is the new content;
    `checkFn_eq_sem_w3d`, mid-batch included via `untaintedShadow_reconcileJobsD`).
    Settledness TRANSPORT proved: `writeLeg_sem_stable` (an unmapped key keeps its
    MEANING — the double-bridge trick), `SettledKey` + `settledKey_writeLeg` +
    `settledKey_cascade_untargeted` (rows write-inert; `writeLeg_derived_inedges_eq` =
    model-level I5 exclusivity). Detail: PROOF_STATUS 2026-07-11g.
    **✅ CLOSED (2026-07-11h, `GraphIndex/CascadeSettle.lean`):** the edge-holder
    coverage clause attack-CONFIRMED load-bearing (a pre-leg STALE holder missing from
    `cands` survives the diff audit — `check ≠ sem` at a fully-drained state; benign
    for `sem`-true holders); `ReachedByW3dC` (the coverage chain: per-job
    `W3dJobCoverage` = edge-holders ⊆ cands + `sem`-completeness of
    `cands`/`negCands`/`uposCands`, Python's per-pass audit re-enumeration) with
    projection to `ReachedByW3d`; `settledComplete_cascade_targeted` (the LAST
    targeting job wholesale-rewrites the row and diff-audits the edges, all guards
    read at mid-batch states via the bridge; `reconcileJobsD_key_edge_sem` = batch
    edge origin: `sem`-true or pre-leg); `CompleteKey` (per-key completeness half:
    row existence, uncovered-edge, `upos`, `neg` membership) + its write-leg/
    untargeted-cascade transports; the DIRTY-OR-SETTLED invariant
    `reachedByW3dC_settled` (empty case via `sem_nil_derived_false`); the W3d reach
    collapse (`reachedByW3d_reach_collapse_root` via `Rnode_source_bare` +
    `edge_target_ne_bare` over the interleaved chain); **`graph_correct_w3d`** at
    every fully-drained state (`cascadeKeys = []`, produced by every accepted cascade:
    `cascade_drains` + `cascadeKeys_nil_of_quiescent`) + T3/T6 `*_w3d`. Deferred to a
    later increment: `reachedByW3d_inv` (the T2a carry over the interleaved chain).
    Detail: PROOF_STATUS 2026-07-11h.
  - **W3d-1c — the audit enumeration from state + `reachedByW3d_inv`. ✅ CLOSED
    (2026-07-12b) — piece A ✅ (2026-07-11j), piece B core ✅ (2026-07-12), piece B
    tail ✅ (2026-07-12b). W3d-1 (single stratum) is COMPLETE.**
    * **(A) `reachedByW3dC_inv` ✅ DONE (2026-07-11j)** (the deferred T2a carry — the
      full 8-clause `Inv` over the interleaved chain, `GraphIndex/CascadeInv.lean`,
      sorry-free, axiom-clean). Parts 3a/3b (2026-07-11i): `reachedByW3d_structInv`
      (schema/nodeEnc/edgesClosed/**acyclic** — acyclicity FREE, `writeDirect`
      cycle-rejects + `removeEdgePair` shrinks reach) and `reachedByW3d_residueHygienic`
      (the edge-FREE I6 clauses `negStarCovered`/`uposNegDisjoint` —
      `reconcileResidueKey`'s filters give them by construction), BOTH with NO fragment
      hypotheses. Part 3c (2026-07-11j): **attack-first REFUTED the plain-chain
      statement** (`#eval`, recorded in the CascadeInv header) — a stale non-candidate
      edge survives the diff audit while a later pass writes its holder into `neg`, so
      `negEdgeFree` is FALSE over plain `ReachedByW3d` and the invariant lives on the
      COVERAGE chain (the coverage clauses are load-bearing for the INVARIANT, not just
      for `graph_correct_w3d`). Proof: `reachedByW3d_residueDeclared` (rows only at
      declared derived keys, no fragment hyps) + `reachedByW3dC_edgeHygienic` by chain
      induction — write legs keep rows/derived in-edges (model-level I5) with the W3d
      reach collapse; targeted cascade keys land `SettledKey` whose row verdicts
      contradict its edge verdicts (`neg` member `sem`-false vs edge holder `sem`-true,
      `upos` member userset vs bare edge source); untargeted keys keep row+in-edges
      verbatim (`reconcileJobsD_other_key_fixed`). Fragment carries as in
      `reachedByW3dC_settled`. **`reachedByW3dC_inv`** assembles StructInv +
      ResidueHygienic + EdgeHygienic into `Inv` at EVERY coverage-chain state — dirty
      keys and mid-drain states included.
    * **(B) the audit enumeration — CORE ✅ DONE (2026-07-12), tail remains**
      (`GraphIndex/CascadeEnum.lean`). Modeled `_leaf_concretes` + the audit set
      (`processor.py:394-441`) as a state-derived enumeration (`leafConcretes` = plain
      star-free nodes reaching an operand/`wAll` node, decoded; `edgeHolders` = incoming
      R-node concretes) and proved **`W3dJobCoverage` as a THEOREM** of it
      (`w3dJobCoverage_enumJob`, all four clauses). The spine: the per-leaf pointwise
      collapse `probeNonDerived_concrete_decomp` → `checkFn_eq_coveredFn_of_no_extra` (a
      subject hitting no concrete-specific probe reads as its shape-star, `evalE`
      congruence, exclusion-safe); `w3d_leg_context` rebuilds the read bridge +
      coverage-declaredness at any W3d state through the shadow; each clause is a
      contrapositive of the bridge fed through the collapse (clause (4)'s dead userset
      coverage fell out of `hcovDecl`'s contrapositive — no separate `wAny`-node lemma).
      **Statement fix (2026-07-11j):** clause (2) carries the UNCOVERED guard (without it
      unsatisfiable by finite jobs on covering stores — every fresh subject `sem`-true
      under a `T:*` grant, `#eval`-checked). Detail: PROOF_STATUS 2026-07-12.
    * **(B tail) the enumerated-cascade restatement ✅ DONE (2026-07-12b)**
      (`GraphIndex/CascadeEnum.lean`). `enumJobs S σ` = `(cascadeKeys S σ).filterMap`
      building each key's `enumJob`; `enumJobs_valid`/`_cover`/`_scope`/`_covg` discharge
      the four `ReachedByW3dC.cascade` hypotheses (validity via `w3cJobValid_enumJob` +
      the new star-free source analog `reachedByW3d_Rnode_source_name_ne_star`; coverage
      via `w3dJobCoverage_enumJob`; `mem_cascadeKeys_props` pins every cascade key to a
      declared derived key at a star-free object). **`ReachedByW3dE`** is the
      fully-operational scheduler chain (cascade legs run `enumJobs`, NO coverage
      hypotheses); `reachedByW3dE_toC` projects it to `ReachedByW3dC` (store hyps weakened
      along write prefixes, all fragment hyps threaded as premises). Payoff:
      **`graph_correct_w3dE`** (`check = sem`, fully-drained) + **`reachedByW3dE_inv`**
      (the full 8-clause `Inv`, every state) hold UNCONDITIONALLY — `W3dJobCoverage` is a
      theorem, not a hypothesis. Detail: PROOF_STATUS 2026-07-12b.
  - **W3d-2 — two strata (derived-reading-derived). ◐ OPENED (2026-07-12c,
    `GraphIndex/CascadeStrata.lean`).** Relax `hLU` to lower-stratum derived operands:
    the leaf dispatch routes derived operands through `probeDerived` (a real model
    extension — Python's `_EvalContext` dispatches `derived_check` →
    `widx._check_derived`, `derived_stars` → residue stars; `member_check` routes on
    tainted); `rounds = 2` with `_bumped` fan-out; per-stratum generalization of the
    shadow + inertness (a stratum-k pass is inert for stratum-<k reads); processor-
    emitted rows now MAP to dependent keys — the leftover check earns its round
    structure, and `stratify_topological` (T0b) supplies the settle order.
    **Done (12c)**: `graphRecR`/`checkFnR`/`coveredFnR` (the routed read),
    conservativity (`checkFnR_eq_checkFn`, `reconcileStarsKeyDR_eq`,
    `reconcileJobsLR_eq` — W3d-1 is the single-stratum image), `checkFnR_evalEq`
    (routed read = exactly the `EvalEq` core), the routed diffing pass, `runCascade2`
    (per-round frontier cursor, leftover reject), `ReachedByW3d2` (C-style two-batch
    closure), `reachedByW3d2_schema`. Attack-first: fully-drained `check = sem`
    SURVIVED cross-stratum union/exclusion/stars/userset-upos under both within-round
    orders and sync/async batching; mid-drain staleness real (fully-drained scope);
    within-round order not load-bearing; the E-chain `enumJobs` must add residue-named
    candidates (`_derived_leaf_neg_ids`, `processor.py:461-495`; old `upos` `:425-429`).
    **Done (12d)**: the scheduler structural layer over `ReachedByW3d2`
    (`reconcileJobsLR_outbox_sound` / `_edge_sound` / `_watermark`, R-node terminality
    over the two-round closure incl. the batch-transported round-stackable form,
    `outbox_le_frontierMax` cursor arithmetic); **T5 at two strata** —
    `runCascade2_no_abort` under `hLU2` (every computed operand of a derived def
    untainted OR a derived key with all-untainted operands; strictly wider than `hLU`,
    `hLU2_of_hLU`) + `cascade2_drains` (attack-first: on the 3-stratum
    `a := b∨y, b := c∨x, c := x∖y` `hLU2` is FALSE and the reject FIRES — round-2
    emission at `b` maps to key `a`; on the 2-stratum truncation `hLU2` TRUE / `hLU`
    FALSE, accept, `check = sem`); **per-stratum operand-read inertness** — a routed
    pass is read-inert at every OTHER key whatever its stratum
    (`check_reconcileStarsKeyDR_other` via `graphRec_reconcileStarsKeyDR_inert` +
    `probeDerived_reconcileStarsKeyDR_other`; guard form
    `checkFnR_reconcileStarsKeyDR_other`), on routed mirrors of the W3d-1b
    reach-inertness/closure/residue-other layer.
    **Remaining**: the stratum-staged shadow/settledness generalization, the read
    bridge → `graph_correct_w3d2`, the E-chain tail (with residue-named candidates).
    Detail: PROOF_STATUS 2026-07-12c/12d.

  **W3c ✅ CLOSED (2026-07-11d): `graph_correct_w3c` + T3/T6 (`*_w3c`) — star-carrying
  stores.** The read half assembled in `GraphIndex/ReconcileStarsComplete.lean`: **the
  LINCHPIN `coveredFn_declared`** (no ghost star coverage — a `sem`-covered shape is
  DECLARED: true computed leaf → `wAny`-sourced probe → first edge → materialised closure
  tuple → the star seed carries its subject → `restrictionMatches`' wildcard flag names a
  `wildcardShapes` entry), the `sem`-level row characterisation `w3c_row_char` (master
  provenance + `checkFn_eq_sem_bs` at the master base), and the batch completeness layer
  for the WHOLESALE residue recompute — `reconcileJobsC_row_isSome`,
  `reconcileJobsC_neg_complete`/`_upos_complete` with the **∀-targeting-jobs enumeration
  form** (attack-first `#eval` confirmed necessity: a second same-key pass with an
  incomplete `negCands` DROPS the exclusion), and `w3cComplete_derived_edge` (covered-filter
  survival + prefix-mid-state inertness + terminal admitted write). **T2b
  `graph_correct_w3c`**: `check = sem` on `W3cComplete` states over `BareStarStore` +
  `TtuStarFree`, subjects bare / star-BARE / userset (`hWSbare` = decision-15 bare-only
  declared shapes; userset coverage dead ⇒ userset read = `upos` exactly). T3/T6 `*_w3c`
  incl. `exclusion_effective_w3c` — a concrete subject excluded from UNDER a `T:*` grant
  (the space rule's `neg` actually excludes). Detail: PROOF_STATUS 2026-07-11d.

  **W3c ◐ WRITE HALF CLOSED (2026-07-11): `stars`/`neg` model + T2a with all-contentful
  I6 + guard canonicity (`GraphIndex/ReconcileStars.lean`).** The wholesale residue
  recompute `reconcileResidueKey` (`stars` = the star-subject `checkFn` filter — the
  pointwise form of `plan.stars_fn`; `neg` = covered ∧ expr-false; `upos` with its
  ¬covered guard), the covered-guarded edge fold (`want_edge = should ∧ ¬covered`) and
  the combined `reconcileStarsKey` (residue-THEN-edges, the faithful atomic unit).
  Three structural devices: the **covered-filter collapse** (`reconcileKeyC_eq_filter` —
  the covered guard is fold-constant, so the W3c edge fold IS a W3a `reconcileKey` on
  the filtered candidates; all W3a fold machinery transfers), the **shadow projection**
  (`reachedByW3c_shadow`), and **star-general operand-read inertness**
  (`graphRec_reconcileKey_inert`, NO `StarFreeStore` — all four probe targets of an
  untainted-key read differ from the terminal R-node, subject-generically incl. star
  subjects). `reachedByW3c_master` pins every persisted `stars` row to the canonical
  star set of the chain base AND guard canonicity (neg canonically expr-false, upos
  canonically expr-true, edge sources canonically expr-true ∧ uncovered — via
  `reconcileKey_edge_guard` + prefix-mid-state inertness). **T2a `reachedByW3c_inv`:
  full `Inv` with ALL FOUR I6 clauses contentful** (`negStarCovered`, `negEdgeFree` =
  the space rule cross-pass, `uposEdgeFree`, `uposNegDisjoint`) — no `StarFreeStore`
  hypothesis anywhere. Attack-first: 342-query grid incl. D1 flow-through coverage,
  nested boolean roots, permuted/duplicated candidates — no refutation.

  **W3c read half step 1 CLOSED (2026-07-11): the star-relaxed base equation.**
  `graph_correct_rulesBS` (`GraphIndex/RulesBareStar.lean`): W2's untainted `check = sem`
  re-proved over `BareStarStore` + `TtuStarFree` (no wildcard TTU parents — attack-
  CONFIRMED necessary: a star tupleset tuple needs W1c in-bridges the rule-routed write
  model does not materialise), with the query scope widened to star-BARE subjects (probe 1
  at the `wAny` source; probe-2 hits transfer to the concrete subject via
  `semAux_star_to_bare`). On top: `graphRec_base_eq_bs` (RestrictBase — `TtuStarFree`
  transfers to `S↾U` since the restriction preserves `schemaRewrites`),
  `graphRec_reduce_base_adm_bs` (ReconcileComplete — the plain-edges probe-killing
  shortcut replaced by transferring ALL FOUR probes, both probe targets carrying the
  untainted key `(dt, r')`), and `checkFn_eq_sem_bs` — the star-relaxed `checkFn ↔ sem`
  bridge the W3c `coveredFn`/`stars ↔ sem` correspondence consumes.

  **W3c read half step 2 part 1 (2026-07-11c): the batch scaffolding.**
  `ReconcileStarsComplete.lean`: `checkFn_eq_sem_w3c` (star-relaxed `checkFn=sem` on any W3c
  state, via `reachedByW3c_shadow` + `checkFn_eq_sem_bs`), and the `W3cJob`/`reconcileJobsC`/
  `W3cJobValid` batch layer (`_pres`, `_edges_mono`; one job settles stars+neg+upos+edges via
  the combined `reconcileStarsKey`). **Remaining for `graph_correct_w3c`:** (A) the LINCHPIN
  `coveredFn σ0 sh = true → sh ∈ wildcardShapes S` (attack-CONFIRMED true & needed for all three
  `probeDerived` branches — the `sem`-true bare-star ⇒ declared-shape fact; Route 2 = graph-level
  via `reachedByRules_edge_sound` + `restrictionMatches` wildcard flag), then (B) `W3cComplete`
  (with a row-existence coverage clause) + the assembly. Detail: PROOF_STATUS 2026-07-11c + HANDOFF.

  **W3b ✅ CLOSED (2026-07-11): `graph_correct_w3b` + T3/T6 (`*_w3b`) — userset `upos`.**
  The W3a bare-subject restriction LIFTED: userset subjects on derived keys are answered
  by the edge-free `upos` residue (blind-audit P4). Write model `reconcileUposKey`
  (per-candidate insert/remove fold, `putResidue`-only) + the congruence spine (`checkFn`
  reads only the edge/node core ⇒ CONSTANT across the upos fold) + the W3b read collapse
  in `GraphIndex/ReconcileUpos.lean`; the closure `ReachedByW3b`, the **shadow
  projection** (every W3b state has a W3a-admitted shadow with identical core — all W3a
  edge facts transfer with zero new induction), contentful-I6 `reachedByW3b_inv`
  (`uposEdgeFree` proved for real), `upos` soundness/persistence/completeness, and
  `graph_correct_w3b` (`check = sem` on EVERY star-free query) in
  `GraphIndex/ReconcileUposComplete.lean`; Step C corollaries in `Equiv.lean`.
  Attack-first: 180-query grid, pass-order insensitivity, idempotence, P4 non-leak,
  I6 edge-freeness — no refutation. Detail: PROOF_STATUS 2026-07-11 (W3b) + HANDOFF.

  **W3a ✅ CLOSED (2026-07-11): `graph_correct_w3a` + T3/T6 (`*_w3a`).** `check = sem`
  on every BARE-subject star-free query over a `W3aComplete` state (one `RootBoolean`
  derived key per untainted operand cone) — untainted via the base reduction, derived
  via the residue-empty edge probe glued by soundness (`reachedByW3aAdmitted_derived_
  edge_sound`) + completeness (`w3aComplete_derived_edge`). `GraphIndex/ReconcileComplete
  .lean`; Step C corollaries in `Equiv.lean`. **Scope finding (attack-first):** a userset
  subject on a derived key can be `sem`-true while the residue-empty read is `false`, so
  the derived-query claim is bare-subject only — usersets are W3b's `upos`. Detail:
  PROOF_STATUS 2026-07-11 (Step B+C) + HANDOFF.

  **W3a history (2026-07-10): attack-first + read collapse + write model DONE.**
  - **Attack-first (machine-checked `#eval` vs `sem`, deleted): the W3a
    residue-read ↔ `sem` correspondence HOLDS — no refutation.** Key modeling fact:
    on the star-free bare-subject fragment the processor stores **no residue row**
    (`stars = neg = upos = ∅` ⇒ `_store_residue` never fires), so the state stays
    `ResidueEmpty` and a derived relation only adds EDGES — a derived edge being
    structurally an ordinary `writeDirect ⟨s, R, o⟩`. W3a reuses ALL of W2's write +
    preservation machinery; the derived read collapses to a pure edge probe.
  - **Read collapse DONE** (`GraphIndex/Reconcile.lean`, axiom-clean):
    `probeDerived_residueEmpty` (the derived read on an empty residue is the bare edge
    probe — object-wildcard / `'*'`-subject / userset all read `False`),
    `probeDerived_ResidueEmpty`, `check_derived_ResidueEmpty` (routing: residue provably
    inert on W3a).
  - **Write model DONE** (`GraphIndex/ReconcileWrite.lean`, axiom-clean): `graphRec`
    (`= probeNonDerived`) + `GraphState.checkFn` (the compiled `check_fn` modelled as
    `evalE` reading the graph — on W3a every leaf dispatches to `leaf_check` =
    `widx.check`), `GraphState.reconcileKey` (guarded `writeDirect` fold: derived edge
    per candidate iff `checkFn`), its full `Inv`/residue-free/quiescence preservation,
    the W3a write-closure `ReachedByW3a` + `reachedByW3a_inv` (T2a `Inv` conjunct) +
    `reachedByW3a_residueEmpty` (the read-side hook).
  - **Read correspondence — TWO STRUCTURAL SPINES DONE (2026-07-11,
    `GraphIndex/ReconcileCorrect.lean`, sorry-free, axiom-clean `[propext]`).**
    - **`checkFn` ↔ `sem`-step reduction.** `ComputedOnly` (the W3a derived-def shape:
      boolean tree over `computed` refs); `evalE_computedOnly` (NO axioms — `evalE` on such
      a tree reads `rec` only at `(dt,on,·)`, so graph-recursion swaps for fuel-recursion);
      **`checkFn_eq_semStep`** — `checkFn = semAux (f+1)` of the derived key given the
      per-relation agreement `graphRec σ s dt on r' = semAux … f dt on r'`. **Reduces the
      reconcile guard `checkFn = sem`-membership to exactly that per-relation fact.**
    - **Reconcile edge characterization.** `reconcileKey_edges_mono` (the fold only adds
      edges), `reconcileKey_edge_sound` (every new edge is a candidate's derived edge
      `subjNode c → objNode ⟨dt,on⟩ R`), **`reachedByW3a_edge_sound`** (every W3a edge is a
      materialised rewrite-closure tuple or a reconcile derived edge). The W3a analog of
      `reachedByDirect_edge_sound` — the spine the bare-subject reach-collapse classifies
      each last edge against.
  - **Read correspondence — the bare-subject REACH-COLLAPSE spine DONE (2026-07-11,
    `GraphIndex/ReconcileCorrect.lean`, sorry-free, axiom-clean; 2 of 4 axiom-free).**
    - **Attack-first finding (analytic): the single-edge collapse needs `NoRuleOutputs S R`**
      (the W3a analog of W2's `TtuTuplesetsDirect`). A **union-rooted** `ComputedOnly` def
      (`member or (admin but not suspended)`) makes `exprArms` emit a `computed` rewrite
      `… ↦ R`, so W2's base rewrite-closure also lands (possibly **userset, non-bare**)
      tuples on the R-node — a genuine ≥ 2-hop path, so the collapse fails. `check = sem`
      still holds (both mechanisms agree — a proof-shape limit, not unsoundness); the
      collapse holds exactly on `inter`/`excl`-rooted defs (`exprArms … = []`).
    - `ReachedByW3a.reconcile` strengthened with `R ≠ BARE` (faithful). Generic
      **`nreaches_collapse_of_source_notarget`** (NO axioms — if every in-edge source of `v`
      has no in-edge, a path to `v` is a single edge). **`reachedByW3a_edge_target_ne_bare`**
      (every W3a edge target has a non-`BARE` predicate) ⇒ **`reachedByW3a_bareNode_no_
      inedge`** (a `BARE`-pred node is never an edge target). Assembly
      **`reachedByW3a_reach_collapse`** — a bare-subject path to `objNode ⟨dt,on⟩ R` is a
      single edge, given `hsrcbare` (every R-node in-edge source is bare — the isolated
      `NoRuleOutputs` gap).
  - **Remaining (the correspondence, sharply isolated) — resume here.** (1) ✅ **DONE
    (2026-07-11):** discharged `hsrcbare` via **`NoRuleOutputs S dt R`**
    (`GraphIndex/ReconcileCorrect.lean`, sorry-free, axiom-clean): on an `inter`/`excl`-rooted
    (`RootBoolean`) def no `schemaRewrites` rule outputs `(dt,R)` (`noRuleOutputs_of_root`, via
    `schemaRewrites_provenance` + `NodupKeys`) and no store tuple sits on it (`exprDirects_
    rootBoolean = []` ⇒ fails `StoreValidRules`), so the base rewrite-closure leg on the R-node
    is impossible and every R-node in-edge is a bare-sourced reconcile edge
    (`reachedByW3a_Rnode_source_bare`; `ReachedByW3a.reconcile` strengthened with bare-candidate
    `hcands`) — so `reachedByW3a_reach_collapse_root` fires unconditionally. (1.5) ✅ **DONE
    (2026-07-11): the flagged R-node-source subtlety RESOLVED + reconcile-edge reachability
    inertness** (`GraphIndex/ReconcileCorrect.lean`, sorry-free, axiom-clean). The derived R-node
    is never an edge SOURCE on the single-stratum fragment where R is *terminal*
    (`NoStoreSubjectR T R` = no stored userset-over-R subject, `NoTtuTarget S R` = R never a TTU
    target — the `PDerivedTTU` shapes are deferred): a rewrite-closure subject predicate is the
    seed's or a `ttu tr`, neither is R (`rewriteClosure_subject_pred_ne`), so
    `reachedByW3a_edge_source_ne_R` / `reachedByW3a_Rnode_not_source` (R-node has no out-edge).
    Payoff `reconcileKey_reach_inert` (via generic `nreaches_cons_inert`): one reconcile pass adds
    no reachability to a non-R-node — the **per-pass** inertness the multi-pass `hag` transfer
    folds over. Carry `NoStoreSubjectR`/`NoTtuTarget` (per derived R) into the W3a/W4 fragment.
    (1.75) ✅ **DONE (2026-07-11): multi-pass reconcile inertness folded to the untainted base**
    (`GraphIndex/ReconcileCorrect.lean`, sorry-free, axiom-clean `[propext, Quot.sound]`). The
    `reconcile` constructor now carries `hder : isDerived S (dt,R) = true` (faithful); the fold
    `reachedByW3a_reach_inert` peels one `reconcileKey_reach_inert` per pass down to the
    `ReachedByRules` base, giving `∀ {u v}, isDerived S (v.type,v.pred) = false → NReaches σ.edges
    u v → NReaches σ0.edges u v` for an untainted base σ0. Target-distinctness from `hder` (equal
    keys share `isDerived`); R-node-not-a-source from `reachedByW3a_Rnode_not_source` on the
    sub-derivation, via the schema-level terminal hypothesis `hterm : ∀ dt R, isDerived (dt,R) →
    NoTtuTarget S R ∧ NoStoreSubjectR T R` (carry into W3a/W4). **The reachability half of `hag`.**
    (1.9) ✅ **DONE (2026-07-11): the operand-read reduction to the untainted base**
    (`GraphIndex/ReconcileCorrect.lean` + `State.lean`, sorry-free, axiom-clean). The inertness
    fold is upgraded to a biconditional (`reachedByW3a_reach_inert_iff`, backward via the new
    general `NReaches.mono_subset` + the `σ0.edges ⊆ σ.edges` inclusion now carried by
    `reachedByW3a_reach_inert`), then lifted to the `probeNonDerived` read `hag` consults: the
    `reconcile` constructor gained two faithful star-free fields (`hcStar`/`honStar`) ⇒
    `reachedByW3a_edges_plain` (every W3a edge endpoint plain) ⇒ `probeNonDerived_plainEdges`
    (plain-edge read = probe 1) ⇒ **`graphRec_reduce_base`**: for every untainted operand `r'`,
    `graphRec σ s dt on r' = graphRec σ0 s dt on r'` on the untainted base. **`hag` is now a pure
    base-state W2 fact** — no residual W3a reasoning.
    (2) discharge the per-relation agreement `hag` — the **per-relation** untainted-correctness
    lemma (STILL the deeper BLOCKER, now W3a-free): with `graphRec_reduce_base` the operand read is
    the *base* read `graphRec σ0 s dt on r'`, so `hag` reduces to
    `graphRec σ0 s dt on r' = semAux … dt on r'` on a `ReachedByRules` σ0 — a W2 statement.
    `graph_correct_rules` proves whole-schema `UntaintedSchema`, too strong for W3's mixed schema.
    **Recommended route (design in HANDOFF.md step A): schema restriction** — evaluate on `S↾U`
    (tainted keys' defs removed; `UntaintedSchema` by taint-heredity), transfer `semAux` for
    untainted `r'` (confinement-style fuel×Expr induction), transfer the state (schema-field swap;
    `schemaRewrites` unchanged since `RootBoolean` defs emit no arms), and reuse W2 as a black box;
    fuel via the T0a-stability sidestep. Fallback: re-thread the W2 chain per-relation. NB
    `checkFn_eq_semStep`'s `hag` is now restricted to `computedRefs e` (2026-07-11 fix — the
    unrestricted `∀ r'` was undischargeable), so the assembly needs "every computed leaf of a
    derived def is untainted" as a fragment fact.
    (2.0) ✅ **DONE (2026-07-11): the schema-restriction foundation + `semAux` transfer**
    (`GraphIndex/RestrictBase.lean`) — `restrictUntainted`, `untaintedSchema_restrict`,
    `restrictUntainted_lookup`, `semAux_restrict` (the semantic heart), and the rewrite-fan-out
    preservation (`schemaRewrites_restrict` / `rewriteClosureAux_restrict`).
    (2.05) ✅ **DONE (2026-07-11): the fuel bridge, closed** (`GraphIndex/RestrictBase.lean`,
    sorry-free, axiom-clean). `rewriteClosure S t` (fuel `|S.keys|+1`) and `rewriteClosure (S↾U) t`
    (smaller fuel `|S↾U.keys|+1`) have **identical membership** (`rewriteClosure_restrict_mem_iff`).
    `⊇` unconditional (`rewriteClosureAux_mono` via the `stepN` layer algebra + `keys_length_le`);
    `⊆` by saturation of the `S↾U`-closure, whose `RewriteRanked (S↾U)` is built from
    `RewriteRanked S` by **rank compression** (`rewriteRanked_restrict`: count `S↾U`-keys ranked
    below `k`, bounded now by `|S↾U.keys|`), given the faithful side condition
    `RewriteMatchDeclared` (every rewrite's match key is a declared untainted relation — mirrors
    the compiler routing arms over declared operands).
    (2.1) ✅ **DONE (2026-07-11): Step A CLOSED — state transfer + base `hag` equation**
    (`GraphIndex/RestrictBase.lean`, sorry-free, axiom-clean). `foldAdmits_of_acyclic` (a
    `writeDirect` fold admits every write when each materialised edge lands in an acyclic target
    containing the running edges — order-insensitive, so the differing fold lists don't matter);
    `exists_admitted_restrict` (canonical `ReachedByRulesAdmitted σ' (S↾U) T` with `σ'.edges ≈
    σ0.edges` — both edge sets are the materialised closures, equal by the fuel bridge; admissions
    transfer via acyclicity of the shared target `σ0.edges`); **`graphRec_base_eq`** (the
    deliverable — `graphRec σ0 s dt on r' = sem S T ⟨s,r',⟨dt,on⟩⟩` for untainted `r'` on an
    admitted mixed-`S` base, via `probeNonDerived σ0 = probeNonDerived σ' = check σ' = sem (S↾U) =
    sem S`). Fragment premise `hRootB` (derived defs `RootBoolean`) supersedes `hDrop` and forces
    stored relations untainted. **Remaining in W3a:** (3) candidate completeness (an
    admitted `ReachedByW3aAdmitted`: every `sem`-member is a positive-leaf concrete) +
    assembly `graph_correct_w3a` (route → `probeDerived` → `check_derived_ResidueEmpty` →
    edge probe → `reachedByW3a_reach_collapse` → `checkFn_eq_semStep` + `hag` → `sem`) +
    T3/T6 widening. Detail in PROOF_STATUS "W3a read correspondence".
- **W4 — full-scope restatement.** The operational closure now covers
  `GraphAccepts`; name it `ReachedBy` and state the final `graph_correct` /
  `graph_reached_inv` / `backend_equivalence` / T6a (with real exclusion
  content) / T6b over it. This discharges the obligations whose false
  predecessors were deleted.
- **T0a**: ✅ DONE (2026-07-10) — see its section below.
- **Phase 6**: sorry gate to 0, audit as hard gate, graph-model conformance
  extension (above), final review doc.

---

## T1 — `setEngine_correct` — ✅ DONE (2026-07-09)

**Closed and axiom-clean.** `SetEngine/Correct.lean` is `sorry`-free; the
`opaque SetEngineModel.check` is a concrete expand model (`SetEngine/Eval.lean`). See
PROOF_STATUS "Session 2026-07-09 (T1 FULLY CLOSED)" for the full lemma list and the
tactic notes. Key wins vs. the original plan below:
- **`Id := SubjectRef`** (as the correction demanded — `MemberSet String` was unsound).
- **The confinement obligation evaporates.** `containsShape` never reads `pop`, so a
  **query-focused population** `popOf s σ = {s}` at `s`'s shape (else `∅`) makes
  `PopFocus`/`Grounded`/`WFp` hold *definitionally* — no `pos ⊆ U` induction. The
  distribution lemmas guarantee the probe answer is pop-invariant, so this focused
  population computes the same answers as the real global one.
- **T1 needs no WF/Stratifiable/AllValid** — the expansion equals `semAux` at every
  fuel; the hypotheses are retained (underscored) but unused.

The distribution core (`containsShape_*_focus`, below) was the genuinely hard,
previously-`FALSE`-then-corrected lemma; the leaves/structure/fuel inductions built on
it. **T3/T6a/T6b now route through T1∘T2b — real the moment T2b lands.**

### (original plan)

**Plan.** Replace `opaque SetEngineModel.check` with a concrete `expand`-based model:
`expandAux : Nat → … → MemberSet Id` (fuel-recursive like `sem`), booleans via
`MemberSet.union/intersect/subtract`, `check` = `containsStar/containsEntity/
containsUserset` of the query subject. Prove T1 by induction on fuel then on the AST.

**CORRECTION to Gemini:** its model used `MemberSet String` (ids = subject *names*).
That is **unsound** — `alice:user` and `alice:group` collide in `pos`. Use
`Id = String × String` (type, name) (or `SubjectRef`), and its `pop` had an unproved
injectivity `sorry`. Fix both.

**The intensional distribution — RESOLVED as a corrected lemma (2026-07-09), in
`SetEngine/Contains.lean`.** The naive law `containsShape (op M N) = containsShape M
⟨op⟩ containsShape N` under `WF` alone is **FALSE** — `#eval`-confirmed counterexample
with both operands `WF`: `a = {stars := {σ}}`, `b = {stars := {shape}, neg := {uid}}`
with `uid ∈ pop σ`, `σ ≠ shape`; both answer `false` for `shape` but `union a b`
answers `true`. The fix is the missing invariant **`PopFocus pop uid shape := ∀ σ,
uid ∈ pop σ → σ = shape`**. Proved, axiom-clean:
- `containsShape_union_focus` — needs `PopFocus` + `WFp` operands;
- `containsShape_intersect_focus` / `containsShape_subtract_focus` — additionally
  need **`Grounded pop uid shape m := uid ∈ m.pos → uid ∈ pop shape`**.

---

## T4 — `pathCount_addEdge` / `pathCount_removeEdge` — ✅ DONE (2026-07-09)

**Closed and axiom-clean.** `GraphIndex/Closure.lean` is `sorry`-free. The plan below was
executed: walk API (`pathsOfLength_pos_iff`) → pigeonhole vanishing
(`pathsOfLength_card_vanish`) → last-edge/monotonicity/no-back-path → recurrence
uniqueness (`rec_closed_form`/`rec_unique`) → `pathCount_addEdge`; `removeEdge` is its
inverse via `(g.removeEdge u v).addEdge u v = g`. Kept over ℕ (no ℤ needed) with **no**
custom axioms. Original plan retained below for the record.

### (original plan)

**Plan.** Replace `opaque pathCount`: add `[Fintype V]`, define
`pathsOfLength : Nat → V → V → Nat` (`0 ↦ [u=v]`; `k+1 ↦ ∑ w, dcount u w *
pathsOfLength k w v`), `pathCount = ∑ k ∈ Ico 1 (card V + 1), pathsOfLength k`,
`phat = pathCount + [u=v]`.

**CORRECTION to Gemini:** do NOT introduce the recurrence as an `axiom` (its
`phat_def`). A custom axiom about the opaque constant fails the C4 axiom-cleanliness
gate. Prove the recurrence as a LEMMA from the definition.

**Hard core:** `phat_recurrence : Acyclic g → phat u v = [u=v] + ∑ w, dcount u w *
phat w v`. From the definition this reduces to showing the boundary term
`∑ w, dcount u w * pathsOfLength (card V) w v = 0` — i.e. **no walk of length
`card V` exists in a DAG** (pigeonhole: such a walk repeats a vertex ⇒ a closed
subwalk ⇒ `pathCount x x > 0` ⇒ ¬Acyclic). This is the genuine combinatorial lemma;
our multigraph has no Mathlib `Walk` API, so it must be built (or bridged to
`Mathlib.Combinatorics.…`). Then `pathCount_addEdge` follows by algebraic expansion
of `(A + E_{uv})` using `phat_recurrence` and the DAG condition `v` cannot reach `u`;
deletion is the exact inverse in `(ℤ,+)`.

---

## T0a — `semAux_fuel_stable_step` — ✅ DONE (2026-07-10)

**Closed and axiom-clean**, in the same session as the falseness finding. The
executed proof follows the "real option (a)" below, upgraded by two structural
moves: (i) the confinement obligation became the reusable `evalE_congr`/
`step_congr` layer (`Spec/Confine.lean`), with `StoreDeclared` exactly
discharging the ttu case; (ii) the untainted monotone convergence became a
generic bounded-chain lemma (`chain_stabilizes`, used for BOTH the taint
fixpoint and the evaluation true-set), with the relative monotonicity obtained
by MASKING `rec` outside the consulted space and reusing the global
`evalE_mono` — no second leaf induction. The tainted phase is a strong
induction over Kahn layers via the new strict topology (`kahn_topo_strict`) and
coverage lemmas; the arithmetic `|atomsU| + 1 + |L| ≤ fuelBound` closes it.
See PROOF_STATUS "T0a CLOSED" for the lemma map. Original notes retained below.

### (original notes)

**⚠ STATEMENT CORRECTED (2026-07-10): the pre-`StoreDeclared` statement is FALSE**
— machine-checked refutation in `Spec/Counterexample.lean` (an admission-invalid
tupleset tuple creates a consultation edge `depEdges` never sees, closing an
exclusion cycle stratification misses; `semAux (n+2) = !(semAux n)` forever). The
theorem now carries `hDecl : StoreDeclared S T` (`Spec/Confine.lean`), the
documented §8 write-validity precondition (implied by the Python admission gate).
Any proof attempt below is understood over `hDecl`; the confinement lemma the
argument needs is *exactly* what `hDecl` makes true for the `ttu` case.

**CORRECTION to Gemini:** it claims "the Tarjan-lowlink guard (which sem mimics)
yields false on a revisit," so pigeonhole gives stability. **But `semAux` has NO
visited-set** — it is pure fuel recursion. Pigeonhole on the state space does not
directly apply.

**Real options:**
(a) *Monotonicity argument.* For a stratifiable schema, positive recursion is
monotone (more fuel only adds `True`, stabilizing once all grants are found via their
shortest acyclic path ≤ state-space size); negative positions (`but not` subtrahends)
are lower strata, hence acyclic and fuel-stable. Formalizing this ties `Stratifiable`
(a Kahn property on `depEdges`) to the evaluation's DAG-depth — substantial.
(b) *Refactor `semAux` to carry a visited-set* (mirroring the oracle). Then Gemini's
pigeonhole applies cleanly — but it is a SPEC CHANGE and must be re-validated by the
conformance suite before relying on it. Prefer (b) if (a) proves too hard; do it
before Phase 5.

**DECISION (2026-07-09): pursue (a), no spec change.** Detailed structure worked out
(see `Spec/FuelStable.lean` header) and **ingredient 1 is proved** (`evalE_mono`:
untainted/positive-fragment monotonicity — on an exclusion-free expr, `evalE`
preserves truth under a `rec` refinement `RecLe`). The full argument:
1. Taint propagates upward ⇒ untainted keys reference only untainted keys and are
   exclusion-free ⇒ a monotone fragment (converges by #reachable untainted atoms —
   what makes `fuelBound` multiplicative; `evalE_mono` is this step).
2. `depEdges` includes *all* tainted-tainted references and Kahn makes them a DAG ⇒
   each tainted key's `Φ` depends only on strictly-lower-rank tainted atoms +
   untainted atoms ⇒ each rank stabilizes one fuel-step after its inputs (**crucially,
   a same-key different-name reference among tainted keys is a self-edge, rejected —
   so no cross-entity chaining *within* a tainted rank; only untainted chains**).
**Remaining to build (next pass):** the finite reachable-atom set + confinement lemma
(`semAux` depends only on `rec` there), the untainted monotone-convergence count, the
per-rank stabilization induction, and the arithmetic that the total level ≤
`|keys|·(2|T|+4)`. This is the multi-session core; ingredient 1 is the foothold.
Ingredient 1½ (`semAux_mono`, evaluator-level fuel monotonicity on exclusion-free
schemas) landed 2026-07-10.

**Tactical framing (from a 2026-07-10 Gemini review, vetted):** formalize the
untainted convergence as monotone iteration on a **finite Bool-lattice** — the
evaluation state restricted to the reachable atoms, with `step` a monotone
endomap (that is `evalE_mono`/`semAux_mono`) — and bound stabilization by the
lattice *height* (≤ #atoms flips), rather than tracking "the set of true
evaluations" explicitly. Kahn rank then adds one fuel step per tainted stratum.
CAVEAT it glossed: `Rec = String³ → Bool` is not finite a priori — the
**confinement lemma** (the evaluation only ever consults reachable atoms) is
still the load-bearing prerequisite before any height argument applies; build it
first.

---

## T0b — `stratify_none_iff_cycle` / `stratify_topological` — ✅ DONE (2026-07-09)

**Closed and axiom-clean.** `Spec/WellDef.lean`'s T0b theorems are `sorry`-free. The plan
below was executed almost verbatim (no Mathlib topological-sort lemma reused — hand-rolled
on the concrete `kahn`). See PROOF_STATUS "Session 2026-07-09 (T0b fully closed)" for the
full lemma list. Original plan retained below for the record.

### (original plan)

**Plan.** Standard Kahn correctness on `depEdges`/`kahn`. Forward
(`none → cycle`): if `kahn` returns `none`, the surviving `remaining` set has every
node with an out-edge into `remaining` (min out-degree ≥ 1) ⇒ a cycle (finite +
pigeonhole walk). Reverse (`cycle → none`): cycle nodes always retain an in-`remaining`
out-edge, so `readyNodes` never peels them ⇒ `remaining` stays non-empty.
`stratify_topological`: invariant that a peeled layer's nodes depend only on
already-peeled nodes. Check `Mathlib.Combinatorics` / `Order` for reusable
topological-sort / acyclicity lemmas before hand-rolling.

---

## T2 / T5 — `graph_reached_inv`, `graph_correct`, `cascade_converges`

**✅ Model concretized + `cascade_converges` (T5) closed (2026-07-10).** The opaque
placeholders are now real (`GraphIndex/State.lean`, `sorry`-free):
- `GraphState := { schema, edges : List (NodeKey × NodeKey), nodes, residue : NodeKey
  → String → Option Residue, outbox, watermark }` (`NodeKey = (type,name,pred,variant∈
  {plain,wAny,wAll})`; `Residue = (stars, neg, upos)`).
- `GraphModel.check` = the ≤4-probe read (`probeNonDerived`) + residue path
  (`probeDerived`), routed by `isDerived` (§7.5–7.6). **Reads probe reachability
  `reachB` (transitive closure of direct edges), not path counts** — the counting
  layer stays factored in `Closure.lean`/T4, dodging a `Fintype NodeKey`.
- `Inv` = the I-series core (node encoding, I1 endpoint existence, I2 `acyclic` via
  `reach`, I6 residue hygiene incl. `neg ∩ edge-holders = ∅`).
- `ReachedBy` = inductive write-closure from `emptyState` via `WriteStep` (a minimal
  operational spec that bakes the in-txn cascade ⇒ outbox drained).
- `cascade_converges` (T5) is **proved** (axiom-clean): `Quiescent` = outbox-drain is
  a `WriteStep` postcondition, so it holds at every reachable state by induction.
  Base cases `inv_empty`/`quiescent_empty`/`reach_empty` proved.

**Reachability layer DONE (2026-07-10, axiom-clean, `GraphIndex/State.lean`):**
`Inv` restated over a fuel-free `NReaches`; `acyclic_addEdge` (cycle-rejection
preserves acyclicity); write-path primitives `addNode`/`addEdge`/`putResidue` with
`structInv_addNode`/`structInv_addEdge`/`inv_putResidue`; and — closing the
**ROADMAP-flagged T2b blocker** — the full `reach ↔ NReaches` bridge
(`reach_iff_nreaches`) via shortest-walk compression (`Trail` API + `trail_compress`
pigeonhole). So the executable fixed-fuel probe now provably equals fuel-free
reachability, and each write primitive's structural preservation is proved.

**Write model STARTED (2026-07-10, `GraphIndex/Write.lean`, axiom-clean).** The
untainted (residue-free) fragment of the faithful write model is now concrete:
`writeDirect` (one guarded direct-edge write, cycle-rejection faithful to §7.3),
`inv_writeDirect` (preserves the whole `Inv` — residue clauses vacuous on the
fragment), and `ReachedByDirect`/`reachedByDirect_inv` (**T2a's `Inv` conjunct
honestly proved for the untainted fragment**), embedding in the abstract
`ReachedBy` via `writeDirect_writeStep`. Two blockers remain, now sharply isolated:
(a) **derived reconcile** — residue materialization + the cross-key hazard (an edge
write re-reaching an existing residue key breaks `negEdgeFree` until reconcile);
(b) **T2b read = sem** — even the pure-direct case needs an acyclic-*data*
hypothesis, because `writeDirect` drops cycle-forming edges while `sem`
fuel-evaluates them.

**T2b groundwork DONE (2026-07-10, axiom-clean) — read=`sem` scaffolded from both
ends.** `GraphIndex/Correct.lean` + `State.lean` + `Write.lean`:
- **Base case CLOSED:** `graph_correct_empty` (`check (emptyState S) q = sem S [] q`,
  both `false`) — the `ReachedBy.empty` case, via `sem_empty_store` + `check_empty`.
- **Read → reachability:** `probeNonDerived_iff` rewrites the executable ≤4-probe read
  as a disjunction of four `NReaches` conditions (via `reach_iff_nreaches`).
- **Reachability → chain:** `TupleChain` + `reachedByDirect_nreaches_chain`
  (+`reachedByDirect_edge_sound`, `writeDirect_edges`) — an untainted graph path IS a
  stored-tuple membership chain. This is T2b's reachability-half soundness, relational.

**FINDING (2026-07-10, taking stock): the two T2 sorries are FALSE as stated, not
merely unproven.** `WriteStep` is a thin postcondition spec (schema fixed, nodes
monotone, outbox drained) and `Inv` never ties `σ.edges`/`σ.residue` to the store
`T`. Counter-model: from `emptyState S`, one `WriteStep` into a state carrying a
single arbitrary acyclic edge `(a,b)` (both nodes added, encoding-valid, outbox
empty) satisfies `ReachedBy σ S [t]`, `Inv S σ`, and every schema hypothesis — yet
`check` answers `true` on the corresponding query while `sem S [t]` answers `false`
for an unrelated `t`. Consequence: **no proof effort can close `graph_correct` or
`graph_reached_inv`'s `Inv` conjunct in their current form.** The operational write
model is not merely "the blocker", it is *mandatory for the statements to be true*.
Endgame: complete the operational write path (untainted `writeDirect` ✓ done;
wildcard bridges; derived reconcile), then RESTATE T2a/T2b over that operational
closure.

**RESOLVED (2026-07-10, user-directed deletion).** The abstract
`WriteStep`/`ReachedBy` layer and every statement over it (`graph_correct`,
`graph_reached_inv`, `backend_equivalence`, `exclusion_effective`,
`no_ghost_grant`, the assertion-backed `cascade_converges`) were **deleted** —
the false statements removed, not proved. All six theorem names were restated
over the operational closure (`ReachedByDirect`/`ReachedByAdmitted`) at the
star-free pure-direct fragment's scope, where they are real, proved,
axiom-clean, sorry-free (`Correct.lean`, `DirectCorrect.lean`, `Equiv.lean`).
The `sorry` count dropped 3 → 1 **by deletion, not proof** — the full-scope
obligations return in stage W4 of the staged plan (top of this file).

**Remaining (the genuine multi-session cores):**
- **T2b semantic core:** `TupleChain T u v ↔ sem`-membership — match the membership
  chain against `directLeaf`/`memberOfGranted`'s userset recursion, the wildcard-node
  promotion (`wAny`/`wAll` in `probeNonDerived_iff`), `instances`, `matchingObjects`.
  Plus the converse edge-completeness (`TupleChain → NReaches`), which needs an
  acyclic-*data* hypothesis (`writeDirect` drops cycle-forming edges while `sem`
  fuel-evaluates them). The read/reachability plumbing is done; this is the last mile.

  **✅ EXECUTED (2026-07-10, same session): the semantic core is CLOSED on the
  star-free pure-direct fragment** — `GraphIndex/DirectCorrect.lean` is sorry-free
  and `graph_correct_direct` is axiom-clean (`[propext, Classical.choice,
  Quot.sound]`, audited). The plan below was executed verbatim (steps 1–6 map to
  `semAux_mono`, `TupleChainN`/`chainN_of_trail`, `semAux_lift`,
  `semAux_of_chainN`, `nreaches_of_semAux`, `graph_correct_direct`). The original
  plan is retained for the record:

  Plan: close the semantic core end-to-end on the star-free pure-direct fragment,
  as a genuine, non-vacuous
  `graph_correct_direct`. Fragment: every schema def is `.direct rs` (`PureDirect`),
  the store is admission-valid (`StoreValid`: each tuple's `(object.type, relation)`
  is declared `.direct rs` with `restrictionMatches rs t`; matches the Python
  admission gate) and star-free; the state is reached by *admitted* writes
  (`ReachedByAdmitted` — faithful to the composed system, where a cycle-rejected
  write rolls back the tuple insert too, so the store never holds a rejected tuple).
  Proof structure, worked out against the code:
  1. `semAux_mono` (fuel monotonicity on exclusion-free schemas, from `evalE_mono`)
     — dual-use: also T0a ingredient 1½.
  2. Length-indexed chains `TupleChainN` + `chainN_of_trail` (via
     `reachedByDirect_edge_sound`), giving NReaches → short chain (`trail_compress`).
  3. **Userset lifting** (the heart): if `s ∈ sem`-member of userset `s'` at fuel f₀
     and `s'` is a member of node `v` at fuel `f`, then `s ∈ v` at `f + f₀` — by fuel
     induction; every direct-match of `s'` at a grant is absorbed by `s`'s
     `memberOfGranted` flow-through on the same grant (needs `s'.predicate ≠ BARE`,
     from `WF.relNames` since `BARE` contains `'.'`).
  4. Soundness: `TupleChainN n → semAux` at fuel `n` (single = direct match at fuel 1;
     cons = lifting with f₀ = 1); fuel fits `fuelBound` since `n ≤ nodes.length + 1
     = 2·|T| + 1 < |keys|·(2|T|+4)` (keys nonempty from `StoreValid` + chain ≠ []).
  5. Completeness: `∀ f, semAux s f ot on r → NReaches (subjNode s) (objNode ⟨ot,on⟩ r)`
     by fuel induction: direct-match ⇒ the grant's own edge (edge-completeness from
     `ReachedByAdmitted`); `memberOfGranted` ⇒ IH + `objNode ⟨g.sub.type,g.sub.name⟩
     g.sub.pred = subjNode g.subject` (both plain, star-free) + `NReaches.tail`.
  6. Assembly: `PureDirect → taintedKeys = []` (so `check` routes to
     `probeNonDerived`); star-free store ⇒ no edge touches `wAny`/`wAll` nodes ⇒
     probes 2–4 are `false`; probe 1 ↔ NReaches (`reach_iff_nreaches`) ↔ chain ↔ sem.
  Wildcards (bridge materialization — the model has none yet; read-side promotion
  only covers the *first* hop), TTU/computed/union defs, and the derived/residue path
  are the explicitly deferred extensions, each widening the fragment.
- **T2b residue path:** for derived relations, residue = `sem` via `ext_normalize`/T1
  MemberSet lemmas; bare-subject edge-hit ≡ full residue via `Inv.negEdgeFree`. Needs
  the write model to know what the residues *are* (the reconcile output).
- **T2a** (`graph_reached_inv`, `Inv` conjunct): the write must re-establish I6 for
  *all* reachability-affected keys with the semantically-correct residues.
  `inv_putResidue` closes the per-key step; a delete-only reconcile-by-construction is
  **unfaithful** (changes residue meaning ⇒ breaks T2b), so the faithful delta output
  must be modeled. Structural clauses already discharged by the `structInv_*` lemmas.

---

## Suggested order

**→ Follow "The staged T2 plan" at the top of this file: W1 (wildcard bridges) →
W2 (rule routing) → W3 (derived reconcile) → W4 (full-scope restatement), with
T0a and the Phase-6 graph-model conformance extension schedulable in parallel.**

Historical single-sorry order (all ✅ except T0a):
1. ~~**T4**~~ ✅ DONE (axiom-clean; `Closure.lean` sorry-free).
2. ~~**T0b**~~ ✅ DONE (axiom-clean; hand-rolled Kahn correctness).
3. ~~**T1**~~ ✅ DONE (axiom-clean; concrete expand model + query-focused population).
4. ~~**T2/T5 at fragment scope**~~ ✅ DONE (2026-07-10): model concretized;
   reachability layer (`reach ↔ NReaches`); T2b groundwork (base case,
   `probeNonDerived_iff`, `TupleChain`); **T2b semantic core
   (`graph_correct_direct`, userset lifting + chain⇔`sem` both directions)**;
   abstract-closure falsehood found, layer deleted, T2a/T2b/T3/T5/T6 restated
   operationally at fragment scope, all proved.
5. ~~**T0a**~~ ✅ DONE (2026-07-10): restated over `StoreDeclared` + fully
   proved (confinement / untainted counting / Kahn rank induction).

---

## Session handoff — environment & hard-won Lean/Mathlib notes

For a fresh session: read `HANDOFF.md` first (entry point), then the target `.lean`.
Everything is committed; `.lake/` (mathlib clone + cache) is on disk and gitignored
(regenerate with `lake exe cache get` if missing).

**Build/verify commands** (Lean toolchain is at `~/.elan/bin`):
```
export PATH="$HOME/.elan/bin:$PATH"
cd formal/lean && lake build                 # library (~min incremental; use background)
lake build ZanzibarProofs.GraphIndex.Closure # one module (~20s)
lake build zcli                              # conformance CLI
rm -f .lake/build/lib/lean/ZanzibarProofs/Audit.olean && lake build ZanzibarProofs.Audit  # axiom audit
bash formal/verify.sh                         # full gate (build + sorries + audit + pytest)
```
Conformance uses the repo conda env python (`.../envs/graph-reachability-zanzibar-index/python.exe -m pytest formal/conformance/ -q`). Lean = v4.31.0, Mathlib pinned v4.31.0.

**Mathlib import quirks (v4.31.0) — these cost build cycles to find:**
- `Finset.Ico` ← `import Mathlib.Order.Interval.Finset.Nat`
- `Finset.sum_Ico_succ_top`, `sum_Ico_consecutive` ← `Mathlib.Algebra.BigOperators.Intervals`
- big-operator ring lemmas (`Finset.mul_sum`, distribution) ← `Mathlib.Algebra.BigOperators.Ring.Finset`
- `∑ w : V, …` Fintype sums ← `Mathlib.Data.Fintype.BigOperators`
- `Finset.biUnion` ← `Mathlib.Data.Finset.Union`
- `Mathlib.Algebra.BigOperators.Basic` / `.Ring` do **NOT** exist (reorganized). `ring`
  tactic needs `Mathlib.Tactic.Ring` (not transitively available).

**Tactic gotchas learned this session:**
- To unfold a plain `def` inside a goal use `unfold f` or `simp only [f]`, **not**
  `rw [f]` (rw usually won't fire on a non-pattern-matching def — this cost ~4 cycles
  on `phat`). `pathCount`/`phat` unfold fine under `simp only [...]`.
- `Nat` distribution: `exact Nat.left_distrib _ _ _` (term-mode, no import).
- `omega` closes linear-Nat goals treating `∑`-terms as opaque atoms — ideal for
  combining `have`s about sums (used to finish `phat_boundary`, `sum_Ico_shift_boundary`).
- `simp only at h` with no lemmas errors "no progress"; drop it (elaboration already
  beta-reduces instantiated lambdas, so `omega` sees the reduced form).
- `Finset.sum_Ico_succ_top (h : a ≤ b)` peels the TOP term of `Ico a (b+1)`; supply the
  witness for `b`, not `b+1` (e.g. `Nat.le_add_left 1 m : 1 ≤ m+1`, not `… (m+1)`).
- Prefer explicit `have e1/e2 … ; calc` over `congr 1` for sum equalities — `congr 1`
  split fragilely here.

*(The historical "T4 blocker" walk-API notes and the original 9-sorry scoping that
used to close this file were executed to completion — T4 and all original sorries are
closed; see the per-theorem sections above for the retained plans-of-record.)*
