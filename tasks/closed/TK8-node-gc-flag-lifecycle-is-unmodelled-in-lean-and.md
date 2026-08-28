---
id: TK8
title: node GC / flag lifecycle is unmodelled in Lean, and TWO named bugs landed inside it
pri: LATER
size: L
deps: []
related: [P19]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-29b
updated: 2026-08-29b
closed: 2026-08-29b
---

Lean models the node-flag RULE and explicitly disclaims the collection ALGORITHM — `ReconcileDiff.lean` and `Cascade.lean` both say *"node GC is a modeled-away optimization"* (`formal/CORRESPONDENCE.md:975-996`). The argument for the exclusion is the usual one and is not silly. What makes it a filed row rather than a declared boundary is the empirical record: **two named correctness bugs have now landed inside that one unmodeled region** — `ZT-P0-1` (the unsound `_keys_referencing` elision) and, added to the map on 2026-08-21, `BL-1` (the released-userset bridge leak, found by the hypothesis campaign).

Two bugs in one modeled-away region is an argument for filing it, not evidence it is handled. The deliverable is not necessarily a model — it may be a recorded decision that the differential + hypothesis nets are the intended net, written where the next reader will find it — but the current state is an exclusion whose justification the evidence has moved against.

## Traps

⚠ **Distinct from `P19` and from the cheap-path reconcile row.** `P19` is the READ surfaces; the `reconcile_subject` cheap path is its own filed row. Do not merge them: three separate regions, three separate arguments.

⚠ **The map records the bugs; it does not record what they imply.** `CORRESPONDENCE.md` §8 is explicit that the anchor gate keeps the map *navigable, not true*. Adding a third bug to the list is not progress.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (the corpus convention; `migrate.py::check_formal_pointer` enforces it for the generated rows and 18/18 formal tasks satisfy it)
- [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md)`:975-996` — the exclusion, and `:983-986`/`:992` for the two landed bugs inside it
- `python task.py show ZT-P0-1` and `show BL-1` — the two bugs
- `python task.py show P19` — the adjacent, separately tracked read-surface gap

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-8 (`CD-6`, tier 2, sweep-d only), distinguished from `P19` (read surfaces). STRENGTHENED 2026-08-21 per COVERAGE.md §C4: formal/CORRESPONDENCE.md:983-986 now names `BL-1` beside `ZT-P0-1`.

### 2026-08-24b

related-edge sweep (trial finding F1): added `related: [P19]`. 'Distinct from P19 ... do not merge them' is stated here and nowhere on P19, so the blind end was the one at risk of merging them.

### 2026-08-29b

APPENDED to docs/latent-gaps.md, section 'Latent, but owned by another doc'. Verified first-hand: both bugs are in one CORRESPONDENCE.md bullet at :982-1003 (ZT-P0-1 :991/:998, BL-1 :992/:999), and the 'two bugs in one region' sentence is :996-997. The bullet was justified because the home does NOT read as open: sec 7.3 sits under sec 7 'Known intentional divergences (model != code, by design)' and its preamble at :862-863 says 'None is a bug'. The new bullet carries the inference (the exclusion's justification has moved) and states the deliverable is an ADJUDICATION, not necessarily a model.
