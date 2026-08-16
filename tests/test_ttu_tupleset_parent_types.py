"""
TTU tupleset parents that COMPILE-TIME metadata throws away: two live divergences.

**★ BOTH CAUSES ARE NOW FIXED — RC1 on 2026-08-10 (``ed46e54``), RC2 on 2026-08-11 — and
this module is GREEN. It stays as the regression pin for both.** Baseline for every
"measured" number below: commit ``e136c8c`` (``git show e136c8c:<file>``), 2026-08-10, with
the conda env under ``C:/Users/user/anaconda3/envs/graph-reachability-zanzibar-index``;
those numbers describe the BUGS, not the tree.

Per ``CLAUDE.md`` these are **positive pins, not xfails** (``verify.sh`` carries
``MAX_TESTS_XFAILED=0``): they assert the CORRECT behaviour, and they were red until the
graph was fixed. Do NOT weaken them, do NOT convert them to xfail, and do NOT edit the
oracle. If one goes red again, the divergence is live again.

**Read the "Fix locations" section below as a record of where the bugs WERE**, and see
``test_compile_refuses_parent_types_narrower_than_admission`` at the foot of this file:
RC1's class is now additionally refused at COMPILE time by an invariant that reads the
emitted filters rather than ``_member_types``, so it cannot recur silently.

## The invariant they guard (one sentence)

``CLAUDE.md``: *"**TTU parents are STORED tupleset tuples**, never computed membership
(oracle-pinned Zanzibar semantics)"* — so ``<target> from <tupleset>`` must walk **every
stored tuple on the tupleset relation**, whatever that relation's own rule says about the
parent and whatever *shape* the stored subject has.

Two separate compile-time/read-time filters violate that, each by silently narrowing the
set of stored tupleset tuples the graph is willing to look at.

## RC1 — a type that appears ONLY in the NEGATIVE arm of the tupleset relation

``zanzibar_utils_v1.py::_member_types`` handles ``Exclusion`` as ``return walk(e.base)``
(the docstring says so out loud: *"Exclusion members come from its base only"*). The
result is the ``parent_types`` tuple baked into ``PDerivedTTU`` / ``PDerivedTuplesetTTU``,
and ``index_v4/processor.py::tupleset_parents`` filters stored parents with
``n.type in parent_types``. So on ``define parent: [folder] but not [doc]`` the type
``doc`` never reaches ``parent_types`` and every stored ``doc``-typed parent is invisible
to the TTU.

Measured (schema in ``_RC1_SCHEMA`` / ``_RC1_SCHEMA_NEGATED_TTU``)::

    (1a)  check(alice, inherited, doc:d1)   oracle=True   graph=False  sets=[True, True]
    (1b)  check(alice, access,    doc:d1)   oracle=False  graph=True   sets=[False, False]

**(1b) is an authorization FAIL-OPEN.** The graph GRANTS ``access`` where the oracle and
both set engines DENY it, because the dropped parent is the one that would have satisfied
the *subtrahend* ``but not viewer from parent``.

⚠ This **corrects the filing of THIS bug**: the original filing in
``docs/spec-deviations.md``'s 2026-08-10 entry (kept struck through there, under
"Superseded original") classified it *"Fail-closed (under-grant),
so not a security fail-open"*. That was drawn from the ``inherited`` probe (1a) alone; the
same dropped parent under a NEGATED TTU inverts the sign. The general rule, which is what
makes this worth writing down: **a dropped TTU parent is a false NEGATIVE under a positive
TTU and a false POSITIVE under a negated one**, so any triage that probes only the positive
direction will mis-classify severity by exactly one sign.

⚠⚠ **NOT claimed here:** the 2026-08-09 sibling (the OWC x star-parent x TTU cross,
``spec-deviations.md:83``) carries the *same* "it fails closed, so it is not a security
fail-open" wording, and the rule above predicts it inverts too — but that was **not
re-tested**, because that bug is FIXED (``c042056``) and testing it would mean reverting the
fix. Treat it as an open question, not a correction. Do not propagate the prediction into
that entry as if it were measured.

## RC2 — a stored ``T:*`` tupleset parent, when the tupleset relation is DERIVED

``index_v4/processor.py::tupleset_parents`` also filters ``n.wildcard == ''``, so a stored
``(doc:*, parent, doc:d1)`` tuple — a legal ``[doc, doc:*]`` write, admitted by all three
backends — is not a TTU parent for the derived read path. No exclusion and no object
wildcard are needed; the tupleset relation just has to be tainted.

Measured (schema in ``_RC2_SCHEMA`` / ``_RC2_SCHEMA_NEGATED_TTU``)::

    (2a)  check(alice, inherited, doc:d1)   oracle=True   graph=False  sets=[True, True]
    (2b)  check(alice, access,    doc:d1)   oracle=False  graph=True   sets=[False, False]

(2b) is the fail-open direction, and it **was** reproducible: the sweep that reported it
was right. It is pinned below.

## ⚠ Correcting the record: the mechanism as ORIGINALLY FILED is WRONG

Both original filings — ``docs/spec-deviations.md`` 2026-08-10 and the ``HANDOFF.md`` item
since archived to ``docs/history/handoff-status-2026-08.md`` §1 "The two TTU-tupleset
divergences" (archived from ``HANDOFF.md`` 2026-08-16); both now carry the correction —
say the graph *"respects the boolean evaluation of the tupleset relation
instead of its stored tuples"* and that the storage-leaf split *"exists and is not being
honoured on a DERIVED tupleset relation"*. **Both clauses are false**, and acting on them
would rewrite correct leaf-routing code. Measured on the RC1 fixture, HEAD:

* the split IS applied — ``plan(doc,parent).leaves`` is
  ``(LeafSpec('parent.0', 'closure', positive=True, storage=True),
  LeafSpec('parent.1', 'closure', positive=False, storage=True))``;
* the write DOES land on a storage leaf — the only direct edges in the store are::

      doc:d2#...        (wildcard='') -> doc:d1#parent.1
      user:alice#...    (wildcard='') -> doc:d2#viewer

  and ``derived_stored_parents`` scans **every** ``spec.storage`` leaf, so it reaches that
  edge;
* the read path never EVALUATES ``parent``'s boolean plan — it consults the plan only for
  its storage-leaf name list (``_ts_leaf_predicates``).

The parent is dropped one step later, by metadata: ``parent_types=('folder',)`` for
``PDerivedTuplesetTTU(target_rel='viewer', tupleset_rel='parent', ...)``, because
``_member_types('doc', 'parent', ast, frozenset()) == frozenset({'folder'})``. RC2 is the
same read-time filter, different clause (``n.wildcard``): there the ``doc:*`` edge sits on
the *storage* leaf ``parent.0`` (``parent.1`` in that schema is ``storage=False``), so the
split is honoured there too::

      doc:*#...         (wildcard='any') -> doc:d1#parent.0     <== storage leaf
      doc:*#...         (wildcard='any') -> doc:d1#gate
      doc:*#...         (wildcard='any') -> doc:d1#parent.1     <== rule-routed leaf
      user:alice#...    (wildcard='')    -> doc:d2#viewer
      doc:d2#viewer     (wildcard='')    -> doc:*#viewer

## Fix locations — WHAT WAS DONE

* **RC1 (fixed 2026-08-10, ``ed46e54``)** — ``zanzibar_utils_v1.py::_member_types``:
  ``if isinstance(e, Exclusion): return walk(e.base)`` now unions the subtrahend's member
  types (a subtrahend restriction is still a *storable* subject type on the public
  relation, and stored-tuple TTU semantics do not care which arm admitted it). Its
  docstring encoded the same mistake and was rewritten with it. ``parent_types`` is
  compiled once and frozen onto the plan node, which ``processor.py`` and
  ``bulk_backfill.py`` merely READ, so this one edit repaired both paths.
* **RC2 (fixed 2026-08-11)** — the ``n.wildcard == ''`` clause was NOT simply deleted;
  see the sabotage note below for why that cannot work. Instead the two subject shapes are
  now split (``_stored_tupleset_subjects``) and given the two semantics the oracle and the
  set engine already implement:
  a stored ``T:*`` parent contributes **(a)** the shape ``(T, target_rel)``
  unconditionally -- carried by ``tupleset_star_types`` / ``derived_stored_star_types``
  into the ``_EvalContext`` TTU methods and thence the residue's ``stars`` -- and
  **(b)** an ∃-expansion over the tuple-mentioned instances of ``T``, folded into
  ``tupleset_parents`` so every downstream consumer (``_from_chain_keys``,
  ``_leaf_concretes``, ``_derived_leaf_neg_ids``) is correct with no edit.
  The cascade fan-out needed widening too (``_stored_parent_objects_of_entity`` and the
  ``'ttu'`` arm of ``_apply_deltas``): a star parent hangs off ``w_any``, not off the
  entity, so a later delta on some ``T:x`` would otherwise invalidate nothing and leave
  the dependent stale.
* **RC2 genuinely needed BOTH sites** — unlike RC1, whose ``parent_types`` is shared. The
  clause is duplicated verbatim in ``index_v4/bulk_backfill.py::_tupleset_parents``, so
  the offline bulk bootstrap would otherwise have kept the divergence alive. The
  ``rc2_star_tupleset`` corpus in ``tests/test_bulk_build.py`` now pins that: reverting
  the bulk half alone takes it from ``7 passed`` to
  ``1 failed, 6 passed`` (``[rc2_star_tupleset] snapshot_rows differ``), where before the
  corpus existed the same one-sided edit left the suite green.
  ``bulk_backfill.py``'s ``_stored_userset_subjects`` still carries a ``w2 == ''`` clause
  for stored USERSETS -- deliberately untouched, and not part of either root cause.

## Sabotage evidence (docs/sabotage-procedure.md — literal observed output)

* **Subject, RC1 (confirms the named fix location).** Monkeypatching ``_member_types``'s
  ``Exclusion`` branch to ``walk(e.base) | walk(e.subtract)`` and re-running the two RC1
  probes in-process::

      --- BASELINE (unpatched _member_types) ---
      RC1a inherited: oracle=True graph=False sets=[True, True]
      RC1b access   : oracle=False graph=True  sets=[False, False]
      --- WITH _member_types Exclusion -> base | subtract ---
      RC1a inherited: oracle=True graph=True  sets=[True, True]
      RC1b access   : oracle=False graph=False sets=[False, False]

  Both pins go green under exactly that one-line change and nothing else moves.
* **Subject, RC2 (confirms the location, refutes the obvious patch).** Monkeypatching
  ``DeltaProcessor.tupleset_parents`` to drop the ``n.wildcard == ''`` clause and nothing
  else does NOT fix RC2 — it breaks admission parity before the query is ever asked::

      AssertionError: accept/reject divergence on add
      ('...', 'doc', '*', 'parent', 'doc', 'd1'): graph=False set:py=True

  So the filter is the drop point, but the fix has to expand/represent the star parent
  (the set engine's ``MemberSet.stars`` algebra is the analogue), not merely admit a
  ``('doc', '*')`` pair into the parent list. Recorded here so the next person does not
  ship the one-liner.
* **Instrument, both directions.** The instrument (``_answers``) is controlled from both
  sides in this file: the seven ``*_positive_control`` / ``*_negative_control`` tests are
  states where it must report agreement (and does, today), and the four pins are states
  where it must report a divergence (and does, today). A harness that always reported
  "graph == oracle" would make the pins pass; a harness that always reported a divergence
  would make the controls fail. Both halves must stay in this file.

## Honest limits

* Every schema here is a **hand-minimised repro**, not a drawn example. No claim is made
  that the hypothesis campaign or any conformance corpus reaches these shapes — the
  evidence is that they were green while these divergences were live, which is the
  "green by seed luck" failure mode ``CLAUDE.md`` already names.
* RC1 and RC2 are **independent**: fixing ``_member_types`` left RC2 red (verified in
  process — RC2 still reported ``oracle=True graph=False sets=[True, True]`` with the RC1
  patch applied), and vice versa. That is why they were fixed and pinned separately.
* Nothing in THIS file exercises the ``bulk_backfill.py`` copies — that gap is now closed
  elsewhere, by the ``rc2_star_tupleset`` corpus in ``tests/test_bulk_build.py``, which
  was added with the fix precisely because that gate was measured BLIND to this direction.
* Nothing here is claimed about the Lean model beyond what ``formal/CORRESPONDENCE.md``
  §7 records for this change.
"""

