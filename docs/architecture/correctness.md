# The correctness argument

What "correct" means here, why we believe it, and — honestly — where belief rests
on arguments vs. machinery vs. nothing. Companion to `theory.md` (the math) and
`verification.md` (the tooling).

## 0. The contract

For every store: after any accepted op sequence, every backend answers every
`check` query identically to the reference semantics; every backend accepts and
rejects the same op sequences (validity parity); a rejected or failed op changes
nothing observable (atomicity, I12); and under the async schedule, a caught-up
index is indistinguishable from a synchronously-maintained one.

The reference semantics is not a paper document — it is the **oracle**
(`tests/oracle.py`): a pointwise, boolean-aware evaluator with no shared code with
either backend (own parser, stdlib only). When implementations disagree, the oracle
is ground truth by definition; an engine is wrong until proven otherwise.

## 1. What is correct *by construction* (arguments, in theory.md)

| claim | argument | machine check of the precondition |
|---|---|---|
| removal of any edge restores exact reachability | path counts form a group; insert/delete are inverses (theory §1.2) | I1 (count algebra), I2 (acyclicity — the bijection's precondition), add-then-remove property tests |
| derived relations have one well-defined meaning | stratified perfect-model semantics; compile rejects SCCs (theory §1.4) | I8 (compile-time), cascade quiescence assert |
| the cascade terminates and lands on that meaning | idempotent reconcile + finite strata (theory §1.4) | I9 (fixpoint audit: a second reconcile changes nothing) |
| identical logical states have identical rows | canonical representation rule (theory §1.5) | permutation-invariance + row-multiset restoration properties; I6 |
| star×boolean answers are exact for `'*'`, concretes, and ghosts | normal-form closure of the star algebra (theory §2.1) | the pinned table asserted by MemberSet property tests + the matrix grids (which always include ghosts and `'*'`) |
| async ≡ sync after catch-up | index state is a function of (schema, log prefix); both schedules run the same step over the same order (theory §3) | async-vs-sync equivalence tests; replay-from-zero property |
| exactly-once apply across crashes | applied rows + cursor commit atomically; applier locks before reading the cursor (theory §3) | crash-injection tests (mid-batch failure, retry) |
| the log is replayable | validity enforced at admission ⇒ log contains only appliable ops | apply-time rejection is a hard failure (`InvariantViolation`), so any violation of this claim is loud, not silent |

"By construction" never means "unverified": each argument's *preconditions* are
what the invariant machinery re-checks continuously. I1/I2 are not tests of the
counting theorem — they are tests that the store still satisfies the theorem's
hypotheses after every commit.

## 2. What is pinned *empirically* (redundant implementations)

The deepest protection is not any single check but **independent redundancy**:
four evaluators of the same function (oracle, set engine × two set
representations, graph index) plus the composed system, compared in lockstep —
unanimous accept/reject and full-grid `check` equality after *every operation* of
randomized walks, over grids that always include the universe, ghosts, and `'*'`.
A bug must now be *correlated* across independently-written evaluators to slip
through. Uncorrelated-bug independence is explicit design: the oracle shares no
parser and no set code with the backends, and the two `SetOps` implementations
share no set representation.

On top of the matrix: handwritten scenario tables (every expected boolean computed
by hand with a justifying comment — the anchor that would catch a bug *common* to
all implementations of a misunderstood semantics), metamorphic laws
(`A∖B ≡ A∖(A∧B)`, distribution, De Morgan — schema-level identities that don't
depend on any implementation), compiled-output byte-identity goldens, and the
hypothesis stateful machine. The fuzzing layer has earned its keep: it found the
pinned-node leak, the duplicate-add divergence, and (via the S4 equivalence test)
the backfill enumeration gap — all after the example-based suites were green.

## 3. Paranoia mode: making violations loud at the moment of writing

Every commit in the test suite runs, inside the transaction, the invariant checker
(I1–I7, I10) and the delta-scoped verifier (each outbox flip re-derived by BFS over
direct edges and compared to the closure row) — a violation aborts the commit — and
runs the checker again post-commit in a fresh session. This converts "eventually a
grid comparison fails somewhere downstream" into "the writing transaction itself
refuses", which is the difference between a reproducible bug and an archaeology
project. The seeded-corruption tests prove each invariant class actually fires.

## 4. Known gaps (documented, not defended)

* **The oracle itself is unverified.** Mitigations: it is small, pointwise, and
  recursion-guarded; the handwritten scenarios pin it against human-computed
  expectations; metamorphic laws constrain it independently of any implementation.
  A semantics bug shared by the oracle *and* both engines *and* the hand
  computations remains logically possible.
* ~~Latent pure-union TTU divergence~~ **closed** (review round): untainted TTU
  tuplesets with computed/rewritten arms are now rejected at compile — the OpenFGA
  model-validation approach — so the graph can no longer silently propagate
  rewrite-derived parents the raw-tuple backends never see.
* **SQLite rowid-reuse corners**: the dead-id-in-neg hazard is mitigated
  (full-reconcile pruning); I7's corner turned out to be a *false positive* (a
  same-transaction recreate reusing the max rowid), now handled by the version-1
  lineage-restart rule — the residual blind spot is an in-place regression to
  exactly version 1. Real databases with non-recycling sequences have neither.
* **Tokened reads against a stale evaluator cost a rebuild.** The `at_least`
  fallback is now watermark-aware (rebuild-on-demand, `StaleRead` when the session
  snapshot itself predates the write), which makes it *correct* across sessions —
  but each stale tokened read pays an O(live tuples) evaluator rebuild. Fine at
  human scale; a hot multi-reader deployment would want a shared invalidation
  signal instead.
* **Concurrency coverage is SQLite-shaped.** `_lock_store`/`FOR UPDATE` semantics
  on PostgreSQL/MySQL are reasoned about, not tested here; the pysqlite
  transaction quirks are worked around in tests, which means production engines
  exercise a *different* (stricter) isolation path than CI does.
* **Paranoia off = most runtime checking off.** Production would run on the
  by-construction arguments plus whatever sampling is wired then; the 2× suite
  cost is paid only while prerelease.
* **Freshness tokens lower-bound, never upper-bound.** `at_least` guarantees "at
  least this fresh"; nothing bounds staleness of un-tokened replica reads except
  the worker's cadence. That is the intended zookie semantics, but it is a
  guarantee *shape*, and callers must not read it as recency.
* **Single-writer-per-store is assumed** for the cascade (serialized by
  `_lock_store`); multi-writer throughput was never a goal and is untested beyond
  the retry-on-busy convergence tests.

## 5. How to extend without breaking the argument

New feature → say which row of §1's table it touches → keep the precondition
machine-checked (extend an invariant or add one) → add it to the matrix walk or a
metamorphic law → never edit a golden or an oracle answer to make a refactor pass
(the goldens and the oracle ARE the spec; a deliberate semantics change goes
through the deviations log and the handwritten scenarios first).
