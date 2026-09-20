---
id: TK90
title: test_conformance_bulk_state.py advertises an I14 coverage hole that P22 closed
brief: the I14 loop is "pinned by NOTHING" -- P22 pinned it 2026-09-16; a gated module advertises a closed hole
pri: NEXT
size: S
deps: []
related: [TK78, TK88, P22]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-20
moved: 2026-09-20
updated: 2026-09-20
closed:
---

`formal/conformance/test_conformance_bulk_state.py`'s module docstring tells the reader that
`index_v4/bulk_build.py`'s I14 crossable-middle loop has no coverage at all:

> *"The I14 loop is pinned by NOTHING: the same sabotage left every `build_index` caller in
> `tests/` green, because no bulk-built corpus in the tree has a crossable shape."*

**Both halves of that sentence are false, and have been since `P22` landed on 2026-09-16.**

`READ 2026-09-20`, `tests/test_bulk_build.py`:

* `::_owc_star_ttu_tuples` (`:389`) is a corpus whose `schema_info.crossable_shapes` is
  NON-EMPTY, wired into `_CORPORA` (`:434-445`) — so a bulk-built corpus with a crossable
  shape does now exist in the tree.
* `::_assert_r4bf_features` clause (g) (`:609-640`) pins the loop's PRODUCT structurally (the
  `viewer(folder, f1)` middle and its two bridges), and mechanically refuses (`:639`) a
  corpus whose concrete `viewer(folder, _)` grants would MASK the loop — which is the trap
  `P22` was actually about ([`docs/p22-i14-corpus-masking-2026-09-16.md`](../docs/p22-i14-corpus-masking-2026-09-16.md)).

The paragraph is stamped *"Measured 2026-09-06"* and was true then. Nothing walks it, so it
has said the opposite of the truth for four days inside a GATED module.

**Why this is worth a row.** It is [[TK88]] pointed the other way. `TK88` is a module
announcing a REDNESS it no longer has, so a genuine red reads as normal. This is a module
announcing a HOLE it no longer has — and the cost is higher, because the hole it advertises
is exactly the kind a session goes looking for: the next one planning offline-bootstrap
assurance reads "pinned by NOTHING", and either re-does `P22`'s work or files it a third
time. It was found this way, during `TK78`'s verification pass.

**The fix, and the thing NOT to do.** `docs/README.md`'s remedy: append a dated correction
line at the site naming `P22`, `_owc_star_ttu_tuples` and clause (g). **Do not delete the
2026-09-06 measurement** — it is the provenance for why the conformance corpora were built
the way they were, and the surrounding "what this does NOT cover" list is the most useful
artifact in the module. The other three entries in that list were re-checked on 2026-09-20
and all three still hold (see the `TK78` map §5a).

## Read first

- [`docs/tk78-offline-bootstrap-audit-2026-09-20.md`](../docs/tk78-offline-bootstrap-audit-2026-09-20.md)
  Corrections + §5a — where this was found, and the verdict on the other three declared gaps.
- [`docs/p22-i14-corpus-masking-2026-09-16.md`](../docs/p22-i14-corpus-masking-2026-09-16.md) —
  what actually closed the hole, and why wiring in a corpus was not sufficient.

## Log
