"""DW-1 sizing probe (2026-09-23): a straw-man in_w4_fragment over the PRODUCTION
AST, compared to the hand-maintained GRAPH_FRAGMENT list. Kept as the evidence behind
docs/dw1-decidable-w4fragment-2026-09-23.md sec 2 -- NOT a checker; nothing pins it to Lean.
Run from the repo root."""
import sys
sys.path.insert(0, '.')
from zanzibar_utils_v1 import (Direct, Computed, TTU, Union, Intersection, Exclusion,
                               parse_schema_ast, compute_taint, parse_openfga_schema,
                               wildcard_userset_restriction_shapes, UnsupportedByGraphIndex)
from formal.conformance import corpus as C

BARE = '...'

def kids(e):
    if isinstance(e, (Union, Intersection)): return e.children
    if isinstance(e, Exclusion): return (e.base, e.subtract)
    return ()

def computed_or_direct(e):
    if isinstance(e, TTU): return False
    return all(computed_or_direct(c) for c in kids(e))

def computed_only(e):
    if isinstance(e, (TTU, Direct)): return False
    return all(computed_only(c) for c in kids(e))

def direct_arms_bare(e):
    if isinstance(e, Direct): return all(r.predicate == BARE for r in e.restrictions)
    return all(direct_arms_bare(c) for c in kids(e))

def directs_all(e):
    if isinstance(e, Direct): yield e
    for c in kids(e): yield from directs_all(c)

def expr_directs_union(e):  # Lean exprDirects: through union only
    if isinstance(e, Direct): return [e]
    if isinstance(e, Union): return [d for c in e.children for d in expr_directs_union(c)]
    return []

def computed_refs(e):
    if isinstance(e, Computed): return [e.relation]
    return [r for c in kids(e) for r in computed_refs(c)]

def ttus_union(e):  # Lean exprArms ttu arms: union-only (untainted defs have no inter/excl)
    if isinstance(e, TTU): return [e]
    if isinstance(e, Union): return [t for c in e.children for t in ttus_union(c)]
    return []

def schema_fields(ast):
    tainted = compute_taint(ast)
    der = lambda k: k in tainted
    out = {}
    D = [(k, e) for k, e in ast.items() if der(k)]
    out['computedOrDirect'] = all(computed_or_direct(e) for _, e in D)
    out['directArmsBare'] = all(direct_arms_bare(e) for _, e in D)
    out['directArmsConcrete'] = all(not r.wildcard for _, e in D for d in directs_all(e) for r in d.restrictions)
    out['computedOnlyOperands'] = all(
        computed_only(ast[(k[0], r)]) for k, e in D for r in computed_refs(e)
        if der((k[0], r)) and (k[0], r) in ast)
    out['noUnionDirects'] = all(not expr_directs_union(e) for _, e in D)
    out['twoStrata'] = all(
        not der((k[0], r2))
        for k, e in D for r in computed_refs(e) if der((k[0], r)) and (k[0], r) in ast
        for r2 in computed_refs(ast[(k[0], r)]))
    out['wsBare'] = not wildcard_userset_restriction_shapes(ast)
    # TTU rewrite rules of UNTAINTED defs: (objectType, matchRel=tupleset, target)
    rules = [(k[0], t.tupleset_rel, t.target_rel) for k, e in ast.items() if not der(k) for t in ttus_union(e)]
    der_names = {r for (_t, r) in tainted}
    out['term.NoTtuTarget'] = all(tr not in der_names for (_o, _m, tr) in rules)
    return out, rules, der_names

def store_fields(tuples, rules, der_names):
    out = {}
    out['bareStar'] = all((t.subject_name != '*' or t.subject_predicate in ('...', None, Ellipsis)) and t.object_name != '*' for t in tuples)
    ts_keys = {(o, m) for (o, m, _tr) in rules}
    out['ttuStarFree'] = all(not (t.subject_name == '*' and (t.object_type, t.relation) in ts_keys) for t in tuples)
    def sp(t):
        p = t.subject_predicate
        return '...' if p in (None, Ellipsis) else p
    out['term.NoStoreSubjectR'] = all(sp(t) not in der_names for t in tuples)
    return out

def classify(name, spec):
    text, tuples, ow = spec
    ast = parse_schema_ast(text)
    sf, rules, dn = schema_fields(ast)
    st = store_fields(tuples, rules, dn)
    f = {**sf, **st}
    try:
        rs = parse_openfga_schema(text, object_wildcard_shapes=frozenset(map(tuple, ow)))
        ns = 0 if rs.compiled is None else len(rs.compiled.strata)
        comp = 'ok'
    except (UnsupportedByGraphIndex, ValueError) as ex:
        ns, comp = None, type(ex).__name__
    return f, ns, comp

allsets = [('SCHEMAS', C.SCHEMAS), ('MULTI_STRATUM', C.MULTI_STRATUM_SCHEMAS),
           ('TTU_USERSET', C.TTU_USERSET_SCHEMAS), ('SELF_REF', C.SELF_REFERENTIAL_SCHEMAS)]
gf = set(C.GRAPH_FRAGMENT)
agree = disagree = 0
for label, d in allsets:
    for name, spec in sorted(d.items()):
        f, ns, comp = classify(name, spec)
        inside = all(f.values())
        listed = (label == 'SCHEMAS' and name in gf)
        fails = [k for k, v in f.items() if not v]
        ts_ok = f['twoStrata']
        strata_ok = ns is not None and ns <= 2
        mark = 'OK ' if inside == listed else 'DIFF'
        if inside == listed: agree += 1
        else: disagree += 1
        print(f"{mark} {label}:{name} mirror={'IN' if inside else 'OUT'} listed={'IN' if listed else 'OUT'} "
              f"strata={ns} compile={comp} twoStrata={ts_ok} fails={fails}")
print(f"agree={agree} disagree={disagree}")
