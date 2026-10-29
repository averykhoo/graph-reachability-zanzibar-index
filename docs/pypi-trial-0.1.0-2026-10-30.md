# Fresh-user PyPI install trial of zanzibar-index 0.1.0 -- 2026-10-30

> **ACTIVE-PLAN** (`docs/README.md` sec 3). The fifth run of the post-release install check
> (previous: [`pypi-trial-0.0.5-2026-10-15.md`](pypi-trial-0.0.5-2026-10-15.md)), including
> [`scripts/installed_smoke.py`](../scripts/installed_smoke.py) against the installed wheel
> (`--version 0.1.0`: 68 passed, 0 failed; control `--version 0.0.5`: one FAIL, the version
> check). Blank conda env, Python 3.13.18, `pip install zanzibar-index==0.1.0` only; env
> removed afterwards. Corrections go at the top, dated. FROZEN once the rows filed from it close.
>
> **Verdict: 1 BROKEN (low severity, over-reporting only), 5 CONFUSING / DOC GAP, 17 WORKS.**
> No wrong permission answer: the agent's own oracle matched both backends on 24,480 cells
> (40 seeds x Roaring / PySets / async), and a deliberately broken oracle showed 30 mismatches.
>
> Release CI for `556011e` / `v0.1.0` (session, first-hand, 2026-10-30): `Publish to PyPI`
> run 40924665912 success through the upload step; `docs` 40924665866 success (Pages deployed);
> `https://pypi.org/pypi/zanzibar-index/0.1.0/json` 200, files
> `zanzibar_index-0.1.0-py3-none-any.whl` and `zanzibar_index-0.1.0.tar.gz`. Before the tag, the
> publish DRY RUN on `984f00b` failed at the wheel smoke step (`AssertionError: 0`); fixed in
> `556011e` (`TK171` log), and the dry run on `556011e` was green.
>
> Provenance: everything below the rule is the trial agent's report, transcribed verbatim
> from the gitignored `.scratch/zanzibar-index-trial-0.1.0/report.md` (AGENT, UNVERIFIED
> unless listed here). Re-run FIRST-HAND by the session against `src/` (HEAD `556011e`, the
> 0.1.0 tag), 2026-10-30, with `PYTHONPATH=src` (confirmed `zanzibar.__file__` in the checkout):
>
> * **F18 CONFIRMED** (SQLite file, two processes): writer `lag()` 1; other process
>   `catch_up()` -> 1; writer `lag()` still `1 1`; writer `check()` True; a fresh instance's
>   `lag()` 0; writer after `refresh()` 0. Cause: `src/zanzibar/store/_store.py::Store.lag`
>   compared against the ORM-cached `self.cursor.applied_log_id`. Filed as `TK172`; fixed on
>   master (counts against the committed cursor row via a scalar subquery), pinned by
>   `tests/test_tk172_lag_reads_committed_cursor.py` (red `assert 1 == 0` before the fix),
>   and checked on PostgreSQL too (`before 1`, `catch_up 1`, `after 0`). Ships in 0.1.1.
> * Not re-run (no BROKEN claim rests on them): F7, F9, F12, F14, F22 (CONFUSING / DOC GAP),
>   filed together as `TK173`.

---

# zanzibar-index 0.1.0 -- fresh-user PyPI install trial (2026-10-30)

- Env: conda env `zanzibar-index-pypi-trial`, Python 3.13.18 (Windows 11, Git Bash), created blank.
- Install: `python -m pip install zanzibar-index==0.1.0` only. Work dir: `%TEMP%/zanzibar-index-trial` (outside repo).
- `zanzibar.__file__` = `...\envs\zanzibar-index-pypi-trial\Lib\site-packages\zanzibar\__init__.py`, `__version__` = `0.1.0`.
- PyPI: wheel + sdist present; requires_python >=3.13; requires_dist sqlmodel>=0.0.39, pyroaring>=1.1.0, extras postgres/test/docs.
- pip pulled in: SQLAlchemy 2.1.6, annotated-types 0.8.0, pydantic 2.14.2, pydantic-core 2.50.2, pyroaring 1.2.0,
  sqlmodel 0.0.48, typing-extensions 4.16.0, typing-inspection 0.4.4, zanzibar-index 0.1.0.
- Docs site (linked from long description) is live: all 14 linked pages checked returned HTTP 200.
- Method: probes are files `pNN_*.py`; `p03_doc_runner.py` executes every code block of a docs page in order and
  checks each `print(x)  # -> expected` comment against the real value (OK / MISMATCH).

