import ZanzibarProofs.GraphIndex.RulesChain
import ZanzibarProofs.GraphIndex.RulesSaturate

/-!
# The untainted rule-routing COMPLETENESS groundwork (ROADMAP W2, read half — the `sem ⇒ reach` side)

`RulesChain.lean` closed the W2 *soundness* direction (`reach ⇒ sem`). This file builds
the operational groundwork for the *completeness* direction (`sem ⇒ reach`): the
**admitted** W2 write-closure `ReachedByRulesAdmitted`, on which every materialised
rewrite-closure edge is present (`reachedByRulesAdmitted_edge_complete`). This is the W2
analog of `admitted_edge_complete` (DirectCorrect) / the W1 admitted closures.

`writeRules` folds `writeDirect` over `rewriteClosure S t`; a `writeDirect` is a *guarded*
edge write (cycle-rejection), so edge-completeness needs every write in the fold to be
admitted. `FoldAdmits` records exactly that (faithful to the composed system: a rejected
write raises and rolls back, so a real store never holds a rejected tuple — here, a real
graph never drops an admitted closure edge). Edges are monotone under `writeDirect`, so an
admitted edge, once added, persists through the rest of the fold.

The completeness *core* (`sem ⇒ reach`) — which additionally needs closure-saturation for
the `computed` case (attack-first confirmed the `|keys|+1` bound is sound) — is the
deferred next increment.
-/

namespace Zanzibar

/-! ## Edge monotonicity of the `writeDirect` fold -/

/-- A single `writeDirect` only ever adds edges. -/
theorem writeDirect_edges_mono (σ : GraphState) (t : Tuple) :
    ∀ e ∈ σ.edges, e ∈ (σ.writeDirect t).edges := by
  intro e he
  rw [writeDirect_edges]
  split
  · exact List.mem_cons_of_mem _ he
  · exact he

/-- Folding `writeDirect` over a tuple list only ever adds edges. -/
theorem foldl_writeDirect_edges_mono (us : List Tuple) :
    ∀ {σ : GraphState}, ∀ e ∈ σ.edges,
      e ∈ (us.foldl (fun acc u => acc.writeDirect u) σ).edges := by
  induction us with
  | nil => intro σ e he; exact he
  | cons t rest ih =>
    intro σ e he
    exact ih e (writeDirect_edges_mono σ t e he)

/-! ## The fold-admission predicate -/

/-- **`FoldAdmits σ us`** — folding `writeDirect` over `us` from `σ` admits every write
    (no cycle-rejection anywhere in the fold). The faithful admission condition for the
    rule-routed write: the composed system rolls back a rejected write, so a real graph
    materialises every closure edge. -/
def FoldAdmits : GraphState → List Tuple → Prop
  | _, [] => True
  | σ, u :: rest =>
      σ.admitEdge (subjNode u.subject) (objNode u.object u.relation) = true ∧
      FoldAdmits (σ.writeDirect u) rest

/-- **Fold edge-completeness.** If every write in the fold is admitted, every tuple's
    materialised edge is present in the folded state — its own `writeDirect` adds it
    (admission), and the rest of the fold preserves it (edge monotonicity). -/
theorem foldl_writeDirect_edge_complete (us : List Tuple) :
    ∀ {σ : GraphState}, FoldAdmits σ us →
      ∀ u ∈ us, (subjNode u.subject, objNode u.object u.relation) ∈
        (us.foldl (fun acc u => acc.writeDirect u) σ).edges := by
  induction us with
  | nil => intro σ _ u hu; simp at hu
  | cons t rest ih =>
    intro σ hfa u hu
    obtain ⟨hadm, hrest⟩ := hfa
    rcases List.mem_cons.mp hu with rfl | hmem
    · -- u = t (t eliminated by subst): its edge is added by σ.writeDirect u (admitted),
      -- then preserved by the rest
      have hstep : (subjNode u.subject, objNode u.object u.relation) ∈ (σ.writeDirect u).edges := by
        rw [writeDirect_edges, if_pos hadm]; exact List.mem_cons_self
      exact foldl_writeDirect_edges_mono rest _ hstep
    · -- u ∈ rest: IH on the post-t fold state
      exact ih hrest u hmem

/-! ## The admitted W2 write-closure -/

/-- **`ReachedByRulesAdmitted σ S T`** — `σ` is reached from empty by rule-routed writes
    (`writeRules`) each of whose rewrite-closure fold was fully admitted. The W2 analog of
    `ReachedByAdmitted`; on it the edge set is complete for every materialised closure
    tuple (`reachedByRulesAdmitted_edge_complete`). -/
