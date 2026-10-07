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
moved: 2026-10-07d
updated: 2026-10-07d
closed:
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
