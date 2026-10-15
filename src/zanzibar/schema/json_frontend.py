"""The OpenFGA JSON front end (`parse_openfga_json`, `openfga_json_to_dsl`).

Part of `zanzibar.schema`.
"""
# Provenance (moved out of the docstring, TK123 item 14): split out of the single-file module
# by TK120 (2026-10-06).
from .errors import SchemaError
from .syntax import Computed, Direct, Exclusion, Expr, Intersection, Restriction, SchemaAST, TTU, Union
from .parser import _validate_ast_consistency, _validate_ast_references, _validate_declared_name, _validate_restriction_types_declared, _validate_stratified_negation, _validate_tuplesets_direct, parse_schema_ast
from .unparse import unparse_schema_ast


# ---- OpenFGA JSON front-end (connected-store spec §5-S5) ----
#
# The OpenFGA authorization-model JSON format is a second FRONT-END to the same
# SchemaAST -- everything downstream (taint, plans, both backends, the oracle's
# independent DSL parser via unparse) is untouched. Unsupported OpenFGA features
# (conditions, non-1.1 schema versions, unknown rewrite operators) are rejected
# loudly, never skipped.

import json as _json


def parse_openfga_json(model) -> SchemaAST:
    """Parse an OpenFGA authorization model (JSON string or dict) into a SchemaAST.

    Supports schema_version 1.1: ``this`` (with ``directly_related_user_types``
    metadata), ``computedUserset``, ``tupleToUserset``, ``union``, ``intersection``,
    ``difference``. Conditions are rejected.

    The result is refused unless the DSL `openfga_json_to_dsl` renders from it parses back
    to the same AST. Duplicate JSON keys are refused
    only for JSON TEXT input: a ``dict`` has already lost them.

    A malformed model -- a field of the wrong JSON kind, or a required key missing -- raises
    ``SchemaError`` (a ``ValueError``) naming the field, never a bare ``AttributeError`` / ``TypeError`` /
    ``KeyError``. An optional object or array given as ``null`` reads as absent.
    """
    # Provenance (moved out of the docstring, TK123 item 14): `_validate_json_round_trip`,
    # `TK115`; `TK134`.
    if isinstance(model, str):
        model = _json.loads(model, object_pairs_hook=_reject_duplicate_json_keys)
    model = _validate_json_object(model, 'the model')
    version = model.get('schema_version')
    # REFUSED SHAPE (connected-store spec §5-S5): a schema_version other than 1.1.
    # WHY: only the 1.1 format is implemented -- its ``directly_related_user_types``
    # metadata is where ``this`` gets its type restrictions (`_json_rewrite`); per the
    # front-end's header comment, unsupported features are rejected, never skipped.
    # INSTEAD: supply the model as schema 1.1, or pass its DSL to `parse_schema_ast`.
    if version != '1.1':
        raise SchemaError(f"unsupported OpenFGA schema_version {version!r} (need '1.1')")
    # REFUSED SHAPE (connected-store spec §5-S5): model-level ``conditions`` (ABAC).
    # WHY: neither backend evaluates a condition, and skipping one would let its tuples
    # grant unconditionally -- wider access than the model says.
    # INSTEAD: none -- conditions are unsupported. Where the condition is a stored fact,
    # model it as a relation: ``define viewer: [user] but not suspended``.
    if model.get('conditions'):
        raise SchemaError('OpenFGA conditions are not supported')
    _validate_json_declares_a_type(model.get('type_definitions'))
    type_definitions = _validate_json_array(model['type_definitions'], 'type_definitions')

    ast: SchemaAST = {}
    seen_types: set[str] = set()
    for i, type_def in enumerate(type_definitions):
        type_def = _validate_json_object(type_def, f'type_definitions[{i}]')
        object_type = _validate_json_field(type_def, 'type', f'type_definitions[{i}]')
        _validate_declared_name('type', object_type)
        # Same S-6 rule as the DSL front-end: a duplicate type_definitions entry
        # silently replaced the earlier one's relations -- the store then ran a
        # different schema than the operator wrote, with no error anywhere.
        # REFUSED SHAPE (blind-audit S-6): a duplicate ``type_definitions`` entry. WHY: the
        # comment above. INSTEAD: merge both entries' ``relations`` and ``metadata`` into
        # ONE type definition.
        if object_type in seen_types:
            raise SchemaError(f'duplicate type declaration: {object_type!r}')
        seen_types.add(object_type)
        where = f'type {object_type}'
        relations = _validate_json_object(
            type_def.get('relations'), f'{where}: relations', optional=True)
        metadata = _validate_json_object(
            type_def.get('metadata'), f'{where}: metadata', optional=True)
        metadata = _validate_json_object(
            metadata.get('relations'), f'{where}: metadata.relations', optional=True)
        for relation_name, rewrite in relations.items():
            # REFUSED SHAPE (boolean spec §3.2): ``.`` in a declared relation name, as in
            # the DSL front-end. WHY: ``.`` names the compiler's leaf predicates
            # (``<relation>.<index>``). INSTEAD: use ``_`` (``can_view``, not ``can.view``).
            if '.' in relation_name:
                raise SchemaError(
                    f"relation {relation_name!r}: '.' is reserved for compiled leaf "
                    f"predicates and cannot appear in a declared relation name")
            _validate_declared_name('relation', relation_name)
            rel_where = f'relation {object_type}#{relation_name}'
            rel_metadata = _validate_json_object(
                metadata.get(relation_name), f'{rel_where}: metadata', optional=True)
            restrictions = _json_restrictions(
                object_type, relation_name,
                _validate_json_array(rel_metadata.get('directly_related_user_types'),
                                     f'{rel_where}: directly_related_user_types',
                                     optional=True))
            ast[(object_type, relation_name)] = _json_rewrite(
                rewrite, object_type, relation_name, restrictions)
    # The S-5 '.'-namespace lock applies to REFERENCED names too (restriction
    # predicates, computedUserset / tupleToUserset refs) -- the DSL front-end runs
    # this in parse_schema_ast; skipping it here left a foreign write handle into
    # compiled leaf families open through JSON metadata.
    _validate_json_declares_a_relation(ast)
    _validate_ast_references(ast)
    _validate_ast_consistency(ast)
    # TK137 S8: a restriction type no type_definitions entry declares. BEFORE the round
    # trip, so a JSON typo gets the named message, not 'its DSL rendering ...'.
    _validate_restriction_types_declared(ast, frozenset(seen_types))
    _validate_tuplesets_direct(ast)
    _validate_stratified_negation(ast)
    _validate_json_round_trip(ast)
    return ast


