import ZanzibarProofs.GraphIndex.RulesComplete
import ZanzibarProofs.GraphIndex.BareStarCorrect

/-!
# The untainted rule-routing correspondence over BARE-STAR stores (ROADMAP W3c read half, step 1)

`graph_correct_rules` (W2) proved `check = sem` on the untainted `computed`/`ttu`/`union`
fragment, but only over `StarFreeStore`. The W3c read half needs the same correspondence on
stores carrying **bare `user:*` grants** (`BareStarStore`, W1a's store predicate) — the star
grants that feed the boolean fragment's `stars` residues — and for **star-bare query
subjects** (the `coveredFn`/`stars ↔ sem` correspondence is exactly the star-subject
instance). This file composes W1a's bare-star machinery (`Covers`-style probe-2 chains,
`directLeaf_elim_bs`, `mog_elim_nus`) with W2's rule routing (`rewriteClosure`,
`ReachedByRulesAdmitted`), closing `graph_correct_rulesBS`.

**Fragment condition** (`TtuStarFree`): no TTU rewrite arm matches a stored star-subject
tuple — wildcard parents stay out of TTU tuplesets. This mirrors the write model's scope:
`writeRules` materialises NO wildcard bridges (it is a plain `writeDirect` fold,
`RulesWrite.lean`); a star parent in a TTU tupleset produces a userset-star subject
`(T, *, tr)` whose graph coverage needs the W1c **in-bridge** machinery
(`wildcard-materialization-spec.md §3.4`, `UsStarWrite.lean`) that is not yet composed with
rule routing. Attack-first (2026-07-11, `#eval`, scratch deleted) CONFIRMED necessity: with
a star tupleset tuple `folder:* → doc:d6#parent`, `sem` (via `ttuLeaf`'s `instances` branch)
answers `true` while the rule-routed graph answers `false`.

**Attack-first (2026-07-11, no refutation; scratch deleted).** Planned `graph_correct_rulesBS`
vs `sem` on a ~180-query grid over a mixed `computed`/`ttu`/`union` schema: `user:*` grants
feeding computed arms, D1 star flow-through (`user:* → group:g#mem`), a star grant on a TTU
*target* relation, a D1 chain crossing a rewrite output fed by a star grant
(`doc:d1#viewer → doc:dz#viewer` with viewer fed by a starred `editor`), star-bare and
userset subjects, ghost endpoints. Zero mismatches; `semAux_star_to_bare` (star coverage ⇒
every bare concrete of the type) had zero violations.
-/

namespace Zanzibar

/-! ## The fragment condition -/

/-- **`TtuStarFree S T`** — no TTU rewrite arm matches a stored star-subject tuple (no
    wildcard parents in TTU tuplesets). See the header: this pins the fragment to what the
    bridge-free `writeRules` write model covers; without it the correspondence is FALSE
    (attack-confirmed), because a star tupleset parent needs W1c in-bridges. -/
def TtuStarFree (S : Schema) (T : Store) : Prop :=
  ∀ t ∈ T, t.subject.name = STAR →
    ∀ a ∈ schemaRewrites S, ∀ tr, a.kind = RuleKind.ttu tr →
      ¬(t.relation = a.matchRel ∧ t.object.type = a.objectType)

/-! ## `ttuLeaf` elimination — the star branch dead by `TtuStarFree` -/

/-- **`ttuLeaf` elimination, no-star-tupleset version.** Like `ttuLeaf_elim`, but the star
    (`instances`) branch is killed by the hypothesis that no stored star tuple matches this
    tupleset `(ts, ot)` — the per-leaf instance of `TtuStarFree`. The parent's star-freeness
    is returned (the graph edge construction needs it). -/
theorem ttuLeaf_elim_nss {rec : Rec} {s' : SubjectRef} {T : Store} {q : Query}
    {tr ts ot on : String}
    (hnostar : ∀ tup ∈ T, tup.subject.name = STAR →
      ¬(tup.relation = ts ∧ tup.object.type = ot))
    (h : ttuLeaf rec s' T q tr ts ot on = true) :
    ∃ tup ∈ T, tup.relation = ts ∧ tup.object.type = ot ∧
      (matchingObjects on).contains tup.object.name = true ∧
      tup.subject.name ≠ STAR ∧
      ((s'.type = tup.subject.type ∧ s'.name = tup.subject.name ∧ s'.predicate = tr)
        ∨ rec tup.subject.type tup.subject.name tr = true) := by
  unfold ttuLeaf at h
  simp only at h
  obtain ⟨tup, htup, hbody⟩ := List.any_eq_true.mp h
  by_cases hcond : (tup.relation == ts && tup.object.type == ot &&
      (matchingObjects on).contains tup.object.name) = true
  · rw [if_pos hcond] at hbody
    have hcond' := hcond
    simp only [Bool.and_eq_true, beq_iff_eq] at hcond'
    have hpn : (tup.subject.name != STAR) = true := by
      rw [bne_iff_ne]
      intro hstar
      exact hnostar tup htup hstar ⟨hcond'.1.1, hcond'.1.2⟩
    rw [if_pos hpn] at hbody
    simp only [Bool.or_eq_true, Bool.and_eq_true, beq_iff_eq] at hbody
    refine ⟨tup, htup, hcond'.1.1, hcond'.1.2, hcond'.2, bne_iff_ne .. |>.mp hpn, ?_⟩
    rcases hbody with ⟨⟨h1, h2⟩, h3⟩ | hrec
    · exact Or.inl ⟨h1, h2, h3⟩
    · exact Or.inr hrec
  · rw [if_neg hcond] at hbody; simp at hbody

/-! ## Closure subject characterisation — star subjects survive the closure untouched

The rewrite closure preserves the subject NAME (`rewriteClosure_subjectName`); only a `ttu`
arm changes the subject (predicate). Under `TtuStarFree` + `TtuTuplesetsDirect`, no `ttu`
arm ever fires on a star-subject closure member: the member is either the stored seed
(excluded by `TtuStarFree` directly) or a rewrite output at the tupleset relation (excluded
by `no_rewrite_outputs_tupleset`). So a star-subject closure member carries the seed's FULL
subject — bare, by `BareStarStore`. -/

/-- The carrier: subject pinned to the seed's on star names, plus output provenance. -/
private def StarSeed (S : Schema) (t w : Tuple) : Prop :=
  (w.subject.name = STAR → w.subject = t.subject) ∧
  (w = t ∨ ∃ r ∈ schemaRewrites S, r.objectType = w.object.type ∧ r.outRel = w.relation)

private theorem starSeed_step {S : Schema} {T : Store}
    (hTT : TtuTuplesetsDirect S) (hTS : TtuStarFree S T)
    {t : Tuple} (ht : t ∈ T) {x u : Tuple}
    (hx : StarSeed S t x) (hu : u ∈ rewriteStep S x) : StarSeed S t u := by
  obtain ⟨hxs, hRx⟩ := hx
  refine ⟨?_, Or.inr (rewriteStep_outRel hu)⟩
  unfold rewriteStep at hu
  obtain ⟨r, hr, happly⟩ := List.mem_filterMap.mp hu
  unfold applyRRule at happly
  split at happly
  · rename_i hcond
    cases hk : r.kind with
    | computed =>
      rw [hk] at happly
      simp only [Option.some.injEq] at happly
      intro hustar
      rw [← happly] at hustar ⊢
      exact hxs hustar
    | ttu tr =>
      rw [hk] at happly
      simp only [Option.some.injEq] at happly
      intro hustar
      -- u.subject = ⟨x.subject.type, x.subject.name, tr⟩, so x's subject name is STAR
      have hxstar : x.subject.name = STAR := by rw [← happly] at hustar; exact hustar
      exfalso
      -- x is the stored seed or a rewrite output; both are excluded
      rcases hRx with rfl | ⟨r', hr', hr'ot, hr'out⟩
      · -- stored star tuple matching a ttu arm: excluded by TtuStarFree
        exact hTS x ht hxstar r hr tr hk hcond
      · -- rewrite output at a ttu tupleset relation: excluded by TtuTuplesetsDirect
        obtain ⟨d, hd, hd1, harm⟩ := schemaRewrites_provenance hr
        have htt : (tr, r.matchRel) ∈ exprTtus d.2 := by
          have harm' : r ∈ exprArms d.1.1 d.1.2 d.2 := harm
          exact exprArms_ttu_mem d.2 harm' tr hk
        refine no_rewrite_outputs_tupleset hTT hd htt hr' ?_ ?_
        · -- r'.objectType = d.1.1 (= r.objectType = x.object.type)
          rw [hr'ot, hcond.2]
          exact (congrArg Prod.fst hd1).symm
        · -- r'.outRel = r.matchRel (= x.relation)
          rw [hr'out, hcond.1]
  · simp at happly

/-- **A star-subject closure member carries the seed's full subject** (no `ttu` arm ever
    fires on it — see the section header). -/
theorem rewriteClosure_star_subject {S : Schema} {T : Store}
    (hTT : TtuTuplesetsDirect S) (hTS : TtuStarFree S T)
    {t : Tuple} (ht : t ∈ T) {u : Tuple} (hu : u ∈ rewriteClosure S t)
    (hstar : u.subject.name = STAR) : u.subject = t.subject := by
  have haux : ∀ (n : Nat) (cur : List Tuple), (∀ w ∈ cur, StarSeed S t w) →
      ∀ v ∈ rewriteClosureAux S n cur, StarSeed S t v := by
    intro n
    induction n with
    | zero => intro cur hcur v hv; exact hcur v hv
    | succ m ih =>
      intro cur hcur v hv
      rw [rewriteClosureAux, List.mem_append] at hv
      rcases hv with hin | hrec
      · exact hcur v hin
      · refine ih (cur.flatMap (rewriteStep S)) ?_ v hrec
        intro w hw
        obtain ⟨x, hx, hwx⟩ := List.mem_flatMap.mp hw
        exact starSeed_step hTT hTS ht (hcur x hx) hwx
  unfold rewriteClosure at hu
  refine (haux (S.keys.length + 1) [t] ?_ u hu).1 hstar
  intro w hw
  rw [List.mem_singleton.mp hw]
  exact ⟨fun _ => rfl, Or.inl rfl⟩

/-- A star-subject closure member is bare (its subject is the seed's; `BareStarStore`). -/
theorem rewriteClosure_star_bare {S : Schema} {T : Store}
    (hTT : TtuTuplesetsDirect S) (hTS : TtuStarFree S T) (hBS : BareStarStore T)
    {t : Tuple} (ht : t ∈ T) {u : Tuple} (hu : u ∈ rewriteClosure S t)
    (hstar : u.subject.name = STAR) : u.subject.predicate = BARE := by
  have hsub := rewriteClosure_star_subject hTT hTS ht hu hstar
  rw [hsub]
  exact (hBS t ht).1 (by rw [← hsub]; exact hstar)

/-! ## Per-hop soundness — every closure tuple is a `sem` membership (subject-generic) -/

/-- **Star-subject self-grant.** A grant whose subject IS the (star) query subject fires the
    star branch's exact-shape disjunct. The star-subject counterpart of
    `directLeaf_grant_self`. -/
theorem directLeaf_grant_starSelf {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {rs : List Restriction} {ot on rel : String} {g : Tuple}
    (hg : g ∈ grantsOf T rs ot on rel) (hsubj : g.subject = s) (hs : s.name = STAR) :
    directLeaf rec s T q rs ot on rel = true := by
  unfold directLeaf
  rw [if_pos (by simpa using hs), Bool.or_eq_true]
  refine Or.inl (List.any_eq_true.mpr ⟨g, hg, ?_⟩)
  rw [hsubj]
  simp [hs]

/-- **Seed membership, bare-star store** — a stored tuple is a fuel-1 `sem` membership of
    its own object node, for its own (possibly star-bare) subject. -/
theorem semAux_seed_bs {S : Schema} {T : Store} {q : Query}
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) {t : Tuple} (ht : t ∈ T) :
    semAux S t.subject T q 1 t.object.type t.object.name t.relation = true := by
  obtain ⟨e, rs, hlk, hdir, hrm⟩ := hSV t ht
  rw [semAux, step, hlk]
  refine evalE_direct_arm e hdir ?_
  have hg : t ∈ grantsOf T rs t.object.type t.object.name t.relation :=
    grantsOf_intro ht rfl rfl (matchingObjects_self _ (hBS t ht).2) hrm
  by_cases hstar : t.subject.name = STAR
  · exact directLeaf_grant_starSelf hg rfl hstar
  · exact directLeaf_grant_self hg rfl hstar

/-- The closure-step carrier (mirror of `RulesSound.SemReached`, bare-star store). -/
private def SemReachedBS (S : Schema) (T : Store) (q : Query) (t w : Tuple) : Prop :=
  (∃ f, semAux S w.subject T q f w.object.type w.object.name w.relation = true) ∧
  (w = t ∨ ∃ r ∈ schemaRewrites S, r.objectType = w.object.type ∧ r.outRel = w.relation)

/-- The closure step, bare-star store (mirror of `semAux_step`; the only star-freeness the
    original used was the OBJECT's, which `BareStarStore` still provides). -/
private theorem semAux_step_bs {S : Schema} {T : Store} {q : Query} (hNK : NodupKeys S)
    (hTT : TtuTuplesetsDirect S) (hBS : BareStarStore T) {t : Tuple} (ht : t ∈ T)
    {x u : Tuple} (hx : SemReachedBS S T q t x) (hu : u ∈ rewriteStep S x) :
    ∃ f, semAux S u.subject T q f u.object.type u.object.name u.relation = true := by
  obtain ⟨⟨fx, hfx⟩, hRx⟩ := hx
  unfold rewriteStep at hu
  obtain ⟨r, hr, happly⟩ := List.mem_filterMap.mp hu
  obtain ⟨d, hd, hd1, harm⟩ := schemaRewrites_provenance hr
  have hlk : S.lookup (r.objectType, r.outRel) = some d.2 := by
    rw [← hd1]; exact lookup_of_mem hNK hd
  have harm' : r ∈ exprArms r.objectType r.outRel d.2 := by
    rw [hd1] at harm; exact harm
  obtain ⟨rot, rmr, rout, rkind⟩ := r
  simp only at hlk harm' happly ⊢
  unfold applyRRule at happly
  split at happly
  · rename_i hcond
    obtain ⟨hxrel, hxot⟩ := hcond
    simp only at hxrel hxot
    rw [← hxot, ← hxrel] at harm'
    rw [← hxot] at hlk
    cases rkind with
    | computed =>
      simp only [Option.some.injEq] at happly
      subst happly
      refine ⟨fx + 1, ?_⟩
      rw [semAux, step, hlk]
      show evalE (semAux S x.subject T q fx) x.subject T q
        x.object.type x.object.name rout d.2 = true
      exact evalE_computed_arm d.2 harm' hfx
    | ttu tr =>
      simp only [Option.some.injEq] at happly
      subst happly
      have hxT : x ∈ T := by
        rcases hRx with rfl | ⟨r', hr', hr'ot, hr'out⟩
        · exact ht
        · exfalso
          have htt : (tr, x.relation) ∈ exprTtus d.2 :=
            exprArms_ttu_mem d.2 harm' tr rfl
          refine no_rewrite_outputs_tupleset hTT hd htt hr' ?_ ?_
          · rw [hr'ot, hxot]; exact (congrArg Prod.fst hd1).symm
          · rw [hr'out]
      refine ⟨1, ?_⟩
      rw [semAux, step, hlk]
      show evalE (semAux S ⟨x.subject.type, x.subject.name, tr⟩ T q 0)
        ⟨x.subject.type, x.subject.name, tr⟩ T q x.object.type x.object.name rout d.2 = true
      refine evalE_ttu_arm d.2 harm' ?_
      unfold ttuLeaf
      refine List.any_eq_true.mpr ⟨x, hxT, ?_⟩
      have hcon : (matchingObjects x.object.name).contains x.object.name = true :=
        matchingObjects_self _ (hBS x hxT).2
      rw [if_pos (by simp only [beq_self_eq_true, Bool.and_true, hcon])]
      by_cases hpn : (x.subject.name != STAR) = true
      · rw [if_pos hpn]; simp
      · rw [if_neg hpn]; simp
  · simp at happly

/-- **Per-hop soundness, bare-star store** (mirror of `semAux_of_rewriteClosure`): every
    closure tuple of a stored write is a `sem` membership for its own subject — star-bare
    subjects included. -/
theorem semAux_of_rewriteClosure_bs {S : Schema} {T : Store} {q : Query} (hNK : NodupKeys S)
    (hTT : TtuTuplesetsDirect S) (hSV : StoreValidRules S T) (hBS : BareStarStore T)
    {t u : Tuple} (ht : t ∈ T) (hu : u ∈ rewriteClosure S t) :
    ∃ f, semAux S u.subject T q f u.object.type u.object.name u.relation = true := by
  have haux : ∀ (n : Nat) (cur : List Tuple), (∀ w ∈ cur, SemReachedBS S T q t w) →
      ∀ v ∈ rewriteClosureAux S n cur, SemReachedBS S T q t v := by
    intro n
    induction n with
    | zero => intro cur hcur v hv; exact hcur v hv
    | succ m ih =>
      intro cur hcur v hv
      rw [rewriteClosureAux, List.mem_append] at hv
      rcases hv with hin | hrec
      · exact hcur v hin
      · refine ih (cur.flatMap (rewriteStep S)) ?_ v hrec
        intro w hw
        obtain ⟨x, hx, hwx⟩ := List.mem_flatMap.mp hw
        exact ⟨semAux_step_bs hNK hTT hBS ht (hcur x hx) hwx,
          Or.inr (rewriteStep_outRel hwx)⟩
  unfold rewriteClosure at hu
  refine (haux (S.keys.length + 1) [t] ?_ u hu).1
  intro w hw
  rw [List.mem_singleton.mp hw]
  exact ⟨⟨1, semAux_seed_bs hSV hBS ht⟩, Or.inl rfl⟩

/-! ## The userset lift, bare-star store

`s ∈ s'` and `s' ∈ v` ⇒ `s ∈ v` on an untainted schema over a `BareStarStore` — the W2
`semAux_lift_untainted`, with the star-freeness leaf eliminations replaced by the bare-star
ones (`directLeaf_elim_bs`, `mog_elim_nus`, `ttuLeaf_elim_nss`). The fixed subject `s` is
GENERIC (star-bare subjects lift, too — `directLeaf_of_mog`/`ttuLeaf_intro_rec` are
subject-blind); the lifted-through userset `s'` is concrete as before. The `ttu` case needs
the rewrite-arm provenance (`harms`) to instantiate `TtuStarFree` at the leaf. -/

/-- The `evalE`-level lift (bare-star store). -/
theorem evalE_lift_bs {S : Schema} {T : Store} {q : Query} {s s' : SubjectRef}
    (hNE : S.noExclAll) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hs'n : s'.name ≠ STAR) (hs'p : s'.predicate ≠ BARE) {f f₀ : Nat}
    (hmem : semAux S s T q f₀ s'.type s'.name s'.predicate = true)
    (ih : ∀ ot on r, semAux S s' T q f ot on r = true →
      semAux S s T q (f + f₀) ot on r = true) :
    ∀ e, containsBool e = false → ∀ ot on r,
      (∀ a ∈ exprArms ot r e, a ∈ schemaRewrites S) →
      evalE (semAux S s' T q f) s' T q ot on r e = true →
      evalE (semAux S s T q (f + f₀)) s T q ot on r e = true := by
  intro e
  induction e with
  | direct rs =>
    intro _ ot on r _ h
    rcases directLeaf_elim_bs hBS.noUsersetStar hs'n h with
      ⟨g, hg, hgs⟩ | ⟨hsp, _⟩ | hmog
    · apply directLeaf_of_mog
      refine mog_intro hg (by rw [hgs]; exact hs'p) (by rw [hgs]; exact hs'n) ?_
      rw [hgs]
      exact semAux_mono S hNE s T q (Nat.le_add_left f₀ f) _ _ _ hmem
    · exact absurd hsp hs'p
    · obtain ⟨g, hg, hpb, hps, hrec⟩ := mog_elim_nus hBS.noUsersetStar hmog
      exact directLeaf_of_mog (mog_intro hg hpb hps (ih _ _ _ hrec))
  | computed r' =>
    intro _ ot on r _ h
    exact ih ot on r' h
  | ttu tr' ts' =>
    intro _ ot on r harms h
    have harm : (⟨ot, ts', r, RuleKind.ttu tr'⟩ : RRule) ∈ schemaRewrites S :=
      harms _ (by simp [exprArms])
    have hnostar : ∀ tup ∈ T, tup.subject.name = STAR →
        ¬(tup.relation = ts' ∧ tup.object.type = ot) :=
      fun tup htup hst => hTS tup htup hst _ harm tr' rfl
    obtain ⟨tup, htup, hrel, hot, hcon, hpn, hdisj⟩ := ttuLeaf_elim_nss hnostar h
    refine ttuLeaf_intro_rec htup hrel hot hcon hpn ?_
    rcases hdisj with ⟨he1, he2, he3⟩ | hrec
    · rw [← he1, ← he2, ← he3]
      exact semAux_mono S hNE s T q (Nat.le_add_left f₀ f) _ _ _ hmem
    · exact ih tup.subject.type tup.subject.name tr' hrec
  | union a b iha ihb =>
    intro hcb ot on r harms h
    simp only [containsBool, Bool.or_eq_false_iff] at hcb
    simp only [evalE, Bool.or_eq_true] at h ⊢
    have harmsa : ∀ x ∈ exprArms ot r a, x ∈ schemaRewrites S := by
      intro x hx; exact harms x (by simp only [exprArms, List.mem_append]; exact Or.inl hx)
    have harmsb : ∀ x ∈ exprArms ot r b, x ∈ schemaRewrites S := by
      intro x hx; exact harms x (by simp only [exprArms, List.mem_append]; exact Or.inr hx)
    rcases h with ha | hb
    · exact Or.inl (iha hcb.1 ot on r harmsa ha)
    · exact Or.inr (ihb hcb.2 ot on r harmsb hb)
  | inter _ _ _ _ => intro hcb; simp [containsBool] at hcb
  | excl _ _ _ _ => intro hcb; simp [containsBool] at hcb

/-- **The userset lift, bare-star store** (mirror of `semAux_lift_untainted`). -/
theorem semAux_lift_untainted_bs {S : Schema} {T : Store} {q : Query} {s s' : SubjectRef}
    (hUT : UntaintedSchema S) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
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
      exact evalE_lift_bs (untainted_noExclAll hUT) hBS hTS hs'n hs'p hmem ih e
        (containsBool_lookup hUT hlk) ot on r (lookup_exprArms_sub hUT hlk) h

/-! ## Chain composition — a graph path is a `sem` membership, subject-generic -/

/-- **`subjNode` is globally injective.** Star subjects map to `wAny` nodes carrying
    the full `(type, STAR, predicate)`; concrete subjects to `plain` nodes — the variants
    separate the two branches, and each branch is injective. -/
theorem subjNode_inj_total {s s' : SubjectRef} (h : subjNode s = subjNode s') : s = s' := by
  by_cases hs : s.name = STAR <;> by_cases hs' : s'.name = STAR
  · unfold subjNode at h
    rw [if_pos hs, if_pos hs'] at h
    simp only [NodeKey.mk.injEq] at h
    obtain ⟨h1, -, h3, -⟩ := h
    obtain ⟨st, sn, sp⟩ := s; obtain ⟨st', sn', sp'⟩ := s'
    simp only at h1 h3 hs hs'
    simp [h1, h3, hs, hs']
  · unfold subjNode at h
    rw [if_pos hs, if_neg hs'] at h
    simp [NodeKey.mk.injEq] at h
  · unfold subjNode at h
    rw [if_neg hs, if_pos hs'] at h
    simp [NodeKey.mk.injEq] at h
  · exact subjNode_inj hs hs' h

/-- **The W2 soundness chain, bare-star store** (mirror of `semAux_of_ruleChain`): a
    membership chain over `Tstar` from `subjNode s` — for ANY subject `s`, star subjects
    included (their node is the `wAny` source the star closure tuples emanate from) — is a
    `sem` membership at some fuel. -/
theorem semAux_of_ruleChain_bs {S : Schema} {T : Store} {q : Query}
    (hWF : WF S) (hUT : UntaintedSchema S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T) :
    ∀ {n : Nat} {u v : NodeKey}, TupleChainN (T.flatMap (rewriteClosure S)) n u v →
      ∀ {s : SubjectRef}, subjNode s = u →
      ∀ {ot on r : String}, on ≠ STAR → objNode ⟨ot, on⟩ r = v →
      ∃ f, semAux S s T q f ot on r = true := by
  intro n u v hchain
  induction hchain with
  | single t ht =>
    intro s hsu ot on r hon hov
    obtain ⟨t0, ht0, htc⟩ := List.mem_flatMap.mp ht
    have hsfobj : t.object.name ≠ STAR := rewriteClosure_object htc ▸ (hBS t0 ht0).2
    have hs' : s = t.subject := subjNode_inj_total hsu
    subst hs'
    obtain ⟨hobj, hrel⟩ := objNode_inj hon hsfobj hov
    subst hrel
    obtain ⟨f, hf⟩ := semAux_of_rewriteClosure_bs (q := q) hNK hTT hSV hBS ht0 htc
    rw [← hobj] at hf
    exact ⟨f, hf⟩
  | @cons t ht n v rest ih =>
    intro s hsu ot on r hon hov
    obtain ⟨t0, ht0, htc⟩ := List.mem_flatMap.mp ht
    have hsfobj : t.object.name ≠ STAR := rewriteClosure_object htc ▸ (hBS t0 ht0).2
    have hs' : s = t.subject := subjNode_inj_total hsu
    subst hs'
    have hs'n : (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).name ≠ STAR := hsfobj
    have hs'p : (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef).predicate ≠ BARE :=
      rewriteClosure_rel_ne_bare hWF hSV ht0 htc
    have hsub : subjNode (⟨t.object.type, t.object.name, t.relation⟩ : SubjectRef) =
        objNode t.object t.relation := (objNode_eq_subjNode hsfobj).symm
    obtain ⟨fw, hfw⟩ := semAux_of_rewriteClosure_bs (q := q) hNK hTT hSV hBS ht0 htc
    obtain ⟨frest, hfrest⟩ := ih hsub hon hov
    exact ⟨frest + fw,
      semAux_lift_untainted_bs hUT hBS hTS hs'n hs'p hfw frest ot on r hfrest⟩

/-! ## Star coverage transfers to every concrete — `semAux_star_to_bare`

The star-subject read covers a bare concrete of the same type: exact-shape star grants are
absorbed by the bare branch's star disjunct, and every recursive consultation is
subject-blind up to the pointwise fuel IH. Needed for the probe-2 glue: a chain from
`wAny(T, BARE)` IS a star-subject chain, and this transfers its `sem` membership to the
bare query subject. (No store conditions needed — attack-confirmed on the corpus.) -/

/-- Star-branch elimination of `directLeaf`. -/
theorem directLeaf_elim_star {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {rs : List Restriction} {ot on rel : String} (hs : s.name = STAR)
    (h : directLeaf rec s T q rs ot on rel = true) :
    (∃ g ∈ grantsOf T rs ot on rel, g.subject.name = STAR ∧ g.subject.type = s.type ∧
      g.subject.predicate = s.predicate)
    ∨ memberOfGranted rec T q (grantsOf T rs ot on rel) = true := by
  unfold directLeaf at h
  rw [if_pos (by simpa using hs), Bool.or_eq_true] at h
  rcases h with h | h
  · obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp h
    simp only [Bool.and_eq_true, beq_iff_eq] at hgt
    exact Or.inl ⟨g, hg, hgt.1.1, hgt.1.2, hgt.2⟩
  · exact Or.inr h

/-- `ttuLeaf` transfers from the star subject `(st, *, BARE)` to any bare concrete of type
    `st`, given the pointwise `rec` transfer: the non-star-parent branch's subject disjunct
    is dead for the star subject; the star-parent branch's `(type, targetRel)` test is
    subject-name-blind. -/
theorem ttuLeaf_star_to_bare {rec1 rec2 : Rec} (hle : RecLe rec1 rec2)
    {st : String} {s : SubjectRef} {T : Store} {q : Query} {tr ts ot on : String}
    (hstype : s.type = st) (hsp : s.predicate = BARE)
    (h : ttuLeaf rec1 ⟨st, STAR, BARE⟩ T q tr ts ot on = true) :
    ttuLeaf rec2 s T q tr ts ot on = true := by
  unfold ttuLeaf at h ⊢
  rw [List.any_eq_true] at h ⊢
  obtain ⟨tup, htup, htt⟩ := h
  refine ⟨tup, htup, ?_⟩
  by_cases hcond : (tup.relation == ts && tup.object.type == ot &&
      (matchingObjects on).contains tup.object.name) = true
  · rw [if_pos hcond] at htt ⊢
    by_cases hpn : (tup.subject.name != STAR) = true
    · rw [if_pos hpn] at htt ⊢
      rw [Bool.or_eq_true] at htt ⊢
      rcases htt with htt | htt
      · exfalso
        simp only [Bool.and_eq_true, beq_iff_eq] at htt
        rw [bne_iff_ne] at hpn
        exact hpn htt.1.2.symm
      · exact Or.inr (hle _ _ _ htt)
    · rw [if_neg hpn] at htt ⊢
      rw [Bool.or_eq_true] at htt ⊢
      rcases htt with htt | htt
      · simp only [Bool.and_eq_true, beq_iff_eq] at htt
        refine Or.inl ?_
        simp only [Bool.and_eq_true, beq_iff_eq]
        exact ⟨by rw [hstype]; exact htt.1, by rw [hsp]; exact htt.2⟩
      · rw [List.any_eq_true] at htt ⊢
        obtain ⟨inst, hi, hit⟩ := htt
        exact Or.inr ⟨inst, hi, hle _ _ _ hit⟩
  · rw [if_neg hcond] at htt; simp at htt

/-- **Star coverage ⇒ concrete membership.** On an untainted schema, a star-subject
    `sem` membership at `(st, *, BARE)` transfers to any bare concrete subject of type
    `st`, fuel-for-fuel. -/
theorem semAux_star_to_bare {S : Schema} {T : Store} {q : Query}
    (hUT : UntaintedSchema S) {st : String} {s : SubjectRef}
    (hstype : s.type = st) (hsn : s.name ≠ STAR) (hsp : s.predicate = BARE) :
    ∀ (f : Nat) (ot on r : String),
      semAux S ⟨st, STAR, BARE⟩ T q f ot on r = true →
      semAux S s T q f ot on r = true := by
  intro f
  induction f with
  | zero => intro ot on r h; simp [semAux] at h
  | succ f ih =>
    intro ot on r h
    rw [semAux, step] at h
    rw [semAux, step]
    cases hlk : S.lookup (ot, r) with
    | none => rw [hlk] at h; simp at h
    | some e =>
      rw [hlk] at h
      show evalE (semAux S s T q f) s T q ot on r e = true
      have hle : RecLe (semAux S ⟨st, STAR, BARE⟩ T q f) (semAux S s T q f) :=
        fun o n r' => ih o n r'
      have inner : ∀ e', containsBool e' = false →
          evalE (semAux S ⟨st, STAR, BARE⟩ T q f) ⟨st, STAR, BARE⟩ T q ot on r e' = true →
          evalE (semAux S s T q f) s T q ot on r e' = true := by
        intro e'
        induction e' with
        | direct rs =>
          intro _ hdl
          rcases directLeaf_elim_star rfl hdl with ⟨g, hg, hgstar, hgtype, hgpred⟩ | hmog
          · refine directLeaf_grant_bareStar hg hgstar hgpred ?_ hsn hsp
            rw [hgtype, hstype]
          · exact directLeaf_of_mog (memberOfGranted_mono hle T q _ hmog)
        | computed r' =>
          intro _ hev
          exact hle _ _ _ hev
        | ttu tr' ts' =>
          intro _ hev
          exact ttuLeaf_star_to_bare hle hstype hsp hev
        | union a b iha ihb =>
          intro hcb hev
          simp only [containsBool, Bool.or_eq_false_iff] at hcb
          simp only [evalE, Bool.or_eq_true] at hev ⊢
          rcases hev with ha | hb
          · exact Or.inl (iha hcb.1 ha)
          · exact Or.inr (ihb hcb.2 hb)
        | inter _ _ _ _ => intro hcb; simp [containsBool] at hcb
        | excl _ _ _ _ => intro hcb; simp [containsBool] at hcb
      exact inner e (containsBool_lookup hUT hlk) h

/-! ## Completeness — a `sem` membership is a probe-1 ∨ probe-2 reachability -/

/-- The computed-case relation rewrite, bare-star store (mirror of
    `nreaches_relation_rewrite`; the only star-freeness the original used was the closure
    tuple's OBJECT, which `BareStarStore` still provides). -/
theorem nreaches_relation_rewrite_bs {σ : GraphState} {S : Schema} {T : Store}
    (hRA : ReachedByRulesAdmitted σ S T) (hR : RewriteRanked S) (hBS : BareStarStore T)
    {ot on r r' : String} (hon : on ≠ STAR)
    (hrule : (⟨ot, r', r, RuleKind.computed⟩ : RRule) ∈ schemaRewrites S)
    {u : NodeKey} (hnr : NReaches σ.edges u (objNode ⟨ot, on⟩ r')) :
    NReaches σ.edges u (objNode ⟨ot, on⟩ r) := by
  obtain ⟨x, hux, hxlast⟩ := nreaches_last hnr
  obtain ⟨t, ht, w, hw, hxsub, hwobj⟩ :=
    reachedByRules_edge_sound (reachedByRules_of_admitted hRA) x _ hxlast
  have hwon : w.object.name ≠ STAR := rewriteClosure_object hw ▸ (hBS t ht).2
  obtain ⟨hobj, hrel⟩ := objNode_inj hon hwon hwobj
  have happly : applyRRule ⟨ot, r', r, RuleKind.computed⟩ w =
      some ⟨w.subject, r, w.object⟩ := by
    unfold applyRRule
    rw [if_pos (by exact ⟨hrel.symm, by rw [← hobj]⟩)]
  have hw' : (⟨w.subject, r, w.object⟩ : Tuple) ∈ rewriteStep S w :=
    List.mem_filterMap.mpr ⟨⟨ot, r', r, RuleKind.computed⟩, hrule, happly⟩
  have hw'cl : (⟨w.subject, r, w.object⟩ : Tuple) ∈ rewriteClosure S t :=
    rewriteClosure_saturated hR hw hw'
  have hedge : (subjNode w.subject, objNode ⟨ot, on⟩ r) ∈ σ.edges := by
    have := reachedByRulesAdmitted_edge_complete hRA t ht _ hw'cl
    rwa [show (⟨ot, on⟩ : ObjectRef) = w.object from hobj]
  rw [hxsub] at hux
  exact hux.tail_edge hedge

/-- **The completeness core, bare-star store.** A `sem` membership for a subject `s`
    (star ⇒ bare, the fragment scope) is graph reachability from `subjNode s` OR — for a
    bare concrete `s` — from `wAny(s.shape)` (the probe-2 disjunct: a bare-star grant's
    edge emanates from the star node, not `s`'s plain node). Mirror of
    `nreaches_of_semAux_rules` × `reach_of_semAux_bs`. -/
theorem nreaches_of_semAux_rulesBS {S : Schema} {T : Store} {q : Query} {σ : GraphState}
    (hUT : UntaintedSchema S) (hR : RewriteRanked S)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRA : ReachedByRulesAdmitted σ S T)
    {s : SubjectRef} (hsb : s.name = STAR → s.predicate = BARE) :
    ∀ (f : Nat) (ot on r : String), on ≠ STAR →
      semAux S s T q f ot on r = true →
      NReaches σ.edges (subjNode s) (objNode ⟨ot, on⟩ r)
      ∨ (s.name ≠ STAR ∧ s.predicate = BARE ∧
         NReaches σ.edges (wAnyNode s.shape) (objNode ⟨ot, on⟩ r)) := by
  intro f
  induction f with
  | zero => intro ot on r _ h; simp [semAux] at h
  | succ f ih =>
    intro ot on r hon h
    rw [semAux, step] at h
    cases hlk : S.lookup (ot, r) with
    | none => rw [hlk] at h; simp at h
    | some e =>
      rw [hlk] at h
      have hedgeSeed := reachedByRulesAdmitted_seed_edge hRA
      -- a flow-through recursion step: recurse, then tail with the userset grant's edge
      have hflow : ∀ {g : Tuple}, g ∈ T → g.subject.predicate ≠ BARE →
          g.subject.name ≠ STAR → g.object = (⟨ot, on⟩ : ObjectRef) → g.relation = r →
          semAux S s T q f g.subject.type g.subject.name g.subject.predicate = true →
          NReaches σ.edges (subjNode s) (objNode ⟨ot, on⟩ r)
          ∨ (s.name ≠ STAR ∧ s.predicate = BARE ∧
             NReaches σ.edges (wAnyNode s.shape) (objNode ⟨ot, on⟩ r)) := by
        intro g hgT hpb hps hobj hgrel hrec
        have hmid := ih _ _ _ hps hrec
        rw [objNode_eq_subjNode hps] at hmid
        have hedge := hedgeSeed g hgT
        rw [hobj, hgrel] at hedge
        rcases hmid with hL | ⟨h1, h2, hR'⟩
        · exact Or.inl (hL.tail hedge)
        · exact Or.inr ⟨h1, h2, hR'.tail hedge⟩
      -- inner induction on the def expr, carrying the rewrite-arm provenance
      have inner : ∀ e', containsBool e' = false →
          (∀ a ∈ exprArms ot r e', a ∈ schemaRewrites S) →
          evalE (semAux S s T q f) s T q ot on r e' = true →
          NReaches σ.edges (subjNode s) (objNode ⟨ot, on⟩ r)
          ∨ (s.name ≠ STAR ∧ s.predicate = BARE ∧
             NReaches σ.edges (wAnyNode s.shape) (objNode ⟨ot, on⟩ r)) := by
        intro e'
        induction e' with
        | direct rs =>
          intro _ _ hdl
          by_cases hstar : s.name = STAR
          · -- star subject: exact-shape star grant (its node IS subjNode s), or flow-through
            rcases directLeaf_elim_star hstar hdl with
              ⟨g, hg, hgstar, hgtype, hgpred⟩ | hmog
            · obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
              have hedge := hedgeSeed g hgT
              have hgon' : g.object.name = on := matchingObjects_elim hgon (hBS g hgT).2
              have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
              have hsubj : subjNode g.subject = subjNode s := by
                unfold subjNode
                rw [if_pos hgstar, if_pos hstar, hgtype, hgpred]
              rw [hobj, hgrel, hsubj] at hedge
              exact Or.inl (NReaches.edge hedge)
            · obtain ⟨g, hg, hpb, hps, hrec⟩ := mog_elim_nus hBS.noUsersetStar hmog
              obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
              have hgon' : g.object.name = on := matchingObjects_elim hgon (hBS g hgT).2
              have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
              exact hflow hgT hpb hps hobj hgrel hrec
          · -- concrete subject: exact match, bare-star cover (probe 2), or flow-through
            rcases directLeaf_elim_bs hBS.noUsersetStar hstar hdl with
              ⟨g, hg, hgs⟩ | ⟨hsp, g, hg, hgstar, hgbare, hgtype⟩ | hmog
            · obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
              have hedge := hedgeSeed g hgT
              have hgon' : g.object.name = on := matchingObjects_elim hgon (hBS g hgT).2
              have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
              rw [hobj, hgrel, hgs] at hedge
              exact Or.inl (NReaches.edge hedge)
            · obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
              have hedge := hedgeSeed g hgT
              have hgon' : g.object.name = on := matchingObjects_elim hgon (hBS g hgT).2
              have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
              have hsubj : subjNode g.subject = wAnyNode s.shape := by
                rw [subjNode, if_pos hgstar]
                simp only [wAnyNode, SubjectRef.shape, hgbare, hgtype, hsp]
              rw [hobj, hgrel, hsubj] at hedge
              exact Or.inr ⟨hstar, hsp, NReaches.edge hedge⟩
            · obtain ⟨g, hg, hpb, hps, hrec⟩ := mog_elim_nus hBS.noUsersetStar hmog
              obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
              have hgon' : g.object.name = on := matchingObjects_elim hgon (hBS g hgT).2
              have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
              exact hflow hgT hpb hps hobj hgrel hrec
        | computed r' =>
          intro _ harms hev
          have hsub : semAux S s T q f ot on r' = true := hev
          have hrule : (⟨ot, r', r, RuleKind.computed⟩ : RRule) ∈ schemaRewrites S :=
            harms _ (by simp [exprArms])
          rcases ih ot on r' hon hsub with hL | ⟨h1, h2, hR'⟩
          · exact Or.inl (nreaches_relation_rewrite_bs hRA hR hBS hon hrule hL)
          · exact Or.inr ⟨h1, h2, nreaches_relation_rewrite_bs hRA hR hBS hon hrule hR'⟩
        | ttu tr ts =>
          intro _ harms hev
          have harm : (⟨ot, ts, r, RuleKind.ttu tr⟩ : RRule) ∈ schemaRewrites S :=
            harms _ (by simp [exprArms])
          have hnostar : ∀ tup ∈ T, tup.subject.name = STAR →
              ¬(tup.relation = ts ∧ tup.object.type = ot) :=
            fun tup htup hst => hTS tup htup hst _ harm tr rfl
          obtain ⟨w, hwT, hwrel, hwot, hwcon, hwn, hdisj⟩ := ttuLeaf_elim_nss hnostar hev
          have happly : applyRRule ⟨ot, ts, r, RuleKind.ttu tr⟩ w =
              some ⟨⟨w.subject.type, w.subject.name, tr⟩, r, w.object⟩ := by
            unfold applyRRule; rw [if_pos (by exact ⟨hwrel, hwot⟩)]
          have hw' : (⟨⟨w.subject.type, w.subject.name, tr⟩, r, w.object⟩ : Tuple) ∈
              rewriteStep S w :=
            List.mem_filterMap.mpr ⟨_, harm, happly⟩
          have hw'cl := rewriteStep_mem_closure hw'
          have hwon : w.object.name = on := matchingObjects_elim hwcon (hBS w hwT).2
          have hedge := reachedByRulesAdmitted_edge_complete hRA w hwT _ hw'cl
          have hobj : w.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hwot, ← hwon]
          rw [hobj] at hedge
          rcases hdisj with ⟨he1, he2, he3⟩ | hrec
          · -- direct parent-match: s = ⟨w.subj.type, w.subj.name, tr⟩
            have hseq : (⟨w.subject.type, w.subject.name, tr⟩ : SubjectRef) = s := by
              obtain ⟨st, sn, sp⟩ := s
              simp only at he1 he2 he3
              simp [← he1, ← he2, ← he3]
            rw [hseq] at hedge
            exact Or.inl (NReaches.edge hedge)
          · -- parent-membership: recurse to the parent userset node, then the edge
            have hmid := ih w.subject.type w.subject.name tr hwn hrec
            rw [objNode_eq_subjNode hwn] at hmid
            rcases hmid with hL | ⟨h1, h2, hR'⟩
            · exact Or.inl (hL.tail hedge)
            · exact Or.inr ⟨h1, h2, hR'.tail hedge⟩
        | union a b iha ihb =>
          intro hcb harms hev
          simp only [containsBool, Bool.or_eq_false_iff] at hcb
          simp only [evalE, Bool.or_eq_true] at hev
          have harmsa : ∀ x ∈ exprArms ot r a, x ∈ schemaRewrites S := by
            intro x hx; exact harms x (by simp only [exprArms, List.mem_append]; exact Or.inl hx)
          have harmsb : ∀ x ∈ exprArms ot r b, x ∈ schemaRewrites S := by
            intro x hx; exact harms x (by simp only [exprArms, List.mem_append]; exact Or.inr hx)
          rcases hev with ha | hb
          · exact iha hcb.1 harmsa ha
          · exact ihb hcb.2 harmsb hb
        | inter _ _ _ _ => intro hcb; simp [containsBool] at hcb
        | excl _ _ _ _ => intro hcb; simp [containsBool] at hcb
      exact inner e (containsBool_lookup hUT hlk) (lookup_exprArms_sub hUT hlk) h

/-! ## Edge-endpoint characterisation and the assembly -/

/-- Every edge of an admitted rule-routed bare-star state has a plain-or-`wAny`-bare source
    and a plain target — the W2 analog of `admitted_edge_source_char` /
    `admitted_edges_target_plain`, via the closure star characterisation. -/
theorem rulesAdmitted_edge_endpoints_bs {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByRulesAdmitted σ S T) (hTT : TtuTuplesetsDirect S)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T) :
    ∀ e ∈ σ.edges,
      (e.1.variant = Variant.plain ∨ (e.1.variant = Variant.wAny ∧ e.1.pred = BARE))
      ∧ e.2.variant = Variant.plain := by
  intro e he
  obtain ⟨t, ht, w, hw, h1, h2⟩ :=
    reachedByRules_edge_sound (reachedByRules_of_admitted h) e.1 e.2 he
  have hwo : w.object.name ≠ STAR := rewriteClosure_object hw ▸ (hBS t ht).2
  refine ⟨?_, by rw [h2, objNode_plain hwo]⟩
  by_cases hst : w.subject.name = STAR
  · have hbare := rewriteClosure_star_bare hTT hTS hBS ht hw hst
    refine Or.inr ?_
    rw [h1, subjNode, if_pos hst]
    exact ⟨rfl, hbare⟩
  · exact Or.inl (by rw [h1, subjNode, if_neg hst])

/-- The `wAny` node of a shape is the star subject's own node. -/
theorem wAnyNode_eq_subjNode (ty p : String) :
    wAnyNode (ty, p) = subjNode ⟨ty, STAR, p⟩ := by
  unfold wAnyNode subjNode
  rw [if_pos rfl]

/-- **T2b, untainted rule-routing over bare-star stores (`graph_correct_rulesBS`).**
    On any state reached by admitted rule-routed writes of an admission-valid
    `BareStarStore` (bare `T:*` subject grants allowed; `TtuStarFree`: no wildcard TTU
    parents) over an untainted, directs-only-tupleset, key-unique, rewrite-acyclic schema,
    the graph read equals the specification for every query whose object is concrete and
    whose subject, if starred, is bare — star-BARE subject queries INCLUDED (their probe-1
    source is the `wAny` node the star grants emanate from).

    Probes 3–4 are dead (plain targets); probe 1 glues by the subject-generic chain
    composition (`semAux_of_ruleChain_bs`) and completeness (`nreaches_of_semAux_rulesBS`);
    probe 2 is live exactly for bare concrete subjects — a hit is a STAR-subject chain
    (`wAnyNode s.shape = subjNode ⟨type, *, pred⟩`), transferred to the concrete subject by
    `semAux_star_to_bare`, and dead for userset subjects (edge sources are plain or
    `wAny`-bare, `rulesAdmitted_edge_endpoints_bs`). -/
theorem graph_correct_rulesBS (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hUT : UntaintedSchema S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE) (hqo : q.object.name ≠ STAR)
    (hRA : ReachedByRulesAdmitted σ S T) :
    GraphModel.check σ q = sem S T q := by
  have hInv : Inv S σ := (reachedByRules_inv (reachedByRules_of_admitted hRA)).1
  have hcl := hInv.edgesClosed
  have hchar := rulesAdmitted_edge_endpoints_bs hRA hTT hBS hTS
  -- the read routes to the non-derived probe (untainted schema)
  have hroute : GraphModel.check σ q = GraphModel.probeNonDerived σ q :=
    check_eq_probeNonDerived hInv.schemaEq hUT q
  -- probes 3,4 dead (plain targets)
  have hpAll : ∀ u, σ.reach u (wAllNode q.object.type q.relation) = false := by
    intro u
    cases hcase : σ.reach u (wAllNode q.object.type q.relation) with
    | false => rfl
    | true =>
      exfalso
      have := nreaches_target_plain (fun e he => (hchar e he).2) (reach_sound hcase)
      simp [wAllNode] at this
  have hprobe : GraphModel.probeNonDerived σ q =
      (σ.reach (subjNode q.subject) (objNode q.object q.relation)
       || (q.subject.name != STAR && σ.reach (wAnyNode q.subject.shape)
             (objNode q.object q.relation))) := by
    unfold GraphModel.probeNonDerived
    simp [hpAll]
  -- soundness plumbing: a graph path from a subject node is a `sem` membership
  have hedge_sound : ∀ a b, (a, b) ∈ σ.edges →
      ∃ w ∈ T.flatMap (rewriteClosure S),
        a = subjNode w.subject ∧ b = objNode w.object w.relation := by
    intro a b hab
    obtain ⟨t, ht, u, hu, h1, h2⟩ :=
      reachedByRules_edge_sound (reachedByRules_of_admitted hRA) a b hab
    exact ⟨u, List.mem_flatMap.mpr ⟨t, ht, hu⟩, h1, h2⟩
  have hStrat := stratifiable_untainted hUT
  have hDecl := storeDeclared_of_validRules hSV
  have hsem_of_path : ∀ (s' : SubjectRef),
      NReaches σ.edges (subjNode s') (objNode q.object q.relation) →
      ∃ f, semAux S s' T q f q.object.type q.object.name q.relation = true := by
    intro s' hnr
    obtain ⟨l, hl⟩ := trail_of_nreaches hnr
    have hchain := chainN_of_trail hedge_sound l _ _ hl
    obtain ⟨f, hf⟩ := semAux_of_ruleChain_bs (q := q) hWF hUT hTT hNK hSV hBS hTS
      hchain rfl hqo rfl
    exact ⟨f, hf⟩
  have hstab : ∀ (f : Nat),
      semAux S q.subject T q f q.object.type q.object.name q.relation = true →
      sem S T q = true := by
    intro f hf
    have hsem_f := semAux_mono S (untainted_noExclAll hUT) q.subject T q
      (le_max_left f (fuelBound S T)) _ _ _ hf
    rw [← sem_fuel_stable S T q hStrat hDecl _ (le_max_right f (fuelBound S T))]
    exact hsem_f
  -- forward, probe 1: a path from the subject's own node
  have hfwd1 : NReaches σ.edges (subjNode q.subject) (objNode q.object q.relation) →
      sem S T q = true := by
    intro hnr
    obtain ⟨f, hf⟩ := hsem_of_path q.subject hnr
    exact hstab f hf
  -- forward, probe 2: a path from the shape's wAny node is a star-subject chain
  have hfwd2 : q.subject.name ≠ STAR →
      NReaches σ.edges (wAnyNode q.subject.shape) (objNode q.object q.relation) →
      sem S T q = true := by
    intro hqsn hnr
    -- the source is a wAny edge source, hence bare: q.subject.predicate = BARE
    have hsrc := nreaches_source_char (fun e he => (hchar e he).1) hnr
    have hbare : q.subject.predicate = BARE := by
      rcases hsrc with hpl | ⟨_, hpred⟩
      · simp [wAnyNode] at hpl
      · simpa [wAnyNode, SubjectRef.shape] using hpred
    have hstar_node : wAnyNode q.subject.shape
        = subjNode ⟨q.subject.type, STAR, BARE⟩ := by
      show wAnyNode (q.subject.type, q.subject.predicate) = _
      rw [hbare]
      exact wAnyNode_eq_subjNode q.subject.type BARE
    rw [hstar_node] at hnr
    obtain ⟨f, hf⟩ := hsem_of_path ⟨q.subject.type, STAR, BARE⟩ hnr
    exact hstab f (semAux_star_to_bare hUT rfl hqsn hbare f _ _ _ hf)
  -- backward: a `sem` membership hits probe 1 or probe 2
  have hbwd : sem S T q = true →
      σ.reach (subjNode q.subject) (objNode q.object q.relation) = true
      ∨ (q.subject.name ≠ STAR ∧
         σ.reach (wAnyNode q.subject.shape) (objNode q.object q.relation) = true) := by
    intro hsem
    unfold sem at hsem
    rcases nreaches_of_semAux_rulesBS (q := q) hUT hR hBS hTS hRA hqs _ _ _ _ hqo hsem with
      hL | ⟨h1, _, hR'⟩
    · exact Or.inl (reach_complete hcl hL)
    · exact Or.inr ⟨h1, reach_complete hcl hR'⟩
  rw [hroute, hprobe]
  cases hsemc : sem S T q with
  | true =>
    rcases hbwd hsemc with h | ⟨h1, h2⟩
    · rw [h, Bool.true_or]
    · rw [h2]
      have : (q.subject.name != STAR) = true := by rw [bne_iff_ne]; exact h1
      rw [this]
      simp
  | false =>
    have hn1 : σ.reach (subjNode q.subject) (objNode q.object q.relation) = false := by
      cases hc : σ.reach (subjNode q.subject) (objNode q.object q.relation) with
      | false => rfl
      | true =>
        have := hfwd1 (reach_sound hc)
        rw [hsemc] at this; exact absurd this (by simp)
    have hn2 : (q.subject.name != STAR &&
        σ.reach (wAnyNode q.subject.shape) (objNode q.object q.relation)) = false := by
      by_cases hqsn : q.subject.name = STAR
      · rw [show (q.subject.name != STAR) = false by simpa using hqsn]
        rfl
      · cases hc : σ.reach (wAnyNode q.subject.shape) (objNode q.object q.relation) with
        | false => simp
        | true =>
          have := hfwd2 hqsn (reach_sound hc)
          rw [hsemc] at this; exact absurd this (by simp)
    rw [hn1, hn2]; rfl

end Zanzibar
