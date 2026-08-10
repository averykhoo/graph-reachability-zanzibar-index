"""Generator-coverage cells + the swarm generator + a reporting 4-backend differential.

This module is the *library*; ``tests/test_generator_coverage.py`` is the gate that
asserts over it. It is the promotion of the validated prototypes in
``docs/design/generator-coverage/prototypes/`` (``zz_cells.py`` / ``zz_gen2.py`` /
``zz_enum2.py`` / ``zz_drive.py``) into gated code — read
``docs/design/generator-coverage/README.md`` before changing anything here.

Three pieces:

**(a) The cell alphabet, DERIVED.** Every feature name is minted from one of six
compiler source-of-truth sites, never from a hand-written list (a hand-written "what
should exist" list is rank 2 on ``docs/sabotage-procedure.md``'s durability ranking —
"correct the day it was written, green forever once the compiler grows a branch"). A
*cell* is an unordered PAIR of features that co-occur in one compiled, driven config;
the cartesian grid over 51 features is ``2**51``, and a hand-picked sub-grid would be
exactly the silent-pass list this work exists to kill.

**(b) The swarm.** ``swarm_subset`` draws a random subset of generator switches to
ENABLE, then ``swarm_schema_asts`` generates deeply within it. One quarter of draws is
the "all on" stratum, which is a superset of today's ``schema_asts`` draw, so the swarm
cannot wash out the existing distribution. There is deliberately **no "minimal"
stratum**: the prototype measured 771 -> 721 cells at 600 draws when one was added,
because tiny schemas consume budget without composing anything.

**(c) The TTU tupleset is drawn**, not pinned to ``[doc]``, at a drawn topological
position, from the same expression grammar as every other relation.

Plus the two controls the design's own instrument-check demanded:

* ``Diff`` — a 4-backend differential that *reports* instead of asserting (ParityEngine
  asserts, which a sweep cannot use), with an explicit comparison counter so a sweep
  that compared nothing cannot report success;
* ``subsets_for`` / ``drive_config`` — **two-regime driving**. See ``subsets_for``'s
  docstring: sparse subsets find fail-CLOSED divergences, the dense per-shape knockout
  (the whole pool MINUS one admission shape) finds fail-OPEN ones, and the full pool
  finds almost neither. Measured over the same 136-config space, 2026-08-10::

      regime            wall     comparisons   FAIL-OPEN   fail-closed
      sparse            64.7 s       62 691         0           10
      dense (knockout)  85.7 s       61 659         1           13
      full pool         86.1 s       41 562         0            3

  That asymmetry is this repo's IIA property and it is why the full-pool variant is
  retained as a permanent negative control rather than as the driving discipline.
"""

from __future__ import annotations

import inspect
import itertools
import random
import re
import typing
from dataclasses import dataclass, field, fields, is_dataclass

from hypothesis import strategies as st

import zanzibar_utils_v1 as Z
from zanzibar_utils_v1 import (Computed, CyclicDerivedDependency, Direct,
                               DoublyBridgedShapeError, Exclusion, Intersection,
                               Restriction, TTU, Union, UnsupportedByGraphIndex,
                               parse_openfga_schema, parse_schema_ast,
                               unparse_schema_ast, _iter_directs)
from setengine import ALL_SETOPS
from tests.oracle import Oracle, OracleTuple
from tests.parity import _GraphSide, _SetSide

RawTuple = tuple[str, str, str, str, str, str]

GHOST = 'zz-ghost'


# =========================================================================== #
# 1. THE ALPHABET, derived from six compiler sites.
#
#    Each derive_* asserts non-vacuity: an empty derivation would shrink the cell
#    universe to nothing and make every coverage assertion below pass trivially.
#    That is the generalisation of the failure
#    `test_required_leaf_kinds_are_exactly_the_compilers_kinds` was written to close.
# =========================================================================== #

def derive_expr_classes() -> tuple[str, ...]:
    """Site 1 — members of the ``Expr`` union alias (the SchemaAST node types)."""
    args = typing.get_args(Z.Expr)
    names = tuple(sorted(a.__name__ for a in args))
    assert names, 'ANTI-VACUITY: Expr union yielded no members'
    return names


def derive_leaf_kinds() -> tuple[str, ...]:
    """Site 2 — the ``LeafSpec(..., '<kind>')`` literals in ``_plan_leaves``, the one
    minting site. Same regex the existing leaf-kind floor uses."""
    src = inspect.getsource(Z._plan_leaves)
    kinds = set(re.findall(r"LeafSpec\([^,]+,\s*'([a-z][a-z-]*)'", src))
    assert kinds, 'ANTI-VACUITY: no LeafSpec kind literal found in _plan_leaves'
    return tuple(sorted(kinds))


def derive_plan_node_classes() -> tuple[str, ...]:
    """Site 3 — the plan-tree node classes, read off the ``isinstance(n, ...)`` dispatch
    inside ``_plan_leaves``.

    NOT "every ``P*`` dataclass in the module": that is the tempting version and it is
    wrong — it sweeps in ``Plan`` and reports 9. A plan node type ``_plan_leaves`` does
    not dispatch on is a node type no leaf coverage can be claimed for. This was the
    instrument bug hit while building the instrument (design README §1.2)."""
    src = inspect.getsource(Z._plan_leaves)
    names = set()
    for grp in re.findall(r"isinstance\(n,\s*\(?([^)]*?)\)?\):", src):
        for nm in re.findall(r"\b(P[A-Z]\w*)\b", grp):
            names.add(nm)
    assert names and all(is_dataclass(getattr(Z, n)) for n in names), \
        f'ANTI-VACUITY: plan-node dispatch derivation yielded {names}'
    return tuple(sorted(names))


