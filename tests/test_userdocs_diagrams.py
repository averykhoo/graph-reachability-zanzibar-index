"""The explanation pages' SVG diagrams are generated, never hand-edited (TK151).

``userdocs/_diagrams/make_diagrams.py`` draws every figure; the SVGs under
``userdocs/explanation/img/`` are its output, committed so the docs build needs no
diagram tooling. These tests fail when the two drift apart (a hand edit to an SVG, or a
generator change without a regenerate), and when a generated figure is not shown on any
page in both themes.

Sabotage, 2026-10-23: changing one label in ``graph_two_paths`` without regenerating
turned ``test_committed_svgs_match_generator`` red naming ``graph-index-paths.svg`` and
``graph-index-paths-dark.svg``; deleting the dark image directive for
``boolean-cascade`` from ``boolean-operators.md`` turned
``test_every_figure_is_shown_in_both_themes`` red naming ``boolean-cascade-dark.svg``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "userdocs" / "_diagrams" / "make_diagrams.py"
IMG = ROOT / "userdocs" / "explanation" / "img"


def _generated() -> dict[str, str]:
    spec = importlib.util.spec_from_file_location("make_diagrams", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.generate()


def test_committed_svgs_match_generator():
    want = _generated()
    have = {p.name: p.read_text(encoding="utf-8").replace("\r\n", "\n")
            for p in IMG.glob("*.svg")}
    stale = sorted(n for n in want if have.get(n) != want[n])
    orphans = sorted(set(have) - set(want))
    assert not stale and not orphans, (
        f"regenerate with `python userdocs/_diagrams/make_diagrams.py`: stale={stale}, "
        f"not generated={orphans}")


def test_every_figure_is_shown_in_both_themes():
    pages = "\n".join(p.read_text(encoding="utf-8")
                      for p in (ROOT / "userdocs" / "explanation").glob("*.md"))
    missing = []
    for name in _generated():
        theme = "only-dark" if name.endswith("-dark.svg") else "only-light"
        if f"```{{image}} img/{name}\n:class: {theme}\n" not in pages.replace("\r\n", "\n"):
            missing.append(name)
    assert not missing, f"figures not shown with their theme class: {missing}"
