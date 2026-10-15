# Fresh-user PyPI install trial of zanzibar-index 0.0.5 -- 2026-10-15

> **ACTIVE-PLAN** (`docs/README.md` sec 3). The fourth run of the post-release install check
> (previous: [`pypi-trial-0.0.4-2026-10-13.md`](pypi-trial-0.0.4-2026-10-13.md)), including
> [`scripts/installed_smoke.py`](../scripts/installed_smoke.py) against the installed wheel
> (no args: 67 checks passed, 0 failed; `--version 0.0.5`: 68 passed; control `--version 0.0.4`:
> `FAIL __version__ is '0.0.5', expected '0.0.4'`, rc 1). Blank conda env, Python 3.13.16,
> `pip install zanzibar-index==0.0.5` only (pulled sqlmodel 0.0.48, SQLAlchemy 2.1.4, pyroaring
> 1.2.0, pydantic 2.14.1); env removed afterwards. Corrections go at the top, dated. FROZEN once
> the rows filed from it close.
>
> **Verdict: 0 BROKEN, 3 DOC GAP, ~10 CONFUSING.** Release CI for `b17759e` / `v0.0.5`: `gate`
> success, `Publish to PyPI` success, `https://pypi.org/pypi/zanzibar-index/0.0.5/json` 200
> (session, first-hand, 2026-10-15).
>
> Provenance: everything below the rule is the trial agent's report, transcribed verbatim
> from the gitignored `.scratch/zanzibar-index-trial-0.0.5/report.md` (AGENT, UNVERIFIED
> unless listed here). Re-run FIRST-HAND by the session against `src/` (HEAD `b17759e`, the
> 0.0.5 tag), 2026-10-15, with `PYTHONPATH=src` (confirmed `zanzibar.__file__` in the checkout):
>
> * **F16 CONFIRMED, and WORSE than the agent reported** (the agent's p14 re-run against
>   `src/`, plus a session probe): `excluded_keys(old_result)` after the ban is removed raises
>   `KeyError: 2`. After the freed id is RECYCLED (ban `eve` next), the stale result silently
>   translates instead: excluded id `{2}` was `('user', 'm', '...')`, and after the recycle
>   `se.excluded_keys(r)` returns `{('doc', 'd', 'banned')}` with no error. The docstring's
>   "only until the next write" makes this misuse, but a silent wrong translation at a
>   service boundary is the house failure mode. Filed as `TK154` (NEXT).
>   Probe (verbatim):
>   `P = "type user\ntype doc\n  relations\n    define banned: [user]\n    define viewer: [user, user:*] but not banned\n"`;
>   add `user:*` viewer and `user:m` banned on `doc:d`; `r = se.lookup_reverse("viewer", "doc", "d")`;
>   remove `m`'s ban; add `user:eve` banned; `se.excluded_keys(r)` -> `{('doc', 'd', 'banned')}`.
> * **F3 CONFIRMED** (non-ASCII docstrings): `inspect.getdoc(zanzibar.connectedstore.advance_index)`
>   contains `U+00A7` and `U+2464`; `.encode("cp1252")` fails with `'charmap' codec can't
>   encode character '⑤'`, which is what printing it to a redirected Windows stdout does.
> * Not re-run (no BROKEN claim rests on them): the remaining DOC GAP / CONFUSING items.
>   Most map onto `TK123`'s accepted list (mapping on the `TK123` row, 2026-10-15); the rest
>   are `TK153` (LATER).

---

# Fresh-user install trial: zanzibar-index 0.0.5 (2026-10-15)

Env: conda `zanzibar-index-pypi-trial`, python 3.13, `pip install zanzibar-index==0.0.5` only.
Work dir: `C:\Users\user\AppData\Local\Temp\zanzibar-index-trial` (outside repo).
Probes are copied beside this report.

