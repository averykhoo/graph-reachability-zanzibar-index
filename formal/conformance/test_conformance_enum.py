"""Phase 6 extra — EXHAUSTIVE small-scope enumeration (FINAL_REVIEW §4(b)).

Replaces sampling with genuine exhaustion at tiny scope: for each of the six
representative fragment shapes below (plus one out-of-fragment shape, TK102),
enumerate ALL stores of up to K tuples
from the DECLARED tuple space (every write matching a direct restriction of a
declared relation — exactly the admission-valid writes) over a 2-names-per-type
pool, and for EVERY enumerated store compare, over the full shared query grid
(`grid.py`, computed once per shape from the full tuple space so all stores
share one grid):

    Lean spec `sem` (zcli)  ×  independent oracle  ×  real `SetEngine`
                            ×  real graph index (`WildcardIndex` + cascade)

THE DOCUMENTED BOUNDS (the §7 claim's "up to the documented bounds"):

    name pool   : user in {u1, u2}, doc in {d1, d2}, group in {g1, g2},
                  folder in {f1, f2}                 (2 names per type)
    K           : PER SHAPE (see "K per shape" below) — four shapes reach K=4
                  (all stores of size 0..4); the two largest tuple spaces stay
                  at K=3 for runtime (documented, never silent)
    shapes      : boolean_exclusion      —  8-tuple space, K=4, 163 stores
                  boolean_intersection   —  8-tuple space, K=4, 163 stores
                  two_stratum_cascade    — 12-tuple space, K=3, 299 stores
                  boolean_star_exclusion —  6-tuple space, K=4,  57 stores
                  wildcard_group_member  — 10-tuple space, K=3, 176 stores
                  ttu                    —  8-tuple space, K=4, 163 stores
                  derived_userset_subject — 16-tuple space, K=3, 697 stores
                                            (TK102, 2026-10-12c; OUTSIDE the
                                            fragment, ORBIT-REDUCED: spec +
                                            graph on 119 orbit representatives,
                                            oracle x set engine on all 697)
                  (total: 1718 stores enumerated, 1140 of them driven through
                  spec + graph; each shape's space, K, store count and, where
                  reduced, representative count is ASSERTED below so the
                  documented bound cannot silently drift)

The seventh shape (TK102, 2026-10-12c) is the first OUTSIDE W4Fragment: a
DERIVED relation (`member: allowed but not blocked`) as a stored userset
subject (`viewer: [user, group#member]`, `TK94`'s corpus). Two consequences,
both mechanical: its graph leg is a declared PYTHON-ONLY differential
(`_GRAPH_PY_DIFFERENTIAL` -- compared against the agreed answer, no Lean
claim), and its 16-tuple space is enumerated at K=3 with the expensive legs
quotiented by pool-name renaming (`_ORBIT_REDUCED`). Measured ~70-110 s on the
reference machine. Its sorted write order puts every `doc.viewer` tuple BEFORE
the `group` tuples, so the userset edge exists before the derived `member`
state it points at. The curated arms reach that interleaving only by
SAMPLING (`test_conformance_remove.py::_sequence` seeded-shuffles the
curated corpus and re-adds removed tuples, and goes red on the same S1
sabotage); this shape drives every store up to K=3 exhaustively.
Sizing, soundness argument and what the quotient gives up:
docs/tk102-derived-userset-enum-2026-10-12.md.

K per shape (widening §4(e) increment (b), 2026-07-18 — NO silent caps):

    Increment (b) widens the enumeration from a uniform K=3 to K=4. But
    increment (a) had already put the REAL graph index (a full SQL index build
    + cascade) inside the enumeration per store, so per-store cost roughly
    doubled; a naive all-shapes K=4 (1726 stores) blows the ~10-min conf-rest
    command cap. K is therefore PER SHAPE, chosen from measured runtime on the
    reference machine:

      * K=4 (reached):  boolean_exclusion, boolean_intersection,
                        boolean_star_exclusion, ttu.
      * K=3 (CAPPED):   two_stratum_cascade (12-tuple space — dominates: 794
                        stores and ~137 s at K=3 already, the single largest
                        leg) and wildcard_group_member (10-tuple space — 386
                        stores/~132 s at K=4, the next-largest). Both stay at
                        K=3.

    Why these two: at K=4 the enum module alone measured ~7.6 min (conf-rest
    ~9.2 min) with only two_stratum capped — too tight against the 10-min cap.
    Capping BOTH large shapes at K=3 brings the module to ~6.4 min (conf-rest
    ~7.9 min), restoring the ≥1-min margin the phase budget wants. This is the
    sanctioned lever: cap the two dominating tuple spaces, take the other four
    shapes to K=4 (they exercise every read branch — plain/star exclusion,
    intersection, TTU — at the wider depth). The capped shapes remain fully
    exhaustive at K=3; only their size-4 stratum is deferred.

The last two shapes (added 2026-07-18, widening §4(e) increment (c)) reach the
userset-subject and TTU read branches the four boolean shapes never touched:
`wildcard_group_member` (`viewer: [group#member]`) exercises userset subjects
plus the public `user:*` group member; `ttu` (`viewer: viewer from parent`)
exercises the tupleset-to-userset rewrite. The SELF-referential nested-group
schema `group_userset` (`member: [user, group#member]`) is DELIBERATELY NOT used
here: at K=3 it makes 132 of its 299 stores admission-INVALID for the set engine
(its userset-membership cycle guard, engine.py:770, rejects `g1#member member g1`
and the g1<->g2 2-cycle), which would break the "exhaustive over admission-valid
writes" premise. On the 167 acyclic stores spec/oracle/set engine agree exactly
(probed 2026-07-18) — the exclusion is an admission-domain difference, not a
check-semantics divergence.

ADMISSION SURVIVAL IS 100% HERE, BY CONSTRUCTION, SO THIS MODULE CARRIES NO
SURVIVAL FLOOR (TK71, 2026-09-27). Every enumerated store goes to
`backends.py::setengine_answers` and `::graphindex_drive`, and neither catches
anything around the write: a refused write RAISES and fails the test. Together
with the exact `len(space)` / `n_stores` pins below, a store cannot leave this
module without turning it red. The modules where a refusal IS absorbed (so an
over-reject would shrink them quietly) are `test_conformance_remove.py`
(`_EXPECTED_POISONED`, exact) and `test_conformance_generated.py` (0 refusals,
exact). Sabotage and map: docs/tk71-admission-survival-2026-09-27.md.

`_tuple_space` puts `"*"` only in the SUBJECT slot, and no shape here declares an
object-wildcard shape, so no store in this module holds a `T:*` object. Those stores
are enumerated by `test_conformance_enum_objstar.py` instead (`TK101`, hole H4), which
reuses `_tuple_space` for its concrete half.

Stores are SETS of tuples (Zanzibar raw tuples are a set; multiplicity is a
write-path concern outside `sem`), enumerated as sorted-space combinations, so
the enumeration is genuinely exhaustive and deterministic.

Scope notes (honest, not silent):
  * one zcli invocation per store — the request format carries ONE store per
    call (Cli.lean: a single `"tuples"` array), so batching happens at the
    query level (the full grid rides in each call). Runtime for the whole
    module is ~6.4 min on the reference machine (1021 stores over six shapes at
    the per-shape K above, including the graph leg; the zcli spec cache absorbs
    most of the per-shape cost), inside the conf-rest phase cap. TK102's
    seventh shape adds ~70-110 s (measured 2026-10-12c: 104.07 s, 69.74 s and
    108.76 s in three runs). Tiles are assigned by collection index mod K, so WHICH tile
    pays it moves whenever a node is added or removed anywhere earlier in the
    directory; no tile assignment is promised here (`verify.sh` usage: raise K
    when a tile approaches the ~600 s command cap).
  * the GRAPH side (the real `WildcardIndex` + `DeltaProcessor`, I5 leaf-
    routing + same-txn cascade) IS enumerated here as of §4(e) increment (a)
    (2026-07-18), over the per-shape K above: for every enumerated store whose
    shape is inside `GRAPH_FRAGMENT` (six of the seven shapes; the seventh
    runs the same leg as a declared Python-only differential, TK102) the real graph
    index `check` is
    compared, over the PROVED graph query scope (concrete objects, star
    subjects bare — `_graph_query_filter`), against the already-agreed
    `sem` (== oracle == set engine). This drives write-order / partial-store
    interleavings the curated corpora never reached — exactly the class of run
    that historically FOUND the P6 leaf-family and 2026-07-17 stale-fanout
    divergences. No zcli "graph" run is needed: the answer-level pin against
    `sem` covers it (the Lean graph model is pinned to `sem` by `graph_correct`
    and to the Python graph by `test_conformance_graph.py`). Adds ~a full SQL
    index build + cascade per store, but no second zcli call, so it stays in
    the conf-rest phase cap.
  * the per-shape K (above) is bounded by the conf-rest command cap, not by
    the combinatorial store count: even the K=4 shapes stay small (largest is
    163 stores); the caps on two_stratum_cascade / wildcard_group_member are
    purely a per-store runtime (graph-leg) budget, not a store-count blowup.
"""

