"""TK77 mutation sweep over the crossable-corpus additions of 2026-09-19d.

Reproduces the sabotage table recorded in `docs/tk77-crossable-census-2026-09-19.md`
(the dated append at the top) and in the docstrings of
`tests/test_wildcard_property.py::assert_crossable_pool`,
`::test_middle_sync_record_filters_a_non_crossable_corpus` and
`::test_middle_sync_record_excludes_the_wildcard_entity`.

Run from the repo root:

    python formal/probes/tk77_middles_reach_sweep_2026-09-19.py

Each mutation is a narrowest-plausible weakening of something the new tests claim; it
is applied to the working tree, the affected tests are run, and the file is restored
from a byte copy in `finally`. **It edits tracked files in place** -- do not run it on
a dirty tree you care about, and check `git status` afterwards.

`M0` is the HARNESS CONTROL (`docs/sabotage-procedure.md`): it flips one of the new
pins' own claims, so a sweep that reports `M0` as INERT is a broken harness rather
than a clean module. This matters here -- the first run of this sweep reported `M9`
as ANCHOR-MISS and `M4`/`M5`/`M10` as INERT, and two of those three inert rows were
real holes that the guards now close.

Selection is `-k 'crossable or middle_sync'` on the two touched modules. That is
sound because every mutated symbol (`CROSSABLE_WC`, `CROSSABLE_SHAPES`,
`_crossable_raw_tuples`, `assert_crossable`, `assert_remove_path_reached`,
`MiddleSyncRecord`, `record_middle_syncs`) is NEW and has no other caller -- so a
mutation cannot redden a test this selection hides. The unmutated full modules are
run green separately.

⚠ An ANCHOR-MISS row measures NOTHING. The line-ending-sensitive multi-line anchor
`M9` shipped in the first run as `0 matches`, which prints beside the CAUGHT rows and
reads like a result.
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
PROP = 'tests/test_wildcard_property.py'
MTX = 'tests/test_matrix.py'
HLP = 'tests/wildcard_helpers.py'
TARGETS = [PROP, MTX, HLP]

# (id, file, old, new, what it is supposed to move)
MUTATIONS = [
    ('M0', PROP,
     "    assert rec.effective, (",
     "    assert not rec.effective, (",
     'HARNESS CONTROL: invert assert_remove_path_reached own claim'),
    ('M1', PROP,
     "CROSSABLE_WC = frozenset({('folder', 'viewer'), ('doc', 'viewer')})",
     "CROSSABLE_WC = frozenset({('doc', 'viewer')})",
     'the plausible parameter edit: drop the owc half of the conjunction'),
    ('M2', PROP,
     "CROSSABLE_WC = frozenset({('folder', 'viewer'), ('doc', 'viewer')})",
     "CROSSABLE_WC = frozenset()",
     'declare no object wildcard at all -> corpus silently non-crossable'),
    ('M3', PROP,
     "CROSSABLE_SHAPES = frozenset({('folder', 'viewer')})",
     "CROSSABLE_SHAPES = frozenset()",
     'weaken the crossability pin to accept an empty set'),
    ('M4', PROP,
     "    out.append(('...', 'folder', '*', 'parent', 'folder', 'f2'))",
     "",
     'drop one bare-star tupleset subject from the pool (data-level bridge)'),
    ('M5', PROP,
     "    out.append(('...', 'folder', '*', 'parent', 'folder', 'f2'))\r\n"
     "    for d in CROSS_DOCS:\r\n"
     "        out.append(('...', 'folder', 'f1', 'parent', 'doc', d))\r\n"
     "        out.append(('...', 'folder', '*', 'parent', 'doc', d))\r\n",
     "    for d in CROSS_DOCS:\r\n"
     "        out.append(('...', 'folder', 'f1', 'parent', 'doc', d))\r\n",
     'drop EVERY bare-star tupleset subject from the pool'),
    ('M6', PROP,
     "            if not present or rng.random() < 0.55:",
     "            if not present or rng.random() < 1.1:",
     'crossable property walk never removes -> remove path unreached'),
    ('M7', MTX,
     "            if not present or rng.random() < 0.55:",
     "            if not present or rng.random() < 1.1:",
     'crossable matrix arm never removes -> remove path unreached'),
    ('M8', HLP,
     "        rec.raw.append((entity_type, name))",
     "        pass",
     'INSTRUMENT KILL: recorder observes nothing'),
    ('M9', HLP,
     "                if n != '*' and t in self._crossable_types]",
     "                if True]",
     'read RAW as reach -- the census trap (a), in the instrument'),
    ('M10', HLP,
     "                if n != '*' and t in self._crossable_types]",
     "                if t in self._crossable_types]",
     "drop only the n != '*' clause from the effective filter"),
    ('M11', PROP,
     "                proc.run_cascade(wm)",
     "                pass",
     'omit the boolean cascade -> `restricted` answers False forever'),
]


def run() -> tuple[int, str]:
    log = Path(tempfile.mkstemp(suffix='.log')[1])
    cmd = [PY, '-m', 'pytest', PROP, MTX, '-q', '-p', 'no:cacheprovider',
           '-k', 'crossable or middle_sync', '--no-header', '-x' if False else '--tb=no']
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
        src = io.open(path, encoding='utf-8', newline='').read()
        n = src.count(old)
        if n != 1:
            rows.append((mid, 'ANCHOR-MISS', f'{n} matches', what))
            print(f'{mid:4} ANCHOR-MISS ({n} matches) -- {what}')
            continue
        io.open(path, 'w', encoding='utf-8', newline='').write(src.replace(old, new))
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

    print('\n=== TK77 SWEEP SUMMARY ===')
    for (mid, verdict, ids, what) in rows:
        print(f'{mid:4} {verdict:11} {what}')
        print(f'     {ids}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
