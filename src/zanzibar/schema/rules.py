"""The relational-triple / pattern / rule data model, `SchemaInfo` and `RuleSet`.

Part of `zanzibar.schema`.
"""
# Provenance (moved out of the docstring, TK123 item 14): split out of the single-file module
# by TK120 (2026-10-06).
from dataclasses import dataclass, field
from types import EllipsisType
from .errors import AdmissionRejected, SchemaError, is_valid_identifier
from .syntax import Computed, DeclaredRelations, Restriction, no_restriction_message


@dataclass(frozen=True, slots=True, order=True, unsafe_hash=True)
class Entity:
    """One object or subject: a type and a name, printed ``type:name``.

    ``name`` may be ``'*'``, the wildcard sentinel (``wildcard`` is then True). Frozen,
    hashable and ordered, so it can key a dict or sit in a set. Public since 0.1.0
    because ``RelationalTriple`` (the argument of ``RuleSet.apply``) is built
    from two of them.
    """
    type: str
    name: str

    @property
    def wildcard(self):
        return self.name == '*'

    def __str__(self):
        return f'{self.type}:{self.name}'


@dataclass(frozen=True, slots=True, order=True, unsafe_hash=True)
class RelationalTriple:
    """One relation tuple as ``RuleSet.apply`` takes it: ``subject`` has ``relation`` on
    ``object``.

    ``subject_predicate`` is ``...`` (``Ellipsis``, the default) for a bare subject such as
    ``user:alice``, or a relation name for a userset subject such as ``group:eng#member``.
    It prints in the Zanzibar paper's form, ``object#relation@subject#predicate``. Public
    since 0.1.0.
    """
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
    # Cached frozen sub-patterns (perf N12). The subject/object EntityPatterns are a
    # pure function of the fields above, so build them ONCE at construction (compile
    # time) instead of rebuilding a fresh frozen dataclass on every match()/replace()
    # -- the property construction was ~20% of RuleSet.apply's tottime. init=False keeps
    # them out of __init__, repr=False keeps the compiled-RuleSet snapshot bytes
    # byte-identical, compare=False keeps eq/order over the declared fields only.
    _subject: 'EntityPattern' = field(init=False, repr=False, compare=False, default=None)
    _object: 'EntityPattern' = field(init=False, repr=False, compare=False, default=None)

    def __post_init__(self):
        omw = (self.match_wildcards if self.object_match_wildcards is None
               else self.object_match_wildcards)
        object.__setattr__(self, '_subject', EntityPattern(
            type=self.subject_type, name=self.subject_name, match_wildcards=self.match_wildcards))
        object.__setattr__(self, '_object', EntityPattern(
            type=self.object_type, name=self.object_name, match_wildcards=omw))

    @property
    def _object_match_wildcards(self) -> bool:
        return self.match_wildcards if self.object_match_wildcards is None else self.object_match_wildcards

    @property
    def subject(self):
        return self._subject

    @property
    def object(self):
        return self._object

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

    Users write derived relations by their public names only; each
    ``Direct`` restriction inside a derived relation compiles to one of these, and in
    ``RuleSet.apply`` *every* matching RewriteFilter fires (fan-in expansion, all-match,
    deduped by resulting triple) -- unlike plain Filters, which stay first-match.

    Implemented as a subclass rather than a new field on ``Filter`` so the compiled
    output of pure-union schemas stays byte-identical (Filter reprs unchanged).
    """
    # Provenance (moved out of the docstring, TK123 item 14): boolean spec sec 3.3; the P0
    # snapshot; docs/spec-deviations.md.
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
    """Wildcard-shape metadata derived from a schema.

    You do not build one: ``compile_ruleset`` / ``parse_openfga_schema`` put it on
    ``RuleSet.schema_info``, and ``WildcardIndex(idx, ruleset.schema_info)`` takes it. Treat
    it as read-only; its fields describe the schema and are not a configuration surface.
    Public since 0.1.0 because it appears in those signatures.

    A *shape* is ``(entity_type, predicate)`` where predicate is ``'...'`` for a bare
    entity or a relation name for a userset. This is intentionally dumb: we never do
    static reachability analysis to elide bridges beyond the bare-shape rule below --
    an unnecessary O(1)-degree bridge is harmless, a missing bridge is a correctness bug.
    """
    # Provenance (moved out of the docstring, TK123 item 14): spec §2.3.
    subject_wildcard_shapes: frozenset[tuple[str, str]] = frozenset()   # (type, predicate); '...' for bare
    object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset()    # (type, relation)
    # Derived-predicate namespace facts (boolean spec §3.3/§3.4), populated only by a
    # boolean-enabled compile; empty for pure-union schemas and hand-built rulesets.
    # The façade enforces derived-family write exclusivity from these (boolean spec I5).
    derived_families: frozenset[tuple[str, str]] = frozenset()          # (object_type, relation)
    leaf_families: frozenset[tuple[str, str]] = frozenset()             # (object_type, leaf_predicate)
    # TK113 (2026-10-03b): node shapes `WildcardIndex.remove_node` must refuse, because
    # a write-time rewrite stores COPIES of a tuple on other nodes and deleting one end
    # leaves the copies inconsistent. Populated by `compile_ruleset` from the compiled
    # Rules/RewriteFilters (`_node_removal_fence`); empty for hand-built SchemaInfo.
    unremovable_node_shapes: frozenset[tuple[str, str]] = frozenset()   # (type, predicate); '...' for bare
    # TK144 (TK138 landing 2): the implicit userset self-relation's static SEED table,
    # ``(type, relation, seed)`` triples. ``seed`` is a relation or compiled leaf predicate on
    # ``type`` whose members include the userset ``type:o#relation`` at the SAME object ``o``
    # through computed rewrites alone (``relation`` itself included). It is the transitive
    # closure of the compiled Computed rewrite Rules, so it is what the closure would hold
    # if the self tuple were materialized, without materializing it. Populated by
    # ``compile_ruleset`` for every DECLARED relation (`_self_seed_table`); empty for a
    # hand-built SchemaInfo (``derive_schema_info``), which then reads non-reflexively --
    # consistent with that path applying no compiled rewrite at all (TK144 review
    # 2026-10-17: it was never SetEngine-equivalent; see its docstring). Not serialized by the
    # compiled-RuleSet snapshots (they read two fields only).
    self_seeds: frozenset[tuple[str, str, str]] = frozenset()
    # TK144 (C5): the boolean compile artifacts (``CompiledBooleans``), so the derived read
    # path can evaluate a plan at read time for a userset subject. Not compared, hashed or
    # printed: it is a function of the schema the other fields already describe.
    compiled: object = field(default=None, compare=False, repr=False)

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

    @property
    def crossable_shapes(self) -> frozenset[tuple[str, str]]:
        """Shapes where a path can CROSS ``w_all -> concrete -> w_any``: bridged in
        AND out.

        On such a shape ``(T, p)`` the two wildcard nodes compose through any
        concrete ``(T, x, p)`` -- "granted on all T#p" reaches "some T#p reaches ..."
        the moment one instance exists. That
        existential is ENTITY-wise (the reference oracle witnesses it with
        any tuple-mentioned entity of type ``T``, whatever relation mentioned it), so
        the concrete middle must track ENTITY existence rather than node existence:
        the graph index interns ``(T, x, p)`` -- with both bridges -- for every live
        entity ``x`` of type ``T`` (``WildcardIndex._ensure_entity_middles``).

        Because ``bridged_in_shapes`` excludes bare ``(T, '...')`` shapes, plain
        OpenFGA ``[user:*]`` usage is never crossable and keeps costing zero bridges
        and zero middles."""
        # Provenance (moved out of the docstring, TK123 item 14):
        # ``tests/oracle.py::instances``; invariant I14, docs/spec-deviations.md 2026-08-09.
        # Provenance (moved out of the docstring, TK123 item 14): wildcard-materialization-
        # spec §3.4.
        return self.bridged_in_shapes & self.bridged_out_shapes


@dataclass
class RuleSet:
    rules_and_filters: list[Rule | Filter]
    # Populated by parse_openfga_schema; None for hand-built rulesets. The façade
    # (§6) reads this; ingestion via .apply ignores it (spec §2.3: "returned
    # alongside (or wrapping) the RuleSet").
    schema_info: SchemaInfo | None = None
    # Boolean-compile artifacts (boolean spec §3.4); None for pure-union schemas
    # compiled without enable_boolean and for hand-built rulesets.
    compiled: 'CompiledBooleans | None' = None   # bound at the bottom of this module
    # What the schema declares, for the admission refusal's explanation only (TK123
    # item 17); set by ``compile_ruleset``, None for hand-built rulesets. Never compared.
    declared: DeclaredRelations | None = field(default=None, compare=False, repr=False)

    def __repr__(self) -> str:
        # TK153 F6 (2026-10-17): the dataclass repr printed every compiled Filter and Rule,
        # thousands of characters for a small schema, in every tuple that carries one.
        # ``rules_and_filters`` is the full form.
        plans = len(self.compiled.plans) if self.compiled is not None else 0
        return (f'RuleSet({len(self.rules_and_filters)} rules and filters, '
                f'{plans} boolean relations)')

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
            # AdmissionRejected: same type-restriction admission gate as the set engine
            # (`SetEngine._validate` step 2 rejects `<rel>.<idx>` for want of a declared
            # restriction). A correct refusal of the tuple, not a broken index.
            raise AdmissionRejected(
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
                # AdmissionRejected (reg13, derived arm): no RewriteFilter admits this
                # raw tuple, i.e. no declared type restriction does. The set engine
                # refuses the identical tuple in `_validate`; this is the graph side of
                # ONE admission rule, so it carries the rejection type.
                raise AdmissionRejected(no_restriction_message(
                    self.declared, str(relational_triple), o_type, rel, derived=True))
        else:
            # Pure-union relations keep first-match admission semantics, unchanged.
            for _, flt in self._candidates(self._plain_filters, rel):
                if flt.apply(relational_triple):
                    seeds = {relational_triple}
                    break
            else:
                # No declared type restriction admits this raw tuple.
                if self.schema_info is None:
                    # Hand-built ruleset used as a pure filter/rewrite engine: it has
                    # no "declared restrictions" concept and no set-engine counterpart,
                    # so keep the historical silent-drop-on-no-match filtering semantics.
                    return
                # Schema-derived ruleset: REJECT loudly (ValueError) -- do NOT silently
                # drop. A silent drop vacuously "accepts" (the graph test harnesses
                # report True, having written nothing) while the set engine's
                # `_validate` step 2 raises `ValueError` on the same tuple: an
                # accept/reject (unanimity) divergence for ANY no-restriction-match
                # write -- a wrong-type/wrong-predicate subject, a wildcard userset
                # `T:*#p` under a concrete `[T#p]` restriction, a bare write to a
                # computed-only relation, etc. This mirrors the derived-family branch
                # above (which already raises) and the set engine, restoring parity.
                # In the production apply path tuples are admission-validated by the
                # set engine before they ever reach here, so this only fires on genuine
                # corruption -- exactly what advance_index treats it as
                # (InvariantViolation).
                #
                # It is nonetheless raised as `AdmissionRejected` (reg13, pure-union
                # arm): the RAISE SITE is an admission gate -- it is answering "does a
                # declared type restriction admit this tuple?", exactly as the set
                # engine's `_validate` does, and every harness that calls `apply` with
                # RAW user tuples (tests/test_matrix.py, formal/conformance) is using it
                # as one. Whether reaching it means "the user wrote nonsense" or "the
                # log is corrupt" is a property of the CALLER's provenance guarantee,
                # not of this check -- and the caller that has such a guarantee already
                # says so: `zanzibar.store.apply._apply_row` promotes any ValueError
                # from this path to `InvariantViolation`. `AdmissionRejected` subclasses
                # ValueError, so that promotion is untouched.
                raise AdmissionRejected(no_restriction_message(
                    self.declared, str(relational_triple), o_type, rel))

        # Fast path (the dominant case: a direct restriction with no rewrite rule):
        # if no rule can fire on any seed relation the worklist can never grow, and
        # `seeds` is already a deduped set, so it IS the output. Draining a static
        # set via .pop() yields the same order as iterating it, so this is
        # byte-identical to the worklist below.
        rules = self._rules
        if not any(self._candidates(rules, t.relation) for t in seeds):
            yield from seeds
            return

        # `seeds` is freshly built and owned here (a set comprehension or {triple}),
        # so drain it in place as the worklist rather than copying it into a new set.
        unprocessed = seeds
        processed = set()
        while unprocessed:
            relational_triple = unprocessed.pop()
            if relational_triple in processed:
                continue
            yield relational_triple

            processed.add(relational_triple)
            for _, rule in self._candidates(rules, relational_triple.relation):
                if (_result := rule.apply(relational_triple)) is not None:
                    unprocessed.add(_result)


def replace_relation(triple: RelationalTriple, relation: str) -> RelationalTriple:
    return RelationalTriple(subject=triple.subject, relation=relation,
                            object=triple.object, subject_predicate=triple.subject_predicate)


def norm_pred(pred: 'str | EllipsisType | None') -> str:
    """The storage form of a subject predicate: '...' for the bare-entity sentinel
    (Ellipsis or None), else the relation name unchanged. THE shared normalizer --
    the backends and the composition layer import this instead of keeping copies
    (the oracle keeps its own by the independence contract).

    ``None -> '...'`` is READ-side leniency only. A write validates the RAW predicate
    first (``validate_write_identifiers`` refuses ``None``), then normalises."""
    # Provenance (moved out of the docstring, TK123 item 14): TK125.
    return '...' if (pred is Ellipsis or pred is None) else pred


def parse_relation_rule(
        rule: str,
) -> tuple[list[tuple[str | None, str | None, str | None]], list[tuple[str, str]]]:
    """
    Parse one bracketed type-restriction list into direct assignments:
    (type, predicate, name) tuples, where name is '*' for a wildcard declaration
    (`T:*` / `T:*#P`), else None. The second tuple element is always empty -- it
    held 'X from Y' pairs when this function also parsed rewrite references; the
    recursive-descent _RelationParser owns those now and only hands bracket
    tokens here (the fallback branches were dead in the production pipeline).

    Examples:
        "[user]" -> ([(user, None, None)], [])
        "[user, domain#member]" -> ([(user, None, None), (domain, member, None)], [])
        "[user:*]" -> ([(user, None, '*')], [])
        "[group:*#member]" -> ([(group, member, '*')], [])
    """
    # Provenance (moved out of the docstring, TK123 item 14): spec §2.1.
    direct_assignments: list[tuple[str | None, str | None, str | None]] = []

    # Bracket lists only (blind-audit S-4: '[user from x]' used to hit a
    # ' from ' fallback branch and silently parse to an empty, un-writable Direct).
    if not rule.startswith('['):
        raise SchemaError(f'expected a bracketed type-restriction list, got {rule!r}')
    subjects = rule[1:].split(']')[0].split(',')
    if not any(s.strip() for s in subjects):
        raise SchemaError(f'empty type-restriction list in {rule!r}')
    for subject in subjects:
        subject = subject.strip()
        if not subject:
            raise SchemaError(f'empty entry in type-restriction list {rule!r}')
        if subject.count('#') > 1:
            raise SchemaError(f'malformed restriction {subject!r} (multiple #)')
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
        # garbage like '[group#]' / '[user: *]' previously produced dead,
        # never-matching Filters instead of a parse error (blind-audit S-4)
        if not is_valid_identifier(subject_type):
            raise SchemaError(f'invalid subject type in restriction {subject!r}')
        if subject_predicate is not None and not is_valid_identifier(subject_predicate):
            raise SchemaError(f'invalid userset relation in restriction {subject!r}')
        direct_assignments.append((subject_type, subject_predicate, subject_name))
    return direct_assignments, []


def _restriction_pattern(r: Restriction, object_type: str,
                         relation_name: str) -> RelationalTriplePattern:
    """The admission pattern for one `[...]` restriction (spec §2.1/§2.3): shared by
    plain Filters, leaf-routing RewriteFilters, and userset storage-leaf routing.

    The wildcard pattern (subject_name='*') matches ONLY wildcard subjects; the
    concrete pattern (subject_name=None) keeps rejecting `T:*`. Object side stays
    permissive so object-wildcard tuples reach the façade.
    """
    return RelationalTriplePattern(
        subject_predicate=(Ellipsis if r.predicate == '...' else r.predicate),
        subject_type=r.type,
        subject_name=('*' if r.wildcard else None),
        relation=relation_name,
        object_type=object_type,
        object_match_wildcards=True,
    )


def _rewrite_rule(expr: 'Computed | TTU', object_type: str, target_relation: str) -> Rule:
    """The Computed/TTU rewrite Rule (permissive so wildcard subjects propagate,
    §2.2). ``target_relation`` is the public relation in ``_emit_expr`` and the
    synthetic leaf predicate in ``_emit_leaf_expr`` -- the pattern shapes are
    shared by construction, not mirrored by hand."""
    if isinstance(expr, Computed):
        return Rule(
            RelationalTriplePattern(relation=expr.relation, object_type=object_type,
                                    match_wildcards=True),
            RelationalTriplePattern(relation=target_relation, object_type=object_type,
                                    match_wildcards=True),
        )
    # `target from tupleset`: a tuple carrying `tupleset` rewrites to `target`#relation.
    return Rule(
        RelationalTriplePattern(relation=expr.tupleset_rel, object_type=object_type,
                                match_wildcards=True),
        RelationalTriplePattern(subject_predicate=expr.target_rel, relation=target_relation,
                                object_type=object_type, match_wildcards=True),
    )


# Bound LAST, for ``RuleSet.compiled``'s string annotation (`TK164`): with it,
# ``typing.get_type_hints(RuleSet)`` resolves instead of raising ``NameError``. It cannot sit at
# the top, because ``boolean`` imports from this module; the package ``__init__`` always imports
# this module before ``boolean``, so by the time this line runs ``boolean`` can finish importing.
from .boolean import CompiledBooleans  # noqa: E402,F401  (circular by design; see above)