## pip list (after install)
annotated-types 0.8.0, packaging 26.3, pip 26.2.1, pydantic 2.14.1, pydantic_core 2.50.1,
pyroaring 1.2.0, setuptools 84.0.0, SQLAlchemy 2.1.4, sqlmodel 0.0.48, typing_extensions 4.16.0,
typing-inspection 0.4.4, wheel 0.47.0, zanzibar-index 0.0.5.
pip pulled in: pyroaring, typing-extensions, annotated-types, typing-inspection, SQLAlchemy,
pydantic-core, pydantic, sqlmodel, zanzibar-index (packaging/setuptools/wheel came with conda python).
PyPI metadata: requires_python >=3.13; requires_dist sqlmodel>=0.0.39, pyroaring>=1.1.0.

## Findings (appended as they land)

### F1 WORKS -- install location/version (p01_where.py)
`zanzibar.__file__` = `...\envs\zanzibar-index-pypi-trial\Lib\site-packages\zanzibar\__init__.py`, `__version__` = `0.0.5`.
Subpackage `__all__` lists printed; `zanzibar` top-level `__all__` is empty (fine, import name only).

### F2 WORKS -- README quickstart verbatim (p02_quickstart.py, extracted programmatically from info.description)
Exit 0; its final `assert` holds.

### F3 CONFUSING -- docstrings (p03_help.py)
- Docstrings contain non-ASCII (`§`, circled digits like U+2464). `print(inspect.getdoc(advance_index))` with stdout
  redirected on Windows (cp1252) raises `UnicodeEncodeError`; fine with PYTHONIOENCODING=utf-8 / interactive console.
- Docstrings are dense with internal references a PyPI user cannot follow: "spec §6.4", "ZT-P1-8a", "TK123 A16",
  "perf P12b", `tests/test_bulk_build.py`, `docs/tk139-...md`, `benchmarks/results/...`. `SetEngine` class docstring
  is one line ("Raw-tuple, bitmap-backed reachability engine (storage + writes; §5, §6.1-6.2)"); `SetEngine.check`
  has NO docstring. `SetEngine.lookup` docstring is ~60 lines of internal completeness proof.
- `ConnectedStore` has no `expand` method (only check/lookup/lookup_reverse); README is consistent with that.

### F4 WORKS -- main use cases, both backends agree (p04_core.py)
Schema with nested groups, TTU (`viewer from parent`), `and`, `but not`, `user:*`. 30 user checks + a userset check:
0 mismatches SetEngine vs ConnectedStore. `lookup` (alice) identical key sets on both. `lookup_reverse viewer doc:pub`
(user:* granted, mallory banned): SetEngine markers `{('user','...')}` + `excluded_keys` `[('user','mallory','...')]`;
ConnectedStore markers `{('user','...','any')}` + excluded node mallory -- matches README "Reading lookup results".
`expand` returns a `MemberSet(pos, stars, neg)`. Removing a ban flips both. SetEngine dup add -> False;
remove of a missing tuple -> `AdmissionRejected: non-existent tuple cannot be removed` on both.
Minor CONFUSING: `ConnectedStore.add_tuple` of a duplicate tuple returns an int (12, equal to the current head) with no
new log row; README says "Each write commits and returns a log id" without saying a no-op returns the head.

### F5 WORKS -- persistence / reopen / SchemaMismatch / async (p05_persist.py)
- SQLite file store reopened in a new engine with `ConnectedStore(session, "app")` reads persisted schema: correct answers.
- Reopen with the same schema re-indented, CRLF, reordered, with a comment, no header: accepted.
- Reopen with a different schema, or different `object_wildcard_shapes`: `SchemaMismatch`.
- NEW 0.0.5: `SetEngine(s, "app", DIFFERENT)` on a ConnectedStore-owned id -> `SchemaMismatch` with a long, clear
  message naming `open_set_engine`; same schema re-indented -> accepted; `open_set_engine(s, "app")` works;
  `SetEngine.add_tuple` there -> `UnloggedWriteRefused` (clear message). `zanzibar.connectedstore.SchemaMismatch is
  zanzibar.schema.SchemaMismatch` -> True.
