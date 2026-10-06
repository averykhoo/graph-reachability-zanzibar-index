"""TK113: ``WildcardIndex.remove_node`` is EXACT or REFUSED, on every node, on any schema.

``RuleSet.apply`` stores a write-time COPY of a tuple for every Computed/TTU rewrite and
every boolean routing leaf. ``remove_node`` deletes one node's edges and runs no rewrite,
so on a node a copy pair straddles it diverged. PROBED before the fix (2026-10-03b,
``docs/tk113-remove-node-fence-2026-10-03.md`` sec 1), on the PURE schema
``viewer: editor``, removing ``doc:x#editor``:
    alice viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
    bob   viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
    carol viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
    check_invariants(schema_info) on committed state: PASSED
and removing a rewrite TARGET made later legitimate removes refuse
(``AdmissionRejected: Non-existent edge cannot be removed``) while the set engine
accepted them (agent-PROBED census, same doc sec 2).

The fix (``src/zanzibar/schema/compiler.py::_node_removal_fence`` ->
``SchemaInfo.unremovable_node_shapes``, refused in ``WildcardIndex.remove_node``) is
pinned here as a PROPERTY over every node of four schemas: each removal is either refused
with the store untouched, or EXACT, meaning that

  A. answers equal the oracle over the tuples NOT incident to the node;
  C. every remaining tuple can then be removed and re-added through the write path (no
     wedge) and answers still equal that oracle;
  B. re-adding the incident tuples restores the full-setup oracle's answers.

Plus the exact shape sets (pins the derivation) and a non-vacuity control (subject nodes
stay removable, so the fence is not "refuse everything").
"""

import pytest
from sqlmodel import select

from zanzibar.graphindex.core import ReachabilityIndex
from zanzibar.graphindex.models import Node
from zanzibar.graphindex.outbox import outbox_watermark
from zanzibar.graphindex.processor import DeltaProcessor
from zanzibar.graphindex.wildcard import WildcardIndex
from tests.oracle import Oracle, parse_schema_ast, t as otuple
from tests.wildcard_helpers import make_wildcard_index
from zanzibar.schema import (AdmissionRejected, Entity, RelationalTriple,
                               parse_openfga_schema)

BASE = """
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define blocked: [user]
    define editor: [user, group#member]
"""
DOC_SETUP = [
    ('...', 'user', 'alice', 'member', 'group', 'h'),
    ('member', 'group', 'h', 'member', 'group', 'g'),
    ('member', 'group', 'g', 'editor', 'doc', 'x'),
    ('...', 'user', 'bob', 'editor', 'doc', 'x'),
    ('...', 'user', 'carol', 'editor', 'doc', 'x'),
    ('...', 'user', 'carol', 'blocked', 'doc', 'x'),
]
TTU = """
type user
type folder
  relations
    define editor: [user]
type doc
  relations
    define parent: [folder]
    define editor: [user] or editor from parent
    define viewer: editor
"""
TTU_SETUP = [
    ('...', 'user', 'u', 'editor', 'folder', 'f'),
    ('...', 'folder', 'f', 'parent', 'doc', 'd'),
    ('...', 'user', 'bob', 'editor', 'doc', 'd'),
]
CASES = {
    'boolean': (BASE + '    define viewer: editor but not blocked\n', DOC_SETUP),
    'pure-computed': (BASE + '    define viewer: editor\n', DOC_SETUP),
    'pure-union': (BASE + '    define viewer: [user] or editor\n', DOC_SETUP),
    'ttu': (TTU, TTU_SETUP),
}
# The compiled fence, pinned exactly. Matches the census agent's independent derivation
# (2026-10-03b) on all four schemas.
EXPECTED_SHAPES = {
    'boolean': {('doc', 'blocked'), ('doc', 'editor'), ('doc', 'viewer'),
                ('doc', 'viewer.0'), ('doc', 'viewer.1')},
    'pure-computed': {('doc', 'editor'), ('doc', 'viewer')},
    'pure-union': {('doc', 'editor'), ('doc', 'viewer')},
    'ttu': {('doc', 'editor'), ('doc', 'parent'), ('doc', 'viewer'),
            ('folder', '...'), ('folder', 'editor')},
}


def _sp(x):
    return Ellipsis if x == '...' else x


def _incident(raw, node):
    return (raw[0], raw[1], raw[2]) == node or (raw[3], raw[4], raw[5]) == node


