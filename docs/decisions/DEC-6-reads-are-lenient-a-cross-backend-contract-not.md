---
type: Decision
id: DEC-6
title: Reads are lenient — a cross-backend contract, not a per-backend default
actor: unrecorded
decided: 2026-08-29
session: 2026-11-03a
decision_status: BUILT
attribution: unrecorded, the log names no one; the date of the commit that wrote the heading (git blame), 2026-08-29
imported_from: docs/evidence/decision-log-normalised-2026-11-03.md
body_sha: sha256:6010317501bb144728788e1872287be0b0227ecc434e1c246b7340bc6e4eeb08
---

* **An undeclared `(type, relation)` reads as constantly false on every surface, and
  never raises.** Enforced in three independent places, deliberately: the graph index
  denies rather than raising (`src/zanzibar/graphindex/wildcard.py::WildcardIndex.check`, whose
  docstring gives the reason — writes are already fenced by `RuleSet.apply` /
  `SetEngine.add_tuple`, so a read has nothing to protect); the set engine returns
  `False` on a missing AST entry (`src/zanzibar/setengine/engine.py::SetEngine.check`); and the
  oracle does the same by the same construct (`tests/oracle.py::Oracle.check.sat`),
  which is what lets it stay an independent reference. Writes are the strict side —
  `validate_write_identifiers` polices the charset there.
* **Rejected: schema type checking that makes a non-match an ERROR.** The open
  question (*should every relation resolve to a single type, or should we duck-type?*)
  is real, but it is not an additive validation: raising on a non-match **changes the
  read contract on all three surfaces at once**, and the oracle's copy would have to
  change separately or the independence contract breaks. Adjudicate any such proposal
  against this bullet first; the leniency is load-bearing, not an omission.
* ⚠ **Do not read this as the other "lenient" in this file.** `lenient ∀⇒∃` in the
  non-goals below is the wildcard vacuity mode and is unrelated to read leniency.
