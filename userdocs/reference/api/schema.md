# zanzibar.schema

Parsing, converting and compiling schemas. Both backends use this layer. The language it
accepts is described on the [Schema language](../schema-language.md) page, and the shapes
it refuses on the [Refused schema shapes](../refused-shapes.md) page.

```{eval-rst}
.. py:module:: zanzibar.schema
```

## Parsing a schema

`parse_openfga_schema` is importable from both `zanzibar` and `zanzibar.schema`; it is
documented here under its top-level name.

```{eval-rst}
.. autofunction:: zanzibar.parse_openfga_schema
```

```{eval-rst}
.. py:function:: parse_schema_ast(schema)

   Parse OpenFGA DSL text into a :py:data:`SchemaAST`, without compiling it. The accepted
   language is described on the :doc:`../schema-language` page. A schema with a
   syntax error, a reference to an undeclared relation or type, or a cycle of computed or
   tuple-to-userset references raises :py:exc:`~zanzibar.SchemaError` or a subclass
   (see :doc:`../refused-shapes`). ``and`` and ``but not`` are accepted here.
```

```{eval-rst}
.. py:function:: unparse_schema_ast(ast)

   Render a :py:data:`SchemaAST` back to DSL text (a ``str``), such that
   ``parse_schema_ast(unparse_schema_ast(a)) == a`` for every AST that
   :py:func:`parse_schema_ast` can produce. The empty AST renders as ``""``, which the
   parser refuses. Both operands of ``but not`` are parenthesised when they are
   operators (``Exclusion(Union(a, b), c)`` renders as ``(a or b) but not c``), and every
   type that is used in a restriction but has no relations gets its own ``type`` line
   first, sorted.
```

## OpenFGA JSON models

```{eval-rst}
.. autofunction:: zanzibar.schema.parse_openfga_json
```

```{eval-rst}
.. autofunction:: zanzibar.schema.openfga_json_to_dsl
```

## Compiling for the graph index

```{eval-rst}
.. py:function:: compile_ruleset(ast, schema_info, *, enable_boolean=True, declared_types=frozenset()) -> RuleSet

   Compile a :py:data:`SchemaAST` into a :py:class:`RuleSet`. Most programs call
   :py:func:`zanzibar.parse_openfga_schema`, which parses, derives ``schema_info`` and
   calls this function. Relations that use ``and`` or ``but not`` compile into derived
   relations, maintained by the graph index's delta processor; with
   ``enable_boolean=False`` the first such operator raises
   :py:exc:`~zanzibar.UnsupportedByGraphIndex` instead. A cycle among derived relations
   raises :py:exc:`~zanzibar.CyclicDerivedDependency`. ``declared_types`` (the schema's
   ``type`` lines) changes only the wording of a later admission refusal.
```

```{eval-rst}
.. py:class:: RuleSet

   A compiled schema, as returned by :py:func:`zanzibar.parse_openfga_schema`. A
   dataclass. Pass it as ``ruleset=`` to :py:class:`~zanzibar.setengine.SetEngine` or
   :py:class:`~zanzibar.store.TupleSource` to skip compiling the same schema again.

   .. py:attribute:: schema_info

      The wildcard and derived-relation facts the graph index needs. Pass it to
      :py:class:`~zanzibar.graphindex.WildcardIndex`.

   .. py:attribute:: compiled

      The compiled ``and`` / ``but not`` relations, or ``None``. Pass it to
      :py:class:`~zanzibar.graphindex.DeltaProcessor`. A schema needs a delta processor
      when ``compiled`` is not ``None`` and ``compiled.plans`` is not empty.

   .. py:attribute:: rules_and_filters

      The compiled routing rules, in order.

   .. py:method:: apply(relational_triple)

      Route one raw tuple through the schema: yield every edge the graph index must
      store for it. A tuple the schema does not admit raises
      :py:exc:`~zanzibar.AdmissionRejected`. It takes a ``RelationalTriple``, which is
      importable from ``zanzibar.schema`` but is not public; see
      :doc:`../../how-to/backends-direct`.
```

## The schema AST

{py:func}`~zanzibar.schema.parse_schema_ast` returns a `SchemaAST`. Each relation's
definition is an expression built from the node classes below. All the node classes are
frozen dataclasses, so they are hashable and compare by value.

```{eval-rst}
.. py:data:: SchemaAST
   :value: dict[tuple[str, str], Expr]

   A parsed schema: a plain ``dict`` mapping ``(object_type, relation)`` to the
   :py:data:`Expr` that defines that relation. It is a type alias, not a class.

.. py:data:: Expr
   :value: Union | Intersection | Exclusion | Direct | Computed | TTU

   The type of one relation definition: any of the node classes below. ``Direct``,
   ``Computed`` and ``TTU`` are leaves; ``Union`` (``or``), ``Intersection`` (``and``)
   and ``Exclusion`` (``but not``) combine other expressions.
```

