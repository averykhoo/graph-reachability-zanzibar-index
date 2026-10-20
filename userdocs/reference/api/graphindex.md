# zanzibar.graphindex

The graph index precomputes who can reach what, so a check is a few indexed lookups
whatever the size of the data, and writes pay to keep that precomputation current. A
{py:class}`zanzibar.Store` owns one and keeps it in step with the tuple log; use this
package directly only to drive the graph index on its own, as described in
[Use the backends directly](../../how-to/backends-direct.md).

```{eval-rst}
.. py:module:: zanzibar.graphindex
```

## Lookup results

`LookupResult` is importable from both `zanzibar` and `zanzibar.graphindex`; it is
documented here under its top-level name. The marker and exclusion fields are summarised
on the [Python API](index.md#result-markers) page.

```{eval-rst}
.. autoclass:: zanzibar.LookupResult

   .. py:attribute:: node_ids
      :type: set[int]

      Ids of :py:class:`~zanzibar.graphindex.Node` rows.

   .. py:attribute:: markers
      :type: set[tuple[str, str, str]]

      Wildcard grants as ``(type, predicate, variant)`` triples.

   .. py:attribute:: excluded_node_ids
      :type: set[int]

      Node ids a marker would cover but that are refused.

   .. py:attribute:: implicit_keys
      :type: set[tuple[str, str, str]]

      Results that have no node, as ``(type, name, predicate)`` keys.

   .. py:attribute:: implicit_excluded_keys
      :type: set[tuple[str, str, str]]

      Exclusions that have no node, as keys.
```

## The index

In the method signatures below, `subject_predicate` is `"..."` (or `Ellipsis`) for a bare
subject such as a user, or the relation of a userset subject (`"member"` for
`group:eng#member`).

Some of these signatures take or return types that are not public: the `schema_info`
object, and the triple that {py:meth}`zanzibar.schema.RuleSet.apply` takes. Take them from a
compiled `RuleSet` (`ruleset.schema_info`) rather than building them yourself; they are
internal, undocumented, and may change in any release.

```{eval-rst}
.. py:class:: WildcardIndex(idx, schema_info)

   The graph index, on top of a :py:class:`ReachabilityIndex` ``idx``, for the schema
   whose :py:attr:`zanzibar.schema.RuleSet.schema_info` is ``schema_info``. It handles
   wildcard subjects and objects, and relations that use ``and`` / ``but not`` (which a
   :py:class:`DeltaProcessor` maintains). It never commits: the caller commits the
   session.

   .. py:attribute:: idx
      :type: ReachabilityIndex

      The underlying index. ``idx.store_id`` is the store id.

   .. py:method:: add_tuple(subject_predicate, subject_type, subject_name, relation, object_type, object_name) -> None

      Add one edge produced by :py:meth:`zanzibar.schema.RuleSet.apply`. Edges are
      counted: adding the same edge twice takes two removes to undo. This is not a
      raw-tuple write; deduplicate raw tuples yourself, and route each one through
      ``RuleSet.apply`` first.

   .. py:method:: remove_tuple(subject_predicate, subject_type, subject_name, relation, object_type, object_name) -> None

      Remove one count of an edge added with :py:meth:`add_tuple`. Removing an edge
      whose endpoints the index has never seen raises
      :py:exc:`~zanzibar.AdmissionRejected`.

   .. py:method:: check(subject_predicate, subject_type, subject_name, relation, object_type, object_name) -> bool

      Is the subject related to the object? A relation name the schema does not declare
      answers ``False``; it does not raise.

   .. py:method:: lookup(subject_predicate, subject_type, subject_name) -> zanzibar.LookupResult

      Everything the subject can reach. Wildcard objects reached become markers, never
      listed one by one.

   .. py:method:: lookup_reverse(relation, object_type, object_name) -> zanzibar.LookupResult

      Everything that can reach the object with ``relation``. Wildcard subjects become
      markers, and the subjects a marker covers but that are refused are in
      ``excluded_node_ids``.

   .. py:method:: filter_result(res, entity_type=None, predicate=None) -> zanzibar.LookupResult

      A copy of a :py:meth:`lookup` or :py:meth:`lookup_reverse` result that keeps only
      the entries (node ids, markers, excluded ids and implicit keys) whose
      ``(type, predicate)`` matches every filter given. With both filters ``None`` it
      returns ``res`` itself. Use it before the next write: an id whose node is gone
      raises :py:exc:`~zanzibar.StaleLookupIds`.

   .. py:method:: remove_node(predicate, entity_type, name) -> None

      Remove a node and all its edges. It raises :py:exc:`~zanzibar.AdmissionRejected`,
      and changes nothing, for a node that does not exist, a wildcard node (name
      ``"*"``), a node that an ``and`` / ``but not`` relation's stored state refers to,
      and a node of a shape that the schema's rewrites store copies of.

   .. py:method:: backfill() -> None

      Create any wildcard bookkeeping missing for the nodes already stored. Idempotent.
```

```{eval-rst}
.. py:class:: ReachabilityIndex(session, store_id, *, max_closure_fanout=None)

   The stored transitive closure for one store id, read and written through
   ``session``. A :py:class:`WildcardIndex` wraps one; its remaining methods are the
   closure's low-level node and edge operations, which :py:class:`WildcardIndex` calls
   and which are not documented here.

   ``max_closure_fanout`` caps how many closure rows one edge addition may create
   (:py:exc:`~zanzibar.ClosureFanoutExceeded` above it). ``None`` reads the
   ``ZANZIBAR_MAX_CLOSURE_FANOUT`` environment variable, and falls back to 100,000 when
   it is unset or empty. ``0`` disables the cap. A negative value, or an environment
   value that is not an integer, raises :py:exc:`ValueError`. The value is fixed when the
   index is constructed. See :doc:`../configuration`.

   .. py:attribute:: store_id
      :type: str

   .. py:attribute:: max_closure_fanout
      :type: int

      The cap in force (``0`` when disabled).

   .. py:method:: fanout_cap_suspended()

      A context manager. Inside it, edge additions in the current thread that exceed
      ``max_closure_fanout`` are applied with a logged warning instead of being refused.
      The path-count limit (:py:exc:`~zanzibar.PathCountExceeded`) still applies. It can
      be nested, and restores the previous setting on exit.
```

```{eval-rst}
.. autoclass:: zanzibar.graphindex.DeltaProcessor

   .. py:method:: run_cascade(txn_start_watermark) -> None

      Bring every ``and`` / ``but not`` relation up to date with the edge writes made in
      this transaction. ``txn_start_watermark`` is :py:func:`outbox_watermark` read
      before those writes. Call it in the same transaction, after the writes and before
      the commit.

   .. py:method:: backfill(chunk_size=200) -> None

      Rebuild every derived relation from the edges already stored. Idempotent; use it
      to bootstrap a processor on an existing index, or to repair derived state.
```

## Outbox retention

Every change in reachability writes a row to the `zanzibar_delta_outbox` table, which the
delta processor reads. Nothing deletes those rows for you.

```{eval-rst}
.. autofunction:: zanzibar.graphindex.outbox_watermark
```

```{eval-rst}
.. py:function:: prune_outbox(session, store_id, before_watermark) -> int

   Delete this store's outbox rows with an id at or below ``before_watermark``, and
   return how many were deleted. Pass the lowest outbox position any reader of the
   outbox still needs; with one synchronous cascade per write, that is
   :py:func:`outbox_watermark` read after the last commit. Rows above
   ``before_watermark`` are never touched. The newest row is always kept, so outbox ids
   keep increasing and :py:func:`outbox_watermark` returns the same value after a prune.
   A negative ``before_watermark`` raises :py:exc:`ValueError`. The library never calls
   this. It does not commit: run it in its own transaction and commit.
```

## Tables

The tables these row classes map are listed on the [Database tables](../tables.md) page.

```{eval-rst}
.. py:class:: IndexStore

   A row of the ``zanzibar_store`` table: one per graph index store id. Columns: ``id``,
   ``description``, ``created_at``.

.. py:class:: Node

   A row of the ``zanzibar_node`` table: an entity, a userset or a relation on an object.
   Columns: ``id``, ``store_id``, ``predicate``, ``type``, ``name``, ``wildcard``,
   ``implicit``, ``reference_count``.

.. py:class:: Edge

   A row of the ``zanzibar_edge`` table: one pair in the precomputed closure, with its
   reference counts. Columns: ``id``, ``store_id``, ``subject_id``, ``object_id``,
   ``direct_edge_count``, ``indirect_edge_count``, ``derived``.
```

## Exceptions re-exported here

These are the same classes as the top-level names and are documented on the
[Exceptions](../exceptions.md) page: {py:exc}`~zanzibar.AdmissionRejected`,
{py:exc}`~zanzibar.InvariantViolation` and {py:exc}`~zanzibar.WriteLockUnsafe`. The graph
index also raises {py:exc}`~zanzibar.ClosureFanoutExceeded`,
{py:exc}`~zanzibar.PathCountExceeded` and {py:exc}`~zanzibar.StaleLookupIds`, which this
subpackage does not re-export; import them from `zanzibar`.
