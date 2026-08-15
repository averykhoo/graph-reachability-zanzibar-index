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
  `extractor.py::graph_fragment_ledger`'s own drive loop): **17 of 25 corpora mint a
  leaf index ≥ 1, and 5 of those reach index 2** — every non-first boolean arm gets its
  own leaf (`viewer.1 = banned` in `boolean_exclusion`, `rhs.2` in `demorgans`,
  `all_of.2` in `nary_intersection`, …), and in `direct_arm_exclusion` the subtract arm
  is `approver.1`. An index-`0`-only routing would fail `diff_states` on most of the
  fragment the moment P6 is retired.
  ⚠ **Re-measured 2026-08-16: this bullet used to read "indices 1 AND 2 in 17 of 25",
  which overstates the index-2 breadth 3.4×.** Live histogram over the dotted-object
  rows: index 0 ×43, 1 ×28, 2 ×7; the five index-2 corpora are `demorgans`,
  `double_exclusion`, `nary_intersection`, `nary_union_derived4`, `nested_boolean`. The
  load-bearing half (an index-0-only routing fails most of the fragment) survives; the
  breadth claim did not.
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

## ★★ 2026-08-16 — the ALLOCATION ORDER itself was measured wrong, twice over

The 2026-08-15 rework fixed the *index* and the *arity* but kept reading the allocation
order off the AST **pre-order**. Attack-first before building step 4c-i on it
(house rule 2), by transcribing this file's `persistedLeaves` into Python and diffing it
against the compiled `LeafFamily` table over every corpus and `.fga` fixture. Two
defects, both structural:

* **Python MERGES a maximal pure subtree; the model recursed through it.**
  `_build_plan_tree`'s `build` stops at the first `_is_pure` node and calls
  `_split_pure`, which yields at most **two** leaves — all `Direct` restrictions merged
  into one storage leaf, allocated **first**, then all other members merged into one
  closure leaf. Measured: `r := (a or b) but not banned` compiles to
  `r.0 = {a, b}` / `r.1 = banned`, where the pre-order model predicted three leaves and
  put `banned` at index 2. `r := (a or [user]) but not banned` puts the storage leaf at
  index **0**, ahead of `a`, because `if restrictions:` runs before `if others:`.
  `r := ([user] or [employee]) but not banned` merges BOTH blocks into `r.0`.
* **A tainted USERSET restriction gets its own storage leaf; the model gave one leaf per
  `Direct` block.** `[user, team#active_member]` with `team#active_member` derived
  compiles to `editor.0` (the pure block) + `editor.1` (`PDerivedUserset`, Python
  `LeafFamily.kind = 'userset-storage'`). ⚠ **This one is reachable from a LIVE
  fixture**, `tests/fga_schemas/userset_over_derived.fga::doc#editor` — it is not a
  constructed-only shape.

`rawWriteRels` was checked against `zanzibar_utils_v1.py::RuleSet.apply`'s real seed set
on **744/744** subject × derived-key comparisons, with three positive controls reddening
it (4, 1 and 4 mismatches), so that instrument is not vacuous.

★ **Why this mattered before 4c-i and not after.** The dropped P6 rows are mostly
rule-copied CLOSURE-leaf edges, so `LeafRules.lean`'s rule minting is indexed by
`persistedLeaves`. Had 4c-i been built on the pre-order model, every closure-leaf rule
on a merged subtree would have targeted the wrong leaf — discoverable only after the
full GraphIndex recompile cone was paid.

## ★★ 2026-08-16b — A THIRD defect, and the instrument that missed it is the lesson

The 2026-08-16 correction above was validated by transcribing `persistedLeaves` into
Python and diffing it against the compiled `LeafFamily` table: *"82/82 derived keys
agree, 0 disagreements."* **That claim was measured with the wrong instrument and this
block replaces it.** The transcription consumed Python's **n-ary** `Union` AST. Lean
never sees that tree: `formal/conformance/encode.py`'s `_fold_binary` **LEFT-FOLDS**, so
what reaches the model is `((m₁ ∪ m₂) ∪ …) ∪ mₖ`, whose left spine contains sub-unions
that are pure *by accident of the folding*. Re-run over the **binarized** AST:

