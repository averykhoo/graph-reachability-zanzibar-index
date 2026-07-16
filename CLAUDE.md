# CLAUDE.md — graph-reachability-zanzibar-index

Zanzibar-style relationship/permission indexing. Two evaluation backends with **identical
semantics but opposite cost models** (a memoization spectrum), pinned together by a shared
independent reference oracle. Both backends support boolean operators (`and` / `but not`):
the set engine natively, the graph index via derived predicates maintained by a stratified
IVM delta processor.

## Start here (every session)
- **Read [`HANDOFF.md`](HANDOFF.md) first** — the mutable session state: current
  status + the open-TODO board. This file (`CLAUDE.md`) is the durable contract;
  `HANDOFF.md` is what changes session-to-session. Keep its TODO board current as
  you pick up / finish work.
- **Always run the gate before pushing.** Never push red or unverified: `pytest
  tests/` green + the phased `verify.sh` (`lean` → `conf-heavy` → `conf-rest`) all
  `PASSED` (+ a fuzz sweep for an algorithm change). The cap-safe recipe is in
  [`docs/gate-runbook.md`](docs/gate-runbook.md); details under "Running things"
  below. Commit and push **only when asked**.

## Running things
- Conda env named after the folder: `graph-reachability-zanzibar-index`.
  Interpreter: `C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe`
- The full suite is the gate (~794 tests: `tests/` 531 + `formal/conformance/` 263):
  `"$PY" -m pytest -q` from the repo root before claiming a change is done. It
  exceeds the harness's ~10-min command cap — run it **cap-safe** per
  [`docs/gate-runbook.md`](docs/gate-runbook.md): `pytest tests/` (§1) + the phased
  Lean gate below (§2).
- **Formal gate** = `bash formal/verify.sh` (Lean build + `sorry`=0 + axiom audit +
  conformance). The one-shot blows the cap; it takes a **phase arg** so an agent can
  run it unattended, in order: `verify.sh lean` → `conf-heavy` → `conf-rest` (each
  fits the cap; same anti-vacuous guards as the one-shot). **Push only after**
  `pytest tests/` + all three phases green (+ a fuzz sweep for an algorithm change).
- Deps: `sqlmodel`, `pytest`, `pyroaring` (set-engine default bitmap backend),
  `hypothesis` (property/stateful fuzzing).

## Layout / mental model
- **`index_v4/`** — the graph index. `ReachabilityIndex` (core.py) materializes the full
  transitive closure as ref-counted edges, so `check` is O(1); `WildcardIndex`
  (wildcard.py) is the wildcard-aware façade adding materialized `*` bridges and the
  derived-relation read path (edge probe + residue). **Boolean operators are supported
  as derived predicates**: `processor.py` (the delta processor: reconcile + per-stratum
  cascade over the outbox), `outbox.py` (transactional `DeltaOutboxV1` stream +
  watermark/drain helpers — write paths return None, deltas are rows), `invariants.py`
  (I1–I12 checker, paranoia mode wiring, §8.3 delta-scoped verifier), `models.py`
  (adds `EdgeV4.derived`, `ResidueV1` symbolic `(stars, neg)` state). **Offline bulk
  bootstrap for `build_index`**: `bulk_build.py` (P13/N18 bulk closure builder —
  direct in-memory closure construction) with `bulk_backfill.py` (R4-BF in-memory
  boolean Phase-D backfill).
- **`setengine/`** — the set engine. Stores only raw tuples (`TupleV1`), builds no
  closure, computes memberships on the fly with bitmap algebra, and **supports `and` /
  `but not`**.
  - `setops.py` — the pluggable `SetOps` seam: `RoaringSets` (default) / `PySets`. Never
    `isinstance`-check the underlying set type.
  - `memberset.py` — the star-closed `MemberSet` (`pos` / `stars` / `neg`) algebra.
  - `engine.py` — `SetEngine`: a reference-counted `Interner` (recycled int32 ids),
    `NodeSets`, `member_of`, `check` / `expand` / `lookup`, and `rebuild()` (replay from
    `TupleV1`).
- **`zanzibar_utils_v1.py`** — shared schema layer. Recursive-descent parser →
  `SchemaAST` (`Direct` / `Computed` / `TTU` / `Union` / `Intersection` / `Exclusion`);
  `compile_ruleset` produces the graph index's Filters/Rules **plus, for boolean
  (tainted) relations, the AOT derived-predicate artifacts** (`RuleSet.compiled`:
  plans, namespace, strata, fan-out tables; leaf routing via `RewriteFilter`s;
  `unparse_schema_ast` round-trips the AST). `UnsupportedByGraphIndex` survives only
  for scope rejections (object wildcards on derived relations, wildcard usersets over
  derived relations) and via `enable_boolean=False`; derived-dependency cycles raise
  `ValueError`. `SchemaInfo`; `validate_write_identifiers`; `.` is reserved in declared
  relation names (leaf predicates are `<relation>.<index>`).
- **`tests/oracle.py`** — independent reference oracle (pointwise, boolean-aware).
  **Independence contract:** it imports nothing from the backends and parses the DSL
  itself, so one parser bug can't corrupt both sides of the validation matrix.
