"""
Test helpers for the wildcard façade: an invariant checker (spec §8.3) and a
row-multiset snapshot for the GC parity test (§7.3 / §8.2).

The checker logic itself moved to ``index_v4.invariants`` (boolean spec P1) so that
paranoia mode can run it pre/post-commit in production wiring; these helpers keep the
original test-facing API and semantics.
"""

from collections import Counter

from sqlmodel import Session, create_engine, SQLModel

from index_v4 import ReachabilityIndex, Store, WildcardIndex
from index_v4.invariants import check_invariants, install_paranoia, snapshot_rows
from zanzibar_utils_v1 import SchemaInfo


def make_wildcard_index(schema_info: SchemaInfo, store_id: str = 'test', *,
                        paranoia: bool = True) -> tuple[Session, WildcardIndex]:
    """Fresh in-memory store + WildcardIndex.

    Paranoia mode (boolean spec §8.1) is ON by default while prerelease: the invariant
    checker runs inside every commit (violation ⇒ raise ⇒ abort) and again post-commit
    in a fresh session. Pass ``paranoia=False`` for benchmarks.
    """
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Store(id=store_id))
    session.commit()
    idx = ReachabilityIndex(session, store_id=store_id)
    if paranoia:
        install_paranoia(session, store_id, schema_info)
    return session, WildcardIndex(idx, schema_info)


# ---------------------------------------------------------------------------
# Invariant checker (§8.3) -- now backed by index_v4.invariants
# ---------------------------------------------------------------------------

def assert_wildcard_invariants(widx: WildcardIndex) -> None:
    check_invariants(widx.idx.session, widx.idx.store_id, widx.schema_info)


# ---------------------------------------------------------------------------
# Row-multiset snapshot for GC parity (§8.2 test_bridge_gc_restores_clean_state)
# ---------------------------------------------------------------------------

def snapshot(widx: WildcardIndex) -> tuple[Counter, Counter]:
    """Return (node_rows, edge_rows) as id-independent multisets, so two stores that
    reach the same logical state compare equal."""
    return snapshot_rows(widx.idx.session, widx.idx.store_id)
