import ZanzibarProofs.GraphIndex.Write
import ZanzibarProofs.GraphIndex.RulesWrite
import ZanzibarProofs.Spec.Stabilize

/-!
# Leaf-family addressing — leg 7 steps 3, 4a and the 4c-pre allocation model

Python's compiler splits every **tainted (derived)** relation `R` into a family of
**leaf predicates** `R.0`, `R.1`, … minted by `alloc` inside `_build_plan_tree`
(`zanzibar_utils_v1.py::_build_plan_tree`, the only creator, called once per tainted key from
`compile_ruleset`). `RuleSet.apply` refuses a raw write that names a
leaf and fan-in-expands a write on the derived **public** name onto the leaf
family via `replace_relation(triple, f.rewrite_relation)` (`zanzibar_utils_v1.py::RuleSet.apply`).

The consequence the model has never carried: **edges land on the LEAF node while the
residue stays keyed at the PUBLIC node** (`index_v4/processor.py::_store_residue`,
and `_write_derived` pins the public node non-implicit because it
"anchors the residue row"). Invariant I4 requires every `'.'`-predicate node to be a
declared leaf family (`index_v4/invariants.py::_check_derived_invariants`).

Until now the conformance extractor hid the difference: projection **P6** drops every
Python edge row whose target predicate carries a `'.'`
(`formal/conformance/extractor.py::_edge_projection`), because the model has no leaf nodes to
compare them against. Retiring P6 is leg 7; this file is its steps 3 and 4a — the
addressing and the forked write — **plus, since 2026-08-15, the measured allocation
model those steps turned out to need** (see the next block). Nothing here is wired into
a CALLER yet (that is step 4c), so no existing caller-level definition changes.

## ★ 2026-08-15 — the index model was re-founded on MEASUREMENT, refuting two shapes

The first cut of this file (2026-08-09 … 2026-08-14) modeled **one undifferentiated
storage leaf, index `0`** (`rawWriteRel … := leafPred t.relation 0`) and declared the
index structure "open and unmeasured" (scope doc §8.2). Both halves of that model are
now **measured wrong**, and this file carries the corrected model:

