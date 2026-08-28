# docs/latent-gaps.md — what is still latent

**LIVING** — every statement here is claimed true today. This file has **replace
semantics** (`docs/README.md` §6): when a gap closes, its section is **deleted**, not
struck through and not annotated with a date. What was found on a date is the ledger's
job, never this file's.

## The boundary — which half owns what

Split out of [`spec-deviations.md`](spec-deviations.md) on 2026-08-20 (board row `HS-2`)
because one file was answering two questions with opposite update rules:

| question | home | semantics |
|---|---|---|
| "what diverged, when and why" | [`spec-deviations.md`](spec-deviations.md) | dated, **append-only**; an entry is true *as of its date* and is never rewritten |
| "what is still latent **today**" | this file | **rewritten in place**; a row carries no date, only a back-pointer to the entry that filed it |

**A dated ledger entry cannot carry live status, and that is the whole defect this split
fixes.** The ledger holds three blocks whose own words are "NOT FIXED here" / "still
unbenchmarked"; all three were fixed later. Two had a correction appended; the third
(`ZT-P5`'s star-subject/star-object divergence) read as open for over three weeks after
`WildcardIndex._reject_star_self_edge` closed it the same day it was filed. So: the ledger
records the finding, this file records whether it is still true, and the two never restate
each other.

⚠ **Ranking is not here.** Priority and size live on the [`HANDOFF.md`](../HANDOFF.md)
board and nowhere else (`docs/README.md` §1); each section below names its board row id so
the two can be joined, and states no `NOW`/`NEXT`/`HOLD` word of its own. A gap with no
board row is one nobody has queued — that is a fact about the board, not a licence to
chase it.

**Entering a gap here.** It must be (a) still true today, verified — not inferred from the
ledger's tense, and (b) named precisely enough that a completion criterion exists. "Filed
not fixed" language in a dated entry is *evidence about that day*, not an entry ticket:
check the code and the pins first. The "Closed" list at the bottom exists because that
check has been skipped before.

---

## Open

**Standing decision on `LT-1` (Target 2 and Target 3), taken 2026-07-26 and unchanged:
do not chase them speculatively — act if a real schema or corpus surfaces one.** This is
the explicit recorded decision the board's `HOLD` points at (`docs/README.md` §4); it
moved here with the rest of the disposition on 2026-08-20. It is a trigger condition, not
a ranking — the ranking is the board's.

### Target 2 — the from-chain TARGET note's *misbehaviour* half

**Key note:** `Target 2` is a stable citation key (`docs/README.md` §5). It is cited by
the board row `LT-1` and by name from `docs/history/handoff-status-2026-07.md`; it moved
files on 2026-08-20 and must keep the name.

**Filed by:** [`spec-deviations.md`](spec-deviations.md) `## 2026-07-26 — ZT-P5` §"Target 2"
(the origin note is the `## 2026-07-13 — graph derived-TTU userset subjects (X4 + X2 fixed)`
entry, X4 §1).
**Board row:** `LT-1`.

The note's *reachability* half is **disproved and closed** — the excluded shape (an
untainted, subject-wildcard-bridged from-chain TARGET with grants already in its `w_any`)
IS reachable, pinned executably by
`tests/test_zt_p5_readjudication.py::test_zt_p5_from_chain_target_shape_IS_reachable`.
What stays open is the *misbehaviour* half: no misbehaviour was observed, and the reason
offered for that is **a hypothesis, not a proof** — that the grant which seeds the `w_any`
is itself a wildcard-userset grant, so the shape is already in the granting relation's
residue `stars` and a later concrete of that shape needs no new recording.

**Bounds of the evidence, stated so it is not over-quoted:** 400 randomized trials varying
the grant relation's operators (`but not` / `and` / `or` / nested), the TTU's operators and
the write order; 88 of them reached a FRESH untainted+bridged from-chain intern; 0
admission divergences, 0 answer divergences vs the oracle, 0 invariant violations, 0
`audit_fixpoint` failures, clean on 3 seeds.

**What would close it:** a bounded search over **more than two strata** *and* over
**intersection-rooted grant relations**. The 400-trial sweep covered neither, so the
hypothesis is unestablished exactly where it is least obvious.

### Target 3 — the object-wildcard corpus at STATE level, Lean side

**Key note:** `Target 3` is a stable citation key. It is cited by the board row `LT-1`, by
`tests/test_owc_star_parent_cross.py`'s module docstring, and by name from
`docs/history/handoff-status-2026-07.md`; it moved files on 2026-08-20 and must keep the
name.

**Filed by:** [`spec-deviations.md`](spec-deviations.md) `## 2026-07-26 — ZT-P5` §"Target 3".
**Board row:** `LT-1`.

