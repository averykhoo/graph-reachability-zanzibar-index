"""P6 PART (iv) -- DOES THE SHIPPED PYTHON BRIDGE ON THE RULE-ROUTED WRITE PATH? (2026-09-15)

WHY THIS EXISTS, and why it is the FIRST thing to measure about step 4'.

The 2026-09-15 scouting sweep (`docs/p6-step4prime-scout-2026-09-15.md`) closed with an
UNVERIFIED blocker that outranks the rest of the cost analysis:

    "UNVERIFIED: Python-side parity.  Nobody checked whether `src/zanzibar/graphindex/wildcard.py`'s
     rule-routed write path bridges.  Per CLAUDE.md the Lean must track the shipped Python,
     and R1's entire justification is that it should.  If the Python does NOT bridge there,
     R1 is chasing a model change the code does not have, and the honest move is a
     `CORRESPONDENCE.md` section 7 gap entry instead."

That is the whole route hanging on one unmeasured fact, so measure it.  `CLAUDE.md` section
"Who decides" makes the direction explicit: the PRIMARY consideration is equivalence, and if
the two disagree the default assumption is that the PYTHON is right and the model is wrong.
So this probe asks the shipped index, not the Lean.

THE QUESTION, precisely.  `GraphIndex/RulesWrite.lean::GraphState.writeRules` -- the step of
`RulesComplete.lean::ReachedByRulesAdmitted`, and the fold the W4 shadow is built with -- is
a bridge-free `writeDirect` fold.  Its shipped counterpart is the rule-routed write path:

    ruleset.apply(triple)  ->  WildcardIndex.add_tuple(...)   (per derived triple)

which is exactly what `tests/test_matrix.py::GraphBackend._derived` does.  If THAT path
materialises the in-bridge `folder:f1#viewer -> w_any(folder,viewer)`, then the Lean fold is
bridge-free where the shipped code is not, the model describes something the system does not
do, and step 4' is a MODEL REPAIR (which is what R1 assumes).  If it does not bridge, step 4'
would be changing the model away from the code, and the honest artifact is a gap entry.

RUN (from the repo root):
    PYTHONPATH=. C:/Users/user/anaconda3/envs/graph-reachability-zanzibar-index/python.exe \
        formal/probes/p6_partiv_python_bridge_parity_2026-09-15.py

THE VERDICT: **YES -- THE SHIPPED PYTHON BRIDGES, AND THE LEAN FOLD DOES NOT.**  So the
model describes something the system does not do, and step 4' is a MODEL REPAIR.  This is
the `CLAUDE.md` section "Who decides" case in its cleanest form: the two disagree, and the
Python is right.

ARM 1, the star-tupleset store, on the rule-routed path `ruleset.apply -> add_tuple`:
the edge list contains

    (('viewer', 'folder', 'f1', ''), ('viewer', 'folder', '*', 'any'), 1, 1)

which IS `folder:f1#viewer -> w_any(folder,viewer)` -- byte for byte the in-bridge that
`p6_partiv_step3_rulerouted_2026-09-15.lean` line (8) had to add BY HAND with
`UsStarWrite.lean::GraphState.ensureInBridges` to make `GraphModel.check` agree with `sem`.
The shipped index materialises it unasked, answers `check = True`, and the independent
oracle agrees.  `bridged_in_shapes = {('folder','viewer')}` -- the shape is declared, so the
bridge is schematic, not incidental.

ARM 2, CONTROL b, the concrete parent: `subject_wildcard_shapes` and `bridged_in_shapes` are
both EMPTY, no `w_any` edge is created, and the query still answers correctly.  So ARM 1's
bridge is attributable to the STAR tupleset parent and not to the index bridging everything
unconditionally.

CONSEQUENCE FOR THE ROUTE, recorded so it is not re-litigated.  The scouting doc's blocker 3
proposed re-pricing a rival to R1 -- "write a `FoldAdmitsBridged -> FoldAdmits` transfer
lemma and keep sigma0 unbridged", noting it would be cheaper and would leave four
currently-true lemmas true.  **That rival is now REFUTED as a direction, not on cost but on
purpose:** it preserves a bridge-free shadow, i.e. it keeps the model faithful to an
algorithm the shipped code does not run.  `CLAUDE.md`: "A proof that describes something
other than the shipped code is a proof of nothing."  Cheapness does not buy that back.  R1
(bridge the shadow) is the direction that closes the gap.

VERBATIM OUTPUT, 2026-09-15 (rc=0):

    ARM 1 -- STAR tupleset parent
      compile: ADMITTED
      subject_wildcard_shapes = frozenset({('folder', 'viewer'), ('folder', '...')})
      bridged_in_shapes       = frozenset({('folder', 'viewer')})
      ** GRAPH INDEX check(user:u in doc:d1#access) = True
      ** ORACLE                                     = True
      ** AGREE                                      = True
      edges (7 distinct rows):
        (('...', 'folder', '*', 'any'), ('parent', 'doc', 'd1', ''), 1, 1)
        (('...', 'user', 'u', ''), ('access', 'doc', 'd1', ''), 0, 1)
        (('...', 'user', 'u', ''), ('viewer', 'folder', '*', 'any'), 0, 1)
        (('...', 'user', 'u', ''), ('viewer', 'folder', 'f1', ''), 1, 1)
        (('viewer', 'folder', '*', 'any'), ('access', 'doc', 'd1', ''), 1, 1)
        (('viewer', 'folder', 'f1', ''), ('access', 'doc', 'd1', ''), 0, 1)
        (('viewer', 'folder', 'f1', ''), ('viewer', 'folder', '*', 'any'), 1, 1)   <-- THE IN-BRIDGE
      ** an in-bridge / w_any edge is present = True

    ARM 2 -- CONTROL b: CONCRETE tupleset parent
      compile: ADMITTED
      subject_wildcard_shapes = frozenset()
      bridged_in_shapes       = frozenset()
      ** GRAPH INDEX check(user:u in doc:d1#access) = True
      ** ORACLE                                     = True
      ** AGREE                                      = True
      edges (4 distinct rows):
        (('...', 'folder', 'f1', ''), ('parent', 'doc', 'd1', ''), 1, 1)
        (('...', 'user', 'u', ''), ('access', 'doc', 'd1', ''), 0, 1)
        (('...', 'user', 'u', ''), ('viewer', 'folder', 'f1', ''), 1, 1)
        (('viewer', 'folder', 'f1', ''), ('access', 'doc', 'd1', ''), 1, 1)
      ** an in-bridge / w_any edge is present = False

⚠ INSTRUMENT LIMIT.  The bridge-presence line is a substring test over the printed edge
rows, not a structural query -- it is a convenience, and the seven-row edge list is printed
in full precisely so the reader does not have to trust it.  Read the list.

CONTROLS, and what each rules out:
  * CONTROL b (concrete tupleset parent, the `SwTn` analogue) -- the shape today's NARROW
    fragment already covers.  Both the query answer and the bridge presence are reported for
    it, so a "Python bridges" result at the star parent is attributable to the STAR parent
    rather than to the index bridging every shape unconditionally.
  * ORACLE + SET ENGINE agreement -- `tests/oracle.py` imports nothing from either backend
    and parses the DSL itself.  Without it, "the graph index answers True" would be an
    unanchored claim about one backend rather than a statement about the SEMANTICS.  This is
    the repo's own referee (`CLAUDE.md`: the oracle is the referee for both).
  * NON-VACUITY -- the schema must be ADMITTED by `parse_openfga_schema` and the through
    shape must actually be declared.  A refused schema would make every answer below vacuous.
"""
import sys

