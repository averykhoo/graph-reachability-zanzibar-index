"""
TTU tupleset parents that COMPILE-TIME metadata throws away: two live divergences.

**★ BOTH CAUSES ARE NOW FIXED — RC1 on 2026-08-10 (``ed46e54``), RC2 on 2026-08-11 — and
this module is GREEN. It stays as the regression pin for both.**

**★★ TK106 (2026-09-26, user decision): a tupleset must be DIRECT-ONLY, as in OpenFGA.**
Both hand-minimised repros below used a BOOLEAN tupleset (RC1 ``[folder] but not [doc]``,
RC2 ``[doc, doc:*] and gate``), and both are now parse refusals. RC1's shape is therefore
unwritable and is pinned as a refusal (``test_rc1_shape_is_refused_by_every_backend``),
with its CLASS pinned on the path that stays live (a multi-type direct tupleset under a
derived target). RC2's fix site is shared with that live path, so its pins moved to a
direct ``[folder, doc, doc:*]`` tupleset and were re-sabotaged there (the RC2 section
comment). Everything below this paragraph is the record as it stood; the schemas it quotes
are the pre-TK106 ones. Baseline for every
"measured" number below: commit ``e136c8c`` (``git show e136c8c:<file>``), 2026-08-10, with
the conda env under ``C:/Users/user/anaconda3/envs/graph-reachability-zanzibar-index``;
those numbers describe the BUGS, not the tree.

Per ``CLAUDE.md`` these are **positive pins, not xfails** (``verify.sh`` carries
``MAX_TESTS_XFAILED=0``): they assert the CORRECT behaviour, and they were red until the
graph was fixed. Do NOT weaken them, do NOT convert them to xfail, and do NOT edit the
oracle. If one goes red again, the divergence is live again.

⚠⚠ **KNOWN LIMITATION — do NOT treat this module as the net for star-expansion LIVENESS.**
Every test here writes its pool in ONE batch and then queries, so it pins that a star
tupleset parent *is* expanded and pins nothing about the expansion staying *live* across a
cascade that interns or GCs nodes. Measured 2026-08-20b: freezing the expansion (memoizing
``processor.py::DeltaProcessor.tupleset_parents``, and separately ``::derived_stored_parents``
and ``::_instances_of_type``) leaves **all 12 tests here green** — and so are
``test_matrix.py`` (``24 passed``) and ``test_lookup_oracle.py`` (2026-08-20b, before
TK106 changed this module's test count). The only pin for liveness
is ``test_stored_cache_scope.py::test_star_expansion_is_not_frozen_by_the_memo``. The same
limitation was recorded for a different fix in the ``## 2026-07-26`` entry of
``docs/spec-deviations.md`` ("those write in one batch and reconcile once") and was not
carried here, so it had to be re-discovered by sabotage; see ``docs/sabotage-procedure.md``
§'"The only net" is a claim about a test'.

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

⚠⚠ **NOT claimed here:** the 2026-08-09 sibling (the OWC x star-parent x TTU cross, the
``## 2026-08-09`` entry of ``docs/spec-deviations.md``) carries the *same* "it fails closed, so it is not a security
fail-open" wording, and the rule above predicts it inverts too — but that was **not
re-tested**, because that bug is FIXED (``c042056``) and testing it would mean reverting the
fix. Treat it as an open question, not a correction. Do not propagate the prediction into
that entry as if it were measured.

(2026-09-27, ``P12``: now MEASURED on the pre-fix tree -- the prediction held, fail-OPEN
under a negated consumer. ``tests/test_p12_severity_sign.py``; ``docs/spec-deviations.md``
2026-09-27b.)

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
# RC1 — the shape is REFUSED since TK106 (2026-09-26)
# ---------------------------------------------------------------------------
#
# RC1 needed a type that reaches the tupleset only through a `but not` arm. TK106 (user
# decision, as OpenFGA does) made every non-direct tupleset a parse refusal, so the shape
# cannot be written and the class is structurally impossible: `_member_types` now only
# ever walks a Direct or a union of Directs. The six RC1 tests that stood here (two pins,
# four controls; `git show 9d1bedf:tests/test_ttu_tupleset_parent_types.py`) are replaced
# by (a) a refusal pin over every RC1 schema they used, and (b) the RC1 CLASS on the path
# that is still live: `parent_types` breadth on a MULTI-TYPE direct tupleset under a
# DERIVED target, where a missing type would drop stored parents exactly as RC1 did.

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

_RC1_REFUSED = {
    'rc1': _RC1_HEAD.format(parent='[folder] but not [doc]'),
    'rc1-negated-ttu': _RC1_HEAD.format(parent='[folder] but not [doc]') + _RC1_ACCESS,
    'rc1-control-type-in-both-arms': _RC1_HEAD.format(parent='[folder, doc] but not [doc]'),
    'rc1-control-computed-right-arm': _RC1_HEAD.format(
        parent='[folder, doc] but not blocked').replace(
            '    define parent:', '    define blocked: [doc]\n    define parent:'),
}


@pytest.mark.parametrize('name', sorted(_RC1_REFUSED))
def test_rc1_shape_is_refused_by_every_backend(name):
    """★ RC1's pin since TK106 (2026-09-26): the shape is refused, by the graph, both set
    engines and the oracle alike (`_Gate` builds all of them), so it cannot be stored.
    Before TK106 the graph compiled it and, while RC1 was live, answered
    `inherited` False and the negated `access` True (a fail-open) where the other three
    backends said True / False."""
    from tests.oracle import parse_schema_ast as oracle_parse
    from zanzibar_utils_v1 import parse_schema_ast
    schema = _RC1_REFUSED[name]
    for build in (parse_schema_ast, oracle_parse,
                  lambda s: _Gate(s, _NO_OBJECT_WILDCARDS, _RC1_POOL)):
        with pytest.raises(ValueError, match='tupleset must be direct'):
            build(schema)


# The RC1 class on the live path. Both viewers are DERIVED, so `inherited` / `access`
# compile to `PDerivedTTU` with `parent_types` ('doc', 'folder'); dropping 'doc' there is
# RC1's mechanism (and `test_compile_refuses_parent_types_narrower_than_admission` refuses
# it at compile time).
_RC1_LIVE_SCHEMA = """model
  schema 1.1

