# Changelog

All notable changes to the `zanzibar-index` distribution (import package `zanzibar`).
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/), with the usual 0.x caveat that any minor release
may break the API. The newest version heading must equal `zanzibar.__version__`
(`tests/test_tk122_release_metadata.py`).

## [0.1.0] - 2026-10-26

The public API break of `TK123`: the first-hour review of 0.0.x, accepted in full. There
are no compatibility aliases. What breaks a 0.0.5 caller, in short:

- `zanzibar.connectedstore` is now `zanzibar.store`, `ConnectedStore` is now `Store`, and
  the graph index's `Store` model is now `IndexStore`.
- Keyword names are `subject_type` / `subject_name` / `object_type` / `object_name` (not
  `s_type` / `s_name` / `o_type` / `o_name`).
- The set engine's result type is `SetLookupResult`.
- `build_index` / `rebuild_index` take `index_store_id` by keyword only.
- The Python `Ellipsis` is refused as a subject predicate.
- A `Store` refuses a `Session` with pending ORM changes.
- `__all__` lists only the public surface.
- `ShapeRefusedSinceTK137` is now `ShapeNoLongerAccepted`.
- The parsers raise `SchemaError` (still a `ValueError`).
- `at_least` must be `None` or an `int >= 0`; `True` and negative values are refused.
- Opening a `Store` on a database without the `zanzibar_*` tables raises
  `TablesNotCreated` (a `RuntimeError`) instead of the driver's own SQLAlchemy error.
- A `Store` refuses a SQLite file created by 0.0.x (`TablesOutdated`): create the tables
  in a new file (TK154).
- `SetEngine` raises `PersistedSchemaRefused` for a store whose stored schema this version
  refuses, as every other entry point does (it raised `SchemaMismatch` or
  `ShapeNoLongerAccepted`); import it from `zanzibar` (TK153, TK164).
- A write to an undeclared relation or type is refused with a message that starts
  `... names an undeclared relation doc#vewer` (TK153).
- An `object_wildcard_shapes` entry that names no declared relation is refused
  (`ShapeNoLongerAccepted`); a store saved by 0.0.5 with one no longer opens
  (`PersistedSchemaRefused`). An entry naming a compiled leaf such as `('doc', 'view.0')`
  raised `UnsupportedByGraphIndex` and now raises `ShapeNoLongerAccepted`, which is not an
  `UnsupportedByGraphIndex` (TK147).
- Many exception and warning messages are reworded (see Changed); code that matches on
  message text may need updating. Exception classes and their builtin bases are unchanged
  except where listed here.
- **Answers change for userset subjects** (TK144): a userset such as `doc:1#banned` is now
  a member of itself, as in OpenFGA. One previously ALLOWED check is now DENIED (a userset
  inside its own `but not`); see Changed. `lookup_reverse` results now include the
  object's own userset.
- **A freshness token from another store is refused** (TK166): every tokened read raises
  the new `ForeignToken` (a `StaleRead`) where a token at or below the store's cursor was
  accepted without error.
- **Exceptions are exported from `zanzibar` only** (TK164): no subpackage `__all__` lists
  an exception or warning any more. Write `from zanzibar import StaleRead`, not
  `from zanzibar.store import StaleRead`.
- `UnsupportedByGraphIndex` and `DoublyBridgedShapeError` are now `ValueError`s (TK164), so
  an `except ValueError` that let them through now catches them.

Each is detailed below, under Changed or Added.

### Changed
- **Breaking: exceptions have one public home, the top-level package** (TK164). Each
  subpackage used to list its own subset of the exceptions in `__all__`, with no rule
  (`zanzibar.graphindex` listed `AdmissionRejected` but not the `ClosureFanoutExceeded` it
  raises; `zanzibar.setengine` listed `StaleLookupIds` but not `SchemaError`). Now no
  subpackage `__all__` (`zanzibar.schema`, `zanzibar.store`, `zanzibar.graphindex`,
  `zanzibar.setengine`) lists any exception or warning, and every one is exported from
  `zanzibar`, as before. Import them from there: `from zanzibar import StaleRead,
  SchemaError`. This breaks `from zanzibar.<subpackage> import *` code that relied on an
  exception arriving that way, and any import of an exception from a subpackage is no
  longer part of the API. Such imports still resolve in 0.1.0 (they name the same class),
  but they are undocumented and may be removed without notice.
- **Behaviour change: `UnsupportedByGraphIndex` (and its subclass
  `DoublyBridgedShapeError`) is a `ValueError`** (TK164). They were the only two
  `ZanzibarError` subclasses with no builtin base, so `except ValueError` around
  `parse_openfga_schema`, `Store(...)` or `compile_ruleset` let a refused schema through.
  Every schema refusal is now a `ValueError`. Additive for `except UnsupportedByGraphIndex`
  and `except ZanzibarError`; only code that relied on `except ValueError` NOT catching them
  sees a change. They are still not `SchemaError`s: the schema text parsed, and compiling
  it for the graph index refused it.
- **Behaviour change: a freshness token issued by another store is refused on every
  tokened read** (TK166). A token is a log id, numbered across every store in the
  database, and the freshness tests only compared ids, so an `at_least=` token returned by
  another store's write was ACCEPTED silently by `check`, `lookup`, `lookup_reverse`,
  `expand` and `TupleSource.check` whenever it was at or below this store's cursor (on an
  async store such a read could still allow a revoked grant), and REFUSED with
  `refresh()` / `catch_up()`-and-retry advice that cannot help when it was above it. Each
  tokened read now looks up the token's log row once by primary key and raises
  `ForeignToken` when another store wrote it, above or below the cursor. The message leads
  with the cause (`Token 3 was returned by a write to store 'b', not 'a': tokens are
  per-store, ...`) and gives no retry advice. `ForeignToken` subclasses `StaleRead`, so
  `except StaleRead` still catches it; it is not a `LookupNotFresh`, also on `lookup` /
  `lookup_reverse`, because it is not retryable. A token that names no visible log row
  keeps its previous behaviour.
