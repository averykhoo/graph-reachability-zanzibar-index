# zanzibar.store

The composed store. An append-only tuple log is the source of truth, a graph index is
kept up to date from it, and a set engine stands beside the index to answer reads the
index cannot serve yet. {py:class}`zanzibar.Store` is the class most programs use.

```{eval-rst}
.. py:module:: zanzibar.store
```

## Store

`Store` and `ExpandResult` are importable from both `zanzibar` and `zanzibar.store`; they
are documented here under their top-level names.

```{eval-rst}
.. autoclass:: zanzibar.Store
   :members: adopt, add_tuple, remove_tuple, catch_up, index_stalled, stall_error,
             refresh, lag, check, lookup, lookup_reverse, expand, result_keys,
             excluded_keys, watermark

   The constructor opens an existing store, or creates one when ``schema`` is given.
   Every argument, with its type, default and meaning, is listed under "Store
   arguments" on the :doc:`../configuration` page. In brief:

   * ``schema`` is OpenFGA DSL text, or an OpenFGA JSON model as a ``dict`` or a JSON
     string (also wrapped as ``{"authorization_model": {...}}``). JSON is converted to DSL
     before it is saved, so the saved schema is always DSL. A compiled ``RuleSet`` is not
     accepted. The schema is saved once; reopening with a schema that parses differently
     raises :py:exc:`~zanzibar.SchemaMismatch`, while the same schema re-indented, with
     CRLF line endings, comments or reordered type blocks is accepted.
   * ``sync=True`` (the default) updates the graph index inside every write. With
     ``sync=False`` writes reach the tuple log only, and the index advances when
     :py:meth:`catch_up` runs.
   * ``paranoia`` selects the runtime check level: ``'off'`` / ``False`` / ``0``,
     ``'residue'``, ``'full'`` / ``True`` / ``1``, or ``'fixpoint'``. Any other value
     raises :py:exc:`ValueError`. An explicit argument wins over the ``ZANZIBAR_PARANOIA``
     environment variable, which wins over :py:attr:`DEFAULT_PARANOIA`. A failed check
     raises :py:exc:`~zanzibar.InvariantViolation` before the write's commit, so the
     write is not committed; the message names the store id, the commit phase and the
     violated invariant. The levels and their costs are in the
     :ref:`table of levels <paranoia-levels>` on the :doc:`../configuration` page.

   .. py:attribute:: DEFAULT_PARANOIA
      :type: str
      :value: 'off'

      The check level used when neither the ``paranoia`` argument nor the
      ``ZANZIBAR_PARANOIA`` environment variable is set.

   .. py:attribute:: store_id
      :type: str

      The store id this store was opened on, as passed to the constructor.

   .. py:attribute:: session
      :type: sqlmodel.Session

      The session passed to the constructor. The store commits on it on open and on
      every write, and rolls it back on a refused write and in :py:meth:`refresh`, so
      give the store a session of its own.

   .. py:attribute:: sync
      :type: bool

      The ``sync`` argument: ``True`` when every write also updates the graph index,
      ``False`` when the index advances only in :py:meth:`catch_up`. It belongs to this
      instance and is not saved with the store.

   .. py:attribute:: paranoia
      :type: str

      The check level this store ended up with: ``'off'``, ``'residue'``, ``'full'`` or
      ``'fixpoint'``.

   The attributes ``widx``, ``ruleset``, ``source``, ``proc``, ``cursor`` and
   ``paranoia_guard`` are internal plumbing, not API: they may change without notice.
```

```{eval-rst}
.. autoclass:: zanzibar.ExpandResult
   :members: covers

   .. py:attribute:: keys
      :type: frozenset[tuple[str, str, str]]

      Members listed one by one, as ``(type, name, predicate)`` keys.

   .. py:attribute:: markers
      :type: frozenset[tuple[str, str]]

      ``(type, predicate)`` shapes granted through a wildcard.

   .. py:attribute:: excluded_keys
      :type: frozenset[tuple[str, str, str]]

      Keys a marker covers that are not members.
```

## Writing through the log without a Store

`TupleSource` is the write half of a `Store` on its own: it validates each write against
the schema, appends it to the tuple log and keeps an in-memory set engine current. It
does not maintain a graph index.

