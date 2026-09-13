import ZanzibarProofs.GraphIndex.Write
import ZanzibarProofs.Spec.Stratify

/-!
# The concrete write model — untainted RULE ROUTING (ROADMAP W2, write half)

`SEMANTICS.md` §4, §7.5; `zanzibar_utils_v1.py::RuleSet.apply` / `::_rewrite_rule` /
`::_emit_expr`. W1 widened the *direct* write model to wildcard bridges. **W2 widens
it to untainted rule structure** — `computed`, `union` of untainted operands, and
`ttu` defs — by transcribing the Python graph index's rewrite-fanout:

> A raw write of a public tuple `t` is expanded by `RuleSet.apply` into the
> **rewrite-closure** of `t` under the schema's Computed/TTU rules (fan-in through
> unions, iterated to a fixpoint), and *each* resulting triple is materialized as a
> direct closure edge. The reachability read is unchanged.

The two rewrite kinds (`zanzibar_utils_v1.py::_rewrite_rule`):
* **Computed** `R := computed R'` on object type `ot`: a tuple `(s, R', o)` with
  `o.type = ot` also produces `(s, R, o)` — same subject/object, relation `R'↦R`.
* **TTU** `R := ttu tr ts` on object type `ot`: a tuple `(s, ts, o)` with
  `o.type = ot` produces `(⟨s.type, s.name, tr⟩, R, o)` — the tupleset parent `s`
  becomes the userset `s#tr`, relation `ts ↦ R`. (Stored-parent semantics: the rule
  fires on the STORED tupleset tuple, never on computed membership.)

Attack-first (2026-07-10, machine-checked `#eval` vs `sem`, then deleted): on a
computed / chained-computed / ttu (±) / union / userset-flow corpus, `sem` answers
exactly what the rewrite-fanout materializes; no refutation. Design confirmed.

**This file is the write half** (mirrors "W1b/W1c write model DONE"): the rewrite
extraction, the bounded closure, `writeRules` (fold `writeDirect` over the closure),
and its structural/`Inv`/residue-free/quiescence preservation + the `ReachedByRules`
operational closure. The read correspondence `check = sem` on this fragment is the
deferred next increment.
-/

namespace Zanzibar

/-! ## §4 — the rewrite rules extracted from a schema -/

/-- A rewrite kind: `computed` keeps the subject; `ttu tr` re-userset-s the subject
    with predicate `tr` (`_rewrite_rule`). -/
inductive RuleKind where
  | computed
  | ttu (tr : String)
deriving DecidableEq, Repr, Inhabited

/-- One compiled rewrite rule: on object type `objectType`, a tuple carrying
    `matchRel` also produces one carrying `outRel` (the derived relation). -/
structure RRule where
  objectType : String
  matchRel : String
  outRel : String
  kind : RuleKind
deriving DecidableEq, Repr, Inhabited

/-- The rewrite arms of one expression targeting relation `outRel` on object type
    `ot` — `_emit_expr` walks INTO unions (each arm targets the same relation) and
    turns each `Computed`/`TTU` leaf into a rewrite rule. `Direct` arms compile to
    admission Filters (no fan-out) and boolean nodes are out of the untainted
    fragment, so both contribute no rules. -/
def exprArms (ot outRel : String) : Expr → List RRule
  | .computed r => [⟨ot, r, outRel, .computed⟩]
  | .ttu tr ts  => [⟨ot, ts, outRel, .ttu tr⟩]
  | .union a b  => exprArms ot outRel a ++ exprArms ot outRel b
  | .direct _   => []
  | .inter _ _  => []
  | .excl _ _   => []

