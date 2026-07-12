"""Encode a (schema, tuples, queries) triple into the Lean CLI's JSON request.

Conformance C1 (SEMANTICS.md §10): drive the Lean executable spec `sem` on the
same inputs as the Python oracle and both backends, then compare answers.

We reuse the repository oracle's INDEPENDENT parser (`tests/oracle.py`) to turn the
DSL into an AST, then translate that AST into the Lean CLI's JSON `Expr` form,
folding n-ary `or`/`and` chains into the left-nested binary nodes the Lean model
uses (see `Core/Schema.lean` modeling note). This keeps the Lean side and the
oracle reading the *same* schema without sharing evaluation logic.
"""

from __future__ import annotations

import json
from typing import Iterable

from tests.oracle import (
    ODirect,
    OComputed,
    OTTU,
    OUnion,
    OIntersection,
    OExclusion,
    OracleTuple,
    parse_schema_ast,
    norm_pred,
)


def _expr_to_json(e) -> dict:
    """Translate one oracle AST node into the Lean CLI's JSON Expr."""
    if isinstance(e, ODirect):
        # oracle restriction is (type, predicate, wildcard) — matches Lean Restriction
        return {"direct": [[t, p, bool(w)] for (t, p, w) in e.restrictions]}
    if isinstance(e, OComputed):
        return {"computed": e.relation}
    if isinstance(e, OTTU):
        return {"ttu": [e.target_rel, e.tupleset_rel]}
    if isinstance(e, OUnion):
        return _fold_binary("union", e.children)
    if isinstance(e, OIntersection):
        return _fold_binary("inter", e.children)
    if isinstance(e, OExclusion):
        return {"excl": [_expr_to_json(e.base), _expr_to_json(e.subtract)]}
    raise TypeError(f"unknown oracle AST node: {e!r}")


def _fold_binary(tag: str, children: tuple) -> dict:
    """Left-fold an n-ary union/intersection (arity >= 2) into binary nodes."""
    if len(children) < 2:
        raise ValueError(f"{tag} with arity {len(children)} (expected >= 2)")
    acc = _expr_to_json(children[0])
    for c in children[1:]:
        acc = {tag: [acc, _expr_to_json(c)]}
    return acc


def schema_to_json(schema_text: str,
                   object_wildcards: Iterable[tuple[str, str]] = ()) -> dict:
    """Parse the DSL (via the oracle's parser) and emit the Lean CLI schema JSON."""
    ast = parse_schema_ast(schema_text)  # {(type, relation): OExpr}
    defs = [[[t, r], _expr_to_json(e)] for (t, r), e in ast.items()]
    ow = [[t, r] for (t, r) in object_wildcards]
    return {"defs": defs, "objectWildcards": ow}


def tuple_to_json(tup: OracleTuple) -> dict:
    """A stored tuple in the CLI's flat form."""
    return {
        "sp": norm_pred(tup.subject_predicate),
        "st": tup.subject_type,
        "sn": tup.subject_name,
        "rel": tup.relation,
        "ot": tup.object_type,
        "on": tup.object_name,
    }


def query_to_json(subject_predicate, subject_type, subject_name,
                  relation, object_type, object_name) -> dict:
    """A query in the CLI's flat form (same layout as a tuple)."""
    return {
        "sp": norm_pred(subject_predicate),
        "st": subject_type,
        "sn": subject_name,
        "rel": relation,
        "ot": object_type,
        "on": object_name,
    }


def build_request(schema_text: str,
                  tuples: Iterable[OracleTuple],
                  queries: Iterable[tuple],
                  object_wildcards: Iterable[tuple[str, str]] = (),
                  mode: str | None = None) -> str:
    """Assemble the full JSON request string for `zcli`.

    `queries` is an iterable of 6-tuples
    `(subject_predicate, subject_type, subject_name, relation, object_type, object_name)`.
    `mode="graph"` makes zcli run the operational GRAPH model (`graphRun` +
    `GraphModel.check`) instead of the spec `sem`; tuples are applied as writes
    in list order (Phase 6 graph-state conformance).
    """
    req = {
        "schema": schema_to_json(schema_text, object_wildcards),
        "tuples": [tuple_to_json(t) for t in tuples],
        "queries": [query_to_json(*q) for q in queries],
    }
    if mode is not None:
        req["mode"] = mode
    return json.dumps(req)