### F1 WORKS -- PyPI long-description quickstart runs verbatim (p02_quickstart_verbatim.py)
Extracted the single ```python block from `info.description`; prints True/False/False/True exactly as the comments say.
Re-running it against the same `perms.db` also works (schema re-passed equal; duplicate add_tuple is a no-op).

### F2 WORKS -- Tutorial "Your first permission check" (p03_doc_runner.py tutorials_first-check.html)
All 10 `# ->` claims OK, including lookup/lookup_reverse/result_keys, remove_tuple and reopen-without-schema.

### F3 WORKS -- How-to "Find who can access what": all 18 blocks, every `# ->` claim OK (p03_doc_runner.py how-to_query-access.html)
lookup / lookup_reverse filters, wildcard markers + excluded_keys, expand + `in`/covers, StaleLookupIds, but-not exclusion.
(Runner note: my first runner executed the async page's "# not run: loops forever" worker block and hung; fixed the runner to skip `# not run` blocks. Docs are fine -- they label it.)

### F4 WORKS -- How-to "async mode and freshness tokens": 19/19 claims OK (p03_doc_runner.py how-to_async-tokens.html)
lag/catch_up, at_least fallback, LookupNotFresh, StaleRead helper, stale-revoke trap demo, second-reader lag.

### F5 WORKS -- How-to "Handle errors" (17/17 OK), "Upgrade from 0.0.x" (16/16 OK), reference "Configuration" (5/5 OK)
Upgrade page block 8 is a DSL fragment (not Python), correctly not runnable; the three "# not run" blocks are 0.0.x code.

### F6 WORKS -- Structural schema refusals explain WHY and what to write instead (p04_bad_schemas.py)
25 bad/edge schemas fed to `Store(...)`. All refusals are `zanzibar.SchemaError` subclasses (ZanzibarError=True). The
OpenFGA-rule refusals are excellent: non-direct tupleset ("Store the links on a direct relation (parent_link: [...])"),
userset tupleset ("Use [folder] for the link and \"member from parent\""), recursion under but not
(CyclicDerivedDependency gives a rewrite AND warns it is not the same schema), dangling ref, computed cycle (shows the
path), empty / types-only schemas, conditions, undeclared restriction type (`ShapeNoLongerAccepted.instead`).
Tabs / no indentation accepted (documented: indentation carries no meaning). `define and: [user]` accepted (documented).
`[group:*#member]` emits UnprovenExtensionWarning as documented.

### F7 CONFUSING / DOC GAP -- a few parse refusals give only a token-level message, no rewrite (p04_bad_schemas.py)
- `define viewer: [user]  # people` -> `SchemaError: relation 'viewer': unexpected token '#'`. The docs say "Put the
  comment on its own line", but the message does not; a user porting an OpenFGA model with trailing comments will hit this first.
- `[user: *]` -> `invalid subject type in restriction 'user: *'` (does not say "write `user:*` without the space").
- `a but not b but not c` -> ShapeNoLongerAccepted whose message suggests `'(a or b) but not c'` and whose `.instead`
  talks about `'a or b but not c or d'` and "how 0.0.4 read it" -- irrelevant to a chain of two `but not`s, and the
  0.0.4 history means nothing to a new 0.1.0 user. Suggest: "`(a but not b) but not c`".
- `type us er` -> `malformed type declaration` (fine, but no charset hint).

### F8 WORKS -- Tuple/identifier validation on writes is strict and well-worded (p05_bad_tuples.py)
Space / non-ASCII / 257-char names -> AdmissionRejected naming the charset; 256 chars accepted; undeclared relation
lists the declared ones; wrong subject type lists what the relation admits; `user:alice#...` says "write the bare subject
as 'user:alice'"; object `doc:d1#viewer` says "pass the relation as its own argument"; `user:a#b:c` refused on reads
(TK169 promise holds); duplicate add returns the current watermark; removing a non-stored tuple raises AdmissionRejected
(documented in "Handle errors"). Reads with an undeclared relation/type or bad-charset name answer False, as documented
("check answers False for an undeclared name") -- note a relation typo (`"editr"`) is silently False.
(Non-ASCII showed as `?` in the console only; `ascii(str(e))` shows the correct `'alic\xe9'` -- p06.)

### F9 CONFUSING / DOC GAP -- old 0.0.x keywords give an arity error, not "unknown keyword" (p06_unicode_msg.py)
`store.check(s_type="user", s_name="alice", relation="viewer", o_type="doc", o_name="d1")` ->
`TypeError: check() takes 3 arguments (user, relation, object) or 6 (...); got 5`. The upgrade guide promises a
TypeError (true), but the message never names the bad keyword `s_type`, so an upgrader gets "got 5" for a call that has 5
arguments and cannot see what is wrong. Same for `lookup("user:alice", o_type="doc")` -> "lookup() takes 1 arguments
(user) or 3 (...); got 2" (also "1 arguments"; and it does not mention the documented `object_type=` filter keyword).
Related: the six-part keyword form has no default for `subject_predicate` --
`check(subject_type="user", subject_name="alice", relation=..., object_type=..., object_name=...)` -> "missing a
required argument: 'subject_predicate'"; a user must know to pass `subject_predicate="..."`.

### F10 WORKS -- Both backends agree with a hand-written oracle on and / but not / TTU / wildcards (p09_equivalence.py)
Schema: nested groups with `user:*`, folder `viewer ... or owner`, doc `reader: [user, user:*, group#member] or editor or
viewer from parent`, `viewer: reader but not banned` (banned via users and groups), `can_publish: editor and approver`.
40 seeds x 3 configs (RoaringSets sync, PySets sync, RoaringSets sync=False + catch_up), 45 random adds + 10 removals each,
every (user incl. unmentioned `zed`) x (relation, object) cell compared across Store.check (graph index),
open_set_engine(...).check (set engine), lookup, lookup_reverse (keys + `any` marker - excluded_keys) and expand (`in`):
**24,480 cells, 0 mismatches** (159 writes refused as tuple cycles, see F11).
Instrument control: p09b (oracle sabotaged to ignore `but not banned`) -> 30 mismatches in 2 seeds, so the comparison bites.

### F11 WORKS (documented limit) -- cyclic tuple data refused (p09_equivalence.py)
`store.add_tuple("group:g1#member", "member", "group:g1")` -> `AdmissionRejected: ... would create a cycle in the userset
membership topology`. Differs from OpenFGA, but documented clearly in "Differences from OpenFGA" (§ Tuple data must be
acyclic) and "Limits". A user importing OpenFGA data must pre-check for cycles.

### F12 CONFUSING / DOC GAP -- `RoaringSets` / `PySets` are instances, not classes (p09_equivalence.py first run)
Configuration reference says `ops` takes "RoaringSets (compressed bitmaps) or PySets (builtin sets)"; CapWords names read as
classes, so `Store(..., ops=PySets())` is the natural first try -> `TypeError: 'SetOps' object is not callable`.
Correct is `ops=PySets`. The signature shows `ops: SetOps = SetOps('roaring')`. A one-line "(pass the object, do not call
it)" in the reference would avoid this.