def _validate_json_declares_a_relation(ast: SchemaAST) -> None:
    """The JSON twin of the no-relation half of `parser.py::_validate_declares_a_type`
    (`TK127` review follow-up, 2026-10-08). Without it the model was still refused, by
    `_validate_json_round_trip`, but with the misleading "DSL rendering does not parse
    (schema declares no type ...)"."""
    # REFUSED SHAPE (TK124, TK127 follow-up): type definitions none of which has a relation
    # (``[{"type": "user"}]``, or ``"relations": {}`` everywhere).
    # WHY: it is the same empty schema as no ``type_definitions`` at all (see
    # `_validate_json_declares_a_type`); a store would persist it and the id would be lost.
    # INSTEAD: give some type a relation, e.g. ``{"type": "doc", "relations": {"viewer":
    # {"this": {}}}, "metadata": {"relations": {"viewer": {"directly_related_user_types":
    # [{"type": "user"}]}}}}``.
    if not ast:
        raise SchemaError('OpenFGA JSON: the model declares no relation (no type has relations)')


def _validate_json_declares_a_type(type_definitions) -> None:
    """The JSON twin of `parser.py::_validate_declares_a_type` (`TK124`, 2026-10-08). A model
    whose types all lack relations is refused by `_validate_json_declares_a_relation`."""
    # REFUSED SHAPE (TK124): a model with no ``type_definitions`` (absent, ``null`` or ``[]``).
    # WHY: it parsed to an empty schema that a store would persist write-once and then refuse
    # every write against; the store id is lost (the DSL twin's comment has the detail).
    # INSTEAD: list the types, e.g. ``"type_definitions": [{"type": "user"}, {"type": "doc",
    # "relations": {"viewer": {"this": {}}}, "metadata": {"relations": {"viewer":
    # {"directly_related_user_types": [{"type": "user"}]}}}}]``.
    if not type_definitions:
        raise SchemaError('OpenFGA JSON: the model declares no type (no type_definitions)')


