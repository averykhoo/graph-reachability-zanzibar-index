"""TK123 item 14: what the wheel SHOWS a user carries no repo-internal references.

The published ``zanzibar-index`` wheel ships ``src/zanzibar/`` only. It has no task tracker,
no ``docs/``, ``tests/`` or ``formal/`` directory and no spec documents, so a task id
(``TK123``, ``ZT-P0-1``, ``ASK-2``, ``P23``, ``R6-19``), a repo path, a spec section
(``spec §8.1``) or an invariant id (``I13``) in a message or in ``help()`` output points a
user at something they cannot open. Provenance belongs in ``#`` comments, which this test
does not read.

Two surfaces are scanned, both from the AST of every module under ``src/zanzibar/``:

1. **Runtime strings**: every string constant (f-string parts included) inside a ``raise``
   statement, a ``warnings.warn(...)`` call, or a logger call (``_log`` / ``log`` /
   ``logger`` / ``logging`` ``.debug/.info/.warning/.error/.exception/.critical``), in ANY
   function, private ones included -- a private helper's message reaches the user too.
2. **Public docstrings**, i.e. what ``help()`` shows: the docstring of every public module
   (no ``_``-prefixed path component; package ``__init__`` included), of every public class
   and function in it, of every public method (and ``__init__``) of a public class. A class
   defined in a private module (``store/_store.py``) counts when the package re-exports it,
   so private MODULES are scanned for their public classes/functions too.

The allowlist is explicit and keyed by ``(file, qualname)``; each entry says why.

Sabotage (2026-10-15): appending ``' See TK-999.'`` with the hyphen dropped (written hyphenated here because
``tests/test_tasktool.py::test_shipped_config_is_measured_not_an_example`` refuses an
unresolvable ticket-shaped token anywhere outside ``tasks/``) to the ``ClosureFanoutExceeded`` message
in ``graphindex/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl`` turned
``test_runtime_strings_carry_no_internal_refs`` red (``graphindex/core.py ...
_add_direct_edge_unsafe_impl [raise] 'TK-999'``, hyphen dropped); adding ``(see docs/x.md)`` to the
``Store.check`` docstring turned ``test_public_docstrings_carry_no_internal_refs`` red
(``store/_store.py Store.check [doc] 'docs/'``). Both restored green.

Review fix (2026-10-15): the scanner first read only raise / warn / log sites, so a message
an exception class builds in its own ``super().__init__(...)`` escaped it --
``PersistedSchemaRefused`` shipped ``(TK137)`` twice that way. It now also reads every
``super().__init__`` / ``Base.__init__`` call and every ``__str__`` return. Sabotage:
re-inserting ``(TK137)`` into ``store/schema_io.py::PersistedSchemaRefused.__init__``
turned ``test_runtime_strings_carry_no_internal_refs`` red (``store/schema_io.py
PersistedSchemaRefused.__init__ [super-init] 'TK137'``; 1 failed, 2 passed); restored green.
"""
from __future__ import annotations

import ast
import pathlib
import re

PKG = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'zanzibar'

#: One alternation per leak class. ``\b`` keeps ordinary words (``TKinter``, ``Pi``) out.
LEAK = re.compile(
    r'\bTK\d+'                      # task rows
    r'|\bZT-[A-Z0-9]'               # review findings
    r'|\bASK-\d'                    # user-decision rows
    r'|\bR\d+-\d+'                  # perf rows (R6-19)
    r'|\bP\d{1,2}[a-z]?\b'          # plan items (P7, P23, P13)
    r'|\bN\d{1,2}\b'                # numbered review notes (N17)
    r'|\bI\d{1,2}\b'                # invariant ids (I1..I14)
    r'|\bH[123]\b'                  # lookup proof-sketch hypotheses
    r'|(?<![\w.])(?:docs|tests|formal|benchmarks|scripts)/'   # repo paths
    r'|\.lean\b|\bW4Fragment\b|\bdecision-\d+'                 # proof / decision refs
    r'|§|\bspec sec\b'                                         # spec sections
    r'|\bzero-trust review\b|\bblind-audit\b|\bR\d+-[A-Z]+\b|\bBROKEN-\d'  # review/trial ids
    r'|\bspec-deviations\b|\bCORRESPONDENCE\b'
)

