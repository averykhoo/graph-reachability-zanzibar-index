"""TK123 A16 + A53: two public paths that let the graph index or a set engine answer
differently from the store's set engine now REFUSE instead (release 0.0.5).

Review record: ``docs/tk123-api-review-2026-10-14.md`` rows A16 and A53.

* A16 -- ``advance_index(..., proc=None)`` on a schema with boolean (``and`` / ``but not``)
  relations applied the log to the leaf families only and never ran the delta processor's
  cascade, so the derived families were never maintained. Reachable with names from
  ``zanzibar.store.__all__`` alone (``ensure_cursor`` + ``open_graph_index`` give a
  cursor and a ``(widx, ruleset)``, but no processor). Review probe output, before the fix::

      advance_index(proc=None) applied 3 rows, no error
        graph check alice viewer doc:d -> False
        source (set engine) alice -> True

  Fix: ``store/apply.py::_require_proc_for_boolean_schema`` raises
  ``MissingDeltaProcessor`` when ``ruleset.compiled.plans`` is non-empty and ``proc`` is
  None. A pure-union schema still takes ``proc=None``.

* A53 -- a ``SetEngine`` opened on a store id a ``Store`` owns (it has a
  ``SchemaRecord``) answered under whatever schema it was GIVEN. With the store's
  ``but not banned`` dropped it returned a stale ALLOW. Review probe output, before::

      Store cs check (persisted BOOL schema): OK -> False
      SetEngine on cs id, persisted schema: OK -> False
      SetEngine on cs id, DIFFERENT schema (no but-not): OK -> True

  Fix: ``SetEngine.__init__`` reads the record's schema on a governed open and raises
  ``SchemaMismatch`` unless it is the same schema by the `TK136` rule (equal declared
  object-wildcard shapes, equal ``SchemaAST``), via
  ``setengine/engine.py::_assert_schema_matches_record``. ``SchemaMismatch`` moved to
  ``zanzibar.schema.errors`` so the set engine raises it without importing the
  composition layer; ``zanzibar.store.SchemaMismatch`` is the same class. A
  standalone store id (no record) is unchanged: it trusts the schema it is given.

SABOTAGE (2026-10-14, literal observed output). Runner: an anchored byte replace per
edit (anchor count asserted == 1), this module re-run, the file restored byte-for-byte and
its sha256 re-checked; ``git diff --stat src/`` was unchanged afterwards. The runner is
scratch; this list is the record.

- S1, the guard call in ``advance_index`` replaced by ``pass``::

      FAILED ...::test_a16_advance_index_without_proc_is_refused_on_a_boolean_schema
      E   Failed: DID NOT RAISE MissingDeltaProcessor
      1 failed, 9 passed

- S2, the guard's ``compiled.plans`` inverted to ``not compiled.plans``::

      FAILED ...::test_a16_advance_index_without_proc_is_refused_on_a_boolean_schema
      FAILED ...::test_a16_pure_union_schema_still_advances_without_a_proc
      2 failed, 8 passed

- S3, ``if record is not None:`` before ``_assert_schema_matches_record`` -> ``if False:``::

      FAILED ...::test_a53_dropping_but_not_on_a_governed_store_is_refused
      FAILED ...::test_a53_object_wildcard_shapes_must_match_too
      E   Failed: DID NOT RAISE SchemaMismatch
      2 failed, 8 passed

- S4, the AST compare weakened to text identity (``if stored_text != schema:``), i.e.
  dropping the `TK136` rule::

      FAILED ...::test_a53_matching_schema_reopens_and_answers_like_the_store
      E   zanzibar.schema.errors.SchemaMismatch: SetEngine on store 'cs': the schema passed
          here disagrees with the persisted schema of this store ...
      1 failed, 9 passed

- S5, the object-wildcard-shapes compare removed::

      FAILED ...::test_a53_object_wildcard_shapes_must_match_too
      1 failed, 9 passed

- S6, the AST compare removed (``if stored_ast != ast:`` -> ``if False:``)::

      FAILED ...::test_a53_dropping_but_not_on_a_governed_store_is_refused
      E   Failed: DID NOT RAISE SchemaMismatch
      1 failed, 9 passed

- S7, the raw probe's ``schema_text`` column misnamed ``schema_txt``::

      FAILED ...::test_a53_raw_probe_reads_the_real_schema_record_columns
      E   AttributeError: schema_text
      7 failed, 3 passed
"""
from __future__ import annotations

