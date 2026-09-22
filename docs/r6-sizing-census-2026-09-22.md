# `R6` — what is actually worth working on: corrected figures, correctness expectations, and the Lean audit

**ACTIVE-PLAN, opened 2026-09-22 — the body is provenance, not a living status.** Produced to
answer two questions for every open `R6` child: *is the headline figure real?* and *what does
the change cost the Lean model — does it break it, and could it SIMPLIFY it?* Every figure is
as-of 2026-09-22. Live state is `python scripts/task.py show R6` and
`python scripts/gate_status.py` — never this file. Corrections append **dated at the top**.
Freeze it when `R6` closes.

Provenance labels: **[M]** MEASURED by this session (probe named, literal output quoted),
**[R]** first-hand READ by this session, **[A-R]** subagent-read and re-verified here,
**[A-X]** subagent reasoning, NOT re-verified, **[U]** unverified. A subagent report is
evidence, not a finding (`CLAUDE.md` § Delegation); **[A-X]** rows still owe verification.

⚠ **Four of the ten open rows describe a surface or a number the code does not have.** Three
were found by re-verifying a subagent census first-hand, one by measurement. None is a defect
in shipped behaviour; all four would mis-steer a session that sized work off the row.

## Verdict table — what is worth working on

Ranked by *honest* value, not by headline percentage.

| id | headline says | honest value | Lean | worth it? |
|---|---|---|---|---|
| `R6-8` | 11.0% paranoid build | 11.0%, gate wall-clock only | **zero anchors** [M] | **Yes — cheapest real win** |
| `R6-7` | 20.7% paranoid build | 20.7%, gate wall-clock only; removes the growth term | §7 log, no def edit | **Yes, but** co-design trap |
| `R6-11` | ~4x scope churn | mechanism, not a win; unmeasured | none (caching unmodelled) | **Yes — cheapest clean landing** |
| `R6-18` | 53.1% smaller table | real, and already instrumented | anchored, no def edit | **Yes, if** the PG migration is accepted |
| `R6-4` | 30.1% + 193 json.loads | **real and undercounted** — see below | modelled; §7 or def edit | **Yes — best true win** |
| `R6-9` | 4.51 SELECTs / 17.7% | **measures SELECTs the fix does not delete** | no anchors | Marginal — fix the instrument first |
| `R6-5` | 32.7% ORM construction | **26.8% of it is R6-4's** [M] → ~23.9 pts | unmodelled (§7.3) | Yes, but split the design |
| `R6-16` | 1.00 row/edge | real; **drags R6-7+R6-8 in** | **modelled — and a SIMPLIFICATION candidate** | Only as the triple |
| `R6-19` | cum 25.4% / self 2.0% | **MEASURED 2026-09-22b: 27.9% soundly memoizable, ~7% of a bulk build** | none (bulk unmodelled) | **Yes -- and it SURVIVES** |
| `R6-1` | 91.4% of lookup | ceiling, not a win; **fix refuted** | anchored closures; §7 owed | No — needs a measurement session first |

## The measured correction: `R6-5`'s 32.7% is not `R6-5`'s

**[M]** Probe: `benchmarks/probe_r6_instance_by_class.py` (2026-09-22), same workload as
the 2026-08-17 pass (demorgans_law_2, scale 40, 60 lookups, 980 raw tuples, 100 residue rows).
It registers a SQLAlchemy `InstanceEvents.load` counter per mapped class, so every ORM
construction is attributed to the entity it built.

```
ORM instances materialised during the 60 lookups: 22,410

by mapped class:
     8,280  ( 36.9%)  NodeV4           <- R6-5
     8,130  ( 36.3%)  EdgeV4           <- R6-5
     6,000  ( 26.8%)  ResidueV1        <- R6-4

R6-4 (residue rows)     : 6,000  (26.8% of ORM constructions)
R6-5 (node/edge rows)   : 16,410  (73.2% of ORM constructions)
unattributed            : 0
```

**The instrument controls itself**: the deduped total is **exactly 22,410**, reconciling to the
independently-recorded profile line `22410 ... sqlalchemy/orm/loading.py:1068(_instance)` in
`benchmarks/results/R6_PROFILE_2026-08-17.md`. A split that did not reconcile would not be
quotable.

⚠ **The first run of that probe was wrong and said so.** `dir(index_v4.models)` exposes
`NodeV4`, `EdgeV4` and `StoreV4` under two names each, so it registered two `load` listeners on
each and reported **38,820** constructions against the profile's 22,410. The disagreement with
an existing figure is what exposed it; the fix (dedupe by class identity) is commented in the
probe. *Control your instrument as well as your subject* —
`docs/sabotage-procedure.md` § "A MEASUREMENT is an assurance step too".

