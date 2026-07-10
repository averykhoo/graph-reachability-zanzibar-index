import ZanzibarProofs.GraphIndex.RulesSound

/-!
# The untainted userset lift + chain composition (ROADMAP W2, soundness half cont.)

`RulesSound.lean` proved the per-hop content (`semAux_of_rewriteClosure`: a rewrite-
closure tuple is a `sem` membership). To turn a *graph path* — a chain of such
materialised tuples — into one `sem` membership, consecutive hops must compose through
their shared userset node. That is the **userset lift**: `s ∈ s'` and `s' ∈ v` ⇒
`s ∈ v`.

DirectCorrect's `semAux_lift` proves exactly this, but only on a `PureDirect` schema
(it unfolds each node's def as a `Direct` leaf). W2 needs it on an `UntaintedSchema`,
where a node the userset flows through may be `computed`/`ttu`/`union`. This file
generalises the lift: a nested induction (fuel outside, `Expr` inside) whose leaf cases
are the `direct` logic (reused from DirectCorrect), the `computed` indirection (the
fuel IH at the sub-node), and the `ttu` stored-parent loop (`ttuLeaf_elim`/`_intro_rec`;
the star branch is dead on star-free data).
-/

namespace Zanzibar

/-! ## `ttuLeaf` elimination / introduction (star-free store)

On star-free data every tupleset tuple has a non-`*` subject, so `ttuLeaf`'s star
branch (`instances`) is dead and a positive answer exhibits a stored tupleset tuple
whose parent userset the subject either *is* (direct disjunct) or *is a member of*
(the `rec` disjunct). -/

/-- A positive `ttuLeaf` on star-free data exhibits its stored tupleset tuple and the
    parent-match / parent-membership disjunction. -/
theorem ttuLeaf_elim {rec : Rec} {s' : SubjectRef} {T : Store} {q : Query}
    {tr ts ot on : String} (hSF : StarFreeStore T)
    (h : ttuLeaf rec s' T q tr ts ot on = true) :
    ∃ tup ∈ T, tup.relation = ts ∧ tup.object.type = ot ∧
      (matchingObjects on).contains tup.object.name = true ∧
      ((s'.type = tup.subject.type ∧ s'.name = tup.subject.name ∧ s'.predicate = tr)
        ∨ rec tup.subject.type tup.subject.name tr = true) := by
  unfold ttuLeaf at h
  simp only at h
  obtain ⟨tup, htup, hbody⟩ := List.any_eq_true.mp h
  by_cases hcond : (tup.relation == ts && tup.object.type == ot &&
      (matchingObjects on).contains tup.object.name) = true
  · rw [if_pos hcond] at hbody
    have hpn : (tup.subject.name != STAR) = true := by
      simp only [bne_iff_ne]; exact (hSF tup htup).1
    rw [if_pos hpn] at hbody
    simp only [Bool.and_eq_true, beq_iff_eq] at hcond
    simp only [Bool.or_eq_true, Bool.and_eq_true, beq_iff_eq] at hbody
    refine ⟨tup, htup, hcond.1.1, hcond.1.2, hcond.2, ?_⟩
    rcases hbody with ⟨⟨h1, h2⟩, h3⟩ | hrec
    · exact Or.inl ⟨h1, h2, h3⟩
    · exact Or.inr hrec
  · rw [if_neg hcond] at hbody; simp at hbody

/-- `ttuLeaf` fires (for any subject) via the `rec` disjunct on a stored tupleset tuple
    whose parent userset `rec` answers positively. -/
theorem ttuLeaf_intro_rec {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {tr ts ot on : String} {tup : Tuple} (htup : tup ∈ T)
    (hrel : tup.relation = ts) (hot : tup.object.type = ot)
    (hcon : (matchingObjects on).contains tup.object.name = true)
    (hpn : tup.subject.name ≠ STAR)
    (hrec : rec tup.subject.type tup.subject.name tr = true) :
    ttuLeaf rec s T q tr ts ot on = true := by
  unfold ttuLeaf
  refine List.any_eq_true.mpr ⟨tup, htup, ?_⟩
  have hc : (tup.relation == ts && tup.object.type == ot &&
      (matchingObjects on).contains tup.object.name) = true := by
    rw [hrel, hot]; simpa using hcon
  rw [if_pos hc, if_pos (by simpa using hpn)]
  simp [hrec]

/-! ## The generalised userset lift

`s ∈ s'` and `s' ∈ v` ⇒ `s ∈ v`, on an `UntaintedSchema`. The inner `evalE`-level lift
handles each node the userset flows through: `direct` (the DirectCorrect logic — a
direct match of `s'` at a grant is absorbed by `s`'s flow-through on the same grant, a
flow-through by the fuel IH), `computed` (the fuel IH at the sub-node), `ttu` (the
stored-parent loop — a direct parent-match becomes `hmem`, a parent-membership the fuel
IH), and `union` (the OR). -/

/-- The looked-up def of an untainted schema is boolean-free. -/
theorem containsBool_lookup {S : Schema} (h : UntaintedSchema S) {k : Key} {e : Expr}
    (hlk : S.lookup k = some e) : containsBool e = false := by
  unfold Schema.lookup at hlk
  cases hf : S.defs.find? (fun p => p.1 = k) with
  | none => rw [hf] at hlk; simp at hlk
  | some p =>
    rw [hf] at hlk
    simp only [Option.map_some, Option.some.injEq] at hlk
    subst hlk
    exact h p (List.mem_of_find?_eq_some hf)

/-- **The `evalE`-level lift** — one `evalE` over an untainted expr propagates a userset
    membership from `s'` to `s`, given `s ∈ s'` (`hmem`) and the fuel IH (`ih`). -/
theorem evalE_lift {S : Schema} {T : Store} {q : Query} {s s' : SubjectRef}
    (hNE : S.noExclAll) (hSF : StarFreeStore T)
    (hs'n : s'.name ≠ STAR) (hs'p : s'.predicate ≠ BARE) {f f₀ : Nat}
    (hmem : semAux S s T q f₀ s'.type s'.name s'.predicate = true)
    (ih : ∀ ot on r, semAux S s' T q f ot on r = true →
      semAux S s T q (f + f₀) ot on r = true) :
    ∀ e, containsBool e = false → ∀ ot on r,
      evalE (semAux S s' T q f) s' T q ot on r e = true →
      evalE (semAux S s T q (f + f₀)) s T q ot on r e = true := by
  intro e
  induction e with
  | direct rs =>
    intro _ ot on r h
    rcases directLeaf_elim hSF hs'n h with ⟨g, hg, hgs⟩ | hmog
    · apply directLeaf_of_mog
      refine mog_intro hg (by rw [hgs]; exact hs'p) (by rw [hgs]; exact hs'n) ?_
      rw [hgs]
      exact semAux_mono S hNE s T q (Nat.le_add_left f₀ f) _ _ _ hmem
    · obtain ⟨g, hg, hpb, hps, hrec⟩ := mog_elim hSF hmog
      exact directLeaf_of_mog (mog_intro hg hpb hps (ih _ _ _ hrec))
  | computed r' =>
    intro _ ot on r h
    exact ih ot on r' h
  | ttu tr' ts' =>
    intro _ ot on r h
    obtain ⟨tup, htup, hrel, hot, hcon, hdisj⟩ := ttuLeaf_elim hSF h
    refine ttuLeaf_intro_rec htup hrel hot hcon (hSF tup htup).1 ?_
    rcases hdisj with ⟨he1, he2, he3⟩ | hrec
    · rw [← he1, ← he2, ← he3]
      exact semAux_mono S hNE s T q (Nat.le_add_left f₀ f) _ _ _ hmem
    · exact ih tup.subject.type tup.subject.name tr' hrec
  | union a b iha ihb =>
    intro hcb ot on r h
    simp only [containsBool, Bool.or_eq_false_iff] at hcb
    simp only [evalE, Bool.or_eq_true] at h ⊢
    rcases h with ha | hb
    · exact Or.inl (iha hcb.1 ot on r ha)
    · exact Or.inr (ihb hcb.2 ot on r hb)
  | inter _ _ _ _ => intro hcb; simp [containsBool] at hcb
  | excl _ _ _ _ => intro hcb; simp [containsBool] at hcb

/-- **The userset lift on an untainted schema** (W2 generalisation of DirectCorrect's
    `semAux_lift`): if `s` is a member of the userset `s'` at fuel `f₀` and `s'` is a
    member of node `(ot, on, r)` at fuel `f`, then `s` is a member of that node at fuel
    `f + f₀`. By fuel induction, each step discharged by `evalE_lift`. -/
theorem semAux_lift_untainted {S : Schema} {T : Store} {q : Query} {s s' : SubjectRef}
    (hUT : UntaintedSchema S) (hSF : StarFreeStore T)
    (hs'n : s'.name ≠ STAR) (hs'p : s'.predicate ≠ BARE)
    {f₀ : Nat} (hmem : semAux S s T q f₀ s'.type s'.name s'.predicate = true) :
    ∀ (f : Nat) (ot on r : String),
      semAux S s' T q f ot on r = true →
      semAux S s T q (f + f₀) ot on r = true := by
  intro f
  induction f with
  | zero => intro ot on r h; simp [semAux] at h
  | succ f ih =>
    intro ot on r h
    rw [show f + 1 + f₀ = (f + f₀) + 1 from by omega, semAux, step]
    rw [semAux, step] at h
    cases hlk : S.lookup (ot, r) with
    | none => rw [hlk] at h; simp at h
    | some e =>
      rw [hlk] at h
      show evalE (semAux S s T q (f + f₀)) s T q ot on r e = true
      exact evalE_lift (untainted_noExclAll hUT) hSF hs'n hs'p hmem ih e
        (containsBool_lookup hUT hlk) ot on r h

/-! ## Rewrite-closure preserves subject name; its relations are declared

The chain composition threads each hop's *userset* intermediate `⟨w.object.type,
w.object.name, w.relation⟩` — so a closure tuple's object must be star-free (already:
`rewriteClosure_object`), its subject name star-free (rewrites keep the subject name),
and its relation non-`BARE` (a closure tuple's relation is the seed's or a rewrite
output relation — both declared). -/

/-- One rewrite step preserves the subject name (computed keeps the subject; ttu keeps
    its name). -/
theorem rewriteStep_subjectName {S : Schema} {t u : Tuple} (h : u ∈ rewriteStep S t) :
    u.subject.name = t.subject.name := by
  unfold rewriteStep at h
  obtain ⟨r, _, hap⟩ := List.mem_filterMap.mp h
  obtain ⟨ot, mr, or, kind⟩ := r
  unfold applyRRule at hap
  split at hap
  · cases kind with
    | computed => simp only [Option.some.injEq] at hap; rw [← hap]
    | ttu tr => simp only [Option.some.injEq] at hap; rw [← hap]
  · simp at hap

/-- Subject-name preservation across the bounded closure. -/
theorem rewriteClosureAux_subjectName {S : Schema} {nm : String} :
    ∀ (n : Nat) (cur : List Tuple), (∀ w ∈ cur, w.subject.name = nm) →
      ∀ u ∈ rewriteClosureAux S n cur, u.subject.name = nm := by
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
      rw [rewriteStep_subjectName hwx]; exact hcur x hx

/-- **Every rewrite-closure tuple keeps the raw write's subject name.** -/
theorem rewriteClosure_subjectName {S : Schema} {t u : Tuple}
    (h : u ∈ rewriteClosure S t) : u.subject.name = t.subject.name := by
  unfold rewriteClosure at h
  exact rewriteClosureAux_subjectName _ _ (fun w hw => by rw [List.mem_singleton.mp hw]) _ h

/-- **A rewrite-closure tuple's relation is never `BARE`**: it is either the raw seed's
    relation (declared, `StoreValidRules`) or a rewrite output relation (a declared def
    key). -/
theorem rewriteClosure_rel_ne_bare {S : Schema} {T : Store} (hWF : WF S)
    (hSV : StoreValidRules S T) {t : Tuple} (ht : t ∈ T) {u : Tuple}
    (hu : u ∈ rewriteClosure S t) : u.relation ≠ BARE := by
  rcases rewriteClosure_produced hu with heq | ⟨r, hr, _, hrout⟩
  · rw [heq]
    obtain ⟨e, _, hlk, _, _⟩ := hSV t ht
    exact lookup_rel_ne_bare hWF hlk
  · obtain ⟨d, hd, hd1, _⟩ := schemaRewrites_provenance hr
    intro hbare
    have hd12 : d.1.2 = BARE := by
      have hsnd : d.1.2 = r.outRel := congrArg Prod.snd hd1
      rw [hsnd, hrout]; exact hbare
    have hrel : relNameOK d.1.2 := hWF.relNames d hd
    rw [hd12] at hrel
    exact hrel (by simp [BARE, String.contains])

/-! ## Chain composition — a graph path over the rewrite-closure is a `sem` membership

Mirror of DirectCorrect's `semAux_of_chainN`, but each hop's base membership is
`semAux_of_rewriteClosure` (at *some* fuel, not fuel 1) and the userset step is
`semAux_lift_untainted`. Fuel is threaded existentially (the tight bound is unnecessary —
the top-level discharges it via the T0a-stability sidestep). -/

/-- **The W2 soundness chain.** A membership chain over `Tstar = ⋃_{t∈T} rewriteClosure
    S t`, from `subjNode s` to `objNode ⟨ot,on⟩ r`, is a `sem` membership at some fuel. -/
theorem semAux_of_ruleChain {S : Schema} {T : Store} {q : Query}
    (hWF : WF S) (hUT : UntaintedSchema S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hSV : StoreValidRules S T) (hSF : StarFreeStore T) :
    ∀ {n : Nat} {u v : NodeKey}, TupleChainN (T.flatMap (rewriteClosure S)) n u v →
      ∀ {s : SubjectRef}, s.name ≠ STAR → subjNode s = u →
      ∀ {ot on r : String}, on ≠ STAR → objNode ⟨ot, on⟩ r = v →
      ∃ f, semAux S s T q f ot on r = true := by
  intro n u v hchain
  induction hchain with
  | single t ht =>
    intro s hsn hsu ot on r hon hov
    obtain ⟨t0, ht0, htc⟩ := List.mem_flatMap.mp ht
    have hsfsub : t.subject.name ≠ STAR := rewriteClosure_subjectName htc ▸ (hSF t0 ht0).1
    have hsfobj : t.object.name ≠ STAR := rewriteClosure_object htc ▸ (hSF t0 ht0).2
    have hs' : s = t.subject := subjNode_inj hsn hsfsub hsu
    subst hs'
    obtain ⟨hobj, hrel⟩ := objNode_inj hon hsfobj hov
    subst hrel
    obtain ⟨f, hf⟩ := semAux_of_rewriteClosure (q := q) hNK hTT hSV hSF ht0 htc
    rw [← hobj] at hf
    exact ⟨f, hf⟩
  | @cons t ht n v rest ih =>
    intro s hsn hsu ot on r hon hov
    obtain ⟨t0, ht0, htc⟩ := List.mem_flatMap.mp ht
    have hsfsub : t.subject.name ≠ STAR := rewriteClosure_subjectName htc ▸ (hSF t0 ht0).1
    have hsfobj : t.object.name ≠ STAR := rewriteClosure_object htc ▸ (hSF t0 ht0).2
    have hs' : s = t.subject := subjNode_inj hsn hsfsub hsu
    subst hs'
    -- the userset intermediate at t's object node
    have hs'n : (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).name ≠ STAR := hsfobj
    have hs'p : (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).predicate ≠ BARE :=
      rewriteClosure_rel_ne_bare hWF hSV ht0 htc
    have hsub : subjNode (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef) =
        objNode t.object t.relation := (objNode_eq_subjNode hsfobj).symm
    obtain ⟨fw, hfw⟩ := semAux_of_rewriteClosure (q := q) hNK hTT hSV hSF ht0 htc
    obtain ⟨frest, hfrest⟩ := ih hs'n hsub hon hov
    exact ⟨frest + fw, semAux_lift_untainted hUT hSF hs'n hs'p hfw frest ot on r hfrest⟩

/-! ## Soundness top-level — a probe hit is a `sem` membership -/

/-- **The W2 soundness direction.** On any state reached by W2 rule-routed writes of an
    admission-valid, star-free store, graph reachability from the query subject node to
    the query object node is a `sem` membership. Every edge materialises a rewrite-
    closure tuple (`reachedByRules_edge_sound`), the trail is a chain over `Tstar`, and
    `semAux_of_ruleChain` maps it to `sem` — the fuel obligation discharged by the
    T0a-stability sidestep (`sem_fuel_stable`; no tight bound needed). -/
theorem sem_of_rules_reach {S : Schema} {T : Store} {σ : GraphState} {q : Query}
    (hWF : WF S) (hUT : UntaintedSchema S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : ReachedByRules σ S T)
    (hnr : NReaches σ.edges (subjNode q.subject) (objNode q.object q.relation)) :
    sem S T q = true := by
  obtain ⟨l, hl⟩ := trail_of_nreaches hnr
  have hsound : ∀ a b, (a, b) ∈ σ.edges →
      ∃ w ∈ T.flatMap (rewriteClosure S),
        a = subjNode w.subject ∧ b = objNode w.object w.relation := by
    intro a b hab
    obtain ⟨t, ht, u, hu, h1, h2⟩ := reachedByRules_edge_sound hReach a b hab
    exact ⟨u, List.mem_flatMap.mpr ⟨t, ht, hu⟩, h1, h2⟩
  have hchain := chainN_of_trail hsound l _ _ hl
  obtain ⟨f, hf⟩ := semAux_of_ruleChain hWF hUT hTT hNK hSV hSF hchain hqs rfl hqo rfl
  have hStrat := stratifiable_untainted hUT
  have hDecl := storeDeclared_of_validRules hSV
  have hsem_f := semAux_mono S (untainted_noExclAll hUT) q.subject T q
    (le_max_left f (fuelBound S T)) _ _ _ hf
  rw [← sem_fuel_stable S T q hStrat hDecl _ (le_max_right f (fuelBound S T))]
  exact hsem_f

end Zanzibar
