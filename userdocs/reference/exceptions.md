# Exceptions

Every exception the library raises on purpose is importable from the top-level package,
`zanzibar`, and every one but {py:exc}`zanzibar.InvariantViolation` derives from
{py:exc}`zanzibar.ZanzibarError`. Most also keep a builtin base ({py:exc}`ValueError`,
{py:exc}`KeyError` or {py:exc}`RuntimeError`), so a handler that catches the builtin keeps
working; {py:exc}`~zanzibar.UnsupportedByGraphIndex` and its subclass
{py:exc}`~zanzibar.DoublyBridgedShapeError` have none.

Import exceptions from `zanzibar`. The subpackages (`zanzibar.store`,
`zanzibar.setengine`, `zanzibar.graphindex`) re-export some of them, but each a different
selection, so `from zanzibar import ...` is the one form that works for all of them. The
classes are the same objects either way.

For how to choose what to catch in an application, see
[Handle errors](../how-to/errors.md).

## Hierarchy

Builtin bases are in brackets. A class inherits every base of its parents.

```text
Exception
├── ZanzibarError
│   ├── SchemaError                  [ValueError]
│   │   └── ShapeNoLongerAccepted
│   ├── PersistedSchemaRefused       [ValueError]
│   ├── CyclicDerivedDependency      [ValueError]
│   ├── SchemaMismatch               [ValueError]
│   ├── UnsupportedByGraphIndex
│   │   └── DoublyBridgedShapeError
│   ├── MalformedTupleString         [ValueError]
│   ├── AdmissionRejected            [ValueError]
│   │   └── IndexResourceLimit
│   │       ├── ClosureFanoutExceeded
│   │       └── PathCountExceeded
│   ├── MissingDeltaProcessor        [ValueError]
│   ├── IndexExists                  [ValueError]
│   ├── StoreNotFound                [KeyError]
│   ├── StaleLookupIds               [KeyError]
│   ├── StaleRead                    [RuntimeError]
│   │   └── LookupNotFresh
│   │       └── IndexStalled
│   ├── WatermarkGap                 [RuntimeError]
│   ├── UnsafeIsolationLevel         [RuntimeError]
│   ├── WriteLockUnsafe              [RuntimeError]
│   ├── UnloggedWriteRefused         [RuntimeError]
│   ├── UnloggedTuplesPresent        [RuntimeError]
│   ├── TablesNotCreated             [RuntimeError]
│   └── TablesOutdated               [RuntimeError]
└── AssertionError
    └── InvariantViolation           (not a ZanzibarError)

UserWarning
└── UnprovenExtensionWarning         (a warning, not an error)
```

{py:exc}`zanzibar.InvariantViolation` is outside the tree on purpose. It means the stored
index is corrupt, not that a call was refused, so `except ZanzibarError` never swallows it.
It is raised by the runtime checks that the `paranoia` setting turns on (see
[Configuration](configuration.md)).

```python
import zanzibar

print(issubclass(zanzibar.ClosureFanoutExceeded, zanzibar.AdmissionRejected))  # -> True
print(issubclass(zanzibar.AdmissionRejected, ValueError))  # -> True
print(issubclass(zanzibar.IndexStalled, zanzibar.StaleRead))  # -> True
print(issubclass(zanzibar.StoreNotFound, KeyError))  # -> True
print(issubclass(zanzibar.CyclicDerivedDependency, zanzibar.SchemaError))  # -> False
print(issubclass(zanzibar.CyclicDerivedDependency, ValueError))  # -> True
print(issubclass(zanzibar.InvariantViolation, zanzibar.ZanzibarError))  # -> False
print(issubclass(zanzibar.InvariantViolation, AssertionError))  # -> True
print(issubclass(zanzibar.UnprovenExtensionWarning, UserWarning))  # -> True
```

## When each is raised

