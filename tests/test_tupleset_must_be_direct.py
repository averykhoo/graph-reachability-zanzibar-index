"""TK106 (user decision 2026-09-26): a `from`-tupleset must be DIRECT-ONLY, as in OpenFGA.

The relation after `from` (``parent`` in ``viewer from parent``) may only be type
restrictions -- ``[folder]``, ``[folder, doc]``, ``[folder] or [doc]``, wildcards included.
OpenFGA refuses anything else: "the relation is referenced in at least one tupleset and
thus must be a direct relation" (``pkg/typesystem/typesystem.go::isUsersetRewriteValid``).

WHY. ``from`` walks the STORED tuples of the tupleset, never its computed membership
(CLAUDE.md, oracle-pinned). So any other arm on a tupleset was silently IGNORED by every
``from`` that used it: ``parent: [folder] but not blockedp`` inherited from blocked
parents too, ``parent: [folder] and vetted`` ignored the vetting, and ``parent: approved``
(a reference) saw no parents at all. Before TK106 the graph refused the untainted computed
form at compile time while the set engine degraded past it and answered, and nothing
refused the tainted (boolean) form.

WHAT IS PINNED HERE.
  1. Every blocked pattern is refused on EVERY construction path, by
     ``zanzibar_utils_v1.py::_validate_tuplesets_direct`` and the oracle's independent
     twin ``tests/oracle.py::_validate_tuplesets_direct``. Each path has a CONTROL, the
     legal direct forms, that it must ACCEPT, so a path refusing everything cannot pass.
  2. The behaviour-preserving REWRITE -- store the links on a direct relation
     (``parent_link: [<every type parent names>]``) and use that in the ``from`` -- gives
     the SAME answers as the old schema did, computed with the refusal patched off (all
     backends unanimous inside ``ParityEngine``). That is the migration a refused user
     makes; it keeps today's behaviour exactly, ignored arm and all.

The design decisions (parse-time refusal in both parsers, untainted computed tuplesets
included, userset restrictions left to the graph compiler) and the sabotage evidence
are in docs/tk106-boolean-tuplesets-2026-09-26.md.

MUTATION SWEEP, 2026-09-26 (literal; the 4 rewrite pins deselected; that doc's § 8):
M0 no mutation `71 passed`; M1 production check -> no-op `31 failed`; M2 oracle twin ->
no-op `12 failed` (oracle paths only); M3 production accepts `but not` `11 failed`
(patterns 1, 3 + JSON); M4 production re-exempts tainted tuplesets `21 failed`
(patterns 1-4 + JSON); M5 oracle twin accepts `and` `2 failed` (pattern 2, oracle paths).
"""
import json

import pytest
from sqlmodel import Session, SQLModel, create_engine

import tests.oracle as oracle_mod
import zanzibar_utils_v1 as Z
from setengine import SetEngine
from tests.oracle import Oracle
from tests.parity import ParityEngine

_HEAD = '''model
  schema 1.1

type user

type folder
  relations
    define viewer: [user]

type doc
  relations
    define viewer: [user]
'''
_VIEW = '    define view: viewer from parent\n'

#: The blocked patterns (the TK106 row's list; 5 is split into its two forms).
BLOCKED = {
    '1-but-not': _HEAD + ('    define blockedp: [folder]\n'
                          '    define parent: [folder] but not blockedp\n') + _VIEW,
    '2-and': _HEAD + ('    define vetted: [folder]\n'
                      '    define parent: [folder] and vetted\n') + _VIEW,
    '3-but-not-direct-rc1': _HEAD + '    define parent: [folder] but not [doc]\n' + _VIEW,
    '4-reference-to-boolean': _HEAD + ('    define blockedp: [folder]\n'
                                       '    define approved: [folder] but not blockedp\n'
                                       '    define parent: approved\n') + _VIEW,
    '5a-computed-arm': _HEAD + ('    define other: [folder]\n'
                                '    define parent: [folder] or other\n') + _VIEW,
    '5b-nested-from': _HEAD + ('    define up: [doc]\n'
                               '    define parent: [folder] or parent from up\n') + _VIEW,
}

