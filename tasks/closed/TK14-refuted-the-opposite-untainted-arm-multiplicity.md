---
id: TK14
title: REFUTED: the opposite untainted-arm multiplicity divergence closed 2026-08-08 (rewriteClosure)
pri: LATER
size: S
deps: []
related: []
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed: 2026-08-21b
---

Filed as a **CLOSED record.** COVERAGE.md carried this as an open tier-2 modelling gap: a second, OPPOSITE untainted-arm multiplicity divergence — model `rewriteClosure` does not dedupe where `zanzibar_utils_v1.py::RuleSet.apply` does — recorded only in `RemoveOccCount.lean`'s header, with *no corpus exercising it today*. Its own entry asked for adjudication against the 2026-08-08 dedup closure before filing. Adjudicated: **the dedup landed, and it landed as the model-side fix for exactly this divergence.**

`GraphIndex/RulesWrite.lean:122` now reads `(rewriteClosureRaw S t).dedup`, with the docstring *"Mirrors `zanzibar_utils_v1.py::RuleSet.apply`'s worklist dedup (its `processed` set), so a reconvergent schema does not over-count edge multiplicity."* `RemoveOccCount.lean`'s header records the same, in the strongest available form: it says the file's own headline sentence *"was FALSE when it was written, and is TRUE as of 2026-08-08"*, and that two corpora (`reconvergent_diamond`, `reconvergent_derived`) now pin it — so the "no corpus exercises it" half is stale too.

## Traps

⚠ **Same root cause as the refuted `SD-C1` item: a dated entry read as current state.** `docs/spec-deviations.md`'s 2026-07-29 entry describes the divergence in the present tense; the fix landed ten days later in the Lean tree, and nothing updated the prose. The Lean file was the authority and it says so plainly — read the source, not the ledger.

⚠ **Do not confuse this with the OTHER multiplicity divergence, which is OPEN.** The derived-arm one (Python does a presence diff where the model does not; faithful fix is a `¬ hasEdge` conjunct on `reconcileKeyDR`'s fold guard) is separately filed and still open. Two opposite divergences on two different arms; one closed, one not.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (the corpus convention; `migrate.py::check_formal_pointer` enforces it for the generated rows and 18/18 formal tasks satisfy it)
- `formal/lean/ZanzibarProofs/GraphIndex/RulesWrite.lean::rewriteClosure` — the dedup, at `:115-122`
- `formal/lean/ZanzibarProofs/GraphIndex/RemoveOccCount.lean`:1-35 — the header that records the divergence AND its closure
- [`docs/spec-deviations.md`](docs/spec-deviations.md)`:1049-1052` — the 2026-07-29 sentence the sweep read as live

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-14 (`SD-C5`, tier 2, sweep-c only), which itself said it *"needs adjudication against the 2026-08-08 rewriteClosure-dedup closure ... before filing"*. Adjudicated this pass against the Lean source; the divergence is closed.

CLOSED ON ARRIVAL as a disproof record. COVERAGE.md U-14 (SD-C5) filed "model rewriteClosure does not dedupe where RuleSet.apply does" as an open modelling gap, quoting docs/spec-deviations.md:1049-1052 (a dated 2026-07-29 entry) and RemoveOccCount.lean's header, and noted it needed adjudication against the 2026-08-08 dedup closure before filing. Adjudicated 2026-08-21 by reading the Lean source: formal/lean/ZanzibarProofs/GraphIndex/RulesWrite.lean:122 defines rewriteClosure S t = (rewriteClosureRaw S t).dedup, docstring at :115-117 "Mirrors zanzibar_utils_v1.py::RuleSet.apply's worklist dedup (its processed set), so a reconvergent schema does not over-count edge multiplicity"; RemoveOccCount.lean:22-35 records that the file's headline sentence "was FALSE when it was written, and is TRUE as of 2026-08-08", that the measured divergence was lean=2 python=1 on `a := b or c ; b := d ; c := d`, and that two corpora (reconvergent_diamond, reconvergent_derived) now pin it -- so the "no corpus exercises it" half of the finding is stale as well. formal/conformance/derived_arm_multiplicity.json exists on disk. No work is owed. This is the SECOND item in this batch refuted by the same mechanism as SD-C1: a present-tense problem statement inside a dated ledger entry, read as current state.