from __future__ import annotations

import itertools

import pytest

from tests.oracle import (
    ODirect,
    OExclusion,
    OIntersection,
    OUnion,
    Oracle,
    parse_schema_ast,
    t as mk_tuple,
)

from formal.conformance import runner
from formal.conformance.backends import setengine_answers, graphindex_answers
from formal.conformance.corpus import SCHEMAS, GRAPH_FRAGMENT
from formal.conformance.encode import build_request
from formal.conformance.grid import grid as _grid, fmt_mismatches as _fmt

_POOL: dict[str, tuple[str, ...]] = {
    "user": ("u1", "u2"), "doc": ("d1", "d2"),
    "group": ("g1", "g2"), "folder": ("f1", "f2"),
}

# shape -> (tuple-space size, PER-SHAPE enumeration depth K, store count at K) —
# all three asserted, so neither the documented bounds nor the per-shape K can
# silently drift from the code. K is PER-SHAPE (widening §4(e) increment (b),
# 2026-07-18): four shapes reach K=4; the two largest tuple spaces stay at K=3
# because the graph leg (increment (a)) makes a naive all-shapes K=4 blow the
# ~10-min conf-rest command cap. See the module docstring's "K per shape" block
# for the measured runtime rationale — no cap is silent.
_SHAPES: dict[str, tuple[int, int, int]] = {
    "boolean_exclusion": (8, 4, 163),
    "boolean_intersection": (8, 4, 163),
    "two_stratum_cascade": (12, 3, 299),      # CAPPED K=3 (12-tuple space)
    "boolean_star_exclusion": (6, 4, 57),
    # userset-subject + TTU read branches (widening §4(e) increment (c),
    # 2026-07-18). Both are acyclic under the pool — no admission-cycle skips,
    # spec == oracle == set engine on every enumerated store.
    "wildcard_group_member": (10, 3, 176),    # CAPPED K=3 (10-tuple space)
    "ttu": (8, 4, 163),
    # A DERIVED relation as a stored userset subject (`TK102`, 2026-10-12c;
    # the corpus is `TK94`'s). CAPPED K=3 (16-tuple space; K=4 is 2517
    # stores) and ORBIT-REDUCED in its expensive legs -- see `_ORBIT_REDUCED`
    # and docs/tk102-derived-userset-enum-2026-10-12.md. Outside W4Fragment,
    # so its graph leg is a declared Python-only differential
    # (`_GRAPH_PY_DIFFERENTIAL`), never a GRAPH_FRAGMENT entry.
    "derived_userset_subject": (16, 3, 697),  # CAPPED K=3 (16-tuple space)
}

