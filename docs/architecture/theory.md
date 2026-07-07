# Theory

Why the two engines work, mathematically — not how they're wired (that's
`graph-index.md` / `derived-predicates.md` / `system.md`). Roaring bitmaps are
assumed known; they only matter here as "id-set ∪∩∖ is cheap and vectorized."

---

## 1. The graph index: reachability by path counting

### 1.1 The object

Let G be a directed acyclic **multi**graph over typed nodes. The index materializes,
for every ordered pair (u, v) with at least one path, the row

```
d(u,v) = number of parallel DIRECT edges u -> v        (direct_edge_count)
p(u,v) = number of distinct directed PATHS u -> v      (indirect_edge_count)
```

Reachability is `p(u,v) > 0`; a length-1 path is a path, so `p ≥ d > 0 ⇒ p > 0`
(invariant I1). Zero rows are deleted, never stored — the table *is* the support of
p. `check` is then a point read; `lookup`/`lookup_reverse` are row scans of one
node's row set.

### 1.2 The counting theorem (why updates are exact)

The whole design rests on one combinatorial fact. In a DAG, a path can use a given
edge **at most once** (using it twice would close a cycle). Therefore, for a new
direct edge e = (u, v), the paths that use e are in bijection with pairs
(path a→u, path v→b), including empty paths at the endpoints. Writing p̂ for counts
with p̂(x,x) = 1 (the empty path):

```
insert e:   p'(a,b) = p(a,b) + p̂(a,u) · p̂(v,b)     for all a, b
```

Deletion is the same statement read backwards: remove the direct edge first, then

```
delete e:   p'(a,b) = p(a,b) − p̂'(a,u) · p̂'(v,b)
```

where the products are computed over the graph *without* e (the code's
"remove direct edge first / add direct edge last" ordering is exactly this — the
neighborhood counts consulted must never include paths through e itself).

Two consequences carry the system:

* **Removal needs no re-derivation.** Boolean (idempotent) closure loses
  information: after `reach(a,b) = true ∨ true` you cannot subtract one reason.
  Counts live in (ℤ, +), a **group**, so every insertion has an exact inverse; the
  booleans (∨) are only a semilattice. This is the same trick as annotating a MAFSA
  with suffix counts to make it indexable: enrich an idempotent structure with a
  cancellative one and updates become local arithmetic.
* **Acyclicity is a hard precondition, not a policy.** With a cycle, path counts
  diverge (a path could traverse e arbitrarily often) and the bijection fails.
  Hence the reverse-reachability pre-check on every insert, and hence the
  *necessity* (not choice) of rejecting self-referential wildcard tuples: the
  bridge + grant pair would close exactly such a cycle. Union semantics could
  tolerate that fixpoint; counting cannot.

Update cost is O(|ancestors(u)| × |descendants(v)|) row touches against O(1)
reads. Under OMv-style lower bounds no dynamic-reachability structure gets both
fast updates and fast queries; this is the query-optimal corner, chosen on purpose
(the set engine is the opposite corner).

### 1.3 Wildcards: intension vs extension, split in two

A wildcard grant is an **intensional** statement ("all/any instance of shape S"),
and materializing it extensionally is wrong twice over: unbounded (ghosts — names
never seen — must be covered) and unstable (instances created later must be covered
retroactively). The construction keeps the intension as *structure*:

* `w_any(S)` is the ∃-node: every concrete c of shape S bridges **in**
  (`c → w_any(S)` — "c witnesses ∃S"), and wildcard-*subject* grants leave from it.
* `w_all(S)` is the ∀-node: wildcard-*object* grants arrive **into** it, and it
  bridges **out** to every concrete (`w_all(S) → c` — "∀S distributes to c").
* There is deliberately **no `w_any → w_all` edge**: being an instance must not
  grant what is distributed to instances. Its absence is also what makes ∀⇒∃
  *strict*: a path `x → w_all(S) → c → w_any(S) → y` requires a real concrete c in
  the middle — no instances, no implication. (A single lenient edge would be the
  vacuous-truth mode; documented hook, not built.)

Bridges materialize every *interior* wildcard hop at write time, so only the two
hops touching the literal query endpoints stay virtual — covered by a fixed,
constant case analysis (the ≤4 probes: concrete/concrete, ∃-covered subject,
∀-covered object, both). That is why nesting depth and fan-out never appear in read
cost.

### 1.4 Boolean relations: stratified fixpoint semantics

`and` / `but not` make the rule system **nonmonotone**, which a closure cannot
represent directly (closures only ever grow along rules). The standard semantics
for nonmonotone recursion-free-through-negation programs is **stratification**
(Datalog¬): order derived relations so every negative/intersective dependency
points strictly downward; then the program has a unique **perfect model**, computed
stratum by stratum, each stratum a plain fixpoint over already-final inputs.

The compiler enforces the precondition (an SCC through a derived relation is a
compile error) and the delta processor computes the perfect model *incrementally*:

* deltas are **invalidation signals, never state transfers** — a reconcile
  recomputes a key's membership from committed lower-stratum state;
* reconciliation is **idempotent by construction** (recompute-and-compare), so each
  stratum's reconciles move state only *toward* its unique fixpoint;
