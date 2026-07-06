"""
P5 validation matrix (spec §7): the artifact that pins "same semantics".

  * 4-way (union + wildcard, wildcards.fga): graph WildcardIndex, reference oracle, and
    the set engine under BOTH SetOps -- unanimous accept/reject after every op and
    identical `check` over the full grid.
  * 4-way (boolean, boolean_wildcards.fga): SAME machinery, graph included -- the
    boolean-IVM acceptance event (boolean spec §10). The graph maintains derived
    relations via the delta-processor cascade; post-op runs the I9 fixpoint audit.
  * De Morgan equivalence (§7.3): for the demorgans fixtures, oracle == set engine ==
    graph pointwise across the grid.

Runs under both SetOps implementations, which must be indistinguishable.
"""

import random
from types import EllipsisType

import pytest
from sqlmodel import Session, SQLModel, create_engine

from index_v4.outbox import outbox_watermark
from index_v4.processor import DeltaProcessor
from zanzibar_utils_v1 import parse_openfga_schema, Entity, RelationalTriple
from tests.oracle import Oracle, OracleTuple
from tests.wildcard_helpers import make_wildcard_index, assert_wildcard_invariants
from setengine import SetEngine, PySets, RoaringSets, ALL_SETOPS
from tests.test_wildcard_property import _candidate_raw_tuples, _query_grid, OBJECT_WC


def _norm(pred: str | EllipsisType) -> str:
    return '...' if pred is Ellipsis else pred


def _fresh_session() -> Session:
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


# ---------------------------------------------------------------------------
# Backend adapters: each maps a raw tuple op to accept/reject + a check() surface
# ---------------------------------------------------------------------------

class GraphBackend:
    name = 'graph'

    def __init__(self, schema, object_wc=frozenset()):
        self.ruleset = parse_openfga_schema(schema, object_wildcard_shapes=object_wc)
        self.session, self.widx = make_wildcard_index(self.ruleset.schema_info, store_id='g')
        self.proc = None
        if self.ruleset.compiled is not None and self.ruleset.compiled.plans:
            self.proc = DeltaProcessor(self.widx, self.ruleset.compiled)

    def _derived(self, raw, op):
        sp = Ellipsis if raw[0] == '...' else raw[0]
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
        fn = self.widx.add_tuple if op == 'add' else self.widx.remove_tuple
        for d in self.ruleset.apply(triple):
            fn(_norm(d.subject_predicate), d.subject.type, d.subject.name,
               d.relation, d.object.type, d.object.name)

    def apply(self, raw, op) -> bool:
        try:
            wm = outbox_watermark(self.session, 'g')
            self._derived(raw, op)
            if self.proc is not None:
                self.proc.run_cascade(wm)               # synchronous v1: same txn
            self.session.commit()
            return True
        except ValueError:
            self.session.rollback()
            return False

    def check(self, q):
        return self.widx.check(*q)

    def post_op(self):
        assert_wildcard_invariants(self.widx)
        if self.proc is not None:
            self.proc.audit_fixpoint()                  # I9, all keys (paranoia dose)

    def close(self):
        self.session.close()


class SetBackend:
    def __init__(self, schema, object_wc, ops):
        self.name = f'set:{ops.name}'
        self.session = _fresh_session()
        self.se = SetEngine(self.session, 's_' + ops.name, schema,
                            object_wildcard_shapes=object_wc, ops=ops)

    def apply(self, raw, op) -> bool:
        try:
            (self.se.add_tuple if op == 'add' else self.se.remove_tuple)(*raw)
            self.session.commit()
            return True
        except ValueError:
            self.session.rollback()
            return False

    def check(self, q):
        return self.se.check(*q)

    def post_op(self):
        pass

    def close(self):
        self.session.close()


class OracleBackend:
    """The oracle has no write state; it re-reads `present` each grid comparison."""
    name = 'oracle'

    def __init__(self, schema):
        self.schema = schema
        self.present = None

    def bind(self, present):
        self.present = present

    def check(self, q):
        oracle = Oracle(self.schema, [OracleTuple(*r) for r in self.present])
        return oracle.check(*q)


class MultiBackend:
    """Fan each op out to every stateful backend; assert unanimous accept/reject (§7.1)."""

    def __init__(self, stateful, decider):
        self.stateful = stateful          # backends that accept/reject and hold state
        self.decider = decider            # the backend whose decision drives `present`

    def apply(self, raw, op) -> bool:
        results = {b.name: b.apply(raw, op) for b in self.stateful}
        decision = results[self.decider.name]
        assert all(v == decision for v in results.values()), \
            f'accept/reject disagreement on {op} {raw}: {results}'
        for b in self.stateful:
            b.post_op()
        return decision


