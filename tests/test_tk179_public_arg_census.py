"""TK179 (2026-10-30): every public parameter refuses a wrong type before any SQL runs.

The 0.1.1 install trial found ``Store(sync=None)`` silently selecting async mode (F19,
``TK176``); the first census run (``docs/tk179-strict-public-args-plan-2026-10-30.md``) found
82 of 391 wrong-typed probes ACCEPTED silently and 122 refused only after SQL or with the
wrong exception, e.g. ``check("user:a", None, "doc:1")`` answering ``False``.

Two properties:

* **Completeness.** ``CENSUS`` names every parameter of every public callable of the user
  tier (``Store``, ``TupleSource``, ``SetEngine``, and the module functions below). A public
  method or parameter that is not in it fails ``test_census_covers_every_public_parameter``,
  so a new argument cannot ship without someone deciding what it accepts. ``EXEMPT`` holds
  the parameters left unprobed, each with its reason.
* **Refusal.** Every listed parameter, given each wrong value of its kind, raises
  ``TypeError`` or ``ValueError`` with ZERO SQL statements executed (a
  ``before_cursor_execute`` listener counts them on a fresh in-memory store per probe).

The graph-index classes (``WildcardIndex``, ``ReachabilityIndex``) are public to study, not to
drive (``userdocs/how-to/backends-direct.md``), so they are outside this census.

SABOTAGE (2026-10-30, session; one asserted-unique anchor per mutation, this module only,
``-p no:cacheprovider``, file restored and checked). Literal tails, every one RED:

- S1 ``tuplestr.require_parts`` read check made a no-op (``require_str`` -> ``pass``):
  ``rc=1 | 157 failed, 519 passed``
- S2 ``argcheck.require_bool`` disabled: ``rc=1 | 20 failed, 661 passed``
- S3 ``argcheck.require_session`` disabled: ``rc=1 | 27 failed, 654 passed``
- S4 the census entry for ``Store.catch_up(batch)`` deleted: ``rc=1 | 1 failed, 676 passed``
  (the completeness test names the missing parameter)
"""
from __future__ import annotations

import inspect

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

import zanzibar
from zanzibar import Store
from zanzibar.graphindex import prune_outbox
from zanzibar.schema.tuplestr import _LOOKUP_LONG, _LOOKUP_SHORT, _REVERSE_LONG, _REVERSE_SHORT, _TUPLE_LONG, _TUPLE_SHORT
from zanzibar.setengine import SetEngine
from zanzibar.store import TupleSource, build_index, open_set_engine, rebuild_index, save_schema

SCHEMA = ("model\n  schema 1.1\ntype user\ntype group\n  relations\n    define member: [user]\n"
          "type doc\n  relations\n    define viewer: [user, group#member]\n")


class _Thing:
    def __repr__(self) -> str:
        return '<object>'


# Wrong values per kind of parameter. None is wrong only where None is not a documented value.
BAD = {
    'str': [None, 0, b'x', ['x'], _Thing()],
    'str?': [0, b'x', ['x'], _Thing()],
    'bool': [None, 0, 1, 'true', _Thing()],
    'int?': [True, '3', 1.5, _Thing()],
    'int': [None, True, '3', 1.5, _Thing()],
    'session': [None, 'x', _Thing()],
    'ops': ['pysets', None, _Thing()],
    'schema': [5, ['x'], _Thing()],
    'shapes': ['doc', 5, _Thing(), [('doc', 5)]],
    'paranoia': [2.5, _Thing(), ['full']],
    'res': [None, 'x', 5, _Thing()],
    'ruleset': ['x', 5, _Thing()],
}

SIX = ['...', 'user', 'a', 'viewer', 'doc', '1']


def _store(s):
    return Store(s, 's')


def _engine(s):
    return SetEngine(s, 'se', SCHEMA)        # standalone: no Store owns 'se'


def _six(owner_fn, method, i):
    def build(s, bad):
        args = list(SIX)
        args[i] = bad
        target = owner_fn(s)
        return lambda: getattr(target, method)(*args)
    return build