import pytest

from tests.oracle import Oracle, OracleTuple
from tests.test_lookup_oracle import _Gate

# ---------------------------------------------------------------------------
# The instrument
# ---------------------------------------------------------------------------

_NO_OBJECT_WILDCARDS = frozenset()


def _answers(schema, pool, adds, query):
    """(oracle, graph, [set engines]) for ``query`` after adding ``adds``.

    ``pool`` only seeds ``_Gate``'s candidate names; ``adds`` is the store. Admission is
    asserted to accept every add, in lockstep across all three backends (``_Gate.apply``
    fails loudly on an accept/reject divergence), so a pin can never be "explained" by one
    backend having quietly refused the write.
    """
    gate = _Gate(schema, _NO_OBJECT_WILDCARDS, pool)
    try:
        for raw in adds:
            assert gate.apply('add', raw), f'admission rejected {raw}'
        oracle = Oracle(schema, [OracleTuple(*r) for r in gate.present])
        return (oracle.check(*query),
                gate.graph.widx.check(*query),
                [side.se.check(*query) for side in gate.sets])
    finally:
        gate.close()


def _assert_parity(oracle, graph, sets, expected_oracle, what):
    """Oracle first, then the set engines, then the graph — so a future failure is
    self-diagnosing: if the first assertion trips the SPEC moved (re-adjudicate before
    touching anything), if the second trips the set engines regressed, and only the third
    is the graph divergence this module pins."""
    assert oracle is expected_oracle, \
        'the oracle is the spec; if this flipped, re-adjudicate first'
    assert all(s == oracle for s in sets), \
        f'both set engines must agree with the oracle: oracle={oracle} sets={sets}'
    assert graph == oracle, (
        f'{what}: graph={graph} oracle={oracle} sets={sets} '
        f'(the graph index is the odd one out, three backends to one)')


