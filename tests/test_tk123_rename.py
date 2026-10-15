"""TK123 item 3 (A1, A45; 2026-10-15): the decided rename, and the guard that the old
names do not survive on the shipped surface.

The rename: package ``zanzibar.connectedstore`` -> ``zanzibar.store``; class
``ConnectedStore`` -> ``Store``; the inner module ``store.py`` -> ``_store.py`` (so the
class is never ``zanzibar.store.store.Store``); the graph index model
``zanzibar.graphindex.Store`` -> ``IndexStore``. The table name ``zanzibar_store`` is
UNCHANGED (0.0.x databases must open), and so are the ``tests/test_connectedstore*.py``
file names (not on the wheel's surface; FROZEN docs cite them by path).

Pins:

* ``test_old_names_do_not_import`` -- every old import path fails, the new ones resolve,
  the class's ``__module__`` is the underscored inner module, and the model keeps its
  table. It also refuses a leftover ``src/zanzibar/connectedstore/`` directory: a stale
  ``__pycache__`` left there by the move makes ``import zanzibar.connectedstore``
  SUCCEED as an empty namespace package, which would fake the import half green.
* ``test_no_shipped_string_names_the_old_module_or_class`` -- a scan of every line of
  ``src/zanzibar/**/*.py`` (code, docstrings, messages and comments alike) plus
  ``PYPI_README.md`` (the wheel's long description) for ``connectedstore`` (not preceded
  by an identifier character, which spares the kept ``test_connectedstore*`` file names),
  ``ConnectedStore`` and ``zanzibar.store.store``.
* ``test_scanner_finds_an_injected_old_name`` -- the scanner's sabotage, made permanent:
  a tmp copy of the package with ``ConnectedStore`` injected into ONE docstring yields
  exactly one finding, and the untouched copy yields none (the instrument control).

Sabotage evidence (2026-10-15, first-hand):

* leftover directory, by hand: ``mkdir src/zanzibar/connectedstore/__pycache__``, then
  ``python -c "import zanzibar.connectedstore as m; print(m)"`` printed
  ``<module 'zanzibar.connectedstore' (namespace) from [...]>`` (rc 0), and this module's
  ``test_old_names_do_not_import`` went red on the directory assert:
  ``AssertionError: a leftover src/zanzibar/connectedstore/ makes the old import succeed``.
* the string scan: see ``test_scanner_finds_an_injected_old_name`` (runs every time).
"""
import importlib
import re
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / 'src' / 'zanzibar'

OLD_NAME_PATTERNS = (
    re.compile(r'(?<![A-Za-z0-9_])connectedstore'),
    re.compile(r'\bConnectedStore\b'),
    re.compile(r'\bzanzibar\.store\.store\b'),
)


def find_old_names(pkg_root: Path, extra_files=()):
    """Every ``(path, line_no, line)`` under ``pkg_root/**/*.py`` (and ``extra_files``)
    that names the pre-TK123 module or class."""
    hits = []
    paths = sorted(p for p in pkg_root.rglob('*.py') if '__pycache__' not in p.parts)
    for path in [*paths, *extra_files]:
        text = path.read_text(encoding='utf-8')
        for no, line in enumerate(text.splitlines(), 1):
            if any(p.search(line) for p in OLD_NAME_PATTERNS):
                hits.append((str(path), no, line.strip()))
    return hits


@pytest.mark.parametrize('old', ['zanzibar.connectedstore', 'zanzibar.store.store',
                                 'zanzibar.connectedstore.store'])
def test_old_names_do_not_import(old):
    assert not (PKG / 'connectedstore').exists(), (
        'a leftover src/zanzibar/connectedstore/ makes the old import succeed')
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(old)
    import zanzibar.graphindex as gi
    import zanzibar.graphindex.models as gm
    import zanzibar.store as st
    assert not hasattr(gi, 'Store') and not hasattr(gm, 'Store')
    assert 'Store' not in gi.__all__ and 'IndexStore' in gi.__all__
    assert gi.IndexStore is gm.IndexStore
    assert gi.IndexStore.__tablename__ == 'zanzibar_store'
    assert st.Store.__module__ == 'zanzibar.store._store'
    assert 'Store' in st.__all__ and 'ConnectedStore' not in st.__all__


def test_no_shipped_string_names_the_old_module_or_class():
    hits = find_old_names(PKG, extra_files=[REPO / 'PYPI_README.md'])
    assert not hits, '\n'.join(f'{p}:{n}: {l}' for p, n, l in hits)


def test_scanner_finds_an_injected_old_name(tmp_path):
    copy = tmp_path / 'zanzibar'
    shutil.copytree(PKG, copy, ignore=shutil.ignore_patterns('__pycache__'))
    assert find_old_names(copy) == []  # control: the clean copy is clean
    target = copy / 'store' / 'apply.py'
    text = target.read_text(encoding='utf-8')
    first_doc = text.index('"""') + 3
    target.write_text(text[:first_doc] + 'ConnectedStore ' + text[first_doc:], encoding='utf-8')
    hits = find_old_names(copy)
    assert len(hits) == 1, hits
    assert hits[0][0].endswith('apply.py')
    # and the kept test-file names do NOT count as the old module name
    (copy / 'note.py').write_text('# see tests/test_connectedstore_build.py\n', encoding='utf-8')
    assert len(find_old_names(copy)) == 1
