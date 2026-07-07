# Spec: Set-based evaluation engine (dynamic, bitmap-backed) with boolean operators

**Audience:** a coding agent working in this repository with no access to prior design discussion. The **materialized-wildcard feature is complete** (see `wildcard-materialization-spec.md`, all phases shipped plus extra tests): the repo now contains `index_v4/wildcard.py::WildcardIndex`, `SchemaInfo` in the schema layer, strict/permissive pattern matching, the reference oracle in `tests/oracle.py` with golden tests, the invariant checker, the property harness, and wildcard fixtures. Verify exact names against the repo before coding; where this spec references them, prefer the repo's actual naming. Run `pytest` first and record the baseline.

**Objective:** add a second, independent evaluation backend — `setengine` — that stores **only raw set memberships** (tuples), builds no closure, and computes memberships on the fly with bitmap algebra. It supports everything the graph index supports (unions, userset rewrites, `from` chains, all wildcard semantics) **plus** boolean operators `and` and `but not`. Reads are O(schema depth × topology) with bulk set work vectorized; writes are O(1) updates. Deltas (`PermissionDelta`) are explicitly not provided by this backend.

**Positioning (put this in the README):** the two backends are endpoints of one memoization spectrum — the graph index memoizes everything at write time (closure), the set engine memoizes nothing across queries. Same semantics, opposite cost model. The validation matrix (§7) is what pins "same semantics."

---

## 1. Decisions (made; do not relitigate)

1. **Set representation: pluggable, roaring by default.** All set state and algebra go through a thin seam — two interchangeable implementations selected at engine construction:
   - `RoaringSets`: `pyroaring.BitMap` / `FrozenBitMap` (add `pyroaring` to requirements). 32-bit ids only — fine, the intern table issues sequential int32s.
   - `PySets`: builtin `set` / `frozenset`.
   Both already share the needed operator surface (`in`, `|`, `&`, `-`, `add`, `discard`, iteration, `len`, bool), so the seam is a factory pair, not a class hierarchy:
   ```python
   @dataclass(frozen=True)
   class SetOps:
       new: Callable[[Iterable[int]], MutSet]      # BitMap / set
       freeze: Callable[[Iterable[int]], FrozSet]  # FrozenBitMap / frozenset
   ```
   Rationale for the seam: builtin `set` is typically **faster for small sets and membership-heavy work** (no C-boundary crossing per op, no bitmap construction); roaring wins on **large populations, bulk union/intersection/difference, and memory**, which is exactly the `expand` path. The engine's `check` mode is membership-heavy; its `expand` mode is bulk-heavy. Ship both, default roaring, and let the benchmark (§8) inform per-deployment choice. Never write `isinstance` checks against either type.
2. **Source of truth: a new raw-tuple table, not JSON, not the edge tables.** Add `TupleV1` (SQLModel, same session idioms as the rest of the repo): `(id, store_id, subject_predicate, subject_type, subject_name, relation, object_type, object_name)` with a uniqueness constraint over the septuple per store. The graph index stores *derived* edges (post-`RuleSet.apply`), so it cannot serve as ground truth for a rewrite-free engine; JSON dumps of bitmaps are opaque and duplicate state. The tuple table is the missing primitive: the set engine rebuilds its in-memory state from it on open (replay), the oracle reads the same rows, and the validation harness gets one canonical op log. `WildcardIndex` internals are **not** refactored (that feature is done and tested); the harness applies each op to both backends side by side (§7.1).
3. **Engine state is in-memory, rebuilt on open.** Bitmap snapshotting via `BitMap.serialize()` blobs is a documented non-goal/hook, not built now.
4. **Per-query memoization only.** A memo dict lives for the duration of one query (or one explicit batch call). Cross-query caching with version counters is a documented non-goal/hook — implementing it is walking back toward the closure index and needs invalidation machinery this phase should not carry.
5. **Write-validity parity with the graph backend.** The set engine could technically evaluate some inputs the graph index rejects (e.g. same-shape wildcard self-reference like `group:*#member member group:g`, which the graph rejects via cycle detection). Reject them here too, with equivalent errors, so the 4-way matrix compares identical stores. Cycles among usersets: rejected at write via a DFS over the stored membership topology (§6.2). A parity test asserts both backends accept/reject the same op sequences.

---

## 2. Parser and AST (prerequisite for both oracle and engine)

