# Leg 7 — the leaf-family split (retire projection P6). SCOPE — ACTIVE-PLAN.

> **ACTIVE-PLAN (declared 2026-08-16).** This document is being executed right now — it is
> live until its board rows close, then it gets the frozen banner. See
> [`docs/README.md`](../../docs/README.md) §2 for the liveness states. Corrections are
> appended dated at the top (§11 is the running record); the body below is provenance and
> **§4 and §11.3 are known-wrong in stated ways** — read §11.1 and §11.5 before acting on
> either.
>
> **CORRECTION 2026-08-16 — this leg is NO LONGER DEFERRED, and the status line below this
> banner is as-of-2026-08-05.** Leg 7 began landing 2026-08-09 (steps 3 and 4a) and now
> carries 4c-pre and 4c-i as well. It is board row `P3` at priority `NOW` in
> [`HANDOFF.md`](../../HANDOFF.md), and rows `P4`, `P5` and `P14` read this file too. The
> board is the live state; no line in this file is. The title said "SCOPE, DEFERRED" until
> today, so a cold reader following `P3`'s read-first list met a false status before this
> banner.

> **CORRECTION 2026-08-30b — §11.12 rule 3 is UNSAFE AS WRITTEN, and §11.10 is wrong in
> two places.** Rule 3 sends findings to `PROOF_STATUS.md` because it "is append-only and
> therefore survives the reset". It does not: append-only is a convention about how the
> file is *edited* and confers nothing on an **uncommitted** working-tree change, which is
> exactly what rule 1's `git reset --hard` discards. Read as written, rules 1 and 3 compose
> into a procedure that destroys the session's yield at the moment it is most needed — and
> it collected on 2026-08-30, costing 105 lines to a plain `git checkout --`. Amend rule 3
> to **"commit the docs-only append FIRST, then reset onto it"**, and add a **rule 6:
> commit every green-stoppable prefix before running a sabotage against it** (a green
> additive prefix is not a partial cone under rule 5 — it contains no re-point and no pin
> asserting anything untrue). §11.10's two corrections: the non-emptiness premise is **not**
> `StoreValidRulesD` (that constrains stored tuples, never relation names — the
> superset-extras lemma needs an explicit `hne : ∀ dt R, isDerived S (dt,R) = true → R ≠ ""`),
> and `rawWriteRels` is `Leaf.lean:587`, not `:541`. Evidence and the recon that also split
> the cone into a green prefix (steps 1–2) and an un-splittable middle (steps 3→10):
> `PROOF_STATUS.md` `## Session 2026-08-30`.

**Status as of 2026-08-05: the design decision is MADE — option (c). The work is DEFERRED,
not scheduled.** Decided by the user 2026-08-05. This file is the scoping pass so the leg
is resumable without re-deriving the blast radius; **no Lean declaration was changed to
produce it.**

> **NOTE 2026-08-16 (handoff migration) — board row `P5` reads §9.1–9.3 PLUS §7 step 6.**
> §9 carries the verdict and the traps, but not the completion criterion: that is **§7
> step 6** — re-point the readers, then the `Inv` stack, then **delete `W4NarrowT2a`**,
> which is what closes `ZT-P3-1` for T2a. Sizing 1–2 sessions, gated on row `P4`. Per §9.1
> this is **effort, not risk** — the attack probe returned NO-KILL.

> **Why this document exists.** `W4NarrowT2a`'s docstring
> (`lean/ZanzibarProofs/FullScope.lean`) offered three ways to correct T2a
> (`graph_reached_inv`), and both HANDOFF files said "a design decision is owed".
> The decision is (c): **model the leaf-family split and retire P6.** (a) and (b) are
> rejected — see §1. Read §1 for *why*, §2–§6 for *what it costs*, §7 for the ordering,
> §8 for what is still unknown.

---

## 1. Why (c), and why not (a) or (b)

The problem, restated: leg-0 probe D.3 (2026-07-28) machine-checked `Inv.negEdgeFree`
**FALSE** on the `_d` fragment. Under `StoreValidRulesD` a Direct-arm write lands an edge
at the very derived R-node whose residue carries the `neg` row, and `Inv` forbids exactly
that. **Python is fine** — `RuleSet.apply` routes the write onto the leaf family, so the
edge lands on `#approver.0`/`#approver.2` and the `neg` row lives on `#approver`; different
nodes, I6 disjointness intact, 0 mismatches over the grid and a 6-way order sweep.

Three facts found while adjudicating, all of which point the same way:

1. **Nothing consumes `Inv`.** `Inv` appears as a hypothesis in exactly four places —
   `State.lean:813` (`Inv.toStruct`), `State.lean:854` (`inv_putResidue`),
   `Write.lean:150` (`inv_writeDirect`), `RulesWrite.lean:181` (`inv_writeRules`) — all
   of them `Inv → Inv` preservation steps. `EdgeHygienic` (`CascadeInv.lean:445`) is
   likewise produced (`:463`, `:481`, `:536`, `CascadeStrataEdge.lean:360`) and consumed
   as a hypothesis nowhere. T2b and the read path do **not** lean on it.
   *Consequence:* option (b) could not break a downstream proof — and that is precisely
   the objection to it. `Inv`'s entire value is as a *claim*. Weakening a claim nothing
   consumes is the house failure mode (an assurance step that fails by passing): the gate
   stays green, the theorem quietly says less, and only the definition pin moves — which
   the leg would be moving deliberately anyway. No mechanical check would object.
2. **(b) would be faithfulness-negative.** The exemption would be phrased over "edges
   written by the current un-cascaded write leg" — a *model* notion with no Python
   counterpart, because in Python the edge is never on that node at all. Weakening an
   invariant to accommodate a modelling artifact is what house rule 5 exists to prevent.
3. **There is precedent, and it is (a)-shaped, not (b)-shaped.** This already happened
   once: on 2026-07-11j an attack-first `#eval` found `negEdgeFree` FALSE over the plain
   `ReachedByW3d` chain (`CascadeInv.lean:14-27` — the stale-edge / `neg = [alice]`
   scenario). The response was **not** to weaken the invariant; it was to scope the
   theorem to the stronger coverage chain, `reachedByW3dC_inv`.

So (a) and (b) both *shrink the claim*; they differ only in which part they shrink. **(c)
is the only option that raises assurance rather than redistributing it** — `negEdgeFree`
becomes TRUE on the `_d` fragment with nothing weakened, `W4NarrowT2a` disappears rather
than being carried, and the state gate stops being blind to a whole edge class (§5).

**The cost is the only argument against it, and it is a real one: 55–65% of the Lean tree
is touched.** Hence: decided, deferred.

---

## 2. What the model has today, and what is missing

**There is no leaf-family concept anywhere in `formal/lean/`.** `<relation>.<index>` does
not exist as a string, a constructor, or a predicate. P6 is not a flag that is off; it is
a genuine absence.

* `Schema` is `defs : List ((String × String) × Expr)` + `objectWildcards`
  (`Core/Schema.lean:36-38`). There is **no compiled RuleSet** — no `Filter`, no
  `RewriteFilter`, no `LeafSpec`/`LeafFamily`/`Plan`, no persisted compiled artifact.
* The nearest analogue to `compile_ruleset` is `schemaRewrites`
  (`GraphIndex/RulesWrite.lean:82-83`), a pure function of `S.defs` that emits `RRule`s
  for `computed`/`ttu` leaves and **nothing** for `direct` (`:65` — "`Direct` arms compile
  to admission Filters (no fan-out)").
* `exprDirectsAll` (`ReconcileCorrect.lean:960-975`) is a partial mirror of Python's leaf
  *extraction*, but it is used for **admission**, not to create leaf nodes.

**Therefore leaf families cannot be derived from what the model has — they must be added
as new structure**: a compile step `Schema → leaf-name assignment`, plus edges landing on
leaf `NodeKey`s.

### The Python ground truth the model must mirror

* Leaf predicates are `f'{relation}.{counter[0]}'`, minted in `alloc()` inside
  `_build_plan_tree` (`zanzibar_utils_v1.py:1658-1659`), the only creator, called once per
  tainted key from `compile_ruleset` (`:1954-1956`). The index is a per-relation counter
  allocated **pre-order, left-to-right, over persisted-leaf positions only** (`:1650-1652`);
  `PDerivedComputed`/`PDerivedTTU` consume no index (`:1756-1763`).
* `storage=True` (RewriteFilter-fed, edges *are* the raw stored tuples — `:1693-1696`,
  `:1713-1715`, `:1663-1666`) vs `storage=False` (Rule-fed closure leaf — `:1697-1699`).
  Direct arms always get their own separate leaf (`:1688-1690`) precisely so rule-routed
  state never counts as "stored tuples".
* `RuleSet.apply` (`zanzibar_utils_v1.py:423`) rejects a raw write naming a leaf
  (`:433-439`) and fan-in expands a derived-public write via
  `replace_relation(triple, f.rewrite_relation)` (`:447`).
* **Edges land on the leaf node; the residue lands on the public node.**
  `DeltaProcessor._store_residue` writes `ResidueV1(object_node_id=<public node>)`
  (`index_v4/processor.py:949-978`), and `_write_derived` pins that public node
  non-implicit because it "anchors the residue row" (`:429-440`). Invariant I4 requires
  every `'.'`-predicate node to be a declared leaf family
  (`index_v4/invariants.py:303-310`).

---

## 3. ★ The disjointness linchpin already exists — no new axiom needed

The first scoping pass flagged "prove leaf nodes are distinct from bare nodes" as the
linchpin of the whole change, and suspected it would need a new sentinel-style axiom
alongside `STAR`/`BARE` (`Core/Ident.lean:16,20`), since `ValidIdent` is deliberately
opaque (`Core/Ident.lean:37`).

**It does not.** `Core/Schema.lean:64` already carries
`relNameOK := ¬ name.contains '.'`, lifted to schemas by `WF.relNames` (`:71`). So a leaf
node `⟨t, n, "R.i", plain⟩` is *provably* distinct from every bare R-node, for free, and
this mirrors Python's own reservation of `.` in declared relation names
(`zanzibar_utils_v1.py:869-875`, `_validate_ast_references` `:890-899`).

**The constraint this imposes is the key design rule for the leg:**

> **Leaf predicates must NOT be added to `S.defs`.** They live in a separate compile
> artifact keyed off the schema. If leaf names ever enter `S.defs`, `relNameOK`/`WF` must
> be restated and three consumers break: `DirectCorrect.lean:73-86`
> (`lookup_rel_ne_bare`, which *derives* "declared relation ≠ `BARE`" from the no-`.`
> property), `ReconcileCorrect.lean:1165`, and `RulesChain.lean:224`.

Corollary: **encode the leaf index in `NodeKey.pred` as `R ++ "." ++ toString i`; do not
add a field to `NodeKey`.** `NodeKey` is a flat 4-field structure
(`GraphIndex/State.lean:53-58`) deriving `DecidableEq`, compared by `==`/`decide` in
hundreds of places; there are ~825 occurrences of the `objNode ⟨…⟩` anonymous-constructor
pattern and 581 `NodeKey` mentions, all of which a 5th field would force through a
rewrite. `Variant` (`:46-48`) is the wildcard axis and should stay that way. A `pred`
convention needs only an additive predicate (e.g. `isLeafPred`); a new field would also
want a companion clause on `Inv.nodeEnc` (`:689`).

---

## 4. ★ The write path forks — and half the discriminator is already built

Every edge placement funnels through **one** definition:

```lean
-- GraphIndex/Write.lean:77-82
def GraphState.writeDirect (σ : GraphState) (t : Tuple) : GraphState :=
  let a := subjNode t.subject
  let b := objNode t.object t.relation      -- ← the bare derived R-node
  if σ.admitEdge a b then (((σ.addNode a).addNode b).addEdge a b) else σ
```

It is shared by **both** Python paths, which land on **different nodes**:

| path | model callers | Python target |
|---|---|---|
| raw leaf-routed write | `writeLoggedOne` (`Cascade.lean:167-170`), `writeLoggedRules` (`:175-176`), `writeRules` (`RulesWrite.lean:116-117`) | `<rel>.<i>` leaf node |
| reconcile emission | `reconcileKey` (`ReconcileWrite.lean:73`), `reconcileKeyD` (`ReconcileDiff.lean:235`), `reconcileKeyDR` (`CascadeStrata.lean:210`) | bare derived R-node |

So `writeDirect` must **fork** (take a target-node argument, or split into
`writeDirectLeaf` / `writeDirectDerived`), which duplicates or re-parameterizes every
`writeDirect_*` projection lemma (`Write.lean:85, 92, 171, 176, 181, 186, 237`) and every
fold lemma (`RulesWrite.lean:122-193`). The removal path forks with it —
`removeEdgePair`/`removeEdgeOne` (`ReconcileDiff.lean:54, 131`) — as does the executable
driver's replicated `admitEdge (subjNode …) (objNode …)` shape (`Exec.lean:44`).

**★ The good news: the discriminator already exists and is already load-bearing.** The
`Delta.leaf : Bool` provenance tag landed 2026-07-20c for exactly this distinction, and
its docstring states the collapse in as many words (`State.lean:80-90`):

> "a `true` row is a RAW leaf-routed write/remove on a storage leaf … a `false` row is a
> reconcile emission at a derived R-node … **In the collapsed model both land at
> `objNode ⟨o⟩ R`, so the tag is the only faithful discriminator.**"

`writeLoggedOne` already pushes `leaf := true` (`Cascade.lean:169`) and reconcile
emissions push `false`. **The routing signal the split needs is therefore already
threaded through the cascade/fence stack** — the leg turns an existing tag from a
*bookkeeping* discriminator into an *addressing* one. That is the single biggest
cost reducer found in this pass.

---

## 5. Blast radius

Tree: **41,813 lines, 64 `.lean` files, 1,717 declarations** (plus `Audit.lean`, 1,678
lines / 481 `#print axioms`).

| scope | files | lines | % |
|---|---|---|---|
| zero `objNode` reference (untouched by construction) | 23 | 6,630 | 16% |
| references the derived R-node `objNode ⟨…⟩` | 34 | 32,887 | 79% |
| **core rework set** (write path + reconcile + cascade + `Inv` stack) | 23 | 24,956 | **60%** |

**Ballpark: 55–65% of the tree touched; 15–20% of declarations need real proof rework;
35–40% need at least a mechanical restatement.** (~281 of 1,717 declarations reference the
derived R-node expression directly — treat as a floor; ~636 touch `NodeKey`/`objNode`/
`subjNode` at all — treat as a ceiling. Both grep-derived.)

**The 16% that is genuinely safe:** `Core/*` (233), `SetEngine/*` (936), `Spec/*` (2,053),
`Closure.lean`, `RulesSaturate.lean`, `RulesSound.lean`, `Equiv.lean`. **The spec side does
not model leaf families at all** — Python's leaf split is a *storage* decision the
semantics is invariant under — so `sem` and the set engine are entirely spared. This is
the best structural news in the scope: the leg cannot perturb the trust root.

### Readers of the bare R-node that need re-pointing

`probeDerived` (`State.lean:570-585`), `probeNonDerived` (`:552-561`), `graphRec`
(`ReconcileWrite.lean:47-48`), `checkFn` (`:60-62`), `coveredAt` (`ReconcileStars.lean:255`),
`edgeHolders` (`CascadeEnum.lean:325-326` — the `_incoming_concretes` analogue),
`storedDirectSubjects` (`CascadeStrataEnum.lean:626`), `enumJob2` (`:230-235`), `enumJob2D`
(`:764`), the three reconcile folds, `edgeOfTuple` (`CascadeStrata.lean:669`).

### Structural predicates that must be re-partitioned (leaf-node vs derived-node)

`DerNode` (`CascadeStable.lean:523-524`, 39 uses), `RnodeTerminalAll` /
`RnodeSourceBareAll` (`CascadeStrataEdge.lean:51-59`), `UntaintedShadow`
(`CascadeStable.lean:528-534`).

### ★ The deepest single change

The **reach-collapse family** — `reachedByW3d2_reach_collapse_root`
(`CascadeStrataSettle.lean:272-282`), `reachedByW3d_reach_collapse_root`
(`CascadeSettle.lean:168`), `reachedByW3a_reach_collapse_root`; ~55 call sites over 13
files — proves "any path into the R-node is a single edge" from `RnodeSourceBareAll` +
`bareNode_no_inedge`. It needs **re-proving, not adapting**. Collapse should still hold
*per node* (leaf nodes' in-edges are also bare-sourced, and Python's `leaf_check` probes
the leaf node via a separate `widx.check` — `index_v4/processor.py:102-110`), but the
`DerNode`/`UntaintedShadow` classification must be re-partitioned and `graphRec`/`checkFn`
re-pointed at leaf predicates. This sits under `CascadeStrataSettle.lean` +
`CascadeStrataResettle.lean` = **7,185 lines, 142 declarations**.

### The `Inv` stack

56 dedicated invariant-preservation declarations across 10 files / 4,190 lines
(`CascadeInv.lean` 22, `CascadeStrataInv.lean` 11, `State.lean` 5, `CascadeStrataEdge.lean`
4, `RulesWrite.lean` 4, `Write.lean` 2, `UsStarWrite.lean` 2, `ObjStarWrite.lean` 2,
`ReconcileWrite.lean` 2, `ReconcileUpos.lean` 2); `Inv`/`StructInv` is *mentioned* in 23
files. `ResidueHygienic` (`CascadeInv.lean:248-250`) is not node-key-sensitive — low risk.
`EdgeHygienic` (`:445-448`) and `EdgeHyg1` (`CascadeStrataEdge.lean:40-43`) are fully
node-key-sensitive.

### Cost multiplier: `Audit.lean`

**1,678 lines, 481 `#print axioms`, zero declarations.** Every renamed or split
declaration breaks an audit line — mechanical, but it must be re-run and re-narrated, and
its prose asserts the P6 limit (`Audit.lean:1649-1650`), which would become false.

---

## 6. The gate ripple (retiring P6)

The filter is three lines — `formal/conformance/extractor.py:235-236`:

```python
        if "." in obj[2] and obj[2] != "...":
            continue                                    # P6: leaf-family copy
```

It drops Python direct edges whose **target** node predicate contains `'.'` (excluding the
bare sentinel `'...'`), Python-side only, edges only — residues are untouched, being keyed
on the public relation.

| file | change |
|---|---|
| `formal/conformance/extractor.py` | delete `:235-236`; rewrite the P6 paragraph `:132-150`; fix cross-refs at `:125`, `:161`, `:173-175`. **★ The non-obvious ripple, and the largest:** leaf predicates are not in the taint set, so newly-compared leaf edges classify as **untainted arm** in `_classify_edges` (`:328-346`) — whose multiplicity P3 then compares **EXACTLY** — and that function's stated justification (`:334`, "routed onto `<rel>.<n>` leaf families which P6 already dropped") becomes **false as written**. It also *raises* on schema-taint/`EdgeV4.derived` disagreement. Settle this before deleting the filter. |
| `formal/conformance/derived_arm_multiplicity.json` | regenerate (`ZANZIBAR_UPDATE_SNAPSHOTS=1`) — model cascade multiplicities change, and the key set may change as edges move between arms |
| `formal/conformance/test_conformance_state.py` | `_MIN_LEDGER_ROWS = 18` / `_MIN_LEDGER_STACKED` (`:94`) and the assertion at `:228` must be **re-derived, not bumped**; docstring numbers `:16-22`, `:43-59` go stale; `test_python_nodes_are_all_justified`'s "41 invisible" claim (`:368-372`) needs re-measuring |
| `formal/CORRESPONDENCE.md` | §7 divergence 4 ("No leaf-family split", `:776-787`) is **retired**; fix the P-list refs (`:85`, `:453`) and the state-gate thinness measurement (`:460-491`). Anchors are gate-checked (`anchor_check.py`) so new Lean symbols must be cited correctly |
| prose elsewhere in `formal/conformance/` | `corpus.py:427`, `test_conformance_graph.py:67`, `test_conformance_enum.py:90`, `test_conformance_enum_state.py:23-26`, `test_conformance_remove.py:397` (that last one *relies* on P2/P6 hiding nothing on the raw-SQL leg) |
| all three pins | `headline_definitions.txt` pins the literal text of `GraphState`/`GraphAdmission`/`ReachedByW3d2{,C,E}`/`applyRRule`/… — any `Schema`/`RRule`/`writeRules` change breaks it. Regenerate deliberately: `"$PY" formal/conformance/statement_pin.py --generate` (both goldens together) and `bash formal/regen_audit_pin.sh` |

**Payoff on the claim side:** `W4NarrowT2a` (`FullScope.lean:227-230`) **disappears** and
`outside_narrow_t2a` becomes a deliberate deletion rather than a repair — T2a widens to
match T2b, and the vacuity caveat retires for `graph_reached_inv` as it did for the T2b
family in leg 6.

### ✅ The P6 measurement — DONE 2026-08-05, and it is now generated

*This section described a defect; the defect is fixed. Kept because the numbers below are
the leg's baseline.*

`extractor.py::projection_ledger` / `::graph_fragment_ledger` drive every in-fragment
corpus and count the drops per projection; `doc_counts.py::measure()` publishes the totals
into `FINAL_REVIEW.md`'s generated block and `verify.sh` step 4e checks them (+~5 s).
`extract_sql_state` and the ledger share ONE predicate (`extractor._edge_projection`), so
the published number cannot describe a different filter than the gate applies.

**Baseline for the leg, measured 2026-08-05** (23 corpora): **477** raw `EdgeV4` rows →
**233** P1, **0** P2, **73** P6, **171** compared; **266** `NodeV4` rows (all P5-dropped);
**13** residue rows over 6 corpora. Two independent implementations agreed exactly.
Drift from the figures that had been quoted since 2026-07-27 (21 corpora): 447→477,
231→233, 62→**73**, 154→171, 235→266, 11-over-5→13-over-6. Only the P2 zero survived.

**When the leg lands, these numbers MUST move**, and loudly: retiring P6 drives `P6` to 0
and `compared` from 171 to 244. Sabotage-verified — deleting the P6 branch turns
`doc_counts --check` red with that literal diff and fails
`test_conformance_state.py::test_projection_ledger_is_not_vacuous` on its `P6 > 0`
assertion. Regenerate the block deliberately, in its own commit, as part of §7 step 7.

⚠ **A dead branch found by controlling that sabotage, recorded so it cannot quietly become
load-bearing.** The narrower sabotage — dropping P6's `and obj[2] != "..."` guard — changes
*nothing*: of the 244 rows surviving P1, 73 have a dotted object predicate and **zero** have
object predicate `"..."` (`"..."` is the bare *subject* sentinel; object nodes carry
relation names). Pinned by `test_p6_bare_sentinel_guard_is_unexercised`.

---

## 7. Suggested ordering (each step green and pushable)

0. ~~Re-measure P6 and put it under the pin.~~ **DONE 2026-08-05** — §6 last block.
1. ~~Settle §8's open question (`evalE`'s modeled arms).~~ **DONE 2026-08-05 — NOT a
   prerequisite** (§8.1). The sizing in §5 stands. What it turned up instead is a real
   obligation *inside* the leg: the **leaf-probe ↔ `directLeaf` bridge**, which slots in
   between steps 4 and 5 below.
