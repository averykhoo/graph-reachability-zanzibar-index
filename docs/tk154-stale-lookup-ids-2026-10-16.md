# TK154 -- stale lookup ids translate to the wrong keys: scouting map (2026-10-16)

> **FROZEN 2026-10-16, at `TK154`'s close -- provenance, not a living document.** (Was
> ACTIVE-PLAN, `docs/README.md` sec 3.) Scouting for `TK154` (0.0.5 install-trial F16,
> [`pypi-trial-0.0.5-2026-10-15.md`](pypi-trial-0.0.5-2026-10-15.md) header). Body is
> provenance; corrections are appended **dated at the top**, never edited into the body.
> FROZEN when `TK154` closes.
>
> Provenance labels: **PROBE** = a probe file under `.scratch/tk150-154/` was run by the
> scouting agent (output quoted verbatim); **READ** = the agent read the code at the cited
> `file::symbol`; **REASONED** = inference, not run. Line numbers are as of 2026-10-16 (HEAD
> `d94e307`) and will rot; the `file::symbol` is the durable cite. Written by a read-only
> scouting agent (no `src/` edits); the session must re-verify anything headed for a pin.

## Corrections (newest first)

### 2026-10-16 (session, at the gate) -- two reds the workflow's review did not catch

First-hand (PROBE, the session's gate runs). (1) `tests-tile:2/4`:
`tests/test_tk123_no_internal_refs.py::test_public_docstrings_carry_no_internal_refs` --
`store/schema_io.py refuse_reusable_node_ids [doc] 'TK154'`. The docstring was reworded and
the id moved to a comment. (2) `tests-tile:4/4`:
`tests/test_tk79_outbox_replica.py::test_late_gc_rows_are_load_bearing` -- `precondition: id
9 was expected to be reused for user:u9, got None`. Its membership-level half depended on
SQLite re-handing the GC'd node id, which is exactly the hazard this item removes (D3).
That half now pins the opposite: the id is never re-handed, and u9 gets a higher id. It is
green, and red under `SAB154=S3` (`id 9 was re-handed to a new node ... Node(id=9, ...
name='u9' ...)`). The closure-level half (dropping the late GC rows strands exactly the GC'd
node's pairs) is unchanged.

### 2026-10-16 (review-fix agent) -- the serial is random, the errors pickle, a cite replaced

Three review findings fixed (review report `.scratch/tk150-154/review-tk154.md`, gitignored;
the facts it rests on are now pinned by tests, cited below).

1. **BLOCKING, fixed: the interner serial was unique only within one process.** The
   correction below says "`serial` is a module-level monotone counter"; that counter
   (`_INTERNER_SERIAL = itertools.count(1)`) restarted at 1 in every process, so a
   `SetLookupResult` pickled in one process and translated by a fresh engine in another
   (both `frees == 0`) passed the stamp check and translated to the OTHER engine's entity.
   **PROBE** (reviewer, two interpreters): `B translates A result to {('doc', 'public',
   'reader')}` for a result that read `{('doc', 'secret', 'reader')}`. **Fix (READ):**
   `src/zanzibar/setengine/engine.py::_new_interner_serial` returns `secrets.randbits(64)`
   per `Interner` (`Interner.__init__`), which also covers a forked child (it would have
   continued its parent's counter). The `(serial, frees)` stamp shape is unchanged.
   Pinned by `tests/test_tk154_stale_lookup_ids.py::test_set_engine_result_from_another_process_is_refused`
   (two fresh child interpreters; asserts both stamps have `frees == 0`, so only the serial
   can refuse) and the permanent control
   `::test_sabotage_control_constant_serial_translates_a_pickled_result_wrong`.
   **Sabotage PROBE (2026-10-16):** `_new_interner_serial` made to `return 1` -> the
   cross-process test red with `assert 'REFUSED StaleLookupIds' in "B frees 0 held frees
   0\nTRANSLATED [('doc', 'public', 'reader')]\n"` (the rebuild and another-instance tests
   go red too, with the "freed an interner id" message instead of theirs); restored, green.
2. **Minor, fixed: `StaleLookupIds` did not survive pickle or `copy.copy`** (`TypeError:
   StaleLookupIds.__init__() missing 2 required positional arguments: 'ids' and 'reason'`),
   so a raise in a worker process could not cross back; `TablesOutdated` came back with
   `.table` set to the whole message. **Fix (READ):** `__reduce__` on both
   (`engine.py::StaleLookupIds`, `store/schema_io.py::TablesOutdated`). Pinned by
   `::test_the_new_errors_survive_pickle_and_copy`; **sabotage PROBE:** each `__reduce__`
   renamed away -> exactly those two failures; restored, green. (`TablesNotCreated` has the
   same pre-existing pattern and was left alone: out of scope for TK154.)
3. **Minor, fixed: a cite to a gitignored log.** The correction below cites
   `.scratch/tk150-154/p154_decide_autoinc.log` as the PROBE for "SQLModel honours the dict
   form of `__table_args__`" and "plain SQLite reuses a deleted rowid, `AUTOINCREMENT` does
   not". That file will not survive; the durable evidence is
   `tests/test_tk154_stale_lookup_ids.py::test_graph_node_ids_are_never_reused_on_sqlite`
   (asserts `AUTOINCREMENT` in the live `zanzibar_node` DDL, so the dict form is honoured)
   and `::test_sabotage_control_graph_without_autoincrement_translates_wrong` (on the 0.0.x
   DDL the held id translates to `{('user', 'b', '...')}`, so the rowid IS reused).

Pins (PROBE): `formal/conformance/claim_rot.py --check` after these edits: `509/509 bodies
match`, so no CORRESPONDENCE anchor moved (`Interner.__init__` and the exception classes are
unanchored).

### 2026-10-16 (implementation agent) -- decision taken, what LANDED, sabotage evidence

**Decision (from `.scratch/tk150-154/decide-tk154.md`, session to record on `TK154`):** D1 + D3
+ one shared named error; D2 rejected. Set engine: every `SetLookupResult` from `lookup` /
`lookup_reverse` carries `id_stamp = (interner.serial, interner.frees)`;
`SetEngine.result_keys` / `excluded_keys` refuse a mismatched stamp or a missing id with
`StaleLookupIds` (a `ZanzibarError` and a `KeyError`, defined in
`src/zanzibar/setengine/engine.py` because the set engine cannot import `zanzibar.store`).
`serial` is a module-level monotone counter taken per `Interner` (so `rebuild()` and another
engine instance never share one); `frees` is bumped in `Interner.release` when an id goes to
the free list, so an add of fresh ids never invalidates a held result. Graph:
`zanzibar_node` gets `sqlite_autoincrement` (`graphindex/models.py::Node.__table_args__`),
so a stale graph id can only go MISSING, and `Store._node_keys`'s bare `KeyError` became
`StaleLookupIds`; a `Store` refuses a 0.0.x SQLite file whose `zanzibar_node` lacks
`AUTOINCREMENT` with `TablesOutdated` (a `ZanzibarError` and a `RuntimeError`,
`store/schema_io.py::refuse_reusable_node_ids`). `engine.interner.key` is no longer
documented on the PyPI page; `expand`'s `MemberSet` stays internal-grade. **PROBE**
`.scratch/tk150-154/p154_decide_autoinc.log` (decision agent) confirmed SQLModel honours the
dict form of `__table_args__` and that a plain in-memory SQLite table reuses rowid 1 after
delete + insert while the `AUTOINCREMENT` table hands out 2.

**One deviation from the decision spec (PROBE, implementation agent):** the spec put the
legacy-table check AFTER `Store.__init__`'s bootstrap commit. That read began a new
transaction and left the session on a stale WAL snapshot, and
`tests/test_zt_p1_hardening.py::test_no_false_gap_when_log_ids_interleave_across_stores`
went RED with `sqlite3.OperationalError: database is locked` on
`UPDATE zanzibar_schema_record SET created_at=...` (green with the check no-op'd). The call
now sits INSIDE the open transaction, right after `probe_store_write_lock` (which stays the
first statement), so the bootstrap commit / failure rollback ends the read; a refused open
writes nothing. `refuse_reusable_node_ids` returns when the table is absent, so
`TablesNotCreated` still reports a skipped `create_all`. After the move the zt_p1 module is
green (23 passed).

**LANDED (uncommitted, in the shared tree):** `src/zanzibar/setengine/engine.py`
(`StaleLookupIds`, `_INTERNER_SERIAL`, `Interner.serial` / `.frees`, `Interner.release`
bumps `frees`, `SetLookupResult.id_stamp`, `SetEngine._id_stamp` / `_check_id_stamp` /
`_translate`, both lookups stamp, docstrings incl. `expand`), `src/zanzibar/setengine/__init__.py`,
`src/zanzibar/graphindex/models.py::Node`, `src/zanzibar/store/schema_io.py`
(`TablesOutdated`, `refuse_reusable_node_ids`), `src/zanzibar/store/_store.py`,
`src/zanzibar/store/__init__.py`, `src/zanzibar/__init__.py`, `PYPI_README.md`,
`CHANGELOG.md` ([Unreleased] summary, Added, new Fixed), `tests/test_tk123_top_level.py`
(builtin bases + the two subpackage surfaces), new `tests/test_tk154_stale_lookup_ids.py`
(11 tests, two of them permanent instrument controls), `formal/correspondence_anchor_pin.txt`.

**Pins (PROBE):** `claim_rot.py --check` before regenerating reported exactly three BODY
CHANGED anchors: `src/zanzibar/graphindex/models.py::Node` (CORRESPONDENCE.md line 313 on
2026-10-16), `src/zanzibar/setengine/engine.py::Interner.release` (line 1297) and
`::SetEngine.lookup_reverse` (lines 286, 1917). Re-read (READ): the GraphState row cites
`Node` for identity/keying, unchanged by a DDL option; the `Interner` recycling layer stays
UNMODELED (Lean `Id := SubjectRef`) and a counter does not change recycling;
`lookup_reverse` still renders `expand` (the stamp is metadata, not algorithm). No Lean
change. `--generate` moved exactly those three lines; `--check` rc 0 afterwards.

**Sabotage (PROBE; applied by a pytest plugin, `.scratch/tk150-154/sab154_plugin.py`, that
monkeypatches at configure time, so the shared source was never edited):**

| id | guard removed | result | literal first red |
| --- | --- | --- | --- |
| S1 | both `raise`s in `SetEngine._check_id_stamp` | 4 failed, 7 passed (t1, t2, t3, t5) | t1 at A3: `Failed: DID NOT RAISE StaleLookupIds` (A2 still raises via the missing-id path) |
| S2 | `self.frees += 1` in `Interner.release` | 2 failed, 9 passed (t1, t5) | t1 at A3: `Failed: DID NOT RAISE StaleLookupIds` |
| S3 | `sqlite_autoincrement` on `Node` | 4 failed, 7 passed (t5, t7, t8, t10) | t7: `AssertionError: assert 'AUTOINCREMENT' in 'CREATE TABLE ZANZIBAR_NODE (...'` |
| S4 | `refuse_reusable_node_ids` returns at once | 1 failed, 10 passed (t8) | `Failed: DID NOT RAISE TablesOutdated` |

The wrong VALUES are pinned positively by the two permanent controls, green with the guard
monkeypatched out: t9 `se.excluded_keys(r) == {('doc', 'd', 'banned')}` (the result held
`user:m`), t10 `store.result_keys(r) == {('user', 'b', '...')}` (the result held `user:a`).
Restored: 11 passed.

**Targeted runs (PROBE, each to its own `.scratch/tk150-154/impl154-*.log`, rc 0 unless
noted):** new module 11 passed; `test_tk123_returns` 10; `test_tk123_call_forms` 34;
`test_tk123_top_level` 18 (2 red before its surfaces were updated); `test_tk123_pypi_page` 8;
`test_tk122_release_metadata` 3; `test_connectedstore_multi_instance` 13;
`test_tk139_lookup_reverse_exclusions` 6; `test_lookup_hypothesis` 17; `test_tk95_truncated_fanout_rollback` 5;
`test_setengine_storage` 18; `test_tk122_table_namespace` 6; `test_tk116_oracle_only_setengine` 41;
`test_tk138_userset_self_relation` 7; `test_zt_p1_hardening` 23 (after the move);
`test_refused_shape_comments` 33; `test_tk120_package_layout` 4; `test_lookup_oracle` 50;
`test_tk123_safety_messages` 37; `test_matrix -x` 17. **RED:** nothing known. The gate
(`verify.sh`) was NOT run; the orchestrator runs it.

**Next action:** orchestrator re-verifies the three pin moves and S1-S4 first-hand, records
the decision on `TK154`, runs the gate, commits by path.

---

## 0. Status

Scouting COMPLETE 2026-10-16 (secs 1-5). Nothing in `src/` was changed. Next action: the session picks a design from sec 5 (scout recommends D1 + D3 + de-document `interner.key`), records it on `TK154`, then implements with the sabotage tests in sec 5.2.

## 1. F16 reproduced against current `src/` (HEAD `d94e307`), and two siblings

**PROBE** `.scratch/tk150-154/p154_setengine.py` (log `p154_setengine.log`, rc 0; first line
confirms `zanzibar` resolved to the checkout's `src/zanzibar/__init__.py`). Verbatim output:

```
A1 result: SetLookupResult(node_ids=set(), markers={('user', '...')}, excluded_node_ids={2})
A1 excluded_keys (fresh): {('user', 'm', '...')}
A2 excluded_keys after remove RAISES: KeyError 2
A3 excluded_keys after recycle (eve banned): {('doc', 'd', 'banned')}
A3 fresh lookup: {('user', 'eve', '...')}
B1 lookup(user:c) ids {0} keys {('doc', 'd3', 'viewer')}
B2 same result after rebuild(): {('user', 'b', '...')} CHANGED
B2 fresh lookup ids {3}
C1 MemberSet pos [0] [('user', 'x', '...')]
C2 stale MemberSet via interner.key: [('doc', 'd2', 'viewer')]
```

* **A = F16 exactly as the trial header states**, unchanged by TK123: a stale
  `SetLookupResult` first raises a raw `KeyError: 2`, then after the id is recycled
  `SetEngine.excluded_keys` silently returns `('doc', 'd', 'banned')`, which is not even a
  user -- under a `('user', '...')` marker.
* **B is new and worse for the epoch design: `SetEngine.rebuild()` with NO write in between
  remaps ids.** After churn the free list makes ids non-dense; `rebuild` replays into a
  fresh `Interner` (`setengine/engine.py::SetEngine._reset_state`), which hands out ids in
  replay order, so the same result now names a DIFFERENT live entity (`doc:d3#viewer` ->
  `user:b`). So the stamp must be an **id-map epoch**, bumped by `rebuild()` too, not a
  "write counter". `rebuild()` is reached without any user write via
  `store/source.py::TupleSource.refresh_evaluator` (on `Store._write`'s error path, see its
  docstring) and `TupleSource.__init__`'s `_open_or_rebuild`.
* **C: `expand()`'s `MemberSet` carries the same ids** (`pos`, `neg`), and the only
  translator for it is `engine.interner.key(id)`, which `PYPI_README.md` § "Reading lookup
  results" documents as public. A stale `MemberSet` translates silently wrong the same way.
  (`MemberSet.pos` is frozen via `ops.freeze` in `SetEngine.expand::direct_expand`, so it
  does not alias live engine state -- READ; the hazard is translation only.)

### 1b. The graph side has the same hazard on SQLite, through `Store` (PROBE)

**PROBE** `.scratch/tk150-154/p154_graph.py` (log `p154_graph.log`, rc 0, file-backed SQLite,
`zanzibar` from the checkout). Verbatim output (two `KeyError` messages truncated by the probe
at 90 chars):

```
DDL has AUTOINCREMENT: False
G1 ids {1} keys {('user', 'a', '...')}
G1 max node id 2
G2 after remove RAISES: KeyError "node_ids [1] name no node in store 'g': the lookup result predates a write that removed t
G3 after add (rowid reuse?): {('user', 'b', '...')}
G4 result LookupResult(node_ids=set(), markers={('user', '...', 'any')}, excluded_node_ids={6}) excluded {('user', 'm', '...')}
G5 after unban RAISES: KeyError "excluded_node_ids [6] name no node in store 'g': the lookup result predates a write that 
G6 after eve banned: {('user', 'eve', '...')}
G6 fresh: {('user', 'eve', '...')}
G7 store set-engine result SetLookupResult(node_ids=set(), markers={('user', '...')}, excluded_node_ids={5}) {('user', 'eve', '...')}
```

* **The `zanzibar_node` table has no `AUTOINCREMENT`** (the probe reads `sqlite_master`), so
  SQLite assigns `max(rowid)+1`: once the highest-id nodes are implicitly GC'd, the next
  created node REUSES the id. That is what the TK154 row's 2026-10-15b REASONED note
  predicted; it is now PROBE-confirmed.
* **G3 is a silent wrong answer on the PRIMARY public surface**: a stale
  `Store.lookup_reverse` result naming `user:a` translates through `Store.result_keys` to
  `user:b`, no error. **G6** is the F16 shape on the graph (`Store.excluded_keys`): the
  stale exclusion id of `m` now reads as `eve` (coincidentally the current answer here, but
  only by the accident of reuse order).
* **The documented guarantee is false.** `store/_store.py::Store.result_keys`'s docstring
  and `PYPI_README.md` § "Reading lookup results" both promise that "an id whose node a
  later write removed raises `KeyError`". That holds only until the id is reused (G2 vs G3).
* **Which graph ids are reused (REASONED, not probed):** only on SQLite, and only when the
  deleted node held the highest id(s) in the WHOLE `zanzibar_node` table (the table is shared
  by every store; `_node_keys` filters by `store_id`, so a reuse by ANOTHER store raises the
  loud `KeyError`, not a wrong key). On PostgreSQL the `id` is a sequence/identity column,
  which never hands out a value twice, so a stale graph id there can only go missing
  (`KeyError`), never be renamed. **Not probed against PostgreSQL** (`scripts/pg_local.sh`
  not started by this read-only scout).
* Node deletion sites (the graph's "id-map changes", READ):
  `graphindex/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl` (three
  `session.delete` of implicit nodes, each preceded by `_evict_node`),
  `graphindex/processor.py::DeltaProcessor._gc_subject_node` and `::_gc_public_node`.
  Creation: `graphindex/core.py::ReachabilityIndex.node` (`create_if_missing`) and
  `graphindex/bulk_build.py` (offline bootstrap). `ReachabilityIndex._evict_node`'s docstring
  already names every delete site, so it is the natural choke point for any graph-side bump.

### 1c. Cross-instance, and whether a READ can remap (PROBE)

**PROBE** `.scratch/tk150-154/p154_cross.py` (log `p154_cross.log`, rc 0). Verbatim:

```
X1 a.result_keys(a_res) {('doc', 'd3', 'viewer')}
X2 b.result_keys(a_res) (wrong instance) {('user', 'u2', '...')}
Y1 inst1 set-engine excluded {('user', 'm', '...')}
Y2 inst1 check (a READ): True
Y3 inst1 stale excluded after a READ only: {('user', 'm', '...')}
```

* **X: a `SetLookupResult` handed to ANOTHER `SetEngine` instance over the same store
  translates silently wrong** (`doc:d3#viewer` -> `user:u2`). The class docstring
  (`setengine/engine.py::SetLookupResult`) calls this misuse, but nothing refuses it. A fix
  that stamps only an epoch integer would NOT catch it (two instances can sit at the same
  epoch); the stamp needs an instance identity too.
* **Y: an untokened `Store.check` on a fresh sync index does not touch the set engine**, so
  it did not remap (Y3 still reads `m`, which is stale content but the right identity for
  that id). REASONED from `store/_store.py::Store.check`: the set engine is caught up
  (`TupleSource.catch_up_evaluator`, which `apply_logged`s other instances' rows and so can
  free/recycle ids) only on the fallback branches (index lags `at_least`, or the index is
  stalled), and on every `Store` write (`TupleSource.add` / `::remove` catch up under the
  source lock first). So on a multi-instance deployment, ANOTHER instance's write becomes a
  remap of THIS instance's ids at this instance's next write or fallback read -- the
  holder never wrote anything between the lookup and the translation. Not probed.

## 2. Surfaces: every public result type carrying internal ids, and every translator

READ unless marked. "Translator" = public code that maps an id to a key.

| surface | returns | id field(s) | id domain | public translator(s) | recycled? |
|---|---|---|---|---|---|
| `setengine/engine.py::SetEngine.lookup` | `SetLookupResult` | `node_ids`, `excluded_node_ids` | interner int32, instance-local | `SetEngine.result_keys`, `SetEngine.excluded_keys`, and `SetEngine.interner.key` (documented in `PYPI_README.md`) | YES (PROBE A, B, X) |
| `setengine/engine.py::SetEngine.lookup_reverse` | `SetLookupResult` (built from `expand`'s `MemberSet`: `pos` -> `node_ids`, `neg` -> `excluded_node_ids`) | same | same | same | YES (PROBE A) |
| `setengine/engine.py::SetEngine.expand` | `setengine/memberset.py::MemberSet` (`pos`, `neg` frozen id sets) | `pos`, `neg` | same | only `SetEngine.interner.key` (no `member_keys`) | YES (PROBE C) |
| `graphindex/wildcard.py::WildcardIndex.lookup` / `::WildcardIndex.lookup_reverse` | `graphindex/wildcard.py::LookupResult` (`zanzibar.LookupResult`) | `node_ids`, `excluded_node_ids` | `zanzibar_node.id` rows, global table, filtered per store | none on `WildcardIndex` itself; a direct user reads `Node` rows (the `graphindex/models.py::Node` docstring says `node_ids` are this table's ids) | SQLite: YES (PROBE G3, G6); PostgreSQL: no (REASONED) |
| `store/_store.py::Store.lookup` / `::Store.lookup_reverse` | the graph `LookupResult` (index-served only; no set-engine fallback, `LookupNotFresh` instead) | same | same | `Store.result_keys`, `Store.excluded_keys` (both via `::Store._node_keys` -> `graphindex/core.py::ReachabilityIndex._load_nodes`) | as the graph row |
| `store/source.py::TupleSource.engine` (`Store.source.engine`) | the Store's own `SetEngine` | as the set-engine rows | | | YES (PROBE G7 shows it is reachable) |

Not id-bearing (REASONED): `check` (bool), `Store.watermark` / freshness tokens (ids
of the permanent `TupleLog`, which no library path deletes), `BuildReport`.

Internal persisted ids (out of TK154's scope, flagged): `graphindex/models.py::Residue`'s
`neg` / `upos` JSON hold node ids, and `rebuild_index` deletes `Residue` before `Node`
precisely because "a residue left behind would name a node id the rebuild may hand to a
DIFFERENT node" (`store/build.py::rebuild_index` comment). That is the same hazard inside
the library, already guarded by I13/I14 and the delete order.

Stale doc claims a fix must correct (READ):

* `store/_store.py::Store.result_keys` docstring and `PYPI_README.md` § "Reading lookup
  results": "an id whose node a later write removed raises `KeyError`" -- false after
  reuse (PROBE G3).
* `store/_store.py::LookupNotFresh` docstring: "`SetEngine.result_keys` is the portable
  form; the graph has no twin" -- stale since TK123 item 19 added `Store.result_keys`.

## 3. Is there an epoch already, and where does the id map change?

**No per-engine write counter or epoch exists on any of the three** (READ; a repo-wide
`grep -i "epoch|generation|write_count"` over `src/zanzibar` finds none). The nearest
things are log positions, and neither is an id-map epoch:

* `store/source.py::TupleSource.evaluator_watermark` (the set engine's applied log id).
  It does NOT move on a `rebuild()` that lands at the same log position (PROBE B shows the
  ids move anyway), and a standalone `SetEngine` has no source and no watermark at all.
* `store/models.py::IndexCursor.applied_log_id` (the graph index's). It is reassigned to the
  same value by `store/build.py::rebuild_index`, which deletes and re-creates every `Node`
  row of the store (`for model in (Edge, ResidueRef, Residue, Node): ... delete(...)`), so on
  SQLite a rebuild with no new writes can re-hand the same ids to different nodes
  (REASONED; not probed).

**Set-engine id-map change points** (READ, `setengine/engine.py`). An id is RE-POINTED only
when it is freed and then re-acquired, or when the whole interner is replaced:

| change | site | reached from |
|---|---|---|
| id freed (refcount -> 0, pushed on `_free`) | `::Interner.release` | `::SetEngine._apply_remove` <- `::SetEngine._remove_tuple_direct` (`remove_tuple`; `TupleSource.remove`) and `::SetEngine.apply_logged` (`TupleSource.catch_up_evaluator`) |
| freed id handed to a new key | `::Interner.acquire` (`self._free.pop()`) | `::SetEngine._apply_add` <- `add_tuple`, `apply_logged`, `rebuild` |
| whole map replaced | `::SetEngine._reset_state` (`self.interner = Interner(self.ops)`) | `::SetEngine.rebuild` <- `SetEngine.__init__`, `store/source.py::TupleSource.__init__` (`_open_or_rebuild`), `::TupleSource.refresh_evaluator` <- `Store.refresh` and `Store._write`'s `except Exception` arm (after a rollback) |

So **set-engine recycling is NOT the only recycler**: the graph recycles on SQLite (sec 1b),
and the set engine also remaps wholesale on `rebuild()` with no write (sec 1, B). A pure
ADD that allocates a FRESH id (`self._next`) never invalidates an old result; only a free
(or a reset) can. That makes "bump on free / reset" strictly more precise than "bump on
every write" at the same cost.

**Graph id-map change points** (READ): node rows are created by
`graphindex/core.py::ReachabilityIndex.node` (`create_if_missing=True`) and
`graphindex/bulk_build.py` (bootstrap), and deleted by
`graphindex/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl` (three implicit-GC
deletes), `graphindex/processor.py::DeltaProcessor._gc_subject_node`,
`::DeltaProcessor._gc_public_node`, and wholesale by `store/build.py::rebuild_index`. Every
per-node delete is preceded by `graphindex/core.py::ReachabilityIndex._evict_node`. The
graph's id map is SHARED DATABASE STATE, not instance state: another process's write can
delete and reuse an id this process is holding, so an in-memory graph epoch cannot see it.

## 4. What a fix touches in the gate: CORRESPONDENCE anchors, content pins, existing tests

**Content-pinned symbols** (`formal/correspondence_anchor_pin.txt`, verify.sh step 4d2,
`formal/conformance/claim_rot.py::check_content_pin`; READ 2026-10-16). Any CODE change in
these bodies (docstring/comment edits do not count) turns `verify.sh lean` red until
`claim_rot.py --generate` is run *after re-reading the CORRESPONDENCE.md rows that cite
them*:

| symbol a fix may touch | pinned? | rows citing it (READ) |
|---|---|---|
| `setengine/engine.py::Interner` (class shell: bases + class-level statements only) | yes | sec 2 "also unmapped" + sec 7 "The `Interner` / int32 id-recycling layer" (declared UNMODELED: Lean uses `Id := SubjectRef`, so recycling cannot be expressed) |
| `::Interner.release` / `::Interner.acquire` | yes | same sec 7 bullet |
| `::SetEngine.rebuild` | yes | sec 7 Interner bullet ("`::SetEngine.rebuild` parity") |
| `::SetEngine.lookup_reverse` | yes | the lookup rows |
| `::SetEngine.apply_logged`, `::_apply_add`, `::_apply_remove`, `::expand*` | yes | the state/expand rows |
| `graphindex/wildcard.py::WildcardIndex.lookup` / `::WildcardIndex.lookup_reverse` | yes | the graph read rows |
| `graphindex/models.py::Node` (class shell -- `__table_args__` is in it) | yes | sec 3 `GraphState` row ("identity/keying") |
| `graphindex/core.py::ReachabilityIndex._evict_node` / `::remove_node` / `::_add_direct_edge_unsafe_impl` | yes | sec 7 "Node GC + flag lifecycle AS AN ALGORITHM" (UNMODELED) |
| `store/build.py::rebuild_index`, `store/source.py::TupleSource.catch_up_evaluator` | yes | |
| `::SetEngine.lookup`, `::SetEngine._reset_state`, `::SetEngine.__init__`, `::Interner.__init__`, `::SetEngine.result_keys`, `::SetEngine.excluded_keys`, `::SetLookupResult`, graph `::LookupResult`, `store/_store.py::Store.lookup` / `::lookup_reverse` / `::result_keys` / `::excluded_keys` / `::_node_keys`, `::TupleSource.refresh_evaluator`, `ReachabilityIndex.node` / `::_load_nodes`, the `SetEngine` and `WildcardIndex` class shells | **no** (each grep'd against the pin file: 0 hits) | -- |

So a fix that lives in the UNPINNED column (translator bodies, `_reset_state`,
`SetEngine.lookup`, `Store.*`, the result dataclasses, `Interner.__init__`) does not move
the pin at all. The two places a minimal fix most naturally wants to touch that ARE pinned
are `::Interner.release` (the precise "an id was freed" site) and
`::SetEngine.lookup_reverse` (to stamp its result). Both rows are UNMODELED / read-surface
rows, so no Lean change follows (REASONED from `CORRESPONDENCE.md` sec 7: no modeled
algorithm changes when a result carries a stamp); the cost is a deliberate pin regenerate.
Renaming any anchored symbol reds step 4d (`anchor_check.py`) as well.

**Existing tests that pin the translators or the result dataclasses** (READ; the session
should `--collect-only` before quoting any count):

* `tests/test_tk123_returns.py::test_result_keys_refuses_an_id_with_no_node` -- builds a
  bare graph `LookupResult(node_ids=set(range(10_000, 12_000)))` by hand and expects
  `KeyError` matching `'run the lookup again'` / `'excluded_node_ids'`. A new named error
  must stay a `KeyError` subclass and keep (or deliberately re-pin) that message, and a
  hand-built UNSTAMPED result must still reach the missing-id check.
* `tests/test_tk123_returns.py::test_result_keys_cover_what_the_oracle_allows` and
  `::test_result_keys_and_excluded_keys_read_a_but_not_wildcard` -- the equivalence gate
  over both backends' translators.
* `tests/test_tk123_call_forms.py::test_set_lookup_result_is_a_dataclass_with_equality` -- `SetLookupResult` is
  built by keyword and compared with `==`; a stamp field must be `compare=False` (and have
  a default) or this goes red.
* `tests/test_connectedstore_multi_instance.py::test_result_keys_portability` -- two
  engines over one store, each translating ITS OWN result; an instance-identity stamp keeps
  it green (it never crosses instances).
* `tests/test_tk139_lookup_reverse_exclusions.py`, `tests/test_tk116_oracle_only_setengine.py`,
  `tests/test_zt_p1_hardening.py`, `tests/test_tk138_userset_self_relation.py`,
  `tests/test_tk123_pypi_page.py` -- translate fresh results; unaffected by a stamp.
* `tests/test_lookup_hypothesis.py` builds `SetLookupResult()` and fills it through
  `SetEngine._lookup_sweep`, then compares coverage via `interner.key` -- an unstamped
  internal result; a stamp default of "unstamped" keeps it green.
* Direct `se.interner.key(...)` translation outside `src/` (bypasses any stamp):
  `tests/test_lookup_oracle.py`, `tests/test_setengine_eval.py`,
  `tests/test_setengine_storage.py` (also asserts `se.interner._next` stays small under
  churn), `tests/test_tk116_oracle_only_setengine.py`,
  `tests/test_tk139_lookup_reverse_exclusions.py`. These are test-internal reads of fresh
  results; they need no change, but they show `interner.key` is a de-facto API.
* `tests/test_tk123_top_level.py::test_every_exception_is_exported_from_the_top_level` and
  `::test_every_exception_is_rooted_and_keeps_its_builtin_base` (whose `_BUILTIN_BASE` table must classify every new class) -- a new error class must be
  added to `zanzibar/__init__.py::_LAZY` and root at `ZanzibarError` plus a builtin base.
* `tests/test_tk122_release_metadata.py` / `tests/test_tk123_pypi_page.py` execute
  `PYPI_README.md`; the README's "raises `KeyError`" and `engine.interner.key(id)` sentences
  are the doc half of the fix.

## 5. Candidate designs

### 5.0 PROBE: SQLite `AUTOINCREMENT` on `zanzibar_node` closes the graph half

**PROBE** `.scratch/tk150-154/p154_graph_autoinc.py` = `p154_graph.py` plus ONE line, set
before `create_all` (probe-only; `src/` untouched):
`Node.__table__.dialect_options['sqlite']['autoincrement'] = True`. Log
`p154_graph_autoinc.log`, rc 0. Verbatim, the lines that changed:

```
DDL has AUTOINCREMENT: True
G3 RAISES: KeyError "node_ids [1] name no node in store 'g': the lookup result predates a write that removed t
G6 RAISES: KeyError "excluded_node_ids [8] name no node in store 'g': the lookup result predates a write that 
```

With `AUTOINCREMENT` SQLite never re-hands a rowid (it keeps a high-water mark in
`sqlite_sequence`), so the graph behaves as PostgreSQL does: a stale id can go MISSING
(loud, the existing `Store._node_keys` refusal) but never be RENAMED. G3 and G6, the two
silent wrong answers, become the documented `KeyError`.

### 5.1 The designs

| # | design | covers | cost / risk |
|---|---|---|---|
| **D1** | **Set engine: id-map stamp checked at translation.** `SetEngine` carries a per-instance token plus a monotone `(generation, frees)` pair: `generation` bumped in `::SetEngine._reset_state` (so `rebuild()` invalidates, PROBE B), `frees` bumped when `::Interner.release` actually frees an id (a FRESH-id add never invalidates, sec 3). `SetEngine.lookup` / `::lookup_reverse` stamp the result; `::result_keys` / `::excluded_keys` raise a named `ZanzibarError` + `KeyError` subclass on a mismatch (wrong instance, PROBE X; rebuilt; any id freed since). Field declared `field(default=None, compare=False, repr=False)`; an unstamped (hand-built) result translates as today. | `SetLookupResult` on every path (A, B, X), standalone and inside `Store` (`Store.source.engine`). NOT `MemberSet` / `interner.key`. | O(1) per lookup and per translation. Over-refuses: ANY free anywhere invalidates every held result, which is what the docstring already promises ("only until the next write") but is now enforced. Pins: `Interner.release` + `SetEngine.lookup_reverse` bodies (sec 4) -> one deliberate `claim_rot.py --generate`; no Lean change (Interner is a declared UNMODELED layer). New exception -> `_LAZY`, `_BUILTIN_BASE` (TK153 is settling exception naming, so name it there). |
| **D2** | **Translate eagerly at result construction** (results carry keys; ids become optional/internal). Set engine: `key_of` dict lookups in `lookup` / `lookup_reverse`. Graph: one `_load_nodes` batch per lookup, best placed in `Store.lookup` / `::lookup_reverse` (UNPINNED) rather than `WildcardIndex.lookup*` (PINNED). | Removes the hazard outright for every surface it is applied to, cross-instance included; translation happens in the lookup's own snapshot. | Every lookup pays O(result) even if the caller never translates: for a set-engine `lookup_reverse` over a large population that is a Python loop over `pos` (REASONED; not benchmarked -- `benchmarks/scale_bench.py` exercises lookups and would measure it). Changes `==` and the field set of both result types: an API break, but 0.1.0 is the break. Graph side: one extra query per lookup. |
| **D3** | **Graph: make node ids non-reusable** -- `sqlite_autoincrement=True` in `graphindex/models.py::Node.__table_args__` (PROBE 5.0), and make `Store._node_keys`'s refusal the named error. | Every graph id surface (`Store.result_keys` / `::excluded_keys` and direct `WildcardIndex` users), all writers including other processes and `rebuild_index`, because it is a DATABASE property, not an instance one. | Pinned `Node` class shell moves (sec 4). **Existing SQLite files created by 0.0.x keep the old DDL** (`create_all` never alters a table), so the hole stays open for them unless the store open refuses or warns on a `zanzibar_node` without `AUTOINCREMENT` (read `sqlite_master`, the dialect seam `graphindex/core.py::is_sqlite` is where that check belongs per CLAUDE.md). Minor per-insert cost (`sqlite_sequence` update). PostgreSQL needs nothing (REASONED, not probed). |
| D4 | Graph: an in-memory epoch like D1. | -- | **Rejected (REASONED):** the graph id map is shared DB state; another process's GC/re-create is invisible to an in-memory counter, and a persisted generation column would be a schema migration. |
| D5 | Set engine: stop recycling ids (monotone `_next`). | -- | **Rejected (READ):** recycling is the design (`Interner` docstring: bounds memory by the live count, keeps ids in uint32), pinned by `tests/test_setengine_storage.py` (`interner._next` under churn), and it still would not cover `rebuild()` (PROBE B). |
| D6 | Docs only. | -- | **Rejected:** a silent wrong key at a service boundary is the house failure mode, and the current docs already say "only until the next write" -- F16 happened anyway. |

**`MemberSet` / `interner.key` (PROBE C) is outside D1** -- `memberset.py::MemberSet` is the
internal algebra's value type, built at every `union` / `subtract`, so stamping it is
invasive. The cheap honest options are (a) stop documenting `engine.interner.key(id)` in
`PYPI_README.md` and point users at `lookup_reverse` + `result_keys`, keeping `expand` /
`interner` as internal-grade, or (b) add a stamped `SetEngine.member_keys(m)` and have
`expand` return a wrapper. REASONED preference: (a), since `lookup_reverse` already IS
`expand` rendered as a result.

### 5.2 Scout's recommendation (REASONED -- a recommendation, the session decides)

**D1 for the set engine + D3 for the graph**, with one shared named error (a `KeyError`
subclass under `ZanzibarError`, so `test_result_keys_refuses_an_id_with_no_node`'s
`pytest.raises(KeyError, ...)` keeps passing) raised by all four translators, plus option
(a) for `MemberSet`. That covers every silent wrong answer this scout reproduced (A3, B2,
C2-by-de-documenting, X2, G3, G6) at O(1) per call, and keeps the per-lookup cost flat. D2
is the cleaner contract and worth weighing for 0.1.0 because it is a break anyway; its only
open question is the per-lookup cost on large `lookup_reverse` results, which is one
benchmark run to settle.

**Sabotage plan for the pin** (per `docs/sabotage-procedure.md`): a permanent test running
PROBE A's sequence must raise the named error at A3; deleting the stamp comparison in
`SetEngine.excluded_keys` must turn it red with A3's `{('doc', 'd', 'banned')}`. Likewise a
rebuild variant (PROBE B: dropping the `_reset_state` bump turns it red), a cross-instance
variant (PROBE X), and a graph variant (PROBE G3: dropping `sqlite_autoincrement` turns it
red with `{('user', 'b', '...')}`).
