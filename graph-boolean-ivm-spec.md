# Spec v1.1: Boolean operators in the graph index via stratified IVM (derived predicates + star residues)

**You are an autonomous coding agent (Claude Code) working in this repository.** This spec was produced across a long design conversation with the repo's author; that conversation is not in your context — this document carries its conclusions. You are trusted to adapt: prefer the intent and rationale here over line-level prescriptions when the two conflict with repo reality.

## §0 How to work — precedence, adaptation charter, workflow

**Precedence.** For *facts* (names, signatures, file layout, what exists), the repo wins — verify every claim here before relying on it. For *decisions, semantics, and invariants*, this document wins over your instinct to redesign: the obvious alternatives were considered and rejected, and the rejections are recorded so you don't re-walk them.

**Frozen (change only by stopping and asking the user):**
- Pinned semantics (§7) — including the star×boolean table, strict ∀⇒∃, ghost rules, intensional `'*'`, and the self-referential-wildcard rejection.
- The O(1) read property: `check` is a constant number of point reads on any relation, no recursion, no set operations at read time.
- Validity parity: every backend accepts/rejects the same op sequences; rejected ops roll back completely on all backends.
- Deltas are invalidation signals, never state transfers (§5).
- Consistency is synchronous in v1 (cascade inside the write transaction).
- The exclusivity invariant: the processor is the only writer of incoming direct edges on derived-public node families.
- The acceptance event: boolean fixture stores flip from 3-way to 4-way in the validation matrix.

**Adaptable (use judgment, record in a deviations log):** all concrete names, signatures, table/column layouts, SQL idioms, module placement, phase-internal ordering, and any mechanism marked *(adapt)*. If the repo has visibly moved past something here, or you find a better local fit that preserves the frozen list, take it — and append a dated entry to `docs/spec-deviations.md` saying what changed and why. If a *frozen* item seems wrong or impossible, stop and surface it; do not silently comply or silently diverge.

**Workflow.** (1) Run the full test suite first; record the green baseline. (2) Read `wildcard-materialization-spec.md` and `set-engine-spec.md` if present — this spec is the third in that series and follows their conventions. (3) Work the phases in §11 in order; each phase lands green before the next begins; commit per phase. (4) Never weaken an existing assert or test to make something pass. (5) When the matrix disagrees, the oracle is ground truth; an engine is wrong until proven otherwise. (6) Snapshot-style regression: before touching compilation, capture `repr` of the compiled output for every pure-union fixture schema; after, they must be byte-identical.

## §1 Decisions (made; do not relitigate)

