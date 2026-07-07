# Boolean operators in the graph index: derived predicates

Full design: `docs/specs/graph-boolean-ivm-spec.md` (cited as `boolean spec §N`);
implementation record: `docs/spec-deviations.md`. The mechanism, end to end:

## Compile (`zanzibar_utils_v1.py`)

**Taint**: a relation is *derived* iff its AST transitively reaches an
`Intersection`/`Exclusion` through `Computed`, `TTU`, or userset restrictions
(`compute_taint`). A plain union over a boolean relation is itself derived —
otherwise its star-covered members (who have no edges) would silently vanish.
**Untainted relations compile byte-identically** to the pure-union path; the
compiled-RuleSet snapshots (`tests/snapshots/`) are the gate.

Each tainted relation compiles to a **plan tree** (`RuleSet.compiled.plans`):

* internal nodes `PUnion` / `PIntersection` / `PExclusion` (per-leaf polarity:
  negative iff under an odd number of `Exclusion.subtract` positions);
* `PClosureLeaf` — a maximal boolean-free, derived-free subtree, compiled under a
  synthetic leaf predicate `<relation>.<index>` (pre-order numbering; `.` is reserved
  in declared relation names for exactly this). **Storage leaves** (`storage=True`)
  hold Direct restrictions and are fed only by `RewriteFilter`s; **routed leaves**
  are fed only by Rules (`Computed`/`TTU` refs). Never merged — storage-leaf edges ARE
  the relation's raw stored tuples, which TTU parent enumeration depends on;
* `PDerivedComputed` / `PDerivedUserset` / `PDerivedTTU` / `PDerivedTuplesetTTU` —
  references to other derived relations, evaluated at reconcile time through their
  edge+residue state, never inlined.

Executable form: `check_fn(ctx, subject)` / `stars_fn(ctx)` are closure-composed
callables (short-circuit, no AST walk at runtime). The star fold is lifted
rule-for-rule from `MemberSet` (∪ = `|`, ∩ = `&`, ∖ = `-` over shape frozensets).

**Write routing**: users write public names only. Every matching `RewriteFilter`
fires (fan-in — `[user] and [user]` populates both leaves from one write; removes
retire symmetrically). Direct writes naming a leaf predicate or matching no
restriction are refused (`ValueError`), matching the set engine. **Exclusivity** is
enforced three ways: compile-time asserts, the façade's `processor_writes` flag
(only the processor may write derived-public families), and invariant I5.

**Stratification**: derived relations are topo-ordered by derived dependency
(`strata`); any cycle through a derived relation is a compile `ValueError`. Fan-out
tables: `dependents` (derived → its readers), `target_feeders` / `tupleset_feeders`
(untainted relations whose deltas must invalidate TTU plans).

**Scope rejections** (`UnsupportedByGraphIndex`, hooks documented in the spec):
object wildcards on derived relations; wildcard userset restrictions over derived
relations (`[T:*#P]`, P tainted). `enable_boolean=False` restores the historical
whole-schema refusal.

## Maintain (`index_v4/processor.py`)

`DeltaProcessor.run_cascade(txn_start_watermark)` runs inside the writing transaction
(synchronous v1; `_lock_store` already serializes it). Per stratum round: map the
outbox frontier to keys (§5.2), reconcile each, advance; assert quiescence after
`len(strata)` rounds.

* **Deltas are invalidation signals, never state transfers.** Concrete leaf deltas
  take the cheap path (`reconcile_subject`); symbolic (w-node) deltas, residue-version
  bumps, and dependency invalidations force **full-object reconcile** — the §5.4 rule:
  a symbolic flip must re-derive the concrete edge-holders on that object, not just
  the residue.
* **State per (object, derived relation)**: materialised **derived edges** for
  concretely-supported members (`EdgeV4.derived`, written through the ordinary façade
  path so bridges/counts/cycle-checks/delta-emission behave normally — emitted deltas
  drive the next stratum), plus one **residue** row (`ResidueV1`): `stars` =
  intensionally covered subject shapes, `neg` = star-covered-but-excluded concrete
  node ids, `upos` = userset-shaped subjects whose membership is true (edge-free —
  see below), `version` bumped on change.
* **Canonical representation** (order-independence + the space rule): star-covered
  subjects hold NO edge — they are answered by the residue (`neg` iff expr-false);
  uncovered **bare-entity** subjects hold an edge iff expr-true and are never in
  `neg`; **userset subjects never hold edges** — a derived edge from a userset node
  would leak through the closure to every member, defeating each member's own
  pointwise exclusion, so true userset memberships live in `upos` instead
  (pos-without-transitivity; blind-audit P4).
* **Reconcile is idempotent by construction**: stars via the plan's fold over
  per-branch intensional probes; `neg` recomputed from negative-leaf concretes ∪ the
  neg sets of every referenced derived leaf (exclusions propagate up strata through
  residues); edge audit over incoming concretes ∪ positive-leaf concretes ∪ neg
  candidates. I9 asserts any second reconcile changes nothing.
* The processor owns its public nodes' lifecycle: pinned non-implicit (they anchor
  residues), GC'd by the processor once neither residue nor edges remain.
* A processor write that would close a cycle is a **hard failure**
  (`InvariantViolation`), never an op rejection — stratification makes it impossible,
  so a hit means corruption.
* `backfill()` bootstraps/repairs from leaf data (per stratum, chunked, idempotent) —
  the recovery path when I9 finds an inconsistent key.

## Read (`index_v4/wildcard.py`)

```
check(s, R, o) on derived R:
    o == '*'          -> False (no object-star state can exist on derived relations)
    s == '*'          -> shape(s) ∈ residue(o,R).stars      (intensional; 1 read)
    s is a userset    -> s_id ∈ upos
                         or (shape(s) ∈ stars and s_id ∉ neg)   (residue only, no probe)
    else (bare)       -> derived edge probe (public family, probe 1 only)
                         or (shape(s) ∈ stars and s_id ∉ neg)   (≤2 point reads)
```

Ghosts have no node, so they can't be in `neg` — stars answer alone.
`lookup_reverse` renders stars as `(type, pred, 'any')` markers +
`excluded_node_ids` (= neg), and unions `upos` into the concrete ids; `lookup` adds
a residue scan (id ∈ upos, or shape ∈ stars ∧ id ∉ neg).

## Cost model (accepted prices)

| | untainted | derived |
|---|---|---|
| check | 1 edge-probe statement (≤4 keys) | ≤2 point reads (edge + residue) |
| concrete write | O(closure delta) | + O(affected keys × plan size) point reads |
| symbolic write | O(closure delta) | + full-object reconcile: O(concrete members with state on that object) — data-bounded, never universe-bounded |
| space | closure edges | + derived edges (concretely-supported only) + one residue row per (object, relation) |

Write amplification is multiplicative in strata depth — the accepted price of O(1)
reads. The outbox fixes memory, not amplification.
