"""P6 step 1 side-question: does the Lean probe's PHANTOM-SUBJECT residual reproduce
in the shipped Python, as a graph-vs-set-engine divergence?

The Lean step-1 probe (formal/probes/p6_step1_logged_bridge_2026-09-13.lean) found its
only residual grid mismatches at a userset subject `folder:f9#viewer` whose object
`folder:f9` appears in NO stored tuple: `sem` says true for the DERIVED relations
admin/gate, the graph model says false, while the PLAIN relation `access` agrees.

This asks the same question of the shipped backends. ParityEngine.check asserts unanimity
across graph index + both SetOps + oracle, so a divergence surfaces as an AssertionError.

Kept OUTSIDE the gated suite for the same reason the Lean probes are kept outside the lake
package: it is evidence that can be re-run, not a pin. Run it with the repo's env:

    C:/Users/user/anaconda3/envs/graph-reachability-zanzibar-index/python.exe \
        formal/probes/p6_phantom_subject_2026-09-13.py

RAN 2026-09-13, VERBATIM stdout -- the answer is NO DIVERGENCE, so the Lean residual is a
model gap and not a shipped bug:

    graph side present: True | drop reason: None
    add ('...', 'folder', '*', 'parent', 'doc', 'd1') -> True
    add ('...', 'user', 'alice', 'viewer', 'folder', 'f1') -> True
    add ('...', 'user', 'bob', 'viewer', 'folder', 'f2') -> True
    add ('viewer', 'folder', 'f1', 'banned', 'doc', 'd2') -> True
    phantom f9   ('viewer', 'folder', 'f9', 'access', 'doc', 'd1') -> UNANIMOUS True
    phantom f9   ('viewer', 'folder', 'f9', 'admin', 'doc', 'd1') -> UNANIMOUS True
    phantom f9   ('viewer', 'folder', 'f9', 'gate', 'doc', 'd1') -> UNANIMOUS True
    control f1   ('viewer', 'folder', 'f1', 'access', 'doc', 'd1') -> UNANIMOUS True
    control f1   ('viewer', 'folder', 'f1', 'admin', 'doc', 'd1') -> UNANIMOUS True
    control f1   ('viewer', 'folder', 'f1', 'gate', 'doc', 'd1') -> UNANIMOUS True
    control f2   ('viewer', 'folder', 'f2', 'gate', 'doc', 'd1') -> UNANIMOUS True

(!) STILL OWED, and named on task row P6 rather than left implicit: this is a re-runnable
probe, NOT a pin. Nothing in the ten-phase gate reddens if the phantom-subject property
regresses. Promoting it to a permanent parity test is a step-2 item; the durability
ranking in `docs/sabotage-procedure.md` puts a tracked probe two rungs below a test.
"""
import sys
import traceback

sys.path.insert(0, r'C:/Users/user/PycharmProjects/graph-reachability-zanzibar-index')

from tests.parity import ParityEngine  # noqa: E402

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

pe = ParityEngine(SCHEMA)
print('graph side present:', pe.graph is not None, '| drop reason:', pe.graph_drop_reason)

for raw in [('...', 'folder', '*', 'parent', 'doc', 'd1'),
            ('...', 'user', 'alice', 'viewer', 'folder', 'f1'),
            ('...', 'user', 'bob', 'viewer', 'folder', 'f2'),
            ('viewer', 'folder', 'f1', 'banned', 'doc', 'd2')]:
    print('add', raw, '->', pe.add_tuple(*raw))

# f9 is mentioned by NO tuple -- the phantom. f1 is the control: same shape, written.
QUERIES = [
    ('phantom f9', ('viewer', 'folder', 'f9', 'access', 'doc', 'd1')),
    ('phantom f9', ('viewer', 'folder', 'f9', 'admin', 'doc', 'd1')),
    ('phantom f9', ('viewer', 'folder', 'f9', 'gate', 'doc', 'd1')),
    ('control f1', ('viewer', 'folder', 'f1', 'access', 'doc', 'd1')),
    ('control f1', ('viewer', 'folder', 'f1', 'admin', 'doc', 'd1')),
    ('control f1', ('viewer', 'folder', 'f1', 'gate', 'doc', 'd1')),
    ('control f2', ('viewer', 'folder', 'f2', 'gate', 'doc', 'd1')),
]

for label, q in QUERIES:
    try:
        print(f'{label:12s} {q} -> UNANIMOUS {pe.check(*q)}')
    except AssertionError as e:
        print(f'{label:12s} {q} -> ** DIVERGENCE ** {e}')
    except Exception:                                    # noqa: BLE001
        print(f'{label:12s} {q} -> ERROR')
        traceback.print_exc()

pe.close()