def _json_kind(value) -> str:
    """The JSON name of a Python value's kind, for refusal messages."""
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'a boolean'
    for kind, name in ((dict, 'an object'), ((list, tuple), 'an array'), (str, 'a string'),
                       ((int, float), 'a number')):
        if isinstance(value, kind):
            return name
    return type(value).__name__


def _validate_json_object(value, where: str, *, optional: bool = False) -> dict:
    """``value`` as a JSON object; ``{}`` for an absent or ``null`` OPTIONAL one (`TK134`)."""
    if value is None and optional:
        return {}
    # REFUSED SHAPE (TK134): a field the OpenFGA model format defines as an object given as
    # some other JSON kind -- the model itself as ``null`` or a list, a type definition as a
    # string, ``"relations": ["viewer"]``, a ``computedUserset`` body as a bare string.
    # WHY: the front end read these with ``.get`` / ``[...]`` and leaked a bare
    # ``AttributeError`` / ``TypeError`` that named no field. INSTEAD: the object form, e.g.
    # ``{"type": "doc", "relations": {"viewer": {"computedUserset": {"relation": "owner"}}}}``.
    if not isinstance(value, dict):
        raise SchemaError(f'OpenFGA JSON: {where} must be an object, got {_json_kind(value)}')
    return value


def _validate_json_array(value, where: str, *, optional: bool = False) -> list:
    """``value`` as a JSON array; ``[]`` for an absent or ``null`` OPTIONAL one (`TK134`)."""
    if value is None and optional:
        return []
    # REFUSED SHAPE (TK134): a field the OpenFGA model format defines as an array given as
    # some other JSON kind -- ``"type_definitions": "user"``, ``"child": null``,
    # ``"directly_related_user_types": "user"``. WHY: as for `_validate_json_object`; worse,
    # a string iterates as its characters. INSTEAD: the array form, e.g.
    # ``"directly_related_user_types": [{"type": "user"}]``.
    if not isinstance(value, (list, tuple)):
        raise SchemaError(f'OpenFGA JSON: {where} must be an array, got {_json_kind(value)}')
    return list(value)


def _validate_json_field(obj: dict, key: str, where: str) -> str:
    """The required string field ``obj[key]`` (`TK134`)."""
    # REFUSED SHAPE (TK134): a required string field that is missing or not a string -- a
    # type definition with no ``"type"``, a ``computedUserset`` with no ``"relation"``, a
    # ``tupleToUserset`` with no ``"tupleset"`` relation. WHY: the front end indexed it
    # directly and leaked a bare ``KeyError: 'type'``. INSTEAD: name it, e.g.
    # ``{"type": "doc"}``, ``{"computedUserset": {"relation": "owner"}}``.
    if key not in obj:
        raise SchemaError(f'OpenFGA JSON: {where} has no {key!r}')
    value = obj[key]
    # WHY/INSTEAD: see above.
    if not isinstance(value, str):
        raise SchemaError(
            f'OpenFGA JSON: {where}: {key!r} must be a string, got {_json_kind(value)}')
    return value


def _reject_duplicate_json_keys(pairs: list) -> dict:
    """``object_pairs_hook`` for `parse_openfga_json`: a JSON object naming one key twice is
    refused, at every depth. Plain `json.loads` keeps the LAST value silently (`TK115`)."""
    out: dict = {}
    for key, value in pairs:
        # REFUSED SHAPE (TK115): a JSON object naming the same key twice -- two ``"viewer"``
        # relations, two ``"schema_version"`` fields. WHY: `json.loads` keeps the last value
        # without a word, so the store would run a schema nobody wrote as such; the DSL twin
        # (a second ``define viewer``) is refused. INSTEAD: one entry per key -- merge the two
        # definitions, e.g. ``"viewer": {"union": {"child": [{"this": {}},
        # {"computedUserset": {"relation": "owner"}}]}}``.
        if key in out:
            raise SchemaError(f'OpenFGA JSON: duplicate key {key!r} in one object')
        out[key] = value
    return out