type user

type folder
  relations
    define banned: [user]
    define viewer: [user] but not banned

type doc
  relations
    define banned: [user]
    define parent: [folder, doc]
    define viewer: [user] but not banned
    define inherited: viewer from parent
"""
_RC1_LIVE_SCHEMA_NEGATED_TTU = _RC1_LIVE_SCHEMA + _RC1_ACCESS

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


def test_rc1_class_negative_control_no_stored_tupleset_tuple():
    """CONTROL / non-vacuity: no stored parent, so nothing may be inherited. Proves the
    pins below expect True / False for a REASON (the stored ``(doc:d2, parent, doc:d1)``
    tuple). Measured 2026-09-26: oracle=False graph=False sets=[False, False]."""
    oracle, graph, sets = _answers(
        _RC1_LIVE_SCHEMA, _RC1_POOL, [_RC1_VIEWER_ON_PARENT], _RC1_INHERITED_Q)
    _assert_parity(oracle, graph, sets, False, 'RC1 class, negative control (no parent)')


def test_rc1_class_second_tupleset_type_is_a_ttu_parent():
    """★ The RC1 class, fail-closed direction, on a legal tupleset: a stored parent of the
    tupleset's SECOND type (``doc``) is a TTU parent of a derived target. Measured
    2026-09-26: oracle=True graph=True sets=[True, True]."""
    oracle, graph, sets = _answers(
        _RC1_LIVE_SCHEMA, _RC1_POOL,
        [_RC1_STORED_PARENT, _RC1_VIEWER_ON_PARENT], _RC1_INHERITED_Q)
    _assert_parity(oracle, graph, sets, True,
                   'RC1 class: a stored parent of the tupleset\'s second type')


def test_rc1_class_second_tupleset_type_dropped_would_fail_open():
    """★★ The RC1 class, FAIL-OPEN direction: the same parent under
    ``access: [user] but not viewer from parent``. A graph that dropped ``doc`` from
    ``parent_types`` would see an empty subtrahend and GRANT. Measured 2026-09-26:
    oracle=False graph=False sets=[False, False]."""
    oracle, graph, sets = _answers(
        _RC1_LIVE_SCHEMA_NEGATED_TTU, _RC1_POOL,
        [_RC1_STORED_PARENT, _RC1_VIEWER_ON_PARENT, _RC1_ACCESS_GRANT], _RC1_ACCESS_Q)
    _assert_parity(oracle, graph, sets, False,
                   'RC1 class FAIL-OPEN: the negated TTU must see the second-type parent')


# ---------------------------------------------------------------------------
# RC2 — a stored `T:*` tupleset parent under a DERIVED target
# ---------------------------------------------------------------------------
#
# Until TK106 (2026-09-26) these pins used `parent: [doc, doc:*] and gate`, a DERIVED
# tupleset, which is now a parse refusal. The fix site is still live:
# `index_v4/processor.py::_stored_tupleset_subjects` / `::_expand_tupleset_parents` are
# shared with the `derived-ttu` path (untainted tupleset, derived target). So the star
# parent now reaches them through `folder#viewer` being derived, which puts `inherited` /
# `access` on `PDerivedTTU` with `parent_types` ('doc', 'folder'); `doc#viewer` stays plain
# `[user]`, because a star tupleset whose OWN type's target is derived is a scope refusal
# (`zanzibar_utils_v1.py::_reject_object_wildcard_scope`).
#
# SABOTAGE, 2026-09-26 (literal, `.scratch` probe; docs/tk106-boolean-tuplesets-2026-09-26.md
# § 6). (A) `_stored_tupleset_subjects` returning no star types, and (B)
# `_expand_tupleset_parents` ignoring `star_types`, each give::
#
#     RC2 star inherited             oracle=True graph=False sets=[True, True]
#     RC2 star access(neg)           oracle=False graph=True sets=[False, False]
#
# while the concrete-parent controls stay green -- RC2's original signature, both signs.
# The hypothesis campaign no longer reaches this path at all (every generated tupleset is
# untainted with an untainted target), so THESE are RC2's pins.

_RC2_HEAD = """model
  schema 1.1

