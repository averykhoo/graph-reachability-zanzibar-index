"""B6 repro: a poison (PathCountExceeded) log row blocks sync=True writes on the store id."""
import os, tempfile, warnings
warnings.simplefilter("ignore")
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store, PathCountExceeded
from zanzibar.store import rebuild_index

SCHEMA = """
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
"""
d = tempfile.mkdtemp()
engine = create_engine(f"sqlite:///{d}/b6.db")
SQLModel.metadata.create_all(engine)

def ev(label, fn):
    try:
        r = fn()
        print(f"{label}: OK -> {r!r}")
    except Exception as e:
        print(f"{label}: {type(e).__name__}: {str(e)[:160]}")

# 1. sync store: the overflowing tuple is refused at write, nothing is logged.
s0 = Store(Session(engine), "sync-only", schema=SCHEMA)
s0.add_tuple("user:alice", "member", "group:a0")
L = 32
def build(st, ):
    last = None
    for i in range(L):
        for up in ("a", "b"):
            for lo in (("a", "b") if i < L - 1 else ("a",)):
                last = (f"group:{up}{i}#member", "member", f"group:{lo}{i+1}")
                st.add_tuple(*last)
    return last
ev("sync store, overflowing tuple", lambda: build(s0))
ev("sync store, later unrelated add", lambda: s0.add_tuple("user:bob", "member", "group:zz"))

# 2. async store logs the poison row.
a = Store(Session(engine), "my-app", schema=SCHEMA, sync=False)
a.add_tuple("user:alice", "member", "group:a0")
build(a)
ev("async catch_up", lambda: a.catch_up())
print("index_stalled:", a.index_stalled, "lag:", a.lag())

# 3. sync instance on the same store id: every write hits the backlog.
s = Store(Session(engine), "my-app")
ev("sync add unrelated tuple", lambda: s.add_tuple("user:bob", "member", "group:zz"))
ev("sync remove existing tuple", lambda: s.remove_tuple("user:alice", "member", "group:a0"))
ev("sync remove of the poison tuple itself", lambda: s.remove_tuple("group:b31#member", "member", "group:a32"))
print("bob in zz (sync inst check):", s.check("user:bob", "member", "group:zz"))
print("bob in zz (set engine):", s.source.evaluator.check("member", "group", "zz", "...", "user", "bob") if hasattr(s.source, "evaluator") else "n/a")
# other store ids unaffected
ev("sync add on other store id", lambda: s0.add_tuple("user:carol", "member", "group:zz"))

# 4. recovery per docs
a.remove_tuple("group:b31#member", "member", "group:a32")
with Session(engine) as ops:
    ev("rebuild_index", lambda: type(rebuild_index(ops, "my-app")).__name__)
s.refresh()
ev("sync add after rebuild", lambda: s.add_tuple("user:bob", "member", "group:zz"))
print("bob in zz after rebuild:", s.check("user:bob", "member", "group:zz"))