The schema layer currently compiles relation definitions (union semantics) into Filters/Rules, and — from the completed wildcard work — emits `SchemaInfo`. Split parsing from compilation:

### 2.1 Expression AST

```python
# leaves
Direct(restrictions=[...])          # [user], [user:*], [group#member], [group:*#member]
Computed(relation)                  # define viewer: editor
TTU(target_rel, tupleset_rel)       # define viewer: viewer from parent_folder
# operators
Union(children) | Intersection(children) | Exclusion(base, subtract)
```

`SchemaAST = dict[(object_type, relation), Expr]`, produced for every schema. `SchemaInfo` derivation moves onto/next to the AST unchanged.

### 2.2 Grammar

Replace the `' or '` string-split with a small recursive-descent parser:

```
expr    := chain ('but not' chain)?          # at most one exclusion, loosest binding
chain   := unit (OP unit)*                   # OP homogeneous: all 'or' or all 'and'
unit    := '(' expr ')' | leaf
leaf    := type-restriction-list | REL | REL 'from' REL
```

Mixing `or` and `and` in one chain without parentheses is a **schema error** with a message naming the relation. Both sides of `but not` may be chains or parenthesized exprs. Verify the grammar accepts the existing `tests/fga_schemas/demorgans_*.fga` fixtures **before** finalizing — read those files first and adjust if they use a construct this grammar misses; they are the authoritative examples.

### 2.3 Compilation split

`compile_ruleset(ast, schema_info) -> RuleSet` produces exactly today's Filters/Rules for pure-union definitions (all current fixtures except the demorgans ones), and raises `UnsupportedByGraphIndex` naming the relation when the AST contains `Intersection`/`Exclusion`. All existing graph-backend tests must stay green through this refactor — they are the regression net. Add a test asserting the loud failure for boolean schemas (the graph backend must never silently mis-ingest one). The old xfail parser test is superseded: parsing demorgans now succeeds; replace it per §7.4.

---

## 3. Oracle upgrade (pointwise refactor + booleans)

The oracle currently expands objects into an intensional triple `(users, usersets, markers)` under union semantics. **Do not extend the set algebra to booleans** — set-difference over intensional triples is a bug farm (e.g. `users₁ − users₂` ignores that a star marker in branch 2 excludes concrete users of that type). Refactor to **pointwise evaluation**: the oracle answers one `(subject, relation, object)` at a time by recursing over the AST, memoized per query on `(subject, object_node, relation)` with a visited-set for recursion safety.

```python
def oracle_check(ast, schema_info, tuples, subject, rel, o_type, o_name) -> bool:
    # Union → any(child); Intersection → all(child); Exclusion → base and not subtract
    # Direct leaf, for THIS subject:
    #   concrete-entity subject u: tuple (u, rel, obj) exists
    #     or (star tuple (S:*, rel, obj) exists and u.type == S)          # ghost-safe
    #     or (userset tuple (t,n,P → rel, obj) exists and oracle_check(..., u, P, t, n))
    #     or (userset-star tuple (S:*#P) exists and any(oracle_check(u,P,S,g) for g in universe(S)))
    #   userset subject (t,n,P): the (t,n,P) tuple exists directly, or (t:*#P) star exists,
    #     or reachable transitively through userset tuples (recurse)
    #   star subject '*': the matching star tuple of this shape exists (intensional, per-branch)
    # object-side: tuples matching object include (…, rel, o_type, '*') when o_name != '*';
    #   when o_name == '*', ONLY star-object tuples match (intensional)
    # TTU leaf: for each tuple (p, tupleset_rel, obj-or-obj-star):
    #   concrete p → oracle_check(subject, target_rel, p)
    #   star p (S:*) → any over universe(S) instances, plus star-subject match for
    #   userset/'*' subjects of shape (S, target_rel)
```

Universe rule is unchanged from the wildcard spec (tuple-mentioned names ∪ query endpoints). **All existing oracle golden and property tests must pass unmodified against the refactored oracle** — they are the spec of the union+wildcard fragment; do not "fix" a golden to make the refactor pass.

**Star × boolean query semantics (pin as a table in the oracle docstring and README):** for a `'*'`-named query subject, evaluation is intensional per branch — `'*' ∈ A∧B` iff star-covered in both, `'*' ∈ A−B` iff star-covered in A and **not** star-covered in B (a concrete-only exclusion like "except bob" does not defeat the star query). Concrete and ghost subjects are unaffected by this convention (for them, exclusion is genuine pointwise membership). The set engine's `MemberSet` (§5) reproduces exactly this by construction; a shared test module asserts oracle ≡ MemberSet-algebra on these corners.

