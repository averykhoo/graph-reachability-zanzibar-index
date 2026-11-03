---
type: Decision
id: DEC-3
title: Boolean relations in the graph index (the IVM build)
actor: unrecorded
decided: 2026-07-07
session: 2026-11-03a
decision_status: BUILT
attribution: unrecorded, the log names no one; the date of the commit that wrote the heading (git blame), 2026-07-07
imported_from: docs/evidence/decision-log-normalised-2026-11-03.md
body_sha: sha256:93d838577fca87eeffa2cede28062b2c401a5d2441d8d31c5b7f33692070a921
---

* **Materialisation as ordinary edges in the SAME closure** over check-time
  expression evaluation: check-time eval can't support anything *downstream* of a
  boolean (TTU over a boolean viewer, userset restrictions, nested booleans).
  Materialised derived edges re-enter the closure and emit their own deltas, which
  drive the next stratum. Strata are logical, never physical — one store, one
  transaction.
* **Taint propagates** (a pure union over a boolean relation is derived): star-covered
  members have no edges, so compiling it normally would silently drop them.
* **Symbolic state is a per-object residue row** (`stars`, `neg`, `upos`) — not
  derived w-edges (splits one relation's symbolic state across two writers +
  bridge-GC interactions), not extensional star expansion (unbounded, ghost-wrong,
  and cycle-creating for self-including universals).
* **Deltas are invalidation signals, never state transfers**; reconciliation is
  recompute-from-committed-state, idempotent. The §5.4 rule is load-bearing: a
  symbolic delta must reconcile the concrete edge-holders on that object, not just
  the residue (blocked:`[user:*]` arriving produces no concrete delta for bob, yet
  must revoke his edge).
* **Canonical representation**: star-covered members hold no edges (residue answers);
  uncovered bare-entity members hold an edge iff true; **userset members never hold
  edges** — a derived edge from a userset node would leak through the closure past
  each member's own pointwise exclusion, so true userset memberships live in the
  residue's `upos` (pos-without-transitivity; blind-audit P4/D2). Required for
  permutation invariance and the "star-only members: zero edges" space rule.
* **Synchronous v1, in-transaction outbox cascade**; no SAVEPOINTs (a failed
  reconcile must abort the whole write; SAVEPOINT-per-delta is the future async
  worker's tool, noted with the pysqlite transaction-boundary caveat).
* **Stratification is mandatory**; recursion through a boolean relation is a compile
  error. Termination of the cascade follows from idempotent reconciliation; the
  quiescence assert enforces it.
* **Namespacing lives in the predicate name** (`<relation>.<index>`, `.` reserved in
  declarations); classification is the compiled namespace map keyed
  `(object_type, predicate)` — no `family` column (a drift surface duplicating
  name-derivable information).
* **TTU parents = stored tupleset tuples** (oracle-pinned Zanzibar semantics).
  Storage leaves are split from rule-routed leaves so "stored tuples of a derived
  relation" is a well-defined edge set. This is also why decision 15's rejection of
  derived-tupleset TTUs could be lifted (the frozen acceptance event required it):
  parents are data-bounded stored tuples, not an object-star-shaped computed set.
* **Raw-tuple set semantics at the API boundary** (duplicate add = no-op) while the
  core stays ref-counted: two *different* raw tuples may rewrite to the same derived
  edge, so counts are load-bearing internally — but Zanzibar raw tuples are a set.
* **Scope hooks, not features**: object wildcards on derived relations and wildcard
  usersets over derived relations both need symbolic composition through residues
  (a symmetric subject-keyed residue) — loud compile errors until someone builds it.
