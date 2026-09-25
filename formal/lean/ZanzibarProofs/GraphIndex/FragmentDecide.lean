import ZanzibarProofs.GraphIndex.Exec

/-!
# `W4Fragment` is decidable — the Bool decider behind a driver-side pre-check (`DW-1`)

`FullScope.lean::W4Fragment` is the hypothesis bundle that SCOPES every headline theorem,
and seven of its ten fields are SILENT on the Python side: a schema outside them is accepted
and answers queries with no signal (`formal/conformance/test_w4fragment_scope_pin.py::
W4FRAGMENT_SCOPE`). Nothing could even ASK whether a given `(S, T)` is inside, because the
bundle had no decider — every witness in the tree was proved field by field, by hand.

This module supplies `w4FragmentB S T : Bool` with the EXACT equivalence
`w4FragmentB_iff : w4FragmentB S T = true ↔ W4Fragment S T` (both directions: soundness
means "accepted ⇒ the theorems apply", completeness means "no in-scope input is refused"),
and hence `instance : Decidable (W4Fragment S T)`. `w4FragmentFieldsB` exposes the same ten
conjuncts BY FIELD NAME, which is what a driver needs to say WHICH field failed.

**The quantifier decision** (`docs/dw1-decidable-w4fragment-2026-09-23.md` §1). Six fields
quantify `∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → …` over ALL
strings. Rephrasing that as `∀ p ∈ S.defs` would be strictly STRONGER when keys repeat
(`Schema.lookup` is a first-match `find?`, and `WF` carries no nodup clause — `NodupKeys` is
only `GraphAdmission.nodup`), so the decider would refuse some in-scope schemas. Instead
`derivedDefsAll` ranges over `taintedKeys S` — `isDerived` IS membership there — and
`match`es `S.lookup k`, which is exact with no premise. `Exec.lean::htermB_iff` is the
precedent for the shape.

`GraphAdmission` — the OTHER half of the headline premise — is NOT decided here: its
`RewriteRanked` field is an existential over rank functions. Out of `DW-1`'s scope, by
decision recorded on the row. It is decided since 2026-09-25 (`TK104`) in
`AdmissionDecide.lean::graphAdmissionB_iff`, which also decides the whole premise.
-/

namespace Zanzibar

/-! ## Bool twins of the three structural `Expr` predicates -/

/-- Executable `ReconcileCorrect.lean::ComputedOrDirect`. -/
def computedOrDirectB : Expr → Bool
  | .computed _ => true
  | .direct _ => true
  | .union a b => computedOrDirectB a && computedOrDirectB b
  | .inter a b => computedOrDirectB a && computedOrDirectB b
  | .excl a b => computedOrDirectB a && computedOrDirectB b
  | .ttu _ _ => false

theorem computedOrDirectB_iff : ∀ e, computedOrDirectB e = true ↔ ComputedOrDirect e
  | .computed _ => by simp [computedOrDirectB, ComputedOrDirect]
  | .direct _ => by simp [computedOrDirectB, ComputedOrDirect]
  | .ttu _ _ => by simp [computedOrDirectB, ComputedOrDirect]
  | .union a b => by
      simp [computedOrDirectB, ComputedOrDirect, computedOrDirectB_iff a, computedOrDirectB_iff b]
  | .inter a b => by
      simp [computedOrDirectB, ComputedOrDirect, computedOrDirectB_iff a, computedOrDirectB_iff b]
  | .excl a b => by
      simp [computedOrDirectB, ComputedOrDirect, computedOrDirectB_iff a, computedOrDirectB_iff b]

/-- Executable `ReconcileCorrect.lean::DirectArmsBare`. -/
def directArmsBareB : Expr → Bool
  | .computed _ => true
  | .direct rs => rs.all fun r => r.2.1 == BARE
  | .union a b => directArmsBareB a && directArmsBareB b
  | .inter a b => directArmsBareB a && directArmsBareB b
  | .excl a b => directArmsBareB a && directArmsBareB b
  | .ttu _ _ => true

