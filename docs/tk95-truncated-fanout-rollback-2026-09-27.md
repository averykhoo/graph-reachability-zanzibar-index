# `TK95`: a refused fan-out leaves no trace, in any order

**FROZEN 2026-09-27, at `TK95`'s close. This is provenance, not a living document.** Status
lines below are as of that date; for live state see `HANDOFF.md` and the session ledger.
Corrections are appended at the top with a date, never edited into the body. Figures were
measured on `2026-09-27` against HEAD `2f46adb`.

Provenance labels: **READ** (first-hand, this session), **REASONED**, **MEASURED** (a run
whose output is quoted), **UNVERIFIED**. No subagents were used.

The deliverable is `tests/test_tk95_truncated_fanout_rollback.py`. Its docstring carries
the mutation-sweep table. This file carries the scouting that chose the fixture, plus what
the pin does not reach.

## § 0 Summary

`RuleSet.apply` yields a raw tuple's fan-out out of a `set`, so when a later leaf is refused,
which leaves were already written depends on the hash seed. The new module drives each
refused fan-out in **all `n!` orders**. For each one it asserts four things:

* the graph store is byte-identical to its pre-write state, row ids and `sqlite_sequence`
  included;
* a follow-up of accepted writes and one removal then produces a store byte-identical to a
  control store that never saw the refused write;
* the check grid agrees with the oracle and with both set engines;
* in the production arm (`advance_index`), the per-batch N15 node cache is gone after the
  failure.

The module has 5 tests: 2 cases in the graph arm, 3 in the production arm. It is green at
`PYTHONHASHSEED` 0, 1 and 7. A 10-mutation sweep with an `M0` control named every expected
red. The one INERT row (M4) is explained in § 3.

## § 1 MEASURED 2026-09-27: the corpus's own aborts, captured

The instrument was a throwaway pytest plugin, `.scratch/tk95/tk95cap.py`, deleted at close.
It wraps `WildcardIndex.add_tuple`/`remove_tuple` and records the triggering `Diff.add`'s
schema, store, raw tuple, fan-out and exception for every refused leaf. It ran over
`tests/test_generator_coverage.py` at `PYTHONHASHSEED=0`.

```
full module (33 passed):                 22 refused leaves (messages below are from the -k run)
-k regime_finds (2 passed, 31 deselected): 22 refused leaves, 8 distinct schemas
(exception, position, fan-out size, op):  ('AdmissionRejected', 3, 3, 'add') x 22
messages:  self-referential edge would create a cycle     12
           <id> is reachable from <id> ... cycle            6
           wildcard tuple ... forms a cycle                  4   (doc:* parent)
```

The smallest witness, the source of the `self-loop` case (store empty, schema verbatim):

```
type doc
  relations
    define r0: [user]
    define parent: [doc]
    define r1: [user]
    define r2: r1 from parent or r2 from parent
write doc:d1#parent@doc:d1  ->  fan-out [parent edge, d1#r1->d1#r2, d1#r2->d1#r2]
                                refused: the third, a self-referential edge
```

The `two-cycle` case is the store-size-1 family from the same capture: a parent write that
closes a cycle against a stored parent. The test drops the unused `r0`.

**Reconciling with `TK93` (not re-bisected):** `docs/tk93-ensure-raw-seed-dependence-2026-09-21.md`
§ 4.2 measured 21 aborts, some at position 2 at seed 0. This capture has 22, all at
position 3. The corpus has changed since then (the module now collects 33 tests where it
collected 31; `TK106` and `TK108` changed which schemas parse). That is the likely cause,
but it is UNVERIFIED. Nothing here depends on it: the test forces every order itself.

## § 2 The fixture choices (REASONED, then MEASURED green)

* **All `n!` orders, not natural plus reversed.** With `n = 3` that is 6 runs per case.
  Across them the refused leaf lands at every position, so the anti-vacuity clause asserts
  that both the empty prefix and the whole prefix occur. Two orders could miss one of them.
* **A byte-identical dump, not `invariants.py::snapshot_rows`.** `snapshot_rows` is
  id-independent and reads only `node_v4` and `edge_v4`. It cannot see an outbox or residue
  row left behind, or a consumed id. The dump reads every table plus `sqlite_sequence`. It
  drops only `created_at`, a wall clock that differs between any two stores (the first run
  went red on `store_v4.created_at` alone, which is an instrument fault, not a finding).
* **A control-store comparison after follow-ups.** A DB rollback cannot reach Python-side
  state. The only way to see a stale cache or buffer is to keep writing and compare against
  a store that never saw the refusal.
* **The prefix must really write something.** When the refused leaf is at position > 1, the
  store as it stood on entry to that leaf must differ from the pre-write store. Otherwise a
  no-op prefix passes for free. Sweep row M9 shows this clause can go red.
* **`cap-fanout`, production arm only.** The generator corpus reaches only cycle refusals,
  and in production those are refused at admission, so `_apply_row` sees them only as
  corruption. The closure fan-out cap is the refusal an ADMITTED row can hit mid-fan-out:
  `_apply_row` lets `ClosureFanoutExceeded` escape and the cursor stays put. The case sets
  `widx.idx.max_closure_fanout = 3` after the stored rows land. It then writes
  `doc:d1#parent@doc:d2`, whose leaf `d1#r1 -> d2#r2` has 5 ancestors, `d1#r2 -> d2#r2`
  has 3, and the bare parent edge 0, so exactly one leaf is refused in every order
  (MEASURED: the anti-vacuity clause passes). It has no graph-arm twin: the set engine has
  no cap, so `Diff` would report the refusal as an admission divergence.

## § 3 What the pin does NOT reach

* **The outbox-buffer leak guard.** That guard is the `finally` in
  `core.py::_add_direct_edge_unsafe`, and sweep row M4 is INERT. READ: every add-path
  refusal raises before the first `_emit`. That covers both cycle checks in
  `core.py::_add_edge_locked` and the cap in `_add_direct_edge_unsafe_impl`, whose comment
  states the no-partial-state contract. So the buffer is always empty when a refusal lands.
  The guard matters only for a fault mid-expansion (a DB error), which is fault-injection
  territory, not a refusal. No row was filed: nothing is wrong, and the gap is structural.
* **Removals.** The cap exempts them by design and the cycle checks are add-only, so no
  refusal can truncate a removal fan-out (REASONED).
* **The boolean cascade.** `_GraphSide.apply` and `advance_index` both refuse inside the
  apply loop, before `run_cascade`, so a refused fan-out never reaches the cascade
  (READ). The fixture schema is untainted.
* **PostgreSQL.** The "ids included" half of the claim is SQLite-specific: PG sequences do
  not roll back, so a refused write consumes ids there. Believed harmless, because outbox
  readers key off monotone watermarks, not contiguity (UNVERIFIED: not audited). The
  id-independent half is what would carry over. It was not run against PG.
* **Whether the cap decision itself depends on order** (REASONED only, not probed). A
  leaf's cap region is its ancestors times its descendants at the time it is applied. For
  a TTU fan-out `dP#X -> dC#Y` with `dP != dC`, and for a derived fan-out
  `s -> o#rel.i`, no leaf's subject is another leaf's object. So adding one leaf changes
  neither the ancestor set nor the descendant set of another, and the decision is
  order-independent. A fan-out whose leaves chain would break this argument. None is known.

## § 4 What landed

* `tests/test_tk95_truncated_fanout_rollback.py`: 5 tests plus the sweep table in its
  docstring.
* Nothing in product code changed. The rollback was already correct in every order, on
  both paths. That is the outcome the row predicted ("It is evidently FINE"), and it is now
  pinned rather than inferred.
