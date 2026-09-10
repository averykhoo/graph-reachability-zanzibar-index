---
id: TK38
title: pin the referenced-vs-invisible NodeV4 split (217/49): the definition has to be written first
brief:
pri: HOLD
size: S
deps: []
related: [P16]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-09-10
updated: 2026-09-10
closed:
---

The `NodeV4` endpoint split re-derives as **217/49** (from an earlier 194/41) but is deliberately NOT under the count pin: unlike the edge ledger it has no in-repo implementation to reuse, so "referenced" had to be reconstructed (edge endpoints ∪ residue object nodes ∪ residue `neg`/`upos` subject nodes) and the number is method-sensitive. The recorded instruction is: *"Treat **266** as solid and 217/49 as provisional; pinning it needs the definition written down first."*

`HOLD`: the blocking step is a definition, not a patch, and nobody has committed to one.

## Traps

⚠ **Pinning a method-sensitive number is how you get a pin that agrees with itself by construction.** The definition has to come from something other than the script that measures it, or the pin proves only that the script is deterministic — which is the `ZT-P3-5` family this repo keeps re-learning.

⚠ **Distinct from `P16`.** `P16` widens enumeration/state bounds (K, store counts); this is a node-classification definition. Different rows.

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (the corpus convention. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md)`:560-565` — the provisional split and the instruction
- `formal/conformance/doc_counts.py` — the generated-counts machinery a pin would ride (`formal/verify.sh` step 4e)
- `python scripts/task.py show P16` — the adjacent bounds row this is NOT

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-23 (`CD-4`, tier 4, sweep-d only), distinct from `P16` (K/store-count bounds); anchor re-read this pass at formal/CORRESPONDENCE.md:560-565.

### 2026-08-24b

related-edge sweep (trial finding F1): added `related: [P16]`. Same shape as TK8/P19: 'Distinct from P16' is stated only here, and P16 was the blind end.

### 2026-09-10

LANDED 2026-09-10 (TK53 append) into `formal/CORRESPONDENCE.md` sec 7.1, as a continuation of the SUPERSEDED blockquote in the State-gate-thinness bullet, immediately after "needs the definition written down first."

GATE-ANCHORED destination, so this was verified before writing, not after: `verify.sh lean` resolves every `file::symbol` anchor in this file, and the one anchor the append adds -- `formal/conformance/extractor.py::graph_fragment_ledger` -- resolves at `extractor.py:277`.

The drafted prose claimed a split would be "pinned off graph_fragment_ledger's own classification". False, and caught by the adversarial pass: that function COUNTS `NodeV4` rows and classifies none, which is exactly why the doc says the split has no in-repo implementation to reuse. The landed text says that absence IS the missing implementation, and cites the canonical form of the rule at `docs/sabotage-procedure.md:273` ("recompute X and compare to the recorded X" tests transcription, never classification) rather than re-deriving it -- the draft had garbled that quote into a run-on.
