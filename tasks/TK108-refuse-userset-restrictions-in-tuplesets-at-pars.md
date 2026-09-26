---
id: TK108
title: refuse userset restrictions in tuplesets at parse too (OpenFGA rule); set engine degrades today
brief: userset restriction in a tupleset: graph refuses, set engine degrades; refuse at parse like TK106? (ask user)
pri: LATER
size: S
deps: []
related: [TK106, ASK-2]
parent:
labels: []
source: hand
source_hash:
created: 2026-09-26b
moved: 2026-09-26b
updated: 2026-09-26b
closed:
---

**Filed 2026-09-26b by TK106 (its design decision D3, `docs/tk106-boolean-tuplesets-2026-09-26.md` § 1).**

A USERSET restriction in a tupleset (`parent: [folder#member]`) has the gap TK106 closed for boolean and computed tuplesets:
- the GRAPH refuses it at compile time (`zanzibar_utils_v1.py::_validate_ttu_tuplesets`, `UnsupportedByGraphIndex`, "tupleset relations must be directly assignable types");
- the SET ENGINE degrades past that refusal (`setengine/engine.py::SetEngine.__init__` catches `UnsupportedByGraphIndex`) and answers.

OpenFGA refuses it too (tupleset relations must be directly assignable types).

It was deliberately NOT folded into TK106, because the user approved only boolean tuplesets. The fix would mirror TK106: make it part of `_validate_tuplesets_direct` and the oracle twin, move the genswarm witnesses `tupleset-userset-restriction` and `tupleset-wildcard-userset-restriction` to `ValueError`, and re-measure the floors.

It changes which schemas are accepted, so ask the user before doing it.

## Log
