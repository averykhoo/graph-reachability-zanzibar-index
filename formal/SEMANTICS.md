# SEMANTICS.md — the specification to be formalized

**Phase 0 output.** This is the human-readable specification that the Lean 4
development (`formal/lean/`) will encode as the spec `sem` and the two backend
models. It is the **trust root**: if this document is wrong, every downstream
proof is proving the wrong thing. It must be reviewed by the user before any Lean
is written (plan §8.1 checkpoint 1).

Every non-trivial claim carries a `file:line` citation into the repo as it stood
at commit `beecd08` (master). Where a spec doc and the code disagree, **the code
wins** (CLAUDE.md), and the divergence is logged in §11. All line numbers were
read directly this session; re-verify before relying on any single one, since the
code will move.

Companion reading already digested into this doc: `docs/architecture/theory.md`
(the math), `docs/architecture/correctness.md` (the contract), the three
`docs/specs/*.md` normative specs, `tests/oracle.py` (the reference evaluator),
`setengine/memberset.py`, `index_v4/{core,wildcard,processor,invariants,models}.py`,
and the parser/stratifier in `zanzibar_utils_v1.py`.

---

## 1. The correctness contract — what "correct" means

Verbatim intent from `docs/architecture/correctness.md:8-18`:

> For every store: after any accepted op sequence, every backend answers every
> `check` query identically to the reference semantics; every backend accepts and
> rejects the same op sequences (validity parity); a rejected or failed op changes
> nothing observable (atomicity); and under the async schedule, a caught-up index
> is indistinguishable from a synchronously-maintained one.

The reference semantics in the repo is operational — it *is* `tests/oracle.py`
(`correctness.md:15-18`). **Our project replaces that role:** the Lean executable
spec `sem` (§5) becomes the reference, and the oracle is demoted to a cross-check
pinned by conformance testing (plan §2.3). `theory.md:192-198` states the unifying
fact we will make precise and prove:

> Both engines compute the same function: **the perfect model of (schema, raw
> tuples), queried pointwise.** The graph index materializes the model at write
> time (O(1) reads); the set engine re-derives it at read time (O(1) writes).

So `sem S T q` is defined as: *is the query `q` true in the stratified perfect
model of the Datalog¬ program induced by schema `S` over stored tuples `T`?*
Both backends are proven to compute `sem`; equivalence is the corollary.

**Scope of the verified `check`.** `q = (subject, relation, object)` with a
*concrete, bare* subject is the primary obligation. Intensional `'*'`-subject
queries and userset-subject queries are also in scope (they are part of the
matrix grid and the pinned star×boolean table). `expand`/`lookup`/`lookup_reverse`
are **out of scope** (plan §1 non-goals).

---

## 2. Domain and identifiers

### 2.1 Identifiers (`zanzibar_utils_v1.py:22-64`)

- Charset: `IDENTIFIER_CHARSET = r'A-Za-z0-9_./@+=-'`, length 1–256
  (`zanzibar_utils_v1.py:22-23`).
- `is_valid_identifier` is **strict charset only**; the sentinels `'*'` and `'...'`
  are NOT valid identifiers — they are admitted *positionally*, never by the
  predicate (`zanzibar_utils_v1.py:26-32`).
- **Write validity** (`validate_write_identifiers`, `:46-57`): on a stored tuple,
  `subject_type`, `relation`, `object_type` must be plain identifiers;
  `subject_name`, `object_name` may additionally be `'*'` (wildcard sentinel);
  `subject_predicate` may additionally be `'...'` / `Ellipsis` (bare sentinel).
- Reads are lenient: an out-of-charset name is not rejected on read, it simply
  never matches any validated stored tuple (`correctness.md`/CLAUDE.md).

**Spec treatment.** Model identifiers as opaque strings with two distinguished
sentinels `STAR = "*"` and `BARE = "..."`. Introduce a predicate `ValidIdent :
String → Prop` = charset+length membership. `Store` tuples carry the
precondition that every field satisfies the positional validity of
`validate_write_identifiers`. The spec does **not** re-derive the charset regex;
it takes `ValidIdent` as an axiom-level predicate and only relies on: (a) a
declared *relation* name can never be `'*'`, `'...'`, or contain `'.'` (§4.1); (b)
a concrete entity name can never be `'*'`. These two facts are what make the
sentinels unambiguous.

### 2.2 References

```
ObjectRef  := (type : String, name : String)         -- name may be STAR (object wildcard)
SubjectRef := (type : String, name : String,          -- name may be STAR (subject wildcard)
               predicate : String)                    -- BARE = "..." for a bare entity, else a relation
Tuple      := (subject : SubjectRef, relation : String, object : ObjectRef)
Store      := Finset Tuple                            -- (see §7 for the graph's MULTISET caveat)
Query      := (subject : SubjectRef, relation : String, object : ObjectRef)
```

The oracle's tuple is the ground truth for field layout (`tests/oracle.py:54-67`):
`(subject_predicate, subject_type, subject_name, relation, object_type,
object_name)`, with `_norm_pred` mapping `Ellipsis`/`None → '...'` (`:70-71`).

