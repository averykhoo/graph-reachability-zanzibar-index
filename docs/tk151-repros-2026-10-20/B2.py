"""Repro B2: are UnsupportedByGraphIndex / DoublyBridgedShapeError ValueErrors?"""
import warnings
warnings.simplefilter("ignore")
import zanzibar
from zanzibar import (ZanzibarError, UnsupportedByGraphIndex, DoublyBridgedShapeError,
                      parse_openfga_schema)

print("== every public ZanzibarError subclass and its builtin bases")
for name in sorted(dir(zanzibar)):
    obj = getattr(zanzibar, name)
    if isinstance(obj, type) and issubclass(obj, ZanzibarError) and obj is not ZanzibarError:
        builtins_ = [b.__name__ for b in obj.__mro__ if b.__module__ == "builtins"
                     and b not in (object, BaseException, Exception)]
        print(f"  {name:28s} ValueError={issubclass(obj, ValueError)!s:5s} builtin={builtins_}")

print("== MRO")
print("  UnsupportedByGraphIndex:", [c.__name__ for c in UnsupportedByGraphIndex.__mro__])
print("  DoublyBridgedShapeError:", [c.__name__ for c in DoublyBridgedShapeError.__mro__])

F1 = """model
  schema 1.1
type user
type folder
  relations
    define parent: [folder, folder:*]
    define viewer: [user, folder:*#viewer, folder#admin]
    define admin: [user] or viewer from parent
"""
OWC = frozenset({("folder", "parent"), ("folder", "viewer")})

print("== parse_openfga_schema(F1, object_wildcard_shapes=OWC) under `except ValueError`")
try:
    try:
        parse_openfga_schema(F1, object_wildcard_shapes=OWC)
        print("  no error")
    except ValueError as e:
        print("  caught by except ValueError:", type(e).__name__)
except Exception as e:
    print("  ESCAPED except ValueError:", type(e).__name__, "| is ZanzibarError:",
          isinstance(e, ZanzibarError))

print("== Store(..., object_wildcard_shapes=OWC)")
from sqlmodel import SQLModel, Session, create_engine
eng = create_engine("sqlite://")
SQLModel.metadata.create_all(eng)
try:
    try:
        zanzibar.Store(Session(eng), "s", schema=F1, object_wildcard_shapes=OWC)
        print("  no error")
    except ValueError as e:
        print("  caught by except ValueError:", type(e).__name__)
except Exception as e:
    print("  ESCAPED except ValueError:", type(e).__name__)

print("== compile_ruleset(enable_boolean=False) on a `but not` schema")
from zanzibar.schema import compile_ruleset, parse_schema_ast, derive_schema_info
B = """model
  schema 1.1
type user
type doc
  relations
    define banned: [user]
    define viewer: [user] but not banned
"""
ast = parse_schema_ast(B)
try:
    try:
        compile_ruleset(ast, derive_schema_info(ast), enable_boolean=False)
        print("  no error")
    except ValueError as e:
        print("  caught by except ValueError:", type(e).__name__)
except Exception as e:
    print("  ESCAPED except ValueError:", type(e).__name__, "|", str(e)[:100])
