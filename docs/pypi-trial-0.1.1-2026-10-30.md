# Fresh-user PyPI install trial of zanzibar-index 0.1.1 -- 2026-10-30

> **ACTIVE-PLAN** (`docs/README.md` sec 3). The sixth run of the post-release install check
> (previous: [`pypi-trial-0.1.0-2026-10-30.md`](pypi-trial-0.1.0-2026-10-30.md)), including
> [`scripts/installed_smoke.py`](../scripts/installed_smoke.py) against the installed wheel
> (`--version 0.1.1`: 68 passed, 0 failed). Blank conda env, Python 3.13.18,
> `pip install zanzibar-index==0.1.1` only; env removed afterwards. Corrections go at the top,
> dated. FROZEN once the rows filed from it close.
>
> **Verdict: 1 BROKEN, 4 CONFUSING / DOC GAP, 19 WORKS.** Every 0.1.1 claim (TK172 lag, TK173
> messages and docs, TK175 self-parent) held against the published wheel.
>
> Release CI for `047bc0b` / `v0.1.1` (session, first-hand, 2026-10-30b): `Publish to PyPI` run
> 40976245515 success (validate tag, gate, fuzz, upload); `docs` 40976245308 success (Pages
> deployed); `https://pypi.org/pypi/zanzibar-index/0.1.1/json` 200, files
> `zanzibar_index-0.1.1-py3-none-any.whl` and `zanzibar_index-0.1.1.tar.gz`. Before the tag, on
> the same commit: gate, docs, the 6-seed `fuzz.yml` and the publish dry run all green.
>
> Provenance: everything below the rule is the trial agent's report, transcribed verbatim from the
> gitignored `.scratch/zanzibar-index-trial-0.1.1/report.md` (AGENT, UNVERIFIED unless listed here).
> Re-run FIRST-HAND by the session against `src/` (0.1.1), 2026-10-30b:
>
> * **F19 CONFIRMED**: `Store(sync=None)` and `sync=0` silently select async mode (`lag()` 1, 2);
>   `sync="false"` / `"async"` silently select sync. Cause: `src/zanzibar/store/_store.py::Store.__init__`
>   stores `sync` unchecked. Filed as `TK176`.
> * **F10 CONFIRMED**: `Store(ops="pysets")` -> `AttributeError: 'str' object has no attribute 'new'`.
>   Filed with F19 as `TK176`.
> * F5, F17, F21 (CONFUSING / DOC GAP) not re-run; triaged on the `TK176` / `TK177` rows.

---

# zanzibar-index 0.1.1 fresh-user PyPI install trial (2026-10-30)

Env: conda `zanzibar-index-pypi-trial`, python 3.13.18 (Windows). Work dir `%TEMP%\zanzibar-index-trial-0.1.1`.
`pip install zanzibar-index==0.1.1` pulled: SQLAlchemy-2.1.6 annotated-types-0.8.0 pydantic-2.14.2
pydantic-core-2.50.2 pyroaring-1.2.0 sqlmodel-0.0.48 typing-extensions-4.16.0 typing-inspection-0.4.4 zanzibar-index-0.1.1.
`zanzibar.__file__` = env site-packages (p00_env.py OK), `__version__ == "0.1.1"`.

Provenance: everything below is first-hand from probes in this directory unless labelled REPO-READ.

