"""P6 part (iv), route `D` cone -- step 1: does the SHIPPED residue carry the star shape
where the Lean model's does not?

WHY. `formal/probes/p6_partiv_residue_locus_2026-09-14.lean` (2026-09-14g) measured the
Lean residue at `(doc:d1, admin)` as `stars := []`, `neg := []`,
`upos := [folder:f2#viewer, folder:f1#viewer]`, and showed the read path is innocent: the
phantom `folder:f9#viewer` and the AGREEING control `folder:f1#viewer` share the shape
`("folder","viewer")`, so `stars` could not have separated them and `upos` did.

Reading `index_v4/wildcard.py::WildcardIndex._check_derived`'s userset arm (`:773-781`)
says Python's logic is structurally the SAME as Lean's `State.lean::GraphModel.probeDerived`:

    stars, neg, upos = self._residue_state(relation, o_type, o_name)
    if subj is not None and subj.id in upos:     return True
    if (s_type, s_pred) not in stars:            return False
    return subj is None or subj.id not in neg

For the PHANTOM, `_get_concrete('viewer','folder','f9')` returns None (no node), so the
`upos` branch cannot fire. **There is therefore no path by which Python returns True except
`("folder","viewer") in stars`.** That is a prediction, and this probe tests it rather than
asserting it: if the shipped `stars` really carries the shape, route `D` ("make the Lean
cascade's star fold produce it") is the right fix and the Lean model is simply missing it.
If the shipped `stars` is ALSO empty, the prediction is wrong, `_check_derived` is not the
arm answering, and route `D` is mis-aimed.

Same schema and store as `p6_phantom_subject_2026-09-13.py`, so the answers are comparable.

    C:/Users/user/anaconda3/envs/graph-reachability-zanzibar-index/python.exe \
        formal/probes/p6_partiv_python_residue_2026-09-14.py

(!) INSTRUMENT CONTROL: `_residue_state` is read through the ParityEngine's graph side. If
the graph side were absent (`graph_drop_reason`) every read below would be vacuous, so the
probe refuses to continue without it. A second control reads the residue at a relation that
should be EMPTY of stars, so "every residue has the shape" cannot masquerade as a result.

THE VERDICT (2026-09-14g): **the prediction HOLDS.** The shipped residue carries the star
shape intensionally (`stars = [('folder','viewer')]`, `upos = []`) where the Lean model
carries concrete members extensionally (`stars = []`, `upos = [f2#viewer, f1#viewer]`).
Same answers at materialised subjects; they can only diverge at a phantom, which is exactly
where they do. Control `(5)` shows `banned` has EMPTY stars, so this is falsifiable and not
"every residue lists every shape"; `(4)` confirms the phantom has no node, so Python's
`upos` branch genuinely cannot fire and `stars` is the only path to its `True`.

Chased to ground in `formal/probes/p6_partiv_shapes_gap_2026-09-14.lean`: the Lean
enumeration `ReconcileStars.lean:97::wildcardShapes` implements only the first of the two
passes that build `SchemaInfo.subject_wildcard_shapes` (`zanzibar_utils_v1.py:993-1008`).

RAN 2026-09-14g, VERBATIM stdout:

    (I) INSTRUMENT CONTROL -- graph side present: True
    (1) * shipped residue at (doc:d1, admin)  (stars, neg, upos-ids): ([('folder', 'viewer')], [], [])
    (2) * shipped residue at (doc:d1, gate)   (stars, neg, upos-ids): ([('folder', 'viewer')], [], [])
    (3) * PREDICTION -- ("folder","viewer") in admin.stars: True
    (4) * the phantom has NO node (so the upos branch cannot fire): True
    (5) CONTROL -- shipped residue at (doc:d1, banned); stars should NOT carry the shape: ([], [], [])
    (6) the answers themselves (phantom admin, control admin): True True
"""
import sys

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
assert pe.graph is not None, f'graph side absent -- every read below would be vacuous: {pe.graph_drop_reason}'
print('(I) INSTRUMENT CONTROL -- graph side present:', pe.graph is not None)

for raw in [('...', 'folder', '*', 'parent', 'doc', 'd1'),
            ('...', 'user', 'alice', 'viewer', 'folder', 'f1'),
            ('...', 'user', 'bob', 'viewer', 'folder', 'f2')]:
    pe.add_tuple(*raw)

widx = pe.graph.widx


def residue(relation):
    """(stars, neg, upos) at (doc:d1, <relation>), with ids resolved to readable names."""
    stars, neg, upos = widx._residue_state(relation, 'doc', 'd1')
    return sorted(stars), sorted(neg), sorted(upos)


print('(1) * shipped residue at (doc:d1, admin)  (stars, neg, upos-ids):', residue('admin'))
print('(2) * shipped residue at (doc:d1, gate)   (stars, neg, upos-ids):', residue('gate'))

# THE PREDICTION under test.
stars_admin = residue('admin')[0]
print('(3) * PREDICTION -- ("folder","viewer") in admin.stars:',
      ('folder', 'viewer') in set(stars_admin))

# The phantom really is absent from the index -- otherwise `upos` could be answering.
try:
    node = widx.idx.node('viewer', 'folder', 'f9', create_if_missing=False)
except KeyError:
    node = None
print('(4) * the phantom has NO node (so the upos branch cannot fire):', node is None)

# CONTROL: a relation whose stars should NOT contain the shape, so that (3) is falsifiable
# and not just "every residue lists every shape".
print('(5) CONTROL -- shipped residue at (doc:d1, banned); stars should NOT carry the shape:',
      residue('banned'))

print('(6) the answers themselves (phantom admin, control admin):',
      pe.check('viewer', 'folder', 'f9', 'admin', 'doc', 'd1'),
      pe.check('viewer', 'folder', 'f1', 'admin', 'doc', 'd1'))

pe.close()
