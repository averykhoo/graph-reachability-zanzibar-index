# TK74 — what actually catches a stale derived key, and how often the settle pass runs

**ACTIVE-PLAN** (`docs/README.md` §3). Opened 2026-09-18. Corrections append **dated at
the top**. FREEZE when `TK74` closes.

Provenance labels are per claim: **READ** (verified first-hand against the live tree by
the session that wrote the line), **MEASURED** (this session ran the probe and read the
literal output), **AGENT-MEASURED** (a subagent ran it; reproduced by at least one
independent skeptic but *not* re-run here), **REASONED**, **UNVERIFIED**. A subagent
report is evidence, not a finding (`CLAUDE.md` § Delegation).

Produced by a 17-agent fan-out (6 reproduction angles, 2 adversarial skeptics each, 1
completeness critic) run 2026-09-17/18 at HEAD `6c5b97c`, plus this session's own
first-hand re-measurement of the two load-bearing numbers.

---

## 1. Verdict

**`TK74`'s premise reproduces exactly — and it is an assurance-coverage gap, not a live
correctness bug.**

Skipping one productive reconcile inside a cascade round yields wrong answers against the
oracle with **no raise** from the shipped settle pass, no raise from the rejected
`rounds+1` candidate, and no raise at **any** `ZANZIBAR_PARANOIA` tier. But every wrong
answer in every arm required a deliberate fault injection; the unmutated control arms are
`divergences=0`. **The board's "Known live correctness bugs: 0" line stays at 0.**

Two agents set `is_wrong_answer_bug: true`; all four skeptics said it must be false, and
they are right — the reproduction is fault-injected. Recorded here because that flag would
have mis-routed the row. (**READ** — the framing was reconciled, not averaged.)

## 2. The mechanism, first-hand

**READ**, `index_v4/processor.py:1628-1636`. After the round loop:

```python
rows = outbox_rows(self.session, self.store_id, frontier_start)
leftover = self._map_deltas_to_keys(rows)
for (b_type, b_rel, b_name) in self._bumped:
    self._fan_out(...)
self._bumped = []
self._settle = None
if not leftover:
    return
```

`leftover` has exactly two sources: outbox rows above the frontier, and `self._bumped`
(sole append at `index_v4/processor.py:1351`, **inside** a reconcile). A reconcile that
never runs writes nothing, therefore emits no outbox row, therefore appends no bump — so
the stale key cannot enter `leftover` by any path, and `if not leftover: return` exits
**above** both the `SettlePass` assert and (in the rejected arm) the pre-`TK73` syntactic
`if leftover: raise`.

Both candidate fixes are gated on the same outbox-derived set. **Staleness that emits
nothing is invisible to both by construction** — for the schemas measured; see §4 for the
bound on that phrase.

This is not a defect in the `TK73` fix. That pass was designed to close a different hole:
work the cascade does not *schedule* (reconcile-time GC emission). It was never aimed at
a scheduled reconcile that did not run.

## 3. The production net, measured

**AGENT-MEASURED** (`tk74-net`, instrument-controlled in both directions: the residue tier
was made to go RED on an I6 dead-node-id corruption and the full tier RED on an I13
refcount corruption in the same harness, so the "no raise" readings come from a detector
demonstrably able to say yes).

| tier | what runs per write | catches a stale derived key? |
|---|---|---|
| `off` (= `connectedstore/store.py::ConnectedStore.DEFAULT_PARANOIA`, `:98`) | `install_paranoia` returns None; **no listeners at all** | no |
| `residue` | `before_commit` then `flush()` + `index_v4/invariants.py::check_residue_hygiene` (`:560`) | no |
| `full` | `check_invariants` + `verify_outbox_deltas` | no |
| (not a tier) | `index_v4/processor.py::DeltaProcessor.audit_fixpoint` (`:1732`) — I9 | **yes, every time** |