inductive ReachedByRulesAdmitted : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedByRulesAdmitted (emptyState S) S []
  | step {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hprev : ReachedByRulesAdmitted σ S T)
      (hadm : FoldAdmits σ (rewriteClosure S t)) :
      ReachedByRulesAdmitted (σ.writeRules S t) S (t :: T)

/-- Admitted rule-routed writes are a special case of the W2 write-closure. -/
theorem reachedByRules_of_admitted {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByRulesAdmitted σ S T) : ReachedByRules σ S T := by
  induction h with
  | empty S => exact ReachedByRules.empty S
  | step t _ _ ih => exact ReachedByRules.step t ih

/-- **W2 edge-completeness.** Every tuple in the rewrite-closure of every stored write has
    its materialised edge present. By induction over the admitted write path: a fresh
    write's closure edges are complete via `foldl_writeDirect_edge_complete` (fold
    admission), and old edges are monotone (`foldl_writeDirect_edges_mono`). The
    completeness-half analog of `reachedByRules_edge_sound`. -/
theorem reachedByRulesAdmitted_edge_complete {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByRulesAdmitted σ S T) :
    ∀ t ∈ T, ∀ u ∈ rewriteClosure S t,
      (subjNode u.subject, objNode u.object u.relation) ∈ σ.edges := by
  induction h with
  | empty S => intro t ht; simp at ht
  | @step σ S T t hprev hadm ih =>
    intro t' ht' u hu
    rcases List.mem_cons.mp ht' with rfl | hmem
    · -- t' = t (t eliminated by subst): the just-written closure's edges are complete
      exact foldl_writeDirect_edge_complete (rewriteClosure S t') hadm u hu
    · -- t' ∈ T: old edge, monotone through σ.writeRules S t
      exact foldl_writeDirect_edges_mono (rewriteClosure S t) _ (ih t' hmem u hu)

/-- **Every stored tuple's own edge is present** (the seed case of edge-completeness — the
    `direct`/`ttu` completeness cases consult exactly this). -/
theorem reachedByRulesAdmitted_seed_edge {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByRulesAdmitted σ S T) :
    ∀ t ∈ T, (subjNode t.subject, objNode t.object t.relation) ∈ σ.edges := by
  intro t ht
  exact reachedByRulesAdmitted_edge_complete h t ht t (rewriteClosure_seed S t)

/-! ## Last-edge extraction and the computed-case relation rewrite

The `computed` case of the completeness core reduces `s ∈ (ot, on, r)` — where `r`'s def
carries a `computed r'` arm — to `s ∈ (ot, on, r')` (the fuel IH), which gives a graph
path to `objNode ⟨ot,on⟩ r'`. To redirect that path's endpoint to the `r`-node we perform
**last-edge surgery**: the path's final edge materialises a rewrite-closure tuple `w`
(relation `r'`, object `⟨ot,on⟩`); the computed rewrite of `w` is the tuple `⟨w.subject, r,
w.object⟩`, which saturation keeps in the closure, so *its* edge (into `objNode ⟨ot,on⟩ r`)
is materialised too — swap it in for `w`'s. -/

/-- Every non-empty path exposes its **last edge**: `u →* x → v`. -/
theorem nreaches_last {edges : List (NodeKey × NodeKey)} {u v : NodeKey}
    (h : NReaches edges u v) : ∃ x, NReachesR edges u x ∧ (x, v) ∈ edges := by
  induction h with
  | @edge u v huv => exact ⟨u, Or.inl rfl, huv⟩
  | @head u w v huw _ ih =>
    obtain ⟨x, hux, hxv⟩ := ih
    refine ⟨x, ?_, hxv⟩
    rcases hux with rfl | hux
    · exact Or.inr (NReaches.edge huw)
    · exact Or.inr (NReaches.head huw hux)

/-- Close a reflexive-path with a trailing edge into a proper path. -/
theorem NReachesR.tail_edge {edges : List (NodeKey × NodeKey)} {u x v : NodeKey}
    (h : NReachesR edges u x) (e : (x, v) ∈ edges) : NReaches edges u v := by
  rcases h with rfl | h
  · exact NReaches.edge e
  · exact h.tail e

/-- **The computed-case relation rewrite.** On an admitted, ranked (saturating) W2 state
    over a star-free store, a path to `objNode ⟨ot,on⟩ r'` extends to `objNode ⟨ot,on⟩ r`
    whenever the schema carries the computed rewrite `r ← r'` at `ot`. The path's last
    edge is a closure tuple `w` on relation `r'`; the computed rewrite `⟨w.subject, r,
    w.object⟩` stays in the closure (`rewriteClosure_saturated`), so its edge — into the
    `r`-node — is materialised (`reachedByRulesAdmitted_edge_complete`), and replaces the
    last hop. -/
theorem nreaches_relation_rewrite {σ : GraphState} {S : Schema} {T : Store}
    (hRA : ReachedByRulesAdmitted σ S T) (hR : RewriteRanked S) (hSF : StarFreeStore T)
    {ot on r r' : String} (hon : on ≠ STAR)
    (hrule : (⟨ot, r', r, RuleKind.computed⟩ : RRule) ∈ schemaRewrites S)
    {u : NodeKey} (hnr : NReaches σ.edges u (objNode ⟨ot, on⟩ r')) :
    NReaches σ.edges u (objNode ⟨ot, on⟩ r) := by
  obtain ⟨x, hux, hxlast⟩ := nreaches_last hnr
  -- the last edge materialises a closure tuple w (relation r', object ⟨ot,on⟩)
  obtain ⟨t, ht, w, hw, hxsub, hwobj⟩ :=
    reachedByRules_edge_sound (reachedByRules_of_admitted hRA) x _ hxlast
  have hwon : w.object.name ≠ STAR := rewriteClosure_object hw ▸ (hSF t ht).2
  -- `hwobj : objNode ⟨ot,on⟩ r' = objNode w.object w.relation` (edge-sound reverses it)
  obtain ⟨hobj, hrel⟩ := objNode_inj hon hwon hwobj
  -- the computed rewrite of w is a closure tuple whose edge lands on the r-node
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

/-! ## The completeness core

`sem ⇒ reach` on the W2 fragment, by fuel induction with an inner induction on the def
expr. `direct`/`ttu`/`union` mirror `nreaches_of_semAux` (each stored grant materialises
its own edge — `reachedByRulesAdmitted_seed_edge` / a depth-1 closure member); `computed`
defers to `nreaches_relation_rewrite`. `inter`/`excl` are dead on the untainted fragment. -/

/-- The def a successful lookup returns is a declared def, so its rewrite arms are schema
    rewrites. -/
theorem lookup_exprArms_sub {S : Schema} (hUT : UntaintedSchema S) {ot r : String} {e : Expr}
    (hlk : S.lookup (ot, r) = some e) :
    ∀ a ∈ exprArms ot r e, a ∈ schemaRewrites S := by
  intro a ha
  unfold Schema.lookup at hlk
  cases hf : S.defs.find? (fun p => p.1 = (ot, r)) with
  | none => rw [hf] at hlk; simp at hlk
  | some p =>
    rw [hf] at hlk
    simp only [Option.map_some, Option.some.injEq] at hlk
    have hkey : p.1 = (ot, r) := by simpa using List.find?_some hf
    have hp : p ∈ S.defs := List.mem_of_find?_eq_some hf
    -- the def survives the taint filter: on an untainted schema no key is derived
    have hfilt : (!(isDerived S p.1)) = true := by
      rw [isDerived_untainted hUT p.1]; rfl
    unfold schemaRewrites
    refine List.mem_flatMap.mpr ⟨p, List.mem_filter.mpr ⟨hp, hfilt⟩, ?_⟩
    rw [hkey]; simp only; rw [hlk]; exact ha

/-- A depth-1 rewrite of a tuple is in its own closure (the `ttu` case's rewrite fires on
    the stored seed, at depth 1 — no saturation needed). -/
theorem rewriteStep_mem_closure {S : Schema} {t u : Tuple} (h : u ∈ rewriteStep S t) :
    u ∈ rewriteClosure S t := by
  unfold rewriteClosure
  refine mem_aux_of_stepN S (S.keys.length + 1) 1 [t] (Nat.succ_le_succ (Nat.zero_le _)) ?_
  show u ∈ ([t].flatMap (rewriteStep S))
  exact List.mem_flatMap.mpr ⟨t, List.mem_singleton.mpr rfl, h⟩

/-- **The W2 completeness core.** On an admitted, ranked W2 state over an admission-valid,
    star-free store, a `sem`-membership at any fuel is graph reachability from the query
    subject node to the object node. Fuel induction (outer) × def-expr induction (inner);
    the `computed` arm uses `nreaches_relation_rewrite`, the others append a stored grant's
    materialised edge. -/
theorem nreaches_of_semAux_rules {S : Schema} {T : Store} {q : Query} {σ : GraphState}
    (hUT : UntaintedSchema S) (hR : RewriteRanked S)
    (hSF : StarFreeStore T) (hRA : ReachedByRulesAdmitted σ S T)
    {s : SubjectRef} (hs : s.name ≠ STAR) :
    ∀ (f : Nat) (ot on r : String), on ≠ STAR →
      semAux S s T q f ot on r = true →
      NReaches σ.edges (subjNode s) (objNode ⟨ot, on⟩ r) := by
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
      -- inner induction on the def expr, carrying the rewrite-arm provenance
      have inner : ∀ e', containsBool e' = false →
          (∀ a ∈ exprArms ot r e', a ∈ schemaRewrites S) →
          evalE (semAux S s T q f) s T q ot on r e' = true →
          NReaches σ.edges (subjNode s) (objNode ⟨ot, on⟩ r) := by
        intro e'
        induction e' with
        | direct rs =>
          intro _ _ hdl
          rcases directLeaf_elim hSF hs hdl with ⟨g, hg, hgs⟩ | hmog
          · -- direct match: the grant's own materialised edge
            obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
            have hedge := hedgeSeed g hgT
            have hgon' : g.object.name = on := matchingObjects_elim hgon (hSF g hgT).2
            have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
            rw [hobj, hgrel, hgs] at hedge
            exact NReaches.edge hedge
          · -- flow-through: the recursion's path + the grant's edge
            obtain ⟨g, hg, hpb, hps, hrec⟩ := mog_elim hSF hmog
            obtain ⟨hgT, hgrel, hgot, hgon, _⟩ := grantsOf_elim hg
            have hmid := ih _ _ _ hps hrec
            rw [objNode_eq_subjNode hps] at hmid
            have hedge := hedgeSeed g hgT
            have hgon' : g.object.name = on := matchingObjects_elim hgon (hSF g hgT).2
            have hobj : g.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hgot, ← hgon']
            rw [hobj, hgrel] at hedge
            exact hmid.tail hedge
        | computed r' =>
          intro _ harms hev
          -- evalE (computed r') = semAux ... ot on r'; rewrite the r'-path to the r-node
          have hsub : semAux S s T q f ot on r' = true := hev
          have hpath := ih ot on r' hon hsub
          have hrule : (⟨ot, r', r, RuleKind.computed⟩ : RRule) ∈ schemaRewrites S :=
            harms _ (by simp [exprArms])
          exact nreaches_relation_rewrite hRA hR hSF hon hrule hpath
        | ttu tr ts =>
          intro _ harms hev
          obtain ⟨w, hwT, hwrel, hwot, hwcon, hdisj⟩ := ttuLeaf_elim hSF hev
          -- the ttu rewrite of the stored tupleset tuple w (depth-1 closure member)
          have hrule : (⟨ot, ts, r, RuleKind.ttu tr⟩ : RRule) ∈ schemaRewrites S :=
            harms _ (by simp [exprArms])
          have happly : applyRRule ⟨ot, ts, r, RuleKind.ttu tr⟩ w =
              some ⟨⟨w.subject.type, w.subject.name, tr⟩, r, w.object⟩ := by
            unfold applyRRule; rw [if_pos (by exact ⟨hwrel, hwot⟩)]
          have hw' : (⟨⟨w.subject.type, w.subject.name, tr⟩, r, w.object⟩ : Tuple) ∈
              rewriteStep S w :=
            List.mem_filterMap.mpr ⟨_, hrule, happly⟩
          have hw'cl := rewriteStep_mem_closure hw'
          have hwon : w.object.name = on := matchingObjects_elim hwcon (hSF w hwT).2
          have hedge := reachedByRulesAdmitted_edge_complete hRA w hwT _ hw'cl
          have hobj : w.object = (⟨ot, on⟩ : ObjectRef) := by rw [← hwot, ← hwon]
          rw [hobj] at hedge
          -- edge : subjNode ⟨w.subj.type, w.subj.name, tr⟩ → objNode ⟨ot,on⟩ r
          rcases hdisj with ⟨he1, he2, he3⟩ | hrec
          · -- direct parent-match: s = ⟨w.subj.type, w.subj.name, tr⟩
            have hseq : (⟨w.subject.type, w.subject.name, tr⟩ : SubjectRef) = s := by
              obtain ⟨st, sn, sp⟩ := s
              simp only at he1 he2 he3
              simp [← he1, ← he2, ← he3]
            rw [hseq] at hedge
            exact NReaches.edge hedge
          · -- parent-membership: recurse to the parent userset node, then the edge
            have hwn : w.subject.name ≠ STAR := (hSF w hwT).1
            have hmid := ih w.subject.type w.subject.name tr hwn hrec
            rw [objNode_eq_subjNode hwn] at hmid
            exact hmid.tail hedge
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

/-! ## Wildcard probes are dead on the star-free rule-routed fragment -/

/-- Every edge endpoint of an admitted rule-routed star-free state is a plain node: each
    edge materialises a rewrite-closure tuple, whose subject name (`rewriteClosure_
    subjectName`) and object name (`rewriteClosure_object`) inherit the star-free store. -/
theorem reachedByRulesAdmitted_edges_plain {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByRulesAdmitted σ S T) (hSF : StarFreeStore T) :
    ∀ e ∈ σ.edges, e.1.variant = Variant.plain ∧ e.2.variant = Variant.plain := by
  intro e he
  obtain ⟨t, ht, w, hw, h1, h2⟩ :=
    reachedByRules_edge_sound (reachedByRules_of_admitted h) e.1 e.2 he
  have hws : w.subject.name ≠ STAR := rewriteClosure_subjectName hw ▸ (hSF t ht).1
  have hwo : w.object.name ≠ STAR := rewriteClosure_object hw ▸ (hSF t ht).2
  exact ⟨by rw [h1, subjNode_plain hws], by rw [h2, objNode_plain hwo]⟩

/-! ## T2b on the untainted rule-routed fragment, assembled -/

/-- **T2b, untainted rule-routing fragment (`graph_correct_rules`) — full `check = sem`.**
    On any state reached by admitted rule-routed writes of an admission-valid, star-free
    store over an untainted, directs-only-tupleset, key-unique, rewrite-acyclic schema, the
    graph read equals the specification for every star-free query. The read routes to the
    ≤4-probe `probeNonDerived` (`check_eq_probeNonDerived`); the wildcard probes 2–4 are
    dead (star-free data materialises only plain nodes); probe 1 glues to both directions
    via `reach ↔ NReaches` — soundness `sem_of_rules_reach`, completeness
    `nreaches_of_semAux_rules` + `reach_complete`. Mirror of `graph_correct_direct`,
    widened to `computed`/`ttu`/`union`. -/
theorem graph_correct_rules (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hUT : UntaintedSchema S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hRA : ReachedByRulesAdmitted σ S T) :
    GraphModel.check σ q = sem S T q := by
  have hInv : Inv S σ := (reachedByRules_inv (reachedByRules_of_admitted hRA)).1
  have hcl := hInv.edgesClosed
  have hplain := reachedByRulesAdmitted_edges_plain hRA hSF
  -- the read routes to the non-derived probe (untainted schema)
  have hroute : GraphModel.check σ q = GraphModel.probeNonDerived σ q :=
    check_eq_probeNonDerived hInv.schemaEq hUT q
  -- the wildcard probes are dead (star-free data ⇒ only plain edge endpoints)
  have hpAny : ∀ v, σ.reach (wAnyNode q.subject.shape) v = false := by
    intro v
    cases hcase : σ.reach (wAnyNode q.subject.shape) v with
    | false => rfl
    | true =>
      exfalso
      have hsrc := nreaches_source_plain (fun e he => (hplain e he).1) (reach_sound hcase)
      simp [wAnyNode] at hsrc
  have hpAll : ∀ u, σ.reach u (wAllNode q.object.type q.relation) = false := by
    intro u
    cases hcase : σ.reach u (wAllNode q.object.type q.relation) with
    | false => rfl
    | true =>
      exfalso
      have htgt := nreaches_target_plain (fun e he => (hplain e he).2) (reach_sound hcase)
      simp [wAllNode] at htgt
  have hprobe : GraphModel.probeNonDerived σ q =
      σ.reach (subjNode q.subject) (objNode q.object q.relation) := by
    unfold GraphModel.probeNonDerived
    simp [hpAny, hpAll]
  -- forward: a probe hit is a sem membership
  have hfwd : σ.reach (subjNode q.subject) (objNode q.object q.relation) = true →
      sem S T q = true := fun hr =>
    sem_of_rules_reach hWF hUT hTT hNK hSV hSF hqs hqo
      (reachedByRules_of_admitted hRA) (reach_sound hr)
  -- backward: a sem membership is a probe hit
  have hbwd : sem S T q = true →
      σ.reach (subjNode q.subject) (objNode q.object q.relation) = true := by
    intro hsem
    unfold sem at hsem
    exact reach_complete hcl
      (nreaches_of_semAux_rules hUT hR hSF hRA hqs _ _ _ _ hqo hsem)
  rw [hroute, hprobe]
  cases hrch : σ.reach (subjNode q.subject) (objNode q.object q.relation) with
  | true => exact (hfwd hrch).symm
  | false =>
    cases hsem : sem S T q with
    | false => rfl
    | true => exact absurd (hbwd hsem) (by simp [hrch])

end Zanzibar
