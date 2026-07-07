import re
from dataclasses import dataclass, field, replace
from functools import reduce
from pprint import pprint
from types import EllipsisType
from typing import Callable

from legacy.index_v2 import Node


# ---------------------------------------------------------------------------
# Identifier validation (strict surrogate ids for both backends)
# ---------------------------------------------------------------------------
#
# Entity types, entity names, and relations are the *surrogate* identities. They are
# stored and interned verbatim, so we constrain them to a conservative, delimiter-free
# charset -- keeping DSL/parsing delimiters (``: # @ , ( ) space`` and the ``or`` /
# ``but not`` keywords already excluded by whitespace), control characters, quotes, and
# injection payloads out of identity strings entirely. Names may additionally be the
# wildcard sentinel ``'*'``; a subject predicate may be the bare sentinel ``'...'``.
# Internal ids remain strictly numeric (allocated int32s), decoupled from these strings.

IDENTIFIER_CHARSET = r'A-Za-z0-9_./@+=-'
_IDENTIFIER_RE = re.compile(rf'^[{IDENTIFIER_CHARSET}]{{1,256}}$')


def is_valid_identifier(value) -> bool:
    return isinstance(value, str) and _IDENTIFIER_RE.match(value) is not None


def _require(value, label: str, *, allow_star: bool = False, allow_ellipsis: bool = False) -> None:
    if allow_ellipsis and (value is Ellipsis or value == '...'):
        return
    if allow_star and value == '*':
        return
    if not is_valid_identifier(value):
        extra = ''.join([" or '*'" if allow_star else '', " or '...'" if allow_ellipsis else ''])
        raise ValueError(
            f"invalid {label} {value!r}: must match [{IDENTIFIER_CHARSET}] (1-256 chars){extra}")


def validate_write_identifiers(subject_predicate, subject_type, subject_name,
                               relation, object_type, object_name) -> None:
    """Reject any out-of-charset identifier on a tuple write (shared by both backends).

    Types and relations must be plain identifiers; names may be the wildcard ``'*'``; the
    subject predicate may be the bare ``'...'`` (or ``Ellipsis``)."""
    _require(subject_type, 'subject_type')
    _require(relation, 'relation')
    _require(object_type, 'object_type')
    _require(subject_name, 'subject_name', allow_star=True)
    _require(object_name, 'object_name', allow_star=True)
    _require(subject_predicate, 'subject_predicate', allow_ellipsis=True)


def validate_node_identifiers(predicate, entity_type, entity_name) -> None:
    """Validate a single node identity (predicate/type/name) for node-level writes."""
    _require(entity_type, 'entity_type')
    _require(entity_name, 'entity_name', allow_star=True)
    _require(predicate, 'predicate', allow_ellipsis=True)


@dataclass(frozen=True, slots=True, order=True, unsafe_hash=True)
class Entity:
    type: str
    name: str

    @property
    def wildcard(self):
        return self.name == '*'

    def __str__(self):
        return f'{self.type}:{self.name}'


@dataclass(frozen=True, unsafe_hash=True, order=True, slots=True)
class NodeV2(Node):
    type: str
    name: str
    predicate: str | EllipsisType


@dataclass(frozen=True, slots=True, order=True, unsafe_hash=True)
class RelationalTriple:
    subject: Entity
    relation: str
    object: Entity

    # needed for adding group:a#member is a writer of document:b
    subject_predicate: str | EllipsisType = Ellipsis

    def __str__(self):
        # follows zanzibar paper
        subject_predicate: str
        if isinstance(self.subject_predicate, str):
            subject_predicate = self.subject_predicate
        else:
            assert self.subject_predicate is Ellipsis
            subject_predicate = '...'
        return f'{self.object}#{self.relation}@{self.subject}#{subject_predicate}'

    @property
    def node_from(self):
        return NodeV2(type=self.subject.type,
                      name=self.subject.name,
                      predicate=self.subject_predicate)

    @property
    def node_to(self):
        return NodeV2(type=self.object.type,
                      name=self.object.name,
                      predicate=self.relation)


@dataclass(frozen=True, slots=True, order=True, kw_only=True)
class EntityPattern:
    type: str | None = None
    name: str | None = None
    # Permissive matching for rewrite RULES (spec §2.2). When True and this pattern
    # does not pin a name (name is None), the wildcard-vs-concrete guard is skipped so
    # a name-agnostic rule matches wildcard entities too (e.g. writer=>viewer must
    # carry a `user:*` subject through). FILTERS keep the default (strict) so `[user]`
    # continues to reject `user:*`.
    match_wildcards: bool = False

    @property
    def wildcard(self):
        return self.name == '*'

    def match(self, entity: Entity) -> bool:
        if not isinstance(entity, Entity):
            raise TypeError(f'expected an `Entity`, got {entity!r}')
        if self.type is not None and self.type != entity.type:
            return False
        if self.name is not None and self.name != entity.name:
            return False
        if not (self.match_wildcards and self.name is None):
            if self.wildcard != entity.wildcard:
                return False
        return True

    def replace(self, entity: Entity) -> Entity:
        if not isinstance(entity, Entity):
            raise TypeError(f'expected an `Entity`, got {entity!r}')
        return Entity(type=self.type or entity.type,
                      name=self.name or entity.name)


@dataclass(frozen=True, slots=True, order=True, kw_only=True)
class RelationalTriplePattern:
    subject_predicate: str | EllipsisType | None = None
    subject_type: str | None = None
    subject_name: str | None = None
    relation: str | None = None
    object_type: str | None = None
    object_name: str | None = None
    # Subject-side permissiveness (spec §2.2): True for RULES, False (strict) for
    # FILTERS so `[user]` keeps rejecting a `user:*` subject.
    match_wildcards: bool = False
    # Object-side permissiveness. Object wildcards (`folder:*`) are the spec's extension
    # beyond OpenFGA and have no subject-restriction meaning, so a FILTER must not reject
    # a tuple merely for having a wildcard object -- that validity is the façade's job
    # (declared object-wildcard shapes). Defaults to `match_wildcards` when unset.
    object_match_wildcards: bool | None = None

    @property
    def _object_match_wildcards(self) -> bool:
        return self.match_wildcards if self.object_match_wildcards is None else self.object_match_wildcards

    @property
    def subject(self):
        return EntityPattern(type=self.subject_type, name=self.subject_name,
                             match_wildcards=self.match_wildcards)

    @property
    def object(self):
        return EntityPattern(type=self.object_type, name=self.object_name,
                             match_wildcards=self._object_match_wildcards)

    def match(self, relational_triple: RelationalTriple) -> bool:
        if not isinstance(relational_triple, RelationalTriple):
            raise TypeError(f'expected a `RelationalTriple`, got {relational_triple!r}')
        if self.subject_predicate is not None and self.subject_predicate != relational_triple.subject_predicate:
            return False
        if self.subject is not None and not self.subject.match(relational_triple.subject):
            return False
        if self.relation is not None and self.relation != relational_triple.relation:
            return False
        if self.object is not None and not self.object.match(relational_triple.object):
            return False
        return True

    def replace(self, relational_triple: RelationalTriple) -> RelationalTriple:
        if not isinstance(relational_triple, RelationalTriple):
            raise TypeError(f'expected a `RelationalTriple`, got {relational_triple!r}')
        _pred = self.subject_predicate if self.subject_predicate else relational_triple.subject_predicate
        _subject = self.subject.replace(relational_triple.subject) if self.subject else relational_triple.subject
        _object = self.object.replace(relational_triple.object) if self.object else relational_triple.object
        return RelationalTriple(subject_predicate=_pred,
                                subject=_subject,
                                relation=self.relation or relational_triple.relation,
                                object=_object)


@dataclass(frozen=True, slots=True, order=True)
class Filter:
    if_pattern: RelationalTriplePattern

    def apply(self, relational_triple: RelationalTriple) -> bool:
        return self.if_pattern.match(relational_triple)


@dataclass(frozen=True, slots=True, order=True)
class RewriteFilter(Filter):
    """An admission Filter that also *routes*: a raw tuple it matches is admitted with
    its relation rewritten to ``rewrite_relation`` (a compiled leaf predicate).

    Boolean spec §3.3: users write derived relations by their public names only; each
    ``Direct`` restriction inside a derived relation compiles to one of these, and in
    ``RuleSet.apply`` *every* matching RewriteFilter fires (fan-in expansion, all-match,
    deduped by resulting triple) -- unlike plain Filters, which stay first-match.

    Implemented as a subclass rather than a new field on ``Filter`` so the compiled
    output of pure-union schemas stays byte-identical to its P0 snapshot (Filter reprs
    unchanged); see docs/spec-deviations.md.
    """
    rewrite_relation: str


