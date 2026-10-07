"""TK116 -- the set engine is differential-tested against the oracle, WITH REMOVES, on every
schema family the graph index refuses.

Property guarded
----------------
When ``parse_openfga_schema`` refuses a schema (``UnsupportedByGraphIndex`` /
``CyclicDerivedDependency``, the decision-15 scope families), the set engine still accepts
it and runs WITHOUT a graph partner: ``src/zanzibar/setengine/engine.py::SetEngine.__init__`` leaves
``_ruleset = None``, which also switches data-cycle rejection off
(``SetEngine._would_cycle``). On those schemas the oracle is the ONLY cross-check. Before
this module, the refusals were pinned only by ``pytest.raises`` and every randomized driver
skipped a refused schema, so no write -- and no remove -- was ever compared on them.

For every refusal family reachable from a checked parse (``WITNESSES``, one per raise site
in ``src/zanzibar/schema/``):

* the graph refuses it with THAT family's message, and no other witness's message matches
  (so the nine witnesses are nine distinct families, not one family nine times; EIGHT
  since 2026-10-08, when TK126 made the name-collision family served and its raise site
  moved to ``UNREACHABLE``);
* ``ParityEngine`` degrades to set:py + set:roaring + oracle, both ``_ruleset``s are None;
* a SCRIPTED walk drives the family's own refused shape (star-object writes, star
  tuplesets, wildcard usersets over a derived relation, data cycles) -- every scripted add
  and every scripted remove must be ACCEPTED, then a seeded random walk, then a drain to
  empty. The full ParityEngine grid (plus the TK117 write-local floor) is compared after
  every accepted op;
* the lookup surfaces (``lookup`` / ``lookup_reverse`` / ``expand``) are checked against
  the oracle on the same schemas, set-only, by ``tests/test_lookup_oracle.py::_Gate``.

``test_every_graph_refusal_site_has_a_witness`` is the census: it counts the refusal raise
sites in ``src/zanzibar/schema/`` and demands ``len(WITNESSES) + len(UNREACHABLE)``, zero
headroom. A new refusal site is red here until it gets a witness (or a reason it cannot be
reached from a checked parse).

The admission asymmetry (decided 2026-10-04d, recorded on the TK116 row)
-----------------------------------------------------------------------
The SAME ``group#member`` data cycle is refused when the schema joins the graph and
accepted when an unrelated relation makes it graph-refused
(``test_admission_asymmetry_is_deliberate``). KEPT, deliberately: cycle rejection is the
graph index's admission constraint (a ref-counted closure cannot hold a cycle), not a
semantic rule -- Zanzibar/OpenFGA accept cyclic tuples, and the oracle evaluates them. With
no graph partner there is nothing to stay in admission parity with, and refusing would
need a RuleSet these schemas do not have. ``src/zanzibar/connectedstore/schema_io.py::save_schema``
refuses every graph-refused schema, so only a standalone ``SetEngine`` sees the
difference. What this module adds is that the accepted cycles are now oracle-checked.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from zanzibar.schema import (CyclicDerivedDependency, UnsupportedByGraphIndex,
                               parse_openfga_schema, parse_schema_ast)
from tests.parity import ParityEngine
from tests.test_hypothesis import _directs
from tests.test_lookup_oracle import _Gate

NAMES = ('n1', 'n2')


@dataclass(frozen=True)
class Witness:
    family: str
    schema: str
    owc: frozenset
    exc: type
    message: str                    # substring of the graph's refusal message
    script: tuple                   # raw tuples the family exists for; ALL must be accepted


def _u(rel, otype, oname, name='n1'):
    return ('...', 'user', name, rel, otype, oname)


WITNESSES: tuple[Witness, ...] = (
    Witness(
        # `_reject_owc_scope`: a shape on a derived relation. The `[user]` arm makes a
        # star-OBJECT write on the derived relation itself writable.
        'owc-on-derived',
        'type user\ntype doc\n  relations\n'
        '    define public: [user:*]\n    define blocked: [user]\n'
        '    define viewer: ([user] or public) but not blocked\n',
        frozenset({('doc', 'viewer')}), UnsupportedByGraphIndex,
        'targets a derived (boolean-tainted) relation',
        (_u('viewer', 'doc', '*'), ('...', 'user', '*', 'public', 'doc', 'n2'),
         _u('blocked', 'doc', 'n2'))),
    Witness(
        # `_reject_owc_scope`: a declared shape naming a compiled leaf. Nothing is writable
        # at `view.0`, so the script is the boolean relation's ordinary traffic.
        'owc-names-a-leaf',
        'type user\ntype doc\n  relations\n'
        '    define editor: [user]\n    define banned: [user]\n'
        '    define view: editor but not banned\n',
        frozenset({('doc', 'view.0')}), UnsupportedByGraphIndex,
        'names a compiled leaf predicate',
        (_u('editor', 'doc', 'n1'), _u('banned', 'doc', 'n1'))),
    Witness(
        # `_reject_owc_scope`: a shape the rewrite rules carry onto a leaf (P10 W1).
        'owc-expands-onto-leaf',
        'type user\ntype doc\n  relations\n'
        '    define editor: [user]\n    define banned: [user]\n'
        '    define view: editor but not banned\n',
        frozenset({('doc', 'editor')}), UnsupportedByGraphIndex,
        'expands onto the compiled leaf predicate',
        (_u('editor', 'doc', '*'), _u('banned', 'doc', 'n2'), _u('editor', 'doc', 'n1'))),
    Witness(
        # `_reject_owc_scope`: a shape on the tupleset of a TTU inside a derived relation.
        # `doc:n1 parent doc:*` makes EVERY doc a child of n1.
        'owc-on-derived-ttu-tupleset',
        'type user\ntype doc\n  relations\n'
        '    define r0: [user]\n    define parent: [doc]\n'
        '    define r1: [user] and r0\n    define r2: r1 from parent\n',
        frozenset({('doc', 'parent')}), UnsupportedByGraphIndex,
        'is the tupleset of TTU',
        (('...', 'doc', 'n1', 'parent', 'doc', '*'), _u('r0', 'doc', 'n1'),
         _u('r1', 'doc', 'n1'))),
    Witness(
        # `_reject_owc_scope`, blind-audit D4 through expansion: the shape sits one
        # Computed hop upstream of the derived relation's TTU target.
        'owc-upstream-of-derived-ttu-target',
        'type user\ntype folder\n  relations\n'
        '    define editor: [user]\n    define viewer: [user] or editor\n'
        'type doc\n  relations\n'
        '    define parent: [folder]\n    define banned: [user]\n'
        '    define access: viewer from parent but not banned\n',
        frozenset({('folder', 'editor')}), UnsupportedByGraphIndex,
        'is the TTU target of derived relation',
        (_u('editor', 'folder', '*'), ('...', 'folder', 'n2', 'parent', 'doc', 'n1'),
         _u('banned', 'doc', 'n1'))),
    Witness(
        # `_reject_owc_scope`: a star tupleset whose TTU target is derived.
        'star-tupleset-over-derived-target',
        'type user\ntype doc\n  relations\n'
        '    define blk: [user]\n    define viewer: [user] but not blk\n'
        '    define parent: [doc, doc:*]\n    define r2: viewer from parent\n',
        frozenset(), UnsupportedByGraphIndex,
        'derives the wildcard userset shape',
        (('...', 'doc', '*', 'parent', 'doc', 'n1'), _u('viewer', 'doc', 'n2'),
         _u('blk', 'doc', 'n2'))),
    Witness(
        # `_build_plan_tree`: a wildcard userset over a derived relation (P10 W2). The
        # last two script rows close a `group#member` DATA CYCLE (n1 -> n2 -> n1), which
        # only the graph-refused schema admits; see `test_admission_asymmetry_is_deliberate`.
        'wildcard-userset-over-derived',
        'type user\ntype group\n  relations\n'
        '    define member: [user, group#member]\n    define blocked: [user]\n'
        '    define ok: member but not blocked\n'
        '    define reader: [group:*#ok, group#member]\n',
        frozenset(), UnsupportedByGraphIndex,
        'wildcard userset restriction',
        (('ok', 'group', '*', 'reader', 'group', 'n1'), _u('member', 'group', 'n2'),
         _u('blocked', 'group', 'n2', name='n2'),
         ('member', 'group', 'n1', 'member', 'group', 'n2'),
         ('member', 'group', 'n2', 'member', 'group', 'n1'))),
    # 2026-10-08 (TK126): the witness `ttu-target-name-is-derived-elsewhere` (an untainted
    # TTU whose target NAME is derived on another type) is RETIRED here: the schema is now
    # SERVED by the graph (both I5 checks key on (type, relation)), so it is no longer a
    # refusal. Its raise site stays as a defensive check and moved to `UNREACHABLE`; the
    # schema itself is driven 4-way as `C_team` in
    # `tests/test_tk126_ttu_target_name_collision.py`. Census: 12 sites = 8 + 4.
    Witness(
        # `_stratify`: a derived cycle through a TTU target. The parent rows form a DATA
        # cycle too (n1 -> n2 -> n1).
        'cyclic-derived-dependency',
        'type user\ntype doc\n  relations\n'
        '    define blk: [user]\n    define parent: [doc]\n'
        '    define a: ([user] but not blk) or a from parent\n',
        frozenset(), CyclicDerivedDependency,
        'dependency cycle',
        (_u('a', 'doc', 'n1'), ('...', 'doc', 'n1', 'parent', 'doc', 'n2'),
         ('...', 'doc', 'n2', 'parent', 'doc', 'n1'), _u('blk', 'doc', 'n2'))),
)

#: Refusal raise sites a CHECKED parse cannot reach, with the reason. Each is still a
#: refusal; it just has no schema text that gets past the parser to it.
UNREACHABLE: tuple[tuple[str, str], ...] = (
    ('_emit_relation: boolean operator',
     'only under compile_ruleset(enable_boolean=False); SetEngine never passes it'),
    ('compile_ruleset: tupleset has computed/rewritten arms',
     'refused at parse since TK106 (`_validate_tuplesets_direct`); hand-built AST only'),
    ('compile_ruleset: tupleset declares a userset restriction',
     'refused at parse since TK108 (`_validate_tuplesets_direct`); hand-built AST only'),
    ('_validate_ttu_tuplesets: untainted TTU reaches a derived (type, target)',
     'TK126 (2026-10-08): keyed on (type, relation), and compute_taint taints every '
     'relation whose TTU reaches a derived target through the same _member_types, so a '
     'checked parse cannot reach it; the undeclared-tupleset fallback is refused at '
     'parse since ASK-1. Hand-built AST / taint regression only, pinned by '
     'tests/test_tk126_ttu_target_name_collision.py'),
)

# The whole schema PACKAGE, globbed (TK120, 2026-10-06): it was one file until the split,
# and a fixed path would let a refusal in a new submodule escape this census unseen.
_SRC_DIR = Path(__file__).resolve().parent.parent / 'src/zanzibar/schema'
_SRC_FILES = sorted(_SRC_DIR.rglob('*.py'))
_RAISE = re.compile(r'raise (UnsupportedByGraphIndex|CyclicDerivedDependency)\(')


def _ids(w):
    return w.family


def _refusal(w: Witness) -> BaseException:
    with pytest.raises(w.exc) as ei:
        parse_openfga_schema(w.schema, object_wildcard_shapes=w.owc)
    return ei.value


def _pool(w: Witness, pe: ParityEngine) -> list[tuple]:
    """Every raw tuple a Direct restriction admits over ``NAMES``, plus a ``*`` OBJECT on
    every declared relation in the (closed) object-wildcard shapes -- the writes TK101
    says the generic pools never emit."""
    ast = parse_schema_ast(w.schema)
    owc = pe.set_sides[0].se.schema_info.object_wildcard_shapes
    out = set()
    for (otype, rel), expr in ast.items():
        onames = list(NAMES) + (['*'] if (otype, rel) in owc else [])
        for d in _directs(expr):
            for r in d.restrictions:
                for sn in (['*'] if r.wildcard else NAMES):
                    for on in onames:
                        out.add((r.predicate, r.type, sn, rel, otype, on))
    return sorted(out)


def _witness_pool(w: Witness) -> list[tuple]:
    pe = ParityEngine(w.schema, object_wildcard_shapes=w.owc)
    try:
        return _pool(w, pe)
    finally:
        pe.close()


def test_witness_families_are_distinct():
    """Each witness's message names its OWN refusal and no other witness's: nine
    witnesses, nine families. Without this a witness drifting onto a neighbouring
    family's check would leave its own family undriven and stay green."""
    msgs = {w.family: str(_refusal(w)) for w in WITNESSES}
    for w in WITNESSES:
        assert w.message in msgs[w.family], (w.family, msgs[w.family])
        others = [v.family for v in WITNESSES
                  if v is not w and type(_refusal(v)) is w.exc and w.message in msgs[v.family]]
        assert not others, f'{w.family}: message {w.message!r} also matches {others}'


