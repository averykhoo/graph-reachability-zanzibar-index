"""Reads refuse a type, relation or subject relation the schema does not declare.

One validator for both backends: ``Store`` and ``SetEngine`` call these functions on the
same ``DeclaredRelations`` (the set engine's), before any answer is computed, so the two
refuse the same calls with the same message. A NAME is never checked: ``doc:999``,
``user:*`` and ``folder:*`` are names, and a read naming one that holds no tuple still
answers ``False`` or empty.

Part of `zanzibar.schema`.
"""
# Provenance: TK185 step 4 (C5 + C7), decision DEC-16 (2026-11-20): the owner decided on
# 2026-11-01 that a read naming an undeclared type or relation is an error. The messages
# reuse ``syntax.py::no_restriction_reason``, the write side's wording, so a read and a
# write that make the same mistake are told the same thing.
from __future__ import annotations

import difflib

from .errors import UndeclaredTypeOrRelation
from .syntax import DeclaredRelations, no_restriction_reason

__all__: list[str] = []

_BARE = (None, '...')
_CHECK_PARAMS = ('subject_predicate', 'subject_type', 'subject_name',
                 'relation', 'object_type', 'object_name')
_LOOKUP_PARAMS = ('subject_predicate', 'subject_type', 'subject_name')


def _declares(declared: DeclaredRelations, type_name: str, relation: str) -> bool:
    return relation in declared.relations.get(type_name, ())


def refuse_undeclared_subject(declared: DeclaredRelations, method: str, subject_predicate,
                              subject_type: str, subject_name: str,
                              rest: tuple = ()) -> None:
    """Refuse a read whose subject names an undeclared type, or a subject relation its type
    does not declare. ``subject_predicate`` ``None`` or ``'...'`` is the bare subject.
    ``rest`` is the call's arguments after the subject (``check``'s relation and object;
    empty for ``lookup``), used only to write the corrected call into the hint."""
    if subject_type in declared.types:
        if (subject_predicate in _BARE
                or _declares(declared, subject_type, subject_predicate)):
            return
        raise UndeclaredTypeOrRelation(
            f'{method}() names an undeclared subject relation '
            f'{subject_type}#{subject_predicate}'
            f'{no_restriction_reason(declared, subject_type, subject_predicate)}',
            method=method, role='subject', type_name=subject_type,
            relation=subject_predicate)
    message = (f'{method}() names an undeclared subject type {subject_type!r}'
               f'{no_restriction_reason(declared, subject_type, "")}')
    # The parts of a result key, (type, name, predicate), passed straight back as the
    # subject: check(*key, ...) puts the type in the predicate slot and '...' in the name.
    if isinstance(subject_predicate, str) and (subject_predicate in declared.types
                                               or subject_name == '...'):
        params = _CHECK_PARAMS if rest else _LOOKUP_PARAMS
        fixed = ', '.join(repr(v) for v in (subject_name, subject_predicate, subject_type,
                                             *rest))
        message += (f'. A result key is (type, name, predicate); {method} takes '
                    f'({", ".join(params)}): write {method}({fixed})')
    raise UndeclaredTypeOrRelation(message, method=method, role='subject',
                                   type_name=subject_type, relation=None)


def refuse_undeclared_object(declared: DeclaredRelations, method: str, object_type: str,
                             relation: str) -> None:
    """Refuse a read of ``object_type#relation`` when the schema declares no such type, or
    no such relation on it (a type with no relations, such as ``type user``, cannot be a
    read's object). The wording is the write refusal's."""
    if _declares(declared, object_type, relation):
        return
    raise UndeclaredTypeOrRelation(
        f'{method}() names an undeclared relation {object_type}#{relation}'
        f'{no_restriction_reason(declared, object_type, relation)}',
        method=method, role='object', type_name=object_type, relation=relation)


def refuse_undeclared_filter(declared: DeclaredRelations, method: str,
                             type_keyword: str, type_value: str | None,
                             relation_keyword: str, relation_value: str | None, *,
                             bare: bool) -> None:
    """Refuse a lookup filter naming an undeclared type or relation. ``None`` is no filter.
    The relation must be declared on the filter's type, or on some type when the type is
    not given. ``bare=True`` (a filter over SUBJECTS) also accepts ``'...'``, the bare
    subject. Both values were type-checked already (``tuplestr.py::shape_filter``)."""
    if type_value is not None and type_value not in declared.types:
        raise UndeclaredTypeOrRelation(
            f'{method}(): {type_keyword}={type_value!r} names an undeclared type'
            f'{no_restriction_reason(declared, type_value, "")}',
            method=method, role='filter', type_name=type_value, relation=None)
    if relation_value is None or (bare and relation_value == '...'):
        return
    if type_value is not None:
        if _declares(declared, type_value, relation_value):
            return
        raise UndeclaredTypeOrRelation(
            f'{method}(): {relation_keyword}={relation_value!r} names an undeclared '
            f'relation {type_value}#{relation_value}'
            f'{no_restriction_reason(declared, type_value, relation_value)}',
            method=method, role='filter', type_name=type_value, relation=relation_value)
    every = sorted({r for rels in declared.relations.values() for r in rels})
    if relation_value in every:
        return
    near = difflib.get_close_matches(relation_value, every, n=1)
    hint = (f'; did you mean {near[0]!r}?' if near
            else f'; it declares {", ".join(every)}' if every else '')
    raise UndeclaredTypeOrRelation(
        f'{method}(): {relation_keyword}={relation_value!r} names an undeclared relation: '
        f'no type in the schema declares a relation {relation_value!r}{hint}',
        method=method, role='filter', type_name=None, relation=relation_value)
