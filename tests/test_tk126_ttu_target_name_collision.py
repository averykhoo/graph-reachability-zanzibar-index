"""TK126 -- a TTU whose target NAME is also a boolean relation somewhere is SERVED by the
graph index, and the graph gives the oracle's answers on it.

Property guarded
----------------
``x from parent`` where ``x`` names a boolean (``and`` / ``but not``) relation on SOME type
is the ordinary OpenFGA idiom (every type defines its own ``viewer``). Until 2026-10-08 the
graph compiler refused it, or crashed, because two compile-time I5 checks compared a TTU's
target to the derived relations by NAME across every type:

* ``src/zanzibar/schema/compiler.py::_validate_ttu_tuplesets`` refused variants B and C with
  ``UnsupportedByGraphIndex`` (scope gap: the set engine served them);
* ``src/zanzibar/schema/boolean.py::compile_boolean_schema``'s exclusivity loop raised a bare
  ``ValueError`` dumping an internal ``Rule`` on variant D, in BOTH backends (the set engine
  compiles the graph ``RuleSet`` for cycle-rejection parity and lets a bare ``ValueError``
  surface).

Design (a) of ``docs/tk126-ttu-target-boolean-name-2026-10-07.md`` (decided 2026-10-07d on
the TK126 row) keys both checks on ``(type, relation)``: a TTU rewrite rule produces subject
nodes whose TYPE is the stored tupleset tuple's subject type, which admission pins to the
tupleset's declared restriction types. This module pins the outcome:

1. every variant and neighbour COMPILES for the graph, and the set engine constructs WITH a
   ruleset (``test_graph_and_set_engine_both_compile``);
2. a scripted walk with known answers, then a seeded add/remove walk, runs through
   ``tests/parity.py::ParityEngine`` with the graph REQUIRED present (oracle + both
   ``SetOps`` set engines + graph, paranoia ON, full-grid parity after every op);
3. the composed system agrees with ``tests/oracle.py`` on the full grid along six
   construction paths: ``ConnectedStore`` sync and async (+ ``catch_up``), each read
   through the store AND straight off its graph index, ``build_index(bulk=True)``,
   ``build_index(bulk=False)`` and ``rebuild_index``;
4. ``lookup`` / ``lookup_reverse`` / ``expand`` match the oracle-composed references
   (``tests/test_lookup_oracle.py::_Gate``, graph required);
5. the two neighbours that ARE still refused (a parent of the boolean relation's own type:
   ``B_multi``, ``D_self``) are refused as ``CyclicDerivedDependency`` -- a documented,
   separate scope limit (boolean spec sec 1.9) -- with no internal-object dump in the
   message, and the set engine serves them ruleset-less;
6. R1 of the design doc: after the fix neither guard is reachable from a checked parse, so
   both are pinned on HAND-BUILT inputs that violate I5 on ``(type, relation)``. The
   ``compile_boolean_schema`` guard reads the subject types off the emitted Filters, not
   off ``_member_types`` (the function RC1 got wrong), and that independence is pinned by
   neutering ``_member_types`` and watching the guard still fire.

The variant schemas are the scout's reconstructions (doc sec 0) plus its neighbours
(sec 2.3), and the old TK116 witness for the refused family (``C_team``).

RED on the pre-fix tree (HEAD 7296eb1 + the TK124/TK125 working tree, 2026-10-08), literal
(first error line of each kind; ``C_cross`` compiled before the fix too, it is a control)::

    32 failed, 10 passed in 20.39s
    B / B_star / C:  UnsupportedByGraphIndex: relation doc#reader: TTU 'viewer' from 'parent'
        targets the derived relation 'viewer', but the containing relation is not itself
        boolean-tainted, ... an undeclared tupleset relation being the usual cause
        (decision-15 family)
    C_team:          UnsupportedByGraphIndex: relation doc#can_view: TTU 'viewer' from ...
    D_nested:        UnsupportedByGraphIndex: relation folder#viewer: TTU 'viewer' from ...
    D:               ValueError: Rule then-pattern carries a derived subject predicate:
        Rule(if_pattern=RelationalTriplePattern(subject_predicate=None, ...
        relation='parent', object_type='doc', ...), then_pattern=RelationalTriplePattern(
        subject_predicate='viewer', ..., relation='viewer.1', object_type='doc', ...))
    test_i5_guard_fires_on_a_hand_built_taint_regression: AssertionError
        (the message was the Rule dump, no 'folder#viewer')
    test_compiler_check_refuses_a_hand_built_taint_regression: Regex pattern did not
        match. Expected regex: 'folder#viewer'

Green after the fix: ``42 passed in 104.75s``.

The ``SlXt`` cases (the Lean model's cross-type probe) were added after that first red
run; their red is observed under S4 below (the guard's pre-fix NAME test restored):
``6 failed, 42 deselected`` on ``-k "SlXt or slxt"``, every SlXt case. Under S5 (only the
compiler check reverted) they stay green: ``6 passed`` -- SlXt's container is tainted.

SABOTAGE (2026-10-08, ``.scratch`` runner, each anchor asserted to match once, the file
restored byte-for-byte and sha256-checked), literal summaries:

- S1, the ``compile_boolean_schema`` I5 guard neutered (``if bad:`` -> ``if False:``),
  on the five hand-built tests::

      FAILED ...::test_i5_guard_fires_on_a_hand_built_taint_regression
      FAILED ...::test_i5_guard_reads_admission_not_member_types
      FAILED ...::test_undeclared_tupleset_falls_back_to_the_name_test
      3 failed, 2 passed

- S2, the guard reads ``_member_types`` only (the Filter-admitted types dropped)::

      FAILED ...::test_i5_guard_reads_admission_not_member_types
      1 failed, 4 passed

- S3, ``_validate_ttu_tuplesets``' first loop neutered::

      FAILED ...::test_compiler_check_refuses_a_hand_built_taint_regression
      FAILED ...::test_undeclared_tupleset_falls_back_to_the_name_test
      2 failed, 3 passed

- S4, the guard reverted to the NAME test only (compiler check left type-aware), on
  ``test_graph_and_set_engine_both_compile``: ``6 failed, 1 passed`` (B, B_star, C, C_team,
  D, D_nested). S5, the compiler check reverted to the NAME test only (guard left
  type-aware): ``5 failed, 2 passed`` (D is green there: its container is tainted, so only
  the guard sees it). So BOTH halves of the fix are load-bearing.
- S6, INSTRUMENT control: the graph's compiled ``Rule``s with if-pattern ``doc#parent``
  dropped after ``compile_boolean_schema`` (the set engines evaluate without a ruleset, so
  only the graph goes wrong), whole module: ``24 failed, 18 passed`` -- every
  ParityEngine, ConnectedStore/build and lookup case red except ``C_cross``, whose TTU is
  inside a tainted relation and so compiles to a plan node, not a ``Rule``.
"""
from __future__ import annotations

