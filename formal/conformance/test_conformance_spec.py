"""C1 answer conformance: the Lean executable spec `sem` vs the reference oracle.

SEMANTICS.md §10 / plan §6. This is the cheap validation that the Lean spec is the
RIGHT spec (Phase 2, before deep proofs). It runs the same (schema, tuples, query)
triples through:
  * the repository oracle (`tests/oracle.check_oracle`), and
  * the Lean executable spec (`zcli` over the encoded request),
and asserts they agree on every grid point. A disagreement is a spec-adjudication
event (plan §8.2): STOP and record it, do not silently reconcile.

The set engine and graph index are added to this comparison in Phase 3/4 (they
require the concrete models). Here we pin spec-vs-oracle, which is what validates
the transcription.

Skips cleanly if the Lean `zcli` binary is not built.
"""

from __future__ import annotations

import itertools

import pytest

from tests.oracle import check_oracle, t as mk_tuple

from formal.conformance.encode import build_request
from formal.conformance import runner


# --- corpus: (name, schema_text, tuples, object_wildcards) --------------------

_SCHEMAS = {
    "union_computed": (
        """
        type user
        type doc
          define editor: [user]
          define viewer: [user] or editor
        """,
        [mk_tuple("...", "user", "alice", "editor", "doc", "d1"),
         mk_tuple("...", "user", "bob", "viewer", "doc", "d1")],
        (),
    ),
    "group_userset": (
        """
        type user
        type group
          define member: [user, group#member]
        type doc
          define viewer: [group#member]
        """,
        [mk_tuple("...", "user", "alice", "member", "group", "g1"),
         mk_tuple("member", "group", "g1", "member", "group", "g2"),
         mk_tuple("member", "group", "g2", "viewer", "doc", "d1")],
        (),
    ),
    "ttu": (
        """
        type user
        type folder
          define viewer: [user]
        type doc
          define parent: [folder]
          define viewer: viewer from parent
        """,
        [mk_tuple("...", "user", "alice", "viewer", "folder", "f1"),
         mk_tuple("...", "folder", "f1", "parent", "doc", "d1")],
        (),
    ),
    "wildcard_public": (
        """
        type user
        type doc
          define viewer: [user, user:*]
        """,
        [mk_tuple("...", "user", "*", "viewer", "doc", "d1")],
        (),
    ),
    "boolean_exclusion": (
        """
        type user
        type doc
          define editor: [user]
          define banned: [user]
          define viewer: editor but not banned
        """,
        [mk_tuple("...", "user", "alice", "editor", "doc", "d1"),
         mk_tuple("...", "user", "bob", "editor", "doc", "d1"),
         mk_tuple("...", "user", "bob", "banned", "doc", "d1")],
        (),
    ),
    "boolean_star_exclusion": (
        """
        type user
        type doc
          define base: [user:*]
          define blocked: [user]
          define viewer: base but not blocked
        """,
        [mk_tuple("...", "user", "*", "base", "doc", "d1"),
         mk_tuple("...", "user", "mallory", "blocked", "doc", "d1")],
        (),
    ),
}


def _grid(tuples):
    """Build the query grid: per type, concrete names in tuples + one ghost + '*',
    crossed with every (relation, object) appearing in the schema/tuples."""
    types = set()
    names_by_type: dict[str, set[str]] = {}
    relations = set()
    objects = set()  # (object_type, object_name)
    for tup in tuples:
        for ty, nm in ((tup.subject_type, tup.subject_name),
                       (tup.object_type, tup.object_name)):
            types.add(ty)
            names_by_type.setdefault(ty, set())
            if nm != "*":
                names_by_type[ty].add(nm)
        relations.add(tup.relation)
        objects.add((tup.object_type, tup.object_name))
    # subjects: bare concretes (+ ghost + '*') per type, and userset subjects
    subjects = []
    for ty in types:
        names = sorted(names_by_type.get(ty, set())) + [f"ghost_{ty}", "*"]
        for nm in names:
            subjects.append(("...", ty, nm))
    return subjects, sorted(relations), sorted(objects)


@pytest.mark.parametrize("name", sorted(_SCHEMAS))
def test_spec_matches_oracle(name):
    schema_text, tuples, obj_wild = _SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    subjects, relations, objects = _grid(tuples)
    queries = []
    for (sp, st, sn), rel, (ot, on) in itertools.product(subjects, relations, objects):
        queries.append((sp, st, sn, rel, ot, on))

    request = build_request(schema_text, tuples, queries, obj_wild)
    spec_answers = runner.run_spec(request)

    oracle_answers = [
        check_oracle(schema_text, tuples, sp, st, sn, rel, ot, on)
        for (sp, st, sn, rel, ot, on) in queries
    ]

    assert len(spec_answers) == len(oracle_answers)
    mismatches = [
        (queries[i], spec_answers[i], oracle_answers[i])
        for i in range(len(queries))
        if spec_answers[i] != oracle_answers[i]
    ]
    assert not mismatches, (
        f"[{name}] spec/oracle disagreement (ADJUDICATION EVENT — see plan §8.2):\n"
        + "\n".join(f"  query={q} spec={s} oracle={o}" for q, s, o in mismatches[:20])
    )