Add boolean golden tests: hand-computed De Morgan scenarios over the demorgans fixtures (expected booleans written by a human with reasoning in comments), plus at least one star-inside-exclusion scenario (`[user:*] but not blocked`, blocked concrete; check a ghost user ⇒ True, check the blocked user ⇒ False).

---

## 4. `MemberSet` — the star-closed set algebra

Plain bitmaps can't represent "all users except bob." The closed form:

```python
@dataclass(frozen=True)
class MemberSet:
    pos: FrozSet                              # concrete member ids
    stars: frozenset[tuple[str, str]]         # shapes: (type, pred); pred '...' for bare
    neg: FrozSet                              # exclusions, meaningful only within starred shapes

    # semantics: pos ∪ (⋃ population(shape) for shape in stars) − neg,  pos wins over neg
    def contains_entity(self, uid, utype) -> bool: ...
    def contains_userset(self, uid, shape) -> bool: ...
    def contains_star(self, shape) -> bool:   # intensional: shape in stars
```

Implement `union`, `intersect`, `subtract` as pure functions over `(pos, stars, neg)` given `ops: SetOps` and the population masks (`ids_of_type[t]`, `ids_of_shape[(t,p)]` — maintained append-only at intern time):

- **union:** `pos = pos₁|pos₂` (then `- neg` overlap resolution: an id in `pos` of either side survives); `stars = stars₁|stars₂`; per shape starred on both sides `neg = neg₁&neg₂`, starred on one side `neg = that side's neg − pos_other − (mask if other starred…)` — derive carefully and let the property test be the judge.
- **intersect:** `stars = stars₁∩stars₂`; rescue `pos₁ & (⋃ masks of stars₂ − neg₂)` and symmetric, plus `pos₁&pos₂`; `neg = (neg₁|neg₂)` within surviving stars.
- **subtract:** subtracting a starred shape removes that shape's star and its masked concretes from `pos`; subtracting concretes under your own star adds to `neg` (minus your `pos`).

Do **not** trust the sketches above as final: the acceptance test for this module is a **brute-force property test** over a small universe (≤3 types, ≤8 entities each, ≤2 shapes) — enumerate random `MemberSet`s, materialize each extensionally as a plain frozenset over the universe (star ⇒ whole population), and assert `materialize(op(a,b)) == op(materialize(a), materialize(b))` for all three ops plus `contains_*` agreement, including the intensional `contains_star` per the §3 table. Run the property suite under **both** `SetOps` implementations. This module has no engine dependencies; build and land it first within its phase.

---

## 5. Engine storage model (`setengine/` package)

```python
class Interner:            # per store; append-only
    id_of: dict[tuple[str, str, str], int]     # (type, name, pred) → int32
    key_of: list[tuple[str, str, str]]
    ids_of_type: dict[str, MutSet]             # concrete entity ids (pred '...')
    ids_of_shape: dict[tuple[str, str], MutSet]# concrete userset ids per (type, pred)

class NodeSets:            # per userset id (object side of tuples)
    entities: MutSet       # direct concrete-entity subject ids + bare-star sentinel ids
    usersets: MutSet       # direct userset subject ids + userset-star sentinel ids

member_of: dict[int, MutSet]   # subject id → userset ids it appears in directly (reverse)
```