def derive_via_kinds() -> tuple[str, ...]:
    """Site 4 — the ``DependentEdge(key, '<via>')`` literals: the fan-out kinds."""
    src = inspect.getsource(Z)
    vias = set(re.findall(r"DependentEdge\([^,()]+,\s*'([a-z][a-z-]*)'", src))
    assert vias, 'ANTI-VACUITY: no DependentEdge via literal found in the compiler'
    return tuple(sorted(vias))


def derive_family_kinds() -> tuple[str, ...]:
    """Site 5 — the single ``LeafFamily(... kind=(a if ... else b))`` construction."""
    src = inspect.getsource(Z)
    m = re.search(r"LeafFamily\((?:[^()]|\([^()]*\))*?kind=\(\s*'([a-z-]+)'"
                  r"[^)]*?else\s*'([a-z-]+)'\)", src, re.S)
    assert m, 'ANTI-VACUITY: no LeafFamily kind literal found'
    return tuple(sorted(m.groups()))


def derive_restriction_modalities() -> tuple[str, ...]:
    """Site 6 — the subject modalities a ``Restriction`` can express, from its FIELDS.
    ``predicate`` splits bare (``'...'``) from userset; ``wildcard`` is a bool: 2x2."""
    fnames = {f.name for f in fields(Restriction)}
    assert {'type', 'predicate', 'wildcard'} <= fnames, \
        f'ANTI-VACUITY: Restriction fields changed: {sorted(fnames)}'
    return ('concrete', 'subject-wildcard', 'userset', 'wildcard-userset')


DERIVATIONS = (
    ('Expr classes', derive_expr_classes),
    ('leaf kinds', derive_leaf_kinds),
    ('plan node classes', derive_plan_node_classes),
    ('via kinds', derive_via_kinds),
    ('family kinds', derive_family_kinds),
    ('restr modalities', derive_restriction_modalities),
)

_MODALITY = {(False, False): 'concrete', (True, False): 'subject-wildcard',
             (False, True): 'userset', (True, True): 'wildcard-userset'}


def _modality(r: Restriction) -> str:
    return _MODALITY[(bool(r.wildcard), r.predicate != '...')]


# --- the assembled alphabet ------------------------------------------------- #
# Sites 1-6 grow and shrink with the compiler automatically. On top of them sit the
# TTU-SCOPED PROJECTIONS of sites 1 and 6 (`ttu.ts:<ExprClass>`, `ttu.ts.restr:<mod>`)
# and eleven hand-named modality flags. Those eleven ARE the irreducible "what do we
# think matters" content of the design; `test_every_switch_moves_the_cell_histogram`
# is how they earn their place (a flag no switch can move is dead weight).

_MODALITY_FLAGS = ('ttu.ts:multitype', 'ttu.ts:tainted', 'ttu.ts:neg-only-type',
                   'ttu.target:tainted', 'ttu:self-target', 'ttu.ts:owc',
                   'schema:owc', 'schema:neg-leaf', 'schema:storage-leaf',
                   'schema:multi-stratum', 'schema:multi-type')


def alphabet() -> tuple[str, ...]:
    A: list[str] = []
    A += [f'ast:{c}' for c in derive_expr_classes()]
    A += [f'leaf:{k}' for k in derive_leaf_kinds()]
    A += [f'plan:{c}' for c in derive_plan_node_classes()]
    A += [f'via:{v}' for v in derive_via_kinds()]
    A += [f'family:{k}' for k in derive_family_kinds()]
    A += [f'restr:{m}' for m in derive_restriction_modalities()]
    A += [f'ttu.ts:{c}' for c in derive_expr_classes()]
    A += ['ttu.ts:undeclared']
    A += [f'ttu.ts.restr:{m}' for m in derive_restriction_modalities()]
    A += list(_MODALITY_FLAGS)
    assert len(set(A)) == len(A), 'duplicate feature name in the alphabet'
    return tuple(A)


def universe_cells(A=None) -> set[frozenset]:
    A = A or alphabet()
    return {frozenset(p) for p in itertools.combinations(sorted(A), 2)}


def cells_of(fs) -> set[frozenset]:
    return {frozenset(p) for p in itertools.combinations(sorted(fs), 2)}


# =========================================================================== #
# 2. THE FEATURE EXTRACTOR
# =========================================================================== #

def _walk(e):
    yield e
    if isinstance(e, (Union, Intersection)):
        for c in e.children:
            yield from _walk(c)
    elif isinstance(e, Exclusion):
        yield from _walk(e.base)
        yield from _walk(e.subtract)


def _neg_only_arms(e):
    """Restrictions occurring ONLY under a subtrahend.

    ⚠ THE TRAP, recorded because a reviewer cannot see it by eye. A subtrahend whose
    restriction ALSO occurs in the base (``[doc, folder] but not [doc]``) *looks* like a
    neg-only arm, compiles, reads correctly in review — and makes the relation
    identically empty, so the cell is "compiled but never driven" (the 2026-07-28 row of
    ``docs/sabotage-procedure.md``). The prototype's first witness builder did exactly
    that and its driven sweep found ZERO divergences; fixing the construction to a
    genuine neg-only arm made the same sweep detonate the live bug."""
    pos, neg = set(), set()

    def rec(x, sign):
        tgt = pos if sign else neg
        if isinstance(x, Direct):
            for r in x.restrictions:
                tgt.add((r.type, r.predicate, r.wildcard))
        elif isinstance(x, (Union, Intersection)):
            for c in x.children:
                rec(c, sign)
        elif isinstance(x, Exclusion):
            rec(x.base, sign)
            rec(x.subtract, not sign)
    rec(e, True)
    return neg - pos


def _plan_walk(n):
    yield n
    if isinstance(n, (Z.PUnion, Z.PIntersection)):
        for c in n.children:
            yield from _plan_walk(c)
    elif isinstance(n, Z.PExclusion):
        yield from _plan_walk(n.base)
        yield from _plan_walk(n.subtract)


