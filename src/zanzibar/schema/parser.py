"""Tokenizer + recursive-descent parser for the OpenFGA-style DSL, and the parse-time refusals.

Part of `zanzibar.schema`; split out of the single-file module by TK120 (2026-10-06).
"""
from .errors import IDENTIFIER_CHARSET, is_valid_identifier
from .syntax import Computed, Direct, Exclusion, Expr, Intersection, Restriction, SchemaAST, TTU, Union, _RESERVED, _directs_only, _iter_directs, _iter_ttus
from .rules import parse_relation_rule


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
        elif c == ']':
            # a ']' outside a bracket previously made the word-scan below produce a
            # zero-length token without advancing i -- an infinite loop on any
            # schema typo like '[user]]' (blind-audit S-1: a DoS on schema text)
            raise ValueError(f"unexpected ']' in relation body {body!r}")
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
            assert j > i, f'tokenizer made no progress at {body[i:]!r}'
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
                    # REFUSED SHAPE: ``or`` and ``and`` mixed in one chain without
                    # parentheses (``a or b and c``). WHY: the grammar gives them no
                    # relative precedence, so either reading would be a guess -- and the two
                    # readings grant different subjects.
                    # INSTEAD: parenthesise the intended reading: ``(a or b) and c`` or
                    # ``a or (b and c)``.
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


def _validate_declared_name(kind: str, name: str) -> None:
    """A declared type or relation name must be writable: inside the write identifier
    charset (`IDENTIFIER_CHARSET`, 1-256 chars). Shared by the DSL and JSON front ends; its
    independent twin is `tests/oracle.py::_validate_declared_name`. Map:
    `docs/p23-parser-refusal-parity-2026-10-03.md`."""
    # REFUSED SHAPE (P23): a declared type or relation name outside the write identifier
    # charset -- ``define *: ...``, ``define can view: ...``, ``type d#oc``, a non-ASCII or a
    # 257-character name. WHY: no write can ever land on such a name (the charset is
    # enforced at write admission, `validate_write_identifiers`), yet a computed or TTU arm
    # can still reach it. Through ``define *: viewer but not blocked`` a VALID write on
    # ``viewer`` was refused (`AdmissionRejected invalid relation '*'`) and the async index
    # stalled; `TK55`'s empty name, the same class, gave a wrong answer.
    # INSTEAD: name it inside ``[A-Za-z0-9_/@+=-]`` (``.`` is also allowed in a TYPE name),
    # e.g. ``define can_view: [user]``.
    if not is_valid_identifier(name):
        raise ValueError(
            f"declared {kind} name {name!r}: must match [{IDENTIFIER_CHARSET}] (1-256 chars), "
            f"the write identifier charset, or no write could ever reach it")


def parse_schema_ast(schema: str) -> SchemaAST:
    """Parse an OpenFGA DSL string into ``{(object_type, relation): Expr}`` (spec §2.2).

    Succeeds for well-formed, SELF-CONSISTENT syntax (`_validate_ast_consistency`),
    including boolean (``and`` / ``but not``) definitions -- refusing booleans is
    compilation's job, not parsing's.
    """
    ast = _parse_schema_ast_unchecked(schema)
    _validate_ast_consistency(ast)
    _validate_tuplesets_direct(ast)
    _validate_stratified_negation(ast)
    return ast


