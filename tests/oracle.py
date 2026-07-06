"""
Reference oracle for wildcard-aware Zanzibar reachability, now with boolean
operators (spec §3).

This is a deliberately naive, memoized evaluator over ``(schema, list_of_input_tuples)``.
It exists ONLY to serve as an independent ground truth for the materialized
``WildcardIndex`` (``index_v4``) and the set engine (``setengine``).

Independence contract (wildcard spec §4, restated):
  * imports NOTHING from ``index_v4`` / ``setengine`` (no DB, no edges, no bridges);
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
        elif c in '()':
            tokens.append(('lparen' if c == '(' else 'rparen', c))
            i += 1
        else:
            j = i
            while j < n and not body[j].isspace() and body[j] not in '()[]':
                j += 1
            tokens.append(('word', body[i:j]))
            i = j
    return tokens


def _parse_restrictions(bracket: str) -> tuple[tuple[str, str, bool], ...]:
    """Parse ``[user, group#member, user:*, group:*#member]`` into (type, pred, wildcard)."""
    inner = bracket[bracket.index('[') + 1:bracket.rindex(']')]
    out: list[tuple[str, str, bool]] = []
    for part in inner.split(','):
        part = part.strip()
        if not part:
            continue
        if '#' in part:
            left, pred = part.split('#', 1)
            pred = pred.strip()
        else:
            left, pred = part, '...'
        left = left.strip()
        if left.endswith(':*'):
            out.append((left[:-2].strip(), pred, True))
        else:
            out.append((left, pred, False))
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
    """Parse the DSL into ``{(type, relation): OExpr}`` (boolean-aware; drives evaluation)."""
    ast: dict[tuple[str, str], object] = {}
    current_type: str | None = None
    for raw in text.strip().splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('type '):
            current_type = line.split(' ', 1)[1].strip()
        elif line.startswith('define '):
            if current_type is None:
                raise ValueError('relation defined outside of a type')
            name, _, body = line[len('define '):].partition(':')
            ast[(current_type, name.strip())] = _Parser(_tokenize(body.strip()), name.strip()).parse()
    return ast


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
        stack: set[tuple[str, str, str]] = set()

        def universe(entity_type: str) -> set[str]:
            return self._universe(entity_type, query_names)

        def sat(o_type: str, o_name: str, rel: str) -> bool:
            key = (o_type, o_name, rel)
            if key in memo:
                return memo[key]
            if key in stack:
                return False            # recursive schema: this path adds nothing new
            expr = self.ast.get((o_type, rel))
            if expr is None:
                memo[key] = False
                return False
            stack.add(key)
            result = sat_expr(expr, o_type, o_name, rel)
            stack.discard(key)
            memo[key] = result
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
                # intensional per-branch: the matching star tuple of this shape must exist
                for g in grants:
                    if g.subject_name == '*' and g.subject_type == s_type and g.subject_predicate == s_pred:
                        return True
                return False

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
                    for inst in universe(g.subject_type):      # member of ANY instance (star)
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
                    # star parent (S:*): marker of shape (S, target_rel) + universe expansion
                    if (s_type, s_pred) == (p_type, target_rel):
                        return True                            # star/userset subject of that shape
                    for inst in universe(p_type):
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
