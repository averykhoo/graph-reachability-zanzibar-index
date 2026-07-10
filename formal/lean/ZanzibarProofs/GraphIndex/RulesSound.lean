import ZanzibarProofs.GraphIndex.RulesCorrect
import ZanzibarProofs.GraphIndex.DirectCorrect
import ZanzibarProofs.Spec.WellDef

/-!
# The untainted rule-routing SOUNDNESS core (ROADMAP W2, read half — the `sem` side)

`SEMANTICS.md` §7.5. `RulesWrite.lean` materializes a raw write's rewrite-closure as
ordinary direct edges; `RulesCorrect.lean` routes the read to `probeNonDerived` and
pins every edge to a rewrite-closure tuple (`reachedByRules_edge_sound`). This file
proves the genuinely-new content of the W2 correspondence's **soundness half**: that a
rewrite-closure tuple's materialised edge is a real `sem` membership — i.e. **the
rewrite-closure realises `evalE`'s `computed`/`ttu`/`union` recursion**.

The heart is `semAux_of_rewriteClosure`: for a stored tuple `t` and any `u` in its
rewrite-closure, `sem` derives the membership `u.subject ∈ (u.object, u.relation)` at
*some* fuel. By the closure structure:
* **seed** `u = t` — a direct self-grant (`t`'s relation has a `Direct` arm the subject
  matches: `StoreValidRules`), fuel 1;
* **computed** hop `u = ⟨s, R, o⟩` from `⟨s, R', o⟩` — `evalE`'s `computed R'` case
  `rec o.type o.name R'` is *exactly* the predecessor's membership, fuel `+1`;
* **ttu** hop `u = ⟨s#tr, R, o⟩` from a *stored* tupleset tuple `⟨s, ts, o⟩` — the
  predecessor is the raw seed `t` (`closure_tupleset_is_seed`, under
  `TtuTuplesetsDirect`), so `ttuLeaf`'s stored-tupleset read fires its direct disjunct;
* **union** — a true arm makes the OR-tree true (`evalE_*_arm`).

The chain composition (the userset lift) and the top-level `check = sem` glue are the
deferred next increments.
-/

namespace Zanzibar

/-! ## Key-uniqueness: `sem`'s `lookup` sees the def a rewrite rule came from

`schemaRewrites` fans out over *all* defs (`flatMap`); `sem`/`evalE` reads
`S.lookup key` = the *first* def with that key. To match a rewrite rule against the
def `sem` actually evaluates, keys must be unique — faithful to the Python schema being
a dict (`zanzibar_utils_v1.py`: `compile_ruleset` keys a `dict`). `NodupKeys` records
it; `lookup_of_mem` is the payoff. -/

/-- **`NodupKeys S`** — declared keys are distinct (the Python schema is a dict). -/
def NodupKeys (S : Schema) : Prop := (S.defs.map (·.1)).Nodup

/-- Under `NodupKeys`, a declared def is exactly what `lookup` returns for its key. -/
theorem lookup_of_mem {S : Schema} (h : NodupKeys S) {d : (String × String) × Expr}
    (hd : d ∈ S.defs) : S.lookup d.1 = some d.2 := by
  unfold NodupKeys at h
  unfold Schema.lookup
  suffices hs : ∀ l : List ((String × String) × Expr), (l.map (·.1)).Nodup → d ∈ l →
      l.find? (fun p => p.1 = d.1) = some d by
    rw [hs S.defs h hd]; rfl
  intro l
  induction l with
  | nil => intro _ hd; simp at hd
  | cons a rest ih =>
    intro hnd hd
    simp only [List.map_cons, List.nodup_cons] at hnd
    by_cases hkey : a.1 = d.1
    · rcases List.mem_cons.mp hd with rfl | hmem
      · simp
      · exact absurd (hkey ▸ List.mem_map.mpr ⟨d, hmem, rfl⟩) hnd.1
    · rcases List.mem_cons.mp hd with rfl | hmem
      · exact absurd rfl hkey
      · simp only [List.find?_cons, hkey, decide_false, Bool.false_eq_true]
        exact ih hnd.2 hmem

/-! ## Arm lemmas — a true leaf makes an untainted OR-tree true