`formal/FINAL_REVIEW.md` §3 and `formal/ARCHITECTURE.md` §6 infer *"the fragment exclusions
are proof-scope, not observed divergence"*. The Python side of that inference is settled
(clean, bounded: live == `build_index(bulk=False)` == `build_index(bulk=True)` exhaustively
to K=2 over the `object_wildcard` corpus and an object-wildcard TTU corpus, order
independence pinned, 160 randomized trials over `tests/fga_schemas/owc_star_ttu.fga` with
0 problems — pins in `tests/test_zt_p5_readjudication.py::test_zt_p5_object_wildcard_state_level_live_equals_rebuild`
and `::test_zt_p5_object_wildcard_state_is_order_independent`). **The Lean side has never
been run.**

**What would close it:** point the state extractor used by
`formal/conformance/test_conformance_state.py` at the `object_wildcard` corpus. It is
currently excluded from `formal/conformance/corpus.py::GRAPH_FRAGMENT` for a stated
proof-scope reason (`BareStarStore`
requires concrete stored objects), so the exact edge+residue equality comparison has never
been made there. Until it runs, §3/§6 must be read as *"no Python-side state divergence
observed (bounded)"*, not as *"no state divergence"*.

⚠ **Do not re-derive comfort from the inference class itself.** "Fragment exclusions are
proof-scope, not observed divergence", argued from check-level evidence, is the **exact**
inference that failed at state level on 2026-07-17. The check-level probe it rests on is
from 2026-07-12.

### ≥3-strata coverage of the LEAN cascade model

**Filed by:** [`spec-deviations.md`](spec-deviations.md) `## 2026-07-27b` §"Residuals — the
honest part" item 2. **Board row:** `P15` (the `twoStrata` cap half).

`runCascade2` is two literal nested applications — the round count is structural, not a
parameter — and `W4Fragment.twoStrata` is a hypothesis of `graph_correct`. Widening needs a
`runCascadeN` and a re-proof of the whole W3d-2 layer.

**Scope correction that travels with this row:** the original finding's framing ("the
≥3-stratum cascade path is tested by NOTHING") was **outdated when filed**. Python is not
ungated — `formal/conformance/test_conformance_nary_strata.py::test_multi_stratum_three_way`
drives the real cascade at 3 strata. The gap is
Lean-only, and quoting the wider version is how it gets re-filed as a Python coverage hole.

### The post-4c-ii headline statements need the `hql` leaf-name guard

**Filed by:** `formal/history/PROOF_STATUS.md` `## Session 2026-08-21b` (the finding's
Python twin — live bug `BL-2` — is FIXED; its record is
[`spec-deviations.md`](spec-deviations.md) `## 2026-08-21b` and is not this gap).
**Board row:** `P3`.

**Today's tree is unaffected — 4c-ii has not landed, so nothing is currently false.**
Machine-checked (two independent kernel `by decide` constructions): AFTER the 4c-ii
re-point, a pinned headline theorem stated over the UNFENCED `GraphModel.check` is
**FALSE AS WRITTEN**, not merely unproven, at queries whose relation is a minted leaf
name: the re-pointed driver's drained state grants where `sem` denies, with every
existing hypothesis inhabited.

**⚠ The blast radius SHRANK on 2026-08-28c and this entry used to overstate it.** It
named six theorems (`graph_correct`, `backend_equivalence`, `exclusion_effective`,
`no_ghost_grant`, `graphRun_check_eq_sem`, `graphRunOps_check_eq_sem`). Five of those,
plus `W4WitnessDirect.final_applies`/`final_applies4`, have since been migrated onto the
PUBLIC read `GraphModel.checkPublic` and are **no longer in the falsity set at all**:
their leaf-name case is discharged by the fence, via `FullScope.lean::graph_correct_public`,
whose fenced branch proves the query undeclared and appeals to `Spec/Confine.lean::semAux_undeclared`.
Post-4c-ii they stay TRUE and PROVED with no new binder — which is exactly the payoff
`2026-08-28b` predicted when it wrote "a migrated `final_applies` never gains an `hql`
binder".

**What is left is ONE row:** `Zanzibar.graph_correct` (`formal/headline_statements.txt:27`),
which is deliberately the INTERNAL-layer statement (`GraphModel.check` = Python's
`_check_internal`) and must stay unfenced — it is what `graph_correct_public`'s own
unfenced branch appeals to. `W4WitnessDirect.unfenced_grants` (`:51`) is likewise
deliberately unfenced: it is the FOIL for `fence_changes_answer`, and migrating it would
destroy the differential. The `Equiv.lean` per-stage ladder and the chain-internal
`correct_applies` / `w3d2E_correct_applies` are staged historical records of the internal
layer and stay on `check` for the same reason.