**Consequences for the two rows:**

* `R6-5`'s true share of that block is `73.2% x 32.7%` ≈ **23.9 percentage points**, not 32.7.
* `R6-4` is **undercounted**, not overcounted. The 6,000 `ResidueV1` constructions happen
  *inside* `_collect_residue_memberships`, so they are already within its 30.1% cum — but the
  profile then attributes them a second time to `R6-5`. The two headline numbers **overlap by
  ~8.8 percentage points**; they cannot be added.
* This is the `R6-10`/`R6-19` decomposition trap recurring, on the two rows the audit's own
  traps section did not cover. **`R6-4` is the better true win of the pair.**

## Correction appended 2026-09-22b — `R6-19` was measured and it SURVIVES

The user asked for `R6-19` to be closed if I was confident it was no good. Step (1) — the
duplicate-evaluation rate this row has owed since 2026-08-18 — was cheap to run, and it
**reversed the verdict**, so the row stays open. Probe:
`benchmarks/probe_r6_19_dup_eval.py` (tracked), demorgans_law_2 bulk build at scale 40.

```
total plan.check_fn evaluations : 5,168
distinct (plan, key) pairs      : 340
redundant evaluations           : 4,828 (93.4% of all evaluations)
pairs whose ANSWER CHANGED      : 80
_reconcile calls observed       : 140
evaluations OUTSIDE a _reconcile: 0 (0.0%)
redundant WITHIN one _reconcile : 1,440 (27.9%)   <- memoizable
redundant ACROSS _reconcile     : 3,388 (65.6%)   <- fixpoint re-asking, NOT memoizable
```

* **The row's own decline condition is not met.** It says *"if it is near zero on real corpora
  the item is finished, declined"*. 93.4% is not near zero, and neither is the sound part,
  27.9%. Against the call site's 25.4% cum that is **~7% of a bulk build — above the 5.0%
  ceiling at which `R6-14` was declined**, so the round's own standard does not retire it.
* **The trap's soundness worry is now evidence, not suspicion.** 80 of 340 pairs flip
  `False → True` within one build, so a `(subject) → bool` memo held ACROSS `_reconcile` calls
  would serve a stale answer — step (3)'s cross-call form is **refuted empirically**, and that
  is exactly the 65.6%. Only the intra-reconcile memo survives, and it still owes the
  interleaved-write argument, because `_reconcile_subject_edge` mutates and stores residues
  within one reconcile too.
* ⚠ **Instrument control, and a corpus limit.** `_reconcile_subject_edge` is also called from
  the edge-apply path (`bulk_backfill.py:801`) outside any `_reconcile`; bucketing those with
  the previous reconcile would have **invented** memoizable duplicates. The probe gives each
  such evaluation its own scope id so it can never pair. On this corpus that count is **0** —
  the workload does not exercise that path, so the split is honest here but is **not** proof
  the path never fires. Widening the corpus is the obvious next refinement.

**Net:** step (1) discharged, step (3)'s cross-call form refuted, and the item now has a
measured basis it has never had since it was self-filed. Remaining scope is narrower and
better defined: an intra-reconcile memo worth ≤ 27.9% of evaluations, owing the
interleaved-write argument.

## The Lean audit

Method: every edit-surface symbol for every open id, grepped against `formal/CORRESPONDENCE.md`
[M, mechanical census 2026-09-22]. Anchor count 0 means the gate's symbol-anchor resolver
(`verify.sh lean`) does not see the symbol at all.

| id | anchored symbols | breaks the model? | owed |
|---|---|---|---|
| `R6-8` | `verify_outbox_deltas` **0**, `bfs_reaches` **0** | **No — invisible to Lean** | nothing |
| `R6-9` | `_load_nodes` **0**, `_db_node` **0**; `_add_direct_edge_unsafe_impl` 1 | No — below the abstraction level | nothing |
| `R6-19` | `_reconcile_subject_edge` **0** | No — bulk path unmodelled | nothing |
| `R6-11` | `run_cascade` 10, `_residue_cache_scope` 1, `_store_residue` 4 | No — caching is explicitly not modelled | doc: TWO→THREE |
| `R6-7` | `_check_outbox_sanity` 1, `check_invariants` 1 | No def edit — but it scopes a modelled **predicate** | §7 divergence log |
| `R6-5` | `lookup_reachable` 3, `lookup_reverse` 6, `_classify_ids` 1 | No — §7.3 unmodelled surface | fuzz sweep (risk, not rule) |
| `R6-18` | `EdgeV4` 9, `_check_internal` 9, `bulk_build` 9 | No def edit — representation only | ten-phase gate + fuzz |
| `R6-1` | `SetEngine.check` + `.sat` closures; `_instances_of_type` **0** | No def edit **if** standalone answers preserved | §7 entry; do not rename closures |
| `R6-4` | `_collect_residue_memberships` 1, `_store_residue` 4, `_sync_residue_refs` 1 | **Yes** (finder); verifier says no *proof* change | §8.1/§7 log + sabotage |
| `R6-16` | `_emit` 6, `_flush_outbox` 1, `DeltaOutboxV1` 2, `drain_deltas` 2 | **Yes — genuinely modelled** | see below |

