---
id: TK104
title: decidable GraphAdmission: the other half of the headline premise has no decider
brief: NOW 2026-09-24: SIZED (LOUD 10/MIXED 2/SILENT 2); next = Lean graphAdmissionB, RewriteRanked the one real proof
pri: NOW
size: M
deps: []
related: [DW-1]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-23d
moved: 2026-09-24
updated: 2026-09-24
closed:
---

`GraphAdmission` has no decider, so a `W4Fragment` verdict (`DW-1`, landed 2026-09-23d) only
establishes HALF of the headline premise `(hA : GraphAdmission S T) (hF : W4Fragment S T)`.
Every `_THEOREM_BACKED` corpus in `formal/conformance/test_conformance_graph.py` is now
machine-checked for the `W4Fragment` half (`test_conformance_fragment.py`), but its
`GraphAdmission` half is still a prose argument in `corpus.py`. The same gap is why
`ttu_fromchain`, `ttu_fromchain_group` and `self_flag` (all IN `W4Fragment` by Lean's decider)
cannot be moved into `GRAPH_FRAGMENT` yet.

Measured 2026-09-23d (READ, `FullScope.lean::GraphAdmission`):
- `Stratifiable S` is `(stratify S).isSome`, which is Bool already.
- `NodupKeys` is `List.Nodup` over the keys, which is decidable.
- `RulesSaturate.lean::RewriteRanked` is `∃ rrank : (String × String) → Nat, (∀ r ∈
  schemaRewrites S, rrank (matchKey) < rrank (outKey)) ∧ (∀ k, rrank k ≤ S.keys.length)`.
  Deciding it needs an acyclicity check plus a witness construction, and it is the only
  field sized above CHEAP.
- `Exec.lean::slV_admission_nil`'s docstring (measured 2026-09-05) lists WF / Stratifiable /
  TtuTuplesetsDirect / RewriteMatchDeclared / StoreValidRulesD as having no `Decidable`
  instance. Several are bounded list quantifiers in the same shape `FragmentDecide.lean`
  already handles.

Deliverable: `graphAdmissionB` + an exact `_iff` in the `FragmentDecide.lean` style, a
`"admission"` key in `zcli mode="fragment"`, and (A) in `test_conformance_fragment.py`
widened to the full premise. It is assurance, ranked against product risk under the
2026-09-22 goal, and is not required by goal step 3.

## Traps

- The sizing is DONE (2026-09-24): do not re-probe. The classification is pinned by
  `formal/conformance/test_graphadmission_scope_pin.py::GRAPHADMISSION_SCOPE`, and its
  probes re-run on every gate.
- `graphadmission_scope_probes.py::silent_admission_failures` is a REASONED hand mirror.
  It is NOT a decider, and nothing pins it to Lean. Do not cite it as one, and do not
  promote it into production as an operator report. `DW-1`'s hand derivation was wrong
  twice before a differential caught it.
- Store admission has TWO gates in series (`zanzibar_utils_v1.py::RuleSet.apply`, then
  `setengine/engine.py::SetEngine._validate`). A mutation to one gate alone is INERT by
  design. Sweep M5 / M5b / M5c.

## Read first

- [`docs/tk104-graphadmission-scope-2026-09-24.md`](../docs/tk104-graphadmission-scope-2026-09-24.md) -- sec 0 (the table), sec 3 (the decision and the `RewriteRanked` proof sketch)
- [`docs/dw1-decidable-w4fragment-2026-09-23.md`](../docs/dw1-decidable-w4fragment-2026-09-23.md) -- sec 1 on `GraphAdmission`, and the Progress block
- `formal/lean/ZanzibarProofs/GraphIndex/FragmentDecide.lean` -- the Bool + exact `_iff` pattern to copy

## Log

### 2026-09-23e

Promoted LATER -> NOW 2026-09-23e at DW-1 close: this row is now the only owner of goal step 3 (docs/goal-census-2026-09-22.md, 2026-09-23e correction). The W4Fragment half is decided in Lean AND reported in Python (zanzibar_utils_v1.py::w4_fragment_report, differential-pinned).
FIRST ACTION is sizing, not proof: classify each GraphAdmission field LOUD / SILENT / MIXED the way formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE does for W4Fragment. Reuse formal/conformance/w4_scope_probes.py as the probe-fixture shape. The DW-1 plan claimed GraphAdmission is largely mirrored by Python compile and write refusals; that is UNVERIFIED, and the classification is what verifies it. If most fields turn out LOUD, the decider may be worth less than the classification; decide after sizing.

### 2026-09-24

SIZED 2026-09-24. Map: docs/tk104-graphadmission-scope-2026-09-24.md (ACTIVE-PLAN).
LANDED: formal/conformance/test_graphadmission_scope_pin.py + graphadmission_scope_probes.py. This is the GraphAdmission twin of W4FRAGMENT_SCOPE: a hand-classified row per field, the field list parsed from FullScope.lean, each row tied to re-runnable probes (LOUD rows' probes must RAISE, SILENT rows' must be ADMITTED), MIXED shadowed_by checked through w4_fragment_report, and a REASONED mirror swept over the _THEOREM_BACKED corpora.
RESULT: LOUD 10, MIXED 2 (ttuDirect, storeValid; both silent halves are shadowed by W4Fragment computedOrDirect / directArmsBare), SILENT 2 (matchDecl = dangling references; ranked = untainted computed cycles). 0 of 36 curated corpora fail either SILENT field.
Sweep: 11 mutations + an M0 control. M5 was INERT because two admission gates run in series (RuleSet.apply, then SetEngine._validate); M5c with both gates weakened went RED, and the storeValid evidence was corrected to cite RuleSet.apply.
Also: the FullScope.lean GraphAdmission docstring, formal/ARCHITECTURE.md and formal/FINAL_REVIEW.md claimed full Python enforcement; they are corrected in place and dated. MIN_CONF_ALL 582 -> 843 and MIN_CONF_REST 447 -> 708: 195 of the 261 were DW-1's unratcheted leak.
DECISION (the session's call per CLAUDE.md Who decides; reasoning in doc sec 3): build the decider, because only a Lean-pinned report can surface matchDecl/ranked to an operator honestly. NOT taken: refusing dangling refs in Python. That is a product change made to fit a proof, and if wanted it is an ASK-* question.
NEXT ACTION: Lean graphAdmissionB + exact _iff in FragmentDecide.lean style. 13 fields are cheap (doc sec 3 lists which already have instances). RewriteRanked is the one real proof: an iterated longest-path candidate rank, soundness trivial, and the completeness sketch is in doc sec 3. Then zcli fragment gains an admission key, (A) widens, then the Python report for the two SILENT fields, differential-pinned.
