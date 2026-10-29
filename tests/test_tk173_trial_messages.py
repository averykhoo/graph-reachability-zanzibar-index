"""TK173 (2026-10-30): the five CONFUSING / DOC GAP findings of the 0.1.0 install trial.

Source: ``docs/pypi-trial-0.1.0-2026-10-30.md`` (F7, F9, F12, F14, F22), re-run first-hand
against ``src/`` before the fix. Each message now says what to write instead:

* **F7** a trailing ``# comment``, ``[user: *]``, ``type us er`` and a ``but not`` chain name
  the rewrite; the ``but not`` hint no longer talks about 0.0.4.
* **F9** an old 0.0.x keyword (``s_type=``) is named, with its 0.1 name, instead of an arity
  error ("got 5"); "1 argument" is singular; the six-part form says to pass
  ``subject_predicate='...'``.
* **F12** ``ops=PySets()`` says to pass the object (it was "'SetOps' object is not callable").
* **F14** swapped ``or`` operands stay a ``SchemaMismatch`` (the compiled leaf numbering
  follows operand order; pinned as refused by ``tests/test_tk136_schema_reopen_semantic.py``),
  and the message now says operand order is what counts.
* **F22** no two docs pages share a SQLite file, so following two in one folder cannot hit
  ``SchemaMismatch`` on a shared ``perms.db``.

SABOTAGE (2026-10-30, session; this docstring is the tracked record). One asserted-unique
anchor per mutation (gitignored ``.scratch/tk173/sab.py``), this module only (10 tests),
``-p no:cacheprovider``, file restored and sha256-checked. Literal tails, every one RED:

- S1 trailing-comment hint keyed on ``'##'``: ``rc=1 | 1 failed, 9 passed``
- S2 ``[user: *]`` hint disabled: ``rc=1 | 1 failed, 9 passed``
- S3 ``type <name>`` hint dropped: ``rc=1 | 1 failed, 9 passed``
- S4 ``but not`` ``.instead`` back to the 0.0.4 history: ``rc=1 | 1 failed, 9 passed``
- S5 unknown-keyword check disabled: ``rc=1 | 1 failed, 9 passed``
- S6 ``subject_predicate='...'`` hint dropped: ``rc=1 | 1 failed, 9 passed``
- S7 ``SetOps.__call__`` renamed away: ``rc=1 | 2 failed, 8 passed``
- S8 ``explain_difference`` returns the bare ``type#relation``: ``rc=1 | 1 failed, 9 passed``
- S9 ``port-openfga.md`` back on ``perms.db``: ``rc=1 | 1 failed, 9 passed``
- S10 the ``subject_predicate`` hint without its ``in names`` guard (so ``lookup_reverse``
  got it too; found by re-reading the diff): ``rc=1 | 1 failed, 9 passed``
"""
import re
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar import SchemaError, SchemaMismatch, ShapeNoLongerAccepted, Store, parse_openfga_schema
from zanzibar.setengine import PySets, RoaringSets

ROOT = Path(__file__).resolve().parent.parent
_HEAD = "model\n  schema 1.1\ntype user\n"
_SCHEMA = (_HEAD + "type group\n  relations\n    define member: [user]\n"
           "type doc\n  relations\n    define editor: [user]\n"
           "    define viewer: [user, group#member] or editor\n")


@pytest.fixture
def store():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield Store(session, "a", schema=_SCHEMA)


# --------------------------------------------------------------------------- F7

@pytest.mark.parametrize("body, needle", [
    ("type doc\n  relations\n    define viewer: [user]  # people\n",
     "a comment must be on its own line"),
    ("type doc\n  relations\n    define viewer: [user: *]\n",
     "type:* with no spaces"),
    ("type us er\n", 'write "type <name>"'),
], ids=["trailing-comment", "spaced-wildcard", "two-word-type"])
def test_token_level_refusals_name_the_rewrite(body, needle):
    with pytest.raises(SchemaError) as ei:
        parse_openfga_schema(_HEAD + body)
    assert needle in str(ei.value)


