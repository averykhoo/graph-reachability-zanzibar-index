import ZanzibarProofs.GraphIndex.RulesWrite
import ZanzibarProofs.GraphIndex.State

/-!
# The untainted rule-routing read correspondence (ROADMAP W2, read half — IN PROGRESS)

`SEMANTICS.md` §7.5. The W2 write half (`RulesWrite.lean`) materializes a raw write's
rewrite-closure as ordinary direct edges. This file builds the read correspondence
`check = sem` on the **untainted** fragment (`computed`/`union`/`ttu`, no `and`/`but
not`). This increment lands the **read-routing** reduction: on an untainted schema no
key is derived, so `GraphModel.check` routes to `probeNonDerived` (pure reachability) —
the same read path W1's `graph_correct_*` theorems glue against.

The remaining, genuinely-new content — `TupleChain over the rewrite-closure ↔ sem over
the raw store` (the rewrite-closure realizing `evalE`'s computed/ttu/union recursion) —
is the deferred next increment (see PROOF_STATUS "W2 STARTED").
-/

namespace Zanzibar

/-! ## The untainted fragment predicate -/

/-- **`UntaintedSchema S`** — no definition uses a boolean operator (`and`/`but not`),
    i.e. every def is built from `direct`/`computed`/`ttu`/`union`. This is exactly the
    W2 scope: on it, taint never propagates, so every relation is read via the
    reachability probes (never the residue path). -/
def UntaintedSchema (S : Schema) : Prop := ∀ p ∈ S.defs, containsBool p.2 = false

/-! ## Taint collapses on the untainted fragment -/

/-- On an untainted schema, no key is base-tainted (whatever the lookup outcome). -/
theorem baseTaint_untainted {S : Schema} (h : UntaintedSchema S) (k : Key) :
    baseTaint S k = false := by
  unfold baseTaint Schema.lookup
  cases hf : S.defs.find? (fun p => p.1 = k) with
  | none => rfl
  | some p =>
    simp only [Option.map_some]
    exact h p (List.mem_of_find?_eq_some hf)

/-- One taint round from `∅` stays `∅`: nothing is base-tainted and nothing references
    a currently-tainted key (there are none). -/
theorem taintStep_nil_untainted {S : Schema} (h : UntaintedSchema S) :
    taintStep S [] = [] := by
  unfold taintStep
  have hp : ∀ k, (baseTaint S k ||
      (refsOf S k).any (fun r => ([] : List Key).contains r)) = false := by
    intro k
    rw [baseTaint_untainted h k]
    simp
  simp only [hp, List.filter_false]

/-- Iterating a `[]`-fixed function from `[]` stays `[]`. -/
theorem iterate_nil_fixed {α : Type} (f : List α → List α) (hf : f [] = []) :
    ∀ n, iterate f n [] = [] := by
  intro n
  induction n with
  | zero => rfl
  | succ m ih =>
    show iterate f m (f []) = []
    rw [hf]; exact ih

/-- **The tainted set is empty on the untainted fragment.** -/
theorem taintedKeys_untainted {S : Schema} (h : UntaintedSchema S) :
    taintedKeys S = [] := by
  unfold taintedKeys
  exact iterate_nil_fixed (taintStep S) (taintStep_nil_untainted h) _

/-- **No key is derived on the untainted fragment.** -/
theorem isDerived_untainted {S : Schema} (h : UntaintedSchema S) (k : Key) :
    isDerived S k = false := by
  unfold isDerived
  rw [taintedKeys_untainted h]
  rfl

/-! ## The read routes to `probeNonDerived` -/

/-- **On the untainted fragment the graph read is pure reachability.** Since no key is
    derived, `check` never takes the residue path — it reduces to the ≤4-probe
    `probeNonDerived`, the same read `graph_correct_direct`/`_bareStar`/`_objStar`/
    `_usStar` glue against. This is the routing half of the W2 correspondence. -/
theorem check_eq_probeNonDerived {σ : GraphState} {S : Schema}
    (hsc : σ.schema = S) (h : UntaintedSchema S) (q : Query) :
    GraphModel.check σ q = GraphModel.probeNonDerived σ q := by
  unfold GraphModel.check
  rw [hsc, isDerived_untainted h]
  simp

/-! ## Soundness groundwork — edges trace back to rewrite-closure tuples

For the deferred reachability ⇒ `sem` half, the edge set must be pinned to the store's
rewrite-closure. `writeRules` folds `writeDirect` over `rewriteClosure S t`, so every
edge is either an old edge or the materialization of some closure tuple — the W2 analog
of `reachedByDirect_edge_sound`. Unconditional, reusable. -/

/-- Folding `writeDirect` over `us`: every resulting edge is an old edge of `σ` or the
    materialization `subjNode u.subject → objNode u.object u.relation` of some `u ∈ us`. -/
theorem foldl_writeDirect_edges_sound (us : List Tuple) :
    ∀ {σ : GraphState} {a b : NodeKey},
      (a, b) ∈ (us.foldl (fun acc u => acc.writeDirect u) σ).edges →
      (a, b) ∈ σ.edges ∨
        ∃ u ∈ us, a = subjNode u.subject ∧ b = objNode u.object u.relation := by
  induction us with
  | nil => intro σ a b hab; exact Or.inl hab
  | cons t rest ih =>
    intro σ a b hab
    -- (t :: rest).foldl f σ = rest.foldl f (σ.writeDirect t)
    rcases ih hab with hin | ⟨u, hu, h1, h2⟩
    · -- edge is in (σ.writeDirect t).edges: either old, or t's materialization
      rw [writeDirect_edges] at hin
      split at hin
      · rcases List.mem_cons.mp hin with heq | hmem
        · obtain ⟨e1, e2⟩ := Prod.ext_iff.mp heq
          exact Or.inr ⟨t, List.mem_cons_self, e1, e2⟩
        · exact Or.inl hmem
      · exact Or.inl hin
    · exact Or.inr ⟨u, List.mem_cons_of_mem _ hu, h1, h2⟩

/-- **Every edge of a W2-reached state materializes a rewrite-closure tuple.** By
    induction over the rule-routed write path: a fresh edge comes from some `u` in the
    rewrite-closure of the just-written `t`; an old edge is handled by the IH. The
    soundness-half groundwork for `graph_correct_rules` — a graph path is a chain of
    rewrite-closure materializations, which the `sem`-correspondence will match against
    `evalE`'s computed/ttu/union recursion. -/
theorem reachedByRules_edge_sound {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByRules σ S T) :
    ∀ a b, (a, b) ∈ σ.edges →
      ∃ t ∈ T, ∃ u ∈ rewriteClosure S t,
        a = subjNode u.subject ∧ b = objNode u.object u.relation := by
  induction h with
  | empty S => intro a b hab; simp [emptyState] at hab
  | @step σ S T t _hd ih =>
    intro a b hab
    -- σ.writeRules S t = (rewriteClosure S t).foldl writeDirect σ
    rcases foldl_writeDirect_edges_sound (rewriteClosure S t) hab with hin | ⟨u, hu, h1, h2⟩
    · obtain ⟨t', ht', u, hu, h1, h2⟩ := ih a b hin
      exact ⟨t', List.mem_cons_of_mem _ ht', u, hu, h1, h2⟩
    · exact ⟨t, List.mem_cons_self, u, hu, h1, h2⟩

/-! ## The storage-only tupleset fragment condition (attack-first finding)

**Attack-first (2026-07-10, machine-checked `#eval`, then deleted): the W2
`check = sem` correspondence is FALSE without a `_validate_ttu_tuplesets` side
condition.** Counterexample: schema `doc#viewer := ttu member parent`,
`doc#parent := computed linked`, `doc#linked := direct [group]`,
`group#member := direct [user]`; store `(group:g, linked, doc:d)`,
`(user:alice, member, group:g)`; query `check(alice, viewer, doc:d)`.

The graph rewrite-fanout of `(g, linked, d)` cascades `linked ↦ parent` (computed)
then fires the TTU rule on the *rewrite-produced* `(g, parent, d)`, materialising
`g#member → viewer(d)`, so `check = true`. But `sem`'s `ttuLeaf` reads only
**stored** `parent` tuples (there are none — `parent` is computed), so `sem = false`.
**Divergence.** With a directs-only `parent` (a raw stored tupleset) the two agree.

This is exactly what `zanzibar_utils_v1.py:_validate_ttu_tuplesets` rejects at
compile: an *untainted* tupleset relation with computed/rewritten arms. Note
`GraphAccepts` clause (3) does NOT catch it — a `computed`-armed tupleset is
untainted (`isDerived = false`), so it passes `GraphAccepts` yet must be excluded
here. The W2 fragment therefore carries `TtuTuplesetsDirect` below; the operational
payoff (`closure_tupleset_is_seed`) is that the graph only ever lands the *raw*
seed on a tupleset relation, so the deferred ttu correspondence reads raw tuplesets
exactly as `ttuLeaf` does. -/

/-- **`directsOnly e`** — every arm of `e` is a `Direct` leaf (a `Direct` or a
    `union` of directs-only). Faithful to `zanzibar_utils_v1.py:_directs_only`. A
    directs-only relation has no `computed`/`ttu` arm, so it is never a rewrite
    *output* (`exprArms_directsOnly`). -/
def directsOnly : Expr → Bool
  | .direct _  => true
  | .union a b => directsOnly a && directsOnly b
  | .computed _ => false
  | .ttu _ _   => false
  | .inter _ _ => false
  | .excl _ _  => false

/-- **`TtuTuplesetsDirect S`** — the untainted-fragment analog of
    `_validate_ttu_tuplesets` (`zanzibar_utils_v1.py:898`): every TTU's tupleset
    relation, *for every declared def carrying that key*, is directs-only. (Python
    keys a dict, so "every def with the key" = "the def"; stating it over all
    matching defs makes `no_rewrite_outputs_tupleset` need no separate key-uniqueness
    lemma, and is implied by the dict semantics.) This is the side condition that
    makes the W2 correspondence true — without it `check ≠ sem` (see the finding
    above). -/
def TtuTuplesetsDirect (S : Schema) : Prop :=
  ∀ d ∈ S.defs, ∀ tt ∈ exprTtus d.2,
    ∀ d' ∈ S.defs, d'.1 = (d.1.1, tt.2) → directsOnly d'.2 = true

/-! ### `exprArms` provenance -/

/-- A rewrite rule from `exprArms ot rel e` carries exactly `(objectType, outRel) =
    (ot, rel)` — the object type and relation of the def it was extracted from. -/
theorem exprArms_key {ot rel : String} :
    ∀ (e : Expr) {r : RRule}, r ∈ exprArms ot rel e →
      r.objectType = ot ∧ r.outRel = rel := by
  intro e
  induction e with
  | direct _ => intro r hr; simp [exprArms] at hr
  | computed _ => intro r hr; simp only [exprArms] at hr; obtain rfl := List.mem_singleton.mp hr; exact ⟨rfl, rfl⟩
  | ttu _ _ => intro r hr; simp only [exprArms] at hr; obtain rfl := List.mem_singleton.mp hr; exact ⟨rfl, rfl⟩
  | union a b iha ihb =>
    intro r hr
    simp only [exprArms, List.mem_append] at hr
    rcases hr with h | h
    · exact iha h
    · exact ihb h
  | inter _ _ _ _ => intro r hr; simp [exprArms] at hr
  | excl _ _ _ _ => intro r hr; simp [exprArms] at hr

/-- **A directs-only expr contributes no rewrite arms** — the core of the finding:
    a relation whose def is directs-only produces no `computed`/`ttu` rule, hence is
    never the output relation of any rewrite. -/
theorem exprArms_directsOnly (ot rel : String) :
    ∀ (e : Expr), directsOnly e = true → exprArms ot rel e = [] := by
  intro e
  induction e with
  | direct _ => intro _; rfl
  | computed _ => intro h; simp [directsOnly] at h
  | ttu _ _ => intro h; simp [directsOnly] at h
  | union a b iha ihb =>
    intro h
    simp only [directsOnly, Bool.and_eq_true] at h
    simp only [exprArms, iha h.1, ihb h.2, List.append_nil]
  | inter _ _ _ _ => intro h; simp [directsOnly] at h
  | excl _ _ _ _ => intro h; simp [directsOnly] at h

/-- Every schema rewrite rule comes from a declared def whose key is
    `(r.objectType, r.outRel)`. -/
theorem schemaRewrites_provenance {S : Schema} {r : RRule} (hr : r ∈ schemaRewrites S) :
    ∃ d ∈ S.defs, d.1 = (r.objectType, r.outRel) ∧ r ∈ exprArms d.1.1 d.1.2 d.2 := by
  unfold schemaRewrites at hr
  rw [List.mem_flatMap] at hr
  obtain ⟨d, hd, hrarm⟩ := hr
  obtain ⟨hoT, hoR⟩ := exprArms_key d.2 hrarm
  exact ⟨d, hd, by rw [hoT, hoR], hrarm⟩

/-- **No rewrite outputs a TTU's tupleset relation** (under the fragment condition).
    A rule with `objectType = ot` and `outRel = ts` would come from a def with key
    `(ot, ts)`, which `TtuTuplesetsDirect` forces directs-only — contributing no arms
    (`exprArms_directsOnly`), a contradiction. -/
theorem no_rewrite_outputs_tupleset {S : Schema} (h : TtuTuplesetsDirect S)
    {d : (String × String) × Expr} (hd : d ∈ S.defs) {tr ts : String}
    (htt : (tr, ts) ∈ exprTtus d.2) {r : RRule} (hr : r ∈ schemaRewrites S)
    (ho : r.objectType = d.1.1) (hout : r.outRel = ts) : False := by
  obtain ⟨d', hd', hkey, hrarm⟩ := schemaRewrites_provenance hr
  have hkey' : d'.1 = (d.1.1, ts) := by rw [hkey, ho, hout]
  have hdo := h d hd (tr, ts) htt d' hd' hkey'
  rw [exprArms_directsOnly _ _ _ hdo] at hrarm
  simp at hrarm

/-! ### Rewrite-closure structure: objects are preserved, outputs are `outRel`s -/

/-- `applyRRule` preserves the object (both branches keep `t.object`). -/
theorem applyRRule_object {r : RRule} {t u : Tuple} (h : applyRRule r t = some u) :
    u.object = t.object := by
  obtain ⟨ot, mr, or, kind⟩ := r
  unfold applyRRule at h
  split at h
  · cases kind with
    | computed => simp only [Option.some.injEq] at h; rw [← h]
    | ttu tr => simp only [Option.some.injEq] at h; rw [← h]
  · simp at h

/-- `applyRRule`'s output carries the rule's object type and output relation. -/
theorem applyRRule_outRel {r : RRule} {t u : Tuple} (h : applyRRule r t = some u) :
    u.object.type = r.objectType ∧ u.relation = r.outRel := by
  obtain ⟨ot, mr, or, kind⟩ := r
  unfold applyRRule at h
  split at h
  · rename_i hcond
    have hot : t.object.type = ot := hcond.2
    cases kind with
    | computed => simp only [Option.some.injEq] at h; rw [← h]; exact ⟨hot, rfl⟩
    | ttu tr => simp only [Option.some.injEq] at h; rw [← h]; exact ⟨hot, rfl⟩
  · simp at h

/-- One rewrite step preserves the object. -/
theorem rewriteStep_object {S : Schema} {t u : Tuple} (h : u ∈ rewriteStep S t) :
    u.object = t.object := by
  unfold rewriteStep at h
  obtain ⟨r, _, hap⟩ := List.mem_filterMap.mp h
  exact applyRRule_object hap

/-- One rewrite step's output relation is some schema rule's `outRel`, on the same
    object type. -/
theorem rewriteStep_outRel {S : Schema} {t u : Tuple} (h : u ∈ rewriteStep S t) :
    ∃ r ∈ schemaRewrites S, r.objectType = u.object.type ∧ r.outRel = u.relation := by
  unfold rewriteStep at h
  obtain ⟨r, hr, hap⟩ := List.mem_filterMap.mp h
  obtain ⟨ht, hrel⟩ := applyRRule_outRel hap
  exact ⟨r, hr, ht.symm, hrel.symm⟩

/-- Object preservation across the bounded closure: every closure tuple keeps the
    seed list's common object. -/
theorem rewriteClosureAux_object {S : Schema} {O : ObjectRef} :
    ∀ (n : Nat) (cur : List Tuple), (∀ w ∈ cur, w.object = O) →
      ∀ u ∈ rewriteClosureAux S n cur, u.object = O := by
  intro n
  induction n with
  | zero => intro cur hcur u hu; exact hcur u hu
  | succ m ih =>
    intro cur hcur u hu
    rw [rewriteClosureAux, List.mem_append] at hu
    rcases hu with hin | hrec
    · exact hcur u hin
    · refine ih _ ?_ u hrec
      intro w hw
      rw [List.mem_flatMap] at hw
      obtain ⟨x, hx, hwx⟩ := hw
      rw [rewriteStep_object hwx]; exact hcur x hx

/-- **Every rewrite-closure tuple has the same object as the raw write** — the
    rewrites only ever change `(subject, relation)`. -/
theorem rewriteClosure_object {S : Schema} {t u : Tuple} (h : u ∈ rewriteClosure S t) :
    u.object = t.object := by
  unfold rewriteClosure at h
  exact rewriteClosureAux_object _ _ (fun w hw => by rw [List.mem_singleton.mp hw]) _ h

/-- **The raw write is in its own rewrite-closure** (the closure seeds with `[t]`). -/
theorem rewriteClosure_seed (S : Schema) (t : Tuple) : t ∈ rewriteClosure S t := by
  unfold rewriteClosure
  rw [rewriteClosureAux]
  exact List.mem_append_left _ (List.mem_singleton.mpr rfl)

/-- Every tuple in `rewriteClosureAux` from a seed list is either in the seed list or
    is a rewrite output (relation = some rule's `outRel`, at its object type). -/
theorem rewriteClosureAux_produced {S : Schema} :
    ∀ (n : Nat) (cur : List Tuple) {u : Tuple}, u ∈ rewriteClosureAux S n cur →
      u ∈ cur ∨ ∃ r ∈ schemaRewrites S, r.objectType = u.object.type ∧ r.outRel = u.relation := by
  intro n
  induction n with
  | zero => intro cur u hu; exact Or.inl hu
  | succ m ih =>
    intro cur u hu
    rw [rewriteClosureAux, List.mem_append] at hu
    rcases hu with hin | hrec
    · exact Or.inl hin
    · rcases ih _ hrec with hcur | hout
      · -- u ∈ cur.flatMap (rewriteStep S): a fresh rewrite output
        rw [List.mem_flatMap] at hcur
        obtain ⟨x, _, hux⟩ := hcur
        exact Or.inr (rewriteStep_outRel hux)
      · exact Or.inr hout

/-- **Every closure tuple is the raw seed or a rewrite output.** -/
theorem rewriteClosure_produced {S : Schema} {t u : Tuple}
    (h : u ∈ rewriteClosure S t) :
    u = t ∨ ∃ r ∈ schemaRewrites S, r.objectType = u.object.type ∧ r.outRel = u.relation := by
  unfold rewriteClosure at h
  rcases rewriteClosureAux_produced _ _ h with hin | hout
  · exact Or.inl (List.mem_singleton.mp hin)
  · exact Or.inr hout

/-- **The operational payoff of the fragment condition: a closure tuple sitting on a
    TTU's tupleset relation is the raw seed.** Under `TtuTuplesetsDirect`, no rewrite
    outputs a tupleset relation (`no_rewrite_outputs_tupleset`), so a closure tuple
    with that relation and object type cannot be a rewrite output — it is `t` itself,
    a raw stored tuple. This is exactly the storage-only tupleset semantics
    (`ttuLeaf` reads raw stored tuplesets): the graph only ever lands the raw seed on
    a tupleset relation, so the deferred ttu correspondence stays sound. -/
theorem closure_tupleset_is_seed {S : Schema} (h : TtuTuplesetsDirect S)
    {d : (String × String) × Expr} (hd : d ∈ S.defs) {tr ts : String}
    (htt : (tr, ts) ∈ exprTtus d.2) {t u : Tuple} (hu : u ∈ rewriteClosure S t)
    (hrel : u.relation = ts) (hot : u.object.type = d.1.1) : u = t := by
  rcases rewriteClosure_produced hu with heq | ⟨r, hr, hro, hrout⟩
  · exact heq
  · exact absurd (no_rewrite_outputs_tupleset h hd htt hr (by rw [hro, hot]) (by rw [hrout, hrel]))
      (by simp)

end Zanzibar
