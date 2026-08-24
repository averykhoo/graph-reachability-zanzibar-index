---
id: TK51
title: Fail-open detection sensitivity gap in generator-coverage design (dense-regime pass unbuilt)
pri: LATER
size: M
deps: []
related: [TK44]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-08-21c
moved: 2026-08-24b
updated: 2026-08-24b
closed:
---

The generator-coverage subset-driving discipline is tuned for **fail-closed** detection and
detuned for **fail-open**: over-grants hide when the store is nearly empty and only appear as
tuples are added, which is the opposite of how the sabotage-4 masking argument (the discipline's
actual design target) is framed. The design's own author names the fix and prices it:
"A complete design would drive both a sparse and a dense regime per config; at 125 ms/run that
doubles C4 to ~60 s, which is still inside budget and is my recommendation if the fail-open case
is a priority." (`docs/design/generator-coverage/README.md:586-591`, FROZEN 2026-08-16).

Fail-open is this repo's declared house failure mode (`docs/sabotage-procedure.md`, "An
assurance step that fails by PASSING") -- an assurance instrument that is specifically weaker
against that failure mode is exactly the class of gap the sabotage procedure exists to surface.
That is what makes this worth tracking rather than leaving dropped: the recommendation is
concrete, bounded (~60s, inside budget per the author's own numbers), and targets the exact
bug class this project treats as its worst case.

This is distinct from `TK44` (U-29 / `J-27`), which is about the ~30% of pair cells left
UNREACHED at any regime. This item is about the *regime itself* being detection-blind in one
direction (fail-open) even over the cells it does reach.

## Traps

⚠ **Do not conflate with TK44.** TK44 is "some cells are never driven"; this is "cells that
are driven don't catch fail-open as reliably as fail-closed". Fixing TK44 does not fix this.

⚠ **No living carrier exists for this specific recommendation.** `docs/sabotage-procedure.md`
names fail-open as the house failure mode in general but does not cite this design's dense/sparse
proposal. Re-check before assuming it has since been folded into a living doc.

## Read first

- [`docs/design/generator-coverage/README.md`](docs/design/generator-coverage/README.md)`:586-591`
  -- §6 point 7, FROZEN, the source recommendation and cost estimate
- [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) -- house failure mode context
  (general fail-open framing, not this specific gap)
- `tests/test_generator_coverage.py` -- the generator-coverage gate this would extend

## Log

### 2026-08-21c

Provenance. COVERAGE.md 'Dropped, with reasons' (PART 1, J-26; sweep-j only; docs/design/generator-coverage/README.md:586-591, FROZEN, no living carrier). Not on the required 30-entry list (PROOF3.md), so filing was not mandatory -- but COVERAGE.md itself flags it: "J-26 is the one worth a second look before it stays dropped", and grep over the corpus/filing-log.md/notes.md/make_filing_plan.py before this session found neither a task nor a recorded decline. Adjudicated 2026-08-21c: filed rather than declined, because the recommendation is concrete, author-costed (~60s, inside budget), and targets fail-open detection specifically -- this repo's declared house failure mode. TK44 (U-29/J-27) covers unreached pair-cells, a different gap; it does not absorb this one.

### 2026-08-24b

related-edge sweep (trial finding F1): added `related: [TK44]`. This row says fixing TK44 does not fix this; TK44 was blind to it, so closing TK44 could over-claim fail-open coverage.
