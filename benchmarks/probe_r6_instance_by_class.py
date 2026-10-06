"""R6-4 vs R6-5 attribution, decisively (2026-09-22).

probe_instance_callers.py reproduced the 22,410 `_instance` constructions but
could not split them: cProfile records only the IMMEDIATE caller, which is
sqlalchemy `loading.py:208(chunks)` for all of them.

SQLAlchemy fires an InstanceEvents.load per ORM instance materialised, per
mapped class. That answers the actual question -- how many of the 22,410 are
Residue rows (R6-4's full scan) versus Node/Edge rows (R6-5's surface) --
without touching the code under measurement.

Run ALONE. Deterministic: same scale/calls as R6_PROFILE_2026-08-17.md's
graph-lookup pass (scale 40, 60 calls, demorgans_law_2).
"""
import sys
from collections import Counter

sys.path.insert(0, '.')

from sqlalchemy import event  # noqa: E402

from benchmarks import scale_bench as sb  # noqa: E402
from benchmarks._harness import build_graph  # noqa: E402

SCALE = 40
CALLS = 60

LOADED = Counter()


def _install_counters():
    """Register a per-class load counter on every mapped model we ship."""
    import zanzibar.graphindex.models as m4
    from sqlmodel import SQLModel

    # DEDUPE BY CLASS IDENTITY. zanzibar.graphindex.models exposes several mapped classes
    # under two names, so a dir()-driven list registers TWO load listeners on
    # Node/Edge/Store and silently doubles their counts. The first run of
    # this probe did exactly that and reported 38,820 constructions against the
    # profile's 22,410 -- the instrument, not the subject, was wrong.
    seen = set()
    classes = []
    for name in dir(m4):
        obj = getattr(m4, name)
        if (isinstance(obj, type) and issubclass(obj, SQLModel)
                and obj is not SQLModel and hasattr(obj, '__tablename__')
                and id(obj) not in seen):
            seen.add(id(obj))
            classes.append(obj)

    for cls in classes:
        def _mk(cname):
            def _on_load(target, context):
                LOADED[cname] += 1
            return _on_load
        try:
            event.listen(cls, 'load', _mk(cls.__name__), propagate=True)
        except Exception as exc:                      # pragma: no cover
            print(f'  could not listen on {cls.__name__}: {exc}')
    return [c.__name__ for c in classes]


def main():
    watched = _install_counters()
    print(f'listening for ORM loads on {len(watched)} mapped classes: '
          f'{", ".join(sorted(watched))}')

    spec = sb.WORKLOADS['demorgans']
    widx, ntup = build_graph(spec['schema'], spec['shapes'], spec['gen'](SCALE))
    subs = spec['lookups'](SCALE, CALLS)

    from zanzibar.graphindex.models import Residue
    from sqlmodel import select
    nres = len(widx.idx.session.exec(select(Residue).where(
        Residue.store_id == widx.idx.store_id)).all())

    LOADED.clear()          # discard build-phase loads; measure the lookups only
    n = 0
    for (sp, st, sn) in subs:
        n += sb._rsz(widx.lookup(sp, st, sn))

    total = sum(LOADED.values())
    print(f'\ndataset: {ntup:,} raw tuples, {nres:,} residue rows, '
          f'{CALLS} lookups, scale={SCALE}')
    print(f'results returned: {n:,}')
    print(f'\nORM instances materialised during the {CALLS} lookups: {total:,}')
    print('\nby mapped class:')
    for name, cnt in LOADED.most_common():
        share = cnt / total * 100 if total else 0.0
        owner = {'Residue': 'R6-4', 'ResidueRef': 'R6-4',
                 'Node': 'R6-5', 'Edge': 'R6-5'}.get(name, '?')
        print(f'  {cnt:8,}  ({share:5.1f}%)  {name:16} <- {owner}')

    r64 = LOADED['Residue'] + LOADED['ResidueRef']
    r65 = LOADED['Node'] + LOADED['Edge']
    print(f'\nR6-4 (residue rows)     : {r64:,}  '
          f'({r64 / total * 100:.1f}% of ORM constructions)')
    print(f'R6-5 (node/edge rows)   : {r65:,}  '
          f'({r65 / total * 100:.1f}% of ORM constructions)')
    print(f'unattributed            : {total - r64 - r65:,}')
    print(f'\nper lookup: {total / CALLS:,.1f} ORM instances '
          f'({r64 / CALLS:,.1f} residue + {r65 / CALLS:,.1f} node/edge)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
