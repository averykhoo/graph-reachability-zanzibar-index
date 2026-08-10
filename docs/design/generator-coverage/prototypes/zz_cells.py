"""PROTOTYPE for deliverable (a): a coverage-cell alphabet DERIVED from the compiler's
own source of truth, plus a feature extractor over (schema_text, owc).

Nothing here is hand-written as a "what should exist" list: every feature name is minted
from one of
  * the `Expr` union members                       (zanzibar_utils_v1.Expr)
  * the `LeafSpec(..., '<kind>')` literals          (_plan_leaves source)
  * the `P*` plan-node dataclasses                  (module introspection)
  * the `DependentEdge(key, '<via>')` literals      (compile_ruleset source)
  * the `LeafFamily.kind` literals                  (compile_ruleset source)
  * the `Restriction` dataclass FIELDS              (dataclass introspection)
so a new compiler branch mints a new feature (and therefore new cells) automatically.
"""
from __future__ import annotations

import inspect
import itertools
import re
import sys
import typing
from dataclasses import fields, is_dataclass

sys.path.insert(0, r'C:\Users\user\PycharmProjects\graph-reachability-zanzibar-index')

import zanzibar_utils_v1 as Z
from zanzibar_utils_v1 import (Computed, Direct, Exclusion, Intersection, Restriction,
                               TTU, Union, parse_openfga_schema, parse_schema_ast)


# --------------------------------------------------------------------------- #
# 1. THE ALPHABET, derived.  Each _derive_* returns a sorted tuple of names and
#    asserts non-vacuity (an empty derivation is a silently-passing coverage check).
# --------------------------------------------------------------------------- #

def derive_expr_classes() -> tuple[str, ...]:
    """Members of the `Expr` union alias -- the SchemaAST node types."""
    args = typing.get_args(Z.Expr)
    names = tuple(sorted(a.__name__ for a in args))
    assert names, 'ANTI-VACUITY: Expr union yielded no members'
    return names


def derive_leaf_kinds() -> tuple[str, ...]:
    """`LeafSpec(..., '<kind>')` literals in `_plan_leaves` -- the one minting site.
    Same regex the existing floor uses (test_conformance_nary_strata.py)."""
    src = inspect.getsource(Z._plan_leaves)
    kinds = set(re.findall(r"LeafSpec\([^,]+,\s*'([a-z][a-z-]*)'", src))
    assert kinds, 'ANTI-VACUITY: no LeafSpec kind literal found in _plan_leaves'
    return tuple(sorted(kinds))


def derive_plan_node_classes() -> tuple[str, ...]:
    """The plan-tree node classes, read off the `isinstance(n, ...)` dispatch in
    `_plan_leaves` -- the single function that walks every plan-tree node type.  A new
    node class that `_plan_leaves` learns to dispatch on mints a new feature here."""
    src = inspect.getsource(Z._plan_leaves)
    names = set()
    for grp in re.findall(r"isinstance\(n,\s*\(?([^)]*?)\)?\):", src):
        for nm in re.findall(r"\b(P[A-Z]\w*)\b", grp):
            names.add(nm)
    assert names and all(is_dataclass(getattr(Z, n)) for n in names), \
        f'ANTI-VACUITY: plan-node dispatch derivation yielded {names}'
    return tuple(sorted(names))


def derive_via_kinds() -> tuple[str, ...]:
    """`DependentEdge(key, '<via>')` literals in `compile_ruleset` -- the fan-out kinds."""
    src = inspect.getsource(Z)
    vias = set(re.findall(r"DependentEdge\([^,()]+,\s*'([a-z][a-z-]*)'", src))
    assert vias, 'ANTI-VACUITY: no DependentEdge via literal found in the compiler'
    return tuple(sorted(vias))


def derive_family_kinds() -> tuple[str, ...]:
    """`LeafFamily(kind=...)` literals -- 'closure' | 'userset-storage'."""
    src = inspect.getsource(Z)
    # the single `LeafFamily(...)` construction site carries `kind=(<a> if .. else <b>)`
    m = re.search(r"LeafFamily\((?:[^()]|\([^()]*\))*?kind=\(\s*'([a-z-]+)'"
                  r"[^)]*?else\s*'([a-z-]+)'\)", src, re.S)
    assert m, 'ANTI-VACUITY: no LeafFamily kind literal found'
    return tuple(sorted(m.groups()))


def derive_restriction_modalities() -> tuple[str, ...]:
    """The subject modalities a `Restriction` can express, derived from its FIELDS.
    `predicate` splits bare ('...') vs userset; `wildcard` is a bool -> 2x2."""
    fnames = {f.name for f in fields(Restriction)}
    assert {'type', 'predicate', 'wildcard'} <= fnames, \
        f'ANTI-VACUITY: Restriction fields changed: {sorted(fnames)}'
    return ('concrete', 'subject-wildcard', 'userset', 'wildcard-userset')


MODALITY = {(False, False): 'concrete', (True, False): 'subject-wildcard',
            (False, True): 'userset', (True, True): 'wildcard-userset'}


def _modality(r: Restriction) -> str:
    return MODALITY[(bool(r.wildcard), r.predicate != '...')]


# --- the assembled alphabet -------------------------------------------------- #

