"""TK114 -- recursion through negation is refused at parse time, in both parsers.

Property guarded
----------------
A schema in which a relation depends on itself through a ``but not`` subtrahend is refused
by ``src/zanzibar/schema/parser.py::parse_schema_ast`` (and the JSON front end) and, independently,
by ``tests/oracle.py::parse_schema_ast``. Positive recursion stays legal. The dependency
steps are a computed ref, a TTU tupleset, a TTU target on a type the tupleset admits, and a
userset restriction ``[T#p]``; a step is negative anywhere inside a subtrahend, at any depth
(classical stratified negation). Decision and its reasoning:
``docs/tk114-stratified-negation-2026-10-04.md`` sec 2.

Why it is refused rather than given a meaning: on ``doc:a parent doc:a`` the schema
``viewer: [user] but not viewer from parent`` reads ``viewer = not viewer``, which has no
fixpoint. The set engine and the oracle answered it anyway, identically, because both seed
in-progress recursion with False; the oracle was not an independent referee there. The
graph refused it at compile (``CyclicDerivedDependency``).

Pre-fix evidence, literal output (2026-10-04, ``.scratch/tk114/probe.py`` on the tree
BEFORE this change; ``.scratch/`` is gitignored, this docstring and the map's sec 1 are the
tracked record). Every shape parsed in BOTH parsers; the graph compile refused all of them::

    == A ttu self-neg
      set answers   : ('OK', [True])
      oracle answers: ('OK', [True])
    == B userset neg
      set answers   : ('OK', [True, True])
      oracle answers: ('OK', [True, True])
    == F neg via computed+ttu
      set answers   : ('OK', [True])
      oracle answers: ('OK', [True])

None of those answers is a model of its schema (map, sec 1). The row named only the TTU
target form; B and B2 (a userset restriction) were found by this probe.

Sabotage: see the per-test docstrings and the map, sec 4.
"""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar.setengine import SetEngine
from tests import oracle as oracle_mod
from tests.parity import ParityEngine
from zanzibar.schema import parse_openfga_json, parse_schema_ast

_DOC = 'model\n  schema 1.1\ntype user\ntype doc\n  relations\n    define parent: [doc]\n'
_GROUP = 'model\n  schema 1.1\ntype user\ntype group\n  relations\n'

#: Every shape here has a cycle through a negative step. The letters are the map's sec 1.
_REFUSED = {
    'A/ttu-self': _DOC + '    define viewer: [user] but not viewer from parent\n',
    'B/userset-via-computed': (_GROUP + '    define member: [user] but not blocked\n'
                               '    define blocked: [group#member]\n'),
    'B2/userset-in-subtract': _GROUP + '    define member: [user] but not [group#member]\n',
    'B3/wildcard-userset': (_GROUP + '    define member: [user] but not blocked\n'
                            '    define blocked: [group:*#member]\n'),
    'D/double-negation': (_DOC + '    define blk: [user]\n'
                          '    define viewer: [user] but not (blk but not viewer from parent)\n'),
    'F/computed-then-ttu': (_DOC + '    define a: [user] but not b\n'
                            '    define b: a from parent\n'),
    'G/intersection-in-subtract': (_DOC + '    define ed: [user]\n'
                                   '    define viewer: [user] but not (ed and viewer from parent)\n'),
    'H/cross-type': ('model\n  schema 1.1\ntype user\n'
                     'type folder\n  relations\n    define child: [doc]\n'
                     '    define fv: [user] but not dv from child\n'
                     'type doc\n  relations\n    define parent: [folder]\n'
                     '    define dv: [user] or fv from parent\n'),
    'I/negative-step-mid-cycle': (_DOC + '    define x: [user] or y from parent\n'
                                  '    define y: [user] but not x\n'),
    # Three steps (a -> b -> c -> a). Every case above closes in at most two, so an oracle
    # whose path closure joined only once refused them all (sweep S9, INERT before this).
    'J/three-step-cycle': (_DOC + '    define a: [user] but not b\n'
                           '    define b: c from parent\n'
                           '    define c: [user] or a\n'),
}

#: Near-misses BOTH parsers must accept with the same keys: positive recursion, a negative
#: step that is not on a cycle, and the INSTEAD rewrites the refusal comments name.
_ACCEPTED = {
    'C/positive-userset-recursion': (_GROUP + '    define banned: [user]\n'
                                     '    define member: [user, group#member] but not banned\n'),
    'E/positive-ttu-recursion': (_DOC + '    define blk: [user]\n'
                                 '    define viewer: ([user] but not blk) or viewer from parent\n'),
    'negative-step-not-on-a-cycle': (_DOC + '    define viewer: [user] or viewer from parent\n'
                                     '    define access: [user] but not viewer from parent\n'),
    'INSTEAD/recursion-in-the-subtrahend': (
        _DOC + '    define blocked: [user] or blocked from parent\n'
        '    define viewer: [user] but not blocked\n'),
    'INSTEAD/double-negation-pushed-in': (
        _DOC + '    define blk: [user]\n'
        '    define viewer: ([user] but not blk) or ([user] and viewer from parent)\n'),
}


