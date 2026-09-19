"""TK77 mutation sweep over the GENERATOR-reach additions of 2026-09-19e.

Sibling of `formal/probes/tk77_middles_reach_sweep_2026-09-19.py` (which sweeps the
2026-09-19d fixture arms). This one sweeps what section 7 items (2) and (3) landed:

  * `tests/genswarm.py::witness` -- the object wildcard on the TTU TARGET, pinned by
    `tests/test_generator_coverage.py::test_driven_config_space_reaches_a_crossable_schema`;
  * `tests/test_hypothesis.py::test_star_bridge_crossing_middle_remove_deterministic_pin`
    -- the REMOVE side of I14, the acceptance target of census section 7.4;
  * `tests/test_hypothesis.py::star_bridge_configs`' crossability re-weighting, which is a
    DISTRIBUTION change and is expected to sweep INERT (see `N6`).

Run from the repo root:

    python formal/probes/tk77_generator_reach_sweep_2026-09-19.py

Each mutation is a narrowest-plausible weakening of something the new pins claim; it is
applied to the working tree, the affected tests are run, and the file is restored from a
byte copy in `finally`. **It edits tracked files in place** -- do not run it on a dirty
tree you care about, and check `git status` afterwards.

`N0` is the HARNESS CONTROL (`docs/sabotage-procedure.md`): it inverts the new pin's own
final claim, so a sweep that reports `N0` INERT is a broken harness and not a clean module.

⚠ ANCHOR ENDINGS ARE HANDLED, DELIBERATELY. The 2026-09-19d sweep shipped an ANCHOR-MISS
because a multi-line anchor was written with `\\n` against a CRLF file -- and an
ANCHOR-MISS measures nothing while printing in the same column as a CAUGHT row. This tree
is MIXED (`tests/genswarm.py` is LF, `tests/test_hypothesis.py` and
`tests/test_generator_coverage.py` are CRLF), so anchors here are written with `\\n` and
translated to each file's own dominant ending by `_fit`. A `0 matches` row is still
reported as ANCHOR-MISS rather than counted.
"""
import io
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PY = r'C:/Users/user/anaconda3/envs/graph-reachability-zanzibar-index/python.exe'
ROOT = Path('.').resolve()
HYP = 'tests/test_hypothesis.py'
GCOV = 'tests/test_generator_coverage.py'
GSW = 'tests/genswarm.py'
PROP = 'tests/test_wildcard_property.py'
WC = 'index_v4/wildcard.py'
TARGETS = [HYP, GCOV, GSW, WC]          # PROP is run, never mutated, by this sweep

SELECT = 'star_bridge or crossable_schema or silently_dropped or middle_sync'

# `middle_sync` (and `PROP` below) are in the selection because of `N5`. On the first
# run the selection was the three new-arm patterns only, and `N5` -- a PRODUCT mutation
# that drops `remove_edge`'s OBJECT-endpoint middle sync -- came back INERT. It is not:
# `tests/test_wildcard_property.py::test_middle_sync_record_excludes_the_wildcard_entity`
# (a 2026-09-19d arm) reddens on it, while `tests/test_i14_crossing_middles.py` -- the
# module named after the invariant -- stays GREEN. A sweep whose selection cannot see
# the test that catches a mutation reports a hole that is not there, which is the
# mirror image of the failure mode these sweeps exist to find.