import random
import warnings

import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar.connectedstore import (ConnectedStore, TupleSource, build_index,
                                     rebuild_index, save_schema)
from zanzibar.schema import (CyclicDerivedDependency, UnsupportedByGraphIndex,
                             parse_openfga_schema, parse_schema_ast)
from zanzibar.schema import _iter_directs
from zanzibar.schema import boolean as boolean_mod
from zanzibar.schema import compiler as compiler_mod
from zanzibar.schema.boolean import compile_boolean_schema, compute_taint
from zanzibar.schema.compiler import _emit_expr, compile_ruleset, derive_schema_info
from zanzibar.schema.parser import _parse_schema_ast_unchecked
from tests.oracle import Oracle, OracleTuple
from tests.parity import ParityEngine
from tests.test_lookup_oracle import _Gate

HEAD = 'model\n  schema 1.1\n'

# ---- the variants (doc sec 0) --------------------------------------------------------

#: B: the containing type defines the boolean ``viewer``; the TTU reaches the PLAIN
#: ``folder#viewer``.
B = HEAD + """type user
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder]
    define banned: [user]
    define reader: [user] or viewer from parent
    define viewer: reader but not banned
"""

#: C: an UNRELATED third type defines a boolean ``viewer``; ``doc`` has no boolean at all.
C = HEAD + """type user
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder]
    define reader: [user] or viewer from parent
type report
  relations
    define banned: [user]
    define viewer: [user] but not banned
"""