def _short(owner_fn, method, i, base):
    def build(s, bad):
        args = list(base)
        args[i] = bad
        target = owner_fn(s)
        return lambda: getattr(target, method)(*args)
    return build


def _kw(owner_fn, method, base, name):
    def build(s, bad):
        target = owner_fn(s)
        return lambda: getattr(target, method)(*base, **{name: bad})
    return build


CENSUS: dict[str, dict[str, tuple[str, object]]] = {}


def _add(owner: str, param: str, kind: str, build) -> None:
    CENSUS.setdefault(owner, {})[param] = (kind, build)


# ---- Store ------------------------------------------------------------------------------
_add('Store.__init__', 'session', 'session', lambda s, b: (lambda: Store(b, 's')))
_add('Store.__init__', 'store_id', 'str', lambda s, b: (lambda: Store(s, b)))
_add('Store.__init__', 'schema', 'schema', lambda s, b: (lambda: Store(s, 's', schema=b)))
_add('Store.__init__', 'object_wildcard_shapes', 'shapes',
     lambda s, b: (lambda: Store(s, 's', object_wildcard_shapes=b)))
_add('Store.__init__', 'ops', 'ops', lambda s, b: (lambda: Store(s, 's', ops=b)))
_add('Store.__init__', 'sync', 'bool', lambda s, b: (lambda: Store(s, 's', sync=b)))
_add('Store.__init__', 'paranoia', 'paranoia', lambda s, b: (lambda: Store(s, 's', paranoia=b)))
_add('Store.adopt', 'session', 'session', lambda s, b: (lambda: Store.adopt(b, 'n', schema=SCHEMA)))
_add('Store.adopt', 'store_id', 'str', lambda s, b: (lambda: Store.adopt(s, b, schema=SCHEMA)))
_add('Store.adopt', 'schema', 'schema', lambda s, b: (lambda: Store.adopt(s, 'n', schema=b)))
_add('Store.adopt', 'object_wildcard_shapes', 'shapes',
     lambda s, b: (lambda: Store.adopt(s, 'n', schema=SCHEMA, object_wildcard_shapes=b)))
_add('Store.adopt', 'bulk', 'bool', lambda s, b: (lambda: Store.adopt(s, 'n', schema=SCHEMA, bulk=b)))
_add('Store.adopt', 'ops', 'ops', lambda s, b: (lambda: Store.adopt(s, 'n', schema=SCHEMA, ops=b)))
_add('Store.adopt', 'sync', 'bool', lambda s, b: (lambda: Store.adopt(s, 'n', schema=SCHEMA, sync=b)))
_add('Store.adopt', 'paranoia', 'paranoia',
     lambda s, b: (lambda: Store.adopt(s, 'n', schema=SCHEMA, paranoia=b)))
for _m in ('add_tuple', 'remove_tuple', 'check'):
    for _i, _p in enumerate(_TUPLE_SHORT):
        _add(f'Store.{_m}', _p, 'str', _short(_store, _m, _i, ['user:a', 'viewer', 'doc:1']))
    for _i, _p in enumerate(_TUPLE_LONG):
        _add(f'Store.{_m}', _p, 'str', _six(_store, _m, _i))
_add('Store.check', 'at_least', 'int?', _kw(_store, 'check', ['user:a', 'viewer', 'doc:1'], 'at_least'))
for _i, _p in enumerate(_LOOKUP_LONG):
    _add('Store.lookup', _p, 'str', _short(_store, 'lookup', _i, SIX[:3]))
_add('Store.lookup', 'user', 'str', _short(_store, 'lookup', 0, ['user:a']))
for _p in ('object_type', 'relation'):
    _add('Store.lookup', _p, 'str?', _kw(_store, 'lookup', ['user:a'], _p))
_add('Store.lookup', 'at_least', 'int?', _kw(_store, 'lookup', ['user:a'], 'at_least'))
for _i, _p in enumerate(_REVERSE_SHORT):
    _add('Store.lookup_reverse', _p, 'str', _short(_store, 'lookup_reverse', _i, ['viewer', 'doc:1']))
