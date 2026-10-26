"""TK161: the residue userset arm's PHANTOM branch, pinned on a seedless facade.

**Why this file exists.** ``src/zanzibar/graphindex/wildcard.py::WildcardIndex._check_derived``
answers a concrete USERSET subject at a derived relation from the residue (``stars`` minus
``neg``, plus ``upos``) whenever it does not take the TK144 read-time branch. Its last line
for that arm is ``return subj is None or subj.id not in neg``: a *phantom* subject (no graph
node) cannot be in ``neg``, so star coverage alone answers. Since TK144 the public read of a
facade built by ``compile_ruleset`` never gets there for a userset subject (the read-time
branch answers first), so the P6 module's sabotage S1 went INERT at that site (S13,
``tests/test_p6_phantom_subject.py`` docstring). The arm is still reached in two ways:

* every ``reflexive=False`` read (the reconcile, the invariants, I9), which this module does
  not target, and
* the PUBLIC read of a facade whose ``SchemaInfo`` carries no seed table
  (``SchemaInfo.self_seeds`` empty, so ``WildcardIndex._reflexive_reads`` is False). No
  public construction path builds one with derived families (``compile_ruleset`` always
  seeds every declared relation with itself; ``derive_schema_info`` carries no derived
  families), but ``WildcardIndex(idx, schema_info)`` accepts a hand-built ``SchemaInfo``,
  and the class comment in ``WildcardIndex.__init__`` documents that such a facade "reads
  non-reflexively throughout".

**Decision (TK161, 2026-10-26): PIN, do not delete.** Deleting the ``subj is None``
disjunct would turn a seedless facade's phantom read into ``AttributeError`` on
``None.id`` instead of an answer, and the bare-subject arm below it keeps the identical
idiom for ghosts on the public read. The pin is the P6 scenario, re-read through a seedless
facade over the SAME store. For this schema the self-relation adds nothing (``banned`` on
``doc:d1`` is empty), so the reflexive and non-reflexive answers coincide and the expected
values are the P6 module's oracle values. Nothing here is a golden: ``engine.check`` is
re-asserted for every query so the expectation is the live oracle's, not a transcription.

**Non-vacuity is asserted:** the seedless facade really reads non-reflexively
(``_reflexive_reads`` False), the subject really is phantom (no node), and the facade
really routes the relation to ``_check_derived`` (it is in ``derived_families``).

**SABOTAGE-VERIFIED 2026-10-26** (``formal/probes/tk161_sabotage_2026_10_26.py``, a
pytest plugin that patches ``WildcardIndex._check_derived`` in memory; the source file is
never edited). Literal observed verdicts::

    (no mode)  4 passed
    S1  userset arm's last line -> `subj is not None and subj.id not in neg`
        (require a MATERIALISED node: the Lean edges-alone reading)
          RED: 2 failed, 2 passed
          FAILED test_seedless_phantom_reads_like_oracle[phantom f9 derived]
          FAILED test_seedless_phantom_reads_like_oracle[phantom f9 strat2]
          E   AssertionError: phantom f9 derived / assert False is True
          (a real red: the property, not a TypeError; the f1 control stays green)
    S2  same edit on the bare-subject arm only (control: wrong arm)
          GREEN -- INERT (4 passed): this module asks userset subjects only

**Repair round 1 (2026-10-26): the BARE-subject arm's ghost branch is pinned too.** The
first verdict above left S2 inert, and the P6 module and ``tests/test_lookup_oracle.py``
were green under S2 as well (59 passed, reviewer's run), so the bare arm's ``subj is None``
disjunct had no recorded pin. ``BARE_SCHEMA`` / ``test_bare_ghost_*`` below add one: a ghost
``user:zed`` covered by ``user:*`` on a ``but not`` relation, read through the compiled
facade's PUBLIC read (bare subjects are not intercepted by the TK144 read-time branch) and
through the seedless facade. Literal observed verdicts, same plugin, 8 tests::

    (no mode)  8 passed
    S1  RED: 2 failed, 6 passed (the same two userset-arm phantoms as above;
          the bare-ghost tests stay green -- S1 is the wrong arm for them)
    S2  RED: 4 passed, 4 errors
          E   AssertionError: check parity broken after add
              ('...', 'user', '*', 'viewer', 'doc', 'd1'):
              q=('...', 'user', 'zz-ghost', 'can', 'doc', 'd1') graph=False oracle=True
          (the red fires in the ``bare_pair`` fixture: ``ParityEngine``'s own per-op grid,
          which includes a ghost name per type, catches the bare arm on the setup write,
          before the test body runs; the 4 passed are the userset-arm tests)

So S2 is red in THIS module, and through ``ParityEngine``'s ghost grid it is red for any
ParityEngine test whose boolean schema puts a bare-subject star under a derived relation.
"""
from dataclasses import replace

import pytest

from zanzibar.graphindex.wildcard import WildcardIndex
from tests.parity import ParityEngine
from tests.test_p6_phantom_subject import SCHEMA, STORE

