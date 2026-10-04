# TK101 -- exhaustive enumeration of object-wildcard WRITES (2026-10-04)

**FROZEN 2026-10-04e, at `TK101`'s close -- provenance, not a living document.** Status lines
below are as-of-then. Corrections are appended dated at the top, never edited into the body.

Row: `python scripts/task.py show TK101`. Provenance labels: **READ** (first-hand read of the
tree), **RUN** (first-hand run, output quoted), **REASONED**.

## 1. The hole, re-read (READ, 2026-10-04e)

`formal/conformance/test_conformance_enum.py::_tuple_space` puts `"*"` only in the SUBJECT
slot (`mk_tuple(rp, rt, "*", rel, ty, on)` with `on` from `_POOL`). None of its six shapes
declares an object-wildcard shape (`SCHEMAS[name][2] == ()` for all six), so even a widened
emitter would have been refused there: `setengine/engine.py` admission (1) raises
`AdmissionRejected` on a `T:*` object outside `schema_info.object_wildcard_shapes`.
The row's first trap holds.

## 2. Decision: option 2, a separate enumeration (REASONED)

Widening `_tuple_space` (option 1) would change six pinned `(space, K, stores)` triples and
multiply the K=4 stratum of a module that is already the biggest conformance runtime. It
would also need object-wildcard declarations on the six shapes. Four of the six are boolean,
and on those the graph refuses any object-wildcard shape (`_reject_object_wildcard_scope`),
which would demote their existing 4-way runs to 3-way. That is exactly the silent
degradation the row's third trap warns about. So the new arm is a separate module,
`formal/conformance/test_conformance_enum_objstar.py`. It enumerates only stores that hold
at least one `*`-object tuple, so its cost is additive. The concrete-object part of each
space is the same `_tuple_space` (imported, so the two cannot drift).

## 3. Probe (RUN, 2026-10-04e, `.scratch/tk101/probe.py`, first 6 star stores of size <=2)

Star space = every Direct restriction of a DECLARED object-wildcard shape, with object `*`
and pool subjects. Queries = `grid.py::grid` over the full space (so `*` targets are asked).

| candidate (base corpus + declared shapes) | graph | conc | star | queries | star stores K2/K3/K4 | s/store | mismatches |
|---|---|---|---|---|---|---|---|
| `ttu` + (folder,viewer),(doc,parent) | admits | 8 | 4 | 252 | 42/206/631 | 0.19 | 0 |
| `wildcard_group_member` + (group,member),(doc,viewer) | admits | 10 | 5 | 216 | 65/400/1555 | 0.30 | 0 |
| `union_computed` + (doc,editor),(doc,viewer) | admits | 8 | 4 | 84 | 42/206/631 | 0.22 | 0 |
| `boolean_exclusion` + (doc,editor),(doc,banned) | REFUSES (expands onto leaf) | 8 | 4 | 153 | 42/206/631 | 0.10 | 0 |

