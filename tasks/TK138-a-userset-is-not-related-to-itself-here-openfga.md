---
id: TK138
title: A userset is not related to itself here; OpenFGA treats doc:1#viewer@doc:1#viewer as implicit
brief: check(doc:1#viewer, viewer, doc:1) is False here; OpenFGA treats a userset as implicitly related to itself
pri: NEXT
size: L
deps: []
related: []
parent:
labels: []
source: docs/openfga-claims-audit-2026-10-13.md
source_hash:
created: 2026-10-13c
moved: 2026-10-14
updated: 2026-10-14
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

### 2026-10-14

Scout + challenge + DECISION, 2026-10-14. Map: docs/tk138-userset-self-relation-2026-10-14.md ("Decision recommendation", challenge C1-C7, sections 1-8).

MEASURED (first-hand PROBE against a live OpenFGA v1.22.0 and this repo): OpenFGA treats a userset as implicitly related to itself and the rule PROPAGATES through computed seeds, ACROSS objects (model C: group:1#admin and group:3#admin are viewers of doc:1 there; False in all four corners here) and flips ALLOW to DENY on a boolean model (vx is ALLOWED here, DENIED by OpenFGA). The challenge's patched oracle (the section 3.2 disjunct) matches OpenFGA on all 9 model-C rows. C1: the planned derived-graph reconcile enumerated own-object keys only and would miss cross-object subjects; C2: the planned tests would pass that bug; C3: the claim that the ttu_leaf from-chain disjunct becomes redundant is false (undeclared TTU target on one tupleset type).

DECIDED (decide-TK138, the fable executive-decision agent per CLAUDE.md Who decides; recorded here as the decision): Option A (adopt OpenFGA semantics everywhere, the user's 2026-10-13d "verify, then ADOPT"), in TWO landings. Why: verification raised the cost, not the goal; equivalence beats parity, so any interim must move NO corner; today's gap is undocumented and security-relevant, so the cheap legible half should not wait; and three concurrent Lean edits (TK119, TK132, this) is a merge risk.
- Landing 1 (S, this session; no semantic change, no Lean, no golden): tests/test_tk138_userset_self_relation.py, a ParityEngine over models A, B, C carrying a LITERAL table of OpenFGA v1.22.0 answers, asserting today's unanimous answer AND the exact set of rows where repo != OpenFGA (a positive divergence pin, never an xfail), plus what must NOT move; sabotaged under the oracle-only sat disjunct. docs/spec-deviations.md dated entry (incl. C3 asymmetry and C6: "both refuse the exact self tuple", not "agrees"); one PYPI_README "differences from OpenFGA" line written with TK137's text.
- Landing 2 (one atomic Python + Lean change set, commit only on green): filed as child TK144.
Sub-decisions: D1 star subjects excluded (answers unchanged). D2 the spec IS the disjunct form; the section 3.1 reduction is a proof device only. D3 = D3a lookups list implicit usersets. D4 keep the ttu_leaf from-chain disjunct unchanged (no answer change, no ttuLeaf churn; C3), and record the asymmetry in spec-deviations.
Size reset M -> L (Python L + Lean XL across both landings).
TK123 IMPLICATION: settle the lookup channel inside TK123's API pass: LookupResult should carry (type, name, predicate) keys, not interned ids (an internal surrogate id is a first-user surprise regardless, and D3a needs the channel).
Child row: TK144 at LATER, deps [TK123, TK119, TK132], parent TK138. Asked for NEXT, but task.py new REFUSED it (NEXT would hold 6, budget 5); all three deps are NEXT rows, so it cannot start before a NEXT slot frees anyway. Promote it when they close.
Do NOT close TK138 on landing 1: the user's ADOPT stands until landing 2 ships. Next action: build landing 1.