```text
AS LANDED  (binary recursion, no spine flatten)      DISAGREEMENTS 1
    SCHEMAS:nary_union_derived4 ('doc', 'any_of4')
      python=[(0, 'closure', False), (1, 'closure', False), (2, 'closure', False)]
      lean  =[(0, 'closure', False)]
WITH FIX   (flatten the union spine when impure)     DISAGREEMENTS 0
```

⚠ **`nary_union_derived4` is IN `GRAPH_FRAGMENT`** — this was a wrong model of a live
in-fragment corpus, which `diff_states` would have surfaced only after step 4c-ii's whole
recompile cone had been paid. The fix is `unionSpineLeaves`; the pin is
`LeafWitness.smN_nary_spine`.

★ **THE METHOD LESSON, and it is the house failure mode wearing a new hat.** Transcribing
a rule into the other language is only half an instrument — *what you feed it* is the
other half. A transcription that consumes the SOURCE representation rather than the one
the model actually receives shares its subject's blind spot exactly as a mirror
instrument does, and reports a confident `82/82`. The companion instrument could not have
caught it either, and for a structural reason worth stating: `rawWriteRels` maps
`.closure _ => none`, and `any_of4` has no storage leaf, so **no closure-leaf allocation
error can ever move the 744/744 number.** Two green instruments, one blind spot, shared.

★★ **AND A LIMIT OF THE BINARY `Expr` ITSELF, which no fix in this file can close.**
`Core/Schema.lean`'s header justifies modelling n-ary unions as left folds because union
is associative and commutative. That is true of `sem` and **false of the leaf
ALLOCATION**. Measured 2026-08-16b on live compiles:

```text
flat      r: a or b or safe      -> leaves [(0,'closure'), (1,'closure')]
parens    r: (a or b) or safe    -> leaves [(0,'closure')]
parensR   r: a or (b or safe)    -> leaves [(0,'closure'), (1,'closure')]
```

The parser does **not** flatten, so Python allocates the parenthesized form differently —
yet `_fold_binary` maps `a or b or safe` and `(a or b) or safe` to the *same* `Expr`. A
model over this AST can therefore be faithful to only one of them. **This file models the
FLAT form**, which is the only form any corpus writes and the only one the encoder can
round-trip; `LeafWitness.smN_models_the_flat_form` states the choice as a theorem.
Because a doc warning would not survive, the shape is refused mechanically on the Python
side by
`formal/conformance/test_conformance_state.py::test_no_corpus_nests_a_pure_union_inside_an_impure_one`.

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

The index a leaf gets is its **position in the allocation order** of the derived def's
expression (`zanzibar_utils_v1.py::_build_plan_tree`, whose `alloc()` is the only
minting site). The first cut of this model (2026-08-15) read that order off the AST
pre-order, one entry per `Direct` block / computed reference / pure TTU arm. **That was
measured WRONG on 2026-08-16** and this section carries the corrected model; the
refutation is in the `## ★ 2026-08-16` block of the module header.

`_build_plan_tree`'s `build` recursion is:

* **at a maximal PURE subtree** (`_is_pure`: boolean-free AND derived-free) it does NOT
  recurse. It calls `_split_pure`, which flattens the subtree into *all* its `Direct`
  restrictions plus *all* its other (computed/TTU) members, and allocates **at most two**
  leaves: one **storage** leaf carrying the merged restrictions, **allocated first**,
  then one **closure** leaf carrying the merged remainder. So `(a or b) but not banned`
  gives `r.0 = {a, b}` and `r.1 = banned` — *two* leaves, not three — and
  `(a or [user]) but not banned` puts the `[user]` storage leaf at index **0** even
  though the AST lists `a` first;
* **`union`/`inter`/`excl` recurse left-to-right** only when the node is NOT pure, and
  mint nothing themselves. Lean's binary `union`/`inter` model n-ary chains as left
  folds (`Core/Schema.lean` header), which preserves the left-to-right leaf order, so
  the allocation stays order-faithful;
