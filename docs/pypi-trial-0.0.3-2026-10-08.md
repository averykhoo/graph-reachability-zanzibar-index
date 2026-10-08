# Fresh-user PyPI install trial of zanzibar-index 0.0.3 -- 2026-10-08

> **ACTIVE-PLAN** (`docs/README.md` sec 3). The second run of the post-release install check
> (first: [`pypi-trial-0.0.2-2026-10-07.md`](pypi-trial-0.0.2-2026-10-07.md)). New this time
> (user instruction 2026-10-08b): the trial also EXECUTES code paths, by running
> [`scripts/installed_smoke.py`](../scripts/installed_smoke.py) against the installed wheel from
> outside the checkout. Corrections go at the top, dated. FROZEN once the rows filed from it
> close.
>
> Provenance: everything below the rule is the trial agent's report, transcribed verbatim
> from the gitignored `.scratch/zanzibar-index-trial-0.0.3/report.md` (AGENT, UNVERIFIED
> unless listed here). Re-run FIRST-HAND by the session against `src/` (same code as 0.0.3),
> 2026-10-08b:
>
> * **probe06 (BROKEN) CONFIRMED.** Bootstrap `orig` with a schema, reopen with
>   `schema=` set to the identical text: accepted. Trailing newline, CRLF, 4-space indent,
>   appended comment: each `SchemaMismatch explicit schema for store 'orig' disagrees with its
>   persisted schema; schemas are static (write-once)`. Cause READ:
>   `src/zanzibar/connectedstore/schema_io.py::ensure_schema` compares
>   `row.schema_text != schema_text` (line 82 on 2026-10-08). Filed as `TK136`.
> * **Smoke-script hygiene CONFIRMED and fixed** (not a library bug): the script never
>   disposed its engines and kept its temp dir. It now disposes every engine and removes the
>   dir on success; a re-run under `-W default` printed 0 `ResourceWarning` lines and
>   `-- 67 checks passed, 0 failed, 19.4s`.
>
> Routing: `TK136` (BROKEN, reopen byte-compare); `TK135` (README gaps a stranger hit:
> acyclic tuples, recursive boolean relations, silent reads, lookup results); the
> ergonomics items (docstrings, `__all__`, error types, internal ids in messages) are logged
> on `TK123`, which the user parked. The pip-cache note ("use `--no-cache-dir` when
> confirming a fresh release") is a method lesson for the next trial prompt.

---

# zanzibar-index 0.0.3 fresh-user install trial (2026-10-08)

Agent: general-purpose subagent. Env: zanzibar-index-pypi-trial (python 3.13), temp dir $TEMP/zanzibar-index-trial.

## Findings (appended incrementally)

### Install (2026-10-08 ~00:34Z)
- conda env `zanzibar-index-pypi-trial`, Python 3.13.16 (declared floor `>=3.13`).
- `pip install zanzibar-index==0.0.3` FAILED twice (rc=1, "from versions: 0.0.2") at ~00:34Z: the wheel was uploaded 00:32:30Z and pip's local HTTP cache held a stale simple page (PyPI JSON + simple index already listed 0.0.3). `pip install --no-cache-dir zanzibar-index==0.0.3` succeeded (rc=0). Logs: pip-install.log, pip-install2.log, pip-install3.log.
  - Class: CONFUSING (operational, not a package bug): a fresh release can look "not found" for up to the pip cache TTL on a machine that queried the package recently. Any release-confirmation step should use `--no-cache-dir`.
- Resolved deps: SQLAlchemy 2.1.4, annotated-types 0.8.0, pydantic 2.13.5, pydantic-core 2.46.5, pyroaring 1.2.0, sqlmodel 0.0.48, typing-extensions 4.16.0, typing-inspection 0.4.4, zanzibar-index 0.0.3.
- `zanzibar.__file__` = C:\Users\user\anaconda3\envs\zanzibar-index-pypi-trial\Lib\site-packages\zanzibar\__init__.py, `__version__` = '0.0.3'. PYTHONPATH empty. Temp dir: %TEMP%\zanzibar-index-trial.
- Note: `zanzibar` has no `__all__` (AttributeError). Class: CONFUSING (minor; `dir()` still works).

### Part A: installed_smoke.py --version 0.0.3 -- WORKS
- rc=0. Verbatim lines:
  - `zanzibar 0.0.3 from C:\Users\user\anaconda3\envs\zanzibar-index-pypi-trial\Lib\site-packages\zanzibar\__init__.py`
  - `sqlmodel 0.0.48, python 3.13.16`
  - main grid: `op   40: 10 live tuples, 13/198 cells True, all backends agree` / `op   80: 24 live tuples, 35/198 cells True, all backends agree` / `op  120: 50 live tuples, 73/198 cells True, all backends agree`
  - tk126-second-form: `op   40: 10 live tuples, 9/198 cells True, all backends agree` / `op   80: 24 live tuples, 30/198 cells True, all backends agree` / `op  120: 50 live tuples, 66/198 cells True, all backends agree`
  - sections: import, README quickstart, hand-written expectations, bad input
  - `-- 67 checks passed, 0 failed, 18.8s (scratch dbs in C:\Users\user\AppData\Local\Temp\zanzibar-smoke-n3az38c4)`
- No FAIL lines.
- Noise: three `Exception ignored in: <sqlite3.Connection ...> ... ResourceWarning: unclosed database` blocks at the top of smoke.log. (REASONED) They come from GC running inside the script's `warnings.simplefilter('error')` block in `installed_smoke.py::differential`, which turns a ResourceWarning into an "Exception ignored" print; the script never closes its Sessions/engines. Class: CONFUSING (smoke-script hygiene; does not change rc). Part B probe checks whether the library itself leaks connections.
- The script does not delete its scratch dir (it prints the path). 4 other `zanzibar-smoke-*` dirs from earlier runs (08:09-08:11 local, not this agent's) also sit in %TEMP%.
- Full log: smoke.log in this dir.

### Part B

#### probe01 README quickstart -- WORKS
- `probe01_quickstart_verbatim.py` (verbatim copy of the PyPI quickstart): rc=0, run twice in the same dir (second run re-adds the same tuples into the existing perms.db): rc=0, no output, no error.
- `probe01b_quickstart_values.py`: add_tuple returned 1, 2, 3; check True then False exactly as the README comments say; reopen `ConnectedStore(session, "my-app")` -> ban persisted (False), membership persisted (True); reopen passing the same schema again is accepted.
- Under `-X dev`, one `ResourceWarning: unclosed database` at interpreter exit (REASONED: the README's engine is never disposed; SQLAlchemy pool behaviour, not a library leak). Not a finding.

#### help(ConnectedStore) -- CONFUSING / DOC GAP
- `add_tuple`, `remove_tuple`, `check`, `watermark` have NO docstrings; the argument order (subject_predicate, s_type, s_name, relation, o_type, o_name) is only in the README comment. `lookup`/`lookup_reverse` docstrings do not say what they return (type/shape).
- The `__init__` docstring cites internal ids and repo-only files a PyPI user cannot see ("zero-trust review ZT-P1-3", "ZT-P0-1", "blind-audit W2", "TK111/TK112", "benchmarks/results/BASELINE_2026-07-13.md", "docs/tk111-stall-aware-freshness-2026-10-02.md sec 7", "boolean spec 8.1").
- `zanzibar.connectedstore.__all__` exports 25 names incl. internals-looking ones (`log_gap`, `ensure_cursor`, `log_rows`) with no guidance which a user needs; README says `__all__` IS the public surface.

#### probe02 main use cases -- WORKS
- `probe02_main_use_cases.py`, `paranoia="full"`: nested groups, `viewer from parent` across folder->folder->doc with the per-type `viewer` idiom (folder and doc each define their own `viewer`), `or owner`, `and approved`, `but not blocked_here`, removals (unblock restores, removing nested group link revokes), userset-subject check (`group:all#member`): all 15 expectations correct, `FAILS: []`, rc=0.

#### probe03 lookup results are opaque node ids -- CONFUSING / DOC GAP (significant)
- `ConnectedStore.lookup` / `lookup_reverse` return `LookupResult(node_ids={3, 7, 8, 12, 16, 18}, markers=set(), excluded_node_ids=set())`. Nothing in the README, `help(ConnectedStore.lookup)`, or `help(LookupResult)` (no docstring at all) says how to turn ids into (type, name, relation), what `markers` or `excluded_node_ids` mean, or whether excluded ids must be subtracted by the caller.
- A stranger can decode by guessing: `select(zanzibar.graphindex.Node).where(Node.id.in_(r.node_ids))` (`probe03_lookup_decode.py`). Decoded answers are semantically right (bob reaches group:all#member, folder:root#viewer, folder:sub#viewer, doc:d1#viewer, doc:d1#editor and an `implicit=True` doc:d1#approved node; who-views-d1 = bob, carol plus the usersets group:all#member, folder:root#viewer, folder:sub#viewer), and agree with `check`. But `implicit` is undocumented, and lookup mixes usersets with concrete subjects with no filter.

#### probe04 async (sync=False, tokens, catch_up) -- WORKS (two minor CONFUSING notes)
- `probe04_async.py`: lag 2 after two writes; untokened check stale (False); `check(..., at_least=t2)` True via fallback; tokened `lookup` raises `LookupNotFresh` with a clear, actionable message (it does cite internal "zero-trust review ZT-P1-8b"); `catch_up()` returned 2, lag 0; after a ban, untokened check stale True, tokened False (correct revocation semantics).
- CONFUSING: a token that was never issued (`at_least=t3+1000`) raises `StaleRead: token 1003 is not visible in this session snapshot (evaluator at 3); call refresh() to start a fresh read transaction and retry` -- the advice to retry can never succeed for a bogus token; message does not distinguish "not yet visible" from "beyond the log head".
- CONFUSING / DOC GAP: sync mode is not persisted. Reopening the async store with `ConnectedStore(s2, "async-app")` gives a sync instance (default `sync=True`); its write applied synchronously (lag 0). Mixing sync and async instances on one store is not mentioned anywhere a user can see (results were correct).

#### probe05 bad input -- mostly WORKS (output: probe05.out)
- WORKS: empty / whitespace-only schema -> `ValueError: schema declares no type (empty, comments only, or only the model / schema header); a store would persist it write-once and refuse every write`; garbage -> `ValueError: unrecognized schema line: 'hello world'`; None/int/empty/space/colon/hash/non-ASCII/257-char names and None predicate on WRITE -> `AdmissionRejected: invalid subject_name None: must match [A-Za-z0-9_./@+=-] (1-256 chars) or '*'` (clear); unknown relation / unknown type / disallowed subject type / disallowed userset / bare group -> `AdmissionRejected: tuple doc:d1#editor@user:alice#... matches no declared type restriction for doc#editor`; removing a never-added tuple -> `AdmissionRejected: non-existent tuple cannot be removed`; bad paranoia -> clear ValueError listing levels; refused computed tupleset -> long, helpful "WHY + INSTEAD" ValueError; dangling ref -> `ValueError: doc#viewer: references undeclared relation doc#editor`; schema mismatch on reopen -> `SchemaMismatch`.
- WORKS (set semantics, undocumented): duplicate `add_tuple` returns the ORIGINAL token (1) and adds nothing; one `remove_tuple` then makes check False.
- CONFUSING / DOC GAP: reads are lenient and silent. `check` with an unknown relation, unknown type, `None` name or int name all return `False` with no error, while the same values on a write raise. A typo in a relation name in `check` is indistinguishable from "denied". Not documented in the README.
- CONFUSING: `check(..., at_least='abc')` -> raw `TypeError: '>=' not supported between instances of 'int' and 'str'`; `at_least=-1` and `at_least=True` accepted silently.
- CONFUSING: `ConnectedStore(s, "nosuch")` (no schema, store absent) -> bare `KeyError: "store 'nosuch' has no persisted schema"` (message fine, a KeyError is an odd type for a user error; not in `__all__` as a named exception).

#### probe06 reopen with schema= compares TEXT byte-for-byte -- BROKEN (usability; orchestrator to decide if intended)
- Repro `probe06_schema_reopen_and_ids.py`: bootstrap store "orig" with SCHEMA, then reopen with `ConnectedStore(s, "orig", schema=<variant>)`. Output:
  ```
  accepted  identical
  REFUSED   trailing newline added: SchemaMismatch
  REFUSED   leading newline removed: SchemaMismatch
  REFUSED   trailing spaces on a line: SchemaMismatch
  REFUSED   blank line between types: SchemaMismatch
  REFUSED   comment added: SchemaMismatch
  REFUSED   indent 4 instead of 2: SchemaMismatch
  REFUSED   CRLF line endings: SchemaMismatch
  REFUSED   types reordered: SchemaMismatch
  ```
  Every variant parses and works as a FRESH store (`fresh ok ... True` x9). Message: `SchemaMismatch: explicit schema for store 'orig' disagrees with its persisted schema; schemas are static (write-once)` -- does not say the comparison is textual.
- (confirmed from repo source) `src/zanzibar/connectedstore/schema_io.py::ensure_schema` does `if row.schema_text != schema_text or ...: raise SchemaMismatch`, i.e. raw string equality.
- Why it matters: the docstring advertises open-or-bootstrap ("Open (or bootstrap, when schema is given)"), so the natural app-startup pattern is `ConnectedStore(session, id, schema=open("model.fga").read())`. An editor adding a trailing newline, a reformat, or a git `core.autocrlf` checkout on Windows (CRLF) makes the app refuse to start against its own data, with a message that says the schemas "disagree". Loud (not a safety bug), but a semantically identical schema is refused.

#### probe06 store ids / schema header -- CONFUSING (minor)
- Store ids `'bad id!'`, `'a:b'`, a 300-char id: accepted; `''` refused (`AdmissionRejected: invalid store_id '': must be a str with a non-whitespace character`). Store ids are not held to the identifier charset/length that tuple names are; inconsistent but documented in `validate_store_id`'s docstring (which itself cites internal "TK127 follow-up ... tests/test_tk127_store_id.py").
- The `schema X.Y` header is ignored: `schema 1.0`, `1.2`, `9.9` and no header at all are all accepted.

#### probe07 knobs -- WORKS (with CONFUSING notes)
- `probe07_knobs.py paranoia`: `ZANZIBAR_PARANOIA` = residue/full/off/1 all accepted; `bogus` -> `ValueError: bad paranoia level 'bogus'; expected one of ('off', 'residue', 'full', 'fixpoint') (or a bool / [...])`; explicit `paranoia='off'` overrides a bogus env value (precedence as documented). Level `'fixpoint'` appears in the error but not in the constructor docstring (DOC GAP, minor). The active level is not observable from the public surface.
- `ZANZIBAR_MAX_CLOSURE_FANOUT=50 probe07_knobs.py fan`: a sync write producing 120 closure rows -> `ClosureFanoutExceeded: closure fan-out cap exceeded: this edge would materialise 120 closure rows (10 ancestors x 10 descendants + fringes), over the limit of 50 for store 'fan'. Raise it with ReachabilityIndex(max_closure_fanout=...) or ZANZIBAR_MAX_CLOSURE_FANOUT (0 disables the cap), or split the grant -- ...`. Atomic as the README says: log rows 20 -> 20, check stays False in both directions, store usable afterwards. `=0` disables (write accepted, 21 rows). `=abc` -> clear `ValueError: ZANZIBAR_MAX_CLOSURE_FANOUT='abc' is not an integer (use a positive row count, or 0 to disable the cap)` at construction.
- CONFUSING: the refusal says "Raise it with ReachabilityIndex(max_closure_fanout=...)", but a `ConnectedStore` user has no such argument; only the env var is reachable without dropping to internals.
- CONFUSING: on the async path the over-cap row is accepted into the log and `catch_up` applies it "with a warning" (docstring), but that warning is a `logging` record, not a Python `warnings` warning: `warnings.catch_warnings(record=True)` captured `[]`; the text `closure fan-out cap exceeded on a replayed row (async apply or build_index), materialised anyway: 120 closure rows ... over the limit of 50 for store 'fan-async'` went to stderr via logging's last-resort handler. So the cap means different things on sync vs async (documented in catch_up's docstring, not in the README's "Write cap" bullet, which says "The write then lands in neither backend").

#### probe08 persistence across processes, multi-tenant isolation -- WORKS
- `probe08_persistence_multistore.py write` then `... read` (separate processes): two stores ("tenant-a", "tenant-b") in one SQLite file are isolated (cross-tenant checks False); state survives process restart; revoke in the second process works; a second Session reading the same store sees a writer's commit (and `at_least=tok`, `refresh()`) correctly. With `engine.dispose()` no ResourceWarning (so the smoke-log warnings are not a library connection leak).
- Note: tokens/watermarks are global across stores (A watermark 2, B watermark 3), as `lag()`'s docstring says; not mentioned in README (harmless).

#### probe09 wildcards + standalone SetEngine cross-check -- WORKS (CONFUSING notes)
- `probe09_wildcards_and_setengine.py`: `[user, user:*, group#member] but not banned` emits no warning (plain OpenFGA); public `user:*` grant + ban of mallory: ConnectedStore and a standalone `SetEngine(s, id, schema)` agree on all 9 queried cells (ann True, mallory False, nobody True on d1, False on d2, etc.).
- `[group:*#member]` emits `UnprovenExtensionWarning` (as README says) and evaluates as expected (zoe True, stranger False). CONFUSING: the warning is emitted TWICE for one `ConnectedStore(...)` construction (under `simplefilter("always")`), and its text cites repo internals ("formal/, W4Fragment").
- DOC GAP (reinforces probe03): `lookup_reverse("viewer","doc","d1")` on the public doc returns `LookupResult(node_ids=set(), markers={('user', '...', 'any')}, excluded_node_ids={4})`, i.e. "any user except node 4". Correct, but a caller must know to interpret markers and subtract exclusions; nothing documents it.

#### probe10 / probe10b: recursive `viewer from parent` that also has `but not` is refused by ConnectedStore, accepted by SetEngine -- CONFUSING / DOC GAP (significant)
- `probe10_deep_differential.py` (all 3 seeds) died at construction: `CyclicDerivedDependency: derived relations form a dependency cycle (boolean spec §1.9 forbids recursion through boolean relations): [('doc', 'secret_viewer'), ('doc', 'viewer'), ('folder', 'viewer')]` (my probe's schema; the list names doc relations that only DEPEND on the cycle, the cycle itself is folder#viewer).
- Minimal repro `probe10b_recursive_boolean_ttu.py`, schema:
  ```
  type folder
    relations
      define parent: [folder]
      define blocked: [user]
      define viewer: ([user] or viewer from parent) but not blocked
  ```
  Output:
  ```
  parse_openfga_schema: zanzibar.schema.errors.CyclicDerivedDependency: derived relations form a dependency cycle (boolean spec §1.9 forbids recursion through boolean relations): [('folder', 'viewer')]
  SetEngine: accepted -> SetEngine
  ConnectedStore: zanzibar.schema.errors.CyclicDerivedDependency: ... [('folder', 'viewer')]
  reopen 'cs' after refusal: KeyError "store 'cs' has no persisted schema"
  SetEngine: a views root True | a views sub (blocked) False
  ```
- So this very common OpenFGA idiom (folder hierarchy with a per-folder block) works on `zanzibar.setengine` but not on `ConnectedStore`/graph index, the two public backends do NOT accept the same schema set, and the README is silent on it. The README's "Schema shapes" bullet promises refused shapes come "with an explanation of what to write instead"; this message has a WHY ("boolean spec §1.9", which a PyPI user cannot read) but no INSTEAD. `CyclicDerivedDependency` is a ValueError subclass exported from `zanzibar.schema`. The refusal is clean (no schema persisted). (REASONED: this is a known design restriction of the stratified delta processor, not a correctness bug; the gap is user-facing documentation and the missing INSTEAD.)

#### probe10c deep differential on a stratifiable rewrite -- WORKS
- `probe10c_deep_differential_stratified.py` (folder: `inherited: [user, group#member] or inherited from parent`, `blocked_eff: [...] or blocked_eff from parent`, `viewer: inherited but not blocked_eff`; doc: `viewer: ([user] or viewer from parent) but not banned` where `banned` is itself `[...] but not suspended`; `secret_viewer: viewer from parent and clearance`; `audit: auditor from parent and clearance`). 150 seeded ops, 41-cell grid, four backends: sync ConnectedStore(paranoia="full"), async ConnectedStore + catch_up, SetEngine(PySets), SetEngine(RoaringSets). Seeds 1-4: `diffs=0` at every checkpoint (`seed 1 DONE diffs=0 refused=8`, `seed 2 ... refused=4`, `seed 3 ... refused=1`, `seed 4 ... refused=3`). (Probe flaw: a skipped duplicate add also skips that op's checkpoint, so some seeds have 2 checkpoints instead of 3.)
- All 16 refusals were cyclic DATA, see probe11.

#### probe11 cyclic tuples are refused at write time, by BOTH backends -- CONFUSING / DOC GAP
- `probe11_cyclic_tuples.py`: `group:b#member member group:a` after `a in b`, `group:c#member member group:c`, and a folder parent loop are refused identically by ConnectedStore and SetEngine: `AdmissionRejected: tuple group:b#member member group:a would create a cycle in the userset membership topology`. Non-cyclic tuples evaluate identically (ann member b True, ann views y True on both).
- Consistent across backends (good for equivalence), but OpenFGA accepts cyclic group/folder tuples, real directories contain mutual group nesting, and the README does not say data must be acyclic. The refusal is data-dependent, so it surfaces in production, not at schema time. "userset membership topology" is jargon.

#### probe12 table-name clash + threaded writers -- WORKS
- `probe12_threads_and_tables.py tables`: 10 tables, all `zanzibar_*` (`zanzibar_delta_outbox, zanzibar_edge, zanzibar_index_cursor, zanzibar_node, zanzibar_relation_tuple, zanzibar_residue, zanzibar_residue_ref, zanzibar_schema_record, zanzibar_store, zanzibar_tuple_log`); a user model reusing `zanzibar_delta_outbox` -> `sqlalchemy.exc.InvalidRequestError: Table 'zanzibar_delta_outbox' is already defined for this MetaData instance. ...` -- loud, as the README says.
- `... threads` and `... threads-default` (4 threads x 15 writes, one Session per thread, one SQLite store; with `timeout=30` and with SQLite's default timeout, the default run twice): `0 errors, 60/60 grants visible` every run. No SQLITE_BUSY at this scale.

## Summary (2026-10-08)
- Part A smoke: WORKS -- rc=0, `67 checks passed, 0 failed, 18.8s`, zero FAIL lines.
- BROKEN: 1, usability-class: reopen with `schema=` compares text byte-for-byte (probe06), so a trailing newline, a reformat or CRLF refuses a semantically identical schema. Loud, not a safety bug.
- CONFUSING / DOC GAP, significant: (a) recursive `viewer from parent` + `but not` is accepted by SetEngine but refused by ConnectedStore, with no INSTEAD in the error and no README mention (probe10b); (b) lookup results are opaque node ids/markers/exclusions with no documented decoding (probe03, probe09); (c) cyclic tuples are refused at write time on both backends, unlike OpenFGA, and the README does not say so (probe11); (d) `check` silently returns False for unknown relations/types and None/int names (probe05).
- CONFUSING, minor: pip cache stale right after upload; no `zanzibar.__all__`; core methods lack docstrings; docstrings/messages cite internal ids and repo-only files; bogus-token StaleRead advice; sync mode not persisted; `at_least` type handling; KeyError for a missing store; store-id charset not enforced; schema version header ignored; ClosureFanoutExceeded points to `ReachabilityIndex(max_closure_fanout=...)`; async over-cap "warning" is a log record; `fixpoint` paranoia level undocumented; UnprovenExtensionWarning emitted twice; smoke script's own ResourceWarning noise and leftover scratch dir.
- WORKS: install, import location, quickstart verbatim + reopen, groups/nesting, TTU per-type viewer idiom, and/but not, removal/revocation, userset subjects, async tokens/catch_up/LookupNotFresh, persistence across processes, multi-tenant isolation, write-side validation messages, refused-shape messages (tupleset), paranoia env/arg precedence, fan-out cap atomicity, `user:*` + exclusion, standalone SetEngine agreement, a 4-seed 4-backend differential (0 diffs), table namespace clash, threaded SQLite writers.

## Cleanup (2026-10-08)
- `conda.exe env remove -y -n zanzibar-index-pypi-trial` rc=0; `conda env list` shows 0 matches; envs dir gone.
- `%TEMP%\zanzibar-index-trial` and this run's `%TEMP%\zanzibar-smoke-n3az38c4` sent to the Recycle Bin, confirmed absent. No trial python processes running.
- Left in place (not mine): `%TEMP%\zanzibar-smoke-{a8hc9ig5,ajxzspwl,q3jo64cm,xfr1dx6m}` from earlier smoke runs (08:09-08:11 local).
- Kept: this report dir.
