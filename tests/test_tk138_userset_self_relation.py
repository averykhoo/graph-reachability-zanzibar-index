"""TK138 / TK144 -- a userset IS related to itself, as in OpenFGA (landing 2).

Property guarded
----------------
OpenFGA treats a userset subject ``o#r`` as a member of ``(o, r)`` unconditionally, at
every resolve node and outside the rewrite: ``Members(o, r) = {o#r} ∪ Eval(rewrite(r))``.
So it propagates through computed usersets, TTU and boolean arms, ACROSS objects, and it
flips a ``but not`` from ALLOW to DENY (the ``vx`` row). Since TK144 (landing 2, one
change set in all four corners) this library applies the same rule: the oracle and the set
engine with one disjunct in ``sat``, the graph index with compile-time seed probes on the
untainted side and a read-time plan evaluation on the derived side (challenge C5), the
lookups through a key channel for answers with no node (D3a), and the Lean spec / set
engine / graph models. Map, probes and decisions:
``docs/tk138-userset-self-relation-2026-10-14.md``; ledger entry ``docs/spec-deviations.md``
``## 2026-10-14 — TK138`` (and its TK144 addendum).

Landing 1 (2026-10-14) pinned the OPPOSITE: every corner unanimous on the non-reflexive
answer, and the exact set of rows where this repo differed from OpenFGA. This file is its
deliberate successor: the tables are unchanged literal transcripts, and the pin is now
AGREEMENT with them.

Every row carries the literal ``openfga`` answer, transcribed by hand from the live OpenFGA
v1.22.0 transcripts in the plan doc (section 1.1 model A, section 1.2 model B, challenge C1
model C, challenge C3 model D, and the 2026-10-17 probe 6, model E). It is NEVER derived
from ``tests/oracle.py``, so the oracle cannot drift with it. Each measured answer is
UNANIMOUS on every corner: ``check`` through ``tests/parity.py::ParityEngine`` (graph index,
set engine under both ``SetOps``, the oracle), lookups computed on the graph and both set
engines and required to agree after translation to ``(type, name, predicate)`` keys,
the key channel (``implicit_keys`` / ``implicit_excluded_keys``) included.

The repo differs from OpenFGA on exactly two rows, both deliberate and documented
(``REPO_EXCEPTIONS``):

* ``A14`` -- an UNDECLARED relation. OpenFGA answers ``validation_error``; this library
  reads leniently and answers False (unchanged by TK138).
* ``D03`` -- a TTU target undeclared on one of the tupleset's types (challenge C3). OpenFGA
  answers ``validation_error``; this library answers True through the ``ttu_leaf``
  from-chain disjunct, which sub-decision D4 keeps.

Rows that must NOT move are in the same tables or in ``REPO_ONLY`` (no OpenFGA probe):
concrete users, ``user:*``, the userset-star subject (D1: star subjects take no
self-relation), the C3 control row, and the self-tuple write refusal (both refuse it, this
repo as a cycle and OpenFGA as "implicit" -- challenge C6).

Model provenance
----------------
* Model A' is the plan doc's model A MINUS ``viewer_bn``, ``vi``, ``banned2`` and
  ``viewer_bn3`` (this repo refuses ``viewer_bn3``/``banned2`` as recursion through
  negation and ``vi`` as a cyclic derived dependency on the graph). Dropping them keeps
  every remaining definition byte-identical to the probed one, so OpenFGA's answers for
  the remaining relations transfer unchanged (REASONED in landing 1). Rows on the
  dropped relations are omitted.
* Models B, C, D and E are the probed models exactly.
* ``ListObjects`` rows project ``lookup(subject)`` onto ``(type, relation)``;
  ``ListUsers`` rows project ``lookup_reverse(relation, object)`` onto the filter
  (``T#r`` = userset keys of type ``T`` and relation ``r``; ``T`` = bare subjects).

Sabotage (2026-10-17, docs/sabotage-procedure.md) -- see ``SABOTAGE`` at the bottom of this
docstring. The plugin is ``formal/probes/tk144_sabotage_plugin_2026_10_17.py``; it patches
one corner at a time at pytest configure time, the source untouched.

SABOTAGE
--------
Observed 2026-10-17 (``SAB144=<mode>``, this module alone; with no mode: ``12 passed``).
Each corner and each guard alone turns it red, so no corner is carried by another. The
counts were RE-MEASURED 2026-10-17 after the review fix added the three seed-shape tests
at the bottom (9 -> 12 tests); each literal is the first failure and did not change.
S15-S19 are recorded in those three tests' docstrings:

* S1 oracle disjunct removed -- ``9 failed, 3 passed``: ``check disagreement on ('viewer',
  'doc', '1', 'viewer', 'doc', '1'): {'graph': True, 'set:py': True, 'set:roaring': True,
  'oracle': False}``
* S2 set-engine self hit removed -- ``9 failed, 3 passed``: ``... {'graph': True, 'set:py':
  False, 'set:roaring': False, 'oracle': True}``
* S3 graph untainted self-relation removed -- ``9 failed, 3 passed``: ``... {'graph': False,
  'set:py': True, 'set:roaring': True, 'oracle': True}``
* S4 graph untainted OWN-OBJECT ONLY (self hit kept, no probes from seed nodes; the
  challenge-C2 sabotage) -- ``4 failed, 8 passed``: ``check parity broken after add
  ('member', 'group', '1', 'viewer', 'doc', '1'): q=('admin', 'group', '1', 'nb', 'doc',
  '1') graph=False oracle=True``
* S5 graph derived C5 removed (the residue answers usersets) -- ``7 failed, 5 passed``:
  ``check disagreement on ('nb', 'doc', '1', 'nb', 'doc', '1'): {'graph': False, ...}``
* S6 graph derived self hit kept, plan evaluation removed -- ``7 failed, 5 passed``:
  ``check disagreement on ('viewer', 'doc', '1', 'nb', 'doc', '1'): {'graph': False, ...}``
* S7 set ``lookup`` own-object pass removed -- ``9 failed, 3 passed``: ``lookup('viewer',
  'doc', '1') disagrees across corners: {'graph': (frozenset({('doc', '1', 'can_view'),
  ('doc', '1', 'nb'), ('doc', '1', 'viewer')}), ...), 'set:py': (frozenset(), ...``
* S8 set ``expand`` correction removed -- ``9 failed, 3 passed``: ``lookup_reverse('viewer',
  'doc', '1') disagrees across corners: {'graph': (frozenset({('doc', '1', 'viewer')}),
  ...), 'set:py': (frozenset(), ...``
* S9 graph ``_self_lookup`` removed -- ``9 failed, 3 passed``: ``lookup('viewer', 'doc', '1')
  disagrees across corners: {'graph': (frozenset(), ...``
* S10 graph untainted reverse expansion removed -- ``9 failed, 3 passed``:
  ``lookup_reverse('viewer', 'doc', '1') disagrees across corners: {'graph': (frozenset(),
  ...), 'set:py': (frozenset({('doc', '1', 'viewer')}), ...``
* S11 graph derived reverse correction removed -- ``6 failed, 6 passed``:
  ``lookup_reverse('nb', 'doc', '1') disagrees across corners: {'graph': (frozenset(), ...),
  'set:py': (frozenset({('doc', '1', 'nb'), ('doc', '1', 'viewer')}), ...``
* S12 D1 widened in the oracle (userset STAR subjects take the rule) -- ``1 failed, 11
  passed``: ``check disagreement on ('viewer', 'doc', '*', 'viewer', 'doc', '*'): {'graph':
  False, 'set:py': False, 'set:roaring': False, 'oracle': True}`` (the ``doc:*#viewer`` at
  ``doc:*`` row in ``REPO_ONLY`` exists for this).

The ``s_pred != '...'`` guard has no sabotage that can turn it red: no declared relation is
named ``...``, so a bare subject never equals a node key. It is kept for the Lean twin
(``Spec/Semantics.lean::selfHit``), whose ``sem`` carries no well-formedness hypothesis.
"""

