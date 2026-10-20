"""B7 repro: is_valid_identifier('...') / `type ...` / `[user#...]`."""
import sys, os, warnings
sys.path.insert(0, r"C:/Users/user/PycharmProjects/graph-reachability-zanzibar-index")  # for tests.oracle
from sqlmodel import SQLModel, Session, create_engine
from zanzibar.schema.errors import is_valid_identifier
from zanzibar.schema import parser as P
from zanzibar.store import Store

print("1 is_valid_identifier('...') =", is_valid_identifier("..."))
print("1 is_valid_identifier('*')   =", is_valid_identifier("*"))
print("1 docstring claims '...' NOT valid:", "'...'`` (bare subject predicate) are NOT valid" in (is_valid_identifier.__doc__ or "").replace("\n    ", " ") or is_valid_identifier.__doc__.split("--")[0])

A = "model\n  schema 1.1\ntype user\ntype doc\n  relations\n    define viewer: [user]\n"
B = "model\n  schema 1.1\ntype user\ntype doc\n  relations\n    define viewer: [user#...]\n"
astA, astB = P.parse_schema_ast(A), P.parse_schema_ast(B)
print("2 [user] AST     :", astA[("doc", "viewer")])
print("2 [user#...] AST :", astB[("doc", "viewer")])
print("2 equal          :", astA == astB)

C = "model\n  schema 1.1\ntype ...\ntype doc\n  relations\n    define viewer: [...]\n"
try:
    astC = P.parse_schema_ast(C)
    print("3 `type ...` parses:", dict(astC))
except Exception as e:
    print("3 `type ...` refused:", type(e).__name__, e)

D = "model\n  schema 1.1\ntype user\ntype doc\n  relations\n    define ...: [user]\n"
try:
    P.parse_schema_ast(D); print("4 `define ...` parses")
except Exception as e:
    print("4 `define ...` refused:", type(e).__name__, e)

# oracle twin
try:
    from tests import oracle
    for lbl, s in (("[user#...]", B), ("type ...", C)):
        try:
            oracle.parse_schema(s) if hasattr(oracle, "parse_schema") else None
            print("5 oracle accepts", lbl)
        except Exception as e:
            print("5 oracle refuses", lbl, type(e).__name__, e)
except Exception as e:
    print("5 oracle import failed:", type(e).__name__, e)

# end-to-end both backends, type named '...'
eng = create_engine("sqlite://")
SQLModel.metadata.create_all(eng)
with Session(eng) as s, warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        st = Store(s, "b7", schema=C)
        st.add_tuple("...:x", "viewer", "doc:d1")
        print("6 check ...:x viewer doc:d1 =", st.check("...:x", "viewer", "doc:d1"))
        print("6 set engine check          =", st.evaluator.check("...", "...", "x", "viewer", "doc", "d1") if hasattr(st, "evaluator") else "n/a")
        print("6 lookup_reverse doc:d1 viewer =", st.lookup_reverse("viewer", "doc", "d1") if hasattr(st, "lookup_reverse") else "n/a")
    except Exception as e:
        print("6 store with `type ...`:", type(e).__name__, e)
with Session(eng) as s:
    st = Store(s, "b7b", schema=B)
    st.add_tuple("user:alice", "viewer", "doc:d1")
    print("7 [user#...] check user:alice =", st.check("user:alice", "viewer", "doc:d1"))

# 8: duplicate restriction spelled two ways; tuple string with explicit '#...'
E = "model\n  schema 1.1\ntype user\ntype doc\n  relations\n    define viewer: [user, user#...]\n"
try:
    print("8 [user, user#...] AST:", P.parse_schema_ast(E)[("doc", "viewer")])
except Exception as e:
    print("8 [user, user#...] refused:", type(e).__name__, e)
from zanzibar.schema import tuplestr as TS
print("8 tuplestr names:", [n for n in dir(TS) if not n.startswith("__")][:12])
with Session(eng) as s:
    st = Store(s, "b7c", schema=A)
    try:
        st.add_tuple("user:carol#...", "viewer", "doc:d1")
        print("8 add 'user:carol#...' ok; check user:carol =", st.check("user:carol", "viewer", "doc:d1"))
    except Exception as e:
        print("8 add 'user:carol#...' refused:", type(e).__name__, e)
