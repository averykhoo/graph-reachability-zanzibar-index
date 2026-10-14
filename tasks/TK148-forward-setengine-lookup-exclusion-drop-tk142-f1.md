---
id: TK148
title: Forward SetEngine.lookup exclusion drop (TK142 F1) is caught only by scripted pins
brief: no broad gate reaches a forward lookup with excluded_node_ids; _Gate.set_forward_excl counts it, asserts nothing
pri: LATER
size: S
deps: []
related: [TK142, TK146]
parent:
labels: []
source: docs/tk142-lookup-oracle-exclusion-gap-2026-10-14.md
source_hash:
created: 2026-10-14
moved: 2026-10-14
updated: 2026-10-14
closed:
---

Residual of TK142 (challenge C4, `docs/tk142-lookup-oracle-exclusion-gap-2026-10-14.md`), not closed by the TK142 build (worktree-wf_9a094007-20b-11 @69080d4, tests only).

The FORWARD lookup exclusion channel has the same class of gap TK142 closed for `lookup_reverse`. Mutant F1 (challenge PROBE, 2026-10-14): `SetEngine.lookup` (forward, TK116) with `excluded_node_ids` cleared, run over `test_lookup_oracle.py`, `test_lookup_hypothesis.py`, `test_tk116_oracle_only_setengine.py` and `test_reads.py`: `6 failed, 126 passed`. RED only in SCRIPTED pins: TK116's witnesses `[owc-on-derived]` / `[owc-expands-onto-leaf]`, `test_lookup_marker_carries_its_exclusions[py/roaring]`, `test_set_forward_checker_sees_a_tampered_exclusion[clear/spurious]`. GREEN in every broad gate, including the TK116 generated walk and the stateful machine: forward lookups with a non-empty `excluded_node_ids` count 0 there.

REASONED cause: the shape needs an object wildcard under `and` / `but not`, which the graph refuses, and every generated gate passes `object_wc=frozenset()`, so none can reach it structurally.

What the TK142 build already did: `_Gate.set_forward_excl` is COUNTED (no assertion), so the instrument exists.

Candidate (UNVERIFIED whether it reaches the shape): a seeded set-only walk, `_run_gate(w.schema, w.owc, _witness_pool(w), seed, 8, allow_graph_absent=True)` over `tests/test_tk116_oracle_only_setengine.py::WITNESSES` families `owc-on-derived` / `owc-expands-onto-leaf`, with a tripwire asserting summed `set_forward_excl > 0`.

Done when: a broad seeded walk goes RED under F1 (observed output in its docstring), with a `set_forward_excl > 0` tripwire that is itself sabotaged red. Positive pins only, never an xfail.

## Traps

- Measure under the mutant with hypothesis `database=None` (TK146): a replayed stored failure fakes a catch.

## Read first

- `docs/tk142-lookup-oracle-exclusion-gap-2026-10-14.md` (Corrections, C4).
- `tests/test_tk116_oracle_only_setengine.py` (WITNESSES, _witness_pool, the generated set-only walk).
- `tests/test_lookup_oracle.py` (_Gate, _run_gate).

## Log
