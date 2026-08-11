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

import os
from pathlib import Path

import pytest

from zanzibar_utils_v1 import parse_openfga_schema, UnsupportedByGraphIndex

SNAPSHOT_DIR = Path(__file__).parent / "snapshots" / "compiled_ruleset"
FGA_DIR = Path(__file__).parent / "fga_schemas"

ALL_FIXTURES = sorted(p.name for p in FGA_DIR.glob("*.fga"))

# ANTI-VACUITY FLOOR. `ALL_FIXTURES` is a glob, and an empty parametrize list is
# reported by pytest as `1 skipped`, rc 0 -- so renaming or moving `fga_schemas/`
# would silently retire this entire byte-identity gate while the suite stayed
# green. Raise this number when fixtures are added; never lower it to fix a red.
MIN_FIXTURES = 15
assert len(ALL_FIXTURES) >= MIN_FIXTURES, (
    f"only {len(ALL_FIXTURES)} .fga fixtures found in {FGA_DIR} (expected at "
    f"least {MIN_FIXTURES}) -- the compiled-RuleSet snapshot gate would run on "
    f"almost nothing")

#: Regenerating a golden must be a DELIBERATE act. See the note in the test.
_UPDATE = os.environ.get("ZANZIBAR_UPDATE_SNAPSHOTS") == "1"


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
    golden_path = SNAPSHOT_DIR / f"{fixture}.txt"

    try:
        rs = parse_openfga_schema(schema)
    except UnsupportedByGraphIndex:
        # A golden on disk is proof this fixture compiled at snapshot time, so a
        # refusal NOW is a scope regression, not a pre-flip skip. Skipping here
        # would retire the golden silently -- exactly the direction this gate
        # exists to catch.
        if golden_path.exists():
            raise
        pytest.skip(f"{fixture} contains boolean operators; graph index refuses it (pre-flip)")

    canonical = _canonical_ruleset(rs)

    if not golden_path.exists():
        # A missing golden used to be silently WRITTEN and the test skipped, so
        # `rm -rf tests/snapshots/compiled_ruleset/` re-baselined the frozen P2
        # invariant against whatever the code happened to do that day -- 11 skips,
        # rc 0, no signal. Regeneration is now an explicit opt-in.
        if not _UPDATE:
            pytest.fail(
                f"no golden snapshot for {fixture}. This gate freezes untainted "
                f"compilation byte-for-byte, so a missing golden means the "
                f"baseline was deleted, not that there is nothing to check. "
                f"Regenerate deliberately with ZANZIBAR_UPDATE_SNAPSHOTS=1 and "
                f"document the change in docs/spec-deviations.md.")
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(canonical, encoding="utf-8")
        pytest.skip(f"generated baseline snapshot for {fixture} (opt-in regeneration)")

    expected = golden_path.read_text(encoding="utf-8")
    assert canonical == expected, (
        f"compiled RuleSet for {fixture} drifted from its P0 snapshot. "
        f"If this is intentional, delete {golden_path.name} and document it in "
        f"docs/spec-deviations.md."
    )
