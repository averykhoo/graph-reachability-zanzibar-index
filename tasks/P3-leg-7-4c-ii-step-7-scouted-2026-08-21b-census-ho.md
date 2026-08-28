---
id: P3
title: leg 7 4c-ii + step 7 -- all pre-4c-ii work DONE 2026-08-28c; the cone remains, sized 3 sessions
pri: NOW
size: L
deps: []
related: [P6]
parent:
labels: [formal]
source: board
source_hash: 90a1f8ce5f73
created: 2026-08-21b
moved: 2026-08-28d
updated: 2026-08-28d
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
expectation, Route B's two premises. **Read §11.10 before touching the cone.**

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule; enforced by `migrate.py::check_formal_pointer`, not merely stated)
- board pointer: [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §11.9

PROOF_STATUS `## Session 2026-08-21b` then `2026-08-20b`, scope doc §11.9
then **§11.10 (the traps)**, `GraphIndex/Scratch4cii.lean`, §11.7, §11.5; completion
criterion: PROOF_STATUS `2026-08-16c`, its numbers re-derived from `formal/FINAL_REVIEW.md`'s
generated ledger, never prose. Then `CascadeStable.lean::shadow_graphRec_agree` /
`::reachedByW3d_shadow` / `::untaintedShadow_writeLeg`, `LeafRules.lean::GraphState.writeRulesRaw`,
`Leaf.lean::publicOfLeaf`, `Exec.lean::foldAdmitsB`, `extractor.py::_edge_projection`.

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
