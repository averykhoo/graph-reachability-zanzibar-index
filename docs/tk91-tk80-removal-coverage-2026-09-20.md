# TK91 + TK80 — the removal axis: a bulk arm that never sees a remove, and a node delete with no residue guard

**ACTIVE-PLAN** (`docs/README.md` §3). Opened 2026-09-20f. Corrections append **dated at
the top**. FREEZE when both `TK91` and `TK80` close.

**2026-10-06 (`TK120`):** the code moved into the `src/zanzibar/` package and lost its version suffixes after this doc was written; its paths and class names are the OLD ones. Key: `docs/architecture/overview.md` § "Renamed in TK120".

Provenance labels are per claim: **READ** (verified first-hand against the live tree by
the session that wrote the line), **RAN** (the session executed it and quotes the literal
output), **REASONED**, **UNVERIFIED** (reported by a subagent and *not* re-checked here).
A subagent report is evidence, not a finding.

These two items are one theme at two altitudes: **removals are where this tree's coverage
thins.** `TK91` is the differential that never sees a remove; `TK80` is the remove path's
own node delete with no residue-reference guard. They were taken together because they
share a workload, not because either depends on the other.

---

## 1. Why this doc exists

Both rows arrived already MEASURED, and both measurements turned out to be *pointing at
the wrong place*. This section is the headline; the rest is the map.

* **`TK91`'s stated blocker was refuted before this session** (row entry 2026-09-20e) —
  the machinery it asks whether to build already exists. This session found a second
  layer: **the bulk arm it proposes also already exists** as
  `formal/conformance/backends.py::bulk_build_drive`, and wiring it up **passes on the
  first try**. An arm that passes on arrival pins nothing until a sabotage says otherwise.
  §4 is the adjudication.
* **`TK80`'s fix target and its evidence do not agree.** The row's brief says `:884` is
  the unguarded branch — true — but the row's own census puts **all `10`** of the measured
  live-residue-reference deletions at `core.py:893`, a *different* branch with an
  implicit-only guard. A guard on `:884` alone covers **none** of the observed hits. §5 is
  the adjudication.

Neither of these is a criticism of the rows. Both are exactly what the rows told the next
session to go and check.

## 2. Status

**Both items LANDED 2026-09-20f.** Everything below is green on its own modules; the
ten-phase gate verdict is on the task rows and in the session log, not here.

| item | state as of 2026-09-20f |
|---|---|
| `TK91` bulk arm | **LANDED** — `test_conformance_remove.py::test_graph_remove_bulk_build_survivors`, `26` params × `5` seeds, five legs. INERT against the row's own mutation *by construction* (§4.1), which is why the arm alone does not close the row |
| `TK91` `[rel]` repair pin | **LANDED** — `tests/test_reg_tk91_live_keys_repair.py` (`5` tests). This is the half that closes the row: the mutation that was INERT across four modules now turns it `4 failed, 1 passed` (§4.2) |
| `TK80` fix layer | **DECIDED + LANDED** — façade refusal in `index_v4/wildcard.py` only; `core.py` untouched (§5) |
| `TK80` permanent test | **LANDED** — `tests/test_reg_tk80_remove_node_residue.py` (`11` tests), incl. the non-vacuity control and both sweep-gap closures |
| `TK80` reproducing arm | **RE-OBSERVED** — was not recoverable by copy (§5.2); re-constructed from its invariants and the I6 violation re-observed on the pre-fix tree |
| sweeps | `3` run. `tk91-repair-pin` **PINNED**; the other two **GAPS_FOUND**, both gaps then closed (§7) |