`UntaintedSchema` defs are built from `direct`/`computed`/`ttu`/`union` — an OR-tree
of leaves (`evalE (union a b) = evalE a || evalE b`, no `inter`/`excl`). So a single
true leaf makes the whole `evalE` true. `exprDirects` collects the `Direct` arms
(mirroring how `exprArms` collects the `computed`/`ttu` arms). -/

/-- The `Direct` restriction-lists reachable through unions (the storage arms). -/
def exprDirects : Expr → List (List Restriction)
  | .direct rs => [rs]
  | .union a b => exprDirects a ++ exprDirects b
  | .computed _ => []
  | .ttu _ _ => []
  | .inter _ _ => []
  | .excl _ _ => []

/-- **Direct arm ⇒ `evalE` true.** A positive `directLeaf` on a `Direct` arm of `e`
    (reachable through unions) makes `evalE` true. -/
theorem evalE_direct_arm {rec : Rec} {subject : SubjectRef} {T : Store} {q : Query}
    {ot on rel : String} {rs : List Restriction} :
    ∀ e, rs ∈ exprDirects e → directLeaf rec subject T q rs ot on rel = true →
      evalE rec subject T q ot on rel e = true := by
  intro e
  induction e with
  | direct rs' =>
    intro hmem hdl
    simp only [exprDirects, List.mem_singleton] at hmem
    subst hmem; exact hdl
  | computed _ => intro hmem _; simp [exprDirects] at hmem
  | ttu _ _ => intro hmem _; simp [exprDirects] at hmem
  | union a b iha ihb =>
    intro hmem hdl
    simp only [exprDirects, List.mem_append] at hmem
    simp only [evalE, Bool.or_eq_true]
    rcases hmem with h | h
    · exact Or.inl (iha h hdl)
    · exact Or.inr (ihb h hdl)
  | inter _ _ _ _ => intro hmem _; simp [exprDirects] at hmem
  | excl _ _ _ _ => intro hmem _; simp [exprDirects] at hmem

/-- **Computed arm ⇒ `evalE` true.** If `e` carries a `computed mr` leaf (extracted as
    the rule `⟨ot, mr, outRel, computed⟩ ∈ exprArms ot outRel e`) and the recursion
    answers `mr` positively on the object, `evalE` is true. -/
theorem evalE_computed_arm {ot outRel mr : String} :
    ∀ e, (⟨ot, mr, outRel, RuleKind.computed⟩ : RRule) ∈ exprArms ot outRel e →
      ∀ {rec : Rec} {subject : SubjectRef} {T : Store} {q : Query} {on : String},
        rec ot on mr = true → evalE rec subject T q ot on outRel e = true := by
  intro e
  induction e with
  | direct _ => intro hmem; simp [exprArms] at hmem
  | computed r =>
    intro hmem rec subject T q on hrec
    simp only [exprArms, List.mem_singleton, RRule.mk.injEq] at hmem
    obtain ⟨-, hr, -, -⟩ := hmem
    subst hr; exact hrec
  | ttu _ _ =>
    intro hmem; simp [exprArms] at hmem
  | union a b iha ihb =>
    intro hmem rec subject T q on hrec
    simp only [exprArms, List.mem_append] at hmem
    simp only [evalE, Bool.or_eq_true]
    rcases hmem with h | h
    · exact Or.inl (iha h hrec)
    · exact Or.inr (ihb h hrec)
  | inter _ _ _ _ => intro hmem; simp [exprArms] at hmem
  | excl _ _ _ _ => intro hmem; simp [exprArms] at hmem

/-- **TTU arm ⇒ `evalE` true.** If `e` carries a `ttu tr ts` leaf (extracted as
    `⟨ot, ts, outRel, ttu tr⟩ ∈ exprArms ot outRel e`) and `ttuLeaf` answers positively,
    `evalE` is true. -/
