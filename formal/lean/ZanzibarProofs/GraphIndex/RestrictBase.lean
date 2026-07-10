import ZanzibarProofs.GraphIndex.RulesComplete
import ZanzibarProofs.Spec.Stabilize

/-!
# Schema restriction to the untainted fragment — the `hag` base reduction (ROADMAP W3a, Step A)

`graphRec_reduce_base` (`ReconcileCorrect.lean`) reduced the W3a correspondence blocker `hag`
to a pure W2 base-state fact: for an untainted operand relation `r'`, the graph read
`graphRec σ0 s dt on r'` on the untainted base `σ0` must equal `sem`. `graph_correct_rules`
proves exactly `check = sem`, but only under **whole-schema** `UntaintedSchema S` — too strong
for W3's *mixed* schema (one `RootBoolean` derived key + untainted operands).

This file builds the **schema-restriction** route (HANDOFF Step A, recommended): restrict `S` to
`S↾U := restrictUntainted S` (drop every tainted-key def), which IS untainted, then transfer
`sem` between `S` and `S↾U` on untainted keys so `graph_correct_rules` applies to `S↾U` as a
black box.

This increment lands the schema-combinatorial foundation + the **semantic heart**
`semAux_restrict`: on any untainted key, `sem` over `S` and over `S↾U` coincide (untaintedness
is hereditary — the taint fixpoint confines an untainted def's references to untainted keys, so
the evaluation of an untainted relation never consults a dropped def). Attack-first confirmed
(machine-checked `#eval` on a mixed `admin but not suspended` schema, then deleted): taint
isolates exactly the derived key, `schemaRewrites` is preserved, and `semAux` agrees on every
operand relation.
-/

namespace Zanzibar

/-! ## The restriction and its schema-combinatorial facts -/

/-- **`restrictUntainted S`** — `S` with every *tainted* (derived) key's definition removed,
    object-wildcard shapes preserved. On the W3a fragment the dropped defs are the `RootBoolean`
    derived booleans; what remains is the untainted operand cone (`UntaintedSchema`, below). -/
def restrictUntainted (S : Schema) : Schema :=
  { defs := S.defs.filter (fun p => !(taintedKeys S).contains p.1),
    objectWildcards := S.objectWildcards }