for _i, _p in enumerate(_REVERSE_LONG):
    _add('Store.lookup_reverse', _p, 'str', _short(_store, 'lookup_reverse', _i, ['viewer', 'doc', '1']))
for _p in ('subject_type', 'subject_predicate'):
    _add('Store.lookup_reverse', _p, 'str?', _kw(_store, 'lookup_reverse', ['viewer', 'doc:1'], _p))
_add('Store.lookup_reverse', 'at_least', 'int?', _kw(_store, 'lookup_reverse', ['viewer', 'doc:1'], 'at_least'))
for _i, _p in enumerate(_REVERSE_SHORT):
    _add('Store.expand', _p, 'str', _short(_store, 'expand', _i, ['viewer', 'doc:1']))
for _i, _p in enumerate(_REVERSE_LONG):
    _add('Store.expand', _p, 'str', _short(_store, 'expand', _i, ['viewer', 'doc', '1']))
_add('Store.expand', 'at_least', 'int?', _kw(_store, 'expand', ['viewer', 'doc:1'], 'at_least'))
_add('Store.catch_up', 'batch', 'int?', _kw(_store, 'catch_up', [], 'batch'))
_add('Store.result_keys', 'res', 'res', _short(_store, 'result_keys', 0, [None]))
_add('Store.excluded_keys', 'res', 'res', _short(_store, 'excluded_keys', 0, [None]))
for _m in ('lag', 'refresh', 'watermark'):
    CENSUS.setdefault(f'Store.{_m}', {})

# ---- TupleSource --------------------------------------------------------------------------
def _source(s):
    return TupleSource(s, 's')


_add('TupleSource.__init__', 'session', 'session', lambda s, b: (lambda: TupleSource(b, 's')))
_add('TupleSource.__init__', 'store_id', 'str', lambda s, b: (lambda: TupleSource(s, b)))
_add('TupleSource.__init__', 'ops', 'ops', lambda s, b: (lambda: TupleSource(s, 's', ops=b)))
_add('TupleSource.__init__', 'ruleset', 'ruleset', lambda s, b: (lambda: TupleSource(s, 's', ruleset=b)))
for _m in ('add', 'remove', 'check'):
    for _i, _p in enumerate(_TUPLE_SHORT):
        _add(f'TupleSource.{_m}', _p, 'str', _short(_source, _m, _i, ['user:a', 'viewer', 'doc:1']))
    for _i, _p in enumerate(_TUPLE_LONG):
        _add(f'TupleSource.{_m}', _p, 'str', _six(_source, _m, _i))
_add('TupleSource.check', 'at_least', 'int?', _kw(_source, 'check', ['user:a', 'viewer', 'doc:1'], 'at_least'))
_add('TupleSource.catch_up_evaluator', 'batch', 'int?', _kw(_source, 'catch_up_evaluator', [], 'batch'))
for _m in ('evaluator_lag', 'pop_pending_rows', 'refresh_evaluator', 'undo_last_admission', 'watermark'):
    CENSUS.setdefault(f'TupleSource.{_m}', {})

# ---- SetEngine ----------------------------------------------------------------------------
_add('SetEngine.__init__', 'session', 'session', lambda s, b: (lambda: SetEngine(b, 'se', SCHEMA)))
_add('SetEngine.__init__', 'store_id', 'str', lambda s, b: (lambda: SetEngine(s, b, SCHEMA)))
_add('SetEngine.__init__', 'schema', 'str?', lambda s, b: (lambda: SetEngine(s, 'se', b)))
_add('SetEngine.__init__', 'object_wildcard_shapes', 'shapes',
     lambda s, b: (lambda: SetEngine(s, 'se', SCHEMA, object_wildcard_shapes=b)))
_add('SetEngine.__init__', 'ops', 'ops', lambda s, b: (lambda: SetEngine(s, 'se', SCHEMA, ops=b)))
_add('SetEngine.__init__', 'ruleset', 'ruleset', lambda s, b: (lambda: SetEngine(s, 'se', SCHEMA, ruleset=b)))
for _m in ('add_tuple', 'remove_tuple', 'check'):
    for _i, _p in enumerate(_TUPLE_LONG):
        _add(f'SetEngine.{_m}', _p, 'str', _six(_engine, _m, _i))
