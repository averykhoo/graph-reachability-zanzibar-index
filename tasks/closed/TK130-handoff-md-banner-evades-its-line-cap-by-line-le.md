---
id: TK130
title: HANDOFF.md banner evades its line cap by line length; add a byte cap and prune
brief: banner evades its 14-line cap via ~3.7k-char lines; add a byte/width cap and prune stale layers
pri: LATER
size: M
deps: []
related: []
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-10-07c
moved: 2026-10-07d
updated: 2026-10-07d
closed: 2026-10-07d
---

Item 3 of the 2026-10-07 cross-repo context audit. The banner sits at its line cap
(`task.py::BANNER_MAX_LINES`), but single lines reach ~3.7k characters, and layers stamped
2026-09-13 and 2026-09-22 are still in it (the layering `docs/README.md` sec 6 bans).
`HANDOFF.md` grew from 4.3 KB at the 2026-09-06 cutover to about 18 KB. Add a byte cap or a
per-line width cap to `scripts/handoff_lint.py`, then prune the stale layers.

## Traps

- (!) Prune into the session log or the rows; a banner layer is not deleted if it is the
  only home of a durable rule. Promote any such rule to `CLAUDE.md` first.

## Read first

- [`docs/context-audit-2026-10-07.md`](../docs/context-audit-2026-10-07.md) item 3 (measured 2026-10-07).

## Log

### 2026-10-07d

LANDED (not closed; gate not yet run): handoff_lint.py::MAX_BYTES (HANDOFF.md 5000 B, LF-normalised) in check_ceilings (verify.sh 4f) + task.py::BANNER_MAX_WIDTH (600 chars as board prints) in check_banner = lint check 12 (verify.sh 4g). Banner pruned 14 lines -> 2; HANDOFF.md 18803 B -> 3415 B on disk (3371 B LF). Every pruned layer has a session-log entry; durable rules found only in the banner (ceiling control, red-on-a-proof, concrete-witness defeq-blindness, two-candidate-fixes) promoted to docs/sabotage-procedure.md end of the sweep section. Pins: tests/test_tk130_handoff_size_caps.py (9 tests; 11-mutant sweep + 3 controls transcribed in its docstring). Docs synced: docs/README.md sec 7 step 2, docs/tasktool-spec.md check 12, docs/gate-runbook.md caps row. Next: run the gate (doc_counts --generate first: tests/ count moved).

Done 2026-10-07d. HANDOFF.md 18.8 KB -> 3.4 KB; banner pruned to the current layer (old layers verified to live in session-log entries/rows; the 2026-09-22c user goal moved to decision-log.md and a CLAUDE.md line). New caps in handoff_lint.py (MAX_BYTES, banner line width), tests/test_tk130_handoff_size_caps.py with sabotage. Evidence (agent reports, moved-text tables, sabotage sweeps): docs/history/context-caps-housekeeping-2026-10-07.md. Gated with the 2026-10-07d commit.
