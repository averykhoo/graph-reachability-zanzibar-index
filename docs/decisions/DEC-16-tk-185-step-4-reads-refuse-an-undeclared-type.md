---
type: Decision
id: DEC-16
title: 'TK-185 step 4: reads refuse an undeclared type or relation -- class, rules, choke points'
actor: agent (claude-opus-5-5)
decision_status: ACCEPTED
refs: [TK-185]
decided: 2026-11-20
session: 2026-11-20a
body_sha: sha256:9ad051ecb3a4d18a7fe7494e6972fc0792791b3641765669abb036c5f0820bd7
---

TK-185 step 4 (C5 + C7) carries out the owner's decision of 2026-11-01: a READ that names an undeclared TYPE or RELATION is an ERROR. This record settles the design points the row left to the session (CLAUDE.md "Who decides"). Equivalence comes first throughout: both backends refuse the same calls with the same message, and no answer is computed before the refusal. Map: `docs/tk185-0.1.3-batch-2026-11-20.md` step 4.

1. **Exception.** `UndeclaredTypeOrRelation(ZanzibarError, ValueError)` lives in `src/zanzibar/schema/errors.py` and is exported from `zanzibar`. It is a ValueError because refusals are ValueErrors (TK164). The name says which names it covers: it is never raised for an unknown object or subject NAME (`doc:999` still matches nothing). Attributes: `method`, `role` (`subject`, `object` or `filter`), `type_name` and `relation` (None for a type-only refusal). The message reuses the write side's facts (`schema/syntax.py::no_restriction_reason`, i.e. "type 'doc' declares no relation 'vewer'; did you mean 'viewer'?" and "type 'alice' is not declared in the schema"). So a read and a write that make the same mistake are told the same thing.

2. **What is checked.**
   - Subject: the subject type must be declared. A subject predicate of `None` or `'...'` means bare. Any other predicate must be a relation declared on the subject type; that covers `group:eng#nosuch`, and a leaf predicate such as `viewer.0`, which is never declared.
   - Object: the object type must be declared, and the relation must be declared on it. A type that declares no relations, such as `type user`, cannot be a read's object.
   - `lookup` filters: `object_type` must be a declared type. `relation` must be declared on `object_type`, or on some type when `object_type` is None.
   - `lookup_reverse` filters: `subject_type` must be a declared type. `subject_predicate` None means no filter and `'...'` means bare; any other value must be declared on `subject_type`, or on some type when `subject_type` is None.
   - `expand(relation, object_type, object_name)` checks the object pair.
   - `SetEngine.filter_result` filters follow the lookup rules.
   - Wildcard names (`user:*`, `folder:*`) are NAMES: only their types and relations are checked.

3. **The C5 hint.** When the subject TYPE is undeclared and either the predicate slot holds a declared type or the name slot holds `'...'`, the message adds: "a result key is (type, name, predicate); check takes (subject_predicate, subject_type, subject_name, relation, object_type, object_name)", followed by the corrected call. That is exactly the shape of `check(*result_key, ...)`.

4. **Where (the choke points).** One shared validator in the schema layer is called:
   - at the top of the public `Store.check` / `lookup` / `lookup_reverse` / `expand`, after argument parsing and type checks and BEFORE token validation, freshness, or any dispatch;
   - at the top level of `SetEngine.check` / `lookup` / `lookup_reverse` / `expand` / `filter_result`. `TupleSource.check` goes through `SetEngine.check`.

   Both backends validate against the SAME `DeclaredRelations`, the set engine's own (built from the AST plus the declared `type` lines). That is why they refuse identically, and why `Store.check`'s set-engine fallback (stalled or tokened-lagging index) cannot change the outcome: the refusal happens before the backend is chosen.

   An order consequence, deliberate and pinned: on a stalled index, a typo'd lookup raises `UndeclaredTypeOrRelation`, not `IndexStalled`. A refusal of the CALL comes before the state of the index.

5. **`WildcardIndex` stays lenient** (it keeps answering False / empty). Its own docs describe it as a study and measure surface, not an application read path. It holds no declared-types set. Its internal callers read candidate predicates off node rows. Its read methods are Lean-modelled and content-pinned. `Store` is its only supported caller, and `Store` validates. The graph's reference page says so.

6. **Lean.** No model change (REASONED). The models are answer-level over declared queries, and the refusal adds a precondition at the API boundary. The algorithm is unchanged. Content pins that move with the validator call (`SetEngine.check` / `expand` / `lookup_reverse`) are regenerated deliberately, and their `CORRESPONDENCE.md` rows are re-read.

7. **Tests.** Grids that read undeclared pairs and expected False are a SPEC change, not a refactor (owner, 2026-11-01). Either they are filtered to declared pairs, or the undeclared cells become pinned refusals. Each change is recorded in the plan doc and the commit message. `tests/oracle.py` stays independent and lenient.
