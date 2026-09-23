# `P14` — the reach-collapse half: what was still owed (nothing), measured

**FROZEN at `P14`'s close, 2026-09-23c.** Close-out map for `P14`, the last row of goal step 2
(`docs/goal-census-2026-09-22.md`). Every figure in the body was measured on `2026-09-23`
against HEAD `988a32c` (built oleans, gate COVERED on that tree); the body is provenance, not a
living status. Live state is `python scripts/task.py show P14` — never this file. Corrections
append **dated at the top**, never edited into the body.

Provenance labels: **READ** (verified first-hand this session, `file::symbol`), **REASONED**,
**MEASURED** (a probe run this session, literal output quoted), **UNVERIFIED**.

---

## § 1 What the row owed, restated from the scope doc (READ)

`formal/history/leaf-family-split-scope-2026-08-05.md` §5 "The deepest single change" and §7
step 5 asked for three things under the leaf split:

1. **Re-partition `DerNode`/`UntaintedShadow`**: the classification half. Absorbed into `P3`
   on 2026-08-20b (scope doc §11.9 point 3). Landed with `P3` on 2026-09-05b.
2. **Re-prove the reach-collapse family** ("any path into the R-node is a single edge"),
   *re-proving, not adapting*, because the write leg would change under it.
3. **Re-point `graphRec`/`checkFn` at leaf predicates**, with collapse holding *per node* at
   leaf nodes too.

## § 2 Item 2 is discharged by the tree as it stands (READ)

The write leg the scope doc feared for is the one the chains now run:

* `CascadeStrata.lean::ReachedByW3d2.write` and `Cascade.lean::ReachedByW3d.write` both step
  by `σ.writeLoggedRules S t` under `FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t))`.
  That is the leaf-routed fold since the 2026-09-05 flip (`formal/HANDOFF.md` "Landed
  2026-09-05").
* The collapse family is proved over that chain at the widened (`_d`) scope:
  `CascadeStrataSettle.lean::reachedByW3d2_reach_collapse_root_d`, from
  `::reachedByW3d2_Rnode_source_bare_d` + `::reachedByW3d2_bareNode_no_inedge_d`. The proof
  comment on `_Rnode_source_bare_d` records the post-flip re-proof: *"`WF S` is new (step
  4c-ii): the write case's rule branch now ranges over `schemaRewritesL`, whose leaf half is
  refuted by name (`noRuleOutputsL_of_derived`)"*.
* The mid-batch form `CascadeStrataSettle.lean::reconcileJobsLR_reach_collapse` takes its
  edge discipline as hypotheses (`htb`, `hsb`) and has no scope premise at all, so the leaf
  split cannot reach it.

So "re-prove the family" happened during 4c-ii and the flip, and nothing recorded it against
this row. Same shape as `P4`: the obligation was met by a different step than the plan named.

## § 3 Item 3 has no consumer (READ via `P4`, REASONED here)

`P4` (2026-09-23, `docs/p4-leaf-probe-bridge-2026-09-23.md`) established that `checkFn` /
`checkFnR` evaluate the RAW def and read the STORE at the PUBLIC relation. `GraphAdmission`
also closes every route a leaf name could take into `rec` (`computedRefsNotLeaf`,
`directRestrNotLeaf`, `ttuNotLeaf`). The tree took the **refusal** route, not the re-point
route. A per-leaf-node collapse lemma would have no reader in Lean. Its only possible reader
is Python's `_EvalContext.leaf_check`, which is `P4`'s `CORRESPONDENCE.md` §7.3 item (Lean ↔
Python). It is not a theorem this row owes.

## § 4 The headline theorems rest on the `_d` family ONLY (MEASURED)

Probe: [`formal/probes/p14_collapse_closure_2026-09-23.lean`](../formal/probes/p14_collapse_closure_2026-09-23.lean),
run `cd formal/lean && lake env lean ../probes/p14_collapse_closure_2026-09-23.lean`, **rc=0**.
Method: the transitive closure of `ConstantInfo.getUsedConstantsAsSet` from each root,
expanding only `ZanzibarProofs.*` constants. Roots: the eight headline theorems
`graph_correct`, `graph_correct_public`, `graph_reached_inv`, `backend_equivalence`,
`no_ghost_grant`, `exclusion_effective`, `graphRunOps_check_eq_sem`,
`graphModeAnswers_eq_sem`.

