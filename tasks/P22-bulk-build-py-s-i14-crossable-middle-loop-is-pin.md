---
id: P22
title: bulk_build.py's I14 crossable-middle loop is pinned by nothing (green sabotage)
brief: bulk_build.py:206-221 I14 loop: deleting it stays GREEN everywhere -- write a corpus that reaches it or prove it dead
pri: LATER
size: S
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 887290727321
created: 2026-09-06b
moved: 2026-09-06b
updated: 2026-09-06b
closed:
---

Found 2026-09-06b by the `P17` sabotage sweep. `index_v4/bulk_build.py:206-221` is the
I14 crossable-middle loop of the bulk closure builder. Deleting it outright stayed GREEN
across every `build_index` caller: `tests/test_bulk_build.py`, the new
`formal/conformance/test_conformance_bulk_state.py` (bulk vs incremental Python graph
state, exact, over all 25 `GRAPH_FRAGMENT` corpora) and the validation matrix. The
observed output is in that module's docstring under "green sabotages".

Two honest outcomes, pick one with evidence:

1. No corpus reaches a crossable middle under bulk. Write a corpus that does, watch the
   sabotage go RED, keep it as a permanent test (durability ranking in
   `docs/sabotage-procedure.md`).
2. The loop is dead code on every reachable input. Prove it (or show the incremental path
   never materialises what it would) and delete it.

A loop no sabotage can reach is unverified code on the DEFAULT constructor.

## Log

### 2026-09-06b

first reconciliation: filed from the board row this session; body and row say the same thing