def ast_features(schema_text: str, owc=frozenset()) -> set[str]:
    """The AST-only half of the feature set — everything derivable WITHOUT compiling.

    This is what a REJECTION WITNESS carries: the compiler refuses it, so no compiled
    artifacts exist. Deliberately conservative — taint-dependent flags are omitted here
    rather than re-derived, because a second taint implementation in the test tree would
    be an instrument that can disagree with its subject."""
    f: set[str] = set()
    ast = parse_schema_ast(schema_text)
    owc = frozenset(owc)
    if owc:
        f.add('schema:owc')
    if len({t for (t, _) in ast}) > 1:
        f.add('schema:multi-type')
    for (otype, rel), body in ast.items():
        for node in _walk(body):
            f.add(f'ast:{type(node).__name__}')
            if isinstance(node, Direct):
                for r in node.restrictions:
                    f.add(f'restr:{_modality(r)}')
            if isinstance(node, TTU):
                ts_key = (otype, node.tupleset_rel)
                if node.target_rel == rel:
                    f.add('ttu:self-target')
                if ts_key not in ast:
                    f.add('ttu.ts:undeclared')
                    continue
                ts_body = ast[ts_key]
                for tn in _walk(ts_body):
                    f.add(f'ttu.ts:{type(tn).__name__}')
                    if isinstance(tn, Direct):
                        for r in tn.restrictions:
                            f.add(f'ttu.ts.restr:{_modality(r)}')
                types = {r.type for d in _walk(ts_body) if isinstance(d, Direct)
                         for r in d.restrictions}
                if len(types) > 1:
                    f.add('ttu.ts:multitype')
                if _neg_only_arms(ts_body):
                    f.add('ttu.ts:neg-only-type')
                if ts_key in owc:
                    f.add('ttu.ts:owc')
    return f


def features(schema_text: str, owc=frozenset()) -> set[str]:
    """Full feature set of one ``(schema, object_wildcard_shapes)`` config.

    Raises whatever the compiler raises — the caller classifies the refusal."""
    f = ast_features(schema_text, owc)
    ast = parse_schema_ast(schema_text)
    rs = parse_openfga_schema(schema_text, object_wildcard_shapes=owc)
    compiled = rs.compiled
    tainted = compiled.tainted if compiled else frozenset()
    if rs.schema_info.object_wildcard_shapes:
        f.add('schema:owc')
    if compiled is None:
        return f
    if len(compiled.strata) > 1:
        f.add('schema:multi-stratum')
    for (otype, rel), body in ast.items():
        for node in _walk(body):
            if isinstance(node, TTU):
                ts_key = (otype, node.tupleset_rel)
                if ts_key in tainted:
                    f.add('ttu.ts:tainted')
                if (otype, node.target_rel) in tainted:
                    f.add('ttu.target:tainted')
    for plan in compiled.plans.values():
        for node in _plan_walk(plan.tree):
            f.add(f'plan:{type(node).__name__}')
        for spec in plan.leaves:
            f.add(f'leaf:{spec.kind}')
            if not spec.positive:
                f.add('schema:neg-leaf')
            if spec.storage:
                f.add('schema:storage-leaf')
    for edges in (list(compiled.dependents.values())
                  + list(compiled.target_feeders.values())
                  + list(compiled.tupleset_feeders.values())):
        for e in edges:
            f.add(f'via:{e.via}')
    for v in compiled.namespace.values():
        if isinstance(v, Z.LeafFamily):
            f.add(f'family:{v.kind}')
    return f


# =========================================================================== #
# 3. THE SWARM (deliverable b) + the drawn tupleset (deliverable c)
# =========================================================================== #

# The typed universe. `_op_pool` in test_hypothesis.py uses
# `USERS if r.type == 'user' else DOCS`, which is correct only while every non-user
# restriction is doc-typed. The moment a tupleset restricts a SECOND entity type that
# fallback emits `folder:d1` -- a restriction-INVALID tuple that the graph admits as a
# silent no-op while the set engine refuses it, so the sweep would measure the ADMISSION
# path and report green. A typed table keyed by the restriction's own `r.type` is what
# keeps the pool schema-valid BY CONSTRUCTION.
TYPE_NAMES = {'user': ['u1', 'u2'], 'doc': ['d1', 'd2'], 'folder': ['f1']}

SWARM_SWITCHES = (
    'ts_boolean',        # tupleset body may be Union/Intersection/Exclusion
    'ts_negonly',        # tupleset carries a restriction ONLY in a negative arm
    'ts_multitype',      # tupleset restricts >1 entity type
    'ts_wildcard',       # tupleset carries a subject-wildcard restriction
    'ts_computed',       # tupleset body may be Computed (rewritten arms)
    'ts_userset',        # tupleset carries a userset restriction   [expect REJECT]
    'ts_undeclared',     # a TTU naming a tupleset relation that is not declared
    'body_boolean',      # non-tupleset bodies may be Union/Intersection/Exclusion
    'body_userset',      # the G2 concrete-userset leaf  [doc#r_k]
    'body_wc_userset',   # the wildcard-userset leaf     [doc:*#r_k]
    'body_wildcard',     # subject-wildcard restrictions in ordinary bodies
    'body_computed',     # Computed references
    'body_negttu',       # a NEGATED TTU: `[user] but not <r> from parent`
    'multi_type',        # a second object type (folder) participates
    'self_ttu',          # a TTU whose target is its own head relation
    'owc',               # object-wildcard shapes declared on some relation
)


@st.composite
def swarm_subset(draw):
    """A feature subset to ENABLE.

    Stratum 0 (p = 1/4) is ALL switches ON — a superset of today's ``schema_asts`` draw,
    so the swarm preserves the existing distribution *by construction* for a quarter of
    the budget. Otherwise a uniformly-drawn FOCUS switch is forced ON (so no switch can
    starve) and every other switch is an independent 1/3 coin.

    ⚠ There is deliberately no "minimal" (focus-only) stratum. The prototype measured
    771 -> 721 cells at 600 draws when one was added: tiny schemas consume budget
    without composing anything, and interaction bugs need composition."""
    if draw(st.integers(min_value=0, max_value=3)) == 0:
        return frozenset(SWARM_SWITCHES)
    focus = draw(st.sampled_from(SWARM_SWITCHES))
    rest = {s for s in SWARM_SWITCHES
            if draw(st.integers(min_value=0, max_value=2)) == 0}
    return frozenset(rest | {focus})