from __future__ import annotations

import pytest

from zanzibar.graphindex import Node

from tests.parity import ParityEngine

T, F = True, False
ERR = 'ERR'           # OpenFGA answered 400 validation_error; this repo reads leniently

# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #

MODEL_A = """
model
  schema 1.1
type user
type folder
  relations
    define viewer: [user, folder#viewer]
    define plain: [user]
type doc
  relations
    define viewer: [user, doc#viewer]
    define banned: [user]
    define editor: [user]
    define plain: [user]
    define parent: [folder]
    define can_view: viewer
    define fview: viewer from parent
    define fplain: plain from parent
    define vu: [user] or editor
    define nb: viewer but not banned
"""

MODEL_B = """
model
  schema 1.1
type user
type doc
  relations
    define banned: [user]
    define editor: [user]
    define plain: [user]
    define viewer: [user, doc#viewer]
    define vx: [user, doc#banned] but not banned
    define vy: [user, doc#editor] and editor
    define nb: viewer but not banned
    define chain: [user, doc#viewer]
    define cv: plain
"""

MODEL_C = """
model
  schema 1.1
type user
type group
  relations
    define admin: [user]
    define member: [user] or admin
type doc
  relations
    define viewer: [user, group#member]
    define banned: [user, group#admin]
    define nb: viewer but not banned
"""

# Challenge C3: a TTU target declared on only one of the tupleset's types (ASK-1 allows it).
MODEL_D = """
model
  schema 1.1
type user
type team
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder, team]
    define x: viewer from parent
"""

# Probe 6 (2026-10-17): challenge C2's variant -- model C with `[group#admin]` removed
# everywhere -- plus a TTU whose target computes from the subject's relation.
MODEL_E = """
model
  schema 1.1
type user
type group
  relations
    define admin: [user]
    define member: [user] or admin
type folder
  relations
    define editor: [user]
    define viewer: [user] or editor
type doc
  relations
    define viewer: [user, group#member]
    define banned: [user]
    define nb: viewer but not banned
    define parent: [folder]
    define fview: viewer from parent
"""

# --------------------------------------------------------------------------- #
# Row encoding.  Subjects and objects are 'type:name' / 'type:name#relation'.
#   ('CHECK',   subject, relation, object)
#   ('LISTOBJ', subject, 'type#relation')                -> set of 'type:name'
#   ('LISTUSR', object, relation, filter)                -> set of subjects
#   ('WRITE',   subject, relation, object)               -> 'ok' | 'refused'
# A row is (row_id, phase, query, openfga); phase 'empty' runs before the model's
# writes, 'write' is a write, 'after' runs after all writes.
# --------------------------------------------------------------------------- #