### F13 WORKS -- Persistence, reopen, multi-store isolation, cross-process visibility, error messages (p10_persistence.py)
File DB: reopen with no schema answers from disk; two stores in one DB are isolated; a second OS process sees a sync write
immediately; token from store a on store b -> ForeignToken with a clear per-store message; future token -> StaleRead saying
"not issued yet ... refresh() and retry"; unknown store id -> StoreNotFound telling you to pass `schema=`; DB without
tables -> TablesNotCreated listing the tables and "run SQLModel.metadata.create_all(engine) once, after importing
zanzibar.store". OpenFGA JSON model as dict works, and reopening with the same model as a JSON string is accepted.
Object wildcard (`object_wildcard_shapes={("folder","viewer")}`, tuple on `folder:*`) works, warns
UnprovenExtensionWarning, lookup returns the documented `('folder','viewer','all')` marker; an undeclared shape ->
ShapeNoLongerAccepted naming the declared relations.

### F14 CONFUSING / DOC GAP -- swapping `or` operands counts as a different schema (p11_schema_reformat.py)
Docs (Configuration reference, `SchemaMismatch` reference): "the same schema reformatted, reordered or with comments is
accepted". Accepted: comments, blank lines, spacing, no header, types reordered, relations reordered, restriction entries
reordered (`[group#member, user]`), redundant parentheses. **Refused:** `define viewer: editor or [user, group#member]`
against the stored `define viewer: [user, group#member] or editor` ->
`SchemaMismatch: explicit schema for store 'a' disagrees with its persisted schema, first at doc#viewer; schemas are static (write-once)`.
Repro: create a store with the first form, reopen with `Store(session, "a", schema=<second form>)`.
Fails safe (refuses rather than serves a different model), so not classed BROKEN, but "reordered" in the docs reads as
including this, and the message names the relation but not what differs. Either normalise commutative `or`/`and` operand
order or say "declaration order only" in the docs.

