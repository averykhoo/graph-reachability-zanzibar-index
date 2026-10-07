"""`unparse_schema_ast`: SchemaAST -> DSL text.

Part of `zanzibar.schema`; split out of the single-file module by TK120 (2026-10-06).
"""
from .syntax import Computed, Direct, Exclusion, Expr, Intersection, Restriction, SchemaAST, TTU, Union


# ---- unparser (round-trip property, boolean spec §9) ----

def unparse_schema_ast(ast: SchemaAST) -> str:
    """Render an AST back to DSL text such that ``parse_schema_ast(unparse_schema_ast(a))
    == a`` for every AST a parse can produce. The empty AST is not one of them: it renders
    as ``""``, which the parser refuses (`TK124`). Operator children inside chains are
    parenthesized (the grammar's `unit`); leaves render bare."""

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
            base = _chain(e.base)
            sub = _chain(e.subtract)
            return f'{base} but not {sub}'
        raise TypeError(f"unknown Expr node {e!r}")

    def _unit(e: Expr) -> str:
        # chain units: operators need parens, leaves don't
        if isinstance(e, (Union, Intersection, Exclusion)):
            return f'({render(e)})'
        return render(e)

    def _chain(e: Expr) -> str:
        # exclusion operands are chains: a nested exclusion needs parens
        if isinstance(e, Exclusion):
            return f'({render(e)})'
        return render(e)

    types_in_order: list[str] = []
    for (t, _rel) in ast:
        if t not in types_in_order:
            types_in_order.append(t)

    lines: list[str] = []
    for t in types_in_order:
        lines.append(f'type {t}')
        rels = [(rel, expr) for (tt, rel), expr in ast.items() if tt == t]
        if rels:
            lines.append('  relations')
            for rel, expr in rels:
                lines.append(f'    define {rel}: {render(expr)}')
        lines.append('')
    return '\n'.join(lines)
