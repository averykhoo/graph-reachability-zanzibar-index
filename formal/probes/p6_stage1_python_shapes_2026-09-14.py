"""`P6` stage 1 (2026-09-14h) — what the SHIPPED Python enumerates at the two `W4Witness`
through-shape schemas, and whether it compiles them.

WHY THIS EXISTS. Stage 1 re-points `FullScope.lean::W4Fragment.wsBare` at pass 1
(`ReconcileStars.lean::declaredWildcardShapes`) instead of the corrected two-pass
`::wildcardShapes`. The load-bearing justification is that a full-list `wsBare` is FALSE on
a schema the implementation ADMITS -- not merely on one it refuses. That distinction decides
the whole design: if every non-bare through-shape schema were refused by Python, `wsBare`
could have kept the full list and the split would have been unnecessary. So it is measured
here against the shipped compiler rather than argued from the Lean side.

RUN: PYTHONPATH=. python formal/probes/p6_stage1_python_shapes_2026-09-14.py

VERBATIM OUTPUT, 2026-09-14 (rc=0):

    SxThruDerived subject_wildcard_shapes = [('folder', '...'), ('folder', 'viewer')]
       compile: REFUSED UnsupportedByGraphIndex: relation doc#viewer: star tupleset [folder:*] on 'parent' derives the wildcard userset sha
    SxThruPlain subject_wildcard_shapes = [('folder', '...'), ('folder', 'viewer')]
       compile: ADMITTED

WHAT IT ESTABLISHES.

 1. **The corrected Lean enumeration matches the shipped one, shape for shape.** At
    `SxThruDerived` the model now gives `declaredWildcardShapes = [("folder", BARE)]` and
    `throughShapes = [("folder", "viewer")]`, i.e. the same two shapes Python returns
    (`'...'` IS `BARE`). Before the 2026-09-14h correction the model returned only the
    first.

 2. ★ **`SxThruPlain` is ADMITTED and still carries the non-bare shape `('folder',
    'viewer')`.** So "every shape in `wildcardShapes S` is `BARE`" is false at a schema
    the graph index compiles and runs -- the full-list `wsBare` would have SHRUNK
    `W4Fragment`, and with it the scope of every headline theorem. This is the shipped-code
    form of `FullScope.lean::sxThruDerived_wsBare_over_full_list_fails`.

 3. `SxThruDerived` is REFUSED by `zanzibar_utils_v1.py::_reject_object_wildcard_scope`,
    which is consistent with `FullScope.lean::W4Witness.sxThruDerived_not_admitted` and with
    that schema's docstring. ⚠ Note the asymmetry this creates and do not misread it: the
    refusal is about the through-shape being DERIVED, not about it being non-bare, which is
    exactly why (2) is the load-bearing measurement and (3) is only a consistency check.

 CONTROL. The two schemas differ on ONE axis -- `folder#viewer` is `[user] but not banned`
 in the first and `[user]` in the second -- and the shape sets come back IDENTICAL. That is
 what attributes the compile-time refusal to the taint and the non-bare shape to the star
 tupleset, rather than letting one explain the other.
"""
from zanzibar_utils_v1 import (
    parse_schema_ast, parse_openfga_schema, derive_schema_info,
    UnsupportedByGraphIndex,
)

SX_THRU_DERIVED = """
type user
type folder
  define banned: [user]
  define viewer: [user] but not banned
type doc
  define parent: [folder, folder:*]
  define viewer: viewer from parent
"""

SX_THRU_PLAIN = """
type user
type folder
  define banned: [user]
  define viewer: [user]
type doc
  define parent: [folder, folder:*]
  define viewer: viewer from parent
"""

for name, dsl in [("SxThruDerived", SX_THRU_DERIVED), ("SxThruPlain", SX_THRU_PLAIN)]:
    info = derive_schema_info(parse_schema_ast(dsl))
    print(name, "subject_wildcard_shapes =", sorted(info.subject_wildcard_shapes))
    try:
        parse_openfga_schema(dsl)
        print("   compile:", "ADMITTED")
    except UnsupportedByGraphIndex as e:
        print("   compile: REFUSED UnsupportedByGraphIndex:", str(e)[:90])
