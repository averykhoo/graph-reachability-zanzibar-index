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

## ★★ START HERE — THE PLAN (2026-08-10)

Written so a fresh session can act without reading the rest of this file first. Ordered.
Everything below is either VERIFIED (reproduced by hand) or explicitly marked UNVERIFIED.

> # 🔴 THE GATE IS RED ON PURPOSE. READ THIS BEFORE YOU DEBUG ANYTHING.
>
> The 2026-08-10 session pinned two live divergences and **deliberately did not fix them**
> (the user scoped that session to test-prep and deferred the fix + gate run). Nothing is
> broken by accident. **The expected-red inventory is exactly this, and nothing else:**
>
> ```
> pytest tests/test_ttu_tupleset_parent_types.py -q   ->  4 failed, 7 passed
>     FAILED ::test_rc1_negative_arm_type_is_still_a_stored_ttu_parent
>     FAILED ::test_rc1_negative_arm_type_dropped_is_an_authorization_fail_open
>     FAILED ::test_rc2_star_stored_parent_on_derived_tupleset_is_a_ttu_parent
>     FAILED ::test_rc2_star_stored_parent_dropped_is_an_authorization_fail_open
> ```
>
> Those 4 land in ONE `verify.sh tests-tile:I/4` phase (structural partition, so which tile
> depends on collection order — find it, don't guess). **Every other phase must be green.**
> If you see red outside that list, it is YOURS, not ours — `git stash` and re-check.
>
> **Do NOT "fix" these by weakening them, and do NOT convert them to xfail**
> (`MAX_TESTS_XFAILED=0`, and `CLAUDE.md` prefers a positive pin). The 7 passing tests in
> that file are controls and must stay green through any fix.
>
> Baseline before this session, for diffing: `tests/` 773 collected, `formal/conformance/`
> 494, doc-counts block current, all ten phases green at `e136c8c`.

### 1. Fix the two TTU-tupleset divergences. PINNED RED (`d0010e2`), fix NOT done.

**★★ These are AUTHORIZATION FAIL-OPENS, not under-reports.** Read through a negated TTU
(`define access: [user] but not viewer from parent`) the graph **GRANTS what the oracle and
both set engines DENY** — `oracle=False graph=True sets=[False, False]`, verified by hand
for both causes. The general rule worth carrying: **a dropped TTU parent is a false NEGATIVE
under a positive TTU and a false POSITIVE under a negated one**, so probing only the
positive direction mis-classifies severity by one sign. That is exactly what the original
filing did. *(No deployment exists — the store is a plain callable API — so this is a
library correctness defect, not an exposed system.)*

**There are TWO independent root causes**, both dropping a STORED tupleset tuple that
`CLAUDE.md`'s rule ("TTU parents are STORED tupleset tuples, never computed membership")
requires the TTU to walk. A bounded exhaustive sweep (2,302,854 queries over 346 compiled
schemas) found **26 distinct minimized divergences and exactly these 2 causes** — so the
family is mapped and closed at two.

* **RC1 — CHEAP, ~1 line.** `zanzibar_utils_v1.py::_member_types` returns `walk(e.base)` for
  an `Exclusion`, so on `define parent: [folder] but not [doc]` the type `doc` never enters
  the compiled `parent_types` and `processor.py::tupleset_parents` drops the stored parent.
  Fix: union `walk(e.subtract)`; update its docstring, which encodes the same mistake.
  **`parent_types` is compiled once (`zanzibar_utils_v1.py:1761`) and frozen onto the plan
  node, which `processor.py` and `bulk_backfill.py` merely READ — so this one fix repairs
  the incremental AND bulk paths together.** Measured: `tests/test_bulk_build.py` 6 passed,
  byte-identity snapshots survive, 773+494 green with it applied.
* **RC2 — NOT CHEAP. Budget a design decision, not a filter tweak.** The `n.wildcard == ''`
  clause of the same filter drops a stored `T:*` parent when the tupleset relation is
  derived (no exclusion, no object wildcard needed). Deleting the clause **breaks admission
  parity** (`accept/reject divergence on add ('...','doc','*','parent','doc','d1'):
  graph=False set:py=True`) and widening it naively **crashes** at `index_v4/core.py:914`
  (`name=='*' and a non-empty wildcard must go together`). The star parent has to be
  **represented** — the set engine's `MemberSet.stars` algebra is the analogue to port — not
  merely admitted. RC2 **does** need the duplicated fix at `bulk_backfill.py:454` alongside
  `processor.py:320`.

**⚠ The mechanism recorded before this session was FALSE** and would have sent you rewriting
correct code. It said the graph "respects the boolean evaluation of the tupleset relation"
and the storage-leaf split "is not being honoured". Measured otherwise: the split IS applied
(`plan(doc,parent).leaves` = `parent.0` + `parent.1`, both `storage=True`), the write DOES
land on a storage leaf (`doc:d2#... -> doc:d1#parent.1`), `derived_stored_parents` DOES reach
it, and the read path never evaluates `parent`'s plan. The loss is **compile-time metadata
only**. Corrected in `docs/spec-deviations.md` 2026-08-10 (which keeps the wrong version
struck-through, deliberately, so the bad reasoning is visible rather than deleted).

**Why nothing caught it, all three measured:**
* **No invariant I1–I14 catches either, and I9 structurally CANNOT** — it re-runs
  `reconcile`, which reads the same wrong `parent_types` and agrees with itself. *The
  instrument shares its subject's defect.* Paranoia was ON and stayed green. A new
  compile-time invariant (checking `parent_types` covers every type admission accepts onto
  the tupleset's storage leaves, read from the emitted `RewriteFilter`s rather than from
  `_member_types`) was prototyped and validated RED-before/GREEN-after — worth landing.
* **The hypothesis campaign cannot reach the shape at ANY budget** — see item 1b.
* **The bulk-vs-incremental identity gate is BLIND to the RC2 direction**, proven with an
  instrument control: one-sided edits S1 (RC2 direction) and S3 (RC1 direction) both leave
  `tests/test_bulk_build.py` **6 passed — GREEN**, while control S2 (`return []`) reddens it
  2/6. So the gate reaches the function and the blindness is a CORPUS gap. The RC2 schema is
  a ready-made minimal corpus — pin it as part of the fix.

**When you fix it:** full phased gate (all ten) + the 6-seed fuzz sweep
(`--hypothesis-seed=` 7 19 31 53 71 97 over `test_hypothesis.py` and
`test_lookup_hypothesis.py`) — it is an algorithm change. Then push.

### 1b. Close the generator gap that let this through. STARTED 2026-08-10, incomplete.

`tests/test_hypothesis.py::schema_asts` hardcodes the TTU tupleset:
`ast = {('doc','parent'): Direct((Restriction('doc','...',False),))}`. **Every TTU in every
generated schema reads a plain single-type non-boolean `parent: [doc]`**, so the entire
"TTU over a structured tupleset" space is unreachable **by construction — not by seed luck,
and not fixable by raising `max_examples`.** `ci` runs `max_examples=12,
stateful_step_count=8`, and there is **no coverage assertion anywhere in the campaign**, so
"we fuzz broadly" is an unchecked claim. Yesterday's IIA instrument can't see it either —
its hypothesis leg samples tuples over four FIXED corpora, so a novel schema shape is
invisible to it too.

Scoped with the user 2026-08-10 as three pieces, all three approved:
* **(a) coverage cells, asserted** — enumerate the feature-cross cells, DERIVE the cell list
  from the compiler's own leaf kinds / AST node types rather than hand-writing it (a
  hand-written list is a future silent pass), record which cell each draw hits, assert every
  cell is hit, and distinguish "unreachable by design (compile-rejected)" from "unreachable
  by generator gap" — the second kind is what let these bugs through;