_BASE_DIRECTS_PLAIN = (Restriction('user', '...', False),)
_BASE_DIRECTS_WC = (Restriction('user', '...', False), Restriction('user', '...', True))
_BASE_DIRECTS_STAR = (Restriction('user', '...', True),)


@st.composite
def swarm_schema_asts(draw, sw=None):
    """Relations on ``doc`` in topo order, with ``parent`` (the TTU tupleset) inserted at
    a DRAWN position and its body drawn from the SAME expression grammar (deliverable c).

    ``tests/test_hypothesis.py::schema_asts`` pins
    ``ast[('doc','parent')] = Direct((Restriction('doc','...',False),))``, which makes all
    ten ``ttu.ts:*`` features (plus their three compiled consequences) unreachable at ANY
    ``max_examples`` — measured, design README §0. That is the hole both 2026-08-10 bugs
    came through."""
    if sw is None:
        sw = draw(swarm_subset())
    n = draw(st.integers(min_value=2, max_value=5))
    names = [f'r{i}' for i in range(n)]
    ts_types = ['doc']
    if 'multi_type' in sw and 'ts_multitype' in sw:
        ts_types = ['doc', 'folder']
    ppos = draw(st.integers(min_value=0, max_value=n - 1)) if 'ts_computed' in sw else 0

    def expr(i, depth, *, tupleset):
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
            base = [_BASE_DIRECTS_PLAIN]
            if 'body_wildcard' in sw:
                base += [_BASE_DIRECTS_WC, _BASE_DIRECTS_STAR]
            leaves.append(Direct(draw(st.sampled_from(base))))
        if i > 0:
            ref = draw(st.sampled_from(names[:i]))
            if tupleset and 'ts_computed' in sw:
                leaves.append(Computed(ref))
            if not tupleset:
                if 'body_computed' in sw:
                    leaves.append(Computed(ref))
                if 'body_ttu' in sw:
                    leaves.append(TTU(ref, 'parent'))
                if 'body_userset' in sw and draw(st.integers(min_value=0, max_value=2)) == 0:
                    leaves.append(Direct((Restriction(
                        'doc', draw(st.sampled_from(names[:i])), False),)))
        leaf = st.sampled_from(leaves)
        boolean_on = ('ts_boolean' if tupleset else 'body_boolean') in sw
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
            ast[('doc', 'parent')] = _tupleset_body(expr(i, 0, tupleset=True), sw)
        ast[('doc', name)] = expr(i, 0, tupleset=False)
    ast.setdefault(('doc', 'parent'), Direct((Restriction('doc', '...', False),)))
    if 'body_negttu' in sw and n >= 2:
        # THE fail-open shape: `[user] but not <r> from parent`. A dropped TTU parent is
        # a false NEGATIVE under a positive TTU and a false POSITIVE under a negated one
        # (HANDOFF.md), so a grammar with only positive TTUs cannot reach a fail-open at
        # any budget or any driving discipline.
        ast[('doc', names[-1])] = Exclusion(
            Direct(_BASE_DIRECTS_PLAIN), TTU(names[0], 'parent'))
    if 'self_ttu' in sw and n >= 2:
        k = names[-1]
        ast[('doc', k)] = Union((ast[('doc', k)], TTU(k, 'parent')))
    if 'multi_type' in sw:
        ast[('folder', names[0])] = Direct(_BASE_DIRECTS_PLAIN)
    return ast


def _tupleset_body(body, sw):
    """Apply the neg-only arm, if enabled. See ``_neg_only_arms``' docstring for why the
    subtrahend type must occur NOWHERE in the base."""
    if 'ts_negonly' not in sw:
        return body
    return Exclusion(body, Direct((Restriction(
        'folder' if 'multi_type' in sw else 'doc', '...', False),)))


def swarm_op_pool(ast) -> list[RawTuple]:
    """Schema-VALID raw tuples, co-generated from the SAME ast (the constraint HANDOFF.md
    warns will bite). Identical walk to ``test_hypothesis.py::_op_pool`` except the
    subject-name table is TYPED and the OBJECT names come from the object's own type."""
    out = []
    for (otype, rel), e in ast.items():
        for d in _iter_directs(e):
            for r in d.restrictions:
                snames = ['*'] if r.wildcard else TYPE_NAMES.get(r.type, ['x1'])
                for sn in snames:
                    for on in TYPE_NAMES.get(otype, ['x1']):
                        out.append((r.predicate, r.type, sn, rel, otype, on))
    return sorted(set(out))


@st.composite
def swarm_configs(draw):
    """``(ast, owc)`` — the object-wildcard-shape subset is drawn from the schema's OWN
    declared ``(type, relation)`` pairs, so it can never name a shape that does not
    exist."""
    sw = draw(swarm_subset())
    ast = draw(swarm_schema_asts(sw=sw))
    owc = frozenset()
    if 'owc' in sw:
        owc = frozenset(draw(st.sets(st.sampled_from(sorted(ast)), max_size=2)))
    return ast, owc


# =========================================================================== #
# 4. THE DETERMINISTIC WITNESS BUILDER
#
#    Each enabled switch contributes its arm UNCONDITIONALLY (no sampling), so a
#    config's witness has maximal feature density and the enumeration over switch
#    subsets is a CLOSED, exhaustive, RNG-free statement about its own config space.
# =========================================================================== #