def _parse_schema_ast_unchecked(schema: str) -> SchemaAST:
    """`parse_schema_ast` WITHOUT the self-consistency refusal (every other refusal
    stays). Only for the non-raising scope reports, which must describe a dangling or
    cyclic schema rather than raise on it (`w4_fragment_report`, `graph_admission_report`)."""
    ast: SchemaAST = {}
    current_type: str | None = None
    seen_types: set[str] = set()

    for line in schema.strip().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        words = line.split()
        head = words[0]
        if head in ('model', 'schema', 'relations'):
            continue
        if head == 'type':
            if len(words) != 2:
                raise ValueError(f'malformed type declaration: {line!r}')
            current_type = words[1]
            _validate_declared_name('type', current_type)
            # duplicate type blocks silently merged before -- a pasted schema with a
            # duplicate silently rewrote relations (blind-audit S-6)
            # REFUSED SHAPE (blind-audit S-6): a second ``type X`` block. WHY: the comment
            # above.
            # INSTEAD: put every relation of the type under ONE ``type doc`` block.
            if current_type in seen_types:
                raise ValueError(f'duplicate type declaration: {current_type!r}')
            seen_types.add(current_type)
        elif head == 'define':
            if not current_type:
                raise ValueError("Relation definition without type context")
            relation_name, colon, body = line[len('define'):].strip().partition(':')
            relation_name = relation_name.strip()
            if not colon:
                raise ValueError(f'malformed relation definition (missing colon): {line!r}')
            # Empty-name lock (TK55, 2026-09-06): `define : [user]` used to parse and
            # compile to a Filter on relation ''. No write can ever land on '' (the
            # identifier charset is 1-256 chars), but a COMPUTED reference to it
            # (`define : viewer`) is reachable through a valid write on `viewer` --
            # and there the backends diverged: the set engine answered check True
            # on '' while the graph answered False (untainted) or refused the write
            # in `DeltaProcessor._write_derived` (boolean). Refusing at parse time
            # is what makes `FullScope.lean::GraphAdmission.keysNonempty` a Python
            # scope claim rather than an assumption. The rest of the identifier charset
            # is `_validate_declared_name` below (P23, 2026-10-03e); this check stays
            # separate so its message keeps naming the enclosing type.
            # REFUSED SHAPE (TK55): an empty declared relation name, ``define : [user]``.
            # WHY: the comment above. INSTEAD: name it -- ``define viewer: [user]``.
            if not relation_name:
                raise ValueError(
                    f"type {current_type!r}: a declared relation name may not be empty "
                    f"({line!r})")
            # Lexical collision lock (boolean spec §3.2): '.' is reserved for synthetic
            # leaf predicates ('<relation>.<index>'), so a *declared* relation name may
            # never contain it. Tuple-side entity names remain unrestricted.
            # REFUSED SHAPE (boolean spec §3.2): ``.`` in a declared relation name. WHY: the
            # comment above.
            # INSTEAD: use ``_`` -- ``define can_view: [user]`` rather than ``can.view``.
            if '.' in relation_name:
                raise ValueError(
                    f"relation {relation_name!r}: '.' is reserved for compiled leaf "
                    f"predicates and cannot appear in a declared relation name")
            _validate_declared_name('relation', relation_name)
            # REFUSED SHAPE: a second ``define viewer`` in the same type.
            # WHY: the assignment below would silently replace the first definition, so the
            # store would run a schema other than the one written.
            # INSTEAD: ONE ``define`` joining the arms --
            # ``define viewer: [user] or editor`` (``and`` / ``but not`` if that is the
            # intended combination).
            if (current_type, relation_name) in ast:
                raise ValueError(
                    f'duplicate relation definition: {current_type}#{relation_name}')
            tokens = _tokenize_relation_body(body.strip())
            ast[(current_type, relation_name)] = _RelationParser(tokens, relation_name).parse()
        else:
            # silently dropping unrecognized lines lost or misattributed whole
            # relation definitions (blind-audit S-3)
            raise ValueError(f'unrecognized schema line: {line!r}')

    _validate_ast_references(ast)
    return ast