⚠ **The single most important line in this doc for a future reader:** the bulk arm
(`TK91`'s stated deliverable) is *blind by construction* to the mutation `TK91` was opened
for, and the thing that actually closes the row is a small `tests/` module the row never
mentioned. Do not read the conformance arm as the item's pin. §4.2 is why.

## 3. The anchor map

Line numbers are as READ on **2026-09-20**; they rot fast, so cite the symbol and re-grep
the line.

### 3.1 TK91 — the conformance remove module

All **UNVERIFIED** (subagent `scout:remove-conformance`) unless re-checked below.

| `file::symbol` | line | what it is |
|---|---|---|
| `formal/conformance/test_conformance_remove.py::test_graph_remove_sequences` | `405` | the test the new arm mirrors; parametrizes `sorted(SCHEMAS)` |
| `::_graph_state` | `393` | the id-free fingerprint: `snapshot_rows(...)` + `::_residues_by_name` |
| `::_residues_by_name` | `375` | `{(type, name, relation): (stars, frozenset neg)}`, id-free by construction |
| `::_sequence` | `109` | generates `[('add'\|'remove', tup), ...]` with forced net removal |
| `::_extras` | `78` | recombines extra tuples from the corpus's own tuple space |
| `::SEEDS` | `60` | `list(range(5))` |
| `::_MIN_SEQ_COMPARISONS` | `69` | anti-vacuity floor, asserted at `:474` |
| `formal/conformance/backends.py::bulk_build_drive` | `95` | **the reuse point** — returns `(session, widx, "conf")` |
| `::graphindex_drive_ops` | `283` | returns `(session, widx, proc, store_id, accepted_final)` |
| `formal/conformance/grid.py::queries_for` | `109` | grid over the FULL universe |
| `::assert_grid_nonvacuous` | `148` | per-store grid floor |
| `index_v4/invariants.py::snapshot_rows` | `681` | node/edge row multisets, **ids erased** |
| `connectedstore/build.py::build_index` | `31` | `bulk=True` branch |

Two facts that shape the arm, both **UNVERIFIED**:

* The driven arm's store id is `"conf"` (`backends.py::GraphDriver.__init__`) and
  `bulk_build_drive` uses `"conf"` too — so `_graph_state` compares **directly, with no
  translation**. This is why the arm is cheap.
* `snapshot_rows` captures `direct_edge_count` and `indirect_edge_count` but **not the
  `EdgeV4.derived` flag**. If the arm comes back inert, this is the first thing to suspect.

### 3.2 TK80 — the delete branches and the guards that exist elsewhere

All **UNVERIFIED** (subagent `scout:core-delete`) unless re-checked below.

`index_v4/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl` (def `:714`) has three
node-delete branches:

| branch | lines | guard |
|---|---|---|
| A | `875-877` | implicit-only |
| B | `881-884` | **none** — no implicit check, no residue check |
| C | `892-894` | implicit-only (`reference_count + count == 0 and _node.implicit`) |

The two-clause residue check exists only as `index_v4/processor.py::DeltaProcessor._residue_row`
(`:320`) and `::_residue_references` (`:623`), used together at `::_gc_subject_node` (`:1099`)
and `::_gc_public_node` (`:1321-1323`).

⚠ **They cannot be imported into `core.py`** — `core` → `processor` → `wildcard` → `core`
is a real cycle (`processor.py:36`, `wildcard.py:23`). A core-side fix means
re-implementing two selects inline against `ResidueV1`/`ResidueRefV1`, which live in
`index_v4/models.py` — a module `core.py` already imports from (`:15`) and which is
import-leaf.

⚠ **Do not reach for `processor.py::_any_residue_reference`** (`:1145-1150`) — it says
explicitly that it is the DEMOTION guard and has different extension.

The façade precedent: `index_v4/wildcard.py::WildcardIndex.remove_node` already refuses
`T:*` at `:667-672`, raising `AdmissionRejected` (a `ValueError` subclass).
`core.py:22-25` states the rejection-vs-violation rule that governs the choice.
`InvariantViolation` is an `AssertionError` subclass and asserts proven corruption — the
wrong class for an admission decision.

## 4. TK91 — the adjudication

**VERDICT 2026-09-20f: the bulk arm is INERT against the mutation the row was opened for,
and the real pin is somewhere else.** Measured first-hand (**RAN**, subagent
`probe:tk91-inert`, notes `.scratch/tk91-tk80/tk91-probe.md`, ten run logs beside it). The
row's deliverable therefore splits in two, and both halves are needed to close it honestly.

### 4.1 The arm passes on arrival, and is blind to the mutation

Baseline, `26` corpora × `5` seeds:

```
TOTAL state comparisons = 130, state MISMATCHES = 0
TOTAL grid comparisons  = 44245, grid MISMATCHES  = 0
ERRORS = 0
PROBE VERDICT: GREEN
```

With `index_v4/processor.py::_live_keys_of`'s leading `rel` deleted — **byte-identical
result**, `130`/`44245`/`0`/`0`, `PROBE VERDICT: GREEN`.

Two independent measured reasons, not one:

1. **The bulk arm never executes the mutated function.** `index_v4/bulk_backfill.py:808`
   carries its OWN `_live_keys_of` mirror, and bulk `build_index` does not call
   `DeltaProcessor.backfill()`. Instrumented call counts: `processor._live_keys_of` called
   `0` times on the bulk arm for **every one** of the `26` corpora; all `170` calls come
   from the driven arm's `audit_fixpoint()`.
2. **On a CONSISTENT store the mutation is a semantic no-op.** Clean vs mutated keyset
   dumps are byte-identical — same sha256 prefix `f6a6c4b959aaad2b`, same `536` enumerated
   names, `diff` exits `0`. Nothing *could* see it.

Stronger arms do not rescue it: adding the per-edge `EdgeV4.derived` flag, and building a
`DeltaProcessor` on the bulk index to run I9 `audit_fixpoint` (`85` of `130` runs are
boolean and do run it), both stay green under the mutation. Mutating the bulk *mirror's*
identical line is also inert.

⚠ **INSTRUMENT CONTROL — the arm is blind to this mutation, not vacuous in general.** A
different narrow bulk-side sabotage (dropping the `derived-computed` recursion in the bulk
mirror) reddens the arm loudly:

```
state comparisons=130  A-mismatch=26  B(+derived)-mismatch=12
grid comparisons=44245  grid mismatch=107
bulk-side audit_fixpoint runs=59  violations=26
VERDICT: RED
```

That control is the evidence the arm earns its place. Without it, "green under the
mutation" would have been indistinguishable from a broken harness.

### 4.2 What the `[rel]` term actually guards — and it is a fail-open

**This is the more important half of the item.** The leading `rel` is a **repair
affordance**, reachable only on an INCONSISTENT store — which is exactly why deleting it
was INERT across four whole modules. On a store where derived state OUTLIVES its leaf (a
leaf REMOVE routed onto the leaf families with the cascade skipped), observed:

```
CLEAN                                        MUTATED
  live_keys_of(doc, viewer) = ['d1']           live_keys_of(doc, viewer) = []
  after backfill(): check = False              after backfill(): check = True   <-- FAIL-OPEN
  backfill CHANGED state = True                backfill repairs nothing
  audit_fixpoint() = OK                        audit_fixpoint() = OK            <-- I9 IS BLIND
```

⚠ **Note the second column's last line.** `audit_fixpoint()` still reports OK under the
mutation, because **I9 enumerates through the same crippled function**. The invariant
checker cannot see this. That is an assurance step that fails by PASSING — the house
failure mode — and it is why the pin must not be routed through `audit_fixpoint`, but
asserted on `check` and the repaired state directly, off the primitive the mutation
touches (the 2026-09-13e lesson).

Because `graphindex_drive_ops` always cascades in the same transaction, **no reachable
variant of a bulk arm in the conformance remove module can construct that state.** The pin
belongs in `tests/` as a corrupt-then-repair unit test. `.scratch/tk91-tk80/probe_stale.py`
is the ~`50`-line promotable reproduction.

### 4.3 Anti-vacuity, from measured numbers

Set any floor from these, not from invention. Exactly `1` of the `130` (corpus, seed) cells
compares two empty indexes — `wildcard_public` seed 4 (`0` survivors, `0` state rows);
`7` of `130` have ≤1 survivor or ≤3 state rows. Sweep totals: `740` survivors, `3757` state
rows, `72` residues, `157` derived edges. Per-corpus minimum over `5` seeds is
`wildcard_public` at `12` state rows. Only `12` of `26` corpora carry any derived edge.

⚠ **Anti-vacuity is a live risk on this arm and the existing floor does not cover it.**
`_graph_state` on two *empty* indexes compares equal, and `bulk_build.py` returns early on
an empty node set. `_MIN_SEQ_COMPARISONS` counts **grid queries, not state rows**, so a
survivor set that happens to be empty passes having compared nothing. Any new arm needs
its own floor, set from measured per-corpus survivor counts.

⚠ **One admission-surface risk, UNVERIFIED** (subagent `scout:bulk-api`):
`bulk_build_drive` validates through `TupleSource` (set-engine admission), while
`graphindex_drive_ops` validates through the graph index. Survivor sets come from
`::_extras` recombinations whose rejections are poison-handled on the *graph* side only. If
the two admission surfaces ever disagree, a survivor lands as zero `TupleV1` rows and
`bulk_build_drive` raises its landed-count assertion rather than reporting a state
mismatch. If that fires, `CLAUDE.md` § "Who decides" applies: **the Python is wrong**, not
the arm.

## 5. TK80 — the adjudication

**DECISION 2026-09-20f: FAÇADE REFUSAL.** The fix goes in `index_v4/wildcard.py` only;
`index_v4/core.py` is untouched, so every `formal/CORRESPONDENCE.md` anchor still resolves
and no modelled algorithm changes. Decided by a design panel against the repo's primary
consideration per `CLAUDE.md` § "Who decides" (notes `.scratch/tk91-tk80/decision.md`);
the reasoning is recorded here because the row is the index and this doc is the body.

**HAZARD RE-OBSERVED 2026-09-20f on the pre-fix tree** (**RAN**, subagent
`witness:tk80-repro`, script `.scratch/tk91-tk80/tk80_repro.py`), first attempt, no
iteration:

```
PARANOIA GUARD INSTALLED = None  (must be None for tier off)
VICTIM node id=8 -> type='user' name='alice' predicate='...' implicit=True reference_count=2
--- calling WildcardIndex.remove_node (NO cascade) ---
remove_node returned without raising
  _evict_node call from core.py:883 in _add_direct_edge_unsafe_impl -> branch B (:881-884 NO guard)  node id=8 user:alice#...
--- COMMIT (no run_cascade in this transaction) ---
check_residue_hygiene (tier `residue`): InvariantViolation: I6: residue neg holds a dead node id 8 on node id=3 doc:x#viewer implicit=False
RESULT: I6 VIOLATION ON COMMITTED STATE
```

### 5.0 Three witness findings that correct or extend the row

1. ⚠ **The branch that COMMITS is B (`core.py:883`), not C** — instrumented, both runs.
   This is not a contradiction of the row's census: the census counted branch-C hits under
   *ordinary add/remove_edge traffic*, which produced `0` corruptions. Branch B is
   reachable only from `ReachabilityIndex.remove_node`'s self-loop (`core.py:1204`), which
   is exactly the shipped path the row names as committing. Line map re-read
   **2026-09-20**: `876`=A, `883`=B, `893`=C, unmoved.
2. ⚠ **The hazard is `neg | upos`, not just `neg`.** A second victim (id `6`, a `upos`
   subject, `group:g2#member`) commits a second I6 clause — and it is `implicit=False` with
   `reference_count=3`, deleted anyway, because **branch B has neither an implicit check
   nor a refcount check**. So the guard must key on residue *reference*, which is what
   `ResidueRefV1` indexes.
3. **The guard is ONE indexed select, not two.** `_residue_references`'s answer is
   reproduced exactly by one indexed seek on `ResidueRefV1 (store_id, subject_node_id)`
   plus a liveness filter on the object node (agreement confirmed on `5` probed nodes).
   Note this concerns reproducing *that helper*; a clause guarding a node that **owns** a
   residue row is a different question, settled at implementation.

Four controls, all as the row predicts: `C1` paranoia `'residue'` and `C2` paranoia
`'full'` both REFUSE pre-commit, so only the production default lets it land; `C4`
`run_cascade` in the same transaction repairs it, confirming transience.

⚠ **`C3` IS LOAD-BEARING FOR THE FIX:** the same unguarded branch B deletes an
*unreferenced* node (`group:g3#member`) and commits **CLEAN**. So the guard must be a
**conditional** refusal — a blanket change would break ordinary `remove_node` traffic, and
the test suite must prove it did not.

### 5.0.1 Why not the core guard

Recorded so it is not re-derived. `WildcardIndex.remove_node` calls `_strip_bridges`
*before* `self.idx.remove_node`, and handles "stripping a bridge may already have
implicit-GC'd the node" with an early `return` and no cascade — so a guard below the
façade can be reached too late, while the façade sits above both branches. Beyond that, a
`return` guard at branch C would keep an implicit rc-0 node alive that a bulk build never
creates — **manufacturing exactly the live-vs-bulk divergence `TK91` exists to detect** —
and would disable the downstream repair that keys on the node being gone. A `raise` at C
would turn routine `remove_tuple` traffic into write failures. All of that buys zero
equivalence: the `10` observed hits gave `0` corruptions.

### 5.1 The question, as it stood before the decision

Where does the fix go? The row offers both and this session owes a decision, not a menu
(`CLAUDE.md` § "Who decides"):

* **(a) core-branch-guard** — re-implement the two-clause check inline in `core.py`. Then:
  which branches, and on trip does it `return` (skip the delete, leak a node) or raise?
  The processor precedent at `::_gc_subject_node` is to `return`.
* **(b) façade-refusal** — `WildcardIndex.remove_node` refuses a residue-referenced node,
  mirroring the `T:*` refusal, raising `AdmissionRejected`.
* **(c) both.**

The weighing that matters, since **equivalence is the primary consideration**: branch C
carries ordinary add/remove traffic, where the dangling state is currently
transient-and-repaired. A guard there changes node-lifecycle behaviour on `10`-in-`5132`
of that traffic. Skipping those deletes is not free — a leaked node or a refcount drift is
itself a divergence from the set engine, which has no nodes at all. The corruption
*commits* only via `remove_node` with no cascade at the production paranoia default.

⚠ **Lean impact is not optional to check.** `formal/CORRESPONDENCE.md:1121-1123` anchors
`::DeltaProcessor._residue_references`, `core.py::ReachabilityIndex.remove_node` and
`::_evict_node`. A guard that can skip a delete changes a modelled algorithm — so either
the Lean model is updated or the gap is logged in `CORRESPONDENCE.md` §7, and
`verify.sh lean` is re-run (`CLAUDE.md` § "Perf work & the Lean model").

### 5.2 ⚠ The reproducing arm is not recoverable by copy

**UNVERIFIED** (subagent `scout:test-conventions`), and it is the finding that most
changes the shape of the work.

`docs/tk74-staleness-net-2026-09-18.md` §10.1/§10.8 (FROZEN) record the *result* — `48`
runs, `4` live-ref deletes, `2` committed corruptions — and the I6 error string, but carry
**no schema, no tuple list and no call sequence**. The `.scratch/tk74d-starisect/star_isect.fga`
fixture those arms used is **gone**. This is the `.scratch/` rule collecting its debt a
second time on the same axis (`CLAUDE.md` § record-keeping).

So the arm must be re-constructed from its invariants:

* a boolean/wildcard schema that actually writes a residue (non-empty `neg`, and/or `stars`)
* a node whose id is recorded in that residue's `neg`, so `ResidueRefV1` references it
* `WildcardIndex.remove_node` on that node
* paranoia **off** — and the test must **assert its own installed tier is `'off'`** rather
  than trust the argument. Every non-off tier refuses the bad state pre-commit, so a test
  written at the default would be green for the wrong reason. The historical bug where the
  tier was dropped and every value installed `'full'` is pinned by
  `tests/test_paranoia_wiring.py::test_helper_forwards_the_tier`.
* **no** `run_cascade` in the same transaction

⚠ **No in-tree test drives `WildcardIndex.remove_node` on a residue-bearing schema at
all** (**UNVERIFIED**). `tests/test_hypothesis.py:1158` does `remove_node` with no cascade
but on a non-boolean schema; `tests/test_reg14_residue_gc_elision.py:222-224` produces the
dangling state but *bypasses* `remove_node` via `_evict_node` + `session.delete`. The
closest fixture seed is `tests/test_residue_ref_index.py:90`'s `SCHEMA`, reportedly the
only in-tree schema that populates `stars`/`neg`/`upos`.

**The hazard must be RE-OBSERVED committing on the pre-fix tree before the guard lands.**
Otherwise the permanent test pins something nobody in this session ever saw fail.

### 5.3 Test home

Depends on §5.1's outcome: guard-in-core → a new `TK`-named module (precedent
`tests/test_reg_tk69_entity_crossing.py`); façade-refusal →
`tests/test_wildcard_remove_node.py` plus a mirror pin beside
`tests/test_admission_rejected.py:201-215`. `tests/test_reg14_residue_gc_elision.py` is
the **wrong** home — its harness always runs the cascade and hardcodes `store_id='reg14'`.

