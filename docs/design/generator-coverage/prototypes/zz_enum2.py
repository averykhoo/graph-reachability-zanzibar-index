"""Deterministic witness builder: each enabled switch contributes its arm UNCONDITIONALLY
(no sampling), so a config's witness has maximal feature density."""
import sys, time, itertools, collections, json
sys.path.insert(0, r'C:\Users\user\AppData\Local\Temp')
sys.path.insert(0, r'C:\Users\user\PycharmProjects\graph-reachability-zanzibar-index')
import zz_cells as C, zz_gen2 as G
from zanzibar_utils_v1 import (Computed, Direct, Exclusion, Intersection, Restriction,
                               TTU, Union, unparse_schema_ast)

A=C.alphabet(); ALLP={frozenset(p) for p in itertools.combinations(sorted(A),2)}
SW=G.SWARM_SWITCHES

def witness(sw):
    """(ast, owc).  r0 = plain base; parent = the tupleset under test; r1/r2 consumers."""
    negonly = 'ts_negonly' in sw
    # A neg-only arm means the restriction in the SUBTRAHEND occurs NOWHERE in the base
    # (otherwise the same raw tuple routes to both arms and cancels -- the shape becomes
    # vacuous and the cell is 'compiled but never driven').  Two ways to build it:
    #   multi-type : base [folder] / neg [doc]         (the 2026-08-10 live-bug shape)
    #   single-type: base [doc:*]  / neg [doc]         (star base, concrete subtrahend)
    if negonly and ('ts_multitype' in sw or 'multi_type' in sw):
        ts_rs=[Restriction('folder','...',False)]
    elif negonly:
        ts_rs=[Restriction('doc','...',True)]
    else:
        ts_rs=[Restriction('doc','...',False)]
        if 'ts_multitype' in sw or 'multi_type' in sw: ts_rs.append(Restriction('folder','...',False))
    if 'ts_wildcard' in sw and Restriction('doc','...',True) not in ts_rs:
        ts_rs.append(Restriction('doc','...',True))
    if 'ts_userset' in sw: ts_rs.append(Restriction('doc','r0',False))
    ts = Direct(tuple(ts_rs))
    if 'ts_computed' in sw: ts = Union((ts, Computed('r0')))
    if 'ts_boolean' in sw:  ts = Intersection((ts, Direct(tuple(ts_rs))))
    if negonly:
        ts = Exclusion(ts, Direct((Restriction('doc','...',False),)))
    b0=[Restriction('user','...',False)]
    if 'body_wildcard' in sw: b0.append(Restriction('user','...',True))
    if 'body_userset' in sw: b0.append(Restriction('doc','r0',False))
    r1 = Direct(tuple(b0))
    if 'body_computed' in sw: r1 = Union((r1, Computed('r0')))
    if 'body_boolean' in sw: r1 = Exclusion(r1, Direct((Restriction('user','...',False),)))
    r2 = TTU('r1','parent') if 'body_ttu' in sw else Direct((Restriction('user','...',False),))
    ast={('doc','r0'): Direct((Restriction('user','...',False),)),
         ('doc','parent'): ts, ('doc','r1'): r1, ('doc','r2'): r2}
    if 'self_ttu' in sw: ast[('doc','r2')] = Union((ast[('doc','r2')], TTU('r2','parent')))
    if 'multi_type' in sw: ast[('folder','r1')] = Direct((Restriction('user','...',False),))
    owc = frozenset({('doc','parent')}) if 'owc' in sw else frozenset()
    return ast, owc

for K, label in ((1,'singletons'),(2,'pairs'),(3,'triples')):
    cfgs=[frozenset(c) for k in range(1,K+1) for c in itertools.combinations(SW,k)]
    t0=time.time(); cells=set(); feats=collections.Counter(); ok=0; rej=collections.Counter()
    for sw in cfgs:
        ast,owc = witness(sw)
        try: fs=C.features(unparse_schema_ast(ast), owc)
        except Exception as e: rej[type(e).__name__]+=1; continue
        ok+=1
        for f in fs: feats[f]+=1
        cells.update(C.cells_of(fs))
    t=time.time()-t0
    print(f'{label:10s} configs={len(cfgs):5d} compiled={ok:5d} rejected={dict(rej)} '
          f'CELLS={len(cells)}/{len(ALLP)} ({100*len(cells)/len(ALLP):.1f}%) '
          f'FEATURES={len(feats)}/{len(A)}  compile-time={t:.1f}s')
    if K==2:
        json.dump(sorted('|'.join(sorted(c)) for c in cells), open('zz_enum_cells.json','w'))
        print('   missing features:', sorted(set(A)-set(feats)))
