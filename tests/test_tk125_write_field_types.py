"""TK125 -- every field of every tuple WRITE must be a ``str`` (or a declared sentinel).

FOUND by the fresh-user install trial of the published ``zanzibar-index`` 0.0.2
(``docs/pypi-trial-0.0.2-2026-10-07.md`` sec 1 B3)::

    store.add_tuple(None, "user", "bob", "viewer", "doc", "d1")
    sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint failed:
    zanzibar_tuple_log.subject_predicate

instead of ``AdmissionRejected``.

ROOT CAUSE (first-hand READ, 2026-10-08). ``zanzibar.schema.rules.norm_pred`` maps
``None`` -> ``'...'``; it is the READ normaliser (reads are lenient by contract). The
set engine's write path (``SetEngine._add_tuple_direct`` / ``_remove_tuple_direct``)
normalised with it BEFORE ``validate_write_identifiers``, so ``None`` validated as the
bare predicate. ``TupleSource.add/remove`` only map ``Ellipsis`` and logged the raw
``None``, which the NOT NULL column refused at flush. The same probe showed a BACKEND
DIVERGENCE on the raw write API: ``SetEngine.add_tuple(None, ...)`` was ACCEPTED as a
bare tuple while ``WildcardIndex.add_tuple`` / ``ReachabilityIndex.add_edge`` refused it.
Every other field and non-str value (``5``, ``b'user'``, ``1.5``) was already refused
(``is_valid_identifier`` requires ``isinstance(value, str)``). A second, narrower hole:
``_require`` admitted the ``'*'`` / ``'...'`` sentinels by ``==`` alone, so a non-str
object whose ``__eq__`` matches a sentinel passed validation.

DECISION (TK125, 2026-10-08): refuse, do not normalise. ``None`` is a common accident
(a missing dict key), the graph backend already refused it, and the documented write
forms of the bare predicate are ``'...'`` and ``Ellipsis`` only. Reads keep ``None`` ->
``'...'`` (pinned below, so an over-eager fix goes red too).

SABOTAGE (docs/sabotage-procedure.md), observed 2026-10-08 with
``pytest tests/test_tk125_write_field_types.py -q -rf --tb=no``. ``[...]`` abbreviates
``test_non_str_write_field_is_refused_before_any_state``.

PRE-FIX tree (HEAD 7296eb1), literal lines::

    FAILED [cs-sync-add-subject_predicate-None] - sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint failed: zanzibar_tuple_log.subject_predicate
    FAILED [cs-sync-remove-s_name-eq_everything] - AssertionError: Regex pattern did not match.
    FAILED [setengine-add-subject_predicate-None] - Failed: DID NOT RAISE AdmissionRejected
    FAILED [setengine-remove-subject_predicate-None] - Failed: DID NOT RAISE AdmissionRejected
    FAILED [graph-add-o_name-eq_everything] - AssertionError: Regex pattern did not match.
    FAILED [core-add-s_name-eq_everything] - ValueError: name=='*' and a non-empty wildcard must go together, got entity_name=<EqEverything>, wildcard=''
    FAILED [core-remove-subject_predicate-eq_everything] - sqlalchemy.exc.ProgrammingError: (sqlite3.ProgrammingError) Error binding parameter 2: type '_EqEverything' is not supported
    40 failed, 233 passed in 6.92s

Each half of the fix planted back alone on the FIXED tree:

* A -- ``_require``'s ``is_str = isinstance(value, str)`` replaced by ``is_str = True``
  (sentinels by ``==`` again): ``34 failed, 239 passed``, every failure an
  ``eq_everything`` case.
* B -- only ``SetEngine._add_tuple_direct`` back to normalise-then-validate (the remove
  site left fixed)::

    FAILED [cs-sync-add-subject_predicate-None] - sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint failed: zanzibar_tuple_log.subject_predicate
    FAILED [cs-async-add-subject_predicate-None] - sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint failed: zanzibar_tuple_log.subject_predicate
    FAILED [setengine-add-subject_predicate-None] - Failed: DID NOT RAISE AdmissionRejected
    3 failed, 270 passed in 7.14s

Fixed tree: ``273 passed``.
"""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from zanzibar.connectedstore import ConnectedStore, TupleLog
from zanzibar.graphindex import ReachabilityIndex, Store
from zanzibar.graphindex.invariants import snapshot_rows
from zanzibar.schema import AdmissionRejected, parse_openfga_schema
from zanzibar.setengine import RelationTuple, SetEngine
from tests.wildcard_helpers import make_wildcard_index

SCHEMA = """
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define viewer: [user, group#member]
"""

GOOD = ('...', 'user', 'bob', 'viewer', 'doc', 'd1')
FIELDS = ('subject_predicate', 's_type', 's_name', 'relation', 'o_type', 'o_name')


class _EqEverything:
    """Not a ``str``, but ``==`` to every sentinel (``'*'``, ``'...'``) -- the narrow
    weakening of a validator that admits sentinels by equality alone."""

    def __eq__(self, other):
        return True

    __hash__ = object.__hash__

    def __repr__(self):
        return '<EqEverything>'


BAD_VALUES = {
    'None': None,
    'int': 5,
    'bytes': b'user',
    'eq_everything': _EqEverything(),
}


def _sqlite_session() -> Session:
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


# --------------------------------------------------------------------------- #
# Entry points. Each factory returns (write, remove, state, present):
#   write/remove -- the public write call under test,
#   state        -- a hashable snapshot of EVERY persisted row it could touch,
#   present      -- does the GOOD tuple currently hold.
# --------------------------------------------------------------------------- #

