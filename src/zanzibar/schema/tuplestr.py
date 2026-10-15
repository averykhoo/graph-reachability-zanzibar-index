"""The OpenFGA string form of a tuple, and the two call forms ``Store`` accepts.

``Store`` and ``TupleSource`` take a tuple either as six parts::

    store.add_tuple("...", "user", "alice", "viewer", "doc", "d1")
    store.add_tuple(subject_predicate="member", subject_type="group", subject_name="eng",
                    relation="viewer", object_type="doc", object_name="d1")

or in the OpenFGA form, a ``user``, a ``relation`` and an ``object``::

    store.add_tuple("user:alice", "viewer", "doc:d1")
    store.add_tuple(user="group:eng#member", relation="viewer", object="doc:d1")

A user string is ``"type:name"`` (the bare subject, predicate ``'...'``),
``"type:name#relation"`` (a userset) or ``"type:*"`` (every subject of the type). An
object string is ``"type:name"``. ``':'`` and ``'#'`` are outside the identifier charset
(``IDENTIFIER_CHARSET``), so the split is never ambiguous. Which form a call uses is decided
by its keywords (``user`` / ``object`` vs ``subject_*`` / ``object_type`` /
``object_name``), and otherwise by how many arguments it passes.
"""

from __future__ import annotations

import inspect

from .errors import ZanzibarError

__all__ = ['MalformedTupleString', 'parse_user', 'parse_object',
           'tuple_args', 'lookup_args', 'lookup_reverse_args']


class MalformedTupleString(ZanzibarError, ValueError):
    """An OpenFGA-style ``"type:name"`` / ``"type:name#relation"`` string could not be
    split into its parts. The message names the expected form."""


_USER_FORM = "'type:name', 'type:name#relation' or 'type:*'"
_OBJECT_FORM = "'type:name'"


def _split_type_name(part: str, text: str, what: str, form: str) -> tuple[str, str]:
    type_, sep, name = part.partition(':')
    if not sep or not type_ or not name or ':' in name:
        raise MalformedTupleString(f'{what} {text!r} is not of the form {form}')
    return type_, name


def parse_user(text: str) -> tuple[str, str, str]:
    """Split an OpenFGA user string into ``(subject_predicate, subject_type, subject_name)``.

    ``"user:alice"`` -> ``('...', 'user', 'alice')``; ``"group:eng#member"`` ->
    ``('member', 'group', 'eng')``; ``"user:*"`` -> ``('...', 'user', '*')``."""
    if not isinstance(text, str):
        raise TypeError(f'user must be a str of the form {_USER_FORM}, '
                        f'not {type(text).__name__}')
    head, sep, predicate = text.partition('#')
    if sep:
        if not predicate or '#' in predicate:
            raise MalformedTupleString(f'user {text!r} is not of the form {_USER_FORM}')
        if predicate == '...':
            raise MalformedTupleString(
                f"user {text!r}: write the bare subject as {head!r}, without '#...' "
                f"(the form is {_USER_FORM})")
    else:
        predicate = '...'
    type_, name = _split_type_name(head, text, 'user', _USER_FORM)
    return predicate, type_, name


def parse_object(text: str) -> tuple[str, str]:
    """Split an OpenFGA object string ``"type:name"`` into ``(object_type, object_name)``."""
    if not isinstance(text, str):
        raise TypeError(f'object must be a str of the form {_OBJECT_FORM}, '
                        f'not {type(text).__name__}')
    if '#' in text:
        raise MalformedTupleString(
            f"object {text!r} is not of the form {_OBJECT_FORM}: an object has no "
            f"'#relation' (pass the relation as its own argument)")
    return _split_type_name(text, text, 'object', _OBJECT_FORM)


def _signature(names: tuple[str, ...]) -> inspect.Signature:
    return inspect.Signature([inspect.Parameter(n, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                              for n in names])


_TUPLE_LONG = ('subject_predicate', 'subject_type', 'subject_name',
               'relation', 'object_type', 'object_name')
_TUPLE_SHORT = ('user', 'relation', 'object')
_LOOKUP_LONG = ('subject_predicate', 'subject_type', 'subject_name')
_LOOKUP_SHORT = ('user',)
_REVERSE_LONG = ('relation', 'object_type', 'object_name')
_REVERSE_SHORT = ('relation', 'object')


def _bind(method: str, args: tuple, kwargs: dict,
          long: tuple[str, ...], short: tuple[str, ...]) -> tuple[bool, tuple]:
    """Pick the call form and bind the arguments to it: ``(is_short, values)``.

    A keyword only one form has decides; otherwise the argument count does."""
    keys = set(kwargs)
    if keys & (set(short) - set(long)):
        is_short = True
    elif keys & (set(long) - set(short)):
        is_short = False
    else:
        count = len(args) + len(kwargs)
        if count not in (len(long), len(short)):
            raise TypeError(
                f'{method}() takes {len(short)} arguments ({", ".join(short)}) or '
                f'{len(long)} ({", ".join(long)}); got {count}')
        is_short = count == len(short)
    names = short if is_short else long
    try:
        bound = _signature(names).bind(*args, **kwargs)
    except TypeError as exc:
        raise TypeError(f'{method}({", ".join(names)}): {exc}') from None
    return is_short, tuple(bound.arguments[n] for n in names)


def tuple_args(method: str, args: tuple, kwargs: dict) -> tuple:
    """``add_tuple`` / ``remove_tuple`` / ``check`` arguments in either form, as the six
    parts ``(subject_predicate, subject_type, subject_name, relation, object_type,
    object_name)``."""
    is_short, values = _bind(method, args, kwargs, _TUPLE_LONG, _TUPLE_SHORT)
    if not is_short:
        return values
    user, relation, obj = values
    return (*parse_user(user), relation, *parse_object(obj))


def lookup_args(method: str, args: tuple, kwargs: dict) -> tuple:
    """``lookup`` arguments (``user`` or the three subject parts) as
    ``(subject_predicate, subject_type, subject_name)``."""
    is_short, values = _bind(method, args, kwargs, _LOOKUP_LONG, _LOOKUP_SHORT)
    return parse_user(values[0]) if is_short else values


def lookup_reverse_args(method: str, args: tuple, kwargs: dict) -> tuple:
    """``lookup_reverse`` arguments (``relation, object`` or ``relation, object_type,
    object_name``) as ``(relation, object_type, object_name)``."""
    is_short, values = _bind(method, args, kwargs, _REVERSE_LONG, _REVERSE_SHORT)
    if not is_short:
        return values
    relation, obj = values
    return (relation, *parse_object(obj))
