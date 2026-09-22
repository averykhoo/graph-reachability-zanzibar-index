---
id: TK99
title: MIN_TESTS_ALL is ratcheted by hand; min_tasks_parsed already solved this mechanically
brief: third consecutive raise found pre-existing headroom; a session that only ADDS tests never sees a red
pri: LATER
size: S
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-22
moved: 2026-09-22
updated: 2026-09-22
closed:
---

`MIN_TESTS_ALL` in `formal/verify.sh` is ratcheted BY HAND, and the third consecutive raise
again found pre-existing headroom -- i.e. tests that could have been deleted while the gate
stayed green. Size and provenance are in the floor's own comment in `formal/verify.sh`.

`tasks/config.json`'s `min_tasks_parsed` solved exactly this problem MECHANICALLY on
2026-09-06: `task.py::ratchet_min_parsed` raises the floor to `max(floor, files on disk)`
after every `new`, never lowers it, so headroom cannot re-accumulate. That key's
`_provenance` string records FOUR consecutive sessions forgetting the manual step before
the mechanical fix landed, and calls itself "the evidence that a note in a provenance string
is not sufficient to cause it".

The gate has no equivalent. A session that only ADDS tests never sees a red to remind it, so
the floor drifts below the live count silently and the zero-headroom property -- the entire
point of the floor -- is lost until someone re-measures by hand.

Carried in `HANDOFF.md`'s `## Still owed` as "Unfiled" until the 2026-09-22 disposition
filed it here.

## Traps

- (!) **Adding tests must stay free; only LOWERING is the defect.** Any mechanical ratchet
  must raise and never lower, exactly as `ratchet_min_parsed` does. A ratchet that can lower
  the floor to make a run green IS the thing the floor exists to catch.
- (!) **`MIN_CONF_ALL` is the same shape** and should be decided together, not separately.
- (!) `CLAUDE.md` states that these floors have ZERO headroom deliberately; do not
  reintroduce headroom as a way to stop the reminder firing.
- (!) **Sabotage it** (`docs/sabotage-procedure.md`): deleting a single test must still turn
  the gate red after the ratchet lands, and a ratchet that runs must not be able to paper
  over a genuine loss of coverage.

## Read first

- `formal/verify.sh` -- the `MIN_TESTS_ALL` / `MIN_CONF_ALL` floors and the floor's own
  provenance comment (the only place the value belongs; do not restate it in prose).
- [`config.json`](config.json) -- `min_tasks_parsed`'s `_provenance`, which is the worked
  precedent for mechanising a hand-ratcheted zero-headroom floor, including what it cost to
  leave it manual.
- `scripts/task.py::ratchet_min_parsed` -- the landed mechanical form, and
  `tests/test_tasktool.py::test_new_ratchets_the_floor_to_the_measured_total_and_never_lowers_it`
  for how it was pinned (with an instrument control).

## Log
