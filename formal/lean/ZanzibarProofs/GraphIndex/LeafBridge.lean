import ZanzibarProofs.GraphIndex.Exec

/-!
# `P4` — the leaf-probe ↔ `directLeaf` bridge, as a THEOREM

`docs/p4-leaf-probe-bridge-2026-09-23.md` § "What `P4` still owes". Until this file the
bridge was six `by decide` witness pins (`Exec.lean::P4Bridge`) at three fixed schemas.
This file states and proves it at every schema and store the headline theorems cover.

**What is bridged.** Python's compiled `check_fn` reads a boolean relation's `Direct`
arms off the index: `zanzibar_utils_v1.py::_compile_check_fn` compiles a `PClosureLeaf` to
`ctx.leaf_check(pred, s)`, and `index_v4/processor.py::_EvalContext.leaf_check` probes the
INDEX at the minted leaf name `<R>.<i>`. The spec reads the same arm off the STORE:
`Spec/Semantics.lean::directLeaf` at the public relation `R`. `leaf_probe_bridge` says the
two agree. The left side is the graph model's probe at the leaf node
(`GraphModel.probeNonDerived`, the read `leaf_check` reaches below the `BL-2` fence). The
right side is `directLeaf` over the leaf's MERGED restriction list. The theorem holds for
every `(i, rs)` in `Exec.lean::storageLeaves`, on every state the operational chain reaches
(`ReachedBy`), under the same two bundles as `graph_correct`.

**How the statement avoids the 2026-09-23 blocker.** `GraphAdmission.computedRefsNotLeaf`
refuses every schema whose `computed` operands name a leaf, so the bridge cannot be routed
through `evalE` (that would need `.computed "R.i"`). It is phrased off the probe and
`directLeaf` directly, with no `evalE`. That is the "cheap" option the map names.

**Why `rec` and `q` are universally quantified.** Under `W4Fragment.directArmsBare` +
`::directArmsConcrete` every restriction of a derived def's storage leaf is
`(type, BARE, false)` (`storageLeaf_restr_bare`). A matching grant therefore has a bare,
star-free subject, so `memberOfGranted` is `false` whatever `rec` is (`mog_false_of_bare`).
The right side does not depend on `rec` or `q`, and stating it for all of them is strictly
stronger than stating it at `graphRec σ s`.