@dataclass(frozen=True, slots=True, order=True)
class Rule:
    if_pattern: RelationalTriplePattern
    then_pattern: RelationalTriplePattern | None

    def apply(self, relational_triple: RelationalTriple) -> RelationalTriple | None:
        if self.if_pattern.match(relational_triple):
            if self.then_pattern is not None:
                return self.then_pattern.replace(relational_triple)
        return None


@dataclass(frozen=True)
class SchemaInfo:
    """Wildcard-shape metadata derived from a schema (spec §2.3).

    A *shape* is ``(entity_type, predicate)`` where predicate is ``'...'`` for a bare
    entity or a relation name for a userset. This is intentionally dumb: we never do
    static reachability analysis to elide bridges beyond the bare-shape rule below --
    an unnecessary O(1)-degree bridge is harmless, a missing bridge is a correctness bug.
    """
    subject_wildcard_shapes: frozenset[tuple[str, str]] = frozenset()   # (type, predicate); '...' for bare
    object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset()    # (type, relation)
    # Derived-predicate namespace facts (boolean spec §3.3/§3.4), populated only by a
    # boolean-enabled compile; empty for pure-union schemas and hand-built rulesets.
    # The façade enforces derived-family write exclusivity from these (boolean spec I5).
    derived_families: frozenset[tuple[str, str]] = frozenset()          # (object_type, relation)
    leaf_families: frozenset[tuple[str, str]] = frozenset()             # (object_type, leaf_predicate)

    @property
    def bridged_in_shapes(self) -> frozenset[tuple[str, str]]:
        # Shapes needing concrete->w_any bridges: subject-wildcard USERSET shapes only.
        # Bare shapes (T, '...') never need in-bridges -- nothing in this graph ever
        # points into a '...'-predicate node, so a bare-shape hop can only be the LEADING
        # hop of a path, which probe #2 covers virtually. This is what makes plain
        # OpenFGA [user:*] cost zero bridges.
        return frozenset(s for s in self.subject_wildcard_shapes if s[1] != '...')

    @property
    def bridged_out_shapes(self) -> frozenset[tuple[str, str]]:
        # Shapes needing w_all->concrete bridges: all declared object-wildcard shapes.
        # (Sink-shape elision is a future optimization; be conservative now.)
        return self.object_wildcard_shapes


@dataclass
class RuleSet:
    rules_and_filters: list[Rule | Filter]
    # Populated by parse_openfga_schema; None for hand-built rulesets. The façade
    # (§6) reads this; ingestion via .apply ignores it (spec §2.3: "returned
    # alongside (or wrapping) the RuleSet").
    schema_info: SchemaInfo | None = None
    # Boolean-compile artifacts (boolean spec §3.4); None for pure-union schemas
    # compiled without enable_boolean and for hand-built rulesets.
    compiled: 'CompiledBooleans | None' = None

    def _build_dispatch(self) -> None:
        """Indexed dispatch (boolean spec §1.12): key Filters/Rules by their if-pattern
        relation. Our patterns test a single triple, so only the alpha layer applies --
        a dict hit replaces the linear scan. Original list order is preserved inside and
        across buckets (position-tagged) so first-match admission is byte-identical.
        Built lazily on first apply(); rules_and_filters is treated as immutable after.
        """
        plain: dict[str | None, list[tuple[int, Filter]]] = {}
        rewrites: dict[str | None, list[tuple[int, RewriteFilter]]] = {}
        rules: dict[str | None, list[tuple[int, Rule]]] = {}
        for pos, rf in enumerate(self.rules_and_filters):
            key = rf.if_pattern.relation
            if isinstance(rf, RewriteFilter):
                rewrites.setdefault(key, []).append((pos, rf))
            elif isinstance(rf, Filter):
                plain.setdefault(key, []).append((pos, rf))
            elif isinstance(rf, Rule):
                rules.setdefault(key, []).append((pos, rf))
        self._plain_filters = plain
        self._rewrite_filters = rewrites
        self._rules = rules

    def _candidates(self, index: dict, relation: str) -> list:
        """Bucket lookup preserving original list order (merge keyed + wildcard bucket)."""
        keyed = index.get(relation, [])
        anyrel = index.get(None, [])
        if not anyrel:
            return keyed
        if not keyed:
            return anyrel
        return sorted(keyed + anyrel)

    def apply(self, relational_triple: RelationalTriple):
        if not hasattr(self, '_plain_filters'):
            self._build_dispatch()

        rel = relational_triple.relation
        compiled = self.compiled
        o_type = relational_triple.object.type

        # Leaf families are processor/rewrite-internal: a *raw* write naming one is
        # invalid, matching the set engine's no-restriction rejection (boolean spec §3.3).
        if compiled is not None and (o_type, rel) in compiled.leaf_families:
            raise ValueError(
                f"relation {rel!r} is a compiled leaf predicate of a derived relation; "
                f"tuples must be written against the public relation name")

        if compiled is not None and (o_type, rel) in compiled.derived_families:
            # Fan-in expansion (boolean spec §3.3): every matching RewriteFilter fires,
            # each yielding the triple with its relation replaced by the owning leaf;
            # dedupe by resulting triple. remove applies the same expansion so counts
            # retire symmetrically.
            seeds = {
                replace_relation(relational_triple, f.rewrite_relation)
                for _, f in self._candidates(self._rewrite_filters, rel)
                if f.apply(relational_triple)
            }
            if not seeds:
                raise ValueError(
                    f"tuple {relational_triple} matches no declared type restriction "
                    f"for derived relation {o_type}#{rel}")
        else:
            # Pure-union relations keep first-match admission semantics, unchanged.
            for _, flt in self._candidates(self._plain_filters, rel):
                if flt.apply(relational_triple):
                    seeds = {relational_triple}
                    break
            else:
                return

        unprocessed = set(seeds)
        processed = set()
        while unprocessed:
            relational_triple = unprocessed.pop()
            if relational_triple in processed:
                continue
            yield relational_triple

            processed.add(relational_triple)
            for _, rule in self._candidates(self._rules, relational_triple.relation):
                if (_result := rule.apply(relational_triple)) is not None:
                    unprocessed.add(_result)


def replace_relation(triple: RelationalTriple, relation: str) -> RelationalTriple:
    return RelationalTriple(subject=triple.subject, relation=relation,
                            object=triple.object, subject_predicate=triple.subject_predicate)


def parse_relation_rule(
        rule: str,
) -> tuple[list[tuple[str | None, str | None, str | None]], list[tuple[str, str]]]:
    """
    NOTE: WINDSURF WROTE THIS CODE (extended for wildcard subjects, spec §2.1)
    Parse a single relation rule into direct assignments and from relations.
    Returns (direct_assignments, from_relations) where:
        - direct_assignments is list of (type, predicate, name) for direct type assignments;
          name is '*' for a wildcard declaration (`T:*` / `T:*#P`), else None
        - from_relations is list of (relation, from_relation) for 'X from Y' rules

    Examples:
        "[user]" -> ([(user, None, None)], [])
        "[user, domain#member]" -> ([(user, None, None), (domain, member, None)], [])
        "[user:*]" -> ([(user, None, '*')], [])
        "[group:*#member]" -> ([(group, member, '*')], [])
        "writer" -> ([(None, writer, None)], [])
        "owner from parent_folder" -> ([], [(owner, parent_folder)])
    """
    direct_assignments: list[tuple[str | None, str | None, str | None]] = []
    from_relations: list[tuple[str, str]] = []

    # Handle 'X from Y' format
    if ' from ' in rule:
        relation, from_relation = rule.strip().split(' from ')
        from_relations.append((relation.strip(), from_relation.strip()))
        return direct_assignments, from_relations

    # Handle direct type assignments [type1, type2#relation, type3:*, type4:*#relation]
    if rule.startswith('['):
        subjects = rule[1:].split(']')[0].split(',')
        for subject in subjects:
            subject = subject.strip()
            if '#' in subject:
                # type#relation or type:*#relation
                left, subject_predicate = subject.split('#')
                subject_predicate = subject_predicate.strip()
            else:
                # bare type or type:*
                left, subject_predicate = subject, None
            left = left.strip()
            if left.endswith(':*'):
                subject_type, subject_name = left[:-len(':*')].strip(), '*'
            else:
                subject_type, subject_name = left, None
            direct_assignments.append((subject_type, subject_predicate, subject_name))
    else:
        # Handle single relation reference (e.g., "writer")
        direct_assignments.append((None, rule.strip(), None))

    return direct_assignments, from_relations