#: D: the TTU sits INSIDE the boolean relation and names that relation's own name.
D = HEAD + """type user
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder]
    define banned: [user]
    define viewer: ([user] or viewer from parent) but not banned
"""

# ---- neighbours (doc sec 2.3) --------------------------------------------------------

#: D_nested: the plain ``folder#viewer`` recurses on the colliding name itself.
D_NESTED = HEAD + """type user
type folder
  relations
    define parent: [folder]
    define viewer: [user] or viewer from parent
type doc
  relations
    define parent: [folder]
    define banned: [user]
    define viewer: ([user] or viewer from parent) but not banned
"""
#: B_star: a star tupleset beside the plain one.
B_STAR = B.replace('define parent: [folder]', 'define parent: [folder, folder:*]')
#: C_cross: the tupleset admits the type whose ``viewer`` IS boolean, so ``doc#reader``
#: is genuinely tainted (a type-aware check must still handle the mixed case).
C_CROSS = C.replace('define parent: [folder]', 'define parent: [folder, report]')
#: C_team: the old TK116 witness of the refused family
#: (``ttu-target-name-is-derived-elsewhere``), verbatim.
C_TEAM = ('type user\ntype folder\n  relations\n'
          '    define blocked: [user]\n    define viewer: [user] but not blocked\n'
          'type team\n  relations\n    define viewer: [user]\n'
          'type doc\n  relations\n'
          '    define parent: [team]\n    define can_view: viewer from parent\n')

#: SlXt: `formal/lean/ZanzibarProofs/GraphIndex/LeafRules.lean::SlXt`, the Lean model's
#: "cross-type drop" probe, as DSL. Before TK126 Python refused it (the model docstring
#: said so); now it is served, and Python allocates the TTU arm as the closure leaf
#: `access.0` with `banned` at `access.1` (probed 2026-10-08), where the model drops the arm
#: -- the recorded `formal/CORRESPONDENCE.md` sec 7 gap, dead inside `W4Fragment`.
SLXT = HEAD + """type user
type team
  relations
    define z: [user]
    define y: [user]
    define viewer: z but not y
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder]
    define banned: [user]
    define access: viewer from parent but not banned
"""

SERVED = {'B': B, 'C': C, 'D': D, 'D_nested': D_NESTED, 'B_star': B_STAR,
          'C_cross': C_CROSS, 'C_team': C_TEAM, 'SlXt': SLXT}

#: Still refused, for a DIFFERENT reason (recursion through a boolean relation).
B_MULTI = B.replace('define parent: [folder]', 'define parent: [folder, doc]')
D_SELF = D.replace('define parent: [folder]', 'define parent: [folder, doc]')
CYCLIC = {'B_multi': B_MULTI, 'D_self': D_SELF}


def _u(rel, otype, oname, name='a'):
    return ('...', 'user', name, rel, otype, oname)


def _p(ptype, pname, otype='doc', oname='a', rel='parent'):
    return ('...', ptype, pname, rel, otype, oname)


