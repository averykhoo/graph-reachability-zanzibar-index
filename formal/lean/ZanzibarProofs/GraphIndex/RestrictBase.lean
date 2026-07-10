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

/-! ## The rewrite fan-out is preserved — the state-transfer groundwork

The graph write path reads the schema only through `schemaRewrites` (`rewriteStep` =
`(schemaRewrites S).filterMap …`; `writeDirect`/`admitEdge`/`reach` are schema-blind). On the
W3a fragment every *dropped* (tainted) def is `RootBoolean`, hence emits no rewrite arms
(`exprArms_rootBoolean`), so removing it leaves `schemaRewrites` — and therefore the whole
rewrite fan-out — unchanged. This is the groundwork for transferring a `ReachedByRules`/
`…Admitted` state from `S` to `S↾U` with identical edges. -/

/-- Flat-mapping over a filtered list drops nothing when the removed elements map to `[]`. -/
theorem filter_flatMap_eq {α β : Type} (p : α → Bool) (f : α → List β) :
    ∀ (l : List α), (∀ x ∈ l, p x = false → f x = []) →
      (l.filter p).flatMap f = l.flatMap f := by
  intro l
  induction l with
  | nil => intro _; rfl
  | cons a t ih =>
    intro h
    have iht := ih (fun x hx => h x (List.mem_cons_of_mem _ hx))
    rw [List.filter_cons]
    by_cases hp : p a
    · rw [if_pos hp, List.flatMap_cons, List.flatMap_cons, iht]
    · have hpf : p a = false := by simpa using hp
      rw [if_neg hp, iht, List.flatMap_cons, h a List.mem_cons_self hpf, List.nil_append]

/-- **`schemaRewrites` is preserved by the restriction** — given the W3a fragment fact that every
    tainted (dropped) def emits no rewrite arms. The relations of `schemaRewrites S` are all
    untainted (an arm's `outRel` is its def's own relation, and tainted defs emit none), so the
    rewrite fan-out lives entirely in the untainted cone that `S↾U` keeps. -/
theorem schemaRewrites_restrict {S : Schema}
    (hDrop : ∀ d ∈ S.defs, isDerived S d.1 = true → exprArms d.1.1 d.1.2 d.2 = []) :
    schemaRewrites (restrictUntainted S) = schemaRewrites S := by
  unfold schemaRewrites restrictUntainted
  refine filter_flatMap_eq _ _ S.defs (fun d hd hpf => ?_)
  refine hDrop d hd ?_
  unfold isDerived
  simpa using hpf

/-- The one-step rewrite is preserved (it reads the schema only via `schemaRewrites`). -/
theorem rewriteStep_restrict {S : Schema}
    (hDrop : ∀ d ∈ S.defs, isDerived S d.1 = true → exprArms d.1.1 d.1.2 d.2 = [])
    (t : Tuple) : rewriteStep (restrictUntainted S) t = rewriteStep S t := by
  unfold rewriteStep; rw [schemaRewrites_restrict hDrop]

/-- **The bounded rewrite closure is preserved at any fixed fuel** — a pure structural
    consequence of `rewriteStep` agreeing (`rewriteClosureAux` reads the schema only through
    `rewriteStep`). NB: the *canonical* closures `rewriteClosure S t` / `rewriteClosure (S↾U) t`
    run at DIFFERENT fuels (`S.keys.length+1` vs the smaller `(S↾U).keys.length+1`); bridging
    that gap (both saturate, so equal membership) is the remaining state-transfer step. -/
theorem rewriteClosureAux_restrict {S : Schema}
    (hDrop : ∀ d ∈ S.defs, isDerived S d.1 = true → exprArms d.1.1 d.1.2 d.2 = []) :
    ∀ (n : Nat) (cur : List Tuple),
      rewriteClosureAux (restrictUntainted S) n cur = rewriteClosureAux S n cur := by
  intro n
  induction n with
  | zero => intro cur; rfl
  | succ m ih =>
    intro cur
    rw [rewriteClosureAux, rewriteClosureAux]
    have hstep : cur.flatMap (rewriteStep (restrictUntainted S)) = cur.flatMap (rewriteStep S) := by
      refine List.flatMap_congr (fun t _ => ?_)
      exact rewriteStep_restrict hDrop t
    rw [hstep, ih]

/-! ## The fuel bridge — closure membership across the fuel gap

The canonical closures run at DIFFERENT fuels: `rewriteClosure S t` at `|S.keys|+1`,
`rewriteClosure (S↾U) t` at the smaller `|S↾U.keys|+1`. Via `rewriteClosureAux_restrict`,
`rewriteClosure (S↾U) t = rewriteClosureAux S (|S↾U.keys|+1) [t]`, so the two canonical
closures are the SAME `S`-closure recurrence at two fuels. The gap direction that is
*unconditional* — the smaller closure embeds in the bigger one — is landed here (fuel
monotonicity + the key-count bound). The reverse embedding (the bigger closure adds no new
members past the smaller fuel) needs saturation of the smaller closure and is deferred to
the `RewriteRanked (S↾U)` step. -/

/-- **Fuel monotonicity of the bounded rewrite closure.** More fuel never drops a member:
    a closure member sits at some layer `k ≤ n` (`stepN_of_mem_aux`), and `k ≤ m` re-embeds
    it (`mem_aux_of_stepN`). Reads only the layer algebra of `RulesSaturate`. -/
theorem rewriteClosureAux_mono {S : Schema} {n m : Nat} (hnm : n ≤ m) {cur : List Tuple}
    {w : Tuple} (hw : w ∈ rewriteClosureAux S n cur) : w ∈ rewriteClosureAux S m cur := by
  obtain ⟨k, hk, hmem⟩ := stepN_of_mem_aux S n cur hw
  exact mem_aux_of_stepN S m k cur (Nat.le_trans hk hnm) hmem

/-- The restricted schema has no more keys than the original (its defs are a filtered
    sublist; `map` preserves length). -/
theorem restrictUntainted_keys_length_le {S : Schema} :
    (restrictUntainted S).keys.length ≤ S.keys.length := by
  unfold Schema.keys restrictUntainted
  rw [List.length_map, List.length_map]
  exact List.length_filter_le _ _

/-- **The `S↾U`-closure embeds in the `S`-closure (the unconditional gap direction).** Both
    are the same `S`-closure recurrence (`rewriteClosureAux_restrict`); the restricted one
    runs at the smaller fuel `|S↾U.keys|+1 ≤ |S.keys|+1`, so fuel monotonicity re-embeds it.
    This is the `⊇` half of the fuel bridge (`sem`-completeness side is unaffected). -/
theorem rewriteClosure_restrict_subset {S : Schema}
    (hDrop : ∀ d ∈ S.defs, isDerived S d.1 = true → exprArms d.1.1 d.1.2 d.2 = [])
    {t w : Tuple} (hw : w ∈ rewriteClosure (restrictUntainted S) t) :
    w ∈ rewriteClosure S t := by
  unfold rewriteClosure at hw ⊢
  rw [rewriteClosureAux_restrict hDrop] at hw
  exact rewriteClosureAux_mono
    (Nat.succ_le_succ restrictUntainted_keys_length_le) hw

end Zanzibar
