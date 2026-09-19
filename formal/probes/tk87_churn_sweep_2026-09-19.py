"""TK87 mutation sweep over the CHURN-PASS additions of 2026-09-19f.

Sibling of `formal/probes/tk77_generator_reach_sweep_2026-09-19.py`, same harness shape.
What it sweeps:

  * `tests/genswarm.py::Diff.remove` / `::Diff.restored` / `::Diff.grid`'s `extra_names`
    and `::drive_config`'s churn pass -- the capability;
  * the three pins in `tests/test_generator_coverage.py` section 6b;
  * one PRODUCT arm in `index_v4/wildcard.py`, because a capability that no product
    mutation can move is a capability that reaches nothing.

Run from the repo root:

    python formal/probes/tk87_churn_sweep_2026-09-19.py

Each mutation is a narrowest-plausible weakening; it is applied to the working tree, the
selected tests are run, and the file is restored from a byte copy in `finally`. **It
edits tracked files in place** -- do not run it on a dirty tree you care about, and check
`git status` afterwards.

`M0` is the HARNESS CONTROL (`docs/sabotage-procedure.md`): it inverts a new pin's own
final claim, so a sweep that reports `M0` INERT is a broken harness, not a clean module.

SELECTION. `tests/test_wildcard_property.py` is RUN and never mutated: TK77's `N5` came
back INERT on its first run purely because the catching test was outside the selection,
and the lesson is that a sweep whose selection cannot see the catching test reports a
hole that does not exist. `M6` is the same product mutation, included here to keep that
attribution visible from this sweep too.

LINE ENDINGS. All three mutated files are CRLF on disk under `core.autocrlf=true`;
anchors are written with `\\n` and translated by `_fit`, and a `0 matches` row is
reported as ANCHOR-MISS rather than counted as a result.
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
GCOV = 'tests/test_generator_coverage.py'
GSW = 'tests/genswarm.py'
PROP = 'tests/test_wildcard_property.py'
WC = 'index_v4/wildcard.py'
TARGETS = [GCOV, GSW, WC]               # PROP is run, never mutated

SELECT = 'churn or removal_grid or middle_sync or crossable_schema or empty_pool'

# (id, file, old, new, what it is supposed to move)
MUTATIONS = [
    ('M0', GCOV,
     "    assert eff, (\n",
     "    assert not eff, (\n",
     'HARNESS CONTROL: invert the reach pin\'s own final claim'),
    ('M1', GSW,
     "        return grid_for(self.ast, self.present, cap=self.grid_cap, rng=self._rng,\n"
     "                        extra_names=self._names)\n",
     "        return grid_for(self.ast, self.present, cap=self.grid_cap, rng=self._rng)\n",
     'the pre-TK87 grid: the universe shrinks the moment a tuple is removed'),
    ('M2', GSW,
     "                half = len(admitted) // 2\n",
     "                half = len(admitted)\n",
     'remove EVERYTHING before the removal sweep (the cheap churn pass)'),
    ('M3', GSW,
     "                assert d.present, 'the churn pass emptied the store before its sweep'\n"
     "                n, bad = d.sweep()\n",
     "                for raw in reversed(admitted[:-half]):\n"
     "                    if d.remove(raw):\n"
     "                        res.removed += 1\n"
     "                n, bad = d.sweep()\n",
     'sweep ONLY at the end -- the restored store compares empty and reports success'),
    ('M4', GSW,
     "        if decision:\n"
     "            self.present.discard(raw)\n"
     "        return decision\n",
     "        return decision\n",
     '`remove` stops updating `present`: the oracle keeps the removed tuple'),
    ('M5', WC,
     "    def _sync_entity_middles(self, entity_type: str, name: str) -> None:\n",
     "    def _sync_entity_middles(self, entity_type: str, name: str) -> None:\n"
     "        return\n",
     'PRODUCT: the I14 remove-side GC does nothing at all'),
    ('M6', WC,
     "        self._sync_entity_middles(s_type, s_name)\n"
     "        self._sync_entity_middles(o_type, o_name)\n",
     "        self._sync_entity_middles(s_type, s_name)\n",
     'PRODUCT: remove_edge stops syncing the OBJECT endpoint (TK77 N5)'),
    ('M7', GSW,
     "                res.remove_comparisons += n\n",
     "                pass\n",
     'the removal half stops counting its own comparisons'),
    ('M8', GSW,
     "                    if t not in admitted:      # a duplicate add no-ops; removing it\n"
     "                        admitted.append(t)     # twice would count a phantom removal\n",
     "                    admitted.append(t)\n",
     'drop the dedupe (expected INERT: `removed` is a report, not a claim)'),
]


def _fit(text: str, path: str) -> str:
    """Translate an `\\n`-written anchor to `path`'s own dominant line ending."""
    raw = Path(path).read_bytes()
    return text.replace('\n', '\r\n') if raw.count(b'\r\n') > raw.count(b'\n') // 2 else text


def run() -> tuple[int, str]:
    log = Path(tempfile.mkstemp(suffix='.log')[1])
    cmd = [PY, '-m', 'pytest', GCOV, PROP, '-q', '-p', 'no:cacheprovider',
           '-k', SELECT, '--no-header', '--tb=line']
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
    tail = [ln for ln in out.strip().splitlines() if ln.strip()][-1]
    print(f'BASELINE  rc={rc}  failed={base_ids}  | {tail}', flush=True)
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
            print(f'{mid:4} ANCHOR-MISS ({n} matches) -- {what}', flush=True)
            continue
        io.open(path, 'w', encoding='utf-8', newline='').write(src.replace(old_f, new_f))
        try:
            rc, out = run()
            ids = [i for i in failed_ids(out) if i not in base_ids]
            tail = [ln for ln in out.strip().splitlines() if ln.strip()][-1]
            verdict = 'CAUGHT' if rc != 0 else 'INERT'
            rows.append((mid, verdict, ','.join(ids) or '-', what))
            print(f'{mid:4} {verdict:6} rc={rc} {tail}', flush=True)
            for i in ids:
                print(f'       red: {i}', flush=True)
        finally:
            Path(path).write_bytes((backup / Path(path).name).read_bytes())

    print('\n=== TK87 CHURN-PASS SWEEP SUMMARY (2026-09-19f) ===')
    for (mid, verdict, ids, what) in rows:
        print(f'{mid:4} {verdict:11} {what}')
        print(f'     {ids}')
    shutil.rmtree(backup, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
