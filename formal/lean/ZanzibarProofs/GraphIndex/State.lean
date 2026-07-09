import ZanzibarProofs.Core.Store
import ZanzibarProofs.Spec.Stratify
import ZanzibarProofs.GraphIndex.Closure

/-!
# The graph-index model — state, invariant, read (CONCRETE, Phase 4)

`SEMANTICS.md` §7. Phase 1 stubbed the state, read, invariant, reachability,
quiescence, and scope predicate as `opaque` placeholders so the T2/T5 statements
could compile. **This file replaces all seven with concrete definitions** — the
"concretize + partial proofs" pass. The deep theorems (`graph_correct`,
the `Inv` half of `graph_reached_inv`) remain tracked `sorry`s in `Correct.lean`;
`cascade_converges` and the `Quiescent` half of `graph_reached_inv` are *closed*
here off the concrete `ReachedBy` (the model bakes the in-transaction cascade into
each write — §7.8 / ambiguity A1, user-approved).

## Modeling choices (logged here + PROOF_STATUS)

* **Reads read reachability, not path counts.** The Python index stores `p(u,v)`
  (the path count) for O(1) reads and for the counting-IVM (T4). Semantically,
  `check` only needs *reachability* `p(u,v) > 0`, which is the transitive closure of
  the direct edges. So `GraphState` tracks the **direct edges** and `check` probes
  reachability via a fuel-bounded closure (`reachB`). The path-*counting* layer is a
  separate concern, modeled and proven in `Closure.lean` (T4); factoring it out
  avoids threading a `Fintype NodeKey` (the key space is infinite) through the read
  proof. `Inv.acyclic` pins the DAG property the counting theorem needs.
* **The schema is baked into the state.** `check : GraphState → Query → Bool` takes
  no schema (the compiled artifacts — taint classification, declared shapes — are
  part of the persisted index), so `GraphState` carries `schema` and `Inv S σ`
  pins `σ.schema = S`.
* **`WriteStep` is a minimal operational spec.** It records only the necessary
  postconditions this pass exercises (schema fixed, nodes monotone, the cascade
  drained in-txn). The full add-edge + bridge + reconcile realization is the
  deferred T2a operational content; `graph_reached_inv`'s `Inv` conjunct stays
  `sorry` because those clauses are *not* free from this thin step.
-/

namespace Zanzibar

/-! ## §7.4 — nodes -/

/-- Node variant: an ordinary concrete/userset node, the ∃-wildcard node `w_any`
    (concretes bridge **in**, wildcard-*subject* grants leave), or the ∀-wildcard
    node `w_all` (wildcard-*object* grants arrive, bridges leave) — `SEMANTICS.md`
    §7.4, `models.py:32-36`. -/
inductive Variant where
  | plain | wAny | wAll
deriving DecidableEq, Repr, Inhabited

/-- A materialized graph node key `(type, name, predicate, variant)` (§7.4). The
    Python key's `store` component is dropped (single-store model). The node
    encoding invariant `name == '*' ⟺ variant ≠ plain` lives in `Inv`. -/
structure NodeKey where
  type : String
  name : String
  pred : String
  variant : Variant
deriving DecidableEq, Repr, Inhabited

/-! ## §7.6 — residues -/

/-- A persisted residue `ResidueV1` for a derived `(object node, relation)`
    (§7.6, `models.py:80-107`): the star-covered shapes, the concrete subjects that
    are star-covered-but-excluded (`neg`), and the edge-free userset members
    (`upos`). Membership is `edges ∪ upos ∪ (⋃_{σ∈stars} pop(σ) ∖ neg)`. -/
structure Residue where
  stars : List Shape
  neg   : List SubjectRef
  upos  : List SubjectRef
deriving DecidableEq, Repr, Inhabited

/-- The empty residue (default for a node with no persisted residue). -/
def Residue.empty : Residue := ⟨[], [], []⟩

/-- A delta-outbox row (§7.8, `outbox.py`) — an id plus the `(node, relation)` it
    dirties. Enough structure to state outbox-drain quiescence (I10). -/
structure Delta where
  id : Nat
  node : NodeKey
  relation : String
deriving DecidableEq, Repr, Inhabited

/-! ## §7.1 — the materialized state -/

/-- The materialized graph-index state (§7.1, §7.6, §7.8). Concrete replacement for
    the Phase-1 opaque placeholder. Edges are the direct multigraph edges (as a
    list; reachability is their transitive closure); `residue` maps a derived
    `(object node, relation)` to its residue; `outbox`/`watermark` model the delta
    stream and its drain frontier. -/
structure GraphState where
  schema : Schema
  edges : List (NodeKey × NodeKey)
  nodes : List NodeKey
  residue : NodeKey → String → Option Residue
  outbox : List Delta
  watermark : Nat

/-! ## Node constructors from query endpoints (§7.4, §7.5) -/

/-- The node for a subject reference: a `'*'` subject is its own `w_any` (∃) node;
    a concrete/userset subject is a plain node. -/
def subjNode (s : SubjectRef) : NodeKey :=
  if s.name = STAR then ⟨s.type, STAR, s.predicate, Variant.wAny⟩
  else ⟨s.type, s.name, s.predicate, Variant.plain⟩

/-- The `w_any` (∃) node of a shape `(type, predicate)`. -/
def wAnyNode (sh : Shape) : NodeKey := ⟨sh.1, STAR, sh.2, Variant.wAny⟩

/-- The userset node carrying relation `R` on object `o`: a `'*'` object is its own
    `w_all` (∀) node; a concrete object is a plain node. -/
