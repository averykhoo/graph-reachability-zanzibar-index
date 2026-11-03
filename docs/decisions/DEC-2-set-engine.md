---
type: Decision
id: DEC-2
title: Set engine
actor: unrecorded
decided: 2026-07-07
session: 2026-11-03a
decision_status: BUILT
attribution: unrecorded, the log names no one; the date of the commit that wrote the heading (git blame), 2026-07-07
imported_from: docs/evidence/decision-log-normalised-2026-11-03.md
body_sha: sha256:6dafd305e46de2d7331c59915964e21e743105760dd1bd842a9bc86a93fe7479
---

* **Raw tuples (`RelationTuple`) are the ground truth**; all set state is in-memory,
  rebuilt by replay on open. Bitmap snapshot persistence rejected (opaque, duplicates
  state).
* **Reference-counted interner with recycled int32 ids**: `(type, name, predicate)`
  is the stable surrogate; memory tracks live entities, not lifetime. Never
  `isinstance`-check the underlying set type — everything goes through the `SetOps`
  seam (roaring/pyset must be indistinguishable; the matrix runs both).
* **`MemberSet (pos, stars, neg)`** carries the pinned star×boolean table:
  stars fold ∪=`|`, ∩=`&`, ∖=`-`; `pos` wins over `neg`; concrete-only exclusions
  never defeat star queries.
