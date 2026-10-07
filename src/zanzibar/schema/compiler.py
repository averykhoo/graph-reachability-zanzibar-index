"""`compile_ruleset` (schema -> graph-index rules), wildcard scope refusals, and the DSL front door `parse_openfga_schema`.

Part of `zanzibar.schema`; split out of the single-file module by TK120 (2026-10-06).
"""
from dataclasses import replace
import warnings
from .errors import DoublyBridgedShapeError, UnsupportedByGraphIndex
from .syntax import Computed, Direct, Exclusion, Expr, Intersection, Restriction, SchemaAST, TTU, Union, _directs_only, _iter_directs, _iter_ttus
from .rules import Filter, Rule, RuleSet, SchemaInfo, _restriction_pattern, _rewrite_rule, norm_pred
from .parser import parse_schema_ast
from .boolean import _member_types, compile_boolean_schema, compute_taint


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

    # Star tuplesets (blind-audit): a wildcard restriction [S:*] on a relation used
    # as a TTU tupleset means the TTU rule will rewrite `S:* ts o` into a tuple
    # whose subject shape is (S, target_rel) -- that through-shape must be declared
    # or the graph rejects a schema-legal write the set engine accepts.
    for (object_type, _rel), expr in ast.items():
        for ttu in _iter_ttus(expr):
            ts_expr = ast.get((object_type, ttu.tupleset_rel))
            if ts_expr is None:
                continue
            for direct in _iter_directs(ts_expr):
                for r in direct.restrictions:
                    if r.wildcard and r.predicate == '...':
                        subject_wildcard_shapes.add((r.type, ttu.target_rel))

    _warn_unproven_extensions(ast, object_wildcard_shapes)
    return SchemaInfo(
        subject_wildcard_shapes=frozenset(subject_wildcard_shapes),
        object_wildcard_shapes=frozenset(object_wildcard_shapes),
    )


class UnprovenExtensionWarning(UserWarning):
    """A schema uses a wildcard extension beyond OpenFGA that the formal proofs do not cover.

    The three extensions (wildcard usersets ``[T:*#p]``, star tuplesets, object wildcards)
    are excluded from the headline equivalence theorems' premise
    (``FullScope.lean::W4Fragment`` fields ``wsBare`` / ``bareStar`` / ``ttuStarFree``), so
    backend agreement on them rests on the differential tests alone. Kept by user decision
    2026-09-26 (task ``ASK-2``); this warning is how a caller learns that. Silence it with
    ``warnings.filterwarnings('ignore', category=UnprovenExtensionWarning)``."""


def unproven_extensions(ast: SchemaAST,
                        object_wildcard_shapes=frozenset()) -> list[str]:
    """Human-readable list of the ``UnprovenExtensionWarning`` features this schema admits
    (empty for a schema inside OpenFGA's wildcard surface; a bare ``[T:*]`` is standard)."""
    found: list[str] = []
    ws = sorted(wildcard_userset_restriction_shapes(ast))
    if ws:
        found.append('wildcard usersets ' + ', '.join(f'[{t}:*#{p}]' for t, p in ws))
    star_ts: set[tuple[str, str]] = set()
    for (object_type, _rel), expr in ast.items():
        for ttu in _iter_ttus(expr):
            ts_expr = ast.get((object_type, ttu.tupleset_rel))
            if ts_expr is None:
                continue
            for direct in _iter_directs(ts_expr):
                if any(r.wildcard and r.predicate == '...' for r in direct.restrictions):
                    star_ts.add((object_type, ttu.tupleset_rel))
    if star_ts:
        found.append('star tuplesets ' + ', '.join(f'{t}#{r}' for t, r in sorted(star_ts)))
    if object_wildcard_shapes:
        found.append('object wildcards ' + ', '.join(
            f'{t}:*#{r}' for t, r in sorted(object_wildcard_shapes)))
    return found


def _warn_unproven_extensions(ast: SchemaAST, object_wildcard_shapes) -> None:
    found = unproven_extensions(ast, object_wildcard_shapes)
    if found:
        warnings.warn(
            'UNPROVEN: this schema uses wildcard extensions beyond OpenFGA ('
            + '; '.join(found) + '). They are not covered by the formal equivalence '
            'proofs (formal/, W4Fragment); graph-index / set-engine agreement on them is '
            'established by tests only. See task ASK-2.',
            UnprovenExtensionWarning, stacklevel=3)


