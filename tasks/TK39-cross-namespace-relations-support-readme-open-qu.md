---
id: TK39
title: cross-namespace relations support (README open question, no design)
brief:
pri: SOMEDAY
size: L
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed:
---

`README.md:399` — *"cross-namespace relations?"* — in the author's open-question list. Today a relation resolves within its declaring namespace; supporting relations that cross namespaces is an unscoped feature question with no design, no tests and no consumer.

`SOMEDAY` by definition: revisit on a concrete need.

## Traps

⚠ **This is a SCHEMA-shape change, and schemas are static here.** `SchemaV4` is write-once and a new schema means a new store/index (`CLAUDE.md`, `connectedstore/`). Any design has to survive that constraint, and it touches the parser, `compile_ruleset`, both backends and the independent oracle — which parses the DSL itself and must be changed SEPARATELY, or the independence contract is broken.

## Read first

- [`README.md`](README.md)`:399` — the question, in its list
- `zanzibar_utils_v1.py::parse_openfga_schema` — the parser that would have to admit it
- `tests/oracle.py` — the independent oracle, which parses the DSL itself

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-24 (`J-9`, tier 4, sweep-j only); README.md:399 re-read this pass. Unchanged by construction — README.md last changed 5e4b770, 2026-08-16.
