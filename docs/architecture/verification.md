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

Default ON while prerelease (wired via `tests/wildcard_helpers.make_wildcard_index`;
`paranoia=False` for benchmarks or deliberate-corruption tests). Inside every
`session.commit()`:

* **pre-commit** (in-transaction; violation aborts): invariant checker + the
  delta-scoped verifier (§8.3: per outbox row, BFS over direct edges vs closure row
  vs claimed flip);
* **post-commit** (fresh session, same bind): checker again — catches
  commit-boundary/session-state bugs.

Invariants: I1 count algebra (`indirect >= direct > 0`-family), I2 direct-edge
acyclicity, I3 bridge hygiene, I4 namespace classification (leaf-style predicates
must be declared leaf families), I5 derived-flag exclusivity, I6 residue placement
(stars ⊆ declared shapes; neg concrete + star-covered + disjoint from edge holders;
upos userset-shaped + uncovered + edge-free + disjoint from neg; no empty rows), I7
residue-version monotonicity (per row lineage), I8 stratification (compile-time), I9
fixpoint audit (`DeltaProcessor.audit_fixpoint`, run per-op by the matrix/parity
graph backends), I10 outbox well-formedness, I11 read purity, I12 rejection
cleanliness, I13 refcount = direct-edge degree. Costs ~2x suite time.

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
