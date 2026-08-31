"""**The W4Fragment SCOPE pin -- a field added to the headline theorem's hypothesis
bundle is a SILENT NARROWING, and nothing in this repo could see it.**

`Zanzibar.graph_correct` ("the graph index agrees with the semantics") is stated as

    (hA : GraphAdmission S T) (hF : W4Fragment S T) ... : GraphModel.check sigma q = sem S T q

so `structure W4Fragment` (`formal/lean/ZanzibarProofs/FullScope.lean::W4Fragment`) IS
the scope of the headline guarantee. **Adding a field makes `graph_correct` strictly
WEAKER**: it then covers a strictly smaller class of (schema, store) pairs, while every
existing gate signal reports success.

Why the existing pins cannot raise that alarm -- both failures are structural, not bugs:

* `formal/headline_statements.txt` records the hypothesis BY NAME, `(hF : W4Fragment S T)`.
  Add or delete a field and the pinned statement row stays **byte-identical**. This is
  deliberate; `formal/headline_definitions.txt` lines 4-5 say so in as many words.
* `formal/headline_definitions.txt` DOES carry a `def:Zanzibar.W4Fragment ... fields=(...)`
  row naming all ten fields -- but that file is **auto-regenerated** by
  `python formal/conformance/statement_pin.py --generate`. The act of accepting the change
  destroys the signal. That is the *generated golden* failure mode
  (`docs/sabotage-procedure.md`, "A GENERATED golden cannot witness a change to the tree
  that generates it").

So this module is deliberately built the other way round, and it is the one place in the
repo where the hand-maintained list is the CORRECT design rather than the anti-pattern:

* `W4FRAGMENT_SCOPE` below is **hand-maintained**. Nothing generates it, no `--generate`
  flag rewrites it, and it is not derived from the Lean source. A new field therefore
  cannot arrive with a blank cell -- it has to be adjudicated and classified by a human.
* The other half, the live field list, IS read from the source
  (`_parse_structure_fields`), so the two sides have independent derivations and a
  divergence is a red test rather than a quiet agreement.

Board row: `P20` (deliverable b).

---------------------------------------------------------------------------
WHAT THE CLASSIFICATION COLUMN MEANS
---------------------------------------------------------------------------
Each field is a restriction the PROOF needs. The interesting question for a reader of
`graph_correct` is: *if I hand the real Python backends a schema/store outside this
field, do I find out?*

    LOUD    Python RAISES on schemas/writes violating the field. The proof's scope
            restriction is mirrored by a runtime refusal, so nothing outside the
            theorem can be built.
    SILENT  Python ACCEPTS such schemas/writes. They run fine and are simply OUTSIDE
            the proof -- the theorem says nothing about them.
    MIXED   Some sub-cases raise and others do not. A MIXED row MUST name which
            sub-case is the loud one (`note`), or this module fails.

**Nine of the ten rows are SILENT or MIXED.** That is the honest reading of
`graph_correct`: its hypothesis bundle is overwhelmingly proof-side carry, not a
description of what the implementation refuses. FullScope.lean's own doc comment says
this per field ("Python handles arbitrary strata", "Proof-side carry, not a Python
restriction"); this module is that comment made mechanical.

---------------------------------------------------------------------------
PROBE EVIDENCE (2026-08-31) -- every classification below was re-derived here,
not inherited. Literal observed output, so it survives `.scratch/` being gitignored.
---------------------------------------------------------------------------
Schema-side probe (`parse_openfga_schema`, one violating schema per field):

    computedOrDirect/ttu-in-derived: ADMITTED (strata=1, derived=[('doc', 'view')])
    directArmsBare/userset-direct-arm: ADMITTED (strata=1, derived=[('doc', 'view')])
    directArmsConcrete/star-direct-arm: ADMITTED (strata=1, derived=[('doc', 'approver')])
    computedOnlyOperands/direct-one-stratum-down: ADMITTED (strata=2, derived=[('doc', 'editor'), ('doc', 'view')])
    noUnionDirects/union-reachable-direct: ADMITTED (strata=1, derived=[('doc', 'view')])
    twoStrata/three-strata: ADMITTED (strata=3, derived=[('doc', 'b'), ('doc', 'c'), ('doc', 'd')])
    wsBare/wildcard-userset-over-UNTAINTED: ADMITTED (strata=0, derived=[])
    wsBare/wildcard-userset-over-DERIVED: RAISED UnsupportedByGraphIndex: relation doc#viewer: wildcard userset restriction [group:*#member] over the derived relation group#member needs symbolic composition through residues (v1 scope
    term.NoTtuTarget/untainted-ttu-onto-derived: ADMITTED (strata=2, derived=[('doc', 'view'), ('org', 'member')])
    ttuStarFree/star-tupleset-schema: ADMITTED (strata=0, derived=[])
    term.NoTtuTarget/undeclared-tupleset: RAISED UnsupportedByGraphIndex: relation doc#view: TTU 'member' from 'parent' targets the derived relation 'member', but the containing relation is not itself boolean-tainted, so it compiles to a plain rewrite rule that would carry
    term.NoTtuTarget/mixed-member-types: RAISED UnsupportedByGraphIndex: relation doc#view: TTU 'member' from 'parent' targets the derived relation 'member', but the containing relation is not itself boolean-tainted, so it compiles to a plain rewrite rule that would carry

Store-side probe (`SetEngine.add_tuple`, one violating write per store-level field):

    bareStar/userset-star-subject: ADMITTED (added=True)
    bareStar/object-wildcard-DECLARED: ADMITTED (added=True)
    bareStar/object-wildcard-UNDECLARED: RAISED AdmissionRejected: object wildcard doc:* (relation 'viewer') is not a declared object-wildcard shape
    ttuStarFree/star-subject-on-tupleset: ADMITTED (added=True)
    term.NoStoreSubjectR/derived-userset-subject: ADMITTED (added=True)
    wsBare/bare-star-subject(in-scope control): ADMITTED (added=True)

**One correction to the scoping note this module was written from.** The `term` field's
`NoTtuTarget` half was reported as "enforced by taint propagation, with a residual corner
that raises". The probe says something sharper: in the ORDINARY case (a declared tupleset)
Python does NOT raise -- taint propagates onto the containing relation and the schema
compiles, `derived=[('doc','view'), ('org','member')]`. What excludes it from the fragment
is then `computedOrDirect` (a `.ttu` leaf inside a now-derived def), NOT `term`, and NOT a
Python refusal. Only the two corners where the containing relation stays UNTAINTED
(undeclared tupleset; mixed member types) reach the raise. The row below says that.

---------------------------------------------------------------------------
SABOTAGE (mandatory; `docs/sabotage-procedure.md`)
---------------------------------------------------------------------------
The property guarded: *the live field set of `structure W4Fragment` is exactly the ten
fields adjudicated below, and any change to it is attributable BY NAME.*

BASELINE first, per "Run the check against a CLEAN tree before you sabotage it" --
`python -m pytest formal/conformance/test_w4fragment_scope_pin.py -q` on the untouched
tree: `15 passed in 0.37s`, rc 0. So every red below is attributable to the sabotage and
not to a pre-existing marker.

**Sabotage 1 -- the thing this pin exists for: a NEW field.** Appended
`  dummySabotage : True` to `structure W4Fragment` in FullScope.lean. This is the
narrowest plausible weakening: exactly one more hypothesis, so `graph_correct` is
strictly weaker, the statement pin stays byte-identical and the definition pin is
regenerable. Literal observed output:

    E  AssertionError: UNCLASSIFIED: ['dummySabotage'] is declared by structure W4Fragment but has no W4FRAGMENT_SCOPE row.
    E      If the Lean structure GAINED that field, `Zanzibar.graph_correct` is now
    E      STRICTLY WEAKER -- it covers a SMALLER class of (schema, store) pairs -- and
    E      neither formal/headline_statements.txt (records the hypothesis by NAME) nor
    E      formal/headline_definitions.txt (auto-regenerated) can tell you that.
    E      Adjudicate the narrowing and classify the field here (LOUD / SILENT / MIXED
    E      + `file::symbol` evidence) before updating this pin.
    E      If instead the ROW was deleted from W4FRAGMENT_SCOPE: put it back. The scope
    E      of the headline theorem did not change; only the record of it did.
    E      Board row P20.
    E  assert not ['dummySabotage']
    E  AssertionError: structure W4Fragment now declares 11 fields, not W4FRAGMENT_FIELD_COUNT=10: ['computedOrDirect', 'directArmsBare', 'directArmsConcrete', 'computedOnlyOperands', 'noUnionDirects', 'twoStrata', 'wsBare', 'bareStar', 'ttuStarFree', 'term', 'dummySabotage']. `Zanzibar.graph_correct`'s hypothesis bundle changed size -- see board row P20.
    FAILED ...::test_w4fragment_fields_match_the_hand_classified_scope_pin
    FAILED ...::test_w4fragment_field_count_is_the_pinned_constant
    2 failed, 13 passed in 0.34s

FullScope.lean was restored with `git checkout -- formal/lean/ZanzibarProofs/FullScope.lean`
and the module re-run: `15 passed in 0.28s`.

`lake build` was deliberately NOT run, and that is a property worth stating: this check
reads SOURCE TEXT, so **it fires on a field addition before, and independently of, any
proof effort** -- at the moment the field is typed, not when the proofs are finished.

**Sabotage 2 -- the complementary direction: a hand-maintained row goes missing** (the
shape a future "tidy-up" produces). Deleted the `twoStrata` row from `W4FRAGMENT_SCOPE`:

    E  AssertionError: UNCLASSIFIED: ['twoStrata'] is declared by structure W4Fragment but has no W4FRAGMENT_SCOPE row.
    E  ...
    E  assert not ['twoStrata']
    E  AssertionError: W4FRAGMENT_SCOPE has 9 rows, not W4FRAGMENT_FIELD_COUNT=10
    E  AssertionError: expected exactly 7 SILENT rows, got {'SILENT': 6, 'MIXED': 3, 'LOUD': 0}
    FAILED ...::test_w4fragment_fields_match_the_hand_classified_scope_pin
    FAILED ...::test_w4fragment_field_count_is_the_pinned_constant
    FAILED ...::test_mixed_and_loud_rows_are_the_minority_and_that_is_the_finding
    3 failed, 11 passed in 0.45s

Restored: `15 passed in 0.38s`.

⚠ **Sabotage 2's FIRST run is the finding, and it changed the code.** The
`len(W4FRAGMENT_SCOPE) >= MIN_FIELDS_PARSED` anti-vacuity floor was originally asserted
BEFORE the set-difference comparison, and it PREEMPTED the attributable message:

    E  AssertionError: W4FRAGMENT_SCOPE carries only 9 row(s); the measured floor is 10. A gutted pin compares against nothing.

That red is true and useless -- it does not name `twoStrata`, so it cannot distinguish
"one row was dropped" from "the pin was gutted". The floor was moved to LAST (see the
comment at its site); only the both-sides-empty state can reach it, which the parse floor
already covers. `docs/sabotage-procedure.md`, "Make the red attributable".

**Sabotage 3 -- the INSTRUMENT, not the subject** ("Sabotage your instrument too"). The
two reds above only prove the COMPARISON works; they say nothing about the extractor,
which is the half that fails silently (`docs/sabotage-procedure.md`, "A check that PARSES
before it compares has two halves"). Blinded `_parse_structure_fields` by clearing its
`body` list before the field scan -- the plausible shape of an indentation-convention
change, not a syntax error:

    E  AssertionError: the W4Fragment field parser recovered only 0 field(s) ([]) from FullScope.lean; the measured floor is 10. This is an INSTRUMENT failure, not a scope change: comparing an empty parse against the pin would report green.
    E  assert 0 >= 10
    E  AssertionError: instrument failure: parsed 0 field(s) ([]), floor 10
    E  AssertionError: assert [] == ['alpha', 'beta', 'delta']
    FAILED ...::test_w4fragment_fields_match_the_hand_classified_scope_pin
    FAILED ...::test_w4fragment_field_count_is_the_pinned_constant
    FAILED ...::test_field_parser_reads_a_synthetic_structure
    3 failed, 12 passed in 0.39s

Restored: `15 passed in 0.40s`. Note that `MIN_FIELDS_PARSED` and the synthetic
known-answer control BOTH fired, and that the well-formedness rows stayed green -- a
blinded extractor is diagnosed as an instrument failure, never as a scope change.
`test_field_parser_refuses_an_absent_structure` is the matching negative control: a
renamed structure must be a `LookupError`, because a parser that returned `[]` would
otherwise let the equality assertion agree with an empty dict.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# --------------------------------------------------------------------------- #
# Locations
# --------------------------------------------------------------------------- #
_REPO_ROOT = Path(__file__).resolve().parents[2]
FULLSCOPE_LEAN = _REPO_ROOT / "formal" / "lean" / "ZanzibarProofs" / "FullScope.lean"
STRUCTURE_NAME = "W4Fragment"

#: Exact number of fields `structure W4Fragment` carries. MEASURED, not guessed:
#: `grep -n "structure W4Fragment" -A 30 formal/lean/ZanzibarProofs/FullScope.lean`
#: on 2026-08-31 shows ten field bindings (:194-212), and
#: `formal/headline_definitions.txt`'s `def:Zanzibar.W4Fragment` row independently
#: lists the same ten in `fields=(...)`. Changing this number is a deliberate,
#: reviewed act -- see the module docstring.
W4FRAGMENT_FIELD_COUNT = 10

#: ANTI-VACUITY floor on the PARSE, asserted before any comparison. A parser that
#: located nothing (structure renamed, indentation convention changed, file moved)
#: returns an empty list, which would compare "equal" against an empty dict and
#: report green. Measured minimum = the live field count on 2026-08-31 (10); it is a
#: `>=` so that ADDING a field can never be blocked by the floor itself -- the
#: equality assertion is what adjudicates additions.
MIN_FIELDS_PARSED = 10

_VALID_CLASSIFICATIONS = frozenset({"LOUD", "SILENT", "MIXED"})


# --------------------------------------------------------------------------- #
# The hand-maintained scope pin. NOTHING REGENERATES THIS.
# --------------------------------------------------------------------------- #
# Keys: the field names of `structure W4Fragment`.
# Values: {"demands", "classification", "evidence", "note"}.
#   demands        -- one sentence, plain English, what the field requires.
#   classification -- LOUD / SILENT / MIXED, from the reader's point of view
#                     ("does Python tell me when I leave the theorem's scope?").
#   evidence       -- a `file::symbol` citation (or a repo path) that a reader can
#                     grep. Bare line numbers are banned: they go stale here fast.
#   note           -- REQUIRED for MIXED (names the loud sub-case); optional otherwise.
W4FRAGMENT_SCOPE: dict[str, dict[str, str]] = {
    "computedOrDirect": {
        "demands": (
            "Every derived (boolean-tainted) relation's definition is a boolean tree over "
            "`computed` references and `direct` grant arms only, so a `.ttu` leaf inside a "
            "derived definition is out of scope."
        ),
        "classification": "SILENT",
        "evidence": "zanzibar_utils_v1.py::_build_plan_tree",
        "note": (
            "`_build_plan_tree.build` compiles a TTU under a derived def straight into a "
            "`PDerivedTTU` plan leaf with no rejection; probe "
            "`computedOrDirect/ttu-in-derived` compiled to 1 stratum with `doc#view` derived. "
            "FullScope.lean's own comment concedes it: 'Python also compiles "
            "PDerivedTTU/PDerivedUserset plan leaves, still out of scope (W3a decision)'."
        ),
    },
    "directArmsBare": {
        "demands": (
            "A derived definition's `direct` arms carry only BARE type restrictions "
            "(`[user]`), never a userset restriction (`[group#member]`)."
        ),
        "classification": "SILENT",
        "evidence": "zanzibar_utils_v1.py::_build_plan_tree",
        "note": (
            "An untainted userset restriction folds into the `pure` closure leaf and a "
            "tainted one becomes a `PDerivedUserset` node; neither path raises. Probe "
            "`directArmsBare/userset-direct-arm` was ADMITTED. FullScope.lean calls this "
            "one 'Proof-side carry'."
        ),
    },
    "directArmsConcrete": {
        "demands": (
            "A derived definition's `direct` arms carry no wildcard-flagged restriction: "
            "`[user:*]` on a boolean relation is out of scope."
        ),
        "classification": "SILENT",
        "evidence": "zanzibar_utils_v1.py::_build_plan_tree",
        "note": (
            "Probe `directArmsConcrete/star-direct-arm` "
            "(`define approver: [user, user:*] but not banned`) was ADMITTED at 1 stratum, "
            "matching FullScope.lean's explicit 'Python admits the shape this excludes'. It "
            "is a VACUITY boundary -- no cascade constructor exists there -- not an "
            "unsoundness one."
        ),
    },
    "computedOnlyOperands": {
        "demands": (
            "A derived definition's DERIVED `computed` operands are themselves "
            "ComputedOnly, i.e. only the top derived definition may carry a `direct` arm."
        ),
        "classification": "SILENT",
        "evidence": "zanzibar_utils_v1.py::compile_boolean_schema",
        "note": (
            "Probe `computedOnlyOperands/direct-one-stratum-down` "
            "(`editor: [user] but not banned` read by `view: editor but not banned`) "
            "compiled to 2 strata with both relations derived, no rejection."
        ),
    },
    "noUnionDirects": {
        "demands": (
            "A derived definition's `direct` arms are never union-reachable "
            "(`exprDirects e = []`): they sit under `and` / `but not` only, the canonical "
            "`but not` shape."
        ),
        "classification": "SILENT",
        "evidence": "zanzibar_utils_v1.py::_build_plan_tree",
        "note": (
            "A union-reachable direct arm compiles to a `PUnion` over a `PClosureLeaf`; "
            "probe `noUnionDirects/union-reachable-direct` "
            "(`view: [user] or (editor but not banned)`) was ADMITTED."
        ),
    },
    "twoStrata": {
        "demands": (
            "The derived dependency graph is at most TWO strata deep: a derived relation's "
            "derived operands have no derived operands of their own."
        ),
        "classification": "SILENT",
        "evidence": (
            "formal/conformance/test_conformance_nary_strata.py::test_nary_corpus_encoding"
        ),
        "note": (
            "Python handles arbitrary strata -- probe `twoStrata/three-strata` compiled to "
            "3 strata with no rejection. The only machine-check anywhere is CORPUS-scoped, "
            "not admission-scoped: `test_nary_corpus_encoding` asserts "
            "`n_strata <= 2` so that a conformance corpus cannot drift out of "
            "`GRAPH_FRAGMENT` unnoticed. It says nothing about user schemas."
        ),
    },
    "wsBare": {
        "demands": (
            "Every declared wildcard restriction in the schema is bare (`[T:*]`), never a "
            "wildcard userset (`[T:*#p]`)."
        ),
        "classification": "MIXED",
        "evidence": "zanzibar_utils_v1.py::_build_plan_tree",
        "note": (
            "LOUD sub-case: a wildcard userset over a DERIVED relation raises "
            "`UnsupportedByGraphIndex` -- the `r.wildcard` raise in `_build_plan_tree.build`'s "
            "`Direct` arm, plus the star-tupleset through-shape form in "
            "`zanzibar_utils_v1.py::_reject_object_wildcard_scope`. SILENT sub-case: over an "
            "UNTAINTED relation `[group:*#member]` is admitted outright (probe "
            "`wsBare/wildcard-userset-over-UNTAINTED`, ADMITTED, 0 strata), and that is the "
            "sub-case a reader is most likely to hit."
        ),
    },
    "bareStar": {
        "demands": (
            "Every stored tuple whose subject name is `*` has a BARE subject predicate, and "
            "no stored tuple has a wildcard OBJECT (`doc:*`)."
        ),
        "classification": "MIXED",
        "evidence": "setengine/engine.py::SetEngine._validate",
        "note": (
            "LOUD sub-case, and only this one: a wildcard-OBJECT write on an UNDECLARED "
            "object-wildcard shape raises `AdmissionRejected` "
            "('object wildcard doc:* (relation 'viewer') is not a declared object-wildcard "
            "shape'). SILENT sub-cases: a wildcard object on a DECLARED shape is admitted "
            "(that is what `object_wildcard_shapes` is FOR), and a userset-star subject "
            "(`group:*#member`) is admitted wherever a `[group:*#member]` restriction "
            "exists -- both probe-confirmed ADMITTED."
        ),
    },
    "ttuStarFree": {
        "demands": (
            "No stored tuple with a `*` subject sits on a relation that some TTU rewrite "
            "reads as its tupleset."
        ),
        "classification": "SILENT",
        "evidence": "zanzibar_utils_v1.py::_validate_ttu_tuplesets",
        "note": (
            "The opposite of a refusal: `_validate_ttu_tuplesets` rejects USERSET "
            "restrictions in tuplesets while deliberately keeping wildcard restrictions "
            "ALLOWED ('star tuplesets are this repo's deliberate object-wildcard "
            "extension'). Probe `ttuStarFree/star-subject-on-tupleset` wrote "
            "`folder:* parent doc:d1` on a TTU tupleset: ADMITTED (added=True)."
        ),
    },
    "term": {
        "demands": (
            "A conjunction: a derived relation is never the TARGET of a TTU rewrite "
            "(NoTtuTarget) and never appears as the predicate of a stored userset subject "
            "(NoStoreSubjectR)."
        ),
        "classification": "MIXED",
        "evidence": "zanzibar_utils_v1.py::_validate_ttu_tuplesets",
        "note": (
            "LOUD sub-case, and it is NARROWER than it looks: `_validate_ttu_tuplesets` "
            "raises `UnsupportedByGraphIndex` for a TTU onto a derived relation only while "
            "the CONTAINING relation stays untainted -- reachable via an undeclared tupleset "
            "or mixed member types (both probe-confirmed RAISED). In the ordinary declared "
            "case taint propagates onto the container and the schema COMPILES (probe "
            "`term.NoTtuTarget/untainted-ttu-onto-derived`: ADMITTED, 2 strata); what "
            "removes it from the fragment is then `computedOrDirect`, not `term`, and not a "
            "raise. The `NoStoreSubjectR` half is fully SILENT: a stored subject whose "
            "predicate is a derived relation was ADMITTED (added=True)."
        ),
    },
}


# --------------------------------------------------------------------------- #
# The parser -- located by NAME, never by line number
# --------------------------------------------------------------------------- #
_FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_'!?]*)\s*:(?!=)")


def _strip_lean_comments(lines: list[str]) -> list[str]:
    """Blank out `--` line comments and `/- ... -/` block comments.

    Structure bodies in this tree carry neither today; the stripper exists so that a
    future field annotated with a comment cannot smuggle a fake `name :` binding past
    `_FIELD_RE`, and so that a commented-OUT field is not counted as live.
    """
    out: list[str] = []
    depth = 0
    for line in lines:
        buf = []
        i = 0
        while i < len(line):
            two = line[i:i + 2]
            if depth == 0 and two == "--":
                break
            if two == "/-":
                depth += 1
                i += 2
                continue
            if two == "-/" and depth > 0:
                depth -= 1
                i += 2
                continue
            if depth == 0:
                buf.append(line[i])
            i += 1
        out.append("".join(buf).rstrip())
    return out


def _parse_structure_fields(source: str, name: str) -> list[str]:
    """Return the field names of `structure <name>` in `source`, in declaration order.

    Located by NAME (a `^structure <name>` header at column 0), never by line number.
    The body is every line after the header up to the first non-blank line at column 0
    (the next top-level declaration, including its `/--` doc comment). Within the body,
    a FIELD is a line at the body's own base indentation matching `ident :`; anything
    more deeply indented is a continuation of the previous field's type.

    Raises `LookupError` if the structure is absent, or if its header is ambiguous.
    """
    lines = source.splitlines()
    header_re = re.compile(rf"^structure\s+{re.escape(name)}\b")
    starts = [i for i, ln in enumerate(lines) if header_re.match(ln)]
    if not starts:
        raise LookupError(
            f"no `structure {name}` header at column 0 in the given Lean source; the "
            f"structure was renamed, moved, or this parser's convention no longer holds"
        )
    if len(starts) > 1:
        raise LookupError(
            f"`structure {name}` header appears {len(starts)} times (lines "
            f"{[i + 1 for i in starts]}); refusing to guess which one is the scope of "
            f"the headline theorem"
        )
    start = starts[0]

    body: list[str] = []
    for line in lines[start + 1:]:
        if not line.strip():
            body.append(line)
            continue
        if not line[:1].isspace():          # column 0 => next top-level declaration
            break
        body.append(line)

    body = _strip_lean_comments(body)
    live = [ln for ln in body if ln.strip()]
    if not live:
        return []
    base = min(len(ln) - len(ln.lstrip()) for ln in live)

    fields: list[str] = []
    for line in live:
        if len(line) - len(line.lstrip()) != base:
            continue                        # continuation of the previous field's type
        m = _FIELD_RE.match(line.strip())
        if m:
            fields.append(m.group(1))
    return fields


def _live_fields() -> list[str]:
    return _parse_structure_fields(
        FULLSCOPE_LEAN.read_text(encoding="utf-8"), STRUCTURE_NAME
    )


# --------------------------------------------------------------------------- #
# The pin
# --------------------------------------------------------------------------- #
def test_w4fragment_fields_match_the_hand_classified_scope_pin():
    """The live `structure W4Fragment` field set is exactly the hand-adjudicated one.

    See the module docstring for the two sabotages (a new Lean field; a deleted dict
    row) and their literal output.
    """
    assert FULLSCOPE_LEAN.is_file(), f"{FULLSCOPE_LEAN} is missing"
    parsed = _live_fields()

    # ---- ANTI-VACUITY, before any comparison. A parser that read nothing must not
    # ---- be able to "agree" with a dict that happens to be empty too.
    assert len(parsed) >= MIN_FIELDS_PARSED, (
        f"the W4Fragment field parser recovered only {len(parsed)} field(s) "
        f"({parsed}) from {FULLSCOPE_LEAN.name}; the measured floor is "
        f"{MIN_FIELDS_PARSED}. This is an INSTRUMENT failure, not a scope change: "
        f"comparing an empty parse against the pin would report green."
    )
    assert len(parsed) == len(set(parsed)), (
        f"duplicate field names parsed out of structure {STRUCTURE_NAME}: {parsed}"
    )

    live = set(parsed)
    pinned = set(W4FRAGMENT_SCOPE)
    added = sorted(live - pinned)
    removed = sorted(pinned - live)

    assert not added, (
        f"UNCLASSIFIED: {added} is declared by structure {STRUCTURE_NAME} but has no "
        f"W4FRAGMENT_SCOPE row.\n"
        f"  If the Lean structure GAINED that field, `Zanzibar.graph_correct` is now\n"
        f"  STRICTLY WEAKER -- it covers a SMALLER class of (schema, store) pairs -- and\n"
        f"  neither formal/headline_statements.txt (records the hypothesis by NAME) nor\n"
        f"  formal/headline_definitions.txt (auto-regenerated) can tell you that.\n"
        f"  Adjudicate the narrowing and classify the field here (LOUD / SILENT / MIXED\n"
        f"  + `file::symbol` evidence) before updating this pin.\n"
        f"  If instead the ROW was deleted from W4FRAGMENT_SCOPE: put it back. The scope\n"
        f"  of the headline theorem did not change; only the record of it did.\n"
        f"  Board row P20."
    )
    assert not removed, (
        f"STALE: {removed} has a W4FRAGMENT_SCOPE row but is no longer declared by "
        f"structure {STRUCTURE_NAME}.\n"
        f"  A DELETED W4Fragment field makes `Zanzibar.graph_correct` STRICTLY STRONGER\n"
        f"  (it now covers MORE schemas) -- good news, and just as invisible to the\n"
        f"  statement pin as the weakening is. Record it deliberately: drop the row and\n"
        f"  W4FRAGMENT_FIELD_COUNT together, and say in the commit what widened.\n"
        f"  Board row P20."
    )
    assert live == pinned

    # ---- The second anti-vacuity floor, deliberately LAST. It is the belt to the
    # ---- parse floor's braces (only the both-sides-empty state can reach it), and it
    # ---- is ordered after the set-difference assertions ON PURPOSE: run first, it
    # ---- PREEMPTED the message that names the missing field, turning an attributable
    # ---- red ("twoStrata is in structure W4Fragment but has no row") into a bare
    # ---- "carries only 9 row(s)". Observed during sabotage 2; see the module
    # ---- docstring, and docs/sabotage-procedure.md "Make the red attributable".
    assert len(W4FRAGMENT_SCOPE) >= MIN_FIELDS_PARSED, (
        f"W4FRAGMENT_SCOPE carries only {len(W4FRAGMENT_SCOPE)} row(s); the measured "
        f"floor is {MIN_FIELDS_PARSED}. A gutted pin compares against nothing."
    )


def test_w4fragment_field_count_is_the_pinned_constant():
    """The field COUNT is a named constant, so a same-size swap cannot slip through.

    Set equality alone would accept "delete one field, add another" as long as the
    dict were edited to match; pinning the count as well makes the arity of the
    headline hypothesis bundle a reviewed number in its own right.
    """
    parsed = _live_fields()
    assert len(parsed) >= MIN_FIELDS_PARSED, (
        f"instrument failure: parsed {len(parsed)} field(s) ({parsed}), floor "
        f"{MIN_FIELDS_PARSED}"
    )
    assert len(parsed) == W4FRAGMENT_FIELD_COUNT, (
        f"structure {STRUCTURE_NAME} now declares {len(parsed)} fields, not "
        f"W4FRAGMENT_FIELD_COUNT={W4FRAGMENT_FIELD_COUNT}: {parsed}. "
        f"`Zanzibar.graph_correct`'s hypothesis bundle changed size -- see board row P20."
    )
    assert len(W4FRAGMENT_SCOPE) == W4FRAGMENT_FIELD_COUNT, (
        f"W4FRAGMENT_SCOPE has {len(W4FRAGMENT_SCOPE)} rows, not "
        f"W4FRAGMENT_FIELD_COUNT={W4FRAGMENT_FIELD_COUNT}"
    )


@pytest.mark.parametrize("field", sorted(W4FRAGMENT_SCOPE))
def test_every_scope_row_is_well_formed(field):
    """No blank cells: a future field cannot be waved through with an empty row.

    Requires prose, a valid classification, and a greppable `file::symbol` (or path)
    citation -- CLAUDE.md's rule that a trap must cite a symbol that EXISTS, and that
    bare line numbers go stale. MIXED additionally requires a note naming the loud
    sub-case, because "some of it raises" is not actionable on its own.
    """
    row = W4FRAGMENT_SCOPE[field]
    assert set(row) <= {"demands", "classification", "evidence", "note"}, (
        f"{field}: unexpected key(s) {sorted(set(row) - {'demands', 'classification', 'evidence', 'note'})}"
    )

    demands = row.get("demands", "")
    assert isinstance(demands, str) and len(demands.strip()) >= 40, (
        f"{field}: `demands` must be a real one-sentence statement of what the field "
        f"requires, got {demands!r}"
    )

    classification = row.get("classification", "")
    assert classification in _VALID_CLASSIFICATIONS, (
        f"{field}: classification {classification!r} is not one of "
        f"{sorted(_VALID_CLASSIFICATIONS)}"
    )

    evidence = row.get("evidence", "")
    assert isinstance(evidence, str) and evidence.strip(), f"{field}: empty `evidence`"
    assert "::" in evidence or "/" in evidence, (
        f"{field}: evidence {evidence!r} is neither a `file::symbol` citation nor a repo "
        f"path -- a reader must be able to grep it"
    )
    assert not re.search(r":\d+", evidence), (
        f"{field}: evidence {evidence!r} cites a bare line number; line numbers in this "
        f"repo go stale fast -- cite `file::symbol`"
    )

    note = row.get("note", "")
    if classification == "MIXED":
        assert isinstance(note, str) and len(note.strip()) >= 40, (
            f"{field} is MIXED but carries no usable note. A MIXED row MUST name which "
            f"sub-case Python raises on -- otherwise a reader cannot tell whether their "
            f"schema is the loud half or the silent half."
        )
        assert "LOUD" in note, (
            f"{field} is MIXED but its note never says which sub-case is LOUD: {note!r}"
        )


def test_mixed_and_loud_rows_are_the_minority_and_that_is_the_finding():
    """A standing, deliberately-stated summary: `graph_correct`'s scope is mostly carry.

    This is not decoration. The single most misleading way to read the headline theorem
    is to assume its hypothesis bundle describes what the implementation refuses. It
    does not: no W4Fragment field is fully LOUD, and the majority are entirely SILENT.
    Pinning that ratio means a future session that makes a field genuinely enforced
    (or that quietly loosens an existing refusal) has to come here and say so.
    """
    counts = {c: 0 for c in _VALID_CLASSIFICATIONS}
    for row in W4FRAGMENT_SCOPE.values():
        counts[row["classification"]] += 1

    assert counts["LOUD"] == 0, (
        f"a W4Fragment field is now classified LOUD ({counts}). If Python really does "
        f"refuse every schema outside that field, say so here and in the field's row -- "
        f"it is a genuine strengthening of what a reader can rely on."
    )
    assert counts["MIXED"] == 3, (
        f"expected exactly 3 MIXED rows (wsBare, bareStar, term), got {counts}"
    )
    assert counts["SILENT"] == 7, (
        f"expected exactly 7 SILENT rows, got {counts}"
    )
    assert sum(counts.values()) == W4FRAGMENT_FIELD_COUNT


# --------------------------------------------------------------------------- #
# Instrument controls (docs/sabotage-procedure.md, "Sabotage your instrument too")
# --------------------------------------------------------------------------- #
_SYNTHETIC = '''\
/-- A doc comment that mentions `structure Decoy` and even a fake
    field `notAField : Nope` at an indentation that must be ignored. -/
structure Sample (S : Schema) (T : Store) : Prop where
  alpha : Nat
  beta : forall x, P x ->
    Q x
  -- gammaCommentedOut : Bool
  delta : True
  deriving Repr

/-- The next top-level declaration; `epsilon : Wrong` below must not be read. -/
def after (s : Sample) : Nat :=
  let epsilon : Nat := 1
  epsilon

structure Other where
  zeta : Nat
'''


def test_field_parser_reads_a_synthetic_structure():
    """POSITIVE CONTROL with a known answer.

    The two sabotages in the module docstring only prove the COMPARISON works -- they
    feed the parser an input in exactly the shape it already handles
    (`docs/sabotage-procedure.md`, "A check that PARSES before it compares has two
    halves"). This fixture drives the shapes that would silently corrupt the field
    list: a doc comment above the header containing a decoy `name : Type` line, a
    multi-line field body, a commented-out field, a `deriving` line, a following
    top-level `def` with an indented local binding, and a second structure.
    """
    assert _parse_structure_fields(_SYNTHETIC, "Sample") == ["alpha", "beta", "delta"]
    assert _parse_structure_fields(_SYNTHETIC, "Other") == ["zeta"]


def test_field_parser_refuses_an_absent_structure():
    """NEGATIVE CONTROL: a renamed/moved structure must be an ERROR, never an empty list.

    Silence is the failure mode this whole module exists to close. If
    `_parse_structure_fields` returned `[]` for a structure it could not find, the
    equality assertion in the main pin would still have the anti-vacuity floor to fall
    back on -- but the diagnosis would be wrong. Fail at the read.
    """
    with pytest.raises(LookupError, match="no `structure W4FragmentRenamed` header"):
        _parse_structure_fields(_SYNTHETIC, "W4FragmentRenamed")

    doubled = _SYNTHETIC + "\nstructure Other where\n  eta : Nat\n"
    with pytest.raises(LookupError, match="appears 2 times"):
        _parse_structure_fields(doubled, "Other")
