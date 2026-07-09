import ZanzibarProofs.Spec.Semantics
import ZanzibarProofs.Spec.Stratify
import ZanzibarProofs.Spec.Confine
import Mathlib.Data.Finset.Card
import Mathlib.Combinatorics.Pigeonhole
import Mathlib.Logic.Function.Iterate

/-!
# T0 — well-definedness of the spec

`SEMANTICS.md` §8, rows T0a/T0b.

- **T0a** (`sem_fuel_stable`): the fuel-bounded evaluator is stable above
  `fuelBound`. This file now PROVES it from a single step lemma
  (`semAux_fuel_stable_step`, the pigeonhole argument) — the reduction is a clean
  induction, so only the pigeonhole core remains `sorry`.
- **T0b** (`stratify_none_iff_cycle`, `stratify_topological`): `stratify` computes a
  topological layering exactly when there is no derived-dependency cycle.

Design note (adopting a Gemini review suggestion, corrected): isolating the
graph-theory / pigeonhole cores as their own lemmas keeps the `sem`-evaluation
reduction provable now and the hard combinatorics separately dischargeable.
-/

namespace Zanzibar

/-- Transitive reachability along a finite edge list (nonempty paths). -/
inductive Reaches (edges : List (Key × Key)) : Key → Key → Prop
  | step {a b} : (a, b) ∈ edges → Reaches edges a b
  | trans {a b c} : Reaches edges a b → Reaches edges b c → Reaches edges a c

/-- A derived-dependency cycle exists. -/
def HasDerivedCycle (S : Schema) : Prop := ∃ k, Reaches (depEdges S) k k

/-! ### T0a — fuel stability -/

/-- **The stabilization core.** At or above `fuelBound`, one more unit of fuel does
    not change the answer. The convergence argument: on a `StoreDeclared` store every
    `rec`-consultation is confined to `exprRefs × relevantNames` (`Spec/Confine.lean`),
    so the untainted (boolean-free) fragment is a monotone iteration on a finite atom
    space and stabilizes by its size, and each Kahn stratum of tainted keys stabilizes
    one fuel step after its (strictly lower) inputs; the total fits under the
    multiplicative `fuelBound`.

    ⚠ **The `hDecl` hypothesis is NOT optional** — without it the statement is FALSE
    (machine-checked refutation: `Spec/Counterexample.lean`): an admission-invalid
    tupleset tuple lets `ttuLeaf` consult a key `depEdges` never sees, closing an
    exclusion cycle that stratification misses, and `semAux` oscillates forever.
    `hDecl` holds for every store the composed system can hold (`SEMANTICS.md` §8
    "write-valid tuples"; the Python admission gate enforces it). -/
theorem semAux_fuel_stable_step (S : Schema) (T : Store) (q : Query)
    (_hStrat : Stratifiable S) (_hDecl : StoreDeclared S T) :
    ∀ f, fuelBound S T ≤ f →
      semAux S q.subject T q f q.object.type q.object.name q.relation
        = semAux S q.subject T q (f + 1) q.object.type q.object.name q.relation := by
  sorry

/-- **T0a.** `sem` is well-defined: fuel above the bound does not change the answer
    (stratifiable schema, admission-valid store — see `semAux_fuel_stable_step` for
    why `hDecl` is required). PROVED from `semAux_fuel_stable_step` by induction from
    the bound. -/
theorem sem_fuel_stable (S : Schema) (T : Store) (q : Query)
    (hStrat : Stratifiable S) (hDecl : StoreDeclared S T) :
    ∀ f, fuelBound S T ≤ f →
      semAux S q.subject T q f q.object.type q.object.name q.relation = sem S T q := by
  intro f hf
  induction f, hf using Nat.le_induction with
  | base => rfl
  | succ n hn ih =>
      rw [← semAux_fuel_stable_step S T q hStrat hDecl n hn]; exact ih

/-! ### T0b — Kahn correctness helper lemmas -/

/-- Membership in `readyNodes`: `n` is ready iff it's remaining and every out-edge
    from `n` leaves the remaining set. -/
theorem mem_readyNodes_iff (R : List Key) (edges : List (Key × Key)) (n : Key) :
    n ∈ readyNodes R edges ↔ n ∈ R ∧ ∀ m, (n, m) ∈ edges → m ∉ R := by
  unfold readyNodes
  simp only [List.mem_filter, decide_eq_true_eq, Bool.not_eq_true, List.any_eq_false,
    Bool.and_eq_true, beq_iff_eq, List.contains_eq_mem]
  constructor
  · rintro ⟨hR, h⟩
    refine ⟨hR, fun m hmem hmR => h (n, m) hmem ⟨rfl, hmR⟩⟩
  · rintro ⟨hR, h⟩
    refine ⟨hR, fun x hmem hx => ?_⟩
    obtain ⟨hx1, hx2⟩ := hx
    exact h x.2 (by rw [← hx1]; exact hmem) hx2