- `ConnectedStore` takeover of a standalone-written id -> `UnloggedTuplesPresent` with the adoption recipe.
- `sync=False`: untokened check stale (False), `check(at_least=tok)` True (fallback), `lookup(at_least=tok)` ->
  `LookupNotFresh` (clear message), after `catch_up()` lookup works.
CONFUSING (minor):
- The ConnectedStore reopen `SchemaMismatch` message is terse ("explicit schema for store 'app' disagrees with its
  persisted schema; schemas are static (write-once)") -- it does not say what differs or that the fix is a new store
  id / omit `schema=`; also reports the same text when only `object_wildcard_shapes` differ.
- Opening an unknown store id without a schema (`ConnectedStore(s,"nope")`, `open_set_engine(s,"nope")`) raises bare
  `KeyError("store 'nope' has no persisted schema")`; does not suggest passing `schema=`.
- `check(..., at_least=10**6)` (a token that never existed) raises `StaleRead: ... call refresh() ... and retry` --
  refreshing can never help for a bogus token.

### F6 WORKS -- adoption recipe from UnloggedTuplesPresent (p06_adopt_advance.py)
`save_schema` -> commit -> `build_index` -> `ConnectedStore(s, id)`: adopted answers correct (alice True, banned bob
False), and removing the ban then works. CONFUSING: `save_schema` / `build_index` return values print the entire
compiled RuleSet (huge reprs); `IndexCursor` repr is `IndexCursor()` (no fields shown);
`help(IndexCursor)` shows only pydantic's generic BaseModel docstring.
(My first attempt passed `ensure_cursor(s, src, idx)` -- the order is (index_store_id, source_store_id); user error,
but the resulting message "index 'x-src' already materializes source 'x-src', not 'x-idx'" did help.)

### F7 WORKS -- NEW 0.0.5 MissingDeltaProcessor (p07_advance_proc_none.py)
`advance_index(s, cursor, widx, ruleset, None)` on `viewer: [user] but not banned` raises
`zanzibar.connectedstore.apply.MissingDeltaProcessor` (isinstance ValueError True), nothing applied (lag stays 1),
and `catch_up()` afterwards repairs it. Union-only schema with `proc=None` applies (returns 1, check True).

### F8 DOC GAP -- MissingDeltaProcessor tells you to build `DeltaProcessor(widx, ruleset.compiled)`, which is not public (p08_deltaprocessor_fix.py)
`DeltaProcessor` is in no subpackage `__all__`; the README says "Each subpackage's `__all__` is the public surface".
It is importable from `zanzibar.graphindex.processor` (also leaks via connectedstore.apply/build/store, none in
`__all__`). The error message does not say where to import it from. Following the advice with
`from zanzibar.graphindex.processor import DeltaProcessor` works (advance returns 3, alice True, banned bob False).
Either export it (graphindex `__all__`) or say the import path in the message.

### F9 WORKS -- NEW 0.0.5 TK137 DSL refusals, identical on parse_openfga_schema / SetEngine / ConnectedStore (p09_refusals.py)
All refused with a ValueError naming the fix: `schema 1.2`, bare `schema`, `schema 1.0`, `model foo`,
`schema 1.1 # hi`, `relations # docs`, `relations define viewer: [user]`, `a but not b or c`, `a or b but not c`,
`a but not b but not c`, `a and b but not c`, `[usr]` undeclared (also via `parse_openfga_json`). Parenthesised
forms accepted. Also refused clearly: conditions, `module`, `extend type`, dangling ref, computed cycle, computed
tupleset, userset tupleset, `.` in relation name, bad charset type name, garbage, empty schema. Recursion through
`but not`: `CyclicDerivedDependency` on parse/ConnectedStore, accepted by SetEngine -- exactly as README says.
CONFUSING:
- The TK137 refusals raise a class named `ShapeRefusedSinceTK137` (`zanzibar.schema.errors`), a ValueError subclass
  NOT in `zanzibar.schema.__all__`; a user-facing exception named after an internal ticket. It carries an `instead`
  attribute that is not documented anywhere a user can see (README mentions `instead` only for
  PersistedSchemaRefused).
- `[user, team#member]` with no `type team`: message says "names an undeclared relation team#member" rather than
  "undeclared type 'team'" (the `[usr]` case gets the better type message).

### F10 WORKS -- NEW 0.0.5 PersistedSchemaRefused for stores persisted by <=0.0.4 (p10_persisted_refused.py)
Simulated by inserting `SchemaRecord` rows with refused shapes (`a or b but not c`, `relations # docs`, `schema 1.2`,
undeclared `user`). `ConnectedStore(s, id)` and `open_set_engine(s, id)` both raise `PersistedSchemaRefused`
(ValueError) with a message quoting the refusal, the meaning-preserving rewrite (in `.instead`), and "needs a NEW
store id". Excellent message. (Gap, not tested further: no public helper to enumerate/export the old store's tuples
to re-write them under a new id.)

