"""Every refused schema shape explains WHY and what to write INSTEAD, at the refusal.

User instruction 2026-09-27 (TK108): *"whenever we refuse a shape can there be a comment in
the parser that explains why and the alternative"*. The convention is a ``#`` block directly
above the refusing ``raise`` (or the ``if`` guarding it), in every parser that refuses::

    # REFUSED SHAPE (<origin id>): <what is refused>.
    # WHY: <why>.
    # INSTEAD: <a DSL rewrite that parses>   -- or --   # INSTEAD: none -- <reason>.

A later refusal in the same function may say ``WHY/INSTEAD: see above``.
`CLAUDE.md` § Gotchas carries the rule; the worked example is
`src/zanzibar/schema/parser.py::_validate_tuplesets_direct`.

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

SABOTAGE (2026-09-27, literal output; each on `src/zanzibar/schema/`, anchor asserted,
file restored byte-for-byte and sha256-checked):

- S1, the TK108 block loses its ``INSTEAD`` line::

      FAILED ...::test_every_refused_shape_block_says_why_and_instead[src/zanzibar/schema/]
      1 failed, 8 passed

- S2, the ASK-1 undeclared-tupleset block deleted whole (3 comment lines). Rule 1 does NOT
  see this (another header sits above it in the same function); the floor does, which is
  why the floor exists::

      FAILED ...::test_refused_shape_blocks_meet_the_floor[src/zanzibar/schema/]
      1 failed, 8 passed

- S3, a new ``_validate_new_shape`` that raises with no comment::

      FAILED ...::test_every_in_scope_refusal_has_a_refused_shape_comment[src/zanzibar/schema/]
      1 failed, 8 passed
"""
from __future__ import annotations

import ast
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIB = 'src/zanzibar/schema/'


def _schema_files() -> tuple[str, ...]:
    """EVERY module of the schema package, globbed (TK120, 2026-10-06). This was a fixed
    entry naming the one-file schema module; after its split into `src/zanzibar/schema/` a
    refusal in a new or renamed submodule would have escaped the scan with the gate green.

    Scope is unchanged by the glob: the schema layer, plus the two fixed files below. A glob
    over the WHOLE library was tried and rejected: it pulls in
    `graphindex/wildcard.py::_reject_star_self_edge` / `_reject_latent_star_cycle`, which
    refuse WRITES that would close a data cycle (explained in their docstrings), not schema
    shapes, so the user rule this file enforces does not apply to them."""
    return tuple(sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / LIB).rglob('*.py')
                        if '__pycache__' not in p.parts))


FILES = _schema_files() + ('tests/oracle.py', 'src/zanzibar/setengine/engine.py')
SHAPE_EXCEPTIONS = frozenset({'UnsupportedByGraphIndex', 'CyclicDerivedDependency'})
SHAPE_FUNCTION_PREFIXES = ('_validate_', '_reject_')
HEADER = 'REFUSED SHAPE'

#: Measured 2026-09-27 (`grep -c "REFUSED SHAPE"` per file, after TK108's sweep). Equal to
#: the live count on purpose: adding a block is free, removing one must be a reviewed edit.
#: Re-measured 2026-10-03e after P23 (+1 product `_validate_declared_name`; +4 oracle: that
#: twin, duplicate type, duplicate relation, `.` in a declared name): 33 / 15 / 1.
#: Re-measured 2026-10-04 after TK114 (+1 product, +1 oracle: `_validate_stratified_negation`
#: in each): 34 / 16 / 1.
#: Re-measured 2026-10-04 after TK115 (+3 product, JSON front end only -- the oracle has no
#: JSON front end: `_reject_duplicate_json_keys`, `_validate_json_wildcard`,
#: `_validate_json_round_trip`): 37 / 16 / 1.
#: Re-keyed 2026-10-06 (TK120): the schema module's floor is now per PACKAGE, because it
#: was split into submodules and a per-submodule floor would only track where code happens
#: to sit. Same count as before the split (37, `header_blocks` summed over the glob).
#: Re-measured 2026-10-08 after TK124 (+2 schema package: `parser.py::_validate_declares_a_type`
#: and `json_frontend.py::_validate_json_declares_a_type`; +1 oracle: its
#: `_validate_declares_a_type` twin): 39 / 17 / 1.
#: Re-measured 2026-10-08 after the TK127 review follow-up (types but no relation: +2 schema
#: package, the second block in `parser.py::_validate_declares_a_type` and
#: `json_frontend.py::_validate_json_declares_a_relation`; +1 oracle, the second block in its
#: twin): 41 / 18 / 1.
MIN_HEADERS = {LIB: 41, 'tests/oracle.py': 18, 'src/zanzibar/setengine/engine.py': 1}
#: In-scope raises the scope rule must keep seeing (anti-vacuity, replacing the per-file
#: "no in-scope raise found" assert, which cannot hold per SUBMODULE). Measured 2026-10-06
#: with `in_scope_raises`: 25 over the schema package (boolean 2, compiler 11,
#: json_frontend 3, parser 9); the oracle keeps its old per-file >= 1. Re-measured
#: 2026-10-08 after TK124: 27 (json_frontend 4, parser 10). Re-measured 2026-10-08 after
#: the TK127 follow-up: 29 (json_frontend 5, parser 11).
MIN_IN_SCOPE_RAISES = {LIB: 29, 'tests/oracle.py': 1}


def _group(rel: str) -> str:
    return LIB if rel.startswith(LIB) else rel


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


def test_the_scope_rule_still_sees_refusals():
    for group, floor in MIN_IN_SCOPE_RAISES.items():
        n = sum(len(list(in_scope_raises(f))) for f in FILES if _group(f) == group)
        assert n >= floor, (f'{group}: {n} in-scope raises, floor {floor} -- the scope rule '
                            f'no longer sees the refusals it is meant to police')


@pytest.mark.parametrize('rel', FILES)
def test_every_in_scope_refusal_has_a_refused_shape_comment(rel):
    missing = _missing_headers(rel)
    assert not missing, ('refusal(s) with no "# REFUSED SHAPE ... WHY ... INSTEAD" comment '
                         '(user rule 2026-09-27, CLAUDE.md sec Gotchas):\n  '
                         + '\n  '.join(missing))


@pytest.mark.parametrize('rel', FILES)
def test_every_refused_shape_block_says_why_and_instead(rel):
    bad = _incomplete_blocks(rel)
    assert not bad, 'REFUSED SHAPE block(s) missing WHY or INSTEAD:\n  ' + '\n  '.join(bad)


@pytest.mark.parametrize('group', sorted(MIN_HEADERS))
def test_refused_shape_blocks_meet_the_floor(group):
    n = sum(1 for f in FILES if _group(f) == group for _ in header_blocks(f))
    assert n >= MIN_HEADERS[group], (
        f'{group}: {n} REFUSED SHAPE blocks, floor {MIN_HEADERS[group]} -- a refusal lost its '
        f'explanation. If the refusal itself was removed, lower the floor deliberately.')
