"""PROTOTYPE of deliverables (b) swarm + (c) un-hardcoded TTU tupleset.

`swarm_schema_asts` is the proposed replacement for `tests/test_hypothesis.py::schema_asts`.
Two changes:
  (c) the TTU tupleset relation is drawn from the SAME expression grammar as every other
      relation (multi-type, boolean, wildcard, neg-only-arm), at a drawn topological
      position so it can reference earlier relations;
  (b) each draw first picks a FEATURE SUBSET to enable, then generates deeply inside it.

`swarm_op_pool` co-generates the candidate pool from the SAME AST, so every candidate is
schema-valid by construction (the graph/set admission asymmetry constraint).
"""
from __future__ import annotations

import sys

sys.path.insert(0, r'C:\Users\user\PycharmProjects\graph-reachability-zanzibar-index')

from hypothesis import strategies as st
from zanzibar_utils_v1 import (Computed, Direct, Exclusion, Intersection, Restriction,
                               TTU, Union)

# --- the tiny universe, now typed ------------------------------------------- #
TYPE_NAMES = {'user': ['u1', 'u2'], 'doc': ['d1', 'd2'], 'folder': ['f1']}
SUBJECT_TYPES = ('user', 'doc', 'folder')

# --- (b) the SWARM feature switches ----------------------------------------- #
# Each switch gates one generator arm.  The names are checked against the cell alphabet
# by `test_swarm_switches_map_onto_alphabet` (see design doc §2.3) so a switch cannot
# exist that reaches no cell, and no cell-bearing arm can exist without a switch.
SWARM_SWITCHES = (
    'ts_boolean',        # tupleset body may be Union/Intersection/Exclusion
    'ts_negonly',        # tupleset carries a restriction ONLY in a negative arm
    'ts_multitype',      # tupleset restricts >1 entity type
    'ts_wildcard',       # tupleset carries a subject-wildcard restriction
    'ts_computed',       # tupleset body may be Computed / TTU (rewritten arms)
    'ts_userset',        # tupleset carries a userset restriction  [expect REJECT]
    'body_boolean',      # non-tupleset bodies may be Union/Intersection/Exclusion
    'body_userset',      # the G2 concrete-userset leaf  [doc#r_k]
    'body_wildcard',     # subject-wildcard restrictions in ordinary bodies
    'body_computed',     # Computed references
    'body_ttu',          # TTU references
    'multi_type',        # a second object type (folder) participates
    'self_ttu',          # a TTU whose target is its own head relation
    'owc',               # object-wildcard shapes declared on some relation
)


@st.composite
def swarm_subset(draw, p: int = 2):
    """A feature subset.  A uniformly-drawn FOCUS switch is forced ON so no switch can
    starve; the rest are independent coin flips.  1 draw in `all_on_every` is the FULL
    set -- today's distribution, kept as an explicit stratum so the swarm cannot reduce
    coverage of what the current generator already reaches (constraint 2)."""
    stratum = draw(st.integers(min_value=0, max_value=3))
    if stratum == 0:
        return frozenset(SWARM_SWITCHES)                       # "all on" stratum
    focus = draw(st.sampled_from(SWARM_SWITCHES))
    if stratum == 1:
        return frozenset({focus})                              # "minimal" stratum
    rest = {s for s in SWARM_SWITCHES
            if draw(st.integers(min_value=0, max_value=p)) == 0}
    return frozenset(rest | {focus})


def _base_directs(sw, types):
    out = [(Restriction('user', '...', False),)]
    if 'body_wildcard' in sw:
        out.append((Restriction('user', '...', False), Restriction('user', '...', True)))
        out.append((Restriction('user', '...', True),))
    return out


