"""Repo-root pytest configuration (TK120, 2026-10-06): every pytest run -- and every
subprocess it spawns -- must import THIS checkout's library from `src/`.

The library lives in `src/zanzibar/`. `pytest.ini` puts `src` on the pytest process's
`sys.path` (`pythonpath = src`), but that does not reach CHILD interpreters
(`tests/test_reg15_security_hardening.py::_run_under_O` runs `python -O -c ...`), which
would otherwise fall back to whatever `zanzibar` the environment has installed -- for an
editable install, possibly ANOTHER worktree's `src/`. So:

* `PYTHONPATH` is prefixed with this checkout's `src` here, at conftest import, and every
  child inherits it;
* `_require_this_checkouts_library` refuses to run at all if the `zanzibar` this process
  imports is not the one under `<this repo>/src/` (a stale or foreign install shadowing
  the tree would otherwise test the wrong code and pass).

Both are pinned, sabotage included, by `tests/test_tk120_package_layout.py`.
"""
import os
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent / 'src'

os.environ['PYTHONPATH'] = os.pathsep.join(
    [str(SRC)] + [p for p in os.environ.get('PYTHONPATH', '').split(os.pathsep) if p])


def _require_this_checkouts_library() -> None:
    import zanzibar
    got = Path(zanzibar.__file__).resolve()
    if SRC.resolve() not in got.parents:
        raise pytest.UsageError(
            f'REFUSED: `import zanzibar` resolved to {got}, not this checkout\'s '
            f'{SRC}. A different install is shadowing the tree, so the suite would test '
            f'the wrong code. Fix sys.path / PYTHONPATH (pytest.ini sets pythonpath = src).')


_require_this_checkouts_library()
