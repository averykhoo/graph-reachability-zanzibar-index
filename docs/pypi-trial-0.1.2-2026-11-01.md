# Fresh-user PyPI install trial of zanzibar-index 0.1.2 -- 2026-11-01

> **ACTIVE-PLAN** (`docs/README.md` sec 3). The seventh run of the post-release install check
> (previous: [`pypi-trial-0.1.1-2026-10-30.md`](pypi-trial-0.1.1-2026-10-30.md)), including
> [`scripts/installed_smoke.py`](../scripts/installed_smoke.py) against the installed wheel
> (`--version 0.1.2`: 103 passed, 0 failed, 20.9 s). Blank conda env, Python 3.13.18,
> `pip install zanzibar-index==0.1.2` only; env removed afterwards. Corrections go at the top,
> dated. FROZEN once the rows filed from it (`TK184`, `TK185`) close.
>
> **Verdict: 0 BROKEN, 8 CONFUSING / DOC GAP, 21 WORKS.** No crash, no wrong permission answer.
> Every 0.1.2 claim (TK176 `sync=` / `ops=`, TK179 typed arguments, TK177 messages, re-runnable
> docs pages) held against the published wheel, with the wording caveats C1 / C8 below.
>
> Release CI for `b743587` / `v0.1.2` (session, first-hand, 2026-11-01): `Publish to PyPI` run
> 41222226556 (event push, `v0.1.2`) success (validate tag, gate, fuzz, upload); `docs`
> 41222226687 success; `https://pypi.org/pypi/zanzibar-index/0.1.2/json` 200, files
> `zanzibar_index-0.1.2-py3-none-any.whl` and `zanzibar_index-0.1.2.tar.gz`. Before the tag, on
> the same commit: gate 41053007894, docs 41053007943, the 6-seed `fuzz.yml` 41053019924 and the
> publish dry run 41053023922 all green. The commit before it, `540bb50`, was red on CI only
> (mypy under newer library versions; fixed in `b743587`, gap filed as `TK183`).
>
> Provenance: everything below the rule is the trial agent's returned report, transcribed
> verbatim (AGENT, UNVERIFIED unless listed here). The agent was refused a `Write` of its report
> file, so the session persisted it on receipt; its probes and outputs are in the gitignored
> `.scratch/zanzibar-index-trial-0.1.2/`. Re-run FIRST-HAND by the session against `src/`
> (0.1.2), 2026-11-01, probe `.scratch/trial-0.1.2-recheck/recheck.py`:
>
> * **C1 CONFIRMED**: `add_tuple("user:a", None, "doc:1")` -> `AdmissionRejected: invalid
>   relation None: must match [A-Za-z0-9_./@+=-] (1-256 chars)`; `check("user:a", None,
>   "doc:1")` -> `TypeError: check(): relation must be a str, not NoneType None`.
> * **C4 CONFIRMED**: `parse_openfga_schema(SCHEMA, object_wildcard_shapes=[["folder",
>   "viewer"]])` -> `TypeError: unhashable type: 'list'` (tuples work). Filed as `TK184`.
> * **C5 CONFIRMED**: `result_keys(lookup_reverse("viewer", "doc", "1"))` ->
>   `{('doc', '1', 'viewer'), ('user', 'alice', '...')}`; `check(*('user', 'alice', '...'),
>   "viewer", "doc", "1")` -> `False`; `check('...', 'user', 'alice', "viewer", "doc", "1")` ->
>   `True`. Filed in `TK185`.
> * **C8 CONFIRMED**: `Store(s, 123, schema=...)` -> `AdmissionRejected: invalid store_id 123:
>   must be a str with a non-whitespace character`.
> * C2, C3, C6, C7 and the WORKS lines not re-run; triaged on `TK185`.

---

# zanzibar-index 0.1.2 fresh-user install trial (2026-11-01)

**Verdict: 0 BROKEN / 8 CONFUSING or DOC GAP / 21 WORKS.** Nothing crashed and no wrong answer
turned up. Every 0.1.2 claim I tested holds in substance. The CONFUSING items are rough edges in
argument checking, messages and docs. None of them gives a wrong permission answer, but one (C5)
silently returns `False` for a check that should be `True`.

## Setup
- **Env:** `zanzibar-index-pypi-trial`, created blank, Python **3.13.18**.
- **Install:** `pip install zanzibar-index==0.1.2` and nothing else. pip pulled:
  `SQLAlchemy-2.1.6 annotated-types-0.8.0 pydantic-2.14.2 pydantic-core-2.50.2 pyroaring-1.2.0
  sqlmodel-0.0.48 typing-extensions-4.16.0 typing-inspection-0.4.4 zanzibar-index-0.1.2`. The env
  also had conda's pip 26.2.2, setuptools 84.2.1, wheel 0.48.0 and packaging 26.3.
