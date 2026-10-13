---
id: TK134
title: parse_openfga_json leaks raw AttributeError/TypeError/KeyError on malformed model shapes
brief: None/list model, type_definitions not a list, a definition without "type": refuse with REFUSED SHAPE
pri: NOW
size: S
deps: []
related: [TK124]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-10-08
moved: 2026-10-13b
updated: 2026-10-13b
closed: 2026-10-13b
---

## Log -- empty

Found 2026-10-08 by the TK127 adversarial review (AGENT, pre-existing at 7296eb1, not a TK124
regression). `zanzibar.schema.parse_openfga_json` leaks raw `AttributeError` / `TypeError` /
`KeyError` on malformed model SHAPES: a `None` or list model, `type_definitions='user'`, and
`type_definitions=[{}]` (a definition with no `type` key). Refuse each with a `ValueError` and a
`# REFUSED SHAPE` / `# WHY` / `# INSTEAD` block in a `_validate_*` function in
`src/zanzibar/schema/json_frontend.py`, next to `_validate_json_declares_a_type`.

## Traps

- (!) Re-run the four repros first-hand before fixing; this row is from an agent report.

## Read first

- `src/zanzibar/schema/json_frontend.py::_validate_json_declares_a_type` (the TK124 guard on the same lines).

## Log

### 2026-10-12c

PROMOTED LATER -> NOW 2026-10-12c at write-back, because closing TK44 left NOW empty and task lint requires exactly one. Why TK134 (model decision, CLAUDE.md Who decides): it is the only small open row with a known user-visible defect (malformed OpenFGA JSON leaks raw AttributeError/TypeError/KeyError instead of a REFUSED SHAPE refusal), it fits the current goal (the refusal surface says WHY), and it is size S. TK97 and TK135 stay LATER per the 2026-10-12b re-rank. No release is implied: the user said no rush to 0.0.4. The user may re-rank.

### 2026-10-13b

CLOSED 2026-10-13b (user: get 0.0.4 release ready). The four repros were re-run FIRST-HAND before the fix, and the class turned out to be wider: a 30-shape probe found 23 leaking bare AttributeError/TypeError/KeyError. LANDED: three shape helpers in `src/zanzibar/schema/json_frontend.py`, `_validate_json_object` / `_validate_json_array` (both `optional=` read null as absent) and `_validate_json_field` (required string). Each has a REFUSED SHAPE / WHY / INSTEAD block, and every read of the model goes through them. Behaviour change, recorded in CHANGELOG 0.0.4: a non-object `metadata` such as `[]` was silently ignored and is now refused; `"metadata": null` (what OpenFGA's API emits) still reads as absent. PINNED: `tests/test_tk134_json_malformed_shapes.py`, 26 malformed shapes plus 4 controls. SABOTAGE (literal, recorded in its docstring): reverting the computedUserset arm to `body['relation']` -> 2 failed, 28 passed. `tests/test_refused_shape_comments.py` floors re-measured and ratcheted 41->44 headers, 29->33 in-scope raises.