* the cascade therefore quiesces in ≤ #strata rounds (each round settles at least
  one further stratum; the machine-checked version is the quiescence assert and I9,
  "a second reconcile changes nothing").

### 1.5 Residues: the canonical form of a star-closed set

A boolean combination over star grants is not representable by edges alone: its
member set can be co-finite relative to a shape ("every user except bob"), and
edges can only enumerate. The persisted form per (object, derived relation) is

```
members = edges  ∪  ( ⋃_{σ ∈ stars} population(σ)  ∖  neg )
```

with the **canonical representation rule**: a subject whose shape is star-covered
holds *no* edge (it is in `neg` iff expression-false); an uncovered subject holds
an edge iff expression-true and is never in `neg`. This makes the representation of
any logical state **unique**, which is what buys row-level determinism: any two op
orders reaching the same logical state produce identical rows (permutation
invariance), and add-then-remove restores the exact row multiset. It also carries
the space bound: star-only members cost zero edges, and `neg` is data-bounded
(a true ghost can never acquire a neg entry — it has no tuples to be a candidate
through — so ghosts are answered by `stars` alone).

---

## 2. The set engine: a star-closed set algebra

### 2.1 The algebra

Fix the declared subject shapes Σ and a population function pop: Σ → id-sets (the
interner's live masks). Consider the smallest family 𝒜 of subject sets containing
all finite id-sets and all pop(σ), closed under ∪, ∩, ∖. **Claim:** every A ∈ 𝒜 is
representable in the normal form

```
A = pos ∪ (starpop(S) ∖ neg),   S ⊆ Σ,  starpop(S) = ⋃_{σ∈S} pop(σ),
    pos ∩ starpop(S) = ∅,  neg ⊆ starpop(S)
```

— which is exactly `MemberSet(pos, stars=S, neg)`. Closure under the operations is
the load-bearing part, and the star component folds by **plain set algebra on the
shape sets**:

```
stars(A ∪ B) = stars(A) ∪ stars(B)
stars(A ∩ B) = stars(A) ∩ stars(B)
stars(A ∖ B) = stars(A) ∖ stars(B)
```

while pos/neg are *renormalized extensionally* against current populations
(`pos = E ∖ starpop`, `neg = starpop ∖ E`, with pos winning over neg). The fold is
the **intensional** reading — used verbatim to answer `'*'` queries and pinned as
the star×boolean table:

* `'*' ∈ A ∩ B` iff the shape is covered in **both**;
* `'*' ∈ A ∖ B` iff covered in A and **not** covered in B — so a concrete-only
  exclusion (finite B, stars(B) = ∅) never defeats a star query;
* concrete and ghost subjects always get genuine pointwise membership through the
  extensional half.

The intensional and extensional halves answer different questions on purpose
(`'*'`-as-query vs a-name-as-query); the normal form keeps both exact
simultaneously. The graph side's residue fold (§1.5) lifts these three stars rules
symbol-for-symbol — one pinned table, two implementations.

### 2.2 Strict ∀⇒∃ and evaluation

Star tupleset/userset positions are expanded to **existential witnesses over the
actual population** (the interner's masks) — never assumed non-empty. Evaluation is
recursive descent over the shared AST with per-query memoization; a revisit during
one query returns False ("this path adds nothing new"), which is the coinductively
correct reading for a purely union-recursive schema and is only reachable for
schemas the graph refuses anyway (cyclic-through-boolean is a compile error there).

Roaring enters only as the representation of pos/neg/populations: bulk ∪∩∖ over
id-sets, behind the `SetOps` seam. The algebra is representation-independent, and
the matrix runs the whole suite under both implementations to prove it.

### 2.3 The spectrum, stated once

Both engines compute the same function: the perfect model of (schema, raw tuples),
queried pointwise. The graph index materializes the model at **write** time (counts
+ bridges + derived edges + residues; O(1) reads); the set engine re-derives it at
**read** time from the raw tuples (O(1) writes). TTU semantics (parents are stored
tuples, never computed membership), the star table, strict ∀⇒∃, and validity
(accept/reject) are pinned identical across both — that identity is not an
aspiration but the thing the validation matrix asserts after every operation.

---

## 3. The connected store: logs, cursors, and one theorem each

* **The log is sufficient**: schemas are static and writes are admission-validated,
  so index state is a deterministic function of (schema, log prefix). The cursor
  names the prefix; `advance_index` is that function restricted to a suffix;
  `build_index` is the same function evaluated on a snapshot + empty suffix.
  Sync and async schedules compute identical states because they run the *same*
  step over the *same* prefix order — only the transaction boundaries differ.
* **Exactly-once is transactionality**: applied rows and the cursor advance commit
  atomically, so the applied prefix is always exactly [1, cursor]; a crash retries
  an unapplied suffix. (The applier locks the index store before reading the
  cursor: two appliers reading the same cursor would otherwise both apply a suffix
  — a lost update on ref-counted state, i.e. corruption, not just waste.)
* **Tokens lower-bound freshness**: a write's log id t satisfies
  "cursor ≥ t ⇒ the index reflects the write"; when it doesn't, the set engine
  evaluates the raw tuples directly, which is fresh by construction. This is the
  Leopard `timestamp ≤ query_timestamp` merge collapsed to a fallback.
