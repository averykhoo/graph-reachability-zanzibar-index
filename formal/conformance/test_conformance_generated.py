"""Generated-schema conformance: zcli `sem` vs oracle vs the real set engine
over schema shapes OUTSIDE the 17 curated corpora.

Gap this closes: the hypothesis campaign (tests/test_hypothesis.py) fuzzes
GENERATED schemas against the Python backends + oracle, and the Lean
conformance suite pins zcli against Python — but only over the curated corpus
pool. The two case pools were fully disjoint, so a `sem`/model-fidelity
divergence on a generated shape (nested boolean over TTU-of-derived, wildcard
inside an intersection operand, ...) was invisible to EVERY gate. Here the
generated pool feeds zcli spec mode directly.

Generator: a seeded `random.Random` re-implementation of the hypothesis suite's
`schema_asts` strategy (tests/test_hypothesis.py:64-91) — relations on `doc`
built in topological order (stratifiable by construction, so inside the spec's
verified envelope), depth <= 2 expression trees over Direct/Computed/TTU leaves
and binary Union/Intersection/Exclusion nodes (arity 2 everywhere, satisfying
encode.py's n-ary-fold arity >= 2 constraint), rendered to DSL text via
`unparse_schema_ast` + an explicit `type user` header (the generated ASTs
declare no relations on `user`, so the unparser alone would omit the type
line). It is deliberately NOT imported from tests/test_hypothesis.py: that
module imports `hypothesis` at module level, and the formal/ suite has no
hypothesis dependency (the deterministic-seeded convention of
test_conformance_random.py); duplicating ~30 generator lines is the price of
keeping this suite inside verify.sh's fail-closed formal gate.

Stores: seeded random subsets of the schema-valid raw-tuple pool over the tiny
{u1,u2} x {d1,d2} universe (the hypothesis suite's `_op_pool` shape, Direct
restrictions only, wildcard `*` rows included). Adds the engine rejects
(graph-parity validation) are excluded from the compared store on all three
corners — this gate pins READ semantics; accept/reject parity is pinned by the
matrix/hypothesis suites.

Properties, per case, over the shared grid (grid built from the FULL pool so
out-of-store subjects/objects stay probed): zcli spec == oracle (adjudication
event on failure) and oracle == driven set engine — hence all three agree.

Runtime: exactly one zcli spawn per case (the whole grid batches into one
request); _N_CASES = 40 keeps the module in the tens of seconds.
"""

from __future__ import annotations

import random

import pytest

from zanzibar_utils_v1 import (Computed, Direct, Exclusion, Intersection,
                               Restriction, TTU, Union, unparse_schema_ast)
from tests.oracle import Oracle, t as mk_tuple

from formal.conformance.encode import build_request
from formal.conformance.grid import queries_for, fmt_mismatches as _fmt
from formal.conformance import runner
from formal.conformance.backends import _fresh_session

_N_CASES = 40
SEEDS = list(range(_N_CASES))

USERS = ['u1', 'u2']
DOCS = ['d1', 'd2']

# Mirrors tests/test_hypothesis.py `_BASE_DIRECTS` (concrete / concrete+star /
# star-only direct restriction sets).
_BASE_DIRECTS = [
    (Restriction('user', '...', False),),
    (Restriction('user', '...', False), Restriction('user', '...', True)),
    (Restriction('user', '...', True),),
]


def _gen_ast(rng: random.Random):
    """Seeded port of the hypothesis `schema_asts` strategy: n in [2,5]
    relations r0..r{n-1} on `doc` + a direct `parent` (the TTU tupleset),
    each body a depth<=2 tree whose Computed/TTU leaves reference only EARLIER
    relations (topo order => stratifiable => inside the spec envelope)."""
    n = rng.randint(2, 5)
    names = [f'r{i}' for i in range(n)]
    ast = {('doc', 'parent'): Direct((Restriction('doc', '...', False),))}

    def expr(i: int, depth: int):
        leaves = [Direct(rng.choice(_BASE_DIRECTS))]
        if i > 0:
            ref = rng.choice(names[:i])
            leaves.append(Computed(ref))
            leaves.append(TTU(ref, 'parent'))
        if depth >= 2:
            return rng.choice(leaves)
        kind = rng.choice(['leaf', 'leaf', 'union', 'intersection', 'exclusion'])
        if kind == 'leaf':
            return rng.choice(leaves)
        a, b = expr(i, depth + 1), expr(i, depth + 1)
        if kind == 'union':
            return Union((a, b))
        if kind == 'intersection':
            return Intersection((a, b))
        return Exclusion(a, b)

    for i, name in enumerate(names):
        ast[('doc', name)] = expr(i, 0)
    return ast


def _op_pool(ast):
    """Schema-valid raw tuples over the tiny universe (Direct restrictions
    only) — the hypothesis suite's `_op_pool`, verbatim shape."""
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
                names = ['*'] if r.wildcard else (USERS if r.type == 'user' else DOCS)
                for sn in names:
                    for on in DOCS:
                        out.append((r.predicate, r.type, sn, rel, otype, on))
    return sorted(set(out))


def _case(seed: int):
    """Deterministic (schema_text, pool, store_ops) for one seed."""
    rng = random.Random(seed)
    ast = _gen_ast(rng)
    # `type user` header: the generated AST has no user-typed relations, so the
    # unparser emits no `type user` line; both parsers accept the prepended one.
    schema_text = 'type user\n' + unparse_schema_ast(ast)
    pool = _op_pool(ast)
    store_ops = [op for op in pool if rng.random() < 0.5]
    if not store_ops:                      # degenerate draw: keep one tuple
        store_ops = [pool[0]]
    return schema_text, pool, store_ops


@pytest.mark.parametrize('seed', SEEDS)
def test_generated_schema_zcli_parity(seed):
    schema_text, pool, store_ops = _case(seed)
    have_zcli = True
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        have_zcli = False

    session = _fresh_session()
    from setengine import SetEngine
    eng = SetEngine(session, 's1', schema_text)
    accepted = []
    for op in store_ops:
        try:
            eng.add_tuple(*op)
        except ValueError:
            continue                       # graph-parity rejection: excluded
        accepted.append(mk_tuple(*op))

    # Grid from the FULL pool: names u1,u2,d1,d2 (+ ghosts, *) are always
    # probed, including subjects/objects the store never mentions.
    queries = queries_for(schema_text, [mk_tuple(*op) for op in pool])
    orc = Oracle(schema_text, accepted)
    oracle = [orc.check(*q) for q in queries]
    se = [bool(eng.check(*q)) for q in queries]
    session.close()

    mism = [(queries[i], oracle[i], se[i]) for i in range(len(queries))
            if oracle[i] != se[i]]
    assert not mism, (
        f'[generated seed={seed}] oracle/set-engine disagreement:\n'
        f'schema:\n{schema_text}\nstore={accepted}\n{_fmt(mism, "oracle", "setengine")}')

    if have_zcli:
        spec = runner.run_spec(build_request(schema_text, accepted, queries))
        mism = [(queries[i], spec[i], oracle[i]) for i in range(len(queries))
                if spec[i] != oracle[i]]
        assert not mism, (
            f'[generated seed={seed}] spec/oracle disagreement '
            f'(ADJUDICATION EVENT — plan §8.2):\n'
            f'schema:\n{schema_text}\nstore={accepted}\n{_fmt(mism, "spec", "oracle")}')