| exception | raised when |
| --- | --- |
| {py:exc}`~zanzibar.SchemaError` | the parser refuses a schema text (DSL or OpenFGA JSON): a syntax error, a dangling or cyclic relation reference, or a refused shape. For a refused shape, the message says what to write instead ([Refused schema shapes](refused-shapes.md), [Rewrite a refused schema shape](../how-to/rewrite-refused-shape.md)). |
| {py:exc}`~zanzibar.ShapeNoLongerAccepted` | a schema you pass uses a shape an older release accepted and this one refuses. `instead` holds the rewrite. See [Rewrite a refused schema shape](../how-to/rewrite-refused-shape.md). |
| {py:exc}`~zanzibar.PersistedSchemaRefused` | a store's *stored* schema uses such a shape, so the store cannot be opened, whichever call opens it. See [Upgrade from 0.0.x to 0.1](../how-to/upgrade-0.1.md). |
| {py:exc}`~zanzibar.CyclicDerivedDependency` | a relation that uses `and` / `but not` depends on itself through a `from` step or a `[type#relation]` restriction. Raised by {py:func}`~zanzibar.parse_openfga_schema` and by {py:class}`~zanzibar.Store`; a standalone {py:class}`~zanzibar.setengine.SetEngine` accepts the schema. Not a {py:exc}`~zanzibar.SchemaError`. |
| {py:exc}`~zanzibar.SchemaMismatch` | a store is opened with a schema other than the one it was created with. |
| {py:exc}`~zanzibar.UnsupportedByGraphIndex` | the graph index cannot represent a schema construct: a wildcard feature (a `[T:*#p]` restriction, a star tupleset or an `object_wildcard_shapes` entry) that reaches a relation using `and` / `but not`, or `and` / `but not` when the rule set is compiled with `enable_boolean=False`. Raised by `parse_openfga_schema` and `Store`; a standalone `SetEngine` accepts these schemas. |
| {py:exc}`~zanzibar.DoublyBridgedShapeError` | a shape is both a wildcard-userset shape and an object-wildcard shape. Both backends refuse it. |
| {py:exc}`~zanzibar.MalformedTupleString` | a `"type:name"` / `"type:name#relation"` argument cannot be split into its parts. The part after `#` is not checked for allowed characters here, so `"group:g#b:c"` is not malformed: a read answers `False` and a write raises `AdmissionRejected`. |
| {py:exc}`~zanzibar.AdmissionRejected` | a write is refused: an undeclared type or relation, a subject the type restriction does not admit, an identifier outside the allowed characters, a cycle, or removing a tuple that is not stored. The store is unchanged. |
| {py:exc}`~zanzibar.IndexResourceLimit` | never raised itself: the common base of the two refusals below, which depend on how large the index's closure has grown rather than on the tuple and the schema. Catch it to handle both. |
| {py:exc}`~zanzibar.ClosureFanoutExceeded` | a synchronous write would add more rows to the index than the fan-out cap allows. Nothing is written. See [Cap write fan-out](../how-to/fanout-cap.md). |
| {py:exc}`~zanzibar.PathCountExceeded` | a write would push a stored path count past the 32-bit integer limit. On a synchronous write the write is refused and nothing is written. With `sync=False` the write is accepted into the log; `catch_up()` then raises this and the index stalls (see {py:exc}`~zanzibar.IndexStalled`). While that row waits, every write through a `sync=True` instance of the store, removals included, raises this too, with a message about the waiting row (`failing_log_row` names it). |
| {py:exc}`~zanzibar.MissingDeltaProcessor` | the index's apply step is driven by hand without a delta processor, on a schema with `and` / `but not`. |
| {py:exc}`~zanzibar.IndexExists` | {py:func}`~zanzibar.store.build_index` or {py:meth}`Store.adopt <zanzibar.Store.adopt>` targets an index that already exists. |
| {py:exc}`~zanzibar.StoreNotFound` | `Store(session, store_id)` without `schema=` names a store id that has no stored schema in this database. |
| {py:exc}`~zanzibar.StaleLookupIds` | ids from a lookup result are translated after they may have been reused (after a write, a rebuild, or on another instance). Run the lookup again. |
| {py:exc}`~zanzibar.StaleRead` | a read carrying an `at_least` token cannot be satisfied. Call `refresh()` and retry. |
| {py:exc}`~zanzibar.LookupNotFresh` | a `lookup` / `lookup_reverse` carrying an `at_least` token while the index is behind the token. Run `catch_up()` and retry. |
| {py:exc}`~zanzibar.IndexStalled` | an untokened `lookup` / `lookup_reverse` while the index has recorded that it cannot advance. See [Recover a stalled index](../how-to/stall-recovery.md). |
| {py:exc}`~zanzibar.WatermarkGap` | advancing the index would skip committed log rows (a concurrent commit not yet visible). Retryable: `refresh()` and retry. |
| {py:exc}`~zanzibar.UnsafeIsolationLevel` | a PostgreSQL session is not at `READ COMMITTED`. Raised when the store opens. |
| {py:exc}`~zanzibar.WriteLockUnsafe` | a SQLite connection is in autocommit mode, so the per-store write lock would not hold. Raised when the store opens. |
| {py:exc}`~zanzibar.UnloggedWriteRefused` | a standalone set engine writes to a store id that a {py:class}`~zanzibar.Store` owns. |
| {py:exc}`~zanzibar.UnloggedTuplesPresent` | a {py:class}`~zanzibar.Store` opens over tuples a standalone set engine wrote. Use {py:meth}`Store.adopt <zanzibar.Store.adopt>`. |
| {py:exc}`~zanzibar.TablesNotCreated` | a {py:class}`~zanzibar.Store` opens on a database without the `zanzibar_*` tables. See [Database tables](tables.md). |
| {py:exc}`~zanzibar.TablesOutdated` | a {py:class}`~zanzibar.Store` opens a SQLite file whose `zanzibar_node` table an older release created. See [Database tables](tables.md) and [Upgrade from 0.0.x to 0.1](../how-to/upgrade-0.1.md). |
| {py:exc}`~zanzibar.InvariantViolation` | a runtime check finds the stored index corrupt. When the check before the commit fails, the commit does not happen. At the `full` and `fixpoint` levels a second check runs after the commit; when that one fails the write is already stored, and in the current version the caller receives `sqlalchemy.exc.InvalidRequestError` with the `InvariantViolation` as its `__context__`. See [Configuration](configuration.md). |
| {py:exc}`~zanzibar.UnprovenExtensionWarning` | (a warning) a schema uses a wildcard extension beyond OpenFGA. |

