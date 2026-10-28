"""The schema AST (`Direct`/`Computed`/`TTU`/`Union`/`Intersection`/`Exclusion`) and walkers over it.

Part of `zanzibar.schema`.
"""
# Provenance (moved out of the docstring, TK123 item 14): split out of the single-file module
# by TK120 (2026-10-06).
from dataclasses import dataclass


# ---- leaves ----

@dataclass(frozen=True, slots=True)
class Restriction:
    """One entry of a ``[...]`` type-restriction list.

    ``predicate`` is ``'...'`` for a bare entity (``[user]``) or a relation name for a
    userset (``[group#member]``). ``wildcard`` is True for ``T:*`` / ``T:*#P``.
    """
    type: str
    predicate: str
    wildcard: bool = False


@dataclass(frozen=True, slots=True)
class Direct:
    """A ``[...]`` direct type-restriction list, e.g. ``[user, group#member, user:*]``."""
    restrictions: tuple[Restriction, ...]


@dataclass(frozen=True, slots=True)
class Computed:
    """A computed userset: ``define viewer: editor`` -> ``Computed('editor')``."""
    relation: str


@dataclass(frozen=True, slots=True)
class TTU:
    """Tuple-to-userset: ``define viewer: viewer from parent`` -> ``TTU('viewer', 'parent')``."""
    target_rel: str
    tupleset_rel: str


# ---- operators ----

@dataclass(frozen=True, slots=True)
class Union:
    """``a or b`` -> ``Union((a, b))``."""
    children: tuple['Expr', ...]


@dataclass(frozen=True, slots=True)
class Intersection:
    """``a and b`` -> ``Intersection((a, b))``."""
    children: tuple['Expr', ...]


@dataclass(frozen=True, slots=True)
class Exclusion:
    """``base but not subtract`` -> ``Exclusion(base, subtract)``."""
    base: 'Expr'
    subtract: 'Expr'


Expr = Union | Intersection | Exclusion | Direct | Computed | TTU
SchemaAST = dict[tuple[str, str], Expr]     # (object_type, relation) -> Expr


_RESERVED = ('or', 'and', 'but', 'not', 'from')


def _iter_directs(expr: Expr):
    if isinstance(expr, Direct):
        yield expr
    elif isinstance(expr, (Union, Intersection)):
        for c in expr.children:
            yield from _iter_directs(c)
    elif isinstance(expr, Exclusion):
        yield from _iter_directs(expr.base)
        yield from _iter_directs(expr.subtract)
    # Computed / TTU carry no direct restrictions


def _iter_ttus(expr: Expr):
    if isinstance(expr, TTU):
        yield expr
    elif isinstance(expr, (Union, Intersection)):
        for c in expr.children:
            yield from _iter_ttus(c)
    elif isinstance(expr, Exclusion):
        yield from _iter_ttus(expr.base)
        yield from _iter_ttus(expr.subtract)
    # Direct / Computed contain no TTUs


def _directs_only(expr: Expr) -> bool:
    if isinstance(expr, Direct):
        return True
    if isinstance(expr, Union):
        return all(_directs_only(c) for c in expr.children)
    return False


# ---- user-facing explanations (TK123 items 17, 18) ----

def _render_restriction(r: Restriction) -> str:
    name = f'{r.type}:*' if r.wildcard else r.type
    return name if r.predicate == '...' else f'{name}#{r.predicate}'


@dataclass(frozen=True, slots=True)
class DeclaredRelations:
    """What a schema declares, for admission messages: the known types (object types
    plus every type a restriction names), each type's relation names, and each
    ``(type, relation)``'s direct restrictions rendered (empty = computed only)."""
    types: frozenset[str]
    relations: dict[str, tuple[str, ...]]
    restrictions: dict[tuple[str, str], tuple[str, ...]]