ROWS_A = [
    # plan doc 1.1, "== empty store ==" (openfga_probe.out)
    ('A01', 'empty', ('CHECK', 'doc:1#viewer', 'viewer', 'doc:1'), T),
    ('A02', 'empty', ('CHECK', 'doc:1#viewer', 'viewer', 'doc:2'), F),
    ('A03', 'empty', ('CHECK', 'doc:1#editor', 'viewer', 'doc:1'), F),
    ('A04', 'empty', ('CHECK', 'doc:1#plain', 'plain', 'doc:1'), T),
    ('A05', 'empty', ('CHECK', 'doc:1#banned', 'banned', 'doc:1'), T),
    ('A06', 'empty', ('CHECK', 'doc:1#can_view', 'can_view', 'doc:1'), T),
    ('A07', 'empty', ('CHECK', 'doc:1#viewer', 'can_view', 'doc:1'), T),
    ('A08', 'empty', ('CHECK', 'doc:1#fview', 'fview', 'doc:1'), T),
    ('A09', 'empty', ('CHECK', 'doc:1#vu', 'vu', 'doc:1'), T),
    ('A10', 'empty', ('CHECK', 'doc:1#nb', 'nb', 'doc:1'), T),
    ('A11', 'empty', ('CHECK', 'doc:1#viewer', 'nb', 'doc:1'), T),
    ('A12', 'empty', ('CHECK', 'folder:1#viewer', 'viewer', 'folder:1'), T),
    ('A13', 'empty', ('CHECK', 'folder:1#viewer', 'fview', 'doc:1'), F),
    ('A14', 'empty', ('CHECK', 'doc:1#nosuchrel', 'nosuchrel', 'doc:1'), ERR),
    ('A15', 'empty', ('LISTOBJ', 'doc:1#viewer', 'doc#viewer'), {'doc:1'}),
    ('A16', 'empty', ('LISTOBJ', 'doc:1#viewer', 'doc#can_view'), {'doc:1'}),
    ('A17', 'empty', ('LISTUSR', 'doc:1', 'viewer', 'doc#viewer'), {'doc:1#viewer'}),
    ('A18', 'empty', ('LISTUSR', 'doc:1', 'can_view', 'doc#viewer'), {'doc:1#viewer'}),
    ('A19', 'empty', ('LISTUSR', 'doc:1', 'viewer', 'user'), set()),
    # "== writes ==" (the banned2 write is on a dropped relation; see the docstring)
    ('A20', 'write', ('WRITE', 'doc:1#viewer', 'viewer', 'doc:1'), 'refused'),
    ('A21', 'write', ('WRITE', 'doc:1#viewer', 'viewer', 'doc:2'), 'ok'),
    ('A22', 'write', ('WRITE', 'user:alice', 'viewer', 'doc:1'), 'ok'),
    ('A23', 'write', ('WRITE', 'user:bob', 'banned', 'doc:1'), 'ok'),
    ('A24', 'write', ('WRITE', 'user:bob', 'viewer', 'doc:1'), 'ok'),
    ('A25', 'write', ('WRITE', 'folder:1', 'parent', 'doc:1'), 'ok'),
    ('A26', 'write', ('WRITE', 'user:carol', 'viewer', 'folder:1'), 'ok'),
    # "== after writes =="
    ('A27', 'after', ('CHECK', 'doc:1#viewer', 'viewer', 'doc:1'), T),
    ('A28', 'after', ('CHECK', 'doc:1#viewer', 'viewer', 'doc:2'), T),
    ('A29', 'after', ('CHECK', 'folder:1#viewer', 'fview', 'doc:1'), T),   # TTU from-chain
    ('A30', 'after', ('CHECK', 'folder:1#plain', 'fplain', 'doc:1'), T),   # TTU from-chain
    ('A31', 'after', ('CHECK', 'folder:2#viewer', 'fview', 'doc:1'), F),
    ('A32', 'after', ('CHECK', 'user:alice', 'viewer', 'doc:2'), T),
    ('A33', 'after', ('CHECK', 'user:bob', 'nb', 'doc:1'), F),
    ('A34', 'after', ('LISTOBJ', 'doc:1#viewer', 'doc#viewer'), {'doc:1', 'doc:2'}),
    ('A35', 'after', ('LISTOBJ', 'doc:1#viewer', 'doc#can_view'), {'doc:1', 'doc:2'}),
    ('A36', 'after', ('LISTOBJ', 'folder:1#viewer', 'doc#fview'), {'doc:1'}),
    ('A37', 'after', ('LISTOBJ', 'folder:1#viewer', 'folder#viewer'), {'folder:1'}),
    ('A38', 'after', ('LISTUSR', 'doc:1', 'viewer', 'doc#viewer'), {'doc:1#viewer'}),
    ('A39', 'after', ('LISTUSR', 'doc:2', 'viewer', 'doc#viewer'),
     {'doc:2#viewer', 'doc:1#viewer'}),
    ('A40', 'after', ('LISTUSR', 'doc:1', 'fview', 'folder#viewer'), {'folder:1#viewer'}),
    ('A41', 'after', ('LISTUSR', 'doc:2', 'viewer', 'user'), {'user:alice', 'user:bob'}),
]