2. ~~**Adjudicate the `_classify_edges` ripple** (§6 row 1) on paper before deleting the
   filter, since it silently converts leaf edges into exactly-compared untainted-arm rows.~~
   **DONE 2026-08-08 — see §10. The cell's stated blocker is DISCHARGED and one of its two
   named hazards was refuted; but §10.3 adds a NEW obligation that lands before step 3.**
3. ~~**Additive leaf addressing:** `isLeafPred`, the leaf-name assignment function, and the
   distinctness lemma off `relNameOK` (§3). No behavior change; nothing rebased.~~
   **DONE 2026-08-09** (`GraphIndex/Leaf.lean`, commit `8291c3a`). §3's central bet held:
   no new sentinel axiom. Audits 481 → 487, statements 38/38 and definition pin 155/155
   unmoved.
4. **Fork `writeDirect`** (§4) driving the target off the existing `Delta.leaf` tag.
   Behaviorally identical on `ComputedOnly` by construction — prove that as the leg's
   subsumption lemma, mirroring `w4Fragment_of_computedOnly`.
   **4a DONE 2026-08-09** (commit `41b7029`) — and **§4's prescription is refuted: do NOT
   fork `writeDirect`.** Fork the TUPLE. See §11.1. **4c (re-point the callers) is NOT
   done**, and §11.3 is a design fork this document does not contain.
4b. **The leaf-probe ↔ `directLeaf` bridge** (§8.1) — the spec still evaluates the raw
   def, so once `checkFn` reads a leaf node the two sides need reconnecting. Easiest
   instance of W1's correspondence, but restated over the leaf-name artifact rather than
   an `S.lookup`-declared key. Note the `hag`-premise trap in §8.1.
5. **Re-partition `DerNode`/`UntaintedShadow`** and re-prove the reach-collapse family
   (§5, the deep one).
6. **Re-point the readers**, then the `Inv` stack, then delete `W4NarrowT2a`.
7. **Retire P6 in the gate** (§6) and regenerate the three pins + the ledger, each in its
   own commit with the reason written.

**Per the §C.3 lesson that recurred three legs running: budget a non-vacuity WITNESS for
every step, not just a green build.** A packaging clone with unsatisfiable premises
compiles, audits clean, and passes every pin. And per §C.5: **a rebase needs a different
control than a clone** — the plausible failure here is a half-done step that typechecks
because a conversion lemma papers over it.

**Attack first (house rule 2), before step 3.** ~~The statement to try to refute is
"`Inv.negEdgeFree` holds on the `_d` fragment once writes are leaf-routed". If that is a
KILL, the leg is dead cheap and we have learned something real.~~ **DONE 2026-08-08 —
NO-KILL. The leg is still on at full price.** See §9.

---

## 9. ★ The attack-first probe (2026-08-08) — NO-KILL, plus a witness trap

Run per §7's instruction, in a scratch module since deleted; `lake build` left green
(1084 jobs). Three results, in ascending order of how much they change the leg.

### 9.1 The verdict: NO-KILL

`Inv.negEdgeFree` **HOLDS** under leaf routing on the `_d` fragment. Literal `#eval`, the
triple being *(bare pre-cascade, LEAF pre-cascade, bare drained)* at D.3's exact
schema/store:

```
("A  (bare-pre, LEAF-pre, bare-drained)",
 some ({ edges := 3, rows := 1, negTested := 1, negFree := false, uposFree := true },   -- POSITIVE CONTROL
       { edges := 3, rows := 1, negTested := 1, negFree := true,  uposFree := true },   -- SUBJECT (leaf)
       { edges := 2, rows := 1, negTested := 3, negFree := true,  uposFree := true }))
```

`negFree := false` on the bare leg reproduces D.3's kill **in the same run**; `negTested
:= 1` on both legs proves the comparison ran on the same one `(residue row, neg member)`
pair. The only difference in the entire state is `pred := "approver"` vs
`pred := "approver.0"` on one edge. Stable under a prefix-order swap.

**Do not upgrade this to "confirmed"** (D.2's lesson): it uses the fuel-capped
`GraphState.reach` rather than `NReaches`, and it is one schema shape, two strata, three
tuples, one object, two orders.

**The instrument's first version was WRONG, and vacuously green.** It enumerated the
residue key domain from `σ.nodes` — but under leaf routing the bare R-node is never added
as a live node, so the residue row fell OUT of the domain and the leaf leg reported
`rows = 0`, `negFree := true` for free. The routing change itself emptied the domain. Caught
only by the non-vacuity counts, exactly as in the 2026-07-28 leg-0 sweep. **Anyone
re-running this must keep the key domain routing-INDEPENDENT** (store objects × declared
relations × `.0/.1/.2`). A second control confirms the probe is reachability-sensitive
rather than key-equality-sensitive: adding a hypothetical `approver.0 → approver` bridge
edge to the leaf state turns it red (`negFree := false`).

### 9.2 `uposEdgeFree` was never at risk — §1 and §7 above are WRONG to pair the clauses

`uposEdgeFree` is **structurally immune on the `_d` fragment, independent of leaf
routing.** `StoreValidRulesD` requires `t.subject.predicate = BARE` on a derived key;
`uposCands` is filtered to `predicate ≠ BARE`. So `res.upos` holds only USERSET subjects
and a raw derived write can never land an edge from one. Measured: `uposTested = 0` in
every in-fragment scenario. Confirmed by deliberately leaving the fragment (userset
restriction moved onto an untainted operand): `uposTested = 1..2`, `uposFree := false`, at
a store `StoreValidRulesD` rejects.

**This corrects four documents that inherited the pairing** — §1 and §7 of this file,
`W4NarrowT2a`'s docstring in `FullScope.lean` (corrected 2026-08-08),
`echain-widening-plan-2026-07-28.md` §D.3, and `PROOF_STATUS.md`. **Leg 7's `Inv`-side
obligation is ONE clause, not two.**

### 9.3 ★★ THE WITNESS TRAP — `Sd`/`Td` cannot be leg 7's witness

§7 says "budget a non-vacuity WITNESS for every step", and every pointer in the tree
(both HANDOFFs, this file's provenance, `W4WitnessDirect` itself) aims at `Sd`/`Td` as
"the canonical Direct-arm counterexample". **For this leg that is a trap.**

`negEdgeFree` is **already vacuously true at `Sd`/`Td` today.** At that pair exactly there
is no residue row at all:

```
("Sd/Td exactly: residue after the single Direct-arm write", some none)
("C  (Sd/Td)", some ({ negTested := 0, negFree := true, ... }, { negTested := 0, ... }, ...))
```

`negTested := 0` on every leg. The cause is structural, not incidental:
`Inv.negStarCovered` forces `neg ⊆ star-covered`, and `Sd` carries no wildcard anywhere,
so `stars = []` forces `neg = []`. **This is why D.3 used its own 3-relation schema and
not `Sd`.**

> **Consequence:** a leg-7 step that proves `negEdgeFree` on the `_d` fragment and
> instantiates it at `Sd`/`Td` would be green, audit-clean, statement-pin-clean,
> definition-pin-clean — **and would prove nothing.** This is the §C.5 half-done-leg
> failure mode with a new face, and no mechanical check in the project would object.

The witness must use D.3's wildcard-carrying schema. Concretely, the pair the probe used:

```lean
S := ⟨[(("doc","banned"),  .direct [("user", BARE, false)]),
       (("doc","viewer"),  .direct [("user", BARE, true)]),      -- the wildcard, load-bearing
       (("doc","approver"), .excl (.union (.direct [("user", BARE, false)]) (.computed "viewer"))
                                  (.computed "banned"))], []⟩
