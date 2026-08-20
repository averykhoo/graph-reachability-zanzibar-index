# Verification machinery

The repo's correctness story is layered redundancy: an independent oracle, a
lockstep matrix, per-commit invariants, delta-scoped verification, and fuzzing.
**Never edit a golden or oracle result to make a refactor pass** — the oracle and
goldens ARE the behavioral spec.

## The oracle (`tests/oracle.py`)

Pointwise, boolean-aware reference. **Independence contract**: imports nothing from
the backends and parses the DSL itself, so one parser bug can't corrupt both sides of
a comparison. Stateless (rebuilt from the raw-tuple multiset per comparison) and
check-only — no lookups, no mutation. When the matrix disagrees, the oracle is ground
truth; an engine is wrong until proven otherwise. Notable pinned semantics readable
straight from it: strict ∀⇒∃ (`universe()` witnesses), intensional `'*'`
(`direct_leaf`), stored-tuple TTU parents (`ttu_leaf` iterates raw tuples).

## The validation matrix (`tests/test_matrix.py`)

What "same semantics" *means* here: after every op of randomized walks, unanimous
accept/reject across backends and identical `check` over a full query grid
(universe ∪ ghosts ∪ `'*'`), under both `SetOps`. Since the boolean-IVM flip the
boolean fixture stores run with the graph included (processor-maintained,
I9-audited per op); since the connected-store round, **`ConnectedBackend`** (the
composed system: tuple log + synchronously-maintained index) sits in the same
matrices — graph · connected · oracle · set engine × both `SetOps`. The demorgans
trio compares oracle · set engine · graph pointwise on every relation.

## ParityEngine (`tests/parity.py`)

The default engine for integration-style tests: one façade over oracle + set engine
(both `SetOps`) + graph (joins automatically when the schema compiles; its writes run
the cascade in-transaction). Per op: unanimity, I12 row-multiset snapshots on
rejection, full-grid check parity vs the oracle. Raw-tuple set semantics live here
(duplicate add = idempotent no-op).

## Paranoia mode (`index_v4/invariants.py`)

Default ON while prerelease **in the TEST harness only** — it is wired by
`tests/wildcard_helpers.make_wildcard_index` and `tests/test_connectedstore.py`, and by
nothing else: `index_v4/invariants.py::install_paranoia` has exactly those two callers, and
`ConnectedStore.__init__` never calls it and exposes no flag. So a production deployment
runs with this entire layer dark. (`paranoia=False` for benchmarks or
deliberate-corruption tests.) Inside every `session.commit()`:

* **pre-commit** (in-transaction; violation aborts): `check_invariants` + the
  delta-scoped verifier (§8.3: per outbox row, BFS over direct edges vs closure row
  vs claimed flip);
* **post-commit** (fresh session, same bind): `check_invariants` again — catches
  commit-boundary/session-state bugs.

**What `check_invariants` actually runs** (read off the function body, 2026-07-26 — its
own docstring says "I1–I6 + I10" and is wrong, and two docs used to give two other
lists): node encoding, then **I1, I2**, then via `_check_derived_invariants` **I3, I13,
I4, I5, I6, I7** (the schema-dependent ones, gated on `schema_info` being supplied), then
via `_check_outbox_sanity` **I10**. That is **I1–I7 + I10 + I13**. Where a doc and the
code disagree, the code wins.

The full invariant vocabulary, and where each is actually checked:

