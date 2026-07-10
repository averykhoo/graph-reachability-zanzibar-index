# ROADMAP — the staged path to the verified model (0 `sorry`s left, was 9)

The plan of record toward the END GOAL: **a formally verified Zanzibar/OpenFGA
model tied to the Python implementation.** Read alongside `PROOF_STATUS.md`
(status) and `SEMANTICS.md` (the spec).

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
  - **W1c — userset stars (in-bridges + `instances`). IN PROGRESS (2026-07-10):
    BOTH SEMANTIC CORES CLOSED; write model + edge characterization done.**
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
- **W3 — derived reconcile (the residue path).** Faithful `reconcile` output
  per derived key (residue `(stars, neg, upos)` = the §7.6 semantics), the
  in-transaction cascade over the outbox, and the cross-key hazard (an edge
  write re-reaching an existing residue key re-reconciles it). Closes full
  T2a (`Inv` incl. I6 across reachability-affected keys) and the derived-read
  half of T2b (residue = `sem` via the T1 MemberSet algebra + `negEdgeFree`
  edge-hit disjointness). T5 becomes contentful (non-empty outbox drained).
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

For a fresh session. Read `PROOF_STATUS.md` (status/resume) → this file → the target
`.lean`. Everything is committed; `.lake/` (mathlib clone + cache) is on disk and
gitignored (regenerate with `lake exe cache get` if missing).

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

**The T4 blocker (do this first to finish T4):** a **walk API** for the Nat-weighted
multigraph. Concretely: (i) `pathsOfLength g k u v > 0 ↔ ∃ (walk : List V) of length k
from u to v with all edges positive` (induction on `k`); (ii) the **vanishing lemma**
`Acyclic g → pathsOfLength g |V| w v = 0` (a length-`|V|` walk has `|V|+1` vertices ⇒
pigeonhole repeat ⇒ closed sub-walk ⇒ `pathCount x x > 0` ⇒ ¬Acyclic) — this discharges
`phat_recurrence`'s `hvanish`; (iii) `pathCount_addEdge` by decomposing `g'`-walks into
"uses new edge `(u,v)` 0 or 1 times" (acyclic ⇒ ≤ 1). Check whether
`Mathlib.Combinatorics.SimpleGraph.Walk` or `Quiver.Path` can be adapted before rolling
your own. Once (ii)+(iii) land, `pathCount_removeEdge` is the `(ℤ,+)` inverse of (iii).

**Realistic scope:** closing all 9 is multi-session. Each of T1/T2 needs its concrete
model built first (see the per-theorem sections above); T0b/T0a and the T4 walk API are
each self-contained multi-hour proofs.