def _restriction_filter(r: Restriction, object_type: str, relation_name: str) -> Filter:
    return Filter(_restriction_pattern(r, object_type, relation_name))


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
        # REFUSED SHAPE (opt-in, pre-P7): ``and`` / ``but not`` under
        # ``compile_ruleset(..., enable_boolean=False)``. WHY: that flag restores the
        # historical refusal (`compile_ruleset` docstring): this emitter builds plain
        # Filters/Rules only, and booleans need the derived-predicate compiler.
        # INSTEAD: compile with the default ``enable_boolean=True`` (boolean spec §3).
        # NOTE: the message's own suggestion is stale ("use the set engine": since P7 the
        # graph index compiles booleans itself; only this opt-in mode refuses them).
        raise UnsupportedByGraphIndex(
            f"relation {object_type}#{relation_name} uses boolean operator {op!r}; "
            f"the graph index materialises closures and cannot ingest boolean relations "
            f"(use the set engine)")
    elif isinstance(expr, Direct):
        for r in expr.restrictions:
            out.append(_restriction_filter(r, object_type, relation_name))
    elif isinstance(expr, (Computed, TTU)):
        out.append(_rewrite_rule(expr, object_type, relation_name))
    else:
        raise TypeError(f"unknown Expr node {expr!r}")