* **Indices > 0 are IN THE GATE, not exotic.** Enumerating the 76 edge rows projection
  P6 drops across all 25 `GRAPH_FRAGMENT` corpora (2026-08-15, via
  `extractor.py::graph_fragment_ledger`'s own drive loop): **17 of 25 corpora mint leaf
  indices 1 and 2** — every non-first boolean arm gets its own leaf (`viewer.1 = banned`
  in `boolean_exclusion`, `rhs.2` in `demorgans`, `all_of.2` in `nary_intersection`, …),
  and in `direct_arm_exclusion` the subtract arm is `approver.1`. An index-`0`-only
  routing would fail `diff_states` on most of the fragment the moment P6 is retired.
* **The allocation rule** (`zanzibar_utils_v1.py::_build_plan_tree`, `alloc`):
  pre-order, left-to-right over **persisted-leaf positions** — a `Direct` block mints
  one storage leaf; a computed reference mints one closure leaf **iff its target is
  untainted** (a derived reference consumes NO index); a TTU arm mints one closure leaf
  **iff it is pure** (untainted target AND tupleset — a `derived-ttu` /
  `derived-tupleset-ttu` node consumes no index). Measured on live compiles 2026-08-15,
  including: `access: viewer from parent but not banned` gives the TTU arm index 0 and
  `banned` index 1 when `viewer` is untainted, but `banned` index **0** when `viewer`
  is derived.
* **A raw write FANS OUT.** `RuleSet.apply` expands a public-name write onto **every**
  storage leaf whose `RewriteFilter` admits the subject, deduped
  (`zanzibar_utils_v1.py::RuleSet.apply`, the fan-in expansion). Measured:
  `approver: [user] or ([user, employee] but not banned)` routes `user:alice` to BOTH
  `approver.0` and `approver.1`, and `employee:bob` to `approver.1` alone. So the
  faithful routing is `rawWriteRels : … → List String`, not a single relation —
  the 2026-08-14 model was wrong in arity as well as index.
* `Leaf.lean`'s previous `rawWriteRel`-hardcodes-0 was already called a known-wrong
  model by scope-doc §11.5 (Python routes the Direct arm of
  `(viewer but not banned) or [user]` to `approver.2` — pinned below as
  `LeafWitness.swU_routes`); this rework discharges that finding.

## The design rule this file encodes (scope doc §3)

> **Leaf predicates must NOT enter `S.defs`.**

`Core/Schema.lean`'s `relNameOK` already forbids `'.'` in a *declared* relation name —
mirroring Python's own reservation (`zanzibar_utils_v1.py::_validate_ast_references`)
— so a leaf node is **provably** distinct from every
bare R-node for free. `leafPred_ne_relName` below is that lemma and it is the linchpin the
whole leg rests on; no new sentinel axiom alongside `STAR`/`BARE` is needed. If leaf names
were ever added to `S.defs`, `relNameOK`/`WF` would have to be restated and three consumers
would break (`DirectCorrect.lean:73-86`, `ReconcileCorrect.lean:1165`, `RulesChain.lean:224`).

The index is carried **in `NodeKey.pred`**, not in a new `NodeKey` field: `NodeKey` is a
flat 4-field structure compared by `==`/`decide` in hundreds of places (`State.lean:53-58`),
and a fifth field would force every one of them through a rewrite while also wanting a
companion clause on `Inv.nodeEnc`.

Reference: `formal/history/leaf-family-split-scope-2026-08-05.md` §2–§4, §9.4, §11.5–§11.6.
-/

namespace Zanzibar

/-! ## Leaf predicate names -/

/-- The leaf predicate of family index `i` under public relation `R` — Python's
    `f'{relation}.{counter[0]}'` (`zanzibar_utils_v1.py::_build_plan_tree`). -/
def leafPred (R : String) (i : Nat) : String := R ++ "." ++ toString i

/-- Is a node predicate a leaf-family predicate? Leaf names are the only dot-carrying
    predicates that can reach an object node (`'.'` is reserved in declared relation names
    by `relNameOK`), so dot-carrying is the whole test — the mirror of Python's I4 scan
    (`index_v4/invariants.py::_check_derived_invariants`).

    ⚠ **Deliberately WIDER than I4 in exactly one place**, recorded as a theorem rather
    than a comment: see `isLeafPred_bare`.

    Stated over `toList` rather than `String.contains` so the whole leaf layer stays
    kernel-reducible (`String.contains` does not reduce under `decide`;
    `String.contains_char_eq` bridges the two forms where a consumer holds the other). -/
def isLeafPred (p : String) : Bool := p.toList.contains '.'

/-- ⚠ **The one point where `isLeafPred` is wider than Python's I4 test.** I4 carries an
    `and n.predicate != '...'` guard (`index_v4/invariants.py::_check_derived_invariants`) because it scans
    *subject* nodes too, and the bare-subject sentinel `BARE = "..."` is dot-carrying.
    This predicate omits the guard, so it must only ever be applied to **object**-node
    predicates, which carry relation names.

    Stated as a positive theorem so the divergence cannot be silently forgotten by a
    later consumer. Python-side the guard is measured-*unexercised* — of the rows
    surviving projection P1, the dotted-object rows have **zero** object predicate
    `"..."` occurrences — pinned by
    `formal/conformance/test_conformance_state.py::test_p6_bare_sentinel_guard_is_unexercised`
    (scope doc §6, last block). -/
theorem isLeafPred_bare : isLeafPred BARE = true := by decide

/-- A minted leaf name is a leaf predicate. Unconditional: the `'.'` separator is part of
    the construction. -/
@[simp] theorem isLeafPred_leafPred (R : String) (i : Nat) :
    isLeafPred (leafPred R i) = true := by
  simp [isLeafPred, leafPred, String.toList_append, List.contains_eq_mem]

/-! ## The linchpin — leaf names are disjoint from declared relation names -/

/-- **The distinctness linchpin (scope doc §3), for free from `relNameOK`.** A minted leaf
    name is never a name a schema may declare, because declared names carry no `'.'`. -/
theorem leafPred_ne_relName {R' : String} (h : relNameOK R') (R : String) (i : Nat) :
    leafPred R i ≠ R' := by
  intro heq
  refine h ?_
  have := isLeafPred_leafPred R i
  rw [heq] at this
  have hmem : '.' ∈ R'.toList := by
    simpa [isLeafPred, List.contains_eq_mem] using this
  simpa [String.contains_char_eq] using hmem

/-- The same, packaged against a well-formed schema's declaration list. -/
theorem leafPred_ne_declared {S : Schema} (hWF : WF S)
    {p : (String × String) × Expr} (hp : p ∈ S.defs) (R : String) (i : Nat) :
    leafPred R i ≠ p.1.2 :=
  leafPred_ne_relName (hWF.relNames p hp) R i

/-- A declared key's relation name is dot-free. (`Schema.keys` is `S.defs.map (·.1)`, so
    membership hands back the defining pair.) -/
theorem relNameOK_of_mem_keys {S : Schema} (hWF : WF S) {k : Key} (hk : k ∈ S.keys) :
    relNameOK k.2 := by
  unfold Schema.keys at hk
  obtain ⟨p, hp, rfl⟩ := List.mem_map.mp hk
  exact hWF.relNames p hp

/-- **A derived key is a declared key.** `taintStep` filters `S.keys`, so every taint round
    after the first is a sublist of it (`taintChain_subset_keys`); round zero is `[]`. -/
theorem taintedKeys_subset_keys (S : Schema) {k : Key} (h : k ∈ taintedKeys S) :
    k ∈ S.keys :=
  taintChain_subset_keys S S.keys.length k h

/-- Hence a derived relation's own name is dot-free, so its leaf family is disjoint from
    it. This is the form step 4 consumes. -/
theorem relNameOK_of_isDerived {S : Schema} (hWF : WF S) {k : Key}
    (h : isDerived S k = true) : relNameOK k.2 :=
  relNameOK_of_mem_keys hWF (taintedKeys_subset_keys S (by
    simpa [isDerived, List.contains_eq_mem] using h))