def _cs(sync: bool):
    session = _sqlite_session()
    cs = ConnectedStore(session, 'tk125', schema=SCHEMA, sync=sync)

    def state():
        log = tuple(sorted((r.op, r.subject_predicate, r.subject_type, r.subject_name,
                            r.relation, r.object_type, r.object_name)
                           for r in session.exec(select(TupleLog)).all()))
        rel = tuple(sorted((r.subject_predicate, r.subject_type, r.subject_name,
                            r.relation, r.object_type, r.object_name)
                           for r in session.exec(select(RelationTuple)).all()))
        nodes, edges = snapshot_rows(session, 'tk125')
        return log, rel, tuple(sorted(nodes.items())), tuple(sorted(edges.items()))

    def present():
        if not sync:
            cs.catch_up()
        return cs.check(*GOOD)

    return cs.add_tuple, cs.remove_tuple, state, present


def _setengine():
    session = _sqlite_session()
    se = SetEngine(session, 'tk125', SCHEMA)

    def state():
        return tuple(sorted((r.subject_predicate, r.subject_type, r.subject_name,
                             r.relation, r.object_type, r.object_name)
                            for r in session.exec(select(RelationTuple)).all()))

    return se.add_tuple, se.remove_tuple, state, lambda: se.check(*GOOD)


def _graph():
    rs = parse_openfga_schema(SCHEMA)
    session, widx = make_wildcard_index(rs.schema_info, store_id='tk125', paranoia=False)

    def state():
        nodes, edges = snapshot_rows(session, 'tk125')
        return tuple(sorted(nodes.items())), tuple(sorted(edges.items()))

    return widx.add_tuple, widx.remove_tuple, state, lambda: widx.idx.check_reachable(*GOOD)


def _core():
    session = _sqlite_session()
    session.add(Store(id='tk125'))
    session.commit()
    idx = ReachabilityIndex(session, store_id='tk125')

    def state():
        nodes, edges = snapshot_rows(session, 'tk125')
        return tuple(sorted(nodes.items())), tuple(sorted(edges.items()))

    return idx.add_edge, idx.remove_edge, state, lambda: idx.check_reachable(*GOOD)


ENTRY_POINTS = {
    'cs-sync': lambda: _cs(True),
    'cs-async': lambda: _cs(False),
    'setengine': _setengine,
    'graph': _graph,
    'core': _core,
}


@pytest.mark.parametrize('bad_label', list(BAD_VALUES))
@pytest.mark.parametrize('field', FIELDS)
@pytest.mark.parametrize('op', ['add', 'remove'])
@pytest.mark.parametrize('entry', list(ENTRY_POINTS))
def test_non_str_write_field_is_refused_before_any_state(entry, op, field, bad_label):
    """A non-str value in ANY field of ANY public write is ``AdmissionRejected``, and
    nothing it could have written changed: no log row, no RelationTuple, no node/edge.

    ``remove`` runs against a store that holds GOOD, so a mis-normalised field would
    have something to (wrongly) remove; GOOD must still hold afterwards."""
    write, remove, state, present = ENTRY_POINTS[entry]()
    if op == 'remove':
        write(*GOOD)
    before = state()
    args = list(GOOD)
    args[FIELDS.index(field)] = BAD_VALUES[bad_label]
    with pytest.raises(AdmissionRejected, match=r'invalid '):
        (write if op == 'add' else remove)(*args)
    assert state() == before, f'{entry} {op}: a refused write changed persisted state'
    assert present() is (op == 'remove'), f'{entry} {op}: GOOD membership changed'


@pytest.mark.parametrize('entry', ['graph', 'core'])
@pytest.mark.parametrize('field', ['predicate', 'entity_type', 'entity_name'])
@pytest.mark.parametrize('bad_label', list(BAD_VALUES))
def test_non_str_remove_node_field_is_refused(entry, field, bad_label):
    """``remove_node`` (graph facade and core) -- the one node-level public write
    (the set engine has none). Refused, and no node/edge row changed."""
    write, _remove, state, present = ENTRY_POINTS[entry]()
    write(*GOOD)
    node_args = ['...', 'user', 'bob']
    node_args[['predicate', 'entity_type', 'entity_name'].index(field)] = BAD_VALUES[bad_label]
    before = state()
    with pytest.raises(AdmissionRejected, match=r'invalid '):
        write.__self__.remove_node(*node_args)
    assert state() == before
    assert present()


@pytest.mark.parametrize('entry', ['cs-sync', 'cs-async', 'setengine'])
@pytest.mark.parametrize('pred', [None, Ellipsis, '...'])
def test_reads_stay_lenient_about_the_bare_predicate(entry, pred):
    """Reads are lenient by contract (CLAUDE.md "Gotchas"): ``None`` still reads as the
    bare predicate. Guards against an over-eager TK125 fix that tightens ``norm_pred``
    (the shared READ normaliser) instead of the write path. And ``Ellipsis`` stays a
    legal WRITE form of the bare predicate."""
    write, _remove, _state, present = ENTRY_POINTS[entry]()
    write(Ellipsis, *GOOD[1:])
    assert present()
    cs_or_engine_check = write.__self__.check
    if entry == 'cs-async':
        write.__self__.catch_up()
    assert cs_or_engine_check(pred, *GOOD[1:]) is True