# Shapes whose GRAPH leg runs as a PYTHON-ONLY differential (`TK102`,
# 2026-10-12c): the real graph index is compared against the already-agreed
# `sem == oracle == set engine` answer, but the shape is OUTSIDE W4Fragment, so
# no theorem routed through `graph_correct` covers it and NO Lean claim is made
# (the licence `test_conformance_remove.py`'s graph legs already use: "Scope:
# sem/Lean deferred"). Adding such a name to `GRAPH_FRAGMENT` instead would be
# the ZT-P3-3 mistake (`TK94` doc sec. 3). Every `_SHAPES` name must sit in
# EXACTLY ONE of `GRAPH_FRAGMENT` and this set
# (`test_every_shape_declares_its_graph_leg`), so the graph leg can no longer be
# skipped silently by a shape that is in neither. `test_conformance_enum_state`
# (which compares against the LEAN graph model) excludes exactly this set.
_GRAPH_PY_DIFFERENTIAL: frozenset[str] = frozenset({"derived_userset_subject"})

# Shapes whose EXPENSIVE legs (zcli spec + real graph index, ~0.72 s/store of
# the ~0.76 s total) run on ONE REPRESENTATIVE PER ORBIT under renaming of the
# pool names, while the cheap legs (oracle x set engine) still run on EVERY
# enumerated store. name -> number of orbit representatives at the shape's K,
# ASSERTED. Sound because `sem` names entities only by equality, so checking
# the full grid on `S` checks it on every renaming of `S` -- PROVIDED the tuple
# space and the grid are closed under renaming, which the test asserts before
# reducing anything (`_assert_renaming_closed`). What it gives up: a
# NAME-DEPENDENT bug in the graph index or zcli (one that fires for g2 but not
# g1) is checked on one orbit member only. Measured 2026-10-12c: 697 stores ->
# 119 orbits at K=3 (397 at K=4). docs/tk102-derived-userset-enum-2026-10-12.md.
# It ALSO gives up WRITE-ORDER variants (added 2026-10-12c after review,
# figure corrected the same day after a second review): the graph index is
# incremental, so its answer may depend on the order tuples are written, and the
# quotient is NOT order-equivariant. Every store is written in sorted-space
# order, and the graph sees only its representative's sequence; by
# name-equivariance that covers every RENAMING of that sequence. A store whose
# own sorted write sequence is no renaming of its representative's is therefore
# never driven through the graph in its own order (only its order-blind
# oracle x set-engine answers are). Measured 2026-10-12c: 116 of the 697 stores,
# falling into 44 write-sequence classes (up to renaming) beyond the 119 the
# representatives drive (163 classes in all). Pinned by
# `test_orbit_reduction_write_order_cost_is_pinned` (`_ORBIT_ORDER_UNDRIVEN`).
_ORBIT_REDUCED: dict[str, int] = {"derived_userset_subject": 119}

