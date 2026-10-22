---
id: TK164
title: public exception and type surface is inconsistent: two refusals not ValueError, ragged re-exports
brief: 0.1.0: UnsupportedByGraphIndex gains ValueError; one exception export rule; make SchemaInfo/Entity public
pri: NEXT
size: M
deps: []
related: [TK151]
parent:
labels: []
source: docs/tk151-repros-2026-10-20/README.md
source_hash:
created: 2026-10-20b
moved: 2026-10-23b
updated: 2026-10-23b
closed: 2026-10-23b
---

B2: UnsupportedByGraphIndex and DoublyBridgedShapeError are the only ZanzibarError subclasses with no builtin base, so except ValueError misses them (agent: additive fix, add ValueError). B10: zanzibar.graphindex / zanzibar.setengine re-export arbitrary subsets of the exceptions, and Entity, RelationalTriple, SchemaInfo, CompiledBooleans appear in public signatures without being public. Both are API shape, so they belong before the 0.1.0 freeze or are explicitly accepted.

Repro and first-hand output: `docs/tk151-repros-2026-10-20/README.md` section B2+B10 (`docs/tk151-repros-2026-10-20/B2.py`). Found by the TK151 docs pass 2026-10-20b; the user docs describe the CURRENT behaviour as a caveat, so fixing this means updating the pages that section lists.

## Read first

- `docs/tk151-repros-2026-10-20/README.md`

## Log

### 2026-10-20b

0.1.0 ITEM (user, 2026-10-20b, in chat). Plan (model): (1) UnsupportedByGraphIndex gains ValueError as a base (check tests/parity.py first, it treats a bare compile ValueError as must-surface); (2) one export rule, pinned by a test: subpackages stop re-exporting exceptions, import them from zanzibar (matches the user docs); (3) make Entity, RelationalTriple, SchemaInfo public with docstrings, and fix the CompiledBooleans annotation so typing.get_type_hints(RuleSet) resolves. Coordinate (3) with TK3 (same bare WildcardIndex surface). Update the userdocs pages listed in docs/tk151-repros-2026-10-20/README.md B2 and B10.

### 2026-10-23b

LANDED 2026-10-23b (wf_7da61747-5e0): UnsupportedByGraphIndex (and so DoublyBridgedShapeError) gains ValueError; exceptions are exported ONLY from zanzibar (subpackage __all__ hold none; old names still resolve, not API; breaking entry in CHANGELOG); Entity, RelationalTriple, SchemaInfo, CompiledBooleans public in zanzibar.schema, get_type_hints(RuleSet) resolves; open_set_engine in zanzibar.store.__all__. tests/test_tk164_public_surface.py; orchestrator sabotage first-hand (ValueError base removed): 5 failed. Plan: docs/tk164-public-surface-2026-10-23.md.