## 6. What this session must not do

* ⚠ **Do not land either arm green-on-arrival.** `docs/sabotage-procedure.md` governs
  both: break the narrowest *plausible* weakening, control the instrument as well as the
  subject, and sweep the whole module with mutations — a single sabotage certifies one
  test. Include an **`M0` control** that flips one pin's own claim and demands the
  attribution name it; a sweep without one cannot tell a clean module from a broken
  harness.
* ⚠ **Do not fold `TK91` into `TK78`.** That row's item is the ENUMERATOR
  (`::_live_keys_of` vs `::_fan_out`, asserted nowhere); this is a separate gap that would
  otherwise ride along unranked.
* ⚠ **Do not widen `TK80`'s claim.** The board's "live correctness bugs: `0`" is not
  disturbed by this work. The severity paragraph stands: transient and repaired
  in-transaction on every shipped path. This is hardening plus the permanent positive test
  the procedure requires.


## 7. APPENDED 2026-09-20 — closing M14: the bulk arm now pins WHICH constructor ran

Provenance: first-hand READ + first-hand MEASURED by the TK91 bulk-arm gap-closer
agent; every run below was a byte edit of the shipped file, restored and
`cmp`-verified. Working notes: `.scratch/tk91-tk80/gap-bulkarm.md`.

