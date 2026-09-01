---
id: P3
title: leg 7 4c-ii -- the MIDDLE split too: the shadow is generic, widening is a re-instantiation
brief: Class-B repair DECIDED (user 2026-09-01): rows 46/56 -> checkPublic, hql refused. 4 conditions. Nothing waiting.
pri: NOW
size: L
deps: []
related: [P6]
parent:
labels: [formal]
source: board
source_hash: 8aec5fb3ac34
created: 2026-08-21b
moved: 2026-09-01
updated: 2026-09-01
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

⚠ **The traps now live in scope doc §11.13, which SUPERSEDES §11.10** (and §11.11 item 8).
Eight items; read it before touching the cone. Summary, with the three 2026-08-30b
measurement flags now ADJUDICATED:

* **the non-emptiness premise is NOT `StoreValidRulesD`** — it constrains stored tuples,
  never relation-name non-emptiness. The superset-extras lemma needs an explicit
  `hne : ∀ dt R, isDerived S (dt,R) = true → R ≠ ""`, and the red middle must thread it.
  It is cheap now: `LeafRules.lean::hne_of_keys_nonempty` turns it into a `by decide`
  scan of `S.keys`. ⚠ Its companion **`hmd` is discharged VACUOUSLY** at the only
  non-vacuity witness (`schemaRewrites SlV = []`, `LeafRules.lean:609`), so the `exfalso`
  at `LeafRules.lean:466-471` is dead under every fixture.
* **`rawWriteRels` is `Leaf.lean:587`** (post-edit), not `:541` — cite `file::symbol`.
* ✅ **FLAG 1 SETTLED — the sizing was wrong, and 42 was a MIS-ROOTED census.** Two
  independent import-BFS runs agree: `CascadeStable`'s reverse cone is **20** (+root =
  **21**). 41+root is reproducibly the cone of `DirectCorrect` AND of `RulesWrite`, and 41
  is the *forward* cone of `CascadeStrataAssemble`. "~136 sites / 8 files" was a raw
  TWO-symbol `grep -c` LINE count, correct at `d3c1226` and now stale (162/9). Size with
  THREE numbers: **21 modules recompile, ~9 files / ~229 sites re-check, ~20 sites in 3
  files go genuinely red.** ⚠ **A site count is meaningless without its symbol list and
  its counting unit** — that ambiguity, not the tree, is what four censuses disagreed about.
* ✅ **FLAG 2 SETTLED** — `FoldAdmits`' second exec gate is `Exec.lean:443`, not `:376`
  (19 Prop + 2 exec gates move, 3 stay).
* ✅ **FLAG 3 SETTLED, and the answer moved: `hql` lands on THREE pinned rows, not one.**
  `docs/latent-gaps.md` excludes `headline_statements.txt:46` / `:56` as "staged records
  over intermediate chains"; that reason is REFUTED by `FullScope.lean:78`
  (`abbrev ReachedBy := ReachedByW3d2E`) and `:84` (`abbrev Drained`), which make
  `w3d2E_correct_applies` hypothesis-IDENTICAL to `final_applies` — it is that theorem
  with the fence deleted, not an intermediate chain. **Their repair is probably migration
  onto `checkPublic`, not the `hql` binder.** Structurally confirmed, not kernel-confirmed.
* ⚠ **NEW — the one tier-1 site with NO existing lemma.** `shadow_graphRec_agree`
  discharges its probe target from `isDerived S (dt',r') = false`, which does not exclude
  a minted leaf name. It needs the operand relation *declared*, and nothing forces
  `computedRefs` names to be declared — `Core/Schema.lean::WF` records only that DECLARED
  names are dot-free. Python enforces it; the repair is faithful new modelling.
* ⚠ **NEW — a BLIND INSTRUMENT, and the NEXT SESSION'S FIRST EDIT.** `Scratch4cii.lean:51`
  defines a local unguarded `leafNodeB` SHADOWING the guarded carrier step 1 added at
  `Leaf.lean:547`; the local one wins every unqualified use, including `clsB` (`:393`) and
  `termB` (`:409`) — so the whole P14 weak battery measures a broader proxy than the
  carrier it validates, in the UNSAFE direction. Delete `:51` first; expect a diagnostic
  red confined to the file (1 importer, 0 audit rows, 0 pin rows — re-verified 2026-08-30c).
* ✅ **Adding a hypothesis to `shadow_graphRec_agree` / `checkFn_eq_sem_w3d` /
  `shadow_reach_agree` / `reachedByW3d_shadow` changes NO pin file** — none is in
  `headline_statements.txt` or `headline_definitions.txt`; they carry name pins only.

All three 2026-08-30b measurement flags are now adjudicated (2026-08-30c). Two new traps
replace them.