**What would close it:** the guard landing on `graph_correct` WITH 4c-ii in the same
commit — never before (today the statement is true unguarded) and never after (the gate
would meanwhile pin a false statement). The accept/refuse analysis is in PROOF_STATUS
`## Session 2026-08-21b`, and the guard was ACCEPTED by user call on 2026-08-28: the
narrowest repairing guard, `hql : publicOfLeaf S q.object.type q.relation = none`; refuse
`isLeafPred q.relation = false` (over-broad — schema-independent, and it also excludes
undeclared junk names where the claim holds today) and anything keyed on
`isDerived`/taint (it guts every derived-query headline claim while the pin regenerates
GREEN — the house failure mode).

---

## Latent, but owned by another doc

Listed so this file is a complete index of what is open, and pointed rather than restated
(`docs/README.md` §1). Do not copy their content here.

* **Derived-arm edge-multiplicity divergence in the Lean model** — Python does a presence
  diff on the reconcile fold where the model does not, so on the derived arm the model
  over-counts edge multiplicity. Home: `formal/CORRESPONDENCE.md` §7.2 item 6, which is
  headed **"Still open, deliberately"** and names both the faithful fix (a `¬ hasEdge`
  conjunct on `reconcileKeyDR`'s fold guard) and why it was not attempted. Filed by
  [`spec-deviations.md`](spec-deviations.md) `## 2026-07-29` §"Left open, deliberately",
  which also records the trap (**do not** instead make
  `formal/lean/ZanzibarProofs/GraphIndex/Write.lean::GraphState.admitEdge` reject a present
  edge — that breaks the untainted arm, which is load-bearing for `untOccCount`).
* **The 2026-08-09 entry's severity sign** — an explicit **prediction, not an
  observation**: the 2026-08-10 rule (a dropped TTU parent is a false NEGATIVE under a
  positive TTU and a false POSITIVE under a negated one) predicts the 2026-08-09 sibling's
  "fails closed" wording inverts too. It was never re-tested. Home: board row `P12`; the
  probe and its completion criterion are in [`spec-deviations.md`](spec-deviations.md)
  `## 2026-08-10` §"Severity: FAIL-OPEN, correcting the original filing".
* **Node GC and the node-flag lifecycle are unmodelled, and two named correctness bugs have
  landed inside that one region** — `ZT-P0-1` (the unsound `_keys_referencing` elision) and
  `BL-1` (the released-userset bridge leak, found by the hypothesis campaign). Home:
  `formal/CORRESPONDENCE.md` §7.3 (`:982-1003`), which records both. ⚠ **What the home does
  not say is what they imply.** §7.3 sits under §7 *"Known intentional divergences (model ≠
  code, by design)"* and its preamble reads *"None is a bug"* (`:862-863`), so the region
  reads as accepted — while the evidence that justified excluding it has moved. What is open
  is the **adjudication** (model it, or record that the differential + hypothesis nets are
  the intended net), not necessarily a model.
* **The per-subject cheap reconcile path is unmodelled and has twice gained real logic** —
  `index_v4/processor.py::DeltaProcessor.reconcile_subject` (body:
  `::DeltaProcessor._reconcile_subject`); Lean models only the full-object reconcile. Home:
  `formal/CORRESPONDENCE.md` §7.1 (`:476-493`), which itemizes both growths — promote-on-
  record (2026-07-17) and escalation to a full reconcile (2026-07-26, `ZT-P0-1`/`ZT-P0-2`).
  The justification that expired is the phrase *"a thin fast path"*
  (`formal/ARCHITECTURE.md:776`), but the disposition in both homes is still "unmodeled, by
  design", so nothing records the expiry as owed. Distinct from the node-GC bullet above —
  different code, different argument, filed apart on purpose; do not merge them.
* **Set-engine write admission is the gates' input filter, and is modelled only
  Python-vs-Python** — `setengine/engine.py::SetEngine._validate` steps (1) and (3), the
  latter via `::SetEngine._would_cycle` → `::SetEngine._flow_reaches`; only step (2) has a
  Lean counterpart and only as a premise. Home: `formal/CORRESPONDENCE.md` §7.3
  (`:950-961`), which already states the shrinkage risk and that nothing formal watches it.
  ⚠ Listed here for the part the home does not frame: this is **not** a check that can pass
  vacuously, it is the filter that decides how much there is to check — one level up from
  the usual shape. A non-vacuity floor on how many corpora survive admission, in the style
  of `anchor_check.py`'s `MIN_*` floors, may be worth more than a model and is a legitimate
  outcome.