### 7.1 The gap

Sweep row **M14** (`.scratch/tk91-tk80/sweep-tk91-bulkarm.md`): in
`connectedstore/build.py`, `if bulk:` -> `if False:` left
`test_conformance_remove.py::test_graph_remove_bulk_build_survivors` at
`26 passed, 104 deselected` rc=0, while an instrumented counter over the same 130
cells showed `index_v4.bulk_build.bulk_build` called **0 times instead of 130**.
The two constructors produce byte-identical state on all 130 cells — that IS the
P13 correctness bar — so no state assertion anywhere can see the difference, and
the arm's entire stated subject (the OFFLINE BULK bootstrap) could be swapped for
the constructor it was written to differ from without a single test reddening.

### 7.2 The fix — an observable fact, not a monkeypatch

* `connectedstore/build.py::BuildReport` — `build_index` now returns a plain
  3-element `tuple` subclass (every `cursor, widx, ruleset = build_index(...)`
  call site is unchanged; all of them were checked) carrying `.constructor` in
  `{'bulk', 'incremental'}`. The label is assigned INSIDE each branch, AFTER that
  branch's constructor returns, with **no default initialiser**: deleting an
  assignment is an `UnboundLocalError`, not a wrong label. `BuildReport.__new__`
  raises `ValueError` on any other label.
