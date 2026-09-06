---
id: P23
title: declared-name charset asymmetry between the oracle parser and zanzibar_utils_v1
brief: oracle parser has no dot-lock; other out-of-charset declared names are graph-refused/set-accepted, no schema-level pin
pri: LATER
size: S
deps: []
related: [TK55]
parent:
labels: [infra]
source: board
source_hash: c7f66db90464
created: 2026-09-06b
moved: 2026-09-06b
updated: 2026-09-06b
closed:
---

`TK55` (closed 2026-09-06b) made BOTH parsers -- `zanzibar_utils_v1.py::parse_schema_ast`
and the independent `tests/oracle.py::parse_schema_ast` -- refuse an EMPTY declared
relation name, pinned by `tests/test_reg_empty_relation_name.py` (15 cases). The wider
asymmetry is still open:

* the oracle parser has no `.`-lock on declared relation names (the main parser has one,
  because leaf predicates are `<relation>.<index>`);
* every other out-of-charset declared name (`*`, a space, `#`, non-ASCII, 257 chars) is
  graph-REFUSED at write time (`_IDENTIFIER_RE`) but set-ACCEPTED, and today only the
  `ParityEngine` accept/reject unanimity catches it -- there is no schema-level pin.

Decide the contract: refuse at parse time, in both parsers, and pin it the way the empty
case is pinned. Ledger entry: `docs/spec-deviations.md` 2026-09-06.

## Log

### 2026-09-06b

first reconciliation: filed from the board row this session; body and row say the same thing
