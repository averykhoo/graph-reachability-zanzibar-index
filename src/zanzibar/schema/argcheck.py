"""Argument checks for the public entry points: a wrong TYPE is a ``TypeError`` raised before
any statement runs, and the message names the argument and what to pass instead.

One function per kind of argument, so every entry point refuses the same mistake with the
same words.
"""
# The census test (tests/test_tk179_public_arg_census.py) lists every public parameter and
# what it accepts; a parameter missing from it fails that test.
# Provenance: TK179 (docs/tk179-strict-public-args-plan-2026-10-30.md). A runtime type-check
# decorator was rejected there: the annotations do not encode the contract (``at_least``
# refuses ``True``, ``paranoia`` accepts it; ``None`` is meaningful for several arguments),
# and the hot methods take ``*args`` in two call forms.
from __future__ import annotations

from collections.abc import Iterable


def _got(value: object) -> str:
    return f'{type(value).__name__} {value!r}' if not isinstance(value, type) else repr(value)


def require_str(method: str, name: str, value: object) -> str:
    """``value`` itself when it is a ``str``; else ``TypeError``."""
    if not isinstance(value, str):
        raise TypeError(f'{method}(): {name} must be a str, not {_got(value)}')
    return value


def require_optional_str(method: str, name: str, value: object) -> str | None:
    """``None`` or a ``str``; else ``TypeError``."""
    if value is not None and not isinstance(value, str):
        raise TypeError(f'{method}(): {name} must be None or a str, not {_got(value)}')
    return value


def require_bool(method: str, name: str, value: object) -> bool:
    """Only ``True`` or ``False``: a truthy stand-in (``None``, ``0``, ``"false"``) would pick
    a mode without a word."""
    if not isinstance(value, bool):
        raise TypeError(f'{method}(): {name} must be True or False, not {_got(value)}')
    return value


def require_int(method: str, name: str, value: object, *, minimum: int | None = None,
                optional: bool = False) -> int | None:
    """An ``int`` (never a ``bool``), at least ``minimum`` when given; ``None`` too when
    ``optional``. A wrong type is a ``TypeError``, a too-small int a ``ValueError``."""
    if value is None and optional:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        what = 'None or an int' if optional else 'an int'
        raise TypeError(f'{method}(): {name} must be {what}, not {_got(value)}')
    if minimum is not None and value < minimum:
        raise ValueError(f'{method}(): {name} must be >= {minimum}, not {value!r}')
    return value


def require_session(method: str, value: object) -> None:
    """A SQLAlchemy / SQLModel ``Session`` (SQLModel's is a subclass)."""
    from sqlalchemy.orm import Session
    if not isinstance(value, Session):
        raise TypeError(f'{method}(): session must be a sqlmodel.Session, not {_got(value)}')


def require_shapes(method: str, value: object) -> frozenset:
    """``object_wildcard_shapes`` is a collection (of ``(type, relation)`` pairs), returned
    as a frozenset of tuples. A bare string is refused: it iterates as characters. A
    2-item list of strings is a pair too (a JSON-loaded config has lists, not tuples); any
    other entry that cannot be a set member (a list of another length, a dict) is a
    ``TypeError`` naming the entry. The other ENTRIES are checked by the schema compiler
    (``ShapeNoLongerAccepted`` naming the entry and what to write instead): the pair shape
    here, before any statement; the declared-relation check with the schema."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise TypeError(f'{method}(): object_wildcard_shapes must be a set of (type, relation) '
                        f'pairs, e.g. {{("folder", "viewer")}}, not {_got(value)}')
    entries = []
    for entry in value:
        # TK185 (C4, 0.1.2 install trial): [["folder", "viewer"]] crashed in frozenset()
        # with Python's own "unhashable type: 'list'", which named neither the argument
        # nor the entry.
        if (isinstance(entry, list) and len(entry) == 2
                and all(isinstance(part, str) for part in entry)):
            entry = tuple(entry)
        try:
            hash(entry)
        except TypeError:
            raise TypeError(
                f'{method}(): object_wildcard_shapes entry {entry!r} is not a (type, relation) '
                f'pair of strings; write each entry as a tuple such as ("folder", "viewer") '
                f'(a 2-item list of strings is accepted too)') from None
        entries.append(entry)
    shapes = frozenset(entries)
    from .compiler import _reject_non_pair_shapes   # lazy: compiler imports this module
    _reject_non_pair_shapes(shapes)
    return shapes


def require_instance(method: str, name: str, value: object, kinds: type | tuple[type, ...],
                     *, what: str, optional: bool = False) -> None:
    """``value`` is one of ``kinds`` (or ``None`` when ``optional``); else a ``TypeError``
    whose text says ``what`` to pass."""
    if value is None and optional:
        return
    if not isinstance(value, kinds):
        raise TypeError(f'{method}(): {name} must be {what}, not {_got(value)}')