# ===========================================================================
# Expression AST (spec §2.1) + recursive-descent parser (spec §2.2)
# ===========================================================================
#
# Parsing is split from compilation (spec §2.3): the DSL is parsed into a
# ``SchemaAST`` -- a plain, backend-agnostic tree -- which BOTH the graph index
# (via ``compile_ruleset``) and the set engine / oracle consume. The graph index
# only supports pure-union definitions; ``compile_ruleset`` refuses ``and`` /
# ``but not`` loudly (``UnsupportedByGraphIndex``) so a boolean schema can never be
# silently mis-ingested.


class UnsupportedByGraphIndex(Exception):
    """A schema construct (``and`` / ``but not``) the graph index cannot represent.

    Raised by ``compile_ruleset`` naming the offending relation. The set-engine
    backend handles these; the closure-materialising graph index does not.
    """


# ---- leaves ----

@dataclass(frozen=True, slots=True)
class Restriction:
    """One entry of a ``[...]`` type-restriction list.

    ``predicate`` is ``'...'`` for a bare entity (``[user]``) or a relation name for a
    userset (``[group#member]``). ``wildcard`` is True for ``T:*`` / ``T:*#P``.
    """
    type: str
    predicate: str
    wildcard: bool = False


@dataclass(frozen=True, slots=True)
class Direct:
    """A ``[...]`` direct type-restriction list, e.g. ``[user, group#member, user:*]``."""
    restrictions: tuple[Restriction, ...]


@dataclass(frozen=True, slots=True)
class Computed:
    """A computed userset: ``define viewer: editor`` -> ``Computed('editor')``."""
    relation: str


@dataclass(frozen=True, slots=True)
class TTU:
    """Tuple-to-userset: ``define viewer: viewer from parent`` -> ``TTU('viewer', 'parent')``."""
    target_rel: str
    tupleset_rel: str


# ---- operators ----

@dataclass(frozen=True, slots=True)
class Union:
    children: tuple['Expr', ...]


@dataclass(frozen=True, slots=True)
class Intersection:
    children: tuple['Expr', ...]


@dataclass(frozen=True, slots=True)
class Exclusion:
    base: 'Expr'
    subtract: 'Expr'


Expr = Union | Intersection | Exclusion | Direct | Computed | TTU
SchemaAST = dict[tuple[str, str], Expr]     # (object_type, relation) -> Expr


_RESERVED = ('or', 'and', 'but', 'not', 'from')


def _tokenize_relation_body(body: str) -> list[tuple[str, str]]:
    """Split a relation body into (kind, text) tokens.

    Brackets are atomic (``[user, group#member]`` -> one ``bracket`` token, commas
    and spaces preserved); parens are their own tokens; everything else is a
    whitespace-delimited ``word`` (relation names + the reserved keywords).
    """
    tokens: list[tuple[str, str]] = []
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if c.isspace():
            i += 1
        elif c == '[':
            j = body.find(']', i)
            if j == -1:
                raise ValueError(f"unterminated '[' in relation body {body!r}")
            tokens.append(('bracket', body[i:j + 1]))
            i = j + 1
        elif c == '(':
            tokens.append(('lparen', '('))
            i += 1
        elif c == ')':
            tokens.append(('rparen', ')'))
            i += 1
        else:
            j = i
            while j < n and not body[j].isspace() and body[j] not in '()[]':
                j += 1
            tokens.append(('word', body[i:j]))
            i = j
    return tokens


class _RelationParser:
    """Recursive-descent parser for one relation body (grammar in spec §2.2):

        expr    := chain ('but not' chain)?     # at most one exclusion, loosest binding
        chain   := unit (OP unit)*              # OP homogeneous: all 'or' or all 'and'
        unit    := '(' expr ')' | leaf
        leaf    := type-restriction-list | REL | REL 'from' REL
    """

    def __init__(self, tokens: list[tuple[str, str]], relation: str):
        self.tokens = tokens
        self.relation = relation
        self.pos = 0

    def _peek(self) -> tuple[str | None, str | None]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else (None, None)

    def parse(self) -> Expr:
        if not self.tokens:
            raise ValueError(f"relation {self.relation!r}: empty definition")
        expr = self._parse_expr()
        if self.pos != len(self.tokens):
            _, text = self._peek()
            raise ValueError(f"relation {self.relation!r}: unexpected token {text!r}")
        return expr

    def _parse_expr(self) -> Expr:
        base = self._parse_chain()
        if self._match_but_not():
            return Exclusion(base, self._parse_chain())
        return base

    def _match_but_not(self) -> bool:
        if (self.pos + 1 < len(self.tokens)
                and self.tokens[self.pos] == ('word', 'but')
                and self.tokens[self.pos + 1] == ('word', 'not')):
            self.pos += 2
            return True
        return False

    def _parse_chain(self) -> Expr:
        children = [self._parse_unit()]
        op: str | None = None
        while True:
            kind, text = self._peek()
            if kind == 'word' and text in ('or', 'and'):
                if op is None:
                    op = text
                elif op != text:
                    raise ValueError(
                        f"relation {self.relation!r}: mixing 'or' and 'and' without "
                        f"parentheses is ambiguous")
                self.pos += 1
                children.append(self._parse_unit())
            else:
                break
        if op is None:
            return children[0]
        return Union(tuple(children)) if op == 'or' else Intersection(tuple(children))

    def _parse_unit(self) -> Expr:
        kind, _ = self._peek()
        if kind == 'lparen':
            self.pos += 1
            expr = self._parse_expr()
            if self._peek()[0] != 'rparen':
                raise ValueError(f"relation {self.relation!r}: expected ')'")
            self.pos += 1
            return expr
        return self._parse_leaf()

    def _parse_leaf(self) -> Expr:
        kind, text = self._peek()
        if kind == 'bracket':
            self.pos += 1
            direct_assignments, _ = parse_relation_rule(text)
            return Direct(tuple(
                Restriction(type=t, predicate=('...' if p is None else p), wildcard=(nm == '*'))
                for (t, p, nm) in direct_assignments
            ))
        if kind == 'word':
            if text in _RESERVED:
                raise ValueError(f"relation {self.relation!r}: unexpected {text!r}")
            self.pos += 1
            if self._peek() == ('word', 'from'):
                self.pos += 1
                k3, t3 = self._peek()
                if k3 != 'word' or t3 in _RESERVED:
                    raise ValueError(f"relation {self.relation!r}: expected a relation after 'from'")
                self.pos += 1
                return TTU(target_rel=text, tupleset_rel=t3)
            return Computed(text)
        raise ValueError(f"relation {self.relation!r}: unexpected end of expression")


def parse_schema_ast(schema: str) -> SchemaAST:
    """Parse an OpenFGA DSL string into ``{(object_type, relation): Expr}`` (spec §2.2).

    Always succeeds for well-formed syntax, including boolean (``and`` / ``but not``)
    definitions -- refusing booleans is compilation's job, not parsing's.
    """
    ast: SchemaAST = {}
    current_type: str | None = None

    for line in schema.strip().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('model') or line.startswith('schema') or line.startswith('relations'):
            continue
        if line.startswith('type '):
            current_type = line.split(' ', 1)[1].strip()
        elif line.startswith('define '):
            if not current_type:
                raise ValueError("Relation definition without type context")
            relation_name, _, body = line[len('define '):].partition(':')
            relation_name = relation_name.strip()
            # Lexical collision lock (boolean spec §3.2): '.' is reserved for synthetic
            # leaf predicates ('<relation>.<index>'), so a *declared* relation name may
            # never contain it. Tuple-side entity names remain unrestricted.
            if '.' in relation_name:
                raise ValueError(
                    f"relation {relation_name!r}: '.' is reserved for compiled leaf "
                    f"predicates and cannot appear in a declared relation name")
            tokens = _tokenize_relation_body(body.strip())
            ast[(current_type, relation_name)] = _RelationParser(tokens, relation_name).parse()
    return ast


def _iter_directs(expr: Expr):
    if isinstance(expr, Direct):
        yield expr
    elif isinstance(expr, (Union, Intersection)):
        for c in expr.children:
            yield from _iter_directs(c)
    elif isinstance(expr, Exclusion):
        yield from _iter_directs(expr.base)
        yield from _iter_directs(expr.subtract)
    # Computed / TTU carry no direct restrictions


def derive_schema_info(
        ast: SchemaAST,
        object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset(),
) -> SchemaInfo:
    """Derive wildcard-shape metadata from the AST (spec §2.3).

    Subject-wildcard shapes come from every ``T:*`` / ``T:*#P`` restriction anywhere in
    the schema. Object-wildcard shapes have no DSL syntax and are declared by the caller.
    """
    subject_wildcard_shapes: set[tuple[str, str]] = set()
    for expr in ast.values():
        for direct in _iter_directs(expr):
            for r in direct.restrictions:
                if r.wildcard:
                    subject_wildcard_shapes.add((r.type, r.predicate))
    return SchemaInfo(
        subject_wildcard_shapes=frozenset(subject_wildcard_shapes),
        object_wildcard_shapes=frozenset(object_wildcard_shapes),
    )


