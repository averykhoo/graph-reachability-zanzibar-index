import ZanzibarProofs.GraphIndex.Leaf

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

Scope doc §11.6 (2026-08-15). The 76 edge rows projection P6 drops are mostly
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

/-! ## The leaf-routed rule write — the shape step 4c-ii re-points callers at -/

/-- **`RuleSet.apply` + per-triple `add_tuple`, both stages.** Stage 1 re-addresses the
    raw write onto its storage leaves (`rawWriteTuples`, the measured fan-out); stage 2
    closes the result under the full rule set including the leaf targets; each surviving
    triple is materialized by today's `writeDirect`.

    ⚠ **No caller yet.** Re-pointing `writeLoggedOne` / `removeLoggedOne` / `writeRules`
    at this, moving the `Delta` row to the leaf per branch (α), and threading
    `publicOfLeaf` into `affectedKeys`' own-key branch is step 4c-ii — which must
    co-land with step 7 (retire P6), because P6 is a Python-side-only filter. -/
def GraphState.writeRulesRaw (σ : GraphState) (S : Schema) (t : Tuple) : GraphState :=
  (rewriteClosureL S (rawWriteTuples S t)).foldl (fun acc u => acc.writeDirect u) σ

/-- **The subsumption theorem the leg's honesty rests on**: on a schema with no derived
    keys, the leaf-routed write IS today's rule-routed write. Not "we checked the tests
    still pass" — the two definitions are equal. -/
theorem writeRulesRaw_untaintedSchema {σ : GraphState} {S : Schema} {t : Tuple}
    (h : ∀ d ∈ S.defs, isDerived S d.1 = false) :
    σ.writeRulesRaw S t = σ.writeRules S t := by
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
  unfold GraphState.writeRulesRaw GraphState.writeRules
  rw [rawWriteTuples_untainted hd]
  unfold rewriteClosureL rewriteClosure
  rw [rewriteClosureRawL_singleton h]

/-! ## Invariant preservation — free, via `RulesWrite`'s list-generic fold family

The whole point of scope doc §11.1's "fork the TUPLE, not the write path": `writeDirect`
is byte-identical, so every `∀ (ts : List Tuple)` fold lemma applies to the leaf-routed
expansion verbatim, with no clone. -/

theorem structInv_writeRulesRaw {S S' : Schema} {σ : GraphState} (h : StructInv S' σ)
    (t : Tuple) : StructInv S' (σ.writeRulesRaw S t) :=
  structInv_foldl_writeDirect _ h

theorem residueEmpty_writeRulesRaw {S : Schema} {σ : GraphState} (t : Tuple)
    (h : ResidueEmpty σ) : ResidueEmpty (σ.writeRulesRaw S t) :=
  residueEmpty_foldl_writeDirect _ h

theorem inv_writeRulesRaw {S S' : Schema} {σ : GraphState} (h : Inv S' σ)
    (hre : ResidueEmpty σ) (t : Tuple) : Inv S' (σ.writeRulesRaw S t) :=
  inv_foldl_writeDirect _ h hre

theorem quiescent_writeRulesRaw {S : Schema} {σ : GraphState} (t : Tuple)
    (h : Quiescent σ) : Quiescent (σ.writeRulesRaw S t) :=
  quiescent_foldl_writeDirect _ h

theorem writeRulesRaw_schema (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.writeRulesRaw S t).schema = σ.schema :=
  schema_foldl_writeDirect _

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
    the `viewer.0` copy — the edge projection P6 drops today, and the reason leg 7
    exists. -/
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
    different edge lists. The `writeDirectRaw_edges_ne` analogue for 4c-i. -/
theorem lrV_writeRulesRaw_edges_ne :
    ((emptyState SlV).writeRulesRaw SlV tlEditor).edges
      ≠ ((emptyState SlV).writeRules SlV tlEditor).edges := by decide

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

end LeafRuleWitness

end Zanzibar
