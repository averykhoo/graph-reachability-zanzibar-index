---
id: P25
title: Star tupleset over a DERIVED through-relation: Python handles it, the fragment excludes it, unproved
brief: Python bridges the PUBLIC derived node from the cascade; no proof covers it. Corpus first, fragment extension second
pri: LATER
size: M
deps: []
related: [P6]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-12b
moved: 2026-09-12b
updated: 2026-09-12b
closed:
---

A star tupleset whose TTU through-relation is DERIVED (e.g. `doc#control := approver from
parent` with `folder#approver := [user] but not blocked`) is handled by Python and covered by
NO proof. Filed 2026-09-12b from the `P6` plan session, where it was found that
`W4Fragment.term` (`formal/lean/ZanzibarProofs/FullScope.lean:299`, via `NoTtuTarget`,
`GraphIndex/ReconcileCorrect.lean:616`) excludes exactly this shape from the proven fragment
— so the 2026-09-12 "scope defect" on `P6` was a measurement OUTSIDE the fragment, and this
row is where that measurement's subject actually lives.

**What Python does here** (read first-hand 2026-09-12b): the in-bridge on the PUBLIC derived
node `folder:x#approver -> w_any(folder, approver)` is created by the delta processor's
derived write — `DeltaProcessor._write_derived` (`index_v4/processor.py`) goes through
`WildcardIndex.add_tuple`, which calls `_ensure_bridges` on both endpoints
(`index_v4/wildcard.py`, the `add_tuple` bridge-before-grant block) — and retracted by
`_gc_public_node` → `_maybe_remove_bridges`. The raw write leg never touches the public node
(it lands on the leaf `approver.0`), which is why routing alone cannot bridge it
(`formal/probes/p6_inbridge_stability_2026-09-12.lean` ROUTING arm on `Sd`, `:902-906`).

**Why it matters for the stated goal** (prove the graph index correct, no edge-case bugs):
this is a shape the shipped index accepts where the only nets are the differential matrix
and the hypothesis campaign; nothing machine-checks that the cascade's public-node bridge
plus its GC give the oracle's answer under churn (write, remove, re-add on the derived key
while the star tuple stays). The `d3_` probe's arm (D) already measured an in-bridge-shaped
edge flipping `Inv.negEdgeFree` on the post-flip write leg, and `PROOF_STATUS.md` sec 3
(`:392-411`) records both a fail-closed MISSING grant and a fail-open GHOST grant at this
key class in an earlier Lean attempt — so the class has history.

**Two ways to close it — pick one at scheduling:**
1. Extend the fragment: model the processor's derived write as bridge-materialising
   (`ensureInBridges` on the public node inside the cascade's derived-write step) and its GC,
   then drop `NoTtuTarget` from `term`. Larger than `P6`; depends on `P6` steps 2–3 landing
   the logged bridge and `releaseInBridges` first, because it reuses both.
2. Pin it empirically: a targeted conformance corpus (star tupleset over a derived relation,
   both boolean operators, churn on the derived key) in `formal/conformance/` with the oracle
   as referee, plus a hypothesis stateful arm biased to this shape. Cheaper, and it is what
   the user's goal actually needs first — a proof of a boundary nobody has tested is the
   wrong order.

## Traps

⚠ Do not "fix" this by bridging the public node from the RAW write leg — that is the ghost-
grant divergence the kernel refuted for `P3` (`PROOF_STATUS.md` `2026-09-05b` sec 3). The
bridge belongs to the cascade's derived write, as in Python.

⚠ Check `formal/conformance/corpus.py` for an existing schema of this shape before writing
one: the 2026-08-20 census found `bridged_in_shapes` empty on all corpus schemas bar one
(fragment-excluded), so the answer is probably "none", but grep first.

## Read first

- `tasks/P6-ttustarfree-ii-bridges-on-rule-routed-write-path.md` Log `2026-09-12b` (the plan that scoped this out).
- `index_v4/processor.py::DeltaProcessor._write_derived`; `index_v4/wildcard.py::WildcardIndex._ensure_bridges`; `index_v4/processor.py::DeltaProcessor._gc_public_node`.
- `formal/lean/ZanzibarProofs/FullScope.lean::W4Fragment` (`term` field); `formal/lean/ZanzibarProofs/GraphIndex/ReconcileCorrect.lean::NoTtuTarget`.
- `formal/CORRESPONDENCE.md` sec 7 (where the boundary gets recorded at `P6` step 0).

## Log
