---
id: TK35
title: sink/source bridge elision for provably-safe shapes -- a spec'd future optimization
brief:
pri: SOMEDAY
size: M
deps: []
related: []
parent:
labels: [perf]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-09-10
updated: 2026-09-10
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

### 2026-09-10

LANDED 2026-09-10 (TK53 append) -- but RE-HOMED, and that is the part to read.

The adjudication named `docs/specs/wildcard-materialization-spec.md` sec 2.3 as the destination. `docs/README.md:122-124` says `docs/specs/` is held FROZEN AT LANDING by hand (nothing walks it, so the rule is not enforced -- which is why an append there looks legal and is not). Writing dated retrospective prose into a frozen spec body would breach that rule, and `CLAUDE.md` names `docs/spec-deviations.md` as the home for implementation divergences. So it landed there as a dated entry instead.

The drafted prose had two factual errors, both caught adversarially and both fixed before writing. (1) It said the BL-1 leak "changed a `lookup` answer rather than merely costing an edge" -- `docs/spec-deviations.md:275` records **Severity: STATE-ONLY** and :279 "Not an authorization fail-open". (2) It claimed lifecycle, not creation, is where this design's bugs land -- refuted by the `## 2026-08-09` entry, whose root cause (:721) is `_ensure_bridges` never interning a crossing middle, i.e. the creation side.

Verified first-hand: spec `:104` carries the unqualified "harmless" sentence, and `zanzibar_utils_v1.py:354` mirrors it verbatim -- both now covered by the entry.
