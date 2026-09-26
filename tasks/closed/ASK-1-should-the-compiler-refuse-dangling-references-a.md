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
moved: 2026-09-26
updated: 2026-09-26
closed: 2026-09-26
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

### 2026-09-26

**ANSWERED by the user, 2026-09-26: YES, refuse.** Verbatim: "I think we can strictly expect schemas to be self consistent." Scope taken by the session (engineering call, per CLAUDE.md "Who decides"): refuse EVERY dangling reference, not just the matchDecl shape -- computed refs, TTU tuplesets, TTU targets, userset restriction relations (`[group#member]`), and restriction types -- in both front-ends (`zanzibar_utils_v1.py::_validate_ast_references`) and the oracle twin (`tests/oracle.py`). Not yet implemented; first step is measuring which test schemas break.

**Follow-up the user raised the same session: should `ranked` (untainted computed cycles) be refused too?** First-hand READ 2026-09-26 of OpenFGA `pkg/typesystem/typesystem.go` (main): `validateRelation` calls `HasCycle`, and `hasCycle` returns true for any cycle made of computedUserset edges on one type, walking through union/intersection/difference; only `this` and tupleToUserset stop the walk. So OpenFGA refuses `a: [user] or b` + `b: [user] or a` with `ErrCycle` ("an authorization model cannot contain a cycle"), entrypoints or not. REASONED: every `ranked` failure is refused by OpenFGA -- a cycle made only of computed edges hits `ErrCycle`, and a cycle through a TTU edge needs a tupleset with an incoming rule arm, i.e. a non-direct tupleset, which OpenFGA also refuses. So `docs/tk104-graphadmission-scope-2026-09-24.md` sec 3's "`ranked` cannot be made LOUD without refusing legitimate recursive schemas" is WRONG: nested groups (`[group#member]`) and folder hierarchies (`x from parent`) are recursion through stored tuples and emit no ranked edge. SpiceDB: its docs (authzed.com/docs/spicedb/modeling/recursion-and-max-depth) say cycles are unsupported and are caught at runtime by a 50-hop depth limit; whether its compiler refuses permission cycles was NOT verified. Waiting on the user's call on `ranked`.

**User, 2026-09-26: refuse `ranked` failures too** ("Okay yes refuse both"). So BOTH SILENT `GraphAdmission` fields become LOUD.

The user asked about OpenFGA's "boolean flag" pattern. First-hand READ, openfga.dev/docs/best-practices/modeling-abac, self-referential variant: `define sso_enabled: [organization]` / `define can_use_sso: member from sso_enabled`, with tuple `organization:acme#sso_enabled@organization:acme`. The recursion is in the DATA, a tuple from an object to itself. In the schema, `sso_enabled` is direct-only, so the rule edge sso_enabled -> can_use_sso is acyclic and nothing dangles. The pattern is unaffected and gets a must-still-accept pin, next to nested groups (`[group#member]`) and folder hierarchies (`viewer from parent`).

OpenFGA rules mirrored (first-hand READ `pkg/typesystem/typesystem.go::isUsersetRewriteValid` / `::validateTypeRestrictions` / `::hasCycle`): computed ref declared on the same type; TTU tupleset declared on the same type; TTU target declared on at least one type the tupleset admits; every restriction type declared; a `[T#P]` restriction needs P declared on T; no cycle of computed/TTU-tupleset references. NOT adopted here: OpenFGA's "a tupleset must be direct-only" rule, which is `ttuDirect`, a different field and not a dangling reference.

ANSWERED and IMPLEMENTED 2026-09-26: schemas must be self-consistent. Both parsers refuse dangling relation references (computed ref, TTU tupleset, TTU target, [T#P]) and any cycle of computed / TTU-tupleset references: zanzibar_utils_v1.py::_validate_ast_consistency (DSL + JSON front ends) and the oracle twin tests/oracle.py::_validate_consistency. GraphAdmission matchDecl and ranked are now LOUD (LOUD 12 / MIXED 2 / SILENT 0); test_conformance_fragment.py (K) ties the refusal to Lean via the report. Not refused, by design: undeclared bare restriction types, and OpenFGA's direct-only-tupleset rule (that is ttuDirect). Reports, the conformance encoder and grammar tests read the new _parse_schema_ast_unchecked / oracle.parse_schema_ast_unchecked. Census 57 failed + 1 error, all resolved; no curated corpus refused. Mutation sweep 16/16 caught with an M0 control. Floors: MIN_TESTS_ALL 1328, MIN_CONF_ALL 1038 (REST 903). Map: docs/ask1-schema-self-consistency-2026-09-26.md.
