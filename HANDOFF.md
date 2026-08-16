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

## ★★ START HERE (2026-08-16)

> # 🟢 THE GATE IS GREEN. Known live correctness bugs: 0.
>
> All ten phases (`lean` → `conf-tile:1/5`…`5/5` → `tests-tile:1/4`…`4/4`) PASSED
> 2026-08-16 on the leg-7 4c-i tree (Lean model + docs + one new refusal test — no Python
> *behaviour* changed, so the 2026-08-14 3-seed fuzz sweep still stands). The 2026-08-10
> fail-open family (RC1 `ed46e54`, RC2 2026-08-11) stays closed.
>
> **★ NO FIGURES IN THIS BANNER, deliberately — read them from
> [`formal/FINAL_REVIEW.md`](formal/FINAL_REVIEW.md)'s generated counts block.** This block
> used to carry its own copy, and on 2026-08-14 all three of its numbers were stale
> (anchors 432 → 464, tests 846 → 879, audits 493 → 501). That is `ZT-P3-5` recurring in
> the *first thing every session reads*. The gate enforces `-ge` FLOORS, so a count quoted
> in prose is not merely stale, it is **unenforced**. Rule 3b at the bottom of this file
> has said so since 2026-07-29; this banner was violating it.
>
> **If you see red, it is yours** — `git stash` and re-check. Four standing footguns:
> * A pytest/verify exit code piped through `tail`/`tee` reports the **PIPE's** status.
>   This bit the 2026-08-10 session (a genuinely `4 failed` run reported exit 0) and it
>   bit again on 2026-08-14. Use `cmd > file 2>&1; echo $?` and **read the `PASSED` line**.
> * `HYPOTHESIS_SEED=N` does nothing; only `--hypothesis-seed=N` works.
> * `MAX_TESTS_XFAILED=0` — a divergence gets a positive pin, never an xfail.
> * `MIN_CONF_ALL` / `MIN_TESTS_ALL` have **zero headroom**; deleting one test is red.

### What landed 2026-08-16 (most recent session)

**Leg 7 step 4c-i is IN with a ZERO recompile cone; the allocation it rests on was refuted
THREE more times first — once by an instrument that was itself blind; and `ttuStarFree`
part (iv)'s standing blocking question is ANSWERED.**

* **★★ Step 4c-i — the leaf-provenance rule layer** (`GraphIndex/LeafRules.lean`, NEW).
  `leafRewrites` supplies the half `schemaRewrites`' taint filter omits: each derived key's
  CLOSURE leaves compile to rewrite rules targeting the **minted leaf name**, exactly as
  Python's `_emit_leaf_expr` → `_rewrite_rule(expr, object_type, leaf)`. Additivity is
  **proved**, not observed (`schemaRewrites_leafRewrites_disjoint`: untainted rules target
  declared dot-free names, leaf rules target minted dot-carrying ones), and
  `writeRulesRaw_untaintedSchema` says the same at the write level. Measured before it was
  written: **50/50 schemas, 0 mismatches, 32 with a non-empty leaf rule set.**
  **★ Scope-doc §11.6's cost cell is REFUTED** — it sized 4c-i as "the full GraphIndex
  tree, ~double the Cascade cone", true only of an *edit* to `schemaRewrites`. As an
  extension downstream of `RulesWrite` the cone is **one file**, and the
  `Cascade → LeafRules` import 4c-ii needs is cycle-free. **Budget the cone once, at 4c-ii.**
* **⚠ THE ALLOCATION WAS WRONG THREE MORE TIMES**, all caught before 4c-i was built on it:
  Python **merges** a maximal pure subtree (`(a or b) but not banned` → `r.0={a,b}` /
  `r.1=banned`, not three leaves, storage always allocated first); a tainted **userset**
  restriction gets its own storage leaf (reachable from the LIVE fixture
  `tests/fga_schemas/userset_over_derived.fga`); and the n-ary union **spine**.
* **★★ THE TRANSFERABLE FINDING — a new member of the mirror-instrument family**, written
  up in [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md). The first two fixes
  were validated by transcribing the Lean model into Python and diffing: *"82/82 derived
  keys, 0 disagreements"*. That transcription consumed Python's **n-ary** AST — but Lean
  never sees it, because `formal/conformance/encode.py::_fold_binary` **LEFT-FOLDS**.
  Re-run over the binarized tree: **1 disagreement, on `nary_union_derived4`, which is IN
  `GRAPH_FRAGMENT`.** *A transcription of the right rule over the wrong input
  REPRESENTATION is the mirror instrument with extra steps.* And the second, genuinely
  independent instrument (744/744, three positive controls) was **structurally incapable**
  of catching it — it maps closure leaves to `none`. Two green instruments, one shared
  blind spot.
