# Leg 7 — the leaf-family split (retire projection P6). SCOPE, DEFERRED.

**Status: the design decision is MADE — option (c). The work is DEFERRED, not scheduled.**
Decided by the user 2026-08-05. This file is the scoping pass so the leg is resumable
without re-deriving the blast radius; **no Lean declaration was changed to produce it.**

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
3. **Additive leaf addressing:** `isLeafPred`, the leaf-name assignment function, and the
   distinctness lemma off `relNameOK` (§3). No behavior change; nothing rebased.
4. **Fork `writeDirect`** (§4) driving the target off the existing `Delta.leaf` tag.
   Behaviorally identical on `ComputedOnly` by construction — prove that as the leg's
   subsumption lemma, mirroring `w4Fragment_of_computedOnly`.
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

## Provenance

Decision: user, 2026-08-05 ("scope it as c and document that in handoff but we will defer
it for now"). Scoping: two read-only exploration passes over `formal/lean/` and
`formal/conformance/` + `zanzibar_utils_v1.py`/`index_v4/`, same session. **No Lean
declaration, proof, golden, or gate file was modified.** The `(a)`/`(b)`/`(c)` framing
originates in leg-0 probe D.3 — `history/echain-widening-plan-2026-07-28.md` §D.3 and
`W4NarrowT2a`'s docstring in `lean/ZanzibarProofs/FullScope.lean`.
