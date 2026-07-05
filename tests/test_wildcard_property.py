"""
Property test (spec §8.4): fixed-seed randomized add/remove sequences over a small
universe, comparing WildcardIndex.check against the reference oracle for the FULL
query grid after every operation, with the invariant checker run each step.

The index is fed DERIVED tuples (via RuleSet.apply); the oracle is fed the RAW input
tuples and does its own expansion. Agreement across the whole grid is the correctness
gate for the entire design.
"""

import random
from types import EllipsisType

import pytest

from zanzibar_utils_v1 import Entity, RelationalTriple, parse_openfga_schema
from tests.oracle import Oracle, OracleTuple
from tests.wildcard_helpers import make_wildcard_index, assert_wildcard_invariants


WILDCARDS_SCHEMA = None  # loaded from fixture in the test


OBJECT_WC = frozenset({('folder', 'viewer'), ('document', 'viewer')})

USERS = ['u1', 'u2']
GROUPS = ['g1', 'g2']
FOLDERS = ['f1', 'f2']
DOCS = ['d1', 'd2']
GHOST = {'user': 'ghostU', 'group': 'ghostG', 'folder': 'ghostF', 'document': 'ghostD'}


def _norm(pred: str | EllipsisType) -> str:
    return '...' if pred is Ellipsis else pred


def _candidate_raw_tuples() -> list[tuple]:
    """All schema-valid raw tuples over the small universe (6-string tuples)."""
    out = []
    viewer_objects = [('folder', f) for f in FOLDERS] + [('document', d) for d in DOCS]
    # object wildcards are valid only for the declared (folder,viewer)/(document,viewer)
    viewer_objects_wc = viewer_objects + [('folder', '*'), ('document', '*')]

    # membership: [user] and [group#member]
    for u in USERS:
        for g in GROUPS:
            out.append(('...', 'user', u, 'member', 'group', g))
    for gi in GROUPS:
        for gj in GROUPS:
            if gi != gj:
                out.append(('member', 'group', gi, 'member', 'group', gj))

    # viewer grants: [user, user:*, group#member, group:*#member] + object wildcards
    for (o_type, o_name) in viewer_objects_wc:
        for u in USERS:
            out.append(('...', 'user', u, 'viewer', o_type, o_name))
        out.append(('...', 'user', '*', 'viewer', o_type, o_name))
        for g in GROUPS:
            out.append(('member', 'group', g, 'viewer', o_type, o_name))
        out.append(('member', 'group', '*', 'viewer', o_type, o_name))

    # parent hierarchy: [folder]
    for fi in FOLDERS:
        for fj in FOLDERS:
            if fi != fj:
                out.append(('...', 'folder', fi, 'parent', 'folder', fj))
    for f in FOLDERS:
        for d in DOCS:
            out.append(('...', 'folder', f, 'parent', 'document', d))
    return out


def _query_grid() -> list[tuple]:
    """(s_pred, s_type, s_name, relation, o_type, o_name) queries.

    Kept intentionally small (spec §8.4, <5s CI budget). Each type contributes a
    concrete, a ghost, and the wildcard name so every probe path is exercised; the
    from-chain is covered by a folder-viewer userset subject.
    """
    subjects = [
        ('...', 'user', 'u1'), ('...', 'user', GHOST['user']), ('...', 'user', '*'),
        ('member', 'group', 'g1'), ('member', 'group', GHOST['group']), ('member', 'group', '*'),
        ('viewer', 'folder', 'f1'),                     # userset subject (from-chain)
    ]
    targets = [
        ('viewer', 'folder', 'f1'), ('viewer', 'folder', GHOST['folder']), ('viewer', 'folder', '*'),
        ('viewer', 'document', 'd1'), ('viewer', 'document', GHOST['document']), ('viewer', 'document', '*'),
        ('member', 'group', 'g1'), ('member', 'group', '*'),
    ]
    return [(sp, st, sn, rel, ot, on)
            for (sp, st, sn) in subjects
            for (rel, ot, on) in targets]


def _raw_to_triple(raw: tuple) -> RelationalTriple:
    s_pred = Ellipsis if raw[0] == '...' else raw[0]
    return RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), s_pred)


def _apply(widx, ruleset, raw, op):
    """Apply an add/remove of a raw tuple through the ruleset to the façade."""
    fn = widx.add_tuple if op == 'add' else widx.remove_tuple
    for d in ruleset.apply(_raw_to_triple(raw)):
        fn(_norm(d.subject_predicate), d.subject.type, d.subject.name,
           d.relation, d.object.type, d.object.name)


@pytest.mark.parametrize('seed', [0, 1, 2])
def test_wildcard_property_vs_oracle(load_fga_schema, seed):
    schema = load_fga_schema('wildcards.fga')
    ruleset = parse_openfga_schema(schema, object_wildcard_shapes=OBJECT_WC)
    session, widx = make_wildcard_index(ruleset.schema_info)

    pool = _candidate_raw_tuples()
    grid = _query_grid()
    rng = random.Random(seed)

    present: set[tuple] = set()
    history: list[tuple] = []

    def fail(msg, query=None):
        lines = [msg, f'seed={seed}', 'history:']
        lines += [f'  {op} {raw}' for (op, raw) in history]
        if query is not None:
            lines.append(f'failing query: {query}')
        pytest.fail('\n'.join(lines))

    STEPS = 12
    for _ in range(STEPS):
        # choose op
        if not present or rng.random() < 0.6:
            candidates = [r for r in pool if r not in present]
            if not candidates:
                op, raw = 'remove', rng.choice(sorted(present))
            else:
                op, raw = 'add', rng.choice(candidates)
        else:
            op, raw = 'remove', rng.choice(sorted(present))

        try:
            _apply(widx, ruleset, raw, op)
            session.commit()
        except ValueError:
            # invalid or cycle-forming tuple: roll back this op, leave state unchanged
            session.rollback()
            continue

        if op == 'add':
            present.add(raw)
        else:
            present.discard(raw)
        history.append((op, raw))

        # structural invariants must hold after every committed op
        try:
            assert_wildcard_invariants(widx)
        except AssertionError as e:
            fail(f'invariant violation: {e}')

        # full-grid oracle comparison
        oracle = Oracle(schema, [OracleTuple(*r) for r in present])
        for q in grid:
            got = widx.check(*q)
            exp = oracle.check(*q)
            if got != exp:
                fail(f'check mismatch: index={got} oracle={exp}', query=q)

    session.close()
