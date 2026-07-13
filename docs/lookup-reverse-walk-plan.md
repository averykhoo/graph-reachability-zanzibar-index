# Plan: set-engine `lookup` — O(store) sweep → O(reachable) reverse walk

**Status:** planned (not started). Baseline + root-cause in
`benchmarks/results/PERF_ANALYSIS.md` (optimization target #2). This is the next
perf task after the `direct_expand` population-copy fix (commit `78cfc2f`).

## The problem

`SetEngine.lookup` (`setengine/engine.py:821`) answers "everything the subject can
reach" with a **full-store candidate sweep**: it iterates *every* interned key and
calls `check` on each —

```python
for (t, n, p) in list(self.interner.key_of.values()):   # O(all interned nodes)
    if p == '...' or n == '*': continue
    if self.check(s_pred, s_type, s_name, p, t, n):      # each check = O(neighborhood)
        result.node_ids.add(self.interner.get(t, n, p))
```

Measured cost is **O(store)** per lookup: throughput slope −1.03 @ R²=1.000 over
1k–100k tuples (simple/gdrive), i.e. a clean linear degradation, while `check` and
`lookup_reverse` stay flat. See `PERF_ANALYSIS.md` "Scaling laws". This is the
single largest structural inefficiency in the set engine's read surface.

## What "reverse index" should (and should NOT) mean here

- ❌ **A materialized per-subject reverse index** (persist "subject → all
  (object,relation)", maintained on writes). That moves cost to write time — it is
  what the *graph index* already does, and it defeats the set engine's whole point
  (cheap writes, nothing materialized). Do not build this.
- ✅ **An on-the-fly reverse *walk*** — the dual of `expand`. Start at the subject,
  traverse membership edges *backward* to enumerate every `(object, relation)` that
  contains it. **O(reachable set)**, zero write-time cost. This is the fix.

## The infrastructure already exists

This is mostly *wiring existing pieces*, not new indexing:

- **`self.member_of`** (`engine.py:250`): `subject id -> {object-node ids it is a
  DIRECT member of}`. Already maintained on add/remove (`engine.py:335, 374`).
  Decode a node id with `self.interner.key(oid)` → `(type, name, relation)`.
  *(A node "object#relation" is interned as `(type, name, relation)`; the predicate
  slot carries the relation.)*
- **`self._object_deps`, `self._chain_targets`** (`engine.py:213`, built by
  `_candidate_reverse_deps` at `engine.py:58`): a *static* reverse schema map,
  precomputed from the AST.
  - `object_deps[(T, r)]` → relations `R` on `T` reachable from a stored `r`-tuple
    on the object (Computed chains + TTUs whose tupleset relation is `r`).
  - `chain_targets[(T, ts)]` → TTU from-chain targets over tupleset `ts`.
  - These are **already used at write time** (`_apply_add`, `engine.py:350`) to
    intern candidate object keys — which is *why* the current sweep finds
    TTU/Computed-only reachable objects. The walk reuses the same tables at *read*
    time instead.
- The current `lookup` is already a **candidate → verify** design; it just
  generates candidates by sweeping everything. We only change candidate
  *generation*.

## Algorithm (reverse BFS from the subject)

Frontier = node ids; seed with the subject. Maintain a `visited` set.

1. Seed the queue with the subject's node id (`_get_concrete`/`interner.get`).
2. Pop node `x`; for each `oid ∈ member_of.get(x, ())`, decode `(t, n, rel)`:
   a. **Emit** `(t,n)#rel` — subject is a direct member (`result.node_ids.add(oid)`).
   b. **Enqueue** `oid` if unvisited — it may itself be a userset node (e.g.
      `group:g#member`) that other objects include, so its own `member_of` must be
      walked (this is how `group#member` fan-in / userset rewrites propagate in
      reverse).
   c. **Candidate relations:** for `R ∈ object_deps.get((t, rel), ())`, the pair
      `(t,n)#R` is a *candidate*. If the relation `R`'s expression is **union-only**
      (no Intersection/Exclusion anywhere in its subtree), emit directly; otherwise
      **verify** with `self.check(subject, R, t, n)` and emit iff true.
   d. **TTU from-chain:** apply `chain_targets.get((t, ts), ())` so a stored
      tupleset tuple lets the parent reach the object as `p#target_rel`
      (mirror the forward `ttu_expand` from-chain rule, `engine.py:785`).
3. Loop to fixpoint.
4. **Stars/markers:** keep the existing `for (t, rel) in self.ast: if
   check(subject, rel, t, '*')` loop (O(declared relations) — already cheap and
   correct; it produces `result.markers`).

### Booleans — the one subtlety

`_candidate_reverse_deps` deliberately **over-approximates**: it walks subtrahends
of `but not` and all `and` branches (docstring, `engine.py:73`). So a relation
reached via one branch of an `∧`/`¬` is only a *candidate* — reaching it does not
prove membership. Hence step 2c's **verify with `check`** for any relation whose
subtree contains Intersection/Exclusion. Union-only relations are exact and need no
verify. Precompute a `set[(T, R)]` of "boolean-tainted" relations once (the schema
already distinguishes tainted relations for the compiler — reuse that) so 2c is a
cheap membership test.

**Key property:** verification runs only on the **O(reachable)** candidates the
walk surfaces — never on all O(store) objects. That is the entire win.

## Complexity

- Before: `O(|interned nodes| × check)`.
- After: `O(|reachable| × check)` + `O(declared relations)` for markers.
- For the common case (subject reaches K ≪ N objects): K vs N — the plotted win.
- Degenerate case (a "super-admin" reaching most of the store): reachable ≈ store,
  so ~current cost, never asymptotically worse.

## Correctness gate (do not weaken these)

- **`tests/test_lookup_oracle.py`** is THE lookup gate — brute-force reference
  `lookup`/`lookup_reverse`/`expand` composed from `oracle.check`, on both backends.
  A green run here proves the walk matches the pointwise semantics. Any strict xfail
  pins a real divergence — fix the walk, don't relax the property.
- `tests/test_hypothesis.py` (lookup coverage) and `tests/test_matrix.py`.
- Full suite is the gate (`pytest -q`, ~11 min, expect 794+ passed).

## Lean / CORRESPONDENCE (required — this is an algorithm change)

Unlike the `direct_expand` copy fix (behavior-preserving, no model change), this
**changes the modeled algorithm** for `lookup`. Per CLAUDE.md "Perf work & the Lean
model": update the corresponding Lean `lookup` definition to describe the reverse
walk (or, if deferring, log the gap in `formal/CORRESPONDENCE.md §7`). Read
`formal/HANDOFF.md` first; check `formal/CORRESPONDENCE.md` for the current
model↔code map for `lookup`.

## Implementation checklist

1. Read the forward duals first: `expand`/`direct_expand`/`ttu_expand`
   (`engine.py:689–804`) and the current `lookup` (`engine.py:821`) — the walk is
   their mirror.
2. Precompute the "boolean-tainted relation" set (reuse the compiler's taint info;
   see `zanzibar_utils_v1` / `RuleSet.compiled`).
3. Implement the reverse BFS as above; keep the marker loop unchanged.
4. Run `tests/test_lookup_oracle.py` first (fast, targeted), then the full suite.
5. Re-measure: `scale_bench.py` lookup should flatten (slope → ~0). Compare against
   the pre-fix rows in `scale_bench.jsonl` (keep those as the *before*; record
   *after* in `PERF_ANALYSIS.md`, do not overwrite the baseline jsonl).
6. Update the Lean `lookup` model + `formal/verify.sh` green, or log in
   `CORRESPONDENCE.md §7`.

## Risks / watch-list

- **Userset recursion:** a userset node's `member_of` must be walked, but guard with
  `visited` to avoid cycles (`group#member` self-refs, `[user, group#member]`).
- **Self-referential tuples** are supported (commit `ab3780f`) — make sure the walk
  doesn't double-count or loop on them.
- **Wildcard/star subjects** (`s_name == '*'`): mirror the current `lookup`'s
  subject-wildcard handling; the walk seed differs.
- **Object wildcards / derived-relation scope rejections** (`UnsupportedByGraphIndex`)
  are graph-index concerns — the set engine `lookup` must still cover them; the
  oracle gate will catch gaps.
- Over-approximation must never *miss* a candidate (a missed one = silently dropped
  lookup result — the X1-class bug). Prefer emitting a candidate + verifying over
  pruning aggressively.