**READ**: `audit_fixpoint` has **zero production callers**; every call site is under
`tests/` or `formal/conformance/`. `index_v4/invariants.py::install_paranoia` (`:773`)
does not wire it, and the exclusion is stated at `index_v4/invariants.py:184` ("Not here,
by design: I9 is the processor's fixpoint audit").

**The decisive datum for the row's design question** (**AGENT-MEASURED**): per-op
`audit_fixpoint` — what `tests/test_matrix.py::GraphBackend.post_op` runs — raised at
exactly the op of the first wrong answer in **8 of 8** divergent cases. End-of-run
`audit_fixpoint` was **clean in 4 of 8**, because a later write re-reconciles the key and
launders the corruption. **Staleness here is often TRANSIENT and the wrong answers are
served inside the window.** So "run the audit periodically" is not a design option:
`TK74` narrows to *a per-write check or nothing*.

Counts: 8 of 18 productive skips diverged, across seeds 0/1/2 on
`tests/fga_schemas/boolean_wildcards.fga`. The originating agent reported 9/18 and 4/9;
two skeptics independently measured **8/18** and **4/8**. Use 8 and 4/8.

## 4. ⚠ The bound nobody noticed, and the reason to distrust §2's "by construction"

**MEASURED first-hand this session.** Probe: a pytest plugin wrapping
`index_v4/processor.py::DeltaProcessor._run_cascade`, reading `self._settle` in a
`finally`, bucketed by `len(self.compiled.strata)`.

```
run 1: tests/test_cascade_quiesce_gc.py tests/test_i14_crossing_middles.py
       tests/test_processor.py tests/test_invariants_derived.py     -> 34 passed in 3.63s
  === SETTLE CENSUS: 118 cascades ===
       69  arm=skipped_leftover_empty   strata=1
       28  arm=skipped_leftover_empty   strata=3
       11  arm=skipped_leftover_empty   strata=2
        7  arm=skipped_leftover_empty   strata=5
        3  arm=SETTLE_RAN               strata=1
    SETTLE_RAN total = 3 / 118  (2.54%)
  === tests where the settle pass ACTUALLY RAN ===
      1  tests/test_cascade_quiesce_gc.py::test_witness_commits_and_agrees_with_the_oracle
      1  tests/test_cascade_quiesce_gc.py::test_settle_pass_runs_and_is_a_fixpoint
      1  tests/test_cascade_quiesce_gc.py::test_settle_pass_detects_genuine_staleness

run 2: tests/test_matrix.py tests/test_reads.py tests/test_boolean_compile.py
       tests/test_connectedstore.py tests/test_connectedstore_multi_instance.py
       tests/test_connectedstore_async.py                          -> 104 passed in 85.96s
  === SETTLE CENSUS: 440 cascades ===
      197  arm=skipped_leftover_empty   strata=2
      136  arm=skipped_leftover_empty   strata=5
       82  arm=skipped_leftover_empty   strata=6
       25  arm=skipped_leftover_empty   strata=1
    SETTLE_RAN total = 0 / 440  (0.00%)
```

**558 cascades; the settle pass executed on 3 — 0.54% — all at `strata == 1`, all three
inside the module written to make it run.** 415 of the 440 in run 2 were multi-stratum.
**The settle pass has never been observed to execute on a multi-stratum schema.**

INSTRUMENT CONTROL: run 1 moved **both** arms in a single run, so run 2's `(none)` is a
measured zero from a demonstrably live counter, not a dead probe. The plugin prints an
explicit INERT warning when only one arm moves, and run 2 printed it.

Mechanical reason (**READ**): `index_v4/processor.py::DeltaProcessor._map_deltas_to_keys`
(`:1379`) routes a `DerivedFamily` object row through `::_fan_out` to its **dependents**,
never to its own key — so an ordinary `_write_derived` output row on a terminal derived
relation contributes zero keys, `leftover` is empty, and the pass returns early.

**Why this bounds §2.** Every skip experiment in the fan-out ran where `rounds` was 1 or 2.
The one shape where the settle pass could plausibly catch a skipped reconcile — skip a
LOWER-stratum reconcile, let a higher stratum compute off the stale input and emit rows
that `_fan_out` maps back onto the skipped key — **was never driven**. Until it is,
"blind by construction" is proven only for the single-stratum case.

**THE NEXT PROBE, and it is the highest-value one available**: one skipped-reconcile
experiment on a multi-stratum schema — `tests/fga_schemas/demorgans_law_2.fga` (6 strata)
or `wildcard_userset_cross.fga` (4) — skipping a reconcile in a NON-final stratum.

## 5. `TK75`, settled in passing

* **Item 2 (the unreproduced second `TK73` witness) is CLOSED** (**AGENT-MEASURED**,
  two-sided instrument control, both skeptics confirmed). Recovered from
  `.scratch/tk73adv/sweep.py` (seed `20260917`), replayed with the pre-`TK73` check
  reinstalled by monkeypatch, reproduced on the first run with the exact reported leftover
  `[('folder','owner','z')]`. It is answer (a), the boring one: byte-identical to witness
  1 modulo the entity name. Minimised to three writes — `add folder:* parent folder:z`;
  `add folder:x parent folder:y`; `remove folder:x parent folder:y` — and the
  `editor: [user, user:*]` declaration is **irrelevant** (schema S1, which lacks it, raises
  the same key). The leftover entity is the star parent's object, **except** `E='y'` (the
  removed edge's own object), which is green and **unexplained**. Two negative controls
  (no star write; concrete parent) stay green.
* **Item 1 is HALF closed.** The **strip** arm of
  `index_v4/wildcard.py::WildcardIndex._sync_entity_middles` (`:404`, no-witness branch,
  then `::_strip_bridges` `:421`) **is** a live late-emission site and it already fires
  **in the existing suite** —
  `tests/test_i14_crossing_middles.py::test_middles_retire_with_their_entity` emits 3
  REMOVED rows above the final frontier from inside a reconcile, via
  `index_v4/processor.py::DeltaProcessor._gc_public_node` (`:1307`), delete branch only
  (`:1300-1307`). **`TK75`'s trap "a new fixture is required" is wrong.** The **re-add**
  arm is reached (269 in-cascade-GC calls) but **inert** — 0 emissions; it only re-ensures
  a middle that is already complete, and it could be made to emit only by manufacturing an
  I14 hole first.
* ⚠ **Do not repeat the "third undocumented callsite" claim.** Two agents made it; three
  skeptics independently killed it. `docs/tk73-cascade-quiesce-gc-2026-09-17.md` §7
  (`:189-193`) names `_gc_public_node` verbatim. The contribution is the first WITNESS, not
  the discovery.
* ⚠ **Do not repeat "TK75's coverage claim is measurably false."** One agent asserted it,
  one skeptic refuted it, and the critic settled it against the agent: the settle pass
  **is** call-site-independent; coverage is mediated by `_map_deltas_to_keys`, and
  `leftover == {}` is the global norm (§4), not a fact about `_sync_entity_middles`.

## 6. Spun out as their own rows

See `TK76`–`TK79`. The short form:

* **`TK76`** — `tests/test_cascade_quiesce_gc.py:169` `graph.widx.paranoia = False` is
  **inert** (**READ**: `grep -c paranoia index_v4/wildcard.py` gives 0; `hasattr` gives
  False). The docstring at `:163` claims "Paranoia is OFF so the settle assert is the
  instrument under test rather than I6" and that is false. House failure mode, one day
  old, inside the pin module for `TK73`.
* **`TK77`** — the validation matrix and the hypothesis campaign have **zero** reach into
  the `_sync_entity_middles` surface (66 tests, 4m37s, empty census) because
  `tests/fga_schemas/wildcards.fga` and `boolean_wildcards.fga` both compute
  `crossable_shapes == []` under the matrix's `OBJECT_WC`.
* **`TK78`** — `index_v4/bulk_backfill.py` is an unaudited second reconcile implementation
  with no quiescence/settle/fixpoint check of any kind, and
  `index_v4/processor.py::DeltaProcessor.backfill` (`:1726`) **discards** `_bumped` where
  `_run_cascade` fans it out.
* **`TK79`** — `index_v4/processor.py:1611` justifies not suppressing the late GC rows with
  "an external `drain_deltas` replica must see them". **Nothing in the tree asserts it**;
  there is no in-tree outbox consumer at all.

## 7. Process finding — a concurrent writer raced this investigation

**READ.** Four of six agents independently detected that `index_v4/processor.py` was
mutated at ~23:28 on 2026-09-17 with
`_sk = sorted(...)` / `for key in (_sk[:-1] if len(_sk) > 1 else _sk)` — a
skip-the-last-key sabotage, i.e. someone running this very experiment directly on the
tracked tree — and reverted by ~23:35. It was not in the `git status` snapshot at launch.

It **produced false readings**: one agent's clean baseline silently flipped 0 to 5
mismatches, and another nearly filed a `_settle=None` result that is not reproducible now
(12 consecutive reruns and `PYTHONHASHSEED` 0-7 give the correct `SettlePass`). Both caught
it only because `inspect.getsource` disagreed with what they had read minutes earlier.

The tree was clean at HEAD `6c5b97c` before and after, and nothing was committed from that
window. **Standing rule earned:** a probe that matters pins a `git archive HEAD` export
under `.scratch/` and checks `git status --porcelain` before **and** after the run. This
machine runs concurrent sessions (machine `CLAUDE.md`), and a fan-out of agents over one
repo is itself a concurrent writer.
