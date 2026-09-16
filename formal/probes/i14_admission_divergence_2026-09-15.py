"""I14 ENTITY-MIDDLE ADMISSION DIVERGENCE -- set engine ACCEPTS, graph index REFUSES.

-- CORRECTION APPENDED 2026-09-16b: THE DIVERGENCE THIS PROBE MEASURES IS FIXED ---------

⚠ **THE TRANSCRIPT BELOW IS HISTORY, NOT CURRENT BEHAVIOUR.** `TK69` was fixed
2026-09-16b and re-running this file now prints

    ok: add ('viewer','doc','d1','member','group','g') -> graph=False set:py=False set:roaring=False
    -> admission divergence: False

i.e. every backend refuses the cycle-closing write and the stores no longer fork. The
header's `graph=False set:py=True set:roaring=True` line was true on 2026-09-15 and is the
record of the defect, which is why it is not edited.

The fix: `setengine/engine.py::SetEngine._flow_reaches` now steps
`w_all(T,p) -> w_any(T,p)` on a CROSSABLE shape when an entity of type `T` exists -- the
I14 crossing middle added virtually, gated on entity existence. Ledger:
`docs/spec-deviations.md` 2026-09-16. Map: `docs/tk69-admission-parity-2026-09-16.md`.

⚠ **THIS FILE IS NO LONGER THE LIVE INSTRUMENT.** Use
`formal/probes/tk69_admission_parity_2026-09-16.py`, which measures BOTH divergence
families plus the over-reject control, and which still exits nonzero because family 2
(`TK70`, the detonation) is open. A second family exists that this probe never saw: the
same four writes in order B,C,D,A leave the graph refusing an ORDINARY grant. Do not read
this file's "the divergence" as definite -- there were two.


  Run:  PYTHONPATH=. <env-python> formal/probes/i14_admission_divergence_2026-09-15.py

Found 2026-09-15 by an adversarial audit; reproduced first-hand the same day. This file
is the TRACKED home for that evidence (the original probe was written to the gitignored
`.scratch/`, which by `CLAUDE.md` is the same as not recording it).

WHAT IT MEASURES, in three parts:

  (A) ADMISSION. Four adds, applied through the validation matrix's OWN backend adapters
      (`tests/test_matrix.py::GraphBackend` / `::SetBackend`) so accept/reject semantics
      are the gate's, not this file's. Write 4 closes a userset cycle:

          doc:d1#viewer -> group:g#member   (write 4)
          group:g#member -> folder:*#viewer (write 2)
          folder:* -> doc:d1#parent         (write 3), and doc.viewer has
                                            `or viewer from parent`

      so `doc:d1#viewer` depends on itself. The GRAPH refuses (it materialises a
      transitive closure; `Inv.acyclic` / I2 is load-bearing). The SET ENGINE accepts on
      BOTH `SetOps` backends -- its cycle check walks a flow graph whose nodes are created
      per incident EDGE (`setengine/engine.py::SetEngine._shape_node_ref`), while the
      graph's entity middles exist per ENTITY (`index_v4/wildcard.py::
      WildcardIndex._ensure_entity_middles`), so the set engine cannot see the crossing.

  (B) THE FORK. After (A) the two backends hold DIFFERENT STORES -- the graph rolled write
      4 back, the set engine kept it. Part (B) asks a query grid of both, plus the
      independent oracle on each store separately, and reports every disagreement. This is
      the part that says whether the divergence is confined to admission or reaches
      ANSWERS.

  (C) THE ADJUDICATION. The oracle is the referee. Run on the 4-tuple store the set engine
      accepted: if the oracle evaluates it and agrees with the set engine, the graph is
      REFUSING A STORE THE SPEC DEFINES, and the fix belongs on the graph/admission
      contract rather than on the set engine. If the oracle disagrees or cannot evaluate,
      the set engine is admitting a store with no defined meaning.

NOT CLAIMED HERE: the downstream severity. Whether this wedges a multi-instance async
cursor (the audit's REASONED claim, via the ValueError -> InvariantViolation promotion in
`connectedstore/apply.py::_apply_row`) is a SEPARATE measurement and is not made by this
file. Do not cite this probe for it.

-- THE RESULT ---------------------------------------------------------------------------

**IT IS AN ADMISSION-CONTRACT DIVERGENCE, NOT A WRONG ANSWER.** The oracle evaluates the
4-tuple store fine, and EVERY backend matches the oracle on the store it holds -- 0 of 12
grid queries has a backend disagreeing with its own spec reading. So neither side computes
anything wrong, and this is NOT a ghost grant.

What it IS: the two backends disagree about which stores may EXIST, and after the
disagreement they hold different data and answer differently -- 4 of 12 grid queries fork.
Given the same write sequence, a set-engine deployment and a graph deployment diverge
permanently. That is the project's primary goal (equivalence) breaking at the admission
layer rather than the evaluation layer.

Which side is wrong is a CONTRACT DECISION, not a bug fix, and this probe does not make
it. The spec defines a meaning for the cyclic store (least fixpoint: the cycle is unfed,
so it grants nothing), so the graph is the more restrictive side -- but the graph's
restriction is load-bearing (it materialises a closure; an admitted cycle breaks I2).
Aligning the set engine's `_would_cycle` to refuse it is the smaller change and the one
that preserves both backends' existing guarantees.

-- TRANSCRIPT (literal, rc=0, 2026-09-15) ----------------------------------------------

  == (A) ADMISSION ==
    ok: add ('...', 'user', 'u1', 'editor', 'folder', 'f1') -> graph=True set:py=True set:roaring=True
    ok: add ('member', 'group', 'g', 'viewer', 'folder', '*') -> graph=True set:py=True set:roaring=True
    ok: add ('...', 'folder', '*', 'parent', 'doc', 'd1') -> graph=True set:py=True set:roaring=True
    DIVERGES: add ('viewer', 'doc', 'd1', 'member', 'group', 'g') -> graph=False set:py=True set:roaring=True
    -> admission divergence: True
    -> graph holds 3 tuple(s), set engine holds 4

  == (C) ADJUDICATION: does the oracle evaluate the store the set engine kept? ==
    oracle evaluates the 4-tuple store: YES (sample answer False)

  == (B) THE FORK: answers on the grid ==
    q | graph | set:py | set:roaring | oracle(graph store) | oracle(set store)
    user:u1#... -viewer-> doc:d1 | False | False | False | False | False
    user:u1#... -viewer-> folder:f1 | False | False | False | False | False
    user:u1#... -editor-> folder:f1 | True | True | True | True | True
    user:u1#... -member-> group:g | False | False | False | False | False
    group:g#member -viewer-> doc:d1 | True | True | True | True | True
    group:g#member -viewer-> folder:f1 | True | True | True | True | True
    group:g#member -editor-> folder:f1 | False | False | False | False | False
    group:g#member -member-> group:g | False | True | True | False | True <-- FORK
    doc:d1#viewer -viewer-> doc:d1 | False | True | True | False | True <-- FORK
    doc:d1#viewer -viewer-> folder:f1 | False | True | True | False | True <-- FORK
    doc:d1#viewer -member-> group:g | False | True | True | False | True <-- FORK

  == VERDICT ==
    admission divergence            : True
    answer fork (graph vs set)      : 4 of 12 queries
    every backend matches the oracle ON THE STORE IT HOLDS
    -> so this is an ADMISSION-CONTRACT divergence, not a wrong answer:
       the two backends disagree about which stores may exist, and each
       then serves its own store correctly.
"""
from setengine.setops import ALL_SETOPS
from tests.oracle import Oracle, t as otuple
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