# Per `_ORBIT_REDUCED` shape: (stores whose own write sequence the quotient does
# not drive, write-sequence classes up to renaming that no representative
# drives) -- see the comment above. ASSERTED, and every reduced shape must state
# its figures, so the cost cannot be added silently.
_ORBIT_ORDER_UNDRIVEN: dict[str, tuple[int, int]] = {
    "derived_userset_subject": (116, 44)}


def _pool_renamings() -> list[dict[tuple[str, str], str]]:
    """Every renaming of `_POOL` names that permutes names WITHIN each type
    (16 = 2!^4 renamings, identity first). `"*"` and grid ghost names are not in
    the pool, so every renaming fixes them."""
    types = sorted(_POOL)
    return [
        {(ty, a): b for ty, perm in zip(types, choice)
         for a, b in zip(_POOL[ty], perm)}
        for choice in itertools.product(
            *(itertools.permutations(_POOL[ty]) for ty in types))
    ]


def _rename_q(q, ren):
    """Rename the subject and object names of a 6-field query/tuple key."""
    sp, st, sn, rel, ot, on = q
    return (sp, st, ren.get((st, sn), sn), rel, ot, ren.get((ot, on), on))


def _tkey(tup):
    return (str(tup.subject_predicate), tup.subject_type, tup.subject_name,
            tup.relation, tup.object_type, tup.object_name)


def _orbit_key(store, renamings):
    """Canonical key of a store's orbit: the least sorted renamed key list."""
    keys = [_tkey(t) for t in store]
    return min(tuple(sorted(_rename_q(k, r) for k in keys))
               for r in renamings)


def _assert_renaming_closed(name, space, queries, renamings):
    """The precondition of the orbit reduction: every renaming maps the tuple
    space onto itself AND the query grid onto itself. Without the second, a
    query the representative is asked could have no counterpart on another
    orbit member (or vice versa), and the quotient would silently drop it."""
    sp_keys = {_tkey(t) for t in space}
    q_set = set(queries)
    for r in renamings:
        assert {_rename_q(k, r) for k in sp_keys} == sp_keys, (
            f"[{name}] tuple space not closed under pool renaming {r}: the "
            f"orbit reduction would be unsound")
        assert {_rename_q(q, r) for q in q_set} == q_set, (
            f"[{name}] query grid not closed under pool renaming {r}: the "
            f"orbit reduction would be unsound")


def _direct_restrictions(expr):
    """All `(type, predicate, wildcard)` Direct restrictions in a def (the
    admission-valid write shapes for its relation)."""
    if isinstance(expr, ODirect):
        return list(expr.restrictions)
    if isinstance(expr, (OUnion, OIntersection)):
        return [r for c in expr.children for r in _direct_restrictions(c)]
    if isinstance(expr, OExclusion):
        return (_direct_restrictions(expr.base)
                + _direct_restrictions(expr.subtract))
    return []  # OComputed / OTTU: no direct write surface


