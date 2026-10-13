---
id: TK137
title: DSL parsers silently accept shapes OpenFGA refuses (schema X.Y header, [a] or [b], or+but not mix)
brief: both parsers accept schema 1.2 headers, [a] or [b], unparenthesised or+but not; OpenFGA refuses
pri: LATER
size: S
deps: []
related: []
parent:
labels: []
source: docs/openfga-claims-audit-2026-10-13.md
source_hash:
created: 2026-10-13c
moved: 2026-10-13c
updated: 2026-10-13c
closed:
---

Found by the 2026-10-13 OpenFGA claims audit; probe and sources in
`docs/openfga-claims-audit-2026-10-13.md` sec 4 item 1 (PROBE, first-hand).

Both checked parsers (`src/zanzibar/schema/parser.py::parse_schema_ast`, oracle twin)
silently accept: any `schema X.Y` header (`1.2`, `9.9`; the JSON front end refuses all but
1.1), no header at all, `define viewer: [user] or [doc]` (two direct blocks), and an
unparenthesised `[user] or a but not b`, read as `([user] or a) but not b`. OpenFGA's
grammar (`OpenFGAParser.g4::relationDefPartials`) refuses the last two.

Decide per shape: refuse (with the REFUSED SHAPE / WHY / INSTEAD block, in BOTH parsers,
`tests/test_p23_parser_refusal_parity.py`), or keep and document as an extension. The
silent header is the sharpest: a `schema 1.2` model that uses 1.2 features would parse
here with different meaning or fail confusingly. Any new refusal is a breaking change for
schemas that parse today, so it wants a CHANGELOG line.

## Read first

- `docs/openfga-claims-audit-2026-10-13.md` (sec 2 fact 2, sec 4 item 1).
- `src/zanzibar/schema/parser.py::parse_schema_ast`; oracle twin `tests/oracle.py::parse_schema_ast`.

## Log