@pytest.mark.parametrize('label', sorted(_REFUSED))
def test_production_parser_refuses(label):
    """Sabotage S1 (2026-10-04): `src/zanzibar/schema/parser.py::_validate_stratified_negation`
    made a no-op -> every case here went red, and every oracle case stayed green
    (literal table: map sec 4)."""
    with pytest.raises(ValueError, match='recursion through negation'):
        parse_schema_ast(_REFUSED[label])


@pytest.mark.parametrize('label', sorted(_REFUSED))
def test_oracle_parser_refuses_independently(label):
    """Sabotage S2 (2026-10-04): the oracle twin made a no-op -> every case here went red,
    and every production case stayed green (map sec 4)."""
    with pytest.raises(ValueError, match='its own negation'):
        oracle_mod.parse_schema_ast(_REFUSED[label])


@pytest.mark.parametrize('label', sorted(_ACCEPTED))
def test_both_parsers_accept_the_controls_with_the_same_keys(label):
    """Without these, a parser that refused every ``but not`` would pass the tests above.
    Sabotage M0 (2026-10-04): production treats EVERY step as negative -> the controls
    with any recursion went red here (map sec 4)."""
    prod = parse_schema_ast(_ACCEPTED[label])
    orac = oracle_mod.parse_schema_ast(_ACCEPTED[label])
    assert set(prod) == set(orac)


def test_the_message_names_the_cycle():
    with pytest.raises(ValueError) as ei:
        parse_schema_ast(_REFUSED['F/computed-then-ttu'])
    assert 'doc#a -> doc#b -> doc#a' in str(ei.value), str(ei.value)


def test_set_engine_refuses_the_schema_instead_of_answering():
    """Pre-fix (module docstring, shape A): a standalone `SetEngine` accepted the schema and
    the cycle-closing write, then answered `True`, which no fixpoint supports."""
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        with pytest.raises(ValueError, match='recursion through negation'):
            SetEngine(session, 'tk114', _REFUSED['A/ttu-self'])


def _json_self_negation():
    return {
        'schema_version': '1.1',
        'type_definitions': [
            {'type': 'user'},
            {'type': 'doc',
             'relations': {
                 'parent': {'this': {}},
                 'viewer': {'difference': {
                     'base': {'this': {}},
                     'subtract': {'tupleToUserset': {
                         'tupleset': {'relation': 'parent'},
                         'computedUserset': {'relation': 'viewer'}}}}}},
             'metadata': {'relations': {
                 'parent': {'directly_related_user_types': [{'type': 'doc'}]},
                 'viewer': {'directly_related_user_types': [{'type': 'user'}]}}}},
        ],
    }


def test_json_front_end_refuses_it_too():
    with pytest.raises(ValueError, match='recursion through negation'):
        parse_openfga_json(_json_self_negation())


def test_the_instead_rewrite_is_served_identically_by_every_backend():
    """The rewrite the refusal comments name is a schema the GRAPH serves too, so it is the
    equivalence-preserving way out, not just one that parses. `ParityEngine` asserts
    unanimity of the graph, both set engines and the oracle on every op, accept/reject
    included.

    Under the rewrite the paradox data cannot even be written: a parent cycle is refused at
    admission on every backend ("would create a cycle in the userset membership topology",
    probed 2026-10-04). The standalone set engine accepted `doc:a parent doc:a` under the
    REFUSED shape only because its graph compile failed, which left it no ruleset to run
    that admission check with (map sec 1)."""
    pe = ParityEngine(_ACCEPTED['INSTEAD/recursion-in-the-subtrahend'])
    try:
        assert pe.graph is not None, pe.graph_drop_reason   # 4-way, not a 3-way degrade
        for raw in [('...', 'user', 'u', 'viewer', 'doc', 'a'),
                    ('...', 'user', 'u', 'viewer', 'doc', 'c'),
                    ('...', 'doc', 'b', 'parent', 'doc', 'a'),
                    ('...', 'doc', 'd', 'parent', 'doc', 'b')]:
            assert pe.add_tuple(*raw)
        assert not pe.add_tuple('...', 'doc', 'a', 'parent', 'doc', 'b')   # cycle: refused
        assert not pe.add_tuple('...', 'doc', 'c', 'parent', 'doc', 'c')   # self-parent too
        assert pe.check('...', 'user', 'u', 'viewer', 'doc', 'a') is True
        assert pe.add_tuple('...', 'user', 'u', 'blocked', 'doc', 'd')     # two levels up
        assert pe.check('...', 'user', 'u', 'viewer', 'doc', 'a') is False
        assert pe.check('...', 'user', 'u', 'viewer', 'doc', 'c') is True
        assert pe.remove_tuple('...', 'user', 'u', 'blocked', 'doc', 'd')
        assert pe.check('...', 'user', 'u', 'viewer', 'doc', 'a') is True
    finally:
        pe.close()
