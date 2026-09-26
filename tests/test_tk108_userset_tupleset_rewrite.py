"""TK108 (user decision 2026-09-27): a tupleset may not restrict to a userset.

``define parent: [folder#member]`` used by ``viewer from parent`` is refused at PARSE time
by both parsers (`zanzibar_utils_v1.py::_validate_tuplesets_direct`, oracle twin
`tests/oracle.py::_validate_tuplesets_direct`), as OpenFGA refuses it. ``from`` takes a
stored parent's type and name and ignores its predicate, so the ``#member`` was silently
dropped; the graph refused the schema while the set engine and the oracle answered.

This module pins the other half of that decision: the REWRITE the refusal message and the
parser comment recommend answers exactly what the refused shape answered. The expectation
is DERIVED, not hand-written: the refused schema is evaluated by the oracle over its
UNCHECKED parse (`tests/oracle.py::parse_schema_ast_unchecked`), which is the semantics the
set engine and the oracle actually served before TK108. The rewrite runs through
`tests/parity.py::ParityEngine` with the graph index IN (4-way: graph, both set engines,
oracle, unanimous per query).

The one-off probe that preceded the refusal ran the refused shapes through the set engines
too (graph dropped) and found 0 differing answers of 135;
`docs/tk108-userset-tuplesets-2026-09-27.md` sec 2 quotes it.

CONTROL (built in, `test_naive_rewrite_is_caught`): dropping the ``#member`` WITHOUT adding
``parent_member`` must differ from the legacy answers -- otherwise the grid could not see
the userset reading at all and the equality tests would pass vacuously.

SABOTAGE (2026-09-27, literal output, each on a throwaway copy / restored file):

- S1, break the recommended rewrite: ``parent_member: owner from parent`` in the
  ``userset`` case::

      FAILED ...::test_rewrite_answers_what_the_refused_shape_answered[userset]
      1 failed, 6 passed

- S2, disable the product refusal (``if r.predicate != '...':`` -> ``if False:`` in
  `zanzibar_utils_v1.py::_validate_tuplesets_direct`)::

      FAILED ...::test_refused_shape_is_refused_by_both_parsers[bare-beside-userset]
      FAILED ...::test_refused_shape_is_refused_by_both_parsers[userset]
      FAILED ...::test_refused_shape_is_refused_by_both_parsers[wildcard-userset]
      3 failed, 4 passed

  INSTRUMENT: the first S1 attempt used a ``sed`` whose anchor matched 0 times and came
  back ``7 passed`` -- an unmutated run, not a surviving mutant. The anchor count is now
  asserted before a mutation is believed.
"""
from __future__ import annotations

import itertools

import pytest

import zanzibar_utils_v1 as Z
from tests import oracle as O
from tests.parity import ParityEngine

HEAD = """
type user
type folder
  relations
    define member: [user]
    define owner: [user]
    define viewer: [user]
"""

BASE = [('...', 'user', 'alice', 'member', 'folder', 'f1'),
        ('...', 'user', 'bob', 'viewer', 'folder', 'f1'),
        ('...', 'user', 'carol', 'viewer', 'folder', 'f2'),
        ('...', 'user', 'dave', 'member', 'folder', 'f2'),
        ('...', 'user', 'dave', 'owner', 'folder', 'f1'),
        ('...', 'user', 'erin', 'viewer', 'doc', 'd1')]

SUBJECTS = [('...', 'user', u) for u in ('alice', 'bob', 'carol', 'dave', 'erin', 'zed')] + \
           [('member', 'folder', 'f1'), ('viewer', 'folder', 'f1'),
            ('member', 'folder', 'f2'), ('...', 'folder', 'f2')]
OBJECTS = ('d1', 'd2', 'd3')