def test_every_graph_refusal_site_has_a_witness():
    """Census, zero headroom: refusal raise sites == witnesses + unreachable sites."""
    assert len(_SRC_FILES) >= 9, _SRC_FILES   # anti-vacuity: the glob still finds the package
    sites = [s for f in _SRC_FILES for s in _RAISE.findall(f.read_text(encoding='utf-8'))]
    assert len(sites) == len(WITNESSES) + len(UNREACHABLE), (
        f'{len(sites)} graph-refusal raise sites in src/zanzibar/schema/, but '
        f'{len(WITNESSES)} witnesses + {len(UNREACHABLE)} unreachable. A new refusal needs '
        f'a WITNESSES entry (driven set-vs-oracle below) or an UNREACHABLE reason; a '
        f'removed one needs its entry retired.')


@pytest.mark.parametrize('seed', [0, 1, 2])
@pytest.mark.parametrize('w', WITNESSES, ids=_ids)
def test_set_engine_matches_oracle_with_removes(w, seed):
    """Scripted family writes (all accepted, then all removed), a seeded walk, a drain."""
    pe = ParityEngine(w.schema, object_wildcard_shapes=w.owc, seed=seed)
    try:
        assert pe.graph is None and pe.graph_drop_reason, 'the graph joined: not a refusal'
        assert w.message in pe.graph_drop_reason, pe.graph_drop_reason
        assert [s.se._ruleset for s in pe.set_sides] == [None, None]

        for raw in w.script:
            assert pe.add_tuple(*raw), f'{w.family}: scripted add refused: {raw}'
        for raw in reversed(w.script):
            assert pe.remove_tuple(*raw), f'{w.family}: scripted remove refused: {raw}'
        assert not pe.present

        pool, rng = _pool(w, pe), random.Random(seed)
        adds = removes = 0
        for _ in range(30):
            absent = [r for r in pool if r not in pe.present]
            if absent and (not pe.present or rng.random() < 0.65):
                adds += pe.add_tuple(*rng.choice(absent))
            else:
                removes += pe.remove_tuple(*rng.choice(sorted(pe.present)))
        for raw in sorted(pe.present):
            removes += pe.remove_tuple(*raw)
        assert not pe.present
        # non-vacuity: a walk that removed nothing is the gap this row was filed for.
        assert adds > 0 and removes > 0, (adds, removes)
    finally:
        pe.close()


