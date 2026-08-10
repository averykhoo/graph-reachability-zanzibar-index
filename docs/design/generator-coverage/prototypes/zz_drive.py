"""Time the DRIVEN deterministic enumerator (build engines + apply pool + grid sweep)
and report divergences.  Non-vacuity: total comparisons must be > 0."""
import sys, time, itertools, collections, json
sys.path.insert(0, r'C:\Users\user\AppData\Local\Temp')
sys.path.insert(0, r'C:\Users\user\PycharmProjects\graph-reachability-zanzibar-index')
import zz_cells as C, zz_gen2 as G
from zz_enum2 import witness
from zz_diff import Diff
from zanzibar_utils_v1 import unparse_schema_ast
A=C.alphabet(); ALLP={frozenset(p) for p in itertools.combinations(sorted(A),2)}
SW=G.SWARM_SWITCHES
K=int(sys.argv[1]) if len(sys.argv)>1 else 2
cfgs=[frozenset(c) for k in range(1,K+1) for c in itertools.combinations(SW,k)]
t0=time.time(); cells=set(); ncmp=0; div=[]; ok=0; drop=0; rej=collections.Counter()
for sw in cfgs:
    ast,owc = witness(sw)
    schema = unparse_schema_ast(ast)
    try: fs = C.features(schema, owc)
    except Exception as e: rej[type(e).__name__]+=1; continue
    try: d = Diff(schema, owc)
    except Exception as e: rej['engine:'+type(e).__name__]+=1; continue
    if d.drop: drop+=1
    pool = G.swarm_op_pool(ast)
    try:
        for t in pool[:24]: d.add(t)
        n,bad = d.sweep()
    except Exception as e:
        rej['run:'+type(e).__name__]+=1; d.close(); continue
    ncmp += n; ok += 1
    cells.update(C.cells_of(fs))          # cell counts only when DRIVEN
    if bad: div.append((sorted(sw), bad[:2]))
    d.close()
t=time.time()-t0
assert ncmp>0, 'VACUOUS'
print(f'K<={K}: configs={len(cfgs)} driven={ok} graph-dropped={drop} rejected={dict(rej)}')
print(f'comparisons={ncmp}  DRIVEN CELLS={len(cells)}/{len(ALLP)} ({100*len(cells)/len(ALLP):.1f}%)')
print(f'wall time = {t:.1f}s   ({t/max(ok,1)*1000:.0f} ms/config)')
print(f'configs with a DIVERGENCE: {len(div)}')
for sw,bad in div[:8]:
    for q,exp,ans in bad[:1]:
        d_ = 'FAIL-OPEN' if any(v and not exp for v in ans.values()) else 'fail-closed'
        print(f'  {d_}  sw={sw}\n      q={q} oracle={exp} {ans}')
