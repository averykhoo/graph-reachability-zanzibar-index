# ROADMAP — closing the 9 `sorry`s

A per-theorem plan for discharging the remaining deep obligations. Synthesizes a
Gemini review roadmap **with corrections from actually type-checking against the
code** (Gemini wrote without a compiler and made several concrete errors, flagged
below). Read alongside `PROOF_STATUS.md` (status) and `SEMANTICS.md` (the spec).

The 9 sorries: `setEngine_correct` (T1); `pathCount_addEdge`, `pathCount_removeEdge`
(T4); `semAux_fuel_stable_step` (T0a); `stratify_none_iff_cycle`,
`stratify_topological` (T0b); `graph_reached_inv`, `graph_correct`,
`cascade_converges` (T2/T5).

---

## T1 — `setEngine_correct` (Phase 3, most tractable)

**Plan.** Replace `opaque SetEngineModel.check` with a concrete `expand`-based model:
`expandAux : Nat → … → MemberSet Id` (fuel-recursive like `sem`), booleans via
`MemberSet.union/intersect/subtract`, `check` = `containsStar/containsEntity/
containsUserset` of the query subject. Prove T1 by induction on fuel then on the AST.

**CORRECTION to Gemini:** its model used `MemberSet String` (ids = subject *names*).
That is **unsound** — `alice:user` and `alice:group` collide in `pos`. Use
`Id = String × String` (type, name) (or `SubjectRef`), and its `pop` had an unproved
injectivity `sorry`. Fix both.

**What's already proved (reusable):** `ext_union/intersect/subtract`,
`mem_ext_union/intersect/subtract` (extensional boolean cases), `containsStar_*`
(star-subject boolean cases — DONE), `ext_empty/singletonEntity/star`,
`neg_subset_starpop`.

**The remaining nut:** the INTENSIONAL distribution `containsShape (op M N) =
containsShape M ⟨op⟩ containsShape N` for concrete/ghost subjects. It needs the
well-formedness invariant `WF M := Disjoint M.pos (starpop M.stars) ∧ M.neg ⊆
starpop M.stars` (a non-WF set breaks it — concrete counterexample: `uid` in both
`pos` and the star population). `wf_normalize` (every op output is WF) is easy.
`simp; tauto` did NOT close the distribution (expanded goal too large). Intended
route: first prove a `containsShape` normal-form lemma
`WF M → (containsShape M uid shape ↔ uid ∈ M.pos ∨ (shape ∈ M.stars ∧ uid ∉ M.neg))`,
then a per-atom `by_cases` split (8 membership atoms) rather than `tauto`. Then the
leaf cases: `Direct` expand = union of `star`/`singletonEntity` over grants + the
userset flow-through recursion; `TTU` = union over stored parents. These must be
shown equal to `sem`'s `directLeaf`/`ttuLeaf` — the largest piece.

Once T1 + T2b land, **T3/T6a/T6b are already `rw`-proved** (they route through them).

---

## T4 — `pathCount_addEdge` / `pathCount_removeEdge` (self-contained, the crux)

**Plan.** Replace `opaque pathCount`: add `[Fintype V]`, define
`pathsOfLength : Nat → V → V → Nat` (`0 ↦ [u=v]`; `k+1 ↦ ∑ w, dcount u w *
pathsOfLength k w v`), `pathCount = ∑ k ∈ Ico 1 (card V + 1), pathsOfLength k`,
`phat = pathCount + [u=v]`.

**CORRECTION to Gemini:** do NOT introduce the recurrence as an `axiom` (its
`phat_def`). A custom axiom about the opaque constant fails the C4 axiom-cleanliness
gate. Prove the recurrence as a LEMMA from the definition.