/-! ## Leaf nodes -/

/-- The leaf node of family index `i` for relation `R` on object `o`. Deliberately built
    through `objNode`, so the wildcard-object (`w_all`) axis keeps behaving exactly as it
    does for the bare node — the leaf split is orthogonal to `Variant`. -/
def leafNode (o : ObjectRef) (R : String) (i : Nat) : NodeKey := objNode o (leafPred R i)

@[simp] theorem leafNode_pred (o : ObjectRef) (R : String) (i : Nat) :
    (leafNode o R i).pred = leafPred R i := by
  simp [leafNode]

/-- **The node-level linchpin.** A leaf node is distinct from the bare R-node of any
    *declared* relation — including its own public relation — whatever the objects are.
    Proved on the `pred` field alone, so it holds across `Variant`s. -/
theorem leafNode_ne_objNode {R' : String} (h : relNameOK R') (o o' : ObjectRef)
    (R : String) (i : Nat) : leafNode o R i ≠ objNode o' R' := by
  intro heq
  exact leafPred_ne_relName h R i (by
    have := congrArg NodeKey.pred heq
    simpa using this)

/-! ## The leaf-family allocation — Python's `_build_plan_tree`, measured

The index a leaf gets is its **position in the pre-order list of persisted-leaf
positions** of the derived def's expression (`zanzibar_utils_v1.py::_build_plan_tree`,
whose `alloc()` is the only minting site). What counts as a persisted position was
MEASURED on live compiles (2026-08-15, three probes; see the module header):

* a `Direct` restriction block → **one storage leaf** (Python `LeafSpec.storage=True`);
* a computed reference → **one closure leaf iff the target is untainted**; a reference
  to a derived relation becomes a `derived-computed` plan node and consumes NO index;
* a TTU arm → **one closure leaf iff pure** (target and tupleset both untainted);
  a `derived-ttu` / `derived-tupleset-ttu` node consumes NO index;
* boolean nodes (`union`/`inter`/`excl`) recurse left-to-right and mint nothing
  themselves. Lean's binary `union`/`inter` model n-ary chains as left folds
  (`Core/Schema.lean` header), which preserves the left-to-right leaf order, so the
  allocation is order-faithful.

⚠ **One declared modeling deviation, in the TTU target-taint test.** Python decides "is
the TTU target derived" over the TTU's frozen `parent_types`; this model has no
parent-types table, so `derivedAnywhere` asks "does ANY declared type carry this
relation name derived". The two agree whenever a relation name has one taint status
across types — true of every conformance corpus and every measured probe. TTU-inside-
a-derived-def is outside the W4 fragment anyway (`W4Fragment.computedOrDirect` maps
`.ttu` to `False`); the arm is modeled so the allocation is total, not because any
in-fragment chain reaches it. -/

/-- One persisted (index-consuming) leaf position of a derived def's plan tree.
    Python: `LeafSpec` rows that reach `alloc()` — `storage` is the `Direct`-block
    storage leaf (`storage=True`), `closure` the pure computed-reference copy leaf,
    `ttuPure` the pure-TTU arm folded to a closure leaf. -/
inductive PLeaf where
  | storage (rs : List Restriction)
  | closure (src : String)
  | ttuPure (target tupleset : String)
deriving Repr, DecidableEq, Inhabited

/-- Does ANY declared type carry `R` as a derived relation? The model's stand-in for
    Python's frozen TTU `parent_types` taint test (see the section header's declared
    deviation). -/
def derivedAnywhere (S : Schema) (R : String) : Bool :=
  S.keys.any (fun k => k.2 == R && isDerived S k)

/-- **The allocation.** The pre-order list of persisted-leaf positions of `e` compiled
    under object type `ty`; a leaf's family index IS its position in this list.
    Mirrors `zanzibar_utils_v1.py::_build_plan_tree` per the measured rules in the
    section header. -/
def persistedLeaves (S : Schema) (ty : String) : Expr → List PLeaf
  | .direct rs => [.storage rs]
  | .computed R => if isDerived S (ty, R) then [] else [.closure R]
  | .ttu tgt ts =>
      if derivedAnywhere S tgt || isDerived S (ty, ts) then [] else [.ttuPure tgt ts]
  | .union a b => persistedLeaves S ty a ++ persistedLeaves S ty b
  | .inter a b => persistedLeaves S ty a ++ persistedLeaves S ty b
  | .excl a b => persistedLeaves S ty a ++ persistedLeaves S ty b

/-! ## `publicOfLeaf` — the INDEX-AGNOSTIC leaf → public map

The (α) fork decision (scope doc §11.5, PROOF_STATUS 2026-08-14 §1) moves the `Delta`
row to the leaf node, so `affectedKeys`' own-key branch must recover the PUBLIC relation
from a leaf predicate. Python carries the public name in the compiled `LeafFamily` table
and parses the `.i` suffix only to record the index
(`index_v4/processor.py::DeltaProcessor._map_deltas_to_keys`); the model's analogue is
`S.keys` + `isDerived`, exactly as §11.5 records.

