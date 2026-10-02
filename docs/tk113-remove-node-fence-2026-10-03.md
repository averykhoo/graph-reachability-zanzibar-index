# TK113 -- `WildcardIndex.remove_node` fence: the probe and the map (ACTIVE-PLAN, 2026-10-03b)

Row: `python scripts/task.py show TK113`. Witness of record: `docs/p10-scope-audit-2026-09-27.md`
sec 5 H3. Corrections are appended, dated, at the TOP of sec 1.

## 1. The probe that was owed (PROBED first-hand 2026-10-03b)

The row's NEXT ACTION was to check whether a PURE-union `Computed` has the same hole. It does,
so **TK113 is not a boolean-schema bug.** The probe is
`.scratch/tk113/probe.py`, which is the P10 verifier's `vprobe.py` with the schema made a
parameter. It uses three references for `remove_node(P, T, N)`: the oracle over the tuples not
incident to node `T:N#P`, the set engine over the same tuples, and a second graph store that
removed those tuples through the sanctioned path (`RuleSet.apply` + `remove_tuple` +
`run_cascade`). Graph answers are read through a FRESH `WildcardIndex`. Setup tuples:
`group:h#member@user:alice, group:g#member@group:h#member, doc:x#editor@group:g#member,
doc:x#editor@user:bob, doc:x#editor@user:carol, doc:x#blocked@user:carol`.
`doc` declares `blocked: [user]` and `editor: [user, group#member]`, and `viewer` is varied:

```
##### boolean
=== victim=('editor', 'doc', 'x') paranoia=off cascade_after=False
  alice viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
  bob   viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
  check_invariants(schema_info) on committed state: PASSED
  divergences=2
=== victim=('blocked', 'doc', 'x') paranoia=off cascade_after=False
  carol viewer  graph=False oracle=True  setengine=True  sanctioned_graph=True  DIVERGES
  check_invariants(schema_info) on committed state: PASSED
  divergences=1
##### pure-computed
=== victim=('editor', 'doc', 'x') paranoia=off cascade_after=False
  alice viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
  bob   viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
  carol viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
  check_invariants(schema_info) on committed state: PASSED
  divergences=3
=== victim=('blocked', 'doc', 'x') paranoia=off cascade_after=False
  check_invariants(schema_info) on committed state: PASSED
  divergences=0
##### pure-union
=== victim=('editor', 'doc', 'x') paranoia=off cascade_after=False
  alice viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
  bob   viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
  carol viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
  check_invariants(schema_info) on committed state: PASSED
  divergences=3
=== victim=('blocked', 'doc', 'x') paranoia=off cascade_after=False
  check_invariants(schema_info) on committed state: PASSED
  divergences=0
```

The `paranoia=full` and `cascade_after=True` arms gave identical answers in every case
(the full output had 8 arms per schema), and `check_invariants(schema_info)` PASSED on
committed state every time.
Schemas: `boolean` is `viewer: editor but not blocked` (the row's witness), `pure-computed`
is `viewer: editor`, and `pure-union` is `viewer: [user] or editor`.

**Why, by READ (2026-10-03b).** A `Computed` / `TTU` arm compiles to a write-time rewrite
`Rule` (`zanzibar_utils_v1.py::_rewrite_rule`): `RuleSet.apply` turns
`doc:x#editor@user:bob` into a SECOND stored edge `doc:x#viewer@user:bob`. It is not a
graph edge `doc:x#editor -> doc:x#viewer`. So deleting the node `doc:x#editor` deletes
the editor edges, and the viewer copies stay. The `blocked` arm diverges only on the boolean
schema, because only there does `blocked` route anywhere (onto leaf `viewer.1`).

**Consequence for the fence (REASONED).** Every rewrite `Rule` and `RewriteFilter` makes
copies, so a node is unsafe to remove when its `(type, predicate)` is any of:
- (a) the SOURCE relation of a rewrite: its copies live on another node, which survives;
- (b) the TARGET relation of a rewrite: removing it deletes the copies but keeps the
  originals;
- (c) a TTU-produced subject predicate (`target_rel` on a parent type): the rewrite's
  subject node is `folder:f#editor`, which no stored tuple names.

The row's "boolean routing source or leaf family" is a strict subset of this. Whether the
refusal should be that wide, or whether `remove_node` should instead cascade through the
rewrites, is the design call. Neither has been made yet.