#: Scripted walks with KNOWN answers: (op, raw-or-query, expected). 'check' rows are the
#: non-vacuity floor -- each schema has at least one True that only the TTU can produce,
#: and (where a ban exists) the ban must flip it to False.
SCRIPTS = {
    'B': [('add', _u('viewer', 'folder', 'a')), ('add', _p('folder', 'a')),
          ('check', _u('reader', 'doc', 'a'), True), ('check', _u('viewer', 'doc', 'a'), True),
          ('add', _u('banned', 'doc', 'a')),
          ('check', _u('viewer', 'doc', 'a'), False), ('check', _u('reader', 'doc', 'a'), True),
          ('remove', _p('folder', 'a')), ('check', _u('reader', 'doc', 'a'), False)],
    'C': [('add', _u('viewer', 'folder', 'a')), ('add', _p('folder', 'a')),
          ('check', _u('reader', 'doc', 'a'), True),
          ('add', _u('viewer', 'report', 'a', name='b')),
          ('check', _u('viewer', 'report', 'a', name='b'), True),
          ('add', _u('banned', 'report', 'a', name='b')),
          ('check', _u('viewer', 'report', 'a', name='b'), False),
          ('check', _u('reader', 'doc', 'a'), True)],
    'D': [('add', _u('viewer', 'folder', 'a')), ('add', _p('folder', 'a')),
          ('check', _u('viewer', 'doc', 'a'), True),
          ('add', _u('banned', 'doc', 'a')), ('check', _u('viewer', 'doc', 'a'), False),
          ('remove', _u('banned', 'doc', 'a')), ('check', _u('viewer', 'doc', 'a'), True)],
    'D_nested': [('add', _u('viewer', 'folder', 'b')),
                 ('add', _p('folder', 'b', otype='folder', oname='a')),
                 ('add', _p('folder', 'a')),
                 ('check', _u('viewer', 'folder', 'a'), True),
                 ('check', _u('viewer', 'doc', 'a'), True),
                 ('add', _u('banned', 'doc', 'a')), ('check', _u('viewer', 'doc', 'a'), False)],
    'B_star': [('add', _u('viewer', 'folder', 'a')), ('add', _p('folder', 'a')),
               ('check', _u('reader', 'doc', 'a'), True),
               ('add', _u('banned', 'doc', 'a')), ('check', _u('viewer', 'doc', 'a'), False)],
    'C_cross': [('add', _u('viewer', 'report', 'a')), ('add', _p('report', 'a')),
                ('check', _u('reader', 'doc', 'a'), True),
                ('add', _u('banned', 'report', 'a')), ('check', _u('reader', 'doc', 'a'), False),
                ('add', _u('viewer', 'folder', 'b')), ('add', _p('folder', 'b')),
                ('check', _u('reader', 'doc', 'a'), True)],
    'C_team': [('add', _u('viewer', 'team', 'a')), ('add', _p('team', 'a')),
               ('check', _u('can_view', 'doc', 'a'), True),
               ('add', _u('viewer', 'folder', 'a')), ('add', _u('blocked', 'folder', 'a')),
               ('check', _u('viewer', 'folder', 'a'), False),
               ('check', _u('can_view', 'doc', 'a'), True)],
    'SlXt': [('add', _u('viewer', 'folder', 'a')), ('add', _p('folder', 'a')),
             ('check', _u('access', 'doc', 'a'), True),
             ('add', _u('z', 'team', 'a')), ('check', _u('viewer', 'team', 'a'), True),
             ('add', _u('banned', 'doc', 'a')), ('check', _u('access', 'doc', 'a'), False)],
}


def test_slxt_python_allocation_is_the_recorded_gap():
    """The Lean model drops ``SlXt``'s TTU arm (``LeafRules.lean::lrXt_cross_type_drop``:
    ``banned`` inherits index 0). Python keeps it as a pure closure leaf. This pins the
    PYTHON side of the recorded gap, so a change to either allocation is seen and the
    CORRESPONDENCE sec 7 entry re-adjudicated."""
    ns = parse_openfga_schema(SLXT).compiled.namespace
    leaves = {k[1]: (f.index, f.positive, f.kind) for k, f in ns.items()
              if k[0] == 'doc' and k[1].startswith('access.')}
    assert leaves == {'access.0': (0, True, 'closure'), 'access.1': (1, False, 'closure')}

NAMES = ('a', 'b')


def _candidates(schema: str) -> list[tuple]:
    """Every raw tuple a Direct restriction admits over ``NAMES`` (``*`` for a wildcard)."""
    out = set()
    for (ot, rel), expr in parse_schema_ast(schema).items():
        for d in _iter_directs(expr):
            for r in d.restrictions:
                for sn in (['*'] if r.wildcard else NAMES):
                    for on in NAMES:
                        out.add((r.predicate, r.type, sn, rel, ot, on))
    return sorted(out)


def _grid(schema: str) -> list[tuple]:
    """Bare subjects (incl. a ghost name) and userset subjects x every declared relation."""
    ast = parse_schema_ast(schema)
    types = sorted({t for (t, _r) in ast} | {'user'})
    subjects = [('...', t, n) for t in types for n in (*NAMES, 'zz')]
    subjects += [(r, t, n) for (t, r) in ast for n in NAMES]
    objs = [(t, r, n) for (t, r) in ast for n in NAMES]
    return [(sp, st, sn, r, ot, on) for (sp, st, sn) in subjects for (ot, r, on) in objs]


