"""`TK89` -- is `formal/probes/tk77_crossable_census_2026-09-19.py` REPRODUCIBLE?

WHY. The census is the acceptance instrument `TK77` and `TK87` were both closed on, and it
booked two different values for one column on one tree from one command: `parse_crossable`
**17** (`TK77`, 2026-09-19e) and **18** (`TK87`, 2026-09-19f,
`docs/tk87-swarm-churn-2026-09-19.md` §1, recorded deliberately unreconciled). The
neighbouring columns matched exactly (`_ensure/EFF` **46**, `CTL` **110**), so this is one
column moving by one, not a wholesale instrument failure.

The deliverable is NOT "the number is 17" or "the number is 18". It is that the census says
which, and why it can be trusted. `CLAUDE.md` already forbids differencing against a
recorded count; an instrument that drifts by one makes any future small delta meaningless.

WHAT THIS RUNS. The recorded command, N times per arm, as separate subprocesses, parsing
the census table out of each run's stdout:

    python formal/probes/tk77_crossable_census_2026-09-19.py --pytest \\
        tests/test_generator_coverage.py -q -p no:cacheprovider -s

  ARM `hash-random` -- `PYTHONHASHSEED` left unset, i.e. exactly how a human runs it.
  ARM `hash-fixed`  -- `PYTHONHASHSEED=0`.

The two arms are the experiment, not decoration. `PYTHONHASHSEED` is unset in this repo
(no `pytest.ini`/`pyproject` setting, READ 2026-09-20g), so every run randomises `set` and
`frozenset` iteration order. If the column is stable under `hash-fixed` and moves under
`hash-random`, hash randomisation is the mechanism and the fix is to pin it for census runs.

★ WHAT IS COMPARED, and why it is not just the module row. `TK89`'s own discriminator:

  * **TOTAL and the `<setup>` row**, not only the module row. A parse booked to a different
    row moves the module number while TOTAL holds still; an EXTRA parse moves both. That
    single comparison separates the task row's candidate (2) from its candidate (1).
  * **the `crossable shape-sets seen at parse` lines**, which name WHICH shape-set gained
    or lost an occurrence. A `parse_crossable` that moves by one with the shape-set list
    unchanged is a different animal from one where a shape-set appears.

(!) CANDIDATE (1) IS ALREADY REFUTED, by a code read rather than by this probe, and it was
the task row's *leading* candidate. READ 2026-09-20g: the only `@given` tests in
`tests/test_generator_coverage.py` are the two nested in
`::test_swarm_campaign_reaches_cells_and_never_starves_a_switch` (`:685`, `:691`), and both
carry `::_SWARM_SETTINGS` (`:594`), which sets **`database=None`** and **`derandomize=True`**
and restricts `phases` to `Phase.generate`. The hypothesis example database is therefore not
consulted by them at all, so `.hypothesis/` state cannot add a replayed execution here and
`-p no:cacheprovider` not covering hypothesis's cache is beside the point. Recorded because
the row names candidate (1) as leading and a future reader should not re-derive it.

(!) INSTRUMENT CONTROLS.

  * The census's own dead-instrument control (`CTL`) is quoted per run. It was **110** in
    both historical runs; a run where it is 0 prints `INSTRUMENT DEAD` and its numbers are
    not a null result, they are nothing.
  * A parse failure of this probe's own table reader is reported as `PARSE-FAIL`, never as
    a zero row -- a reader that silently yields zeros would report perfect stability.
  * The pytest summary line is captured per run, so a run that FAILED tests cannot be read
    as a clean census (`CLAUDE.md`'s standing exit-code footgun).

USAGE
  python formal/probes/tk89_census_reproducibility_2026-09-20.py [--runs N]

THE VERDICT -- see the RAN block appended at the bottom of this file after the run.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PY = sys.executable
_CENSUS = 'formal/probes/tk77_crossable_census_2026-09-19.py'

_COLS = ('parse_total', 'parse_crossable', '_ensure/raw', '_ensure/EFF',
         '_sync/raw', '_sync/EFF', 'CTL')
_HDR = '=== TK77 EFFECTIVE MIDDLES CENSUS (attributed) ==='


def parse_table(out: str):
    """``({row_label: {col: int}}, [shape-set lines], summary)`` or ``None`` on a miss."""
    if _HDR not in out:
        return None
    body = out.split(_HDR, 1)[1]
    rows, shapes = {}, []
    for line in body.splitlines():
        if line.strip().startswith('crossable shape-sets'):
            continue
        m = re.match(r'^(\S.*?)\s{2,}((?:\s*-?\d+){7})\s*$', line)
        if m:
            label = m.group(1).strip()
            nums = [int(x) for x in m.group(2).split()]
            if label != 'module':
                rows[label] = dict(zip(_COLS, nums))
            continue
        if re.match(r'^\s{4}\S+\s+\[', line):
            shapes.append(line.strip())
    summary = next((ln.strip() for ln in out.splitlines()[::-1]
                    if ' passed' in ln or ' failed' in ln or ' error' in ln), '?')
    return (rows, shapes, summary) if rows else None


def one_run(seed: str | None):
    env = dict(os.environ)
    if seed is None:
        env.pop('PYTHONHASHSEED', None)
    else:
        env['PYTHONHASHSEED'] = seed
    p = subprocess.run(
        [_PY, _CENSUS, '--pytest', 'tests/test_generator_coverage.py',
         '-q', '-p', 'no:cacheprovider', '-s'],
        cwd=_REPO_ROOT, capture_output=True, text=True, env=env)
    return p.returncode, parse_table(p.stdout + p.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=int, default=2)
    args = ap.parse_args()

    verdicts = {}
    for arm, seed in (('hash-random', None), ('hash-fixed', '0')):
        print(f'\n===== ARM {arm} (PYTHONHASHSEED={seed or "unset"}) =====')
        observed = []
        for i in range(args.runs):
            rc, table = one_run(seed)
            if table is None:
                print(f'  run {i}: PARSE-FAIL rc={rc} -- the table reader found no census. '
                      f'This is an instrument failure, NOT a zero.')
                observed.append(None)
                continue
            rows, shapes, summary = table
            total = rows.get('TOTAL', {})
            setup = rows.get('<setup>', {})
            mod = rows.get('tests/test_generator_coverage.py', {})
            print(f'  run {i}: rc={rc}  {summary}')
            print(f'    TOTAL            ' +
                  '  '.join(f'{c}={total.get(c)}' for c in _COLS))
            print(f'    <setup>          ' +
                  '  '.join(f'{c}={setup.get(c)}' for c in _COLS))
            print(f'    module row       ' +
                  '  '.join(f'{c}={mod.get(c)}' for c in _COLS))
            if not total.get('CTL'):
                print('    (!) CTL is 0 -- INSTRUMENT DEAD, these numbers are nothing')
            for s in shapes:
                print(f'    shapes: {s}')
            observed.append((rows, shapes, summary))

        good = [o for o in observed if o]
        if len(good) < 2:
            print(f'  VERDICT {arm}: INCONCLUSIVE -- fewer than 2 parsable runs')
            verdicts[arm] = 'INCONCLUSIVE'
            continue
        base_rows = good[0][0]
        drift = {}
        for rows, _s, _u in good[1:]:
            for label in sorted(set(base_rows) | set(rows)):
                for col in _COLS:
                    a = base_rows.get(label, {}).get(col)
                    b = rows.get(label, {}).get(col)
                    if a != b:
                        drift.setdefault((label, col), []).append((a, b))
        shape_drift = any(g[1] != good[0][1] for g in good[1:])
        if drift:
            print(f'  VERDICT {arm}: DRIFTS')
            for (label, col), obs in sorted(drift.items()):
                print(f'    {label:40} {col:16} {obs}')
        else:
            print(f'  VERDICT {arm}: STABLE across {len(good)} runs (every row, every column)')
        print(f'    crossable shape-set lines differ between runs: {shape_drift}')
        verdicts[arm] = 'DRIFTS' if drift else 'STABLE'

    print(f'\n===== SUMMARY: {verdicts} =====')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