theorem directArmsBareB_iff : ∀ e, directArmsBareB e = true ↔ DirectArmsBare e
  | .computed _ => by simp [directArmsBareB, DirectArmsBare]
  | .direct _ => by simp [directArmsBareB, DirectArmsBare, List.all_eq_true]
  | .ttu _ _ => by simp [directArmsBareB, DirectArmsBare]
  | .union a b => by
      simp [directArmsBareB, DirectArmsBare, directArmsBareB_iff a, directArmsBareB_iff b]
  | .inter a b => by
      simp [directArmsBareB, DirectArmsBare, directArmsBareB_iff a, directArmsBareB_iff b]
  | .excl a b => by
      simp [directArmsBareB, DirectArmsBare, directArmsBareB_iff a, directArmsBareB_iff b]

/-- Executable `ReconcileCorrect.lean::ComputedOnly`. -/
def computedOnlyB : Expr → Bool
  | .computed _ => true
  | .union a b => computedOnlyB a && computedOnlyB b
  | .inter a b => computedOnlyB a && computedOnlyB b
  | .excl a b => computedOnlyB a && computedOnlyB b
  | .direct _ => false
  | .ttu _ _ => false

theorem computedOnlyB_iff : ∀ e, computedOnlyB e = true ↔ ComputedOnly e
  | .computed _ => by simp [computedOnlyB, ComputedOnly]
  | .direct _ => by simp [computedOnlyB, ComputedOnly]
  | .ttu _ _ => by simp [computedOnlyB, ComputedOnly]
  | .union a b => by
      simp [computedOnlyB, ComputedOnly, computedOnlyB_iff a, computedOnlyB_iff b]
  | .inter a b => by
      simp [computedOnlyB, ComputedOnly, computedOnlyB_iff a, computedOnlyB_iff b]
  | .excl a b => by
      simp [computedOnlyB, ComputedOnly, computedOnlyB_iff a, computedOnlyB_iff b]

/-! ## The two quantifier shapes -/

/-- "Every definition at the FIXED key `k`, if any, satisfies `Q`." -/
def lookupAll (S : Schema) (k : String × String) (Q : Expr → Bool) : Bool :=
  match S.lookup k with
  | some e => Q e
  | none => true

theorem lookupAll_iff (S : Schema) (k : String × String) (Q : Expr → Bool) :
    lookupAll S k Q = true ↔ ∀ e, S.lookup k = some e → Q e = true := by
  unfold lookupAll
  cases S.lookup k <;> simp

/-- "Every DERIVED definition satisfies `P`" — the shape of six `W4Fragment` fields, decided
    over `taintedKeys S` (exact: no `NodupKeys` premise; see the module docstring). -/
def derivedDefsAll (S : Schema) (P : String → Expr → Bool) : Bool :=
  (taintedKeys S).all fun k => lookupAll S k (P k.1)

theorem derivedDefsAll_iff (S : Schema) (P : String → Expr → Bool) :
    derivedDefsAll S P = true ↔
      ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → P dt e = true := by
  unfold derivedDefsAll isDerived
  rw [List.all_eq_true]
  refine ⟨fun h dt R e hl hd => ?_, fun h k hk => ?_⟩
  · have hmem : (dt, R) ∈ taintedKeys S := by simpa [List.contains_iff_mem] using hd
    exact (lookupAll_iff S _ _).mp (h (dt, R) hmem) e hl
  · rw [lookupAll_iff]
    intro e hl
    exact h k.1 k.2 e hl (by simpa [List.contains_iff_mem] using hk)

private theorem bool_false_or_iff {b : Bool} {Q : Prop} : (b = false ∨ Q) ↔ (b = true → Q) := by
  cases b <;> simp

/-! ## One Bool per `W4Fragment` field, each with its exact `_iff` -/

def fragComputedOrDirectB (S : Schema) : Bool :=
  derivedDefsAll S fun _ e => computedOrDirectB e

theorem fragComputedOrDirectB_iff (S : Schema) :
    fragComputedOrDirectB S = true ↔
      ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOrDirect e := by
  unfold fragComputedOrDirectB
  rw [derivedDefsAll_iff]
  simp only [computedOrDirectB_iff]