def objNode (o : ObjectRef) (R : String) : NodeKey :=
  if o.name = STAR then ⟨o.type, STAR, R, Variant.wAll⟩
  else ⟨o.type, o.name, R, Variant.plain⟩

/-- The `w_all` (∀) node for object-wildcard of type `t`, relation `R`. -/
def wAllNode (t R : String) : NodeKey := ⟨t, STAR, R, Variant.wAll⟩

/-! ## Reachability (transitive closure of the direct edges) -/

/-- Fuel-bounded reachability: is there a directed path `u → v` of length `1..fuel`?
    A length-`(k+1)` path is a first edge `u→w` then a length-`k` path `w→v`. -/
def reachB (edges : List (NodeKey × NodeKey)) : Nat → NodeKey → NodeKey → Bool
  | 0, _, _ => false
  | fuel + 1, u, v => edges.any (fun e => e.1 == u && (e.2 == v || reachB edges fuel e.2 v))

/-- The read-side reachability probe `p(u,v) > 0`: a path exists within the node
    count (any longer walk in a DAG would repeat a node). -/
def GraphState.reach (σ : GraphState) (u v : NodeKey) : Bool :=
  reachB σ.edges (σ.nodes.length + 1) u v

/-! ## Fuel-free reachability — the invariant / write-path layer

`GraphState.reach` above is the *executable* probe: a fuel-capped closure whose
fuel is tied to `nodes.length`. For the state invariant and the write-path proofs
it is far cleaner to reason about reachability as a **fuel-free relation**
`NReaches` — the transitive closure of the direct edges (≥ 1 hop). This sidesteps
the `nodes.length`-fuel bookkeeping (adding a node changes the fuel, which would
otherwise perturb a capped probe out from under an acyclicity argument). The bridge
`reach ↔ NReaches` — that the fuel `nodes.length + 1` is always enough — is a
stabilization (pigeonhole) fact needed only by the read theorem T2b, and is
factored there. `Inv` below is stated over `NReaches`. -/

/-- Fuel-free directed reachability: a path of ≥ 1 edge from `u` to `v`. -/
inductive NReaches (edges : List (NodeKey × NodeKey)) : NodeKey → NodeKey → Prop where
  | edge {u v} : (u, v) ∈ edges → NReaches edges u v
  | head {u w v} : (u, w) ∈ edges → NReaches edges w v → NReaches edges u v

/-- Reflexive closure of `NReaches` (a path of ≥ 0 edges). -/
def NReachesR (edges : List (NodeKey × NodeKey)) (u v : NodeKey) : Prop :=
  u = v ∨ NReaches edges u v

/-- Extend a path by one trailing edge. -/
theorem NReaches.tail {edges : List (NodeKey × NodeKey)} {u w v : NodeKey}
    (h : NReaches edges u w) (e : (w, v) ∈ edges) : NReaches edges u v := by
  induction h with
  | edge huw => exact NReaches.head huw (NReaches.edge e)
  | head huw _ ih => exact NReaches.head huw (ih e)

/-- `NReaches` is transitive. -/
theorem NReaches.trans {edges : List (NodeKey × NodeKey)} {u w v : NodeKey}
    (h1 : NReaches edges u w) (h2 : NReaches edges w v) : NReaches edges u v := by
  induction h1 with
  | edge huw => exact NReaches.head huw h2
  | head huw _ ih => exact NReaches.head huw (ih h2)

/-- `NReachesR` is transitive. -/
theorem NReachesR.trans {edges : List (NodeKey × NodeKey)} {u w v : NodeKey}
    (h1 : NReachesR edges u w) (h2 : NReachesR edges w v) : NReachesR edges u v := by
  rcases h1 with rfl | r1
  · exact h2
  · rcases h2 with rfl | r2
    · exact Or.inr r1
    · exact Or.inr (r1.trans r2)

/-- The empty edge set reaches nothing. -/
theorem nreaches_nil (u v : NodeKey) : ¬ NReaches [] u v := by
  intro h; cases h <;> simp_all

/-- Adding an edge never removes reachability. -/
theorem NReaches.mono {edges : List (NodeKey × NodeKey)} {e : NodeKey × NodeKey}
    {u v : NodeKey} (h : NReaches edges u v) : NReaches (e :: edges) u v := by
  induction h with
  | edge huv => exact NReaches.edge (List.mem_cons_of_mem _ huv)
  | head huw _ ih => exact NReaches.head (List.mem_cons_of_mem _ huw) ih

/-- **First-use decomposition.** A path in `(a,b) :: edges` either avoids the new
    edge entirely (a path in the old edges) or factors through it as
    `u →* a → b →* v` (the reflexive-closure legs use only old edges). -/
