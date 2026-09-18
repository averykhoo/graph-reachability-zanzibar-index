# TK74 — what actually catches a stale derived key, and how often the settle pass runs

**FROZEN 2026-09-18c — provenance, not a living document.** Status lines below are
as-of-then and several are now known false; live state: `python scripts/task.py show <id>`
and `HANDOFF.md`. Corrections are appended dated at the top, never edited into the body.
Opened 2026-09-18 as ACTIVE-PLAN; frozen when `TK74` closed and §9.10 was measured out.

⚠ **CORRECTION 2026-09-18c — READ §10 BEFORE CITING ANYTHING ABOVE IT.** §9.10's seven
open items were measured (six arms, all load-bearing claims re-verified first-hand). Two
sentences in this document are now known to be **stronger than the evidence supports**:

> 1. **"structurally incapable of detecting a skipped/stale reconcile at ANY schema
>    shape"** (§1, §9.2, and the `TK74` close message) needs the scope qualifier **"within
>    the cascade that skipped it"**. Across cascades the settle pass catches them
>    *opportunistically* — a later unrelated write surfaces the stale key and it raises.
>    §10.8 has the three-arm witness, reproduced first-hand.
> 2. **"the divergence is carried entirely in materialized closure edges"** (§9.5) is
>    **false** once a wildcard can reach an intersection. §9.5's own caveat called the
>    starred case untested; it is not clean. §10.5.

Also corrected in §10: §9.3's reachability route for the unguarded delete (`_gc_subject_node`
is transitively guarded — the live route is the ordinary `remove_tuple` one); §9.2's
"requires a WRITE" (it requires the reconcile to RUN and reach `_store_residue`); §9.1's
`driven` column (relation-level, not object-level — the miscount recurred a **fourth** time,
inside the correction written to fix it); and §9.4's census, whose `SETTLE_RAN = 0` does not
survive a deduped generator. **The overall verdict and the `TK82` design are unchanged.**

Provenance labels are per claim: **READ** (verified first-hand against the live tree by
the session that wrote the line), **MEASURED** (this session ran the probe and read the
literal output), **AGENT-MEASURED** (a subagent ran it; reproduced by at least one
independent skeptic but *not* re-run here), **REASONED**, **UNVERIFIED**. A subagent
report is evidence, not a finding (`CLAUDE.md` § Delegation).

Produced by a 17-agent fan-out (6 reproduction angles, 2 adversarial skeptics each, 1
completeness critic) run 2026-09-17/18 at HEAD `6c5b97c`, plus this session's own
first-hand re-measurement of the two load-bearing numbers.

**CORRECTION 2026-09-18b — §4's "next probe" HAS BEEN RUN (§8), AND ITS OWN GAPS ARE NOW
CLOSED (§9). Read §9 before citing §4 or §8.** Two fan-outs, 19 agents. The answer:

> **The TK73 settle pass is structurally incapable of detecting a skipped/stale reconcile,
> at ANY schema shape** — `leftover` is built exclusively from things that were WRITTEN
> (outbox rows above the final frontier, and the `_bumped` fan-out whose sole append is
> `_store_residue`, `index_v4/processor.py:1351`), and a stale reconcile is a *non-write*.
> Its teeth are real and correctly aimed at a **different** class (late reconcile-time GC
> emission). The only detector for *this* class is `audit_fixpoint` (I9), which has **zero
> production callers**.

⚠ **Two corrections to earlier sections, both load-bearing.** (1) §8.2 blamed the null on
`if not keys: break` (`:1583`) decapitating strict chains — that is one sufficient cause,
**not** the reason; §9.2 has the stronger law and the non-vacuous counter-instance. (2) §8.4's
"no paranoia tier fires" **overclaims**; §9.6 narrows it. §8.7's n of **6** is superseded by
**~62** skeptic-confirmed driven arms (§9.1), with the net still empty in every one.

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

## 8. 2026-09-18b — the multi-stratum skip experiment (§4's "next probe"), run

§4 left one blocking probe: drive a skipped **non-final-stratum** reconcile on a genuinely
multi-stratum schema, and see whether higher-stratum emissions map *back* onto the skipped
key via `_fan_out`, land it in `leftover`, and make the settle pass raise. **It has now been
run.** 11-agent fan-out (3 independent probes, 2 adversarial skeptics each on distinct
lenses — instrument and premise — plus reconciliation and a completeness critic).

### 8.1 Fixture selection — MEASURED first-hand (this session, 2026-09-18)

`zanzibar_utils_v1.parse_openfga_schema(text).compiled.strata` over `tests/fga_schemas/*.fga`:

```
6 strata [1,1,1,1,1,1]  demorgans_law_2.fga
5 strata [1,1,1,1,1]    demorgans_reverse.fga
5 strata [1,1,1,1,1]    demorgans_law_1.fga
4 strata [1,1,1,2]      wildcard_userset_cross.fga
3 strata [1,2,2]        userset_over_derived.fga
3 strata [1,1,2]        heterogeneous_tupleset.fga
2 strata [2,2]          tupleset_shapes.fga
2 strata [2,1]          boolean_wildcards.fga    <- everything before today ran HERE
```

Driven: `demorgans_law_2` (6), `demorgans_reverse` (5), `wildcard_userset_cross` (4).

### 8.2 The headline — the settle pass is blind, and n is 6, not 104

**AGENT-MEASURED**, reproduced by both skeptics on each schema. Unit = **skip arms**; one
arm = one op sequence with exactly one proven-productive non-final-stratum reconcile
suppressed by an instance-level monkeypatch.

| schema | strata | arms | shape **driven** | settle executed | settle raised | `leftover` non-empty | skipped key in `leftover` |
|---|---|---|---|---|---|---|---|
| `demorgans_law_2` | 6 | 50 | **0** | 0 | 0 | 0 | 0 |
| `demorgans_reverse` | 5 | 34 | **4** | 0 | 0 | 0 | 0 |
| `wildcard_userset_cross` | 4 | 20 | **2** | 0 | 0 | 0 | 0 |

⚠ **The `driven` column is the whole point, and the first-round probes got it wrong.**
"104 arms, settle executed 0 times" is the right count for *skips that produced no settle
execution*; it is the **wrong** count for *tests of the hypothesis*. On a strict-chain
schema the suppressed reconcile is the **sole scheduler of its dependent**, so
`index_v4/processor.py::DeltaProcessor._run_cascade`'s `if not keys: break` (`:1583`,
2026-09-18) **decapitates the cascade** and the shape is structurally unreachable. The
`dm2` probe sold "9 full 6-round cascades — the shape that had never been driven"; that
was its *unmutated census*, a fact about the control arm. Its `premise` skeptic measured
**0 of 50** and is right (`calls_after=0 HIGHER_after=0` on every row).

The mechanism is visible, not just the outcome — **AGENT-MEASURED**, `_map_deltas_to_keys`
call counts on one `dm2` cascade: unmutated **7**, skip stratum 0 -> **3**, stratum 1 -> **4**,
stratum 2 -> **5**, stratum 3 -> **6**. The skip does not perturb the cascade, it *collapses* it.

**So: 6 arms across 2 schemas genuinely drove the shape, and in all 6 the settle pass
stayed silent while the oracle disagreed.** On `wildcard_userset_cross` op#16 and op#17 the
combination "shape driven **and** user-visible wrong answer **and** settle pass silent" is
an observed fact (`divergences=3`, `first_bad_op=16` / `17`) — re-measured first-hand by
the reconciler, and claimed by no single probe.

### 8.3 The silence is reachability, not a weak assertion

**AGENT-MEASURED**, two independent agents, 4/4 and 2/2. Inject the skipped key into the
**post-loop** `_map_deltas_to_keys` return (`index_v4/processor.py:1629`) and the settle
pass executes, finds `changed`, and raises:

```
SettlePass(keys=(('cond','user_missing_requirement','c1'),),
         changed=(('cond','user_missing_requirement','c1'),))
InvariantViolation: cascade failed to quiesce after 6 strata rounds; the settle pass
CHANGED derived state at [('cond','user_missing_requirement','c1')]
```

**Do not "fix" the settle pass.** It is doing its declared `TK73` job (late-GC drainage);
it simply never sees the key.

### 8.4 No paranoia tier fires — and the null is controlled

**AGENT-MEASURED.** `off` / `residue` / `full` gave **byte-identical divergence counts** on
all 50 `dm2` arms and 0 raises on all 104 arms: `{'off': 0, 'residue': 0, 'full': 0}`. Not
merely "no raise" — no partial detection at any tier. **REASONED** (corroborated by an I6
positive control): a skipped reconcile leaves residue and refs *mutually consistent* — it
never writes. I1–I12 ask structural-consistency questions; staleness is semantic.

