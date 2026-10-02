---
id: TK113
title: WildcardIndex.remove_node on a rewrite source/target (any schema) leaves routed copies stale
brief: NOT boolean-only: pure Computed/union diverge too (probed 2026-10-03b); fence or cascade undecided
pri: NOW
size: M
deps: []
related: []
parent:
labels: []
source: docs/p10-scope-audit-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-10-03b
updated: 2026-10-03b
closed: 2026-10-03b
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

### 2026-10-03b

2026-10-03b: THE OWED PROBE RAN, and it WIDENS the row: the remove_node hole is NOT boolean-specific. PROBED first-hand (.scratch/tk113/probe.py, the P10 vprobe with the schema as a parameter; literal output in docs/tk113-remove-node-fence-2026-10-03.md sec 1). Under viewer: editor (pure Computed) and viewer: [user] or editor (pure union), remove_node(editor, doc, x) leaves alice, bob AND carol as viewers, against oracle, set engine and the sanctioned graph path (3 divergences per arm, at paranoia off/full, with or without a cascade after). check_invariants PASSED every time. Cause (READ): a Computed/TTU arm is a write-time rewrite Rule (zanzibar_utils_v1.py::_rewrite_rule), so RuleSet.apply stores a SECOND edge doc:x#viewer@user:bob; removing the doc:x#editor node leaves that copy behind. The blocked arm diverges only on the boolean schema, because only there does blocked route anywhere. So the fence must cover every rewrite source relation, every rewrite target relation and every TTU-produced subject predicate, on ANY schema; or remove_node must cascade through rewrites. That design call is NOT made yet. NEXT ACTION: census the remove_node callers in tests/ and formal/conformance/ that hit such nodes (a wider refusal may break existing pins), then decide refusal vs cascade.

2026-10-03b CLOSED. DECISION (the model's call): REFUSE, do not cascade. WildcardIndex holds edges, not tuples, so a routed copy cannot be traced back to its raw tuple; a cascade would need the tuple store, which the index layer must not import. LANDED: zanzibar_utils_v1.py::SchemaInfo.unremovable_node_shapes, filled by ::_node_removal_fence on both return paths of ::compile_ruleset. It covers rewrite sources and targets, TTU tupleset subjects and TTU-produced subjects, and derived/leaf families, on ANY schema; a match-any pattern fails loud. The refusal sits in index_v4/wildcard.py::WildcardIndex.remove_node, after the TK80 guard and before _strip_bridges, with REFUSED SHAPE / WHY / INSTEAD comments; INSTEAD is to remove the incident tuples through the write path. A census agent found 1 product caller and 16 test calls through WildcardIndex, plus a 4th unsafe shape (the bare TTU tupleset subject) and a WEDGE failure mode: after a target removal, a later legitimate remove is refused. The compiled shape sets equal the agent's independent derivation on all 4 schemas (READ first-hand). PINNED: tests/test_tk113_remove_node_fence.py (45 tests): exact shape sets on both compile paths, the property "exact or refused" over every node of 4 schemas (A: oracle over non-incident tuples, C: churn without wedge, B: restore), non-vacuity (every user node really removes), and the row witness. Mutation sweep with M0: 12 of 12 red. F9 goes red only on the exact-shape pin, a REASONED redundancy noted in the doc. An INERT RewriteFilter branch was deleted, and the F11 compile path got its own pin. Map (FROZEN): docs/tk113-remove-node-fence-2026-10-03.md; spec-deviations entry 2026-10-03b.
