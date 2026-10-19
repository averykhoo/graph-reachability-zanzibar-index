# TK157 -- `Store.adopt`: the adoption recipe as one call (2026-10-19)

> **FROZEN 2026-10-19, at `TK157`'s close -- provenance, not a living document.** Status
> lines below are as-of-then and several may now be false; live state: `HANDOFF.md` + the
> session ledger, and `python scripts/task.py show TK157`. Corrections are appended dated at
> the top, never edited into the body. Was ACTIVE-PLAN (`docs/README.md` §3) until that close.

**Was ACTIVE-PLAN** (`docs/README.md` §3). Row: `TK157` (SPLIT from `TK123`, review item
A25b, `docs/tk123-api-review-2026-10-14.md` row A25). Session key `2026-10-19b`, written by the
workflow agent `TK157/implement` as it scouted. Corrections go at the top, dated.

Provenance labels: **READ** = first-hand read of the named symbol this session; **REASONED** =
inferred, not run; **RUN** = executed this session, output quoted.

## Correction 2026-10-19 (review fix, agent `TK157/fix`)

- **RUN** The "a refused adopt commits nothing" claim below (D2, D3) was FALSE for a bad
  `paranoia` or `ops` argument: `Store.__init__` checked them only after `build_index` had
  committed, so `Store.adopt(s, 'app', schema=S, paranoia='bogus')` left SchemaRecord and
  IndexCursor committed and a retry raised `IndexExists` (reviewer probes
  `probe_adopt_late_refusal.py` / `p1_post_commit.py`, reproduced first-hand). Fixed: adopt
  now calls `resolve_paranoia_level` and checks `isinstance(ops, SetOps)` (`TypeError`) before
  anything is built (the env var `ZANZIBAR_PARANOIA` is covered too). Pinned by
  `tests/test_tk157_store_adopt.py::test_a_bad_store_argument_is_refused_before_anything_is_built`
  and `::test_a_bad_paranoia_environment_is_refused_before_anything_is_built`.