# (subject_predicate, subject_type, subject_name, relation, object_type, object_name)
OPS = [
    ('...', 'user', 'u1', 'editor', 'folder', 'f1'),
    ('member', 'group', 'g', 'viewer', 'folder', '*'),
    ('...', 'folder', '*', 'parent', 'doc', 'd1'),
    ('viewer', 'doc', 'd1', 'member', 'group', 'g'),   # <- closes the cycle
]

SUBJECTS = [
    ('...', 'user', 'u1'),
    ('member', 'group', 'g'),
    ('viewer', 'doc', 'd1'),
]
TARGETS = [
    ('viewer', 'doc', 'd1'),
    ('viewer', 'folder', 'f1'),
    ('editor', 'folder', 'f1'),
    ('member', 'group', 'g'),
]
GRID = [s + r for s in SUBJECTS for r in TARGETS]


def _fmt(q):
    return f'{q[1]}:{q[2]}#{q[0]} -{q[3]}-> {q[4]}:{q[5]}'


def main() -> int:
    print('== (A) ADMISSION ==')
    graph = GraphBackend(SCHEMA, OBJ_WC)
    sets = [SetBackend(SCHEMA, OBJ_WC, ops) for ops in ALL_SETOPS]

    graph_store, set_store = [], []
    admission_diverged = False
    for raw in OPS:
        g = graph.apply(raw, 'add')
        ss = [b.apply(raw, 'add') for b in sets]
        if g:
            graph_store.append(raw)
        if ss[0]:
            set_store.append(raw)
        tag = 'DIVERGES' if any(s != g for s in ss) else 'ok'
        admission_diverged |= tag == 'DIVERGES'
        print(f'  {tag}: add {raw} -> graph={g} ' +
              ' '.join(f'{b.name}={s}' for b, s in zip(sets, ss)))
    print(f'  -> admission divergence: {admission_diverged}')
    print(f'  -> graph holds {len(graph_store)} tuple(s), set engine holds {len(set_store)}')

    # The oracle on each store SEPARATELY -- each backend judged against the spec
    # reading of the store it actually holds.
    orc_graph = Oracle(SCHEMA, [otuple(*r) for r in graph_store])
    orc_set = Oracle(SCHEMA, [otuple(*r) for r in set_store])

    print('\n== (C) ADJUDICATION: does the oracle evaluate the store the set engine kept? ==')
    try:
        probe = orc_set.check(*GRID[0])
        print(f'  oracle evaluates the 4-tuple store: YES (sample answer {probe})')
    except Exception as exc:                                  # noqa: BLE001 - reporting
        print(f'  oracle FAILED on the 4-tuple store: {type(exc).__name__}: {exc}')
        print('  -> the set engine admitted a store the SPEC cannot evaluate')
        return 0

    print('\n== (B) THE FORK: answers on the grid ==')
    print('  q | graph | set:py | set:roaring | oracle(graph store) | oracle(set store)')
    answer_div_vs_own_oracle = []
    fork = []
    for q in GRID:
        g = graph.check(q)
        ss = [b.check(q) for b in sets]
        og = orc_graph.check(*q)
        os_ = orc_set.check(*q)
        # Each backend against the oracle reading of ITS OWN store: a real bug.
        if g != og:
            answer_div_vs_own_oracle.append((q, 'graph', g, og))
        for b, s in zip(sets, ss):
            if s != os_:
                answer_div_vs_own_oracle.append((q, b.name, s, os_))
        # The two systems against each other: the operational fork.
        if any(s != g for s in ss):
            fork.append(q)
        flag = ' <-- FORK' if any(s != g for s in ss) else ''
        print(f'  {_fmt(q)} | {g} | ' + ' | '.join(str(s) for s in ss) +
              f' | {og} | {os_}{flag}')

    print('\n== VERDICT ==')
    print(f'  admission divergence            : {admission_diverged}')
    print(f'  answer fork (graph vs set)      : {len(fork)} of {len(GRID)} queries')
    if answer_div_vs_own_oracle:
        print(f'  ** BACKEND DISAGREES WITH ORACLE ON ITS OWN STORE: '
              f'{len(answer_div_vs_own_oracle)} case(s) **')
        for q, who, got, want in answer_div_vs_own_oracle:
            print(f'     {_fmt(q)}: {who}={got} oracle={want}')
    else:
        print('  every backend matches the oracle ON THE STORE IT HOLDS')
        print('  -> so this is an ADMISSION-CONTRACT divergence, not a wrong answer:')
        print('     the two backends disagree about which stores may exist, and each')
        print('     then serves its own store correctly.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
