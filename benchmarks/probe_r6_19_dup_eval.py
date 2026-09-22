"""R6-19 step (1): instrument the duplicate-evaluation rate (2026-09-22b).

The row's own decision rule: "instrument the duplicate-evaluation rate -- if it
is near zero on real corpora the item is finished, DECLINED". Its trap adds the
soundness half: "check_fn closures read live bf state, and both _reconcile and
_reconcile_subject_edge WRITE residues between the two evaluation points, so a
(subject) -> bool memo needs an argument that no interleaved write can change
the answer".

So this probe measures BOTH halves at once, which is what makes it decisive:

  (a) the duplicate rate -- how many plan.check_fn evaluations repeat a
      (plan, key) pair a memo would have hit;
  (b) whether any repeated pair ever CHANGES ITS ANSWER within one build.

(b) is the interleaved-write question, asked empirically. A duplicate that
flips is a memo that would have returned a stale answer -- direct evidence
against step (3), not merely an absent argument for it.

Run ALONE. Read-only with respect to the tree; wraps check_fn via the compiled
plan objects only.
"""
import sys
from collections import Counter, defaultdict

sys.path.insert(0, '.')

from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from benchmarks.scale_bench import WORKLOADS  # noqa: E402
from connectedstore import build_index  # noqa: E402
from connectedstore import save_schema  # noqa: E402
from setengine.models import TupleV1  # noqa: E402

CALLS = Counter()            # (plan_id, key) -> times evaluated
ANSWERS = defaultdict(set)   # (plan_id, key) -> set of answers seen
TOTAL = [0]
# The decisive split: a duplicate INSIDE one _reconcile call is memoizable work;
# a duplicate ACROSS _reconcile calls is the fixpoint legitimately re-asking as
# state advances, and no memo may serve it.
RECONCILE = [0]
IN_RECONCILE = [False]       # are we lexically inside a _reconcile invocation?
LOOSE = [0]                  # unique scope ids for evaluations outside one
IN_SCOPE = Counter()         # (scope_id, plan_id, key) -> times


def _instrument(plans):
    """Wrap every compiled plan's check_fn with a counting shim."""
    n = 0
    for plan in plans:
        orig = plan.check_fn
        if getattr(orig, '_r619_wrapped', False):
            continue

        def make(orig_fn, pid):
            def shim(ctx, key):
                out = orig_fn(ctx, key)
                TOTAL[0] += 1
                CALLS[(pid, key)] += 1
                # CONSERVATIVE SCOPING: _reconcile_subject_edge is ALSO called
                # from the edge-apply path (bulk_backfill.py:801), outside any
                # _reconcile. Bucketing those with the previous _reconcile would
                # invent memoizable duplicates. Give each such evaluation its own
                # scope id so it can never pair with anything.
                if IN_RECONCILE[0]:
                    scope = ('rec', RECONCILE[0])
                else:
                    LOOSE[0] += 1
                    scope = ('loose', LOOSE[0])
                IN_SCOPE[(scope, pid, key)] += 1
                ANSWERS[(pid, key)].add(bool(out))
                return out
            shim._r619_wrapped = True
            return shim

        try:
            plan.check_fn = make(orig, id(plan))
            n += 1
        except Exception as exc:
            print(f'  could not wrap plan {id(plan)}: {exc}')
    return n


def _collect_plans(compiled):
    out = []
    for attr in ('plans', 'plan_by_key', 'by_key'):
        v = getattr(compiled, attr, None)
        if isinstance(v, dict):
            out.extend(v.values())
        elif isinstance(v, (list, tuple)):
            out.extend(v)
    return [p for p in out if hasattr(p, 'check_fn')]


