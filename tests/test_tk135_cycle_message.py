"""TK135: the derived-cycle refusal names only the cycle and says what to write instead.

The 0.0.3 install trial (`docs/pypi-trial-0.0.3-2026-10-08.md` probe10) hit
``CyclicDerivedDependency`` on a folder hierarchy with a per-folder block. The message cited
"boolean spec §1.9", which a PyPI user cannot see, gave no alternative, and listed
``('doc', 'secret_viewer'), ('doc', 'viewer')`` beside the real cycle ``('folder', 'viewer')``:
`boolean.py::_stratify` reported every relation Kahn could not place, and that includes each
relation DOWNSTREAM of the cycle. `_cycle_members` keeps only the strongly connected part.

SABOTAGE (2026-10-13, literal output): `_stratify` reverted to
``cyclic = sorted(k for k, d in indeg.items() if d > 0)``, file restored and sha256-checked::

    FAILED tests/test_tk135_cycle_message.py::test_the_cycle_list_names_only_relations_on_the_cycle
    FAILED tests/test_tk135_cycle_message.py::test_two_disjoint_cycles_are_both_named_and_nothing_else
    2 failed, 3 passed in 0.37s
"""
from __future__ import annotations

import ast
import re

import pytest

from zanzibar.schema import CyclicDerivedDependency, parse_openfga_schema

HEAD = 'model\n  schema 1.1\ntype user\n'

#: The trial's shape: folder#viewer recurses through `but not`; doc#viewer only DEPENDS on it.
FOLDER_CYCLE = HEAD + """type folder
  relations
    define parent: [folder]
    define blocked: [user]
    define viewer: ([user] or viewer from parent) but not blocked
type doc
  relations
    define parent: [folder]
    define banned: [user]
    define viewer: viewer from parent but not banned
"""

#: Two independent cycles plus a relation downstream of both.
TWO_CYCLES = HEAD + """type folder
  relations
    define parent: [folder]
    define blocked: [user]
    define viewer: ([user] or viewer from parent) but not blocked
    define editor: ([user] or editor from parent) but not blocked
    define both: viewer and editor
"""

#: The rewrite the message recommends; it must parse in the graph index.
REWRITE = HEAD + """type folder
  relations
    define parent: [folder]
    define blocked: [user]
    define viewer_base: [user] or viewer_base from parent
    define viewer: viewer_base but not blocked
"""


def _cycle(text):
    with pytest.raises(CyclicDerivedDependency) as info:
        parse_openfga_schema(text)
    listed = re.search(r'dependency cycle: (\[.*?\])\.', str(info.value))
    assert listed, str(info.value)
    return ast.literal_eval(listed.group(1)), str(info.value)


def test_the_cycle_list_names_only_relations_on_the_cycle():
    cycle, _ = _cycle(FOLDER_CYCLE)
    assert cycle == [('folder', 'viewer')]


def test_two_disjoint_cycles_are_both_named_and_nothing_else():
    cycle, _ = _cycle(TWO_CYCLES)
    assert cycle == [('folder', 'editor'), ('folder', 'viewer')]


def test_the_message_says_why_and_instead_without_citing_a_repo_spec():
    _, message = _cycle(FOLDER_CYCLE)
    assert 'spec' not in message, message
    assert 'SetEngine on its own accepts it' in message
    assert 'Instead, recurse on a plain relation' in message
    assert 'NOT the same schema' in message


def test_the_recommended_rewrite_parses():
    assert ('folder', 'viewer') in parse_openfga_schema(REWRITE).compiled.plans


def test_still_a_value_error_for_existing_callers():
    with pytest.raises(ValueError, match='dependency cycle'):
        parse_openfga_schema(FOLDER_CYCLE)
