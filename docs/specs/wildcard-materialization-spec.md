# Spec: Materialized `*` wildcard support for the reachability index

**Audience:** a coding agent working in this repository with no access to prior design discussion. Everything needed is in this document plus the repo. Read `README.md`, `zanzibar_utils_v1.py`, `index_v4/core.py`, `index_v4/models.py`, and `tests/test_integration.py` before writing code. Run `pytest` first and record the baseline (one test is `xfail`; that is expected and out of scope).

**Objective:** support wildcard entities (`user:*`, `group:*#member`, and — as a deliberate extension beyond OpenFGA — wildcard *objects* like `folder:*`) such that `check()` remains constant time: at most 4 point lookups on a unique index, independent of data size, nesting depth, or fan-out. All wildcard hops that can occur in the **interior** of a path are materialized as real edges at write time. Only the two hops touching the literal query endpoints stay virtual, covered by fixed probes.

**Non-negotiable invariant:** no read path may ever recurse, walk the graph, or issue a data-size-dependent query. If an implementation choice forces that, the choice is wrong — materialize instead.

---

## 1. Vocabulary and data model

### 1.1 Shapes

A **shape** is a pair `(entity_type, predicate)`. Every node `(predicate, type, name)` has a shape. Two families exist:

- **Subject shapes** — shapes nodes can have in subject position: bare entities `(T, '...')` and usersets `(T, P)` where `P` is a relation (e.g. `(group, 'member')`).
- **Object shapes** — always `(T, R)` where `R` is a relation defined on type `T`. Never `(T, '...')`, because object nodes always carry the relation as predicate.

### 1.2 Split wildcard nodes

Each wildcard-capable shape `S = (T, P)` gets up to **two** distinct nodes, and the distinction is the heart of the design:

- **`w_any(S)`** — "some instance of S." Instance bridge edges point **into** it (`concrete → w_any`). Grants depart **out of** it. A tuple whose *subject* is a wildcard (`user:* viewer doc:x`, `group:*#member viewer folder:f`) produces a real edge departing from `w_any` of the subject's shape.
- **`w_all(S)`** — "all instances of S." Grants arrive **into** it. Instance bridge edges point **out of** it (`w_all → concrete`). A tuple whose *object* is a wildcard (`alice viewer folder:*`) produces a real edge arriving into `w_all(folder, viewer)`.

**Position rule (uniform, no exceptions, applies to raw and rewrite-derived tuples alike):** wildcard in subject position resolves to `w_any(subject_type, subject_predicate)`; wildcard in object position resolves to `w_all(object_type, relation)`.

There is deliberately **no** `w_any → w_all` or `w_all → w_any` bridge. This is what prevents the instance leak `alice → user:* → bob` (being an instance must not grant what is distributed to instances). The composition `w_all(S) → concrete → w_any(S)` through an *existing* concrete is legal and is exactly the strict "granted-on-all implies reaches-some" semantics (§3.4).

### 1.3 Node encoding

Add a column to `NodeV4`:

```python
wildcard: str = Field(default='')   # '' | 'any' | 'all'
```

- Include `wildcard` in the unique constraint: `('store_id', 'predicate', 'type', 'name', 'wildcard')`.
- Use the empty string, **not** `NULL`, as the concrete-node default. SQLite treats NULLs as distinct in unique constraints; a nullable column would silently permit duplicate concrete nodes.
- Wildcard nodes store `name='*'` and `wildcard ∈ {'any','all'}`. Enforce in `ReachabilityIndex.node()`: `name == '*'` ⇔ `wildcard != ''`. Reject any attempt to create `name='*'` with `wildcard=''` (ValueError), so raw callers cannot smuggle in an ambiguous wildcard node.
- `node()` gains a keyword-only param `wildcard: str = ''` threaded into lookup and creation. All existing call sites are unchanged by the default.

### 1.4 Edge taxonomy (structural invariant)

Edge classification is derivable from endpoint variants alone — no new edge column:

| edge | classification |
|---|---|
| `concrete → w_any` | **bridge** (instance membership) |
| `w_any → anything` | **grant** (wildcard-subject tuple, raw or derived) |
| `anything → w_all` | **grant** (wildcard-object tuple) |
| `w_all → concrete` | **bridge** (instance distribution) |
| `concrete → concrete` | ordinary edge |
| `w_any → w_all` | grant (tuple wildcard on both sides, e.g. `user:* viewer folder:*`) |
| `concrete → w_all`, `w_any → concrete` where "concrete" is another wildcard's variant | never — reject |

A bridge into `w_any` must come from a concrete of the **same shape**; a bridge out of `w_all` must go to a concrete of the same shape. The invariant checker (§8.3) enforces all of this.

---

## 2. Schema layer (`zanzibar_utils_v1.py`)

### 2.1 Wildcard declarations

- Parse `[T:*]` and `[T:*#P]` type restrictions in `parse_relation_rule` / `parse_openfga_schema`. Each declaration marks a **subject-wildcard shape**: `(T, '...')` for `[T:*]`, `(T, P)` for `[T:*#P]`.
- Each declaration emits a **strict Filter** with `subject_name='*'` for exactly that `(relation, object_type)`. Do not loosen the existing filters: `[user]` must continue to reject a `user:*` tuple. (The existing `EntityPattern.match` wildcard-mismatch guard already gives this; keep it for filters.)
- **Object-wildcard shapes** have no OpenFGA syntax. Accept them as a constructor argument: `parse_openfga_schema(schema, object_wildcard_shapes: set[tuple[str, str]] = frozenset())` where entries are `(object_type, relation)`. Tuples with object name `'*'` are valid only for declared shapes.

### 2.2 Strict vs. permissive pattern matching — the existing bug

`EntityPattern.match` contains `if self.wildcard != entity.wildcard: return False`, so any pattern with `name=None` refuses wildcard entities. Correct for filters (validity), **wrong for rewrite rules**: with `define writer: [user:*]` and `define viewer: writer`, the writer⇒viewer rule silently drops the `user:*` subject, so wildcard grants never propagate through computed usersets or `from` chains.

Fix: add `match_wildcards: bool = False` to `EntityPattern` (and thread through `RelationalTriplePattern`). When `True` and `name is None`, skip the wildcard-mismatch guard. Every schema-generated **Rule** uses permissive patterns; every schema-generated **Filter** stays strict. Default `False` preserves behavior for all existing hand-built rulesets in the repo.

`EntityPattern.replace` / `RelationalTriplePattern.replace` need no semantic change — they already preserve the entity name (including `'*'`) when the pattern's name is `None`. Add a regression test proving a derived tuple keeps its `'*'` name through a from-rule rewrite.

### 2.3 SchemaInfo

New dataclass returned alongside (or wrapping) the `RuleSet`:

```python
@dataclass(frozen=True)
class SchemaInfo:
    subject_wildcard_shapes: frozenset[tuple[str, str]]   # (type, predicate); predicate '...' for bare
    object_wildcard_shapes:  frozenset[tuple[str, str]]   # (type, relation)

    @property
    def bridged_in_shapes(self) -> frozenset[tuple[str, str]]:
        # shapes needing concrete→w_any bridges: subject-wildcard USERSET shapes only.
        # Bare shapes (T, '...') never need in-bridges: nothing in this graph ever
        # points into a '...'-predicate node, so a bare-shape hop can only be the
        # LEADING hop of a path, which probe #2 covers virtually. This structural
        # fact is what makes plain OpenFGA [user:*] cost zero bridges.
        return frozenset(s for s in self.subject_wildcard_shapes if s[1] != '...')

    @property
    def bridged_out_shapes(self) -> frozenset[tuple[str, str]]:
        # shapes needing w_all→concrete bridges: all declared object-wildcard shapes.
        # (Sink-shape elision is a future optimization; be conservative now.)
        return self.object_wildcard_shapes
```

Keep the analysis conservative and dumb. Do not attempt static reachability analysis of the schema to elide bridges for provable sinks/sources beyond the bare-shape rule above; a few unnecessary O(1)-degree bridge edges are harmless, a missed bridge is a correctness bug.

---

## 3. Semantics (normative)

