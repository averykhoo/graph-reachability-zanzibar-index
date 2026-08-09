import ZanzibarProofs.GraphIndex.State
import ZanzibarProofs.Spec.Stabilize

/-!
# Leaf-family addressing — leg 7 step 3 (ADDITIVE: no behavior change)

Python's compiler splits every **tainted (derived)** relation `R` into a family of
**leaf predicates** `R.0`, `R.1`, … minted by `alloc` inside `_build_plan_tree`
(`zanzibar_utils_v1.py:1658-1659`, the only creator, called once per tainted key from
`compile_ruleset` `:1954-1956`). `RuleSet.apply` (`:423`) refuses a raw write that names a
leaf (`:433-439`) and fan-in-expands a write on the derived **public** name onto the leaf
family via `replace_relation(triple, f.rewrite_relation)` (`:447`).

The consequence the model has never carried: **edges land on the LEAF node while the
residue stays keyed at the PUBLIC node** (`index_v4/processor.py::_store_residue`
`:949-978`, and `_write_derived` `:429-440` pins the public node non-implicit because it
"anchors the residue row"). Invariant I4 requires every `'.'`-predicate node to be a
declared leaf family (`index_v4/invariants.py:303-310`).

Until now the conformance extractor hid the difference: projection **P6** drops every
Python edge row whose target predicate carries a `'.'`
(`formal/conformance/extractor.py:235-236`), because the model has no leaf nodes to
compare them against. Retiring P6 is leg 7; **this file is its step 3 — addressing only.**
Nothing here is wired into the write path yet (that is step 4, the `writeDirect` fork), so
no existing definition, statement or proof changes.

## The design rule this file encodes (scope doc §3)

> **Leaf predicates must NOT enter `S.defs`.**

`Core/Schema.lean:64`'s `relNameOK` already forbids `'.'` in a *declared* relation name —
mirroring Python's own reservation (`zanzibar_utils_v1.py:869-875`,
`_validate_ast_references` `:890-899`) — so a leaf node is **provably** distinct from every
bare R-node for free. `leafPred_ne_relName` below is that lemma and it is the linchpin the
whole leg rests on; no new sentinel axiom alongside `STAR`/`BARE` is needed. If leaf names
were ever added to `S.defs`, `relNameOK`/`WF` would have to be restated and three consumers
would break (`DirectCorrect.lean:73-86`, `ReconcileCorrect.lean:1165`, `RulesChain.lean:224`).

The index is carried **in `NodeKey.pred`**, not in a new `NodeKey` field: `NodeKey` is a
flat 4-field structure compared by `==`/`decide` in hundreds of places (`State.lean:53-58`),
and a fifth field would force every one of them through a rewrite while also wanting a
companion clause on `Inv.nodeEnc`.

Reference: `formal/history/leaf-family-split-scope-2026-08-05.md` §2–§4, §9.4.
-/

namespace Zanzibar

/-! ## Leaf predicate names -/

/-- The leaf predicate of family index `i` under public relation `R` — Python's
    `f'{relation}.{counter[0]}'` (`zanzibar_utils_v1.py:1658-1659`). -/
def leafPred (R : String) (i : Nat) : String := R ++ "." ++ toString i

/-- Is a node predicate a leaf-family predicate? Leaf names are the only dot-carrying
    predicates that can reach an object node (`'.'` is reserved in declared relation names
    by `relNameOK`), so dot-carrying is the whole test — the mirror of Python's I4 scan
    (`index_v4/invariants.py:303-310`).

    ⚠ **Deliberately WIDER than I4 in exactly one place**, recorded as a theorem rather
    than a comment: see `isLeafPred_bare`. -/
def isLeafPred (p : String) : Bool := p.contains '.'

/-- ⚠ **The one point where `isLeafPred` is wider than Python's I4 test.** I4 carries an
    `and n.predicate != '...'` guard (`index_v4/invariants.py:307`) because it scans
    *subject* nodes too, and the bare-subject sentinel `BARE = "..."` is dot-carrying.
    This predicate omits the guard, so it must only ever be applied to **object**-node
    predicates, which carry relation names.

    Stated as a positive theorem so the divergence cannot be silently forgotten by a
    later consumer. Python-side the guard is measured-*unexercised* — of the 244 rows
    surviving projection P1, 73 have a dotted object predicate and **zero** have object
    predicate `"..."` — pinned by
    `formal/conformance/test_conformance_state.py::test_p6_bare_sentinel_guard_is_unexercised`
    (scope doc §6, last block). -/