/-- Membership in the restricted defs: a kept def is an original def whose key is untainted. -/
theorem mem_restrictUntainted_defs {S : Schema} {p : (String × String) × Expr} :
    p ∈ (restrictUntainted S).defs ↔ p ∈ S.defs ∧ isDerived S p.1 = false := by
  unfold restrictUntainted isDerived
  simp only [List.mem_filter, Bool.not_eq_true']

/-- The restricted defs are a subset of the originals. -/
theorem restrictUntainted_defs_subset {S : Schema} {p : (String × String) × Expr}
    (hp : p ∈ (restrictUntainted S).defs) : p ∈ S.defs :=
  (mem_restrictUntainted_defs.mp hp).1

/-- Restricted keys are a subset of the original keys. -/
theorem restrictUntainted_keys_subset {S : Schema} {k : String × String}
    (hk : k ∈ (restrictUntainted S).keys) : k ∈ S.keys := by
  unfold Schema.keys at hk ⊢
  obtain ⟨p, hp, hpk⟩ := List.mem_map.mp hk
  exact List.mem_map.mpr ⟨p, restrictUntainted_defs_subset hp, hpk⟩

/-- Key-uniqueness is inherited: the restricted key list is a sublist of the original. -/
theorem restrictUntainted_nodup {S : Schema} (hNK : NodupKeys S) :
    NodupKeys (restrictUntainted S) := by
  unfold NodupKeys at hNK ⊢
  exact List.Nodup.sublist (List.Sublist.map _ List.filter_sublist) hNK

/-- **The restricted schema is untainted.** A kept def has an untainted key, so its expression
    is boolean-free (an untainted declared key is not base-tainted — `untainted_closed` — and
    under `NodupKeys` its `baseTaint` reads exactly this def's `containsBool`). -/
theorem untaintedSchema_restrict {S : Schema} (hNK : NodupKeys S) :
    UntaintedSchema (restrictUntainted S) := by
  intro p hp
  obtain ⟨hpS, hpu⟩ := mem_restrictUntainted_defs.mp hp
  have hkey : p.1 ∈ S.keys := List.mem_map.mpr ⟨p, hpS, rfl⟩
  have hpu' : p.1 ∉ taintedKeys S := by
    unfold isDerived at hpu
    rw [List.contains_eq_mem] at hpu
    exact of_decide_eq_false hpu
  have hbt := (untainted_closed S hkey hpu').1
  -- baseTaint reads this def's containsBool (NodupKeys ⇒ lookup p.1 = some p.2)
  unfold baseTaint at hbt
  rw [lookup_of_mem hNK hpS] at hbt
  exact hbt

/-- No key is derived in the restricted schema (it is untainted). -/
theorem isDerived_restrict {S : Schema} (hNK : NodupKeys S) (k : String × String) :
    isDerived (restrictUntainted S) k = false :=
  isDerived_untainted (untaintedSchema_restrict hNK) k

/-! ## Lookup agreement on untainted keys -/

/-- **`lookup` agrees on untainted keys.** For a key `k` that is not derived, the restricted
    schema returns the same definition as `S`: if `k` is declared, its (unique, `NodupKeys`)
    def is kept; if undeclared, both return `none`. -/
theorem restrictUntainted_lookup {S : Schema} (hNK : NodupKeys S) {k : String × String}
    (hu : isDerived S k = false) :
    (restrictUntainted S).lookup k = S.lookup k := by
  by_cases hmem : k ∈ S.keys
  · obtain ⟨e, he⟩ := lookup_some_of_mem S hmem
    -- the declaring def, kept in the restriction
    have hfind : S.defs.find? (fun p => p.1 = k) = some ((S.defs.find? (fun p => p.1 = k)).get
        (by rw [Option.isSome_iff_ne_none]; intro hn; rw [Schema.lookup, hn] at he; simp at he)) :=
      (Option.some_get _).symm
    obtain ⟨p, hp⟩ : ∃ p, S.defs.find? (fun p => p.1 = k) = some p := by
      cases hf : S.defs.find? (fun p => p.1 = k) with
      | none => rw [Schema.lookup, hf] at he; simp at he
      | some p => exact ⟨p, rfl⟩
    have hpmem : p ∈ S.defs := List.mem_of_find?_eq_some hp
    have hpk : p.1 = k := by simpa using List.find?_some hp
    have hpe : p.2 = e := by
      have : S.lookup k = some p.2 := by rw [Schema.lookup, hp]; rfl
      rw [he] at this; exact (Option.some.injEq .. ▸ this).symm
    have hpkept : p ∈ (restrictUntainted S).defs :=
      mem_restrictUntainted_defs.mpr ⟨hpmem, hpk ▸ hu⟩
    rw [he, ← hpe, ← hpk]
    exact lookup_of_mem (restrictUntainted_nodup hNK) hpkept
  · rw [lookup_eq_none S hmem, lookup_eq_none (restrictUntainted S)
      (fun hk => hmem (restrictUntainted_keys_subset hk))]

/-! ## The semantic heart — `sem` transfer on untainted keys

`semAux S ... = semAux (S↾U) ...` at every untainted key. By fuel induction: at an untainted
key the two schemas' definitions coincide (`restrictUntainted_lookup`); `evalE` then consults
`rec` only at that def's `exprRefs`, all untainted by heredity (`untainted_closed`), where the
IH supplies agreement — so `evalE_congr` closes the step. Needs `StoreDeclared S T` (the
admission-validity precondition `evalE_congr` requires for the `ttu` parent consultations). -/

/-- **`sem` transfer on untainted keys.** For every untainted key `(t, r)` (`isDerived S = false`)
    and every name `m`, the fuel-`f` `sem` reads over `S` and over `S↾U` coincide. Untaintedness
    is hereditary, so evaluating an untainted relation never touches a dropped derived def. This
    is the fact that lets `graph_correct_rules` (proved over `UntaintedSchema S↾U`) discharge the
    mixed-schema `hag`. -/
theorem semAux_restrict {S : Schema} {T : Store} (hNK : NodupKeys S) (hDecl : StoreDeclared S T)
    (sub : SubjectRef) (q : Query) :
    ∀ (f : Nat) (t r : String), isDerived S (t, r) = false →
      ∀ m, semAux S sub T q f t m r = semAux (restrictUntainted S) sub T q f t m r := by
  intro f
  induction f with
  | zero => intro t r _ m; rfl
  | succ f ih =>
    intro t r hu m
    show step S sub T q (semAux S sub T q f) t m r
       = step (restrictUntainted S) sub T q (semAux (restrictUntainted S) sub T q f) t m r
    unfold step
    rw [restrictUntainted_lookup hNK hu]
    cases hlk : S.lookup (t, r) with
    | none => rfl
    | some e =>
      -- the two recs (semAux S f / semAux (S↾U) f) agree on every consulted operand key
      refine evalE_congr S T q hDecl sub t m r e (fun t' m' r' hk' _ => ?_)
      -- (t', r') is a reference of the untainted key (t, r), hence untainted (heredity)
      have hkdecl : (t, r) ∈ S.keys := by
        unfold Schema.lookup at hlk
        obtain ⟨p, hp, hpe⟩ := Option.map_eq_some_iff.mp hlk
        have hpk : p.1 = (t, r) := by simpa using List.find?_some hp
        exact hpk ▸ List.mem_map.mpr ⟨p, List.mem_of_find?_eq_some hp, rfl⟩
      have hu' : (t, r) ∉ taintedKeys S := by
        unfold isDerived at hu; rw [List.contains_eq_mem] at hu; exact of_decide_eq_false hu
      have href : (t', r') ∈ refsOf S (t, r) := by unfold refsOf; rw [hlk]; exact hk'
      have hb : (t', r') ∉ taintedKeys S := (untainted_closed S hkdecl hu').2 (t', r') href
      have hud : isDerived S (t', r') = false := by
        unfold isDerived; rw [List.contains_eq_mem]; exact decide_eq_false hb
      exact ih t' r' hud m'

end Zanzibar
