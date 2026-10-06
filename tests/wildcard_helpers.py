"""
Test helpers for the wildcard façade: an invariant checker (spec §8.3) and a
row-multiset snapshot for the GC parity test (§7.3 / §8.2).

The checker logic itself moved to ``zanzibar.graphindex.invariants`` (boolean spec P1) so that
paranoia mode can run it pre/post-commit in production wiring; these helpers keep the
original test-facing API and semantics.
"""

from collections import Counter
from contextlib import contextmanager

from sqlmodel import Session, create_engine, SQLModel

from zanzibar.graphindex import ReachabilityIndex, Store, WildcardIndex
from zanzibar.graphindex.invariants import check_invariants, install_paranoia, snapshot_rows
from zanzibar.schema import SchemaInfo


def make_wildcard_index(schema_info: SchemaInfo, store_id: str = 'test', *,
                        paranoia: 'bool | str' = True) -> tuple[Session, WildcardIndex]:
    """Fresh in-memory store + WildcardIndex.

    Paranoia mode (boolean spec §8.1) is ON by default while prerelease: the invariant
    checker runs inside every commit (violation ⇒ raise ⇒ abort) and again post-commit
    in a fresh session. Pass ``paranoia=False`` for benchmarks.

    ``paranoia`` takes anything ``normalize_paranoia_level`` takes -- ``True``/``False``
    (the historical flag, = ``'full'``/``'off'``) or a tier name ``'off'`` / ``'residue'``
    / ``'full'``. **The level is FORWARDED**; it used to be dropped, which made every
    non-empty string truthy and installed ``'full'``, so ``paranoia='off'`` silently
    installed the strongest checker there is and a three-tier sweep written against this
    helper actually ran off/full/full. Pinned by
    ``tests/test_paranoia_wiring.py::test_helper_forwards_the_tier`` and
    ``::test_helper_rejects_a_typod_tier`` (TK74, 2026-09-18b).
    """
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Store(id=store_id))
    session.commit()
    idx = ReachabilityIndex(session, store_id=store_id)
    install_paranoia(session, store_id, schema_info, level=paranoia)
    return session, WildcardIndex(idx, schema_info)


# ---------------------------------------------------------------------------
# Invariant checker (§8.3) -- now backed by zanzibar.graphindex.invariants
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


# ---------------------------------------------------------------------------
# I14 crossing-middle reach instrument (TK77)
# ---------------------------------------------------------------------------

class MiddleSyncRecord:
    """The `(entity_type, entity_name)` argument of every ``_sync_entity_middles``
    call made on one façade, plus the EFFECTIVE subset.

    ⚠ **A RAW count is not reach.** ``WildcardIndex._sync_entity_middles`` is called
    UNCONDITIONALLY -- from ``::remove_edge`` (both endpoints), from ``::remove_node``,
    and from ``src/zanzibar/graphindex/processor.py`` -- and returns at a guard when the schema has no
    crossable shape of that entity's type, so a corpus with an empty
    ``SchemaInfo.crossable_shapes`` still books hundreds of calls that do nothing. The
    census measured **7408 raw vs 257 effective** across seven modules
    (`docs/tk77-crossable-census-2026-09-19.md` §6, MEASURED 2026-09-19c); reading raw
    as reach inverts its whole table.

    ``effective`` is the census's EFFECTIVE definition, computed from the façade's own
    ``schema_info``: a call naming a CONCRETE entity of a type that carries a crossable
    shape. That is a claim about the call, not about the callee's control flow -- so it
    stays true if the guard inside ``_sync_entity_middles`` is ever restructured.
    """

    def __init__(self, schema_info: SchemaInfo):
        self._crossable_types = frozenset(t for (t, _p) in schema_info.crossable_shapes)
        self.raw: list[tuple[str, str]] = []

    @property
    def effective(self) -> list[tuple[str, str]]:
        return [(t, n) for (t, n) in self.raw
                if n != '*' and t in self._crossable_types]


@contextmanager
def record_middle_syncs(widx: WildcardIndex):
    """Record ``_sync_entity_middles`` calls on ``widx`` for the duration (TK77).

    Patches the INSTANCE attribute, so ``self.widx._sync_entity_middles(...)`` from
    ``src/zanzibar/graphindex/processor.py`` is recorded too; restored on exit.
    """
    rec = MiddleSyncRecord(widx.schema_info)
    original = widx._sync_entity_middles

    def wrapper(entity_type: str, name: str) -> None:
        rec.raw.append((entity_type, name))
        return original(entity_type, name)

    widx._sync_entity_middles = wrapper
    try:
        yield rec
    finally:
        del widx._sync_entity_middles