| | invariant | checked where |
|---|---|---|
| I1 | count algebra (`indirect >= direct > 0`-family) | `check_invariants`, per commit |
| I2 | direct-edge acyclicity | `check_invariants`, per commit |
| I3 | bridge hygiene | `check_invariants` (needs `schema_info`) |
| I4 | namespace classification (leaf-style predicates must be declared leaf families) | `check_invariants` (needs `schema_info`) |
| I5 | derived-flag exclusivity | `check_invariants` (needs `schema_info`) |
| I6 | residue placement (stars ⊆ declared shapes; neg concrete + star-covered + disjoint from edge holders; upos userset-shaped + uncovered + edge-free + disjoint from neg; no empty rows; no dead node ids) | `check_invariants` (needs `schema_info`) |
| I7 | residue-version monotonicity (per row lineage) | `check_invariants` (needs the caller's `residue_versions` dict) |
| I8 | stratification | **compile time**, not per commit |
| I9 | fixpoint audit (a second reconcile changes nothing) | `DeltaProcessor.audit_fixpoint`, run per-op by the matrix/parity graph backends — **not** by `check_invariants` |
| I10 | outbox well-formedness | `check_invariants` → `_check_outbox_sanity` |
| I11 | read purity | test-level assertions, not per commit |
| I12 | rejection cleanliness (row-multiset snapshots) | test-level, per op in the matrix/ParityEngine |
| I13 | refcount = direct-edge degree | `check_invariants` (needs `schema_info`) |

Costs ~2x suite time.

## Snapshots (`tests/test_compile_snapshot.py`)

Byte-identity gate over compiled RuleSets for every fixture. Untainted compilation
must never drift; a drift is a regression until proven intentional (then delete the
golden, regenerate, and log it in `docs/spec-deviations.md`).

## Hypothesis campaign (`tests/test_hypothesis.py`)

Generated stratifiable schemas + metamorphic pairs (`A∖B ≡ A∖(A∧B)` etc.),
add-then-remove row-multiset restoration, permutation invariance, cascade
replay-from-zero, boundary cases (self-referential wildcards both orientations), and
a stateful machine driving a ParityEngine. Profiles: `ci` (default, small) /
`HYPOTHESIS_PROFILE=deep` (local/nightly). **Freeze every shrunk counterexample as a
named regression** — the two found so far live in `test_processor.py::
test_regression_public_node_gc_on_add_remove` and `test_parity_engine.py::
test_regression_duplicate_raw_add_is_idempotent`.

## Connected-store suites

`tests/test_connectedstore*.py`: schema write-once + self-describing opens; log ≡
applied writes + replay; cross-half write atomicity (injected index-half failure,
evaluator self-heal); built-vs-live equivalence; async lag → catch-up →
convergence with crash-retry exactly-once; concurrent-writer convergence and
torn-read detection on file-backed SQLite (WAL + real BEGIN semantics).
`tests/test_openfga_json.py`: JSON twins parse to identical ASTs + loud rejections.

## Handwritten anchors

`tests/scenarios/__init__.py`: declarative scenario tables where every expected
boolean is computed by hand with a justifying comment — the human anchor the
automated layers hang off.

## Formal (machine-checked) verification

Everything above is the **Python-side** redundancy. A separate, deeper layer lives
under [`../../formal/`](../../formal/): a **Lean 4 proof** that the set-engine and
graph-index **algorithms** (modeled in Lean) compute the stratified-Datalog¬ semantics
`sem` and are therefore equivalent — machine-checked and axiom-audited. The Python
implementations are pinned to those models by a conformance harness (the Lean spec is
executable, so the same artifact is both proof subject and CLI oracle) that reuses this
oracle's parser for independence, plus state-level equality and small-scope enumeration.
Set engine is proved at full scope; the graph index at a documented fragment of what the
Python accepts. **On stores written through the `Direct` arm of a derived def
(`can_view: [user] but not blocked`) the graph-side theorems used to hold VACUOUSLY —
no theorem there at all — until E-chain legs 5+6 (2026-08-05) rebased the
admission/fragment bundles; T2a `graph_reached_inv` alone is still vacuous there**
(`formal/FINAL_REVIEW.md` §3.0). It never
rounds up to "the code is formally verified". Two whole subsystems have no Lean model:
the **bulk build/backfill** constructor (the default `build_index` path, netted only by a
Python-vs-Python differential identity gate) and the **multi-instance/HA** layer (locks,
lock ordering, replica log tailing).

- [`../../formal/ARCHITECTURE.md`](../../formal/ARCHITECTURE.md) — the topical map
  (trust root, models, theorem table + scopes, how Python is pinned, residual surface).
- [`../../formal/FINAL_REVIEW.md`](../../formal/FINAL_REVIEW.md) — the authoritative,
  clause-checked claim (exactly what is and is not proved).
