"""`TK119`: the compiled rewrite-rule set, differential-checked against the Lean definition.

`formal/CORRESPONDENCE.md`'s `keyLeafRewrites` / `leafRewrites` / `schemaRewritesL` row
used to carry a "50/50 schemas, 0 mismatches" number from a one-off 2026-08-16 probe that
transcribed the model into Python. Nothing re-ran it. This module replaces that number
with a test that runs the Lean definition ITSELF: `zcli mode="leaf-rules"`
(`formal/lean/ZanzibarProofs/Cli.lean::leafRulesJson`) prints
`GraphIndex/RulesWrite.lean::schemaRewrites S` (the untainted fanout) and
`GraphIndex/LeafRules.lean::leafRewrites S` (each derived key's closure-leaf rules) for
the schema, and each half must equal what `src/zanzibar/schema/compiler.py::compile_ruleset`
actually emits (`src/zanzibar/schema/compiler.py::_emit_expr` for the untainted half,
`src/zanzibar/schema/boolean.py::_emit_leaf_expr` for the leaf half). The plan and the
measurements behind every number here are in
`docs/tk119-leaf-rules-differential-2026-10-14.md`.

WHAT IS SWEPT (`_SOURCES`), with NO expected refusals (challenge X6): every curated corpus
(the four `test_conformance_fragment.py::_FAMILIES`, cross-checked by
`test_corpus_families_match_the_fragment_sweep`), every `tests/fga_schemas/*.fga` fixture,
the constructed `corpus.py::LEAF_RULE_WITNESSES` and `corpus.py::TK126_SERVED_SCHEMAS`. A
Python compile refusal on any of them is a FAILURE, never a skip: record (c) below says why
(a skip-on-refusal comparator goes GREEN under the S9 twin).

HOW RULES ARE COMPARED. A Python `Rule` is normalised to the model's `RRule` shape,
`(objectType, matchRel, outRel, "computed")` or `(objectType, matchRel, outRel, "ttu", tr)`,
by `_normalise`, which checks EVERY field of `RelationalTriplePattern` (the set is read off
`dataclasses.fields`, so a new field fails loudly instead of being flattened into a match).
Directs compile to `Filter`s / `RewriteFilter`s, not `Rule`s, matching `exprArms`'
`.direct _ => []`. Rules whose outRel carries a `.` are the leaf half (declared names cannot,
`P23`). Then, per half:

* MULTISET equality (`collections.Counter`), never set equality: both sides keep a
  duplicated arm, and `W7` (`(a or a) but not c`) is the input on which a multiset and a
  set comparison give different verdicts (record (d) below).
* ORDER, measured 2026-10-14 (challenge C2) and asserted: the untainted half is in the SAME
  order on both sides, and within one derived key (same object type and public relation)
  the leaf rules are in the same order. The order ACROSS derived keys is NOT compared: Python
  walks `sorted(tainted)` (`boolean.py::compile_boolean_schema`), the model walks declaration
  order (`leafRewrites` filters `S.defs`), and nine sources differ that way. Rule order is
  not observable through `rewriteStep` (a `filterMap` over all rules).

THE ONE KNOWN DISAGREEMENT (`TK132`, positively pinned, never xfailed). A TTU arm inside a
derived def whose target NAME is derived on some type, but not on any type the tupleset
admits: Python's type-aware `boolean.py::_is_pure` keeps the arm as a closure leaf, the
model's `Leaf.lean::isPure` (`derivedAnywhere`, by name) drops it and shifts the later
leaves down. `_TK132_EXPECTED` records each of the four witnesses' diff EXACTLY, and
`test_mismatching_sources_are_exactly_tk132_and_sweep_is_not_vacuous` asserts no fifth
source mismatches. When TK132
fixes the model, these pins go red; its builder deletes the entries in the same commit. The
Python side is the oracle-checked one (`tests/test_tk126_ttu_target_name_collision.py`), so
the pin says "the model is out of date here", not "Python is wrong".

SABOTAGE (2026-10-14, `docs/sabotage-procedure.md`). Permanent: `test_python_side_sabotages_are_caught`
re-runs the Python half under two in-process mutations of the compiler and asserts exactly
which sources go red. One-off runs of this whole module, literal pytest summary lines:

* Baseline: `73 passed`. The sweep measured 66 sources (SCHEMAS 27, MULTI_STRATUM 1,
  TTU_USERSET 5, SELF_REF 2, fga 15, WIT 8, TK126 8), 62 agreeing, 44 of those with a
  non-empty leaf half (32 corpus/fixture + 7 witnesses + 5 TK126), and the cross-key order
  differing on 9 (the doc's list, unchanged).
* (a) S11 twin (a closure leaf keeps only its first rule, once per leaf): `7 failed, 66
  passed` -- the `W2`, `W3b`, `W6`, `W7` params, the `W3` TK132 pin (its diff vanishes), the
  sweep test and the permanent test; every corpus and fixture param stays GREEN. Literal:
  `AssertionError: WIT:W2: the model's compiled rules differ from compile_ruleset's (per
  half: python_only, lean_only): {'leaf': ([], [('doc', 'b', 'viewer.0', 'computed')])}`.
* (b) Rule-only off-by-one (`boolean.py`'s `_rewrite_rule` reference bumps `R.i` to
  `R.(i+1)`, routing untouched): `50 failed, 23 passed` -- the 44 agreeing non-empty-leaf
  params, all 4 TK132 pins, the sweep test and the permanent test; zero Python refusals. Literal: `AssertionError: WIT:W1: ... {'leaf': ([('doc',
  'banned', 'access.2', 'computed'), ('doc', 'parent', 'access.1', 'ttu', 'viewer')],
  [('doc', 'banned', 'access.1', 'computed'), ('doc', 'parent', 'access.0', 'ttu',
  'viewer')])}`.
* (c) S9 twin (leaf rules target the PUBLIC relation): `50 failed, 23 passed`, every one a
  Python refusal surfacing as a failure: `ValueError: Rule rewrites into a derived-public
  family: Rule(...)`. A skip-on-refusal comparator reported 0 mismatches under this
  mutation in the 2026-10-14 scout probe, which is why a refusal here is never a skip.
* (d) Python dedups a closure leaf's duplicated arms (multiset control): `3 failed, 70
  passed` -- `W7`, the sweep and the permanent test: `{'leaf': ([], [('doc', 'a',
  'viewer.0', 'computed')])}`.
* (e) A closure leaf's rules in REVERSE order (within-key order control): `4 failed, 69
  passed` -- `W2`, `W3b`, `W6` on the ORDER assertion, plus the permanent test.
* (f) LEAN emitter control (challenge X5): `rruleJson` printed `outRel` with its `.i`
  stripped, `Cli`-only rebuild: `51 failed, 22 passed`, caught FIRST at the runner seam
  (`runner.run_leaf_rules`: `rules on the wrong side of the half split`). With that seam
  check disabled in-process, still `51 failed, 22 passed`, now by the comparator: `{'leaf':
  ([('doc', 'b1', 's1.1', 'computed'), ...` vs the stripped names. Restored, rebuilt, `73
  passed`.
"""
from __future__ import annotations