# ---------------------------------------------------------------------------
# RC1 fixtures — the tupleset relation's negative arm carries the parent type
# ---------------------------------------------------------------------------

_RC1_HEAD = """model
  schema 1.1

type user

type folder
  relations
    define viewer: [user]

type doc
  relations
    define parent: {parent}
    define viewer: [user]
    define inherited: viewer from parent
"""
_RC1_ACCESS = '    define access: [user] but not viewer from parent\n'

# the divergent schema: `doc` reachable ONLY through the subtrahend
_RC1_SCHEMA = _RC1_HEAD.format(parent='[folder] but not [doc]')
_RC1_SCHEMA_NEGATED_TTU = _RC1_SCHEMA + _RC1_ACCESS

# control schema: the SAME composition with `doc` in BOTH arms
_RC1_CONTROL_SCHEMA = _RC1_HEAD.format(parent='[folder, doc] but not [doc]')
_RC1_CONTROL_SCHEMA_NEGATED_TTU = _RC1_CONTROL_SCHEMA + _RC1_ACCESS

# control schema: an Exclusion whose right arm is a COMPUTED relation, not a Direct
_RC1_COMPUTED_ARM_SCHEMA = """model
  schema 1.1

type user

type folder
  relations
    define viewer: [user]

type doc
  relations
    define blocked: [doc]
    define parent: [folder, doc] but not blocked
    define viewer: [user]
    define inherited: viewer from parent
""" + _RC1_ACCESS