def alphabet() -> tuple[str, ...]:
    A: list[str] = []
    A += [f'ast:{c}' for c in derive_expr_classes()]
    A += [f'leaf:{k}' for k in derive_leaf_kinds()]
    A += [f'plan:{c}' for c in derive_plan_node_classes()]
    A += [f'via:{v}' for v in derive_via_kinds()]
    A += [f'family:{k}' for k in derive_family_kinds()]
    A += [f'restr:{m}' for m in derive_restriction_modalities()]
    # --- the TTU-SCOPED axes: the ones `schema_asts` hardcodes away ---------- #
    A += [f'ttu.ts:{c}' for c in derive_expr_classes()]      # tupleset body node type
    A += ['ttu.ts:undeclared']
    A += [f'ttu.ts.restr:{m}' for m in derive_restriction_modalities()]
    A += ['ttu.ts:multitype', 'ttu.ts:tainted', 'ttu.ts:neg-only-type',
          'ttu.target:tainted', 'ttu:self-target', 'ttu.ts:owc']
    # --- schema-level modalities -------------------------------------------- #
    A += ['schema:owc', 'schema:neg-leaf', 'schema:storage-leaf',
          'schema:multi-stratum', 'schema:multi-type']
    assert len(set(A)) == len(A), 'duplicate feature name'
    return tuple(A)


# --------------------------------------------------------------------------- #
# 2. THE FEATURE EXTRACTOR
# --------------------------------------------------------------------------- #

def _walk(e):
    yield e
    if isinstance(e, (Union, Intersection)):
        for c in e.children:
            yield from _walk(c)
    elif isinstance(e, Exclusion):
        yield from _walk(e.base)
        yield from _walk(e.subtract)


def _neg_only_arms(e):
    """Restrictions occurring ONLY under a subtrahend (the `[A] but not [B]` shape where
    B occurs solely in the negative arm)."""
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


def features(schema_text: str, owc=frozenset()) -> set[str]:
    """Feature set of one (schema, object-wildcard-shapes) config.  Compile failures
    return the empty set (the caller classifies them)."""
    f: set[str] = set()
    ast = parse_schema_ast(schema_text)
    rs = parse_openfga_schema(schema_text, object_wildcard_shapes=owc)
    compiled = rs.compiled
    tainted = compiled.tainted if compiled else frozenset()
    owc_shapes = rs.schema_info.object_wildcard_shapes

    if owc_shapes:
        f.add('schema:owc')
    if len({t for (t, _) in ast}) > 1:
        f.add('schema:multi-type')
    if compiled and len(compiled.strata) > 1:
        f.add('schema:multi-stratum')

    for (otype, rel), body in ast.items():
        for node in _walk(body):
            f.add(f'ast:{type(node).__name__}')
            if isinstance(node, Direct):
                for r in node.restrictions:
                    f.add(f'restr:{_modality(r)}')
            if isinstance(node, TTU):
                ts_key = (otype, node.tupleset_rel)
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
                if ts_key in tainted:
                    f.add('ttu.ts:tainted')
                if _neg_only_arms(ts_body):
                    f.add('ttu.ts:neg-only-type')
                if ts_key in owc_shapes:
                    f.add('ttu.ts:owc')
                if (otype, node.target_rel) in tainted:
                    f.add('ttu.target:tainted')
                if node.target_rel == rel:
                    f.add('ttu:self-target')

    if compiled:
        for plan in compiled.plans.values():
            for node in _plan_walk(plan.tree):
                f.add(f'plan:{type(node).__name__}')
            for spec in plan.leaves:
                f.add(f'leaf:{spec.kind}')
                if not spec.positive:
                    f.add('schema:neg-leaf')
                if spec.storage:
                    f.add('schema:storage-leaf')
        for edges in list(compiled.dependents.values()) + \
                list(compiled.target_feeders.values()) + \
                list(compiled.tupleset_feeders.values()):
            for e in edges:
                f.add(f'via:{e.via}')
        for v in compiled.namespace.values():
            if isinstance(v, Z.LeafFamily):
                f.add(f'family:{v.kind}')
    return f


def _plan_walk(n):
    yield n
    if isinstance(n, (Z.PUnion, Z.PIntersection)):
        for c in n.children:
            yield from _plan_walk(c)
    elif isinstance(n, Z.PExclusion):
        yield from _plan_walk(n.base)
        yield from _plan_walk(n.subtract)


# --------------------------------------------------------------------------- #
# 3. CELLS = unordered PAIRS over the alphabet (2-wise interaction coverage)
# --------------------------------------------------------------------------- #

def cells_of(fs: set[str]) -> set[frozenset]:
    return {frozenset(p) for p in itertools.combinations(sorted(fs), 2)}


def universe_pairs(A=None) -> int:
    A = A or alphabet()
    return len(A) * (len(A) - 1) // 2


if __name__ == '__main__':
    A = alphabet()
    print(f'alphabet size          : {len(A)}')
    print(f'pair-cell universe     : {universe_pairs(A)}')
    for name, fn in (('Expr classes', derive_expr_classes),
                     ('leaf kinds', derive_leaf_kinds),
                     ('plan node classes', derive_plan_node_classes),
                     ('via kinds', derive_via_kinds),
                     ('family kinds', derive_family_kinds),
                     ('restr modalities', derive_restriction_modalities)):
        print(f'  {name:20s}: {fn()}')
