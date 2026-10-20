"""B1 repro: a post-commit InvariantViolation (paranoia='full') as seen by a Store caller.

Sabotage instrument: wrap zanzibar.graphindex.invariants.check_invariants so it raises
ONLY when called on a session other than the Store's own (the post-commit pass runs in a
fresh Session on the same bind; the pre-commit pass runs on the Store's session).
"""
import os, tempfile, traceback
os.chdir(tempfile.mkdtemp())
import sqlalchemy
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store, InvariantViolation
import zanzibar.graphindex.invariants as inv

SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
"""
print("sqlalchemy", sqlalchemy.__version__)
engine = create_engine("sqlite:///b1.db")
SQLModel.metadata.create_all(engine)
real = inv.check_invariants
st = Store(Session(engine), "s", schema=SCHEMA, paranoia="full")
st.add_tuple("user:a", "viewer", "doc:1")

def fake(sess, store_id, *a, **k):
    if sess is not st.session:
        raise InvariantViolation("SABOTAGE post-commit")
    return real(sess, store_id, *a, **k)

inv.check_invariants = fake
try:
    st.add_tuple("user:b", "viewer", "doc:1")
    print("no exception")
except BaseException as e:
    print("caller type:", type(e).__module__ + "." + type(e).__name__)
    print("caller msg :", str(e).splitlines()[0])
    print("isinstance InvariantViolation:", isinstance(e, InvariantViolation))
    print("__cause__  :", repr(e.__cause__))
    print("__context__:", type(e.__context__).__name__, "|", e.__context__)
    print("--- innermost frames of caller exception ---")
    print("".join(traceback.format_tb(e.__traceback__)[-3:]))
finally:
    inv.check_invariants = real

print("session state: in_transaction =", st.session.in_transaction(),
      "| _transaction._state =", getattr(st.session._transaction, "_state", None))
for label, fn in (("check b", lambda: st.check("user:b", "viewer", "doc:1")),
                  ("add c", lambda: st.add_tuple("user:c", "viewer", "doc:1")),
                  ("refresh", lambda: st.refresh())):
    try:
        print(f"{label} -> {fn()!r}")
    except BaseException as e:
        print(f"{label} RAISED {type(e).__name__}: {str(e).splitlines()[0]}")

fresh = Store(Session(engine), "s")
print("fresh Store sees b:", fresh.check("user:b", "viewer", "doc:1"),
      "| a:", fresh.check("user:a", "viewer", "doc:1"))

# does session.close() revive the original Store object?
try:
    st.session.close()
    print("after session.close(): check b ->", st.check("user:b", "viewer", "doc:1"))
    print("after session.close(): add c ->", st.add_tuple("user:c", "viewer", "doc:1"))
except BaseException as e:
    print("after session.close() RAISED", type(e).__name__, str(e).splitlines()[0])

# control: same instrument, but the store's own session raises (pre-commit) -> fail-closed
st2 = Store(Session(engine), "s2", schema=SCHEMA, paranoia="full")
def fake_pre(sess, store_id, *a, **k):
    if sess is st2.session:
        raise InvariantViolation("SABOTAGE pre-commit")
    return real(sess, store_id, *a, **k)
inv.check_invariants = fake_pre
try:
    st2.add_tuple("user:b", "viewer", "doc:1")
except BaseException as e:
    print("control pre-commit caller type:", type(e).__name__, "|", str(e).splitlines()[0])
finally:
    inv.check_invariants = real
print("control: b stored?", Store(Session(engine), "s2").check("user:b", "viewer", "doc:1"),
      "| store usable, add c ->", st2.add_tuple("user:c", "viewer", "doc:1"))