def _walk(schema: str, seed: int, steps: int) -> list[tuple[str, tuple]]:
    """A seeded add/remove walk over the candidate pool (ops are proposals: a backend may
    refuse one, e.g. a data cycle, and every driver below must then refuse it too)."""
    rng = random.Random(seed)
    cands = _candidates(schema)
    present: set = set()
    ops = []
    for _ in range(steps):
        t = rng.choice(cands)
        op = 'remove' if (t in present and rng.random() < 0.5) else 'add'
        (present.add if op == 'add' else present.discard)(t)
        ops.append((op, t))
    return ops


def _session() -> Session:
    e = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(e)
    return Session(e)


# ---- 1. compiles ---------------------------------------------------------------------

@pytest.mark.parametrize('name', sorted(SERVED))
def test_graph_and_set_engine_both_compile(name):
    """The graph compiles every variant, and ``SetEngine`` constructs WITH its graph
    ``RuleSet`` (cycle rejection on) -- before TK126 D raised a bare ``ValueError`` here."""
    rs = parse_openfga_schema(SERVED[name])
    assert rs.rules_and_filters
    pe = ParityEngine(SERVED[name])
    try:
        assert pe.graph is not None, pe.graph_drop_reason
        for side in pe.set_sides:
            assert side.se._ruleset is not None, side.name
    finally:
        pe.close()


# ---- 2. ParityEngine: scripted + seeded walk -----------------------------------------

def _run_script(pe: ParityEngine, script) -> int:
    trues = 0
    for row in script:
        if row[0] == 'check':
            got = pe.check(*row[1])            # unanimous across every backend + oracle
            assert got is row[2], (row, got)
            trues += got
        else:
            ok = (pe.add_tuple if row[0] == 'add' else pe.remove_tuple)(*row[1])
            assert ok, f'scripted {row[0]} refused: {row[1]}'
    return trues


@pytest.mark.parametrize('seed', [1, 2])
@pytest.mark.parametrize('name', sorted(SERVED))
def test_parity_engine_four_way(name, seed):
    """Graph REQUIRED (``pe.graph is not None``), paranoia ON; ParityEngine asserts
    unanimity, I12 and full-grid oracle parity after every op internally."""
    pe = ParityEngine(SERVED[name], paranoia=True, seed=seed)
    try:
        assert pe.graph is not None, pe.graph_drop_reason
        assert _run_script(pe, SCRIPTS[name]) >= 1
        accepted = 0
        for op, t in _walk(SERVED[name], seed, 24):
            accepted += bool((pe.add_tuple if op == 'add' else pe.remove_tuple)(*t))
        assert accepted >= 12, f'only {accepted} of 24 walk ops accepted'
    finally:
        pe.close()


# ---- 3. composed system: six construction paths vs the oracle -------------------------

@pytest.mark.parametrize('name', sorted(SERVED))
def test_connected_store_and_build_paths_match_the_oracle(name):
    schema = SERVED[name]
    s_live, s_async, s_src = _session(), _session(), _session()
    try:
        live = ConnectedStore(s_live, 'live', schema=schema, paranoia='full')
        asy = ConnectedStore(s_async, 'asy', schema=schema, sync=False, paranoia='full')
        save_schema(s_src, 'b1', schema)
        save_schema(s_src, 'b2', schema)
        save_schema(s_src, 'b3', schema)
        s_src.commit()
        srcs = [TupleSource(s_src, sid) for sid in ('b1', 'b2', 'b3')]
        present: set = set()
        ops = [r for r in SCRIPTS[name] if r[0] != 'check'] + _walk(schema, 7, 30)
        refused = 0
        for op, t in ops:
            try:
                (live.add_tuple if op == 'add' else live.remove_tuple)(*t)
            except ValueError:
                # Refused by the sync graph (a data cycle); nothing was written, so the
                # other paths must not see it either.
                s_live.rollback()
                refused += 1
                continue
            (asy.add_tuple if op == 'add' else asy.remove_tuple)(*t)
            for src in srcs:
                (src.add if op == 'add' else src.remove)(*t)
            s_src.commit()
            (present.add if op == 'add' else present.discard)(t)
        asy.catch_up()
        bulk = build_index(s_src, 'b1', bulk=True)
        incr = build_index(s_src, 'b2', bulk=False)
        assert (bulk.constructor, incr.constructor) == ('bulk', 'incremental')
        build_index(s_src, 'b3', bulk=True)
        rebuilt = rebuild_index(s_src, 'b3', bulk=False)
        paths = {'live': live.check, 'live.graph': live.widx.check,
                 'async': asy.check, 'async.graph': asy.widx.check,
                 'build-bulk': bulk[1].check, 'build-incr': incr[1].check,
                 'rebuild': rebuilt[1].check}
        orc = Oracle(schema, [OracleTuple(*t) for t in present])
        bad, trues = [], 0
        grid = _grid(schema)
        for q in grid:
            want = orc.check(*q)
            trues += bool(want)
            got = {k: f(*q) for k, f in paths.items()}
            if any(v != want for v in got.values()):
                bad.append((q, want, got))
        assert not bad, f'{len(bad)} mismatches vs the oracle, first: {bad[:3]}'
        assert trues >= 3, f'vacuous grid: {trues} oracle-True answers of {len(grid)}'
        assert len(present) >= 4
    finally:
        for s in (s_live, s_async, s_src):
            s.close()


