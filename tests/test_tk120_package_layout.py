"""TK120 (2026-10-06): the library is the `src/zanzibar/` package, and the suite tests
THIS checkout's copy of it.

Pins, each with its sabotage made permanent:

* `test_a_foreign_zanzibar_is_refused` -- the root `conftest.py` guard. A fake `zanzibar`
  package put first on the path (with pytest.ini's `pythonpath` overridden away) must make
  pytest REFUSE to start, not quietly test the fake.
* `test_children_import_this_checkouts_src` -- a child interpreter spawned by a test
  (the `_run_under_O` shape) imports `zanzibar` from `<repo>/src/`.
* `test_every_library_dir_is_a_package` -- setuptools `packages.find` only ships
  directories with an `__init__.py`; a subpackage without one would pass every test here
  (pythonpath imports it as a namespace package) and be MISSING from a built wheel.
* `test_no_library_code_outside_src` -- no product module may be re-added at the repo
  root under an old name.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / 'src'


def test_a_foreign_zanzibar_is_refused(tmp_path):
    fake = tmp_path / 'zanzibar'
    fake.mkdir()
    (fake / '__init__.py').write_text('"""a foreign install"""\n', encoding='utf-8')
    env = dict(os.environ, PYTHONPATH=str(tmp_path))
    r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '--collect-only', '-p', 'no:cacheprovider',
                        '-o', 'pythonpath=', 'tests/test_index.py'],
                       cwd=REPO, env=env, capture_output=True, text=True)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out
    assert 'REFUSED: `import zanzibar` resolved to' in out, out
    # control: the same command WITHOUT the fake collects normally, so the refusal above
    # is the guard and not some other breakage of the instrument
    ok = subprocess.run([sys.executable, '-m', 'pytest', '-q', '--collect-only', '-p', 'no:cacheprovider',
                         'tests/test_index.py'], cwd=REPO, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr


def test_children_import_this_checkouts_src():
    r = subprocess.run([sys.executable, '-c', 'import zanzibar; print(zanzibar.__file__)'],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    got = Path(r.stdout.strip()).resolve()
    assert SRC.resolve() in got.parents, got


def test_every_library_dir_is_a_package():
    lib = SRC / 'zanzibar'
    dirs = {p.parent for p in lib.rglob('*.py') if '__pycache__' not in p.parts}
    assert len(dirs) >= 4, dirs  # zanzibar, graphindex, setengine, connectedstore (+ schema once split)
    missing = sorted(str(d.relative_to(REPO)) for d in dirs if not (d / '__init__.py').is_file())
    assert not missing, f'directories that a wheel would silently drop: {missing}'


def test_no_library_code_outside_src():
    # .py files only: a moved package can leave an ignored __pycache__/ behind
    old = ['zanzibar_utils_v1.py', 'index_v4', 'setengine', 'connectedstore', 'legacy', 'zanzibar']
    present = [o for o in old
               if (REPO / o).is_file() or ((REPO / o).is_dir() and any((REPO / o).rglob('*.py')))]
    assert not present, present
