---
id: TK79
title: the late-GC rows' design justification (a drain_deltas replica must see them) is pinned by nothing
brief: drain_deltas replica needs the late GC rows: TRUE; pinned 2026-10-12c by tests/test_tk79_outbox_replica.py
pri: NOW
size: S
deps: []
related: [TK73, TK74]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-18
moved: 2026-10-12c
updated: 2026-10-12c
closed: 2026-10-12c
---

`DeltaProcessor._run_cascade` refuses to drop the outbox rows that a reconcile-time GC emits late, on the grounds that "an external `drain_deltas` replica must see them". That sentence is what makes `TK73` ask a semantic question instead of suppressing the rows, so the design rests on it. Until 2026-10-12c nothing tested it in either direction. This row pins it: a replica fed the drained stream equals the primary, and one that misses the GC-window rows is wrong, at each of the three emission sites.

## Traps

## Read first

- `docs/tk79-outbox-replica-2026-10-12.md` — the ACTIVE-PLAN doc; read its dated Correction at the top first
- `tests/test_tk79_outbox_replica.py` — the pin; its module docstring holds the literal sabotage output
- `src/zanzibar/graphindex/processor.py::DeltaProcessor._gc_subject_node` and `::_gc_public_node` — the GC entry points whose rows are pinned
- `src/zanzibar/graphindex/core.py::ReachabilityIndex._emit` — why the stream is an exact Edge-pair changelog

## Log

### 2026-09-18

READ by the `TK74` fan-out completeness critic (2026-09-18); the grep half re-checkable in seconds.

`src/zanzibar/graphindex/processor.py:1611` carries the justification for NOT suppressing the late reconcile-time-GC outbox rows: they are "honest, balanced retractions (an external `drain_deltas` replica must see them)". That sentence is the reason the `TK73` fix asks a SEMANTIC question instead of simply dropping the rows -- i.e. **it is load-bearing for the shipped design**.

**Nothing in the tree asserts it.** `src/zanzibar/graphindex/outbox.py::drain_deltas` is called only from `tests/test_outbox.py`, `tests/test_graphindex.py:41` and `tests/test_boolean_compile.py:434` -- none of them about GC emission. `tests/test_cascade_quiesce_gc.py` never inspects outbox contents at all (grepped: no `outbox` in any assertion, 213 lines). And `src/zanzibar/connectedstore/source.py::catch_up_evaluator` tails the TUPLE LOG, not the outbox, so **there is no in-tree outbox consumer whatsoever**.

So the claim "a replica must see these rows" is untested in both directions: nothing shows a replica needs them, and nothing shows a replica fed them arrives at the right state.