# ---- 4. lookup surfaces --------------------------------------------------------------

@pytest.mark.parametrize('name', sorted(SERVED))
def test_lookup_surfaces_match_the_oracle(name):
    schema = SERVED[name]
    pool = sorted({tuple('n1' if x == 'a' else 'n2' if x == 'b' else x for x in t)
                   for t in _candidates(schema)})
    g = _Gate(schema, frozenset(), pool)          # allow_graph_absent=False: graph required
    try:
        assert g.graph is not None
        g.assert_surfaces(context='initial')
        rng = random.Random(3)
        batteries = 0
        for _ in range(14):
            raw = rng.choice(pool)
            op = 'remove' if (raw in g.present and rng.random() < 0.5) else 'add'
            if g.apply(op, raw):
                g.assert_surfaces(context=f'{op} {raw}')
                batteries += 1
        assert batteries >= 8
    finally:
        g.close()


# ---- 5. the neighbours that stay refused, for their own reason -------------------------

@pytest.mark.parametrize('name', sorted(CYCLIC))
def test_boolean_recursion_neighbours_stay_a_cycle_refusal(name):
    """``parent: [folder, doc]`` lets the TTU reach the derived ``doc#viewer`` itself: a
    derived dependency cycle (boolean spec sec 1.9, ``boolean.py::_stratify``), NOT TK126.
    The refusal is the documented class with a readable message, and the set engine
    serves the schema ruleset-less (3-way, oracle-checked)."""
    with pytest.raises(CyclicDerivedDependency) as ei:
        parse_openfga_schema(CYCLIC[name])
    assert 'RelationalTriplePattern' not in str(ei.value)
    assert 'Rule(' not in str(ei.value)
    pe = ParityEngine(CYCLIC[name])
    try:
        assert pe.graph is None
        assert all(side.se._ruleset is None for side in pe.set_sides)
        assert pe.add_tuple(*_u('viewer', 'folder', 'a'))
        assert pe.add_tuple(*_p('folder', 'a'))
    finally:
        pe.close()


# ---- 6. R1: the guards still fire on hand-built inputs ---------------------------------

#: A TTU that GENUINELY reaches a derived (type, relation): ``folder#viewer`` is boolean,
#: and ``doc#parent: [folder]``. A correct ``compute_taint`` therefore taints
#: ``doc#reader``; the hand-built inputs below simulate a taint regression (the RC1 class)
#: that leaves it untainted, so its TTU compiles to a PLAIN rewrite rule producing the
#: derived-public subject node ``(folder, f, viewer)`` -- an I5 violation.
GENUINE = HEAD + """type user
type folder
  relations
    define banned: [user]
    define viewer: [user] but not banned
type doc
  relations
    define parent: [folder]
    define reader: viewer from parent
"""


def _hand_built_untainted_reader():
    ast = parse_schema_ast(GENUINE)
    true_taint = compute_taint(ast)
    assert ('doc', 'reader') in true_taint          # the regression below is a real deviation
    tainted = true_taint - {('doc', 'reader')}
    rules_and_filters: list = []
    for key, expr in ast.items():
        if key not in tainted:
            _emit_expr(expr, key[0], key[1], rules_and_filters)
    return ast, tainted, rules_and_filters