⚠ Instrument note, and it matters: the `dm2` probe cited its PC3 leftover-injection as the
control for this null, and its `premise` skeptic is **right that it is not one** — PC3
raises from the settle pass *inside* `_run_cascade` (`:1637-1643`), before any commit,
whereas `install_paranoia` (`index_v4/invariants.py:773`) registers before/after-**commit**
listeners. The gap was closed by a *different* agent (`wuc-instrument`), which sabotaged an
`EdgeV4` row per tier: `level=full ... RAISED InvariantViolation: store='g' [pre-commit]
I13: reference_count 4 != direct-edge degree 3`, with `off`/`residue` green. The null is
controlled — by someone else's control than the one the probe cited.

### 8.5 One detector catches it, and it is dead code in production

**AGENT-MEASURED**, 50/50 · 20/20 · 31/31, naming the skipped key every time:

```
I9: reconcile of (folder, owner, f1) was not a fixpoint -- derived state was stale
```

`index_v4/processor.py::DeltaProcessor.audit_fixpoint` (`:1732`, 2026-09-18) is the only
thing that sees this class. **READ**: zero production callers — outside `tests/` and
`.scratch/`, `grep -rn audit_fixpoint --include=*.py .` returns only
`formal/conformance/test_conformance_remove.py:435,519`, the comments at
`index_v4/invariants.py:184` and `index_v4/processor.py:1275`, and the definition.
(`tests/parity.py:98` is a harness, not a test — the closest thing to a would-be entry point.)

**That, not the settle pass, is the hole `TK74` found.**

### 8.6 Traps earned

- ⚠ **Inject at the post-loop map call only.** The reconciler's first positive control
  injected at an **in-loop** call; the loop then re-reconciled and **repaired** the key
  (`divergences` 3 -> 0, `rounds_seen` 4 -> 5, `0 / 2` raised). Reported as-is that reads as
  *"even forcing the key into `leftover` does not raise"* — the house failure mode, arriving
  from the instrument. Corrected to a post-loop-only injection: 2/2 RED, agreeing with the
  other agents' 4/4.
- ⚠ **`audit_fixpoint` (`:1738`) calls `self.reconcile`** — the *same* bound method a skip
  monkeypatch wraps. A wrapper left armed suppresses the **detector's** reconcile too and
  the audit reads green. Any sabotage of a fixpoint-based check must state its disarm point
  and prove it.
- ⚠ **A strict-chain schema is a dead instrument for this hypothesis.** Screen
  `compiled.dependents` for a key with two or more producers at *different* strata before
  believing a null. **MEASURED first-hand** (this session): across all 15 fixtures, exactly
  one has it — `heterogeneous_tupleset.fga` (`('doc','viewer')` and `('doc','quarantined')`
  each fed by `('custom_group','member')` at stratum 0 and `('group','member')` at stratum 1).
  Every other fixture is in-degree < 2.
- ⚠ **`graph.widx.paranoia = False` is INERT** — `grep -c paranoia index_v4/wildcard.py` -> **0**
  (run first-hand). `WildcardIndex` has no such attribute, so that line creates an unused one.
  Control the tier via `install_paranoia` / `make_wildcard_index`. This confirms `TK76` on the
  live tree.
- ⚠ **3 of 34 proven-productive skips on `demorgans_reverse` were MEMBERSHIP-NEUTRAL**: the
  suppressed reconcile genuinely returned `True` and would have rewritten residue/neg state,
  yet every `check` answer matched the oracle. **An answer-diffing staleness check scores
  those as clean pins.** The fixpoint question catches them; the answer question does not.

### 8.7 What is still unmeasured — do not read §8.2 as more than it is

1. **The residue-GC route into `leftover` is NOT covered by the `_fan_out` argument.**
   **READ**, `index_v4/processor.py::_map_deltas_to_keys` `:1420-1425` (2026-09-18): branch (A)
   maps a GC'd subject node id through `::_keys_referencing` (`:1424`) onto *every* key whose
   residue records that id — it does **not** consult `compiled.dependents` and is
   **stratum-agnostic**. It is therefore the one route that could legitimately place a
   skipped lower-stratum key in `leftover`. It was measured on `demorgans_law_2` **only**
   (`hits=0`) — the schema §8.2 proves is structurally incapable of driving the shape. **The
   single live route was measured only on the instrument known to be dead.**
2. **The shape was never driven through an INTERSECTION.** All 6 driven arms are
   exclusion-only (`but not`). `and` occurs in exactly one driven schema, `demorgans_law_2:24`,
   where 0 of 50 arms drove it.
3. **`heterogeneous_tupleset.fga` — the only structurally-capable fixture — was never run.**
4. **No habitat control.** `leftover` was empty in all 104 skip arms *and* all 61 unmutated
   control cascades; the settle pass has never been observed to execute at 2+ strata by any
   natural route. So "blind to skips" is not yet separable from "never runs here".
5. **Systematic bias: all 104 arms mutate the EXECUTION side** (`reconcile`). Nobody mutated
   the **scheduling** side (`_fan_out`, `_map_deltas_to_keys`, `compiled.dependents`). A
   scheduling-side miss never puts the key in the cascade's scheduled set at all — so a
   cheap touched-key check would not see it, and only full-key `audit_fixpoint` would.
6. **`4 of 34` on `demorgans_reverse` is single-sourced** — one agent, never re-run. Four of
   the six arms that constitute the entire n rest on that one log.

Items 1–4 and 6 are the subject of a second fan-out launched 2026-09-18b; this section will
carry a dated correction if any of them moves §8.2.

### 8.8 The design answer (round 1)

**Recommendation: yes, a cheap per-write staleness check should exist — but it cannot be
built out of the settle pass or out of paranoia I1–I12, and it must be opt-in.**

Ship it as a **new opt-in paranoia tier** beside `off`/`residue`/`full` at
`index_v4/invariants.py::install_paranoia` (`:773`), **default OFF**, asking the I9 fixpoint
question over a **bounded** key set.

⚠ **The key set must be the cascade's SCHEDULED-key union** (every key ever placed in
`_run_cascade`'s `keys` map across rounds, plus `leftover`) — **not** the reconciled set. The
skipped key is absent from the reconciled set *by construction*: its reconcile is precisely
what did not run. Specified the wrong way, the tier ships dead.

**Cost, stated honestly:** one extra full reconcile per key the cascade already reconciled —
roughly **doubles** cascade cost, and worse for subject-scoped rounds, since the settle pass
already notes a full-object reconcile "recomputes neg/upos wholesale" and is "the strictly
stronger fixpoint question" (**READ**, `:1639-1641`). Far past the ~+5% `residue` costs. It
cannot be the default.

**Bound it in the spec:** the narrowed tier detects **execution-side** misses only (§8.7
item 5). Full-key `audit_fixpoint` remains the only detector for scheduling-side misses, so
the cost argument is not comparing two checks that detect the same class.

**Rider, and arguably the real deliverable:** give `audit_fixpoint` at least one
production-reachable entry point. A complete detector for this entire class is currently
dead code outside tests.

### 8.9 Framing that must survive

**This is an assurance gap, not a live bug.** Every wrong answer in all 104 arms required a
deliberate instance-level monkeypatch; every unmutated control arm is `divergences=0`
(**AGENT-MEASURED**, e.g. `divergences=0 cascades=23 settle_executed=0 settle_raised=0`).
Nothing shipped is known to skip a reconcile. That is exactly why the answer is an opt-in
tier plus a production entry point for I9 — not a default-on cost on the write path.
The board's **Known live correctness bugs: 0** line stays at 0.

**Process:** the 2026-09-17 concurrent-writer incident (§7) did **not** recur. All 11 agents
reported empty `git status --porcelain` at both ends with HEAD pinned at `66655d7`, and the
reconciler cross-checked rather than trusting the reports — `cmp -s` of its own
`git archive HEAD` export against another agent's export and against the live tree both give
`SAME processor.py`. The orchestrating session verified clean before and after
independently.

## 9. 2026-09-18b (second fan-out) — the gaps in §8.7, closed

8-agent fan-out against §8.7's six open items: the structurally-capable fixture, the
intersection operator, the stratum-agnostic residue-GC route, a habitat control, and a
re-derivation of the single-sourced `4 of 34`. **§8.2's conclusion survives and is
upgraded from a lucky null to a structural one. §8.2's stated MECHANISM was half wrong
and is corrected in §9.2 — read that before citing §8.**

### 9.1 n went from 6 to ~62, and the net stayed empty

Unit = **skip arms** (one op-sequence replayed with one proven-productive, non-final-stratum
reconcile suppressed). "Driven" = a consumer of the skipped key reconciled at a **strictly
later cascade round**, scored **object-level**, and the result was oracle-wrong.