/-- All rewrite rules of a schema (`RuleSet`'s Computed/TTU Rules).

    **Taint filter — faithful mirror of the Python**
    (`zanzibar_utils_v1.py::compile_ruleset`'s `if (object_type, relation_name) not in
    tainted: _emit_expr(...)` loop): the compiler routes every DERIVED (tainted / boolean)
    key OFF the rewrite fanout entirely (`if key not in tainted: fan out; else: derived
    plan`), so it NEVER emits a rewrite rule whose output is a tainted relation. The
    earlier unfiltered model (`S.defs.flatMap …`) materialized a transient fanout edge at
    a union-rooted derived R-node; with a userset-subject stored tuple matching the arm
    that stale fanout edge SURVIVED to the drained state — a real Lean-model-vs-Python
    state divergence (found 2026-07-17). Skipping derived defs here is the faithful
    mirror: `isDerived` (taint fixpoint, `Spec/Stratify.lean`) is exactly the compiler's
    `tainted` set. -/
def schemaRewrites (S : Schema) : List RRule :=
  (S.defs.filter (fun d => !(isDerived S d.1))).flatMap (fun d => exprArms d.1.1 d.1.2 d.2)

/-- **A TTU node of a BOOLEAN-FREE expression is one of its rewrite arms.**

    `exprTtus` (`State.lean`) and `exprArms` agree on `computed`/`ttu`/`union`/`direct`;
    they part company at `inter`/`excl`, where `exprTtus` RECURSES and `exprArms` returns
    `[]` ("boolean nodes are out of the untainted fragment", above). `containsBool e = false`
    is exactly the hypothesis that rules those two arms out, and it is what an untainted
    declared key supplies (`RestrictBase.lean::containsBool_of_mem_defs_untainted`).

    ⚠ **The hypothesis is not decoration.** Without it the statement is FALSE: at
    `e = .inter (.ttu "tr" "ts") (.computed "c")` the LHS list is `[("tr","ts")]` while
    `exprArms ot outRel e = []`. So this is the honest form of "`exprTtus` targets ⊆ what
    `exprArms` collects" — it holds on the boolean-free defs, which are precisely the ones
    `schemaRewrites` keeps. -/
theorem mem_exprArms_of_mem_exprTtus {ot outRel tr ts : String} :
    ∀ {e : Expr}, containsBool e = false → (tr, ts) ∈ exprTtus e →
      (⟨ot, ts, outRel, RuleKind.ttu tr⟩ : RRule) ∈ exprArms ot outRel e := by
  intro e
  induction e with
  | direct _ => intro _ h; simp [exprTtus] at h
  | computed _ => intro _ h; simp [exprTtus] at h
  | ttu tr' ts' =>
    intro _ h
    simp only [exprTtus, List.mem_singleton, Prod.mk.injEq] at h
    obtain ⟨rfl, rfl⟩ := h
    simp [exprArms]
  | union a b iha ihb =>
    intro hcb h
    simp only [containsBool, Bool.or_eq_false_iff] at hcb
    simp only [exprTtus, List.mem_append] at h
    simp only [exprArms, List.mem_append]
    exact h.imp (iha hcb.1) (ihb hcb.2)
  | inter _ _ _ _ => intro hcb; simp [containsBool] at hcb
  | excl _ _ _ _ => intro hcb; simp [containsBool] at hcb

/-- **A declared UNTAINTED def's rewrite arms are schema rewrites.** The `def`-level twin of
    `RulesComplete.lean::lookup_exprArms_sub`, which asks for `UntaintedSchema S` — an
    untaintedness claim about the WHOLE schema, far too strong for a consumer that holds a
    boolean schema and knows only that THIS def survived the taint filter. Both directions of
    `schemaRewrites`' definition are one `List.mem_flatMap` / `List.mem_filter` step; the
    only content is that `isDerived S d.1 = false` is literally the filter's predicate. -/
theorem mem_schemaRewrites_of_mem_exprArms {S : Schema} {d : (String × String) × Expr}
    (hd : d ∈ S.defs) (hu : isDerived S d.1 = false) {a : RRule}
    (ha : a ∈ exprArms d.1.1 d.1.2 d.2) : a ∈ schemaRewrites S := by
  unfold schemaRewrites
  exact List.mem_flatMap.mpr ⟨d, List.mem_filter.mpr ⟨hd, by rw [hu]; rfl⟩, ha⟩

/-- Apply one rewrite rule to a tuple, if it matches (relation + object type). -/
def applyRRule (r : RRule) (t : Tuple) : Option Tuple :=
  if t.relation = r.matchRel ∧ t.object.type = r.objectType then
    match r.kind with
    | .computed => some ⟨t.subject, r.outRel, t.object⟩
    | .ttu tr   => some ⟨⟨t.subject.type, t.subject.name, tr⟩, r.outRel, t.object⟩
  else none

/-- One rewrite step: every schema rule that matches `t` fires (fan-in expansion,
    `RuleSet.apply`). -/
def rewriteStep (S : Schema) (t : Tuple) : List Tuple :=
  (schemaRewrites S).filterMap (applyRRule · t)

/-- The bounded rewrite closure kernel: accumulate the current frontier and every
    tuple reachable by ≤ fuel rewrite steps. May emit duplicates on reconvergent
    schemas — deduplication is the caller's job (`rewriteClosure`). -/
def rewriteClosureAux (S : Schema) : Nat → List Tuple → List Tuple
  | 0, cur => cur
  | n + 1, cur => cur ++ rewriteClosureAux S n (cur.flatMap (rewriteStep S))

/-- The RAW (un-deduplicated) bounded rewrite closure of a single seed `t`.
    `RuleSet.apply`'s worklist iterates to a fixpoint; the rewrite graph on
    relations is a DAG (stratification), so `|keys|+1` levels suffice. On a
    reconvergent schema (two rewrite paths from one tuple to the same derived
    key) the same tuple can appear more than once — see `rewriteClosure`. -/
def rewriteClosureRaw (S : Schema) (t : Tuple) : List Tuple :=
  rewriteClosureAux S (S.keys.length + 1) [t]

/-- The rewrite-closure of a single raw write `t` (`RuleSet.apply t` as a list).

    Mirrors `zanzibar_utils_v1.py::RuleSet.apply`'s worklist dedup (its `processed`
    set): each derived key is materialized at most once per stored tuple, so a
    reconvergent schema does not over-count edge multiplicity. The dedup is
    **per-closure (per stored tuple)**, never over the assembled edge list —
    cross-tuple multiplicity is load-bearing and P3-compared (`nary_union` routes
    `alice -> any_of` from three separate tuples and must stay at 3). -/
def rewriteClosure (S : Schema) (t : Tuple) : List Tuple :=
  (rewriteClosureRaw S t).dedup

/-- The bridge lemma: dedup preserves MEMBERSHIP, which is all every
    reachability-level consumer needs. -/
@[simp] theorem mem_rewriteClosure_iff {S : Schema} {t u : Tuple} :
    u ∈ rewriteClosure S t ↔ u ∈ rewriteClosureRaw S t := List.mem_dedup

/-! ## The rule-routed write -/

/-- **Materialize one raw write with rule routing** (§7.5, `RuleSet.apply` +
    per-triple `add_tuple`): expand `t` into its rewrite-closure and materialize
    each resulting triple as a guarded direct edge (`writeDirect`, cycle-rejection
    faithful, residue-free). This is the untainted fan-out — no derived residues. -/
def GraphState.writeRules (σ : GraphState) (S : Schema) (t : Tuple) : GraphState :=
  (rewriteClosure S t).foldl (fun acc u => acc.writeDirect u) σ

/-! ## Folding `writeDirect` preserves the structural / residue / quiescence facts -/

/-- Folding `writeDirect` over any tuple list preserves `StructInv`. -/
theorem structInv_foldl_writeDirect {S : Schema} (ts : List Tuple) :
    ∀ {σ : GraphState}, StructInv S σ →
      StructInv S (ts.foldl (fun acc u => acc.writeDirect u) σ) := by
  induction ts with
  | nil => intro σ h; exact h
  | cons t rest ih => intro σ h; exact ih (structInv_writeDirect h t)

/-- Folding `writeDirect` preserves residue-freeness. -/
theorem residueEmpty_foldl_writeDirect (ts : List Tuple) :
    ∀ {σ : GraphState}, ResidueEmpty σ →
      ResidueEmpty (ts.foldl (fun acc u => acc.writeDirect u) σ) := by
  induction ts with
  | nil => intro σ h; exact h
  | cons t rest ih => intro σ h; exact ih (residueEmpty_writeDirect t h)

/-- Folding `writeDirect` preserves the full `Inv` on the residue-free fragment. -/
theorem inv_foldl_writeDirect {S : Schema} (ts : List Tuple) :
    ∀ {σ : GraphState}, Inv S σ → ResidueEmpty σ →
      Inv S (ts.foldl (fun acc u => acc.writeDirect u) σ) := by
  induction ts with
  | nil => intro σ h _; exact h
  | cons t rest ih =>
    intro σ h hre
    exact ih (inv_writeDirect h hre t) (residueEmpty_writeDirect t hre)

/-- Folding `writeDirect` preserves cascade-quiescence (outbox/watermark untouched). -/
theorem quiescent_foldl_writeDirect (ts : List Tuple) :
    ∀ {σ : GraphState}, Quiescent σ →
      Quiescent (ts.foldl (fun acc u => acc.writeDirect u) σ) := by
  induction ts with
  | nil => intro σ h; exact h
  | cons t rest ih => intro σ h; exact ih (quiescent_writeDirect h t)

/-- Folding `writeDirect` keeps the schema fixed. -/
theorem schema_foldl_writeDirect (ts : List Tuple) :
    ∀ {σ : GraphState},
      (ts.foldl (fun acc u => acc.writeDirect u) σ).schema = σ.schema := by
  induction ts with
  | nil => intro σ; rfl
  | cons t rest ih =>
    intro σ
    simp only [List.foldl_cons]
    rw [ih]; exact writeDirect_schema σ t

/-! ## `writeRules` preservation (immediate corollaries of the fold lemmas) -/

/-- **Structural preservation** for the rule-routed write. -/
theorem structInv_writeRules {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (t : Tuple) : StructInv S (σ.writeRules S t) :=
  structInv_foldl_writeDirect _ h

/-- **Residue-freeness preservation.** -/
theorem residueEmpty_writeRules {σ : GraphState} {S : Schema} (t : Tuple)
    (h : ResidueEmpty σ) : ResidueEmpty (σ.writeRules S t) :=
  residueEmpty_foldl_writeDirect _ h

/-- **Full-`Inv` preservation on the residue-free fragment** — W2's T2a `Inv`
    conjunct for untainted rule routing, proved honestly by folding
    `inv_writeDirect` over the rewrite-closure. -/
theorem inv_writeRules {S : Schema} {σ : GraphState} (h : Inv S σ)
    (hre : ResidueEmpty σ) (t : Tuple) : Inv S (σ.writeRules S t) :=
  inv_foldl_writeDirect _ h hre

/-- **Quiescence preservation.** -/
theorem quiescent_writeRules {σ : GraphState} {S : Schema} (t : Tuple)
    (h : Quiescent σ) : Quiescent (σ.writeRules S t) :=
  quiescent_foldl_writeDirect _ h

/-- The schema is fixed by the rule-routed write. -/
theorem writeRules_schema (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.writeRules S t).schema = σ.schema :=
  schema_foldl_writeDirect _

/-! ## The W2 operational write-closure -/

/-- **`ReachedByRules σ S T`** — `σ` is reached from the empty state by applying
    `T`'s writes as untainted *rule-routed* writes (`writeRules`). The W2 reachable-
    state closure; W1's `ReachedByDirect` is the special case where the schema has
    no Computed/TTU rules (`rewriteClosure` = `[t]`). -/
inductive ReachedByRules : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedByRules (emptyState S) S []
  | step {σ : GraphState} {S : Schema} {T : Store} (t : Tuple) :
      ReachedByRules σ S T → ReachedByRules (σ.writeRules S t) S (t :: T)

/-- **T2a for the untainted rule-routed fragment.** Every state reached by W2 writes
    satisfies the full I-series invariant, stays residue-free, and is cascade-
    quiescent — by induction over the concrete rule-routed write path, never
    postulated. -/
theorem reachedByRules_inv {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByRules σ S T) : Inv S σ ∧ ResidueEmpty σ ∧ Quiescent σ := by
  induction h with
  | empty S => exact ⟨inv_empty S, residueEmpty_empty S, quiescent_empty S⟩
  | step t _ ih =>
    obtain ⟨hInv, hRe, hQ⟩ := ih
    exact ⟨inv_writeRules hInv hRe t, residueEmpty_writeRules t hRe,
      quiescent_writeRules t hQ⟩

end Zanzibar