A **shape** is `(type, predicate)`: bare entity shapes `(T, "...")`, userset shapes
`(T, P)` where `P` is a relation (`memberset.py:42`, `wildcard-spec §1.1`).

---

## 3. The store as a Datalog¬ program (the semantic bridge)

`theory.md:91-110` fixes the intended meaning: `and`/`but not` make the rule
system **nonmonotone**; the semantics is **stratified Datalog¬** with its unique
**perfect model**, computed stratum by stratum, each stratum a plain least
fixpoint over already-final lower strata.

For the Lean spec we do **not** need to build a general Datalog engine. The oracle
(`tests/oracle.py`) already *is* the perfect-model evaluator, realized as pointwise
recursion with a provisional-False recursion guard. We formalize **that**
evaluation and separately prove it computes the stratified perfect model. Concretely
`sem` is defined twice and the two are proven equal (this equality is theorem T0a):

1. **Relational `Sem` (`Prop`-valued):** the inductively-defined perfect model.
   Theorems quantify over this.
2. **Executable `sem` (`Bool`-valued):** the fuel-bounded fixpoint iterator (or the
   oracle-style memoized recursion). The conformance CLI runs this.

Both are parameterized by a **stratification** of `S`; the theorems carry
`stratify S = some strata` as a hypothesis (§8). On non-stratifiable schemas the
spec is **partial / undefined** and out of the verified envelope (§4.4).

---

## 4. Schema AST and well-formedness

### 4.1 The AST

The oracle's independent AST is the cleanest reference (`tests/oracle.py:78-109`);
the production AST in `zanzibar_utils_v1.py` (`SchemaAST`) is
structurally identical (`Direct`/`Computed`/`TTU`/`Union`/`Intersection`/`Exclusion`).

```
Expr :=
  | Direct (restrictions : List (type:String, predicate:String, wildcard:Bool))
  | Computed (relation : String)
  | TTU (target_rel : String, tupleset_rel : String)      -- "target_rel from tupleset_rel"
  | Union (children : List Expr)                            -- len ≥ 2
  | Intersection (children : List Expr)                     -- len ≥ 2
  | Exclusion (base : Expr, subtract : Expr)
Schema := Map (type:String, relation:String) Expr
```

A `Direct` restriction `(t, p, w)` reads: bare `[t]` → `(t, "...", false)`; userset
`[t#p]` → `(t, p, false)`; subject-wildcard `[t:*]` → `(t, "...", true)`;
`[t:*#p]` → `(t, p, true)` (`tests/oracle.py:144-166`).

**Grammar** (both parsers implement it identically — this identity is load-bearing
for T0/conformance): `expr := chain ('but not' chain)? ; chain := unit (OP unit)*
(OP homogeneous: all 'or' or all 'and') ; unit := '(' expr ')' | leaf ; leaf :=
[restrictions] | REL | REL 'from' REL`. Oracle parser: `tests/oracle.py:169-243`;
`set-engine-spec.md:52-59`. Mixing `or`/`and` in one chain without parens is a
schema error (`tests/oracle.py:205-206`). At most one `but not`, loosest binding
(`:190-195`).

### 4.2 Well-formedness `WF S` (with citations)

Enforced in `zanzibar_utils_v1.py` and mirrored by the oracle parser:

- **`.` reserved in declared relation names** — leaf predicates are `<relation>.<index>`
  and would collide (`parse_schema_ast:697-702`, `parse_openfga_schema:1802`,
  `boolean-ivm-spec §3.2`). The tuple-side entity *names* are unrestricted by this
  rule (charset only).
- **Referenced predicates may not be in the reserved leaf namespace** (contain `.`)
  (`_validate_ast_references:718-726`).
- **`Union`/`Intersection` arity ≥ 2** (parser builds them only from ≥2 chained
  units; the JSON front-end enforces it too — `set-engine-spec §2.2`,
  boolean audit). A 1-child intersection cannot arise, so `all([]) → True`
  fail-open is unreachable (confirmed by the schema-parser audit).
- **Referenced relations must be declared** on the referent type (the oracle
  returns False for an undefined `(o_type, rel)` — `tests/oracle.py:360-363` — so an
  undeclared reference is "constantly empty", not an error, in the spec; the
  production compiler is stricter and may reject at compile. Model the spec side as
  "undefined ⇒ empty" to match the oracle, and treat compile rejection as a
  `WF`-level precondition — see §11 ambiguity A3).
- **TTU tupleset restriction rule** (`_validate_ttu_tuplesets:898`): a TTU's
  tupleset must resolve to **stored** (Direct) tuples; the graph rejects TTU
  tuplesets with computed/rewritten arms (`correctness.md:76-79`). This is the
  stored-parent rule (§5.5).

### 4.3 Taint / derived vs untainted (affects the GRAPH model only)