_LOG_METHODS = {'debug', 'info', 'warning', 'warn', 'error', 'exception', 'critical'}
_LOGGERS = {'_log', 'log', 'logger', '_logger', 'logging', 'LOG'}

#: (file relative to src/zanzibar, qualname or '*' for every docstring in the file) ->
#: (regex the ALLOWED tokens fully match, why). Only that token class is excused.
ALLOW_DOC: dict[tuple[str, str], tuple[str, str]] = {
    # The invariant numbering I1..I14 is DEFINED in this module's own docstring, which the
    # wheel ships (help(zanzibar.graphindex.invariants)), so an id there resolves for a user;
    # tests/test_invariants_docstring_matches_body.py also REQUIRES check_invariants'
    # docstring to name the invariants it checks.
    ('graphindex/invariants.py', '*'): (r'I\d+', 'the module defines the invariant ids'),
    # The public API is NAMED after the Lean predicate it mirrors (w4_fragment_report,
    # W4FragmentReport): the name cannot be explained without saying it.
    ('schema/reports.py', '*'): (r'W4Fragment|\.lean', 'the API is named after W4Fragment'),
}
#: (file, qualname) -> (regex the ALLOWED tokens fully match, why). Only the named token
#: class is excused at that site; any other leak there is still red.
_CORRUPTION = (r'I\d+', 'an InvariantViolation is a corruption report, not a refusal: the '
               'invariant id is what the bug report must carry, and tests pin it '
               '(test_cascade_fixpoint_tier, test_invariants_derived, test_reg_tk91_*)')
ALLOW_RUNTIME: dict[tuple[str, str], tuple[str, str]] = {
    ('graphindex/core.py', 'ReachabilityIndex._add_db_edges_unsafe'): _CORRUPTION,
    ('graphindex/core.py', 'ReachabilityIndex._add_indirect_edges_batch_unsafe'): _CORRUPTION,
    ('graphindex/processor.py', 'DeltaProcessor._check_cascade_fixpoint'): _CORRUPTION,
    ('graphindex/processor.py', 'DeltaProcessor.audit_fixpoint'): _CORRUPTION,
}


def _modules():
    for path in sorted(PKG.rglob('*.py')):
        yield path, path.relative_to(PKG).as_posix(), ast.parse(path.read_text(encoding='utf-8'))


def _strings(node):
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            yield sub.value


def _is_message_call(call: ast.Call) -> bool:
    f = call.func
    if isinstance(f, ast.Attribute):
        if f.attr == 'warn' and isinstance(f.value, ast.Name) and f.value.id == 'warnings':
            return True
        if f.attr in _LOG_METHODS and isinstance(f.value, ast.Name) and f.value.id in _LOGGERS:
            return True
    return False


def _is_super_init(call: ast.Call) -> bool:
    """``super().__init__(...)`` or ``Base.__init__(self, ...)``: where an exception class
    builds the message its ``raise`` sites never spell out."""
    f = call.func
    if not (isinstance(f, ast.Attribute) and f.attr == '__init__'):
        return False
    v = f.value
    return ((isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == 'super')
            or isinstance(v, (ast.Name, ast.Attribute)))


def _message_sites(tree):
    """Yield (innermost qualname, kind, node) for every raise / warn / log call, every
    ``super().__init__(...)`` call (an exception's own message) and every ``return`` in a
    ``__str__`` method."""
    def walk(node, q):
        for child in ast.iter_child_nodes(node):
            cq = q
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                cq = child.name if q == '<module>' else f'{q}.{child.name}'
            if isinstance(child, ast.Raise) and child.exc is not None:
                yield cq, 'raise', child.exc
            elif isinstance(child, ast.Call) and _is_message_call(child):
                yield cq, 'warn/log', child
            elif isinstance(child, ast.Call) and _is_super_init(child):
                yield cq, 'super-init', child
            elif (isinstance(child, ast.Return) and child.value is not None
                    and cq.rsplit('.', 1)[-1] == '__str__'):
                yield cq, '__str__', child.value
            yield from walk(child, cq)
    yield from walk(tree, '<module>')


