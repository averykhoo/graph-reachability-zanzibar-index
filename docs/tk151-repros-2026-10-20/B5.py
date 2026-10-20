"""B5 repro: StaleRead / LookupNotFresh for a token issued by ANOTHER store."""
import zanzibar
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

print("zanzibar from:", zanzibar.__file__)

SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
"""

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
session = Session(engine)

a = Store(session, "store-a", schema=SCHEMA)
b = Store(session, "store-b", schema=SCHEMA)
ta = a.add_tuple("user:alice", "viewer", "doc:d1")
b.add_tuple("user:bob", "viewer", "doc:d1")
tb = b.add_tuple("user:carol", "viewer", "doc:d1")
print("token from a:", ta, " token from b:", tb, " a.watermark():", a.watermark())


def attempt(label, fn):
    try:
        print(label, "->", fn())
    except Exception as e:
        print(label, "->", type(e).__name__ + ":", e)


for round_ in (1, 2):
    print(f"--- round {round_} ---")
    attempt("a.check(at_least=tb)",
            lambda: a.check("user:alice", "viewer", "doc:d1", at_least=tb))
    attempt("a.expand(at_least=tb)",
            lambda: a.expand("viewer", "doc:d1", at_least=tb))
    attempt("a.lookup(at_least=tb)",
            lambda: a.lookup("user:alice", at_least=tb))
    if round_ == 1:
        print("following the advice: a.refresh(); a.catch_up()")
        a.refresh()
        a.catch_up()