def _validate_json_wildcard(object_type: str, relation_name: str, entry: dict) -> bool:
    """Whether a ``directly_related_user_types`` entry is a wildcard (``[T:*]``). OpenFGA's
    ``Wildcard`` message has no fields, so its JSON is ``{}``; absent or ``null`` means not a
    wildcard (`TK115`)."""
    value = entry.get('wildcard')
    if value is None:
        return False
    # REFUSED SHAPE (TK115): ``"wildcard"`` set to anything but ``{}`` or ``null`` --
    # ``false``, ``0``, ``""``, ``{"enabled": false}``. WHY: the old test was "present and not
    # null", so ``"wildcard": false`` rendered ``[user:*]`` -- a PUBLIC grant from a value that
    # reads "not a wildcard". Canonical OpenFGA never emits these; any reading is a guess.
    # INSTEAD: ``{"type": "user", "wildcard": {}}`` for ``[user:*]``; omit the key for ``[user]``.
    if not isinstance(value, dict) or value:
        raise SchemaError(
            f'relation {object_type}#{relation_name}: "wildcard" must be {{}} or absent, '
            f'got {value!r}')
    return True


def _validate_json_round_trip(ast: SchemaAST) -> None:
    """The JSON front end's AST must survive `unparse_schema_ast` -> `parse_schema_ast`
    unchanged, so the DSL `openfga_json_to_dsl` persists IS the schema the JSON declared
    (`TK115`). The field-level checks cover declared names; this closes the class for every
    other name, e.g. a restriction type that carries a newline or a comma. Map:
    `docs/tk115-json-front-end-fidelity-2026-10-04.md`.

    Since `TK137` (2026-10-14) every such restriction type is refused EARLIER, by
    `parser.py::_validate_restriction_types_declared` (a malformed type string is never a
    declared type), so no known JSON input reaches either branch below. The guard stays as
    defence in depth for the class; its branches are pinned by direct calls in
    `tests/test_tk137_openfga_dsl_refusals.py`."""
    try:
        back = parse_schema_ast(unparse_schema_ast(ast))
    except (ValueError, TypeError) as e:
        problem = f'its DSL rendering does not parse ({e})'
    else:
        added = sorted(set(back) - set(ast))
        lost = sorted(set(ast) - set(back))
        changed = sorted(k for k in set(ast) & set(back) if ast[k] != back[k])
        problem = (None if not (added or lost or changed) else
                   f'its DSL rendering parses to a different schema '
                   f'(added {added}, lost {lost}, changed {changed})')
    # REFUSED SHAPE (TK115): a JSON model whose DSL rendering is not the same schema -- a
    # restriction ``{"type": "user]\n    define secret: [user"}`` (renders a second relation),
    # ``{"type": "user,group"}`` (renders two restrictions), ``{"type": "us er"}`` (renders text
    # the DSL parser refuses). WHY: `openfga_json_to_dsl` output is the persisted schema
    # source, so the store would run a schema the JSON never declared, and admit writes on a
    # relation it never had. INSTEAD: use names inside the write charset in every field, e.g.
    # ``{"type": "user"}``.
    if problem is not None:
        raise SchemaError(f'OpenFGA JSON: {problem}')


def _json_restrictions(object_type: str, relation_name: str,
                       entries: list) -> tuple[Restriction, ...]:
    out = []
    where = f'relation {object_type}#{relation_name}: directly_related_user_types'
    for i, e in enumerate(entries):
        e = _validate_json_object(e, f'{where}[{i}]')
        restricted_type = _validate_json_field(e, 'type', f'{where}[{i}]')
        # REFUSED SHAPE: a conditional type restriction,
        # ``{"type": "user", "condition": ...}``. WHY: conditions are unsupported
        # (`parse_openfga_json`); dropping one would make the restriction unconditional --
        # wider access than the model says.
        # INSTEAD: none -- remove ``condition`` only if the unconditional grant is what is
        # meant, or model the condition as a relation (``[user] but not suspended``).
        if e.get('condition'):
            raise SchemaError(
                f'relation {object_type}#{relation_name}: conditional type '
                f'restrictions are not supported')
        predicate = (_validate_json_field(e, 'relation', f'{where}[{i}]')
                     if e.get('relation') is not None else '') or '...'
        wildcard = _validate_json_wildcard(object_type, relation_name, e)
        out.append(Restriction(type=restricted_type, predicate=predicate, wildcard=wildcard))
    return tuple(out)


