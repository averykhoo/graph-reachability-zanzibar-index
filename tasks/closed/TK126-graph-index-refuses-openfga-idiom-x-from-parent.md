---
id: TK126
title: graph index refuses OpenFGA idiom: x from parent, where x names a boolean relation on any type
brief: graph refuses a TTU whose target name is a boolean relation on ANY type; set engine accepts (scope gap)
pri: LATER
size: L
deps: []
related: [TK122]
parent: TK127
labels: [formal]
source: hand
source_hash:
created: 2026-10-07b
moved: 2026-10-08
updated: 2026-10-08
closed: 2026-10-08
---

The graph index refuses a relation `x from parent` whenever `x` is also the name of a boolean
(`and` / `but not`) relation on ANY type. That includes an unrelated type, and the common
OpenFGA idiom where every type defines its own `viewer`. The set engine accepts the same schema
(AGENT, probe variants B/C). The refusal comes from a deliberately name-based, type-agnostic
check (`src/zanzibar/schema/compiler.py::_validate_ttu_tuplesets`, per its comment, AGENT
read). Its message blames "an undeclared tupleset relation", which cannot be the cause any
more. A second form, `define viewer: ([user] or viewer from parent) but not banned`, crashes in
BOTH backends with an internal-object `ValueError: Rule then-pattern carries a derived subject
predicate`, from a check documented as unreachable (CONFIRMED graph side, 2026-10-07).

By `CLAUDE.md` sec "Who decides", variants B/C are a SCOPE gap, where the graph refuses what the
set engine serves; variant D is an unreachable-by-design error being reached. Default
assumption: the Python is too coarse (a TTU's target should be resolved on the tupleset's
member types, not by name across all types). Narrowing the refusal is NOT the fix.

**Next action:** read `_validate_ttu_tuplesets`, `boolean.py::compile_boolean_schema` and the
Lean `ttuDirect` / I5 exclusivity model. Decide whether a type-aware check is sound, and record
the decision on this row. Meanwhile, the messages should at least say what is true and name
the workaround (rename the boolean relation).

## Traps

- (!) The graph-admission scope is pinned against Lean (`formal/conformance/test_graphadmission_scope_pin.py`,
  `test_conformance_fragment.py`). Widening it changes those pins and possibly the Lean
  decider. Follow `formal/CORRESPONDENCE.md` sec 8 and do not let the model drift.
- (!) Variant D must become either served or a proper `REFUSED SHAPE` with WHY/INSTEAD in
  both parsers. An internal-object dump is never the user-facing answer.

## Read first

- [`docs/pypi-trial-0.0.2-2026-10-07.md`](../docs/pypi-trial-0.0.2-2026-10-07.md) sec 1 B1 (the three variants and the exact schemas).
- `CLAUDE.md` sec "Who decides" (equivalence is the goal; a divergence means fix the Python).

## Log

### 2026-10-07d

Design scouted read-only 2026-10-07d: docs/tk126-ttu-target-boolean-name-2026-10-07.md (ACTIVE-PLAN, claims labelled READ/PROBE/REASONED). Recommendation: design (a), type-aware I5 subject check + _validate_ttu_tuplesets, serve B/C/D; probes showed 0 mismatches vs the oracle on every path tried. DECISION (2026-10-07d, delegated per CLAUDE.md Who decides): adopt (a) -- equivalence is the goal and the name key is not load-bearing. Implementation follows under TK127.

### 2026-10-08

Design (a) IMPLEMENTED 2026-10-08 (uncommitted; gate not run). LANDED: boolean.py compile_boolean_schema I5 subject check keyed on (type, relation) via new _rule_subject_types_fn (types read off emitted Filters, unioned with _member_types; NAME-test fallback when unpinned); compiler.py _validate_ttu_tuplesets type-aware, new message + REFUSED SHAPE/WHY/INSTEAD (block count unchanged). B, C, D and neighbours D_nested/B_star/C_cross/C_team/SlXt SERVED. New pin module tests/test_tk126_ttu_target_name_collision.py (48 tests: ParityEngine 4-way paranoia, ConnectedStore sync+async, build_index bulk+incr, rebuild_index, lookups, cyclic neighbours, 4 hand-built R1 guard tests); RED pre-fix 32 failed/10 passed; sabotage S1-S8 recorded in its docstring. Pins: PYTHON_OUTCOME mixed-member-types -> ADMITTED; TK116 witness retired to UNREACHABLE (12 sites = 8+4); dated notes in test_w4fragment_scope_pin.py, Leaf.lean, LeafRules.lean, CORRESPONDENCE.md (isPure row, row 442, new sec 7.1 TK126 entry), docs/spec-deviations.md 2026-10-08. lake build Leaf+LeafRules OK; statement pin 58/58 + 280/280. Follow-ups filed: TK132 (a+, LATER), TK133 (term widening, SOMEDAY). OWED by orchestrator: claim_rot.py --generate (compile_boolean_schema, _validate_ttu_tuplesets bodies changed; SlXt + test anchor new), doc_counts regenerate, full gate + fuzz, PG leg.

TK127 review follow-up (fix-tk127, 2026-10-08). (1) Fuzz coverage: tests/test_hypothesis.py::_TUPLESET_BODIES gained folder-only (the one body without doc); _schema_ast declares every name PLAIN on folder for it (ASK-1). New _is_tk126_new detector + test_tk126_new_detector_control + test_schema_asts_draws_the_tk126_cell (floor 5). Red first: 0/180; after: 9/180, census 242/3000 (was 0/3000). Four-way 150/180 = 83%. Sabotage: body dropped -> 0/180 red; folder declares only r0 -> ASK-1 ValueError red. (2) W4 scope pin: term reclassified MIXED -> SILENT (decided here): its last RAISED probe is ASK-1 generic dangling-reference refusal, identical with a PLAIN target (test_term_undeclared_tupleset_refusal_is_not_term_specific); both term-keyed raises are in TK116 UNREACHABLE. Evidence -> boolean.py::compile_boolean_schema; counts 3/7 -> 2/8; new test_a_loud_or_mixed_row_does_not_cite_dead_refusal_code (red on the old row). CyclicDerivedDependency through a TTU target not counted (computedOrDirect is SILENT on the same reasoning).

Done 2026-10-08, design (a). compile_boolean_schema's I5 subject check and _validate_ttu_tuplesets key on (type, relation) (types read off emitted Filters; name fallback when empty). Variants B/C/D served; pinned 4-way in tests/test_tk126_ttu_target_name_collision.py (red-before-green, sabotages S1-S6, hand-built-AST guard test for R1). Pins moved with provenance: term.NoTtuTarget/mixed-member-types ADMITTED; term row MIXED->SILENT; TK116 witness UNREACHABLE. Hypothesis campaign now draws the TK126 cell (folder-only tupleset body). Lean prose + CORRESPONDENCE sec 7.1 gap recorded; follow-ups TK132 (faithful isPure, LATER), TK133 (term widening, SOMEDAY). PG leg + 6-seed fuzz green 2026-10-08. First-hand: B and D served, alice True / banned bob False. Gated with the 2026-10-08 commit (0.0.3). Workflow reports: docs/history/tk127-fixes-2026-10-08.md.
