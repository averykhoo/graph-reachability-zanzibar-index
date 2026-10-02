# TK113 -- `WildcardIndex.remove_node` fence: the probe and the map (2026-10-03b)

**FROZEN 2026-10-03b, at `TK113`'s close -- provenance, not a living document.** Status lines
below are as-of-then and may now be false; live state: `HANDOFF.md` + the session
ledger (`python scripts/task.py board`). Corrections are appended dated at the top, never
edited into the body.

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

## 2. Census of `remove_node` callers and shapes (agent-PROBED/READ 2026-10-03b; the orchestrator re-derived the shape sets first-hand)

A read-only census agent wrote `.scratch/tk113/census.md` (gitignored). What matters from it:
- **Callers (READ).** Product code has exactly one caller:
  `index_v4/wildcard.py::WildcardIndex.remove_node`, which calls
  `index_v4/core.py::ReachabilityIndex.remove_node`. There are no callers in `connectedstore/`,
  `setengine/`, `benchmarks/`, `formal/conformance/`, `tests/parity.py` or
  `tests/test_matrix.py`. Tests make 21 calls in 8 files. 5 go to the core directly (outside
  the fence), and 16 go through `WildcardIndex`. Neither the set engine nor the oracle has a
  `remove_node`.
- **A fourth unsafe shape (PROBED):** the bare TTU tupleset SUBJECT. Removing `folder:f#...`
  deletes `doc:d#parent@folder:f`, but the copy `folder:f#editor -> doc:d#editor` stays
  (`user:u editor doc:d`: graph=True, oracle=False).
- **A second failure mode, the WEDGE (PROBED).** After removing a rewrite target or a leaf, a
  sanctioned remove of an ordinary, NON-incident tuple is refused (`AdmissionRejected:
  Non-existent edge cannot be removed`), while the set engine accepts it. For
  `doc:x#viewer.0` this is the only symptom, so a check-answer comparison alone misses it.
- **Prediction vs probe (PROBED).** Every one of 37 nodes on four schemas was removed and
  checked three ways (A/C/B, as in sec 3). The shape prediction disagreed with the outcome 0
  times.
- **Blast radius of a refusal (PROBED).** A monkeypatched fence running over the 8
  `remove_node` modules gave `1 failed, 100 passed`. The one red was an ordering clash with
  the TK80 owner test, fixed by placing the fence after the TK80 guard.

## 3. Decision and what LANDED (2026-10-03b)