```{eval-rst}
.. py:class:: Direct(restrictions)

   A ``[...]`` direct type-restriction list, for example ``[user, group#member, user:*]``.

   .. py:attribute:: restrictions
      :type: tuple[Restriction, ...]

.. py:class:: Restriction(type, predicate, wildcard)

   One entry of a ``[...]`` type-restriction list.

   .. py:attribute:: type
      :type: str

   .. py:attribute:: predicate
      :type: str

      ``'...'`` for a bare entity (``[user]``), or a relation name for a userset
      (``[group#member]``).

   .. py:attribute:: wildcard
      :type: bool

      ``True`` for ``T:*`` and ``T:*#P``.

.. py:class:: Computed(relation)

   A computed userset: ``define viewer: editor`` is ``Computed('editor')``.

   .. py:attribute:: relation
      :type: str

.. py:class:: TTU(target_rel, tupleset_rel)

   Tuple-to-userset: ``define viewer: viewer from parent`` is ``TTU('viewer', 'parent')``.

   .. py:attribute:: target_rel
      :type: str

   .. py:attribute:: tupleset_rel
      :type: str

.. py:class:: Union(children)

   ``a or b or ...``.

   .. py:attribute:: children

      A tuple of :py:data:`Expr`.

.. py:class:: Intersection(children)

   ``a and b and ...``.

   .. py:attribute:: children

      A tuple of :py:data:`Expr`.

.. py:class:: Exclusion(base, subtract)

   ``base but not subtract``.

   .. py:attribute:: base

      An :py:data:`Expr`.

   .. py:attribute:: subtract

      An :py:data:`Expr`.
```

```python
from zanzibar.schema import Computed, Direct, Exclusion, Restriction, parse_schema_ast

ast = parse_schema_ast("""
model
  schema 1.1
type user
type doc
  relations
    define owner: [user]
    define banned: [user]
    define viewer: owner but not banned
""")
print(ast[("doc", "owner")] == Direct((Restriction("user", "...", False),)))  # -> True
print(ast[("doc", "viewer")] == Exclusion(Computed("owner"), Computed("banned")))  # -> True
```

## Identifiers

The identifier rules are described on the
[Tuple strings and identifiers](../tuple-strings.md) page.

```{eval-rst}
.. py:data:: IDENTIFIER_CHARSET
   :type: str
   :value: 'A-Za-z0-9_./@+=-'

   The characters an identifier may use, written as the inside of a regular-expression
   character class. An identifier is 1 to 256 of these characters.

.. py:function:: is_valid_identifier(value) -> bool

   ``True`` if ``value`` is a string of 1 to 256 characters from
   :py:data:`IDENTIFIER_CHARSET`, and ``False`` for anything else, including a
   non-string. It checks the characters only: ``'*'`` returns ``False``, and ``'...'``
   returns ``True`` because ``.`` is in the character set. Where the reserved names
   ``*`` and ``...`` are accepted is described on the :doc:`../tuple-strings` page.

.. py:function:: validate_store_id(store_id, label='store_id') -> None

   Raise :py:exc:`~zanzibar.AdmissionRejected` unless ``store_id`` is a ``str`` with at
   least one non-whitespace character. The identifier character set does not apply to
   store ids. ``label`` names the argument in the error message.
```

## Exceptions re-exported here

These are the same classes as the top-level names and are documented on the
[Exceptions](../exceptions.md) page:
{py:exc}`~zanzibar.ZanzibarError`, {py:exc}`~zanzibar.SchemaError`,
{py:exc}`~zanzibar.ShapeNoLongerAccepted`, {py:exc}`~zanzibar.AdmissionRejected`,
{py:exc}`~zanzibar.IndexResourceLimit`, {py:exc}`~zanzibar.ClosureFanoutExceeded`,
{py:exc}`~zanzibar.PathCountExceeded`, {py:exc}`~zanzibar.UnsupportedByGraphIndex`,
{py:exc}`~zanzibar.DoublyBridgedShapeError`, {py:exc}`~zanzibar.CyclicDerivedDependency`,
{py:exc}`~zanzibar.SchemaMismatch`, {py:exc}`~zanzibar.PersistedSchemaRefused`,
{py:exc}`~zanzibar.MalformedTupleString` and the warning
{py:exc}`~zanzibar.UnprovenExtensionWarning`.
