"""
ParityEngine (boolean spec §8.4): one façade over oracle + set engine (both SetOps) +
graph backend simultaneously, asserting semantic lockstep after every operation.

Per op:
  * identical accept/reject on every stateful backend (same error family: ValueError);
  * on reject: I12 -- each backend's row multiset (ids ignored) is unchanged;
  * on accept: check-parity over the query grid (universe ∪ ghosts ∪ '*'), all
    backends vs the oracle (ground truth).

The oracle is check-only and stateless (rebuilt from the raw-tuple multiset per
comparison; see docs/spec-deviations.md #3) -- so per-op parity is *check* parity;
lookup/lookup_reverse are served by the graph backend (or the first set engine while a
boolean schema keeps the graph out, pre-P7) and pinned by their own dedicated tests.

Boolean schemas run 4-way since the P7 matrix flip: the graph joins automatically when
compile succeeds (its writes run the delta-processor cascade in-transaction, its post-op
runs the I9 fixpoint audit). Schemas the graph still refuses -- decision-15 scope,
cyclic derived dependencies -- degrade to 3-way, oracle + both set engines.

Paranoia mode (spec §8.1) defaults ON: the graph store gets pre/post-commit invariant
checking (index_v4.invariants.install_paranoia) plus the per-op I12 snapshots here.
"""

from __future__ import annotations

import random
from types import EllipsisType
from collections import Counter

from sqlmodel import Session, SQLModel, create_engine, select

from index_v4.invariants import snapshot_rows
from setengine import SetEngine, ALL_SETOPS
from setengine.models import TupleV1
from zanzibar_utils_v1 import (CyclicDerivedDependency, Entity, RelationalTriple,
                               UnsupportedByGraphIndex, parse_openfga_schema,
                               parse_schema_ast, _iter_directs)
from tests.oracle import Oracle, OracleTuple
from tests.wildcard_helpers import make_wildcard_index, assert_wildcard_invariants

RawTuple = tuple[str, str, str, str, str, str]

GHOST_NAME = 'zz-ghost'


def _norm(pred: str | EllipsisType) -> str:
    return '...' if pred is Ellipsis else pred


def _fresh_session() -> Session:
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


class _GraphSide:
    """The graph backend: RuleSet rewrite fan-out into a WildcardIndex, plus the
    delta-processor cascade for schemas with derived (boolean) relations."""
    name = 'graph'

    def __init__(self, ruleset, *, paranoia: bool):
        self.ruleset = ruleset
        self.session, self.widx = make_wildcard_index(
            ruleset.schema_info, store_id='pg', paranoia=paranoia)
        self.proc = None
        if ruleset.compiled is not None and ruleset.compiled.plans:
            from index_v4.processor import DeltaProcessor
            self.proc = DeltaProcessor(self.widx, ruleset.compiled)

    def apply(self, raw: RawTuple, op: str) -> bool:
        from index_v4.outbox import outbox_watermark
        sp = Ellipsis if raw[0] == '...' else raw[0]
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
        fn = self.widx.add_tuple if op == 'add' else self.widx.remove_tuple
        try:
            wm = outbox_watermark(self.session, 'pg')
            for d in self.ruleset.apply(triple):
                fn(_norm(d.subject_predicate), d.subject.type, d.subject.name,
                   d.relation, d.object.type, d.object.name)
            if self.proc is not None:
                self.proc.run_cascade(wm)                # synchronous v1: same txn
            self.session.commit()
            return True
        except ValueError:
            self.session.rollback()
            return False

    def check(self, q) -> bool:
        return self.widx.check(*q)

    def snapshot(self):
        return snapshot_rows(self.session, 'pg')

    def post_op(self) -> None:
        assert_wildcard_invariants(self.widx)
        if self.proc is not None:
            self.proc.audit_fixpoint()                   # I9, all keys (paranoia dose)

    def close(self) -> None:
        self.session.close()


class _SetSide:
    def __init__(self, schema: str, object_wc, ops):
        self.name = f'set:{ops.name}'
        self.session = _fresh_session()
        self.store_id = 's_' + ops.name
        self.se = SetEngine(self.session, self.store_id, schema,
                            object_wildcard_shapes=object_wc, ops=ops)

    def apply(self, raw: RawTuple, op: str) -> bool:
        try:
            (self.se.add_tuple if op == 'add' else self.se.remove_tuple)(*raw)
            self.session.commit()
            return True
        except ValueError:
            self.session.rollback()
            return False

    def check(self, q) -> bool:
        return self.se.check(*q)

    def snapshot(self) -> Counter:
        rows = self.session.exec(
            select(TupleV1).where(TupleV1.store_id == self.store_id)).all()
        return Counter(
            (r.subject_predicate, r.subject_type, r.subject_name,
             r.relation, r.object_type, r.object_name) for r in rows)

    def post_op(self) -> None:
        pass

    def close(self) -> None:
        self.session.close()


