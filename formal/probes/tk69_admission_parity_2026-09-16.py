"""TK69: ADMISSION PARITY between the graph index and the set engine -- BOTH families.

  Run:  PYTHONPATH=. <env-python> formal/probes/tk69_admission_parity_2026-09-16.py

`TK69` was CONFIRMED 2026-09-15d as an admission-contract divergence: a write that closes
a userset cycle is REFUSED by the graph index and ACCEPTED by both `SetOps` set-engine
backends, so the two backends hold different data from the same write sequence. The
tracked evidence for the audited case is
`formal/probes/i14_admission_divergence_2026-09-15.py`.

THIS PROBE ADDS WHAT THAT ONE DID NOT MEASURE: the same four writes in a DIFFERENT ORDER
expose a SECOND, independent divergence family, and the two families need opposite fixes.
It is the pre/post instrument for the `TK69` fix.

  F1  order A,B,C,D -- the audited case. The last write D closes the userset cycle. The
      graph refuses it; both set backends accept it. The set engine cannot see the
      crossing because its flow-graph nodes exist per incident EDGE
      (`setengine/engine.py::SetEngine._shape_node_ref`, "Added on the first incident
      edge") while the graph's crossing middles exist per ENTITY
      (`index_v4/wildcard.py::WildcardIndex._ensure_entity_middles`).

  F2  order B,C,D,A -- the DETONATION. With no `folder` entity yet, the graph ACCEPTS the
      cycle-closing write D, and then refuses A = `user:u1 editor folder:f1` -- an
      ordinary grant naming no wildcard, no userset and not the crossable relation --
      because minting that entity's I14 middle emits the bridge edge that closes the
      now-latent cycle. This is exactly the failure
      `index_v4/wildcard.py::WildcardIndex._reject_star_self_edge` was written to
      prevent, and its docstring names both the mechanism and the verdict: "admitting the
      edge while the shape happens to have no concretes yet therefore does not avoid the
      cycle -- it defers it onto the next innocent write, which is then permanently
      rejected (the 'detonation': the graph locks itself out of a grant the set engine
      and the oracle both allow)". So F2 is NOT the set engine being too permissive; it
      is a hole in the graph's own by-construction early rejection.

  CTRL  order B,C,D with no A at all -- the OVER-REJECT CONTROL. No `folder` entity ever
      exists, so the crossing has nothing to cross through and every backend must ACCEPT
      all three writes. This is the case that goes red if the F1 fix makes the virtual
      crossing hop unconditional instead of gating it on entity existence. It matters as
      much as F1: a fix that reddens CTRL has bought parity by over-rejecting.

WHY THE TWO FAMILIES TAKE OPPOSITE FIXES. F1 is the set engine failing to implement a
clause that `docs/specs/set-engine-spec.md` sec 1 item 5 already decided ("Reject them
here too, with equivalent errors, so the 4-way matrix compares identical stores"), with
the mechanic prescribed in sec 6.2. Narrowing the set engine is therefore an unimplemented
spec clause, not a fresh design call. F2 points the other way: propagating the graph's
refusal into the set engine would make BOTH backends lock themselves out of a grant the
ORACLE allows, which is the outcome `_reject_star_self_edge` exists to avoid. F2's fix
belongs on the graph side -- refuse the latent-cycle write D early, as that method already
does for the same-shape `w_any -> w_all` routed edge it does cover.

The probe drives `tests/test_matrix.py::GraphBackend` / `::SetBackend` deliberately, so the
accept/reject semantics are the GATE's and not a hand-rolled wrapper's.

-- TRANSCRIPTS (literal, 2026-09-16) ----------------------------------------------------

PRE-FIX, rc=1 -- both families diverge, and CTRL is clean:

  == F1   -- the audited case: D must be refused by every backend ==
    ok       add ('...', 'user', 'u1', 'editor', 'folder', 'f1') -> graph=True set:py=True set:roaring=True
    ok       add ('member', 'group', 'g', 'viewer', 'folder', '*') -> graph=True set:py=True set:roaring=True
    ok       add ('...', 'folder', '*', 'parent', 'doc', 'd1') -> graph=True set:py=True set:roaring=True
    DIVERGES add ('viewer', 'doc', 'd1', 'member', 'group', 'g') -> graph=False set:py=True set:roaring=True
  == F2   -- the detonation: the graph refuses the ordinary grant A ==
    ok       add ('member', 'group', 'g', 'viewer', 'folder', '*') -> graph=True set:py=True set:roaring=True
    ok       add ('...', 'folder', '*', 'parent', 'doc', 'd1') -> graph=True set:py=True set:roaring=True
    ok       add ('viewer', 'doc', 'd1', 'member', 'group', 'g') -> graph=True set:py=True set:roaring=True
    DIVERGES add ('...', 'user', 'u1', 'editor', 'folder', 'f1') -> graph=False set:py=True set:roaring=True
  == CTRL -- over-reject control: every backend must ACCEPT all three ==
    ok       (all three writes accepted by every backend)

  ADMISSION PARITY BROKEN on 2 write(s):
      F1: ('viewer', 'doc', 'd1', 'member', 'group', 'g')
      F2: ('...', 'user', 'u1', 'editor', 'folder', 'f1')

POST-FIX, rc=1 -- F1 closed, CTRL unchanged (no over-reject), F2 still open as `TK70`:

  == F1 ==
    ok       add ('viewer', 'doc', 'd1', 'member', 'group', 'g') -> graph=False set:py=False set:roaring=False
  == F2 ==
    DIVERGES add ('...', 'user', 'u1', 'editor', 'folder', 'f1') -> graph=False set:py=True set:roaring=True
  == CTRL ==
    ok       (unchanged -- all three writes accepted by every backend)

  ADMISSION PARITY BROKEN on 1 write(s):
      F2: ('...', 'user', 'u1', 'editor', 'folder', 'f1')

(!) THIS PROBE EXITS NONZERO ON PURPOSE WHILE `TK70` IS OPEN. rc=0 means F2 was closed --
at which point `tests/test_reg_tk69_entity_crossing.py::test_family2_detonation_is_still_open`
goes red too, and both are meant to be flipped deliberately in the same change. Do not
"fix" the rc by deleting the F2 case.

"""
import sys

