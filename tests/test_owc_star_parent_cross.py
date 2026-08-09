"""
The OWC x star-parent x TTU cross, at ANSWER level, on the GRAPH index.

**This module is currently RED, deliberately, and it pins a live divergence.** It was
found on 2026-08-09 by ``tests/test_lookup_hypothesis.py::TestLookupSurfaceMachine``, whose
own docstring says: *"If a generated walk ever trips a checker, that is a genuine
lookup/expand divergence the properties (the spec) forbid -- capture the minimal example
and REPORT it; do NOT relax the assertions."* This file is that capture.

## The divergence

Schema ``tests/fga_schemas/owc_star_ttu.fga`` with
``object_wildcard_shapes = {('folder','viewer'), ('doc','viewer')}``::

    folder#parent: [folder, folder:*]
    doc#parent:    [folder, folder:*]
    doc#viewer:    [user, user:*, group#member] or viewer from parent

Three tuples::

    (user:u1, editor, folder:f1)    # any tuple that makes folder:f1 exist
    (user:u1, viewer, folder:*)     # OBJECT-wildcard grant  -> w_all(folder, viewer)
    (folder:*, parent, doc:d1)      # SUBJECT-wildcard tupleset -> w_any(folder, '...')

``check(user:u1, viewer, doc:d1)``::

    oracle            = True
    set engine (py)   = True
    set engine (roar) = True
    graph index       = False     <== the graph is the odd one out

It is a **false negative** -- the graph under-grants, so it fails closed and is not a
security fail-open. It is still a semantics divergence between two backends whose whole
contract is "identical semantics, opposite cost models".

## Root cause (measured, not inferred)

``index_v4/wildcard.py::_ensure_bridges`` only ever links
``w_all(T,p) -> concrete -> w_any(T,p)`` through an **interned node of shape (T,p)**, and
``backfill``'s docstring says so in as many words ("Does not create a w node for a shape
that has no concrete instances"). ``tests/oracle.py::instances`` witnesses the existential
with any **tuple-mentioned entity of type T**, whatever relation mentioned it. So the two
sides disagree about what counts as a witness for ``wildcard-materialization-spec.md``
§3.4's pinned rule -- *"'granted on all S' implies 'reaches some S' only if at least one
concrete instance of S exists ... which requires a real concrete in the middle"*. The spec
says "instance of S"; the graph reads that as "node of shape (T,p)", the oracle and the
set engine read it as "entity of type T". That asymmetry is nowhere written down.

Measured, holding everything else fixed and varying only which relation mentions
``folder:f1``::

    witness interns folder:f1#editor    oracle=True  graph=False   <== DIVERGES
    witness interns folder:f1#blocked   oracle=True  graph=False   <== DIVERGES
    witness interns folder:f1#viewer    oracle=True  graph=True

The set engine has an explicit, named mechanism for exactly this case and the graph has no
analogue -- ``setengine/engine.py:1476-1480``, *"the star-parent cross for the triple combo
owc x star-parent x TTU where NO concrete (T, X, r') is interned"*. That is the pointer for
whoever fixes this.

## Why this file exists rather than an xfail

The shape was reachable by the hypothesis campaign all along; it had simply never been
drawn (``max_examples=12``, ``stateful_step_count=8``, over a ~50-tuple pool). So the gate
was green **by seed luck** -- the house failure mode this repo names explicitly: *an
assurance step that fails by PASSING*. Pinning the minimal example makes the red
deterministic and reproducible in 0.1s instead of dependent on a draw.

Per ``CLAUDE.md``: never relax the properties, and prefer converting an xfail into a
positive pin. So ``test_owc_star_parent_cross_graph_matches_oracle`` asserts the CORRECT
behaviour and fails until the graph is fixed. ``test_..._positive_control`` is its control:
the same composition with a concrete-shape witness, which passes today and must keep
passing through any fix.

Nearest prior art, and why neither covers this (checked 2026-08-09):
``docs/spec-deviations.md`` F1 (``:1320``, CLOSED ``:1336``) is a doubly-bridged topology
rejected at compile time -- this schema compiles fine. The "all -> any is NOT read
semantics" adjudication (``:1360-1367``) was decided on an **oracle-False** probe (no
concrete in the universe), so it does not adjudicate an oracle-True case. ``ZT-P5``
bullet 2 / "Target 3" probed this exact fixture but only at STATE level, never against
oracle answers.
"""