import warnings

import pytest
from sqlmodel import Session, SQLModel, create_engine

import zanzibar.store as cs
import zanzibar.schema as zschema
from zanzibar.store import Store, SchemaRecord
from zanzibar.graphindex.processor import DeltaProcessor
from zanzibar.setengine import SetEngine
from zanzibar.setengine import engine as engine_mod

BOOL = """
model
  schema 1.1
type user
type doc
  relations
    define banned: [user]
    define viewer: [user] but not banned
"""

UNION = """
model
  schema 1.1
type user
type group
  relations
    define member: [user]
type doc
  relations
    define viewer: [user, group#member]
"""


def _mem():
    e = create_engine('sqlite://')
    SQLModel.metadata.create_all(e)
    return e


def _logged_source(s, schema):
    """A bootstrapped source store 'src' written ONLY through public names."""
    cs.save_schema(s, 'src', schema)
    s.commit()
    return cs.TupleSource(s, 'src')


# --------------------------------------------------------------------------- A16


def _bool_source_with_rows(s):
    src = _logged_source(s, BOOL)
    src.add('...', 'user', 'alice', 'viewer', 'doc', 'd')
    src.add('...', 'user', 'bob', 'viewer', 'doc', 'd')
    src.add('...', 'user', 'bob', 'banned', 'doc', 'd')
    s.commit()
    return src


def test_a16_advance_index_without_proc_is_refused_on_a_boolean_schema():
    """The review's public-only repro: now a refusal naming the fix, and nothing moved."""
    with Session(_mem()) as s:
        _bool_source_with_rows(s)
        cursor = cs.ensure_cursor(s, 'src', 'src')
        widx, ruleset = cs.open_graph_index(s, 'src')
        assert ruleset.compiled is not None and ruleset.compiled.plans
        with pytest.raises(cs.MissingDeltaProcessor) as ei:
            cs.advance_index(s, cursor, widx, ruleset, None)
        msg = str(ei.value)
        assert 'DeltaProcessor' in msg and 'proc' in msg, msg
        assert cursor.applied_log_id == 0          # refused before anything was applied


def test_a16_missing_proc_is_a_value_error_exported_from_connectedstore():
    assert issubclass(cs.MissingDeltaProcessor, ValueError)
    assert 'MissingDeltaProcessor' in cs.__all__


def test_a16_control_with_the_delta_processor_agrees_with_the_set_engine():
    """The control from the review (v5): the same rows with the processor are correct."""
    with Session(_mem()) as s:
        src = _bool_source_with_rows(s)
        cursor = cs.ensure_cursor(s, 'src', 'src')
        widx, ruleset = cs.open_graph_index(s, 'src')
        n = cs.advance_index(s, cursor, widx, ruleset, DeltaProcessor(widx, ruleset.compiled))
        s.commit()
        assert n == 3
        for who, want in (('alice', True), ('bob', False)):
            assert widx.check('...', 'user', who, 'viewer', 'doc', 'd') is want
            assert src.check('...', 'user', who, 'viewer', 'doc', 'd') is want


def test_a16_pure_union_schema_still_advances_without_a_proc():
    """The guard is scoped to boolean schemas: a pure union never cascades."""
    with Session(_mem()) as s:
        src = _logged_source(s, UNION)
        src.add('...', 'user', 'alice', 'member', 'group', 'g')
        src.add('member', 'group', 'g', 'viewer', 'doc', 'd')
        s.commit()
        cursor = cs.ensure_cursor(s, 'src', 'src')
        widx, ruleset = cs.open_graph_index(s, 'src')
        assert ruleset.compiled is None or not ruleset.compiled.plans
        assert cs.advance_index(s, cursor, widx, ruleset, None) == 2
        s.commit()
        for who, want in (('alice', True), ('bob', False)):
            assert widx.check('...', 'user', who, 'viewer', 'doc', 'd') is want
            assert src.check('...', 'user', who, 'viewer', 'doc', 'd') is want


