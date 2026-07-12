import ZanzibarProofs.Spec.Semantics
import ZanzibarProofs.GraphIndex.Exec
import Lean.Data.Json

/-!
# Conformance CLI — the executable spec as a JSON oracle

`SEMANTICS.md` §10 (conformance C1). Reads a JSON request file and prints the
spec's answers, so the Python harness can compare `sem` against the oracle and the
two backends six ways.

Request format (the Python harness folds n-ary `or`/`and` into binary nodes):
```json
{ "mode": "spec" | "graph"  (optional, default "spec"),
  "schema": { "defs": [ [[type, rel], <expr>], ... ],
              "objectWildcards": [ [type, rel], ... ] },
  "tuples": [ {"sp":.., "st":.., "sn":.., "rel":.., "ot":.., "on":..}, ... ],
  "queries": [ {"sp":.., "st":.., "sn":.., "rel":.., "ot":.., "on":..}, ... ] }
```
`<expr>` is one of: `{"direct": [[type,pred,wild], ...]}`, `{"computed": rel}`,
`{"ttu": [targetRel, tuplesetRel]}`, `{"union": [e,e]}`, `{"inter": [e,e]}`,
`{"excl": [base, subtract]}`.

Modes (Phase 6 — graph-state conformance):
* `"spec"` (default) — answer each query with the executable spec `sem`.
* `"graph"` — run the OPERATIONAL graph model (`graphRun`: per input tuple one
  admitted logged write + one two-round cascade leg — the `ReachedBy` chain's
  own constructors, `GraphIndex/Exec.lean`), then answer each query with the
  graph read `GraphModel.check`. Errors (nonzero exit) if a write fails edge
  admission (rc 2) or the final state is not drained (rc 3) — those inputs are
  outside the proved scope and MUST NOT silently produce answers.

An unrecognized mode — a `"mode"` value that is present but not a string, or a
string other than `"spec"`/`"graph"` — is rejected with rc 4 (stderr message).
A mislabeled mode must never silently fall through to spec answers, or the
graph-vs-spec conformance pin would void.

Exit codes: 0 = answers printed · 1 = usage / JSON parse / decode error ·
2 = graph write failed admission · 3 = graph state not drained ·
4 = unrecognized mode.

Output: a JSON array of booleans, one per query. Usage: `zcli <request.json>`.
-/

open Lean

namespace Zanzibar.Cli
open Zanzibar

private def getIdx (a : Array Json) (i : Nat) : Except String Json :=
  match a[i]? with
  | some v => .ok v
  | none => .error s!"array index {i} out of bounds"

partial def decodeExpr (j : Json) : Except String Expr := do
  if let .ok r := j.getObjVal? "direct" then
    let arr ← r.getArr?
    let rs ← arr.toList.mapM (fun e => do
      let a ← e.getArr?
      pure ((← (← getIdx a 0).getStr?), (← (← getIdx a 1).getStr?), (← (← getIdx a 2).getBool?)))
    return .direct rs
  else if let .ok r := j.getObjVal? "computed" then
    return .computed (← r.getStr?)
  else if let .ok r := j.getObjVal? "ttu" then
    let a ← r.getArr?
    return .ttu (← (← getIdx a 0).getStr?) (← (← getIdx a 1).getStr?)
  else if let .ok r := j.getObjVal? "union" then
    let a ← r.getArr?
    return .union (← decodeExpr (← getIdx a 0)) (← decodeExpr (← getIdx a 1))
  else if let .ok r := j.getObjVal? "inter" then
    let a ← r.getArr?
    return .inter (← decodeExpr (← getIdx a 0)) (← decodeExpr (← getIdx a 1))
  else if let .ok r := j.getObjVal? "excl" then
    let a ← r.getArr?
    return .excl (← decodeExpr (← getIdx a 0)) (← decodeExpr (← getIdx a 1))
  else
    .error s!"unknown expr node: {j.compress}"

def decodeTuple (j : Json) : Except String Tuple := do
  pure {
    subject := { predicate := ← (← j.getObjVal? "sp").getStr?,
                 type := ← (← j.getObjVal? "st").getStr?,
                 name := ← (← j.getObjVal? "sn").getStr? },
    relation := ← (← j.getObjVal? "rel").getStr?,
    object := { type := ← (← j.getObjVal? "ot").getStr?,
                name := ← (← j.getObjVal? "on").getStr? } }