FIRST ACTION: write the missing consumer-side property -- drain the outbox across a cascade that includes a reconcile-time GC strip, apply the deltas to an independent replica, and assert the replica's membership equals the primary's (and the oracle's). That is a real differential test of a claim the design rests on, and `tests/test_i14_crossing_middles.py::test_middles_retire_with_their_entity` is already a witness that produces such rows (`TK75` log, 2026-09-18), so the fixture exists.

### 2026-10-04g

PROMOTED LATER -> NEXT 2026-10-04g (user: NEXT raised to 5, ranked by correctness certainty). Why (READ 2026-10-04g): drain_deltas is called only from src/zanzibar/graphindex/outbox.py, src/zanzibar/graphindex/processor.py and three test modules (test_outbox, test_graphindex, test_boolean_compile); no consumer replays the drained stream, so the design premise that late-GC rows must reach a replica is unpinned. Cheap shape: replay the drained rows into a replica and compare it with the primary AND the oracle. Independent of TK120 ordering.

### 2026-10-12b

Re-ranked 2026-10-12b (user approved the order in chat): TK118 NOW, then TK79, then TK102 (NEXT); TK97 and TK44 down to LATER (process tooling / coverage research with no known bug); TK134+TK135 stay LATER, user says no rush to release 0.0.4. Why TK118 first: it is the only row about a fail-OPEN, and it bears on what we tell production users about residue today.

### 2026-10-12c

IMPLEMENTED 2026-10-12c (uncommitted; gate not run; row left open for the close stage). VERDICT: the justification is TRUE, so the comment was pinned, not corrected. Measured first-hand (READ): core.py::ReachabilityIndex._emit emits ADDED/REMOVED exactly on Edge row create/delete, so the drained stream is a changelog of the Edge pair set. On the TK73 witness, a drain_deltas replica equals the primary after every commit; one fed the stream minus the rows emitted inside _gc_subject_node keeps (admin@folder:x -> 3 nodes), and once SQLite recycles that id for folder:q the replica claims folder:q reaches viewer@folder:x, which the primary check and the oracle deny. TK75 strip-arm site is load-bearing too. DOC: docs/tk79-outbox-replica-2026-10-12.md (ACTIVE-PLAN). LANDED: tests/test_tk79_outbox_replica.py (7 tests, green: test_drained_replica_matches_primary_closure[x,z,w,q,y], test_strip_arm_rows_reach_the_replica, test_late_gc_rows_are_load_bearing); a pointer added to the processor.py comment. SABOTAGE: S1 suppress rows around _maybe_remove_bridges in _gc_subject_node -> 5 red; S2 suppress rows around _sync_entity_middles in both GC fns -> 1 red (strip-arm test); S3/S4 instrument controls -> 7/2 red; literal output in the module docstring; all restored, src clean. RED: nothing known. NEXT: gate (doc_counts --generate needed: tests/ count +7), then close.

FIX-1 after adversarial review, 2026-10-12c (uncommitted; gate not run; row open for the close stage). (1) MAJOR fixed: the third late-emission site, the _sync_entity_middles strip arm at the end of processor.py::DeltaProcessor._gc_subject_node, was unpinned; on the TK73/I14 fixtures it never emits (every recorded subject there has a non-crossable type). New witness + pin: tests/test_tk79_outbox_replica.py::test_subject_gc_strip_arm_rows_reach_the_replica on SUBJECT_GC_SCHEMA (folder#member recorded in doc.restricted upos; un-recording GCs the entity folder:f1 last real node; strip emits rows 8..10). S2sub now 1 red (was 7 green); S2 both sites 2 red. (2) Oracle leg stated as transitive (replica == primary Edge pairs, primary == oracle) and checked per write on the new fixture. (3) Membership demo is now type-legal: id 9 reused for user:u9, stale pair reads user:u9 viewer folder:x, oracle and primary False, control u8 True; id->key resolution relabelled REASONED. (4) Body paragraph + Read first filled (lint check 14 resolves; sabotaged pointer went red). (5) doc_counts regenerated: tests/ 2281, suite 3370. DOC: docs/tk79-outbox-replica-2026-10-12.md, dated Correction at the top. Module: 8 passed. RED: nothing known. NEXT: gate, then close.

CLOSED 2026-10-12c. VERDICT: the design justification is TRUE (a drain_deltas replica needs the late GC rows), so it is pinned, not corrected. LANDED: tests/test_tk79_outbox_replica.py (8 tests): test_drained_replica_matches_primary_closure[x,z,w,q,y] (replica == primary Edge pairs after every commit on the TK73 witness), test_strip_arm_rows_reach_the_replica (TK75 _sync_entity_middles in _gc_public_node), test_subject_gc_strip_arm_rows_reach_the_replica (SUBJECT_GC_SCHEMA; _sync_entity_middles in _gc_subject_node; primary == oracle per write), test_late_gc_rows_are_load_bearing (dropping the GC rows leaves a stale pair; SQLite id reuse makes it a wrong ALLOW that primary and oracle deny). processor.py::DeltaProcessor._run_cascade comment points at the pin (comment-only). Sabotage S1/S2/S2sub/S3/S4 each red, literal output in the module docstring and plan doc. PostgreSQL id-reuse half is REASONED only. DOC (now FROZEN): docs/tk79-outbox-replica-2026-10-12.md.
