# zanzibar.setengine

The set engine stores only the raw tuples and computes every answer when it is asked,
with bitmap algebra. A {py:class}`zanzibar.Store` keeps one beside the graph index; use
this package directly only to run the set engine on its own.

```{eval-rst}
.. py:module:: zanzibar.setengine
```

## The engine

```{eval-rst}
.. autoclass:: zanzibar.setengine.SetEngine
   :members: rebuild, check, lookup, filter_result, result_keys, excluded_keys

   ``SetEngine(session, store_id, schema=None, *, object_wildcard_shapes=frozenset(),
   ops=RoaringSets, ruleset=None)`` opens the set engine on ``store_id`` and replays its
   stored tuples. ``schema`` is OpenFGA DSL text. It may be left out for a store a
   :py:class:`~zanzibar.Store` created: the engine then reads the saved schema and its
   object-wildcard shapes. Leaving it out for a store with no saved schema raises
   :py:exc:`TypeError`. ``ops`` selects the set representation (:py:data:`RoaringSets` or
   :py:data:`PySets`); ``ruleset`` is an already-compiled
   :py:class:`~zanzibar.schema.RuleSet` for the same schema, to skip compiling it again.

   .. py:method:: add_tuple(subject_predicate, subject_type, subject_name, relation, object_type, object_name) -> bool

      Add one raw tuple. Returns ``True`` if it was added, ``False`` if it was already
      stored (nothing changes). ``subject_predicate`` is ``"..."`` for a bare subject.
      Does not commit. A tuple the schema does not admit raises
      :py:exc:`~zanzibar.AdmissionRejected` (a :py:exc:`ValueError`) before anything
      changes. On a store that a ``Store`` or a :py:class:`~zanzibar.store.TupleSource`
      governs, it raises :py:exc:`~zanzibar.UnloggedWriteRefused`.

   .. py:method:: remove_tuple(subject_predicate, subject_type, subject_name, relation, object_type, object_name) -> None

      Remove one raw tuple. Does not commit. A tuple that is not stored, or one the
      schema does not admit, raises :py:exc:`~zanzibar.AdmissionRejected` (a
      :py:exc:`ValueError`) before anything changes. On a
      store that a ``Store`` or a ``TupleSource`` governs, it raises
      :py:exc:`~zanzibar.UnloggedWriteRefused`.

   .. py:method:: lookup_reverse(relation, object_type, object_name) -> SetLookupResult

      Every subject that has ``relation`` on the object. Concrete subjects are in
      ``node_ids``; a subject wildcard grant is a ``(type, predicate)`` marker, never
      listed subject by subject; subjects a marker covers but that are refused are in
      ``excluded_node_ids``. Read the ids with :py:meth:`result_keys` and
      :py:meth:`excluded_keys`.

   .. py:method:: expand(relation, o_type, o_name) -> MemberSet

      The member set of the relation on the object, as a :py:class:`MemberSet`. Its ids
      are the engine's internal handles and are not checked for staleness; to get keys,
      use :py:meth:`lookup_reverse` with :py:meth:`result_keys` and
      :py:meth:`excluded_keys`, or :py:meth:`zanzibar.Store.expand`.
```