prefix := [⟨user:bob, "banned", doc:d1⟩, ⟨user:*, "viewer", doc:d1⟩]   -- cascade to drained
write  := ⟨user:bob, "approver", doc:d1⟩                                -- probe pre-cascade here
```

Any leg-7 witness must carry a `negTested > 0`-style non-vacuity fact, not merely typecheck.

### 9.4 Cost

**§5's 55–65% stands** (independently re-grepped: 64 files, ~41.9k lines). Direction
slightly down: the `Inv` obligation halves per §9.2, and the leaf-NAME function is ~3
lines and needs no new parameter —
`if isDerived S (t.object.type, t.relation) then t.relation ++ ".0" else t.relation`,
which correctly leaves untainted writes on their bare nodes. But §4's caller-side fork is
**confirmed necessary**: `reconcileKey`/`reconcileKeyD`/`reconcileKeyDR` call `writeDirect`
on a derived key and must keep landing on the BARE R-node, so the schema alone is not a
sufficient discriminator and `Delta.leaf`-style caller provenance is genuinely required.
The reach-collapse family and `Audit.lean` are untouched by anything the probe found.
§8.2 (`storage=True`/`storage=False`) remains unmeasured — one undifferentiated leaf per
index sufficed for `negEdgeFree`, which says nothing about TTU stored-parent enumeration.

---

## 8. What is NOT settled

1. ~~**The one question this pass could not answer, and it gates further sizing:** does
   introducing storage leaves require widening `evalE`'s modeled arms first?~~
   **★ SETTLED 2026-08-05 — NO, and the sizing in §5 stands unchanged.** Both halves:
   * **`probeDerived` stays at the bare R-node**, with leaf probes added underneath
     `checkFn` — the Python-mirroring option. The model already routes that way:
     `isDerived S (dt, "R.i") = false`, so `graphRecR` sends a leaf key to
     `probeNonDerived` (`CascadeStrata.lean:94-101`).
   * **Widening `evalE` is NOT a prerequisite — it is orthogonal, and for `direct` it was
     already paid by leg 5.** The concern rested on `ReconcileWrite.lean:56-59`, which leg 5
     made **stale**: `ComputedOrDirect` (`ReconcileCorrect.lean:145-151`) admits `.direct`,
     the read-half lemmas exist (`evalE_computedOrDirect` `:246-269`, `directLeaf_bare_indep`
     `:228-236`, `checkFn_eq_semStep_cd` `:279-290`), and the store is genuinely live on that
     fragment (`CascadeStrataSettle.lean:3094-3099`: "a `Direct` arm reads the store, so
     `checkFnR_store_irrel` is FALSE for CD defs"). `ttu` is not implicated at all —
     verified Python-side that `PDerivedTTU`/`PDerivedComputed` consume **no leaf index**
     (only `PClosureLeaf`/`PDerivedUserset` call `alloc`, `zanzibar_utils_v1.py:1688-1699`,
     `:1754-1763`), so leaf families never arise from a `ttu` plan leaf.
   * **Decisive structural fact:** `Rec = String → String → String → Bool`
     (`Spec/Semantics.lean:27`) places no constraint that the relation be *declared*, and
     `graphRec σ s ot on' r' = probeNonDerived σ ⟨s, r', ⟨ot,on'⟩⟩`
     (`ReconcileWrite.lean:47-48`). So `evalE … (.computed "approver.0")` is **already
     well-formed and already means "probe the leaf node"** — no new `Expr` constructor, no
     arm widening. On the compiled-plan side the split makes the fragment *narrower*: with
     `.direct rs` replaced by `.computed "R.i"`, the tree `checkFn` walks is `ComputedOnly`
     again and `T`/`q` go dead — `ReconcileWrite:56-59` becomes true again.
   * **Nothing in the derived READ path touches `evalE` at all.** `GraphModel.check`
     (`State.lean:589-593`) → `probeDerived` (`:570-585`) / `probeNonDerived` (`:552-561`);
     none of them mention `evalE`/`directLeaf`/`ttuLeaf`/`Store`, and they take no `Store`
     argument. `evalE` appears in exactly two places: the spec `sem`, and the write-time
     guard `checkFn`.

   **★ But the concern was pointing at a real obligation — it just lives INSIDE the leg.**
   The spec side is immovable (`sem` evaluates the raw def, `.direct rs → directLeaf … T`,
   `Semantics.lean:120`). Once `checkFn` reads a leaf *node* instead of the store, the two
   sides stop being the same expression and a new bridge is owed:

   > `probeNonDerived σ ⟨s, "R.i", ⟨dt,on⟩⟩ = directLeaf rec s T q rs dt on R`,
   > given that writes matching `rs` were routed to `objNode ⟨dt,on⟩ "R.i"`.

   Today that equality is free (`directLeaf_bare_indep`: both sides are the same term).
   After the split it is **W1's pure-direct graph↔store correspondence transplanted onto a
   synthetic, undeclared key** — machinery exists (`DirectCorrect.lean`, `RestrictBase.lean`,
   `RulesSound`/`RulesComplete`) but is stated over `S.lookup`-declared keys, and §3 forbids
   putting leaf names in `S.defs`, so it needs restating over the leaf-name artifact. Under
   `DirectArmsBare` + `DirectArmsConcrete` this is the **easiest** instance of that
   correspondence (bare concrete restrictions ⇒ `memberOfGranted` dead by
   `memberOfGranted_of_bareGrants` `:214-220`, no wildcard bridges), not the hardest.
   Add it to §7 between steps 4 and 5.

   ⚠ **One trap, flagged as inference rather than a built result:** you cannot reuse
   `checkFn_eq_semStep`/`_cd` by feeding them the plan tree. Their `hag` premise quantifies
   over `computedRefs e` demanding `graphRec … r' = semAux … r'` (`ReconcileCorrect.lean:103-104`);
   with `r' = "R.0"`, `step` hits `S.lookup (dt,"R.0") = none ⇒ false`
   (`Semantics.lean:127-131`), so the premise is **false whenever the leaf holds an edge**.
   The leg needs a plan-vs-raw-def bridge carrying a per-leaf *bridge* in place of a per-leaf
   *agreement* — a new theorem shape, ~one file, not a fragment widening.
2. Whether the `storage=True` / `storage=False` distinction (§2) needs to be modeled at
   all, or whether one undifferentiated leaf node per index suffices for `Inv`'s purposes.
   Python's reason for the split is TTU stored-parent enumeration, and **TTU parents are
   stored tupleset tuples** (a pinned semantic) — so this probably *does* need modeling,
   but it was not verified in this pass.
3. Whether retiring P6 interacts with the **P3 derived-arm multiplicity** adjudication
   (`CORRESPONDENCE.md` §7.2). Edges moving between arms changes what P3 compares exactly
   vs golden-pins; §6 row 1 is the symptom, but the full interaction was not traced.
4. The 55–65% figure is grep-derived attribution, not a compile experiment. A cheap
   sharpening: fork `writeDirect` locally, `lake build`, and count the errors.

---

## 10. Step 2 adjudicated (2026-08-08) — measured, and §6 row 1 is partly refuted

Read-only measurement pass over all 23 in-fragment corpora, with the P6 branch removed in
a throwaway copy. No repo file was changed to produce this.

### 10.1 The measured facts

* **75** leaf-target `EdgeV4` rows exist (not 73). 73 survive P1 and are the ones P6
  drops; the other **2** are closure-only rows P1 drops first, so retiring P6 does not
  surface them. 16 of 23 corpora contribute; the 7 that do not are exactly the 7 with an
  empty taint set. **Zero** rows anywhere are *sourced* at a leaf node with
  `direct_edge_count > 0` — the class is target-side only, as P6's shape assumes.
* `direct_edge_count` over the 73 is uniformly **1**; `EdgeV4.derived` is uniformly
  **False**; `(obj_type, leaf_pred) ∈ taint` is **False 73/73** while the public pair is
  **True 73/73**.
* **`_classify_edges` does not raise — 0 raises / 23 corpora**, with all 73 landing in
  the untainted arm (untainted 153 → 226; derived arm unchanged at 18; total 244, matching
  §6's prediction).
* **Leaf multiplicity ACCUMULATES and path-dedupes.** Writing the same raw tuple 3× moved
  `viewer.0` 1 → **3** while the derived `viewer` stayed **1**; on a reconvergent diamond
  one write gives leaf dec **1**, not 2. So a leaf row is an occurrence count — the same
  kind of quantity as the untainted arm, and categorically unlike the derived arm's
  presence-diff cap (`CORRESPONDENCE.md` §7.2 item 1).

### 10.2 Verdict on §6 row 1

| clause | verdict |
|---|---|
| leaf edges classify as untainted arm | **CORRECT** — 73/73 |
| whose multiplicity P3 compares EXACTLY | **CORRECT in principle, a non-event on P6 deletion** — the model holds none of these keys, so today deleting P6 yields 73 `only in PYTHON` set-diff lines and **0** multiplicity lines. It becomes real only after the `writeDirect` fork |
| the `:334` justification becomes false as written | **CORRECT — the only genuine defect in the cell.** Fixed 2026-08-08 |
| "it also **raises** on disagreement — settle before deleting" | **REFUTED as a hazard.** Both predicates are structurally False on leaf rows (leaf families live in `compiled.leaf_families`, not `derived_families`, and `_derived_write_ctx` gates on the latter; `.` is reserved in declared names so `compute_taint` cannot emit a dotted pair), so they cannot disagree |
| "★ the non-obvious ripple, and the largest" | **MISATTRIBUTED** — neither named hazard is largest. See §10.3 |

**Net: step 2 was a docstring rewrite plus a positive pin, not a logic change.**
`_classify_edges`' logic is unchanged; leaf edges belong in the untainted arm and routing
them to the derived arm would be actively wrong (it would golden-pin 73 corresponding
comparisons and break `test_derived_arm_multiplicity_ledger`'s uniform-1 assertion the
first time anyone duplicates a tuple). The false sentence is replaced by the structural
argument and pinned by
`test_conformance_state.py::test_leaf_rows_are_structurally_untainted` — deliberately
stated over RAW `EdgeV4` rows, upstream of `_edge_projection`, so it keeps testing the
same property after P6 is deleted.

### 10.3 ★ The actually-largest ripple, which §6 row 1 does not mention — and §8.3 is now settled YES

Retiring P6 interacts with the P3 derived-arm adjudication in three ways. The first two
were anticipated (regenerate `derived_arm_multiplicity.json`, since 23 of the 73 leaf
edges have a Lean public-node counterpart and all are derived-arm ledger keys; and the
untainted arm grows 153 → 226). **The third was not, and it is the largest:**

The 73 leaf edges are produced by the **rule-rewrite** path — exactly where
`CORRESPONDENCE.md` §7.2 item 6 records a known divergence: *the model's `rewriteClosure`
does not dedupe where `RuleSet.apply` does, so on a reconvergent schema the model
over-counts; **no corpus exercises it today***. That divergence was measured end-to-end
through the real `zcli` for the first time on 2026-08-08:

```
a := b or c ; b := d ; c := d ; d := [user]        (one write: alice@d)
  alice -> d1#a   lean=2  python=1    <== DIVERGES (untainted arm, would fire TODAY)

viewer := e but not banned ; e := b or c ; b := d ; c := d
  alice -> d1#e        lean=2   python=1   <== DIVERGES today
  alice -> d1#viewer   lean=10  python=1   <== masked by the derived-arm exemption
```

**After the fork, that masked contribution lands on `viewer.0` — a leaf node, untainted
arm, compared EXACTLY.** So the leg does not merely re-partition existing comparisons; it
moves a recorded, currently-unexercised divergence class into the exactly-compared arm.

It does not block the leg — measured, **no `GRAPH_FRAGMENT` corpus is reconvergent** (the
only non-unit untainted multiplicity across all 23 is `nary_union`'s `alice -> any_of = 3`,
where Lean agrees at 3). But:

> **★ NEW OBLIGATION, ordered BEFORE step 3: add a reconvergent corpus, and settle §7.2
> item 6 first.** Adding one today turns the gate red for a real, pre-existing reason.
> Doing it before the leg starts is what makes any later red attributable to the leg
> rather than to this. Doing it after is how a genuine divergence gets debugged as a leg
> bug — or worse, absorbed into a regenerated golden.

### 10.5 ★ §7.2 item 6 ADJUDICATED (2026-08-08) — MODEL-side, fix it, ~one session

The obligation in §10.3 was worked the same day. **Verdict: the divergence is real, correctly
filed, and MODEL-side. Disposition (a): add a dedup to `rewriteClosure`.**

**It is not a retirement bug — both sides retire correctly.** Measured over a five-sequence
battery (add/remove, partial removal on a two-grant schema, double-add): Python and the model
AGREE on edge presence in every case, and answer parity is clean (0 mismatches over 56 and 108
queries). The model is internally consistent because `removeLoggedRules` folds over the *same*
closure the write folded, so add-k / remove-k cancels exactly.

**It is a UNIT divergence.** Python's `direct_edge_count` counts **live raw tuples**; the
model's `List.count` counts **derivation paths**. Measured, and fuel-stable (so a genuine
path count, not an artifact): `occ "a"` is `1` linear, `2` one diamond, **`4` two chained
diamonds** — i.e. the model's ref count grows with SCHEMA SHAPE, exponentially, rather than
with store content. Nothing in the system wants that quantity.

**The decisive argument is house rule 5, and it is sharper than "the model should match
Python".** `RemoveOccCount.lean`'s opening paragraph *asserts Python's unit*: "`List.count
(a,b)` **IS** the model's `direct_edge_count` (the ref-count maintained by
`ReachabilityIndex._add_direct_edge_unsafe`…)". That sentence is FALSE on any reconvergent
schema, and the same file's attack-first bullet already says so. **The file contradicts
itself, and R3/R4's whole faithfulness claim rests on the wrong half.** Fixing the model is
what makes the sentence true.

Also decisive against fixing Python: its `processed` worklist dedup is the **termination
mechanism**, not an optimisation — measured, `a: [user] or b ; b: a` compiles fine (only
*derived* cycles raise) and would loop forever without it.

**Blast radius is smaller than feared, and this is the key finding.** The count machinery is
**list-generic and survives untouched** — `count_removeLoggedRules` opens with
`generalize rewriteClosure S t = us`, and `count_foldl_writeDirect` is `∀ (us : List Tuple)`.
So `untOccCount`, R3 (`reachedByW3d2E_untOccCount`) and R4 (`RemoveConfluence`) need **no
proof rework**; their values change and their meaning improves. What needs redoing: **15
`unfold rewriteClosure` sites** (mechanical, via one `mem_rewriteClosure_iff` bridge) and **2
list-EQUALITY sites** (`rewriteClosure_derived_eq_seed`, `…_nk`). Minimal-diff shape: rename
the current def `rewriteClosureRaw`, define `rewriteClosure := (rewriteClosureRaw …).dedup`,
add the one membership lemma. `DecidableEq Tuple` exists and `List.dedup` is already used once
in the model, so no new idiom. **~17 declarations, zero count-stack proofs, one session.**