def test_but_not_chain_hint_fits_the_chain():
    text = (_HEAD + "type doc\n  relations\n    define a: [user]\n    define b: [user]\n"
            "    define c: [user]\n    define v: a but not b but not c\n")
    with pytest.raises(ShapeNoLongerAccepted) as ei:
        parse_openfga_schema(text)
    assert "'(a but not b) but not c'" in str(ei.value)
    assert "'(a but not b) but not c'" in ei.value.instead
    assert "0.0.4" not in str(ei.value) + ei.value.instead


# --------------------------------------------------------------------------- F9

def test_old_keywords_are_named_with_their_new_names(store):
    with pytest.raises(TypeError) as ei:
        store.check(s_type="user", s_name="alice", relation="viewer", o_type="doc",
                    o_name="d1")
    msg = str(ei.value)
    assert "unexpected keyword arguments 'o_name', 'o_type', 's_name', 's_type'" in msg
    assert "s_type is now subject_type" in msg and "o_name is now object_name" in msg
    with pytest.raises(TypeError, match=r"unexpected keyword argument 'o_type' .*"
                                        r"o_type is now object_type"):
        store.lookup("user:alice", o_type="doc")
    with pytest.raises(TypeError, match=r"unexpected keyword argument 'bogus'; it takes"):
        store.check("user:alice", "viewer", "doc:d1", bogus=1)


def test_six_part_form_says_to_pass_subject_predicate(store):
    with pytest.raises(TypeError, match=r"pass subject_predicate='\.\.\.'"):
        store.check(subject_type="user", subject_name="alice", relation="viewer",
                    object_type="doc", object_name="d1")
    # lookup_reverse's long form has no subject_predicate, so no such hint there
    with pytest.raises(TypeError) as ei:
        store.lookup_reverse(relation="viewer", object_type="doc")
    assert "missing a required argument: 'object_name'" in str(ei.value)
    assert "subject_predicate" not in str(ei.value)


# --------------------------------------------------------------------------- F12

@pytest.mark.parametrize("ops, name", [(PySets, "PySets"), (RoaringSets, "RoaringSets")])
def test_calling_a_setops_says_pass_the_object(ops, name):
    with pytest.raises(TypeError, match=rf"pass ops={name}, without the parentheses"):
        ops()


# --------------------------------------------------------------------------- F14

def test_swapped_or_operands_say_operand_order_counts():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        Store(session, "a", schema=_SCHEMA)
        session.commit()
    swapped = _SCHEMA.replace("[user, group#member] or editor", "editor or [user, group#member]")
    with Session(engine) as session:
        with pytest.raises(SchemaMismatch) as ei:
            Store(session, "a", schema=swapped)
    assert "first at doc#viewer (its definition differs" in str(ei.value)
    assert "the operands of 'or' / 'and' / 'but not' may not" in str(ei.value)


# --------------------------------------------------------------------------- F22

def test_no_two_docs_pages_share_a_sqlite_file():
    """Sabotage (2026-10-30): with ``port-openfga.md`` back on ``perms.db`` -> red naming
    ``perms.db`` and both pages."""
    pages = [ROOT / "PYPI_README.md", *sorted((ROOT / "userdocs").rglob("*.md"))]
    users: dict[str, set[str]] = {}
    for page in pages:
        for name in set(re.findall(r"sqlite:///([A-Za-z0-9_.-]+\.db)", page.read_text(encoding="utf-8"))):
            users.setdefault(name, set()).add(page.relative_to(ROOT).as_posix())
    assert users, "no sqlite:/// file names found: the pattern no longer matches the docs"
    shared = {name: sorted(p) for name, p in users.items() if len(p) > 1}
    assert not shared, f"docs pages share a SQLite file: {shared}"