## Findings
- F1 WORKS: PyPI quickstart verbatim (p01_quickstart.py) prints True/False/False/True; re-run on the existing perms.db also prints the same.
- F2 WORKS: scripts/installed_smoke.py --version 0.1.1 against the wheel: `-- 68 checks passed, 0 failed, 11.9s` (smoke.log).
- F3 WORKS (item g): docs site crawled (45 pages, crawl_docs.py). Every page that opens a SQLite FILE uses its own name (first-check.db, async-demo.db, change-schema.db, checks.db, consistency.db, empty.db+errors.db on errors.html, fanout.db, new.db, port-openfga.db, prune-outbox.db, stall.db, tables.db, two-backends.db+txn.db on two-backends.html, app.db on bulk-load-adopt.html); no two pages share a file. Other pages use in-memory `sqlite://`. PyPI quickstart uses perms.db (not used by any docs page).
- F4 WORKS: every executable docs page run through p02_run_doc_pages.py (extracts the page's python blocks in order, runs them, compares each `print(...)  # -> X` with X), each page in a FRESH process and empty folder: first-check (10 outputs), drive-app (32), async-tokens (19), query-access (27), errors (17), upgrade-0.1 (16), patterns (17), runtime-checks (4), prune-outbox (5), fanout-cap (14), stall-recovery (12), change-schema (6), bulk-load-adopt (12), port-openfga (5), backends-direct (9), rewrite-refused-shape (14), consistency (7), tables (2), two-backends (9). All match on a first run. Logs: p02_run1.log, p02_run2.log, p02_rerun.log.
  (Instrument note: in p02_run2.log stall-recovery errored only because the earlier fanout-cap page set os.environ ZANZIBAR_MAX_CLOSURE_FANOUT=5 in the same process; alone it passes. Not a product finding.)
- F5 CONFUSING / DOC GAP: five docs pages print different values (or raise) when run a SECOND time in the same folder, because they open a fixed SQLite file without deleting it first (async-tokens and errors do `Path(...).unlink(missing_ok=True)`; these do not). Second-run mismatches (p02_rerun.log):
  * how-to/stall-recovery: `print(store.lag())` -> 1, doc says 27 (the tuples already exist, only the removed bad tuple is re-added).
  * how-to/fanout-cap: 7 mismatches (check True vs False, lag 0 vs 1, refused False vs True, catch_up 0 vs 1, message texts).
  * how-to/prune-outbox: outbox_rows 7 vs 5, removed 6 vs 4.
  * explanation/two-backends: set_engine.check(bob viewer roadmap) True vs False.
  * how-to/bulk-load-adopt: 5 problems: UnloggedWriteRefused and IndexExists ("already adopted; open it with Store(session, 'my-app')") -- the errors themselves are clear.
  Fix: give these pages the same `Path("<name>.db").unlink(missing_ok=True)` first line async-tokens uses. 0.1.1's claim "two pages run in one folder no longer clash" is TRUE (distinct file names, F3); it is re-running ONE page that drifts.
- F6 WORKS (claim b, p03_messages.log): every old 0.0.x keyword (s_type/s_name/o_type/o_name) on check, add_tuple, remove_tuple, lookup (incl. the o_type filter), lookup_reverse (incl. s_type filter) raises TypeError naming EACH bad keyword and its 0.1 name, e.g. `check() got an unexpected keyword argument 'o_type' (0.1 renamed the 0.0.x keywords: o_type is now object_type); it takes 3 arguments (user, relation, object) or 6 arguments (...)`.
- F7 WORKS (claim b): arity messages: `lookup() takes 1 argument (user) or 3 arguments (subject_predicate, subject_type, subject_name); got 2` (also for 0 and 4); check and lookup_reverse similar.
- F8 WORKS (claim b): six-part keyword form without subject_predicate (check and add_tuple): `missing a required argument: 'subject_predicate' (pass subject_predicate='...' for a plain subject such as user:alice)`.
- F9 WORKS (claim c): `Store(..., ops=PySets())` and `SetEngine(..., ops=PySets())`: `TypeError: PySets is already a SetOps object, not a class: pass ops=PySets, without the parentheses`. ops=PySets works.
- F10 CONFUSING: `Store(session, "m", ops="pysets")` raises a raw `AttributeError: 'str' object has no attribute 'new'` -- no hint about what ops accepts. Minimal repro: `Store(Session(engine), "m", ops="pysets")` on an existing store. (Low priority; a string is a natural guess next to the documented `SetOps('roaring')` repr in the signature.)
- F11 WORKS (claim d): trailing `# comment` -> `unexpected token '#'; a comment must be on its own line, not after a definition` (also with no space before #); `[user: *]` -> `a wildcard is written type:* with no spaces, e.g. [user:*]`; `type us er` -> `malformed type declaration: 'type us er' (write "type <name>", where the name is one word ...)`; `a but not b but not c` -> ShapeNoLongerAccepted `parenthesise the intended reading, e.g. ... '(a but not b) but not c'`. The parenthesised rewrite and a full-line comment are accepted. No message mentions 0.0.4 (grep count 0).
- F12 WORKS (claim e, p04.log): reopening with `b or a` for `a or b` (also and, but not, nested) raises SchemaMismatch (a ValueError): `explicit schema for store 's0' disagrees with its persisted schema, first at doc#v (its definition differs; type blocks, define lines and restriction lists may be reordered, but the operands of 'or' / 'and' / 'but not' may not); schemas are static (write-once)`. Identical schema and a trailing-space difference are accepted. Note: the text is the same for a GENUINE change (`a or b` -> `a or c`); it never says "the operands are swapped", it just always lists what may and may not be reordered. Accurate in both cases, so WORKS.
- F13 WORKS (claim f, p05.log): the self-parent schema from the brief, sync and async (catch_up after each write), under both RoaringSets and PySets: no IntegrityError, no stall (`lag 0, stalled False` after every catch_up). After `doc:d1 parent doc:d1`: r0 True, r1 False, r2 False (untokened and tokened agree); after removing it r1 True; a reopened instance agrees; re-adding and opening a fresh instance gives r1 False again. Hand-reasoned expectation (REASONED): r1 = r0 but not r0(parent) = True but not True = False with the self-parent; r2 = r1(parent=d1) = False. Matches.
- F14 WORKS (claim a, p06.log): long-lived async instance A, read transaction open (an untokened check just ran), no refresh(): after a same-process instance B's catch_up A.lag() 0 (was 3); after a CHILD PROCESS's catch_up A.lag() 0 (was 2); after a child process wrote 4 tuples A.lag() 4 and A.watermark() includes them; a sync instance's lag sees an async instance's write (1) and its own write applies the backlog (both 0).
- F15 WORKS (p07_first_hour.py, seeds 1-3, logs p07-<seed>.log): Drive-like schema (nested groups + user:* member wildcard, folder owner/viewer, doc "viewer from parent", "approver: [user] and editor", "(...) but not banned"), 150 random add/remove steps per seed. Every 10 steps a sync Store (paranoia="full"), an async Store after catch_up and a standalone SetEngine agree on all 5x20 check cells; lookup / lookup_reverse (+markers, excluded_keys) / expand coverage agree with check on both stores; after closing and reopening the SQLite file a fresh sync and async Store agree. 0 problems on all three seeds (~17 s each). Instrument control: p07_sabotage_ignore_markers.py (ignores lookup_reverse markers) reports 429 REVERSE MISMATCHes on seed 1, so the wildcard-marker path is really exercised.
- F16 WORKS: writes that close a cycle are refused with AdmissionRejected and the store is unchanged (e.g. group:g2#member member group:g0 when g0 is inside g2; p07 seeds 1 and 3 hit 2 and 3 such refusals; the standalone SetEngine refuses the same tuples). Documented in explanation/semantics-vs-openfga and reference/exceptions.
- F17 CONFUSING / DOC GAP (p08_cycles.py, p08.log): whether an object may be its own parent depends on the schema, and the docs read as saying both. With "define viewer: [user] or viewer from parent" on folder, folder:f parent folder:f is refused (sync and async): "AdmissionRejected: tuple folder:f#... parent folder:f would create a cycle in the userset membership topology", matching reference/exceptions ("a folder that is its own ancestor" is refused). With the brief's doc schema (non-recursive from chain), or a parent relation no from uses, the same self-parent tuple is accepted. The 0.1.1 release note ("A tuple that makes an object its own parent (doc:d1 parent doc:d1) under a from chain ... is written normally now") reads as unconditional. The refusal also prints the subject as folder:f#... (internal spelling, not the folder:f the user wrote), says "userset membership topology", and gives no INSTEAD hint. Repro: schema type user / type folder relations "define parent: [folder]", "define viewer: [user] or viewer from parent"; store.add_tuple("folder:f", "parent", "folder:f").
- F18 WORKS: remove_tuple of an unstored tuple -> "AdmissionRejected: non-existent tuple cannot be removed: user:a member group:g is not stored" (as reference/exceptions says).
- F19 BROKEN (p10_sync_kw.py, p10.log): Store's documented "sync (bool)" accepts ANY value and picks the mode by truthiness, with no error. sync=None or sync=0 silently gives ASYNC mode (lag 1 after a write), the mode in which an untokened check keeps allowing a revoked grant (how-to/async-tokens "stale-revoke trap"); sync="false" / "no" / "async" silently give SYNC mode. paranoia= on the same constructor validates strictly ("bad paranoia level 'bogus'; expected one of ..."), as do at_least= and batch=, so sync is the odd one out. Minimal repro:
    e = create_engine("sqlite://"); SQLModel.metadata.create_all(e)
    Store(Session(e), "s", schema=SCHEMA)
    st = Store(Session(e), "s", sync=None); st.add_tuple("user:a", "viewer", "doc:1"); print(st.lag())   # 1: async, no error
    st = Store(Session(e), "s", sync="false"); st.add_tuple("user:b", "viewer", "doc:1"); print(st.lag()) # 0: sync, no error
  Expected: TypeError for a non-bool (as at_least=True / batch=1.5 already raise TypeError).
- F20 WORKS (p09.log, bad input): malformed tuple strings -> MalformedTupleString naming the accepted forms; bad identifiers (space, non-ASCII, 257 chars, int) -> AdmissionRejected naming the charset and 1-256 length; undeclared type / type not admitted -> "matches no declared type restriction for doc#viewer: it admits only user, user:*, group#member"; undeclared relation -> lists the declared ones; doc:* -> "not a declared object-wildcard shape"; Ellipsis -> "write the string '...'"; None subject -> TypeError; at_least -1 / '5' / True / 10**9 / foreign token -> clear ValueError / TypeError / StaleRead ("not issued yet") / ForeignToken; unknown store id -> StoreNotFound with the create recipe; schema "" -> SchemaError; no tables -> TablesNotCreated naming create_all + import zanzibar.store; dirty session -> ValueError; store_id "" or 5 -> AdmissionRejected; batch 0 / 1.5 -> ValueError / TypeError.
- F21 CONFUSING (cosmetic): AdmissionRejected messages quote the tuple in an internal notation the user never wrote: "tuple doc:1#viewer@robot:r#... matches no declared type restriction" for add_tuple("robot:r", "viewer", "doc:1") (object-first, "@", and a "#..." bare predicate). Same notation as F17. The input forms the docs teach are "robot:r" / "doc:1".
- F22 WORKS (reads): check with an undeclared relation or type answers False (documented in reference/exceptions); lookup(relation="nope"), lookup_reverse("nope", ...), expand("nope", ...) return empty results the same way; user:* on a public doc is True for any user and for "user:*" itself.
- F23 WORKS (knobs, child processes): ZANZIBAR_PARANOIA residue / FULL (case-insensitive) / "" (= off) honoured and visible as Store.paranoia; "bogus" -> ValueError at Store creation, listing the levels; paranoia="residue" write works. ZANZIBAR_MAX_CLOSURE_FANOUT 0 disables; "abc" and "-5" -> ValueError at creation; "1" -> ClosureFanoutExceeded naming the variable and "0 disables it"; " 50 " (spaces) is accepted.
  F19 confirmation (read of the INSTALLED wheel, not the repo; line number as of 2026-10-30): site-packages/zanzibar/store/_store.py::Store.__init__ line 456 is a bare `self.sync = sync`, and line 692 branches on `if self.sync:` -- no type check.
- F24 WORKS (p11_two_writers.py, p11.log): two child processes each add 40 tuples to one SQLite store concurrently, sync and async: no SQLITE_BUSY / IntegrityError surfaced (0 retries needed), a fresh instance sees all 80 (async: lag 80, catch_up 80), and 80/80 users are viewers through their groups.

## Verdict counts
24 findings: 1 BROKEN (F19), 4 CONFUSING / DOC GAP (F5, F10, F17, F21), 19 WORKS.
All seven 0.1.1 claims (a-g) hold: a = F14, b = F6-F8, c = F9, d = F11, e = F12, f = F13, g = F3.
