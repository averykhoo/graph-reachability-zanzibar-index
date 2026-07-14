# P13 — bulk closure builder for `build_index` (design, 2026-07-15)

Goal: make `build_index` construct the graph index's final state directly —
one in-memory pass + bulk writes — instead of replaying every tuple through
the incremental `widx.add_tuple` machinery (which pays an O(ancestors×
descendants) closure-region update + admission-grade SQL per routed triple).
**Correctness bar (chosen deliberately): the bulk-built store state is
IDENTICAL to the incremental build's, modulo auto-assigned row ids** — pinned
by a differential state-equality gate, so no new proof obligations arise: the
incremental path's entire verification story (invariants, matrix, conformance,
Lean T4's closed-form path counts) transfers by equality.

## The exact state the incremental add-only load produces (code-verified)

All references are the semantics as of 2026-07-15 (`index_v4/core.py`,
`index_v4/wildcard.py`).

1. **Nodes** (`NodeV4`): one row per distinct natural key
   `(predicate, type, name, wildcard)` appearing as a routed-triple endpoint
   or a bridge w-node. All created `implicit=True` during a load (`_resolve`
   passes no `implicit` for concretes → defaults True; w-nodes pass
   `implicit=True`). No promotion to explicit happens before `backfill()`.
   `reference_count(n)` = Σ over incident direct edges of their multiplicity
   (each direct-edge add does +1 to BOTH endpoints — `core.py`
   `_add_direct_edge_unsafe` tail; bridge adds go through the same path).
2. **Edges** (`EdgeV4`) per pair `(s, o)`:
   - `direct_edge_count` = **multigraph multiplicity** `m(s,o)`: the number of
     routed triples that added this pair (rewrite fan-in can add the same pair
     more than once — deliberate multigraph semantics, `wildcard.py add_tuple`
     docstring) plus 1 for a bridge edge (bridges are existence-checked, so
     their multiplicity is exactly 1).
   - `indirect_edge_count` = **total path count** `P(s,o)` in the direct
     multigraph: Σ over all s→o paths of the product of `m` along the path.
     The direct edge itself is a length-1 path, hence the invariant
     `indirect ≥ direct > 0 ∨ (direct = 0 ∧ indirect > 0)`; a pair exists iff
     `P > 0`. (This is the closed form the Lean T4 model states —
     `pathCount`; the incremental algorithm maintains it via
     `P(a,u)·P(v,b)` region updates.)
   - `derived = False` everywhere: a plain load routes onto storage/closure
     leaf families, never derived-public ones (`_derived_write_ctx` is False —
     `processor_writes` is unset); derived edges are written only by
     `proc.backfill()` afterwards, which is unchanged by this design.
3. **Bridges** (`_ensure_bridges`): for each concrete node whose shape
   `(type, predicate)` ∈ `schema_info.bridged_in_shapes`: direct edge
   `concrete → w_any(type, predicate)`; ∈ `bridged_out_shapes`:
   `w_all(type, predicate) → concrete`. Multiplicity 1, created lazily at the
   node's first appearance. Bridge edges participate in the closure like any
   other direct edge (they are inputs to the same DP).
4. **Position rule** (`_resolve`): subject `'*'` → `wildcard='any'` and the
   shape must be a declared subject-wildcard shape; object `'*'` →
   `wildcard='all'` and a declared object-wildcard shape; violations raise.
   Predicates normalized via `norm_pred` (Ellipsis → `'...'`).
5. **Outbox** (`DeltaOutboxV1`): `_emit` fires only on the **0→positive flip**
   of a pair's `indirect_edge_count`. An add-only load therefore emits
   **exactly one ADDED row per final closure pair**, endpoint identities
   denormalized from the (live) node rows; no REMOVED rows. Build-era outbox
   rows are never cascaded (build_index runs `backfill()` instead, and any
   later `advance_index` captures the watermark ABOVE them), so their
   **order** is inert; their **content set** is state.
6. **Cycles**: the tuple log is admission-validated (set-engine flow-graph
   parity), so the routed direct graph is acyclic; a cycle here is a
   corruption signal → `InvariantViolation`, mirroring `_apply_row`'s stance.

## Bulk algorithm (replaces only the per-tuple loop in `connectedstore/build.py`)

Everything before (watermark/schema/fresh-store guards) and after
(`backfill()`, watermark re-check, cursor) is unchanged.

