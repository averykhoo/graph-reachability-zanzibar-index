"""R6-10: the stored-tuple enumeration memo, and the four things that make it exact.

``index_v4/processor.py::DeltaProcessor._stored_cache_scope`` installs a memo over
``::DeltaProcessor._stored_tupleset_subjects`` and ``::DeltaProcessor.stored_userset_subjects``
for the duration of one cascade / one reconcile. A memo is only ever as good as the
argument that its inputs cannot change while it is installed, so what is pinned here is
NOT "the cache is fast" — it is the four properties that carry correctness:

  1. **Teardown.** The scope must not survive its cascade, or the next cascade answers
     from the previous cascade's stored tuples (``test_a_changed_storage_leaf_tuple_is_
     visible_to_the_next_cascade``, BOTH signs).
  2. **Placement.** A raw (non-processor) write must never execute while a scope is
     open — which is exactly why the scope is installed inside ``run_cascade`` and NOT
     in ``connectedstore/apply.py::advance_index``, where the N15 node cache lives and
     spans the apply loop (``test_raw_writes_never_run_inside_a_stored_cache_scope``,
     plus the deliberately-degraded ``test_a_scope_spanning_a_raw_write_serves_a_stale_
     answer`` which shows what that placement would buy).
  3. **Reentrancy.** ``run_cascade`` wraps ``reconcile``/``reconcile_subject``,
     ``reconcile_subject`` escalates into ``_reconcile``, and ``_reconcile`` step 4
     nests ``_reconcile_subject`` — a non-reentrant scope tears the cache down under
     its own caller (``test_stored_cache_scope_is_reentrant``).
  4. **Scope of the memo.** It stops at ``_stored_tupleset_subjects``. The RC2 star
     expansion above it (``::DeltaProcessor._expand_tupleset_parents`` ->
     ``::DeltaProcessor._instances_of_type``) reads the GLOBAL NodeV4 table, which
     legitimately changes mid-reconcile, and must stay live
     (``test_star_expansion_is_not_frozen_by_the_memo``).

⚠ Property 4 is the one no benchmark can defend. `R6-3`/`R6-13` measured
``_instances_of_type`` at **0 calls** on every benchmarked workload, so a profile of the
"obvious" fix — memoize ``tupleset_parents`` instead — would report a *larger* win and
nothing would go red. That test is the only instrument pointed at it.

------------------------------------------------------------------------------
SABOTAGE (``docs/sabotage-procedure.md``; literal observed output)
------------------------------------------------------------------------------

SIX sabotages were run (2026-08-20), each the narrowest *plausible* weakening of one
property. S4 came back GREEN and that is recorded here as a finding, not dropped
(`docs/sabotage-procedure.md`: "a green sabotage is a finding, not a non-event") — it
is why `test_memoized_results_are_not_shared_mutable_state` now drives BOTH memoized
readers. Baseline for all of them, on the same tree with the fix in place::

    $ python -m pytest tests/test_stored_cache_scope.py tests/test_processor.py \
          tests/test_ttu_tupleset_parent_types.py -q
    36 passed in 4.24s

The three modules collect 10 + 14 + 12. Every count below is from THAT command; a
wider run (with `tests/test_matrix.py`, 48 collected) is used only where it is named,
and its totals differ accordingly. Sabotages are applied by `-p` plugin monkeypatch,
never by editing the source, so there is no restore step to get wrong.

--- S1: DELETE THE TEARDOWN (property 1) ---------------------------------------

In ``_stored_cache_scope``'s ``finally``, drop the ``self._stored_cache = None`` line
so the memo becomes a permanent instance dict surviving across cascades. This is the
plausible one: it reads as "cache it for the whole session", and it makes every counter
in ``benchmarks/profile_r6_write.py --target cascade`` look BETTER::

    10 failed, 26 passed in 4.56s
    FAILED tests/test_stored_cache_scope.py::test_a_changed_storage_leaf_tuple_is_visible_to_the_next_cascade
    FAILED tests/test_stored_cache_scope.py::test_the_memo_is_torn_down_between_cascades
    FAILED tests/test_stored_cache_scope.py::test_raw_writes_never_run_inside_a_stored_cache_scope[True]
    FAILED tests/test_stored_cache_scope.py::test_a_scope_spanning_a_raw_write_serves_a_stale_answer
    FAILED tests/test_stored_cache_scope.py::test_stored_cache_scope_is_reentrant
    FAILED tests/test_stored_cache_scope.py::test_nested_reconcile_entry_points_keep_one_cache
    FAILED tests/test_stored_cache_scope.py::test_star_expansion_is_not_frozen_by_the_memo
    FAILED tests/test_stored_cache_scope.py::test_expand_tupleset_parents_matches_the_public_wrapper
    FAILED tests/test_processor.py::test_derived_tupleset_ttu_with_stored_tuples
    FAILED tests/test_processor.py::test_tainted_userset_end_to_end_vs_oracle

    E  AssertionError: STALE MEMO: removing the only stored tupleset tuple
       (folder:f1, parent, doc:d1) left access(alice, doc:d1) = True. The memo
       outlived the cascade that filled it.
    E  assert True is False
    E   +  where True = derived_check('doc', 'access', 'd1', ('...', 'user', 'alice'))

    E  AssertionError: PLACEMENT VIOLATION: 6 raw write(s) ran with a stored-tuple
       memo installed: [('parent', 'doc', 'd1'), ('blocked', 'folder', 'f1'),
       ('ok.1', 'folder', 'f1'), ('blocked', 'folder', 'f1'), ('ok.1', 'folder',
       'f1'), ('parent', 'doc', 'd1')]. The scope must not span the raw-write apply
       loop.

Two things to read out of that list rather than just the count.

* **Both signs appear in the pre-existing suite**, which is what makes S1 a real
  authorization defect and not just a broken new file:
  ``test_processor.py::test_derived_tupleset_ttu_with_stored_tuples`` fails
  ``assert True is False`` (an over-grant, fail-OPEN) and
  ``test_tainted_userset_end_to_end_vs_oracle`` fails
  ``after unban: ('...','user','alice','viewer','doc','d1') graph=False oracle=True``
  (an under-grant).
* **S1 is the LEAST attributable of the six** — 8 of this file's 10 tests go red,
  because six of them assert "no memo is installed" as a pre/post-condition. That is a
  known weakness of this particular sabotage, stated rather than hidden: S1 alone
  cannot distinguish "teardown is load-bearing" from "the file is broken". The
  attribution is carried by S2/S2b/S3/S4/S5 below, each of which reddens ONE test.
  Note also that ``test_raw_writes_never_run_inside_a_stored_cache_scope[False]`` (the
  ASYNC schedule) stayed green under S1, and so did all 12 tests of
  ``tests/test_ttu_tupleset_parent_types.py``.
* ★ **The validation matrix is blind to S1.** Re-run WIDENED to include
  ``tests/test_matrix.py`` (48 collected): ``10 failed, 38 passed in 77.47s`` — the
  same 10 failures, zero of them in ``test_matrix.py``. So the 4-way matrix that
  ``CLAUDE.md`` names as "what pins same semantics" stayed fully green while S1 was
  producing BOTH an over-grant and an under-grant (the two ``test_processor.py``
  failures above). It writes and queries through one schema's fixed op sequence; a
  cross-cascade stale memo needs a specific write-cascade-write-cascade shape it never
  builds. The pins in THIS file are the net for that, not the matrix.

--- S2 / S2b: WIDEN THE MEMO PAST `_stored_tupleset_subjects` (property 4) --------

Move the memo one level up so the RC2 ``_instances_of_type`` expansion is frozen with
it. This is the naive fix the round-6 audit's verifier pre-refuted, and it is *more*
profitable on every measured workload — no benchmark can tell it apart from the right
fix. After step A the three routes to the expansion are siblings rather than nested, so
both levels were sabotaged separately.

S2 = memoize ``DeltaProcessor.tupleset_parents``::

    1 failed, 35 passed in 4.56s
    FAILED tests/test_stored_cache_scope.py::test_star_expansion_is_not_frozen_by_the_memo
    E  AssertionError: FROZEN STAR EXPANSION: a `doc:*` tupleset parent must expand
       over the instances that exist NOW -- doc:d3 was interned inside the scope
       (exactly what _reconcile step 2a does) and tupleset_parents did not see it.
       first=[('doc', 'd1'), ('doc', 'd2')] second=[('doc', 'd1'), ('doc', 'd2')]
    E  assert ('doc', 'd3') in [('doc', 'd1'), ('doc', 'd2')]

S2b = memoize ``DeltaProcessor.derived_stored_parents``::

    1 failed, 35 passed in 4.50s
    FAILED tests/test_stored_cache_scope.py::test_star_expansion_is_not_frozen_by_the_memo
    E  AssertionError: FROZEN STAR EXPANSION: ... and derived_stored_parents did not
       see it. first=[('doc', 'd1'), ('doc', 'd2')] second=[('doc', 'd1'), ('doc', 'd2')]

★ **The finding, and the reason S2 was worth running at all:**
``tests/test_ttu_tupleset_parent_types.py`` — the module the R6-10 scout and
``::DeltaProcessor._expand_tupleset_parents``'s own docstring name as "the net" for the
RC2 region — stayed **fully green** under S2 and S2b: 35 passed, and all **12** of its
tests are among them (``pytest tests/test_ttu_tupleset_parent_types.py -q
--collect-only`` -> ``12 tests collected in 0.21s``; an earlier draft of this docstring
said "26", which was pytest's ``26 passed`` SUMMARY line from the S1 run above misread
as a module count — 26 = 36 collected minus S1's 10 failures). It writes its whole pool
in one batch and then queries, so the star expansion is never re-read across a
mid-reconcile intern: it pins that a star parent IS expanded, never that the expansion
stays LIVE. For this specific mistake the RC2 region was **unguarded**, and
``test_star_expansion_is_not_frozen_by_the_memo`` is the sole evidence. Do not delete
it as redundant with the RC1/RC2 pins.

  ★ And it is not only that module. Re-run with the matrix included::

      $ SAB=s2c pytest tests/test_ttu_tupleset_parent_types.py tests/test_matrix.py \
            -q -p sab_s2_plugin        # s2c = BOTH widenings active
      24 passed in 59.42s

  so ``tests/test_matrix.py`` is blind to the frozen-star-expansion mistake too
  (a reviewer extended this to ``tests/test_lookup_oracle.py`` as well: ``69 passed``).
  Three of the project's headline nets see nothing here.

  ⚠ The FIRST version of S2 reported ``36 passed`` — a green sabotage. The instrument
  was at fault, not the sabotage: the test drove only ``derived_stored_parents``, which
  step A had just rerouted around ``tupleset_parents``, so the memo added to
  ``tupleset_parents`` was never consulted. That is the sabotage procedure's
  "a green pin under a sabotage that should break it is a verdict on the pin" — the
  test was widened to probe all three routes and both levels, and only then did it fire.

--- S3: MAKE THE SCOPE NON-REENTRANT (property 3) --------------------------------

Write the contextmanager the way a careless copy would: install ``{}`` unconditionally
and clear it in ``finally``, with no outer flag::

    2 failed, 34 passed in 4.62s
    FAILED tests/test_stored_cache_scope.py::test_stored_cache_scope_is_reentrant
    FAILED tests/test_stored_cache_scope.py::test_nested_reconcile_entry_points_keep_one_cache

    E  AssertionError: a nested scope replaced the outer cache with a fresh one
    E  assert ('ts', 'doc', 'sentinel', 'parent', ('folder',)) in {}
    E  AssertionError: reconcile replaced/dropped the outer cache
    E  assert None is {}

  ⚠ The first attempt at S3 (``outer = True`` while keeping the rest of the body) was
  rejected as a sabotage: the ``keys_max`` line in the ``finally`` then runs ``len()``
  on a cache an inner scope already nulled, so it raises ``TypeError: object of type
  'NoneType' has no len()`` and produced ``33 failed, 3 passed in 3.16s`` — a
  catastrophe, not a plausible weakening, and it tells you nothing about which property
  is guarded. The accepted form guards that stat line, so the ONLY thing it changes is
  the reentrancy.

--- S4 / S5: SHARE THE CACHED LIST INSTEAD OF COPYING IT ------------------------

The narrowest plausible weakening of the freshness-on-hit property, applied to each
memoized reader separately: ``cache[key] = out`` (the mutable list) and ``return hit``
(the same object on every hit) instead of ``tuple(out)`` / ``list(hit)``.

S5 = the TUPLESET half (``_stored_tupleset_subjects``)::

    1 failed, 35 passed in 4.21s
    FAILED tests/test_stored_cache_scope.py::test_memoized_results_are_not_shared_mutable_state
    E  AssertionError: ([('folder', 'f1'), ('folder', 'POISON')], ['POISON'])
    E  assert [('folder', 'f1'), ('folder', 'POISON')] == [('folder', 'f1')]

★ **S4 = the USERSET half (``stored_userset_subjects``) — and it came back GREEN::**

    [SABOTAGE ACTIVE] S4 (userset half shares a mutable list)
    ....................................                                     [100%]
    36 passed in 12.83s

S5 is S4's instrument control: the *identical* weakening on the other half reddens the
test, so the harness works and the difference is COVERAGE. Until 2026-08-20
``test_memoized_results_are_not_shared_mutable_state`` drove only
``_stored_tupleset_subjects``; ``stored_userset_subjects``'s ``return list(hit)`` was
unpinned, and any future caller that filtered its result in place
(``stored.remove(x)``) would have corrupted every later hit on that key inside the
cascade — a wrong grant, silent. The test now loops over BOTH halves; re-run of S4
against the widened test::

    1 failed, 35 passed in 4.58s
    FAILED tests/test_stored_cache_scope.py::test_memoized_results_are_not_shared_mutable_state
    E  AssertionError: the userset memo handed back shared mutable state: ['g1', 'POISON']
    E  assert ['g1', 'POISON'] == ['g1']

The userset half needs its own schema to be reachable at all (``_USERSET_SCHEMA``
below): no benchmark workload calls ``stored_userset_subjects`` even once
(``benchmarks/profile_r6_write.py --target cascade``: ``0 calls``), and the suite as a
whole drives it ~400 times against ~12,000 for the tupleset half. Half of this memo is
thinly exercised; keep that in mind before widening it.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from connectedstore import ConnectedStore
from index_v4.models import NodeV4
from index_v4.outbox import outbox_watermark
from index_v4.processor import DeltaProcessor
from tests.wildcard_helpers import make_wildcard_index
from zanzibar_utils_v1 import Entity, RelationalTriple, parse_openfga_schema


# A tainted TTU whose tupleset (`parent`) is an ordinary STORAGE relation: the
# `derived-ttu` leaf kind, so `check_fn` reaches `_stored_tupleset_subjects` through
# `tupleset_parents`. `ok` is tainted by the exclusion, which taints `access`.
_TTU_SCHEMA = '''
    type user
    type folder
      relations
        define blocked: [user]
        define viewer: [user]
        define ok: viewer but not blocked
    type doc
      relations
        define parent: [folder]
        define access: ok from parent
'''


# A tainted USERSET restriction: `banned: [group#member]` with `member` tainted, so
# `banned`'s raw tuples live on the `derived-userset` storage leaf `banned.0` and the
# read path is `stored_userset_subjects` — the OTHER memoized reader, which no
# benchmark workload and (until 2026-08-20) no test in this file exercised.
_USERSET_SCHEMA = '''
    type user
    type group
      relations
        define gblocked: [user]
        define member: [user] but not gblocked
    type doc
      relations
        define banned: [group#member]
        define viewer: [user] but not banned
'''


def _build(schema, object_wc=frozenset()):
    """The synchronous-v1 write path `tests/test_matrix.py::GraphBackend.apply` uses:
    route the raw tuple, run the cascade in the SAME transaction, commit."""
    rs = parse_openfga_schema(schema, object_wildcard_shapes=object_wc, enable_boolean=True)
    session, widx = make_wildcard_index(rs.schema_info)
    proc = DeltaProcessor(widx, rs.compiled)

    def write(op, raw):
        wm = outbox_watermark(session, 'test')
        sp = Ellipsis if raw[0] == '...' else raw[0]
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
        fn = widx.add_tuple if op == 'add' else widx.remove_tuple
        for d in rs.apply(triple):
            fn('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
               d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
        proc.run_cascade(wm)
        session.commit()

    return session, widx, proc, write


# ---------------------------------------------------------------------------
# (1) TEARDOWN -- the memo must not outlive its cascade. Both signs.
# ---------------------------------------------------------------------------

def test_a_changed_storage_leaf_tuple_is_visible_to_the_next_cascade():
    """Property guarded: a stored tupleset tuple written between two cascades is read
    by the second one — the memo is scoped to a cascade, never to the processor.

    BOTH SIGNS are driven, per `docs/sabotage-procedure.md` §"Probe BOTH signs": the
    REMOVE half is the fail-OPEN direction (a stale parent keeps granting `access`)
    and the ADD half is the fail-CLOSED one (a fresh parent is never seen). A
    one-directional probe here would mis-classify the severity of a stale memo.

    Sabotaged by S1 (delete the scope teardown) — see the module docstring for the
    literal output; this test is the first of S1's ten failures.
    """
    session, widx, proc, write = _build(_TTU_SCHEMA)
    q = ('...', 'user', 'alice')

    write('add', ('...', 'user', 'alice', 'viewer', 'folder', 'f1'))
    write('add', ('...', 'folder', 'f1', 'parent', 'doc', 'd1'))
    assert proc.derived_check('doc', 'access', 'd1', q) is True, 'setup'

    # --- fail-OPEN direction: the tupleset tuple goes away between cascades
    write('remove', ('...', 'folder', 'f1', 'parent', 'doc', 'd1'))
    assert proc.derived_check('doc', 'access', 'd1', q) is False, (
        'STALE MEMO: removing the only stored tupleset tuple (folder:f1, parent, '
        'doc:d1) left access(alice, doc:d1) = True. The memo outlived the cascade '
        'that filled it.')

    # --- fail-CLOSED direction: a DIFFERENT tupleset tuple arrives between cascades
    write('add', ('...', 'user', 'alice', 'viewer', 'folder', 'f2'))
    write('add', ('...', 'folder', 'f2', 'parent', 'doc', 'd1'))
    assert proc.derived_check('doc', 'access', 'd1', q) is True, (
        'STALE MEMO: a tupleset tuple added after the first cascade '
        '(folder:f2, parent, doc:d1) is invisible — the negative result was cached '
        'across the cascade boundary.')


def test_the_memo_is_torn_down_between_cascades():
    """The structural half of the test above: after any entry point returns, no memo
    is installed. Stated as state rather than behaviour so a future reader can see the
    contract without reconstructing an authorization scenario."""
    session, widx, proc, write = _build(_TTU_SCHEMA)
    assert proc._stored_cache is None
    write('add', ('...', 'user', 'alice', 'viewer', 'folder', 'f1'))
    assert proc._stored_cache is None, 'run_cascade left a memo installed'
    proc.reconcile('doc', 'access', 'd1')
    assert proc._stored_cache is None, 'reconcile left a memo installed'
    proc.reconcile_subject('doc', 'access', 'd1', ('...', 'user', 'alice'))
    assert proc._stored_cache is None, 'reconcile_subject left a memo installed'
    proc.backfill()
    assert proc._stored_cache is None, 'backfill left a memo installed'


# ---------------------------------------------------------------------------
# (2) PLACEMENT -- no raw write may run inside a scope
# ---------------------------------------------------------------------------

_CS_SCHEMA = _TTU_SCHEMA

_CS_OPS = [
    ('add', ('...', 'user', 'alice', 'viewer', 'folder', 'f1')),
    ('add', ('...', 'folder', 'f1', 'parent', 'doc', 'd1')),
    ('add', ('...', 'user', 'alice', 'blocked', 'folder', 'f1')),
    ('remove', ('...', 'user', 'alice', 'blocked', 'folder', 'f1')),
    ('remove', ('...', 'folder', 'f1', 'parent', 'doc', 'd1')),
]


@pytest.mark.parametrize('sync', [True, False])
def test_raw_writes_never_run_inside_a_stored_cache_scope(sync):
    """Property guarded: every RAW (user) write executes with NO memo installed.

    This is the placement rule, mechanically. The memo's whole correctness argument is
    that stored tuples on storage-leaf families are constant for the life of a scope;
    a raw write inside a scope violates that directly. It is the reason the scope is
    installed in ``DeltaProcessor.run_cascade`` and NOT in
    ``connectedstore/apply.py::advance_index`` — ``advance_index`` installs the N15
    node cache around the WHOLE ``_apply_row`` loop, so a stored-tuple memo copied to
    that site would span the raw writes.

    Both schedules are driven: sync (``advance_index`` inlined per write) and async
    (``catch_up`` batching several log rows into one apply loop + one cascade), because
    the batching schedule is the one where a scope at the ``advance_index`` level would
    span several raw writes rather than one.

    Non-vacuity is asserted: a spy that observed no raw writes at all would pass
    silently, which is the house failure mode.
    """
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        cs = ConnectedStore(session, 's', schema=_CS_SCHEMA, sync=sync)
        proc, widx = cs.proc, cs.widx
        assert proc is not None, 'schema must compile derived plans or this pins nothing'

        seen = {'raw': 0, 'processor': 0, 'raw_inside_scope': []}
        # `advance_index` routes RAW log rows through the trusted fast path (perf N9)
        # while `_write_derived` uses the ordinary `add_tuple`/`remove_tuple`, so all
        # four have to be spied or the probe silently watches the wrong door.
        names = ('add_tuple', 'remove_tuple', '_add_tuple_trusted', '_remove_tuple_trusted')
        real = {n: getattr(widx, n) for n in names}

        def make_spy(fn):
            def spy(sp, st, sn, rel, ot, on, *a, **k):
                if widx.processor_writes:
                    seen['processor'] += 1
                else:
                    seen['raw'] += 1
                    if proc._stored_cache is not None:
                        seen['raw_inside_scope'].append((rel, ot, on))
                return fn(sp, st, sn, rel, ot, on, *a, **k)
            return spy

        for n in names:
            setattr(widx, n, make_spy(real[n]))
        try:
            for op, raw in _CS_OPS:
                (cs.add_tuple if op == 'add' else cs.remove_tuple)(*raw)
            if not sync:
                assert cs.catch_up() == len(_CS_OPS)
        finally:
            for n in names:
                setattr(widx, n, real[n])

        # non-vacuity: the spy must have seen BOTH kinds, or it proves nothing
        assert seen['raw'] > 0, 'spy observed no raw writes — probe ran on nothing'
        assert seen['processor'] > 0, (
            'spy observed no processor writes — the cascade never wrote a derived '
            'edge, so this run does not exercise the scope at all')
        assert seen['raw_inside_scope'] == [], (
            f'PLACEMENT VIOLATION: {len(seen["raw_inside_scope"])} raw write(s) ran '
            f'with a stored-tuple memo installed: {seen["raw_inside_scope"]}. The '
            f'scope must not span the raw-write apply loop.')


def test_a_scope_spanning_a_raw_write_serves_a_stale_answer():
    """The permanent form of the placement sabotage: a DELIBERATELY mis-placed scope,
    constructed here in the test rather than by editing the source.

    Opening the scope around a raw write — which is what installing it at
    ``connectedstore/apply.py::advance_index`` would do — makes
    ``_stored_tupleset_subjects`` serve the pre-write answer. Asserting the stale
    answer appears is the point: it proves the placement rule is load-bearing and not
    a stylistic preference, and it survives whoever next reads the comment.

    If a future change makes the memo self-invalidating on raw writes, THIS test is
    what will go red, and that is the correct signal to revisit the placement rule
    (and this file's docstring) rather than to weaken the assertion.
    """
    session, widx, proc, write = _build(_TTU_SCHEMA)
    write('add', ('...', 'user', 'alice', 'viewer', 'folder', 'f1'))
    key = ('doc', 'd1', 'parent', ('folder',))

    with proc._stored_cache_scope():
        before = proc._stored_tupleset_subjects(*key)
        assert before == ([], []), before
        # a raw write INSIDE the scope -- the thing the placement rule forbids
        widx.add_tuple('...', 'folder', 'f1', 'parent', 'doc', 'd1')
        assert proc._stored_tupleset_subjects(*key) == ([], []), (
            'expected the mis-placed scope to serve the STALE answer; if this now '
            'reflects the write, the memo gained invalidation and the placement rule '
            'in DeltaProcessor._stored_cache_scope needs re-deriving')
    # outside the scope the truth is immediately visible again
    assert proc._stored_tupleset_subjects(*key) == ([('folder', 'f1')], [])


# ---------------------------------------------------------------------------
# (3) REENTRANCY
# ---------------------------------------------------------------------------

def test_stored_cache_scope_is_reentrant():
    """Property guarded: a NESTED scope neither replaces nor tears down the outer
    cache; only the outermost entry installs and removes it.

    This is a contract pin, not an authorization pin — a non-reentrant scope loses the
    cache under its own caller (a perf regression, and it would silently un-do the
    whole item) rather than producing a wrong answer. It is pinned because the nesting
    is real and not obvious: ``run_cascade`` -> ``reconcile``/``reconcile_subject``,
    ``reconcile_subject`` -> ``_reconcile`` on the ``s_node is None`` escalation, and
    ``_reconcile`` step 4 -> ``_reconcile_subject``.

    Sabotage S3 (copy the contextmanager without its outer flag — see the module
    docstring for the full run, ``2 failed, 34 passed``)::

        FAILED tests/test_stored_cache_scope.py::test_stored_cache_scope_is_reentrant
        E   AssertionError: a nested scope replaced the outer cache with a fresh one
        E   assert ('ts', 'doc', 'sentinel', 'parent', ('folder',)) in {}
    """
    session, widx, proc, write = _build(_TTU_SCHEMA)
    sentinel = ('ts', 'doc', 'sentinel', 'parent', ('folder',))

    assert proc._stored_cache is None
    with proc._stored_cache_scope():
        assert proc._stored_cache is not None
        proc._stored_cache[sentinel] = ((), ())
        with proc._stored_cache_scope():
            assert proc._stored_cache is not None, 'a nested scope dropped the cache'
            assert sentinel in proc._stored_cache, (
                'a nested scope replaced the outer cache with a fresh one')
        assert proc._stored_cache is not None, 'a nested scope tore down the outer cache'
        assert sentinel in proc._stored_cache
    assert proc._stored_cache is None, 'the outermost scope must tear down'


def test_nested_reconcile_entry_points_keep_one_cache():
    """The same property through the real entry points rather than by hand: with a
    scope open, ``reconcile`` and ``reconcile_subject`` (each of which installs a
    scope of its own) must leave the outer cache in place."""
    session, widx, proc, write = _build(_TTU_SCHEMA)
    write('add', ('...', 'user', 'alice', 'viewer', 'folder', 'f1'))
    write('add', ('...', 'folder', 'f1', 'parent', 'doc', 'd1'))

    with proc._stored_cache_scope():
        outer = proc._stored_cache
        proc.reconcile('doc', 'access', 'd1')
        assert proc._stored_cache is outer, 'reconcile replaced/dropped the outer cache'
        proc.reconcile_subject('doc', 'access', 'd1', ('...', 'user', 'alice'))
        assert proc._stored_cache is outer, \
            'reconcile_subject replaced/dropped the outer cache'
        assert outer, 'the nested reconciles populated nothing — probe ran on nothing'
    assert proc._stored_cache is None


# ---------------------------------------------------------------------------
# (4) THE STAR ARM MUST STAY LIVE  (RC2)
# ---------------------------------------------------------------------------

# `parent` is DERIVED (`and gate`), so its stored tuples live on its storage leaf and
# the TTU reads them through `derived_stored_parents`. A stored `doc:*` tupleset parent
# is expanded over the instances of `doc` — the expansion this test keeps live.
_RC2_SCHEMA = '''model
  schema 1.1

type user

type doc
  relations
    define gate: [doc, doc:*]
    define parent: [doc, doc:*] and gate
    define viewer: [user]
    define inherited: viewer from parent
'''


def test_star_expansion_is_not_frozen_by_the_memo():
    """Property guarded: the RC2 star expansion is re-read on every call, so a node
    interned MID-SCOPE is a parent immediately.

    ``_reconcile`` step 2a interns from-chain subjects with ``create_if_missing=True``
    and step 5 ``_gc_subject_node`` deletes them, so the global NodeV4 table that
    ``_instances_of_type`` reads genuinely changes inside one reconcile. The memo
    therefore stops at ``_stored_tupleset_subjects``; widening it to
    ``tupleset_parents`` / ``derived_stored_parents`` freezes the expansion.

    The intern below is done directly, with the same call ``_reconcile`` step 2a makes,
    because that isolates the property from any particular schema's from-chain shape.

    ⚠ This test is the ONLY net for that mistake, and that was MEASURED, not assumed:
    ``R6-3``/``R6-13`` measured ``_instances_of_type`` at 0 calls on every benchmarked
    workload, so no profile can see it, and under sabotages S2 / S2b / S2c all **12**
    tests of ``tests/test_ttu_tupleset_parent_types.py`` (the module named as the RC2
    net) AND all 12 of ``tests/test_matrix.py`` stayed GREEN while this one went red
    (module docstring for the literal runs). Do not remove it as redundant with the
    RC1/RC2 pins.
    """
    session, widx, proc, write = _build(_RC2_SCHEMA)
    write('add', ('...', 'doc', 'd2', 'gate', 'doc', 'd1'))      # interns doc:d2
    write('add', ('...', 'doc', '*', 'parent', 'doc', 'd1'))
    write('add', ('...', 'doc', '*', 'gate', 'doc', 'd1'))

    leaf, = proc._ts_leaf_predicates('doc', 'parent')

    # EVERY entry point above `_stored_tupleset_subjects` is probed, not just one:
    # after step A the three are no longer nested (`derived_stored_parents` reaches
    # `_expand_tupleset_parents` through `_split_parents`, not through
    # `tupleset_parents`), so a memo bolted onto any ONE of them must redden this.
    def parents_by_every_route():
        return {
            'tupleset_parents': proc.tupleset_parents('doc', 'd1', leaf, ('doc',)),
            'derived_stored_parents':
                proc.derived_stored_parents('doc', 'd1', 'parent', ('doc',)),
            '_expand_tupleset_parents': proc._expand_tupleset_parents(
                *proc._stored_tupleset_subjects('doc', 'd1', leaf, ('doc',))),
        }

    with proc._stored_cache_scope():
        first = parents_by_every_route()
        for route, got in first.items():
            assert ('doc', 'd2') in got, (
                f'setup: the `doc:*` tupleset parent must expand over doc:d2 via '
                f'{route} — {got}')
            assert ('doc', 'd3') not in got

        # exactly what `_reconcile` step 2a does mid-reconcile
        proc.idx.node('...', 'doc', 'd3', create_if_missing=True, implicit=False)
        assert session.exec(select(NodeV4).where(NodeV4.type == 'doc')
                            .where(NodeV4.name == 'd3')).first() is not None

        second = parents_by_every_route()
        for route, got in second.items():
            assert ('doc', 'd3') in got, (
                'FROZEN STAR EXPANSION: a `doc:*` tupleset parent must expand over '
                'the instances that exist NOW -- doc:d3 was interned inside the scope '
                f'(exactly what _reconcile step 2a does) and {route} did not see it. '
                f'first={first[route]} second={got}')

        # ...and the memo IS doing its job on the level below, or this test would pass
        # for the trivial reason that nothing is cached at all
        assert proc._stored_cache, 'no memo entries — the scope cached nothing'


def test_expand_tupleset_parents_matches_the_public_wrapper():
    """`_EvalContext.ttu_check` derives both halves locally from ONE
    `_stored_tupleset_subjects` call (R6-10 step A) instead of calling
    `tupleset_star_types` and `tupleset_parents` in turn. Pin that the local derivation
    is the same function as the public one — including the star expansion, the leaf
    ordering and the dedup — so the dedup cannot drift from the anchored wrappers."""
    session, widx, proc, write = _build(_RC2_SCHEMA)
    write('add', ('...', 'doc', 'd2', 'parent', 'doc', 'd1'))
    write('add', ('...', 'doc', 'd2', 'gate', 'doc', 'd1'))
    write('add', ('...', 'doc', '*', 'parent', 'doc', 'd1'))
    write('add', ('...', 'doc', '*', 'gate', 'doc', 'd1'))

    for leaf in proc._ts_leaf_predicates('doc', 'parent'):
        concretes, stars = proc._stored_tupleset_subjects('doc', 'd1', leaf, ('doc',))
        assert proc._expand_tupleset_parents(concretes, stars) == \
            proc.tupleset_parents('doc', 'd1', leaf, ('doc',))
        assert stars == proc.tupleset_star_types('doc', 'd1', leaf, ('doc',))

    split = proc._derived_stored_split('doc', 'd1', 'parent', ('doc',))
    assert split, 'no storage leaves — probe ran on nothing'
    assert proc._split_parents(split) == \
        proc.derived_stored_parents('doc', 'd1', 'parent', ('doc',))
    assert proc._split_star_types(split) == \
        proc.derived_stored_star_types('doc', 'd1', 'parent', ('doc',))
    assert proc._split_star_types(split) == ['doc'], proc._split_star_types(split)


def test_memoized_results_are_not_shared_mutable_state():
    """A cache hit must hand back a FRESH list, on BOTH memoized readers.

    `_stored_tupleset_subjects` and `stored_userset_subjects` each store an immutable
    snapshot on a miss (`tuple(out)`) and rebuild a list on a hit (`list(hit)`). A
    caller that mutates its result in place would otherwise corrupt every later hit on
    the same key within the cascade — silently, since nothing else re-reads the store.

    ⚠ THE USERSET HALF WAS ADDED BECAUSE A SABOTAGE CAME BACK GREEN (S4, module
    docstring). Until 2026-08-20 this test drove `_stored_tupleset_subjects` only, so
    `stored_userset_subjects`'s copy-on-hit was unpinned: weakening it to
    `cache[key] = out` / `return hit` left the whole 3-module suite at `36 passed`,
    while the identical weakening on the tupleset half (S5) reddened this test. That
    asymmetry was a coverage verdict, not a broken instrument
    (`docs/sabotage-procedure.md`: "a green sabotage is a finding, not a non-event").
    Drive both halves or the pin covers half of what it claims.
    """
    # --- tupleset half
    session, widx, proc, write = _build(_TTU_SCHEMA)
    write('add', ('...', 'folder', 'f1', 'parent', 'doc', 'd1'))
    key = ('doc', 'd1', 'parent', ('folder',))

    with proc._stored_cache_scope():
        c1, s1 = proc._stored_tupleset_subjects(*key)
        assert c1 == [('folder', 'f1')], c1
        c1.append(('folder', 'POISON'))
        s1.append('POISON')
        c2, s2 = proc._stored_tupleset_subjects(*key)
        assert c2 == [('folder', 'f1')] and s2 == [], (c2, s2)
        # ...and the SECOND hit must be clean too: mutating a hit's result must not
        # write back into the snapshot either.
        c2.append(('folder', 'POISON2'))
        c3, _s3 = proc._stored_tupleset_subjects(*key)
        assert c3 == [('folder', 'f1')], c3
        ts_hits = proc._stored_cache_stats['hits']
        assert ts_hits > 0, 'no hit — probe ran on nothing'
    session.close()

    # --- userset half (S4's blind spot)
    session, widx, proc, write = _build(_USERSET_SCHEMA)
    write('add', ('...', 'user', 'alice', 'member', 'group', 'g1'))
    write('add', ('member', 'group', 'g1', 'banned', 'doc', 'd1'))
    leaf, = [spec.predicate for spec in proc.compiled.plans[('doc', 'banned')].leaves
             if spec.storage]
    ukey = ('doc', 'd1', leaf, 'group', 'member')

    before = proc._stored_cache_stats['hits']
    with proc._stored_cache_scope():
        u1 = proc.stored_userset_subjects(*ukey)
        assert u1 == ['g1'], u1                      # non-vacuity: a real stored userset
        u1.append('POISON')
        u2 = proc.stored_userset_subjects(*ukey)
        assert u2 == ['g1'], (
            f'the userset memo handed back shared mutable state: {u2}')
        u2.append('POISON2')
        u3 = proc.stored_userset_subjects(*ukey)
        assert u3 == ['g1'], u3
        assert proc._stored_cache_stats['hits'] > before, (
            'no userset hit — probe ran on nothing (the memo was never consulted)')
    session.close()