- **RUN** D4's `IndexExists` from adopt now carries adopt's advice ("open it with
  Store(session, 'app')") instead of build_index's; same type. `IndexExists` gained an
  optional `hint` argument and a `detail` attribute (`src/zanzibar/store/build.py::IndexExists`).
- **RUN** New pins: `object_wildcard_shapes` reaches `save_schema`
  (`::test_adopt_saves_the_object_wildcard_shapes`), `ops` passes through (PySets), the
  SchemaMismatch path releases the transaction. The tautological top-level test was
  replaced by an ASCII / no-internal-id docstring check.
- Documented, not changed: a stored `doc:*` tuple without the matching shapes raises
  `ValueError` with `bulk=True` but `AdmissionRejected` with `bulk=False`. That split is
  pre-existing `build_index` behaviour (nothing is committed either way); unifying it belongs
  to `build_index`, not TK157.
- Sabotage S4/S5 are in section 3.2.

## 1. What exists (scouting, 2026-10-19)

- **READ** `src/zanzibar/store/_store.py::_reject_unlogged_adoption` -- the `UnloggedTuplesPresent`
  refusal (TK140) names the recipe in its `# INSTEAD:` block and its message:
  `save_schema(session, id, schema)` if the store has none, `session.commit()`, then
  `build_index(session, id)`, then `Store(session, id)` without `schema=`.
- **READ** `PYPI_README.md` § "Things to know before you use it", bullet "One write path per
  store id": the same four-step recipe is the documented user path.
- **READ** `tests/test_tk140_one_write_path.py::test_p09_the_instead_recipe_adopts_the_store`
  executes the recipe by hand; `docs/pypi-trial-0.0.5-2026-10-15.md` F6 is the install trial
  running it (WORKS).
- **READ** `src/zanzibar/store/build.py::build_index` -- one transaction, commit on success,
  rollback on failure; `_require_clean_session` first; refuses an index with a cursor or graph
  state (`IndexExists`); `_require_quiescent` re-reads the watermark (concurrent writers ->
  `RuntimeError`). It does **not** call `assert_read_isolation` and does **not** call
  `refuse_reusable_node_ids` (grep of `build.py`, 2026-10-19). So a bare `build_index` on a
  SERIALIZABLE PostgreSQL bind or an outdated 0.0.x SQLite file BUILDS, and only the later
  `Store(...)` open refuses -- after an index has been committed.
- **READ** `src/zanzibar/store/source.py::_require_clean_session` -- sees ORM-pending objects
  only (`new`/`dirty`/`deleted`); a FLUSHED object is invisible to it.
- **READ** `src/zanzibar/store/schema_io.py::save_schema` -- `flush()`es the `SchemaRecord`, does
  not commit; identical schema = no-op, different = `SchemaMismatch`.
- **READ** `src/zanzibar/store/_store.py::Store.__init__` -- order: `validate_store_id`,
  `_schema_text` (JSON -> DSL), `_require_clean_session`, then inside try: `assert_read_isolation`,
  `probe_store_write_lock`, `refuse_reusable_node_ids`, `_reject_unlogged_adoption` (skipped once a
  cursor exists), ..., commit; a `DBAPIError` maps to `TablesNotCreated` via `missing_tables`.

## 2. Decisions (REASONED; the row delegates them, CLAUDE.md "Who decides")

- **D1 shape: a classmethod `Store.adopt(session, store_id, *, schema=None,
  object_wildcard_shapes=frozenset(), bulk=True, ops=..., sync=True, paranoia=None)` returning
  `(store, report)`** -- the opened `Store` and the named `BuildReport`. The row says "returns the
  named BuildReport", but a helper that opens a store and then drops it is useless, so the store
  comes back too. A plain 2-tuple, not a new public NamedTuple: no new name on `__all__`, and
  `store, report = Store.adopt(...)` reads naturally. Being a classmethod it needs no new export
  (`Store` is already on `zanzibar.__all__` and `zanzibar.store.__all__`).
- **D2 atomic schema + build.** `save_schema` only flushes, and `build_index`'s clean-session
  guard ignores flushed rows, so adopt does NOT commit between them: `build_index`'s own commit
  lands schema + index together and its rollback undoes both. A refused adopt (a build that
  fails, `IndexExists`, concurrent writes) leaves no `SchemaRecord` behind. (The hand recipe
  commits in between, so a failed build there leaves the schema saved; harmless since a re-save
  of the same schema is a no-op, but adopt does better.)
- **D3 refuse BEFORE building.** adopt runs `assert_read_isolation` (SERIALIZABLE etc. ->
  `UnsafeIsolationLevel`) and `refuse_reusable_node_ids` (TK154 -> `TablesOutdated`) first, so a
  refused adopt commits nothing. `build_index` itself is left unchanged (public, its contract
  untouched).
- **D4 an id that already has an index is `IndexExists`** (from `build_index`), not a silent
  open: adopt is the bootstrap; opening an adopted store is `Store(session, id)`. The schema saved
  in the same call is rolled back with it (D2).
- **D5 schema=None** means "the store already has a persisted schema"; none ->
  `StoreNotFound` (from `build_index`'s `load_schema`). A persisted schema an older version
  saved and this one refuses -> `PersistedSchemaRefused` (from `open_graph_index`), unchanged.
  `schema` accepts what `Store(schema=...)` accepts (DSL, OpenFGA JSON str/dict) via
  `_store.py::_schema_text`.
- **D6 missing tables** -> `TablesNotCreated`, the same `DBAPIError` -> `missing_tables`
  mapping `Store.__init__` uses.
- **D7 PostgreSQL leg: reasoned skip.** adopt adds no SQL, no lock and no isolation logic of its
  own: it sequences `assert_read_isolation`, `refuse_reusable_node_ids` (a no-op off SQLite),
  `save_schema`, `build_index` and `Store.__init__`, each already covered on PG where it matters
  (`tests/test_postgres_ha.py::test_serializable_bind_is_refused`, the TK140 tests through
  `tests/dbengine.py::shared_engine`). The new tests use `shared_engine` too, so they run
  against PG whenever `ZANZIBAR_TEST_DSN` is set. CLAUDE.md's PG rule is for locking,
  watermarks, isolation or multi-instance state; this changes none of them.

## 3. Landed (filled in as it lands)

See the end of this file.

### 3.1 What landed (2026-10-19, uncommitted; the orchestrator commits)

- `src/zanzibar/store/_store.py::Store.adopt` -- classmethod, D1-D6 as above. `UnloggedTuplesPresent`'s
  message and docstring now name `Store.adopt` first, with the hand recipe kept (the TK140 pins
  read `save_schema` and `build_index` in the message; both are still there).
- `tests/test_tk157_store_adopt.py` -- 14 tests (RUN 2026-10-19: `14 passed`), on
  `tests/dbengine.py::shared_engine` where the shape is dialect-neutral (so a PG leg runs
  them), plain SQLite for the TK154 file and missing-tables pins.
- `CHANGELOG.md` `[Unreleased]` / Added; `PYPI_README.md` "One write path per store id" bullet
  now shows `Store.adopt`.
- No `__all__` change: `Store` is already exported at both levels (D1).

### 3.2 Sabotage (RUN 2026-10-19; each restored, then `14 passed` (S1-S3) / `19 passed` (S4-S5))

| id | weakening | red output |
|---|---|---|
| S1 | `session.commit()` after `save_schema` in `Store.adopt` | `test_a_failed_build_leaves_no_schema_behind`: `E       assert (True, False) == (False, False)`; 1 failed, 13 passed |
| S2 | `refuse_reusable_node_ids(session)` replaced by `pass` | `test_an_outdated_sqlite_file_is_refused_before_anything_is_built`: `E       assert (True, True) == (False, False)`; 1 failed, 13 passed |
| S3 | `assert_read_isolation(session)` replaced by `pass` | `test_a_refused_isolation_level_is_refused_before_anything_is_built`: `E       assert (True, True) == (False, False)`; 1 failed, 13 passed |
| S4 (fix) | early `resolve_paranoia_level` / `isinstance(ops, SetOps)` deleted | paranoia + env cases `E       assert (True, True) == (False, False)`, ops case `AttributeError: 'object' object has no attribute 'new'`; 4 failed, 15 passed |
| S5 (fix) | `save_schema(session, store_id, schema)` (shapes dropped) | `test_adopt_saves_the_object_wildcard_shapes`: `ValueError: object wildcard doc:* (relation 'viewer') is not a declared object-wildcard shape ('doc', 'viewer')`; 1 failed, 18 passed |

S2 and S3 matter because the exception TYPE survives the weakening (the `Store` open at the end
raises it anyway, after an index was committed); only the committed-state read goes red.

### 3.3 Targeted runs (RUN 2026-10-19)

- `tests/test_tk157_store_adopt.py` + `test_tk140_one_write_path.py`, `test_tk153_ascii_public_text.py`,
  `test_tk153_install_trial_ergonomics.py`, `test_tk123_no_internal_refs.py`, `test_tk123_top_level.py`,
  `test_tk122_release_metadata.py`, `test_refused_shape_comments.py`, `test_tk154_stale_lookup_ids.py`,
  `test_bulk_build.py`: rc=0, `176 passed in 18.75s`.
- Broad slice (`tests/test_tk1*.py`, `tests/test_*store*.py`, `tests/test_tasktool.py`, `-x`): rc=0, `1328 passed in 665.07s`.
- PostgreSQL leg: reasoned skip (D7). `formal/verify.sh` not run (orchestrator gates).

### 3.4 Next action

Orchestrator: run the gate phases, commit by path. Then `task.py close TK157`.
