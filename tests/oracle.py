"""
Reference oracle for wildcard-aware Zanzibar reachability (spec §4).

This is a deliberately naive, memoized BFS/DFS evaluator over
``(schema, list_of_input_tuples)``. It exists ONLY to serve as an independent
ground truth for testing the materialized ``WildcardIndex`` in ``index_v4``.

Independence contract (spec §4):
  * imports NOTHING from ``index_v4`` (no DB, no edges, no bridges, no RuleSet.apply);
  * shares no *evaluation* logic with the production index -- only plain data;
  * parses the OpenFGA DSL itself into a small declarative model, so a bug in the
    production schema parser cannot silently corrupt both sides.

The evaluator answers questions *intensionally* (spec §4.2): a wildcard query
asks "does a grant flow THROUGH the wildcard", not "does every concrete instance
happen to have access". Ghost entities (never mentioned in any tuple) are handled
because the universe is recomputed per-query and includes the query endpoints,
and because marker matching is by shape alone.

Performance is irrelevant here; clarity is everything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import EllipsisType
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Input data
# ---------------------------------------------------------------------------

class OracleTuple(NamedTuple):
    """A single stored relation tuple. ``'...'`` is the bare subject predicate."""
    subject_predicate: str
    subject_type: str
    subject_name: str
    relation: str
    object_type: str
    object_name: str


def t(subject_predicate, subject_type, subject_name, relation, object_type, object_name) -> OracleTuple:
    """Convenience constructor that normalises the bare predicate (Ellipsis -> '...')."""
    return OracleTuple(_norm_pred(subject_predicate), subject_type, subject_name,
                       relation, object_type, object_name)


def _norm_pred(pred: str | EllipsisType) -> str:
    return '...' if (pred is Ellipsis or pred is None) else pred


# ---------------------------------------------------------------------------
# Declarative schema model (built by an independent parser)
# ---------------------------------------------------------------------------

@dataclass
class RelationDef:
    """The union children of one ``define <relation>: ...`` clause."""
    has_direct: bool = False                       # at least one ``[...]`` restriction
    computed: list[str] = field(default_factory=list)          # computed usersets: ``writer``
    ttu: list[tuple[str, str]] = field(default_factory=list)   # tuple-to-userset: (P, R2) for ``P from R2``


def parse_schema(text: str) -> dict[tuple[str, str], RelationDef]:
    """
    Parse an OpenFGA DSL string into ``{(type, relation): RelationDef}``.

    Independent of ``zanzibar_utils_v1`` on purpose. Only the constructs this
    project supports are handled: ``[...]`` direct restrictions, bare computed
    usersets (``writer``), and ``P from R2`` tuple-to-usersets, joined by ``or``.
    Boolean ``and`` / ``but not`` are out of scope (spec §10) and not parsed.
    """
    relations: dict[tuple[str, str], RelationDef] = {}
    current_type: str | None = None

    for raw in text.strip().splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('type '):
            current_type = line.split(' ', 1)[1].strip()
        elif line.startswith('define '):
            if current_type is None:
                raise ValueError('relation defined outside of a type')
            name, _, rules = line[len('define '):].partition(':')
            rel_def = relations.setdefault((current_type, name.strip()), RelationDef())
            for clause in rules.split(' or '):
                clause = clause.strip()
                if not clause:
                    continue
                if clause.startswith('['):
                    rel_def.has_direct = True
                elif ' from ' in clause:
                    computed_rel, _, tupleset_rel = clause.partition(' from ')
                    rel_def.ttu.append((computed_rel.strip(), tupleset_rel.strip()))
                else:
                    rel_def.computed.append(clause)
    return relations


# ---------------------------------------------------------------------------
# Expansion accumulator
# ---------------------------------------------------------------------------

@dataclass
class Expansion:
    """Everything that can reach an object node under a relation."""
    users: set[tuple[str, str]] = field(default_factory=set)          # (type, name) bare subjects
    usersets: set[tuple[str, str, str]] = field(default_factory=set)  # (type, name, predicate)
    markers: set[tuple[str, str]] = field(default_factory=set)        # (type, predicate) wildcard shapes

    def update(self, other: 'Expansion') -> None:
        self.users |= other.users
        self.usersets |= other.usersets
        self.markers |= other.markers


# ---------------------------------------------------------------------------
# Oracle
# ---------------------------------------------------------------------------

class Oracle:
    def __init__(self, schema: str, tuples: list[OracleTuple]):
        self.relations = parse_schema(schema)
        self.tuples = list(tuples)

    def _universe(self, entity_type: str, query_names: set[tuple[str, str]]) -> set[str]:
        """
        Concrete type-``entity_type`` names appearing anywhere in the tuples
        (either position), plus the query's own endpoint names (spec §4.1).
        Wildcard ``'*'`` is never a concrete instance.
        """
        names: set[str] = set()
        for tup in self.tuples:
            if tup.subject_type == entity_type and tup.subject_name != '*':
                names.add(tup.subject_name)
            if tup.object_type == entity_type and tup.object_name != '*':
                names.add(tup.object_name)
        for q_type, q_name in query_names:
            if q_type == entity_type and q_name != '*':
                names.add(q_name)
        return names

    def check(self, subject_predicate, subject_type, subject_name,
              relation, object_type, object_name) -> bool:
        s_pred = _norm_pred(subject_predicate)
        query_names = {(subject_type, subject_name), (object_type, object_name)}

        # ``seen`` is a single per-query DFS-visited set (spec §4.3): it prevents
        # divergence on recursive schemas. Re-visiting a key returns the empty
        # expansion; the first visit's full result is already in the union.
        seen: set[tuple[str, str, str]] = set()

        def expand(o_type: str, o_name: str, rel: str) -> Expansion:
            key = (o_type, o_name, rel)
            if key in seen:
                return Expansion()
            seen.add(key)

            acc = Expansion()
            rel_def = self.relations.get((o_type, rel))
            if rel_def is None:
                return acc

            # o_name='*' expands ONLY wildcard-object tuples (intensional, §4.2);
            # a concrete object also absorbs tuples targeting T:* (w_all->concrete).
            matching_objects = {o_name} if o_name == '*' else {o_name, '*'}

            if rel_def.has_direct:
                for tup in self.tuples:
                    if (tup.relation == rel and tup.object_type == o_type
                            and tup.object_name in matching_objects):
                        s_p, s_t, s_n = tup.subject_predicate, tup.subject_type, tup.subject_name
                        if s_n == '*':
                            acc.markers.add((s_t, s_p))
                            if s_p != '...':               # bridged-in shape / members-of-any
                                for g in self._universe(s_t, query_names):
                                    acc.update(expand(s_t, g, s_p))
                        elif s_p == '...':
                            acc.users.add((s_t, s_n))
                        else:
                            acc.usersets.add((s_t, s_n, s_p))
                            acc.update(expand(s_t, s_n, s_p))

            for r2 in rel_def.computed:
                acc.update(expand(o_type, o_name, r2))

            for computed_rel, tupleset_rel in rel_def.ttu:
                for tup in self.tuples:
                    if (tup.relation == tupleset_rel and tup.object_type == o_type
                            and tup.object_name in matching_objects):
                        s_t, s_n = tup.subject_type, tup.subject_name
                        if s_n == '*':
                            acc.markers.add((s_t, computed_rel))
                            for g in self._universe(s_t, query_names):
                                acc.update(expand(s_t, g, computed_rel))
                        else:
                            acc.usersets.add((s_t, s_n, computed_rel))
                            acc.update(expand(s_t, s_n, computed_rel))

            return acc

        expansion = expand(object_type, object_name, relation)

        if subject_name == '*':
            return (subject_type, s_pred) in expansion.markers
        if s_pred == '...':
            return ((subject_type, subject_name) in expansion.users
                    or (subject_type, '...') in expansion.markers)
        return ((subject_type, subject_name, s_pred) in expansion.usersets
                or (subject_type, s_pred) in expansion.markers)


def check_oracle(schema: str, tuples: list[OracleTuple],
                 subject_predicate, subject_type, subject_name,
                 relation, object_type, object_name) -> bool:
    """Module-level convenience: build a fresh Oracle and answer one query."""
    return Oracle(schema, tuples).check(subject_predicate, subject_type, subject_name,
                                        relation, object_type, object_name)