_RC1_POOL = [
    ('...', 'doc', 'd2', 'parent', 'doc', 'd1'),
    ('...', 'user', 'alice', 'viewer', 'doc', 'd2'),
    ('...', 'user', 'alice', 'access', 'doc', 'd1'),
    ('...', 'folder', 'f1', 'parent', 'doc', 'd1'),
    ('...', 'user', 'alice', 'viewer', 'folder', 'f1'),
]

_RC1_STORED_PARENT = ('...', 'doc', 'd2', 'parent', 'doc', 'd1')
_RC1_VIEWER_ON_PARENT = ('...', 'user', 'alice', 'viewer', 'doc', 'd2')
_RC1_ACCESS_GRANT = ('...', 'user', 'alice', 'access', 'doc', 'd1')

_RC1_INHERITED_Q = ('...', 'user', 'alice', 'inherited', 'doc', 'd1')
_RC1_ACCESS_Q = ('...', 'user', 'alice', 'access', 'doc', 'd1')


def test_rc1_positive_control_type_in_both_arms():
    """CONTROL (green today, must stay green through the fix).

    Identical composition to the RC1 pin — same tuples, same query, same
    ``[...] but not [doc]`` exclusion on the tupleset relation — except that ``doc`` also
    appears in the POSITIVE arm, so ``_member_types`` puts it in ``parent_types`` anyway.
    Measured: oracle=True graph=True sets=[True, True]. Note the stored parent ``doc:d2``
    is still EXCLUDED from ``parent`` by the ``but not`` (all four backends agree on
    ``check(doc:d2, parent, doc:d1)``), so this control also demonstrates the stored-tuple
    TTU semantics working on a derived tupleset relation.

    This proves the harness, the schema, the admission path and the query are sound, so a
    failure of the pin below is about ``parent_types`` and nothing else.

    Do not weaken: if this ever goes red, the fix at
    ``zanzibar_utils_v1.py::_member_types`` broke a case that already worked.
    """
    oracle, graph, sets = _answers(
        _RC1_CONTROL_SCHEMA, _RC1_POOL,
        [_RC1_STORED_PARENT, _RC1_VIEWER_ON_PARENT], _RC1_INHERITED_Q)
    _assert_parity(oracle, graph, sets, True, 'RC1 control (type in both arms)')


