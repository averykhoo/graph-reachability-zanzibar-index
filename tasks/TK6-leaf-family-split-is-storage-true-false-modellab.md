---
id: TK6
title: leaf-family split: is storage=True/False modellable as one leaf? unresolved at 4 dates
brief:
pri: LATER
size: S
deps: []
related: [P3, P4]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-09-10
updated: 2026-09-10
closed:
---

Open question §8.2 item 2 of the leaf-family-split scope doc: whether the `storage=True` / `storage=False` leaf distinction needs to be modelled at all, or whether one undifferentiated leaf node per index suffices for `Inv`'s purposes. The doc's own answer is *"this probably **does** need modeling, but it was not verified in this pass"* — Python's reason for the split is TTU stored-parent enumeration, and TTU parents are stored tupleset tuples, a pinned semantic.

**It is flagged unresolved at four separate dates in that one doc** (`:467-468`, `:530-534`, `:772-775`, `:819-822`) and has never been folded into any board row's scope pointer. The doc is ACTIVE-PLAN and the leg it scopes is the one currently executing, so this constrains LIVE work (`P3`/`P4`), not future work — which is why it is `LATER` rather than `SOMEDAY` despite being a question rather than a task.

## Traps

⚠ **Answering it "no" is the expensive direction, and it is not obviously wrong.** One undifferentiated leaf is cheaper to model but throws away the distinction TTU enumeration depends on. Whoever answers must say which theorems the answer buys and which it costs — an unrecorded answer is how this reached four dates.

⚠ **`deps` is deliberately empty.** This scopes `P3`/`P4`; it does not wait on them. Adding a dep edge would invert the direction and make it invisible to `ready` for the wrong reason.

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (the corpus convention. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- [`formal/history/leaf-family-split-scope-2026-08-05.md`](formal/history/leaf-family-split-scope-2026-08-05.md)`:530-534` (§8.2 item 2) — the question, and `:467-468`, `:772-775`, `:819-822` for the other three flags (ACTIVE-PLAN)
- `python scripts/task.py show P3` and `show P4` — the live work this scopes

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-6 (`LFS-1`, tier 2, sweep-f only); anchors re-resolved by COVERAGE.md §C4 and re-read here at formal/history/leaf-family-split-scope-2026-08-05.md:530-534.

### 2026-08-24b

related-edge sweep (trial finding F1): added `related: [P3, P4]`. This row states it scopes LIVE work and 'has never been folded into any board row's scope pointer' -- and P3 is the NOW item. `deps` stays empty for the reason this row already gives (it would invert the direction); `related` is ordering-free, so it encodes the link without touching `ready`.

### 2026-09-10

TK53 disposition 2026-09-10: NOT an append -- SUPERSEDED, and the destination itself is gone.

The adjudication routed this to a `P4` board-row scope pointer at `HANDOFF.md:51`. That location was ABOLISHED by the 2026-09-06 cutover, which turned the note into a one-hop banner. Verified first-hand today: `HANDOFF.md` is 49 lines and contains ZERO table rows, so there is no row to append a pointer to, and the file cannot grow one (its cap is `handoff_lint.py::MAX_LINES`).

The first pass called this ALREADY_CARRIED via the tree's own derived incoming-`related` edges; the adversarial pass overturned that to SUPERSEDED on the stronger ground that the named destination no longer exists in any form. Both agree no prose should be written, which is the operative conclusion.

If the underlying leaf-family-split question still needs a live pointer, it needs a NEW destination decided by a human -- do not re-point it at `HANDOFF.md`. The row stays open.
