---
id: P23
title: parser refusal parity: both parsers refuse the same schemas (children TK109, TK105)
brief: ONE task with TK109+TK105: refuse bad declared names in both parsers; oracle twins of 7 product refusals
pri: NEXT
size: M
deps: []
related: [TK55, TK109, TK105, TK115]
parent:
labels: [infra]
source: board
source_hash: c7f66db90464
created: 2026-09-06b
moved: 2026-10-03c
updated: 2026-10-03c
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

### 2026-09-27d

P10 re-run (2026-09-27d): TK115 (JSON front-end fidelity) needs a declared-name refusal on the JSON path, and should reuse whatever charset contract this row decides. This row never mentions the JSON path today.

### 2026-10-03c

PROMOTED LATER -> NEXT and made the PARENT of `TK109` and `TK105` (user decision 2026-10-03c: "link them all together ... we'll handle all 3 together as one task"). Size S -> M for the bundle. Why bundled: all three are the same fix shape -- a `_validate_*` refusal in `zanzibar_utils_v1.py` and its twin in `tests/oracle.py`, each with a REFUSED SHAPE / WHY / INSTEAD block, pinned both-refuse like `tests/test_reg_empty_relation_name.py` (`TK55`). Why P23 is the parent: it is the only one of the three that changes the PRODUCT parser and has a shipped consequence; `TK109`/`TK105` are oracle-only twins of refusals production already has. Also give `parse_openfga_json` the same declared-name contract (`TK115` asks for it).
Evidence (AGENT-REPORTED 2026-10-03c, skeptic verdict WEAKENED, gap still exists): both parsers accept declared names `*`, `a#b`, non-ASCII, a 257-char name, a tab; with `define *: viewer but not blocked`, `ConnectedStore(sync=True)` refuses a VALID write (`AdmissionRejected "invalid relation '*'"`), and async logs it and stalls the index. No wrong answer reachable (stall is not served since `TK111`). Map: `docs/promote-next-triage-2026-10-03.md` secs 2 and 4. Close the children first (lint: no closed parent with open children).
NEXT ACTION: re-probe the `*` witness first-hand, then add the charset refusal to both parsers plus the oracle twins listed on `TK109`.