def fragDirectArmsBareB (S : Schema) : Bool :=
  derivedDefsAll S fun _ e => directArmsBareB e

theorem fragDirectArmsBareB_iff (S : Schema) :
    fragDirectArmsBareB S = true ↔
      ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → DirectArmsBare e := by
  unfold fragDirectArmsBareB
  rw [derivedDefsAll_iff]
  simp only [directArmsBareB_iff]

def fragDirectArmsConcreteB (S : Schema) : Bool :=
  derivedDefsAll S fun _ e => (exprDirectsAll e).all fun rs => rs.all fun r => r.2.2 == false

theorem fragDirectArmsConcreteB_iff (S : Schema) :
    fragDirectArmsConcreteB S = true ↔ DirectArmsConcrete S := by
  unfold fragDirectArmsConcreteB DirectArmsConcrete
  rw [derivedDefsAll_iff]
  simp only [List.all_eq_true, beq_iff_eq]

def fragComputedOnlyOperandsB (S : Schema) : Bool :=
  derivedDefsAll S fun dt e =>
    (computedRefs e).all fun r' => !(isDerived S (dt, r')) || lookupAll S (dt, r') computedOnlyB

theorem fragComputedOnlyOperandsB_iff (S : Schema) :
    fragComputedOnlyOperandsB S = true ↔
      ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
        ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
          ∀ e', S.lookup (dt, r') = some e' → ComputedOnly e' := by
  unfold fragComputedOnlyOperandsB
  rw [derivedDefsAll_iff]
  simp only [List.all_eq_true, Bool.or_eq_true, Bool.not_eq_true', lookupAll_iff,
    computedOnlyB_iff, bool_false_or_iff]

def fragNoUnionDirectsB (S : Schema) : Bool :=
  derivedDefsAll S fun _ e => decide (exprDirects e = [])

theorem fragNoUnionDirectsB_iff (S : Schema) :
    fragNoUnionDirectsB S = true ↔
      ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → exprDirects e = [] := by
  unfold fragNoUnionDirectsB
  rw [derivedDefsAll_iff]
  simp only [decide_eq_true_eq]

