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
moved: 2026-10-13b
updated: 2026-10-13b
closed: 2026-10-13b
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

### 2026-10-13b

CLOSED 2026-10-13b. All four gaps re-checked FIRST-HAND before writing (probe of 2026-10-13: group a-in-b-in-a, group-in-itself and the folder parent loop are refused with AdmissionRejected by BOTH ConnectedStore and SetEngine; a check with typo relation / typo type / None / int name returns False while the typo write raises; lookup and lookup_reverse decoded via graphindex.Node). LANDED in `PYPI_README.md`: three new "Things to know" bullets (no recursion through and/but not, acyclic tuple data, lenient reads) and a "Reading lookup results" section. The quickstart now resolves lookup node ids and ASSERTS the result, so `tests/test_tk122_release_metadata.py` executes the claim. `graphindex/wildcard.py::LookupResult` got a docstring. Item 1's message is also fixed in code: `boolean.py::_stratify` now names only the SCC members (`_cycle_members`, Tarjan) instead of every relation Kahn could not place, drops the 'boolean spec 1.9' citation, and gives the INSTEAD rewrite plus how it differs. The difference was measured with SetEngine: user blocked only at mid, leaf view is orig False, rewrite True. PINNED: `tests/test_tk135_cycle_message.py`. SABOTAGE: reverting to the Kahn leftovers -> 2 failed, 3 passed.
