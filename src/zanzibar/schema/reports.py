"""Opt-in, non-raising scope reports: `w4_fragment_report` (mirror of the Lean decider) and `graph_admission_report`.

Part of `zanzibar.schema`; split out of the single-file module by TK120 (2026-10-06).
"""
from dataclasses import dataclass
from .syntax import Computed, Direct, Exclusion, Expr, Intersection, TTU, Union
from .parser import _parse_schema_ast_unchecked
from .boolean import compute_taint




# ---------------------------------------------------------------------------
# W4Fragment scope report (DW-1 step 3) -- SAYS which inputs the proofs cover
# ---------------------------------------------------------------------------
#
# Every headline theorem (`Zanzibar.graph_correct` and its siblings) is stated under
# `(hA : GraphAdmission S T) (hF : W4Fragment S T)`, so `W4Fragment` IS the scope of the
# graph index's proved guarantee. Seven of its ten fields are SILENT in the backends
# (`formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE`): a schema or store
# outside them is accepted and answered, and its correctness rests on the differential net
# (matrix, oracle, conformance), not on a theorem. This function is the operator-facing
# twin of the Lean decider `FragmentDecide.lean::w4FragmentB` (proved exact by
# `w4FragmentB_iff`). It REPORTS scope and changes no behaviour: nothing calls it on a
# write path, and it never raises on an out-of-fragment input.
#
# It is a hand-written MIRROR, and a mirror drifts (`W4Fragment` has been reshaped three
# times). What stops it from saying "covered" when the proof does not is
# `formal/conformance/test_conformance_fragment.py`, which compares this report field
# for field with Lean's `zcli mode="fragment"`. If that differential goes red, fix THIS
# function to agree with Lean. Do not edit the decider to agree with Python.
#
# Scope of the report: the `W4Fragment` half ONLY, so `in_fragment=True` means "inside
# W4Fragment", not "the theorem applies". The `GraphAdmission` half is decided in Lean
# since TK104 (`AdmissionDecide.lean::graphAdmissionB`); its two fields that Python
# neither refuses nor shadows are reported by `graph_admission_report` below.

#: The ten `W4Fragment` fields, in declaration order (`FullScope.lean::W4Fragment`).
W4_FRAGMENT_FIELDS: tuple[str, ...] = (
    'computedOrDirect', 'directArmsBare', 'directArmsConcrete', 'computedOnlyOperands',
    'noUnionDirects', 'twoStrata', 'wsBare', 'bareStar', 'ttuStarFree', 'term',
)


@dataclass(frozen=True)
class W4FragmentReport:
    """Per-field verdict of `W4Fragment` at one (schema, store). ``fields`` is ordered as
    `W4_FRAGMENT_FIELDS`; ``tainted`` is the derived-relation set the fields quantify over
    (`compute_taint`, pinned equal to Lean's `taintedKeys`)."""
    fields: tuple[tuple[str, bool], ...]
    tainted: frozenset[tuple[str, str]]

    @property
    def failures(self) -> tuple[str, ...]:
        """The fields that do NOT hold, in declaration order."""
        return tuple(name for name, ok in self.fields if not ok)

    @property
    def in_fragment(self) -> bool:
        """True iff all ten fields hold (the `W4Fragment` half of the premise only)."""
        return not self.failures


def _w4_children(e: Expr) -> tuple[Expr, ...]:
    if isinstance(e, (Union, Intersection)):
        return e.children
    if isinstance(e, Exclusion):
        return (e.base, e.subtract)
    return ()


def _w4_computed_or_direct(e: Expr) -> bool:
    # ReconcileCorrect.lean::ComputedOrDirect -- no TTU leaf anywhere.
    if isinstance(e, TTU):
        return False
    return all(_w4_computed_or_direct(c) for c in _w4_children(e))


def _w4_computed_only(e: Expr) -> bool:
    # ReconcileCorrect.lean::ComputedOnly -- only Computed leaves.
    if isinstance(e, (TTU, Direct)):
        return False
    return all(_w4_computed_only(c) for c in _w4_children(e))


def _w4_directs_all(e: Expr) -> list[Direct]:
    # ReconcileCorrect.lean::exprDirectsAll -- Direct leaves through ANY nesting.
    if isinstance(e, Direct):
        return [e]
    return [d for c in _w4_children(e) for d in _w4_directs_all(c)]


def _w4_directs_union(e: Expr) -> list[Direct]:
    # RulesSound.lean::exprDirects -- Direct leaves through UNIONS ONLY. Walking
    # Intersection/Exclusion here (i.e. using `_w4_directs_all`) is the trap the DW-1
    # plan names: it wrongly fails every canonical `[user] but not banned` definition.
    if isinstance(e, Direct):
        return [e]
    if isinstance(e, Union):
        return [d for c in e.children for d in _w4_directs_union(c)]
    return []


