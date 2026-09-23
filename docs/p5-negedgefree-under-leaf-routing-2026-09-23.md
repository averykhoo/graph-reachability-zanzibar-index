# `P5` — `Inv.negEdgeFree` under leaf routing; retiring `W4NarrowT2a`: the measured map

**FROZEN at `P5`'s close, 2026-09-23b.** Execution map for `P5`, goal step 2
(`docs/goal-census-2026-09-22.md`). Every figure in the body was measured on `2026-09-23`
against the tree that became the `P5` commit; the body is provenance, not a living status.
Live state is `python scripts/task.py show P5` and `python scripts/gate_status.py` — never
this file. Corrections append **dated at the top**, never edited into the body.

Provenance labels on every claim: **READ** (verified first-hand this session with
`file::symbol`), **REASONED** (inferred from READ facts), **MEASURED** (a probe run this
session, literal output quoted), **UNVERIFIED**.

---

## § 1 Step 0 — the Sd/Td probe the row demanded FIRST (MEASURED)

The row's 2026-09-23 trap: *"the obstacle-is-gone probe runs at `LeafWitness.Sw` while
`outside_narrow_t2a` refutes at `Sd`/`Td` — the two halves have never been measured at the
same store."* Probe: [`formal/probes/p5_negedgefree_sd_td_2026-09-23.lean`](../formal/probes/p5_negedgefree_sd_td_2026-09-23.lean),
run `cd formal/lean && lake env lean ../probes/p5_negedgefree_sd_td_2026-09-23.lean`,
**rc=0**, against the built oleans of HEAD `a295a2c`. Store = the four-tuple conformance
store `Td4` (prefix: alice-approver, bob-banned, carol-banned; probe write: bob-approver,
so the write lands on a key that also carries a ban). Literal output:

    ("Sd: DOMAIN SIZE", 64)
    ("Sd: declaredWildcardShapes", [])
    ("Sd: rawWriteRels tbA", ["approver.0"])
    ("Sd: PROBE (A subject, B bare-preflip, C drained, D bridge)",
     some ({ edges := 9, rows := 1, starsRows := 0, negTested := 0, negFree := true, uposTested := 0, uposFree := true },
      { edges := 9, rows := 1, starsRows := 0, negTested := 0, negFree := true, uposTested := 0, uposFree := true },
      { edges := 10, rows := 1, starsRows := 0, negTested := 0, negFree := true, uposTested := 0, uposFree := true },
      { edges := 10, rows := 1, starsRows := 0, negTested := 0, negFree := true, uposTested := 0, uposFree := true }))
    ("Sd: DRAINED ROWS (C)",
     some [({ type := "doc", name := "d1", pred := "approver", variant := Zanzibar.Variant.plain },
       "approver",
       { stars := [], neg := [], upos := [] })])
    ("Sw: DOMAIN SIZE", 144)
    ("Sw: PROBE (A subject, B bare-preflip, C drained, D bridge)",
     some ({ edges := 5, rows := 1, starsRows := 1, negTested := 2, negFree := true, uposTested := 0, uposFree := true },
      { edges := 5, rows := 1, starsRows := 1, negTested := 2, negFree := false, uposTested := 0, uposFree := true },
      { edges := 5, rows := 1, starsRows := 1, negTested := 4, negFree := true, uposTested := 0, uposFree := true },
      { edges := 6, rows := 1, starsRows := 1, negTested := 2, negFree := false, uposTested := 0, uposFree := true }))

**What it licenses:**

* **At `Sd`/`Td4` the invariant clause is never exercised: `negTested := 0` on all four
  legs, INCLUDING the pre-flip control (B) and the bridge control (D).** The row exists
  (`rows := 1`, keyed at the bare `doc:d1#approver`, so the key is in the domain) but its
  `stars` are empty — `Sd` declares no wildcard shape — and a `neg` member is only ever
  recorded against a covered star shape. So the instrument cannot tell pre-flip from
  post-flip at this store. MEASURED; the mechanism REASONED from `stars := []` + the
  2026-09-05b trap on the row (*"no wildcard ⇒ `neg = []`"*), which this run confirms.
* **Consequence: the two "halves" were never in tension.** `outside_narrow_t2a`
  (`FullScope.lean::W4WitnessDirect.outside_narrow_t2a`) refutes the BUNDLE — its proof is
  `fun hN => outside_old_admission hN.storeValid`, i.e. the narrow `StoreValidRules`
  field, READ — not the invariant. The only store where `negEdgeFree` has content is `Sw`,
  and there the same file reproduces 2026-09-05 exactly (A green / B red at the same
  `negTested := 2`; D red). So "the obstacle is gone" is measured where the obstacle was.
