"""P22: THE INPUT THAT REACHES bulk_build.py's I14 CROSSABLE-MIDDLE LOOP.

-- CORRECTION APPENDED 2026-09-16, AFTER THE CORPUS WAS WIRED IN ------------------------

THIS PROBE IS CORRECT AND ITS TRANSCRIPT REPRODUCES FIRST-HAND. Its closing instruction --
"add this corpus to `tests/test_bulk_build.py::_CORPORA` so the sabotage cannot go green
again" -- WAS NOT SUFFICIENT, and the difference is the whole content of
`docs/p22-i14-corpus-masking-2026-09-16.md`.

The store this probe measures is the MINIMAL three-tuple shape. The corpus first wired into
`_CORPORA` carried four further tuples for coverage, and two of them MASK the mechanism: a
concrete `viewer(folder, _)` grant or a concrete `parent` edge lets the generic
bridged-in/out loop complete the `w_all -> middle -> w_any` crossing without the I14 loop,
so the sabotage went GREEN again with a corpus whose `crossable_shapes` was non-empty. The
per-tuple measurement is in that doc and in `_owc_star_ttu_tuples`'s own comment.

So: reaching the loop and PINNING the loop are different claims, and this probe establishes
only the first. What pins it is the corpus keeping the minimal shape, plus the structural
clause in `tests/test_bulk_build.py::_assert_r4bf_features` that pins the loop's product
(the `viewer(folder, f1)` middle and its two bridges) and mechanically refuses a corpus that
re-introduces masking.

  Run:  PYTHONPATH=. <env-python> formal/probes/bulk_i14_crossable_middle_2026-09-16.py

`P22` was filed 2026-09-06b as a GREEN SABOTAGE: deleting the I14 crossable-middle loop
at `src/zanzibar/graphindex/bulk_build.py` (the `crossable_shapes` loop) left every `build_index` caller
GREEN -- `tests/test_bulk_build.py`, `formal/conformance/test_conformance_bulk_state.py`
(bulk vs incremental over all 25 `GRAPH_FRAGMENT` corpora) and the validation matrix. A
loop no sabotage can reach is unverified code on the DEFAULT constructor, and the row
offered two honest outcomes: (1) find a corpus that reaches it and keep the sabotage as a
permanent test, or (2) prove it is dead code and delete it.

THIS FILE SETTLES IT AS OUTCOME 1. The candidate input was proposed by the 2026-09-15
adversarial audit (`docs/adversarial-audit-2026-09-15.md` sec 2) as an AGENT-PROBED claim
written only to the gitignored `.scratch/`; it is re-run FIRST-HAND here and this is its
tracked home. The transcript below is literal and was observed 2026-09-16.

WHAT IT MEASURES, in two parts:

  (A) SHIPPED. Build the same 3-tuple store twice through `connectedstore.build_index`,
      once `bulk=False` (incremental) and once `bulk=True` (the offline closure builder),
      and compare both against the independent oracle on a 3-query grid. The shipped tree
      must AGREE -- this part is the control, and a divergence here would be a live bug
      rather than the assurance gap `P22` is about.

  (B) SABOTAGE. Neuter the loop's only guard by monkeypatching
      `zanzibar.schema.SchemaInfo.crossable_shapes` to the empty set, rebuild with
      `bulk=True`, and re-ask the grid. If an answer now disagrees with the oracle, this
      corpus REACHES the loop and is exactly the missing pin.

WHY NO EXISTING CORPUS REACHES IT: every entry of `tests/test_bulk_build.py::_CORPORA`
has an empty `crossable_shapes`, because `src/zanzibar/schema/::
_reject_doubly_bridged_shapes` intersects only LITERAL `T:*#p` shapes, while a
star-tupleset THROUGH-shape (here `folder:* parent doc:d1` feeding `viewer from parent`)
makes the set non-empty on a schema the compiler admits. That is the gap the corpus never
crossed. (AGENT-READ as a mechanism; the reaching itself is CONFIRMED by part (B).)

THE SHAPE THAT DOES IT: the `owc_star_ttu` class -- an object-wildcard grant
(`u1 viewer folder:*` with `object_wildcard_shapes={('folder','viewer'),('doc','viewer')}`)
creating `w_all(folder,viewer)`, a bare-star tupleset parent (`folder:* parent doc:d1`)
carrying it into `doc.viewer`'s `or viewer from parent`, and a WITNESS tuple that mentions
`folder:f1` WITHOUT ever putting a `viewer` triple on it (`u1 editor folder:f1`). The
middle `w_all(folder,viewer) -> folder:f1#viewer -> w_any(folder,viewer)` therefore exists
only if the I14 loop creates it.

NOT CLAIMED HERE: anything about the INCREMENTAL path's I14 handling, which is separately
pinned, or about `TK69` (the admission divergence, a different I14 surface -- see
`formal/probes/i14_admission_divergence_2026-09-15.py`). Do not cite this probe for either.

-- THE RESULT ---------------------------------------------------------------------------

**THE LOOP IS LIVE CODE ON A REACHABLE INPUT, AND IT WAS PINNED BY NOTHING.** The shipped
tree is correct on this corpus (part A: bulk, incremental and oracle all agree), and with
the guard neutered the bulk build answers `viewer(u1, doc:d1) = False` against an oracle
`True` -- a MISSING GRANT, i.e. the deletion sabotage that has stayed green since
2026-09-06b now goes RED. So `P22` resolves as outcome 1: keep the loop, and add this
corpus to `tests/test_bulk_build.py::_CORPORA` so the sabotage cannot go green again.

Note which query moved: only the TTU leg (`doc:d1`) flips. The two controls -- the
object-wildcard leg (`folder:f1#viewer`) and the plain direct edge
(`folder:f1#editor`) -- stay green under sabotage, which is what makes this a
one-mechanism result rather than a broken instrument (`docs/sabotage-procedure.md`,
sec "Sweep the TEST MODULE with mutations": a mutation that reddens everything is not
evidence about the clause it targets).

-- TRANSCRIPT (literal, rc=0, 2026-09-16) -----------------------------------------------

  ok: q=('...', 'user', 'u1', 'viewer', 'doc', 'd1') inc=True bulk=True oracle=True
  ok: q=('...', 'user', 'u1', 'viewer', 'folder', 'f1') inc=True bulk=True oracle=True
  ok: q=('...', 'user', 'u1', 'editor', 'folder', 'f1') inc=True bulk=True oracle=True
  SHIPPED RESULT: no divergence (loop compensates?)
  SABOTAGE-RED: q=('...', 'user', 'u1', 'viewer', 'doc', 'd1') bulk_no_i14=False oracle=True
  sabotage-green: q=('...', 'user', 'u1', 'viewer', 'folder', 'f1') bulk_no_i14=True oracle=True
  sabotage-green: q=('...', 'user', 'u1', 'editor', 'folder', 'f1') bulk_no_i14=True oracle=True
  SABOTAGE RESULT: loop IS reached by this corpus (pin found)

(The 2026-09-15 agent run reported the same three lines from `.scratch/probe_bulk_i14.py`;
this transcript is the first-hand reproduction that `CLAUDE.md` sec Delegation requires
before the claim may be acted on.)
"""
from sqlmodel import Session, SQLModel, create_engine, select

