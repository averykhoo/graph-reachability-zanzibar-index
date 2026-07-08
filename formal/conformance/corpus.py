"""Shared schema corpus for conformance tests (SEMANTICS.md §10 / plan C1).

Each entry: name -> (schema_text, tuples, object_wildcard_shapes). Tuples use the
oracle's `t(...)` constructor. Kept small so the full query grid stays fast, but
chosen to exercise every AST node and the star x boolean corners.
"""

from __future__ import annotations

from tests.oracle import t as mk_tuple


def _deep_grid(n_rel: int = 8, n_obj: int = 8):
    """A schema/tuples pair that traverses the object x relation grid so the
    evaluation depth is ~n_rel*n_obj — far exceeding an additive fuel bound.
    Regression for the multiplicative-fuelBound fix (Store.lean). check(alice, r1,
    node{n_obj}) is True (reaches the r1@node1 grant through the grid)."""
    lines = ["type user", "type node", "  define parent: [node]",
             "  define r1: [user] or r2"]
    for i in range(2, n_rel):
        lines.append(f"  define r{i}: r{i + 1}")
    lines.append(f"  define r{n_rel}: r1 from parent")
    schema = "\n".join(lines)
    tuples = [mk_tuple("...", "node", f"node{i}", "parent", "node", f"node{i + 1}")
              for i in range(1, n_obj)]
    tuples.append(mk_tuple("...", "user", "alice", "r1", "node", "node1"))
    return schema, tuples, ()


SCHEMAS: dict[str, tuple[str, list, tuple]] = {
    "deep_grid": _deep_grid(),
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
    "wildcard_group_member": (
        """
        type user
        type group
          define member: [user, user:*]
        type doc
          define viewer: [group#member]
        """,
        [mk_tuple("...", "user", "*", "member", "group", "g1"),
         mk_tuple("member", "group", "g1", "viewer", "doc", "d1")],
        (),
    ),
    "object_wildcard": (
        """
        type user
        type folder
          define viewer: [user]
        """,
        [mk_tuple("...", "user", "alice", "viewer", "folder", "*")],
        (("folder", "viewer"),),
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
    "boolean_intersection": (
        """
        type user
        type doc
          define editor: [user]
          define required: [user]
          define viewer: editor and required
        """,
        [mk_tuple("...", "user", "alice", "editor", "doc", "d1"),
         mk_tuple("...", "user", "alice", "required", "doc", "d1"),
         mk_tuple("...", "user", "bob", "editor", "doc", "d1")],
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
    "two_stratum_cascade": (
        """
        type user
        type doc
          define editor: [user]
          define banned: [user]
          define viewer: editor but not banned
          define muted: [user]
          define approver: viewer but not muted
        """,
        [mk_tuple("...", "user", "alice", "editor", "doc", "d1"),
         mk_tuple("...", "user", "bob", "editor", "doc", "d1"),
         mk_tuple("...", "user", "bob", "muted", "doc", "d1"),
         mk_tuple("...", "user", "carol", "editor", "doc", "d1"),
         mk_tuple("...", "user", "carol", "banned", "doc", "d1")],
        (),
    ),
    "taint_union_over_boolean": (
        # §3.1 taint: a plain union OVER a boolean relation must still serve
        # star-covered members. viewer is boolean (star base minus blocked);
        # approver unions viewer with admin.
        """
        type user
        type doc
          define base: [user:*]
          define blocked: [user]
          define viewer: base but not blocked
          define admin: [user]
          define approver: viewer or admin
        """,
        [mk_tuple("...", "user", "*", "base", "doc", "d1"),
         mk_tuple("...", "user", "mallory", "blocked", "doc", "d1"),
         mk_tuple("...", "user", "root", "admin", "doc", "d1")],
        (),
    ),
    "nested_boolean": (
        """
        type user
        type doc
          define editor: [user]
          define required: [user]
          define banned: [user]
          define viewer: (editor and required) but not banned
        """,
        [mk_tuple("...", "user", "alice", "editor", "doc", "d1"),
         mk_tuple("...", "user", "alice", "required", "doc", "d1"),
         mk_tuple("...", "user", "bob", "editor", "doc", "d1"),
         mk_tuple("...", "user", "bob", "required", "doc", "d1"),
         mk_tuple("...", "user", "bob", "banned", "doc", "d1")],
        (),
    ),
    "double_exclusion": (
        # a but not (b but not c): parenthesized nested exclusion as the subtrahend.
        """
        type user
        type doc
          define a: [user]
          define b: [user]
          define c: [user]
          define viewer: a but not (b but not c)
        """,
        [mk_tuple("...", "user", "alice", "a", "doc", "d1"),
         mk_tuple("...", "user", "bob", "a", "doc", "d1"),
         mk_tuple("...", "user", "bob", "b", "doc", "d1"),
         mk_tuple("...", "user", "carol", "a", "doc", "d1"),
         mk_tuple("...", "user", "carol", "b", "doc", "d1"),
         mk_tuple("...", "user", "carol", "c", "doc", "d1")],
        (),
    ),
    "demorgans": (
        # (A but not B) vs (not (not A or B)) style — exercise nested exclusion.
        """
        type user
        type doc
          define a: [user]
          define b: [user]
          define lhs: a but not b
          define rhs: a but not (a and b)
        """,
        [mk_tuple("...", "user", "alice", "a", "doc", "d1"),
         mk_tuple("...", "user", "bob", "a", "doc", "d1"),
         mk_tuple("...", "user", "bob", "b", "doc", "d1"),
         mk_tuple("...", "user", "carol", "b", "doc", "d1")],
        (),
    ),
}
