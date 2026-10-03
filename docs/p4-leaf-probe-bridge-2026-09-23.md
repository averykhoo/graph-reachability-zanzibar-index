# `P4` — leg 7 step 4b, the leaf-probe ↔ `directLeaf` bridge: the measured map

**FROZEN 2026-10-03d, at `P4`'s close — provenance, not a living document.** Status lines
below are as-of-then and several may now be false; live state: `HANDOFF.md` + the session
ledger. Corrections are appended dated at the top, never edited into the body. (Opened
2026-09-23 as the ACTIVE-PLAN execution map for `P4`, goal step 2,
`docs/goal-census-2026-09-22.md`.)

Provenance labels on every claim: **READ** (verified first-hand this session with
`file::symbol` / `file:line`), **REASONED** (inferred from READ facts), **AGENT** (a
subagent's report, reconciled but not re-derived), **UNVERIFIED**.

## Correction 2026-10-03d — the general theorem LANDED; "§ What `P4` still owes" is discharged

All READ first-hand this session (Lean `rc=0` on the file, then the gate). No agent was used.

* **Owed item 1, the general theorem:** `formal/lean/ZanzibarProofs/GraphIndex/LeafBridge.lean::leaf_probe_bridge`.
  It took the "cheap" route below: phrased off the probe and `directLeaf`, never through
  `evalE`, so `computedRefsNotLeaf` is not in the way. Premises are the two headline
  bundles, `ReachedBy`, a derived `(o.type, R)`, `(i, rs) ∈ storageLeaves`, and
  `o.name ≠ STAR`. The conclusion holds for every subject, `rec` and `q`, with no
  `Drained`. That is stronger than the sketch below, which fixed `rec := graphRec σ s`.
* **The payload was smaller than "~one file" predicted**, because the declaredness half
  the sketch expected to restate was not needed. R3
  (`RemoveOccCount.lean::reachedByW3d2E_untOccCount`) already pins the edge count at
  leaf targets. What was missing was the content of that count at a STORAGE leaf, and the
  only non-trivial step there is `LeafBridge.lean::LeafBridge.no_rule_targets_storageLeaf`:
  leaf rules (`LeafRules.lean::keyLeafRewrites`) target `.closure` indices only, and an
  index holds one leaf. That needs `leafPred` injectivity, which needs `toString`
  injectivity on `Nat` (`LeafBridge.leafPred_inj`). The path collapse is P14's
  `CascadeStrataSettle.lean::reachedByW3d2_bareNode_no_inedge_d`.
* **Owed item 2, the `.userset` kind:** it does not exist in-fragment,
  `LeafBridge.lean::no_userset_leaf_in_fragment` (`directArmsBare` forbids the tainted
  userset restriction that allocates one). The theorem is silent there by SCOPE. A
  `.userset` bridge needs a fragment admitting userset arms on derived defs. No row is
  filed for it: `CORRESPONDENCE.md` §7.3 already lists `PDerivedUserset` as netted only.
* **Sabotage and pins:** `formal/history/PROOF_STATUS.md`, session 2026-10-03d (literal
  outputs). The plausible mis-statement, probing the PUBLIC name, reddened only inside
  the proof, so the statement is byte-pinned in `formal/headline_statements.txt`, and
  `LeafBridgeWitness.leafBridge_corpus` refutes that form at a reached state (bob: leaf
  probe `true`, public probe `false`, `directLeaf` `true`).

---

## § The headline: 4b's stated premise is FALSE in the model today

`P4`'s obligation comes from the scope doc
[`formal/history/leaf-family-split-scope-2026-08-05.md`](../formal/history/leaf-family-split-scope-2026-08-05.md)
§8.1, written 2026-08-05, which states it as:

> `probeNonDerived σ ⟨s, "R.i", ⟨dt,on⟩⟩ = directLeaf rec s T q rs dt on R`,
> given that writes matching `rs` were routed to `objNode ⟨dt,on⟩ "R.i"`.

and motivates it with *"Once `checkFn` reads a leaf **node** instead of the store, the two
sides stop being the same expression and a new bridge is owed."*

**That conditional never fired inside the Lean model, and by admission it cannot.** READ
2026-09-23:

* `GraphIndex/ReconcileWrite.lean::GraphState.checkFn` (`:72`) and
  `GraphIndex/CascadeStrata.lean::GraphState.checkFnR` (`:113`) both evaluate
  `evalE … e` where `e` is the **raw def** fetched from `S.lookup` — not a compiled plan.
  READ.
* `Spec/Semantics.lean::evalE` (`:114`) sends `.direct rs` to
  `Spec/Semantics.lean::directLeaf` (`:65`), which reads the **store** through
  `::grantsOf` (`:45`) filtered on the **public** relation `rel`. It never touches a node.
  READ.
* The only way a `checkFn` evaluation could reach a leaf node is an `Expr` containing
  `.computed "R.i"` — and `GraphAdmission`'s field `ComputedRefsNotLeaf` **refuses exactly
  that**. The pin pair is `FullScope.lean::SxLeafRef` (`:968`) /
  `::sxLeafRef_computedRefsNotLeaf_false` (`:977`), with
  `::sxLeafRef_other_admission_fields_hold` (`:985`) proving the field is independent, not
  implied. READ.

So in the Lean model the two sides **never stopped being the same expression**: the write
leg moved onto the leaf family (leg 7's flip, landed 2026-09-05), the read leg did not.

## § …but the obligation is real — it just belongs to the Lean↔Python map, not to the fragment

Python's compiled `check_fn` **does** read leaf nodes. READ 2026-09-23:

* `zanzibar_utils_v1.py::_compile_check_fn` (`:1940`) compiles a `PClosureLeaf` to
  `lambda ctx, s: ctx.leaf_check(pred, s)` (`:1943`), where `pred` is the minted
  `<relation>.<index>` name.
* `index_v4/processor.py::_EvalContext.leaf_check` (`:146`) is
  `self.proc.widx._check_internal(sp, st, sn, leaf_pred, …)` — a probe of the **index at
  the leaf name**, below the public leaf-name fence (`BL-2`).

`formal/CORRESPONDENCE.md` §7.3 already records this as an **unmodelled** region, in these
words (READ, `formal/CORRESPONDENCE.md:1150-1159`):

> *"Lean's reconcile evaluates an `Expr` directly via `checkFnR`/`coveredFnR`; Python
> evaluates a **compiled closure tree over split leaf families**. The correspondence is
> 'same boolean semantics', pinned by the differential matrix and the snapshot gate … **not
> by any theorem about the compiler**."*

**That is `P4`'s real consumer**, and it is squarely the chosen goal ("make the assurance
surface honest and legible"): the bridge converts one clause of a §7.3 "netted by the
differential matrix" entry into a machine-checked statement.

## § The write leg the bridge would stand on (READ 2026-09-23)

* `GraphIndex/Leaf.lean::rawWriteRels` (`:707`) — a raw write of `t` on a **derived** key
  materializes under the minted leaf names of the storage-bearing leaves whose restrictions
  admit `t` (`.storage rs` → `restrictionMatches rs t`; `.userset r` → `restrictionMatches
  [r] t`; `.closure _` takes no raw write). On an untainted key it is `[t.relation]`
  (`::rawWriteRels_untainted`, `:723`).
* `GraphIndex/Leaf.lean::rawWriteTuples` (`:793`) re-addresses the tuple;
  `::GraphState.writeDirectRaw` (`:806`) folds today's `writeDirect` over the expansion.
* `GraphIndex/Leaf.lean::persistedLeaves` (`:427`) is the allocation; a leaf's family index
  **is** its position. `PLeaf` is `.storage (List Restriction) | .userset Restriction |
  .closure Expr` (READ, `::atomLeaves` `:406`, `::pureLeaves` `:398`).
* `GraphIndex/LeafRules.lean::leafRewrites` (`:122`) / `::schemaRewritesL` (`:130`) add the
  rule-fed closure copies **into** leaf nodes; `::rewriteClosureL` (`:229`) is the closure
  the two logged legs fold (`GraphIndex/Cascade.lean::GraphState.writeLoggedRules`,
  `::removeLoggedRules`).

⚠ **The bridge is NOT 1:1 with `evalE`'s `.direct` arms.** `pureLeaves` **merges** every
pure `Direct` arm of a maximal pure subtree into ONE `.storage` leaf, so the leaf's
restriction list is the merged one, not any single arm's `rs`. Any statement of the bridge
must quantify over `persistedLeaves`' entries, not over the def's `Direct` occurrences.
REASONED from `::pureLeaves` (`:399`) and `::atomLeaves` (`:406`), both READ.

## § `P5` and `P14` DO NOT depend on `P4` — measured, and this unblocks the goal's milestone

Both rows carry `deps: [P4]`, and `P5`'s own `2026-09-05b` log already asked for this check
(*"re-check whether 4b is really prerequisite"*). It is not. READ 2026-09-23:

* `GraphIndex/State.lean::Inv` (`:717-730`) is a statement about `σ.nodes` / `σ.edges` /
  `σ.residue` and `NReaches` **only**. `negEdgeFree` (`:724-725`) reads *"for every residue
  row, no `neg` member's subject node reaches the row's key node"*. No store, no `evalE`, no
  `directLeaf`, no probe. ⚠ The scope doc and `P5`'s row cite `State.lean:706` for it —
  **stale by 11 lines** as of today.
* `probeNonDerived` and `directLeaf` — the two sides of the 4b bridge — occur **zero times**
  in `GraphIndex/CascadeStrataEdge.lean` and `GraphIndex/CascadeStrataInv.lean`, the two
  files that own `EdgeHyg1` and the lemma that produces `negEdgeFree`. First-hand `grep -c`,
  both `0`.
* `graph_reached_inv` (`FullScope.lean:793-799`) has **zero proof consumers**: every other
  occurrence of the name in the tree is prose or `Audit.lean`'s `#print axioms`. Grepped
  whole-tree 2026-09-23. So retiring `W4NarrowT2a` from it breaks nothing — and, the other
  way round, **weakening it cannot go red**; the only enforcement is the byte-pinned
  statement (`formal/headline_statements.txt`) plus the audit identity pin.

**Verdict, taken not deferred (`CLAUDE.md` § "Who decides"): the `deps: [P4]` edge on `P5`
and on `P14` is removed.** The chain the goal names — `P4` → `P5` + `P14` — was a *plan*
ordering from the scope doc's §7, not a proof dependency, and the landed architecture
(refusal rather than bridge, see above) severed it. Goal step 2 is startable today.

**Where the residual cost of retiring `W4NarrowT2a` actually sits** (AGENT, reconciled
first-hand for the three load-bearing facts): `hN.computedOnly` threads
`CascadeStrataEdge.lean::edgeHyg1_runCascade2` (`:178`) → `::edgeHyg1_reconcileJobsLR`
(`:140`) → `::edgeHyg1_applyLoggedR` (`:86`), which at `:115` feeds
`GraphIndex/CascadeStrataInv.lean::reconcileStarsKeyDR_row_edge_consistent` (`:418`) — whose
`hco : ComputedOnly e` binder is at `:422`, and which has **exactly one call site**
(verified: `:115`, plus its audit line `Audit.lean:1247`). That single lemma plus the
three-lemma `edgeHyg1_*` re-point is the work. The `_d` twins of the surrounding facts are
already in the tree and unused by T2a (`CascadeStrataSettle.lean::writeLeg_inedges_eq_of_unmapped`
`:4342`, `::removeLeg_inedges_eq_of_unmapped` `:4374` — neither takes `ComputedOnly` or
`StoreValidRules`). **`grep -rn "edgeHyg1.*_d\b"` returns nothing: no `_d` twin exists.**

⚠ **One gap nobody had flagged, and it matters to `P5`** (AGENT, UNVERIFIED by me): the
"obstacle is gone" measurement (`formal/probes/d3_negedgefree_postflip_2026-09-05.lean`)
runs at `LeafWitness.Sw` — union arm, wildcard on `viewer` — while the refutation that keeps
the bundle biting (`W4WitnessDirect.outside_narrow_t2a`) is at `Sd`/`Td`, which has neither.
**The probe has never been run at `Sd`/`Td`.** That is `P5`'s first action, not its last.

## § What LANDED this session

1. **Six `by decide` witness pins** in `GraphIndex/Exec.lean` (`P4Bridge` namespace) —
   `bridge_holds_Sw` / `_SwU` / `_SwF`, and the two discriminating controls
   `bridge_needs_the_leaf_name_Sw` / `_SwU` and `bridge_is_per_leaf_SwF`. Each pins a
   `BridgeTally` whose third field, `bothTrue`, is the row count where **both** sides
   answered `true`, so agreement-by-universal-denial cannot pass. Audited (`Audit.lean`,
   standard axioms only); the identity pin went `617` → `623`.
2. **The tracked probe** `formal/probes/p4_leaf_probe_bridge_2026-09-23.lean` (rc=0,
   2026-09-23), the attack-first run house rule 2 requires. **NO-KILL**: 0 disagreements at
   all three allocations over a store-derived subject grid.
3. **`CORRESPONDENCE.md` §7.3** — the compiled-`check_fn` entry no longer says the whole
   layer rests on the differential matrix; the `PClosureLeaf` clause now names the pins, and
   says in the same breath that the other four plan-leaf kinds are still netted only.

### The measured tallies (PROBE, rc=0, 2026-09-23)

| shape | storage leaves | pairing | rows | agree | bothTrue |
|---|---|---|---|---|---|
| `LeafWitness.Sw` | index `0` | leaf name | 5 | 5 | 2 |
| `LeafWitness.Sw` | index `0` | **public name (control)** | 5 | **3** | **0** |
| `LeafWitness.SwU` | index `2` | leaf name | 5 | 5 | 2 |
| `LeafWitness.SwU` | index `2` | **public name (control)** | 5 | **3** | **0** |
| `LeafWitness.SwF` | indices `0`,`1` | leaf name | 10 | 10 | 3 |
| `LeafWitness.SwF` | indices `0`,`1` | **cross-paired (control)** | 10 | **8** | 2 |

### The sabotage record — the attribution control passed, both write-leg mutations were caught UPSTREAM

Per [`docs/sabotage-procedure.md`](sabotage-procedure.md). Literal outcomes, 2026-09-23:

* **M0 (instrument control)** — flip `bridge_holds_Sw`'s own `rows` from `5` to `4`.
  **RED at exactly one declaration**, `Exec.lean:1445`, the theorem's own `by decide`, with
  `Tactic 'decide' proved that the proposition ... is false`. So the sweep can tell a clean
  module from a broken harness (`P6` step 0's lesson).
* **M1** — un-flip the logged write leg (`writeLoggedRules` seeded with `[t]` instead of
  `rawWriteTuples S t`). **Never reached this file.** `Cascade.lean:757` fails first, on the
  logged/unlogged `EvalEq` coupling to `writeRulesRaw`; neutralising the two mechanical sites
  did not help, because `:757` couples to `LeafRules.lean` which still routes.
* **M2** — hardcode the leaf index at `0` inside `Leaf.lean::rawWriteRels`. **Also never
  reached this file**: six declarations inside `Leaf.lean` fail first (`:743`, `:746`,
  `:1034`, `:1067`, `:1074`, `:1216`), three of them *after* their own pins were re-stated to
  match the mutation.

⚠ **The honest reading of M1/M2 is a scope statement, not a weakness**: the leaf-routed
**write** leg is so densely pinned inside `Leaf.lean` and `Cascade.lean` that no mutation of
it survives to be evaluated here. These six pins are therefore evidence about the **read**
side — which is exactly the side `CORRESPONDENCE.md` §7.3 says is unmodelled. The two
in-statement controls, not M1/M2, are what certifies them, and they are permanent tests
rather than a recorded run (the top of the procedure's durability ranking).

## § What `P4` still owes — the general theorem

The witness pins are not the statement. The statement is, roughly:

>     probeNonDerived σ ⟨s, leafPred R i, o⟩ = directLeaf rec s T q rs o.type o.name R
>     for every `(i, rs) ∈ storageLeaves S o.type R`, on a state reached by the
>     leaf-routed write leg from `T`.

and it is blocked on **two** things, in this order:

1. ⚠ **It cannot be stated inside the admitted fragment.** `GraphAdmission`'s
   `computedRefsNotLeaf` refuses every schema whose `computedRefs` mention a leaf name, and
   `FullScope.lean::sxLeafRef_other_admission_fields_hold` (`:985`) proves no other field
   would notice the difference. So stating the bridge needs either a second bundle that
   permits leaf names, or a statement phrased off the probe directly and never routed through
   `evalE` — **and the second is the cheap one**, because the bridge's own content does not
   need `rec` at all (see 2).
2. The payload is a `StoreValid`-analogue at a **synthetic, undeclared** key. Under
   `DirectArmsBare` + `DirectArmsConcrete` the right-hand side is `rec`-free, query-free and
   wildcard-free (`ReconcileCorrect.lean::memberOfGranted_of_bareGrants` `:214-220` kills the
   userset flow-through), so what is left is *"an edge `subjNode s → objNode o (leafPred R i)`
   exists iff `s` matches leaf `i`'s merged restrictions in `T`"*. The schema-free half of the
   machinery transplants free (`DirectCorrect.lean::grantsOf_elim` `:286` / `::grantsOf_intro`
   `:297`); what must be restated over leaf names is the declaredness-carrying half — `WF`,
   `StoreValid`, `StoreValidRules{,D}` are all statements about `S.defs`, which a leaf name is
   provably not in (`Leaf.lean::leafPred_ne_relName` `:235`). AGENT-sized at ~one file; the
   scope doc's own 2026-08-05 estimate agrees and has not rotted.

**Also still owed, and cheap:** the `.userset` leaf kind. `rawWriteRels` routes it
(`Leaf.lean:707`, the `.userset r` branch) and no pin above touches it — every witness here
allocates `.storage` leaves only.
