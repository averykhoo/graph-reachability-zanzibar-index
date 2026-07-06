import re
from dataclasses import dataclass
from pprint import pprint
from types import EllipsisType

from index_v2 import Node


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

    def apply(self, relational_triple: RelationalTriple):
        unprocessed = set()
        for rule in self.rules_and_filters:
            if not isinstance(rule, Filter):
                continue
            if rule.apply(relational_triple):
                unprocessed.add(relational_triple)
                break
        else:
            return

        processed = set()
        while unprocessed:
            relational_triple = unprocessed.pop()
            if relational_triple in processed:
                continue
            yield relational_triple

            processed.add(relational_triple)
            for rule in self.rules_and_filters:
                if not isinstance(rule, Rule):
                    continue
                if (_result := rule.apply(relational_triple)) is not None:
                    unprocessed.add(_result)


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


def compile_ruleset(ast: SchemaAST, schema_info: SchemaInfo) -> RuleSet:
    """Compile a (pure-union) AST into the graph index's Filters/Rules (spec §2.3).

    Raises ``UnsupportedByGraphIndex`` (naming the relation) on the first ``and`` /
    ``but not`` encountered, so the graph backend never silently mis-ingests a boolean
    schema.
    """
    rules_and_filters: list[Rule | Filter] = []
    for (object_type, relation_name), expr in ast.items():
        _emit_expr(expr, object_type, relation_name, rules_and_filters)
    return RuleSet(rules_and_filters, schema_info=schema_info)


def parse_openfga_schema(
        schema: str,
        object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset(),
) -> RuleSet:
    """Parse + compile an OpenFGA schema into a graph-index RuleSet (spec §2.1/§2.3).

    Pipeline: ``parse_schema_ast`` -> ``derive_schema_info`` -> ``compile_ruleset``.
    ``object_wildcard_shapes`` are ``(object_type, relation)`` pairs enabling wildcard
    *objects* (e.g. `folder:*`), a deliberate extension beyond OpenFGA that has no DSL
    syntax and so must be declared here. Boolean (`and` / `but not`) schemas raise
    ``UnsupportedByGraphIndex`` -- parse to an AST directly for those.
    """
    ast = parse_schema_ast(schema)
    schema_info = derive_schema_info(ast, object_wildcard_shapes)
    return compile_ruleset(ast, schema_info)


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