def _restriction_filter(r: Restriction, object_type: str, relation_name: str) -> Filter:
    """The strict FILTER for one `[...]` restriction (spec §2.1/§2.3).

    The wildcard filter (subject_name='*') matches ONLY wildcard subjects; the concrete
    filter (subject_name=None) keeps rejecting `T:*`. Object side stays permissive so
    object-wildcard tuples reach the façade.
    """
    return Filter(RelationalTriplePattern(
        subject_predicate=(Ellipsis if r.predicate == '...' else r.predicate),
        subject_type=r.type,
        subject_name=('*' if r.wildcard else None),
        relation=relation_name,
        object_type=object_type,
        object_match_wildcards=True,
    ))


def schema_filters(ast: SchemaAST) -> list[Filter]:
    """Every strict direct-restriction Filter in the schema, booleans included (spec §6.2).

    Unlike ``compile_ruleset`` this never raises on ``and`` / ``but not`` -- it walks the
    Direct leaves inside boolean branches too. The set engine reuses these Filters for
    write-validity parity with the graph backend without materialising any RuleSet.
    """
    out: list[Filter] = []
    for (object_type, relation_name), expr in ast.items():
        for direct in _iter_directs(expr):
            for r in direct.restrictions:
                out.append(_restriction_filter(r, object_type, relation_name))
    return out


def _emit_expr(expr: Expr, object_type: str, relation_name: str,
               out: list[Rule | Filter]) -> None:
    if isinstance(expr, Union):
        for c in expr.children:
            _emit_expr(c, object_type, relation_name, out)
    elif isinstance(expr, (Intersection, Exclusion)):
        op = 'and' if isinstance(expr, Intersection) else 'but not'
        raise UnsupportedByGraphIndex(
            f"relation {object_type}#{relation_name} uses boolean operator {op!r}; "
            f"the graph index materialises closures and cannot ingest boolean relations "
            f"(use the set engine)")
    elif isinstance(expr, Direct):
        for r in expr.restrictions:
            out.append(_restriction_filter(r, object_type, relation_name))
    elif isinstance(expr, Computed):
        # Permissive RULE so wildcard subjects propagate through computed usersets (§2.2).
        out.append(Rule(
            RelationalTriplePattern(relation=expr.relation, object_type=object_type,
                                    match_wildcards=True),
            RelationalTriplePattern(relation=relation_name, object_type=object_type,
                                    match_wildcards=True),
        ))
    elif isinstance(expr, TTU):
        # `target from tupleset`: a tuple carrying `tupleset` rewrites to `target`#relation.
        out.append(Rule(
            RelationalTriplePattern(relation=expr.tupleset_rel, object_type=object_type,
                                    match_wildcards=True),
            RelationalTriplePattern(subject_predicate=expr.target_rel, relation=relation_name,
                                    object_type=object_type, match_wildcards=True),
        ))
    else:
        raise TypeError(f"unknown Expr node {expr!r}")


def compile_ruleset(ast: SchemaAST, schema_info: SchemaInfo, *,
                    enable_boolean: bool = True) -> RuleSet:
    """Compile an AST into the graph index's Filters/Rules (spec §2.3).

    Boolean (`and` / `but not`) relations compile into derived predicates (boolean
    spec §3): untainted relations byte-identically to the pure-union path, tainted
    ones into leaf routing + executable plans on ``RuleSet.compiled``, with
    ``RuleSet.schema_info`` enriched with the derived/leaf namespace facts.
    ``UnsupportedByGraphIndex`` survives only for the decision-15 scope rejections;
    derived-dependency cycles raise ``ValueError``.

    ``enable_boolean=False`` restores the historical refusal (the pre-P7 behavior):
    the first boolean operator raises ``UnsupportedByGraphIndex``.
    """
    if not enable_boolean:
        rules_and_filters: list[Rule | Filter] = []
        for (object_type, relation_name), expr in ast.items():
            _emit_expr(expr, object_type, relation_name, rules_and_filters)
        return RuleSet(rules_and_filters, schema_info=schema_info)

    tainted = compute_taint(ast)
    rules_and_filters = []
    for (object_type, relation_name), expr in ast.items():
        if (object_type, relation_name) not in tainted:
            _emit_expr(expr, object_type, relation_name, rules_and_filters)
    compiled, schema_info = compile_boolean_schema(ast, schema_info, rules_and_filters)
    return RuleSet(rules_and_filters, schema_info=schema_info, compiled=compiled)


# ===========================================================================
# Boolean derived-predicate compilation (boolean spec §3)
# ===========================================================================
#
# Boolean relations become DERIVED predicates: their state is materialised by a delta
# processor as ordinary edges in the same closure (per-object symbolic state in a
# residue row), fed by tuples that the write path routes into synthetic LEAF predicate
# families ('<relation>.<index>'). Everything here is ahead-of-time: taint analysis,
# plan trees with executable check/star folds, write-routing RewriteFilters, the
# namespace map, invalidation fan-out tables, and topological strata. Nothing walks
# the AST at runtime (boolean spec §1.11).


# ---- plan tree nodes (boolean spec §3.2) ----

@dataclass(frozen=True, slots=True)
class PClosureLeaf:
    """A maximal boolean-free, derived-free subtree, compiled to ordinary Filters/Rules
    under the synthetic leaf predicate; evaluated via the wildcard-aware closure check.

    ``storage=True`` marks a RewriteFilter-fed leaf (Direct restrictions): its edges
    ARE the relation's raw stored tuples -- the parent set for TTUs over this derived
    relation (stored-tuple semantics). Rule-fed (routed) leaves never count as stored
    tuples, so Direct restrictions are always compiled into their own leaf."""
    predicate: str          # '<relation>.<index>'
    positive: bool
    storage: bool = False


@dataclass(frozen=True, slots=True)
class PDerivedComputed:
    """A Computed reference to another derived relation (same object); evaluated through
    that relation's edge+residue check, never inlined."""
    relation: str
    positive: bool


@dataclass(frozen=True, slots=True)
class PDerivedUserset:
    """A tainted userset restriction ``[T#P]`` (P derived on T). Raw tuples land on this
    node's own storage leaf; membership is ∃ stored userset x: subject ∈ P(x)."""
    subject_type: str
    subject_predicate: str
    predicate: str          # the storage leaf ('<relation>.<index>')
    positive: bool


@dataclass(frozen=True, slots=True)
class PDerivedTTU:
    """``target from tupleset`` where the *target* is derived (tupleset untainted):
    ∃ tupleset-parent p: derived check (subject, target, p). ``parent_types`` are the
    tupleset's member entity types, resolved at compile so the processor never walks
    the AST (boolean spec §1.11)."""
    target_rel: str
    tupleset_rel: str
    positive: bool
    parent_types: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PDerivedTuplesetTTU:
    """``target from tupleset`` where the *tupleset* itself is derived. Parents are
    the STORED tupleset tuples only (the pinned Zanzibar TTU semantics -- the oracle's
    ttu_leaf reads raw tuples, never computed membership), which for a derived
    tupleset live on its leaf families. A derived tupleset with no Direct restrictions
    can hold no stored tuples, making its dependent TTU constantly empty -- exactly
    the oracle's answer. (Deviation from spec decision 15, which rejected this shape:
    the frozen acceptance event requires demorgans_law_1.fga to flip 4-way, and that
    fixture is three of these. See docs/spec-deviations.md.)"""
    target_rel: str
    tupleset_rel: str
    positive: bool
    parent_types: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PUnion:
    children: tuple


@dataclass(frozen=True, slots=True)
class PIntersection:
    children: tuple


@dataclass(frozen=True, slots=True)
class PExclusion:
    base: object
    subtract: object


# ---- compiled artifacts (boolean spec §3.4) ----

@dataclass(frozen=True, slots=True)
class LeafSpec:
    predicate: str          # leaf predicate for closure/userset kinds; public name otherwise
    kind: str               # 'closure' | 'derived-computed' | 'derived-userset' | 'derived-ttu' | 'derived-tupleset-ttu'
    positive: bool
    storage: bool = False   # True iff this family holds the relation's raw stored tuples


@dataclass(frozen=True, slots=True)
class LeafFamily:
    """Namespace classification for one leaf predicate family (I4)."""
    owner_relation: str
    object_type: str
    index: int
    positive: bool
    kind: str               # 'closure' | 'userset-storage'
    storage: bool = False