type user

type folder
  relations
    define banned: [user]
    define viewer: [user] but not banned

type doc
  relations
    define parent: {parent}
    define viewer: [user]
    define inherited: viewer from parent
"""

_RC2_SCHEMA = _RC2_HEAD.format(parent='[folder, doc, doc:*]')
_RC2_SCHEMA_NEGATED_TTU = _RC2_SCHEMA + _RC1_ACCESS

# control: the star parent with an UNTAINTED target, i.e. the ordinary closure path
_RC2_CONTROL_SCHEMA = """model
  schema 1.1

type user

type doc
  relations
    define parent: [doc, doc:*]
    define viewer: [user]
    define inherited: viewer from parent
"""

_RC2_POOL = [
    ('...', 'doc', '*', 'parent', 'doc', 'd1'),
    ('...', 'user', 'alice', 'viewer', 'doc', 'd2'),
    ('...', 'doc', 'd2', 'parent', 'doc', 'd1'),
    ('...', 'user', 'alice', 'access', 'doc', 'd1'),
]

_RC2_STAR_PARENT = ('...', 'doc', '*', 'parent', 'doc', 'd1')
_RC2_CONCRETE_PARENT = ('...', 'doc', 'd2', 'parent', 'doc', 'd1')
_RC2_VIEWER_ON_PARENT = ('...', 'user', 'alice', 'viewer', 'doc', 'd2')
_RC2_ACCESS_GRANT = ('...', 'user', 'alice', 'access', 'doc', 'd1')

_RC2_INHERITED_Q = ('...', 'user', 'alice', 'inherited', 'doc', 'd1')
_RC2_ACCESS_Q = ('...', 'user', 'alice', 'access', 'doc', 'd1')


def test_rc2_positive_control_concrete_stored_parent_on_derived_ttu():
    """CONTROL: the same derived-target TTU with a CONCRETE stored parent ``doc:d2``.
    Isolates any failure of the pins below to the star arm. Measured 2026-09-26:
    oracle=True graph=True sets=[True, True], and green under both RC2 sabotages."""
    oracle, graph, sets = _answers(
        _RC2_SCHEMA, _RC2_POOL, [_RC2_CONCRETE_PARENT, _RC2_VIEWER_ON_PARENT],
        _RC2_INHERITED_Q)
    _assert_parity(oracle, graph, sets, True,
                   'RC2 control (concrete stored parent, derived target)')


def test_rc2_positive_control_star_parent_on_untainted_tupleset():
    """CONTROL: the same ``doc:*`` stored parent with an UNTAINTED target, so the ordinary
    closure path answers, not the delta processor. Controls the star-parent x TTU
    COMPOSITION; the derived-path control is the test above. Unchanged by TK106."""
    oracle, graph, sets = _answers(
        _RC2_CONTROL_SCHEMA, _RC2_POOL, [_RC2_STAR_PARENT, _RC2_VIEWER_ON_PARENT],
        _RC2_INHERITED_Q)
    _assert_parity(oracle, graph, sets, True,
                   'RC2 control (star parent on an untainted tupleset)')


def test_rc2_star_stored_parent_on_derived_ttu_is_a_ttu_parent():
    """★ RC2, fail-closed direction: a stored ``doc:*`` tupleset tuple is a TTU parent of a
    derived target, expanded over the instances of ``doc`` (so ``doc:d2``, where alice is
    a viewer). Measured 2026-09-26: oracle=True graph=True sets=[True, True]; RED
    (graph=False) under both sabotages in the section comment above.

    Do NOT weaken and do NOT xfail."""
    oracle, graph, sets = _answers(
        _RC2_SCHEMA, _RC2_POOL, [_RC2_STAR_PARENT, _RC2_VIEWER_ON_PARENT],
        _RC2_INHERITED_Q)
    _assert_parity(
        oracle, graph, sets, True,
        'RC2: the graph drops a stored `doc:*` TTU parent on the derived-ttu path '
        '(processor.py::_stored_tupleset_subjects / _expand_tupleset_parents)')


def test_rc2_positive_control_negated_ttu_concrete_parent():
    """CONTROL for the fail-open pin: the negated TTU with a CONCRETE stored parent cancels
    the grant. Measured 2026-09-26: oracle=False graph=False sets=[False, False]."""
    oracle, graph, sets = _answers(
        _RC2_SCHEMA_NEGATED_TTU, _RC2_POOL,
        [_RC2_CONCRETE_PARENT, _RC2_VIEWER_ON_PARENT, _RC2_ACCESS_GRANT], _RC2_ACCESS_Q)
    _assert_parity(oracle, graph, sets, False,
                   'RC2 control (negated TTU, concrete stored parent)')


def test_rc2_star_stored_parent_dropped_is_an_authorization_fail_open():
    """★★ RC2, FAIL-OPEN direction. Pin this one hardest: the same ``doc:*`` parent read
    through ``access: [user] but not viewer from parent``. A graph that drops the star
    parent sees an empty subtrahend and GRANTS what the oracle and both set engines deny.
    Measured 2026-09-26: oracle=False graph=False sets=[False, False]; graph=True (the
    fail-open) under both sabotages in the section comment above.

    Do NOT weaken and do NOT xfail."""
    oracle, graph, sets = _answers(
        _RC2_SCHEMA_NEGATED_TTU, _RC2_POOL,
        [_RC2_STAR_PARENT, _RC2_VIEWER_ON_PARENT, _RC2_ACCESS_GRANT], _RC2_ACCESS_Q)
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

    # Until TK106 (2026-09-26) this was RC1's own `parent: [folder] but not [doc]`, now a
    # parse refusal. The invariant only inspects `PDerivedTTU` / `PDerivedTuplesetTTU`
    # plan nodes, so the tupleset going direct is not enough on its own: the TARGET must be
    # derived, or no plan node exists and the sabotage below would pass silently.
    schema = _RC1_LIVE_SCHEMA

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
