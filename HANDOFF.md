# HANDOFF — start here

The single entry point for a Claude Code (or human) session on this repo. Read
this **first**, then [`CLAUDE.md`](CLAUDE.md), then whatever the task points into.

- **`CLAUDE.md`** = the durable contract (how to run things, conventions, the
  gate, invariants). It rarely changes.
- **`HANDOFF.md`** (this file) = the mutable state: current status + the open-TODO
  board. **Keep it current** — when you pick up or finish work, edit the board
  below. This is the "one thing to point at" so instructions don't have to be
  relayed each session.

> The formal subtree has its own compact entry point,
> [`formal/HANDOFF.md`](formal/HANDOFF.md) — read that before touching anything
> under `formal/`. This file is the whole-project analog.

---

## ★★ START HERE (2026-08-11)

> # 🟢 THE GATE IS GREEN. The 2026-08-10 fail-open family is CLOSED.
>
> **RC2 is FIXED (2026-08-11); RC1 was fixed 2026-08-10 (`ed46e54`).** All ten gate phases
> plus the 6-seed fuzz sweep are green. The red banner that stood here is gone because the
> five tests it inventoried are green **with no test edit** — the stated completeness
> criterion. Measured at the commit that replaced this block:
>
> ```
> verify.sh lean            PASSED     493 audits, 38/38 statements, 155/155 defs,
>                                      432 anchors resolved, counts block exact
> verify.sh conf-tile:1..5  PASSED     99+99+99+99+98 = 494
> verify.sh tests-tile:1..4 PASSED     212+212+211+211 = 846
> fuzz --hypothesis-seed=   7 19 31 53 71 97   clean on test_hypothesis.py
>                                              and test_lookup_hypothesis.py
> ```
>
> *(tests figures re-measured 2026-08-11 after the real-world shape corpus landed:
> 823 → 846. The fuzz line is from the RC2 run and was NOT re-run — nothing since has
> changed an algorithm.)*
>
> The two seeds this file previously flagged as *extra* detonations — 53 and 97, where
> `TestParityMachine` independently found RC1 on a generator-assembled schema — are green.
>
> **Known live correctness bugs: 0.** If you see red, it is yours — `git stash` and
> re-check. Three standing footguns still apply and are still worth reading: a pytest exit
> code piped through `tail`/`tee` reports the PIPE's status (this bit the 2026-08-10
> session — a genuinely `4 failed` run was reported exit 0); `HYPOTHESIS_SEED=N` does
> nothing, only `--hypothesis-seed=N` works; and `MAX_TESTS_XFAILED=0`, so a divergence
> gets a positive pin, never an xfail.

### What landed 2026-08-11 (this session)

