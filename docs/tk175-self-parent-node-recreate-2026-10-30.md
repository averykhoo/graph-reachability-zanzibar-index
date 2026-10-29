# TK175 -- a node collected and re-created in one cascade: `zanzibar_node` UNIQUE violation (2026-10-30)

> **FROZEN** (`docs/README.md` sec 3) -- `TK175` closed 2026-10-30b, fix shipped in 0.1.1.
> Found by the gate: `tests/test_hypothesis.py::test_add_then_remove_restores_row_multiset` failed in
> `tests-tile:4/4` on a rare draw (it passed on the previous run of the same tile).
>
> Provenance. Below the rule is the diagnosis agent's report, transcribed from the gitignored
> `.scratch/tk175-node-integrity/agent.md` (AGENT; each section labels RUN / REASONED). Verified FIRST-HAND
> by the session, 2026-10-30b:
>
> * The Store repro (`store_probe.py`) re-run: sync `add_tuple('doc:d1','parent','doc:d1')` raises the
>   UNIQUE `IntegrityError` and rolls back (`check r1` True, tuple not stored); async commits the tuple
>   to the log and the catch-up raises (the set-engine fallback answers `r1` False, which is correct).
> * The fix as applied (`src/zanzibar/graphindex/core.py::ReachabilityIndex.node`, flush pending deletes
>   before the INSERT) plus `tests/test_tk175_self_parent_node_recreate.py` (3 tests): with the guard
>   removed, `rc=1 | 3 failed`; a first draft's async leg passed under that sabotage and was fixed (see
>   the test docstring). Neighbouring suites (processor, self-referential, cascade GC, stratified
>   negation, hypothesis): 94 passed.
> * `ReachabilityIndex.node` is not a `formal/CORRESPONDENCE.md` anchor; bookkeeping below the model,
>   no Lean change (REASONED, agrees with the agent's F6).

---


## F1 Repro (first-hand RUN, current tree)
`.scratch/tk175-node-integrity/repro.py` (pytest-free, uses tests/test_processor.py::build):
base add ('...','user','u2','r0','doc','d1') ok; add ('...','doc','d1','parent','doc','d1') FAILS:
`sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed: zanzibar_node.store_id, zanzibar_node.predicate, zanzibar_node.type, zanzibar_node.name, zanzibar_node.wildcard ... parameters: ('test', 'r1', 'doc', 'd1', '', 0, 0)`
Fails on the ADD of the self-parent (the remove is never reached). Deterministic.

## F2 Mechanism (first-hand RUN, `.scratch/tk175-node-integrity/trace.py`)
Trace output (literal):
```
  node 5 r1 doc d1 '' impl False rc 1
FLUSH new [('...', 'doc', 'd1')] deleted []
FLUSH new [('parent', 'doc', 'd1')] deleted []
DELETE node 5 r1 doc d1 from _gc_public_node:1229 <- _reconcile_subject:863 <- _reconcile:999 <- reconcile:870 <- _run_cascade:1529
FLUSH new [('r1', 'doc', 'd1')] deleted [(5, 'r1', 'doc', 'd1')]
FAILED IntegrityError ...
```
1. reconcile(doc, r1, d1): self-parent makes `r0 from parent` true for u2, so u2 loses r1; its derived edge goes,
   and processor.py::_gc_public_node (line 1229 @2026-10-30) calls `idx._evict_node(node)` (cache -> _MISSING)
   and `session.delete(node)` -- a PENDING delete, not flushed.
2. reconcile(doc, r2, d1): r2 = r1 from parent, parent = doc:d1 itself, so the from-chain userset subject is
   doc:d1#r1 = the identity just deleted. processor.py::_reconcile step 2a (line 924 @2026-10-30): `self._node`
   -> cache _MISSING -> None; should(true) != covered(false) -> `idx.node(..., create_if_missing=True, implicit=False)`.
3. core.py::ReachabilityIndex.node (add at ~1136, flush at 1137 @2026-10-30) adds a new Node and flushes. The
   flush holds BOTH the pending DELETE of id 5 and the INSERT of the same identity; SQLAlchemy's unit of work
   emits INSERTs before DELETEs for one mapper, so the INSERT hits the still-present row -> UNIQUE violation.
Root cause (REASONED from the trace + SQLAlchemy UOW ordering): the N15 cache is CORRECT (it says missing; the
row is logically deleted); the bug is creation-after-pending-delete of the same natural key within one flush.

## F3 HEAD (first-hand RUN)
`git worktree add $TEMP/zz-head-tk175 HEAD` (d41b9a4), repro.py + store_probe.py run with PYTHONPATH=<wt>;<wt>\src
(zanzibar.__file__ confirmed in the worktree): SAME IntegrityError, same parameters. Worktree removed
(`git worktree list` shows only the main tree). The uncommitted message-text edits are irrelevant.

## F4 Public Store impact (first-hand RUN, SQLite in-memory, no PostgreSQL needed)
`.scratch/tk175-node-integrity/store_probe.py`, `async_probe.py`; DSL = `schema.fga` (same AST; `define r0: [user] and [user]`,
user writes public `r0`, RuleSet.apply routes it to both leaves r0.0/r0.1, which the test helper also does).
- sync: `store.add_tuple('doc:d1','parent','doc:d1')` raises RAW `sqlalchemy.exc.IntegrityError` (not a classified
  refusal). Atomic: tuple not stored (later remove -> AdmissionRejected "not stored"), check r1 still True (consistent
  with no parent). REASONED from src/zanzibar/store/_store.py generic `except Exception` arm (~725-731 @2026-10-30:
  pop_pending_rows, rollback, refresh_evaluator). => availability loss: a VALID tuple can never be written.
- async: add_tuple commits to the log (token 2, lag 1); every catch_up() re-raises IntegrityError (poison row);
  index_stalled=True, stall_error "applied through 1: IntegrityError ...". Untokened AND at_least=2 check(u2 r1 d1)
  = False (correct, set-engine fallback); lookup_reverse raises IndexStalled. Stalled until the tuple is removed
  (then catch_up of the batch went through: observed ok). => availability loss, NOT a wrong answer.
Wrong-answer risk: none observed; REASONED: the failure is a flush raising inside the transaction, so no partial
state commits (sync rolls back; async's TK111 stall path stops serving the index).

## F5 Proposed fix (NOT applied) -- core.py::ReachabilityIndex.node creation branch
```diff
         _node = Node(store_id=self.store_id, predicate=predicate, type=entity_type, name=entity_name,
                        wildcard=wildcard, implicit=implicit)
+        # TK175: a same-identity Node may be PENDING DELETE in this session (e.g. processor
+        # _gc_public_node collected doc:d1#r1, then a self-parent from-chain re-interns it in the
+        # same cascade). The unit of work emits INSERTs before DELETEs, so flushing both together
+        # hits the unique key. Emit pending deletes first. The N15 cache already says _MISSING.
+        if self.session.deleted:
+            self.session.flush()
         self.session.add(_node)
         self.session.flush()
```
Validated by monkeypatch (`tk175_fixplugin.py`, `fixprobe.py`, `canon_probe.py`, first-hand RUN):
add ok; audit_fixpoint ok; derived_check r1/r2 for u2 = False (correct: d1 is its own parent and u2 has r0);
remove ok; `_state` restored == before: True; post-add state is write-order independent (r0-first == parent-first): True.
Store sync+async with fix: all writes ok, no stall, checks r1 False after add / True after remove.
pytest with plugin: tests/test_processor.py, test_self_referential_tuples.py, test_cascade_quiesce_gc.py,
test_tk114_stratified_negation.py -> 59 passed. Seed sweep (--hypothesis-seed 1..6) of add_then_remove +
permutation_invariance: green with AND without fix (the draw is rare -> the sweep is NOT a discriminating instrument;
the deterministic repro is).
Why here and not at the delete sites: node() is the sole incremental Node-creation point (census: only other
`Node(` is bulk_build.py:290, offline fresh build), so one guard covers every create-after-delete; flushing after
every delete would cost a flush per GC. `session.deleted` is empty on the hot path -> one truthiness test.
Alternative rejected: resurrecting the deleted object (SQLAlchemy has no clean undelete).

## F6 Pins / modelling
- No existing test pins this (self-parent + boolean + TTU-of-derived). Nearest area: tests/test_self_referential_tuples.py,
  tests/test_hypothesis.py::test_add_then_remove_restores_row_multiset (draw-dependent), tests/test_cascade_quiesce_gc.py.
  Propose a deterministic regression test (graph-only via tests.test_processor.build: base add, add/remove self-parent,
  assert `_state` restored + audit_fixpoint; plus a Store sync+async leg asserting no stall). RED today (observed crash),
  green with the fix (observed via monkeypatch) -> sabotage already shown in both directions.
- Modelling: REASONED behaviour-preserving persistence bookkeeping. formal/CORRESPONDENCE.md says run_cascade's N15 node
  cache scope is "not part of the modeled algorithm"; flush ordering is below the model. No Lean change; no §7 gap.
  Caveat (REASONED): the re-created node gets a NEW id (old id was deleted); nothing references the old id
  (_gc_public_node only deletes when no residue references it), and the round-trip/canonical probes are id-insensitive.