import dataclasses
import glob
from collections import Counter
from pathlib import Path

import pytest

from formal.conformance import runner
from formal.conformance.corpus import (
    LEAF_RULE_WITNESSES,
    MULTI_STRATUM_SCHEMAS,
    SCHEMAS,
    SELF_REFERENTIAL_SCHEMAS,
    TK126_SERVED_SCHEMAS,
    TTU_USERSET_SCHEMAS,
)
from formal.conformance.encode import build_request
from zanzibar.schema import boolean as boolean_mod
from zanzibar.schema import parse_openfga_schema
from zanzibar.schema.rules import Filter, RelationalTriplePattern, Rule

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: The curated families, exactly `test_conformance_fragment.py::_FAMILIES` (asserted by
#: `test_corpus_families_match_the_fragment_sweep`; not imported, because that module
#: imports `test_conformance_graph` -> `backends` -> the composed store, and an import break
#: there must not stop this module from collecting).
_FAMILIES = (
    ("SCHEMAS", SCHEMAS),
    ("MULTI_STRATUM", MULTI_STRATUM_SCHEMAS),
    ("TTU_USERSET", TTU_USERSET_SCHEMAS),
    ("SELF_REF", SELF_REFERENTIAL_SCHEMAS),
)


def _collect_sources() -> dict[str, tuple[str, frozenset]]:
    out: dict[str, tuple[str, frozenset]] = {}
    for label, fam in _FAMILIES:
        for name, spec in fam.items():
            out[f"{label}:{name}"] = (spec[0], frozenset(spec[2]))
    for f in sorted(glob.glob(str(_REPO_ROOT / "tests" / "fga_schemas" / "*.fga"))):
        out[f"fga:{Path(f).name}"] = (Path(f).read_text(encoding="utf-8"), frozenset())
    for name, text in LEAF_RULE_WITNESSES.items():
        out[f"WIT:{name}"] = (text, frozenset())
    for name, text in TK126_SERVED_SCHEMAS.items():
        out[f"TK126:{name}"] = (text, frozenset())
    return out


_SOURCES = _collect_sources()

#: The `TK132` class: the exact `(python_only, lean_only)` diff per half, sorted. Measured
#: 2026-10-14 by the scout and challenge probes and re-measured by this module on its first
#: run; byte-identical to `docs/tk119-leaf-rules-differential-2026-10-14.md` sec 4. A half not
#: listed must AGREE. TK132's builder deletes these entries when the model is fixed.
_TK132_EXPECTED: dict[str, dict[str, tuple[list, list]]] = {
    "TK126:D": {"leaf": (
        [("doc", "banned", "viewer.2", "computed"), ("doc", "parent", "viewer.1", "ttu", "viewer")],
        [("doc", "banned", "viewer.1", "computed")])},
    "TK126:D_nested": {"leaf": (
        [("doc", "banned", "viewer.2", "computed"), ("doc", "parent", "viewer.1", "ttu", "viewer")],
        [("doc", "banned", "viewer.1", "computed")])},
    "TK126:SlXt": {"leaf": (
        [("doc", "banned", "access.1", "computed"), ("doc", "parent", "access.0", "ttu", "viewer")],
        [("doc", "banned", "access.0", "computed")])},
    "WIT:W3": {"leaf": (
        [("doc", "parent", "viewer.0", "ttu", "viewer")],
        [])},
}

#: Non-vacuity floor: matched sources whose leaf half is NON-EMPTY. Measured 2026-10-14 by
#: this module's own sweep (`_sweep`): 32 corpus/fixture sources (the 2026-08-16 figure,
#: reproduced) + 7 agreeing witnesses + 5 agreeing `TK126` schemas = 44. A `>=`, so adding a
#: source is free; it catches a family that silently went empty or lost its boolean schemas.
MIN_MATCHED_NONEMPTY_LEAF = 44

#: Shape witnesses, pinned BY NAME (challenge X4: a `>= 1` count survives deleting two of
#: three). Each must be a MATCHED source with the shape on both sides.
_LEAF_TTU_WITNESSES = frozenset({"WIT:W1", "WIT:W5", "WIT:W3b"})
_MERGED_LEAF_WITNESSES = frozenset({"WIT:W2", "WIT:W6", "WIT:W3b", "WIT:W7"})
_DUPLICATE_RULE_WITNESSES = frozenset({"WIT:W7"})

#: `tests/fga_schemas/*.fga` count on 2026-10-14 (15). A `>=`: a deleted fixture is red.
MIN_FGA_FIXTURES = 15


# ---- the two sides --------------------------------------------------------------------

#: The `RelationalTriplePattern` fields `_normalise` checks, and the derived caches it may
#: ignore (`init=False, compare=False`, rebuilt from the checked fields in `__post_init__`).
_CHECKED_FIELDS = frozenset({
    "subject_predicate", "subject_type", "subject_name", "relation", "object_type",
    "object_name", "match_wildcards", "object_match_wildcards"})
_DERIVED_FIELDS = frozenset({"_subject", "_object"})


def _normalise(rule: Rule) -> tuple:
    """A Python `Rule` as the model's `RRule` tuple. Fails LOUDLY on anything the tuple
    cannot carry, so a future rule shape cannot be flattened into a false match."""
    if {f.name for f in dataclasses.fields(Rule)} != {"if_pattern", "then_pattern"}:
        raise AssertionError(f"Rule grew a field: {dataclasses.fields(Rule)!r}")
    fields = dataclasses.fields(RelationalTriplePattern)
    names = {f.name for f in fields}
    if names != _CHECKED_FIELDS | _DERIVED_FIELDS:
        raise AssertionError(
            f"RelationalTriplePattern fields changed; _normalise does not cover "
            f"{sorted(names - _CHECKED_FIELDS - _DERIVED_FIELDS)} / stale "
            f"{sorted((_CHECKED_FIELDS | _DERIVED_FIELDS) - names)}")
    if {f.name for f in fields if not f.init} != _DERIVED_FIELDS:
        raise AssertionError("the non-init (derived) RelationalTriplePattern fields changed")
    ip, tp = rule.if_pattern, rule.then_pattern
    if tp is None:
        raise AssertionError(f"Rule with no then_pattern: {rule!r}")
    for side, p in (("if", ip), ("then", tp)):
        if type(p) is not RelationalTriplePattern:
            raise AssertionError(f"{side}-pattern of unexpected type: {rule!r}")
        for f in ("subject_type", "subject_name", "object_name", "object_match_wildcards"):
            if getattr(p, f) is not None:
                raise AssertionError(f"{side}.{f} is set; RRule cannot carry it: {rule!r}")
        if p.match_wildcards is not True:
            raise AssertionError(f"{side}.match_wildcards is not True: {rule!r}")
        if not (isinstance(p.relation, str) and isinstance(p.object_type, str)):
            raise AssertionError(f"{side} relation/object_type not a string: {rule!r}")
    if ip.subject_predicate is not None:
        raise AssertionError(f"if.subject_predicate is set: {rule!r}")
    if tp.object_type != ip.object_type:
        raise AssertionError(f"rule changes object type: {rule!r}")
    sp = tp.subject_predicate
    if sp is None:
        return (ip.object_type, ip.relation, tp.relation, "computed")
    if not isinstance(sp, str):  # Ellipsis included
        raise AssertionError(f"then.subject_predicate is not a relation name: {rule!r}")
    return (ip.object_type, ip.relation, tp.relation, "ttu", sp)


def _python(label: str) -> dict[str, list[tuple]]:
    """Python's compiled rules, split into halves. A compile refusal PROPAGATES."""
    text, ow = _SOURCES[label]
    items = parse_openfga_schema(text, ow).rules_and_filters
    odd = [x for x in items if not isinstance(x, (Rule, Filter))]
    if odd:
        raise AssertionError(f"{label}: rules_and_filters holds a non-Rule/Filter: {odd!r}")
    rules = [_normalise(x) for x in items if isinstance(x, Rule)]
    return {"untainted": [r for r in rules if "." not in r[2]],
            "leaf": [r for r in rules if "." in r[2]]}


def _require_zcli() -> None:
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")


def _lean(label: str) -> dict[str, list[tuple]]:
    _require_zcli()
    text, ow = _SOURCES[label]
    return runner.run_leaf_rules(build_request(text, [], [], ow, mode="leaf-rules"))


def _diff(py: dict, lean: dict) -> dict[str, tuple[list, list]]:
    """Per half that differs as a MULTISET: `(python_only, lean_only)`, each sorted."""
    out = {}
    for half in ("untainted", "leaf"):
        cp, cl = Counter(py[half]), Counter(lean[half])
        if cp != cl:
            out[half] = (sorted((cp - cl).elements()), sorted((cl - cp).elements()))
    return out


def _by_key(rules: list[tuple]) -> dict[tuple, list[tuple]]:
    """Leaf rules grouped by derived key `(objectType, public relation)`, order kept."""
    out: dict[tuple, list[tuple]] = {}
    for r in rules:
        out.setdefault((r[0], r[2].rsplit(".", 1)[0]), []).append(r)
    return out


def _sweep() -> dict[str, dict]:
    """Every source's per-half diff. The Python side is recompiled on each call (no cache),
    so a monkeypatched compiler is seen; the Lean side is memoised by `runner`."""
    return {label: _diff(_python(label), _lean(label)) for label in _SOURCES}


# ---- the differential -----------------------------------------------------------------

@pytest.mark.parametrize("label", sorted(set(_SOURCES) - set(_TK132_EXPECTED)))
def test_leaf_rules_match_python(label):
    """Lean's `schemaRewrites` / `leafRewrites` equal Python's compiled `Rule`s, per half,
    as multisets, with the untainted order and the within-key leaf order equal too."""
    py, lean = _python(label), _lean(label)
    assert _diff(py, lean) == {}, (
        f"{label}: the model's compiled rules differ from compile_ruleset's "
        f"(per half: python_only, lean_only): {_diff(py, lean)!r}")
    assert py["untainted"] == lean["untainted"], (
        f"{label}: untainted rule ORDER differs: py={py['untainted']} lean={lean['untainted']}")
    assert _by_key(py["leaf"]) == _by_key(lean["leaf"]), (
        f"{label}: within-key leaf rule ORDER differs: py={py['leaf']} lean={lean['leaf']}")


@pytest.mark.parametrize("label", sorted(_TK132_EXPECTED))
def test_tk132_gap_is_exactly_the_recorded_diff(label):
    """POSITIVE pin of the `TK132` disagreement: the diff must EQUAL the recorded one, so
    a change on either side (including TK132's fix) turns this red."""
    got = _diff(_python(label), _lean(label))
    assert got == _TK132_EXPECTED[label], (
        f"{label}: the TK132 diff changed. Recorded {_TK132_EXPECTED[label]!r}, got {got!r}. "
        f"If TK132 just fixed `Leaf.lean::isPure`, delete this entry from _TK132_EXPECTED.")


def test_mismatching_sources_are_exactly_tk132_and_sweep_is_not_vacuous():
    """The whole sweep at once: the set of disagreeing sources EQUALS `_TK132_EXPECTED`'s
    keys (no fifth mismatch can hide), and the agreeing sources exercise the shapes the
    corpus alone never reaches, pinned by name."""
    diffs = _sweep()
    assert {k for k, d in diffs.items() if d} == set(_TK132_EXPECTED)
    matched = [k for k, d in diffs.items() if not d]
    lean = {k: _lean(k) for k in matched}
    nonempty = [k for k in matched if lean[k]["leaf"]]
    assert len(nonempty) >= MIN_MATCHED_NONEMPTY_LEAF, (
        f"only {len(nonempty)} matched sources with a non-empty leaf half; floor "
        f"{MIN_MATCHED_NONEMPTY_LEAF}")
    leaf_ttu = {k for k in matched if any(r[3] == "ttu" for r in lean[k]["leaf"])}
    merged = {k for k in matched
              if any(n >= 2 for n in Counter((r[0], r[2]) for r in lean[k]["leaf"]).values())}
    dup = {k for k in matched if any(n >= 2 for n in Counter(lean[k]["leaf"]).values())}
    assert _LEAF_TTU_WITNESSES <= leaf_ttu, sorted(_LEAF_TTU_WITNESSES - leaf_ttu)
    assert _MERGED_LEAF_WITNESSES <= merged, sorted(_MERGED_LEAF_WITNESSES - merged)
    assert _DUPLICATE_RULE_WITNESSES <= dup, sorted(_DUPLICATE_RULE_WITNESSES - dup)
    n_fga = sum(1 for k in _SOURCES if k.startswith("fga:"))
    assert n_fga >= MIN_FGA_FIXTURES, f"only {n_fga} .fga fixtures swept"
    assert set(LEAF_RULE_WITNESSES) == {"W1", "W2", "W3", "W3b", "W4", "W5", "W6", "W7"}
    assert set(TK126_SERVED_SCHEMAS) == {"B", "C", "D", "D_nested", "B_star", "C_cross",
                                         "C_team", "SlXt"}


def test_corpus_families_match_the_fragment_sweep():
    """The curated sources swept here are exactly `test_conformance_fragment.py::ALL_CORPORA`,
    so a new corpus family enrolled there but not here is red. Imported lazily: see
    `_FAMILIES`."""
    from formal.conformance.test_conformance_fragment import ALL_CORPORA
    mine = {k for k in _SOURCES if k.split(":", 1)[0] in {lab for lab, _ in _FAMILIES}}
    assert mine == set(ALL_CORPORA)


def test_tk126_copies_match_their_source():
    """`corpus.py::TK126_SERVED_SCHEMAS` is a verbatim copy of
    `tests/test_tk126_ttu_target_name_collision.py::SERVED`. Imported lazily, so a break in
    that module's import chain fails only this test, not this module's collection."""
    from tests.test_tk126_ttu_target_name_collision import SERVED
    assert TK126_SERVED_SCHEMAS == SERVED


def test_emitter_agrees_with_a_proved_theorem():
    """Instrument cross-check: on `SlXt` the emitted leaf half equals what
    `LeafRules.lean::LeafRuleWitness.lrXt_cross_type_drop` proves `by decide`, so the
    channel prints the model's value and not some re-derivation of it."""
    assert _lean("TK126:SlXt") == {"untainted": [], "leaf": [
        ("team", "z", "viewer.0", "computed"),
        ("team", "y", "viewer.1", "computed"),
        ("doc", "banned", "access.0", "computed")]}


# ---- instrument controls --------------------------------------------------------------

def _pat(**kw) -> RelationalTriplePattern:
    return RelationalTriplePattern(match_wildcards=True, **kw)


def test_normaliser_control():
    """The normaliser maps each rule kind to the exact tuple and REFUSES every shape the
    `RRule` tuple cannot carry, instead of flattening it into a match."""
    assert _normalise(Rule(_pat(relation="a", object_type="doc"),
                           _pat(relation="viewer.0", object_type="doc"))) == (
        "doc", "a", "viewer.0", "computed")
    assert _normalise(Rule(_pat(relation="parent", object_type="doc"),
                           _pat(subject_predicate="viewer", relation="access.0",
                                object_type="doc"))) == (
        "doc", "parent", "access.0", "ttu", "viewer")
    bad = [
        Rule(_pat(relation="a", object_type="doc"), None),
        Rule(_pat(relation="a", object_type="doc", subject_type="user"),
             _pat(relation="v", object_type="doc")),
        Rule(_pat(relation="a", object_type="doc"),
             _pat(relation="v", object_type="doc", object_name="d1")),
        Rule(_pat(relation="a", object_type="doc"),
             _pat(relation="v", object_type="folder")),
        Rule(_pat(relation="a", object_type="doc", subject_predicate="x"),
             _pat(relation="v", object_type="doc")),
        Rule(_pat(relation="a", object_type="doc"),
             _pat(relation="v", object_type="doc", subject_predicate=...)),
        Rule(_pat(relation="a", object_type="doc"),
             _pat(relation="v", object_type="doc", object_match_wildcards=False)),
        Rule(RelationalTriplePattern(relation="a", object_type="doc"),
             _pat(relation="v", object_type="doc")),
    ]
    for r in bad:
        with pytest.raises(AssertionError):
            _normalise(r)


def test_ops_in_leaf_rules_mode_rejected():
    """rc 5: leaf-rules mode reads no store, so an `"ops"` stream is refused, not ignored."""
    _require_zcli()
    from tests.oracle import t as mk_tuple
    tup = mk_tuple("...", "user", "alice", "a", "doc", "d1")
    req = build_request(LEAF_RULE_WITNESSES["W2"], [], [], (), mode="leaf-rules",
                        ops=[("add", tup)])
    proc, req_path = runner.invoke_zcli(req, "leaf-rules-ops-test")
    runner.discard_request(req_path)
    assert proc.returncode == 5, (proc.returncode, proc.stderr)
    assert "leaf-rules" in proc.stderr


def _s11_twin(monkeypatch) -> None:
    """Python twin of `LeafRules.lean` sabotage S11 (`.take 1`): a closure leaf's subtree
    keeps only its FIRST rule. Applied ONCE per leaf (challenge X1): `_emit_leaf_expr`
    recurses through the module global, so a naive wrapper would truncate again at every
    nested `Union`; the depth guard passes nested calls straight through."""
    orig = boolean_mod._emit_leaf_expr
    depth = [0]

    def take1(expr, object_type, public_relation, leaf, out):
        if depth[0]:
            return orig(expr, object_type, public_relation, leaf, out)
        depth[0] += 1
        try:
            tmp: list = []
            orig(expr, object_type, public_relation, leaf, tmp)
        finally:
            depth[0] -= 1
        rules = [x for x in tmp if isinstance(x, Rule)]
        out.extend(x for x in tmp if not isinstance(x, Rule))
        out.extend(rules[:1])
    monkeypatch.setattr(boolean_mod, "_emit_leaf_expr", take1)


def _rule_offbyone(monkeypatch) -> None:
    """Leaf rule index `R.i` -> `R.(i+1)` in the RULE only (challenge X1): `boolean.py`'s own
    `_rewrite_rule` reference is patched, so `RewriteFilter` routing and the untainted half
    (`compiler.py` holds its own reference) are untouched."""
    orig = boolean_mod._rewrite_rule

    def bumped(expr, object_type, leaf):
        base, i = leaf.rsplit(".", 1)
        return orig(expr, object_type, f"{base}.{int(i) + 1}")
    monkeypatch.setattr(boolean_mod, "_rewrite_rule", bumped)


def test_python_side_sabotages_are_caught(monkeypatch):
    """PERMANENT sabotage of the Python side, asserting EXACTLY which sources go red.

    (a) S11 twin: only the merged-leaf witnesses go red; every corpus and fixture source
        stays green (the corpus is blind to merged leaves, which is why the witnesses
        exist), and `W3`'s TK132 diff vanishes because the dropped arm IS the TTU arm.
    (b) rule-only off-by-one: every source with a non-empty Python leaf half goes red, the
        TK132 four included, and no source with an empty one does.
    """
    baseline = {label: _python(label) for label in _SOURCES}
    with monkeypatch.context() as m:
        _s11_twin(m)
        red = {k for k, d in _sweep().items() if d}
    assert red == {"WIT:W2", "WIT:W6", "WIT:W3b", "WIT:W7",
                   "TK126:D", "TK126:D_nested", "TK126:SlXt"}, sorted(red)
    with monkeypatch.context() as m:
        _rule_offbyone(m)
        red = {k for k, d in _sweep().items() if d}
    assert red == {k for k, py in baseline.items() if py["leaf"]}, sorted(red)
    assert {k for k, d in _sweep().items() if d} == set(_TK132_EXPECTED)  # patch undone
