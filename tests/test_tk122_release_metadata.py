"""TK122 (2026-10-07): the release-facing text cannot drift from the code.

* The PyPI README's quickstart is EXECUTED here, with every line commented `# True` /
  `# False` turned into an assertion. A README example nobody runs is the doc-shaped
  version of a test that fails by passing.
* `CHANGELOG.md`'s newest version heading equals `zanzibar.__version__`, which is the
  single source of the package version (`pyproject.toml` reads it dynamically).

Sabotage evidence (2026-10-07, TK122), each applied alone and reverted:

    Q1 flip the README's final `# False` to `# True`   -> 1 failed, 2 passed
    Q2 bump CHANGELOG's newest heading to 0.1.1        -> 1 failed, 2 passed
    Q3 add a static `version = "0.1.0"` to [project]   -> 1 failed, 2 passed
"""
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import zanzibar

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "PYPI_README.md"
CHANGELOG = ROOT / "CHANGELOG.md"
PYPROJECT = ROOT / "pyproject.toml"

_EXPECT = re.compile(r"^(\s*)(store\.check\(.*\))\s*#\s*(True|False)\s*$")


def _quickstart() -> str:
    blocks = re.findall(r"```python\n(.*?)```", README.read_text(encoding="utf-8"), re.S)
    assert len(blocks) == 1, f"expected exactly one python block, found {len(blocks)}"
    out, n = [], 0
    for line in blocks[0].splitlines():
        m = _EXPECT.match(line)
        if m:
            indent, expr, want = m.groups()
            line = f"{indent}assert ({expr}) is {want}, {expr!r}"
            n += 1
        out.append(line)
    assert n >= 2, "the quickstart lost its checked expectations"
    return "\n".join(out) + "\nprint('QUICKSTART-OK')\n"


def test_the_pypi_readme_quickstart_runs_and_its_comments_are_true(tmp_path):
    # Its own process and cwd: the example writes perms.db and touches the global
    # SQLModel metadata, neither of which may leak into the tile.
    r = subprocess.run([sys.executable, "-c", _quickstart()], cwd=tmp_path,
                       capture_output=True, text=True, env=os.environ.copy(), timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip().endswith("QUICKSTART-OK"), r.stdout


def test_changelog_newest_version_is_the_package_version():
    versions = re.findall(r"^## \[(\d+\.\d+\.\d+[^\]]*)\]", CHANGELOG.read_text(encoding="utf-8"),
                          re.M)
    assert versions, "no released version heading in CHANGELOG.md"
    assert versions[0] == zanzibar.__version__, (versions[0], zanzibar.__version__)


def test_pyproject_takes_its_version_from_the_package():
    meta = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert "version" not in meta["project"], "a second, static copy of the version"
    assert "version" in meta["project"]["dynamic"]
    assert meta["tool"]["setuptools"]["dynamic"]["version"] == {"attr": "zanzibar.__version__"}