- **`connectedstore/`** — the composed system (Zanzibar/Leopard split): `TupleV1` +
  permanent `TupleLogV1` = source of truth, graph index = materialized view.
  `TupleSource` (admission-validated writes returning log-id freshness tokens),
  `advance_index` (THE apply step — sync inlines it, async loops it via
  `ConnectedStore.catch_up`), `build_index` (offline bootstrap), `SchemaV4`
  (write-once schema source; compiled artifacts are cache). Composition layer only:
  it imports both backends, they never import it. Schemas are static — a new schema
  means a new store/index.
- **`legacy/`** — superseded predecessors v1–v3 (v1 in-memory; v3 the DB closure design,
  carrying a documented concurrency note that points at the v4 fix). Runnable
  documentation only — don't build on them; live code still imports `legacy.index_v1.
  MultiSet` and `legacy.index_v2.Node`.
- **Docs**: start at `docs/architecture/overview.md` (module map + pointers; the other
  architecture files cover the graph index, derived predicates, verification, and the
  decision log). Full design specs live in `docs/specs/` — code comments cite them by
  section: bare "spec §N" in `index_v4/*` → wildcard-materialization-spec.md, in
  `setengine/*` → set-engine-spec.md; "boolean spec §N" → graph-boolean-ivm-spec.md.
  Implementation divergences: `docs/spec-deviations.md`. Where a spec and the code
  disagree on a name, the code wins.

## Testing conventions
- The **validation matrix** (`tests/test_matrix.py`) is what pins "same semantics":
  handwritten expectations · oracle · set engine · graph index, compared over a full query
  grid, under **both** `SetOps`. Boolean schemas run **4-way** (graph included, processor-
  maintained, I9-audited per op).
- The **ParityEngine** (`tests/parity.py`) is the default engine for integration-style
  tests: every op fans out to all backends with unanimity, I12, and full-grid oracle
  parity asserted internally. **Paranoia mode** (default ON via `make_wildcard_index`)
  runs the invariant checker + delta-scoped verifier inside every commit; pass
  `paranoia=False` in benchmarks or when a test corrupts state on purpose.
- The **hypothesis campaign** (`tests/test_hypothesis.py`): metamorphic schema pairs,
  add/remove row-multiset restoration, permutation invariance, cascade replay-from-zero,
  generated-schema round-trips, and a stateful ParityEngine machine. Profiles: `ci`
  (default) / `HYPOTHESIS_PROFILE=deep` locally.
- Property tests reuse a shared candidate pool + grid (`tests/test_wildcard_property.py`).
- **`tests/test_lookup_oracle.py` is the lookup-surface oracle gate**: it composes
  `oracle.check` into brute-force reference lookups and pins `lookup` /
  `lookup_reverse` / `expand` on both backends. **Any strict xfail there pins a genuine
  divergence** — fix the surface and then flip the xfail; never relax the properties
  (how X1–X4 were closed; see `docs/spec-deviations.md` 2026-07-12/13).
- **Never edit a golden or oracle result just to make a refactor pass** — the oracle and
  goldens ARE the behavioral spec.

## Gotchas / invariants
- **Identifiers** are validated on writes to `[A-Za-z0-9_./@+=-]` (1–256 chars). Reserved:
  a name may be `*` (wildcard sentinel), a subject predicate may be `...` (bare). Reads are
  lenient (an out-of-charset name just never matches).
- **Object wildcards** (`folder:*`) have no DSL syntax — pass `object_wildcard_shapes` to
  `parse_openfga_schema` / `SetEngine`.
- **Set-engine ids** are recycled int32 (roaring is uint32); the `(type, name, predicate)`
  key is the stable surrogate. State is in-memory — `rebuild()` replays from `TupleV1`.
- **Concurrency**: `ReachabilityIndex._lock_store` (a `FOR UPDATE` store-row lock)
  serializes writers per store on PostgreSQL/MySQL; it's a no-op on SQLite, which
  serializes writers itself (concurrent SQLite writers need retry on `SQLITE_BUSY` /
  node-creation `IntegrityError`). Use one `Session` per thread — never share one.
- **Derived-relation exclusivity (I5)**: only the delta processor writes incoming direct
  edges on derived-public families (`WildcardIndex.processor_writes` flag); users write
  public names, `RuleSet.apply` routes them onto leaf families. A graph write on a
  boolean schema must run `DeltaProcessor.run_cascade(watermark)` in the same
  transaction (synchronous v1) — see `GraphBackend.apply` in `tests/test_matrix.py`.
- **TTU parents are STORED tupleset tuples**, never computed membership (oracle-pinned
  Zanzibar semantics): a TTU over a derived relation with no direct restrictions is
  constantly empty. Storage leaves are split from rule-routed leaves for exactly this.
- **Never edit a golden/oracle result to make a refactor pass** — and the compiled-
  RuleSet snapshots (`tests/snapshots/`) are the byte-identity gate for untainted
  compilation.
- **Perf work & the Lean model.** The Lean proofs (`formal/`) verify *algorithm-twins*
  of the Python (`formal/CORRESPONDENCE.md` is the model↔code map). A behavior-preserving
  micro-optimization needs no Lean change (the differential matrix + hypothesis +
  conformance are the net). But an optimization that **changes the modeled algorithm**
  (candidate pruning, cascade order, closure/residue update, a new fast path) makes the
  corresponding Lean definition describe dead code — update that Lean model and re-run
  `formal/verify.sh` (phased: `lean` → `conf-heavy` → `conf-rest`, per gate-runbook §2),
  or log the gap in `CORRESPONDENCE.md` §7. Don't let code and model drift unrecorded
  (`CORRESPONDENCE.md` §8).