⚠ **The revert-to-green exit is scope doc §11.12, and its rule 3 is DEFECTIVE**: it
promises `PROOF_STATUS.md` "survives the reset", but nothing uncommitted survives
`git reset --hard`. Commit the docs-only append first and reset onto it, and commit every
green-stoppable prefix before running a sabotage against it. It cost 105 lines on
2026-08-30b — PROOF_STATUS `## Session 2026-08-30` §6.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule; enforced by `migrate.py::check_formal_pointer`, not merely stated)
- board pointer: [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §11.9

PROOF_STATUS **`## Session 2026-08-30c` (§0–§6) FIRST** — it carries the genericization that
landed, the settled sizing, the blind instrument, and the three now-adjudicated measurement
flags — then `## Session 2026-08-30` (§0–§8) for the prefix and its sabotages, then
`2026-08-28c` / `2026-08-28d` / `2026-08-21b`; scope doc **§11.13 (the traps, which
SUPERSEDES §11.10)**, §11.11, §11.12, then §11.9 / §11.7 / §11.5;
`GraphIndex/Scratch4cii.lean`; completion criterion: PROOF_STATUS `2026-08-16c`, its numbers
re-derived from `formal/FINAL_REVIEW.md`'s generated ledger, never prose. Then
**`CascadeStable.lean::ShadowOver`** (the generic structure) and its `UntaintedShadow`
abbrev, `Leaf.lean::LeafNode`, `LeafRules.lean::rewriteClosureL_extras_leafNode`,
`CascadeStable.lean::reachedByW3d_shadow` / `::untaintedShadow_writeLeg` /
`::shadow_graphRec_agree` (the census hole),
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

### 2026-08-30c

THE MIDDLE SPLIT TOO. The recorded plan opened step 3 by widening UntaintedShadow.classify in place, red until step 10 -- that is why the middle was un-splittable. The plan conflates two separable things: making the shadow chain ABLE to carry a wider extras set, and WIDENING it. Separating them costs one abbrev.

LANDED, green: CascadeStable.lean now carries `structure ShadowOver (P : NodeKey -> Prop)` with classify : forall ab in sigma.edges, ab in sigma0.edges OR P ab.2, and term : forall k, P k -> forall y, (k,y) not-in sigma.edges, plus `abbrev UntaintedShadow S sigma sigma0 := ShadowOver (DerNode S) sigma sigma0`. shadow_reach_agree, shadow_admitEdge_agree, untaintedShadow_writeLoggedOne, ::writeLeg and ::foldAdmits are generalized over {Extra}. ABBREV is the load-bearing word: it is reducible, so every existing field access, anonymous constructor, rcases and signature kept working unchanged. lake build green, 1089 jobs -- first try for the structure, one trivial repair (a stray S in a have-annotation) for the five lemmas. THREE in-cone cycles against an abort budget of TEN. The 65 UntaintedShadow sites in CascadeStrataSettle.lean and the whole CascadeSettle / CascadeEnum / CascadeStrataEnum / CascadeStrataAssemble chain never went red. The widening is now a one-line re-instantiation instead of a re-proof of the cascade chain.

WHY FOUR SESSIONS OF COSTING MISSED IT: every census measured how many sites MENTION the symbol (85-229, depending on the symbol list). None asked how many depend on DerNode SPECIFICALLY rather than on "extras are terminal and off the probe target". That answer is 17 .classify sites and 9 .term sites. A sizing question asked in the wrong units cost roughly two sessions.

SIZING SETTLED, and the record was wrong. Two independent import-BFS measurements agree name-for-name on the ring decomposition. CascadeStable's reverse cone is 20 (+root = 21), NOT 42. 41+root is reproducibly the reverse cone of DirectCorrect AND of RulesWrite, and 41 is the forward cone of CascadeStrataAssemble -- so the recorded "42 modules" is a delegated census rooted at the wrong module, and the wall-clock half of the 3-session estimate rested on a number 2x too large. The "~136 sites / 8 files" figure was a raw TWO-symbol grep -c LINE count (UntaintedShadow 89/8 + DerNode 47/4, at commit d3c1226): correct when taken, now stale at 162/9, a ~19 percent undercount -- the same failure mode it was written to correct. The 2026-08-30b census's "13 files" is exactly right (the raw mention set of the ~26-name shadow family); its "24 modules / 125 code sites" is unreproducible under any stated convention. SIZE WITH THREE NUMBERS: 21 modules recompile, ~9 files / ~229 sites re-check, ~20 sites in 3 files go genuinely red.

DURABLE LESSON, and it should become a house rule: a site count is meaningless without its symbol list and its counting unit. The record and the censuses never disagreed about the tree -- they disagreed about what a "site" is, for four sessions, with neither publishing its convention.

THE CENSUS HOLE IS REAL AND HAS NO EXISTING LEMMA. shadow_graphRec_agree discharges its probe target from hunt : isDerived S (dt',r') = false, which does NOT exclude a minted leaf name (approver.0 is not itself derived, but publicOfLeaf maps it to some "approver"). It needs the operand relation DECLARED, and nothing in the model forces computedRefs names to be declared -- Core/Schema.lean::WF records only that DECLARED names are dot-free. Python does enforce it (parse_schema_ast's _validate_ast_references), so the repair is faithful new modelling, not a lemma lookup. The other two halves are FREE: the wAllNode probe (LeafNode carries on != STAR, so the existing variant-mismatch proof transcribes verbatim) and the BARE-subject write-leg premise (leafPublic BARE = "" against LeafNode's mandatory != "" guard -- the E3 residual guard, already pinned at Leaf.lean::swBare_not_leafNode).

RISK RETIRED BY MEASUREMENT: none of shadow_graphRec_agree / checkFn_eq_sem_w3d / shadow_reach_agree / reachedByW3d_shadow appears in headline_statements.txt or headline_definitions.txt -- they carry audited_theorems.txt rows only, which pin NAMES, not statements. Adding a hypothesis to any of them changes NO pin file. The recorded worry about "a new hypothesis on an audited signature" is therefore a worry about the 14 call sites only, not about the gate.

BLIND INSTRUMENT, created by step 1's own session, and it is the next session's FIRST edit. Scratch4cii.lean:51 defines a local unguarded `def leafNodeB (S) (k) : Bool := (publicOfLeaf S k.type k.pred).isSome` inside namespace Zanzibar.Scratch4cii. The real carrier, added by step 1 at Leaf.lean:547 in namespace Zanzibar, is strictly narrower -- it also requires leafPublic k.pred != "" && k.name != STAR && k.variant == Variant.plain. Scratch4cii imports LeafRules -> Leaf, so both are in scope and the LOCAL one wins every unqualified reference, including clsB (:393) and termB (:409) -- the definitions the entire P14 weakened battery is stated over (d_weak_holds :549, narrow_weak_holds_strong_fails :575, d_idx2_weak_holds :583, mixed_weak_holds_strong_fails :618). The direction of the error is the UNSAFE one: a broader proxy makes the weak disjunct easier to satisfy, so those rows can be green while the real widened classify fails. Reported by a recon agent, then verified FIRST-HAND before being written down. Step 1 created it by adding a correctly-guarded twin in the parent namespace without noticing the child's proxy; nothing went red because shadowing is legal, and Scratch4cii.lean:432-433's own docstring still reads that leafNodeB "has no leafNodeB_correct twin (:51)" -- a comment that was true when written and that step 1 silently falsified. NOT FIXED HERE ON PURPOSE: its expected outcome is a diagnostic red worth its own gate cycle, not a rider on a commit whose headline is the genericization. Blast radius re-verified this session: 1 importer (ZanzibarProofs.lean:86), 0 audit rows, 0 headline-pin rows.

MEASUREMENT FLAG (3) SETTLED, and the answer moved: hql lands on THREE pinned rows, not one. docs/latent-gaps.md excludes headline_statements.txt:46 (correct_applies) and :56 (w3d2E_correct_applies) as "staged records over intermediate chains". That reason is REFUTED by two abbrevs in the same file as the theorems, both read first-hand: FullScope.lean:78 `abbrev ReachedBy : GraphState -> Schema -> Store -> Prop := ReachedByW3d2E` and :84 `abbrev Drained (S) (sigma) : Prop := cascadeKeys S sigma = []`. So w3d2E_correct_applies (:1278) and final_applies (:1375) have DEFINITIONALLY IDENTICAL hypotheses; the sole difference is GraphModel.check (raw) versus GraphModel.checkPublic (fenced). ReachedByW3d2E IS the headline closure -- w3d2E_correct_applies is final_applies with the fence deleted and q still universally quantified, not an intermediate chain. Row :46 follows a fortiori via toC_applies (:1255), whose own docstring records that the projection is one-way. CONSEQUENCE FOR THE PLAN: the repair for :46/:56 is probably MIGRATION ONTO checkPublic (exactly as final_applies was migrated on 2026-08-28c), not the hql binder -- cheaper, and it keeps the guard off the pinned statements. Only :27 (graph_correct) genuinely needs the binder, because graph_correct_public delegates to it and takes the guard there. STRUCTURALLY CONFIRMED, NOT KERNEL-CONFIRMED: no build witness was constructed, and 4c-ii has not landed. Also found: docs/latent-gaps.md:152 cites unfenced_grants as headline_statements.txt:51; it is :52, and the off-by-one sits inside the very paragraph doing the exclusion arithmetic this finding disputes.

CORRECTION TO THIS TASK'S OWN 2026-08-30b ENTRY: hmd is discharged VACUOUSLY. rewriteClosureL_extras_leafNode_nonvacuous was recorded as having "all four premises discharged at SlV/tlEditor". That is literally true and weaker than it sounds -- hmd is `by decide` at SlV precisely BECAUSE schemaRewrites SlV = [] (pinned in the same file at LeafRules.lean:609::lrV_untainted_layer_silent, verified first-hand this session). The theorem is still non-vacuous in the sense that mattered (the conclusion is reached THROUGH the lemma, with the left disjunct refuted by decide), but no fixture in the tree exercises the hmd branch of the induction -- the exfalso at LeafRules.lean:466-471 is dead under every witness. A schema with a non-empty schemaRewrites whose rules are all dot-free is owed before that premise can be called measured.

EXIT PROCEDURE, applied in its AMENDED form. Green anchor 5f48be2, verified COVERED first-hand by gate_status.py before the first edit; the docs-only preamble was COMMITTED FIRST (99f4245) so the reset target already contained the session's yield -- the repair for the rule-3 defect that cost 105 lines on 2026-08-30b. Abort trigger declared up front (70 percent context, or 10 red in-cone cycles); spent 3, all green. Full record: PROOF_STATUS `## Session 2026-08-30c` sections 0-6; root ledger 2026-08-30c.

Same-session mirror, not housekeeping: this session rewrote the P3 board row, the HANDOFF banner and the item block (the genericization, the settled sizing, the blind instrument, the three hql rows, the two corrections) and mirrored all of it here in the same pass -- title, brief, and this Log entry.

Same-session re-stamp: this session rewrote the P3 board row and item block (the ShadowOver genericization, the settled 21-module sizing, the Scratch4cii:51 blind instrument, the three hql rows, the hmd-vacuity correction) and mirrored all of it into the 2026-08-30c Log entry in the same pass. Re-stamping the digest against the row I just wrote. The body's 2026-08-21 summary block is left as filed, per this task's convention that the Log carries the updates.

SABOTAGED BEFORE BELIEVED, and the extras predicate is load-bearing. A refactor is not a
check, so the house rule does not literally apply -- but this one makes a CLAIM (that the
widening is now a one-line re-instantiation), and that claim is false if the chain had
stopped depending on the extras predicate at all, in which case the genericization would
have papered over the red window rather than deferring it. Discriminating sabotage, run
AFTER the green prefix was committed at b42c52d (section 11.12 rule 6): instantiate the
abbrev at the weakest possible predicate, `ShadowOver (fun _ => True) sigma sigma0`.

OBSERVED: rc=1, TEN errors, in BOTH directions -- producers and consumers.

    CascadeStable.lean:800:19: Insufficient number of fields for `<...>` constructor:
      Constructor `True.intro` does not have explicit fields, but 7 were provided
    CascadeStable.lean:827:13: Unknown identifier `R`
    CascadeStable.lean:922:67: Application type mismatch: The argument
    CascadeStable.lean:923:62: Application type mismatch: The argument
    CascadeStable.lean:938:80: unsolved goals
    CascadeStable.lean:956:29: Application type mismatch: The argument

:800 is the applyD producer, whose anonymous constructor collapses to True.intro;
:922/:923/:938 are shadow_graphRec_agree and :956 is checkFn_eq_sem_w3d -- EXACTLY the
consumers predicted to need the `not LeafNode` half. So the remaining work is real and
sits where the plan says it sits. Reverted; lake build green again at 1089 jobs. Five
in-cone cycles used of the ten-cycle abort budget.

Two docstrings were narrower than their theorems after the generalization
(shadow_reach_agree said "off the DerNodes", shadow_admitEdge_agree said "never a DerNode")
and were rewritten to name Extra, with this sabotage's result recorded in the first of them
so the next reader does not have to re-run it.

CITATION HYGIENE, caught by a sweep rather than by luck: a draft of this session's write-up
cited `Leaf.lean::swBare_not_leafNode` as the BARE-subject pin. NO SUCH DECLARATION EXISTS.
A `grep -c "(theorem|def) <name>"` sweep over every symbol cited in the session records
caught it; the real one is Leaf.lean:1180::bare_subject_not_leafNode, and note
Scratch4cii.lean:296 declares a SAME-NAMED twin, so cite the file, not the bare symbol.
This is CLAUDE.md's "a trap must cite a symbol that EXISTS" rule collecting again -- run
the sweep before writing citations down, not after.

### 2026-08-30d

BLIND INSTRUMENT CLOSED, and the prediction attached to it was WRONG in the safe direction. The declared first edit was to delete Scratch4cii.lean:51, the local unguarded `leafNodeB` shadowing step 1's guarded carrier at Leaf.lean:547, with the recorded expectation of "a diagnostic red confined to the file". OBSERVED: rc=0, Build completed successfully (1089 jobs). No `by decide` row and no #eval row in the P14 weak battery distinguishes the broad proxy from the narrow carrier, so the shadowing corrupted nothing and those rows are valid as taken.

A GREEN IS NOT A MEASUREMENT -- "the two predicates agree everywhere I probe" and "my edit did not take effect" produce the same rc=0. So the difference was made mechanical instead of argued. New positive pin (not an xfail, not a docstring): Scratch4cii.lean::leafNodeB_here_is_the_guarded_carrier asserts `leafNodeB LeafWitness.SwEmptyRel (subjNode <"user","alice",BARE>) = false AND (publicOfLeaf LeafWitness.SwEmptyRel "user" BARE).isSome = true`. The two conjuncts disagree BY CONSTRUCTION at SwEmptyRel, the pathological empty-relation-name schema: the second is exactly the proxy's sole test, the first is E3's residual `leafPublic != ""` guard that only the real carrier carries.

SABOTAGED BEFORE BELIEVED: re-add the deleted proxy verbatim. rc=1, and that pin was the ONLY error in the build -- `Tactic decide proved that the proposition ... is false` at Scratch4cii.lean:344:78. "Only error" is the load-bearing half: it proves this pin is the sole thing in the file separating the two carriers, which is what upgrades the green above from an absence of evidence into a measurement. Proxy removed again: rc=0, 1089 jobs.

TWO DOCSTRINGS were falsified in silence by step 1 and are corrected in place, each now saying what it corrects and when: Scratch4cii.lean:432-433 claimed leafNodeB "still has no leafNodeB_correct twin" (it has had one at Leaf.lean:552 since step 1), and :288-289 claimed "no LeafNode definition exists anywhere in this tree, only the leafNodeB proxy above" (Leaf.lean:538 defines it; the proxy is gone). The design constraint the latter describes was ANSWERED, not dropped -- LeafNode carries `leafPublic p != ""` for it, pinned at Leaf.lean::swEmptyRel_bare_subject_not_leafNode.

CITATION HYGIENE, applied prospectively this time rather than caught after: `bare_subject_not_leafNode` exists in BOTH Leaf.lean:1180 and Scratch4cii.lean, so a warning to cite file::symbol is now attached to the Scratch4cii twin's own docstring -- where the next reader of that name is actually standing, rather than in a session record they may not read.

RE-POINT NOT STARTED. Remaining 4c-ii work is unchanged: repoint the abbrev at DerNode v LeafNode and discharge ~20 tier-1 sites in 3 files, with shadow_graphRec_agree's census hole (trap (g)) the one site having no existing lemma -- now the ONLY trap that decides the next session, since (h) is closed. Scouting was delegated to read-only subagents this session; reports land in .scratch/4cii-repoint/ and anything acted on gets transcribed into PROOF_STATUS before it is relied on, since .scratch/ is gitignored.

Same-session mirror: this session rewrote the P3 board row, brief, the HANDOFF banner and the item block, and scope doc 11.13 item (h); all of it mirrored here in the same pass with the same session key. Full record: PROOF_STATUS `## Session 2026-08-30d` sections 0-5.

RE-POINT SCOUTED (six read-only agents), transcribed OUT of .scratch/ into PROOF_STATUS `## Session 2026-08-30d` section 6 the same session -- .scratch/ is gitignored, so a report left only there is already lost. Labelled as AGENT OUTPUT, not a finding: nothing is kernel-confirmed and no Lean edit was made from it.

THE USEFUL IDEA: make the flip a NO-OP before making it. UntaintedShadow is a reducible abbrev, so the flip changes what ~19 goals ASSERT simultaneously in a file with 20 downstream modules. Three moves defuse that: ANCHOR (restate a declaration that genuinely means the strong shadow at `ShadowOver (DerNode S)` -- definitionally identical today, immune to the flip); GENERALISE (lift a proof's hardcoded DerNode facts to explicit premises over {Extra}, then instantiate); PRE-WIDEN (strengthen a `have : not DerNode S k` in place to `not (DerNode S k or LeafNode S k)` and feed today's already-Extra-generic consumers via Or.inl -- this typechecks TODAY, and it is what makes the three hardest sites green-stoppable). Ten green-stoppable steps result; step 9, the flip itself, becomes an import plus one abbrev body with a two-line rollback.

TWO OF MY OWN BRIEFING CLAIMS CAME BACK REFUTED, and both are accepted:
(1) "the fun _ => True sabotage's TEN errors is an upper bound on the damage" -- recorded 2026-08-30c and repeated by me -- is WRONG in the dangerous direction. Lean does not build a module whose dependency errored, so that run never compiled CascadeStrataSettle.lean or Scratch4cii.lean, and those two carry 14 of the 19 obligations. TEN IS A LOWER BOUND tree-wide; it upper-bounds only the error count within the first failing file. Size off the 19-obligation census, off neither number.
(2) The pin blast radius is real and two scouts contradicted each other on it -- reconciled, not averaged. The PREDICATE names (UntaintedShadow / ShadowOver / DerNode / LeafNode) are unpinned, but the LEMMA names are identity-pinned in audited_theorems.txt. VERIFIED FIRST-HAND because it is a gate-safety claim: shadow_graphRec_agree, checkFn_eq_sem_w3d, shadow_reach_agree and reachedByW3d_shadow each carry exactly one audited_theorems.txt row and ZERO rows in headline_statements.txt / headline_definitions.txt; the four predicate names carry zero rows in all three. So adding a hypothesis changes no pin (names are what is pinned), the abbrev re-point cannot red the gate by itself, and NO STEP MAY RENAME OR DELETE A PINNED NAME.

TOP OPEN RISK, DO NOT ASSUME IT AWAY: three Class-B call sites (CascadeSettle.lean:1119, CascadeStrataResettle.lean:1539 and :2683) invoke shadow_graphRec_agree with the ARBITRARY QUERY'S OWN relation, constrained only by a by_cases on isDerived, so step 7's ComputedRefsDeclared says nothing about them. The proposed guard is one GraphModel.checkPublic already performs -- but nobody traced whether it stops at graph_correct_w3d* or reaches graph_correct, whose statement is byte-pinned at headline_statements.txt:27. If it reaches, the cost is a reviewed weakening of a headline theorem: a user-visible scope change that must NOT be smuggled into this item. Spike it between steps 6 and 7.

SECOND OPEN RISK: NoLeafSubjects (steps 4-6) is a new UNDISCHARGED assumption on the headline chain, and the existing leaf fixtures are vacuous the same way hmd was (schemaRewrites SlV = [], leafRewrites SlUnt = []; no fixture exercises both layers at once). Pinning it only at SlV reproduces exactly that vacuity -- so do step 4's non-vacuity witness AND its failing control before step 6, to learn the answer at the cheap end.

STEPS 1 AND 2 OF THE RE-POINT LANDED GREEN, each with its own control. Full record: PROOF_STATUS `## Session 2026-08-30d` section 7.

STEP 1 -- ANCHOR (Scratch4cii.lean, 1 module, green first try). The four declarations that genuinely mean THE STRONG SHADOW are restated at `ShadowOver (DerNode ...)` instead of the UntaintedShadow abbrev: strong_shadow_false_at_raw, shadowB_correct, strong_shadow_false_at_d_own_sigma0, strong_shadow_false_at_mixed. Definitionally identical today because abbrev is reducible, so the build is unchanged; the point is that they are now immune to the flip. Each carries a warning telling the next reader NOT to simplify it back.

WHY THAT WAS MANDATORY RATHER THAN COSMETIC -- VERIFIED FIRST-HAND, not taken from the scout: Scratch4cii.lean:631::d_weak_holds proves the WEAK mirror TRUE at `(sR SlSw tApp) (sF SlSw [tApp])`, byte-for-byte the fixture that strong_shadow_false_at_d_own_sigma0 asserts the STRONG shadow is FALSE at. So spelled with the abbrev, that theorem would have flipped from true to FALSE at step 9 -- a false theorem, not a broken proof, which is the failure a build cannot catch for you. CascadeStable.lean's ShadowOver docstring also cites that symbol as the justification for the whole genericization, so re-pointing it silently would have left the contract citing a theorem that no longer says what it is cited for.

Also fixed: both citations of strong_shadow_false_at_raw carried a stale `(:332)` -- it is at :409. The numbers are DROPPED, not refreshed, per this file's own rule that "the anchors that keep are the symbols".

STEP 2 -- the leaf-refutation toolkit (Leaf.lean, 10 modules, green). Four additive declarations after leafNodeB_correct: leafPublic_bare, NotLeafName, not_leafNode_of_notLeafName, bare_subjNode_not_leafNode. The gap is real and was verified first-hand: EVERY existing "a bare subject is not a LeafNode" fact in the tree is a `by decide` pin at a FIXED schema (Leaf.lean:1180 at Sw, :1229 at SwEmptyRel, the Scratch4cii twin at SlV), and none is usable at the quantified S that the ~19 post-flip goals will face.

SABOTAGED, on the one claim in it that could be wrong: NotLeafName p is `p = BARE or isLeafPred p = false`, and its docstring claims the two disjuncts are non-redundant. Tested rather than asserted -- collapse it to the second disjunct alone. rc=1, and the second error names the reason exactly: `|- isLeafPred BARE = false`, unprovable because Leaf.lean:210::isLeafPred_bare proves it TRUE. BARE is dot-CARRYING, so dot-freeness never covers it, and that asymmetry is the whole reason LeafNode needs its `leafPublic != ""` conjunct. Restored: rc=0, 1089 jobs. The observed output lives in the NotLeafName docstring, where the next person tempted to simplify it will be standing.

STEPS 3-10 REMAIN, and both recorded risks are unchanged and un-spiked -- in particular the Class-B question (does the checkPublic guard reach the byte-pinned graph_correct?) must be answered BEFORE step 7 is started, not assumed during it.

Trial close-the-loop for this session, mirrored from the root session-log. lint line: `task lint: clean (12 checks, 154 task file(s) parsed)`. read: board + HANDOFF. Honest note, since the trial measures exactly this: `task.py board` was the FIRST command of the session and named the next action correctly, so the query did replace the file read for ORIENTATION -- but it did not replace HANDOFF.md and could not have. `show P3` is 35KB and overflowed context, so the item detail came from tasks/P3-*.md read directly, and the traps / read-first list / exit procedure came from HANDOFF.md and the scope doc. For this session the query was ADDITIVE, NOT SUBSTITUTIVE. That is the outcome the trial exists to detect, and the reason the read-line is a required literal rather than a summary. Actionable consequence for the cutover-or-keep-both decision: `show` has no bounded mode, and a per-item read that cannot fit in a context window is not a replacement for a file -- TT-1 should treat that as a blocking gap, not a polish item.

### 2026-08-31

Steps 3-5 landed green (TtuTargetsSat + additive _gen chain; NoLeafSubjects with a two-layer witness whose sabotage bit twice, S12/S13; the pre-widen). Abbrev STILL UNFLIPPED. Pre-widen is PARTIAL: only 3 of the 6 'free' subjNode sites were free -- CascadeStable.lean:919, CascadeStrataSettle.lean:685 and :1246 quantify over rewriteClosure S t, whose subject predicate is not bare, so bare_subjNode_not_leafNode does not apply. 5 obligations outstanding, not 2. NEXT EDIT: place the NoLeafSubjects -> TtuTargetsSat S NotLeafName bridge (it is List.mem_append_left, since schemaRewritesL = schemaRewrites ++ leafRewrites at LeafRules.lean:106) in a module importing both LeafRules and ReconcileCorrect; only the seed-side NotLeafName t.subject.predicate is then unowned. Steps 6-10 blocked on P20. Full record: PROOF_STATUS ## Session 2026-08-31 sec 3-4; new traps at scope doc 11.13 (i) and (j).

### 2026-08-31b

Bridge LANDED: CascadeStable.lean::ttuTargetsSat_notLeafName_of_noLeafSubjects (mem_append_left), green 1089 jobs, 5 of a 6-cycle budget, sabotage on the containment DIRECTION (mem_append_right -> sole error in the tree). Also removed a FALSE sentence from the Lean source: the old rewriteClosure_subject_not_leafNode docstring taught that NoLeafSubjects is 'the same discipline on the OTHER rule list and does not discharge these'; schemaRewritesL = schemaRewrites ++ leafRewrites is a SUPERSET. Steps 6-10 UNBLOCKED (P20 closed ACCEPT). Still 5 obligations: the three rewriteClosure sites now need ONE premise (seed-side NotLeafName t.subject.predicate), not two, and remain undischarged; plus CascadeStable.lean:946/:956.

### 2026-08-31c

CLASS-B SPIKE ANSWERED -- REACHES, and on THREE pinned rows not one. Of the three sites passing shadow_graphRec_agree the arbitrary query's own relation, only CascadeStrataResettle.lean::graph_correct_w3d2_d reaches FullScope.lean::graph_correct (via CascadeStrataAssemble.lean::graph_correct_w3d2E_d at FullScope.lean:369, graph_correct's sole proof route); sites 1-2 (graph_correct_w3d / graph_correct_w3d2) die in the superseded Equiv.lean milestone theorems. Consumer sets re-verified FIRST-HAND by grep, not taken from the scout, because it is a gate-safety claim. headline_statements.txt rows 27/46/56 carry NO checkPublic (the nine that do: 28,30,31,32,34,36,53,59,64), so graph_correct AND W4WitnessDirect.correct_applies AND ::w3d2E_correct_applies all sit below the fence -- REFUTING the 2026-08-28c claim (repeated in HANDOFF.md) that the hql surface is one pinned row, and independently confirming scope doc 11.13 item (e). The cost lands on the two NON-VACUITY instruments, where an hql binder risks a hypothesis nothing satisfies; likely repair is migration onto checkPublic, not the binder. NOT ATTEMPTED -- user-visible scope change, needs an explicit user call, and P3's own record forbids smuggling it into step 7.

