---
id: TK50
title: the _bumped residue-version channel is a second dirty-key source with no Lean model
brief:
pri: HOLD
size: M
deps: []
related: []
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-09-10
updated: 2026-09-10
closed:
---

`formal/CORRESPONDENCE.md:436-452` records a second dirty-key source with no Lean model: `self._bumped`, appended by `index_v4/processor.py::DeltaProcessor._store_residue` on every residue write and drained into a fan-out. The consequence is stated plainly at `:352` and in §7: **T5 (`runCascade2_no_abort` / `cascade2_drains`) is a claim about a STRICTLY WEAKER abort condition than the one Python ships**, because Python's abort fires iff the outbox is empty AND the pending `_bumped` fan-out is empty. So T5 does not entail *"Python's abort is dead code"*, which is how it is easy to read it.

Not a crash or a correctness bug — a version bump with no outbox row would abort a real transaction in a case the theorem does not cover, i.e. it fails loudly and in the safe direction. It is a live gap in **what a landed theorem actually proves**, and it has no id.

**Filed against COVERAGE.md's drop.** The consolidated list dropped this as frozen-provenance with no living carrier; the carrier is `formal/CORRESPONDENCE.md`, which is the model↔code map and is maintained (its anchors are gate-checked). Recorded here so the drop is visible and reversible rather than silent.

## Traps

⚠ **The risk is a citation, not a crash.** The failure mode is someone quoting T5 as "the abort is dead code" in a review or a doc. If this row is closed by ACCEPTING the gap rather than modelling it, the acceptance has to land next to T5's statement, not only in a task Log.

⚠ **Appendix lead A10 changes the fan-out this channel feeds.** That lead would make residue bumps carry granularity instead of always escalating to a full reconcile — which is the same channel, and it already owes a Lean update. Sequence them, or the model gets rewritten twice.

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (the corpus convention. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md)`:436-452` — the ★ NEW entry (`ZT-P4-3a`), and `:352` — the T5 row that carries the weaker-abort warning
- `index_v4/processor.py::DeltaProcessor._store_residue` — where `_bumped` is appended, and `index_v4/processor.py::DeltaProcessor._run_cascade` — where it is drained
- `formal/lean/ZanzibarProofs/GraphIndex/CascadeStrata.lean::runCascade2_no_abort` — the theorem whose scope this bounds

## Log

### 2026-08-21b

**Provenance.** inventory-formal.md MISS #4, citing formal/CORRESPONDENCE.md §7.1 ("★ NEW -- the `_bumped` residue-version channel is a SECOND dirty-key source with no model", `ZT-P4-3a`). COVERAGE.md DROPPED it as frozen-provenance; re-instated here because the carrier is CORRESPONDENCE.md, and the anchors (`:352`, `:436-452`) resolve in the current tree.

### 2026-09-10

LANDED 2026-09-10 (TK53 append) into `formal/CORRESPONDENCE.md` sec 7.1, as a continuation of the `_bumped` residue-version-channel bullet.

The prior sweep called this ALREADY_CARRIED and the adversarial pass OVERTURNED it: the channel and T5 legs ARE carried, but the second trap -- that a pending perf lead rewrites what this entry declares unmodelled -- was carried nowhere.

I then had to correct the REFUTER too, which is why this is a first-hand write and not a transcription. Its revised draft said A10 "would propagate granularity through the residue-bump fan-out", i.e. that A10 touches the `_bumped` channel directly. That is NOT what the audit says. `docs/perf-round6-audit-2026-08.md:857-862` says A10's sketch names the sec 5.2 invalidation rule and routes computed dependents onto `::DeltaProcessor._reconcile_subject`, a DIFFERENT sec 7 gap with no Lean counterpart -- so A10 makes an already-logged modelling gap the cascade default. That weaker, accurate claim is what landed.

Verified first-hand: :857 carries "the only one of the sixteen filed `algorithm change: yes`" verbatim, and `grep -r 'A10' formal/` returns ZERO matches, so the "no file under formal/ names A10" clause is true as written.
