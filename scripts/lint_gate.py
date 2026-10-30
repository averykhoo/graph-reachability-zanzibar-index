"""Lint + type-check step of the gate (`formal/verify.sh lean`, step 4h; TK182).

    python scripts/lint_gate.py

Runs ``ruff check`` (rules: ``pyproject.toml`` ``[tool.ruff.lint]``) over the repo and
``mypy`` (``[tool.mypy]``, the library under ``src/zanzibar``), with the interpreter that runs
this script. Exit 0 only when both report nothing.

The tool versions are pinned EXACTLY in ONE place, ``pyproject.toml``'s ``lint`` extra
(``requirements.txt`` carries the same pins so CI installs them). This script reads the pins
there and refuses to run a different installed version: a new ruff or mypy release can add
findings, and the gate must not change meaning because the environment drifted. It refuses
a missing tool the same way, rather than skipping: a tolerated skip is how coverage leaks
out of a gate.

Design and measurements: ``docs/tk182-lint-typecheck-plan-2026-10-30.md``.

SABOTAGE (2026-10-30, session; each file restored and checked; the restored tree then ran
``rc=0 | lint + type check: clean``). Literal results, every one RED:

- L1 a type error added in ``src`` -> ``rc=1``, ``error: Incompatible types in assignment
  (expression has type "str", variable has type "int")  [assignment]``
- L2 an unused ``import os`` in a test -> ``rc=1``, ``F401 [*] `os` imported but unused``
- L3 the pin set to ``mypy==2.4.0`` while 2.4.1 is installed -> ``rc=1``,
  ``FAIL: mypy 2.4.1 is installed, the gate pins 2.4.0``
"""
from __future__ import annotations

import importlib.metadata
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOLS = ('ruff', 'mypy')


def pinned_versions(pyproject: Path = REPO / 'pyproject.toml') -> dict[str, str]:
    """``{tool: version}`` from the ``lint`` extra; every tool must be pinned with ``==``."""
    extra = tomllib.loads(pyproject.read_text(encoding='utf-8'))[
        'project']['optional-dependencies']['lint']
    pins = {}
    for req in extra:
        m = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)', req.strip())
        if not m:
            raise SystemExit(f'lint_gate: {req!r} in the lint extra is not an exact == pin')
        pins[m.group(1).lower()] = m.group(2)
    missing = set(TOOLS) - set(pins)
    if missing:
        raise SystemExit(f'lint_gate: the lint extra pins no {sorted(missing)}')
    return pins


def check_installed(pins: dict[str, str]) -> list[str]:
    """One problem line per tool that is missing or at another version."""
    problems = []
    for tool in TOOLS:
        try:
            have = importlib.metadata.version(tool)
        except importlib.metadata.PackageNotFoundError:
            problems.append(f'{tool} is not installed in {sys.executable}')
            continue
        if have != pins[tool]:
            problems.append(f'{tool} {have} is installed, the gate pins {pins[tool]}')
    return problems


def main() -> int:
    pins = pinned_versions()
    problems = check_installed(pins)
    if problems:
        for p in problems:
            print(f'FAIL: {p}')
        print('      install the pinned tools: pip install -r requirements.txt')
        return 1
    rc = 0
    for tool, cmd in (('ruff', [sys.executable, '-m', 'ruff', 'check', '--quiet', '--no-cache']),
                      ('mypy', [sys.executable, '-m', 'mypy', '--no-incremental'])):
        print(f'  {tool} {pins[tool]}: {" ".join(cmd[1:])}', flush=True)
        result = subprocess.run(cmd, cwd=REPO)
        if result.returncode != 0:
            print(f'FAIL: {tool} reported findings (rc={result.returncode}, see above)')
            rc = 1
    if rc == 0:
        print('  lint + type check: clean')
    return rc


if __name__ == '__main__':
    sys.exit(main())