def _validate_ast_references(ast: SchemaAST) -> None:
    """Referenced predicates may not use the reserved leaf namespace (the '.'-lock
    was previously bypassable through restriction predicates, Computed refs, and TTU
    refs -- blind-audit S-5: a `[doc#viewer.0]` restriction was a foreign write
    handle into a compiled leaf family)."""
    def check_name(name: str, where: str) -> None:
        # REFUSED SHAPE (blind-audit S-5): ``.`` in a REFERENCED name -- ``[doc#viewer.0]``,
        # ``viewer.0``, ``viewer.0 from parent``. WHY: the docstring above: ``.``-names are
        # the compiler's leaf predicates, so a reference reads or writes compiled state.
        # INSTEAD: reference the public relation -- ``[doc#viewer]``, ``viewer``.
        if '.' in name and name != '...':
            raise ValueError(
                f"{where}: {name!r} is inside the reserved leaf namespace "
                f"('.' in referenced relation names)")

    for (object_type, relation), expr in ast.items():
        where = f'{object_type}#{relation}'

        def walk(e: Expr) -> None:
            if isinstance(e, Direct):
                for r in e.restrictions:
                    check_name(r.predicate, where)
            elif isinstance(e, Computed):
                check_name(e.relation, where)
            elif isinstance(e, TTU):
                check_name(e.target_rel, where)
                check_name(e.tupleset_rel, where)
            elif isinstance(e, (Union, Intersection)):
                for c in e.children:
                    walk(c)
            elif isinstance(e, Exclusion):
                walk(e.base)
                walk(e.subtract)

        walk(expr)


def _iter_refs(expr: Expr):
    """Every Computed / TTU node anywhere in ``expr``, through every operator."""
    if isinstance(expr, (Computed, TTU)):
        yield expr
    elif isinstance(expr, (Union, Intersection)):
        for c in expr.children:
            yield from _iter_refs(c)
    elif isinstance(expr, Exclusion):
        yield from _iter_refs(expr.base)
        yield from _iter_refs(expr.subtract)