#: Legal tuplesets -- the CONTROL every path must accept.
ALLOWED = {
    'direct': _HEAD + '    define parent: [folder]\n' + _VIEW,
    'multi-type': _HEAD + '    define parent: [folder, doc]\n' + _VIEW,
    'union-of-directs': _HEAD + '    define parent: [folder] or [doc]\n' + _VIEW,
    'star': _HEAD + '    define parent: [folder, folder:*]\n' + _VIEW,
}


def _session():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _set_engine(schema):
    session = _session()
    try:
        SetEngine(session, 's', schema)
    finally:
        session.close()


def _connected_store(schema):
    from connectedstore import ConnectedStore
    session = _session()
    try:
        ConnectedStore(session, 'cs', schema=schema)
    finally:
        session.close()


def _parity(schema):
    ParityEngine(schema).close()


PATHS = {
    'parse_schema_ast': Z.parse_schema_ast,
    'oracle.parse_schema_ast': oracle_mod.parse_schema_ast,
    'parse_openfga_schema': Z.parse_openfga_schema,
    'SetEngine': _set_engine,
    'Oracle': lambda s: Oracle(s, []),
    'ParityEngine': _parity,
    'ConnectedStore': _connected_store,
}


@pytest.mark.parametrize('path', sorted(PATHS))
@pytest.mark.parametrize('pattern', sorted(BLOCKED))
def test_blocked_tupleset_is_refused_on_every_path(pattern, path):
    with pytest.raises(ValueError, match='tupleset must be direct'):
        PATHS[path](BLOCKED[pattern])


@pytest.mark.parametrize('path', sorted(PATHS))
@pytest.mark.parametrize('pattern', sorted(ALLOWED))
def test_direct_tupleset_is_accepted_on_every_path(pattern, path):
    """CONTROL: the refusal is not "refuse every `from`"."""
    PATHS[path](ALLOWED[pattern])


def test_openfga_json_front_end_refuses_a_boolean_tupleset():
    """The JSON front-end (`parse_openfga_json`) shares the refusal: pattern 1 as an
    OpenFGA authorization model."""
    this = {'this': {}}
    model = {
        'schema_version': '1.1',
        'type_definitions': [
            {'type': 'user'},
            {'type': 'folder', 'relations': {'viewer': this},
             'metadata': {'relations': {'viewer': {'directly_related_user_types': [
                 {'type': 'user'}]}}}},
            {'type': 'doc',
             'relations': {
                 'blockedp': this,
                 'parent': {'difference': {'base': this,
                                           'subtract': {'computedUserset': {
                                               'relation': 'blockedp'}}}},
                 'view': {'tupleToUserset': {'tupleset': {'relation': 'parent'},
                                             'computedUserset': {'relation': 'viewer'}}}},
             'metadata': {'relations': {
                 'blockedp': {'directly_related_user_types': [{'type': 'folder'}]},
                 'parent': {'directly_related_user_types': [{'type': 'folder'}]}}}},
        ],
    }
    with pytest.raises(ValueError, match='tupleset must be direct'):
        Z.parse_openfga_json(json.dumps(model))
    # control: the same model with a direct `parent` is accepted
    model['type_definitions'][2]['relations']['parent'] = this
    Z.parse_openfga_json(json.dumps(model))


# --------------------------------------------------------------------------- #
# The behaviour-preserving rewrite gives the SAME answers as the old schema did.
# --------------------------------------------------------------------------- #

