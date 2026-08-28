---
id: TK7
title: relNameOK admits the EMPTY relation name, so leafPublic BARE = "" -- constrains unwritten Lean
pri: HOLD
size: S
deps: [P3]
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

`formal/lean/ZanzibarProofs/Core/Schema.lean:64` is `def relNameOK (name : String) : Prop := ¬ name.contains '.'`, which admits `""`, and `WF` (`:70-71`) carries only the `relNames` clause — no nonempty-name clause. `leafPublic` takes the dot-free prefix, so `leafPublic BARE = ""`, and a pathological schema declaring a derived relation named `""` would make bare-subject nodes classify as `LeafNode`. The fix is one clause: carry `leafPublic p ≠ ""` in the `LeafNode` definition, or add a WF nonempty-name clause, or prove the empty name unreachable.

**DOWNGRADED, and the body has to say so.** COVERAGE.md filed this as tier 1, *"a soundness hole in a well-formedness condition"*. It is not. `LeafNode` **does not exist in mainline Lean**: every occurrence in `formal/lean/` is in `GraphIndex/Scratch4cii.lean`, the Route-B scratch file added 2026-08-21. `formal/history/PROOF_STATUS.md:121` agrees: *"`LeafNode` does not exist and must be written."* So this constrains code that has not been written yet; it is not a hole in a shipped proof, and nothing in today's tree is false because of it.

`deps: [P3]` is the honest edge — there is nothing to patch until `P3`'s Route B writes `LeafNode`.

## Traps

⚠ **Its capture is already good and its risk is closure, not loss.** The residual is recorded THREE times: `PROOF_STATUS.md:217-220`, `PROOF_STATUS.md:123`, and `Scratch4cii.lean:279-284`, the last one sitting next to a positive pin (`bare_publicOfLeaf_none`) proving the CURRENT carrier is safe. The failure mode is someone writing `LeafNode` without reading any of the three — which is what this row is for. Do not "close" it by adding a fourth prose copy.

⚠ **Do not raise its severity back on re-read.** The tier-1 framing came from reading a design constraint as a live defect; the same class of error produced the sweep's other refuted tier-1 item.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (the corpus convention; `migrate.py::check_formal_pointer` enforces it for the generated rows and 18/18 formal tasks satisfy it)
- `formal/lean/ZanzibarProofs/Core/Schema.lean::relNameOK` — the definition (`:64`) and `::WF` (`:70-71`)
- `formal/lean/ZanzibarProofs/GraphIndex/Scratch4cii.lean`:279-284 — the residual as written for the Route-B implementer, beside `::bare_publicOfLeaf_none`
- [`formal/history/PROOF_STATUS.md`](formal/history/PROOF_STATUS.md)`:217-220` and `:121-123` — the residual, and the statement that `LeafNode` does not yet exist
- `python task.py show P3` — the row that will write the definition this constrains

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-7 (tier 1 as filed); CONFIRMED OPEN but SEVERITY DOWNGRADED by COVERAGE.md §C2/§C3. Re-verified this pass: `LeafNode` occurs in exactly one Lean source file, GraphIndex/Scratch4cii.lean.

### 2026-08-29b

APPENDED to formal/lean/ZanzibarProofs/GraphIndex/Scratch4cii.lean:279-292, beside the residual it corrects, rather than to docs/latent-gaps.md. Verification refused the latent-gaps bullet: the home already issues the imperative ('Carry leafPublic p != "" ... or prove the empty name unreachable'), and the scope doc repeats it at leaf-family-split-scope-2026-08-05.md:1049-1052, so the residual is carried twice already and a third prose copy is what the finding's own trap forbids. The unique increment was the SEVERITY ADJUDICATION -- the tier-1 downgrade and 'do not re-raise on re-read' -- which now sits in that docstring. Correction found while verifying: LeafNode does not exist ANYWHERE in the tree, not merely outside mainline; only the leafNodeB proxy at Scratch4cii.lean:51. relNameOK unchanged at Core/Schema.lean:64, WF still single-field at :70-71.
