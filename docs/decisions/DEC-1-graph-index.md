---
type: Decision
id: DEC-1
title: Graph index
actor: unrecorded
decided: 2026-07-07
session: 2026-11-03a
decision_status: BUILT
attribution: unrecorded, the log names no one; the date of the commit that wrote the heading (git blame), 2026-07-07
imported_from: docs/evidence/decision-log-normalised-2026-11-03.md
body_sha: sha256:42f77e7d3070d53fde7178bb3f0c7d5b9f25487d2ae6d450f9bac1bd546747cc
---

* **Path-counted closure rows** over interval/2-hop/PLL labelings and per-object
  bitmaps: labelings have non-constant queries and degrade under deletion; bitmap
  bits can't be ref-counted for exact removal. Under OMv-style lower bounds nothing
  gets both fast updates and fast queries — the query-optimal corner is chosen
  deliberately; multiplicative path counting is what makes removal exact.
* **Cycle rejection is a counting necessity**, not a policy: a cycle means infinite
  path multiplicity. Hence also: self-referential wildcard tuples rejected (the
  bridge+grant pair closes a loop), while object-star self-containment is fine
  (subject-role and object-role are different nodes; entity nodes have in-degree 0).
* **Split wildcard nodes** (`w_any`/`w_all`, never bridged to each other) over a
  single `*` node: prevents the instance leak (being an instance ≠ receiving what is
  distributed to instances). Interior wildcard hops are materialised as bridges so
  check stays ≤4 probes; only query-endpoint hops stay virtual.
* **Store-granularity writer lock** (`_lock_store`) over per-edge locking: the
  affected closure region is discovered while walking, so piecemeal locking in graph
  order invites deadlocks; one logical write already touches many rows.
