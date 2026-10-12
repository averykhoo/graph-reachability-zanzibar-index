"""TK118 cost probe: what the delta-scoped I14 adds to ``ZANZIBAR_PARANOIA=residue``.

Interleaved A/B (arms alternate inside each round, min-of-ROUNDS), per-write commits
through the real ``ConnectedStore`` sync path -- the method the 2026-07-26 residue
measurement used (``tests/test_paranoia_wiring.py`` docstring). Arms:

  off           no paranoia
  residue-pre   residue WITHOUT the TK118 I14 (listener + check patched to no-ops)
  residue       residue as shipped (I6 hygiene + delta-scoped I14)

Fixtures:
  plain  ``tests/fga_schemas/boolean_wildcards.fga`` -- no crossable shape, so the I14
         cost should be noise (the listener returns at once, the check never queries)
  owc    ``tests/fga_schemas/owc_star_ttu.fga`` with object wildcards on
         ``(folder, viewer)`` / ``(doc, viewer)`` -- crossable, so every write that touches
         a folder/doc entity runs the check

Run: ``python benchmarks/probe_tk118_residue_i14.py [N ...]`` (default 160 480).
Results: ``docs/tk118-residue-i14-2026-10-12.md`` § 3.
"""
import sys
import time
import warnings
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from zanzibar.connectedstore import ConnectedStore
from zanzibar.graphindex import invariants

ROUNDS = 3
FGA = Path(__file__).resolve().parent.parent / 'tests' / 'fga_schemas'
OWC_SHAPES = frozenset({('folder', 'viewer'), ('doc', 'viewer')})


def plain_writes(n):
    out = [('...', 'user', '*', 'public', 'doc', 'd0')]
    i = 0
    while len(out) < n:
        rel = ('editor', 'blocked', 'editor')[i % 3]
        out.append(('...', 'user', f'u{i % 17}', rel, 'doc', f'd{i // 3}'))
        i += 1
    return out[:n]


def owc_writes(n):
    out = [('...', 'user', 'u0', 'viewer', 'folder', '*'),
           ('...', 'folder', '*', 'parent', 'doc', 'd0')]
    i = 0
    while len(out) < n:
        kind = i % 4
        if kind == 0:
            out.append(('...', 'user', f'u{i % 13}', 'editor', 'folder', f'f{i // 4}'))
        elif kind == 1:
            out.append(('...', 'user', f'u{i % 11}', 'blocked', 'folder', f'f{i // 4}'))
        elif kind == 2:
            out.append(('...', 'user', f'u{i % 7}', 'editor', 'doc', f'd{i // 4}'))
        else:
            out.append(('...', 'folder', f'f{i // 4}', 'parent', 'doc', f'd{i // 4}'))
        i += 1
    return out[:n]


FIXTURES = {
    'plain': ((FGA / 'boolean_wildcards.fga').read_text(), frozenset(), plain_writes),
    'owc': ((FGA / 'owc_star_ttu.fga').read_text(), OWC_SHAPES, owc_writes),
}


def run_arm(arm, schema, owc, writes):
    real_check, real_note = invariants.check_i14_delta, invariants.ParanoiaGuard.note_flush
    if arm == 'residue-pre':
        invariants.check_i14_delta = lambda *a, **k: None
        invariants.ParanoiaGuard.note_flush = lambda self, sess: None
    try:
        engine = create_engine('sqlite:///:memory:')
        SQLModel.metadata.create_all(engine)
        with Session(engine) as s:
            cs = ConnectedStore(s, 'bench', schema=schema, object_wildcard_shapes=owc,
                                paranoia='off' if arm == 'off' else 'residue')
            t0 = time.perf_counter()
            for w in writes:
                cs.add_tuple(*w)
            return time.perf_counter() - t0
    finally:
        invariants.check_i14_delta, invariants.ParanoiaGuard.note_flush = real_check, real_note


def main(sizes):
    warnings.simplefilter('ignore')
    arms = ('off', 'residue-pre', 'residue')
    for name, (schema, owc, gen) in FIXTURES.items():
        for n in sizes:
            writes = gen(n)
            best = {a: float('inf') for a in arms}
            for _ in range(ROUNDS):
                for a in arms:
                    best[a] = min(best[a], run_arm(a, schema, owc, writes))
            off, pre, new = best['off'], best['residue-pre'], best['residue']
            print(f'{name:5} {n:4} writes: off {off:7.3f}s | residue-pre {pre:7.3f}s '
                  f'({(pre / off - 1) * 100:+5.1f}%) | residue {new:7.3f}s '
                  f'({(new / off - 1) * 100:+5.1f}%) | I14 share {(new / pre - 1) * 100:+5.1f}%',
                  flush=True)


if __name__ == '__main__':
    main([int(a) for a in sys.argv[1:]] or [160, 480])
