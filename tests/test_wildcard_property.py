"""
Property test (spec §8.4): fixed-seed randomized add/remove sequences over a small
universe, comparing WildcardIndex.check against the reference oracle for the FULL
query grid after every operation, with the invariant checker run each step.

The index is fed DERIVED tuples (via RuleSet.apply); the oracle is fed the RAW input
tuples and does its own expansion. Agreement across the whole grid is the correctness
gate for the entire design.
"""

import random
from types import EllipsisType

import pytest

from zanzibar.graphindex.outbox import outbox_watermark
from zanzibar.graphindex.processor import DeltaProcessor
from zanzibar.schema import Entity, RelationalTriple, parse_openfga_schema
from tests.oracle import Oracle, OracleTuple
from tests.wildcard_helpers import (make_wildcard_index, assert_wildcard_invariants,
                                    record_middle_syncs)


WILDCARDS_SCHEMA = None  # loaded from fixture in the test


OBJECT_WC = frozenset({('folder', 'viewer'), ('document', 'viewer')})

USERS = ['u1', 'u2']
GROUPS = ['g1', 'g2']
FOLDERS = ['f1', 'f2']
DOCS = ['d1', 'd2']
GHOST = {'user': 'ghostU', 'group': 'ghostG', 'folder': 'ghostF', 'document': 'ghostD'}


def _norm(pred: str | EllipsisType) -> str:
    return '...' if pred is Ellipsis else pred


def _candidate_raw_tuples() -> list[tuple]:
    """All schema-valid raw tuples over the small universe (6-string tuples)."""
    out = []
    viewer_objects = [('folder', f) for f in FOLDERS] + [('document', d) for d in DOCS]
    # object wildcards are valid only for the declared (folder,viewer)/(document,viewer)
    viewer_objects_wc = viewer_objects + [('folder', '*'), ('document', '*')]

    # membership: [user] and [group#member]
    for u in USERS:
        for g in GROUPS:
            out.append(('...', 'user', u, 'member', 'group', g))
    for gi in GROUPS:
        for gj in GROUPS:
            if gi != gj:
                out.append(('member', 'group', gi, 'member', 'group', gj))

    # viewer grants: [user, user:*, group#member, group:*#member] + object wildcards
    for (o_type, o_name) in viewer_objects_wc:
        for u in USERS:
            out.append(('...', 'user', u, 'viewer', o_type, o_name))
        out.append(('...', 'user', '*', 'viewer', o_type, o_name))
        for g in GROUPS:
            out.append(('member', 'group', g, 'viewer', o_type, o_name))
        out.append(('member', 'group', '*', 'viewer', o_type, o_name))

    # parent hierarchy: [folder]
    for fi in FOLDERS:
        for fj in FOLDERS:
            if fi != fj:
                out.append(('...', 'folder', fi, 'parent', 'folder', fj))
    for f in FOLDERS:
        for d in DOCS:
            out.append(('...', 'folder', f, 'parent', 'document', d))
    return out


def _query_grid() -> list[tuple]:
    """(s_pred, s_type, s_name, relation, o_type, o_name) queries.

    Kept intentionally small (spec §8.4, <5s CI budget). Each type contributes a
    concrete, a ghost, and the wildcard name so every probe path is exercised; the
    from-chain is covered by a folder-viewer userset subject.
    """
    subjects = [
        ('...', 'user', 'u1'), ('...', 'user', GHOST['user']), ('...', 'user', '*'),
        ('member', 'group', 'g1'), ('member', 'group', GHOST['group']), ('member', 'group', '*'),
        ('viewer', 'folder', 'f1'),                     # userset subject (from-chain)
    ]
    targets = [
        ('viewer', 'folder', 'f1'), ('viewer', 'folder', GHOST['folder']), ('viewer', 'folder', '*'),
        ('viewer', 'document', 'd1'), ('viewer', 'document', GHOST['document']), ('viewer', 'document', '*'),
        ('member', 'group', 'g1'), ('member', 'group', '*'),
    ]
    return [(sp, st, sn, rel, ot, on)
            for (sp, st, sn) in subjects
            for (rel, ot, on) in targets]


