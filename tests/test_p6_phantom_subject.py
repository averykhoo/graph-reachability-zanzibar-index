"""PHANTOM USERSET SUBJECT over a star-tupleset TTU through-shape: every backend agrees.

**Why this file exists.** The `P6` step-1 probe
(``formal/probes/p6_step1_logged_bridge_2026-09-13.lean``) found that after composing the
in-bridge into the whole write leg, exactly **2** grid mismatches of 546 survived against
the Lean model's `sem`, and both were the same shape: a userset subject ``folder:f9#viewer``
whose object ``folder:f9`` is mentioned by NO stored tuple -- a *phantom* -- queried at the
DERIVED relations ``admin``/``gate``. At that same subject the PLAIN relation ``access``
answered correctly. The Lean graph model's derived read path is EDGES ALONE, so it needs a
materialised concrete node where its plain path answers symbolically; the shipped Python's
derived read path is edge probe **plus residue**, so it does not. Measuring the shipped
backends the same hour is what turned that residual from a candidate bug into a
``formal/CORRESPONDENCE.md`` sec 7 model boundary, and this module is that measurement,
promoted from a probe to a pin.

**What it pins, and why a probe was not enough.** The probe
``formal/probes/p6_phantom_subject_2026-09-13.py`` is tracked and re-runnable, but nothing
in the ten-phase gate reddens if the property regresses -- ``docs/sabotage-procedure.md``'s
durability ranking puts a tracked probe two rungs below a permanent test, and the `P6` row
carried the gap as an explicit "still owed" from 2026-09-13b. So: same schema, same store,
same queries, run through ``tests/parity.py::ParityEngine``, whose ``check`` asserts
unanimity across the graph index, BOTH ``SetOps`` and the independent oracle.

**Non-vacuity is asserted, not assumed** (the house failure mode -- a matrix that silently
halves is how ``pyroaring``'s absence used to pass as green). ``test_graph_backend_joined``
refuses the 3-way degrade: if the graph index ever stops compiling this schema, the
graph-vs-set question this module exists to ask would go unmeasured while every other test
here still passed. ``test_phantom_object_has_no_graph_node`` asserts the phantom really is
phantom, and the ``f1`` arm is the written-subject control.

**SABOTAGE-VERIFIED 2026-09-13b** (``docs/sabotage-procedure.md``; script was throwaway,
``.scratch/p6_phantom_test_sabotage.py``). Literal observed verdicts::

    S0  INSTRUMENT CONTROL: flip one expected value (phantom f9 derived -> False)
          RED: test_phantom_subject_unanimous[phantom f9 derived]   [1 failed, 8 passed]
    S1  wildcard.py:780 userset arm -> `subj is not None and ...`, i.e. require a
        MATERIALISED node (the Lean model's edges-alone reading, which is the exact
        regression this module exists to catch)
          RED: all 9, at fixture setup                              [9 errors]
    S2  wildcard.py:776 drop the `upos` fast path                   GREEN -- INERT
    S3  wildcard.py:793 bare-subject arm -> require a materialised node
                                                                    GREEN -- INERT

**S1 reds at SETUP, and the reason is worth knowing**: ``ParityEngine._apply`` runs a
full-grid parity assertion after every write, and its grid already contains ghost subjects,
so the sabotage is caught on the FIRST store write with
``q=('viewer','folder','zz-ghost','admin','doc','d1') graph=False oracle=True`` -- the
phantom shape, found by the engine rather than by a query below. That is a stronger red
than a parametrized failure, and it is a real red: the mutation dies of the property, not of
a ``TypeError`` (the `GL-1` instrument trap, 2026-09-08).

**S2 and S3 are INERT and that is stated rather than hidden.** Every query here uses a
USERSET subject, so the bare-subject arm (S3) is never reached; and this store produces no
edge-free ``upos`` membership, so the S2 fast path never fires. Neither is evidence that
those lines are dead -- only that THIS module does not exercise them. Do not cite this table
as coverage for them, and do not widen the schema to chase them: the scenario is pinned
here because it is the one the `P6` step-1 probe measured, and changing it would decouple
the pin from its evidence.
"""
import pytest

from index_v4.core import ReachabilityIndex  # noqa: F401  (documents the node API used below)
from tests.parity import ParityEngine