**Decision: REFUSE, do not cascade (REASONED, the model's call).** `WildcardIndex` holds
edges, not tuples. Once a write has been routed, its copies cannot be traced back to the raw
tuple that produced them, so a cascading `remove_node` would need the tuple store, which the
index layer must not import (`connectedstore` composes them, never the reverse). A refusal
is mechanical and closes the divergence on every schema. The sanctioned route, removing the
incident tuples through the write path, already exists and is named in the error.

LANDED:
- `zanzibar_utils_v1.py::SchemaInfo.unremovable_node_shapes`, filled by
  `::_node_removal_fence` on BOTH return paths of `::compile_ruleset`. It covers rewrite
  sources, rewrite targets, TTU tupleset subjects, TTU-produced subjects, and the
  derived/leaf families; a match-any pattern fails loud.
- The refusal in `index_v4/wildcard.py::WildcardIndex.remove_node`, placed after the TK80
  guard and before `_strip_bridges`. The compiled sets equal the census agent's
  independently derived ones on all four schemas (READ first-hand).
- Pins in `tests/test_tk113_remove_node_fence.py`: the exact shape sets on both compile
  paths, and "exact or refused" as a property over every node of the four schemas. Exact
  means three checks: (A) the answers match the oracle over the non-incident tuples; (C) a
  churn of every remaining tuple through the write path succeeds and still matches; (B)
  re-adding the incident tuples restores the full oracle. Also: a non-vacuity control (every
  user node really is removed) and the row witness.

**Mutation sweep (PROBED first-hand 2026-10-03b; runner `.scratch/tk113-sweep/sweep.py`,
gitignored, so this table IS the record)** over `tests/test_tk113_remove_node_fence.py`,
`tests/test_reg_tk80_remove_node_residue.py`, `tests/test_wildcard_remove_node.py` and
`tests/test_admission_rejected.py`. Literal lines, truncated:

```
BASELINE rc=0 | 80 passed in 10.68s
M0 control: drop a pinned shape: rc=1 red | 3 failed, 77 passed in 10.71s | ['test_fence_is_filled_on_the_non_boolean_compile_path_too[pure-computed]', 'test_fence_shapes_are_exactly_the_rewrite_strad
F1 no fence in remove_node: rc=1 red | 14 failed, 66 passed in 10.69s | ['test_fence_refuses_the_row_witness_on_a_pure_schema', 'test_remove_node_is_exact_or_refused[boolean-doc:x#blocked]', 'test_rem
F2 fence over-broad (refuse all): rc=1 red | 26 failed, 54 passed in 6.48s | ['test_a_dangling_residue_ref_does_not_count_as_a_recording', 'test_an_unreferenced_node_is_still_removable_and_commits_cle
F3 rules ignored (leaf/derived only, the row original plan): rc=1 red | 19 failed, 61 passed in 10.64s | ['test_fence_is_filled_on_the_non_boolean_compile_path_too[pure-computed]', 'test_fence_is_fill
F4 rule SOURCE not fenced: rc=1 red | 13 failed, 67 passed in 10.53s | ['test_fence_is_filled_on_the_non_boolean_compile_path_too[pure-computed]', 'test_fence_is_filled_on_the_non_boolean_compile_path
F5 rule TARGET not fenced: rc=1 red | 9 failed, 71 passed in 10.84s | ['test_fence_is_filled_on_the_non_boolean_compile_path_too[pure-computed]', 'test_fence_is_filled_on_the_non_boolean_compile_path_
F6 TTU branch dropped: rc=1 red | 4 failed, 76 passed in 10.20s | ['test_fence_is_filled_on_the_non_boolean_compile_path_too[ttu]', 'test_fence_shapes_are_exactly_the_rewrite_straddled_shapes[ttu]', '
F7 TTU tupleset subject not fenced: rc=1 red | 3 failed, 77 passed in 10.45s | ['test_fence_is_filled_on_the_non_boolean_compile_path_too[ttu]', 'test_fence_shapes_are_exactly_the_rewrite_straddled_sh
F8 TTU-produced subject not fenced: rc=1 red | 3 failed, 77 passed in 10.70s | ['test_fence_is_filled_on_the_non_boolean_compile_path_too[ttu]', 'test_fence_shapes_are_exactly_the_rewrite_straddled_sh
F9 derived/leaf families not added: rc=1 red | 1 failed, 79 passed in 9.77s | ['test_fence_shapes_are_exactly_the_rewrite_straddled_shapes[boolean]']
F10 fence placed BEFORE the TK80 guard: rc=1 red | 2 failed, 78 passed in 10.34s | ['test_removing_the_node_that_owns_a_residue_row_is_refused', 'test_fence_refuses_the_row_witness_on_a_pure_schema']
F11 pure compile path never fills the fence: rc=1 red | 3 failed, 77 passed in 10.43s | ['test_fence_is_filled_on_the_non_boolean_compile_path_too[pure-computed]', 'test_fence_is_filled_on_the_non_boo
DONE
```

Every mutant went red, and the M0 control was attributed to the pin it edited. F9 (no
derived/leaf families) goes red ONLY on the exact-shape pin. On these schemas every leaf is
also a rule target, so the behavioural property cannot see it (REASONED). The family union
is kept as defence in depth, and the shape pin is what holds it. Before the sweep, an INERT
branch was found by reading and deleted: the `RewriteFilter` arm, redundant because a
`RewriteFilter` only routes a derived-public relation onto a leaf. F11 (the non-boolean
compile path) was INERT until
`::test_fence_is_filled_on_the_non_boolean_compile_path_too` was added.
