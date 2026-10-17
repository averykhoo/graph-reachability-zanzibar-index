"""TK153 F3: what ``help()`` shows a user, and every message the package raises, is ASCII.

The 0.0.5 install trial found ``U+00A7`` and ``U+2464`` in ``advance_index``'s docstring:
``print(inspect.getdoc(advance_index))`` with stdout redirected on Windows (a ``cp1252``
console codepage) raised ``UnicodeEncodeError`` -- reading the documentation crashed the
reader. The same holds for an exception message printed to such a stream, so both surfaces
are pinned:

1. **Public docstrings**: exactly the surface ``tests/test_tk123_no_internal_refs.py``
   scans (every public module, public class / function, public method and ``__init__``),
   read from the AST of every module under ``src/zanzibar/``.
2. **Runtime message strings**: every string constant inside a ``raise``, a
   ``warnings.warn`` / logger call, an exception's ``super().__init__(...)`` and a
   ``__str__`` return (the same sites that test reads).

Private docstrings and ``#`` comments are not read: ``help()`` never shows them.

Sabotage (2026-10-17, TK153 agent; runner ``.scratch/ultracode-2026-10-17/tk153-probes/
sabotage.py``, gitignored, so this docstring is the record). One asserted-unique anchor per
mutation, the file restored byte-for-byte and sha256-checked after each; this module only
(3 tests), ``-p no:cacheprovider``. Literal output, every one RED:

- SB7 ``U+2208`` put back into ``WildcardIndex.lookup``'s docstring
  (``graphindex/wildcard.py``): ``1 failed, 2 passed``; ``graphindex/wildcard.py
  WildcardIndex.lookup [doc] ['U+2208']``.
- SB8 ``U+2014`` added to the ``MissingDeltaProcessor`` message (``store/apply.py``):
  ``1 failed, 2 passed``; ``store/apply.py _require_proc_for_boolean_schema [raise]
  ['U+2014']``.
- SB9 ``U+2464`` put back into ``advance_index``'s docstring (the trial's own repro):
  ``2 failed, 1 passed`` (``test_public_docstrings_are_ascii`` and
  ``test_advance_index_help_prints_on_cp1252``).
"""
from __future__ import annotations

import ast
import inspect

from tests.test_tk123_no_internal_refs import _message_sites, _modules, _public_path, _strings


def _non_ascii(s: str) -> list[str]:
    return sorted({f'U+{ord(c):04X}' for c in s if ord(c) > 127})


def _help_visible(name: str) -> bool:
    """``pydoc.visiblename`` for a class member: a dunder (``__str__``, ``__repr__``) is
    rendered by ``help()``, a ``_single`` private name is not."""
    return (name.startswith('__') and name.endswith('__')) or not name.startswith('_')


def _class_doc_targets(prefix: str, cls: ast.ClassDef):
    yield prefix, cls
    for m in cls.body:
        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and _help_visible(m.name):
            yield f'{prefix}.{m.name}', m
        elif isinstance(m, ast.ClassDef) and _help_visible(m.name):
            yield from _class_doc_targets(f'{prefix}.{m.name}', m)


def _public_doc_targets(rel: str, tree: ast.Module):
    # TK153 review (2026-10-17): this used to read only ``__init__`` among the dunders and
    # no nested class, but ``help()`` renders both (``__str__`` / ``__repr__`` docstrings,
    # a nested class's methods), so a non-ASCII character there would have brought the F3
    # crash back with this pin green. ``test_the_pin_reads_what_help_renders`` pins the
    # wider reach.
    if _public_path(rel):
        yield '<module>', tree
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith('_'):
            yield node.name, node
        elif isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
            yield from _class_doc_targets(node.name, node)


def non_ascii_docstrings() -> list[str]:
    out = []
    for _path, rel, tree in _modules():
        for q, node in _public_doc_targets(rel, tree):
            doc = ast.get_docstring(node, clean=False)
            if doc and _non_ascii(doc):
                out.append(f'{rel} {q} [doc] {_non_ascii(doc)}')
    return sorted(out)


def non_ascii_messages() -> list[str]:
    out = []
    for _path, rel, tree in _modules():
        for q, kind, target in _message_sites(tree):
            for s in _strings(target):
                if _non_ascii(s):
                    out.append(f'{rel} {q} [{kind}] {_non_ascii(s)}')
    return sorted(set(out))


def test_public_docstrings_are_ascii():
    bad = non_ascii_docstrings()
    assert bad == [], f'{len(bad)} public docstring(s) carry non-ASCII:\n' + '\n'.join(bad)


def test_runtime_messages_are_ascii():
    bad = non_ascii_messages()
    assert bad == [], f'{len(bad)} message string(s) carry non-ASCII:\n' + '\n'.join(bad)


def test_advance_index_help_prints_on_cp1252():
    """The trial's literal repro, on the imported object rather than the AST."""
    from zanzibar.store.apply import advance_index
    inspect.getdoc(advance_index).encode('cp1252')


_PROBE_SRC = (
    'class PublicThing:\n'
    '    """ok"""\n'
    '    def __str__(self):\n'
    '        """section \\u00a7 sign"""\n'
    '        return "x"\n'
    '    def __repr__(self):\n'
    '        """circled \\u2464"""\n'
    '        return "y"\n'
    '    def _hidden(self):\n'
    '        """private \\u2014 help() hides it"""\n'
    '    class Nested:\n'
    '        def go(self):\n'
    '            """nested \\u2208"""\n'
)


def test_the_pin_reads_what_help_renders(monkeypatch):
    """The INSTRUMENT check: a synthetic public class whose ``__str__``, ``__repr__`` and
    nested-class method docstrings carry non-ASCII must be caught, its ``_hidden``
    method (which ``help()`` does not render) must not, and ``pydoc`` must agree.

    Sabotage (2026-10-17, TK153 review agent; runner ``.scratch/ultracode-2026-10-17/
    tk153-review2-sabotage.py`` SB-pin-old-filter, gitignored, so this is the record):
    restoring the old member filter (``not m.name.startswith('_') or m.name ==
    '__init__'``, no nested-class recursion), this module only: ``1 failed, 3 passed``;
    ``assert [] == ["store/fake_...] ['U+00A7']"]`` / ``Right contains 3 more items, first
    extra item: "store/fake_public.py PublicThing.Nested.go [doc] ['U+2208']"``. Restored
    byte-for-byte (sha256-checked)."""
    import pydoc
    import sys
    import types
    tree = ast.parse(_PROBE_SRC)
    mod = sys.modules[__name__]
    monkeypatch.setattr(mod, '_modules', lambda: [(None, 'store/fake_public.py', tree)])
    seen = non_ascii_docstrings()
    assert seen == [
        "store/fake_public.py PublicThing.Nested.go [doc] ['U+2208']",
        "store/fake_public.py PublicThing.__repr__ [doc] ['U+2464']",
        "store/fake_public.py PublicThing.__str__ [doc] ['U+00A7']",
    ]
    fake = types.ModuleType('fake_public')
    exec(_PROBE_SRC, fake.__dict__)
    # help(PublicThing) lists Nested only as an attribute; help(PublicThing.Nested) -- one
    # attribute access away -- renders its methods, so the pin reads both.
    rendered = (pydoc.render_doc(fake.PublicThing, renderer=pydoc.plaintext)
                + pydoc.render_doc(fake.PublicThing.Nested, renderer=pydoc.plaintext))
    assert '—' not in rendered      # the _hidden method: help() does not show it
    assert {c for c in rendered if ord(c) > 127} == {'§', '⑤', '∈'}