* `formal/conformance/backends.py::bulk_build_drive` — MECHANICAL REFUSAL
  (`docs/sabotage-procedure.md` prefers one over a doc warning): raises unless the
  report says `'bulk'`. Placed at the seam rather than in one caller, so
  `test_conformance_bulk_state.py` and `extractor.py` inherit it.
* `test_conformance_remove.py::_incremental_constructor_label` — the CONTROL that
  keeps that refusal from being an assertion that cannot fail. Once per corpus it
  rebuilds the last seed's same survivors with `bulk=False` and requires the OTHER
  label. Leg (e) of the arm's docstring.

### 7.3 Evidence (literal)

Subset `object_wildcard or residue_rich or wildcard_public` — the bridge corpus,
the residue-carrying boolean corpus, and the one whose last seed leaves ZERO
survivors, so the control is exercised on an empty snapshot too.

| run | tail | rc |
|---|---|---|
| clean | `3 passed, 127 deselected in 11.48s` | 0 |
| M14 (`if bulk:` -> `if False:`) | `3 failed, 127 deselected in 1.49s` | 1 |
| M-CTL (label made constant: else-branch `'incremental'` -> `'bulk'`) | `3 failed, 127 deselected in 11.87s` | 1 |
| whole arm, clean, leg (e) in place | `26 passed, 104 deselected in 169.65s (0:02:49)` | 0 |