* **a non-pure `Direct`** (one carrying tainted *userset* restrictions) mints one
  storage leaf for its pure restrictions **plus one storage leaf per tainted userset
  restriction** (`PDerivedUserset`, Python `LeafFamily.kind = 'userset-storage'`);
* a non-pure `computed`/`ttu` becomes a `derived-computed` / `derived-ttu` /
  `derived-tupleset-ttu` plan node and consumes **NO** index.

**Validated by measurement, not by reading**: the model below, transcribed into Python
and diffed against the compiled `LeafFamily` table (index → kind → storage) over every
corpus in `formal/conformance/corpus.py` and every `tests/fga_schemas/*.fga` fixture,
agrees on **82 / 82 derived keys, 0 disagreements** (2026-08-16). The pre-2026-08-16
model disagrees on `tests/fga_schemas/userset_over_derived.fga::doc#editor` — a LIVE
fixture — and on the four constructed pure-union shapes pinned below.

★ **The TTU target-taint deviation is no longer a bare carry — it is BACKED BY A PYTHON
REFUSAL.** Python decides "is the TTU target derived" over the TTU's frozen
`parent_types`; this model has no parent-types table, so `derivedAnywhere` asks the
type-agnostic question "does ANY declared type carry this relation name derived". The
two can only disagree when a relation name is derived on some type but untainted on
every type the tupleset admits — and on exactly that shape `compile_ruleset`'s
exclusivity pass **refuses to compile at all**, because its own guard is the same
type-agnostic name test (`derived_predicates = {r for (_t, r) in derived}`; *"Rule
then-pattern carries a derived subject predicate"*). Measured 2026-08-16 on
`viewer` derived on `team`, untainted on `folder`, `parent: [folder]`: `ValueError`.
So on the domain of schemas Python compiles, `derivedAnywhere` **is** the
`parent_types` test for this purpose. -/

/-- One persisted (index-consuming) leaf position of a derived def's plan tree.
    Python: the `alloc()` calls in `zanzibar_utils_v1.py::_build_plan_tree` —
    `storage` is a merged `Direct`-restriction block (`LeafSpec.storage=True`),
    `closure` the merged pure non-Direct remainder of one pure subtree, and `userset`
    one tainted userset restriction's own storage leaf (`PDerivedUserset`).

    ⚠ `closure` carries an `Expr`, not a relation NAME, precisely because Python
    MERGES: one closure leaf can hold a whole union of computed/TTU members, and
    step 4c-i's rule minting walks it (`LeafRules.lean::keyLeafRewrites`). -/
inductive PLeaf where
  | storage (rs : List Restriction)
  | closure (e : Expr)
  | userset (r : Restriction)
deriving Repr, DecidableEq, Inhabited

/-- Does ANY declared type carry `R` as a derived relation? The model's stand-in for
    Python's frozen TTU `parent_types` taint test — and, per the section header, the
    same type-agnostic name test `compile_ruleset`'s exclusivity pass itself uses. -/
def derivedAnywhere (S : Schema) (R : String) : Bool :=
  S.keys.any (fun k => k.2 == R && isDerived S k)

/-- Is a restriction a **tainted userset** one, `[T#P]` with `T#P` derived? These are
    the restrictions `_build_plan_tree` peels off into their own storage leaves. -/
def isTaintedUserset (S : Schema) (r : Restriction) : Bool :=
  (r.2.1 != BARE) && isDerived S (r.1, r.2.1)

/-- **Purity** — `zanzibar_utils_v1.py::_is_pure`: no boolean operator and no
    derived-relation reference anywhere in the subtree, so it can become ONE closure
    leaf. `inter`/`excl` are never pure (Python returns `False` for both). -/
def isPure (S : Schema) (ty : String) : Expr → Bool
  | .direct rs  => rs.all (fun r => !isTaintedUserset S r)
  | .computed R => !isDerived S (ty, R)
  | .ttu tgt ts => !isDerived S (ty, ts) && !derivedAnywhere S tgt
  | .union a b  => isPure S ty a && isPure S ty b
  | .inter _ _  => false
  | .excl _ _   => false

/-- **The pure-subtree flattening** — `zanzibar_utils_v1.py::_split_pure`. A pure
    subtree is a union of `{Direct, Computed, TTU}`, so splitting it into "all the
    restrictions" and "all the other members" is lossless. -/
def splitPure : Expr → List Restriction × List Expr
  | .direct rs => (rs, [])
  | .union a b =>
      let l := splitPure a
      let r := splitPure b
      (l.1 ++ r.1, l.2 ++ r.2)
  | e => ([], [e])

/-- Python's `others[0] if len(others) == 1 else Union(tuple(others))`. Lean's binary
    `union` models an n-ary chain as a LEFT fold (`Core/Schema.lean` header), which is
    what keeps `exprArms`' arm order equal to Python's rule-emission order. -/
def unionAll : List Expr → Option Expr
  | [] => none
  | e :: es => some (es.foldl Expr.union e)

/-- The at-most-two leaves a maximal PURE subtree allocates: the merged storage leaf
    FIRST, then the merged closure leaf. Factored out so `persistedLeaves`' four pure
    arms share one definition and the sabotage surface is a single site. -/
def pureLeaves (e : Expr) : List PLeaf :=
  let sp := splitPure e
  (if sp.1.isEmpty then [] else [.storage sp.1]) ++
    (match unionAll sp.2 with | none => [] | some sub => [.closure sub])

/-- The non-boolean arms of the allocation, factored out so `persistedLeaves` and
    `unionSpineLeaves` can share them without a same-size recursive call. -/
def atomLeaves (S : Schema) (ty : String) : Expr → List PLeaf
  | .direct rs =>
      if isPure S ty (.direct rs) then pureLeaves (.direct rs)
      else
        (let pure := rs.filter (fun r => !isTaintedUserset S r)
         if pure.isEmpty then [] else [.storage pure]) ++
        (rs.filter (isTaintedUserset S)).map .userset
  | .computed R => if isDerived S (ty, R) then [] else [.closure (.computed R)]
  | .ttu tgt ts => if isPure S ty (.ttu tgt ts) then [.closure (.ttu tgt ts)] else []
  | _ => []

mutual

/-- **The allocation.** The list of persisted-leaf positions of `e` compiled under
    object type `ty`; a leaf's family index IS its position in this list. Mirrors
    `zanzibar_utils_v1.py::_build_plan_tree`'s `build` per the measured rules in the
    section header.

    WARNING: the impure `union` arm goes through `unionSpineLeaves`, NOT through
    `persistedLeaves` directly. That difference is load-bearing and was measured wrong
    once -- see `unionSpineLeaves`. -/
def persistedLeaves (S : Schema) (ty : String) : Expr → List PLeaf
  | .union a b =>
      if isPure S ty (.union a b) then pureLeaves (.union a b)
      else unionSpineLeaves S ty a ++ unionSpineLeaves S ty b
  | .inter a b => persistedLeaves S ty a ++ persistedLeaves S ty b
  | .excl a b => persistedLeaves S ty a ++ persistedLeaves S ty b
  | e => atomLeaves S ty e

/-- **The union SPINE -- the n-ary children of an impure union, recovered.**

    Python's `build` merges a union only when the **whole n-ary node** is `_is_pure`;
    otherwise it iterates `expr.children` and builds each one separately. Lean's `Expr`
    is binary and `formal/conformance/encode.py`'s `_fold_binary` **left-folds**, so the
    n-ary node `m1 or ... or mk` arrives as `((m1 U m2) U ...) U mk` -- and its left
    spine contains sub-unions that are pure *by accident of the folding*. Recursing
    through `persistedLeaves` there would merge them, which Python never does.

    So inside an impure union the spine is flattened and never merged. This arm is the
    whole content of the 2026-08-16b correction; `LeafWitness.smN_nary_spine` pins it at
    the in-fragment `nary_union_derived4` shape. -/
def unionSpineLeaves (S : Schema) (ty : String) : Expr → List PLeaf
  | .union a b => unionSpineLeaves S ty a ++ unionSpineLeaves S ty b
  | .inter a b => persistedLeaves S ty a ++ persistedLeaves S ty b
  | .excl a b => persistedLeaves S ty a ++ persistedLeaves S ty b
  | e => atomLeaves S ty e

end

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
    names of the **storage-bearing** leaves whose restrictions admit `t`'s subject, at
    their allocation indices; `[t.relation]` on an untainted key. Both storage-bearing
    kinds route — the merged `Direct` block (`.storage`) and a tainted userset
    restriction's own leaf (`.userset`, Python `LeafFamily.kind = 'userset-storage'`);
    `.closure` leaves are rule-fed and take no raw write. The `none` lookup branch is
    unreachable for a derived key (derived ⇒ declared, `taintedKeys_subset_keys`) and
    is a fail-closed backstop.

    **Validated against `zanzibar_utils_v1.py::RuleSet.apply`'s real seed set**
    (2026-08-16): 744 subject × derived-key comparisons over every corpus and `.fga`
    fixture, **0 mismatches**, with three positive controls each reddening it (drop the
    userset leaves → 4; drop the pure-subtree merge → 1; allocate storage last → 4). -/
def rawWriteRels (S : Schema) (t : Tuple) : List String :=
  if isDerived S (t.object.type, t.relation) then
    match S.lookup (t.object.type, t.relation) with
    | some e =>
        (persistedLeaves S t.object.type e).zipIdx.filterMap fun pi =>
          match pi.1 with
          | .storage rs =>
              if restrictionMatches rs t then some (leafPred t.relation pi.2) else none
          | .userset r =>
              if restrictionMatches [r] t then some (leafPred t.relation pi.2) else none
          | .closure _ => none
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

## ★ CONTROLLED — three more sabotages, run 2026-08-16 (the allocation correction)

**(S6) The pure-subtree MERGE is dropped** — `persistedLeaves`' `.union` arm recurses
unconditionally, i.e. exactly the pre-2026-08-16 model. SIX errors, all in the new
block: `smA_merges`, `smA_banned_is_index_1`, `smB_storage_first`, `smB_routes_to_zero`,
`smC_one_storage_leaf`, `smC_both_route_to_zero`. Literal head:
`Tactic 'decide' proved that the proposition Option.map (persistedLeaves SmA "doc")
(SmA.lookup ("doc", "r")) = some [PLeaf.closure ((Expr.computed "a").union
(Expr.computed "b")), PLeaf.closure (Expr.computed "banned")] is false`.
**★ `sw_leaves`, `stP_leaves`, `stD_leaves`, `swX_skip`, `swU_routes`, `swF_fanout` and
every `pol_*` stay GREEN** — this is S3's lesson recurring: on `Sw`'s shape the merged
and unmerged allocations COINCIDE, so the entire pre-2026-08-16 witness set was
VACUOUS for the merge. The A/B/C shapes are the ones that earn their keep.

**(S7) The tainted-userset split is dropped** — the non-pure `.direct` arm emits only
the merged pure block, the pre-2026-08-16 `.direct rs => [.storage rs]` behaviour. TWO
errors: `smU_userset_splits` and `smU_routes_split`; everything else GREEN. This is the
one defect that is reachable from a LIVE fixture
(`tests/fga_schemas/userset_over_derived.fga::doc#editor`).

**(S8) Storage allocated AFTER the merged closure leaf** — `pureLeaves` emits the
closure entry first (the "AST order wins" misreading, refuted by `_split_pure`'s
`if restrictions:` running before `if others:`). FOUR errors: `sw_leaves`,
`routes_to_leaf`, `smB_storage_first`, `smB_routes_to_zero`; `swU_routes`/`swF_*` stay
GREEN (their storage leaves sit in pure subtrees with no closure sibling, so the order
is unobservable there — another vacuity that the B shape closes).

**(S14) The impure-union arm recurses BINARY** — `persistedLeaves` calls itself instead
of `unionSpineLeaves`, i.e. exactly the model that shipped before 2026-08-16b. THREE
errors, all `smN_*`:
```text
ZanzibarProofs/GraphIndex/Leaf.lean:1019: Tactic `decide` proved that the proposition
  Option.map (persistedLeaves SmN "doc") (SmN.lookup ("doc", "any_of4")) =
    some [PLeaf.closure (Expr.computed "a"), PLeaf.closure (Expr.computed "b"),
          PLeaf.closure (Expr.computed "c")]
is false
ZanzibarProofs/GraphIndex/Leaf.lean:1024: … = some 3 is false
ZanzibarProofs/GraphIndex/Leaf.lean:1042: … .length = 2 is false
```
`sw_leaves`, `smA_*`, `smB_*`, `smC_*`, `smU_*`, `swU_routes`, `swF_*`, `pol_*`,
`stP_leaves`, `stD_leaves`, `swX_skip` **all stay GREEN** — every one of them, because
none has an impure union with a multi-member spine. `SmN` is the only witness that
distinguishes it, which is precisely why it is drawn from an in-fragment corpus rather
than constructed.

⚠ **A note on running S14 itself, since it bit once.** The first S14 run reported "no
errors" — because `lake` was invoked from the repo root and failed with *"no
configuration file with a supported extension"*, which the error grep did not match. A
sabotage that reports green because the build never ran is the same failure mode the
sabotage exists to catch. Run `lake` from `formal/lean`, and check for the `Build
completed` line rather than only for the absence of errors.
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
      = some [.storage [("user", BARE, false)], .closure (.computed "viewer"),
              .closure (.computed "banned")] := by
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
      = some [.closure (.ttu "viewer" "parent"), .closure (.computed "banned")] := by decide

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
      = some [.closure (.computed "banned")] := by decide

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
      = some [.closure (.computed "m")] := by decide

/-! ### The 2026-08-16 witnesses — the pure-subtree MERGE and the userset split

These five pin the behaviour the pre-2026-08-16 pre-order model got wrong. Each was
measured against the compiled `LeafFamily` table before being written
(`.scratch/probe6.py`, deleted); the shapes are exactly the constructed probes A/B/C/E
plus the live fixture shape. -/

/-- **Shape A — the MERGE.** `r := (a or b) but not banned`, all pure: Python allocates
    `r.0 = {a, b}` (ONE closure leaf carrying BOTH members) and `r.1 = banned`. The old
    pre-order model gave three leaves and put `banned` at index 2. -/
def SmA : Schema :=
  ⟨[(("doc", "a"), .direct [("user", BARE, false)]),
    (("doc", "b"), .direct [("user", BARE, false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "r"), .excl (.union (.computed "a") (.computed "b")) (.computed "banned"))], []⟩

theorem smA_merges :
    (SmA.lookup ("doc", "r")).map (persistedLeaves SmA "doc")
      = some [.closure (.union (.computed "a") (.computed "b")),
              .closure (.computed "banned")] := by decide

/-- **…and the index that the merge MOVES.** `banned` is `r.1`, not `r.2`. Stated
    separately from `smA_merges` because this is the fact a caller consumes, and it is
    the one an "off by one leaf" defect changes. -/
theorem smA_banned_is_index_1 :
    ((SmA.lookup ("doc", "r")).map (persistedLeaves SmA "doc")).map List.length = some 2 := by
  decide

/-- **Shape B — STORAGE IS ALLOCATED FIRST, against AST order.**
    `r := (a or [user]) but not banned`: `_split_pure` hoists the `Direct` restrictions
    ahead of the computed member, so the storage leaf is `r.0` even though `a` is
    written first. A raw write therefore routes to `r.0`, not `r.1`. -/
def SmB : Schema :=
  ⟨[(("doc", "a"), .direct [("user", BARE, false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "r"),
      .excl (.union (.computed "a") (.direct [("user", BARE, false)])) (.computed "banned"))], []⟩

theorem smB_storage_first :
    (SmB.lookup ("doc", "r")).map (persistedLeaves SmB "doc")
      = some [.storage [("user", BARE, false)], .closure (.computed "a"),
              .closure (.computed "banned")] := by decide

/-- The routing consequence of shape B, at a store: the raw write lands on `r.0`. -/
theorem smB_routes_to_zero :
    rawWriteRels SmB ⟨⟨"user", "bob", BARE⟩, "r", ⟨"doc", "d1"⟩⟩ = [leafPred "r" 0 ] := by
  decide

/-- **Shape C — TWO `Direct` blocks MERGE into one storage leaf.**
    `r := ([user] or [employee]) but not banned` gives `r.0 = {user, employee}` and
    `r.1 = banned`; a write of either subject type lands on the SAME leaf. The old model
    minted two storage leaves and pushed `banned` to index 2. -/
def SmC : Schema :=
  ⟨[(("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "r"),
      .excl (.union (.direct [("user", BARE, false)]) (.direct [("employee", BARE, false)]))
            (.computed "banned"))], []⟩

theorem smC_one_storage_leaf :
    (SmC.lookup ("doc", "r")).map (persistedLeaves SmC "doc")
      = some [.storage [("user", BARE, false), ("employee", BARE, false)],
              .closure (.computed "banned")] := by decide

/-- Both subject types route to the SAME leaf — the fan-out does not split a merged
    storage block. -/
theorem smC_both_route_to_zero :
    rawWriteRels SmC ⟨⟨"user", "a1", BARE⟩, "r", ⟨"doc", "d1"⟩⟩ = [leafPred "r" 0] ∧
    rawWriteRels SmC ⟨⟨"employee", "e1", BARE⟩, "r", ⟨"doc", "d1"⟩⟩ = [leafPred "r" 0] := by
  decide

/-- **Shape U — a tainted USERSET restriction gets its OWN storage leaf.** The shape of
    `tests/fga_schemas/userset_over_derived.fga::doc#editor`, the LIVE fixture the
    pre-2026-08-16 model disagreed with: `[user, team#active_member]` where
    `team#active_member` is derived splits into `editor.0` (the pure `[user]` block) and
    `editor.1` (the userset's own leaf). The old `.direct rs => [.storage rs]` arm gave
    one leaf and routed a `team#active_member` subject to `editor.0`. -/
def SmU : Schema :=
  ⟨[(("team", "e"), .direct [("user", BARE, false)]),
    (("team", "b"), .direct [("user", BARE, false)]),
    (("team", "active_member"), .excl (.computed "e") (.computed "b")),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "editor"),
      .excl (.direct [("user", BARE, false), ("team", "active_member", false)])
            (.computed "banned"))], []⟩

theorem smU_userset_splits :
    (SmU.lookup ("doc", "editor")).map (persistedLeaves SmU "doc")
      = some [.storage [("user", BARE, false)],
              .userset ("team", "active_member", false),
              .closure (.computed "banned")] := by decide

/-- **The routing consequence, and it is the one the live fixture measures**: a
    `team#active_member` userset subject lands on `editor.1`, a bare `user` subject on
    `editor.0`. Under the pre-2026-08-16 model the userset subject routed to `editor.0`
    — a write landing on the wrong node. -/
theorem smU_routes_split :
    rawWriteRels SmU ⟨⟨"user", "u1", BARE⟩, "editor", ⟨"doc", "d1"⟩⟩ = [leafPred "editor" 0] ∧
    rawWriteRels SmU ⟨⟨"team", "t1", "active_member"⟩, "editor", ⟨"doc", "d1"⟩⟩
      = [leafPred "editor" 1] := by
  decide

/-- **Non-vacuity for the userset split**: the restriction really is tainted, so the
    `.userset` arm is REACHED rather than being dead code. -/
theorem smU_active_member_isDerived : isDerived SmU ("team", "active_member") = true := by
  decide

/-! ### ★★ The n-ary union SPINE — the 2026-08-16b correction, at an IN-FRAGMENT shape

Everything above was measured with an instrument that consumed Python's **n-ary** AST.
Lean does not see that tree: `formal/conformance/encode.py`'s `_fold_binary` LEFT-folds,
so `a or b or c or safe` arrives as `((a ∪ b) ∪ c) ∪ safe`. Its left spine `((a∪b)∪c)`
is pure *by accident of the folding*, and a `persistedLeaves` that recursed binary
merged it into ONE closure leaf where Python allocates THREE.

⚠ **This is not a constructed shape.** It is
`formal/conformance/corpus.py::SCHEMAS`' `nary_union_derived4`, which is in
`GRAPH_FRAGMENT` and contributes rows to the P6 ledger — so the defect would have
surfaced as a `diff_states` divergence the moment leg 7 step 7 retired P6, i.e. after
the whole 4c-ii cone had been paid. -/

/-- `nary_union_derived4`'s schema, encoded exactly as `encode.py` hands it to Lean:
    `any_of4 = ((a ∪ b) ∪ c) ∪ safe` with `safe` derived. -/
def SmN : Schema :=
  ⟨[(("doc", "a"), .direct [("user", BARE, false)]),
    (("doc", "b"), .direct [("user", BARE, false)]),
    (("doc", "c"), .direct [("user", BARE, false)]),
    (("doc", "x"), .direct [("user", BARE, false)]),
    (("doc", "blocked"), .direct [("user", BARE, false)]),
    (("doc", "safe"), .excl (.computed "x") (.computed "blocked")),
    (("doc", "any_of4"),
      .union (.union (.union (.computed "a") (.computed "b")) (.computed "c"))
             (.computed "safe"))], []⟩

/-- **Non-vacuity: the spine really is impure**, i.e. this shape exercises the
    `unionSpineLeaves` arm rather than `pureLeaves`. -/
theorem smN_safe_isDerived : isDerived SmN ("doc", "safe") = true := by decide

/-- **…and its left spine really IS pure**, which is exactly why a binary recursion
    merges it. Without this the next theorem could pass for the wrong reason. -/
theorem smN_left_spine_is_pure :
    isPure SmN "doc" (.union (.union (.computed "a") (.computed "b")) (.computed "c"))
      = true := by decide

/-- **THE CORRECTION, pinned.** Python allocates `a ↦ any_of4.0`, `b ↦ any_of4.1`,
    `c ↦ any_of4.2` and gives `safe` no index (measured on the live compile). The
    binary-recursing model produced a SINGLE merged closure leaf. -/
theorem smN_nary_spine :
    (SmN.lookup ("doc", "any_of4")).map (persistedLeaves SmN "doc")
      = some [.closure (.computed "a"), .closure (.computed "b"),
              .closure (.computed "c")] := by decide

/-- The same fact in the form a caller feels: THREE leaves, not one. -/
theorem smN_three_leaves :
    ((SmN.lookup ("doc", "any_of4")).map (persistedLeaves SmN "doc")).map List.length
      = some 3 := by decide

/-- **The declared limit of the binary `Expr`, as a theorem rather than a comment.**
    `Core/Schema.lean`'s header justifies modelling n-ary unions as left folds because
    union is associative and commutative — true of `sem`, **false of the leaf
    ALLOCATION**. Python allocates `(a or b) or safe` (ONE leaf, the inner pure union
    merges) differently from `a or b or safe` (TWO leaves), yet `encode.py::_fold_binary`
    maps both to the SAME `Expr`. So this model necessarily agrees with exactly one of
    them; it agrees with the FLAT form, which is the only form any corpus writes and the
    only one the encoder can round-trip.

    This theorem states the choice explicitly at the smaller witness, so the deviation is
    machine-visible rather than buried in prose. The Python-side guard that keeps a
    parenthesized shape from entering a corpus unnoticed is
    `formal/conformance/test_conformance_state.py::test_no_corpus_nests_a_pure_union_inside_an_impure_one`. -/
theorem smN_models_the_flat_form :
    (persistedLeaves SmN "doc"
       (.union (.union (.computed "a") (.computed "b")) (.computed "safe"))).length = 2 := by
  decide

end LeafWitness

end Zanzibar