**Hard core:** `phat_recurrence : Acyclic g → phat u v = [u=v] + ∑ w, dcount u w *
phat w v`. From the definition this reduces to showing the boundary term
`∑ w, dcount u w * pathsOfLength (card V) w v = 0` — i.e. **no walk of length
`card V` exists in a DAG** (pigeonhole: such a walk repeats a vertex ⇒ a closed
subwalk ⇒ `pathCount x x > 0` ⇒ ¬Acyclic). This is the genuine combinatorial lemma;
our multigraph has no Mathlib `Walk` API, so it must be built (or bridged to
`Mathlib.Combinatorics.…`). Then `pathCount_addEdge` follows by algebraic expansion
of `(A + E_{uv})` using `phat_recurrence` and the DAG condition `v` cannot reach `u`;
deletion is the exact inverse in `(ℤ,+)`.

---

## T0a — `semAux_fuel_stable_step` (subtle — Gemini's proof is WRONG here)

**CORRECTION to Gemini:** it claims "the Tarjan-lowlink guard (which sem mimics)
yields false on a revisit," so pigeonhole gives stability. **But `semAux` has NO
visited-set** — it is pure fuel recursion. Pigeonhole on the state space does not
directly apply.

**Real options:**
(a) *Monotonicity argument.* For a stratifiable schema, positive recursion is
monotone (more fuel only adds `True`, stabilizing once all grants are found via their
shortest acyclic path ≤ state-space size); negative positions (`but not` subtrahends)
are lower strata, hence acyclic and fuel-stable. Formalizing this ties `Stratifiable`
(a Kahn property on `depEdges`) to the evaluation's DAG-depth — substantial.
(b) *Refactor `semAux` to carry a visited-set* (mirroring the oracle). Then Gemini's
pigeonhole applies cleanly — but it is a SPEC CHANGE and must be re-validated by the
conformance suite before relying on it. Prefer (b) if (a) proves too hard; do it
before Phase 5.

---

## T0b — `stratify_none_iff_cycle`, `stratify_topological`

**Plan.** Standard Kahn correctness on `depEdges`/`kahn`. Forward
(`none → cycle`): if `kahn` returns `none`, the surviving `remaining` set has every
node with an out-edge into `remaining` (min out-degree ≥ 1) ⇒ a cycle (finite +
pigeonhole walk). Reverse (`cycle → none`): cycle nodes always retain an in-`remaining`
out-edge, so `readyNodes` never peels them ⇒ `remaining` stays non-empty.
`stratify_topological`: invariant that a peeled layer's nodes depend only on
already-peeled nodes. Check `Mathlib.Combinatorics` / `Order` for reusable
topological-sort / acyclicity lemmas before hand-rolling.

---

## T2 / T5 — `graph_reached_inv`, `graph_correct`, `cascade_converges`

**Plan (largest, Phase 4).** Replace `opaque GraphState`/`Inv`/`GraphModel.check`/
`ReachedBy`/`Quiescent` with concrete definitions:
- `GraphState := { edges : DirectGraph NodeKey, residues : … → Option Residue,
  outbox : … }` (`NodeKey = (type,name,pred,variant)`; `Residue = (stars, neg, upos)`).
- `GraphModel.check` = the ≤4-probe edge read + residue path (§7.5–7.6).
- `Inv` = the I-series (I1 count algebra via `pathCount`, I2 `Acyclic`, I6 residue
  hygiene `neg ∩ edge-holders = ∅`, etc.).
- `ReachedBy` = fold of the write ops (with cascade) from empty.

**T2b** (`graph_correct`): case analysis on subject kind. Bare subject: edge-hit ⇒
allow, justified because `Inv.residueHygiene` gives `neg ∩ edge-holders = ∅` (the
edge fast-path ≡ full residue). Star/userset: residue = `ext_normalize` by `Inv`, so
equals `sem`. Uses T4 (edges = path counts) and the T1 MemberSet lemmas.
**T2a/T5**: induction over ops; cycle-rejection preserves `Acyclic`; `runCascade`
descends strata (lower strata immutable while higher evaluate) ⇒ quiesces in
`|strata|` rounds.

---

## Suggested order

1. **T4** (self-contained; the crux; unblocks T2b's edge reasoning).
2. **T1** (scaffolding mostly proved; unblocks T3/T6).
3. **T0b** (self-contained graph theory).
4. **T2/T5** (largest; needs T1 + T4).
5. **T0a** (decide (a) vs (b) first).