theorem evalE_ttu_arm {ot outRel tr ts : String} :
    ∀ e, (⟨ot, ts, outRel, RuleKind.ttu tr⟩ : RRule) ∈ exprArms ot outRel e →
      ∀ {rec : Rec} {subject : SubjectRef} {T : Store} {q : Query} {on : String},
        ttuLeaf rec subject T q tr ts ot on = true →
        evalE rec subject T q ot on outRel e = true := by
  intro e
  induction e with
  | direct _ => intro hmem; simp [exprArms] at hmem
  | computed r =>
    intro hmem; simp [exprArms] at hmem
  | ttu tr' ts' =>
    intro hmem rec subject T q on htl
    simp only [exprArms, List.mem_singleton, RRule.mk.injEq, RuleKind.ttu.injEq] at hmem
    obtain ⟨-, hts, -, htr⟩ := hmem
    subst hts; subst htr; exact htl
  | union a b iha ihb =>
    intro hmem rec subject T q on htl
    simp only [exprArms, List.mem_append] at hmem
    simp only [evalE, Bool.or_eq_true]
    rcases hmem with h | h
    · exact Or.inl (iha h htl)
    · exact Or.inr (ihb h htl)
  | inter _ _ _ _ => intro hmem; simp [exprArms] at hmem
  | excl _ _ _ _ => intro hmem; simp [exprArms] at hmem

/-- A `ttu`-kind rewrite arm of `e` witnesses a `ttu` node of `e`. -/
theorem exprArms_ttu_mem {ot outRel : String} :
    ∀ e {r : RRule}, r ∈ exprArms ot outRel e →
      ∀ tr, r.kind = RuleKind.ttu tr → (tr, r.matchRel) ∈ exprTtus e := by
  intro e
  induction e with
  | direct _ => intro r hr; simp [exprArms] at hr
  | computed _ =>
    intro r hr tr hkind
    simp only [exprArms, List.mem_singleton] at hr; subst hr
    simp at hkind
  | ttu tr' ts' =>
    intro r hr tr hkind
    simp only [exprArms, List.mem_singleton] at hr; subst hr
    simp only [RuleKind.ttu.injEq] at hkind; subst hkind
    simp [exprTtus]
  | union a b iha ihb =>
    intro r hr tr hkind
    simp only [exprArms, List.mem_append] at hr
    simp only [exprTtus, List.mem_append]
    rcases hr with h | h
    · exact Or.inl (iha h tr hkind)
    · exact Or.inr (ihb h tr hkind)
  | inter _ _ _ _ => intro r hr; simp [exprArms] at hr
  | excl _ _ _ _ => intro r hr; simp [exprArms] at hr

/-! ## The W2 read fragment predicates

Untainted rule routing on star-free data. `UntaintedSchema` / `TtuTuplesetsDirect`
are in `RulesCorrect.lean`; here we add the store-validity analog and the
exclusion-free / stratifiable / `StoreDeclared` consequences the soundness assembly
consumes. Wildcards (`W1`) and booleans (`W3`) are out of scope; the combined
generality lands at `W4`. -/

/-- **W2 store admission-validity.** Each stored tuple's `(object.type, relation)` is a
    declared relation whose def carries a `Direct` arm (reachable through unions) the
    tuple's subject matches. The Python write-admission gate routes a raw write onto a
    storage leaf (`RuleSet.apply` + `validate_write_identifiers`); a stored tuple thus
    lands on a relation with a `Direct` restriction it satisfies. -/
def StoreValidRules (S : Schema) (T : Store) : Prop :=
  ∀ t ∈ T, ∃ e rs, S.lookup (t.object.type, t.relation) = some e ∧
    rs ∈ exprDirects e ∧ restrictionMatches rs t = true

/-- `containsBool = false` collapses to `noExcl` (no `inter`/`excl` either). -/
theorem noExcl_of_containsBool_false : ∀ e : Expr, containsBool e = false → e.noExcl := by
  intro e
  induction e with
  | direct _ => intro _; trivial
  | computed _ => intro _; trivial
  | ttu _ _ => intro _; trivial
  | union a b iha ihb =>
    intro h
    simp only [containsBool, Bool.or_eq_false_iff] at h
    exact ⟨iha h.1, ihb h.2⟩
  | inter _ _ _ _ => intro h; simp [containsBool] at h
  | excl _ _ _ _ => intro h; simp [containsBool] at h

/-- An untainted schema is exclusion-free, so `semAux` is fuel-monotone on it. -/
theorem untainted_noExclAll {S : Schema} (h : UntaintedSchema S) : S.noExclAll := by
  intro k e hlk
  unfold Schema.lookup at hlk
  cases hf : S.defs.find? (fun p => p.1 = k) with
  | none => rw [hf] at hlk; simp at hlk
  | some p =>
    rw [hf] at hlk
    simp only [Option.map_some, Option.some.injEq] at hlk
    subst hlk
    exact noExcl_of_containsBool_false _ (h p (List.mem_of_find?_eq_some hf))

