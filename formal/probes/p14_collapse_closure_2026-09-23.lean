/-
  `P14` (leg 7 step 5, reach-collapse half) — which reach-collapse lemmas do the HEADLINE
  theorems actually rest on? Kept OUTSIDE the lake package on purpose (like the `P4`
  probe): it is not part of the gated build, it is evidence that can be re-run. Run from
  formal/lean (needs built oleans):

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p14_collapse_closure_2026-09-23.lean

  METHOD: the transitive closure of `ConstantInfo.getUsedConstantsAsSet` from each root,
  expanding only constants defined in a `ZanzibarProofs.*` module (core/Mathlib are
  leaves). For every name in `families`, print whether it is IN the closure of each root.

  CONTROLS (the instrument must be able to say both YES and NO):
    * POSITIVE — `reachedByW3d2_reach_collapse_root_d` must be IN `graph_reached_inv`'s
      closure (`P5` consumes it at `CascadeStrataEdge.lean::reachedByW3d2E_edgeHygienic`).
    * NEGATIVE — `P4Bridge.bridge_holds_Sw` is a `by decide` witness nothing imports, so
      it must be OUT of every root's closure.
  A run where either control fails is a broken instrument, not a finding.
-/
import Lean
import ZanzibarProofs
open Lean Elab Command

namespace P14Probe

def inProject (env : Environment) (n : Name) : Bool :=
  match env.getModuleIdxFor? n with
  | some idx => (`ZanzibarProofs).isPrefixOf (env.header.moduleNames[idx.toNat]!)
  | none => true   -- defined in this file / main module

partial def closure (env : Environment) (roots : List Name) : NameSet := Id.run do
  let mut seen : NameSet := {}
  let mut work := roots
  while !work.isEmpty do
    match work with
    | [] => pure ()
    | n :: rest =>
      work := rest
      if seen.contains n then continue
      seen := seen.insert n
      if !inProject env n then continue
      match env.find? n with
      | some ci => work := ci.getUsedConstantsAsSet.toList ++ work
      | none => pure ()
  return seen

def roots : List Name := [
  `Zanzibar.graph_correct, `Zanzibar.graph_correct_public, `Zanzibar.graph_reached_inv,
  `Zanzibar.backend_equivalence, `Zanzibar.no_ghost_grant, `Zanzibar.exclusion_effective,
  `Zanzibar.graphRunOps_check_eq_sem, `Zanzibar.graphModeAnswers_eq_sem]

def families : List Name := [
  -- controls
  `Zanzibar.P4Bridge.bridge_holds_Sw,
  -- W3d2 (the chain the headlines are stated over)
  `Zanzibar.reachedByW3d2_reach_collapse_root_d, `Zanzibar.reachedByW3d2_reach_collapse_root,
  `Zanzibar.reachedByW3d2_Rnode_source_bare_d, `Zanzibar.reachedByW3d2_Rnode_source_bare,
  `Zanzibar.reachedByW3d2_bareNode_no_inedge_d, `Zanzibar.reachedByW3d2_bareNode_no_inedge,
  `Zanzibar.reconcileJobsLR_reach_collapse,
  -- W3d
  `Zanzibar.reachedByW3d_reach_collapse_root, `Zanzibar.reachedByW3d_Rnode_source_bare,
  `Zanzibar.reachedByW3d_bareNode_no_inedge,
  -- W3a
  `Zanzibar.reachedByW3a_reach_collapse_root_d, `Zanzibar.reachedByW3a_reach_collapse_root,
  `Zanzibar.reachedByW3a_reach_collapse, `Zanzibar.reachedByW3a_Rnode_source_bare_d,
  `Zanzibar.reachedByW3a_Rnode_source_bare,
  -- the base-chain fact §11.9 says keeps leaf edges off declared R-nodes
  `Zanzibar.reachedByRules_derived_no_inedge,
  -- the classification half (landed with P3)
  `Zanzibar.DerNode, `Zanzibar.UntaintedShadow, `Zanzibar.LeafNode]

#eval show CommandElabM Unit from do
  let env ← getEnv
  for f in families do
    if (env.find? f).isNone then logInfo m!"MISSING {f}"
  let mut out := ""
  for r in roots do
    if (env.find? r).isNone then
      out := out ++ s!"ROOT MISSING {r}\n"; continue
    let c := closure env [r]
    out := out ++ s!"{r}  (closure {c.size})\n"
    for f in families do
      out := out ++ s!"    {if c.contains f then "IN " else "out"}  {f}\n"
  logInfo out

end P14Probe