Some argument errors are plain builtins and not part of this tree: for example, a bad
`paranoia` value is a {py:exc}`ValueError`, a compiled rule set passed as `schema=` is a
{py:exc}`TypeError`, and a `Session` with pending changes passed to a
{py:class}`~zanzibar.Store` is a {py:exc}`ValueError`.

```python
from sqlmodel import SQLModel, Session, create_engine
import zanzibar
import zanzibar.store  # registers the zanzibar_* tables before create_all

SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
"""

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    store = zanzibar.Store(session, "exceptions-demo", schema=SCHEMA)
    try:
        store.add_tuple("user:alice", "vewer", "doc:1")
    except zanzibar.AdmissionRejected as exc:
        caught = type(exc).__name__
    print(caught)  # -> 'AdmissionRejected'

    try:
        store.add_tuple("user alice", "viewer", "doc:1")
    except ValueError as exc:  # the builtin base still catches it
        caught = type(exc).__name__
    print(caught)  # -> 'MalformedTupleString'

with Session(engine) as session:
    try:
        zanzibar.Store(session, "no-such-store")
    except zanzibar.StoreNotFound as exc:
        missing_id = exc.store_id
print(missing_id)  # -> 'no-such-store'
```

## The root

```{eval-rst}
.. py:exception:: zanzibar.ZanzibarError

   Bases: :py:exc:`Exception`

   The root of every exception the library raises on purpose. ``except
   zanzibar.ZanzibarError`` catches every refusal, limit and freshness error the library
   defines. :py:exc:`zanzibar.InvariantViolation` and
   :py:exc:`zanzibar.UnprovenExtensionWarning` are deliberately outside it.
```

## Schema errors