A relation is **derived (tainted)** iff its AST transitively reaches an
`Intersection`/`Exclusion` through `Computed`/`TTU`/userset-`Direct` references
(`compute_taint:1320-1333`, `_contains_boolean:1282-1287`,
`boolean-ivm-spec §3.1`, taint decision `theory.md:...`). **This does not change
`sem`'s meaning** — the spec is uniform over all relations. Taint matters only to
the *graph index model* (§7), which materializes untainted relations as ordinary
closure edges and derived relations via the residue/cascade machinery. The set
engine and the spec ignore taint entirely.

### 4.4 Non-stratifiable schemas — OUT of the verified envelope

`stratify S` (`_stratify:1630-1664`, Kahn topological layering over tainted
derived→derived dependency edges) raises `CyclicDerivedDependency` (a `ValueError`
subclass, `:461-467`) when a derived-dependency cycle exists. The graph index
**rejects** such schemas at compile; the set engine and oracle evaluate them with a
provisional-False recursion guard (`tests/oracle.py:333-375`,
`set-engine-spec.md`/`theory.md:182-184`). Because such schemas have no classical
perfect model, **all theorems carry `stratify S = some strata` as a hypothesis**
and make no claim otherwise. (Audit recommendation: reject upstream.)

---

## 5. The specification `sem` — pointwise stratified evaluation

This section is the normative definition, transcribed from the oracle
(`tests/oracle.py:309-487`), which the plan promotes to ground truth. The Lean
`sem` mirrors it function-for-function.

### 5.1 Shape of the evaluation

`sem` fixes the query **subject** for the whole recursion and recurses over the
node `(o_type, o_name, relation)` (`tests/oracle.py:15-19, 327-331`). Memo keyed on
that triple; an in-progress revisit returns **False** (provisional), with a
Tarjan-lowlink guard deciding which frames may be memoized (`:333-375`). For a
**stratifiable** schema this provisional-False recursion computes exactly the
stratified perfect model (the recursion only ever descends into strictly-lower
strata for negated/intersected references, and same-stratum recursion is monotone
union where provisional-False = least-fixpoint seed). The Lean executable `sem`
may instead iterate a monotone step per stratum to a fuel bound `|universe|`; prove
it equals the relational `Sem` (T0a). Either realization must agree with the oracle
on all inputs (conformance C1).

### 5.2 Universe (for star existential witnesses)

`_universe(T, query_names)` = concrete type-`T` names appearing in any tuple
position, **∪ query endpoints** of type `T` (`tests/oracle.py:314-325`).
`instances(T)` = the same **without** query endpoints (`:346-351`, blind-audit O3):
query endpoints must never *witness* existence (a ghost you asked about must not
"exist"), but they do count for shape/marker matching. Model both as functions of
`(Store, Query)`.

### 5.3 Boolean composition (`tests/oracle.py:377-391`)

```
Sem(Union cs)        = ∃ c ∈ cs, Sem(c)
Sem(Intersection cs) = ∀ c ∈ cs, Sem(c)
Sem(Exclusion b s)   = Sem(b) ∧ ¬ Sem(s)
Sem(Computed r)      = sat(o_type, o_name, r)          -- recurse, same object, new relation
Sem(Direct rs)       = direct_leaf(rs, o_type, o_name, relation)
Sem(TTU tr ts)       = ttu_leaf(tr, ts, o_type, o_name)
```

### 5.4 Direct leaf (`tests/oracle.py:398-462`) — the subtle core

`matching_objects(o_name)` = `{o_name}` if `o_name == '*'` else `{o_name, '*'}`
(`:393-396`): a concrete object also absorbs `T:*` object-wildcard grants; a `'*'`
object query is intensional (only star-object tuples).

`grants` = stored tuples with `relation == rel`, `object_type == o_type`,
`object_name ∈ matching_objects`, whose subject matches one of the leaf
restrictions by `(type, predicate, is-name-'*') == (r_type, r_pred, r_wild)`
(`restriction_matches`, `:402-411`). Then, by query-subject kind:

- **Star subject** (`s_name == '*'`, `:413-422`): true if a matching star tuple of
  the exact shape `(s_type, s_pred, '*')` is in `grants` (intensional, per-branch);
  **or** flow-through `_member_of_granted(grants)` (blind-audit D1: `'*'` resolves
  through granted usersets like any other subject — the graph closure cannot
  express per-branch-only for userset flow, so the oracle matches it).
- **Bare concrete** (`s_pred == '...'`, `:424-436`): a direct concrete grant
  `(s_type, s_name)` with bare predicate; **or** a bare-star grant `(s_type, '*',
  '...')` covering all of `s_type`; **or** `_member_of_granted(grants)`.
- **Userset subject** (`s_name != '*'`, `s_pred != '...'`, `:438-448`): the exact
  userset `(s_type, s_name, s_pred)` is granted; **or** a userset-star of the same
  shape `(s_type, '*', s_pred)`; **or** `_member_of_granted(grants)`.

`_member_of_granted(grants)` (`:450-462`): is the fixed subject a transitive member
of any granted *userset*? For each grant with non-bare predicate: concrete userset
→ `sat(g.subject_type, g.subject_name, g.subject_predicate)`; star userset `S:*#P`
→ `∃ inst ∈ instances(S), sat(S, inst, P)` (strict ∀⇒∃ over the *witness*
population, ghosts excluded).

