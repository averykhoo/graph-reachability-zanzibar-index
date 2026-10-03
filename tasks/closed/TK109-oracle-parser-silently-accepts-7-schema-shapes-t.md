---
id: TK109
title: oracle parser silently accepts 7 schema shapes the product parser refuses
brief: PROBED 7 of 8: oracle accepts [] / dup type / dup relation / '.' in name / unrecognised line; product refuses
pri: LATER
size: S
deps: []
related: [TK105, TK108, P23]
parent: P23
labels: []
source: hand
source_hash:
created: 2026-09-27
moved: 2026-10-03e
updated: 2026-10-03e
closed: 2026-10-03e
---

## Log -- empty

**Filed 2026-09-27 by TK108's refusal census** (subagent, `.scratch/tk108/refusal-census.md`), **PROBED first-hand the same session** (`.scratch/tk108/oracle_gap.py`, both parsers' checked parse):

```
empty-restriction []       prod=REFUSE oracle=accept
duplicate type             prod=REFUSE oracle=accept
malformed type line        prod=REFUSE oracle=accept
dot in declared name       prod=REFUSE oracle=accept
duplicate relation         prod=REFUSE oracle=accept
unrecognised line          prod=REFUSE oracle=accept
dot in computed ref        prod=REFUSE oracle=REFUSE
empty entry [user,]        prod=REFUSE oracle=accept
```

The oracle (`tests/oracle.py::parse_schema_ast`) is the independent referee, and it silently ACCEPTS seven schema shapes the product parser (`zanzibar_utils_v1.py::parse_schema_ast`) refuses. The census reported "`.` in a computed or TTU reference" as an eighth; the probe above does not reproduce it for a computed ref (the oracle refuses, possibly via ASK-1's dangling-reference check rather than a '.' lock -- UNVERIFIED which).

Why it matters: a test that feeds such a schema to the oracle alone gets an answer where the system refuses, so the oracle cannot referee the refusal. The duplicate-relation case is `TK105`'s (the oracle keeps the last `define`).

Fix shape: independent twins in `tests/oracle.py` (NOT shared code -- independence contract), each with a `# REFUSED SHAPE ... WHY ... INSTEAD` comment (the rule from TK108), plus a differential test over these probes that both parsers refuse. Census also noted `parse_openfga_json` has no empty-relation-name check (REASONED, not probed).

## Log

### 2026-09-27d

P10 re-run (2026-09-27d): this row's REASONED JSON line (parse_openfga_json has no empty-relation-name check) is subsumed by TK115. The P10 audit probed that empty names fail loudly downstream; the live JSON holes are newline/colon names, duplicate keys and wildcard: false (docs/p10-scope-audit-2026-09-27.md sec 5 H5).

### 2026-10-03c

Now a CHILD of `P23` (user decision 2026-10-03c): done together with `P23` and `TK105` as one task; `P23` carries the NEXT slot and the plan. Triage 2026-10-03c (AGENT-REPORTED, PROBED) re-reproduced all 7 shapes as prod=REFUSE oracle=accept in the live tree. Map: `docs/promote-next-triage-2026-10-03.md`.

### 2026-10-03e

CLOSED with P23. All seven shapes are now oracle-refused, each pinned by a named both-refuse case in tests/test_p23_parser_refusal_parity.py (the TK109/* labels). A differential fuzz over the 15 fga_schemas fixtures found three more classes the census missed (a restriction-type charset, tab-separated type/define heads making the oracle STRICTER by accident, and duplicate type), now twinned too. Four planned twins were INERT (subsumed by the charset / ASK-1 consistency) and were deleted rather than kept untestable. Map with census and 16-row sweep: docs/p23-parser-refusal-parity-2026-10-03.md sec 1b and sec 4. The REASONED JSON empty-name line is fixed under P23 (parse_openfga_json now runs _validate_declared_name).