- **Import check:** `zanzibar.__file__` =
  `C:\Users\user\anaconda3\envs\zanzibar-index-pypi-trial\Lib\site-packages\zanzibar\__init__.py`,
  and `__version__ == "0.1.2"`. All probes ran with `python -I` from a work dir under `%TEMP%`.
- **Smoke:** `installed_smoke.py --version 0.1.2` gave **103 checks passed, 0 failed, 20.9 s**,
  rc=0.

## CONFUSING / DOC GAP

**C1. A non-string relation on a write is `AdmissionRejected`, not `TypeError`.**
- Repro (`p04_sync_and_followups.py` / `p04.out`):
  - `add_tuple("user:a", None, "doc:1")` -> `AdmissionRejected: invalid relation None: must match
    [A-Za-z0-9_./@+=-] (1-256 chars)`. `5` and `remove_tuple` behave the same way.
  - `add_tuple(None, "viewer", "doc:1")` -> `TypeError`, and `check("user:a", None, "doc:1")` ->
    `TypeError`.
- So the same mistake raises a different exception depending on which argument it is in, and the
  release note's "every public argument ... TypeError naming the argument" does not hold here.
- REPO-READ: this is deliberate. `src/zanzibar/schema/tuplestr.py::require_parts` sends write
  parts through `validate_write_identifiers` ("as it always was, only earlier"). It is a wording or
  consistency issue, not a crash.

**C2. `None` as a subject predicate means three different things.**
- Repro (`p05_messages.py` / `p05.out`):
  - On a read it means the bare subject: `check(None, "user", "alice", "viewer", "doc", "1")` ->
    True.
  - On a write it is refused: `add_tuple(None, "user", "bob", ...)` -> `AdmissionRejected: invalid
    subject_predicate None ... or '...'`.
  - On `lookup_reverse(..., subject_predicate=None)` it means no filter, so usersets come back too.

**C3. `ShapeNoLongerAccepted` for a malformed `object_wildcard_shapes` entry.**
- Repro (`p05.out`):
  - `object_wildcard_shapes=frozenset({"folder"})` -> `ShapeNoLongerAccepted:
    object_wildcard_shapes entry 'folder' is not a (type, relation) pair of strings`.
  - `{("folder", "nosuch")}` -> `... names the undeclared relation folder#nosuch (type 'folder'
    declares: parent, viewer)`.
- The exceptions reference says "The message ends with the rewrite". Here `str(e)` has no
  rewrite; it is only in `e.instead`.
- The class name ("a shape an older release accepted", with `accepted_through='0.0.5'`) is odd
  for a plain bad argument, and it is a `ValueError` rather than the `TypeError` the release note
  promises.

**C4. A list-of-lists for `object_wildcard_shapes` gives a raw Python error.**
- Repro (`p03.out`, `p05.out`): `object_wildcard_shapes=[["folder", "viewer"]]` -> `TypeError:
  unhashable type: 'list'`, which does not name the argument.
- REPO-READ: `src/zanzibar/schema/argcheck.py::require_shapes` calls `frozenset(value)` before
  checking the entries.

**C5. Feeding a result key back into `check` silently answers `False`.**
- Repro (`p12_key_order_trap.py` / `p12.out`):
  - `key = ('user', 'alice', '...')` from `result_keys`; `check(*key, "viewer", "doc", "1")` ->
    **False**, but `check(p, t, n, ...)` -> True.
- Result keys are `(type, name, predicate)` while the six-part call is `(subject_predicate,
  subject_type, subject_name, ...)`, and reads are lenient, so the misordered call gives no error.
- The write side does refuse it: `tuple alice:...#user viewer doc:2 matches no declared type
  restriction`.

**C6. `SetEngine.check` / `lookup` have no short `"user:a"` form.**
- Repro (`p11_lowlevel_args.py` / `p11.out`):
  - `open_set_engine(s, "x").check("user:a", "viewer", "doc:1")` -> `TypeError: SetEngine.check()
    missing 3 required positional arguments: 'relation', 'object_type', and 'object_name'`.
  - `se.lookup("user:a")` fails the same way.
- `Store` gives a friendly "takes 3 arguments ... or 6 arguments" message for the same mistake.
  The docs page only shows the six-part form, so this is consistent with the docs, just
  unfriendly.