M14's message:

```
AssertionError: bulk_build_drive: build_index ran its 'incremental' constructor,
not 'bulk' -- index_v4/bulk_build.py never executed. ...
```

M-CTL's message:

```
AssertionError: [object_wildcard] CONTROL: build_index(bulk=False) reported
constructor 'bulk', so `BuildReport.constructor` does not discriminate the two
branches and leg (e) -- bulk_build_drive's refusal -- is an assertion that
cannot fail.
```

Regression check on the other `build_index` callers: `tests/test_bulk_build.py` +
`tests/test_connectedstore_build.py` `13 passed in 6.07s` rc=0;
`formal/conformance/test_conformance_bulk_state.py` `26 passed in 6.96s` rc=0;
`formal/conformance/anchor_check.py` `696 parsed ... 696 resolved` rc=0.

### 7.4 Measured and DELIBERATELY NOT PINNED (2026-09-20)

Recorded rather than chased; each is a real measurement, each would be a contortion
to pin from this arm.

* **M15** — `backends.bulk_build_drive`'s `landed != len(tuples)` refusal cannot
  fire on this input class: all 130 cells satisfy `landed == len(tuples)`, so
  neutering it to `if False:` is GREEN. It guards a future divergence (an
  accept/reject disagreement between the set-engine and graph-index admission
  surfaces), not a live property.