```{eval-rst}
.. py:class:: SetLookupResult(node_ids=set(), markers=set(), excluded_node_ids=set(), implicit_keys=set(), implicit_excluded_keys=set())

   What :py:meth:`SetEngine.lookup` and :py:meth:`SetEngine.lookup_reverse` return. A
   dataclass: build one by keyword and compare with ``==``.

   ``node_ids`` and ``excluded_node_ids`` are ids local to the engine instance that
   produced the result. Translate them with :py:meth:`SetEngine.result_keys` and
   :py:meth:`SetEngine.excluded_keys` on that same instance, before the next write: once
   any id has been freed (by a remove, or a catch-up that applies one), the engine has been
   rebuilt, or the result came from another instance, both raise
   :py:exc:`~zanzibar.StaleLookupIds`.

   .. py:attribute:: node_ids
      :type: set[int]

      The concrete results.

   .. py:attribute:: markers
      :type: set[tuple[str, str]]

      Wildcard grants as ``(type, predicate)`` pairs. Unlike
      :py:attr:`zanzibar.LookupResult.markers`, these have no third field.

   .. py:attribute:: excluded_node_ids
      :type: set[int]

      Ids a marker would cover but that are refused (by a ``but not`` or an ``and``).

   .. py:attribute:: implicit_keys
      :type: set[tuple[str, str, str]]

      Results that have no id, as ``(type, name, predicate)`` keys: for example
      ``doc:1#viewer`` is a viewer of ``doc:1`` even on an empty store.
      :py:meth:`SetEngine.result_keys` includes them.

   .. py:attribute:: implicit_excluded_keys
      :type: set[tuple[str, str, str]]

      Exclusions that have no id, as keys. :py:meth:`SetEngine.excluded_keys` includes
      them.
```

```{eval-rst}
.. py:class:: MemberSet

   What :py:meth:`SetEngine.expand` returns: a set of members that can include "every
   subject of a shape". A frozen dataclass. The ids in it are the engine's internal
   handles.

   .. py:attribute:: pos

      Ids of the members listed one by one.

   .. py:attribute:: stars
      :type: frozenset[tuple[str, str]]

      ``(type, predicate)`` shapes of which every subject is a member (``predicate`` is
      ``"..."`` for a bare subject).

   .. py:attribute:: neg

      Ids a shape in ``stars`` covers that are not members.

   .. py:attribute:: ipos
      :type: frozenset[tuple[str, str, str]]

      Members that have no id, as ``(type, name, predicate)`` keys.

   .. py:attribute:: ineg
      :type: frozenset[tuple[str, str, str]]

      Keys a shape in ``stars`` covers that are not members.

   .. py:method:: contains_star(shape) -> bool

      Is ``shape`` in ``stars``?

   .. py:method:: contains_entity(uid, utype) -> bool

      Is the bare subject with id ``uid`` and type ``utype`` a member?

   .. py:method:: contains_userset(uid, shape) -> bool

      Is the userset with id ``uid`` and shape ``shape`` a member?

   .. py:method:: contains_key(key) -> bool

      Is the ``(type, name, predicate)`` key, which has no id, a member: in ``ipos``, or
      covered by a shape in ``stars`` and not in ``ineg``?
```

## Stored tuples

```{eval-rst}
.. py:class:: RelationTuple

   A row of the ``zanzibar_relation_tuple`` table: one currently stored tuple.
   ``subject_predicate`` is ``'...'`` for a bare subject. Columns: ``id``, ``store_id``,
   ``subject_predicate``, ``subject_type``, ``subject_name``, ``relation``,
   ``object_type``, ``object_name``, ``created_at``. See the :doc:`../tables` page.
```

## Set implementations

```{eval-rst}
.. py:class:: SetOps

   The set representation the engine uses for its id sets. Pass one of the two instances
   below as ``ops``; answers are the same with either.

   .. py:attribute:: name
      :type: str

      ``'roaring'`` or ``'py'``.

.. py:data:: RoaringSets
   :type: SetOps

   Compressed bitmaps (``pyroaring``). The default.

.. py:data:: PySets
   :type: SetOps

   Python's built-in ``set`` and ``frozenset``.
```

## Exceptions re-exported here

These are the same classes as the top-level names and are documented on the
[Exceptions](../exceptions.md) page: {py:exc}`~zanzibar.UnloggedWriteRefused` and
{py:exc}`~zanzibar.StaleLookupIds`. The set engine also raises
{py:exc}`~zanzibar.AdmissionRejected`, {py:exc}`~zanzibar.SchemaMismatch` and
{py:exc}`~zanzibar.PersistedSchemaRefused`, which this subpackage does not re-export;
import them from `zanzibar`.
