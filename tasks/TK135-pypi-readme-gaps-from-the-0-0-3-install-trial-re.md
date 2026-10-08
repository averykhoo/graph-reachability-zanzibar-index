---
id: TK135
title: PyPI README gaps from the 0.0.3 install trial (recursion, acyclic data, silent reads, lookups)
brief: README gaps the 0.0.3 trial hit: boolean recursion refused by graph only, acyclic tuples, silent reads, lookup ids
pri: LATER
size: S
deps: []
related: [TK123, TK127]
parent:
labels: [infra]
source: docs/pypi-trial-0.0.3-2026-10-08.md
source_hash:
created: 2026-10-08b
moved: 2026-10-08b
updated: 2026-10-08b
closed:
---

PyPI-facing documentation gaps the 0.0.3 install trial hit (AGENT, transcribed in
`docs/pypi-trial-0.0.3-2026-10-08.md`). None is a wrong answer; each one cost a stranger time.
`PYPI_README.md` is the long description and its quickstart is executed by
`tests/test_tk122_release_metadata.py`.

1. **Recursion through a boolean relation** (`viewer: ([user] or viewer from parent) but not
   blocked`) is refused by the graph index / `ConnectedStore` with `CyclicDerivedDependency`
   but accepted by `SetEngine` (probe10b). This is the known boundary (boolean spec sec 1.9).
   The README is silent, and the message cites a spec PyPI users cannot see and gives no
   INSTEAD. Its cycle list also names relations that only DEPEND on the cycle.
2. **Tuple data must be acyclic** (group-in-itself, A-in-B-in-A, parent loops are refused
   at write time with `AdmissionRejected ... would create a cycle`), unlike OpenFGA (probe11).
3. **Reads are lenient and silent**: `check` returns False for an unknown relation/type or a
   None/int name, where the same write raises (probe05). Say so.
4. **Lookup results**: `LookupResult` has no docstring; how to map `node_ids` to
   (type, name, predicate), and what `markers`, `excluded_node_ids` and `implicit` mean, is
   undocumented (probe03, probe09).

Ergonomics items (docstrings, `__all__`, error types) belong to `TK123`, not here.

## Log