⚠ **The leg's one real risk, flagged as unverified:** Mathlib's `List.dedup` keeps the LAST
occurrence, so write order shifts. Measured topological on both probe diamonds, but that is
luck rather than a theorem — if a proof turns out order-sensitive, a first-occurrence dedup is
the fallback.

⚠ **Ordering within the leg: corpus FIRST (red, attributable, recorded), then the fix
(green).** Adding the corpus alone leaves a red gate; fixing alone leaves the fix unexercised.

**Verified `.dedup` reproduces Python element-for-element** on three schemas (linear, one
diamond, two diamonds) — same sets, order differing only because Python drains a `set`.
Generalisation beyond those three is INFERRED, resting on the existing edge-set correspondence.

### 10.4 Still unmeasured

Post-fork Lean leaf multiplicity vs Python's (the forked model does not exist; the
inference is that leaf nodes receive edges only from the raw-write leg, never from
reconcile emissions, so no cascade compounding — **not verified**); the post-fork
derived-arm golden values; whether a forked `schemaRewrites` double-emits on a
reconvergent schema; and §8.2, untouched.

---

---

## 11. Steps 3 and 4a executed (2026-08-09) — §4 is refuted, §5's sizing is unverified in
## the one direction that matters, and there is a design fork this document does not contain

Steps 3 and 4a landed green (`8291c3a`, `41b7029`); step 4c did not. What follows is what
executing them measured, including the parts that contradict the cells above.

### 11.1 ★ §4 prescribes the wrong fork — fork the TUPLE, not the write path

§4 says `writeDirect` "must **fork** (take a target-node argument, or split into
`writeDirectLeaf` / `writeDirectDerived`), which duplicates or re-parameterizes every
`writeDirect_*` projection lemma … and every fold lemma". That cost is avoidable and the
avoidance is the *more* faithful modelling, not a shortcut:

> **Python does not fork its write path at all.** `RuleSet.apply` re-addresses the TUPLE —
> `replace_relation(triple, f.rewrite_relation)` (`zanzibar_utils_v1.py:447`) — and then
> the ordinary `add_tuple`/`_add_edge_locked` path runs unchanged.

So `rawWriteTuple S t := { t with relation := rawWriteRel S t }` and
`writeDirectRaw σ S t := σ.writeDirect (rawWriteTuple S t)`. Consequences, all observed:

* `GraphState.writeDirect` is **byte-identical** — the headline definition pin does not
  move for a change that changes no meaning (155/155 across both commits).
* Every `writeDirect_*` projection and fold lemma applies to the re-addressed tuple
  verbatim. `structInv_writeDirectRaw` / `inv_writeDirectRaw` are one-line term proofs
  over the originals; §4's predicted duplication of `Write.lean:85,92,171,176,181,186,237`
  and `RulesWrite.lean:122-193` **did not happen and is not owed**.
* The untainted subsumption is stronger than the node-level one §4 implies: on an
  untainted key `rawWriteTuple S t = t` — identity on the TUPLE — so downstream lemmas
  transport by rewriting rather than by a clone (`rawWriteTuple_untainted`).

The same shape should be tried on the removal path (`removeEdgePair`/`removeEdgeOne`,
§4's last paragraph) before cloning anything there.

### 11.2 The step-4c walk — much cheaper than §5 predicts, but the number is a FRONTIER

§8.4 asks for "a cheap sharpening: fork `writeDirect` locally, `lake build`, and count the
errors". Done, and then walked four modules deep, re-pointing `writeRules`
(`RulesWrite.lean:136`) only — it already takes `S`, so no signature change:

| module | errors | what discharged them |
|---|---|---|
| `RulesWrite.lean` | **5** | ONE new lemma, `foldl_writeDirectRaw_eq`. The fold family is stated `∀ (ts : List Tuple)` — **list-generic, exactly like the count stack the dedup leg found** — so a raw fold is an ordinary fold over the re-addressed list and all five corollaries follow with no clone |
| `RulesCorrect.lean` | **1** | `reachedByRules_edge_sound` — the first genuine STATEMENT change of the leg: `b = objNode u.object u.relation` becomes `b = rawWriteNode S u` |
| `RulesChain.lean` | **1** | `rawWriteNode_untaintedSchema` — on `UntaintedSchema` no key is derived, so the routing is the identity and **the entire W2 soundness development is insulated by construction** |
| `RulesComplete.lean` | **4** | not walked |

**⚠ Read those counts correctly. `lake build` does not build the dependents of a failing
module, so each row is the frontier at that moment, not a total.** The 55–65% figure in §5
is neither confirmed nor refuted by this; what IS established is that the first four
modules cost one new lemma, one statement change and one insulation lemma between them,
and that §5's two named cost drivers (duplicating the projection lemmas, duplicating the
fold family) are **not** owed at all under §11.1's shape.

`foldl_writeDirectRaw_eq` is landed and audited; the rest of the walk was reverted.

### 11.3 ★★ THE DESIGN FORK THIS DOCUMENT DOES NOT CONTAIN — where the `Delta` row is addressed

Step 4c cannot be finished without deciding it, and it is why the walk stopped.

`writeLoggedOne` (`Cascade.lean:167-170`) does two things at once: it writes the edge **and**
pushes `pushDelta (objNode t.object t.relation) t.relation true`. Once the EDGE moves to the
leaf node, the delta row's addressing is a separate, unforced choice:

* **(α) the row moves too** — `pushDelta` at the leaf node with the leaf relation. This is
  what Python's outbox literally records, since `_add_edge_locked` emits on the edge it
  wrote. But then `affectedKeys` (`Cascade.lean:433`) must map leaf → public in its
  `leaf = true` own-key branch, and Python does that through a compiled table
  (`_map_deltas_to_keys`'s `isinstance(fam, LeafFamily)` → its derived key), which the
  model has no analogue of. In Lean it would be string surgery on the `.i` suffix.
* **(β) the row stays public** — only the edge moves. `affectedKeys` is untouched, the
  whole cascade/fence stack is untouched. Less faithful to the outbox row; defensible as
  a declared carry only if written down as one.

§4 asserts the `Delta.leaf` tag is "the single biggest cost reducer found in this pass"
because it is "already threaded". That is true for *discriminating* the two write legs and
it is why 4a is cheap — but the tag does not answer this question, because the tag says
*which leg wrote the row*, not *which node the row is keyed at*.

**This needs the house's attack-first treatment before either branch is coded** (rule 2),
and neither branch should be smuggled in as part of a mechanical caller re-point. Note
`writeLoggedOne` also has to gain an `S` parameter under either branch (~58 references,
mechanical), so the branch should be decided first and the churn paid once.

### 11.4 Unchanged and still owed

§8.2 (`storage=True`/`storage=False`, and more than one storage leaf per relation) is
still untouched — `rawWriteRel` deliberately models ONE undifferentiated leaf, index `0`,
and says so in its docstring. §10.4's post-fork multiplicity numbers are still unmeasured
because the fork is not wired to a caller.

### 11.5 ★★ THE FORK IS DECIDED — branch (α), 2026-08-14. Appended, not edited.

`history/` is append-only, so §11.3 above is left as written. **Read this section as its
resolution, and note that §11.3 is wrong in two places.**

**DECISION: (α) — the `Delta` row moves to the leaf node.** Settled by measurement on both
sides; full evidence in `history/PROOF_STATUS.md` 2026-08-14 §1.

* **Python is unambiguous.** `index_v4/models.py::DeltaOutboxV1` has **no relation column
  at all** — the relation IS the object node's `object_predicate`, and
  `index_v4/core.py::ReachabilityIndex._emit` reads it off the edge it just wrote. Measured:
  a raw write emits `id=1 ADDED object=(doc,d1,approver.0)` (LEAF) and the reconcile
  emission is a *separate* row `id=2 object=(doc,d1,approver)` (PUBLIC).
* **The Lean attack-first probe did not refute (α)**, and its control fired: the *half-done*
  (α) — row moved, `affectedKeys` untouched — produces the **empty** cascade key set.

**★ §11.3 IS WRONG IN TWO PLACES, both measured:**

1. *"`affectedKeys` must map leaf → public … which the model has no analogue of. In Lean it
   would be string surgery on the `.i` suffix."* **Both halves false.** `S.keys` +
   `isDerived` IS the analogue (Python's own `LeafFamily` table *carries* the public name
   and parses `.i` only to record the index). And string surgery is **measurably wrong**: a
   `".0"`-stripper returns `none` on `approver.2`, and Python really does route the Direct
   arm of `(viewer but not banned) or [user]` to `approver.2`. **`publicOfLeaf` must be
   INDEX-AGNOSTIC** — match the `"R."` prefix, never a literal `".0"`.
2. *"`writeLoggedOne` also has to gain an `S` parameter under either branch (~58
   references, mechanical), so the branch should be decided first and the churn paid once."*
   **The churn is avoidable entirely.** `GraphState` already carries `schema : Schema`, and
   a `σ.schema`-reading variant is **definitionally equal** to the `S`-parameter one under
   `σ.schema = S` (`subst h; rfl`). Real scale, re-measured: **61 `writeLoggedOne` + 84
   `removeLoggedOne`** mention-lines, not 58. ⚠ It is a trade — signature churn becomes a
   per-site `σ.schema = S` hypothesis, which `writeRules_schema`/`reachedByW3d2_schema`
   already supply.

**★ AND A SCHEDULING CONSTRAINT THIS DOCUMENT DOES NOT CONTAIN, which refutes §7's "each
step green and pushable" AT STEP 4c.** Projection **P6 is a Python-side-only filter**
(`formal/conformance/extractor.py::_edge_projection`). The instant 4c re-points `Exec.lean`'s
driver, Lean emits leaf edges with no Python counterpart and `diff_states` reports every one
of them. **So 4c must co-land with step 7 (delete P6) in a single commit**, paying the
pin/golden regeneration before the `Inv` and reach-collapse work — or 4c lands without
re-pointing the driver and proves nothing end-to-end. Decide this WITH the fork, not at 4c.

**§8.2/§11.4's "open and unmeasured" is now MEASURED, and the answer is negative.**
`rawWriteRel` hardcodes `leafPred t.relation 0`; index 0 is the wrong model, because Python
demonstrably mints indices > 0 for Direct arms. §10.4's post-fork multiplicity numbers
remain unmeasured.

**Also stale in this document, found while resolving the fork** (re-measured against the
live tree, so trust these over the cells above): §6's success figures `P6 73 → 0`,
`compared 171 → 244` are the 2026-08-05 23-corpus era — **live is `P6 76 → 0`,
`compared 189 → 265`**, the THIRD expiry of these numbers in this file, so re-derive them
from `FINAL_REVIEW.md`'s generated block immediately before starting rather than reading
them here. §10.3's "no `GRAPH_FRAGMENT` corpus is reconvergent" is **false** since
2026-08-08b (`reconvergent_diamond`/`reconvergent_derived`), and its `lean=10 python=1`
figure is now `52`. §11.2 credits `rawWriteNode_untaintedSchema` with insulating the W2
development, but **that lemma does not exist in the tree** — the walk was reverted, and 4c
must re-derive it.

### 11.6 ★★ 4c-AS-SCOPED IS REFUTED BY CORPUS MEASUREMENT — the allocation must be modeled
### first, and the RULE copies need provenance the model does not carry. 2026-08-15.

Attack-first, before any caller was re-pointed. The question asked: **can the landed
routing (`rawWriteRel … := leafPred t.relation 0`) meet the landing criterion
(`dropped by P6 → 0`, `compared → 265`)?** The answer is NO, twice over, and coding 4c
first would have discovered it only after paying the full recompile cone.

