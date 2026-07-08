import ZanzibarProofs.Core.Schema

/-!
# Taint and stratification

`SEMANTICS.md` §4.3, §4.4, transcribed from `zanzibar_utils_v1.py` (`compute_taint`
:1320, `_contains_boolean` :1282, `_stratify` :1630).

A relation is **derived (tainted)** iff it transitively reaches an
`Intersection`/`Exclusion`. Stratification is Kahn topological layering over the
dependency edges *among tainted relations only* (untainted relations may be
positively recursive; the closure handles them). `stratify S = none` iff a
derived-dependency cycle exists.

**Fidelity note (PROOF_STATUS variations):** the static reference/taint extraction
here is a faithful-but-independent reimplementation of the Python; Phase-2
conformance checks it against `compute_taint`/`_stratify` on the corpora.
-/

namespace Zanzibar

abbrev Key := String × String

/-- Types named in the `Direct` restrictions of an expression (the tupleset's
    parent member types, for TTU target references). -/
def directTypes : Expr → List String
  | .direct rs => rs.map (·.1)
  | .computed _ => []
  | .ttu _ _ => []
  | .union a b => directTypes a ++ directTypes b
  | .inter a b => directTypes a ++ directTypes b
  | .excl a b => directTypes a ++ directTypes b

/-- The `(type, relation)` nodes referenced by an expression at owner type `t`. -/
def exprRefs (S : Schema) (t : String) : Expr → List Key
  | .direct rs => rs.filterMap (fun r => if r.2.1 = BARE then none else some (r.1, r.2.1))
  | .computed r => [(t, r)]
  | .ttu tr ts =>
      -- tupleset reference on this object type, + target refs via parent types
      (t, ts) :: (match S.lookup (t, ts) with
                  | some e => (directTypes e).map (fun pt => (pt, tr))
                  | none => [])
  | .union a b => exprRefs S t a ++ exprRefs S t b
  | .inter a b => exprRefs S t a ++ exprRefs S t b
  | .excl a b => exprRefs S t a ++ exprRefs S t b

/-- References out of a declared key. -/
def refsOf (S : Schema) (k : Key) : List Key :=
  match S.lookup k with
  | some e => exprRefs S k.1 e
  | none => []

/-- Does an expression directly contain a boolean operator? (`_contains_boolean`). -/
def containsBool : Expr → Bool
  | .inter _ _ => true
  | .excl _ _ => true
  | .direct _ => false
  | .computed _ => false
  | .ttu _ _ => false
  | .union a b => containsBool a || containsBool b

/-- Base taint: the key's own definition contains a boolean operator. -/
def baseTaint (S : Schema) (k : Key) : Bool :=
  match S.lookup k with
  | some e => containsBool e
  | none => false

/-- One round of taint propagation: base-tainted, or references a currently-tainted
    key (`compute_taint` reachability). -/
def taintStep (S : Schema) (cur : List Key) : List Key :=
  S.keys.filter (fun k => baseTaint S k || (refsOf S k).any (fun r => cur.contains r))

/-- Iterate a function `n` times from `start`. -/
def iterate {α : Type} (f : α → α) : Nat → α → α
  | 0, x => x
  | n + 1, x => iterate f n (f x)

/-- The tainted (derived) keys: taint propagation to a fixpoint (bounded by the
    number of declared keys). -/
def taintedKeys (S : Schema) : List Key :=
  iterate (taintStep S) (S.keys.length) []

/-- Is a key derived? -/
def isDerived (S : Schema) (k : Key) : Bool := (taintedKeys S).contains k

/-- Dependency edges among derived relations: `(a, b)` means `a` depends on `b`
    (`b` must be settled first), for `a`, `b` both derived. -/
def depEdges (S : Schema) : List (Key × Key) :=
  (taintedKeys S).flatMap (fun a =>
    (refsOf S a).filterMap (fun b => if (taintedKeys S).contains b then some (a, b) else none))

/-- Nodes ready this round: no outstanding dependency on a still-remaining node. -/
def readyNodes (remaining : List Key) (edges : List (Key × Key)) : List Key :=
  remaining.filter (fun n => ¬ edges.any (fun e => e.1 == n && remaining.contains e.2))

/-- Kahn layering; `none` if a cycle blocks progress. -/
def kahn (edges : List (Key × Key)) : Nat → List Key → List (List Key) → Option (List (List Key))
  | 0, remaining, acc => if remaining.isEmpty then some acc.reverse else none
  | fuel + 1, remaining, acc =>
      if remaining.isEmpty then some acc.reverse
      else
        let ready := readyNodes remaining edges
        if ready.isEmpty then none
        else kahn edges fuel (remaining.filter (fun n => ¬ ready.contains n)) (ready :: acc)

/-- Stratify the derived relations into topological layers, or fail on a cycle. -/
def stratify (S : Schema) : Option (List (List Key)) :=
  kahn (depEdges S) (taintedKeys S).length (taintedKeys S) []

/-- `Stratifiable S` — the hypothesis `hStrat` carried by all theorems (§8). -/
def Stratifiable (S : Schema) : Prop := (stratify S).isSome

end Zanzibar