def _w4_computed_refs(e: Expr) -> list[str]:
    # ReconcileCorrect.lean::computedRefs
    if isinstance(e, Computed):
        return [e.relation]
    return [r for c in _w4_children(e) for r in _w4_computed_refs(c)]


def _w4_ttu_arms(e: Expr) -> list[TTU]:
    # RulesWrite.lean::exprArms, TTU arms only -- through unions only.
    if isinstance(e, TTU):
        return [e]
    if isinstance(e, Union):
        return [t for c in e.children for t in _w4_ttu_arms(c)]
    return []


def _w4_tuple_fields(tup) -> tuple[str, str, str, str, str, str]:
    """`(subject_predicate, subject_type, subject_name, relation, object_type,
    object_name)` from a `RelationTuple` / `OracleTuple`-shaped object or a plain 6-sequence;
    a ``None`` / ``...`` predicate is the bare ``'...'``."""
    if hasattr(tup, 'subject_name'):
        sp, st, sn = tup.subject_predicate, tup.subject_type, tup.subject_name
        rel, ot, on = tup.relation, tup.object_type, tup.object_name
    else:
        sp, st, sn, rel, ot, on = tup
    if sp is None or sp is Ellipsis:
        sp = '...'
    return sp, st, sn, rel, ot, on


def w4_fragment_report(schema: 'SchemaAST | str', tuples=()) -> W4FragmentReport:
    """Report, field by field, whether ``(schema, tuples)`` lies inside `W4Fragment`.

    ``schema`` is a raw `SchemaAST` (`parse_schema_ast`; `SetEngine.ast` retains one) or
    DSL text. It must be the AST, not a `RuleSet`: compilation folds a TTU inside a
    derived definition into a closure leaf, which loses `computedOrDirect`. ``tuples`` is
    the store. The store fields quantify over every tuple, so an empty store reports the
    schema half only.

    Pure, and it never raises on an out-of-scope input. See the section comment above for
    what the result does and does not mean, and for the Lean differential that pins it."""
    ast = _parse_schema_ast_unchecked(schema) if isinstance(schema, str) else schema
    tuples = [_w4_tuple_fields(t) for t in tuples]
    tainted = compute_taint(ast)
    derived = [(key, expr) for key, expr in ast.items() if key in tainted]

    def derived_operands(key: tuple[str, str], expr: Expr) -> list[Expr]:
        # the definitions of `expr`'s DERIVED computed operands (same object type)
        return [ast[(key[0], r)] for r in _w4_computed_refs(expr)
                if (key[0], r) in tainted and (key[0], r) in ast]

    # TTU rewrite arms of the UNTAINTED definitions (RulesWrite.lean::schemaRewrites):
    # (object_type, tupleset relation, target relation).
    rewrites = [(key[0], t.tupleset_rel, t.target_rel)
                for key, expr in ast.items() if key not in tainted
                for t in _w4_ttu_arms(expr)]
    tupleset_keys = {(ot, ts) for (ot, ts, _tr) in rewrites}
    derived_names = {rel for (_t, rel) in tainted}

    fields = {
        'computedOrDirect': all(_w4_computed_or_direct(e) for _k, e in derived),
        'directArmsBare': all(r.predicate == '...' for _k, e in derived
                              for d in _w4_directs_all(e) for r in d.restrictions),
        'directArmsConcrete': all(not r.wildcard for _k, e in derived
                                  for d in _w4_directs_all(e) for r in d.restrictions),
        'computedOnlyOperands': all(_w4_computed_only(op) for k, e in derived
                                    for op in derived_operands(k, e)),
        'noUnionDirects': all(not _w4_directs_union(e) for _k, e in derived),
        'twoStrata': all((k[0], r) not in tainted for k, e in derived
                         for op in derived_operands(k, e) for r in _w4_computed_refs(op)),
        # ReconcileStars.lean::declaredWildcardShapes -- every wildcard restriction in
        # the WHOLE schema (both taint classes) is bare.
        'wsBare': all(r.predicate == '...' for e in ast.values()
                      for d in _w4_directs_all(e) for r in d.restrictions if r.wildcard),
        # BareStarCorrect.lean::BareStarStore
        'bareStar': all((sn != '*' or sp == '...') and on != '*'
                        for sp, _st, sn, _rel, _ot, on in tuples),
        # RulesBareStar.lean::TtuStarFree
        'ttuStarFree': all(sn != '*' or (ot, rel) not in tupleset_keys
                           for _sp, _st, sn, rel, ot, _on in tuples),
        # NoTtuTarget /\ NoStoreSubjectR, both keyed on the derived relation NAME only.
        'term': (all(tr not in derived_names for (_ot, _ts, tr) in rewrites)
                 and all(sp not in derived_names for sp, *_rest in tuples)),
    }
    return W4FragmentReport(tuple((f, fields[f]) for f in W4_FRAGMENT_FIELDS), tainted)