# ---------------------------------------------------------------------------
# 4-way: union + wildcard
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('seed', [0, 1, 2])
def test_matrix_4way_union_wildcard(load_fga_schema, seed):
    schema = load_fga_schema('wildcards.fga')
    graph = GraphBackend(schema, OBJECT_WC)
    set_py = SetBackend(schema, OBJECT_WC, PySets)
    set_backends = [set_py] + ([SetBackend(schema, OBJECT_WC, RoaringSets)] if RoaringSets else [])
    oracle = OracleBackend(schema)
    mb = MultiBackend([graph] + set_backends, decider=graph)

    pool = _candidate_raw_tuples()
    grid = _query_grid()
    rng = random.Random(seed)
    present, history = set(), []

    for _ in range(14):
        if not present or rng.random() < 0.6:
            cands = [r for r in pool if r not in present]
            op, raw = ('add', rng.choice(cands)) if cands else ('remove', rng.choice(sorted(present)))
        else:
            op, raw = 'remove', rng.choice(sorted(present))

        accepted = mb.apply(raw, op)
        if accepted:
            (present.add if op == 'add' else present.discard)(raw)
            history.append((op, raw))

        oracle.bind(present)
        all_backends = [graph, oracle] + set_backends
        for q in grid:
            answers = {b.name: b.check(q) for b in all_backends}
            if len(set(answers.values())) != 1:
                pytest.fail(f'check disagreement seed={seed} q={q}: {answers}\n'
                            + '\n'.join(f'  {o} {r}' for o, r in history))

    for b in [graph] + set_backends:
        b.close()


# ---------------------------------------------------------------------------
# 4-way: boolean (THE acceptance event, boolean spec §10 -- the graph joins the
# same grids and after-every-op comparison it used to refuse)
# ---------------------------------------------------------------------------

BOOL_USERS = ['u1', 'u2']
BOOL_GROUPS = ['g1', 'g2']
BOOL_DOCS = ['d1', 'd2']


def _boolean_pool():
    out = []
    for u in BOOL_USERS:
        for g in BOOL_GROUPS:
            out.append(('...', 'user', u, 'member', 'group', g))
    for gi in BOOL_GROUPS:
        for gj in BOOL_GROUPS:
            if gi != gj:
                out.append(('member', 'group', gi, 'member', 'group', gj))
    for d in BOOL_DOCS:
        out.append(('...', 'user', '*', 'public', 'doc', d))
        for u in BOOL_USERS:
            out.append(('...', 'user', u, 'blocked', 'doc', d))
            out.append(('...', 'user', u, 'editor', 'doc', d))
        for g in BOOL_GROUPS:
            out.append(('member', 'group', g, 'editor', 'doc', d))
    for di in BOOL_DOCS:
        for dj in BOOL_DOCS:
            if di != dj:
                out.append(('...', 'doc', di, 'parent', 'doc', dj))
    return out


def _boolean_grid():
    subjects = [('...', 'user', 'u1'), ('...', 'user', 'ghostU'), ('...', 'user', '*'),
                ('member', 'group', 'g1'), ('member', 'group', 'ghostG')]
    rels = ['viewer', 'restricted', 'inherited', 'editor', 'public', 'blocked']
    targets = [(r, 'doc', d) for r in rels for d in ['d1', 'd2', 'ghostD']]
    return [(sp, st, sn, r, ot, on) for (sp, st, sn) in subjects for (r, ot, on) in targets]


@pytest.mark.parametrize('seed', [0, 1, 2])
def test_matrix_4way_boolean(load_fga_schema, seed):
    """Boolean store, 4-way: graph (processor-maintained) · oracle · set engine under
    both SetOps -- unanimous accept/reject after every op, identical check over the
    full grid. This is the feature's acceptance event (boolean spec §10)."""
    schema = load_fga_schema('boolean_wildcards.fga')
    graph = GraphBackend(schema)
    set_backends = [SetBackend(schema, frozenset(), PySets)] \
        + ([SetBackend(schema, frozenset(), RoaringSets)] if RoaringSets else [])
    oracle = OracleBackend(schema)
    mb = MultiBackend([graph] + set_backends, decider=graph)

    pool = _boolean_pool()
    grid = _boolean_grid()
    rng = random.Random(seed)
    present, history = set(), []

    for _ in range(16):
        if not present or rng.random() < 0.6:
            cands = [r for r in pool if r not in present]
            op, raw = ('add', rng.choice(cands)) if cands else ('remove', rng.choice(sorted(present)))
        else:
            op, raw = 'remove', rng.choice(sorted(present))

        accepted = mb.apply(raw, op)
        if accepted:
            (present.add if op == 'add' else present.discard)(raw)
            history.append((op, raw))

        oracle.bind(present)
        all_backends = [graph, oracle] + set_backends
        for q in grid:
            answers = {b.name: b.check(q) for b in all_backends}
            if len(set(answers.values())) != 1:
                pytest.fail(f'boolean check disagreement seed={seed} q={q}: {answers}\n'
                            + '\n'.join(f'  {o} {r}' for o, r in history))

    for b in [graph] + set_backends:
        b.close()