def decodeQuery (j : Json) : Except String Query := do
  pure {
    subject := { predicate := ← (← j.getObjVal? "sp").getStr?,
                 type := ← (← j.getObjVal? "st").getStr?,
                 name := ← (← j.getObjVal? "sn").getStr? },
    relation := ← (← j.getObjVal? "rel").getStr?,
    object := { type := ← (← j.getObjVal? "ot").getStr?,
                name := ← (← j.getObjVal? "on").getStr? } }

def decodePair (j : Json) : Except String (String × String) := do
  let a ← j.getArr?
  pure (← (← getIdx a 0).getStr?, ← (← getIdx a 1).getStr?)

def decodeSchema (j : Json) : Except String Schema := do
  let defsJson ← (← j.getObjVal? "defs").getArr?
  let defs ← defsJson.toList.mapM (fun e => do
    let a ← e.getArr?
    let key ← decodePair (← getIdx a 0)
    let expr ← decodeExpr (← getIdx a 1)
    pure (key, expr))
  let owJson ← (← j.getObjVal? "objectWildcards").getArr?
  let ow ← owJson.toList.mapM decodePair
  pure { defs := defs, objectWildcards := ow }

def decodeRequest (j : Json) : Except String (Schema × Store × List Query) := do
  let S ← decodeSchema (← j.getObjVal? "schema")
  let tuplesJson ← (← j.getObjVal? "tuples").getArr?
  let T ← tuplesJson.toList.mapM decodeTuple
  let queriesJson ← (← j.getObjVal? "queries").getArr?
  let qs ← queriesJson.toList.mapM decodeQuery
  pure (S, T, qs)

/-- The request mode string. `.ok "spec"` when the `"mode"` key is absent (the
    preserved default); the string value when present; `.error` when the key is
    present but not a string — a non-string `"mode"` must be rejected, never
    silently coerced to spec. Recognized-mode validation happens at dispatch. -/
def decodeMode (j : Json) : Except String String :=
  match j.getObjVal? "mode" with
  | .ok m =>
    match m.getStr? with
    | .ok s => .ok s
    | .error _ => .error s!"\"mode\" must be a string, got {m.compress}"
  | .error _ => .ok "spec"

def printAnswers (answers : List Bool) : IO UInt32 := do
  IO.println ((Json.arr (answers.map Json.bool).toArray).compress)
  pure 0

def main (args : List String) : IO UInt32 := do
  match args with
  | [path] =>
    let contents ← IO.FS.readFile path
    match Json.parse contents with
    | .error e => IO.eprintln s!"parse error: {e}"; pure 1
    | .ok j =>
      match decodeRequest j with
      | .error e => IO.eprintln s!"decode error: {e}"; pure 1
      | .ok (S, T, qs) =>
        match decodeMode j with
        | .error e => IO.eprintln s!"mode error: {e}"; pure 4
        | .ok "graph" =>
          -- Phase 6: run the operational graph model; the honesty theorems
          -- (`graphRun_reached`, `graphRun_check_eq_sem`) cover exactly what is
          -- printed here. Refuse to answer outside the proved scope.
          match graphRun S T with
          | none =>
            IO.eprintln "graph mode: a write failed edge admission \
              (input outside the add-only chain)"
            pure 2
          | some (σ, _) =>
            if drainedB S σ then
              printAnswers (qs.map (fun q => GraphModel.check σ q))
            else do
              IO.eprintln "graph mode: final state not drained \
                (outside the proved read scope)"
              pure 3
        | .ok "spec" =>
          printAnswers (qs.map (fun q => sem S T q))
        | .ok other =>
          IO.eprintln s!"unknown mode: {other} (expected \"spec\" or \"graph\")"
          pure 4
  | _ => IO.eprintln "usage: zcli <request.json>"; pure 1

end Zanzibar.Cli

/-- Executable entry point. -/
def main (args : List String) : IO UInt32 := Zanzibar.Cli.main args