#: pattern -> (old schema, old data, rewritten schema). The rewrite stores the links on
#: `parent_link: [<every type parent names>]` and uses that in the `from`; the data
#: migration renames `parent` tuples to `parent_link` and keeps everything else.
_REWRITES = {
    '1-but-not': (
        BLOCKED['1-but-not'],
        [('...', 'folder', 'f2', 'blockedp', 'doc', 'd1')],
        _HEAD + ('    define blockedp: [folder]\n'
                 '    define parent_link: [folder]\n'
                 '    define view: viewer from parent_link\n')),
    '2-and': (
        BLOCKED['2-and'],
        [('...', 'folder', 'f1', 'vetted', 'doc', 'd1')],
        _HEAD + ('    define vetted: [folder]\n'
                 '    define parent_link: [folder]\n'
                 '    define view: viewer from parent_link\n')),
    '3-but-not-direct-rc1': (
        BLOCKED['3-but-not-direct-rc1'],
        [('...', 'doc', 'd2', 'parent', 'doc', 'd1')],
        _HEAD + ('    define parent_link: [folder, doc]\n'
                 '    define view: viewer from parent_link\n')),
    '5a-computed-arm': (
        BLOCKED['5a-computed-arm'],
        [('...', 'folder', 'f3', 'other', 'doc', 'd1')],
        _HEAD + ('    define other: [folder]\n'
                 '    define parent_link: [folder]\n'
                 '    define view: viewer from parent_link\n')),
}

_COMMON = [
    ('...', 'user', 'alice', 'viewer', 'folder', 'f1'),
    ('...', 'user', 'bob', 'viewer', 'folder', 'f2'),
    ('...', 'user', 'carol', 'viewer', 'folder', 'f3'),
    ('...', 'user', 'dave', 'viewer', 'doc', 'd2'),
    ('...', 'folder', 'f1', 'parent', 'doc', 'd1'),
    ('...', 'folder', 'f2', 'parent', 'doc', 'd1'),
    ('...', 'folder', 'f2', 'parent', 'doc', 'd2'),
]
#: pattern -> (query, OLD answer): the witness that the old schema really IGNORED its arm
#: -- the grant (or non-grant) the rewrite has to reproduce.
_IGNORED_ARM_WITNESS = {
    '1-but-not': (('...', 'user', 'bob', 'view', 'doc', 'd1'), True),      # f2 is blocked
    '2-and': (('...', 'user', 'bob', 'view', 'doc', 'd1'), True),          # f2 is not vetted
    '3-but-not-direct-rc1': (('...', 'user', 'dave', 'view', 'doc', 'd1'), True),  # doc:d2
    '5a-computed-arm': (('...', 'user', 'carol', 'view', 'doc', 'd1'), False),     # via other
}
_QUERIES = [('...', 'user', u, 'view', 'doc', d)
            for u in ('alice', 'bob', 'carol', 'dave', 'erin') for d in ('d1', 'd2', 'd3')]


def _answers(schema, data):
    eng = ParityEngine(schema)
    try:
        for raw in data:
            assert eng.add_tuple(*raw), f'refused {raw}'
        return {q: eng.check(*q) for q in _QUERIES}, eng.graph is not None
    finally:
        eng.close()


def _migrate(data):
    return [(sp, st, sn, 'parent_link' if rel == 'parent' else rel, ot, on)
            for (sp, st, sn, rel, ot, on) in data]


@pytest.mark.parametrize('pattern', sorted(_REWRITES))
def test_rewrite_keeps_the_old_answers(pattern, monkeypatch):
    """The old schema is evaluated with the refusal patched OFF in both parsers, which is
    exactly what every backend answered before TK106 (ParityEngine asserts they agree).
    The rewrite, on migrated data, must answer every query identically -- including the
    grants the old schema gave THROUGH the ignored arm (e.g. bob via the blocked f2)."""
    old_schema, extra, new_schema = _REWRITES[pattern]
    data = _COMMON + extra
    with monkeypatch.context() as m:
        m.setattr(Z, '_validate_tuplesets_direct', lambda ast: None)
        m.setattr(oracle_mod, '_validate_tuplesets_direct', lambda ast: None)
        old, _old_graph = _answers(old_schema, data)
    new, new_graph = _answers(new_schema, _migrate(data))
    assert new_graph, 'the rewrite must join the graph index (4-way)'
    assert any(old.values()), 'ANTI-VACUITY: the old schema granted nothing'
    q, ignored = _IGNORED_ARM_WITNESS[pattern]
    assert old[q] is ignored, (
        f'{pattern}: the old schema did not ignore its arm on {q} -- the pin would not '
        f'show the behaviour the rewrite preserves')
    diff = {q: (old[q], new[q]) for q in _QUERIES if old[q] != new[q]}
    assert not diff, f'{pattern}: rewrite changed answers (old, new): {diff}'
