#!/usr/bin/env python
"""`TK72` -- what `check_invariants(..., schema_info)` actually buys, demonstrated.

THE CLAIM UNDER TEST. `tests/test_zt_p5_readjudication.py` called
`index_v4/invariants.py::check_invariants(session, store)` with no `schema_info` at three
sites, and its docstring said *"I1-I13 are green on all three"*. Without the handle the
checker skips the rest of I3 (bridge completeness/exclusivity), I14, I4 namespace
classification and every derived invariant -- so the docstring named invariants the run did
not perform. This probe shows the difference is REAL on that module's own corpus, by
corrupting a store in a way that only the gated clause can see.

WHY A CORRUPTION AND NOT A COUNT. A green after passing the handle proves nothing on its own:
2026-09-17c measured *"147 check_invariants(with schema_info) calls, 0 RED"* on these corpora
and the honest reading was **"I14 was never applicable"** -- `crossable_shapes` is EMPTY here
(bridged OUT only; crossability needs in AND out). The instrument control below prints the
`SchemaInfo` so that reading is forced, and the sabotage below is what makes the remaining
clause's teeth visible.

THE SABOTAGE. Delete one `w_all -> concrete` bridge edge and decrement the two endpoint
reference counts, so every SCHEMA-INDEPENDENT clause stays satisfied (I1's per-edge algebra,
I2 acyclicity, I3's direct-edge variant rules, I13's refcount == degree). The store is then
consistent to the reduced checker and broken to the full one.

USAGE
  python formal/probes/tk72_schema_info_gate_2026-09-19.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlmodel import Session, SQLModel, create_engine, select      # noqa: E402

from connectedstore import ConnectedStore                          # noqa: E402
from index_v4.invariants import check_invariants                   # noqa: E402
from index_v4.models import EdgeV4, NodeV4                         # noqa: E402
from tests.test_zt_p5_readjudication import _OWC_TTU_CORPUS        # noqa: E402


def build(seq):
    schema, owc, _space = _OWC_TTU_CORPUS
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    cs = ConnectedStore(session, 'live', schema=schema, object_wildcard_shapes=owc)
    session.commit()
    landed = []
    for w in seq:
        try:
            cs.add_tuple(*w)
            landed.append(w)
        except ValueError:
            pass
    session.commit()
    return session, landed, cs.widx.schema_info


def main() -> int:
    _schema, _owc, space = _OWC_TTU_CORPUS
    session, landed, si = build(list(space))
    print(f'corpus: {len(space)} candidate writes, {len(landed)} landed')
    print('INSTRUMENT CONTROL, live SchemaInfo:')
    print(f'    crossable_shapes   {sorted(si.crossable_shapes)}')
    print(f'    bridged_in_shapes  {sorted(si.bridged_in_shapes)}')
    print(f'    bridged_out_shapes {sorted(si.bridged_out_shapes)}')
    print(f'    derived_families   {sorted(si.derived_families)}')
    print('    -> I14 iterates NOTHING on this corpus. The clause under test is I3')
    print('       bridge completeness/exclusivity.')

    nodes = list(session.exec(select(NodeV4).where(NodeV4.store_id == 'live')).all())
    by_id = {n.id: n for n in nodes}
    edges = list(session.exec(select(EdgeV4).where(EdgeV4.store_id == 'live')).all())
    victim = None
    for e in edges:
        if e.direct_edge_count <= 0:
            continue
        s, o = by_id[e.subject_id], by_id[e.object_id]
        if s.wildcard == 'all' and o.wildcard == '' and (o.type, o.predicate) in si.bridged_out_shapes:
            victim = (e, s, o)
            break
    if victim is None:
        print('NO w_all->concrete BRIDGE EDGE FOUND -- the probe measures nothing')
        return 2
    e, s, o = victim
    print(f'\nsabotage: deleting the bridge {s.type}:{s.name or "*"}#{s.predicate}'
          f'[{s.wildcard}] -> {o.type}:{o.name}#{o.predicate}, '
          f'and decrementing both refcounts by {e.direct_edge_count}')

    s.reference_count -= e.direct_edge_count
    o.reference_count -= e.direct_edge_count
    session.add(s)
    session.add(o)
    session.delete(e)
    session.commit()

    for label, arg in (('WITHOUT schema_info', None), ('WITH schema_info', si)):
        try:
            check_invariants(session, 'live', arg)
            print(f'  {label:20} GREEN')
        except AssertionError as exc:
            first = str(exc).strip().splitlines()[0]
            print(f'  {label:20} RED   {first}')
    session.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