### 3.1 Check probes

`check(subject_pred, s_type, s_name, relation, o_type, o_name)` evaluates up to four edge existence lookups, ORed, short-circuiting:

| # | probe | gated on |
|---|---|---|
| 1 | `(subject) → (object)` | always |
| 2 | `w_any(s_type, subject_pred) → (object)` | `(s_type, subject_pred) ∈ subject_wildcard_shapes` and `s_name != '*'` |
| 3 | `(subject) → w_all(o_type, relation)` | `(o_type, relation) ∈ object_wildcard_shapes` and `o_name != '*'` |
| 4 | `w_any(...) → w_all(...)` | both gates above |

If a query endpoint's name is itself `'*'`, map it to its variant node (subject→`w_any`, object→`w_all`) in probe 1 and skip its own wildcard probe. Missing nodes make a probe false; they never raise — this is what makes **ghost entities** work (§3.3).

Probes are point lookups: resolve ≤4 node ids (cacheable — the wildcard-node id set per store is tiny and changes rarely), then ≤4 unique-index edge reads. That is the entire read path.

### 3.2 Why probes + interior bridges are complete

Any semantic path decomposes as: `[optional leading instance-hop at the subject] · materialized closure segment · [interior hops] · materialized closure segment · [optional trailing instance-hop at the object]`. Interior hops are materialized (bridges), so both closure segments plus everything between them collapse into a single closure row; the leading hop is exactly probe 2/4's left endpoint substitution; the trailing hop is probe 3/4's right endpoint substitution. No fifth case exists.

**Canonical worked example** (encode as a named regression test, §8.2): schema declares `[user:*]` on `viewer` for folders, object-wildcards enabled for `(folder, viewer)`; `define viewer: [user:*, user] or viewer from parent_folder` on both folder and document. Data: `user:* viewer folder:xyz` and `folder:* parent_folder doc:1`.

Materialized edges after ingestion: grant `w_any(user,'...') → folder:xyz#viewer`; the parent tuple rewrites (per the existing from-rule machinery) to subject `folder:*#viewer` → grant `w_any(folder, viewer) → doc:1#viewer`... **note**: `folder:*` here is in *subject* position of the derived triple, hence `w_any(folder, viewer)` — which requires `(folder, viewer)` to be declared a *subject*-wildcard shape (`[folder:*#viewer]`-style) for this construct; bridge `folder:xyz#viewer → w_any(folder, viewer)` exists because the shape is bridged-in and the concrete node exists.

`check(alice, viewer, doc:1)`: probe 1 misses; probe 2 looks up `w_any(user,'...') → doc:1#viewer` — present in the closure via grant → bridge → grant. **True in ≤2 lookups**, and still ≤2 lookups if the folder tree is 200 levels deep, because the closure flattened it at write time.

### 3.3 Ghost entities

