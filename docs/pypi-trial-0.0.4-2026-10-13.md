# Fresh-user PyPI install trial of zanzibar-index 0.0.4 -- 2026-10-13

> **ACTIVE-PLAN** (`docs/README.md` sec 3). The third run of the post-release install check
> (previous: [`pypi-trial-0.0.3-2026-10-08.md`](pypi-trial-0.0.3-2026-10-08.md)), including
> [`scripts/installed_smoke.py`](../scripts/installed_smoke.py) against the installed wheel
> (68 checks passed, 0 failed). Corrections go at the top, dated. FROZEN once the rows filed
> from it close.
>
> Provenance: everything below the rule is the trial agent's report, transcribed verbatim
> from the gitignored `.scratch/zanzibar-index-trial-0.0.4/report.md` (AGENT, UNVERIFIED
> unless listed here). Re-run FIRST-HAND by the session against `src/` (HEAD `0ec7fed`, the
> 0.0.4 tag), 2026-10-13c, with `PYTHONPATH=src` (confirmed `zanzibar.__file__` in the
> checkout):
>
> * **BROKEN-1 CONFIRMED** (p05): `SetEngine.check(mallory)` False, while
>   `SetEngine.lookup_reverse` returns `markers={('user', '...')}, excluded_node_ids=set()`.
>   `expand` carries `neg=[2]`, which `lookup_reverse` drops. `ConnectedStore.lookup_reverse`
>   fills `excluded_node_ids={4}`. Filed as `TK139`.
> * **BROKEN-2 CONFIRMED** (p12): a second `SetEngine` on a `ConnectedStore` store id has
>   `log_governed=False`, its unlogged remove is accepted, `ConnectedStore.check(alice)` stays
>   True, and `ConnectedStore.remove_tuple` then raises `AdmissionRejected non-existent tuple
>   cannot be removed`. Filed as `TK140`.
> * **BROKEN-3 CONFIRMED** (p09): `ConnectedStore` adopts a store id a standalone `SetEngine`
>   wrote: `check(carol)` False, `remove_tuple` raises `InvariantViolation log row 1 (REMOVE)
>   was rejected by the index`, a fresh `SetEngine` then says True. Filed with BROKEN-2 as
>   `TK140` (same root: nothing ties a store id to one write path).
> * **The undeclared-type item CONFIRMED** (p16): with `define viewer: [usr]` and no
>   `type usr`, both backends admit a `usr:x` write and `check` says True. The PyPI README's
>   "a write naming an undeclared type ... raises AdmissionRejected" holds for a typo in a
>   WRITE, not for a typo in the SCHEMA. Logged on `TK137` (schema leniencies vs OpenFGA).
>
> Routing: `TK139`, `TK140` (BROKEN, so the next patch, 0.0.5); `TK137` (undeclared type in
> a restriction; the generic messages for DSL conditions / modules); the remaining
> CONFUSING / DOC GAP items on `TK123`, as for 0.0.3.

---

# zanzibar-index 0.0.4 -- fresh-user PyPI install trial (2026-10-13)

Env: conda `zanzibar-index-pypi-trial`, python 3.13, `pip install zanzibar-index==0.0.4` only.
Work dir: `$TEMP/zanzibar-index-trial` (outside repo). Probes kept beside this report.
Classes: BROKEN (repro + literal output) / CONFUSING-DOC GAP / WORKS.
Repo reads (only to confirm suspected bugs) are labelled [REPO READ].

## Findings (appended incrementally)

