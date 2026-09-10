---
id: TK36
title: delta post-processing layer to expand symbolic wildcard PermissionDeltas -- no id anywhere
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

`docs/specs/wildcard-materialization-spec.md:259`: *"`PermissionDelta`s that mention a wildcard node id are **symbolic** ('everyone of shape S gained/lost X'). Pass them through untouched and document this in the README delta section; expansion is a future post-processing layer, out of scope."* The pass-through shipped; the expansion layer has no id and no later doc tracking it.

`SOMEDAY`: a consumer that needs expanded deltas is the concrete need that would justify it, and none exists.

## Traps

⚠ **"Never enumerate a marker into concretes" is a design invariant elsewhere in the same spec** (`:258`, for `lookup`/`lookup_reverse` results). An expansion layer is exactly that enumeration, done deliberately and in one place. Whoever builds it must say why the invariant holds for reads and not here — or the layer will be copied into a read path by the next reader.

## Read first

- [`docs/specs/wildcard-materialization-spec.md`](docs/specs/wildcard-materialization-spec.md)`:259` and §10 line 324 — the deferral
- `README.md` delta section — where the symbolic pass-through is documented

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-21 (`W-3`, tier 4, sweep-l only); anchor re-read this pass at docs/specs/wildcard-materialization-spec.md:259.

### 2026-09-10

LANDED 2026-09-10 (TK53 append), RE-HOMED to `docs/spec-deviations.md` for the same reason as TK35: `docs/README.md:122-124` holds `docs/specs/` frozen at landing by hand, so a dated append into the spec body is not the right form.

The drafted prose said sec 10 keeps expansion a non-goal "until a consumer that actually needs expanded deltas exists". Caught adversarially and dropped: `wildcard-materialization-spec.md:324` lists it among Non-goals with NO condition attached -- the consumer rationale is this task row's, not the spec's. Verified :324 first-hand.

The landed text keeps the half that is actually load-bearing and adds the stronger second reason the read path has since grown: `index_v4/wildcard.py::WildcardIndex.lookup_reverse` fences leaf families because a leaf family is storage-internal (`wildcard.py:864`). The sec 6 invariant it is in tension with, "Never enumerate a marker into concretes", is at `:258` -- grepped.