### F15 WORKS -- Documented env knobs and `paranoia=` behave as documented (p10_persistence.py)
ZANZIBAR_PARANOIA residue/full/fixpoint work (writes + checks fine), empty = off, `bogus` -> ValueError listing the allowed
values; `paranoia="Residue"` case-insensitive, `"yes"` = full, `2` refused. ZANZIBAR_MAX_CLOSURE_FANOUT `abc` / `-5` ->
ValueError with the remedy. Configuration-page fan-out demo (cap 3) refuses atomically (F5).

### F16 WORKS -- repo smoke script against the installed wheel (installed_smoke.py, copied into the temp dir)
`installed_smoke.py --version 0.1.0` -> rc=0, "68 checks passed, 0 failed, 10.4s" (import from site-packages, README
quickstart, two 120-op differential grids "all backends agree", hand-written expectations, bad input). No FAIL lines.
Control `--version 0.0.5` -> rc=1, exactly one FAIL: "__version__ is '0.1.0', expected '0.0.5'" (67 passed, 1 failed),
so the version gate bites. (The failing control keeps its scratch DBs in `%TEMP%\zanzibar-smoke-<rand>`; deleted at cleanup.)

### F17 WORKS -- async writer + catch_up worker in a separate OS process (p12_async_two_process.py)
52 async writes (group of 50, group grant, one `but not banned`): untokened check False (index behind), tokened check True for
u1 and False for banned u3 (set-engine fallback), tokened lookup_reverse -> LookupNotFresh with a clear message; worker
process `catch_up(batch=7)` applied 52; afterwards untokened reads are right and lookup_reverse lists 49 users without u3.

### F18 BROKEN (low severity) -- `Store.lag()` stays stale on an instance after another process's catch_up (p13_async_lag_snapshot.py)
Repro (verbatim, file DB `p13.db`):
```python
w = Store(Session(eng), "app", schema="type user\ntype doc\n  relations\n    define viewer: [user]\n", sync=False)
w.add_tuple("user:a", "viewer", "doc:1")
w.lag()        # 1  (correct)
# another process: Store(Session(create_engine("sqlite:///p13.db")), "app", sync=False).catch_up()  -> 1
w.lag()        # 1  <- still 1, repeatedly
w.check("user:a", "viewer", "doc:1")   # True: the same instance's untokened read already sees the applied index
Store(Session(eng), "app", sync=False).lag()   # 0 on a fresh instance
w.refresh(); w.lag()                   # 0
```
Observed: `[0] lag: 1 check: True lag: 1` and `[1] lag: 1 check: True lag: 1`; fresh instance `lag: 0`.
The docs say lag() "counts the log rows the index has not applied yet" and tell you to "Watch index_stalled and lag() from
your monitoring" -- a long-lived monitoring instance would report a permanent backlog for an index that is caught up.
Cause (CONFIRMED by reading the INSTALLED site-packages source `zanzibar/store/_store.py::Store.lag`): the COUNT filters on
`TupleLog.id > self.cursor.applied_log_id`, the instance's cached cursor object, which is not re-read (the tokened lookup
path does re-read the cursor row). Errs toward over-reporting lag, so not a safety issue.

Note: `index_stalled`'s docstring explicitly says it is "as fresh as this session's view of the cursor row" and that a
reader sees another instance's stall "after its next refresh()"; `lag()`'s docstring and the async how-to say nothing of the
kind, and here the session's view is NOT stale (check sees the applied rows) -- only the cached cursor object is. If the
staleness is intended, at minimum the docs for lag() need the same caveat.

### F19 WORKS (documented cost) -- first-hour performance on a modest SQLite file store (p14_perf_first_hour.py)
Nested groups + recursive folders + `but not banned`: 607 sync add_tuple calls took 111 s (~183 ms/write, Windows SQLite
file, one commit each); 1000 checks 1.04 s; user lookup 13 ms; lookup_reverse 31 ms; expand 1 ms; userset lookup 0.24 s;
reopen 0.01 s; DB 7.9 MB. The per-write cost is slow for an import loop but matches the documented "fixed part of about 0.1 s
per write" ("Limits and costs"), and the port-OpenFGA / upgrade guides point large imports at Store.adopt / bulk load.

