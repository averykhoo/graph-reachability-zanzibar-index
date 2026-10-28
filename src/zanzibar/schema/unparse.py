"""`unparse_schema_ast`: SchemaAST -> DSL text.

Part of `zanzibar.schema`.
"""
# Provenance (moved out of the docstring, TK123 item 14): split out of the single-file module
# by TK120 (2026-10-06).
from .syntax import Computed, Direct, Exclusion, Expr, Intersection, Restriction, SchemaAST, TTU, Union, _iter_directs


# ---- unparser (round-trip property, boolean spec §9) ----

def unparse_schema_ast(ast: SchemaAST) -> str:
    """Render an AST back to DSL text such that ``parse_schema_ast(unparse_schema_ast(a))
    == a`` for every AST a parse can produce. The empty AST is not one of them: it renders
    as ``""``, which the parser refuses. Operator children inside chains are
    parenthesized (the grammar's `unit`); leaves render bare.

    Two rules keep the output inside what the parser accepts since 0.0.5:

    * BOTH operands of ``but not`` render as units, so an operator operand is
      parenthesised: ``Exclusion(Union(a, b), c)`` renders ``(a or b) but not c``. The old
      rendering ``a or b but not c`` is refused since 0.0.5.
    * Every restriction type that keys no relation (``user`` in ``[user]``) gets its own
      ``type`` line FIRST, sorted, the way OpenFGA examples declare ``type user`` before
      the types that use it. A restriction to an undeclared type is refused since 0.0.5, and
      a relation-less ``type`` line is not an AST key, so the round trip still holds."""
      # Provenance (moved out of the docstring, TK123 item 14): TK137 (2026-10-14).
    # Provenance (moved out of the docstring, TK123 item 14): `TK124`.

    def render_restriction(r: Restriction) -> str:
        s = r.type + (':*' if r.wildcard else '')
        if r.predicate != '...':
            s += f'#{r.predicate}'
        return s

    def render(e: Expr) -> str:
        if isinstance(e, Direct):
            return '[' + ', '.join(render_restriction(r) for r in e.restrictions) + ']'
        if isinstance(e, Computed):
            return e.relation
        if isinstance(e, TTU):
            return f'{e.target_rel} from {e.tupleset_rel}'
        if isinstance(e, Union):
            return ' or '.join(_unit(c) for c in e.children)
        if isinstance(e, Intersection):
            return ' and '.join(_unit(c) for c in e.children)
        if isinstance(e, Exclusion):
            # both operands are units (TK137 S7): ``(a or b) but not (c and d)``
            return f'{_unit(e.base)} but not {_unit(e.subtract)}'
        raise TypeError(f"unknown Expr node {e!r}")

    def _unit(e: Expr) -> str:
        # units: operators need parens, leaves don't
        if isinstance(e, (Union, Intersection, Exclusion)):
            return f'({render(e)})'
        return render(e)

    types_in_order: list[str] = []
    for (t, _rel) in ast:
        if t not in types_in_order:
            types_in_order.append(t)
    keyed = set(types_in_order)
    relationless = sorted({r.type for expr in ast.values() for d in _iter_directs(expr)
                           for r in d.restrictions} - keyed)

    lines: list[str] = []
    for t in relationless:
        lines.append(f'type {t}')
    if relationless:
        lines.append('')
    for t in types_in_order:
        lines.append(f'type {t}')
        rels = [(rel, expr) for (tt, rel), expr in ast.items() if tt == t]
        if rels:
            lines.append('  relations')
            for rel, expr in rels:
                lines.append(f'    define {rel}: {render(expr)}')
        lines.append('')
    return '\n'.join(lines)
