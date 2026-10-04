---
id: TK101
title: object-wildcard WRITES are unenumerable: _tuple_space emits '*' only as a subject
brief: censused 2026-09-22c as hole H4; found in TK71's traps 2026-09-16b and never owned
pri: NOW
size: M
deps: []
related: [TK71, TK94, P25]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-22c
moved: 2026-10-04d
updated: 2026-10-04d
closed:
---

## What it is

**MEASURED by READ (2026-09-22c, census leg of [`docs/goal-census-2026-09-22.md`](../docs/goal-census-2026-09-22.md) §2, hole H4).**
`formal/conformance/test_conformance_enum.py::_tuple_space` emits `"*"` only in the
SUBJECT position; object names come from `_POOL`. So **no enumerated store ever contains
an object-wildcard WRITE** — the enumerated arm cannot reach the shape at all, in any
schema, at any bound.

This was found on-row inside `TK71`'s traps (2026-09-16b) and has never had an owner of
its own, which is why it is invisible to `ready` and to the board.

## Why it is worth a row

The class is not exotic: `object_wildcard` is the ONE corpus schema of 26 that sits
outside `GRAPH_FRAGMENT`, and object wildcards have their own materialization path
(`index_v4/wildcard.py`'s `*` bridges) plus a dedicated scope-rejection family
(`zanzibar_utils_v1.py::_reject_object_wildcard_scope`). The enumerated arm is the one
that reasons over ALL stores up to a bound rather than over transcribed fixtures, so a
shape it cannot emit is a shape no exhaustive argument covers.

`W4Fragment.bareStar` is one of the SILENT seven
(`formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE` classifies it
`MIXED`, and its LOUD sub-case is narrower than it looks: only a wildcard OBJECT on an
UNDECLARED shape raises). So on this shape the Lean side is narrow AND the enumerated
differential is empty.

## First action

Decide the cheaper of the two, then measure rather than predict:

1. **Widen `_tuple_space`'s object range** to include `"*"` for declared wildcard shapes
   only. ⚠ This MULTIPLIES the enum bound — size it against `MIN_CONF_ALL` and the
   `test_conformance_enum.py` runtime BEFORE writing it, exactly as `TK94` is required to.
2. **A separate bounded enumeration** restricted to object-wildcard stores, so the cost
   is additive rather than multiplicative on the main space.

Then say, per arm, WHICH branch newly runs. A new arm that passes is not evidence it ran.

## (!) Traps

- **(!) `MIN_CONF_ALL` / `MIN_TESTS_ALL` have ZERO headroom.** Re-measure the floors with
  `pytest <dir> -q --collect-only`, never estimate them.
- **(!) Do not reach the shape by adding it to `_POOL` generally.** Object wildcards are
  admitted only on DECLARED shapes (`object_wildcard_shapes`); an undeclared one RAISES,
  so a naive widening turns most of the new space into refusals and buys nothing. That
  refusal is itself the MIXED field's only LOUD sub-case.
- **(!) Check the arm is not silently degraded to 3-way.** `tests/parity.py::ParityEngine`
  drops the graph backend on an `UnsupportedByGraphIndex` (`graph_drop_reason`), which
  makes a differential look green while comparing fewer backends.

## Read first

- [`docs/goal-census-2026-09-22.md`](../docs/goal-census-2026-09-22.md) §2 — where this
  was censused and how it ranks against the other holes.
- `formal/conformance/test_conformance_enum.py::_tuple_space` — the emitter, first-hand.
- `tasks/closed/TK71-test-conformance-enum-py-asserts-no-admission-su.md` traps (closed 2026-09-27b) — where the observation was originally recorded.
- `formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE`, field `bareStar` —
  the Lean-side narrowness on the same shape, and the note naming its LOUD sub-case.

## Log

### 2026-10-04d

PROMOTED NEXT -> NOW 2026-10-04d, following the user's 2026-10-04c order (TK116, then TK101 and TK121). A precedent from TK116: tests/test_tk116_oracle_only_setengine.py::_pool emits a '*' OBJECT on every declared relation in the CLOSED object-wildcard shapes (SetEngine.schema_info.object_wildcard_shapes), which is the shape this row says _tuple_space never produces. It found a real set-engine lookup fail-open on its first run, so object-star writes are worth enumerating.