```{eval-rst}
.. autoclass:: zanzibar.store.TupleSource
   :members: add, remove, check, evaluator_lag

   ``TupleSource(session, store_id, *, ops=RoaringSets, ruleset=None)`` opens the store
   ``store_id``, which must already have a saved schema
   (:py:exc:`~zanzibar.StoreNotFound` otherwise). ``ops`` selects the set representation,
   as for :py:class:`~zanzibar.Store`. ``ruleset`` is a :py:class:`~zanzibar.schema.RuleSet`
   already compiled from the store's schema, to skip compiling it again. The session's
   isolation level is checked as for a ``Store``
   (:py:exc:`~zanzibar.UnsafeIsolationLevel`).

   .. py:property:: engine
      :type: zanzibar.setengine.SetEngine

      The in-memory set engine, for reads. It cannot be replaced, and writing to it
      directly raises :py:exc:`~zanzibar.UnloggedWriteRefused`: write through
      :py:meth:`add` and :py:meth:`remove`.

   .. py:method:: watermark() -> int

      The newest freshness token in this store's tuple log, as this session sees it
      (``0`` for an empty log).

   .. py:method:: catch_up_evaluator(batch=None) -> int

      Apply the committed log rows the set engine has not seen yet, and return how many
      were applied. ``batch`` caps the rows read per query (``None`` reads them in one
      query). It reads what this session's snapshot shows, so a long-lived session must
      ``rollback()`` first to see newer commits. After rolling back a write of your own,
      call :py:meth:`refresh_evaluator` instead. A row that does not fit the engine's
      state raises :py:exc:`RuntimeError`; recover with :py:meth:`refresh_evaluator`.

   .. py:method:: refresh_evaluator() -> None

      Rebuild the in-memory set engine from the stored tuples and reset its watermark to
      match. Costs time proportional to the store's size, where
      :py:meth:`catch_up_evaluator` costs time proportional to the new rows.
```

## Building and rebuilding the index offline

```{eval-rst}
.. py:function:: build_index(session, source_store_id, *, index_store_id=None, bulk=True) -> BuildReport

   Build a fresh graph index from the store's current tuples, in one transaction
   (committed on success, rolled back on failure). ``index_store_id`` defaults to
   ``source_store_id``, the index a :py:class:`~zanzibar.Store` on that id serves.
   Raises :py:exc:`~zanzibar.IndexExists` if that index already has state; use
   :py:func:`rebuild_index` to replace one in place.

   ``bulk=True`` (the default) builds the index state in one in-memory pass and writes it
   with bulk inserts. ``bulk=False`` replays the tuples one at a time through the
   incremental write path. The resulting index is the same either way.

   Returns a :py:class:`BuildReport`.
```

```{eval-rst}
.. py:function:: rebuild_index(session, source_store_id, *, index_store_id=None, bulk=True) -> BuildReport

   Throw away an existing graph index and build it again, in place, from the store's
   current tuples. This is the recovery for an index that :py:meth:`zanzibar.Store.catch_up`
   cannot advance because a logged write is refused by the index for good
   (:py:exc:`~zanzibar.PathCountExceeded`). Remove the offending tuple first
   (:py:meth:`zanzibar.Store.remove_tuple` through a ``sync=False`` instance works while
   the index is stalled; a ``sync=True`` instance refuses every write, that removal
   included, with ``PathCountExceeded``); a snapshot
   that still cannot be built is refused exactly as :py:func:`build_index` refuses it.

   It runs in one transaction under the graph index's write lock: it deletes the index's
   state, runs the same build as :py:func:`build_index`, and moves the existing cursor
   row to the new position, clearing its stall marker. Other instances see the rebuilt
   index after their next :py:meth:`~zanzibar.Store.refresh`. The delta outbox is left
   alone. On any failure nothing changes: the old index and its stall marker remain.
   Stop the store's async worker first; a write committed during the rebuild makes it
   refuse with "concurrent writes", as :py:func:`build_index` does. Returns a
   :py:class:`BuildReport`.
```

