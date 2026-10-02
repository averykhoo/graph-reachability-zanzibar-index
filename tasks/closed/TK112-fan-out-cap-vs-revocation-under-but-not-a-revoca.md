---
id: TK112
title: fan-out cap vs revocation: under but not a revocation is an ADD; a capped async row strands removals
brief: async case fixed for reads 2026-10-02b (TK111 stall marker); owed: polarity-aware cap exemption under but-not
pri: NEXT
size: M
deps: []
related: [TK111, TK33]
parent:
labels: []
source: docs/p10-scope-audit-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-10-03b
updated: 2026-10-03b
closed: 2026-10-03b
---

Filed from the P10 re-run (2026-09-27d). Full witness, provenance and reconciliation: [`docs/p10-scope-audit-2026-09-27.md`](../docs/p10-scope-audit-2026-09-27.md) §5 H2. The section is copied below as it stood when filed; the doc is the body of record.


**Witness** (*verify* `PROBED`, fixed cap `ZANZIBAR_MAX_CLOSURE_FANOUT=20` set before import,
2026-09-27; schema `group{member:[user]}`,
`doc{grant:[user, group#member]; banned:[user, group#member]; viewer: grant but not banned}`,
which both parsers accept):

```
A2 sync:  grant (3 members): OK -> 4 ... member add u29: OK -> 31
          viewer u0 before ban: True
          ban group:big (30 members): REFUSED ClosureFanoutExceeded: ... 30 closure rows (30 ancestors x 0 descenda...
          graph viewer u0 after refused ban: True | set engine: True ; oracle if ban had landed: False
          ban user:u0 individually: OK -> 32 ; REMOVE grant: OK -> 33
C2 async, PLAIN schema: tokens grant/remove: 32 33 ; catch_up REFUSED ClosureFanoutExceeded ; lag: 2
          untokened check u0 viewer doc:old (revoked in source): True
          tokened check (at_least=remove token): False ; set engine: False
D3 sync:  doc{grant;banned;viewer: grant but not banned} + folder{reader:[doc#viewer]}, 30 folders
          un-ban REMOVE: REFUSED ClosureFanoutExceeded: ... 30 closure rows (0 ancestors x 30 descenda...
```

Sites (`READ`, verify, line numbers as of 2026-09-27): `index_v4/core.py` `:805`
`if count > 0 and self.max_closure_fanout and fanout > ...`, with the "REMOVALS ARE
DELIBERATELY EXEMPT" comment at `:793`. `connectedstore/apply.py::_apply_row` re-raises
("the cursor cannot advance past this row"). `connectedstore/store.py::ConnectedStore._fresh_enough`
returns `at_least is None or ...`. `index_v4/processor.py::DeltaProcessor._write_derived`
calls `widx.add_tuple` (`:712`). `tests/test_reg17_closure_fanout_cap.py` has 0 hits for
`but not|subtrahend|banned|revoc` (synth re-grep, 2026-09-28).

**Proposed row** — *"Fan-out cap vs revocation: under `but not` a revocation is an ADD, and a
capped async row strands every later removal"*, **NEXT**, size M.
Brief: CLAUDE.md says removals are exempt from the cap "because a cap that can refuse a
revocation is a fail-open". Three admitted paths contradict that (witness above):
(a) sync: banning a large group through a `but not` subtrahend is an ADD, and it is refused;
(b) sync: an un-ban REMOVE is capped through `DeltaProcessor._write_derived`, which fails
closed;
(c) async, any schema: a capped logged row stalls `catch_up`, and untokened
`ConnectedStore.check` keeps serving revoked grants without bound.
Fix: (1) exempt edges routed onto an Exclusion's subtrahend leaf. The compiler knows them
in `RuleSet.compiled`, and their fan-out is linear. (2) Make freshness stall-aware:
`_fresh_enough(None)` stops certifying index reads while the cursor is stalled on a refused
row, and falls back to the set engine as tokened reads already do. (2) is shared with H4.
Pin A2, C2 and D3 as positive tests in `tests/test_reg17_closure_fanout_cap.py`, sabotaged.
Correct the CLAUDE.md "removals are exempt" bullet, the `core.py` comment, the TK33 premise,
and `docs/spec-deviations.md` 2026-07-29c's "Does not bite at the 100,000 default" (false for
a group of more than 100k members).

