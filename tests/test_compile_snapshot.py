"""
Compile-output regression gate (spec §0 workflow step 6, P0 accept criterion).

Captures a canonical snapshot of the compiled ``RuleSet`` for every fixture schema
that the graph index currently accepts (i.e. the *pure-union* fixtures -- the boolean
ones still raise ``UnsupportedByGraphIndex`` and are skipped until the matrix flip).

The frozen invariant this guards (spec §3.1 / P2): **untainted relations must compile
byte-identically** after boolean support lands. Adding taint/plan-trees/leaf-renaming
must not perturb a single Filter or Rule of a schema that contains no boolean operator.

Snapshots live in ``tests/snapshots/compiled_ruleset/<fixture>.txt`` and are generated
on first run (P0). A drift is a P2 regression until proven an intentional, documented
change -- in which case delete the golden and regenerate with a deviations-log entry.
"""

from pathlib import Path

import pytest

from zanzibar_utils_v1 import parse_openfga_schema, UnsupportedByGraphIndex

SNAPSHOT_DIR = Path(__file__).parent / "snapshots" / "compiled_ruleset"
FGA_DIR = Path(__file__).parent / "fga_schemas"

ALL_FIXTURES = sorted(p.name for p in FGA_DIR.glob("*.fga"))


def _canonical_ruleset(rs) -> str:
    """Deterministic text form of a compiled RuleSet.

    ``rules_and_filters`` is an ordered list (compile order is a deterministic function
    of source order), and Filter/Rule are frozen dataclasses of plain scalars, so their
    ``repr`` is stable. The only non-determinism is the ``frozenset`` shapes in
    ``SchemaInfo`` -- sort those explicitly.
    """
    lines = ["# rules_and_filters (in compile order)"]
    lines += [repr(x) for x in rs.rules_and_filters]
    si = rs.schema_info
    lines.append("# schema_info")
    if si is None:
        lines.append("schema_info=None")
    else:
        lines.append(f"subject_wildcard_shapes={sorted(si.subject_wildcard_shapes)!r}")
        lines.append(f"object_wildcard_shapes={sorted(si.object_wildcard_shapes)!r}")
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_compiled_ruleset_matches_snapshot(fixture, load_fga_schema):
    schema = load_fga_schema(fixture)
    try:
        rs = parse_openfga_schema(schema)
    except UnsupportedByGraphIndex:
        pytest.skip(f"{fixture} contains boolean operators; graph index refuses it (pre-flip)")

    canonical = _canonical_ruleset(rs)
    golden_path = SNAPSHOT_DIR / f"{fixture}.txt"

    if not golden_path.exists():
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(canonical, encoding="utf-8")
        pytest.skip(f"generated baseline snapshot for {fixture}")

    expected = golden_path.read_text(encoding="utf-8")
    assert canonical == expected, (
        f"compiled RuleSet for {fixture} drifted from its P0 snapshot. "
        f"If this is intentional, delete {golden_path.name} and document it in "
        f"docs/spec-deviations.md."
    )