def declared_relations(ast: SchemaAST,
                       declared_types: frozenset[str] = frozenset()) -> DeclaredRelations:
    # ``declared_types``: the ``type`` lines of the source text, when the caller parsed one
    # (`parser.py::_parse_schema_ast_checked`). Without it a relation-less ``type folder``
    # that no restriction names was reported as "not declared in the schema" (TK153
    # review, 2026-10-17); with it the reason is "declares no relations".
    relations: dict[str, list[str]] = {}
    restrictions: dict[tuple[str, str], tuple[str, ...]] = {}
    types: set[str] = set(declared_types)
    for (t, rel), expr in ast.items():
        types.add(t)
        relations.setdefault(t, []).append(rel)
        rs = [r for d in _iter_directs(expr) for r in d.restrictions]
        types.update(r.type for r in rs)
        restrictions[(t, rel)] = tuple(dict.fromkeys(_render_restriction(r) for r in rs))
    return DeclaredRelations(frozenset(types),
                             {t: tuple(sorted(rs)) for t, rs in relations.items()},
                             restrictions)


def no_restriction_reason(declared: 'DeclaredRelations | None', object_type: str,
                          relation: str) -> str:
    """Why no declared type restriction admits a tuple on ``object_type#relation``:
    an undeclared type, an undeclared relation (with a did-you-mean), a relation that is
    computed only, or a subject outside the declared restrictions. One wording for both
    backends, so their refusals stay identical."""
    import difflib
    if declared is None:
        return ''
    if object_type not in declared.types:
        near = difflib.get_close_matches(object_type, sorted(declared.types), n=1)
        hint = f"; did you mean {near[0]!r}?" if near else ''
        return f": type {object_type!r} is not declared in the schema{hint}"
    rels = declared.relations.get(object_type, ())
    if relation not in rels:
        if not rels:
            return f": type {object_type!r} declares no relations"
        near = difflib.get_close_matches(relation, rels, n=1)
        hint = f"did you mean {near[0]!r}?" if near else f"it declares {', '.join(rels)}"
        return f": type {object_type!r} declares no relation {relation!r}; {hint}"
    allowed = declared.restrictions.get((object_type, relation), ())
    if not allowed:
        return (f": {object_type}#{relation} has no direct type restriction (it is "
                f"computed from other relations), so tuples cannot be written to it")
    return f": it admits only {', '.join(allowed)}"


def no_restriction_message(declared: 'DeclaredRelations | None', tuple_text: str,
                           object_type: str, relation: str, *, derived: bool = False) -> str:
    """The whole admission refusal for a tuple no declared type restriction admits, the
    same on both backends. A write to a relation the schema does not declare (or on an
    undeclared type) says so first -- ``names an undeclared relation doc#vewer`` -- rather
    than talking about type restrictions of a relation that does not exist; every other
    case keeps ``matches no declared type restriction for ...``. The reason
    (``no_restriction_reason``) follows either lead."""
    # TK153 F11 (2026-10-17): the lead used to be the restriction wording for every case.
    reason = no_restriction_reason(declared, object_type, relation)
    if declared is not None and (object_type not in declared.types
                                 or relation not in declared.relations.get(object_type, ())):
        return f"tuple {tuple_text} names an undeclared relation {object_type}#{relation}{reason}"
    kind = 'derived relation ' if derived else ''
    return (f"tuple {tuple_text} matches no declared type restriction for "
            f"{kind}{object_type}#{relation}{reason}")


def _canonical_expr(expr: Expr) -> Expr:
    """``expr`` with every restriction list sorted, so two schemas that list the same
    restrictions in a different order compare equal."""
    if isinstance(expr, Direct):
        return Direct(tuple(sorted(expr.restrictions,
                                   key=lambda r: (r.type, r.predicate, r.wildcard))))
    if isinstance(expr, Union):
        return Union(tuple(_canonical_expr(c) for c in expr.children))
    if isinstance(expr, Intersection):
        return Intersection(tuple(_canonical_expr(c) for c in expr.children))
    if isinstance(expr, Exclusion):
        return Exclusion(_canonical_expr(expr.base), _canonical_expr(expr.subtract))
    return expr


def first_schema_difference(a: SchemaAST, b: SchemaAST) -> str | None:
    """``None`` when the two schemas are the same up to the order of restriction lists
    (and of type blocks and ``define`` lines, which the AST already ignores); otherwise
    the first differing ``type#relation`` (sorted order), with which side declares it."""
    for key in sorted(set(a) | set(b)):
        t, rel = key
        if key not in a:
            return f'{t}#{rel} (declared only in the second schema)'
        if key not in b:
            return f'{t}#{rel} (declared only in the first schema)'
        if _canonical_expr(a[key]) != _canonical_expr(b[key]):
            return f'{t}#{rel}'
    return None
