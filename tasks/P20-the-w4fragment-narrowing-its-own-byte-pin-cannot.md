---
id: P20
title: the W4Fragment narrowing its own byte pin cannot see -- graph_correct weakens silently
brief: User call 2026-08-31: NOT accepted inside P3. Needs a mechanical refusal, not a docstring. Blocks P3 steps 6-10.
pri: NEXT
size: M
deps: []
related: [P3]
parent:
labels: [formal]
source: board
source_hash:
created: 2026-08-31
moved: 2026-08-31
updated: 2026-08-31
closed:
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-08-31

Split out of P3 on a user call 2026-08-31: the graph_correct weakening is NOT accepted inside P3. Finding: adding a NoLeafSubjects field to FullScope.lean:193::W4Fragment makes Zanzibar.graph_correct strictly weaker, but headline_statements.txt:27 records the hypothesis BY NAME as (hF : W4Fragment S T) -- by design, headline_definitions.txt:4-5 -- so the statement pin stays byte-identical and only headline_definitions.txt:102 moves. The statement pin is structurally blind to this whole class of weakening. Deliverables: (a) the scope decision, (b) a MECHANICAL REFUSAL (field-count assertion on W4Fragment, sabotaged by adding a dummy field), because sabotage-procedure.md ranks that above the docstring that is the alternative. Blocks P3 steps 6-10.
