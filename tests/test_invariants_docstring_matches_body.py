"""``check_invariants``'s docstring claimed a SMALLER invariant set than it runs.

The zero-trust review's last P5 bullet: "three documents give three different lists of
which invariants run per commit, and none matches ``index_v4/invariants.py``". Two
architecture docs were corrected and left the docstring flagged as still wrong -- it
said "Assert I1-I6 + I10", while the body also runs I7 (residue-version monotonicity)
and I13 (reference_count == direct-edge degree).

An understated docstring is not cosmetic here: it is the document an operator reads to
decide what paranoia mode is buying them, and I13 is the clause that makes the
refcount corruption which silently defeats bridge/derived-node GC visible at all.

This pin has two halves, and it needs both -- asserting on prose alone would let the
docstring drift the other way (into an OVERclaim) unnoticed:
  * the docstring no longer makes the understated claim and names I7 and I13;
  * ``check_invariants`` demonstrably ENFORCES I7 and I13, i.e. the corrected claim
    is true of the body.
"""

import json

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from index_v4 import ReachabilityIndex, Store
from index_v4.invariants import InvariantViolation, check_invariants
from index_v4.models import NodeV4, ResidueV1
from zanzibar_utils_v1 import parse_openfga_schema
from tests.wildcard_helpers import make_wildcard_index

_SCHEMA = '''
    type user
    type doc
      relations
        define editor: [user, user:*]
        define blocked: [user]
        define viewer: editor but not blocked
'''


def test_docstring_states_the_set_the_body_actually_runs():
    """The HEADLINE claim (everything before the first blank line) is what a reader
    takes away; that is where the understatement lived, so that is what is pinned.
    The body of the docstring is free to discuss I9/I11/I12 and say they run
    elsewhere -- which is why this looks at the headline and not the whole string."""
    doc = check_invariants.__doc__
    assert doc, 'check_invariants lost its docstring'
    headline = doc.split('\n\n', 1)[0]
    assert len(headline.strip()) > 20, 'headline is empty -- the checks below would be vacuous'

    # The exact understated claim that was live until this fix.
    assert 'I1-I6' not in headline
    # Everything the body enforces must be named or covered by a stated range.
    # (I14, crossing-middle completeness, joined 2026-08-09; its body-enforcement
    # proof lives in tests/test_i14_crossing_middles.py.)
    named = 0
    for clause in ('I1-I7', 'I10', 'I13', 'I14'):
        assert clause in headline, f'{clause} runs in the body but is unnamed'
        named += 1
    assert named == 4
    # ...and nothing that runs somewhere else may be claimed here.
    for absent in ('I9', 'I11', 'I12'):
        assert absent not in headline, f'{absent} does not run here but is claimed'


def test_body_enforces_i13_reference_count_degree():
    """I13 is one of the two clauses the old docstring omitted -- prove it runs."""
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Store(id='s'))
        session.commit()
        idx = ReachabilityIndex(session, store_id='s')
        idx.add_edge(..., 'user', 'alice', 'viewer', 'doc', 'd1')
        session.commit()
        check_invariants(session, 's')            # clean baseline, or the rest lies

        node = idx.node(..., 'user', 'alice', create_if_missing=False)
        assert node.reference_count == 1
        node.reference_count = 7                  # corrupt: degree is still 1
        session.add(node)
        session.flush()
        with pytest.raises(InvariantViolation) as exc:
            check_invariants(session, 's')
        assert 'I13' in str(exc.value)
        session.rollback()


def test_body_enforces_i7_residue_version_monotonicity():
    """I7 is the other omitted clause. It only runs when the caller passes the
    ``residue_versions`` ledger -- which the paranoia guard does on every commit."""
    rs = parse_openfga_schema(_SCHEMA, enable_boolean=True)
    session, widx = make_wildcard_index(rs.schema_info)
    from index_v4.processor import DeltaProcessor
    from index_v4.outbox import outbox_watermark
    from zanzibar_utils_v1 import Entity, RelationalTriple

    proc = DeltaProcessor(widx, rs.compiled)

    def write(raw):
        wm = outbox_watermark(session, 'test')
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]),
                                  Ellipsis if raw[0] == '...' else raw[0])
        for d in rs.apply(triple):
            widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                           d.subject.type, d.subject.name, d.relation,
                           d.object.type, d.object.name)
        proc.run_cascade(wm)
        session.commit()

    write(('...', 'user', '*', 'editor', 'doc', 'd1'))    # star-covered positive arm
    write(('...', 'user', 'bob', 'blocked', 'doc', 'd1'))  # -> a neg entry

    rows = session.exec(select(ResidueV1)).all()
    assert len(rows) == 1, f'fixture produced {len(rows)} residue rows, need exactly 1'
    row = rows[0]
    assert json.loads(row.stars), 'residue has no stars -- fixture did not bite'

    # A ledger claiming a HIGHER last-seen version than the row carries is exactly
    # the "version regressed" corruption I7 exists to catch.
    ledger = {(row.id, row.object_node_id): row.version + 5}
    with pytest.raises(InvariantViolation) as exc:
        check_invariants(session, 'test', rs.schema_info, residue_versions=ledger)
    assert 'I7' in str(exc.value)

    # ...and the honest ledger passes, so the clause is discriminating, not a
    # blanket raise.
    check_invariants(session, 'test', rs.schema_info,
                     residue_versions={(row.id, row.object_node_id): row.version})
    session.close()


# ===========================================================================
# The OPTIONAL argument that is not optional in practice (TK72, 2026-09-19f)
# ===========================================================================