for _i, _p in enumerate(_LOOKUP_LONG):
    _add('SetEngine.lookup', _p, 'str', _short(_engine, 'lookup', _i, SIX[:3]))
for _i, _p in enumerate(_REVERSE_LONG):
    _add('SetEngine.lookup_reverse', _p, 'str', _short(_engine, 'lookup_reverse', _i, ['viewer', 'doc', '1']))
for _i, _p in enumerate(('relation', 'o_type', 'o_name')):
    _add('SetEngine.expand', _p, 'str', _short(_engine, 'expand', _i, ['viewer', 'doc', '1']))
_add('SetEngine.result_keys', 'res', 'res', _short(_engine, 'result_keys', 0, [None]))
_add('SetEngine.excluded_keys', 'res', 'res', _short(_engine, 'excluded_keys', 0, [None]))
CENSUS.setdefault('SetEngine.rebuild', {})

# ---- module functions ----------------------------------------------------------------------
_add('parse_openfga_schema', 'schema', 'str', lambda s, b: (lambda: zanzibar.parse_openfga_schema(b)))
_add('parse_openfga_schema', 'object_wildcard_shapes', 'shapes',
     lambda s, b: (lambda: zanzibar.parse_openfga_schema(SCHEMA, b)))
_add('parse_openfga_schema', 'enable_boolean', 'bool',
     lambda s, b: (lambda: zanzibar.parse_openfga_schema(SCHEMA, enable_boolean=b)))
for _fn in (build_index, rebuild_index):
    _add(_fn.__name__, 'session', 'session', lambda s, b, f=_fn: (lambda: f(b, 's')))
    _add(_fn.__name__, 'source_store_id', 'str', lambda s, b, f=_fn: (lambda: f(s, b)))
    _add(_fn.__name__, 'index_store_id', 'str?', lambda s, b, f=_fn: (lambda: f(s, 's', index_store_id=b)))
    _add(_fn.__name__, 'bulk', 'bool', lambda s, b, f=_fn: (lambda: f(s, 's', bulk=b)))
_add('save_schema', 'session', 'session', lambda s, b: (lambda: save_schema(b, 'n', SCHEMA)))
_add('save_schema', 'store_id', 'str', lambda s, b: (lambda: save_schema(s, b, SCHEMA)))
_add('save_schema', 'schema_text', 'str', lambda s, b: (lambda: save_schema(s, 'n', b)))
_add('save_schema', 'object_wildcard_shapes', 'shapes', lambda s, b: (lambda: save_schema(s, 'n', SCHEMA, b)))
_add('open_set_engine', 'session', 'session', lambda s, b: (lambda: open_set_engine(b, 's')))
_add('open_set_engine', 'store_id', 'str', lambda s, b: (lambda: open_set_engine(s, b)))
_add('open_set_engine', 'ops', 'ops', lambda s, b: (lambda: open_set_engine(s, 's', ops=b)))
_add('open_set_engine', 'ruleset', 'ruleset', lambda s, b: (lambda: open_set_engine(s, 's', ruleset=b)))
_add('prune_outbox', 'session', 'session', lambda s, b: (lambda: prune_outbox(b, 's', 0)))
_add('prune_outbox', 'store_id', 'str', lambda s, b: (lambda: prune_outbox(s, b, 0)))
_add('prune_outbox', 'before_watermark', 'int', lambda s, b: (lambda: prune_outbox(s, 's', b)))

# On a READ, None as the subject predicate is documented to mean the bare subject
# (userdocs/reference/tuple-strings.md, "Writes are strict, reads are lenient").
for _owner in ('Store.check', 'Store.lookup', 'TupleSource.check', 'SetEngine.check', 'SetEngine.lookup'):
    _kind, _build = CENSUS[_owner]['subject_predicate']
    CENSUS[_owner]['subject_predicate'] = ('str?', _build)

