---
id: TK35
title: sink/source bridge elision for provably-safe shapes -- a spec'd future optimization
pri: SOMEDAY
size: M
deps: []
related: []
parent:
labels: [perf]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed:
---

`bridged_out_shapes` returns every declared object-wildcard shape, with the comment *"(Sink-shape elision is a future optimization; be conservative now.)"* — in the spec at `docs/specs/wildcard-materialization-spec.md:100` and mirrored in the code at `zanzibar_utils_v1.py:376`. A shape that can never be a bridge source (or sink) does not need its bridges materialized. Deliberately unbuilt, and it has never carried an id.

`SOMEDAY`: it is an optimization with no measurement behind it, in an area where being conservative was a deliberate choice.

## Traps

⚠ **Bridges are correctness furniture, not just cost.** Eliding one on a wrong safety argument is a missing grant or a missing revocation; `BL-1` (the released-userset bridge leak) is the recent reminder of how that class actually shows up. Whatever "provably safe" means here has to be provable, and §10 line 324 lists this under non-goals for now.

## Read first

- [`docs/specs/wildcard-materialization-spec.md`](docs/specs/wildcard-materialization-spec.md)`:100` and §10 line 324 — the deferral
- `zanzibar_utils_v1.py::SchemaInfo.bridged_out_shapes` — the conservative implementation and its comment
- `index_v4/wildcard.py::WildcardIndex._ensure_own_bridges` — what elision would skip

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-20 (`W-1`, tier 4, sweep-l only); anchor re-read this pass at docs/specs/wildcard-materialization-spec.md:100 and zanzibar_utils_v1.py:376.
