---
id: DW-1
title: decidable W4Fragment for a driver-side pre-check
brief: steps 1+2 LANDED 2026-09-23d (Lean decider + zcli mode=fragment); next: Python report + differential
pri: NOW
size: M
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 04392ec66204
created: 2026-08-16
moved: 2026-09-23d
updated: 2026-09-23d
closed:
---

decidable `W4Fragment` for a driver-side pre-check. **Promoted SOMEDAY → LATER on
2026-08-31b, on measured evidence:** the scope pin classifies `W4Fragment`'s ten fields
**LOUD 0 · MIXED 3 · SILENT 7**, so for seven fields a schema outside the proven fragment is
accepted, runs, and answers queries with no signal to the operator — its correctness resting
on the differential net, not on `graph_correct`. A driver-side pre-check is what converts
those seven silent holes into a refusal or a warning.

## Traps

- ⚠ **Do NOT lift `ttuDirect` in Lean.** It is load-bearing for the current admission story; this row is the open descendant, and nothing is blocked meanwhile. (Moved here from `HANDOFF.md` "Standing traps" at the 2026-09-06 cutover -- the note carries no trap list; a trap lives with the item it guards.)

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- [`CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) §"Conformance gates"
- the live table: `formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE` (`:228`)

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-08-31b

Promoted SOMEDAY -> LATER on measured evidence: the new scope pin classifies W4Fragment's ten fields LOUD 0 / MIXED 3 / SILENT 7. For seven fields a schema outside the proven fragment is accepted, runs, and answers queries with no operator signal -- correctness resting on the differential net, not graph_correct. A driver-side pre-check is what converts those into a refusal or a warning. Live table: test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE.

### 2026-09-06b

Board cell rewritten 2026-08-31b (SOMEDAY -> LATER on the LOUD 0 / MIXED 3 / SILENT 7 scope-pin evidence; live table named). The pri was already LATER in the tree; the summary, brief and Read first now carry the evidence and the table symbol. Diff source: git 077bb50 -> HEAD.

### 2026-09-06d

The "do not lift ttuDirect in Lean" trap moved here from HANDOFF.md Standing traps at the 2026-09-06d cutover (see ## Traps). No change to the item itself.

### 2026-09-23c

Promoted LATER -> NOW 2026-09-23c: P14 closed as absorbed (docs/p14-reach-collapse-absorbed-2026-09-23.md), so goal step 2 is COMPLETE and this row is the most direct owner of goal step 3, "surface the silent narrowing -- the strongest version is a machine-checked coverage statement, not a doc" (docs/goal-census-2026-09-22.md, recommended moves). The census listed DW-1 among assurance-vs-product-risk rows; that was written before step 2 closed, and step 3 has no other owning row (grep of tasks/ for the silent-narrowing / scope-pin evidence finds DW-1, P21, P6, P4, TK101, TK103 only; P21 is the Lean-side differential channel, which this row may want but does not need first). UNSIZED: the first action is to size it against test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE (7 SILENT fields). For each field, say whether a decidable instance exists in Lean and whether the Python pre-check could be a mirror (P21 residual) or needs a real differential.

### 2026-09-23d

SIZED and steps 1+2 LANDED (2026-09-23d). Map: docs/dw1-decidable-w4fragment-2026-09-23.md (ACTIVE-PLAN; read its Progress block first).

Sizing, measured by two read-only agents and spot-checked first-hand:
- 4 fields already had a decider: wsBare, bareStar, ttuStarFree, term.
- 6 fields were CHEAP, none MEDIUM or HARD.

DECISIONS (the session's, per CLAUDE.md "Who decides"):
(1) Quantify the six lookup fields over taintedKeys S and match S.lookup, not over S.defs. The defs form is strictly stronger under duplicate keys (WF has no nodup clause), so it would lose completeness.
(2) GraphAdmission is out of this row: RewriteRanked is an existential. Filed as TK104.
(3) zcli mode=graph does NOT refuse out-of-fragment input. That would abolish _DIFFERENTIAL_ONLY. It REPORTS instead, via the new mode=fragment. This revises the CORRESPONDENCE.md completion criterion; see the dated note there.

LANDED:
- GraphIndex/FragmentDecide.lean: w4FragmentB, w4FragmentB_iff (exact, both directions), the Decidable instance, per-field report, 2 positive pins, 10 per-field controls.
- A 14-mutation sweep of that module, recorded in its docstring.
- Cli.lean mode=fragment and runner.run_fragment.
- formal/conformance/test_conformance_fragment.py: (A) theorem-backed corpora inside, (B) the per-field verdict on 36 corpora vs an independent Python derivation, (C) taintedKeys == compute_taint. 4 sabotages recorded in the plan doc.
- The three GRAPH_FRAGMENT prose disagreements are settled: all IN for the W4Fragment half.

BUILDS: lake build rc 0, lake build zcli rc 0.
RED: nothing.

NEXT (step 3): the production Python w4_fragment_report(ast, tuples), a pure per-field report, plus its differential against zcli mode=fragment. Turn the scope-pin probe schemas into fixtures first. Trap: noUnionDirects walks exprDirects (union-only), NOT exprDirectsAll. Sabotage S2 shows that mistake reddens direct_arm_exclusion.
