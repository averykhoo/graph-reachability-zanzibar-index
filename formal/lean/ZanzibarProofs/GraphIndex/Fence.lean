import ZanzibarProofs.GraphIndex.Leaf

/-!
# The public read fence — `GraphModel.checkPublic`

**Model source: `index_v4/wildcard.py::WildcardIndex.check` (the PUBLIC entry) versus
`::WildcardIndex._check_internal` (the unfenced probe).** Since `BL-2` (2026-08-21b) the
public entry answers `False` for every LEAF FAMILY name and delegates everything else to
`_check_internal`; the delta processor's operand reads deliberately enter *below* that
fence, via `_check_internal` (`index_v4/processor.py::_EvalContext.leaf_check`). The two
layers are pinned apart by `tests/test_reg18_leaf_name_read_leak.py` and recorded in
`docs/spec-deviations.md`.

Until this file the Lean model had only the unfenced layer: `GraphIndex/State.lean::
GraphModel.check` corresponds to `_check_internal`, and nothing corresponded to the
public entry. That is the gap this file closes, and it is why the headline theorems can
keep their *unguarded* shape: the leaf-name case is discharged by the fence rather than
excluded by a hypothesis on the caller.

## Why this is not a weakening

`checkPublic` is strictly more conservative than `check` — it can only turn a `true` into
a `false`, never the reverse. The theorem that matters (`FullScope.lean::
graph_correct_public`) states it equals `sem` on the nose, so conservatism alone is not
the claim; the fenced branch is *correct*, because a leaf-family name is by construction
undeclared (`Leaf.lean::relNameOK_of_mem_keys` — declared relation names are dot-free,
leaf predicates are not) and the spec denies at undeclared keys
(`Spec/Confine.lean::semAux_undeclared`).

⚠ **The vacuity hazard this file is designed against.** Before the 4c-ii re-point no leaf
nodes are ever minted, so `check σ qLeaf` is already `false` at every leaf name and the
correctness theorem below would be provable *even if the fence never fired*. A fence that
never fires would then go silently false the instant 4c-ii mints leaf nodes. So the
polarity of `publicOfLeaf` is pinned by positive `by decide` witnesses at the HEADLINE
schema (`FullScope.lean::LeafFence.*`) — those witnesses, not this correctness proof, are
what makes the fence non-vacuous. Per `docs/sabotage-procedure.md`, they are written
before the theorem, not after it.
-/

namespace Zanzibar

/-- **The public read.** `some` from `publicOfLeaf` means "this name is a minted leaf of a
    derived family" — exactly the `BL-2` condition — and the public entry denies there.
    Everything else is the ordinary closure read.

    Reads `σ.schema` rather than taking the schema as a parameter, faithfully to Python:
    `WildcardIndex.check` consults `self.schema_info`, not a caller-supplied schema. The
    bridge back to the ambient `S` of the headline hypotheses is
    `CascadeStrataAssemble.lean::reachedByW3d2E_schema`. -/
def GraphModel.checkPublic (σ : GraphState) (q : Query) : Bool :=
  if (publicOfLeaf σ.schema q.object.type q.relation).isSome then false
  else GraphModel.check σ q

/-- **The bridge: a leaf-family name is never a declared key.** Contraposition of
    `Leaf.lean::relNameOK_of_mem_keys` (a declared key's relation name is dot-free)
    against the dot-carrying half of `publicOfLeaf`'s guard. This is the fact that makes
    the fenced branch *correct* rather than merely conservative — it feeds
    `Spec/Confine.lean::semAux_undeclared`. -/
theorem not_mem_keys_of_publicOfLeaf_isSome {S : Schema} (hWF : WF S) {ty p : String}
    (h : (publicOfLeaf S ty p).isSome = true) : (ty, p) ∉ S.keys := by
  intro hk
  -- `publicOfLeaf` returns `some` only through its guard, whose left conjunct is the
  -- dot-carrying test.
  have hleaf : isLeafPred p = true := by
    by_contra hne
    rw [publicOfLeaf_not_leaf (S := S) (ty := ty) (by simpa using hne)] at h
    simp at h
  -- A declared key's relation name is dot-free, contradicting it.
  have hnd : relNameOK p := relNameOK_of_mem_keys hWF (k := (ty, p)) hk
  apply hnd
  rw [String.contains_char_eq]
  simpa [isLeafPred, List.contains_eq_mem] using hleaf

/-- The unfenced branch, as a rewrite: off the leaf families the public read IS the
    ordinary read, so every existing `check`-shaped fact transports unchanged. -/
theorem checkPublic_of_not_leaf {σ : GraphState} {q : Query}
    (h : publicOfLeaf σ.schema q.object.type q.relation = none) :
    GraphModel.checkPublic σ q = GraphModel.check σ q := by
  simp [GraphModel.checkPublic, h]

/-- The fenced branch, as a rewrite: on a leaf family the public read denies. -/
@[simp] theorem checkPublic_of_leaf {σ : GraphState} {q : Query} {R : String}
    (h : publicOfLeaf σ.schema q.object.type q.relation = some R) :
    GraphModel.checkPublic σ q = false := by
  simp [GraphModel.checkPublic, h]

/-- **The fence is conservative**: it never invents a grant. Independent of any
    admission/reachability hypothesis, so it holds on every state — including the
    post-4c-ii states this file is being landed ahead of. -/
theorem checkPublic_le_check {σ : GraphState} {q : Query} :
    GraphModel.checkPublic σ q = true → GraphModel.check σ q = true := by
  unfold GraphModel.checkPublic
  split
  · intro h; exact absurd h (by simp)
  · exact id

end Zanzibar
