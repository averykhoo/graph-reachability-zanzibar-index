2026-09-02b — ten-phase gate re-run after the eliminator landed; verdict in the session-log entry.

(nav) **THE 4c-ii CO-LANDING IS SIZED BY PROBE AND IS A CLOSED LIST — 14 SITES / 12 DECLS /
6 FILES.** Staging `sorry` at every site builds the whole tree (rc=0, 1089 jobs), so nothing
outside the census exists. 14 sites but 12 decls: `graph_correct_w3d2` and `_d` each host TWO
(one servable, one query-relation), so "thread the predicate" and "add the query premise" are
NOT separable — that is where a partial landing gets left half-done. Servability 7 of 8.
LANDED: `Leaf.lean::not_leafNode_of_publicOfLeaf_none`, row 27's guard's eliminator, additive
and pinned by a RELATION-varying pair; `lean` identical to anchor (585/584/164).
(!) **NEXT IS THE ATOMIC CO-LANDING — nothing smaller is green-stoppable** (§11.12 rule 5).

(!) **`grep "declaration uses 'sorry'"` RETURNS 0 — Lean uses BACKTICKS** — §11.13 **(u)**.
14 staged sorries + rc=0 read back as "premise never needed". Make an assurance grep fire on
purpose before believing its zero. (q) is the over-counting half of the same lesson.