@pytest.mark.parametrize('w', WITNESSES, ids=_ids)
def test_lookup_surfaces_match_oracle_without_a_graph(w):
    """``_Gate`` set-only: lookup / lookup_reverse / expand vs the oracle after every
    accepted op of the script, its reverse, and a drain."""
    gate = _Gate(w.schema, w.owc, _witness_pool(w), allow_graph_absent=True)
    try:
        assert gate.graph is None
        gate.assert_surfaces(context=f'{w.family}: initial')
        for raw in w.script:
            assert gate.apply('add', raw), raw
            gate.assert_surfaces(context=f'{w.family}: add {raw}')
        for raw in reversed(w.script):
            assert gate.apply('remove', raw), raw
            gate.assert_surfaces(context=f'{w.family}: remove {raw}')
        # non-vacuity: both SetOps' batteries ran at every state (initial + 2 per row)
        assert gate.set_checks == 2 * (1 + 2 * len(w.script)), gate.set_checks
    finally:
        gate.close()


def test_walk_catches_a_planted_set_engine_lie(monkeypatch):
    """Instrument control for ``test_set_engine_matches_oracle_with_removes``: with no
    graph partner, a set-engine lie on the family's own state must still be caught by the
    ParityEngine's oracle comparison. Both SetOps lie identically, so unanimity between
    them cannot catch it -- only the oracle can."""
    from zanzibar.setengine import engine as se_mod
    real = se_mod.SetEngine.check

    def lying(self, sp, st, sn, rel, ot, on):
        ans = real(self, sp, st, sn, rel, ot, on)
        planted = (st, sn, rel, ot, on) == ('user', 'n1', 'viewer', 'doc', 'n2')
        return (not ans) if planted else ans

    monkeypatch.setattr(se_mod.SetEngine, 'check', lying)
    pe = ParityEngine(_OWC_ON_DERIVED.schema, object_wildcard_shapes=_OWC_ON_DERIVED.owc)
    try:
        assert pe.graph is None
        with pytest.raises(AssertionError, match='parity'):
            for raw in _OWC_ON_DERIVED.script:
                pe.add_tuple(*raw)
    finally:
        pe.close()


