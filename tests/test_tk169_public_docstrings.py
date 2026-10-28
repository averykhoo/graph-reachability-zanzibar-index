"""TK169 guard: no internal task id or private repo path in a public docstring.

What ``help()`` shows a user must not point at things the user cannot see: task ids
(``TK12``, ``ZT-P0-1``, ``R6-4``, ``ASK-1``), paths inside this repository that are not
shipped in the wheel (``docs/``, ``formal/``, ``tests/``, ``scripts/``, ``.scratch/``),
or dated session keys (``2026-09-12b``). The census that cleaned them out is
``docs/tk169-docstring-census-2026-10-28.md``; this module stops them coming back.

The walk (``_public_docstrings``):

* every package in ``PACKAGES`` and every non-underscore submodule below
  ``zanzibar`` (module docstrings: ``pydoc`` lists them);
* every name in each package's ``__all__`` (``zanzibar``'s lazy names are resolved);
* for each class: its own docstring and every public (non-underscore) method, property,
  classmethod and staticmethod defined in the class body or inherited from a
  ``zanzibar`` class (inherited builtins such as ``Exception.args`` are skipped: their
  text is not ours).

``ALLOWLIST`` holds ``(owner, matched text)`` pairs that are legitimate, each with a
reason. It is empty on purpose; add to it only with a reason a reviewer can check.
A stale allowlist entry (one that no longer matches) is itself a failure.

Sabotage (2026-10-28, ``docs/sabotage-procedure.md``), each restored byte-identical
(``cmp``) and re-run green afterwards:

1. Leak: the ``Store.check`` docstring (``src/zanzibar/store/_store.py``) got
   ``" See TK_999."`` (written TK_999 here, so `tests/test_tasktool.py` does not read it as a
   citation of a task that does not exist; the injected and observed token was TK then 999). Observed::

       E       AssertionError: internal ids / private paths in public docstrings:
       E           zanzibar.store._store.Store.check: 'TK_999'
       FAILED tests/test_tk169_public_docstrings.py::test_no_internal_ids_or_private_paths_in_public_docstrings
       1 failed, 2 passed in 0.29s

2. Every other pattern at once: the same docstring got
   ``" See docs/x.md, ZT-P0-1, R6-4, ASK-1 (2026-09-12b)."``. Observed::

       E           zanzibar.store._store.Store.check: '2026-09-12b'
       E           zanzibar.store._store.Store.check: 'ASK-1'
       E           zanzibar.store._store.Store.check: 'R6-4'
       E           zanzibar.store._store.Store.check: 'ZT-P'
       E           zanzibar.store._store.Store.check: 'docs/'
       1 failed, 2 passed in 0.30s

3. Walker: ``return`` inserted as the first statement of ``_public_docstrings``, so it
   yields nothing. The leak test stayed GREEN (that is why the tripwire exists); the
   tripwire went red::

       E       AssertionError: the walk visited 0 docstrings; floor is 180
       E       assert 0 >= 180
       E        +  where 0 = len([])
       1 failed, 2 passed in 0.24s
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
import re

import zanzibar

PACKAGES = (
    'zanzibar',
    'zanzibar.graphindex',
    'zanzibar.setengine',
    'zanzibar.schema',
    'zanzibar.store',
)

# Each pattern is anchored so ordinary prose does not trip it: ids need their exact
# prefix shape; paths need a leading boundary that rules out URLs and dotted names.
LEAK_PATTERNS = (
    re.compile(r'\bTK\d+\b'),
    re.compile(r'\bZT-[A-Z0-9]'),
    re.compile(r'\bR6-\d'),
    re.compile(r'\bASK-\d'),
    re.compile(r'(?<![\w./:-])(?:docs|formal|tests|scripts|\.scratch)/'),
    re.compile(r'(?<![\w-])20\d\d-\d\d-\d\d[a-z]?(?![\w-])'),
)

# (qualified owner, matched text) -> reason. Empty on purpose; see module docstring.
ALLOWLIST: dict[tuple[str, str], str] = {}

# Floor for the walk: 188 docstrings over 34 modules measured 2026-10-28. Slack of 8 so
# deleting a stale docstring is not a gate break; a lost subpackage or an empty walk is.
MIN_DOCSTRINGS = 180


def _is_ours(obj) -> bool:
    module = getattr(obj, '__module__', None) or ''
    return module == 'zanzibar' or module.startswith('zanzibar.')


def _public_modules():
    names = list(PACKAGES)
    for info in pkgutil.walk_packages(zanzibar.__path__, prefix='zanzibar.'):
        if any(part.startswith('_') for part in info.name.split('.')):
            continue
        names.append(info.name)
    seen = set()
    for name in names:
        if name not in seen:
            seen.add(name)
            yield name, importlib.import_module(name)


def _class_members(cls):
    """Public members defined on ``cls`` or on a zanzibar base class."""
    for klass in cls.__mro__:
        if not _is_ours(klass):
            continue
        for name, raw in vars(klass).items():
            if name.startswith('_'):
                continue
            if isinstance(raw, (staticmethod, classmethod)):
                raw = raw.__func__
            if isinstance(raw, property) or inspect.isfunction(raw):
                yield f'{cls.__module__}.{cls.__qualname__}.{name}', raw


def _public_docstrings():
    """Yield ``(owner, docstring)`` for every public docstring a user can reach."""
    seen_ids = set()

    def emit(owner, obj):
        if id(obj) in seen_ids:
            return
        seen_ids.add(id(obj))
        doc = getattr(obj, '__doc__', None)
        if isinstance(doc, str) and doc.strip():
            yield owner, doc

    for modname, module in _public_modules():
        yield from emit(modname, module)
    for pkg in PACKAGES:
        module = importlib.import_module(pkg)
        for name in getattr(module, '__all__', ()):
            obj = getattr(module, name)
            if not _is_ours(obj) or inspect.ismodule(obj):
                continue
            owner = f'{obj.__module__}.{getattr(obj, "__qualname__", name)}'
            yield from emit(owner, obj)
            if inspect.isclass(obj):
                for member_owner, member in _class_members(obj):
                    yield from emit(member_owner, member)


def _leaks():
    hits = []
    for owner, doc in _public_docstrings():
        for pattern in LEAK_PATTERNS:
            for match in pattern.finditer(doc):
                hits.append((owner, match.group(0)))
    return hits


def test_walk_visits_the_public_surface():
    """Tripwire: a walker that visits nothing passes the leak test vacuously."""
    docs = list(_public_docstrings())
    assert len(docs) >= MIN_DOCSTRINGS, (
        f'the walk visited {len(docs)} docstrings; floor is {MIN_DOCSTRINGS}')
    owners = {owner for owner, _ in docs}
    # Spot pins: one class docstring, one method, one module docstring.
    for required in ('zanzibar.store._store.Store', 'zanzibar.store._store.Store.check',
                     'zanzibar.graphindex.invariants'):
        assert required in owners, f'walk missed {required}'


def test_no_internal_ids_or_private_paths_in_public_docstrings():
    hits = _leaks()
    unexpected = sorted({h for h in hits if h not in ALLOWLIST})
    assert not unexpected, 'internal ids / private paths in public docstrings:\n' + '\n'.join(
        f'  {owner}: {text!r}' for owner, text in unexpected)


def test_allowlist_entries_are_live():
    hits = set(_leaks())
    stale = [key for key in ALLOWLIST if key not in hits]
    assert not stale, f'allowlist entries that no longer match anything: {stale}'