**Measurement 1 — the 76 P6-dropped rows, enumerated per corpus** (via
`extractor.py::graph_fragment_ledger`'s own drive loop; total reconciles to the generated
block's 76 exactly): **17 of 25 `GRAPH_FRAGMENT` corpora mint leaf indices 1 and 2.**
Every non-first boolean arm gets its own leaf (`viewer.1 = banned` in `boolean_exclusion`,
`rhs.2` in `demorgans`, `all_of.2` in `nary_intersection`, `viewer.2` in
`double_exclusion`/`nested_boolean`, `any_of4.2` in `nary_union_derived4`); in
`direct_arm_exclusion` the subtract arm is `approver.1`. Zero subject-side dots. An
index-0-only model diffs on most of the fragment the moment P6 is retired.

**Measurement 2 — the allocation rule and the raw-write fan-out** (live compiles +
`RuleSet.apply` driven directly):
* `_build_plan_tree` allocates **pre-order over persisted-leaf positions**: a `Direct`
  block mints one storage leaf; a computed ref mints one closure leaf **iff untainted**
  (derived refs consume NO index); a TTU arm mints **iff pure** — a
  `derived-ttu`/`derived-tupleset-ttu` node consumes no index, so under a tainted TTU
  target the *next* arm inherits index 0.
* A raw write **fans out to EVERY matching storage leaf** (deduped):
  `approver: [user] or ([user, employee] but not banned)` routes `user:alice` to BOTH
  `approver.0` and `approver.1`. So `rawWriteRel : … → String` was wrong in ARITY as
  well as index.

**What landed (4c-pre, 2026-08-15, additive + a rework of the still-unwired 4a layer):**
`Leaf.lean::persistedLeaves` (the allocation, with a declared TTU-target deviation —
`derivedAnywhere` vs Python's frozen `parent_types`), `::leafPublic`/`::publicOfLeaf`
(the (α) map, index-agnostic by construction; `publicOfLeaf_rawWriteRels` is the round
trip `affectedKeys` will consume), and `::rawWriteRels`/`::rawWriteTuples`/
`::GraphState.writeDirectRaw` (the measured fan-out; `RulesWrite`'s list-generic fold
family still discharges everything with no clone). Five sabotages, each reddening its
own pin with controls green — literal outputs in the `LeafWitness` section docstring.
Audits 501 → 520. `String.contains` does not kernel-reduce, so `isLeafPred` moved to
`toList.contains` — keep new leaf-layer defs `toList`-based or `decide` pins stall.

**★ THE CONSEQUENCE FOR 4c's REMAINING SHAPE, and it is structural.** The 76 dropped
rows are mostly **rule-copied closure-leaf edges** (`viewer.0 = the editor arm's copy`),
and the correct index is a function of **which arm produced the copy** — provenance
`rewriteClosure` does not carry (its members are bare tuples; for
`viewer: editor but not banned` the `editor`-arm and `banned`-arm members are
shape-identical, yet Python routes them to `viewer.0` vs `viewer.1`). **No re-addressing
function of the tuple alone can produce Python's leaf edges.** Python bakes the leaf
target into the compiled rule (`RewriteFilter.rewrite_relation`); the faithful model
does the same: **the rule layer (`schemaRewrites`/`exprArms`/`rewriteClosure`) must mint
leaf-indexed target relations for tainted keys**, positioned by `persistedLeaves`. That
is a rules-model change UNDER `RulesWrite.lean`, i.e. the recompile cone is the full
GraphIndex tree, roughly double the 19-module Cascade cone. Steps for a next session:
* **4c-i:** leaf-indexed rule targets for tainted keys (today `schemaRewrites` emits no
  arms for derived keys at all — the taint filter — so this is an EXTENSION, not an
  edit of the untainted path; the untainted fragment must stay byte-identical).
* **4c-ii:** re-point `writeLoggedOne`/`removeLoggedOne`/`writeRules` through the raw
  layer; move the `Delta` row to the leaf per (α); `affectedKeys` own-key branch via
  `publicOfLeaf` with **`d.leaf = true` kept the LEADING conjunct** (PROOF_STATUS
  2026-08-14's binding condition) — `publicOfLeaf_rawWriteRels` is the feeder lemma.
  `foldAdmitsB`/`FoldAdmits` must move their admission probe in lockstep or `graphRunAux`
  admit-checks a different edge from the one it writes.
* Then 4b / 5 / 6 / 7 as ordered in §7, with 4c-ii + 7 still forced to co-land.

### 11.7 ★★ STEP 4c-i LANDED (2026-08-16) — the cone estimate is REFUTED, and the
### allocation was wrong three more times, once invisibly to its own instrument

`history/` is append-only, so §11.6 stands as written. Read this as its resolution.

**§11.6's cost cell is REFUTED.** It sized 4c-i as *"a rules-model change UNDER
`RulesWrite.lean`, i.e. the recompile cone is the full GraphIndex tree, roughly double the
19-module Cascade cone."* That is true only of an **edit** to `schemaRewrites`. 4c-i is an
**extension**, so it landed as `GraphIndex/LeafRules.lean` DOWNSTREAM of `RulesWrite` and
the cone is **one file**. Verified cycle-free for 4c-ii: `Cascade.lean` imports
`ReconcileDiff` (far downstream of `RulesWrite`) and `Leaf.lean` imports only
`Write`/`RulesWrite`/`Spec.Stabilize`, so the `Cascade → LeafRules` import 4c-ii needs
introduces no cycle. **The cone is paid once, at 4c-ii — do not budget it twice.**

**What landed:** `keyLeafRewrites`/`leafRewrites`/`schemaRewritesL` (each derived key's
CLOSURE leaves compile to rewrite rules targeting the minted leaf name — Python's
`_emit_leaf_expr` → `_rewrite_rule(expr, object_type, leaf)`), the seed-list
generalisation `rewriteClosureL` (mirroring `RuleSet.apply`'s two stages: the
`RewriteFilter` fan-in builds `seeds`, then the `processed`-deduped worklist fires every
`Rule`), and `GraphState.writeRulesRaw` — the shape 4c-ii re-points callers at. Additivity
is **proved**, not observed: `schemaRewrites_leafRewrites_disjoint` (untainted rules target
declared dot-free names, leaf rules target minted dot-carrying ones) and
`writeRulesRaw_untaintedSchema`. Model diffed against the `Rule`s `compile_ruleset` emits:
**50/50 schemas, 0 mismatches, 32 with a non-empty leaf rule set.**

**★★ THE ALLOCATION §11.6 LANDED WAS WRONG THREE MORE TIMES**, all found before 4c-i was
built on it:
1. **Python MERGES a maximal pure subtree** (`_split_pure`): at most TWO leaves, storage
   first. `(a or b) but not banned` → `r.0={a,b}` / `r.1=banned`, not three leaves.
2. **A tainted userset restriction gets its OWN storage leaf** — reachable from the LIVE
   fixture `tests/fga_schemas/userset_over_derived.fga::doc#editor`.
3. **★ The one the instrument could not see.** (1)+(2) were validated by transcribing
   `persistedLeaves` into Python — *"82/82, 0 disagreements"* — but that transcription
   consumed Python's **n-ary** AST. `formal/conformance/encode.py::_fold_binary`
   **left-folds**, so Lean receives a tree whose left spine is pure by accident of the
   folding. Re-run binarized: **1 disagreement, on `nary_union_derived4`, which is IN
   `GRAPH_FRAGMENT`** — Python allocates three leaves, the model merged them into one.
   Fixed by `unionSpineLeaves`; re-diffed binarized, 0 disagreements.

**★★ A LIMIT OF THE BINARY `Expr` THAT NO FIX IN `Leaf.lean` CAN CLOSE, and leg 7 must
carry it.** `Core/Schema.lean` justifies left-folding n-ary unions by associativity and
commutativity — **true of `sem`, FALSE of the leaf allocation.** Measured: `a or b or safe`
→ 2 leaves, `(a or b) or safe` → **1**, and `_fold_binary` maps both to the same `Expr`.
The model is faithful to the FLAT form (the only form any corpus writes); the other shape
is refused mechanically at
`formal/conformance/test_conformance_state.py::test_no_corpus_nests_a_pure_union_inside_an_impure_one`,
sabotage-verified. If leg 7 ever needs the parenthesized form, `Expr` must go n-ary — a
trust-root change, out of this leg's scope.

**Also stale in this document, re-measured 2026-08-16:** §11.6's *"17 of 25 `GRAPH_FRAGMENT`
corpora mint leaf indices 1 and 2"* **overstates the index-2 breadth 3.4×**. Live: index
≥ 1 in 17 of 25; index 2 in **5** (`demorgans`, `double_exclusion`, `nary_intersection`,
`nary_union_derived4`, `nested_boolean`); histogram 0 ×43, 1 ×28, 2 ×7. The load-bearing
half survives.

**Next:** 4c-ii (caller re-point + (α) row move + `affectedKeys` via `publicOfLeaf`,
`d.leaf = true` LEADING) **co-landing with step 7**, then 4b/5/6. Criterion re-derived from
`FINAL_REVIEW.md`'s generated block and unchanged: `dropped by P6` **76 → 0**, `compared
against Lean` **189 → 265**.

### 11.8 ★★ 4c-ii IS BLOCKED ON A PROOF-DESIGN ADJUDICATION, NOT ON CODING (2026-08-16c).
### The shadow chain's cheap route is refuted, and §11.7's "Next" cell understates the step.

`history/` is append-only, so §11.7 stands as written. Read this as the resolution of its
**Next** cell. Full detail and every quoted line: `history/PROOF_STATUS.md` 2026-08-16c.

**§11.7's "Next: 4c-ii (caller re-point + (α) row move + `affectedKeys` via `publicOfLeaf`)"
is not a caller re-point either.** Re-pointing the callers forces a decision about the
`ReachedByRulesAdmitted` shadow chain, and the cheap branch is **refuted**:
`ReconcileComplete.lean:164` needs a `ReachedByRules σ S T` witness for a
`writeRulesRaw`-built σ, and `LeafRules.lean:461::lrV_writeRulesRaw_edges_ne` already
machine-checks that those two states' edge sets **differ**. The surviving branch weakens
`UntaintedShadow`, which is a slice of board row `P14` — filed `deps: P4`, which is filed
`deps: P3`, so the board's own dependency graph closes a cycle here. **Settle this before
paying any cone.**

**Two further cells of the step plan are refuted by measurement, both in the tree today:**

* The own-key theorems cannot be re-proved from "some member of a multi-element leaf list
  dirties the key". On the `ComputedOnly` fragment the list is **empty** — `Leaf.lean:401`
  gives `[]` for a derived `.computed` arm and `Leaf.lean:551` maps `.closure _ => none` —
  so `writeLeg_own_key_dirty` becomes FALSE there, and what it needs is a non-emptiness
  premise (`StoreValidRules`), not `WF`.
* The `FoldAdmits`/`foldAdmitsB` lockstep is **24 spelled-list sites**, not the seven
  `write` constructors: thirteen theorem hypotheses carry the same list, plus
  `Exec.lean:72` and `:376`.

**★ AND THE LANDING CRITERION THIS DOCUMENT HAS CARRIED SINCE §11.5 IS WEAK.** *"`dropped by
P6` 76 → 0, `compared against Lean` 189 → 265"* is a pure function of the **Python** side:
commenting out the two-line P6 branch at `formal/conformance/extractor.py:236-237`, with no
Lean file touched, makes `doc_counts.measure()` publish `{'P6': 0, 'compared': 265}` exactly.
The control is what saves it — the same probe leaves the state gate at **19 failed, 37
passed**, reporting the leaf edges as `only in PYTHON`. So the criterion is only a criterion
**conjoined with `conf-tile` green**, and it must be written that way. (Note also that
§11.5's predicted direction is the mirror of what a Python-first order produces: `only in
LEAN model` vs `only in PYTHON`.)

**Two gate facts the step plan must carry**, neither of which any regeneration can repair:
`Audit.lean:314` `#print axioms reachedByRules_of_admitted` reddens `verify.sh lean` the
moment that theorem is deleted (so `Audit.lean` is an EDITED FILE of this step, not just a
build target); and `test_conformance_state.py:377-378`'s `_MIN_LEDGER_ROWS`/
`_MIN_LEDGER_STACKED = 19/19` are asserted at `:516`, before the golden read, over exactly
the multiplicity leg 4c-ii moves.

### 11.9 ★★ THE §11.8 ADJUDICATION IS SETTLED (2026-08-20): the `UntaintedShadow`
### weakening is SOUND, it is HALF of P14 (the classification half), and a third route
### exists — full evidence `PROOF_STATUS.md` 2026-08-20b, pins `GraphIndex/Scratch4cii.lean`

`history/` is append-only, so §11.8 stands as written. Read this as its resolution.

**The weakening is sound — no-kill at all six `LeafRules.lean` witnesses, both chains,
with the instrument proved (`Scratch4cii.lean::derNodeB_correct`) and controlled (the
clause-2 probe under `derNodeB` alone observed `false` at `SlV`).** Every σ-only extra
of `writeRulesRaw` over `writeRules` is leaf-targeted under the `publicOfLeaf` carrier;
leaf nodes are never edge sources; no rule reads a leaf predicate (the `SlStP` TTU arm
mints the DECLARED subject predicate, not a leaf name). The `by decide` pins re-run the
battery on every build.

**Three corrections to the framing §11.8 inherited:**

1. **The adjudicating proposition is per-chain, not global.** On the `StoreValidRulesD`
   chain a derived-key Direct-arm write makes `writeRules ⊆ writeRulesRaw` FALSE
   (pinned, `slSwD_not_mono`): today's write keeps the closure seed at the PUBLIC
   R-node, the raw write routes it to the storage leaf. That refutes the scout's (★) as
   stated and kills nothing: on the shadow chain that write is a σ-only extra with σ0
   held FIXED (`untaintedShadow_writeLoggedOne_derived` is the landed template), and
   the measured fact is a clean classification SWAP — `(derNodeB, leafNodeB)` goes
   `(true, false) → (false, true)` on the same edge, at index 0 and at `SwU`'s index 2.
   The weakening is exactly that swap.
2. **§11.8's "the surviving branch" undersells the option space: Route C exists** —
   widen `RulesWrite.lean::ReachedByRules.step` itself onto `writeRulesRaw`, leaving
   `DerNode`/`UntaintedShadow` untouched and `reachedByRules_of_admitted` true by
   construction. It survives the battery too, but its recompile cone is the whole
   GraphIndex tree (vs Route B's zero-additional — `CascadeStable` is inside the cone
   4c-ii pays anyway), and with σ0 raw-built the read bridges need the SAME
   leaf-terminality lemmas relocated into the W2 chain. **Recommended: Route B; the
   fork is a human call and both budgets are in `PROOF_STATUS.md` 2026-08-20b §3.**
3. **The `P3 → P14 → P4 → P3` cycle breaks by SPLITTING P14, not by merging items.**
   Route B absorbs only P14's classification half (~123 mention sites re-verified
   2026-08-20: `DerNode` 39/3 files, `UntaintedShadow` 84/7 files; template lemmas
   exist). The reach-collapse half is untouched because clause 2 keeps leaf edges off
   declared R-nodes, so `reachedByRules_derived_no_inedge` and the collapse family
   survive verbatim. Split the board row into `P14a` (classification — into `P3` under
   Route B) and `P14b` (reach-collapse — stays `deps: P4`).

**The §(c) starvation residual is answered (one witness, no-kill):** `edgeHolders` at
the public R-node starves (`[alice] → []` at the `Sw` derived write) but
`storedDirectSubjects` reads the STORE and still yields the candidate — so 4c-ii + 7
stays a closed cone and P4 owes the leaf-probe bridge for edge-side READS, not a
candidate-set rescue (pinned, `slSwD_starvation`).

**Two carrier facts the Route-B implementer must not lose:** the `LeafNode` carrier is
`publicOfLeaf`, never `isLeafPred` (sabotage (Sa): nine reds, all on the BARE sentinel);
and `relNameOK` permits the EMPTY relation name while `leafPublic BARE = ""`, so carry
`leafPublic p ≠ ""` (or a WF nonempty-name clause) or prove `""` undeclarable.

### 11.10 Traps for the 4c-ii cone — demoted from `HANDOFF.md` 2026-08-20b (board overflow)

These were carried on the board's `P3` block. Moved here, per `docs/README.md` §4's defined
overflow move, when the board hit its trap budget; the board keeps a pointer to this section.
They are the mechanics that have each cost a session, and they are unchanged by Route B.

* ⚠ **The own-key premise is BACKWARDS.** On the `ComputedOnly` fragment the leaf list is
  EMPTY, not multi-element (`Leaf.lean::atomLeaves`, `::rawWriteRels`), so
  `writeLeg_own_key_dirty` goes FALSE and needs a non-emptiness premise (`StoreValidRules`),
  not `WF`.
* ⚠ **Keep `d.leaf = true` as the LEADING conjunct** of the own-key guard: the
  `rw [hleaf]; simp` discharges depend on that order, and there are **four**, not three.
* ⚠ **It CANNOT be split** — the un-buildable window is the whole cone, not a step. A
  half-started re-point leaves the tree red across a session boundary with no green phase to
  resume from.
* ⚠ **`FoldAdmits` lockstep is 24 spelled-list sites**, not the 7 `write` constructors, and
  `Audit.lean` is an EDITED file of this step (it carries the
  `#print axioms reachedByRules_of_admitted` pin).
* ⚠ **Expect a deliberate golden regen — but `derived_arm_multiplicity.json` needs a DERIVED
  expectation, not a re-recording**, and
  `test_conformance_state.py::_MIN_LEDGER_ROWS`/`::_MIN_LEDGER_STACKED` (19/19) are asserted
  *before* the golden read, so no regeneration repairs them.
* ⚠ **Route B's equivalence argument is polarity-dependent.** It holds only because
  `UntaintedShadow` sits in hypothesis position at every lemma whose conclusion leaves the
  shadow layer. Putting a shadow-mentioning term in a headline-reaching conclusion kills it —
  re-run the census in `PROOF_STATUS.md` `2026-08-20b` §7 before assuming it survives.
* ⚠ **Route B stops supplying σ/σ0 agreement at leaf-node targets.** Nothing probes those
  today; the post-4b derived read path will, and that surface is board row `P4`. Do not
  cancel `P4` without revisiting this.

### 11.11 ★★ LIVE CENSUS RE-RUN (2026-08-28) — the census hole PROPAGATES (~45 second-ring
### sites, 4 files with zero `UntaintedShadow`), so Route B's "ZERO additional cone" — the
### sole stated ground for preferring it over Route C — is FALSIFIED. Polarity (trap 6)
### holds. The `hql` guard is CHEAP and terminates at depth 2. NO Lean declaration changed.

**Method.** Six read-only census agents over the live tree (`.lake` excluded), commissioned
because this item's sizing had already come in low twice. Nothing was edited. The two
load-bearing claims below were re-verified FIRST-HAND, not taken from a report:
`Core/Schema.lean::WF` is a one-field structure (`relNames : ∀ p ∈ S.defs, relNameOK p.1.2`,
declared key names only — its own docstring calls it a "Placeholder"), and
`ReconcileStars.lean:615::checkFn_agree_of_graphRec` quantifies `r'` INSIDE the helper
(`hag : ∀ s' r', isDerived S (dt, r') = false → …`). Counts marked (delegated) below are
agent-reported and re-derivable, not hand-verified. Gate state at time of writing: clean
tree, all ten phases green on `t2a:b73c66415942`.

**1. ★★ THE CENSUS HOLE IS NOT 14 REPAIRS — it propagates, and ZERO of the 14 are
mechanical today.** `PROOF_STATUS.md` 2026-08-21b §2 frames it as "a new hypothesis on an
audited signature plus 14 call-site repairs"; that phrasing reads as a terminal count and is
not one. The 14 sites split three ways:
* **12-14** (`graph_correct_w3d` `CascadeSettle.lean:1119`, `graph_correct_w3d2`
  `CascadeStrataResettle.lean:1539`, `_d` `:2683`) take the QUERY relation and need exactly
  the `hql` guard — **already inside §1's budget, not new work**.
* **1-3** (`CascadeEnum.lean:366`, `CascadeStable.lean:959`,
  `CascadeStrataSettle.lean:3943`) push the hypothesis into `checkFn_agree_of_graphRec`
  ITSELF, which has two further callers — `ReconcileDiff.lean:694` and
  `ReconcileStarsComplete.lean:1021` — in files with **zero `UntaintedShadow` mentions**.
  `ReconcileDiff.lean:694` has neither `hWF` nor `hlk` to derive the fact from.
  (`checkFn_agree_of_graphRec_cd` at `:629` can be left alone, sparing four more sites.)
* **4-11** change signatures of theorems used ~45 times in total (delegated count), reaching
  `Equiv.lean`, `FullScope.lean`, `CascadeStrataAssemble.lean`, `CascadeEnum.lean`.

**Why none are mechanical: nothing in the tree gives dot-freeness of a computed ref.** `WF`
constrains declared key names only; `RewriteMatchDeclared` (`RestrictBase.lean:289`)
constrains rewrite MATCH keys, not def refs. The alternative repair — a `WF` clause
`∀ p ∈ S.defs, ∀ r ∈ computedRefs p.2, relNameOK r` — is not free: `WF` is pinned in
`headline_definitions.txt:103` WITH its field list, so the clause turns gate step 4c red
until deliberately regenerated, and every `WF` witness in `LeafWitness`/`W4Witness*`/
`FullScope` must be re-discharged.

**2. ★★ ROUTE B's SELECTION ARGUMENT IS FALSIFIED, and the fork returns to the user.**
§11.9 and `PROOF_STATUS.md` 2026-08-20b §3 recommend Route B over Route C on ONE stated
ground — Route B's **"Cone: ZERO additional"** (`CascadeStable` is downstream of `Cascade`,
inside the 39-module cone 4c-ii pays anyway) versus Route C's whole-GraphIndex cone. Per
item 1, Route B reaches **at least four files outside that cone**: `CascadeEnum`,
`ReconcileStars`, `ReconcileDiff`, `ReconcileStarsComplete`. The gap between the routes is
materially narrower than when the recommendation was made. **This does not by itself flip
the recommendation** — Route C still owes the same leaf-terminality lemmas relocated into
the W2 chain (2026-08-20b §3), which was a substantive objection and is unaffected. But the
comparison no longer holds on its stated grounds, and the fork was a human call the first
time. ⚠ Do not read this as "Route C is now preferred"; read it as "the basis for
preferring B is gone and the choice is open."

**3. THE `hql` GUARD IS CHEAP — 8 declarations, propagation terminates at DEPTH 2.** Not
"~10 headlines plus dependents cascading". `graph_correct` is the only one of the six with
any term-level consumers; the other five have none. Full threading list (delegated):
5 one-token thread-throughs where the consumer is already in the change set
(`FullScope.lean:383/398/411`, `Exec.lean:159/479`), plus **two genuinely new signatures** —
`W4WitnessDirect.final_applies` (`FullScope.lean:1234`) and `.final_applies4` (`:1366`),
which have no Lean consumers, hence depth 2. Pin impact: `audited_theorems.txt`
**UNTOUCHED** (it is a NAME superset pin; no name changes, so `regen_audit_pin.sh` output is
byte-identical); `headline_statements.txt` 8 rows; `headline_definitions.txt` **grows** —
`publicOfLeaf`, `leafPublic`, `isLeafPred` enter the headline dependency closure for the
first time, and that is the one pin diff that is not mechanical to eyeball.

**4. ⚠⚠ THE GUARD LANDS ON THE NON-VACUITY INSTRUMENT — unrecorded by 2026-08-21b.**
`W4WitnessDirect.final_applies` is not an ordinary consumer: `FullScope.lean:1181` names it
**"★ THE LEG-5 INSTRUMENT"**, the sabotage-controlled witness whose whole job is to show
`graph_correct` is not vacuous at `[user] but not blocked`, and whose own docstring states
the failure mode it guards ("would still compile, still audit with standard axioms only,
and still pass the identity, statement and definition pins — while saying nothing at all").
`hql` is genuinely FALSE there: `Sd` declares `doc#approver := [user] but not banned`, so
`approver` is derived and `publicOfLeaf Sd "doc" "approver.0" = some "approver"` by
`Leaf.lean:499::publicOfLeaf_leafPred`; with `q` universally quantified the guard is not
dischargeable and must become a binder. **So landing `hql` naively puts a hypothesis on the
instrument that exists to detect vacuous hypotheses.** Mitigation, owed in the same commit:
pair each witness with a concrete-`q` corollary whose `hql` is discharged `by decide`, so a
hypothesis-free claim survives at a real query. Verified first-hand (`Sd` at
`FullScope.lean:821`, `publicOfLeaf_leafPred` at `Leaf.lean:499`).

**5. Trap 6 (polarity) HOLDS — the one piece of unambiguous good news.** Full mechanical
polarity census of every declaration mentioning `UntaintedShadow` (delegated): **19 in
conclusion position, all staying inside the shadow layer** (15 preservation lemmas, 3
existence lemmas of the form `∃ σ0, ReachedByRulesAdmitted σ0 S T ∧ UntaintedShadow S σ σ0`,
and one NEGATED occurrence `Scratch4cii.lean:332::strong_shadow_false_at_raw`); **28 in
hypothesis position**, including every lemma whose conclusion leaves the shadow layer; and
**zero occurrences in `headline_statements.txt` / `headline_definitions.txt` / `Equiv.lean`
/ `FullScope.lean`**. Route B's equivalence argument is intact on its own terms. What
threatens it is item 1, not polarity.

**6. Route B's site budget is ~136 / 8 files, not ~123 / 7.** Every file in the 2026-08-20b
distribution matches its claimed line count EXACTLY; the gap is `GraphIndex/Scratch4cii.lean`
(`UntaintedShadow` 5 lines, `DerNode` 8), absent from both claimed lists because it is the
pin module that same session created. Live: `UntaintedShadow` 89 lines / 8 files, `DerNode`
47 lines / 4 files (delegated). Third consecutive low sizing on this item.

**7. `FoldAdmits`: the "21 / 3" and "24" counts differ only by CONVENTION — write the
convention down.** Live strict Prop-hypothesis sites on a chain state: **22** (19 move + 3
stay). The 2026-08-21b "21 move + 3 stay = 24" reconciles only if the two `foldAdmitsB`
RUNTIME GATES (`Exec.lean:72` in `graphRunAux`, `:376` in `graphRunOpsAux`) are counted,
which do move in lockstep. The three STAY sites are confirmed live at exactly their cited
lines: `RulesComplete.lean:91` (`ReachedByRulesAdmitted.step`, `hadm`),
`RestrictBase.lean:470` (`exists_admitted_restrict`), `:531`
(`exists_admitted_ofAcyclicTarget`). No tree drift. §11.10's bare "24" is superseded and,
read alone, also loses the fact that three sites must NOT move.

**8. Corrections to §11.10's other traps** (append-only, so they are recorded here, not
edited above):
* Trap 1 — substance holds, phrasing imprecise. `atomLeaves` returns `[]` on `.computed R`
  only when the operand is DERIVED (`Leaf.lean:404`); on the normal untainted shape it
  returns a singleton. **The emptiness that actually bites is at `rawWriteRels`**
  (`Leaf.lean:541`), not `atomLeaves`. And the named non-emptiness premise should be
  `StoreValidRulesD`, not `StoreValidRules` — the latter + `ComputedOnly` admits no stored
  derived-key tuple at all (`Scratch4cii.lean:113-118`), making the case vacuous.
* Trap 2 — the FOUR `rw [h…leaf…]; simp` discharges are confirmed exactly
  (`Cascade.lean:810`, `CascadeStrata.lean:1286`, `:1345`, `CascadeStrataSettle.lean:2044`),
  but **three further sites are order-dependent on the same conjunct and are not `rw`-shaped**,
  so the trap's phrasing does not cover them: `CascadeStrataSettle.lean:3190` and `:3243`
  (`refine ⟨rfl, ?_, ?_⟩`, proving the leading `d.leaf = true` by `rfl`) and
  `CascadeEnum.lean:491-494` (`by_cases` then positional `obtain`). Safer statement: **7
  order-sensitive sites, 4 of them `rw`-discharges.**
* Trap 5 — holds fully, mechanism re-verified: `_MIN_LEDGER_ROWS`/`_MIN_LEDGER_STACKED` are
  both 19 (`test_conformance_state.py:377-378`), computed from live `observed` at `:514-515`
  and asserted at `:516`, while the golden's only read is at `:545` and its write is in the
  not-`exists()` branch at `:541` — so no regeneration repairs a floor failure. ⚠ But
  **§11.10's own neighbourhood carries a stale cross-ref at line 281** of this file, still
  saying `_MIN_LEDGER_ROWS = 18` at `:94` with the assertion at `:228`. §11.10 is right; :281
  is wrong.

**9. A gate blind spot, recorded for its own sake.** Changing `shadow_graphRec_agree`'s
signature does **not** trip the gate. It is audited (`audited_theorems.txt:501`,
`Audit.lean:790`), but step 4a pins NAMES as a superset check; it is in neither headline pin
(it is a theorem, so not in 4c's definition closure) and has no `CORRESPONDENCE.md` anchor.
Only `lake build` catches the 14 sites. The gate detects the CLAIM weakening downstream once
`hql` lands, and is blind to the audited signature change itself — a small instance of the
house failure mode located in the audit pin.

**Owed before 4c-ii lands (unchanged in kind, re-sized here):** the `hql` acceptance is
still the human call recorded at `PROOF_STATUS.md` 2026-08-21b §1, and item 2 above adds a
SECOND: whether Route B survives losing its selection argument. Neither is settled by this
census.

### 11.12 The revert-to-green exit for the 4c-ii cone (declared 2026-08-28d)

Demoted here from `HANDOFF.md` (board line-ceiling); the board keeps the two rules that
decide whether the exit exists at all, and points here for the rest. Both `HANDOFF.md` and
`tasks/P3` had *required* a declared exit since 2026-08-28c; a repo-wide grep found the
requirement in those two places and the plan in none. §11.11 and `PROOF_STATUS.md`
2026-08-28c §5 are why one is needed: the cone is **un-splittable** — the headline theorems
are kernel-`decide`-proven FALSE between the re-point and the guard landing — so there is
no green intermediate state to stop at, and "I'll just finish it next session" is not
available. Five rules, each with the failure it prevents.

1. **The green anchor is a commit sha, not a stash.** Before opening the cone, `git log -1`
   must name a commit that `python scripts/gate_status.py` calls COVERED on this tree.
   Write that sha into the session-log entry FIRST. The exit is `git reset --hard <sha>`;
   without a recorded sha there is no exit, only a diff nobody can evaluate.
2. **Declare the abort trigger up front, in cycles.** In-cone `lake build` is **200–400s
   and serial** (one tree compiles; subagents do not change that — 2026-08-28c §5), so
   "try one more repair" has a price you can count before paying it. A wall-clock time or
   a context fraction, fixed when the cone opens, not renegotiated at 90%.
3. **Write the findings down BEFORE reverting.** Which sites broke, in what order, with
   what error — that is the session's whole yield if the cone does not close, and it makes
   attempt *n+1* cheaper than attempt *n*. It goes in `PROOF_STATUS.md`, which is
   append-only and therefore survives the reset. Not `.scratch/`: the reset does not touch
   it, but the repo does not keep it (`CLAUDE.md`, the `P7` precedent).
4. **Two things the revert deliberately does not undo**: rows already appended to
   `.gate-runs/ledger.tsv` (gitignored — a red row is evidence the attempt happened) and
   anything already appended to `formal/history/`. Do not tidy either; the record of a
   failed attempt is not damage.
5. **Never commit a partial cone to "save progress".** A mid-cone tree is one whose own
   pins assert something untrue, which is worse than no progress — it is the fail-by-
   passing shape this repo has a standing procedure for. Green or reset.

### 11.13 ★★ THE MIDDLE SPLIT TOO (2026-08-30c) — the shadow is now GENERIC in its extras
### predicate, so the widening is a one-line re-instantiation; and §11.7/§11.11's "42
### modules" is a MIS-ROOTED census — the real recompile cone is 21

Appended, not edited. Full record: `PROOF_STATUS.md` `## Session 2026-08-30c` §0–§6.

**1. The un-splittability was an artefact of the plan, not of the cone.** §11.12 exists
because the recorded step 3 widens `UntaintedShadow.classify` *in place*, going red until
`hql` lands at step 10. That conflates two separable things: making the shadow chain
**able** to carry a wider extras set, and **widening** it. `CascadeStable.lean` now carries
`structure ShadowOver (P : NodeKey → Prop)` — `classify` and `term` both quantified over
`P` — with `abbrev UntaintedShadow S σ σ0 := ShadowOver (DerNode S) σ σ0`, and
`shadow_reach_agree` / `shadow_admitEdge_agree` / `untaintedShadow_writeLoggedOne` /
`::writeLeg` / `::foldAdmits` generalized over `{Extra}`. **`abbrev` is load-bearing**: it
is reducible, so every field access, anonymous constructor, `rcases` and signature kept
working unchanged. Observed: `lake build` green, **1089 jobs, three in-cone cycles against
a ten-cycle abort budget**; the 65 `UntaintedShadow` sites in `CascadeStrataSettle.lean`
and the whole `CascadeSettle`/`CascadeEnum`/`CascadeStrataEnum`/`CascadeStrataAssemble`
chain never went red. §11.12 is NOT weakened — what remains after the re-instantiation is
still a genuine red window — but it is now ~20 sites in 3 files, not the whole chain.

**2. The sizing figures in §11.7 and §11.11 are refuted, and the failure was a UNIT
ERROR.** Two independent import-BFS measurements agree name-for-name:
`CascadeStable`'s reverse cone is **20** (+root = 21). **41 (+root = 42) is reproducibly
the reverse cone of `DirectCorrect` and of `RulesWrite`**, and 41 is the *forward* cone of
`CascadeStrataAssemble` — the recorded "42 modules" is a delegated census rooted at the
wrong module, so the wall-clock half of the 3-session estimate rested on a 2×-too-large
number. "~136 sites / 8 files" (`:1190-1195`) was a raw **two-symbol `grep -c` LINE
count** — `UntaintedShadow` 89/8 + `DerNode` 47/4 at `d3c1226` — correct when taken and now
stale at 162/9. The 2026-08-30b census's "13 files" is exactly right for the ~26-name
family; its "24 modules / 125 sites" is unreproducible.

⚠ **The durable rule this earns: a site count is meaningless without its symbol list and
its counting unit.** The record and the censuses never disagreed about the tree — they
disagreed about what a "site" is, for four sessions, with neither publishing its
convention. Size 4c-ii with THREE numbers: **21 modules recompile, ~9 files / ~229 sites
re-check, ~20 sites in 3 files go genuinely red.**

**3. §11.10's trap set, as corrected on 2026-08-30c.** Supersedes the 2026-08-30b list.
* **(a)** the non-emptiness premise is NOT `StoreValidRulesD` (it constrains stored tuples,
  never relation names): thread `hne : ∀ dt R, isDerived S (dt,R) = true → R ≠ ""`, cheap
  via `LeafRules.lean::hne_of_keys_nonempty`. ⚠ Its companion **`hmd` is discharged
  VACUOUSLY** at the only non-vacuity witness — `schemaRewrites SlV = []`
  (`LeafRules.lean:609::lrV_untainted_layer_silent`), so the `exfalso` at
  `LeafRules.lean:466-471` is dead under every fixture. 2026-08-30b's "all four premises
  discharged" is true but weaker than it reads.
* **(b)** `rawWriteRels` is `Leaf.lean:587`, not `:541`. ⚠ **This trap is ITSELF now stale
  (2026-08-31): it is `Leaf.lean:645`.** Step 2 (`50af00e`) inserted the leaf-refutation
  toolkit at `:577-621`, so **every `Leaf.lean` line number above `:552` written before
  2026-08-31 is +58 out** — in this doc, in `PROOF_STATUS`, and in the task file. A trap that
  corrects a line number is a trap with a short half-life: **cite `file::symbol`.**
* **(c)** sizing: settled, see item 2 above. Do not re-cite 42 / ~136 / 24 / 125.
* **(d)** `FoldAdmits`' second exec gate is `Exec.lean:443`, not `:376`.
* **(e)** **`hql` lands on THREE pinned rows, not one.** ✅ **CONFIRMED by consumer-set
  enumeration 2026-08-31c, and its "probably" is now DECIDED — see (l): the `checkPublic`
  migration is the adjudicated repair for `:46`/`:56` (user, 2026-09-01).**
  `docs/latent-gaps.md` excludes
  `headline_statements.txt:46` (`correct_applies`) and `:56` (`::w3d2E_correct_applies`)
  as "staged records over intermediate chains"; that reason is refuted by `FullScope.lean:78`
  (`abbrev ReachedBy := ReachedByW3d2E`) and `:84` (`abbrev Drained`), which make
  `w3d2E_correct_applies` hypothesis-**identical** to `final_applies` — it is that theorem
  with the fence deleted, not an intermediate chain. **Their repair is probably migration
  onto `checkPublic`** (as `final_applies` was on 2026-08-28c), not the `hql` binder.
  Structurally confirmed, not kernel-confirmed. (`latent-gaps.md:152` also cites
  `unfenced_grants` as `:51`; it is `:52`, inside the paragraph doing that arithmetic.)
  ✅ **CONFIRMED INDEPENDENTLY 2026-08-31c, by a second and disjoint method** — consumer-set
  enumeration rather than the `abbrev` argument above. Rows **27 / 46 / 56 carry no
  `checkPublic`** (the nine that do: 28, 30, 31, 32, 34, 36, 53, 59, 64), and rows 46/56
  consume `graph_correct_w3d2_d` / `graph_correct_w3d2E_d` **directly** at
  `FullScope.lean:1112` / `:1285`, not through `graph_correct_public`. Two independent routes
  to the same answer, so treat "three rows" as settled. ⚠ **The tension this item flagged is
  now RESOLVED AGAINST `HANDOFF.md`**: its 2026-08-28c line "the remaining `hql` surface is
  ONE pinned row" is **wrong**, and the banner now says so. 2026-08-28c was right only about
  `final_applies`/`final_applies4`, which do route through `checkPublic` and stay safe.
  Detail: PROOF_STATUS `## Session 2026-08-31c` §1.
* **(f)** adding a hypothesis to `shadow_graphRec_agree` / `checkFn_eq_sem_w3d` /
  `shadow_reach_agree` / `reachedByW3d_shadow` changes **no pin file** — none is in
  `headline_statements.txt` or `headline_definitions.txt`; they carry name pins only. The
  recorded worry about "a new hypothesis on an audited signature" is about the 14 call
  sites, not the gate.
* **(g) NEW — the one tier-1 site with no existing lemma.** `shadow_graphRec_agree`
  discharges its probe target from `isDerived S (dt',r') = false`, which does **not**
  exclude a minted leaf name. ~~It needs the operand relation *declared*, and nothing in
  the model forces `computedRefs` names to be declared — `Core/Schema.lean::WF` records
  only that *declared* names are dot-free. Python enforces it
  (`_validate_ast_references`), so the repair is faithful new modelling.~~ The `wAllNode`
  half (`on ≠ STAR`) and the BARE-subject half (the E3 `leafPublic p ≠ ""` guard) are both
  free.
  * ⚠ **STRUCK 2026-09-01c — "declared" was measured FALSE.**
    `zanzibar_utils_v1.py::_validate_ast_references` enforces a **dot-lock**, not
    declaredness: an undeclared operand is accepted and compiled; only a dotted one
    raises. A declaredness clause would be strictly stronger than Python. The landed
    predicate is `CascadeStable.lean::ComputedRefsNotLeaf` over `Leaf.lean::NotLeafName`,
    which is byte-for-byte the Python check.
  * ⚠ **MECHANISM DISSOLVED 2026-09-01d.** The trap's operative claim — that the premise
    *cannot be phrased locally*, because `ReconcileStars.lean::checkFn_agree_of_graphRec`
    and `_cd` hand their `hag` callback exactly `isDerived S (dt,r') = false` — no longer
    holds. Both `hag`s now also carry `r' ∈ computedRefs e` (the callback always bound it
    and spent it only on `hleafUnt`), and
    `CascadeStable.lean::checkFn_agree_of_graphRec_notLeafNode` converts it to
    `¬ LeafNode` for a caller holding `ComputedRefsNotLeaf S`.
  * **What is still open is NOT (g).** The 14 term-level `shadow_graphRec_agree` sites
    partition **3 + 8 + 3**: 3 arrive via the `hag` callback (served 2026-09-01d, all with
    `hlk` in scope); 8 already hold `hr' : r' ∈ computedRefs e` locally and need only
    `ComputedRefsNotLeaf S` threaded onto their enclosing declaration — ⚠ except
    `CascadeStrataEnum.lean::checkFnR_star_declared` (`:336-345`), which has **no `hlk`
    binder** and needs a lookup premise too, unbudgeted; and 3 —
    `CascadeSettle.lean:1119`, `CascadeStrataResettle.lean:1539` and `:2683` — apply it at
    the arbitrary **query** relation inside the `untainted query` branch, where no
    `computedRefs` membership exists or can. Those need the query-level premise adjudicated
    2026-09-01 for headline row 27, which is not landable before step 9's flip. Track them
    as the residue of (e), not (g). **`11 = 3 + 8`** is where the ten-step plan's "11 call
    sites" came from; it never recorded that the other 3 are a different repair.
  * ⚠ **The way-out citation on record is INCOMPLETE, and half a fix builds.**
    "`ReconcileStars.lean:618/622/633`" is binder / discard / **binder** — it names only ONE
    of the two discard sites. The `_cd` twin's is **`:637`**. A session editing exactly the
    three cited lines would have shipped a widened `checkFn_agree_of_graphRec` and an
    un-widened `_cd`, which compiles. Cite `file::symbol`, per trap (b).
* **(h) NEW — a BLIND INSTRUMENT created by step 1's own session.** `Scratch4cii.lean:51`
  defines a local unguarded `leafNodeB` that **shadows** the guarded carrier step 1 added
  at `Leaf.lean:547`; the local one wins every unqualified use, including `clsB` (`:393`)
  and `termB` (`:409`), so the entire P14 weak battery measures a broader proxy than the
  carrier it validates — in the **unsafe** direction (a broader proxy makes the weak
  disjunct easier, so those rows can be green while the real widened `classify` fails).
  Delete `:51` **first**, before relying on the battery; expect a diagnostic red confined
  to the file (1 importer, 0 audit rows, 0 pin rows).

  ✅ **CLOSED 2026-08-30d, and the prediction in the sentence above was WRONG** — deleting
  `:51` built **green**, `rc=0`, 1089 jobs: no battery row distinguishes the two carriers,
  so the shadowing corrupted nothing and the P14 weak rows are valid as taken. Wrong in
  the safe direction, but a green is not a measurement, so the difference was made
  mechanical instead of argued: `Scratch4cii.lean::leafNodeB_here_is_the_guarded_carrier`
  pins the two predicates apart at `LeafWitness.SwEmptyRel`, and re-adding the proxy makes
  it — and **only** it — go red. That "only" is what licenses the green. Full record and
  the literal sabotage output: PROOF_STATUS `## Session 2026-08-30d` §1–§2.
* **(i) NEW 2026-08-31 — RE-EXPRESSING a pinned definition moves a pin, and (f) does not
  cover it.** (f) says adding a *hypothesis* touches no pin file, which is true and was
  relied on. It does not follow that the definition layer is free: **`NoTtuTarget` IS
  pinned**, at `headline_definitions.txt:62`. Step 3 introduced the generic
  `ReconcileCorrect.lean::TtuTargetsSat S Q`, of which `NoTtuTarget` is exactly the
  `Q := (· ≠ R)` instance — so the tidy-up of rewriting the old def in terms of the new one
  would have reddened the definition pin for a pure refactor. It was left **byte-identical**
  and the generic added beside it. Generalising a definition is the same hazard as renaming
  one: **before generalising any `def`, grep `headline_definitions.txt` for its name.**
* **(j) NEW 2026-08-31 — "the six free `subjNode` sites" is wrong; three of them are not
  free.** `CascadeStable.lean:919`, `CascadeStrataSettle.lean:685` and `:1246` quantify over
  `u ∈ rewriteClosure S t`, and `rewriteStep`'s `.ttu tr` branch **overwrites** the subject
  predicate with the rule target — so the subject predicate is not BARE in general and
  `Leaf.lean::bare_subjNode_not_leafNode` does not apply. Only the three that talk about the
  **raw write subject** (`CascadeStrataSettle.lean:910`, `:957`, `:1228`) are free.
  Refuting `LeafNode` at the other three needs `TtuTargetsSat S NotLeafName` **and**
  `NotLeafName t.subject.predicate`. ✅ The first already exists as of step 4:
  `schemaRewritesL = schemaRewrites ++ leafRewrites` (`LeafRules.lean:106`) makes
  `NoLeafSubjects → TtuTargetsSat S NotLeafName` a `List.mem_append_left` — the obstacle is
  *placement* (`LeafRules` imports only `GraphIndex.Leaf`; `TtuTargetsSat` lives in
  `ReconcileCorrect`), not proof. The **seed-side** half is genuinely unowned: nothing at
  those sites constrains a stored subject predicate's name shape (`NoTtuTarget S R` says
  targets are `≠ R`, not their shape; `WF` constrains *declared keys*, while `tr` is a
  referenced string inside an `Expr`). Full derivation: PROOF_STATUS `## Session 2026-08-31`
  §4, including the correction to the implementer's own "different rule lists" conclusion.
* **(k) NEW 2026-08-31c — A SABOTAGE CAN FAIL TO FIRE BECAUSE THE TARGET IS GUARDED
  *REDUNDANTLY*, and that reads exactly like a passing sabotage.** Landing
  `Leaf.lean::wAllNode_not_leafNode`, the first attempt weakened one of `leafNodeB`'s two
  shape conjuncts and the pin **stayed green** — not because the pin is weak, but because
  `wAllNode` is excluded *twice over*: `k.name != STAR` **and** `k.variant == Variant.plain`
  each refute it alone. A single-conjunct weakening therefore cannot reach the pin, and
  stopping there would have recorded "sabotage ran, pin held" — a green that means nothing.
  Dropping **both** fired it. **Rule: before believing a sabotage that fails to fire, check
  whether your weakening can actually reach the assertion — enumerate the guards, do not
  assume the one you picked is load-bearing.** This is the house failure mode (an assurance
  step that fails by passing) reappearing *inside the sabotage procedure itself*, which is
  why it is written here and not only in a session record.
  Corollary already known but re-confirmed: the resulting error count is a **lower bound**,
  since Lean does not compile dependents of a failed module (the 2026-08-30d trap). Both
  observations: PROOF_STATUS `## Session 2026-08-31c` §2.
* **(l) NEW 2026-08-31c — the Class-B spike is DONE; do not re-scope it. ADJUDICATED
  2026-09-01: the repair is DECIDED and the user call it was waiting on has been made.**
  Answer: **REACHES** `graph_correct`, via
  `graph_correct_w3d2_d` only (sites 1–2 die in superseded `Equiv.lean` milestones), landing
  on the three pinned rows of (e). The repair touches pinned statements on the two
  **non-vacuity instruments** (`W4WitnessDirect.correct_applies` / `::w3d2E_correct_applies`),
  where an `hql` binder risks a hypothesis nothing satisfies — the failure shape
  `FullScope.lean::graph_correct_public`'s own docstring warns about.
  **DECISION (user, 2026-09-01): rows 46/56 MIGRATE onto `checkPublic`; the `hql` binder is
  REFUSED there. Row 27 keeps the binder accepted on 2026-08-28 — that call is untouched.**
  Four conditions bind the repair session (own commit before step 7; sabotage the
  migrated witnesses' NON-fence branch; re-verify the two `2026-08-31c` UNVERIFIED
  paragraphs; doc sweep + `lean` re-run in the same commit) — full grounds and the one
  known unknown (`reachedByW3d2C_schema` may not exist): `PROOF_STATUS.md`
  `## Session 2026-09-01`. **`P3`'s standing instruction that this must
  not be smuggled into step 7 is unchanged and now has a measured cost behind it** — and is
  now discharged by condition 1 rather than by deferral.
* **(m) NEW 2026-09-01b — (e), (l) and the "three rows" framing are now SPENT: the repair
  LANDED, and the `hql` surface is ONE row again.** Rows 46/56 are stated over
  `GraphModel.checkPublic` as of this date, neither took the `hql` binder, and row 27 is
  untouched — so (e)'s "lands on THREE pinned rows, not one" was true when written and is
  now history rather than a live constraint. Read (e) and (l) as the record of how the
  decision was reached, not as open scope. Corrections to the facts they assert:
  * **(e)'s enumeration is stale in one clause.** "Rows **27 / 46 / 56 carry no
    `checkPublic`**" is now false for 46 and 56. The companion list — "the nine that do:
    28, 30, 31, 32, 34, 36, 53, 59, 64" — still resolves correctly, because the three new
    pins were deliberately APPENDED to `statement_pin.py`'s list (golden rows 65-67)
    rather than filed thematically. Filing them next to the `fence_*` pins had shifted
    `w3d2E_correct_applies` 56→59 and this enumeration 59→62, 64→67; that was caught and
    reverted. `statement_pin.py`'s list order IS the golden's line order — file new pins
    at the tail.
  * **(l)'s "one known unknown" is REFUTED.** There is no `reachedByW3d2C_schema`, none
    is needed, and the grep that failed to find one was looking for the wrong name: row
    46's bridge composes as `reachedByW3d2_schema (reachedByW3d2C_toW3d2 h)`. This is now
    kernel-checked, not a source read.
  * **(k)'s redundant-guard trap was applied, not just cited.** The condition-2 sabotage
    on `public_grant_survives_fence` holds the grant fixed (`unfenced_grants` machine-
    checks the unfenced read still grants at `σLeaf`) so the observed flip is attributable
    to leaf-ness alone and not to a missing edge.
  * All four binding conditions are discharged. Full record, including both sabotages'
    literal output: `PROOF_STATUS.md` `## Session 2026-09-01b`. What remains of this item
    is row 27 / step 7, unchanged.

* **(n) NEW 2026-09-01e — the flip's cost is MEASURED END TO END, and (k) has a second,
  sharper exemplar: for a PRE-WIDEN, the flip PROBE is the control and no weakening can be.**
  Step 8's free half landed by PRE-WIDEN in place rather than GENERALISE
  (`CascadeStable.lean::untaintedShadow_applyD`,
  `CascadeStrataSettle.lean::untaintedShadow_applyLoggedR{,_d}`), using step 5's
  `first | <post-flip form> | <today's form>` idiom. Three durable facts fall out.
  * **The "~20 sites in 3 files go genuinely red" scout figure (2026-08-30c) is RETIRED.**
    Measured: **5 repair sites, 4 declarations, 2 files.** With the abbrev flipped and only
    the four unowned obligations `sorry`-stubbed, the **entire tree builds green (1089
    jobs)** — `CascadeSettle`, `CascadeStrataResettle`, `CascadeEnum`, `CascadeStrataEnum`,
    `Equiv`, `Audit`, `Scratch4cii` and every headline theorem included. ⚠ This sizes the
    flip's STRUCTURE. It does not license landing it: `sorry` supplies precisely the
    false-as-written content, so the green is the claim *"only those four obligations stand
    between today's tree and the flip"*, not *"the flip is sound"*.
  * **How to close a probe's lower bound, and it is reusable.** Lean does not build
    dependents of a failed module, which is why 2026-09-01d's "6 errors in 3 declarations"
    saw only one third of the flip. Stub each *already-known-blocked* obligation with
    `sorry` — a warning, not an error — and `lake` proceeds past the red module and reveals
    the next wave. Wave 2 was **8 errors in 4 declarations, all in
    `CascadeStrataSettle.lean`**; full first-plus-second wave, **14 errors in 7
    declarations**. Never report a probe's error count without saying which modules it
    could not reach.
  * **(k) generalised: an alternative that only elaborates after a re-point cannot be
    sabotaged before it.** The post-flip branch of a `first | … | …` is dead code today, so
    S1 (`hoffW` narrowed to its `DerNode` half at all three sites) is **GREEN unflipped —
    `Build completed successfully (1089 jobs). rc=0`** — and **RED under the flip**, one
    attributable error at `CascadeStable.lean:1248` (itself a lower bound; the build stops
    there). Run BOTH halves and record BOTH; a PRE-WIDEN whose only evidence is a
    today-tree green has no evidence at all.
  * **What is left is not step 8.** Step 9 was **blocked on a design decision, not proof
    effort**: the seed-side `NotLeafName t.subject.predicate` at
    `::reachedByW3d_shadow` / `::reachedByW3d2_shadow{,_d}` wants a premise threaded
    through three signatures — changing their premises, hence downstream statements, hence
    potentially the headline theorems. **That call was MADE 2026-09-02 (user): thread it
    AND discharge it from `GraphAdmission`.** See **(o)** and **(p)**. Full records:
    `PROOF_STATUS.md` `## Session 2026-09-01e` and `## Session 2026-09-02`.

* **(o) NEW 2026-09-02 — the seed-side premise must be `NotLeafName`-shaped, and a
  `relNameOK`-shaped one would RE-VACUATE the headline theorems.** This is the sharpest
  trap on the item, because the wrong clause is the one that reads more naturally.
  `NotLeafName p := p = BARE ∨ isLeafPred p = false` — *"the bare sentinel, OR dot-free"*.
  It is **not** `relNameOK p := ¬ p.contains '.'`. The reason is that `BARE = "..."` is
  **itself dot-carrying** (`Core/Ident.lean:20`; `isLeafPred` is a bare dot test,
  `Leaf.lean:196`, and `Leaf.lean::isLeafPred_bare` records that divergence on purpose),
  while **every `Direct` restriction in every `GraphAdmission` witness schema is
  `("user", BARE, _)`** (`FullScope.lean:615`/`:725`/`:888`). So a dot-free clause is FALSE
  at `Sx`/`Sy`/`Sd`, makes the bundle uninhabited at its four construction sites, and turns
  the final theorems VACUOUS — the exact 2026-08-05 failure mode this whole leg exists to
  retire, arriving through a new door. The `NotLeafName` shape also mirrors Python, whose
  `_validate_ast_references` dot-lock carries its own `and name != '...'` escape.
  ⚠ It follows that `relNameOK` is the wrong tool anywhere a SUBJECT predicate is in
  question; it is right only for object-side relation names. Step 7 hit the same wall from
  the other side and landed `ComputedRefsNotLeaf` over `NotLeafName` for the same reason.

* **(p) NEW 2026-09-02 — thread the SCHEMA fact, not the store fact; and the seed's
  admission is ALREADY in scope.** The board and `2026-09-01e` both describe step 9 as
  threading a store-level `NoLeafStoreSubjects T`. Cheaper and more natural, established by
  building the discharge (`PROOF_STATUS` `2026-09-02` §3/§5): thread the schema-level
  `CascadeStable.lean::DirectRestrictionsNotLeaf S` instead, because (i) `hSV` is already a
  hypothesis at all three sites and each `write` case's store is `t :: T`, so
  `hSV t List.mem_cons_self` IS the seed tuple's own admission fact; (ii) a schema premise
  needs no `List.mem_cons_of_mem` weakening line per recursive call, a store premise needs
  one at every one; (iii) **7 of `GraphAdmission`'s 8 fields are already schema-level** —
  only `storeValid` is not. `NoLeafStoreSubjects` stays as the named CONCLUSION of the
  discharge lemmas, not as the threaded hypothesis.
  ⚠ **Quantify over `exprDirectsAll`, never `exprDirects`** — the latter returns `[]` under
  `inter`/`excl`, so it would leave `StoreValidRulesD`'s DERIVED disjunct (the one admitting
  `can_view: [user] but not blocked`) completely unguarded. Pinned discriminatingly by
  `::directRestrictionsNotLeaf_false_sdrBadDerived` against
  `::sdrBadDerived_clean_under_exprDirects`.
  ⚠ **Both admission forms are needed**: `reachedByW3d_shadow`/`reachedByW3d2_shadow` carry
  the narrow `StoreValidRules`, `reachedByW3d2_shadow_d` carries `StoreValidRulesD`.