def _tuple_space(schema_text: str) -> list:
    """The declared tuple space over `_POOL`: for every declared relation and
    every Direct restriction, all admission-valid tuples with pool names."""
    ast = parse_schema_ast(schema_text)  # {(type, relation): OExpr}
    space = []
    for (ty, rel) in sorted(ast):
        for (rt, rp, wild) in _direct_restrictions(ast[(ty, rel)]):
            for on in _POOL.get(ty, ()):
                if wild:
                    space.append(mk_tuple(rp, rt, "*", rel, ty, on))
                else:
                    for sn in _POOL.get(rt, ()):
                        space.append(mk_tuple(rp, rt, sn, rel, ty, on))
    return space


def _all_stores(space: list, k: int):
    """Every store (tuple SET) of size 0..k, deterministically ordered."""
    for size in range(k + 1):
        yield from itertools.combinations(space, size)


def _graph_query_filter(subjects, targets):
    """Restrict the shared grid to the PROVED graph query scope (mirrors
    `test_conformance_graph._graph_queries_for`): concrete objects only
    (`hqo : q.object.name != STAR`); star subjects stay, since the grid emits
    them bare-predicate only (userset subjects are concrete-named), satisfying
    `hqs` (`graphRun_check_eq_sem`, GraphIndex/Exec.lean)."""
    targets = [(rel, ot, on) for (rel, ot, on) in targets if on != "*"]
    return [
        (sp, st, sn, rel, ot, on)
        for (sp, st, sn), (rel, ot, on) in itertools.product(subjects, targets)
    ]