Star nodes intern like anything else — `(T, '*', pred)` — and **no any/all split is needed**: that split existed to separate bridge edges from grant edges in the graph; here the role of a star id is unambiguous from which side of storage it sits on (as a *subject* it's a sentinel inside some node's `entities`/`usersets`; as an *object* it's a `NodeSets` key holding star-object grants). Call this simplification out in the module docstring.

The `entities`/`usersets` split is a performance invariant, not cosmetics: evaluator recursion iterates only `usersets` (small, topology-shaped, Python-level loop), while `entities` bitmaps (potentially huge populations) are only ever combined by C-level bulk ops. Preserve it everywhere.

---

## 6. Engine behavior

### 6.1 Writes

`add_tuple` / `remove_tuple`: validate (§6.2) → insert/delete the `TupleV1` row → update the three in-memory structures (`NodeSets` of the object node, `member_of` of the subject, interner masks on first sight). No rewrite expansion, no derived state — `RuleSet.apply` is not called; the schema is consulted only at read time. Removing the last tuple touching a node may leave empty sets; leave them (no GC needed — nothing derived exists to leak). Deltas: return `[]`, docstring stating this backend does not compute deltas.

### 6.2 Validation (parity with graph backend)

Reuse the schema layer's strict Filters for type-restriction validity (`[user]` rejects `user:*`; declarations gate star tuples in both positions via `SchemaInfo`) — call the same code, don't reimplement. Add cycle rejection: before inserting, DFS from the object node through `member_of`-inverse (i.e., would the new subject node be reachable *from* the object through existing userset membership edges, treating star sentinels as connecting to their shape's population per the §4 semantics); on hit, raise the same error type/message family the graph backend raises for cycles. Acceptance: a parity test running randomized op sequences (including the known-rejected self-referential star tuples) through both backends and asserting identical accept/reject outcomes and store contents on reject (rollback).

### 6.3 Evaluator — two modes, one skeleton

```python
def check(subject, rel, o_type, o_name, *, memo, stack) -> bool     # pointwise, short-circuits
def expand(rel, o_type, o_name, *, memo, stack) -> MemberSet        # bulk, memoized FrozSets
```

Shared structure over the AST: `Union → any/⋃`, `Intersection → all/∩`, `Exclusion → (base ∧ ¬sub)/(base − sub)`. Leaves:

- **Direct:** local sets of `(o_type, o_name, rel)` **plus**, if `(o_type, rel) ∈ object_wildcard_shapes`, local sets of the star object `(o_type, '*', rel)` — this is also what answers ghost objects (unknown `o_name` ⇒ empty local, star part still applies; never intern on read). Bare-star sentinels in `entities` → add shape to `MemberSet.stars` / match any subject of that type in check mode. Userset-star sentinels → add shape to `stars` **and** extensionally union `expand` over `ids_of_shape[(S,P)]` (strict ∀⇒∃ falls out: empty population contributes nothing extensional; the marker still answers ghost-userset and `'*'` queries — mirroring the completed graph feature's probes-plus-bridges exactly). Concrete userset members → recurse.
- **Computed(r2):** recurse with `rel=r2`, same object.
- **TTU(P, R2):** iterate `entities` of `(o_type, o_name, R2)` (∪ its star object if declared): concrete parents recurse with `(P, parent)`; a bare-star parent sentinel of type S → shape-star `(S, P)`: marker + extensional union over `ids_of_shape[(S, P)]`… note the population here is *usersets of shape (S,P)*, whose members come from recursing `expand(P, S, name)` per instance — bounded by real data, still no closure.

Check mode is the same recursion answering only the queried subject: membership tests against stored bitmaps, `any()` over small `usersets` iterations, star handling per the §3 semantics table. `stack` guards cycles defensively (writes already reject them, but the evaluator must not infinite-loop on a corrupted store — raise, don't hang). Memoized `expand` results are `FrozSet`/`MemberSet` keyed by `(object_id_or_key, rel)`; a fresh memo per public call.

### 6.4 Lookups

- `lookup(subject)` ("what can alice reach"): seed = `member_of[alice] ∪ member_of[star sentinel of her shape]`; propagate upward through schema implications in reverse (direct→its relation; `Computed` reversed; `TTU` reversed via the parent's `member_of` on the tupleset relation), collecting candidate `(object, relation)` pairs from **positive** branches only (union/intersection members and exclusion *bases* — never subtrahends); then **verify each candidate with check mode** (the semi-join). Booleans make candidate generation unsound as a final answer; verification makes it correct. Return concrete results plus symbolic markers ("all T", "any T#P") mirroring `LookupResult` from the wildcard work.
- `lookup_reverse(rel, object)` = `expand` rendered as `LookupResult` (concretes from `pos`/extensional parts, markers from `stars` minus obvious `neg` notes).

### 6.5 Backend protocol

Expose `SetEngineBackend` implementing the same protocol the integration tests use for `V4WildcardBackend` (`add_tuple/remove_tuple/check/lookup/lookup_reverse`, construction from `(session, store_id, schema)`), plus `rebuild()` (replay `TupleV1`). A test asserts open-replay equivalence: apply ops → snapshot answers over a grid → discard engine → rebuild from table → identical answers.

---

## 7. Validation matrix

### 7.1 Harness

Extend the existing property harness (from the wildcard phases) rather than writing a new one:

- A `MultiBackend` test helper fans each op out to every backend under test and asserts unanimous accept/reject.
- Store classes: **union+wildcard fixtures** (existing `wildcards.fga` etc.) → **4-way**: handwritten expectations, oracle, set engine, graph `WildcardIndex`. **Boolean fixtures** (demorgans trio + new `boolean_wildcards.fga` mixing `[user:*]`, `but not`, `and`, and a `from` chain) → **3-way**: handwritten, oracle, set engine; plus the §2.3 assertion that graph compilation refuses the schema.
- After every op, compare `check` across backends over the full grid (universe ∪ one ghost per type ∪ `'*'` names, per the existing harness's grid builder), and run the graph invariant checker on the graph backend as before. On mismatch, print the op sequence and the disagreeing triple (shrinking = the printed replay).
- Run the whole matrix under both `SetOps` implementations (parametrize; roaring and builtin must be indistinguishable).

### 7.2 Handwritten expectations

A declarative scenario format (python data or YAML in `tests/scenarios/`): `{schema: <fixture>, ops: [add/remove tuples...], expect: [(subject, rel, object, bool), ...]}` executed against every applicable backend **and** the oracle. These are the human anchor of the matrix — expected values computed by hand with a comment justifying each non-obvious one. Minimum new scenarios: De Morgan pair equivalence with absolute values (not just pairwise equality); `(A and B)` where membership arrives via different mechanisms per branch (direct vs `from` chain); `[user:*] but not blocked` incl. ghost; exclusion whose subtrahend is star (`[user] but not [user:*]`-style ⇒ empty for concretes, per the §3 table for `'*'`); intersection with an empty branch.

### 7.3 Equivalence properties

For the demorgans fixtures, add the *property* form: for all grid points, `check(lhs_relation) == check(rhs_relation)` on oracle and set engine. This is the test the original xfail was gesturing at.

### 7.4 xfail retirement

Delete/replace the old `test_demorgans_parses` xfail with: (a) parser unit tests over the demorgans fixtures asserting AST shape, (b) the §7.3 property, (c) the §2.3 graph-refusal test.

---

## 8. Benchmark (`benchmarks/set_engine_bench.py`)

Not CI; a script printing a table. Axes: `SetOps` impl × workload. Workloads: (a) deep/narrow — many small usersets, nesting depth 8, check-heavy; (b) wide/flat — 3 relations, entity populations 10⁵–10⁶, star + exclusion, expand-heavy; (c) mixed batch — 10⁴ checks reusing one memo. Report ops/sec and peak RSS. Also include one comparison column running the same (a) workload against the graph backend for read *and* write, to make the memoization-spectrum trade concrete in the README. Seeded, deterministic sizes via CLI flags.

---

## 9. Phase plan (each phase ends with the full suite green)

- **P0 — Parser/AST/compile split (§2).** Graph tests green unchanged; boolean schemas parse; `compile_ruleset` refuses booleans loudly; demorgans fixtures read and covered by parser unit tests.
- **P1 — Oracle pointwise refactor + boolean goldens (§3).** All existing oracle tests pass unmodified; new goldens pass; star×boolean semantics table documented.
- **P2 — `SetOps` + `MemberSet` (§1.1, §4).** Brute-force property suite green under both impls. No engine imports.
- **P3 — Storage & writes (§5, §6.1–6.2, `TupleV1`).** Replay-equivalence test; accept/reject parity test vs graph backend.
- **P4 — Evaluator & lookups (§6.3–6.5).** Named scenario tests green on the set engine.
- **P5 — Validation matrix (§7).** 4-way and 3-way suites green under both `SetOps`; xfail retired; harness parametrized over backends.
- **P6 — Benchmark + README (§8).** Spectrum framing, cost model, non-goals, star×boolean table, delta caveat.

## 10. Non-goals (documented hooks only)

Cross-query caching / version-counter invalidation; bitmap snapshot persistence (`serialize()` blobs); deltas from the set engine; wiring the graph backend through `TupleV1` (harness-level fan-out only — `WildcardIndex` is finished code, leave it); boolean support in the graph backend (a future check-time expression layer over `WildcardIndex.check`; the shared AST from §2 is deliberately the artifact it will consume); 64-bit id space (`BitMap64`); any query-time node interning.