**All eight rows are identical except for closure size** (`2113`–`2363` project constants).
One row, literal:

    Zanzibar.graph_reached_inv  (closure 2113)
        out  Zanzibar.P4Bridge.bridge_holds_Sw
        IN   Zanzibar.reachedByW3d2_reach_collapse_root_d
        out  Zanzibar.reachedByW3d2_reach_collapse_root
        IN   Zanzibar.reachedByW3d2_Rnode_source_bare_d
        out  Zanzibar.reachedByW3d2_Rnode_source_bare
        IN   Zanzibar.reachedByW3d2_bareNode_no_inedge_d
        out  Zanzibar.reachedByW3d2_bareNode_no_inedge
        IN   Zanzibar.reconcileJobsLR_reach_collapse
        out  Zanzibar.reachedByW3d_reach_collapse_root
        out  Zanzibar.reachedByW3d_Rnode_source_bare
        out  Zanzibar.reachedByW3d_bareNode_no_inedge
        out  Zanzibar.reachedByW3a_reach_collapse_root_d
        out  Zanzibar.reachedByW3a_reach_collapse_root
        out  Zanzibar.reachedByW3a_reach_collapse
        out  Zanzibar.reachedByW3a_Rnode_source_bare_d
        out  Zanzibar.reachedByW3a_Rnode_source_bare
        out  Zanzibar.reachedByRules_derived_no_inedge
        IN   Zanzibar.DerNode
        IN   Zanzibar.UntaintedShadow
        IN   Zanzibar.LeafNode

**Instrument controls, both in the same run:** the POSITIVE control
(`reachedByW3d2_reach_collapse_root_d` IN `graph_reached_inv`) sits several hops deep
(`graph_reached_inv` → `reachedByW3d2E_inv` → `reachedByW3d2E_edgeHygienic` → it), so the
closure really is transitive. The NEGATIVE control (`P4Bridge.bridge_holds_Sw`, a `by decide`
witness nothing imports) is OUT of all eight, so the instrument can also say no. The first
two runs failed on API names (`ConstantInfo.getUsedConstants` does not exist in
`v4.31.0`). They were compile errors, never a result, and the fixed file is the one tracked.

## § 5 Verdict — `P14` closes as ABSORBED (decision per `CLAUDE.md` § "Who decides")

Nothing is owed. The classification half landed with `P3`. The collapse family is proved
over the leaf-routed chain at the scope every headline states (§2, §4). The per-leaf-node
half has no Lean reader by construction (§3). Goal step 2 is complete: all headline
theorems stand under `GraphAdmission` + `W4Fragment` alone, and the collapse lemmas they
use carry no narrower premise.

## § 6 Observations handed on, not acted on (READ; goal step 3 territory)

* The **narrow** collapse lemmas (`reachedByW3d2_reach_collapse_root`,
  `_Rnode_source_bare`, `_bareNode_no_inedge`) still have in-tree consumers
  (`CascadeStrataEnum.lean`, `CascadeStrataResettle.lean`, `CascadeStrataSettle.lean`,
  `CascadeStrataAssemble.lean`; grep 2026-09-23). None of those consumers is in a headline
  closure (§4). They serve the staged `ComputedOnly` milestones.
* `ReconcileCorrect.lean::reachedByW3a_reach_collapse_root_d` has **zero** consumers outside
  `Audit.lean` (grep 2026-09-23). It is audited, but no theorem uses it.
* The whole W3a/W3d collapse families are off every headline closure. They prove the
  staged ladder (`ARCHITECTURE.md`), not the shipped claim.

In short, the audited set (`formal/audited_theorems.txt`) is not the same thing as "what the
headlines rest on", and nothing in the repo currently says which audited names are which. The
probe in §4 generalises directly: take the union closure of the headline set and intersect it
with `audited_theorems.txt`. Filed as `TK103` (`LATER`); this probe is its starting point.
