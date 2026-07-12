# Overnight session review — formal verification

**For your one-shot morning review.** This summarizes everything done in the
autonomous session of 2026-07-09→10. The living detail is in `PROOF_STATUS.md`; this
is the "what happened and what to check" digest. Everything below is committed and
pushed to `master`; the tree is green at every commit.

**Verify it yourself in one command:** `bash formal/verify.sh` (builds the Lean
library + CLI, prints the axiom audit, runs the Python conformance suite). It passed
when this was written.

---

## Headline

- The Lean development **builds green** (Lean 4.31 + Mathlib, 659 jobs), all theorems
  T0–T6 **stated**, **9 tracked `sorry`s** on the deep theorems.
- The specification `sem` is **empirically validated against your oracle AND the real
  set engine**: 12 handwritten schemas × 3 evaluators + 12 schemas × 25 random stores
  = **48 conformance tests green**, agreeing on every query-grid point.
- **A real spec bug was found and fixed** (see below) — the whole reason the "validate
  before proving" phase exists.
- Genuinely **proved** (axiom-clean, no `sorry`): the full `MemberSet` star-closed
  algebra, wildcard type-scoping (T6c), and `sem` fuel-stability reduced to one lemma.
- Deep theorems (T1, T2a/b, T4, T5, the T0a pigeonhole core, T0b Kahn) remain honest
  `sorry`s — they need the large model constructions and are genuinely multi-hour/
  multi-day proofs. **None are faked.**

## The bug (this is the important one)

Gemini reviewed the Lean spec and flagged `fuelBound`. I **confirmed it empirically**:
a schema whose per-object computed-relation chains are linked across an m-object parent
chain by TTU evaluates to depth ~n·m; my additive `fuelBound = |keys| + 2|T| + 4` (=29
at n=m=8) cut the evaluator off early, so `sem` returned **false** where your oracle
returns **true** (depth 64). Root cause: the recursion depth is bounded by the
`(entity × relation)` state space — a **product**, not a sum. Fixed to
`|keys| · (2|T| + 4)`; added a `deep_grid` regression to the corpus; the randomized
fuzzer (25 seeds/schema) found no further divergences. The shallow original corpus is
why it slipped past the first conformance pass — lesson logged.

This is exactly the class of latent trust-root bug the conformance phase is designed to
catch, and it validates doing conformance before the deep proofs.

## What's proved vs. deferred

**Proved (real theorems, axiom-audited):**
- `MemberSet.ext_normalize`, `ext_union/ext_intersect/ext_subtract`, the star laws,
  and the star×boolean intensional table (`containsStar_union/intersect/subtract`) —
  the workhorse algebra for T1. Membership + constructor lemmas (`mem_ext_*`,
  `ext_empty/singletonEntity/star`, `neg_subset_starpop`).
- `restrictionMatches_type` / `wildcard_scoping` (**T6c**): a `T:*` grant matches only
  subjects of its own type. Axiom surface `[propext, Quot.sound]`.
- `sem_fuel_stable` (**T0a**): PROVED from a single pigeonhole step lemma
  (`semAux_fuel_stable_step`) by `Nat.le_induction`.
- `backend_equivalence` (**T3**), `exclusion_effective` (**T6a**), `no_ghost_grant`
  (**T6b**): proved by `rw` through T1/T2b — they become unconditional the moment
  T1/T2b are discharged.

**The 9 `sorry`s (deep theorems, honestly deferred):**
- `semAux_fuel_stable_step` (T0a pigeonhole core), `stratify_none_iff_cycle` +
  `stratify_topological` (T0b Kahn) — `Spec/WellDef.lean`.
- `setEngine_correct` (T1) — needs the concrete MemberSet-expand model.
- `pathCount_addEdge` + `pathCount_removeEdge` (T4 counting) — `GraphIndex/Closure.lean`.
- `graph_reached_inv`, `graph_correct`, `cascade_converges` (T2a/T2b/T5) — need the
  concrete graph state machine.

## Decisions made (rationale — flag any you dislike)

1. **Spec `sem` is fuel-primitive-recursive**, mirroring the oracle's depth-bounded
   provisional-False recursion. Faithful and total. (§ Semantics.lean)
2. **Binary `union`/`inter` AST** instead of n-ary (associativity + WF arity≥2 ⇒
   faithful; no empty-fold fail-open).
3. **Backend models are `opaque` placeholders** (`SetEngineModel.check`, `GraphState`,
   `Inv`, etc.) so T1/T2 aren't vacuous; Phases 3–4 replace them with real defs.
4. **Rejected Gemini's `phat_def` axiom** for T4. A custom axiom about the opaque
   `pathCount` would violate the C4 axiom-cleanliness gate; instead the first-edge
   recurrence is recorded as the Phase-4 proof strategy (define `pathCount`
   concretely, prove the recurrence as a lemma). The axiom audit confirms **no custom
   axioms** in the development.
5. **Adopted (corrected) Gemini's WellDef decomposition** to actually prove
   `sem_fuel_stable`; fixed the ∃-membership / defeq issues in the suggested code.
6. **A1/A4** (from SEMANTICS.md §11): cascade baked into the Lean graph write op;
   graph modeled at the connectedstore deduped-set boundary. (You approved these.)

## Honest scope note (unchanged from the plan's §7)

When T1/T2 land, the claim will be: the backend **algorithms** are proven to compute
the stratified perfect model and hence equivalent; the **Python** is pinned to those
models by conformance (48 tests here) + correspondence review. The interner/bitmap
layer and SQL/concurrency are out of the Lean scope, conformance-pinned. Nothing here
rounds up to "the code is formally verified."

## What I'd do next

Phase 3 finish: build the concrete `MemberSet`-expand set-engine model and prove T1
using the algebra lemmas now in place (the boolean cases reduce to `mem_ext_*`; the
leaf/ghost cases need a couple more lemmas). Then Phase 4 (the graph state machine —
the hard half: T2/T4/T5). The Kahn T0b and pigeonhole T0a are self-contained and can
be attacked independently.

## Commits this session (newest first)

`c484c84` MemberSet lemmas + real T6c + axiom audit · `c8a306c` randomized fuzzing ·
`f0a4acf` **fuelBound bug fix** + regression · `895b9a7` 3-way conformance ·
`327e08e` algebra lemmas · `e43b742` Phase 1 skeleton + Phase 2 conformance ·
`d7d6941` Phase 0 SEMANTICS.md.
