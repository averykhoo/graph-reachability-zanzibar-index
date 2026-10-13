# TK140 -- one write path per store id (ACTIVE-PLAN, 2026-10-13)

**FROZEN 2026-10-13d, at `TK140`'s close -- provenance, not a living document.** Status lines
below are as-of-then. Corrections are appended dated at the top, never edited into the body.
Session `2026-10-13d`.
Source: `docs/pypi-trial-0.0.4-2026-10-13.md` BROKEN-2 (p12) and BROKEN-3 (p09).

Provenance labels: **READ** = read first-hand in the tree by the TK140 lead this session;
**REASONED** = the lead's argument, not yet executed; **RUN** = executed, literal output
quoted. No subagent was used: the TK140 lead had no `Agent` tool in its toolset, so the
scout, design, implementation and sabotage were done by the lead directly. No `fable`
consult happened for the same reason; the design decision below is the lead's, recorded
with its reasoning per CLAUDE.md "Who decides".

> **Correction 2026-10-13d (TK140 review, fix lead; RUN first-hand unless labelled).**
> 1. **Sec 2's residuals missed a race against a LOGGED writer, now fixed.** The adoption
>    check ran three separate COUNTs (`RelationTuple`, `TupleLog` ADD, `TupleLog` REMOVE),
>    and on PostgreSQL nothing serialises them (`graphindex/core.py::probe_store_write_lock`
>    is SQLite-only), so READ COMMITTED re-snapshotted between them. The reviewer's
>    deterministic interleave (a `TupleSource.add` committed after the first COUNT) made a
>    fully-logged store refuse with `UnloggedTuplesPresent ... already has 1 RelationTuple
>    row(s) but its tuple log accounts for 2 (ADD 2 - REMOVE 0)` (reviewer RUN; READ by the
>    fix lead: the three `session.exec` calls). By the same arithmetic an unlogged store
>    could be accepted (REASONED). Fix: `connectedstore/store.py::_adoption_counts` reads all
>    three in ONE statement (scalar subqueries), so it reads one snapshot and every committed
>    writer is seen whole or not at all. Pin:
>    `tests/test_tk140_one_write_path.py::test_the_adoption_counts_are_one_statement`
>    (sabotage S12, back to three statements: `1 failed, 12 passed`). PG stress probe
>    (`.scratch/s1013d/fix-lead/race_stress.py`, a writer thread committing while a first
>    open runs, 1000 rounds each): the old three-statement form with a 2 ms gap gave 1
>    spurious refusal and the new form gave 0. The module on PostgreSQL: `19 passed`
>    together with the TK139 module.
> 2. **The reopen cost claim is now pinned.** `test_a_reopened_store_is_never_reaudited`
>    counts `_adoption_counts` calls. Sabotage S11 (the `has_cursor` short-circuit off) now
>    gives `2 failed, 11 passed`; before the pin it was `1 failed` (only the p09 recipe test
>    caught it, incidentally).
> 3. **Sec 4's two non-TK140 reds are resolved.** The claim-rot pin was regenerated after
>    re-reading CORRESPONDENCE.md line 1901 (`tests/test_claim_rot_gate.py` `42 passed`), and
>    `task.py lint` is clean again with `TK142` promoted to NOW.

## 1. The map (READ, 2026-10-13; line numbers are as of this date)

* `src/zanzibar/setengine/engine.py::SetEngine.__init__` sets `self.log_governed = False`
  unconditionally. The comment there rejects "does a TupleLog row exist?" as the governance
  test (the log is empty on a fresh store, and it would cost a SELECT per write).
* `src/zanzibar/setengine/engine.py::SetEngine.add_tuple` / `remove_tuple` refuse with
  `UnloggedWriteRefused` only while `self.log_governed` is True; the `_*_direct` bodies are
  the sanctioned writer's entry (`TupleSource.add/remove`).
* `src/zanzibar/connectedstore/source.py::TupleSource.__init__` is the ONLY setter of
  `log_governed = True` (after `_consistent_rebuild`). It opens its engine via
  `src/zanzibar/connectedstore/schema_io.py::open_set_engine`, which requires a
  `SchemaRecord` (`load_schema` raises `KeyError` otherwise).