def test_rc1_negative_control_no_stored_tupleset_tuple():
    """CONTROL / non-vacuity (green today, must stay green through the fix).

    The RC1 schema and query with the stored tupleset tuple OMITTED: ``doc:d1`` has no
    parent at all, so nothing may be inherited. Measured: oracle=False graph=False
    sets=[False, False]. This is the instrument's negative control — it proves the pin
    below expects True for a REASON (the stored ``(doc:d2, parent, doc:d1)`` tuple) rather
    than because this query is unconditionally true.

    Do not weaken: this must stay False after ``zanzibar_utils_v1.py::_member_types`` is
    fixed. A fix that makes it True has invented a parent.
    """
    oracle, graph, sets = _answers(
        _RC1_SCHEMA, _RC1_POOL, [_RC1_VIEWER_ON_PARENT], _RC1_INHERITED_Q)
    _assert_parity(oracle, graph, sets, False, 'RC1 negative control (no stored parent)')


def test_rc1_negative_arm_type_is_still_a_stored_ttu_parent():
    """★ CURRENTLY RED — RC1, fail-closed direction (the graph under-grants).

    Property guarded: a TTU walks every STORED tupleset tuple, including one whose subject
    type reaches the tupleset relation only through the exclusion's SUBTRAHEND
    (``define parent: [folder] but not [doc]`` — ``doc`` is a storable subject type on
    ``parent``, so ``(doc:d2, parent, doc:d1)`` is a stored parent of ``doc:d1``).

    Measured at ``e136c8c``: oracle=True graph=False sets=[True, True] — three backends to
    one. Cause: ``_member_types('doc', 'parent', ast, frozenset()) == {'folder'}``, so the
    compiled ``PDerivedTuplesetTTU`` carries ``parent_types=('folder',)`` and
    ``index_v4/processor.py::tupleset_parents`` filters the ``doc``-typed parent out with
    ``n.type in parent_types``. The write itself lands correctly, on storage leaf
    ``doc:d1#parent.1`` (module docstring).

    Do NOT weaken this to ``graph is False`` and do NOT xfail it. Fix
    ``zanzibar_utils_v1.py::_member_types`` (the ``Exclusion`` branch must union
    ``walk(e.subtract)``), and mirror it into ``index_v4/bulk_backfill.py:453-455``.
    """
    oracle, graph, sets = _answers(
        _RC1_SCHEMA, _RC1_POOL,
        [_RC1_STORED_PARENT, _RC1_VIEWER_ON_PARENT], _RC1_INHERITED_Q)
    _assert_parity(
        oracle, graph, sets, True,
        'RC1: the graph drops a stored TTU parent whose type appears only in the '
        'negative arm of the tupleset relation (parent_types is missing "doc")')


def test_rc1_positive_control_negated_ttu_type_in_both_arms():
    """CONTROL for the fail-open pin (green today, must stay green through the fix).

    Same schema as ``test_rc1_positive_control_type_in_both_arms`` plus
    ``define access: [user] but not viewer from parent``, same tuples plus the direct
    ``access`` grant. With ``doc`` in the positive arm the subtrahend sees the stored
    parent and correctly cancels the grant. Measured: oracle=False graph=False
    sets=[False, False].

    Do not weaken: this pins that the NEGATED TTU is wired up at all, so the fail-open pin
    below cannot be dismissed as "the subtrahend never fires in this schema shape".
    """
    oracle, graph, sets = _answers(
        _RC1_CONTROL_SCHEMA_NEGATED_TTU, _RC1_POOL,
        [_RC1_STORED_PARENT, _RC1_VIEWER_ON_PARENT, _RC1_ACCESS_GRANT], _RC1_ACCESS_Q)
    _assert_parity(oracle, graph, sets, False,
                   'RC1 control (negated TTU, type in both arms)')


def test_rc1_positive_control_negated_ttu_computed_right_arm():
    """CONTROL (green today, must stay green through the fix).

    The exclusion's right arm is a COMPUTED relation (``but not blocked`` where
    ``blocked: [doc]``) rather than an inline ``[doc]``, with ``doc`` in the left arm.
    ``_member_types`` reaches ``doc`` through ``walk(e.base)``, the negated TTU cancels the
    grant, and everything agrees. Measured: oracle=False graph=False sets=[False, False].

    This is the second half of the control pair: it shows the ``Exclusion`` node shape per
    se is not what breaks, only which ARM the parent type comes from.

    Do not weaken: a fix at ``zanzibar_utils_v1.py::_member_types`` that unions the
    subtrahend must keep this exact answer.
    """
    oracle, graph, sets = _answers(
        _RC1_COMPUTED_ARM_SCHEMA, _RC1_POOL,
        [_RC1_STORED_PARENT, _RC1_VIEWER_ON_PARENT, _RC1_ACCESS_GRANT], _RC1_ACCESS_Q)
    _assert_parity(oracle, graph, sets, False,
                   'RC1 control (negated TTU, computed right arm)')


