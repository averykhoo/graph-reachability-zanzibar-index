"""Boolean derived-predicate compilation: plan nodes, compiled artifacts, taint, strata.

Part of `zanzibar.schema`; split out of the single-file module by TK120 (2026-10-06).
"""
from dataclasses import dataclass, replace
from functools import reduce
from typing import Callable
from .errors import CyclicDerivedDependency, UnsupportedByGraphIndex
from .syntax import Computed, Direct, Exclusion, Expr, Intersection, Restriction, SchemaAST, TTU, Union
from .rules import Filter, RewriteFilter, Rule, SchemaInfo, _restriction_pattern, _rewrite_rule


def _assert_ttu_parent_types_cover_admission(compiled, rules_and_filters: list) -> None:
    """★ COMPILE-TIME INVARIANT, landed 2026-08-11 with the RC2 fix.

    Property guarded: for every TTU plan node, the frozen ``parent_types`` covers every
    bare-entity subject type that ADMISSION accepts onto that tupleset relation. A type
    admission accepts but ``parent_types`` omits is a stored tupleset tuple the TTU will
    silently refuse to walk -- which is a false NEGATIVE under a positive TTU and an
    authorization FAIL-OPEN under a negated one. That is exactly RC1, and this invariant
    is red on it.

    ★★ IT READS THE EMITTED FILTERS, NOT ``_member_types``, AND THAT IS THE WHOLE POINT.
    ``_member_types`` is the function RC1 got wrong. An invariant deriving its
    expectation from that same function would be a MIRROR
    (``docs/sabotage-procedure.md``, "the mirror instrument"): a defect there would move
    the check and its subject together and it would agree with itself. That is precisely
    how invariant **I9** stayed green through two live authorization fail-opens with
    paranoia ON -- it re-runs ``reconcile``, which reads the same wrong ``parent_types``.
    Filters are built from the ``Restriction``s directly (``_restriction_pattern``), so
    the two derivations are genuinely independent.

    Direction is deliberate: ``admitted ⊆ parent_types``, not equality. ``_member_types``
    legitimately over-approximates -- it recurses through ``Computed``/``TTU`` arms that
    admit no raw tuple of their own -- and an over-broad ``parent_types`` costs a wasted
    lookup, never a wrong answer.

    HONEST LIMIT: it can only see types that some Filter accepts. A tupleset relation fed
    ONLY by rewrite Rules (a ``Computed`` arm) contributes nothing here, so the invariant
    is vacuous on that shape rather than wrong about it. Untainted computed tuplesets are
    separately refused by ``_validate_ttu_tuplesets``.
    """
    # What admission ACCEPTS, per (object_type, public relation), from the emitted
    # filters alone. Only bare-entity subjects can be TTU parents -- a userset node is
    # not a parent -- and only STORAGE leaves hold raw stored tuples (rule-routed leaves
    # carry computed state, which stored-tuple TTU semantics never count).
    admitted: dict[tuple[str, str], set[str]] = {}
    for rf in rules_and_filters:
        if not isinstance(rf, Filter):
            continue                                  # a Rule admits nothing
        pat = rf.if_pattern
        if pat.subject_predicate is not Ellipsis:
            continue                                  # userset restriction
        if isinstance(rf, RewriteFilter):
            fam = compiled.namespace.get((pat.object_type, rf.rewrite_relation))
            if not isinstance(fam, LeafFamily) or not fam.storage:
                continue
            key = (pat.object_type, fam.owner_relation)
        else:
            key = (pat.object_type, pat.relation)
        if pat.subject_type is not None:
            admitted.setdefault(key, set()).add(pat.subject_type)

    for plan in compiled.plans.values():
        o_type = plan.key[0]
        for node in plan.leaf_nodes:
            if not isinstance(node, PDerivedTTU):
                continue
            accepts = admitted.get((o_type, node.tupleset_rel), set())
            missing = sorted(accepts - set(node.parent_types))
            if missing:
                raise ValueError(
                    f'TTU {node.target_rel!r} from {node.tupleset_rel!r} in '
                    f'{o_type}#{plan.key[1]}: compiled parent_types '
                    f'{tuple(node.parent_types)!r} omits type(s) {missing!r} that '
                    f'ADMISSION accepts onto {o_type}#{node.tupleset_rel}. A stored '
                    f'tupleset tuple of that type would be silently dropped as a TTU '
                    f'parent (fail-open under a negated TTU). This is the RC1 class -- '
                    f'suspect _member_types, not this check.')


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
    kind: str               # 'closure' | 'derived-computed' | 'derived-userset' | 'derived-ttu'
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
    via: str                            # 'computed' | 'userset' | 'ttu'
    tupleset_rel: str | None = None
    leaf: str | None = None             # storage leaf, for via='userset'