**C7. A typo in a read's relation answers `False` with no warning.**
- Repro (`p04.out`): `check("user:a", "nosuch", "doc:1")` -> False.
- This is documented in the exceptions reference ("a check naming an undeclared relation answers
  False"), but a typo is easy to miss.

**C8. A non-string `store_id` is `AdmissionRejected`, not `TypeError`.**
- Repro (`p03.out`, `p11.out`): `Store(session, 123, ...)`, `open_set_engine(s, 5)` and
  `build_index(..., index_store_id=7)` -> `AdmissionRejected: invalid store_id 123: must be a str
  with a non-whitespace character`.
- The configuration reference documents this, but it does not fit the 0.1.2 "TypeError naming the
  argument" rule.

## WORKS (one line each)
- **W1 Install:** clean dependency set, `__file__` in site-packages, `__version__` correct.
- **W2 Smoke:** 103/0.
- **W3 README quickstart:** run verbatim, prints True/False/False/True, gives the same output on a
  second run (`p01`).
- **W4 First tutorial:** run verbatim twice, every `# ->` matches (`p02`).
- **W5 Docs pages re-runnable:** 15 how-to/tutorial pages and 19 reference/explanation pages
  extracted and run twice each; 323 annotated prints, 0 mismatches (`docs/summary.txt`,
  `ref/summary.txt`). `how-to/test-permissions` was not run: it needs pytest, which is not a
  dependency, and the page only says "Run them with pytest".
- **W6 `sync=`:** only True/False. None, 0, 1, "yes", "false" and 1.0 all raise `TypeError: sync
  must be True (sync mode) or False (async mode), not ...`, on create, reopen and `adopt` (`p04`).
- **W7 `ops=`:** only PySets/RoaringSets; `PySets()` gets the "pass ops=PySets, without the
  parentheses" hint (`p03`, `p11`).
- **W8 Read part types:** a non-string read part (`check("user:a", None, "doc:1")`, objects,
  `lookup` / `lookup_reverse` / `expand` filters) raises a `TypeError` naming the argument;
  `at_least`, `batch` and `result_keys` types are checked too.
- **W9 `None` predicate on reads:** means the bare subject, positional and keyword (`p05`).
- **W10 `bulk=` / `enable_boolean=`:** bool only on `adopt`, `build_index` and
  `parse_openfga_schema` (`p03`, `p05`, `p11`).
- **W11 `object_wildcard_shapes` pairs:** a bare string -> `TypeError`; non-pairs, undeclared
  types and relations are refused with `.instead`.
- **W12 Refused tuples quoted as written:** `tuple robot:r viewer doc:1 matches no declared type
  restriction ...`, also for the six-part keyword form (`p05`).
- **W13 Cycle refusals say what to do:** tuple cycles ("Instead, leave this tuple out, or remove
  the tuple that closes the loop") and `CyclicDerivedDependency` (gives a rewrite and warns it
  changes meaning) (`p05`, `p07`).
- **W14 Boolean schema answers:** `and` / `but not` / `user:*` / TTU answers are correct by hand;
  `markers` and `excluded_keys` behave as documented; `expand` keys agree with `check` key by key
  (`p06`, `p07`).
- **W15 Backends agree:** graph index and set engine agree on a 2400-cell grid after 177 writes,
  sync and async (`p09`).
- **W16 Async mode:** lag, `catch_up`, tokened check falling back to the set engine;
  `LookupNotFresh`, `StaleRead` and `ForeignToken` messages are clear; `lag()` follows another
  instance's `catch_up` (the 0.1.1 fix) (`p06`, `p07`).
- **W17 Persistence:** reopening with a new engine gives the same answers and watermark; a
  reformatted schema is accepted (`p06`).
- **W18 Lifecycle errors:** `SchemaMismatch`, `StoreNotFound`, `TablesNotCreated` and the
  dirty-session `ValueError` all say what to do (`p06`, `p07`).
- **W19 Knobs:** env vars and `paranoia=` work; bad values are `ValueError`; residue and fixpoint
  writes work (`p06`).
- **W20 Schema refusals:** 21 bad schemas each get a specific message, with rewrites (trailing
  `#`, `[user: *]`, two `but not`s, `from` tuplesets, conditions); OpenFGA JSON models (dict, str,
  wrapped) work and a bad field is named (`p07`).
- **W21 Docstrings, costs and threads:**
  - 82 public objects scanned, 0 internal task ids or paths in docstrings; 6 minor attributes have
    no docstring (`SchemaInfo.bridged_in_shapes` / `bridged_out_shapes`, `Entity.wildcard`,
    `CompiledBooleans.derived_families` / `leaf_families`, `Node.predicate_or_ellipsis`) (`p08`).
  - Costs match the limits page: about 89 ms per sync write on a SQLite file, about 1 ms per
    `Store.check`, 0.04 ms per `SetEngine.check` (`p09`, `p10`). (Trial machine, 2026-11-01.)
  - 3 threads x 30 writes on one SQLite store: 90/90 visible, 0 errors (`p09`).

## Cleanup
- `conda env remove` rc=0; `conda env list` shows 0 matches and there is no env directory.
- The `%TEMP%` work dir and the stray `.db` copies in `.scratch` went to the Recycle Bin.
- No trial python processes are running.
- `git status` was clean: nothing in the repo was edited, committed, pushed or tagged. The
  `.scratch/zanzibar-index-trial-0.1.2/` evidence dir is kept (it is gitignored).