_CYCLE = (('member', 'group', 'n1', 'member', 'group', 'n2'),
          ('member', 'group', 'n2', 'member', 'group', 'n1'))
_JOINED_CONTROL = ('type user\ntype group\n  relations\n'
                   '    define member: [user, group#member]\n    define blocked: [user]\n'
                   '    define ok: member but not blocked\n'
                   '    define reader: [group#member]\n')


def test_admission_asymmetry_is_deliberate():
    """The same ``group#member`` data cycle: refused by EVERY backend when the schema
    joins the graph, accepted (and oracle-checked) when ``reader``'s wildcard userset
    over the derived ``ok`` makes it graph-refused. Decision in the module docstring."""
    joined = ParityEngine(_JOINED_CONTROL)
    try:
        assert joined.graph is not None
        assert joined.add_tuple(*_CYCLE[0])
        assert not joined.add_tuple(*_CYCLE[1])       # unanimous refusal, I12-checked
    finally:
        joined.close()
    refused = ParityEngine(next(w.schema for w in WITNESSES
                                if w.family == 'wildcard-userset-over-derived'))
    try:
        assert refused.graph is None
        assert refused.add_tuple(*_CYCLE[0])
        assert refused.add_tuple(*_CYCLE[1])          # accepted; grid parity vs oracle
        assert refused.add_tuple(*_u('member', 'group', 'n1'))
        assert refused.check('...', 'user', 'n1', 'member', 'group', 'n2')
    finally:
        refused.close()