def witness(sw) -> tuple[dict, frozenset]:
    """``(ast, owc)`` for a switch subset. ``r0`` = plain base, ``parent`` = the tupleset
    under test, ``r1``/``r2`` = consumers."""
    negonly = 'ts_negonly' in sw
    if negonly and ('ts_multitype' in sw or 'multi_type' in sw):
        ts_rs = [Restriction('folder', '...', False)]          # base [folder] / neg [doc]
    elif negonly:
        ts_rs = [Restriction('doc', '...', True)]              # base [doc:*] / neg [doc]
    else:
        ts_rs = [Restriction('doc', '...', False)]
        if 'ts_multitype' in sw or 'multi_type' in sw:
            ts_rs.append(Restriction('folder', '...', False))
    if 'ts_wildcard' in sw and Restriction('doc', '...', True) not in ts_rs:
        ts_rs.append(Restriction('doc', '...', True))
    if 'ts_userset' in sw:
        ts_rs.append(Restriction('doc', 'r0', False))
    ts = Direct(tuple(ts_rs))
    if 'ts_computed' in sw:
        ts = Union((ts, Computed('r0')))
    if 'ts_boolean' in sw:
        ts = Intersection((ts, Direct(tuple(ts_rs))))
    if negonly:
        ts = Exclusion(ts, Direct((Restriction('doc', '...', False),)))

    b0 = [Restriction('user', '...', False)]
    if 'body_wildcard' in sw:
        b0.append(Restriction('user', '...', True))
    r1 = Direct(tuple(b0))
    if 'body_boolean' in sw:
        # r1 becomes TAINTED here, which is what makes r4/r5 below compile to
        # derived-computed / derived-userset leaves rather than plain closure ones.
        r1 = Exclusion(r1, Direct((Restriction('user', '...', False),)))

    # The POSITIVE TTU is UNCONDITIONAL, and that is a deliberate deviation from the
    # design README's `body_ttu` switch. `parent` exists only to be a TTU tupleset, so a
    # config with no TTU tests nothing on the axis this work exists to open -- and with
    # the switch present the RC2 shape (a star parent on a TAINTED tupleset) needed the
    # TRIPLE {ts_wildcard, ts_boolean, body_ttu} and so fell out of the `ci` pair space
    # entirely. Unconditional, it is the PAIR {ts_wildcard, ts_boolean}.
    ast = {('doc', 'r0'): Direct((Restriction('user', '...', False),)),
           ('doc', 'parent'): ts, ('doc', 'r1'): r1,
           ('doc', 'r2'): TTU('r1', 'parent')}
    if 'body_negttu' in sw:
        # `define r3: [user] but not r1 from parent` -- the negated TTU. The RC1/RC2 pins
        # show this is where a dropped TTU parent becomes an authorization FAIL-OPEN.
        ast[('doc', 'r3')] = Exclusion(
            Direct((Restriction('user', '...', False),)), TTU('r1', 'parent'))
    if 'body_computed' in sw:
        # A Computed arm over r1. `via:computed` / `leaf:derived-computed` /
        # `plan:PDerivedComputed` only appear when the REFERENT is tainted, which is why
        # this references r1 (taintable by body_boolean) and not the plain r0.
        ast[('doc', 'r4')] = Union((Direct((Restriction('user', '...', False),)),
                                    Computed('r1')))
    if 'body_userset' in sw:
        # The G2 concrete-userset leaf `[doc#r1]`: over a tainted r1 this is the
        # PDerivedUserset / userset-storage family.
        ast[('doc', 'r5')] = Union((Direct((Restriction('user', '...', False),)),
                                    Direct((Restriction('doc', 'r1', False),))))
    if 'body_wc_userset' in sw:
        # `[doc:*#r1]` -- the wildcard-userset modality. Its own switch because over a
        # DERIVED relation this is a decision-15 scope refusal, and folding it into
        # body_userset would make that whole switch reject rather than compile.
        ast[('doc', 'r6')] = Union((Direct((Restriction('user', '...', False),)),
                                    Direct((Restriction('doc', 'r1', True),))))
    if 'ts_undeclared' in sw:
        # A TTU whose tupleset relation is NOT declared on the object type. It compiles
        # (it is not a parse error) and evaluates constantly empty -- so it is a real
        # grammar point that no existing generator can express, and it is deliberately
        # UNIONED with a live arm rather than standing alone, so the relation it sits on
        # is still driven non-vacuously.
        ast[('doc', 'r7')] = Union((Direct((Restriction('user', '...', False),)),
                                    TTU('r1', 'nodecl')))
    if 'self_ttu' in sw:
        ast[('doc', 'r2')] = Union((ast[('doc', 'r2')], TTU('r2', 'parent')))
    if 'multi_type' in sw:
        ast[('folder', 'r1')] = Direct((Restriction('user', '...', False),))
    owc = frozenset({('doc', 'parent')}) if 'owc' in sw else frozenset()
    return ast, owc


def enumerate_configs(k: int):
    """Every switch subset of size 1..k — the CLOSED config space. Adding a switch
    immediately adds configs, so a new UNKNOWN cell is red on the next run."""
    return [frozenset(c) for j in range(1, k + 1)
            for c in itertools.combinations(SWARM_SWITCHES, j)]


# =========================================================================== #
# 5. REJECTION WITNESSES — the exemption mechanism
#
#    A cell counts "unreachable by design" ONLY if a concrete (schema, owc) the
#    compiler is ASSERTED to refuse carries it. A hand-written EXPECTED_UNREACHABLE
#    list is a future silent pass: the day the compiler starts admitting the shape the
#    list still says "unreachable" and the gate stays green. A rejection witness
#    inverts that -- the moment the compiler admits it the `pytest.raises` fails, the
#    exemption is REVOKED, and the cell goes back to UNKNOWN (red until a generator
#    reaches it). A scope relaxation cannot silently mint a new blind spot.
# =========================================================================== #

@dataclass(frozen=True)
class Rejection:
    name: str
    schema: str
    owc: frozenset
    exc: type
    message: str          # substring that must appear in str(exc)


