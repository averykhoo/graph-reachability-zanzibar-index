# References

The system this formalization verifies is a hybrid of Zanzibar-style relationship
reachability and Datalog¬ incremental view maintenance. Canonical sources:

## Authorization model

- **Zanzibar: Google's Consistent, Global Authorization System** — Pang et al.,
  USENIX ATC '19. https://research.google/pubs/pub48190/
  Defines `tupleToUserset` (`from` chains), computed usersets, and the `check` API.
  This system implements those semantics but replaces Zanzibar's on-the-fly
  Leopard-index traversal with an exact path-counted closure.
- **OpenFGA** (CNCF). https://openfga.dev/
  The schema DSL / 1.1 JSON the parser ingests. OpenFGA supports `and` / `but not`
  and evaluates them at read time; the graph index here materializes them at write
  time via the stratified IVM cascade.

## Path-counting transitive closure (basis of T4)

- **Maintaining Transitive Closure of Graphs in SQL** — Dong, Libkin, Su, Wong,
  1999. https://dl.acm.org/doi/10.1145/304181.304214
  Maintaining DAG reachability by counting paths — where insertion and deletion are
  exact inverses in `(ℤ, +)` — supports O(1) closure queries without re-derivation on
  delete. This is the `theory.md §1.2` counting theorem the Lean `pathCount_addEdge`
  (T4) formalizes.

## Incremental view maintenance for Datalog¬ (basis of the cascade / T5)

- **Maintaining Views Incrementally** — Gupta, Mumick, Subrahmanian, SIGMOD '93.
  https://dl.acm.org/doi/10.1145/170036.170066
  IVM for (non-monotone) views. `but not` makes the rule system non-monotone; the
  standard treatment is stratified Datalog¬ evaluated bottom-up (counting IVM / DRed).
  The delta processor's `reconcile` cascade is a direct implementation, and the Lean
  spec `sem` is the stratified perfect model these compute.

## Formalization

- **Lean 4** (leanprover) + **Mathlib** — the proof assistant and library used here.
- Stratified Datalog¬ perfect-model semantics — the denotational target `sem`
  (`docs/architecture/theory.md §1.4`).
