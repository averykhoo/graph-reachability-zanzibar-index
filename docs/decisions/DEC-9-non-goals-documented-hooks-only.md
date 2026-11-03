---
type: Decision
id: DEC-9
title: Non-goals (documented hooks only)
actor: unrecorded
decided: 2026-07-07
session: 2026-11-03a
decision_status: BUILT
attribution: unrecorded, the log names no one; the date of the commit that wrote the heading (git blame), 2026-07-07
imported_from: docs/evidence/decision-log-normalised-2026-11-03.md
body_sha: sha256:4b807f95c11a552a66b1469c8939212bd272bb4f3d181ced4f762c0cb050020f
---

Async outbox workers; exposing derived-relation deltas to external consumers;
cross-query caching; snapshot ("at exactly") reads and cross-store zookies (the
zookie-lite log-id token and multi-instance catch-up ARE built — see round 3);
automatic outbox pruning; residue GC beyond empty-row deletion; lenient ∀⇒∃; a
`family` metadata column; Rete-style general incremental matching; 64-bit id space;
query-time node interning.

**Rejected outright, with no hook — OpenFGA conditions.** Listed apart because the
heading above promises hooks, and this one has none: `src/zanzibar/schema/` raises on
a conditional type at parse time. The reason has never been written down and is not a
matter of effort. **Conditions are evaluated at CHECK time; the graph index
materializes the closure at WRITE time** — that is the whole basis of its O(1)
`check` — so a condition depending on request context cannot be folded into a
materialized closure at all. That makes "should we support conditions" a question
about **which backend could host them**, not a feature to schedule: the set engine
evaluates per call and memoizes nothing across queries, so it is the only plausible
home, and supporting them on one backend would break the identical-semantics contract
the two backends exist to hold. Anyone reopening this starts there, not at the parser.
