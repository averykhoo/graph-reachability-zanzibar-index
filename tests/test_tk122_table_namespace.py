"""TK122 (2026-10-07): the library's tables live in a `zanzibar_` namespace, and a clash
with a consumer's own table is LOUD.

Before TK122 the ten tables had generic names (`store`, `node`, `edge`, ...) on SQLModel's
default metadata, and every one set `extend_existing=True`. Observed 2026-10-07 against an
installed wheel: an application that declared its own `node` table and THEN imported
`zanzibar.graphindex` got no error, and its table silently gained our columns
(`['id', 'label', 'store_id', 'predicate', 'type', 'name', 'wildcard', 'implicit',
'reference_count']`). Map: `docs/pypi-readiness-2026-10-07.md` sec 2 B2.

The clash tests run in a SUBPROCESS: SQLModel's metadata is process-global, so declaring a
colliding table in this process would poison every later test in the tile.

Sabotage evidence (2026-10-07, TK122), each mutation applied alone and the bytes restored:

    S1 re-add {'extend_existing': True} on Node only -> 1 failed, 5 passed
       (test_a_consumer_table_declared_first_makes_our_import_fail_loudly[zanzibar_node])
    S2 un-prefix relation_tuple's __tablename__       -> 2 failed, 4 passed
       (test_the_library_declares_exactly_ten_tables,
        test_every_table_and_named_constraint_is_prefixed)
    S3 un-prefix one explicit Index name (tuple_log)  -> 1 failed, 5 passed
       (test_every_table_and_named_constraint_is_prefixed)
"""
import inspect
import os
import subprocess
import sys
import textwrap

import pytest
from sqlmodel import SQLModel, UniqueConstraint

import zanzibar.connectedstore.models as cs_models
import zanzibar.graphindex.models as gi_models
import zanzibar.setengine.models as se_models

PREFIX = "zanzibar_"
MODULES = (gi_models, se_models, cs_models)


def _library_tables():
    out = []
    for mod in MODULES:
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if (obj.__module__ == mod.__name__ and issubclass(obj, SQLModel)
                    and hasattr(obj, "__table__")):
                out.append(obj.__table__)
    return out


def test_the_library_declares_exactly_ten_tables():
    """A count pin, so a new model cannot slip past the namespace checks below by
    living in a module this file does not walk."""
    names = sorted(t.name for t in _library_tables())
    assert len(names) == 10, names
    registered = {n for n in SQLModel.metadata.tables if n.startswith(PREFIX)}
    assert registered == set(names)


def test_every_table_and_named_constraint_is_prefixed():
    for t in _library_tables():
        assert t.name.startswith(PREFIX), t.name
        # PK/FK constraints are unnamed (the database names them); every NAMED one is a
        # UniqueConstraint, and those names are global per schema on PostgreSQL.
        for c in t.constraints:
            if isinstance(c, UniqueConstraint):
                assert str(c.name).startswith(PREFIX), (t.name, c.name)
        for ix in t.indexes:
            assert ix.name.startswith("ix_" + PREFIX), (t.name, ix.name)
        for fk in t.foreign_keys:
            assert fk.target_fullname.startswith(PREFIX), (t.name, fk.target_fullname)


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)],
                          capture_output=True, text=True, env=os.environ.copy(),
                          timeout=120)


@pytest.mark.parametrize("table", ["zanzibar_node", "zanzibar_store", "zanzibar_tuple_log"])
def test_a_consumer_table_declared_first_makes_our_import_fail_loudly(table):
    """The direction that USED to merge silently: consumer first, library second.
    Without `extend_existing` SQLAlchemy refuses the second declaration."""
    r = _run(f"""
        from sqlmodel import SQLModel, Field
        class Mine(SQLModel, table=True):
            __tablename__ = {table!r}
            id: int | None = Field(default=None, primary_key=True)
            label: str
        try:
            import zanzibar.graphindex, zanzibar.connectedstore
        except Exception as e:
            print("RAISED", type(e).__name__)
        else:
            print("MERGED", [c.name for c in SQLModel.metadata.tables[{table!r}].columns])
        """)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "RAISED InvalidRequestError", r.stdout + r.stderr


def test_a_consumer_table_with_a_generic_name_is_left_alone():
    """The common case: the consumer has a `node` table. It must keep exactly its own
    columns, and both tables must coexist."""
    r = _run("""
        from sqlmodel import SQLModel, Field
        class Node(SQLModel, table=True):
            __tablename__ = "node"
            id: int | None = Field(default=None, primary_key=True)
            label: str
        import zanzibar.graphindex
        print(sorted(c.name for c in SQLModel.metadata.tables["node"].columns))
        print("zanzibar_node" in SQLModel.metadata.tables)
        """)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split("\n")[:2] == ["['id', 'label']", "True"], r.stdout