@dataclass(frozen=True, slots=True)
class DerivedFamily:
    """Namespace classification for a derived relation's public predicate family."""
    relation: str
    object_type: str


@dataclass(frozen=True, slots=True)
class DependentEdge:
    """One invalidation fan-out edge (boolean spec §5.2): when the keyed relation's
    state changes on some object, ``dependent`` must reconcile."""
    dependent: tuple[str, str]          # (object_type, relation)
    via: str                            # 'computed' | 'userset' | 'ttu' | 'tupleset-ttu'
    tupleset_rel: str | None = None
    leaf: str | None = None             # storage leaf, for via='userset'


@dataclass
class Plan:
    """One derived relation's executable plan. ``check_fn(ctx, subject) -> bool`` and
    ``stars_fn(ctx) -> frozenset[shape]`` are closure-composed (no AST walk, no
    per-node dispatch, short-circuit); ``ctx`` is the processor's evaluation context
    bound to one (store, object)."""
    key: tuple[str, str]                # (object_type, relation)
    tree: object
    leaves: tuple[LeafSpec, ...]
    deps: tuple[tuple[str, str], ...]   # tainted keys this plan reads
    stratum: int
    check_fn: Callable
    stars_fn: Callable


@dataclass
class CompiledBooleans:
    """The AOT compile output for a boolean-enabled schema (boolean spec §3.4)."""
    tainted: frozenset[tuple[str, str]]
    namespace: dict[tuple[str, str], LeafFamily | DerivedFamily]   # (type, predicate) ->
    plans: dict[tuple[str, str], Plan]
    dependents: dict[tuple[str, str], list[DependentEdge]]
    # Deltas on these (possibly untainted) target relations must fan out to the
    # TTU plans that read them (keyed by the target's (type, relation)).
    target_feeders: dict[tuple[str, str], list[DependentEdge]]
    # Deltas on an (untainted) tupleset relation of a PDerivedTTU invalidate the
    # dependent on the SAME object (a new/removed parent tuple changes the parent set;
    # §5.2 does not enumerate this case but correctness requires it -- deviations P4).
    tupleset_feeders: dict[tuple[str, str], list[DependentEdge]]
    strata: list[list[tuple[str, str]]]

    @property
    def derived_families(self) -> frozenset[tuple[str, str]]:
        return frozenset(k for k, v in self.namespace.items() if isinstance(v, DerivedFamily))

    @property
    def leaf_families(self) -> frozenset[tuple[str, str]]:
        return frozenset(k for k, v in self.namespace.items() if isinstance(v, LeafFamily))


# ---- taint analysis (boolean spec §3.1) ----

def _mentions(key: tuple[str, str], expr: Expr, ast: SchemaAST) -> set[tuple[str, str]]:
    """Declared relations this expr references (Computed, TTU target+tupleset, userset
    Direct restrictions)."""
    object_type = key[0]
    out: set[tuple[str, str]] = set()

    def walk(e: Expr) -> None:
        if isinstance(e, Direct):
            for r in e.restrictions:
                if r.predicate != '...' and (r.type, r.predicate) in ast:
                    out.add((r.type, r.predicate))
        elif isinstance(e, Computed):
            if (object_type, e.relation) in ast:
                out.add((object_type, e.relation))
        elif isinstance(e, TTU):
            if (object_type, e.tupleset_rel) in ast:
                out.add((object_type, e.tupleset_rel))
            for t in _member_types(object_type, e.tupleset_rel, ast, frozenset()):
                if (t, e.target_rel) in ast:
                    out.add((t, e.target_rel))
        elif isinstance(e, (Union, Intersection)):
            for c in e.children:
                walk(c)
        elif isinstance(e, Exclusion):
            walk(e.base)
            walk(e.subtract)

    walk(expr)
    return out


def _contains_boolean(expr: Expr) -> bool:
    if isinstance(expr, (Intersection, Exclusion)):
        return True
    if isinstance(expr, Union):
        return any(_contains_boolean(c) for c in expr.children)
    return False


def _member_types(object_type: str, relation: str, ast: SchemaAST,
                  seen: frozenset) -> frozenset[str]:
    """Entity types that can be *members* of (object_type, relation) -- used to resolve
    which (type, target_rel) keys a TTU's parents can carry. Userset restrictions
    contribute nothing (a userset node is not a TTU parent); Exclusion members come
    from its base only."""
    key = (object_type, relation)
    if key in seen or key not in ast:
        return frozenset()
    seen = seen | {key}

    def walk(e: Expr) -> frozenset[str]:
        if isinstance(e, Direct):
            return frozenset(r.type for r in e.restrictions if r.predicate == '...')
        if isinstance(e, Computed):
            return _member_types(object_type, e.relation, ast, seen)
        if isinstance(e, TTU):
            out: frozenset[str] = frozenset()
            for t in _member_types(object_type, e.tupleset_rel, ast, seen):
                out |= _member_types(t, e.target_rel, ast, seen)
            return out
        if isinstance(e, (Union, Intersection)):
            return frozenset().union(*(walk(c) for c in e.children)) if e.children else frozenset()
        if isinstance(e, Exclusion):
            return walk(e.base)
        raise TypeError(f"unknown Expr node {e!r}")

    return walk(ast[key])


def compute_taint(ast: SchemaAST) -> frozenset[tuple[str, str]]:
    """Tainted = reaches an Intersection/Exclusion through the schema reference graph
    (boolean spec §3.1). Tainted relations become derived predicates; untainted ones
    compile byte-identically to today (the P0 snapshot gate)."""
    mentions = {key: _mentions(key, expr, ast) for key, expr in ast.items()}
    tainted = {key for key, expr in ast.items() if _contains_boolean(expr)}
    changed = True
    while changed:
        changed = False
        for key, deps in mentions.items():
            if key not in tainted and deps & tainted:
                tainted.add(key)
                changed = True
    return frozenset(tainted)


# ---- plan construction + leaf emission (boolean spec §3.2/§3.3) ----

def _is_pure(expr: Expr, object_type: str, tainted: frozenset, ast: SchemaAST) -> bool:
    """True iff the subtree has no boolean operator and no derived-relation reference
    (i.e. it can be a closure-leaf)."""
    if isinstance(expr, Direct):
        return all(not (r.predicate != '...' and (r.type, r.predicate) in tainted)
                   for r in expr.restrictions)
    if isinstance(expr, Computed):
        return (object_type, expr.relation) not in tainted
    if isinstance(expr, TTU):
        if (object_type, expr.tupleset_rel) in tainted:
            return False
        return all((t, expr.target_rel) not in tainted
                   for t in _member_types(object_type, expr.tupleset_rel, ast, frozenset()))
    if isinstance(expr, Union):
        return all(_is_pure(c, object_type, tainted, ast) for c in expr.children)
    return False    # Intersection / Exclusion


def _emit_leaf_expr(expr: Expr, object_type: str, public_relation: str, leaf: str,
                    out: list) -> None:
    """Compile one closure-leaf subtree. Directs become RewriteFilters (admission
    matches the PUBLIC relation name; routing lands on the leaf); Computed/TTU become
    ordinary Rules targeting the leaf. Mirrors _emit_expr's pattern shapes exactly."""
    if isinstance(expr, Union):
        for c in expr.children:
            _emit_leaf_expr(c, object_type, public_relation, leaf, out)
    elif isinstance(expr, Direct):
        for r in expr.restrictions:
            out.append(RewriteFilter(
                if_pattern=RelationalTriplePattern(
                    subject_predicate=(Ellipsis if r.predicate == '...' else r.predicate),
                    subject_type=r.type,
                    subject_name=('*' if r.wildcard else None),
                    relation=public_relation,
                    object_type=object_type,
                    object_match_wildcards=True,
                ),
                rewrite_relation=leaf,
            ))
    elif isinstance(expr, Computed):
        out.append(Rule(
            RelationalTriplePattern(relation=expr.relation, object_type=object_type,
                                    match_wildcards=True),
            RelationalTriplePattern(relation=leaf, object_type=object_type,
                                    match_wildcards=True),
        ))
    elif isinstance(expr, TTU):
        out.append(Rule(
            RelationalTriplePattern(relation=expr.tupleset_rel, object_type=object_type,
                                    match_wildcards=True),
            RelationalTriplePattern(subject_predicate=expr.target_rel, relation=leaf,
                                    object_type=object_type, match_wildcards=True),
        ))
    else:
        raise TypeError(f"boolean/derived node inside a closure-leaf: {expr!r}")


