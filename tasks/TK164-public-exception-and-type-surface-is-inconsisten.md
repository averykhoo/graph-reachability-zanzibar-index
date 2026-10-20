---
id: TK164
title: public exception and type surface is inconsistent: two refusals not ValueError, ragged re-exports
brief: decide before the 0.1.0 freeze: UnsupportedByGraphIndex not a ValueError; subpackage re-exports ragged
pri: LATER
size: M
deps: []
related: [TK151]
parent:
labels: []
source: docs/tk151-repros-2026-10-20/README.md
source_hash:
created: 2026-10-20b
moved: 2026-10-20b
updated: 2026-10-20b
closed:
---

B2: UnsupportedByGraphIndex and DoublyBridgedShapeError are the only ZanzibarError subclasses with no builtin base, so except ValueError misses them (agent: additive fix, add ValueError). B10: zanzibar.graphindex / zanzibar.setengine re-export arbitrary subsets of the exceptions, and Entity, RelationalTriple, SchemaInfo, CompiledBooleans appear in public signatures without being public. Both are API shape, so they belong before the 0.1.0 freeze or are explicitly accepted.

Repro and first-hand output: `docs/tk151-repros-2026-10-20/README.md` section B2+B10 (`docs/tk151-repros-2026-10-20/B2.py`). Found by the TK151 docs pass 2026-10-20b; the user docs describe the CURRENT behaviour as a caveat, so fixing this means updating the pages that section lists.

## Read first

- `docs/tk151-repros-2026-10-20/README.md`

## Log