* **(b) swarm testing** — per run draw a random subset of features to ENABLE and generate
  deeply within it. Rationale: at a 12-example budget, uniform sampling over a rich grammar
  touches many features shallowly, the worst configuration for interaction bugs — and every
  bug this repo has found is an interaction bug;
* **(c) un-hardcode the TTU tupleset** so it is drawn from the same expression grammar.

⚠ **Constraint that will bite:** the candidate tuple pool must co-vary with the generated
schema. The existing generators guarantee schema-VALID candidates by construction, because
the graph admits a restriction-invalid tuple as a silent no-op while the set engine does
not. Widen the grammar without co-generating a valid pool and most draws are refused at
admission, so the sweep measures the REJECTION path **and reports green** — the house
failure mode. ★ **There is an unusually strong control available right now: the two bugs are
UNFIXED in the tree, so a correct new generator should go RED on them today and GREEN after
the fix. Use that as the sabotage evidence — it is a real defect, not a synthetic one.**

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

---

## Current status — 2026-08-10

**🔴 The gate is RED, deliberately, and there are TWO KNOWN LIVE FAIL-OPENS.** This
reverses the 2026-08-09 status below. See the red banner at the top of this file for the
exact expected-red inventory and why nothing else should be red. No `sorry` and no `xfail`
— the pins are positive assertions, so the red is a real failing test by design.