* **Six dead paths in the bulk constructor**, each proven dead by an instrumented
  counter over all 130 cells — MEASURED, not inferred: the hit counters were never
  taken. Weakening any of them leaves the arm green because nothing reaches them.
  1. subject-side bridging in `index_v4/bulk_build.py` Phase B;
  2. the `_ensure_bridges` call in `index_v4/bulk_backfill.py::_write_derived_add`;
  3. Phase P's multiplicity weight (`mult` is never != 1 on these inputs);
  4. `ResidueV1.version` is never != 1 on a fresh bulk build;
  5. `bulk_backfill.py::_store_residue`'s re-store branch is never entered;
  6. the step-4 neg-maintenance branch in `_reconcile_subject_edge` is never taken.

  (1)+(2) are sweep rows M2/M11, (3) is M3, (4) is M7, (5) is M9, (6) is M12.

## 8. APPENDED 2026-09-20 — the three mutation sweeps, and what is still unpinned

Three sweeps ran, one per landed module, each with an `M0` control that flipped a pin's own
claim and demanded the attribution name it. **All three `M0` controls attributed correctly**,
so all three tables are readable rather than being reports from a broken harness.

| sweep | verdict | gaps | outcome |
|---|---|---|---|
| `tk91-repair-pin` | **PINNED** | — | `M1` (the `[rel]` deletion) turns it `4 failed, 1 passed` |
| `tk80-facade` | GAPS_FOUND | `M2`, `M10` | both **closed** — §8.1 |
| `tk91-bulk-arm` | GAPS_FOUND | `M14` | **closed** — §7 |

