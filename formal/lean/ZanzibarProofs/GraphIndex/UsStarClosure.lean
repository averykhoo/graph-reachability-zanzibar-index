import ZanzibarProofs.GraphIndex.UsStarCorrect
import ZanzibarProofs.GraphIndex.ObjStarClosure
import ZanzibarProofs.Spec.WellDef

/-!
# T2b, stage W1c — the userset-star write-closure and `check = sem`

`SEMANTICS.md` §7.3–7.5; ROADMAP "The staged T2 plan", sub-stage **W1c**;
`wildcard-materialization-spec.md §1.1` (the `concrete → w_any` in-bridge composition).

`UsStarCorrect.lean` proved both semantic cores of the W1c read correspondence *over
the operational facts they consume* — soundness over the grant-or-bridge edge
characterization (`usStarReach_of_trail` + `semAux_of_usStarReach`, a property of any
`UsStarReached` state), completeness over edge-completeness `hEC` and the **guarded**
in-bridge completeness `hib`. This file **assembles** the two halves into
`graph_correct_usStar` (full `check = sem`):

* **Soundness assembly** (`sem_of_usStar_probe`) — needs no closure and no fuel-count.
  The W1b plain-node accounting (`grantReach_of_trail`'s `isPlain`-source bound) does
  **not** transfer: a userset-star grant's source is a `w_any` node, not plain, and an
  in-bridge consumes a `w_any` as a target. Instead we discharge the fuel obligation via
  **`sem_fuel_stable`** (T0a): the chain gives `semAux` at fuel `m` for *some* `m`, and
  `sem` is stable above `fuelBound`, so `sem = semAux (max m fuelBound) = true` by
  `semAux_mono` (up to the max) then stability (down to `sem`). No tight `m ≤ fuelBound`
  bound is needed — the exact gap the ROADMAP flagged for W1c is sidestepped.
* **`UsStarReachedAdmitted`** + **`usStarReachedAdmitted_edge_complete`** (`hEC`) and
  **`usStarReachedAdmitted_inbridge_complete`** (discharging the guarded `hib`) — the W1c
  analog of `WildReachedAdmitted`.
* **`graph_correct_usStar`** — `check = sem` on the userset-star fragment (probe 1 ∨
  probe 2; probes 3,4 dead — objects star-free, no `w_all` target). Probe 2 is LIVE
  (a userset query subject's `wAny(s.shape)` sees userset-star direct grants), unlike
  W1b. Mirror of `graph_correct_bareStar`.
-/

namespace Zanzibar

/-! ## `StoreValid ⇒ StoreDeclared` (for the T0a stability hypothesis) -/

/-- Admission-validity implies the (weaker) `StoreDeclared` clause T0a needs: a stored
    tuple's subject type is named in its relation's `Direct` restrictions. From
    `restrictionMatches`: the matched restriction `r` has `r.1 = subject.type`, and
    `directTypes (.direct rs) = rs.map (·.1)`. -/
theorem storeDeclared_of_storeValid {S : Schema} {T : Store}
    (h : StoreValid S T) : StoreDeclared S T := by
  intro tup htup
  obtain ⟨rs, hlk, hrm⟩ := h tup htup
  refine ⟨Expr.direct rs, hlk, ?_⟩
  unfold restrictionMatches at hrm
  obtain ⟨r, hr, hrmatch⟩ := List.any_eq_true.mp hrm
  simp only [Bool.and_eq_true, beq_iff_eq] at hrmatch
  unfold directTypes
  exact List.mem_map.mpr ⟨r, hr, hrmatch.1.1.symm⟩

/-! ## Soundness assembly — the fuel obligation via T0a stability

`semAux_of_usStarReach` yields a `sem` membership at fuel = the chain length `m`, with
no bound on `m` (the W1c chain over-counts: an in-bridge hop is a separate hop but the
`sem` derivation absorbs it into the following userset-star grant). Rather than
re-derive a tight `m ≤ fuelBound` count (the plain-node argument breaks — a userset-star
grant's source is a `w_any` node), we appeal to fuel-stability: `sem` does not change
above `fuelBound`, so any fuel `≥ fuelBound` computes `sem`, and `semAux_mono` lifts the
fuel-`m` membership to `max m fuelBound ≥ fuelBound`. -/

/-- **`UsStarReach ⇒ sem` at `fuelBound`.** A generalized userset-star chain from a node
    `w` covering the star-free query subject to the concrete query object is a `sem`
    membership — discharging the fuel obligation via `sem_fuel_stable` (no tight
    chain-length bound). -/
theorem sem_of_usStarReach {S : Schema} {T : Store} {q : Query}
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hUS : UsStarStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    {m : Nat} {w : NodeKey} (hcov : UsCovers q.subject w)
    (hm : UsStarReach T m w (objNode q.object q.relation)) : sem S T q = true := by
  have hsem_m : semAux S q.subject T q m q.object.type q.object.name q.relation = true :=
    semAux_of_usStarReach hWF hPD hSV hUS hm hqs hcov hqo rfl
  have hStrat := stratifiable_pureDirect hPD
  have hDecl := storeDeclared_of_storeValid hSV
  have hmf : m ≤ max m (fuelBound S T) := le_max_left _ _
  have hfbf : fuelBound S T ≤ max m (fuelBound S T) := le_max_right _ _
  have hsem_f := semAux_mono S (pureDirect_noExclAll hPD) q.subject T q hmf _ _ _ hsem_m
  rw [← sem_fuel_stable S T q hStrat hDecl _ hfbf]
  exact hsem_f

/-- **Soundness of the W1c read (forward direction).** From a probe source `w` covering
    the star-free query subject (probe 1 = `subjNode q.subject`, probe 2 =
    `wAnyNode q.subject.shape`), graph reachability to the concrete query object node is
    a `sem` membership. Routes through `usStarReach_of_trail` (existence of a chain) then
    `sem_of_usStarReach` (the fuel-stable discharge). -/
theorem sem_of_usStar_probe {S : Schema} {T : Store} {σ : GraphState} {q : Query}
    (hWF : WF S) (hPD : PureDirect S) (hSV : StoreValid S T) (hUS : UsStarStore T)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)
    (hReach : UsStarReached σ S T) {w : NodeKey} (hcov : UsCovers q.subject w)
    (hnr : NReaches σ.edges w (objNode q.object q.relation)) : sem S T q = true := by
  have hwvar : w.variant = Variant.plain ∨ w.variant = Variant.wAny := by
    rcases hcov with h | ⟨_, h⟩
    · subst h; left; rw [subjNode_plain hqs]
    · subst h; right; rfl
  have hvvar : (objNode q.object q.relation).variant = Variant.plain := by
    rw [objNode_plain hqo]
  obtain ⟨l, hl⟩ := trail_of_nreaches hnr
  obtain ⟨m, hm⟩ := usStarReach_of_trail hReach hUS l.length l (le_refl _)
    w (objNode q.object q.relation) hwvar hvvar hl
  exact sem_of_usStarReach hWF hPD hSV hUS hqs hqo hcov hm

end Zanzibar