def test_generated_refused_schemas_run_the_set_only_lookup_gate():
    """The generated-schema lookup gate used to RETURN on a graph-refused draw; it now runs
    set-only (``test_lookup_oracle_gate_generated_schemas``). That test is hypothesis-drawn,
    so this is the deterministic floor: the first refused draws of the join-rate sweep's
    seeded generator (``random.Random(seed)``, the same body ``schema_asts`` uses) each run
    a seeded add/remove walk, drained to empty, with the set surfaces checked after every
    accepted op. Non-vacuity: at least ``want`` refused schemas, and the walk must accept
    at least one remove on each."""
    from tests.test_hypothesis import _op_pool, _schema_ast, _RandomChoices
    from tests.test_lookup_oracle import _run_gate
    from zanzibar.schema import unparse_schema_ast
    want, ran = 4, 0
    for seed in range(240):
        ast = _schema_ast(_RandomChoices(random.Random(seed)))
        pool = _op_pool(ast)
        schema = unparse_schema_ast(ast)
        if not pool:
            continue
        try:
            parse_openfga_schema(schema)
            continue
        except UnsupportedByGraphIndex:
            pass
        removes = []
        _run_gate(schema, frozenset(), pool, seed, walk_steps=8, allow_graph_absent=True,
                  on_apply=lambda op, raw, ok: removes.append(ok) if op == 'remove' else None)
        assert any(removes), f'seed {seed}: the walk accepted no remove'
        ran += 1
        if ran == want:
            break
    assert ran == want, f'only {ran} refused generated schemas found in 240 seeds'


