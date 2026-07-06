# CLAUDE.md — graph-reachability-zanzibar-index

Zanzibar-style relationship/permission indexing. Two evaluation backends with **identical
semantics but opposite cost models** (a memoization spectrum), pinned together by a shared
independent reference oracle.

## Running things
- Conda env named after the folder: `graph-reachability-zanzibar-index`.
  Interpreter: `C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe`
- The full suite is the gate (300+ tests): run
  `"C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe" -m pytest -q`
  from the repo root before claiming a change is done.
- Deps: `sqlmodel`, `pytest`, `pyroaring` (set-engine default bitmap backend).

## Layout / mental model
- **`index_v4/`** — the graph index. `ReachabilityIndex` (core.py) materializes the full
  transitive closure as ref-counted edges, so `check` is O(1); `WildcardIndex`
  (wildcard.py) is the wildcard-aware façade adding materialized `*` bridges.
  **No boolean operators** (it can't represent negation).
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
  `compile_ruleset` produces the graph index's Filters/Rules and **raises
  `UnsupportedByGraphIndex` on booleans**; `SchemaInfo`; `validate_write_identifiers`.
- **`tests/oracle.py`** — independent reference oracle (pointwise, boolean-aware).
  **Independence contract:** it imports nothing from the backends and parses the DSL
  itself, so one parser bug can't corrupt both sides of the validation matrix.
- **`index_v1/2/3.py`** — superseded predecessors (v1 in-memory; v3 the DB closure design,
  carrying a documented concurrency note that points at the v4 fix). Don't build on them.
- Design source-of-truth: the spec markdown (`wildcard-materialization-spec.md` and
  `set-engine-spec.md`; the code's `spec §N` citations point at the latter). Where a spec
  and the code disagree on a name, the code wins.

## Testing conventions
- The **validation matrix** (`tests/test_matrix.py`) is what pins "same semantics":
  handwritten expectations · oracle · set engine · graph index, compared over a full query
  grid, under **both** `SetOps`. Boolean schemas are 3-way (the graph refuses them).
- Property tests reuse a shared candidate pool + grid (`tests/test_wildcard_property.py`).
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