### 5.5 TTU leaf — stored-parent semantics (`tests/oracle.py:464-485`)

For each stored tuple `(_, p_type, p_name, tupleset_rel, o_type, o_name∈matching)`
(the **tupleset** parents — STORED tuples only, never computed membership):

- concrete parent `p`: true if the subject *is* the from-chain userset itself
  `(s_type, s_name, s_pred) == (p_type, p_name, target_rel)`, **or**
  `sat(p_type, p_name, target_rel)`.
- star parent `S:*`: true if the subject is a star/userset of shape `(S,
  target_rel)`, **or** `∃ inst ∈ instances(S), sat(S, inst, target_rel)`.

**Stored-parent rule (pin):** TTU parents come only from stored tupleset tuples, so
a TTU over a relation with no Direct restrictions is *constantly empty*
(`theory.md:195`, `correctness.md:76-79`, CLAUDE.md gotcha). This is why the graph
splits storage leaves from rule-routed leaves (`processor.py` `_ts_leaf_predicates`
filters `spec.storage`).

### 5.6 Star × boolean (intensional `'*'` queries) — the pinned table

From `tests/oracle.py:29-39` and `theory.md:155-171`:

```
query subject   A and B (Intersection)      A but not B (Exclusion)
'*' (star)      star-covered in BOTH         star-covered in A and NOT in B
concrete u      u ∈ A and u ∈ B              u ∈ A and u ∉ B   (genuine pointwise)
ghost g         (same as concrete)           (same as concrete)
```

So a concrete-only exclusion (`A but not bob`) does **not** defeat a `'*'` query of
`A`. The set engine's `MemberSet` reproduces this by construction (§6); the graph's
residue fold lifts the same three star rules (§7).

---

## 6. Set engine model — the `MemberSet` algebra

Source: `setengine/memberset.py` (whole file, 132 lines) + `theory.md:137-189`.

### 6.1 Representation and invariant

```
MemberSet := (pos : Finset Id, stars : Finset Shape, neg : Finset Id)
```

Extensional meaning over a population `pop : Shape → Finset Id`
(`memberset.py:13-24, 91-96`):

```
ext(M) = pos ∪ (starpop(stars) ∖ neg)      where starpop(S) = ⋃_{σ∈S} pop(σ)
                                            -- pos WINS over neg
```

**Normal-form invariant** (established by `_normalize`, `memberset.py:99-105`):
`pos = E ∖ starpop`, `neg = starpop ∖ E`, hence `pos ∩ starpop = ∅` and
`neg ⊆ starpop`. `theory.md:143-149` states the closure claim: every set built from
finite id-sets and `pop(σ)` under `∪∩∖` has this normal form.

### 6.2 Operations (`memberset.py:112-127`) — one recipe

Each op computes the target extension `E` and target star set `S`, then
`_normalize(E, S)`:

```
union(a,b):     E = ext(a) ∪ ext(b),  S = a.stars ∪ b.stars
intersect(a,b): E = ext(a) ∩ ext(b),  S = a.stars ∩ b.stars
subtract(a,b):  E = ext(a) ∖ ext(b),  S = a.stars ∖ b.stars
```

The star bookkeeping (`∪`, `∩`, `∖` on shape sets) is exactly the §5.6 table
(`memberset.py:25-30`). Membership: `contains_entity(u, T) = u ∈ pos ∨ ((T,"...") ∈
stars ∧ u ∉ neg)` (`:57-63`); `contains_star(shape) = shape ∈ stars` (`:54`).

### 6.3 The set-engine `check`

The engine (`setengine/engine.py`, out of this doc's line budget but extracted in
the prior audit) evaluates the AST pointwise exactly like §5: `Union→any`,
`Intersection→all`, `Exclusion→base ∧ ¬sub`, `Direct` = tuple lookup with wildcard
match, `Computed` = recurse, `TTU` = stored-parent loop; recursion well-founded by
`(stratum, AST-size)`. **T1** proves `SetEngineModel.check S T q = sem S T q`. The
`MemberSet` algebra lemmas (each op's `ext` equals the set-theoretic op on `ext`s,
incl. ghost/star members via `contains_*`) are the workhorses; they are exactly
what `memberset.py`'s brute-force property suite checks (`memberset.py:31-32`), so
Lean is proving what tests already sample. The interner/id-recycling layer
(`engine.py` `Interner`) is **out of scope** (plan §1) — the model works over
abstract `(type,name,predicate)` keys.

---

## 7. Graph index model — materialized closure + residues + cascade

Sources: `index_v4/{core,wildcard,processor,invariants,models}.py`;
`theory.md:9-133`; `wildcard-materialization-spec.md`; `graph-boolean-ivm-spec.md`.
This is the largest and hardest model (plan Phase 4, ~half the effort).

### 7.1 The object: path-counted DAG closure (`theory.md:9-66`)