* **★★ A LIMIT OF THE MODEL'S AST that leg 7 must now carry.** `Core/Schema.lean` justifies
  left-folding n-ary unions by associativity+commutativity — true of `sem`, **false of the
  leaf ALLOCATION**. Measured: `a or b or safe` → 2 leaves, `(a or b) or safe` → **1**, and
  the encoder maps both to the same `Expr`. The model is faithful to the FLAT form (the only
  one any corpus writes); the other shape is now **refused mechanically**, not by a doc
  warning, at
  `formal/conformance/test_conformance_state.py::test_no_corpus_nests_a_pure_union_inside_an_impure_one`
  (sabotage-verified). Faithful-to-both needs an n-ary `Expr` — a trust-root change.
* **★★ `ttuStarFree` part (iv) is UNBLOCKED** (`GraphIndex/TtuStarWide.lean`, NEW,
  additive, no caller). The board has carried "(iv) has an unanswered question that could
  block it outright — is the widened predicate still decidable by a boolean function?"
  since 2026-08-14. **Answer: NO-BLOCK, machine-checked.** `TtuStarFree` is a bounded
  quantification over finite lists; the widening only weakens the body; the new conjunct
  `Schema.isSubjectWildcardUserset` is **already `Bool`-valued**. So `ttuStarFreeWB` decides
  `TtuStarFreeW` and `removeGateB` widens by the same textual edit. Proved a genuine
  weakening *and* strictly wider at a store, with two sabotages reddening **disjoint** pins
  (strictness vs soundness). ⚠ `W4Fragment.ttuStarFree` is UNCHANGED — the 2026-08-10
  refutation stands until part (ii) materializes the bridge.
* Audits 520 → **573**, anchors 471 → **497**; headline statements 38/38 and definitions
  155/155 **UNMOVED**. Also re-measured: *"17 of 25 corpora mint indices 1 AND 2"*
  overstated the index-2 breadth 3.4× — index ≥1 in 17 of 25, index 2 in **5**.

### What landed 2026-08-15

**Leg 7 4c-pre: the briefed step 4c was REFUTED by measurement before its 36-module cone
was paid, and the addressing layer under it landed measured-correct instead.**

* **★★ The kill (attack-first, before coding):** enumerating the 76 P6-dropped edge rows
  per corpus shows **leaf indices 1 and 2 in 17 of 25 `GRAPH_FRAGMENT` corpora** — every
  non-first boolean arm gets its own leaf — and a raw write **fans out to every matching
  storage leaf**. So the landed `rawWriteRel` (single target, hardcoded index 0) could
  never meet the landing criterion, in index OR arity. Worse structurally: the dropped
  rows are mostly RULE-copied closure leaves whose index depends on **which arm produced
  the copy** — provenance `rewriteClosure` does not carry — so **4c is not a caller
  re-point at all**; the rule layer must mint leaf-indexed targets first. Revised plan:
  scope-doc **§11.6** (4c-i rules-with-provenance → 4c-ii caller re-point + (α) row move,
  4c-ii + 7 still co-landing).