STEP 6, THE ONE FREE OBLIGATION, LANDED. CascadeStable.lean::shadow_graphRec_agree's hv3 pre-widened to the DerNode-or-LeafNode form at the wAll node with ZERO new premises -- State.lean::wAllNode is Variant.wAll while Leaf.lean::LeafNode forces Variant.plain via on != STAR + DirectCorrect.lean::objNode_plain, so the LeafNode disjunct dies by the same variant mismatch DerNode already used. Two uses weakened via Or.inl (the CascadeStrataSettle.lean:960 pattern), so step 9 is 'delete two wrappers'. Green first try, 1089 jobs; 3 build cycles of a 6 budget, the single red being the deliberate sabotage.

SABOTAGE, and it corrected itself once: wAllNode is excluded by BOTH of leafNodeB's shape conjuncts, so dropping either alone leaves the pin green and proves nothing. Dropping both fired it -- 'Tactic decide proved that the proposition leafNodeB Sw (wAllNode ...) = false is false' -- but it was NOT the only error: Leaf.lean:556 (leafNodeB_correct) also broke, which is the instrument being controlled alongside the subject. Both counts are a LOWER bound since Lean does not build dependents of a failed module (2026-08-30d trap recurring). New pin Leaf.lean::wAllNode_not_leafNode, discriminating against the pre-existing ::minted_leaf_is_leafNode at the same schema/type/predicate.

