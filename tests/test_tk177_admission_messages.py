"""TK177 (2026-10-30): a refused tuple is quoted the way the user wrote it, and the cycle
refusal says what to do instead.

Source: the 0.1.1 install trial (``docs/pypi-trial-0.1.1-2026-10-30.md``), F21 and the
message half of F17. ``add_tuple("robot:r", "viewer", "doc:1")`` was refused as
``tuple doc:1#viewer@robot:r#...`` (the graph side) or ``tuple robot:r#... viewer doc:1``
(the set engine); the cycle refusal named no rewrite. Both sides now use
``zanzibar.schema.syntax.tuple_text``.

SABOTAGE (2026-10-30, session; this module only, ``-p no:cacheprovider``, file restored
and checked). Literal tails, both RED:

- S1 ``tuple_text`` always appends ``#<predicate>``: ``rc=1 | 4 failed, 1 passed``
- S2 the cycle message's ``Instead,`` sentence removed: ``rc=1 | 2 failed, 3 passed``
"""
import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar import AdmissionRejected, Store
from zanzibar.schema import Entity, RelationalTriple, parse_openfga_schema
from zanzibar.schema.syntax import tuple_text

SCHEMA = ("type user\ntype robot\n"
          "type group\n  relations\n    define member: [user, group#member]\n"
          "type folder\n  relations\n    define parent: [folder]\n"
          "    define viewer: [user] or viewer from parent\n"
          "type doc\n  relations\n    define blocked: [user]\n    define viewer: [user] but not blocked\n")


@pytest.fixture
def store():
    eng = create_engine('sqlite://')
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        yield Store(s, 's', schema=SCHEMA)


def test_tuple_text_is_the_openfga_string_form():
    assert tuple_text('...', 'user', 'a', 'viewer', 'doc', '1') == 'user:a viewer doc:1'
    assert tuple_text(Ellipsis, 'user', 'a', 'viewer', 'doc', '1') == 'user:a viewer doc:1'
    assert tuple_text('member', 'group', 'g', 'viewer', 'doc', '1') == 'group:g#member viewer doc:1'


def test_store_refusal_quotes_the_users_tuple(store):
    with pytest.raises(AdmissionRejected) as ei:
        store.add_tuple('robot:r', 'viewer', 'doc:1')
    assert str(ei.value).startswith('tuple robot:r viewer doc:1 ')
    assert '#...' not in str(ei.value) and '@' not in str(ei.value)


def test_graph_side_refusal_quotes_the_users_tuple():
    rs = parse_openfga_schema(SCHEMA)
    triple = RelationalTriple(subject=Entity('robot', 'r'), relation='viewer', object=Entity('doc', '1'))
    with pytest.raises(AdmissionRejected) as ei:
        list(rs.apply(triple))   # apply is lazy
    assert str(ei.value).startswith('tuple robot:r viewer doc:1 ')
    assert '@' not in str(ei.value)


@pytest.mark.parametrize('args, inside', [
    (('folder:f', 'parent', 'folder:f'), 'folder:f'),
    (('group:g#member', 'member', 'group:g'), 'group:g'),
])
def test_cycle_refusal_names_the_way_out(store, args, inside):
    with pytest.raises(AdmissionRejected) as ei:
        store.add_tuple(*args)
    msg = str(ei.value)
    assert msg.startswith(f'tuple {args[0]} {args[1]} {args[2]} would create a cycle')
    assert f'{inside} would end up inside itself' in msg
    assert 'Instead, leave this tuple out, or remove the tuple that closes the loop' in msg