- **Phase R (route, in memory):** for each `TupleV1` row in id order, run
  `ruleset.apply(triple)`; for each derived triple apply the position rule to
  get `(subject_key, object_key)` natural keys; `m[(skey, okey)] += 1`.
  Reject `skey == okey` (self-edge = trivial cycle = corruption). Identifier
  charset revalidation is skipped exactly as the N9 trusted path skips it
  (admission validated the raw tuple; `ruleset.apply` rewrites only the
  relation to a compiler-generated, charset-valid leaf predicate) — but the
  position-rule/shape checks of `_resolve` ARE replicated (they are semantic,
  not charset).
- **Phase B (bridges, in memory):** for each distinct concrete node key,
  if its shape is bridged-in: `m[(key, w_any(shape))] = max(existing, 1)`
  (i.e. add once); bridged-out: `m[(w_all(shape), key)]` likewise.
- **Phase C (cycle check):** topological sort of the direct graph; failure →
  `InvariantViolation`.
- **Phase P (path counts):** DP in reverse topological order:
  `P[a] = Σ_{v ∈ succ(a)} m(a,v) · (unit(v) + P[v])` as sparse integer
  vectors, i.e. `P(a,b) = m(a,b) + Σ_v m(a,v)·P(v,b)`. Pure integer
  arithmetic; no floats.
- **Phase W (bulk write):**
  1. INSERT all nodes (`implicit=True`,
     `reference_count = Σ_{(n,·)} m + Σ_{(·,n)} m`), flush once, collect ids.
  2. Bulk-INSERT all edges: `direct=m`, `indirect=P`, `derived=False`
     (`session.execute(insert(EdgeV4), rows)` executemany-style).
  3. Bulk-INSERT one outbox ADDED row per pair with denormalized endpoint
     identities, in deterministic `(subject_key, object_key)` sort order.
     (Order differs from the incremental discovery order — documented,
     provably inert per §5 above; the identity gate compares content as a
     multiset.)

## The identity gate (the crux — lands WITH the builder, in the same commit)

New test `tests/test_bulk_build.py`: for a corpus of schemas spanning every
state-shaping feature — plain union, computed chains, TTU, subject- and
object-wildcard shapes (bridged in/out), userset restrictions, boolean
and/but-not (backfill + residues) — generate a deterministic tuple set, build
TWO stores of the same content: (a) the incremental per-tuple loop (kept
available as `build_index(..., bulk=False)`), (b) the bulk builder. Compare
**canonical projections** (natural keys, never raw ids):

- nodes: `{(pred, type, name, wildcard): (implicit, reference_count)}` — equal.
- edges: `{(subject_key, object_key): (direct, indirect, derived)}` — equal.
- residues (post-backfill): `{object_key: (stars set, neg as subject keys,
  upos as userset keys)}` — equal. (`version` counts reconciles inside
  backfill and must also match — same backfill code runs on both sides.)
- outbox: multiset of `(subject identity, object identity, action)` — equal.

Plus: the I1–I12 invariant checker runs green on the bulk-built store, and a
read-parity spot check (grid of checks vs the oracle) on top. Any inequality
fails loudly with the differing keys.

## Lean / CORRESPONDENCE

The incremental add is the modeled algorithm (`pathCount_addEdge`); the bulk
builder is an **alternative constructor of the same modeled state**, computing
T4's closed form directly. Log in `CORRESPONDENCE.md §8.1` at landing with the
identity gate named as the net. No Lean change: no modeled definition becomes
dead code (the incremental path still runs for every online write and remains
the default apply step; only `build_index`'s loop is replaced).

## Gates before push

Identity gate (new) + split full suite + phased `verify.sh` (`lean` →
`conf-heavy` → `conf-rest`) per `docs/gate-runbook.md` + build-throughput
before/after measurement (time `build_index` bulk vs incremental at ≥2 scales,
recorded in `PERF_ANALYSIS.md`). The builder is add-only by construction
(fresh-store guard already refuses non-empty targets), so the remove-path fuzz
surface is untouched; the hypothesis cascade/stateful nets still run in the
suite.

## Rollback / escape hatch

`bulk=True` default with the incremental loop retained behind `bulk=False`
(it IS the identity gate's reference side, so it stays maintained and tested
by construction).