_REJ_HEAD = 'type user\ntype folder\n  relations\n    define r0: [user]\n'


REJECTION_WITNESSES: tuple[Rejection, ...] = (
    Rejection(
        'tupleset-userset-restriction',
        _REJ_HEAD + ('type doc\n  relations\n'
                     '    define r0: [user]\n'
                     '    define parent: [doc, doc#r0]\n'
                     '    define r2: r0 from parent\n'),
        frozenset(),
        UnsupportedByGraphIndex,
        'tupleset relations must be directly assignable types'),
    Rejection(
        # carries `ttu.ts.restr:wildcard-userset`, which nothing else can reach
        'tupleset-wildcard-userset-restriction',
        _REJ_HEAD + ('type doc\n  relations\n'
                     '    define r0: [user]\n'
                     '    define parent: [doc, doc:*#r0]\n'
                     '    define r2: r0 from parent\n'),
        frozenset(),
        UnsupportedByGraphIndex,
        'tupleset relations must be directly assignable types'),
    Rejection(
        'tupleset-rewritten-arms',
        _REJ_HEAD + ('type doc\n  relations\n'
                     '    define r0: [user]\n'
                     '    define own: [doc]\n'
                     '    define parent: [doc] or own\n'
                     '    define r2: r0 from parent\n'),
        frozenset(),
        UnsupportedByGraphIndex,
        'Zanzibar tupleset semantics read stored tuples only'),
    Rejection(
        # carries `ttu.ts:TTU` -- a TTU whose tupleset is itself a TTU. Design README
        # §6.2 names this as "not designed; named"; as a rejection witness it is
        # positively accounted for instead of silently absent.
        'tupleset-is-itself-a-ttu',
        _REJ_HEAD + ('type doc\n  relations\n'
                     '    define r0: [user]\n'
                     '    define gp: [doc]\n'
                     '    define parent: r0 from gp\n'
                     '    define r2: r0 from parent\n'),
        frozenset(),
        UnsupportedByGraphIndex,
        'Zanzibar tupleset semantics read stored tuples only'),
    Rejection(
        'star-tupleset-over-derived-target',
        _REJ_HEAD + ('type doc\n  relations\n'
                     '    define r0: [user]\n'
                     '    define blk: [user]\n'
                     '    define viewer: [user] but not blk\n'
                     '    define parent: [doc, doc:*]\n'
                     '    define r2: viewer from parent\n'),
        frozenset(),
        UnsupportedByGraphIndex,
        'derives the wildcard userset shape'),
    Rejection(
        'owc-on-derived-relation',
        _REJ_HEAD + ('type doc\n  relations\n'
                     '    define blk: [user]\n'
                     '    define parent: [doc] but not blk\n'
                     '    define r2: blk from parent\n'),
        frozenset({('doc', 'parent')}),
        UnsupportedByGraphIndex,
        'targets a derived (boolean-tainted) relation'),
    Rejection(
        'owc-on-a-ttu-tupleset',
        _REJ_HEAD + ('type doc\n  relations\n'
                     '    define r0: [user]\n'
                     '    define parent: [doc]\n'
                     '    define r1: [user] and r0\n'
                     '    define r2: r1 from parent\n'),
        frozenset({('doc', 'parent')}),
        UnsupportedByGraphIndex,
        'is the tupleset of TTU'),
    Rejection(
        'wildcard-userset-over-derived-relation',
        _REJ_HEAD + ('type doc\n  relations\n'
                     '    define blk: [user]\n'
                     '    define r1: [user] but not blk\n'
                     '    define r6: [user] or [doc:*#r1]\n'),
        frozenset(),
        UnsupportedByGraphIndex,
        'wildcard userset restriction'),
    Rejection(
        # ⚠ FOUND BY THIS WORK, 2026-08-10, and NOT a scoped refusal: a TTU whose
        # tupleset relation is UNDECLARED and whose target relation is DERIVED escapes
        # the decision-15 scope checks and dies inside `compile_boolean_schema` on an
        # internal invariant, as a bare `ValueError`. `tests/parity.py` says out loud
        # that "a bare ValueError from compile is a regression that must surface"; this
        # one is recorded here rather than swallowed, so the family is visible and the
        # exemption is revoked the moment the compiler's behaviour changes. Compare
        # `... define r7: [user] or r0 from nodecl` (UNTAINTED target), which compiles
        # cleanly -- so it is the taint of the TARGET, not the undeclared tupleset, that
        # trips it. Reported, not fixed: fixing the compiler is out of this task's scope.
        'undeclared-tupleset-with-derived-target',
        _REJ_HEAD + ('type doc\n  relations\n'
                     '    define blk: [user]\n'
                     '    define r1: [user] but not blk\n'
                     '    define r7: [user] or r1 from nodecl\n'),
        frozenset(),
        ValueError,
        'Rule then-pattern carries a derived subject predicate'),
    Rejection(
        'cyclic-derived-dependency',
        _REJ_HEAD + ('type doc\n  relations\n'
                     '    define blk: [user]\n'
                     '    define a: ([user] but not blk) or b\n'
                     '    define b: [user] and a\n'),
        frozenset(),
        CyclicDerivedDependency,
        'dependency cycle'),
)


def match_rejection(exc: BaseException) -> Rejection | None:
    """The recorded family a compile refusal belongs to, or None.

    Matching is by ``(exception class, message substring)``. Several witnesses may share
    one FAMILY (one scope check) while carrying different features — e.g. both
    ``parent: [doc, doc#r0]`` and ``parent: [doc, doc:*#r0]`` are refused by the
    directly-assignable-types rule but only the second carries
    ``ttu.ts.restr:wildcard-userset``."""
    for w in REJECTION_WITNESSES:
        if isinstance(exc, w.exc) and w.message in str(exc):
            return w
    return None