@pytest.mark.parametrize("name", sorted(_SHAPES))
def test_exhaustive_small_scope(name):
    """spec == oracle == set engine on EVERY store up to the documented bound.

    (For an `_ORBIT_REDUCED` shape: oracle == set engine on every store, spec
    and graph on one representative per renaming orbit.)

    SABOTAGE RECORD for the TK102 shape (2026-10-12c, each mutation restored
    byte-exact from a temp copy and checked with `git diff`; literal output):
      * S1, the subject: `graphindex/core.py::_add_direct_edge_unsafe_impl`
        made to drop the object's descendants when the delta processor adds a
        derived edge (a derived `member` edge then never reaches a `doc#viewer`
        through an EXISTING userset edge) -> `[derived_userset_subject]
        graph/spec disagreement (... PYTHON-ONLY differential, no Lean claim
        ...) at enumerated store #75 = [g1#member viewer d1, u1 allowed g1]:
        [(('...', 'user', 'u1', 'viewer', 'doc', 'd1'), True, False)]`, 1
        failed in 14.61s. The SIX pre-existing shapes stayed GREEN under the
        same mutation (`7 passed, 1 deselected in 476.60s`), so within this
        module only the new shape sees it (re-run by review 2 in an isolated
        copy with S1 reconstructed: `6 passed, 3 deselected in 569.29s`).
        (TK94's remove-arm graph legs for
        the same corpus also go red on it: `3 failed, 2 passed`.)
      * S2, the skip it replaces: `run_graph = name in GRAPH_FRAGMENT` ->
        `graph leg ran on 0 of 119 driven stores over 0 queries`, 30.78s.
      * S4, the reduction's precondition: `grid._USERSET_NAME_BOUND = 1` ->
        `query grid not closed under pool renaming {... ('group', 'g1'): 'g2'
        ...}: the orbit reduction would be unsound`, 0.83s.
      * S5, an over-coarse orbit key (subject name dropped from `_orbit_key`)
        -> `drove 61 stores through spec + graph but the documented count is
        119 (orbit representatives)`, 49.28s.
      * S11, the cheap leg on the 578 non-representatives skipped (a bare
        `continue` first in that branch) -> `[derived_userset_subject]
        oracle x set-engine compared on 0 of the 578 stores the orbit
        quotient did not drive`, 1 failed in 100.11s. LIMIT: the
        `n_cheap_only` counter proves the branch is reached, not that its
        assert is live -- a skip that keeps the increment stayed GREEN
        (`1 passed in 107.04s`), and so does `assert True or not mism`.
    """
    schema_text, _corpus_tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    space = _tuple_space(schema_text)
    exp_space, k, exp_stores = _SHAPES[name]
    assert len(space) == exp_space, (
        f"[{name}] declared tuple space drifted: {len(space)} tuples "
        f"(documented bound says {exp_space}) — update the documented bounds "
        f"deliberately, never silently")

    # ONE grid per shape, derived from the full space, shared by every store.
    subjects, targets = _grid(schema_text, space)
    queries = [
        (sp, st, sn, rel, ot, on)
        for (sp, st, sn), (rel, ot, on) in itertools.product(subjects, targets)
    ]

    # Graph leg (widening §4(e) increment (a)): exhaustively drive the REAL
    # graph index (WildcardIndex + DeltaProcessor, I5 leaf-routing + cascade)
    # over EVERY enumerated store, compared at ANSWER level against the already-
    # agreed spec (== oracle == set engine). Gated to shapes inside
    # GRAPH_FRAGMENT (apples-to-apples with graph_correct); six of the seven enum
    # shapes qualify, the seventh is the declared Python-only differential below. Query scope narrowed to the PROVED graph scope (`_graph_query_
    # filter`); graph_queries is a subset of `queries`, so the spec answers
    # computed above are the reference (no extra zcli call).
    # A shape outside GRAPH_FRAGMENT runs the graph leg only if DECLARED as a
    # Python-only differential (`_GRAPH_PY_DIFFERENTIAL`, TK102); the label
    # below keeps its failure message from claiming a Lean-backed result.
    py_only = name in _GRAPH_PY_DIFFERENTIAL
    run_graph = name in GRAPH_FRAGMENT or py_only
    graph_queries = _graph_query_filter(subjects, targets) if run_graph else []

    # Orbit reduction of the expensive legs (TK102): see `_ORBIT_REDUCED`.
    reduce_orbits = name in _ORBIT_REDUCED
    renamings = _pool_renamings() if reduce_orbits else []
    if reduce_orbits:
        _assert_renaming_closed(name, space, queries, renamings)
    seen_orbits: set = set()

    n_stores = n_driven = n_graph = n_cheap_only = 0
    for store in _all_stores(space, k):
        n_stores += 1
        store = list(store)
        oracle = Oracle(schema_text, store)
        orc = [oracle.check(*q) for q in queries]
        se = setengine_answers(schema_text, store, queries, obj_wild)

        if reduce_orbits:
            okey = _orbit_key(store, renamings)
            if okey in seen_orbits:
                # Not its orbit's representative: the cheap legs only (the
                # expensive ones ran on the representative, sound by
                # `_assert_renaming_closed` + name-equivariance of `sem`).
                mism = [(queries[i], orc[i], se[i])
                        for i in range(len(queries)) if orc[i] != se[i]]
                assert not mism, (
                    f"[{name}] oracle/set-engine disagreement (ADJUDICATION "
                    f"EVENT -- plan §8.2) at enumerated store #{n_stores} = "
                    f"{store}:\n{_fmt(mism, 'oracle', 'setengine')}")
                n_cheap_only += 1
                continue
            seen_orbits.add(okey)

        n_driven += 1
        spec = runner.run_spec(build_request(schema_text, store, queries,
                                             obj_wild))

        mism = [(queries[i], spec[i], orc[i]) for i in range(len(queries))
                if spec[i] != orc[i]]
        assert not mism, (
            f"[{name}] spec/oracle disagreement (ADJUDICATION EVENT — plan "
            f"§8.2) at enumerated store #{n_stores} = {store}:\n"
            f"{_fmt(mism, 'spec', 'oracle')}")
        mism = [(queries[i], spec[i], se[i]) for i in range(len(queries))
                if spec[i] != se[i]]
        assert not mism, (
            f"[{name}] spec/set-engine disagreement (ADJUDICATION EVENT — "
            f"plan §8.2) at enumerated store #{n_stores} = {store}:\n"
            f"{_fmt(mism, 'spec', 'setengine')}")

        if run_graph:
            n_graph += 1
            ref = {q: spec[i] for i, q in enumerate(queries)}  # spec == agreed
            graph = graphindex_answers(schema_text, store, graph_queries,
                                       obj_wild)
            mism = [(graph_queries[i], ref[graph_queries[i]], graph[i])
                    for i in range(len(graph_queries))
                    if ref[graph_queries[i]] != graph[i]]
            scope = ("PYTHON-ONLY differential, no Lean claim: shape outside "
                     "W4Fragment -- fix the Python" if py_only
                     else "graph check != sem == oracle == set engine")
            assert not mism, (
                f"[{name}] graph/spec disagreement (ADJUDICATION EVENT — plan "
                f"§8.2; {scope}) at "
                f"enumerated store #{n_stores} = {store}:\n"
                f"{_fmt(mism, 'spec', 'graph')}")

    assert n_stores == exp_stores, (
        f"[{name}] enumerated {n_stores} stores but the documented bound says "
        f"{exp_stores} — the enumeration or the docstring drifted")
    exp_driven = _ORBIT_REDUCED.get(name, exp_stores)
    assert n_driven == exp_driven, (
        f"[{name}] drove {n_driven} stores through spec + graph but the "
        f"documented count is {exp_driven} ("
        f"{'orbit representatives' if reduce_orbits else 'every store'}) — "
        f"the orbit reduction or `_ORBIT_REDUCED` drifted")
    # Every store the quotient did NOT drive still ran the oracle x set-engine
    # comparison (TK102 review 2: nothing counted that branch before).
    assert n_cheap_only == n_stores - n_driven, (
        f"[{name}] oracle x set-engine compared on {n_cheap_only} of the "
        f"{n_stores - n_driven} stores the orbit quotient did not drive")
    # The graph leg ran on every driven store, never silently skipped (TK102).
    assert n_graph == n_driven and graph_queries, (
        f"[{name}] graph leg ran on {n_graph} of {n_driven} driven stores "
        f"over {len(graph_queries)} queries — a shape in `_SHAPES` must run "
        f"its graph leg (see `test_every_shape_declares_its_graph_leg`)")