### F20 WORKS -- pending-changes refusal and 4 threads x 15 writes on one SQLite file (p15_session_threads.py)
A Session with a pending ORM row -> ValueError "Store owns the transaction ... commit or roll back your own changes first".
4 threads, one Session/Store each, 60 concurrent sync writes: no errors (no SQLITE_BUSY surfaced), all 60 users listed.

### F21 WORKS -- every runnable docs page executes and every `# ->` claim holds (p03_doc_runner.py, 31 pages)
Beyond F2-F5: drive-app tutorial 32 OK, backends-direct 9, bulk-load-adopt 12, change-schema 6, fanout-cap 14, patterns 17,
port-openfga 5, prune-outbox 5, rewrite-refused-shape 14, runtime-checks 4, stall-recovery 12, semantics-vs-openfga 19,
boolean-operators 7, wildcard-extensions 6, consistency 7, two-backends 9, graph-index 6, tuple-strings 19, exceptions 15,
schema-language 11, tables 2, environments 2. **0 MISMATCH across all pages.** Remaining "exceptions" were non-Python
blocks (DSL/SQL/table text), the test-permissions page needs pytest (the `[test]` extra; not installed by design), and the
artefacts in F22. Refused-shapes reference is thorough (what / why / instead / raises for each shape).

### F22 CONFUSING / DOC GAP -- docs pages reuse `sqlite:///perms.db` + store "my-app" with different schemas (p03 runs)
The PyPI quickstart, how-to "Port an OpenFGA model", how-to "Prune the change outbox", explanation "The two backends" and
reference "Database tables" all open `create_engine("sqlite:///perms.db")` and `Store(..., "my-app", schema=<their own>)`.
A newcomer who runs the README quickstart and then the port-OpenFGA guide in the same folder gets:
`SchemaMismatch: explicit schema for store 'my-app' disagrees with its persisted schema, first at doc#banned (declared only in
the persisted schema); schemas are static (write-once)` (observed on port-openfga, prune-outbox, two-backends). Run each page
in a fresh folder and all pass. The async page already does `Path("async-demo.db").unlink(missing_ok=True)`; the others
could use their own file names or `sqlite://`. (The message itself is clear -- this is a docs ergonomics issue.)

### F23 WORKS -- changelog promise "public docstrings no longer cite internal task ids or repository paths" (p16_docstring_leaks.py)
Walked 209 public objects (`__all__` of zanzibar, .store, .setengine, .graphindex, .schema + public methods): 0 hits for
TK/ZT-/ASK- ids, `spec §`, `docs/`, `tests/`, `formal/`, `.md`. Without docstrings: only SQLModel-generated `__init__`s and a
few small attributes/properties (`Node.predicate_or_ellipsis`, `SchemaInfo.bridged_in_shapes` / `bridged_out_shapes`,
`Entity.wildcard`, `CompiledBooleans.derived_families` / `leaf_families`) -- cosmetic. All Store methods have docstrings,
though `Store.check/lookup/...` signatures are `(*args, **kwargs)` so `help()` relies on the docstring prose (which is good).

## Summary

Counts: **BROKEN 1, CONFUSING / DOC GAP 5, WORKS 17.**

- BROKEN: F18 `Store.lag()` reports a stale backlog on an instance after another process's `catch_up()` (cached cursor;
  low severity, over-reports).
- CONFUSING / DOC GAP: F7 a few parse refusals lack a rewrite (trailing comment, `[user: *]`, `but not` chain hint talks
  about 0.0.4); F9 old 0.0.x keywords give an arity error that never names the bad keyword; F12 `RoaringSets`/`PySets`
  are instances, not classes; F14 swapping `or` operands is a SchemaMismatch although docs say "reordered" is accepted;
  F22 docs pages reuse `perms.db` + "my-app" with different schemas, so following two pages in one folder hits SchemaMismatch.
- Headline WORKS: quickstart verbatim; all 31 runnable docs pages with 0 `# ->` mismatches; 24,480-cell differential vs a
  hand-written oracle with 0 mismatches (instrument sabotage-checked); smoke script 68/68 with a failing control.

## Cleanup (2026-10-30)
- `conda.exe env remove -y -n zanzibar-index-pypi-trial` rc=0; `conda.exe env list` no longer lists it; env dir gone.
- `%TEMP%\zanzibar-index-trial` and the control run's `%TEMP%\zanzibar-smoke-holkaigw` sent to the Recycle Bin (both
  confirmed absent). Two older `zanzibar-smoke-*` dirs (2026-10-12, 2026-10-15) are not from this run and were left alone.
- No trial python process left running (checked by executable path). Probes + logs kept beside this report.