@dataclass
class Plan:
    """One derived relation's executable plan. ``check_fn(ctx, subject) -> bool`` and
    ``stars_fn(ctx) -> frozenset[shape]`` are closure-composed (no AST walk, no
    per-node dispatch, short-circuit); ``ctx`` is the processor's evaluation context
    bound to one (store, object). ``leaf_nodes`` is index-aligned with ``leaves`` --
    the authoritative spec→tree-node pairing (never reconstruct it by name)."""
    key: tuple[str, str]                # (object_type, relation)
    tree: object
    leaves: tuple[LeafSpec, ...]
    leaf_nodes: tuple                   # plan-tree node per leaf, index-aligned
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
    contribute nothing (a userset node is not a TTU parent).

    **Exclusion contributes BOTH arms, deliberately** (fixed 2026-08-10; every caller
    passes a ``tupleset_rel``, so this function only ever answers "what types can a TTU
    parent have"). The subtrahend's restrictions are still *storable* subject types on
    the public relation -- ``(doc:d2, parent, doc:d1)`` is admitted against
    ``define parent: [folder] but not [doc]`` -- and ``CLAUDE.md`` pins stored-tuple TTU
    semantics: *"TTU parents are STORED tupleset tuples, never computed membership"*.
    A TTU must therefore walk that tuple whatever the exclusion decides about ``d2``'s
    membership, so which ARM admitted the type is irrelevant here.

    This docstring previously read *"Exclusion members come from its base only"* and the
    code matched it. That was RC1: it silently narrowed ``parent_types``, dropping every
    stored parent whose type reached the tupleset relation only through the subtrahend --
    a false NEGATIVE under a positive TTU and an authorization FAIL-OPEN under a negated
    one. Pinned by ``tests/test_ttu_tupleset_parent_types.py``; do not narrow this again
    without turning those pins red first."""
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
            # BOTH arms -- see the docstring. A subtrahend restriction is still a storable
            # subject type, and stored-tuple TTU semantics do not care which arm admitted
            # it. `walk(e.base)` alone was RC1 (2026-08-10).
            return walk(e.base) | walk(e.subtract)
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
        # a tupleset is never tainted: `_validate_ttu_tuplesets` refuses every
        # non-direct one before plans are built (TK107)
        return all((t, expr.target_rel) not in tainted
                   for t in _member_types(object_type, expr.tupleset_rel, ast, frozenset()))
    if isinstance(expr, Union):
        return all(_is_pure(c, object_type, tainted, ast) for c in expr.children)
    return False    # Intersection / Exclusion


def _emit_leaf_expr(expr: Expr, object_type: str, public_relation: str, leaf: str,
                    out: list) -> None:
    """Compile one closure-leaf subtree. Directs become RewriteFilters (admission
    matches the PUBLIC relation name; routing lands on the leaf); Computed/TTU become
    ordinary Rules targeting the leaf. Shares _emit_expr's pattern builders."""
    if isinstance(expr, Union):
        for c in expr.children:
            _emit_leaf_expr(c, object_type, public_relation, leaf, out)
    elif isinstance(expr, Direct):
        for r in expr.restrictions:
            out.append(RewriteFilter(
                if_pattern=_restriction_pattern(r, object_type, public_relation),
                rewrite_relation=leaf,
            ))
    elif isinstance(expr, (Computed, TTU)):
        out.append(_rewrite_rule(expr, object_type, leaf))
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
            # (userset.predicate is never '...', so the shared pattern is identical)
            out_rules.append(RewriteFilter(
                if_pattern=_restriction_pattern(userset, object_type, relation),
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
                        # REFUSED SHAPE (decision-15 family): a wildcard userset
                        # ``[group:*#member]`` over a derived (boolean) ``group#member``.
                        # WHY: "members of every group" over a boolean relation needs
                        # symbolic composition through residues, which the v1 processor
                        # lacks. INSTEAD: ``[group#member]`` with one tuple per group
                        # (closest legal form: covers only the groups written), or make
                        # ``group#member`` plain.
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
            return PDerivedTTU(e.target_rel, e.tupleset_rel, positive, parent_types)
        raise TypeError(f"unknown Expr node {e!r}")

    return build(expr, True)


def _plan_leaves(tree) -> tuple[tuple[LeafSpec, ...], tuple]:
    """Pre-order leaf specs AND their plan-tree nodes, index-aligned. The pairing is
    load-bearing (blind-audit P2): reconstructing the spec→node association by name
    silently resolved BOTH of two same-target TTU leaves to the first node, dropping
    the second tupleset's parents -- invisibly, because the audit enumeration shared
    the bug."""
    specs: list[LeafSpec] = []
    nodes: list = []

    def leaf(spec: LeafSpec, n) -> None:
        specs.append(spec)
        nodes.append(n)

    def walk(n) -> None:
        if isinstance(n, PClosureLeaf):
            leaf(LeafSpec(n.predicate, 'closure', n.positive, storage=n.storage), n)
        elif isinstance(n, PDerivedComputed):
            leaf(LeafSpec(n.relation, 'derived-computed', n.positive), n)
        elif isinstance(n, PDerivedUserset):
            leaf(LeafSpec(n.predicate, 'derived-userset', n.positive, storage=True), n)
        elif isinstance(n, PDerivedTTU):
            leaf(LeafSpec(n.target_rel, 'derived-ttu', n.positive), n)
        elif isinstance(n, (PUnion, PIntersection)):
            for c in n.children:
                walk(c)
        elif isinstance(n, PExclusion):
            walk(n.base)
            walk(n.subtract)

    walk(tree)
    return tuple(specs), tuple(nodes)


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
        # REFUSED SHAPE (boolean spec §1.9): derived relations in a dependency cycle, e.g.
        # ``define member: [user, group#member] but not banned``. The ASK-1 cycle check
        # misses it: a userset restriction or TTU target makes no reference edge.
        # WHY: a derived relation that depends on itself gets no stratum, so the per-stratum
        # cascade cannot order it. GRAPH-only: the set engine evaluates it as a least
        # fixpoint. From a checked parse the recursion here is POSITIVE (the example's
        # ``group#member`` is in the base): recursion through a ``but not`` subtrahend is
        # refused at parse since TK114 (`_validate_stratified_negation`), so only a
        # hand-built AST reaches this with one. INSTEAD: recurse on a plain relation, apply
        # the boolean on top:
        #     define member_base: [user, group#member_base]
        #     define member: member_base but not banned
        # NOT equivalent: ``banned`` is subtracted once, at the queried group, not at every
        # nesting level. Per-level exclusion has no legal form.
        raise CyclicDerivedDependency(
            f"derived relations form a dependency cycle (boolean spec §1.9 forbids "
            f"recursion through boolean relations): {cyclic}")
    return strata


def compile_boolean_schema(ast: SchemaAST, schema_info: SchemaInfo,
                           rules_and_filters: list,
                           tainted: frozenset) -> tuple[CompiledBooleans, SchemaInfo]:
    """Compile every tainted relation: plans + leaf routing appended to
    ``rules_and_filters``; returns the artifacts and a SchemaInfo enriched with the
    derived/leaf namespace facts. Derived-dependency cycles raise ``ValueError``.
    The decision-15-family scope restrictions live in
    ``_reject_object_wildcard_scope``, which the caller runs after shape expansion
    (they must see the expanded shape set, not just the declared one)."""
    namespace: dict[tuple[str, str], LeafFamily | DerivedFamily] = {}
    plans: dict[tuple[str, str], Plan] = {}
    dependents: dict[tuple[str, str], list[DependentEdge]] = {}
    target_feeders: dict[tuple[str, str], list[DependentEdge]] = {}
    tupleset_feeders: dict[tuple[str, str], list[DependentEdge]] = {}

    for key in sorted(tainted):
        object_type, relation = key
        tree = _build_plan_tree(key, ast[key], tainted, ast, rules_and_filters)
        leaves, leaf_nodes = _plan_leaves(tree)
        deps = _plan_deps_and_fanout(key, tree, tainted, ast, dependents, target_feeders,
                                     tupleset_feeders)
        plans[key] = Plan(key=key, tree=tree, leaves=leaves, leaf_nodes=leaf_nodes,
                          deps=deps, stratum=0,
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
    # and no Rule then-target lands on a derived-public family. Real raises, not
    # asserts (blind-audit: last line of defense for I5, must survive python -O).
    derived = compiled.derived_families
    derived_predicates = {r for (_t, r) in derived}
    for rf in rules_and_filters:
        if isinstance(rf, RewriteFilter):
            o_t = rf.if_pattern.object_type
            if (o_t, rf.rewrite_relation) not in compiled.leaf_families:
                raise ValueError(f'RewriteFilter routes outside a leaf family: {rf}')
        elif isinstance(rf, Filter):
            if (rf.if_pattern.object_type, rf.if_pattern.relation) in derived:
                raise ValueError(f'plain Filter admits a derived-public relation: {rf}')
        elif isinstance(rf, Rule) and rf.then_pattern is not None:
            then_rel = rf.then_pattern.relation
            then_t = rf.then_pattern.object_type or rf.if_pattern.object_type
            if (then_t, then_rel) in derived:
                raise ValueError(f'Rule rewrites into a derived-public family: {rf}')
            sp = rf.then_pattern.subject_predicate
            if isinstance(sp, str) and sp in derived_predicates:
                raise ValueError(
                    f'Rule then-pattern carries a derived subject predicate: {rf}')

    _assert_ttu_parent_types_cover_admission(compiled, rules_and_filters)

    if not derived and not compiled.leaf_families:
        return compiled, schema_info      # pure schema: nothing to enrich
    enriched = replace(schema_info,
                       derived_families=derived,
                       leaf_families=compiled.leaf_families)
    return compiled, enriched