def test_rc1_negative_arm_type_dropped_is_an_authorization_fail_open():
    """★★ CURRENTLY RED — RC1, FAIL-OPEN direction. Pin this one hardest.

    Same dropped parent as the pin above, read through a NEGATED TTU:
    ``define access: [user] but not viewer from parent``. Because the graph cannot see the
    stored parent ``doc:d2``, the subtrahend is empty for it and the direct ``access``
    grant survives.

    Measured at ``e136c8c``: oracle=False graph=True sets=[False, False].
    **The graph GRANTS what the oracle and both set engines DENY.** This is an
    authorization fail-open, not an under-grant.

    ⚠ This CORRECTS the record. ``docs/spec-deviations.md`` (2026-08-10 entry) and the
    ``HANDOFF.md`` item since archived to ``docs/history/handoff-status-2026-08.md`` §1
    "The two TTU-tupleset divergences" (archived from ``HANDOFF.md`` 2026-08-16)
    originally classified this bug as *"Fail-closed (under-grant), so not a security
    fail-open"*.
    That conclusion was reached from the ``inherited`` probe only; one extra relation in
    the SAME schema inverts the sign. The bug is a live authorization fail-open and should
    be triaged as one.

    Do NOT weaken this to ``graph is True`` and do NOT xfail it. Fix
    ``zanzibar_utils_v1.py::_member_types`` (Exclusion must union the subtrahend), then
    ``index_v4/bulk_backfill.py:453-455``.
    """
    oracle, graph, sets = _answers(
        _RC1_SCHEMA_NEGATED_TTU, _RC1_POOL,
        [_RC1_STORED_PARENT, _RC1_VIEWER_ON_PARENT, _RC1_ACCESS_GRANT], _RC1_ACCESS_Q)
    _assert_parity(
        oracle, graph, sets, False,
        'RC1 FAIL-OPEN: the graph grants `access` because it dropped the stored TTU '
        'parent that the `but not viewer from parent` subtrahend needed')


# ---------------------------------------------------------------------------
# RC2 fixtures — a stored `T:*` tupleset parent on a DERIVED tupleset relation
# ---------------------------------------------------------------------------

_RC2_HEAD = """model
  schema 1.1

type user

type doc
  relations
    define gate: [doc, doc:*]
    define parent: {parent}
    define viewer: [user]
    define inherited: viewer from parent
"""

# divergent: `parent` is TAINTED (`and gate`), so the derived read path is used
_RC2_SCHEMA = _RC2_HEAD.format(parent='[doc, doc:*] and gate')
_RC2_SCHEMA_NEGATED_TTU = _RC2_SCHEMA + _RC1_ACCESS

# control: identical shape with an UNTAINTED tupleset relation
_RC2_CONTROL_SCHEMA = _RC2_HEAD.format(parent='[doc, doc:*]')

_RC2_POOL = [
    ('...', 'doc', '*', 'parent', 'doc', 'd1'),
    ('...', 'doc', '*', 'gate', 'doc', 'd1'),
    ('...', 'user', 'alice', 'viewer', 'doc', 'd2'),
    ('...', 'doc', 'd2', 'parent', 'doc', 'd1'),
    ('...', 'doc', 'd2', 'gate', 'doc', 'd1'),
    ('...', 'user', 'alice', 'access', 'doc', 'd1'),
]

_RC2_STAR_PARENT = ('...', 'doc', '*', 'parent', 'doc', 'd1')
_RC2_STAR_GATE = ('...', 'doc', '*', 'gate', 'doc', 'd1')
_RC2_CONCRETE_PARENT = ('...', 'doc', 'd2', 'parent', 'doc', 'd1')
_RC2_CONCRETE_GATE = ('...', 'doc', 'd2', 'gate', 'doc', 'd1')
_RC2_VIEWER_ON_PARENT = ('...', 'user', 'alice', 'viewer', 'doc', 'd2')
_RC2_ACCESS_GRANT = ('...', 'user', 'alice', 'access', 'doc', 'd1')

_RC2_INHERITED_Q = ('...', 'user', 'alice', 'inherited', 'doc', 'd1')
_RC2_ACCESS_Q = ('...', 'user', 'alice', 'access', 'doc', 'd1')


def test_rc2_positive_control_concrete_stored_parent_on_derived_tupleset():
    """CONTROL (green today, must stay green through the fix). The tight one.

    The SAME derived tupleset relation (``define parent: [doc, doc:*] and gate``) and the
    same query, with a CONCRETE stored parent ``doc:d2`` instead of ``doc:*``. Measured:
    oracle=True graph=True sets=[True, True].

    This isolates the defect to the ``n.wildcard == ''`` clause alone: the derived-tupleset
    TTU read path (``derived_stored_parents`` -> ``tupleset_parents`` over the storage
    leaves of a tainted tupleset relation) demonstrably works here, so the pin below cannot
    be explained by "derived tuplesets are broken in general".

    Do not weaken: a fix at ``index_v4/processor.py::tupleset_parents`` must keep this True.
    """
    oracle, graph, sets = _answers(
        _RC2_SCHEMA, _RC2_POOL,
        [_RC2_CONCRETE_PARENT, _RC2_CONCRETE_GATE, _RC2_VIEWER_ON_PARENT],
        _RC2_INHERITED_Q)
    _assert_parity(oracle, graph, sets, True,
                   'RC2 control (concrete stored parent on a derived tupleset)')