def _raw_to_triple(raw: tuple) -> RelationalTriple:
    s_pred = Ellipsis if raw[0] == '...' else raw[0]
    return RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), s_pred)


def _apply(widx, ruleset, raw, op):
    """Apply an add/remove of a raw tuple through the ruleset to the façade."""
    fn = widx.add_tuple if op == 'add' else widx.remove_tuple
    for d in ruleset.apply(_raw_to_triple(raw)):
        fn(_norm(d.subject_predicate), d.subject.type, d.subject.name,
           d.relation, d.object.type, d.object.name)


@pytest.mark.parametrize('seed', [0, 1, 2])
def test_wildcard_property_vs_oracle(load_fga_schema, seed):
    schema = load_fga_schema('wildcards.fga')
    ruleset = parse_openfga_schema(schema, object_wildcard_shapes=OBJECT_WC)
    session, widx = make_wildcard_index(ruleset.schema_info)

    pool = _candidate_raw_tuples()
    grid = _query_grid()
    rng = random.Random(seed)

    present: set[tuple] = set()
    history: list[tuple] = []

    def fail(msg, query=None):
        lines = [msg, f'seed={seed}', 'history:']
        lines += [f'  {op} {raw}' for (op, raw) in history]
        if query is not None:
            lines.append(f'failing query: {query}')
        pytest.fail('\n'.join(lines))

    STEPS = 12
    for _ in range(STEPS):
        # choose op
        if not present or rng.random() < 0.6:
            candidates = [r for r in pool if r not in present]
            if not candidates:
                op, raw = 'remove', rng.choice(sorted(present))
            else:
                op, raw = 'add', rng.choice(candidates)
        else:
            op, raw = 'remove', rng.choice(sorted(present))

        try:
            _apply(widx, ruleset, raw, op)
            session.commit()
        except ValueError:
            # invalid or cycle-forming tuple: roll back this op, leave state unchanged
            session.rollback()
            continue

        if op == 'add':
            present.add(raw)
        else:
            present.discard(raw)
        history.append((op, raw))

        # structural invariants must hold after every committed op
        try:
            assert_wildcard_invariants(widx)
        except AssertionError as e:
            fail(f'invariant violation: {e}')

        # full-grid oracle comparison
        oracle = Oracle(schema, [OracleTuple(*r) for r in present])
        for q in grid:
            got = widx.check(*q)
            exp = oracle.check(*q)
            if got != exp:
                fail(f'check mismatch: index={got} oracle={exp}', query=q)

    # ANTI-VACUITY. Every `except ValueError: ... continue` above skips the rest
    # of the loop body -- which is where BOTH the invariant check and the entire
    # oracle grid comparison live. A regression that makes every write raise
    # (an over-eager admission check, a cycle detector false-positive) would
    # `continue` all STEPS times, leave `history` empty, compare nothing, and
    # PASS. Rejections are legitimate and expected here, so the bar is a
    # majority, not all of them.
    assert len(history) >= STEPS // 2, (
        f'only {len(history)}/{STEPS} ops were accepted (seed={seed}) -- the '
        f'invariant and oracle-grid checks ran that few times, so this property '
        f'test verified almost nothing. Suspect a write path rejecting wholesale.')

    session.close()


