---
id: TK41
title: schema type checking so every relation resolves to a single type (README open question)
pri: SOMEDAY
size: M
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

`README.md:463-464` — *"schema type checking, so that all relations always resolve to a single type?"*, with the author's own alternative in the next line: *"or resolve by relations and do duck-typing checks instead? this is more correct maybe but also more effort"*. Two candidate designs, neither chosen.

`SOMEDAY`: the question is open in the source and there is no forcing need.

## Traps

⚠ **Reads are LENIENT by contract and that is load-bearing.** An out-of-charset or undeclared name simply never matches, on both backends and in the oracle (`CLAUDE.md`, Identifiers). A type checker that turns a non-match into an ERROR changes the read contract and would have to be adjudicated against that rule, not just implemented.

## Read first

- [`README.md`](README.md)`:462-465` — the question and its alternative
- `zanzibar_utils_v1.py::validate_write_identifiers` — the write-side admission that already exists

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-26 (`J-11`, tier 4, sweep-j only); README.md:463-464 re-read this pass.