| fixture | strata | arms | driven | settle exec | settle raised | `leftover` non-empty | skipped key in `leftover` |
|---|---|---|---|---|---|---|---|
| `demorgans_law_2` (isect) | 6 | 138 | **54** | 0 | 0 | 0 | 0 |
| `heterogeneous_tupleset` (het) | 3 | 32 | **4** | 0 | 0 | 0 | 0 |
| `demorgans_reverse` (habitat) | 5 | 34 | **4** | 0 | 0 | 0 | 0 |
| three fixtures (gcroute) | 3–5 | 208 exec / 189 distinct | 2 strict | 0 | 0 | 0 | 0 |

**At least 62 skeptic-confirmed driven arms**, against §8.2's 6. In every one the settle
pass never executed, never raised, and `leftover` was never non-empty.

⚠ **The orchestrator's own round-2 premise was MEASURED FALSE** by the probe assigned to
exploit it. "`heterogeneous_tupleset` drives the shape by structure on every arm" is wrong:
only **4 of 32**, and all 4 required a **diamond** the probe had to *add* to the witness
(`cg1` a subgroup of both `g1` and `g2`; `d3` parented by both). Reason: invalidation is
**per-object** delta propagation, not per-relation, so relation-level multi-producer
structure does **not** create an independent scheduler. The fixture was still the right
instrument — it is the only one that *admits* the object-level diamond — but the shape had
to be constructed, not harvested.

### 9.2 ⚠ THE MECHANISM CORRECTION — §8.2 attributed the null to the wrong cause

§8.2 said the null came from `if not keys: break` (`index_v4/processor.py:1583`, 2026-09-18)
decapitating strict chains. **That is one sufficient cause, not the reason.** `het` built a
diamond that *defeats* decapitation — the cascade ran a full round 3 with 4–6 consumer
reconciles after the skip and emitted 3–7 outbox rows — and `leftover` was still empty. Its
skeptic supplied the non-vacuous instance (**MEASURED**):

```
arms where the :1629 map saw >=1 outbox ROW : 3 / 32
    (34,3,rows=1,keys=0)  (35,2,rows=3,keys=0)  (35,3,rows=4,keys=0)
arms where the :1629 map returned >=1 KEY   : 0 / 32
```

The final round **did** write and **did** emit, and `_map_deltas_to_keys` still returned
zero keys. **The correct law, READ at `:1628-1633` and `:1351`:**

> `leftover` is built **exclusively** from (a) outbox rows written above the final frontier
> and (b) the `_bumped` fan-out, whose sole append site is `_store_residue` (`:1351`).
> **Both require a WRITE. A suppressed or stale reconcile is a non-write.**

So the settle pass is **structurally incapable** of seeing this class **at any schema
shape**, and no amount of multi-path structure helps. This is stronger than §8.2's claim
and it rules out the cheap alternative — "widen the settle pass / add a round" is a
different net for a different class (late reconcile-time GC emission), where its teeth are
demonstrably real (`het` PC2: **4/4** raises on the very arms where it stayed silent).

### 9.3 The residue-GC route (§8.7 item 1) — CLOSED, and it is structural too

**READ**, `index_v4/processor.py::_map_deltas_to_keys` branch (A), `:1422-1425`. The
decisive point is the **loop head**: the candidate set is `{r.subject_node_id for r in rows}`
— **branch (A) is itself rows-driven**, so it inherits the same write-precondition as the
main fan-out. That is a code fact, not a fixture fact.

**MEASURED** (`gcroute` + skeptic), unit = `_keys_referencing` calls at the `:1424` site:
**781 calls = 708 in-loop (`:1577`) + 73 post-loop (`:1629`) + 0 tail (`:1651`)**. 113
returned non-empty — **113 at `:1577`, 0 at `:1629`**. 16 arms had branch (A) return the
skipped key itself, all at `:1577`, where the cascade simply re-reconciles it inside the loop.

Why, **READ first-hand**: both processor GC paths refuse to delete a residue-referenced
node, so anything they *do* delete has an empty `_keys_referencing` by construction —
`_gc_subject_node` (`:1066`) guards at `:1075`, `_gc_public_node` (`:1282`) guards on
`reference_count == 0 and _residue_row(...) is None and not _residue_references(...)`.

**The route is WIRED, not dead** — positive control, force one post-loop branch-(A) return
and make the key genuinely stale:

```
PC-ROUTE teeth  bA_calls@1629=1 forced=1 settle=SettlePass(keys=(('attr','does_not_label','at1'),),
                changed=(('attr','does_not_label','at1'),))
InvariantViolation: cascade failed to quiesce after 5 strata rounds; the settle pass
CHANGED derived state at [('attr','does_not_label','at1')]
```

⚠ **THE ONE NAMED CRACK, with its citation corrected.** `gcroute` reported an unguarded
implicit-node-delete path as `index_v4/core.py::_adjust_reference_counts`. **MEASURED
first-hand by this session: that symbol does not exist anywhere in the tracked tree**
(`grep -rn "_adjust_reference_counts" --include=*.py .` → no match). The *code* is real and
the line numbers are right; the enclosing symbol is
`index_v4/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl` (`:714`; class at `:267`),
whose two implicit-delete branches (`:877` and `:894`, 2026-09-18) delete a node with **no
residue-reference check**, unlike both processor GC paths, and are reachable post-final-round
via `_gc_subject_node` → `index_v4/wildcard.py::WildcardIndex._maybe_remove_bridges` (`:437`).
Status: **unobserved in 208 arm executions, not excluded by any guard**. This is the
`CLAUDE.md` "cite a symbol that EXISTS" trap catching a live phantom — the finding survives,
the citation did not.

### 9.4 The habitat control (§8.7 item 4) — the settle pass DOES execute at 3 strata

**AGENT-MEASURED, and reproduced first-hand by the reconciler** (`rc=0`, `BOTH ARMS MOVED = True`):

```
== W_HABITAT  (paranoia=off)  strata=3 [[('folder','owner')], [('box','b1')], [('box','b2')]]
   op3  remove (..., 'folder','x','parent','folder','y')  ok=True
        _settle=SettlePass(keys=(('folder','owner','x'),), changed=())
   oracle grid: 420 queries, divergences=0      audit_fixpoint: CLEAN
   SETTLE PASS EXECUTED in 1 of 4 cascades  -> keys=[('folder','owner','x')] changed=[] FIXPOINT=True
```

**This separates "blind to skips" from "never runs here", which §8 could not.** Three things
it pins: the pass executes on a 3-stratum schema with **no skip and no fault injection** and
returns a fixpoint; the leftover key is **stratum 0**, so the pass is not restricted to
final-stratum keys — `leftover` is simply emission-driven; and the instrument wraps
*nothing*, it only reads `_settle`, so no stray wrapper can suppress it.

**The habitat is brittle, and that is the finding.** Adding one tuple `folder:x src box:bx`
moves the emitting `_gc_subject_node` from round 2 to round 0, where rounds 1–2 drain it,
and the pass goes silent. It had to be **engineered**: across **2385** multi-stratum cascades
fuzzed over all 15 fixtures plus 3 engineered schemas, `SETTLE_RAN = 0`
(**PROBE-MEASURED, SKEPTIC-UNREVIEWED** — the reconciler reproduced the witness, not the census).

### 9.5 Intersection (§8.7 item 2) — closed, and it changes nothing

**Fixture substitution, justified and skeptic-confirmed.** The assigned `tupleset_shapes.fga`
is **disqualified on structure**: its only `PIntersection` is `('doc','approved_parent')` at
stratum 0 with `derived_deps=()` (both children are `PClosureLeaf`s), and `via_intersection`
is a `PDerivedTuplesetTTU`, not an intersection node. A compiler screen of all 15 fixtures
found **exactly one** `PIntersection` anywhere with a non-empty derived dep:
`demorgans_law_2.fga::('role','authorized_user')` at stratum 4. The measurement was carried there.

```
arms_total 138 | settle EXECUTED 0 | settle RAISED 0 | leftover non-empty 0
arms with >=1 oracle divergence 138 | audit_fixpoint RAISED 138
TIGHT (intersection reconciled AFTER the skip AND ended WRONG, same object): 16 {stratum 1:8, 2:8}
```

In **16 arms the intersection provably ran half-stale** — fresh leaf child, stale derived
child — and committed a wrong answer, with the settle pass never executing.

**Stratum 3 contributes zero tight arms (0 of 41)**, structurally: `('role','role_user_met')`
is the intersection's *sole* scheduler, so skipping it decapitates its own consumer.
**Corollary worth carrying: "skip the node directly feeding the operator" is the WRONG
instrument for this class** — a half-stale operator is only reachable from ≥2 strata below it.