4 OBLIGATIONS REMAIN, NOT 5. hv1 deliberately NOT bundled: hunt does not refute a minted leaf name, and the premise cannot be phrased locally because ReconcileStars.lean::checkFn_agree_of_graphRec{,_cd} hand hag exactly that hypothesis (11.13 trap (g)). Seed-side NotLeafName t.subject.predicate still has no owner; scout reports the only workable shape is a new store-level NoLeafStoreSubjects T threaded at ~20 sites -- AGENT OUTPUT, unverified, sizing input only. Full record: PROOF_STATUS ## Session 2026-08-31c.

### 2026-09-01

THE CLASS-B REPAIR IS ADJUDICATED -- user call -- and this item now carries NO open decision.

DECISION: headline_statements.txt rows 46/56 (W4WitnessDirect.correct_applies /
::w3d2E_correct_applies) are RE-STATED over GraphModel.checkPublic. The hql binder is
REFUSED on them. Row 27 (graph_correct) KEEPS the binder accepted 2026-08-28 -- that call
is not reopened; it is the internal-layer statement, not a satisfiability instrument.

GROUNDS (short form; full argument in PROOF_STATUS `## Session 2026-09-01` sec 1):
(a) rows 46/56 are satisfiability witnesses with q universally quantified, so an
    hql : publicOfLeaf S q.object.type q.relation = none binder puts a schema-dependent
    hypothesis on the very declarations whose job is to detect unsatisfiable hypotheses --
    the failure FullScope.lean::graph_correct_public's docstring already refuses for
    final_applies.