def _validate_ttu_tuplesets(ast: SchemaAST, tainted: frozenset) -> None:
    """Zanzibar/OpenFGA tupleset semantics: a TTU's parent set comes from STORED
    tuples of the tupleset relation, never from computed membership. An *untainted*
    tupleset relation with Computed/TTU arms would break that in the graph backend:
    its rewrite rules land derived triples on the tupleset family, and the TTU rule
    would illegally propagate them (the oracle and the set engine, reading raw
    tuples, would not) -- a silent cross-backend divergence. Rejected loudly instead,
    exactly as OpenFGA validates its models.

    Tainted (derived) tuplesets were exempt until TK107 (2026-10-05) and compiled to
    ``PDerivedTuplesetTTU``. Since TK106 both checked parsers refuse every non-direct
    tupleset, so that plan node was reachable only from a hand-built or unchecked AST,
    through code no differential exercised. It was deleted, and this check now refuses
    a tainted tupleset too, so no input reaches plan construction with one."""
    # A TTU inside an UNTAINTED relation compiles to a rewrite Rule whose then-pattern
    # carries `target_rel` as its subject predicate (`_emit_expr` -> `_rewrite_rule`).
    # If that NAME is also a derived relation, the rule would route derived state
    # through a plain rewrite, which `compile_boolean_schema`'s I5 exclusivity check
    # refuses -- with a bare `ValueError`, a class `tests/parity.py` declares "must
    # surface", so `ParityEngine` was UNCONSTRUCTIBLE rather than degrading to 3-way.
    #
    # Reaching it needs the containing relation to stay untainted while a target it
    # can actually reach is tainted, which `compute_taint` prevents: `_mentions` taints
    # the caller via `_member_types(tupleset)`, the same type set this check reads.
    #
    # TK126 (2026-10-08): keyed on (type, relation). Until then the test was the target
    # NAME against every derived relation on ANY type, which refused the ordinary
    # OpenFGA idiom (`viewer from parent` with `parent: [folder]`, plain `folder#viewer`,
    # while some OTHER type's `viewer` is boolean) although the set engine served it.
    # The rule's produced subject type is the stored tupleset tuple's type, which
    # admission pins to the tupleset's restriction types, so only those types matter
    # (`docs/tk126-ttu-target-boolean-name-2026-10-07.md` sec 2.2). From a checked
    # parse this raise is now unreachable; it stays as the scoped pre-emption of the
    # `compile_boolean_schema` `ValueError` for a hand-built / unchecked AST or a taint
    # regression. An UNDECLARED tupleset (refused at parse since ASK-1) has no types at
    # all, so it keeps the old conservative NAME test, mirroring that guard's fallback.
    for (object_type, relation), expr in ast.items():
        if (object_type, relation) in tainted:
            continue                      # boolean path: no rewrite Rule is emitted
        for e in _iter_ttus(expr):
            ts_key = (object_type, e.tupleset_rel)
            types = (_member_types(object_type, e.tupleset_rel, ast, frozenset())
                     if ts_key in ast else frozenset())
            if types:
                hit = sorted(t for t in types if (t, e.target_rel) in tainted)
            else:
                hit = sorted(t for (t, r) in tainted if r == e.target_rel)
            # REFUSED SHAPE (decision-15 family): a TTU in an untainted relation that can
            # reach a boolean-tainted (type, target) -- possible only from a hand-built or
            # unchecked AST (e.g. an undeclared tupleset) or a taint-analysis bug.
            # WHY: the comment above -- the TTU would compile to a plain rewrite rule that
            # produces derived-public subject nodes (I5 exclusivity), so the graph index
            # would diverge from the set engine and the oracle.
            # INSTEAD: parse the schema text with the checked parser and declare the
            # tupleset as a direct relation, ``define parent: [folder]`` then
            # ``define reader: viewer from parent``; the checked compile taints such a
            # relation and serves it. A same-NAMED boolean relation on another type is
            # NOT refused (TK126), so no rename is needed.
            if hit:
                undeclared = ts_key not in ast
                raise UnsupportedByGraphIndex(
                    f"relation {object_type}#{relation}: TTU {e.target_rel!r} from "
                    f"{e.tupleset_rel!r} can reach the boolean-tainted relation(s) "
                    f"{', '.join(f'{t}#{e.target_rel}' for t in hit)}, but the "
                    f"containing relation is not itself tainted, so it would compile "
                    f"to a plain rewrite rule carrying derived state on its subject "
                    f"predicate (I5 exclusivity). "
                    + (f"The tupleset {object_type}#{e.tupleset_rel} is undeclared; "
                       f"declare it, e.g. 'define {e.tupleset_rel}: [<type>]'. "
                       if undeclared else
                       "A checked parse taints such a relation, so this AST is "
                       "hand-built/unchecked or the taint analysis regressed. ")
                    + "(decision-15 family)")
    for (object_type, relation), expr in ast.items():
        for e in _iter_ttus(expr):
            ts_key = (object_type, e.tupleset_rel)
            # REFUSED SHAPE: a tupleset with computed / TTU / boolean arms, tainted or
            # not. WHY: the docstring above. Since TK106 every non-direct tupleset is
            # refused at parse time (`_validate_tuplesets_direct`), so only a hand-built
            # or unchecked AST reaches this; since TK107 it is the guard that keeps a
            # tainted tupleset out of plan construction.
            # INSTEAD: store the links on a direct relation,
            # ``define parent_link: [folder]``, and use ``viewer from parent_link``.
            if ts_key in ast and not _directs_only(ast[ts_key]):
                raise UnsupportedByGraphIndex(
                    f"relation {object_type}#{relation}: tupleset "
                    f"{e.tupleset_rel!r} has computed/rewritten arms (or boolean "
                    f"ones); Zanzibar tupleset semantics read stored tuples only, so "
                    f"declare it direct-only (e.g. 'define parent_link: [folder]') "
                    f"and use 'from parent_link'")
            if ts_key in ast:
                # USERSET restrictions in tuplesets are rejected (OpenFGA model
                # rule): they bypassed taint analysis entirely (a relation
                # reading derived state compiled as pure union with no
                # invalidation wiring) and had drop-the-predicate parent
                # semantics no spec defines (blind-audit D3). Since TK108
                # (2026-09-27) both parsers refuse this at PARSE time
                # (`_validate_tuplesets_direct`, which carries the why and the
                # rewrite), so a checked parse never reaches here: this is the
                # last line of defence for a hand-built AST. Wildcard
                # restrictions stay ALLOWED -- star tuplesets are this repo's
                # deliberate object-wildcard extension (w_all machinery);
                # derive_schema_info derives their through-shapes.
                for d in _iter_directs(ast[ts_key]):
                    for r in d.restrictions:
                        if r.predicate != '...':
                            raise UnsupportedByGraphIndex(
                                f"relation {object_type}#{relation}: tupleset "
                                f"{e.tupleset_rel!r} declares a userset "
                                f"restriction; tupleset relations must be "
                                f"directly assignable types (OpenFGA model rule)")


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
        _validate_ttu_tuplesets(ast, frozenset())
        rules_and_filters: list[Rule | Filter] = []
        for (object_type, relation_name), expr in ast.items():
            _emit_expr(expr, object_type, relation_name, rules_and_filters)
        schema_info = _expand_object_wildcard_shapes(rules_and_filters, schema_info)
        _reject_doubly_bridged_shapes(ast, schema_info)
        schema_info = _node_removal_fence(rules_and_filters, schema_info)
        return RuleSet(rules_and_filters, schema_info=schema_info)

    tainted = compute_taint(ast)
    _validate_ttu_tuplesets(ast, tainted)
    declared_shapes = schema_info.object_wildcard_shapes
    # Scope guards run twice: on the declared shapes up front (early, precise
    # rejection before plan construction can trip a coarser exclusivity error),
    # and on the EXPANDED set after the rules close over the shapes -- a shape one
    # rewrite hop upstream of a rejected position is the same shape post-expansion,
    # and guarding declared shapes only re-admitted exactly the rejected class
    # through Computed/TTU indirection.
    _reject_object_wildcard_scope(ast, tainted, declared_shapes, declared_shapes)
    rules_and_filters = []
    for (object_type, relation_name), expr in ast.items():
        if (object_type, relation_name) not in tainted:
            _emit_expr(expr, object_type, relation_name, rules_and_filters)
    compiled, schema_info = compile_boolean_schema(ast, schema_info, rules_and_filters,
                                                   tainted)
    schema_info = _expand_object_wildcard_shapes(rules_and_filters, schema_info)
    _reject_object_wildcard_scope(ast, tainted, schema_info.object_wildcard_shapes,
                                  declared_shapes)
    _reject_doubly_bridged_shapes(ast, schema_info)
    schema_info = _node_removal_fence(rules_and_filters, schema_info)
    return RuleSet(rules_and_filters, schema_info=schema_info, compiled=compiled)


