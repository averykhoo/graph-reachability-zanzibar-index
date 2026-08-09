"""ZT-P4-6 — the query grid must not be read off the ENCODER's parser.

`formal/conformance/encode.py` feeds the LEAN corner of every differential, and
it parses the DSL with `tests/oracle.py::parse_schema_ast`. Until 2026-07-27
`grid.py` imported the SAME function to decide which `(type, relation)` targets
to query. That coupling has a specific, nasty failure mode: a relation the
oracle's parser mis-reads is mis-encoded into the Lean corner AND simultaneously
dropped from (or distorted in) the query grid — so the harness deletes the very
query that would expose its own misparse. The "three genuinely independent
corners" phrasing was therefore 2-of-3 at the schema-READING layer.

`grid.py` now derives declared targets from `zanzibar_utils_v1.parse_schema_ast`
(the production parser; step 1 of `parse_openfga_schema`). This module is the
anti-regression pin for that, in three parts:

  1. the two parsers really ARE different code — demonstrated on a live input
     they disagree about (a duplicate `define`);
  2. on every corpus and every generated schema the harness actually runs, they
     agree on the declared-key set — so the swap changed no grid (verified
     byte-identical when it landed) and any FUTURE divergence surfaces here as a
     named finding rather than as a silently shrunken grid;
  3. `grid.grid` is genuinely wired to the production parser (patching the
     oracle's parser to garbage must not change a grid).

What this does NOT claim: independence of the two EVALUATORS is a separate
property (that is what `test_conformance_spec.py` compares). And `encode.py`
still reads schemas through the oracle's parser — that residual is stated in
`CORRESPONDENCE.md` §1.
"""

from __future__ import annotations

import pytest

from tests.oracle import parse_schema_ast as oracle_parse, t as mk_tuple
from zanzibar_utils_v1 import parse_schema_ast as prod_parse

from formal.conformance import corpus as C
from formal.conformance import grid as grid_mod
from formal.conformance.grid import grid


def _all_corpora():
    """Every (label, schema_text, tuples) the shared grid is ever built over."""
    out = []
    for dname in ("SCHEMAS", "MULTI_STRATUM_SCHEMAS", "TTU_USERSET_SCHEMAS",
                  "SELF_REFERENTIAL_SCHEMAS"):
        d = getattr(C, dname, None) or {}
        for k, (schema_text, tuples, _ow) in d.items():
            out.append((f"{dname}:{k}", schema_text, tuples))
    return out


# Measured 2026-07-27: there were then 28 curated corpora across the four dicts;
# RE-MEASURED 2026-07-29, **33** as of that date (SCHEMAS 24 + TTU_USERSET 6 +
# SELF_REFERENTIAL 2 + MULTI_STRATUM 1); RE-MEASURED 2026-08-09 after the
# `rewriteClosure` dedup leg added two reconvergent corpora, **35** as of that
# date (SCHEMAS 26 + 6 + 2 + 1). A floor, not an equality — new corpora are
# welcome, a collapse is not — so the constant deliberately lags the
# measurement, and the live figure belongs in `FINAL_REVIEW.md`'s generated
# block rather than here.
_MIN_CORPORA = 28


def test_the_two_parsers_are_really_different_code():
    """A live input the two parsers DISAGREE about, so this file is not pinning
    an alias. `zanzibar_utils_v1` REJECTS a duplicate `define`; `tests/oracle.py`
    silently keeps the last one. (`encode.py`'s docstring is honest about the
    shared-parser coupling; this is the demonstration.)"""
    dup = (
        "type user\n"
        "type doc\n"
        "  define viewer: [user]\n"
        "  define viewer: [user, user:*]\n"
    )
    # oracle: last-wins, no error
    oast = oracle_parse(dup)
    assert ("doc", "viewer") in oast, "oracle stopped accepting a duplicate define"

    # production: loud rejection
    with pytest.raises(Exception) as exc:
        prod_parse(dup)
    assert "viewer" in str(exc.value) or "duplicate" in str(exc.value).lower(), (
        f"production parser rejected the duplicate define, but not with a "
        f"message naming it: {exc.value!r}")


def test_grid_uses_the_production_parser_not_the_oracle():
    """Sabotage the ORACLE's parser; the grid must be unmoved. This fails loudly
    if `grid.py` is ever re-pointed at `tests.oracle.parse_schema_ast`."""
    schema_text, tuples, _ow = C.SCHEMAS["boolean_exclusion"]
    baseline = grid(schema_text, tuples)
    assert baseline[1], "grid produced no targets — the pin below would be vacuous"

    import tests.oracle as oracle_mod
    saved = oracle_mod.parse_schema_ast
    try:
        oracle_mod.parse_schema_ast = lambda _text: {("doc", "SABOTAGE"): None}
        after = grid(schema_text, tuples)
    finally:
        oracle_mod.parse_schema_ast = saved

    assert after == baseline, (
        "the shared query grid MOVED when the oracle's parser was replaced — "
        "grid.py is reading the encoder's parser again (ZT-P4-6 regression)")
    assert grid_mod.parse_schema_ast is prod_parse, (
        "grid.py's `parse_schema_ast` is not zanzibar_utils_v1's")


def test_declared_keys_agree_on_every_corpus():
    """Both parsers see the same declared `(type, relation)` set on every corpus
    the harness runs. A failure here is a FINDING, not a nuisance: it means the
    Lean corner is being fed a schema the production side reads differently."""
    corpora = _all_corpora()
    assert len(corpora) >= _MIN_CORPORA, (
        f"ANTI-VACUITY: only {len(corpora)} corpora enumerated (floor "
        f"{_MIN_CORPORA}) — the comparison below would be near-empty")

    disagreements = []
    for label, schema_text, _tuples in corpora:
        o = set(oracle_parse(schema_text))
        p = set(prod_parse(schema_text))
        if o != p:
            disagreements.append((label, sorted(o - p), sorted(p - o)))
    assert not disagreements, (
        "PARSER DIVERGENCE on a live corpus (oracle-only / production-only):\n"
        + "\n".join(f"  {l}: only-oracle={a} only-production={b}"
                    for l, a, b in disagreements))


def test_declared_keys_agree_on_every_generated_schema():
    """Same, over the 40 seeded GENERATED schemas — the pool deliberately outside
    the curated corpora, where a parser divergence is most likely to hide."""
    from formal.conformance.test_conformance_generated import _case, SEEDS

    assert len(SEEDS) >= 10, "ANTI-VACUITY: generated seed pool collapsed"
    disagreements = []
    n_declared = 0
    for seed in SEEDS:
        schema_text, pool, _store_ops = _case(seed)
        o = set(oracle_parse(schema_text))
        p = set(prod_parse(schema_text))
        n_declared += len(p)
        if o != p:
            disagreements.append((seed, sorted(o - p), sorted(p - o)))
        # the grid must be buildable from the production parse alone
        subjects, targets = grid(schema_text, [mk_tuple(*op) for op in pool])
        assert subjects and targets, (
            f"[generated seed={seed}] grid collapsed under the production parser")
    assert n_declared > 0, "ANTI-VACUITY: no declared relations across all seeds"
    assert not disagreements, (
        "PARSER DIVERGENCE on a generated schema (oracle-only / production-only):\n"
        + "\n".join(f"  seed={s}: only-oracle={a} only-production={b}"
                    for s, a, b in disagreements))