### F11 WORKS -- write validation / read leniency / tuple cycles (p11_badinput_wildcards.py)
Bad names (space, empty, 257 chars, `zoë`, int, None/'' predicate), undeclared type/relation, disallowed type,
disallowed `user:*`, undeclared object wildcard: `AdmissionRejected` on both backends with the same message. 256 chars
and `a.b+c@x.com` accepted. Typo'd relation / bad identifier in `check` -> False (documented). `lookup*` on unknown
things -> empty result. Group cycle and self-membership -> `AdmissionRejected ... would create a cycle` on both.
Minor CONFUSING: an undeclared relation write says "matches no declared type restriction for doc#vewer" rather
than "relation 'vewer' is not declared on doc".

### F12 WORKS -- wildcard extensions + README "All does not imply some" (p11_badinput_wildcards.py)
`[user:*]` silent; `[group:*#member]`, `parent: [folder, folder:*]`, object wildcards emit `UnprovenExtensionWarning`.
README zero-folders example reproduces exactly on both backends: alice denied on doc:1 with no folder, allowed once
one folder exists.
CONFUSING: the warning text cites "formal/, W4Fragment" and "See task ASK-2" -- internal references a PyPI user cannot
resolve. ConnectedStore emits the warning TWICE per construction (engine.py:467 and compiler.py:622).

### F13 WORKS -- knobs (p12_knobs.py, p13_fanout.py)
- `paranoia=` off/residue/full/True/False all work; bad value -> clear ValueError listing levels (which include an
  undocumented `'fixpoint'`). `ZANZIBAR_PARANOIA` residue/full/1 work; `bogus` -> same clear ValueError.
- `ZANZIBAR_MAX_CLOSURE_FANOUT=10`: a write adding 50 closure rows is refused with `ClosureFanoutExceeded`; atomic
  (edges 50->50, watermark unchanged, check False on both). `0` and `100000` accept it. `abc` / `-5` -> clear ValueError.
  CONFUSING: the refusal message says "Raise it with ReachabilityIndex(max_closure_fanout=...)", but a
  ConnectedStore user has no such constructor argument; only the env var is reachable.
- `ops=PySets` works on SetEngine and ConnectedStore.

### F14 WORKS -- repo smoke script against the installed wheel (installed_smoke.py, smoke.out / smoke2.out / smoke3.out)
Copied to the temp dir and run with the trial env python, outside the repo. Imports zanzibar 0.0.5 from the env's
site-packages. No args: `67 checks passed, 0 failed, 47.7s`, rc 0. `--version 0.0.5`: `68 checks passed, 0 failed,
40.1s`, rc 0. Control: `--version 0.0.4` -> `FAIL __version__ is '0.0.5', expected '0.0.4'`, rc 1 (the check can fail).

### F15 WORKS -- README edge examples (p14_misc.py)
- "A userset is not a member of itself": `doc:1#banned vx doc:1` -> True on both backends, as documented.
- "No recursion through and/but not" rewrite (`viewer_base` + `viewer: viewer_base but not blocked`) loads in
  ConnectedStore; blocked at root -> denied at root, allowed at sub (the documented caveat).
- `unparse_schema_ast` and `openfga_json_to_dsl` output parenthesise `but not` and reparse (0.0.5 change holds);
  `openfga_json_to_dsl` also takes a JSON string.