* **(q) NEW 2026-09-02 — a grep census OVER-counts this cone, and the direction of the error
  is the surprise.** Every previous sizing here came in LOW (`P3`'s "~123 sites" was live
  ~136), which trained the habit of padding a grep figure upward. Threading
  `reachedByW3d_shadow` measured the opposite: the grep said **46 non-comment lines across 9
  files**, the probe said **18 declarations across 6 files**, and `CascadeStrata*` — 2 of the
  9 files — **does not move at all**, because its matches are docstring references that a
  `^\s*(--|\*|/--)` comment filter does not catch (Lean docstrings are `/-- … -/` blocks whose
  CONTINUATION lines start with ordinary prose). Two rules follow, and they are cheap:
  **(i)** `Audit.lean`'s `#print axioms` rows and `audited_theorems.txt` name rows are NOT
  repair sites — a signature change does not break them — so exclude them before quoting any
  figure; **(ii)** a declaration-level count via `awk` "nearest preceding `theorem`" is
  unreliable and was **discarded** this session for reporting more declarations than there
  were matching lines. **Size this cone with the probe** — add the premise, build, read the
  errors, repeat — which is `2026-09-01e` §2's method and costs a handful of incremental
  builds because Lean stops at the first failing module.

* **(s) NEW 2026-09-02 — STEP 9 IS DONE, and the flip is down to ONE obligation.** All
  three `hsubj` sites are threaded and both premises are `GraphAdmission` fields
  (`ttuNotLeaf`, `directRestrNotLeaf`), discharged `by decide` at all four construction
  sites. Re-running the flip probe on the finished tree: the only reds are the **eight
  `Or.inl` wrappers** the pre-widens were built to leave — six at the `hsubj` sites, two at
  `hv3` — plus `shadow_graphRec_agree`'s **`hv1`**; with the wrappers swapped and `hv1`
  ALONE stubbed the whole tree builds (**1089 jobs, rc=0**, one `sorry` warning at
  `CascadeStable.lean:1640`). **`2026-09-01e`'s "four unowned obligations" is retired.**
  `hv1` needs row 27's query-level premise (the operand-side `NotLeafName r'` at the query
  relation) and is the whole of what remains before 4c-ii.
  ⚠ **The pin cost is now a measured fact rather than a prediction**: `headline_statements
  .txt` byte-identical (49/49); `headline_definitions.txt` regenerated DELIBERATELY 161 →
  164 — the `GraphAdmission` row plus **three newly-reachable definitions** (`NotLeafName`,
  `DirectRestrictionsNotLeaf`, `TtuTargetsSat`). That third part is the one to expect and
  not to panic at: the definition pin fires when *the meaning of a claim grows a new
  dependency*, which is exactly what happened, and `FINAL_REVIEW.md`'s counts block must be
  regenerated in the same breath (`doc_counts --generate`).
  ⚠ **Do NOT extend `W4WitnessDirect`'s flat conjunction** (`headline_statements.txt:43`)
  to carry the new fields: four sites destructure it positionally, and it is a pinned
  headline row. Supply the two facts inline at those sites instead.

* **(r) NEW 2026-09-02 — the six W3d-layer endpoints are AUDITED BUT NOT STATEMENT-PINNED,
  so adding a hypothesis to them is invisible to the gate.** `graph_correct_w3d`,
  `backend_equivalence_w3d`, `exclusion_effective_w3d`, `no_ghost_grant_w3d`,
  `reachedByW3dC_inv`, `reachedByW3dE_inv` each carry an `audited_theorems.txt` row and an
  `Audit.lean` `#print axioms`, and each is a TERMINAL claim consumed by nothing else in the
  tree — yet **none has a `headline_statements.txt` row**, and audit rows pin NAMES only. So
  the ten-phase gate reports green across a genuine weakening of all six. This is the house
  failure mode in its exact form. **Anyone adding a premise anywhere in this cone must state
  that fact in the session record and name the discharge that retires it** — the gate will
  not do it for you. (Landed once, deliberately, on 2026-09-02; PROOF_STATUS `2026-09-02`
  §7 carries the standing caveat until the `GraphAdmission` discharge lands.)
  ⚠ **AMENDED 2026-09-02b: "six" is an UNDERCOUNT — two independent measurements put the
  audited-but-unpinned carriers at 38**, this list omitting the whole `_w3d2` family. Both
  measurements are UNVERIFIED first-hand; re-measure before quoting either number.

