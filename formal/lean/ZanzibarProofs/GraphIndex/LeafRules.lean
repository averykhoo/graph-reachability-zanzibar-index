import ZanzibarProofs.GraphIndex.Leaf
-- Obligation (F) only: `StoreValidRules` (`RulesSound.lean:201`) and `lookup_rel_ne_bare`
-- (`DirectCorrect.lean:74`), so `rewriteClosureL_rel_ne_bare` can carry EXACTLY the premise
-- list of its plain twin `RulesChain.lean::rewriteClosure_rel_ne_bare` and be a drop-in at
-- the post-flip consumer `CascadeSettle.lean:112`. **Cycle-checked 2026-09-05, by transitive
-- closure rather than by eye**: `RulesSound`'s import cone is 29 modules and contains
-- neither `GraphIndex.Leaf` nor `GraphIndex.LeafRules` nor any `Cascade*` module, while
-- `LeafRules` is imported only by `Audit`, `CascadeStable` and `Scratch4cii` — none of which
-- is in that cone. No new module is added, so the job count is unchanged.
import ZanzibarProofs.GraphIndex.RulesSound
-- **`P6` step 3b, re-point #2 (2026-09-14).** `GraphState.writeRulesRaw` below folds
-- `UsStarWrite.lean::GraphState.writeBridgedOne`, so that module must be in scope; without
-- this line the re-point does not even elaborate. **Cycle-checked first-hand 2026-09-14, by
-- transitive closure over `^import ZanzibarProofs`, not by eye**: `UsStarWrite`'s import cone
-- is 9 modules (`Core.Ident/Refs/Schema/Store`, `Spec.Stratify`,
-- `GraphIndex.Closure/State/Write/ObjStarWrite`) and contains neither `GraphIndex.Leaf` nor
-- `GraphIndex.LeafRules`; `LeafRules`' own cone is 18 modules and does not contain
-- `UsStarWrite`, which is why the edge is new rather than redundant. ⚠ The 2026-09-05 note
-- above is STALE on one point, corrected here rather than edited there: `LeafRules` is now
-- imported by FOUR modules, not three — `Cascade` joined `Audit`, `CascadeStable` and
-- `Scratch4cii`. None of the four is in `UsStarWrite`'s cone, so the conclusion is unchanged.
import ZanzibarProofs.GraphIndex.UsStarWrite

/-!
# Leaf-provenance rewrite rules — leg 7 step **4c-i**

`RulesWrite.lean::schemaRewrites` routes every **derived** key OFF the rewrite fanout
entirely (its taint filter, `!(isDerived S d.1)`), faithfully mirroring
`zanzibar_utils_v1.py::compile_ruleset`'s `if key not in tainted: _emit_expr(...)` loop.
That is only *half* of what Python does with a derived key. The other half is
`_build_plan_tree` → `_emit_leaf_expr`, which compiles each of the key's **closure
leaves** into ordinary `Rule`s whose target is the minted leaf name:

```text
viewer: editor but not banned          -- measured 2026-08-16, live compile
  Rule  if(rel='editor', otype='doc')  -> then(rel='viewer.0')
  Rule  if(rel='banned', otype='doc')  -> then(rel='viewer.1')
```

This file supplies exactly that missing half, and nothing else.

## ★★ Why this is step 4c-**i**, and why it is not a caller re-point

Scope doc §11.6 (2026-08-15). The 76 edge rows projection P6 dropped (★ RETIRED
2026-09-05 — P3 landed (α)+(R5); P6 branch deleted from
`formal/conformance/extractor.py`, the 76 now the `_MIN_LEAF_COMPARED` floor in
`formal/conformance/test_conformance_state.py`) are mostly
**rule-copied closure-leaf edges**, and the correct leaf index is a function of *which
arm produced the copy* — provenance `rewriteClosure` does not carry. For
`viewer: editor but not banned` the `editor`-arm and `banned`-arm members are
**shape-identical tuples**, yet Python routes them to `viewer.0` and `viewer.1`
respectively. **No re-addressing function of the tuple alone can produce Python's leaf
edges.** Python bakes the target into the compiled rule
(`zanzibar_utils_v1.py::_emit_leaf_expr` → `_rewrite_rule(expr, object_type, leaf)`);
the faithful model does the same, which is what `leafRewrites` below is.

## ★ The recompile cone is ZERO, and scope doc §11.6 over-estimated it

§11.6 sizes 4c-i as *"a rules-model change UNDER `RulesWrite.lean`, i.e. the recompile
cone is the full GraphIndex tree, roughly double the 19-module Cascade cone."* That is
true only if `schemaRewrites` is **edited**. It is an *extension*, so it lands in a new
module DOWNSTREAM of `RulesWrite` and the cone is one file. Verified 2026-08-16:
`GraphIndex/Cascade.lean` imports `ReconcileDiff` — far downstream of `RulesWrite` —
and `Leaf.lean` imports only `Write` / `RulesWrite` / `Spec.Stabilize`, so the import
`Cascade → LeafRules` that step **4c-ii** needs creates **no cycle**. The cone is paid
once, at 4c-ii, when the callers actually move; 4c-i does not pay it twice.

Nothing here is wired into a caller. `writeRulesRaw` below is the shape 4c-ii will
re-point `writeLoggedOne` / `writeRules` at; today it has no consumer, exactly as
`writeDirectRaw` had none at 4a.

## The composition it models — `RuleSet.apply`, read literally

`zanzibar_utils_v1.py::RuleSet.apply` is two stages, and the model must be too:

1. **Seeds.** On a derived family, *every* matching `RewriteFilter` fires and the triple
   is re-addressed onto that filter's leaf, deduped — `Leaf.lean::rawWriteTuples`.
   On an untainted relation the seed set is `{t}` itself.
2. **Worklist.** Every matching `Rule` fires on every triple, to a fixpoint, deduped by
   the `processed` set — `rewriteClosureL` below, seeded by the *list* from stage 1
   rather than by a single tuple.

So `rewriteClosureRawL` generalises `RulesWrite.lean::rewriteClosureRaw` from one seed
to a seed list; at `[t]` with an untainted schema the two are definitionally equal
(`rewriteClosureRawL_singleton`).

## Measured before it was written

The model below was transcribed into Python and diffed against the `Rule`s
`compile_ruleset` actually emits, over every corpus dict in
`formal/conformance/corpus.py` and every `tests/fga_schemas/*.fga` fixture:
**50 / 50 schemas match, 0 mismatches**, of which **32 have a non-empty leaf rule set**
(the non-vacuity count — a model that returned `[]` everywhere would have matched the
other 18 and proved nothing).

Reference: `formal/history/leaf-family-split-scope-2026-08-05.md` §11.6,
`formal/history/PROOF_STATUS.md` 2026-08-16.
-/

namespace Zanzibar

/-! ## The rules a derived key's closure leaves emit -/

/-- **`_emit_leaf_expr`'s rule half** for one derived key: each CLOSURE leaf, at its
    allocation index `i`, contributes the rewrite arms of its (possibly merged) subtree
    targeting `leafPred R i` instead of the public `R`.

    `exprArms` is reused verbatim from `RulesWrite.lean` — it already walks unions and
    turns each `computed` / `ttu` leaf into an `RRule`, and returns `[]` on
    `direct`/`inter`/`excl`, which is exactly `_emit_leaf_expr`'s split: `Direct`
    restrictions become `RewriteFilter`s (the *storage* routing, modeled by
    `rawWriteRels`), and a boolean node cannot occur inside a pure subtree at all
    (`_emit_leaf_expr` raises `TypeError` there; `isPure` makes it unreachable here). -/
def keyLeafRewrites (S : Schema) (ty R : String) (e : Expr) : List RRule :=
  (persistedLeaves S ty e).zipIdx.flatMap fun pi =>
    match pi.1 with
    | .closure sub => exprArms ty (leafPred R pi.2) sub
    | _ => []

/-- Every rewrite rule the schema's DERIVED keys emit through their closure leaves —
    the exact complement of `schemaRewrites`' taint filter. -/
def leafRewrites (S : Schema) : List RRule :=
  (S.defs.filter (fun d => isDerived S d.1)).flatMap
    (fun d => keyLeafRewrites S d.1.1 d.1.2 d.2)

/-- **The full compiled rule set** — untainted fanout plus leaf-targeted derived rules.
    Order mirrors `compile_ruleset`, which walks the untainted defs before the derived
    plans; rule ORDER is not observable through `rewriteStep` (a `filterMap` over all
    rules, not first-match) but keeping it faithful costs nothing. -/
def schemaRewritesL (S : Schema) : List RRule := schemaRewrites S ++ leafRewrites S

/-! ## Disjointness — the untainted fragment is untouched BY CONSTRUCTION

The two halves cannot collide: `schemaRewrites` only ever targets a **declared**
relation name, and `WF` forbids `'.'` in one, while `leafRewrites` only ever targets a
minted leaf name, which carries one. So the extension is additive in the strongest
sense available — not "we checked and nothing broke", but "the new rules are provably
a disjoint set". -/

/-- Every rule the untainted layer emits targets a name of the form `exprArms` was
    given, i.e. one of the schema's declared relation names. -/
theorem outRel_mem_of_mem_exprArms {ot outRel : String} {e : Expr} {r : RRule}
    (h : r ∈ exprArms ot outRel e) : r.outRel = outRel := by
  induction e with
  | direct _ => simp [exprArms] at h
  | computed _ => simp [exprArms] at h; subst h; rfl
  | ttu _ _ => simp [exprArms] at h; subst h; rfl
  | union a b iha ihb =>
      rw [exprArms, List.mem_append] at h
      exact h.elim iha ihb
  | inter _ _ _ _ => simp [exprArms] at h
  | excl _ _ _ _ => simp [exprArms] at h

/-- **Every leaf rule targets a leaf predicate.** -/
theorem isLeafPred_outRel_of_mem_leafRewrites {S : Schema} {r : RRule}
    (h : r ∈ leafRewrites S) : isLeafPred r.outRel = true := by
  unfold leafRewrites at h
  obtain ⟨d, _, hd⟩ := List.mem_flatMap.mp h
  unfold keyLeafRewrites at hd
  obtain ⟨pi, _, hpi⟩ := List.mem_flatMap.mp hd
  split at hpi
  · rw [outRel_mem_of_mem_exprArms hpi]; exact isLeafPred_leafPred _ _
  · simp at hpi

/-- **Every untainted rule targets a DECLARED — hence dot-free — relation.** -/
theorem not_isLeafPred_outRel_of_mem_schemaRewrites {S : Schema} (hWF : WF S) {r : RRule}
    (h : r ∈ schemaRewrites S) : isLeafPred r.outRel = false := by
  unfold schemaRewrites at h
  obtain ⟨d, hd, hr⟩ := List.mem_flatMap.mp h
  have hdefs : d ∈ S.defs := (List.mem_filter.mp hd).1
  have := outRel_mem_of_mem_exprArms hr
  have hok : relNameOK d.1.2 := hWF.relNames d hdefs
  rw [this]
  by_contra hne
  exact hok (by
    simp only [Bool.not_eq_false] at hne
    have : '.' ∈ d.1.2.toList := by simpa [isLeafPred, List.contains_eq_mem] using hne
    simpa [String.contains_char_eq] using this)

/-- **The disjointness fact.** No rule is in both halves, so `schemaRewritesL` is a
    genuine extension and the untainted layer keeps its exact meaning. -/
theorem schemaRewrites_leafRewrites_disjoint {S : Schema} (hWF : WF S) {r : RRule}
    (h1 : r ∈ schemaRewrites S) (h2 : r ∈ leafRewrites S) : False := by
  have ht := isLeafPred_outRel_of_mem_leafRewrites h2
  have hf := not_isLeafPred_outRel_of_mem_schemaRewrites hWF h1
  rw [ht] at hf
  exact Bool.noConfusion hf

/-- **Subsumption.** A schema with no derived keys emits no leaf rules, so the full rule
    set IS today's rule set — the analogue of `rawWriteRels_untainted`. -/
theorem leafRewrites_eq_nil {S : Schema} (h : ∀ d ∈ S.defs, isDerived S d.1 = false) :
    leafRewrites S = [] := by
  unfold leafRewrites
  have : S.defs.filter (fun d => isDerived S d.1) = [] := by
    apply List.filter_eq_nil_iff.mpr
    intro d hd
    simp [h d hd]
  rw [this]; rfl

/-- Hence the whole compiled rule set collapses to the untainted one. -/
theorem schemaRewritesL_eq {S : Schema} (h : ∀ d ∈ S.defs, isDerived S d.1 = false) :
    schemaRewritesL S = schemaRewrites S := by
  simp [schemaRewritesL, leafRewrites_eq_nil h]

/-! ## The rewrite closure over the full rule set

`RulesWrite.lean`'s closure is seeded by a single tuple because, before leaf routing,
`RuleSet.apply`'s stage 1 was the identity. With the fan-out it is not, so the closure
takes a seed LIST. Everything else is `rewriteClosureAux` verbatim. -/

/-- One rewrite step under the FULL rule set (untainted fanout + leaf targets). -/
def rewriteStepL (S : Schema) (t : Tuple) : List Tuple :=
  (schemaRewritesL S).filterMap (applyRRule · t)

/-- The bounded closure kernel — `rewriteClosureAux` with `rewriteStepL`. -/
def rewriteClosureAuxL (S : Schema) : Nat → List Tuple → List Tuple
  | 0, cur => cur
  | n + 1, cur => cur ++ rewriteClosureAuxL S n (cur.flatMap (rewriteStepL S))

/-- The RAW bounded closure of a SEED LIST (`RuleSet.apply`'s worklist over its
    post-`RewriteFilter` seed set). The rewrite graph on relations is a DAG
    (stratification), so `|keys|+1` levels suffice, exactly as for the single-seed
    version. -/
def rewriteClosureRawL (S : Schema) (seeds : List Tuple) : List Tuple :=
  rewriteClosureAuxL S (S.keys.length + 1) seeds

/-- The deduplicated closure — `RuleSet.apply`'s `processed` set, which is per-`apply`
    call and therefore spans the whole seed list, not one seed. -/
def rewriteClosureL (S : Schema) (seeds : List Tuple) : List Tuple :=
  (rewriteClosureRawL S seeds).dedup

@[simp] theorem mem_rewriteClosureL_iff {S : Schema} {seeds : List Tuple} {u : Tuple} :
    u ∈ rewriteClosureL S seeds ↔ u ∈ rewriteClosureRawL S seeds := List.mem_dedup

/-- On a schema with no derived keys the stepped rule set is today's, so the kernel is
    today's kernel at every fuel and seed list. -/
theorem rewriteStepL_eq {S : Schema} (h : ∀ d ∈ S.defs, isDerived S d.1 = false) (t : Tuple) :
    rewriteStepL S t = rewriteStep S t := by
  simp [rewriteStepL, rewriteStep, schemaRewritesL_eq h]

theorem rewriteClosureAuxL_eq {S : Schema} (h : ∀ d ∈ S.defs, isDerived S d.1 = false) :
    ∀ (n : Nat) (cur : List Tuple), rewriteClosureAuxL S n cur = rewriteClosureAux S n cur := by
  have hstep : rewriteStepL S = rewriteStep S := funext (rewriteStepL_eq h)
  intro n
  induction n with
  | zero => intro cur; rfl
  | succ n ih =>
      intro cur
      simp only [rewriteClosureAuxL, rewriteClosureAux, hstep, ih]

/-- **The single-seed collapse.** On an untainted schema the generalised closure at
    `[t]` is `rewriteClosure S t` — so `RulesWrite`'s whole development is the special
    case, and no consumer of it changes meaning. -/
theorem rewriteClosureRawL_singleton {S : Schema}
    (h : ∀ d ∈ S.defs, isDerived S d.1 = false) (t : Tuple) :
    rewriteClosureRawL S [t] = rewriteClosureRaw S t := by
  simp [rewriteClosureRawL, rewriteClosureRaw, rewriteClosureAuxL_eq h]

/-! ## The SUPERSET direction — the plain closure sits inside the leaf-routed one

`rewriteClosureL_extras_leafNode` (below) classifies what the L closure has that the plain
one does not. Its mirror — that the L closure loses NOTHING — is what the post-flip shadow
needs for `ShadowOver.sub`: every edge the shadow's plain fold materializes must still be
present in the logged, leaf-routed state. It is pure rule-set monotonicity: `schemaRewritesL`
is `schemaRewrites ++ leafRewrites`, and `filterMap` over an append is an append. -/

/-- One step of the untainted kernel is contained in one step of the full kernel. -/
theorem rewriteStep_subset_rewriteStepL {S : Schema} {t u : Tuple}
    (h : u ∈ rewriteStep S t) : u ∈ rewriteStepL S t := by
  unfold rewriteStep at h
  unfold rewriteStepL schemaRewritesL
  rw [List.filterMap_append, List.mem_append]
  exact Or.inl h

/-- **Kernel monotonicity at equal fuel.** A frontier contained in an L-frontier stays
    contained after any number of rounds. -/
theorem rewriteClosureAux_subset_auxL (S : Schema) :
    ∀ (n : Nat) (cur curL : List Tuple), (∀ x ∈ cur, x ∈ curL) →
      ∀ y ∈ rewriteClosureAux S n cur, y ∈ rewriteClosureAuxL S n curL := by
  intro n
  induction n with
  | zero => intro cur curL hs y hy; exact hs y hy
  | succ n ih =>
    intro cur curL hs y hy
    rw [rewriteClosureAux, List.mem_append] at hy
    rw [rewriteClosureAuxL, List.mem_append]
    rcases hy with hcur | hnext
    · exact Or.inl (hs y hcur)
    · refine Or.inr (ih _ _ ?_ y hnext)
      intro x hx
      obtain ⟨c, hc, hxc⟩ := List.mem_flatMap.mp hx
      exact List.mem_flatMap.mpr ⟨c, hs c hc, rewriteStep_subset_rewriteStepL hxc⟩