* **Consequence for the dual witness the row owes:** a positive witness at `Sd`/`Td` would
  be VACUOUS for `negEdgeFree` and would pass under a sabotage of that clause. The
  discriminating witness belongs at `Sw` (§ 3). An `Sd`/`Td` instance is still worth
  landing, but as the SCOPE witness (the theorem now applies to a Direct-arm store it was
  vacuous on), not as evidence about `negEdgeFree`.

## § 2 The proof map (READ unless marked)

The owed obligation, restated from READ code: `CascadeStrataEdge.lean::reachedByW3d2E_inv`
takes `hCO` (schema-wide `ComputedOnly`) and `hSV : StoreValidRules` (narrow); both come
from `W4NarrowT2a` in `FullScope.lean::graph_reached_inv`. Every consumer of those two in
the T2a chain, and its widened twin:

| consumer (in `CascadeStrataEdge.lean` unless noted) | uses | `_d` twin (READ, exists) |
|---|---|---|
| `CascadeStrataInv.lean::reconcileStarsKeyDR_row_edge_consistent` | `hco` → `reconcileStarsKeyDR_edge_char` | **none** — but `CascadeStrataResettle.lean::reconcileStarsKeyDR_edge_char_d` exists (takes `hcd`+`hba`), so the twin is a one-call swap |
| `edgeHyg1_applyLoggedR` / `_reconcileJobsLR` / `_runCascade2` | thread `hCO` to the row above | none — mechanical |
| `reachedByW3d2E_edgeHyg1`, write leg | `writeLeg_derived_inedges_eq` (hco, hSV) | `CascadeStrataSettle.lean::writeLeg_derived_inedges_eq_d` (hne from node inequality) |
| same, remove leg | `removeLeg_derived_inedges_eq` | `::removeLeg_derived_inedges_eq_d` |
| same, cascade leg: σp chain facts | `reachedByW3d2E_toC` | `CascadeStrataAssemble.lean::reachedByW3d2E_toC_d` |
| same, cascade leg: `hsb`, `hjv1`/`hjv2` | `reachedByW3d2_Rnode_source_bare` / `_name_ne_star` | `::reachedByW3d2_Rnode_source_bare_d` / `::reachedByW3d2_Rnode_source_name_ne_star_d` |
| `reachedByW3d2E_edgeHygienic` | `reachedByW3d2_reach_collapse_root` | `::reachedByW3d2_reach_collapse_root_d` |

So the P4-session estimate (*"one `hco` binder + the three-lemma `edgeHyg1_*` re-point"*)
UNDERCOUNTED: the chain lemma `reachedByW3d2E_edgeHyg1` and `reachedByW3d2E_edgeHygienic`
also consume `hCO`/`hSV` at five further sites — but every one already has a `_d` twin, so
the size stays `M` and no new mathematics is owed. REASONED from the table.

`GraphAdmission.storeValid` is already `StoreValidRulesD` (READ, `FullScope.lean`
structure `GraphAdmission`), so the restated `graph_reached_inv` takes `hA`/`hF` only.

## § 3 Witnesses owed with the restatement (REASONED; the landing section records what landed)

* **Scope witness at `Sd`/`Td`**: `graph_reached_inv` instantiated with
  `W4WitnessDirect.admission`/`w4fragment` — the theorem stops being vacuous on the
  Direct-arm store.
* **Discriminating witness at `Sw`**: the only store where `negEdgeFree` is exercised
  (§ 1). Requires `GraphAdmission`/`W4Fragment` at `Sw` and its store.

## § 4 What LANDED (2026-09-23; READ unless marked)

**Decision (recorded per `CLAUDE.md` § "Who decides"): widen IN PLACE, delete the bundle.**
The T2a chain lemmas had exactly one consumer (`FullScope.lean::graph_reached_inv`; grep
2026-09-23, every other hit an `Audit.lean` `#print axioms`), so minting `_d` twins beside
them would have left a dead narrow chain. And a `W4NarrowT2a` structure that no theorem takes,
kept alive only by a pinned refutation of itself, would be exactly the illegible surface the
goal (`docs/goal-census-2026-09-22.md`) says to stop producing. So:

* `CascadeStrataInv.lean::reconcileStarsKeyDR_row_edge_consistent` — `hco : ComputedOnly e`
  replaced by `hcd : ComputedOrDirect e` + `hba : DirectArmsBare e`, consuming
  `CascadeStrataResettle.lean::reconcileStarsKeyDR_edge_char_d`.