```{eval-rst}
.. py:exception:: zanzibar.SchemaError

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`ValueError`

   The parser refused a schema text (DSL or OpenFGA JSON): a syntax error, a dangling or
   cyclic relation reference, or a refused shape. The message says what is wrong and, for
   a refused shape, what to write instead. Two refusals are not ``SchemaError`` (and not
   ``ValueError``): :py:exc:`~zanzibar.UnsupportedByGraphIndex` and its subclass
   :py:exc:`~zanzibar.DoublyBridgedShapeError`; and
   :py:exc:`~zanzibar.CyclicDerivedDependency` is a ``ValueError`` but not a
   ``SchemaError``. Catch :py:exc:`~zanzibar.ZanzibarError` to cover all of them.

.. py:exception:: zanzibar.ShapeNoLongerAccepted

   Bases: :py:exc:`zanzibar.SchemaError`

   A schema you pass uses a shape that an earlier release accepted and this one refuses:
   a ``schema`` line naming a version other than ``1.1``, extra words on a header line,
   ``but not`` sharing a level with another operator without parentheses, a type
   restriction naming an undeclared type, or an ``object_wildcard_shapes`` entry naming
   no declared relation. The message ends with the rewrite.

   .. py:attribute:: instead
      :type: str

      The rewrite that keeps the meaning, in words you can act on.

   .. py:attribute:: accepted_through
      :type: str

      The last release that accepted the shape.

   .. py:attribute:: refused_since
      :type: str

      The first release that refuses it.

.. py:exception:: zanzibar.PersistedSchemaRefused

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`ValueError`

   A store's *stored* schema text uses a shape this release refuses, so the store cannot
   be opened. Every open re-parses the stored text, so this is raised whatever opens the
   store: :py:class:`zanzibar.Store` with or without ``schema=``,
   :py:class:`zanzibar.setengine.SetEngine`, or :py:func:`zanzibar.store.build_index`. There is no
   lenient mode. The message quotes the parser's refusal and gives the rewrite.

   .. py:attribute:: store_id
      :type: str

   .. py:attribute:: refusal
      :type: zanzibar.ShapeNoLongerAccepted

      The parser's refusal; also the exception's ``__cause__``.

   .. py:attribute:: instead
      :type: str

      The rewrite, as in ``refusal.instead``.

.. py:exception:: zanzibar.CyclicDerivedDependency

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`ValueError`

   A relation that uses ``and`` / ``but not`` depends on itself, through a ``from`` step
   or a ``[type#relation]`` restriction. The graph index cannot evaluate that recursion,
   so :py:func:`zanzibar.parse_openfga_schema` and :py:class:`~zanzibar.Store` refuse the
   schema. A standalone :py:class:`zanzibar.setengine.SetEngine` accepts it. The message
   suggests a rewrite.

   Not a subclass of :py:exc:`~zanzibar.SchemaError`. Recursion that the parser itself
   refuses is a ``SchemaError``: a relation referring to itself through relation names
   alone, and recursion through the part a ``but not`` subtracts.

.. py:exception:: zanzibar.SchemaMismatch

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`ValueError`

   An explicit schema, or set of object-wildcard shapes, disagrees with the one the store
   was created with. Stored schemas never change. Raised by :py:class:`zanzibar.Store`
   and by :py:class:`zanzibar.setengine.SetEngine` opened on a store id that has a stored schema.
   The same schema reformatted, reordered or with comments is not a mismatch.

.. py:exception:: zanzibar.UnsupportedByGraphIndex

   Bases: :py:exc:`zanzibar.ZanzibarError`

   The graph index cannot represent a schema construct: a wildcard feature (a
   ``[T:*#p]`` restriction, a star tupleset or an ``object_wildcard_shapes`` entry) that
   reaches a relation using ``and`` / ``but not``, or ``and`` / ``but not`` when the rule
   set is compiled with ``enable_boolean=False``. Raised by
   :py:func:`zanzibar.parse_openfga_schema` and :py:class:`zanzibar.Store`. The message
   names the relation. The set engine handles every
   shape this refuses except :py:exc:`~zanzibar.DoublyBridgedShapeError`.

.. py:exception:: zanzibar.DoublyBridgedShapeError

   Bases: :py:exc:`zanzibar.UnsupportedByGraphIndex`

   A shape is both a wildcard-userset shape (a ``[T:*#p]`` restriction) and an
   object-wildcard shape. A wildcard write on it would make the graph index refuse every
   later ordinary write of that shape, so both backends refuse the schema.
```

## Write refusals