# --------------------------------------------------------------------------- A53

BOOL_REORDERED = """
model
  schema 1.1

type doc
  relations
    define viewer: [user] but not banned
    define banned: [user]
type user
"""


def _governed_store(e):
    with Session(e) as s:
        store = Store(s, 'cs', schema=BOOL)
        store.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd')
        store.add_tuple('...', 'user', 'alice', 'banned', 'doc', 'd')
        s.commit()


def test_a53_dropping_but_not_on_a_governed_store_is_refused():
    """The review's stale-ALLOW repro: the engine is refused, not answering True."""
    e = _mem()
    _governed_store(e)
    with Session(e) as s:
        assert Store(s, 'cs').check('...', 'user', 'alice', 'viewer', 'doc', 'd') is False
    with Session(e) as s:
        with pytest.raises(cs.SchemaMismatch) as ei:
            SetEngine(s, 'cs', BOOL.replace(' but not banned', ''))
        msg = str(ei.value)
        assert "'cs'" in msg and 'open_set_engine' in msg, msg


def test_a53_matching_schema_reopens_and_answers_like_the_store():
    """Identical text, and the same schema written differently (TK136: define-line and
    type-block order, blank lines), both open as before and read the store's answer."""
    e = _mem()
    _governed_store(e)
    for text in (BOOL, BOOL_REORDERED):
        assert text == BOOL or zschema.parse_schema_ast(text) == zschema.parse_schema_ast(BOOL)
        with Session(e) as s:
            se = SetEngine(s, 'cs', text)
            assert se.log_governed is True
            assert se.check('...', 'user', 'alice', 'viewer', 'doc', 'd') is False


def test_a53_object_wildcard_shapes_must_match_too():
    """Same text, different declared object-wildcard shapes: a different schema (the
    shapes are half of what both backends compile). A pure-union schema, since the graph
    refuses an object wildcard that feeds a boolean relation."""
    shapes = frozenset({('doc', 'viewer')})
    e = _mem()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')        # object wildcards are an unproven extension
        with Session(e) as s:
            Store(s, 'cs', schema=UNION, object_wildcard_shapes=shapes)
        with Session(e) as s:
            assert SetEngine(s, 'cs', UNION, object_wildcard_shapes=shapes).log_governed
        with Session(e) as s:
            with pytest.raises(cs.SchemaMismatch) as ei:
                SetEngine(s, 'cs', UNION)
        assert 'object_wildcard_shapes' in str(ei.value)


def test_a53_standalone_store_without_a_record_is_unchanged():
    """No SchemaRecord means nothing to compare: the engine trusts its given schema."""
    e = _mem()
    with Session(e) as s:
        se = SetEngine(s, 'solo', BOOL)
        se.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd')
        se.add_tuple('...', 'user', 'alice', 'banned', 'doc', 'd')
        s.commit()
    with Session(e) as s:
        se = SetEngine(s, 'solo', BOOL.replace(' but not banned', ''))
        assert se.log_governed is False
        assert se.check('...', 'user', 'alice', 'viewer', 'doc', 'd') is True


def test_a53_schema_mismatch_is_one_class_across_layers():
    """Moved to the shared layer, not duplicated: every import path is the same class,
    so an existing ``except zanzibar.store.SchemaMismatch`` still catches the set
    engine's refusal."""
    from zanzibar.store.schema_io import SchemaMismatch as via_io
    from zanzibar.schema.errors import SchemaMismatch as via_errors
    assert cs.SchemaMismatch is via_io is via_errors is zschema.SchemaMismatch
    assert issubclass(via_errors, ValueError)


def test_a53_raw_probe_reads_the_real_schema_record_columns():
    """The set engine reads the record through a raw table (it may not import the
    connected store); a renamed column would make every governed open fail, so pin the
    names to the model."""
    probe_cols = {c.name for c in engine_mod._SCHEMA_RECORD.c}
    model_cols = set(SchemaRecord.__table__.c.keys())
    assert probe_cols == {'store_id', 'schema_text', 'object_wildcard_shapes'}
    assert probe_cols <= model_cols
