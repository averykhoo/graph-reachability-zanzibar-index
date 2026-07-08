import ZanzibarProofs.Core.Store
import ZanzibarProofs.GraphIndex.Closure

/-!
# The graph-index model — state, invariant, read

`SEMANTICS.md` §7. For Phase 1 the state, read function, invariant, reachability,
quiescence, and scope predicate are `opaque` placeholders so the T2/T5 statements
compile. **Phase 4 replaces them** with concrete definitions:

- `GraphState` — nodes (incl. `w_any`/`w_all`), path-counted edges (`Closure`),
  residues `(stars, neg, upos)`, outbox.
- `GraphModel.check` — the ≤4-probe read (§7.5) + derived residue path (§7.6).
- `Inv` — the I-series well-formedness (§7.7).
- `ReachedBy σ S T` — `σ` results from applying `T`'s writes (with in-txn cascade)
  from the empty state, accepted by `GraphAccepts` (§7.8).
- `Quiescent` — the cascade fixpoint (I9): a second reconcile changes nothing.
- `GraphAccepts S` — the decision-15 scope predicate `hAcc` (§8).
-/

namespace Zanzibar

/-- The materialized graph-index state. Opaque placeholder (Phase 4). -/
opaque GraphState : Type

namespace GraphModel
/-- The graph-index `check`: constant-time probes + residue (§7.5, §7.6). -/
opaque check : GraphState → Query → Bool
end GraphModel

/-- The I-series state invariant `Inv S σ` (§7.7). -/
opaque Inv : Schema → GraphState → Prop

/-- `σ` is reached by applying `T`'s writes (with in-transaction cascade) from
    empty, under a schema whose scope the graph accepts. -/
opaque ReachedBy : GraphState → Schema → Store → Prop

/-- Cascade quiescence (I9): a second full reconcile changes nothing. -/
opaque Quiescent : GraphState → Prop

/-- The graph scope predicate `hAcc` (decision 15): no object-wildcard on a derived
    relation, no wildcard userset over a derived relation, no TTU whose tupleset is
    derived. -/
opaque GraphAccepts : Schema → Prop

end Zanzibar