from pathlib import Path

import pytest

from tests.oracle import Oracle, OracleTuple
from tests.test_lookup_oracle import _Gate, OWC_STAR_TTU_SHAPES, _owc_star_ttu_pool

_QUERY = ('...', 'user', 'u1', 'viewer', 'doc', 'd1')

_OBJECT_WILDCARD_GRANT = ('...', 'user', 'u1', 'viewer', 'folder', '*')
_STAR_PARENT_TUPLESET = ('...', 'folder', '*', 'parent', 'doc', 'd1')


def _schema() -> str:
    return (Path(__file__).parent / 'fga_schemas' / 'owc_star_ttu.fga').read_text()


def _answers(tuples):
    """(oracle, graph, [set engines]) for the fixed query after adding `tuples`."""
    gate = _Gate(_schema(), OWC_STAR_TTU_SHAPES, _owc_star_ttu_pool())
    for raw in tuples:
        assert gate.apply('add', raw), f'admission rejected {raw}'
    oracle = Oracle(_schema(), [OracleTuple(*r) for r in gate.present])
    return (oracle.check(*_QUERY),
            gate.graph.widx.check(*_QUERY),
            [side.se.check(*_QUERY) for side in gate.sets])


def test_owc_star_parent_cross_positive_control():
    """The SAME composition, with a witness that interns a node of shape (folder, viewer).

    This is the control: it proves the harness, the schema, the admission path and the
    query are all sound, so a failure of the pin below is about the missing bridge and
    nothing else. It passes today and must keep passing through any fix.
    """
    concrete_shape_witness = ('...', 'user', 'u9', 'viewer', 'folder', 'f1')
    oracle, graph, sets = _answers(
        [concrete_shape_witness, _OBJECT_WILDCARD_GRANT, _STAR_PARENT_TUPLESET])
    assert oracle is True
    assert graph == oracle
    assert all(s == oracle for s in sets)


@pytest.mark.parametrize('witness_relation', ['editor', 'blocked'])
def test_owc_star_parent_cross_graph_matches_oracle(witness_relation):
    """★ CURRENTLY RED — the live divergence, minimised to three tuples.

    ``folder:f1`` exists (some tuple mentions it) but no node of shape
    ``(folder, viewer)`` is interned, so ``_ensure_bridges`` never builds the
    ``w_all(folder,viewer) -> folder:f1#viewer -> ...`` middle and the graph cannot see
    that the object-wildcard grant reaches a concrete folder which the star-parent
    tupleset makes a parent of ``doc:d1``.

    Parameterised over two different witness relations to show the defect is about the
    SHAPE not being interned, not about anything specific to ``editor``.

    Do NOT xfail this. Do NOT weaken it to `graph is False`. Fix the bridge — the set
    engine's ``star-parent cross`` (``setengine/engine.py:1476-1480``) is the analogue to
    port, and ``docs/spec-deviations.md`` 2026-08-09 carries the full filing.
    """
    witness = ('...', 'user', 'u9', witness_relation, 'folder', 'f1')
    oracle, graph, sets = _answers(
        [witness, _OBJECT_WILDCARD_GRANT, _STAR_PARENT_TUPLESET])
    assert oracle is True, 'the oracle is the spec; if this flipped, re-adjudicate first'
    assert all(s == oracle for s in sets), 'both set engines agree with the oracle'
    assert graph == oracle, (
        f'graph index under-reports the OWC x star-parent x TTU cross: '
        f'graph={graph} oracle={oracle} sets={sets} '
        f'(witness relation {witness_relation!r} interns folder:f1#{witness_relation}, '
        f'never folder:f1#viewer)')
