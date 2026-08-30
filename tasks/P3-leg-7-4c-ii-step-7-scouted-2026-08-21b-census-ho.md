---
id: P3
title: leg 7 4c-ii + step 7 -- green prefix COMPLETE 2026-08-30b (steps 1-2); left is the middle, 3-10
brief: Opens at step 3 (classify gains a LeafNode disjunct, first red edit), never at a session tail; sizing DISPUTED
pri: NOW
size: L
deps: []
related: [P6]
parent:
labels: [formal]
source: board
source_hash: c002792b539d
created: 2026-08-21b
moved: 2026-08-30b
updated: 2026-08-30b
closed:
---

Re-point the rule-routed write path onto leaf-indexed targets and retire projection `P6`
in the same commit. Critical path. Route B (weaken `UntaintedShadow`) stands adjudicated
(2026-08-20b, user call), absorbs `P14`'s classification half; scouted 2026-08-21b into
an executable design — full record in PROOF_STATUS `## Session 2026-08-21b`. Movers:
**census hole** — `CascadeStable.lean::shadow_graphRec_agree` (audited, 14 call sites, one
in `CascadeEnum.lean`, outside the 7-file/84-site budget) discharges from
`hunt : isDerived S (dt',r') = false`, which does not imply `publicOfLeaf = none` — a new
hypothesis on an audited signature + 14 repairs, unbudgeted; **`FoldAdmits`** — 21 sites
move, 3 stay σ0-side, not "all 24 in lockstep"; **decision taken** — keep names, change
bodies of the live write leg, `rewriteClosure` keeps its meaning (the σ0 chain is
rules-built by design), `writeRules` untouched (= the rejected Route C); **unowned
obligation** — `CascadeStable.lean::reachedByW3d_shadow` (via `untaintedShadow_writeLeg`)
pairs the same list on both folds; post-re-point the leaf list is a strict superset on a
mixed schema even for untainted tuples — no slice owned it, the Lean budget grows.

🧭 **MACHINE-CHECKED, and it needs a HUMAN CALL before 4c-ii lands: after the re-point
the headline theorems are FALSE AS WRITTEN — not merely unproven — at minted leaf-name
queries.** Two independent kernel `by decide` constructions; probe 2 typechecked
`graph_correct qLeaf admission w4fragment h hq b1 b2` verbatim, then the re-pointed
drained state grants it while `sem` denies. Probe 1's literal output (`SlV`, `tlEditor`):

    ("minted leaf name", "viewer.0")
    ("hd: isDerived at leaf name", false)
    ("hqs holds", true, "hqo holds", true)
    ("probeNonDerived sR qLeaf", true)
    ("check sR qLeaf", true)
    ("sem qLeaf", false)
    ("drainedB sRLc", true, "check sRLc qLeaf", true, "sem qLeaf", false, "check sRLc qPub", true)

The ~10 pinned headlines (`formal/headline_statements.txt`) each need a guard — accept
the narrowest, `hql : publicOfLeaf S q.object.type q.relation = none`; refuse the
`isLeafPred`- and `isDerived`/taint-keyed shapes (analysis + probe-2 caveat: PROOF_STATUS).

## Traps

⚠ **Seven traps live in scope doc §11.10** — the backwards own-key premise, the
leading-conjunct ordering, the `FoldAdmits` sites (21/3 above), the derived golden
expectation, Route B's two premises. **Read §11.10 before touching the cone**, AS
CORRECTED BY §11.11 item 8 and by five corrections made 2026-08-30b:

* **the non-emptiness premise is NOT `StoreValidRulesD`** — it constrains stored tuples,
  never relation-name non-emptiness. The superset-extras lemma needs an explicit
  `hne : ∀ dt R, isDerived S (dt,R) = true → R ≠ ""`, and the red middle must thread it.
  It is cheap now: `LeafRules.lean::hne_of_keys_nonempty` turns it into a `by decide`
  scan of `S.keys`.
* **`rawWriteRels` is `Leaf.lean:587`** (post-edit), not `:541` — cite `file::symbol`.
* ⚠ **the cone sizing is DISPUTED and unverified in BOTH directions.** A live import-BFS
  census on 2026-08-30b measured **24 modules / 125 code sites / 13 files** (second ring
  36 raw / 27 code) against the record's **42 / ~136 / 8** (90 / 50), and no measured set
  reproduced the recorded figures. The **3-session estimate rests on those figures**, so
  re-measure before planning the middle and do not re-cite either set as fact.