- **Breaking: a userset is a member of itself, as in OpenFGA** (TK144, TK138 landing 2). A
  concrete userset subject `T:o#r` is now a member of its own declared relation `r` on
  `T:o`, outside the relation's definition, and of everything built on that: a computed
  relation (`can_view: viewer` makes `doc:1#viewer` a `can_view` of `doc:1`), a `but not`
  base, a TTU target, and other objects through a stored userset (with
  `member: [user] or admin` and `group:1#member viewer doc:1`, `group:1#admin` is a viewer
  of `doc:1`). Measured against OpenFGA v1.22.0; the oracle, both backends and the Lean
  models apply it together.
  - **ALLOW to DENY:** with `define vx: [user, doc#banned] but not banned` and the tuple
    `doc:1#banned vx doc:1`, `check("doc:1#banned", "vx", "doc:1")` was `True` and is now
    `False` (the userset is in its own subtrahend `banned`). Code that relied on the old
    answer loses that access.
  - **DENY to ALLOW:** with `define vy: [user, doc#editor] and editor` and
    `doc:1#editor vy doc:1`, `check("doc:1#editor", "vy", "doc:1")` was `False` and is now
    `True`; on an empty store `check("doc:1#viewer", "viewer", "doc:1")` is now `True`.
  - **Lookups list such usersets.** `lookup` of a userset includes its own object's
    relations it is a member of, and `lookup_reverse(r, T:o)` includes `T:o#r` itself (and
    the usersets of `T:o` that `r` is built on). A userset with no stored tuple has no
    node or interned id, so it arrives in the new `implicit_keys` field; read results
    through `result_keys` / `excluded_keys`, which include it. Callers that list USERS by
    taking keys of type `user` are unaffected.
  - **A userset `lookup` is slow on large stores with `and` / `but not`** (TK162). To list
    those answers, `Store.lookup` for a userset subject runs a `check` against every object
    of each `and` / `but not` relation's type. It was measured at about 2 s at 10,000
    tuples and 21 to 29 s at 100,000 (2026-10-26, SQLite). Lookups for plain users,
    `lookup_reverse`, and schemas without `and` / `but not` are not affected. See the
    user docs, "Limits and costs".
  - Unchanged: plain users and `user:*` answers (the rule adds only the userset itself,
    never its members), userset-star subjects such as `doc:*#viewer`, an undeclared
    relation (still `False`, where OpenFGA errors), and the write refusal of the exact
    self tuple `doc:1#viewer viewer doc:1` (refused as a cycle; OpenFGA refuses it as
    implicit). One OpenFGA difference remains, on purpose: a `from` whose parent type does
    not declare the target relation (`parent: [folder, team]`, `x: viewer from parent`,
    `team` with no relations) still answers `True` for `team:1#viewer` here, where OpenFGA
    returns a validation error. The version stays 0.0.5 until the 0.1.0 release, which
    carries this break.
- **Breaking: the composed-system package and its class are renamed** (TK123). There are
  no compatibility aliases; the old names no longer import.
  - `zanzibar.connectedstore` is now `zanzibar.store`, and `ConnectedStore` is now `Store`:
    write `from zanzibar.store import Store`. Every other name in the package keeps its
    name (`TupleSource`, `build_index`, `save_schema`, ...).
  - The class's own module is `zanzibar.store._store` (it was `connectedstore/store.py`),
    so a traceback never shows `zanzibar.store.store.Store`. Import from `zanzibar.store`.
  - The graph index's bookkeeping model `zanzibar.graphindex.Store` is now `IndexStore`, so
    it no longer shares a name with the user-facing class. Its table is still
    `zanzibar_store`, so databases written by 0.0.x open unchanged.
- **Breaking: documented keyword names** (TK123). The tuple parameters are now
  `subject_predicate`, `subject_type`, `subject_name`, `relation`, `object_type`,
  `object_name` on `add_tuple` / `remove_tuple` / `check` / `lookup` / `lookup_reverse` of
  `Store`, `SetEngine` and `WildcardIndex` (and `TupleSource.add` / `remove` / `check`).
  Positional calls are unchanged; keyword calls using the old `s_type` / `s_name` / `o_type`
  / `o_name` must be renamed.
- **Breaking: the set engine's result type is `SetLookupResult`** (TK123), so it is never
  confused with the graph index's `zanzibar.LookupResult` that `Store.lookup` returns. It is
  now a dataclass (keyword constructor, `==`) with the same three fields;
  `zanzibar.setengine.LookupResult` no longer exists.
- **Breaking: `build_index` / `rebuild_index` take `index_store_id` by keyword only**
  (TK123): write `build_index(session, "src", index_store_id="idx")`.
- **Breaking: the subject predicate `...` (Python `Ellipsis`) is refused** at the public
  entries of `Store`, `TupleSource` and `SetEngine` (TK123): the bare predicate is the
  string `"..."`. Writes raise `AdmissionRejected`, reads raise `TypeError`. (`None` on a
  read still means bare.)
- **Breaking: `Store` refuses a `Session` with pending ORM changes** (TK123), at open, on
  every write and in `refresh()`, with a `ValueError`. It commits and rolls back its own
  transactions, so a caller's pending rows used to be committed with a write or silently
  discarded by a rollback. Commit or roll back your own changes first.