theorem nreaches_cons_split {edges : List (NodeKey × NodeKey)} {a b u v : NodeKey}
    (h : NReaches ((a, b) :: edges) u v) :
    NReaches edges u v ∨ (NReachesR edges u a ∧ NReachesR edges b v) := by
  induction h with
  | @edge u v huv =>
    rcases List.mem_cons.mp huv with heq | hmem
    · obtain ⟨hu, hv⟩ := Prod.ext_iff.mp heq
      exact Or.inr ⟨Or.inl hu, Or.inl hv.symm⟩
    · exact Or.inl (NReaches.edge hmem)
  | @head u w v huw _ ih =>
    rcases List.mem_cons.mp huw with heq | hmem
    · obtain ⟨hu, hw⟩ := Prod.ext_iff.mp heq
      subst hu; subst hw
      refine Or.inr ⟨Or.inl rfl, ?_⟩
      rcases ih with hl | ⟨_, hr⟩
      · exact Or.inr hl
      · exact hr
    · rcases ih with hl | ⟨hwa, hbv⟩
      · exact Or.inl (NReaches.head hmem hl)
      · refine Or.inr ⟨?_, hbv⟩
        rcases hwa with rfl | hwa'
        · exact Or.inr (NReaches.edge hmem)
        · exact Or.inr (NReaches.head hmem hwa')

/-- **Cycle-rejection preserves acyclicity.** Adding a direct edge `(a,b)` to an
    acyclic edge set keeps it acyclic provided there is no back-path `b →* a` and
    `a ≠ b` — exactly the admission check the write path performs (I2 / §7.7). -/
theorem acyclic_addEdge {edges : List (NodeKey × NodeKey)} {a b : NodeKey}
    (hac : ∀ v, ¬ NReaches edges v v)
    (hback : ¬ NReaches edges b a) (hne : a ≠ b) :
    ∀ v, ¬ NReaches ((a, b) :: edges) v v := by
  intro v hv
  rcases nreaches_cons_split hv with hl | ⟨hva, hbv⟩
  · exact hac v hl
  · have hba : NReachesR edges b a := hbv.trans hva
    rcases hba with heq | hr
    · exact hne heq.symm
    · exact hback hr

/-! ### Bridging the executable probe `reachB` to `NReaches`

`reachB` (fuel-capped) and `NReaches` (fuel-free) agree once the fuel is large
enough. **Soundness** (`reachB → NReaches`) holds at any fuel; **completeness**
(`NReaches → reachB`) needs a fuel bound and is proved below via shortest-walk
compression. Together they let a read theorem move between the executable probe and
the relational invariant. -/

/-- `reachB` is sound for `NReaches` at any fuel. -/
theorem reachB_sound {edges : List (NodeKey × NodeKey)} :
    ∀ (f : Nat) (u v : NodeKey), reachB edges f u v = true → NReaches edges u v := by
  intro f
  induction f with
  | zero => intro u v h; simp [reachB] at h
  | succ f ih =>
    intro u v h
    rw [reachB, List.any_eq_true] at h
    obtain ⟨e, hmem, he⟩ := h
    obtain ⟨e1, e2⟩ := e
    simp only [Bool.and_eq_true, Bool.or_eq_true, beq_iff_eq] at he
    obtain ⟨hu, hv | hr⟩ := he
    · subst hu; subst hv; exact NReaches.edge hmem
    · subst hu; exact NReaches.head hmem (ih e2 v hr)

/-- `reachB` is monotone in fuel (one step). -/
theorem reachB_mono_succ {edges : List (NodeKey × NodeKey)} :
    ∀ (f : Nat) (u v : NodeKey),
      reachB edges f u v = true → reachB edges (f + 1) u v = true := by
  intro f
  induction f with
  | zero => intro u v h; simp [reachB] at h
  | succ f ih =>
    intro u v h
    rw [reachB, List.any_eq_true] at h ⊢
    obtain ⟨e, hmem, he⟩ := h
    refine ⟨e, hmem, ?_⟩
    obtain ⟨e1, e2⟩ := e
    simp only [Bool.and_eq_true, Bool.or_eq_true, beq_iff_eq] at he ⊢
    obtain ⟨hu, hv | hr⟩ := he
    · exact ⟨hu, Or.inl hv⟩
    · exact ⟨hu, Or.inr (ih e2 v hr)⟩

/-- `reachB` is monotone in fuel. -/
theorem reachB_mono {edges : List (NodeKey × NodeKey)} {f f' : Nat} (hle : f ≤ f')
    {u v : NodeKey} (h : reachB edges f u v = true) : reachB edges f' u v = true := by
  induction hle with
  | refl => exact h
  | step _ ih => exact reachB_mono_succ _ _ _ ih

/-- **Completeness at some fuel.** Every `NReaches` path is found by `reachB` at a
    (sufficiently large, path-length) fuel. -/
theorem reachB_of_nreaches {edges : List (NodeKey × NodeKey)} {u v : NodeKey}
    (h : NReaches edges u v) : ∃ f, reachB edges f u v = true := by
  induction h with
  | @edge u v huv =>
    exact ⟨1, by rw [reachB, List.any_eq_true]; exact ⟨(u, v), huv, by simp [reachB]⟩⟩
  | @head u w v huw _ ih =>
    obtain ⟨f, hf⟩ := ih
    exact ⟨f + 1, by rw [reachB, List.any_eq_true]; exact ⟨(u, w), huw, by simp [hf]⟩⟩

/-- **`reachB` and `NReaches` describe the same relation** (at unbounded fuel). The
    remaining bridge for the *executable* probe `σ.reach` (fixed fuel
    `nodes.length + 1`) is the shortest-walk length bound, factored into T2b. -/
theorem nreaches_iff_reachB {edges : List (NodeKey × NodeKey)} {u v : NodeKey} :
    NReaches edges u v ↔ ∃ f, reachB edges f u v = true :=
  ⟨reachB_of_nreaches, fun ⟨_, hf⟩ => reachB_sound _ _ _ hf⟩

/-- The executable probe is sound for `NReaches`: a `reach` hit is a genuine path. -/
theorem reach_sound {σ : GraphState} {u v : NodeKey}
    (h : σ.reach u v = true) : NReaches σ.edges u v :=
  reachB_sound _ _ _ h

/-! ### Shortest-walk compression — the fixed-fuel bridge

To move `NReaches` into the *executable* probe `σ.reach` (fuel `nodes.length + 1`)
we bound the walk length: a walk whose intermediate vertices all lie in `nodes`
compresses (pigeonhole: a repeat gives a removable cycle) to one with
`≤ nodes.length` intermediates, which `reachB` finds within `nodes.length + 1`
fuel. This is the stabilization the ROADMAP flagged as T2b's blocker. -/

/-- A directed walk `u → v` with intermediate vertices `l` (excluding endpoints):
    `Trail edges u v []` is a single edge `u→v`; `Trail edges u v (x :: xs)` is a
    first edge `u→x` then a trail `x → v`. -/
def Trail (edges : List (NodeKey × NodeKey)) : NodeKey → NodeKey → List NodeKey → Prop
  | u, v, [] => (u, v) ∈ edges
  | u, v, x :: xs => (u, x) ∈ edges ∧ Trail edges x v xs

/-- Split a trail at an interior vertex: `u →* v` through `x` factors as `u →* x`
    then `x →* v`, with intermediates `p` and `s`. -/
theorem trail_split (edges : List (NodeKey × NodeKey)) (x v : NodeKey) (p : List NodeKey) :
    ∀ (u : NodeKey) (s : List NodeKey),
      Trail edges u v (p ++ x :: s) ↔ (Trail edges u x p ∧ Trail edges x v s) := by
  induction p with
  | nil => intro u s; simp [Trail]
  | cons a p ih =>
    intro u s
    simp only [List.cons_append, Trail]
    rw [ih a s]
    tauto

/-- `reachB` finds a trail within `length + 1` fuel. -/
theorem reachB_of_trail {edges : List (NodeKey × NodeKey)} :
    ∀ (l : List NodeKey) (u v : NodeKey),
      Trail edges u v l → reachB edges (l.length + 1) u v = true := by
  intro l
  induction l with
  | nil =>
    intro u v ht
    rw [reachB, List.any_eq_true]
    exact ⟨(u, v), ht, by simp [reachB]⟩
  | cons x xs ih =>
    intro u v ht
    obtain ⟨hux, htail⟩ := ht
    have hrec := ih x v htail
    simp only [List.length_cons]
    rw [reachB, List.any_eq_true]
    exact ⟨(u, x), hux, by simp [hrec]⟩

/-- Every `NReaches` path is realized by a trail. -/
theorem trail_of_nreaches {edges : List (NodeKey × NodeKey)} {u v : NodeKey}
    (h : NReaches edges u v) : ∃ l, Trail edges u v l := by
  induction h with
  | @edge u v huv => exact ⟨[], huv⟩
  | @head u w v huw _ ih => obtain ⟨l, hl⟩ := ih; exact ⟨w :: l, huw, hl⟩

/-- A trail's interior vertices are all live nodes (from endpoint-closure). -/
theorem trail_verts_mem {edges : List (NodeKey × NodeKey)} {N : List NodeKey}
    (hcl : ∀ e ∈ edges, e.1 ∈ N ∧ e.2 ∈ N) :
    ∀ (l : List NodeKey) (u v : NodeKey), Trail edges u v l → ∀ x ∈ l, x ∈ N := by
  intro l
  induction l with
  | nil => intro u v _ x hx; simp at hx
  | cons a xs ih =>
    intro u v ht x hx
    obtain ⟨hua, htail⟩ := ht
    rcases List.mem_cons.mp hx with hxa | hxs
    · rw [hxa]; exact (hcl (u, a) hua).2
    · exact ih a v htail x hxs

/-- A member splits its list: `a ∈ l → l = s ++ a :: t`. -/
theorem mem_split_aux {α : Type} {a : α} :
    ∀ {l : List α}, a ∈ l → ∃ s t, l = s ++ a :: t := by
  intro l
  induction l with
  | nil => intro h; simp at h
  | cons b t ih =>
    intro h
    rcases List.mem_cons.mp h with rfl | hmem
    · exact ⟨[], t, rfl⟩
    · obtain ⟨s, t', rfl⟩ := ih hmem
      exact ⟨b :: s, t', rfl⟩

/-- A duplicated element splits a non-`Nodup` list around its two occurrences. -/
theorem exists_dup_split {α : Type} [DecidableEq α] :
    ∀ (l : List α), ¬ l.Nodup → ∃ (x : α) (p q r : List α), l = p ++ x :: q ++ x :: r := by
  intro l
  induction l with
  | nil => intro h; exact absurd List.nodup_nil h
  | cons a t ih =>
    intro h
    by_cases ha : a ∈ t
    · obtain ⟨q, r, rfl⟩ := mem_split_aux ha
      exact ⟨a, [], q, r, by simp⟩
    · have ht : ¬ t.Nodup := fun ht => h (List.nodup_cons.mpr ⟨ha, ht⟩)
      obtain ⟨x, p, q, r, rfl⟩ := ih ht
      exact ⟨x, a :: p, q, r, by simp⟩

/-- A `Nodup` list whose elements lie in `N` is no longer than `N`. -/
theorem nodup_len_le {α : Type} [DecidableEq α] {l N : List α} (hnd : l.Nodup)
    (hsub : ∀ x ∈ l, x ∈ N) : l.length ≤ N.length := by
  have h1 : l.toFinset.card = l.length := List.toFinset_card_of_nodup hnd
  have h2 : l.toFinset ⊆ N.toFinset := by
    intro x hx; simp only [List.mem_toFinset] at hx ⊢; exact hsub x hx
  calc l.length = l.toFinset.card := h1.symm
    _ ≤ N.toFinset.card := Finset.card_le_card h2
    _ ≤ N.length := List.toFinset_card_le N

/-- **Shortest-walk compression.** A trail with interior vertices in `N` compresses
    to one with `≤ N.length` interior vertices (repeats give removable cycles). -/
theorem trail_compress {edges : List (NodeKey × NodeKey)} {N : List NodeKey} {u v : NodeKey} :
    ∀ (n : Nat) (l : List NodeKey), l.length ≤ n → Trail edges u v l →
      (∀ x ∈ l, x ∈ N) → ∃ l', Trail edges u v l' ∧ l'.length ≤ N.length := by
  intro n
  induction n with
  | zero =>
    intro l hlen ht _
    cases l with
    | nil => exact ⟨[], ht, Nat.zero_le _⟩
    | cons a t => simp only [List.length_cons] at hlen; omega
  | succ n ih =>
    intro l hlen ht hsub
    by_cases hnd : l.Nodup
    · exact ⟨l, ht, nodup_len_le hnd hsub⟩
    · obtain ⟨x, p, q, r, rfl⟩ := exists_dup_split l hnd
      -- `p ++ x :: q ++ x :: r`  parses as  `(p ++ x :: q) ++ x :: r`
      -- split at the SECOND x, then at the FIRST x, dropping the `x →* x` cycle `q`.
      have hcut : Trail edges u x (p ++ x :: q) ∧ Trail edges x v r :=
        (trail_split edges x v (p ++ x :: q) u r).mp ht
      have hcut2 : Trail edges u x p ∧ Trail edges x x q :=
        (trail_split edges x x p u q).mp hcut.1
      have hshort : Trail edges u v (p ++ x :: r) :=
        (trail_split edges x v p u r).mpr ⟨hcut2.1, hcut.2⟩
      have hlen2 : (p ++ x :: r).length ≤ n := by
        simp only [List.length_append, List.length_cons] at hlen ⊢
        omega
      have hsub2 : ∀ y ∈ p ++ x :: r, y ∈ N := by
        intro y hy
        apply hsub y
        simp only [List.mem_append, List.mem_cons] at hy ⊢
        tauto
      exact ih (p ++ x :: r) hlen2 hshort hsub2

/-- **The executable probe is complete for `NReaches`** on any endpoint-closed state:
    a genuine path is found by `σ.reach` at fuel `nodes.length + 1`. With
    `reach_sound`, `σ.reach u v = true ↔ NReaches σ.edges u v`. -/
theorem reach_complete {σ : GraphState}
    (hcl : ∀ e ∈ σ.edges, e.1 ∈ σ.nodes ∧ e.2 ∈ σ.nodes) {u v : NodeKey}
    (hr : NReaches σ.edges u v) : σ.reach u v = true := by
  obtain ⟨l, hl⟩ := trail_of_nreaches hr
  have hsub : ∀ x ∈ l, x ∈ σ.nodes := trail_verts_mem hcl l u v hl
  obtain ⟨l', hl', hlen⟩ := trail_compress l.length l (le_refl _) hl hsub
  have hb := reachB_of_trail l' u v hl'
  have : reachB σ.edges (σ.nodes.length + 1) u v = true := reachB_mono (by omega) hb
  simpa [GraphState.reach] using this

/-- The executable probe exactly decides `NReaches` on an endpoint-closed state. -/
theorem reach_iff_nreaches {σ : GraphState}
    (hcl : ∀ e ∈ σ.edges, e.1 ∈ σ.nodes ∧ e.2 ∈ σ.nodes) {u v : NodeKey} :
    σ.reach u v = true ↔ NReaches σ.edges u v :=
  ⟨reach_sound, reach_complete hcl⟩

/-! ## §7.5, §7.6 — the read `GraphModel.check` -/

namespace GraphModel

/-- Non-derived read: the ≤4 candidate probes (§7.5, `wildcard.py:354-374`).
    `(s,o)`, `(w_any(shape s), o)`, `(s, w_all(o.type,R))`, `(w_any, w_all)`,
    each `p>0`, OR-combined. A literal `'*'` endpoint IS its own variant node and so
    skips its own extra probe (the `!= STAR` guards). A key whose node is absent
    contributes `reach = false` (ghost coverage) automatically. -/
def probeNonDerived (σ : GraphState) (q : Query) : Bool :=
  let s := q.subject
  let o := q.object
  let R := q.relation
  let sN := subjNode s
  let oN := objNode o R
  σ.reach sN oN
  || (s.name != STAR && σ.reach (wAnyNode s.shape) oN)
  || (o.name != STAR && σ.reach sN (wAllNode o.type R))
  || (s.name != STAR && o.name != STAR && σ.reach (wAnyNode s.shape) (wAllNode o.type R))

/-- Derived read: the residue path (§7.6, `wildcard.py:398-432`). An object wildcard
    on a derived relation is rejected (decision-15) ⇒ `False`. A `'*'` subject checks
    shape-star coverage. A userset subject is edge-free: in `upos` ⇒ True, else
    shape not covered ⇒ False, else not excluded. A bare subject probes its derived
    edge first (an edge hit returns True **without** consulting `neg` — the I6
    disjointness), else falls back to `stars ∖ neg`. -/
def probeDerived (σ : GraphState) (q : Query) : Bool :=
  let s := q.subject
  let o := q.object
  let R := q.relation
  if o.name == STAR then false
  else
    let oN := objNode o R
    let res := (σ.residue oN R).getD Residue.empty
    if s.name == STAR then
      res.stars.contains s.shape
    else if s.predicate != BARE then
      if res.upos.contains s then true
      else if !res.stars.contains s.shape then false
      else !res.neg.contains s
    else
      σ.reach (subjNode s) oN || (res.stars.contains s.shape && !res.neg.contains s)

/-- The graph-index `check` (§7.5–7.6): route by whether the queried relation is
    derived (tainted). The schema is read off the baked-in `σ.schema`. -/
def check (σ : GraphState) (q : Query) : Bool :=
  if isDerived σ.schema (q.object.type, q.relation) then
    probeDerived σ q
  else
    probeNonDerived σ q

end GraphModel

/-! ## §8 — the graph scope predicate `GraphAccepts` (decision-15) -/

/-- All `Direct` restrictions occurring anywhere in an expression. -/
def exprRestrictions : Expr → List Restriction
  | .direct rs => rs
  | .computed _ => []
  | .ttu _ _ => []
  | .union a b => exprRestrictions a ++ exprRestrictions b
  | .inter a b => exprRestrictions a ++ exprRestrictions b
  | .excl a b => exprRestrictions a ++ exprRestrictions b

/-- All TTU nodes `(targetRel, tuplesetRel)` occurring anywhere in an expression. -/
def exprTtus : Expr → List (String × String)
  | .direct _ => []
  | .computed _ => []
  | .ttu tr ts => [(tr, ts)]
  | .union a b => exprTtus a ++ exprTtus b
  | .inter a b => exprTtus a ++ exprTtus b
  | .excl a b => exprTtus a ++ exprTtus b

/-- **`GraphAccepts S`** — the decision-15 scope predicate (`SEMANTICS.md` §8,
    `boolean-ivm-spec §1.15`): (1) no object-wildcard shape on a derived relation;
    (2) no wildcard *userset* restriction referencing a derived relation; (3) no TTU
    whose tupleset relation is derived. Outside this scope the graph rejects the
    schema at compile. -/
def GraphAccepts (S : Schema) : Prop :=
  (∀ tr ∈ S.objectWildcards, isDerived S tr = false)
  ∧ (∀ d ∈ S.defs, ∀ r ∈ exprRestrictions d.2,
       r.2.2 = true → r.2.1 ≠ BARE → isDerived S (r.1, r.2.1) = false)
  ∧ (∀ d ∈ S.defs, ∀ tt ∈ exprTtus d.2, isDerived S (d.1.1, tt.2) = false)

/-! ## §7.8 — cascade quiescence -/

/-- **`Quiescent σ`** (I9 / §7.8): the outbox is fully drained — no delta sits above
    the watermark, i.e. `run_cascade` has advanced the frontier past every dirtied
    row. This is the in-transaction fixpoint condition the model bakes into each
    write; the full "a second reconcile changes nothing" characterization is the
    deferred T5 content. -/
def Quiescent (σ : GraphState) : Prop :=
  ∀ d ∈ σ.outbox, d.id ≤ σ.watermark

/-! ## §7.7 — the state invariant `Inv` -/

/-- **`Inv S σ`** — the concretely-expressible core of the I-series (§7.7,
    `invariants.py`). Named clauses so a proof can use exactly the piece it needs:

    * `schemaEq` — the state was built for `S`.
    * `nodeEnc` — node encoding (`:83-87`): `name == '*' ⟺ variant ≠ plain`.
    * `edgesClosed` — I1 endpoint existence (`:89-101`): both ends of a direct edge
      are live nodes.
    * `acyclic` — I2 (`:103-128`): the direct-edge graph is a DAG (no self-reach).
    * `negStarCovered` / `negEdgeFree` / `uposEdgeFree` / `uposNegDisjoint` — I6
      residue hygiene (`:220-273`): `neg ⊆ star-covered`, `neg ∩ edge-holders = ∅`
      (the load-bearing disjointness the bare edge-hit relies on), `upos ∩
      edge-holders = ∅`, `upos ∩ neg = ∅`.

    The path-count algebra (I1's `p ≥ d`), refcounts (I13), and the full bridge
    completeness (I3) are counting/structural facts factored to `Closure.lean` (T4)
    and the deferred T2a; they are not restated here. -/
structure Inv (S : Schema) (σ : GraphState) : Prop where
  schemaEq : σ.schema = S
  nodeEnc : ∀ k ∈ σ.nodes, (k.name = STAR ↔ k.variant ≠ Variant.plain)
  edgesClosed : ∀ e ∈ σ.edges, e.1 ∈ σ.nodes ∧ e.2 ∈ σ.nodes
  acyclic : ∀ v, ¬ NReaches σ.edges v v
  negStarCovered : ∀ k r res, σ.residue k r = some res →
      ∀ n ∈ res.neg, res.stars.contains n.shape = true
  negEdgeFree : ∀ k r res, σ.residue k r = some res →
      ∀ n ∈ res.neg, ¬ NReaches σ.edges (subjNode n) k
  uposEdgeFree : ∀ k r res, σ.residue k r = some res →
      ∀ n ∈ res.upos, ¬ NReaches σ.edges (subjNode n) k
  uposNegDisjoint : ∀ k r res, σ.residue k r = some res →
      ∀ n ∈ res.upos, res.neg.contains n = false

/-! ## §7.8 — reachable states -/

/-- The empty index state for schema `S` (the `build_index` seed). -/
def emptyState (S : Schema) : GraphState :=
  { schema := S, edges := [], nodes := [], residue := fun _ _ => none,
    outbox := [], watermark := 0 }

/-- **`WriteStep S σ σ' t`** — one accepted write incorporating tuple `t` (§7.8).
    A minimal *operational spec*: the schema is fixed, existing nodes persist, and
    the in-transaction cascade leaves the outbox drained (§7.8 / A1 — the model bakes
    the cascade into every write). The full edge/bridge/reconcile realization (and
    hence the preservation of the remaining `Inv` clauses) is the deferred T2a
    content, so this step deliberately does *not* assert `Inv`. -/
structure WriteStep (S : Schema) (σ σ' : GraphState) (t : Tuple) : Prop where
  schemaEq : σ'.schema = σ.schema
  monoNodes : ∀ k ∈ σ.nodes, k ∈ σ'.nodes
  drained : ∀ d ∈ σ'.outbox, d.id ≤ σ'.watermark

/-- **`ReachedBy σ S T`** — `σ` is reached by applying `T`'s writes (each with its
    in-transaction cascade) from the empty state, under schema `S`. The transitive
    closure of `WriteStep` from `emptyState`. -/
inductive ReachedBy : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedBy (emptyState S) S []
  | step {σ σ' : GraphState} {S : Schema} {T : Store} (t : Tuple) :
      ReachedBy σ S T → WriteStep S σ σ' t → ReachedBy σ' S (t :: T)

/-! ## Partial results (this pass) -/

/-- Reachability in the empty edge set is always `false`. -/
theorem reachB_nil (f : Nat) (u v : NodeKey) : reachB [] f u v = false := by
  cases f <;> rfl

/-- The empty state reaches nothing. -/
theorem reach_empty (S : Schema) (u v : NodeKey) : (emptyState S).reach u v = false := by
  unfold GraphState.reach emptyState
  exact reachB_nil _ _ _

/-- The empty state satisfies `Inv` (the `build_index` base case). -/
theorem inv_empty (S : Schema) : Inv S (emptyState S) where
  schemaEq := rfl
  nodeEnc := by intro k hk; simp [emptyState] at hk
  edgesClosed := by intro e he; simp [emptyState] at he
  acyclic := fun v => nreaches_nil v v
  negStarCovered := by intro k r res h; simp [emptyState] at h
  negEdgeFree := by intro k r res h; simp [emptyState] at h
  uposEdgeFree := by intro k r res h; simp [emptyState] at h
  uposNegDisjoint := by intro k r res h; simp [emptyState] at h

/-- The empty state is quiescent. -/
theorem quiescent_empty (S : Schema) : Quiescent (emptyState S) := by
  intro d hd; simp [emptyState] at hd

/-! ## Write-path primitives and invariant preservation (§7.8, T2a)

The write path is realized here as three primitive state mutations, each proved to
preserve the invariant clauses it can affect:

* `addNode` / `addEdge` maintain the **structural** invariant `StructInv` (schema,
  node-encoding, endpoint-closure, acyclicity). `addEdge`'s acyclicity step is
  exactly the cycle-rejection admission check (`acyclic_addEdge`: no back-path
  `b →* a` and `a ≠ b`).
* `putResidue` preserves the **whole** invariant `Inv`, provided the residue it
  writes is I6-hygienic at its key (reconcile's per-key correctness spec) — the
  other keys are untouched, and edges/nodes are unchanged.

What these do **not** yet close is the residue conjuncts of `Inv` under `addEdge`:
adding an edge can make an existing residue's `neg`/`upos` subject edge-reachable
(breaking `negEdgeFree`/`uposEdgeFree`) until the cascade re-reconciles. Realizing
that global reconcile (so a whole write re-establishes I6) is the remaining T2a
content; it needs the `reach ↔ NReaches` bridge, deferred with T2b. -/

/-- Add a live node. -/
def GraphState.addNode (σ : GraphState) (k : NodeKey) : GraphState :=
  { σ with nodes := k :: σ.nodes }

/-- Add one direct edge `a → b`. -/
def GraphState.addEdge (σ : GraphState) (a b : NodeKey) : GraphState :=
  { σ with edges := (a, b) :: σ.edges }

/-- Overwrite the residue at `(k, r)` (reconcile of one derived key). -/
def GraphState.putResidue (σ : GraphState) (k : NodeKey) (r : String) (res : Residue) :
    GraphState :=
  { σ with residue := fun k' r' => if k' = k ∧ r' = r then some res else σ.residue k' r' }

@[simp] theorem addNode_edges (σ : GraphState) (k : NodeKey) :
    (σ.addNode k).edges = σ.edges := rfl
@[simp] theorem addNode_residue (σ : GraphState) (k : NodeKey) :
    (σ.addNode k).residue = σ.residue := rfl
@[simp] theorem addNode_schema (σ : GraphState) (k : NodeKey) :
    (σ.addNode k).schema = σ.schema := rfl
@[simp] theorem addNode_nodes (σ : GraphState) (k : NodeKey) :
    (σ.addNode k).nodes = k :: σ.nodes := rfl
@[simp] theorem addEdge_nodes (σ : GraphState) (a b : NodeKey) :
    (σ.addEdge a b).nodes = σ.nodes := rfl
@[simp] theorem addEdge_residue (σ : GraphState) (a b : NodeKey) :
    (σ.addEdge a b).residue = σ.residue := rfl
@[simp] theorem addEdge_schema (σ : GraphState) (a b : NodeKey) :
    (σ.addEdge a b).schema = σ.schema := rfl
@[simp] theorem addEdge_edges (σ : GraphState) (a b : NodeKey) :
    (σ.addEdge a b).edges = (a, b) :: σ.edges := rfl
@[simp] theorem putResidue_edges (σ : GraphState) (k : NodeKey) (r : String) (res : Residue) :
    (σ.putResidue k r res).edges = σ.edges := rfl
@[simp] theorem putResidue_nodes (σ : GraphState) (k : NodeKey) (r : String) (res : Residue) :
    (σ.putResidue k r res).nodes = σ.nodes := rfl
@[simp] theorem putResidue_schema (σ : GraphState) (k : NodeKey) (r : String) (res : Residue) :
    (σ.putResidue k r res).schema = σ.schema := rfl
theorem putResidue_residue (σ : GraphState) (k : NodeKey) (r : String) (res : Residue)
    (k' : NodeKey) (r' : String) :
    (σ.putResidue k r res).residue k' r' =
      if k' = k ∧ r' = r then some res else σ.residue k' r' := rfl

/-- **`StructInv S σ`** — the structural (edge/node) core of `Inv`: everything
    independent of the residue table. `addNode`/`addEdge` preserve exactly this. -/
structure StructInv (S : Schema) (σ : GraphState) : Prop where
  schemaEq : σ.schema = S
  nodeEnc : ∀ k ∈ σ.nodes, (k.name = STAR ↔ k.variant ≠ Variant.plain)
  edgesClosed : ∀ e ∈ σ.edges, e.1 ∈ σ.nodes ∧ e.2 ∈ σ.nodes
  acyclic : ∀ v, ¬ NReaches σ.edges v v

/-- The structural clauses are part of `Inv`. -/
theorem Inv.toStruct {S : Schema} {σ : GraphState} (h : Inv S σ) : StructInv S σ :=
  ⟨h.schemaEq, h.nodeEnc, h.edgesClosed, h.acyclic⟩

/-- Adding a live node (encoding-valid) preserves the structural invariant. -/
theorem structInv_addNode {S : Schema} {σ : GraphState} (h : StructInv S σ) {k : NodeKey}
    (hk : k.name = STAR ↔ k.variant ≠ Variant.plain) : StructInv S (σ.addNode k) where
  schemaEq := h.schemaEq
  nodeEnc := by
    intro k' hk'
    rw [addNode_nodes] at hk'
    rcases List.mem_cons.mp hk' with rfl | hmem
    · exact hk
    · exact h.nodeEnc k' hmem
  edgesClosed := by
    intro e he
    rw [addNode_edges] at he
    obtain ⟨h1, h2⟩ := h.edgesClosed e he
    exact ⟨List.mem_cons_of_mem _ h1, List.mem_cons_of_mem _ h2⟩
  acyclic := h.acyclic

/-- **Cycle-rejection preserves the structural invariant.** Adding `a → b` between
    two live nodes with no back-path `b →* a` and `a ≠ b` keeps `StructInv`. -/
theorem structInv_addEdge {S : Schema} {σ : GraphState} (h : StructInv S σ) {a b : NodeKey}
    (ha : a ∈ σ.nodes) (hb : b ∈ σ.nodes)
    (hback : ¬ NReaches σ.edges b a) (hne : a ≠ b) : StructInv S (σ.addEdge a b) where
  schemaEq := h.schemaEq
  nodeEnc := h.nodeEnc
  edgesClosed := by
    intro e he
    rw [addEdge_edges] at he
    rcases List.mem_cons.mp he with rfl | hmem
    · exact ⟨ha, hb⟩
    · exact h.edgesClosed e hmem
  acyclic := by
    rw [addEdge_edges]
    exact acyclic_addEdge h.acyclic hback hne

/-- **Reconcile of one key preserves the full invariant.** Writing an I6-hygienic
    residue at `(k, r)` — `neg` star-covered, `neg`/`upos` edge-free, `upos`
    disjoint from `neg` — keeps `Inv`: the other keys are untouched and edges/nodes
    are unchanged. -/
theorem inv_putResidue {S : Schema} {σ : GraphState} (h : Inv S σ)
    {k : NodeKey} {r : String} {res : Residue}
    (hns : ∀ n ∈ res.neg, res.stars.contains n.shape = true)
    (hnf : ∀ n ∈ res.neg, ¬ NReaches σ.edges (subjNode n) k)
    (huf : ∀ n ∈ res.upos, ¬ NReaches σ.edges (subjNode n) k)
    (hun : ∀ n ∈ res.upos, res.neg.contains n = false) :
    Inv S (σ.putResidue k r res) where
  schemaEq := h.schemaEq
  nodeEnc := h.nodeEnc
  edgesClosed := h.edgesClosed
  acyclic := h.acyclic
  negStarCovered := by
    intro k' r' res' hr' n hn
    rw [putResidue_residue] at hr'
    by_cases hkey : k' = k ∧ r' = r
    · rw [if_pos hkey] at hr'
      obtain rfl := Option.some.inj hr'
      exact hns n hn
    · rw [if_neg hkey] at hr'; exact h.negStarCovered k' r' res' hr' n hn
  negEdgeFree := by
    intro k' r' res' hr' n hn
    rw [putResidue_residue] at hr'
    by_cases hkey : k' = k ∧ r' = r
    · rw [if_pos hkey] at hr'
      obtain rfl := Option.some.inj hr'
      obtain ⟨rfl, _⟩ := hkey
      simpa using hnf n hn
    · rw [if_neg hkey] at hr'; exact h.negEdgeFree k' r' res' hr' n hn
  uposEdgeFree := by
    intro k' r' res' hr' n hn
    rw [putResidue_residue] at hr'
    by_cases hkey : k' = k ∧ r' = r
    · rw [if_pos hkey] at hr'
      obtain rfl := Option.some.inj hr'
      obtain ⟨rfl, _⟩ := hkey
      simpa using huf n hn
    · rw [if_neg hkey] at hr'; exact h.uposEdgeFree k' r' res' hr' n hn
  uposNegDisjoint := by
    intro k' r' res' hr' n hn
    rw [putResidue_residue] at hr'
    by_cases hkey : k' = k ∧ r' = r
    · rw [if_pos hkey] at hr'
      obtain rfl := Option.some.inj hr'
      exact hun n hn
    · rw [if_neg hkey] at hr'; exact h.uposNegDisjoint k' r' res' hr' n hn

/-- The empty state satisfies the structural invariant. -/
theorem structInv_empty (S : Schema) : StructInv S (emptyState S) :=
  (inv_empty S).toStruct

end Zanzibar