**(1) RC2 — the last root cause of the 2026-08-10 fail-open family.** A stored `T:*`
tupleset parent was dropped on the derived read path. The `n.wildcard == ''` clause was
**not** deleted — both recorded dead ends were re-confirmed first. Instead the two subject
shapes are split (`_stored_tupleset_subjects`) and the star one gets the semantics the
oracle and both set engines have always implemented: the shape `(T, target_rel)`
unconditionally (into the residue's `stars`), **plus** an ∃-expansion over tuple-mentioned
instances of `T`, folded into `tupleset_parents` so every downstream consumer
(`_from_chain_keys`, `_leaf_concretes`, `_derived_leaf_neg_ids`) became correct with no
edit. Fixed at BOTH sites — `processor.py` and `bulk_backfill.py` — which RC2 genuinely
needed, unlike RC1.

⚠ **Scope note — one clause was left alone DELIBERATELY, and it is a near neighbour of the
one that was fixed.** `index_v4/bulk_backfill.py::_stored_userset_subjects` still carries its
own `w2 == ''` test, for stored **usersets**. Different code path from the RC2 site, not part
of either root cause, and not widened because **no divergence justified it** — widening a
star-admitting filter without a failing case is precisely how RC2's two measured dead ends
happened. Recorded here because the board is what gets read: it otherwise lives only in
`tests/test_ttu_tupleset_parent_types.py`'s module docstring. **Bring a divergence before you
touch it** — the exhaustive sweep that mapped this family (2,302,854 queries, 346 schemas)
found exactly two root causes and neither was here.

★ **And a rot hazard this note exposed, worth more than the note.** The old board cited the
RC2 site as `bulk_backfill.py:454`. **That citation is now WRONG in the worst possible way:**
the fix inserted `_stored_tupleset_subjects`, and post-fix `:454` lands inside
`_stored_userset_subjects` — i.e. the line number that used to mean "fix this" now points at
the one clause that must be left alone. Current layout, as of this commit:
`_stored_userset_subjects` **447** (the untouched `w2 == ''` at 454) ·
`_stored_tupleset_subjects` **466** (the RC2 fix; its own `w2 == ''` at 479 is *fixed* code) ·
`_tupleset_parents` **485**. **Cite `file::function`, never `file:line`, for anything a
future session is meant to act on** — `verify.sh lean` already enforces exactly that for
`CORRESPONDENCE.md` anchors, and this file has no such gate.

★ **The part no design note predicted, and the transferable finding: the CASCADE FAN-OUT
had to change too.** A star tupleset tuple hangs off the `w_any(T,'...')` node, not off any
entity, so `_stored_parent_objects_of_entity` — which answers "what does a delta on this
entity invalidate?" by walking the entity's own edges — saw nothing, and a later write to
some `T:x` would have invalidated no dependent at all. **The read fix alone passes every
pin in the file**, because the pins write in one batch and reconcile once; it would have
failed only under incremental maintenance. *A correctness fix to a read path in an IVM
system is not done until the invalidation path has been asked the same question.*

**(2) The bulk corpus gap is CLOSED.** `rc2_star_tupleset` in `tests/test_bulk_build.py`,
carrying both TTU directions (positive fails closed, negated fails open — probing only one
mis-classifies severity by a sign). **Sabotage, literal output:** reverting the bulk half
alone — the S1 edit that used to leave the suite **6 passed GREEN** — now gives
`1 failed, 6 passed`, `AssertionError: [rc2_star_tupleset] snapshot_rows differ`, with the
other six corpora green so the red is attributable.

**(3) The compile-time invariant landed, and deliberately is NOT a mirror.**
`zanzibar_utils_v1.py::_assert_ttu_parent_types_cover_admission` — every TTU's frozen
`parent_types` must cover every bare-entity type ADMISSION accepts onto that tupleset
relation, read from the emitted `RewriteFilter`/`Filter` patterns and **never** from
`_member_types` (the function RC1 got wrong; an invariant reading it would reproduce I9's
mirror defect exactly). Validated RED-before/GREEN-after and made permanent as
`test_compile_refuses_parent_types_narrower_than_admission`. It catches the RC1 class **at
compile time, before any tuple is written**. Honest limit, stated in its docstring: it only
sees types some Filter accepts, so a tupleset fed only by rewrite Rules is vacuous there.

**(4) The compiler rough edge is FIXED** (was fix-list item 1a(4), "reported not fixed" —
now in the 2026-08 archive, where that stale wording is still visible). A TTU
whose tupleset is undeclared and whose target is derived died in `compile_boolean_schema`
with a bare `ValueError` — a class `tests/parity.py` says "must surface", so `ParityEngine`
was *unconstructible* (a hard crash) rather than degrading to 3-way. `_validate_ttu_tuplesets`
now refuses it up front as a scoped `UnsupportedByGraphIndex` and the `ValueError` is back
to being an unreachable backstop. The `genswarm` rejection witness was flipped to match,
and `test_undeclared_tupleset_with_untainted_target_still_compiles` is its **negative
control** — the witness alone is satisfied by an over-broad refusal, and "reject every
undeclared tupleset" is precisely the one-line over-fix a future reader would reach for.

**(5) Gate floors re-measured and raised** (`-ge`, so raising is free): `MIN_CONF_ALL`
465 → **494** (= 104 + 390), `MIN_TESTS_ALL` 763 → **823**. They had drifted ~90 tests below
live, i.e. that much coverage could have vanished silently.

**(6) No Lean change owed — and the reason is worth reading.** RC2's region is excluded
from the graph fragment by **two** standing hypotheses: `RulesBareStar.lean::TtuStarFree`
(star-subject tuples matching a TTU arm) and `RulesCorrect.lean::TtuTuplesetsDirect` (every
TTU tupleset must be `directsOnly`, so a *derived* tupleset is not expressible at all).
Nothing became dead code. Recorded in `CORRESPONDENCE.md` §7.3 — including the near-miss:
`TtuStarFree`'s own header records an attack-first `#eval` from 2026-07-11 on exactly this
shape, finding `sem=true` against a rule-routed graph `false`. ⚠ That was a property of the
LEAN write model and is **not** evidence anyone had observed the Python defect — Python's
UNTAINTED star-tupleset path was and is correct, and is pinned green by a control in the
same file. The general lesson still stands: **a shape fenced out of the model as "not
covered here" is a standing hint about where the implementation is least watched.**
Python moved TOWARD the models here: the new split is structurally
`SetEngine/Eval.lean::parentMS`.

⚠ **Correction to the previous board.** The item "`BoolStarBridgeParityMachine` runs the
graph on 12% of draws — cheap and independent, do it FIRST" was **already done** on
2026-08-10 in `d0dbefa` (the assertion is at `tests/test_hypothesis.py:1886`, 13% → 76–82%
4-way, floored with provenance). `docs/sabotage-procedure.md:31` was the accurate record;
this file and `docs/design/generator-coverage/README.md` were stale. Nothing to do.

### Still open (unchanged by this session)

Items 2–5 below are untouched and none is blocking: the two UNVERIFIED audit leads,
`ttuStarFree` as a four-part Lean leg, the scope-audit re-run, and leg 7. Item 6 is a
one-question optional loose end from the closed arc.

### 1. The RC1/RC2 arc — CLOSED. Archived 2026-08-11; three things kept here.

Both root causes are fixed (RC1 `ed46e54`, RC2 2026-08-11), the fix list is fully
discharged, and the generator gap that hid them is closed. The full text as it was briefed
while open — the divergence filing, the fix list, the generator-coverage leg, and the
measured-FALSE mechanisms — moved to
[`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md) §§1–1b.
**Read it before re-opening anything in this area**: it records which mechanisms were
measured FALSE, and a reader who acted on the original filing would have rewritten correct
leaf-routing code.

Three things are kept HERE because they are live, not historical:

* **★ The severity-sign rule — the single most transferable output of the arc.** A dropped
  TTU parent is a false NEGATIVE under a positive TTU and a false POSITIVE (an authorization
  **fail-open**) under a negated one (`define access: [user] but not viewer from parent`).
  **Probing only the positive direction mis-classifies severity by one sign** — which is
  exactly what the original filing did. Any new TTU corpus must carry both directions.
* **★ An instrument that shares its subject's defect cannot see it.** Neither RC was caught
  by I1–I14 with paranoia ON, and **I9 structurally CANNOT** catch this class: it re-runs
  `reconcile`, reads the same wrong `parent_types`, and agrees with itself. That is why the
  new compile-time invariant reads the emitted `RewriteFilter`s and **never** `_member_types`.
  Generalised in [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) ("the mirror
  instrument").
* **Generator coverage — the current baseline, and its honest limit.** `tests/genswarm.py`
  + `tests/test_generator_coverage.py` (**27** gated tests — re-measured 2026-08-11 with
  `--collect-only`; the archived prose says 26 and was already stale) reach, against a 1275-cell pairwise
  space **derived from six compiler sites** rather than hand-written:

  | | cells | % |
  |---|---|---|
  | baseline before the leg (the old generators) | 514 | 40.3 |
  | union, `ci` | **967** | **75.8** |
  | union, `deep` | 1034 | 81.1 |

  `UNACCOUNTED == set()` exactly, with no hand-written exemption list; 3 cells carry
  executable rejection witnesses instead. **~24–28 % of the pair space is still unreached
  even at `deep`** — so read a green gate as "the instruments we have found nothing", not as
  a proof. Design + raw evidence: [`docs/design/generator-coverage/`](docs/design/generator-coverage/),
  but ⚠ **trust the archive's three implementation corrections over that design doc.**

### 2. Verify or discard two UNVERIFIED claims from the failed audit.

Both come from single agents whose adversarial verifiers never ran. Treat as leads only.

* **`W4Fragment.computedOrDirect` — a LEAN-side under-report, and the driver fails OPEN.**
  Claim: on `access: viewer from parent but not banned`, `zcli mode=graph` answers
  `[false]` with **rc=0** while `mode=spec`, the Python graph, both set engines and the
  oracle all answer `[true]`. If it holds, the executable driver gives a wrong answer
  rather than refusing an out-of-fragment schema — worse than a refusal.
* **`GraphAdmission.ttuDirect` (`TtuTuplesetsDirect`)** — flagged `risk=HIGH`,
  `divergenceFound=YES`. Unread in detail.

⚠ Of the 26 audits that completed, one reported `divergenceFound: YES` on a schema **both
backends refuse**. That is exactly the false positive the verify phase existed to kill, so
do not promote any of these to a finding without reproducing it yourself.

### 3. `ttuStarFree` — DO NOT DROP IT. Machine-checked FALSE without it.

The user asked to undo this scope reduction. **It cannot simply be dropped**: dropping it
makes `graph_correct` and `backend_equivalence` FALSE, not merely unproven. The probe
machine-checked the refutation (sorry-free, axiom-clean, `ReachedBy` from the tree's own
`graphRun_reached`, 120 comparisons across 3 runs, control a one-character delta
`folder:*` → `folder:f1`):

```lean
theorem graph_correct_without_ttuStarFree_is_FALSE :
    ¬ (∀ S T σ q, GraphAdmission S T → W4FragmentNoTS S T → ... → GraphModel.check σ q = sem S T q)
```

★ **The counterexample needs no object wildcard**, so this is NOT the I14 bug — the
predicted mechanism was wrong and the conclusion still holds. The real gap is one layer
earlier: Lean's W1c in-bridge has no star-tupleset **through-shape** notion, and
`writeRules`/`writeLoggedRules` materialise **no bridges at all**. Python handles the shape
correctly; Lean's `ensureInBridges` on it is a literal no-op (`edges 3 → 3, nodes 6 → 6`).

**Lifting it is a four-part leg, not a flag edit:** (i) fold star-tupleset through-shapes
into `UsStarWrite.lean::Schema.isSubjectWildcardUserset` (mirroring
`derive_schema_info`'s second loop); (ii) compose `ensureInBridges`/`ensureBridges` into
the rule-routed write path; (iii) re-prove `ttuLeaf_elim_nss` and `StarSeed`, which exist
*because* of the clause; (iv) the remove leg (`removeGateB`, `ttuStarFree_restrict`).
`TtuStarFree` occurs **162 times across 18 modules**. Decide whether to schedule it; it is
not blocking anything.

### 4. Re-run the scope audit properly — hand-curated, ~15 items.

The 2026-08-10 fan-out died at 32 of 278 agents with **verify and synthesis never running**.
Read [`docs/subagent-fanout-runbook.md`](docs/subagent-fanout-runbook.md) BEFORE launching
another one — it is written from this failure. The two rules that would have saved it: a
machine sweep DISCOVERS candidates but must never DEFINE the fan-out (96 of its items were
parser error messages, which exclude nothing admissible), and every agent must persist its
result to its own file so a dead run still leaves its findings on disk.

### 5. Leg 7 (leaf-family split) stays parked.

Steps 3 and 4a landed 2026-08-09. Step 4c is blocked on the design fork in
`formal/history/leaf-family-split-scope-2026-08-05.md` §11.3 — where the `Delta` row is
addressed once the edge moves to the leaf node. Attack-first that before coding either
branch.

### 6. Optional, open question — NOT a finding. (Promoted from the closed fix list.)

The 2026-08-09 sibling (`docs/spec-deviations.md`) carries the same "it fails closed, so it
is not a security fail-open" wording, and the severity-sign rule above (a dropped TTU parent
inverts sign under a negated TTU) **predicts it inverts too**. It was never re-tested,
because it is fixed and testing it means reverting. If you want it settled: revert
`c042056` in a scratch worktree and add a negated TTU consumer. **Do not propagate the
prediction as measured fact** — it is a prediction from a rule, not an observation.

---

## Current status — 2026-08-11

**🟢 The gate is GREEN end to end, and the 2026-08-10 fail-open family is CLOSED.** All
ten phases plus the 6-seed fuzz sweep; no `sorry`, no `xfail`, no skip. See the banner at
the top of this file for the measured figures.

* **Known live correctness bugs: 0.** RC1 (`ed46e54`, 2026-08-10) and RC2 (2026-08-11) are
  both fixed, both at every site, and both pinned by positive assertions rather than
  xfails. The bounded exhaustive sweep that mapped the family found exactly two root
  causes, so it is closed at two.
* **Nothing regressed to get here.** Both bugs were PRE-EXISTING — RC1 reproduces on a
  hand-written schema at `e136c8c` with no `.py` file touched. The 2026-08-10 session made
  them *known and pinned*; this one fixed them.
* **★ The 2026-08-09 "everything is green" was true of the gate and false of the code**,
  and that caveat is now DISCHARGED rather than merely repeated: the generator-coverage leg
  landed (cell coverage, swarm, a drawn TTU tupleset, two driving regimes), and it is what
  made RC2 visible to a generator at all. A green gate here now means meaningfully more than
  it did — but its honest limit still stands, ~24–28% of the pair space is unreached even at
  `deep`, so read green as "the instruments we have found nothing", not as a proof.
  Numbers in §1 above; full leg in the 2026-08 archive §1b.

- **★ Last landed: LEG 7 IS UNDER WAY — steps 3 and 4a are IN** (2026-08-09, `8291c3a` +
  `41b7029`). `formal/lean/ZanzibarProofs/GraphIndex/Leaf.lean` is new: leaf addressing,
  the raw-write routing, the forked write `writeDirectRaw`, and the distinctness linchpin.
  Additive — headline statements 38/38 and the definition pin 155/155 **unmoved**.
  **The leg is NOT finished**; steps 4c, 4b, 5, 6, 7 remain. Three things a next session
  must read before touching it (all in `formal/history/leaf-family-split-scope-2026-08-05.md`
  §11 and `formal/history/PROOF_STATUS.md` 2026-08-09):
  * **The scope doc's §3 bet HELD** — the leaf-vs-bare distinctness linchpin needs no new
    axiom, `relNameOK` already gives it.
  * **★ Its §4 prescription is REFUTED.** Do not fork `writeDirect`; fork the TUPLE, as
    `RuleSet.apply` does. `writeDirect` then stays byte-identical and the duplication §4
    predicted for every projection and fold lemma is not owed.
  * **★★ Step 4c is blocked on a design fork the scope doc does not contain** (§11.3):
    once the edge moves to the leaf node, where is the `Delta` row addressed? The
    `Delta.leaf` tag does not answer it. Attack-first that before coding either branch.
- **Previously landed: THE `rewriteClosure` DEDUP LEG — `CORRESPONDENCE.md` §7.2 item 6 is
  CLOSED** (2026-08-08, `911c887` + `c488a2f`). The Lean model counted DERIVATION PATHS
  where Python counts LIVE RAW TUPLES, so on a *reconvergent* schema it over-counted edge
  multiplicity; `rewriteClosure` now mirrors `RuleSet.apply`'s worklist dedup, per stored
  tuple. Two corpora (`reconvergent_diamond`, `reconvergent_derived`) were added FIRST, in
  their own deliberately-red commit, so the divergence was attributable rather than
  arriving mixed into the fix. The count stack needed zero proof rework; the definition
  pin moved (154 → 155) while all 38 headline statements stayed byte-identical. **Leg 7's
  step 2b is discharged.** Three findings that correct live documents are in the board item
  below; full detail in `formal/history/PROOF_STATUS.md` 2026-08-08b.
- **Previously landed: E-chain Direct-arm widening, LEGS 5 AND 6 — `ZT-P3-1` IS CLOSED for
  T2b** (2026-08-05). The headline `graph_correct` / `backend_equivalence` /
  `exclusion_effective` / `no_ghost_grant` / `Exec.graphRun{,Ops}_check_eq_sem` are **no
  longer VACUOUS on `can_view: [user] but not blocked`**, the canonical Zanzibar boolean
  shape they had said nothing about since the claim was first written.
  `W4WitnessDirect.final_applies` instantiates the unsuffixed T2b at that store, and
  `final_applies4` does it at the four-tuple `direct_arm_exclusion` corpus store verbatim.
  * **Leg 5** rebased the bundles: `GraphAdmission.storeValid` → `StoreValidRulesD`;
    `W4Fragment`'s single `computedOnly` field → **five** derived-def clauses (so **ten**
    fields, not the plan's nine — `DirectArmsConcrete` again, exactly as §C.4 warned).
    `graph_correct` routes through `graph_correct_w3d2E_d`; the T3/T6 finals and both Exec
    drivers inherited it with **zero edits**. `w4Fragment_of_computedOnly` machine-checks
    that the old six fields imply all ten, so nothing that held before stopped holding.
  * **Leg 6** moved `direct_arm_exclusion` from `_DIFFERENTIAL_ONLY` into
    `_THEOREM_BACKED` (`_EXPECTED_SPLIT` `(22,1)` → `(23,0)`) and retired the vacuity
    caveat from ~25 prose sites across `formal/` and `docs/`.
  * **⚠ T2a did NOT widen, and now says so in its own type.** `graph_reached_inv` takes a
    third bundle `W4NarrowT2a` (schema-wide `ComputedOnly` + narrow `StoreValidRules`), and
    `outside_narrow_t2a` machine-checks that the Direct-arm store fails it. **T2a is still
    vacuous exactly where T2b no longer is.** Not a proof gap — probe D.3 machine-checked
    `Inv.negEdgeFree` FALSE on the `_d` fragment; Python is fine (P6 leaf-family modelling
    limit). A **design decision** is owed, not effort. This is the arc's predicted honest
    end state (plan §F) and the board item below is now about that decision.
  * Audits 471 → **481**; statements **26 → 38**; definitions **142 → 154**. No Python
    behavior changed (only conformance CLASSIFICATION + prose), so no fuzz sweep was owed.
  * **★ The leg-5 sabotage is the transferable finding, and it is worse than legs 3/4's.**
    A bundle REBASE needs a different control than a packaging clone. The plausible failure
    is the **half-done leg**: widen `W4Fragment` but leave `GraphAdmission.storeValid`
    narrow and convert with `storeValidRulesD_of_storeValidRules_directArmsBare` — which
    **typechecks**. Every gate signal then reads as success (statement byte-identical,
    definition pin MOVES so the gate even reports "meaning changed", audits clean), and the
    theorem is still worth nothing. Measured: with the witnesses present, ONE error in the
    whole tree; delete the four witness declarations and it is **"Build completed
    successfully (1084 jobs)"** — and since both goldens are GENERATED from the tree, the
    leg would have regenerated them to a self-consistent pair and passed the entire gate.
    Legs 3/4's sabotages at least reddened `FullScope`; this one reddens nothing.
  * Detail: `formal/history/PROOF_STATUS.md` 2026-08-05c/d, plan §C.5/§C.6.
- **Previously landed: legs 2/3/4** (2026-08-04 / 2026-08-05 / 2026-08-05) — the
  enumeration model change, the coverage packaging, the chain projection + E-chain final.
  Each carries a plan correction worth reading before trusting any cell of that document:
  two of its instructions were refuted by measurement, its gate specification was found
  insufficient **three legs running**, and its obligation inventory missed a hypothesis.
- **Previously landed: the P3 edge-multiplicity blind spot, ADJUDICATED and closed** — the
  last open item where the gate was blind to a whole class of divergence. Verdict:
  real, model-side, confined exactly to the DERIVED arm (Python's presence diff caps
  `direct_edge_count` at 1 there; the model compounds to 1013), removal-inert. P3 is
  narrowed so untainted-arm multiplicity is now compared EXACTLY — 153 edges that
  nothing had ever compared — and the derived arm is golden-pinned. Detail:
  `formal/CORRESPONDENCE.md` §7.2, `docs/spec-deviations.md` 2026-07-29.
- **Also landed 2026-07-29: the counts pin.** `ZT-P3-5` ("every doc number is stale and
  nothing enforces any of them") had been hand-fixed twice and rotted a third time, so
  `formal/FINAL_REVIEW.md`'s headline counts are now GENERATED
  (`formal/conformance/doc_counts.py`) and checked by `verify.sh` step 4e. It **fired on
  this session's leg-6 doc edits** (a new `CORRESPONDENCE.md` anchor), which is the first
  time it has caught a live drift rather than a historical one.
- **Live gate figures live in ONE place** — the generated counts block in
  `formal/FINAL_REVIEW.md`. Do not restate them here; this file went stale three times
  doing exactly that.

**History moved out 2026-07-29:** the dated status run, the full zero-trust review, and
every completed board item are now in
[`docs/history/handoff-status-2026-07.md`](docs/history/handoff-status-2026-07.md),
together with the reconciled **`ZT-*` disposition ledger** (which fixes three ids that
had no disposition anywhere and one that was listed CLOSED while its substance was
open). This file is now only what a future session must ACT on.

**History moved out again 2026-08-11:** the whole RC1/RC2 arc as briefed while open (the
divergence filing, the discharged fix list, the generator-coverage leg) plus four completed
board items are now in
[`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md).
⚠ **Status lines inside an archive are frozen as-of-then, and several in that one are now
wrong** (it still says "still owes the fuzz sweep", "when you fix it", "reported not
fixed") — its header says so. The live end state is "What landed 2026-08-11" at the top of
this file. **The rule this file keeps re-learning: archive the STATUS, keep the METHOD.**

---

## Open-TODO board

### Active work

> **Three items retired from this board on 2026-08-11** — all landed, full text in
> [`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md):
> the OWC × star-parent × TTU divergence (found + fixed 2026-08-09, `c042056`, pinned by
> `tests/test_owc_star_parent_cross.py`, property lifted to **I14**); the `rewriteClosure`
> dedup leg (landed 2026-08-08, `911c887` + `c488a2f` — `CORRESPONDENCE.md` §7.2 item 6
> CLOSED, leg 7 step 2b DISCHARGED); and that leg's superseded original filing, kept then
> for its scope pointers. Their carries into leg 7 survive in the item below.

- [ ] **★ START HERE (next session, refreshed 2026-08-05d) — the E-chain arc has reached
      its predicted end state, and what is left is a DESIGN DECISION, not proof effort.**
      The zero-trust backlog is CLEARED, the gate is green end-to-end, and as of 2026-08-05
      **`ZT-P3-1` is closed for T2b**: legs 0–6 of the E-chain Direct-arm widening have all
      landed, so the headline graph theorems are no longer vacuous on
      `can_view: [user] but not blocked`. See the status block above for what that means.

      **(B1) T2a (`graph_reached_inv`), leg 7 — ★ THE DECISION IS MADE (2026-08-05):
      option (c), model the leaf-family split and retire P6. DEFERRED, not scheduled.**
      Scope + blast radius + suggested ordering:
      [`formal/history/leaf-family-split-scope-2026-08-05.md`](formal/history/leaf-family-split-scope-2026-08-05.md).
      **Nothing is blocking and nothing is broken** — the asymmetry is honestly declared in
      the type, so leaving it costs only reach, not correctness. Headline numbers: **55–65%
      of the Lean tree touched**, 15–20% of declarations needing real proof rework; the spec
      side (`Spec/`, `SetEngine/`, `Equiv.lean`) is entirely spared, so the leg cannot
      perturb the trust root. Two findings that make it cheaper than it looks: the
      distinctness linchpin **already exists** (`Core/Schema.lean:64` `relNameOK` forbids
      `.` in declared names, so leaf nodes are provably distinct for free — no new axiom,
      provided leaf preds stay OUT of `S.defs`), and the routing signal **is already
      threaded** (the `Delta.leaf` tag landed 2026-07-20c; the leg turns it from a
      bookkeeping discriminator into an addressing one).
      **★ RESUME POINT (2026-08-09): steps 0, 1, 2, 2b, 3 and 4a are DONE. The leg resumes
      at the §11.3 DESIGN FORK, then step 4c.** Read `formal/history/PROOF_STATUS.md`
      2026-08-09 and scope doc §11 FIRST — §4 of that document is refuted (fork the TUPLE,
      not `writeDirect`) and §11.3 is a decision the document does not contain (where the
      `Delta` row is addressed once the edge moves; the `Delta.leaf` tag does NOT settle
      it). The four older notes below still stand:
      * **The attack-first probe returned NO-KILL** — `negEdgeFree` holds under leaf
        routing, positive control reproduced D.3's kill in the same run. The leg is still
        on at full price (§9.1).
      * **★★ `Sd`/`Td` CANNOT be leg 7's witness.** `negEdgeFree` is already vacuously
        true there (no residue row at all; `negStarCovered` + no wildcard ⇒ `neg = []`).
        A step proving it and instantiating at `Sd`/`Td` would pass every mechanical check
        in the project and prove nothing. Use D.3's wildcard-carrying schema (§9.3).
      * **`uposEdgeFree` was never implicated** — structurally immune on the `_d`
        fragment. The `Inv`-side obligation is ONE clause, not two (§9.2).
      * **~~★ NEW step 2b, ordered BEFORE step 3~~ — DONE 2026-08-08.** The two
        reconvergent corpora are in, and `CORRESPONDENCE.md` §7.2 item 6 is CLOSED:
        `rewriteClosure` now dedupes per stored tuple. **Step 3 may start; any red it
        produces is now attributable to the leg.** ⚠ Two carries for the leg proper:
        the post-fork leaf multiplicity is still UNMEASURED (scope doc §10.4), and
        `reconvergent_derived`'s derived arm is `lean=52 python=1` — after the
        `writeDirect` fork that contribution lands on `viewer.0`, untainted arm, compared
        EXACTLY, so expect it to move and budget for it.
      **Steps 0 and 1 were done 2026-08-05.**
      (0) The P6 figure everyone quoted ("62 of 447 rows") was the 2026-07-27 measurement
      over **21** corpora and every leg but the P2 zero had drifted. It is now GENERATED
      (`extractor.py::graph_fragment_ledger` → `FINAL_REVIEW.md`'s counts block, checked by
      `verify.sh` step 4e, +~5 s) and sabotage-verified. **Read the live baseline out of
      `FINAL_REVIEW.md`'s generated block, not from here** — until 2026-08-09 this line
      used to carry its own copy (`23 corpora, 477 raw rows → 233 P1, 0 P2, 73 P6, 171
      compared, target compared=244`, all of it as of 2026-08-05 and all of it since
      superseded) and the dedup leg's two new corpora made every one of those figures
      wrong within three days, including **the leg's own success criterion**. The criterion
      is now stated in the form that cannot rot: **when the leg lands, `dropped by P6` must
      be 0 and `compared against Lean` must equal today's `compared + dropped by P6`** —
      loudly, by design. Re-derive both from the generated table immediately before
      starting, because adding any corpus moves them.
      (1) The filed "widen `evalE`'s modeled arms first" prerequisite **does not exist** —
      leg 5 already widened `direct`, `ttu` is not implicated, and a leaf probe goes through
      `probeNonDerived`, not `evalE`. The stale docstring that caused it
      (`ReconcileWrite.lean`) is corrected. What the concern was really pointing at is a
      **leaf-probe ↔ `directLeaf` bridge** *inside* the leg, now step 4b.
      Why (a) and (b) were rejected, and why (c) is not merely the expensive option, is §1
      of the scope doc — the short version is that **nothing consumes `Inv`** (four
      hypothesis sites, all `Inv → Inv` preservation), so weakening it could not go red,
      which is exactly the house failure mode.

      Background — what the decision is *about*:
      `graph_reached_inv` now takes a third bundle `W4NarrowT2a` (schema-wide
      `ComputedOnly` + the narrow `StoreValidRules`), and
      `W4WitnessDirect.outside_narrow_t2a` machine-checks that the canonical Direct-arm
      store fails it — **T2a is vacuous exactly where T2b no longer is.** That asymmetry is
      now DECLARED in the type rather than buried, which was leg 5's deliberate output.

      Why it is a decision and not a proof: Leg-0 probe D.3 (2026-07-28) **machine-checked
      `Inv.negEdgeFree` FALSE** on the `_d` fragment. Under `StoreValidRulesD` a Direct-arm
      write lands an edge at the very derived R-node whose residue carries the `neg` row,
      and `Inv` forbids that. **Python is fine** — verified on the real backends:
      `RuleSet.apply` routes the write onto the leaf family, so the edge lands on
      `#approver.0`/`#approver.2` and never on `#approver`; different nodes, I6 disjointness
      intact, 0 mismatches over the grid and a 6-way order sweep. It is a modelling limit of
      projection **P6** (the leaf-family collapse), and no gate in the project can see it.

      The three options were (a) restate T2a at DRAINED states only, (b) weaken
      `negEdgeFree` to exempt the current un-cascaded write leg, and
      **(c) model the leaf-family split — CHOSEN.** (⚠ (b) used to name
      `uposEdgeFree` as well; **refuted by measurement 2026-08-08** — it is
      structurally immune on the `_d` fragment, so leg 7's `Inv`-side obligation is
      ONE clause, not two.)
      **Start:** the scope doc above, then `W4NarrowT2a`'s docstring in `FullScope.lean`,
      then plan §D.3.

      **(B2) Two smaller pieces of the arc's payoff that legs 5–6 did NOT deliver**, both
      recorded rather than quietly dropped:
      * **The Lean REMOVE gate still excludes `direct_arm_exclusion`**
        (`test_conformance_remove_graph._REMOVE_EXCLUDED`). The REASON changed and the
        exclusion did not: it used to be an admission-scope exclusion (gone with leg 5) and
        is now purely that `removeGateB` decides plain `storeValidRulesB`. Lifting it needs
        a `storeValidRulesDB` decision procedure + soundness lemma + a widened `remove`
        constructor. Note leg 4 converted the constructor's admission INWARD with
        `storeValidRulesD_of_storeValidRules_directArmsBare`, and that does not run
        backwards — **its own leg, not a flag edit** (plan §C.5 item 6).
      * **`self_flag` — ADJUDICATED 2026-08-08: it HOLDS, and the premise of this item was
        wrong.** All ten `W4Fragment` fields hold, plus all eight `GraphAdmission` fields
        and **both `W4NarrowT2a` fields** (so unlike `direct_arm_exclusion` it is inside
        T2a too). The expired justification — "Direct arms under a boolean — genuine
        storage leaves, not `computedOnly`" — was **factually wrong when written**, not
        merely stale: `usable: activated but not deprecated` has NO Direct arm inside the
        derived def (machine-extracted AST is `.excl (.computed …) (.computed …)`, i.e.
        `ComputedOnly`; Python gives it two `PClosureLeaf(storage=False)`). It was in the
        fragment before leg 5; leg 5 was never load-bearing for it. The two flagged fields
        are orthogonal to self-referentiality — `bareStar` constrains subject NAME vs
        `STAR`, `NoStoreSubjectR` constrains subject PREDICATE, self-referentiality is a
        subject-ENTITY↔object-entity property. Corroborated live: 0 mismatches on a
        78-query grid, `zcli` graph mode rc 0 and landed drained, `diff_states` → `None`.
        **Still spec-side, deliberately** — per ZT-P3-3 the argument is prose until the
        witness exists. **Remaining work: write `W4WitnessSelfRef`** (designed in
        PROOF_STATUS 2026-08-08 §6; model on `W4Witness`, not `W4WitnessDirect` — it needs
        no `_d` layer), with two non-vacuity instruments, because the plausible failure
        here is not an uninhabitable bundle but a **tautological clone** of `W4Witness.Sx`
        under renaming. ⚠ And decide promotion separately: it buys less than it looks —
        the node-level GC behaviour the corpus exists for is dropped entirely by P5
        (9 node rows, 0 crossing the seam).

      **(A) ~~the store-level write quota~~ — DECLINED by the user 2026-07-29**, and the
      alternative was measured rather than assumed. *"I don't want to limit what can be
      added to a permission store — it might be slow but it should not be limited by perf."*
      The proposed substitute (detect a DoS fan-out, bulk-rebuild instead of adding
      normally) was **measured and does not work**: bulk is 7–15x faster to BUILD but
      produces byte-identical closure rows (so it fixes nothing about size), makes the worst
      single lock stall 25–43x WORSE (105 ms -> 2.7 s at N=480; 237 ms -> 10.1 s at N=960),
      cannot be triggered (the only fan-out signal is the per-write region, measured at 120
      — the signal already known not to fire), is structurally refused mid-stream by
      `build_index`, and **loses every REMOVED outbox row** (measured 143 ADDED/42 REMOVED
      incrementally vs 101/0 on a rebuild) — which §8.3's verifier is blind to. **The answer
      that already exists is `ConnectedStore(sync=False)`:** measured 14.5x lower write
      latency (2.7 ms/write vs 105 ms max), closure work off the write path, writers and
      catch-up on different lock rows, and a consistency contract that is already built and
      pinned. It bounds *whose latency pays*, not what can be stored. Full measurement + the
      two further options (rebuild-vs-K-deltas amortisation, crossover K* ~ 30–40; and
      routing hub workloads to the set engine, 0.03 s vs 74 s at N=960):
      `docs/spec-deviations.md` 2026-07-29c. `ZT-P1-6a` therefore stays half-closed by
      decision: `ZANZIBAR_MAX_CLOSURE_FANOUT` bounds what ONE add may materialise, and no
      store-level quota is wanted.

      **★ READ THIS BEFORE FOLLOWING ANY CELL of
      `formal/history/echain-widening-plan-2026-07-28.md`.** The plan is a *reading* of the
      tree, not gospel, and executing it produced six sections of corrections
      (§C.1–§C.6). The pattern worth carrying to the next arc:
      * **Two of its instructions were WRONG and were caught by measuring rather than
        following them** (§C.2): "`enum2BaseD`'s `.dedup` goes first" — the duplicate was
        somewhere else and `.dedup` a no-op; and "leg 2 will break the multiplicity ledger"
        — it did not, and the green was *controlled* (defeating the filter moves exactly one
        corpus) rather than trusted.
      * **Its per-leg GATE cell was insufficient THREE LEGS RUNNING** (§C.3, §C.4, §C.5) —
        each time specifying "`lean` + pins" and no non-vacuity instrument, the second and
        third times *after* the document already contained a section saying so. Legs 3, 4
        and 5 each had to budget a witness the plan did not ask for.
      * **Its obligation inventory misses hypotheses because it walks one half of the
        proof** (§C.4, recurring in §C.5): `DirectArmsConcrete` arrives through the VALIDITY
        half, so an inventory organised around the coverage lemma predicted 15 hypotheses
        where there were 16, and 9 fragment fields where there were 10.
      * **A rebase needs a different sabotage than a clone** (§C.5) — see the status block.

      **Before starting anything:** `bash formal/verify.sh lean` should be green in
      ~60 s warm. If it is not, fix that first — it is the fastest signal in the repo.
- [ ] **Follow-ups left from the assurance-widening arc (opened 2026-07-18).** The arc
      itself is archived — legs #1(1–3), #3 and #4(R1–R5b) all landed, and its two
      "next" pointers are dead (#2 strata >2 was scoped and DECLINED 2026-07-27; #1
      Direct-arm is now the E-chain arc, whose plan supersedes the old fork list).
      What genuinely survives is three small items, none blocking:
      1. **`FINAL_REVIEW.md` §4(d) scope wording under-claims** (stale-conservative
         after the remove leg closed). Plausibly subsumed by the `ZT-P3-4`/`ZT-P3-5`
         sweeps — never confirmed either way.
      2. **Exec-driver remove hardening** — largely done 2026-07-19g (`graphRunOps`,
         `removeGateB`, the zcli `"ops"` stream, `test_conformance_remove_graph.py`),
         but with one live exclusion: `_REMOVE_EXCLUDED = {"direct_arm_exclusion"}`,
         because the remove guard is stated over plain `StoreValidRules` under which a
         Direct-arm-under-exclusion tuple is inadmissible. So "removes are driven
         end-to-end" holds for every in-fragment corpus except the newest. **This did
         NOT ride E-chain leg 5, as this line used to predict** — leg 5 widened the
         ADMISSION bundle, and `removeGateB`/the `remove` constructor are a separate
         guard that still decides plain `storeValidRulesB`. It needs a
         `storeValidRulesDB` decision procedure + soundness lemma + a widened `remove`
         constructor: its own leg. Tracked in board item (B2) above.
      3. **The guard design decision** (validly-stored + drained-prior scope) was
         APPROVED 2026-07-19; no longer open. Recorded here only so the pointer in
         `formal/HANDOFF.md` is not read as a pending item.
      Resume detail: `formal/history/optional-widening-2026-07.md`,
      `formal/history/PROOF_STATUS.md` 2026-07-19f.
- [ ] **`_any_residue_reference` / `_keys_referencing` — MEASURED 2026-07-29; the fix
      is not done.** The complete `ResidueV1` scan on every node-release path is
      cleanly **O(R) at ~15 µs per residue row** (0.35 ms at 25 rows → 22 ms at 1600;
      x1.98 per doubling). It is a minority term below ~1–2k residue rows and the
      DOMINANT term above; extrapolated, 100k residue-bearing keys cost **~1.4 s per
      node release**, and a churn past the crossover goes quadratic. **Scope:** R is
      the number of `(object, derived relation)` pairs with a WILDCARD grant, not
      tuples — stores with no boolean relations pay nothing.
      **Remaining work** is the fix `ZT-P0-1`'s own note named: replace the scan with
      a node-id-keyed reference index maintained alongside `neg`/`upos`. That is an
      algorithm change (full gate + multi-seed fuzz + a Lean/CORRESPONDENCE look), so
      it was deliberately not smuggled into a measurement pass.
      Numbers + the instrument trap: `docs/spec-deviations.md` 2026-07-29b.
### Someday / out of scope (low priority — revisit only on a concrete need)

- [x] ~~**Vendor a corpus of REAL OpenFGA schemas, crawled from the wild**~~ —
      **DONE DIFFERENTLY, 2026-08-11: reviewed, measured, and ADAPTED rather than
      vendored.** The user supplied a corpus (canonical `openfga/sample-stores` +
      internal models). Outcome, all measured:
      * **48 schema files, 22 compile, and `UnsupportedByGraphIndex` rejections = 0.**
        That is the evidence this item was built to produce → see the scope-rejection
        item directly below, whose deferral is now **evidence-backed rather than
        assumed**. (The 26 non-compiling are out of scope by construction, not
        rejections: 11 use CEL conditions, 4 use modular `module` models, 11 are
        `model_file:` indirections or test-only files.)
      * ⚠ **This item's own premise was WRONG, and the correction is the useful part.**
        It said real schemas "essentially never touch the wildcard × boolean × TTU
        crosses". One internal schema hits that cross dead-on — a De Morgan
        "holds ALL required roles" model with `[user:*]`, an exclusion over it, a TTU
        whose TARGET is derived, and that TTU under a negation. **The prediction still
        held** (0 divergences; an RC1 sabotage leaves it green, instrument controlled
        against the known RC1 repro) — but "they never touch the crosses" is false, and
        the *reason* to expect passing is not the reason recorded here.
      * **Nothing was vendored, and copying would have been near-worthless anyway:**
        `demorgans_law_2.fga` is structurally the same schema as the interesting
        internal one, plus an `and` and an extra TTU hop. Instead two shapes measured
        at **zero occurrences across all 11 pre-existing fixtures** were adapted into
        new fixtures — `tests/fga_schemas/userset_over_derived.fga` and
        `heterogeneous_tupleset.fga`, driven by `tests/test_real_world_shapes.py`.
        ★ The sharper of the two: **every TTU tupleset in the old corpus was
        single-type**, so `parent_types` was never exercised with breadth > 1 — and
        `parent_types` breadth is exactly what RC1 got wrong.
      * **Licensing sidestepped, not solved.** Adapting rather than copying means no
        internal schema text entered the tree and no per-schema manifest was needed.
        If anyone later wants the literal schemas, that decision is still open and is
        the user's. `.scratch/` is now gitignored (`0e6ef33`) — it was untracked but
        NOT ignored, in a repo that mirrors.
      * **Still open from the original framing:** the "plausibility anchor for the
        generated-schema campaign" use. `tests/genswarm.py` remains tied to nothing
        real; the two new fixtures are a start, not that anchor.

      *Original filing kept below for the reasoning it recorded.*
      **What it is for, and it is NOT bug-finding.** Real-world schemas are union/TTU
      heavy and essentially never touch the wildcard x boolean x TTU crosses where every
      divergence this repo has found actually lived, so expect them to pass. The value is
      that they are the **empirical instrument for the scope-rejection item directly
      below**: that item defers on "revisit on a concrete need", and its *previous*
      priority argument was already found INVALID once (see its own note). A corpus of
      schemas people actually wrote is how you decide whether a concrete need exists —
      if 3 of 40 hit `UnsupportedByGraphIndex` the item's priority changes overnight; if
      0 of 40 do, the deferral becomes evidence-backed instead of assumed. Second use:
      a plausibility anchor for the generated-schema campaign, which is otherwise tied
      to nothing real.
      **Precedent already exists** — `tests/fga_schemas/gdrive.fga` and `github.fga` are
      OpenFGA's canonical sample stores, already vendored. This extends an accepted
      pattern.
      **Sources:** `openfga/sample-stores`, the OpenFGA docs modeling guides, the
      playground examples, GitHub code search for `.fga` / `model\n  schema 1.1`.
      **Two constraints:** record provenance + license per schema in a manifest (OpenFGA
      is Apache-2.0), and remember a crawl supplies **inputs only** — `tests/oracle.py`
      stays the spec, so a real schema is a query-grid subject, never an expected answer.
- [ ] **Lift the two scope rejections** — object wildcards on derived relations, and
      wildcard usersets over derived relations, currently raise
      `UnsupportedByGraphIndex` (loud compile-error hooks); the documented fix is a
      symmetric subject-keyed residue (symbolic composition through residues), and it
      is the sole item not yet modeled in Lean (`formal/FINAL_REVIEW.md` §4 last item).
      **Priority argument CORRECTED 2026-07-29.** This item used to read "Low priority —
      the OpenFGA DSL does not support these either". `ZT-P5` bullet 1 declared that
      argument **INVALID** and it was never applied back here: this repo already ships
      object wildcards as a deliberate extension BEYOND OpenFGA (they have no DSL
      syntax and are passed via `object_wildcard_shapes`), so "OpenFGA doesn't have it"
      cannot justify deprioritising a construct the repo itself invented. The honest
      remaining argument is narrower and still holds: no concrete need has appeared,
      the rejection is LOUD (compile-time, not a silent wrong answer), and the one
      plausible pattern (broad grant + per-object boolean exception) is expressible via
      a supported TTU/hierarchy. Revisit on a concrete need — not on the old reasoning.
      **Scope note (2026-07-28):** wildcard usersets over an UNTAINTED relation are
      fully supported and now have corpora; only the DERIVED case is rejected.
- [ ] **A real service wrapper** — deliberately skipped; the store is a plain
      callable API.
- [ ] **Tuple-log compaction** — only if the log ever outgrows "humans wrote this" scale.
- [ ] **Bulk-merge write path (batch closure update seeded from EXISTING state).** The one
      high-value UNBUILT write optimization (never filed in the perf arc — it crosses the
      Lean/identity bar, so it isn't a micro-opt). Sits between the two shipped paths:
      incremental `advance_index` (per-edge `O(anc×desc)`, writes only the delta) and
      from-empty `bulk_build`/`bulk_backfill` (one topo+DP pass, 30–200×, but REFUSES a
      non-empty store). Goal: apply a large batch to an already-populated index by loading
      the affected region, recomputing the merged closure delta in memory (bulk-builder DP
      seeded with existing boundary path-counts), and writing back ONLY changed rows.
      **When it wins:** batch touches ~>2–3% of the closure (incremental's summed regions
      get expensive) but far less than the whole graph (a full rebuild wastefully rewrites
      the untouched majority). **Why it's hard / the crux:** a merge must reproduce, against
      PRE-EXISTING rows, all the coupled invariants the from-empty builders are add-only
      exempt from — `EdgeV4` direct/indirect counts (incl. boundary composition), the I5
      `derived` flag, `ResidueV1` stars/neg/upos+version, from-chain nodes, node
      `reference_count`/implicit GC (order-sensitive), sticky explicit-promotion — plus
      remove/GC/diff cases (`_gc_*` deletes) the mirrors never hit. **Reuse:** `bulk_build.py`
      Phases R/C/P/W + a `_BulkBackfill` recompute SCOPED to affected derived keys. **Gates:**
      changes a modeled algorithm → differential identity gate (mirror `tests/test_bulk_build.py`:
      bulk-merge == incremental `advance_index`, byte-identical mod row-ids), hypothesis
      campaign (esp. removes), a Lean twin + `CORRESPONDENCE.md §7/§8` entry (an "alternative
      constructor" like P13/R4-BF), full phased `verify.sh` + fuzz. **Phasing:** bench first
      (no large-batch-on-large-index bench exists today — build one, and confirm whether the
      cascade or the closure DP dominates), then add-only merge behind a distinct entry point,
      then removes. Watch the P12c fence (outbox/watermark/cascade coupling). A fuller
      design sketch was produced 2026-07-19 in a read-only session but not yet written to a
      `docs/` design doc — write it up (match `docs/architecture/p13-bulk-build-design.md`
      style) before implementing. Revisit only on a concrete large-batch ingest need.

### Standing / latent (non-blocking — no action needed unless a motivating case appears)

> **`TupleSource.__init__` is not atomic on PostgreSQL** — CLOSED (the entry was itself
> stale; nothing in the tree is xfailed, `MAX_TESTS_XFAILED=0`). Retired 2026-08-11 to
> [`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md), which
> keeps *why* it stayed visible: for two days it was the one entry that would have made a
> reader believe a live authorization-adjacent bug was open.

- [ ] **Other documented latent/theoretical notes** — "documented, no corpus exercises
      it, not urgent" corners. **Inventory refreshed 2026-07-29:**
      * the **from-chain TARGET** note — **RE-DERIVED 2026-07-27, and its reachability
        half is DISPROVED.** (`ZT-P5` bullet 5 said it had "never been re-derived", and
        the 2026-07-29 board refresh repeated that; both were stale — the work was done
        on 2026-07-27 and is executable, not asserted.) The 2026-07-13 claim "no
        currently-compilable schema class reaches this shape" is FALSE: `_from_chain_keys`
        enumerates ALL stored parents, so a parent of a different type with an UNTAINTED
        `target_rel` yields exactly the excluded shape. Pinned by
        `tests/test_zt_p5_readjudication.py::test_zt_p5_from_chain_target_shape_IS_reachable`.
        **The other half survived:** 400 randomized trials (88 of which reached a fresh
        untainted+bridged from-chain intern) gave 0 admission divergences, 0 answer
        divergences, 0 invariant violations, 0 `audit_fixpoint` failures, on 3 seeds.
        **What is genuinely still open is narrower than "the note":** the structural
        reason offered for the clean result is explicitly *a hypothesis, not a proof*,
        it is **not established for intersection-rooted grant relations**, and **no
        bounded search was run over >2 strata**. Those two are the live residue.
        Detail: `docs/spec-deviations.md` "Target 2".
      * the **I7 checker corner** — an in-place residue-version regression to exactly 1
        is undetectable. Note this is now known to be worse than "checker sensitivity":
        `ZT-P4-5` established that **I7 is gated by nothing formal at all** (Lean's
        `Residue` has no version field — projection **P7**), so the Python paranoia
        checker is its only pin. See `formal/CORRESPONDENCE.md` §7.2.
      * **`_any_residue_reference`'s full `ResidueV1` scan** (`ZT-P5` bullet 6) is
        unbenchmarked and became UNCONDITIONAL after the `ZT-P0-1` fix. The only
        item here with a measurable cost.
      * **Object wildcards at STATE level** (`ZT-P5` bullet 2) — **half done.** The
        PYTHON side was probed clean on 2026-07-27 (a deterministic ~72-state slice is
        pinned by
        `tests/test_zt_p5_readjudication.py::test_zt_p5_bounded_search_object_wildcard_out_bridge_no_further_divergence`,
        plus a 344-trial exclusion sweep with zero divergences). **The LEAN side is
        still UNVERIFIED** — `docs/spec-deviations.md` "Target 3" says so in as many
        words. So the "fragment exclusions are proof-scope, not observed divergence"
        inference still rests on check-level evidence for the model corner, which is
        the exact inference class that failed at state level on 2026-07-17.
      The tupleset-of-derived gap formerly listed here was RESOLVED 2026-07-13.
      Full log: [`docs/spec-deviations.md`](docs/spec-deviations.md).
      Do not chase speculatively; act if a real schema or corpus surfaces one.

## Where things live

| doc | what it is |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | durable rules: env, the gate, layout/mental model, testing conventions, invariants |
| [`docs/architecture/overview.md`](docs/architecture/overview.md) | **architecture index** — module map + pointers to every deeper doc |
| [`docs/gate-runbook.md`](docs/gate-runbook.md) | how to run the full gate cap-safe (phased `verify.sh`, incl. `tests/`, + the Postgres leg + fuzz), and every floor/budget it enforces |
| [`scripts/pg_local.sh`](scripts/pg_local.sh) | throwaway user-space PostgreSQL for the server leg (`start`/`stop`/`status`/`destroy`) — no system install |
| [`tests/dbengine.py`](tests/dbengine.py) | the SQLite-vs-server engine seam (`ZANZIBAR_TEST_DSN` / `ZANZIBAR_PG_REQUIRED`) |
| [`docs/perf-next-round.md`](docs/perf-next-round.md) | perf standing guardrails (arc closed; fence + dead-ends + hygiene) |
| [`docs/spec-deviations.md`](docs/spec-deviations.md) | dated log of where the code diverges from the specs, and the latent-gap inventory |
| [`docs/specs/`](docs/specs/) | the full original design specs (cited by code comments as "spec §N") |
| [`formal/HANDOFF.md`](formal/HANDOFF.md) | entry point for the Lean formal layer (read before touching `formal/`) |
| [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) | the model↔Python code map (§7/§8 record any algorithm drift) |
| [`formal/history/leaf-family-split-scope-2026-08-05.md`](formal/history/leaf-family-split-scope-2026-08-05.md) | leg 7 (T2a / retire P6): the DECIDED-but-DEFERRED design, its blast radius, and the step ordering |
| [`benchmarks/results/PERF_ANALYSIS.md`](benchmarks/results/PERF_ANALYSIS.md) | measured perf numbers per landed item ("Applied") |
| [`docs/history/`](docs/history/) | retired records — perf rounds 3–5 and the HANDOFF status archive; provenance, not living docs |
| [`docs/history/handoff-status-2026-07.md`](docs/history/handoff-status-2026-07.md) | this file's retired dated status run, the full zero-trust review, every completed board item, and the reconciled **`ZT-*` disposition ledger** |
| [`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md) | the retired RC1/RC2 TTU-tupleset arc (filing, fix list, generator-coverage leg) + the 2026-08-08/09 completed board items — ⚠ status lines frozen as-of-then, read for method not state |
| [`formal/FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) | the governing claim doc — and the ONLY place live counts belong (generated block, gated by `verify.sh` step 4e) |

---

## Working rhythm

1. **Read this file + `CLAUDE.md` first.** Pull deeper docs on demand from the map above.
2. **Run the gate before pushing** — never push red or unverified. Cap-safe recipe
   in [`docs/gate-runbook.md`](docs/gate-runbook.md): `verify.sh lean` →
   `conf-tile:1/5`…`5/5` → `tests-tile:1/4`…`4/4`, all `PASSED`; an algorithm change
   also runs the multi-seed fuzz sweep (`--hypothesis-seed=N`, **not**
   `HYPOTHESIS_SEED=N`, which hypothesis does not read — `tests/conftest.py` now
   refuses it). `tests/` runs THROUGH `verify.sh` since 2026-07-27; a bare
   `pytest tests/` is for iterating, not for gating. Anything touching locking,
   watermarks, isolation or multi-instance state should also run the PostgreSQL leg
   (`bash scripts/pg_local.sh start`, then `ZANZIBAR_TEST_DSN=…`). **The local
   cluster is STOPPED but RETAINED** — `start` brings it back in seconds, `destroy`
   removes it entirely; nothing in the default gate needs it.
   Commit and push **only when asked**.
3. **Keep the honesty norms** — report gate output as-is; if something is skipped
   or fails, say so. Never edit a golden/oracle/snapshot just to make a change pass.
   Corollary learned 2026-07-27: **an assurance step that fails by PASSING is the
   house failure mode** — a skip, an xfail, a zero-length loop, a count that cannot
   go down, a green run of a seed that never varied. When you add a check, sabotage
   the thing it guards and watch it go red before you believe it.
3b. **Do not restate gate counts in prose.** They live in `formal/FINAL_REVIEW.md`'s
   generated block and are machine-checked (`verify.sh` step 4e); regenerate with
   `python -m formal.conformance.doc_counts --generate`. This file went stale three
   separate times by keeping its own copies (`ZT-P3-5`).
4. **Keep this board current** — add active tasks when you start them, clear them
   when the work lands (the git log + `docs/history/` are the durable trail).
5. **Perf or algorithm work?** A behavior-preserving micro-opt needs no Lean change;
   an optimization that changes a *modeled* algorithm must update the matching Lean
   def and re-run `verify.sh`, or log the gap in `formal/CORRESPONDENCE.md §7`
   (see `CLAUDE.md` "Perf work & the Lean model").
