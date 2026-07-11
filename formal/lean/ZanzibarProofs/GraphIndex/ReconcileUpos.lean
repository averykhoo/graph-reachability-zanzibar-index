import ZanzibarProofs.GraphIndex.ReconcileComplete

/-!
# The derived reconcile — userset subjects and the `upos` residue (ROADMAP W3b, write half)

`SEMANTICS.md` §7.6; `index_v4/processor.py` (`reconcile_subject` userset branch,
`:345-357`; `reconcile` step 2c, `:431-441`; `_store_residue`, `:555-579`);
`index_v4/wildcard.py:411-419` (the edge-free userset read, blind-audit P4).

W3a closed the derived-boolean read correspondence for **bare** subjects: on the
star-free fragment the processor stores no residue and a derived membership is a
materialised edge. Its attack-first recorded the scope gap: a **userset** subject
(e.g. `group:g#mem` granted `member` under `viewer := member but not banned`) can be
`sem`-true while the residue-empty read returns `false`. W3b makes the read's `upos`
branch go live:

* **Write.** For a userset candidate `c` (predicate ≠ BARE) at derived key
  `(dt, R)` / object `on`, the processor maintains the residue entry
  `c ∈ upos ⟺ check_fn(c)` — **edge-free** (a userset edge would leak through the
  closure to every member, defeating pointwise exclusion — P4). On star-free data
  `covered = false`, so `want_upos = should` and `want_neg = false`
  (`processor.py:345-357`). Modelled as `reconcileUposKey`: a per-candidate
  insert/remove fold on the `upos` list via `putResidue`, leaving `stars`/`neg`
  empty and edges/nodes untouched.
* **Read.** `probeDerived`'s userset branch consults `upos` (`State.lean:562-565` =
  `wildcard.py:411-419`). On a `upos`-only residue table the whole derived read
  collapses to: star subject ⇒ `false`, userset subject ⇒ `upos` membership, bare
  subject ⇒ the W3a edge probe (`probeDerived_uposOnly` below).

**Attack-first (2026-07-11, machine-checked `#eval` vs `sem`, scratch deleted).** On
`doc#viewer := member but not banned` (operands `member = direct ∪ computed editor`,
`banned` direct; userset grants `group:{g,h,i}#mem` variously member/banned/editor):
the planned model's `check` equals `sem` on a 180-query grid (bare + userset + star +
ghost subjects, incl. the derived key itself as a userset subject); order of the
bare/userset reconcile passes and candidate order are irrelevant; a repeated pass is
idempotent; the P4 non-leak holds (a banned member of an `upos`-true userset stays
denied); and `upos` members do NOT reach the R-node even though userset nodes carry
operand out-edges (I6 `uposEdgeFree` content). No refutation.

The key structural fact driving everything: **the upos fold never touches edges or
nodes**, so `checkFn` (which reads only the edge/node structure and the store) is
*constant* across the fold — provenance and presence need no mid-state bookkeeping
beyond the congruence lemmas below.
-/

namespace Zanzibar

/-! ## `putResidue` field projections (completing `State.lean`'s set) -/

@[simp] theorem putResidue_outbox (σ : GraphState) (k : NodeKey) (r : String) (res : Residue) :
    (σ.putResidue k r res).outbox = σ.outbox := rfl
@[simp] theorem putResidue_watermark (σ : GraphState) (k : NodeKey) (r : String) (res : Residue) :
    (σ.putResidue k r res).watermark = σ.watermark := rfl

/-! ## Congruence — reads that depend only on the edge/node structure

`GraphState.reach` is `reachB σ.edges (σ.nodes.length + 1)`; `probeNonDerived` is a
disjunction of `reach` probes; `graphRec`/`checkFn` read the graph only through
`probeNonDerived` (plus the store `T`). So all of them agree across states with
equal `edges` and `nodes` — in particular across any residue-only mutation. -/