**INDEX-AGNOSTIC by construction**: `leafPublic` takes everything before the FIRST
`'.'` and never inspects what follows. §11.5's control C2 measured the plausible
alternative — a literal `".0"`-stripper — returning `none` on `approver.2`, a name
Python really mints (`LeafWitness.pol_idx2` below pins the index-2 case). -/

/-- Everything before the first `'.'` — on a minted leaf name, the public relation. -/
def leafPublic (p : String) : String := String.ofList (p.toList.takeWhile (· ≠ '.'))

/-- The public derived relation a leaf predicate belongs to, if any: `p` must be
    dot-carrying and its dot-free prefix must be a derived relation of `ty`. On a public
    (declared) name this is `none` — the map is not the identity (§11.3's NV8) — and on
    an UNTAINTED family's leaf it is `none` too, which is exactly the guard
    `affectedKeys`' own-key branch needs (untainted leaves have no derived own-key). -/
def publicOfLeaf (S : Schema) (ty p : String) : Option String :=
  if isLeafPred p && isDerived S (ty, leafPublic p) then some (leafPublic p) else none

/-- `takeWhile (≠ '.')` recovers exactly the dot-free prefix. -/
private theorem takeWhile_append_dot (l : List Char) (h : ∀ c ∈ l, c ≠ '.')
    (rest : List Char) : (l ++ '.' :: rest).takeWhile (fun c => c ≠ '.') = l := by
  induction l with
  | nil => simp
  | cons a as ih =>
      have ha : a ≠ '.' := h a (List.mem_cons_self ..)
      have ihr := ih (fun c hc => h c (List.mem_cons_of_mem _ hc))
      simp only [List.cons_append, List.takeWhile_cons]
      simp only [decide_not] at ihr ⊢
      simp [ha, ihr]

/-- On a minted leaf name of a dot-free relation, `leafPublic` recovers the relation —
    for EVERY index `i`. This is the index-agnosticity fact, as a theorem. -/
theorem leafPublic_leafPred (R : String) (i : Nat) (h : ¬ R.contains '.') :
    leafPublic (leafPred R i) = R := by
  have hchars : ∀ c ∈ R.toList, c ≠ '.' := by
    intro c hc heq
    apply h
    rw [String.contains_char_eq]
    subst heq
    simpa using hc
  have hdata : (leafPred R i).toList = R.toList ++ '.' :: (toString i).toList := by
    simp [leafPred, String.toList_append]
  unfold leafPublic
  rw [hdata, takeWhile_append_dot R.toList hchars]
  exact String.ofList_toList

/-- **The (α) round trip, at every index.** A derived relation's minted leaf names map
    back to it. `WF` supplies dot-freeness of the declared name; `isDerived` supplies
    the guard. -/
theorem publicOfLeaf_leafPred {S : Schema} {ty R : String} (hWF : WF S)
    (hd : isDerived S (ty, R) = true) (i : Nat) :
    publicOfLeaf S ty (leafPred R i) = some R := by
  have hR : leafPublic (leafPred R i) = R :=
    leafPublic_leafPred R i (relNameOK_of_isDerived hWF (k := (ty, R)) hd)
  unfold publicOfLeaf
  rw [hR]
  simp [hd]

/-- A dot-free (declared/public) name maps to `none` — the map is not the identity. -/
theorem publicOfLeaf_not_leaf {S : Schema} {ty p : String} (h : isLeafPred p = false) :
    publicOfLeaf S ty p = none := by
  simp [publicOfLeaf, h]

/-- An untainted family's leaf maps to `none` — the guard `affectedKeys`' own-key
    branch relies on (untainted leaves have no derived own-key). -/
theorem publicOfLeaf_untainted {S : Schema} {ty p : String}
    (h : isDerived S (ty, leafPublic p) = false) : publicOfLeaf S ty p = none := by
  simp [publicOfLeaf, h]

/-! ## Raw-write routing — the measured fan-out

Faithful shape per the 2026-08-15 measurement (module header): a raw write on a
**derived** public relation is fan-in-expanded onto EVERY storage leaf whose
restrictions admit the subject (`zanzibar_utils_v1.py::RuleSet.apply`, matching via the
compiled `RewriteFilter`s — modeled by `restrictionMatches`, the same test
`StoreValidRules` uses); a raw write on an untainted key is not rewritten at all and
keeps landing on its bare R-node exactly as today. -/

/-- The relations a RAW (leaf-routed) write of `t` materializes under: the minted leaf
    names of the storage leaves whose restriction block admits `t`'s subject, at their
    allocation indices; `[t.relation]` on an untainted key. The `none` lookup branch is
    unreachable for a derived key (derived ⇒ declared, `taintedKeys_subset_keys`) and
    is a fail-closed backstop. -/
def rawWriteRels (S : Schema) (t : Tuple) : List String :=
  if isDerived S (t.object.type, t.relation) then
    match S.lookup (t.object.type, t.relation) with
    | some e =>
        (persistedLeaves S t.object.type e).zipIdx.filterMap fun pi =>
          match pi.1 with
          | .storage rs =>
              if restrictionMatches rs t then some (leafPred t.relation pi.2) else none
          | _ => none
    | none => []
  else [t.relation]

/-- **The subsumption fact.** On an untainted key the routing is the identity, so the
    forked write path is today's write path on the whole untainted fragment — the
    analogue of `w4Fragment_of_computedOnly`. -/
@[simp] theorem rawWriteRels_untainted {S : Schema} {t : Tuple}
    (h : isDerived S (t.object.type, t.relation) = false) :
    rawWriteRels S t = [t.relation] := by
  simp [rawWriteRels, h]

/-- Every relation a derived-key raw write routes to is a minted leaf name of the
    public relation. -/
theorem mem_rawWriteRels_derived {S : Schema} {t : Tuple} {r : String}
    (hd : isDerived S (t.object.type, t.relation) = true) (hr : r ∈ rawWriteRels S t) :
    ∃ i, r = leafPred t.relation i := by
  unfold rawWriteRels at hr
  rw [if_pos hd] at hr
  cases hlk : S.lookup (t.object.type, t.relation) with
  | none => rw [hlk] at hr; simp at hr
  | some e =>
      rw [hlk] at hr
      obtain ⟨pi, _, hout⟩ := List.mem_filterMap.mp hr
      split at hout
      · split at hout
        · exact ⟨pi.2, ((Option.some.injEq ..).mp hout).symm⟩
        · cases hout
      · cases hout

/-- **The routing is contentful, not a relabeling**: on a derived key every raw-write
    target is a *different node* from the bare R-node the model writes today. Needs no
    store hypothesis, only `WF`. -/
theorem rawWriteNode_ne_objNode {S : Schema} (hWF : WF S) {t : Tuple} {r : String}
    (hd : isDerived S (t.object.type, t.relation) = true) (hr : r ∈ rawWriteRels S t) :
    objNode t.object r ≠ objNode t.object t.relation := by
  obtain ⟨i, rfl⟩ := mem_rawWriteRels_derived hd hr
  exact leafNode_ne_objNode (relNameOK_of_isDerived hWF (k := (t.object.type, t.relation)) hd)
    t.object t.object t.relation i

/-- **The (α) feeder.** Every relation a derived-key raw write routes to maps back to
    the public relation under `publicOfLeaf` — whatever index the allocation gave it.
    This is the lemma the `affectedKeys` own-key branch will consume at step 4c. -/
theorem publicOfLeaf_rawWriteRels {S : Schema} (hWF : WF S) {t : Tuple} {r : String}
    (hd : isDerived S (t.object.type, t.relation) = true) (hr : r ∈ rawWriteRels S t) :
    publicOfLeaf S t.object.type r = some t.relation := by
  obtain ⟨i, rfl⟩ := mem_rawWriteRels_derived hd hr
  exact publicOfLeaf_leafPred hWF hd i

/-! ## The forked write — and why `writeDirect` itself does NOT fork

Scope doc §4 prescribed forking `GraphState.writeDirect` itself. **It is cheaper than
that, and more faithful.** Python does not fork its write path at all: `RuleSet.apply`
re-addresses the **tuples** — `replace_relation(triple, f.rewrite_relation)`
(`zanzibar_utils_v1.py::RuleSet.apply`) — and then the ordinary
`add_tuple`/`_add_edge_locked` path runs unchanged, once per expanded triple. Modelling
the fork the same way (`rawWriteTuples` below, then a fold of today's `writeDirect`)
means `GraphState.writeDirect` is **byte-identical**, and the `∀ (ts : List Tuple)`
fold family in `RulesWrite.lean` (`structInv_foldl_writeDirect` and siblings) applies
to the re-addressed list **verbatim, with no clone**.

What the leg still owes is the *caller* re-pointing (`writeLoggedOne`
`GraphIndex/Cascade.lean::GraphState.writeLoggedOne`, `writeRules`
`GraphIndex/RulesWrite.lean::GraphState.writeRules`) and everything downstream that
assumes the written tuple's relation is the DECLARED one — **including the rule-routed
closure copies, whose per-arm leaf indices need rule provenance that `rewriteClosure`
does not yet carry** (scope doc §11.6). That is step 4c and it is where the cost lives;
this section is only the addressing half. -/

/-- **The raw write, fan-in-expanded onto its leaf family.** Python's
    `replace_relation(triple, f.rewrite_relation)` over every matching storage filter
    (`zanzibar_utils_v1.py::RuleSet.apply`). On an untainted relation there is no
    family and this is `[t]`. -/
def rawWriteTuples (S : Schema) (t : Tuple) : List Tuple :=
  (rawWriteRels S t).map fun r => { t with relation := r }

@[simp] theorem rawWriteTuples_untainted {S : Schema} {t : Tuple}
    (h : isDerived S (t.object.type, t.relation) = false) : rawWriteTuples S t = [t] := by
  simp [rawWriteTuples, rawWriteRels_untainted h]

/-- **The RAW (leaf-routed) write.** Today's `writeDirect`, folded over the re-addressed
    expansion — the `writeLoggedOne` / `writeRules` leg of scope doc §4's table. The
    reconcile-emission leg (`reconcileKey` / `reconcileKeyD` / `reconcileKeyDR`) keeps
    calling `writeDirect` directly, which is what makes `Delta.leaf`-style caller
    provenance genuinely required (§9.4: the schema alone is not a sufficient
    discriminator). -/
def GraphState.writeDirectRaw (σ : GraphState) (S : Schema) (t : Tuple) : GraphState :=
  (rawWriteTuples S t).foldl (fun acc u => acc.writeDirect u) σ

/-- On the untainted fragment the forked write IS today's write — the whole existing
    development is untouched by construction. -/
@[simp] theorem writeDirectRaw_untainted {σ : GraphState} {S : Schema} {t : Tuple}
    (h : isDerived S (t.object.type, t.relation) = false) :
    σ.writeDirectRaw S t = σ.writeDirect t := by
  simp [GraphState.writeDirectRaw, rawWriteTuples_untainted h]

/-- **The fold bridge, and the reason step 4c's fold half is cheap.** A fold of raw
    writes is a fold of ordinary writes over the flattened re-addressed list, so
    `RulesWrite.lean`'s `∀ (ts : List Tuple)` fold family discharges every projection
    at the raw fold with no clone. -/
theorem foldl_writeDirectRaw_eq (S : Schema) (ts : List Tuple) (σ : GraphState) :
    ts.foldl (fun acc u => acc.writeDirectRaw S u) σ
      = (ts.flatMap (rawWriteTuples S)).foldl (fun acc u => acc.writeDirect u) σ := by
  induction ts generalizing σ with
  | nil => rfl
  | cons a as ih =>
      simp only [List.foldl_cons, List.flatMap_cons, List.foldl_append]
      exact ih _

/-- The invariant survives the forked write for free — no clone of
    `structInv_writeDirect`, because the targets moved by re-addressing the tuples. -/
theorem structInv_writeDirectRaw {S S' : Schema} {σ : GraphState} (h : StructInv S' σ)
    (t : Tuple) : StructInv S' (σ.writeDirectRaw S t) :=
  structInv_foldl_writeDirect (rawWriteTuples S t) h

/-- Likewise the full invariant on the residue-free fragment. -/
theorem inv_writeDirectRaw {S S' : Schema} {σ : GraphState} (h : Inv S' σ)
    (hre : ResidueEmpty σ) (t : Tuple) : Inv S' (σ.writeDirectRaw S t) :=
  inv_foldl_writeDirect (rawWriteTuples S t) h hre

/-- The accepted-write edge list, factored out because it is what state-level
    instruments need. (General; unchanged by the fan-out rework.) -/
theorem writeDirect_edges_of_admit {σ : GraphState} {t : Tuple}
    (h : σ.admitEdge (subjNode t.subject) (objNode t.object t.relation) = true) :
    (σ.writeDirect t).edges = (subjNode t.subject, objNode t.object t.relation) :: σ.edges := by
  unfold GraphState.writeDirect
  simp only [h, if_true]
  rfl

/-! ## The non-vacuity witnesses

Scope doc §7: *"budget a non-vacuity WITNESS for every step, not just a green build"* —
the lesson that recurred three legs running. Everything above is additive, so a green
build vets nothing: an allocation whose derived-skip branch is unreachable, a
`publicOfLeaf` that happens to work only at index 0, or a routing that never fans out,
would compile and audit exactly as cleanly.

**And per §9.3 the obvious witness is a TRAP.** `W4WitnessDirect`'s `Sd`/`Td` carries no
wildcard, so `Inv.negStarCovered` forces `neg = []` and a leg-7 fact instantiated there
is vacuously true. `Sw` below is D.3's **wildcard-carrying** schema, verbatim from scope
doc §9.3, which is the pair the leg-0 attack probe actually reddened. The 2026-08-15
witnesses (`SwU`, `SwF`, `StP`/`StD`, `SwX`) each pin one MEASURED Python behavior; the
provenance of each is its docstring.

## ★ CONTROLLED — five sabotages, run 2026-08-15 (`docs/sabotage-procedure.md`)

Each is the narrowest *plausible* weakening of one measured rule; each reddens the pin
that carries that rule while the named controls stay green, so every red is
attributable. Literal outputs, `lake build ZanzibarProofs.GraphIndex.Leaf`:

**(S1) The derived-skip guard is dropped** — `persistedLeaves`' `.computed` arm mints
unconditionally (`[.closure R]`). The plausible misreading: "every reference is a leaf".
ONE error in the tree:
`Tactic 'decide' proved that the proposition Option.map (persistedLeaves SwX "doc")
(SwX.lookup ("doc", "a")) = some [PLeaf.closure "m"] is false` — `swX_skip` REDDENS;
`sw_leaves`, `stP_leaves`, `stD_leaves` stay GREEN.

**(S2) The TTU purity guard is dropped** — the `.ttu` arm mints unconditionally.
ONE error: `... Option.map (persistedLeaves StD "doc") (StD.lookup ("doc", "access"))
= some [PLeaf.closure "banned"] is false` — `stD_leaves` REDDENS (`banned` displaced
from index 0); `stP_leaves` stays GREEN.

**(S3) `publicOfLeaf` as the `".0"`-stripper** — §11.5's control C2, the exact wrong
model the scope doc measured: strip a literal `".0"` suffix off `leafPublic`. TWO
errors: `leafPublic_leafPred`'s proof breaks (the theorem is now FALSE at every index
except 0 — the general lemma guards too), and
`Tactic 'decide' proved that the proposition publicOfLeaf SwU "doc"
(leafPred "approver" 2) = some "approver" is false` — `pol_idx2` REDDENS. **`pol_nv7`
(index 0) stays GREEN** — an index-0-only pin would have been VACUOUSLY satisfied by
the wrong model; the index-2 pin is the one that earns its keep.

**(S4) The subject-match guard is dropped** — `rawWriteRels` routes to every storage
leaf regardless of `restrictionMatches`. `swF_second_only` REDDENS
(`... rawWriteRels SwF {employee bob …} = [leafPred "approver" 1] is false` —
`employee:bob` lands on `approver.0` too); `swF_fanout` stays GREEN. (Plus one proof
artifact in `mem_rawWriteRels_derived`, whose `split` finds no `if` left.)

**(S5) First-match-only routing** — `.take 1` on the fan-out (the natural "one write,
one edge" misreading; refuted by measurement 2). `swF_fanout` REDDENS
(`... = [leafPred "approver" 0, leafPred "approver" 1] is false` — `user:alice` loses
`approver.1`); `swF_second_only` stays GREEN.
-/

namespace LeafWitness

/-- D.3's schema (scope doc §9.3): `approver := ([user] or viewer) but not banned`, with
    the load-bearing wildcard on `viewer`. `approver` is derived, `banned`/`viewer` are not. -/
def Sw : Schema :=
  ⟨[(("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "viewer"), .direct [("user", BARE, true)]),
    (("doc", "approver"),
      .excl (.union (.direct [("user", BARE, false)]) (.computed "viewer"))
            (.computed "banned"))], []⟩

/-- A raw write on the **derived** public relation. -/
def tw : Tuple := ⟨⟨"user", "bob", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩

/-- A raw write on an **untainted** relation, same object. -/
def tb : Tuple := ⟨⟨"user", "bob", BARE⟩, "banned", ⟨"doc", "d1"⟩⟩

/-- `WF` is satisfiable here, so the schema premises are not empty. -/
theorem wf : WF Sw := ⟨by
  intro p hp
  simp only [Sw, List.mem_cons, List.not_mem_nil, or_false] at hp
  rcases hp with rfl | rfl | rfl <;> simp [relNameOK, String.contains_char_eq]⟩

/-- **Non-vacuity, half 1: the derived branch is REACHED.** Without this every leaf lemma
    above is decoration. -/
theorem approver_isDerived : isDerived Sw ("doc", "approver") = true := by decide

/-- **Non-vacuity, half 2: the untainted branch is reached too** — the routing is a fork,
    not a blanket rewrite. -/
theorem banned_not_isDerived : isDerived Sw ("doc", "banned") = false := by decide

/-- The allocation at `Sw`'s derived def: storage `[user]` at 0, `viewer` copy at 1,
    `banned` copy at 2 — the pre-order rule at a shape carrying all three leaf kinds
    Python storage-compiles here. -/
theorem sw_leaves :
    (Sw.lookup ("doc", "approver")).map (persistedLeaves Sw "doc")
      = some [.storage [("user", BARE, false)], .closure "viewer", .closure "banned"] := by
  decide

/-- **The routing MOVES the write, onto exactly `doc:d1#approver.0`** — the storage
    leaf's allocation index at this shape. -/
theorem routes_to_leaf : rawWriteRels Sw tw = [leafPred "approver" 0] := by decide

/-- **…and every routed target is a different node from the public one.** Instantiates
    the general theorem, so a sabotage of *either* goes red here. -/
theorem routes_away : ∀ r ∈ rawWriteRels Sw tw,
    objNode tw.object r ≠ objNode tw.object tw.relation :=
  fun _ hr => rawWriteNode_ne_objNode wf approver_isDerived hr

/-- **The untainted write is untouched** — byte-for-byte today's target list. This is
    the subsumption claim step 4 must preserve, checked at a store rather than assumed. -/
theorem untainted_unmoved : rawWriteRels Sw tb = [tb.relation] :=
  rawWriteRels_untainted banned_not_isDerived

/-- **The fork is real at STATE level, not just at node level.** From the empty state
    the raw write and today's write produce different edge lists. (Kernel-checked by
    `decide` — the whole write path is computable.) -/
theorem writeDirectRaw_edges_ne :
    ((emptyState Sw).writeDirectRaw Sw tw).edges ≠ ((emptyState Sw).writeDirect tw).edges := by
  decide

/-! ### The 2026-08-15 measured witnesses -/

/-- **Scope-doc §11.5's measured shape**: `approver := (viewer but not banned) or [user]`.
    Python routes the Direct arm to `approver.2` — the fact that killed both the
    `".0"`-stripper and the hardcoded index 0. -/
def SwU : Schema :=
  ⟨[(("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "viewer"), .direct [("user", BARE, true)]),
    (("doc", "approver"),
      .union (.excl (.computed "viewer") (.computed "banned"))
             (.direct [("user", BARE, false)]))], []⟩

/-- **The index-2 routing pin** — Python's measured `approver.2` (scope doc §11.5,
    control C2). Under sabotage S3 (`".0"`-stripper) or the pre-2026-08-15 hardcoded
    index 0, this is FALSE. -/
theorem swU_routes :
    rawWriteRels SwU ⟨⟨"user", "bob", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩
      = [leafPred "approver" 2] := by decide

/-- **`publicOfLeaf` at the index Python actually mints** (NV7's shape, at index 2 —
    see sabotage S3 for why index 0 alone would be a vacuous pin). -/
theorem pol_idx2 : publicOfLeaf SwU "doc" (leafPred "approver" 2) = some "approver" := by
  decide

/-- NV7 (PROOF_STATUS 2026-08-14 §1): the index-0 case. -/
theorem pol_nv7 : publicOfLeaf Sw "doc" (leafPred "approver" 0) = some "approver" := by
  decide

/-- NV8: the map is NOT the identity — a public name maps to `none`. -/
theorem pol_nv8 : publicOfLeaf Sw "doc" "approver" = none := by decide

/-- An untainted family's leaf maps to `none` — the own-key guard for untainted
    `leaf = true` rows keeps holding under (α). -/
theorem pol_untainted : publicOfLeaf Sw "doc" (leafPred "viewer" 0) = none := by decide

/-- **The fan-out shape** (measurement 2, 2026-08-15):
    `approver := [user] or ([user, employee] but not banned)` — two storage leaves with
    overlapping restrictions. -/
def SwF : Schema :=
  ⟨[(("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "approver"),
      .union (.direct [("user", BARE, false)])
             (.excl (.direct [("user", BARE, false), ("employee", BARE, false)])
                    (.computed "banned")))], []⟩

/-- **A raw write FANS OUT** — `user:alice` lands on BOTH storage leaves, exactly as
    Python's measured 2-triple expansion. Under sabotage S5 (first-match-only) this is
    FALSE. -/
theorem swF_fanout :
    rawWriteRels SwF ⟨⟨"user", "alice", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩
      = [leafPred "approver" 0, leafPred "approver" 1] := by decide

/-- **…and the fan-out is FILTERED** — `employee:bob` matches only the second arm's
    restrictions, so it lands on `approver.1` alone. Under sabotage S4 (match guard
    dropped) this is FALSE. -/
theorem swF_second_only :
    rawWriteRels SwF ⟨⟨"employee", "bob", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩
      = [leafPred "approver" 1] := by decide

/-- **The pure-TTU shape** (measurement 1a):
    `access := viewer from parent but not banned`, `viewer` untainted on `folder`.
    The TTU arm consumes index 0; `banned` gets 1. -/
def StP : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"), .direct [("folder", BARE, false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "access"), .excl (.ttu "viewer" "parent") (.computed "banned"))], []⟩

theorem stP_leaves :
    (StP.lookup ("doc", "access")).map (persistedLeaves StP "doc")
      = some [.ttuPure "viewer" "parent", .closure "banned"] := by decide

/-- **The tainted-target TTU shape** (measurement 1b): same `access`, but `viewer` is
    derived on `folder` — the TTU arm consumes NO index and `banned` inherits 0. -/
def StD : Schema :=
  ⟨[(("folder", "e"), .direct [("user", BARE, false)]),
    (("folder", "b"), .direct [("user", BARE, false)]),
    (("folder", "viewer"), .excl (.computed "e") (.computed "b")),
    (("doc", "parent"), .direct [("folder", BARE, false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "access"), .excl (.ttu "viewer" "parent") (.computed "banned"))], []⟩

theorem stD_leaves :
    (StD.lookup ("doc", "access")).map (persistedLeaves StD "doc")
      = some [.closure "banned"] := by decide

/-- **The derived-reference skip** (the `cross_stratum_resettle` corpus fact,
    2026-08-15 ledger enumeration): `a := v but not m` with `v` derived — `v` consumes
    no index, so `m` mints `a.0`. -/
def SwX : Schema :=
  ⟨[(("doc", "e"), .direct [("user", BARE, false)]),
    (("doc", "b"), .direct [("user", BARE, false)]),
    (("doc", "m"), .direct [("user", BARE, false)]),
    (("doc", "v"), .excl (.computed "e") (.computed "b")),
    (("doc", "a"), .excl (.computed "v") (.computed "m"))], []⟩

theorem swX_skip :
    (SwX.lookup ("doc", "a")).map (persistedLeaves SwX "doc")
      = some [.closure "m"] := by decide

end LeafWitness

end Zanzibar