# ===========================================================================
# TK77: the CROSSABLE corpus -- the I14 crossing-middle surface
#
# `docs/tk77-crossable-census-2026-09-19.md` measured that neither this module
# nor `tests/test_matrix.py` compiles a single crossable schema (0 of 3 and 0 of
# 36 parses, MEASURED 2026-09-19c), so the two mechanisms this repo relies on to
# find semantic divergence had ZERO reach into I14 -- the
# `w_all -> concrete -> w_any` crossing `src/zanzibar/graphindex/wildcard.py` maintains per live
# entity. §2 of that census also closed the cheap fix: 13 of the 15
# `tests/fga_schemas/` fixtures have an empty `bridged_in_shapes`, so NO
# `object_wildcard_shapes` argument can make them crossable, and `wildcards.fga`
# (the fixture both grids already use) is compile-REFUSED if you try. The fix is
# therefore a second corpus on a different fixture, which is what follows.
#
# The conjunction that makes a schema crossable (census §1): a TTU over a
# tupleset that admits a bare object star `[S:*]`, whose TARGET relation is also
# an object-wildcard shape. `owc_star_ttu.fga` is the only fixture that carries
# it -- `viewer from parent` over `parent: [folder, folder:*]`, with `viewer`
# object-wildcarded -- and it yields `crossable_shapes == {('folder','viewer')}`
# (MEASURED 2026-09-19d).
#
# REACH AFTER (MEASURED 2026-09-19d, the census probe over these two modules,
# command in that doc section 8). `parse_crossable` 0 -> 6 for `test_matrix.py`
# and 0 -> 5 here; the acceptance column `_sync/EFF` 0 -> 46 and 0 -> 23, with the
# ceiling control 0 -> 196 and 0 -> 101. For scale, the whole seven-module suite
# measured 8 effective `_sync` calls before this, all of them in
# `tests/test_i14_crossing_middles.py`.
#
# SABOTAGE (`docs/sabotage-procedure.md`), 12 mutations, 11 caught, reproducer
# `formal/probes/tk77_middles_reach_sweep_2026-09-19.py`. Literal observed table,
# MEASURED 2026-09-19d:
#
#   M0   CAUGHT   HARNESS CONTROL: invert assert_remove_path_reached's claim  6 red
#   M1   CAUGHT   CROSSABLE_WC -> {('doc','viewer')}                          8 red
#   M2   CAUGHT   CROSSABLE_WC -> frozenset()                                 8 red
#   M3   CAUGHT   CROSSABLE_SHAPES -> frozenset() (weaken the pin itself)      8 red
#   M4   INERT    drop ONE of the two bare-star tupleset subjects
#   M5   CAUGHT   drop EVERY bare-star tupleset subject from the pool         6 red
#   M6   CAUGHT   property walk never removes                                 3 red
#   M7   CAUGHT   matrix arm never removes                                    3 red
#   M8   CAUGHT   INSTRUMENT KILL: recorder observes nothing                  8 red
#   M9   CAUGHT   effective filter -> `if True` (read RAW as reach)   2 controls red
#   M10  CAUGHT   drop only the `n != '*'` clause                     1 control red
#   M11  CAUGHT   omit proc.run_cascade(wm)                            2 of 3 seeds
#
# `M4` is legitimately inert: one of the two star subjects is enough for the
# feature. `M5` and `M10` were INERT on the FIRST run of that sweep and are real
# holes it found -- `assert_crossable_pool` and
# `test_middle_sync_record_excludes_the_wildcard_entity` exist because of them.
# ===========================================================================

# Same set as `tests/test_lookup_oracle.py::OWC_STAR_TTU_SHAPES` for the same
# fixture (that module runs the lookup-surface gate over it; this one and
# `test_matrix.py` run the differential grids). Deliberately NOT imported from
# there: `test_lookup_oracle` imports this module, so the dependency only runs
# one way.
CROSSABLE_WC = frozenset({('folder', 'viewer'), ('doc', 'viewer')})

#: What `CROSSABLE_WC` must buy. Pinned as an equality, not a non-emptiness,
#: because an empty `crossable_shapes` is a SILENT no-op: a corpus that stops
#: being crossable keeps passing every test it is in and still looks like
#: coverage (census §7, trap). `test_crossable_corpus_is_actually_crossable`
#: is the standalone pin; the walks below re-assert it so a red names itself.
CROSSABLE_SHAPES = frozenset({('folder', 'viewer')})