def runtime_leaks():
    out = []
    for _path, rel, tree in _modules():
        for q, kind, target in _message_sites(tree):
            allowed = ALLOW_RUNTIME.get((rel, q), ('(?!)', ''))[0]
            for s in _strings(target):
                for m in LEAK.finditer(s):
                    if not re.fullmatch(allowed, m.group(0)):
                        out.append(f'{rel} {q} [{kind}] {m.group(0)!r}: {s[:90]!r}')
    return sorted(set(out))


def _public_path(rel: str) -> bool:
    parts = rel[:-3].split('/')
    return all(not p.startswith('_') or p == '__init__' for p in parts)


def docstring_leaks():
    out = []
    for _path, rel, tree in _modules():
        targets = []
        if _public_path(rel):
            targets.append(('<module>', tree))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith('_'):
                targets.append((node.name, node))
            elif isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
                targets.append((node.name, node))
                for m in node.body:
                    if (isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and (not m.name.startswith('_') or m.name == '__init__')):
                        targets.append((f'{node.name}.{m.name}', m))
        for q, node in targets:
            doc = ast.get_docstring(node, clean=False)
            if not doc:
                continue
            allowed = ALLOW_DOC.get((rel, q), ALLOW_DOC.get((rel, '*'), ('(?!)', '')))[0]
            for m in LEAK.finditer(doc):
                if not re.fullmatch(allowed, m.group(0)):
                    out.append(f'{rel} {q} [doc] {m.group(0)!r}')
                    break
    return sorted(out)


def test_runtime_strings_carry_no_internal_refs():
    leaks = runtime_leaks()
    assert leaks == [], f'{len(leaks)} runtime message(s) cite repo-internal refs:\n' + '\n'.join(leaks)


def test_public_docstrings_carry_no_internal_refs():
    leaks = docstring_leaks()
    assert leaks == [], f'{len(leaks)} public docstring(s) cite repo-internal refs:\n' + '\n'.join(leaks)


def test_the_scanner_sees_what_it_claims_to():
    """Instrument control: the scanner must actually reach both surfaces, so a refactor
    that makes it scan nothing cannot pass vacuously. The pattern must catch each leak
    class, and the allowlisted docstring must really carry the ids it is excused for."""
    for sample in ('see TK123', 'ZT-P0-1', 'ASK-2', 'R6-19', 'P23', 'N17', 'I13',
                   'docs/x.md', 'tests/test_x.py', 'formal/', 'FullScope.lean', 'W4Fragment',
                   'spec §8.1', 'decision-15', 'spec-deviations'):
        assert LEAK.search(sample), sample
    for clean in ('TKinter', 'Pi', 'API', 'I/O', 'ZT', 'type#relation', 'IndexStore',
                  'zanzibar.docs', 'H100'):
        assert not LEAK.search(clean), clean
    sites = {(r, q, k) for _p, r, t in _modules() for q, k, _n in _message_sites(t)}
    assert ('store/schema_io.py', 'PersistedSchemaRefused.__init__', 'super-init') in sites
    assert ('store/schema_io.py', 'StoreNotFound.__str__', '__str__') in sites
    n_raise = sum(1 for _p, _r, t in _modules() for n in ast.walk(t) if isinstance(n, ast.Raise))
    assert n_raise > 200, n_raise
    n_docs = 0
    for _p, rel, tree in _modules():
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and not node.name.startswith('_') and ast.get_docstring(node):
                n_docs += 1
    assert n_docs > 40, n_docs
    tree = ast.parse((PKG / 'graphindex/invariants.py').read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'check_invariants')
    assert re.search(r'\bI7\b', ast.get_docstring(fn)), 'the invariants allowlist is stale'