ROWS_B = [
    # plan doc 1.2 (openfga_probe2.out)
    ('B01', 'empty', ('CHECK', 'doc:1#plain', 'plain', 'doc:1'), T),
    ('B02', 'empty', ('LISTOBJ', 'doc:1#plain', 'doc#plain'), {'doc:1'}),
    ('B03', 'empty', ('LISTUSR', 'doc:1', 'plain', 'doc#plain'), {'doc:1#plain'}),
    ('B04', 'empty', ('CHECK', 'doc:1#plain', 'cv', 'doc:1'), T),
    ('B05', 'empty', ('LISTOBJ', 'doc:1#plain', 'doc#cv'), {'doc:1'}),
    ('B06', 'empty', ('LISTUSR', 'doc:1', 'cv', 'doc#plain'), {'doc:1#plain'}),
    ('B07', 'empty', ('CHECK', 'doc:1#viewer', 'nb', 'doc:1'), T),
    ('B08', 'empty', ('LISTOBJ', 'doc:1#viewer', 'doc#nb'), {'doc:1'}),
    ('B09', 'empty', ('LISTUSR', 'doc:1', 'nb', 'doc#viewer'), {'doc:1#viewer'}),
    ('B10', 'write', ('WRITE', 'doc:1#banned', 'vx', 'doc:1'), 'ok'),
    ('B11', 'write', ('WRITE', 'doc:1#editor', 'vy', 'doc:1'), 'ok'),
    ('B12', 'write', ('WRITE', 'doc:1#viewer', 'chain', 'doc:2'), 'ok'),
    ('B13', 'write', ('WRITE', 'doc:2#chain', 'viewer', 'doc:3'), 'refused'),
    # the vx row: DENIED by OpenFGA (self in the subtrahend); ALLOWED here before TK144
    ('B14', 'after', ('CHECK', 'doc:1#banned', 'vx', 'doc:1'), F),
    ('B15', 'after', ('CHECK', 'doc:1#banned', 'vx', 'doc:2'), F),
    ('B16', 'after', ('CHECK', 'doc:1#editor', 'vy', 'doc:1'), T),
    ('B17', 'after', ('LISTOBJ', 'doc:1#banned', 'doc#vx'), set()),
    ('B18', 'after', ('LISTUSR', 'doc:1', 'vx', 'doc#banned'), set()),
    ('B19', 'after', ('LISTOBJ', 'doc:1#editor', 'doc#vy'), {'doc:1'}),
    ('B20', 'after', ('LISTUSR', 'doc:1', 'vy', 'doc#editor'), {'doc:1#editor'}),
    ('B21', 'after', ('CHECK', 'doc:1#viewer', 'chain', 'doc:2'), T),
    ('B22', 'after', ('CHECK', 'doc:2#chain', 'chain', 'doc:2'), T),
]

ROWS_C = [
    # challenge C1 (openfga_probe3.out); the server was asked only after the writes
    ('C01', 'write', ('WRITE', 'group:1#member', 'viewer', 'doc:1'), 'ok'),
    ('C02', 'write', ('WRITE', 'group:1#member', 'viewer', 'doc:2'), 'ok'),
    ('C03', 'write', ('WRITE', 'group:1#admin', 'banned', 'doc:2'), 'ok'),
    ('C04', 'write', ('WRITE', 'user:alice', 'admin', 'group:1'), 'ok'),
    ('C05', 'write', ('WRITE', 'group:3#member', 'viewer', 'doc:1'), 'ok'),
    ('C06', 'after', ('CHECK', 'group:1#admin', 'viewer', 'doc:1'), T),
    ('C07', 'after', ('CHECK', 'group:1#admin', 'nb', 'doc:1'), T),
    ('C08', 'after', ('CHECK', 'group:3#admin', 'viewer', 'doc:1'), T),
    ('C09', 'after', ('CHECK', 'group:3#admin', 'nb', 'doc:1'), T),
    ('C10', 'after', ('CHECK', 'group:1#member', 'nb', 'doc:1'), T),
    ('C11', 'after', ('CHECK', 'group:1#admin', 'nb', 'doc:2'), F),
    ('C12', 'after', ('CHECK', 'group:1#member', 'nb', 'doc:2'), T),
    ('C13', 'after', ('CHECK', 'user:alice', 'nb', 'doc:2'), F),
    ('C14', 'after', ('CHECK', 'user:alice', 'nb', 'doc:1'), T),
    ('C15', 'after', ('LISTOBJ', 'group:1#admin', 'doc#viewer'), {'doc:1', 'doc:2'}),
    ('C16', 'after', ('LISTOBJ', 'group:1#admin', 'doc#nb'), {'doc:1'}),
    ('C17', 'after', ('LISTOBJ', 'group:3#admin', 'doc#nb'), {'doc:1'}),
    ('C18', 'after', ('LISTUSR', 'doc:1', 'nb', 'group#admin'),
     {'group:1#admin', 'group:3#admin'}),
    ('C19', 'after', ('LISTUSR', 'doc:2', 'nb', 'group#member'), {'group:1#member'}),
]

ROWS_D = [
    # challenge C3 (openfga_probe5.out: "relation 'team#viewer' not found"). This repo
    # answers True through the ttu_leaf from-chain disjunct, which TK138 keeps (D4).
    ('D01', 'write', ('WRITE', 'team:1', 'parent', 'doc:1'), 'ok'),
    ('D02', 'write', ('WRITE', 'folder:1', 'parent', 'doc:1'), 'ok'),
    ('D03', 'after', ('CHECK', 'team:1#viewer', 'x', 'doc:1'), ERR),
]

