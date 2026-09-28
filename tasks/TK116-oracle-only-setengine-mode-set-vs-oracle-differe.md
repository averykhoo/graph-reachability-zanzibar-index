---
id: TK116
title: oracle-only SetEngine mode: set-vs-oracle differential with removes for every decision-15 family
brief: coverage: decision-15 families are differential-tested set-vs-oracle without removes
pri: LATER
size: M
deps: []
related: []
parent:
labels: []
source: docs/p10-scope-audit-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-09-27d
updated: 2026-09-27d
closed:
---

Filed from the P10 re-run (2026-09-27d). Full witness, provenance and reconciliation: [`docs/p10-scope-audit-2026-09-27.md`](../docs/p10-scope-audit-2026-09-27.md) §5 H6. The section is copied below as it stood when filed; the doc is the body of record.


**Witness** (*verify* `PROBED`, `v_probe.py`, 2026-09-28):

```
W1 owc (doc,editor), view: editor but not banned
   graph compile: REFUSED UnsupportedByGraphIndex: object-wildcard shape (doc, view) expands onto the compiled leaf predicate (doc, view.0)
   graph joined: False | _ruleset None: [True, True]
   add ('...','user','u1','editor','doc','*') -> accepted=True ; remove ... -> accepted=True
   W1 seed 0: 3-way parity OK, accepted {'add': 27, 'remove': 18}
W2 reader: [group:*#ok, group#member]  (ok = member but not blocked)
   REFUSED UnsupportedByGraphIndex: ... wildcard userset restriction [group:*#ok] over the derived relation group#ok
   add ('member','group','g2','member','group','g1') -> accepted=True   (closes a data cycle)
W2C control (reader: [group#member]): graph joined: True, close cycle accepted = False
v_bsb_decomp: ANY applicable family ...: {'star-tupleset-over-derived': 768, 'owc-tupleset-of-derived-ttu': 384, 'owc-on-derived': 384}
```

No divergence was found. The gap is that the owc-feeding-leaf family, D4 (owc upstream of a
derived TTU target), wildcard-userset-over-derived, and cyclic-derived-with-removes are never
driven set-vs-oracle. Only `pytest.raises` pins cover them
(`tests/test_boolean_compile.py::test_object_wildcard_expanding_onto_leaf_rejected`,
`::test_object_wildcard_upstream_of_derived_ttu_target_rejected`), and every other driver
skips refused schemas (`tests/test_generator_coverage.py::_sweep`,
`tests/test_lookup_oracle.py::test_lookup_oracle_gate_generated_schemas`,
`tests/test_zt_p5_readjudication.py`). `connectedstore/schema_io.py::save_schema` refuses all
of them, so only standalone `SetEngine` users are exposed.

**Proposed row** — *"Oracle-only SetEngine mode: set-vs-oracle differential with removes for
every decision-15 family"*, **LATER**, size S-M.
Brief: on a graph-refused schema, `setengine/engine.py::SetEngine.__init__` sets
`_ruleset = None`. That makes `::_would_cycle` return False, so data-cycle rejection is off,
and the only cross-check is the oracle. Add a deterministic parametrized test over
`tests/genswarm.py::REJECTION_WITNESSES` plus the `tests/test_boolean_compile.py` refusal
witnesses. For each: build a `ParityEngine`, assert the graph is absent and `_ruleset is None`,
run a seeded add/remove walk that includes star-object and cycle-closing writes, and floor the
accepted removes above zero. Run the lookup-oracle gate on refused schemas instead of skipping
them. Decide and record the admission asymmetry (the same `group#member` accepts a cycle only
when an unrelated relation makes the schema graph-refused). Fix the stale "Boolean schemas
have no graph partner" comment in `_would_cycle`. Delete or assert-out the dead `continue` in
`tests/test_hypothesis.py::test_every_tupleset_kind_is_driven_against_the_oracle`: *audit*
measured 0 of 10 cells refused (2026-09-27). If H1 lands first, its negative cycles leave this
row's cyclic-derived witness set.

## Log