def test_every_shape_declares_its_graph_leg():
    """Every `_SHAPES` name runs the graph leg under EXACTLY ONE declared scope:
    Lean-backed (`GRAPH_FRAGMENT`) or a Python-only differential
    (`_GRAPH_PY_DIFFERENTIAL`). Before TK102 the leg was gated on
    `name in GRAPH_FRAGMENT` alone, so an out-of-fragment shape would have
    SKIPPED the graph silently (the row's 2026-10-04g note). The reduction
    bookkeeping is pinned here too: `_ORBIT_REDUCED` names only `_SHAPES`
    entries, and a representative count can never exceed its store count.

    SABOTAGE (2026-10-12c, S3): `_GRAPH_PY_DIFFERENTIAL = frozenset()` ->
    `['derived_userset_subject'] in `_SHAPES` but in neither GRAPH_FRAGMENT nor
    `_GRAPH_PY_DIFFERENTIAL`: its graph leg has no declared scope`, 1 failed in
    0.84s. Restored byte-exact."""
    shapes, frag = set(_SHAPES), set(GRAPH_FRAGMENT)
    assert not (_GRAPH_PY_DIFFERENTIAL & frag), (
        f"{sorted(_GRAPH_PY_DIFFERENTIAL & frag)} declared Python-only but in "
        f"GRAPH_FRAGMENT: pick one scope")
    assert _GRAPH_PY_DIFFERENTIAL <= shapes, (
        f"{sorted(_GRAPH_PY_DIFFERENTIAL - shapes)} declared Python-only but "
        f"not enumerated in `_SHAPES`")
    undeclared = shapes - frag - _GRAPH_PY_DIFFERENTIAL
    assert not undeclared, (
        f"{sorted(undeclared)} in `_SHAPES` but in neither GRAPH_FRAGMENT nor "
        f"`_GRAPH_PY_DIFFERENTIAL`: its graph leg has no declared scope")
    assert set(_ORBIT_REDUCED) <= shapes, sorted(set(_ORBIT_REDUCED) - shapes)
    for n, reps in _ORBIT_REDUCED.items():
        assert 0 < reps <= _SHAPES[n][2], (n, reps, _SHAPES[n])