theorem isLeafPred_bare : isLeafPred BARE = true := by
  simp [isLeafPred, BARE, String.contains_char_eq]

/-- A minted leaf name is a leaf predicate. Unconditional: the `'.'` separator is part of
    the construction. -/
@[simp] theorem isLeafPred_leafPred (R : String) (i : Nat) :
    isLeafPred (leafPred R i) = true := by
  simp [isLeafPred, leafPred, String.contains_char_eq]

/-! ## The linchpin — leaf names are disjoint from declared relation names -/

/-- **The distinctness linchpin (scope doc §3), for free from `relNameOK`.** A minted leaf
    name is never a name a schema may declare, because declared names carry no `'.'`. -/
theorem leafPred_ne_relName {R' : String} (h : relNameOK R') (R : String) (i : Nat) :
    leafPred R i ≠ R' := by
  intro heq
  refine h ?_
  have := isLeafPred_leafPred R i
  rw [heq] at this
  simpa [isLeafPred] using this

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

/-! ## Raw-write routing

The function step 4 will drive `writeDirect`'s target off. Faithful shape per scope doc
§9.4: a raw write on a **derived** key is rewritten onto the leaf family, a raw write on an
untainted key is not rewritten at all and keeps landing on its bare R-node exactly as
today.

⚠ **Modelling scope, declared here rather than discovered later.** This models **one
undifferentiated storage leaf per derived relation** (index `0`). Python allocates an index
per *persisted-leaf position* (pre-order, left-to-right, `zanzibar_utils_v1.py:1650-1652`)
and a derived def with two Direct arms therefore has two storage leaves. Whether that
distinction — and the `storage=True`/`storage=False` split (`:1693-1699`) that exists for
TTU stored-parent enumeration — needs modelling is scope doc §8.2, still **open and
unmeasured**. Nothing below depends on the index being `0`; the lemmas are stated for
arbitrary `i` and only `rawWriteRel` picks one. -/

/-- The relation a RAW (leaf-routed) write of `t` materializes under. -/
def rawWriteRel (S : Schema) (t : Tuple) : String :=
  if isDerived S (t.object.type, t.relation) then leafPred t.relation 0 else t.relation

/-- The node a RAW write of `t` lands its edge on. -/
def rawWriteNode (S : Schema) (t : Tuple) : NodeKey := objNode t.object (rawWriteRel S t)

/-- **The subsumption fact step 4 needs.** On an untainted key the routing is the identity,
    so the forked write path is definitionally today's write path on the whole untainted
    fragment — the analogue of `w4Fragment_of_computedOnly`. -/
@[simp] theorem rawWriteRel_untainted {S : Schema} {t : Tuple}
    (h : isDerived S (t.object.type, t.relation) = false) : rawWriteRel S t = t.relation := by
  simp [rawWriteRel, h]

/-- …and at node level. -/
@[simp] theorem rawWriteNode_untainted {S : Schema} {t : Tuple}
    (h : isDerived S (t.object.type, t.relation) = false) :
    rawWriteNode S t = objNode t.object t.relation := by
  simp [rawWriteNode, rawWriteRel_untainted h]

/-- On a derived key the write is rewritten onto the leaf family. -/
theorem rawWriteRel_derived {S : Schema} {t : Tuple}
    (h : isDerived S (t.object.type, t.relation) = true) :
    rawWriteRel S t = leafPred t.relation 0 := by
  simp [rawWriteRel, h]

theorem rawWriteNode_derived {S : Schema} {t : Tuple}
    (h : isDerived S (t.object.type, t.relation) = true) :
    rawWriteNode S t = leafNode t.object t.relation 0 := by
  simp [rawWriteNode, leafNode, rawWriteRel_derived h]

/-- **The routing is contentful, not a relabeling**: on a derived key the raw-write target
    is a *different node* from the bare R-node the model writes today. This is the fact
    that makes step 4 a real fork — and note it needs no store hypothesis, only `WF`. -/