```{eval-rst}
.. py:exception:: zanzibar.MalformedTupleString

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`ValueError`

   A ``"type:name"`` or ``"type:name#relation"`` string could not be split into its parts.
   The message names the expected form. The relation part after ``#`` is not checked for
   allowed characters at this step: ``"group:g#b:c"`` is not malformed, so a read with it
   answers ``False`` and a write raises :py:exc:`~zanzibar.AdmissionRejected`.

.. py:exception:: zanzibar.AdmissionRejected

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`ValueError`

   A write was correctly refused; the store is intact. The refusals are: a cycle, an
   identifier outside the allowed characters or length, a tuple no declared type
   restriction admits, an undeclared wildcard shape, and removing a tuple that is not
   stored. It is never a sign of corruption; that is
   :py:exc:`~zanzibar.InvariantViolation`.

.. py:exception:: zanzibar.IndexResourceLimit

   Bases: :py:exc:`zanzibar.AdmissionRejected`

   The graph index declined to materialise an admitted write because of a limit on the
   size of its closure, not because of the tuple or the schema. Not raised itself: its two
   subclasses are :py:exc:`~zanzibar.ClosureFanoutExceeded` and
   :py:exc:`~zanzibar.PathCountExceeded`.

.. py:exception:: zanzibar.ClosureFanoutExceeded

   Bases: :py:exc:`zanzibar.IndexResourceLimit`

   A synchronous write would add more rows to the graph index's closure than the
   ``ZANZIBAR_MAX_CLOSURE_FANOUT`` cap allows (default 100,000; ``0`` disables it). The
   refusal is atomic: the write is absent from the tuple log and from both backends. The
   cap bounds how long one write holds the store's write lock; it is not an access rule,
   and under ``but not`` a ban is capped like any other write. Rows already in the log are
   never refused: :py:meth:`Store.catch_up <zanzibar.Store.catch_up>` and
   :py:func:`~zanzibar.store.build_index` apply them with a logged warning. See
   :doc:`configuration`.

.. py:exception:: zanzibar.PathCountExceeded

   Bases: :py:exc:`zanzibar.IndexResourceLimit`

   A write would push a closure row's path count past 2,147,483,647, the 32-bit integer
   limit, which applies on SQLite and PostgreSQL alike. Path counts count derivations, so
   a chain of K diamonds doubles them K times. A synchronous write is refused. With
   ``sync=False``, :py:meth:`Store.catch_up <zanzibar.Store.catch_up>` raises it and the
   index stalls (see :py:exc:`~zanzibar.IndexStalled`). While that row waits in the log,
   every write through a ``sync=True`` instance of the same store, removals included,
   raises it as well, because a sync write applies the waiting rows first; the message
   then describes the waiting row, not the tuple being written, and the exception's
   ``failing_log_row`` attribute is ``(log id, row)``. See :doc:`../how-to/stall-recovery`.
```

## Freshness and the index

```{eval-rst}
.. py:exception:: zanzibar.StaleRead

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`RuntimeError`

   A read carrying an ``at_least`` token could not be satisfied: the index is behind the
   token and the write is not visible in this session's read snapshot. Call
   ``refresh()`` and retry. If the message ends by saying the token was returned by a
   write to another store, retrying does not help, although the message opens with that
   advice. A token from another store is refused only when it is newer than this store's
   writes; an older one is accepted without error and guarantees nothing.

.. py:exception:: zanzibar.LookupNotFresh

   Bases: :py:exc:`zanzibar.StaleRead`

   A ``lookup`` / ``lookup_reverse`` carrying an ``at_least`` token could not be served,
   because the index is behind the token. ``check`` falls back to the set engine in this
   case; the lookups do not, because the two backends' results use different node ids.
   Run ``catch_up()`` (any instance may) and retry. For a single yes/no answer,
   ``check(..., at_least=...)`` needs no catch-up. Neither helps when the token came from
   another store (the message ends by saying so); see :py:exc:`~zanzibar.StaleRead`.

.. py:exception:: zanzibar.IndexStalled

   Bases: :py:exc:`zanzibar.LookupNotFresh`

   An untokened ``lookup`` / ``lookup_reverse`` was refused because the last
   ``catch_up()`` could not advance the index, so how far behind it is no longer bounded.
   ``check`` falls back to the set engine in this state. A stall from a transient failure
   (a lock timeout, a lost connection) ends at the next successful ``catch_up()`` that
   applies at least one row. A ``catch_up()`` that applies nothing does not end it, even
   though the message suggests a successful ``catch_up()``: a stall recorded while nothing
   was pending (the message says "lag 0") lasts until some write is made and applied, or
   until :py:func:`~zanzibar.store.rebuild_index`. A row
   that can never be applied, a path-count overflow, needs action: ``Store.stall_error``
   names the row and the failure. See :doc:`../how-to/stall-recovery`.

.. py:exception:: zanzibar.WatermarkGap

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`RuntimeError`

   Advancing the index or the set engine would have skipped committed log rows. On
   PostgreSQL a log row with a lower id can become visible after one with a higher id, so
   a catch-up can see a gap; the advance is refused instead of skipping it. Nothing is
   corrupt. Call ``refresh()`` and retry.

.. py:exception:: zanzibar.StaleLookupIds

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`KeyError`

   ``result_keys`` / ``excluded_keys`` refused to translate a lookup result whose ids may
   no longer name what they named when the lookup ran. Ids are valid only for the read
   snapshot the lookup used. Run the lookup again and translate the new result before
   the next write.

   .. py:attribute:: field
      :type: str

      ``'node_ids'`` or ``'excluded_node_ids'``.

   .. py:attribute:: ids
      :type: list[int]

      The first offending ids; empty when the whole result is stale.

.. py:exception:: zanzibar.MissingDeltaProcessor

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`ValueError`

   The index's apply step was driven by hand without a delta processor, on a schema with
   ``and`` / ``but not``. Without it the index would disagree with the set engine. A
   :py:class:`~zanzibar.Store` never raises it.

.. py:exception:: zanzibar.IndexExists

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`ValueError`

   :py:func:`~zanzibar.store.build_index` or :py:meth:`Store.adopt <zanzibar.Store.adopt>`
   was pointed at an index store id that already has a cursor or graph state. Use a new
   index store id, or :py:func:`~zanzibar.store.rebuild_index` to rebuild in place.

   .. py:attribute:: index_store_id
      :type: str

   .. py:attribute:: detail
      :type: str

      What was found.
```