from zanzibar.connectedstore import TupleSource, build_index, save_schema
from zanzibar.setengine.models import RelationTuple
from tests.oracle import Oracle, OracleTuple

SCHEMA = '''
type user

type group
  relations
    define member: [user, group#member]

type folder
  relations
    define parent: [folder, folder:*]
    define blocked: [user]
    define editor: [user, group#member]
    define viewer: [user, user:*, group#member] or viewer from parent
    define restricted: editor but not blocked

type doc
  relations
    define parent: [folder, folder:*]
    define blocked: [user]
    define editor: [user, group#member]
    define viewer: [user, user:*, group#member] or viewer from parent
    define restricted: editor but not blocked
'''

OBJ_WC = frozenset({('folder', 'viewer'), ('doc', 'viewer')})

TUPLES = [
    ('...', 'user', 'u1', 'editor', 'folder', 'f1'),   # witness: mentions f1, NOT via viewer
    ('...', 'user', 'u1', 'viewer', 'folder', '*'),    # object-wildcard grant -> w_all
    ('...', 'folder', '*', 'parent', 'doc', 'd1'),     # bare star tupleset parent
]

QUERIES = [
    ('...', 'user', 'u1', 'viewer', 'doc', 'd1'),      # the predicted divergence
    ('...', 'user', 'u1', 'viewer', 'folder', 'f1'),   # control: object-wildcard leg
    ('...', 'user', 'u1', 'editor', 'folder', 'f1'),   # control: plain direct
]