* **`advance_index`'s docstring asserts the exact claim the model leaves unproved** —
  `connectedstore/apply.py:104-105` argues that batch size *"affects only latency/
  granularity, not the final materialized state or any semantic guarantee"*. Home:
  `formal/CORRESPONDENCE.md` §6 (`:393-424`), which owns the batched-schedule gap and
  already marks it open (*"nothing in the Lean tree quantifies over 'apply N ops, then one
  cascade'"*, `:420-424`). ⚠ Named here only for the collision, which neither end records:
  the home discusses `advance_index` and never mentions that the function's own docstring
  states the unproved claim as settled. **It is an argument, not a proof — do not cite it as
  one.**
* **The two compile-time scope rejections are deliberate, not gaps** — object wildcards on
  derived relations, and wildcard usersets over derived relations, both raising
  `zanzibar_utils_v1.py::UnsupportedByGraphIndex`. Stated in `CLAUDE.md`'s layout section;
  board row `SD-1` tracks lifting them. Named here only so a reader hunting a gap does not
  mistake a rejection for one.

---

## Closed — do not re-file from the ledger's tense

Each of these still *reads* as open somewhere in the dated ledger, because a ledger entry
is written in the present tense of its own day. They are closed. This list is the guard
rail; delete a bullet only when its ledger text can no longer be misread.

* **`ZT-P5`'s star-subject/star-object tupleset write divergence** (`folder:* parent
  folder:*`, accept/reject parity) — the 2026-07-26 entry says "**NOT FIXED here**
  (investigation scope)". It was **fixed the same day** by
  `index_v4/wildcard.py::WildcardIndex._reject_star_self_edge`; the strict xfail and its
  behaviour-of-today companion were flipped together into plain regression pins
  (`tests/test_zt_p5_readjudication.py::test_zt_p5_star_subject_star_object_tupleset_write_parity`,
  `::test_zt_p5_star_subject_star_object_fixed_behaviour_pinned`,
  `::test_zt_p5_starstar_fix_does_not_over_reject_the_legal_class`), and the generator
  blind spot is closed too (`::test_zt_p5_starstar_generator_blind_spot_is_closed`).
  `formal/verify.sh` asserts the live `tests/` xfail count against its declared
  `MAX_TESTS_XFAILED` budget, so a strict xfail surviving here would have to be declared
  there. The budget's VALUE lives only in `formal/verify.sh` — never quoted in prose
  (`CLAUDE.md`, standing footgun 3).
* **Target 1** (reg11's "the multi-hop out-bridge generalization is unreachable") —
  **disproved**, and the disproof is the closure: parity holds in the instance, and the
  bounded negative result behind it is executable
  (`tests/test_zt_p5_readjudication.py::test_zt_p5_bounded_search_object_wildcard_out_bridge_no_further_divergence`).
  Nothing is owed.
* **Target 4** (`group_userset` enum exclusion) — **confirmed correct**, exhaustively: 0
  per-write admission disagreements over all 299 stores, 0 order-dependent stores, 0 answer
  divergences. It was never a gap.
* **Target 5** (three orphaned `formal/history/` findings) — answered Python-side and
  pinned. The residue is Lean-side *modelling*, which is `formal/`'s own backlog, not a
  behavioural gap.
* **`Residuals` item 1 — "the cap does not stop the DoS that motivated it."** Adjudicated
  by [`spec-deviations.md`](spec-deviations.md) `## 2026-07-29c`: a store-level write quota
  was **DECLINED by the user**, "bulk rebuild instead" was measured and rejected on four
  independent blockers, and `ConnectedStore(sync=False)` is the accepted answer. Closed as
  a decision, not as a fix — do not re-open it as an unbuilt feature.
* **`Residuals` item 3** (zero coverage for wildcard usersets and the
  `derived-tupleset-ttu` leaf) — closed 2026-07-28; both are corpus'd or recorded as scope
  rejections. The ledger already strikes it through.
* **`Residuals` item 4** (`_any_residue_reference`'s complete `ResidueV1` scan, unbenchmarked
  and unconditional) — measured 2026-07-29b, **fixed 2026-08-14** by the `ResidueRefV1`
  reverse index. The new lookup is flat in R.
* **The untainted-arm `rewriteClosure` dedupe divergence** — the same `## 2026-07-29`
  §"Left open, deliberately" paragraph carries it in the present tense ("no corpus
  exercises it today", plus a count of agreeing untainted comparisons). Both clauses were
  retired on **2026-08-08**: the dedup landed, and two corpora (`reconvergent_diamond`,
  `reconvergent_derived`) now exercise the shape in
  `formal/conformance/corpus.py::GRAPH_FRAGMENT`. Evidence:
  `formal/CORRESPONDENCE.md` §7.2 item 6's "CLOSED 2026-08-08" note and
  `formal/lean/ZanzibarProofs/GraphIndex/RemoveOccCount.lean`'s header. Item 2 of that
  ledger entry has a dated ⚠ QUALIFIED blockquote; the "Left open" paragraph does not, so
  it is the one that reads open. It is the *derived*-arm divergence above that is still
  live — do not conflate the two arms.
