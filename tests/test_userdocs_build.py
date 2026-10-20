"""TK151 (2026-10-20): the user-docs site builds STRICTLY, inside the gate.

Runs exactly the command ``.github/workflows/docs.yml`` deploys with::

    python -m sphinx -W -n --keep-going -b html userdocs <outdir>

``-W`` makes every warning an error and ``-n`` (nitpicky, also set in ``userdocs/conf.py``)
makes a cross-reference to a symbol that does not exist a warning, so a renamed API breaks
this test rather than leaving a dead link on the site. A page left out of every toctree is
a warning too. Intersphinx reads the pinned inventories in ``userdocs/_inventories/``, so
the build needs no network.

Sabotage evidence (2026-10-20, TK151 scaffold), each applied alone and reverted:

    B1 add "{py:class}`zanzibar.NoSuchThing`" to reference/exceptions.md (a dead API link):
         FAILED tests/test_userdocs_build.py::test_userdocs_build_strictly
         reference/exceptions.md:3: WARNING: py:class reference target not found:
         zanzibar.NoSuchThing [ref.class]
    B2 add an orphan page userdocs/how-to/orphan.md that no toctree lists:
         FAILED tests/test_userdocs_build.py::test_userdocs_build_strictly
         how-to/orphan.md: WARNING: document isn't included in any toctree [toc.not_included]
    Restored: 1 passed.

The same build is then scanned for repository-internal references (task ids such as
``TK123``, internal paths such as ``docs/...md`` or ``formal/...``), which a page for
library users must not carry; the old 0.0.x class name ``ShapeRefusedSinceTK137`` is the one
allowed hit, because it is a real API name a reader upgrading from 0.0.x will meet.
Sabotage evidence (2026-10-20): ``test_internal_reference_scan_fires`` runs the scanner on a
planted page body; and the scanner run over the round-1 build, whose changelog page
included CHANGELOG.md verbatim, reported exactly that page:

    reference/changelog.html ['TK123', 'TK137', 'TK138', 'TK139', 'TK140', 'TK144', 'TK147',
    'TK153', 'TK154', 'TK155', 'TK156', 'TK157', 'TK4', 'docs/pypi-trial-0.0.2-2026-10-07.md',
    'docs/pypi-trial-0.0.3-2026-10-08.md', 'formal/conformance/test_runner_retry.py',
    'tests/test_tk122_release_metadata.py']

    and planting "Planted TK<999>." (the planted id is that text without the angle brackets; spelled this way here
    because tests/test_tasktool.py refuses an unfiled task id outside tasks/) in
    reference/changelog.md (reverted after):
         FAILED tests/test_userdocs_build.py::test_userdocs_build_strictly
         E  AssertionError: user pages carry internal references:
            {'reference/changelog.html': ['TK<999>']}   (brackets added here, see above)
    Restored: 2 passed.
"""

from __future__ import annotations

import html
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USERDOCS = ROOT / "userdocs"


# Repository-internal references a user page must not show. Real API names that happen to
# contain one are allowed by exact name.
_INTERNAL = re.compile(r"\b(?:TK|ZT-P|ASK-)\d+[a-z]?\b"
                       r"|(?<![\w./-])(?:docs|formal|tests|tasks|scripts)/[\w./-]*[\w/]")
_ALLOWED = ("ShapeRefusedSinceTK137",)


def internal_references(page_html: str) -> list[str]:
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", page_html, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", body))
    for name in _ALLOWED:
        text = text.replace(name, " ")
    return sorted(set(m.group(0) for m in _INTERNAL.finditer(text)))


def test_internal_reference_scan_fires():
    planted = "<p>Fixed in <code>TK154</code>; see docs/tk154-stale-lookup-ids-2026-10-16.md.</p>"
    assert internal_references(planted) == ["TK154", "docs/tk154-stale-lookup-ids-2026-10-16.md"]
    assert internal_references("<p>ShapeRefusedSinceTK137 is now ShapeNoLongerAccepted</p>") == []
    assert internal_references("<p>see the userdocs/ folder and how-to/errors.html</p>") == []


def test_userdocs_build_strictly(tmp_path):
    out, doctrees, warnfile = tmp_path / "html", tmp_path / "doctrees", tmp_path / "warnings.txt"
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    r = subprocess.run(
        [sys.executable, "-m", "sphinx", "-W", "-n", "--keep-going", "-E", "-q", "--no-color",
         "-b", "html", "-d", str(doctrees), "-w", str(warnfile), str(USERDOCS), str(out)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env, timeout=600)
    warnings = warnfile.read_text(encoding="utf-8") if warnfile.exists() else ""
    assert r.returncode == 0, f"strict Sphinx build failed (rc={r.returncode}):\n{warnings}\n{r.stdout}\n{r.stderr}"
    assert warnings.strip() == "", warnings

    # Every source page was actually rendered (guards a conf.py exclude_patterns that
    # quietly drops a section: a page that is never READ produces no toctree warning).
    pages = sorted(p.relative_to(USERDOCS).with_suffix(".html").as_posix()
                   for p in USERDOCS.rglob("*.md") if "_build" not in p.relative_to(USERDOCS).parts)
    assert pages, "userdocs/ has no pages"
    missing = [p for p in pages if not (out / p).is_file()]
    assert not missing, f"pages with no rendered HTML: {missing}"

    # No page shows a repository-internal task id or path.
    leaks = {p: hits for p in pages
             if (hits := internal_references((out / p).read_text(encoding="utf-8")))}
    assert not leaks, f"user pages carry internal references: {leaks}"
