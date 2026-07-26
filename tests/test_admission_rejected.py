"""`AdmissionRejected` — the type that separates a CORRECT REFUSAL from a BUG.

ZT-P4-7. `index_v4` used to raise bare `ValueError` for BOTH (a) legitimate write
refusals (cycle, undeclared wildcard shape, bad identifier, removing what is not
there, a tuple no declared restriction admits) and (b) internal-contract failures
that are bugs (a stale node id, a malformed wildcard encoding, an I5 routing
breach). A consumer could not tell them apart, so `formal/conformance/backends.py`
had to classify by MESSAGE SUBSTRING — recorded at the time as an explicit stopgap.
That mattered concretely: `GraphDriver.apply` reports "rejected", and
`test_conformance_remove.py` builds its oracle from the graph's own accepted set,
so an `index_v4` bug that spuriously raised on a LEGITIMATE add shrank BOTH sides
of the differential and the gate stayed green.

This module pins the replacement contract:

  1. every genuine refusal site raises `AdmissionRejected`, with its message text
     UNCHANGED (this refactor changed exception TYPES, never a decision);
  2. `AdmissionRejected` IS a `ValueError` — every pre-existing `except ValueError`
     around a write keeps classifying it identically (backward compatibility is a
     requirement, not an accident);
  3. `InvariantViolation` is untouched: an `AssertionError`, NOT a `ValueError`, so
     it never enters a `ValueError` handler at all;
  4. the sites deliberately left as plain `ValueError` stay unclassified, and
  5. `GraphDriver.apply` absorbs ONLY `AdmissionRejected`; an unclassified
     `ValueError` from the index now PROPAGATES (as a loud `AssertionError`)
     instead of silently shrinking the store the oracle is built from.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from index_v4 import ReachabilityIndex, Store, WildcardIndex
from index_v4.core import AdmissionRejected as CoreAdmissionRejected
from index_v4.invariants import InvariantViolation
from setengine import SetEngine
from tests.oracle import t as mk_tuple
from tests.wildcard_helpers import make_wildcard_index
from zanzibar_utils_v1 import (AdmissionRejected, Entity, RelationalTriple,
                               parse_openfga_schema, validate_write_identifiers)


SCHEMA = """
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define viewer: [user, group#member]
"""

BOOL_SCHEMA = """
type user
type doc
  relations
    define banned: [user]
    define viewer: [user] but not banned
"""


def _widx(schema_text=SCHEMA, owc=frozenset()):
    rs = parse_openfga_schema(schema_text, object_wildcard_shapes=owc)
    session, widx = make_wildcard_index(rs.schema_info, store_id='adm')
    return rs, session, widx


def _core():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Store(id='adm'))
    session.commit()
    return session, ReachabilityIndex(session, store_id='adm')


# --------------------------------------------------------------------------- #
# 1. The class itself
# --------------------------------------------------------------------------- #

def test_admission_rejected_is_a_valueerror_subclass():
    """BACKWARD COMPATIBILITY, and it is load-bearing: `connectedstore.store._write`,
    `tests/parity.py`, `tests/test_matrix.py`'s backends, `index_v4.processor`'s
    cycle guard and `connectedstore.apply._apply_row` all catch `ValueError` around
    a write. Breaking this subclassing silently changes all of them."""
    assert issubclass(AdmissionRejected, ValueError)
    assert AdmissionRejected is CoreAdmissionRejected      # re-exported, one class

    try:
        raise AdmissionRejected('x')
    except ValueError as e:                                # the pre-existing form
        assert isinstance(e, AdmissionRejected)


def test_invariant_violation_is_untouched_and_disjoint():
    """The mirror class. A violation is CORRUPTION and must never be mistaken for a
    refusal: it is an `AssertionError`, so a `except ValueError` handler cannot see
    it, and the two classes share no ancestry below `Exception`."""
    assert issubclass(InvariantViolation, AssertionError)
    assert not issubclass(InvariantViolation, ValueError)
    assert not issubclass(InvariantViolation, AdmissionRejected)
    assert not issubclass(AdmissionRejected, AssertionError)

    with pytest.raises(InvariantViolation):
        try:
            raise InvariantViolation('corruption')
        except ValueError:                                 # must NOT catch
            pytest.fail('InvariantViolation was absorbed by a ValueError handler')


# --------------------------------------------------------------------------- #
# 2. The converted refusal sites — type AND unchanged message text
# --------------------------------------------------------------------------- #

def test_cycle_self_edge_is_admission_rejected():
    """`core._add_edge_locked`: subject node IS object node (the trivial cycle)."""
    _rs, session, widx = _widx()
    with pytest.raises(AdmissionRejected,
                       match='self-referential edge would create a cycle'):
        widx.add_tuple('member', 'group', 'a', 'member', 'group', 'a')
    session.rollback()
    session.close()


def test_cycle_back_path_is_admission_rejected():
    """`core._add_edge_locked`: the reverse-reachability pre-check."""
    _rs, session, widx = _widx()
    widx.add_tuple('member', 'group', 'a', 'member', 'group', 'b')
    session.commit()
    with pytest.raises(AdmissionRejected,
                       match='adding this edge would create a cycle'):
        widx.add_tuple('member', 'group', 'b', 'member', 'group', 'a')
    session.rollback()
    session.close()


def test_cycle_rejection_is_still_catchable_as_valueerror():
    """The same rejection, through the pre-existing handler shape."""
    _rs, session, widx = _widx()
    try:
        widx.add_tuple('member', 'group', 'a', 'member', 'group', 'a')
    except ValueError as e:
        assert isinstance(e, AdmissionRejected)
    else:                                                  # pragma: no cover
        pytest.fail('the self-edge cycle was accepted')
    session.rollback()
    session.close()


WC_SCHEMA = """
type user
type group
  relations
    define member: [user, group#member, group:*#member]
"""


def test_wildcard_cycle_redress_is_admission_rejected():
    """`wildcard.add_tuple`'s re-dress of the core's cycle refusal (the wildcard
    endpoint gets a wildcard-specific message). Its `except` was narrowed from
    `ValueError` to `AdmissionRejected`; this pins that the wrapper still fires and
    still carries the rejection type."""
    _rs, session, widx = _widx(WC_SCHEMA)
    widx.add_tuple('...', 'user', 'u', 'member', 'group', 'g1')   # mint the concrete
    session.commit()
    with pytest.raises(AdmissionRejected, match='wildcard tuple rejected'):
        widx.add_tuple('member', 'group', '*', 'member', 'group', 'g1')
    session.rollback()
    session.close()


def test_wildcard_redress_does_not_swallow_an_internal_valueerror(monkeypatch):
    """The narrowing's other half: an UNclassified `ValueError` raised inside
    `add_edge_by_id` must pass straight through the re-dress handler, unwrapped and
    unclassified (it did before too — it never contained 'cycle', so it hit the bare
    `raise`; now it simply never enters the handler)."""
    _rs, session, widx = _widx(WC_SCHEMA)

    def boom(self, *a, **kw):
        raise ValueError('node id 42 no longer exists (concurrent removal?)')

    monkeypatch.setattr(type(widx.idx), 'add_edge_by_id', boom)
    with pytest.raises(ValueError) as ei:
        widx.add_tuple('member', 'group', '*', 'member', 'group', 'g1')
    assert not isinstance(ei.value, AdmissionRejected)
    assert 'no longer exists' in str(ei.value)          # unwrapped, not re-dressed
    session.rollback()
    session.close()


def test_remove_nonexistent_edge_is_admission_rejected():
    """`wildcard._remove_tuple_trusted`: endpoint the store never saw."""
    _rs, session, widx = _widx()
    with pytest.raises(AdmissionRejected,
                       match='Non-existent edge cannot be removed'):
        widx.remove_tuple('...', 'user', 'ghost', 'member', 'group', 'g')
    session.rollback()
    session.close()


def test_remove_nonexistent_node_is_admission_rejected():
    """`wildcard.remove_node`: node the store never saw."""
    _rs, session, widx = _widx()
    with pytest.raises(AdmissionRejected,
                       match='Non-existent node cannot be removed'):
        widx.remove_node('...', 'user', 'ghost')
    session.rollback()
    session.close()


def test_remove_wildcard_node_is_admission_rejected():
    """`wildcard.remove_node`: `T:*` is bridge/GC-managed — a user-facing refusal."""
    _rs, session, widx = _widx()
    with pytest.raises(AdmissionRejected,
                       match='wildcard nodes are bridge/GC-managed'):
        widx.remove_node('member', 'group', '*')
    session.rollback()
    session.close()


def test_core_remove_edge_paths_are_admission_rejected():
    """`core.remove_edge` (node-resolution miss) and `core._remove_edge_locked`
    (both endpoints live, but no direct edge; and the self-edge form)."""
    session, idx = _core()
    idx.add_edge('...', 'T', 'a', 'p', 'T', 'b')
    idx.add_edge('p', 'T', 'b', 'p', 'T', 'c')
    session.commit()

    with pytest.raises(AdmissionRejected,
                       match='Non-existent edge cannot be removed'):
        idx.remove_edge('...', 'T', 'nope', 'p', 'T', 'b')
    session.rollback()

    with pytest.raises(AdmissionRejected,
                       match='cannot remove nonexistent edge'):
        idx.remove_edge('...', 'T', 'a', 'p', 'T', 'c')   # live nodes, no edge
    session.rollback()

    with pytest.raises(AdmissionRejected,
                       match='no self-referential edge can exist'):
        idx.remove_edge('p', 'T', 'b', 'p', 'T', 'b')     # resolves to ONE node
    session.rollback()
    session.close()


def test_undeclared_wildcard_shapes_are_admission_rejected():
    """`wildcard._resolve`, both positions: the write names a `*` shape the schema
    never declared. (`SCHEMA` declares neither.)"""
    _rs, session, widx = _widx()
    with pytest.raises(AdmissionRejected,
                       match='is not a declared subject-wildcard shape'):
        widx.add_tuple('...', 'user', '*', 'member', 'group', 'g')
    session.rollback()
    with pytest.raises(AdmissionRejected,
                       match='is not a declared object-wildcard shape'):
        widx.add_tuple('...', 'user', 'u', 'member', 'group', '*')
    session.rollback()
    session.close()


def test_identifier_charset_violation_is_admission_rejected():
    """`zanzibar_utils_v1._require`, reached through both backends' write paths."""
    with pytest.raises(AdmissionRejected, match=r'must match \['):
        validate_write_identifiers('...', 'user', 'bad name', 'member', 'group', 'g')

    _rs, session, widx = _widx()
    with pytest.raises(AdmissionRejected, match=r'must match \['):
        widx.add_tuple('...', 'user', 'bad name', 'member', 'group', 'g')
    session.rollback()
    session.close()


def test_no_declared_restriction_match_is_admission_rejected():
    """`RuleSet.apply` (reg13). This is the type-restriction ADMISSION GATE — the
    same question `SetEngine._validate` step 2 answers, and it refuses the identical
    tuple. Pinned for both arms: pure-union and derived (boolean)."""
    rs = parse_openfga_schema(SCHEMA)
    bad = RelationalTriple(Entity('doc', 'd'), 'member', Entity('group', 'g'))
    with pytest.raises(AdmissionRejected,
                       match='matches no declared type restriction'):
        list(rs.apply(bad))                                # generator: force it

    brs = parse_openfga_schema(BOOL_SCHEMA)
    bad_derived = RelationalTriple(Entity('doc', 'x'), 'viewer', Entity('doc', 'd'))
    with pytest.raises(AdmissionRejected,
                       match='for derived relation doc#viewer'):   # the OTHER arm
        list(brs.apply(bad_derived))


def test_raw_write_to_a_leaf_predicate_is_admission_rejected():
    """`RuleSet.apply`: a raw write naming a compiler-generated `<rel>.<idx>` leaf."""
    brs = parse_openfga_schema(BOOL_SCHEMA)
    leaf = sorted(r for (_t, r) in brs.compiled.leaf_families)[0]
    triple = RelationalTriple(Entity('user', 'u'), leaf, Entity('doc', 'd'))
    with pytest.raises(AdmissionRejected,
                       match='is a compiled leaf predicate'):
        list(brs.apply(triple))


def test_set_engine_refusals_are_admission_rejected():
    """The peer backend raises the SAME class, so a rejection is one type
    system-wide (`SetEngine._validate` + the missing-tuple rejection). The composed
    store's admission gate IS the set engine, so this is what
    `connectedstore.store._write`'s narrowed handler keys on."""
    session = Session(create_engine('sqlite:///:memory:'))
    SQLModel.metadata.create_all(session.get_bind())
    eng = SetEngine(session, 's', SCHEMA)

    with pytest.raises(AdmissionRejected,
                       match='matches no declared type restriction'):
        eng.add_tuple('...', 'doc', 'd', 'member', 'group', 'g')
    with pytest.raises(AdmissionRejected,
                       match='is not a declared object-wildcard shape'):
        eng.add_tuple('...', 'user', 'u', 'member', 'group', '*')
    with pytest.raises(AdmissionRejected, match='would create a cycle'):
        eng.add_tuple('member', 'group', 'a', 'member', 'group', 'a')
    with pytest.raises(AdmissionRejected,
                       match='non-existent tuple cannot be removed'):
        eng.remove_tuple('...', 'user', 'u', 'member', 'group', 'g')
    session.close()


# --------------------------------------------------------------------------- #
# 3. The sites deliberately NOT classified
# --------------------------------------------------------------------------- #

def test_internal_contract_failures_stay_plain_valueerror():
    """Fail-closed by design: a site that means "a CALLER is broken" must stay
    unclassified so a classifier propagates it. Two representatives:

      * the node ENCODING contract (`core.node`) — only this library can reach it;
      * I5 derived-family exclusivity (`wildcard._assert_derived_exclusivity`) — a
        hit means the write bypassed `RuleSet.apply`'s leaf routing, i.e. a wiring
        bug in the caller, not an inadmissible tuple.
    """
    session, idx = _core()
    with pytest.raises(ValueError) as ei:
        idx.node('p', 'T', 'x', create_if_missing=True, wildcard='bogus')
    assert not isinstance(ei.value, AdmissionRejected)
    session.rollback()
    session.close()

    _rs, session2, widx = _widx(BOOL_SCHEMA)
    with pytest.raises(ValueError) as ei2:
        widx.add_tuple('...', 'user', 'u', 'viewer', 'doc', 'd')  # derived, unrouted
    assert not isinstance(ei2.value, AdmissionRejected)
    assert 'derived (boolean) relation' in str(ei2.value)
    session2.rollback()
    session2.close()


# --------------------------------------------------------------------------- #
# 4. GraphDriver.apply — the consumer this whole thing exists for
# --------------------------------------------------------------------------- #

def _drv():
    from formal.conformance.backends import GraphDriver
    return GraphDriver(SCHEMA)


def test_graphdriver_absorbs_only_admission_rejected():
    """A genuine refusal is reported as "rejected" (False), a legitimate write as
    committed (True). This is the behaviour the remove gate's poison bookkeeping
    depends on."""
    drv = _drv()
    ok = mk_tuple('...', 'user', 'u', 'member', 'group', 'g')
    assert drv.apply(ok, 'add') is True
    cyc = mk_tuple('member', 'group', 'a', 'member', 'group', 'a')
    assert drv.apply(cyc, 'add') is False                  # AdmissionRejected
    drv.close()


def test_graphdriver_propagates_an_unclassified_valueerror(monkeypatch):
    """THE ZT-P4-7 REGRESSION TEST. Inject an internal-contract `ValueError` into
    the index's write path on a LEGITIMATE add. Before the type existed the driver
    reported "rejected", the tuple vanished from the driven store AND from the
    oracle built off it, both corners agreed, and the gate stayed green. Now it
    fails loudly."""
    drv = _drv()

    def boom(*a, **kw):
        raise ValueError('node id 42 no longer exists (concurrent removal?)')

    monkeypatch.setattr(type(drv.widx), 'add_tuple', boom)
    ok = mk_tuple('...', 'user', 'u', 'member', 'group', 'g')
    with pytest.raises(AssertionError,
                       match='NOT an `AdmissionRejected` write-admission refusal'):
        drv.apply(ok, 'add')
    drv.close()


def test_graphdriver_propagates_an_invariant_violation(monkeypatch):
    """Corruption was already structurally separated (`InvariantViolation` is an
    `AssertionError`); pin that the narrowing did not weaken it."""
    drv = _drv()

    def boom(*a, **kw):
        raise InvariantViolation('I1 violated')

    monkeypatch.setattr(type(drv.widx), 'add_tuple', boom)
    ok = mk_tuple('...', 'user', 'u', 'member', 'group', 'g')
    with pytest.raises(InvariantViolation):
        drv.apply(ok, 'add')
    drv.close()


def test_backends_has_no_message_marker_machinery():
    """The stopgap is GONE, not merely unused: string-matching exception messages
    was the fragility this change exists to remove, and a re-introduced allow-list
    would silently reopen the hole."""
    from formal.conformance import backends
    assert not hasattr(backends, '_ADMISSION_REJECTION_MARKERS')
    assert not hasattr(backends, 'is_admission_rejection')