* **Known live correctness bugs: 2** (RC1, RC2 — plan item 1). Both pinned (`d0010e2`),
  neither fixed. Both have an authorization fail-open direction.
* **What changed vs. the 2026-08-09 "everything is green" line:** nothing regressed. These
  bugs are PRE-EXISTING — RC1 reproduces on a hand-written schema at `e136c8c` with no `.py`
  file touched. What changed is that they are now *known and pinned* rather than unnoticed.
* **The 2026-08-09 session's "everything is green" was true of the gate and false of the
  code**, which is the whole lesson of plan item 1b: the gate's generators could not reach
  these shapes at any budget, so green meant "we did not look here", not "there is nothing
  here". Do not read a green gate in this repo as an absence of divergence until 1b lands.

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

---

## Open-TODO board

### Active work

- [x] ~~**★★ (2026-08-09) — A LIVE ANSWER-LEVEL DIVERGENCE.**~~ **FOUND, ADJUDICATED AND
      FIXED the same day** (`58b51a8` pin-red, `310fbcb` IIA-red, `c042056` fix). The graph
      index under-reported the **OWC × star-parent × TTU cross**. Three
      tuples on `tests/fga_schemas/owc_star_ttu.fga`:

      ```
      (user:u1, editor,  folder:f1)   # any tuple that makes folder:f1 exist
      (user:u1, viewer,  folder:*)    # OBJECT-wildcard grant
      (folder:*, parent, doc:d1)      # SUBJECT-wildcard tupleset
      check(user:u1, viewer, doc:d1): oracle=True set:py=True set:roaring=True GRAPH=False
      ```

      **A false negative** — it fails closed, so it is not a security fail-open, but it
      breaks the repo's central contract (two backends, identical semantics). **Pre-existing:**
      reproduces at `6d3c540` with byte-identical Python; the session that found it changed
      no `.py` file. **Found by** the hypothesis lookup campaign on a generated walk.

      **Root cause, measured:** `index_v4/wildcard.py::_ensure_bridges` bridges
      `w_all(T,p) → concrete → w_any(T,p)` only through an interned node of **shape `(T,p)`**,
      while `tests/oracle.py::instances` witnesses ∃ with any **entity of type `T`**. Vary
      only the witness relation and the graph flips: `folder:f1#editor` → False,
      `folder:f1#blocked` → False, `folder:f1#viewer` → True. The two sides read
      `wildcard-materialization-spec.md` §3.4 differently and **that asymmetry is written
      down nowhere** — adjudicate which reading is intended BEFORE assuming the graph is
      the side to change.

      **Pointer for the fix:** the set engine already has the analogue the graph lacks —
      `setengine/engine.py:1476-1480`, "the star-parent cross for the triple combo owc x
      star-parent x TTU where NO concrete `(T, X, r')` is interned".

      **Pinned deterministically** by `tests/test_owc_star_parent_cross.py` — 2 red pins +
      1 green positive control, a positive pin and NOT an xfail, per `CLAUDE.md`.
      ⚠ **Second finding, arguably the more important one:** before that file existed the
      shape was reachable but essentially never drawn (`max_examples=12`,
      `stateful_step_count=8`, ~50-tuple pool) — **the gate was green by seed luck**, the
      house failure mode by name. *The hypothesis campaign's green is a sample, not a
      proof, and nothing in the gate says so.* Consider whether that deserves its own fix.

      **The fix:** the crossing middle now tracks the **entity**, not the node —
      `WildcardIndex._ensure_entity_middles` / `::_sync_entity_middles`, with the property
      lifted into `index_v4/invariants.py` as **I14** so paranoia aborts the first innocent
      write if a path stops maintaining it. `_ALLOWED_DIRECT` was NOT relaxed; ∀⇒∃ stays
      strict *structurally* rather than by a counter. Sabotage: making
      `_ensure_entity_middles` a no-op leaves **I3 green and only I14 red**.

      **Two more findings that correct live documents:**
      * **The formal layer could not have caught this, by construction.** Lean's in-bridge
        test keys on a *literal* `T:*#p` restriction; Python's `bridged_in_shapes` also
        folds in star-tupleset through-shapes. So Lean's crossable set is exactly the
        compile-rejected set — empty among admissible schemas — and the arm where the bug
        lived has no Lean counterpart. Filed as a fragment boundary,
        `formal/CORRESPONDENCE.md` §7.3. **Do not read "the wildcard write path has a Lean
        twin" as "it is covered".**
      * **A live comment was refuted.** `zanzibar_utils_v1.py::wildcard_userset_restriction_shapes`
        claimed the `owc_star_ttu` class is "oracle-correct and unanimous on both
        backends". It was not. Corrected in situ; the narrowing it justifies still stands
        on its own argument.

      Full filing, including the five prior-art items checked and why none covers this:
      [`docs/spec-deviations.md`](docs/spec-deviations.md) 2026-08-09.