CROSS_USERS = ['u1', 'u2']
CROSS_FOLDERS = ['f1', 'f2']
CROSS_DOCS = ['d1']
CROSS_GHOST = {'user': 'ghostU', 'group': 'ghostG', 'folder': 'ghostF', 'doc': 'ghostD'}


def _crossable_raw_tuples() -> list[tuple]:
    """Schema-valid raw tuples for `owc_star_ttu.fga` over a small universe.

    Covers all four features at once, because the crossing needs three of them
    live simultaneously: object-wildcard `viewer` grants (which mint `w_all`),
    the star tupleset `folder:*` as a `parent` subject (which mints the in-bridge
    on `(folder, viewer)` through the TTU), concrete `viewer`/`editor`/`blocked`
    grants, and group usersets. The boolean `restricted: editor but not blocked`
    rides along, so the graph leg runs its delta-processor cascade here too.
    """
    viewer_objs = [('folder', f) for f in CROSS_FOLDERS] + [('doc', d) for d in CROSS_DOCS]
    viewer_objs_wc = viewer_objs + [('folder', '*'), ('doc', '*')]
    out = []
    for u in CROSS_USERS:
        out.append(('...', 'user', u, 'member', 'group', 'g1'))
    for (ot, on) in viewer_objs:
        for u in CROSS_USERS:
            out.append(('...', 'user', u, 'editor', ot, on))
        out.append(('member', 'group', 'g1', 'editor', ot, on))
        out.append(('...', 'user', 'u1', 'blocked', ot, on))
    for (ot, on) in viewer_objs_wc:
        for u in CROSS_USERS:
            out.append(('...', 'user', u, 'viewer', ot, on))
        out.append(('...', 'user', '*', 'viewer', ot, on))
        out.append(('member', 'group', 'g1', 'viewer', ot, on))
    # parent hierarchy, INCLUDING the bare star tupleset subject `folder:*` --
    # without it the TTU has no star to carry and the corpus is crossable by
    # schema but never actually bridged in practice.
    out.append(('...', 'folder', 'f1', 'parent', 'folder', 'f2'))
    out.append(('...', 'folder', '*', 'parent', 'folder', 'f2'))
    for d in CROSS_DOCS:
        out.append(('...', 'folder', 'f1', 'parent', 'doc', d))
        out.append(('...', 'folder', '*', 'parent', 'doc', d))
    return list(dict.fromkeys(out))


def _crossable_query_grid() -> list[tuple]:
    """Queries for the crossable corpus. Every target type contributes a
    concrete, a ghost and the wildcard name; `restricted` puts the derived
    (processor-maintained) relation in the grid, and the `viewer(folder, f1)`
    userset subject walks the from-chain the crossing lives on."""
    subjects = [
        ('...', 'user', 'u1'), ('...', 'user', CROSS_GHOST['user']), ('...', 'user', '*'),
        ('member', 'group', 'g1'), ('member', 'group', '*'),
        ('viewer', 'folder', 'f1'),                     # userset subject (from-chain)
    ]
    targets = [
        ('viewer', 'folder', 'f1'), ('viewer', 'folder', CROSS_GHOST['folder']),
        ('viewer', 'folder', '*'),
        ('viewer', 'doc', 'd1'), ('viewer', 'doc', '*'),
        ('editor', 'folder', 'f1'), ('restricted', 'folder', 'f1'),
        ('member', 'group', 'g1'),
    ]
    return [(sp, st, sn, rel, ot, on)
            for (sp, st, sn) in subjects
            for (rel, ot, on) in targets]


def assert_crossable(schema_info, where: str) -> None:
    """Refuse a corpus that is not crossable (census §7 trap).

    Mechanical rather than documented on purpose: the failure mode this guards is
    a corpus that silently stops exercising I14 -- an empty `crossable_shapes`
    changes no answer, so every test over it stays green and the coverage is gone
    without a single red.
    """
    assert schema_info.crossable_shapes == CROSSABLE_SHAPES, (
        f'{where}: crossable_shapes is {sorted(schema_info.crossable_shapes)}, '
        f'expected {sorted(CROSSABLE_SHAPES)} -- this corpus exists ONLY to reach the '
        f'I14 crossing middles, and an empty/changed set means it no longer does. '
        f'See docs/tk77-crossable-census-2026-09-19.md section 1 for the conjunction '
        f'that mints the shape; do not "fix" this by relaxing the assertion.')


