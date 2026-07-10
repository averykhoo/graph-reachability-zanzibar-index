import ZanzibarProofs.GraphIndex.RulesComplete

/-!
# The derived reconcile — the residue path (ROADMAP W3)

`SEMANTICS.md` §7.6, §7.8; `index_v4/processor.py` (`reconcile` / `reconcile_subject`).
W1 widened the write model to wildcard bridges; W2 to untainted rule routing. **W3
widens it to DERIVED relations** — `and` / `but not` (the `.inter` / `.excl` nodes) —
by transcribing the processor's incremental reconcile of the per-key residue
`(stars, neg, upos)` and the derived edges.

## The residue read (recap, `State.lean:probeDerived`)

A derived `(object, relation)` carries a persisted residue and is read by
`probeDerived`, whose canonical membership form (§7.6, `theory.md:117-133`) is

    members = edges ∪ upos ∪ ( ⋃_{σ∈stars} population(σ) ∖ neg )

- object wildcard on derived → `False` (decision-15).
- `'*'` subject → `(type,pred) ∈ stars` (intensional).
- userset subject → `∈ upos ? True : shape ∉ stars ? False : ∉ neg` (edge-free, P4).
- bare subject → **edge probe first** (a hit returns `True` *without* consulting
  `neg`, the I6 disjointness) else `stars ∖ neg`.

## Sub-staging (this file starts W3a)

- **W3a — star-free, bare-subject derived booleans (THIS INCREMENT).** With no star
  data the processor stores **no residue row** (`stars = neg = upos = ∅` ⇒
  `_store_residue` is never called, I6's non-empty clause), so the state stays
  `ResidueEmpty` and a derived relation only adds **edges**. The derived read then
  collapses to the *bare edge probe* (`probeDerived_residueEmpty` below), and a
  derived edge is structurally an ordinary `writeDirect ⟨s, R, o⟩` — so W3a reuses
  **all** of W2's write + preservation machinery. The genuinely-new content is the
  *correspondence*: the reconcile materialises a derived edge for `s` **iff** `s`'s
  full boolean evaluation (`.inter`/`.excl` over the — untainted, single-stratum —
  sub-relations) is `sem`-true. That is the next increment.
- **W3b — userset subjects → `upos`** (edge-free userset members, the P4 rule).
- **W3c — star data → `stars` / `neg`** (star coverage minus per-subject exclusions;
  the concrete-only-exclusion-does-not-defeat-`*` rule, §5.4).
- **W3d — multi-stratum cascade** (nested derived, the cross-key re-reconcile hazard,
  the non-empty-outbox drain = contentful T5).

Attack-first (2026-07-10, machine-checked `#eval` vs `sem`, then deleted): on a
`doc#viewer := member but not banned` (both direct) star-free store, `check` (routed
to `probeDerived`) equals `sem` on every query — derived edge materialised for the
member-not-banned subject, none for the banned one, residue empty. No refutation.
-/

namespace Zanzibar

namespace GraphModel

/-- **The derived read on an empty-residue state is the bare edge probe.** With no
    persisted residue at `(objNode o R, R)` the residue defaults to `Residue.empty`,
    so every `stars`/`neg`/`upos` lookup is `false`: an object-wildcard, a `'*'`
    subject, and a userset subject all read `False`, and a bare (non-`'*'`) subject
    reduces to the reachability probe `subjNode s → objNode o R`. This is the W3a
    collapse of the residue path — the derived read becomes a pure edge probe. -/
theorem probeDerived_residueEmpty {σ : GraphState} (q : Query)
    (hre : σ.residue (objNode q.object q.relation) q.relation = none) :
    probeDerived σ q =
      ((q.object.name != STAR) && (q.subject.name != STAR)
        && (q.subject.predicate == BARE)
        && σ.reach (subjNode q.subject) (objNode q.object q.relation)) := by
  unfold probeDerived
  simp only [hre, Option.getD_none]
  by_cases ho : q.object.name = STAR
  · simp [ho]
  · by_cases hs : q.subject.name = STAR
    · simp [ho, hs, Residue.empty]
    · by_cases hb : q.subject.predicate = BARE
      · simp [ho, hs, hb, Residue.empty]
      · simp [ho, hs, hb, Residue.empty]

/-- **The derived read on a globally `ResidueEmpty` state.** Corollary of
    `probeDerived_residueEmpty` specialised to the W3a fragment, where the whole
    residue table is empty. -/
theorem probeDerived_ResidueEmpty {σ : GraphState} (hre : ResidueEmpty σ) (q : Query) :
    probeDerived σ q =
      ((q.object.name != STAR) && (q.subject.name != STAR)
        && (q.subject.predicate == BARE)
        && σ.reach (subjNode q.subject) (objNode q.object q.relation)) :=
  probeDerived_residueEmpty q (hre _ _)

/-- **The derived-relation read on an empty-residue state.** For a query whose
    `(object.type, relation)` is derived (tainted), `check` routes to `probeDerived`;
    on an empty residue that is the bare edge probe. So on the W3a fragment a derived
    read is decided by the same reachability the non-derived read uses — the residue
    machinery is provably inert. -/
theorem check_derived_ResidueEmpty {σ : GraphState} (hre : ResidueEmpty σ) (q : Query)
    (hder : isDerived σ.schema (q.object.type, q.relation) = true) :
    check σ q =
      ((q.object.name != STAR) && (q.subject.name != STAR)
        && (q.subject.predicate == BARE)
        && σ.reach (subjNode q.subject) (objNode q.object q.relation)) := by
  unfold check
  simp only [hder, if_true]
  exact probeDerived_ResidueEmpty hre q

end GraphModel

end Zanzibar