- [x] ~~**★★ (2026-08-08) — THE `rewriteClosure` DEDUP LEG.**~~ **LANDED
      2026-08-08 (`911c887` corpora-red, `c488a2f` fix). `CORRESPONDENCE.md` §7.2 item 6
      is CLOSED; leg 7's step 2b is DISCHARGED.** All ten gate phases green. Kept visible
      for one cycle because three of its outcomes correct documents that are still live:
      * **The sizing held exactly** — the count stack is list-generic, so `untOccCount`/R3/R4
        needed ZERO proof rework. **16 sites repaired, not the pre-measured 15**: the extra
        one consumed the definition through term-level defeq, so it was invisible to a grep
        for the TACTIC `unfold rewriteClosure`. *Grep the identifier, not the tactic.*
      * **★ The over-count cost RUNTIME, which nothing predicted.** Every prior write-up
        treated it as read-invisible bookkeeping; in fact `reconvergent_derived` blew
        zcli's 120 s remove-stream budget before the fix and passes after it (derived-arm
        multiplicity `185 → 52`). The masked value was also `lean=185`, not the scope doc's
        predicted `lean=10` — that figure was for a ONE-write probe.
      * **★ The sabotage found a real limitation, not a confirmation.** The two new corpora
        do **NOT** catch the WRONG fix (a global `admitEdge` presence dedup): every
        multiplicity in them is 1, so it leaves them green. `nary_union` catches that one,
        at `3 → 1`. They guard OPPOSITE errors and neither substitutes for the other —
        recorded in `corpus.py` so nobody deletes `nary_union` believing reconvergence is
        now covered. The `List.dedup` last-occurrence risk was probed and retired
        (topological on all three probe schemas, with a positive control).
      Detail: `formal/history/PROOF_STATUS.md` 2026-08-08b.