# (label, query). Derived relations only: the plain `access` relation never reaches
# `_check_derived`. f9 is the phantom; f1 is the written control.
QUERIES = [
    ('phantom f9 derived', ('viewer', 'folder', 'f9', 'admin', 'doc', 'd1')),
    ('phantom f9 strat2', ('viewer', 'folder', 'f9', 'gate', 'doc', 'd1')),
    ('control f1 derived', ('viewer', 'folder', 'f1', 'admin', 'doc', 'd1')),
]


@pytest.fixture()
def pair():
    pe = ParityEngine(SCHEMA)
    for raw in STORE:
        assert pe.add_tuple(*raw) is True, f'setup write refused: {raw}'
    assert pe.graph is not None, f'graph side dropped: {pe.graph_drop_reason}'
    widx = pe.graph.widx
    seedless = WildcardIndex(widx.idx, replace(widx.schema_info, self_seeds=frozenset()))
    yield pe, seedless
    pe.close()


def test_seedless_facade_is_what_it_claims(pair):
    """NON-VACUITY: the facade reads non-reflexively, f9 is phantom, `admin`/`gate` are
    derived (so the read is `_check_derived`'s residue arm), and the compiled facade it was
    cloned from DOES read reflexively (so the clone is the only thing that changed)."""
    pe, seedless = pair
    assert pe.graph.widx._reflexive_reads is True
    assert seedless._reflexive_reads is False
    assert {('doc', 'admin'), ('doc', 'gate')} <= seedless.schema_info.derived_families
    with pytest.raises(KeyError):
        seedless.idx.node('viewer', 'folder', 'f9', create_if_missing=False)
    seedless.idx.node('viewer', 'folder', 'f1', create_if_missing=False)   # control


@pytest.mark.parametrize('label,query', QUERIES, ids=[q[0] for q in QUERIES])
def test_seedless_phantom_reads_like_oracle(pair, label, query):
    """The seedless facade's residue answer equals the unanimous answer of the graph
    index (compiled facade), both `SetOps` and the oracle (`ParityEngine.check`)."""
    pe, seedless = pair
    expected = pe.check(*query)
    assert expected is True, f'{label}: the P6 oracle value moved; re-read the P6 module'
    assert seedless.check(*query) is expected, label


# ---- the BARE-subject arm's ghost branch (TK161 repair round 1, 2026-10-26) ----------
# The same `subj is None` idiom closes the bare-subject arm of `_check_derived`. Unlike the
# userset arm, a bare subject is NOT intercepted by the TK144 read-time branch, so the
# compiled facade's PUBLIC read reaches it. A ghost (`user:zed`, named by no tuple, so no
# node) is covered by the `user:*` star and cannot be in `neg`: the star alone answers.
# `bob` is the written, banned control (in `neg`), `amy` the written, unbanned control.
BARE_SCHEMA = (
    'type user\n'
    'type doc\n'
    '  relations\n'
    '    define viewer: [user, user:*]\n'
    '    define banned: [user]\n'
    '    define can: viewer but not banned\n'
)
BARE_STORE = [
    ('...', 'user', '*', 'viewer', 'doc', 'd1'),
    ('...', 'user', 'bob', 'banned', 'doc', 'd1'),
    ('...', 'user', 'amy', 'viewer', 'doc', 'd2'),
]
BARE_QUERIES = [
    ('ghost zed', ('...', 'user', 'zed', 'can', 'doc', 'd1'), True),
    ('control bob banned', ('...', 'user', 'bob', 'can', 'doc', 'd1'), False),
    ('control amy d2', ('...', 'user', 'amy', 'can', 'doc', 'd2'), True),
]


@pytest.fixture()
def bare_pair():
    pe = ParityEngine(BARE_SCHEMA)
    for raw in BARE_STORE:
        assert pe.add_tuple(*raw) is True, f'setup write refused: {raw}'
    assert pe.graph is not None, f'graph side dropped: {pe.graph_drop_reason}'
    widx = pe.graph.widx
    seedless = WildcardIndex(widx.idx, replace(widx.schema_info, self_seeds=frozenset()))
    yield pe, widx, seedless
    pe.close()


def test_bare_ghost_is_what_it_claims(bare_pair):
    """NON-VACUITY: `zed` has no node, `can` is derived (so `_check_derived` answers),
    and `bob` really has one (the control is written)."""
    pe, widx, seedless = bare_pair
    assert ('doc', 'can') in widx.schema_info.derived_families
    with pytest.raises(KeyError):
        widx.idx.node('...', 'user', 'zed', create_if_missing=False)
    widx.idx.node('...', 'user', 'bob', create_if_missing=False)   # control


@pytest.mark.parametrize('label,query,expected', BARE_QUERIES,
                         ids=[q[0] for q in BARE_QUERIES])
def test_bare_ghost_reads_like_oracle(bare_pair, label, query, expected):
    """The compiled facade's PUBLIC read and the seedless facade's read both equal the
    oracle for a ghost bare subject. The transcribed expectation is re-asserted against the
    live oracle (`ParityEngine._oracle`), so a unanimously wrong change cannot pass."""
    pe, widx, seedless = bare_pair
    assert pe._oracle().check(*query) is expected, f'{label}: the oracle value moved'
    assert widx.check(*query) is expected, f'{label} (compiled facade)'
    assert seedless.check(*query) is expected, f'{label} (seedless facade)'
