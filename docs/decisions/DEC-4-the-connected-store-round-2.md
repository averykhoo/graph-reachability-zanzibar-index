---
type: Decision
id: DEC-4
title: The connected store (round 2)
actor: unrecorded
decided: 2026-07-07
session: 2026-11-03a
decision_status: BUILT
attribution: unrecorded, the log names no one; the date of the commit that wrote the heading (git blame), 2026-07-07
imported_from: docs/evidence/decision-log-normalised-2026-11-03.md
body_sha: sha256:5e14a5feda2ff683e427b8bbb9f3f7755ce252e7f02f058493e34eea7b21db8c
---

* **Source-of-truth / materialized-view split** (Zanzibar/Leopard): tuples live in
  `RelationTuple` + a permanent log; the graph index is downstream and owns nothing.
  "Reconstruct tuples from the index" was rejected — likely possible in principle
  (topo-order peeling with path-count subtraction) but it's the whole forward engine
  reimplemented in reverse, kept bug-for-bug in sync forever, to recover data one
  table keeps losslessly.
* **Schemas are static, write-once, stored as SOURCE** (`SchemaRecord`); compiled
  artifacts are cache (closures can't be persisted; stored compiled state is a
  drift surface — the `family`-column argument again). A new schema = a new
  store/index built from the tuples; no versioning, no migration.
* **The tuple log is permanent** (audit + replay + token domain; human-scale
  volume); bootstrap-from-snapshot keeps builds independent of log length, so
  compaction stays a hook.
* **One apply step, two schedules**: sync = the async worker inlined into the write
  transaction. The coupling is a temporary *schedule*, not temporary machinery.
* **Validity at admission** keeps the log replayable: the write path enforces full
  parity (incl. graph-cycle rejection via the set engine's flow graph), so an
  apply-time rejection is a corruption signal — no dead-letter mechanism.
* **Exactly-once by transactionality**: applied rows + cursor advance commit
  together; the applier locks the index store before reading the cursor
  (lost-update prevention).
* **Freshness tokens are log ids** (zookie-lite): index serves iff cursor ≥ token,
  else the set engine answers fresh — Leopard's timestamp merge simplified to a
  fallback. (Round 3 makes the fallback O(delta) and honors `at_least` on
  `TupleSource.check` too.)
