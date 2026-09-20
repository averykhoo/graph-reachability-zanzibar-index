---
id: TK91
title: the bulk-vs-live differential never sees a removal; one op in one history is the whole pin
brief: MEASURED 2026-09-20d: dropping `rel` from _live_keys_of preds is INERT tree-wide -- removals are the hole
pri: NOW
size: M
deps: []
related: [TK78, TK87]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-20
moved: 2026-09-20e
updated: 2026-09-20e
closed:
---

The bulk bootstrap builds from the SURVIVING TUPLES of a snapshot; the live path replays a
HISTORY. A removal is therefore exactly where the two constructions can legitimately diverge
— stale residue, refcounts, GC'd nodes — and it is the arm with almost nothing behind it.

`READ 2026-09-20`. The live-vs-offline differentials and what they drive:

| pin | removal coverage |
|---|---|
| `formal/conformance/test_conformance_bulk_state.py::test_state_bulkbuild_vs_pythongraph` | **none** — its own docstring: *"Every `GRAPH_FRAGMENT` corpus is an add-only tuple list … the snapshot the bulk side builds from is the whole list"* |
| `tests/test_invariants_derived.py::test_backfill_vs_live_equivalence` (`:220`) | **none** — `_OPS` is add-only |
| `tests/test_connectedstore_build.py::test_built_index_equals_live_maintained` (`:70`) | **one** `('remove', ...)` op, `:41` |

So the whole bootstrap≡replay-under-removal story rests on a single removal of a single
tuple in a single fixed history. The conformance module names this gap itself, first in its
"what this does NOT cover, said plainly" list, and points at that one test.

**Why now.** `TK87` closed on precisely this shape four days ago: `tests/genswarm.py` was
add-only, so no driven config of any shape could reach `index_v4/wildcard.py::_sync_entity_middles`,
whose every caller is a removal path — a structural zero that had read as coverage. The
same argument applies here one level up: an add-only differential cannot see a
construction-order divergence that only a removal can create.

**Shape (a DECISION for the taking session, not a plan to inherit).** The cheap version is
to widen `test_built_index_equals_live_maintained`'s `_OPS` beyond its one remove and add a
boolean schema; the honest version is a removal arm in the conformance differential, which
is where the 25 corpora and the Lean anchoring are. Note what makes this non-trivial:
`graphindex_drive` replays a tuple LIST, so a removal arm needs the corpus format to carry
ops, not tuples. Check whether `formal/conformance/test_conformance_remove.py` already has
the machinery before building any.

⚠ Do NOT fold this into [[TK78]]. That row's measured conclusion is that the ENUMERATOR
(`::_live_keys_of` vs `::_fan_out`, asserted nowhere) is the item, and this is a separate,
thinner-but-real gap that would otherwise ride along unranked.

## Read first

- [`docs/tk78-offline-bootstrap-audit-2026-09-20.md`](../docs/tk78-offline-bootstrap-audit-2026-09-20.md)
  §5a — the four declared gaps and the verdict on each, and §6 for why this was split out.
- `formal/conformance/test_conformance_bulk_state.py` — the "does NOT cover" list is the
  source; read it before widening anything.

## Log

### 2026-09-20d

MEASURED EVIDENCE, from `TK78`'s sabotage sweep -- this row no longer rests on an analogy
with `TK87`, it has a named unpinned branch.

`index_v4/processor.py::_live_keys_of` builds `preds = [rel] + <positive closure /
derived-userset predicates>`. The leading `rel` -- the object's own PUBLIC family -- is the
only entry that can enumerate an object whose derived state OUTLIVES the leaf that produced
it, which is exactly a removal: drop the `parent` tuple and `('doc', 'access', d)` is no
longer reachable through any storage family or recursion, but its public node still exists
and still holds a stale derived edge for backfill to clean up.

`READ 2026-09-20d`: deleting `rel` from that list left ALL FOUR of
`tests/test_backfill_enumeration.py`, `tests/test_bulk_build.py`,
`tests/test_invariants_derived.py` and
`formal/conformance/test_conformance_bulk_state.py` GREEN. Every corpus they drive is
add-only (the new module deliberately so -- bulk builds from SURVIVORS, live replays a
HISTORY, and that is the divergence this row is about), so the branch cannot move. Per
`docs/sabotage-procedure.md` that is reported INERT, not as a clean pin: the mutation is
plausible and narrow, and nothing in the tree can see it.

So the concrete first ask for whoever takes this row is smaller than the row's framing: a
remove history that reddens that one deletion. The other three kind-drops in the same sweep
were each caught somewhere; this one was not caught anywhere.

### 2026-09-20e

THIS ROW'S STATED BLOCKER IS REFUTED. Read this before sizing the item -- the 2026-09-20d
entry says the honest version is non-trivial because "graphindex_drive replays a tuple LIST,
so a removal arm needs the corpus format to carry ops, not tuples". That is no longer true,
and the row told the next session to check exactly this.

`READ 2026-09-20e`, first-hand:

* `formal/conformance/backends.py:283::graphindex_drive_ops` already drives an interleaved
  `('add'|'remove', tup)` stream through the real graph index, with poison semantics mirrored
  from the set-engine driver -- AND it RETURNS the surviving accepted set (`present`), which
  is precisely the snapshot input a bulk build needs. The machinery the row asks whether to
  build exists.
* `formal/conformance/test_conformance_remove.py:428::test_graph_remove_sequences` already
  compares the removal-driven state against a FRESH rebuild over that survivor set, at full
  state level (nodes, edges, `EdgeV4.derived` flags, residues -- via `::_graph_state`) plus
  the grid plus the oracle, over seeded sequences with an anti-vacuity floor.

So "removals converge to a rebuild" is WELL pinned -- for the INCREMENTAL rebuild. The fresh
arm at `:453` is `graphindex_drive_ops(schema_text, [('add', t) for t in final_tuples], ...)`,
i.e. write-by-write through `GraphDriver`. The bulk constructor is never the comparand.

THE HOLE, restated one arm wide: nothing anywhere bulk-builds from a POST-REMOVAL survivor
set. `tests/test_bulk_build.py` contains ZERO remove ops (grepped 2026-09-20e -- no
`'remove'`, no `remove_tuple`); `formal/conformance/test_conformance_bulk_state.py` names the
gap itself in its "does NOT cover" list; the only coverage is
`tests/test_connectedstore_build.py:41`, one history with one remove.

SO THE CHEAPER SHAPE IS THE HONEST ONE, which inverts this row's own menu: add a BULK arm to
the EXISTING `test_graph_remove_sequences` -- reusing its ops corpora, seeds, `_graph_state`
and grid -- rather than building a removal arm into the bulk-state module. That also gives
the row's measured-INERT branch (`processor.py::_live_keys_of`'s leading `rel`) a corpus that
can finally move it, which is why this row is `NOW`.

UNVERIFIED: whether `test_built_index_equals_live_maintained`'s `_SCHEMA` is boolean (it has
`blocked`/`public`, which suggests an exclusion) -- not checked, and it does not change the
conclusion above.