# ---------------------------------------------------------------------------
# GraphAdmission report (TK104) -- the two premise fields NOTHING ELSE surfaces
# ---------------------------------------------------------------------------
#
# `GraphAdmission` is the other half of the headline premise. The TK104 sizing
# (`formal/conformance/test_graphadmission_scope_pin.py::GRAPHADMISSION_SCOPE`) found ten of
# its fourteen fields LOUD (the compiler or the write path refuses a violating input) and
# two MIXED, whose silent halves always also fail a `W4Fragment` field that
# `w4_fragment_report` names. The remaining two are SILENT: Python accepts a violating
# schema and answers queries on it, and before this report no operator could find out.
#
# * `matchDecl` -- no untainted rewrite rule matches an undeclared or derived relation, i.e.
#   no DANGLING reference (`define viewer: [user] or editor` with no `editor`).
# * `ranked` -- the untainted rewrite graph is acyclic, i.e. no untainted computed CYCLE
#   (`a: [user] or b` with `b: [user] or a`). TTU recursion through a direct-only tupleset
#   (nested folders) emits no cycle and is fine.
#
# Both schemas are valid Zanzibar and both backends answer them; they are outside the
# proved scope, not wrong. So this is a REPORT, like `w4_fragment_report`: pure, opt-in,
# never raises, and nothing calls it on a write path.
#
# The Lean decider is `AdmissionDecide.lean::graphAdmissionB` (proved exact by
# `graphAdmissionB_iff`). This function mirrors only its two SILENT fields, and
# `formal/conformance/test_conformance_fragment.py` (section J) compares it with
# `zcli mode="fragment"` on every curated corpus and every parseable sizing probe. If
# that differential goes red, fix THIS function.

#: The `GraphAdmission` fields this report covers, in declaration order. The other twelve
#: are refused by Python or shadowed by `W4Fragment` (see the section comment).
GRAPH_ADMISSION_REPORTED_FIELDS: tuple[str, ...] = ('matchDecl', 'ranked')


@dataclass(frozen=True)
class GraphAdmissionReport:
    """Per-field verdict on the two SILENT `GraphAdmission` fields, ordered as
    `GRAPH_ADMISSION_REPORTED_FIELDS`."""
    fields: tuple[tuple[str, bool], ...]

    @property
    def failures(self) -> tuple[str, ...]:
        """The reported fields that do NOT hold, in declaration order."""
        return tuple(name for name, ok in self.fields if not ok)

    @property
    def silent_fields_hold(self) -> bool:
        """True iff both SILENT fields hold. This alone is NOT "GraphAdmission holds": the
        other twelve fields are established by Python's refusals, not by this report."""
        return not self.failures


def _ga_rule_arms(e: Expr):
    # RulesWrite.lean::exprArms -- the match relation of each Computed / TTU arm, walking
    # into unions only (boolean nodes emit no rewrite rule).
    if isinstance(e, Computed):
        yield e.relation
    elif isinstance(e, TTU):
        yield e.tupleset_rel
    elif isinstance(e, Union):
        for c in e.children:
            yield from _ga_rule_arms(c)


def graph_admission_report(schema: 'SchemaAST | str') -> GraphAdmissionReport:
    """Report whether ``schema`` satisfies the two SILENT `GraphAdmission` fields.

    ``schema`` is a raw `SchemaAST` or DSL text. Both fields are schema-only. Pure, and it
    never raises on an out-of-scope input. See the section comment above for what the
    result does and does not mean."""
    ast = _parse_schema_ast_unchecked(schema) if isinstance(schema, str) else schema
    tainted = compute_taint(ast)
    # RulesWrite.lean::schemaRewrites -- the rules of the UNTAINTED definitions only, as
    # (match key, out key) on the definition's own object type.
    rules = [((ot, m), (ot, rel)) for (ot, rel), e in ast.items() if (ot, rel) not in tainted
             for m in _ga_rule_arms(e)]
    match_decl = all(mk in ast and mk not in tainted for mk, _ok in rules)
    # RulesSaturate.lean::RewriteRanked. Its rank bound (<= the key count) is implied by
    # acyclicity: the keys of a walk after its first are distinct out keys, and out keys are
    # declared, so a walk is never longer than the key count.
    succ: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for mk, ok in rules:
        succ.setdefault(mk, set()).add(ok)
    done: set[tuple[str, str]] = set()
    ranked = True
    for root in list(succ):
        if root in done or not ranked:
            continue
        on_path = {root}
        stack = [(root, iter(succ.get(root, ())))]
        while stack and ranked:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                stack.pop()
                on_path.discard(node)
                done.add(node)
            elif nxt in on_path:
                ranked = False
            elif nxt not in done:
                on_path.add(nxt)
                stack.append((nxt, iter(succ.get(nxt, ()))))
    fields = {'matchDecl': match_decl, 'ranked': ranked}
    return GraphAdmissionReport(tuple((f, fields[f]) for f in GRAPH_ADMISSION_REPORTED_FIELDS))