def fragTwoStrataB (S : Schema) : Bool :=
  derivedDefsAll S fun dt e =>
    (computedRefs e).all fun r' => !(isDerived S (dt, r')) ||
      lookupAll S (dt, r') fun e' => (computedRefs e').all fun r'' => !(isDerived S (dt, r''))

theorem fragTwoStrataB_iff (S : Schema) :
    fragTwoStrataB S = true ↔
      ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
        ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
          ∀ e', S.lookup (dt, r') = some e' →
            ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false := by
  unfold fragTwoStrataB
  rw [derivedDefsAll_iff]
  simp only [List.all_eq_true, Bool.or_eq_true, Bool.not_eq_true', lookupAll_iff,
    bool_false_or_iff]

def fragWsBareB (S : Schema) : Bool :=
  (declaredWildcardShapes S).all fun sh => sh.2 == BARE

theorem fragWsBareB_iff (S : Schema) :
    fragWsBareB S = true ↔ ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE := by
  unfold fragWsBareB
  simp only [List.all_eq_true, beq_iff_eq]

/-! ## The decider -/

/-- The ten `W4Fragment` conjuncts, by FIELD NAME, in declaration order. The names are
    the structure's own field names so a driver can report which field failed. -/
def w4FragmentFieldsB (S : Schema) (T : Store) : List (String × Bool) :=
  [("computedOrDirect", fragComputedOrDirectB S),
   ("directArmsBare", fragDirectArmsBareB S),
   ("directArmsConcrete", fragDirectArmsConcreteB S),
   ("computedOnlyOperands", fragComputedOnlyOperandsB S),
   ("noUnionDirects", fragNoUnionDirectsB S),
   ("twoStrata", fragTwoStrataB S),
   ("wsBare", fragWsBareB S),
   ("bareStar", bareStarStoreB T),
   ("ttuStarFree", ttuStarFreeB S T),
   ("term", htermB S T)]

/-- **Executable `W4Fragment`.** -/
def w4FragmentB (S : Schema) (T : Store) : Bool :=
  (w4FragmentFieldsB S T).all (·.2)

/-- **`W4Fragment` is decided EXACTLY by `w4FragmentB`** — soundness and completeness. -/
theorem w4FragmentB_iff (S : Schema) (T : Store) : w4FragmentB S T = true ↔ W4Fragment S T := by
  unfold w4FragmentB w4FragmentFieldsB
  simp only [List.all_cons, List.all_nil, Bool.and_true, Bool.and_eq_true]
  constructor
  · rintro ⟨h1, h2, h3, h4, h5, h6, h7, h8, h9, h10⟩
    exact ⟨(fragComputedOrDirectB_iff S).mp h1, (fragDirectArmsBareB_iff S).mp h2,
      (fragDirectArmsConcreteB_iff S).mp h3, (fragComputedOnlyOperandsB_iff S).mp h4,
      (fragNoUnionDirectsB_iff S).mp h5, (fragTwoStrataB_iff S).mp h6,
      (fragWsBareB_iff S).mp h7, (bareStarStoreB_iff T).mp h8, (ttuStarFreeB_iff S T).mp h9,
      (htermB_iff S T).mp h10⟩
  · intro h
    exact ⟨(fragComputedOrDirectB_iff S).mpr h.computedOrDirect,
      (fragDirectArmsBareB_iff S).mpr h.directArmsBare,
      (fragDirectArmsConcreteB_iff S).mpr h.directArmsConcrete,
      (fragComputedOnlyOperandsB_iff S).mpr h.computedOnlyOperands,
      (fragNoUnionDirectsB_iff S).mpr h.noUnionDirects,
      (fragTwoStrataB_iff S).mpr h.twoStrata,
      (fragWsBareB_iff S).mpr h.wsBare, (bareStarStoreB_iff T).mpr h.bareStar,
      (ttuStarFreeB_iff S T).mpr h.ttuStarFree, (htermB_iff S T).mpr h.term⟩

instance instDecidableW4Fragment (S : Schema) (T : Store) : Decidable (W4Fragment S T) :=
  decidable_of_iff _ (w4FragmentB_iff S T)

/-- The names of the fields `(S, T)` FAILS, in declaration order — `[]` iff in scope. -/
def w4FragmentFailures (S : Schema) (T : Store) : List String :=
  ((w4FragmentFieldsB S T).filter (fun p => !p.2)).map (·.1)

theorem w4FragmentFailures_nil_iff (S : Schema) (T : Store) :
    w4FragmentFailures S T = [] ↔ W4Fragment S T := by
  rw [← w4FragmentB_iff]
  unfold w4FragmentFailures w4FragmentB
  simp only [List.map_eq_nil_iff, List.filter_eq_nil_iff, Bool.not_eq_true', Bool.not_eq_false,
    List.all_eq_true]

/-! ## Evidence pins (`DW-1`)

The `_iff` lemmas prove the decider CORRECT; these pins are evidence that it is USABLE —
that `decide` actually evaluates it in the kernel at real schemas — and that it
DISCRIMINATES. A decider stuck at `false` fails the two positives; one stuck at `true`, or
one that confuses two fields, fails the ten per-field controls, each of which pins the EXACT
failure list (the named field and nothing else). Every control is `W4Witness.Sx`/`Tx` with
ONE edit. -/

/-! ### Sabotage record (2026-09-23d) — a 14-mutation sweep of THIS module

Each mutation was applied to a copy of this file and elaborated standalone with
`lake env lean`; the declarations named are those with a diagnostic, so a name can appear
for a linter warning (e.g. an unused binder) as well as for an error. Literal results:

    M0  refutes_twoStrata's own claim -> ["noUnionDirects"]   : refutes_twoStrata
    M1  computedOrDirectB `.ttu` -> true                      : computedOrDirectB_iff refutes_computedOrDirect
    M2  directArmsBareB `.direct` -> true                     : directArmsBareB directArmsBareB_iff refutes_directArmsBare
    M3  computedOnlyB `.direct` -> true                       : computedOnlyB_iff refutes_computedOnlyOperands
    M4  directArmsConcrete body -> true                       : fragDirectArmsConcreteB(_iff) refutes_directArmsConcrete
    M5  noUnionDirects body `exprDirectsAll = [] ∨ true`      : fragNoUnionDirectsB_iff refutes_noUnionDirects
    M6  twoStrata inner check -> true                         : fragTwoStrataB(_iff) outside_S6_by_decide refutes_twoStrata
    M7  wsBare body -> true                                   : fragWsBareB(_iff) refutes_wsBare
    M8  bareStar conjunct -> true                             : refutes_bareStar w4FragmentB_iff
    M9  ttuStarFree conjunct -> bareStarStoreB T              : refutes_bareStar refutes_ttuStarFree w4FragmentB_iff
    M10 term conjunct -> true                                 : refutes_term w4FragmentB_iff
    M11 swap the first two conjuncts' deciders                : refutes_computedOrDirect refutes_directArmsBare w4FragmentB_iff
    M12 derivedDefsAll over `S.keys` (untainted defs too)     : derivedDefsAll_iff + both accepts + 10 refutes
    M13 lookupAll `none` -> false                             : lookupAll_iff ONLY

M0 is the attribution control: it flips one pin's own claim and exactly that pin reddens.
Every field mutation reddens BOTH its `_iff` and its own per-field pin, so no field is
guarded by a proof alone. M13 is the one proof-only red, and it is proof-only BY
CONSTRUCTION: `lookupAll` meets `none` only at a key with no definition, and a tainted key
always has one, so no concrete schema can observe that branch. Completeness
(`lookupAll_iff`) is the claim that the branch must be `true`, and it is what went red. -/

namespace FragmentDecideWitness

open W4Witness (Sx Tx)

/-- Positive 1: the minimal witness, hand-proved as `W4Witness.fragment`. -/
theorem accepts_Sx : w4FragmentFailures Sx Tx = [] := by decide

/-- Positive 2: D.3's store (a bare star subject, a BARE wildcard restriction, a derived
    def with a `Direct` arm under `excl`), hand-proved as `P5Witness.w4fragment`. -/
