"""The ONE shared conformance query grid (spec / random / graph suites).

Previously each suite carried its own copy of `_grid`/`_queries` (F7) and the
grid derived its relation set purely from STORED tuples, so derived-only
relations — including every boolean root, e.g. `viewer: editor but not banned` —
were never queried (F2), and only bare-predicate subjects were emitted, leaving
the Lean spec's userset-subject branches (`Semantics.lean` directLeaf third arm,
ttuLeaf predicate arms) unpinned (F3). This module fixes all three:

* **Stored-tuple-derived behavior is preserved verbatim**: bare subjects are
  every concrete name per type seen in the tuples + one ghost + `*`, and the
  stored relations are still crossed with EVERY stored object type-obliviously
  (that cross product is the deliberate out-of-schema "ghost relation" probe).
* **Schema-declared targets (F2)**: the schema text is parsed with the oracle's
  INDEPENDENT parser (same parse `encode.py` uses) and every declared
  `(type, relation)` is paired with the stored objects OF THAT TYPE — type-aware
  on purpose, so the addition doesn't explode into querying every relation on
  every type.
* **Userset subjects (F3)**: for each declared `(type, relation)` whose type
  appears in the tuples, subjects `(relation, type, name)` over a BOUNDED name
  pool (first `_USERSET_NAME_BOUND` concrete names + the ghost). The bound keeps
  the full suite inside its runtime budget; `*` is deliberately excluded from
  the pool so every generated query keeps star subjects bare-predicate
  (the proved graph read scope's `hqs` gate, `GraphIndex/Exec.lean`).
"""

from __future__ import annotations

import itertools

from tests.oracle import parse_schema_ast

# F3 bound: userset-subject names per type = first N concrete names + the ghost.
# The naive full-name-pool product pushed the suite past its runtime budget on
# the wide corpora (deep_grid); 2 + ghost keeps every userset arm pinned
# (member/non-member/absent) while keeping growth bounded.
_USERSET_NAME_BOUND = 2


def grid(schema_text, tuples):
    """Build the query grid for one corpus.

    Returns ``(subjects, targets)`` where ``subjects`` is a list of
    ``(subject_predicate, subject_type, subject_name)`` and ``targets`` is a
    sorted list of ``(relation, object_type, object_name)``.
    """
    names_by_type: dict[str, set[str]] = {}
    stored_relations: set[str] = set()
    objects: set[tuple[str, str]] = set()
    for tup in tuples:
        for ty, nm in ((tup.subject_type, tup.subject_name),
                       (tup.object_type, tup.object_name)):
            names_by_type.setdefault(ty, set())
            if nm != "*":
                names_by_type[ty].add(nm)
        stored_relations.add(tup.relation)
        objects.add((tup.object_type, tup.object_name))

    declared = sorted(parse_schema_ast(schema_text))  # [(type, relation), ...]

    # Bare subjects: unchanged stored-tuple-derived behavior (names + ghost + *).
    subjects = []
    for ty in sorted(names_by_type):
        for nm in sorted(names_by_type[ty]) + [f"ghost_{ty}", "*"]:
            subjects.append(("...", ty, nm))
    # Userset subjects (F3): declared relations on their own type, bounded pool.
    for ty, rel in declared:
        if ty not in names_by_type:
            continue
        pool = sorted(names_by_type[ty])[:_USERSET_NAME_BOUND] + [f"ghost_{ty}"]
        for nm in pool:
            subjects.append((rel, ty, nm))

    # Targets: stored relations x ALL stored objects (preserved, type-oblivious
    # ghost probes included) ∪ declared relations x objects of their own type
    # (F2: derived-only relations — boolean roots — are now actually queried).
    targets = {(rel, ot, on) for rel in stored_relations for (ot, on) in objects}
    for ty, rel in declared:
        targets.update((rel, ot, on) for (ot, on) in objects if ot == ty)
    return subjects, sorted(targets)


def queries_for(schema_text, tuples):
    """The full query list: subjects x targets, as 6-tuples
    ``(subject_predicate, subject_type, subject_name, relation, object_type,
    object_name)``."""
    subjects, targets = grid(schema_text, tuples)
    return [
        (sp, st, sn, rel, ot, on)
        for (sp, st, sn), (rel, ot, on) in itertools.product(subjects, targets)
    ]


def fmt_mismatches(mismatches, a_name, b_name):
    return "\n".join(
        f"  query={q} {a_name}={a} {b_name}={b}" for q, a, b in mismatches[:20])