* **(t) NEW 2026-09-02b — the `hv1` cone is a CLOSED LIST of 14 sites / 12 declarations /
  6 files, measured by probe.** Staging `sorry` at every site (trap (n)'s technique) makes
  the whole tree build — `rc=0`, 1089 jobs, zero errors, 14 `sorry` tokens, 12 `declaration
  uses sorry` warnings — so nothing outside the census exists; this is a closed list, not a
  lower bound. Declarations: `CascadeEnum:347`; `CascadeSettle:899`; `CascadeStable:1707`;
  `CascadeStrataEnum:336/:373/:413`; `CascadeStrataSettle:1642/:1711/:1857/:4005`;
  `CascadeStrataResettle:1440/:2551`. **14 sites but 12 declarations**, because
  `graph_correct_w3d2` (`:1440`) and `graph_correct_w3d2_d` (`:2551`) each host TWO — one
  membership-servable, one query-relation. ⚠ **Those two are where a partial landing gets
  left half-done**: they are why "thread the predicate" and "add the query premise" are NOT
  separable at declaration granularity. Servability, measured per site: **7 of 8** carry
  `hlk` already; only `CascadeStrataEnum::checkFnR_star_declared` (`:336`) lacks it (and
  lacks `hder`, so the `isDerived_declared` escape is unavailable) — but its single caller
  `::w3d2_leg_context` (`:463`, applying at `:486`) already holds `hlk` at `:473` for the
  same `(dt, R)` and `e`, so the fix is one binder and one argument, not a new obligation.
  Retires the board's "18 declarations across 6 files" for this step.

* **(u) NEW 2026-09-02b — ⚠ a `sorry`-counting grep SILENTLY RETURNS ZERO, because Lean
  uses BACKTICKS.** Lean writes ``declaration uses `sorry` ``. `grep -c "declaration uses
  'sorry'"` (straight quotes) matches **nothing** and reports `0`. Observed on run 2 of the
  (t) probe: 14 staged `sorry` tokens and `rc=0` read back as "0 sorries", which taken at
  face value says the added premise was never needed — a green verdict produced entirely by
  a broken instrument, inside the tool being used to measure a cone whose whole hazard is
  green-that-means-nothing. Use `grep -c "declaration uses .sorry."`, and more generally:
  **a grep used as an assurance instrument must be made to fire once on purpose before its
  zero is believed** — the same rule this repo already applies to tests, floors and pins.
  Companion to (q), which is the over-counting half of the same lesson.

## Provenance

Decision: user, 2026-08-05 ("scope it as c and document that in handoff but we will defer
it for now"). Scoping: two read-only exploration passes over `formal/lean/` and
`formal/conformance/` + `zanzibar_utils_v1.py`/`index_v4/`, same session. **No Lean
declaration, proof, golden, or gate file was modified.** The `(a)`/`(b)`/`(c)` framing
originates in leg-0 probe D.3 — `history/echain-widening-plan-2026-07-28.md` §D.3 and
`W4NarrowT2a`'s docstring in `lean/ZanzibarProofs/FullScope.lean`.
