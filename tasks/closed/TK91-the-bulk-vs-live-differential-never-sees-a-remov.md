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
moved: 2026-09-20f
updated: 2026-09-20f
closed: 2026-09-20f
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

### 2026-09-20f

CLOSED. Map: docs/tk91-tk80-removal-coverage-2026-09-20.md (ACTIVE-PLAN -> freeze with TK80).

WHAT LANDED, and the row's own deliverable is only half of it.

(1) The BULK ARM the row asked for:
formal/conformance/test_conformance_remove.py::test_graph_remove_bulk_build_survivors,
26 params x 5 SEEDS = 130 cells, reusing the module's own _sequence/_extras/_graph_state/grid
so all arms traverse identical op streams. It closes the structural zero the row names --
nothing anywhere bulk-built from a POST-REMOVAL survivor set. Five legs: (a) invariants +
I9 audit_fixpoint on the bulk index, (b) _graph_state equality, (c) per-edge EdgeV4.derived
equality (the I5 stamp snapshot_rows does not carry), (d) grid parity, (e) the constructor pin.
Three anti-vacuity floors set AT the measured minimum, with dated provenance:
_MIN_BULK_STATE_ROWS = 12, _MIN_BULK_DERIVED_STATE = 1, plus the shared grid floor.

(!) THE ARM IS INERT AGAINST THIS ROW'S OWN MUTATION, BY CONSTRUCTION. Do not read it as the
row's pin. Measured twice over: the bulk path never calls processor._live_keys_of (bulk_backfill
has its OWN mirror; instrumented 0 calls on the bulk arm across all 26 corpora, all 170 from the
driven arm), AND on a consistent store the mutation is a semantic no-op (clean vs mutated keyset
dumps byte-identical, same sha, 536 names, diff rc=0). Stronger arms do not rescue it -- adding
the derived flag and a bulk-side audit_fixpoint both stay green. INSTRUMENT CONTROL proving the
arm is not merely vacuous: dropping the derived-computed recursion in the bulk mirror reddens it
loudly -- 26/130 state mismatches, 107 grid, 26 I9 violations.

(2) THE HALF THAT ACTUALLY CLOSES THE ROW, which the row never mentioned:
tests/test_reg_tk91_live_keys_repair.py (5 tests). The leading `rel` in _live_keys_of is a REPAIR
AFFORDANCE reachable only on an INCONSISTENT store -- which is exactly why it measured INERT
across four modules on 2026-09-20d. On a store where derived state outlives its leaf:

  CLEAN                                    MUTATED
    live_keys_of(doc,viewer) = ['d1']        = []
    after backfill(): check = False          check = True   <-- LIVE AUTHORIZATION FAIL-OPEN
    audit_fixpoint() = OK                    audit_fixpoint() = OK  <-- I9 IS BLIND

(!) I9 REPORTS OK UNDER THE MUTATION because it enumerates through the same crippled function.
The pin is therefore asserted off the primitive, never routed through audit_fixpoint (the
2026-09-13e lesson). Deleting `[rel]` now turns the module `4 failed, 1 passed`.

SWEEPS: 3, each with an M0 control that flipped a pin's own claim; all 3 attributed correctly.
tk91-repair-pin PINNED. tk91-bulk-arm GAPS_FOUND -> M14 closed: `if bulk:` -> `if False:` in
connectedstore/build.py left the arm at `26 passed` while bulk_build ran 0 times instead of 130.
build_index now returns a BuildReport (a tuple subclass, so every call site is untouched)
carrying .constructor, assigned inside each branch with no default so a deleted assignment is an
UnboundLocalError; bulk_build_drive refuses a non-'bulk' label. Leg (e) carries its own control
that reddens if the label ever becomes a constant.

NEW FINDING beyond the brief: the arm PINS bulk_build.py Phase P (closed-form path counts),
which test_conformance_bulk_state.py documents as invisible to itself. Two of that module's
"does NOT cover" bullets got dated CORRECTION entries appended in place.

(!) STILL UNPINNED, deliberately -- index_v4/bulk_backfill.py:811 carries an UNPINNED DUPLICATE
of the exact line just pinned. Deleting it leaves all four modules at `29 passed`. Scope was not
widened. The hypothesis that it is unreachable by construction (build_index refuses to run on an
index that already has state) is REASONED and NOBODY HAS PROVED IT. Live trap for the next session.