def test_rc2_positive_control_star_parent_on_untainted_tupleset():
    """CONTROL (green today, must stay green through the fix).

    The same ``doc:*`` stored tupleset parent, but with ``define parent: [doc, doc:*]``
    (UNTAINTED — no ``and gate``). Measured: oracle=True graph=True sets=[True, True].

    Honest limit: an untainted tupleset makes ``inherited`` untainted too, so this exercises
    the ordinary closure path, NOT the delta processor. It controls the star-parent x TTU
    COMPOSITION (the write shape and the query are fine, and the graph handles them when it
    is not going through ``tupleset_parents``); the control for the derived read path is
    ``test_rc2_positive_control_concrete_stored_parent_on_derived_tupleset`` above. Both are
    needed, neither substitutes for the other.

    Do not weaken: a fix must not regress the untainted path.
    """
    oracle, graph, sets = _answers(
        _RC2_CONTROL_SCHEMA, _RC2_POOL,
        [_RC2_STAR_PARENT, _RC2_VIEWER_ON_PARENT], _RC2_INHERITED_Q)
    _assert_parity(oracle, graph, sets, True,
                   'RC2 control (star parent on an untainted tupleset)')


def test_rc2_star_stored_parent_on_derived_tupleset_is_a_ttu_parent():
    """★ CURRENTLY RED — RC2, fail-closed direction (the graph under-grants).

    Property guarded: a stored ``T:*`` tupleset tuple is a TTU parent, on a DERIVED
    tupleset relation exactly as on an untainted one. ``(doc:*, parent, doc:d1)`` is a
    legal ``[doc, doc:*]`` write, admitted by all three backends.

    Measured at ``e136c8c``: oracle=True graph=False sets=[True, True]. No exclusion and no
    ``object_wildcard_shapes`` are involved — the tupleset relation only has to be tainted.
    Cause: ``index_v4/processor.py::tupleset_parents`` filters ``n.wildcard == ''``, and the
    ``doc:*`` subject node has ``wildcard='any'``. The edge is on the STORAGE leaf
    (``doc:*#... -> doc:d1#parent.0``, ``storage=True``), so the storage-leaf split is
    honoured; only this filter drops it.

    Do NOT weaken and do NOT xfail. Fix ``index_v4/processor.py::tupleset_parents`` — but
    see the module docstring: naively deleting the clause breaks admission parity, the star
    parent has to be represented, not just admitted. Mirror into
    ``index_v4/bulk_backfill.py:453-455``.
    """
    oracle, graph, sets = _answers(
        _RC2_SCHEMA, _RC2_POOL,
        [_RC2_STAR_PARENT, _RC2_STAR_GATE, _RC2_VIEWER_ON_PARENT], _RC2_INHERITED_Q)
    _assert_parity(
        oracle, graph, sets, True,
        'RC2: the graph drops a stored `doc:*` TTU parent when the tupleset relation is '
        'DERIVED (the n.wildcard == "" filter in tupleset_parents)')


def test_rc2_positive_control_negated_ttu_concrete_parent():
    """CONTROL for the RC2 fail-open pin (green today, must stay green through the fix).

    ``define access: [user] but not viewer from parent`` over the same derived tupleset,
    with a CONCRETE stored parent. The subtrahend sees the parent and cancels the grant.
    Measured: oracle=False graph=False sets=[False, False].

    Do not weaken: this pins that the negated TTU over a DERIVED tupleset is wired up, so
    the fail-open pin below is about the star parent alone.
    """
    oracle, graph, sets = _answers(
        _RC2_SCHEMA_NEGATED_TTU, _RC2_POOL,
        [_RC2_CONCRETE_PARENT, _RC2_CONCRETE_GATE, _RC2_VIEWER_ON_PARENT,
         _RC2_ACCESS_GRANT], _RC2_ACCESS_Q)
    _assert_parity(oracle, graph, sets, False,
                   'RC2 control (negated TTU, concrete stored parent)')