- `excluded_keys(lookup_reverse)` -> `{('user','m','...')}`.

### F16 CONFUSING / DOC GAP -- SetEngine ids go stale after a write; KeyError (p14_misc.py)
`r = se.lookup_reverse(...)`, then a write (remove the ban), then `se.excluded_keys(r)` -> raw `KeyError: 2`.
`result_keys`' docstring says ids are "only valid against THIS instance, and only until the next write", but the
README only says "Translate ids before they leave the process" -- it should say "before the next write". A raw
KeyError is the best case; the docstring says ids are recycled, so a stale id could also translate to a DIFFERENT
key silently (not reproduced here).

### F17 CONFUSING -- one condition, three exception types (p14_misc.py, p10)
Opening a store persisted with a now-refused shape: `ConnectedStore(s,id)` / `open_set_engine` ->
`PersistedSchemaRefused`; `SetEngine(s, id, rewritten_schema)` -> `SchemaMismatch` (message good, cites TK137);
`SetEngine(s, id, same_old_text)` -> `ShapeRefusedSinceTK137` (just the parse refusal, no "persisted by 0.0.4"
context). All ValueErrors, so `except ValueError` catches all three.

### F18 WORKS -- edges of the 0.0.5 owned-id rules (p15_new_features_edges.py)
- SetEngine opened on an unclaimed id, then a ConnectedStore claims it in another session: after the SetEngine's
  next transaction its `add_tuple` raises `UnloggedWriteRefused`; the CS never sees the write. As CHANGELOG says.
- SetEngine with the right text but different `object_wildcard_shapes` on an owned id -> `SchemaMismatch` with a
  specific "its object_wildcard_shapes disagree" message (better than ConnectedStore's, see F5).
- Exclusions through nested groups and `banned from parent` under a `user:*` grant: SetEngine and ConnectedStore
  return identical nodes / markers / exclusions (m1, m2, m3); README recipe "marker minus exclusions" equals `check`
  for every probed user on both.

### F19 DOC GAP -- what `lookup_reverse`'s userset nodes mean for "list the users" (p16_userset_exclusion.py)
`viewer: [user, group#member] but not banned`, group g = {ok, m1}, g#member granted, m1 banned:
both backends return nodes `{group:g#member, user:ok}`, no markers, no exclusions. Correct (users are already
flattened and m1 is omitted), but `group:g#member` is listed too, and a caller who expands it to its members
(natural reading of "usersets on the way included") lists m1, who `check` denies, with no exclusion to subtract.
README should say: to list users, take the user-typed nodes (plus markers minus exclusions); do not expand
userset nodes. Both backends agree, so this is documentation, not a divergence.

## Cleanup (2026-10-15)
`conda.exe env remove -y -n zanzibar-index-pypi-trial` rc 0; `conda env list` and `anaconda3/envs/` show no
`pypi-trial` entry; temp dir `%TEMP%\zanzibar-index-trial` deleted; no python.exe from the trial env running
(remaining python processes belong to other repos' envs). Repo tracked tree untouched (`git status --short` clean).

## Summary
BROKEN: none found.
DOC GAP: F8 (DeltaProcessor not public but required by MissingDeltaProcessor's advice), F16 (ids stale after a
write -> KeyError; README does not say so), F19 (userset nodes in lookup_reverse must not be expanded to list users).
CONFUSING: F3, F4 (dup-add token), F5 (terse reopen mismatch, KeyError on unknown id, StaleRead for bogus token),
F6 (huge reprs, empty IndexCursor repr), F9 (ShapeRefusedSinceTK137 class name, undeclared-userset-type message),
F11 (undeclared-relation write message), F12 (warning cites formal/ & ASK-2, emitted twice), F13 (fanout message
names an unreachable constructor arg; undocumented 'fixpoint'), F17 (three exception types for one condition).
WORKS: F1, F2, F4, F5, F6, F7, F9, F10, F11, F12, F13, F14, F15, F18.
