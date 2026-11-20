---
type: Task
id: TK-307
title: 'TK-275 split: adjudicate the docs/README.md sec 2 undeclared-liveness list (a) and fix the stale TK107-residue symbol cites (d)'
brief: re-measure first (the 2026-10-13 lists are stale); never restate the undeclared-doc count
pri: LATER
state: open
deps: []
source: session 2026-11-20a
created: 2026-11-20
moved: 2026-11-20a
updated: 2026-11-20a
---

TK-275 split: adjudicate the docs/README.md sec 2 undeclared-liveness list (part a) and fix the stale TK107-residue symbol cites (part d).

Split from TK-275 at the 2026-11-20a re-rank, so that TK-275 (NOW) holds only its part (c): freeze the closed-row ACTIVE-PLAN docs and add a lint check, sabotaged. The evidence is TK-275's Log entry 2026-10-13 ("REMAINING SCOPE"), 5 weeks old as of 2026-11-20: re-measure before acting.

- (a) The docs/README.md sec 2 "Not yet adjudicated" list is incomplete by sec 2's own method. Adjudicate which undeclared docs are deliberately exempt, and write the exemption rule into docs/README.md sec 2. Do not restate a count in this row (TK-275's trap).
- (d) `formal/SEMANTICS.md` sec 5.5 cites `processor.py` `_ts_leaf_predicates` as live, and `formal/ARCHITECTURE.md` cites `processor.py::_EvalContext.tupleset_ttu_check`; both had 0 hits under src/ on 2026-10-13. Also comment-only: `src/zanzibar/schema/boolean.py` still gives the pre-TK107 reason for storage leaves. Fix the cites (re-grep first).

## Traps

- Do not restate the undeclared-doc count here: it rotted three times on TK-275 (six, nine, eleven).

## Read first

- TK-275, Log 2026-10-13 (parts a and d)
- docs/README.md sec 2

## Log