def rejection_message_families() -> tuple[str, ...]:
    """The DISTINCT scope-refusal messages, i.e. one entry per compiler check."""
    return tuple(sorted({w.message for w in REJECTION_WITNESSES}))


def rejection_features() -> dict[str, set[str]]:
    """``witness name -> the AST features the refused config would have carried``."""
    return {w.name: ast_features(w.schema, w.owc) for w in REJECTION_WITNESSES}


def rejection_explained_cells() -> set[frozenset]:
    out: set[frozenset] = set()
    for fs in rejection_features().values():
        out |= cells_of(fs)
    return out


# =========================================================================== #
# 6. THE REPORTING DIFFERENTIAL
# =========================================================================== #

def grid_for(ast, present, *, cap: int = 400, rng: random.Random | None = None):
    """Universe u ghosts u ``'*'``, derived from the schema's own shapes — the same
    construction ``ParityEngine._grid`` uses, including its anti-vacuity fallback for a
    schema whose relations are all Computed/TTU (which declares no Direct restriction,
    so the naive grid would be EMPTY and every parity assertion would pass by looping
    zero times)."""
    names: dict[str, set[str]] = {}
    for (_, s_type, s_name, _, o_type, o_name) in present:
        if s_name != '*':
            names.setdefault(s_type, set()).add(s_name)
        if o_name != '*':
            names.setdefault(o_type, set()).add(o_name)
    shapes = {(r.type, r.predicate) for expr in ast.values()
              for d in _iter_directs(expr) for r in d.restrictions}
    subjects = []
    for (s_type, s_pred) in sorted(shapes):
        for name in sorted(names.get(s_type, set())) + [GHOST, '*']:
            subjects.append((s_pred, s_type, name))
    if not subjects:
        subjects = [('...', t, GHOST) for t in sorted({o for (o, _) in ast})]
    queries = []
    for (o_type, rel) in sorted(ast):
        for on in sorted(names.get(o_type, set())) + [GHOST]:
            for (sp, sty, sn) in subjects:
                queries.append((sp, sty, sn, rel, o_type, on))
    assert queries, 'ANTI-VACUITY: the parity grid is EMPTY'
    if len(queries) > cap:
        queries = (rng or random.Random(0)).sample(sorted(queries), cap)
    return queries


class AdmissionDivergence(AssertionError):
    """Backends disagreed on accept/reject. Not a query divergence — a harder failure,
    and one that would otherwise silently make the sweep measure the rejection path."""


@dataclass
class RunResult:
    comparisons: int = 0
    attempted: int = 0
    accepted: int = 0
    driven: bool = False
    graph_dropped: str | None = None
    divergences: list = field(default_factory=list)   # (query, oracle, {backend: ans})

    @property
    def fail_open(self):
        return [d for d in self.divergences
                if not d[1] and any(v for v in d[2].values())]

    @property
    def fail_closed(self):
        return [d for d in self.divergences
                if d[1] and any(not v for v in d[2].values())]


class Diff:
    """Oracle + graph + both set engines, REPORTING divergences instead of asserting.

    ``ParityEngine`` asserts on the first disagreement, which a sweep cannot use: a
    sweep needs to keep going and count. The comparison counter is not decoration —
    ``docs/sabotage-procedure.md``: *a sweep that compared nothing reports success.*

    Paranoia is OFF by default here (the invariant checker cannot see either RC1 or RC2
    — I9 re-runs ``reconcile``, which reads the same wrong ``parent_types`` and agrees
    with itself) and it triples the write cost."""

    def __init__(self, schema: str, owc=frozenset(), *, paranoia: bool = False,
                 grid_cap: int = 400, seed: int = 0):
        self.schema = schema
        self.ast = parse_schema_ast(schema)
        self._rng = random.Random(seed)
        self.grid_cap = grid_cap
        try:
            rs = parse_openfga_schema(schema, object_wildcard_shapes=owc)
            self.graph = _GraphSide(rs, paranoia=paranoia)
            self.drop = None
        except (UnsupportedByGraphIndex, CyclicDerivedDependency,
                DoublyBridgedShapeError) as e:
            self.graph = None
            self.drop = f'{type(e).__name__}: {e}'
        self.sets = [_SetSide(schema, owc, ops) for ops in ALL_SETOPS]
        self.sides = ([self.graph] if self.graph else []) + self.sets
        self.present: set[RawTuple] = set()
        self._names: dict[str, set[str]] = {}

    def add(self, raw: RawTuple) -> bool:
        if raw in self.present:
            return True                       # raw tuples are a SET; duplicate add no-ops
        results = {b.name: b.apply(raw, 'add') for b in self.sides}
        decision = next(iter(results.values()))
        if any(v != decision for v in results.values()):
            raise AdmissionDivergence(f'accept/reject divergence on add {raw}: {results}')
        if decision:
            self.present.add(raw)
            _, s_type, s_name, _, o_type, o_name = raw
            if s_name != '*':
                self._names.setdefault(s_type, set()).add(s_name)
            if o_name != '*':
                self._names.setdefault(o_type, set()).add(o_name)
        return decision

    def grid(self):
        return grid_for(self.ast, self.present, cap=self.grid_cap, rng=self._rng)

    def sweep(self):
        """``(comparisons, divergences)``. One comparison = one (query, backend) pair."""
        oracle = Oracle(self.schema, [OracleTuple(*r) for r in self.present])
        n = 0
        bad = []
        for q in self.grid():
            exp = oracle.check(*q)
            ans = {b.name: b.check(q) for b in self.sides}
            n += len(ans)
            if any(v != exp for v in ans.values()):
                bad.append((q, exp, ans))
        return n, bad

    def close(self):
        for b in self.sides:
            b.close()


# =========================================================================== #
# 7. TWO-REGIME DRIVING
# =========================================================================== #

SPARSE, DENSE, FULL = 'sparse', 'dense', 'full'