ROWS_E = [
    # probe 6, 2026-10-17 (plan doc, corrections 2026-10-17: openfga_probe6.out)
    ('E01', 'write', ('WRITE', 'group:1#member', 'viewer', 'doc:1'), 'ok'),
    ('E02', 'write', ('WRITE', 'group:1#member', 'viewer', 'doc:2'), 'ok'),
    ('E03', 'write', ('WRITE', 'user:alice', 'admin', 'group:1'), 'ok'),
    ('E04', 'write', ('WRITE', 'user:bob', 'banned', 'doc:2'), 'ok'),
    ('E05', 'write', ('WRITE', 'group:3#member', 'viewer', 'doc:1'), 'ok'),
    ('E06', 'write', ('WRITE', 'folder:1', 'parent', 'doc:1'), 'ok'),
    ('E07', 'after', ('CHECK', 'group:1#admin', 'viewer', 'doc:1'), T),
    ('E08', 'after', ('CHECK', 'group:1#admin', 'nb', 'doc:1'), T),
    ('E09', 'after', ('CHECK', 'group:3#admin', 'viewer', 'doc:1'), T),
    ('E10', 'after', ('CHECK', 'group:3#admin', 'nb', 'doc:1'), T),
    ('E11', 'after', ('CHECK', 'group:1#admin', 'nb', 'doc:2'), T),
    ('E12', 'after', ('CHECK', 'group:1#member', 'nb', 'doc:2'), T),
    ('E13', 'after', ('CHECK', 'user:alice', 'nb', 'doc:2'), T),
    ('E14', 'after', ('CHECK', 'user:bob', 'nb', 'doc:2'), F),
    ('E15', 'after', ('CHECK', 'user:alice', 'nb', 'doc:1'), T),
    ('E16', 'after', ('CHECK', 'group:2#admin', 'viewer', 'doc:1'), F),
    ('E17', 'after', ('CHECK', 'folder:1#editor', 'fview', 'doc:1'), T),
    ('E18', 'after', ('CHECK', 'folder:1#viewer', 'fview', 'doc:1'), T),
    ('E19', 'after', ('CHECK', 'folder:2#editor', 'fview', 'doc:1'), F),
    ('E20', 'after', ('LISTOBJ', 'group:1#admin', 'doc#viewer'), {'doc:1', 'doc:2'}),
    ('E21', 'after', ('LISTOBJ', 'group:1#admin', 'doc#nb'), {'doc:1', 'doc:2'}),
    ('E22', 'after', ('LISTOBJ', 'group:3#admin', 'doc#nb'), {'doc:1'}),
    ('E23', 'after', ('LISTOBJ', 'folder:1#editor', 'doc#fview'), {'doc:1'}),
    ('E24', 'after', ('LISTUSR', 'doc:1', 'nb', 'group#admin'),
     {'group:1#admin', 'group:3#admin'}),
    ('E25', 'after', ('LISTUSR', 'doc:2', 'nb', 'group#admin'), {'group:1#admin'}),
    ('E26', 'after', ('LISTUSR', 'doc:1', 'fview', 'folder#editor'), {'folder:1#editor'}),
]

# Pins with NO OpenFGA probe behind them: they must not move (the rule adds only the
# subject o#r itself -- never its members, never a star subject (D1)).
REPO_ONLY = {
    'A': [('after', ('CHECK', 'user:*', 'viewer', 'doc:1'), F),
          ('after', ('CHECK', 'user:*', 'nb', 'doc:1'), F),
          ('after', ('CHECK', 'doc:*#viewer', 'viewer', 'doc:1'), F),   # D1: userset star
          ('after', ('CHECK', 'doc:*#viewer', 'viewer', 'doc:2'), F),
          ('after', ('CHECK', 'doc:*#viewer', 'viewer', 'doc:*'), F),   # D1 at its own node
          ('after', ('CHECK', 'user:carol', 'fview', 'doc:1'), T),
          ('after', ('CHECK', 'user:alice', 'can_view', 'doc:1'), T),
          ('after', ('CHECK', 'user:bob', 'can_view', 'doc:2'), T)],
    'B': [('after', ('CHECK', 'user:*', 'vx', 'doc:1'), F),
          ('after', ('CHECK', 'doc:*#banned', 'vx', 'doc:1'), F)],
    'C': [('after', ('CHECK', 'user:*', 'nb', 'doc:1'), F),
          ('after', ('CHECK', 'group:*#admin', 'nb', 'doc:1'), F)],
    'D': [('after', ('CHECK', 'folder:1#viewer', 'x', 'doc:1'), T)],   # C3's control row
    'E': [('after', ('CHECK', 'group:*#admin', 'nb', 'doc:1'), F),
          ('after', ('CHECK', 'user:bob', 'viewer', 'doc:2'), F)],
}

# The ONLY rows where this repo answers differently from OpenFGA, with the repo's answer.
REPO_EXCEPTIONS = {
    'A14': F,     # undeclared relation: OpenFGA validation_error, this repo reads leniently
    'D03': T,     # D4: the ttu_leaf from-chain disjunct is kept (challenge C3)
}