The implementing agent for `TK80` also hit a **green sabotage** before any sweep ran: moving
the refusal below `_strip_bridges` left the module at `8 passed`, because `_strip_bridges`
writes nothing for any node of the original fixture. It added a bridged fixture and
`::test_the_refusal_runs_before_the_bridge_strip` in response. That is the third time this
session that a check looked sound until something was deliberately broken underneath it.

### 8.1 The two TK80 gaps, both proven-to-move before being called gaps

Neither was hypothetical — each was a GREEN mutation with probe evidence that it changed the
guard's answer:

* **`M2`, the liveness filter.** Dropping `if s.get(NodeV4, r.object_node_id) is not None`
  stayed green. On a dangling `ResidueRefV1` row the guard answered `True` while
  `DeltaProcessor._keys_referencing` answered `False` — so the agreement that
  `::test_the_guard_agrees_with_the_processor_on_every_node` *claimed* to pin was not pinned
  at the one place the two can differ. Closed by
  `::test_a_dangling_residue_ref_does_not_count_as_a_recording`, which also catches a
  narrower variant the sweep never tried (probe the subject node instead of the object node).
* **`M10`, store scoping.** Deleting both `.where(... .store_id == sid)` clauses stayed
  green. Closed by `::test_the_guard_is_scoped_to_its_own_store`, which needed a **co-tenant**
  fixture — two stores on one session/engine sharing one `NodeV4` table and one global id
  sequence, which `make_wildcard_index` cannot express (it builds its own engine per call,
  and two isolated databases would have proved nothing). Each clause is pinned separately.

### 8.2 ⚠ Still unpinned, deliberately — read before trusting a green here

* **`index_v4/bulk_backfill.py:811` carries an unpinned duplicate of the `[rel]` line just
  pinned in `processor.py`.** Measured: deleting it leaves all four relevant modules at
  `29 passed`. Scope was deliberately not widened. The recorded hypothesis — that
  `build_index` "refuses to run on an index that already has state", so the bulk path only
  ever backfills a state it built itself and its `[rel]` term may be unreachable by
  construction — is **REASONED, nobody has proved it**. A live trap for the next session.
* **`processor.py::_reconcile`'s trailing `if residue_changed or edges_changed:
  self._gc_public_node(...)`** is green when deleted, on the new module *and* on
  `test_backfill_enumeration` + `test_bulk_build` + `test_invariants_derived`. Measured
  reason: `_reconcile_subject` has already collected the dead public node before that call
  runs.
* **`processor.py::_live_keys_of`** — dropping `spec.positive` from the comprehension is
  green everywhere (widening only: `preds` gains a name, the key set is unchanged;
  fail-closed/perf). Dropping `.where(NodeV4.wildcard == '')` is green everywhere because
  zero wildcard node rows exist in any fixture reached — distinguishing it needs a
  `*`-object-node store.
* **The `TK80` guard reads the derived `ResidueRefV1` index, not the `ResidueV1.neg`/`upos`
  JSON.** Adjudicated a **defensible boundary**, not a gap: `DeltaProcessor._keys_referencing`
  reads the same index under the same liveness rule, so a JSON-reading façade guard would
  become a second, divergent definition of "referenced". An index out of sync with its JSON
  is already an invariant violation owned by `index_v4/invariants.py::_check_residue_rows`
  — verified by running it, not cited from memory:
  `I6: residue_ref index disagrees with neg|upos on node id=3 doc:x#viewer`.
  ⚠ **The honest caveat:** that check only runs when a paranoia tier is INSTALLED. At the
  production default (`off`) nothing compares the index to the JSON at write time. That is an
  argument for `ZANZIBAR_PARANOIA=residue` in production, not for widening the guard.

### 8.3 One behaviour change worth knowing about

`remove_node` followed by `run_cascade` **in one transaction** is now refused. Pre-fix that
sequence self-repaired (control `C4`). No in-tree caller does it, and the sanctioned order is
the reverse — remove the recording tuples, cascade, *then* remove the node — which is what
the refusal message names.