**The precedent for adjudicating a perf change against this model is already in §7** [R]: the
P2 batching entry reasons that `DirectGraph` is a pure `V → V → Nat` "with no notion of a DB
round-trip to restructure", and that the outbox model is preserved because the loops enumerate
**distinct** pairs, so each pair flips at most once and the batch emits the same action per
pair in the same order. Verdict: *"Below the model's abstraction level; no Lean change."* Any
`R6` id that only changes *how* rows are fetched or written, without changing which flips
occur or their order, inherits that reasoning.

### ★ `R6-16` could SIMPLIFY the Lean model, not just complicate it

This is the one place where the answer to "does it break the model" is genuinely interesting,
and it has not been asked before in this round.

* **[R] What is modelled.** `CORRESPONDENCE.md:317` maps `_emit`/`_flush_outbox` to
  `GraphIndex/Cascade.lean::GraphState.writeLoggedOne` / `::removeLoggedOne` /
  `::writeLoggedRules` — "routed write + **delta row per accepted flip**", unconditionally.
  `:327` maps `DeltaOutboxV1` + `outbox_watermark`/`drain_deltas` to `::nextDeltaId` /
  `::pushDelta` / `::maxOutboxId`. So emission *is* in the model; the audit's "conditional
  emission changes the modeled write algorithm" is correct.
* **[R] But the exact predicate R6-16 needs already exists in the fragment.** The verifier
  requires the gate derive from "durable store-level facts (schema boolean-ness)". Lean's
  `GraphIndex/LeafRules.lean::writeRulesRaw_untaintedSchema` is stated at precisely that
  hypothesis:

  ```lean
  theorem writeRulesRaw_untaintedSchema {σ : GraphState} {S : Schema} {t : Tuple}
      (h : ∀ d ∈ S.defs, isDerived S d.1 = false) :
      σ.writeRulesRaw S t
        = (rewriteClosure S t).foldl (fun acc u => acc.writeBridgedOne u) σ
  ```

  `∀ d ∈ S.defs, isDerived S d.1 = false` **is** "the schema has no boolean consumer". The
  fragment can already *say* R6-16's gating condition, and this theorem is the worked pattern
  for collapsing a write path under it.
* **[X] The simplification candidate, stated as a hypothesis to test, not a finding.** If
  emission is gated on untainted-ness, then on an untainted schema the logged and unlogged
  write paths should become provably equal — the `writeLoggedRules` / `writeRulesRaw`
  distinction *collapses*, exactly as `writeRulesRaw_untaintedSchema` collapses
  `writeRulesRaw` into `writeRules`. That would retire a branch of reasoning for pure-union
  stores rather than adding one. **This is REASONED from the two statements above and has not
  been attempted in Lean.** It is the single most valuable thing to try in this round, because
  it converts R6-16's Lean cost from a debit into a possible credit.
* ⚠ **It still cannot be taken alone.** Verified verbatim on the row
  (`tasks/R6-16-*.md:29`): *"**Take all three in one session, or take none of them.**"*
  Reason confirmed first-hand: `ParanoiaGuard.before_commit` calls `verify_outbox_deltas` at
  FULL tier on **all** schemas, so gating emission without gating that consumer makes the
  verifier silently vacuous — the house failure mode. `docs/tasktool-trial-protocol.md:287`
  records the dependency edge added to harden it.

## Rows whose prose does not match the code

All four verified first-hand this session. Each is written back onto its row.

1. ⚠ **`R6-9`'s instrument is mis-keyed, so the fix cannot move its own headline number**
   [R]. `benchmarks/profile_r6_write.py:198` keys the verdict on
   `_find(rows, func='_db_node', file_frag='index_v4/core.py')` and prints
   `_db_node point SELECTs ... <- R6-9`. But `index_v4/core.py::ReachabilityIndex._db_node`
   (`:965`) resolves by `(predicate, entity_type, entity_name, wildcard)`, while the two
   SELECTs R6-9 deletes are an **inline** `select(NodeV4).where(NodeV4.store_id ==
   ...).where(NodeV4.id == node_id)` in the write tail (`core.py:886-888`, dated). The
   per-table `node_v4` counter is what will drop ~2/write. **Re-key the instrument before
   landing**, and treat that as a gated step — it would be this round's fourth instrument
   correction.