def test_i5_guard_fires_on_a_hand_built_taint_regression():
    """``compile_boolean_schema``'s I5 subject check, driven directly with a taint set that
    omits ``doc#reader``. No checked parse reaches this guard after TK126, so this test is
    the only thing that sees it deleted."""
    ast, tainted, rules_and_filters = _hand_built_untainted_reader()
    with pytest.raises(ValueError, match='carries a derived subject predicate') as ei:
        compile_boolean_schema(ast, derive_schema_info(ast), rules_and_filters, tainted)
    msg = str(ei.value)
    assert 'folder#viewer' in msg and 'doc#parent' in msg, msg
    assert 'RelationalTriplePattern' not in msg, msg


def test_i5_guard_reads_admission_not_member_types(monkeypatch):
    """The guard's subject types come from the emitted Filters, a derivation independent
    of ``_member_types``. Make ``_member_types`` WRONG but non-empty (``{'user'}`` for
    every relation, so ``compute_taint`` misses ``doc#reader`` -- the RC1 shape: a wrong
    type set, not an empty one) and switch the friendlier compiler check off: the guard
    must still refuse, because admission says ``doc#parent`` holds ``folder`` subjects.

    An EMPTY ``_member_types`` would not do: the guard then falls back to the NAME test
    and refuses anyway, so a guard reading ``_member_types`` alone stays green -- observed
    2026-10-08 as sabotage S2 passing (``5 passed``) on the first draft of this test."""
    monkeypatch.setattr(boolean_mod, '_member_types', lambda *a, **k: frozenset({'user'}))
    monkeypatch.setattr(compiler_mod, '_validate_ttu_tuplesets', lambda ast, tainted: None)
    assert ('doc', 'reader') not in compute_taint(parse_schema_ast(GENUINE))
    with pytest.raises(ValueError, match='carries a derived subject predicate'):
        parse_openfga_schema(GENUINE)


def test_compiler_check_refuses_a_hand_built_taint_regression(monkeypatch):
    """``_validate_ttu_tuplesets`` (type-aware) pre-empts the bare ``ValueError`` with the
    scoped ``UnsupportedByGraphIndex`` when the taint set misses a container whose TTU
    reaches a derived ``(type, relation)``."""
    real = compiler_mod.compute_taint
    monkeypatch.setattr(compiler_mod, 'compute_taint',
                        lambda ast: real(ast) - {('doc', 'reader')})
    with pytest.raises(UnsupportedByGraphIndex, match='folder#viewer') as ei:
        parse_openfga_schema(GENUINE)
    assert 'undeclared tupleset relation being the usual cause' not in str(ei.value)


UNDECLARED = HEAD + """type user
type folder
  relations
    define banned: [user]
    define viewer: [user] but not banned
type doc
  relations
    define reader: [user] or viewer from parent
"""


def test_undeclared_tupleset_falls_back_to_the_name_test():
    """A hand-built / unchecked AST whose tupleset is UNDECLARED gives both guards an
    empty type set; they fall back to the conservative NAME test rather than passing."""
    ast = _parse_schema_ast_unchecked(UNDECLARED)
    with pytest.raises(UnsupportedByGraphIndex, match='undeclared'):
        compile_ruleset(ast, derive_schema_info(ast))
    tainted = compute_taint(ast)
    assert ('doc', 'reader') not in tainted
    rules_and_filters: list = []
    for key, expr in ast.items():
        if key not in tainted:
            _emit_expr(expr, key[0], key[1], rules_and_filters)
    with pytest.raises(ValueError, match='carries a derived subject predicate'):
        compile_boolean_schema(ast, derive_schema_info(ast), rules_and_filters, tainted)


def test_renamed_control_still_compiles():
    """Negative control for the guards above: the same shape with the target NOT derived
    on the admitted type (``GENUINE`` with ``folder#viewer`` made plain) compiles."""
    plain = GENUINE.replace('define viewer: [user] but not banned', 'define viewer: [user]')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        parse_openfga_schema(plain)
