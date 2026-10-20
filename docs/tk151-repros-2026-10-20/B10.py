"""B10 repro: exception re-exports per subpackage vs zanzibar top level; non-public
types in public signatures."""
import inspect, typing
import zanzibar
import zanzibar.schema as S, zanzibar.setengine as SE, zanzibar.graphindex as G, zanzibar.store as ST

print("zanzibar.__file__:", zanzibar.__file__)
top_exc = [n for n in zanzibar._LAZY
           if isinstance(getattr(zanzibar, n), type) and issubclass(getattr(zanzibar, n), BaseException)]
print(f"top-level exception/warning names: {len(top_exc)}")
mods = {'schema': S, 'setengine': SE, 'graphindex': G, 'store': ST}
print(f"{'name':28} " + " ".join(f"{m:>10}" for m in mods))
for n in top_exc:
    cells = []
    for m, mod in mods.items():
        in_all = n in getattr(mod, '__all__', ())
        has = hasattr(mod, n)
        same = has and getattr(mod, n) is getattr(zanzibar, n)
        cells.append('ALL' if in_all else ('attr' if has else '-') if same or not has else 'DIFF')
    print(f"{n:28} " + " ".join(f"{c:>10}" for c in cells))

# Raised-by-backend vs re-exported-by-backend
from zanzibar.schema.errors import ClosureFanoutExceeded, PathCountExceeded
print("graphindex raises ClosureFanoutExceeded/PathCountExceeded (core.py) but exports them:",
      'ClosureFanoutExceeded' in G.__all__, 'PathCountExceeded' in G.__all__)
print("setengine raises AdmissionRejected but exports it:", 'AdmissionRejected' in SE.__all__)

print("\n-- non-public types in public signatures --")
for n in ('Entity', 'RelationalTriple', 'SchemaInfo'):
    print(f"{n}: in zanzibar.schema.__all__={n in S.__all__}, importable from zanzibar.schema={hasattr(S, n)},"
          f" defined in {getattr(S, n).__module__}")
def hints(f):
    return {k: v for k, v in typing.get_type_hints(f).items()}
print("compile_ruleset (in schema.__all__):", inspect.signature(S.compile_ruleset))
print("RuleSet.schema_info field type:", S.RuleSet.__annotations__["schema_info"])
try:
    typing.get_type_hints(S.RuleSet)
except NameError as e:
    print("typing.get_type_hints(RuleSet) ->", type(e).__name__, e)
print("RuleSet.apply:", inspect.signature(S.RuleSet.apply))
print("WildcardIndex.__init__ (in graphindex.__all__):", inspect.signature(G.WildcardIndex.__init__))
print("DeltaProcessor.__init__:", inspect.signature(G.DeltaProcessor.__init__))

# Can a user drive RuleSet.apply without the private type?
rs = zanzibar.parse_openfga_schema("model\n  schema 1.1\ntype user\ntype doc\n  relations\n    define viewer: [user]\n")
from zanzibar.schema import Entity, RelationalTriple
t = RelationalTriple(Entity('user', 'a'), 'viewer', Entity('doc', 'd'), ...)
print("RuleSet.apply(RelationalTriple(...)) ->", rs.apply(t))
try:
    print(rs.apply(('user', 'a', 'viewer', 'doc', 'd')))
except Exception as e:
    print("RuleSet.apply(tuple) ->", type(e).__name__, e)