def _node_removal_fence(rules_and_filters: list, schema_info: SchemaInfo) -> SchemaInfo:
    """Fill ``SchemaInfo.unremovable_node_shapes`` (``TK113``, 2026-10-03b).

    ``RuleSet.apply`` stores a write-time COPY of a tuple for every Computed/TTU rewrite
    (``_rewrite_rule``) and every boolean routing leaf (``RewriteFilter``). The copy sits
    on a different node from the original, so ``WildcardIndex.remove_node`` -- which
    deletes one node's edges and runs no rewrite -- can only be exact on a node no copy
    pair straddles. Unsafe shapes (all PROBED to diverge from the oracle, or to refuse a
    later legitimate remove, in ``docs/tk113-remove-node-fence-2026-10-03.md``):

      * a rewrite SOURCE ``(T, rel)`` -- its copies survive on the target node;
      * a rewrite TARGET ``(T, rel')`` -- its copies go, the originals stay;
      * a TTU's tupleset SUBJECT ``(P, pred)`` for every subject the tupleset admits --
        the stored ``P:p parent T:t`` goes, the copy ``P:p#target -> T:t#rel`` stays;
      * a TTU-PRODUCED subject ``(P, target)`` -- the copies go, the parent tuple stays;
      * every derived-public and leaf family. This also covers every ``RewriteFilter``,
        which only ever routes a derived-public relation onto one of its leaves.

    Any pattern field this derivation needs that is ``None`` ("match any") fails LOUD:
    a fence that silently skipped a shape would be a fence with a hole."""
    unsafe: set[tuple[str, str]] = set()

    def need(value, what):
        if value is None:
            raise ValueError(f'_node_removal_fence: {what} is a match-any pattern; the '
                             f'TK113 fence cannot name the shape it would have to refuse')
        return value

    admitted: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for rf in rules_and_filters:
        if isinstance(rf, Filter):          # RewriteFilter included
            p = rf.if_pattern
            key = (need(p.object_type, 'filter object_type'), need(p.relation, 'filter relation'))
            admitted.setdefault(key, set()).add(
                (need(p.subject_type, 'filter subject_type'), norm_pred(p.subject_predicate)))
    for rf in rules_and_filters:
        if isinstance(rf, Rule):
            i, th = rf.if_pattern, rf.then_pattern
            src = (need(i.object_type, 'rule object_type'), need(i.relation, 'rule relation'))
            unsafe.add(src)
            unsafe.add((need(th.object_type, 'rule target object_type'),
                        need(th.relation, 'rule target relation')))
            if th.subject_predicate is not None:        # TTU: the subject is re-addressed
                for (s_type, s_pred) in admitted.get(src, ()):
                    unsafe.add((s_type, s_pred))
                    unsafe.add((s_type, norm_pred(th.subject_predicate)))
    unsafe |= schema_info.derived_families | schema_info.leaf_families
    return replace(schema_info, unremovable_node_shapes=frozenset(unsafe))