def _json_rewrite(node: dict, object_type: str, relation_name: str,
                  restrictions: tuple[Restriction, ...]) -> Expr:
    """One OpenFGA userset-rewrite node -> Expr. ``this`` means "the directly
    related tuples" -- the same restriction set wherever it appears in the tree."""
    if not isinstance(node, dict) or len(node) != 1:
        raise SchemaError(
            f'relation {object_type}#{relation_name}: rewrite node must have exactly '
            f'one operator, got {node!r}')
    kind, body = next(iter(node.items()))
    where = f'relation {object_type}#{relation_name}: {kind}'
    if kind in ('computedUserset', 'tupleToUserset', 'union', 'intersection', 'difference'):
        body = _validate_json_object(body, where)

    if kind == 'this':
        # REFUSED SHAPE: ``this`` with no ``directly_related_user_types`` metadata.
        # WHY: with no type restrictions ``this`` admits no subject type, so the arm could
        # never hold a tuple. INSTEAD: add the metadata on the type definition, e.g.
        # ``"metadata": {"relations": {"viewer": {"directly_related_user_types": [{"type":
        # "user"}]}}}``.
        if not restrictions:
            raise SchemaError(
                f'relation {object_type}#{relation_name}: `this` requires '
                f'directly_related_user_types metadata')
        return Direct(restrictions)
    if kind == 'computedUserset':
        return Computed(_validate_json_field(body, 'relation', where))
    if kind == 'tupleToUserset':
        target = _validate_json_object(body.get('computedUserset'), f'{where}.computedUserset')
        tupleset = _validate_json_object(body.get('tupleset'), f'{where}.tupleset')
        return TTU(target_rel=_validate_json_field(target, 'relation', f'{where}.computedUserset'),
                   tupleset_rel=_validate_json_field(tupleset, 'relation', f'{where}.tupleset'))
    if kind in ('union', 'intersection'):
        children = tuple(_json_rewrite(c, object_type, relation_name, restrictions)
                         for c in _validate_json_array(body.get('child'), f'{where}.child'))
        if not children:
            raise SchemaError(
                f'relation {object_type}#{relation_name}: empty {kind} child list')
        if len(children) == 1:
            # a single-child operator must collapse: Union((x,)) unparses to text
            # that reparses as x, breaking the round-trip contract (blind-audit S-7)
            return children[0]
        return Union(children) if kind == 'union' else Intersection(children)
    if kind == 'difference':
        return Exclusion(
            _json_rewrite(_validate_json_object(body.get('base'), f'{where}.base'),
                          object_type, relation_name, restrictions),
            _json_rewrite(_validate_json_object(body.get('subtract'), f'{where}.subtract'),
                          object_type, relation_name, restrictions))
    # REFUSED SHAPE (connected-store spec §5-S5): an unknown rewrite operator.
    # WHY: only the six operators above are implemented, and skipping an unknown node would
    # silently drop an arm (the front-end's header comment: rejected, never skipped).
    # INSTEAD: none -- use ``this``, ``computedUserset``, ``tupleToUserset``, ``union``,
    # ``intersection`` or ``difference`` (a misspelt key such as ``computedUserSet`` lands
    # here too).
    raise SchemaError(
        f'relation {object_type}#{relation_name}: unsupported rewrite operator {kind!r}')


def openfga_json_to_dsl(model) -> str:
    """OpenFGA JSON -> canonical DSL text (the persistable schema source): parse to
    the shared AST, render through the round-trip-safe unparser."""
    return unparse_schema_ast(parse_openfga_json(model))
