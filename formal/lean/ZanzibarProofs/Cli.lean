import ZanzibarProofs.Spec.Semantics
import Lean.Data.Json

/-!
# Conformance CLI — the executable spec as a JSON oracle

`SEMANTICS.md` §10 (conformance C1). Reads a JSON request file and prints the
spec's answers, so the Python harness can compare `sem` against the oracle and the
two backends six ways.

Request format (the Python harness folds n-ary `or`/`and` into binary nodes):
```json
{ "schema": { "defs": [ [[type, rel], <expr>], ... ],
              "objectWildcards": [ [type, rel], ... ] },
  "tuples": [ {"sp":.., "st":.., "sn":.., "rel":.., "ot":.., "on":..}, ... ],
  "queries": [ {"sp":.., "st":.., "sn":.., "rel":.., "ot":.., "on":..}, ... ] }
```
`<expr>` is one of: `{"direct": [[type,pred,wild], ...]}`, `{"computed": rel}`,
`{"ttu": [targetRel, tuplesetRel]}`, `{"union": [e,e]}`, `{"inter": [e,e]}`,
`{"excl": [base, subtract]}`.

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
        let answers := qs.map (fun q => sem S T q)
        IO.println ((Json.arr (answers.map Json.bool).toArray).compress)
        pure 0
  | _ => IO.eprintln "usage: zcli <request.json>"; pure 1

end Zanzibar.Cli

/-- Executable entry point. -/
def main (args : List String) : IO UInt32 := Zanzibar.Cli.main args