def _expand_object_wildcard_shapes(rules_and_filters: list,
                                   schema_info: SchemaInfo) -> SchemaInfo:
    """Close declared object-wildcard shapes over the rewrite rules (blind-audit):
    a star-object tuple on a declared shape is REWRITTEN by Rules onto other
    relations (and boolean storage/routed leaves), and the façade validates the
    rewritten tuple's shape -- undeclared, the write was rejected on one backend
    and accepted on the other. Fixpoint over then-relations."""
    shapes = set(schema_info.object_wildcard_shapes)
    changed = True
    while changed:
        changed = False
        for rf in rules_and_filters:
            if not isinstance(rf, Rule) or rf.then_pattern is None:
                continue
            src = (rf.if_pattern.object_type, rf.if_pattern.relation)
            if src in shapes or (rf.if_pattern.object_type is None and
                                 any(s[1] == rf.if_pattern.relation for s in shapes)):
                dst_type = rf.then_pattern.object_type or rf.if_pattern.object_type
                dst = (dst_type, rf.then_pattern.relation)
                if dst_type is not None and rf.then_pattern.relation is not None \
                        and dst not in shapes:
                    shapes.add(dst)
                    changed = True
    if shapes == set(schema_info.object_wildcard_shapes):
        return schema_info
    return replace(schema_info, object_wildcard_shapes=frozenset(shapes))


def wildcard_userset_restriction_shapes(ast: SchemaAST) -> frozenset[tuple[str, str]]:
    """Shapes ``(T, p)`` that carry a LITERAL wildcard-userset restriction ``T:*#p``
    (``p != '...'``) somewhere in the schema.

    A strict subset of ``bridged_in_shapes``: it EXCLUDES the star-tupleset
    through-shapes ``derive_schema_info`` also folds into ``subject_wildcard_shapes``
    (a ``[S:*]`` bare tupleset used by a TTU derives the through-shape ``(S, target)``).
    That distinction is the whole difference between F1/F2 and reg11: only a literal
    ``T:*#p`` restriction lets a ``T:*#p ... o`` tuple be written DIRECTLY by the user,
    which makes the danger a property of the SCHEMA and so compile-rejectable. Counting
    through-shapes here would over-reject the legal reg11 / ``owc_star_ttu`` class,
    whose coarse ``bridged_in ∩ bridged_out`` is non-empty.

    ⚠ CORRECTION (2026-08-09). This sentence used to end "-- yet their whole write
    space is oracle-correct and unanimous on both backends", offered as the evidence
    that the class is safe to admit. **That clause was REFUTED by measurement.** The
    graph index under-reported on exactly this class -- an object-wildcard grant
    crossing a star-tupleset TTU with no interned node of the shape -- disagreeing with
    the oracle AND with both set engines (docs/spec-deviations.md 2026-08-09; fixed by
    the entity-wise crossing middle, invariant I14). The NARROWING itself still stands
    on its own argument: the F1/F2 danger is a writable userset SUBJECT creating a
    latent cycle and innocent-write lockout, which a through-shape does not enable.
    Admitting the class was right; the unanimity cited for it was not true.

    ⚠ CORRECTION (ZT-P5-NEW, 2026-07-26). The original justification for this narrowing
    also claimed that a through-shape *"is never a writable userset subject -- reg11's
    dangerous writes self-cycle and are rejected on both backends, so nothing
    persists"*. **That second clause is FALSE.** A through-shape ``(T, target)`` CAN be
    minted in subject position -- not by a direct write, but by the TTU REWRITE: on a
    SELF-REFERENTIAL TTU (``viewer: … or viewer from parent``) over a star-restricted
    tupleset whose shape carries an object wildcard, the raw write ``T:* parent T:*``
    routes to ``T:*#viewer viewer T:*`` = ``w_any(T,viewer) -> w_all(T,viewer)``, which
    the position-split encoding hides from the graph's cycle check. That is a genuine
    latent cycle and it DID detonate. It is NOT fixed by widening this function --
    the schema it needs is precisely the legal reg11 class, so widening here would
    over-reject it. It is fixed at WRITE time instead, in
    ``zanzibar.graphindex.wildcard.WildcardIndex._reject_star_self_edge`` (the graph-side mirror of
    ``SetEngine._would_cycle``'s raw-level ``u == v`` rule). Do not re-derive "therefore
    through-shapes are harmless" from this docstring: they are harmless *to the compile
    gate*, nothing more. See docs/spec-deviations.md 2026-07-17 + 2026-07-26.

    This is the precise left factor of the doubly-bridged precondition (see
    ``_reject_doubly_bridged_shapes``)."""
    shapes: set[tuple[str, str]] = set()
    for expr in ast.values():
        for direct in _iter_directs(expr):
            for r in direct.restrictions:
                if r.wildcard and r.predicate != '...':
                    shapes.add((r.type, r.predicate))
    return frozenset(shapes)


