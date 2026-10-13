---
id: TK138
title: A userset is not related to itself here; OpenFGA treats doc:1#viewer@doc:1#viewer as implicit
brief: check(doc:1#viewer, viewer, doc:1) is False here; OpenFGA treats a userset as implicitly related to itself
pri: LATER
size: M
deps: []
related: []
parent:
labels: []
source: docs/openfga-claims-audit-2026-10-13.md
source_hash:
created: 2026-10-13c
moved: 2026-10-13c
updated: 2026-10-13c
closed:
---

Found by the 2026-10-13 OpenFGA claims audit; `docs/openfga-claims-audit-2026-10-13.md`
sec 2 fact 5 and sec 4 item 2.

PROBE (first-hand): with `define viewer: [user, doc#viewer]` and no tuples,
`check(doc:1#viewer, viewer, doc:1)` is False on the set engine and the oracle (graph not
probed). OpenFGA's `pkg/tuple/tuple.go::IsSelfDefining` treats
`document:1#viewer@document:1#viewer` as implicit (its API refuses to store it "because
they are implicit"), so its check answers true. That last step is REASONED from the RFC
`tuple.go` cites (openfga/rfcs 20240328-queries-with-usersets), not run against a server.

Not an equivalence bug: all three backends agree. It is an OpenFGA-parity question, so
decide whether to adopt the reflexive reading (all backends + oracle + Lean model, a
semantic change) or to document it in `docs/spec-deviations.md` and the PyPI README.
Verify against a real OpenFGA server first.

## Read first

- `docs/openfga-claims-audit-2026-10-13.md` (sec 2 fact 5, sec 4 item 2).
- `docs/spec-deviations.md` (the 2026-07-13 self-referential entry).

## Log