* **What landed in Lean (`GraphIndex/Leaf.lean`, reworked while still unwired — the cheap
  moment):** `persistedLeaves` (the measured pre-order allocation; derived refs and
  non-pure TTU arms consume no index), `leafPublic`/`publicOfLeaf` (the (α) leaf→public
  map, **index-agnostic by construction**; `publicOfLeaf_rawWriteRels` is the feeder
  `affectedKeys` will consume), `rawWriteRels`/`rawWriteTuples`/`writeDirectRaw` (the
  filtered fan-out). Every measured Python fact is a `decide` pin (`swU_routes` =
  §11.5's `approver.2`; `swF_fanout`; `stP_leaves`/`stD_leaves`; `swX_skip`), **five
  sabotages run with attributable reds and green controls** — including the `".0"`-
  stripper run where the index-0 pin stayed green, proving an index-0-only pin would
  have been vacuous. Audits 501 → **520**; headline statements/definitions UNMOVED.

### Earlier sessions — archived 2026-08-16

The full "What landed" blocks for **2026-08-11** (the RC2 fix, the bulk-corpus gap, the
compile-time TTU invariant, the compiler rough edge, the floor raise) and **2026-08-14**
(the §11.3 fork decision, `ttuStarFree` part (i), the two method write-ups) are in
[`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md)
§"Retired 2026-08-16". Their durable output is already in the live docs: §1 below keeps
the severity-sign rule and the mirror instrument, and `docs/sabotage-procedure.md` keeps
the INERT-change lesson and the fan-out runbook pointer. ⚠ One line in the 2026-08-14
block is now FALSE — "(iv) carries a possibly-blocking decidability question" was
answered NO-BLOCK on 2026-08-16.
### ★ THE SEQUENTIAL PHASE PLAN (written 2026-08-16, at the user's request)

Every remaining board item, ordered, with dependencies and an honest per-phase size. **"1
session" means one agent session ending on a green ten-phase gate.** Phases are ordered so
that nothing later is invalidated by something earlier; where two are independent, that is
said.

| # | phase | depends on | size | notes |
|---|---|---|---|---|
| **P1** | ~~leg 7 **4c-i** — leaf-provenance rules~~ | 4c-pre | ~~1 session~~ | ✅ **DONE 2026-08-16.** Zero cone. |
| **P2** | ~~`ttuStarFree` (iv) decidability question~~ | — | ~~½ session~~ | ✅ **DONE 2026-08-16.** NO-BLOCK. |
| **P3** | leg 7 **4c-ii + step 7**, one commit | P1 | **2–3 sessions, the big one** | Caller re-point + (α) row move + `affectedKeys` via `publicOfLeaf` + `FoldAdmits`/`foldAdmitsB` in lockstep + delete P6 + regen both goldens. **Cannot be split** — P6 is Python-side-only. Criterion: `P6 76 → 0`, `compared 189 → 265`. |
| **P4** | leg 7 **4b** — the leaf-probe ↔ `directLeaf` bridge | P3 | 1 session | Scope doc §7; the prerequisite filed as "widen `evalE` first" does not exist (2026-08-05 finding). |
| **P5** | leg 7 **5 + 6** — `Inv.negEdgeFree` under leaf routing, then retire the T2a caveat | P4 | 1–2 sessions | The attack probe returned NO-KILL (§9.1), so this is effort, not risk. ⚠ **`Sd`/`Td` CANNOT be the witness** (`negEdgeFree` is vacuously true there) — use D.3's wildcard-carrying schema (§9.3). Closes `ZT-P3-1` for T2a. |
| **P6** | `ttuStarFree` **(ii)** — bridges on the rule-routed write path | independent of P3–P5 | 1–2 sessions | The step that actually **materializes the edge** and closes the 2026-08-10 counterexample. Compose `ensureInBridges`/`ensureBridges` into `writeRules`/`writeLoggedRules`. Everything else in this leg is inert until it lands. |
| **P7** | `ttuStarFree` **(iii) + (iv)** — re-prove the 5 consumed sites, then widen the gate | P6 | 1–2 sessions | (iii)'s cost is 5 consumed sites in two modules (`RulesBareStar`, `RestrictBase`) needing two structures that do not exist (a through-shape carrier weakening `StarSeed`; a bridge-completeness clause on `ReachedByRulesAdmitted`). (iv) is then mostly the textual gate edit `TtuStarWide.lean` already demonstrates. |
| **P8** | **`W4WitnessSelfRef`** (board B2) | — | ½–1 session | `self_flag` is adjudicated as HOLDING; write the witness with two non-vacuity instruments (the plausible failure is a tautological CLONE of `W4Witness.Sx`). Model on `W4Witness`, not `W4WitnessDirect`. |
| **P9** | **the remove-gate exclusion** `_REMOVE_EXCLUDED = {direct_arm_exclusion}` (board B2) | P5 helps, not required | 1 session | Needs a `storeValidRulesDB` decision procedure + soundness lemma + a widened `remove` constructor. Note leg 4's inward conversion does **not** run backwards. |
| **P10** | **the scope-audit re-run** (board item 4) | — | 1 session | ★ Do **not** start from zero: 279 agent transcripts survive under `…/subagents/workflows/wf_f8c85180-b74/`. Mine first, re-dispatch ~15 hand-curated items. Read `docs/subagent-fanout-runbook.md` first. |
| **P11** | **the fixture-TRIPLE question** (subsumed `.fga` fixtures) | — | ½ session | Score triples over the five `KNOWN_SUBSUMED` fixtures vs the rest. Settles keep-or-delete. ⚠ Do not extend `test_fixture_earns_its_place` corpus-wide. |
| **P12** | **the severity-sign revert probe** (board item 6) | — | ½ session | Revert `c042056` in a scratch worktree, add a negated-TTU consumer. **A prediction, not an observation** — do not propagate it as measured until it is. |

**Ordering notes.** P3 is the critical path and the only multi-session phase; P6/P7 are a
fully independent leg and can run in parallel with P3–P5 by a different session. P8/P10/P11/P12
are independent of everything and are the right pick for a short session.

**P13 — CORRESPONDENCE claim-rot detection** (the board item below the E-chain one) is independent of every phase above and is the only one that adds a NEW gate check rather than a proof. Build (B) + (C); it needs its own sabotage and a full ten-phase re-run. **P3 is the only
phase that regenerates a golden** — everything else in leg 7 and the `ttuStarFree` leg so
far has been additive with statements and definitions unmoved.

### Still open — updated 2026-08-16

**What moved 2026-08-16:**
* **Leg 7 step 4c-i LANDED** (`GraphIndex/LeafRules.lean`) — and the cost went DOWN, not up:
  §11.6 sized it as ~double the Cascade cone, but as an extension downstream of
  `RulesWrite` the recompile cone is **one file**. The remaining expense is concentrated in
  **4c-ii + 7**, which must co-land. See item 5 and scope-doc **§11.7**.
* **The allocation 4c-i rests on was refuted three more times first**, once by an instrument
  that was itself blind — including a wrong model of the in-fragment corpus
  `nary_union_derived4`. Audits 520 → **573**.
* **`ttuStarFree` part (iv) is UNBLOCKED** — the decidability question is answered NO-BLOCK
  and machine-checked. Item 3.

Item 4 (the scope-audit re-run) is untouched and not blocking. **Item 3 moved on
2026-08-16: part (iv)'s decidability question is ANSWERED (NO-BLOCK) and the predicate +
its decider are machine-checked in `GraphIndex/TtuStarWide.lean`; parts (ii) and (iii)
remain.**
Item 6 is a one-question optional loose end from the closed arc. **Item 2 (the two
UNVERIFIED audit leads) was CLOSED 2026-08-14** — both reproduced, neither leaves a live
bug; read its residue before touching the zcli driver or `ttuDirect`.

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

### 2. ~~Verify or discard two UNVERIFIED claims from the failed audit.~~ CLOSED — archived 2026-08-16.

Both were reproduced from scratch on 2026-08-14 with attribution and positive controls.
**Neither leaves a live correctness bug; do not re-open either.** Full text, including the
`zcli` mode=graph fail-CLOSED finding and the `ttuDirect`-was-RC2 re-measurement, is in
[`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md).

Three things survive as live constraints rather than history:
* ⚠ **Do NOT lift `ttuDirect` in Lean** (the audit's recommendation #3), consistent with
  item 3 below and `CORRESPONDENCE.md` §7.
* **The one genuinely open descendant, and it is its own leg:** a driver-side fragment
  pre-check needs a **DECIDABLE `W4Fragment`**, and none exists (no `admissionB`-style
  boolean). Nothing is blocked meanwhile. ★ Note the contrast with `ttuStarFree` part
  (iv), whose analogous decidability question turned out to be answerable (2026-08-16) —
  so this one is worth actually attempting rather than assuming.
* **The audit's primary record survives in the session journal**, not the repo:
  `~/.claude/projects/<this-project>/…/subagents/workflows/wf_f8c85180-b74/` (279 agent
  transcripts). That is also item 4's head start.
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

**★ PART (i) LANDED 2026-08-14.** `UsStarWrite.lean::Schema.isStarTuplesetThrough` is the
twin of `derive_schema_info`'s SECOND loop, and `Schema.isSubjectWildcardUserset` is now
the disjunction of both loops, as Python has always been. The predicate's own docstring
used to declare the through-shape out of scope — **that declaration WAS the hole.**
* ⚠ **It is INERT and does NOT close the counterexample.** `writeRules`/`writeLoggedRules`
  are bridge-free folds that never call `ensureInBridges`; **part (ii) materializes the
  edge**. Read part (i) as "the definition-level gap is closed, the machinery-level gap is
  not".
* ★ **Being inert is exactly why it carries six `decide` pins.** The narrowest plausible
  sabotage — short-circuiting `isStarTuplesetThrough` to `false` — reddens *nothing else in
  the tree*. It reddens two of the pins while the four controls stay green, so the red is
  attributable. Literal output is in the section docstring.
* It also converted a **live correctness claim** from prose to a theorem: `CORRESPONDENCE
  .md`'s `ZT-P5-NEW` rested partly on "the definition scopes the through-shape out", which
  part (i) falsified; `isStarTuplesetThrough_of_pureDirect` now carries it, **for W1c only**.

**Remaining: (ii), (iii), (iv).** ✅ **(iv)'s blocking question is ANSWERED 2026-08-16 —
NO-BLOCK, and it is a theorem, not an argument.** `GraphIndex/TtuStarWide.lean`:
`TtuStarFree` is a bounded quantification over two FINITE lists (the store and
`schemaRewrites S`), the widening only weakens the BODY from `¬(match)` to
`match → bridged`, and the new conjunct `Schema.isSubjectWildcardUserset` is **already
`Bool`-valued and kernel-computable** (part (i)). So `ttuStarFreeWB` decides `TtuStarFreeW`
(`ttuStarFreeWB_iff`) and `removeGateB` widens by the same textual edit
(`removeGateBW_gate` still supplies every hypothesis). It is proved a genuine WEAKENING
(nothing driven today stops being driven) and STRICTLY wider at a store, with two sabotages
reddening disjoint pins — S12 (exemption dropped) proves strictness, S13 (exemption made
unconditional) proves soundness. **(iv) is now schedulable on effort alone; do not defer it
on decidability again.**
⚠ **`W4Fragment.ttuStarFree` is UNCHANGED and must stay so until part (ii) lands** — the
2026-08-10 refutation stands, because `writeRules`/`writeLoggedRules` never call
`ensureInBridges`, so the in-bridge the widened predicate assumes exists is not
materialized. `TtuStarWide.lean` is the SPECIFICATION and the decidability answer, not the
lift.
**The real cost is not the occurrence count.** Re-measured 2026-08-14: **163 occurrences in
18 modules** (this file said 162; `RestrictBase` is 19), split **124 hypothesis-carry / 5
genuinely CONSUMED / 5 bundle-or-decider / 29 prose** — 97% mechanical. The 5 consumed sites
live in just two modules (`RulesBareStar`, `RestrictBase`) and need **two structures that do
not exist yet** (a through-shape carrier weakening `StarSeed`, and a bridge-completeness
clause on `ReachedByRulesAdmitted`). That is where the time goes; it is not blocking.

### 4. Re-run the scope audit properly — hand-curated, ~15 items.

The 2026-08-10 fan-out died at 32 of 278 agents with **verify and synthesis never running**.
Read [`docs/subagent-fanout-runbook.md`](docs/subagent-fanout-runbook.md) BEFORE launching
another one — it is written from this failure.

★ **It does NOT have to start from zero** (found 2026-08-14, while closing item 2): all
279 agent transcripts survive in the session journal under
`~/.claude/projects/<this-project>/…/subagents/workflows/wf_f8c85180-b74/`, including the
completed structured output of agents whose findings never reached any document. Mine
that before re-dispatching — two of the transcripts settled item 2 without re-running the
audit at all. It also shows the failure mode directly: the dispatched verifiers are 4
lines each, prompt in and nothing out. The two rules that would have saved it: a
machine sweep DISCOVERS candidates but must never DEFINE the fan-out (96 of its items were
parser error messages, which exclude nothing admissible), and every agent must persist its
result to its own file so a dead run still leaves its findings on disk.

### 5. Leg 7 — steps 3/4a/4c-pre/**4c-i** are in; next is **4c-ii, co-landing with 7**.

Steps 3 and 4a landed 2026-08-09; the §11.3 fork was decided (α) 2026-08-14; 4c-pre landed
2026-08-15; **4c-i landed 2026-08-16** (`GraphIndex/LeafRules.lean` — the leaf-provenance
rule layer, zero recompile cone). Scope-doc **§11.7** is the current plan; §11.6's cost
cell is refuted and its index-breadth figure is stale.

**4c-ii is the expensive step and it CANNOT land alone** — it must co-land with step 7
(retire P6), because P6 is a Python-side-only filter. Its checklist:
* re-point `Cascade.lean::GraphState.writeLoggedOne` / `::removeLoggedOne` and
  `RulesWrite.lean::GraphState.writeRules` at `LeafRules.lean::GraphState.writeRulesRaw`
  (import `Cascade → LeafRules`; **verified cycle-free 2026-08-16**);
* move the `Delta` row to the leaf per branch (α), keeping **`d.leaf = true` as the LEADING
  conjunct** of the own-key guard (PROOF_STATUS 2026-08-14's binding condition — three
  one-line `rw [hleaf]; simp` discharges depend on it);
* feed `affectedKeys`' own-key branch through `Leaf.lean::publicOfLeaf`
  (`publicOfLeaf_rawWriteRels` is the feeder lemma, already proved);
* move `RulesComplete.lean::FoldAdmits` / `Exec.lean::foldAdmitsB` in lockstep or
  `graphRunAux` admit-checks a different edge from the one it writes. ⚠ Both are
  `headline_definitions.txt` literal-body pins — expect a deliberate golden regen;
* delete P6 from `extractor.py::_edge_projection` in the SAME commit and regenerate
  `FINAL_REVIEW.md`'s counts block.

**Landing criterion, re-derived 2026-08-16 from the generated block (never from prose):**
`dropped by P6` **76 → 0** and `compared against Lean` **189 → 265**.

### 6. Optional, open question — NOT a finding. (Promoted from the closed fix list.)

The 2026-08-09 sibling (`docs/spec-deviations.md`) carries the same "it fails closed, so it
is not a security fail-open" wording, and the severity-sign rule above (a dropped TTU parent
inverts sign under a negated TTU) **predicts it inverts too**. It was never re-tested,
because it is fixed and testing it means reverting. If you want it settled: revert
`c042056` in a scratch worktree and add a negated TTU consumer. **Do not propagate the
prediction as measured fact** — it is a prediction from a rule, not an observation.

---

## Status run — 2026-08-11 (historical; the live status is the banner at the top)

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

- **LEG 7 STARTED HERE — steps 3 and 4a went IN** (2026-08-09, `8291c3a` + `41b7029`).
  `formal/lean/ZanzibarProofs/GraphIndex/Leaf.lean` is new: leaf addressing,
  the raw-write routing, the forked write `writeDirectRaw`, and the distinctness linchpin.
  Additive — headline statements 38/38 and the definition pin 155/155 **unmoved**.
  ⚠ **The raw-write half of this bullet was SUPERSEDED 2026-08-15** — `rawWriteRel`'s
  single index-0 target was measured wrong and is now `rawWriteRels` (a fan-out); see the
  banner. The addressing and linchpin halves stand.
  **The leg is NOT finished**; steps 4c-i, 4c-ii, 4b, 5, 6, 7 remain. Three things a next session
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

**History moved out again 2026-08-16:** the "What landed" blocks for 2026-08-11 and
2026-08-14, board item 2 (both audit claims adjudicated), the completed
`_any_residue_reference` item, and the completed OpenFGA-corpus item — 288 lines — are in
[`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md)
§"Retired 2026-08-16". **The METHOD from each was kept in the live docs, not archived with
the status** — notably *"a teardown test is not a delete test"*, which is now a named
subsection of [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) rather than a
bullet inside a ticked checkbox.

**History moved out again 2026-08-11:** the whole RC1/RC2 arc as briefed while open (the
divergence filing, the discharged fix list, the generator-coverage leg) plus four completed
board items are now in
[`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md).
⚠ **Status lines inside an archive are frozen as-of-then, and several in that one are now
wrong** (it still says "still owes the fuzz sweep", "when you fix it", "reported not
fixed") — its header says so. The live end state is the banner + "What landed 2026-08-16" at the top of this file
(the 2026-08-11 block itself was archived on 2026-08-16). **The rule this file keeps re-learning: archive the STATUS, keep the METHOD.**

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

- [ ] **Execute the handoff-system redesign migration (designed + user-approved
      2026-08-16; THIS FILE gets rewritten by it).** The design and the ordered step
      plan: [`docs/handoff-redesign-2026-08.md`](docs/handoff-redesign-2026-08.md)
      (§9 steps 2–11; step 1 is done, step 12 is its own later session). The survey
      evidence it consumes: [`docs/history/handoff-migration-map-2026-08.md`](docs/history/handoff-migration-map-2026-08.md).
      User decisions are recorded in §11 of the design — do not re-open them.

- [ ] **Perf round 6 — an 18-item CANDIDATE worklist exists (audited 2026-08-15; nothing
      landed, nothing MEASURED).** A 24-agent audit of both backends, every finding
      adversarially verified against the code: full record — verbatim evidence, fix
      sketches, verdicts, corrections, Lean-impact notes, plus 16 unverified lower-ranked
      leads — in [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md)
      (the worklist pointer in [`docs/perf-next-round.md`](docs/perf-next-round.md) is
      updated). Per that file's reopening rule, every item needs a motivating measurement
      before landing. Three items change MODELED algorithms (R6-2/4/16 → Lean model or
      `CORRESPONDENCE.md` §7 + fuzz); two rewrite assurance checkers (R6-7/8 →
      re-sabotage per `docs/sabotage-procedure.md`). ⚠ **Do not implement from titles
      alone — read each entry's verifier corrections.** One finder's fix was REFUTED by
      counterexample while its finding stood (R6-1: the naive shared memo is a
      correctness bug; the two-tier design in its verdict is the fix).

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
      **★★ RESUME POINT (updated 2026-08-15): steps 0, 1, 2, 2b, 3, 4a AND 4c-pre are
      DONE; the §11.3 fork is decided (α). The leg resumes at step 4c-i — the rule layer
      must mint leaf-indexed targets BEFORE any caller is re-pointed; "4c re-points the
      callers" is REFUTED.** Read `formal/history/PROOF_STATUS.md` 2026-08-15 and
      scope-doc **§11.6** FIRST (then §11.5 for the fork evidence). The 2026-08-14
      context below still stands:
      * **(α) by measurement on both sides.** Python's outbox row is keyed at the LEAF
        (`DeltaOutboxV1` has no relation column at all; the relation IS the object node's
        predicate) and `DeltaProcessor._map_deltas_to_keys` recovers the public name from
        the compiled `LeafFamily` table. The Lean probe's control fired: a half-done (α) —
        row moved, `affectedKeys` untouched — yields the **empty** cascade key set.
      * **⚠ §11.3 is WRONG in two places.** Its "the model has no analogue … string surgery
        on the `.i` suffix" is false on both halves (`S.keys` + `isDerived` IS the analogue,
        and a `.0`-stripper is measurably wrong — Python routes a Direct arm to
        `approver.2`). **`publicOfLeaf` must be INDEX-AGNOSTIC**, and `Leaf.lean::
        rawWriteRel`'s hardcoded index `0` is now a *known-wrong* model, not an unmeasured
        one. Its "`writeLoggedOne` must gain an `S` parameter" is also avoidable —
        `GraphState.schema` exists and the two forms are definitionally equal under
        `σ.schema = S`, saving ~145 mention-lines.
      * **★★ 4c CANNOT LAND ALONE — it must co-land with step 7.** P6 is a Python-side-only
        filter, so the moment 4c re-points `Exec.lean` the state gate reports ~76 leaf edges
        "only in LEAN model". Scope doc §7's "each step green and pushable" is refuted at
        4c. Budget one commit for 4c+7, not two.
      * **Live landing criterion:** `dropped by P6` → **0** and `compared against Lean` →
        **265** (today 76 and 189). Scope doc §6's `73 → 0 / 171 → 244` is stale for the
        third time — re-derive from `FINAL_REVIEW.md`'s generated block, not from prose.
      The four older notes below still stand:
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
- [ ] **★ Detect CORRESPONDENCE.md CLAIM-ROT automatically — designed and measured
      2026-08-16, NOT built.** The anchor pin (`verify.sh` step 4d) resolves 524 `file::symbol`
      pointers and **nothing else**; §9.2 says so in as many words. A 2026-08-16 audit of the
      rows this session touched found **four defects, three of them invisible to every gate in
      the project**: a retracted measurement claim still live in a row ("82/82 derived keys
      agree", retracted everywhere else the same day); two rows describing a model that had
      since changed; `unionSpineLeaves` — the def carrying the whole 2026-08-16b correction —
      **unanchored, so renaming it would have passed**; and the binary-`Expr` divergence
      missing from §7 entirely. All four are now fixed by hand. **The point of this item is
      that hand-fixing does not generalise.**

      **The measured constraint that shapes the design:** only **143 of 396** non-witness
      top-level decls under `formal/lean/ZanzibarProofs/` are anchored — **36%**, with a
      253-decl backlog (worst: `Cli.lean` 20/22 unmapped, `State.lean` 20/29). So
      "every def must be in the map" is not a viable gate today; it has to be a ratchet.

      Three mechanisms, in recommended order:
      * **(B) ANCHOR CONTENT PIN — build this first.** Hash the source text of each anchored
        symbol into a golden, exactly as `formal/headline_definitions.txt` already does for
        the 155 headline definitions (reuse `formal/conformance/statement_pin.py`). When an
        anchored symbol's BODY changes, the pin moves and you must regenerate deliberately —
        and that regeneration is the moment you re-read the row. **Zero-tolerance-viable
        immediately** (143 symbols, no backlog). ⚠ Must hash the **body, not the signature**:
        `persistedLeaves` changed twice on 2026-08-16 with its signature
        (`Schema → String → Expr → List PLeaf`) byte-identical, so a signature pin would have
        missed the exact case that motivated this. Cost: it fires on behaviour-preserving
        refactors of anchored symbols — the same noise `headline_definitions.txt` already
        accepts at the same scale.
      * **(C) PROSE-NUMBER LINT — cheap, build alongside.** Any CORRESPONDENCE row carrying an
        `N/M` or "N of M" validation claim must cite a test or a generated block. Direct
        analogue of step 4e's existing "corpus-count prose: 0 stale claim(s)" scan. This is
        what would have caught the live "82/82".
      * **(A) REVERSE-ANCHOR RATCHET — weakest, optional.** Floor the anchored count at 143 so
        it can only rise, plus: **any NEW file under `formal/lean/` must have every
        non-witness def anchored.** Would have caught `LeafRules.lean` / `TtuStarWide.lean`
        but NOT `unionSpineLeaves` (a new def in an already-mapped file). ⚠ The
        witness-exclusion must be STRUCTURAL (`namespace *Witness`), never a hand-maintained
        list — that pattern has already failed twice in this tree.

      ⚠ **State the honest limit in each new check's own docstring, or it will be
      over-trusted exactly as the anchor check was.** None of these verifies that a row is
      TRUE. They convert *silently stale* into *loudly must-look*. And one of the four defects
      is not mechanizable at all: knowing that a newly discovered fact about Python belongs in
      §7's drift log is irreducibly human.

      **Sabotage plan when built:** for (B), edit an anchored symbol's body and confirm the
      pin moves while the anchor check stays green (proving it catches what 4d cannot); for
      (C), re-insert the "82/82" claim and confirm it fails. Adding these is a new gate phase,
      so it needs the full ten-phase re-run.

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
- [ ] **Five `.fga` fixtures are fully subsumed at the pairwise level — TRACKED IN CODE,
      no action owed, no rush.** Measured 2026-08-11 against `genswarm`'s derived
      alphabet: `confluence`, `custom_roles`, `gdrive`, `github` and `master_store`
      contribute **0 unique features AND 0 new feature pairs**. They are listed in
      `tests/test_schema_shapes.py::KNOWN_SUBSUMED`, which is a **retirement register,
      not a failure list** — being on it carries no obligation to delete, and
      `test_subsumption_register_is_current` keeps it honest in both directions (a
      fixture newly becoming subsumed is flagged; one that stops being subsumed must be
      de-listed). This entry exists only to record the reasoning; the register is the
      live artifact.
      * **Why not just delete them.** Pairwise coverage is not the only axis. These are
        the LARGE, realistic schemas (`github.fga` alone has far more relations than any
        synthetic fixture), so they may exercise 3-way+ interactions, compile-order
        effects, or sheer scale that a pairwise score cannot see. They are also cheap,
        and they feed the byte-identity snapshot gate and the bulk differential gate
        with realistic structure. **Nobody has measured whether they contribute a unique
        TRIPLE** — that is the missing evidence, and `genswarm.universe_cells()` is
        pairwise by deliberate design (the cartesian grid is 2^51).
      * **What would settle it:** score triples over just these five vs the rest. If
        they add none either, they are genuinely redundant and the argument shifts to
        "keep as realism anchors or not". If they do, the question is closed.
      * ⚠ **Do not extend `test_fixture_earns_its_place` corpus-wide to force the
        issue** — it would redden on exactly these five, and the tempting fix (adding
        them to an exemption list) is the hand-maintained-list-beside-a-glob pattern
        that has already failed twice in this tree. The test deliberately covers only
        the fixtures in `REQUIRED`.

### Someday / out of scope (low priority — revisit only on a concrete need)

- [x] ~~**Vendor a corpus of REAL OpenFGA schemas, crawled from the wild**~~ —
      **DONE DIFFERENTLY 2026-08-11 (reviewed, measured, ADAPTED rather than vendored);
      archived 2026-08-16.** 48 schema files, 22 compile, `UnsupportedByGraphIndex`
      rejections = **0** — which is what makes the scope-rejection item below
      evidence-backed rather than assumed. Three shapes measured at zero occurrences were
      adapted in (`userset_over_derived.fga`, `heterogeneous_tupleset.fga`,
      `tupleset_shapes.fga`); corpus coverage went 43 → 46 of 51 features, floored by
      `test_fga_corpus_feature_coverage_does_not_regress`. **The "plausibility anchor" use
      is RETIRED, not deferred** (user, 2026-08-11): a realism prior only pays off if you
      are prioritising WHICH divergences to fix first, and this project's goal is that
      everything is correct. Full text, including the two findings about `parent_types`
      breadth and the TTU-tupleset axis:
      [`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md).
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
| [`docs/perf-next-round.md`](docs/perf-next-round.md) | perf standing guardrails (fence + dead-ends + hygiene) + pointer to the round-6 candidate worklist ([`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md)) |
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
