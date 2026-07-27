"""``check_invariants``'s docstring claimed a SMALLER invariant set than it runs.

The zero-trust review's last P5 bullet: "three documents give three different lists of
which invariants run per commit, and none matches ``index_v4/invariants.py``". Two
architecture docs were corrected and left the docstring flagged as still wrong -- it
said "Assert I1-I6 + I10", while the body also runs I7 (residue-version monotonicity)
and I13 (reference_count == direct-edge degree).

An understated docstring is not cosmetic here: it is the document an operator reads to
decide what paranoia mode is buying them, and I13 is the clause that makes the
refcount corruption which silently defeats bridge/derived-node GC visible at all.

This pin has two halves, and it needs both -- asserting on prose alone would let the
docstring drift the other way (into an OVERclaim) unnoticed:
  * the docstring no longer makes the understated claim and names I7 and I13;
  * ``check_invariants`` demonstrably ENFORCES I7 and I13, i.e. the corrected claim
    is true of the body.
"""

import json

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from index_v4 import ReachabilityIndex, Store
from index_v4.invariants import InvariantViolation, check_invariants
from index_v4.models import NodeV4, ResidueV1
from zanzibar_utils_v1 import parse_openfga_schema
from tests.wildcard_helpers import make_wildcard_index

_SCHEMA = '''
    type user
    type doc
      relations
        define editor: [user, user:*]
        define blocked: [user]
        define viewer: editor but not blocked
'''


def test_docstring_states_the_set_the_body_actually_runs():
    """The HEADLINE claim (everything before the first blank line) is what a reader
    takes away; that is where the understatement lived, so that is what is pinned.
    The body of the docstring is free to discuss I9/I11/I12 and say they run
    elsewhere -- which is why this looks at the headline and not the whole string."""
    doc = check_invariants.__doc__
    assert doc, 'check_invariants lost its docstring'
    headline = doc.split('\n\n', 1)[0]
    assert len(headline.strip()) > 20, 'headline is empty -- the checks below would be vacuous'

    # The exact understated claim that was live until this fix.
    assert 'I1-I6' not in headline
    # Everything the body enforces must be named or covered by a stated range.
    named = 0
    for clause in ('I1-I7', 'I10', 'I13'):
        assert clause in headline, f'{clause} runs in the body but is unnamed'
        named += 1
    assert named == 3
    # ...and nothing that runs somewhere else may be claimed here.
    for absent in ('I9', 'I11', 'I12'):
        assert absent not in headline, f'{absent} does not run here but is claimed'


def test_body_enforces_i13_reference_count_degree():
    """I13 is one of the two clauses the old docstring omitted -- prove it runs."""
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Store(id='s'))
        session.commit()
        idx = ReachabilityIndex(session, store_id='s')
        idx.add_edge(..., 'user', 'alice', 'viewer', 'doc', 'd1')
        session.commit()
        check_invariants(session, 's')            # clean baseline, or the rest lies

        node = idx.node(..., 'user', 'alice', create_if_missing=False)
        assert node.reference_count == 1
        node.reference_count = 7                  # corrupt: degree is still 1
        session.add(node)
        session.flush()
        with pytest.raises(InvariantViolation) as exc:
            check_invariants(session, 's')
        assert 'I13' in str(exc.value)
        session.rollback()


def test_body_enforces_i7_residue_version_monotonicity():
    """I7 is the other omitted clause. It only runs when the caller passes the
    ``residue_versions`` ledger -- which the paranoia guard does on every commit."""
    rs = parse_openfga_schema(_SCHEMA, enable_boolean=True)
    session, widx = make_wildcard_index(rs.schema_info)
    from index_v4.processor import DeltaProcessor
    from index_v4.outbox import outbox_watermark
    from zanzibar_utils_v1 import Entity, RelationalTriple

    proc = DeltaProcessor(widx, rs.compiled)

    def write(raw):
        wm = outbox_watermark(session, 'test')
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]),
                                  Ellipsis if raw[0] == '...' else raw[0])
        for d in rs.apply(triple):
            widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                           d.subject.type, d.subject.name, d.relation,
                           d.object.type, d.object.name)
        proc.run_cascade(wm)
        session.commit()

    write(('...', 'user', '*', 'editor', 'doc', 'd1'))    # star-covered positive arm
    write(('...', 'user', 'bob', 'blocked', 'doc', 'd1'))  # -> a neg entry

    rows = session.exec(select(ResidueV1)).all()
    assert len(rows) == 1, f'fixture produced {len(rows)} residue rows, need exactly 1'
    row = rows[0]
    assert json.loads(row.stars), 'residue has no stars -- fixture did not bite'

    # A ledger claiming a HIGHER last-seen version than the row carries is exactly
    # the "version regressed" corruption I7 exists to catch.
    ledger = {(row.id, row.object_node_id): row.version + 5}
    with pytest.raises(InvariantViolation) as exc:
        check_invariants(session, 'test', rs.schema_info, residue_versions=ledger)
    assert 'I7' in str(exc.value)

    # ...and the honest ledger passes, so the clause is discriminating, not a
    # blanket raise.
    check_invariants(session, 'test', rs.schema_info,
                     residue_versions={(row.id, row.object_node_id): row.version})
    session.close()