## Log

### 2026-09-27d

2026-09-27d, ORCHESTRATOR FIRST-HAND REPRODUCTION. Ran `.scratch/wf-0927/probes/fanout-cap-boolean-revocation/verify/vprobe.py` (cap=20 set via ZANZIBAR_MAX_CLOSURE_FANOUT before import). Literal: A2 `ban group:big (30 members): REFUSED ClosureFanoutExceeded` then `graph viewer u0 after refused ban: True | set engine: True` (refusal is loud and the backends agree -- an operational fail-open for the caller, not a divergence); C2 async plain schema `catch_up: REFUSED ClosureFanoutExceeded`, `lag: 2`, `untokened check u0 viewer doc:old (revoked in source): True`, `tokened check (at_least=remove token): False`, `set engine: False` -- the SAME stale-ALLOW mechanism as TK111; D3 `un-ban REMOVE: REFUSED ClosureFanoutExceeded ... (0 ancestors x 30 descenda...`. At the 100,000 default this needs a >100k-member group. Body ids: H2 = this row, H4 = TK111.

### 2026-10-02b

2026-10-02b: case (c) is CLOSED FOR READS by the shared fix on TK111 (see that row and docs/tk111-stall-aware-freshness-2026-10-02.md). A capped async row still stalls catch_up, but the untokened check now falls back to the set engine and the untokened lookup refuses with IndexStalled; raising the cap and re-running catch_up clears the stall (pinned: tests/test_tk111_stall_aware_freshness.py::test_fanout_capped_row_stalls_and_untokened_check_stops_serving_revoked_allow). STILL OPEN: (1) the sync refusal of a revocation-shaped ADD under but-not; the plan doc sec 4 shows the exemption must key on the leaf NET POLARITY (a subtrahend of a subtrahend is a grant), not on subtrahend-ness, and proposes the compiler emit negative leaf families from _build_plan_tree (UNVERIFIED); (2) whether the async apply should cap at all (undecided); (b) the un-ban REMOVE capped via DeltaProcessor._write_derived fails CLOSED, an availability defect, rank below (1); plus the doc corrections listed in the body. NEXT ACTION: probe the polarity of every leaf in the compiled plans for a nested but-not schema, then implement (1).

### 2026-10-03b

2026-10-03b CLOSED. DECISION (option iv, a fable consult adopted by the session; the user steered toward "not broken or too surprising" and guessed "make the cap less strict"): the closure fan-out cap is a SYNC-ADMISSION bound only. Sync: every edge ADD is capped, including revocation-shaped adds under but-not (case a, the ban; case K, joining a banned group) and the un-ban REMOVE that restores a grant via the processor (case b, fails closed). The refusal is loud (ClosureFanoutExceeded) and atomic (log, set engine and index all unchanged, so the backends agree). Async: ConnectedStore.catch_up and the non-bulk build_index run inside ReachabilityIndex.fanout_cap_suspended, so an over-cap row is applied with a warning and case (c) cannot stall any more. Options (i)/(iii), polarity exemptions, were rejected: a sound exemption needs a global sign fixpoint, and cases K and G show it would switch the cap off for most of a boolean schema. Map and reasoning: docs/tk111-stall-aware-freshness-2026-10-02.md sec 7 (and sec 8 for the scout salvage). LANDED: index_v4/core.py::ReachabilityIndex.fanout_cap_suspended + _fanout_cap_suspended (thread-scoped, re-entrant), the cap site's suspended branch (_log.warning), connectedstore/store.py::ConnectedStore.catch_up, connectedstore/build.py::build_index. PINNED: tests/test_tk112_cap_policy.py (8 tests: sync refusal is atomic for ban/join/unban, async never capped for all three, non-bulk build_index never capped, window re-entrant and thread-scoped); tests/test_tk111_stall_aware_freshness.py::test_fanout_over_cap_row_no_longer_stalls_the_async_apply replaces the old stall pin. Mutation sweep with an M0 control, PROBED first-hand: 16 of 16 mutants red, 0 INERT (table in doc sec 7). DOCS CORRECTED: CLAUDE.md Operational-knobs bullet, the core.py cap comment, the reg17 module docstring, spec-deviations 2026-07-29c (dated correction), TK33 (comment).
