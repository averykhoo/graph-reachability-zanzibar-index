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

end LeafRuleWitness

end Zanzibar