**Why no `Drained` premise.** Storage leaves are written by the raw write leg alone
(`Leaf.lean::rawWriteTuples`), and the cascade only touches DERIVED public nodes
(`RemoveOccCount.lean::reachedByW3d2E_untOccCount`'s `cascade` arm). The leaf node is exact
after every write and every remove, before any drain.

**The proof is short because the invariant was already there.** R3
(`RemoveOccCount.lean::reachedByW3d2E_untOccCount`) pins every non-derived edge's ref-count
to the store's closure occurrences, AT LEAF TARGETS INCLUDED (R5 made that true). What is
new here is the count's content at a storage-leaf target: exactly the stored tuples the
leaf's restrictions admit (`mem_edges_storageLeaf_iff`). The key fact is that no rewrite
rule outputs into a storage leaf (`no_rule_targets_storageLeaf`): untainted rules target
declared names, and leaf rules target CLOSURE leaves, a different allocation index.

**What it does not cover — the `.userset` leaf kind.** `rawWriteRels` also routes a tainted
userset restriction to its own `.userset` leaf. Inside `W4Fragment` no such leaf exists
(`no_userset_leaf_in_fragment`): `directArmsBare` forbids the userset restriction that
would allocate one. So this theorem is silent on `.userset` leaves by SCOPE, not by
omission. A `.userset` bridge needs a fragment that admits userset arms, which
`W4Fragment` deliberately does not.
-/

namespace Zanzibar

namespace LeafBridge

/-! ## Name-level facts -/

/-- `toString` on `Nat` is injective, read off its character list via the core round-trip
    `Nat.ofDigitChars_ten_toDigits`. -/
theorem nat_eq_of_toString_toList {i j : Nat}
    (h : (toString i).toList = (toString j).toList) : i = j := by
  have hi : Nat.ofDigitChars 10 (toString i).toList 0 = i := by
    rw [Nat.toString_eq_ofList_toDigits, String.toList_ofList]
    exact Nat.ofDigitChars_ten_toDigits
  have hj : Nat.ofDigitChars 10 (toString j).toList 0 = j := by
    rw [Nat.toString_eq_ofList_toDigits, String.toList_ofList]
    exact Nat.ofDigitChars_ten_toDigits
  rw [← hi, ← hj, h]

/-- **Leaf names are injective on dot-free public names.** `leafPublic` recovers the public
    relation (`Leaf.lean::leafPublic_leafPred`), and the index is what follows the dot. -/
theorem leafPred_inj {R R' : String} {i j : Nat} (hR : relNameOK R) (hR' : relNameOK R')
    (h : leafPred R i = leafPred R' j) : R = R' ∧ i = j := by
  have hRR : R = R' := by
    rw [← leafPublic_leafPred R i hR, ← leafPublic_leafPred R' j hR', h]
  subst hRR
  refine ⟨rfl, nat_eq_of_toString_toList ?_⟩
  have hl := congrArg String.toList h
  simp only [leafPred, String.toList_append] at hl
  exact List.append_cancel_left hl

/-- A declared key's relation name is dot-free. -/
theorem relNameOK_of_lookup {S : Schema} (hWF : WF S) {k : String × String} {e : Expr}
    (h : S.lookup k = some e) : relNameOK k.2 :=
  hWF.relNames (k, e) (mem_defs_of_lookup h)

/-- A minted leaf name is never a derived relation: derived keys are declared, and declared
    names are dot-free. -/
theorem leafPred_not_derived {S : Schema} (hWF : WF S) (ty R : String) (i : Nat) :
    isDerived S (ty, leafPred R i) = false := by
  cases hd : isDerived S (ty, leafPred R i) with
  | false => rfl
  | true =>
    exact absurd rfl
      (leafPred_ne_relName (relNameOK_of_mem_keys hWF (mem_keys_of_isDerived hd)) R i)

/-! ## Node-level facts -/

theorem objNode_name (o : ObjectRef) (p : String) : (objNode o p).name = o.name := by
  unfold objNode; split <;> simp_all

/-- `objNode` is injective at EVERY object, star included (the existing
    `DirectCorrect.lean::objNode_inj` needs both names star-free). -/
theorem objNode_inj_any {a b : ObjectRef} {p q : String} (h : objNode a p = objNode b q) :
    a = b ∧ p = q := by
  have h1 : (objNode a p).type = (objNode b q).type := by rw [h]
  have h2 : (objNode a p).name = (objNode b q).name := by rw [h]
  have h3 : (objNode a p).pred = (objNode b q).pred := by rw [h]
  rw [objNode_type, objNode_type] at h1
  rw [objNode_name, objNode_name] at h2
  rw [objNode_pred, objNode_pred] at h3
  obtain ⟨at', an⟩ := a
  obtain ⟨bt, bn⟩ := b
  exact ⟨by simp_all, h3⟩

theorem objRef_eq {a b : ObjectRef} (h1 : a.type = b.type) (h2 : a.name = b.name) : a = b := by
  obtain ⟨at', an⟩ := a
  obtain ⟨bt, bn⟩ := b
  simp_all

/-- One edge is a path the executable probe finds. -/
theorem reach_of_edge {σ : GraphState} {u v : NodeKey} (h : (u, v) ∈ σ.edges) :
    σ.reach u v = true := by
  simp only [GraphState.reach, reachB, List.any_eq_true]
  exact ⟨(u, v), h, by simp⟩

/-! ## The allocation: where a storage leaf's restrictions come from -/

theorem mem_exprDirectsAll_of_mem_splitPure :
    ∀ (e : Expr) {r : Restriction}, r ∈ (splitPure e).1 → ∃ rs ∈ exprDirectsAll e, r ∈ rs := by
  intro e
  induction e with
  | direct rs0 =>
    intro r hr
    exact ⟨rs0, by simp [exprDirectsAll], by simpa [splitPure] using hr⟩
  | union a b iha ihb =>
    intro r hr
    simp only [splitPure, List.mem_append] at hr
    rcases hr with h | h
    · obtain ⟨rs, hrs, hr⟩ := iha h
      exact ⟨rs, by simp [exprDirectsAll, hrs], hr⟩
    · obtain ⟨rs, hrs, hr⟩ := ihb h
      exact ⟨rs, by simp [exprDirectsAll, hrs], hr⟩
  | computed _ => intro r hr; simp [splitPure] at hr
  | ttu _ _ => intro r hr; simp [splitPure] at hr
  | inter _ _ _ _ => intro r hr; simp [splitPure] at hr
  | excl _ _ _ _ => intro r hr; simp [splitPure] at hr

theorem storage_mem_pureLeaves {e : Expr} {rs : List Restriction}
    (h : PLeaf.storage rs ∈ pureLeaves e) : rs = (splitPure e).1 := by
  unfold pureLeaves at h
  simp only [List.mem_append] at h
  rcases h with h | h
  · split at h
    · simp at h
    · simpa using h
  · split at h <;> simp at h

/-- **Every restriction of a `.storage` leaf is one of the def's `Direct`-arm
    restrictions** — the merge (`pureLeaves`) and the impure filter only ever regroup arm
    restrictions, never invent one. Proved for `persistedLeaves` and `unionSpineLeaves`
    together, the shape of `CascadeStrataSettle.lean`'s `persistedLeaves_takes` (which is
    the converse direction). -/
theorem storage_restr_provenance {S : Schema} {ty : String} :
    ∀ (e : Expr),
      (∀ rs, PLeaf.storage rs ∈ persistedLeaves S ty e →
          ∀ r ∈ rs, ∃ rs' ∈ exprDirectsAll e, r ∈ rs') ∧
      (∀ rs, PLeaf.storage rs ∈ unionSpineLeaves S ty e →
          ∀ r ∈ rs, ∃ rs' ∈ exprDirectsAll e, r ∈ rs') := by
  intro e
  induction e with
  | direct rs0 =>
    have hatom : ∀ rs, PLeaf.storage rs ∈ atomLeaves S ty (.direct rs0) →
        ∀ r ∈ rs, ∃ rs' ∈ exprDirectsAll (.direct rs0), r ∈ rs' := by
      intro rs hrs r hr
      refine ⟨rs0, by simp [exprDirectsAll], ?_⟩
      rw [show atomLeaves S ty (.direct rs0)
          = (if isPure S ty (.direct rs0) then pureLeaves (.direct rs0)
             else ((if (rs0.filter (fun r => !isTaintedUserset S r)).isEmpty then []
                    else [PLeaf.storage (rs0.filter (fun r => !isTaintedUserset S r))])
                   ++ (rs0.filter (isTaintedUserset S)).map PLeaf.userset)) from rfl] at hrs
      split at hrs
      · have := storage_mem_pureLeaves hrs
        subst this
        simpa [splitPure] using hr
      · rcases List.mem_append.mp hrs with h | h
        · split at h
          · simp at h
          · simp only [List.mem_singleton, PLeaf.storage.injEq] at h
            subst h
            exact (List.mem_filter.mp hr).1
        · simp at h
    exact ⟨hatom, hatom⟩
  | computed R0 =>
    have hatom : ∀ rs, PLeaf.storage rs ∈ atomLeaves S ty (.computed R0) → False := by
      intro rs h
      simp only [atomLeaves] at h
      split at h <;> simp at h
    exact ⟨fun rs h => (hatom rs h).elim, fun rs h => (hatom rs h).elim⟩
  | ttu tgt ts =>
    have hatom : ∀ rs, PLeaf.storage rs ∈ atomLeaves S ty (.ttu tgt ts) → False := by
      intro rs h
      simp only [atomLeaves] at h
      split at h <;> simp at h
    exact ⟨fun rs h => (hatom rs h).elim, fun rs h => (hatom rs h).elim⟩
  | union a b iha ihb =>
    have hspine : ∀ rs, PLeaf.storage rs ∈ unionSpineLeaves S ty a ++ unionSpineLeaves S ty b →
        ∀ r ∈ rs, ∃ rs' ∈ exprDirectsAll (.union a b), r ∈ rs' := by
      intro rs h r hr
      rcases List.mem_append.mp h with h | h
      · obtain ⟨rs', h1, h2⟩ := iha.2 rs h r hr
        exact ⟨rs', by simp [exprDirectsAll, h1], h2⟩
      · obtain ⟨rs', h1, h2⟩ := ihb.2 rs h r hr
        exact ⟨rs', by simp [exprDirectsAll, h1], h2⟩
    refine ⟨?_, hspine⟩
    intro rs h r hr
    rw [show persistedLeaves S ty (.union a b)
        = (if isPure S ty (.union a b) then pureLeaves (.union a b)
           else unionSpineLeaves S ty a ++ unionSpineLeaves S ty b) from rfl] at h
    split at h
    · have := storage_mem_pureLeaves h
      subst this
      exact mem_exprDirectsAll_of_mem_splitPure _ hr
    · exact hspine rs h r hr
  | inter a b iha ihb =>
    have hb : ∀ rs, PLeaf.storage rs ∈ persistedLeaves S ty a ++ persistedLeaves S ty b →
        ∀ r ∈ rs, ∃ rs' ∈ exprDirectsAll (.inter a b), r ∈ rs' := by
      intro rs h r hr
      rcases List.mem_append.mp h with h | h
      · obtain ⟨rs', h1, h2⟩ := iha.1 rs h r hr
        exact ⟨rs', by simp [exprDirectsAll, h1], h2⟩
      · obtain ⟨rs', h1, h2⟩ := ihb.1 rs h r hr
        exact ⟨rs', by simp [exprDirectsAll, h1], h2⟩
    exact ⟨hb, hb⟩
  | excl a b iha ihb =>
    have hb : ∀ rs, PLeaf.storage rs ∈ persistedLeaves S ty a ++ persistedLeaves S ty b →
        ∀ r ∈ rs, ∃ rs' ∈ exprDirectsAll (.excl a b), r ∈ rs' := by
      intro rs h r hr
      rcases List.mem_append.mp h with h | h
      · obtain ⟨rs', h1, h2⟩ := iha.1 rs h r hr
        exact ⟨rs', by simp [exprDirectsAll, h1], h2⟩
      · obtain ⟨rs', h1, h2⟩ := ihb.1 rs h r hr
        exact ⟨rs', by simp [exprDirectsAll, h1], h2⟩
    exact ⟨hb, hb⟩

theorem bare_of_mem_exprDirectsAll :
    ∀ {e : Expr}, DirectArmsBare e → ∀ rs ∈ exprDirectsAll e, ∀ r ∈ rs, r.2.1 = BARE := by
  intro e
  induction e with
  | direct rs0 =>
    intro h rs hrs r hr
    simp only [exprDirectsAll, List.mem_singleton] at hrs
    subst hrs
    exact h r hr
  | computed _ => intro _ rs hrs; simp [exprDirectsAll] at hrs
  | ttu _ _ => intro _ rs hrs; simp [exprDirectsAll] at hrs
  | union a b iha ihb =>
    intro h rs hrs r hr
    simp only [exprDirectsAll, List.mem_append] at hrs
    rcases hrs with hh | hh
    · exact iha h.1 rs hh r hr
    · exact ihb h.2 rs hh r hr
  | inter a b iha ihb =>
    intro h rs hrs r hr
    simp only [exprDirectsAll, List.mem_append] at hrs
    rcases hrs with hh | hh
    · exact iha h.1 rs hh r hr
    · exact ihb h.2 rs hh r hr
  | excl a b iha ihb =>
    intro h rs hrs r hr
    simp only [exprDirectsAll, List.mem_append] at hrs
    rcases hrs with hh | hh
    · exact iha h.1 rs hh r hr
    · exact ihb h.2 rs hh r hr

/-! ## Rewrite rules never output into a storage leaf -/

/-- **No rule of the full leaf-routed rule set outputs into a storage leaf.** Untainted
    rules output declared, dot-free names (`not_isLeafPred_outRel_of_mem_schemaRewrites`).
    Leaf rules output `leafPred R' k` only for a `.closure` leaf at index `k`
    (`keyLeafRewrites`), and an allocation index holds exactly one leaf. -/
theorem no_rule_targets_storageLeaf {S : Schema} (hWF : WF S) (hNK : NodupKeys S)
    {ty R : String} {e : Expr} {i : Nat} {rs : List Restriction}
    (hlk : S.lookup (ty, R) = some e)
    (hi : (persistedLeaves S ty e)[i]? = some (PLeaf.storage rs))
    {r : RRule} (hr : r ∈ schemaRewritesL S) (hty : r.objectType = ty)
    (hout : r.outRel = leafPred R i) : False := by
  rcases List.mem_append.mp hr with hs | hl
  · have := not_isLeafPred_outRel_of_mem_schemaRewrites hWF hs
    rw [hout, isLeafPred_leafPred] at this
    exact Bool.noConfusion this
  · unfold leafRewrites at hl
    obtain ⟨⟨⟨dty, dR⟩, de⟩, hd, hk⟩ := List.mem_flatMap.mp hl
    have hdefs : ((dty, dR), de) ∈ S.defs := (List.mem_filter.mp hd).1
    unfold keyLeafRewrites at hk
    obtain ⟨⟨pl, k⟩, hpi, hpr⟩ := List.mem_flatMap.mp hk
    cases pl with
    | closure sub =>
      have hpr' : r ∈ exprArms dty (leafPred dR k) sub := hpr
      have h1 := outRel_mem_of_mem_exprArms hpr'
      have h2 := objectType_of_mem_exprArms hpr'
      rw [hout] at h1
      obtain ⟨hRR, hki⟩ :=
        leafPred_inj (relNameOK_of_lookup hWF hlk) (hWF.relNames _ hdefs) h1
      have hdty : dty = ty := h2.symm.trans hty
      subst hRR hki hdty
      have hde : de = e := by
        have := lookup_of_mem hNK hdefs
        rw [hlk] at this
        exact (Option.some.inj this).symm
      subst hde
      have hk2 := List.mem_zipIdx_iff_getElem?.mp hpi
      dsimp only at hk2
      rw [hi] at hk2
      simp at hk2
    | storage _ => simp at hpr
    | userset _ => simp at hpr

/-! ## The edge content at a storage-leaf target -/

theorem seed_mem_rewriteClosureL {S : Schema} {seeds : List Tuple} {u : Tuple}
    (h : u ∈ seeds) : u ∈ rewriteClosureL S seeds := by
  rw [mem_rewriteClosureL_iff]
  unfold rewriteClosureRawL
  simp only [rewriteClosureAuxL, List.mem_append]
  exact Or.inl h

/-- **A closure member landing on a storage-leaf node IS the routed raw write.** Its object
    and subject are the stored tuple's, the tuple is on the public relation `R`, and the
    leaf's restrictions admit it. -/
theorem storageLeaf_member {S : Schema} {T : Store} (hWF : WF S) (hNK : NodupKeys S)
    (hSV : StoreValidRulesD S T) {t : Tuple} (ht : t ∈ T)
    {ty R : String} {e : Expr} {i : Nat} {rs : List Restriction}
    (hlk : S.lookup (ty, R) = some e)
    (hi : (persistedLeaves S ty e)[i]? = some (PLeaf.storage rs))
    {u : Tuple} (hu : u ∈ rewriteClosureL S (rawWriteTuples S t))
    {O : ObjectRef} (hO : O.type = ty)
    (heq : objNode u.object u.relation = objNode O (leafPred R i)) :
    t.object = O ∧ t.relation = R ∧ restrictionMatches rs t = true ∧ u.subject = t.subject := by
  obtain ⟨huO, hurel⟩ := objNode_inj_any heq
  have hRok : relNameOK R := relNameOK_of_lookup hWF hlk
  rcases rewriteClosureL_produced hu with hseed | ⟨r, hr, hrty, hrout⟩
  · unfold rawWriteTuples at hseed
    obtain ⟨rel, hrel, rfl⟩ := List.mem_map.mp hseed
    dsimp only at huO hurel
    obtain ⟨e', hlk'⟩ : ∃ e', S.lookup (t.object.type, t.relation) = some e' := by
      rcases hSV t ht with ⟨_, e', _, h, _⟩ | ⟨_, _, e', _, h, _⟩ <;> exact ⟨e', h⟩
    have hTok : relNameOK t.relation := relNameOK_of_lookup hWF hlk'
    have htty : t.object.type = ty := by rw [huO, hO]
    by_cases hd : isDerived S (t.object.type, t.relation) = true
    · unfold rawWriteRels at hrel
      rw [if_pos hd, hlk'] at hrel
      obtain ⟨⟨pl, k⟩, hpi, hout⟩ := List.mem_filterMap.mp hrel
      have hk := List.mem_zipIdx_iff_getElem?.mp hpi
      dsimp only at hk
      -- every surviving entry names `leafPred t.relation k`; pin `t.relation = R`, `k = i`
      have hname : ∀ {x : String}, some (leafPred t.relation k) = some x → x = rel →
          t.relation = R ∧ k = i := by
        intro x hx hxr
        have : leafPred t.relation k = leafPred R i := by
          rw [Option.some.inj hx, hxr, hurel]
        exact leafPred_inj hTok hRok this
      have he' : ∀ {k' : Nat}, t.relation = R → k' = i →
          (persistedLeaves S t.object.type e')[k']? = (persistedLeaves S ty e)[i]? := by
        intro k' hRR hk'
        have hee : e' = e := by
          rw [htty, hRR, hlk] at hlk'
          exact (Option.some.inj hlk').symm
        rw [htty, hee, hk']
      cases pl with
      | storage rs' =>
        by_cases hm : restrictionMatches rs' t = true
        · simp only [hm, if_true] at hout
          obtain ⟨hRR, hki⟩ := hname hout rfl
          rw [he' hRR hki, hi] at hk
          simp only [Option.some.injEq, PLeaf.storage.injEq] at hk
          subst hk
          exact ⟨huO, hRR, hm, rfl⟩
        · simp [hm] at hout
      | userset r' =>
        by_cases hm : restrictionMatches [r'] t = true
        · simp only [hm, if_true] at hout
          obtain ⟨hRR, hki⟩ := hname hout rfl
          rw [he' hRR hki, hi] at hk
          simp at hk
        · simp [hm] at hout
      | closure _ => simp at hout
    · have hdf : isDerived S (t.object.type, t.relation) = false := by
        simpa using hd
      rw [rawWriteRels_untainted hdf, List.mem_singleton] at hrel
      subst hrel
      exact absurd hurel (leafPred_ne_relName hTok R i).symm
  · exfalso
    rw [hurel] at hrout
    rw [huO, hO] at hrty
    exact no_rule_targets_storageLeaf hWF hNK hlk hi hr hrty hrout

/-- **The edge content of a storage-leaf node, on every reached state.** An edge
    `a → objNode O (leafPred R i)` is present iff some stored tuple on `(O, R)`, admitted by
    leaf `i`'s merged restrictions, has subject node `a`. Any object `O` of the leaf's type,
    star objects included. -/
theorem mem_edges_storageLeaf_iff {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hNK : NodupKeys S) (hSV : StoreValidRulesD S T) (h : ReachedBy σ S T)
    {ty R : String} {e : Expr} {i : Nat} {rs : List Restriction}
    (hlk : S.lookup (ty, R) = some e)
    (hi : (persistedLeaves S ty e)[i]? = some (PLeaf.storage rs))
    (hd : isDerived S (ty, R) = true) {O : ObjectRef} (hO : O.type = ty) (a : NodeKey) :
    (a, objNode O (leafPred R i)) ∈ σ.edges ↔
      ∃ t ∈ T, t.object = O ∧ t.relation = R ∧ restrictionMatches rs t = true ∧
        a = subjNode t.subject := by
  have hcount := reachedByW3d2E_untOccCount h a (objNode O (leafPred R i))
    (by rw [objNode_type, objNode_pred]; exact leafPred_not_derived hWF _ R i)
    (objNode_ne_wAny _ _)
  rw [← List.count_pos_iff, hcount]
  unfold untOccCount
  rw [List.count_pos_iff, List.mem_map]
  constructor
  · rintro ⟨u, hu, hue⟩
    obtain ⟨t, ht, hut⟩ := List.mem_flatMap.mp hu
    unfold edgeOfTuple at hue
    obtain ⟨h1, h2⟩ := Prod.mk.inj hue
    obtain ⟨hto, htr, hm, hsub⟩ := storageLeaf_member hWF hNK hSV ht hlk hi hut hO h2
    exact ⟨t, ht, hto, htr, hm, by rw [← h1, hsub]⟩
  · rintro ⟨t, ht, hto, htr, hm, rfl⟩
    refine ⟨{ t with relation := leafPred R i },
      List.mem_flatMap.mpr ⟨t, ht, seed_mem_rewriteClosureL ?_⟩, ?_⟩
    · unfold rawWriteTuples
      refine List.mem_map.mpr ⟨leafPred R i, ?_, rfl⟩
      have hd' : isDerived S (t.object.type, t.relation) = true := by
        rw [hto, htr, hO]; exact hd
      have hlk' : S.lookup (t.object.type, t.relation) = some e := by
        rw [hto, htr, hO]; exact hlk
      unfold rawWriteRels
      rw [if_pos hd', hlk']
      refine List.mem_filterMap.mpr ⟨(PLeaf.storage rs, i), ?_, ?_⟩
      · exact List.mem_zipIdx_iff_getElem?.mpr (by rw [hto, hO]; exact hi)
      · simp [hm, htr]
    · simp [edgeOfTuple, hto]

/-! ## The spec side: a bare, star-free leaf reads the store alone -/

theorem mog_false_of_bare {rec : Rec} {T : Store} {q : Query} {grants : List Tuple}
    (h : ∀ g ∈ grants, g.subject.predicate = BARE) : memberOfGranted rec T q grants = false := by
  unfold memberOfGranted
  rw [List.any_eq_false]
  intro g hg
  rw [if_pos (by simpa using h g hg)]
  simp

/-- When every grant is bare and star-free, a positive `directLeaf` is a grant whose subject
    IS the query subject — no flow-through, no star branch. -/
theorem directLeaf_elim_bare {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {rs : List Restriction} {ot on rel : String}
    (hg : ∀ g ∈ grantsOf T rs ot on rel, g.subject.predicate = BARE ∧ g.subject.name ≠ STAR)
    (h : directLeaf rec s T q rs ot on rel = true) :
    ∃ g ∈ grantsOf T rs ot on rel, g.subject = s := by
  have hmog : memberOfGranted rec T q (grantsOf T rs ot on rel) = false :=
    mog_false_of_bare (fun g hg' => (hg g hg').1)
  unfold directLeaf at h
  by_cases h1 : (s.name == STAR) = true
  · rw [if_pos h1, hmog, Bool.or_false] at h
    obtain ⟨g, hg', hgt⟩ := List.any_eq_true.mp h
    simp only [Bool.and_eq_true, beq_iff_eq] at hgt
    exact absurd hgt.1.1 (hg g hg').2
  · rw [if_neg h1] at h
    by_cases h2 : (s.predicate == BARE) = true
    · rw [if_pos h2, hmog, Bool.or_false] at h
      obtain ⟨g, hg', hgt⟩ := List.any_eq_true.mp h
      obtain ⟨hgb, hgn⟩ := hg g hg'
      refine ⟨g, hg', ?_⟩
      have hsp : s.predicate = BARE := by simpa using h2
      obtain ⟨⟨gt, gn, gp⟩, grel, gobj⟩ := g
      obtain ⟨st, sn, sp⟩ := s
      simp only [Bool.or_eq_true, Bool.and_eq_true, bne_iff_ne, ne_eq, beq_iff_eq] at hgt
      simp only at hgb hgn hsp
      rcases hgt with ⟨⟨⟨_, _⟩, h3⟩, h4⟩ | ⟨⟨h5, _⟩, _⟩
      · simp_all
      · exact absurd h5 hgn
    · rw [if_neg h2, hmog, Bool.or_false] at h
      obtain ⟨g, hg', hgt⟩ := List.any_eq_true.mp h
      obtain ⟨hgb, _⟩ := hg g hg'
      simp only [Bool.or_eq_true, Bool.and_eq_true, bne_iff_ne, ne_eq, beq_iff_eq] at hgt
      rcases hgt with ⟨⟨⟨⟨_, h6⟩, _⟩, _⟩, _⟩ | ⟨⟨⟨_, h6⟩, _⟩, _⟩
      · exact absurd hgb h6
      · exact absurd hgb h6

end LeafBridge

open LeafBridge

/-- **In the fragment, a storage leaf's restrictions are bare and concrete.** Every one is
    a derived def's `Direct`-arm restriction (`storage_restr_provenance`), and
    `W4Fragment.directArmsBare` / `::directArmsConcrete` pin those. -/
theorem storageLeaf_restr_bare {S : Schema} {T : Store} (hF : W4Fragment S T)
    {ty R : String} {e : Expr} {rs : List Restriction}
    (hlk : S.lookup (ty, R) = some e) (hder : isDerived S (ty, R) = true)
    (hmem : PLeaf.storage rs ∈ persistedLeaves S ty e) :
    ∀ r ∈ rs, r.2.1 = BARE ∧ r.2.2 = false := by
  intro r hr
  obtain ⟨rs', hrs', hr'⟩ := (storage_restr_provenance e).1 rs hmem r hr
  exact ⟨bare_of_mem_exprDirectsAll (hF.directArmsBare _ _ e hlk hder) rs' hrs' r hr',
    hF.directArmsConcrete _ _ e hlk hder rs' hrs' r hr'⟩

/-- **Inside `W4Fragment` a derived def allocates no `.userset` leaf.** A `.userset` leaf
    is allocated only for a TAINTED userset restriction (`Leaf.lean::isTaintedUserset`,
    whose first conjunct is `r.2.1 != BARE`), and `directArmsBare` makes every derived
    `Direct`-arm restriction bare. This is why `leaf_probe_bridge` ranges over `.storage`
    leaves only: the `.userset` kind is outside the fragment, not skipped inside it. -/
theorem no_userset_leaf_in_fragment {S : Schema} {T : Store} (hF : W4Fragment S T)
    {ty R : String} {e : Expr} (hlk : S.lookup (ty, R) = some e)
    (hder : isDerived S (ty, R) = true) (r : Restriction) :
    PLeaf.userset r ∉ persistedLeaves S ty e := by
  have hbare := bare_of_mem_exprDirectsAll (hF.directArmsBare _ _ e hlk hder)
  suffices hgen : ∀ (x : Expr), (∀ rs ∈ exprDirectsAll x, ∀ r ∈ rs, r.2.1 = BARE) →
      PLeaf.userset r ∉ persistedLeaves S ty x ∧ PLeaf.userset r ∉ unionSpineLeaves S ty x from
    (hgen e hbare).1
  intro x
  induction x with
  | direct rs0 =>
    intro hb
    have hatom : PLeaf.userset r ∉ atomLeaves S ty (.direct rs0) := by
      intro h
      rw [show atomLeaves S ty (.direct rs0)
          = (if isPure S ty (.direct rs0) then pureLeaves (.direct rs0)
             else ((if (rs0.filter (fun r => !isTaintedUserset S r)).isEmpty then []
                    else [PLeaf.storage (rs0.filter (fun r => !isTaintedUserset S r))])
                   ++ (rs0.filter (isTaintedUserset S)).map PLeaf.userset)) from rfl] at h
      split at h
      · unfold pureLeaves at h
        simp only [List.mem_append] at h
        rcases h with h | h
        · split at h <;> simp at h
        · split at h <;> simp at h
      · rcases List.mem_append.mp h with h | h
        · split at h <;> simp at h
        · obtain ⟨r', hr', hrr⟩ := List.mem_map.mp h
          obtain ⟨hr0, htu⟩ := List.mem_filter.mp hr'
          have hb' : r'.2.1 = BARE := hb rs0 (by simp [exprDirectsAll]) r' hr0
          simp [isTaintedUserset, hb'] at htu
    exact ⟨hatom, hatom⟩
  | computed R0 =>
    intro _
    have hatom : PLeaf.userset r ∉ atomLeaves S ty (.computed R0) := by
      intro h; simp only [atomLeaves] at h; split at h <;> simp at h
    exact ⟨hatom, hatom⟩
  | ttu tgt ts =>
    intro _
    have hatom : PLeaf.userset r ∉ atomLeaves S ty (.ttu tgt ts) := by
      intro h; simp only [atomLeaves] at h; split at h <;> simp at h
    exact ⟨hatom, hatom⟩
  | union a b iha ihb =>
    intro hb
    have hba : ∀ rs ∈ exprDirectsAll a, ∀ r ∈ rs, r.2.1 = BARE :=
      fun rs h => hb rs (by simp [exprDirectsAll, h])
    have hbb : ∀ rs ∈ exprDirectsAll b, ∀ r ∈ rs, r.2.1 = BARE :=
      fun rs h => hb rs (by simp [exprDirectsAll, h])
    have hspine : PLeaf.userset r ∉ unionSpineLeaves S ty a ++ unionSpineLeaves S ty b := by
      intro h
      rcases List.mem_append.mp h with h | h
      · exact (iha hba).2 h
      · exact (ihb hbb).2 h
    refine ⟨?_, hspine⟩
    intro h
    rw [show persistedLeaves S ty (.union a b)
        = (if isPure S ty (.union a b) then pureLeaves (.union a b)
           else unionSpineLeaves S ty a ++ unionSpineLeaves S ty b) from rfl] at h
    split at h
    · unfold pureLeaves at h
      simp only [List.mem_append] at h
      rcases h with h | h
      · split at h <;> simp at h
      · split at h <;> simp at h
    · exact hspine h
  | inter a b iha ihb =>
    intro hb
    have hba : ∀ rs ∈ exprDirectsAll a, ∀ r ∈ rs, r.2.1 = BARE :=
      fun rs h => hb rs (by simp [exprDirectsAll, h])
    have hbb : ∀ rs ∈ exprDirectsAll b, ∀ r ∈ rs, r.2.1 = BARE :=
      fun rs h => hb rs (by simp [exprDirectsAll, h])
    have hboth : PLeaf.userset r ∉ persistedLeaves S ty a ++ persistedLeaves S ty b := by
      intro h
      rcases List.mem_append.mp h with h | h
      · exact (iha hba).1 h
      · exact (ihb hbb).1 h
    exact ⟨hboth, hboth⟩
  | excl a b iha ihb =>
    intro hb
    have hba : ∀ rs ∈ exprDirectsAll a, ∀ r ∈ rs, r.2.1 = BARE :=
      fun rs h => hb rs (by simp [exprDirectsAll, h])
    have hbb : ∀ rs ∈ exprDirectsAll b, ∀ r ∈ rs, r.2.1 = BARE :=
      fun rs h => hb rs (by simp [exprDirectsAll, h])
    have hboth : PLeaf.userset r ∉ persistedLeaves S ty a ++ persistedLeaves S ty b := by
      intro h
      rcases List.mem_append.mp h with h | h
      · exact (iha hba).1 h
      · exact (ihb hbb).1 h
    exact ⟨hboth, hboth⟩

/-- **★ `P4` — THE LEAF-PROBE BRIDGE (leg 7 step 4b), general form.**

    At every state the operational chain reaches, under the two headline bundles, the
    graph's probe at a storage leaf's minted node equals the spec's `directLeaf` over that
    leaf's merged restrictions, read at the PUBLIC relation. This holds for every subject
    (star and userset included), every `rec`, every `q`, and with no drain. This is the
    statement behind `zanzibar_utils_v1.py::_compile_check_fn`'s `PClosureLeaf` →
    `index_v4/processor.py::_EvalContext.leaf_check`, the clause `CORRESPONDENCE.md` §7.3
    used to record as netted by the differential matrix only.

    The `Exec.lean::P4Bridge` pins are its instances at three fixed schemas, and they stay:
    their two controls (`bridge_needs_the_leaf_name_*`, `bridge_is_per_leaf_SwF`) fix the
    argument pairing this theorem's statement fixes symbolically. `leafBridge_corpus`
    below is the instance on the headline's own corpus store, with both sides decided. -/
theorem leaf_probe_bridge {S : Schema} {T : Store} {σ : GraphState}
    (hA : GraphAdmission S T) (hF : W4Fragment S T) (h : ReachedBy σ S T)
    {o : ObjectRef} {R : String} {i : Nat} {rs : List Restriction}
    (hder : isDerived S (o.type, R) = true)
    (hleaf : (i, rs) ∈ storageLeaves S o.type R)
    (hqo : o.name ≠ STAR) (s : SubjectRef) (rec : Rec) (q : Query) :
    GraphModel.probeNonDerived σ ⟨s, leafPred R i, o⟩
      = directLeaf rec s T q rs o.type o.name R := by
  -- the leaf, as an allocation position
  obtain ⟨e, hlk, hi⟩ : ∃ e, S.lookup (o.type, R) = some e ∧
      (persistedLeaves S o.type e)[i]? = some (PLeaf.storage rs) := by
    unfold storageLeaves at hleaf
    cases hl : S.lookup (o.type, R) with
    | none => rw [hl] at hleaf; simp at hleaf
    | some e =>
      rw [hl] at hleaf
      obtain ⟨⟨pl, k⟩, hpi, hout⟩ := List.mem_filterMap.mp hleaf
      cases pl with
      | storage rs' =>
        simp only [Option.some.injEq, Prod.mk.injEq] at hout
        obtain ⟨rfl, rfl⟩ := hout
        exact ⟨e, rfl, List.mem_zipIdx_iff_getElem?.mp hpi⟩
      | closure _ => simp at hout
      | userset _ => simp at hout
  have hrsB := storageLeaf_restr_bare hF hlk hder (List.mem_of_getElem? hi)
  -- an admitted grant has a bare, star-free subject
  have hgrant : ∀ t : Tuple, restrictionMatches rs t = true →
      t.subject.predicate = BARE ∧ t.subject.name ≠ STAR := by
    intro t hm
    unfold restrictionMatches at hm
    obtain ⟨r, hr, hp⟩ := List.any_eq_true.mp hm
    obtain ⟨hb, hc⟩ := hrsB r hr
    obtain ⟨rt, rp, rw'⟩ := r
    simp only at hb hc
    subst hb hc
    simp only [Bool.and_eq_true, beq_iff_eq] at hp
    refine ⟨hp.1.2, ?_⟩
    have h3 := hp.2
    intro hs
    rw [hs] at h3
    simp at h3
  have hedge := fun (O : ObjectRef) (hO : O.type = o.type) (a : NodeKey) =>
    mem_edges_storageLeaf_iff hA.wf hA.nodup hA.storeValid h hlk hi hder hO a
  -- a bare-predicate node has no in-edge (the chain's structural fact)
  have hW3d2 : ReachedByW3d2 σ S T :=
    reachedByW3d2C_toW3d2 (reachedByW3d2E_toC_d h hA.wf hA.ttuDirect hA.nodup hA.ranked
      hA.matchDecl hA.strat hA.ttuNotLeaf hA.directRestrNotLeaf hA.leafScope
      hA.computedRefsNotLeaf hA.noBridgedDerived hF.computedOrDirect hF.directArmsBare
      hF.directArmsConcrete hF.computedOnlyOperands hF.twoStrata hF.wsBare hA.storeValid
      hF.bareStar hF.ttuStarFree hF.term)
  have hnoin : ∀ {k : NodeKey}, k.pred = BARE → ∀ x, (x, k) ∉ σ.edges :=
    fun hk => reachedByW3d2_bareNode_no_inedge_d hA.wf hF.directArmsBare hA.storeValid hW3d2 hk
  -- so every path into a storage-leaf node is ONE edge
  have hone : ∀ O : ObjectRef, O.type = o.type → ∀ x,
      NReaches σ.edges x (objNode O (leafPred R i)) → (x, objNode O (leafPred R i)) ∈ σ.edges := by
    intro O hO x hr
    generalize hv : objNode O (leafPred R i) = v at hr
    induction hr with
    | edge hxv => exact hxv
    | @head _ w _ hxw _ ih =>
      exfalso
      have hwv : (w, objNode O (leafPred R i)) ∈ σ.edges := by rw [hv]; exact ih hv
      obtain ⟨t, _, _, _, hm, hw⟩ := (hedge O hO _).mp hwv
      exact hnoin (by rw [hw, subjNode_pred]; exact (hgrant t hm).1) _ hxw
  have hpull : ∀ O : ObjectRef, O.type = o.type → ∀ x,
      σ.reach x (objNode O (leafPred R i)) = true →
      ∃ t ∈ T, t.object = O ∧ t.relation = R ∧ restrictionMatches rs t = true ∧
        x = subjNode t.subject :=
    fun O hO x hx => (hedge O hO x).mp (hone O hO x (reach_sound hx))
  have hwall : wAllNode o.type (leafPred R i) = objNode ⟨o.type, STAR⟩ (leafPred R i) := by
    simp [objNode, wAllNode]
  -- a grant subject's node is plain, so no `wAny` probe source can be one
  have hnotwany : ∀ t : Tuple, restrictionMatches rs t = true → ∀ sh : Shape,
      wAnyNode sh ≠ subjNode t.subject := by
    intro t hm sh hx
    have hv := congrArg NodeKey.variant hx
    rw [subjNode_plain (hgrant t hm).2] at hv
    simp [wAnyNode] at hv
  have hrhs : ∀ t ∈ T, t.relation = R → t.object.type = o.type →
      (matchingObjects o.name).contains t.object.name = true →
      restrictionMatches rs t = true → subjNode s = subjNode t.subject →
      directLeaf rec s T q rs o.type o.name R = true := by
    intro t ht htr hty hobj hm hx
    have hns := (hgrant t hm).2
    have hsn : s.name ≠ STAR := by
      intro hs
      have hv := congrArg NodeKey.variant hx
      rw [subjNode_plain hns] at hv
      simp [subjNode, hs] at hv
    exact directLeaf_grant_self (grantsOf_intro ht htr hty hobj hm)
      (subjNode_inj hns hsn hx.symm) hsn
  apply Bool.eq_iff_iff.mpr
  constructor
  · intro hl
    unfold GraphModel.probeNonDerived at hl
    simp only [Bool.or_eq_true, Bool.and_eq_true, bne_iff_ne, ne_eq] at hl
    rcases hl with ((h1 | ⟨_, h2⟩) | ⟨_, h3⟩) | ⟨_, h4⟩
    · obtain ⟨t, ht, hto, htr, hm, hx⟩ := hpull o rfl _ h1
      exact hrhs t ht htr (by rw [hto]) (by rw [hto]; simp [matchingObjects, hqo]) hm hx
    · obtain ⟨t, _, _, _, hm, hx⟩ := hpull o rfl _ h2
      exact absurd hx (hnotwany t hm _)
    · rw [hwall] at h3
      obtain ⟨t, ht, hto, htr, hm, hx⟩ := hpull ⟨o.type, STAR⟩ rfl _ h3
      exact hrhs t ht htr (by rw [hto]) (by rw [hto]; simp [matchingObjects, hqo]) hm hx
    · rw [hwall] at h4
      obtain ⟨t, _, _, _, hm, hx⟩ := hpull ⟨o.type, STAR⟩ rfl _ h4
      exact absurd hx (hnotwany t hm _)
  · intro hr
    have hgr : ∀ g ∈ grantsOf T rs o.type o.name R,
        g.subject.predicate = BARE ∧ g.subject.name ≠ STAR :=
      fun g hg => hgrant g (grantsOf_elim hg).2.2.2.2
    obtain ⟨g, hg, hgs⟩ := directLeaf_elim_bare hgr hr
    obtain ⟨hgT, hgrel, hgty, hgobj, hgm⟩ := grantsOf_elim hg
    simp [matchingObjects, hqo] at hgobj
    unfold GraphModel.probeNonDerived
    simp only [Bool.or_eq_true, Bool.and_eq_true, bne_iff_ne, ne_eq]
    rcases hgobj with hon | hstar
    · have hgo : g.object = o := objRef_eq hgty hon
      have he : (subjNode s, objNode o (leafPred R i)) ∈ σ.edges :=
        (hedge o rfl _).mpr ⟨g, hgT, hgo, hgrel, hgm, by rw [hgs]⟩
      exact Or.inl (Or.inl (Or.inl (reach_of_edge he)))
    · have hgo : g.object = ⟨o.type, STAR⟩ := objRef_eq hgty hstar
      have he : (subjNode s, objNode ⟨o.type, STAR⟩ (leafPred R i)) ∈ σ.edges :=
        (hedge ⟨o.type, STAR⟩ rfl _).mpr ⟨g, hgT, hgo, hgrel, hgm, by rw [hgs]⟩
      rw [← hwall] at he
      exact Or.inl (Or.inr ⟨hqo, reach_of_edge he⟩)

/-! ## Instances at the headline's own corpus store -/

namespace LeafBridgeWitness

open W4WitnessDirect

/-- `Sd`'s one storage leaf: `approver := [user] but not banned` allocates the `Direct`
    arm at index 0. -/
theorem sd_storageLeaves :
    storageLeaves Sd "doc" "approver" = [(0, [("user", BARE, false)])] := by decide

/-- **The general theorem APPLIES at `Sd`/`Td4`** — the four-tuple conformance store the
    headline witnesses `final_applies4` / `reached_inv_applies4` run at. Same bundles, every
    reached state, every subject. A theorem whose premises could not be met at a concrete
    store would still compile; this declaration is the check that they can. -/
theorem leafBridge_applies4 {σ : GraphState} (h : ReachedBy σ Sd Td4) (s : SubjectRef)
    (rec : Rec) (q : Query) :
    GraphModel.probeNonDerived σ ⟨s, leafPred "approver" 0, ⟨"doc", "d1"⟩⟩
      = directLeaf rec s Td4 q [("user", BARE, false)] "doc" "d1" "approver" :=
  leaf_probe_bridge admission4 w4fragment4 h (by decide)
    (by rw [sd_storageLeaves]; simp) (by decide) s rec q

def alice : SubjectRef := ⟨"user", "alice", BARE⟩
def bob : SubjectRef := ⟨"user", "bob", BARE⟩
def carol : SubjectRef := ⟨"user", "carol", BARE⟩
def d1 : ObjectRef := ⟨"doc", "d1"⟩

set_option maxHeartbeats 4000000 in
/-- **CONTENT, at a driver-built state: the leaf is the ARM, not the relation.** Replay
    `Td4` through the op driver. At the leaf node `approver.0`, alice and bob are granted
    and carol is not, which is exactly what the `[user]` arm stores. The PUBLIC derived
    relation denies bob, because bob is banned: both the raw probe at the public name
    (fifth component) and the fenced public read (sixth) say `false`. So at bob the leaf
    probe and the public node DISAGREE, and the theorem's agreement is with `directLeaf`
    (the arm), not with `sem` at `approver`.

    The fifth component is the kernel refutation of the plausible mis-statement "probe at
    the public name `R`": `leafBridge_corpus_spec` decides `directLeaf … bob … = true`, so
    that form is FALSE at this reached state. Sabotage S-M2 (2026-10-03) made exactly that
    edit to `leaf_probe_bridge`'s statement. It went red only inside the proof, and Lean
    error-recovers a failed declaration at its stated type, so a downstream use cannot see
    the edit. That is why the evidence is decided here off the primitives, not routed
    through the theorem, and why the statement is byte-pinned in
    `formal/headline_statements.txt`. The `true`s also rule out agreement by universal
    denial. -/
theorem leafBridge_corpus :
    ((graphRunOps Sd (Td4.reverse.map GraphOp.add)).map fun p =>
        (p.2,
         GraphModel.probeNonDerived p.1 ⟨alice, leafPred "approver" 0, d1⟩,
         GraphModel.probeNonDerived p.1 ⟨bob, leafPred "approver" 0, d1⟩,
         GraphModel.probeNonDerived p.1 ⟨carol, leafPred "approver" 0, d1⟩,
         GraphModel.probeNonDerived p.1 ⟨bob, "approver", d1⟩,
         GraphModel.checkPublic p.1 ⟨bob, "approver", d1⟩))
      = some (Td4, true, true, false, false, false) := by
  decide

/-- The spec side of the same three rows, decided directly: `directLeaf` over the leaf's
    restrictions at the public relation says alice yes, bob yes, carol no. Read with
    `leafBridge_corpus`, this is the theorem's conclusion checked row by row. -/
theorem leafBridge_corpus_spec (rec : Rec) (q : Query) :
    (directLeaf rec alice Td4 q [("user", BARE, false)] "doc" "d1" "approver",
     directLeaf rec bob Td4 q [("user", BARE, false)] "doc" "d1" "approver",
     directLeaf rec carol Td4 q [("user", BARE, false)] "doc" "d1" "approver")
      = (true, true, false) := by
  simp [directLeaf, grantsOf, memberOfGranted, restrictionMatches, matchingObjects, Td4,
    alice, bob, carol, BARE, STAR]

end LeafBridgeWitness

end Zanzibar
