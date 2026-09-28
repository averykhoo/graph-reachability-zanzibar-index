---
id: TK111
title: path-count overflow wedges async catch_up; untokened ConnectedStore.check serves a stale ALLOW
brief: LIVE fail-open: a poison row stalls async catch_up; untokened check keeps a revoked ALLOW (verified first-hand)
pri: NEXT
size: M
deps: []
related: [TK112]
parent:
labels: []
source: docs/p10-scope-audit-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-09-27d
updated: 2026-09-27d
closed:
---

Filed from the P10 re-run (2026-09-27d). Full witness, provenance and reconciliation: [`docs/p10-scope-audit-2026-09-27.md`](../docs/p10-scope-audit-2026-09-27.md) §5 H4. The section is copied below as it stood when filed; the doc is the body of record.


**Witness.** Schema `type user / type group relations define member: [user, group#member]`,
which both parsers accept. Writes: `user:u member group:L0`, then for each layer `i`:
`L_i#member → A_i`, `L_i#member → B_i`, `A_i#member → L_{i+1}`, `B_i#member → L_{i+1}`.

*verify* `PROBED` on SQLite, `K=63`, 2026-09-28:

```
VK=63 async: writes=255 refused=0
  catch_up attempt 0/1/2: OverflowError: Python int too large to convert to SQLite INTEGER | lag=255
  check(u member L1): ConnectedStore.check(untokened)=False set_engine=True oracle=True
VK=63 async, VBATCH=1 (revoke of mallory viewer doc:secret logged behind the poison row): lag=2
  check(mallory viewer doc:secret): ConnectedStore.check(untokened)=True set_engine=False oracle=False
  tokened check(at_least=255) mallory=False ; tokened lookup(u): LookupNotFresh
VK=63 sync: refused: ('+', ('member','group','B62','member','group','L63'), 'OverflowError', ...)
```

*audit* `PROBED` on PostgreSQL, `K=31` (125 tuples), 2026-09-27:

```
pg sync=True  K=31 accepted=124/125 first_refusal=(('member','group','B30','member','group','L31'), 'DataError', 'integer out of range')
pg sync=False K=31 accepted=125/125 catch_up_err=('DataError', 'integer out of range') lag=125 | check(u member L31): graph=False set_engine=True oracle=True
pg after revoke: untokened check (graph)=True | set_engine=False | tokened check(at_least=127)=False
```

Column widths (`READ`/`PROBED`, both agents): every integer column is `INTEGER`, which is
int4 on PostgreSQL (ids `SERIAL`) and int64 on SQLite, including `index_v4/models.py::EdgeV4`
`indirect_edge_count`. The closure fan-out cap never fires on this witness.

**Proposed row** — *"Path-count overflow: an admitted write whose apply overflows
`indirect_edge_count` wedges async `catch_up`, and untokened reads keep a stale ALLOW"*,
**NEXT**, size M.
Brief: `EdgeV4.indirect_edge_count` counts derivations. A K-layer diamond chain makes it
`2^K`, which overflows at `K=31` on PostgreSQL (the only supported server) and at `K=63` on
SQLite. Sync fails closed with a raw `DataError` / `OverflowError`. Async logs the write,
`catch_up` retries the poison row forever, and every later row, revocations included, never
reaches the index. Untokened `ConnectedStore.check` then serves a stale ALLOW without bound
(witness above). Widening to `BigInteger` only moves the ceiling. Decide instead between a
clean admission refusal, raised before the `TupleLogV1` row commits on both dialects, and
count saturation. Saturation breaks exact decrement, so refusal is probably right. Add H2's
stall-aware freshness (shared fix). Permanent test on SQLite at `K=63`, async, with the
revoke-behind-the-poison-row variant, sabotaged. Optionally add a PostgreSQL leg of the matrix
behind `ZANZIBAR_TEST_DSN`: *audit* measured `17 passed in 453.83s` on 2026-09-27 via a
redirect plugin. The `.scratch/wf-0927/probes/pg-leg-outside-gate/` probes are the starting
point. *audit* also flagged, `REASONED` only: `SERIAL` int4 primary keys cap a store's
lifetime log and node ids at `2^31-1` on PostgreSQL (fails closed).

## Log

### 2026-09-27d

2026-09-27d, ORCHESTRATOR FIRST-HAND REPRODUCTION (the rule for anything that moves the live-bug count). Ran the P10 verifier's probe `.scratch/wf-0927/probes/pg-leg-outside-gate/verify/vprobe.py` with VK=63 VBATCH=1, SQLite, async. Literal: `K=63 sync=False writes=255 refused=0`; `catch_up attempt 0/1/2: OverflowError: Python int too large to convert to SQLite INTEGER | lag=2`; `check(user:mallory viewer doc:secret): ConnectedStore.check(untokened)=True set_engine=False oracle=False`; `tokened check(at_least=255) mallory=False`; `tokened lookup(u): LookupNotFresh`. So the untokened read serves a REVOKED grant, without bound, while tokened reads correctly refuse to be fresh. The body calls this H4 and its sibling H2; those ids are local to docs/p10-scope-audit-2026-09-27.md -- H2 is TK112, and the stall-aware freshness fix is shared with it. The probe lives in gitignored .scratch; the vprobe source is short (81 lines) and its schema+write list are in the body above, so the witness survives a sweep.

NOW -> NEXT by user instruction (2026-09-28): both TK111 and TK112 sit at NEXT for now; NOW is left empty. The user has not asked for the fix to start.