# Every (repo-relative path, enclosing function) whose `check_invariants` call
# deliberately passes NO `schema_info`, with the reason. Each was READ first-hand on
# 2026-09-19f: all six build a raw `index_v4.ReachabilityIndex`, which has no
# `schema_info` attribute at all (`grep schema_info index_v4/core.py` -> nothing), so
# there is no handle in scope to pass and the reduced checker is the only one available.
_SCHEMALESS_SITES = {
    ('tests/test_blind_audit_regressions.py',
     'test_remove_node_decrements_neighbour_refcounts'):
        'raw ReachabilityIndex; the store is asserted EMPTY on the line above',
    ('tests/test_invariants_docstring_matches_body.py',
     'test_body_enforces_i13_reference_count_degree'):
        'raw ReachabilityIndex built inline to corrupt a refcount (2 call sites)',
    ('tests/test_reg17_closure_fanout_cap.py',
     'test_rejection_leaves_no_partial_state'):
        'raw ReachabilityIndex with a synthetic p/t shape and no compiled schema',
    ('tests/test_reg17_closure_fanout_cap.py',
     'test_removals_are_never_capped'):
        'raw ReachabilityIndex with a synthetic p/t shape and no compiled schema',
    ('tests/test_reg17_closure_fanout_cap.py',
     'test_node_removal_is_never_capped'):
        'raw ReachabilityIndex with a synthetic p/t shape and no compiled schema',
}

_MIN_CALL_SITES = 40        # measured 2026-09-19f: 42 sites across 184 parsed files


def test_every_schema_backed_check_invariants_call_passes_schema_info():
    """TK72 (2026-09-19f). Property guarded: a caller that HAS a `SchemaInfo` passes
    it, so the schema-gated half of the checker actually runs.

    WHY A CENSUS AND NOT A CODE COMMENT. `schema_info` defaults to `None`, and without
    it `check_invariants` silently skips the rest of I3 (bridge
    completeness/exclusivity), I14, I4 namespace classification and every derived
    invariant -- roughly half the body -- while still returning cleanly. Dropping the
    argument is therefore INVISIBLE: the call keeps passing, the test keeps passing,
    and the coverage is gone. `tests/test_zt_p5_readjudication.py` lived that way for
    weeks with a docstring claiming "I1-I13 are green on all three"; nothing went red
    when it was fixed, and nothing would go red if it were un-fixed. This test is that
    missing red.

    MEASURED 2026-09-19f, `formal/probes/tk72_schema_info_gate_2026-09-19.py`: on the
    ZT-P5 corpus, deleting one `w_all -> concrete` bridge (and decrementing the two
    endpoint refcounts, so every schema-independent clause stays satisfied) is GREEN
    without the handle and RED with it -- `I3: concrete ... of bridged-out shape
    missing its w_all->concrete bridge`. That is the coverage the argument buys.

    The allowlist is asserted EXACT in both directions. A new schema-less site must be
    justified here; a listed site that gains a handle must be removed from the list, or
    the list rots into a permanent exemption.

    SWEPT by `formal/probes/tk72_callsite_sweep_2026-09-19.py` (2026-09-19f): 6
    mutations, 4 CAUGHT — `S0` the harness control, `S1` below, `S2` (drop an allowlist
    entry -> reported MISSING), `S4` (blind the AST walk -> the ceiling control fires,
    `only 0 check_invariants call site(s) found, floor 40`). Two INERT and both
    predicted: `S3` a no-op edit beside the floor, and `S5` weakening the ZT-P5
    instrument control to `or True`, which claims nothing while that corpus IS
    bridged-out — a control only fires when its subject changes.

    SABOTAGE (literal output, 2026-09-19f). Narrowest plausible weakening: revert ONE
    of the three `tests/test_zt_p5_readjudication.py` calls to the pre-TK72 form::

        FAILED tests/test_invariants_docstring_matches_body.py::test_every_schema_backed_check_invariants_call_passes_schema_info
        AssertionError: check_invariants called WITHOUT schema_info at a schema-backed
        site: [('tests/test_zt_p5_readjudication.py',
        'test_zt_p5_object_wildcard_state_level_live_equals_rebuild')]
    """
    import ast
    import pathlib

    skip = {'.scratch', '.gate-runs', '.git', '.lake', 'build', '.venv', '__pycache__'}
    root = pathlib.Path(__file__).resolve().parents[1]
    total = 0
    bare: dict = {}
    for path in root.rglob('*.py'):
        rel = path.relative_to(root).as_posix()
        if any(part in skip for part in path.relative_to(root).parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except SyntaxError:                     # not this test's business
            continue
        stack: list = []

        def walk(node):
            nonlocal total
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                stack.append(node.name)
                for child in ast.iter_child_nodes(node):
                    walk(child)
                stack.pop()
                return
            if isinstance(node, ast.Call):
                name = getattr(node.func, 'id', None) or getattr(node.func, 'attr', None)
                if name == 'check_invariants':
                    total += 1
                    has = (len(node.args) >= 3
                           or any(k.arg == 'schema_info' for k in node.keywords))
                    if not has:
                        bare.setdefault((rel, stack[-1] if stack else '<module>'), []) \
                            .append(node.lineno)
            for child in ast.iter_child_nodes(node):
                walk(child)

        walk(tree)

    # CEILING CONTROL: a walker that found nothing would pass this test silently.
    assert total >= _MIN_CALL_SITES, (
        f'only {total} check_invariants call site(s) found, floor {_MIN_CALL_SITES} -- '
        f'the AST walk is broken, so the census below means nothing')

    missing = sorted(set(bare) - set(_SCHEMALESS_SITES))
    assert not missing, (
        f'check_invariants called WITHOUT schema_info at a schema-backed site: '
        f'{missing}')
    stale = sorted(set(_SCHEMALESS_SITES) - set(bare))
    assert not stale, (
        f'allowlisted site(s) no longer call check_invariants without schema_info, so '
        f'the exemption is rot: {stale}')
