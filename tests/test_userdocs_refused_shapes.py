"""TK151 (2026-10-20, round 2): the refused-shapes reference page renders EVERY refusal.

``userdocs/_ext/refused_shapes.py`` turns each ``# REFUSED SHAPE`` comment block under
``src/zanzibar/`` into one section of ``userdocs/reference/refused-shapes.md``, with the
class ``refused-shape``. This module checks that count against an INDEPENDENT grep of the
source tree (``_grep_count``: its own walk and its own regex, nothing imported from the
extension), on a one-page Sphinx project that loads only the extension, so the check does
not depend on the rest of the site. It also pins the extension's own refusals: an
unreadable source file, no block found anywhere, and a header line the scan cannot see.

Sabotage evidence (2026-10-20), each applied alone to ``userdocs/_ext/refused_shapes.py``
and reverted; the literal observed output:

    S1 drop one source file from the scan (``source_files`` also filters
       ``p.name != "json_frontend.py"``). The one-page build itself goes red, because every
       hand-written entry for that file is now stale:
         E       AssertionError: rc=2
         E         Extension error!
         E             sphinx.errors.ExtensionError: refused-shapes:
         E               OVERRIDES entry ('schema/json_frontend.py', 'parse_openfga_json', 0)
                         names no REFUSED SHAPE block under src/zanzibar/; it is stale.
         (one such line per json_frontend.py entry)
         FAILED tests/test_userdocs_refused_shapes.py::test_every_refused_shape_block_is_rendered
         1 failed, 3 passed in 1.66s
    S2 drop one rendered entry, not a source file (the directive skips its last stage,
       "Graph index maintenance", so no build-time check can see it; this is the case
       only the count comparison catches):
         E       AssertionError: the page renders 56 refused-shape entries but src/zanzibar/
                 has 57 '# REFUSED SHAPE' blocks
         FAILED tests/test_userdocs_refused_shapes.py::test_every_refused_shape_block_is_rendered
         1 failed, 3 passed in 2.12s
    Restored (``cmp`` byte-identical to the pre-sabotage copy): 4 passed in 2.01s.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "zanzibar"
EXT = ROOT / "userdocs" / "_ext"

_HEADER_LINE = re.compile(r"^[ \t]*#[ \t]*REFUSED SHAPE\b", re.M)


def _grep_count(root: Path) -> dict[str, int]:
    """Lines starting a ``# REFUSED SHAPE`` comment, per file -- independent of the extension."""
    counts: dict[str, int] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            if name.endswith(".py"):
                path = Path(dirpath, name)
                n = len(_HEADER_LINE.findall(path.read_text(encoding="utf-8")))
                if n:
                    counts[path.relative_to(root).as_posix()] = n
    return counts


def test_every_refused_shape_block_is_rendered(tmp_path):
    expected = _grep_count(SRC)
    total = sum(expected.values())
    assert total > 0, "the grep found no '# REFUSED SHAPE' block under src/zanzibar/"
    # The product parser is not the only refusal site: the page must cover the others too.
    assert len(expected) > 1, expected

    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "conf.py").write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(SRC.parent)!r})\n"
        f"sys.path.insert(0, {str(EXT)!r})\n"
        "extensions = ['refused_shapes']\n"
        "root_doc = 'index'\n", encoding="utf-8")
    (proj / "index.rst").write_text("Refused\n=======\n\n.. refused-shapes::\n", encoding="utf-8")
    out = tmp_path / "html"
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    # Not -W: the one-page project has no API pages, so the "Raises:" links cannot resolve
    # here (the full strict build in test_userdocs_build.py resolves them).
    r = subprocess.run(
        [sys.executable, "-m", "sphinx", "-E", "-q", "--no-color", "-b", "html",
         "-d", str(tmp_path / "doctrees"), str(proj), str(out)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env, timeout=600)
    assert r.returncode == 0, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
    html = (out / "index.html").read_text(encoding="utf-8")
    rendered = len(re.findall(r"<section\b[^>]*\bclass=\"refused-shape\"", html))
    assert rendered == total, (
        f"the page renders {rendered} refused-shape entries but src/zanzibar/ has {total} "
        f"'# REFUSED SHAPE' blocks")


def _extension():
    sys.path.insert(0, str(EXT))
    sys.path.insert(0, str(SRC.parent))
    import refused_shapes
    return refused_shapes


def test_unreadable_source_file_fails_the_build(tmp_path):
    rs = _extension()
    from sphinx.errors import ExtensionError
    (tmp_path / "ok.py").write_text("def f():\n    # REFUSED SHAPE: x.\n    raise ValueError\n",
                                    encoding="utf-8")
    (tmp_path / "bad.py").write_bytes(b"# \xff\xfe not utf-8\n")
    with pytest.raises(ExtensionError, match=r"cannot read src/zanzibar/bad\.py"):
        rs.collect(tmp_path)


def test_no_block_anywhere_fails_the_build(tmp_path):
    rs = _extension()
    from sphinx.errors import ExtensionError
    (tmp_path / "a.py").write_text("def f():\n    raise ValueError\n", encoding="utf-8")
    with pytest.raises(ExtensionError, match="found no '# REFUSED SHAPE' comment block"):
        rs.collect(tmp_path)


def test_header_outside_a_comment_fails_the_build(tmp_path):
    rs = _extension()
    from sphinx.errors import ExtensionError
    (tmp_path / "a.py").write_text(
        'def f():\n    """REFUSED SHAPE: hidden in a docstring."""\n'
        "    # REFUSED SHAPE: seen.\n    raise ValueError\n", encoding="utf-8")
    with pytest.raises(ExtensionError, match=r"names 'REFUSED SHAPE' on 2 line\(s\) but 1"):
        rs.collect(tmp_path)