/-- A single `Reaches` walk along an orbit `g^[·] n0`, from index `i` to `i+d+1`. -/
private theorem reaches_orbit (edges : List (Key × Key)) (g : Key → Key) (n0 : Key)
    (hedge : ∀ i, (g^[i] n0, g^[i + 1] n0) ∈ edges) (i d : Nat) :
    Reaches edges (g^[i] n0) (g^[i + d + 1] n0) := by
  induction d with
  | zero => exact Reaches.step (hedge i)
  | succ e ih => exact Reaches.trans ih (Reaches.step (hedge (i + e + 1)))

/-- **Pigeonhole core.** A non-empty "stuck" remaining set — one where no node is ready,
    i.e. every node still has an out-edge into the set — contains a dependency cycle. -/
theorem stuck_cycle (R : List Key) (edges : List (Key × Key))
    (hne : R ≠ []) (hstuck : readyNodes R edges = []) :
    ∃ k, Reaches edges k k := by
  classical
  -- every node in R has a successor in R (nothing is ready)
  have hsucc : ∀ n, n ∈ R → ∃ m, m ∈ R ∧ (n, m) ∈ edges := by
    intro n hn
    by_contra hc
    simp only [not_exists, not_and] at hc
    have hmem : n ∈ readyNodes R edges := by
      refine (mem_readyNodes_iff R edges n).mpr ⟨hn, ?_⟩
      intro m hme hmR
      exact hc m hmR hme
    rw [hstuck] at hmem
    simp at hmem
  -- a total successor function on R
  let g : Key → Key := fun n => if h : n ∈ R then (hsucc n h).choose else n
  have hg : ∀ n, n ∈ R → g n ∈ R ∧ (n, g n) ∈ edges := by
    intro n hn
    have := (hsucc n hn).choose_spec
    simpa only [g, dif_pos hn] using this
  obtain ⟨n0, hn0⟩ := List.exists_mem_of_ne_nil R hne
  have horb : ∀ i, g^[i] n0 ∈ R := by
    intro i
    induction i with
    | zero => simpa using hn0
    | succ k ih => rw [Function.iterate_succ_apply']; exact (hg _ ih).1
  have hedge : ∀ i, (g^[i] n0, g^[i + 1] n0) ∈ edges := by
    intro i
    rw [Function.iterate_succ_apply']
    exact (hg _ (horb i)).2
  -- pigeonhole: |R|+1 orbit points into R.toFinset (card ≤ |R|)
  have hcard : (R.toFinset).card < (Finset.range (R.length + 1)).card := by
    rw [Finset.card_range]
    exact Nat.lt_succ_of_le (List.toFinset_card_le R)
  have hmaps : ∀ i ∈ Finset.range (R.length + 1), g^[i] n0 ∈ R.toFinset :=
    fun i _ => List.mem_toFinset.mpr (horb i)
  obtain ⟨i, _, j, _, hij, heq⟩ :=
    Finset.exists_ne_map_eq_of_card_lt_of_maps_to hcard hmaps
  rcases Nat.lt_or_ge i j with hlt | hge
  · obtain ⟨d, hd⟩ := Nat.exists_eq_add_of_lt hlt
    refine ⟨g^[i] n0, ?_⟩
    have h := reaches_orbit edges g n0 hedge i d
    rw [← hd, ← heq] at h
    exact h
  · have hlt : j < i := lt_of_le_of_ne hge (Ne.symm hij)
    obtain ⟨d, hd⟩ := Nat.exists_eq_add_of_lt hlt
    refine ⟨g^[j] n0, ?_⟩
    have h := reaches_orbit edges g n0 hedge j d
    rw [← hd, heq] at h
    exact h

/-- One-step unfolding of `kahn` on a non-empty remaining set. -/
theorem kahn_succ (edges : List (Key × Key)) (n : Nat) (R : List Key)
    (acc : List (List Key)) (hR : R ≠ []) :
    kahn edges (n + 1) R acc =
      (if (readyNodes R edges).isEmpty then none
       else kahn edges n (R.filter (fun x => ¬ (readyNodes R edges).contains x))
              (readyNodes R edges :: acc)) := by
  simp only [kahn]
  rw [if_neg]
  simp only [List.isEmpty_iff]
  exact hR

/-- If `kahn` fails, some reachable remaining set was "stuck" (non-empty, no ready
    nodes). Uses the invariant `|remaining| ≤ fuel`, so the fuel-exhaustion branch is
    never the culprit — only a genuine stuck set is. -/
theorem kahn_none_stuck (edges : List (Key × Key)) :
    ∀ (fuel : Nat) (R : List Key) (acc : List (List Key)),
      R.length ≤ fuel → kahn edges fuel R acc = none →
      ∃ R', R' ≠ [] ∧ readyNodes R' edges = [] := by
  intro fuel
  induction fuel with
  | zero =>
      intro R acc hlen hnone
      have hR : R = [] := List.length_eq_zero_iff.mp (Nat.le_zero.mp hlen)
      subst hR
      simp [kahn] at hnone
  | succ n ih =>
      intro R acc hlen hnone
      by_cases hR : R = []
      · subst hR; simp [kahn] at hnone
      · rw [kahn_succ edges n R acc hR] at hnone
        by_cases hready : (readyNodes R edges).isEmpty
        · exact ⟨R, hR, List.isEmpty_iff.mp hready⟩
        · rw [if_neg hready] at hnone
          refine ih _ _ ?_ hnone
          -- the filter drops at least one ready node, so length strictly decreases
          obtain ⟨r, hr⟩ := List.exists_mem_of_ne_nil _ (by
            simpa only [List.isEmpty_iff] using hready)
          have hrR : r ∈ R := List.mem_of_mem_filter hr
          have hlt : (R.filter (fun x => ¬ (readyNodes R edges).contains x)).length < R.length := by
            have hle := List.length_filter_le (fun x => ¬ (readyNodes R edges).contains x) R
            rcases lt_or_eq_of_le hle with h | h
            · exact h
            · exfalso
              rw [List.length_filter_eq_length_iff] at h
              have hthis := h r hrR
              revert hthis
              simp [List.contains_eq_mem, hr]
          omega

/-- Every `Reaches` walk starts with a concrete edge. -/
private theorem first_edge (edges : List (Key × Key)) {a c : Key} (h : Reaches edges a c) :
    ∃ b, (a, b) ∈ edges ∧ (b = c ∨ Reaches edges b c) := by
  induction h with
  | step hab => exact ⟨_, hab, Or.inl rfl⟩
  | @trans a b c _ r2 ih1 _ =>
      obtain ⟨x, hax, hx⟩ := ih1
      refine ⟨x, hax, Or.inr ?_⟩
      rcases hx with rfl | hxb
      · exact r2
      · exact Reaches.trans hxb r2

/-- A cycle node has an out-edge to another cycle node. -/
private theorem cyc_out (edges : List (Key × Key)) {k : Key} (h : Reaches edges k k) :
    ∃ m, (k, m) ∈ edges ∧ Reaches edges m m := by
  obtain ⟨m, hkm, hm⟩ := first_edge edges h
  refine ⟨m, hkm, ?_⟩
  rcases hm with rfl | hmk
  · exact h
  · exact Reaches.trans hmk (Reaches.step hkm)

/-- **Cycle-node persistence.** If every cycle node is currently remaining, `kahn`
    never empties the remaining set and returns `none`: no cycle node is ever ready
    (it always has an out-edge to another remaining cycle node). -/
theorem kahn_cycle_none (edges : List (Key × Key)) (hcyc : ∃ k, Reaches edges k k) :
    ∀ (fuel : Nat) (R : List Key) (acc : List (List Key)),
      (∀ x, Reaches edges x x → x ∈ R) → kahn edges fuel R acc = none := by
  intro fuel
  induction fuel with
  | zero =>
      intro R acc hsub
      obtain ⟨k, hk⟩ := hcyc
      cases R with
      | nil => exact absurd (hsub k hk) (by simp)
      | cons a t => simp [kahn]
  | succ n ih =>
      intro R acc hsub
      obtain ⟨k, hk⟩ := hcyc
      have hRne : R ≠ [] := List.ne_nil_of_mem (hsub k hk)
      rw [kahn_succ edges n R acc hRne]
      by_cases hready : (readyNodes R edges).isEmpty
      · simp [hready]
      · rw [if_neg hready]
        apply ih
        intro x hx
        have hxR : x ∈ R := hsub x hx
        obtain ⟨m, hxm, hmm⟩ := cyc_out edges hx
        have hmR : m ∈ R := hsub m hmm
        have hxnotready : x ∉ readyNodes R edges := by
          rw [mem_readyNodes_iff]
          rintro ⟨-, hall⟩
          exact hall m hxm hmR
        rw [List.mem_filter]
        refine ⟨hxR, ?_⟩
        simp [List.contains_eq_mem, hxnotready]

/-- Both endpoints of a dependency edge are tainted (derived) keys. -/
theorem depEdges_mem (S : Schema) {a b : Key} (h : (a, b) ∈ depEdges S) :
    a ∈ taintedKeys S ∧ b ∈ taintedKeys S := by
  unfold depEdges at h
  rw [List.mem_flatMap] at h
  obtain ⟨a', ha', hmem⟩ := h
  rw [List.mem_filterMap] at hmem
  obtain ⟨b', _hb', heq⟩ := hmem
  by_cases hc : (taintedKeys S).contains b'
  · rw [if_pos hc, Option.some.injEq, Prod.mk.injEq] at heq
    obtain ⟨rfl, rfl⟩ := heq
    exact ⟨ha', by simpa [List.contains_eq_mem] using hc⟩
  · rw [if_neg hc] at heq
    exact absurd heq (by simp)

/-- **T0b (part 1).** `stratify` fails exactly on a derived-dependency cycle: Kahn's
    ready-node filter peels every node iff there is no cycle. `⟹` a failed run leaves a
    non-empty stuck set (fuel = `|nodes|` rules out premature exhaustion), which
    contains a cycle by pigeonhole; `⟸` every cycle node persists in `remaining`, so the
    run never empties it. -/
theorem stratify_none_iff_cycle (S : Schema) :
    stratify S = none ↔ HasDerivedCycle S := by
  unfold stratify
  constructor
  · intro hnone
    obtain ⟨R', hne, hstuck⟩ :=
      kahn_none_stuck (depEdges S) (taintedKeys S).length (taintedKeys S) [] le_rfl hnone
    exact stuck_cycle R' (depEdges S) hne hstuck
  · intro hcyc
    apply kahn_cycle_none (depEdges S) hcyc
    intro x hx
    obtain ⟨m, hxm, _⟩ := cyc_out (depEdges S) hx
    exact (depEdges_mem S hxm).1

/-- The topological property of a produced layer list: every edge `(a,b)` points from
    a layer to an earlier-or-equal one. -/
def TopoLayered (edges : List (Key × Key)) (L : List (List Key)) : Prop :=
  ∀ a b i j, (a, b) ∈ edges → a ∈ L.getD i [] → b ∈ L.getD j [] → j ≤ i

theorem readyNodes_subset {R : List Key} {edges : List (Key × Key)} {n : Key}
    (h : n ∈ readyNodes R edges) : n ∈ R :=
  ((mem_readyNodes_iff R edges n).mp h).1

/-! Small `getD`/`++` index lemmas (this Mathlib has no direct `getD_append`). -/

private theorem getD_app_lt {α} (l l' : List α) (d : α) {i : Nat} (h : i < l.length) :
    (l ++ l').getD i d = l.getD i d := by
  rw [List.getD_eq_getElem?_getD, List.getD_eq_getElem?_getD, List.getElem?_append_left h]

private theorem getD_app_ge {α} (l l' : List α) (d : α) {i : Nat} (h : l.length ≤ i) :
    (l ++ l').getD i d = l'.getD (i - l.length) d := by
  rw [List.getD_eq_getElem?_getD, List.getD_eq_getElem?_getD, List.getElem?_append_right h]

private theorem getD_ge_default {α} (l : List α) (d : α) {i : Nat} (h : l.length ≤ i) :
    l.getD i d = d := by
  rw [List.getD_eq_getElem?_getD, List.getElem?_eq_none_iff.mpr h, Option.getD_none]

/-- Membership in the `getD` of a singleton layer collapses to membership in it (the
    out-of-range case is vacuous). -/
private theorem mem_getD_singleton {α} {x : List α} {b : α} :
    ∀ {k}, b ∈ ([x].getD k []) → b ∈ x
  | 0, h => by rwa [List.getD_cons_zero] at h
  | _ + 1, h => by
      rw [getD_ge_default [x] [] (by simp)] at h
      simp at h

/-- A singleton layer's `getD` above index `0` is the empty default. -/
private theorem getD_singleton_high {α} (x : List α) {k : Nat} (h : 1 ≤ k) :
    ([x].getD k [] : List α) = [] :=
  getD_ge_default [x] [] (by simpa using h)

/-- **Kahn topological invariant.** Threading a two-part invariant through the recursion:
    (H1) the already-peeled layers `acc.reverse` are topologically ordered, and (H2)
    every peeled node's out-edges have already left `remaining`. Each newly-peeled ready
    layer is appended last, and readiness + (H2) force its edges to point strictly
    earlier — so the invariant is preserved and the final `L` is topologically layered. -/
theorem kahn_topo (edges : List (Key × Key)) :
    ∀ (fuel : Nat) (remaining : List Key) (acc L : List (List Key)),
      kahn edges fuel remaining acc = some L →
      TopoLayered edges acc.reverse →
      (∀ a b, (a, b) ∈ edges → a ∈ acc.reverse.flatten → b ∉ remaining) →
      TopoLayered edges L := by
  intro fuel
  induction fuel with
  | zero =>
      intro remaining acc L hkahn h1 _h2
      simp only [kahn] at hkahn
      split at hkahn
      · rw [Option.some.injEq] at hkahn; subst hkahn; exact h1
      · exact absurd hkahn (by simp)
  | succ n ih =>
      intro remaining acc L hkahn h1 h2
      by_cases hRe : remaining = []
      · subst hRe
        simp only [kahn, List.isEmpty_nil, if_true] at hkahn
        rw [Option.some.injEq] at hkahn; subst hkahn; exact h1
      · rw [kahn_succ edges n remaining acc hRe] at hkahn
        by_cases hready : (readyNodes remaining edges).isEmpty
        · rw [if_pos hready] at hkahn; exact absurd hkahn (by simp)
        · rw [if_neg hready] at hkahn
          refine ih _ _ _ hkahn ?_ ?_
          · -- H1' : TopoLayered edges (ready :: acc).reverse = acc.reverse ++ [ready]
            rw [List.reverse_cons]
            intro a b i j hab hai hbj
            set P := acc.reverse with hP
            set ready := readyNodes remaining edges with hrdef
            rcases lt_or_ge i P.length with hi | hi
            · -- a in an already-peeled layer i
              rw [getD_app_lt _ _ _ hi] at hai
              have haP : a ∈ P.flatten := by
                have hEl : P.getD i [] = P[i] := by
                  rw [List.getD_eq_getElem?_getD, List.getElem?_eq_getElem hi, Option.getD_some]
                rw [hEl] at hai
                exact List.mem_flatten.mpr ⟨P[i], List.getElem_mem hi, hai⟩
              rcases lt_or_ge j P.length with hj | hj
              · rw [getD_app_lt _ _ _ hj] at hbj
                exact h1 a b i j hab hai hbj
              · -- b would be in the freshly-peeled layer, contradicting H2
                rw [getD_app_ge _ _ _ hj] at hbj
                exact absurd (readyNodes_subset (mem_getD_singleton hbj)) (h2 a b hab haP)
            · rcases Nat.lt_or_ge i (P.length + 1) with hi2 | hi2
              · -- a in the freshly-peeled last layer (index P.length); any real b is ≤ i
                have hieq : i = P.length := by omega
                rcases lt_or_ge j (P.length + 1) with hj2 | hj2
                · omega
                · exfalso
                  rw [getD_app_ge _ _ _ (by omega), getD_singleton_high ready (by omega)] at hbj
                  simp at hbj
              · -- i beyond the last layer: a ∈ [] is impossible
                exfalso
                rw [getD_app_ge _ _ _ hi, getD_singleton_high ready (by omega)] at hai
                simp at hai
          · -- H2' : peeled-now nodes' edges leave the filtered remaining
            intro a b hab ha
            rw [List.reverse_cons, List.flatten_append, List.flatten_cons,
              List.flatten_nil, List.append_nil, List.mem_append] at ha
            rcases ha with ha | ha
            · exact fun hb => h2 a b hab ha (List.mem_of_mem_filter hb)
            · have hall := ((mem_readyNodes_iff remaining edges a).mp ha).2
              exact fun hb => hall b hab (List.mem_of_mem_filter hb)

/-! ### Kahn strictness, coverage, and size — the T0a rank-induction interface -/

/-- The STRICT topological property: every edge points to a strictly earlier
    layer. Holds for `kahn` output because a ready node's out-edges have all left
    `remaining`, while its own layer is still remaining when peeled — so
    within-layer (and self-) edges are impossible. -/
def TopoLayeredStrict (edges : List (Key × Key)) (L : List (List Key)) : Prop :=
  ∀ a b i j, (a, b) ∈ edges → a ∈ L.getD i [] → b ∈ L.getD j [] → j < i

/-- `kahn_topo`, strengthened to the strict conclusion. Same invariant threading;
    the new case (both endpoints in the freshly-peeled layer) contradicts the
    peeled node's readiness. -/
theorem kahn_topo_strict (edges : List (Key × Key)) :
    ∀ (fuel : Nat) (remaining : List Key) (acc L : List (List Key)),
      kahn edges fuel remaining acc = some L →
      TopoLayeredStrict edges acc.reverse →
      (∀ a b, (a, b) ∈ edges → a ∈ acc.reverse.flatten → b ∉ remaining) →
      TopoLayeredStrict edges L := by
  intro fuel
  induction fuel with
  | zero =>
      intro remaining acc L hkahn h1 _h2
      simp only [kahn] at hkahn
      split at hkahn
      · rw [Option.some.injEq] at hkahn; subst hkahn; exact h1
      · exact absurd hkahn (by simp)
  | succ n ih =>
      intro remaining acc L hkahn h1 h2
      by_cases hRe : remaining = []
      · subst hRe
        simp only [kahn, List.isEmpty_nil, if_true] at hkahn
        rw [Option.some.injEq] at hkahn; subst hkahn; exact h1
      · rw [kahn_succ edges n remaining acc hRe] at hkahn
        by_cases hready : (readyNodes remaining edges).isEmpty
        · rw [if_pos hready] at hkahn; exact absurd hkahn (by simp)
        · rw [if_neg hready] at hkahn
          refine ih _ _ _ hkahn ?_ ?_
          · rw [List.reverse_cons]
            intro a b i j hab hai hbj
            set P := acc.reverse with hP
            set ready := readyNodes remaining edges with hrdef
            rcases lt_or_ge i P.length with hi | hi
            · -- a in an already-peeled layer i
              rw [getD_app_lt _ _ _ hi] at hai
              have haP : a ∈ P.flatten := by
                have hEl : P.getD i [] = P[i] := by
                  rw [List.getD_eq_getElem?_getD, List.getElem?_eq_getElem hi,
                    Option.getD_some]
                rw [hEl] at hai
                exact List.mem_flatten.mpr ⟨P[i], List.getElem_mem hi, hai⟩
              rcases lt_or_ge j P.length with hj | hj
              · rw [getD_app_lt _ _ _ hj] at hbj
                exact h1 a b i j hab hai hbj
              · -- b would be in the freshly-peeled layer, contradicting H2
                rw [getD_app_ge _ _ _ hj] at hbj
                exact absurd (readyNodes_subset (mem_getD_singleton hbj))
                  (h2 a b hab haP)
            · rcases Nat.lt_or_ge i (P.length + 1) with hi2 | hi2
              · -- a in the freshly-peeled last layer (index P.length)
                have hieq : i = P.length := by omega
                have haR : a ∈ ready := by
                  rw [getD_app_ge _ _ _ hi] at hai
                  exact mem_getD_singleton hai
                rcases lt_or_ge j P.length with hj | hj
                · omega
                · rcases Nat.lt_or_ge j (P.length + 1) with hj2 | hj2
                  · -- b in the fresh layer too: a's readiness is contradicted
                    exfalso
                    have hbR : b ∈ ready := by
                      rw [getD_app_ge _ _ _ hj] at hbj
                      exact mem_getD_singleton hbj
                    have hall := ((mem_readyNodes_iff remaining edges a).mp haR).2
                    exact hall b hab (readyNodes_subset hbR)
                  · exfalso
                    rw [getD_app_ge _ _ _ (by omega),
                      getD_singleton_high ready (by omega)] at hbj
                    simp at hbj
              · exfalso
                rw [getD_app_ge _ _ _ hi, getD_singleton_high ready (by omega)] at hai
                simp at hai
          · intro a b hab ha
            rw [List.reverse_cons, List.flatten_append, List.flatten_cons,
              List.flatten_nil, List.append_nil, List.mem_append] at ha
            rcases ha with ha | ha
            · exact fun hb => h2 a b hab ha (List.mem_of_mem_filter hb)
            · have hall := ((mem_readyNodes_iff remaining edges a).mp ha).2
              exact fun hb => hall b hab (List.mem_of_mem_filter hb)

private theorem mem_flatten_of_mem_reverse {x : Key} {acc : List (List Key)}
    (hx : x ∈ acc.flatten) : x ∈ acc.reverse.flatten := by
  rw [List.mem_flatten] at hx ⊢
  obtain ⟨l, hl, hxl⟩ := hx
  exact ⟨l, List.mem_reverse.mpr hl, hxl⟩

/-- **Coverage**: everything remaining or already peeled ends up in the output. -/
theorem kahn_covers (edges : List (Key × Key)) :
    ∀ (fuel : Nat) (R : List Key) (acc L : List (List Key)),
      kahn edges fuel R acc = some L →
      ∀ x, (x ∈ R ∨ x ∈ acc.flatten) → x ∈ L.flatten := by
  intro fuel
  induction fuel with
  | zero =>
      intro R acc L hkahn x hx
      simp only [kahn] at hkahn
      split at hkahn
      · rw [Option.some.injEq] at hkahn; subst hkahn
        rcases hx with hx | hx
        · rename_i hemp
          rw [List.isEmpty_iff] at hemp; subst hemp; simp at hx
        · exact mem_flatten_of_mem_reverse hx
      · exact absurd hkahn (by simp)
  | succ n ih =>
      intro R acc L hkahn x hx
      by_cases hRe : R = []
      · subst hRe
        simp only [kahn, List.isEmpty_nil, if_true, Option.some.injEq] at hkahn
        subst hkahn
        rcases hx with hx | hx
        · simp at hx
        · exact mem_flatten_of_mem_reverse hx
      · rw [kahn_succ edges n R acc hRe] at hkahn
        by_cases hready : (readyNodes R edges).isEmpty
        · rw [if_pos hready] at hkahn; exact absurd hkahn (by simp)
        · rw [if_neg hready] at hkahn
          refine ih _ _ _ hkahn x ?_
          rcases hx with hx | hx
          · by_cases hxr : x ∈ readyNodes R edges
            · right
              rw [List.flatten_cons]
              exact List.mem_append_left _ hxr
            · left
              rw [List.mem_filter]
              refine ⟨hx, ?_⟩
              simp [List.contains_eq_mem, hxr]
          · right
            rw [List.flatten_cons]
            exact List.mem_append_right _ hx

/-- Conversely, output layers only hold nodes that were remaining or peeled. -/
theorem kahn_layers_sub (edges : List (Key × Key)) :
    ∀ (fuel : Nat) (R : List Key) (acc L : List (List Key)),
      kahn edges fuel R acc = some L →
      ∀ x, x ∈ L.flatten → x ∈ R ∨ x ∈ acc.flatten := by
  intro fuel
  induction fuel with
  | zero =>
      intro R acc L hkahn x hx
      simp only [kahn] at hkahn
      split at hkahn
      · rw [Option.some.injEq] at hkahn; subst hkahn
        refine Or.inr ?_
        rw [List.mem_flatten] at hx ⊢
        obtain ⟨l, hl, hxl⟩ := hx
        exact ⟨l, List.mem_reverse.mp hl, hxl⟩
      · exact absurd hkahn (by simp)
  | succ n ih =>
      intro R acc L hkahn x hx
      by_cases hRe : R = []
      · subst hRe
        simp only [kahn, List.isEmpty_nil, if_true, Option.some.injEq] at hkahn
        subst hkahn
        refine Or.inr ?_
        rw [List.mem_flatten] at hx ⊢
        obtain ⟨l, hl, hxl⟩ := hx
        exact ⟨l, List.mem_reverse.mp hl, hxl⟩
      · rw [kahn_succ edges n R acc hRe] at hkahn
        by_cases hready : (readyNodes R edges).isEmpty
        · rw [if_pos hready] at hkahn; exact absurd hkahn (by simp)
        · rw [if_neg hready] at hkahn
          rcases ih _ _ _ hkahn x hx with hx' | hx'
          · exact Or.inl (List.mem_of_mem_filter hx')
          · rw [List.flatten_cons, List.mem_append] at hx'
            rcases hx' with hx' | hx'
            · exact Or.inl (readyNodes_subset hx')
            · exact Or.inr hx'

/-- Peeling at least one node per round bounds the number of layers. -/
theorem kahn_length (edges : List (Key × Key)) :
    ∀ (fuel : Nat) (R : List Key) (acc L : List (List Key)),
      kahn edges fuel R acc = some L → L.length ≤ R.length + acc.length := by
  intro fuel
  induction fuel with
  | zero =>
      intro R acc L hkahn
      simp only [kahn] at hkahn
      split at hkahn
      · rw [Option.some.injEq] at hkahn; subst hkahn
        simp
      · exact absurd hkahn (by simp)
  | succ n ih =>
      intro R acc L hkahn
      by_cases hRe : R = []
      · subst hRe
        simp only [kahn, List.isEmpty_nil, if_true, Option.some.injEq] at hkahn
        subst hkahn
        simp
      · rw [kahn_succ edges n R acc hRe] at hkahn
        by_cases hready : (readyNodes R edges).isEmpty
        · rw [if_pos hready] at hkahn; exact absurd hkahn (by simp)
        · rw [if_neg hready] at hkahn
          have hlt : (R.filter (fun x => ¬ (readyNodes R edges).contains x)).length
              < R.length := by
            obtain ⟨r, hr⟩ := List.exists_mem_of_ne_nil _ (by
              simpa only [List.isEmpty_iff] using hready)
            have hrR : r ∈ R := List.mem_of_mem_filter hr
            have hle := List.length_filter_le
              (fun x => ¬ (readyNodes R edges).contains x) R
            rcases lt_or_eq_of_le hle with h | h
            · exact h
            · exfalso
              rw [List.length_filter_eq_length_iff] at h
              have hthis := h r hrR
              revert hthis
              simp [List.contains_eq_mem, hr]
          have := ih _ _ _ hkahn
          simp only [List.length_cons] at this
          omega

/-- Flattened membership names a concrete layer index. -/
theorem mem_flatten_getD {L : List (List Key)} {x : Key} (hx : x ∈ L.flatten) :
    ∃ i, i < L.length ∧ x ∈ L.getD i [] := by
  rw [List.mem_flatten] at hx
  obtain ⟨l, hl, hxl⟩ := hx
  obtain ⟨i, hi, hEl⟩ := List.getElem_of_mem hl
  refine ⟨i, hi, ?_⟩
  rw [List.getD_eq_getElem?_getD, List.getElem?_eq_getElem hi, Option.getD_some, hEl]
  exact hxl

/-! Stratify-level wrappers of the Kahn lemmas. -/

/-- Every tainted key lands in some layer. -/
theorem stratify_covers (S : Schema) {L : List (List Key)} (h : stratify S = some L) :
    ∀ k ∈ taintedKeys S, ∃ i, i < L.length ∧ k ∈ L.getD i [] := by
  intro k hk
  exact mem_flatten_getD
    (kahn_covers (depEdges S) (taintedKeys S).length (taintedKeys S) [] L h k
      (Or.inl hk))

/-- Layers hold only tainted keys. -/
theorem stratify_layers_tainted (S : Schema) {L : List (List Key)}
    (h : stratify S = some L) :
    ∀ i, ∀ k ∈ L.getD i [], k ∈ taintedKeys S := by
  intro i k hk
  rcases Nat.lt_or_ge i L.length with hi | hi
  · have hkfl : k ∈ L.flatten := by
      have hEl : L.getD i [] = L[i] := by
        rw [List.getD_eq_getElem?_getD, List.getElem?_eq_getElem hi, Option.getD_some]
      rw [hEl] at hk
      exact List.mem_flatten.mpr ⟨L[i], List.getElem_mem hi, hk⟩
    rcases kahn_layers_sub (depEdges S) (taintedKeys S).length (taintedKeys S) [] L h
        k hkfl with h' | h'
    · exact h'
    · simp at h'
  · rw [getD_ge_default _ _ hi] at hk
    simp at hk

/-- No more layers than tainted keys. -/
theorem stratify_length (S : Schema) {L : List (List Key)} (h : stratify S = some L) :
    L.length ≤ (taintedKeys S).length := by
  have := kahn_length (depEdges S) (taintedKeys S).length (taintedKeys S) [] L h
  simpa using this

/-- The layering is STRICTLY topological. -/
theorem stratify_topo_strict (S : Schema) {L : List (List Key)}
    (h : stratify S = some L) : TopoLayeredStrict (depEdges S) L := by
  apply kahn_topo_strict (depEdges S) _ (taintedKeys S) [] L h
  · intro a b i j _ ha; simp at ha
  · intro a b _ ha; simp at ha

/-- **T0b (part 2).** When it succeeds, every dependency edge points to an
    earlier-or-equal layer (topological). -/
theorem stratify_topological (S : Schema) (L : List (List Key)) (h : stratify S = some L) :
    (∀ e ∈ depEdges S, ∀ i j, e.1 ∈ L.getD i [] → e.2 ∈ L.getD j [] → j ≤ i) := by
  have htopo : TopoLayered (depEdges S) L := by
    apply kahn_topo (depEdges S) _ (taintedKeys S) [] L h
    · intro a b i j _ ha; simp at ha
    · intro a b _ ha; simp at ha
  intro e he i j hei hej
  exact htopo e.1 e.2 i j he hei hej

end Zanzibar