### Setup
- pip pulled in (python 3.13.16): zanzibar-index 0.0.4, SQLAlchemy 2.1.4, sqlmodel 0.0.48, pydantic 2.14.1, pydantic_core 2.50.1, pyroaring 1.2.0, typing_extensions 4.16.0, typing-inspection 0.4.4, annotated-types 0.8.0 (plus env's pip/setuptools/wheel/packaging).
- `zanzibar.__file__` = `...\envs\zanzibar-index-pypi-trial\Lib\site-packages\zanzibar\__init__.py`, `__version__` = 0.0.4 (not the checkout).
- PyPI: requires_python >=3.13; wheel + sdist present; project_urls include Changelog (GitHub CHANGELOG.md). The CHANGELOG is NOT in the long description; it was read from the repo [REPO READ: CHANGELOG.md, to know the claims to check].

### Quickstart (p01_quickstart.py, p01b_quickstart_printed.py)
- WORKS: README quickstart run verbatim, exit 0, assert passes. Printed: check True then False; lookup `LookupResult(node_ids={2, 5}, ...)` resolves to `[('doc','d1','banned'), ('group','eng','member')]`; tokens are ints 1, 2.
- WORKS: re-running the verbatim quickstart against the existing `perms.db` (same store id + schema= again, duplicate add_tuple) exits 0 silently.

### API discovery (p02_help.py, p03_help_setengine.py)
- CONFUSING / DOC GAP: `ConnectedStore.add_tuple`, `.check`, `.remove_tuple`, `.watermark` and `SetEngine.check` have NO docstring (`help()` shows nothing), though they are the main entry points. The argument order is only in a README comment.
- CONFUSING / DOC GAP: public docstrings are full of internal references a user cannot resolve: `ZT-P1-8a`, `TK134`, `TK115`, `TK112`, `H1/H2/H3 hops`, "spec §6.1", "blind-audit W2", `_validate_json_round_trip`. E.g. `ConnectedStore.catch_up`: "The closure fan-out cap is SUSPENDED here (TK112, 2026-10-03b)".
- CONFUSING / DOC GAP: `ConnectedStore` has no `expand`; only the standalone `SetEngine.expand` exists, and it returns a `MemberSet` of instance-local interner ids (`pos=FrozenBitMap([0, 1, 2, 5, 8, 14])`) with no documented helper to resolve them (`result_keys` takes a `LookupResult`, not a `MemberSet`). The README never mentions `expand`.
- CONFUSING: `SetEngine.add_tuple` docstring says it "Raises ``ValueError`` only from validation", but the README says writes raise `AdmissionRejected`. (Checked below whether AdmissionRejected is a ValueError subclass.)

### Main use cases (p04_usecases.py)
- WORKS: folder hierarchy (`viewer from parent`, recursive), nested groups, `user:*` (written as `("...", "user", "*", ...)`), `and`, `but not`: ConnectedStore and a standalone SetEngine agree on all 80 checks (0 disagreements); alice / bob (banned) / carol / mallory / dave answers are all correct by hand.
- WORKS: `lookup("...","user","alice")` identical across backends after resolving ids (Node rows vs `SetEngine.result_keys`).
- WORKS: `remove_tuple` (un-ban) flips `can_read` on both; userset-subject check `group:eng#member reader doc:d1` True on both.
- WORKS: `ConnectedStore.lookup_reverse("can_read","doc","public")` = `markers={('user','...','any')}, excluded_node_ids={<mallory>}` exactly as the README describes.

#### BROKEN-1: `SetEngine.lookup_reverse` drops `but not` exclusions under a `user:*` grant (list-users over-grants; disagrees with its own `check` and with `ConnectedStore`)
Repro (p05_se_lookup_reverse_exclusion.py):
```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar.setengine import SetEngine
from zanzibar.connectedstore import ConnectedStore
SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define banned: [user]
    define viewer: [user:*] but not banned
"""
engine = create_engine("sqlite://"); SQLModel.metadata.create_all(engine)
with Session(engine) as s:
    se = SetEngine(s, "a", SCHEMA)
    se.add_tuple("...", "user", "*", "viewer", "doc", "d")
    se.add_tuple("...", "user", "mallory", "banned", "doc", "d")
    print("se check mallory:", se.check("...", "user", "mallory", "viewer", "doc", "d"))
    print("se lookup_reverse:", se.lookup_reverse("viewer", "doc", "d"))
    print("se expand:", se.expand("viewer", "doc", "d"))
    cs = ConnectedStore(s, "b", schema=SCHEMA)
    cs.add_tuple("...", "user", "*", "viewer", "doc", "d")
    cs.add_tuple("...", "user", "mallory", "banned", "doc", "d")
    print("cs check mallory:", cs.check("...", "user", "mallory", "viewer", "doc", "d"))
    print("cs lookup_reverse:", cs.lookup_reverse("viewer", "doc", "d"))
```
Literal output:
```
se check mallory: False
se lookup_reverse: LookupResult(node_ids=set(), markers={('user', '...')}, excluded_node_ids=set())
se expand: MemberSet(pos=FrozenBitMap([]), stars=frozenset({('user', '...')}), neg=FrozenBitMap([2]))
cs check mallory: False
cs lookup_reverse: LookupResult(node_ids=set(), markers={('user', '...', 'any')}, excluded_node_ids={4})
```
The set engine's answer reads "every user can view doc:d" with no exception, while its own `check` says mallory cannot; `expand` knows (`neg=[2]`) but `lookup_reverse` discards it. The README's "Reading lookup results" contract ("`excluded_node_ids`: subjects a marker would cover but who are refused ... Subtract them from the marker yourself") is filled by ConnectedStore but always empty here, and the `SetEngine.lookup_reverse` docstring does not say exclusions are dropped. A user following the README with the standalone SetEngine (which the README positions as a supported path) would grant mallory.
[REPO READ to confirm: `src/zanzibar/setengine/engine.py::SetEngine.lookup_reverse` copies only `m.pos` and `m.stars`; `tests/test_lookup_oracle.py` docstring item "S3 lookup_reverse is the documented neg-dropping render of expand" -- so the repo treats this as INTENDED, but the "documentation" is a test docstring, not anything a user sees. Forward `SetEngine.lookup` DOES fill `excluded_node_ids` (TK116). Either fill it in reverse too, or say so loudly in the docstring/README.]

- CONFUSING / DOC GAP: marker shape differs by backend. README: markers are `(type, predicate, variant)` triples, e.g. `("user", "...", "any")`. `SetEngine` returns 2-tuples `('user', '...')` (its `LookupResult` docstring says "(type, predicate) shapes"). Code written against the README breaks when switched to SetEngine.

### Persistence / reopen (p06_persist_write.py, p07_persist_reopen.py, p08_reopen_edge.py)
- WORKS: reopen from a SQLite file in a new process with `ConnectedStore(session, "app")` (no schema): answers persist, `watermark()`=4, `lag()`=0.
- WORKS (0.0.4 CHANGELOG claim): reopen with `schema=` reformatted is accepted for: same text, CRLF + extra trailing newlines, no trailing newline, tabs / different indent, whole-line comment added, a comment line between defines, reordered `type` blocks AND reordered `define` lines, redundant parens.
- WORKS: a genuinely different schema (`but not banned` -> `or banned`) is refused: `SchemaMismatch: explicit schema for store 'app' disagrees with its persisted schema; schemas are static (write-once)`.
- CONFUSING: reordering the type list inside one restriction, `[user, group#member]` -> `[group#member, user]`, is semantically identical but raises `SchemaMismatch` (same message). The CHANGELOG says reopening "now compares the parsed schema, not the text"; a user who reorders a restriction list gets "disagrees with its persisted schema" with no hint of which relation differs. (The message also never says which relation/type differs for a real mismatch.)
- CONFUSING: an end-of-line comment is a parse error: `type user  # people` -> `ValueError: malformed type declaration: 'type user  # people'`; `define banned: [user] # bans` -> `ValueError: relation 'banned': unexpected token '#'`. (OpenFGA's DSL also only allows whole-line comments as far as I know, so the refusal itself may be right; the message should say "comments must be on their own line".)
- CONFUSING: opening an unknown store without a schema raises a bare `builtins.KeyError: "store 'nope' has no persisted schema"` (not a library exception type). Also, after that failed constructor the caller's Session is left `in_transaction()==True` holding the SQLite write lock: a second Session's write then fails with `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database is locked` until the first session is closed (p08). A refused WRITE does not do this (p10: `in_transaction` False after `AdmissionRejected`, other sessions write fine) -- only the failed open.
- DOC GAP: a standalone `SetEngine.add_tuple` does not commit; tuples written without `session.commit()` are gone on reopen (p06/p07: "SetEngine reopen (no commit at write)" -> False). Nothing in `help(SetEngine)` says the caller owns the commit (the README says ConnectedStore writes commit, and is silent on SetEngine).
- DOC GAP: a standalone `SetEngine` persists no schema; reopening the same store id with a DIFFERENT schema is silently accepted and evaluates the old tuples under the new schema (p07 "SetEngine reopen with DIFFERENT schema" -> OK).

#### BROKEN-2: a standalone `SetEngine` on a `ConnectedStore`'s store id is not refused; an unlogged remove leaves the grant ALLOWing forever, and `ConnectedStore` can then no longer revoke it
The README presents `SetEngine` and `ConnectedStore` as two public paths over the same tables; nothing stops a user (or a second service) opening `SetEngine(session, "<same id>", schema)`. Its own docstrings promise "Refused with ``UnloggedWriteRefused`` on a log-governed store", but the flag is per-instance (`log_governed: False` on a fresh instance).
Repro (p12_unlogged_remove_fail_open.py):
```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar.setengine import SetEngine
from zanzibar.connectedstore import ConnectedStore
SCHEMA = "model\n  schema 1.1\ntype user\ntype doc\n  relations\n    define viewer: [user]\n"
engine = create_engine("sqlite://"); SQLModel.metadata.create_all(engine)
with Session(engine) as s:
    cs = ConnectedStore(s, "app", schema=SCHEMA)
    cs.add_tuple("...", "user", "alice", "viewer", "doc", "d")
with Session(engine) as s:
    se = SetEngine(s, "app", SCHEMA)
    print("SetEngine.log_governed:", getattr(se, "log_governed", "<no attr>"))
    se.remove_tuple("...", "user", "alice", "viewer", "doc", "d")   # expected: UnloggedWriteRefused
    s.commit()
    print("standalone SetEngine after remove:", se.check("...", "user", "alice", "viewer", "doc", "d"))
with Session(engine) as s:
    cs = ConnectedStore(s, "app")
    print("ConnectedStore check alice:", cs.check("...", "user", "alice", "viewer", "doc", "d"), "lag", cs.lag())
    print("ConnectedStore lookup_reverse:", cs.lookup_reverse("viewer", "doc", "d"))
    print("fresh SetEngine view:", SetEngine(s, "app", SCHEMA).check("...", "user", "alice", "viewer", "doc", "d"))
    try:
        cs.remove_tuple("...", "user", "alice", "viewer", "doc", "d"); print("cs.remove_tuple OK")
    except Exception as ex:
        print("cs.remove_tuple:", type(ex).__name__, str(ex)[:200])
    print("ConnectedStore check alice after its own remove:", cs.check("...", "user", "alice", "viewer", "doc", "d"))
```
Literal output:
```
SetEngine.log_governed: False
standalone SetEngine after remove: False
ConnectedStore check alice: True lag 0
ConnectedStore lookup_reverse: LookupResult(node_ids={1}, markers=set(), excluded_node_ids=set())
fresh SetEngine view: False
cs.remove_tuple: AdmissionRejected non-existent tuple cannot be removed
ConnectedStore check alice after its own remove: True
```
Fail-OPEN and unrecoverable through the public API: alice is ALLOWed by `ConnectedStore.check` with `lag 0`, the two backends inside one store disagree, and the revocation is refused. A standalone `SetEngine.add_tuple` on the same id is likewise ACCEPTED (p11: "SetEngine write on logged store: ACCEPTED").
[REPO READ to confirm: `src/zanzibar/setengine/engine.py::UnloggedWriteRefused` docstring describes exactly this hazard ("silent, permanent, and in the fail-OPEN direction when the bypassed write is a remove"); `SetEngine.__init__` sets `self.log_governed = False` and only `src/zanzibar/connectedstore/source.py` (`TupleSource.__init__`) sets it True, so the guard only covers the evaluator a ConnectedStore owns, not a second SetEngine instance on the same store. The constructor could refuse when a `SchemaRecord`/log exists for the id (the comment there rejects a TupleLog-existence probe because the log can be empty; a SchemaRecord exists from construction).]

#### BROKEN-3: `ConnectedStore` silently adopts a store id that a standalone `SetEngine` already wrote; index and set engine disagree; removing the tuple raises `InvariantViolation` ("corruption")
Repro (p09_cs_adopts_se_store.py):
```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar.setengine import SetEngine
from zanzibar.connectedstore import ConnectedStore
SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
"""
engine = create_engine("sqlite://"); SQLModel.metadata.create_all(engine)
with Session(engine) as s:
    se = SetEngine(s, "app", SCHEMA)
    se.add_tuple("...", "user", "carol", "viewer", "doc", "d")
    s.commit()
with Session(engine) as s:
    cs = ConnectedStore(s, "app", schema=SCHEMA)
    print("check carol:", cs.check("...", "user", "carol", "viewer", "doc", "d"))
    print("lookup_reverse:", cs.lookup_reverse("viewer", "doc", "d"), "lag", cs.lag(), "watermark", cs.watermark())
    try:
        print("remove carol:", cs.remove_tuple("...", "user", "carol", "viewer", "doc", "d"))
    except Exception as ex:
        print("remove carol:", type(ex).__name__, ex)
    try:
        print("re-add carol:", cs.add_tuple("...", "user", "carol", "viewer", "doc", "d"))
    except Exception as ex:
        print("re-add carol:", type(ex).__name__, ex)
    print("check carol after:", cs.check("...", "user", "carol", "viewer", "doc", "d"))
    print("standalone SetEngine view now:", SetEngine(s, "app", SCHEMA).check("...", "user", "carol", "viewer", "doc", "d"))
```
Literal output:
```
check carol: False
lookup_reverse: LookupResult(node_ids=set(), markers=set(), excluded_node_ids=set()) lag 0 watermark 0
remove carol: InvariantViolation log row 1 (REMOVE) was rejected by the index -- the log is admission-validated, so this is corruption or a validity-parity bug: Non-existent edge cannot be removed
re-add carol: 0
check carol after: False
standalone SetEngine view now: True
```
This is the fail-closed twin of BROKEN-2 (pre-existing tuples are invisible; the store is wedged: add is a no-op returning 0, remove is "corruption"). Expected: `ConnectedStore` refuses to claim a store id that already has `RelationTuple` rows but no log/schema, pointing at `build_index` (which exists in `__all__` as the "offline bootstrap"). `paranoia="residue"` and `paranoia="full"` both open it and write to it without complaint (p11).

### Malformed OpenFGA JSON (p13_bad_json.py, p14_json_to_store.py) -- 0.0.4 CHANGELOG claims
- WORKS: a valid model with `"metadata": null` on a type parses (`[good (with user metadata: null)] OK`); `relations: null`, `metadata.relations: null` and `directly_related_user_types: null` read as absent.
- WORKS: every malformed shape tried raises `ValueError` naming the field, no bare AttributeError/TypeError/KeyError: model null/list/"null" ("the model must be an object, got null"/"got an array"); `type_definitions` {"a":1}/"abc"/5 ("type_definitions must be an array, got an object/a string/a number"); `type_definitions[0] must be an object, got a number`; missing `type` ("type_definitions[1] has no 'type'"); `'type' must be a string, got a number`; computedUserset with no relation; union with no child / child an object; difference with no subtract; tupleToUserset with no tupleset; `metadata: []` ("type group: metadata must be an object, got an array"); `relations: []`; drut entry a string; empty rewrite `{}`; unknown operator; duplicate JSON keys in text; schema_version 1.0 / 1.2 / missing; conditions; conditional type restriction. Invalid JSON text raises `json.JSONDecodeError` (a ValueError subclass).
- WORKS: JSON -> `openfga_json_to_dsl` -> `ConnectedStore` end to end (check True, no warnings).
- CONFUSING: `type_definitions: {}` (empty object) says "the model declares no type (no type_definitions)" rather than "must be an array, got an object" (a non-empty object gets the right message).
- CONFUSING: passing the OpenFGA API's ReadAuthorizationModel response shape `{"authorization_model": {...}}` gives `ValueError: unsupported OpenFGA schema_version None (need '1.1')` -- a hint "pass the inner authorization_model" would save a user a detour.
- CONFUSING: `openfga_json_to_dsl` output drops the `model / schema 1.1` header and every type without relations (`type user` vanishes), so the "canonical DSL" is not valid OpenFGA DSL any more (OpenFGA requires the header and refuses `[user]` with no `type user`). It works here only because of the undeclared-type leniency below.
- NOTE (not a finding against the README, which only speaks of the DSL): JSON with `metadata.module` (a modular model as the API returns it) is accepted.

### Malformed / unsupported DSL (p15_bad_dsl.py, p16_undeclared_type.py) -- parse / SetEngine / ConnectedStore all agree in every case
- WORKS: empty / header-only / no-define schemas refused with a clear reason; missing colon, duplicate type, duplicate relation, `.` in a relation name, unbalanced parens, `or`/`and` mixed without parens ("ambiguous"), undeclared relation reference ("doc#viewer: references undeclared relation doc#editor"), computed cycle ("doc#a -> doc#b -> doc#a").
- WORKS (README claim "a `from` tupleset must be a direct relation"): computed tupleset, boolean tupleset and userset-restricted tupleset are all refused with WHY + INSTEAD text, e.g. "a tupleset must be direct (...) Store the links on a direct relation (parent_link: [...]) and use that in the "from" (OpenFGA rule)".
- CONFUSING / DOC GAP: README: "Conditions (`with`) and modules are not supported. Refused shapes come with an explanation of what to write instead". In the DSL, a condition gives `ValueError: invalid subject type in restriction 'user with non_expired'`, `module core` gives `unrecognized schema line: 'module core'`, `extend type doc` gives `unrecognized schema line: 'extend type doc'`. They are refused (good) but the messages never say "conditions/modules are not supported" (the JSON path does: "OpenFGA conditions are not supported").
- CONFUSING: DSL `schema 1.0` is accepted silently (JSON `schema_version "1.0"` is refused "need '1.1'"); a missing `model` header is accepted too.
- CONFUSING / DOC GAP: a restriction naming an UNDECLARED type is accepted by every parser, and writes using that type are then admitted: schema `type user / type doc / define viewer: [usr]` -> `cs.add_tuple("...","usr","x","viewer","doc","d")` returns 1 and `check` True; the intended `user` write is refused "matches no declared type restriction". This contradicts the README ("A write naming an undeclared type or relation ... raises `AdmissionRejected`"; "a subset of the OpenFGA DSL" -- OpenFGA refuses `[usr]` with no `type usr`), and turns a typo into a silent new type. Both backends agree, so it is not an equivalence bug. [REPO READ: `docs/p10-scope-audit-2026-09-27.md` item "11, undeclared type ... SOUND stands" -- deliberate leniency, judged sound; the README sentence is what is off.]

### Recursion through `but not`; extension warnings (p17_cycles_warnings.py, p18_star_tupleset_cs.py, p18b_default_filter.py)
- WORKS (0.0.4 CHANGELOG claim): `define viewer: ([user] or viewer from parent) but not blocked` on folder, with doc#viewer and doc#editor depending on it, raises `CyclicDerivedDependency` (a ValueError) from `parse_openfga_schema` and `ConnectedStore`; the message names ONLY `[('folder', 'viewer')]`, cites no internal spec, gives the rewrite and says how it differs. `SetEngine` accepts the schema, as the README says.
- WORKS: the README's rewrite (`viewer_base` + `viewer: viewer_base but not blocked`) is served by both backends, and behaves as the README warns: blocked at root -> False at root, True at sub.
- WORKS (README claim): `UnprovenExtensionWarning` fires for wildcard usersets `[group:*#member]`, wildcard tuplesets `parent: [folder, folder:*]` and object wildcards (`object_wildcard_shapes`), from `parse_openfga_schema`, `SetEngine` and `ConnectedStore`; a plain `[user:*]` is silent. The wildcard tupleset is served and both backends agree (u via `folder:*` -> True, v -> False).
- CONFUSING: the warning text ends "See task ASK-2." and mentions "formal/, W4Fragment" -- an internal task id and repo path a PyPI user cannot look up. Its stacklevel points into the library (`...\site-packages\zanzibar\schema\compiler.py:622: UnprovenExtensionWarning ... schema_info = derive_schema_info(ast, object_wildcard_shapes)`), not at the user's call. `ConnectedStore` emits it twice (three times for a star-tupleset schema) per construction under `simplefilter("always")`.
- Cosmetic: the cycle list prints as a Python repr, `[('folder', 'viewer')]`, rather than `folder#viewer` as other messages do.

### Identifiers, lenient reads, data cycles (p19_identifiers_reads.py)
- WORKS: `AdmissionRejected` is one class (graphindex and schema re-export the same object) and subclasses `ValueError` (so the SetEngine docstring's "raises ValueError" is technically true).
- WORKS: writes refuse space, non-ASCII, `:`, `#`, empty, 257 chars, `None`, int, empty/None subject predicate, undeclared relation, undeclared subject type, `doc:*` object without a declared shape, `group:*` where not restricted, bad userset predicate -- identically on ConnectedStore and SetEngine, with the charset in the message. `a.b+c@x.com` and 256 chars accepted.
- WORKS (README claim "Tuple data must be acyclic"): group in itself, folder its own parent, 2-cycles of groups and of folders all refused with `AdmissionRejected ... would create a cycle in the userset membership topology` on both backends.
- WORKS (README claim "Reads are lenient"): typo relation, undeclared type, bad chars, `None` name all return `False` on both backends, no error.
- CONFUSING: writing an undeclared relation says "matches no declared type restriction for doc#editor" instead of "doc has no relation editor".
- DOC GAP: a duplicate `ConnectedStore.add_tuple` returns the current head log id (4 here) rather than a new id or a "no-op" signal (`SetEngine.add_tuple` returns False); there is no docstring saying so.

### Knobs (p20_knobs.py, p21_fanout_atomic.py)
- WORKS: `paranoia=` accepts None/False/True/"residue"/"full"/"fixpoint"/"off"; a bad level is refused loudly: `ValueError: bad paranoia level 'bogus'; expected one of ('off', 'residue', 'full', 'fixpoint') (or a bool / ['0', '1', 'false', 'no', 'on', 'true', 'yes'])`. `ZANZIBAR_PARANOIA=residue` runs clean; `ZANZIBAR_PARANOIA=bogus` raises the same ValueError at construction (explicit `paranoia=False` overrides the env var). Not observable from outside whether residue mode is actually on (no public attribute / log line) -- accepted on trust.
- Cosmetic: `paranoia=1` (int) is refused while the string `"1"` is accepted.
- DOC GAP: README/`help(ConnectedStore)` list `"residue"` only; `"full"` and `"fixpoint"` exist (seen only in the error message) with no description of cost or meaning.
- WORKS (README claim): `ZANZIBAR_MAX_CLOSURE_FANOUT=12` refuses a 43-row nested-group write with `ClosureFanoutExceeded` (message gives rows, limit, store); watermark unchanged (13 -> 13), lag 0, and the write is absent from ConnectedStore, from a reopened ConnectedStore and from a fresh SetEngine over the same store ("lands in neither backend"). Later small writes and removals proceed. `=0` disables (the same write succeeds); `=abc` -> `ValueError: ZANZIBAR_MAX_CLOSURE_FANOUT='abc' is not an integer (...)`; `=-1` -> `ValueError: max_closure_fanout must be >= 0 (0 disables the cap), got -1`.
- CONFUSING: the `ClosureFanoutExceeded` message says "Raise it with ReachabilityIndex(max_closure_fanout=...) or ZANZIBAR_MAX_CLOSURE_FANOUT"; a ConnectedStore user has no `max_closure_fanout` parameter (not in `ConnectedStore.__init__`), so only the env var applies to them.
- CONFUSING: the env var is read at construction time, and a bad value surfaces as a traceback from `zanzibar/graphindex/core.py::resolve_max_closure_fanout` deep inside `ConnectedStore(...)` -- fine, but it is the first time a user hears of `ReachabilityIndex`.
- WORKS: `sync=False`: token returned, `lag()`=1, untokened check stale (False), tokened check True (set-engine fallback), tokened lookup raises `LookupNotFresh` with an explanation, a future token raises `StaleRead ... call refresh()`, `catch_up()` applies 1 and lag -> 0. After a remove, untokened check/lookup still show the grant (documented "bounded-stale"), tokened check says False.

### Smoke script (repo scripts/installed_smoke.py copied to the temp dir, run with the trial env)
- WORKS: `installed_smoke.py --version 0.0.4` exit 0: "zanzibar 0.0.4 from C:\Users\user\anaconda3\envs\zanzibar-index-pypi-trial\Lib\site-packages\zanzibar\__init__.py" (installed wheel, not the checkout); README quickstart; differential grids main + tk126-second-form (120 ops each, all backends agree); hand-written expectations; bad input; "68 checks passed, 0 failed, 28.3s". Zero FAIL lines.

### Misc (p22_reverse_usersets_tables.py)
- WORKS: `ConnectedStore.lookup_reverse("viewer","doc","d1")` enumerates transitive users as well as the userset: before ban `[group:eng#member, user:alice, user:bob]`, after banning alice `[group:eng#member, user:bob]`.
- WORKS (README "Tables" claim): declaring a user model with `__tablename__ = "zanzibar_store"` raises `sqlalchemy.exc.InvalidRequestError: Table 'zanzibar_store' is already defined for this MetaData instance.` (SQLAlchemy's own text then suggests `extend_existing=True`, which is exactly what one should not do; the README could say so.)

## Summary
- BROKEN: 3 (BROKEN-1 SetEngine.lookup_reverse drops `but not` exclusions under `user:*`; BROKEN-2 a standalone SetEngine on a ConnectedStore's store id is not refused, so an unlogged remove fails OPEN and cannot be revoked; BROKEN-3 ConnectedStore silently adopts a SetEngine-written store id: the backends diverge and remove raises InvariantViolation).
- CONFUSING / DOC GAP / cosmetic: 24 bullets above.
- WORKS: 27 bullets above, including every 0.0.4 CHANGELOG claim tested (malformed JSON -> ValueError naming the field; `metadata: null`; CyclicDerivedDependency names only the cycle; reformatted-schema reopen) and the README's OpenFGA statements (with the undeclared-type and condition/module-message caveats).
- Smoke script: 68 passed, 0 failed (28.3s), against the installed wheel.
- Cleanup: env `zanzibar-index-pypi-trial` removed (absent from `conda env list` and `envs/`); `$TEMP/zanzibar-index-trial` sent to the Recycle Bin; no trial python processes left. Probes + this report kept here.
