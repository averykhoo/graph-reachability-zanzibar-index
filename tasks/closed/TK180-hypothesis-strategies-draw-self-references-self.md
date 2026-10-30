---
id: TK180
title: hypothesis strategies: draw self-references (self-parent tuples, a from back to its own type) often
brief: hypothesis rarely draws self-parent tuples; TK175 surfaced on a lucky draw: bias the strategies
pri: NEXT
size: S
deps: []
related: [TK175, TK178]
parent:
labels: []
source: hand
source_hash:
created: 2026-10-30b
moved: 2026-10-30b
updated: 2026-10-30b
closed: 2026-10-30b
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-10-30b

Why: TK175 (docs/tk175-self-parent-node-recreate-2026-10-30.md) was latent through 0.1.0; test_add_then_remove_restores_row_multiset hit it on one rare draw, and the 6-seed fuzz.yml plus seeds 1-6 do not. Next action: in the shared candidate pool / tuple strategies (tests/test_hypothesis.py, tests/test_wildcard_property.py) make tuples with subject == object and tupleset relations whose restriction includes their own type common; then show the new strategy finds TK175 with the core.py guard removed (sabotage) within the ci profile.

Map: docs/tk180-tk181-stranger-tests-2026-10-30.md. tests/test_hypothesis.py draws self-references often: pool_ops biases tuples toward subject==object; _schema_ast self_ref_motif (1 in 3 in schema_asts) builds boolean-around-from over a self-typed tupleset. New test_self_reference_add_then_remove_restores_row_multiset finds TK175 with the core.py guard removed on agent seeds 1-6 and session first-hand seeds 4 and 7 (1 failed, 33 deselected; green with guard); floor test _TK175_SHAPE_FLOOR=6 (13/180 drawn, 0/180 before; sabotage red). Runtime unchanged. Trap: hypothesis shrinks toward the low end / False, so weights are ch.one(preferred first).