def seed(session, store_id):
    save_schema(session, store_id, SCHEMA, OBJ_WC)
    src = TupleSource(session, store_id)
    landed = []
    for raw in TUPLES:
        try:
            src.add(*raw)
            landed.append(raw)
        except ValueError as e:
            print(f'  ADMISSION REFUSED in {store_id}: {raw} -> {e}')
    session.commit()
    rows = session.exec(
        select(RelationTuple).where(RelationTuple.store_id == store_id).order_by(RelationTuple.id)).all()
    return [OracleTuple(r.subject_predicate, r.subject_type, r.subject_name,
                        r.relation, r.object_type, r.object_name) for r in rows]


def main():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        landed_inc = seed(s, 'src_inc')
        landed_blk = seed(s, 'src_blk')
        assert landed_inc == [OracleTuple(*t) for t in TUPLES], landed_inc
        assert landed_blk == [OracleTuple(*t) for t in TUPLES], landed_blk

        _, widx_inc, _ = build_index(s, 'src_inc', bulk=False)
        _, widx_blk, _ = build_index(s, 'src_blk', bulk=True)

        oracle = Oracle(SCHEMA, landed_inc)
        any_diff = False
        for q in QUERIES:
            a = widx_inc.check(*q)
            b = widx_blk.check(*q)
            c = oracle.check(*q)
            tag = 'DIVERGES' if not (a == b == c) else 'ok'
            if tag == 'DIVERGES':
                any_diff = True
            print(f'{tag}: q={q} inc={a} bulk={b} oracle={c}')
        print('SHIPPED RESULT:',
              'CONFIRMED divergence' if any_diff else 'no divergence (loop compensates?)')

        # --- P22 sabotage: does THIS corpus reach the I14 loop? --------------------
        # Neuter the loop's only guard (schema_info.crossable_shapes) and rebuild bulk.
        # If the answer flips vs oracle, the corpus REACHES the loop => it is the
        # missing pin P22 asks for (outcome 1).
        import zanzibar.schema as Z
        landed_sab = seed(s, 'src_sab')
        assert landed_sab == [OracleTuple(*t) for t in TUPLES], landed_sab
        orig_prop = Z.SchemaInfo.crossable_shapes
        Z.SchemaInfo.crossable_shapes = property(lambda self: frozenset())
        try:
            _, widx_sab, _ = build_index(s, 'src_sab', bulk=True)
        finally:
            Z.SchemaInfo.crossable_shapes = orig_prop
        sab_diff = False
        for q in QUERIES:
            b = widx_sab.check(*q)
            c = oracle.check(*q)
            tag = 'SABOTAGE-RED' if b != c else 'sabotage-green'
            if b != c:
                sab_diff = True
            print(f'{tag}: q={q} bulk_no_i14={b} oracle={c}')
        print('SABOTAGE RESULT:',
              'loop IS reached by this corpus (pin found)' if sab_diff
              else 'loop NOT reached even here (still green)')


if __name__ == '__main__':
    main()