## Opening a store

```{eval-rst}
.. py:exception:: zanzibar.StoreNotFound

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`KeyError`

   The store id has no stored schema in this database: it was never created here, or the
   session points at another database. A store is created by passing its schema once:
   ``Store(session, store_id, schema=...)``.

   .. py:attribute:: store_id
      :type: str

.. py:exception:: zanzibar.TablesNotCreated

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`RuntimeError`

   The database has none, or only some, of the ``zanzibar_*`` tables. Raised by
   :py:class:`~zanzibar.Store` in place of the database driver's own error. See
   :doc:`tables`.

   .. py:attribute:: missing
      :type: list[str]

      The absent table names.

.. py:exception:: zanzibar.TablesOutdated

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`RuntimeError`

   A SQLite file's ``zanzibar_node`` table was created by a 0.0.x release, without
   ``AUTOINCREMENT``. The file is not migrated. See :doc:`tables` and
   :doc:`../how-to/upgrade-0.1`.

   .. py:attribute:: table
      :type: str

      ``'zanzibar_node'``.

.. py:exception:: zanzibar.UnsafeIsolationLevel

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`RuntimeError`

   A PostgreSQL session runs at an isolation level other than ``READ COMMITTED``, under
   which a committed write can stay invisible to the store. Raised when the store opens.
   The message names the fix. See :doc:`environments`.

.. py:exception:: zanzibar.WriteLockUnsafe

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`RuntimeError`

   The per-store write lock cannot be taken on this session's connection (a SQLite
   connection in autocommit mode), so a write's checks would not be atomic against other
   writers. Raised when the store opens. The message names the fix.

.. py:exception:: zanzibar.UnloggedTuplesPresent

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`RuntimeError`

   A :py:class:`~zanzibar.Store` refused to open over a store id that already has tuples
   with no matching tuple-log rows, written by a standalone set engine before any
   ``Store`` claimed the id. The index, which is built from the log, would not see them.
   Open such a store with :py:meth:`Store.adopt <zanzibar.Store.adopt>`.

.. py:exception:: zanzibar.UnloggedWriteRefused

   Bases: :py:exc:`zanzibar.ZanzibarError`, :py:exc:`RuntimeError`

   A direct ``add_tuple`` / ``remove_tuple`` on a standalone
   :py:class:`~zanzibar.setengine.SetEngine` was refused because a :py:class:`~zanzibar.Store` owns
   that store id. Such a write would bypass the tuple log, so the index and every other
   instance would never see it. Write through the ``Store``.
```

## Outside the tree

```{eval-rst}
.. py:exception:: zanzibar.InvariantViolation

   Bases: :py:exc:`AssertionError`

   A stored-state invariant does not hold: the index is corrupt. Raised by the runtime
   checks that the ``paranoia`` setting turns on (see :doc:`configuration`). It is
   deliberately not a :py:exc:`~zanzibar.ZanzibarError`, so a handler for refusals never
   swallows it; catch it explicitly if you catch it at all.

.. py:exception:: zanzibar.UnprovenExtensionWarning

   Bases: :py:exc:`UserWarning`

   A schema uses a wildcard extension beyond OpenFGA: a wildcard userset ``[T:*#p]``, a
   wildcard tupleset, or object wildcards. Agreement between the two backends on these
   rests on tests alone. Emitted once per :py:class:`~zanzibar.Store` open (or
   :py:func:`zanzibar.parse_openfga_schema` / :py:class:`~zanzibar.setengine.SetEngine` call).
   Silence it with
   ``warnings.filterwarnings('ignore', category=zanzibar.UnprovenExtensionWarning)``.
```