* `CascadeStrataEdge.lean` — `edgeHyg1_applyLoggedR` / `_reconcileJobsLR` / `_runCascade2`
  take `hCD`+`hDAB` for `hCO`; `reachedByW3d2E_edgeHyg1` / `_edgeHygienic` / `_inv` take
  `reachedByW3d2E_toC_d`'s bundle. Write/remove legs use `writeLeg_derived_inedges_eq_d` /
  `removeLeg_derived_inedges_eq_d` with the new `::objNode_ne_derived_of_untainted`
  (type+pred projection, so NO `t.object.name ≠ STAR` side condition — the existing
  `CascadeStrataSettle.lean::writeLeg_inedges_eq_of_unmapped` needs one). The remove leg's
  plain `StoreValidRules` carry converts via
  `CascadeStrataSettle.lean::storeValidRulesD_of_storeValidRules_directArmsBare`.
* `FullScope.lean::graph_reached_inv` — `hN` deleted; statement pin regenerated
  (`formal/headline_statements.txt`). `W4NarrowT2a`, `w4NarrowT2a_of_untainted`,
  `W4WitnessDirect.outside_narrow_t2a` DELETED.
* Witnesses: `FullScope.lean::W4WitnessDirect.reached_inv_applies` / `::reached_inv_applies4`
  (scope), `GraphIndex/Exec.lean::P5Witness.leafRouted_inv_preflip_not` +
  `::P5Witness.prefix_facts` (content), with `::P5Witness.admission` / `::w4fragment` — the
  first `GraphAdmission`/`W4Fragment` instance at a store carrying a wildcard grant and a
  Direct-arm derived write together.
* Audit identity pin: `formal/audited_theorems.txt` regenerated, `628` names on 2026-09-23 (two removed,
  `W4WitnessDirect.outside_narrow_t2a` and `w4NarrowT2a_of_untainted`, seven added). Justification for the removal is this
  section and `formal/history/` (the dated entry this session adds).

Build: `lake build` (whole package incl. `Audit`) rc=0, `Build completed successfully (1089 jobs)`,
2026-09-23. No new warnings in the touched modules.

## § 5 Sabotage (2026-09-23; literal output, `docs/sabotage-procedure.md`)

Each mutation applied to the working tree, `lake build ZanzibarProofs.GraphIndex.Exec`, then
restored (`cmp` against the saved copy).

* **M1 — drop the wildcard grant** (`prefixOps := [add tb]`, `prefixStore := [tb]`). RED at the
  target:

      error: ZanzibarProofs/GraphIndex/Exec.lean:1374:2: Tactic `decide` proved that the proposition
        Option.map (fun p => (p.2, foldAdmitsBridgedB …, … r.neg.contains bob …, …))
            (graphRunOps LeafWitness.Sw prefixOps) =
          some (prefixStore, true, some true, some true, true)
      is false

  plus collateral at `P5Witness.admission` (`:1296`, its `rcases` destructures the store
  shape: `restrictionMatches [("user", BARE, true)] LeafWitness.tb = true is false`). Shows the
  `neg` row is non-empty BECAUSE of the star — the witness is not vacuous.
* **M2 — claim the leaf-routed write lands `bob → approver`** (last component of
  `prefix_facts` switched from `writeLoggedOne` to `writeLoggedRules`). RED at the target
  (`Exec.lean:1374:2: Tactic decide proved that the proposition … is false`), plus collateral
  `Exec.lean:1423:75: Application type mismatch: The argument hedge` in the `¬ Inv` proof.
  Shows the discriminating fact is real: the routed write does NOT land the edge.
* **M3 — weaken `Inv.negEdgeFree` to range over `res.upos`** (`State.lean:725`). **Died
  upstream**, never reached the witness:

      error: ZanzibarProofs/GraphIndex/State.lean:910:24: Application type mismatch: The argument
        hn
      has type
        n ∈ res.upos
      but is expected to have type
        n ∈ res.neg
      in the application
        hnf n hn

  (`State.lean::inv_putResidue`). Instrument limit, as on `P4`'s M1/M2: a definition mutation
  is caught by the first upstream consumer, so this says nothing about the witness. That the
  witness would catch it is REASONED only — `leafRouted_inv_preflip_not` applies
  `hInv.negEdgeFree` to `bob ∈ res.neg` directly — and the `Inv` definition is independently
  byte-pinned (`formal/headline_definitions.txt`, `def:Zanzibar.Inv`).