/-- An untainted schema is trivially stratifiable (no tainted keys). -/
theorem stratifiable_untainted {S : Schema} (h : UntaintedSchema S) : Stratifiable S := by
  unfold Stratifiable stratify
  rw [taintedKeys_untainted h]
  simp [kahn]

/-- A `Direct` arm's restriction types are among `e`'s `directTypes`. -/
theorem directTypes_mem_of_exprDirects {rs : List Restriction} {x : String} :
    ∀ e, rs ∈ exprDirects e → x ∈ directTypes (Expr.direct rs) → x ∈ directTypes e := by
  intro e
  induction e with
  | direct rs' =>
    intro hmem hx
    simp only [exprDirects, List.mem_singleton] at hmem; subst hmem; exact hx
  | computed _ => intro hmem _; simp [exprDirects] at hmem
  | ttu _ _ => intro hmem _; simp [exprDirects] at hmem
  | union a b iha ihb =>
    intro hmem hx
    simp only [exprDirects, List.mem_append] at hmem
    simp only [directTypes, List.mem_append]
    rcases hmem with h | h
    · exact Or.inl (iha h hx)
    · exact Or.inr (ihb h hx)
  | inter _ _ _ _ => intro hmem _; simp [exprDirects] at hmem
  | excl _ _ _ _ => intro hmem _; simp [exprDirects] at hmem

/-- `StoreValidRules` implies the `StoreDeclared` clause `sem_fuel_stable` needs. -/
theorem storeDeclared_of_validRules {S : Schema} {T : Store}
    (h : StoreValidRules S T) : StoreDeclared S T := by
  intro tup htup
  obtain ⟨e, rs, hlk, hdir, hrm⟩ := h tup htup
  refine ⟨e, hlk, ?_⟩
  obtain ⟨r, hr, htype⟩ := restrictionMatches_type rs tup hrm
  -- the matched restriction's type is `tup.subject.type`, and it lives in `directTypes e`
  have : tup.subject.type ∈ directTypes (Expr.direct rs) := by
    unfold directTypes; exact List.mem_map.mpr ⟨r, hr, htype.symm⟩
  exact directTypes_mem_of_exprDirects e hdir this

/-! ## The heart: every rewrite-closure tuple is a `sem` membership

`semAux_of_rewriteClosure`: for a stored `t` and any `u ∈ rewriteClosure S t`, `sem`
derives `u.subject ∈ (u.object, u.relation)` at some fuel. The proof folds a base case
(the seed is a direct self-grant) with a closure step (a `computed`/`ttu` rewrite of a
member is again a member). The `ttu` step is the only one needing the fragment
condition: it fires on the *stored* tupleset tuple, which `closure_tupleset_is_seed`
(under `TtuTuplesetsDirect`) forces to be the raw seed `t ∈ T`, exactly what `ttuLeaf`'s
stored-tupleset read consults. -/

/-- **Seed membership.** A stored tuple is a fuel-1 `sem` membership of its own object
    node (a direct self-grant on the `Direct` arm the subject matches). -/
theorem semAux_seed {S : Schema} {T : Store} {q : Query}
    (hSV : StoreValidRules S T) (hSF : StarFreeStore T) {t : Tuple} (ht : t ∈ T) :
    semAux S t.subject T q 1 t.object.type t.object.name t.relation = true := by
  obtain ⟨e, rs, hlk, hdir, hrm⟩ := hSV t ht
  rw [semAux, step, hlk]
  refine evalE_direct_arm e hdir ?_
  refine directLeaf_grant_self ?_ rfl (hSF t ht).1
  exact grantsOf_intro ht rfl rfl (matchingObjects_self _ (hSF t ht).2) hrm

/-- The property carried through the closure: a `sem` membership of `w`, plus the
    structural fact that `w` is the raw seed or a rewrite output (needed to rule out a
    deeper tuple sitting on a TTU tupleset relation). -/
private def SemReached (S : Schema) (T : Store) (q : Query) (t w : Tuple) : Prop :=
  (∃ f, semAux S w.subject T q f w.object.type w.object.name w.relation = true) ∧
  (w = t ∨ ∃ r ∈ schemaRewrites S, r.objectType = w.object.type ∧ r.outRel = w.relation)

