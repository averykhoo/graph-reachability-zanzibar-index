import ZanzibarProofs.GraphIndex.ReconcileCorrect
import ZanzibarProofs.GraphIndex.RulesBareStar
import ZanzibarProofs.Spec.Stabilize

/-!
# Schema restriction to the untainted fragment — the `hag` base reduction (ROADMAP W3a, Step A)

`graphRec_reduce_base` (`ReconcileCorrect.lean`) reduced the W3a correspondence blocker `hag`
to a pure W2 base-state fact: for an untainted operand relation `r'`, the graph read
`graphRec σ0 s dt on r'` on the untainted base `σ0` must equal `sem`. `graph_correct_rules`
proves exactly `check = sem`, but only under **whole-schema** `UntaintedSchema S` — too strong
for W3's *mixed* schema (one derived key + untainted operands).

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
    object-wildcard shapes preserved. On the W3a fragment the dropped defs are the derived
    booleans; what remains is the untainted operand cone (`UntaintedSchema`, below). -/
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
`(schemaRewrites S).filterMap …`; `writeDirect`/`admitEdge`/`reach` are schema-blind). The
taint filter in `schemaRewrites` already skips every *dropped* (tainted) def's arms — on BOTH
`S` and `S↾U` — so removing those defs leaves `schemaRewrites` (and therefore the whole rewrite
fan-out) unchanged, needing only `NodupKeys` (`isDerived_restrict`). This is the groundwork for
transferring a `ReachedByRules`/`…Admitted` state from `S` to `S↾U` with identical edges. -/

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
theorem schemaRewrites_restrict {S : Schema} (hNK : NodupKeys S) :
    schemaRewrites (restrictUntainted S) = schemaRewrites S := by
  -- The taint filter in `schemaRewrites` already drops every derived def's arms on BOTH
  -- schemas. On the restricted schema every key is untainted (`isDerived_restrict`), so its
  -- own filter keeps all defs; and `restrictUntainted` dropped exactly the S-tainted defs —
  -- the same set `schemaRewrites S`'s filter removes. So no `hDrop` fact is needed.
  unfold schemaRewrites
  -- LHS filter is a no-op: all restricted keys are untainted.
  rw [List.filter_eq_self.mpr (fun d _ => by rw [isDerived_restrict hNK]; rfl)]
  -- (restrictUntainted S).defs = S.defs.filter (S-untainted); the same predicate the RHS uses.
  rfl

/-- The one-step rewrite is preserved (it reads the schema only via `schemaRewrites`). -/
theorem rewriteStep_restrict {S : Schema} (hNK : NodupKeys S)
    (t : Tuple) : rewriteStep (restrictUntainted S) t = rewriteStep S t := by
  unfold rewriteStep; rw [schemaRewrites_restrict hNK]

/-- **The bounded rewrite closure is preserved at any fixed fuel** — a pure structural
    consequence of `rewriteStep` agreeing (`rewriteClosureAux` reads the schema only through
    `rewriteStep`). NB: the *canonical* closures `rewriteClosure S t` / `rewriteClosure (S↾U) t`
    run at DIFFERENT fuels (`S.keys.length+1` vs the smaller `(S↾U).keys.length+1`); bridging
    that gap (both saturate, so equal membership) is the remaining state-transfer step. -/
theorem rewriteClosureAux_restrict {S : Schema} (hNK : NodupKeys S) :
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
      exact rewriteStep_restrict hNK t
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
theorem rewriteClosure_restrict_subset {S : Schema} (hNK : NodupKeys S)
    {t w : Tuple} (hw : w ∈ rewriteClosure (restrictUntainted S) t) :
    w ∈ rewriteClosure S t := by
  unfold rewriteClosure at hw ⊢
  rw [rewriteClosureAux_restrict hNK] at hw
  exact rewriteClosureAux_mono
    (Nat.succ_le_succ restrictUntainted_keys_length_le) hw

/-! ## The `⊆` half — the `S`-closure embeds in the `S↾U`-closure (via saturation)

The bigger closure adds no new members past the smaller fuel: the `S↾U`-closure is
saturated (closed under one more `rewriteStep S`), so it swallows every `S`-closure layer.
Saturation needs `RewriteRanked (S↾U)`, which we build from `RewriteRanked S` by rank
COMPRESSION — count the `S↾U`-keys ranked below `k` — bounded now by `|S↾U.keys|`. The one
faithful side condition: every rewrite's *match* key is a declared untainted relation
(`RewriteMatchDeclared`), so the compressed rank strictly increases at each arm. -/

/-- A declared untainted key survives the restriction. -/
theorem mem_restrictUntainted_keys {S : Schema} {k : String × String}
    (hk : k ∈ S.keys) (hu : isDerived S k = false) : k ∈ (restrictUntainted S).keys := by
  obtain ⟨p, hp, hpk⟩ := List.mem_map.mp hk
  exact List.mem_map.mpr ⟨p, mem_restrictUntainted_defs.mpr ⟨hp, hpk ▸ hu⟩, hpk⟩

/-- **`RewriteMatchDeclared S`** — every schema rewrite's *match* key `(objectType, matchRel)`
    is a declared, untainted relation. Faithful to the compiler: rewrite arms are compiled
    from operand reads routed through `RewriteFilter`s over DECLARED relations, and in the
    boolean fragment every operand is untainted. This is what confines each rewrite step to
    the untainted cone `S↾U` keeps, so the compressed rank (below) can be bounded by
    `|S↾U.keys|`. -/
