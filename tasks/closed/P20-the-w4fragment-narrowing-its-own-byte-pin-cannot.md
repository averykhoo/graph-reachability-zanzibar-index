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
moved: 2026-08-31b
updated: 2026-08-31b
closed: 2026-08-31b
---

`Zanzibar.graph_correct`'s scope is exactly `FullScope.lean::W4Fragment`, so adding a field
makes the headline theorem strictly WEAKER. No pin can raise an alarm about that:
`headline_statements.txt` records the hypothesis by NAME so its row stays byte-identical, and
`headline_definitions.txt`'s `fields=(...)` row does move but is cleared by
`statement_pin.py --generate` -- i.e. inside the same act as the change. **CLOSED ACCEPT
2026-08-31b**; both deliverables landed. Full record: `formal/history/PROOF_STATUS.md`
`## Session 2026-08-31b` sec 2-3.

## Traps

* ⚠ **Do not reuse this adjudication's reasoning without redoing it.** It was accepted
  because Python refuses every schema the narrowing excludes. Deliverable (b) then measured
  the ten EXISTING fields at **LOUD 0 / MIXED 3 / SILENT 7** -- that ground holds for none of
  them. This narrowing is the exception; the next one inherits nothing.
* ⚠ **The durable method lesson has a home**: `docs/sabotage-procedure.md`, sec "A pin you
  REGENERATE to accept a change cannot be the alarm for that change".
* ⚠ The live classification is a gated table, not prose:
  `formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE`. Read it there; do not
  restate the counts.

## Read first

* `formal/history/PROOF_STATUS.md` `## Session 2026-08-31b` sec 2 (the adjudication) and
  sec 3 (the three artifacts, with the literal sabotage outputs).
* `formal/conformance/test_w4fragment_scope_pin.py` -- the mechanical refusal itself.
* Descendants: `DW-1` (close the seven silent fields), `P21` (make the classification
  measured rather than argued).

## Log

### 2026-08-31

Split out of P3 on a user call 2026-08-31: the graph_correct weakening is NOT accepted inside P3. Finding: adding a NoLeafSubjects field to FullScope.lean:193::W4Fragment makes Zanzibar.graph_correct strictly weaker, but headline_statements.txt:27 records the hypothesis BY NAME as (hF : W4Fragment S T) -- by design, headline_definitions.txt:4-5 -- so the statement pin stays byte-identical and only headline_definitions.txt:102 moves. The statement pin is structurally blind to this whole class of weakening. Deliverables: (a) the scope decision, (b) a MECHANICAL REFUSAL (field-count assertion on W4Fragment, sabotaged by adding a dummy field), because sabotage-procedure.md ranks that above the docstring that is the alternative. Blocks P3 steps 6-10.

### 2026-08-31b

ADJUDICATED ACCEPT 2026-08-31b. (a) the narrowing excludes only schemas Python already refuses (_validate_ast_references); sabotage proves that refusal is the PREMISE -- neutered, 'define safe: viewer.0 from parent' compiles to the forbidden rule, so the narrowing would be UNSOUND. (b) mechanical refusal landed: formal/conformance/test_w4fragment_scope_pin.py, 15 tests, hand-maintained W4FRAGMENT_SCOPE table, sabotaged 3 ways. Key finding: the ten EXISTING fields classify LOUD 0 / MIXED 3 / SILENT 7, so the justification does NOT generalise.