@st.composite
def swarm_schema_asts(draw, sw=None):
    """Relations on ``doc`` in topo order.  ``parent`` (the TTU tupleset) is inserted at a
    DRAWN position and its body drawn from the same grammar."""
    if sw is None:
        sw = draw(swarm_subset())
    n = draw(st.integers(min_value=2, max_value=5))
    names = [f'r{i}' for i in range(n)]
    ts_types = ['doc']
    if 'multi_type' in sw and 'ts_multitype' in sw:
        ts_types = ['doc', 'folder']
    ppos = draw(st.integers(min_value=0, max_value=n - 1)) if (
        'ts_computed' in sw) else 0

    def expr(i, depth, *, tupleset: bool):
        """One relation body.  ``tupleset=True`` uses the tupleset switches."""
        pre = 'ts_' if tupleset else 'body_'
        leaves = []
        if tupleset:
            rs = [Restriction(t, '...', False) for t in ts_types]
            leaves.append(Direct(tuple(rs)))
            if 'ts_wildcard' in sw:
                leaves.append(Direct(tuple(rs) + (Restriction(ts_types[0], '...', True),)))
            if 'ts_userset' in sw and i > 0:
                leaves.append(Direct(tuple(rs) + (
                    Restriction('doc', draw(st.sampled_from(names[:i])), False),)))
        else:
            leaves.append(Direct(draw(st.sampled_from(_base_directs(sw, ts_types)))))
        if i > 0:
            ref = draw(st.sampled_from(names[:i]))
            if (pre + 'computed') in sw or (not tupleset and 'body_computed' in sw):
                leaves.append(Computed(ref))
            if not tupleset and 'body_ttu' in sw:
                leaves.append(TTU(ref, 'parent'))
            if tupleset and 'ts_computed' in sw:
                leaves.append(Computed(ref))
            if not tupleset and 'body_userset' in sw and \
                    draw(st.integers(min_value=0, max_value=2)) == 0:
                leaves.append(Direct((Restriction(
                    'doc', draw(st.sampled_from(names[:i])), False),)))
        leaf = st.sampled_from(leaves)
        boolean_on = (('ts_boolean' if tupleset else 'body_boolean') in sw)
        if depth >= 2 or not boolean_on:
            return draw(leaf)
        kind = draw(st.sampled_from(['leaf', 'leaf', 'union', 'intersection', 'exclusion']))
        if kind == 'leaf':
            return draw(leaf)
        a, b = expr(i, depth + 1, tupleset=tupleset), expr(i, depth + 1, tupleset=tupleset)
        if kind == 'union':
            return Union((a, b))
        if kind == 'intersection':
            return Intersection((a, b))
        return Exclusion(a, b)

    ast = {}
    for i, name in enumerate(names):
        if i == ppos:
            body = expr(i, 0, tupleset=True)
            if 'ts_negonly' in sw:
                # THE shape: a type occurring ONLY in the negative arm.
                body = Exclusion(body, Direct((Restriction(
                    'folder' if 'multi_type' in sw else 'doc', '...', False),)))
            ast[('doc', 'parent')] = body
        ast[('doc', name)] = expr(i, 0, tupleset=False)
    if ('doc', 'parent') not in ast:
        ast[('doc', 'parent')] = Direct((Restriction('doc', '...', False),))
    if 'self_ttu' in sw and n >= 2:
        # a TTU whose target IS its own head relation, unioned with the existing body
        k = names[-1]
        ast[('doc', k)] = Union((ast[('doc', k)], TTU(k, 'parent')))
    if 'multi_type' in sw:
        ast[('folder', names[0])] = Direct((Restriction('user', '...', False),))
    return ast


def swarm_op_pool(ast):
    """Schema-VALID raw tuples, co-generated from the SAME ast (constraint 1).  Identical
    walk to the current ``_op_pool`` except the subject-name table is TYPED, so a
    multi-type tupleset yields valid `folder:` subjects rather than none."""
    out = []
    for (otype, rel), e in ast.items():
        def directs(x):
            if isinstance(x, Direct):
                yield x
            elif isinstance(x, (Union, Intersection)):
                for c in x.children:
                    yield from directs(c)
            elif isinstance(x, Exclusion):
                yield from directs(x.base)
                yield from directs(x.subtract)
        for d in directs(e):
            for r in d.restrictions:
                names = ['*'] if r.wildcard else TYPE_NAMES.get(r.type, ['x1'])
                for sn in names:
                    for on in TYPE_NAMES[otype]:
                        out.append((r.predicate, r.type, sn, rel, otype, on))
    return sorted(set(out))


@st.composite
def swarm_configs(draw):
    """(ast, owc) -- the object-wildcard-shape subset is drawn from the schema's OWN
    declared (type, relation) pairs, so it can never name a shape that does not exist."""
    sw = draw(swarm_subset())
    ast = draw(swarm_schema_asts(sw=sw))
    owc = frozenset()
    if 'owc' in sw:
        dom = sorted(ast)
        owc = frozenset(draw(st.sets(st.sampled_from(dom), max_size=2)))
    return ast, owc