# `doc#parent: [folder:*]` used as a TTU tupleset is exactly the star-tupleset
# through-shape of `zanzibar_utils_v1.py::derive_schema_info`'s SECOND loop, i.e. the
# shape `W4Fragment.ttuStarFree` is about. `admin`/`gate` put it behind a `but not` and
# an `and`, so the derived (residue-backed) read path is the one under test.
SCHEMA = (
    'type user\n'
    'type folder\n'
    '  relations\n'
    '    define viewer: [user]\n'
    'type doc\n'
    '  relations\n'
    '    define parent: [folder:*]\n'
    '    define access: viewer from parent\n'
    '    define banned: [user, folder#viewer]\n'
    '    define admin: access but not banned\n'
    '    define gate: admin and access\n'
)

STORE = [
    ('...', 'folder', '*', 'parent', 'doc', 'd1'),
    ('...', 'user', 'alice', 'viewer', 'folder', 'f1'),
    ('...', 'user', 'bob', 'viewer', 'folder', 'f2'),
    ('viewer', 'folder', 'f1', 'banned', 'doc', 'd2'),
]

# (label, query, expected). `f9` is named by no tuple above -- the phantom. `f1`/`f2` are
# the written controls. Expectations are the oracle's, transcribed from the 2026-09-13 run
# recorded in the probe's docstring; they are asserted so that a change making every
# backend UNANIMOUSLY WRONG cannot pass as parity.
QUERIES = [
    ('phantom f9 plain  ', ('viewer', 'folder', 'f9', 'access', 'doc', 'd1'), True),
    ('phantom f9 derived', ('viewer', 'folder', 'f9', 'admin', 'doc', 'd1'), True),
    ('phantom f9 strat2 ', ('viewer', 'folder', 'f9', 'gate', 'doc', 'd1'), True),
    ('control f1 plain  ', ('viewer', 'folder', 'f1', 'access', 'doc', 'd1'), True),
    ('control f1 derived', ('viewer', 'folder', 'f1', 'admin', 'doc', 'd1'), True),
    ('control f1 strat2 ', ('viewer', 'folder', 'f1', 'gate', 'doc', 'd1'), True),
    ('control f2 strat2 ', ('viewer', 'folder', 'f2', 'gate', 'doc', 'd1'), True),
]


@pytest.fixture()
def engine():
    pe = ParityEngine(SCHEMA)
    for raw in STORE:
        assert pe.add_tuple(*raw) is True, f'setup write refused: {raw}'
    yield pe
    pe.close()


def test_graph_backend_joined(engine):
    """NON-VACUITY: the graph index is in the matrix.

    Without this the module degrades to oracle + two set engines and still passes, which
    would leave the graph-vs-set question -- the only question it exists to ask --
    unmeasured. `graph_drop_reason` is reported so a future failure names its own cause.
    """
    assert engine.graph is not None, f'graph side dropped: {engine.graph_drop_reason}'
    assert engine.graph_drop_reason is None


def test_phantom_object_has_no_graph_node(engine):
    """NON-VACUITY: `folder:f9` really is a phantom.

    If some later change starts materialising a node for every schema-declared shape, the
    parity assertions below would still pass but would no longer be about a phantom. The
    written control `folder:f1` must resolve, so this is not merely "node lookup raises".
    """
    idx = engine.graph.widx.idx
    idx.node('viewer', 'folder', 'f1', create_if_missing=False)      # control: present
    with pytest.raises(KeyError):
        idx.node('viewer', 'folder', 'f9', create_if_missing=False)


@pytest.mark.parametrize('label,query,expected', QUERIES, ids=[q[0].strip() for q in QUERIES])
def test_phantom_subject_unanimous(engine, label, query, expected):
    """Graph index, both `SetOps` and the oracle agree -- and agree on the right answer.

    `ParityEngine.check` raises `AssertionError` naming the disagreeing backends, so a
    regression on either side of the equivalence surfaces here rather than as a silent
    difference. The three `f9` rows are the Lean residual; they are the reason this is a
    `CORRESPONDENCE.md` sec 7 boundary and not a Python bug (`P6` log 2026-09-13b).
    """
    assert engine.check(*query) is expected, label