# Public parameters deliberately NOT probed, with the reason.
EXEMPT = {
    ('SetEngine.expand', 'memo'): 'the recursion accumulator; callers leave it None',
    ('SetEngine.filter_result', '*'): 'a result filter over a SetLookupResult; checked by shape_filter',
    ('SetEngine.population', '*'): 'a shape lookup over interned ids, no SQL; internal to readers',
    ('SetEngine.apply_logged', '*'): 'the log-replay entry the Store drives with validated rows',
}

TARGETS = {'Store': Store, 'TupleSource': TupleSource, 'SetEngine': SetEngine}
FUNCTIONS = (zanzibar.parse_openfga_schema, build_index, rebuild_index, save_schema,
             open_set_engine, prune_outbox)
# *args methods: their parameters are the names of their call forms.
FORMS = {
    'add_tuple': _TUPLE_SHORT + _TUPLE_LONG, 'remove_tuple': _TUPLE_SHORT + _TUPLE_LONG,
    'check': _TUPLE_SHORT + _TUPLE_LONG, 'add': _TUPLE_SHORT + _TUPLE_LONG,
    'remove': _TUPLE_SHORT + _TUPLE_LONG, 'lookup': _LOOKUP_SHORT + _LOOKUP_LONG,
    'lookup_reverse': _REVERSE_SHORT + _REVERSE_LONG, 'expand': _REVERSE_SHORT + _REVERSE_LONG,
}


def _public_parameters() -> set[tuple[str, str]]:
    found = set()
    for cname, cls in TARGETS.items():
        for mname, member in vars(cls).items():
            if mname.startswith('_') and mname != '__init__':
                continue
            fn = member.__func__ if isinstance(member, (classmethod, staticmethod)) else member
            if isinstance(fn, property) or not callable(fn):
                continue
            label = f'{cname}.{mname}'
            params = [p for p in inspect.signature(fn).parameters.values()
                      if p.name not in ('self', 'cls')]
            names = set()
            for p in params:
                if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                    names |= set(FORMS[mname])
                else:
                    names.add(p.name)
            found.add((label, '#'))                     # the callable itself
            found |= {(label, n) for n in names}
    for fn in FUNCTIONS:
        found.add((fn.__name__, '#'))
        found |= {(fn.__name__, n) for n in inspect.signature(fn).parameters}
    return found


def test_census_covers_every_public_parameter():
    listed = {(o, '#') for o in CENSUS} | {(o, p) for o, ps in CENSUS.items() for p in ps}
    exempt_owners = {o for (o, p) in EXEMPT if p == '*'}
    listed |= set(EXEMPT) | {(o, '#') for o in exempt_owners}
    missing = sorted(k for k in _public_parameters()
                     if k not in listed and k[0] not in exempt_owners)
    assert not missing, (
        'public parameters with no census entry -- decide what each accepts, add it to '
        f'CENSUS (or to EXEMPT with a reason): {missing}')


def _fresh():
    eng = create_engine('sqlite://')
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        st = Store(s, 's', schema=SCHEMA)
        st.add_tuple('user:a', 'viewer', 'doc:1')
        s.commit()
    statements = []
    event.listen(eng, 'before_cursor_execute', lambda *a, **k: statements.append(a[2]))
    return eng, statements


CASES = [(owner, param, kind, build, bad)
         for owner, params in CENSUS.items()
         for param, (kind, build) in params.items()
         for bad in BAD[kind]]


@pytest.mark.parametrize('owner, param, kind, build, bad', CASES,
                         ids=[f'{o}-{p}-{b!r}' for o, p, _k, _b, b in CASES])
def test_wrong_type_is_refused_before_any_sql(owner, param, kind, build, bad):
    eng, statements = _fresh()
    with Session(eng) as s:
        call = build(s, bad)
        statements.clear()
        with pytest.raises((TypeError, ValueError)):
            call()
        assert statements == [], f'{owner}({param}={bad!r}) refused only after SQL ran'