_OWC_ON_DERIVED = next(w for w in WITNESSES if w.family == 'owc-on-derived')


@pytest.mark.parametrize('k', [0, 1], ids=['py', 'roaring'])
def test_lookup_marker_carries_its_exclusions(k):
    """The TK116 finding, pinned exact (docs/tk116-oracle-only-setengine-2026-10-04.md
    sec 2). Before the fix ``lookup(user:n1)`` returned the marker ``(doc, viewer)`` --
    "every doc" -- with nothing to say ``doc:n2`` is subtracted: a FAIL-OPEN, while
    ``check`` said False. Literal pre-fix output:
    ``LookupResult(node_ids={2}, markers={('doc', 'viewer')})``."""
    pe = ParityEngine(_OWC_ON_DERIVED.schema, object_wildcard_shapes=_OWC_ON_DERIVED.owc)
    try:
        assert pe.add_tuple(*_u('viewer', 'doc', '*'))
        assert pe.add_tuple(*_u('blocked', 'doc', 'n2'))
        assert pe.add_tuple(*_u('viewer', 'doc', 'n3'))
        se = pe.set_sides[k].se
        res = se.lookup('...', 'user', 'n1')
        assert res.markers == {('doc', 'viewer')}
        assert se.result_keys(res) == {('doc', 'n3', 'viewer'), ('doc', 'n2', 'blocked')}
        assert {se.interner.key(i) for i in res.excluded_node_ids} == {('doc', 'n2', 'viewer')}
        assert not pe.check('...', 'user', 'n1', 'viewer', 'doc', 'n2')
        # A subject the subtraction does not touch gets the marker with no exceptions.
        assert pe.add_tuple(*_u('viewer', 'doc', '*', name='n2'))
        res2 = se.lookup('...', 'user', 'n2')
        assert res2.markers == {('doc', 'viewer')} and not res2.excluded_node_ids
    finally:
        pe.close()


@pytest.mark.parametrize('tamper', ['clear', 'spurious'])
def test_set_forward_checker_sees_a_tampered_exclusion(tamper):
    """Instrument control for the S4 exclusion clause in
    ``tests/test_lookup_oracle.py::_check_set_forward``: a cleared exclusion (the pre-fix
    fail-open) and a spurious one (an oracle-true object dropped) must both go red."""
    from tests.test_lookup_oracle import _check_set_forward
    gate = _Gate(_OWC_ON_DERIVED.schema, _OWC_ON_DERIVED.owc, _witness_pool(_OWC_ON_DERIVED),
                 allow_graph_absent=True)
    try:
        for raw in (_u('viewer', 'doc', '*'), _u('blocked', 'doc', 'n2'),
                    _u('blocked', 'doc', 'n1', name='n2')):
            assert gate.apply('add', raw)
        from tests.oracle import Oracle, OracleTuple
        oracle = Oracle(gate.schema, [OracleTuple(*r) for r in gate.present])
        se = gate.sets[0].se
        res = se.lookup('...', 'user', 'n1')
        assert res.excluded_node_ids                 # the untampered result has one
        _check_set_forward(se, oracle.check, ('...', 'user', 'n1'), gate.objects, res)
        if tamper == 'clear':
            res.excluded_node_ids = set()
        else:
            res.excluded_node_ids.add(se.interner.get('doc', 'n1', 'viewer'))
        with pytest.raises(AssertionError):
            _check_set_forward(se, oracle.check, ('...', 'user', 'n1'), gate.objects, res)
    finally:
        gate.close()
