---
id: TK113
title: WildcardIndex.remove_node on a boolean routing source or leaf family leaves derived edges stale
brief: graph != oracle via the admin remove_node API on a boolean schema; invariants blind to it
pri: NEXT
size: M
deps: []
related: []
parent:
labels: []
source: docs/p10-scope-audit-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-10-02b
updated: 2026-10-02b
closed:
---

Filed from the P10 re-run (2026-09-27d). Full witness, provenance and reconciliation: [`docs/p10-scope-audit-2026-09-27.md`](../docs/p10-scope-audit-2026-09-27.md) §5 H3. The section is copied below as it stood when filed; the doc is the body of record.


**Witness** (*verify* `PROBED`, independent `vprobe.py` with three references, 2026-09-27;
schema `group{member:[user, group#member]}`,
`doc{blocked:[user]; editor:[user, group#member]; viewer: editor but not blocked}`; tuples
through `RuleSet.apply` + `run_cascade`:
`group:h#member@user:alice, group:g#member@group:h#member, doc:x#editor@group:g#member,
doc:x#editor@user:bob, doc:x#editor@user:carol, doc:x#blocked@user:carol`):

```
leaf_families: [('doc', 'viewer.0'), ('doc', 'viewer.1')]
routing of bob editor tuple -> ['editor', 'viewer.0']
Victim ('editor','doc','x'), identical at paranoia off/full, cascade_after False/True:
  alice viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
  bob   editor  graph=False oracle=False setengine=False sanctioned_graph=False OK
  bob   viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
  check_invariants(schema_info) on committed state: PASSED
Victim ('blocked','doc','x'):
  carol viewer  graph=False oracle=True  setengine=True  sanctioned_graph=True  DIVERGES
```

`bob editor=False` next to `bob viewer=True` under `viewer = editor but not blocked` means
the graph is inconsistent with itself, whichever reference is chosen (`REASONED`, verify).
The internal leaf names `viewer.0` / `viewer.1` are also admitted as `remove_node` victims:
*audit* `PROBED`, *verify* `READ` only. `connectedstore/` has no `remove_node` caller (`READ`).

**Proposed row** — *"`WildcardIndex.remove_node` on a boolean routing source or a leaf family
leaves derived edges stale; the invariants are blind to it"*, **LATER**, size S-M.
Brief: `index_v4/wildcard.py::WildcardIndex.remove_node` refuses only `*`, derived-public
names (`_assert_derived_exclusivity`) and residue-recorded nodes (`_residue_records_node`,
TK80). It runs no cascade. `RuleSet.apply` fans a routing-source tuple onto the public node
AND a separate leaf node, so removing the public node leaves the leaf copy, and the derived
answer goes wrong at every paranoia tier (witness above). Fix with mechanical refusals, no
algorithm change: (1) a leaf-family fence mirroring `WildcardIndex.check`'s; (2) on a boolean
schema, refuse a node whose (type, predicate) routes into a leaf family, and name the
sanctioned route (remove the incident tuples through `RuleSet.apply` + `run_cascade`). Both
get REFUSED SHAPE / WHY / INSTEAD blocks. Pin the editor and blocked arms, plus a subject-only
control that still removes cleanly, and run a sweep with an M0 control. The exposure is the
public admin API only.

## Log

### 2026-10-02b

2026-10-02b scouting (no code yet), detail in docs/tk111-stall-aware-freshness-2026-10-02.md sec 4: the witness routing source doc#editor fans to viewer.0 via a compiled Rule (Computed arm, zanzibar_utils_v1.py::_emit_leaf_expr), NOT a RewriteFilter, so a fence keyed only on RewriteFilter sources would miss the witness. The fence set must be every compiled Rule/RewriteFilter source whose target is in schema_info.leaf_families. UNVERIFIED and to probe FIRST: whether a pure-union Computed (viewer: editor, no boolean) has the same remove_node hole, which would widen the row beyond boolean schemas. NEXT ACTION: that probe.
