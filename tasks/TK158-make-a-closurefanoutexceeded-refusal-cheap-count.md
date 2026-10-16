---
id: TK158
title: Make a ClosureFanoutExceeded refusal cheap: count before loading, undo instead of rebuild
brief: A refused grant of a 1M-member group costs 91 s and 3.8 GB (TK150 sec 4); make the refusal cheap
pri: LATER
size: M
deps: []
related: [TK150]
parent:
labels: []
source: docs/closure-fanout-cost-2026-10-14.md
source_hash:
created: 2026-10-16
moved: 2026-10-16
updated: 2026-10-16
closed:
---

Filed 2026-10-16 from TK150 (proposed text in `docs/closure-fanout-cost-2026-10-14.md` § Correction 2026-10-16 (e) item 1, verbatim below).

Measured in `docs/closure-fanout-cost-2026-10-14.md` sec 4: the cap bounds what
is written, not what a refusal costs. Two causes (READ 2026-10-16, still open):
`core.py::ReachabilityIndex._add_direct_edge_unsafe_impl` loads the ancestor and descendant
sets as full ORM `Edge` rows before counting; and `src/zanzibar/store/_store.py::Store._write`'s
error arm calls `self.source.refresh_evaluator()` (a whole set-engine rebuild, 39.8 s at
1M tuples) because admission already put the tuple into the evaluator. Proposed: count |A|
and |D| with `SELECT count(*)` and refuse before loading; on `IndexResourceLimit`, undo
the one admitted tuple in the evaluator instead of rebuilding. Acceptance: re-run
`point --shape userset --n 1000000 --mode refuse` and show the refusal well under 1 s;
a test that the evaluator matches a fresh rebuild after a refusal. Changes no modelled
algorithm (the count precedes the modelled expansion), but check `formal/CORRESPONDENCE.md`.
Run the PostgreSQL leg (locking path).

## Read first

- `docs/closure-fanout-cost-2026-10-14.md` sec 4 (the refusal path) and § Correction 2026-10-16

## Log
