"""`P6` (2026-09-14i) — the TWO REPRESENTATION DIVERGENCES, measured against the SHIPPED
Python at a schema the compiler admits.

WHY THIS EXISTS. Stage 1 (2026-09-14h) landed `ReconcileStars.lean::wildcardShapes` as
`declaredWildcardShapes ++ (throughShapes).filter (not already declared)`, and recorded two
deliberate divergences from `zanzibar_utils_v1.py::derive_schema_info`, whose result is a
`frozenset` rendered `sorted(...)` at `index_v4/processor.py::DeltaProcessor.__init__:237`:

  (a) MULTIPLICITY — a shape produced twice appears twice in Lean, once in Python;
  (b) ORDER        — Lean is pass-1-then-pass-2, Python is sorted.

Both were documented and UNCHECKED. Nothing established that a duplicate is even reachable
on a schema the parser admits, and nothing checked either divergence against a consumer. A
divergence no admissible schema exhibits is not a divergence, it is a docstring.

⚠ WHAT THIS PROBE DELIBERATELY DOES NOT DO: re-derive Lean's enumeration in Python. That
would be a THIRD transcription of `derive_schema_info`'s loops, and two transcriptions that
could not see each other is precisely the defect stage 1 existed to repair
(`TtuStarWide.lean::mem_throughShapes_iff_isStarTuplesetThrough`). The Lean side of this
comparison is pinned by the kernel at
`ReconcileStars.lean::ShapeRepresentationWitness.wildcardShapes_diverges` (`by decide`); this
file measures the PYTHON side of the same witness and nothing else. Read the two together.

RUN: PYTHONPATH=. python formal/probes/p6_shape_representation_2026-09-14.py

VERBATIM OUTPUT, 2026-09-14i (rc=0):

    Sdup: compile ADMITTED
    Sdup: shipped sorted(frozenset) = [('folder', '...'), ('folder', 'viewer'), ('user', '...')]  len=3
    Sdup: Lean pins (ReconcileStars ShapeRepresentationWitness) = [('user', '...'), ('folder', '...'), ('folder', '...'), ('folder', 'viewer'), ('folder', 'viewer')]  len=5
    Sdup:   MULTIPLICITY divergence (len differs): True
    Sdup:   ORDER divergence (first entry differs): True
    Sdup:   SAME SET -- must be True or the enumerations disagree on CONTENT: True
    CONTROL Sctl: compile ADMITTED
    CONTROL Sctl: shipped sorted(frozenset) = [('folder', '...'), ('folder', 'viewer')]  len=2
    CONTROL Sctl: Lean pins (ReconcileStars ShapeRepresentationWitness) = [('folder', '...'), ('folder', 'viewer')]  len=2
    CONTROL Sctl:   MULTIPLICITY divergence (len differs): False
    CONTROL Sctl:   ORDER divergence (first entry differs): False
    CONTROL Sctl:   SAME SET -- must be True or the enumerations disagree on CONTENT: True

WHAT IT ESTABLISHES.

 1. ★ **Both divergences are REACHABLE on a schema the graph index ADMITS.** `Sdup` compiles
    (no `UnsupportedByGraphIndex`), and at it Python returns 3 shapes where the Lean model
    enumerates 5, starting with a different one. So the docstring's two caveats describe live
    behaviour, not a hypothetical.

 2. **The CONTENT agrees — it is only the representation that differs.** `set(lean) ==
    set(shipped)` at both schemas. That is the claim the correspondence actually needs, and it
    is what makes the divergence affordable: every consumer on both sides reads these lists
    through membership (census, 2026-09-14i; the one exception is a `by decide` structural
    equality over CLOSED terms, which can only fail loudly).

 3. **CONTROL `Sctl`** — one parent, no wildcard on `folder#viewer`, so neither pass can
    duplicate. There the two representations agree entry for entry. Without it, a `True` at
    (1) could be an artefact of comparing a list with a set rather than of the duplication.

⚠ The Lean literals below are TRANSCRIBED from the `by decide` theorems named above; the
theorems are the authority. If they are edited, this file is stale and the `SAME SET` line is
the check that notices.
"""

from zanzibar_utils_v1 import (
    derive_schema_info,
    parse_schema_ast,
    parse_openfga_schema,
    UnsupportedByGraphIndex,
)

# The Lean twin is `ReconcileStars.lean::ShapeRepresentationWitness.Sdup`, definition for
# definition:
#   folder#viewer  -> .direct [("user", BARE, false), ("user", BARE, true)]
#   doc#parent     -> .direct [("folder", BARE, false), ("folder", BARE, true)]
#   doc#owner      -> .direct [("folder", BARE, false), ("folder", BARE, true)]
#   doc#access     -> .union (.ttu "viewer" "parent") (.ttu "viewer" "owner")
S_DUP = """
type user
type folder
  define viewer: [user, user:*]
type doc
  define parent: [folder, folder:*]
  define owner: [folder, folder:*]
  define access: viewer from parent or viewer from owner
"""

# CONTROL: one parent, and no wildcard on `folder#viewer`. Neither pass can emit a shape
# twice, so the two representations must agree entry for entry.
S_CTL = """
type user
type folder
  define viewer: [user]
type doc
  define parent: [folder, folder:*]
  define access: viewer from parent
"""

# Transcribed from the `by decide` theorems in
# `ReconcileStars.lean::ShapeRepresentationWitness` (`BARE` is Python's `'...'`).
LEAN_PINNED = {
    "Sdup": [
        ("user", "..."),
        ("folder", "..."),
        ("folder", "..."),
        ("folder", "viewer"),
        ("folder", "viewer"),
    ],
    "CONTROL Sctl": [("folder", "..."), ("folder", "viewer")],
}

for name, dsl in [("Sdup", S_DUP), ("CONTROL Sctl", S_CTL)]:
    try:
        parse_openfga_schema(dsl)
        print(f"{name}: compile ADMITTED")
    except UnsupportedByGraphIndex as e:
        print(f"{name}: compile REFUSED UnsupportedByGraphIndex: {str(e)[:90]}")

    shipped = sorted(derive_schema_info(parse_schema_ast(dsl)).subject_wildcard_shapes)
    lean = LEAN_PINNED[name]
    print(f"{name}: shipped sorted(frozenset) = {shipped}  len={len(shipped)}")
    print(
        f"{name}: Lean pins (ReconcileStars ShapeRepresentationWitness) = {lean}"
        f"  len={len(lean)}"
    )
    print(f"{name}:   MULTIPLICITY divergence (len differs): {len(lean) != len(shipped)}")
    print(
        f"{name}:   ORDER divergence (first entry differs): "
        f"{bool(lean) and bool(shipped) and lean[0] != shipped[0]}"
    )
    print(
        f"{name}:   SAME SET -- must be True or the enumerations disagree on CONTENT: "
        f"{set(lean) == set(shipped)}"
    )