def RewriteMatchDeclared (S : Schema) : Prop :=
  ∀ r ∈ schemaRewrites S, (r.objectType, r.matchRel) ∈ S.keys ∧
    isDerived S (r.objectType, r.matchRel) = false

/-- **Strict `countP`-style monotonicity of a filtered length.** On one list `l`, if `p`
    pointwise implies `q` and some `a ∈ l` is counted by `q` but not `p`, the `q`-filter is
    strictly longer. (`p`-filter is a `q`-sublist by monotonicity; equal length would force
    equal lists, contradicting `a`.) -/
theorem length_filter_lt_of_mem {α : Type} {l : List α} {p q : α → Bool}
    (hpq : ∀ x, p x = true → q x = true)
    {a : α} (ha : a ∈ l) (hqa : q a = true) (hpa : p a = false) :
    (l.filter p).length < (l.filter q).length := by
  have hsub : List.Sublist (l.filter p) (l.filter q) := List.monotone_filter_right l hpq
  rcases Nat.lt_or_ge (l.filter p).length (l.filter q).length with h | h
  · exact h
  · exfalso
    have heq : l.filter p = l.filter q := hsub.eq_of_length_le h
    have haq : a ∈ l.filter q := List.mem_filter.mpr ⟨ha, hqa⟩
    rw [← heq] at haq
    have hap : p a = true := (List.mem_filter.mp haq).2
    rw [hpa] at hap; exact Bool.false_ne_true hap

/-- **`RewriteRanked` transfers to the restriction** by rank COMPRESSION. Reuse `S`'s rank
    `rrank`; the compressed rank of `k` counts the `S↾U`-keys ranked strictly below `k` —
    bounded by `|S↾U.keys|` (`length_filter_le`). Each rewrite arm still strictly increases
    it: its match key `a` (declared untainted, `RewriteMatchDeclared` ⇒ `a ∈ S↾U.keys`) is
    counted by the out-key's threshold but not its own (`length_filter_lt_of_mem`). -/
theorem rewriteRanked_restrict {S : Schema} (hNK : NodupKeys S)
    (hMatch : RewriteMatchDeclared S) (hR : RewriteRanked S) :
    RewriteRanked (restrictUntainted S) := by
  obtain ⟨rrank, hinc, _hbound⟩ := hR
  refine ⟨fun k => ((restrictUntainted S).keys.filter
      (fun j => decide (rrank j < rrank k))).length, ?_, ?_⟩
  · intro r hr
    rw [schemaRewrites_restrict hNK] at hr
    have hlt : rrank (r.objectType, r.matchRel) < rrank (r.objectType, r.outRel) := hinc r hr
    obtain ⟨hmemk, hmemu⟩ := hMatch r hr
    have hak : (r.objectType, r.matchRel) ∈ (restrictUntainted S).keys :=
      mem_restrictUntainted_keys hmemk hmemu
    exact length_filter_lt_of_mem
      (fun x hx => decide_eq_true (Nat.lt_trans (of_decide_eq_true hx) hlt))
      hak (decide_eq_true hlt) (by simp)
  · intro k; exact List.length_filter_le _ _

/-- **The `S`-closure embeds in the `S↾U`-closure** — every `S`-closure layer stays inside
    the saturated (`rewriteRanked_restrict`) `S↾U`-closure: layer 0 is the seed, and each
    further `rewriteStep S` (= `rewriteStep (S↾U)`) is swallowed by saturation. This is the
    conditional (`⊆`) half; with `rewriteClosure_restrict_subset` it closes the fuel bridge. -/