/-- **The plain rewrite-closure of a seed is inside the leaf-routed closure of any seed
    list containing it.** Both kernels run at the SAME fuel `S.keys.length + 1`, so no
    saturation fact is needed — exactly as for `rewriteClosureL_extras_leafNode`. This is
    `ShadowOver.sub`'s side condition at the flip
    (`CascadeStable.lean::untaintedShadow_writeLegL`'s `hsub`). -/
theorem rewriteClosure_subset_rewriteClosureL {S : Schema} {t : Tuple} {seeds : List Tuple}
    (hseed : t ∈ seeds) {u : Tuple} (h : u ∈ rewriteClosure S t) :
    u ∈ rewriteClosureL S seeds := by
  rw [mem_rewriteClosure_iff] at h
  rw [mem_rewriteClosureL_iff]
  unfold rewriteClosureRaw at h
  unfold rewriteClosureRawL
  refine rewriteClosureAux_subset_auxL S _ [t] seeds ?_ u h
  intro x hx
  rw [List.mem_singleton] at hx
  exact hx ▸ hseed

/-- The raw write is one of its own leaf-routed seeds when it is untainted — the
    instantiation `rewriteClosure_subset_rewriteClosureL` is consumed at. -/
theorem mem_rawWriteTuples_self {S : Schema} {t : Tuple}
    (h : isDerived S (t.object.type, t.relation) = false) : t ∈ rawWriteTuples S t := by
  rw [rawWriteTuples_untainted h]
  exact List.mem_singleton_self t

/-! ## The leaf-routed rule write — the shape step 4c-ii re-points callers at -/

/-- **`RuleSet.apply` + per-triple `add_tuple`, both stages.** Stage 1 re-addresses the
    raw write onto its storage leaves (`rawWriteTuples`, the measured fan-out); stage 2
    closes the result under the full rule set including the leaf targets; each surviving
    triple is materialized by `UsStarWrite.lean::GraphState.writeBridgedOne`.

    ★ **`P6` step 3b RE-POINT #2 LANDED 2026-09-14.** This fold was `acc.writeDirect u`
    until this edit; it is now `acc.writeBridgedOne u`, i.e. Python's bridge-before-grant
    prologue (`index_v4/wildcard.py::_maybe_add_bridges` ahead of the per-triple grant)
    runs on the LEAF-ROUTED write path. `writeBridgedOne` has the same arity and
    explicitness as `writeDirect` (`UsStarWrite.lean` vs `Write.lean::GraphState.writeDirect`),
    so this is a two-token change at the definition and every `∀ (ts : List Tuple)` fold
    lemma below re-points by swapping ONE lemma name — see the `structInv_`/`residueEmpty_`/
    `inv_`/`quiescent_`/`_schema` block. What it is NOT is free downstream: the widened
    star-freeness predicate becomes inhabited here, which is the whole point of the step.

    ⚠ **CALLERS, as of R5 + (alpha) — this docstring said "No caller yet" and was wrong on
    the tree it sat in.** `Cascade.lean::GraphState.writeLoggedRules` has folded this list
    since the write flip, `::GraphState.removeLoggedRules` since R5, and
    `::affectedKeys`' own-key branch now threads `Leaf.lean::publicOfLeaf` (branch (α)). The
    one thing that remains UNCHANGED and un-re-pointed is
    `RulesWrite.lean::GraphState.writeRules` — the PLAIN shadow rebuild that
    `ReachedByRulesAdmitted` folds, deliberately kept on `rewriteClosure` so the
    `RulesComplete`/`RulesWrite` development stands; the bridge between the two is
    `CascadeStrataSettle.lean::untOccCount_eq_plainOcc_of_notLeaf`. **Measured 2026-09-13d,
    and it is why the asymmetry is deliberate rather than lazy**: `writeRules`' reverse cone
    is 40 modules against `writeBridgedOne`'s 24. ★ **Step 7 RETIRED P6
    2026-09-05** (P3 landed (α)+(R5); the branch is deleted from
    `formal/conformance/extractor.py`, ledger key and all) — nothing on this leg is owed. -/
def GraphState.writeRulesRaw (σ : GraphState) (S : Schema) (t : Tuple) : GraphState :=
  (rewriteClosureL S (rawWriteTuples S t)).foldl (fun acc u => acc.writeBridgedOne u) σ

/-- **The subsumption theorem's LIST half** — extracted by `P6` step 3 from
    `writeRulesRaw_untaintedSchema` below, because after the bridge composition the list
    half is the part that survives unchanged. On a schema with no derived keys the
    leaf-routed expansion IS the plain rewrite-closure, as lists. -/
theorem rewriteClosureL_rawWriteTuples_untaintedSchema {S : Schema} {t : Tuple}
    (h : ∀ d ∈ S.defs, isDerived S d.1 = false) :
    rewriteClosureL S (rawWriteTuples S t) = rewriteClosure S t := by
  have hd : isDerived S (t.object.type, t.relation) = false := by
    by_cases hne : isDerived S (t.object.type, t.relation) = true
    · exfalso
      have hk : (t.object.type, t.relation) ∈ S.keys := taintedKeys_subset_keys S (by
        simpa [isDerived, List.contains_eq_mem] using hne)
      unfold Schema.keys at hk
      obtain ⟨d, hdmem, hde⟩ := List.mem_map.mp hk
      rw [← hde, h d hdmem] at hne
      exact Bool.noConfusion hne
    · simpa using hne
  rw [rawWriteTuples_untainted hd]
  unfold rewriteClosureL rewriteClosure
  rw [rewriteClosureRawL_singleton h]

/-- **The subsumption theorem the leg's honesty rests on**, RESTATED by `P6` step 3b on
    2026-09-14: on a schema with no derived keys, the leaf-routed write folds exactly the
    PLAIN rewrite closure — the routing is the identity there. Not "we checked the tests
    still pass"; the two expressions are equal as definitions.

    ★ **WHAT MOVED, AND WHY THE OLD STATEMENT IS NOW FALSE RATHER THAN MERELY UNPROVEN.**
    Until 2026-09-14 this read `σ.writeRulesRaw S t = σ.writeRules S t`. Re-point #2 makes
    `writeRulesRaw` fold `GraphState.writeBridgedOne` while `RulesWrite.lean::
    GraphState.writeRules` keeps folding the bare `writeDirect`, so the two differ at any
    `bridged_in_shapes` endpoint — and, critically, they are **not definitionally equal
    even where nothing is bridged**, for the FUEL reason and not the bridging reason:
    `GraphState.bridgePre`'s two unconditional `addNode`s shift `GraphState.reach`'s fuel
    (`State.lean::GraphState.reach`, `nodes.length + 1`), so the admission probe reads a
    different state on every write. Do NOT try to recover `= σ.writeRules S t` under an
    added premise; there is no premise that repairs a fuel difference.

    ⚠ **THE NAME IS GATE-PINNED AND MUST NOT BE DELETED** — it is in
    `formal/audited_theorems.txt` and carries a `#print axioms` row in `Audit.lean`, so
    `verify.sh` step 4a reds if it disappears. Only the STATEMENT moves. That the move is
    affordable is MEASURED (2026-09-13d, re-confirmed 2026-09-14): this theorem has **no
    consumer anywhere in the Lean development** — the only tree-wide hits are the audit row
    and prose citations, so restating it costs zero call sites.

    **Not bridging `writeRules` too is the recorded decision**: it is the PLAIN shadow
    rebuild `ReachedByRulesAdmitted` folds (see the caller note on `writeRulesRaw`), its
    reverse cone is 40 modules against `writeBridgedOne`'s 24, and the live chain reaches it
    only through `CascadeStrataSettle.lean::untOccCount_eq_plainOcc_of_notLeaf`. The
    surviving mathematical content of the old statement is the LIST half,
    `rewriteClosureL_rawWriteTuples_untaintedSchema` above — a pure list equation naming no
    `GraphState`, which is why that half was extracted at step 3 rather than here, and which
    needs no edit at all under the re-point. -/
theorem writeRulesRaw_untaintedSchema {σ : GraphState} {S : Schema} {t : Tuple}
    (h : ∀ d ∈ S.defs, isDerived S d.1 = false) :
    σ.writeRulesRaw S t
      = (rewriteClosure S t).foldl (fun acc u => acc.writeBridgedOne u) σ := by
  unfold GraphState.writeRulesRaw
  rw [rewriteClosureL_rawWriteTuples_untaintedSchema h]

/-! ## Invariant preservation — free, via the list-generic fold family

The whole point of scope doc §11.1's "fork the TUPLE, not the write path": the per-triple
materializer is list-generic, so every `∀ (ts : List Tuple)` fold lemma applies to the
leaf-routed expansion verbatim, with no clone.

★ **`P6` step 3b, 2026-09-14 — the five below are the RE-POINT'S MECHANICAL HALF, and the
fact that they are mechanical is the load-bearing claim.** Each was
`*_foldl_writeDirect` (`RulesWrite.lean`) and is now `*_foldl_writeBridgedOne`
(`UsStarWrite.lean`'s fold family, landed by step 2). Every STATEMENT here is unchanged and
every proof is a one-name swap, because the five bridged twins were written with
binder shapes byte-identical to the `writeDirect` originals and carry **no extra premise**
— in particular `structInv_foldl_writeBridgedOne` needs no `edgesClosed` side condition and
`inv_foldl_writeBridgedOne` still takes exactly `(h : Inv S σ) (hre : ResidueEmpty σ)`. If a
future edit makes one of these need a premise, that is a real widening and the consumers
below it must be re-examined, not `_`-filled. -/

theorem structInv_writeRulesRaw {S S' : Schema} {σ : GraphState} (h : StructInv S' σ)
    (t : Tuple) : StructInv S' (σ.writeRulesRaw S t) :=
  structInv_foldl_writeBridgedOne _ h

theorem residueEmpty_writeRulesRaw {S : Schema} {σ : GraphState} (t : Tuple)
    (h : ResidueEmpty σ) : ResidueEmpty (σ.writeRulesRaw S t) :=
  residueEmpty_foldl_writeBridgedOne _ h

theorem inv_writeRulesRaw {S S' : Schema} {σ : GraphState} (h : Inv S' σ)
    (hre : ResidueEmpty σ) (t : Tuple) : Inv S' (σ.writeRulesRaw S t) :=
  inv_foldl_writeBridgedOne _ h hre

theorem quiescent_writeRulesRaw {S : Schema} {σ : GraphState} (t : Tuple)
    (h : Quiescent σ) : Quiescent (σ.writeRulesRaw S t) :=
  quiescent_foldl_writeBridgedOne _ h

/-- ⚠ **SUFFIX form — `writeRulesRaw_schema`, not `schema_writeRulesRaw`.** Its four
    downstream consumers (`CascadeStrata.lean`, `CascadeStrataAssemble.lean`,
    `CascadeStrataSettle.lean` ×2) stay green across re-point #2 because the statement does
    not move; only the discharger name does. -/
theorem writeRulesRaw_schema (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.writeRulesRaw S t).schema = σ.schema :=
  schema_foldl_writeBridgedOne _

/-! ## Step 4c-ii, step 2 — the superset EXTRAS are all leaf nodes

`writeRulesRaw`'s closure list is a strict superset of `writeRules`' **even for an
untainted `t`**: the seeds agree there (`rawWriteTuples_untainted`), but
`rewriteClosureL` closes under `schemaRewritesL = schemaRewrites S ++ leafRewrites S`,
and a `leafRewrites` rule can fire on an untainted relation and mint a leaf-targeted
copy `rewriteClosure` never produces — `lrV_closure_reaches_leaf` /
`lrV_closure_today_misses_leaf` below are that pair at a store. Until now no proof
slice OWNED the obligation "every such extra is leaf-targeted"; the post-re-point
shadow classification (`Scratch4cii.lean`, PROOF_STATUS 2026-08-28d) consumes it in
the shape of `Leaf.lean::LeafNode`. This section proves it against TODAY's tree, so
the red middle of the 4c-ii re-point consumes a green fact instead of re-deriving it.

Why the proof needs no saturation fact: the bounded kernels run at the SAME fuel
(`S.keys.length + 1`), so the two closures are walked in LOCKSTEP — layer `n` of
`rewriteClosureAuxL` is compared to layer `n` of `rewriteClosureAux`, and a
leaf-shaped tuple never re-enters the untainted side because no `schemaRewrites` rule
MATCHES a leaf name (`hmd`). That sidesteps "the bounded closure is closed under one
more step", which only holds via the rank argument (`RestrictBase.lean` §saturation)
and is not needed here.

On the premises of the payoff theorem:
* `hmd` — no untainted rewrite matches a leaf name. Without it, a schema whose
  expression references a DOTTED name would let a `schemaRewrites` rule fire on a
  leaf-routed seed and mint an extra that is neither in `rewriteClosure S t` nor
  leaf-targeted. It is the `isLeafPred` shadow of
  `RestrictBase.lean::RewriteMatchDeclared` + `WF` (declared ⇒ dot-free): a consumer
  holding those discharges it as
  `fun r hr => isLeafPred_eq_false_of_relNameOK (relNameOK_of_mem_keys hWF (hMatch r hr).1)`.
  It is taken EXPLICITLY, not derived, because `RewriteMatchDeclared` lives in
  `RestrictBase.lean`, whose imports (`ReconcileCorrect`, `RulesBareStar`) would drag
  the Reconcile cone under this module and void the header's "the cone is one file"
  accounting.
* `hne` — a derived relation name is non-empty. `LeafNode` carries a mandatory
  `leafPublic p ≠ ""` conjunct (E3's residual guard, `Leaf.lean::LeafNode`), and
  `Core/Schema.lean::relNameOK` does not forbid `""`, so the fact must arrive as a
  premise. ⚠ It is NOT supplied by `StoreValidRulesD`, which constrains stored
  tuples, never relation-name non-emptiness.
* `hon` — a `STAR`-named object routes `objNode` to its `w_all` variant, which
  `LeafNode` deliberately excludes (it models the target of a raw leaf-routed write,
  and object wildcards on derived relations are scope-rejected,
  `zanzibar_utils_v1.py::UnsupportedByGraphIndex`). -/

/-- A rule can only produce `some` by matching, and it keeps the object: the four
    facts every consumer of `applyRRule` re-derives, extracted once.
    (`RulesWrite.lean::applyRRule` — both kinds keep `t.object` and emit `r.outRel`.) -/
theorem applyRRule_some {r : RRule} {t u : Tuple} (h : applyRRule r t = some u) :
    u.object = t.object ∧ u.relation = r.outRel ∧
      t.relation = r.matchRel ∧ t.object.type = r.objectType := by
  unfold applyRRule at h
  split at h
  next hc =>
    split at h
    all_goals
      have heq := Option.some.inj h
      subst heq
      exact ⟨rfl, rfl, hc.1, hc.2⟩
  next => simp at h

/-- The `objectType` companion of `outRel_mem_of_mem_exprArms`: `exprArms` stamps the
    object type it was given onto every arm. -/
theorem objectType_of_mem_exprArms {ot outRel : String} {e : Expr} {r : RRule}
    (h : r ∈ exprArms ot outRel e) : r.objectType = ot := by
  induction e with
  | direct _ => simp [exprArms] at h
  | computed _ => simp [exprArms] at h; subst h; rfl
  | ttu _ _ => simp [exprArms] at h; subst h; rfl
  | union a b iha ihb =>
      rw [exprArms, List.mem_append] at h
      exact h.elim iha ihb
  | inter _ _ _ _ => simp [exprArms] at h
  | excl _ _ _ _ => simp [exprArms] at h

/-- **Every leaf rule targets a minted leaf of a relation DERIVED on its own object
    type.** Sharpens `isLeafPred_outRel_of_mem_leafRewrites` from "carries a dot" to
    the full provenance the `LeafNode` conclusion needs (`publicOfLeaf` demands
    `isDerived`, not just a dot). -/
theorem mem_leafRewrites_shape {S : Schema} {r : RRule} (h : r ∈ leafRewrites S) :
    ∃ R i, r.outRel = leafPred R i ∧ isDerived S (r.objectType, R) = true := by
  unfold leafRewrites at h
  obtain ⟨d, hd, hr⟩ := List.mem_flatMap.mp h
  have hder : isDerived S d.1 = true := (List.mem_filter.mp hd).2
  unfold keyLeafRewrites at hr
  obtain ⟨pi, _, hpi⟩ := List.mem_flatMap.mp hr
  split at hpi
  · refine ⟨d.1.2, pi.2, outRel_mem_of_mem_exprArms hpi, ?_⟩
    rw [objectType_of_mem_exprArms hpi]
    exact hder
  · simp at hpi

/-- A fired leaf rule's OUTPUT is leaf-shaped whatever tuple it fired on: minted leaf
    relation, derived on the (preserved) object's type. This is why the invariant
    below is absorbing — leaf rules can chain off anything and still land leaf-shaped. -/
theorem leafShape_of_applyRRule_leafRewrites {S : Schema} {r : RRule} {u v : Tuple}
    (hr : r ∈ leafRewrites S) (h : applyRRule r u = some v) :
    ∃ R i, v.relation = leafPred R i ∧ isDerived S (v.object.type, R) = true ∧
      v.object = u.object := by
  obtain ⟨R, i, hout, hder⟩ := mem_leafRewrites_shape hr
  obtain ⟨hobj, hrel, -, hty⟩ := applyRRule_some h
  refine ⟨R, i, hrel.trans hout, ?_, hobj⟩
  rw [hobj, hty]
  exact hder

/-- The `hmd` discharge bridge: a dot-free name is not a leaf predicate. With
    `relNameOK_of_mem_keys`, this turns `RestrictBase.lean::RewriteMatchDeclared`'s
    "declared" into this section's "matches no leaf name" without importing
    `RestrictBase` (see the section header for why the import is refused). -/
theorem isLeafPred_eq_false_of_relNameOK {R : String} (h : relNameOK R) :
    isLeafPred R = false := by
  by_contra hne
  refine h ?_
  have hne' : isLeafPred R = true := by simpa using hne
  have hmem : '.' ∈ R.toList := by
    simpa [isLeafPred, List.contains_eq_mem] using hne'
  simpa [String.contains_char_eq] using hmem

/-- **The lockstep kernel induction.** If every current-frontier tuple is either on
    the untainted frontier or leaf-shaped (and shares `t`'s object), the same split
    holds of every tuple either kernel ever produces — at EQUAL fuel, which is what
    lets the payoff theorem instantiate both kernels at `S.keys.length + 1` with no
    saturation lemma. Leaf-shaped means: relation is a minted leaf name of a relation
    derived on `t.object.type`. The two step cases:
    * an untainted rule cannot fire on a leaf-shaped tuple (`hmd` vs
      `isLeafPred_leafPred`), so the untainted side only ever steps from the
      untainted side — in lockstep;
    * a leaf rule's output is leaf-shaped from ANY input
      (`leafShape_of_applyRRule_leafRewrites`) — the invariant absorbs it. -/
theorem rewriteClosureAuxL_extras {S : Schema}
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false) (t : Tuple) :
    ∀ (n : Nat) (cur curB : List Tuple),
      (∀ u ∈ cur, u.object = t.object) →
      (∀ u ∈ cur, u ∈ curB ∨ ∃ R i, u.relation = leafPred R i ∧
          isDerived S (t.object.type, R) = true) →
      ∀ v ∈ rewriteClosureAuxL S n cur,
        (v ∈ rewriteClosureAux S n curB ∨ ∃ R i, v.relation = leafPred R i ∧
            isDerived S (t.object.type, R) = true) ∧ v.object = t.object := by
  intro n
  induction n with
  | zero =>
      intro cur curB hobj hinv v hv
      exact ⟨hinv v hv, hobj v hv⟩
  | succ n ih =>
      intro cur curB hobj hinv v hv
      simp only [rewriteClosureAuxL, List.mem_append] at hv
      rcases hv with hv | hv
      · rcases hinv v hv with hB | hleaf
        · refine ⟨Or.inl ?_, hobj v hv⟩
          simp only [rewriteClosureAux, List.mem_append]
          exact Or.inl hB
        · exact ⟨Or.inr hleaf, hobj v hv⟩
      · have hstep_obj : ∀ w ∈ cur.flatMap (rewriteStepL S), w.object = t.object := by
          intro w hw
          obtain ⟨u, hu, hwu⟩ := List.mem_flatMap.mp hw
          unfold rewriteStepL at hwu
          obtain ⟨r, _, hr⟩ := List.mem_filterMap.mp hwu
          rw [(applyRRule_some hr).1]
          exact hobj u hu
        have hstep_inv : ∀ w ∈ cur.flatMap (rewriteStepL S),
            w ∈ curB.flatMap (rewriteStep S) ∨ ∃ R i, w.relation = leafPred R i ∧
              isDerived S (t.object.type, R) = true := by
          intro w hw
          obtain ⟨u, hu, hwu⟩ := List.mem_flatMap.mp hw
          unfold rewriteStepL at hwu
          obtain ⟨r, hrmem, hr⟩ := List.mem_filterMap.mp hwu
          rw [schemaRewritesL, List.mem_append] at hrmem
          rcases hrmem with hrS | hrL
          · rcases hinv u hu with hB | ⟨R, i, hrel, _⟩
            · refine Or.inl (List.mem_flatMap.mpr ⟨u, hB, ?_⟩)
              unfold rewriteStep
              exact List.mem_filterMap.mpr ⟨r, hrS, hr⟩
            · exfalso
              have hm : u.relation = r.matchRel := (applyRRule_some hr).2.2.1
              have hlp : isLeafPred r.matchRel = true := by
                rw [← hm, hrel]; exact isLeafPred_leafPred R i
              rw [hmd r hrS] at hlp
              exact Bool.noConfusion hlp
          · obtain ⟨R, i, hrel, hder, hwo⟩ := leafShape_of_applyRRule_leafRewrites hrL hr
            refine Or.inr ⟨R, i, hrel, ?_⟩
            rw [hwo, hobj u hu] at hder
            exact hder
        obtain ⟨hres, hvo⟩ := ih (cur.flatMap (rewriteStepL S))
          (curB.flatMap (rewriteStep S)) hstep_obj hstep_inv v hv
        rcases hres with hB | hleaf
        · refine ⟨Or.inl ?_, hvo⟩
          simp only [rewriteClosureAux, List.mem_append]
          exact Or.inr hB
        · exact ⟨Or.inr hleaf, hvo⟩

/-- **The unowned superset-extras fact (4c-ii step 2).** Every tuple the leaf-routed
    closure produces is either one today's rewrite closure already produced, or its
    target node is a `LeafNode` — the exact split the post-re-point shadow
    classification consumes, stated pre-re-point so it is green-stoppable. Seeds:
    untainted `t` seeds `[t]` on both sides (`rawWriteTuples_untainted`); derived `t`
    seeds only leaf-shaped tuples (`mem_rawWriteRels_derived`). The kernels then run
    in lockstep (`rewriteClosureAuxL_extras`), and `publicOfLeaf_leafPred` /
    `leafPublic_leafPred` + `hne` assemble a leaf-shaped survivor into `LeafNode`. -/
theorem rewriteClosureL_extras_leafNode {S : Schema} (hWF : WF S)
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false)
    (hne : ∀ dt R, isDerived S (dt, R) = true → R ≠ "")
    {t : Tuple} (hon : t.object.name ≠ STAR) :
    ∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
      u ∈ rewriteClosure S t ∨ LeafNode S (objNode u.object u.relation) := by
  intro u hu
  rw [mem_rewriteClosureL_iff] at hu
  unfold rewriteClosureRawL at hu
  have hobj : ∀ w ∈ rawWriteTuples S t, w.object = t.object := by
    intro w hw
    obtain ⟨r, _, rfl⟩ := List.mem_map.mp hw
    rfl
  have hinv : ∀ w ∈ rawWriteTuples S t, w ∈ [t] ∨ ∃ R i, w.relation = leafPred R i ∧
      isDerived S (t.object.type, R) = true := by
    intro w hw
    by_cases hd : isDerived S (t.object.type, t.relation) = true
    · obtain ⟨r, hr, rfl⟩ := List.mem_map.mp hw
      refine Or.inr ?_
      obtain ⟨i, rfl⟩ := mem_rawWriteRels_derived hd hr
      exact ⟨t.relation, i, rfl, hd⟩
    · rw [rawWriteTuples_untainted (by simpa using hd)] at hw
      exact Or.inl hw
  obtain ⟨hres, huo⟩ := rewriteClosureAuxL_extras hmd t (S.keys.length + 1)
    (rawWriteTuples S t) [t] hobj hinv u hu
  rcases hres with hmem | ⟨R, i, hrel, hder⟩
  · exact Or.inl (mem_rewriteClosure_iff.mpr hmem)
  · refine Or.inr ⟨t.object.type, t.object.name, leafPred R i, ?_, ?_, hon, ?_⟩
    · rw [publicOfLeaf_leafPred hWF hder i]; rfl
    · rw [leafPublic_leafPred R i (relNameOK_of_isDerived hWF (k := (t.object.type, R)) hder)]
      exact hne t.object.type R hder
    · rw [huo, hrel]

/-- The `hne` discharge bridge. `hne` quantifies over ALL strings, so it is not
    decidable at a concrete schema; but derived ⇒ declared (`taintedKeys_subset_keys`),
    so an `.all`-scan of the KEYS list — which IS `by decide` at any concrete schema —
    suffices. The nonvacuity witness below consumes it, and 4c-ii can too. -/
theorem hne_of_keys_nonempty {S : Schema} (h : S.keys.all (fun k => k.2 != "") = true) :
    ∀ dt R, isDerived S (dt, R) = true → R ≠ "" := by
  intro dt R hd
  have hk : (dt, R) ∈ S.keys := taintedKeys_subset_keys S (by
    simpa [isDerived, List.contains_eq_mem] using hd)
  have := List.all_eq_true.mp h _ hk
  simpa using this

/-! ## Step 4c-ii, step 4 — `NoLeafSubjects` and the SUBJECT half of the extras split

`rewriteClosureL_extras_leafNode` above owns the **object** half of the widened shadow
extras: every superset extra's target node is a `LeafNode`. The re-point's other half is
the mirror obligation on the **subject** side — the goals of the shape
`¬ (DerNode S (subjNode u.subject) ∨ LeafNode S (subjNode u.subject))` that
`CascadeStable.lean` / `CascadeStrataSettle.lean` open once `UntaintedShadow` is
re-pointed at the disjunction. The `DerNode` half of those goals is owned by
`ReconcileCorrect.lean::rewriteClosure_subject_pred_gen` (leg 7 step 3); the `LeafNode`
half needs one fact this tree did not have.

**Where a subject predicate can come from at all.** `RulesWrite.lean::applyRRule` is the
only constructor of a rewritten tuple's subject, and it has exactly two branches:
`.computed` copies `t.subject` through verbatim, and `.ttu tr` overwrites the predicate
with `tr`. So "the rewrite machinery never MINTS a leaf-named subject predicate" is
precisely a statement about the compiled rules' TTU targets — nothing else in the model
can produce one. That statement is `NoLeafSubjects`.

## ★★ Why the quantifier ranges over `schemaRewritesL`, and not over `schemaRewrites`

⚠ **This is the trap the step exists to avoid, and it is live in this very file.**
`LeafRuleWitness.lrV_untainted_layer_silent` proves `schemaRewrites SlV = []`, so ANY
premise of the form `∀ r ∈ schemaRewrites S, …` is discharged **vacuously** at `SlV` —
which is exactly how `rewriteClosureL_extras_leafNode`'s `hmd` is discharged, making the
`exfalso` in `rewriteClosureAuxL_extras`' untainted-rule case dead under every fixture in
this file. A `NoLeafSubjects` quantified over the untainted layer alone would reproduce
that shape while looking done.

It therefore ranges over `schemaRewritesL S = schemaRewrites S ++ leafRewrites S`, and
the witness schema `LeafRuleWitness.SnlBoth` carries a TTU rule in **each** half, both of
which fire in one closure. The two negative controls
(`LeafRuleWitness.noLeafSubjects_false_leafLayer` /
`::noLeafSubjects_false_untLayer`) are one per layer: each is the red produced by
narrowing the quantifier to the other layer. -/

/-- The subject predicate a rule REWRITES TO, as a 0-or-1 element list: `computed` copies
    the subject through and mints nothing, `ttu tr` overwrites the predicate with `tr`
    (`RulesWrite.lean::applyRRule`).

    A `List` rather than an `Option` or an `∀ tr, r.kind = .ttu tr → …` binder **on
    purpose**: it makes `NoLeafSubjects` a nest of BOUNDED quantifiers over decidable
    atoms, hence `by decide`-able at a concrete schema. The binder shape is not
    decidable, and every witness below would have had to be a hand proof — which is how
    an unmeasured premise gets its non-vacuity asserted instead of checked. -/
def ttuTargets (r : RRule) : List String :=
  match r.kind with
  | .computed => []
  | .ttu tr => [tr]

theorem ttuTargets_of_kind {r : RRule} {tr : String} (h : r.kind = RuleKind.ttu tr) :
    ttuTargets r = [tr] := by
  unfold ttuTargets; rw [h]

/-- `NotLeafName` is `p = BARE ∨ isLeafPred p = false`, both halves decidable — but it is
    a plain `def`, so instance synthesis will not unfold it. Supplied here so
    `NoLeafSubjects` is `by decide`-able. -/
instance : DecidablePred NotLeafName := fun p =>
  inferInstanceAs (Decidable (p = BARE ∨ isLeafPred p = false))

/-- **No rule of the FULL leaf-routed rule set mints a leaf-named subject predicate.**
    Quantified over `schemaRewritesL` — see the ★★ note above for why the untainted-layer
    -only form is the vacuous one. -/
def NoLeafSubjects (S : Schema) : Prop :=
  ∀ r ∈ schemaRewritesL S, ∀ tr ∈ ttuTargets r, NotLeafName tr

/-- …and it is DECIDABLE at a concrete schema, which is what lets the witnesses below be
    `decide` pins rather than hand proofs. (A plain `def` is not unfolded by instance
    synthesis, so the instance has to be stated.) -/
instance (S : Schema) : Decidable (NoLeafSubjects S) :=
  inferInstanceAs (Decidable (∀ r ∈ schemaRewritesL S, ∀ tr ∈ ttuTargets r, NotLeafName tr))

/-! ### `LeafScope` — the four schema-level facts the FLIPPED write leg needs

Step 4c-ii re-points the logged write leg at `rewriteClosureL S (rawWriteTuples S t)`.
Two shadow obligations open at every W3d / W3d-2 chain state, and between them they want
FOUR schema facts that the pre-flip development never threaded:

* the SUBJECT half — `rewriteClosureL_subject_not_leafNode` wants `NoLeafSubjects S`
  (`CascadeStable.lean::admissionNameShape_does_not_give_noLeafSubjects` refutes deriving
  it from the three name-shape fields `GraphAdmission` already carried);
* the OBJECT half — `rewriteClosureL_extras_leafNode` wants `WF S`, its `hmd`
  (no untainted rule MATCHES a leaf name) and its `hne` (a derived relation's public name
  is non-empty, `LeafNode`'s E3 residual guard).

They are bundled into ONE carrier rather than threaded as four separate premises purely to
keep the re-point's signature churn to one binder per theorem: the cone between
`reachedByW3d_shadow` and `FullScope.lean` is ~20 signatures deep, and four binders there
is four times the chance of a mis-ordered call site. Every field is decidable at a concrete
schema, which is what makes the ultimate discharge `by decide` at each `GraphAdmission`
witness. -/

/-- **The leaf-routing scope discipline.** See the section note above; `wf` and
    `matchNotLeaf` feed `rewriteClosureL_extras_leafNode`'s `hWF`/`hmd`, `keysNonempty`
    feeds its `hne` through `LeafScope.derivedNameNonempty`, and `noLeafSubjects` feeds
    `rewriteClosureL_subject_not_leafNode`.

    `keysNonempty` is stated in the `.all` (decidable) form rather than as the `∀ dt R,
    isDerived …` binder the consumer wants, for the reason `hne_of_keys_nonempty`'s
    docstring gives: the binder form quantifies over ALL strings and so is not `by
    decide`-able, and an undecidable field is how a scope premise gets asserted instead of
    checked. -/
structure LeafScope (S : Schema) : Prop where
  wf : WF S
  matchNotLeaf : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false
  noLeafSubjects : NoLeafSubjects S
  keysNonempty : S.keys.all (fun k => k.2 != "") = true

/-- The `hne` shape `rewriteClosureL_extras_leafNode` consumes, from the decidable field. -/
theorem LeafScope.derivedNameNonempty {S : Schema} (h : LeafScope S) :
    ∀ dt R, isDerived S (dt, R) = true → R ≠ "" :=
  hne_of_keys_nonempty h.keysNonempty

/-- **`keysNonempty` IS a new assumption** — the kernel refutation of the tempting shortcut
    "`WF` already forbids a degenerate relation name, so drop the field".

    Per `docs/sabotage-procedure.md`, the narrowest plausible weakening of `LeafScope` is to
    delete `keysNonempty` and try to recover `derivedNameNonempty` from `wf`; this says that
    cannot work, at a fixture that already exists for exactly this hazard
    (`Leaf.lean::LeafWitness.SwEmptyRel`, minted for the E3 `leafPublic … ≠ ""` guard —
    `::swEmptyRel_bare_subject_not_leafNode`). The schema is `WF` (its declared names carry no
    `'.'`) and declares a DERIVED relation named `""`, so the `.all`-scan is false. It is not
    a realistic schema — Python's `check_name` rejects the empty identifier, which is what
    makes the field an honest scope claim rather than a hole — but `WF` does not know that. -/
theorem wf_does_not_give_keysNonempty :
    WF LeafWitness.SwEmptyRel
      ∧ isDerived LeafWitness.SwEmptyRel ("user", "") = true
      ∧ LeafWitness.SwEmptyRel.keys.all (fun k => k.2 != "") = false := by
  refine ⟨⟨?_⟩, by decide, by decide⟩
  intro p hp
  simp only [LeafWitness.SwEmptyRel, List.mem_cons, List.not_mem_nil, or_false] at hp
  rcases hp with rfl | rfl <;> simp [relNameOK]

/-- `matchNotLeaf` from the shape the admission fragment already carries: a rewrite's match
    key is DECLARED (`RestrictBase.lean::RewriteMatchDeclared`, whose first component this
    takes as `hdecl`), declared names are dot-free (`WF`), and a dot-free name is not a leaf
    predicate. Stated over `hdecl` rather than over `RewriteMatchDeclared` itself so this
    file need not import `RestrictBase` (see the `isLeafPred_eq_false_of_relNameOK` note). -/
theorem matchNotLeaf_of_declared {S : Schema} (hWF : WF S)
    (hdecl : ∀ r ∈ schemaRewrites S, (r.objectType, r.matchRel) ∈ S.keys) :
    ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false :=
  fun r hr => isLeafPred_eq_false_of_relNameOK (relNameOK_of_mem_keys hWF (hdecl r hr))

/-- The subject-predicate half of `applyRRule_some`: a fired rule either keeps the
    subject predicate or replaces it with its own TTU target. There is no third case. -/
theorem applyRRule_subject_pred {r : RRule} {t u : Tuple} (h : applyRRule r t = some u) :
    u.subject.predicate = t.subject.predicate ∨ u.subject.predicate ∈ ttuTargets r := by
  unfold applyRRule at h
  split at h
  next =>
    split at h
    next =>
      have heq := Option.some.inj h
      subst heq
      exact Or.inl rfl
    next tr hk =>
      have heq := Option.some.inj h
      subst heq
      refine Or.inr ?_
      rw [ttuTargets_of_kind hk]
      simp
  next => simp at h

/-- One step of the FULL rule set preserves "the subject predicate is not a leaf name". -/
theorem rewriteStepL_subject_notLeafName {S : Schema} (hnl : NoLeafSubjects S)
    {t u : Tuple} (ht : NotLeafName t.subject.predicate) (h : u ∈ rewriteStepL S t) :
    NotLeafName u.subject.predicate := by
  unfold rewriteStepL at h
  obtain ⟨r, hr, hap⟩ := List.mem_filterMap.mp h
  rcases applyRRule_subject_pred hap with heq | hmem
  · rw [heq]; exact ht
  · exact hnl r hr _ hmem

/-- The kernel induction — the invariant is absorbing at every fuel and frontier. -/
theorem rewriteClosureAuxL_subject_notLeafName {S : Schema} (hnl : NoLeafSubjects S) :
    ∀ (n : Nat) (cur : List Tuple),
      (∀ w ∈ cur, NotLeafName w.subject.predicate) →
      ∀ v ∈ rewriteClosureAuxL S n cur, NotLeafName v.subject.predicate := by
  intro n
  induction n with
  | zero => intro cur hcur v hv; exact hcur v hv
  | succ n ih =>
      intro cur hcur v hv
      simp only [rewriteClosureAuxL, List.mem_append] at hv
      rcases hv with hv | hv
      · exact hcur v hv
      · refine ih _ ?_ v hv
        intro w hw
        obtain ⟨u, hu, hwu⟩ := List.mem_flatMap.mp hw
        exact rewriteStepL_subject_notLeafName hnl (hcur u hu) hwu

/-- **The closure corollary.** Under `NoLeafSubjects`, the leaf-routed closure of a seed
    list whose subject predicates are all non-leaf names produces only non-leaf-named
    subject predicates. -/
theorem rewriteClosureL_subject_notLeafName {S : Schema} (hnl : NoLeafSubjects S)
    {seeds : List Tuple} (hs : ∀ w ∈ seeds, NotLeafName w.subject.predicate)
    {u : Tuple} (hu : u ∈ rewriteClosureL S seeds) : NotLeafName u.subject.predicate := by
  rw [mem_rewriteClosureL_iff] at hu
  unfold rewriteClosureRawL at hu
  exact rewriteClosureAuxL_subject_notLeafName hnl _ seeds hs u hu

/-- **The shape the 4c-ii write leg consumes.** `rawWriteTuples` only re-addresses the
    RELATION (`{t with relation := r}`), so the seed premise collapses to a fact about
    the raw write's own subject; the closure then never mints a leaf-named subject, so
    no subject node of the leaf-routed write's expansion is a `LeafNode` — at ANY schema
    satisfying `NoLeafSubjects`, with no `WF`, no store, and no fixture. -/
theorem rewriteClosureL_subject_not_leafNode {S : Schema} (hnl : NoLeafSubjects S)
    {t : Tuple} (ht : NotLeafName t.subject.predicate) :
    ∀ u ∈ rewriteClosureL S (rawWriteTuples S t), ¬ LeafNode S (subjNode u.subject) := by
  intro u hu
  refine not_leafNode_of_notLeafName ?_
  rw [subjNode_pred]
  refine rewriteClosureL_subject_notLeafName hnl ?_ hu
  intro w hw
  unfold rawWriteTuples at hw
  obtain ⟨r, _, rfl⟩ := List.mem_map.mp hw
  exact ht

/-- The BARE specialisation — a raw write of a concrete (non-userset) subject, which is
    the overwhelmingly common caller shape. -/
theorem rewriteClosureL_subject_not_leafNode_bare {S : Schema} (hnl : NoLeafSubjects S)
    {t : Tuple} (ht : t.subject.predicate = BARE) :
    ∀ u ∈ rewriteClosureL S (rawWriteTuples S t), ¬ LeafNode S (subjNode u.subject) :=
  rewriteClosureL_subject_not_leafNode hnl (show NotLeafName _ from Or.inl ht)

/-! ## The WRITE-PATH re-point — the structural twins the re-pointed fold needs

`Cascade.lean::GraphState.writeLoggedRules` folds `rewriteClosure S t`; the re-point makes
it fold `rewriteClosureL S (rawWriteTuples S t)`, the same list `::writeRulesRaw` above
already folds. Its consumers in `CascadeStable.lean` reach for
`RulesCorrect.lean::rewriteClosure_object` and `::rewriteClosure_produced`, neither of which
has an L twin — obligations **(B)** and **(C)** of the write-path cone
(`formal/history/PROOF_STATUS.md` `## Session 2026-09-03c` §4).

⚠ **SUPERSEDED FRAMING.** These were proved on the then-UNFLIPPED tree as §11.12 **rule 6**'s
*green additive prefix* — additive, consuming nothing, changing no declaration and no pin.
That framing described the tree they landed on, not the tree they sit in: post-flip both
legs (`writeLoggedRules`, and `removeLoggedRules` since R5) fold
`rewriteClosureL S (rawWriteTuples S t)`, so `rewriteClosureL_object` and
`rewriteClosureL_produced` are LOAD-BEARING on the live write and remove paths — every
notarget/subject-shape argument in `CascadeStable.lean` and `CascadeStrataSettle.lean` goes
through them. Landing them before opening the cone still made what remained smaller — the
move that cut the `hcr` thread 79 → 62 on 2026-09-02c — but they are no longer a prefix.

The proofs transcribe their plain twins modulo `schemaRewrites → schemaRewritesL`, because
`rewriteStepL` (`:188`) differs from `RulesWrite.lean::rewriteStep` only in which rule list
it `filterMap`s, and `applyRRule` is shared. `applyRRule_some` above is the four-fact
extraction both need, which is why `RulesCorrect` is not imported here.

## ★ CONTROLLED — two sabotages, run 2026-09-05 (`docs/sabotage-procedure.md`)

Everything here is ADDITIVE and therefore INERT, so a green build vets nothing. The one
claim that can actually be wrong is that **`schemaRewritesL` is load-bearing** — that these
are not just the plain lemmas with a longer name. Both sabotages are that claim, attacked at
its two independent entry points. Restored from a byte-exact `cp` backup, never
`git checkout --` (trap (aa)); tree byte-identical after, `1089 jobs`, `rc=0`, zero `sorry`.

**(SAB-A) `TtuTargetsSatL` narrowed to `schemaRewrites`** — the narrowest plausible
weakening of obligation (A)'s new premise, i.e. "it was `NoTtuTarget` all along". `rc=1`,
SIX errors, and the two that matter are the WITNESSES rather than the plumbing:

```text
LeafRules.lean:859:55: Type mismatch                    -- noLeafSubjects_iff_ttuTargetsSatL
LeafRules.lean:871:16: Application type mismatch        -- rewriteStepL_subject_pred_gen
LeafRules.lean:1348:8: (kernel) application type mismatch  -- stP_full_layer_does_target_viewer
LeafRules.lean:1354:8: (kernel) application type mismatch  -- ttuTargetsSatL_snlBoth_ne_banned
```

`:1348` firing is the whole point: under the narrowed premise `TtuTargetsSatL SlStP
(· ≠ "viewer")` becomes VACUOUSLY TRUE (`stP_untainted_layer_silent`), so its negation stops
being provable. That is the `SlStP` pair doing the job it was written for — without it, the
narrowing would have been invisible at the witness layer and only the plumbing would have
complained.

**(SAB-B) `rewriteStepL_outRel`'s existential narrowed to `schemaRewrites`** — the same
attack on (B)/(C)'s side. `rc=1`, TWO errors, both attributable:

```text
LeafRules.lean:730:12: Application type mismatch  -- rewriteStepL_outRel
LeafRules.lean:786:23: Application type mismatch  -- rewriteClosureAuxL_produced
```

⚠ Both counts are LOWER bounds: Lean does not build the dependents of a failed module, and
`LeafRules` is upstream of the whole cascade chain (traps (k)/(v)). -/

/-- One L-rewrite step preserves the object — twin of
    `RulesCorrect.lean::rewriteStep_object`. -/
theorem rewriteStepL_object {S : Schema} {t u : Tuple} (h : u ∈ rewriteStepL S t) :
    u.object = t.object := by
  unfold rewriteStepL at h
  obtain ⟨r, _, hap⟩ := List.mem_filterMap.mp h
  exact (applyRRule_some hap).1

/-- One L-rewrite step's output relation is some FULL-rule-set rule's `outRel`, at that
    rule's object type — twin of `RulesCorrect.lean::rewriteStep_outRel`.

    ⚠ The existential ranges over `schemaRewritesL`, and that is not a cosmetic widening:
    a leaf rule's `outRel` is a MINTED LEAF NAME, which the untainted layer provably never
    emits (`not_isLeafPred_outRel_of_mem_schemaRewrites`). So the plain twin is not merely
    weaker at a leaf-routed output — it is false there. -/
theorem rewriteStepL_outRel {S : Schema} {t u : Tuple} (h : u ∈ rewriteStepL S t) :
    ∃ r ∈ schemaRewritesL S, r.objectType = u.object.type ∧ r.outRel = u.relation := by
  unfold rewriteStepL at h
  obtain ⟨r, hr, hap⟩ := List.mem_filterMap.mp h
  obtain ⟨hobj, hrel, -, hty⟩ := applyRRule_some hap
  exact ⟨r, hr, by rw [hobj, hty], hrel.symm⟩

/-- Object preservation across the L closure kernel, over an ARBITRARY seed list — which is
    what the leaf-routed write needs, its seed being the `rawWriteTuples` fan-out rather
    than a singleton. Twin of `RulesCorrect.lean::rewriteClosureAux_object`. -/
theorem rewriteClosureAuxL_object {S : Schema} {O : ObjectRef} :
    ∀ (n : Nat) (cur : List Tuple), (∀ w ∈ cur, w.object = O) →
      ∀ u ∈ rewriteClosureAuxL S n cur, u.object = O := by
  intro n
  induction n with
  | zero => intro cur hcur u hu; exact hcur u hu
  | succ m ih =>
      intro cur hcur u hu
      rw [rewriteClosureAuxL, List.mem_append] at hu
      rcases hu with hin | hrec
      · exact hcur u hin
      · refine ih _ ?_ u hrec
        intro w hw
        rw [List.mem_flatMap] at hw
        obtain ⟨x, hx, hwx⟩ := hw
        rw [rewriteStepL_object hwx]; exact hcur x hx

/-- **(B) Every leaf-routed closure tuple carries the raw write's object.** Twin of
    `RulesCorrect.lean::rewriteClosure_object`, at the seed the re-pointed
    `writeLoggedRules` fold uses.

    Object preservation survives the fan-out for a reason worth naming: `Leaf.lean:762
    rawWriteTuples` re-addresses the RELATION only (`fun r => { t with relation := r }`),
    so the entire seed list already shares `t.object` before the closure starts. -/
theorem rewriteClosureL_object {S : Schema} {t u : Tuple}
    (h : u ∈ rewriteClosureL S (rawWriteTuples S t)) : u.object = t.object := by
  rw [mem_rewriteClosureL_iff] at h
  unfold rewriteClosureRawL at h
  refine rewriteClosureAuxL_object _ _ ?_ _ h
  intro w hw
  unfold rawWriteTuples at hw
  obtain ⟨r, _, rfl⟩ := List.mem_map.mp hw
  rfl

/-- Every `rewriteClosureAuxL` member is in the seed list or is an L-rewrite output. Twin of
    `RulesCorrect.lean::rewriteClosureAux_produced`. -/
theorem rewriteClosureAuxL_produced {S : Schema} :
    ∀ (n : Nat) (cur : List Tuple) {u : Tuple}, u ∈ rewriteClosureAuxL S n cur →
      u ∈ cur ∨ ∃ r ∈ schemaRewritesL S,
        r.objectType = u.object.type ∧ r.outRel = u.relation := by
  intro n
  induction n with
  | zero => intro cur u hu; exact Or.inl hu
  | succ m ih =>
      intro cur u hu
      rw [rewriteClosureAuxL, List.mem_append] at hu
      rcases hu with hin | hrec
      · exact Or.inl hin
      · rcases ih _ hrec with hcur | hout
        · rw [List.mem_flatMap] at hcur
          obtain ⟨x, _, hux⟩ := hcur
          exact Or.inr (rewriteStepL_outRel hux)
        · exact Or.inr hout

/-- **(C) Every leaf-routed closure tuple is a re-addressed seed or an L-rewrite output.**
    Twin of `RulesCorrect.lean::rewriteClosure_produced`.

    ⚠ **The left disjunct is `u ∈ seeds`, NOT `u = t`.** The plain twin can say `u = t`
    because its closure seeds with the singleton `[t]`; the leaf-routed one seeds with the
    measured FAN-OUT `rawWriteTuples S t`, so a member may be any of the re-addressed
    storage-leaf copies. A consumer wanting the raw write back must compose with
    `rewriteClosureL_object` (same object) and `rawWriteTuples`' relation re-addressing.
    The singleton form does NOT survive the re-point, and that is content of the leg rather
    than an accident of how this statement is written. -/
theorem rewriteClosureL_produced {S : Schema} {seeds : List Tuple} {u : Tuple}
    (h : u ∈ rewriteClosureL S seeds) :
    u ∈ seeds ∨ ∃ r ∈ schemaRewritesL S,
      r.objectType = u.object.type ∧ r.outRel = u.relation := by
  rw [mem_rewriteClosureL_iff] at h
  unfold rewriteClosureRawL at h
  exact rewriteClosureAuxL_produced _ _ h

/-- **`TtuTargetsSatL S Q`** — every TTU target of the FULL leaf-routed rule set satisfies
    `Q`. The predicate-generic form of `NoLeafSubjects` above (which is this at
    `Q := NotLeafName`), and the L twin of `ReconcileCorrect.lean::TtuTargetsSat`.

    ⚠ **This is obligation (A)'s NEW PREMISE, and it is genuinely new rather than a
    re-spelling.** `ReconcileCorrect.lean::NoTtuTarget` quantifies over `schemaRewrites S`
    ALONE, so it constrains only the untainted layer. `leafRewrites` (`:98`) runs `exprArms`
    over the closure leaves of DERIVED keys — exactly the keys `schemaRewrites` drops by its
    taint filter (`RulesWrite.lean:61-67`) — and `exprArms` on a `.ttu` arm emits a `.ttu`
    rule. So a derived key's TTU arm produces a leaf rule whose target `NoTtuTarget S R` says
    nothing about: **`NoTtuTarget` does NOT transfer to the L closure**, which is why the
    L-analogue below cannot simply re-use it.

    The reassuring half is that this quantification is ALREADY ACCEPTED in this tree at a
    different `Q`: `NoLeafSubjects` is literally it at `NotLeafName`, and that one is
    discharged from `GraphAdmission` (2026-09-02). So (A) needs a new premise, not a new
    KIND of premise.

    ★ **AND THE PREMISE LOOKS DISCHARGEABLE, which the record does not say** (it frames (A)
    as needing a new premise, full stop, and sizes the plan off that). Two facts, each
    verified first-hand 2026-09-05, compose:

    * `Leaf.lean::isPure`'s TTU arm is `!isDerived S (ty, ts) && !derivedAnywhere S tgt`, and
      `Leaf.lean::atomLeaves` emits `.closure (.ttu tgt ts)` ONLY under `isPure`. So every
      TTU target a LEAF rule can carry is `derivedAnywhere`-FALSE.
    * `FullScope.lean:238 W4Fragment.term` supplies `NoTtuTarget S R` only under
      `isDerived S (dt, R) = true` — as do all fifteen `Equiv.lean` consumers (`:281`…`:660`).
      So the `R` these consumers care about is always derived, i.e. `derivedAnywhere S R`.

    Those cannot both hold of the same name, so `tgt ≠ R` is FREE on the leaf half and
    `TtuTargetsSatL S (· ≠ R)` should follow from `NoTtuTarget S R` plus "R is derived".

    ⚠ **THIS WARNING IS NOW DISCHARGED — corrected 2026-09-05, re-checked against the live
    tree rather than deleted.** It read "NOT PROVED HERE — this is a source reading, not a
    kernel check", and named the missing lemma as "every `.closure` leaf of
    `persistedLeaves` is `isPure`", "for which NO purity lemma exists in the tree today".
    That lemma DOES exist now: see the section **"Obligation (A)'s PREMISE — DISCHARGED, not
    assumed"** below in this same file, which proves it and concludes `TtuTargetsSatL S
    (· ≠ R)` from `ReconcileCorrect.lean::NoTtuTarget S R` plus `isDerived S (dt, R) = true`
    — exactly the pair `FullScope.lean:238 W4Fragment.term` and all fifteen `Equiv.lean`
    consumers already carry. So obligation (A) needs NO new premise, and the composition
    above is a kernel fact rather than sizing input.

    The `SlStP` pair below still shows the gap is REAL at a NON-derived `R`; it does not
    show it survives at the derived `R` the consumers actually supply, and those remain
    different claims. -/
def TtuTargetsSatL (S : Schema) (Q : String → Prop) : Prop :=
  ∀ r ∈ schemaRewritesL S, ∀ tr ∈ ttuTargets r, Q tr

/-- …and it is decidable at a concrete schema and decidable `Q`, which is what lets the
    witnesses below be `decide` pins. (A plain `def` is not unfolded by instance synthesis,
    so the instance has to be stated — same reason as `NoLeafSubjects`' above.) -/
instance (S : Schema) (Q : String → Prop) [DecidablePred Q] :
    Decidable (TtuTargetsSatL S Q) :=
  inferInstanceAs (Decidable (∀ r ∈ schemaRewritesL S, ∀ tr ∈ ttuTargets r, Q tr))

/-- `NoLeafSubjects` IS `TtuTargetsSatL` at `NotLeafName` — definitionally, so the existing
    `NotLeafName` development above and this generic one are one chain, not two. -/
theorem noLeafSubjects_iff_ttuTargetsSatL {S : Schema} :
    NoLeafSubjects S ↔ TtuTargetsSatL S NotLeafName := Iff.rfl

/-- One L-rewrite step preserves any `Q` on the subject predicate that the FULL rule set's
    TTU targets satisfy. The generic parent of `rewriteStepL_subject_notLeafName`; the proof
    is that one with `NotLeafName` abstracted, since it never inspects the predicate. -/
theorem rewriteStepL_subject_pred_gen {S : Schema} {Q : String → Prop}
    (hnt : TtuTargetsSatL S Q) {t u : Tuple} (ht : Q t.subject.predicate)
    (h : u ∈ rewriteStepL S t) : Q u.subject.predicate := by
  unfold rewriteStepL at h
  obtain ⟨r, hr, hap⟩ := List.mem_filterMap.mp h
  rcases applyRRule_subject_pred hap with heq | hmem
  · rw [heq]; exact ht
  · exact hnt r hr _ hmem

/-- Subject-predicate `Q`-preservation across the L closure kernel, at every fuel and
    frontier. -/
theorem rewriteClosureAuxL_subject_pred_gen {S : Schema} {Q : String → Prop}
    (hnt : TtuTargetsSatL S Q) :
    ∀ (n : Nat) (cur : List Tuple), (∀ w ∈ cur, Q w.subject.predicate) →
      ∀ v ∈ rewriteClosureAuxL S n cur, Q v.subject.predicate := by
  intro n
  induction n with
  | zero => intro cur hcur v hv; exact hcur v hv
  | succ n ih =>
      intro cur hcur v hv
      simp only [rewriteClosureAuxL, List.mem_append] at hv
      rcases hv with hv | hv
      · exact hcur v hv
      · refine ih _ ?_ v hv
        intro w hw
        obtain ⟨u, hu, hwu⟩ := List.mem_flatMap.mp hw
        exact rewriteStepL_subject_pred_gen hnt (hcur u hu) hwu

/-- The `Q`-generic L closure corollary, over an arbitrary seed list. -/
theorem rewriteClosureL_subject_pred_gen {S : Schema} {Q : String → Prop}
    (hnt : TtuTargetsSatL S Q) {seeds : List Tuple}
    (hs : ∀ w ∈ seeds, Q w.subject.predicate) {u : Tuple}
    (hu : u ∈ rewriteClosureL S seeds) : Q u.subject.predicate := by
  rw [mem_rewriteClosureL_iff] at hu
  unfold rewriteClosureRawL at hu
  exact rewriteClosureAuxL_subject_pred_gen hnt _ seeds hs u hu

/-- **(A) No leaf-routed closure tuple of an `R`-avoiding raw write has subject predicate
    `R`.** The L twin of `ReconcileCorrect.lean::rewriteClosure_subject_pred_ne`, at the seed
    the re-pointed `writeLoggedRules` fold uses.

    The seed premise collapses to a fact about the raw write's OWN subject, exactly as in
    `rewriteClosureL_subject_not_leafNode`: `rawWriteTuples` re-addresses the relation only,
    so the fan-out cannot introduce a fresh subject predicate. -/
theorem rewriteClosureL_subject_pred_ne {S : Schema} {R : String}
    (hnt : TtuTargetsSatL S (· ≠ R)) {t : Tuple} (ht : t.subject.predicate ≠ R)
    {u : Tuple} (hu : u ∈ rewriteClosureL S (rawWriteTuples S t)) :
    u.subject.predicate ≠ R := by
  refine rewriteClosureL_subject_pred_gen hnt ?_ hu
  intro w hw
  unfold rawWriteTuples at hw
  obtain ⟨r, _, rfl⟩ := List.mem_map.mp hw
  exact ht

/-! ## Obligation (F) — the L twin of `RulesChain.lean::rewriteClosure_rel_ne_bare`

★ **Dot-freeness is the right instrument on ONE arm and useless on the other**, and that
asymmetry is the whole content of (F). `isLeafPred_bare` (`Leaf.lean:210`) proves
`isLeafPred BARE = true` — the bare-subject sentinel `"..."` is itself dot-carrying. So:

* on the **untainted** arm the existing `not_isLeafPred_outRel_of_mem_schemaRewrites`
  (`:141`) closes the goal precisely BECAUSE a declared name is dot-FREE and `BARE` is not;
* on the **leaf** arm it separates nothing: a minted `leafPred R i` is dot-carrying exactly
  like `BARE`, so `isLeafPred_outRel_of_mem_leafRewrites` (`:129`) is satisfied by both. The
  leaf arm needs the SHAPE of the minted name — `leafPred_ne_bare` below.

## ★ CONTROLLED — three sabotages, run 2026-09-05 (`docs/sabotage-procedure.md`)

(F) is **INERT**: the write-path re-point that consumes it has not landed, so a green build
vets nothing about it and these runs — plus the `decide` attack pins in
`LeafRuleWitness` — are the only evidence there is. Each weakening below is the NARROWEST
plausible one (a premise, or a quantifier's range), never an obvious catastrophe; each was
restored from a byte-exact `cp` backup, never `git checkout --`.

**(S15) `leafPred_ne_bare` is given a non-emptiness premise** — `(_hR : R ≠ "")`, the
plausible reading that only the empty relation name could collide with `"..."`. It is not:
`R` is unbounded at BOTH consumers. `lake build` rc=**1**, two errors, and they are the two
arms firing at once — a single-arm red would have meant the other arm was dead code:

```text
error: ZanzibarProofs/GraphIndex/LeafRules.lean:1117:4: Type mismatch
  leafPred_ne_bare R i
has type
  R ≠ "" → leafPred R i ≠ BARE
but is expected to have type
  leafPred R i ≠ BARE
error: ZanzibarProofs/GraphIndex/LeafRules.lean:1130:4: Type mismatch
  leafPred_ne_bare ?m.75 ?m.76
has type
  ?m.75 ≠ "" → leafPred ?m.75 ?m.76 ≠ BARE
but is expected to have type
  leafPred t.relation i ≠ BARE
```

(`:1117` is `outRel_ne_bare_of_mem_schemaRewritesL`'s leaf arm, `:1130` is
`rawWriteTuples_rel_ne_bare`'s DERIVED-seed branch. This weakening changes no line COUNT, so
both numbers read the same in the restored file — checked, not assumed.)

**(S16) The leaf half is dropped from the rule quantifier** — `outRel_ne_bare_of_mem_`
`schemaRewritesL` restated over `schemaRewrites S`, i.e. exactly `(S12)`'s shape one section
later. The untainted proof still goes through unchanged, so nothing local complains; the red
lands at the closure theorem, the only place that knows the produced rule is in the FULL set:

```text
error: ZanzibarProofs/GraphIndex/LeafRules.lean:1145:52: Application type mismatch: The argument
  hr
has type
  r ∈ schemaRewritesL S
but is expected to have type
  r ∈ schemaRewrites S
in the application
  outRel_ne_bare_of_mem_schemaRewritesL hWF hr
```

(This weakening deletes five lines, so `:1145` in the sabotaged file is
`rewriteClosureL_rel_ne_bare_of_rel`'s rule case at `:1150` in the restored one.)

**(S17) The WRONG INSTRUMENT — run because the paragraph above makes a claim.** The leaf arm
is closed from `isLeafPred_outRel_of_mem_leafRewrites` (dot-carrying) instead of
`outRel_leafPred_of_mem_leafRewrites` (minted shape). The residual hypothesis states the
defect exactly: under `r.outRel = BARE` the dot-carrying fact simplifies to **`True`** — it
carries no information whatever, and `False` stays unreachable.

```text
error: ZanzibarProofs/GraphIndex/LeafRules.lean:1115:2: unsolved goals
case inr
S : Schema
hWF : WF S
r : RRule
hl : r ∈ leafRewrites S
hb : r.outRel = BARE
hlp : True
⊢ False
```

(`:1115` is the leaf arm's `·` bullet, the same line in the sabotaged and restored files.)

All three restored by `cp` from the pre-sabotage copy: rc=0, `Build completed successfully
(1089 jobs)`, zero `declaration uses `sorry``.

⚠ **The sorry-grep instrument was itself controlled** (trap (u)), same session and before any
zero above was believed: a throwaway
`theorem zzz_sorry_instrument_control : (1:Nat) = 1 := by sorry` appended to this file made
`grep -c 'declaration uses .sorry.'` report **1** while the straight-quote spelling reported
**0**, on the literal warning
`ZanzibarProofs/GraphIndex/LeafRules.lean:1652:8: declaration uses `sorry``. That `:1652` was
the end of the file in THAT run — the throwaway was `cp`-restored away and this record was
inserted afterwards, so nothing at `:1652` today relates to it. The zeroes above are measured
zeroes, not an unfired grep.
-/

/-- **A minted leaf name is never the `BARE` sentinel** — for EVERY relation `R` (including
    dot-carrying and empty ones) and every index `i`.

    Not a `decide`: `R` ranges over all strings. The argument is structural, and rests on two
    core facts about `Nat.toDigits` — it is never `[]` (`Nat.toDigits_ne_nil`) and every
    character in it is a digit (`Nat.isDigit_of_mem_toDigits`). `leafPred R i` ends in
    `toString i`, so its character list CONTAINS a digit; every character of `BARE = "..."`
    is `'.'`, which is not one.

    ⚠ The tempting shortcut — "`R` is declared, hence dot-free, so `leafPred R i` carries one
    dot and `BARE` carries three" — does not serve the `leafRewrites` arm: nothing there
    bounds `R`'s dots except `WF`, and the arm is reached only after a `List.mem_flatMap`
    extraction that hands back `R := d.1.2`. The unconditional form keeps the leaf arm
    `WF`-FREE, which is why (F) needs `WF` for the untainted arm alone. -/
theorem leafPred_ne_bare (R : String) (i : Nat) : leafPred R i ≠ BARE := by
  intro heq
  have hdata : (leafPred R i).toList = R.toList ++ '.' :: (toString i).toList := by
    simp [leafPred, String.toList_append]
  rw [heq] at hdata
  have hbare : (BARE : String).toList = ['.', '.', '.'] := by decide
  rw [hbare] at hdata
  obtain ⟨c, hc⟩ : ∃ c, c ∈ Nat.toDigits 10 i :=
    List.exists_mem_of_ne_nil _ Nat.toDigits_ne_nil
  have hcs : c ∈ (toString i).toList := by simpa using hc
  have hdig : c.isDigit = true := Nat.isDigit_of_mem_toDigits (by decide) (by decide) hc
  have hmem : c ∈ ['.', '.', '.'] := by
    rw [hdata]; exact List.mem_append_right _ (List.mem_cons_of_mem _ hcs)
  have hdot : c = '.' := by simpa using hmem
  rw [hdot] at hdig
  exact absurd hdig (by decide)

/-- **Every leaf rule targets a MINTED leaf name**, with its public relation and index
    recoverable. The shape-carrying strengthening of `isLeafPred_outRel_of_mem_leafRewrites`
    (`:129`), whose `isLeafPred` conclusion cannot tell a leaf target from `BARE`. -/
theorem outRel_leafPred_of_mem_leafRewrites {S : Schema} {r : RRule}
    (h : r ∈ leafRewrites S) : ∃ R i, r.outRel = leafPred R i := by
  unfold leafRewrites at h
  obtain ⟨d, _, hd⟩ := List.mem_flatMap.mp h
  unfold keyLeafRewrites at hd
  obtain ⟨pi, _, hpi⟩ := List.mem_flatMap.mp hd
  split at hpi
  · exact ⟨d.1.2, pi.2, outRel_mem_of_mem_exprArms hpi⟩
  · simp at hpi

/-- **No rule of the FULL leaf-routed rule set targets `BARE`** — the two arms for two
    different reasons, which is exactly what the twin's single `relNameOK` argument cannot
    cover once `leafRewrites` is in range. -/
theorem outRel_ne_bare_of_mem_schemaRewritesL {S : Schema} (hWF : WF S) {r : RRule}
    (h : r ∈ schemaRewritesL S) : r.outRel ≠ BARE := by
  rw [schemaRewritesL, List.mem_append] at h
  rcases h with hu | hl
  · intro hb
    have hnl := not_isLeafPred_outRel_of_mem_schemaRewrites hWF hu
    rw [hb, isLeafPred_bare] at hnl
    exact Bool.noConfusion hnl
  · obtain ⟨R, i, hr⟩ := outRel_leafPred_of_mem_leafRewrites hl
    rw [hr]
    exact leafPred_ne_bare R i

/-- **The seed fan-out never mints `BARE` either.** Either the key is untainted and the
    single seed keeps `t.relation`, or it is derived and every seed carries a minted leaf
    name (`Leaf.lean::mem_rawWriteRels_derived`). Note the premise is about the RAW write,
    not about the seeds: the fan-out is what this lemma has to see through. -/
theorem rawWriteTuples_rel_ne_bare {S : Schema} {t : Tuple} (ht : t.relation ≠ BARE)
    {u : Tuple} (hu : u ∈ rawWriteTuples S t) : u.relation ≠ BARE := by
  unfold rawWriteTuples at hu
  obtain ⟨r, hr, rfl⟩ := List.mem_map.mp hu
  show r ≠ BARE
  by_cases hd : isDerived S (t.object.type, t.relation) = true
  · obtain ⟨i, rfl⟩ := mem_rawWriteRels_derived hd hr
    exact leafPred_ne_bare _ _
  · rw [rawWriteRels_untainted (by simpa using hd)] at hr
    rw [List.mem_singleton.mp hr]
    exact ht

/-- **(F), general form.** No tuple of the leaf-routed closure of a raw write carries the
    bare-subject sentinel as its RELATION.

    ★ **Strictly weaker premises than the twin, and the report says so.**
    `RulesChain.lean::rewriteClosure_rel_ne_bare` carries `StoreValidRules S T` and `t ∈ T`
    only to extract `t.relation ≠ BARE` through `lookup_rel_ne_bare`; nothing else in either
    argument inspects the store. This form takes that consequence directly and needs **no
    store at all**. The drop-in twin-shaped version is the two-line corollary below, so the
    consumer site is unaffected by the weakening. -/
theorem rewriteClosureL_rel_ne_bare_of_rel {S : Schema} (hWF : WF S) {t : Tuple}
    (ht : t.relation ≠ BARE) {u : Tuple}
    (hu : u ∈ rewriteClosureL S (rawWriteTuples S t)) : u.relation ≠ BARE := by
  rcases rewriteClosureL_produced hu with hseed | ⟨r, hr, -, hrout⟩
  · exact rawWriteTuples_rel_ne_bare ht hseed
  · rw [← hrout]
    exact outRel_ne_bare_of_mem_schemaRewritesL hWF hr

/-- **(F), drop-in form.** EXACTLY `RulesChain.lean::rewriteClosure_rel_ne_bare`'s premise
    list and conclusion, at the leaf-routed seed. Post-flip, `CascadeSettle.lean:112`'s
    `exact rewriteClosure_rel_ne_bare hWF hSV List.mem_cons_self hu` becomes
    `exact rewriteClosureL_rel_ne_bare hWF hSV List.mem_cons_self hu` — one identifier, no
    other movement. Pinned as such by `rewriteClosureL_rel_ne_bare_dropin_nonvacuous`, which
    applies it at that literal argument shape. -/
theorem rewriteClosureL_rel_ne_bare {S : Schema} {T : Store} (hWF : WF S)
    (hSV : StoreValidRules S T) {t : Tuple} (ht : t ∈ T) {u : Tuple}
    (hu : u ∈ rewriteClosureL S (rawWriteTuples S t)) : u.relation ≠ BARE :=
  rewriteClosureL_rel_ne_bare_of_rel hWF
    (by obtain ⟨e, _, hlk, _, _⟩ := hSV t ht; exact lookup_rel_ne_bare hWF hlk) hu

/-! ## The non-vacuity witnesses

Everything above is additive, so a green build vets nothing: `leafRewrites` returning
`[]` on every schema, or minting the right rules at the wrong index, would compile and
audit exactly as cleanly. Each witness below pins ONE measured Python fact; the
provenance is its docstring, and the literal Python output is in the module header of
`Leaf.lean` and in `formal/history/PROOF_STATUS.md` 2026-08-16.

## ★ CONTROLLED — three sabotages, run 2026-08-16 (`docs/sabotage-procedure.md`)

**(S9) The leaf index is dropped** — `keyLeafRewrites` targets the PUBLIC relation `R`
instead of `leafPred R pi.2`. This is the "4c is a caller re-point" misreading in its
purest form, and it is what the whole of §11.6 exists to refute. SIX errors: the four
rule pins `lrV_rules` / `lrSw_rules` / `lrStP_rules` / `lrA_rules`, the payoff pin
`lrV_closure_reaches_leaf`, and — the structural half — a `Type mismatch` inside
`isLeafPred_outRel_of_mem_leafRewrites`, because the disjointness theorem is no longer
TRUE. Literal head:
```text
leafRewrites SlV =
  [{ objectType := "doc", matchRel := "editor", outRel := leafPred "viewer" 0, kind := RuleKind.computed },
    { objectType := "doc", matchRel := "banned", outRel := leafPred "viewer" 1, kind := RuleKind.computed }]
is false
```
Controls GREEN: `slV_derived`, `lrV_untainted_layer_silent`, `lrUnt_no_leaf_rules`,
`lrUnt_subsumed`, `lrV_closure_today_misses_leaf`.

**(S10) The taint filter is inverted** — `leafRewrites` filters `!isDerived` instead of
`isDerived`, i.e. it mints leaf rules for UNTAINTED keys. EIGHT errors: all four rule
pins, both `lrUnt_*` subsumption controls (`lrUnt_no_leaf_rules`, `lrUnt_subsumed`),
both closure pins — **and** `leafRewrites_eq_nil`'s proof breaks. The `lrUnt_*` reds are
the point: the subsumption claim ("the untainted fragment is untouched") is exactly what
those controls guard, and an inverted filter is the one defect that voids it.

**(S11) The merged closure leaf is only half-walked** — `keyLeafRewrites` takes
`exprArms` of only the FIRST member of a merged subtree (`.take 1`). `lrA_rules` ALONE
reddens (plus a proof artifact in the disjointness extraction):
```text
leafRewrites SlA =
  [{ objectType := "doc", matchRel := "a", outRel := leafPred "r" 0, kind := RuleKind.computed },
    { objectType := "doc", matchRel := "b", outRel := leafPred "r" 0, kind := RuleKind.computed },
    { objectType := "doc", matchRel := "banned", outRel := leafPred "r" 1, kind := RuleKind.computed }]
is false
```
`lrV_rules` / `lrSw_rules` / `lrStP_rules` stay GREEN, because none of them has a merged
closure leaf. That asymmetry is exactly why `SlA` is in this witness set — it is the
only shape that distinguishes the merge at the RULE layer, just as `SmA` is the only one
that distinguishes it at the ALLOCATION layer (`Leaf.lean` sabotage S6).
-/

/-! ## Obligation (A)'s PREMISE — DISCHARGED, not assumed

★ The `TtuTargetsSatL` note above (`:891`) ends by flagging its own composition as
**"NOT PROVED HERE — this is a source reading, not a kernel check"**, and names the missing
step: *"every `.closure` leaf of `persistedLeaves` is `isPure`"*. This section proves that
lemma and closes the gap, so obligation (A) needs **no new premise**: `TtuTargetsSatL S (· ≠ R)`
follows from the pair the consumers already carry — `ReconcileCorrect.lean::NoTtuTarget S R`
together with `isDerived S (dt, R) = true`, which is exactly what `FullScope.lean:238
W4Fragment.term` supplies and what all fifteen `Equiv.lean` consumers (`:281`…`:660`) hold.

⚠ **`NoTtuTarget` is spelled out UNFOLDED below rather than named**, for the same reason
`stP_untainted_layer_no_ttu_target_viewer` spells it out: it lives in `ReconcileCorrect.lean`,
which this file does not import. The two are definitionally equal, so a consumer holding a
`NoTtuTarget S R` passes it straight in — checked out-of-tree 2026-09-05 with
`lake env lean` on a scratch file importing BOTH modules, where
`rewriteClosureL_subject_pred_ne_of_noTtuTarget (hnt : NoTtuTarget S R) …` elaborates with no
coercion. **The import would in fact be legal** (cycle check by transitive closure, not by
eye: `ReconcileCorrect`'s import cone is 35 modules and contains neither `GraphIndex.Leaf` nor
`GraphIndex.LeafRules` nor any `Cascade*`, while `LeafRules` is imported only by `Audit`,
`CascadeStable` and `Scratch4cii`, none of which is in that cone); it is simply not needed,
and the unfolded form keeps this change import-free.

## ★ STEP 1 WAS THE ATTACK, NOT THE PROOF (house rule 2)

The claim under attack: **a `.closure` leaf can never carry a TTU node whose target is
derived anywhere**, so no leaf rule can mint that target as a subject predicate. It was
attacked by enumerating every site that can emit a `PLeaf.closure` at all — there are exactly
four, and `pureLeaves` has exactly two call sites, both `isPure`-guarded:

* `atomLeaves`'s `.ttu` arm (`Leaf.lean:402`) — emits `.closure (.ttu tgt ts)` **only** under
  `isPure`, whose TTU conjunct is `!derivedAnywhere S tgt`. No bypass.
* `atomLeaves`'s `.computed` arm — emits `.closure (.computed R)`, which `exprArms` turns into
  a `.computed` rule; `ttuTargets` of that is `[]`. Nothing to target.
* `atomLeaves`'s `.direct` arm — the impure branch emits `.storage`/`.userset` only, and the
  pure branch goes through `pureLeaves (.direct rs)` where `splitPure` returns `(rs, [])`, so
  `unionAll [] = none` and no closure leaf is emitted at all.
* `persistedLeaves`'s `.union` arm — `pureLeaves (.union a b)` under `isPure`, and `isPure` on
  a union is the CONJUNCTION of its arms, so every member of the merged leaf is pure.

The `.inter`/`.excl` arms of both `persistedLeaves` and `unionSpineLeaves`, and the whole
`unionSpineLeaves` spine, only recurse — they emit nothing themselves. **No arm bypasses
`isPure`, so the attack fails and the lemma is true as stated.**

Four adversarial schemas were then run through `leafRewrites` as a control on that reading
(`lake env lean`, 2026-09-05): a derived TTU target under a plain `excl` (`LeafWitness.StD`);
the same target buried in an IMPURE union next to a clean one, so the spine-flattening arm
runs; a `.direct ∪ .ttu` union whose derived target makes the whole union impure; and the
same target under nested `inter`/`excl`. In every one the derived-target arm minted **no
rule at all** and the clean arms minted theirs at the shifted indices. The first and the
cross-type case are kept below as permanent `decide` pins (`lrStD_no_ttu_rule`,
`lrXt_cross_type_drop`) rather than described, because a described run is a lost run.

## What is proved, in dependency order

1. `mem_keys_of_mem_taintedKeys` / `mem_keys_of_isDerived` — taint never leaves `S.keys`
   (`taintStep` is a `filter` of `S.keys`, and the fixpoint's outermost application is one).
   **No `WF` and no `NodupKeys` needed**: this is the weakest premise there is, none.
2. `derivedAnywhere_of_isDerived` — one derived key witnesses the type-agnostic test.
3. `isPure_of_closure_mem_persistedLeaves` — **the missing purity lemma**, by one induction
   over `Expr` proving the `persistedLeaves`/`unionSpineLeaves` pair simultaneously (the two
   are mutually defined but every recursive call is on an immediate subterm, so plain
   structural induction on the shared argument suffices — no mutual-induction principle).
4. `derivedAnywhere_eq_false_of_mem_leafRewrites` — every leaf rule's TTU target is derived
   NOWHERE, by (3) plus a walk of `exprArms` over a pure subtree.
5. `ttuTargetsSatL_ne_of_noTtuTarget` and its closure corollary — the two arms of
   `schemaRewritesL` closed by `NoTtuTarget` (untainted) and by (4) + (2) (leaf).

## ★ CONTROLLED — three sabotages, run 2026-09-05 (`docs/sabotage-procedure.md`)

Each is the NARROWEST plausible weakening of the thing it guards, not an obvious catastrophe;
each was applied to the green file, built with `lake build ZanzibarProofs.GraphIndex.LeafRules`,
and restored from a byte-exact `cp` backup (md5-verified identical after each restore), never
by `git checkout`. Every line number quoted below was RE-MEASURED against this final file,
after this record was inserted, by re-running all three sabotages; the outputs are literal.

**The instrument was controlled first.** Lean prints *declaration uses* with the word `sorry`
in BACKTICKS, so a straight-quote grep for it matches nothing and a zero from that grep is
meaningless. Appending `theorem zzz_sorry_instrument_control_A : (1:Nat) = 1 := by sorry` and
rebuilding this module gave `rc=0`, dot-wildcard grep **1**, straight-quote grep **0**, at
`LeafRules.lean:2309:8`. Removed; the zero in the final build is a measurement, not a hope.

**(S14) The TTU purity is read off the TUPLESET conjunct instead of the TARGET conjunct.**
`isPure`'s TTU arm is a two-conjunct `&&` and the two are adjacent:
`!isDerived S (ty, ts)` is about the tupleset relation — which becomes the rule's `matchRel` —
and `!derivedAnywhere S tgt` is about the target, which becomes `ttuTargets`. Reading the
first is the single most plausible transcription slip in this development, and it is exactly
the confusion that would make the leaf-layer fact false. `hp.2` → `hp.1`;
`lake build` rc=**1**:

```text
error: ZanzibarProofs/GraphIndex/LeafRules.lean:1571:6: Type mismatch: After simplification, term
  hp.left
 has type
  isDerived S (ty, ts) = false
but is expected to have type
  derivedAnywhere S tr = false
```

**(S15) The purity lemma is narrowed to the SPINE half.** `persistedLeaves` and
`unionSpineLeaves` differ on exactly one arm — the pure union, which the first MERGES through
`pureLeaves` and the second never does. That distinction was measured WRONG once already in
this file's history (the 2026-08-16b `unionSpineLeaves` correction), so projecting the wrong
component is a live failure mode and not a hypothetical. `.1` → `.2` in
`isPure_of_closure_mem_persistedLeaves`; `lake build` rc=**1**:

```text
error: ZanzibarProofs/GraphIndex/LeafRules.lean:1536:53: Application type mismatch: The argument
  h
has type
  PLeaf.closure sub ∈ persistedLeaves S ty e
but is expected to have type
  PLeaf.closure sub ∈ unionSpineLeaves S ty e
in the application
  (isPure_closure_persistedLeaves_and_spine e).right sub h
```

**(S16) `hder` is dropped from the leaf arm** — the weakening the record's own framing invites
("reuse `NoTtuTarget`"), and the one `hder_load_bearing` refutes semantically. Removing the
`derivedAnywhere_of_isDerived hder` rewrite leaves the `Bool` collision unclosed;
`lake build` rc=**1**:

```text
error: ZanzibarProofs/GraphIndex/LeafRules.lean:1624:4: Type mismatch
  Bool.noConfusion h1
has type
  Bool.noConfusionType ?m.66 (derivedAnywhere S R) false
but is expected to have type
  False
```

⚠ S16 is the weakest of the three as evidence, because it reddens by failing to COMPILE. The
durable form of that control is `hder_load_bearing` below, which is a permanent `decide`
refutation of the `hder`-free STATEMENT at `SlStP` — a lemma that no longer needs the premise
would still be false there, and no proof-shape change can hide it. -/

section ObligationAPremise

variable {S : Schema}

/-- **Taint never leaves the declared keys.** `taintStep` is a `filter` of `S.keys`, so at
    any nonzero fuel the OUTERMOST application of the fixpoint iteration is one; at fuel zero
    the result is the empty seed. Hence `taintedKeys S ⊆ S.keys` with no side conditions —
    in particular no `WF` and no `NodupKeys`, which is the weakest premise available. -/
theorem mem_keys_of_mem_taintedKeys {k : Key} (h : k ∈ taintedKeys S) : k ∈ S.keys := by
  have gen : ∀ (n : Nat) (cur : List Key),
      k ∈ iterate (taintStep S) n cur → k ∈ cur ∨ k ∈ S.keys := by
    intro n
    induction n with
    | zero => intro cur hc; exact Or.inl hc
    | succ m ih =>
        intro cur hc
        rw [iterate] at hc
        rcases ih _ hc with h1 | h2
        · rw [taintStep] at h1
          exact Or.inr (List.mem_of_mem_filter h1)
        · exact Or.inr h2
  rcases gen _ _ h with h1 | h2
  · simp at h1
  · exact h2

/-- A derived key is a DECLARED key. -/
theorem mem_keys_of_isDerived {k : Key} (h : isDerived S k = true) : k ∈ S.keys := by
  refine mem_keys_of_mem_taintedKeys ?_
  unfold isDerived at h
  simpa [List.contains_eq_mem] using h

/-- **The type-agnostic taint test, from one witness type.** `derivedAnywhere S R` is
    `S.keys.any (k.2 == R && isDerived S k)`, so a single derived `(dt, R)` decides it —
    the key is in `S.keys` by `mem_keys_of_isDerived`, which is the only non-obvious step. -/
theorem derivedAnywhere_of_isDerived {R dt : String} (h : isDerived S (dt, R) = true) :
    derivedAnywhere S R = true := by
  unfold derivedAnywhere
  refine List.any_eq_true.mpr ⟨(dt, R), mem_keys_of_isDerived h, ?_⟩
  simp [h]

/-- Splitting a PURE subtree (`Leaf.lean::splitPure`) leaves every non-`Direct` member pure:
    the only interesting arm is `union`, where `isPure` is the conjunction of the arms. -/
theorem isPure_of_mem_splitPure_snd {ty : String} :
    ∀ {e : Expr}, isPure S ty e = true → ∀ x ∈ (splitPure e).2, isPure S ty x = true := by
  intro e
  induction e with
  | direct rs => intro _ x hx; simp [splitPure] at hx
  | computed R => intro h x hx; simp [splitPure] at hx; subst hx; exact h
  | ttu tgt ts => intro h x hx; simp [splitPure] at hx; subst hx; exact h
  | union a b iha ihb =>
      intro h x hx
      rw [isPure, Bool.and_eq_true] at h
      rw [splitPure] at hx
      simp only [List.mem_append] at hx
      rcases hx with hx | hx
      · exact iha h.1 x hx
      · exact ihb h.2 x hx
  | inter a b _ _ => intro h; simp [isPure] at h
  | excl a b _ _ => intro h; simp [isPure] at h

/-- Re-folding pure members into `unionAll`'s LEFT-nested union keeps them pure. -/
theorem isPure_foldl_union {ty : String} :
    ∀ (es : List Expr) (e : Expr), isPure S ty e = true →
      (∀ x ∈ es, isPure S ty x = true) → isPure S ty (es.foldl Expr.union e) = true := by
  intro es
  induction es with
  | nil => intro e he _; simpa using he
  | cons a es ih =>
      intro e he hall
      simp only [List.foldl_cons]
      refine ih _ ?_ (fun x hx => hall x (List.mem_cons_of_mem _ hx))
      rw [isPure, Bool.and_eq_true]
      exact ⟨he, hall a (List.mem_cons_self ..)⟩

/-- `unionAll` of pure members is pure. -/
theorem isPure_of_unionAll {ty : String} {es : List Expr} {sub : Expr}
    (hall : ∀ x ∈ es, isPure S ty x = true) (h : unionAll es = some sub) :
    isPure S ty sub = true := by
  cases es with
  | nil => simp [unionAll] at h
  | cons e es =>
      rw [unionAll] at h
      simp only [Option.some.injEq] at h
      subst h
      exact isPure_foldl_union es e (hall e (List.mem_cons_self ..))
        (fun x hx => hall x (List.mem_cons_of_mem _ hx))

/-- **The MERGED closure leaf is pure.** `pureLeaves`' storage half carries no `.closure` at
    all; its closure half is `unionAll (splitPure e).2`, pure by the two lemmas above. This is
    the arm that covers `persistedLeaves`' pure-union merge — the shape `SlA`/`SmA` exist to
    distinguish, and the one a purity lemma written only for atoms would miss. -/
theorem isPure_of_closure_mem_pureLeaves {ty : String} {e sub : Expr}
    (hp : isPure S ty e = true) (h : PLeaf.closure sub ∈ pureLeaves e) :
    isPure S ty sub = true := by
  simp only [pureLeaves, List.mem_append] at h
  rcases h with h | h
  · split at h <;> simp at h
  · split at h
    · simp at h
    · rename_i sub' heq
      simp only [List.mem_singleton, PLeaf.closure.injEq] at h
      subst h
      exact isPure_of_unionAll (isPure_of_mem_splitPure_snd hp) heq

/-- **Every `.closure` leaf `atomLeaves` emits is pure** — the three non-recursive emission
    sites, checked one at a time. The `.direct` impure branch emits `.storage`/`.userset`
    only; the `.computed` else-branch is pure exactly because it is the else-branch; the
    `.ttu` arm is `isPure`-guarded outright. -/
theorem isPure_of_closure_mem_atomLeaves {ty : String} {e sub : Expr}
    (h : PLeaf.closure sub ∈ atomLeaves S ty e) : isPure S ty sub = true := by
  cases e with
  | direct rs =>
      rw [atomLeaves] at h
      split at h
      · rename_i hp; exact isPure_of_closure_mem_pureLeaves hp h
      · simp only [List.mem_append] at h
        rcases h with h | h
        · split at h <;> simp at h
        · obtain ⟨r, _, hr⟩ := List.mem_map.mp h; simp at hr
  | computed R =>
      rw [atomLeaves] at h
      split at h
      · simp at h
      · rename_i hnd
        simp only [List.mem_singleton, PLeaf.closure.injEq] at h
        subst h
        simp [isPure, hnd]
  | ttu tgt ts =>
      rw [atomLeaves] at h
      split at h
      · rename_i hp
        simp only [List.mem_singleton, PLeaf.closure.injEq] at h
        subst h; exact hp
      · simp at h
  | union a b => simp [atomLeaves] at h
  | inter a b => simp [atomLeaves] at h
  | excl a b => simp [atomLeaves] at h

/-- **THE MISSING PURITY LEMMA, both halves at once.** `persistedLeaves` and
    `unionSpineLeaves` are mutually defined, but every recursive call in the block is on an
    IMMEDIATE SUBTERM of the shared `Expr` argument, so one plain structural induction proving
    the conjunction discharges both — no mutual-induction principle is needed. The `.union`
    case is where the two differ and where the whole content sits: `persistedLeaves` may MERGE
    (via `pureLeaves`, purity carried by `isPure_of_closure_mem_pureLeaves`), while
    `unionSpineLeaves` never merges and only flattens. -/
theorem isPure_closure_persistedLeaves_and_spine {ty : String} : ∀ (e : Expr),
    (∀ sub, PLeaf.closure sub ∈ persistedLeaves S ty e → isPure S ty sub = true) ∧
    (∀ sub, PLeaf.closure sub ∈ unionSpineLeaves S ty e → isPure S ty sub = true) := by
  intro e
  induction e with
  | direct rs =>
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves] at h; exact isPure_of_closure_mem_atomLeaves h
      · simp only [unionSpineLeaves] at h; exact isPure_of_closure_mem_atomLeaves h
  | computed R =>
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves] at h; exact isPure_of_closure_mem_atomLeaves h
      · simp only [unionSpineLeaves] at h; exact isPure_of_closure_mem_atomLeaves h
  | ttu tgt ts =>
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves] at h; exact isPure_of_closure_mem_atomLeaves h
      · simp only [unionSpineLeaves] at h; exact isPure_of_closure_mem_atomLeaves h
  | union a b iha ihb =>
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves] at h
        split at h
        · rename_i hp; exact isPure_of_closure_mem_pureLeaves hp h
        · simp only [List.mem_append] at h
          exact h.elim (iha.2 sub) (ihb.2 sub)
      · simp only [unionSpineLeaves, List.mem_append] at h
        exact h.elim (iha.2 sub) (ihb.2 sub)
  | inter a b iha ihb =>
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves, List.mem_append] at h
        exact h.elim (iha.1 sub) (ihb.1 sub)
      · simp only [unionSpineLeaves, List.mem_append] at h
        exact h.elim (iha.1 sub) (ihb.1 sub)
  | excl a b iha ihb =>
      refine ⟨fun sub h => ?_, fun sub h => ?_⟩
      · simp only [persistedLeaves, List.mem_append] at h
        exact h.elim (iha.1 sub) (ihb.1 sub)
      · simp only [unionSpineLeaves, List.mem_append] at h
        exact h.elim (iha.1 sub) (ihb.1 sub)

/-- **Every `.closure` leaf of the allocation is pure.** The `persistedLeaves` projection of
    the pair — the statement `:885` says no lemma in the tree has. -/
theorem isPure_of_closure_mem_persistedLeaves {ty : String} {e sub : Expr}
    (h : PLeaf.closure sub ∈ persistedLeaves S ty e) : isPure S ty sub = true :=
  (isPure_closure_persistedLeaves_and_spine e).1 sub h

/-- The converse of `ttuTargets_of_kind` (`:595`): the LIST form determines the kind. -/
theorem kind_of_mem_ttuTargets {r : RRule} {tr : String} (h : tr ∈ ttuTargets r) :
    r.kind = RuleKind.ttu tr := by
  unfold ttuTargets at h
  split at h
  · simp at h
  · rename_i t hk
    simp only [List.mem_singleton] at h
    subst h; exact hk

/-- **The TTU targets of a PURE subtree are derived nowhere.** `exprArms` mints a `.ttu tgt`
    rule exactly at a `.ttu tgt ts` node, and `isPure`'s TTU arm is
    `!isDerived S (ty, ts) && !derivedAnywhere S tgt` — the SECOND conjunct, about the TARGET,
    is the one this consumes. (The first is about the TUPLESET relation `ts`, which becomes
    the rule's `matchRel`, not its target; see sabotage (S14).) -/
theorem derivedAnywhere_eq_false_of_mem_exprArms_of_isPure {ty : String} :
    ∀ {e : Expr}, isPure S ty e = true → ∀ {ot outRel : String} {r : RRule},
      r ∈ exprArms ot outRel e → ∀ tr ∈ ttuTargets r, derivedAnywhere S tr = false := by
  intro e
  induction e with
  | direct rs => intro _ _ _ _ hr; simp [exprArms] at hr
  | computed R =>
      intro _ _ _ _ hr tr htr
      simp only [exprArms, List.mem_singleton] at hr
      subst hr
      simp [ttuTargets] at htr
  | ttu tgt ts =>
      intro hp _ _ _ hr tr htr
      simp only [exprArms, List.mem_singleton] at hr
      subst hr
      simp only [ttuTargets, List.mem_singleton] at htr
      subst htr
      rw [isPure, Bool.and_eq_true] at hp
      simpa using hp.2
  | union a b iha ihb =>
      intro hp _ _ _ hr
      rw [isPure, Bool.and_eq_true] at hp
      rw [exprArms, List.mem_append] at hr
      exact hr.elim (iha hp.1) (ihb hp.2)
  | inter a b _ _ => intro hp; simp [isPure] at hp
  | excl a b _ _ => intro hp; simp [isPure] at hp

/-- **★ THE LEAF-LAYER FACT.** Every rule in `leafRewrites S` that has a TTU target has one
    that is derived NOWHERE. `keyLeafRewrites` mints rules only off `.closure` leaves (its
    `_ => []` arm), those leaves are pure, and a pure subtree's TTU targets are
    `derivedAnywhere`-false. The `zipIdx` index is irrelevant to the target, so it is
    projected away with `List.zipIdx_map_fst`. -/
theorem derivedAnywhere_eq_false_of_mem_leafRewrites {r : RRule} (h : r ∈ leafRewrites S) :
    ∀ tr ∈ ttuTargets r, derivedAnywhere S tr = false := by
  unfold leafRewrites at h
  obtain ⟨d, _, hd⟩ := List.mem_flatMap.mp h
  unfold keyLeafRewrites at hd
  obtain ⟨pi, hpi, hr⟩ := List.mem_flatMap.mp hd
  split at hr
  · rename_i sub heq
    have hmem : PLeaf.closure sub ∈ persistedLeaves S d.1.1 d.2 := by
      rw [← heq]
      have := List.mem_map_of_mem (f := Prod.fst) hpi
      rwa [List.zipIdx_map_fst] at this
    exact derivedAnywhere_eq_false_of_mem_exprArms_of_isPure
      (isPure_of_closure_mem_persistedLeaves hmem) hr
  · simp at hr

/-- **★★ OBLIGATION (A)'s PREMISE, DISCHARGED.** `TtuTargetsSatL S (· ≠ R)` from the pair the
    consumers already carry. The two arms of `schemaRewritesL` are closed differently and
    that asymmetry is the whole proof:

    * **untainted arm** — `NoTtuTarget S R` verbatim (spelled out; see the section header on
      why it is not named), via `kind_of_mem_ttuTargets` to get from the list form to the
      binder form;
    * **leaf arm** — a leaf rule's TTU target is `derivedAnywhere`-FALSE
      (`derivedAnywhere_eq_false_of_mem_leafRewrites`) while `R` is `derivedAnywhere`-TRUE
      (`derivedAnywhere_of_isDerived hder`), and a `Bool` is not both.

    ⚠ `hder` is LOAD-BEARING, not decoration: `hder_load_bearing` below is the machine-checked
    refutation of the `hder`-free statement, at `SlStP`. -/
theorem ttuTargetsSatL_ne_of_noTtuTarget {R dt : String}
    (hnt : ∀ r ∈ schemaRewrites S, ∀ tr, r.kind = RuleKind.ttu tr → tr ≠ R)
    (hder : isDerived S (dt, R) = true) : TtuTargetsSatL S (· ≠ R) := by
  intro r hr tr htr
  rw [schemaRewritesL, List.mem_append] at hr
  rcases hr with hr | hr
  · exact hnt r hr tr (kind_of_mem_ttuTargets htr)
  · intro heq
    have h1 := derivedAnywhere_eq_false_of_mem_leafRewrites hr tr htr
    rw [heq, derivedAnywhere_of_isDerived hder] at h1
    exact Bool.noConfusion h1

/-- **(A) in the CONSUMER's exact shape.** `Cascade.lean:713`'s
    `exact rewriteClosure_subject_pred_ne …` has `NoTtuTarget S R` and
    `isDerived S (dt, R) = true` in scope; post-flip it needs the L twin at the same premises,
    and this is it — `rewriteClosureL_subject_pred_ne` with its `TtuTargetsSatL` premise
    manufactured rather than assumed. -/
theorem rewriteClosureL_subject_pred_ne_of_noTtuTarget {R dt : String}
    (hnt : ∀ r ∈ schemaRewrites S, ∀ tr, r.kind = RuleKind.ttu tr → tr ≠ R)
    (hder : isDerived S (dt, R) = true) {t : Tuple} (ht : t.subject.predicate ≠ R)
    {u : Tuple} (hu : u ∈ rewriteClosureL S (rawWriteTuples S t)) :
    u.subject.predicate ≠ R :=
  rewriteClosureL_subject_pred_ne (ttuTargetsSatL_ne_of_noTtuTarget hnt hder) ht hu

end ObligationAPremise

namespace LeafRuleWitness

/-- The canonical boolean shape, and the one whose measured rules head this file:
    `viewer := editor but not banned`. -/
def SlV : Schema :=
  ⟨[(("doc", "editor"), .direct [("user", BARE, false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "viewer"), .excl (.computed "editor") (.computed "banned"))], []⟩

/-- **Non-vacuity: the derived branch is REACHED.** -/
theorem slV_derived : isDerived SlV ("doc", "viewer") = true := by decide

/-- **The measured rule set**, verbatim from the live compile in the module header:
    `editor ↦ viewer.0` and `banned ↦ viewer.1`. THE fact that makes 4c-i necessary —
    the two arms produce shape-identical tuples and must land on different leaves. -/
theorem lrV_rules :
    leafRewrites SlV =
      [⟨"doc", "editor", leafPred "viewer" 0, .computed⟩,
       ⟨"doc", "banned", leafPred "viewer" 1, .computed⟩] := by decide

/-- **…and the untainted layer emits NOTHING for this key** — `schemaRewrites`' taint
    filter is what leaves the hole 4c-i fills. Without this the previous theorem is
    consistent with the rules being emitted twice. -/
theorem lrV_untainted_layer_silent : schemaRewrites SlV = [] := by decide

/-- Scope-doc §11.5's shape: `approver := ([user] or viewer) but not banned`. The
    storage leaf takes index 0, so the RULE arms are 1 and 2 — a rule layer that
    counted only its own leaves would put them at 0 and 1. -/
def SlSw : Schema := LeafWitness.Sw

theorem lrSw_rules :
    leafRewrites SlSw =
      [⟨"doc", "viewer", leafPred "approver" 1, .computed⟩,
       ⟨"doc", "banned", leafPred "approver" 2, .computed⟩] := by decide

/-- The pure-TTU shape: `access := viewer from parent but not banned`. The TTU arm is a
    `ttu` rule keyed on the TUPLESET relation and carrying the target as the rewritten
    subject predicate — Python's measured
    `Rule if(rel='parent') -> then(rel='access.0', subj_pred='viewer')`. -/
def SlStP : Schema := LeafWitness.StP

theorem lrStP_rules :
    leafRewrites SlStP =
      [⟨"doc", "parent", leafPred "access" 0, .ttu "viewer"⟩,
       ⟨"doc", "banned", leafPred "access" 1, .computed⟩] := by decide

/-- **The MERGE, at the rule layer.** `r := (a or b) but not banned`: BOTH `a` and `b`
    are rules targeting the SAME leaf `r.0`, and `banned` targets `r.1`. Measured
    2026-08-16; under the pre-2026-08-16 allocation `b` would target `r.1` and `banned`
    `r.2`. This is the witness sabotage S11 exists for. -/
def SlA : Schema := LeafWitness.SmA

theorem lrA_rules :
    leafRewrites SlA =
      [⟨"doc", "a", leafPred "r" 0, .computed⟩,
       ⟨"doc", "b", leafPred "r" 0, .computed⟩,
       ⟨"doc", "banned", leafPred "r" 1, .computed⟩] := by decide

/-- **★★ The n-ary SPINE, at the rule layer.** `LeafWitness.SmN` is
    `formal/conformance/corpus.py::SCHEMAS`' in-fragment `nary_union_derived4`:
    `any_of4 := a or b or c or safe` with `safe` derived, encoded by
    `formal/conformance/encode.py`'s `_fold_binary` as `((a ∪ b) ∪ c) ∪ safe`.

    Python emits three rules at three DIFFERENT leaves. Before the 2026-08-16b
    `unionSpineLeaves` correction the allocation merged the accidentally-pure left spine
    into ONE leaf and this rule set collapsed to `a, b, c ↦ any_of4.0` — a wrong model of
    an in-fragment corpus, which `diff_states` would have caught only after 4c-ii's whole
    cone was paid. -/
def SlN : Schema := LeafWitness.SmN

theorem lrN_rules :
    leafRewrites SlN =
      [⟨"doc", "x", leafPred "safe" 0, .computed⟩,
       ⟨"doc", "blocked", leafPred "safe" 1, .computed⟩,
       ⟨"doc", "a", leafPred "any_of4" 0, .computed⟩,
       ⟨"doc", "b", leafPred "any_of4" 1, .computed⟩,
       ⟨"doc", "c", leafPred "any_of4" 2, .computed⟩] := by decide

/-- **The untainted control.** A schema with no derived key emits no leaf rules at all,
    so the extension cannot perturb the untainted fragment. Checked at a store rather
    than inferred from the filter. -/
def SlUnt : Schema :=
  ⟨[(("doc", "editor"), .direct [("user", BARE, false)]),
    (("doc", "viewer"), .computed "editor")], []⟩

theorem lrUnt_no_leaf_rules : leafRewrites SlUnt = [] := by decide

/-- …and the full rule set is then byte-identical to today's. -/
theorem lrUnt_subsumed : schemaRewritesL SlUnt = schemaRewrites SlUnt := by decide

/-- **The untainted layer is non-empty here** — so `lrUnt_subsumed` is not the trivial
    `[] = []`. -/
theorem lrUnt_nonempty : schemaRewrites SlUnt ≠ [] := by decide

/-! ### The end-to-end fact: a raw write now reaches the LEAF closure edges -/

/-- A raw write on the untainted `editor` of `SlV`. Its rewrite closure must now contain
    the `viewer.0` copy — the edge projection P6 used to drop, and the reason leg 7
    exists. ★ **RETIRED 2026-09-05** (P3 landed (α)+(R5); P6 branch deleted from
    `formal/conformance/extractor.py`), so this copy now reaches the compare arm. -/
def tlEditor : Tuple := ⟨⟨"user", "alice", BARE⟩, "editor", ⟨"doc", "d1"⟩⟩

/-- **THE 4c-i PAYOFF, at a store.** Under the full rule set the closure of a raw
    `editor` write contains `doc:d1#viewer.0@user:alice`; under today's `rewriteClosure`
    it does not, because `schemaRewrites` filtered the derived key out. Both halves are
    stated so the red is attributable to the EXTENSION, not to a change in the base. -/
theorem lrV_closure_reaches_leaf :
    (rewriteClosureL SlV (rawWriteTuples SlV tlEditor)).contains
      ⟨⟨"user", "alice", BARE⟩, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩ = true := by decide

theorem lrV_closure_today_misses_leaf :
    (rewriteClosure SlV tlEditor).contains
      ⟨⟨"user", "alice", BARE⟩, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩ = false := by decide

/-- **The forked write is contentful at STATE level**, not merely at list level: from
    the empty state the leaf-routed write and today's rule-routed write produce
    different edge lists. The `writeDirectRaw_edges_ne` analogue for 4c-i.

    ⚠ **THIS PIN NOW HAS TWO CAUSES AND THEREFORE ATTRIBUTES NEITHER** (`P6` step 3b
    re-point #2, 2026-09-14). Until the re-point the only difference between the two sides
    was the leaf ROUTING; now `writeRulesRaw` also folds `writeBridgedOne` while
    `writeRules` folds `writeDirect`, so the inequality would survive even if routing were
    the identity. It is kept because the audit pins its name, but the routing-only evidence
    is the LIST pair `lrV_closure_reaches_leaf` / `lrV_closure_today_misses_leaf` above,
    which names no `GraphState` and is untouched by bridging; the bridging-only evidence is
    `SlBridgeWitness` below, whose control holds routing fixed. Do not cite this theorem
    for either half on its own. -/
theorem lrV_writeRulesRaw_edges_ne :
    ((emptyState SlV).writeRulesRaw SlV tlEditor).edges
      ≠ ((emptyState SlV).writeRules SlV tlEditor).edges := by decide

/-! ### ★★ `P6` step 3b RE-POINT #2 — the COMPOSITION's red-to-green arm (2026-09-14)

The plan's ASSURANCE BLOCKER, discharged here rather than deferred: every step-3a `decide`
witness (`UsStarWrite.lean::BridgedWriteWitness`, `Cascade.lean::InBridgeLegWitness`,
`::BridgedLegWitness`) is stated on `bridgePre` / `writeBridgedOne` / `releasePostLogged`
**directly**, never through `writeRulesRaw`. So re-point #2 cannot flip any of them and the
composition would otherwise land with ZERO red-to-green evidence — the exact shape
`docs/sabotage-procedure.md` calls an assurance step that fails by passing.

`writeRulesRaw_creates_the_bridge` below is the arm that was FALSE on 2026-09-13 and is TRUE
on 2026-09-14, and `plain_fold_misses_the_bridge` spells the pre-re-point definition out
IN FULL so the delta is exhibited in the file rather than described in a docstring. The
control (`control_agrees_where_nothing_bridges`) holds the routing fixed and shows the two
folds AGREE at `SlV` — without it the payoff would be satisfied by a `writeBridgedOne` that
differs from `writeDirect` everywhere, which would say nothing about the bridge.

⚠ **What this block deliberately does NOT claim.** It does not show the widened
`TtuStarFreeW` predicate inhabited (that is step 4's obligation, over `schemaRewrites`) and
it does not touch the `leafRewrites` ttu arm, which sits outside `TtuStarFree`'s quantifier
entirely — see `CascadeStable.lean::StarBareWitness.slStP_leaf_ttu_breaks_star_bare`.

##### CONTROLLED — MUTATION SWEEP (2026-09-14)

Four mutations, one whole-module `lake build` each, file restored byte-clean between runs
(`md5 7633435b9777510d06b11b2369c3a9f0` before and after the sweep). **The GREEN column was
written down BEFORE each run**, which is the only way a table like this distinguishes "the
pin is load-bearing" from "the module is broken". Literal `lake` output, elided only where
a line repeats:

```
M0  INSTRUMENT CONTROL -- flip `slBridge_derived`'s own claim, `= true` -> `= false`.
    RED: exactly 1 declaration, and the attribution names it.
      error: LeafRules.lean:2037:78: Tactic `decide` proved that the proposition
        isDerived SlBridge ("doc", "viewer") = false
      is false
    -> the harness attributes a single-declaration red. Without this row every table
       below could be a broken module reading as a discovery (`P6` step 0, 2026-09-13).

M1  THE DELIVERABLE -- revert the fold in `GraphState.writeRulesRaw`,
    `acc.writeBridgedOne u` -> `acc.writeDirect u` (i.e. undo re-point #2 and nothing else).
    RED: 8 declarations = `writeRulesRaw_untaintedSchema` (:406, unsolved goals), the five
    mechanical corollaries (:429/:433/:437/:441/:449, Type mismatch), and TWO KERNEL
    REFUTATIONS:
      error: LeafRules.lean:2073:73: Tactic `decide` proved that the proposition
        (subjNode tlGrp.subject, wGrp) ∈ ((emptyState SlBridge).writeRulesRaw SlBridge tlGrp).edges
      is false
      error: LeafRules.lean:2102:48: Tactic `decide` proved that the proposition
        List.count (subjNode tlGrp.subject, wGrp) ((emptyState SlBridge).writeRulesRaw SlBridge tlGrp).edges = 1
      is false
    GREEN as predicted: `plain_fold_misses_the_bridge`, `control_agrees_where_nothing_bridges`,
    all five `slBridge_*` non-vacuity pins, both grant pins, `lrV_writeRulesRaw_edges_ne`.
    -> the payoff pins are FALSE without the re-point, and they fail as `decide`
       REFUTATIONS rather than as incomplete proofs. That matters: a red on a helper
       lemma does NOT propagate (Lean admits a failed declaration at its stated type --
       `TK68` 2026-09-13e, and again on the T2 sweep 2026-09-14), so a pin routed through
       a helper could never have shown this. These sit on the primitive.

M2  ATTRIBUTION -- drop the wildcard flag from the witness schema alone,
    `("group", "member", true)` -> `("group", "member", false)`. Source untouched.
    RED: exactly 3 = `slBridge_subject_is_bridged_in` (:2059) plus the SAME two payoff
    refutations (:2073, :2102).
    GREEN: `slBridge_derived`, `slBridge_rules`, `slBridge_closure_length`,
    `slBridge_closure_shares_the_subject` -- i.e. the ROUTING is provably unmoved by this
    mutation.
    -> the bridge is driven by the wildcard flag and by nothing else in the schema. This is
       the row that separates re-point #2's effect from leaf routing's.

M3  NON-VACUITY OF THE NEGATIVE PIN -- retarget `plain_fold_misses_the_bridge`'s own
    statement from `acc.writeDirect u` to `acc.writeBridgedOne u`.
    RED: exactly 1.
      error: LeafRules.lean:2084:82: Tactic `decide` proved that the proposition
        (subjNode tlGrp.subject, wGrp) ∉ (List.foldl (fun acc u => acc.writeBridgedOne u) …).edges
      is false
    -> the `∉` is observing the MATERIALISER, not an unreachable `wGrp`. A mis-shaped
       bridge target would have left this green while reddening the payoff; it does the
       opposite, which is the discriminating outcome. (`P6` step 2, 2026-09-13c: a mutation
       that does not move the property under test reports INERT and reads exactly like a
       clean pin — so say what the edit was supposed to move, and check it moved.)
```

⚠ **Honest limit of this sweep.** It is a MODULE sweep, not a tree sweep: a mutation here
stops the build at `LeafRules`, so every downstream consumer is un-elaborated and the RED
lists mean *"at least these"*, never *"only these"*.

⚠ **The line numbers inside the fenced block are the swept file's, `md5
7633435b9777510d06b11b2369c3a9f0`, and DO NOT resolve in the file you are reading** —
appending this note pushed everything below it down. They are kept because they are part of
the literal observed output and editing them would make the quotation a paraphrase. Resolve
by SYMBOL; every declaration named above is in this namespace. -/
namespace SlBridgeWitness

/-- `SlV` plus ONE restriction: `doc#editor` additionally accepts `[group:*#member]`.
    Everything else is character-for-character `SlV`, so the boolean shape, the taint and
    the leaf allocation are all unchanged and the delta is the wildcard flag alone. -/
def SlBridge : Schema :=
  ⟨[(("doc", "editor"), .direct [("user", BARE, false), ("group", "member", true)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "viewer"), .excl (.computed "editor") (.computed "banned"))], []⟩

/-- A raw `editor` write whose SUBJECT is a concrete of the bridged-in shape. -/
def tlGrp : Tuple := ⟨⟨"group", "g1", "member"⟩, "editor", ⟨"doc", "d1"⟩⟩

/-- The bridge target of `tlGrp`'s subject. -/
def wGrp : NodeKey := wAnyNode ("group", "member")

/-- **NON-VACUITY (routing).** The schema is genuinely derived, so the leaf layer is live
    and this is the LEAF-routed path, not a plain write wearing its name. -/
theorem slBridge_derived : isDerived SlBridge ("doc", "viewer") = true := by decide

/-- **NON-VACUITY (routing), measured not assumed** — the same two-leaf allocation `SlV`
    gets, so the control below differs from this witness in the wildcard flag ONLY. -/
theorem slBridge_rules :
    leafRewrites SlBridge =
      [⟨"doc", "editor", leafPred "viewer" 0, .computed⟩,
       ⟨"doc", "banned", leafPred "viewer" 1, .computed⟩] := by decide

/-- **NON-VACUITY (multiplicity).** The fold runs over TWO members — the raw write and its
    `viewer.0` leaf copy — which is what makes `keeps_one_bridge_copy` a claim about the
    presence guard rather than about a one-element fold. -/
theorem slBridge_closure_length :
    (rewriteClosureL SlBridge (rawWriteTuples SlBridge tlGrp)).length = 2 := by decide

/-- …and BOTH members share the subject, so both would bridge. -/
theorem slBridge_closure_shares_the_subject :
    (rewriteClosureL SlBridge (rawWriteTuples SlBridge tlGrp)).all
      (fun u => u.subject == tlGrp.subject) = true := by decide

/-- **NON-VACUITY (bridging).** The subject endpoint really is bridge-eligible here… -/
theorem slBridge_subject_is_bridged_in :
    (emptyState SlBridge).bridgedInConcrete (subjNode tlGrp.subject) = true := by decide

/-- …and the OBJECT endpoint is not, so every pin below is the SUBJECT-side
    `ensureInBridges` call and cannot be passed off as the object-side one. -/
theorem slBridge_object_is_not_bridged_in :
    (emptyState SlBridge).bridgedInConcrete
      (objNode tlGrp.object tlGrp.relation) = false := by decide

/-- ★★ **THE PAYOFF — re-point #2, observed at the composition.** The leaf-routed write
    materialises the in-bridge. **This proposition was FALSE on 2026-09-13** (literal
    `writeRulesRaw` of that date is `plain_fold_misses_the_bridge` below) and is TRUE on
    2026-09-14; nothing else in the tree pins it. -/
theorem writeRulesRaw_creates_the_bridge :
    (subjNode tlGrp.subject, wGrp)
      ∈ ((emptyState SlBridge).writeRulesRaw SlBridge tlGrp).edges := by decide

/-- ★★ **…and the PRE-RE-POINT definition, spelled out in full, does not.** This is the
    body `GraphState.writeRulesRaw` had until 2026-09-14 with `writeDirect` in the fold —
    written out rather than cited, so the red-to-green delta survives in the file even after
    the definition it names has moved on. ⚠ Do NOT "simplify" this to
    `σ.writeRules SlBridge tlGrp`: that would change the LIST as well as the materialiser
    and stop attributing anything. -/
theorem plain_fold_misses_the_bridge :
    (subjNode tlGrp.subject, wGrp)
      ∉ ((rewriteClosureL SlBridge (rawWriteTuples SlBridge tlGrp)).foldl
          (fun acc u => acc.writeDirect u) (emptyState SlBridge)).edges := by decide

/-- ★ **ATTRIBUTION CONTROL — routing held fixed.** At `SlV`, which differs from
    `SlBridge` by the single wildcard flag and therefore has the identical leaf routing, the
    bridged fold and the plain fold produce the SAME edges. So the two pins above are the
    BRIDGE's doing and not "the two folds differ everywhere". -/
theorem control_agrees_where_nothing_bridges :
    ((emptyState SlV).writeRulesRaw SlV tlEditor).edges
      = ((rewriteClosureL SlV (rawWriteTuples SlV tlEditor)).foldl
          (fun acc u => acc.writeDirect u) (emptyState SlV)).edges := by decide

/-- ★ **The presence guard survives the LEAF-ROUTED composition** — `P6` step 2's
    `ensureInBridges_count_le_one` observed through `writeRulesRaw`, where the fold really
    does call `ensureInBridges` once per closure member. Two members share the subject;
    exactly one bridge copy results. Before the step-2 guard this would read `2`, and the
    per-write accumulation is the `_leak_accumulates` shape. -/
theorem writeRulesRaw_keeps_one_bridge_copy :
    (((emptyState SlBridge).writeRulesRaw SlBridge tlGrp).edges.count
      (subjNode tlGrp.subject, wGrp)) = 1 := by decide

/-- ★ **Bridging does not cost the grant the write was for.** -/
theorem writeRulesRaw_keeps_the_raw_grant :
    (subjNode tlGrp.subject, objNode tlGrp.object tlGrp.relation)
      ∈ ((emptyState SlBridge).writeRulesRaw SlBridge tlGrp).edges := by decide

/-- ★ **…nor the LEAF copy's grant**, which is the half re-point #2 composes with: routing
    and bridging are both live in the same fold, at the same store. -/
theorem writeRulesRaw_keeps_the_leaf_grant :
    (subjNode tlGrp.subject, objNode tlGrp.object (leafPred "viewer" 0))
      ∈ ((emptyState SlBridge).writeRulesRaw SlBridge tlGrp).edges := by decide

end SlBridgeWitness

/-! ### Non-vacuity of the superset-extras lemma (4c-ii step 2)

`rewriteClosureL_extras_leafNode` carries four premises, and a lemma whose premises
never hold at once is true and says nothing — the `graph_correct_public` VACUITY
WARNING shape (PROOF_STATUS 2026-08-28b), recurring. So the premises are DISCHARGED
at `SlV`/`tlEditor` — all four, no hypothesis survives — and the lemma is APPLIED at
the exact extra the `lrV_closure_reaches_leaf` / `lrV_closure_today_misses_leaf`
pair pins: `doc:d1#viewer.0@user:alice` is in the leaf-routed closure and NOT in
today's, so the instantiation is FORCED onto the `LeafNode` disjunct. The conclusion
below is thereby derived *through the lemma* on a reachable instance, never decided
directly — a `by decide` of the conclusion alone would prove nothing about the
lemma's applicability. -/

/-- `WF SlV` — same shape as `LeafWitness.wf`; no `WF` witness for `SlV` existed
    anywhere importable, so it is proved here rather than found. -/
theorem slV_wf : WF SlV := ⟨by
  intro p hp
  simp only [SlV, List.mem_cons, List.not_mem_nil, or_false] at hp
  rcases hp with rfl | rfl | rfl <;> simp [relNameOK, String.contains_char_eq]⟩

/-- **The superset-extras lemma is NON-VACUOUS**: at `SlV`/`tlEditor` every premise is
    discharged (`hWF` := `slV_wf`; `hmd`, `hon` and the seed membership by `decide`;
    `hne` via `hne_of_keys_nonempty` + `decide`), and on the pinned extra it must take
    the `LeafNode` disjunct, because the left one is refuted (`by decide`, the
    membership half of `lrV_closure_today_misses_leaf`). -/
theorem rewriteClosureL_extras_leafNode_nonvacuous :
    LeafNode SlV (objNode ⟨"doc", "d1"⟩ (leafPred "viewer" 0)) := by
  have h := rewriteClosureL_extras_leafNode slV_wf (by decide)
    (hne_of_keys_nonempty (by decide)) (t := tlEditor) (by decide)
    ⟨⟨"user", "alice", BARE⟩, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩ (by decide)
  rcases h with hmem | hleaf
  · exact absurd hmem (by decide)
  · exact hleaf

/-! ### Non-vacuity of `NoLeafSubjects` (4c-ii step 4) — and the failing control

⚠ **Trap 7, restated where it can bite.** `lrV_untainted_layer_silent` above proves
`schemaRewrites SlV = []`, so `SlV` cannot witness ANYTHING about the untainted layer:
a premise quantified over it is discharged there by emptiness, which is the exact shape
that makes `rewriteClosureL_extras_leafNode`'s `hmd` vacuous. Every witness in this
block therefore runs at `SnlBoth`, whose two layers are both non-empty and both carry a
**TTU** rule — the only rule kind that can mint a subject predicate at all.

The instrument is CONTROLLED two ways: a positive pin at `SnlBoth`, and one *refutation*
per layer (`noLeafSubjects_false_leafLayer` / `noLeafSubjects_false_untLayer`). A
narrowing of the quantifier to either single layer leaves the positive pin green and
reddens the refutation for the dropped layer.

## ★ CONTROLLED — two sabotages, run 2026-08-31 (`docs/sabotage-procedure.md`)

Both are the *narrowest plausible* weakening (the quantifier's range, nothing else), and
both are exactly the vacuity shape trap 7 describes. ⚠ In **both** runs
`noLeafSubjects_snlBoth` — the positive pin — stayed **GREEN**. A section carrying only
that pin would have shipped either defect. That is the whole reason the refutations exist.

**(S12) The leaf layer is dropped** — `NoLeafSubjects` quantified over `schemaRewrites S`
instead of `schemaRewritesL S`. This is precisely `hmd`'s shape, and at `SlV`
(`lrV_untainted_layer_silent`: `schemaRewrites SlV = []`) it would be vacuously true.
`lake build` rc=**1**, two errors, the second naming the witness:

```text
error: ZanzibarProofs/GraphIndex/LeafRules.lean:636:16: Application type mismatch: The argument
  hr
has type
  r ∈ schemaRewritesL S
but is expected to have type
  r ∈ schemaRewrites S
in the application
  hnl r hr
error: ZanzibarProofs/GraphIndex/LeafRules.lean:991:75: Tactic `decide` proved that the proposition
  ¬NoLeafSubjects SnlBadLeaf
is false
```

(`:636` is `rewriteStepL_subject_notLeafName`, `:991` is `noLeafSubjects_false_leafLayer`,
`:1008` is `noLeafSubjects_false_untLayer` — all three verified live after this record was
inserted, by re-running both sabotages against the final file.)

**(S13) The untainted layer is dropped** — quantified over `leafRewrites S`. The mirror
image; `noLeafSubjects_false_untLayer` is the one that reddens, and
`noLeafSubjects_false_leafLayer` stays green:

```text
error: ZanzibarProofs/GraphIndex/LeafRules.lean:1008:73: Tactic `decide` proved that the proposition
  ¬NoLeafSubjects SnlBadUnt
is false
```

Restored: rc=0, 1089 jobs, `Build completed successfully`. -/

/-- **The both-layers witness.** `parent` / `banned` are storage; `editor` is an
    UNTAINTED TTU (`viewer from parent`) and so compiles into the `schemaRewrites` layer;
    `access := (viewer from parent) but not banned` is DERIVED and so compiles into the
    `leafRewrites` layer, with its TTU arm at closure leaf 0.

    `viewer` is deliberately NOT declared: `Leaf.lean::isPure`'s `!derivedAnywhere S tgt`
    conjunct has to hold for a TTU arm to allocate a closure leaf at all. -/
def SnlBoth : Schema :=
  ⟨[(("doc", "parent"), .direct [("folder", BARE, false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "editor"), .ttu "viewer" "parent"),
    (("doc", "access"), .excl (.ttu "viewer" "parent") (.computed "banned"))], []⟩

/-- **Layer 1 is non-empty and carries a TTU rule** — the direct refutation of the
    `lrV_untainted_layer_silent` shape at this witness. -/
theorem snlBoth_untainted_layer_ttu :
    schemaRewrites SnlBoth = [⟨"doc", "parent", "editor", .ttu "viewer"⟩] := by decide

/-- **Layer 2 is non-empty and also carries a TTU rule**, at the minted leaf. -/
theorem snlBoth_leaf_layer_ttu :
    leafRewrites SnlBoth =
      [⟨"doc", "parent", leafPred "access" 0, .ttu "viewer"⟩,
       ⟨"doc", "banned", leafPred "access" 1, .computed⟩] := by decide

/-- The positive pin: `NoLeafSubjects` HOLDS at the both-layers witness. On its own this
    says little — the two refutations below are what make it an instrument. -/
theorem noLeafSubjects_snlBoth : NoLeafSubjects SnlBoth := by decide

/-- Same schema, except the DERIVED key's TTU arm targets a dotted name. The untainted
    layer is untouched and still clean (`snlBadLeaf_untainted_layer_clean`), so the only
    reason `NoLeafSubjects` fails here is the LEAF layer. -/
def SnlBadLeaf : Schema :=
  ⟨[(("doc", "parent"), .direct [("folder", BARE, false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "editor"), .ttu "viewer" "parent"),
    (("doc", "access"), .excl (.ttu "viewer.0" "parent") (.computed "banned"))], []⟩

theorem snlBadLeaf_untainted_layer_clean :
    schemaRewrites SnlBadLeaf = [⟨"doc", "parent", "editor", .ttu "viewer"⟩] := by decide

/-- **REFUTATION, leaf layer.** Reddens iff the quantifier stops covering
    `leafRewrites` — the narrowing this whole section exists to make impossible. -/
theorem noLeafSubjects_false_leafLayer : ¬ NoLeafSubjects SnlBadLeaf := by decide

/-- The mirror: the UNTAINTED key's TTU arm targets a dotted name and the derived key is
    clean, so the only reason `NoLeafSubjects` fails here is the untainted layer. -/
def SnlBadUnt : Schema :=
  ⟨[(("doc", "parent"), .direct [("folder", BARE, false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "editor"), .ttu "viewer.0" "parent"),
    (("doc", "access"), .excl (.ttu "viewer" "parent") (.computed "banned"))], []⟩

theorem snlBadUnt_leaf_layer_clean :
    leafRewrites SnlBadUnt =
      [⟨"doc", "parent", leafPred "access" 0, .ttu "viewer"⟩,
       ⟨"doc", "banned", leafPred "access" 1, .computed⟩] := by decide

/-- **REFUTATION, untainted layer.** Reddens iff the quantifier stops covering
    `schemaRewrites`. -/
theorem noLeafSubjects_false_untLayer : ¬ NoLeafSubjects SnlBadUnt := by decide

/-! #### The closure corollary, applied — both layers fire on ONE write -/

/-- A raw write on the untainted storage relation `parent`, with a BARE subject. -/
def tnlParent : Tuple := ⟨⟨"folder", "f1", BARE⟩, "parent", ⟨"doc", "d1"⟩⟩

theorem tnlParent_subject_bare : tnlParent.subject.predicate = BARE := rfl

/-- The UNTAINTED layer's TTU rule fires on this write… -/
theorem snlBoth_closure_reaches_untainted_extra :
    (rewriteClosureL SnlBoth (rawWriteTuples SnlBoth tnlParent)).contains
      ⟨⟨"folder", "f1", "viewer"⟩, "editor", ⟨"doc", "d1"⟩⟩ = true := by decide

/-- …and so does the LEAF layer's, in the same closure. This pair is the "both layers at
    once" fact at the level that matters — not just "both rule lists are non-empty" but
    "both rule lists CONTRIBUTE to the closure the corollary quantifies over". -/
theorem snlBoth_closure_reaches_leaf_extra :
    (rewriteClosureL SnlBoth (rawWriteTuples SnlBoth tnlParent)).contains
      ⟨⟨"folder", "f1", "viewer"⟩, leafPred "access" 0, ⟨"doc", "d1"⟩⟩ = true := by decide

/-- **The corollary is not the identity here.** Both extras' subject predicate is
    `viewer`, REWRITTEN by a TTU rule from the seed's `BARE` — so
    `rewriteClosureL_subject_notLeafName` is genuinely propagating through the `.ttu`
    branch of `applyRRule_subject_pred`, the only branch `NoLeafSubjects` constrains. A
    `computed`-only witness would have exercised the `Or.inl` branch and proved nothing
    about the premise. -/
theorem snlBoth_extra_subject_rewritten :
    (⟨"folder", "f1", "viewer"⟩ : SubjectRef).predicate ≠ tnlParent.subject.predicate := by
  decide

/-- **The applied conclusion, derived THROUGH the corollary** at the pinned leaf-layer
    extra — never decided directly, because a `by decide` of the conclusion alone would
    say nothing about whether the corollary applies. -/
theorem noLeafSubjects_closure_nonvacuous :
    ¬ LeafNode SnlBoth (subjNode ⟨"folder", "f1", "viewer"⟩) :=
  rewriteClosureL_subject_not_leafNode_bare noLeafSubjects_snlBoth
    (t := tnlParent) tnlParent_subject_bare
    ⟨⟨"folder", "f1", "viewer"⟩, leafPred "access" 0, ⟨"doc", "d1"⟩⟩ (by decide)

/-! ### Non-vacuity of the write-path twins — obligations (A), (B), (C)

`rewriteClosureL_object` / `::rewriteClosureL_produced` / `::rewriteClosureL_subject_pred_ne`
are **INERT**: the write-path re-point that will consume them has not landed, so a green
build vets nothing about them and the pins below are the SOLE evidence
(`docs/sabotage-procedure.md` §"The INERT change").

Two separate things are pinned. **That the twins APPLY** — at a closure member which is
genuinely DERIVED rather than handed to them by the seed fan-out, so neither is a claim about
an empty or trivial set. And **that obligation (A)'s new premise is genuinely new**: the
claim that `NoTtuTarget` does not transfer to the L closure was PROSE in
`formal/history/PROOF_STATUS.md` `## Session 2026-09-03c` §4, and the `SlStP` pair below
makes it a `decide`. -/

/-- The pinned leaf-layer extra is **not a seed** — the closure produced it, `rawWriteTuples`'
    fan-out did not. This is what stops the two applications below from landing at a seed,
    where they would say nothing. -/
theorem snlBoth_leaf_extra_not_a_seed :
    ⟨⟨"folder", "f1", "viewer"⟩, leafPred "access" 0, ⟨"doc", "d1"⟩⟩ ∉
      rawWriteTuples SnlBoth tnlParent := by decide

/-- **(B) applied** at that derived extra. The object survives a `.ttu` hop that rewrote the
    SUBJECT (`snlBoth_extra_subject_rewritten`), which is the only way object preservation
    could plausibly have failed. Derived THROUGH the lemma — a `by decide` of the equation
    alone would say nothing about whether the lemma applies. -/
theorem rewriteClosureL_object_nonvacuous :
    (⟨"doc", "d1"⟩ : ObjectRef) = tnlParent.object :=
  rewriteClosureL_object (S := SnlBoth) (t := tnlParent)
    (u := ⟨⟨"folder", "f1", "viewer"⟩, leafPred "access" 0, ⟨"doc", "d1"⟩⟩) (by decide)

/-- **(C) applied**, and FORCED onto the right disjunct: the extra is not a seed, so
    "produced by a rule" is the only branch available. The rule it names lives in the
    `leafRewrites` half — `snlBoth_untainted_layer_ttu` pins `schemaRewrites SnlBoth` to its
    single member, whose `outRel` is `editor`, not `access.0`. So (C)'s quantification over
    `schemaRewritesL` rather than `schemaRewrites` is load-bearing here, not decorative. -/
theorem rewriteClosureL_produced_nonvacuous :
    ∃ r ∈ schemaRewritesL SnlBoth,
      r.objectType = "doc" ∧ r.outRel = leafPred "access" 0 := by
  rcases rewriteClosureL_produced (S := SnlBoth)
      (seeds := rawWriteTuples SnlBoth tnlParent)
      (u := ⟨⟨"folder", "f1", "viewer"⟩, leafPred "access" 0, ⟨"doc", "d1"⟩⟩)
      (by decide) with hseed | h
  · exact absurd hseed snlBoth_leaf_extra_not_a_seed
  · exact h

/-- **(A)'s premise gap, MACHINE-CHECKED rather than argued.** `SlStP` is
    `access := viewer from parent but not banned`. Its UNTAINTED layer satisfies
    `ReconcileCorrect.lean::NoTtuTarget SlStP "viewer"` — spelled out verbatim here, since
    importing `ReconcileCorrect` is refused in this file — while its FULL layer does NOT
    satisfy the L twin at the same relation, because `leafRewrites` compiles the DERIVED
    key's TTU arm into `⟨"doc", "parent", access.0, .ttu "viewer"⟩` (`lrStP_rules`).

    ⚠ The first holds VACUOUSLY — the taint filter leaves `schemaRewrites SlStP` empty — and
    that IS the finding rather than a weakness of the witness: a premise constraining only the
    untainted layer is satisfied, trivially, by a schema whose leaf layer does target the
    relation. That is exactly why obligation (A) needs a new premise instead of re-using
    `NoTtuTarget`, and it is the pair to re-run if anyone proposes threading `NoTtuTarget`
    through the re-pointed fold.

    ⚠ The `NoTtuTarget` side is deliberately NOT a `decide`: its `∀ tr, r.kind = .ttu tr → …`
    shape quantifies over ALL strings, so it has no `Decidable` instance (observed:
    *"failed to synthesize Decidable (∀ r ∈ schemaRewrites SlStP, ∀ (tr : String), …)"*).
    Routing it through `stP_untainted_layer_silent` is the better witness anyway — the empty
    rule list is the *reason* the premise holds, stated rather than hidden inside a kernel
    evaluation. -/
theorem stP_untainted_layer_silent : schemaRewrites SlStP = [] := by decide

theorem stP_untainted_layer_no_ttu_target_viewer :
    ∀ r ∈ schemaRewrites SlStP, ∀ tr, r.kind = RuleKind.ttu tr → tr ≠ "viewer" := by
  rw [stP_untainted_layer_silent]
  simp

theorem stP_full_layer_does_target_viewer :
    ¬ TtuTargetsSatL SlStP (· ≠ "viewer") := by decide

/-- The satisfiability half of the pair: `TtuTargetsSatL` is not a premise nothing meets.
    `SnlBoth`'s TTU targets are `viewer` in BOTH layers, so it satisfies the L form at
    `(· ≠ "banned")`. -/
theorem ttuTargetsSatL_snlBoth_ne_banned : TtuTargetsSatL SnlBoth (· ≠ "banned") := by decide

/-- **(A) applied** where its premise genuinely holds, at the same derived extra. The seed's
    subject predicate is `BARE` and the extra's is `viewer`, so the `.ttu` branch of
    `applyRRule_subject_pred` — the only branch `TtuTargetsSatL` constrains — is the one
    carrying the conclusion. A `computed`-only witness would have run the `Or.inl` branch and
    proved nothing about the premise. -/
theorem rewriteClosureL_subject_pred_ne_nonvacuous :
    (⟨"folder", "f1", "viewer"⟩ : SubjectRef).predicate ≠ "banned" :=
  rewriteClosureL_subject_pred_ne ttuTargetsSatL_snlBoth_ne_banned
    (t := tnlParent) (by decide)
    (u := ⟨⟨"folder", "f1", "viewer"⟩, leafPred "access" 0, ⟨"doc", "d1"⟩⟩) (by decide)

/-! ### Obligation (F) — the ATTACK, its two surviving counterexamples, and the applications

★ **STEP 1 was the attack, not the proof** (formal house rule 2, `formal/HANDOFF.md:257-272`).
Before anything was proved, the target statement was attacked at each of the three routes by
which a `BARE` relation could reach the leaf-routed closure. **Two of the three attacks
SUCCEED** against a weakened premise list, and both are pinned below as `decide`
counterexamples rather than described:

* **(i) A seed minted by `rawWriteRels`.** Attack FAILS, and provably so. A derived key's
  seeds are `leafPred t.relation i` (`Leaf.lean::mem_rawWriteRels_derived`), and
  `leafPred_ne_bare` rules those out for every `R` and `i`. No schema can be built against
  it: `leafPred R i` ends in `toString i`, a non-empty DIGIT string, and `BARE` is three
  dots. The `decide`-over-`R` route the record floated is not available (`R` is unbounded),
  which is why that lemma is structural.
* **(ii) A seed that is the raw write ITSELF, on an untainted key.** Attack **SUCCEEDS**.
  `rawWriteTuples S t = [t]` there, so a write whose own relation is `BARE` puts a
  `BARE`-relation tuple straight into the closure — `bareSeed_attack` decides it, at a schema
  for which `WF` HOLDS (`slV_wf`). So `WF` alone does not save the statement: this is what
  the twin's `hSV`/`ht` pair buys, and what
  `rewriteClosureL_rel_ne_bare_of_rel`'s `ht : t.relation ≠ BARE` buys directly.
* **(iii) A rule whose `outRel` is `BARE`.** Attack **SUCCEEDS** against a `WF`-free
  statement. `schemaRewrites` COPIES the declared relation name into `outRel`, and the only
  thing forbidding a relation literally named `"..."` is `relNameOK` — a `WF` clause, not a
  structural one. `sbareRel_closure_reaches_bare` builds that schema and decides the
  membership; `sbareRel_not_wf` pins that `WF` is exactly what excludes it. On the
  `leafRewrites` half the same attack fails, because `outRel` there is MINTED
  (`outRel_leafPred_of_mem_leafRewrites`), never copied.

Both surviving counterexamples are kept as permanent pins: they are what make (F)'s two
premises load-bearing instead of decorative, and either one going green under a future
premise-narrowing is the signal. -/

/-- ATTACK (ii). A write whose relation IS the bare sentinel, on a key `SlV` does not
    declare — hence untainted, hence `rawWriteTuples` is the identity on it. -/
def tBareRel : Tuple := ⟨⟨"user", "alice", BARE⟩, BARE, ⟨"doc", "d1"⟩⟩

theorem tBareRel_rel_is_bare : tBareRel.relation = BARE := rfl

/-- **The seed premise is load-bearing**: this closure member's relation is `BARE`, at a
    schema satisfying `WF`. Drop `ht` from `rewriteClosureL_rel_ne_bare_of_rel` and the
    statement is false here. -/
theorem bareSeed_attack :
    (rewriteClosureL SlV (rawWriteTuples SlV tBareRel)).contains tBareRel = true := by decide

/-- ATTACK (iii). A schema declaring a relation literally NAMED `BARE`. Everything else is
    ordinary: `editor` is a storage relation and the second def is an untainted `computed`,
    so it compiles into the `schemaRewrites` half and copies its own name into `outRel`. -/
def SbareRel : Schema :=
  ⟨[(("doc", "editor"), .direct [("user", BARE, false)]),
    (("doc", BARE), .computed "editor")], []⟩

/-- The rule really is minted with `outRel = BARE` — stated so the counterexample below is
    attributable to the rule layer, not to a seed. -/
theorem sbareRel_rule :
    schemaRewrites SbareRel = [⟨"doc", "editor", BARE, .computed⟩] := by decide

/-- **`WF` is load-bearing**: a raw `editor` write reaches a closure tuple whose relation is
    `BARE`, purely through the untainted rewrite arm. -/
theorem sbareRel_closure_reaches_bare :
    (rewriteClosureL SbareRel (rawWriteTuples SbareRel tlEditor)).contains
      ⟨⟨"user", "alice", BARE⟩, BARE, ⟨"doc", "d1"⟩⟩ = true := by decide

/-- …and `WF` is exactly what excludes that schema, so the counterexample is a statement
    about the premise rather than about the model. -/
theorem sbareRel_not_wf : ¬ WF SbareRel := by
  intro h
  exact h.relNames (("doc", BARE), Expr.computed "editor") (by simp [SbareRel])
    (by simp [BARE, String.contains])

/-! #### Non-vacuity — both arms of (F) are REACHED, and the drop-in shape is exercised

(F) is inert until the write-path flip lands, so a green build vets nothing about it. Three
applications below, each derived THROUGH the theorem (never `decide`d directly, which would
say nothing about applicability) and each landing on a DIFFERENT arm of the case split. -/

/-- **NON-VACUITY, the leaf-RULE arm.** `lrV_closure_reaches_leaf` pins
    `doc:d1#viewer.0@user:alice` as a closure member; its relation is a minted leaf name, so
    (F) discharges it through `outRel_ne_bare_of_mem_schemaRewritesL`'s `leafRewrites` half —
    the half where `isLeafPred` is the wrong instrument. -/
theorem rewriteClosureL_rel_ne_bare_leafArm_nonvacuous :
    leafPred "viewer" 0 ≠ BARE :=
  rewriteClosureL_rel_ne_bare_of_rel slV_wf (t := tlEditor) (by decide)
    (u := ⟨⟨"user", "alice", BARE⟩, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩) (by decide)

/-- The SEED that carries a minted leaf name: at `LeafWitness.Sw` the write `tw` is on a
    DERIVED public relation, so `rawWriteRels` re-addresses it onto `approver.0`
    (`LeafWitness.routes_to_leaf`) before the closure starts. -/
theorem swSeedLeaf_mem :
    ({ LeafWitness.tw with relation := leafPred "approver" 0 } : Tuple) ∈
      rewriteClosureL LeafWitness.Sw (rawWriteTuples LeafWitness.Sw LeafWitness.tw) := by
  decide

/-- **NON-VACUITY, the SEED arm.** Same theorem, discharged through
    `rawWriteTuples_rel_ne_bare`'s DERIVED branch (`mem_rawWriteRels_derived`) instead. The
    `SlV`/`tlEditor` witness above can never reach this branch — its write is untainted, so
    its seed list is the singleton and the derived branch is dead there. -/
theorem rewriteClosureL_rel_ne_bare_seedArm_nonvacuous :
    leafPred "approver" 0 ≠ BARE :=
  rewriteClosureL_rel_ne_bare_of_rel LeafWitness.wf (t := LeafWitness.tw) (by decide)
    swSeedLeaf_mem

/-- A one-tuple store `SlV` admits: `tlEditor` lands on the declared `editor`, whose def is a
    `Direct` arm its `user`/BARE subject matches. Needed so the drop-in form is applied at a
    store that genuinely satisfies `StoreValidRules`, not at a vacuous one. -/
theorem slV_storeValid : StoreValidRules SlV [tlEditor] := by
  intro t ht
  obtain rfl := List.mem_singleton.mp ht
  exact ⟨.direct [("user", BARE, false)], [("user", BARE, false)],
    by decide, by decide, by decide⟩

/-- **The drop-in form applied at the consumer's LITERAL argument shape** —
    `hWF`, `hSV`, `List.mem_cons_self`, `hu` — so what is checked is the expression
    `CascadeSettle.lean:112` will actually contain post-flip, not merely a lemma with a
    matching type. -/
theorem rewriteClosureL_rel_ne_bare_dropin_nonvacuous :
    leafPred "viewer" 0 ≠ BARE :=
  rewriteClosureL_rel_ne_bare slV_wf slV_storeValid List.mem_cons_self
    (u := ⟨⟨"user", "alice", BARE⟩, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩) (by decide)

/-! ### Obligation (A)'s premise — the surviving ATTACK pins, the CONTROL, and non-vacuity

Three separate things live here and they are not interchangeable:

* the **attack** pins — two schemas on which a derived TTU target reaches the allocation and
  is DROPPED, kept as `decide` facts rather than as the prose of a deleted `#eval` run;
* the **control** — `hder_load_bearing`, the machine-checked refutation of the `hder`-free
  statement, which is what makes the premise a premise instead of decoration;
* the **non-vacuity** witnesses — every new theorem applied at a fixture where its hypotheses
  genuinely hold and its interesting branch is genuinely taken, derived THROUGH the theorem.

⚠ Everything runs at `SnlBoth`, not at `SlV`: `lrV_untainted_layer_silent` proves
`schemaRewrites SlV = []`, so `SlV` discharges `hnt` by EMPTINESS and would witness nothing
about the untainted arm. `SnlBoth` carries a TTU rule in BOTH layers, which is the only
rule kind either arm of `ttuTargetsSatL_ne_of_noTtuTarget` constrains. -/

/-- **ATTACK PIN 1 — the derived TTU target mints no rule.** `LeafWitness.StD` is `access :=
    viewer from parent but not banned` with `viewer` DERIVED on `folder`. The `viewer` arm
    contributes nothing and `banned` inherits index 0 — so `leafRewrites` carries no `.ttu`
    rule at all, and the leaf-layer fact holds here for the strongest possible reason.
    (`Leaf.lean::stD_leaves` pins the same drop one layer down, at the ALLOCATION; this is
    the RULE layer, which is what `TtuTargetsSatL` quantifies over.) -/
theorem lrStD_no_ttu_rule :
    leafRewrites LeafWitness.StD =
      [⟨"folder", "e", leafPred "viewer" 0, .computed⟩,
       ⟨"folder", "b", leafPred "viewer" 1, .computed⟩,
       ⟨"doc", "banned", leafPred "access" 0, .computed⟩] := by decide

/-- **ATTACK PIN 2 — the CROSS-TYPE drop, which is why the lemma is stated over
    `derivedAnywhere` and not over `isDerived S (ty, ·)`.** Here `viewer` is UNTAINTED on
    `folder` — the only type `doc:parent` admits — and DERIVED on the unrelated type `team`.
    A same-type taint test would let `doc:access`'s TTU arm through; `derivedAnywhere` does
    not, and the arm is dropped exactly as in pin 1.

    ⚠ `Leaf.lean`'s `derivedAnywhere` section header records that Python's `compile_ruleset`
    REFUSES to compile this shape (its exclusivity pass runs the same type-agnostic name
    test), so this fixture is a MODEL-level probe and not a corpus schema. It is kept anyway,
    because it is the only shape that distinguishes the two taint tests, and the model is the
    thing `ttuTargetsSatL_ne_of_noTtuTarget` is proved about. -/
def SlXt : Schema :=
  ⟨[(("team", "z"), .direct [("user", BARE, false)]),
    (("team", "y"), .direct [("user", BARE, false)]),
    (("team", "viewer"), .excl (.computed "z") (.computed "y")),
    (("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"), .direct [("folder", BARE, false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "access"), .excl (.ttu "viewer" "parent") (.computed "banned"))], []⟩

/-- The premise of the attack: `viewer` IS derived somewhere here… -/
theorem slXt_viewer_derived_anywhere : derivedAnywhere SlXt "viewer" = true := by decide

/-- …and NOT on the type the tupleset admits — so a same-type test would pass it. -/
theorem slXt_viewer_untainted_on_folder : isDerived SlXt ("folder", "viewer") = false := by
  decide

/-- …and the TTU arm is dropped regardless: `banned` inherits index 0. -/
theorem lrXt_cross_type_drop :
    leafRewrites SlXt =
      [⟨"team", "z", leafPred "viewer" 0, .computed⟩,
       ⟨"team", "y", leafPred "viewer" 1, .computed⟩,
       ⟨"doc", "banned", leafPred "access" 0, .computed⟩] := by decide

/-- **★ THE CONTROL — `hder` is load-bearing, and this is the refutation that proves it.**
    Drop `hder` from `ttuTargetsSatL_ne_of_noTtuTarget` and the statement is FALSE, witnessed
    by `SlStP`: its untainted layer satisfies `NoTtuTarget SlStP "viewer"` (vacuously — the
    taint filter empties it, `stP_untainted_layer_silent`), yet its FULL layer targets
    `viewer` from the derived key's compiled TTU arm. The two halves already existed as the
    (A)-premise gap pins at `:2016`/`:2021`; pairing them is what turns them into an
    instrument for THIS theorem.

    The `hder`-free statement fails here precisely because `viewer` is derived NOWHERE in
    `SlStP` (`slStP_viewer_not_derived_anywhere`), which is the hypothesis being dropped. -/
theorem slStP_viewer_not_derived_anywhere : derivedAnywhere SlStP "viewer" = false := by decide

theorem hder_load_bearing :
    (∀ r ∈ schemaRewrites SlStP, ∀ tr, r.kind = RuleKind.ttu tr → tr ≠ "viewer")
      ∧ ¬ TtuTargetsSatL SlStP (· ≠ "viewer") :=
  ⟨stP_untainted_layer_no_ttu_target_viewer, stP_full_layer_does_target_viewer⟩

/-! #### Non-vacuity — every new theorem applied where its branches are REACHED -/

/-- `access` is derived at `SnlBoth`, on `doc`. -/
theorem snlBoth_access_derived : isDerived SnlBoth ("doc", "access") = true := by decide

/-- **`derivedAnywhere_of_isDerived` applied**, not decided: the type-agnostic conclusion
    comes out of the one-witness lemma. -/
theorem derivedAnywhere_of_isDerived_nonvacuous : derivedAnywhere SnlBoth "access" = true :=
  derivedAnywhere_of_isDerived (dt := "doc") snlBoth_access_derived

/-- **The leaf arm is REACHED.** `SnlBoth`'s leaf layer really does contain a rule with a TTU
    target, so `derivedAnywhere_eq_false_of_mem_leafRewrites` is not quantifying over an empty
    set of interesting rules — the shape that would make the whole leaf half vacuous. -/
theorem snlBoth_leaf_layer_has_ttu_target :
    ∃ r ∈ leafRewrites SnlBoth, ttuTargets r ≠ [] := by decide

/-- **`derivedAnywhere_eq_false_of_mem_leafRewrites` applied THROUGH the lemma**, at that
    rule and its target. A `by decide` of `derivedAnywhere SnlBoth "viewer" = false` would
    prove the fact without proving the lemma reaches it. -/
theorem derivedAnywhere_eq_false_of_mem_leafRewrites_nonvacuous :
    derivedAnywhere SnlBoth "viewer" = false :=
  derivedAnywhere_eq_false_of_mem_leafRewrites
    (r := ⟨"doc", "parent", leafPred "access" 0, .ttu "viewer"⟩) (by decide) "viewer"
    (by decide)

/-- The untainted premise at `SnlBoth`, in the unfolded `NoTtuTarget` shape. NOT vacuous:
    `snlBoth_untainted_layer_ttu` pins that this layer contains a TTU rule, whose target
    `viewer` is what the `≠ "access"` obligation is discharged against. -/
theorem snlBoth_untainted_layer_no_ttu_target_access :
    ∀ r ∈ schemaRewrites SnlBoth, ∀ tr, r.kind = RuleKind.ttu tr → tr ≠ "access" := by
  rw [snlBoth_untainted_layer_ttu]
  intro r hr tr hk
  simp only [List.mem_singleton] at hr
  subst hr
  simp only [RuleKind.ttu.injEq] at hk
  subst hk
  decide

/-- **★ (A)'s PREMISE, MANUFACTURED.** `TtuTargetsSatL SnlBoth (· ≠ "access")` derived through
    `ttuTargetsSatL_ne_of_noTtuTarget` from `NoTtuTarget` + "`access` is derived" — never
    `decide`d, so what is checked is the THEOREM's applicability and not just the fact.
    Compare `ttuTargetsSatL_snlBoth_ne_banned` (`:2027`), which IS a `decide`: that one shows
    the predicate is satisfiable, this one shows it is DERIVABLE from the consumers' premises. -/
theorem ttuTargetsSatL_snlBoth_ne_access_manufactured :
    TtuTargetsSatL SnlBoth (· ≠ "access") :=
  ttuTargetsSatL_ne_of_noTtuTarget snlBoth_untainted_layer_no_ttu_target_access
    (dt := "doc") snlBoth_access_derived

/-- **The consumer-shaped corollary applied end to end.** The seed is the untainted write
    `tnlParent` (subject predicate `BARE`), and the tuple examined is the LEAF-layer extra
    `snlBoth_closure_reaches_leaf_extra` pins — a tuple the leaf layer's TTU rule minted, so
    the `.ttu` branch of `applyRRule_subject_pred` is the one carrying the conclusion. A
    `computed`-only witness would have run `Or.inl` and exercised no premise. -/
theorem rewriteClosureL_subject_pred_ne_of_noTtuTarget_nonvacuous :
    (⟨"folder", "f1", "viewer"⟩ : SubjectRef).predicate ≠ "access" :=
  rewriteClosureL_subject_pred_ne_of_noTtuTarget
    snlBoth_untainted_layer_no_ttu_target_access (dt := "doc") snlBoth_access_derived
    (t := tnlParent) (by decide)
    (u := ⟨⟨"folder", "f1", "viewer"⟩, leafPred "access" 0, ⟨"doc", "d1"⟩⟩) (by decide)

/-- **The purity lemma is non-vacuous at a MERGED leaf** — the arm a lemma written only for
    atoms would miss. `SlA` is `r := (a or b) but not banned`, whose leaf `r.0` is the merged
    `.union (.computed "a") (.computed "b")` (`Leaf.lean::smA_merges`); the lemma says that
    merged subtree is pure. -/
theorem isPure_of_closure_mem_persistedLeaves_merged_nonvacuous :
    isPure SlA "doc" (.union (.computed "a") (.computed "b")) = true :=
  isPure_of_closure_mem_persistedLeaves (ty := "doc")
    (e := .excl (.union (.computed "a") (.computed "b")) (.computed "banned")) (by decide)

end LeafRuleWitness

/-! ## Step 4c-ii, step 6 — THE LOCALISATION: where the flip's damage lives, exactly

`rewriteClosureL_extras_leafNode` (above) is a ONE-SIDED classification: every tuple the
leaf-routed closure produces that today's closure does not is `LeafNode`-targeted. That is
what the shadow transport needs, and it is deliberately weak — it says nothing about the
tuples the two closures SHARE, and nothing about the direction in which the plain closure
could be the larger one.

This section closes both gaps. The two membership lemmas below say exactly where the two
closures agree:

* **away from LEAF names the leaf-routed closure adds nothing**
  (`mem_rewriteClosure_of_mem_rewriteClosureL_notLeaf`), and
* **away from DERIVED names it loses nothing**
  (`mem_rewriteClosureL_of_mem_rewriteClosure_notDerived`),

so on the intersection of the two guards the two closures have the SAME members
(`mem_rewriteClosureL_iff_notLeaf_notDerived`).

⚠ **ROLE CHANGE at step R5, recorded because this docstring used to say the opposite.** It
read: "Rounds 3–5 left three `sorry`s standing for the R3 occurrence-count invariant
(`CascadeStrata.lean::reachedByW3d2_untOccCount`, `::reachedByW3d2_srcOccCount`,
`RemoveOccCount.lean::reachedByW3d2E_untOccCount`), each REFUTED in the kernel post-flip …
the flip does not break R3, it PUNCTURES it", and it named `::reachedByW3d2_untOccCount_notLeaf`
/ `::reachedByW3d2E_untOccCount_notLeaf` as the guarded repairs that landed sorry-free.
All three R3 theorems are now UNGUARDED THEOREMS — R5 made both legs fold the same
leaf-routed closure and moved `untOccCount` onto it, so there is no puncture left to
localise — and the two guarded twins are deleted as redundant. What this section supplies
now is the PLAIN↔LEAF-ROUTED bridge that
`CascadeStrataSettle.lean::untOccCount_eq_plainOcc_of_notLeaf` uses to carry facts about the
un-re-pointed PLAIN shadow rebuild (`ReachedByRulesAdmitted`) across to `untOccCount`. That
is a load-bearing role, not a repair role.

⚠ **Both guards are load-bearing and both are pinned by a witness below**, per
`docs/sabotage-procedure.md` — a localisation lemma whose guards are decorative is exactly
the "assurance step that fails by passing" this repo keeps finding. Dropping `hlp` is
refuted by `lrV_localisation_needs_notLeaf`; dropping `hut` by
`lrV_localisation_needs_notDerived`. Neither is a hypothetical: they are the two mechanisms
the flip actually has.

The premises are the ones this file already threads (`rewriteClosureL_extras_leafNode`'s
`hmd` = `LeafScope.matchNotLeaf`, and `hnd` = the second component of
`RestrictBase.lean::RewriteMatchDeclared`, which `GraphAdmission.matchDecl` carries). They
are taken as bare binders rather than as `LeafScope`/`RewriteMatchDeclared` so this file
still needs no import from `RestrictBase` — the same reason
`matchNotLeaf_of_declared` is stated over `hdecl`. -/

/-- The empty worklist stays empty at any fuel.

    ⚠ `RestrictBase.lean::rewriteClosureAux_nil` is the SAME fact under a different name.
    This file sits below `RestrictBase` in the import order and deliberately does not import
    it, so the two-line induction is repeated under a distinct name; naming it identically
    would make every module that sees both an ambiguous-identifier error. -/
theorem rewriteClosureAux_nil_frontier (S : Schema) : ∀ n, rewriteClosureAux S n [] = [] := by
  intro n
  induction n with
  | zero => rfl
  | succ m ih =>
    show [] ++ rewriteClosureAux S m (List.flatMap (rewriteStep S) []) = []
    simpa using ih

/-- **No untainted rewrite fires on a derived-key tuple.** A firing rule's match key would
    BE the derived key, but every schema rewrite's match key is untainted (`hnd`). The
    `RewriteMatchDeclared`-based twin is `RestrictBase.lean::rewriteClosure_derived_eq_seed`;
    this is the `hnd`-only form, so it is available here. -/
theorem rewriteStep_nil_of_derived {S : Schema}
    (hnd : ∀ r ∈ schemaRewrites S, isDerived S (r.objectType, r.matchRel) = false)
    {t : Tuple} (hd : isDerived S (t.object.type, t.relation) = true) :
    rewriteStep S t = [] := by
  unfold rewriteStep
  rw [List.filterMap_eq_nil_iff]
  intro r hr
  unfold applyRRule
  rw [if_neg]
  rintro ⟨hrel, htype⟩
  have hu := hnd r hr
  rw [htype, hrel] at hd
  rw [hu] at hd
  exact Bool.false_ne_true hd

/-- **The dead-end seed, membership form.** A derived-key tuple's plain rewrite closure is
    the seed alone, so anything in it IS the seed. -/
theorem mem_rewriteClosure_derived_self {S : Schema}
    (hnd : ∀ r ∈ schemaRewrites S, isDerived S (r.objectType, r.matchRel) = false)
    {t : Tuple} (hd : isDerived S (t.object.type, t.relation) = true)
    {u : Tuple} (hu : u ∈ rewriteClosure S t) : u = t := by
  have hstep := rewriteStep_nil_of_derived hnd hd
  rw [mem_rewriteClosure_iff] at hu
  unfold rewriteClosureRaw at hu
  rw [rewriteClosureAux] at hu
  have hfm : List.flatMap (rewriteStep S) [t] = [] := by simp [hstep]
  rw [hfm, rewriteClosureAux_nil_frontier] at hu
  simpa using hu

/-- **(→) AWAY FROM LEAF NAMES THE LEAF-ROUTED CLOSURE ADDS NOTHING.** The sharp form of
    `rewriteClosureL_extras_leafNode`: that lemma's second disjunct is `LeafNode`, a
    predicate with three further conjuncts; here the disjunct is discharged outright by the
    ONE observable a consumer actually has at an edge endpoint — the target predicate is not
    a minted (dot-carrying) name. Needs neither `WF` nor the `hne` non-empty-name guard,
    which is why it can serve the occurrence-count sites where no `LeafScope` is in hand. -/
theorem mem_rewriteClosure_of_mem_rewriteClosureL_notLeaf {S : Schema}
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false)
    {t u : Tuple} (hu : u ∈ rewriteClosureL S (rawWriteTuples S t))
    (hlp : isLeafPred u.relation = false) : u ∈ rewriteClosure S t := by
  rw [mem_rewriteClosureL_iff] at hu
  unfold rewriteClosureRawL at hu
  have hobj : ∀ w ∈ rawWriteTuples S t, w.object = t.object := by
    intro w hw
    obtain ⟨r, _, rfl⟩ := List.mem_map.mp hw
    rfl
  have hinv : ∀ w ∈ rawWriteTuples S t, w ∈ [t] ∨ ∃ R i, w.relation = leafPred R i ∧
      isDerived S (t.object.type, R) = true := by
    intro w hw
    by_cases hd : isDerived S (t.object.type, t.relation) = true
    · obtain ⟨r, hr, rfl⟩ := List.mem_map.mp hw
      refine Or.inr ?_
      obtain ⟨i, rfl⟩ := mem_rawWriteRels_derived hd hr
      exact ⟨t.relation, i, rfl, hd⟩
    · rw [rawWriteTuples_untainted (by simpa using hd)] at hw
      exact Or.inl hw
  obtain ⟨hres, _⟩ := rewriteClosureAuxL_extras hmd t (S.keys.length + 1)
    (rawWriteTuples S t) [t] hobj hinv u hu
  rcases hres with hmem | ⟨R, i, hrel, _⟩
  · exact mem_rewriteClosure_iff.mpr hmem
  · exfalso
    rw [hrel, isLeafPred_leafPred] at hlp
    exact Bool.noConfusion hlp

/-- **(←) AWAY FROM DERIVED NAMES THE LEAF-ROUTED CLOSURE LOSES NOTHING.** Two cases, and
    the second is the half a reader will not expect. On an UNTAINTED seed the plain closure
    is literally a subset (`rewriteClosure_subset_rewriteClosureL`, pure rule-set
    monotonicity). On a DERIVED seed it is NOT: `rawWriteTuples` re-addresses the write onto
    its storage leaves and the public-named seed `t` is simply gone. That case is not proved,
    it is EXCLUDED — a derived seed's whole closure is `{t}` (`mem_rewriteClosure_derived_self`)
    and `t`'s own relation is derived, so `hut` rules it out.

    ⚠ Which is exactly why `hut` cannot be dropped: `lrV_localisation_needs_notDerived`
    exhibits a directly-written derived relation whose post-flip closure is `[]`. -/
theorem mem_rewriteClosureL_of_mem_rewriteClosure_notDerived {S : Schema}
    (hnd : ∀ r ∈ schemaRewrites S, isDerived S (r.objectType, r.matchRel) = false)
    {t u : Tuple} (hu : u ∈ rewriteClosure S t)
    (hut : isDerived S (u.object.type, u.relation) = false) :
    u ∈ rewriteClosureL S (rawWriteTuples S t) := by
  by_cases hd : isDerived S (t.object.type, t.relation) = true
  · exfalso
    rw [mem_rewriteClosure_derived_self hnd hd hu, hd] at hut
    exact Bool.noConfusion hut
  · exact rewriteClosure_subset_rewriteClosureL
      (mem_rawWriteTuples_self (by simpa using hd)) hu

/-- **THE LOCALISATION.** On a tuple whose relation is neither a minted leaf name nor a
    derived relation of its own object type, the leaf-routed closure and today's closure
    agree on membership — for EVERY seed, tainted or not. The flip is invisible there. -/
theorem mem_rewriteClosureL_iff_notLeaf_notDerived {S : Schema}
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false)
    (hnd : ∀ r ∈ schemaRewrites S, isDerived S (r.objectType, r.matchRel) = false)
    {t u : Tuple} (hlp : isLeafPred u.relation = false)
    (hut : isDerived S (u.object.type, u.relation) = false) :
    u ∈ rewriteClosureL S (rawWriteTuples S t) ↔ u ∈ rewriteClosure S t :=
  ⟨fun h => mem_rewriteClosure_of_mem_rewriteClosureL_notLeaf hmd h hlp,
   fun h => mem_rewriteClosureL_of_mem_rewriteClosure_notDerived hnd h hut⟩

namespace LeafRuleWitness

/-! ### The localisation's three controls

Two guard-necessity refutations and one premise-non-vacuity witness. All three are
`by decide` at fixtures this file already owns, so none of them can rot into a claim about
a schema that no longer exists. -/

/-- **CONTROL 1 — `hlp` is load-bearing.** Drop the not-a-leaf-name guard from
    `mem_rewriteClosureL_iff_notLeaf_notDerived` and the `→` direction is FALSE: at `SlV`
    the `editor` write's leaf copy `doc:d1#viewer.0@user:alice` is in the leaf-routed
    closure and not in today's, and it SATISFIES `hut` (`isDerived SlV ("doc","viewer.0")`
    is `false`, because a minted leaf name is never a declared key — the very fact that
    makes the R3 guard `isDerived … = false` fail to fence the extras out). -/
theorem lrV_localisation_needs_notLeaf :
    (⟨⟨"user", "alice", BARE⟩, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩ : Tuple)
        ∈ rewriteClosureL SlV (rawWriteTuples SlV tlEditor)
      ∧ (⟨⟨"user", "alice", BARE⟩, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩ : Tuple)
        ∉ rewriteClosure SlV tlEditor
      ∧ isDerived SlV ("doc", leafPred "viewer" 0) = false := by decide

/-- **CONTROL 2 — `hut` is load-bearing, and the mechanism is the opposite one.** A DIRECT
    write of the derived public relation `viewer` on `SlV` re-addresses to NOTHING:
    `viewer := editor but not banned` has no direct arm, so it has no storage-bearing leaf,
    so `rawWriteRels` filter-maps to `[]` and the post-flip write materialises an EMPTY
    closure while today's write materialises the seed. Its relation is not a leaf name
    (`isLeafPred "viewer" = false`), so `hlp` alone does not exclude it.

    Measured 2026-09-05 by `#eval`, literal output:
    `rawWriteTuples SlV ⟨⟨"group","g1","member"⟩, "viewer", ⟨"doc","d1"⟩⟩` → `[]`;
    `rewriteClosure SlV` of the same tuple → the one-element list containing it.

    ⚠ Scope, stated so it is not over-read: such a tuple is NOT admitted —
    `CascadeStrata.lean::tvDer_not_storeValidD` proves `¬ StoreValidRulesD SlV [tvDer]`,
    because `StoreValidRulesD`'s derived arm demands a BARE subject. So this control
    establishes that `hut` is needed for the lemma AS STATED (which quantifies over all
    seeds, admitted or not); it does not by itself establish a live authorization gap. -/
theorem lrV_localisation_needs_notDerived :
    rawWriteTuples SlV ⟨⟨"group", "g1", "member"⟩, "viewer", ⟨"doc", "d1"⟩⟩ = []
      ∧ rewriteClosureL SlV
          (rawWriteTuples SlV ⟨⟨"group", "g1", "member"⟩, "viewer", ⟨"doc", "d1"⟩⟩) = []
      ∧ (⟨⟨"group", "g1", "member"⟩, "viewer", ⟨"doc", "d1"⟩⟩ : Tuple)
          ∈ rewriteClosure SlV ⟨⟨"group", "g1", "member"⟩, "viewer", ⟨"doc", "d1"⟩⟩
      ∧ isLeafPred "viewer" = false := by decide

/-- **CONTROL 3 — the premises are not vacuous, and neither is the conclusion.** `SlV` is a
    poor non-vacuity witness for `hmd`/`hnd`: `lrV_untainted_layer_silent` proves
    `schemaRewrites SlV = []`, so both premises hold for the empty reason. `SnlBoth` has a
    real untainted rewrite — measured 2026-09-05, literal `#eval` output:

    `schemaRewrites SnlBoth` → `[{objectType := "doc", matchRel := "parent",
    outRel := "editor", kind := RuleKind.ttu "viewer"}]`

    — and it FIRES: the plain closure of `doc:d1#parent@doc:d0#viewer` is two tuples
    (`parent`, then the rewritten `editor`), while the leaf-routed closure is three (those
    two plus the leaf `access.0`). So on this schema the localisation is contentful in both
    directions at once: it says the two closures agree at `parent` and at `editor`, and it
    says nothing at `access.0`, which is precisely where they differ. -/
theorem snlBoth_localisation_nonvacuous :
    (∀ r ∈ schemaRewrites SnlBoth, isLeafPred r.matchRel = false)
      ∧ (∀ r ∈ schemaRewrites SnlBoth, isDerived SnlBoth (r.objectType, r.matchRel) = false)
      ∧ schemaRewrites SnlBoth ≠ []
      ∧ rewriteClosure SnlBoth ⟨⟨"doc", "d0", "viewer"⟩, "parent", ⟨"doc", "d1"⟩⟩
          = [⟨⟨"doc", "d0", "viewer"⟩, "parent", ⟨"doc", "d1"⟩⟩,
             ⟨⟨"doc", "d0", "viewer"⟩, "editor", ⟨"doc", "d1"⟩⟩]
      ∧ rewriteClosureL SnlBoth
            (rawWriteTuples SnlBoth ⟨⟨"doc", "d0", "viewer"⟩, "parent", ⟨"doc", "d1"⟩⟩)
          = [⟨⟨"doc", "d0", "viewer"⟩, "parent", ⟨"doc", "d1"⟩⟩,
             ⟨⟨"doc", "d0", "viewer"⟩, "editor", ⟨"doc", "d1"⟩⟩,
             ⟨⟨"doc", "d0", "viewer"⟩, leafPred "access" 0, ⟨"doc", "d1"⟩⟩] := by decide

end LeafRuleWitness

end Zanzibar