def tupleset_relations(ast) -> set[tuple[str, str]]:
    """``(object_type, relation)`` pairs used as the TUPLESET of some TTU."""
    out = set()
    for (otype, _), body in ast.items():
        for n in _walk(body):
            if isinstance(n, TTU):
                out.add((otype, n.tupleset_rel))
    return out


def _shape(t: RawTuple):
    """The admission SHAPE of a raw tuple: ``(relation, object type, subject type,
    is-wildcard)``. Wildcard is part of the shape on purpose — RC2 is a divergence that
    only a ``T:*`` parent exhibits, so folding ``doc:*`` in with ``doc:d1`` would make
    the knockout below unable to isolate it."""
    return (t[3], t[4], t[1], t[2] == '*')


def subsets_for(pool, regime: str, k: int, rng: random.Random, ast=None):
    """The driving discipline, and the single most load-bearing decision in this design.

    ``docs/design/generator-coverage/README.md`` §4 sabotage 4 measured that driving each
    config with the WHOLE pool found **0 divergences** over the same 97 configs that
    small-subset driving detonates. A fail-CLOSED divergence is an under-grant, so ANY
    extra granting tuple supplies an alternative path and masks it — this repo's own IIA
    property (commit ``310fbcb``). ⚠ Re-measured here over the 136-config space the
    number is **3, not 0** (vs 10 for sparse): the masking is large but not total, and
    the README's stronger claim should not be repeated.

    §6.7 then admits the dual, which this function closes. A fail-OPEN divergence is an
    over-grant through a negation, so it is masked from BELOW (a near-empty store gives
    the subtrahend nothing to subtract) *and* from ABOVE (a full pool supplies an
    ALTERNATIVE subtraction path that the defective backend can still see). It is
    visible only in the band between.

    * ``sparse`` — ``k`` random subsets of size 1..3. Random is fine here because ANY
      small subset that happens to contain the causal chain exposes an under-grant.
    * ``dense`` — **deterministic leave-one-shape-out over the TUPLESET relations**:
      for each admission shape written to a TTU tupleset relation, the whole pool MINUS
      every tuple of that shape. Randomly dropping 1-3 arbitrary tuples was tried first
      and is NOT good enough — measured 2026-08-10: over the same 96 driven configs it
      found the live fail-open under one switch set and 0 under another (116 s, FO=0),
      because the masking alternative is a whole SHAPE (all `folder`-typed parents), not
      a tuple. A discipline whose detection depends on the seed is not a control.
    * ``full`` — the whole pool. Retained ONLY as the negative control; it is what
      driving looks like when nobody has thought about IIA, and it sees neither
      direction.
    """
    pool = list(pool)
    if not pool:
        return []
    if regime == FULL:
        return [tuple(pool)]
    if regime == SPARSE:
        out = []
        for _ in range(k):
            m = min(len(pool), rng.randint(1, 3))
            out.append(tuple(rng.sample(pool, m)))
        return out
    ts_rels = tupleset_relations(ast or {})
    shapes = sorted({_shape(t) for t in pool if (t[4], t[3]) in ts_rels})
    out = []
    for sh in shapes[:k]:
        rest = tuple(t for t in pool if _shape(t) != sh)
        if rest and len(rest) != len(pool):
            out.append(rest)
    return out or [tuple(pool)]


def drive_config(ast, owc, *, regime: str, k: int = 2, seed: int = 0,
                 pool_cap: int = 24, grid_cap: int = 400) -> RunResult:
    """Compile ``(ast, owc)``, then drive it under ``regime`` and sweep the grid.

    Returns a ``RunResult``; raises nothing except ``AdmissionDivergence`` (which is a
    genuine failure, not a shape the sweep should skip). Compile refusals are reported
    via ``RunResult.graph_dropped`` / by re-raising so the caller can classify."""
    schema = unparse_schema_ast(ast)
    pool = swarm_op_pool(ast)[:pool_cap]
    rng = random.Random(seed)
    res = RunResult()
    for subset in subsets_for(pool, regime, k, rng, ast):
        d = Diff(schema, owc, grid_cap=grid_cap, seed=seed)
        try:
            res.graph_dropped = d.drop
            for t in subset:
                res.attempted += 1
                if d.add(t):
                    res.accepted += 1
            n, bad = d.sweep()
            res.comparisons += n
            res.divergences.extend(bad)
            if n:
                res.driven = True
        finally:
            d.close()
    return res


# =========================================================================== #
# 8. THE SYNTHETIC DEFECT — a permanent, bug-independent control
# =========================================================================== #

def dropped_parent_defect(subject_type: str, relation: str):
    """The RC1 defect, as an injectable predicate: *"every stored tuple on ``relation``
    whose subject type is ``subject_type`` is invisible."*

    That is precisely what a missing entry in the compiled ``parent_types`` does
    (`tests/test_ttu_tupleset_parent_types.py`) — note it drops the whole TYPE, not one
    tuple. Modelling it as a single dropped tuple is too weak: any sibling tuple of the
    same type masks it, and the control then reports "masked" everywhere and proves
    nothing about the regime."""
    return lambda t: t[1] == subject_type and t[3] == relation


def detect_synthetic(schema: str, present, grid, defect):
    """``(comparisons, [(query, oracle, defective)])`` for an injected synthetic defect.

    Why synthetic rather than "just use the live bug": the live bug is going to be
    FIXED, and a control that only works while a bug is open is a control that silently
    stops controlling — the house failure mode applied to controls themselves. The
    defect here is injected by the caller, so the regime comparison keeps its teeth
    forever."""
    truth = Oracle(schema, [OracleTuple(*r) for r in present])
    broken = Oracle(schema, [OracleTuple(*r) for r in present if not defect(r)])
    bad = []
    n = 0
    for q in grid:
        exp = truth.check(*q)
        got = broken.check(*q)
        n += 1
        if got != exp:
            bad.append((q, exp, got))
    return n, bad