def assert_crossable_pool(pool, where: str) -> None:
    """Refuse a pool that dropped one of the two DATA features the crossing needs.

    `assert_crossable` pins the SCHEMA half; this pins the corpus half, and the two
    are independent. MEASURED 2026-09-19d, sweep `M5`: deleting every bare-star
    tupleset subject from `_crossable_raw_tuples` left all eight crossable tests
    GREEN -- `crossable_shapes` is computed from the schema, and both
    `_sync_entity_middles`' guard and the census's EFFECTIVE column key off the
    entity TYPE, so none of them can see a pool that no longer carries the star.
    The differential simply explored a smaller state space and agreed with itself.

    A pool shrink is never caught by the tests that consume the pool, so this is a
    refusal rather than a comment. It pins PRESENCE in the pool, not that any
    particular seed drew it -- the walks are 14 steps over ~40 tuples.
    """
    star_tupleset = [r for r in pool
                     if r[3] == 'parent' and r[1] == 'folder' and r[2] == '*']
    owc_grant = [r for r in pool
                 if r[3] == 'viewer' and r[4] in ('folder', 'doc') and r[5] == '*']
    assert star_tupleset, (
        f'{where}: the pool carries no bare-star tupleset subject '
        f"(`folder:*` as a `parent`). Without it the TTU has no star to carry, so "
        f'the walk never actually bridges IN on (folder, viewer) and the crossable '
        f'states this corpus exists for are unreachable -- silently, because every '
        f'assertion here is schema- or type-keyed.')
    assert owc_grant, (
        f'{where}: the pool carries no object-wildcard `viewer` grant '
        f"(`viewer` on `folder:*`/`doc:*`), so `w_all` is never minted and the "
        f'crossing has no left end.')


def assert_remove_path_reached(rec, where: str) -> None:
    """Refuse a walk that never reached the crossing-middle REMOVE path (TK77).

    The census's acceptance target: `_ensure_entity_middles` (the ADD side) is
    reached by five of seven modules, while `_sync_entity_middles` (the REMOVE
    side) was reached by exactly ONE -- `tests/test_i14_crossing_middles.py`, 8
    effective calls in an 82-test run, in both runs (census section 6, MEASURED
    2026-09-19c). A corpus that lifts the add side and leaves the remove side at
    8 has bought nothing, so this is asserted, not hoped for.
    """
    assert rec.effective, (
        f'{where}: {len(rec.raw)} _sync_entity_middles call(s), NONE of them '
        f'effective -- every one named a non-crossable type or the wildcard name, so '
        f'this walk did not reach the I14 remove path at all. Raw calls prove nothing '
        f'here (see MiddleSyncRecord); the walk needs a remove whose endpoint is a '
        f'concrete entity of a crossable type.')