theorem accepts_Sw : w4FragmentFailures LeafWitness.Sw P5Witness.store = [] := by decide

/-- The instance, not just the Bool, closes a `W4Fragment` goal by `decide`. -/
theorem fragment_Sx_by_decide : W4Fragment Sx Tx := by decide

/-- `computedOrDirect`: a TTU leaf inside the derived def. -/
def S1 : Schema :=
  ⟨[(("doc", "a"), .direct [("user", BARE, false)]),
    (("doc", "b"), .direct [("user", BARE, false)]),
    (("doc", "p"), .direct [("doc", BARE, false)]),
    (("doc", "r"), .excl (.ttu "a" "p") (.computed "b"))], []⟩
theorem refutes_computedOrDirect : w4FragmentFailures S1 Tx = ["computedOrDirect"] := by decide

/-- `directArmsBare`: a userset restriction on the derived def's `Direct` arm. -/
def S2 : Schema :=
  ⟨[(("doc", "a"), .direct [("user", BARE, false)]),
    (("doc", "b"), .direct [("user", BARE, false)]),
    (("doc", "r"), .excl (.direct [("group", "member", false)]) (.computed "b"))], []⟩
theorem refutes_directArmsBare : w4FragmentFailures S2 Tx = ["directArmsBare"] := by decide

/-- `directArmsConcrete`: a wildcard-flagged (`[user:*]`) restriction on the derived def. -/
def S3 : Schema :=
  ⟨[(("doc", "a"), .direct [("user", BARE, false)]),
    (("doc", "b"), .direct [("user", BARE, false)]),
    (("doc", "r"), .excl (.direct [("user", BARE, true)]) (.computed "b"))], []⟩