MODELS = {
    'A': (MODEL_A, ROWS_A),
    'B': (MODEL_B, ROWS_B),
    'C': (MODEL_C, ROWS_C),
    'D': (MODEL_D, ROWS_D),
    'E': (MODEL_E, ROWS_E),
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _ent(text: str) -> tuple[str, str, str]:
    """'type:name[#pred]' -> (type, name, pred) with '...' for a bare subject."""
    ent, _, pred = text.partition('#')
    t, _, n = ent.partition(':')
    return t, n, pred or '...'


def _render(key: tuple[str, str, str]) -> str:
    t, n, p = key
    return f'{t}:{n}' if p == '...' else f'{t}:{n}#{p}'


def _raw(subject: str, relation: str, obj: str) -> tuple[str, ...]:
    st, sn, sp = _ent(subject)
    ot, on, _ = _ent(obj)
    return sp, st, sn, relation, ot, on


def _graph_keys(pe: ParityEngine, ids) -> set[tuple[str, str, str]]:
    out = set()
    for nid in ids:
        node = pe.graph.session.get(Node, nid)
        assert node is not None, f'dead graph node id {nid}'
        out.add((node.type, node.name, node.predicate))
    return out


def _lookup_keys(pe: ParityEngine, kind: str, *args) -> set[tuple[str, str, str]]:
    """``lookup`` / ``lookup_reverse`` on the graph and BOTH set engines, translated to
    portable keys (ids and the TK144 key channel) and required to agree across corners
    (ParityEngine pins check parity only)."""
    assert pe.graph is not None, pe.graph_drop_reason
    answers = {}
    g = getattr(pe.graph.widx, kind)(*args)
    answers['graph'] = (frozenset(_graph_keys(pe, g.node_ids) | set(g.implicit_keys)),
                        frozenset(g.markers),
                        frozenset(_graph_keys(pe, g.excluded_node_ids)
                                  | set(g.implicit_excluded_keys)))
    for side in pe.set_sides:
        r = getattr(side.se, kind)(*args)
        answers[side.name] = (frozenset(side.se.result_keys(r)), frozenset(r.markers),
                              frozenset(side.se.excluded_keys(r)))
    assert len(set(answers.values())) == 1, f'{kind}{args} disagrees across corners: {answers}'
    nodes, markers, excluded = answers['graph']
    # No row here involves a wildcard: a marker or an exclusion would need its own row.
    assert not markers and not excluded, f'{kind}{args}: unexpected {markers} / {excluded}'
    return set(nodes)


def _ask(pe: ParityEngine, query: tuple):
    kind = query[0]
    if kind == 'CHECK':
        _, subject, relation, obj = query
        return pe.check(*_raw(subject, relation, obj))           # unanimous incl. oracle
    if kind == 'WRITE':
        _, subject, relation, obj = query
        return 'ok' if pe.add_tuple(*_raw(subject, relation, obj)) else 'refused'
    if kind == 'LISTOBJ':
        _, subject, target = query
        st, sn, sp = _ent(subject)
        o_type, _, rel = target.partition('#')
        keys = _lookup_keys(pe, 'lookup', sp, st, sn)
        return {f'{t}:{n}' for (t, n, p) in keys if t == o_type and p == rel}
    if kind == 'LISTUSR':
        _, obj, relation, filt = query
        ot, on, _ = _ent(obj)
        f_type, _, f_rel = filt.partition('#')
        f_rel = f_rel or '...'
        keys = _lookup_keys(pe, 'lookup_reverse', relation, ot, on)
        return {_render(k) for k in keys if k[0] == f_type and k[2] == f_rel}
    raise AssertionError(f'unknown row kind {kind!r}')


def _run_model(model: str):
    """Run the model's rows in phase order; return {row_id: (openfga, measured)}."""
    schema, rows = MODELS[model]
    pe = ParityEngine(schema)
    try:
        assert pe.graph is not None, f'model {model} lost the graph: {pe.graph_drop_reason}'
        measured = {}
        for phase in ('empty', 'write', 'after'):
            for row_id, row_phase, query, openfga in rows:
                if row_phase == phase:
                    measured[row_id] = (openfga, _ask(pe, query))
            for row_phase, query, want in REPO_ONLY.get(model, []):
                if row_phase == phase:
                    got = _ask(pe, query)
                    assert got == want, f'repo-only pin moved: {query} -> {got}, pinned {want}'
        return measured
    finally:
        pe.close()


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

def test_row_ids_are_unique_and_exceptions_name_real_rows():
    """Instrument control: unique ids, and every exception names a real row whose
    OpenFGA answer is NOT the repo answer it records (so the exceptions are not vacuous)."""
    all_rows = {}
    for model, (_, rows) in MODELS.items():
        ids = [r[0] for r in rows]
        assert len(ids) == len(set(ids)), f'duplicate row id in model {model}'
        all_rows.update({r[0]: r for r in rows})
    for row_id, repo in REPO_EXCEPTIONS.items():
        assert row_id in all_rows, row_id
        assert all_rows[row_id][3] != repo, f'{row_id}: exception equals OpenFGA'


@pytest.mark.parametrize('model', sorted(MODELS))
def test_every_corner_agrees_with_openfga(model):
    """Every row's measured answer -- unanimous on every corner -- equals OpenFGA
    v1.22.0's literal answer, except the documented ``REPO_EXCEPTIONS``."""
    measured = _run_model(model)
    _, rows = MODELS[model]
    assert set(measured) == {r[0] for r in rows}
    wrong = {}
    for row_id, (openfga, got) in measured.items():
        want = REPO_EXCEPTIONS.get(row_id, openfga)
        if got != want:
            wrong[row_id] = (want, got)
    assert not wrong, f'model {model}: rows off the pinned answer (row: pinned, measured): {wrong}'


def test_vx_is_denied_like_openfga():
    """The security-relevant direction, named on its own so a reader cannot miss it: a
    stored ``doc:1#banned vx doc:1`` under ``vx: [user, doc#banned] but not banned`` is
    DENIED, as by OpenFGA v1.22.0 (``doc:1#banned`` is in the subtrahend ``banned`` on
    ``doc:1`` by the self-relation). Before TK144 this library ALLOWED it -- an
    ALLOW-to-DENY change for any caller that relied on it (``CHANGELOG.md``)."""
    by_id = {r[0]: r for r in ROWS_B}
    assert by_id['B14'][2] == ('CHECK', 'doc:1#banned', 'vx', 'doc:1')
    assert by_id['B14'][3] is False
    measured = _run_model('B')
    assert measured['B14'] == (False, False)
    assert measured['B17'] == (set(), set()) and measured['B18'] == (set(), set())


def test_cross_object_userset_no_restriction_names():
    """Challenge C1/C2: the self-relation crosses objects, and reaches a userset that no
    type restriction names. In model E (no ``[group#admin]`` anywhere) ``group:3#admin`` --
    which has no tuple of its own and no graph node -- is a viewer of ``doc:1`` and listed
    by ``lookup_reverse`` through the key channel."""
    measured = _run_model('E')
    for row in ('E09', 'E10', 'E22', 'E24'):
        openfga, got = measured[row]
        assert got == openfga, (row, openfga, got)


def test_self_tuple_write_is_refused_on_every_backend():
    """Both sides refuse the EXACT self tuple ``doc:1#viewer viewer doc:1`` -- OpenFGA as
    "implicit" (400), this repo as a closure cycle (``AdmissionRejected``, unanimous via
    ParityEngine, I12 row multisets unchanged). Agreement in outcome only (C6)."""
    pe = ParityEngine(MODEL_A)
    try:
        assert pe.add_tuple(*_raw('doc:1#viewer', 'viewer', 'doc:1')) is False
        assert pe.add_tuple(*_raw('folder:1#viewer', 'viewer', 'folder:1')) is False
        assert pe.present == set()
    finally:
        pe.close()


# --------------------------------------------------------------------------- #
# Seed-shape wildcard and object-star probes (TK144 review, 2026-10-17)
# --------------------------------------------------------------------------- #
# Models A-E reach the self-relation's seed probes only through plain userset nodes. The
# graph read has three more branches -- a seed SHAPE's ``w_any`` probe, its witness gate,
# and the seed -> object-star ``w_all`` probe -- plus their lookup twins, and the review
# found each of them deletable with the whole gate green (4090 passed under each of W1,
# W2+L1 and W3). These pins close that. ``[group:*#member]`` and object wildcards are
# beyond OpenFGA (ASK-2), so there is NO OpenFGA answer to transcribe: the pinned values
# are the oracle's (the referee), REASONED from ``Members(o, r) = {o#r} ∪ Eval(rewrite(r))``
# with a ``[T:*#r1]`` grant expanded over tuple-mentioned instances only
# (``tests/oracle.py`` ``instances``), and required UNANIMOUS on every corner.

# Model F: a seed shape that is a subject-wildcard shape. ``(group, admin)`` seeds
# ``member``; ``(group, member)`` is a declared subject-wildcard shape via ``[group:*#member]``.
MODEL_F = """
model
  schema 1.1
type user
type group
  relations
    define admin: [user]
    define owner: [user]
    define member: [user] or admin
type doc
  relations
    define viewer: [user, group:*#member]
    define banned: [user]
    define nb: viewer but not banned
"""

# Model G: model C's shape with an object wildcard on (doc, viewer) (no OpenFGA syntax).
MODEL_G = """
model
  schema 1.1
type user
type group
  relations
    define admin: [user]
    define member: [user] or admin
type doc
  relations
    define viewer: [user, group#member]
"""


def _lookup_all(pe: ParityEngine, kind: str, *args):
    """Like ``_lookup_keys``, but wildcard markers allowed: the graph's ``(t, p, variant)``
    markers map to the set engine's ``(t, p)`` -- variant ``all`` for a forward lookup,
    ``any`` for a reverse one; the other variant must not occur. Returns
    ``(keys, markers, excluded)``, unanimous across the graph and both set engines."""
    assert pe.graph is not None, pe.graph_drop_reason
    variant = 'all' if kind == 'lookup' else 'any'
    g = getattr(pe.graph.widx, kind)(*args)
    assert {v for (_, _, v) in g.markers} <= {variant}, (kind, args, g.markers)
    answers = {'graph': (frozenset(_graph_keys(pe, g.node_ids) | set(g.implicit_keys)),
                         frozenset((t, p) for (t, p, _) in g.markers),
                         frozenset(_graph_keys(pe, g.excluded_node_ids)
                                   | set(g.implicit_excluded_keys)))}
    for side in pe.set_sides:
        r = getattr(side.se, kind)(*args)
        answers[side.name] = (frozenset(side.se.result_keys(r)), frozenset(r.markers),
                              frozenset(side.se.excluded_keys(r)))
    assert len(set(answers.values())) == 1, f'{kind}{args} disagrees across corners: {answers}'
    return answers['graph']


def test_seed_shape_wildcard_unwitnessed_entity_is_denied():
    """W2 guard (the false-ALLOW direction). ``group:*#member viewer doc:1`` grants
    ``viewer`` to the members of every group INSTANCE; ``group:zz-ghost`` and ``group:1``
    are mentioned by no tuple, so ``group:zz-ghost#admin`` / ``group:1#admin`` are not
    viewers even though ``admin`` seeds ``member``. The graph's seed-shape ``w_any`` probe
    is gated on ``_entity_has_witness``; without the gate it ALLOWS a ghost userset.

    Sabotage (2026-10-17, ``SAB144=S16``: the gate's condition replaced by ``if False:``):
    ``2 failed, 10 passed`` (this test and the next): ``check parity broken after add
    ('member', 'group', '*', 'viewer', 'doc', '1'): q=('admin', 'group', 'zz-ghost', 'nb',
    'doc', '1') graph=True oracle=False``
    """
    pe = ParityEngine(MODEL_F)
    try:
        assert pe.graph is not None, pe.graph_drop_reason
        assert pe.add_tuple('member', 'group', '*', 'viewer', 'doc', '1')
        assert pe.check('admin', 'group', 'zz-ghost', 'nb', 'doc', '1') is False
        assert pe.check('admin', 'group', 'zz-ghost', 'viewer', 'doc', '1') is False
        assert pe.check('admin', 'group', '1', 'viewer', 'doc', '1') is False
        assert pe.check('admin', 'group', '1', 'nb', 'doc', '1') is False
        keys, markers, excluded = _lookup_all(pe, 'lookup', 'admin', 'group', '1')
        assert keys == {('group', '1', 'admin'), ('group', '1', 'member')}
        assert not markers and not excluded
        keys, markers, excluded = _lookup_all(pe, 'lookup_reverse', 'viewer', 'doc', '1')
        assert keys == {('doc', '1', 'viewer')}
        assert markers == {('group', 'member')} and not excluded
    finally:
        pe.close()


def test_seed_shape_wildcard_witnessed_entity_without_seed_node():
    """W1 / L1 / R1 guard (the false-DENY direction). ``user:alice owner group:1`` makes
    ``group:1`` an instance WITHOUT creating a ``group:1#member`` node, so the only graph
    route from ``group:1#admin`` to ``doc:1#viewer`` is the seed SHAPE's ``w_any(group,
    member)`` node (the probe in ``_check_internal``, the collection in ``_self_lookup``,
    the marker expansion in ``_self_reverse_extra``). ``group:7`` stays unwitnessed.

    Sabotage (2026-10-17): ``SAB144=S15`` (the seed-shape ``w_any`` probes dropped):
    ``1 failed, 11 passed``: ``check parity broken after add ('...', 'user', 'alice',
    'owner', 'group', '1'): q=('admin', 'group', '1', 'nb', 'doc', '1') graph=False oracle=True``
    ``SAB144=S18`` (``_self_lookup``'s witnessed seed-shape collection dropped):
    ``1 failed, 11 passed``: ``lookup('admin', 'group', '1') disagrees across corners:
    {'graph': (frozenset({('group', '1', 'admin'), ('doc', '1', 'nb'), ('group', '1',
    'member')}), ...), 'set:py': (frozenset({..., ('doc', '1', 'viewer'), ...``
    ``SAB144=S19`` (``_self_reverse_extra``'s ``any``-marker expansion dropped):
    ``1 failed, 11 passed``: ``lookup_reverse('viewer', 'doc', '1') disagrees across
    corners: {'graph': (frozenset({('doc', '1', 'viewer')}), frozenset({('group',
    'member')}), ...), 'set:py': (frozenset({('group', '1', 'admin'), ('doc', '1',
    'viewer')}), ...``
    """
    pe = ParityEngine(MODEL_F)
    try:
        assert pe.graph is not None, pe.graph_drop_reason
        assert pe.add_tuple('member', 'group', '*', 'viewer', 'doc', '1')
        assert pe.add_tuple('...', 'user', 'alice', 'owner', 'group', '1')
        assert pe.check('admin', 'group', '1', 'viewer', 'doc', '1') is True
        assert pe.check('admin', 'group', '1', 'nb', 'doc', '1') is True
        assert pe.check('admin', 'group', '7', 'viewer', 'doc', '1') is False
        keys, markers, excluded = _lookup_all(pe, 'lookup', 'admin', 'group', '1')
        assert keys == {('group', '1', 'admin'), ('group', '1', 'member'),
                        ('doc', '1', 'viewer'), ('doc', '1', 'nb')}
        assert not markers and not excluded
        for rel, want in (('viewer', {('doc', '1', 'viewer'), ('group', '1', 'admin')}),
                          ('nb', {('doc', '1', 'nb'), ('doc', '1', 'viewer'),
                                  ('group', '1', 'admin')})):
            keys, markers, excluded = _lookup_all(pe, 'lookup_reverse', rel, 'doc', '1')
            assert keys == want, (rel, keys)
            assert markers == {('group', 'member')} and not excluded
    finally:
        pe.close()


def test_seed_node_reaches_object_star():
    """W3 guard. ``group:1#member viewer doc:*`` under an object wildcard on
    ``(doc, viewer)``: ``group:1#admin`` (no node of its own) is a viewer of EVERY doc
    through the seed node ``group:1#member`` -> ``w_all(doc, viewer)`` probe, and
    ``group:2#admin`` is not.

    Sabotage (2026-10-17, ``SAB144=S17``: the seed -> ``w_all`` probe deleted):
    ``1 failed, 11 passed``: ``check parity broken after add ('member', 'group', '1',
    'viewer', 'doc', '*'): q=('admin', 'group', '1', 'viewer', 'doc', 'zz-ghost')
    graph=False oracle=True``
    """
    pe = ParityEngine(MODEL_G, object_wildcard_shapes=frozenset({('doc', 'viewer')}))
    try:
        assert pe.graph is not None, pe.graph_drop_reason
        assert pe.add_tuple('member', 'group', '1', 'viewer', 'doc', '*')
        assert pe.check('admin', 'group', '1', 'viewer', 'doc', '5') is True
        assert pe.check('admin', 'group', '2', 'viewer', 'doc', '5') is False
        keys, markers, excluded = _lookup_all(pe, 'lookup', 'admin', 'group', '1')
        assert keys == {('group', '1', 'admin'), ('group', '1', 'member')}
        assert markers == {('doc', 'viewer')} and not excluded
        keys, markers, excluded = _lookup_all(pe, 'lookup_reverse', 'viewer', 'doc', '5')
        assert keys == {('doc', '5', 'viewer'), ('group', '1', 'admin'),
                        ('group', '1', 'member')}
        assert not markers and not excluded
    finally:
        pe.close()