def _reject_doubly_bridged_shapes(ast: SchemaAST, schema_info: SchemaInfo) -> None:
    """Decision-15-family scope rejection (the THIRD entry, 2026-07-17): a shape that is
    simultaneously a LITERAL wildcard-userset shape (a writable ``T:*#p`` restriction,
    ``wildcard_userset_restriction_shapes``) and an object-wildcard shape
    (``bridged_out_shapes``) -- the "doubly-bridged" precondition of F1/F2.

    Run AFTER ``_expand_object_wildcard_shapes`` so it sees the CLOSED object-wildcard
    set (a shape can become doubly-bridged only via compiler propagation through TTU
    heads -- the F1 case propagates ``(folder, admin)`` and the P3 case propagates the
    intersecting ``(folder, viewer)`` the user never declared).

    NOTE on the left factor: we intersect against the LITERAL ``T:*#p`` restriction
    shapes, NOT the full ``bridged_in_shapes``. ``bridged_in_shapes`` also carries
    star-tupleset through-shapes (reg11's ``(folder, viewer)`` from ``[folder:*]`` on a
    TTU tupleset). Using the full ``bridged_in_shapes`` here over-rejects the legal
    reg11 / ``owc_star_ttu`` class, whose coarse ``bridged_in ∩ bridged_out`` IS
    non-empty while every one of their writes is oracle-correct and unanimous across
    backends -- so the coarse criterion would delete working, pinned functionality.

    ⚠ CORRECTION (ZT-P5-NEW, 2026-07-26). This NOTE used to add "…which are NOT writable
    usersets and cannot mint a persistent w_any -- dangerous writes self-cycle". **The
    second half is false.** A self-referential TTU over a star-restricted tupleset with
    an object wildcard on the tupleset shape lets the TTU REWRITE mint exactly such a
    persistent ``w_any(T,p) -> w_all(T,p)`` edge, and it detonated. The correct reading
    is narrower: a through-shape cannot make the danger a property of the SCHEMA (the
    same schema also has an entirely legal write space), so it does not belong in a
    COMPILE-time criterion. The residual write-level case is rejected at write time by
    ``zanzibar.graphindex.wildcard.WildcardIndex._reject_star_self_edge``. See
    docs/spec-deviations.md 2026-07-26.

    Such a shape admits wildcard writes whose materialized bridges form a latent cycle
    ``w_any(T,p) -> w_all(T,p)`` in the graph closure (closed by any present-or-future
    concrete node's concrete->w_any in-bridge and w_all->concrete out-bridge): the graph
    accepts the wildcard write, then permanently REJECTS every later innocent concrete
    write of that shape -- the F1/F2 accept/reject + completeness divergences plus the
    innocent-write lockout ("detonation"). Neither wildcard usersets nor object-wildcard
    tuple objects exist in OpenFGA, so this corner is doubly out of spec; lift via the
    symmetric subject-keyed residue design if ever needed. See docs/spec-deviations.md
    2026-07-17."""
    doubly = (wildcard_userset_restriction_shapes(ast)
              & frozenset(schema_info.bridged_out_shapes))
    if doubly:
        offending = ', '.join(f'({t}, {p})' for (t, p) in sorted(doubly))
        # REFUSED SHAPE (decision-15 family, F1/F2): a shape that is both a ``T:*#p``
        # wildcard-userset shape and an object-wildcard shape. WHY: the docstring above (a
        # latent w_any -> w_all cycle, then innocent concrete writes are locked out); the
        # set engine re-raises it (`SetEngine.__init__`), so neither backend runs it.
        # INSTEAD: drop one factor. Either ``[group#member]`` for ``[group:*#member]``
        # (closest legal form: covers only the groups written, not every group), or remove
        # the shape from ``object_wildcard_shapes`` -- it may arrive by propagation through
        # a TTU head, so the declared shape to drop can be upstream. Neither is in OpenFGA.
        raise DoublyBridgedShapeError(
            f"shape(s) {offending} are BOTH a wildcard-userset shape (a T:*#p "
            f"restriction) and an object-wildcard shape; a wildcard write on such a "
            f"shape materializes bridges that form a latent cycle in the graph closure "
            f"(w_any -> w_all closed by any present-or-future concrete node's in/out "
            f"bridges), so the graph accepts the wildcard write then permanently rejects "
            f"every later innocent concrete write of that shape -- set/graph divergences "
            f"plus innocent-write lockout. Neither wildcard usersets nor object-wildcard "
            f"tuple objects exist in OpenFGA; lift via the symmetric subject-keyed "
            f"residue design if ever needed (decision-15 scope family; see "
            f"docs/spec-deviations.md 2026-07-17)")


