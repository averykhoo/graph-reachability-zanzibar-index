# Adversarial bug audit — 2026-09-15

**ACTIVE-PLAN** (`docs/README.md` §3). Corrections are appended **dated at the top** of the
corrections section; FROZEN when the last item it tracks closes. This is the tracked home
for a `claude-fable-5` adversarial audit (user-requested) plus the top-level session's
first-hand reconciliation of it.

**2026-10-06 (`TK120`):** the code moved into the `src/zanzibar/` package and lost its version suffixes after this doc was written; its paths and class names are the OLD ones. Key: `docs/architecture/overview.md` § "Renamed in TK120".

**Provenance labels, and they matter more than usual here** because most of this document
is a subagent's output and `CLAUDE.md` § Delegation is explicit that a subagent report is
**evidence, not a finding**:

* **CONFIRMED** — the top-level session reproduced it first-hand, with a tracked probe.
* **AGENT-PROBED** — the audit agent ran a probe and reported literal output; the top-level
  session has **not** re-run it.
* **AGENT-READ** — the agent opened the code and reported what it saw; not re-verified.
* **REASONED** — inference, by either party. Nothing here is REASONED-only above item 3.

⚠ Every unlabelled claim in an earlier draft of this material was the agent's. Do not
promote anything below to a test, a gate pin, or `formal/history/` without re-verifying it
first-hand — that is the standing rule, and item 1's severity clause is a live example of
why (the agent's framing was wrong, see § *What the reconciliation changed*).

---

## 1. ★ CONFIRMED — the two backends disagree about which stores may exist

**Status: real, reproduced, unpinned. This is the only confirmed defect in the audit.**

**The divergence.** Four adds; the graph index refuses the fourth, both `SetOps` backends
accept it. Literal output, reproduced first-hand 2026-09-15 by
[`formal/probes/i14_admission_divergence_2026-09-15.py`](../formal/probes/i14_admission_divergence_2026-09-15.py)
(rc=0, full transcript in its header):

```
DIVERGES: add ('viewer','doc','d1','member','group','g')
          -> graph=False set:py=True set:roaring=True
```

**The mechanism** (AGENT-READ, mechanism re-derived first-hand from the probe's behaviour,
symbols grepped): write 4 closes a userset cycle — `doc:d1#viewer` → `group:g#member` →
`folder:*#viewer` → (wildcard parent + `viewer from parent`) → `doc:d1#viewer`. The graph
must refuse it (`index_v4` materialises a transitive closure; `Inv.acyclic` / I2 is
load-bearing). The set engine cannot see it: its cycle-check flow graph creates nodes per
incident **edge** (`setengine/engine.py::SetEngine._shape_node_ref`, reached from
`::SetEngine._flow_reaches` / `::SetEngine._would_cycle`), while the graph's entity middles
exist per **entity** (`index_v4/wildcard.py::WildcardIndex._ensure_entity_middles`). Entity
existence strictly contains flow-node existence, so the crossing is invisible to the set
engine's check.

**★ WHAT IT IS, precisely — and this is NOT what the audit reported.** The probe's part (C)
brings in the independent oracle, and the result reframes the finding:

```
oracle evaluates the 4-tuple store: YES
every backend matches the oracle ON THE STORE IT HOLDS
answer fork (graph vs set): 4 of 12 queries
```

* **It is NOT a ghost grant and NOT a wrong answer.** Zero of twelve grid queries has a
  backend disagreeing with the oracle's reading of the store that backend holds.
* **It IS an admission-contract divergence.** The two backends disagree about which stores
  may EXIST; after the disagreement they hold different data (3 tuples vs 4) and answer
  differently on 4 of 12 queries. Given identical write sequences, two deployments fork
  permanently. That is the project's primary goal (`CLAUDE.md` § Who decides) breaking at
  the **admission** layer rather than the evaluation layer.

**Which side is wrong is a CONTRACT DECISION, not a bug fix, and the probe does not make
it.** The spec defines a meaning for the cyclic store (least fixpoint — the cycle is unfed,
so it grants nothing), so the graph is the more restrictive side. But the graph's
restriction is structural. **Recommendation (REASONED):** align
`setengine/engine.py::SetEngine._would_cycle` to refuse the write — the smaller change, and
the one that preserves both backends' existing guarantees. Decide it on the row, not here.

**⚠ THE SEVERITY IS STILL UNMEASURED.** The audit reported this as a corruption-class error
with a possible permanently-wedged multi-instance cursor, via a `ValueError` →
`InvariantViolation` promotion in `connectedstore/apply.py::_apply_row`. That clause is
**AGENT-READ for the promotion and REASONED for the wedge**, and the top-level session has
verified **neither**. Nothing above depends on it. **The open question is what the composed
`ConnectedStore` does with the refusal** — if the log row commits and apply then fails
repeatedly, this is serious; if the write is cleanly rejected end to end, it is a contract
wart with an answer fork behind it. **Measure this before sizing the fix.**

**Owed:** the reproduction is a ready-made permanent test and nothing in the suite catches
it today.

---

## 2. AGENT-PROBED — `P22`'s `bulk_build` I14 loop is reachable, and the corpus is the pin

**Status: resolves a standing open item, pending first-hand re-verification.**

`P22` records a GREEN SABOTAGE: `index_v4/bulk_build.py`'s I14 crossable-middle loop is
guarded by `schema_info.crossable_shapes` and no test reaches it. The audit found an input
that does.

* **Claim (AGENT-PROBED):** with an `owc_star_ttu`-class schema plus
  `object_wildcard_shapes={('folder','viewer'),('doc','viewer')}` and three tuples
  (`u1 editor f1`; `u1 viewer folder:*`; `folder:* parent doc:d1`), query
  `check(u1, viewer, doc:d1)` gives `inc=True bulk=True oracle=True` on the shipped tree,
  and `SABOTAGE-RED: bulk_no_i14=False oracle=True` with the loop's guard neutered.
* **Why no existing corpus reaches it (AGENT-READ):** every entry of
  `tests/test_bulk_build.py::_CORPORA` has `crossable_shapes = ∅`, because
  `zanzibar_utils_v1.py::_reject_doubly_bridged_shapes` intersects only *literal* `T:*#p`
  shapes while star-tupleset *through-shapes* make the set non-empty on an admitted schema.
* **⚠ Also claimed (AGENT-READ, unverified):** `tests/test_zt_p5_readjudication.py` calls
  `check_invariants` without `schema_info`, which disables the I14 clause. If true that is a
  second silent hole and belongs on its own row.

**Owed:** re-run first-hand, then add the corpus entry to `_CORPORA` and close `P22`.

---

## 3. ★ SELF-REFUTED — batched-cascade under-invalidation. Recorded so it is not re-run

The audit's own opening hypothesis — `connectedstore/apply.py::advance_index` applies N log
rows then runs ONE `run_cascade(wm)`, so a later row could destroy state an earlier row's
fan-out needed — **came back negative under its own randomized sweep**: sync store vs async
store (whole sequence drained in one batch, and again at `batch=2`) vs `tests/oracle.py`,
over a negated-TTU + nested-group schema and a star-tupleset/derived-parent schema:

```
400 seeds x 2 batch modes ... failing trials: 0
150 seeds x 2 batch modes ... failing trials: 0
```

**CONFIRMED first-hand, the coverage half:** `ConnectedStore`, `catch_up` and `sync=False`
each appear **zero** times in `tests/parity.py` and in `tests/test_hypothesis.py` (grepped
2026-09-15). So no *randomized* harness reaches the batched schedule — it is exercised by
fixed scenarios only, in at least 12 modules (`tests/test_connectedstore_async.py`,
`::test_connectedstore_build.py`, `::test_connectedstore_multi_instance.py`,
`::test_connectedstore_concurrency.py`, `tests/test_bulk_build.py`, and others).

⚠ **An earlier form of this claim said the batched path was "structurally under-tested",
which is FALSE as stated** and was corrected before it reached this document. The defensible
claim is the narrow one above: *no randomized harness reaches it*.

**The formal gap is separately real and already ledgered** (`formal/CORRESPONDENCE.md` §6:
only the interleaved schedule is modelled). **Cheap residual (REASONED):** promote the
agent's sweep to a hypothesis stateful machine over `ConnectedStore(sync=False)` — that
closes the randomized-coverage hole permanently rather than for 700 trials.

---

## 4. UNVERIFIED LEADS — assurance gaps, none with a demonstrated live defect

Filed together because they share a shape: *nothing is watching this*, rather than *this is
broken*. All are AGENT-READ unless noted. Each needs first-hand verification before it earns
a row of its own.

| # | Claim | Where (agent's citations — **grep before use**) | Severity if real |
|---|---|---|---|
| 4a | No exact-count oracle anywhere on the REMOVE path: an inflated `indirect_edge_count` survives every pin until the last genuine path is revoked. Agent audited the arithmetic itself **clean**; this is an instrument gap | `index_v4/core.py::_remove_edge_locked`, `::_add_indirect_edges_batch_unsafe`; only exact-count oracle is `tests/test_bulk_build.py::_edges_proj` vs the closed-form DP, and `bulk_build` is **add-only** | ghost grant (deferred detection) |
| 4b | `ClosureFanoutExceeded` leaves flushed nodes + bridge edges behind through the COMPOSED write path; the "leaves the transaction as it found it" claim holds for the raw index only | `index_v4/wildcard.py::WildcardIndex._add_tuple_trusted` vs `index_v4/core.py`'s claim site; pin gap in `tests/test_reg17_closure_fanout_cap.py::test_rejection_leaves_no_partial_state` (pre-creates endpoints) | state corruption for direct `index_v4` consumers; benign through `ConnectedStore` (which rolls back) |
| 4c | `_maybe_remove_bridges` safety rests on an unasserted three-file conjunction; weakening any clause re-opens the BL-1 dangling-`neg` class (reads as *not excluded* ⇒ DENY→GRANT) | `index_v4/wildcard.py::WildcardIndex._maybe_remove_bridges`; `index_v4/processor.py` reconcile step 2d; `zanzibar_utils_v1.py::_reject_object_wildcard_scope` | latent ghost grant |
| 4d | `formal/conformance/test_conformance_enum.py` has no non-vacuity floor on surviving-store counts, so an admission OVER-REJECT silently shrinks the enumerated space and the suite stays green. **Note the coupling: this is the check that would have to catch a bad fix to item 1** | `formal/conformance/test_conformance_enum.py` (no `MIN_*` assertion — agent grepped) | assurance-only |
| 4e | `_add_indirect_edges_batch_unsafe` dropped the self-edge/trivial-cycle stop its per-pair predecessor raises, despite a docstring claiming it reproduces that writer "EXACTLY" | `index_v4/core.py::_add_indirect_edges_batch_unsafe` vs `::_add_db_edges_unsafe` | benign today; reachable only downstream of separate corruption |

**Dropped from the audit's ranking, correctly:** `P23` (declared-name charset asymmetry) —
real, but already filed with a decided fix shape, so not a new finding.

---

## What the reconciliation changed

Recorded because it is the argument for the standing rule, not a complaint about the agent:

1. **Item 1's severity was wrong as reported** — "corruption-class error / wedged cursor"
   became "admission-contract divergence, no wrong answers", once the oracle was brought in.
   The agent compared the two backends to each other and never asked the referee.
2. **Item 3's coverage claim was too strong** and was corrected before landing (12 modules do
   drive the batched path; what is missing is *randomized* coverage).
3. **The agent's probes were written to `.scratch/`**, which `CLAUDE.md` says is the same as
   not recording them. Item 1's is transcribed to `formal/probes/`; **items 2 and 3's are
   still only in `.scratch/` and will be lost.**

## Still owed

* **Measure item 1's severity through `ConnectedStore`** — the one open question that changes
  its priority. Do this first.
* **Write item 1's reproduction as a permanent test.** Confirmed equivalence break, unpinned.
* **Re-verify item 2 first-hand**, add the `_CORPORA` entry, close `P22`.
* **Transcribe the item-2 and item-3 probes out of `.scratch/`** before they are lost.
* Decide the item-1 contract (`_would_cycle` narrowing vs graph widening) on the task row,
  per `CLAUDE.md` § Who decides.
