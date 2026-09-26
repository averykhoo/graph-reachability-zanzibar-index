---
id: TK108
title: refuse userset restrictions in tuplesets at parse too (OpenFGA rule); set engine degrades today
brief: userset restriction in a tupleset: graph refuses, set engine degrades; refuse at parse like TK106? (ask user)
pri: NOW
size: S
deps: []
related: [TK106, ASK-2]
parent:
labels: []
source: hand
source_hash:
created: 2026-09-26b
moved: 2026-09-27
updated: 2026-09-27
closed: 2026-09-27
---

**Filed 2026-09-26b by TK106 (its design decision D3, `docs/tk106-boolean-tuplesets-2026-09-26.md` § 1).**

A USERSET restriction in a tupleset (`parent: [folder#member]`) has the gap TK106 closed for boolean and computed tuplesets:
- the GRAPH refuses it at compile time (`zanzibar_utils_v1.py::_validate_ttu_tuplesets`, `UnsupportedByGraphIndex`, "tupleset relations must be directly assignable types");
- the SET ENGINE degrades past that refusal (`setengine/engine.py::SetEngine.__init__` catches `UnsupportedByGraphIndex`) and answers.

OpenFGA refuses it too (tupleset relations must be directly assignable types).

It was deliberately NOT folded into TK106, because the user approved only boolean tuplesets. The fix would mirror TK106: make it part of `_validate_tuplesets_direct` and the oracle twin, move the genswarm witnesses `tupleset-userset-restriction` and `tupleset-wildcard-userset-restriction` to `ValueError`, and re-measure the floors.

It changes which schemas are accepted, so ask the user before doing it.

## Log

### 2026-09-27

USER GO 2026-09-27: "Okay then let's refuse the shape. Just to be sure, try the other shape to accomplish the same thing and then document it somewhere." Plus a STANDING RULE in the same message: every refused shape gets a parser comment with WHY and the ALTERNATIVE. LANDED in the working tree (uncommitted): refusal at parse in both parsers (zanzibar_utils_v1.py::_validate_tuplesets_direct + tests/oracle.py::_validate_tuplesets_direct), message substring 'tupleset may not restrict to a userset' (tests/genswarm.py::TUPLESET_NO_USERSET); both genswarm witnesses moved to ValueError; tests/test_blind_audit_regressions.py::test_userset_restriction_in_tupleset_rejected now pins both parsers. REWRITE PROBED EXACT (0 of 135 answers differ, control arm 4 differ): parent: [folder] + parent_member: member from parent. Pinned by tests/test_tk108_userset_tupleset_rewrite.py (S1/S2 sabotage red). Map: docs/tk108-userset-tuplesets-2026-09-27.md. RUNNING: full census of tests/ + formal/conformance/. NEXT: census fixes, refusal-comment sweep (subagent census -> .scratch/tk108/refusal-census.md), spec-deviations entry, CLAUDE.md rule, gate.

DONE 2026-09-27 (user decision: refuse the shape; try the rewrite; document it). Both parsers refuse a userset restriction on a tupleset at parse ([folder#member], [folder:*#member], mixed [folder, folder#member]): zanzibar_utils_v1.py::_validate_tuplesets_direct + tests/oracle.py::_validate_tuplesets_direct, message 'tupleset may not restrict to a userset'. REWRITE proven exact: parent: [folder] + parent_member: member from parent (probe 0 of 135 answers differ, control 4 differ), pinned 4-way in tests/test_tk108_userset_tupleset_rewrite.py (derived expectation: oracle over the unchecked parse of the refused schema; S1/S2 sabotage red). Documented: docs/spec-deviations.md 2026-09-27, CLAUDE.md Gotchas, the parser comment itself. Census of both suites: 0 real breakage (2 source-introspection artifacts from editing mid-run, green alone). STANDING RULE from the same user message: every refused shape carries a REFUSED SHAPE / WHY / INSTEAD comment; 42 sites swept (comments only, AST-identical, verified first-hand), enforced by tests/test_refused_shape_comments.py (3 sabotages red). MIN_TESTS_ALL 1405 -> 1421. Side finding filed: TK109 (oracle accepts 7 shapes the product refuses). Map (FROZEN on close): docs/tk108-userset-tuplesets-2026-09-27.md.