# ---------------------------------------------------------------------------
# De Morgan equivalence (§7.3): the property the retired xfail was gesturing at
# ---------------------------------------------------------------------------

# (fixture, [(lhs_relation, rhs_relation, object_type)]) -- relations that must be
# pointwise-equal for all subjects/objects by De Morgan's laws.
DEMORGAN_EQUIVS = {
    # matchable_conds and matched_roles chain the same negations; a direct pair is the
    # two _all_* -- but the fixtures encode the law through the full chain, so we assert
    # the documented invariant: the reverse fixture's requirement_met equals the negation
    # structure. We take the simplest robust anchor: the two demorgans_law fixtures agree
    # with the oracle (already covered); here we assert oracle == set engine pointwise on
    # every relation, which is the operational meaning of "same semantics".
}


def _demorgan_pool(schema_text):
    """All schema-valid raw tuples over a tiny universe, derived from the AST directions."""
    from zanzibar_utils_v1 import parse_schema_ast, Direct
    ast = parse_schema_ast(schema_text)
    names = {'user': ['a', 'b'], 'role': ['r1'], 'cond': ['c1'], 'attr': ['at1'],
             'doc': ['dc1'], 'group': ['g1']}
    out = []
    for (otype, rel), expr in ast.items():
        from zanzibar_utils_v1 import _iter_directs
        for direct in _iter_directs(expr):
            for r in direct.restrictions:
                onames = names.get(otype, ['o1'])
                snames = ['*'] if r.wildcard else names.get(r.type, ['s1'])
                for on in onames:
                    for sn in snames:
                        out.append((r.predicate, r.type, sn, rel, otype, on))
    return list(dict.fromkeys(out))     # dedup, keep order


@pytest.mark.parametrize('fixture', ['demorgans_law_1.fga', 'demorgans_law_2.fga', 'demorgans_reverse.fga'])
@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_demorgan_oracle_equals_setengine_equals_graph(load_fga_schema, fixture, ops):
    """The operational De Morgan check, 3 evaluators since the P7 flip: oracle, set
    engine, and the graph backend agree pointwise on every relation over randomized
    tuple sets."""
    schema = load_fga_schema(fixture)
    pool = _demorgan_pool(schema)
    from zanzibar_utils_v1 import parse_schema_ast
    ast = parse_schema_ast(schema)
    rels = sorted({(ot, rel) for (ot, rel) in ast})

    # a compact query grid: every relation, a couple of subjects, a couple of objects
    subjects = [('...', 'user', 'a'), ('...', 'user', 'ghost'), ('...', 'user', '*'),
                ('...', 'doc', 'dc1'), ('...', 'doc', '*')]

    rng = random.Random(0)
    for trial in range(4):
        present = set(rng.sample(pool, k=min(len(pool), rng.randint(1, len(pool)))))
        session = _fresh_session()
        se = SetEngine(session, f't{trial}', schema, ops=ops)
        graph = GraphBackend(schema)
        for raw in sorted(present):
            try:
                se.add_tuple(*raw)
            except ValueError:
                present.discard(raw)
                continue
            assert graph.apply(raw, 'add'), f'graph rejected what the set engine took: {raw}'
        session.commit()
        graph.post_op()
        oracle = Oracle(schema, [OracleTuple(*r) for r in present])

        for (ot, rel) in rels:
            for (sp, st, sn) in subjects:
                for on in ['dc1', 'ghost', '*', 'r1', 'c1', 'at1']:
                    q = (sp, st, sn, rel, ot, on)
                    got, exp, g = se.check(*q), oracle.check(*q), graph.check(q)
                    assert got == exp == g, \
                        f'{fixture} {ops.name} q={q} set={got} oracle={exp} graph={g} ' \
                        f'present={sorted(present)}'
        graph.close()
        session.close()
