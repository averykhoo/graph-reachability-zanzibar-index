---
id: TK112
title: fan-out cap vs revocation: under but not a revocation is an ADD; a capped async row strands removals
brief: fan-out cap refuses revocations under but-not; a capped async row strands later removals (shares TK111 fix)
pri: NEXT
size: M
deps: []
related: [TK111, TK33]
parent:
labels: []
source: docs/p10-scope-audit-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-09-27d
updated: 2026-09-27d
closed:
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
