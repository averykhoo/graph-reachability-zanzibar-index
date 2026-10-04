---
id: TK107
title: remove (or mark) the tainted-tupleset code path TK106 made unreachable
brief: dead code since TK106: PDerivedTuplesetTTU + processor/bulk derived_stored_* are unreachable
pri: NEXT
size: M
deps: []
related: [TK106]
parent:
labels: []
source: hand
source_hash:
created: 2026-09-26b
moved: 2026-10-04g
updated: 2026-10-04g
closed:
---

**Filed 2026-09-26b by TK106.** Once a tupleset must be direct-only (TK106), a tupleset is never boolean-tainted. So the whole tainted-tupleset path is UNREACHABLE from any checked parse. It is still compiled and tested only through the unchecked parse.

Candidate removals are REASONED in `docs/tk106-triage-2026-09-26.md` § 18 (a subagent report; verify first-hand):
- `zanzibar_utils_v1.py`:
  - `PDerivedTuplesetTTU`, and the tainted arm of `_build_plan_tree`'s TTU case;
  - the `derived-tupleset-ttu` LeafSpec emission;
  - `_member_types`' Exclusion / Intersection / Computed / TTU arms;
  - the tainted-tupleset TTU arm of `_is_pure`;
  - the "has computed/rewritten arms" branch of `_validate_ttu_tuplesets`;
  - the `PDerivedTuplesetTTU` half of `_assert_ttu_parent_types_cover_admission`.
- `index_v4/processor.py`: `derived_stored_parents`, `derived_stored_star_types`, `_derived_stored_split`, `_split_parents`, `_split_star_types`, `_ts_leaf_predicates`, `_stored_parent_objects_of_entity`, and every `derived-tupleset-ttu` branch, including `_live_keys_of`'s.
- `index_v4/bulk_backfill.py`: the twins (`_derived_stored_parents`, `_ts_leaf_predicates`, the `derived-tupleset-ttu` branches).

Cautions:
- `formal/CORRESPONDENCE.md` cites `PDerivedTuplesetTTU` (the `lean` phase resolves every anchor, so the map must change with the symbol).
- The Lean model has a `PDerivedTuplesetTTU` twin, per `formal/HANDOFF.md`; decide whether to delete it or leave it as modelled-but-unreachable.
- The conformance suite excludes the leaf kind as unreachable, asserted by refusal.

First step: a census of call sites (file::symbol), and a mutation that deletes each branch while the gate stays green. That proves each branch is dead rather than assuming it.

## Log

### 2026-10-04g

PROMOTED LATER -> NEXT 2026-10-04g (user: NEXT raised to 5). Why: TK106 made the tainted-tupleset path unreachable (zanzibar_utils_v1.py::_validate_tuplesets_direct and its oracle twin), yet PDerivedTuplesetTTU and the processor derived_stored_* helpers remain. Dead code cannot answer wrong, so this is surface reduction, not new certainty -- but do it BEFORE TK120 (fewer symbols and CORRESPONDENCE.md anchors to move). Check whether P25-adjacent bridge code is part of the same dead set.
