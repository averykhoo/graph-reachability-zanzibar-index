---
id: TK9
title: reconcile_subject's cheap path is unmodelled and has grown real logic twice
pri: LATER
size: M
deps: []
related: []
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-29b
updated: 2026-08-29b
closed: 2026-08-29b
---

Lean models only the full-object reconcile (`reconcileStarsKey`/`reconcileStarsKeyD`). The per-subject cheap path has no model and has grown real logic twice: *promote-on-record* (2026-07-17) and *escalation to the full reconcile* (2026-07-26, the `ZT-P0-1`/`ZT-P0-2` fix). `formal/ARCHITECTURE.md:759-774` states the consequence plainly — *"the gap is no longer plausibly characterizable as 'a thin fast path'"* — and `CORRESPONDENCE.md` §7.1 puts it as *"a per-subject path that can escalate to a full reconcile and can mutate node flags is a real algorithm, and none of it is in the model."*

Both landed fixes are pinned Python-side by regression tests, so this is a modelling gap, not a live defect. It is filed because the justification for the exclusion ("a thin fast path") is the thing that stopped being true.

## Traps

⚠ **Adjacent to, and distinct from, the node-GC region.** Both are `CORRESPONDENCE.md` §7.1 bullets and both are unmodeled; they are different code and different arguments. Filed separately on purpose.

⚠ **Read `formal/ARCHITECTURE.md` with suspicion.** It carries no liveness banner and the sweep found several of its claims stale (it still presents the T2a fork as undecided; it was decided 2026-08-05). Its *statement of this gap* was re-confirmed, but check anything else there against the code.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (the corpus convention; `migrate.py::check_formal_pointer` enforces it for the generated rows and 18/18 formal tasks satisfy it)
- [`formal/ARCHITECTURE.md`](formal/ARCHITECTURE.md)`:759-774` — the gap and the 2026-07-26 update that grew it
- [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) §7.1, third bullet — the same gap in the map
- `index_v4/processor.py::DeltaProcessor.reconcile_subject` — the unmodeled code

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-9 (`ARCH-H-10`, tier 2, sweep-h only) and inventory-formal.md MISS #5, independently. Anchor re-read this pass at formal/ARCHITECTURE.md:759-764.

### 2026-08-29b

APPENDED to docs/latent-gaps.md, same section, as a bullet explicitly distinct from the node-GC one. Verified: reconcile_subject is the public wrapper at index_v4/processor.py:798 and _reconcile_subject the body at :803 -- CORRESPONDENCE cites the underscore form, so the bullet names both or the anchor looks like a mismatch. Both growths itemized at CORRESPONDENCE.md:483-486 and :487-491; the expired justification 'a thin fast path' is verbatim at formal/ARCHITECTURE.md:776. Home says nothing is owed (ARCHITECTURE.md:774-776 'does not widen the gap's disposition'), which is what justified the bullet.