# name -> (refused schema, its tupleset links, rewrite schema, its links,
#          {refused relation: rewrite relations whose OR is its twin})
CASES = {
    'userset': (
        HEAD + 'type doc\n  relations\n'
               '    define parent: [folder#member]\n'
               '    define viewer: [user] or viewer from parent\n',
        [('member', 'folder', 'f1', 'parent', 'doc', 'd1'),
         ('member', 'folder', 'f2', 'parent', 'doc', 'd2')],
        HEAD + 'type doc\n  relations\n'
               '    define parent: [folder]\n'
               '    define parent_member: member from parent\n'
               '    define viewer: [user] or viewer from parent\n',
        [('...', 'folder', 'f1', 'parent', 'doc', 'd1'),
         ('...', 'folder', 'f2', 'parent', 'doc', 'd2')],
        {'viewer': ('viewer',), 'parent': ('parent_member',)}),
    'wildcard-userset': (
        HEAD + 'type doc\n  relations\n'
               '    define parent: [folder:*#member]\n'
               '    define viewer: [user] or viewer from parent\n',
        [('member', 'folder', '*', 'parent', 'doc', 'd1')],
        HEAD + 'type doc\n  relations\n'
               '    define parent: [folder:*]\n'
               '    define parent_member: member from parent\n'
               '    define viewer: [user] or viewer from parent\n',
        [('...', 'folder', '*', 'parent', 'doc', 'd1')],
        {'viewer': ('viewer',), 'parent': ('parent_member',)}),
    # A tupleset mixing a bare type and a userset of it: the links are split by which
    # restriction they were stored under, so neither reading is lost.
    'bare-beside-userset': (
        HEAD + 'type doc\n  relations\n'
               '    define parent: [folder, folder#member]\n'
               '    define viewer: [user] or viewer from parent\n',
        [('member', 'folder', 'f1', 'parent', 'doc', 'd1'),
         ('...', 'folder', 'f2', 'parent', 'doc', 'd2')],
        HEAD + 'type doc\n  relations\n'
               '    define parent: [folder]\n'
               '    define parent_via_member: [folder]\n'
               '    define parent_member: member from parent_via_member\n'
               '    define viewer: [user] or viewer from parent or viewer from parent_via_member\n',
        [('...', 'folder', 'f1', 'parent_via_member', 'doc', 'd1'),
         ('...', 'folder', 'f2', 'parent', 'doc', 'd2')],
        {'viewer': ('viewer',), 'parent': ('parent', 'parent_member')}),
}


def _legacy_oracle(schema: str, links) -> O.Oracle:
    """The oracle as it answered the refused schema before TK108: same evaluator, the
    parse without the refusal. Built by hand because `Oracle.__init__` parses checked."""
    o = O.Oracle.__new__(O.Oracle)
    o.ast = O.parse_schema_ast_unchecked(schema)
    o.tuples = [O.OracleTuple(*r) for r in BASE + links]
    return o


def _answers(case: str, relmap_override=None):
    old_schema, old_links, new_schema, new_links, relmap = CASES[case]
    relmap = relmap_override or relmap
    legacy = _legacy_oracle(old_schema, old_links)
    pe = ParityEngine(new_schema)
    try:
        assert pe.graph is not None, f'rewrite must run 4-way: {pe.graph_drop_reason}'
        for r in BASE + new_links:
            assert pe.add_tuple(*r), r
        out = []
        for (sp, st, sn), rel, obj in itertools.product(SUBJECTS, relmap, OBJECTS):
            want = legacy.check(sp, st, sn, rel, 'doc', obj)
            got = any(pe.check(sp, st, sn, r2, 'doc', obj) for r2 in relmap[rel])
            out.append(((sp, st, sn, rel, obj), want, got))
        return out
    finally:
        pe.close()


@pytest.mark.parametrize('case', sorted(CASES))
def test_refused_shape_is_refused_by_both_parsers(case):
    old_schema = CASES[case][0]
    with pytest.raises(ValueError, match='tupleset may not restrict to a userset'):
        Z.parse_schema_ast(old_schema)
    with pytest.raises(ValueError, match='tupleset may not restrict to a userset'):
        O.parse_schema_ast(old_schema)


@pytest.mark.parametrize('case', sorted(CASES))
def test_rewrite_answers_what_the_refused_shape_answered(case):
    rows = _answers(case)
    diffs = [q for q, want, got in rows if want != got]
    assert not diffs, f'{case}: rewrite differs from the refused shape on {diffs}'
    # Non-vacuous: the grid must contain positive answers, including through the
    # userset reading (a `parent` query answered True by the legacy semantics).
    assert sum(want for _q, want, _g in rows) > 0
    assert any(want for (q, want, _g) in rows if q[3] == 'parent')


def test_naive_rewrite_is_caught():
    """CONTROL: `parent: [folder]` WITHOUT `parent_member` loses the userset reading, and
    this grid must see that, or the equality test above proves nothing."""
    rows = _answers('userset', relmap_override={'parent': ('parent',)})
    diffs = [q for q, want, got in rows if want != got]
    assert diffs, 'the grid cannot distinguish the naive rewrite -- the pin is vacuous'