(b) The migration is a landed precedent (seven declarations, 2026-08-28c, none gained a
    hypothesis), and fence_changes_answer -- the pin that makes the fence contentful -- is
    stated at Sd, the SAME schema rows 46/56 are instantiated at.
(c) checkPublic models the real public WildcardIndex.check; the hql binder models nothing
    in Python.
Nothing true is given up: post-re-point the unguarded statement is machine-checked FALSE,
so the choice was only WHICH weakening.

FOUR CONDITIONS, all binding on the repair session:
 1. Own session, own green commit, landing BEFORE step 7 (provable on today's tree). This
    is what discharges "must not be smuggled into step 7" -- by sequencing, not deferral.
 2. Sabotage the migrated witnesses' NON-fence branch. fence_changes_answer proves the
    fence fires, NOT that the witness still exercises graph_correct through the other
    branch. Discriminating pair, per Leaf.lean::wAllNode_not_leafNode.
 3. Re-verify the two paragraphs 2026-08-31c labelled UNVERIFIED: headline_definitions.txt
    needs no regeneration; audited_theorems.txt pins names only. Not from prose.
 4. Doc sweep in the same commit (rows 46/56 are a deliberate golden edit); re-run
    verify.sh lean after any *.md edit.

KNOWN UNKNOWN (sizing input, not a finding): row 28's fence branch takes sigma.schema = S
from CascadeStrataAssemble.lean::reachedByW3d2E_schema, reusable by row 56 -- but row 46
hypothesises ReachedByW3d2C and no reachedByW3d2C_schema appeared in a NAME GREP of
formal/lean/ZanzibarProofs/. May be a structure field (cf. CascadeInv.lean:53-114 exposing
.schema/.schemaEq), may exist under another name, may need landing. That is a grep, not a
build -- resolve it in the kernel.

Docs re-pointed this session so nothing still defers to the user: HANDOFF.md banner + P3
row + P3 item block; formal/HANDOFF.md (the refuted "ONE pinned row" line, struck in
place); docs/latent-gaps.md ("what would close it" is now two moves); scope doc sec 11.13
(e) and (l). No Lean file was opened for edit.

KNOWN UNKNOWN CLOSED (same session it was raised). Row 46's fence branch does NOT need a
new lemma: sigma.schema = Sd composes from two that already exist --
  CascadeStrataSettle.lean::reachedByW3d2C_toW3d2 : ReachedByW3d2C -> ReachedByW3d2 (:2669)
  CascadeStrata.lean::reachedByW3d2_schema : ReachedByW3d2 -> sigma.schema = S (:433,
    #print axioms-audited at Audit.lean:950)
i.e. `reachedByW3d2_schema (reachedByW3d2C_toW3d2 h)`. The earlier NAME GREP failed only
because the searched-for name was wrong: the C-chain reaches the schema fact through the
plain W3d-2 chain rather than carrying its own projection.

(!) SOURCE READ, NOT A KERNEL CHECK -- both symbols have exactly the types the composition
needs and it typechecks by inspection, but no build was run. Let the kernel confirm it;
do not cite this note as the proof. What it changes is SIZING: the pessimistic branch
(land a new lemma on an audited signature, with the cone that implies) is off the table,
so the migration is two statement edits plus condition 2's sabotage.

Also superseded: docs/latent-gaps.md's guess that :46 might have to come a fortiori from
:56 via the one-way toC_applies. Unnecessary -- both rows discharge their own fence branch.
