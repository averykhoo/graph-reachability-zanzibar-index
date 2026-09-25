---
id: ASK-1
title: should the compiler refuse dangling references, as OpenFGA does?
brief: product call: refuse dangling references (makes matchDecl LOUD) or keep reporting them?
pri: LATER
size: S
deps: []
related: [TK104]
parent:
labels: []
source: hand
source_hash:
created: 2026-09-25
moved: 2026-09-25
updated: 2026-09-25
closed:
---

**Question for the user (product behaviour, not an engineering call):** should the schema
compiler REFUSE a dangling reference, the way OpenFGA does? That is a computed reference or
TTU tupleset naming a relation the schema never declares, e.g.
`define viewer: [user] or editor` with no `editor`.

Today both backends and the oracle accept it and treat the undefined relation as empty, so
answers are consistent. But it is outside the proved scope: `GraphAdmission.matchDecl` fails,
so no headline theorem covers such a schema. Since 2026-09-25 (`TK104`) an operator can SEE
this through `zanzibar_utils_v1.py::graph_admission_report`.

- **Yes:** one check in `zanzibar_utils_v1.py::_validate_ast_references` (plus the oracle's
  twin), and `matchDecl` becomes LOUD. It rejects schemas that work today.
- **No:** the report stays the only signal, and nothing changes.

Recorded as NOT the model's call in `docs/tk104-graphadmission-scope-2026-09-24.md` sec 3.
The sibling SILENT field `ranked` (untainted computed cycles) cannot be made LOUD without
refusing legitimate recursive schemas, so it is not part of this question.

## Read first

- [`docs/tk104-graphadmission-scope-2026-09-24.md`](../docs/tk104-graphadmission-scope-2026-09-24.md) -- sec 3, why this is not the model's call
- `zanzibar_utils_v1.py::graph_admission_report` -- what an operator sees today

## Log
