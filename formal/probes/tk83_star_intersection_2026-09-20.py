"""`TK83` -- is a star-admitting intersection with a derived dep reachable in the tree,
and does it write the residue `docs/tk74-staleness-net-2026-09-18.md` sec 9.5 said it
would not?

WHY. sec 9.5 recorded, correctly for its fixture, that a half-stale intersection writes
**no residue at all** and that "the divergence is carried entirely in materialized closure
edges". Its own caveat flagged the STARRED case as *untested, not tested-and-clean*, and
sec 10.5 then refuted it -- on `.scratch/tk74d-starisect/star_isect.fga`, a gitignored file.
`TK83` exists because the shape was unreachable from anything tracked.

This probe is the acceptance instrument for putting it in the tree. It answers two
separate questions and does not conflate them:

  (A) STRUCTURAL -- over every `.fga` in `tests/fga_schemas/`, which `PIntersection`
      plans have BOTH a non-empty `Plan.deps` AND a star-admitting leaf child? sec 10.5
      measured 3 intersections and 0 such plans. The new fixture must be the only one.

  (B) OPERATIONAL -- does the intersection actually WRITE a starred `ResidueV1` row?
      This is the claim sec 9.5 got wrong, and it is a measurement, not a code read.
      A structural yes with an empty residue would mean the fixture is the wrong shape.

    C:/Users/user/anaconda3/envs/graph-reachability-zanzibar-index/python.exe \
        formal/probes/tk83_star_intersection_2026-09-20.py

(!) INSTRUMENT CONTROLS, three, because each of (A) and (B) has a way to pass vacuously.

  * (I1) The corpus scan must SEE the intersections it is scanning. A census that found
    0 `PIntersection` nodes anywhere would report "the new fixture is the only one" and
    be reporting a broken walker. The probe refuses unless it finds the 3 sec 10.5 named.
  * (I2) The graph side must be present. `ParityEngine` degrades to 3-way when the graph
    refuses a schema (`graph_drop_reason`), and every residue read below would then be
    against a store nothing wrote.
  * (I3) The residue dump is run on `demorgans_law_2.fga` too, under the SAME workload
    shape. It is the one-token-different control: if the starred row appeared there as
    well, the row would not be evidence about the star.

THE VERDICT (2026-09-20g): **both questions answered YES, and sec 9.5 is refuted from a
TRACKED fixture.** `star_admitting_intersection.fga` is the only plan in the corpus with
both a non-empty dep and a star-admitting leaf child, and it writes
`('role','authorized_user','r3') stars=[['user','...']]`. The one-token control writes no
residue row on that key AT ALL (4 rows vs 5) and carries `stars=[]` one relation further at
`('doc','access','d2')` -- which is exactly the propagation sec 10.5 measured, now visible
as a standing difference between two tracked fixtures rather than only under fault
injection. The end-to-end answer differs too: `access(bob, doc:d2)` is True on the new
fixture and False on the control, so the star is load-bearing and not decoration.

RAN 2026-09-20g, VERBATIM stdout:

    === (A) STRUCTURAL -- every PIntersection plan in tests/fga_schemas/ ===
    fixture                            key                                str  star? deps
    boolean_wildcards                  ('doc', 'restricted')                0  True  ()
    demorgans_law_2                    ('role', 'authorized_user')          4  False (('role', 'role_user_met'),)
    star_admitting_intersection        ('role', 'authorized_user')          4  True  (('role', 'role_user_met'),)
    tupleset_shapes                    ('doc', 'approved_parent')           0  False ()

    (I1) control -- the sec 10.5 star column reproduced on all 3 pre-existing intersections
    (A) plans with BOTH a non-empty dep AND a star-admitting child: [('star_admitting_intersection', ('role', 'authorized_user'))]

    === (B) OPERATIONAL -- star_admitting_intersection.fga ===
        grants: [('user:*', 'taken'), ('user:alice', 'taken')]
        answers: {'access(alice, doc:d2)': True, 'authorized_user(alice, role:r3)': True, 'access(bob, doc:d2)': True}
        ResidueV1 rows (unit: residue rows): 5
          ('cond', 'user_met_requirement', 'c1')   stars=[['user', '...']]   neg=[]   upos=[]
          ('cond', 'user_missing_requirement', 'c1')   stars=[]   neg=[]   upos=[6]
          ('doc', 'access', 'd2')   stars=[['user', '...']]   neg=[]   upos=[17]
          ('role', 'authorized_user', 'r3')   stars=[['user', '...']]   neg=[]   upos=[]
          ('role', 'role_user_met', 'r3')   stars=[['user', '...']]   neg=[]   upos=[11]
        starred residue on the INTERSECTION (authorized_user): [{'key': ('role', 'authorized_user', 'r3'), 'stars': [['user', '...']], 'neg': [], 'upos': []}]

    === (B) OPERATIONAL -- demorgans_law_2.fga ===
        grants: [('user:*', 'refused'), ('user:alice', 'taken')]
        answers: {'access(alice, doc:d2)': True, 'authorized_user(alice, role:r3)': True, 'access(bob, doc:d2)': False}
        ResidueV1 rows (unit: residue rows): 4
          ('cond', 'user_met_requirement', 'c1')   stars=[['user', '...']]   neg=[]   upos=[]
          ('cond', 'user_missing_requirement', 'c1')   stars=[]   neg=[]   upos=[6]
          ('doc', 'access', 'd2')   stars=[]   neg=[]   upos=[17]
          ('role', 'role_user_met', 'r3')   stars=[['user', '...']]   neg=[]   upos=[11]
        starred residue on the INTERSECTION (authorized_user): NONE

(!) SCOPE. This probe measures REACHABILITY and the residue channel. It does NOT re-run
sec 10.5's 144 fault-injection arms and says nothing about what the settle pass or the
paranoia tiers catch -- that is still `TK74`'s assurance gap and is unchanged by putting
the fixture in the tree. What changes is that the shape now exists somewhere `pytest` can
find it.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r'C:/Users/user/PycharmProjects/graph-reachability-zanzibar-index')

from sqlmodel import select                                      # noqa: E402

from index_v4.models import NodeV4, ResidueV1                    # noqa: E402
from tests.parity import ParityEngine                            # noqa: E402
from zanzibar_utils_v1 import (                                  # noqa: E402
    Direct, Computed, TTU, Union, Intersection, Exclusion,
    PIntersection, parse_openfga_schema, parse_schema_ast,
)

FGA_DIR = Path(__file__).resolve().parents[2] / 'tests' / 'fga_schemas'

#: sec 10.5 (2026-09-18c) census, re-measured here rather than trusted. Used only as the
#: (I1) anti-vacuity floor -- the probe must still SEE these three.
SEC_10_5_INTERSECTIONS = {
    ('boolean_wildcards', ('doc', 'restricted')),
    ('demorgans_law_2', ('role', 'authorized_user')),
    ('tupleset_shapes', ('doc', 'approved_parent')),
}

NEW = 'star_admitting_intersection'
CONTROL = 'demorgans_law_2'


#: sec 10.5's own column, re-derived here. The probe asserts it reproduces these three
#: before reporting anything about the new fixture -- a walker that got `boolean_wildcards`
#: wrong would also get the new fixture wrong, and "the only one" is exactly the shape of
#: claim a broken walker produces.
SEC_10_5_STAR_COLUMN = {
    ('boolean_wildcards', ('doc', 'restricted')): True,
    ('demorgans_law_2', ('role', 'authorized_user')): False,
    ('tupleset_shapes', ('doc', 'approved_parent')): False,
}


class _TtuChild(Exception):
    """A TTU child would make the star column an UNDER-count, not a measurement."""


def _star_admitting(expr, otype, ast, tainted, seen=()):
    """True iff this LEAF child admits a `T:*` subject.

    "Leaf child" is the compiler's own unit -- `PClosureLeaf` is the maximal
    boolean-free, derived-free subtree -- so a `Computed` reference to an UNTAINTED
    relation is INLINED and its restrictions count, while a `Computed` to a tainted one
    is a derived dep and stops the walk. That distinction is the whole measurement:
    stars DO reach `demorgans_law_2`'s intersection through its derived dep and it still
    writes no residue, so a walker that followed the dep would report `True` for the
    control and prove nothing.
    """
    if isinstance(expr, Direct):
        return any(r.wildcard for r in expr.restrictions)
    if isinstance(expr, Computed):
        key = (otype, expr.relation)
        if key in tainted or key in seen or key not in ast:
            return False
        return _star_admitting(ast[key], otype, ast, tainted, seen + (key,))
    if isinstance(expr, (Union, Intersection)):
        return any(_star_admitting(c, otype, ast, tainted, seen) for c in expr.children)
    if isinstance(expr, Exclusion):
        return (_star_admitting(expr.base, otype, ast, tainted, seen)
                or _star_admitting(expr.subtract, otype, ast, tainted, seen))
    if isinstance(expr, TTU):
        raise _TtuChild(f'{otype}: TTU child {expr!r} -- the star column is not total here')
    return False


def census():
    """(A) -- every `.fga` in the corpus, every `PIntersection` plan."""
    rows = []
    seen_any = {}
    for path in sorted(FGA_DIR.glob('*.fga')):
        text = path.read_text(encoding='utf-8')
        try:
            ruleset = parse_openfga_schema(text)
        except Exception as e:                                   # noqa: BLE001
            rows.append((path.stem, None, None, None, None, f'{type(e).__name__}: {e}'))
            continue
        if ruleset.compiled is None:
            continue
        ast = parse_schema_ast(text)
        tainted = ruleset.compiled.tainted
        for key, plan in sorted(ruleset.compiled.plans.items()):
            if not isinstance(plan.tree, PIntersection):
                continue
            otype = key[0]
            expr = ast[key]
            children = expr.children if isinstance(expr, Intersection) else ()
            try:
                starred = any(_star_admitting(c, otype, ast, tainted) for c in children)
            except _TtuChild as e:
                rows.append((path.stem, key, plan.stratum, plan.deps, None, str(e)))
                continue
            seen_any[(path.stem, key)] = starred
            rows.append((path.stem, key, plan.stratum, plan.deps, starred, ''))
    return rows, seen_any


#: One workload, shape-identical on both fixtures. `role:r3 assigned user:*` is the only
#: tuple the control cannot take -- its `assigned` is `[user]` -- so it is applied
#: conditionally and the divergence in what is WRITABLE is itself reported.
WORKLOAD = [
    ('...', 'user', 'alice', 'has_attr', 'attr', 'at1'),
    ('...', 'attr', 'at1', 'requires', 'cond', 'c1'),
    ('...', 'user', '*', '_all_users', 'cond', 'c1'),
    ('...', 'cond', 'c1', 'match_any', 'role', 'r3'),
    ('...', 'role', 'r3', 'associated_role', 'doc', 'd2'),
]
STAR_GRANT = ('...', 'user', '*', 'assigned', 'role', 'r3')
CONCRETE_GRANT = ('...', 'user', 'alice', 'assigned', 'role', 'r3')


def residues(stem: str):
    """(B) -- drive the fixture and dump every `ResidueV1` row, joined to `NodeV4`.

    Joined, not a guessed subset: sec 9.5's G5 hypothesis was killed by dumping ALL rows.
    """
    eng = ParityEngine((FGA_DIR / f'{stem}.fga').read_text(encoding='utf-8'))
    try:
        assert eng.graph is not None, \
            f'(I2) {stem} did not join the graph index: {eng.graph_drop_reason}'
        took = []
        for raw in WORKLOAD:
            assert eng.add_tuple(*raw), f'{stem}: refused {raw}'
        for grant in (STAR_GRANT, CONCRETE_GRANT):
            try:
                ok = eng.add_tuple(*grant)
            except Exception as e:                               # noqa: BLE001
                took.append((grant[1] + ':' + grant[2], f'REFUSED {type(e).__name__}'))
                continue
            took.append((grant[1] + ':' + grant[2], 'taken' if ok else 'refused'))

        session = eng.graph.widx.idx.session
        store_id = eng.graph.widx.idx.store_id
        out = []
        for res, node in session.exec(
                select(ResidueV1, NodeV4)
                .where(ResidueV1.object_node_id == NodeV4.id)
                .where(ResidueV1.store_id == store_id)).all():
            out.append({
                'key': (node.type, res.relation, node.name),
                'stars': json.loads(res.stars),
                'neg': json.loads(res.neg),
                'upos': json.loads(res.upos),
            })
        out.sort(key=lambda r: r['key'])
        answers = {
            'access(alice, doc:d2)': eng.check('...', 'user', 'alice', 'access', 'doc', 'd2'),
            'authorized_user(alice, role:r3)': eng.check(
                '...', 'user', 'alice', 'authorized_user', 'role', 'r3'),
            'access(bob, doc:d2)': eng.check('...', 'user', 'bob', 'access', 'doc', 'd2'),
        }
        return took, out, answers
    finally:
        eng.close()


def main() -> int:
    rows, seen = census()
    print('=== (A) STRUCTURAL -- every PIntersection plan in tests/fga_schemas/ ===')
    print(f'{"fixture":34} {"key":34} {"str":>3}  {"star?":5} deps')
    hits = []
    for stem, key, stratum, deps, starred, err in rows:
        if err:
            print(f'{stem:34} {err}')
            continue
        print(f'{stem:34} {str(key):34} {stratum:>3}  {str(starred):5} {deps}')
        if deps and starred:
            hits.append((stem, key))

    missing = SEC_10_5_INTERSECTIONS - set(seen)
    assert not missing, (
        f'(I1) the census lost intersections sec 10.5 measured: {sorted(missing)}. '
        f'The walker is broken; nothing below is evidence.')
    disagree = {k: (seen[k], v) for k, v in SEC_10_5_STAR_COLUMN.items() if seen[k] != v}
    assert not disagree, (
        f'(I1) the star column disagrees with sec 10.5 (got, expected): {disagree}. '
        f'Either the walker is wrong or a pre-existing fixture changed -- reconcile '
        f'before reading the new row.')
    print()
    print(f'(I1) control -- the sec 10.5 star column reproduced on all '
          f'{len(SEC_10_5_STAR_COLUMN)} pre-existing intersections')
    print(f'(A) plans with BOTH a non-empty dep AND a star-admitting child: {hits}')

    for stem in (NEW, CONTROL):
        took, res, answers = residues(stem)
        print(f'\n=== (B) OPERATIONAL -- {stem}.fga ===')
        print(f'    grants: {took}')
        print(f'    answers: {answers}')
        print(f'    ResidueV1 rows (unit: residue rows): {len(res)}')
        for r in res:
            print(f'      {r["key"]}   stars={r["stars"]}   neg={r["neg"]}   '
                  f'upos={r["upos"]}')
        starred_isect = [r for r in res
                         if r['key'][1] == 'authorized_user' and r['stars']]
        print(f'    starred residue on the INTERSECTION (authorized_user): '
              f'{starred_isect if starred_isect else "NONE"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
