---
id: TK134
title: parse_openfga_json leaks raw AttributeError/TypeError/KeyError on malformed model shapes
brief: None/list model, type_definitions not a list, a definition without "type": refuse with REFUSED SHAPE
pri: LATER
size: S
deps: []
related: [TK124]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-10-08
moved: 2026-10-08
updated: 2026-10-08
closed:
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
