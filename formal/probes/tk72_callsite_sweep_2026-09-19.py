"""TK72 mutation sweep over the 2026-09-19f call-site census and the ZT-P5 fix.

Same harness shape as `formal/probes/tk87_churn_sweep_2026-09-19.py`. What it sweeps:

  * `tests/test_invariants_docstring_matches_body.py
    ::test_every_schema_backed_check_invariants_call_passes_schema_info` -- the census
    that makes dropping `schema_info` visible;
  * `tests/test_zt_p5_readjudication.py`'s three now-fixed call sites and its instrument
    control.

`S0` is the HARNESS CONTROL: it inverts the census's own final claim, so a sweep that
reports `S0` INERT is a broken harness rather than a clean module.

Run from the repo root:

    python formal/probes/tk72_callsite_sweep_2026-09-19.py

It edits tracked files in place and restores them from a byte copy in `finally`; check
`git status` afterwards. Anchors are written with `\n` and fitted to each file's dominant
line ending, and a `0 matches` row is reported as ANCHOR-MISS, never counted.
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
DOC = 'tests/test_invariants_docstring_matches_body.py'
ZTP5 = 'tests/test_zt_p5_readjudication.py'
TARGETS = [DOC, ZTP5]

SELECT = 'schema_backed or state_level_live_equals_rebuild or i13'

MUTATIONS = [
    ('S0', DOC,
     "    missing = sorted(set(bare) - set(_SCHEMALESS_SITES))\n"
     "    assert not missing, (\n",
     "    missing = sorted(set(bare) - set(_SCHEMALESS_SITES))\n"
     "    assert missing, (\n",
     "HARNESS CONTROL: invert the census's own claim"),
    ('S1', ZTP5,
     "            check_invariants(session, 'live', si)\n",
     "            check_invariants(session, 'live')\n",
     'revert ONE ZT-P5 call site to the pre-TK72 form'),
    ('S2', DOC,
     "    ('tests/test_reg17_closure_fanout_cap.py',\n"
     "     'test_node_removal_is_never_capped'):\n"
     "        'raw ReachabilityIndex with a synthetic p/t shape and no compiled schema',\n",
     "",
     'drop one allowlist entry -> the census must report it as MISSING'),
    ('S3', DOC,
     "_MIN_CALL_SITES = 40",
     "_MIN_CALL_SITES = 40\n_UNUSED = ('tests/nope.py', 'nope')",
     'a no-op edit next to the floor (expected INERT: it claims nothing)'),
    ('S4', DOC,
     "    for path in root.rglob('*.py'):\n",
     "    for path in root.rglob('*.pyx'):\n",
     'blind the AST walk -> the ceiling control must catch it'),
    ('S5', ZTP5,
     "            assert si.bridged_out_shapes, (\n",
     "            assert si.bridged_out_shapes or True, (\n",
     'weaken the instrument control (expected INERT: the corpus IS bridged-out today)'),
]


def _fit(text, path):
    raw = Path(path).read_bytes()
    return text.replace('\n', '\r\n') if raw.count(b'\r\n') > raw.count(b'\n') // 2 else text


def run():
    log = Path(tempfile.mkstemp(suffix='.log')[1])
    cmd = [PY, '-m', 'pytest', DOC, ZTP5, '-q', '-p', 'no:cacheprovider',
           '-k', SELECT, '--no-header', '--tb=line']
    with io.open(log, 'w', encoding='utf-8', errors='replace') as fh:
        rc = subprocess.call(cmd, cwd=str(ROOT), stdout=fh, stderr=subprocess.STDOUT)
    return rc, io.open(log, encoding='utf-8', errors='replace').read()


def failed_ids(out):
    return sorted(set(re.findall(r'^(?:FAILED|ERROR) (\S+)', out, re.M)))


def main():
    backup = Path(tempfile.mkdtemp())
    for t in TARGETS:
        (backup / Path(t).name).write_bytes(Path(t).read_bytes())
    rc, out = run()
    base = failed_ids(out)
    print(f'BASELINE rc={rc} failed={base} | '
          f'{[l for l in out.strip().splitlines() if l.strip()][-1]}', flush=True)
    if rc != 0:
        print('REFUSING: baseline is not green, attribution would be meaningless')
        return 2
    rows = []
    for (mid, path, old, new, what) in MUTATIONS:
        old_f, new_f = _fit(old, path), _fit(new, path)
        src = io.open(path, encoding='utf-8', newline='').read()
        n = src.count(old_f)
        if n != 1:
            print(f'{mid:4} ANCHOR-MISS ({n} matches) -- {what}', flush=True)
            rows.append((mid, 'ANCHOR-MISS', f'{n} matches', what))
            continue
        io.open(path, 'w', encoding='utf-8', newline='').write(
            src.replace(old_f, new_f, 1))
        try:
            rc, out = run()
            ids = [i for i in failed_ids(out) if i not in base]
            tail = [l for l in out.strip().splitlines() if l.strip()][-1]
            verdict = 'CAUGHT' if rc != 0 else 'INERT'
            rows.append((mid, verdict, ','.join(ids) or '-', what))
            print(f'{mid:4} {verdict:6} rc={rc} {tail}', flush=True)
            for line in out.splitlines():
                if 'AssertionError' in line and 'assert' not in line[:6]:
                    print(f'       {line.strip()[:200]}', flush=True)
                    break
        finally:
            Path(path).write_bytes((backup / Path(path).name).read_bytes())
    print('\n=== TK72 CALL-SITE SWEEP SUMMARY (2026-09-19f) ===')
    for (mid, verdict, ids, what) in rows:
        print(f'{mid:4} {verdict:11} {what}')
        print(f'     {ids}')
    shutil.rmtree(backup, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