- [ ] **~~START HERE~~ (superseded — kept for the scope pointers below)** This is the
      original filing of the leg that landed above; everything else on this board is either
      deferred (leg 7 proper) or a design decision already made.

      **What it is.** `CORRESPONDENCE.md` §7.2 item 6: the Lean model's `rewriteClosure`
      does not dedupe where Python's `RuleSet.apply` does, so on a **reconvergent** schema
      the model over-counts edge multiplicity. Filed 2026-07-28 as "no corpus exercises it
      today"; **measured live 2026-08-08 and adjudicated MODEL-side.**

      ```
      a := b or c ; b := d ; c := d ; d := [user]   (one write: alice@d)
        alice -> doc:d1#a    lean=2  python=1   <== untainted arm, P3 compares EXACTLY
      ```

      **It is a UNIT divergence, not a retirement bug.** Both sides retire correctly
      (five-sequence add/remove battery agrees on presence; answer parity 0 mismatches over
      56 and 108 queries). Python counts **live raw tuples**; the model counts **derivation
      paths** — measured `1 → 2 → 4` for zero/one/two chained diamonds, fuel-stable, i.e.
      the model's ref count grows with SCHEMA SHAPE.

      **Why the model is the wrong side (house rule 5, and it is sharp):**
      `RemoveOccCount.lean`'s header *asserts Python's unit* — "`List.count (a,b)` IS the
      model's `direct_edge_count`" — which is FALSE on any reconvergent schema, while the
      same file's attack bullet already says so. **The file contradicts itself and R3/R4's
      faithfulness claim rests on the wrong half.** Fixing Python is not available: its
      `processed` worklist dedup is the TERMINATION mechanism (`a: [user] or b ; b: a`
      compiles — only *derived* cycles raise — and loops forever without it).

      **Why it is cheap — the key finding.** The count machinery is **list-generic**:
      `count_removeLoggedRules` opens with `generalize rewriteClosure S t = us`, and
      `count_foldl_writeDirect` is `∀ (us : List Tuple)`. So `untOccCount`, R3
      (`reachedByW3d2E_untOccCount`) and R4 (`RemoveConfluence`) need **zero proof rework** —
      values change, meaning improves. Only **15 `unfold rewriteClosure` sites** (mechanical,
      via one new `mem_rewriteClosure_iff`) and **2 list-equality sites**
      (`rewriteClosure_derived_eq_seed`, `…_nk`) need redoing.
      **Minimal-diff shape:** rename the current def `rewriteClosureRaw`, define
      `rewriteClosure S t := (rewriteClosureRaw S t).dedup`, add the one membership lemma.
      `DecidableEq Tuple` exists (`Core/Refs.lean`) and `List.dedup` is already used once
      (`Core/Store.lean`), so no new idiom.

      **⚠ ORDER WITHIN THE LEG: corpus FIRST (red, attributable, recorded), then the fix
      (green).** Corpus alone leaves a red gate; fix alone leaves the fix unexercised.
      Two corpora, both `SCHEMAS` + `GRAPH_FRAGMENT` + `_THEOREM_BACKED`,
      `_EXPECTED_SPLIT (23,0) → (25,0)`: `reconvergent_diamond` (taint set empty) and
      `reconvergent_derived` (`viewer := e but not banned` over a reconvergent base — this
      is the one that carries the leg-7 payload, since after the `writeDirect` fork its
      currently-masked `lean=10 python=1` moves onto a leaf node in the exactly-compared
      untainted arm).

      **⚠ The leg's one real risk, unverified:** Mathlib's `List.dedup` keeps the **LAST**
      occurrence, so write order shifts. Measured topological on both probe diamonds, but
      that is luck rather than a theorem. If a proof turns out order-sensitive, a
      first-occurrence dedup is the fallback.

      **Owed regenerations** (deliberate, each with the reason written): the definition pin
      (`rewriteClosure`'s row moves; the rows that merely NAME it stay byte-identical),
      `derived_arm_multiplicity.json`, `FINAL_REVIEW.md`'s counts block, and `zcli`.
      **Prose corrections owed:** `RulesWrite.lean`'s "duplicates are harmless (reachability,
      not counts)" — the sentence being retired — plus `RemoveOccCount.lean`'s header and
      attack bullet, `ReconcileDiff.lean`'s multiset claim, `Audit.lean`, and
      `CORRESPONDENCE.md` §7.2 item 6 (which now carries the adjudication).

      **Full adjudication, corpus design, and the exact predicted red:**
      [`formal/history/leaf-family-split-scope-2026-08-05.md`](formal/history/leaf-family-split-scope-2026-08-05.md)
      §10.5 (+ §10.3 for why it blocks leg 7), `formal/history/PROOF_STATUS.md` 2026-08-08.

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

- [ ] **Vendor a corpus of REAL OpenFGA schemas, crawled from the wild** (requested
      2026-08-10; the user will pick this up later — do not start it unasked).
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

- [x] ~~**`TupleSource.__init__` is not atomic on PostgreSQL**~~ — **CLOSED; this entry
      was STALE and said so in a way that mattered.** It claimed "the single remaining
      strict xfail in the tree … declared in `verify.sh`'s `MAX_TESTS_XFAILED=1`".
      Verified 2026-07-29 against the code: `verify.sh` carries
      **`MAX_TESTS_XFAILED=0`**, `tests/test_postgres_ha.py` records that
      `test_open_instance_races_a_concurrent_commit` **became a plain pin** when
      `TupleSource._consistent_rebuild` landed, and that helper
      (`connectedstore/source.py`) is used by BOTH `__init__` and `refresh_evaluator` —
      the two sites the finding named. Nothing in the tree is xfailed. Kept visible
      rather than deleted because for two days this was the one entry that would have
      made a reader believe a live authorization-adjacent bug was open.
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