from zanzibar.schema import parse_openfga_schema, UnsupportedByGraphIndex
from zanzibar.graphindex.invariants import snapshot_rows
from zanzibar.schema import RelationalTriple, Entity

sys.path.insert(0, 'tests')
from wildcard_helpers import make_wildcard_index          # noqa: E402
import oracle as oracle_mod                               # noqa: E402

# `SwT`: doc#parent carries the BARE wildcard restriction [folder:*] -- the WILDCARD FORM
# ONLY, which is why a concrete parent is not store-valid there (measured in
# `formal/probes/p6_partiv_stepC_diag_2026-09-15.lean`).
SCHEMA_STAR = """
type user
type folder
  define viewer: [user]
type doc
  define parent: [folder:*]
  define access: viewer from parent
"""

# `SwTn`: the one-restriction delta -- a CONCRETE folder parent.  Today's narrow fragment.
SCHEMA_CONC = """
type user
type folder
  define viewer: [user]
type doc
  define parent: [folder]
  define access: viewer from parent
"""

STAR_STORE = [
    ('...', 'user', 'u', 'viewer', 'folder', 'f1'),
    ('...', 'folder', '*', 'parent', 'doc', 'd1'),
]
CONC_STORE = [
    ('...', 'user', 'u', 'viewer', 'folder', 'f1'),
    ('...', 'folder', 'f1', 'parent', 'doc', 'd1'),
]

