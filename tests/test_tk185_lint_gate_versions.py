"""`scripts/lint_gate.py` prints the versions mypy ran against (TK185, folded in from TK183).

The 0.1.2 cycle's mypy step went red only on CI (540bb50, fixed in b743587): CI installs the
newest sqlmodel / SQLAlchemy / pydantic, the local env the pinned ones, and nothing in either
log said which. Those libraries stay UNPINNED for the test run on purpose (CI's newest-deps
install is how drift is caught), so the gate prints them instead:
`scripts/lint_gate.py::environment_line`, printed first by `main`. These tests pin that line
without running mypy (`subprocess.run` is stubbed).

SABOTAGE (2026-11-20, docs/sabotage-procedure.md). The narrowest plausible weakening: the
`print(environment_line(), flush=True)` line in `main` deleted (the function kept, so only the
print-site test can catch it). Literal observed result::

    E   AssertionError: assert '  ruff 0.17....et --no-cache' == '  type-check...dantic 2.13.4'
    E     -   type-check environment: Python 3.13.14, mypy 2.4.1, sqlmodel 0.0.39, SQLAlchemy 2.0.51, pydantic 2.13.4
    E     +   ruff 0.17.3: -m ruff check --quiet --no-cache
    FAILED tests/test_tk185_lint_gate_versions.py::test_main_prints_the_environment_line_first
    1 failed, 3 passed

Restored with the Edit tool; the module then ran `4 passed`.
"""
from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from scripts import lint_gate  # noqa: E402


def test_the_typed_deps_are_the_ones_ci_drifts_on() -> None:
    """Dropping one of these from the line is how the next CI-only red goes unreadable."""
    assert set(lint_gate.TYPED_DEPS) >= {'mypy', 'sqlmodel', 'SQLAlchemy', 'pydantic'}


def test_environment_line_names_python_and_each_installed_version() -> None:
    line = lint_gate.environment_line()
    assert line.startswith('  type-check environment: Python ')
    assert f'Python {sys.version.split()[0]}' in line
    for dist in lint_gate.TYPED_DEPS:
        assert f'{dist} {importlib.metadata.version(dist)}' in line, (dist, line)


def test_a_missing_distribution_reads_not_installed(monkeypatch) -> None:
    monkeypatch.setattr(lint_gate, 'TYPED_DEPS', ('mypy', 'no-such-dist-tk185'))
    line = lint_gate.environment_line()
    assert 'no-such-dist-tk185 not installed' in line
    assert f'mypy {importlib.metadata.version("mypy")}' in line


def test_main_prints_the_environment_line_first(monkeypatch, capsys) -> None:
    calls = []

    def fake_run(cmd, cwd=None):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(lint_gate.subprocess, 'run', fake_run)
    rc = lint_gate.main()
    out = capsys.readouterr().out.splitlines()
    assert out[0] == lint_gate.environment_line()
    # The stub was reached (the pins matched), so the line precedes a real mypy invocation.
    assert rc == 0 and [c[2] for c in calls] == ['ruff', 'mypy'], (rc, calls, out)