def _build_plan_tree(key: tuple[str, str], expr: Expr, tainted: frozenset,
                     ast: SchemaAST, out_rules: list):
    """Normalize one derived relation's AST into a plan tree, allocating leaf indexes
    pre-order left-to-right over persisted-leaf positions (closure leaves + userset
    storage leaves) and emitting their Filters/Rules."""
    object_type, relation = key
    counter = [0]

    def alloc(subtree_for_emission: Expr | None, *, userset: Restriction | None = None,
              positive: bool = True):
        leaf = f'{relation}.{counter[0]}'
        counter[0] += 1
        if userset is not None:
            # storage leaf for a tainted userset restriction: one RewriteFilter
            out_rules.append(RewriteFilter(
                if_pattern=RelationalTriplePattern(
                    subject_predicate=userset.predicate,
                    subject_type=userset.type,
                    subject_name=('*' if userset.wildcard else None),
                    relation=relation,
                    object_type=object_type,
                    object_match_wildcards=True,
                ),
                rewrite_relation=leaf,
            ))
        else:
            _emit_leaf_expr(subtree_for_emission, object_type, relation, leaf, out_rules)
        return leaf

    def _split_pure(e: Expr) -> tuple[tuple, list]:
        """Flatten a pure subtree into (Direct restrictions, other exprs) -- pure
        subtrees are unions of {Direct, Computed, TTU}, so the split is lossless."""
        if isinstance(e, Direct):
            return e.restrictions, []
        if isinstance(e, Union):
            restrictions: tuple = ()
            others: list = []
            for c in e.children:
                r, o = _split_pure(c)
                restrictions += r
                others += o
            return restrictions, others
        return (), [e]

    def build(e: Expr, positive: bool):
        if _is_pure(e, object_type, tainted, ast):
            # Direct restrictions get their OWN storage leaf: its edges are exactly
            # the relation's raw stored tuples (never mixed with rule-routed state),
            # which TTU-over-this-relation parent enumeration depends on.
            restrictions, others = _split_pure(e)
            nodes = []
            if restrictions:
                nodes.append(PClosureLeaf(
                    alloc(Direct(tuple(restrictions)), positive=positive),
                    positive, storage=True))
            if others:
                sub = others[0] if len(others) == 1 else Union(tuple(others))
                nodes.append(PClosureLeaf(alloc(sub, positive=positive), positive))
            return nodes[0] if len(nodes) == 1 else PUnion(tuple(nodes))
        if isinstance(e, Union):
            return PUnion(tuple(build(c, positive) for c in e.children))
        if isinstance(e, Intersection):
            return PIntersection(tuple(build(c, positive) for c in e.children))
        if isinstance(e, Exclusion):
            return PExclusion(build(e.base, positive), build(e.subtract, not positive))
        if isinstance(e, Direct):
            # mixed restrictions: pure subset -> one closure-leaf; each tainted userset
            # restriction -> its own derived-userset node with a storage leaf.
            pure = tuple(r for r in e.restrictions
                         if not (r.predicate != '...' and (r.type, r.predicate) in tainted))
            nodes = []
            if pure:
                nodes.append(PClosureLeaf(alloc(Direct(pure), positive=positive),
                                          positive, storage=True))
            for r in e.restrictions:
                if r.predicate != '...' and (r.type, r.predicate) in tainted:
                    if r.wildcard:
                        raise UnsupportedByGraphIndex(
                            f"relation {object_type}#{relation}: wildcard userset "
                            f"restriction [{r.type}:*#{r.predicate}] over the derived "
                            f"relation {r.type}#{r.predicate} needs symbolic composition "
                            f"through residues (v1 scope hook; see spec-deviations)")
                    nodes.append(PDerivedUserset(r.type, r.predicate,
                                                 alloc(None, userset=r, positive=positive),
                                                 positive))
            return nodes[0] if len(nodes) == 1 else PUnion(tuple(nodes))
        if isinstance(e, Computed):
            return PDerivedComputed(e.relation, positive)
        if isinstance(e, TTU):
            parent_types = tuple(sorted(_member_types(object_type, e.tupleset_rel, ast, frozenset())))
            if (object_type, e.tupleset_rel) in tainted:
                return PDerivedTuplesetTTU(e.target_rel, e.tupleset_rel, positive, parent_types)
            return PDerivedTTU(e.target_rel, e.tupleset_rel, positive, parent_types)
        raise TypeError(f"unknown Expr node {e!r}")

    return build(expr, True)


def _plan_leaves(tree) -> tuple[LeafSpec, ...]:
    out: list[LeafSpec] = []

    def walk(n) -> None:
        if isinstance(n, PClosureLeaf):
            out.append(LeafSpec(n.predicate, 'closure', n.positive, storage=n.storage))
        elif isinstance(n, PDerivedComputed):
            out.append(LeafSpec(n.relation, 'derived-computed', n.positive))
        elif isinstance(n, PDerivedUserset):
            out.append(LeafSpec(n.predicate, 'derived-userset', n.positive, storage=True))
        elif isinstance(n, PDerivedTTU):
            out.append(LeafSpec(n.target_rel, 'derived-ttu', n.positive))
        elif isinstance(n, PDerivedTuplesetTTU):
            out.append(LeafSpec(n.target_rel, 'derived-tupleset-ttu', n.positive))
        elif isinstance(n, (PUnion, PIntersection)):
            for c in n.children:
                walk(c)
        elif isinstance(n, PExclusion):
            walk(n.base)
            walk(n.subtract)

    walk(tree)
    return tuple(out)


# ---- executable plans (boolean spec §3.4: no AST walk, short-circuit) ----

def _compile_check_fn(node) -> Callable:
    if isinstance(node, PClosureLeaf):
        pred = node.predicate
        return lambda ctx, s: ctx.leaf_check(pred, s)
    if isinstance(node, PDerivedComputed):
        rel = node.relation
        return lambda ctx, s: ctx.derived_check(rel, s)
    if isinstance(node, PDerivedUserset):
        leaf, t, p = node.predicate, node.subject_type, node.subject_predicate
        return lambda ctx, s: ctx.userset_check(leaf, t, p, s)
    if isinstance(node, PDerivedTTU):
        tr, ts, pt = node.target_rel, node.tupleset_rel, node.parent_types
        return lambda ctx, s: ctx.ttu_check(tr, ts, pt, s)
    if isinstance(node, PDerivedTuplesetTTU):
        tr, ts, pt = node.target_rel, node.tupleset_rel, node.parent_types
        return lambda ctx, s: ctx.tupleset_ttu_check(tr, ts, pt, s)
    if isinstance(node, PUnion):
        fns = tuple(_compile_check_fn(c) for c in node.children)
        return lambda ctx, s: any(f(ctx, s) for f in fns)
    if isinstance(node, PIntersection):
        fns = tuple(_compile_check_fn(c) for c in node.children)
        return lambda ctx, s: all(f(ctx, s) for f in fns)
    if isinstance(node, PExclusion):
        base_fn, sub_fn = _compile_check_fn(node.base), _compile_check_fn(node.subtract)
        return lambda ctx, s: base_fn(ctx, s) and not sub_fn(ctx, s)
    raise TypeError(f"unknown plan node {node!r}")


def _compile_stars_fn(node) -> Callable:
    """The star fold (boolean spec §5.3 step 1), lifted rule-for-rule from the set
    engine's MemberSet algebra (memberset.py:115/121/127): Union -> |, Intersection ->
    &, Exclusion -> minus, over frozensets of subject shapes."""
    if isinstance(node, PClosureLeaf):
        pred = node.predicate
        return lambda ctx: ctx.leaf_stars(pred)
    if isinstance(node, PDerivedComputed):
        rel = node.relation
        return lambda ctx: ctx.derived_stars(rel)
    if isinstance(node, PDerivedUserset):
        leaf, t, p = node.predicate, node.subject_type, node.subject_predicate
        return lambda ctx: ctx.userset_stars(leaf, t, p)
    if isinstance(node, PDerivedTTU):
        tr, ts, pt = node.target_rel, node.tupleset_rel, node.parent_types
        return lambda ctx: ctx.ttu_stars(tr, ts, pt)
    if isinstance(node, PDerivedTuplesetTTU):
        tr, ts, pt = node.target_rel, node.tupleset_rel, node.parent_types
        return lambda ctx: ctx.tupleset_ttu_stars(tr, ts, pt)
    if isinstance(node, PUnion):
        fns = tuple(_compile_stars_fn(c) for c in node.children)
        return lambda ctx: reduce(frozenset.__or__, (f(ctx) for f in fns))
    if isinstance(node, PIntersection):
        fns = tuple(_compile_stars_fn(c) for c in node.children)
        return lambda ctx: reduce(frozenset.__and__, (f(ctx) for f in fns))
    if isinstance(node, PExclusion):
        base_fn, sub_fn = _compile_stars_fn(node.base), _compile_stars_fn(node.subtract)
        return lambda ctx: base_fn(ctx) - sub_fn(ctx)
    raise TypeError(f"unknown plan node {node!r}")