def test_rc2_star_stored_parent_dropped_is_an_authorization_fail_open():
    """★★ CURRENTLY RED — RC2, FAIL-OPEN direction. Reproduced, so pinned.

    The sweep that reported an RC2 fail-open direction was right, and this is it: the same
    dropped ``doc:*`` parent read through ``define access: [user] but not viewer from
    parent``. The graph cannot see the star parent, so the subtrahend is empty and the
    direct ``access`` grant survives.

    Measured at ``e136c8c``: oracle=False graph=True sets=[False, False].
    **The graph GRANTS what the oracle and both set engines DENY.**

    So BOTH root causes in this file have a fail-open direction, by the same mechanism: a
    dropped TTU parent is a false negative under a positive TTU and a false POSITIVE under
    a negated one. Any triage that reads either one as "fails closed" is looking at half
    the schema.

    Do NOT weaken and do NOT xfail. Fix ``index_v4/processor.py::tupleset_parents``, then
    ``index_v4/bulk_backfill.py:453-455``.
    """
    oracle, graph, sets = _answers(
        _RC2_SCHEMA_NEGATED_TTU, _RC2_POOL,
        [_RC2_STAR_PARENT, _RC2_STAR_GATE, _RC2_VIEWER_ON_PARENT, _RC2_ACCESS_GRANT],
        _RC2_ACCESS_Q)
    _assert_parity(
        oracle, graph, sets, False,
        'RC2 FAIL-OPEN: the graph grants `access` because it dropped the stored `doc:*` '
        'TTU parent that the `but not viewer from parent` subtrahend needed')


# =========================================================================== #
# The compile-time invariant landed with the RC2 fix (2026-08-11)
# =========================================================================== #

def test_compile_refuses_parent_types_narrower_than_admission():
    """★ The RC1/RC2 class caught at COMPILE time, by an instrument that is NOT a mirror.

    Property guarded: a TTU's compiled ``parent_types`` covers every bare-entity type
    ADMISSION accepts onto that tupleset relation. If it does not, a stored tupleset
    tuple of the missing type is silently not a TTU parent -- a false negative under a
    positive TTU and an authorization FAIL-OPEN under a negated one.

    ★★ WHY THIS TEST EXISTS RATHER THAN TRUSTING I9. Invariant I9 audits the cascade by
    re-running ``reconcile``, which reads the same compile-time ``parent_types`` its
    subject reads -- so it agrees with itself and stayed GREEN through both live
    authorization fail-opens with paranoia ON. It is a MIRROR
    (``docs/sabotage-procedure.md``). ``_assert_ttu_parent_types_cover_admission``
    derives its expectation from the emitted ``RewriteFilter``/``Filter`` patterns
    instead, which are built from the ``Restriction``s directly, so a ``_member_types``
    defect moves the subject and not the check.

    SABOTAGE (literal output). This test IS the sabotage, made permanent: it narrows
    ``parent_types`` exactly the way RC1 did (the subtrahend's type never arrives) and
    asserts compilation refuses. Verified by hand 2026-08-11 against the REAL defect --
    reverting ``_member_types``' Exclusion arm to ``return walk(e.base)`` in the source
    and compiling ``parent: [folder] but not [doc]`` produced::

        ValueError: TTU 'viewer' from 'parent' in doc#inherited: compiled parent_types
        ('folder',) omits type(s) ['doc'] that ADMISSION accepts onto doc#parent. A
        stored tupleset tuple of that type would be silently dropped as a TTU parent
        (fail-open under a negated TTU). This is the RC1 class -- suspect _member_types,
        not this check.

    and restoring the arm compiled clean again.
    """
    import zanzibar_utils_v1 as zu

    schema = ('model\n  schema 1.1\n\ntype user\n\ntype folder\n\ntype doc\n'
              '  relations\n'
              '    define parent: [folder] but not [doc]\n'
              '    define viewer: [user]\n'
              '    define inherited: viewer from parent\n')

    # control: the tree as it stands compiles, so the red below is the sabotage's doing
    zu.parse_openfga_schema(schema)

    real = zu._member_types

    def rc1_narrowed(object_type, relation, ast, seen):
        """RC1 in its essential form: the subtrahend's type never reaches parent_types."""
        out = real(object_type, relation, ast, seen)
        if (object_type, relation) == ('doc', 'parent'):
            out = out - {'doc'}
        return out

    zu._member_types = rc1_narrowed
    try:
        with pytest.raises(ValueError) as ei:
            zu.parse_openfga_schema(schema)
    finally:
        zu._member_types = real

    msg = str(ei.value)
    assert 'omits type(s)' in msg and "'doc'" in msg, msg
    assert 'ADMISSION accepts' in msg, msg
    # and the tree is genuinely restored -- otherwise this test would poison the module
    zu.parse_openfga_schema(schema)