* `src/zanzibar/connectedstore/schema_io.py::ensure_schema` -> `save_schema` inserts the
  `SchemaRecord` (table `zanzibar_schema_record`, PK `store_id`) on first bootstrap.
* `src/zanzibar/connectedstore/store.py::ConnectedStore.__init__`: `validate_store_id`,
  `assert_read_isolation`, `probe_store_write_lock` (must be the FIRST statement on
  SQLite), `ensure_schema` (when `schema=` is passed), `open_graph_index` (creates the
  `Store` row), `TupleSource(...)`, `ensure_cursor(session, id, id)` (creates an
  `IndexCursor` at `applied_log_id=0` when none exists), then commits. Nothing looks at
  pre-existing `RelationTuple` rows: an index born here starts EMPTY and is advanced only
  from the log, so tuples that no log row accounts for are invisible to it (BROKEN-3).
* `src/zanzibar/connectedstore/build.py::build_index` is the offline bootstrap for a store
  that already has tuples: it loads the schema (needs a `SchemaRecord`), materialises the
  index from the `RelationTuple` SNAPSHOT, and sets the cursor to the log watermark. It
  refuses a dirty session (`_require_clean_session`) and an index that already has a
  cursor or nodes.
* Layering (READ, `src/zanzibar/__init__.py` docstring + CLAUDE.md): `zanzibar.setengine`
  imports nothing from `zanzibar.connectedstore`; `zanzibar` itself imports nothing. So a
  process can use `SetEngine` without the connected-store models ever being imported, and
  then `SQLModel.metadata.create_all` does NOT create `zanzibar_schema_record`.

### Constructor census (READ, grep 2026-10-13)

`grep -rn "SetEngine(" --include=*.py src tests formal benchmarks scripts`: 68 sites in 37
files. Files that construct a `SetEngine` AND use `ConnectedStore` / `TupleSource` /
`save_schema` / `ensure_schema` / `build_index`: `schema_io.py` (`open_set_engine`, the
sanctioned path), `tests/test_blind_audit_regressions.py`,
`tests/test_connectedstore_multi_instance.py`, `tests/test_connectedstore_source.py`,
`tests/test_matrix.py`, `tests/test_tk125_write_field_types.py`,
`tests/test_tk127_store_id.py`, `tests/test_tk139_lookup_reverse_exclusions.py`,
`tests/test_tupleset_must_be_direct.py`, `tests/test_zt_p1_8.py`,
`tests/test_zt_p1_hardening.py`, `formal/conformance/backends.py`,
`formal/conformance/test_conformance_remove.py`,
`formal/conformance/test_graphadmission_scope_pin.py`, `scripts/installed_smoke.py`.
Spot-read: every standalone `SetEngine` in those files is on its OWN store id (`'s'`,
`'solo'`, `'deep'`, `'diff-set-r'`, ...), not one a `ConnectedStore` governs -- REASONED
from the reads, CONFIRMED only by the targeted runs in section 4.

## 2. Decision (REASONED, the lead's; recorded on the TK140 row)