def _validate_ast_consistency(ast: SchemaAST) -> None:
    """A schema must be SELF-CONSISTENT: every referenced relation is declared, and no
    relation depends on itself through schema references (ASK-1, user decision
    2026-09-26). OpenFGA refuses both (`pkg/typesystem/typesystem.go::
    isUsersetRewriteValid`, `::validateTypeRestrictions`, `::hasCycle`).

    Before this, a dangling reference silently meant "empty" and a computed cycle was
    answered by a fixpoint. Both backends and the oracle agreed on those answers, but no
    headline theorem covers them: they are exactly the `GraphAdmission` fields `matchDecl`
    and `ranked`, which were the premise's only SILENT fields (TK104). This refusal makes
    both LOUD. `graph_admission_report` still reports them: it reads a hand-built
    `SchemaAST` or `_parse_schema_ast_unchecked`, never this refusal.

    * A computed ref ``editor`` and a TTU tupleset ``parent`` must be declared on the
      defining type.
    * A TTU target must be declared on at least one type the tupleset admits, or on any
      type when the tupleset admits none.
    * A userset restriction ``[group#member]`` must name a declared relation. Bare subject
      types (``[user]``) are NOT checked, because a relation-less ``type`` line leaves no
      trace in a `SchemaAST`.
    * No cycle of computed / TTU-tupleset references, through any operator. Recursion
      through stored tuples (nested groups ``[group#member]``, folders ``x from parent``,
      OpenFGA's self-referential boolean flag) makes no such edge and stays legal. A
      DERIVED cycle through a TTU target or a userset restriction is not caught here: if a
      step on it is inside a ``but not`` subtrahend, `_validate_stratified_negation`
      refuses it at parse (TK114); otherwise `_stratify` refuses it on the graph only
      (`CyclicDerivedDependency`).

    Every dangling-reference message contains ``undeclared relation`` and every cycle
    message ``depend on themselves``; `tests/genswarm.py::REJECTION_WITNESSES` matches on
    them.

    The oracle carries an independent twin (`tests/oracle.py::_validate_consistency`)."""
    deps: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for (object_type, relation), expr in ast.items():
        where = f'{object_type}#{relation}'
        for d in _iter_directs(expr):
            for r in d.restrictions:
                # REFUSED SHAPE (ASK-1): ``[group#member]`` where ``group#member`` is
                # undeclared.
                # WHY (all five refusals in this function): the docstring -- a dangling
                # reference silently meant "empty" and a computed cycle was answered by a
                # fixpoint; no headline theorem covers either, and OpenFGA refuses both.
                # INSTEAD: declare it (``type group`` / ``define member: [user]``), or write
                # ``[group]`` if a group object itself was meant.
                if r.predicate != '...' and (r.type, r.predicate) not in ast:
                    raise ValueError(
                        f'{where}: restriction [{r.type}#{r.predicate}] names an undeclared '
                        f'relation {r.type}#{r.predicate}')
        out = deps.setdefault((object_type, relation), set())
        for ref in _iter_refs(expr):
            if isinstance(ref, Computed):
                # REFUSED SHAPE (ASK-1): a computed ref to an undeclared relation
                # (``define viewer: [user] or editor``, no ``editor``). WHY: see above.
                # INSTEAD: declare it on the SAME type (``define editor: [user]``), or fix
                # the spelling.
                if (object_type, ref.relation) not in ast:
                    raise ValueError(
                        f'{where}: references undeclared relation {object_type}#{ref.relation}')
                out.add((object_type, ref.relation))
                continue
            # REFUSED SHAPE (ASK-1): an undeclared tupleset (``viewer from parent``, no
            # ``parent``). WHY: see above. INSTEAD: declare the link on the same type,
            # ``define parent: [folder]``.
            if (object_type, ref.tupleset_rel) not in ast:
                raise ValueError(
                    f'{where}: tupleset of {ref.target_rel!r} from {ref.tupleset_rel!r} is '
                    f'undeclared relation {object_type}#{ref.tupleset_rel}')
            out.add((object_type, ref.tupleset_rel))
            parent_types = {r.type for d in _iter_directs(ast[(object_type, ref.tupleset_rel)])
                            for r in d.restrictions}
            # A tupleset that admits no type is constantly empty; its target must still be
            # declared SOMEWHERE (OpenFGA's schema-1.0 rule), or the name dangles.
            candidates = parent_types or {t for t, _r in ast}
            # REFUSED SHAPE (ASK-1): a TTU target declared on none of the tupleset's types
            # (``viewer from parent``, ``parent: [folder]``, no ``folder#viewer``). WHY: see
            # above. INSTEAD: declare it on the parent type (``type folder`` /
            # ``define viewer: [user]``), or let the tupleset admit a type that has it.
            if not any((t, ref.target_rel) in ast for t in candidates):
                raise ValueError(
                    f'{where}: {ref.target_rel!r} from {ref.tupleset_rel!r} is an undeclared '
                    f'relation on every tupleset type {sorted(candidates)}')
    # Depth-first cycle search over "depends on" edges, reporting the first cycle found.
    state: dict[tuple[str, str], int] = {}          # 1 = on the current path, 2 = done
    for root in deps:
        if root in state:
            continue
        path = [root]
        state[root] = 1
        stack = [iter(sorted(deps[root]))]
        while stack:
            nxt = next(stack[-1], None)
            if nxt is None:
                stack.pop()
                state[path.pop()] = 2
            elif state.get(nxt) == 1:
                # REFUSED SHAPE (ASK-1): a cycle of computed / TTU-tupleset references
                # (``define a: [user] or b`` + ``define b: a``). WHY: see above (OpenFGA
                # ``hasCycle``). INSTEAD: none for a pure alias loop -- delete one
                # direction. Intended recursion goes through STORED tuples, which stays
                # legal: ``define member: [user, group#member]`` or
                # ``define viewer: [user] or viewer from parent``.
                cycle = path[path.index(nxt):] + [nxt]
                raise ValueError(
                    'reference cycle: relations depend on themselves through schema '
                    'references: ' + ' -> '.join(f'{t}#{r}' for t, r in cycle))
            elif nxt not in state:
                state[nxt] = 1
                path.append(nxt)
                stack.append(iter(sorted(deps[nxt])))