```{eval-rst}
.. py:class:: BuildReport

   What :py:func:`build_index` returns: a named tuple ``(cursor, widx, ruleset)``, so
   ``cursor, widx, ruleset = build_index(...)`` works, plus one extra attribute.

   .. py:attribute:: cursor

      The index's cursor row, at the log position the build read up to.

   .. py:attribute:: widx
      :type: zanzibar.graphindex.WildcardIndex

      The built graph index.

   .. py:attribute:: ruleset
      :type: zanzibar.schema.RuleSet

      The compiled schema.

   .. py:attribute:: constructor
      :type: str

      Which build ran: ``'bulk'`` or ``'incremental'``.
```

## The schema record and the tuple log

```{eval-rst}
.. py:function:: save_schema(session, store_id, schema_text, object_wildcard_shapes=frozenset())

   Save a store's schema (DSL text) and object-wildcard shapes, once. The schema is
   compiled first, so an invalid one is refused before anything is written. Saving the
   schema the store already has is a no-op, judged as a ``Store`` judges it on reopen
   (the same parsed schema and the same ``object_wildcard_shapes``); a different one
   raises :py:exc:`~zanzibar.SchemaMismatch`, naming the first difference. Returns a
   tuple ``(record, ruleset)``: the :py:class:`SchemaRecord` row and the compiled
   :py:class:`~zanzibar.schema.RuleSet`.
   It flushes the new row but does not commit; the caller commits the session.
```

```{eval-rst}
.. py:function:: open_set_engine(session, store_id, *, ops=DEFAULT_SETOPS, ruleset=None)

   Open a standalone :py:class:`~zanzibar.setengine.SetEngine` on a store that a
   :py:class:`~zanzibar.Store` created, using the schema saved in the database, so you
   cannot pass a different one by mistake. This is the remedy the
   :py:exc:`~zanzibar.SchemaMismatch` from ``SetEngine(session, store_id, schema)`` names.
   Raises :py:exc:`~zanzibar.StoreNotFound` when no schema is saved under ``store_id``,
   and :py:exc:`~zanzibar.PersistedSchemaRefused` when this release refuses the saved
   schema. ``ruleset`` skips recompiling a schema you already compiled; it must be that
   schema's. Public since 0.1.0.
```

```{eval-rst}
.. py:class:: SchemaRecord

   A row of the ``zanzibar_schema_record`` table: one per store, holding its schema as
   DSL text and its object-wildcard shapes. Written once, never changed. Columns:
   ``store_id``, ``schema_text``, ``object_wildcard_shapes``, ``created_at``. See the
   :doc:`../tables` page.
```

```{eval-rst}
.. py:class:: TupleLog

   A row of the ``zanzibar_tuple_log`` table: one accepted write. A row's ``id`` is the
   freshness token that write returned. Columns: ``id``, ``store_id``, ``op``,
   ``subject_predicate``, ``subject_type``, ``subject_name``, ``relation``,
   ``object_type``, ``object_name``, ``created_at``. See the :doc:`../tables` page.
```

## Constants

```{eval-rst}
.. py:data:: PARANOIA_ENV_VAR
   :type: str
   :value: 'ZANZIBAR_PARANOIA'

   The name of the environment variable that sets the runtime-check (paranoia) level
   when the ``Store`` constructor's ``paranoia`` argument is not given; an explicit
   argument always wins, and an empty value counts as unset. It accepts a level name,
   ``off``, ``residue``, ``full`` or ``fixpoint`` (case-insensitive), or a boolean word:
   ``1``, ``true``, ``yes`` and ``on`` mean ``full``; ``0``, ``false``, ``no`` and
   ``off`` mean ``off``. Any other value raises :py:exc:`ValueError`. The knob is
   described on the :doc:`../configuration` page.
```

## Exceptions

`zanzibar.store` exports no exceptions. Import them from `zanzibar`; they are documented
on the [Exceptions](../exceptions.md) page. A tokened read on a `Store` (`check`,
`lookup`, `lookup_reverse`, `expand` with `at_least=`) can raise
{py:exc}`~zanzibar.StaleRead`, {py:exc}`~zanzibar.LookupNotFresh` or
{py:exc}`~zanzibar.ForeignToken`.