theorem rewriteClosure_subset_restrict {S : Schema} (hNK : NodupKeys S)
    (hMatch : RewriteMatchDeclared S) (hR : RewriteRanked S)
    {t w : Tuple} (hw : w ∈ rewriteClosure S t) :
    w ∈ rewriteClosure (restrictUntainted S) t := by
  have hRU : RewriteRanked (restrictUntainted S) := rewriteRanked_restrict hNK hMatch hR
  have hlayer : ∀ (k : Nat) (w' : Tuple), w' ∈ stepN S k [t] →
      w' ∈ rewriteClosure (restrictUntainted S) t := by
    intro k
    induction k with
    | zero =>
      intro w' hw'
      change w' ∈ [t] at hw'
      rw [List.mem_singleton.mp hw']
      exact rewriteClosure_seed (restrictUntainted S) t
    | succ m ih =>
      intro w' hw'
      change w' ∈ (stepN S m [t]).flatMap (rewriteStep S) at hw'
      obtain ⟨v, hv, hvw⟩ := List.mem_flatMap.mp hw'
      have hvw' : w' ∈ rewriteStep (restrictUntainted S) v := by
        rw [rewriteStep_restrict hNK]; exact hvw
      exact rewriteClosure_saturated hRU (ih v hv) hvw'
  obtain ⟨k, _, hmem⟩ := stepN_of_mem_aux S (S.keys.length + 1) [t] hw
  exact hlayer k w hmem

/-- **The fuel bridge, closed** — the two canonical closures have identical membership on the
    W3a fragment (`RewriteMatchDeclared` + `RewriteRanked S`). The `⊆` half is
    saturation of the `S↾U`-closure; the `⊇` half is unconditional fuel monotonicity. Edge
    sets of a rule-routed admitted state are exactly the materialised closure tuples
    (`reachedByRules_edge_sound` + `reachedByRulesAdmitted_edge_complete`), so equal closure
    membership will give equal edges under the state transfer (Step A assembly). -/
theorem rewriteClosure_restrict_mem_iff {S : Schema} (hNK : NodupKeys S)
    (hMatch : RewriteMatchDeclared S) (hR : RewriteRanked S) {t w : Tuple} :
    w ∈ rewriteClosure (restrictUntainted S) t ↔ w ∈ rewriteClosure S t :=
  ⟨rewriteClosure_restrict_subset hNK, rewriteClosure_subset_restrict hNK hMatch hR⟩

/-! ## The state transfer — a canonical admitted `S↾U`-state with agreeing edges

The base `hag` equation reads the graph on an admitted rule-routed state `σ0` over the MIXED
schema `S`, but `graph_correct_rules` (`check = sem`) needs a state built over an UNTAINTED
schema. This section transfers `σ0` to a canonical `ReachedByRulesAdmitted σ' (S↾U) T` whose
edges have identical membership.

The one subtlety flagged by the roadmap: σ' and σ0 fold `writeDirect` over DIFFERENT lists
(`rewriteClosure (S↾U) t` vs `rewriteClosure S t`, which differ by fuel/dups), so they are not
literally equal — and admission (`FoldAdmits`, cycle-rejection) is order-sensitive. The bridge
is that admission depends only on the *final* edge relation being acyclic: `foldAdmits_of_acyclic`
shows every `writeDirect` in a fold admits as long as each materialised edge lands in an acyclic
relation `Ef` that already contains the running edges. Since `σ0.edges` is acyclic (`Inv.acyclic`)
and the fuel bridge makes the two closures materialise the SAME edges, both states' admissions —
and hence their edge sets — coincide. -/

/-- **Admission from acyclicity of the target relation.** Folding `writeDirect` over `us` from
    `σ` admits every write, provided (i) `Ef` is acyclic, (ii) `σ`'s edges already sit inside
    `Ef`, and (iii) every write's materialised edge is in `Ef`. Each step: the edge `a → b`
    is not a self-loop (`(a,a) ∈ Ef` would be a 1-cycle) and has no back-path `b →* a` in the
    running edges (which embed in `Ef`, so `b →* a → b` would be a cycle). The write keeps the
    running edges inside `Ef` (`writeDirect_edges`), so the induction proceeds. Order-insensitive:
    the only input from `us` is its set of materialised edges. -/
theorem foldAdmits_of_acyclic {S' : Schema} {Ef : List (NodeKey × NodeKey)}
    (hacyc : ∀ v, ¬ NReaches Ef v v) :
    ∀ (us : List Tuple) {σ : GraphState}, StructInv S' σ →
      (∀ e ∈ σ.edges, e ∈ Ef) →
      (∀ u ∈ us, (subjNode u.subject, objNode u.object u.relation) ∈ Ef) →
      FoldAdmits σ us := by
  intro us
  induction us with
  | nil => intro σ _ _ _; exact trivial
  | cons u rest ih =>
    intro σ hSI hsub hmat
    have hmatu : (subjNode u.subject, objNode u.object u.relation) ∈ Ef :=
      hmat u List.mem_cons_self
    refine ⟨?_, ?_⟩
    · -- admission of the head write
      have hne : subjNode u.subject ≠ objNode u.object u.relation := fun heq =>
        hacyc _ (heq ▸ NReaches.edge hmatu)
      have hnr : σ.reach (objNode u.object u.relation) (subjNode u.subject) = false := by
        by_contra hc
        rw [Bool.not_eq_false] at hc
        exact hacyc _ (((reach_sound hc).mono_subset hsub).tail hmatu)
      unfold GraphState.admitEdge
      rw [Bool.and_eq_true, bne_iff_ne]
      exact ⟨hne, by simp [hnr]⟩
    · -- the rest of the fold, on the post-write state (edges still inside `Ef`)
      refine ih (structInv_writeDirect hSI u) ?_ (fun u' hu' => hmat u' (List.mem_cons_of_mem _ hu'))
      intro e he
      rw [writeDirect_edges] at he
      split at he
      · rcases List.mem_cons.mp he with rfl | hmem
        · exact hmatu
        · exact hsub e hmem
      · exact hsub e he

/-- **The state transfer.** From an admitted rule-routed state `σ0` over the mixed schema `S`,
    build a canonical admitted state `σ'` over the untainted restriction `S↾U` whose edges have
    identical membership. Both states' edges are exactly the materialised rewrite-closure tuples
    (`reachedByRules_edge_sound` ⊆ / `reachedByRulesAdmitted_edge_complete` ⊇), and the fuel
    bridge (`rewriteClosure_restrict_mem_iff`) makes the two closures agree — so the edge sets
    agree. The admissions transfer via `foldAdmits_of_acyclic` (target `σ0.edges`, acyclic by
    `Inv.acyclic`). Proof by induction on the write path; the fragment side conditions
    (`RewriteMatchDeclared`, `RewriteRanked`) are premises, faithful and discharged in assembly. -/
theorem exists_admitted_restrict {S : Schema} {T : Store} {σ0 : GraphState}
    (h0 : ReachedByRulesAdmitted σ0 S T) :
    NodupKeys S →
    RewriteMatchDeclared S → RewriteRanked S →
    ∃ σ', ReachedByRulesAdmitted σ' (restrictUntainted S) T ∧
      ∀ a b, ((a, b) ∈ σ'.edges ↔ (a, b) ∈ σ0.edges) := by
  induction h0 with
  | empty S =>
    intro _ _ _
    exact ⟨emptyState (restrictUntainted S), ReachedByRulesAdmitted.empty _,
      by intro a b; simp [emptyState]⟩
  | @step σp S T t hprev hadm ih =>
    intro hNK hMatch hR
    obtain ⟨σ'p, h'prev, hedgeIH⟩ := ih hNK hMatch hR
    -- the current (step) admitted state over `S`, and its invariant
    have h0 : ReachedByRulesAdmitted (σp.writeRules S t) S (t :: T) :=
      ReachedByRulesAdmitted.step t hprev hadm
    have hInv0 : Inv S (σp.writeRules S t) :=
      (reachedByRules_inv (reachedByRules_of_admitted h0)).1
    -- σ'p sits inside `Ef := (σp.writeRules S t).edges` and its writes materialise there
    have hSI'p : StructInv (restrictUntainted S) σ'p :=
      (reachedByRules_inv (reachedByRules_of_admitted h'prev)).1.toStruct
    have hsub : ∀ e ∈ σ'p.edges, e ∈ (σp.writeRules S t).edges := by
      rintro ⟨a, b⟩ he
      exact foldl_writeDirect_edges_mono (rewriteClosure S t) (a, b) ((hedgeIH a b).mp he)
    have hmat : ∀ u ∈ rewriteClosure (restrictUntainted S) t,
        (subjNode u.subject, objNode u.object u.relation) ∈ (σp.writeRules S t).edges := by
      intro u hu
      exact reachedByRulesAdmitted_edge_complete h0 t List.mem_cons_self u
        (rewriteClosure_restrict_subset hNK hu)
    -- admission of the restricted closure fold transfers by acyclicity of the target
    have hFA : FoldAdmits σ'p (rewriteClosure (restrictUntainted S) t) :=
      foldAdmits_of_acyclic hInv0.acyclic (rewriteClosure (restrictUntainted S) t) hSI'p hsub hmat
    refine ⟨σ'p.writeRules (restrictUntainted S) t,
      ReachedByRulesAdmitted.step t h'prev hFA, ?_⟩
    -- edge agreement: both edge sets are the materialised closures, which agree (fuel bridge)
    have h' : ReachedByRulesAdmitted (σ'p.writeRules (restrictUntainted S) t)
        (restrictUntainted S) (t :: T) := ReachedByRulesAdmitted.step t h'prev hFA
    intro a b
    constructor
    · intro hab
      obtain ⟨t', ht', w, hw, h1, h2⟩ :=
        reachedByRules_edge_sound (reachedByRules_of_admitted h') a b hab
      have hwS : w ∈ rewriteClosure S t' := rewriteClosure_restrict_subset hNK hw
      have := reachedByRulesAdmitted_edge_complete h0 t' ht' w hwS
      rwa [← h1, ← h2] at this
    · intro hab
      obtain ⟨t', ht', w, hw, h1, h2⟩ :=
        reachedByRules_edge_sound (reachedByRules_of_admitted h0) a b hab
      have hwU : w ∈ rewriteClosure (restrictUntainted S) t' :=
        rewriteClosure_subset_restrict hNK hMatch hR hw
      have := reachedByRulesAdmitted_edge_complete h' t' ht' w hwU
      rwa [← h1, ← h2] at this

/-! ## Rebuild-existence over a sub-store — the R5b from-store admitted rebuild

The `remove` constructor (leg R5b) removes a tuple `t ∈ T` from the store, landing over
`T.erase t`, and needs a build-FROM-store admitted witness over the SMALLER store. It is the
store-restriction dual of `exists_admitted_restrict` (which restricts the SCHEMA): the one new
ingredient — closure-acyclicity of the admission target over the smaller store — is obtained by
INHERITANCE from an already-admitted larger store (a subgraph of an acyclic graph is acyclic, so
`foldAdmits_of_acyclic` discharges every `writeDirect` fold over the sub-store against
`Ef := σ0.edges`). Honestly premised on `ReachedByRulesAdmitted σ0 S T` (from-scratch
admissibility is FALSE over an arbitrary store — the userset 2-cycle store admits no chain). -/

/-- **The from-store admitted-rebuild core.** Given a FIXED acyclic target relation `Ef`
    already containing every materialised closure edge of every tuple of a store `T'`, fold an
    admitted rule-routed chain over `T'`: each write's fold admits by `foldAdmits_of_acyclic`
    (target `Ef`, `σp.edges ⊆ Ef` recovered from `reachedByRules_edge_sound`), and the built
    edges stay inside `Ef`. The store-analog of the write-path induction inside
    `exists_admitted_restrict`, with the acyclic target supplied rather than reconstructed. -/
theorem exists_admitted_ofAcyclicTarget {S : Schema} {Ef : List (NodeKey × NodeKey)}
    (hacyc : ∀ v, ¬ NReaches Ef v v) :
    ∀ T' : Store,
      (∀ t' ∈ T', ∀ u ∈ rewriteClosure S t',
        (subjNode u.subject, objNode u.object u.relation) ∈ Ef) →
      ∃ σ0', ReachedByRulesAdmitted σ0' S T' ∧ (∀ e ∈ σ0'.edges, e ∈ Ef) := by
  intro T'
  induction T' with
  | nil =>
    intro _
    exact ⟨emptyState S, ReachedByRulesAdmitted.empty S,
      by intro e he; simp [emptyState] at he⟩
  | cons t' T'' ih =>
    intro hmatAll
    obtain ⟨σp, hp, hsubp⟩ := ih (fun t'' ht'' u hu =>
      hmatAll t'' (List.mem_cons_of_mem _ ht'') u hu)
    have hSI : StructInv S σp :=
      (reachedByRules_inv (reachedByRules_of_admitted hp)).1.toStruct
    have hmat : ∀ u ∈ rewriteClosure S t',
        (subjNode u.subject, objNode u.object u.relation) ∈ Ef :=
      fun u hu => hmatAll t' List.mem_cons_self u hu
    have hFA : FoldAdmits σp (rewriteClosure S t') :=
      foldAdmits_of_acyclic hacyc (rewriteClosure S t') hSI hsubp hmat
    refine ⟨σp.writeRules S t', ReachedByRulesAdmitted.step t' hp hFA, ?_⟩
    -- every edge of the new state materialises a closure tuple of `t' :: T''`, all in `Ef`
    rintro ⟨a, b⟩ hab
    obtain ⟨t'', ht'', u, hu, h1, h2⟩ :=
      reachedByRules_edge_sound
        (reachedByRules_of_admitted (ReachedByRulesAdmitted.step t' hp hFA)) a b hab
    rw [h1, h2]
    exact hmatAll t'' ht'' u hu

/-- **Rebuild-existence over a SUBSET store.** From an admitted chain over `T`, any store `T'`
    whose tuples all lie in `T` admits its own rule-routed chain, with edges inside `σ0`'s.
    Acyclicity is inherited from `σ0` (`Inv.acyclic`); completeness of the target from
    `reachedByRulesAdmitted_edge_complete`. Route-agnostic (stated over ⊆, not just `erase`). -/
theorem exists_admitted_ofSubset {S : Schema} {T T' : Store} {σ0 : GraphState}
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsub : T' ⊆ T) :
    ∃ σ0', ReachedByRulesAdmitted σ0' S T' ∧ (∀ e ∈ σ0'.edges, e ∈ σ0.edges) := by
  refine exists_admitted_ofAcyclicTarget
    ((reachedByRules_inv (reachedByRules_of_admitted h0)).1.acyclic) T' ?_
  intro t' ht' u hu
  exact reachedByRulesAdmitted_edge_complete h0 t' (hsub ht') u hu

/-- **Rebuild-existence over `T.erase t` — the R5b tool.** The specific instance route (a)'s
    `reachedByW3d2_shadow` remove case consumes: erasing one occurrence yields a subset store
    (`List.erase_subset`), so an admitted rebuild exists over it, with edges ⊆ `σ0`'s. R5b will
    match this rebuild against the actual retraction state via the R4 confluence (`ReadEq`). -/
theorem exists_admitted_erase {S : Schema} {T : Store} {σ0 : GraphState}
    (h0 : ReachedByRulesAdmitted σ0 S T) (t : Tuple) :
    ∃ σ0', ReachedByRulesAdmitted σ0' S (T.erase t) ∧ (∀ e ∈ σ0'.edges, e ∈ σ0.edges) :=
  exists_admitted_ofSubset h0 (List.erase_subset)

/-! ## The base `hag` equation — the operand read equals `sem` on the untainted base

Composing the state transfer with `graph_correct_rules`: on an admitted rule-routed state `σ0`
over the mixed schema `S`, the operand read `graphRec σ0 s dt on r'` (for an untainted operand
`r'`) equals `sem S T ⟨s, r', ⟨dt,on⟩⟩`. The route: `graphRec σ0 = probeNonDerived σ0` (def)
`= probeNonDerived σ'` (edge-membership agreement ⇒ `reach` agreement, state transfer) `= check σ'`
(`S↾U` untainted, so the read routes to the probe) `= sem (S↾U) T q'` (`graph_correct_rules`)
`= sem S T q'` (`semAux_restrict` at fuel `fuelBound S T`, then fuel stability over the untainted
`S↾U` to reach `fuelBound (S↾U) T`).

The base is `ReachedByRulesAdmitted` (the completeness half of `graph_correct_rules` needs the
admitted edge story); the W3a assembly (Step B) supplies the admitted W3a base. Fragment side
conditions carried as premises: `hCO` (every derived def is `ComputedOnly` — the W3a shape),
`RewriteMatchDeclared`, and the W2 conditions on the base. -/

/-- A successful `lookup` names a declared def (reconstruct membership from `find?`). -/
theorem mem_defs_of_lookup {S : Schema} {k : String × String} {e : Expr}
    (hlk : S.lookup k = some e) : (k, e) ∈ S.defs := by
  unfold Schema.lookup at hlk
  obtain ⟨p, hp, hpe⟩ := Option.map_eq_some_iff.mp hlk
  have hpk : p.1 = k := by simpa using List.find?_some hp
  have hpp : p = (k, e) := by obtain ⟨pk, pe⟩ := p; simp only at hpk hpe; subst hpk; subst hpe; rfl
  exact hpp ▸ List.mem_of_find?_eq_some hp

/-- **The base `hag` equation.** The operand read on the admitted mixed-schema base equals `sem`,
    for every untainted operand relation `r'`. This discharges the W3a correspondence blocker
    `hag` once composed with `graphRec_reduce_base` (which reduces the full W3a state's operand
    read to this base read). -/
theorem graphRec_base_eq {S : Schema} {T : Store} {σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S)
    (h0 : ReachedByRulesAdmitted σ0 S T)
    {s : SubjectRef} {dt on : String} (hs : s.name ≠ STAR) (hon : on ≠ STAR) :
    ∀ r', isDerived S (dt, r') = false →
      GraphModel.graphRec σ0 s dt on r' = sem S T ⟨s, r', ⟨dt, on⟩⟩ := by
  intro r' hunt
  -- stored relations are untainted: a derived def is `ComputedOnly` ⇒ no `Direct` arm to match
  have hStoreUnt : ∀ t ∈ T, isDerived S (t.object.type, t.relation) = false := by
    intro t ht
    obtain ⟨e, rs, hlk, hdir, _⟩ := hSV t ht
    by_contra hcon
    rw [Bool.not_eq_false] at hcon
    rw [exprDirects_computedOnly (hCO _ _ _ hlk hcon)] at hdir
    simp at hdir
  -- the untainted restriction and its W2 hypotheses
  have hUT : UntaintedSchema (restrictUntainted S) := untaintedSchema_restrict hNK
  have hNKU : NodupKeys (restrictUntainted S) := restrictUntainted_nodup hNK
  have hWFU : WF (restrictUntainted S) :=
    ⟨fun p hp => hWF.relNames p (restrictUntainted_defs_subset hp)⟩
  have hTTU : TtuTuplesetsDirect (restrictUntainted S) := by
    intro d hd tt htt d' hd' hkey
    exact hTT d (restrictUntainted_defs_subset hd) tt htt d'
      (restrictUntainted_defs_subset hd') hkey
  have hRU : RewriteRanked (restrictUntainted S) := rewriteRanked_restrict hNK hMatch hR
  have hSVU : StoreValidRules (restrictUntainted S) T := by
    intro t ht
    obtain ⟨e, rs, hlk, hdir, hrm⟩ := hSV t ht
    exact ⟨e, rs, by rw [restrictUntainted_lookup hNK (hStoreUnt t ht)]; exact hlk, hdir, hrm⟩
  -- the canonical admitted restricted state with agreeing edges (the state transfer)
  obtain ⟨σ', h', hEdge⟩ := exists_admitted_restrict h0 hNK hMatch hR
  -- edge-membership agreement ⇒ `reach` agreement (both states endpoint-closed)
  have hcl0 := (reachedByRules_inv (reachedByRules_of_admitted h0)).1.edgesClosed
  have hcl' := (reachedByRules_inv (reachedByRules_of_admitted h')).1.edgesClosed
  have hsub01 : ∀ e ∈ σ0.edges, e ∈ σ'.edges := by rintro ⟨a, b⟩ h; exact (hEdge a b).mpr h
  have hsub10 : ∀ e ∈ σ'.edges, e ∈ σ0.edges := by rintro ⟨a, b⟩ h; exact (hEdge a b).mp h
  have hreach : ∀ a b, σ0.reach a b = σ'.reach a b := by
    intro a b
    cases h0r : σ0.reach a b <;> cases h'r : σ'.reach a b <;> try rfl
    · have : NReaches σ0.edges a b := (reach_sound h'r).mono_subset hsub10
      rw [reach_complete hcl0 this] at h0r; exact absurd h0r (by decide)
    · have : NReaches σ'.edges a b := (reach_sound h0r).mono_subset hsub01
      rw [reach_complete hcl' this] at h'r; exact absurd h'r (by decide)
  -- graphRec σ0 = probeNonDerived σ0 q' = probeNonDerived σ' q' (reach agreement)
  have hprobe : GraphModel.probeNonDerived σ0 ⟨s, r', ⟨dt, on⟩⟩
      = GraphModel.probeNonDerived σ' ⟨s, r', ⟨dt, on⟩⟩ := by
    unfold GraphModel.probeNonDerived; simp only [hreach]
  -- probeNonDerived σ' = check σ' (restriction untainted) = sem (S↾U) T q' (graph_correct_rules)
  have hInv' := (reachedByRules_inv (reachedByRules_of_admitted h')).1
  have hcheck : GraphModel.check σ' ⟨s, r', ⟨dt, on⟩⟩
      = GraphModel.probeNonDerived σ' ⟨s, r', ⟨dt, on⟩⟩ :=
    check_eq_probeNonDerived hInv'.schemaEq hUT _
  have hgc : GraphModel.check σ' ⟨s, r', ⟨dt, on⟩⟩ = sem (restrictUntainted S) T ⟨s, r', ⟨dt, on⟩⟩ :=
    graph_correct_rules (restrictUntainted S) T σ' ⟨s, r', ⟨dt, on⟩⟩ hWFU hUT hTTU hNKU hRU hSVU hSF
      hs hon h'
  -- sem (S↾U) T q' = sem S T q' (semAux_restrict at fuelBound S T + fuel stability over S↾U)
  have hDecl : StoreDeclared S T := storeDeclared_of_validRules hSV
  have hfuel_le : fuelBound (restrictUntainted S) T ≤ fuelBound S T := by
    unfold fuelBound
    exact Nat.mul_le_mul restrictUntainted_keys_length_le (le_refl _)
  have hStableU := sem_fuel_stable (restrictUntainted S) T ⟨s, r', ⟨dt, on⟩⟩
    (stratifiable_untainted hUT) (storeDeclared_of_validRules hSVU) (fuelBound S T) hfuel_le
  have hsemR := semAux_restrict (S := S) hNK hDecl s ⟨s, r', ⟨dt, on⟩⟩ (fuelBound S T) dt r' hunt on
  have hsembridge : sem (restrictUntainted S) T ⟨s, r', ⟨dt, on⟩⟩ = sem S T ⟨s, r', ⟨dt, on⟩⟩ := by
    have e1 : sem (restrictUntainted S) T ⟨s, r', ⟨dt, on⟩⟩
        = semAux (restrictUntainted S) s T ⟨s, r', ⟨dt, on⟩⟩ (fuelBound S T) dt on r' := hStableU.symm
    have e3 : semAux S s T ⟨s, r', ⟨dt, on⟩⟩ (fuelBound S T) dt on r' = sem S T ⟨s, r', ⟨dt, on⟩⟩ :=
      rfl
    exact e1.trans (hsemR.symm.trans e3)
  -- assemble the chain
  show GraphModel.graphRec σ0 s dt on r' = sem S T ⟨s, r', ⟨dt, on⟩⟩
  calc GraphModel.graphRec σ0 s dt on r'
      = GraphModel.probeNonDerived σ0 ⟨s, r', ⟨dt, on⟩⟩ := rfl
    _ = GraphModel.probeNonDerived σ' ⟨s, r', ⟨dt, on⟩⟩ := hprobe
    _ = GraphModel.check σ' ⟨s, r', ⟨dt, on⟩⟩ := hcheck.symm
    _ = sem (restrictUntainted S) T ⟨s, r', ⟨dt, on⟩⟩ := hgc
    _ = sem S T ⟨s, r', ⟨dt, on⟩⟩ := hsembridge

/-! ## The STAR-RELAXED base `hag` equation (W3c read half, step 1)

`graphRec_base_eq` over `BareStarStore` instead of `StarFreeStore`: bare `T:*` grants in
the base store, and the query subject widened to star-BARE subjects — the instance the
W3c `coveredFn`/`stars ↔ sem` correspondence consumes. Same schema-restriction route; the
untainted correspondence consumed as a black box is now `graph_correct_rulesBS`
(`RulesBareStar.lean`), whose extra fragment condition `TtuStarFree` transfers to `S↾U`
because the restriction preserves `schemaRewrites`. -/

/-- `TtuStarFree` transfers to the untainted restriction (`schemaRewrites` preserved). -/
theorem ttuStarFree_restrict {S : Schema} {T : Store} (hNK : NodupKeys S)
    (hTS : TtuStarFree S T) : TtuStarFree (restrictUntainted S) T := by
  intro t ht hstar a ha tr hk
  rw [schemaRewrites_restrict hNK] at ha
  exact hTS t ht hstar a ha tr hk

/-- **The star-relaxed base `hag` equation.** The operand read on the admitted
    mixed-schema base over a `BareStarStore` + `TtuStarFree` store equals `sem`, for every
    untainted operand relation `r'` and every subject that is concrete or star-bare —
    including the STAR-subject reads `coveredFn` performs. Mirror of `graphRec_base_eq`
    with `graph_correct_rulesBS` as the untainted black box. -/
theorem graphRec_base_eq_bs {S : Schema} {T : Store} {σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S)
    (h0 : ReachedByRulesAdmitted σ0 S T)
    {s : SubjectRef} {dt on : String}
    (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    ∀ r', isDerived S (dt, r') = false →
      GraphModel.graphRec σ0 s dt on r' = sem S T ⟨s, r', ⟨dt, on⟩⟩ := by
  intro r' hunt
  -- stored relations are untainted: a derived def is `ComputedOnly` ⇒ no `Direct` arm to match
  have hStoreUnt : ∀ t ∈ T, isDerived S (t.object.type, t.relation) = false := by
    intro t ht
    obtain ⟨e, rs, hlk, hdir, _⟩ := hSV t ht
    by_contra hcon
    rw [Bool.not_eq_false] at hcon
    rw [exprDirects_computedOnly (hCO _ _ _ hlk hcon)] at hdir
    simp at hdir
  -- the untainted restriction and its hypotheses
  have hUT : UntaintedSchema (restrictUntainted S) := untaintedSchema_restrict hNK
  have hNKU : NodupKeys (restrictUntainted S) := restrictUntainted_nodup hNK
  have hWFU : WF (restrictUntainted S) :=
    ⟨fun p hp => hWF.relNames p (restrictUntainted_defs_subset hp)⟩
  have hTTU : TtuTuplesetsDirect (restrictUntainted S) := by
    intro d hd tt htt d' hd' hkey
    exact hTT d (restrictUntainted_defs_subset hd) tt htt d'
      (restrictUntainted_defs_subset hd') hkey
  have hRU : RewriteRanked (restrictUntainted S) := rewriteRanked_restrict hNK hMatch hR
  have hSVU : StoreValidRules (restrictUntainted S) T := by
    intro t ht
    obtain ⟨e, rs, hlk, hdir, hrm⟩ := hSV t ht
    exact ⟨e, rs, by rw [restrictUntainted_lookup hNK (hStoreUnt t ht)]; exact hlk, hdir, hrm⟩
  have hTSU : TtuStarFree (restrictUntainted S) T := ttuStarFree_restrict hNK hTS
  -- the canonical admitted restricted state with agreeing edges (the state transfer)
  obtain ⟨σ', h', hEdge⟩ := exists_admitted_restrict h0 hNK hMatch hR
  -- edge-membership agreement ⇒ `reach` agreement (both states endpoint-closed)
  have hcl0 := (reachedByRules_inv (reachedByRules_of_admitted h0)).1.edgesClosed
  have hcl' := (reachedByRules_inv (reachedByRules_of_admitted h')).1.edgesClosed
  have hsub01 : ∀ e ∈ σ0.edges, e ∈ σ'.edges := by rintro ⟨a, b⟩ h; exact (hEdge a b).mpr h
  have hsub10 : ∀ e ∈ σ'.edges, e ∈ σ0.edges := by rintro ⟨a, b⟩ h; exact (hEdge a b).mp h
  have hreach : ∀ a b, σ0.reach a b = σ'.reach a b := by
    intro a b
    cases h0r : σ0.reach a b <;> cases h'r : σ'.reach a b <;> try rfl
    · have : NReaches σ0.edges a b := (reach_sound h'r).mono_subset hsub10
      rw [reach_complete hcl0 this] at h0r; exact absurd h0r (by decide)
    · have : NReaches σ'.edges a b := (reach_sound h0r).mono_subset hsub01
      rw [reach_complete hcl' this] at h'r; exact absurd h'r (by decide)
  -- graphRec σ0 = probeNonDerived σ0 q' = probeNonDerived σ' q' (reach agreement)
  have hprobe : GraphModel.probeNonDerived σ0 ⟨s, r', ⟨dt, on⟩⟩
      = GraphModel.probeNonDerived σ' ⟨s, r', ⟨dt, on⟩⟩ := by
    unfold GraphModel.probeNonDerived; simp only [hreach]
  -- probeNonDerived σ' = check σ' = sem (S↾U) T q' (graph_correct_rulesBS)
  have hInv' := (reachedByRules_inv (reachedByRules_of_admitted h')).1
  have hcheck : GraphModel.check σ' ⟨s, r', ⟨dt, on⟩⟩
      = GraphModel.probeNonDerived σ' ⟨s, r', ⟨dt, on⟩⟩ :=
    check_eq_probeNonDerived hInv'.schemaEq hUT _
  have hgc : GraphModel.check σ' ⟨s, r', ⟨dt, on⟩⟩ = sem (restrictUntainted S) T ⟨s, r', ⟨dt, on⟩⟩ :=
    graph_correct_rulesBS (restrictUntainted S) T σ' ⟨s, r', ⟨dt, on⟩⟩ hWFU hUT hTTU hNKU hRU
      hSVU hBS hTSU hs hon h'
  -- sem (S↾U) T q' = sem S T q' (semAux_restrict at fuelBound S T + fuel stability over S↾U)
  have hDecl : StoreDeclared S T := storeDeclared_of_validRules hSV
  have hfuel_le : fuelBound (restrictUntainted S) T ≤ fuelBound S T := by
    unfold fuelBound
    exact Nat.mul_le_mul restrictUntainted_keys_length_le (le_refl _)
  have hStableU := sem_fuel_stable (restrictUntainted S) T ⟨s, r', ⟨dt, on⟩⟩
    (stratifiable_untainted hUT) (storeDeclared_of_validRules hSVU) (fuelBound S T) hfuel_le
  have hsemR := semAux_restrict (S := S) hNK hDecl s ⟨s, r', ⟨dt, on⟩⟩ (fuelBound S T) dt r' hunt on
  have hsembridge : sem (restrictUntainted S) T ⟨s, r', ⟨dt, on⟩⟩ = sem S T ⟨s, r', ⟨dt, on⟩⟩ := by
    have e1 : sem (restrictUntainted S) T ⟨s, r', ⟨dt, on⟩⟩
        = semAux (restrictUntainted S) s T ⟨s, r', ⟨dt, on⟩⟩ (fuelBound S T) dt on r' := hStableU.symm
    have e3 : semAux S s T ⟨s, r', ⟨dt, on⟩⟩ (fuelBound S T) dt on r' = sem S T ⟨s, r', ⟨dt, on⟩⟩ :=
      rfl
    exact e1.trans (hsemR.symm.trans e3)
  -- assemble the chain
  show GraphModel.graphRec σ0 s dt on r' = sem S T ⟨s, r', ⟨dt, on⟩⟩
  calc GraphModel.graphRec σ0 s dt on r'
      = GraphModel.probeNonDerived σ0 ⟨s, r', ⟨dt, on⟩⟩ := rfl
    _ = GraphModel.probeNonDerived σ' ⟨s, r', ⟨dt, on⟩⟩ := hprobe
    _ = GraphModel.check σ' ⟨s, r', ⟨dt, on⟩⟩ := hcheck.symm
    _ = sem (restrictUntainted S) T ⟨s, r', ⟨dt, on⟩⟩ := hgc
    _ = sem S T ⟨s, r', ⟨dt, on⟩⟩ := hsembridge

end Zanzibar