The graph leg in the probe was asked the FULL grid, `*` objects included, and agreed.
That comparison is Python against the agreed answer, NOT theorem-backed: `object_wildcard`
is outside `GRAPH_FRAGMENT` (`corpus.py`, "`BareStarStore` requires stored objects
concrete").

Budget (READ, `.gate-runs/ledger.tsv`, 2026-10-04 run): conf tiles 1-5 took 298/153/114/128/191 s
against the ~600 s cap.

## 4. The module, first full run (RUN, 2026-10-04e)

`formal/conformance/test_conformance_enum_objstar.py`, K=3 on all four shapes. Every store
of size 1..3 with at least one `*`-object tuple. **Zero disagreements on any side, any
store.** The first run had placeholder `grants`/`revokes` pins of 0 and failed only on those.
The measured values, now pinned exactly in `_SHAPES`:

| shape | graph | stores | queries | grants | revokes | call time |
|---|---|---|---|---|---|---|
| `ttu` | 4-way | 206 | 252 | 888 | 0 | 100.07 s |
| `wildcard_group_member` | 4-way | 400 | 216 | 2128 | 0 | 231.63 s |
| `union_computed` | 4-way | 206 | 84 | 556 | 0 | 62.84 s |
| `boolean_exclusion` | 3-way (graph refuses) | 206 | 153 | 596 | 40 | 18.78 s |

`grants` / `revokes` = concrete-object answers (summed over stores) that differ between the
store and the same store with its `*`-object tuples removed, per the oracle. They are the
evidence that the `*` branch RAN and was load-bearing, not just that it passed:

- Every shape has grants > 0, so every shape's `*` writes reached concrete objects.
- `boolean_exclusion`'s 40 revocations are `doc:*#banned` writes overriding concrete
  editor grants. The set engine got all of them right (3-way agreement).

Tile placement (RUN, `pytest formal/conformance --collect-only`, 1085 collected): the four
new nodes are indices 41-44, so conf tiles 2/3/4/5. Every later node shifts by one tile,
so the gate run is the measurement of the new tile loads (sec 6).

(REASONED) The parent module could not see any of this, structurally. None of its shapes
declares an object-wildcard shape, so `setengine/engine.py`'s
`(o_type, rel) in self.schema_info.object_wildcard_shapes` branch is false on every
store it builds.

## 5. Mutation sweep (RUN, 2026-10-04e, `.scratch/tk101/sweep.py`)

Each mutation was a single-occurrence byte anchor (count asserted). It was applied, the whole
module was run, and the file was restored in `finally` (restore asserted, and `git diff` on
`setengine/ index_v4/ tests/` was empty afterwards). "First error" is read from each log,
not inferred.

| id | mutation | verdict | red params | first error (quoted) |
|---|---|---|---|---|
| B | none (baseline) | PASS | -- | `4 passed in 515.95s` |
| M0 | CONTROL: `ttu` pinned stores 206 -> 207 | RED | ttu only | `[ttu] enumerated 206 star stores, pinned 207` |
| M1 | `setengine/engine.py`: concrete-object read ignores the `T:*` tuple (`if (o_type, rel) in ...object_wildcard_shapes:` -> `if False:`) | RED | all 4 | `query=('...', 'user', 'u1', 'editor', 'doc', 'd1') spec=True setengine=False` |
| M2 | `index_v4/wildcard.py`: no `w_all -> concrete` out-bridge | RED | 3 graph shapes | `InvariantViolation: ... I3: concrete ... of bridged-out shape missing its w...` |
| M3 | `index_v4/wildcard.py` `check`: probe 3 (`subj -> w_all`) dropped | RED | 3 graph shapes | `query=('...', 'user', 'u1', 'editor', 'doc', 'd1') spec=True graph=False` |
| M4 | `tests/oracle.py::_matching_objects`: concrete object stops absorbing `T:*` | RED | all 4 | `query=('...', 'user', 'u1', 'banned', 'doc', 'd1') spec=True oracle=False` |
| M5 | test: empty star space | RED | all 4 | `tuple space drifted: conc=8 star=0, pinned conc=8 star=4` |
| M6 | test: star-store filter dropped | RED | all 4 | `[ttu] enumerated 298 star stores, pinned 206` |
| M7 | test: graph leg skipped | RED | 3 graph shapes | `the graph was compared on 0 of 206 stores (graph=True)` |
| M8 | test: set engine not told the declared shapes | RED | all 4 | `AdmissionRejected: object wildcard doc:* (relation 'editor') is not a declared object-wildcard shape` |
| M9 | test: without-star oracle keeps the star tuples | RED | all 4 | `grants=0 revokes=0, pinned grants=888 revokes=0` |
| M10 | test: revocations never counted | RED | boolean_exclusion | `grants=596 revokes=0, pinned grants=596 revokes=40` |
| M11 | test: lift counted on `*`-object queries | RED | all 4 | `[ttu] ... grants=484 revokes=0, pinned grants=888` |

12/12 RED, each on the claim it targeted. Two notes:

- **M2 was caught by the paranoia invariant checker (I3), not by the answer differential.**
  It is still this module's graph leg that drives the write which trips it. M3 is the
  read-path twin, and it reddens the answer claim itself.
- **M7 is the reason the `n_graph` pin exists.** It was added before the sweep, when the
  sweep plan showed that nothing would notice a skipped graph leg. Without it, M7 would
  have been INERT.

## 6. Tile loads after landing (RUN, 2026-10-04e, `.gate-runs/ledger.tsv`)

The four new nodes shifted every later conformance node by one tile. Pytest-reported times
for the gate run on this change, against the earlier 2026-10-04 run (sec 3), which had
different machine load:

| tile | before | after |
|---|---|---|
| conf-tile:1/5 | 298 s | 183.15 s |
| conf-tile:2/5 | 153 s | 123.86 s |
| conf-tile:3/5 | 114 s | 181.81 s |
| conf-tile:4/5 | 128 s | 181.23 s |
| conf-tile:5/5 | 191 s | 277.97 s |

The heaviest tile is 278 s against the ~600 s cap. `wildcard_group_member` (tile 5) is the
one shape to cap at K=2 if a later addition squeezes the budget: its K=2 star stores are 65,
against 400 at K=3 (sec 3).

## 7. What this does NOT cover (REASONED)

- **Removes.** Every store is add-only. Object-star REMOVES on graph-refused schemas are
  driven by `tests/test_tk116_oracle_only_setengine.py`, not here.
- **Closed-but-undeclared shapes.** Only declared shapes are written (module docstring).
- **Lean.** `W4Fragment.bareStar` is unchanged and still MIXED. The graph leg here is
  Python-vs-agreed.