A directed acyclic **multigraph** over typed nodes. The closure materializes, per
ordered pair with ≥1 path, a row with two counters
(`models.py:57-77`, `core.py`):

```
d(u,v) = direct_edge_count   = # parallel direct edges u→v (multigraph multiplicity)
p(u,v) = indirect_edge_count = # distinct directed paths u→v (incl. direct)
```

Reachability = `p(u,v) > 0`. Invariant: `p ≥ d`, `p > 0` on any live row, zero rows
deleted (`core.py:93-94,139-140,131-134`; `theory.md:16-24`; I1). `check` is a point
read.

### 7.2 The counting theorem (`theory.md:26-61`) — basis of T4

In a DAG a path uses each edge at most once, so for a new direct edge `e=(u,v)`,
paths using `e` biject with pairs (path a→u, path v→b), empty paths included. With
`p̂(x,x)=1`:

```
insert e:  p'(a,b) = p(a,b) + p̂(a,u)·p̂(v,b)      ∀ a,b
delete e:  p'(a,b) = p(a,b) − p̂'(a,u)·p̂'(v,b)     (products over graph WITHOUT e)
```

Counts live in the group `(ℤ,+)`, so delete is the exact inverse of insert — no
re-derivation (`theory.md:48-56`). **Acyclicity is a hard precondition**: with a
cycle, counts diverge and the bijection fails (`theory.md:57-61`). This is
theorem **T4** and its precondition.

**The load-bearing op ordering** (`core.py:155-256`, extraction confirmed): on
**remove**, decrement the direct edge FIRST (`:158-160`) then snapshot neighbor
path-counts and expand; on **add**, snapshot+expand then increment the direct edge
LAST (`:218-220`). This keeps the mutating edge out of the
`reachable_before_subject`/`reachable_after_object` snapshots (`:188-205`), so the
products never count paths through `e` itself (`theory.md:44-47`). The three
expansion updates (`:207-216`) are exactly the cross/left/right terms of the
theorem.

### 7.3 Cycle rejection (`core.py:319-342`) — exact, fail-closed

`_add_edge_locked`: reject a self-loop (`ValueError`, `:323-329` — deliberately a
`ValueError` not an `assert`, because under `-O` an assert would fall into the
node-deletion shortcut and corrupt the store, blind-audit C3); then a single
reverse-edge point lookup — if `p(object→subject) > 0`, reject as cycle-forming
(`:338-340`). Because the closure is complete, `p(object→subject)>0` iff subject is
reachable from object, so the check is **exact — no false accept/reject** given the
closure invariant. The model's `addTuple` returns a `Rejection` here; T4's
acyclicity precondition is thereby *enforced*, not assumed.

### 7.4 Wildcards: split w-nodes and bridges (`theory.md:69-90`, `wildcard-spec §1`)

Each wildcard-capable shape `S` gets up to two nodes: `w_any(S)` (∃-node: concretes
bridge **in** `c→w_any`, wildcard-*subject* grants leave from it) and `w_all(S)`
(∀-node: wildcard-*object* grants arrive **in**, bridges **out** `w_all→c`). There
is deliberately **no `w_any→w_all` edge** — being an instance must not grant what is
distributed to instances, and its absence makes ∀⇒∃ *strict* (a path
`x→w_all→c→w_any→y` needs a real concrete `c`) (`theory.md:79-83`,
`wildcard-spec §1.2, §3.4`). Node identity is `(store, predicate, type, name,
wildcard∈{'','any','all'})` with `name=='*' ⟺ wildcard!=''`
(`models.py:32-36,43-46`; unique constraint verbatim there). This keying is why a
`user:*` bridge for relation R cannot alias another type/relation (§ invariant I3).

### 7.5 Read path — the ≤4 probes (`wildcard.py:318-375`, `wildcard-spec §3.1`)

Non-derived `check` is **one SQL statement**: up to 4 candidate keys —
`(s,o)`, `(w_any(shape s), o)`, `(s, w_all(o.type, R))`, `(w_any, w_all)` — gated by
declared shapes, combined into one `IN (...) LIMIT 1` with `p>0`
(`wildcard.py:354-374`). A literal `'*'` endpoint maps to its own variant node and
skips its own probe. A missing node drops its keys (ghost coverage). §3.2 of the
wildcard spec gives the completeness argument (every semantic path decomposes as
leading-hop · materialized-closure · trailing-hop; interior hops are bridges).
This is **T2b** for non-derived relations.

### 7.6 Derived relations: residues (`theory.md:111-133`, `boolean-ivm-spec §4-6`)

Persisted per `(object node, derived relation)` as `ResidueV1`
(`models.py:80-107`): `stars` (JSON list of covered shapes), `neg` (concrete subject
ids star-covered-but-excluded), `upos` (userset-shaped members recorded edge-free).
The canonical membership form (`theory.md:117-133`):

```
members = edges ∪ upos ∪ ( ⋃_{σ∈stars} population(σ) ∖ neg )
```