**(1) A `SetEngine` on a governed store id becomes log-governed; it is not refused.**
"Governed" = a `SchemaRecord` row exists for the store id (it is written by the first
`ConnectedStore`/`save_schema` and is write-once, so it exists from the moment a store is
claimed, even while its log is still empty -- the objection the old comment raised against
a `TupleLog` probe does not apply).
* Why not refuse construction: READS through a second `SetEngine` on a logged store are
  legitimate and used (`open_set_engine`, replica evaluators, the trial's own "fresh
  SetEngine view"); only the unlogged WRITE is the hazard. Auto-governing gives exactly the
  `UnloggedWriteRefused` the trial expected, and keeps every read path.
* Probe at CONSTRUCTION and before a standalone WRITE (once per transaction, memoised on
  the `SessionTransaction` object, the same idiom as `TupleSource._locked_txn`). The
  construction probe covers p12 (store claimed first). The write probe covers the reverse
  order: a standalone engine opened on a fresh id, the id then claimed by a
  `ConnectedStore`, then the engine writes. A latched engine never re-probes; the
  governed path (`TupleSource`'s own engine) never probes at all, so the hot sync write
  path pays nothing.
* Layering: the probe names the table by STRING (`zanzibar_schema_record`) through a Core
  `table()` clause, guarded by `inspect(conn).has_table` (a PostgreSQL statement on a
  missing table would abort the caller's transaction). A test pins the string to
  `SchemaRecord.__tablename__` so a rename cannot silently disable the guard.

**(2) `ConnectedStore` refuses to be BORN over tuples the log does not account for.**
When the open would CREATE the store's `IndexCursor` (no cursor exists yet), it counts
`RelationTuple` rows for the id against the log's net effect (`ADD` rows minus `REMOVE`
rows; admission-validated logging makes these equal on any fully-logged store). On a
mismatch it rolls back (so neither the `SchemaRecord` nor the SQLite write lock survives
the failed open) and raises `UnloggedTuplesPresent`, naming `save_schema` + `build_index`
as the bootstrap for a store that already has tuples. An existing cursor means an index
has already been born (by a previous `ConnectedStore` or by `build_index`), so later
opens pay nothing.

**Residual, NOT closed (REASONED):** under READ COMMITTED a standalone write that is
CONCURRENT with a `ConnectedStore` bootstrap (neither committed) can pass both probes
(write skew). Closing it would need a lock both sides take before either exists, and a
standalone `SetEngine` has no lock surface by design (single writer per store). Likewise
a standalone engine whose CURRENT transaction probed before the claim committed keeps
writing until that transaction ends (the memo). Both are concurrent misuse of one id by
two write paths; the sequential cases from the trial are closed.

## 3. Landed (READ: the lead's own edits, 2026-10-13d; uncommitted at time of writing)

* `src/zanzibar/setengine/engine.py`: `SCHEMA_RECORD_TABLE`, `store_has_schema_record`
  (has_table-guarded Core probe), `SetEngine._probe_log_governance` (latch + per-transaction
  memo `_governance_probed_txn`), called at the end of `__init__` (after the schema compiles,
  before `rebuild`) and at the top of `add_tuple` / `remove_tuple`. `_refuse_unlogged_write`
  renamed `_reject_unlogged_write` (so `tests/test_refused_shape_comments.py` polices it), with
  a `# REFUSED SHAPE (ZT-P1-8a, TK140)` block; its message now says "a ConnectedStore/
  TupleSource owns it -- it has a SchemaRecord" and that a standalone engine needs an unowned id.
* `src/zanzibar/connectedstore/store.py`: `UnloggedTuplesPresent(RuntimeError)`,
  `_reject_unlogged_adoption` (runs right after `probe_store_write_lock`, before
  `ensure_schema`; rolls back before raising), exported from `zanzibar.connectedstore`.
* Tests: new `tests/test_tk140_one_write_path.py` (12 tests on `tests/dbengine.py::
  shared_engine`, so they re-run on PostgreSQL under `ZANZIBAR_TEST_DSN`);
  `tests/test_refused_shape_comments.py` scans `connectedstore/store.py` too (floors
  engine.py 1 -> 2, store.py 1). Two existing tests wrote directly through a standalone engine
  on an id WITH a `SchemaRecord`, which is exactly the refused shape, and were adapted (their
  assertions kept): `tests/test_connectedstore_source.py::test_replaying_log_reproduces_state`
  (a needless `save_schema('replay')` dropped) and
  `tests/test_connectedstore_schema.py::test_open_set_engine_self_describing` (writes now go
  through `TupleSource`, then `se.rebuild()`; it also pins `log_governed` and the refusal).
* Docs: `CHANGELOG.md` [Unreleased] Fixed (2 bullets), `PYPI_README.md` "One write path per
  store id", `docs/architecture/decision-log.md` round-3 bullet.

## 4. Runs (RUN, 2026-10-13d, fresh mktemp logs, rc captured)

* Repros (`.scratch/s1013d/tk140/probe_repros.py`): p12 -> `log_governed: True check: True`,
  `remove: UnloggedWriteRefused ...`; p09 -> `open: UnloggedTuplesPresent store 'app' already
  has 1 RelationTuple row(s) but its tuple log accounts for 0 (ADD 0 - REMOVE 0) ...`,
  `in_transaction after refusal: False`, `SchemaRecord left behind: None`; the INSTEAD recipe
  (`save_schema`, commit, `build_index`, `ConnectedStore(s, id)`) -> `check: True`, then
  `after remove check: False lag 0`; reverse order (claim after open) -> `late remove:
  UnloggedWriteRefused`, `late add: UnloggedWriteRefused`.
* Full `tests/` (bare pytest, NOT the gate): `13 failed, 2385 passed in 1195.62s`. TK140's own
  failure was `test_connectedstore_schema.py::test_open_set_engine_self_describing` (adapted,
  above). The other 12 are NOT TK140: 8 in `tests/test_claim_rot_gate.py` (the claim-rot
  content pin for `src/zanzibar/setengine/engine.py::SetEngine.lookup_reverse`, whose body
  TK139 changed; `formal/correspondence_anchor_pin.txt` needs the deliberate regenerate plus a
  re-read of CORRESPONDENCE.md line 1901), and 4 `tests/test_tasktool.py::test_sabotage_live_*`
  ("BASELINE NOT GREEN on the live corpus": `task.py lint` is red because no row is at NOW).
  No pinned claim-rot anchor is a TK140 symbol (`grep` of the pin file, 2026-10-13d).
* Targeted after the adaptations: `tests/test_connectedstore_schema.py`,
  `test_tk140_one_write_path.py`, `test_connectedstore_source.py`,
  `test_refused_shape_comments.py` -> `57 passed`; `formal/conformance/
  test_graphadmission_scope_pin.py` + `test_zt_p1_8.py` + `test_zt_p1_hardening.py` +
  `test_tk127_store_id.py` + `test_tk125_write_field_types.py` +
  `test_blind_audit_regressions.py` + `test_tupleset_must_be_direct.py` +
  `test_tk122_release_metadata.py` + `test_tk139_lookup_reverse_exclusions.py` ->
  `540 passed`; `formal/conformance/test_conformance_remove.py` -> `135 passed in 513.28s`;
  `scripts/installed_smoke.py --allow-checkout` -> `68 checks passed, 0 failed`.
* Sabotage S1-S10: every one red, literal output in the docstring of
  `tests/test_tk140_one_write_path.py`.
* PostgreSQL leg (`bash scripts/pg_local.sh start`: the conda `zanzibar-pg` server on
  127.0.0.1:55432, not Docker; `ZANZIBAR_TEST_DSN` set, `ZANZIBAR_PG_REQUIRED=1`):
  `tests/test_postgres_ha.py` + `test_tk140_one_write_path.py` + `test_concurrency.py` +
  `test_connectedstore_concurrency.py` + `test_connectedstore_multi_instance.py` +
  `test_zt_p1_8.py` + `test_zt_p1_hardening.py` -> `81 passed, 3 skipped in 122.94s`, rc=0.
  The 3 skips are the pre-existing SQLite-WAL-only pins (`test_connectedstore_concurrency.py`
  lines 156 / 280, `test_connectedstore_multi_instance.py` line 161, reasons in the `-rs`
  output: READ COMMITTED re-snapshots per statement). `test_tk140_one_write_path.py` alone on
  PostgreSQL: `12 passed`. Sabotage on PostgreSQL: S3 (has_table guard removed) ->
  `psycopg2.errors.UndefinedTable: relation "zanzibar_schema_record" does not exist`,
  `1 failed, 11 passed`; S6 (rollback removed) -> `assert not True` on
  `in_transaction()`, `1 failed, 11 passed`. Server then stopped (`pg_local.sh stop` ->
  `pg_local: stopped`; `status` -> `not running`; `wsl docker ps` lists no containers).
* NOT run: any `formal/verify.sh` phase (left to the session's gate agent).
