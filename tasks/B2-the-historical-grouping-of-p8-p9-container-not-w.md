---
id: B2
title: the historical grouping of P8 + P9 (container, not work)
pri: LATER
size: ?
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: acked-no-row
created: 2026-08-16
moved: 2026-08-16
updated: 2026-08-21
closed:
---

The historical grouping of `P8` (write `W4WitnessSelfRef`) and `P9` (lift the remove-gate exclusion). `HANDOFF.md` records it as surviving purely as that grouping after `B1` was retired, so it carries no work of its own: it is done exactly when both children are. Nothing here should be worked directly — promote a child instead.

## Traps

⚠ **A parent is not a dependency.** `P8` and `P9` are independently ready; `B2` blocks neither. If a future session gives `B2` `deps`, it is modelling the wrong edge.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule; enforced by `migrate.py::check_formal_pointer`, not merely stated)
- [`PROOF_STATUS.md`](formal/history/PROOF_STATUS.md) 2026-08-08 §6

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. `B2` had no board row of its own — it is reconstructed from `HANDOFF.md`’s "`B2` survives as the historical grouping of `P8` + `P9`" line, and `moved` is borrowed from its children. **`pri` and `size` are NOT a ranking**: nobody ever ranked or sized `B2`. It is OPEN, and lint requires both fields on an open row (a row an unassigned session could pick up has to sort), so this carries the two least-asserting values the enums have — `LATER` (`task.py new`’s own default) and `?`, which is the size enum’s literal "unsized". The previous `size: M` was invented and has been removed.

No row on HANDOFF.md, and that is correct: B2 is prose-only there -- the board names it once, in the retired line's trailing clause "B2 survives as the historical grouping of P8 + P9", which is a note about what the id MEANS, not a ranked row. It is also not retired: handoff_lint.py's line-by-line harvest truncates that span, so the id the clause names is deliberately excluded from the retired set (verified: the harvest yields B1, BL-1, BL-2, GS-1, GS-2, HS-1..HS-4, P1, P2, ZT-* and no B2). So there is nothing to close and nothing to file; the absence of a row is the expected steady state.
