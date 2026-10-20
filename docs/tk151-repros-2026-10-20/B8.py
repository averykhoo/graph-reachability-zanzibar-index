"""Repro for B8: parse_user leniency and lookup-vs-check refusal asymmetry."""
import warnings
from sqlmodel import SQLModel, Session, create_engine
from zanzibar.store import Store
from zanzibar.schema.tuplestr import parse_user
import zanzibar
print('zanzibar from', zanzibar.__file__)


def run(label, fn):
    try:
        r = fn()
        print(f'{label}: OK -> {r!r}')
    except Exception as e:  # noqa: BLE001
        print(f'{label}: {type(e).__name__}: {e}')


print('--- parse_user ---')
for s in ['user:a#b:c', 'user:a#b c', 'user:a#', 'user:a#...', 'user:a#b#c', 'user::a', 'user:a:b']:
    run(f'parse_user({s!r})', lambda s=s: parse_user(s))

SCHEMA = """
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define viewer: [user, group#member]
"""
engine = create_engine('sqlite://')
SQLModel.metadata.create_all(engine)
with Session(engine) as session:
    store = Store(session, 'b8', schema=SCHEMA)
    store.add_tuple('user:alice', 'member', 'group:g')
    store.add_tuple('group:g#member', 'viewer', 'doc:d1')
    print('--- short form, "#..." ---')
    run('check("group:g#...", "viewer", "doc:d1")', lambda: store.check('group:g#...', 'viewer', 'doc:d1'))
    run('lookup("group:g#...")', lambda: store.lookup('group:g#...'))
    print('--- long form, bare group subject ---')
    run('check("...","group","g","viewer","doc","d1")', lambda: store.check('...', 'group', 'g', 'viewer', 'doc', 'd1'))
    run('lookup("...","group","g")', lambda: store.lookup('...', 'group', 'g'))
    run('lookup("group:g")', lambda: store.lookup('group:g'))
    print('--- malformed predicate via short form "b:c" ---')
    run('check("group:g#b:c", "viewer", "doc:d1")', lambda: store.check('group:g#b:c', 'viewer', 'doc:d1'))
    run('lookup("group:g#b:c")', lambda: store.lookup('group:g#b:c'))
    run('add_tuple("group:g#b:c","viewer","doc:d1")', lambda: store.add_tuple('group:g#b:c', 'viewer', 'doc:d1'))
    print('--- undeclared predicate ---')
    run('check("group:g#nope", "viewer", "doc:d1")', lambda: store.check('group:g#nope', 'viewer', 'doc:d1'))
    run('lookup("group:g#nope")', lambda: store.lookup('group:g#nope'))
    print('--- control: valid userset ---')
    run('check("group:g#member","viewer","doc:d1")', lambda: store.check('group:g#member', 'viewer', 'doc:d1'))
    run('lookup("group:g#member")', lambda: store.lookup('group:g#member'))
    print('--- set engine directly ---')
    src = store.source
    run('source.check("...","group","g","viewer","doc","d1")', lambda: src.check('...', 'group', 'g', 'viewer', 'doc', 'd1'))
    run('source.check("b:c","group","g","viewer","doc","d1")', lambda: src.check('b:c', 'group', 'g', 'viewer', 'doc', 'd1'))
    run('widx.check(...,"group","g","viewer","doc","d1")', lambda: store.widx.check(..., 'group', 'g', 'viewer', 'doc', 'd1'))
