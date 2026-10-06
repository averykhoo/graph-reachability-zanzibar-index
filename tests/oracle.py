"""
Reference oracle for wildcard-aware Zanzibar reachability, now with boolean
operators (spec §3).

This is a deliberately naive, memoized evaluator over ``(schema, list_of_input_tuples)``.
It exists ONLY to serve as an independent ground truth for the materialized
``WildcardIndex`` (``zanzibar.graphindex``) and the set engine (``zanzibar.setengine``).

Independence contract (wildcard spec §4, restated):
  * imports NOTHING from ``zanzibar.graphindex`` / ``zanzibar.setengine`` (no DB, no edges, no bridges);
  * shares no *evaluation* logic and no *parser* with the production code -- it parses
    the OpenFGA DSL itself (``parse_schema_ast`` below), so a bug in the production
    schema parser cannot silently corrupt both sides of the validation matrix.

Evaluation is **pointwise** (spec §3): ``check`` answers one ``(subject, relation,
object)`` at a time by recursing over the AST. The subject is *fixed* for the whole
recursion; only the ``(object_type, object_name, relation)`` node changes, so a memo
keyed on that node (with an in-progress guard for recursive schemas) is the direct
analogue of the old intensional ``seen`` set. Booleans compose trivially:
``Union -> any(child)``, ``Intersection -> all(child)``, ``Exclusion -> base and not
subtract``.

Wildcard queries are answered **intensionally** (wildcard spec §4.2): a ``'*'`` query
asks "does a grant flow THROUGH the wildcard", not "does every concrete instance
happen to have access". Ghost entities (never mentioned in any tuple) work because the
universe is recomputed per query (tuple-mentioned names ∪ query endpoints) and markers
match by shape alone.

Star × boolean semantics (spec §3 -- the corner the set engine's MemberSet reproduces):

    query subject   A and B (Intersection)      A but not B (Exclusion)
    -------------   -----------------------      -----------------------
    '*'  (star)     star-covered in BOTH         star-covered in A and NOT star-covered in B
    concrete u      u in A and u in B            u in A and u not in B   (genuine pointwise)
    ghost   g       (same as concrete)           (same as concrete)

    So a concrete-only exclusion ("A but not bob") does NOT defeat a '*' query of A:
    the star is star-covered in A and bob's concrete removal is not a star in B.

Performance is irrelevant here; clarity is everything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import EllipsisType
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Input data
# ---------------------------------------------------------------------------

class OracleTuple(NamedTuple):
    """A single stored relation tuple. ``'...'`` is the bare subject predicate."""
    subject_predicate: str
    subject_type: str
    subject_name: str
    relation: str
    object_type: str
    object_name: str


def t(subject_predicate, subject_type, subject_name, relation, object_type, object_name) -> OracleTuple:
    """Convenience constructor that normalises the bare predicate (Ellipsis -> '...')."""
    return OracleTuple(_norm_pred(subject_predicate), subject_type, subject_name,
                       relation, object_type, object_name)


def _norm_pred(pred: str | EllipsisType) -> str:
    return '...' if (pred is Ellipsis or pred is None) else pred


# Public alias for the subject-predicate normaliser. The internal name keeps its
# leading underscore to avoid churn across this module's many call sites; external
# reusers (e.g. the conformance encoder, which intentionally borrows this oracle's
# independent parser) should import this public name instead of the private one.
norm_pred = _norm_pred


# ---------------------------------------------------------------------------
# Independent boolean-aware AST + parser (deliberately NOT the production parser)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ODirect:
    # each restriction is (type, predicate, wildcard); predicate '...' for bare entity
    restrictions: tuple[tuple[str, str, bool], ...]


@dataclass(frozen=True)
class OComputed:
    relation: str


@dataclass(frozen=True)
class OTTU:
    target_rel: str
    tupleset_rel: str


@dataclass(frozen=True)
class OUnion:
    children: tuple


@dataclass(frozen=True)
class OIntersection:
    children: tuple


@dataclass(frozen=True)
class OExclusion:
    base: object
    subtract: object


_OP_WORDS = ('or', 'and', 'but', 'not', 'from')


def _tokenize(body: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if c.isspace():
            i += 1
        elif c == '[':
            j = body.find(']', i)
            if j == -1:
                raise ValueError(f'unterminated [ in {body!r}')
            tokens.append(('bracket', body[i:j + 1]))
            i = j + 1
        elif c == ']':
            # a stray ']' would make the word branch scan zero characters and loop
            # forever (mirrors the production tokenizer's fix -- found blind-audit O4)
            raise ValueError(f'unmatched ] in {body!r}')
        elif c in '()':
            tokens.append(('lparen' if c == '(' else 'rparen', c))
            i += 1
        else:
            j = i
            while j < n and not body[j].isspace() and body[j] not in '()[]':
                j += 1
            assert j > i, f'tokenizer made no progress at {i} in {body!r}'
            tokens.append(('word', body[i:j]))
            i = j
    return tokens


def _parse_restrictions(bracket: str) -> tuple[tuple[str, str, bool], ...]:
    """Parse ``[user, group#member, user:*, group:*#member]`` into (type, pred, wildcard)."""
    inner = bracket[bracket.index('[') + 1:bracket.rindex(']')]
    out: list[tuple[str, str, bool]] = []
    # An empty entry is NOT skipped (TK109, 2026-10-03e). It used to be, so `[]` parsed as a
    # Direct nobody can write and `[user,,group#member]` as if the gap were not there, where
    # production refuses both. Now its type is '' and the charset check below refuses it.
    for part in (p.strip() for p in inner.split(',')):
        if '#' in part:
            left, pred = part.split('#', 1)
            pred = pred.strip()
            # mirrors the production parser (blind-audit O4): a second '#' or an
            # empty predicate silently misparsed before
            # REFUSED SHAPE (blind-audit S-5), the `.` case only (the rest is syntax): a `.`
            # in a userset predicate, `[doc#viewer.0]`. WHY: `.`-names are the compiler's
            # leaf predicates, a write handle into compiled state. INSTEAD: `[doc#viewer]`.
            # The bare sentinel `...` is exempt, as in production's
            # `_validate_ast_references`: `[group#...]` IS `[group]` (P23, 2026-10-03e).
            if not pred or '#' in pred or ('.' in pred and pred != '...'):
                raise ValueError(f'malformed userset restriction {part!r}')
        else:
            left, pred = part, '...'
        left = left.strip()
        typ, wild = (left[:-2].strip(), True) if left.endswith(':*') else (left, False)
        # A restriction's type must be an identifier (P23 twin of the production S-4 check):
        # `[use r]`, `[user: *]` and `[folder:)]` used to parse as restrictions to a type no
        # tuple can carry. No twin is needed for the USERSET relation: `[group#mem*er]` names
        # `group#mem*er`, which no declared name can be, so `_validate_consistency` refuses it.
        if _NAME_RE.fullmatch(typ) is None:
            raise ValueError(f'invalid subject type in restriction {part!r}')
        out.append((typ, pred, wild))
    return tuple(out)


class _Parser:
    """expr := chain ('but not' chain)? ; chain := unit (OP unit)* ; unit := '(' expr ')' | leaf."""

    def __init__(self, tokens, relation):
        self.tokens = tokens
        self.relation = relation
        self.pos = 0

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else (None, None)

    def parse(self):
        if not self.tokens:
            raise ValueError(f'relation {self.relation!r}: empty definition')
        expr = self._expr()
        if self.pos != len(self.tokens):
            raise ValueError(f'relation {self.relation!r}: trailing tokens')
        return expr

    def _expr(self):
        base = self._chain()
        if (self.pos + 1 < len(self.tokens)
                and self.tokens[self.pos] == ('word', 'but')
                and self.tokens[self.pos + 1] == ('word', 'not')):
            self.pos += 2
            return OExclusion(base, self._chain())
        return base

    def _chain(self):
        children = [self._unit()]
        op = None
        while True:
            kind, text = self._peek()
            if kind == 'word' and text in ('or', 'and'):
                if op is None:
                    op = text
                elif op != text:
                    # REFUSED SHAPE: `or` and `and` mixed without parentheses. WHY: the
                    # grammar gives them no relative precedence, so any reading would be a
                    # guess.
                    # INSTEAD: `(a or b) and c` or `a or (b and c)`.
                    raise ValueError(f'relation {self.relation!r}: mixed or/and without parens')
                self.pos += 1
                children.append(self._unit())
            else:
                break
        if op is None:
            return children[0]
        return OUnion(tuple(children)) if op == 'or' else OIntersection(tuple(children))

    def _unit(self):
        kind, _ = self._peek()
        if kind == 'lparen':
            self.pos += 1
            expr = self._expr()
            if self._peek()[0] != 'rparen':
                raise ValueError(f'relation {self.relation!r}: expected )')
            self.pos += 1
            return expr
        return self._leaf()

    def _leaf(self):
        kind, text = self._peek()
        if kind == 'bracket':
            self.pos += 1
            return ODirect(_parse_restrictions(text))
        if kind == 'word':
            if text in _OP_WORDS:
                raise ValueError(f'relation {self.relation!r}: unexpected {text!r}')
            self.pos += 1
            if self._peek() == ('word', 'from'):
                self.pos += 1
                k, t3 = self._peek()
                if k != 'word' or t3 in _OP_WORDS:
                    raise ValueError(f'relation {self.relation!r}: expected relation after from')
                self.pos += 1
                return OTTU(text, t3)
            return OComputed(text)
        raise ValueError(f'relation {self.relation!r}: unexpected end')


def parse_schema_ast(text: str) -> dict[tuple[str, str], object]:
    """Parse the DSL into ``{(type, relation): OExpr}`` (boolean-aware; drives evaluation),
    refusing a schema that is not self-consistent (``_validate_consistency``)."""
    ast = parse_schema_ast_unchecked(text)
    _validate_consistency(ast)
    _validate_tuplesets_direct(ast)
    _validate_stratified_negation(ast)
    return ast


def parse_schema_ast_unchecked(text: str) -> dict[tuple[str, str], object]:
    """``parse_schema_ast`` without the self-consistency refusal. The conformance encoder
    (``formal/conformance/encode.py::schema_to_json``) uses it: it is a translator, and
    Lean decides admission for itself, so it must be able to send Lean a schema this
    parser would refuse."""
    ast: dict[tuple[str, str], object] = {}
    current_type: str | None = None
    seen_types: set[str] = set()
    for raw in text.strip().splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        # The line head is the first WHITESPACE-delimited word, as in production: testing
        # `startswith('type ')` skipped `type<TAB>folder` and `define<TAB>viewer: ...` (P23).
        words = line.split()
        head = words[0]
        if head in ('model', 'schema', 'relations'):
            continue
        if head == 'type':
            if len(words) != 2:
                raise ValueError(f'malformed type declaration: {line!r}')
            current_type = words[1]
            _validate_declared_name('type', current_type)
            # REFUSED SHAPE (blind-audit S-6, oracle twin added by P23): a second `type X`
            # block. WHY: merging it silently rewrote the first block's relations.
            # INSTEAD: put every relation of the type under ONE `type doc` block.
            if current_type in seen_types:
                raise ValueError(f'duplicate type declaration: {current_type!r}')
            seen_types.add(current_type)
        elif head == 'define':
            if current_type is None:
                raise ValueError('relation defined outside of a type')
            # No colon: the name is then the whole rest of the line (`viewer [user]`, refused
            # by the charset below) or the body is empty (refused by `_Parser.parse`).
            name, _, body = line[len('define'):].strip().partition(':')
            name = name.strip()
            # Independent empty-name refusal (TK55, 2026-09-06). The production parser
            # has the same check; this one is NOT shared with it (independence
            # contract above), so a regression in either parser is caught alone by
            # tests/test_reg_empty_relation_name.py.
            # REFUSED SHAPE (TK55): an empty relation name, `define : [user]`. WHY: no write
            # can land on '', yet a computed ref to it was reachable, and there the backends
            # answered differently. INSTEAD: name it, `define viewer: [user]`.
            if not name:
                raise ValueError(
                    f"type {current_type!r}: a declared relation name may not be empty "
                    f"({line!r})")
            # REFUSED SHAPE (boolean spec sec 3.2, oracle twin added by P23): `.` in a
            # declared relation name. WHY: `.` names the compiler's leaf predicates
            # (`<relation>.<index>`), so production refuses it, and an oracle that accepted
            # it refereed a schema the system never runs. INSTEAD: `define can_view: [user]`.
            if '.' in name:
                raise ValueError(
                    f"relation {name!r}: '.' is reserved for compiled leaf predicates and "
                    f"cannot appear in a declared relation name")
            _validate_declared_name('relation', name)
            # REFUSED SHAPE (TK105, oracle twin added by P23): a second `define viewer` in the
            # same type. WHY: this parser used to keep the LAST one, so the oracle (and the
            # conformance encoder, which reads it) tested a different schema than production,
            # which refuses it. INSTEAD: ONE `define` joining the arms,
            # `define viewer: [user] or editor`.
            if (current_type, name) in ast:
                raise ValueError(f'duplicate relation definition: {current_type}#{name}')
            ast[(current_type, name)] = _Parser(_tokenize(body.strip()), name).parse()
        else:
            # silently skipping an unrecognised line lost whole definitions (production's
            # blind-audit S-3; oracle twin added by P23)
            raise ValueError(f'unrecognized schema line: {line!r}')
    return ast


#: Independent copy of the write identifier charset (`src/zanzibar/schema/errors.py::IDENTIFIER_CHARSET`),
#: NOT imported, by the independence contract above. Anchored with `\Z`, never `$`
#: (`$` also matches before a trailing newline; ZT-P1-1 in production).
_NAME_RE = re.compile(r'[A-Za-z0-9_./@+=-]{1,256}\Z')


def _validate_declared_name(kind: str, name: str) -> None:
    """Independent twin of `src/zanzibar/schema/parser.py::_validate_declared_name` (P23, 2026-10-03e)."""
    # REFUSED SHAPE (P23): a declared type or relation name outside the write identifier
    # charset (`define *: ...`, `define can view: ...`, `type d#oc`). WHY: no write can land
    # on it, yet a computed or TTU arm can reach it, and there the backends split (a valid
    # write was refused through `define *: viewer but not blocked`). INSTEAD: name it inside
    # `[A-Za-z0-9_/@+=-]` (`.` also allowed in a TYPE name), e.g. `define can_view: [user]`.
    if _NAME_RE.fullmatch(name) is None:
        raise ValueError(f'declared {kind} name {name!r}: outside the write identifier charset')


def _oracle_nodes(expr):
    """Every node of ``expr``, through every operator."""
    yield expr
    if isinstance(expr, (OUnion, OIntersection)):
        for c in expr.children:
            yield from _oracle_nodes(c)
    elif isinstance(expr, OExclusion):
        yield from _oracle_nodes(expr.base)
        yield from _oracle_nodes(expr.subtract)


def _validate_consistency(ast) -> None:
    """Independent twin of the production self-consistency refusal (ASK-1, 2026-09-26).
    NOT shared with ``src/zanzibar/schema/parser.py::_validate_ast_consistency`` (independence
    contract above). Refused: a computed ref or TTU tupleset naming an undeclared relation
    on its own type; a TTU target declared on none of the tupleset's restriction types (on
    no type at all, when it has none); a ``[T#P]`` restriction with no ``T#P``; and any
    relation that reaches itself through computed / TTU-tupleset references."""
    edges = {}
    for (typ, rel), expr in ast.items():
        edges[(typ, rel)] = []
        for node in _oracle_nodes(expr):
            if isinstance(node, ODirect):
                for (rtype, rpred, _wild) in node.restrictions:
                    # REFUSED SHAPE (ASK-1): an undeclared `[T#P]`. WHY (all five refusals
                    # here): a dangling reference silently meant "empty" and a reference
                    # cycle was answered by a fixpoint; no headline theorem covers either,
                    # and OpenFGA refuses both.
                    # INSTEAD: declare `T#P`, or write `[T]` if the object itself was meant.
                    if rpred != '...' and (rtype, rpred) not in ast:
                        raise ValueError(f'{typ}#{rel}: undeclared restriction {rtype}#{rpred}')
            elif isinstance(node, OComputed):
                # REFUSED SHAPE (ASK-1): an undeclared computed ref. WHY: see above.
                # INSTEAD: declare it on the same type (`define editor: [user]`), or fix the
                # spelling.
                if (typ, node.relation) not in ast:
                    raise ValueError(f'{typ}#{rel}: undeclared relation {typ}#{node.relation}')
                edges[(typ, rel)].append((typ, node.relation))
            elif isinstance(node, OTTU):
                # REFUSED SHAPE (ASK-1): an undeclared tupleset. WHY: see above.
                # INSTEAD: declare the link on the same type, `define parent: [folder]`.
                if (typ, node.tupleset_rel) not in ast:
                    raise ValueError(f'{typ}#{rel}: undeclared tupleset {typ}#{node.tupleset_rel}')
                edges[(typ, rel)].append((typ, node.tupleset_rel))
                types = {r[0] for n in _oracle_nodes(ast[(typ, node.tupleset_rel)])
                         if isinstance(n, ODirect) for r in n.restrictions}
                types = types or {t for t, _r in ast}   # no restriction: any declared type
                # REFUSED SHAPE (ASK-1): a TTU target declared on no tupleset type. WHY: see
                # above.
                # INSTEAD: declare it on the parent type (`type folder` /
                # `define viewer: [user]`), or let the tupleset admit a type that has it.
                if all((t, node.target_rel) not in ast for t in types):
                    raise ValueError(f'{typ}#{rel}: {node.target_rel!r} is declared on no '
                                     f'type of tupleset {typ}#{node.tupleset_rel}')
    # A key is on a cycle iff it can reach itself; the schemas here are tiny, so a plain
    # reachability walk per key is the clearest form.
    for start in edges:
        seen, todo = set(), list(edges[start])
        while todo:
            k = todo.pop()
            # REFUSED SHAPE (ASK-1): a cycle of computed / TTU-tupleset references. WHY: see
            # above. INSTEAD: none for a pure alias loop (delete one direction); intended
            # recursion goes through STORED tuples, which stays legal:
            # `define member: [user, group#member]`,
            # `define viewer: [user] or viewer from parent`.
            if k == start:
                raise ValueError(f'{start[0]}#{start[1]} depends on itself through schema '
                                 f'references')
            if k not in seen:
                seen.add(k)
                todo.extend(edges[k])


def _validate_tuplesets_direct(ast) -> None:
    """Independent twin of ``src/zanzibar/schema/parser.py::_validate_tuplesets_direct`` (TK106,
    2026-09-26), NOT shared with it (independence contract above). A relation named as a
    TTU tupleset must be only type restrictions, alone or joined by ``or``: ``from`` walks
    stored tuples, so any other arm would be silently ignored. OpenFGA refuses it too.

    Its restrictions must also be bare or wildcard types, never a userset (TK108,
    2026-09-27): see the comment at the second refusal."""
    def direct_only(expr) -> bool:
        if isinstance(expr, ODirect):
            return True
        if isinstance(expr, OUnion):
            return all(direct_only(c) for c in expr.children)
        return False

    for (typ, rel), expr in ast.items():
        for node in _oracle_nodes(expr):
            if not (isinstance(node, OTTU) and (typ, node.tupleset_rel) in ast):
                continue
            ts = ast[(typ, node.tupleset_rel)]
            # REFUSED SHAPE (TK106). WHY: `ttu_leaf` below reads stored tuples only, so a
            # computed / boolean / `from` arm of the tupleset never contributes a parent.
            # INSTEAD: `parent_link: [<the types>]`, and `x from parent_link`.
            if not direct_only(ts):
                raise ValueError(f'{typ}#{rel}: tupleset must be direct, but '
                                 f'{typ}#{node.tupleset_rel} is not')
            # REFUSED SHAPE (TK108). WHY: `ttu_leaf` below takes a stored parent's type and
            # name and ignores its predicate, so `[folder#member]` silently meant
            # `[folder]`. INSTEAD: `parent: [folder]` for the link, plus
            # `parent_member: member from parent` where the userset itself is meant
            # (`[folder:*#member]` -> `[folder:*]` likewise).
            for sub in _oracle_nodes(ts):
                if isinstance(sub, ODirect):
                    for (r_type, r_pred, _wild) in sub.restrictions:
                        if r_pred != '...':
                            raise ValueError(
                                f'{typ}#{rel}: tupleset may not restrict to a userset, '
                                f'but {typ}#{node.tupleset_rel} allows {r_type}#{r_pred}')

def _validate_stratified_negation(ast) -> None:
    """Independent twin of ``src/zanzibar/schema/parser.py::_validate_stratified_negation`` (TK114,
    2026-10-04), NOT shared with it (independence contract above). Refuses any relation
    that reaches itself along a path with at least one step taken inside a ``but not``
    subtrahend. A step is a computed ref, a tupleset, a TTU target on a type the tupleset
    admits, or a ``[T#p]`` restriction. Computed here as a closure over (from, to, negated)
    triples, not as the product's per-edge search."""
    steps = set()

    def collect(key, expr, negated):
        typ = key[0]
        if isinstance(expr, ODirect):
            for (r_type, r_pred, _wild) in expr.restrictions:
                if r_pred != '...':
                    steps.add((key, (r_type, r_pred), negated))
        elif isinstance(expr, OComputed):
            steps.add((key, (typ, expr.relation), negated))
        elif isinstance(expr, OTTU):
            steps.add((key, (typ, expr.tupleset_rel), negated))
            ts = ast.get((typ, expr.tupleset_rel))
            for node in (_oracle_nodes(ts) if ts is not None else ()):
                if isinstance(node, ODirect):
                    for (r_type, _r_pred, _wild) in node.restrictions:
                        if (r_type, expr.target_rel) in ast:
                            steps.add((key, (r_type, expr.target_rel), negated))
        elif isinstance(expr, (OUnion, OIntersection)):
            for c in expr.children:
                collect(key, c, negated)
        elif isinstance(expr, OExclusion):
            collect(key, expr.base, negated)
            collect(key, expr.subtract, True)

    for key, expr in ast.items():
        collect(key, expr, False)
    paths = set(steps)
    while True:
        joined = {(a, d, n1 or n2) for (a, b, n1) in paths for (c, d, n2) in steps if b == c}
        if joined <= paths:
            break
        paths |= joined
    for (a, b, negated) in sorted(paths):
        # REFUSED SHAPE (TK114): a relation reaching itself through a `but not` subtrahend,
        # e.g. `define viewer: [user] but not viewer from parent`. WHY: with `doc:a parent
        # doc:a` that reads `viewer = not viewer`, which has no answer; this evaluator's
        # provisional-False recursion guard (`Oracle.check`) used to return one anyway.
        # INSTEAD: subtract a relation that does not depend on the one being defined --
        # `define blocked: [user] or blocked from parent` + `define viewer: [user] but not
        # blocked`.
        if a == b and negated:
            raise ValueError(f'{a[0]}#{a[1]} is defined in terms of its own negation '
                             f'(non-stratifiable "but not")')


# ---------------------------------------------------------------------------
# Legacy union-only classification view (kept for the parser-sanity test)
# ---------------------------------------------------------------------------

@dataclass
class RelationDef:
    """The union children of one ``define <relation>: ...`` clause (pure-union only)."""
    has_direct: bool = False
    computed: list = None                 # type: ignore[assignment]
    ttu: list = None                      # type: ignore[assignment]

    def __post_init__(self):
        if self.computed is None:
            self.computed = []
        if self.ttu is None:
            self.ttu = []


def parse_schema(text: str) -> dict[tuple[str, str], RelationDef]:
    """Classification adapter over ``parse_schema_ast`` for pure-union schemas.

    Retained for ``test_parse_schema_classification`` (a direct hedge on the DSL
    reading). Boolean operators are out of scope for this view and raise.
    """
    out: dict[tuple[str, str], RelationDef] = {}
    for (typ, rel), expr in parse_schema_ast(text).items():
        rd = RelationDef()
        children = expr.children if isinstance(expr, OUnion) else (expr,)
        for child in children:
            if isinstance(child, ODirect):
                rd.has_direct = True
            elif isinstance(child, OComputed):
                rd.computed.append(child.relation)
            elif isinstance(child, OTTU):
                rd.ttu.append((child.target_rel, child.tupleset_rel))
            else:
                # REFUSED SHAPE (test-only view): a boolean operator. WHY: `RelationDef`
                # classifies pure-union children only. INSTEAD: `parse_schema_ast`, which
                # parses the full boolean grammar.
                raise ValueError(f'{typ}#{rel}: boolean operators not supported by parse_schema')
        out[(typ, rel)] = rd
    return out


# ---------------------------------------------------------------------------
# Oracle -- pointwise boolean evaluator
# ---------------------------------------------------------------------------

class Oracle:
    def __init__(self, schema: str, tuples: list[OracleTuple]):
        self.ast = parse_schema_ast(schema)
        self.tuples = list(tuples)

    def _universe(self, entity_type: str, query_names: set[tuple[str, str]]) -> set[str]:
        """Concrete names of ``entity_type`` in any tuple position ∪ query endpoints."""
        names: set[str] = set()
        for tup in self.tuples:
            if tup.subject_type == entity_type and tup.subject_name != '*':
                names.add(tup.subject_name)
            if tup.object_type == entity_type and tup.object_name != '*':
                names.add(tup.object_name)
        for q_type, q_name in query_names:
            if q_type == entity_type and q_name != '*':
                names.add(q_name)
        return names

    def check(self, subject_predicate, subject_type, subject_name,
              relation, object_type, object_name) -> bool:
        s_pred = _norm_pred(subject_predicate)
        subject = (subject_type, subject_name, s_pred)
        query_names = {(subject_type, subject_name), (object_type, object_name)}

        memo: dict[tuple[str, str, str], bool] = {}
        stack: dict[tuple[str, str, str], int] = {}     # key -> stack depth
        # Tarjan-lowlink-style memo guard: a frame whose subtree consulted a key that
        # was still IN PROGRESS computed only a provisional answer (the guard returns
        # False on revisit), so memoizing it would poison later, non-short-circuiting
        # consumers (a and b / a but not b). Only the frame at the top of its cycle
        # (lowlink == own depth) may be memoized.
        INF = float('inf')
        low = [INF]                                      # min in-stack depth touched

        def universe(entity_type: str) -> set[str]:
            return self._universe(entity_type, query_names)

        def instances(entity_type: str) -> set[str]:
            """∃-witnesses for strict ∀⇒∃ star expansions: tuple-mentioned names
            ONLY. Query endpoints must never witness existence -- a ghost would
            "exist" because you asked about it (blind-audit O3). ``universe()``
            (endpoints included) remains correct for shape/marker matching."""
            return self._universe(entity_type, set())

        def sat(o_type: str, o_name: str, rel: str) -> bool:
            key = (o_type, o_name, rel)
            if key in memo:
                return memo[key]
            if key in stack:
                low[0] = min(low[0], stack[key])
                return False            # recursive schema: this path adds nothing new
            expr = self.ast.get((o_type, rel))
            if expr is None:
                memo[key] = False
                return False
            depth = len(stack)
            stack[key] = depth
            outer_low, low[0] = low[0], INF
            result = sat_expr(expr, o_type, o_name, rel)
            my_low = low[0]
            del stack[key]
            if my_low >= depth:         # cycle (if any) closed at or below this frame
                memo[key] = result
                low[0] = outer_low
            else:                       # provisional: an ancestor was consulted
                low[0] = min(outer_low, my_low)
            return result

        def sat_expr(expr, o_type: str, o_name: str, rel: str) -> bool:
            if isinstance(expr, OUnion):
                return any(sat_expr(c, o_type, o_name, rel) for c in expr.children)
            if isinstance(expr, OIntersection):
                return all(sat_expr(c, o_type, o_name, rel) for c in expr.children)
            if isinstance(expr, OExclusion):
                return (sat_expr(expr.base, o_type, o_name, rel)
                        and not sat_expr(expr.subtract, o_type, o_name, rel))
            if isinstance(expr, ODirect):
                return direct_leaf(expr.restrictions, o_type, o_name, rel)
            if isinstance(expr, OComputed):
                return sat(o_type, o_name, expr.relation)
            if isinstance(expr, OTTU):
                return ttu_leaf(expr.target_rel, expr.tupleset_rel, o_type, o_name)
            raise TypeError(f'unknown AST node {expr!r}')

        def _matching_objects(o_name: str) -> set[str]:
            # o_name='*' expands ONLY star-object tuples (intensional); a concrete object
            # also absorbs tuples targeting T:* (the object-wildcard grant).
            return {o_name} if o_name == '*' else {o_name, '*'}

        def direct_leaf(restrictions, o_type: str, o_name: str, rel: str) -> bool:
            objs = _matching_objects(o_name)
            s_type, s_name, s_pred = subject

            def restriction_matches(tup) -> bool:
                for (r_type, r_pred, r_wild) in restrictions:
                    if (tup.subject_type == r_type and tup.subject_predicate == r_pred
                            and (tup.subject_name == '*') == r_wild):
                        return True
                return False

            grants = [tup for tup in self.tuples
                      if tup.relation == rel and tup.object_type == o_type
                      and tup.object_name in objs and restriction_matches(tup)]

            if s_name == '*':
                # intensional on this branch's own restrictions: the matching star
                # tuple of this shape exists...
                for g in grants:
                    if g.subject_name == '*' and g.subject_type == s_type and g.subject_predicate == s_pred:
                        return True
                # ...or flow-through: '*' resolves through granted usersets like any
                # other subject (blind-audit D1: OpenFGA literal-subject semantics;
                # the graph closure cannot express per-branch-only for userset flow)
                return _member_of_granted(grants)

            if s_pred == '...':
                # concrete bare entity u
                for g in grants:
                    if g.subject_name != '*' and g.subject_predicate == '...':
                        if (g.subject_type, g.subject_name) == (s_type, s_name):
                            return True                        # direct concrete grant
                    elif g.subject_name == '*' and g.subject_predicate == '...':
                        if g.subject_type == s_type:
                            return True                        # bare-star covers u
                # membership inside a granted userset (concrete or star)
                if _member_of_granted(grants):
                    return True
                return False

            # userset query subject (s_type, s_name, s_pred), s_name != '*'
            for g in grants:
                if g.subject_name != '*' and g.subject_predicate != '...':
                    if (g.subject_type, g.subject_name, g.subject_predicate) == (s_type, s_name, s_pred):
                        return True                            # this exact userset is granted
                elif g.subject_name == '*' and g.subject_predicate != '...':
                    if (g.subject_type, g.subject_predicate) == (s_type, s_pred):
                        return True                            # userset-star of same shape
            if _member_of_granted(grants):
                return True
            return False

        def _member_of_granted(grants) -> bool:
            """Is the fixed subject a (transitive) member of any granted userset in ``grants``?"""
            for g in grants:
                if g.subject_predicate == '...':
                    continue                                   # bare grants handled above
                if g.subject_name != '*':
                    if sat(g.subject_type, g.subject_name, g.subject_predicate):
                        return True                            # member of concrete userset
                else:
                    for inst in instances(g.subject_type):     # member of ANY instance (star)
                        if sat(g.subject_type, inst, g.subject_predicate):
                            return True
            return False

        def ttu_leaf(target_rel: str, tupleset_rel: str, o_type: str, o_name: str) -> bool:
            objs = _matching_objects(o_name)
            s_type, s_name, s_pred = subject
            for tup in self.tuples:
                if not (tup.relation == tupleset_rel and tup.object_type == o_type
                        and tup.object_name in objs):
                    continue
                p_type, p_name = tup.subject_type, tup.subject_name
                if p_name != '*':
                    # concrete parent p -> subject reaches obj if it reaches p under target_rel
                    if (s_type, s_name, s_pred) == (p_type, p_name, target_rel):
                        return True                            # the from-chain userset itself
                    if sat(p_type, p_name, target_rel):
                        return True
                else:
                    # star parent (S:*): marker of shape (S, target_rel) + instance expansion
                    if (s_type, s_pred) == (p_type, target_rel):
                        return True                            # star/userset subject of that shape
                    for inst in instances(p_type):
                        if sat(p_type, inst, target_rel):
                            return True
            return False

        return sat(object_type, object_name, relation)


def check_oracle(schema: str, tuples: list[OracleTuple],
                 subject_predicate, subject_type, subject_name,
                 relation, object_type, object_name) -> bool:
    """Module-level convenience: build a fresh Oracle and answer one query."""
    return Oracle(schema, tuples).check(subject_predicate, subject_type, subject_name,
                                        relation, object_type, object_name)