class _G:
    """One graph store written through the SANCTIONED path (RuleSet.apply + cascade)."""

    def __init__(self, schema):
        self.rs = parse_openfga_schema(schema, enable_boolean=True)
        self.session, self.widx = make_wildcard_index(self.rs.schema_info, store_id='v',
                                                      paranoia='off')
        self.proc = (DeltaProcessor(self.widx, self.rs.compiled)
                     if self.rs.compiled is not None and self.rs.compiled.plans else None)

    def write(self, raw, add=True):
        wm = outbox_watermark(self.session, 'v')
        tr = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]),
                              _sp(raw[0]))
        for d in list(self.rs.apply(tr)):
            args = ('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                    d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
            (self.widx.add_tuple if add else self.widx.remove_tuple)(*args)
        if self.proc is not None:
            self.proc.run_cascade(wm)
        self.session.commit()

    def nodes(self):
        return sorted({(n.predicate, n.type, n.name) for n in
                       self.session.exec(select(Node).where(Node.store_id == 'v')).all()
                       if n.wildcard == ''})

    def answers(self, grid):
        fresh = WildcardIndex(ReachabilityIndex(self.session, store_id='v'),
                              self.rs.schema_info)
        return {q: fresh.check(*q) for q in grid}


def _grid(schema, setup):
    ast = parse_schema_ast(schema)
    subs = {(r[0], r[1], r[2]) for r in setup} | {('...', 'user', 'v')}
    objs = {(r[4], r[5]) for r in setup}
    return [(s[0], s[1], s[2], r, ot, on)
            for (ot, on) in sorted(objs) for s in sorted(subs)
            for r in sorted(r for (t_, r) in ast if t_ == ot)]


def _oracle(schema, tuples):
    return Oracle(schema, [otuple(*r) for r in tuples])


def _all_nodes(case):
    schema, setup = CASES[case]
    g = _G(schema)
    for raw in setup:
        g.write(raw)
    nodes = g.nodes()
    g.session.close()
    return [(case, n) for n in nodes]


NODE_CASES = [p for c in sorted(CASES) for p in _all_nodes(c)]


@pytest.mark.parametrize('case', sorted(CASES))
def test_fence_shapes_are_exactly_the_rewrite_straddled_shapes(case):
    rs = parse_openfga_schema(CASES[case][0], enable_boolean=True)
    assert set(rs.schema_info.unremovable_node_shapes) == EXPECTED_SHAPES[case]


@pytest.mark.parametrize('case, node', NODE_CASES,
                         ids=[f'{c}-{n[1]}:{n[2]}#{n[0]}' for c, n in NODE_CASES])
def test_remove_node_is_exact_or_refused(case, node):
    schema, setup = CASES[case]
    grid = _grid(schema, setup)
    full = _oracle(schema, setup)
    g = _G(schema)
    for raw in setup:
        g.write(raw)
    shape = (node[1], node[0])

    try:
        g.widx.remove_node(_sp(node[0]), node[1], node[2])
        g.session.commit()
    except ValueError as e:                     # AdmissionRejected, or I5's ValueError
        g.session.rollback()
        if 'the schema rewrites tuples on' in str(e):
            # the TK113 fence refused: only ever on a straddled shape (not over-broad)
            assert isinstance(e, AdmissionRejected)
            assert shape in EXPECTED_SHAPES[case], f'fence over-refused {shape}'
        got = g.answers(grid)
        assert [q for q in grid if got[q] != full.check(*q)] == [], 'a refusal wrote'
        return

    assert shape not in EXPECTED_SHAPES[case], f'{shape} must be refused, was admitted'
    reduced = [r for r in setup if not _incident(r, node)]
    orc = _oracle(schema, reduced)
    got = g.answers(grid)
    assert [q for q in grid if got[q] != orc.check(*q)] == [], 'A: diverged after removal'
    for raw in reduced:                          # C: no wedge, and still exact
        g.write(raw, add=False)
        g.write(raw)
    got = g.answers(grid)
    assert [q for q in grid if got[q] != orc.check(*q)] == [], 'C: diverged after churn'
    for raw in setup:                            # B: restoring the incident tuples
        if _incident(raw, node):
            g.write(raw)
    got = g.answers(grid)
    assert [q for q in grid if got[q] != full.check(*q)] == [], 'B: did not restore'
    g.session.close()


@pytest.mark.parametrize('case', sorted(CASES))
def test_non_vacuity_user_nodes_are_still_removable(case):
    """A fence that refused every node would pass the property above. Every user node --
    a subject no rewrite straddles -- must actually be REMOVED (no exception)."""
    schema, setup = CASES[case]
    users = [n for c, n in NODE_CASES if c == case and n[1] == 'user']
    assert users
    for node in users:
        g = _G(schema)
        for raw in setup:
            g.write(raw)
        g.widx.remove_node(_sp(node[0]), node[1], node[2])
        g.session.commit()
        g.session.close()


def test_fence_refuses_the_row_witness_on_a_pure_schema():
    """The witness from the module docstring, refused with the INSTEAD named."""
    schema, setup = CASES['pure-computed']
    g = _G(schema)
    for raw in setup:
        g.write(raw)
    with pytest.raises(AdmissionRejected) as ei:
        g.widx.remove_node('editor', 'doc', 'x')
    msg = str(ei.value)
    assert 'doc:x#editor cannot be removed directly' in msg and 'RuleSet.apply' in msg
    g.session.rollback()
    g.session.close()


@pytest.mark.parametrize('case', ['pure-computed', 'pure-union', 'ttu'])
def test_fence_is_filled_on_the_non_boolean_compile_path_too(case):
    """``compile_ruleset(..., enable_boolean=False)`` returns from its own branch; the
    fence must be filled there as well (it was the one path the property tests above,
    which all compile with booleans on, could not see)."""
    rs = parse_openfga_schema(CASES[case][0], enable_boolean=False)
    assert set(rs.schema_info.unremovable_node_shapes) == EXPECTED_SHAPES[case]