/-- Agreement on `edges` and `nodes` gives agreement of the executable reach probe. -/
theorem reach_congr {σ σ' : GraphState} (he : σ'.edges = σ.edges) (hn : σ'.nodes = σ.nodes)
    (u v : NodeKey) : σ'.reach u v = σ.reach u v := by
  unfold GraphState.reach
  rw [he, hn]

/-- The non-derived ≤4-probe read agrees across edge/node-equal states. -/
theorem probeNonDerived_congr {σ σ' : GraphState} (he : σ'.edges = σ.edges)
    (hn : σ'.nodes = σ.nodes) (q : Query) :
    GraphModel.probeNonDerived σ' q = GraphModel.probeNonDerived σ q := by
  unfold GraphModel.probeNonDerived
  simp only [reach_congr he hn]

/-- The `check_fn` node-recursion oracle agrees across edge/node-equal states. -/
theorem graphRec_congr {σ σ' : GraphState} (he : σ'.edges = σ.edges)
    (hn : σ'.nodes = σ.nodes) (s : SubjectRef) :
    GraphModel.graphRec σ' s = GraphModel.graphRec σ s := by
  funext ot on' r'
  exact probeNonDerived_congr he hn _

/-- **`checkFn` agrees across edge/node-equal states** — the compiled boolean reads
    the graph only through `graphRec` (the store/query arguments are state-free). -/
theorem checkFn_congr {σ σ' : GraphState} (he : σ'.edges = σ.edges)
    (hn : σ'.nodes = σ.nodes) (T : Store) (s : SubjectRef) (dt on R : String) (e : Expr) :
    σ'.checkFn T s dt on R e = σ.checkFn T s dt on R e := by
  unfold GraphState.checkFn
  rw [graphRec_congr he hn s]

/-! ## The `upos` write model -/

/-- The `upos` list persisted at `(k, R)` (empty if no residue row — `getD`, matching
    the read's default). -/
def GraphState.uposAt (σ : GraphState) (k : NodeKey) (R : String) : List SubjectRef :=
  ((σ.residue k R).getD Residue.empty).upos

/-- **One userset reconcile-subject step** (`reconcile_subject`, `processor.py:345-357`).
    On star-free data `covered = false`, so the candidate `c` is kept in `upos` iff
    `check_fn(c)` (`want_upos = should`), `neg` stays empty (`want_neg = false`), and no
    edge is ever written for a userset subject (P4). `_store_residue` upserts the row;
    the model's `putResidue` stores a possibly-empty `upos` where Python deletes an
    all-empty row — read-equivalent via the `getD Residue.empty` default. -/
def GraphState.reconcileUposStep (σ : GraphState) (T : Store) (dt on R : String) (e : Expr)
    (c : SubjectRef) : GraphState :=
  let k := objNode ⟨dt, on⟩ R
  let cur := σ.uposAt k R
  if σ.checkFn T c dt on R e then
    σ.putResidue k R ⟨[], [], if cur.contains c then cur else c :: cur⟩
  else
    σ.putResidue k R ⟨[], [], cur.filter (fun x => x != c)⟩

/-- **Reconcile the userset candidates of one derived key** `(dt, R)` at object `on`:
    the per-candidate insert/remove fold. Mirrors `reconcileKey` (the bare-candidate
    edge fold); the two passes commute semantically because this one never touches
    edges/nodes and that one never touches residues. -/
def GraphState.reconcileUposKey (σ : GraphState) (T : Store) (dt on R : String) (e : Expr)
    (cands : List SubjectRef) : GraphState :=
  cands.foldl (fun acc c => acc.reconcileUposStep T dt on R e c) σ

/-! ### Structural equalities — the upos fold is residue-only -/

@[simp] theorem reconcileUposStep_edges (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (c : SubjectRef) : (σ.reconcileUposStep T dt on R e c).edges = σ.edges := by
  simp only [GraphState.reconcileUposStep]
  split <;> rfl

@[simp] theorem reconcileUposStep_nodes (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (c : SubjectRef) : (σ.reconcileUposStep T dt on R e c).nodes = σ.nodes := by
  simp only [GraphState.reconcileUposStep]
  split <;> rfl

@[simp] theorem reconcileUposStep_schema (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (c : SubjectRef) : (σ.reconcileUposStep T dt on R e c).schema = σ.schema := by
  simp only [GraphState.reconcileUposStep]
  split <;> rfl

@[simp] theorem reconcileUposStep_outbox (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (c : SubjectRef) : (σ.reconcileUposStep T dt on R e c).outbox = σ.outbox := by
  simp only [GraphState.reconcileUposStep]
  split <;> rfl

@[simp] theorem reconcileUposStep_watermark (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (c : SubjectRef) :
    (σ.reconcileUposStep T dt on R e c).watermark = σ.watermark := by
  simp only [GraphState.reconcileUposStep]
  split <;> rfl

theorem reconcileUposKey_edges (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileUposKey T dt on R e cands).edges = σ.edges := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    show ((σ.reconcileUposStep T dt on R e c).reconcileUposKey T dt on R e rest).edges = σ.edges
    rw [ih, reconcileUposStep_edges]

theorem reconcileUposKey_nodes (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileUposKey T dt on R e cands).nodes = σ.nodes := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    show ((σ.reconcileUposStep T dt on R e c).reconcileUposKey T dt on R e rest).nodes = σ.nodes
    rw [ih, reconcileUposStep_nodes]

theorem reconcileUposKey_schema (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileUposKey T dt on R e cands).schema = σ.schema := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    show ((σ.reconcileUposStep T dt on R e c).reconcileUposKey T dt on R e rest).schema = σ.schema
    rw [ih, reconcileUposStep_schema]

theorem reconcileUposKey_outbox (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileUposKey T dt on R e cands).outbox = σ.outbox := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    show ((σ.reconcileUposStep T dt on R e c).reconcileUposKey T dt on R e rest).outbox = σ.outbox
    rw [ih, reconcileUposStep_outbox]

theorem reconcileUposKey_watermark (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileUposKey T dt on R e cands).watermark = σ.watermark := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    show ((σ.reconcileUposStep T dt on R e c).reconcileUposKey T dt on R e rest).watermark
        = σ.watermark
    rw [ih, reconcileUposStep_watermark]

/-- `checkFn` is constant across the whole upos fold (edges/nodes untouched). -/
theorem checkFn_reconcileUposKey (T : Store) (dt on R : String) (e : Expr)
    (cands : List SubjectRef) (σ : GraphState) (T' : Store) (s : SubjectRef)
    (dt' on' R' : String) (e' : Expr) :
    (σ.reconcileUposKey T dt on R e cands).checkFn T' s dt' on' R' e'
      = σ.checkFn T' s dt' on' R' e' :=
  checkFn_congr (reconcileUposKey_edges T dt on R e cands σ)
    (reconcileUposKey_nodes T dt on R e cands σ) T' s dt' on' R' e'

/-- The structural invariant transfers across any edge/node/schema-equal state. -/
theorem structInv_congr {S : Schema} {σ σ' : GraphState} (he : σ'.edges = σ.edges)
    (hn : σ'.nodes = σ.nodes) (hs : σ'.schema = σ.schema) (h : StructInv S σ) :
    StructInv S σ' where
  schemaEq := hs.trans h.schemaEq
  nodeEnc := by rw [hn]; exact h.nodeEnc
  edgesClosed := by rw [he, hn]; exact h.edgesClosed
  acyclic := by rw [he]; exact h.acyclic

/-- The upos fold preserves `StructInv` (it is residue-only). -/
theorem structInv_reconcileUposKey {S : Schema} {σ : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef) (h : StructInv S σ) :
    StructInv S (σ.reconcileUposKey T dt on R e cands) :=
  structInv_congr (reconcileUposKey_edges T dt on R e cands σ)
    (reconcileUposKey_nodes T dt on R e cands σ)
    (reconcileUposKey_schema T dt on R e cands σ) h

/-- The upos fold preserves cascade-quiescence (outbox/watermark untouched). -/
theorem quiescent_reconcileUposKey {σ : GraphState} (T : Store) (dt on R : String)
    (e : Expr) (cands : List SubjectRef) (h : Quiescent σ) :
    Quiescent (σ.reconcileUposKey T dt on R e cands) := by
  intro d hd
  rw [reconcileUposKey_outbox] at hd
  rw [reconcileUposKey_watermark]
  exact h d hd

/-! ### Residue characterization -/

/-- Reading back the residue just written at its own key. -/
theorem uposAt_putResidue_self (σ : GraphState) (k : NodeKey) (r : String) (res : Residue) :
    (σ.putResidue k r res).uposAt k r = res.upos := by
  unfold GraphState.uposAt
  rw [putResidue_residue, if_pos ⟨rfl, rfl⟩]
  rfl

/-- A upos step leaves every other `(key, relation)` residue untouched. -/
theorem reconcileUposStep_residue_other {σ : GraphState} {T : Store} {dt on R : String}
    {e : Expr} {c : SubjectRef} {k' : NodeKey} {r' : String}
    (h : ¬(k' = objNode ⟨dt, on⟩ R ∧ r' = R)) :
    (σ.reconcileUposStep T dt on R e c).residue k' r' = σ.residue k' r' := by
  simp only [GraphState.reconcileUposStep]
  split <;> rw [putResidue_residue, if_neg h]

/-- The upos fold leaves every other `(key, relation)` residue untouched. -/
theorem reconcileUposKey_residue_other {T : Store} {dt on R : String} {e : Expr}
    {k' : NodeKey} {r' : String} (h : ¬(k' = objNode ⟨dt, on⟩ R ∧ r' = R)) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileUposKey T dt on R e cands).residue k' r' = σ.residue k' r' := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    show ((σ.reconcileUposStep T dt on R e c).reconcileUposKey T dt on R e rest).residue k' r'
        = σ.residue k' r'
    rw [ih, reconcileUposStep_residue_other h]

/-- Any residue the upos step leaves behind is `upos`-only, and the step never
    *creates* residues at other keys. At its own key it writes `⟨[], [], _⟩`. -/
theorem reconcileUposStep_residue_shape {σ : GraphState} {T : Store} {dt on R : String}
    {e : Expr} {c : SubjectRef} {k' : NodeKey} {r' : String} {res : Residue}
    (h : (σ.reconcileUposStep T dt on R e c).residue k' r' = some res) :
    (σ.residue k' r' = some res) ∨ (res.stars = [] ∧ res.neg = []) := by
  by_cases hkey : k' = objNode ⟨dt, on⟩ R ∧ r' = R
  · simp only [GraphState.reconcileUposStep] at h
    split at h <;>
    · rw [putResidue_residue, if_pos hkey] at h
      obtain rfl := Option.some.inj h
      exact Or.inr ⟨rfl, rfl⟩
  · rw [reconcileUposStep_residue_other hkey] at h
    exact Or.inl h

/-- **Per-step `upos` membership.** After one userset reconcile step for candidate
    `c`, a subject `x` is in the key's `upos` iff it *is* `c` and the guard held, or
    it is a different subject that was already there. (`x = c` with the guard false is
    the explicit removal — `want_upos` gone, `upos.discard`.) -/
theorem reconcileUposStep_upos_mem {σ : GraphState} {T : Store} {dt on R : String}
    {e : Expr} {c : SubjectRef} (x : SubjectRef) :
    x ∈ (σ.reconcileUposStep T dt on R e c).uposAt (objNode ⟨dt, on⟩ R) R ↔
      ((x = c ∧ σ.checkFn T c dt on R e = true) ∨
       (x ≠ c ∧ x ∈ σ.uposAt (objNode ⟨dt, on⟩ R) R)) := by
  simp only [GraphState.reconcileUposStep]
  by_cases hg : σ.checkFn T c dt on R e = true
  · rw [if_pos hg, uposAt_putResidue_self]
    show x ∈ (if (σ.uposAt (objNode ⟨dt, on⟩ R) R).contains c
        then σ.uposAt (objNode ⟨dt, on⟩ R) R
        else c :: σ.uposAt (objNode ⟨dt, on⟩ R) R) ↔ _
    by_cases hc : (σ.uposAt (objNode ⟨dt, on⟩ R) R).contains c = true
    · rw [if_pos hc]
      have hcmem : c ∈ σ.uposAt (objNode ⟨dt, on⟩ R) R := by
        rw [List.contains_eq_mem] at hc; exact of_decide_eq_true hc
      constructor
      · intro hx
        by_cases hxc : x = c
        · exact Or.inl ⟨hxc, hg⟩
        · exact Or.inr ⟨hxc, hx⟩
      · rintro (⟨rfl, _⟩ | ⟨_, hx⟩)
        · exact hcmem
        · exact hx
    · rw [if_neg hc]
      constructor
      · intro hx
        rcases List.mem_cons.mp hx with rfl | hmem
        · exact Or.inl ⟨rfl, hg⟩
        · by_cases hxc : x = c
          · exact Or.inl ⟨hxc, hg⟩
          · exact Or.inr ⟨hxc, hmem⟩
      · rintro (⟨rfl, _⟩ | ⟨_, hx⟩)
        · exact List.mem_cons_self
        · exact List.mem_cons_of_mem _ hx
  · rw [if_neg hg, uposAt_putResidue_self]
    constructor
    · intro hx
      obtain ⟨hmem, hne⟩ := List.mem_filter.mp hx
      exact Or.inr ⟨by simpa [bne_iff_ne] using hne, hmem⟩
    · rintro (⟨rfl, hgc⟩ | ⟨hne, hx⟩)
      · exact absurd hgc hg
      · exact List.mem_filter.mpr ⟨hx, by simpa [bne_iff_ne] using hne⟩

/-- **Whole-fold `upos` membership.** After the userset reconcile pass over `cands`,
    `x` is in the key's `upos` iff it was a candidate and the (fold-constant) guard
    held at the pass start, or it was no candidate and was already there. The guard
    constancy is `checkFn_congr` — the fold never touches edges/nodes. -/
theorem reconcileUposKey_upos_mem {T : Store} {dt on R : String} {e : Expr}
    (x : SubjectRef) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      x ∈ (σ.reconcileUposKey T dt on R e cands).uposAt (objNode ⟨dt, on⟩ R) R ↔
        ((x ∈ cands ∧ σ.checkFn T x dt on R e = true) ∨
         (x ∉ cands ∧ x ∈ σ.uposAt (objNode ⟨dt, on⟩ R) R)) := by
  intro cands
  induction cands with
  | nil =>
    intro σ
    simp [GraphState.reconcileUposKey]
  | cons c rest ih =>
    intro σ
    have hfold : σ.reconcileUposKey T dt on R e (c :: rest)
        = (σ.reconcileUposStep T dt on R e c).reconcileUposKey T dt on R e rest := rfl
    rw [hfold, ih]
    have hck : ∀ y : SubjectRef,
        (σ.reconcileUposStep T dt on R e c).checkFn T y dt on R e
          = σ.checkFn T y dt on R e := fun y =>
      checkFn_congr (reconcileUposStep_edges σ T dt on R e c)
        (reconcileUposStep_nodes σ T dt on R e c) T y dt on R e
    rw [hck x]
    constructor
    · rintro (⟨hxr, hchk⟩ | ⟨hxr, hxstep⟩)
      · exact Or.inl ⟨List.mem_cons_of_mem _ hxr, hchk⟩
      · rcases (reconcileUposStep_upos_mem x).mp hxstep with ⟨rfl, hchk⟩ | ⟨hne, hmem⟩
        · exact Or.inl ⟨List.mem_cons_self, hchk⟩
        · exact Or.inr ⟨by
            intro hmem'
            rcases List.mem_cons.mp hmem' with rfl | h'
            · exact hne rfl
            · exact hxr h', hmem⟩
    · rintro (⟨hxm, hchk⟩ | ⟨hxm, hmem⟩)
      · rcases List.mem_cons.mp hxm with rfl | hxr
        · by_cases hxrest : x ∈ rest
          · exact Or.inl ⟨hxrest, hchk⟩
          · exact Or.inr ⟨hxrest,
              (reconcileUposStep_upos_mem x).mpr (Or.inl ⟨rfl, hchk⟩)⟩
        · exact Or.inl ⟨hxr, hchk⟩
      · have hxc : x ≠ c := fun heq => hxm (heq ▸ List.mem_cons_self)
        have hxrest : x ∉ rest := fun h' => hxm (List.mem_cons_of_mem _ h')
        exact Or.inr ⟨hxrest,
          (reconcileUposStep_upos_mem x).mpr (Or.inr ⟨hxc, hmem⟩)⟩

/-! ## The `upos`-only residue table and the W3b read collapse -/

/-- **`ResidueUposOnly σ`** — every persisted residue carries only `upos` content
    (`stars = neg = []`). The W3b analog of W3a's `ResidueEmpty`: on the star-free
    fragment the processor never stores star coverage or exclusions
    (`covered = false` ⇒ `want_neg = false`, `processor.py:349`), so the whole
    residue table is `upos`-only. -/
def ResidueUposOnly (σ : GraphState) : Prop :=
  ∀ k r res, σ.residue k r = some res → res.stars = [] ∧ res.neg = []

/-- A residue-free state is trivially `upos`-only. -/
theorem residueUposOnly_of_empty {σ : GraphState} (h : ResidueEmpty σ) :
    ResidueUposOnly σ := by
  intro k r res hres
  rw [h k r] at hres
  cases hres

/-- `writeDirect` never touches the residue table. -/
theorem writeDirect_residue (σ : GraphState) (t : Tuple) :
    (σ.writeDirect t).residue = σ.residue := by
  by_cases h : σ.admitEdge (subjNode t.subject) (objNode t.object t.relation) = true
  · unfold GraphState.writeDirect
    simp only [h, if_true]
    rfl
  · rw [writeDirect_reject (by simpa using h)]

/-- The bare-candidate reconcile fold never touches the residue table. -/
theorem reconcileKey_residue (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileKey T dt on R e cands).residue = σ.residue := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    show ((if σ.checkFn T c dt on R e then σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩
        else σ).reconcileKey T dt on R e rest).residue = σ.residue
    rw [ih]
    split
    · exact writeDirect_residue σ _
    · rfl

/-- The upos step preserves `upos`-onlyness (it writes only `⟨[], [], _⟩` rows). -/
theorem residueUposOnly_reconcileUposStep {σ : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (c : SubjectRef) (h : ResidueUposOnly σ) :
    ResidueUposOnly (σ.reconcileUposStep T dt on R e c) := by
  intro k r res hres
  rcases reconcileUposStep_residue_shape hres with hold | hshape
  · exact h k r res hold
  · exact hshape

/-- The upos fold preserves `upos`-onlyness. -/
theorem residueUposOnly_reconcileUposKey (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) {σ : GraphState}, ResidueUposOnly σ →
      ResidueUposOnly (σ.reconcileUposKey T dt on R e cands) := by
  intro cands
  induction cands with
  | nil => intro σ h; exact h
  | cons c rest ih =>
    intro σ h
    exact ih (residueUposOnly_reconcileUposStep T dt on R e c h)

/-- `writeDirect` preserves `upos`-onlyness (residues untouched). -/
theorem residueUposOnly_writeDirect {σ : GraphState} (t : Tuple)
    (h : ResidueUposOnly σ) : ResidueUposOnly (σ.writeDirect t) := by
  intro k r res hres
  rw [writeDirect_residue] at hres
  exact h k r res hres

/-- The bare-candidate reconcile fold preserves `upos`-onlyness. -/
theorem residueUposOnly_reconcileKey {σ : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef) (h : ResidueUposOnly σ) :
    ResidueUposOnly (σ.reconcileKey T dt on R e cands) := by
  intro k r res hres
  rw [reconcileKey_residue] at hres
  exact h k r res hres

namespace GraphModel

/-- **The W3b read collapse: the derived read on a `upos`-only residue table.** With
    `stars = neg = []` everywhere, `probeDerived` (§7.6, `wildcard.py:398-432`)
    reduces to: object wildcard ⇒ `false` (decision-15); star subject ⇒ `false` (no
    coverage); **userset subject ⇒ `upos` membership** (the edge-free P4 read, now
    live); bare subject ⇒ the W3a bare edge probe (the `stars ∖ neg` fallback is
    dead). -/
theorem probeDerived_uposOnly {σ : GraphState} (hru : ResidueUposOnly σ) (q : Query) :
    probeDerived σ q =
      if q.object.name = STAR then false
      else if q.subject.name = STAR then false
      else if q.subject.predicate = BARE then
        σ.reach (subjNode q.subject) (objNode q.object q.relation)
      else
        (σ.uposAt (objNode q.object q.relation) q.relation).contains q.subject := by
  unfold probeDerived
  have hshape : ((σ.residue (objNode q.object q.relation) q.relation).getD
      Residue.empty).stars = [] ∧
      ((σ.residue (objNode q.object q.relation) q.relation).getD Residue.empty).neg = [] := by
    cases hres : σ.residue (objNode q.object q.relation) q.relation with
    | none => exact ⟨rfl, rfl⟩
    | some res => exact hru _ _ res hres
  by_cases ho : q.object.name = STAR
  · simp [ho]
  · by_cases hs : q.subject.name = STAR
    · simp [ho, hs, hshape.1]
    · by_cases hb : q.subject.predicate = BARE
      · simp [ho, hs, hb, hshape.1, hshape.2]
      · simp only [if_neg ho, if_neg hs, if_neg hb]
        simp only [beq_iff_eq, ho, if_false, bne_iff_ne, ne_eq, hb, not_false_eq_true,
          hs, hshape.1, hshape.2]
        show (if ((σ.residue (objNode q.object q.relation) q.relation).getD
            Residue.empty).upos.contains q.subject = true then true
          else if !(([] : List Shape).contains q.subject.shape) then false
          else !(([] : List SubjectRef).contains q.subject)) = _
        by_cases hu : ((σ.residue (objNode q.object q.relation) q.relation).getD
            Residue.empty).upos.contains q.subject = true
        · rw [if_pos hu]
          exact (hu.symm : _)
        · rw [if_neg hu]
          have : (([] : List Shape).contains q.subject.shape) = false := rfl
          rw [this]
          simp only [Bool.not_false, if_true]
          symm
          unfold GraphState.uposAt
          exact Bool.not_eq_true _ ▸ (Bool.of_not_eq_true hu)

/-- The routed derived read (`check`) on a `upos`-only state. -/
theorem check_derived_uposOnly {σ : GraphState} (hru : ResidueUposOnly σ) (q : Query)
    (hder : isDerived σ.schema (q.object.type, q.relation) = true) :
    check σ q =
      if q.object.name = STAR then false
      else if q.subject.name = STAR then false
      else if q.subject.predicate = BARE then
        σ.reach (subjNode q.subject) (objNode q.object q.relation)
      else
        (σ.uposAt (objNode q.object q.relation) q.relation).contains q.subject := by
  unfold check
  rw [hder]
  simp only [if_true]
  exact probeDerived_uposOnly hru q

end GraphModel

end Zanzibar
