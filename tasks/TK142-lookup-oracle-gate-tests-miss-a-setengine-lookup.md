---
id: TK142
title: lookup-oracle gate_* tests miss a SetEngine.lookup_reverse that drops excluded_node_ids (TK139 gap)
brief: lookup-oracle gates stay green with lookup_reverse exclusions dropped; only scripted pins catch it
pri: NOW
size: M
deps: []
related: [TK139]
parent:
labels: []
source: docs/tk139-lookup-reverse-exclusions-2026-10-13.md
source_hash:
created: 2026-10-13d
moved: 2026-10-13d
updated: 2026-10-13d
closed:
---

Filed by the TK139 review (session 2026-10-13d). The broad lookup-oracle gates in
`tests/test_lookup_oracle.py` do NOT catch a `SetEngine.lookup_reverse` that drops
`excluded_node_ids`, although their S3 check (`_check_set_reverse`) is two-sided on it.

RUN first-hand 2026-10-13d (fix lead): the TK139 fix line
`result.excluded_node_ids = set(m.neg)` in `src/zanzibar/setengine/engine.py::SetEngine.lookup_reverse`
replaced by `pass`, then `pytest tests/test_lookup_oracle.py -k gate`: `9 passed, 38
deselected` (rc 0). Every `test_lookup_oracle_gate_*` stayed green: `_gate_wildcards`,
`_gate_boolean`, `_gate_demorgans_reverse`, `_gate_owc_star_ttu` and the generated-schema
gates. Only the scripted `test_lookup_oracle_dense_boolean`, the tamper test
`test_tamper_set_reverse_is_caught` and the TK139 pins
(`tests/test_tk139_lookup_reverse_exclusions.py`) catch it.

Cause (REASONED, not yet measured): no gate fixture/pool reaches a reverse lookup whose
`expand` has a non-empty `neg`, i.e. a `but not` / `and` under a SUBJECT wildcard
(`[user:*]`) with an interned refused subject. The generated pool rarely builds that shape.

Done when: at least one broad gate (a seeded fixture walk or the generated-schema gate)
goes RED under the same sabotage, with the observed output recorded in its docstring; and
a coverage tripwire (count of reverse lookups with non-empty `neg` seen by the gate,
asserted > 0) so the gate cannot silently lose the shape again.

Map: `docs/tk139-lookup-reverse-exclusions-2026-10-13.md` sec 5 and its dated correction.

## Log

### 2026-10-13d

Why NOW (fix lead decision, 2026-10-13d): closing TK141 left no NOW row, so lint was red. TK142 is a gate that PASSES under a known regression, the house failure mode, and is on the current goal (an honest assurance surface). The only other NEXT row, HS-5, is a doc-liveness tidy. The coordinator or the next session may re-rank with promote --demote.