def test_middle_sync_record_excludes_the_wildcard_entity(load_fga_schema):
    """Second INSTRUMENT CONTROL: the `n != '*'` clause of the effective filter.

    Dropping that clause alone left every crossable test green (MEASURED
    2026-09-19d, sweep `M10`), because on the crossable corpus both raw and
    filtered counts are non-zero either way. It is still load-bearing: a walk whose
    only `folder`-side removes name the bare star `folder:*` would then report reach
    into the I14 remove path, and there is no such thing -- `_sync_entity_middles`
    returns on `name == '*'` before doing anything, and a middle for `'*'` is
    exactly what the node encoding reserves against.

    So: the crossable schema, and a remove whose only crossable-type endpoint IS the
    wildcard. Raw must see it; effective must not.
    """
    ruleset = parse_openfga_schema(load_fga_schema('owc_star_ttu.fga'),
                                  object_wildcard_shapes=CROSSABLE_WC)
    assert_crossable(ruleset.schema_info, 'wildcard-entity instrument control')
    session, widx = make_wildcard_index(ruleset.schema_info)
    grant = ('...', 'user', 'u1', 'viewer', 'folder', '*')
    _apply(widx, ruleset, grant, 'add')
    session.commit()
    with record_middle_syncs(widx) as rec:
        _apply(widx, ruleset, grant, 'remove')
        session.commit()
    session.close()

    assert ('folder', '*') in rec.raw, (
        f'the remove booked no _sync_entity_middles call on the wildcard folder '
        f'entity ({rec.raw}) -- this control cannot say anything about the clause it '
        f'exists for. Did the object endpoint stop being (viewer, folder, *)?')
    assert rec.effective == [], (
        f"a call naming the WILDCARD entity was counted as effective ({rec.effective}) "
        f"-- the n != '*' clause is gone, so a walk that only ever removes "
        f'wildcard-endpoint tuples now reports reach into the I14 remove path it '
        f'cannot have.')


def test_middle_sync_record_filters_a_non_crossable_corpus(load_fga_schema):
    """INSTRUMENT CONTROL for `assert_remove_path_reached` (TK77).

    The census's trap (a): a RAW `_sync_entity_middles` count is not reach, because
    the function is called unconditionally and returns at a guard. So an
    `effective` that forgot to filter would report reach for EVERY corpus, and
    `assert_remove_path_reached` would be a green that means nothing -- which is
    unobservable from the crossable walks, where raw and effective are both
    non-zero.

    This pins the filter from the other side, on `wildcards.fga`, whose
    `crossable_shapes` is empty (census §2): removes here MUST book raw calls and
    MUST book zero effective ones.
    """
    ruleset = parse_openfga_schema(load_fga_schema('wildcards.fga'),
                                   object_wildcard_shapes=OBJECT_WC)
    assert not ruleset.schema_info.crossable_shapes, (
        'wildcards.fga became crossable -- this control depends on it NOT being, and '
        'the census measured it structurally un-crossable (its only in-bridge is the '
        'literal group:*#member, which cannot also be an object wildcard)')
    session, widx = make_wildcard_index(ruleset.schema_info)
    with record_middle_syncs(widx) as rec:
        for raw in [('...', 'user', 'u1', 'viewer', 'folder', 'f1'),
                    ('...', 'user', 'u1', 'member', 'group', 'g1')]:
            _apply(widx, ruleset, raw, 'add')
        session.commit()
        for raw in [('...', 'user', 'u1', 'viewer', 'folder', 'f1'),
                    ('...', 'user', 'u1', 'member', 'group', 'g1')]:
            _apply(widx, ruleset, raw, 'remove')
        session.commit()
    session.close()

    assert rec.raw, (
        'no _sync_entity_middles call recorded at all -- the recorder is not '
        'observing the remove path, so every `assert_remove_path_reached` elsewhere '
        'is resting on a dead instrument')
    assert rec.effective == [], (
        f'{len(rec.raw)} raw call(s) on a corpus with NO crossable shape produced '
        f'{rec.effective} effective one(s) -- MiddleSyncRecord.effective is not '
        f'applying the guard, so it is a raw count wearing the word "effective" '
        f'(census trap (a)).')


def test_crossable_corpus_is_actually_crossable(load_fga_schema):
    """The structural precondition for both crossable walks, pinned on its own so a
    red points at the schema rather than at a differential mismatch."""
    ruleset = parse_openfga_schema(load_fga_schema('owc_star_ttu.fga'),
                                   object_wildcard_shapes=CROSSABLE_WC)
    assert_crossable(ruleset.schema_info, 'owc_star_ttu.fga')
    # The two halves of the conjunction, so a red says WHICH one was lost.
    assert ('folder', 'viewer') in ruleset.schema_info.bridged_in_shapes, \
        'the star-tupleset through-shape is gone: no TTU over a [folder:*]-admitting parent'
    assert ('folder', 'viewer') in ruleset.schema_info.bridged_out_shapes, \
        'the object-wildcard half is gone: (folder, viewer) is no longer an owc shape'