from setengine.setops import ALL_SETOPS
from tests.test_matrix import GraphBackend, SetBackend

SCHEMA = '''
type user
type group
  relations
    define member: [user, doc#viewer]
type folder
  relations
    define editor: [user]
    define parent: [folder, folder:*]
    define viewer: [user, group#member] or viewer from parent
type doc
  relations
    define parent: [folder, folder:*]
    define viewer: [user, group#member] or viewer from parent
'''

OBJ_WC = frozenset({('folder', 'viewer')})

A = ('...', 'user', 'u1', 'editor', 'folder', 'f1')      # ordinary grant; mints folder:f1
B = ('member', 'group', 'g', 'viewer', 'folder', '*')    # object-wildcard userset grant
C = ('...', 'folder', '*', 'parent', 'doc', 'd1')        # bare-star tupleset parent
D = ('viewer', 'doc', 'd1', 'member', 'group', 'g')      # closes the userset cycle

CASES = [
    ('F1  ', [A, B, C, D], 'the audited case: D must be refused by every backend'),
    ('F2  ', [B, C, D, A], 'the detonation: the graph refuses the ordinary grant A'),
    ('CTRL', [B, C, D],    'over-reject control: every backend must ACCEPT all three'),
]


def run_case(ops):
    """Apply ops to all three backends, returning per-write accept tuples."""
    graph = GraphBackend(SCHEMA, OBJ_WC)
    sets = [SetBackend(SCHEMA, OBJ_WC, o) for o in ALL_SETOPS]
    rows = []
    for raw in ops:
        g = graph.apply(raw, 'add')
        ss = [b.apply(raw, 'add') for b in sets]
        rows.append((raw, g, list(zip([b.name for b in sets], ss))))
    return rows


def main() -> int:
    diverged = []
    for tag, ops, why in CASES:
        print(f'== {tag} -- {why} ==')
        for raw, g, ss in run_case(ops):
            agree = all(s == g for _n, s in ss)
            mark = 'ok      ' if agree else 'DIVERGES'
            print(f'  {mark} add {raw} -> graph={g} ' +
                  ' '.join(f'{n}={s}' for n, s in ss))
            if not agree:
                diverged.append((tag.strip(), raw))
    print()
    if diverged:
        print(f'ADMISSION PARITY BROKEN on {len(diverged)} write(s):')
        for tag, raw in diverged:
            print(f'    {tag}: {raw}')
        return 1
    print('ADMISSION PARITY HOLDS on all three cases.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