def test_orbit_reduction_write_order_cost_is_pinned():
    """The orbit quotient's SECOND cost, measured and pinned (TK102 review,
    2026-10-12c; metric corrected after the second review the same day).

    Every enumerated store is written in sorted-space order. The graph leg runs
    on each orbit's REPRESENTATIVE (the first store of its orbit in enumeration
    order, exactly as `test_exhaustive_small_scope` picks it), and by name-
    equivariance its drive covers every RENAMING of the representative's write
    sequence. A store is UNDRIVEN when its own write sequence is none of those:
    the graph index is incremental, so that order was never exercised. Pinned
    per shape: the undriven STORE count, and the number of write-sequence
    classes (up to renaming) no representative drives. The identity
    `classes == representatives + undriven classes` is asserted too, so the
    orbit key and the representative choice cannot drift apart. No zcli, no
    graph index: pure bookkeeping, under a second.

    Correction (2026-10-12c): the first version pinned 328, counting stores
    for which SOME renaming permutes their sorted order. That set includes 68
    of the 119 representatives, whose order IS driven, so the label "write
    order the quotient does not drive" was false; the true figure is 116.
    Independent cross-check: the reviewer's probe
    (`.scratch/uc-2026-10-12c/tk102-review2/order_gap.py`) printed `stores
    whose own sorted write order is NOT a renaming of its rep drive: 116` and
    `sequence classes up to renaming: 163` (163 - 119 = 44).

    SABOTAGE (2026-10-12c, each restored byte-exact from a temp copy, `cmp`):
      * S7A, the pin: (116, 44) -> (117, 44) -> `[derived_userset_subject]
        116 of 697 stores have a write sequence the orbit quotient never
        drives through the graph (44 sequence classes up to renaming), but
        `_ORBIT_ORDER_UNDRIVEN` says (117, 44) ...`, 1 failed in 0.90s.
      * S7B, the instrument: `renamings = _pool_renamings()[:1]` (identity
        only) -> `('derived_userset_subject', 697, 119)`, 1 failed in 0.86s.
      * S7C, the equivariance closure dropped (`driven.add(seq)` instead of
        every renaming of it) -> `163 write-sequence classes != 119
        representatives + 158 undriven classes: the orbit key and the
        representative choice disagree`, 1 failed in 1.14s.
      * S7D, every store counted as driven (`if True:` in the representative
        choice) -> `163 write-sequence classes != 119 representatives + 0
        undriven classes ...`, 1 failed in 0.88s."""
    assert set(_ORBIT_ORDER_UNDRIVEN) == set(_ORBIT_REDUCED), (
        f"every `_ORBIT_REDUCED` shape must state its write-order cost in "
        f"`_ORBIT_ORDER_UNDRIVEN` (and only those): "
        f"{sorted(set(_ORBIT_ORDER_UNDRIVEN) ^ set(_ORBIT_REDUCED))}")
    renamings = _pool_renamings()
    for name, (exp_stores, exp_classes) in sorted(_ORBIT_ORDER_UNDRIVEN.items()):
        space = _tuple_space(SCHEMAS[name][0])
        rep_seq: dict = {}          # orbit key -> representative's write sequence
        driven: set = set()         # every renaming of every rep's sequence
        seqs: list = []
        for store in _all_stores(space, _SHAPES[name][1]):
            seq = tuple(_tkey(t) for t in store)   # the order it is written in
            seqs.append(seq)
            okey = _orbit_key(store, renamings)
            if okey not in rep_seq:                # first of its orbit = the rep
                rep_seq[okey] = seq
                driven.update(tuple(_rename_q(k, r) for k in seq)
                              for r in renamings)

        def seq_class(s):
            return min(tuple(_rename_q(k, r) for k in s) for r in renamings)

        undriven = [s for s in seqs if s not in driven]
        all_classes = {seq_class(s) for s in seqs}
        undriven_classes = {seq_class(s) for s in undriven}
        assert len(seqs) == _SHAPES[name][2], (name, len(seqs), _SHAPES[name])
        assert len(rep_seq) == _ORBIT_REDUCED[name], (
            name, len(rep_seq), _ORBIT_REDUCED[name])
        assert len(all_classes) == len(rep_seq) + len(undriven_classes), (
            f"[{name}] {len(all_classes)} write-sequence classes != "
            f"{len(rep_seq)} representatives + {len(undriven_classes)} "
            f"undriven classes: the orbit key and the representative choice "
            f"disagree")
        got = (len(undriven), len(undriven_classes))
        assert got == (exp_stores, exp_classes), (
            f"[{name}] {got[0]} of {len(seqs)} stores have a write sequence the "
            f"orbit quotient never drives through the graph ({got[1]} sequence "
            f"classes up to renaming), but `_ORBIT_ORDER_UNDRIVEN` says "
            f"{(exp_stores, exp_classes)} -- re-measure and update the figures "
            f"and their carriers (the `_ORBIT_REDUCED` comment, ARCHITECTURE / "
            f"FINAL_REVIEW / CORRESPONDENCE enum rows, the TK102 doc) "
            f"deliberately")