@pytest.mark.parametrize('seed', [0, 1, 2])
def test_wildcard_property_crossable_vs_oracle(load_fga_schema, seed):
    """`test_wildcard_property_vs_oracle`, re-run over the CROSSABLE corpus (TK77).

    Same property, same oracle, same after-every-op full-grid comparison -- the
    only difference is the fixture, chosen so `crossable_shapes` is non-empty and
    the walk's removes drive `_sync_entity_middles` past its guard.
    """
    schema = load_fga_schema('owc_star_ttu.fga')
    ruleset = parse_openfga_schema(schema, object_wildcard_shapes=CROSSABLE_WC)
    assert_crossable(ruleset.schema_info, f'crossable property walk (seed={seed})')
    session, widx = make_wildcard_index(ruleset.schema_info)
    # ANTI-VACUITY on the boolean half: this corpus carries `restricted`, so the
    # walk is only a test of the derived read path while a cascade actually runs.
    assert ruleset.compiled is not None and ruleset.compiled.plans, \
        'owc_star_ttu.fga minted no derived plans -- the `restricted` grid cell is vacuous'
    proc = DeltaProcessor(widx, ruleset.compiled)

    pool = _crossable_raw_tuples()
    grid = _crossable_query_grid()
    assert_crossable_pool(pool, f'crossable property walk (seed={seed})')
    rng = random.Random(seed)

    present: set[tuple] = set()
    history: list[tuple] = []

    def fail(msg, query=None):
        lines = [msg, f'seed={seed}', 'history:']
        lines += [f'  {op} {raw}' for (op, raw) in history]
        if query is not None:
            lines.append(f'failing query: {query}')
        pytest.fail('\n'.join(lines))

    STEPS = 14
    with record_middle_syncs(widx) as rec:
        for _ in range(STEPS):
            if not present or rng.random() < 0.55:
                candidates = [r for r in pool if r not in present]
                if not candidates:
                    op, raw = 'remove', rng.choice(sorted(present))
                else:
                    op, raw = 'add', rng.choice(candidates)
            else:
                op, raw = 'remove', rng.choice(sorted(present))

            try:
                wm = outbox_watermark(session, widx.idx.store_id)
                _apply(widx, ruleset, raw, op)
                # Boolean schema: the cascade is part of the WRITE, same txn
                # (CLAUDE.md "Derived-relation exclusivity (I5)"). Omitting it does
                # not error -- `restricted` simply answers False forever, which this
                # walk caught as an oracle mismatch on the first seed that granted
                # an `editor` (observed 2026-09-19d, seeds 0 and 2).
                proc.run_cascade(wm)
                session.commit()
            except ValueError:
                session.rollback()
                continue

            if op == 'add':
                present.add(raw)
            else:
                present.discard(raw)
            history.append((op, raw))

            try:
                assert_wildcard_invariants(widx)
            except AssertionError as e:
                fail(f'invariant violation: {e}')

            oracle = Oracle(schema, [OracleTuple(*r) for r in present])
            for q in grid:
                got = widx.check(*q)
                exp = oracle.check(*q)
                if got != exp:
                    fail(f'check mismatch: index={got} oracle={exp}', query=q)

    # ANTI-VACUITY -- see `test_wildcard_property_vs_oracle`. Same reasoning: the
    # `continue` above skips the invariant check AND the whole oracle grid.
    assert len(history) >= STEPS // 2, (
        f'only {len(history)}/{STEPS} ops were accepted (seed={seed}) -- the '
        f'invariant and oracle-grid checks ran that few times, so this property '
        f'test verified almost nothing. Suspect a write path rejecting wholesale.')
    assert_remove_path_reached(rec, f'crossable property walk (seed={seed})')

    session.close()
