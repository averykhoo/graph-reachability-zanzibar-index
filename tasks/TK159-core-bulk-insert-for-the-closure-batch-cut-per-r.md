---
id: TK159
title: Core bulk insert for the closure batch (cut per-row time and RAM of an admitted write)
brief: Replace one ORM Edge per pair in _add_indirect_edges_batch_unsafe with a Core bulk insert, as bulk_build does
pri: LATER
size: M
deps: []
related: [TK150]
parent:
labels: [perf]
source: docs/closure-fanout-cost-2026-10-14.md
source_hash:
created: 2026-10-16
moved: 2026-10-16
updated: 2026-10-16
closed:
---

Filed 2026-10-16 from TK150 (proposed text in `docs/closure-fanout-cost-2026-10-14.md` § Correction 2026-10-16 (e) item 2, verbatim below).

Measured in `docs/closure-fanout-cost-2026-10-14.md` sec 3a: the ORM flush is
30-40 % of an admitted write, and the writer holds ~4.6 KB per new closure row as ORM
objects until the commit (the memory wall at ~1M rows). READ 2026-10-16:
`core.py::ReachabilityIndex._add_indirect_edges_batch_unsafe` still does
`self.session.add(Edge(...))` per pair. Proposed: a Core `insert()` of the batch in
chunks, as `bulk_build` already does, keeping the outbox emission one row per pair.
Behaviour-preserving (no Lean change per `CLAUDE.md` "Perf work & the Lean model"), but
paranoia's invariant checker and the ORM identity map must still see consistent state.
Acceptance: same answers (matrix, conformance), and `fanout_cost_bench` at 10,000 /
100,000 showing lower write s and peak delta MB than this doc's table.

## Read first

- `docs/closure-fanout-cost-2026-10-14.md` sec 3a (where the time goes) and § Correction 2026-10-16

## Log