2. ⚠ **`R6-16` names one symbol and has six call sites** [R]. The row and the audit index
   name `core.py::ReachabilityIndex._add_db_edges_unsafe`. `grep -n "self\._emit(" index_v4/core.py`
   returns **six**: `:550/:578/:600` inside `_add_db_edges_unsafe` (`:506`) and
   `:664/:676/:696` inside `::ReachabilityIndex._add_indirect_edges_batch_unsafe` (`:602`),
   which the row does not mention. The row describes **half** its own surface.
3. ⚠ **`R6-19`'s cheapest sub-step is not argument-free** [R]. The row calls the
   `_residue_state` hoist a no-op needing "no soundness argument at all".
   `index_v4/bulk_backfill.py::_BulkBackfill._residue_state` (`:390`) returns **fresh copies**,
   and the loop body mutates and writes back — `(neg.add if want_neg else neg.discard)(skey)`
   then `self._store_residue(...)` at `:706-707`. Today each subject reads a snapshot including
   the previous subject's committed change; hoisting shares one mutable set across the loop.
   It may well be equivalent, but that is an argument, not a no-op.
4. ⚠ **`R6-11`'s owed doc edit is already done** [R]. The audit says `CORRESPONDENCE.md`
   line 339 describes `run_cascade` as "a thin `_node_cache_scope()` wrapper" and must be
   updated to mention the second scope. `R6-10` already landed that: `:355` and `:370` both
   read **"TWO perf caches"**. The real edit is **TWO → THREE, in two places**. Separately the
   audit's fix sketch names `_run_cascade`; the scope install site is
   `::DeltaProcessor.run_cascade` [A-R].

## Session budget — how much of this fits in one sitting

* **The gate is ~31 min across ten commands** [M]: summed from `.gate-runs/ledger.tsv`, the
  complete 2026-09-22 pass ran `46 + 177 + 187 + 126 + 134 + 257 + 272 + 195 + 188 + 197` =
  **1779 s**. One phase per command; it must run *after* the write-back, since `t2c` covers
  `tasks/*.md` and `HANDOFF.md`. In practice: **one full gate per session.**
* **`R6-6` is the calibration and it is declared `size: S`** [R]. It took the whole 2026-08-24d
  session: 28 files, ~1,400 insertions, eight sabotages, a fixture rewritten because its pin
  came back *green* under the sabotage it exists for, an orphaned `WildcardIndex._w_id` deleted
  with its docstring rehomed onto `_w_node`, and a correction to the instrument. It still
  closed owing nine tile verdicts. **`S` here has meant "one full session".**
* **Therefore: one id end-to-end, or two only if they are `R6-11` + `R6-9`** (disjoint cones —
  cascade scope install vs. raw-write tail — both behaviour-preserving, no Lean change, no
  migration, both with a live benchmark target).

**Sizes that are wrong on the rows** [A-R]: `R6-5` and `R6-8` and `R6-19` carry `size: ?`,
which is an unset field, not a measured size. On surface evidence `R6-8` is an **S** (2 symbols,
one file, ~47 lines, two ready-made sabotage pins) and is smaller than `R6-7`.

## The structural fact that dominates all of it

**`R6-16`, `R6-7` and `R6-8` are one unit, not three rows** — ~16 symbols across three modules.
A session picking "two small ones" off the tail will pick `R6-7` and `R6-8` and unknowingly
take on `R6-16`, or will violate the co-design trap. If a solo `R6-7`/`R6-8` win is wanted, the
triple must be broken by an explicit recorded decision first.

## Still unverified — what a next session owes

* **[A-X]** `R6-5`'s stale audit call-site line numbers (symbols resolve, numbers do not).
* **[A-X]** `R6-1`'s third `self.check(...)` site in `setengine/engine.py` (subagent grep says
  `:1544/:1599/:1624`; the row names two). Re-grep before sizing.
* **[A-X]** `R6-18`'s row pointing at `WildcardIndex.check` when the probe is in
  `::WildcardIndex._check_internal`.
* **[X]** the `R6-16` Lean-simplification hypothesis above — the highest-value experiment in
  the round.

## Process note — the persistence rule cannot be satisfied by a read-only agent

Both census subagents were instructed to write `.scratch/r6-sizing/<agent>.md` incrementally
before returning. **Neither could**: both run strictly read-only with no write tool and blocked
shell redirection, so each reported in-message only. Had either turn been lost, that census
would have gone with it — the exact failure `CLAUDE.md` § Delegation added the rule for. **A
read-only agent profile cannot satisfy a persist-before-return instruction.** Either dispatch
an agent that can write, or make the orchestrating session the persister and write on receipt,
as was done here.
