"""Prototype of (c): TTU tupleset drawn from a real expression grammar.
Enumerates tupleset bodies x target bodies, co-generates a schema-VALID pool,
applies the whole pool, sweeps the grid.  Reports divergences + comparison count."""
import sys, itertools, traceback
sys.path.insert(0, r'C:\Users\user\AppData\Local\Temp')
from zz_diff import Diff

HEAD = 'type user\ntype folder\ntype doc\n  relations\n'

# tupleset bodies for relation `parent` on doc  (name -> (body, restrictions used))
TS = {
 'plain':        '[doc]',
 'multitype':    '[doc, folder]',
 'excl_only_neg':'[folder] but not [doc]',     # the live bug shape
 'excl_pos_neg': '[doc, folder] but not [doc]',
 'union':        '[doc] or [folder]',
 'inter':        '[doc, folder] and [doc]',
 'wildcard':     '[doc, doc:*]',
 'wc_excl':      '[doc, doc:*] but not [doc]',
 'userset':      '[doc, doc#viewer]',
 'computed_ref': 'owner',
}
# target bodies for `viewer` on doc AND folder
TGT = {
 'direct':  '[user]',
 'excl':    '[user] but not blocked',
 'inter':   '[user] and [user]',
}

def build(ts_name, tgt_name):
    ts = TS[ts_name]; tgt = TGT[tgt_name]
    s = HEAD
    s += '    define blocked: [user]\n'
    s += '    define owner: [doc]\n'
    s += f'    define parent: {ts}\n'
    s += f'    define viewer: {tgt}\n'
    s += '    define inherited: viewer from parent\n'
    s += 'type folder\n  relations\n'
    s += '    define blocked: [user]\n'
    s += f'    define viewer: {tgt}\n'
    return s

# oops: doc must come after folder decl; rebuild cleanly
def build(ts_name, tgt_name):
    ts = TS[ts_name]; tgt = TGT[tgt_name]
    return ('type user\n'
            'type folder\n  relations\n'
            '    define blocked: [user]\n'
            f'    define viewer: {tgt}\n'
            'type doc\n  relations\n'
            '    define blocked: [user]\n'
            '    define owner: [doc]\n'
            f'    define parent: {ts}\n'
            f'    define viewer: {tgt}\n'
            '    define inherited: viewer from parent\n')

DOCS=['d1','d2']; FOLDERS=['f1']; USERS=['u1']

def pool(ts_name):
    P=set()
    for u in USERS:
        for on in DOCS: P.add(('...','user',u,'viewer','doc',on)); P.add(('...','user',u,'blocked','doc',on))
        for on in FOLDERS: P.add(('...','user',u,'viewer','folder',on)); P.add(('...','user',u,'blocked','folder',on))
    for a in DOCS:
        for b in DOCS: P.add(('...','doc',a,'owner','doc',b))
    ts = TS[ts_name]
    for on in DOCS:
        if '[doc' in ts:
            for a in DOCS: P.add(('...','doc',a,'parent','doc',on))
        if 'folder' in ts:
            for f in FOLDERS: P.add(('...','folder',f,'parent','doc',on))
        if 'doc:*' in ts: P.add(('...','doc','*','parent','doc',on))
        if 'doc#viewer' in ts:
            for a in DOCS: P.add(('viewer','doc',a,'parent','doc',on))
        if ts == 'owner':
            for a in DOCS: P.add(('...','doc',a,'parent','doc',on))
    return sorted(P)

tot_cmp=0; found=[]
for ts_name, tgt_name in itertools.product(TS, TGT):
    schema = build(ts_name, tgt_name)
    try:
        d = Diff(schema)
    except Exception as e:
        print(f'{ts_name:14s} {tgt_name:8s} CONSTRUCT-REFUSED {type(e).__name__}: {e}'); continue
    if d.drop:
        print(f'{ts_name:14s} {tgt_name:8s} GRAPH-DROPPED {d.drop}'); d.close(); continue
    try:
        for t in pool(ts_name):
            d.add(t)
        n, bad = d.sweep()
    except Exception as e:
        print(f'{ts_name:14s} {tgt_name:8s} EXPLODED {type(e).__name__}: {e}'); d.close(); continue
    tot_cmp += n
    tag = 'OK ' if not bad else f'DIVERGE({len(bad)})'
    print(f'{ts_name:14s} {tgt_name:8s} cmp={n:5d} {tag}')
    for q,exp,ans in bad[:3]:
        direction = 'FAIL-OPEN' if any(v and not exp for v in ans.values()) else 'fail-closed'
        print(f'      {direction} q={q} oracle={exp} {ans}')
    if bad: found.append((ts_name,tgt_name,bad))
    d.close()
assert tot_cmp>0, 'VACUOUS SWEEP'
print(f'\ntotal comparisons {tot_cmp}; configs with divergence: {len(found)}')
