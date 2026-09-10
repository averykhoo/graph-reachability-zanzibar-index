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
moved: 2026-09-10
updated: 2026-09-10
closed:
---

`README.md:399` — *"cross-namespace relations?"* — in the author's open-question list. Today a relation resolves within its declaring namespace; supporting relations that cross namespaces is an unscoped feature question with no design, no tests and no consumer.

`SOMEDAY` by definition: revisit on a concrete need.

## Traps

⚠ **This is a SCHEMA-shape change, and schemas are static here.** `SchemaV4` is write-once and a new schema means a new store/index (`CLAUDE.md`, `connectedstore/`). Any design has to survive that constraint, and it touches the parser, `compile_ruleset`, both backends and the independent oracle — which parses the DSL itself and must be changed SEPARATELY, or the independence contract is broken.

## Read first

- [`README.md`](../README.md)`:399` — the question, in its list (the ROOT README, 660 lines; `tasks/README.md` is a different 86-line file and this link used to resolve to it)
- `zanzibar_utils_v1.py::parse_openfga_schema` — the parser that would have to admit it
- `tests/oracle.py` — the independent oracle, which parses the DSL itself

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-24 (`J-9`, tier 4, sweep-j only); README.md:399 re-read this pass. Unchanged by construction — README.md last changed 5e4b770, 2026-08-16.

### 2026-09-10

LANDED 2026-09-10 (TK53 append) as a nested sub-bullet under `* cross-namespace relations?` in the root `README.md` notes list.

The first pass put it at :405, a free-floating paragraph before the mermaid fence, which reads as an annotation of the WRONG bullet (`* default condition exists?`). The adversarial pass caught that and the placement moved to :400, directly under the bullet it annotates, with the 4-space sub-bullet indent this section already uses (verified at README.md:432-436).

Two other draft defects were dropped rather than written: a self-contradicting "lands in four places at once" followed by a five-item list (the source row deliberately carries no count), and a verbatim restatement of `SchemaV4 is write-once` that already has a home in this same file.

Not superseded: `namespace` appears in README only at :399 and inside the mermaid diagram, so the question is schema-shaped and is not answered by existing type-crossing usersets.
