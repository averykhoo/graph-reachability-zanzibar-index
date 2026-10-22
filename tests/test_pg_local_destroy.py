"""``scripts/pg_local.sh destroy`` deletes the cluster directory, never its parent.

Incident, 2026-10-22: the destroy arm ran ``rm -rf "$(dirname "$DATA")"``. With the
documented ``ZANZIBAR_PG_DATA`` override pointing at ``<scratchpad>/pgreview`` it erased
the whole session scratchpad -- other lanes' files included, past the Recycle Bin. It was
safe only on the default layout, where the parent is the script's own ``zanzibar-pg``.
The fix removes ``$DATA`` and the script's ``server.log``, ``rmdir``s the parent only if
that leaves it empty, and refuses a ``$DATA`` that is not a cluster (no ``PG_VERSION``).

No server is needed: ``ZANZIBAR_PG_BIN`` points at an empty directory, so ``running``
is false and only the file handling runs.

Sabotage, 2026-10-22: the destroy arm restored to ``rm -rf "$(dirname "$DATA")"`` (the
refusal kept) -> ``test_override_keeps_the_parent_and_its_other_files`` RED with
``AssertionError: a sibling of the cluster was deleted``; the PG_VERSION refusal removed ->
``test_refuses_a_directory_that_is_not_a_cluster`` RED with ``assert 0 == 1``.
Instrument control: the first sabotage run was red for the WRONG reason (``no Git Bash
found``: git.exe here lives under ``Git/mingw64/bin``), which is why ``_bash`` walks
every parent of git.exe; re-run after that fix gave the two lines above.
"""

import os
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / 'scripts' / 'pg_local.sh'


def _bash() -> str:
    """Git Bash on Windows (``System32\\bash.exe`` is WSL and cannot see these paths),
    plain ``bash`` elsewhere. A missing bash FAILS: the gate itself runs in bash."""
    if os.name == 'nt':
        git = shutil.which('git')
        cands = []
        if git:   # .../Git/cmd/git.exe or .../Git/mingw64/bin/git.exe
            cands += [p / 'bin' / 'bash.exe' for p in Path(git).resolve().parents]
        cands.append(Path('C:/Program Files/Git/bin/bash.exe'))
        for c in cands:
            if c.is_file():
                return str(c)
        raise AssertionError(f'no Git Bash found among {cands}')
    b = shutil.which('bash')
    assert b, 'bash not on PATH'
    return b


def _destroy(data: Path, tmp_path: Path):
    env = dict(os.environ)
    empty_bin = tmp_path / 'nobin'
    empty_bin.mkdir(exist_ok=True)
    env['ZANZIBAR_PG_BIN'] = empty_bin.as_posix()
    env['ZANZIBAR_PG_DATA'] = data.as_posix()
    env['ZANZIBAR_PG_PORT'] = '55498'
    return subprocess.run([_bash(), SCRIPT.as_posix(), 'destroy'], env=env,
                          capture_output=True, text=True, timeout=60)


def _cluster(parent: Path) -> Path:
    data = parent / 'cluster'
    (data / 'base').mkdir(parents=True)
    (data / 'PG_VERSION').write_text('17\n')
    (parent / 'server.log').write_text('log\n')
    return data


def test_override_keeps_the_parent_and_its_other_files(tmp_path):
    parent = tmp_path / 'scratchpad'
    data = _cluster(parent)
    keep = parent / 'someone_elses_probe.py'
    keep.write_text('print(1)\n')
    r = _destroy(data, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not data.exists(), 'the cluster directory survived destroy'
    assert not (parent / 'server.log').exists(), "the script's own log survived"
    assert keep.is_file(), 'a sibling of the cluster was deleted'
    assert parent.is_dir()


def test_default_layout_removes_the_emptied_parent(tmp_path):
    parent = tmp_path / 'zanzibar-pg'
    data = _cluster(parent)
    r = _destroy(data, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not parent.exists(), 'the emptied zanzibar-pg parent was left behind'


def test_refuses_a_directory_that_is_not_a_cluster(tmp_path):
    data = tmp_path / 'not-a-cluster'
    data.mkdir()
    (data / 'precious.txt').write_text('x\n')
    r = _destroy(data, tmp_path)
    assert r.returncode == 1
    assert 'refusing to destroy' in r.stderr
    assert (data / 'precious.txt').is_file()