- **Breaking: each subpackage's `__all__` lists only the public surface** (TK123). Internal
  helpers are gone from it (for example the compiler's plan nodes and `compute_taint` in
  `zanzibar.schema`; `SetEngineBackend`, `Interner`, `NodeSets`, `DEFAULT_SETOPS` and
  `ALL_SETOPS` in `zanzibar.setengine`; `PermissionDelta` in `zanzibar.graphindex`;
  `advance_index`, `ensure_cursor`, `log_rows` and the other log helpers in `zanzibar.store`).
  They still import by name; only `from ... import *` and the documented surface change.
- **Breaking: `ShapeRefusedSinceTK137` is renamed `ShapeNoLongerAccepted`** (TK123), now a
  `SchemaError` subclass and exported from the top level. It is the parser's refusal of a
  shape that 0.0.4 and earlier accepted.
- **Breaking: the schema parsers raise `SchemaError`** instead of a bare `ValueError` (TK123). Code that
  checks `type(e) is ValueError` must change; `except ValueError` still works.
- **Breaking: `at_least` is validated** (TK123): it must be `None` or an `int >= 0` (`TypeError` /
  `ValueError` otherwise; `True` is refused). When a token cannot be satisfied, the error
  now says if the token was issued by ANOTHER store, or if it is past the newest log id the
  session can see (not issued yet, or committed after this session's snapshot).
- **Reopening with reordered restrictions is accepted** (TK123): `[user, group#member]` and
  `[group#member, user]` are the same schema. A `SchemaMismatch` now names the first
  differing `type#relation` (or the differing `object_wildcard_shapes`).
- **`save_schema` of the schema a store already has is a no-op** (TK123): it returns the
  stored row, as reopening a `Store` with that schema does. A different schema raises
  `SchemaMismatch` (still a `ValueError`) naming the first difference, instead of a plain
  `ValueError`.
- **`build_index` returns a named tuple** (TK123): `BuildReport` has the fields `cursor`,
  `widx`, `ruleset` (it still unpacks as `cursor, widx, ruleset = ...` and keeps
  `.constructor`), and a short `repr`.
- **`UnprovenExtensionWarning` is raised once per `Store` and points at your code**
  (TK123): opening a `Store` on a schema with a wildcard extension used to warn twice and
  attribute the warning to a library line; it now warns once, at the line that called
  `Store(...)`, `parse_openfga_schema(...)` or `SetEngine(...)`. A `SetEngine` handed a
  compiled `RuleSet` no longer warns again. The message says how to silence it
  (`warnings.filterwarnings('ignore', category=zanzibar.UnprovenExtensionWarning)`) and still
  starts with `UNPROVEN:`.
- **A stalled index names its row** (TK123): the exception from `catch_up()` carries
  `failing_log_row` (log id and the tuple, e.g. `ADD group:b#member member group:c`) and a
  note, `Store.stall_error` reads `applied through N; failing row M (...)`, and a
  `PathCountExceeded` names its nodes as `type:name#relation` instead of row ids.
- **Clearer admission refusals** (TK123): a tuple no restriction admits now says why, the
  same way on both backends: the type is not declared (with a did-you-mean), the type has
  no such relation (did-you-mean), the relation is computed only, or which subjects it
  admits. A `type:name` passed as a type or name field gets a hint to split it or use the
  three-argument form. Removing a tuple that is not stored names it:
  `non-existent tuple cannot be removed: user:alice viewer doc:d1 is not stored`.
- **`ClosureFanoutExceeded` names the knob you have** (TK123): the message reads "this
  write would add N permission-closure rows" and says to raise the limit with the
  `ZANZIBAR_MAX_CLOSURE_FANOUT` environment variable (`0` disables it), instead of
  pointing at a `ReachabilityIndex` argument a `Store` user cannot reach.
- **Error messages and `help()` text no longer cite repository-internal references**
  (TK123): task ids, review-finding ids, spec section numbers and `docs/` / `tests/` /
  `formal/` paths, none of which ship in the wheel, are gone from exception and warning
  messages and from public docstrings. The SQLite write-lock refusal (`WriteLockUnsafe`)
  now spells out the two-listener SQLAlchemy recipe instead of naming a test file.
  `LookupNotFresh` no longer tells you to "wait for the async worker" (none ships; run
  `catch_up()`), and `compile_ruleset(enable_boolean=False)` on a boolean schema says to
  use the default `enable_boolean=True`. Internal-corruption reports (`InvariantViolation`)
  keep their invariant ids.
- `SetOps` prints as `SetOps('roaring')` instead of a dataclass repr full of lambda
  addresses (TK123).
- **Breaking: one exception type for a store whose STORED schema this version refuses**
  (TK153). `SetEngine(session, id, ...)` on such a store now raises
  `PersistedSchemaRefused`, as `Store(...)`, `open_set_engine`, `save_schema`,
  `ensure_schema` and `build_index` already did. It used to raise `SchemaMismatch` when
  given a rewritten schema, and `ShapeNoLongerAccepted` (the bare parser refusal) when
  given the stored text or no schema. The class moved to `zanzibar.schema.errors`; import
  it from `zanzibar` (TK164: no subpackage `__all__` lists an exception). A schema text
  you pass for a store with no stored schema still raises `ShapeNoLongerAccepted`; its
  `.instead` (the meaning-preserving rewrite) is now documented.
- **Clearer refusals** (TK153): a write to a relation the schema does not declare (or on
  an undeclared type) now reads `tuple ... names an undeclared relation doc#vewer: type
  'doc' declares no relation 'vewer'; did you mean 'viewer'?` instead of starting with
  "matches no declared type restriction"; a restriction `[team#member]` with no
  `type team` says the TYPE is undeclared (and a wildcard restriction keeps its `:*`,
  `[team:*#member]`); a write on a declared type that has no relations says `type 'folder'
  declares no relations` instead of calling the type undeclared; `MissingDeltaProcessor`
  says where `DeltaProcessor` imports from.
- **Short reprs** (TK153): a `RuleSet` prints as `RuleSet(12 rules and filters, 1 boolean
  relations)`, so `save_schema`'s return value no longer prints every compiled rule, and
  `SchemaRecord` / `IndexCursor` name their fields even after a commit expired them (they
  printed as `SchemaRecord()`).
- **`help()` text is ASCII** (TK153): public docstrings no longer carry characters such as
  the section sign or circled digits, which raised `UnicodeEncodeError` when printed to a redirected
  Windows console.
- The `ClosureFanoutExceeded` docstring no longer says the cap cannot bite at the 100,000
  default: a grant or ban over a group of more than 100,000 members is refused (TK153).
- **Breaking: `object_wildcard_shapes` must name declared relations** (TK147). An entry
  naming an undeclared type (`('nosuch', 'viewer')`), an undeclared relation
  (`('doc', 'nosuchrel')`, or a compiled leaf such as `('doc', 'view.0')`), or that is not
  a `(type, relation)` pair of strings, raises `ShapeNoLongerAccepted` from
  `parse_openfga_schema`, `derive_schema_info`, `compile_ruleset` (whose `SchemaInfo` may be
  built by hand), `SetEngine`, `Store`, `save_schema` and `ensure_schema`. 0.0.5 accepted an
  undeclared type or relation, and it did nothing: no object-wildcard write was admitted
  for it. 0.0.5 refused a compiled leaf with `UnsupportedByGraphIndex` from
  `parse_openfga_schema` and `Store`, while a `SetEngine` on its own accepted it; code that
  caught `UnsupportedByGraphIndex` for it must catch `ShapeNoLongerAccepted`. A store
  saved by 0.0.5 with such an entry raises `PersistedSchemaRefused` on every open ("saved by
  zanzibar-index 0.0.5 or earlier"); its `.instead` says to drop the entry, which changes no
  answer. Schemas are write-once, so create a new store id with the entry dropped and write
  the tuples again. `ShapeNoLongerAccepted` gains `accepted_through` and `refused_since`
  (the versions `PersistedSchemaRefused` quotes).
- **A sync write blocked by someone else's pending row now says so** (TK167). A
  `sync=True` write applies the pending backlog first, so one row a `sync=False` instance
  logged and the index cannot apply refuses every sync write on that store id, removals
  of that very tuple included. The `PathCountExceeded` / `ClosureFanoutExceeded` message
  used to describe only that row's closure, which read as "your write was too big". It
  now starts "this write (log row N) was rolled back because the index backlog of store
  ... holds an earlier log row it cannot apply", names the row, and gives the recovery: a
  `sync=False` removal then `zanzibar.store.rebuild_index` for a path-count overflow,
  `catch_up()` for a fan-out-capped row. A duplicate add (which appends no log row)
  starts "this write (a duplicate add, which appends no log row)" instead. Same exception
  type and `failing_log_row`; a refusal of your own row reads as before.

### Added
- **The types in public signatures are public** (TK164). `zanzibar.schema` now exports
  `SchemaInfo` (on `RuleSet.schema_info`, taken by `WildcardIndex`), `Entity` and
  `RelationalTriple` (what `RuleSet.apply` takes), and `CompiledBooleans` (on
  `RuleSet.compiled`, taken by `DeltaProcessor`; an opaque value to pass through, whose
  fields are not API), each with a docstring. `typing.get_type_hints(RuleSet)` now resolves;
  it raised `NameError: name 'CompiledBooleans' is not defined`.
- **`zanzibar.store.open_set_engine` is public** (TK164): it opens the set engine on a
  store with the schema persisted in the database. The `SchemaMismatch` that
  `SetEngine(session, store_id, schema)` raises already named it as the fix.
- **`Store.expand`: Zanzibar Expand on the store** (TK155). `store.expand("viewer",
  "doc:d1")` (or `"viewer", "doc", "d1"`) returns an `ExpandResult` (exported as
  `zanzibar.ExpandResult`) of `(type, name, predicate)` keys: `keys` (members listed one
  by one), `markers` (`(type, predicate)` shapes granted through a wildcard) and
  `excluded_keys` (subjects a marker covers that are not members). Test one subject with
  `key in result`; `keys` alone is not the member list, because a member a marker covers
  is not repeated there. Served by the set engine, so a lagging or stalled index does not
  affect it; it first reads every write this session can see, and `at_least` raises
  `StaleRead` when the token is not in this session's snapshot. Before this, Expand meant
  `SetEngine.expand`, which returns instance-local bitmap ids.
- **A type and relation filter on lookups** (TK156). `store.lookup("user:alice",
  object_type="doc", relation="viewer")` keeps only the doc viewers alice reaches, and
  `store.lookup_reverse("viewer", "doc:d1", subject_type="user",
  subject_predicate="...")` keeps only the users (`"..."` is a bare subject; a relation
  name keeps usersets). Either part may be given alone. Markers and their exclusions are
  filtered together, so a marker keeps its exclusions. A name the schema does not declare
  matches nothing (an empty result, as `check` answers False); a filter that is not a
  `str` raises `TypeError`. The backends filter the same way through the new
  `WildcardIndex.filter_result(result, entity_type=None, predicate=None)` and
  `SetEngine.filter_result(...)`, which filter a result the lookup already computed.
- **`Store.adopt`: adopt an existing tuple store in one call** (TK157). `store, report =
  Store.adopt(session, "app", schema=SCHEMA)` saves the schema (leave `schema` out when the
  store already has one), builds the index from the stored tuples with `build_index`, and
  opens the `Store`; `report` is the `BuildReport`. It replaces the four-step recipe
  (`save_schema`, commit, `build_index`, `Store(...)`) that `UnloggedTuplesPresent` names,
  and the schema and index commit together: a refused adopt saves nothing. An isolation
  level other than READ COMMITTED (`UnsafeIsolationLevel`) and a 0.0.x SQLite file
  (`TablesOutdated`) are refused before anything is built, which a bare `build_index`
  does not check, and so are a bad `paranoia` or `ops` argument. An id that already has
  an index is `IndexExists`, whose message says to open it with `Store(session, id)`. `save_schema` and
  `build_index` stay public.
- **The key channel of a lookup result** (TK144): `LookupResult.implicit_keys` /
  `implicit_excluded_keys` and `SetLookupResult.implicit_keys` / `implicit_excluded_keys`,
  `(type, name, predicate)` keys for answers and exclusions that have no node or interned
  id (a userset that is a member of itself before any tuple names it).
  `Store.result_keys` / `excluded_keys` and `SetEngine.result_keys` / `excluded_keys`
  include them. `MemberSet` gains the same channel (`ipos` / `ineg`, `contains_key`) for
  `SetEngine.expand`.
- `SchemaInfo.self_seeds` (TK144): the compile-time table the graph index reads the
  self-relation through (filled by `compile_ruleset`; a hand-built `SchemaInfo` has none
  and reads as before).
- `compile_ruleset(..., declared_types=...)` (TK153): the schema text's `type` lines, used
  only to word an admission refusal; `parse_openfga_schema` passes them for you.
- `derive_schema_info(..., declared_types=...)` (TK147): the same facts, used only to word
  an `object_wildcard_shapes` refusal (a type with no relations that no restriction names
  is otherwise reported as undeclared); `parse_openfga_schema` passes them for you.
- **`zanzibar.graphindex.DeltaProcessor` is public** (TK153): the processor that maintains
  the `and` / `but not` relations, which `MissingDeltaProcessor` tells a caller who drives
  the apply step by hand to pass. A `Store` still builds its own.
- **The OpenFGA tuple form** (TK123): `Store.add_tuple("user:alice", "viewer", "doc:d1")`,
  with a userset as `"group:eng#member"` and every user as `"user:*"`; the same for
  `remove_tuple`, `check(user, relation, object, *, at_least=None)`, `lookup("user:alice")`,
  `lookup_reverse("viewer", "doc:d1")`, and `TupleSource.add` / `remove` / `check` (whose
  `check` now has an explicit signature instead of `*q`). The six-part form still works;
  the form is chosen by keyword (`user` / `object`) or by the number of arguments. A
  malformed string raises the new `MalformedTupleString` (a `ZanzibarError` and a
  `ValueError`) naming the expected form.
- **`Store(schema=...)` accepts an OpenFGA JSON model** (TK123): a `dict`, a JSON string,
  or either wrapped as `{"authorization_model": {...}}`. It is converted to DSL before it
  is saved, so the persisted schema is always DSL and reopening with the same JSON is
  accepted. Any other type, a compiled `RuleSet` included, raises `TypeError` naming `str`
  and `dict` (it used to fail with `AttributeError: 'RuleSet' object has no attribute
  'strip'`).
- **`Store.result_keys(result)` / `Store.excluded_keys(result)`** (TK123): read a
  `lookup` / `lookup_reverse` result as `(type, name, predicate)` keys, the same key
  format `SetEngine.result_keys` / `excluded_keys` use, with no SQL on the `Node` table.
  The key sets may differ (the graph index can also list a subject a marker already
  covers), so compare results by what they cover, not by key-set equality. An id whose
  node a later write removed raises `KeyError`. The PyPI quickstart uses them.
  `Store.lookup` / `lookup_reverse` are annotated `-> LookupResult`.
- **Top-level imports** (TK123): `from zanzibar import Store, LookupResult,
  parse_openfga_schema` and every exception class, `WriteLockUnsafe` included (it was in no
  `__all__`). They load lazily, so `import zanzibar` and `import zanzibar.schema` still do not
  import the database stack.
- **`zanzibar.ZanzibarError`**, the root of every exception the library raises on purpose,
  and **`zanzibar.SchemaError`** (a `ZanzibarError` and a `ValueError`), raised for every
  schema the parsers refuse. Each existing exception keeps its builtin base, so
  `except ValueError` / `except RuntimeError` handlers are unchanged. `InvariantViolation`
  (store corruption) is deliberately NOT a `ZanzibarError`, so `except ZanzibarError` never
  swallows it.
- `zanzibar.graphindex` exports `prune_outbox` and `outbox_watermark`. (An earlier
  draft of this release also re-exported exceptions from `zanzibar.store` and
  `zanzibar.graphindex`; TK164 replaced that: exceptions are exported from `zanzibar`
  only.)
- **`StoreNotFound`** (TK123): opening a store id that was never created raises it
  instead of a bare `KeyError`. It is a `ZanzibarError` and still a `KeyError`; its message
  says how to create the store (`Store(session, id, schema=...)`) and is not quoted twice.
  The failed open now rolls back, so it no longer holds the SQLite write lock.
- **`TablesNotCreated`** (TK123): opening a `Store` on a database without the `zanzibar_*`
  tables says to run `SQLModel.metadata.create_all(engine)`, instead of the driver's own
  `no such table` / `relation ... does not exist` error. `.missing` lists the tables.
- **`StaleLookupIds`** (TK154; a `ZanzibarError` and a `KeyError`): `SetEngine.result_keys` /
  `excluded_keys` and `Store.result_keys` / `excluded_keys` raise it instead of translating
  a result whose ids may have been reused (set engine: after any id is freed by a write or
  catch-up, after `rebuild()`, or on another engine instance; graph: an id whose node was
  removed). The bare `KeyError` the graph side raised is now this class. **`TablesOutdated`**
  (a `RuntimeError`): a `Store` refuses to open a SQLite database whose `zanzibar_node` was
  created by 0.0.x without `AUTOINCREMENT`; create the tables in a new file.
- **`IndexExists`** (TK123): `build_index` over an index that already exists raises it
  (a `ZanzibarError` and still a `ValueError`), pointing at `rebuild_index`.
- `SetEngine(session, store_id)` may omit the schema when a `Store` created the store: it
  reads the persisted schema (TK123).
- `Store(paranoia=...)` documents `'fixpoint'` and accepts the ints `1` / `0` as
  `'full'` / `'off'` (TK123).
- Docstrings for the table models (`Node`, `Edge`, `SchemaRecord`, `TupleLog`,
  `IndexCursor`), `WildcardIndex`, `SetEngine.check` and `Store.watermark`; the
  `LookupResult` docstring and the PyPI page explain the `"any"` / `"all"` markers and
  that a userset listed by `lookup_reverse` is itself allowed, not each of its members
  (TK123). The `Store` docstring now says that only a TOKENED `check` falls back to the set
  engine (an untokened read of a lagging async index can be stale, a revoke included) and
  that `sync` is per instance; the `SetEngine` docstring says it never commits (the caller
  does) and that its state is rebuilt in memory on open.
- **New PyPI page sections** (TK123; interim, to be folded into the full documentation):
  freshness tokens and async mode (what a token is, including that a duplicate add returns
  the current watermark rather than a row of its own; the caller-scheduled `catch_up()` loop, stale untokened
  reads after a grant or a revoke, per-instance `sync`), stall recovery, wildcards, an
  exception table, sessions / transactions / threads, and memory and storage (state rebuilt
  in memory on open, the permanent tuple log, pruning the delta outbox with
  `prune_outbox` / `outbox_watermark`). The quickstart now prints its checks. The page's
  imports, the `Store` attributes it names, its exception table and its async, wildcard and
  pruning claims are pinned by tests.

### Fixed
- A stall recorded while nothing was pending (for example a lock timeout or a lost
  connection while an async worker polled an idle store) is cleared by the next successful
  `catch_up()`, even one that applies nothing (TK165). It used to last until some write
  was made and applied, and until then untokened lookups raised `IndexStalled`. A stall on
  a row that cannot be applied (`PathCountExceeded`) is unchanged.
- A user string with a `:` in its relation part, such as `"user:a#b:c"`, raises
  `MalformedTupleString` on reads as well as writes (TK168). A read used to answer
  `False` and a write raised `AdmissionRejected`.
- The `StaleRead` message says "set engine at log id N" where it said "evaluator at
  N", and `TupleSource.check`'s says to call `refresh_evaluator()` (TK169).
- The `WatermarkGap` message raised by the set engine's catch-up says "set engine
  watermark N -> M" where it said "evaluator watermark", and names `refresh()` for a
  `Store` as well as `refresh_evaluator()` for a `TupleSource` (TK151).
- A write refused by `ZANZIBAR_MAX_CLOSURE_FANOUT` is cheap to refuse (TK158). The graph
  index counts the region with two indexed counts and refuses before loading it, and a
  `Store` takes the one admitted tuple back out of the set engine instead of rebuilding it
  (also for `PathCountExceeded`). A refused grant to a 1,000,000-member group took 91 s and
  3.8 GB; on a store already written to it now takes about 0.2 s (SQLite, 2026-10-22). The
  refusal is still atomic across the log, the set engine and the index.
- A direct `WildcardIndex` write on a schema with `and` / `but not` that is committed
  without `DeltaProcessor.run_cascade` is refused at the commit with the new
  `CascadeNotRun` (exported from `zanzibar`), instead of
  committing derived relations that disagree with the set engine (TK3). The check is
  always on, costs no SQL, and re-arms when a savepoint that held the cascade is rolled
  back. It shows that a cascade was called, not that its watermark was right. A `Store`
  is not affected.
- With `ZANZIBAR_PARANOIA=full` (or `fixpoint`), releasing a savepoint
  (`session.begin_nested()` ... `.commit()`) ran the after-commit check. On an in-memory
  SQLite database that check shared the caller's connection and rolled back the whole open
  transaction, so the savepoint's writes were lost: `check` could answer `True` where the
  set engine answers `False`, and a later rollback of an outer savepoint failed with
  `no such savepoint`. The after-commit check now runs only when the outermost transaction
  commits (TK170). `off` and `residue` were not affected.
- A `SetLookupResult` or graph `LookupResult` held across a write could translate to
  ANOTHER entity's key with no error (0.0.5 install trial F16): set-engine ids are
  recycled, and SQLite reused `zanzibar_node` row ids. Results are now stamped and checked
  (set engine) and graph node ids are never reused (`sqlite_autoincrement`);
  `engine.interner.key` is no longer documented. (TK154)

## [0.0.5] - 2026-10-14

### Added
- `SetEngine.excluded_keys(result)`: the portable `(type, name, predicate)` form of a
  `LookupResult`'s `excluded_node_ids`, the companion of `result_keys`. A lookup result
  that leaves the process is three parts: `result_keys`, `markers` and `excluded_keys`.
  `result_keys`'s docstring had called its output alone "the portable form", which would
  drop a `but not` exclusion at a service boundary (TK139 review).

### Changed
- **Breaking: four DSL shapes that OpenFGA refuses are refused here too** (`ValueError` at
  parse, with what to write instead) (TK137):
  - a `schema` line naming any version but `1.1` (`schema 1.2`, a bare `schema`). The version
    used to be ignored. Write `schema 1.1`; schema 1.2's modules are not supported.
  - extra words on a `model`, `schema 1.1` or `relations` line, a trailing comment included
    (`relations # docs`). Put each `define`, and each comment, on its own line.
  - `but not` beside `or` / `and` / a second `but not` at one level. It used to bind loosest,
    so `a but not b or c` meant `a but not (b or c)`. Parenthesise the reading you mean:
    `(a or b) but not c`, `a but not (b or c)`, `(a but not b) or c`.
  - a restriction naming a type no `type` line declares (`define viewer: [usr]` with no
    `type usr`), also in `parse_openfga_json`. Before, the typo let a `usr:x` write in and
    `check` said True. Declare the type or fix the spelling.
- `unparse_schema_ast` and `openfga_json_to_dsl` now declare every restriction type that has
  no relations (`type user`) at the top, and parenthesise both operands of `but not`, so
  their output parses under the rules above.
- `module`, `extend type`, `condition` blocks and `[user with cond]` were already refused;
  the message now names the unsupported OpenFGA feature.
- **No migration path for persisted stores.** Opening a store re-parses its persisted schema
  text, so a store saved under 0.0.4 or earlier with one of the refused shapes (including
  `openfga_json_to_dsl` output that restricts to a relation-less type, or renders
  `a or b but not c`) now refuses to open, and no public API drops a store id. The only
  way forward is a new store id with the rewritten schema, with its tuples written again.
  Such a store's open raises `zanzibar.connectedstore.PersistedSchemaRefused` (a
  `ValueError`), whose message says the schema was saved by 0.0.4 or earlier using a shape
  this version refuses, quotes the refusal, and gives the rewrite that keeps the meaning the
  store was serving (`instead` attribute), so the break does not read as corruption.

### Fixed
- `advance_index(..., proc=None)` on a schema with `and` / `but not` relations now raises
  `zanzibar.connectedstore.MissingDeltaProcessor` (a `ValueError`) before reading or writing
  anything, and the message names the fix: pass `DeltaProcessor(widx, ruleset.compiled)`, or
  let `ConnectedStore` advance the index (`refresh()` / `catch_up()`). Before, it applied the
  log without maintaining the `and` / `but not` relations, so the graph index silently
  disagreed with the set engine: with `define viewer: [user] but not banned` and alice
  granted, the index said False and the set engine True. A schema with only unions still
  takes `proc=None` (TK123).
- A `SetEngine` opened on a store id that a `ConnectedStore` owns (the id has a persisted
  schema) now compares the schema it is given with the store's and raises `SchemaMismatch`
  if they differ, by the same rule as `ConnectedStore(..., schema=...)`: the parsed schema
  and the declared `object_wildcard_shapes` must be equal, so formatting and the order of
  `type` / `define` lines do not matter. Before, it answered under whatever schema it was
  given: with the store's `but not banned` dropped, a banned user read as allowed.
  `zanzibar.connectedstore.open_set_engine(session, store_id)` opens one with the store's
  own schema. A `SetEngine` on a store id no `ConnectedStore` owns is unchanged: it uses
  the schema it is given. `SchemaMismatch` now lives in `zanzibar.schema.errors` and is also
  exported from `zanzibar.schema`; `zanzibar.connectedstore.SchemaMismatch` is the same
  class, so existing `except` clauses still catch it (TK123).
- A `relations` line with a `define` on it (`relations define viewer: [user]`) parsed and
  silently dropped the relation. It is now refused (TK137).
- `SetEngine.lookup_reverse` now fills `excluded_node_ids` with the subjects a `but not`
  refuses under a wildcard grant, as `ConnectedStore.lookup_reverse` already did. Before,
  with `define viewer: [user:*] but not banned`, a `user:*` grant and `mallory` banned, it
  returned the "every user" marker with nothing excluded, so a list-users page built on the
  standalone set engine listed mallory although `check` refused her (TK139).
- A standalone `SetEngine` opened on a store id that a `ConnectedStore` owns (the id has a
  persisted schema) now refuses `add_tuple` / `remove_tuple` with `UnloggedWriteRefused`;
  reads through it still work. Before, its writes skipped the tuple log: an unlogged
  `remove_tuple` left the grant ALLOWed by `ConnectedStore.check` with `lag() == 0`, and
  `ConnectedStore.remove_tuple` then refused to revoke it. The engine also refuses once the
  id is claimed after it was opened, from its next transaction on (TK140).
- `ConnectedStore(session, store_id, ...)` refuses, with the new
  `zanzibar.connectedstore.UnloggedTuplesPresent`, to open a store id for the first time
  when it holds tuples the tuple log does not account for (written by a standalone
  `SetEngine`). Before, it adopted them silently: its index never saw them (`check` False
  while the set engine said True), and removing one raised `InvariantViolation`. The
  refused open writes nothing. To adopt such a store: `save_schema(session, id, schema)`,
  commit, `build_index(session, id)`, then `ConnectedStore(session, id)` (TK140).

### Documentation
- **A userset is not a member of itself here, unlike OpenFGA** (documented, not changed;
  TK138). OpenFGA counts `doc:1#banned` as a member of `doc:1#banned`, and so of every
  relation built on it; this library does not, except through a `from` parent. The
  security-relevant case: with `define vx: [user, doc#banned] but not banned` and the tuple
  `doc:1#banned vx doc:1`, checking `doc:1#banned` for `vx` on `doc:1` is allowed here and
  denied by OpenFGA. The opposite also happens: `define vy: [user, doc#editor] and editor`
  with `doc:1#editor vy doc:1` is denied here and allowed by OpenFGA. Only userset subjects
  are affected; plain users and `user:*` are not. The PyPI README lists it. Adopting
  OpenFGA's rule is planned for a later minor version, because it changes answers.
- The READMEs now state that a grant on every instance (`folder:*`) does not reach a grant
  on "any" instance while no instance exists, with a zero-folders example. This strict
  reading is the current mode; a lenient mode may come later, in all backends together
  (TK4).

## [0.0.4]

### Fixed
- A malformed OpenFGA JSON model is refused with a `ValueError` that names the field:
  the model given as `null` or a list, `type_definitions` that is not an array, a type
  definition with no `"type"`, a `computedUserset` with no `"relation"`, a union with no
  `"child"`, and so on. `parse_openfga_json` used to leak a bare `AttributeError`,
  `TypeError` or `KeyError`. An optional object or array given as `null` (OpenFGA's
  DSL-to-JSON transformer emits `"metadata": null`) still reads as absent; a non-object
  `metadata` such as `[]`, previously ignored, is now refused.
- The `CyclicDerivedDependency` message names only the relations on the cycle, not every
  relation that depends on it. It no longer cites an internal spec, and it says what to
  write instead and how that rewrite differs.
- Reopening a store with `ConnectedStore(session, store_id, schema=...)` now compares the
  parsed schema, not the text. Before, a trailing newline, Windows line endings, a different
  indent, a comment, or reordered `type` / `define` blocks raised `SchemaMismatch` for the
  store's own schema. A different schema is still refused, and the stored text is never
  rewritten (found by the 0.0.3 install trial, `docs/pypi-trial-0.0.3-2026-10-08.md`).

### Changed
- `ZANZIBAR_PARANOIA=residue` (`paranoia='residue'`) now also checks crossing-middle
  completeness (invariant I14), but only for the entities each write touches. A regression
  of the 2026-08-09 crossing-middle fix used to grant access silently at this level. It now
  aborts the write with `InvariantViolation`. The check costs nothing on a schema without
  object wildcards (`object_wildcard_shapes`).

### Documentation
- The PyPI README now covers what the 0.0.3 install trial had to discover by hand: recursion
  through `and` / `but not` (refused by `ConnectedStore`, accepted by `SetEngine`, with a
  rewrite and how it differs), acyclic tuple data, lenient reads, and how to read a
  `LookupResult` (resolving node ids, markers, exclusions). `LookupResult` has a docstring.
- Statements about OpenFGA were checked against its documentation and source, and the
  inaccurate ones corrected. The schema language is described as a subset of the OpenFGA
  DSL (no conditions or modules). Wildcard tuplesets (`parent: [folder:*]`) are listed with
  the other extensions beyond OpenFGA. The userset-tupleset refusal message now tags only
  the refusal itself as the OpenFGA rule, not its suggested rewrite.

## [0.0.3]

Fixes everything the fresh-user install trial of the published 0.0.2 found broken
(`docs/pypi-trial-0.0.2-2026-10-07.md`).

### Fixed
- The graph index now serves `x from parent` when `x` names a boolean (`and` / `but not`)
  relation on some type, which is the common OpenFGA pattern of every type defining its
  own `viewer`. Before, `parse_openfga_schema` and `ConnectedStore` raised
  `UnsupportedByGraphIndex` on schemas the set engine accepted. The admission checks now
  compare `(type, relation)` instead of the bare relation name.
- `define viewer: ([user] or viewer from parent) but not banned` no longer crashes both
  backends with an internal `ValueError: Rule then-pattern carries a derived subject
  predicate`. It is served.
- A schema that declares no type (empty, whitespace, comments only, or only the
  `model` / `schema 1.1` header) is refused at parse time, and so is one whose types declare
  no relation. The same goes for an OpenFGA JSON model with no `type_definitions` or no
  relations. `ConnectedStore` used to persist these schemas write-once, which made the
  store id unusable.
- A write field that is not a `str` (`None`, numbers, bytes) is refused with
  `AdmissionRejected` on every backend and for every field. A `None` subject predicate
  used to leak `sqlalchemy.exc.IntegrityError` from `ConnectedStore`, and `SetEngine`
  silently accepted it as the bare predicate.
- A store id must be a `str` containing a non-whitespace character. `None`, numbers,
  bytes and blank strings now raise `AdmissionRejected` in every constructor. Before, they
  were accepted, or leaked a database error.

## [0.0.2]

First release published to PyPI. Same library as 0.0.1.

### Fixed
- `formal/conformance/test_runner_retry.py`'s spawn-error stub now sets `.winerror`
  explicitly. Only Windows CPython derives it from `OSError`'s fourth argument, so on the
  Linux CI runner the retry test failed and the no-retry test passed for the wrong reason.
  Test-only; no library change.

## [0.0.1]

Tagged but never published: the release gate failed on the Linux CI runner (the test
above), so the upload was skipped. A trial of the release pipeline (tag -> gate -> fuzz ->
PyPI), not a stability promise.

### Added
- The `zanzibar` package: `zanzibar.schema` (OpenFGA-DSL parser and compiler, including
  `and` / `but not`), `zanzibar.setengine`, `zanzibar.graphindex` and
  `zanzibar.connectedstore`.
- Apache-2.0 licence, `py.typed` marker, PyPI metadata.

### Changed
- All database tables are prefixed `zanzibar_` (`node` -> `zanzibar_node`, ...), as are the
  explicit constraint and index names. The tables no longer set `extend_existing`, so a
  name clash with an application's own table raises instead of silently merging the two.
  This is a schema change for any existing database. There is no migration: rebuild the
  store from its tuples.
