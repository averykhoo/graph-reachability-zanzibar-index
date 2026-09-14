# `P6` step 3b — the deliberate pin regeneration (2026-09-14)

**FROZEN as-of 2026-09-14.** A history file: read it for METHOD and for the reasoning behind
one regeneration, never for current state. Live state is `python scripts/task.py show P6`
and `python scripts/gate_status.py`.

This records the **why** for a `statement_pin.py --generate` run, as
`formal/conformance/statement_pin.py`'s own failure text requires. Two pins moved: the
headline STATEMENT pin (2 rows) and the headline DEFINITION pin (13 added, 2 removed, 14
changed). Both were seen RED first, and the RED is quoted below.

## 1. What landed, in one sentence

`P6` step 3b re-pointed the LEAF-routed write path onto
`UsStarWrite.lean::GraphState.writeBridgedOne` (re-point #2), the LOGGED write leg onto
`Cascade.lean::GraphState.bridgePreLogged` + `addEdge` (re-point #1), and the logged
retraction onto a `::releasePostLogged` epilogue (re-point #3) — so the graph index's
in-bridges are now materialised on the live path rather than defined and left inert. Step 14
(the `FoldAdmits` → `FoldAdmitsBridged` honesty move) landed with it, because it turned out
to be a **precondition** of step 8 rather than a follow-up.

## 2. The STATEMENT pin: 2 rows, both predicted

Observed RED, verbatim (elided to the delta):

```
FAIL: the STATEMENT of Zanzibar.runCascade2_no_abort changed
    pinned: … (hterm : ∀ dt R, …) (hLU2 : …) …
    source: … (hterm : ∀ dt R, …) (hNBD : NoBridgedDerived S) (hLU2 : …) …
FAIL: the STATEMENT of Zanzibar.cascade2_drains changed
    … same delta …
      2 headline theorem statement(s) differ from formal/headline_statements.txt.
```

**Both gain exactly one hypothesis, `(hNBD : NoBridgedDerived S)`, and nothing else moves.**
`docs/p6-step3b-plan-2026-09-13.md` § Blockers predicted this by name as its HEADLINE
BLOCKER — "two statement-pinned headlines gain `(hNBD : NoBridgedDerived S)` and
headline_statements.txt moves by two rows" — and the observed red is that forecast to the
row. Nothing unforecast moved.

**Why the hypothesis is necessary and not cosmetic.** Both headlines consume
`CascadeStrata.lean::reachedByW3d2_Rnode_not_source`, which consumes
`::reachedByW3d2_edge_source_ne_R`, whose old shape-free conclusion
(`∀ a b, (a,b) ∈ σ.edges → a.pred ≠ R`) is **FALSE** once the write leg bridges: a bridge
edge is sourced at its CONCRETE endpoint, and `Schema.isSubjectWildcardUserset` is keyed on
`(type, relation)`, so a literal `[x:*#R]` restriction at an UNTAINTED key `(x, R)` is legal
Python and bridges a node whose `pred` IS `R` (`TK68`'s type-index trap). The repair is the
carry plus a type-carrying conclusion; `NoBridgedDerived` was chosen over any store-indexed
alternative because it mentions no `Store` and therefore rides through a `write` (`t :: T`)
or `remove` (`T.erase t`) leg verbatim, with no weakening lambda at any of the ~30 threading
sites. Its provider already exists: `FullScope.lean::GraphAdmission.noBridgedDerived`, so the
carry TERMINATES at the admission bundle and costs the final theorems nothing.

## 3. The DEFINITION pin: the cone payment, made visible

`253` → `264` rows (`255` `def:` + `9` `ambient:`). The membership change is the part worth
reading, because it is the honest content of the whole item:

```
REMOVED from the pinned closure (no longer reachable from a headline statement):
    def:Zanzibar.FoldAdmits          def:Zanzibar.foldAdmitsB

ADDED (a headline claim now depends on these):
    def:Zanzibar.FoldAdmitsBridged   def:Zanzibar.foldAdmitsBridgedB
    def:Zanzibar.NoBridgedDerived
    def:Zanzibar.GraphState.writeBridgedOne     ::bridgePre       ::bridgePreLogged
    def:Zanzibar.GraphState.bridgedInConcrete   ::ensureInBridges ::ensureInBridgesLogged
    def:Zanzibar.GraphState.inBridgeOnly        ::releaseInBridges
    def:Zanzibar.GraphState.releaseInBridgesLogged  ::releasePostLogged

CHANGED (same name, different text):
    def:Zanzibar.GraphState.writeLoggedOne   ::removeLoggedOne
    def:Zanzibar.ReachedByW3d2   ::ReachedByW3d2C   ::ReachedByW3d2E
    def:Zanzibar.graphRunAux     ::graphRunOpsAux
```

⚠ **Read the REMOVED pair first — it is the honesty fix, visible at the pin level.**
`FoldAdmits` and its executable mirror `foldAdmitsB` describe a fold over
`GraphState.writeDirect`. Before step 14 the headline theorems' meaning still depended on
them while the code folded `writeBridgedOne`; the pin recorded that dependency faithfully,
which is exactly why it reds now that the dependency is gone. That the stale predicates
LEAVE the closure and the honest ones ENTER it is the single best piece of evidence that
step 14 did what it claims.

The ADDED block is the cone payment: a headline that says "the cascade drains" now depends,
through the write leg, on the bridge machinery. That was the point of `P6` (ii).

⚠ **`graphRunAux` / `graphRunOpsAux` changed because the RUNTIME GATES moved too.** Both
drivers gated on `foldAdmitsB` — the unbridged probe — which is strictly WEAKER than the
fold they drive (`GraphState.admitEdge` is anti-monotone in edges and
`GraphState.bridgePre` only adds edges). A driver left on the old gate would ACCEPT a batch
the write leg then refuses. They now gate on `foldAdmitsBridgedB`. This is the runtime half
of the same honesty obligation, and it is the reason the move could not stop at the
inductive's `hadm` binder.

## 4. What was checked before regenerating

* **RED first.** Both checks were run and their failures read before `--generate` was
  invoked; the statement RED is quoted above verbatim.
* **The whole tree is green** — `lake build` rc=0, `Build completed successfully (1089
  jobs).`, on the tree this note describes.
* **`audited_theorems.txt` is untouched.** Every restated theorem KEPT its name, which is
  what `verify.sh` step 4a pins. That includes two names that are now mildly misleading and
  must stay: `CascadeStable.lean::reachedByW3d_edges_target_plain` and its W3d-2 twin now
  conclude `≠ Variant.wAll` rather than `= Variant.plain` (a bridge target is `wAny`, so the
  old reading is FALSE), and `LeafRules.lean::writeRulesRaw_untaintedSchema` now equates the
  leaf-routed write to a `writeBridgedOne` fold rather than to `GraphState.writeRules`.
* **⚠ A reconnaissance report claimed the definition pins "already reflect
  `FoldAdmitsBridged`". They did not** — `grep` on the pre-regeneration file shows
  `(hadm : FoldAdmits σ …)` on rows 116/117/118. A subagent report is evidence, not a
  finding; this one was contradicted by one grep before anything was written down.

## 5. The trap that fired on purpose, and the one that fired by design

* `Cascade.lean::FoldAdmitsHonestyWitness.w3d_write_applies_with_the_stale_hypothesis` was
  planted on 2026-09-14 as a **deliberate tripwire**: it inhabits the live
  `ReachedByW3d.write` constructor at a CYCLE fixture, so re-pointing `hadm` makes it
  uninhabitable. When step 14 landed it produced **exactly one error**, at that declaration,
  with the type mismatch naming both predicates. Its docstring's prescribed response (move
  the pin to an admitted fixture; never weaken the constructor back) was applied, and the
  flip is recorded in the tree at `::w3d_write_applies_with_the_bridged_hypothesis` with the
  literal error text.
* `Exec.lean::reachedByW3d2E_edgeCount_store_indexed` is a **staleness trap** whose statement
  is hand-copied from `RemoveOccCount.lean::reachedByW3d2E_untOccCount`. R3 gained a
  `b.variant ≠ Variant.wAny` scope this session and the trap broke, as intended. The copy was
  updated; the duplication is the mechanism and must not be "simplified" into a reference.