**The G5 hypothesis is FALSE, recorded so nobody re-hypothesises it.** A half-stale
intersection does not write a *different* residue signature; it writes **none**. All 13
baseline `ResidueV1` rows were dumped (joined to `NodeV4`, not a guessed subset); zero sit on
`authorized_user` in either the correct or the stale state. Intersection and exclusion behave
identically — `residue=None` in both states while members diverge `('alice',)` → `('alice','bob')`.
The divergence is carried entirely in materialized closure edges. **CAVEAT** (REASONED,
unexecuted): `assigned: [user]` admits no wildcard, and every other in-tree `PIntersection`
has `deps=()`, so a **starred** half-stale intersection is unreachable across all 15 fixtures.
That residue channel is **untested, not tested-and-clean**.

### 9.6 §8.4 overclaimed — "no paranoia tier fires" must be narrowed

`gcroute` MEASURED a real raise at the FULL tier on `demorgans_reverse`:

```
InvariantViolation: store='g' [pre-commit] I6: residue neg holds a dead node id 12
on type='attr' id=11 ... predicate='does_not_label' ... name='at1'
```

**Reconciled statement:** paranoia fires on a *minority* of skip arms on *one* fixture — 5
raises across 208 arm executions (~2.4%), all skipping the same key — and it fires on a
**structural side-effect** of the skip (a dangling dead node id left in a residue's `neg`),
**not on the staleness**. `het` (correct tier control) and the corrected `isect` re-run both
measured **0** fires, arm-for-arm identical across off/residue/full. So §8.4's sentence
narrows to: *no tier detects the closure-edge-only staleness; the FULL tier incidentally
catches a dangling-id side-effect on ~2.4% of arms on one fixture.*

### 9.7 ⚠ A LIVE ASSURANCE TRAP IN TRACKED TEST CODE — the tier knob is a lie

**MEASURED first-hand by this session**, and it is the reason §9.8's next action is what it is:

```
make_wildcard_index(paranoia=False)     -> guard=None        level=None
make_wildcard_index(paranoia='off')     -> guard=ParanoiaGuard level='full'   (!!)
make_wildcard_index(paranoia='residue') -> guard=ParanoiaGuard level='full'   (!!)
install_paranoia(level='off')           -> guard=None        level=None
install_paranoia(level='residue')       -> guard=ParanoiaGuard level='residue'
```

**READ**, `tests/wildcard_helpers.py::make_wildcard_index` (`:19-35`, 2026-09-18): the
signature is `paranoia: bool = True` and the body is `if paranoia: install_paranoia(session,
store_id, schema_info)` — **no `level=` forwarded** — while
`index_v4/invariants.py::install_paranoia` (`:773-775`) defaults `level=PARANOIA_FULL`. The
string `'off'` is **truthy**, so it installs **FULL**.

The irony is load-bearing: `index_v4/invariants.py::normalize_paranoia_level` (`:112-130`)
already handles bools *and* strings and raises loudly on a typo, with the docstring *"a
typo'd security switch must never silently mean 'off'"*. `make_wildcard_index` violates that
exact intent one layer up — a typo'd switch here silently means **full**.

**It already cost this investigation a measurement**: `isect`'s three-tier sweep actually ran
off/FULL/FULL, and only its skeptic's corrected re-run is citable. Every present and future
"we swept the tiers" claim is unverifiable until this is fixed.

### 9.8 Traps earned (round 2)

- ⚠ **Count OBJECT-level, at a STRICTLY LATER cascade round, AND oracle-wrong.** Probe vs
  skeptic disagreed on the driven count **three times**, the same error each time —
  `isect` 130 vs **54**, `gcroute` 5 vs **2 strict**, and round 1's own 104 vs **6**. Every
  time the probe's metric was relation-level over any object, or ignored the round index.
  **The skeptics were right in all three.** `isect` even *had* the corrected metric (its own
  `tight.py`, 95 → 16) and shipped the uncorrected number as its headline anyway.
- ⚠ **`make_wildcard_index(paranoia=<string>)` silently installs FULL** (§9.7). Control a
  tier with `install_paranoia(..., level=...)` until that is fixed.
- ⚠ **A phantom symbol nearly reached a tracked doc** (§9.3). Grep `file::symbol` before
  writing it down — the code can be real while the name is invented.
- ⚠ **Units inside assurance numbers.** `gcroute`'s `escaped_raise: 4` was **runs**, not
  arms (arm count 2); its `arms_total: 208` was **executions over 189 distinct
  configurations** (19 duplicates, sized only when the skeptic re-ran and matched byte-for-byte).
- ⚠ **State the measurement WINDOW of a detector claim.** §8.5's "`audit_fixpoint` catches it
  every time" is true **only for an audit fired in the same op as the skip**: `gcroute`
  measured 57/58 same-op but **11/58** at end-of-witness, and `habitat` measured 31/31 at the
  first divergent op but **0 of 34** still-divergent after the full 22-op workload. Three
  windows, three numbers, all correct.
- ⚠ **`demorgans_reverse`'s "4 of 34" has new provenance.** No round-1 artifact contains it —
  `.scratch/tk74b-dmr-instrument/shape_driven.log` scores at *relation* level and closes
  `SHAPE DRIVEN in 3 / 7 probed skips` (7 probed, not 34). `habitat` **independently
  re-derived 4/34 object-level with a different composition**. Cite it as habitat's
  re-derivation (2026-09-18b), never as a read of the round-1 log.

### 9.9 The design answer — confirmed, with three amendments

**Unchanged:** ship a new **opt-in paranoia tier**, default OFF, asking the I9 fixpoint
question over the cascade's **scheduled-key union**. **READ** `:1591-1598`: the
`for key in sorted(keys, ...)` loop is the *only* in-loop reconcile dispatch, so every
suppressed call in all four probes came from it and the skipped key was in `keys`
**by construction** — while being absent from `leftover` by construction, for the opposite
reason (§9.2). Taking the union from the **scheduling** side also keeps the detector
independent of the execution side it is detecting.

**AMENDMENT 1 — timing is load-bearing, and it demotes the `audit_fixpoint` half.** Staleness
here is usually **transient**: 31 of 34 arms on `demorgans_reverse` are transiently divergent
and **0 of 34** still divergent after the workload — later writes launder it. So a **periodic
or end-of-run `audit_fixpoint` sweep is worth ≈0 as a detector** for this class. The
production entry point should ship framed as a **repair/diagnosis** tool (its docstring
already names `backfill()` as the recovery path), not as the net. **If only one of the two
ships, ship the tier.**

**AMENDMENT 2 — restate the bound's mechanism** per §9.2. This definitively rules out
"just widen the settle pass".

**AMENDMENT 3 — a prerequisite the round-1 design did not know about.** §9.7. **You cannot
ship a new TIER into a harness whose tier knob is a lie.** Fix it first, with a sabotage test
that goes RED before the fix.

**Cost** (MEASURED on a toy store, read as a *shape*, not a benchmark): scheduled-union 112
vs `audit_fixpoint` scope 233 derived keys over 38 cascades on `heterogeneous_tupleset`
(ratio 0.481, upper bound — the store peaks at 9 live derived keys). The durable claim is
**REASONED from the code**: the tier is **O(cascade work)**, `audit_fixpoint` is **O(live
derived keys in the store)**, unbounded by the size of the write. That asymmetry is the
argument for the tier, and for default OFF.

**Scope bound, confirmed unchanged:** execution-side misses only. No round-2 arm falsified
`_fan_out` (`:1504`), `_map_deltas_to_keys`'s key derivation, or `compiled.dependents`, so a
**scheduling-side** bug — a key never scheduled at all — is out of scope for this tier and
stays uncovered by it.

**Mandatory sabotage for the tier** (`docs/sabotage-procedure.md`): the narrowest plausible
weakening is **take the union from the RECONCILED set instead of the SCHEDULED set** and
watch the test go green. That is the failure mode the design chooses against, and it must be
shown to fail by passing before the choice is believed.

### 9.10 Still unmeasured after round 2

1. Whether a **coincidental** late-GC emission from some *other* write can place a skipped key
   into `leftover` — the one part of the blindness that is UNOBSERVED rather than STRUCTURAL
   (bounded: 0 of 73 post-loop branch-(A) calls non-empty; 0 of 208 arms).
2. The unguarded implicit-node delete at `core.py::ReachabilityIndex._add_direct_edge_unsafe_impl`
   (`:877`/`:894`) — never deliberately driven.
3. A **starred** half-stale intersection — unreachable across all 15 fixtures (§9.5).
4. `habitat`'s 2385-cascade census — **skipped by the skeptic pass entirely**; `habitat` is the
   one round-2 gap with an empty skeptic list.
5. The tier's **false-positive rate** — nobody ran the union re-reconcile on unmutated traffic.
6. PostgreSQL. Everything in both rounds ran on SQLite in-memory; no `_lock_store`, watermark
   or multi-instance path was touched.
7. No generated-schema sweep — `tests/test_hypothesis.py`'s machinery was never pointed at
   this question, so "structural at any schema shape" rests on the **code read**, not a search.

---

## 10. 2026-09-18c (third fan-out) — §9.10's seven items, measured

Six arms, one per §9.10 item (items 1 and 4 share an arm, since both are "does anything ever
put a key into `leftover` that was not written"). Every structural claim below was
**re-verified first-hand by this session** against HEAD `05e4ba2` before it was written here;
where an arm's report and this session's own read disagree, the read wins and the
disagreement is recorded rather than averaged (`CLAUDE.md` § Delegation).

Provenance labels are as declared at the top of this file.

### 10.0 The law re-verified, and the one hole in it

**READ first-hand, 2026-09-18c.** §9.2's law survives an independent enumeration:
`leftover` has exactly one assignment (`index_v4/processor.py:1629`) and exactly one
mutation (`:1632`, the `_bumped` fan-out); `self._bumped` has exactly one `.append` site
(`:1351`, in `_store_residue`). There is no third path.

⚠ **But "rows-driven" is not the same as "written-key-driven", and §9.3 elided the
difference.** `_map_deltas_to_keys` branch (A) (`:1422-1425`) has a rows-driven *loop head*
— `for nid in {r.subject_node_id for r in rows}` — yet the key it inserts is not the key
that was written: it is `ref_key`, drawn from `_keys_referencing(nid)` (`:568`, served by
the `ResidueRefV1` reverse index). **Branch (A) is therefore a genuine path by which a
NON-WRITTEN key can enter `leftover`**, and it is the only one.

What closes it is not the write-precondition but §9.3's *guard* argument: a node reaching
branch (A) has been GC'd, and both processor GC paths refuse to delete a residue-referenced
node, so `_keys_referencing` on it is empty by construction. **READ first-hand:**
`_gc_subject_node` returns at `:1075-1076` (`if self._residue_row(n.id) is not None or
self._residue_references(n.id): return`), `_gc_public_node` at `:1296-1299`.

**So §9.10 items 1 and 2 are ONE mechanism, not two loose ends.** Item 2's unguarded delete
is precisely the hole in item 1's argument: `index_v4/core.py` deletes `NodeV4` at three
sites with **no residue consultation at all** (`grep _residue index_v4/core.py` → no match),
and a node killed there can still be residue-referenced — which is exactly the precondition
branch (A) needs. The two arms were run separately and are reconciled in §10.1–10.2.

### 10.1 Item 2 / row `TK80` — the delete is REACHED, and it commits corruption on one path

**Verdict: OBSERVED-AND-POSSIBLE.** Not unreachable, and no longer unobserved — §9.3's
"unobserved in 208 arm executions" is **refuted**.

**The branch table, READ first-hand and dated 2026-09-18c** (`_add_direct_edge_unsafe_impl`
at `:714`, class `ReachabilityIndex` at `:267`). §9.3 named two branches; **there are
three**, and the one it omitted is the only *unguarded* one:

| line | branch | guard | reachable from |
|---|---|---|---|
| `:875-877` | neighbour-debit implicit GC | `implicit` only | self-edge path only |
| `:882-884` | `_node = nodes.get(subject_id)` → evict → delete | **NONE** — no `implicit`, no residue | self-edge path only |
| `:892-894` | `reference_count + count == 0 and _node.implicit` → delete | `implicit` only | **every** `add_edge` / `remove_edge` |

⚠ **The arm claimed the self-edge path is `remove_node`-only; this session verified the
claim AND supplied the reason it is true**, because the claim as stated did not survive the
obvious objection (this repo has `tests/test_self_referential_tuples.py`, so a self-edge
removal looks reachable from `remove_tuple`). It is not: a self direct edge is **never
created** — `:854` guards `if subject_id != object_id and count > 0` — so
`_remove_edge_locked` finds `direct_edge_count == 0` and raises `AdmissionRejected` at
`:1135-1141` before reaching `:1143`. A cycle's self `Edge` row carries only
`indirect_edge_count` and is rejected by the same test. `_add_direct_edge_unsafe` has exactly
three call sites (`:1099` add, `:1143` remove, `:1204` in `remove_node`), so `:877`/`:884`
are `remove_node`-only **by construction**, not by observation.

⚠ **§9.3's stated reachability route is WRONG and is corrected here.** `_gc_subject_node` →
`WildcardIndex._maybe_remove_bridges` (`wildcard.py:437`) is **transitively guarded** —
`_gc_subject_node` returns at `:1075-1076` before it ever reaches the `_maybe_remove_bridges`
call at `:1096`, exactly when a residue references the node. **READ first-hand.** The live
route is the ordinary one: `remove_tuple` → `_remove_tuple_trusted:645` →
`remove_edge_by_id:1149` → `_remove_edge_locked:1143` → `:894`.

**MEASURED (arm, single-sourced, reproduced in structure but not re-run here):**

| path | removals | node deletes | deletes with a LIVE residue ref | committed corruptions |
|---|---|---|---|---|
| `remove_tuple` + `run_cascade` (shipped) | 31 | 87 | 2 | **0** |
| `remove_node` + cascade | — | 48 runs | 4 | **0** |
| `remove_node`, **no cascade** | — | 48 runs | 4 | **2** |
| ordinary suite census (120 tests) | — | 240 | 2 | 0 |

The corrupting path raises, verbatim:

```
independent check_invariants RAISED: I6: residue neg holds a dead node id 4 on
store_id='s_off' predicate='access' name='d' implicit=False id=3 type='doc'
wildcard='' reference_count=0
```

and is **refused pre-commit at both live paranoia tiers** (`residue`, `full`); it commits
silently only at the production default (`off`). The arm verified tier forwarding first-hand
before trusting that result (§9.7's trap), and this session independently confirmed the fix
is live: `tests/wildcard_helpers.py:42` forwards `level=paranoia`, pinned by
`tests/test_paranoia_wiring.py::test_helper_forwards_the_tier` (`:350`).

**Severity is bounded, and the hazard was already named in the tree.** `remove_node` has no
caller in `connectedstore/` (**READ first-hand**: the only non-test callers are
`index_v4/wildcard.py:697` → `index_v4/core.py:1199`), and
`tests/test_reg14_residue_gc_elision.py::test_reg14_cheap_path_self_heals_a_missing_userset_node`
already documents it as an admin-API gap with a self-heal mitigation. **`TK80` stays `LATER`.**

⚠ **The arm ran a control that FAILED to go red, and reported it honestly — it is the most
useful thing in the arm.** Stubbing `_keys_referencing` to `[]` (neutralising branch (A))
on the reproducing workload left the state CLEAN. **Branch (A) is therefore not the only
repair**; the ordinary leaf/dependent fan-out in the same function also reconciles the key.
The delete's safety rests on **at least two independent downstream repairs, neither of which
is a guard on the delete itself** — which is why the fix belongs on the delete.

### 10.2 Item 7 — the generated-schema search, run; §9.2's law SURVIVES and gets tighter

**Verdict: CLOSED BY SEARCH. No counter-instance.** "Structural at any schema shape" no
longer rests on the code read alone.

**AGENT-MEASURED**, over **588** distinct generated schemas (strata depth to 5), **738**
skip arms, **31,824** executed cascades: `skipped key in leftover` = **0**, settle pass
executed **0** times. Generator is the repo's own campaign grammar
(`tests/test_hypothesis.py::_schema_ast` driven by `::_RandomChoices`, workloads from
`::_op_pool`).

The zero is **non-vacuous on both sides**, which is what §8.7 item 7 actually needed:

* *Staleness side* — **682 of 738** arms were truncated so the skip cascade is last, and
  I9 then confirmed the store was **genuinely left non-fixpoint** at the moment
  `_run_cascade` returned (388/443 full-reconcile, 294/295 subject-scoped). The fault was
  real in 92% of arms and the settle pass saw nothing in every one.
* *Rows side* — a post-loop census on the `:1629` call over the same 8,688 unmutated
  cascades: **416 calls were fed ≥1 outbox row and returned 0 keys**. That replicates
  §9.2's `het` instance (`rows>=1: 3/32`, `keys>=1: 0/32`) at ~130× the scale, on
  generated schemas.

⚠ **TWO CORRECTIONS TO §9.2's LAW, both verified first-hand by this session.**

1. **The law is TIGHTER than stated — the enumeration closes by SIGNATURE, not by branch
   inspection.** `_fan_out` (`index_v4/processor.py:1504-1543`, next `def` at `:1544`)
   takes a `keys: dict` parameter and **never reads or writes it**: `keys` occurs exactly
   once in the whole function, on the signature line `:1505`. **READ first-hand.** Every
   invalidation it performs goes through the `full` callback instead. So `:1632`'s lambda
   is not merely the only *observed* channel into `leftover` — it is the only *possible*
   one. (The dead parameter is passed at `:1471`, `:1580`, `:1631`, `:1654`. Not a defect;
   noted as a cleanup in §10.6.)
2. ⚠ **The (b) clause's precondition is MIS-STATED and must be narrowed.** §9.2 says the
   `_bumped` half "requires a WRITE". **READ first-hand at `:1329-1351`:** `_store_residue`
   early-returns at `:1331-1333` **only** when `row is None and empty`. Its `elif empty`
   branch deletes the row (`:1339`) and its `else` branch rewrites all three columns and
   does `row.version += 1` (`:1341-1345`) **even when the values are unchanged** — and both
   fall through to the `:1351` append. The accurate precondition is therefore **"the
   reconcile RAN and reached `_store_residue` past that early return"**, not "a write
   occurred".
   **The conclusion is unaffected** — a suppressed reconcile never calls `_store_residue`
   at all — but §9.2 as written claims more than the code guarantees, and a future session
   reasoning from the stronger sentence would be reasoning from something false.

**Settle-pass null, combined and re-stated on 2026-09-18c:** `SETTLE_RAN = 0` over
**16,497** unmutated cascades — 2,385 handwritten-fixture (§9.4) + 14,112 generated
(8,688 full + 5,424 subject-scoped).

**Instrument limits, recorded because they bound the claim** (AGENT-REPORTED, not
independently re-run): the grammar has two entity types, relations `r0..r4`, one tupleset
body drawn from 8, and a 5-name universe — so "any schema shape" means *any shape this
repo's own campaign generates*, which includes **no object-wildcard shapes** and no HA
structure. 114 of 500 drawn schemas were `UnsupportedByGraphIndex` and never ran. And the
fault model is one *suppressed* reconcile; a reconcile that RUNS but reads a stale input
was not injected — §9.2's argument covers it identically (still a non-write for the
consumer key) but that remains **REASONED**, not measured.

### 10.3 Item 5 — the `TK82` tier's false-positive rate is ZERO, and the design choice is unfalsifiable on clean traffic

**Verdict: CLOSED. Nothing about false positives blocks shipping `TK82`.** But the arm's
*second* result matters more to the design than the first, and it is recorded here because
it changes what evidence the item is allowed to accept.

**AGENT-MEASURED**, 8 seeds × 40 ops over the **9** fixtures that have derived predicates
(the other 6 of 15 are `NO_DERIVED` — `RuleSet.compiled` has no plans, so the tier is
vacuous there and they must not be counted as passing):

```
---- TOTALS: cascades=2853 tier_ran=2853 keys_rereconciled=3358 FALSE_POSITIVE_CASCADES=0 settle_ran=0 bumped_grew=0
FP RATE = 0 / 2853 cascades
```

The zero is controlled at both ends, which is what makes it a measurement rather than a
hope:

```
---- CONTROL TOTALS: {'arms': 49, 'wrong': 43, 'B_raise': 49, 'C_raise': 0, 'B_raise_and_wrong': 43, 'C_raise_and_wrong': 0}
CONTROL (job 4): proposed tier raised on 43 / 43 genuinely-wrong arms
SABOTAGE  (job 5): reconciled-union tier raised on 0 / 43 genuinely-wrong arms
```

* **The detector has teeth: 43/43** on arms where the state is genuinely oracle-wrong.
* **§9.9's mandatory sabotage behaves exactly as predicted: 0/43.** The reconciled-union
  variant ships **dead**. Note the sabotaged union is *not* trivially empty — `|U_C| = 1`
  where `|U_B| = 2` on several arms — it is non-empty and still blind, which is a more
  convincing failure than an empty set would have been.
* **The tier is strictly MORE sensitive than the oracle grid: 49 raises on 43 wrong arms.**
  On the 6 extra arms the suppressed reconcile left derived state internally stale while
  the check surface still answered correctly. These are `TK81`'s transiently-divergent
  cases, caught before a later write launders them. **That is a detector firing on a
  genuine I9 violation, not a false positive** — and it is the strongest argument yet
  against `TK81`'s "a periodic audit is worth ~zero", because a *per-cascade* tier catches
  what a *periodic* audit cannot.

⚠ **THE LOAD-BEARING RESULT, and it belongs next to §9.9 AMENDMENT 3.** On unmutated
traffic the scheduled union and the dispatched (reconciled) set are **byte-identical** —
`union_minus_dispatched = 0` and `never_dispatched = 0` across 3,744 clean cascades
(1239/1239, 3344/3344, 288/288). **So the right design and the sabotaged design are
indistinguishable by ANY clean-traffic measurement — same cost, same FP rate, same union
size.** The scheduled-vs-reconciled choice can be justified **only** by a fault-injection
arm. A benchmark cannot see it. `TK82` must therefore carry its sabotage as a permanent
test, not as a one-time check.

⚠ **A trap earned: do NOT write "the tier is a subset of `audit_fixpoint`".** The
per-cascade ratio of scheduled-union size to `audit_fixpoint` scope **exceeds 1, max 2.0 on
four fixtures**. REASONED cause: the union is scheduled from deltas, so it can contain keys
whose object has just gone dead and left `_live_keys_of`'s enumeration (`:1671`) — keys
`audit_fixpoint` (`:1732-1742`) would never visit. The aggregate ratio is **0.242** over
1,429 cascades (2026-09-18c, **40-op toy stores** — quote it only with that caveat).
§9.9's single toy-store `0.481` is not contradicted, it is unrepresentative. The durable
claim stays the REASONED one: the tier is **O(cascade work)**, `audit_fixpoint` is
**O(live derived keys)**, unbounded by write size.

**Instrument caveat that must survive into `TK82`:** the arm wrapped the *public*
`run_cascade` (`:1544`), so its re-reconciles ran **outside** `_node_cache_scope()` +
`_stored_cache_scope()`. That is the stronger question (a stale memo cannot mask a
divergence), but **a tier shipped INSIDE those scopes is not what was measured — re-measure
if `TK82` lands inside them.**

**No control coverage on two fixtures**, and they must not be counted: `owc_star_ttu`
(1 stratum, so "non-final stratum" is empty by definition) and `demorgans_law_1` (0
productive non-final-stratum reconciles in 16 ops).

### 10.4 ⚠ AN INSTRUMENT BUG IN THE ROUND-2 HARNESS — reproduced first-hand

**MEASURED first-hand by this session**, not taken from the arm that found it:

```
add1 None
add2 None
rm   None
still present? True
```

`WildcardIndex.add_tuple` is **ref-counted**: `add(t); add(t); remove(t)` leaves `t`
**present**. The sanctioned write path is not: `connectedstore/source.py::TupleSource.add`
(`:470-473`) is documented *"Idempotent on duplicates (raw tuples are a set): no state
change, no log row"* and enforces it via `_add_tuple_direct` (`:489`).

**So a probe that writes straight to `WildcardIndex` and draws adds from the whole pool
without excluding already-live tuples silently diverges from `tests/oracle.py`** — graph
`True`, oracle `False` — for reasons that have nothing to do with the property under test.
The `fprate` arm hit it on 28 seed-runs across 7 of 9 fixtures before fixing its generator;
its headline was unchanged by the fix (FP was 0 either way), but **the meaning changed**,
because a false-positive rate measured on oracle-divergent traffic is not the number
§9.10 item 5 asked for.

⚠ **This impugns a ROUND-2 number.** `.scratch/tk74c-habitat/habitat_fuzz.py` and
`habitat_census.py` share that generator and never oracle-checked — and that is the code
behind §9.4's **2385-cascade `SETTLE_RAN = 0` census**, i.e. §9.10 item 4, the one round-2
arm with an empty skeptic list. The item-4 arm was warned mid-flight and asked to re-run
the census with a deduping generator and report both numbers; the outcome is §10.5.

**The durable rule, and it is new:** *a harness that writes directly to a backend must
reproduce that backend's admission semantics, or its oracle comparison means nothing.*
Prefer driving `TupleSource`/`ConnectedStore`, which dedupes for you.

### 10.5 ⚠ Item 3 — §9.5's "the residue channel is clean" is REFUTED; it was untested, and it is wrong

**Verdict: DIVERGENT.** §9.5 recorded, correctly for its fixture, that a half-stale
intersection writes **no residue at all** and that "the divergence is carried entirely in
materialized closure edges". §9.5's own CAVEAT flagged the starred case as *untested, not
tested-and-clean*. It was right to hedge: **the starred case is not clean.**

**The premise re-verified first-hand, 2026-09-18c.** Exactly **3** `PIntersection` nodes
exist in the whole tree, and the screen below is this session's own run, not the arm's:

| fixture | intersection key | stratum | `Plan.deps` | star-admitting leaf child? |
|---|---|---|---|---|
| `boolean_wildcards.fga` | `('doc','restricted')` | 0 | `()` | **yes** (`public: [user:*]`) — but nothing to go stale |
| `demorgans_law_2.fga` | `('role','authorized_user')` | 4 | `(('role','role_user_met'),)` | **no** (`assigned: [user]`) |
| `tupleset_shapes.fga` | `('doc','approved_parent')` | 0 | `()` | no |

**So no in-tree fixture has both a non-empty derived dep AND a star-admitting leaf child.**
That is *why* §9.5 measured `residue=None`, and the mechanism is now MEASURED rather than
assumed: stars *do* reach `demorgans_law_2`'s intersection through the derived child, but
`stars ∩ no-stars = ∅`, so nothing is ever written.

**The constructed fixture is inside the supported fragment** — this matters, because "the
graph index rejects it" would have been a perfectly good answer and is not the answer.
`.scratch/tk74d-starisect/star_isect.fga` is `demorgans_law_2.fga` with **one token
changed** (`define assigned: [user]` → `[user, user:*]`). **Verified first-hand:** it
compiles with no `UnsupportedByGraphIndex` and no `ValueError`, same six strata, with
`('role','authorized_user')` at stratum 4, `deps=(('role','role_user_met'),)`.

**And the intersection then DOES write a residue — reproduced first-hand by this session**
(the arm's control re-run here, `rc=0`):

```
CONTROL divergences (unit: grid queries): 0 grid size: 160
CONTROL audit_fixpoint: clean
CONTROL ResidueV1 rows (unit: residue rows): 20
   ('role', 'authorized_user', 'r3')   stars=[["user", "..."]]   neg=[]   upos=[]
```

**In the half-stale state that residue is WRONG** (AGENT-MEASURED, 144 arms; TIGHT = §9.8's
corrected rule, object-level at a strictly later round and oracle-wrong):

```
  TIGHT arms                                   : 18 {1: 9, 2: 9}
  TIGHT arms hitting the STARRED object r3     : 4 {1: 2, 2: 2}
  settle EXECUTED / RAISED                     : 0 / 0
  TIGHT arms where audit_fixpoint RAISED       : 18
```

In 2 of the 4 star-tight arms the row is **present-and-starred when correct and ABSENT when
stale**, and the loss propagates one relation further (`('doc','access','d2')` `stars` →
`[]`). **So for the starred case the divergence is carried in the residue too, not only in
closure edges.** Nothing catches it: the settle pass never executed, and `off`/`residue`/
`full` all returned `err=none` — with the tier read back off the installed guard, and with
a sabotage (a planted dead node id in that *same* `authorized_user` residue row) proving
`residue` and `full` **can** go red there. The tier green is real, not a blind instrument.

⚠ **One arm diverges FAIL-OPEN** — `graph=True, oracle=False` on three
`user_missing_requirement c4` queries, alongside five fail-closed. Recorded explicitly
because a fail-open in an authorization index is the direction that matters.

**This is NOT a live correctness bug and the board's "0" stays 0.** It needs both a
constructed fixture that exists nowhere in the tree and a deliberate fault injection. It is
an assurance-coverage gap of exactly `TK74`'s class — but a *wider* one than §9.5 left on
record, because §9.5's "carried entirely in materialized closure edges" would have sent a
future session looking in the wrong place. **Filed as `TK83`** (add a star-admitting
intersection fixture to the tree, so the case stops being unreachable).

**Caveat, and it bounds the claim:** one constructed schema, one object, 4 star-tight arms,
2 of which show the diff (the other 2 have no residue on either side at that op prefix).
**Do not quote "the residue always differs".** That a *general* starred intersection
diverges is REASONED, not measured.

### 10.6 Item 6 — PostgreSQL: the result is BYTE-IDENTICAL, and the concurrency question gets a real answer

**Verdict: SAME.** Not "similar" — the two sweep logs differ only in the storage-name line
and the elapsed-time lines; all 170 arm result lines are identical, and a field-by-field
JSON diff of the per-arm records gives **0** differences (32 arms × 16 fields on `het`,
138 × 15 on `demorgans_law_2`). The settle pass's blindness is a property of
`_run_cascade`, not of the storage engine.

The PG leg was genuinely live, not silently falling back: `index_v4/core.py::is_sqlite`
returned `False` on every run, so `take_row_write_lock`'s real `FOR UPDATE` arm and
`_lock_store` were exercised. Sanity first, to the log-file recipe: `rc=0`,
`17 passed in 11.23s`.

**§9.2's non-vacuity instance reproduces on PG arm-for-arm and row-for-row:**

```
arms where the :1629 map saw >=1 outbox ROW : 3 / 32
arms where the :1629 map returned >=1 KEY   : 0 / 32
    (34, 3, rows=1, keys=0)  (35, 2, rows=3, keys=0)  (35, 3, rows=4, keys=0)
```

**The concurrency answer to §9.10 item 1 — the honest shape.** Two threads on the raw
graph path, with outbox rows attributed to their writing transaction by PostgreSQL's
`xmin` (server ground truth, not a heuristic):

```
_lock_store acquisitions                     : 800   ... that BLOCKED >5ms : 79  max wait=2.325s
IN-LOOP reads (:1574) that saw a FOREIGN row : 79
POST-LOOP reads (:1628) with a FOREIGN row   : 0
cascades with NON-EMPTY leftover             : 0
outbox rows=408 distinct writing txids=88 id-order block boundaries=87
```

**88 distinct writers, 87 boundaries ⇒ exactly 88 contiguous blocks, zero id interleaving.**
That is the structural reason the coincidence cannot fire for a lock-respecting writer: the
store lock is held from the first edge write through commit, so a competitor cannot allocate
an outbox id inside another's range. It survived a widened window (a 0.5s sleep injected
immediately before the `:1628` read, `fired 88 times`, wall clock +39s — so the sleep really
was inside the held critical section): still 0 foreign post-loop rows. The composed path
(`ConnectedStore`/`TupleSource`, 4 writers + a tailing replica) is **stricter still** —
in-loop foreign rows drop to 0, because `_lock_source` is taken before the watermark is read.

⚠ **But the mechanism is real for a writer that BYPASSES `_lock_store`**, and this is the
part worth carrying: a bare INSERT into `delta_outbox_v1` never touches `store_v4`, so it
does not block, and it lands above another cascade's final frontier **on the first try**.
Nothing in the shipped write paths does this — but an external outbox producer, a future
async worker (boolean spec §13), or any tool writing the outbox directly **would**, and it
would put a *foreign* key into someone else's `leftover`. So item 1's answer is:
**not observed from any lock-respecting writer in 128 concurrent op transactions across two
layers with a widened window; trivially producible by a lock-bypassing one.**

**The control is the strongest in this document** — a second PG session on a second
connection commits a *real* `DeltaOutboxV1` row timed between the last frontier snapshot and
the `:1628` read, so the real `_map_deltas_to_keys` maps a real committed row:

```
C-A  STALE  (reconcile suppressed, then foreign row forces leftover)
    settle.changed : [('group', 'member', 'g1')]      RAISED : True
    InvariantViolation: cascade failed to quiesce after 3 strata rounds; the settle pass
    CHANGED derived state at [('group', 'member', 'g1')] -- those keys were genuinely stale
C-B  FRESH  (no suppression, IDENTICAL foreign injection)
    settle.changed : []                                RAISED : False
```

C-A proves the instrument goes red on PG; **C-B proves the red is caused by the staleness
and not by the injection.** That is the control-your-instrument discipline done right.

### 10.7 ⚠ §9.1's `driven` COLUMN IS WRONG — the miscount recurred a FOURTH time, in the correction itself

The banner records that this count "was wrong three times the same way". **It is wrong a
fourth time, and this time it is wrong in the row that was written to fix it.**

**MEASURED first-hand by this session** from round 2's own artifact,
`.scratch/tk74c-isect/sweep_rows.json`:

```
rows                       : 138
later_consumer > 0         : 130          <- relation-level
later_consumer>0 AND div>0 : 130
settle_exec True           : 0
settle_raised True         : 0
leftover_n > 0             : 0
skipped_in_leftover True   : 0
```

* **`demorgans_law_2 driven = 54` is not reproducible from the artifact it came from.**
  The artifact yields **130** at relation level; the PG arm's strict object-level score
  yields **27**. Neither is 54. **UNRECONCILED** — recorded as a discrepancy rather than
  silently replaced, because guessing which is right is how the number got wrong the first
  three times.
* **`heterogeneous_tupleset driven = 4` is the RELATION-level count.** Its source
  (`.scratch/tk74c-het-sk/attack.py`, the "object-level DRIVEN check" block) filters on
  `(kk[0], kk[1]) in cons` only — no object match and no oracle-wrong conjunct, despite
  its own heading. The strict count is **2**. The two dropped arms are instructive: on
  `op=35 ord=3` the only oracle-wrong key is the *skipped key itself*, and on `op=35 ord=2`
  the wrong consumer (`doc.viewer.d1`) was never among the later-round reconciles.
* ⚠ **A trap that produced this, found first-hand:** every field in `sweep_rows.json` is
  stored as a **STRING**, so `'0'` is truthy and a naive count returns **138 for every
  column** — including `skipped_in_leftover`, which would read as "the net caught
  everything". Convert before counting, and sanity-check any column that comes back equal
  to the row count.

**The verdict does not move.** Every net column in that artifact is 0 on both backends, so
the blindness result stands exactly as §9.2 states it. What moves is the *size of the
evidence*: `~62 skeptic-confirmed driven arms` in §9.1 is a relation-level figure, and the
strict object-level number is substantially smaller. **Cite §9.1's `driven` column as
relation-level, or re-derive it.**

### 10.8 ⚠⚠ Items 1 and 4 — THE HEADLINE NEEDS A QUALIFIER, and §9.4's census verdict does not survive

This is the most consequential result of the round. Read it before citing §1, §9.2 or the
`TK74` close message.

#### Item 1 — REFUTED as stated. The settle pass DOES catch a skipped key, across cascades.

**Reproduced first-hand by this session** (`rc=0`), three arms on a 1-stratum schema:

```
### ARM A -- no skip (negative control)
   RAISED: no          oracle grid: 252 queries, divergences=0
### ARM B -- skip at op1 only; op4 is an UNRELATED write
   RAISED: [(4, "cascade failed to quiesce after 1 strata rounds; the settle pass CHANGED
            derived state at [('folder','owner','x')] -- those keys were genuinely stale")]
                       oracle grid: 252 queries, divergences=1
### ARM C -- same skip, script truncated BEFORE op4 (staleness control)
   RAISED: no          oracle grid: 252 queries, divergences=1
  ALL THREE ARMS MOVED AS PREDICTED = True
```

**Arm C is the load-bearing one**: the staleness is demonstrably present and the settle pass
does **not** see it. **Arm B**: the *same* staleness, plus one later unrelated write, and the
settle pass **raises**. Independently reproduced at 3 strata, where the raising key is the
downstream consumer `('box','b2','bx')` rather than the skipped key itself.

**So §9.2's law is mechanically intact and its CONCLUSION was overstated.** A later write is
a write; its rows map to the stale key; `leftover` gets it. What must be added everywhere the
claim appears is the scope qualifier:

> The settle pass is structurally incapable of detecting a skipped/stale reconcile **within
> the cascade that skipped it**. Across cascades it catches them **opportunistically**.

**How opportunistic — AGENT-MEASURED, and the numbers keep it in proportion:** of 2,179 skip
arms, the skipped key reached `leftover` in **8**; of those, **1** was a genuinely
staleness-creating skip, and that one **RAISED (1 of 1)**. A ~0.4% placement rate on a
fault-injected corpus is **not a net**, and `TK82` is still the answer — but "structurally
incapable at any schema shape" is no longer a true sentence and must not be repeated.

⚠ **The doc's named route is the WRONG one.** Branch (A) at `:1424` called from `:1629`
stayed at **0 non-empty across 866 calls** — an 11.9× widening of §9.3's 73, so §9.3's
number holds and grows. The hits arrive by the post-loop mapcall's **ordinary per-row
fan-out** and by the **`_bumped`** route (`:1630-1633`), not by branch (A). My own §10.0
reasoning — that branch (A) is the one non-written-key path — is therefore **correct about
branch (A) and wrong about where the risk lives**; recorded rather than quietly amended.

**And item 2's delete IS driven, closing §10.1's open end:** of 5,132 `_evict_node` calls,
**10** deleted a node under a live residue reference — **all 10 at `core.py:893`**, none at
either processor GC path (0 of 458 and 0 of 992, exactly as their guards predict). All 10
fired on the raw-write path before round 0 and were drained by the first in-loop mapcall.

#### Item 4 — the census REPRODUCES exactly, and its verdict still does not survive

**The instrument is sound** — the mandatory control passes on both instruments (the §9.4
witness reports `SETTLE_RAN=1`, its negative control `0`, `BOTH MOVED=True`). The `0` was a
real observation of **contaminated and under-powered** traffic:

| run | generator | multi-stratum cascades | `SETTLE_RAN` |
|---|---|---|---|
| prior probe, verbatim re-run | buggy | **2385** | **0** ✅ reproduces |
| independent instrument, 18 seeds | buggy | 7155 | **1** |
| same instrument, **deduped** generator | dedupe | 7156 | **5** |

**The §10.4 harness bug is confirmed to have contaminated it**: `habitat_census.py::sweep`
(`:91`) and `habitat_fuzz.py::sweep` both do `t = rng.choice(pool); op = 'add'` with **no
dedupe**. On the census's own traffic that put **34.4%** of ops on ref-count-inflated state
and left **87 of 198** seed runs oracle-dirty. **The fix changed the verdict: 1 → 5 at the
same N.**

**It is also diluted**, which is the more durable finding: only **6.7%** of budget≥3 cascades
ever enter their final budgeted round (the loop `break`s early), falling to 0.37% at budget 5.
A census of a pass that only runs in the final round is mostly counting cascades that never
reach it.

⚠ **Two framing corrections to §9.4, MEASURED:** the census covers **8 fixtures + 2
engineered schemas**, not "all 15 fixtures plus 3 engineered" (6 fixtures have no derived
relations, `owc_star_ttu` is 1-stratum and excluded, one engineered schema is
`UNSUPPORTED`). And the §9.4 witness is **not** `demorgans_reverse` (that fixture is 5
strata) — it is the engineered `E1` `folder`/`box` schema at budget 3.

**Consequence: `SETTLE_RAN = 0` must not be cited again from those two probes.** Any number
taken from `habitat_census.py` or `habitat_fuzz.py` is contaminated until their generator
dedupes. Filed as `TK84`.

### 10.9 §9.10 closed out — all seven items

| # | item | verdict | where |
|---|---|---|---|
| 1 | coincidental late emission places a skipped key in `leftover` | ⚠ **REFUTED as stated** — it happens (8/2179, the 1 genuinely-stale one raised). The *branch-(A)* route stays 0-of-866. Headline needs "within the skipping cascade". | §10.8 |
| 2 | the unguarded implicit-node delete (`TK80`) | **OBSERVED-AND-POSSIBLE.** Three branches not two; `:884` is the unguarded one; 10 of 5132 evictions ran under a live residue ref, all at `core.py:893`. Corrupts only via `remove_node` with no cascade. `TK80` stays `LATER`. | §10.1, §10.8 |
| 3 | a **starred** half-stale intersection | ⚠ **REFUTES §9.5.** The residue channel is not clean, it was unreachable. One token makes it reachable; the residue diverges and one query goes FAIL-OPEN. → `TK83` | §10.5 |
| 4 | `habitat`'s 2385-cascade census | **REPRODUCES, verdict does NOT survive.** Instrument sound; traffic contaminated and under-powered. `SETTLE_RAN` 0 → 1 (3× N) → 5 (deduped). → `TK84` | §10.8 |
| 5 | the tier's false-positive rate | **CLOSED. 0 of 2853**, control 43/43, sabotage 0/43. `TK82` unblocked. | §10.3 |
| 6 | PostgreSQL | **CLOSED — SAME.** Byte-identical arm logs; `_lock_store` genuinely serializing; the coincidence is structurally blocked for lock-respecting writers, trivially producible by a lock-bypassing one. | §10.6 |
| 7 | generated-schema sweep | **CLOSED BY SEARCH.** 588 schemas / 738 arms / 31,824 cascades / 0 hits, non-vacuous at both ends. Law tightened (dead `keys` param) and one clause narrowed. | §10.2 |

**What this round changed about the answer, in one paragraph.** `TK74`'s verdict survives:
the settle pass is the wrong net for this class, `audit_fixpoint` is the only real detector
and still has zero production callers, and `TK82`'s scheduled-union tier is the right fix —
now with a measured FP rate of zero and a sabotage that demonstrably ships dead. What
changed is the *strength* of two sentences that were written more confidently than the
evidence supported: "structurally incapable at **any** schema shape" needs **"within the
skipping cascade"**, and "the divergence is carried **entirely** in materialized closure
edges" is false once a star can reach an intersection. Both were found by pointing controls
at the claims rather than at the code.

**Next action:** implement `TK82` (`NOW`) against §10.3's constraints — the sabotage is
mandatory *and permanent*, because §10.3 proves no clean-traffic measurement can
distinguish the right design from the wrong one.