theorem rawWriteNode_ne_objNode {S : Schema} (hWF : WF S) {t : Tuple}
    (h : isDerived S (t.object.type, t.relation) = true) :
    rawWriteNode S t ≠ objNode t.object t.relation := by
  rw [rawWriteNode_derived h]
  exact leafNode_ne_objNode (relNameOK_of_isDerived hWF h) _ _ _ _

/-! ## The non-vacuity witness

Scope doc §7: *"budget a non-vacuity WITNESS for every step, not just a green build"* — the
lesson that recurred three legs running (`echain-widening-plan-2026-07-28.md` §C.3/§C.4/§C.5).
Everything above is additive, so a green build vets nothing: a `rawWriteRel` whose derived
branch is unreachable, or a `rawWriteNode_ne_objNode` whose `isDerived … = true` premise no
real schema satisfies, would compile and audit exactly as cleanly.

**And per §9.3 the obvious witness is a TRAP.** `W4WitnessDirect`'s `Sd`/`Td` — the pair
every pointer in the tree aims at as "the canonical Direct-arm counterexample" — carries no
wildcard, so `Inv.negStarCovered` forces `neg = []` and a leg-7 fact instantiated there is
vacuously true. The schema below is D.3's **wildcard-carrying** one, verbatim from scope
doc §9.3, which is the pair the leg-0 attack probe actually reddened.

## ★ CONTROLLED — two sabotages, and only the second one needs this section

Both run 2026-08-09 against this file (`docs/sabotage-procedure.md`); literal output, with
line numbers as observed — i.e. before this docstring was added, so they no longer point at
the named declarations.

**(A) The routing collapses to the identity** — `rawWriteRel S t := t.relation`, i.e. the
derived branch is dropped. Caught by the GENERAL section, so the witness is not what earns
its keep here:

```
error: ZanzibarProofs/GraphIndex/Leaf.lean:183:47: unsolved goals   -- rawWriteRel_derived
```

**(B) The routing guard is made UNSATISFIABLE** — `&& isLeafPred t.relation` added to the
`if`, with the three derived-branch lemmas' hypotheses tightened to match. This is a
*plausible* misreading, not a strawman: `RuleSet.apply` really does refuse a raw write that
names a leaf (`zanzibar_utils_v1.py:433-439`), so "never re-route an already-routed write"
reads like a faithfulness fix. It is not — no raw write ever names a leaf, so the derived
branch becomes dead and every leaf lemma becomes vacuously true about nothing.

**Every general lemma above still compiles, `rawWriteNode_ne_objNode` included.** Exactly
two errors in the whole tree, both in this section:

```
error: ZanzibarProofs/GraphIndex/Leaf.lean:250:29: Application type mismatch: The argument
  approver_isDerived
has type
  isDerived Sw ("doc", "approver") = true
but is expected to have type
  (isDerived Sw (tw.object.type, tw.relation) && isLeafPred tw.relation) = true
error: ZanzibarProofs/GraphIndex/Leaf.lean:254:23: Application type mismatch: ...
```

Delete these five declarations and sabotage (B) is "Build completed successfully
(971 jobs)" — green build, clean audit, both pins byte-identical. -/

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

/-- `WF` is satisfiable here, so `rawWriteNode_ne_objNode`'s schema premise is not empty. -/
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

/-- **The routing MOVES the node.** The step's whole content, at a concrete pair: a raw
    write on `approver` no longer targets `doc:d1#approver`. Instantiates the general
    theorem, so a sabotage of *either* goes red here. -/
theorem routes_away : rawWriteNode Sw tw ≠ objNode tw.object tw.relation :=
  rawWriteNode_ne_objNode wf approver_isDerived

/-- …onto exactly `doc:d1#approver.0`. -/
theorem routes_to_leaf : rawWriteNode Sw tw = leafNode ⟨"doc", "d1"⟩ "approver" 0 :=
  rawWriteNode_derived approver_isDerived

/-- **The untainted write is untouched** — byte-for-byte today's target. This is the
    subsumption claim step 4 must preserve, checked at a store rather than assumed. -/
theorem untainted_unmoved : rawWriteNode Sw tb = objNode tb.object tb.relation :=
  rawWriteNode_untainted banned_not_isDerived

end LeafWitness

end Zanzibar