1. **Boolean relations become derived predicates materialized as ordinary edges in the *same* closure index**, maintained by a delta processor consuming the closure's own `PermissionDelta` stream. Strata are logical (namespaced predicate families), never physical: one store, one closure, one transaction. Physically separate per-relation graphs were rejected — they fracture atomicity and prevent derived edges from re-entering the closure that downstream rewrites read.
2. **Rejected: check-time expression evaluation** as the primary mechanism — it cannot support anything downstream of a boolean relation (TTU over a boolean `viewer`, `[doc#viewer]` restrictions, nested booleans). Materialization dissolves all of that: derived edges are real, flow through rewrites, and emit their own deltas, which drive the next stratum.
3. **Rejected: reachability labelings and per-object bitmaps as primary storage.** Interval/2-hop/PLL labelings have non-constant queries and degrade badly under deletion; bitmaps store the same relation with worse delete semantics (a bit cannot be ref-counted). Path-counted edge rows are the query-optimal corner's best dynamic form; under OMv-style lower bounds there is no structure with both fast updates and fast queries — the corner is chosen deliberately.
4. **Taint propagates.** A relation is **derived** iff its AST transitively reaches an `Intersection`/`Exclusion` through `Computed`, `TTU`, or userset `Direct` restrictions. Rationale: star-covered members have no edges, so a plain union over a boolean relation compiled normally would silently drop them (§3.1). Untainted relations compile byte-identically to today.
5. **Symbolic wildcard state is a persisted residue** per `(object node, derived relation)`: a small `(stars, neg)` record consulted by `check` alongside the edge probe. Not derived w-edges (splits one relation's symbolic state across two writers + bridge-GC interactions), not extensional expansion (unbounded, ghost-wrong, and cycle-creating for self-including universals — §7).
6. **Deltas are invalidation signals.** On any delta touching a derived relation's inputs, recompute membership from committed base state and reconcile. Additionally — load-bearing — **a symbolic delta must reconcile concrete edge-holders and concrete leaf members on that object, not just the residue** (§5.4).
7. **Synchronous v1** with an in-transaction **outbox table** as the delta stream (memory-flat, replayable, the seam for a future async worker). No Python generators across commit boundaries.
8. **No SAVEPOINTs in v1.** Nested transactions exist (`session.begin_nested()`; SQLite supports them) but the cascade's correctness requires all-or-nothing — a failed reconcile must abort the entire write. The legitimate future use is the async worker isolating per-delta failures; note the pysqlite driver's transaction-boundary quirks (SQLAlchemy documents the connect-event workaround) for that day. Record as a hook, build nothing.
9. **Stratification is mandatory.** Topo-order relations by derived-dependency at compile; any SCC through a derived relation is a compile error naming the cycle. Termination of the cascade follows from idempotent reconciliation.
10. **Namespacing lives in the name; the typed view is compiled, not stored.** Leaf predicates are named `<relation>.<index>` (deterministic pre-order function of the AST — persisted edges reference these names; renaming orphans data). No `family` column: it would duplicate name-derivable information and create a drift surface. Classification lives in the compiled namespace map and is enforced by invariant I4. A denormalized tag column may be added later as metadata, never identity.
11. **Ahead-of-time compilation all the way.** Nothing walks the AST at runtime: compile emits routing tables and executable plans (§4.1). The processor's per-delta overhead is dict lookups plus point reads.
12. **`RuleSet.apply` gets indexed dispatch, not Rete.** Key filters/rules by if-pattern relation (subdivided by subject-predicate where patterned). Our patterns test a single triple — only Rete's alpha layer applies; the one join that matters (transitivity) already has its specialized incremental structure (the closure), whose ref counting handles retraction natively.
13. **Paranoia mode defaults ON while prerelease** (§8): invariant checker pre-commit (inside the transaction — violations abort) and post-commit (fresh session), plus delta-scoped verification, plus the `ParityEngine` as the default engine in integration tests.
14. **`check` is one SQL round trip** on untainted relations: the ≤4 probe keys go into a single `IN (…) LIMIT 1` query; `SchemaInfo` gates prune the key list. Derived relations add one residue read (two point reads total; a `UNION ALL` merge is possible but not required — keep the code simple) *(adapt)*.
15. **v1 scope restrictions (loud compile errors, documented hooks):** object-wildcard shapes on derived relations *and their leaves* are rejected (needs a symmetric subject-keyed residue — hook only); a `TTU` whose *tupleset* relation is derived is rejected (a boolean parent-set is object-star-shaped — same hook). Subject wildcards — the OpenFGA-standard kind and everything in the boolean fixtures — are fully supported.

## §2 Background model (verify against repo)

`index_v4`: materialized DAG reachability closure; edges carry direct/indirect path counts (match the core's actual count asserts — repo wins on the exact inequality); `check` = point lookups on the unique edge index; reachability flips (0→positive, →0) emit `PermissionDelta`s; writes that would close a cycle are rejected via a reverse-reachability pre-check; `_lock_store` serializes writers per store. `WildcardIndex` façade: split wildcard nodes (`w_any` receives instance bridges, emits grants; `w_all` receives grants, emits bridges), position rule (wildcard subject → `w_any(subject shape)`, wildcard object → `w_all(object_type, relation)`), materialized bridges created idempotently per concrete node whose `(type, predicate)` shape is declared bridged, bridge GC tied to implicit-node ref counts, ≤4 check probes gated by `SchemaInfo`. Schema layer: AST (`Union`/`Intersection`/`Exclusion` over `Direct`/`Computed`/`TTU`), parser, `compile_ruleset` → Filters (admission) + Rules (rewrites); **it currently refuses `Intersection`/`Exclusion` — that refusal is the hole this spec fills.** Oracle: pointwise boolean-capable reference over (schema AST, raw tuples). Set engine: bitmap backend with the property-tested `MemberSet` `(pos, stars, neg)` and the pinned star×boolean table. Validation harness: handwritten scenario tables, MultiBackend fan-out, full-grid check comparison (universe ∪ ghosts ∪ `'*'`) after every op; boolean stores currently run 3-way.

## §3 Compilation

### 3.1 Taint analysis

Compute taint as reachability over the schema reference graph (relation → relations it mentions via `Computed`, `TTU.target_rel`, `TTU.tupleset_rel`, userset `Direct` restrictions `[T#P]`), seeded at relations containing a boolean operator. Tainted ⇒ derived (gets a plan, processor management, a residue). Untainted ⇒ today's compile path, byte-identical output (regression gate). Why taint and not just "boolean relations": star-covered members of a derived relation have no edges, so closure rewrites reading it see only concretes — `approver: viewer or admin` over a boolean `viewer` would silently drop every star-covered viewer. Named test required (§10).

### 3.2 Plan trees and leaves

Normalize each derived relation's AST into a **plan tree**: internal nodes `Union`/`Intersection`/`Exclusion`; leaves of two kinds — **closure-leaf** (maximal subtree with no boolean operator and no derived-relation reference; compiled via existing `_emit_expr` with the leaf's synthetic name as `relation_name`) and **derived-leaf** (a `Computed`/userset reference to another derived relation; evaluated at reconcile time through that relation's edge+residue check; never inlined). A `TTU` whose `target_rel` is derived stays a plan node `DerivedTTU(target_rel, tupleset_rel)`. Record per-leaf **polarity**: negative iff under an odd number of `Exclusion.subtract` positions (drives neg candidates and the never-generate-from-subtrahends rule).

**Leaf naming:** `<relation>.<index>`, pre-order left-to-right over closure-leaf positions. Collision locks, all three: *lexical* — schema declarations reject `.` in relation names (tuple-side entity names are unrestricted); *structural* — undeclared relations match no Filter, and leaf names embed their owner so cross-owner collision is impossible by construction; *checked* — invariant I4.

### 3.3 Write routing (the rename rule, mechanized)

Users write tuples against public relation names only. For derived relations:

- Extend `Filter` with `rewrite_relation: str | None = None` *(adapt the exact mechanism if Filters compose differently than assumed; preserve the behavior)*. Each `Direct` restriction inside a derived relation compiles to a Filter matching the raw tuple (public relation name, existing strict subject pattern) with `rewrite_relation` = its owning leaf.
- **Fan-in expansion:** in `apply()`, for derived relations, *every* matching rewriting Filter fires (not first-match), each yielding the triple with the relation replaced; dedupe by resulting triple. Rationale: `[user] and [user]`-shaped schemas must populate both leaves from one raw write for oracle parity. `remove` applies the identical expansion so counts retire symmetrically. Pure-union relations keep first-match semantics unchanged.
- `Computed`/`TTU` *inside* a closure-leaf compile to Rules targeting the leaf name.
- **Exclusivity, enforced three ways:** compile-time assert (no Filter admission and no Rule then-target is a derived-public relation); write-path assert (raw/rewritten triples landing on a derived-public family raise unless the processor flag is set); invariant I5.
- `SchemaInfo`: subject-wildcard shapes declared inside derived definitions attach to the **leaf** predicates (bridges per leaf; leaf probes then implement per-branch intensional stars). Derived-public relations are never wildcard shapes themselves. Object-wildcard on derived relations: rejected per decision 15.

### 3.4 Compile outputs (the AOT contract)

`compile_schema(ast, schema_info) -> CompiledSchema` *(adapt names)* containing:

- `ruleset`: Filters/Rules for untainted relations + all closure-leaves, with **indexed dispatch**: `dict[relation → list[Filter|Rule]]`, subdivided by subject-predicate where the pattern constrains it. The apply worklist dedupes on triple identity.
- `namespace: dict[predicate_str → Family]` where `Family ∈ {USER, LEAF(owner, index, polarity), DERIVED_PUBLIC}`.
- `plans: dict[(object_type, relation) → Plan]`; each `Plan` carries: the executable form — **compile to closure-composed Python callables or a flat postfix program, your choice; requirements: no AST walk, no dict-dispatch per node, short-circuit evaluation** — plus `leaves: list[LeafSpec]` (predicate name, polarity, kind), `deps: list[derived relations referenced]`, `stratum: int`.
- `leaf_owner: dict[leaf_predicate → (owner_relation, object_type, index, polarity)]` — one dict hit maps a delta to its key.
- `dependents: dict[derived_relation → list[(dependent_relation, via, tupleset_rel|None)]]` where `via ∈ {computed, userset, ttu}` — drives invalidation fan-out (§5.2).
- `strata: list[list[(object_type, relation)]]` in topo order.

`UnsupportedByGraphIndex` survives only for decision-15 rejections; messages name the construct and the hook.

## §4 Data model

```python
class EdgeV4(...):            # existing, plus:
    derived: bool = False     # True iff written by the processor into a derived-public family

class ResidueV1(SQLModel, table=True):
    store_id: str
    object_node_id: int       # the derived relation's public object node
    relation: str             # denormalized public relation name (for lookup())
    stars: str                # JSON list of subject shapes [(type, predicate), …] intensionally covered
    neg: bytes                # roaring bitmap of concrete subject node ids: star-covered but excluded
    version: int              # bumped on every changing reconcile
    # UNIQUE(store_id, object_node_id); INDEX(store_id, relation)

class DeltaOutboxV1(SQLModel, table=True):
    id: int                   # PK autoincrement — the cursor
    store_id: str
    subject_node_id: int
    object_node_id: int
    action: str               # 'ADDED' | 'REMOVED'
    # INDEX(store_id, id)
```

*(adapt column types/layout to repo conventions; preserve: cursor ordering, uniqueness, the derived flag.)*

- All existing delta-emission points insert outbox rows (batched inserts); **no write path materializes a `list[PermissionDelta]`**. A thin helper drains a cursor range to a list for tests/back-compat.
- The cascade reads the outbox by keyset pagination from the transaction's starting watermark. Streaming fixes memory, not write amplification — a root-folder grant still writes O(fan-out) closure rows; that price was accepted when the closure was. Say so in the docs.
- `neg` is data-bounded: exclusion requires subtrahend derivations, which require tuples mentioning the subject — a true ghost can never be in `neg` and is answered by `stars` alone. Empty residues are deleted, never stored.
- The processor may intern the public object node when first writing a derived edge or residue for it (write path; the never-intern rule applies to reads only).

## §5 The delta processor

### 5.1 Cascade loop (in-transaction, v1)

```
after applying the raw write (leaf edges + closure maintenance):
  frontier = outbox rows with id > txn_start_watermark
  for stratum in strata:
      keys = coalesce(map_deltas_to_keys(frontier))     # §5.2; one reconcile per key
      for key in keys: reconcile(key)                    # §5.3/§5.4; emits new outbox rows
      frontier = outbox rows since previous frontier end
  assert map_deltas_to_keys(frontier) == ∅               # stratification ⇒ quiescence
```

`_lock_store` already serializes the whole cascade; no new locking.

### 5.2 Delta → key mapping

For outbox row `(s_id, o_id, action)`: resolve `o_id`'s node; classify its predicate via `namespace`:
- `LEAF(owner, …)` → key `(owner, public_object_node(o.type, o.name, owner))`. If either endpooint node is a w-node (`wildcard != ''`), mark the key **symbolic** (full-object reconcile). Assert: no `w_all`-object deltas can map to derived keys in v1 (decision 15 rejected the shapes that would produce them).
- `DERIVED_PUBLIC(R)` → for each `(dep, via, tupleset)` in `dependents[R]`: `computed` → same object under `dep`; `ttu` → every object holding a tupleset edge from this object (enumerate via the tupleset relation's stored edges — data-bounded); `userset` → objects granted-to by this `(o, R)` userset node (its direct outgoing tuple edges). Residue-version bumps enqueue the same dependent keys.
- Anything else → not a processor concern (external consumers are a non-goal).

### 5.3 `reconcile(R, obj)` — full-object form

1. **Stars.** Per closure-leaf: `leaf_stars = {σ : WildcardIndex.check((σ,'*'), leaf, obj)}` (the intensional per-branch probe). Per derived-leaf `D`: `residue(obj', D).stars` (same object for computed; for `DerivedTTU`, `∪` over tupleset parents of `obj` of `residue(p, target).stars`). Fold the plan with the pinned star algebra: Union → ∪, Intersection → ∩, Exclusion → base ∖ sub. **Reuse the star×boolean semantics from the `MemberSet` module — lift the fold rules/table, not the type** (its bitmaps are coupled to the set engine's interner; do not import that coupling into the processor).
2. **Neg.** Candidates = concrete members, on this object, of every negative-polarity leaf (`lookup_reverse` per leaf family, markers excluded) ∪ `neg` sets of referenced derived-leaves. `neg = {c ∈ candidates : shape(c) ∈ stars ∧ ¬eval_plan(c, obj)}`. Recomputed in full each time — idempotent by construction.
3. **Upsert/delete** the residue row iff changed (bump `version`; enqueue dependents).
4. **Edge audit** over `C` = current derived incoming concretes on `(obj, R)` ∪ concretes of every *positive*-polarity leaf on `obj` ∪ step-2 candidates: `reconcile_subject(R, obj, c)` for each.

`eval_plan(s, obj)`: closure-leaf → `WildcardIndex.check(s, leaf, obj)` (wildcard-aware, so star-under-boolean composes per §7); derived-leaf D → derived check (§6) on D; `DerivedTTU` → ∃ tupleset-parent p: derived check `(s, target, p)`. Defensive revisit guard **raises** (stratification makes cycles impossible; a hit means a corrupted store — never spin, never return-False like the set engine's read guard).

**`reconcile_subject(R, obj, s)`** = ensure a derived direct edge `s → (obj,R)` exists iff `eval_plan(s, obj)`. Writes go through the ordinary façade path with the processor flag, so bridges, counts, cycle checks, and **delta emission** behave normally — the emitted deltas drive the next stratum. Presence is checked first; replays are no-ops. Concrete leaf deltas take this cheap path for the delta's subject only; symbolic deltas, residue bumps, dependency invalidations, and backfill take §5.3.

### 5.4 The symbolic rule (prevents silent corruption)

A delta on a w-node is symbolic ("everyone of that shape gained/lost at this leaf") and is consumed as an invalidation — never a fan-out over the shape's population. But residue recompute alone is insufficient: with `viewer = editor.0 but not blocked.1`, bob holding a concrete editor tuple and a derived edge, adding `[user:*]` to blocked flips `eval_plan(bob)` false while producing **no concrete delta for bob** (mirrored for intersections). Therefore **every symbolic delta triggers full-object reconcile**, whose step-4 audit re-derives exactly the concretes whose edges could depend on symbolic state. The candidate set is bounded by stored edges on that object — never the shape's universe; star-only members and ghosts have no edges and are answered by the residue with zero per-subject work. Named test: `test_symbolic_flip_reconciles_concretes` (both polarities).

### 5.5 Backfill / bootstrap

Compiling a derived schema over existing leaf data: per stratum in topo order, enumerate distinct object nodes of each relation's leaf families (reverse lookup on the most selective **positive** leaf per family; subtrahends never generate candidates, only filter), `reconcile` each. Chunked, idempotent, mirroring the wildcard `backfill()` precedent. Doubles as the recovery path when invariant I9 finds an inconsistent key.

## §6 Reads

**Untainted relations:** unchanged semantics; consolidate the ≤4 probes into **one** SQL round trip: build the candidate key list — `(s,o)`, `(w_any(shape(s)), o)`, `(s, w_all(o.type, R))`, `(w_any(shape(s)), w_all(o.type, R))` — include a key only if `SchemaInfo` declares the form and both node ids resolve (a missing node simply drops its keys; ghosts thus retain their star-probe coverage); then `SELECT 1 … WHERE (from,to) IN (VALUES …) LIMIT 1` (SQLAlchemy `tuple_().in_()`; *adapt idiom*).

**Derived relations:**
```
check(s, R, o):
    if s.name == '*': return shape(s) ∈ residue(o,R).stars        # intensional; 1 read
    return edge_probe(s → (o,R))                                   # public family, probe 1 only
        or (shape(s) ∈ residue(o,R).stars and s_id ∉ residue.neg)  # ≤2 point reads total
```
Missing residue row ⇒ empty. Ghost subject ⇒ edge probe false, residue still answers. Probes 2–4 don't apply on public families (derived relations are never wildcard shapes; symbolic state lives in the residue by decision 5).

**`lookup_reverse(R, o)`** on derived: concretes = incoming derived edges' subjects; markers = `residue.stars` rendered as the existing symbolic markers; **add `excluded_node_ids: set[int]`** to `LookupResult` (additive, default empty, from `residue.neg`) so "everyone of shape σ except these" is representable without enumeration.

**`lookup(subject)`**: existing reachable-set collection returns derived edges naturally; additionally scan `ResidueV1` by `(store, relation)` per derived relation and include objects where `shape ∈ stars ∧ subject ∉ neg`. Lookup was already enumeration-shaped; correctness is pinned by the matrix.

## §7 Pinned semantics (do not let these drift)

Strict ∀⇒∃ (no vacuous grants). Intensional `'*'` queries per branch: `'*' ∈ A∧B` iff star-covered in both; `'*' ∈ A∖B` iff star-covered in A and *not* star-covered in B; concrete-only exclusions never defeat star queries. Concrete and ghost subjects always get genuine pointwise membership through exclusions. Never intern or create nodes on the read path. `[user] but not [user:*]` ⇒ empty relation, empty residue. The oracle is ground truth.

**Self-inclusion, both flavors, pinned:** object-star self-containment (`folder:X contains folder:*` ⇒ X contains itself) is **representable and true, with no cycle** — subject-role and object-role are different nodes (`(folder,X,'')` vs `(folder,X,contains)`), plain entity nodes have in-degree zero, so the path X → w_all → (X,contains) cannot close. Do not "fix" this into a rejection. Conversely, **self-referential wildcard tuples whose object is an instance of the wildcard's own shape** (`group:*#member member group:g`) are **rejected by cycle detection and that is correct**: grant `w_any(group,member) → (g,member)` meets bridge `(g,member) → w_any(group,member)`. Union semantics would tolerate the fixpoint; multiplicative path counting cannot (infinite path multiplicity) — the rejection is a counting-invariant necessity, the façade re-raises with an explanatory message, and the set engine rejects identically (validity parity). Derived edges must never create cycles (stratification); a processor write that would close one is a **hard failure**, not a rejection.

## §8 Verification machinery

### 8.1 Paranoia mode

A store/engine flag, **default ON** until the codebase is declared prod-ready. Effects: invariant checker runs pre-commit inside the transaction (violation ⇒ raise ⇒ rollback) **and** post-commit in a fresh session (catches commit-boundary/session-state bugs); delta-scoped verification (§8.3) runs per transaction; `ParityEngine` (§8.4) is the default engine in integration tests. Provide `paranoia=False` for benchmarks. *(adapt the wiring — decorator, context manager, or engine ctor arg.)*

### 8.2 Invariant checker — full list

I1 **Count algebra:** per edge row, counts satisfy the core's asserted inequalities (verify the exact form in the core — repo wins), no zero-reachability rows persisted.
I2 **Acyclicity:** DFS over direct edges asserts a DAG (paranoia can afford it; sample outside paranoia).
I3 **Bridge hygiene:** every bridge edge justified by a declared bridged shape + live concrete node; every concrete node of a bridged shape has its bridges (materialization completeness); no bridges for undeclared shapes; no implicit node whose only edges are bridges survives an op (GC completeness).
I4 **Namespace classification:** every node predicate classifies under the compiled namespace map; leaf/derived families appear only in stores whose schema declares them.
I5 **Derived-flag exclusivity:** `derived=True` iff an incoming direct edge on a derived-public family; no such edge lacks the flag; the flag appears nowhere else.
I6 **Residue placement:** rows only on derived relations; `stars ⊆` declared subject-wildcard shapes; `neg` subjects concrete and star-covered by `stars`; `neg ∩ {subjects holding a derived edge on the same object} = ∅` (an edge means expr-true; neg means expr-false); no empty rows.
I7 **Residue version monotonicity** across a run (checker keeps last-seen versions in memory).
I8 **Stratification acyclic** (compile-time; re-asserted).
I9 **Fixpoint audit:** for sampled keys (all keys in paranoia), `reconcile` produces zero changes.
I10 **Outbox sanity:** watermark ≥ max processed id; rows well-formed.
I11 **Read purity:** node/edge/residue row counts unchanged across read-only ops.
I12 **Rejection cleanliness:** after any rejected op, the row multiset (ids ignored) equals the pre-op snapshot.

### 8.3 Delta-scoped verification

The outbox names exactly the pairs whose reachability allegedly flipped. Per transaction (paranoia mode): for each row, recompute reachability for `(s, o)` by bounded BFS over **direct** edges and compare with closure-row existence; for symbolic rows, verify the w-node edge itself plus a sampled instance implication. O(affected × local neighborhood) — catches maintenance bugs at the moment and location they occur. Full-closure recompute remains a sampled audit and a test-suite job, never a per-write cost.

### 8.4 `ParityEngine`

A façade implementing the common op API (`load_schema`, `add_tuple`, `remove_tuple`, `check`, `lookup`, `lookup_reverse`) over **oracle + set engine + graph backend** simultaneously. It keeps the raw-tuple multiset as the oracle's input. Per op: assert identical accept/reject (same error family); on accept, assert check-parity over the delta-affected pairs ∪ a sampled grid (universe ∪ ghosts ∪ `'*'`); on reject, assert I12 on every backend. Expose as a pytest fixture and make it the default engine in every test that isn't unit-scoped. This is the wrapper the author asked for; build it early (phase 1) so all later phases develop under it.

## §9 Hypothesis fuzzing

Add `hypothesis` as a dev dependency. Two layers:

**Property tests (stateless):**
- Metamorphic schema pairs over identical tuple sequences: `A ∖ B ≡ A ∖ (A ∧ B)`; `(A ∪ B) ∖ C ≡ (A ∖ C) ∪ (B ∖ C)`; the De Morgan pair (complements via a declared-star base, as the demorgans fixtures do). Assert full-grid equality between the paired stores on every backend.
- Add-then-remove restores the exact row multiset (ids ignored), including counts and bridges.
- Permutation invariance for commuting op sets.
- Replay: drain the outbox from zero through a fresh processor state; end state equals live.
- Backfill-vs-live equivalence: same tuples, one store maintained incrementally, one bulk-loaded then backfilled.
- Parser round-trip: `parse → unparse → parse` is identity on the AST.

**Stateful (`RuleBasedStateMachine`):** rules draw ops (weighted add/remove/check/lookup; removes drawn from the live tuple multiset for hit rate) against a `ParityEngine`; `invariant()` runs the checker in paranoia mode. Schema strategy: `st.recursive` over the AST grammar, bounded (≤ ~6 relations, depth ≤ 3), generated in topo order referencing only earlier relations so stratifiability holds by construction; generate known-cyclic schemas separately to assert compile rejection. Entity pools small (2–4 names/type) plus `'*'` where declared plus fresh ghost names used only in checks. **Deliberate boundary generators:** self-referential wildcard tuples in both orientations (the rejected subject-shape case and the accepted object-star self-containment), and multi-hop symbolic loops threaded through bridges — assert accept/reject parity and I12. Settings: fast profile for CI (`max_examples` modest, `deadline=None`), deep profile for local/nightly; seed corpus from the existing fixtures via `@example`. Shrinking then hands you minimal counterexamples for free — when it does, freeze each one as a named regression test.

## §10 Validation & matrix flip

**The acceptance event:** boolean fixture stores (`demorgans_*` trio, `boolean_wildcards.fga`) flip **3-way → 4-way** — same grids, same after-every-op comparison, graph backend included, under both `SetOps`. The current refusal test is replaced by compile-success + plan-shape assertions.

**Named scenarios (handwritten, each with a justifying comment):** `test_symbolic_flip_reconciles_concretes` (both polarities); interleaved add/remove order-independence (a sequence and its shuffle reach identical end state); a leaf flip cascading two strata (`viewer` boolean → `approver: viewer or admin` → `auditor: approver but not muted`); star-minus-concrete residues vs ghost and `'*'` subjects; removal of the last positive-leaf edge revoking the derived edge and its downstream stratum; `[user] but not [user:*]`; intersection with an empty branch; De Morgan equivalence on the graph backend; **taint coverage** — a pure-union relation over a boolean one serving star-covered members (the §3.1 bug); backfill-vs-live equality.

## §11 Phased plan (each phase lands green; commit per phase)

**P0 — Recon & baseline.** Run the suite, record. Verify every repo-fact this spec cites; open `docs/spec-deviations.md` with findings. Snapshot compiled-`RuleSet` reprs for all pure-union fixtures. *Accept:* baseline green; deviations log exists.

**P1 — Verification foundation.** `ParityEngine` over the existing three backends; invariant checker core (I1–I3, I11–I12) + paranoia wiring (pre/post-commit). *Accept:* whole existing suite green under `ParityEngine` + paranoia; at least one deliberately-broken mutation caught by a checker unit test.

**P2 — Compile.** Taint, stratification + cycle error, plan trees, deterministic leaf naming + `.`-reservation in declarations, `Filter.rewrite_relation`, fan-in expansion (add **and** remove), exclusivity asserts, `SchemaInfo` leaf attribution, decision-15 rejections, routing tables + executable plans, indexed `apply()` dispatch. *Accept:* pure fixtures byte-identical to P0 snapshots; boolean fixtures compile; raw writes land only in leaf families; direct writes to leaf/derived names refused; parser round-trip property passes.

**P3 — Models + outbox.** `EdgeV4.derived`, `ResidueV1`, `DeltaOutboxV1`, emission refactor (no delta lists on write paths), watermark, list-draining test helper; delta-scoped verifier (§8.3) wired into paranoia. *Accept:* outbox stream ≡ legacy list output across the suite; delta-scoped verifier green; a seeded closure-maintenance bug is caught by it in a unit test.

**P4 — Processor.** Plan evaluator, `reconcile_subject`, full-object `reconcile` (star fold, neg recompute, edge audit), cascade loop with coalescing, symbolic rule (§5.4), hard-fail cycle guard on derived writes. *Accept:* named scenarios pass on the graph backend driven directly; I9 clean after every scenario.

**P5 — Reads.** Single-round-trip check on untainted relations; derived check; `LookupResult.excluded_node_ids`; `lookup`/`lookup_reverse` extensions. *Accept:* full-grid check parity with the oracle on boolean fixtures; untainted check verified as exactly one SQL statement (assert via statement counter in a test).

**P6 — New-state invariants + backfill.** I4–I10; `backfill()`; residue recovery path. *Accept:* invariants green across the suite; backfill-vs-live property passes.

**P7 — Matrix flip.** Boolean stores 4-way under both `SetOps`; refusal tests replaced. *Accept:* the entire matrix green. **This is the feature's acceptance event.**

**P8 — Hypothesis campaign.** §9 in full; freeze every shrunk counterexample as a named regression. *Accept:* CI profile green; deep profile run at least once with findings triaged (fixes may reopen earlier phases — that's expected and fine).

**P9 — Docs.** README memoization-spectrum update (graph column: booleans ✓, deltas ✓ including derived relations), CLAUDE.md layout notes, honesty notes (write amplification; symbolic-write reconcile cost), cross-link this spec and the deviations log.

## §12 Cost model (document honestly)

| | untainted relation | derived relation |
|---|---|---|
| `check` | ≤4 keys, **1 SQL round trip** | ≤2 point reads (edge + residue) |
| concrete write | O(closure delta) | + O(affected keys × plan size) point reads |
| symbolic write | O(closure delta) | + full-object reconcile: O(concrete members on that object) — data-bounded, never universe-bounded |
| space | closure edges | + derived edges for concretely-supported members only (star-only members: zero edges) + one residue row per (object, relation) |

Write amplification is multiplicative in strata depth — the accepted price of O(1) reads; the outbox fixes memory, not amplification.

## §13 Non-goals (documented hooks only)

Async outbox workers (the replay property keeps the seam viable; SAVEPOINT-per-delta noted in decision 8); exposing derived-relation deltas to external consumers; object wildcards on derived relations / derived tupleset relations (symmetric subject-keyed residue — the hook); cross-query caching / zookies; automatic outbox pruning; residue GC beyond empty-row deletion; lenient ∀⇒∃; a `family` metadata column (additive later if indexed family filtering is ever needed); Rete-style general incremental matching.
