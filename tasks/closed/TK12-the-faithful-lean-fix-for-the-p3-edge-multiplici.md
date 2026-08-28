---
id: TK12
title: the faithful Lean fix for the P3 edge-multiplicity divergence was never attempted
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

On the derived arm the Lean model over-counts edge multiplicity: Python does a presence diff on the reconcile fold where the model does not. The faithful fix is named and narrow — **mirror the presence diff by adding a `¬ hasEdge` conjunct to `GraphIndex/CascadeStrata.lean::reconcileKeyDR`'s fold guard** — and it was *"left open, deliberately"*: it ripples through the edge-characterisation and settledness stacks.

This addresses the BASELINE `n → 2n` derived-edge stacking artifact. `P3` covers the closed headline finding, not this residual, and sweep-n's "captured (own doc: `CORRESPONDENCE` §7.2 item 6)" is the error worth naming: **a doc section is not a board id.** `docs/latent-gaps.md` exists precisely to index what is open and it points here, so the carrier is live.

## Traps

⚠ **DO NOT instead make `GraphIndex/Write.lean::GraphState.admitEdge` reject a present edge.** That global version breaks the untainted arm, which is load-bearing for `untOccCount` / erase-one removal. Both `latent-gaps.md:163-166` and `spec-deviations.md:1047-1049` carry this warning; it is the obvious wrong fix and it is written down twice for a reason.

⚠ **Distinct from the second, OPPOSITE untainted-arm divergence** (model `rewriteClosure` vs `RuleSet.apply` dedup), which is CLOSED — the dedup landed 2026-08-08. See the closed record filed alongside this one. Do not let the two blur.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (the corpus convention; `migrate.py::check_formal_pointer` enforces it for the generated rows and 18/18 formal tasks satisfy it)
- [`docs/latent-gaps.md`](docs/latent-gaps.md)`:158-166` — the live index entry, including the do-not-do-this trap (LIVING)
- [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md)`:687-689` — §7.2 item 6, *"Still open, deliberately"*, naming the fix
- [`docs/spec-deviations.md`](docs/spec-deviations.md)`:1045-1052` — the filing entry, and `formal/history/echain-widening-plan-2026-07-28.md:446-449`
- `python task.py show P3` — the closed headline finding this is the residual of

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-12 (`SD-C4` = `NEW-1`, tier 2) — the most-corroborated item in the sweep: three buckets (c, i, n), three documents. Survives the frozen-provenance filter because docs/latent-gaps.md (LIVING) carries it; re-read this pass at latent-gaps.md:158-166.

### 2026-08-29b

WRITTEN OFF against a living carrier, and the write-off survived an adversarial refutation attempt. docs/latent-gaps.md:176-184 is bullet one of section 'Latent, but owned by another doc', whose preamble states the section exists so the file is a complete index of what is open. It carries the finding AND its wrong-fix trap (do not make GraphState.admitEdge reject a present edge -- that breaks the untainted arm, load-bearing for untOccCount). Nothing is lost by the tasks/ deletion. Disposition recorded in docs/history/tk-findings-adjudication-2026-08-29.md.