def _validate_tuplesets_direct(ast: SchemaAST) -> None:
    """A relation used as a TTU tupleset (the ``parent`` in ``viewer from parent``) must be
    DIRECT-ONLY: ``[folder]``, ``[folder, doc]`` or ``[folder] or [doc]`` (TK106, user
    decision 2026-09-26). OpenFGA refuses the rest: "the relation is referenced in at least
    one tupleset and thus must be a direct relation"
    (`pkg/typesystem/typesystem.go::isUsersetRewriteValid`).

    ``from`` walks the STORED tuples of the tupleset, never its computed membership. So a
    boolean arm (``[folder] but not blocked``), a computed arm (``[folder] or other``) or
    a nested ``from`` on a tupleset was silently ignored by every ``from`` that used it.
    ``parent: [folder] but not [doc]`` even let a doc link be written only because it was
    excluded. Before this, the graph refused the untainted form at compile time and the
    set engine degraded past it, and nothing refused the tainted form. The behaviour-
    preserving rewrite is ``parent_link: [<every type parent names>]``, used by the ``from``.

    Wildcard restrictions (``[folder:*]``, star tuplesets, ASK-2) stay legal here.

    A USERSET restriction on a tupleset (``parent: [folder#member]`` or
    ``[folder:*#member]``) is refused too (TK108, user decision 2026-09-27); see the second
    refusal below for why and for the rewrite.

    Every message of the first refusal contains ``tupleset must be direct``, and every
    message of the second contains ``tupleset may not restrict to a userset``;
    `tests/genswarm.py::REJECTION_WITNESSES` matches on both. The oracle carries an
    independent twin (`tests/oracle.py::_validate_tuplesets_direct`)."""
    for (object_type, relation), expr in ast.items():
        for ttu in _iter_ttus(expr):
            ts_key = (object_type, ttu.tupleset_rel)
            # REFUSED SHAPE (TK106): a tupleset with computed, ``from``, ``and`` or
            # ``but not`` arms. WHY and INSTEAD: the docstring above.
            if ts_key in ast and not _directs_only(ast[ts_key]):
                raise ValueError(
                    f'{object_type}#{relation}: {ttu.target_rel!r} from '
                    f'{ttu.tupleset_rel!r}: a tupleset must be direct (only type '
                    f'restrictions such as [folder] or [folder, doc]), but '
                    f'{object_type}#{ttu.tupleset_rel} has computed, "from", "and" or '
                    f'"but not" arms that "from" would silently ignore, because it '
                    f'walks stored tuples only. Store the links on a direct relation '
                    f'(parent_link: [...]) and use that in the "from" (OpenFGA rule)')
            if ts_key in ast:
                # REFUSED SHAPE (TK108): a userset restriction on a tupleset,
                # ``parent: [folder#member]`` with ``viewer from parent``.
                # WHY: ``from`` takes the stored subject's OBJECT as the parent and
                # never looks at its predicate, so a stored ``folder:f#member`` meant
                # just ``folder:f`` -- the ``#member`` was silently dropped. The set
                # engine and the oracle answered that way while the graph refused the
                # schema at compile time (`_validate_ttu_tuplesets`), so the backends
                # disagreed on whether the schema existed at all. OpenFGA refuses it:
                # tupleset relations must be directly assignable types.
                # INSTEAD: store the bare link, and spell the userset reading as its
                # own TTU. Both answer exactly what the refused shape answered
                # (probed on every backend, `docs/tk108-userset-tuplesets-2026-09-27.md`
                # sec 2; pinned by `tests/test_tk108_userset_tupleset_rewrite.py`):
                #     define parent: [folder]                # was [folder#member]
                #     define parent_member: member from parent   # what `parent` meant
                #     define viewer: viewer from parent      # unchanged
                # ``[folder:*#member]`` becomes ``[folder:*]`` the same way.
                for d in _iter_directs(ast[ts_key]):
                    for r in d.restrictions:
                        if r.predicate != '...':
                            star = ':*' if r.wildcard else ''
                            raise ValueError(
                                f'{object_type}#{relation}: {ttu.target_rel!r} from '
                                f'{ttu.tupleset_rel!r}: a tupleset may not restrict to a '
                                f'userset, but {object_type}#{ttu.tupleset_rel} allows '
                                f'[{r.type}{star}#{r.predicate}]; "from" would ignore '
                                f'the #{r.predicate}. Use [{r.type}{star}] for the link '
                                f'and "{r.predicate} from {ttu.tupleset_rel}" where the '
                                f'userset itself is meant (OpenFGA rule)')