with the **canonical representation rule** making the state UNIQUE (buys
permutation-invariance and add/remove row restoration): a star-covered subject holds
NO edge (in `neg` iff expr-false); an uncovered bare-entity subject holds an edge
iff expr-true (never in `neg`); an uncovered *userset* subject is in `upos` iff
expr-true, never an edge (a derived edge from a userset node would leak through the
closure to every member and defeat pointwise exclusion — blind-audit P4).

**Derived read path** (`wildcard.py:398-432`, extraction confirmed):
- object wildcard on derived → `False` (decision-15 rejected the shapes, `:400-403`).
- `s_name=='*'` → `(s_type,s_pred) ∈ stars` (intensional, 1 read, `:404-407`).
- userset subject (`s_pred!='...'`) → `subj.id ∈ upos` ? True ; else shape ∉ stars ?
  False ; else `subj.id ∉ neg` (`:411-419`) — edge-free.
- bare subject (`'...'`) → edge probe first (`check_reachable_by_id`); **an edge hit
  returns True WITHOUT consulting `neg`** (`:421-425`); else `stars`∖`neg` (`:429-432`).

**Why the edge hit may ignore `neg` (cross-module obligation, must be a proven
lemma):** the processor writes a derived edge for a subject *only when* that
subject's full boolean evaluation (incl. `but not`) is true, and `neg` only ever
subtracts from coarse star coverage — the two positive mechanisms (concrete edge vs
star-shape) are disjoint by construction. Invariant I6 enforces `neg ∩
edge-holders = ∅` (`invariants.py:252-254`). T2b must prove this disjointness from
the cascade's postcondition, not assume it.

### 7.7 The I-series invariants (state well-formedness) — `invariants.py`

`Inv σ` for the graph model formalizes these (numbers per code; note the module
docstring says "I1–I12" but the code asserts **I13** and omits I8/I9 from this
file). Extraction-confirmed list:

- **node encoding** (`:83-87`): `wildcard ∈ {'','any','all'}`; `name=='*' ⟺
  wildcard!=''`.
- **I1 count algebra** (`:89-101`): per edge `p≥d`, `p>0`, `d≥0`, both endpoints exist.
- **I2 acyclicity** (`:103-128`): direct-edge graph is a DAG.
- **direct-edge variant rules** (`:130-145`): allowed `(subj.wildcard,obj.wildcard)`
  combos; into-`w_any` and out-of-`w_all` must be same-shape concrete bridges.
- **I3 bridge completeness/exclusivity** (`:147-167`): every concrete of a bridged
  shape has its bridge; none for unbridged shapes.
- **I13 refcount = direct-degree** (`:169-183`, blind-audit C5).
- **I4 namespace classification** (`:201-206`): `.`-predicate families are declared
  leaves; no `w_all` on leaf/derived families.
- **I5 derived-flag exclusivity** (`:208-218`): `edge.derived ⟺` direct edge into a
  derived-public family, nowhere else.
- **I6 residue hygiene** (`:220-273`): residue on a derived family; `relation ==
  node.predicate`; non-empty; `stars ⊆ declared subject-wildcard shapes`; for each
  `neg` id: live, concrete, `(type,pred) ∈ stars` (**`neg ⊆ star-covered`**), and
  `neg ∩ derived-edge-holders = ∅`; for `upos`: `upos ∩ neg = ∅`, `upos ∩
  edge-holders = ∅`, each userset-shaped and not star-covered.
- **I7 residue-version monotonicity** (`:274-293`) — modulo the `version==1`
  lineage-restart escape hatch (SQLite rowid reuse).
- **I10 outbox sanity** (`:296-304`).

I8 (stratification acyclic, compile-time) and **I9 (fixpoint audit)** live
elsewhere: I9 is `processor.audit_fixpoint` (`processor.py:806-816`) and is
**test-suite-only — NOT wired into per-commit paranoia** (`invariants.py:390-403`
run only `check_invariants` + `verify_outbox_deltas`). I11/I12 (read purity,
rejection cleanliness) are differential/harness-only. **This is the single most
important cross-cutting fact for the proof (§9, §11-A1).**

### 7.8 IVM cascade — the perfect model, incrementally (`processor.py`)

- **Stratification** (`_stratify:1630-1664`): Kahn topo-layering over tainted
  derived→derived dependency edges; `Plan.stratum` assigned per layer;
  `CyclicDerivedDependency` on any leftover. Polarity-blind: `Exclusion` base and
  subtract both contribute ordinary dependency edges (`:1622-1624`).
- **`reconcile_subject`** (`:321-380`): the canonical rule — `should =
  check_fn(s)`, `covered = shape(s) ∈ stars`; userset ⇒ maintain `upos =
  should∧¬covered`, `neg = covered∧¬should`, no edges; bare-entity ⇒ `want_edge =
  should∧¬covered` (write/remove derived edge), `neg = covered∧¬should`.
- **`reconcile`** (full-object, `:382-459`): recompute `stars` (pinned star fold),
  `neg`, `upos` wholesale from committed lower-stratum state and diff — invalidation,
  not state transfer (`theory.md:103-106`). Returns True iff changed = the I9 signal.
