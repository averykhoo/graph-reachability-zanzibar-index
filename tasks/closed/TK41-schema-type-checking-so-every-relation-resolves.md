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
moved: 2026-08-29b
updated: 2026-08-29b
closed: 2026-08-29b
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

### 2026-08-29b

APPENDED as a NEW section 'Reads are lenient -- a cross-backend contract, not a per-backend default'. The filed destination was WRONG and verification caught it: the adjudication said 'append to the existing lenient-reads material' in decision-log.md, and no such material exists -- the file's only 'lenient' token is ':200' lenient forall=>exists, the wildcard VACUITY MODE, a different sense entirely, and also the anchor TK4 targets. Appending there would have fused two unrelated concepts under one word, so the new section carries an explicit warning not to confuse them. Leniency verified in CODE on all three surfaces, which is the load-bearing part: index_v4/wildcard.py:639-647 (denies, does not raise), setengine/engine.py:1075-1078 (missing AST entry -> False), tests/oracle.py:367-370 (same construct). Uniform, so the collision is real: a type checker that raises changes the read contract on three surfaces at once and the oracle's copy must change separately or independence breaks.
