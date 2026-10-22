"""Sphinx configuration for the zanzibar-index user documentation (TK151).

Build (strict: any warning, including a broken cross-reference, fails the build)::

    python -m sphinx -W -n --keep-going -b html userdocs <outdir>

The same command runs in ``tests/test_userdocs_build.py`` (inside the gate) and in
``.github/workflows/docs.yml`` (GitHub Pages).

Intersphinx reads PINNED inventories from ``userdocs/_inventories/`` rather than fetching
them at build time, so the gate never depends on the network: an unreachable
docs.python.org would otherwise be a warning, and ``-W`` would turn it into a red tile.
Refresh them deliberately with::

    curl -sSfL -o userdocs/_inventories/python.inv https://docs.python.org/3.13/objects.inv
    curl -sSfL -o userdocs/_inventories/sqlalchemy.inv https://docs.sqlalchemy.org/en/20/objects.inv
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Document THIS checkout's code, never an installed copy.
sys.path.insert(0, str(HERE.parent / "src"))

import zanzibar  # noqa: E402

# -- Project -----------------------------------------------------------------
project = "zanzibar-index"
author = "Avery Khoo"
copyright = "Avery Khoo"
release = zanzibar.__version__
version = release

# -- Unreleased-API banner ---------------------------------------------------
# The site is built from master, which can be ahead of the newest PyPI release. While
# CHANGELOG.md's newest heading is ``## [Unreleased]``, every page carries a banner naming
# the newest release (the next ``## [x.y.z]`` heading), so a reader who ran
# ``pip install zanzibar-index`` knows the pages may describe an API they do not have.
# The banner goes away by itself once the release heading replaces ``[Unreleased]``.
import re as _re  # noqa: E402

_SITE = "https://averykhoo.github.io/graph-reachability-zanzibar-index"
_REPO = "https://github.com/averykhoo/graph-reachability-zanzibar-index"
_headings = _re.findall(r"^## \[([^\]]+)\]", (HERE.parent / "CHANGELOG.md").read_text(encoding="utf-8"),
                        _re.MULTILINE)
UNRELEASED = bool(_headings) and _headings[0] == "Unreleased"
NEWEST_RELEASE = next((h for h in _headings if h != "Unreleased"), None)
if UNRELEASED:
    _announcement = (
        "These pages describe the development version, which has changes not yet on PyPI, "
        f"so their code may not run on the newest release, {NEWEST_RELEASE}. To follow them, "
        f"install from source: <code>pip install git+{_REPO}</code>.")
    if NEWEST_RELEASE and NEWEST_RELEASE.startswith("0.0."):
        _announcement += (f' {NEWEST_RELEASE} has the older 0.0.x API; see '
                          f'<a href="{_SITE}/how-to/upgrade-0.1.html">Upgrade from 0.0.x to 0.1</a>.')

# -- General -----------------------------------------------------------------
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    # local: renders every REFUSED SHAPE comment under src/zanzibar/ (userdocs/_ext/refused_shapes.py)
    "refused_shapes",
]
# Local extensions live in userdocs/_ext/.
sys.path.insert(0, str(HERE / "_ext"))

source_suffix = {".md": "markdown"}
root_doc = "index"
exclude_patterns = ["_build", "_inventories", "Thumbs.db", ".DS_Store"]

# A broken reference is a build failure (with -n), not a silent plain-text fallback.
nitpicky = True

# -- MyST --------------------------------------------------------------------
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
# Stable anchors for "## Heading" so pages can link [text](page.md#heading).
myst_heading_anchors = 3

# -- autodoc -----------------------------------------------------------------
autodoc_member_order = "bysource"
autodoc_typehints = "description"

# -- intersphinx -------------------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3.13", str(HERE / "_inventories" / "python.inv")),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20", str(HERE / "_inventories" / "sqlalchemy.inv")),
}

# Third-party types with no Sphinx inventory to link to (sqlmodel and pydantic publish their
# docs with MkDocs). They render as plain text. Keep this list to types that are genuinely
# unlinkable; anything in zanzibar must resolve.
nitpick_ignore = [
    ("py:class", "sqlmodel.orm.session.Session"),
    ("py:class", "sqlmodel.Session"),
    ("py:class", "Session"),
    ("py:class", "pydantic.config.ConfigDict"),
    ("py:class", "ConfigDict"),
    # Internal zanzibar types that appear in PUBLIC signatures (``RuleSet``'s fields,
    # ``BuildReport``) but are in no ``__all__``, so they are deliberately not
    # documented. (``SchemaInfo`` and ``CompiledBooleans`` became public in 0.1.0, TK164.) They render as plain text. Remove an entry if its type becomes public.
    ("py:class", "zanzibar.schema.rules.Rule"),
    ("py:class", "zanzibar.schema.rules.Filter"),
    ("py:class", "zanzibar.schema.syntax.DeclaredRelations"),
    ("py:class", "zanzibar.store.models.IndexCursor"),
]

# -- Public names for internal module paths ----------------------------------
# autodoc writes type hints with the DEFINING module (``zanzibar.graphindex.wildcard.
# LookupResult``), but the documented, canonical name is the public one: top-level exports
# as ``zanzibar.<Name>``, the rest at their public subpackage (``zanzibar.store.<Name>``).
# This resolver retargets an unresolved ``zanzibar.*`` (or bare) Python reference to the
# public object of the same trailing name, IF that object is documented. Anything it cannot
# map stays unresolved, so nitpicky mode still fails the build on a genuinely dead link.
_PUBLIC_PACKAGES = ("zanzibar.store", "zanzibar.schema", "zanzibar.setengine", "zanzibar.graphindex")


def _public_target(domain, target: str) -> str | None:
    objects = domain.objects  # fullname -> ObjectEntry
    parts = target.split(".")
    if parts[0] != "zanzibar" and len(parts) > 1:
        return None
    # the trailing dotted names, longest first: Store.check before check
    for k in range(1 if parts[0] == "zanzibar" else 0, len(parts)):
        suffix = ".".join(parts[k:])
        prefer = [f"zanzibar.{suffix}"]
        own = [p for p in _PUBLIC_PACKAGES if target.startswith(p + ".")]
        prefer += own + [p for p in _PUBLIC_PACKAGES if p not in own]
        for cand in [prefer[0]] + [f"{p}.{suffix}" for p in prefer[1:]]:
            if cand in objects and cand != target:
                return cand
    return None


def _resolve_internal_paths(app, env, node, contnode):
    if node.get("refdomain") != "py":
        return None
    domain = env.get_domain("py")
    target = node.get("reftarget", "")
    public = _public_target(domain, target)
    if public is None:
        return None
    node["reftarget"] = public
    return domain.resolve_xref(env, node.get("refdoc"), app.builder, node.get("reftype"),
                               public, node, contnode)


def setup(app):
    app.connect("missing-reference", _resolve_internal_paths)


# -- HTML --------------------------------------------------------------------
html_theme = "furo"
html_title = "zanzibar-index"
html_theme_options = {"announcement": _announcement} if UNRELEASED else {}
