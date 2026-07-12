# Formal Verification Plan — Set Engine, Graph Index, and Their Equivalence

**Status:** written 2026-07-09, before the build; the strategy/honesty contract of
record. **The build is well underway — a fresh working session reads
`formal/HANDOFF.md` FIRST** (the compact entry point: current state, next task,
house rules) and comes back here only for the phase definitions, process rules, and
the §7 honesty clauses (the final report uses that wording verbatim).

---

## 0. Executive summary

We formally verify the **semantic correctness** of both authorization backends —
the set engine (`setengine/`) and the graph index (`index_v4/`) — and their
**equivalence**, in **Lean 4**.

The strategy in one paragraph: we write down THE specification of Zanzibar
`check` semantics as a **stratified-Datalog least fixpoint** in Lean (§3). We
then build two *algorithm-level models* inside Lean — one mirroring the set
engine's on-demand `pos/stars/neg` algebra, one mirroring the graph index's
ref-counted materialized closure + residue read path + IVM cascade — and prove
each model **refines the spec** (returns the spec's answer on every input).
Equivalence of the two backends is then a two-line **corollary by transitivity,
entirely inside Lean** (§5, T3). The Lean spec is also **executable**, and a
conformance harness (§6) pins the Python implementations to the Lean models by
differential testing over (a) the existing test matrix, (b) hypothesis-generated
cases, (c) **exhaustive small-scope enumeration**, and (d) **state-level dumps**
of the graph index's edge table. The proven artifact is the Lean development;
the Python↔Lean link is empirical but exhaustive at small scope — this split
and its honesty conditions are spelled out in §7.

The test oracle (`tests/oracle.py`) does **not** get its own proof. It is
demoted from ground truth to cross-check: the Lean executable spec becomes the
top oracle, and the Python oracle is pinned to it by the conformance harness
(§2.3).

---

## 1. What "correct" means — the precise proof obligations

Everything below quantifies over: a **schema** `S` (well-formed, stratifiable),
a finite **tuple store** `T` (containing only write-valid tuples), and a
**query** `q = (subject, relation, object)`.

The ground-truth denotation is `spec S T q : Bool` — the stratified least
fixpoint semantics defined in §3. "Correct" means:

| ID | Theorem (informal statement) | About |
|----|------------------------------|-------|
| **T0a** | `spec` is well-defined: for every stratifiable `S` and finite `T`, the fixpoint exists, is unique, and the executable evaluator terminates and computes it. | the spec itself |
| **T0b** | The stratifier is sound: `stratify S = some strata` implies no derived relation depends (negatively or at all, per the stratification discipline the code uses) on a relation in the same or later stratum; `stratify S = none` iff a derived-dependency cycle exists. | shared compiler |
| **T1** | Set-engine model correctness: `SetEngineModel.check S T q = spec S T q` for all `S, T, q`. | `setengine/` |
| **T2a** | Graph-index state correctness: for every op sequence `ops` (adds/removes of valid tuples, accepted by the graph's scope predicate) applied from the empty state, the resulting model state `σ` satisfies the state invariant `Inv σ` (which includes `edgeCount(x,y) = number of distinct support paths x→y` and the Lean analogues of invariants I1–I12) **and** `σ.materialized = materialize S (netTuples ops)`. Incremental maintenance ≡ recompute from scratch. | `index_v4/core.py`, `processor.py` |
| **T2b** | Graph-index read correctness: for every reachable state `σ`, `GraphModel.check σ q = spec S (netTuples ops) q`. (Edge probe + residue `(stars, neg)` + wildcard bridges give the spec's answer.) | `index_v4/wildcard.py` |
| **T3** | **Equivalence** (corollary of T1 + T2b, proved in Lean by transitivity): `SetEngineModel.check S T q = GraphModel.check σ q` whenever `σ` is the state reached by writing exactly `T`. | both |
| **T4** | Counting-IVM soundness under acyclicity (the load-bearing lemma inside T2a, stated separately because it is the theorem most likely to be violated by future changes): given the node graph is acyclic — which the model, like the code, *enforces* by rejecting cycle-forming writes — add/remove of a direct edge preserves `edgeCount = #paths`. State explicitly that acyclicity is the precondition; the classic counting algorithm is UNSOUND with cycles (self-supporting counts). | `index_v4/core.py` |
| **T5** | Cascade/stratification soundness (inside T2a): after `run_cascade`, derived state equals the stratified fixpoint of the base state; in particular every `but not` operand is fully settled before any consumer reads it. | `index_v4/processor.py` |
| **T6** | Security corollaries, stated as named theorems because they are the review's headline properties: **(T6a exclusion-effectiveness)** if `spec` says the subject is in the exclusion operand, `check` on both models returns false; **(T6b no-ghost-grant)** removing the last tuple supporting an access makes both models deny; **(T6c wildcard scoping)** a `T:*` grant only matches subjects of type `T` on the granted relation/object. These are one-line consequences of T1/T2 + spec lemmas — cheap, high-communication-value. | both |

### What we deliberately do NOT prove (non-goals, with rationale)

- **The Python code itself.** No practical Python verifier handles this codebase
  (SQLModel, pyroaring, dynamic typing). The Lean models are algorithm-level
  twins; the Python link is the conformance harness (§6). Never claim the
  Python is "proven" — claim the *algorithm* is proven and the implementation is
  *conformance-tested against the proven model* (exhaustively at small scope).
- **The interner / bitmap representation layer** (`setengine/engine.py` id
  recycling, `RoaringSets` vs `PySets`). The model works over abstract keys
  `(type, name, predicate)`. Rationale: the recycling discipline was audited and
  is structurally pinned by existing tests; modeling int32 recycling buys little
  and costs a refinement layer. Covered instead by C2 state conformance + the
  existing property tests.
- **SQL, transactions, crash-recovery, concurrency** (locking, `advance_index`
  watermarks, `catch_up`, SQLite vs Postgres). These are *protocol* properties,
  wrong tool in Lean. Optional Phase 7 models them in TLA+/TLC; the core plan
  treats all state transitions as atomic, matching the single-writer-per-store
  contract the code enforces via `_lock_store`.
- **`expand` / `lookup`.** Scope is `check` only. `lookup` in the set engine is
  a verify-based semi-join over `check` and inherits its correctness; `expand`
  can be a stretch goal (T7, optional) after T3 is closed.
- **Performance, termination bounds beyond well-definedness, DoS.**
- **The oracle (`tests/oracle.py`).** See §2.3.

---

## 2. Architecture of the verification

### 2.1 Why one spec + two refinements (not direct A≡B)

Proving each backend against the shared spec gives: O(backends) proofs instead
of O(backends²); blame localization when something diverges; and protection
against the both-wrong-the-same-way failure mode that a direct A≡B proof cannot
see. T3 (equivalence) then costs nothing. **Do not** attempt a direct
model-to-model bisimulation.

### 2.2 Why Lean 4

- Single toolchain (`elan` + `lake`), works on Windows (this repo's platform).
- Definitions are **executable** (`#eval`, compiled binaries) — the same
  artifact serves as proof subject and as conformance-test oracle. This is the
  property that makes §6 possible without a second modeling effort.
- Decent automation for finite-set reasoning (`Finset` in mathlib, `decide`,
  `omega`, `simp`); our domain is finite sets and structural induction, not
  deep analysis.
- Alternatives rejected: Coq/Rocq (extraction friction on Windows, no gain);
  Isabelle (stronger automation but heavier setup, worse executable story for
  our JSON CLI needs); SMT-only (can't state the unbounded fixpoint theorems);
  TLA+ (model checking, not proof; reserved for optional Phase 7).

### 2.3 The oracle question, answered

`tests/oracle.py` needs **no proof**. Its independence was valuable when it was
the top of the trust chain; after this project the Lean spec is the top. The
oracle remains in the repo untouched, and the conformance harness (§6) runs
`LeanSpec vs oracle vs set engine vs graph index` four-way. A Lean-vs-oracle
disagreement is a **spec adjudication event** (§8.2) — one of them
misunderstands Zanzibar semantics, and a human decides using the docs/specs and
upstream Zanzibar behavior. The existing rule stands: never edit the oracle or
goldens to make something pass.

### 2.4 Trust chain after completion

```
Zanzibar semantics (docs/specs/, human review)
        │  (human review of SEMANTICS.md + theorem statements — §8.1)
        ▼
Lean spec  ──T0──►  well-defined
   │  ▲
   │  └── conformance C1/C3 pins ──►  tests/oracle.py  (cross-check, unproven)
   ├──T1──►  Lean SetEngineModel  ──C1/C3──►  setengine/  (Python)
   ├──T2──►  Lean GraphModel      ──C1/C2/C3──►  index_v4/  (Python)
   └──T3 = T1+T2 (equivalence, inside Lean)
```

The two human-review arrows (theorem statements, SEMANTICS.md) are the trust
root. Everything else is machine-checked or exhaustively tested.

---

## 3. The specification (what goes in `Spec/`)

### 3.1 Domain

Model identifiers as opaque `String`s with the distinguished sentinel `"*"`
(wildcard name) and `"..."` (bare subject predicate). Write-validity (charset,
length) is a predicate `ValidIdent` used as a *precondition* on stored tuples,
mirroring `validate_write_identifiers` — the spec does not re-derive the charset,
it takes it as given. (Reads over out-of-charset names simply never match, which
falls out of set membership over validated stores automatically.)

```
ObjectRef  := { type : String, name : String }        -- name may be "*" (object wildcard)
SubjectRef := { type : String, name : String,          -- name may be "*" (subject wildcard)
                predicate : Option String }            -- none = bare ("..."), some r = userset
Tuple      := { object : ObjectRef, relation : String, subject : SubjectRef }
Store      := Finset Tuple
Query      := { subject : SubjectRef (concrete, bare), relation : String, object : ObjectRef }
```

### 3.2 Schema AST — mirror `zanzibar_utils_v1.py`'s `SchemaAST` exactly

`Direct (allowed : List SubjectShape)` (shapes: bare type, type#relation
userset, `type:*` wildcard) · `Computed rel` · `TTU (tupleset, computed)` ·
`Union / Intersection (children, len ≥ 2)` · `Exclusion (base, subtract)`.
Well-formedness `WF S`: referenced relations declared, no `.` in declared
names, intersection/union arity ≥ 2, TTU tuplesets are direct-only (the
stored-parent rule), the scope rules the code enforces. Copy the rules from
`_validate_ast_references` / `_validate_ttu_tuplesets` — during Phase 0,
enumerate them into SEMANTICS.md with file:line citations.

**TTU semantics (the known trap, get it right in the spec):** TTU parents are
STORED tupleset tuples, never computed membership. A TTU over a relation with
no direct restrictions is constantly empty. This is oracle-pinned; encode it
as: `TTU t c` holds for `(u, obj)` iff ∃ stored tuple `(obj, t, parent)` with
`parent` a concrete bare subject, and `spec` grants `(u, c, parent-as-object)`.

### 3.3 Semantics — stratified least fixpoint, defined twice

Define **both** and prove them equal (this equality is most of T0a):

1. **Relational spec** `Sem : Schema → Store → Query → Prop` — per stratum, an
   inductive definition (monotone within a stratum, negation only on earlier
   strata). This is the version theorems quantify over.
2. **Executable spec** `sem : Schema → Store → Query → Bool` — iterate a
   monotone step function on `Finset` until fixpoint, stratum by stratum. Since
   the reachable universe from a finite store is finite, iteration terminates
   with an explicit fuel bound (`|universe|` per stratum) and a lemma that fuel
   suffices. This is the version the CLI (§6) runs, and `decide`-style proofs
   use.

Wildcards in the spec: a query subject `u` matches a stored subject `T:*` iff
`u.type = T` (and the shape is allowed by the Direct restriction); an object
wildcard `folder:*` grants on every object of that type per the code's
`object_wildcard_shapes` gating. Intensional queries (subject = `*`) follow the
set engine's documented star-query semantics — Phase 0 must pin these from
`tests/oracle.py` + `docs/specs/set-engine-spec.md` before formalizing.

Non-stratifiable schemas: `stratify S = none` → the spec is **partial** (no
semantics claimed). The Python engines evaluate cycles with provisional-False
lockstep semantics; that behavior is explicitly OUT of the verified envelope.
The theorems all carry `stratify S = some strata` as hypothesis. (The audit
already flagged cyclic schemas as "reject upstream if it matters.")

---

## 4. The two models

### 4.1 `SetEngine/` — the algebra model (mirrors `setengine/memberset.py` + `engine.py` eval)

- `MemberSet := { pos : Finset SubjKey, stars : Finset TypeKey, neg : Finset SubjKey }`
  with the invariant `neg ⊆ starPop stars ∧ pos ∩ neg = ∅` (copy the real
  invariant from `memberset.py` — Phase 0 documents it).
- Operations: union, intersection, difference, star-closure — transcribe the
  renormalization recipe the audit identified (`E := extension; pos := E −
  starpop; neg := starpop − E`). Prove the algebra lemmas: each op's extension
  equals the set-theoretic op on extensions, including ghost/star members.
  These are the workhorse lemmas of T1 and are independently valuable.
- `SetEngineModel.check`: structural recursion over the schema AST exactly as
  `engine.py`'s `member_of`/`check` does (pointwise: Exclusion = `base && !sub`,
  Intersection = `all`, TTU = stored-parent loop, Direct = tuple lookup with
  wildcard match). Recursion is well-founded by (stratum, AST-size) — same
  argument as the code's memo/stratification.
- **T1 proof shape:** induction over strata, then over the AST, with the
  algebra lemmas discharging each node type. The fixpoint connection: within a
  stratum, pointwise evaluation of a monotone system equals its least fixpoint
  on finite domains — prove once as a reusable lemma.

### 4.2 `GraphIndex/` — the state-machine model (mirrors `index_v4/`)

State (abstract, no SQL):

```
GraphState := {
  edges    : (NodeKey × NodeKey) → ℕ         -- direct count + indirect count (two maps,
  direct   : (NodeKey × NodeKey) → ℕ         --  mirroring EdgeV4's two counters)
  bridges  : ...                              -- materialized * bridges (w-nodes)
  residues : NodeKey → Option Residue         -- Residue := (stars : Finset ..., neg : Finset ..., upos : ...)
  outbox   : List Delta                       -- for the cascade model
}
```

NodeKey mirrors the `(store-scoped) (type, name, predicate)` node identity,
including w-node variants — copy the identity scheme from `index_v4/models.py`
(the unique-constraint key) during Phase 0.

Operations (each a pure function `GraphState → GraphState ⊕ Rejection`):
`addTuple`, `removeTuple`, `removeNode`, each inlining the closure maintenance
loops from `core.py:_add_direct_edge_unsafe` (path-count expansion:
`paths(X→s) × paths(o→Y)`; remove decrements direct FIRST, add increments
LAST — preserve this ordering, it is load-bearing for T4), bridge
ensure/teardown from `wildcard.py`, and `runCascade` from `processor.py`
(reconcile + per-stratum drain to quiescence, `rounds = |strata|`).

Cycle rejection: `addTuple` returns `Rejection` when the edge would close a
cycle, exactly as `core.py:_add_edge_locked` does. The model is only defined on
the acyclic reachable set — that is a *feature* (T4's precondition is enforced,
not assumed).

Scope predicate: the model carries `GraphAccepts S : Prop` mirroring
`UnsupportedByGraphIndex` rejections (object wildcards on derived relations,
wildcard usersets over derived relations). T2 theorems hypothesize
`GraphAccepts S`.

**Invariant `Inv σ`** (the induction workhorse; formalize the I-series):
- `I-count`: `σ.edges (x,y) = #(distinct support paths x→y)` in the direct
  multigraph — the heart of T4.
- `I-acyclic`: direct graph acyclic.
- `I-bridge`: bridge completeness + exclusivity (I3).
- `I-residue`: residue hygiene — `neg ∩ edgeHolders = ∅`, `upos ∩ neg = ∅`,
  `neg ⊆ starCovered` (I6) — this is what makes the read path's early-return
  safe (T2b), per the audit.
- `I-derived-exclusivity` (I5): only cascade writes derived-family incoming edges.
- `I-quiescent`: outbox empty at operation boundaries.

**Proof shape:** T2a = induction over op sequences: each op preserves `Inv` and
maintains `materialized = materialize(spec, netTuples)`. T4 and T5 are the two
hard preservation lemmas. T2b = for `Inv`-satisfying quiescent states, the read
path (edge probe, else residue stars/neg/upos consultation, else bridge-mediated
reachability) returns `spec`'s answer — a case analysis powered by I-residue +
I-count.

Expected hard spots (budget accordingly): the path-count expansion lemma for
diamonds/multigraphs (T4 core — do the `remove_node` variant last, it's the
messiest); cascade convergence in `|strata|` rounds (T5 — prove "one round
settles one stratum" as the induction step); the residue read-path case
analysis (many cases, each shallow).

---

## 5. Equivalence — inside Lean

```lean
theorem backend_equivalence
    (hWF : WF S) (hStrat : stratify S = some strata) (hAcc : GraphAccepts S)
    (hReach : ReachedBy σ S T) (q : Query) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [T1 hWF hStrat, T2b hWF hStrat hAcc hReach]
```

That's the whole point of the shared-spec architecture. Also derive T6a–c here
as named corollaries with readable statements — they are what a security
reviewer will actually read.

---

## 6. Pinning Python to the proof — the conformance harness

The refinement gap ("how do we know the Python matches the Lean model?") is
closed empirically, four ways. This is honest engineering, not proof — see §7.

**C0. Correspondence document.** `formal/CORRESPONDENCE.md`: a table mapping
every Lean definition to its Python twin with file:line (e.g.
`GraphIndex/Ops.lean addTuple ↔ index_v4/core.py:_add_direct_edge_unsafe
155-256`). Reviewed whenever either side changes. The Lean models must be
written to *mirror the Python's structure* function-by-function — resist the
temptation to write the "mathematically nicer" version; the nicer version is
the spec, which already exists. Deviations (e.g. no interner) get a rationale
row.

**C1. Answer conformance.** A Lean CLI binary (`formal/lean/…/Cli.lean`,
JSON on stdin → JSON on stdout, using `Lean.Data.Json`) exposing:
`{schema, ops[], queries[]} → {outcomes}` where outcome per op is
`applied | rejected(class)` and per query is `allow | deny`, evaluated by BOTH
the executable spec and each model. A pytest harness
(`formal/conformance/test_conformance_spec.py`) runs the same cases through the
Python oracle, set engine, and graph index (reusing `tests/parity.py`'s
ParityEngine fan-out) and asserts six-way agreement — including agreement on
*rejections* (cycle writes, scope rejections, invalid identifiers), which are
part of the security surface.
Case sources: (a) every schema/tuple-set in `tests/test_matrix.py` and the
scenario suites; (b) hypothesis-generated cases (reuse the generators in
`tests/test_hypothesis.py`); (c) small-scope exhaustive (C3).

**C2. State conformance (graph index only — the strong signal).** After each op
sequence, dump the Python graph index's abstract state — edge table with
(direct, indirect) counts, w-nodes/bridges, residue rows `(stars, neg, upos)` —
via a small test-only extractor, normalize node ids to `(type,name,predicate)`
keys, and compare **structurally** with `GraphState` from the Lean model run on
the same ops. Answer conformance can pass by luck; state conformance can't.
This is also the guard for the not-modeled representation layers.

**C3. Small-scope exhaustive enumeration.** The bug classes here (refcount
diamonds, exclusion leaks, bridge teardown, residue anchoring) all manifest at
tiny scope. Enumerate ALL cases up to bounds rather than sampling:
- Schemas: all ASTs over ≤ 2 types, ≤ 3 relations, AST depth ≤ 2, drawn from
  {Direct(bare), Direct(+userset), Direct(+star), Computed, TTU, Union₂,
  Intersection₂, Exclusion} — deduplicated by unparse-normal-form.
- Stores: all subsets of a candidate tuple pool of size ≤ 8 over 2–3 subjects
  (+ `*`), executed as add/remove sequences (not just final states — order
  matters for the index), with sequence length ≤ 5 as ops-sequences and full
  power set as final-states.
- Queries: full grid (every subject × relation × object incl. star queries).
Tune the bounds to keep the suite ≤ ~10 min; report the achieved bounds in the
final docs. Mark the suite `@pytest.mark.slow` if needed, but it must run in CI.

**C4. CI gates.** (i) `lake build` green with **zero `sorry`** in the T0–T6
chain (during development, `sorry`s are tracked in PROOF_STATUS.md's ledger and
gated to never increase); (ii) `#print axioms` audit on every T-theorem — only
`propext, Classical.choice, Quot.sound` allowed, no custom axioms; (iii) the
conformance pytest suite green under the repo conda env.

**Drift protocol:** any future PR touching `setengine/`, `index_v4/`, or
`zanzibar_utils_v1.py` semantics must update the Lean twin + CORRESPONDENCE.md
or explicitly record the divergence. The conformance suite is the tripwire that
makes forgetting this loud.

---

## 7. Honesty clauses — what the final claim is

When done, the correct claim is exactly this, no more:

> The set-engine and graph-index **algorithms**, as modeled in Lean at the
> level of `CORRESPONDENCE.md`, are **proven** to compute stratified-Datalog
> Zanzibar semantics and hence to be equivalent (machine-checked, axiom-audited).
> The **Python implementations** are pinned to those models by structural
> correspondence review, six-way differential conformance including state-level
> equality, and exhaustive small-scope enumeration up to the documented bounds.
> Residual unverified surface: the interner/bitmap representation layer, the
> SQL/transaction/concurrency layer (optional TLA+ phase), non-stratifiable
> schemas, `expand`/`lookup`, and the fidelity of the model-to-code
> correspondence itself.

Never let a summary round this up to "the code is formally verified."

---

## 8. Process rules for the executor (Opus) — read carefully

### 8.1 Human checkpoints (STOP and wait for user review)

1. **End of Phase 0:** SEMANTICS.md complete → user reviews before any Lean is
   written. Wrong spec = everything downstream is wasted.
2. **End of Phase 1:** the *statements* of T0–T6 (with all hypotheses) compile
   with `sorry` bodies → user reviews the statements. Statements are the trust
   root; proofs can't be wrong if they compile, but statements can be vacuous
   or weaker than intended. Specifically check: no accidentally-empty
   hypothesis sets, quantifiers over the right things, `Rejection` outcomes not
   silently excluded.
3. **Any spec adjudication event** (§8.2).
4. **End of each later phase:** short written status + next-phase go/no-go.

### 8.2 Spec adjudication events

If at any point the Lean spec, the oracle, and/or a backend **disagree** on a
case (conformance failure), or a theorem is unprovable because the code's
actual behavior differs from the drafted spec: **STOP. Do not** edit the
oracle, goldens, or Python semantics; **do not** quietly weaken the theorem or
the spec to match. Write the divergent case up in
`formal/history/PROOF_STATUS.md#adjudications` (schema, ops, query, each system's
answer, your analysis of which is right per docs/specs), and ask the user.
Every adjudication is potentially a real bug found — that is the project
succeeding, not failing.

### 8.3 Working discipline

- **PROOF_STATUS.md is the session-persistent brain.** Maintain: current phase
  + resume point; theorem ledger (name, status ∈ {stated, sorry, proved,
  blocked}, blocking reason); sorry count per file (must be monotonically
  non-increasing within a phase); adjudication log; decisions made with
  rationale. Update it before ending ANY session.
- Small lemmas, small commits. Each commit compiles (`lake build` green — a
  `sorry` compiles; a syntax error does not). Commit messages: `formal: <what>`.
  Do not push unless asked (per repo rules).
- If stuck on a proof > ~2 hours of effort: leave `sorry`, record the precise
  stuck point + attempted tactics in the ledger, move to the next lemma. Do not
  spiral. Batch stuck proofs for a harder push or user discussion.
- Never weaken a theorem statement to close a proof without logging it as a
  decision and flagging for review.
- The Python side is READ-ONLY for this project, with one exception: the
  test-only state extractor for C2 (a new file under `tests/` or
  `formal/conformance/`, no changes to `setengine/` / `index_v4/` modules), and
  the conformance pytest files. Run the existing full suite
  (`"C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe" -m pytest -q`)
  before claiming any phase that touched Python files is done.
- Toolchain installs (elan/Lean/lake, anything global): **ask the user first**
  (repo rule: confirm before installing). Lean lives outside the conda env; the
  conformance harness runs under the repo conda env. Pin the Lean toolchain in
  `formal/lean/lean-toolchain` and mathlib (if used — prefer core-only + `std`
  if feasible, mathlib only if `Finset` ergonomics demand it, which they likely
  do) in the lake manifest.
- Windows notes: `lake` and `elan` work natively; use forward-slash paths in
  lakefiles; the CLI binary lands in `.lake/build/bin/`. If native Lean proves
  flaky, discuss WSL with the user before switching.

### 8.4 Repository layout to create

```
formal/
  README.md                 -- 1-page orientation, points here and to PROOF_STATUS.md
  SEMANTICS.md              -- Phase 0 output (THE human-readable spec)
  CORRESPONDENCE.md         -- Lean ↔ Python mapping (C0)
  PROOF_STATUS.md           -- living status/ledger/adjudications (§8.3)
  lean/
    lean-toolchain, lakefile.toml, lake-manifest.json
    ZanzibarProofs/
      Core/    Ident.lean Refs.lean Tuple.lean Store.lean Schema.lean
      Spec/    Stratify.lean Semantics.lean  (relational)  Exec.lean (executable)  WellDef.lean (T0)
      SetEngine/  MemberSet.lean Algebra.lean Eval.lean Correct.lean (T1)
      GraphIndex/ State.lean Invariant.lean Ops.lean Closure.lean (T4) Cascade.lean (T5) Read.lean Correct.lean (T2)
      Equiv.lean  (T3, T6)
      Cli.lean    (JSON conformance endpoint)
  conformance/
    encode.py               -- schema/ops/query ↔ JSON for the CLI
    extractor.py            -- Python graph-state dump for C2
    small_scope.py          -- C3 enumerators
    test_conformance_spec.py test_conformance_state.py
docs/formal-verification-plan.md   -- this file
```

---

## 9. Phases

Each phase ends with: PROOF_STATUS.md updated, acceptance criteria met, user
checkpoint if listed in §8.1.

**Phase 0 — Semantics extraction (no Lean).**
Read: `docs/architecture/overview.md`, `docs/specs/set-engine-spec.md`,
`docs/specs/wildcard-materialization-spec.md`,
`docs/specs/graph-boolean-ivm-spec.md`, `docs/spec-deviations.md`,
`zanzibar_utils_v1.py` (parser + compile + stratify), `tests/oracle.py`,
`setengine/memberset.py`, `index_v4/core.py:_add_direct_edge_unsafe`,
`index_v4/processor.py:reconcile_subject/run_cascade`,
`index_v4/wildcard.py:_check_derived`. Write **SEMANTICS.md**: the domain,
the AST, well-formedness rules (with file:line), the fixpoint semantics in
math, wildcard/star-query semantics, TTU stored-parent rule, the MemberSet
invariant + op recipes, the graph state + I-series invariants + op algorithms
+ read path, the exact hypotheses each theorem will carry, and a list of every
ambiguity found with proposed resolution. *Acceptance:* every claim carries a
code citation; ambiguity list explicitly resolved or escalated. **CHECKPOINT.**

**Phase 1 — Lean skeleton + spec + theorem statements.**
Set up `formal/lean` (ask before installing toolchain). Implement Core/ +
Spec/ (both semantics), `stratify`, and ALL of T0–T6 as `sorry`-bodied
statements that compile. Prove T0a/T0b (these are foundational and comparatively
mechanical). *Acceptance:* `lake build` green; T0 proved; statement review
package written (each theorem restated in English next to its Lean).
**CHECKPOINT.**

**Phase 2 — Conformance bridge v1 (BEFORE deep proofs).**
Build Cli.lean over the executable spec only; build encode.py + the pytest
harness; run C1 on the matrix + scenario corpora and a first hypothesis batch;
stand up C3 at modest bounds. Rationale for doing this now: it validates the
spec is the *right* spec while it is still cheap to change — proving theorems
about a wrong spec is the project's biggest risk. Expect adjudication events
here; handle per §8.2. *Acceptance:* six-way agreement (spec + oracle + 2
backends, on answers AND rejection outcomes) on all corpora, or adjudications
resolved by the user.

**Phase 3 — Set-engine model + T1.**
MemberSet algebra + lemmas, Eval, T1 by strata/AST induction. Wire the model
into the CLI; extend C1 to compare the model (not just the spec) against
`setengine/`. *Acceptance:* T1 `sorry`-free + axiom-audit clean; conformance
green.

**Phase 4 — Graph-index model + T2/T4/T5.**
State, Inv, ops, closure lemma (T4: pair-count expansion first, diamonds, then
multigraph multiplicity, `remove_node` LAST), cascade (T5), read path (T2b),
assemble T2a. Wire into CLI; implement extractor.py; run C2 state conformance
over matrix + small-scope op sequences. *Acceptance:* T2/T4/T5 `sorry`-free +
audit clean; C1 + C2 green. This is the longest phase — expect it to be ~half
the total effort; split PROOF_STATUS work items accordingly.

**Phase 5 — Equivalence + security corollaries.**
T3, T6a–c. Write `formal/README.md` final claim section using §7's wording
verbatim. *Acceptance:* zero `sorry` project-wide; axiom audit clean on
everything.

**Phase 6 — Hardening + CI + handoff.**
C3 at final bounds (document them); CI wiring (proof build + conformance suite);
drift protocol documented in CORRESPONDENCE.md header; final report to user:
theorems proved (English), adjudications/bugs found, residual risk per §7.

**Phase 7 (OPTIONAL, separate go/no-go) — Concurrency & crash protocol in TLA+.**
Model `advance_index` watermark exactly-once under crash/retry, `catch_up`
racing appliers, freshness-token gating (`StaleRead`), sync-mode
cascade-in-same-transaction; check refinement to an atomic-apply spec with TLC.
Out of the core scope; do not start without explicit user go.

---

## 10. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Spec drafted wrong → theorems about the wrong thing | med | Phase 0 checkpoint; Phase 2 conformance BEFORE deep proofs; adjudication protocol |
| T4/T5 proofs too hard, effort spirals | med-high | staged lemma order (§9 P4), 2-hour stuck rule, sorry ledger, statements reviewed early so partial credit is real |
| Vacuous theorems (empty hypothesis intersection) | low-med | statement review checkpoint explicitly hunts this; C3 exercises the hypothesis set non-vacuously |
| Lean/Windows toolchain friction | low-med | pin toolchain; WSL fallback (ask user) |
| Model quietly diverges from code ("nicer" model temptation) | med | C0 correspondence table + C2 state conformance catches it mechanically |
| Conformance suite too slow for CI | low | bounds tuning; slow-marked tier; keep a fast smoke subset |
| mathlib version churn | low | pin manifest; core+std preferred where possible |

---

## 11. Glossary (for fresh sessions)

- **Spec / `sem`**: the stratified-Datalog least-fixpoint denotation of
  `(schema, store, query)` — THE definition of correct.
- **T-theorems**: §1 table. T3 is the equivalence deliverable; T4 is the
  counting-IVM-under-acyclicity crux; T6 are the security corollaries.
- **C-links (C0–C4)**: §6 — the empirical bridge from Python to the Lean models.
- **Adjudication event**: any disagreement between spec/oracle/backends — stop
  and ask the user (§8.2).
- **Small-scope hypothesis**: the empirical observation that this system's bug
  classes (refcount diamonds, exclusion leaks, bridge teardown) all manifest at
  ≤ ~5 nodes — the justification for exhaustive C3 bounds.