class ParityEngine:
    """The default integration engine (spec §8.4): all backends in lockstep."""

    def __init__(self, schema: str, *,
                 object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset(),
                 paranoia: bool = True,
                 grid_cap: int = 600,
                 seed: int = 0):
        self.schema = schema
        self.paranoia = paranoia
        self.grid_cap = grid_cap
        self._rng = random.Random(seed)
        self.ast = parse_schema_ast(schema)

        # Graph joins iff the schema compiles for it. Cyclic derived dependencies
        # (CyclicDerivedDependency, a ValueError subclass) must also degrade to
        # 3-way -- blind-audit X7: catching only UnsupportedByGraphIndex made
        # ParityEngine unconstructible on exactly the schema class (cyclic
        # booleans) where the evaluator memo bug lived. ONLY those two: a bare
        # ValueError from compile is a regression that must surface, not silently
        # shrink the matrix to 3-way (review 3).
        try:
            ruleset = parse_openfga_schema(schema, object_wildcard_shapes=object_wildcard_shapes)
            self.graph: _GraphSide | None = _GraphSide(ruleset, paranoia=paranoia)
            self.graph_drop_reason: str | None = None
        except (UnsupportedByGraphIndex, CyclicDerivedDependency) as e:
            self.graph = None
            self.graph_drop_reason = f'{type(e).__name__}: {e}'

        self.set_sides = [_SetSide(schema, object_wildcard_shapes, ops) for ops in ALL_SETOPS]
        self.stateful = ([self.graph] if self.graph else []) + self.set_sides

        # The raw-tuple set IS the oracle's input (set semantics: TupleV1 is unique).
        self.present: set[RawTuple] = set()
        # Names seen per entity type, for universe-∪-ghosts-∪-'*' grid construction.
        self._names_by_type: dict[str, set[str]] = {}

    # ------------------------------------------------------------------ #
    # Op API
    # ------------------------------------------------------------------ #

    def add_tuple(self, *raw: str) -> bool:
        return self._apply(tuple(raw), 'add')

    def remove_tuple(self, *raw: str) -> bool:
        return self._apply(tuple(raw), 'remove')

    def check(self, *q) -> bool:
        """Unanimous check across every backend + the oracle."""
        answers = {b.name: b.check(q) for b in self.stateful}
        answers['oracle'] = self._oracle().check(*q)
        assert len(set(answers.values())) == 1, f'check disagreement on {q}: {answers}'
        return answers['oracle']

    def lookup(self, *args):
        """Served by the richest live backend; cross-backend lookup parity is pinned by
        dedicated tests (the oracle cannot do lookups -- deviations log #3)."""
        side = self.graph if self.graph else self.set_sides[0]
        return (side.widx if self.graph else side.se).lookup(*args)

    def lookup_reverse(self, *args):
        side = self.graph if self.graph else self.set_sides[0]
        return (side.widx if self.graph else side.se).lookup_reverse(*args)

    def close(self) -> None:
        for b in self.stateful:
            b.close()

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _apply(self, raw: RawTuple, op: str) -> bool:
        if op == 'add' and raw in self.present:
            # Zanzibar raw tuples are a SET: a duplicate add is an idempotent no-op
            # (TupleV1's unique constraint already makes the set engine no-op it; the
            # graph core is deliberately ref-counted for REWRITTEN fan-in -- two
            # different raw tuples may derive the same edge -- so raw-level
            # idempotence lives here, at the tuple API boundary). Found by the P8
            # stateful machine: add,add,remove diverged graph from oracle otherwise.
            return True

        pre = {b.name: b.snapshot() for b in self.stateful} if self.paranoia else {}

        results = {b.name: b.apply(raw, op) for b in self.stateful}
        decision = next(iter(results.values()))
        assert all(v == decision for v in results.values()), \
            f'accept/reject disagreement on {op} {raw}: {results}'

        if not decision:
            if self.paranoia:
                # I12: a rejected op leaves every backend's row multiset untouched.
                for b in self.stateful:
                    assert b.snapshot() == pre[b.name], \
                        f'I12 violated: {b.name} state changed by rejected {op} {raw}'
            return False

        (self.present.add if op == 'add' else self.present.discard)(raw)
        self._note_names(raw)
        for b in self.stateful:
            b.post_op()
        self._assert_grid_parity(context=f'{op} {raw}')
        return True

    def _note_names(self, raw: RawTuple) -> None:
        _, s_type, s_name, _, o_type, o_name = raw
        if s_name != '*':
            self._names_by_type.setdefault(s_type, set()).add(s_name)
        if o_name != '*':
            self._names_by_type.setdefault(o_type, set()).add(o_name)

    def _oracle(self) -> Oracle:
        return Oracle(self.schema, [OracleTuple(*r) for r in self.present])

    def _grid(self) -> list[tuple]:
        """Universe ∪ ghosts ∪ '*' (spec §8.4), derived from the schema's own shapes:
        subjects from Direct restrictions, targets from declared (object_type, relation).
        Deterministically sampled down to grid_cap if large."""
        subject_shapes: set[tuple[str, str]] = set()
        for expr in self.ast.values():
            for direct in _iter_directs(expr):
                for r in direct.restrictions:
                    subject_shapes.add((r.type, r.predicate))

        subjects: list[tuple[str, str, str]] = []
        for (s_type, s_pred) in sorted(subject_shapes):
            names = sorted(self._names_by_type.get(s_type, set()))
            for name in names + [GHOST_NAME, '*']:
                subjects.append((s_pred, s_type, name))

        queries: list[tuple] = []
        for (o_type, rel) in sorted(self.ast):
            o_names = sorted(self._names_by_type.get(o_type, set()))
            for on in o_names + [GHOST_NAME]:
                for (sp, st, sn) in subjects:
                    queries.append((sp, st, sn, rel, o_type, on))

        if len(queries) > self.grid_cap:
            queries = self._rng.sample(queries, self.grid_cap)
        return queries

    def _assert_grid_parity(self, context: str) -> None:
        oracle = self._oracle()
        for q in self._grid():
            expected = oracle.check(*q)
            for b in self.stateful:
                got = b.check(q)
                assert got == expected, (
                    f'check parity broken after {context}: q={q} '
                    f'{b.name}={got} oracle={expected}')
