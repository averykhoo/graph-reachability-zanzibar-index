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

from .argcheck import require_str
from .errors import ZanzibarError, validate_write_identifiers

__all__ = ['MalformedTupleString', 'parse_user', 'parse_object',
           'tuple_args', 'lookup_args', 'lookup_reverse_args', 'shape_filter']


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
        # TK168: ':' in the relation part is a shape error, as it is in the name, so
        # 'user:a#b:c' is malformed on reads and writes alike (it used to read False).
        if not predicate or '#' in predicate or ':' in predicate:
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
_RENAMED_0_1 = {'s_type': 'subject_type', 's_name': 'subject_name',
                'o_type': 'object_type', 'o_name': 'object_name'}


def _form(names: tuple[str, ...]) -> str:
    """``'3 arguments (user, relation, object)'`` -- the singular for one."""
    noun = 'argument' if len(names) == 1 else 'arguments'
    return f'{len(names)} {noun} ({", ".join(names)})'


def _bind(method: str, args: tuple, kwargs: dict,
          long: tuple[str, ...], short: tuple[str, ...]) -> tuple[bool, tuple]:
    """Pick the call form and bind the arguments to it: ``(is_short, values)``.

    A keyword only one form has decides; otherwise the argument count does."""
    keys = set(kwargs)
    unknown = sorted(keys - set(long) - set(short))
    if unknown:
        # TK173 F9: an old 0.0.x keyword (``s_type=``) used to surface as an arity error
        # ("got 5") that never named it.
        noun = 'argument' if len(unknown) == 1 else 'arguments'
        renamed = [f'{k} is now {_RENAMED_0_1[k]}' for k in unknown if k in _RENAMED_0_1]
        hint = f' (0.1 renamed the 0.0.x keywords: {", ".join(renamed)})' if renamed else ''
        raise TypeError(
            f'{method}() got an unexpected keyword {noun} '
            f'{", ".join(repr(k) for k in unknown)}{hint}; it takes {_form(short)} or '
            f'{_form(long)}')
    if keys & (set(short) - set(long)):
        is_short = True
    elif keys & (set(long) - set(short)):
        is_short = False
    else:
        count = len(args) + len(kwargs)
        if count not in (len(long), len(short)):
            raise TypeError(f'{method}() takes {_form(short)} or {_form(long)}; got {count}')
        is_short = count == len(short)
    names = short if is_short else long
    try:
        bound = _signature(names).bind(*args, **kwargs)
    except TypeError as exc:
        hint = ''
        filled = set(names[:len(args)]) | keys
        if 'subject_predicate' in names and 'subject_predicate' not in filled:
            hint = " (pass subject_predicate='...' for a plain subject such as user:alice)"
        raise TypeError(f'{method}({", ".join(names)}): {exc}{hint}') from None
    return is_short, tuple(bound.arguments[n] for n in names)


_WRITES = frozenset({'add', 'remove', 'add_tuple', 'remove_tuple'})


def require_parts(method: str, names: tuple[str, ...], values: tuple) -> None:
    """The identifier parts of a call, checked before anything reads the database.

    A WRITE gets the full write validation (``validate_write_identifiers``): a non-``str``
    or out-of-charset part is ``AdmissionRejected``, as it always was, only earlier. A READ
    stays lenient about VALUES (a name that cannot exist matches nothing) but not about
    TYPES: a part that is not a ``str`` is a ``TypeError``. ``None`` as a read's subject
    predicate keeps its documented meaning, the bare subject; an ``Ellipsis`` predicate
    gets its own refusal further on."""
    # TK179 G1/G2: a wrong-typed relation or six-part field used to read as "no access"
    # (check -> False) or reach SQLite, and writes refused it only after taking locks.
    if method in _WRITES and names == _TUPLE_LONG:
        validate_write_identifiers(*values)
        return
    for name, value in zip(names, values, strict=True):
        if name == 'subject_predicate' and (value is None or value is Ellipsis):
            continue
        require_str(method, name, value)


def tuple_args(method: str, args: tuple, kwargs: dict) -> tuple:
    """``add_tuple`` / ``remove_tuple`` / ``check`` arguments in either form, as the six
    parts ``(subject_predicate, subject_type, subject_name, relation, object_type,
    object_name)``."""
    is_short, values = _bind(method, args, kwargs, _TUPLE_LONG, _TUPLE_SHORT)
    if is_short:
        user, relation, obj = values
        values = (*parse_user(user), relation, *parse_object(obj))
    require_parts(method, _TUPLE_LONG, values)
    return values


def lookup_args(method: str, args: tuple, kwargs: dict) -> tuple:
    """``lookup`` arguments (``user`` or the three subject parts) as
    ``(subject_predicate, subject_type, subject_name)``."""
    is_short, values = _bind(method, args, kwargs, _LOOKUP_LONG, _LOOKUP_SHORT)
    values = parse_user(values[0]) if is_short else values
    require_parts(method, _LOOKUP_LONG, values)
    return values


def lookup_reverse_args(method: str, args: tuple, kwargs: dict) -> tuple:
    """``lookup_reverse`` arguments (``relation, object`` or ``relation, object_type,
    object_name``) as ``(relation, object_type, object_name)``."""
    is_short, values = _bind(method, args, kwargs, _REVERSE_LONG, _REVERSE_SHORT)
    if is_short:
        relation, obj = values
        values = (relation, *parse_object(obj))
    require_parts(method, _REVERSE_LONG, values)
    return values


def shape_filter(method: str, entity_type, predicate,
                 names: tuple[str, str] = ('the type filter', 'the predicate filter')):
    """A lookup filter as a predicate on ``(type, predicate)`` shapes, or ``None``
    when neither part is given (the caller then returns the result unchanged).

    ``entity_type`` / ``predicate`` are each ``None`` (no filter on that part) or a
    ``str``. An undeclared name is not refused: like every read, it matches nothing and
    the filtered result is empty. Anything else is a ``TypeError`` naming ``method`` and
    the argument's name in ``names`` (the caller's own keywords)."""
    # Provenance: TK156 (docs/tk156-lookup-filter-2026-10-19.md); ``names`` from the
    # TK156 review, so a Store-level refusal names the keyword the caller passed.
    for name, value in zip(names, (entity_type, predicate), strict=True):
        if value is not None and not isinstance(value, str):
            hint = ''
            if value is Ellipsis and name == names[1]:
                hint = "; write the string '...' for a bare subject"
            raise TypeError(f'{method}(): {name} must be a str or None, '
                            f'not {type(value).__name__}{hint}')
    if entity_type is None and predicate is None:
        return None

    def matches(t: str, p: str) -> bool:
        return ((entity_type is None or t == entity_type)
                and (predicate is None or p == predicate))
    return matches
