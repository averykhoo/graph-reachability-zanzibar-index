"""The schema AST (`Direct`/`Computed`/`TTU`/`Union`/`Intersection`/`Exclusion`) and walkers over it.

Part of `zanzibar.schema`; split out of the single-file module by TK120 (2026-10-06).
"""
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
    children: tuple['Expr', ...]


@dataclass(frozen=True, slots=True)
class Intersection:
    children: tuple['Expr', ...]


@dataclass(frozen=True, slots=True)
class Exclusion:
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