def _validate_stratified_negation(ast: SchemaAST) -> None:
    """No relation may depend on itself through a ``but not`` subtrahend (TK114, decided
    2026-10-04): classical stratified negation. Map:
    `docs/tk114-stratified-negation-2026-10-04.md`.

    The dependency graph runs ``(type, relation) -> (type, relation)`` along a computed
    ref, a TTU's tupleset, a TTU's target on every type the tupleset admits, and a userset
    restriction ``[T#p]`` / ``[T:*#p]``. An edge is NEGATIVE when its node sits anywhere
    inside the subtract of a ``but not``, at any depth. A schema with a cycle through a
    negative edge is refused. Positive recursion (``viewer: [user] or viewer from parent``,
    ``member: [user, group#member] but not banned``) stays legal; the graph still refuses
    a DERIVED one at compile (`_stratify`).

    Runs after `_validate_ast_consistency` and `_validate_tuplesets_direct`, so every
    reference is declared. Every message contains ``recursion through negation``. The
    oracle carries an independent twin (`tests/oracle.py::_validate_stratified_negation`)."""
    edges: dict[tuple[str, str], list[tuple[tuple[str, str], bool]]] = {k: [] for k in ast}
    for (object_type, relation), expr in ast.items():
        out = edges[(object_type, relation)]

        def walk(e: Expr, neg: bool) -> None:
            if isinstance(e, Direct):
                for r in e.restrictions:
                    if r.predicate != '...':
                        out.append(((r.type, r.predicate), neg))
            elif isinstance(e, Computed):
                out.append(((object_type, e.relation), neg))
            elif isinstance(e, TTU):
                ts_key = (object_type, e.tupleset_rel)
                out.append((ts_key, neg))
                for d in _iter_directs(ast.get(ts_key, Direct(()))):
                    for r in d.restrictions:
                        if (r.type, e.target_rel) in ast:
                            out.append(((r.type, e.target_rel), neg))
            elif isinstance(e, (Union, Intersection)):
                for c in e.children:
                    walk(c, neg)
            elif isinstance(e, Exclusion):
                walk(e.base, neg)
                walk(e.subtract, True)

        walk(expr, False)

    for src in sorted(edges):
        for dst, neg in edges[src]:
            if not neg:
                continue
            # Breadth-first from the negative edge's head back to its tail.
            parent: dict[tuple[str, str], tuple[str, str] | None] = {dst: None}
            frontier = [dst]
            while frontier and src not in parent:
                nxt = []
                for k in frontier:
                    for k2, _neg in edges.get(k, ()):
                        if k2 not in parent:
                            parent[k2] = k
                            nxt.append(k2)
                frontier = nxt
            if src in parent:
                # REFUSED SHAPE (TK114): a relation that depends on itself through a
                # ``but not`` subtrahend -- ``define viewer: [user] but not viewer from
                # parent``, or ``member: [user] but not blocked`` with
                # ``blocked: [group#member]``.
                # WHY: such a schema has no fixpoint on some data (``doc:a parent doc:a``
                # makes ``viewer = not viewer``) and several on other data, so there is no
                # answer for the backends to agree on. The set engine and the oracle used to
                # answer anyway, identically, because both seed in-progress recursion with
                # False; their answers were not models of the schema. The graph refused it
                # at compile (`CyclicDerivedDependency`).
                # INSTEAD: subtract a relation that does not depend on the one being
                # defined, and put the recursion in it:
                #     define blocked: [user] or blocked from parent
                #     define viewer: [user] but not blocked
                # A nested ``x but not (y but not z)`` is ``(x but not y) or (x and z)``,
                # which is positive in ``z``.
                path = [src]
                k = src
                while k != dst:
                    k = parent[k]
                    path.append(k)
                cycle = [src] + path[::-1]
                raise ValueError(
                    'recursion through negation: relations depend on themselves through a '
                    '"but not" subtrahend, which has no single meaning: '
                    + ' -> '.join(f'{t}#{r}' for t, r in cycle)
                    + f' (the step out of {src[0]}#{src[1]} is negative)')