QUERY = ('...', 'user', 'u', 'access', 'doc', 'd1')


def _norm(sp):
    return Ellipsis if sp == '...' else sp


def run(label, schema, store):
    print("=" * 78)
    print("%s" % label)
    print("=" * 78)
    try:
        rs = parse_openfga_schema(schema)
    except UnsupportedByGraphIndex as e:
        print("  compile: REFUSED %s -- every number below would be vacuous" % e)
        return
    print("  compile: ADMITTED   (NON-VACUITY control)")
    print("  subject_wildcard_shapes = %r" % (rs.schema_info.subject_wildcard_shapes,))
    print("  bridged_in_shapes       = %r" % (rs.schema_info.bridged_in_shapes,))

    session, widx = make_wildcard_index(rs.schema_info, store_id='p')
    for raw in store:
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3],
                                  Entity(raw[4], raw[5]), _norm(raw[0]))
        # THE RULE-ROUTED WRITE PATH -- the shipped analogue of Lean's `writeRules` fold.
        for d in rs.apply(triple):
            widx.add_tuple(_norm(d.subject_predicate), d.subject.type, d.subject.name,
                           d.relation, d.object.type, d.object.name)
    session.commit()

    got = widx.check(*(_norm(QUERY[0]),) + QUERY[1:])
    print("")
    print("  ** GRAPH INDEX check(user:u in doc:d1#access) = %s" % got)

    # The REFEREE: an independent oracle that imports neither backend.
    otuples = [oracle_mod.t(*raw) for raw in store]
    orc = oracle_mod.check_oracle(schema, otuples, *QUERY)
    print("  ** ORACLE                                     = %s" % orc)
    print("  ** AGREE                                      = %s" % (got == orc))

    nodes, edges = snapshot_rows(session, 'p')
    print("")
    print("  edges (%d distinct rows):" % len(edges))
    bridge_present = False
    for row in sorted(map(str, edges)):
        print("    %s" % row)
        if 'w_any' in row or 'wAny' in row or "'*'" in row:
            bridge_present = True
    print("")
    print("  ** an in-bridge / w_any edge is present = %s" % bridge_present)
    session.close()


def main():
    print("P6 PART (iv) -- PYTHON BRIDGE PARITY ON THE RULE-ROUTED WRITE PATH")
    print("2026-09-15.  Question: does the SHIPPED index materialise the in-bridge that")
    print("Lean's `RulesWrite.lean::GraphState.writeRules` fold does NOT?")
    print("")
    run("ARM 1 -- STAR tupleset parent (the store part (iv) exists to admit)",
        SCHEMA_STAR, STAR_STORE)
    print("")
    run("ARM 2 -- CONTROL b: CONCRETE tupleset parent (today's narrow fragment)",
        SCHEMA_CONC, CONC_STORE)
    return 0


if __name__ == '__main__':
    sys.exit(main())
