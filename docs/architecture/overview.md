# Architecture overview

Zanzibar-style relationship/permission indexing: **two evaluation backends with
identical semantics and opposite cost models**, pinned together by an independent
reference oracle and a validation matrix. Start here; go deeper per file:

| doc | covers |
|---|---|
| [`system.md`](./system.md) | the composed system: source-of-truth tuple store + log, the apply step, sync/async schedules, freshness tokens, bootstrap |
| [`graph-index.md`](./graph-index.md) | closure maintenance, path counts, wildcard split-node model, the ≤4-probe check |
| [`derived-predicates.md`](./derived-predicates.md) | boolean operators in the graph index: taint, leaf routing, the delta processor, residues |
| [`verification.md`](./verification.md) | oracle contract, validation matrix, ParityEngine, paranoia/invariants, hypothesis campaign |
| [`decision-log.md`](./decision-log.md) | load-bearing decisions + rejected alternatives, compressed from the specs |
| [`../spec-deviations.md`](../spec-deviations.md) | dated implementation record: where the builds diverged from the specs and why |
| [`../specs/`](../specs/) | the full original design specs (see "Citations" below) |

## The memoization spectrum

Same questions, same answers, opposite place to spend the work:

* **Graph index** (`index_v4/`) — memoizes *everything at write time*: the full
  transitive closure as ref-counted edges. `check` is O(1) point reads; writes pay
  O(closure delta), and boolean relations pay the delta-processor cascade on top.
* **Set engine** (`setengine/`) — memoizes *nothing across queries*: stores raw tuples
  (`TupleV1`, the repo's ground-truth table), evaluates memberships on demand with
  bitmap algebra (`MemberSet`), O(1) writes.

## Module map (live code)

```
zanzibar_utils_v1.py     shared schema layer: DSL parser -> SchemaAST; compile_ruleset ->
                         Filters/Rules (+ boolean artifacts in RuleSet.compiled);
                         SchemaInfo; identifier validation; unparse_schema_ast
index_v4/
  core.py                ReachabilityIndex: ref-counted closure, cycle pre-check,
                         _lock_store writer serialization, outbox emission (_emit)
  wildcard.py            WildcardIndex facade: bridges, ≤4-probe check (one SQL stmt),
                         derived read path (edge + residue), lookups
  processor.py           DeltaProcessor: stratified IVM cascade for boolean relations
  outbox.py              DeltaOutboxV1 helpers: watermark / rows / drain_deltas
  invariants.py          I1-I12 checker, paranoia mode, delta-scoped verifier
  models.py              StoreV4 / NodeV4 / EdgeV4(.derived) / ResidueV1 / DeltaOutboxV1
setengine/
  engine.py              SetEngine: interner (ref-counted, recycled int32 ids),
                         NodeSets, check/expand/lookup, rebuild() from TupleV1
  memberset.py           star-closed MemberSet (pos/stars/neg) algebra -- the pinned
                         star×boolean table lives here
  setops.py              pluggable SetOps seam: RoaringSets (default) / PySets
connectedstore/          the composed system (imports both backends, never imported
                         by them): SchemaV4 (write-once schema source), TupleLogV1
                         (permanent tuple log = tokens), IndexCursorV1, TupleSource
                         (validated source-of-truth writes), advance_index (THE
                         apply step), ConnectedStore (sync/async schedules,
                         freshness-gated reads, refresh(), catch_up()),
                         build_index (offline bootstrap)
legacy/                  superseded v1-v3, runnable documentation only (v1.MultiSet and
                         v2.Node are still imported by live code)
tests/
  oracle.py              INDEPENDENT reference oracle: own parser, stdlib only,
                         pointwise, boolean-aware. Ground truth for semantics.
  parity.py              ParityEngine: all backends in lockstep per op
  test_matrix.py         THE validation matrix (4-way, boolean stores included)
  snapshots/             compiled-RuleSet goldens (byte-identity gate)
```

## Key semantics (pinned -- see decision-log.md for why)

* **Strict ∀⇒∃**: no vacuous grants; a star grant reaches concretes only if instances
  exist. `'*'` queries are intensional, per branch.
* **TTU parents are STORED tupleset tuples**, never computed membership (the oracle's
  `ttu_leaf` reads raw tuples -- authentic Zanzibar). A TTU over a derived relation
  with no direct restrictions is constantly empty.
* **Raw tuples are a set** (duplicate add = idempotent no-op at the tuple API
  boundary); the graph core stays ref-counted internally because two *different* raw
  tuples can rewrite to the same derived edge.
* **Identifiers**: writes validate `[A-Za-z0-9_./@+=-]` (1-256); `*` reserved for
  wildcards, `...` for the bare subject predicate, `.` reserved in *declared relation
  names* (compiled leaf predicates are `<relation>.<index>`). Reads are lenient.
* **Validity parity**: both live backends accept/reject the same op sequences;
  rejected ops roll back completely everywhere (I12).

## Citations in code comments

Three spec series are cited by section number; all live in `docs/specs/`:

* `spec §N` in `index_v4/{core,wildcard,models}.py` and wildcard tests →
  `wildcard-materialization-spec.md`
* `spec §N` in `setengine/*` and set-engine/matrix/oracle tests →
  `set-engine-spec.md`
* `boolean spec §N` anywhere → `graph-boolean-ivm-spec.md`

Where a spec and the code disagree on a name, the code wins; behavioral divergences
from the boolean spec are recorded in `docs/spec-deviations.md`.

## Running things

Conda env named after the repo folder. Full suite is the gate (425 tests):

```
"C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe" -m pytest -q
```

Deps: `sqlmodel`, `pytest`, `pyroaring`, `hypothesis`. Paranoia mode (invariants inside
every commit) is ON by default in tests and costs ~2x runtime; `HYPOTHESIS_PROFILE=deep`
enables the heavy fuzzing profile locally.