* **`FoldAdmits`' second exec gate is `Exec.lean:443`**, not the scope doc's `:376`
  (19 Prop + 2 exec gates move, 3 stay).
* ⚠ **`hql` may land on more than one pinned row.** `headline_statements.txt:46`
  (`W4WitnessDirect.correct_applies`) and `:56` (`::w3d2E_correct_applies`) carry the
  identical unfenced shape and are excluded from the "one row" count only as "staged
  records over intermediate chains". Check before step 7; step 7 finds out the hard way.

None of the three measurement flags was adjudicated — the prefix work did not need the
cone's size, and they are logged, not settled.

⚠ **The revert-to-green exit is scope doc §11.12, and its rule 3 is DEFECTIVE**: it
promises `PROOF_STATUS.md` "survives the reset", but nothing uncommitted survives
`git reset --hard`. Commit the docs-only append first and reset onto it, and commit every
green-stoppable prefix before running a sabotage against it. It cost 105 lines on
2026-08-30b — PROOF_STATUS `## Session 2026-08-30` §6.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule; enforced by `migrate.py::check_formal_pointer`, not merely stated)
- board pointer: [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §11.9

PROOF_STATUS **`## Session 2026-08-30` (§0–§8) FIRST** — it carries the prefix that landed,
the sabotages, and the three measurement flags — then `2026-08-28c` / `2026-08-28d` /
`2026-08-21b`; scope doc §11.11, **§11.10 (the traps)**, §11.12, then §11.9 / §11.7 / §11.5;
`GraphIndex/Scratch4cii.lean`; completion criterion: PROOF_STATUS `2026-08-16c`, its numbers
re-derived from `formal/FINAL_REVIEW.md`'s generated ledger, never prose. Then
`Leaf.lean::LeafNode`, `LeafRules.lean::rewriteClosureL_extras_leafNode`,
`CascadeStable.lean::UntaintedShadow` / `::reachedByW3d_shadow` / `::untaintedShadow_writeLeg`,
`LeafRules.lean::GraphState.writeRulesRaw`, `Exec.lean::foldAdmitsB`,
`extractor.py::_edge_projection`.

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-21b`), which is an upper bound on the real creation date, not a measurement. Summary, traps and read-first come from the `### P3` item block verbatim; the board pointer is the first line of Read first.

### 2026-08-28

Six-agent live census + both human calls adjudicated (user delegated 2026-08-28): hql ACCEPTED; Route B RETAINED on corrected grounds -- its 'zero additional cone' argument is FALSIFIED (census hole propagates ~45 second-ring sites through checkFn_agree_of_graphRec into 4 files outside the cone). hql itself is cheap: 8 declarations, depth 2, audit pin untouched -- but it lands on the leg-5 non-vacuity instrument (final_applies), so the fence-modeling endgame (checkPublic mirroring BL-2's public deny) is the recommended repair shape. Full census: scope doc sec 11.11; adjudication record: PROOF_STATUS 2026-08-28. Stale-comment debt from 2026-08-21b discharged (4 sites). Sizing: ~136 sites / 8 files, third consecutive low count.

### 2026-08-28b

Fence-modeling endgame LANDED and green, without hql and without opening the 4c-ii cone. New: GraphIndex/Fence.lean::GraphModel.checkPublic + the bridge not_mem_keys_of_publicOfLeaf_isSome; FullScope.lean::graph_correct_public (public read = sem under exactly graph_correct's hypotheses, NO leaf-name guard); CascadeStrataAssemble.lean::reachedByW3d2E_schema (prerequisite no document costed). Purely additive: pins 38->45 statements / 155->160 definitions, ZERO rows moved. Key correction to 2026-08-28: the layer was recorded as owed INSIDE the 4c-ii commit; it is not -- its fenced branch needs only WF S + undeclared-implies-sem-denies, so it lands BEFORE the un-splittable cone on green. Preflight CLOSED: parse_schema_ast rejects dotted REFERENCES (_validate_ast_references, zanzibar_utils_v1.py:910-940), so the WF clause is faithful; carve-out for BARE at :916. VACUITY WARNING: graph_correct_public proves green even under a fence that never fires (pre-4c-ii nothing mints leaf nodes); the six W4WitnessDirect.fence_* pins at Sd carry non-vacuity, and only fence_changes_answer catches a fence REMOVAL -- the four polarity pins stay green under that sabotage. NOT done on purpose: migrating the public surface + final_applies/final_applies4 onto checkPublic (changes pinned statements on the non-vacuity instruments; own session). That is the next P3 step and it is still pre-4c-ii.

### 2026-08-28c

Public-surface migration LANDED (step A of the remaining plan). Seven declarations -- backend_equivalence, exclusion_effective, no_ghost_grant, Exec.graphRun_check_eq_sem, ::graphRunOps_check_eq_sem, W4WitnessDirect.final_applies/final_applies4 -- re-stated over GraphModel.checkPublic via graph_correct_public. NONE gained a hypothesis; every proof stayed a 1-2 line delegation; lake build clean first try. Cli.lean's graph mode migrated with them.

**hql surface cut from 6 rows to 1.** docs/latent-gaps.md named six theorems as FALSE post-4c-ii; five plus both final_applies witnesses are now out of that set (the fence discharges the leaf case). Only graph_correct (headline_statements.txt:27) still needs the binder -- it is deliberately the INTERNAL-layer statement. This supersedes the item block's "8 declarations" figure.

**A hole was found and closed.** Sabotage 1: revert Cli.lean to the unfenced read, migrate everything else -> `495 passed in 590.51s`, nothing caught it. Structural, not an oversight: pre-4c-ii no corpus can distinguish the two reads. Fix is TEXTUAL -- new Exec.lean::graphModeAnswers, a named definition pinned verbatim at headline_definitions.txt:138, dragged into the closure by graphModeAnswers_eq_sem in statement_pin.py::HEADLINE. Sabotage 2 (repaired form, build stays green at 1089 jobs): definition pin FIRED, and the statement pin matched 46/46 -- BLIND. Do not remove graphModeAnswers_eq_sem from HEADLINE; it un-pins the driver.

**Equiv.lean 27-rung ladder: NOT migrated, zero edits.** Resolved from the file's own header (per-stage record, "each rung kept exactly as proved at its stage"), not by taste. Was flagged pre-emptively as the session's load-bearing unbudgeted branch (would have been 6->8 module cone, +27 edits).

**Doc debt:** the "26 statements" rot was 8 live sites, not the 5 previously recorded; fixed by deleting the number rather than updating it. Found-not-fixed and declared: formal/README.md:122-124 stale gate figures (tests/ 762 vs live 943); docs/tasktool-trial-protocol.md:403 deliberately untouched (pre-registered rubric).

**Sizing (the question asked): the rest of P3 is 3 sessions, not 1.** 9-agent census + 2 adversarial critics. Every figure corrected UPWARD, first time in four: cone 38/39->42 modules, second ring ~45/4 -> 90 raw/50 code across 8 files, sites ~123->136, in-cone verify cycle ~45s -> 200-400s. Binding constraint is trap 3: the cone is un-splittable (headline theorems kernel-decide FALSE mid-way), so there is no green state to stop at. Subagents do not help -- one tree compiles, lake build is serial.

Next session: settle the P14 UntaintedShadow adjudication with #eval probes in Scratch4cii.lean (1 importer, 0 audit rows, 0 pin rows, deletable), then open the cone at the top of a fresh window with a declared revert-to-green exit. Full record: PROOF_STATUS 2026-08-28c.

### 2026-08-28d

P14 UntaintedShadow adjudication SETTLED, and it moved the answer. New six-field battery in Scratch4cii.lean (additive, zero-cone, still 1 importer / 0 audit / 0 pin rows).

FINDINGS. (1) classify is the ONLY UntaintedShadow field that ever fails, and only unweakened -- term holds in its leaf-extended form, so Route B's clause 3 costs nothing. Route B's weakening is exactly ONE disjunct on ONE field. (2) nodesSub/closed/closed0 hold everywhere (both chains, idx-0 and idx-2, mixed store). No probe in this repo had touched them -- the 2026-08-20 battery is edge-only. So 4c-ii owes NO writeRulesRaw endpoint-closure edit; that unbudgeted risk is retired by measurement. (3) slSwD_not_mono is an INSTRUMENT ARTIFACT w.r.t. the _d chain: reachedByW3d2_shadow_d builds sigma0 over the untainted-FILTERED store (CascadeStrataSettle.lean:1188-1189), so at a one-derived-tuple store sigma0 is emptyState and sub holds vacuously. Row B isolates it -- against sP the failures are sub+nodesSub, not classify. Corrects 2026-08-20b; the pin stays (it is true as stated) with d_vs_sP_fails_on_sub beside it.

Prop-level: strong_shadow_false_at_d_own_sigma0 -- the unweakened shadow is UNINHABITED at a leaf-routed _d state against the sigma0 that chain itself constructs. Mixed store also witnesses the unowned superset-extras shape: the UNTAINTED viewer write mints approver.1, classifying under the same disjunct.

Instrument PROVED: shadowB_correct (shadowB S false = UntaintedShadow, via five per-field lemmas). Sabotage -- trim closedB's ab.2 conjunct AND its lemma statement to stay consistent -> rc=1, three errors, ALL inside shadowB_correct, while EVERY decide pin stayed green. 2026-08-28c's 'a guard-only pin cannot catch a fence removal' one layer down. Do not replace shadowB_correct with more decide rows.

Also: revert-to-green exit plan written into the HANDOFF item block (was required in two places, existed in none). MIN_TESTS_ALL drift repaired 923->943 (20 tests of headroom against CLAUDE.md's zero-headroom contract), floor instrument-checked at 944. formal/README.md's rotted figures deleted rather than updated (both paragraphs). Cone sizing UNCHANGED: 42 modules / ~136 sites / 3 sessions. Full record: PROOF_STATUS 2026-08-28d.

### 2026-08-29

Digest-only drift: the four 2026-08-28* sessions rewrote the board row (fence layer, public-surface migration, P14 settled) without re-stamping. The task body IS current -- its Log carries per-session entries through 2026-08-28d -- so this re-stamps the source_hash against the rewritten row and changes no content.

### 2026-08-29d

`brief` populated from the board row's constraint annotation (mechanical: `updated` only,
`moved` held -- populating a field is not progress on the cone).

### 2026-08-30b

Step 1 of the cone LANDED green, and the plan's SHAPE changed. An 8-agent read-only recon
established that P3 is NOT one un-splittable block: steps 1-2 (the LeafNode carrier, and
the unowned superset-extras lemma) are purely additive and green-stoppable; the
un-splittable middle is steps 3->10, beginning at the UntaintedShadow.classify weakening
(CascadeStable.lean:529) and ending when hql lands on graph_correct (FullScope.lean /
headline_statements.txt:27). Size unchanged (~3 sessions); only the shape moved -- the cone
now has a prefix a bounded session can bank.

LANDED: Leaf.lean::LeafNode (Route B's carrier for the classify disjunct), the Bool mirror
::leafNodeB, ::leafNodeB_correct, and the pins. +107 lines, purely additive, zero
deletions. Carrier is publicOfLeaf, never isLeafPred (the E3 trap).

A REAL HOLE, FOUND AND CLOSED BY SABOTAGE. The E3 guard `leafPublic p != ""` was UNPINNED:
removing it from BOTH LeafNode and leafNodeB consistently builds GREEN (rc=0) -- both `by
decide` pins and leafNodeB_correct were blind, because the Sw fixture declares no ""-named
relation. Closed with a pathological fixture LeafWitness.SwEmptyRel ("" declared derived on
"user") plus swEmptyRel_pol_bare and swEmptyRel_bare_subject_not_leafNode. Verified
first-hand: under the sabotage the pin fires, rc=1, "Leaf.lean:1228:74: Tactic decide
proved that the proposition ... is false". NEAR-MISS inside the repair: the first fixture
declared "" on "doc" and the sabotaged build stayed GREEN -- publicOfLeaf keys on the
SUBJECT's type, so the empty derived relation must be declared on "user". A discriminating
pin that could not discriminate.

TWO CORRECTIONS TO THE TRAPS. (1) "the non-emptiness premise is StoreValidRulesD" does NOT
verify for the superset-extras lemma: StoreValidRulesD constrains stored tuples, never
relation-name non-emptiness. The lemma needs an explicit hne : forall dt R, isDerived S
(dt,R) = true -> R != "", and the red-middle consumer must thread it. (2) rawWriteRels is
Leaf.lean:587 post-edit, not :541 -- cite file::symbol, not a line.

PROCESS FAILURE WORTH THE ROW. Restoring after the verification sabotage, `git checkout --
.../Leaf.lean` on uncommitted work reverted to HEAD and destroyed all 105 lines then
written, not just the sabotage (recovered from a file backup plus the authoring agent's
context). That is a live defect in the section 11.12 exit: rule 3 promises PROOF_STATUS
"survives the reset", but nothing uncommitted survives `git reset --hard`. Amendment
recommended in PROOF_STATUS 2026-08-30 section 6, and appended to the scope doc: commit the
docs-only append FIRST and reset onto it, plus a new rule 6 -- commit every green-stoppable
prefix before running a sabotage against it.

NEXT: step 2 is designed and verified feasible (green-stoppable, no red dependency) but NOT
written. Proposed home LeafRules.lean after ::writeRulesRaw; shape "every edge produced by
the leaf fold is either produced by the rewrite fold, or its target is a LeafNode";
premises hne (above) and hmd (no schemaRewrites rule matches a dotted relation).
Strict-superset witness already pinned at Scratch4cii.lean::mixed_is_strict_superset /
::mixed_extras_are_the_two_leaves. All ten gate phases green on this tree after the Lean
edit. Full record: PROOF_STATUS `## Session 2026-08-30`; root ledger 2026-08-30b.

Same-session re-stamp, not housekeeping: this session rewrote the P3 board row and item block (step 1 landed; the prefix/middle split; the two trap corrections) and mirrored all of it here -- title, brief, the 2026-08-30b Log entry, and a rewritten Traps section carrying the StoreValidRulesD and rawWriteRels corrections plus the defective 11.12 rule 3. The body's 2026-08-21 summary block is left as filed, per this task's own convention that the Log carries the updates.

SECOND WRITE-BACK, same session. Step 2 also LANDED green, so the green prefix is COMPLETE
and everything left in P3 is the un-splittable middle, steps 3->10.

STEP 2: LeafRules.lean::rewriteClosureL_extras_leafNode -- the unowned superset-extras
lemma that section 11.11 recorded as owned by no slice. Proved at the designed statement,
general t, no premise weakened: for all u in rewriteClosureL S (rawWriteTuples S t),
u is in rewriteClosure S t OR LeafNode S (objNode u.object u.relation). +229 lines, purely
additive, full lake build green. Workhorse: ::rewriteClosureAuxL_extras, a lockstep
equal-fuel induction over both kernels.

NON-VACUITY PINNED with no hypotheses:
LeafRuleWitness::rewriteClosureL_extras_leafNode_nonvacuous. All four premises discharged
at SlV/tlEditor, and the conclusion is derived THROUGH the lemma (left disjunct refuted),
not decided directly. Demanded because a four-premise lemma whose premises never hold
together is true and empty -- the same shape as 2026-08-28b's graph_correct_public vacuity
warning. Two by-products: ::slV_wf had to be proved (no WF SlV witness existed anywhere
importable), and ::hne_of_keys_nonempty, a reusable bridge turning the undecidable hne into
a `by decide` scan of S.keys -- the middle inherits both.

SABOTAGE: drop the LeafNode disjunct -> rc=1, type mismatch at LeafRules.lean:518, red for
the right reason. No pre-existing `by decide` pin would have caught it; the non-vacuity
theorem is now that reference.

NEXT ACTION IS STEP 3: CascadeStable.lean::UntaintedShadow.classify gains the LeafNode
disjunct (:529) -- the FIRST RED edit and the middle's only door. Open it at the top of a
fresh window, never at a session tail, with the section 11.12 exit declared first.

THREE MEASUREMENT FLAGS, logged and NOT adjudicated (the prefix did not need the cone
size); all three are now in the Traps section. (1) A live import-BFS census measured 24
modules / 125 code sites / 13 files (ring 2: 36 raw / 27 code) against the record's 42 /
~136 / 8 (90 / 50), and no measured set reproduced the record -- the 3-session sizing rests
on those figures and is unverified in both directions. (2) FoldAdmits' second exec gate is
Exec.lean:443, not the scope doc's :376. (3) hql may land on more than one pinned row:
headline_statements.txt:46 correct_applies and :56 w3d2E_correct_applies carry the
identical unfenced shape.

Gate: all ten phases were green after step 1; the step-2 run was still going at write-back
-- ask scripts/gate_status.py, never a line here. Full detail: PROOF_STATUS
`## Session 2026-08-30` sections 7-8; root ledger 2026-08-30b.

Second write-back of the same session: the board row was rewritten again (prefix complete, step 3 is the next action, five trap corrections) and mirrored here in the same pass -- title, brief, the Traps section with the three measurement flags, the reordered Read first, and the 2026-08-30b Log entry. Re-stamping the digest against the row I just wrote and read.
