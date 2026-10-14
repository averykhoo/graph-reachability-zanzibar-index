---
id: TK138
title: A userset is not related to itself here; OpenFGA treats doc:1#viewer@doc:1#viewer as implicit
brief: check(doc:1#viewer, viewer, doc:1) is False here; OpenFGA treats a userset as implicitly related to itself
pri: NEXT
size: M
deps: []
related: []
parent:
labels: []
source: docs/openfga-claims-audit-2026-10-13.md
source_hash:
created: 2026-10-13c
moved: 2026-10-13d
updated: 2026-10-13d
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

### 2026-10-13d

USER DECISION 2026-10-13d (in chat): verify against a real OpenFGA server, then ADOPT the reflexive reading. Promoted LATER -> NEXT.

Why it is False today (REASONED by the coordinator, no recorded design decision found in specs, spec-deviations or oracle): membership is defined as reachable through at least one stored tuple or rewrite (a non-reflexive closure), and writing the self tuple doc:1#viewer viewer doc:1 is refused as a cycle in the userset membership topology (AdmissionRejected), so nothing can make it True. Nobody weighed OpenFGA's reading before the 2026-10-13 audit.

Plan: (1) throwaway openfga/openfga container in WSL (never Docker Desktop; stop it after). Pin first-hand: the reflexive check; under but-not (viewer: [user, doc#viewer] but not banned); on a relation whose type restriction does not allow doc#viewer; on a computed or TTU relation; and what ListUsers / ListObjects / Expand return for it. Record every answer in a tracked doc, docs/tk138-openfga-reflexive-userset-<date>.md. (2) Adopt in set engine, graph index, oracle and the Lean model together; expected shape is a check-time identity short-circuit (no closure change, cycles still refused), but the lookup surfaces must match whatever OpenFGA returns. (3) Spec-deviations entry plus the PyPI README.