# ---- deps / dependents / strata (boolean spec §1.9, §3.4, §5.2) ----

def _plan_deps_and_fanout(key: tuple[str, str], tree, tainted: frozenset, ast: SchemaAST,
                          dependents: dict, target_feeders: dict,
                          tupleset_feeders: dict) -> tuple:
    object_type, _ = key
    deps: list[tuple[str, str]] = []

    def dep(k: tuple[str, str]) -> None:
        if k not in deps:
            deps.append(k)

    def walk(n) -> None:
        if isinstance(n, PDerivedComputed):
            k = (object_type, n.relation)
            dep(k)
            dependents.setdefault(k, []).append(DependentEdge(key, 'computed'))
        elif isinstance(n, PDerivedUserset):
            k = (n.subject_type, n.subject_predicate)
            dep(k)
            dependents.setdefault(k, []).append(
                DependentEdge(key, 'userset', leaf=n.predicate))
        elif isinstance(n, PDerivedTTU):
            # a new/removed tupleset tuple changes the parent set: invalidate this
            # relation on the tuple's object
            tupleset_feeders.setdefault((object_type, n.tupleset_rel), []).append(
                DependentEdge(key, 'ttu', tupleset_rel=n.tupleset_rel))
            for t in _member_types(object_type, n.tupleset_rel, ast, frozenset()):
                k = (t, n.target_rel)
                if k in tainted:
                    dep(k)
                    dependents.setdefault(k, []).append(
                        DependentEdge(key, 'ttu', tupleset_rel=n.tupleset_rel))
                elif k in ast:
                    # untainted target on this parent type (mixed-type target):
                    # its ordinary closure deltas must still invalidate this plan
                    target_feeders.setdefault(k, []).append(
                        DependentEdge(key, 'ttu', tupleset_rel=n.tupleset_rel))
        elif isinstance(n, PDerivedTuplesetTTU):
            ts_key = (object_type, n.tupleset_rel)
            dep(ts_key)
            dependents.setdefault(ts_key, []).append(
                DependentEdge(key, 'tupleset-ttu', tupleset_rel=n.tupleset_rel))
            for t in _member_types(object_type, n.tupleset_rel, ast, frozenset()):
                target_key = (t, n.target_rel)
                if target_key not in ast:
                    continue
                edge = DependentEdge(key, 'tupleset-ttu', tupleset_rel=n.tupleset_rel)
                if target_key in tainted:
                    dep(target_key)
                    dependents.setdefault(target_key, []).append(edge)
                else:
                    # untainted target: its ordinary closure deltas must still fan out
                    # to this plan (the residue-scan path; see spec-deviations)
                    target_feeders.setdefault(target_key, []).append(edge)
        elif isinstance(n, (PUnion, PIntersection)):
            for c in n.children:
                walk(c)
        elif isinstance(n, PExclusion):
            walk(n.base)
            walk(n.subtract)

    walk(tree)
    return tuple(deps)


def _stratify(plans: dict) -> list[list[tuple[str, str]]]:
    """Topo-order the derived relations by derived-dependency (Kahn). Any SCC through a
    derived relation is a compile error naming the cycle (boolean spec §1.9)."""
    indeg = {k: 0 for k in plans}
    fwd: dict[tuple[str, str], list] = {k: [] for k in plans}
    for k, plan in plans.items():
        for d in plan.deps:
            if d in plans:
                fwd[d].append(k)
                indeg[k] += 1

    strata: list[list[tuple[str, str]]] = []
    frontier = sorted(k for k, d in indeg.items() if d == 0)
    placed = 0
    stratum = 0
    while frontier:
        strata.append(frontier)
        for k in frontier:
            plans[k].stratum = stratum
        placed += len(frontier)
        nxt = []
        for k in frontier:
            for succ in fwd[k]:
                indeg[succ] -= 1
                if indeg[succ] == 0:
                    nxt.append(succ)
        frontier = sorted(set(nxt))
        stratum += 1

    if placed != len(plans):
        cyclic = sorted(k for k, d in indeg.items() if d > 0)
        raise ValueError(
            f"derived relations form a dependency cycle (boolean spec §1.9 forbids "
            f"recursion through boolean relations): {cyclic}")
    return strata


def compile_boolean_schema(ast: SchemaAST, schema_info: SchemaInfo,
                           rules_and_filters: list) -> tuple[CompiledBooleans, SchemaInfo]:
    """Compile every tainted relation: plans + leaf routing appended to
    ``rules_and_filters``; returns the artifacts and a SchemaInfo enriched with the
    derived/leaf namespace facts. Decision-15-family scope restrictions raise
    ``UnsupportedByGraphIndex``; derived-dependency cycles raise ``ValueError``."""
    tainted = compute_taint(ast)

    # Scope restrictions (boolean spec decision 15): object wildcards on derived
    # relations (and their leaves, which are unnameable lexically) are rejected.
    for (t, r) in sorted(schema_info.object_wildcard_shapes):
        if (t, r) in tainted:
            raise UnsupportedByGraphIndex(
                f"object-wildcard shape ({t}, {r}) targets a derived (boolean-tainted) "
                f"relation; symbolic object state on derived relations needs a "
                f"subject-keyed residue (v1 scope hook)")
        if '.' in r:
            raise UnsupportedByGraphIndex(
                f"object-wildcard shape ({t}, {r}) names a compiled leaf predicate")

    namespace: dict[tuple[str, str], LeafFamily | DerivedFamily] = {}
    plans: dict[tuple[str, str], Plan] = {}
    dependents: dict[tuple[str, str], list[DependentEdge]] = {}
    target_feeders: dict[tuple[str, str], list[DependentEdge]] = {}
    tupleset_feeders: dict[tuple[str, str], list[DependentEdge]] = {}

    for key in sorted(tainted):
        object_type, relation = key
        tree = _build_plan_tree(key, ast[key], tainted, ast, rules_and_filters)
        leaves = _plan_leaves(tree)
        deps = _plan_deps_and_fanout(key, tree, tainted, ast, dependents, target_feeders,
                                     tupleset_feeders)
        plans[key] = Plan(key=key, tree=tree, leaves=leaves, deps=deps, stratum=0,
                          check_fn=_compile_check_fn(tree), stars_fn=_compile_stars_fn(tree))
        namespace[(object_type, relation)] = DerivedFamily(relation, object_type)
        for spec in leaves:
            if spec.kind in ('closure', 'derived-userset'):
                idx = int(spec.predicate.rsplit('.', 1)[1])
                namespace[(object_type, spec.predicate)] = LeafFamily(
                    owner_relation=relation, object_type=object_type, index=idx,
                    positive=spec.positive,
                    kind=('closure' if spec.kind == 'closure' else 'userset-storage'),
                    storage=spec.storage)

    strata = _stratify(plans)

    compiled = CompiledBooleans(
        tainted=tainted, namespace=namespace, plans=plans,
        dependents=dependents, target_feeders=target_feeders,
        tupleset_feeders=tupleset_feeders, strata=strata)

    # Exclusivity, compile-time third (boolean spec §3.3): no plain-Filter admission
    # and no Rule then-target lands on a derived-public family.
    derived = compiled.derived_families
    for rf in rules_and_filters:
        if isinstance(rf, RewriteFilter):
            o_t = rf.if_pattern.object_type
            assert (o_t, rf.rewrite_relation) in compiled.leaf_families, \
                f'RewriteFilter routes outside a leaf family: {rf}'
        elif isinstance(rf, Filter):
            assert (rf.if_pattern.object_type, rf.if_pattern.relation) not in derived, \
                f'plain Filter admits a derived-public relation: {rf}'
        elif isinstance(rf, Rule) and rf.then_pattern is not None:
            then_rel = rf.then_pattern.relation
            then_t = rf.then_pattern.object_type or rf.if_pattern.object_type
            assert (then_t, then_rel) not in derived, \
                f'Rule rewrites into a derived-public family: {rf}'

    if not derived and not compiled.leaf_families:
        return compiled, schema_info      # pure schema: nothing to enrich
    enriched = replace(schema_info,
                       derived_families=derived,
                       leaf_families=compiled.leaf_families)
    return compiled, enriched


