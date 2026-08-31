"""P20 — the Python side of Lean's `NoLeafSubjects`: no compiled rule mints a
leaf-named TTU subject predicate, because the parser REFUSES such a schema.

`GraphIndex/LeafRules.lean` is narrowing `W4Fragment` with a new field::

    def NoLeafSubjects (S : Schema) : Prop :=
      ∀ r ∈ schemaRewritesL S, ∀ tr ∈ ttuTargets r, NotLeafName tr

(`formal/lean/ZanzibarProofs/GraphIndex/LeafRules.lean::NoLeafSubjects`, over
`::ttuTargets` and `formal/lean/ZanzibarProofs/GraphIndex/Leaf.lean::NotLeafName`,
which is `p = BARE ∨ isLeafPred p = false` with
`Leaf.lean::isLeafPred p := p.toList.contains '.'`).

Narrowing a fragment is only sound if the Python it models never leaves the fragment.
It doesn't: `zanzibar_utils_v1.py::_validate_ast_references` raises `ValueError`
("reserved leaf namespace") on any *referenced* relation name containing `'.'` other
than the bare `'...'`, and it applies that to a `TTU` node's ``target_rel``. Until this
module, that argument existed only as PROSE in the Lean file's ★★ note.

★ WHAT THIS IS NOT — `CORRESPONDENCE.md` §7 discipline
------------------------------------------------------
**This module is a PYTHON RE-IMPLEMENTATION of the Lean predicate, not a machine-check
against Lean.** The `zcli` binary this harness drives exposes exactly three modes
(`spec` / `graph` / `graph-state`) and has NO channel for evaluating an arbitrary Lean
`Prop`, so nothing here invokes Lean's `Decidable (NoLeafSubjects S)` instance
(`LeafRules.lean`, the `instance (S : Schema) : Decidable (NoLeafSubjects S)`). What is
compared is a hand-written Python mirror (`_not_leaf_name` / `_ttu_targets` below)
against the compiled `RuleSet`. Making this a true machine-check would require a
**fourth zcli mode** that takes an encoded `Schema` and prints the decision of
`NoLeafSubjects` — then this file would diff Lean's verdict against Python's instead of
recomputing the predicate. Do not describe this module as "machine-checked against
Lean"; per §7 the residual is: *the mirror could be wrong in the same direction as the
model and nothing here would notice.* `test_the_notleafname_mirror_is_not_constantly_true`
is the cheap half of the remedy (a mirror that is constantly `True` is caught); the
expensive half — an `iff` proof, per `docs/sabotage-procedure.md` "Never hand-write a
Bool mirror of a `Prop` without PROVING it" — is on the Lean side, not here.

Three parts, and part 3 is the load-bearing one:

  1. corpus sweep — no rule the harness ever compiles has a leaf-named TTU target;
  2. a LOCAL leaf-layer witness, because part 1 is VACUOUS on the leaf layer
     (measured: 0 of 86 leaf-layer rules corpus-wide is a TTU) — exactly the
     "looks done" vacuity the ★★ note in `LeafRules.lean` warns about;
  3. the refusal control. Parts 1 and 2 can only ever pass: the parser rejects every
     violating schema before a `Rule` is emitted, so they RE-OBSERVE an invariant
     rather than test one. Part 3 pins that the refusal is LIVE.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path
from types import EllipsisType

import pytest

from zanzibar_utils_v1 import Rule, parse_openfga_schema

_REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# The Python mirror of the two Lean symbols. Kept as free functions so the
# instrument itself can be controlled (see the first test).
# ---------------------------------------------------------------------------

BARE = '...'


def _not_leaf_name(p: str) -> bool:
    """Mirror of `Leaf.lean::NotLeafName`: `p = BARE ∨ isLeafPred p = false`,
    where `isLeafPred p := p.toList.contains '.'`."""
    return p == BARE or '.' not in p


def _ttu_targets(rule: Rule) -> list[str]:
    """Mirror of `LeafRules.lean::ttuTargets`: the subject predicate a rule REWRITES
    TO, as a 0-or-1 element list. `.computed` copies the subject through and mints
    nothing (`then_pattern.subject_predicate is None`); `.ttu tr` overwrites the
    predicate with `tr`. `Ellipsis` is the Python spelling of `BARE`."""
    pat = rule.then_pattern
    if pat is None:
        return []
    sp = pat.subject_predicate
    if sp is None:
        return []
    if isinstance(sp, EllipsisType):
        return [BARE]
    return [sp]


# ---------------------------------------------------------------------------
# Sources. Same collector shape as
# `test_conformance_state.py::test_no_corpus_nests_a_pure_union_inside_an_impure_one`
# and `test_grid_independence.py::_all_corpora`, plus the object-wildcard shapes
# (element 2 of each corpus value) which those two do not need.
# ---------------------------------------------------------------------------

def _all_schema_sources() -> list[tuple[str, str, frozenset]]:
    """Every `(label, schema_text, object_wildcard_shapes)` the harness carries."""
    from formal.conformance import corpus as _corpus

    out: list[tuple[str, str, frozenset]] = []
    for dname in ('SCHEMAS', 'MULTI_STRATUM_SCHEMAS', 'TTU_USERSET_SCHEMAS',
                  'SELF_REFERENTIAL_SCHEMAS'):
        d = getattr(_corpus, dname, None)
        if isinstance(d, dict):
            for k, v in d.items():
                ow = v[2] if len(v) > 2 and v[2] else frozenset()
                out.append((f'{dname}:{k}', v[0], frozenset(ow)))
    for f in sorted(glob.glob(str(_REPO_ROOT / 'tests' / 'fga_schemas' / '*.fga'))):
        out.append((f'fga:{os.path.basename(f)}', Path(f).read_text(), frozenset()))
    return out


# ANTI-VACUITY floors. MEASURED 2026-08-31 by `_probe1.py` over the live tree
# (`python _probe1.py` from the repo root, the throwaway that became this module):
#
#     sources: 50
#     schemas_ok 50 rules 166 leaf-layer rules 86 ttu rules 28 leaf-layer ttu 0
#
# ⚠ The P20 brief carried a scout figure of **4** TTU-target rules corpus-wide. That
# number is the four CORPUS-DICT rules only (`SCHEMAS:deep_grid`, `SCHEMAS:ttu`,
# `TTU_USERSET_SCHEMAS:ttu_fromchain`, `::ttu_fromchain_group`); the 24 others live in
# `tests/fga_schemas/*.fga`, which the brief's own collector pattern includes. Floors
# below are the re-measurement, and they deliberately LAG it (new corpora are welcome,
# a collapse is not) — the live figures belong in `FINAL_REVIEW.md`'s generated block,
# not here.
_MIN_SCHEMAS_COMPILED = 45          # live 50
_MIN_TTU_TARGETS = 24               # live 28
_MIN_LEAF_LAYER_RULES = 80          # live 86


def test_the_notleafname_mirror_is_not_constantly_true():
    """Instrument control for parts 1-2 (`docs/sabotage-procedure.md`, "Sabotage your
    instrument too" / "Never hand-write a Bool mirror of a `Prop` without PROVING it").

    `_not_leaf_name` is a hand transcription of a Lean `Prop`. A transcription that
    silently returns `True` for everything makes the corpus sweep and the leaf-layer
    witness both green and both meaningless — the exact 2026-07-28 / 2026-08-16 failure
    the procedure names. So: one input it must REJECT, and the two it must ACCEPT
    (a plain name, and `BARE`, which is the disjunct that is easy to drop).

    SABOTAGE-VERIFIED (b), 2026-08-31. Dropping the `'.' not in p` conjunct from
    `_not_leaf_name` -- i.e. weakening the part-1 predicate to `p == BARE or True`,
    the narrowest plausible weakening -- reddens exactly this test and nothing else::

        E       AssertionError: the NotLeafName mirror ACCEPTED a compiler-minted leaf name -- it is constantly true, and parts 1-2 are vacuous
        E       assert not True
        E        +  where True = _not_leaf_name('viewer.0')
        FAILED formal/conformance/test_leaf_namespace_correspondence.py::test_the_notleafname_mirror_is_not_constantly_true
        1 failed, 4 passed in 0.44s

    Read the `4 passed`: the corpus sweep stayed GREEN under that weakening, and so did
    its three anti-vacuity floors (they still counted 50 schemas / 28 TTU targets / 86
    leaf-layer rules, because a weakened PREDICATE does not change what is INSPECTED).
    That is the finding, not a nuisance: an anti-vacuity floor CANNOT catch a weakened
    predicate, so this control is the sole guard on the mirror's content.
    """
    assert not _not_leaf_name('viewer.0'), (
        'the NotLeafName mirror ACCEPTED a compiler-minted leaf name -- it is '
        'constantly true, and parts 1-2 are vacuous')
    assert not _not_leaf_name('safe.11'), 'multi-digit leaf index accepted'
    assert _not_leaf_name('viewer'), 'the mirror rejects an ordinary relation name'
    assert _not_leaf_name(BARE), (
        "the mirror dropped NotLeafName's `p = BARE` disjunct")


def test_no_corpus_rule_mints_a_leaf_named_ttu_target():
    """PART 1 — the corpus sweep. Over every schema source the harness carries, no
    compiled rule's TTU target is a compiler-minted leaf name. This is the Python
    mirror of `LeafRules.lean::NoLeafSubjects` evaluated at every schema this repo
    actually drives.

    `RuleSet.rules_and_filters` holds BOTH Lean rule layers in one list -- untainted
    rules from `zanzibar_utils_v1.py::_emit_expr` (Lean `schemaRewrites`) and leaf
    rules from `::_emit_leaf_expr` (Lean `leafRewrites`) -- so one pass covers
    `schemaRewritesL = schemaRewrites S ++ leafRewrites S`.

    ⚠ KNOWN LIMITATION, in this docstring rather than a dated ledger entry because
    this is where someone will lean on it (`docs/sabotage-procedure.md`, "'The only
    net' is a claim about a test"): **this test cannot fail while
    `_validate_ast_references` is live.** The parser refuses a violating schema before
    any `Rule` is emitted, so part 1 re-observes an invariant rather than testing one.
    Its value is (i) pinning that the CURRENT corpus stays inside `W4Fragment`, and
    (ii) catching a future compiler that mints a leaf TTU target from a *legal* schema.
    The thing that makes it mean anything is
    `test_dsl_refuses_a_ttu_target_in_the_reserved_leaf_namespace`.

    ⚠ SECOND KNOWN LIMITATION, and the reason part 2 exists: this sweep inspects
    **zero leaf-layer TTU targets**. Measured 2026-08-31: 86 leaf-layer rules across
    50 schemas, of which 0 is a TTU. So on the `leafRewrites` half -- the half the ★★
    note in `LeafRules.lean` says the quantifier was widened to reach -- part 1 is
    exactly as vacuous as a `∀ r ∈ schemaRewrites S, …` premise at `SlV`. The
    intermediate counts are asserted below rather than only the verdict, so that
    vacuity is visible in the failure message instead of being inferred.

    SABOTAGE-VERIFIED (a), 2026-08-31: with `_validate_ast_references::check_name`
    neutered to a no-op, this test STAYS GREEN (the corpus contains no violating
    schema to admit) while part 3 goes red. A green sabotage is a finding, per the
    procedure: it is the proof that part 1 alone certifies nothing about the refusal.
    """
    schemas_compiled = 0
    ttu_targets_inspected = 0
    leaf_layer_rules_seen = 0
    leaf_layer_ttu_targets = 0
    offenders: list[str] = []

    for label, text, ow in _all_schema_sources():
        rs = parse_openfga_schema(text, object_wildcard_shapes=ow)
        schemas_compiled += 1
        for rf in rs.rules_and_filters:
            if not isinstance(rf, Rule) or rf.then_pattern is None:
                continue
            out_rel = rf.then_pattern.relation
            is_leaf_layer = out_rel is not None and '.' in out_rel
            if is_leaf_layer:
                leaf_layer_rules_seen += 1
            for tr in _ttu_targets(rf):
                ttu_targets_inspected += 1
                if is_leaf_layer:
                    leaf_layer_ttu_targets += 1
                if not _not_leaf_name(tr):
                    offenders.append(
                        f'{label}: rule -> {out_rel!r} mints subject predicate {tr!r}')

    assert not offenders, (
        'a compiled rule mints a leaf-named TTU subject predicate, which puts the '
        'schema OUTSIDE Lean\'s W4Fragment.NoLeafSubjects:\n  '
        + '\n  '.join(offenders))

    # ANTI-VACUITY: assert what was actually INSPECTED, not just the verdict.
    assert schemas_compiled >= _MIN_SCHEMAS_COMPILED, (
        f'only {schemas_compiled} schemas compiled (floor {_MIN_SCHEMAS_COMPILED}, '
        f'measured 50 on 2026-08-31) -- the sweep lost sources')
    assert ttu_targets_inspected >= _MIN_TTU_TARGETS, (
        f'only {ttu_targets_inspected} TTU targets inspected (floor '
        f'{_MIN_TTU_TARGETS}, measured 28 on 2026-08-31) -- the sweep is going vacuous')
    assert leaf_layer_rules_seen >= _MIN_LEAF_LAYER_RULES, (
        f'only {leaf_layer_rules_seen} leaf-layer rules seen (floor '
        f'{_MIN_LEAF_LAYER_RULES}, measured 86 on 2026-08-31) -- the corpus stopped '
        f'compiling a leaf layer, so this sweep no longer touches `leafRewrites` at all')
    # The intermediate that names the vacuity, so the next reader cannot mistake this
    # test for coverage of the leaf layer. If a corpus ever DOES grow a leaf-layer TTU,
    # this fires and the fix is to delete this assertion and say so in part 2.
    assert leaf_layer_ttu_targets == 0, (
        f'{leaf_layer_ttu_targets} leaf-layer TTU target(s) now exist in the corpus '
        f'(was 0 on 2026-08-31). Good news -- but this docstring and part 2 both claim '
        f'the corpus is leaf-layer-vacuous. Update them.')


# The LOCAL leaf-layer witness. Deliberately NOT added to
# `formal/conformance/corpus.py`: every corpus-sweeping test in the repo would change
# its counts, and several carry `-ge` floors and byte-identity snapshots.
_LEAF_LAYER_TTU_WITNESS = (
    'type user\n'
    'type folder\n'
    '  define viewer: [user]\n'
    'type doc\n'
    '  define parent: [folder]\n'
    '  define banned: [user]\n'
    '  define safe: viewer from parent but not banned\n'
)


def test_a_leaf_layer_ttu_rule_exists_and_is_not_leaf_named():
    """PART 2 — the leaf-layer witness part 1 does not have.

    `LeafRules.lean`'s ★★ note: `NoLeafSubjects` ranges over `schemaRewritesL`, not
    `schemaRewrites`, precisely because a premise quantified over the untainted layer
    alone is discharged vacuously at a schema whose untainted layer is empty
    (`LeafRuleWitness.lrV_untainted_layer_silent`). The Python-side twin of that trap
    is part 1: all 28 corpus TTU targets are untainted-layer, so a sweep that stopped
    at the corpus would certify the `leafRewrites` half by inspecting nothing.

    A leaf-layer TTU rule IS constructible. `define safe: viewer from parent but not
    banned` taints `doc#safe`, so the TTU arm compiles through
    `zanzibar_utils_v1.py::_emit_leaf_expr` onto leaf family `safe.0`. Verified by
    throwaway probe on 2026-08-31 before this assertion was written::

        RULE if: parent None -> then rel: safe.0 sp: 'viewer'
        RULE if: banned None -> then rel: safe.1 sp: None

    This test asserts BOTH halves -- that the rule really is on the leaf layer (its
    target relation contains `'.'`, i.e. it is a compiled leaf family, otherwise the
    witness is not exercising the layer it claims) and that its minted subject
    predicate satisfies `NotLeafName`. Asserting only the second would be the same
    vacuity one level up.

    SABOTAGE-VERIFIED, 2026-08-31: rewriting the witness as `define safe: viewer from
    parent` (dropping `but not banned` -- the innocent-looking edit that keeps a TTU,
    keeps the schema compiling, and keeps a `NotLeafName` check running, so a test that
    asserted only the second half would stay GREEN and silently stop covering the leaf
    layer) untaints `doc#safe`, and the leaf-layer assertion fires with the literal
    output::

        E       AssertionError: the witness produced NO leaf-layer TTU rule -- it is not exercising `leafRewrites` at all. Leaf-layer rules seen: 0
        E       assert 0 > 0
        E        +  where 0 = len([])
        FAILED formal/conformance/test_leaf_namespace_correspondence.py::test_a_leaf_layer_ttu_rule_exists_and_is_not_leaf_named
        1 failed, 4 passed in 0.56s
    """
    rs = parse_openfga_schema(_LEAF_LAYER_TTU_WITNESS)

    leaf_layer_ttu: list[tuple[str, str]] = []
    for rf in rs.rules_and_filters:
        if not isinstance(rf, Rule) or rf.then_pattern is None:
            continue
        out_rel = rf.then_pattern.relation
        if out_rel is None or '.' not in out_rel:
            continue                      # untainted layer -- part 1 already covers it
        for tr in _ttu_targets(rf):
            leaf_layer_ttu.append((out_rel, tr))

    assert len(leaf_layer_ttu) > 0, (
        'the witness produced NO leaf-layer TTU rule -- it is not exercising '
        f'`leafRewrites` at all. Leaf-layer rules seen: {len(leaf_layer_ttu)}')
    assert ('safe.0', 'viewer') in leaf_layer_ttu, (
        f'the witness compiled to an unexpected shape: {leaf_layer_ttu!r}')

    for out_rel, tr in leaf_layer_ttu:
        assert _not_leaf_name(tr), (
            f'leaf-layer rule -> {out_rel!r} mints leaf-named subject predicate {tr!r}')


def test_dsl_refuses_a_ttu_target_in_the_reserved_leaf_namespace():
    """PART 3 — the refusal control. This is what makes parts 1 and 2 mean anything.

    Parts 1 and 2 can only ever pass, because `zanzibar_utils_v1.py::
    _validate_ast_references` rejects a violating schema at PARSE time. So the load-
    bearing claim behind Lean's `NoLeafSubjects` narrowing is not "the corpus happens
    to comply" -- it is "Python REFUSES everything the narrowed fragment excludes".
    That refusal is what is pinned here, on all three routes a `'.'` can reach a
    REFERENCED relation name through the DSL front-end (the fourth route, a dotted
    DECLARED name, is a different guard and gets its own test below).

    ⚠ COVERAGE HOLE THIS CLOSES. Before this module the `'.'`-namespace lock was
    pinned in exactly one place, `tests/test_openfga_json.py::
    test_rejects_reserved_dot_in_referenced_names`, which drives the **JSON**
    front-end (`parse_openfga_json`) and only two of the routes (a
    `directly_related_user_types` restriction and a `computedUserset` ref). Grepped
    2026-08-31: no test anywhere pinned the **DSL** path (`parse_openfga_schema` on a
    `.fga` string), and NO test on either front-end pinned the **TTU target** route --
    which is the one and only route Lean's `ttuTargets` reads. The declared-name lock
    (a different message, "reserved for compiled leaf predicates") was unpinned on
    both front-ends.

    SABOTAGE-VERIFIED (a), 2026-08-31. Neutering the refusal -- `check_name` inside
    `zanzibar_utils_v1.py::_validate_ast_references` replaced by a bare `return`, the
    narrowest plausible weakening (a future contributor "simplifying" a validator that
    no test appeared to need) -- makes this test fail with the literal output::

        FAILED formal/conformance/test_leaf_namespace_correspondence.py::test_dsl_refuses_a_ttu_target_in_the_reserved_leaf_namespace
        E       Failed: DID NOT RAISE ValueError
        1 failed, 4 passed in 0.36s

    Parts 1 and 2 stayed GREEN throughout, and so did the declared-name sibling below
    (a DIFFERENT guard) -- that is what makes the red attributable rather than "the
    file is broken". Under the sabotage the violating schema COMPILES to exactly the
    rule `NoLeafSubjects` forbids, probed in the same session::

        rule -> 'safe' mints subject predicate 'viewer.0'

    i.e. `W4Fragment`'s new field would be FALSE at a schema Python accepted, and the
    Lean narrowing would be unsound. That probe is the reason this test is the
    load-bearing one: it is the only place in the repo where the fragment's Python
    side is asserted rather than assumed.
    """
    # (i) the TTU TARGET -- the route Lean's `ttuTargets` reads, and the whole point.
    ttu_target = (
        'type user\n'
        'type folder\n'
        '  define viewer: [user]\n'
        'type doc\n'
        '  define parent: [folder]\n'
        '  define safe: viewer.0 from parent\n'
    )
    with pytest.raises(ValueError, match='reserved leaf namespace'):
        parse_openfga_schema(ttu_target)

    # (ii) the TTU TUPLESET ref -- the other name a TTU node carries.
    ttu_tupleset = (
        'type user\n'
        'type folder\n'
        '  define viewer: [user]\n'
        'type doc\n'
        '  define parent: [folder]\n'
        '  define safe: viewer from parent.0\n'
    )
    with pytest.raises(ValueError, match='reserved leaf namespace'):
        parse_openfga_schema(ttu_tupleset)

    # (iii) a Computed ref -- DSL parity with the JSON pin.
    computed_ref = (
        'type user\n'
        'type doc\n'
        '  define viewer: [user]\n'
        '  define alias: viewer.0\n'
    )
    with pytest.raises(ValueError, match='reserved leaf namespace'):
        parse_openfga_schema(computed_ref)


def test_dsl_refuses_a_dotted_DECLARED_relation_name():
    """PART 3, sibling — and the NEGATIVE CONTROL for the sabotage above.

    A declared relation name carrying `'.'` is refused by a DIFFERENT guard, in
    `zanzibar_utils_v1.py::parse_schema_ast`'s line loop rather than in
    `::_validate_ast_references`, with a different message. Kept as its own test on
    purpose (`docs/sabotage-procedure.md`, "Make the red attributable"): under the
    sabotage that neuters `_validate_ast_references::check_name` this test must stay
    GREEN, and it does -- probed directly under the sabotage on 2026-08-31::

        declared_dot -> ValueError: relation 'safe.0': '.' is reserved for compiled
        leaf predicates and cannot appear in a declared relation name

    so a reader of that red can tell "one specific guard died" from "the file broke".

    It is independently valuable: grepped 2026-08-31, this message was pinned by NO
    test on either front-end.
    """
    declared_dot = (
        'type user\n'
        'type doc\n'
        '  define safe.0: [user]\n'
    )
    with pytest.raises(ValueError, match='reserved for compiled leaf predicates'):
        parse_openfga_schema(declared_dot)