def _reject_object_wildcard_scope(ast: SchemaAST, tainted: frozenset,
                                  shapes: frozenset,
                                  declared: frozenset) -> None:
    """Decision-15-family scope rejections, run AFTER ``_expand_object_wildcard_shapes``
    so they cover the closed shape set, not just the declared one (guarding declared
    shapes only silently re-admitted the rejected class one Computed/TTU hop upstream:
    the expansion routed the same wildcard-object state into the guarded position).

    Rejected: shapes on derived relations, shapes expanding onto compiled leaf
    predicates (wildcard-object state inside a derived plan -- the delta processor
    cannot map w_all deltas to derived keys), shapes on the TTU *target* of a tainted
    plan (blind-audit D4: derived evaluation probes the closure directly and never
    consults w_all), shapes on the TTU *tupleset* of a tainted plan (tupleset-parent
    enumeration reads direct stored tuples on the tupleset node, so a wildcard-object
    tupleset tuple would be silently invisible -- wrong denials with no invariant
    tripping), and star-tupleset through-shapes landing on a derived TTU target (the
    derived subject-wildcard shape is a wildcard userset over a derived relation,
    which needs symbolic composition through residues -- same v1 scope hook as the
    declared form)."""
    for (t, r) in sorted(shapes):
        if (t, r) in tainted:
            # REFUSED SHAPE (decision-15 family): an object-wildcard shape on a derived
            # (boolean-tainted) relation. WHY: symbolic every-object (w_all) state on a
            # derived relation needs a subject-keyed residue the v1 processor lacks. Every
            # refusal in this function is GRAPH-only: the set engine still runs the schema,
            # with no graph partner to cross-check it.
            # INSTEAD: none in the graph index -- drop ``(T, r)`` from
            # ``object_wildcard_shapes`` and write concrete objects (covers only the objects
            # written, not every object).
            raise UnsupportedByGraphIndex(
                f"object-wildcard shape ({t}, {r}) targets a derived (boolean-tainted) "
                f"relation; symbolic object state on derived relations needs a "
                f"subject-keyed residue (v1 scope hook)")
        if '.' in r:
            if (t, r) in declared:
                # REFUSED SHAPE: a declared object-wildcard shape naming a compiled leaf
                # predicate (``(doc, viewer.0)``). WHY: ``.``-names are compiler-internal
                # (boolean spec §3.2) and never a user's to declare. INSTEAD: declare the
                # public relation (``(doc, viewer)``), subject to the refusal above.
                raise UnsupportedByGraphIndex(
                    f"object-wildcard shape ({t}, {r}) names a compiled leaf predicate")
            # REFUSED SHAPE (decision-15 family): an object-wildcard shape that the rewrite
            # rules carry onto a leaf of a derived relation. WHY: the docstring -- the delta
            # processor cannot map w_all deltas onto derived keys. INSTEAD: none -- no
            # object wildcard may flow into a boolean relation; drop the shape, or drop the
            # arm of the boolean relation that reads the wildcarded relation (that changes
            # its answers).
            raise UnsupportedByGraphIndex(
                f"object-wildcard shape ({t}, {r.rsplit('.', 1)[0]}) expands onto the "
                f"compiled leaf predicate ({t}, {r}) through the rewrite rules; "
                f"wildcard-object state cannot feed a derived relation (decision-15 "
                f"family)")

    for key in sorted(tainted):
        for ttu in _iter_ttus(ast[key]):
            ts_key = (key[0], ttu.tupleset_rel)
            if ts_key in shapes:
                # REFUSED SHAPE (decision-15 family): an object-wildcard shape on the
                # tupleset of a TTU inside a derived relation. WHY: derived parent
                # enumeration reads stored tupleset tuples directly, so a ``doc:*`` parent
                # tuple would be invisible -- wrong denials with no invariant tripping.
                # INSTEAD: drop the shape and write one concrete parent tuple per object
                # (``doc:d parent folder:f``), covering only those written.
                raise UnsupportedByGraphIndex(
                    f"object-wildcard shape {ts_key} is the tupleset of TTU "
                    f"'{ttu.target_rel} from {ttu.tupleset_rel}' in derived relation "
                    f"{key[0]}#{key[1]}; derived-TTU parent enumeration reads stored "
                    f"tupleset tuples directly and cannot see object-wildcard (w_all) "
                    f"state (decision-15 family)")
            ts_expr = ast.get(ts_key)
            if ts_expr is None:
                continue
            for direct in _iter_directs(ts_expr):
                for restr in direct.restrictions:
                    if (restr.type, ttu.target_rel) in shapes:
                        # REFUSED SHAPE (blind-audit D4): an object-wildcard shape on the
                        # TTU TARGET of a derived relation. WHY: derived evaluation probes
                        # the closure directly and never consults w_all state. INSTEAD: drop
                        # the shape and write concrete target tuples
                        # (``folder:f viewer user:u``), covering only the objects written.
                        raise UnsupportedByGraphIndex(
                            f"object-wildcard shape ({restr.type}, {ttu.target_rel}) "
                            f"is the TTU target of derived relation {key[0]}#{key[1]}; "
                            f"derived evaluation probes the closure directly and "
                            f"cannot see object-wildcard (w_all) state (decision-15 "
                            f"family, blind-audit D4)")
                    if (restr.wildcard and restr.predicate == '...'
                            and (restr.type, ttu.target_rel) in tainted):
                        # REFUSED SHAPE: a star tupleset ``[folder:*]`` whose TTU target is
                        # derived. WHY: it derives a wildcard userset over a derived
                        # relation, which needs symbolic composition through residues that
                        # the v1 processor lacks (the same scope hook as
                        # `_build_plan_tree`). INSTEAD: ``define parent: [folder]`` and one
                        # parent tuple per folder (closest legal form: covers only the
                        # folders written).
                        raise UnsupportedByGraphIndex(
                            f"relation {key[0]}#{key[1]}: star tupleset "
                            f"[{restr.type}:*] on {ttu.tupleset_rel!r} derives the "
                            f"wildcard userset shape ({restr.type}, {ttu.target_rel}) "
                            f"over the derived relation {restr.type}#{ttu.target_rel}, "
                            f"which needs symbolic composition through residues (v1 "
                            f"scope hook; see spec-deviations)")


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