def main(workload='demorgans', scale=40):
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    spec = WORKLOADS[workload]
    schema, shapes = spec['schema'], spec['shapes']
    save_schema(session, f'{workload}_src', schema, shapes)
    seen = set()
    rows = []
    for t in spec['gen'](scale):
        if t in seen:
            continue
        seen.add(t)
        rows.append(TupleV1(store_id=f'{workload}_src', subject_predicate=t[0],
                            subject_type=t[1], subject_name=t[2], relation=t[3],
                            object_type=t[4], object_name=t[5]))
    session.add_all(rows)
    session.commit()
    print(f'workload={workload} scale={scale}: {len(rows):,} raw tuples seeded')

    # Instrument every compiled plan as the backfill object is constructed --
    # that is the only place the CompiledBooleans artifact is reachable.
    import index_v4.bulk_backfill as bb
    orig_init = bb._BulkBackfill.__init__

    orig_rec = bb._BulkBackfill._reconcile

    def patched_reconcile(self, o_type, rel, o_name):
        RECONCILE[0] += 1
        prev = IN_RECONCILE[0]
        IN_RECONCILE[0] = True
        try:
            return orig_rec(self, o_type, rel, o_name)
        finally:
            IN_RECONCILE[0] = prev

    bb._BulkBackfill._reconcile = patched_reconcile

    def patched_init(self, m, nodes, schema_info, compiled):
        orig_init(self, m, nodes, schema_info, compiled)
        plans = list(compiled.plans.values())
        print(f'  instrumented {_instrument(plans)} of {len(plans)} compiled plan(s)')

    bb._BulkBackfill.__init__ = patched_init
    try:
        build_index(session, f'{workload}_src', f'{workload}_gidx', bulk=True)
    finally:
        bb._BulkBackfill.__init__ = orig_init
        bb._BulkBackfill._reconcile = orig_rec

    total = TOTAL[0]
    distinct = len(CALLS)
    if total == 0:
        print('\nZERO check_fn evaluations observed -- the wrap did not take '
              'effect. PROBE INVALID, do not quote it.')
        return 2

    repeats = total - distinct
    flipped = [k for k, v in ANSWERS.items() if len(v) > 1]
    multi = [k for k, v in CALLS.items() if v > 1]

    print(f'\ntotal plan.check_fn evaluations : {total:,}')
    print(f'distinct (plan, key) pairs      : {distinct:,}')
    print(f'redundant evaluations           : {repeats:,} '
          f'({repeats / total * 100:.1f}% of all evaluations)')
    print(f'pairs evaluated more than once  : {len(multi):,}')
    if multi:
        worst = sorted(CALLS.items(), key=lambda kv: -kv[1])[:5]
        print('  worst offenders (evaluations of one pair):')
        for (pid, key), n in worst:
            print(f'    {n:5,}x  {key}')
    print(f'\npairs whose ANSWER CHANGED between evaluations: {len(flipped):,}')
    if flipped:
        print('  -> a (subject)->bool memo would have served a STALE answer; '
              'step (3) is refuted empirically, not merely unargued.')
        for k in flipped[:5]:
            print(f'    {k[1]}  answers={sorted(ANSWERS[k])}')
    else:
        print('  -> no observed flip on this corpus (absence of evidence; the '
              'interleaved-write argument is still not made)')

    intra = sum(v - 1 for v in IN_SCOPE.values() if v > 1)
    print('')
    print('--- the split that decides the item ---')
    print(f'_reconcile calls observed        : {RECONCILE[0]:,}')
    print(f'evaluations OUTSIDE a _reconcile : {LOOSE[0]:,} '
          f'({LOOSE[0] / total * 100:.1f}%)  <- each scoped alone, never memoizable')
    print(f'redundant WITHIN one _reconcile  : {intra:,} '
          f'({intra / total * 100:.1f}% of all evaluations)  <- memoizable')
    print(f'redundant ACROSS _reconcile calls: {repeats - intra:,} '
          f'({(repeats - intra) / total * 100:.1f}%)  <- fixpoint re-asking, NOT memoizable')

    ceiling = intra / total * 100 if total else 0.0
    print('')
    print('VERDICT INPUT: a SOUND (intra-reconcile) memo removes at '
          f'most {ceiling:.1f}% of check_fn evaluations.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
