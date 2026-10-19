import ZanzibarProofs.GraphIndex.SelfRead
import ZanzibarProofs.GraphIndex.AdmissionDecide

/-!
# Non-vacuity witnesses for the self-relation headlines (TK144)

The `*R` headline theorems (`GraphIndex/SelfRead.lean`) are stated under `graph_correct`'s
bundles. A bundle nobody can inhabit, or a reflexive read that never differs from the base
one, would make them true and empty. These declarations refute both at a concrete store:
challenge C1's cross-object model C, cut to the rows that matter
(`docs/tk138-userset-self-relation-2026-10-14.md` §C1; OpenFGA v1.22.0 answers `group:1#admin`
a viewer of `doc:1`, and of `doc:1#nb`).

* `premise` -- `GraphAdmission ∧ W4Fragment` hold there (decided, `headlinePremiseB_iff`).
* `spec_flip` -- the spec moved: `semR` grants `group:1#admin` on `nb@doc:1`, the base `sem`
  denies it. A self-relation spec that never fired would fail this.
* `driver_flip` -- the executable driver: the reflexive public read answers `true`, the base
  public read `false`, on a drained state.
* `correct_applies` -- `graph_correct_publicR` INSTANTIATED there, every hypothesis
  discharged, and the agreed answer is a GRANT.
* `vx_flip` -- model B's `vx`: a userset in its own subtrahend is DENIED by `semR` and was
  ALLOWED by `sem` (the ALLOW-to-DENY change; outside the graph fragment, spec level only).
-/

namespace Zanzibar

namespace SelfWitness

/-- Model C, cut down: `group#member := [user] or admin`, `doc#viewer := [user, group#member]`,
    `doc#nb := viewer but not banned`. -/
def Sc : Schema :=
  ⟨[(("group", "admin"), .direct [("user", BARE, false)]),
    (("group", "member"), .union (.direct [("user", BARE, false)]) (.computed "admin")),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "viewer"), .direct [("user", BARE, false), ("group", "member", false)]),
    (("doc", "nb"), .excl (.computed "viewer") (.computed "banned"))], []⟩

/-- The one input tuple: `group:1#member viewer doc:1`. -/
def tc : List Tuple := [⟨⟨"group", "1", "member"⟩, "viewer", ⟨"doc", "1"⟩⟩]

/-- The store the driver ends with. -/
def Tc : Store := [⟨⟨"group", "1", "member"⟩, "viewer", ⟨"doc", "1"⟩⟩]

/-- `group:1#admin` on `doc:1#nb` -- reached only through `group#member`'s computed `admin`
    arm and the stored `group:1#member viewer doc:1` (OpenFGA v1.22.0: true). -/
def qc : Query := ⟨⟨"group", "1", "admin"⟩, "nb", ⟨"doc", "1"⟩⟩

theorem premise : GraphAdmission Sc Tc ∧ W4Fragment Sc Tc :=
  (headlinePremiseB_iff Sc Tc).mp (by decide)

theorem spec_flip : semR Sc Tc qc = true ∧ sem Sc Tc qc = false := by decide

theorem driver_flip :
    (graphRun Sc tc).map (fun p => (p.2, graphModeAnswersR p.1 [qc], graphModeAnswers p.1 [qc],
        drainedB Sc p.1)) = some (Tc, [true], [false], true) := by
  decide

/-- **`graph_correct_publicR` instantiated at the witness**, the answer a grant. -/
theorem correct_applies :
    ∃ σ : GraphState, graphRun Sc tc = some (σ, Tc) ∧
      GraphModel.checkPublicR σ qc = semR Sc Tc qc ∧ semR Sc Tc qc = true := by
  have hd := driver_flip
  cases hopt : graphRun Sc tc with
  | none => rw [hopt] at hd; simp at hd
  | some p =>
      obtain ⟨σ0, T0⟩ := p
      rw [hopt] at hd
      simp only [Option.map_some, Option.some.injEq, Prod.mk.injEq] at hd
      obtain ⟨hT, _, _, hdr⟩ := hd
      subst hT
      refine ⟨σ0, rfl, ?_, spec_flip.1⟩
      exact graphRun_check_eq_semR hopt hdr premise.1 premise.2 qc (by decide) (by decide)

/-- Model B's `vx := [user, doc#banned] but not banned` with the stored
    `doc:1#banned vx doc:1`: DENIED by the spec (the userset is in its own subtrahend),
    ALLOWED by the base `sem`. -/
def Sb : Schema :=
  ⟨[(("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "vx"), .excl (.direct [("user", BARE, false), ("doc", "banned", false)])
      (.computed "banned"))], []⟩

def Tb : Store := [⟨⟨"doc", "1", "banned"⟩, "vx", ⟨"doc", "1"⟩⟩]

def qb : Query := ⟨⟨"doc", "1", "banned"⟩, "vx", ⟨"doc", "1"⟩⟩

theorem vx_flip : semR Sb Tb qb = false ∧ sem Sb Tb qb = true := by decide

end SelfWitness

end Zanzibar