theorem refutes_directArmsConcrete : w4FragmentFailures S3 Tx = ["directArmsConcrete"] := by
  decide

/-- `computedOnlyOperands`: a DERIVED operand `e` that itself carries a `Direct` arm. -/
def S4 : Schema :=
  ⟨[(("doc", "a"), .direct [("user", BARE, false)]),
    (("doc", "b"), .direct [("user", BARE, false)]),
    (("doc", "e"), .excl (.direct [("user", BARE, false)]) (.computed "b")),
    (("doc", "r"), .excl (.computed "e") (.computed "b"))], []⟩
theorem refutes_computedOnlyOperands :
    w4FragmentFailures S4 Tx = ["computedOnlyOperands"] := by decide

/-- `noUnionDirects`: a union-reachable `Direct` arm in the derived def. -/
def S5 : Schema :=
  ⟨[(("doc", "a"), .direct [("user", BARE, false)]),
    (("doc", "b"), .direct [("user", BARE, false)]),
    (("doc", "r"), .union (.direct [("user", BARE, false)]) (.excl (.computed "a") (.computed "b")))],
   []⟩
theorem refutes_noUnionDirects : w4FragmentFailures S5 Tx = ["noUnionDirects"] := by decide

/-- `twoStrata`: three derived strata `c ← d ← r`. -/
def S6 : Schema :=
  ⟨[(("doc", "a"), .direct [("user", BARE, false)]),
    (("doc", "b"), .direct [("user", BARE, false)]),
    (("doc", "c"), .excl (.computed "a") (.computed "b")),
    (("doc", "d"), .excl (.computed "c") (.computed "b")),
    (("doc", "r"), .excl (.computed "d") (.computed "b"))], []⟩
theorem refutes_twoStrata : w4FragmentFailures S6 Tx = ["twoStrata"] := by decide

/-- `wsBare`: a wildcard USERSET restriction (`[group:*#member]`) on an UNTAINTED def — the
    sub-case `W4FRAGMENT_SCOPE` records as the SILENT half of this MIXED field. -/
def S7 : Schema :=
  ⟨[(("doc", "a"), .direct [("user", BARE, false), ("group", "member", true)]),
    (("doc", "b"), .direct [("user", BARE, false)]),
    (("doc", "r"), .excl (.computed "a") (.computed "b"))], []⟩
theorem refutes_wsBare : w4FragmentFailures S7 Tx = ["wsBare"] := by decide

/-- `bareStar`: a stored wildcard OBJECT. -/
def T8 : Store := [⟨⟨"user", "alice", BARE⟩, "a", ⟨"doc", "*"⟩⟩]
theorem refutes_bareStar : w4FragmentFailures Sx T8 = ["bareStar"] := by decide

/-- `ttuStarFree`: a bare star subject stored on a relation an untainted TTU reads as its
    tupleset. -/
def S9 : Schema :=
  ⟨[(("doc", "a"), .direct [("user", BARE, false)]),
    (("doc", "b"), .direct [("user", BARE, false)]),
    (("doc", "p"), .direct [("folder", BARE, false), ("folder", BARE, true)]),
    (("doc", "v"), .ttu "a" "p"),
    (("doc", "r"), .excl (.computed "a") (.computed "b"))], []⟩
def T9 : Store := [⟨⟨"folder", "*", BARE⟩, "p", ⟨"doc", "1"⟩⟩]
theorem refutes_ttuStarFree : w4FragmentFailures S9 T9 = ["ttuStarFree"] := by decide

/-- `term` (its `NoStoreSubjectR` half): a stored userset subject whose predicate is the
    derived relation `r`. -/
def T10 : Store := [⟨⟨"doc", "x", "r"⟩, "a", ⟨"doc", "1"⟩⟩]
theorem refutes_term : w4FragmentFailures Sx T10 = ["term"] := by decide

/-- The instance closes a NEGATIVE goal too. -/
theorem outside_S6_by_decide : ¬ W4Fragment S6 Tx := by decide

end FragmentDecideWitness

end Zanzibar
