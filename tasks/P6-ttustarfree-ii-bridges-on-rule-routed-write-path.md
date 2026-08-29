---
id: P6
title: ttuStarFree (ii) -- bridges on rule-routed write path; NOT parallel-safe with P3 (38-module cone)
brief: NOT parallel-safe with P3 (same 38-module cone): land increment A and stop, or sequence B after P3, never both
pri: NEXT
size: M
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 5c25e542f542
created: 2026-08-20b
moved: 2026-08-20b
updated: 2026-08-29d
closed:
---

Materialise the in-bridge on the rule-routed write path so the widened star-freeness
predicate is actually inhabited.

## Traps

⚠ **"It can run in parallel with `P3`" was WRONG, and this row carried it for weeks**
(corrected 2026-08-20b). Logically independent, **textually colliding**: both re-point
`RulesWrite.lean::writeRules` and `Cascade.lean::writeLoggedOne`, both move `FoldAdmits` +
`Exec.lean::foldAdmitsB` in lockstep, and **both pay the same 38-module cone** — whichever
lands second re-pays it. Land increment A (additive, zero-cone) and stop, or sequence B
after `P3`; never concurrently. **Probe with `#eval` before paying the cone, exactly as
`P3` did**: `CascadeStable.lean`'s `writeLeg_reach_stable` family says a write leg does not
change reachability at these nodes, and **an in-bridge DOES change reachability — that is
its purpose**, so those statements may go FALSE at a bridged state rather than merely
needing a new case. The change is also **INERT on every corpus** (measured 2026-08-20:
`bridged_in_shapes` empty on all 26 `corpus.SCHEMAS` and every extended set bar one,
fragment-excluded), so the gate cannot see it and all evidence must be new Lean pins —
[`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) §"The INERT change" governs, as
for part (i). Increment B also **inverts
`extractor.py::_edge_projection`'s `P2` projection** (it drops PYTHON `w_any` rows because
"Lean never creates them"); its docstring is already false. Detail: ledger `2026-08-20b`.

⚠ **DO NOT DROP IT.** Without `ttuStarFree`, `graph_correct` and `backend_equivalence` are
machine-checked **FALSE** — not merely unproven. Part (i) is **INERT**: part (ii)
materialises the edge, and the rest of the leg is inert until it lands.
`W4Fragment.ttuStarFree` must stay **UNCHANGED** until (ii) is in.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule; enforced by `migrate.py::check_formal_pointer`, not merely stated)
- board pointer: `ttuStarFree` **(ii)** — bridges on the rule-routed write path; **NOT parallel-safe with `P3`** (same 38-module cone, corrected 2026-08-20b)

`formal/CORRESPONDENCE.md` §7 (`ZT-P5-NEW`);
`UsStarWrite.lean::Schema.isStarTuplesetThrough` / `::Schema.isSubjectWildcardUserset`;
`ensureInBridges` / `ensureBridges`; `writeRules` / `writeLoggedRules`; `derive_schema_info`'s
second loop.

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-20b`), which is an upper bound on the real creation date, not a measurement. Summary, traps and read-first come from the `### P6` item block verbatim; the board pointer is the first line of Read first.
