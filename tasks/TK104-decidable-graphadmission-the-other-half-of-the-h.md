---
id: TK104
title: decidable GraphAdmission: the other half of the headline premise has no decider
brief: NOW 2026-09-23e: last half of goal step 3; size first -- classify GraphAdmission fields LOUD/SILENT
pri: NOW
size: M
deps: []
related: [DW-1]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-23d
moved: 2026-09-23e
updated: 2026-09-23e
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

## Read first

- [`docs/dw1-decidable-w4fragment-2026-09-23.md`](../docs/dw1-decidable-w4fragment-2026-09-23.md) -- sec 1 on `GraphAdmission`, and the Progress block
- `formal/lean/ZanzibarProofs/GraphIndex/FragmentDecide.lean` -- the Bool + exact `_iff` pattern to copy

## Log

### 2026-09-23e

Promoted LATER -> NOW 2026-09-23e at DW-1 close: this row is now the only owner of goal step 3 (docs/goal-census-2026-09-22.md, 2026-09-23e correction). The W4Fragment half is decided in Lean AND reported in Python (zanzibar_utils_v1.py::w4_fragment_report, differential-pinned).
FIRST ACTION is sizing, not proof: classify each GraphAdmission field LOUD / SILENT / MIXED the way formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE does for W4Fragment. Reuse formal/conformance/w4_scope_probes.py as the probe-fixture shape. The DW-1 plan claimed GraphAdmission is largely mirrored by Python compile and write refusals; that is UNVERIFIED, and the classification is what verifies it. If most fields turn out LOUD, the decider may be worth less than the classification; decide after sizing.
