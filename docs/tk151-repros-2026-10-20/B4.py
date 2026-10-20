"""Repro B4: a freshness token from ANOTHER store, at/below this store's cursor,
is accepted silently by check/lookup/lookup_reverse/expand (at_least=)."""
import os, tempfile, warnings
from sqlmodel import SQLModel, Session, create_engine
from zanzibar.store import Store
import zanzibar

print("zanzibar from:", zanzibar.__file__)
SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
"""
db = os.path.join(tempfile.mkdtemp(), "b4.db")
engine = create_engine(f"sqlite:///{db}")
SQLModel.metadata.create_all(engine)

def attempt(label, fn):
    try:
        print(f"{label}: returned {fn()!r}")
    except Exception as e:
        print(f"{label}: raised {type(e).__name__}: {e}")

with Session(engine) as sa, Session(engine) as sb:
    a = Store(sa, "store-a", schema=SCHEMA)
    b = Store(sb, "store-b", schema=SCHEMA)
    t_a = a.add_tuple("user:carol", "viewer", "doc:d9")       # token issued by store-a
    t_b1 = b.add_tuple("user:bob", "viewer", "doc:d1")
    t_b2 = b.add_tuple("user:dave", "viewer", "doc:d2")
    print("tokens: t_a =", t_a, " t_b1 =", t_b1, " t_b2 =", t_b2)
    print("b.cursor.applied_log_id =", b.cursor.applied_log_id)

    print("--- CASE 1: foreign token t_a <= b's cursor (claimed silent accept)")
    attempt("b.check(carol viewer d9, at_least=t_a)",
            lambda: b.check("user:carol", "viewer", "doc:d9", at_least=t_a))
    attempt("b.check(bob viewer d1, at_least=t_a)",
            lambda: b.check("user:bob", "viewer", "doc:d1", at_least=t_a))
    attempt("b.lookup(carol, at_least=t_a) keys",
            lambda: b.result_keys(b.lookup("user:carol", at_least=t_a)))
    attempt("b.lookup_reverse(viewer, doc:d1, at_least=t_a) keys",
            lambda: b.result_keys(b.lookup_reverse("viewer", "doc:d1", at_least=t_a)))
    attempt("b.expand(viewer, doc:d1, at_least=t_a) keys",
            lambda: sorted(b.expand("viewer", "doc:d1", at_least=t_a).keys))

    print("--- CASE 2 (control): foreign token ABOVE b's cursor")
    t_a2 = a.add_tuple("user:erin", "viewer", "doc:d9")
    print("t_a2 =", t_a2, " b.cursor.applied_log_id =", b.cursor.applied_log_id)
    attempt("b.check(carol viewer d9, at_least=t_a2)",
            lambda: b.check("user:carol", "viewer", "doc:d9", at_least=t_a2))
    attempt("b.lookup(carol, at_least=t_a2)",
            lambda: b.lookup("user:carol", at_least=t_a2))

    print("--- CASE 3: same-store control, b's own token")
    attempt("b.check(dave viewer d2, at_least=t_b2)",
            lambda: b.check("user:dave", "viewer", "doc:d2", at_least=t_b2))

    print("--- CASE 4: async store-c with a backlog; foreign token below its cursor")
    sc = Session(engine)
    cw = Store(sc, "store-c", schema=SCHEMA, sync=False)
    t_c1 = cw.add_tuple("user:frank", "viewer", "doc:d3")
    cw.catch_up()
    t_c2 = cw.add_tuple("user:gina", "viewer", "doc:d3")   # not applied (async)
    print("t_c1 =", t_c1, " t_c2 =", t_c2, " c.cursor =", cw.cursor.applied_log_id, " lag =", cw.lag())
    attempt("c.check(gina viewer d3)  [untokened]",
            lambda: cw.check("user:gina", "viewer", "doc:d3"))
    attempt("c.check(gina viewer d3, at_least=t_a)  [foreign, <= cursor]",
            lambda: cw.check("user:gina", "viewer", "doc:d3", at_least=t_a))
    attempt("c.check(gina viewer d3, at_least=t_c2)  [own token]",
            lambda: cw.check("user:gina", "viewer", "doc:d3", at_least=t_c2))
    sc.close()