/-- **The closure step** — a `computed`/`ttu` rewrite of a `SemReached` tuple is a `sem`
    membership. Computed reuses the predecessor's membership under the `computed` arm;
    ttu fires `ttuLeaf`'s stored-tupleset disjunct on the seed. -/
theorem semAux_step {S : Schema} {T : Store} {q : Query} (hNK : NodupKeys S)
    (hTT : TtuTuplesetsDirect S) (hSF : StarFreeStore T) {t : Tuple} (ht : t ∈ T)
    {x u : Tuple} (hx : SemReached S T q t x) (hu : u ∈ rewriteStep S x) :
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
    -- normalise the extracted `(objectType, matchRel)` to `x`'s fields
    rw [← hxot, ← hxrel] at harm'
    rw [← hxot] at hlk
    cases rkind with
    | computed =>
      -- u = ⟨x.subject, rout, x.object⟩
      simp only [Option.some.injEq] at happly
      subst happly
      refine ⟨fx + 1, ?_⟩
      rw [semAux, step, hlk]
      show evalE (semAux S x.subject T q fx) x.subject T q
        x.object.type x.object.name rout d.2 = true
      exact evalE_computed_arm d.2 harm' hfx
    | ttu tr =>
      -- u = ⟨⟨x.subject.type, x.subject.name, tr⟩, rout, x.object⟩
      simp only [Option.some.injEq] at happly
      subst happly
      -- the tupleset tuple `x` must be the stored seed `t`
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
      -- ttuLeaf fires on the stored tupleset tuple x, matched directly (no recursion)
      unfold ttuLeaf
      refine List.any_eq_true.mpr ⟨x, hxT, ?_⟩
      have hcon : (matchingObjects x.object.name).contains x.object.name = true :=
        matchingObjects_self _ (hSF x hxT).2
      rw [if_pos (by simp only [beq_self_eq_true, Bool.and_true, hcon])]
      by_cases hpn : (x.subject.name != STAR) = true
      · rw [if_pos hpn]; simp
      · rw [if_neg hpn]; simp
  · simp at happly

/-- The `SemReached` property is closed along the bounded rewrite closure: seed the
    generalised induction with `SemReached`-tuples and every closure tuple stays one. -/
theorem semAux_of_closureAux {S : Schema} {T : Store} {q : Query} (hNK : NodupKeys S)
    (hTT : TtuTuplesetsDirect S) (hSF : StarFreeStore T) {t : Tuple} (ht : t ∈ T) :
    ∀ (n : Nat) (cur : List Tuple), (∀ w ∈ cur, SemReached S T q t w) →
      ∀ u ∈ rewriteClosureAux S n cur, SemReached S T q t u := by
  intro n
  induction n with
  | zero => intro cur hcur u hu; exact hcur u hu
  | succ m ih =>
    intro cur hcur u hu
    rw [rewriteClosureAux, List.mem_append] at hu
    rcases hu with hin | hrec
    · exact hcur u hin
    · refine ih (cur.flatMap (rewriteStep S)) ?_ u hrec
      intro w hw
      rw [List.mem_flatMap] at hw
      obtain ⟨x, hx, hwx⟩ := hw
      exact ⟨semAux_step hNK hTT hSF ht (hcur x hx) hwx, Or.inr (rewriteStep_outRel hwx)⟩

/-- **The heart of the W2 soundness half.** For a stored `t` and any `u` in its
    rewrite-closure, `sem` derives `u.subject ∈ (u.object, u.relation)` at some fuel —
    the rewrite-closure realises `evalE`'s `computed`/`ttu`/`union` recursion. -/
theorem semAux_of_rewriteClosure {S : Schema} {T : Store} {q : Query} (hNK : NodupKeys S)
    (hTT : TtuTuplesetsDirect S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    {t u : Tuple} (ht : t ∈ T) (hu : u ∈ rewriteClosure S t) :
    ∃ f, semAux S u.subject T q f u.object.type u.object.name u.relation = true := by
  unfold rewriteClosure at hu
  refine (semAux_of_closureAux hNK hTT hSF ht (S.keys.length + 1) [t] ?_ u hu).1
  intro w hw
  rw [List.mem_singleton] at hw; subst hw
  exact ⟨⟨1, semAux_seed hSV hSF ht⟩, Or.inl rfl⟩

end Zanzibar