def parse_openfga_schema(
        schema: str,
        object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset(),
        *,
        enable_boolean: bool = True,
) -> RuleSet:
    """Parse + compile an OpenFGA schema into a graph-index RuleSet (spec §2.1/§2.3).

    Pipeline: ``parse_schema_ast`` -> ``derive_schema_info`` -> ``compile_ruleset``.
    ``object_wildcard_shapes`` are ``(object_type, relation)`` pairs enabling wildcard
    *objects* (e.g. `folder:*`), a deliberate extension beyond OpenFGA that has no DSL
    syntax and so must be declared here.

    Boolean (`and` / `but not`) schemas compile into derived predicates maintained by
    the delta processor (boolean spec §3/§5) -- the P7 matrix flip. Pass
    ``enable_boolean=False`` for the historical refusal behavior.
    """
    ast = parse_schema_ast(schema)
    schema_info = derive_schema_info(ast, object_wildcard_shapes)
    return compile_ruleset(ast, schema_info, enable_boolean=enable_boolean)


# ---- unparser (round-trip property, boolean spec §9) ----

def unparse_schema_ast(ast: SchemaAST) -> str:
    """Render an AST back to DSL text such that ``parse_schema_ast(unparse_schema_ast(a))
    == a``. Operator children inside chains are parenthesized (the grammar's `unit`);
    leaves render bare."""

    def render_restriction(r: Restriction) -> str:
        s = r.type + (':*' if r.wildcard else '')
        if r.predicate != '...':
            s += f'#{r.predicate}'
        return s

    def render(e: Expr, *, top: bool = False) -> str:
        if isinstance(e, Direct):
            return '[' + ', '.join(render_restriction(r) for r in e.restrictions) + ']'
        if isinstance(e, Computed):
            return e.relation
        if isinstance(e, TTU):
            return f'{e.target_rel} from {e.tupleset_rel}'
        if isinstance(e, Union):
            return ' or '.join(_unit(c) for c in e.children)
        if isinstance(e, Intersection):
            return ' and '.join(_unit(c) for c in e.children)
        if isinstance(e, Exclusion):
            base = _chain(e.base)
            sub = _chain(e.subtract)
            return f'{base} but not {sub}'
        raise TypeError(f"unknown Expr node {e!r}")

    def _unit(e: Expr) -> str:
        # chain units: operators need parens, leaves don't
        if isinstance(e, (Union, Intersection, Exclusion)):
            return f'({render(e)})'
        return render(e)

    def _chain(e: Expr) -> str:
        # exclusion operands are chains: a nested exclusion needs parens
        if isinstance(e, Exclusion):
            return f'({render(e)})'
        return render(e)

    types_in_order: list[str] = []
    for (t, _rel) in ast:
        if t not in types_in_order:
            types_in_order.append(t)

    lines: list[str] = []
    for t in types_in_order:
        lines.append(f'type {t}')
        rels = [(rel, expr) for (tt, rel), expr in ast.items() if tt == t]
        if rels:
            lines.append('  relations')
            for rel, expr in rels:
                lines.append(f'    define {rel}: {render(expr, top=True)}')
        lines.append('')
    return '\n'.join(lines)


def generate_example_ruleset() -> RuleSet:
    """
    NOTE: WINDSURF WROTE THIS CODE
    Generate a RuleSet from the Google Drive example OpenFGA schema.
    """
    schema = '''
    model
      schema 1.1

    type user

    type domain
      relations
        define member: [user]

    type folder
      relations
        define can_share: writer
        define owner: [user, domain#member] or owner from parent_folder
        define parent_folder: [folder]
        define viewer: [user, domain#member] or writer or viewer from parent_folder
        define writer: [user, domain#member] or owner or writer from parent_folder

    type document
      relations
        define can_share: writer
        define owner: [user, domain#member] or owner from parent_folder
        define parent_folder: [folder]
        define viewer: [user, domain#member] or writer or viewer from parent_folder
        define writer: [user, domain#member] or owner or writer from parent_folder
    '''
    return parse_openfga_schema(schema)


if __name__ == '__main__':
    # Test the parser with the Google Drive example
    ruleset = generate_example_ruleset()

    # Test some example triples
    test_triples = [
        # Direct user ownership
        RelationalTriple(Entity('user', 'alice'), 'owner', Entity('folder', 'root')),
        # Domain member ownership
        RelationalTriple(Entity('domain', 'example.com'), 'member', Entity('user', 'bob')),
        # Parent folder inheritance
        RelationalTriple(Entity('folder', 'root'), 'parent_folder', Entity('folder', 'subfolder')),
        # Writer implies viewer
        RelationalTriple(Entity('user', 'charlie'), 'writer', Entity('document', 'doc1')),
    ]

    for triple in test_triples:
        print(f"\nProcessing: {triple}")
        for result in ruleset.apply(triple):
            print(f"Generated: {result}")

if __name__ == '__main__':
    # https://github.com/openfga/sample-stores/blob/main/stores/github/model.fga
    # (the openfga dsl is slightly nicer than the spicedb dsl)
    rules_and_filters = RuleSet([
        # model
        #   schema 1.1

        # type user

        # type team
        #   relations
        #     define member: [user, team#member]
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='member', object_type='team')),

        # type organization
        #   relations
        #     define owner: [user]
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='owner', object_type='organization')),
        #     define member: [user] or owner
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='member', object_type='organization')),
        Rule(RelationalTriplePattern(relation='owner', object_type='organization'),
             RelationalTriplePattern(relation='member', object_type='organization')),
        #     define repo_admin: [user, organization#member]
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='repo_admin', object_type='organization')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='organization',
                                       relation='repo_admin', object_type='organization')),
        #     define repo_writer: [user, organization#member]
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='repo_writer', object_type='organization')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='organization',
                                       relation='repo_writer', object_type='organization')),
        #     define repo_reader: [user, organization#member]
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='repo_reader', object_type='organization')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='organization',
                                       relation='repo_reader', object_type='organization')),

        # type repo
        #   relations
        #     define owner: [organization]
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='organization',
                                       relation='owner', object_type='repo')),
        #     define admin: [user, team#member] or repo_admin from owner
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='admin', object_type='repo')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='team',
                                       relation='admin', object_type='repo')),
        Rule(RelationalTriplePattern(subject_predicate=..., subject_type='organization',
                                     relation='owner', object_type='repo'),
             RelationalTriplePattern(subject_predicate='repo_admin', relation='admin')),
        #     define maintainer: [user, team#member] or admin
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='maintainer', object_type='repo')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='team',
                                       relation='maintainer', object_type='repo')),
        Rule(RelationalTriplePattern(relation='admin', object_type='repo'),
             RelationalTriplePattern(relation='maintainer', object_type='repo')),
        #     define writer: [user, team#member] or maintainer or repo_writer from owner
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='writer', object_type='repo')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='team',
                                       relation='writer', object_type='repo')),
        Rule(RelationalTriplePattern(relation='maintainer', object_type='repo'),
             RelationalTriplePattern(relation='writer', object_type='repo')),
        Rule(RelationalTriplePattern(subject_predicate=..., subject_type='organization',
                                     relation='owner', object_type='repo'),
             RelationalTriplePattern(subject_predicate='repo_writer', relation='writer')),
        #     define triager: [user, team#member] or writer
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='triager', object_type='repo')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='team',
                                       relation='triager', object_type='repo')),
        Rule(RelationalTriplePattern(relation='writer', object_type='repo'),
             RelationalTriplePattern(relation='triager', object_type='repo')),
        #     define reader: [user, team#member] or triager or repo_reader from owner
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='reader', object_type='repo')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='team',
                                       relation='reader', object_type='repo')),
        Rule(RelationalTriplePattern(relation='triager', object_type='repo'),
             RelationalTriplePattern(relation='reader', object_type='repo')),
        Rule(RelationalTriplePattern(subject_predicate=..., subject_type='organization',
                                     relation='owner', object_type='repo'),
             RelationalTriplePattern(subject_predicate='repo_reader', relation='reader')),
    ])

    pprint(list(rules_and_filters.apply(RelationalTriple(Entity('user', 'A'), 'admin', Entity('repo', 'X')))))
    pprint(list(rules_and_filters.apply(RelationalTriple(Entity('user', 'A'), 'owner', Entity('team', 'X')))))
    pprint(list(rules_and_filters.apply(RelationalTriple(Entity('organization', 'O'), 'owner', Entity('team', 'X')))))
    pprint(list(rules_and_filters.apply(RelationalTriple(Entity('organization', 'O'), 'owner', Entity('repo', 'X')))))

    print(RelationalTriple(subject=Entity(type='organization', name='O'),
                           relation='admin',
                           object=Entity(type='repo', name='X'),
                           subject_predicate='repo_admin',
                           ).node_from)
    print(RelationalTriple(subject=Entity(type='organization', name='O'),
                           relation='admin',
                           object=Entity(type='repo', name='X'),
                           subject_predicate='repo_admin',
                           ).node_to)