- **`run_cascade(watermark)`** (`:694-739`): drain the outbox from the passed
  watermark; frontier advances by `max(row.id)`; `rounds = len(strata)`; per round
  process keys `sorted by (stratum, key)` so lower strata settle first; cross-stratum
  residue bumps deferred to next round via `_bumped`; on non-quiescence after the
  rounds, **raise `InvariantViolation`** (abort) — never silently continue
  (`:729-739`). Termination in ≤#strata rounds = **T5** (each round settles ≥1
  further stratum; `theory.md:107-109`).
- **Cascade-in-same-transaction is an assumed precondition, not a checked
  invariant.** Nothing structural forces `run_cascade` to run on a write; the
  commit hooks don't call it (`invariants.py:390-395`). Every production write path
  *does* call it (`connectedstore/apply.py:85-86`; `GraphBackend.apply` in the test
  matrix), and `build_index` uses `backfill`. The graph model in Lean will bake the
  cascade into each write op (so the model is always consistent); the honesty note
  (§11-A1) records that the *Python* relies on convention here.

### 7.9 Multigraph / dedup boundary (must model edges as counters, not sets)

`add_tuple` at the wildcard layer is **multigraph** — the same triple twice counts
to 2 and needs two removes (`wildcard.py:226-232`, extraction surprise #7). Zanzibar
set-idempotence lives one layer up in `connectedstore.TupleSource`
(`source.py:88-91` + the `TupleV1` unique constraint). The graph model's edges are
**multisets (ℤ counters)**; `Store` at the spec level is a set, so the graph model's
op sequence must apply the connectedstore dedup or model raw multiplicity explicitly.
Resolve per §11-A4.

---

## 8. Theorem statements — the precise hypotheses

All theorems quantify over a schema `S`, a finite store `T` (write-valid tuples),
and a query `q`. Hypotheses, named for reuse:

- `hWF : WF S` (§4.2)
- `hStrat : stratify S = some strata` (§4.4 — no claim without it)
- `hAcc : GraphAccepts S` — the graph scope predicate: no object-wildcard on a
  derived relation, no wildcard userset over a derived relation, no TTU whose
  tupleset is derived (decision-15, `boolean-ivm-spec §1.15`). Graph theorems only.
- `hReach : ReachedBy σ S T` — `σ` is the graph state reached by applying the
  writes of `T` (with cascade) from empty. Graph theorems only.
- `hValid : ∀ t ∈ T, WriteValid t` — every stored tuple passes
  `validate_write_identifiers` positional validity (§2.1).
- `hDecl : StoreDeclared S T` — every stored tuple's `(object.type, relation)`
  is declared and its subject type is among the declared restriction types
  (`Spec/Confine.lean`). The semantic half of write-validity, implied by the
  admission gate (`engine.py:_validate` (2)). **Required by T0a** — without it
  the fuel-stability statement is FALSE (machine-checked:
  `Spec/Counterexample.lean`; an admission-invalid tupleset tuple closes a
  consultation cycle stratification never sees, and `semAux` oscillates).

| ID | Statement |
|----|-----------|
| **T0a** | `∀ S T q, WF S → hStrat → Sem S T q ↔ sem S T q = true` (relational ≡ executable; well-defined, terminating). |
| **T0b** | `stratify` sound: `some strata` ⟹ dependency order respected; `none` ⟺ derived-dependency cycle exists. |
| **T1** | `∀ S T q, hWF → hStrat → hValid → SetEngineModel.check S T q = sem S T q`. |
| **T2a** | `∀ ops, (each op valid & accepted by GraphAccepts) → Inv (run ops) ∧ (run ops).materialized = materialize S (netTuples ops)`. |
| **T2b** | `∀ σ q, Inv σ → hReach σ S T → GraphModel.check σ q = sem S T q`. |
| **T3** | `hWF → hStrat → hAcc → hReach σ S T → hValid → SetEngineModel.check S T q = GraphModel.check σ q` (⟸ T1 ∘ T2b). |
| **T4** | acyclic precondition ⟹ add/remove of a direct edge preserves `p = #paths` (the counting theorem; the DAG hypothesis is enforced by §7.3). |
| **T5** | after `run_cascade`, derived state = stratified fixpoint of base state; each `but not` operand settled before its consumer reads it. |
| **T6a** | exclusion-effectiveness: `Sem S T (in subtract-operand for subject) → GraphModel.check = SetEngineModel.check = false`. |
| **T6b** | no-ghost-grant: removing the last supporting tuple ⟹ both models deny. |
| **T6c** | wildcard scoping: a `T:*` grant matches subject `u` only if `u.type = T` on that relation/object. |

T3 and T6 are corollaries proved in Lean by rewriting with T1/T2b + spec lemmas.

---

## 9. What the proof buys over the existing tests (targeting)

`correctness.md:38-67` already gives four independent evaluators + paranoia + a
hypothesis campaign. The formal effort is aimed where sampling is weakest:

1. **Unbounded generalization** — T1/T2 quantify over all `S,T,q`; tests sample.
2. **The counting-IVM-under-acyclicity crux (T4)** — the group-inverse argument
   whose failure needs a rare diamond+remove+re-add; `theory.md:48-61` states it,
   nothing proves it.
3. **Cascade settling order (T5)** and the **edge-hit-ignores-`neg` disjointness**
   (§7.6) — cross-module obligations that no single per-commit invariant checks
   (I9 is test-only).

---

## 10. Conformance plan recap (how Python is pinned to `sem`)

Per plan §6: C0 correspondence table (Lean def ↔ Python `file:line`); C1 six-way
answer conformance (Lean spec + 2 Lean models + oracle + 2 Python backends, on
answers AND rejection outcomes) over the matrix/scenario corpora + hypothesis cases;
C2 graph state-level conformance (edge counts + residues dumped and compared
structurally — the strong signal); C3 exhaustive small-scope enumeration; C4 CI
gates (zero `sorry`, axiom audit, conformance green). The Lean spec is
**executable** so the same artifact is proof subject and CLI oracle.

---

## 11. Ambiguities & resolutions (for the checkpoint)

Each must be resolved or escalated before Phase 1 Lean. Proposed resolutions given;
**A1, A4 want explicit user sign-off.**

- **A1 — Cascade-as-precondition vs invariant.** The Python relies on *convention*
  that every boolean write runs `run_cascade` in-txn; I9 (the only fixpoint check)
  is test-only (§7.8, §7.7). *Proposed:* the Lean graph model bakes the cascade into
  each write op (so `Inv` always holds and T2 is provable), and we record in
  `formal/README.md`'s honesty section that the Python's fixpoint correctness rests
  on that always-call convention, not a per-commit gate. This means T2 proves the
  *algorithm* correct; it does **not** prove the Python never forgets to call it.
  **Escalate: is that scope boundary acceptable, or do you want a Phase-7-style check
  that the write paths always cascade?**
- **A2 — Provisional-False recursion vs stratum iteration.** The oracle uses
  Tarjan-lowlink provisional-False; the plan proposes per-stratum fixpoint iteration.
  *Proposed:* define the executable `sem` by stratum iteration (cleaner to prove
  T0a/terminating), and prove it agrees with the oracle by conformance C1 rather than
  by matching the oracle's exact control flow. For stratifiable schemas the two
  coincide; that coincidence is asserted empirically, not proven. Acceptable because
  the oracle is being *demoted*, not verified.
- **A3 — Undefined reference = empty (spec) vs compile-reject (graph).** The oracle
  treats an undeclared `(o_type, rel)` as constantly False (`oracle.py:360-363`); the
  production compiler may reject. *Proposed:* `sem` follows the oracle (undefined ⇒
  empty); fold "compiler rejects" into `WF S` so graph theorems never see such a
  schema. Verify the compiler's actual behavior in Phase 0.5 and adjust `WF`.
- **A4 — Store as set vs graph multigraph.** The spec `Store` is a set; the graph
  layer counts multiplicity, with idempotence added by `connectedstore`
  (§7.9). *Proposed:* the graph model op sequence applies connectedstore-style dedup
  (add is a no-op if the tuple is present; remove deletes) so its edge multiplicities
  stay in `{0,1}` per tuple and match the set semantics. **Escalate: confirm we model
  at the connectedstore (deduped) boundary, not the raw multigraph `WildcardIndex`
  boundary** — this changes which Python `add_tuple` the correspondence table points
  at (source.py vs wildcard.py).
- **A5 — `-O` assert-stripping.** Several core invariants are `assert`s
  (`core.py` counting/refcount/dangling-edge; §7.2, extraction surprise #4). The Lean
  model treats them as *proven* postconditions; the honesty note records that the
  Python only *checks* them when assertions are enabled. No proof impact; documentation
  only.
- **A6 — Interner/id-recycling & SetOps out of scope.** Confirmed non-goal (plan §1);
  the set-engine model uses abstract keys. The prior security audit found the
  recycling sound; conformance C2/existing property tests cover it. No spec impact.
- **A7 — Object-wildcard shapes have no DSL syntax.** They enter via
  `object_wildcard_shapes` constructor args (CLAUDE.md gotcha). The spec must take
  the object-wildcard shape set as a *parameter* of `S`, not parse it from the DSL.

---

## 12. Glossary

- **`sem` / perfect model** — the stratified-Datalog¬ least-fixpoint denotation of
  `(S, T, q)`; THE definition of correct (§1, §5).
- **taint / derived** — a relation reaching a boolean operator; changes the graph
  *representation*, never `sem` (§4.3).
- **residue** `(stars, neg, upos)` — the canonical star-closed member set per
  (object, derived relation) (§7.6).
- **counting theorem** — `p' = p ± p̂·p̂`; basis of exact incremental closure (§7.2, T4).
- **strict ∀⇒∃** — "granted on all S" ⟹ "reaches some S" only if a concrete instance
  exists (§5.4, §7.4).
- **Adjudication event** — any disagreement between spec/oracle/backends: stop and
  ask the user (plan §8.2).