# (id, file, old, new, what it is supposed to move)
MUTATIONS = [
    ('N0', HYP,
     "    assert effective, (\n",
     "    assert not effective, (\n",
     'HARNESS CONTROL: invert the remove pin\'s own final claim'),
    ('N1', GSW,
     "            owc.add(('doc', 'r1'))\n",
     "            pass\n",
     'revert to the pre-2026-09-19e owc (tupleset shape only)'),
    ('N2', GSW,
     "        if 'body_boolean' not in sw and 'body_wc_userset' not in sw:\n",
     "        if True:\n",
     'drop the two-switch guard -- the "why is this conditional?" tidy'),
    ('N3', HYP,
     "    owc = frozenset({(T, 'parent')})\n"
     "    schema = _star_bridge_schema(T, A, A)\n"
     "    crossable = parse_openfga_schema(\n",
     "    owc = frozenset()\n"
     "    schema = _star_bridge_schema(T, A, A)\n"
     "    crossable = parse_openfga_schema(\n",
     'make the pin\'s own config NON-crossable (the silent-no-op trap)'),
    ('N4', HYP,
     "        for raw in reversed(accepted):\n",
     "        for raw in reversed(accepted[:0]):\n",
     'pin adds but never removes -> the remove side is never driven'),
    ('N5', WC,
     "        self._sync_entity_middles(s_type, s_name)\n"
     "        self._sync_entity_middles(o_type, o_name)\n",
     "        self._sync_entity_middles(s_type, s_name)\n",
     'PRODUCT: remove_edge stops syncing the OBJECT endpoint\'s middles'),
    ('N6', HYP,
     "    B = A if draw(st.booleans()) else draw(st.sampled_from(_SB_RELS))\n",
     "    B = draw(st.sampled_from(_SB_RELS))\n",
     'revert half the re-weighting (expected INERT -- a distribution is not a claim)'),
]


def _fit(text: str, path: str) -> str:
    """Translate an `\\n`-written anchor to `path`'s own dominant line ending."""
    raw = Path(path).read_bytes()
    return text.replace('\n', '\r\n') if raw.count(b'\r\n') > raw.count(b'\n') // 2 else text


def run() -> tuple[int, str]:
    log = Path(tempfile.mkstemp(suffix='.log')[1])
    cmd = [PY, '-m', 'pytest', HYP, GCOV, PROP, '-q', '-p', 'no:cacheprovider',
           '-k', SELECT, '--no-header', '--tb=no']
    with io.open(log, 'w', encoding='utf-8', errors='replace') as fh:
        rc = subprocess.call(cmd, cwd=str(ROOT), stdout=fh, stderr=subprocess.STDOUT)
    return rc, io.open(log, encoding='utf-8', errors='replace').read()


def failed_ids(out: str) -> list[str]:
    return sorted(set(re.findall(r'^(?:FAILED|ERROR) (\S+)', out, re.M)))


def main() -> int:
    backup = Path(tempfile.mkdtemp())
    for t in TARGETS:
        (backup / Path(t).name).write_bytes(Path(t).read_bytes())

    rc, out = run()
    base_ids = failed_ids(out)
    tail = [l for l in out.strip().splitlines() if l.strip()][-1]
    print(f'BASELINE  rc={rc}  failed={base_ids}  | {tail}')
    if rc != 0:
        print('REFUSING: baseline is not green, attribution would be meaningless')
        return 2

    rows = []
    for (mid, path, old, new, what) in MUTATIONS:
        old_f, new_f = _fit(old, path), _fit(new, path)
        src = io.open(path, encoding='utf-8', newline='').read()
        n = src.count(old_f)
        if n != 1:
            rows.append((mid, 'ANCHOR-MISS', f'{n} matches', what))
            print(f'{mid:4} ANCHOR-MISS ({n} matches) -- {what}')
            continue
        io.open(path, 'w', encoding='utf-8', newline='').write(src.replace(old_f, new_f))
        try:
            rc, out = run()
            ids = [i for i in failed_ids(out) if i not in base_ids]
            tail = [l for l in out.strip().splitlines() if l.strip()][-1]
            verdict = 'CAUGHT' if rc != 0 else 'INERT'
            rows.append((mid, verdict, ','.join(ids) or '-', what))
            print(f'{mid:4} {verdict:6} rc={rc} {tail}')
            for i in ids:
                print(f'       red: {i}')
        finally:
            Path(path).write_bytes((backup / Path(path).name).read_bytes())

    print('\n=== TK77 GENERATOR-REACH SWEEP SUMMARY (2026-09-19e) ===')
    for (mid, verdict, ids, what) in rows:
        print(f'{mid:4} {verdict:11} {what}')
        print(f'     {ids}')
    shutil.rmtree(backup, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
