---
id: P6
title: ttuStarFree (ii) -- bridge on the LEAF-routed write path; P3 LANDED 2026-09-05b, collision gone
brief: P3 LANDED: increment B bridges on the LEAF-routed list (rawWriteTuples), never the public name; 38-cone is pre-flip
pri: NOW
size: M
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 1c868fadf76b
created: 2026-08-20b
moved: 2026-09-06b
updated: 2026-09-06b
closed:
---

Materialise the in-bridge on the rule-routed write path so the widened star-freeness
predicate is actually inhabited.

**`NOW` as of 2026-09-05b, by mechanism not by judgement**: `P3` landed and closed, this
was the top `NEXT` row, and its only blocker was the textual collision recorded below — so
it moved up. **Re-rank freely.** What `P3` changed for this item: the write leg is no longer
`writeLoggedOne` over the public closure — `GraphState.writeLoggedRules` folds
`rewriteClosureL S (rawWriteTuples S t)` (`Cascade.lean:190-191`), the remove leg folds the
SAME list (`:340-341`), and `affectedKeys` dirties the PUBLIC key through `publicOfLeaf`
(`:542-546`). **Increment B must bridge on that leaf-routed list**; a bridge keyed on the
public relation name would land on a node the write leg no longer touches — the same
leg-asymmetry class the kernel refuted in `P3`'s first attempt, where a write-then-remove
left a ghost grant (PROOF_STATUS `2026-09-05b` §2). Also inherited from `P3`: the dirty-key
list `cascadeKeysAbove` and the enum candidates `enumJob2(D).cands` are `.eraseDups` sets
(membership via `mem_cascadeKeys_iff_above` / `List.mem_eraseDups`) — any increment
touching `affectedKeys` or the candidate lists re-measures `two_stratum_cascade`'s
multiplicities (expect `1…5`) before regenerating a golden (PROOF_STATUS `2026-09-05b` §10).

## Traps

⚠ **`P3` LANDED 2026-09-05b, so "NOT parallel-safe with `P3`" is MOOT** — the collision
below is kept as the record of why the two could not run concurrently, not as a live
constraint. The "38-module cone" figure in it is **pre-flip and unreproduced** (the
2026-08-30c Log entry already flagged its lineage as a census rooted at the wrong module);
re-measure with a probe wave before quoting it. The live constraint now is the one above:
**bridge on the LEAF-routed list (`rawWriteTuples`), never on the public relation name.**

⚠ **Historical (superseded by `P3` landing): "It can run in parallel with `P3`" was WRONG,
and this row carried it for weeks**
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
- board pointer: `ttuStarFree` **(ii)** — bridges on the rule-routed write path. **Promoted `NEXT` → `NOW` MECHANICALLY on 2026-09-05b** — `P3` LANDED (write leg now folds `rewriteClosureL S (rawWriteTuples S t)`, `Cascade.lean:190-191`), so "NOT parallel-safe with `P3`" is moot and **increment B must bridge on the LEAF-routed list, not the public one**. Fresh evidence 2026-08-31b that this is a live hole: `ttuStarFree` classifies **SILENT** in the `W4Fragment` scope pin (`formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE`)

`formal/CORRESPONDENCE.md` §7 (`ZT-P5-NEW`);
`UsStarWrite.lean::Schema.isStarTuplesetThrough` / `::Schema.isSubjectWildcardUserset`;
`ensureInBridges` / `ensureBridges`; `writeRules` / `writeLoggedRules`; `derive_schema_info`'s
second loop.

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-20b`), which is an upper bound on the real creation date, not a measurement. Summary, traps and read-first come from the `### P6` item block verbatim; the board pointer is the first line of Read first.

### 2026-08-30c

Sizing flag, filed from P3's 2026-08-30c census. This row's '38-module cone' figure shares the lineage of P3's recorded '42 modules', which was SETTLED WRONG this session: 41+root is reproducibly the reverse import cone of DirectCorrect.lean and RulesWrite.lean, while CascadeStable.lean's is 20 (+root = 21), so the recorded figure was a delegated census rooted at the wrong module. I did NOT measure P6's own cone, so this is a flag, not a correction -- do not overwrite 38 with a number nobody measured. Re-measure before using it to decide the P3/P6 parallel-safety question, and publish the symbol list and counting unit with the result: four sessions of censuses disagreed not about the tree but about what a 'site' is. Method and evidence: scope doc sec 11.13 item 2, PROOF_STATUS '## Session 2026-08-30c' sec 2.

### 2026-08-31b

Fresh evidence this is a LIVE hole: ttuStarFree classifies SILENT in the new W4Fragment scope pin (test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE). Probe wrote 'folder:* parent doc:d1' onto a TTU tupleset: ADMITTED. _validate_ttu_tuplesets rejects userset restrictions in tuplesets but deliberately keeps wildcard ones ('star tuplesets are this repo's deliberate object-wildcard extension'). So the field graph_correct depends on is one Python does not enforce.

### 2026-09-05b

2026-09-05b: P3 LANDED, so the 'NOT parallel-safe with P3' blocker is gone and this row is promoted to NOW MECHANICALLY (top NEXT row; user may re-rank). Re-scope before starting: the write leg now lives at Cascade.lean:190-191 GraphState.writeLoggedRules := (rewriteClosureL S (rawWriteTuples S t)).foldl writeLoggedOne, and the remove leg mirrors it (:340-341); RulesWrite.lean::writeRules and Cascade.lean::writeLoggedOne are byte-unchanged. Increment B's in-bridge must be materialised on the LEAF-routed list (rawWriteTuples), not on the raw public tuple, or it re-creates the ghost-grant divergence PROOF_STATUS 2026-09-05b sec 2 refuted. The definition pin is 250 rows now; expect a pin diff on writeLoggedRules/removeLoggedRules and adjudicate it in formal/history/ (scope doc trap (ff): the pin shows the body that moved, not the meaning changes through it).

2026-09-05b addendum: the cascade's dirty-key list is now cascadeKeysAbove := (...).eraseDups and enumJob2(D).cands is deduped (CascadeStrataEnum.lean) -- both are faithfulness mirrors of processor.py landed with P3 after the flip doubled an exponential derived-arm stacking. Any increment here that touches affectedKeys or the enum candidates inherits those eraseDups and their membership lemmas (mem_cascadeKeys_iff_above, List.mem_eraseDups); re-measure two_stratum_cascade multiplicities (expect 1..5) before regenerating any golden.

### 2026-09-06b

Board block rewritten 2026-09-05b (P3 landed; promoted NEXT -> NOW mechanically; increment B must bridge on the LEAF-routed list). Task body reconciled 2026-09-06b: title/brief/summary/Traps/board pointer now say P3 LANDED and the collision is moot; the 38-module cone paragraph is kept as history and marked pre-flip/unreproduced. Old-vs-new source diff taken from git (077bb50 -> HEAD) by .scratch/tt1/drift_diff.py, transcribed here rather than left in .scratch.
