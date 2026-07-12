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
* `"graph-state"` — run the SAME `graphRun` fold under the SAME rc 2/3 gates,
  but instead of query answers emit the final materialized state as canonical
  JSON: `{"edges": [...], "residues": [...]}` (state-LEVEL conformance,
  FINAL_REVIEW §4(a)). Queries in the request are ignored. Canonical form and
  the documented projections:
    - `edges`: the direct-edge SET (each `[[type,name,pred,variant],
      [type,name,pred,variant]]`, variant in `""`/`"any"`/`"all"` — the Python
      `NodeV4.wildcard` encoding), sorted + deduplicated. Deduplication is a
      documented projection: the model's edge LIST carries multiplicity where
      Python ref-counts one `EdgeV4` row (`direct_edge_count`), so the
      comparison is at set level on both sides.
    - `residues`: every persisted residue row as `[[type,objName,relation],
      stars, neg, upos]` with `stars` a sorted list of `[type,pred]` shapes and
      `neg`/`upos` sorted lists of `[type,name,pred]` subjects. Rows are
      emitted RAW, including all-empty rows the model stores where Python
      deletes them (`_store_residue`, `processor.py` — "empty residues are
      deleted, never stored"); the Python-side comparison applies that
      documented drop-empty projection, so the divergence stays observable
      here.
    - residue-key enumeration honesty: `GraphState.residue` is a function, so
      the dump enumerates candidate keys `objNode ⟨dt, on⟩ R` over every
      derived `(dt, R)` in the schema and every name occurring in the
      accumulated store or in `σ.nodes` (incl. `'*'`). That is exhaustive for
      the operational chain: `putResidue` is reached only through the cascade's
      job keys, whose object names come from outbox-delta nodes — all created
      by `writeDirect` (hence in `σ.nodes`/the store) — and from edge endpoints
      (in `σ.nodes` by `edgesClosed`).

An unrecognized mode — a `"mode"` value that is present but not a string, or a
string other than `"spec"`/`"graph"`/`"graph-state"` — is rejected with rc 4
(stderr message). A mislabeled mode must never silently fall through to spec
answers, or the graph-vs-spec conformance pin would void.

Exit codes: 0 = answers/state printed · 1 = usage / JSON parse / decode error ·
2 = graph write failed admission · 3 = graph state not drained ·
4 = unrecognized mode.

Output: a JSON array of booleans, one per query (spec/graph modes), or the
canonical state object (graph-state mode). Usage: `zcli <request.json>`.
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

/-! ## Graph-state dump (mode `"graph-state"`) — driver-level, like the modes
above; the projections it applies are enumerated in the file header. -/

/-- The Python `NodeV4.wildcard` encoding of a node variant (`models.py:46`). -/
def variantStr : Variant → String
  | Variant.plain => ""
  | Variant.wAny => "any"
  | Variant.wAll => "all"

/-- A node key as `[type, name, pred, variant]`. -/
def nodeKeyJson (k : NodeKey) : Json :=
  Json.arr #[Json.str k.type, Json.str k.name, Json.str k.pred,
             Json.str (variantStr k.variant)]

/-- A direct edge as `[subjectNode, objectNode]`. -/
def edgeJson (e : NodeKey × NodeKey) : Json :=
  Json.arr #[nodeKeyJson e.1, nodeKeyJson e.2]

/-- A residue subject as `[type, name, pred]`. -/
def subjectJson (s : SubjectRef) : Json :=
  Json.arr #[Json.str s.type, Json.str s.name, Json.str s.predicate]

/-- A star shape as `[type, pred]`. -/
def shapeJson (sh : Shape) : Json :=
  Json.arr #[Json.str sh.1, Json.str sh.2]

/-- Canonicalize a JSON list: sort by compressed rendering (deterministic — the
    rendering is injective on values), drop exact duplicates. -/
def canonJsonArr (l : List Json) : Json :=
  let tagged := (l.map (fun j => (j.compress, j))).mergeSort
    (fun a b => (compare a.1 b.1).isLE)
  let rec dedup : List (String × Json) → List Json
    | [] => []
    | [x] => [x.2]
    | x :: y :: rest =>
        if x.1 == y.1 then dedup (y :: rest) else x.2 :: dedup (y :: rest)
  Json.arr (dedup tagged).toArray

/-- All persisted residue rows, enumerated over the candidate-key superset
    (see the header's enumeration-honesty note): derived `(dt, R)` defs ×
    every name in the accumulated store or in `σ.nodes` (incl. `'*'` — a
    wAll-keyed row, though unreachable for the chain, must not be silently
    missed if it ever appeared). All-empty rows are emitted too — dropping
    them is the Python side's documented projection, not ours. -/
def stateResidues (S : Schema) (σ : GraphState) (T : Store) : List Json :=
  let names := T.flatMap (fun t => [t.subject.name, t.object.name])
               ++ σ.nodes.map NodeKey.name
  S.defs.flatMap fun d =>
    if isDerived S d.1 then
      names.filterMap fun n =>
        match σ.residue (objNode ⟨d.1.1, n⟩ d.1.2) d.1.2 with
        | some res => some (Json.arr #[
            Json.arr #[Json.str d.1.1, Json.str n, Json.str d.1.2],
            canonJsonArr (res.stars.map shapeJson),
            canonJsonArr (res.neg.map subjectJson),
            canonJsonArr (res.upos.map subjectJson)])
        | none => none
    else []

/-- The canonical final-state object (mode `"graph-state"`). -/
def stateJson (S : Schema) (σ : GraphState) (T : Store) : Json :=
  Json.mkObj [
    ("edges", canonJsonArr (σ.edges.map edgeJson)),
    ("residues", canonJsonArr (stateResidues S σ T))]

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
        | .ok "graph-state" =>
          -- Same driver + same rc 2/3 gates as graph mode; emits the final
          -- state instead of answers (queries ignored). The store passed to
          -- the residue enumeration is the chain store the driver accumulated.
          match graphRun S T with
          | none =>
            IO.eprintln "graph-state mode: a write failed edge admission \
              (input outside the add-only chain)"
            pure 2
          | some (σ, Tc) =>
            if drainedB S σ then do
              IO.println (stateJson S σ Tc).compress
              pure 0
            else do
              IO.eprintln "graph-state mode: final state not drained \
                (outside the proved read scope)"
              pure 3
        | .ok "spec" =>
          printAnswers (qs.map (fun q => sem S T q))
        | .ok other =>
          IO.eprintln s!"unknown mode: {other} \
            (expected \"spec\", \"graph\", or \"graph-state\")"
          pure 4
  | _ => IO.eprintln "usage: zcli <request.json>"; pure 1

end Zanzibar.Cli

/-- Executable entry point. -/
def main (args : List String) : IO UInt32 := Zanzibar.Cli.main args
