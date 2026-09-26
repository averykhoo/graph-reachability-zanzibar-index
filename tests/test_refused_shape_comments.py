"""Every refused schema shape explains WHY and what to write INSTEAD, at the refusal.

User instruction 2026-09-27 (TK108): *"whenever we refuse a shape can there be a comment in
the parser that explains why and the alternative"*. The convention is a ``#`` block directly
above the refusing ``raise`` (or the ``if`` guarding it), in every parser that refuses::

    # REFUSED SHAPE (<origin id>): <what is refused>.
    # WHY: <why>.
    # INSTEAD: <a DSL rewrite that parses>   -- or --   # INSTEAD: none -- <reason>.

A later refusal in the same function may say ``WHY/INSTEAD: see above``.
`CLAUDE.md` § Gotchas carries the rule; the worked example is
`zanzibar_utils_v1.py::_validate_tuplesets_direct`.

What this module enforces, and its limit:

1. **Every IN-SCOPE raise has a header** between its innermost function's ``def`` and itself.
   In scope: any ``raise UnsupportedByGraphIndex`` / ``raise CyclicDerivedDependency`` (those
   classes ARE shape refusals), and any ``raise`` in a function named ``_validate_*`` or
   ``_reject_*``, in `FILES`. A new refusal of either kind without a comment is red.
2. **Every header block carries WHY and INSTEAD** (or the ``see above`` form), within its
   contiguous comment lines.
3. **Per-file header floors with ZERO headroom** (`MIN_HEADERS`, the repo's floor
   discipline): deleting a block is red even where rule 1 cannot see it.

LIMIT: a plain ``raise ValueError`` refusal added to a function outside the naming
convention (e.g. inside ``_parse_schema_ast_unchecked``) is caught by nothing here except a
reviewer. The 2026-09-27 census (`docs/tk108-userset-tuplesets-2026-09-27.md` § 4) listed
the parse-level refusals that live there, and each carries a block today.

SABOTAGE (2026-09-27, literal output; each on `zanzibar_utils_v1.py`, anchor asserted,
file restored byte-for-byte and sha256-checked):

- S1, the TK108 block loses its ``INSTEAD`` line::

      FAILED ...::test_every_refused_shape_block_says_why_and_instead[zanzibar_utils_v1.py]
      1 failed, 8 passed

- S2, the ASK-1 undeclared-tupleset block deleted whole (3 comment lines). Rule 1 does NOT
  see this (another header sits above it in the same function); the floor does, which is
  why the floor exists::

      FAILED ...::test_refused_shape_blocks_meet_the_floor[zanzibar_utils_v1.py]
      1 failed, 8 passed

- S3, a new ``_validate_new_shape`` that raises with no comment::

      FAILED ...::test_every_in_scope_refusal_has_a_refused_shape_comment[zanzibar_utils_v1.py]
      1 failed, 8 passed
"""
from __future__ import annotations

import ast
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILES = ('zanzibar_utils_v1.py', 'tests/oracle.py', 'setengine/engine.py')
SHAPE_EXCEPTIONS = frozenset({'UnsupportedByGraphIndex', 'CyclicDerivedDependency'})
SHAPE_FUNCTION_PREFIXES = ('_validate_', '_reject_')
HEADER = 'REFUSED SHAPE'

#: Measured 2026-09-27 (`grep -c "REFUSED SHAPE"` per file, after TK108's sweep). Equal to
#: the live count on purpose: adding a block is free, removing one must be a reviewed edit.
MIN_HEADERS = {'zanzibar_utils_v1.py': 32, 'tests/oracle.py': 11, 'setengine/engine.py': 1}


def _source(rel: str) -> tuple[str, list[str]]:
    src = (ROOT / rel).read_text(encoding='utf-8')
    return src, src.splitlines()


def _innermost_functions(tree: ast.AST):
    """``(function, raise)`` pairs, each raise attributed to its INNERMOST function."""
    def walk(node, fn):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield from walk(child, child)
            else:
                if isinstance(child, ast.Raise) and fn is not None:
                    yield fn, child
                yield from walk(child, fn)
    yield from walk(tree, None)


def _exc_name(r: ast.Raise) -> str:
    exc = r.exc.func if isinstance(r.exc, ast.Call) else r.exc
    return getattr(exc, 'id', None) or getattr(exc, 'attr', None) or ''


def in_scope_raises(rel: str):
    src, _ = _source(rel)
    for fn, r in _innermost_functions(ast.parse(src)):
        if r.exc is None:
            continue                          # bare re-raise
        if _exc_name(r) in SHAPE_EXCEPTIONS or fn.name.startswith(SHAPE_FUNCTION_PREFIXES):
            yield fn, r


def header_blocks(rel: str):
    """``(line_no, block_text)`` for every comment block containing the header."""
    _, lines = _source(rel)
    for i, line in enumerate(lines):
        s = line.strip()
        if not (s.startswith('#') and HEADER in s):
            continue
        block = [s]
        for nxt in lines[i + 1:]:
            t = nxt.strip()
            if not t.startswith('#') or HEADER in t:
                break
            block.append(t)
        yield i + 1, ' '.join(block)


def _missing_headers(rel: str) -> list[str]:
    _, lines = _source(rel)
    out = []
    for fn, r in in_scope_raises(rel):
        span = lines[fn.lineno - 1: r.lineno - 1]
        if not any(HEADER in l and l.strip().startswith('#') for l in span):
            out.append(f'{rel}::{fn.name}:{r.lineno} raise {_exc_name(r)}')
    return out


def _incomplete_blocks(rel: str) -> list[str]:
    out = []
    for n, text in header_blocks(rel):
        up = text.upper()
        if 'SEE ABOVE' in up and 'WHY' in up and 'INSTEAD' in up:
            continue
        if 'WHY' not in up or 'INSTEAD' not in up:
            out.append(f'{rel}:{n}: {text[:100]}')
    return out


@pytest.mark.parametrize('rel', FILES)
def test_every_in_scope_refusal_has_a_refused_shape_comment(rel):
    assert list(in_scope_raises(rel)) or rel == 'setengine/engine.py', \
        f'{rel}: no in-scope raise found -- the scope rule no longer sees this file'
    missing = _missing_headers(rel)
    assert not missing, ('refusal(s) with no "# REFUSED SHAPE ... WHY ... INSTEAD" comment '
                         '(user rule 2026-09-27, CLAUDE.md sec Gotchas):\n  '
                         + '\n  '.join(missing))


@pytest.mark.parametrize('rel', FILES)
def test_every_refused_shape_block_says_why_and_instead(rel):
    bad = _incomplete_blocks(rel)
    assert not bad, 'REFUSED SHAPE block(s) missing WHY or INSTEAD:\n  ' + '\n  '.join(bad)


@pytest.mark.parametrize('rel', FILES)
def test_refused_shape_blocks_meet_the_floor(rel):
    n = sum(1 for _ in header_blocks(rel))
    assert n >= MIN_HEADERS[rel], (
        f'{rel}: {n} REFUSED SHAPE blocks, floor {MIN_HEADERS[rel]} -- a refusal lost its '
        f'explanation. If the refusal itself was removed, lower the floor deliberately.')