An entity never mentioned in any tuple must still be covered by wildcards. Probe 2 answers for ghost *subjects* of any shape (a never-seen user against `user:*` grants; a never-seen group's `#member` against `group:*#member` grants). Probe 3 answers for ghost *objects* under an all-grant (`check(alice, viewer, folder:ghost)` hits `alice → w_all(folder, viewer)`). No node creation ever happens on the read path.

### 3.4 Strict ∀⇒∃ (pinned)

"Alice is granted on **all** S" implies "alice reaches **some** S" only if at least one concrete instance of S exists — realized structurally by `alice → w_all(S) → concrete → w_any(S)`, which requires a real concrete in the middle. With zero instances the implication does not hold. This is the **default and only** mode for this feature. Leave a documented hook (a per-shape config flag that would add a single `w_all(S) → w_any(S)` edge for the lenient/vacuous reading) but do not implement it.

### 3.5 Validity rules (writes)

1. Tuple with subject name `'*'`: shape must be in `subject_wildcard_shapes`, else `ValueError` naming the missing declaration. (Strict filters enforce this for raw tuples; the façade enforces it again for defense in depth and better messages.)
2. Tuple with object name `'*'`: `(o_type, relation)` must be in `object_wildcard_shapes`, else `ValueError`.
3. Concrete entity names equal to `'*'` are reserved everywhere; reject at the façade and in `node()`.
4. **Self-referential wildcard tuples are rejected by cycle detection, and that is correct behavior.** `group:*#member member group:g` produces grant `w_any(group,member) → g#member` while bridge `g#member → w_any(group,member)` exists — a genuine cycle (g's members would include members-of-any-group, including g's). Likewise `folder:* parent_folder folder:f`. Catch the core's cycle `ValueError` in the façade and re-raise with a message explaining that wildcard tuples whose object participates in the wildcard's own shape are unsupported by construction.

### 3.6 Cost model (document in README, do not "fix")

- Plain OpenFGA usage (`[user:*]` only): zero bridges, zero backfill, +≤3 probes on gated checks. One edge per wildcard tuple.
- Declaring a bridged-in shape (e.g. `[group:*#member]`) costs one bridge edge per concrete of that shape **plus** the closure rows connecting each bridge's ancestors to `w_any` — i.e., roughly one closure row per (member × group) even before any wildcard grant exists. Declaring a bridged-out shape is symmetric on the descendant side. **Declaration itself has a cost; only declare shapes actually used.**
- A wildcard grant on a bridged shape fans out through the closure to every instance's subtree. This is the same row count as granting each instance explicitly — the wildcard automates the fan-out; nothing can eliminate it while reads are O(1). This is the accepted trade.

---

## 4. Reference oracle (build FIRST — Phase 0)

An independent evaluator over `(schema, list_of_input_tuples)` only. It must not touch `index_v4`, the DB, edges, bridges, or `RuleSet.apply`. It **may** share the parsed schema AST (the declarative output of `parse_openfga_schema` / `SchemaInfo`) — sharing data types is acceptable; sharing evaluation logic is not. Hedge the shared parser with hand-written golden tests (§8.1) whose expected values were computed by a human, not by either implementation.

**Files:** `tests/oracle.py`, `tests/test_oracle.py`.

### 4.1 Universe

`universe(T)` = names of type-`T` entities appearing in any input tuple (either position, concrete names only) ∪ type-`T` names appearing in the current query. Query endpoints count as existing (mirrors ghost-entity semantics) but do **not** satisfy the ∃ in strict ∀⇒∃ paths for *other* entities... more precisely: the universe is recomputed per query and simply includes the query's own endpoint names; no special-casing beyond that.

### 4.2 Wildcard queries are intensional

`check(user:*, viewer, doc:x)` asks "does a grant *through the wildcard* exist," **not** "does every existing user happen to have access." (Two users each individually granted ⇒ extensional-∀ true, intensional false; the index answers intensionally and the oracle must match.) Same for object-side: `check(alice, viewer, folder:*)` = "is alice granted on all folders via a wildcard-object chain."

### 4.3 Evaluation (normative pseudocode)

Memoized recursive expansion; `seen` prevents divergence on recursive schemas. Expansion of an object node returns three sets: concrete users, visited usersets, and wildcard markers.

```
def expand(o_type, o_name, rel, seen) -> (users:{(t,n)}, usersets:{(t,n,p)}, markers:{(t,p)}):
    key = (o_type, o_name, rel);  if key in seen: return ∅;  seen |= {key}
    acc = ∅
    matching_objects = {o_name} if o_name == '*' else {o_name, '*'}
        # o_name='*' expands ONLY wildcard-object tuples (intensional, §4.2);
        # a concrete object also absorbs tuples targeting T:* (the w_all→c bridge, backward)
    for child in schema_children(o_type, rel):          # union semantics at this layer
        case direct restriction:
            for tuple (s_pred, s_type, s_name, rel, o_type, on) with on in matching_objects:
                if s_name == '*':
                    acc.markers |= {(s_type, s_pred)}
                    if s_pred != '...':                  # strict ∀⇒∃ / bridged-in shapes:
                        for g in universe(s_type):       # members-of-any = union over existing instances
                            acc |= expand(s_type, g, s_pred, seen)
                elif s_pred == '...':
                    acc.users |= {(s_type, s_name)}
                else:
                    acc.usersets |= {(s_type, s_name, s_pred)}
                    acc |= expand(s_type, s_name, s_pred, seen)
        case computed userset R2:
            acc |= expand(o_type, o_name, R2, seen)
        case tuple-to-userset (P from R2):
            for tuple (_, s_type, s_name, R2, o_type, on) with on in matching_objects:
                if s_name == '*':
                    acc.markers |= {(s_type, P)}
                    for g in universe(s_type):
                        acc |= expand(s_type, g, P, seen)
                else:
                    acc.usersets |= {(s_type, s_name, P)}
                    acc |= expand(s_type, s_name, P, seen)
    # object-side all-grants distributing to this concrete object are covered by
    # matching_objects including '*' above; nothing further needed here.
    return acc

def check_oracle(s_pred, s_type, s_name, rel, o_type, o_name):
    E = expand(o_type, o_name, rel, seen=set())
    if s_name == '*':               return (s_type, normalize(s_pred)) in E.markers
    if s_pred in ('...', Ellipsis): return (s_type, s_name) in E.users  or (s_type, '...') in E.markers
    return (s_type, s_name, s_pred) in E.usersets or (s_type, s_pred) in E.markers
```

Notes the implementer must preserve: marker matching by shape alone is what gives ghost subjects (concrete or userset) access under wildcard-subject grants; the `for g in universe` unions are what give strict ∀⇒∃ and members-of-any-group semantics; `matching_objects` including `'*'` for concrete objects is what gives all-grant distribution including to ghost objects (the queried name is in the universe by §4.1). Memoize per-query; performance is irrelevant, clarity is everything.

---

## 5. Core index changes (`index_v4`) — keep these minimal

1. `models.py`: `NodeV4.wildcard` column + widened unique constraint (§1.3).
2. `core.py::node()`: `wildcard: str = ''` keyword param; validation `('*' == name) == (wildcard != '')`.
3. `core.py`: add id-based public methods so the façade never re-resolves names:
   - `add_edge_by_id(subject_id, object_id) -> list[PermissionDelta]` — performs the same reverse-reachability cycle pre-check as `add_edge`, then `_add_direct_edge_unsafe(+1)`.
   - `remove_edge_by_id(subject_id, object_id) -> list[PermissionDelta]` — same existence check as `remove_edge`, then `(-1)`.
   - `check_reachable_by_id(subject_id, object_id) -> bool` — the edge point lookup only.
   - Refactor the existing name-based `add_edge` / `remove_edge` / `check_reachable` to delegate. Existing tests are the guard; behavior must be byte-identical.
4. **No changes** to `_add_direct_edge_unsafe`, `_add_db_edges_unsafe`, path-count math, or GC logic. Bridges are ordinary ref-counted direct edges to the core.

---

## 6. `WildcardIndex` façade (`index_v4/wildcard.py`, exported from `__init__.py`)

Owns a `ReachabilityIndex`, a `SchemaInfo`, and per-store cached wildcard-node ids. Does **not** commit; sessions and transactions remain the caller's job (mirrors `ReachabilityIndex`). All errors raise; on cycle rejection the caller's rollback restores consistency (bridge creation and grant insertion must happen in the same session/transaction — assert this in tests by forcing a failure after bridge creation and verifying rollback leaves no orphan bridges).

```python
class WildcardIndex:
    def __init__(self, idx: ReachabilityIndex, schema_info: SchemaInfo): ...
    def backfill(self) -> None                       # §7.2; idempotent
    def add_tuple(self, subject_pred, s_type, s_name, relation, o_type, o_name) -> list[PermissionDelta]
    def remove_tuple(...) -> list[PermissionDelta]
    def check(...) -> bool                           # §3.1 probes
    def lookup(self, subject_node...) -> LookupResult
    def lookup_reverse(self, object_node...) -> LookupResult

@dataclass
class LookupResult:
    node_ids: set[int]                               # concrete results
    markers: set[tuple[str, str, str]]               # (type, predicate, variant) — symbolic "all/any" results
```

- `_resolve(pred, type, name, position, create)` applies the position rule (§1.2), validates (§3.5), and returns the `NodeV4`.
- `add_tuple`: resolve both endpoints (creating concretes as needed) → `_ensure_bridges(endpoint)` for each **concrete** endpoint whose shape is bridged (idempotent: skip if the bridge edge row already exists) → `add_edge_by_id` for the grant. Bridge-before-grant ordering makes cycle errors attach to the grant (the semantically offending write), not the bridge.
- `remove_tuple`: `remove_edge_by_id` for the grant → for each concrete endpoint `c` of a bridged shape: if `c.implicit` and `c.reference_count == bridge_degree(c)`, remove `c`'s bridge edges via `remove_edge_by_id`; the core's existing implicit-GC then deletes `c` on the last decrement. `bridge_degree(c)` = `1 if shape(c) ∈ bridged_in_shapes else 0` + `1 if shape(c) ∈ bridged_out_shapes else 0`. Explicit (`implicit=False`) nodes keep their bridges for as long as they exist; `remove_node` on such a node must strip bridges via `remove_edge_by_id` **before** the core `remove_node` (whose precondition, per the README, is an otherwise edge-free node).
- `check`: §3.1. `lookup(subject)` = `lookup_reachable(subject)` ∪ (if gated) `lookup_reachable(w_any(subject shape))`; translate any wildcard node ids in the result into `markers` instead of expanding them. `lookup_reverse(object)` symmetric with `w_all` and `w_any`-in-results → "every T#P" markers. Never enumerate a marker into concretes.
- `PermissionDelta`s that mention a wildcard node id are **symbolic** ("everyone of shape S gained/lost X"). Pass them through untouched and document this in the README delta section; expansion is a future post-processing layer, out of scope.

---

## 7. Bridge lifecycle

### 7.1 Creation

Lazily, inside `add_tuple`, whenever a concrete node of a bridged shape is touched (created *or* pre-existing without its bridge — the idempotent existence check covers schema-declaration changes mid-life). `w_any`/`w_all` nodes are created lazily (`implicit=True`) on first need.

### 7.2 Backfill

`WildcardIndex.backfill()`: for each bridged shape, ensure the `w` node, select all existing concrete nodes of that shape, and add any missing bridges via `add_edge_by_id`. Chunk the loop (e.g. flush every 500) but a single transaction is fine at current scale. Called once after constructing the façade over a pre-existing store (and harmless to call always — tests should call it in every fixture).

### 7.3 GC

Covered in `remove_tuple` above. The one subtlety to test hard: a node whose **only** remaining edges are its bridges must be collected (implicit case) — otherwise every entity that ever existed leaks a bridge and closure rows forever. The row-count parity test (§8.2, `test_bridge_gc_restores_clean_state`) is the acceptance gate: build store A with a scripted add/remove sequence ending at logical state Z; build store B by adding state Z directly; assert identical `node_v4`/`edge_v4` row multisets (ignoring ids).

---

## 8. Testing

### 8.1 Golden tests (`tests/test_oracle.py`)

Hand-computed scenarios asserting oracle outputs directly — these are the check on the shared parser. Minimum: a `[user:*]` public-doc scenario, a `[group:*#member]` scenario with zero groups (strict ∀⇒∃ ⇒ False) and one group (⇒ True), and an object-wildcard hierarchy scenario. Write the expected booleans by hand in comments with the reasoning.

### 8.2 Named unit/integration tests (`tests/test_wildcard.py`, backend = v4 only; do **not** wire wildcards into v3)

- `test_public_doc_ghost_user` — `user:* viewer doc`, check a never-mentioned user ⇒ True.
- `test_user_created_after_grant` — grant first, then involve a new user in an unrelated tuple; check ⇒ True; assert no bridge edges exist for bare shapes (edge table contains no `concrete→w_any(user,'...')` rows).
- `test_undeclared_wildcard_rejected` / `test_declared_wildcard_accepted` — filters + façade validation, both positions.
- `test_wildcard_through_computed_userset` and `test_wildcard_through_from_chain` — the §2.2 propagation fix.
- `test_group_any_member_grant` — `[group:*#member]` with nested membership; include a ghost-group `#member` subject check (probe parity).
- `test_all_folders_grant_reaches_child_docs` — object wildcard distributing through the hierarchy; include a ghost-folder direct check (probe 3).
- `test_two_hop_user_star_folder_star` — the canonical §3.2 example, asserted end-to-end. This is the regression test for the whole design.
- `test_forall_implies_exists_strict` — 0 concretes ⇒ False, then add one concrete ⇒ True, remove it ⇒ False again.
- `test_no_instance_leak` — grant something to bob directly; assert alice (a fellow instance) does not acquire it via any wildcard machinery.
- `test_wildcard_cycle_rejected` — `group:*#member member group:g` raises the friendly error; store state unchanged after rollback.
- `test_revoke_wildcard_grant_revokes_all` — remove the single wildcard tuple; every beneficiary loses access.
- `test_bridge_gc_restores_clean_state` — §7.3 row-count parity.
- `test_reserved_star_name_rejected` — creating a concrete entity literally named `*` fails at façade and at `node()`.

### 8.3 Invariant checker (`tests/` helper, run after every op in scripted tests)

Asserts: `(name=='*') == (wildcard!='')` for all nodes; every in-edge of a `w_any` has a concrete same-shape subject; every out-edge of a `w_all` has a concrete same-shape object; no `concrete→w_all` or `w_any→concrete` bridge-shaped edges exist except grants per §1.4; every concrete of a bridged shape has exactly its configured bridges and no node outside bridged shapes has any; core invariants (`indirect >= direct`, `indirect > 0`) hold — port the v3-style checks.

### 8.4 Property test (`tests/test_wildcard_property.py`)

Fixed-seed randomized sequences of `add_tuple`/`remove_tuple` (only removes of currently-present tuples) over a small universe (≤4 users, ≤3 groups, ≤3 folders, ≤3 docs) against 2–3 fixture schemas including wildcards (add `tests/fga_schemas/wildcards.fga`). After every operation, compare `WildcardIndex.check` against `check_oracle` for the **full** grid of (subject ∈ universe ∪ one ghost per type ∪ wildcard names) × relations × (objects ∪ one ghost ∪ wildcard names). Run the invariant checker each step. Keep the grid small enough for CI (<5s); shrinkage on failure = print the operation sequence.

---

## 9. Phase plan

Execute in order; each phase must leave the full suite green (plus the pre-existing xfail).

- **P0 — Oracle.** `tests/oracle.py`, `tests/test_oracle.py` (goldens). No production code touched. *Done:* goldens pass; oracle imports nothing from `index_v4`.
- **P1 — Model & core.** §5 changes; refactor name-based methods onto `*_by_id`. *Done:* existing suite green, byte-identical behavior.
- **P2 — Schema layer.** §2: declaration parsing, strict/permissive patterns, `SchemaInfo`, `wildcards.fga` fixture, unit tests for parsing/matching including the §2.2 regression.
- **P3 — Façade writes.** `WildcardIndex` with `add_tuple`/`remove_tuple`/`backfill`, bridge lifecycle, validation, cycle re-raise. Invariant checker. *Done:* scripted-op invariant tests + GC parity test green.
- **P4 — Façade reads.** `check` probes, `lookup`/`lookup_reverse` with markers. *Done:* all §8.2 named tests + §8.4 property test green.
- **P5 — Integration & docs.** Wire a `V4WildcardBackend` into `tests/test_integration.py` (v3 untouched; wildcard tests skip v3). Replace the README's `*` notes with this design: position rule, probe table, validity rules, cost model (§3.6), symbolic-delta caveat, strict-∀⇒∃ pin with the lenient-mode hook noted as future.

## 10. Non-goals (do not build)

Boolean operators (`and` / `but not` — a separate check-time expression layer whose leaves will call `WildcardIndex.check`; nothing here may preclude that, and nothing here implements it). Lenient/vacuous ∀⇒∃ mode (hook only). Delta post-processing/expansion of symbolic wildcard deltas. Sink/source bridge elision beyond the structural bare-shape rule. Schema re-declaration migrations beyond idempotent `backfill()`. Any v3 support. Any read-path caching beyond wildcard-node-id memoization.
