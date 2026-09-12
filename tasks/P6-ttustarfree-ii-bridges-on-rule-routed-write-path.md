---
id: P6
title: ttuStarFree (ii) -- bridge on the LEAF-routed write path; P3 LANDED 2026-09-05b, collision gone
brief: P3 LANDED: increment B bridges on the LEAF-routed list (rawWriteTuples), never the public name; 38-cone is pre-flip
pri: NOW
size: M
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 1c868fadf76b
created: 2026-08-20b
moved: 2026-09-12
updated: 2026-09-12
closed:
---

Materialise the in-bridge on the rule-routed write path so the widened star-freeness
predicate is actually inhabited.

**`NOW` as of 2026-09-05b, by mechanism not by judgement**: `P3` landed and closed, this
was the top `NEXT` row, and its only blocker was the textual collision recorded below — so
it moved up. **Re-rank freely.** What `P3` changed for this item: the write leg is no longer
`writeLoggedOne` over the public closure — `GraphState.writeLoggedRules` folds
`rewriteClosureL S (rawWriteTuples S t)` (`Cascade.lean:190-191`), the remove leg folds the
SAME list (`:340-341`), and `affectedKeys` dirties the PUBLIC key through `publicOfLeaf`
(`:542-546`). **Increment B must bridge on that leaf-routed list**; a bridge keyed on the
public relation name would land on a node the write leg no longer touches — the same
leg-asymmetry class the kernel refuted in `P3`'s first attempt, where a write-then-remove
left a ghost grant (PROOF_STATUS `2026-09-05b` §2). Also inherited from `P3`: the dirty-key
list `cascadeKeysAbove` and the enum candidates `enumJob2(D).cands` are `.eraseDups` sets
(membership via `mem_cascadeKeys_iff_above` / `List.mem_eraseDups`) — any increment
touching `affectedKeys` or the candidate lists re-measures `two_stratum_cascade`'s
multiplicities (expect `1…5`) before regenerating a golden (PROOF_STATUS `2026-09-05b` §10).

## Traps

⚠ **`P3` LANDED 2026-09-05b, so "NOT parallel-safe with `P3`" is MOOT** — the collision
below is kept as the record of why the two could not run concurrently, not as a live
constraint. The "38-module cone" figure in it is **pre-flip and unreproduced** (the
2026-08-30c Log entry already flagged its lineage as a census rooted at the wrong module);
re-measure with a probe wave before quoting it. The live constraint now is the one above:
**bridge on the LEAF-routed list (`rawWriteTuples`), never on the public relation name.**

⚠ **Historical (superseded by `P3` landing): "It can run in parallel with `P3`" was WRONG,
and this row carried it for weeks**
(corrected 2026-08-20b). Logically independent, **textually colliding**: both re-point
`RulesWrite.lean::writeRules` and `Cascade.lean::writeLoggedOne`, both move `FoldAdmits` +
`Exec.lean::foldAdmitsB` in lockstep (⚠ **21 of 24 sites, not all 24 — three must STAY on
the σ0 side**; `PROOF_STATUS.md:4897`, `TK67`), and **both pay the same 38-module cone** — whichever
lands second re-pays it. Land increment A (additive, zero-cone) and stop, or sequence B
after `P3`; never concurrently. **Probe with `#eval` before paying the cone, exactly as
`P3` did**: `CascadeStable.lean`'s `writeLeg_reach_stable` family says a write leg does not
change reachability at these nodes, and **an in-bridge DOES change reachability — that is
its purpose**, so those statements may go FALSE at a bridged state rather than merely
needing a new case. The change is also **INERT on every corpus** (measured 2026-08-20:
`bridged_in_shapes` empty on all 26 `corpus.SCHEMAS` and every extended set bar one,
fragment-excluded), so the gate cannot see it and all evidence must be new Lean pins —
[`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) §"The INERT change" governs, as
for part (i). Increment B also **inverts
`extractor.py::_edge_projection`'s `P2` projection** (it drops PYTHON `w_any` rows because
"Lean never creates them"); its docstring is already false. Detail: ledger `2026-08-20b`.

⚠ **DO NOT DROP IT.** Without `ttuStarFree`, `graph_correct` and `backend_equivalence` are
machine-checked **FALSE** — not merely unproven. Part (i) is **INERT**: part (ii)
materialises the edge, and the rest of the leg is inert until it lands.
`W4Fragment.ttuStarFree` must stay **UNCHANGED** until (ii) is in.

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- board pointer: `ttuStarFree` **(ii)** — bridges on the rule-routed write path. **Promoted `NEXT` → `NOW` MECHANICALLY on 2026-09-05b** — `P3` LANDED (write leg now folds `rewriteClosureL S (rawWriteTuples S t)`, `formal/lean/ZanzibarProofs/GraphIndex/Cascade.lean:190-191`), so "NOT parallel-safe with `P3`" is moot and **increment B must bridge on the LEAF-routed list, not the public one**. Fresh evidence 2026-08-31b that this is a live hole: `ttuStarFree` classifies **SILENT** in the `W4Fragment` scope pin (`formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE`)

`formal/CORRESPONDENCE.md` §7 (`ZT-P5-NEW`);
`formal/lean/ZanzibarProofs/GraphIndex/UsStarWrite.lean::Schema.isStarTuplesetThrough` /
`formal/lean/ZanzibarProofs/GraphIndex/UsStarWrite.lean::Schema.isSubjectWildcardUserset`;
`ensureInBridges` / `ensureBridges`; `writeRules` / `writeLoggedRules`; `derive_schema_info`'s
second loop.

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-20b`), which is an upper bound on the real creation date, not a measurement. Summary, traps and read-first come from the `### P6` item block verbatim; the board pointer is the first line of Read first.

### 2026-08-30c

Sizing flag, filed from P3's 2026-08-30c census. This row's '38-module cone' figure shares the lineage of P3's recorded '42 modules', which was SETTLED WRONG this session: 41+root is reproducibly the reverse import cone of DirectCorrect.lean and RulesWrite.lean, while CascadeStable.lean's is 20 (+root = 21), so the recorded figure was a delegated census rooted at the wrong module. I did NOT measure P6's own cone, so this is a flag, not a correction -- do not overwrite 38 with a number nobody measured. Re-measure before using it to decide the P3/P6 parallel-safety question, and publish the symbol list and counting unit with the result: four sessions of censuses disagreed not about the tree but about what a 'site' is. Method and evidence: scope doc sec 11.13 item 2, PROOF_STATUS '## Session 2026-08-30c' sec 2.

### 2026-08-31b

Fresh evidence this is a LIVE hole: ttuStarFree classifies SILENT in the new W4Fragment scope pin (test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE). Probe wrote 'folder:* parent doc:d1' onto a TTU tupleset: ADMITTED. _validate_ttu_tuplesets rejects userset restrictions in tuplesets but deliberately keeps wildcard ones ('star tuplesets are this repo's deliberate object-wildcard extension'). So the field graph_correct depends on is one Python does not enforce.

### 2026-09-05b

2026-09-05b: P3 LANDED, so the 'NOT parallel-safe with P3' blocker is gone and this row is promoted to NOW MECHANICALLY (top NEXT row; user may re-rank). Re-scope before starting: the write leg now lives at Cascade.lean:190-191 GraphState.writeLoggedRules := (rewriteClosureL S (rawWriteTuples S t)).foldl writeLoggedOne, and the remove leg mirrors it (:340-341); RulesWrite.lean::writeRules and Cascade.lean::writeLoggedOne are byte-unchanged. Increment B's in-bridge must be materialised on the LEAF-routed list (rawWriteTuples), not on the raw public tuple, or it re-creates the ghost-grant divergence PROOF_STATUS 2026-09-05b sec 2 refuted. The definition pin is 250 rows now; expect a pin diff on writeLoggedRules/removeLoggedRules and adjudicate it in formal/history/ (scope doc trap (ff): the pin shows the body that moved, not the meaning changes through it).

2026-09-05b addendum: the cascade's dirty-key list is now cascadeKeysAbove := (...).eraseDups and enumJob2(D).cands is deduped (CascadeStrataEnum.lean) -- both are faithfulness mirrors of processor.py landed with P3 after the flip doubled an exponential derived-arm stacking. Any increment here that touches affectedKeys or the enum candidates inherits those eraseDups and their membership lemmas (mem_cascadeKeys_iff_above, List.mem_eraseDups); re-measure two_stratum_cascade multiplicities (expect 1..5) before regenerating any golden.

### 2026-09-06b

Board block rewritten 2026-09-05b (P3 landed; promoted NEXT -> NOW mechanically; increment B must bridge on the LEAF-routed list). Task body reconciled 2026-09-06b: title/brief/summary/Traps/board pointer now say P3 LANDED and the collision is moot; the 38-module cone paragraph is kept as history and marked pre-flip/unreproduced. Old-vs-new source diff taken from git (077bb50 -> HEAD) by .scratch/tt1/drift_diff.py, transcribed here rather than left in .scratch.

### 2026-09-12

Sizing session (no Lean edited). User asked whether (ii) fits one session; answer delivered
was NO, and the four figures below are the evidence. Everything here is measured 2026-09-12
against the live tree, not transcribed from a doc.

**1. The cone is MEASURED at last, and 38 was an undercount.** Counting unit: `.lean`
modules that transitively import the target, EXCLUDING the target itself and EXCLUDING the
root aggregator `ZanzibarProofs.lean` (it imports 60 modules so it lands in every cone and
inflates each count by exactly 1 without representing proof work). Tree total: 70 modules.
Per-target reverse cones -- `RulesWrite` 40, `Cascade` 20, `CascadeStable` 19,
`UsStarWrite` 8, `FullScope` 4 (this is where `structure W4Fragment` lives, `:280` -- there
is NO `W4Fragment.lean`), `Exec` 3. UNION of the six = **42 modules to re-prove**, 44 of 70
including the targets (63% of the tree), 44,410 lines in the cone. `RulesWrite` alone
carries 40 of the 42 because it sits under `Leaf` -> `LeafRules` -> the whole Cascade stack.
This independently REPRODUCES the 42 that `P3`'s 2026-08-28c census corrected upward, so two
separate measurements now agree and the 38 on this row is retired. The edited files are tiny
(`RulesWrite` 238 lines, `UsStarWrite` 402, `Cascade` 928) -- the cost is entirely
downstream. Measured twice: once by a subagent, once first-hand by the session, identical on
every number. Method: parse every `import ZanzibarProofs.*` line, invert, transitive closure;
zero dangling imports, so the graph is closed.

**2. The at-risk stability surface was under-reported, and the counting unit is the whole
story.** This row warned that `CascadeStable.lean`'s `writeLeg_reach_stable` family "may go
FALSE". Measured: the STABILITY CORE is **23 theorems / ~1,050 proof lines across 3 files**
in three tiers -- tier 1 `CascadeStable.lean` (10 theorems, 323 lines, the `writeLeg`/
`removeLeg` `reach`/`graphRec`/`checkFn`/`sem` duals), tier 2 `CascadeStrataSettle.lean`
(7 theorems, 383 lines, the `_sh`/`2` strata restatements, `writeLeg_sem_stable2` alone 98
lines), tier 3 the `_d` Direct-arm duplicates (5 theorems, 292 lines, `writeLeg_sem_stable2_d`
alone **126 lines**) plus `completeKey_writeLeg` (`CascadeSettle.lean:317`, 54 lines). A
PREFIX-WIDE count of declarations named `writeLeg*`/`removeLeg*`/`settledKey_*Leg*`/
`completeKey_*Leg*` is **52** across 5 files (adds the `probeDerived`/`checkFnR`/`inedges_eq`/
`extra_*` families). Both numbers are honest; they count different things. A session that
greps only `^theorem writeLeg` in `CascadeStable.lean` gets **14** and will under-budget by
3-4x -- that is exactly what happened at first pass this session before the sweep widened.
This is the `2026-08-30c` lesson recurring: four sessions disagreed not about the tree but
about what a "site" is, so any future figure here states its unit or it is worthless.

**3. Increment B is an INTENTION, not a specification -- and its anchors are stale.** The
entire design for (ii) anywhere in the tree is ONE bullet, `PROOF_STATUS.md:5736-5737`:
"Compose bridges into the rule-routed write path: `RulesWrite.lean:135 writeRules` and
`Cascade.lean:175 writeLoggedRules` are plain folds that materialise no bridges at all."
It names no new definition, states no lemma, sets no proof obligation -- and BOTH file:line
anchors are pre-flip stale (the live write leg is `Cascade.lean:190-191`). By contrast parts
(iii)/(iv) ARE specified: `:5290-5299` names two structures that must exist (a `StarSeed`
weakening; a bridge-completeness clause on `ReachedByRulesAdmitted`, called "the hardest of
the five") with a 163-occurrence / 18-module / 5-consumed census at `:5286-5289`. **The
downstream of (ii) is better specified than (ii) itself**, which is the strongest argument
that the next session here is a SPEC session, not a lift session.

**4. The hazard is no longer speculative -- the repo already measured it.**
`formal/probes/d3_negedgefree_postflip_2026-09-05.lean:25` arm (D), literal transcript in the
file header: "a hypothetical `approver.0 -> approver` bridge turns (A) red, so the instrument
is reachability-sensitive" -- edges 6, negTested 2, **negFree := false**. An in-bridge-shaped
edge has been MEASURED flipping `Inv.negEdgeFree` on the post-flip write leg. Mitigating
nuance, and the thing a probe must decide: every stability theorem is stated at an UNMAPPED
key (`hunmapped : (dt, R, on) NOTIN cascadeKeys ...`, `CascadeStable.lean:367`), so the
survivable outcome is a NEW PREMISE (the bridged shape is mapped/dirtied) rather than a false
statement. Which of the two you are in must be decided for all THREE tiers, not just tier 1.

**5. Scope REDUCTION worth recording, the one piece of good news.** `ensureInBridges` and
`ensureBridges` already EXIST in Lean with `StructInv` preservation proved --
`UsStarWrite.lean:213::GraphState.ensureInBridges` (in-bridge, W1c),
`:274::structInv_ensureInBridges` (audited `Audit.lean:159`), `:256::ensureInBridges_mono`,
`:238::ensureInBridges_schema`, `ensureInBridges_edges_mem` (audited `Audit.lean:166`),
`ObjStarWrite.lean::ensureBridges` + `ObjStarClosure.lean::ensureBridges_creates_bridge`, and
a composed bridge-before-grant write already exists as `UsStarWrite.lean:228::writeUsStar`.
So (ii) is NOT "write the bridge machinery" -- it is "route the existing, already-proved
machinery from the leaf-routed write leg." `UsStarWrite.lean:112` says it outright: "no live
chain calls `ensureInBridges` yet." Likewise `TtuStarWide.lean` (277 lines, 19 decls) is the
SPECIFICATION and the decidability answer, not the lift: the widened predicate is already
proved a genuine weakening (`ttuStarFreeW_of_ttuStarFree`) and strictly wider at a store
(`narrow_rejects` false / `wide_admits` true), and part (iv)'s once-blocking question is
answered NO-BLOCK (`ttuStarFreeWB` decides `TtuStarFreeW` via `ttuStarFreeWB_iff`).

**6. TWO CITATION ERRORS ON THIS ROW, both fixed here rather than in place.** (a) This row's
summary and its `2026-09-05b` Log entry cite "PROOF_STATUS `2026-09-05b` sec 2" for the
ghost-grant divergence. It is **sec 3** (`:392-411`) -- two mechanisms, a fail-closed MISSING
grant (`:394-402`, `affectedKeys`' own-key branch tests `isDerived` on a leaf name that is
not a declared key, so the cascade never fires) and a fail-open GHOST grant (`:404-411`,
`Exec.lean::writeThenRemove_leaks_leaf_edge`, `::_leak_accumulates` unbounded under churn).
Section 2 (`:366`) is a DIFFERENT and more alarming finding -- a green `lake build` shipping
a FALSE headline, `Exec.lean:980::graph_correct_refuted`, sorryAx-free. (b) `FoldAdmits`:
verified first-hand at `PROOF_STATUS.md:4895` that it is 21 MOVE / 3 STAY, the three being
`RulesComplete.lean:91` (`ReachedByRulesAdmitted.step`), `RestrictBase.lean:470` and `:531`.
Note a THIRD live counting unit exists -- `:4266` says "19 Prop sites + 2 exec gates move, 3
stay" and `formal/HANDOFF.md:135-136` endorses THAT one as superseding. 21 = 19+2; the tree
agrees, the unit drifted. `TK67` still owns verifying the three against the current tree.

**7. Trap for the next reader: a NAME COLLISION.** `formal/HANDOFF.md:470` says "Step 7
co-landed: projection P6 is retired". That is the PYTHON `extractor.py::_edge_projection` P6
projection, NOT this task. The same file uses "P6" in both senses within 20 lines (`:54` "a
P6 leaf-family modelling limit"). Do not read "P6 is retired" as this row being done.

**8. The sizing precedent, which is why none of the above should be discounted.** On
2026-08-28c a session was asked this same question about `P3` -- the structurally analogous
flip -- and answered "3 sessions, not 1" after a nine-agent census with two adversarial
critics. `P3` then took **24 sessions** (24 session-log entries naming it between that answer
and its landing on 2026-09-05b). `P3` was also sized `M` and was later re-sized `M` -> `L`;
this row is still `M`. `P3` was additionally sized "5 sites / 4 decls / 2 files" and landed at
"62 + 13 decls / ELEVEN files" (`formal/HANDOFF.md:85-87`), a >10x miss, after the
write-leg-only version was kernel-refuted. Four estimates in this family have been corrected
UPWARD and none downward.

**What the next session should actually do** (recommendation, not a re-rank -- this row stays
a user-owned call): the probe wave this row already prescribes, which is zero-cone and
decisive. `formal/probes/d3_negedgefree_postflip_2026-09-05.lean` is DIRECTLY reusable -- kept
deliberately OUTSIDE the lake package (`:3-5`, "not part of the gated build, it is evidence
that can be re-run"), so a probe costs no cone; run recipe in the file at `:7-8`
(`lake env lean ../probes/<file>`); it already carries the four-arm subject/control structure
house rule 7 demands, and arm (D) is ALREADY an in-bridge sabotage, so you edit one arm rather
than build a harness. (!) Its single highest-value line for this task is the witness trap at
`:46-48`: the residue key domain must be routing-INDEPENDENT, built from store objects x
declared relations x {bare,.0,.1,.2}, NEVER from `sigma.nodes` -- because a leaf-routed write
CHANGES `sigma.nodes`, so a sigma-derived domain measures nothing. Also inherited: any
increment touching `affectedKeys` or the enum candidates drags in sec 10's eraseDups repair
(~18 sites -- 8 in `CascadeStrataResettle`, 4+1 in `CascadeStrataAssemble`, 2 in
`CascadeStrataSettle`, plus `CascadeStrata`, `CascadeStrataInv`, 3 in `CascadeStrataEnum`;
`cascadeKeys_eq_above` was a `rfl` and is now `mem_cascadeKeys_iff_above`) and requires
re-measuring `two_stratum_cascade` multiplicities (expect 1..5) before regenerating a golden.
Sec 10 item 6 (residual +1 per reconcile) is recorded as STILL OPEN at `:807`.

Ultracode session (11 agents: 4 spec/split/census/probe-design, 1 serial Lean probe, 5
adversarial skeptics, 1 synthesis). Attempted to COMPLETE (ii) and, failing that, to SPLIT it.
**Both answers are NO, and the reason is not effort -- it is a SCOPE DEFECT plus a missing
mechanism, and each needs a human decision.** All 5 skeptics refuted something; I reconciled
rather than averaged, and caught one false claim in my own synthesis (see CORRECTIONS 3).

**THE PROBE RAN, AND IT IS TRACKED.**
`formal/probes/p6_inbridge_stability_2026-09-12.lean`, committed with this comment, transcript
verbatim in its header. Kept outside the lake package like its `d3_` predecessor, so it costs
ZERO cone and `verify.sh` never reads it (grepped: no `probes` reference in `formal/verify.sh`).
**Re-run FIRST-HAND by this session, not taken on a subagent's word**: `rc=0`, 12,150 bytes,
output identical to the agent's report. Recipe (from the file):
`export PATH="$HOME/.elan/bin:$PATH" && cd formal/lean && lake env lean ../probes/p6_inbridge_stability_2026-09-12.lean`
Instrument IS controlled: the positive control arm (POS, a RAW unlogged edge into
`doc:d1#access`) went RED with `reachStable := false`, `graphRecStable := false`,
`checkFnStable := false`; BASE and NULL arms green; non-vacuity counts nonzero throughout
(`reachPairs := 1152`, `guardPairs := 168`, grid 546).

**WALL 1 -- the widened predicate is WIDER THAN ANYTHING ROUTING CAN INHABIT.** This is the
finding. Verified first-hand at `TtuStarWide.lean:72-76`: `TtuStarFreeW` requires only
`S.isSubjectWildcardUserset t.subject.type tr = true`, with **no `isDerived ... = false`
conjunct**. So it admits stores whose TTU through-shape is a DERIVED relation -- and at a
derived through-shape there is no node on the leaf-routed list for `ensureInBridges` to fire
on, because `isStarTuplesetThrough` and disjunct (a) both scan `S.defs` and a minted leaf
`<R>.<i>` is not a declared shape. The probe measured exactly this, and it is the KILL
CONDITION firing:
`("ROUTING (leaf-routed vs public-keyed)", { derivedKey := true, rawRels := ["approver.0"],`
`throughShapeDeclared := true, publicBridged := true, leafBridged := FALSE, legEdges := 1,`
`legEdgesIntoPublic := 0, legEdgesIntoLeaf := 1, bridgesOnLeafRouted := 0,`
`bridgesOnPublicKeyed := 1 })`
Read that pair: the write leg lands ONLY on the leaf (`legEdgesIntoLeaf := 1`,
`legEdgesIntoPublic := 0`), while the ONLY bridgeable node is the PUBLIC one -- which is
precisely the node this row's CRITICAL CONSTRAINT forbids bridging. **So part (ii) cannot
inhabit the predicate part (iv) already landed and audit-pinned.** Nobody noticed because
(iv) was scheduled on DECIDABILITY alone, and decidability was the only question asked.
**The payoff criterion also FAILED**: `("REPAIR", some { gridSize := 546, baseDrained := true,`
`bridgeDrained := true, baseAgree := false, baseMismatch := 14, bridgedAgree := FALSE,`
`bridgedMismatch := 9 })` -- bridging moves 14 mismatches to 9 but does NOT restore
graph-vs-`sem` agreement, which is the entire stated purpose of increment B.

**THE DECISION WALL 1 FORCES (user call -- deliberately NOT taken by this session).**
(a) Narrow `TtuStarFreeW` to untainted through-shapes. Cheapest. Re-opens part (iv): four
    audited names (`ttuStarFreeWB`, `ttuStarFreeWB_iff`, `ttuStarFreeWB_of_ttuStarFreeB`,
    `ttuStarFreeW_of_ttuStarFree`, pinned `formal/audited_theorems.txt:537-540`) and reds
    `[4b]`/`[4c]`/`[4e]`. GOOD NEWS: `WideWitness.SwT`'s `(folder,"viewer")` is `.direct`
    (`TtuStarWide.lean:226`), so `narrow_rejects` (`:247`), `wide_admits` (`:251`) and
    `unbridged_still_rejected` (`:267`) all SURVIVE a narrowing conjunct.
(b) Model the entity-middle half and close the recorded gap. A NEW, LARGER project than P6 --
    `formal/CORRESPONDENCE.md:964-973` records that half as DELIBERATELY unmodelled ("a
    fragment boundary, not model drift"), and it is Python's own answer to this exact case
    (`index_v4/wildcard.py::_ensure_entity_middles` / `::_sync_entity_middles`, I14).
(c) Teach `isSubjectWildcardUserset` about minted leaves. `UsStarWrite.lean:106-109` warns
    this breaks `bridgedInConcrete_elim` (audit-pinned `Audit.lean:134`) and
    `UsStarReach.inbridge`'s `hcp` field.
Choosing wrong SILENTLY is how the tree ends up with `graph_correct` true of a predicate no
implementation satisfies. Escalate before editing.

**WALL 2 -- the write leg would mint an edge the remove leg PROVABLY CANNOT RETRACT, and the
obvious repair is FORBIDDEN.** `count_removeLoggedRules` (`CascadeStrata.lean:738`) subtracts
exactly the closure-list count, and no bridge pair is ever an `edgeOfTuple` image because
`objNode` yields only `Variant.wAll`/`Variant.plain` (`State.lean:126-128`) while `wAnyNode`
is `Variant.wAny` (`State.lean:122`). **Verified first-hand: there is ZERO bridge-retraction
machinery tree-wide** -- grep for `removeInBridge|removeBridge|dropBridge|unBridge|
retractBridge|unbridge` over all of `formal/lean/` returns only `WideWitness.
unbridged_still_rejected`, an unrelated sabotage pin. And the guard repair is refused by a
recorded decision: `RemoveOccCount.lean:178-194` says the guarded twin
`reachedByW3d2E_untOccCount_notLeaf` was DELETED because "the guard is gone, not narrowed,
which is what keeps this from being the house failure mode (a theorem rescued by making its
counterexample inadmissible)". Adding `b.variant = Variant.plain` to
`reachedByW3d2E_untOccCount` (`RemoveOccCount.lean:143`) is exactly that forbidden shape.
This one IS many sessions of proof repair -- but only after a SECOND human decision: should
the Lean model grow a bridge-GC story, or should Python's presence-guard become ref-counted?
(Python's `_ensure_own_bridges`, `index_v4/wildcard.py:267-279`, is presence-guarded, one copy,
NOT ref-counted, and its retract dual is entity GC.)

**THE LOGGED/UNLOGGED VISE (why there is no third way).** UNLOGGED: `ensureInBridges`
(`UsStarWrite.lean:213-218`) adds via `addNode`/`addEdge` and pushes no delta, so
`writeLoggedRules_edge_delta` (`CascadeStable.lean:118-121`, audit-pinned `Audit.lean:761`)
goes FALSE, taking `writeLeg_reach_stable` (`:362`, pinned `Audit.lean:765`) and the whole
stability core. LOGGED: the bridged key becomes MAPPED (probe arms B-OBJ and B-SUB-L both print
`hazardUnmapped := false`), so every `hunmapped`-stated theorem goes VACUOUS at bridged keys
rather than false, and `cascadeKeys` multiplicity doubles (B-SUB-L `ckeys := 8`, 4 distinct) --
which `Cascade.lean:561-566` records as having "timed out ten conformance tests".

**PER-TIER VERDICTS (this REPLACES the hopeful "new premise suffices" framing).**
* Tier 1 (10 thms, `CascadeStable.lean`): **FALSE, NOT premise-repairable.** Probe arm B-SUB
  (bridge on the SUBJECT endpoint): `bridges := 2`, `hazardUnmapped := TRUE`,
  `hazardReachPre := false -> hazardReachPost := true`, t1 `reachStable`/`graphRecStable`/
  `checkFnStable` all false, verdict string `"FALSE - unstable AND ('doc','admin','d1') is
  UNMAPPED: no premise on (dt,R,on) saves the statement"`. The `hunmapped` escape genuinely
  holds here and still does not save it. This is the opposite of what the row hoped.
* Tier 2 (`CascadeStrataSettle.lean`): **UNDECIDED, zero information.** `guardPre := false`
  AND `guardPost := false` in ALL EIGHT ARMS including BASE and NULL, so no arm ever satisfied
  the tier-2 premises. The probe's own rule (`:434-436`) says a red BASE invalidates the arm.
  A replacement instrument is owed; do not read tier 2 as green OR red.
* Tier 3 (the `_d` Direct-arm decls): **partially measured** via `checkFnMatched`/
  `checkFnRStable` (false in B-SUB); the sem-level `_d` theorems were not measured at all.
* Tier 0, NOT in this row's census and not probe-measured: `reachedByW3d_edges_target_plain`
  (`CascadeStable.lean:292`, pinned `Audit.lean:763`, consumed `:2098`) and
  `reachedByW3d2_edges_target_plain` (`CascadeStrataSettle.lean:193`, consumed `:2694`,
  `:3289`, `:3366`, `:5104`, `:5250`) go hard-FALSE. Follows from `State.lean:122` vs
  `:126-128`; needs no run.
(!) Do NOT read arm B-SUB-L's `verdict := "GREEN"` as "logging the bridge fixes it". Four of
`verdictOf`'s six conjuncts quantify over UNMAPPED keys only and the bridge mapped 3 of 4, so
the green is bought by a ~75% collapse of the instrument's domain (`reachPairs` 1152 -> 288,
`guardPairs` 168 -> 42, `unmapped` 4 -> 1) with `reachStableAll := false` -- the probe's own
documented vacuity signature -- ignored by the verdict. The verdict function is the instrument
and it is not trustworthy at a mapped key.

**WHY IT DOES NOT SPLIT.** Every candidate boundary either leaves the bridge UN-CALLED (a
fourth repeat of part (i)'s inertness, with `W4Fragment.ttuStarFree` still uninhabited) or mints
the edge and takes the whole 42-module cone at once. Candidate (d) -- bridge on `FullScope`/
`Exec` only, cone 5 -- is REFUTED by the ROUTING measurement above, not by argument. Also:
"cone 0 implies gate green at the boundary" is FALSE here -- `statement_pin.py::lean_files` is
`LEAN_ROOT.rglob("*.lean")` and consults imports NEVER, so a new decl inside `formal/lean/`
can add a pin row at import-cone 0; and `doc_counts --check` runs inside the `lean` phase
(`formal/verify.sh:935`), so any audit-row addition reds `[4e]` until `FINAL_REVIEW.md` is
regenerated. Widening `TtuStarFree` additionally reds the HEADLINE statement pin: verified
first-hand that it appears in `formal/headline_statements.txt:44`, inside
`Zanzibar.W4WitnessDirect.fragment`.
The only two landable items are PREREQUISITES, not increments of B: (i) track this probe
[DONE in this commit]; (ii) turn the ROUTING measurement into a `decide` pin so K1 is
mechanically un-forgettable, which is a SPECIFICATION edit gated on the Wall-1 decision.

**CORRECTIONS -- including to my OWN earlier comment on this row today.**
1. **"38 was an undercount / is retired" (my 2026-09-12 comment, item 1) is WRONG.** It is a
   COUNTING-UNIT difference, which is grimly funny given item 2 of that same comment. Measured:
   union of the six reverse cones, excluding the root aggregator, = **42**; FOUR of the six
   targets (`Cascade`, `CascadeStable`, `Exec`, `FullScope`) are themselves members of that
   union; so **union minus all six targets = 38**, and **union union targets = 44**. The
   historical 38 is therefore RECONCILABLE as union-minus-targets, not an error. All three
   numbers describe one graph. 42 and 44 reproduced a third time this session.
2. **"23 theorems / ~1,050 lines / 3 files" (my same comment, item 2) was ALSO an undercount,
   twice over**: its enumeration summed to 22, not 23, AND it dropped the remove-leg duals in
   tiers 2 and 3. First-hand recount, unit = **theorem whose name matches
   `(writeLeg|removeLeg)_(reach|graphRec|checkFn|sem)_stable`,
   `(writeLeg|removeLeg)_reach_wAll_false`, or `(settledKey|completeKey)_(writeLeg|removeLeg)*`**:
   `CascadeStable.lean` **10**, `CascadeStrataSettle.lean` **18**, `CascadeSettle.lean` **1**
   = **29 declarations**. (The synthesis independently landed on a 28 floor under a slightly
   different unit; I did not average -- 29 is what I counted, and the unit is stated so it is
   re-checkable.) Add tier 0's two `_edges_target_plain` providers and the unconditional
   in-edge-fixity family (`CascadeStrataSettle.lean:4120`, `:4046`, `CascadeStable.lean:2002`)
   and the surface is larger still.
3. (!) **MY OWN SYNTHESIS AGENT MADE A FALSE CLAIM AND I AM NOT PROPAGATING IT.** It reported
   that "`RulesComplete.lean:91` / `ReachedByRulesAdmitted.step` does not exist ... there is no
   `step` constructor", and elsewhere called the constructor `write`. **Both are wrong.**
   Verified first-hand: the inductive is `RulesComplete.lean:111`, its constructor IS **`step`**
   at `:113`, `hadm` is its field at `:115`, and `ReachedByRulesAdmitted.step` is used at 8+
   sites (`CascadeStable.lean:1850`, `CascadeStrataSettle.lean:866`/`:1570`,
   `RestrictBase.lean:455`/`:473`/`:476`/`:533`/`:538`). ONLY the line number `91` is stale.
   So the FoldAdmits stay-site trap is sound and stays: the three sites are
   `RulesComplete.lean:115` (`hadm` of `ReachedByRulesAdmitted.step`), `RestrictBase.lean:470`,
   `RestrictBase.lean:531`. This is the standing rule earning its keep -- a subagent report is
   evidence, not a finding, and this one would have retired a VALID trap.
4. **The eraseDups distribution in my earlier comment describes the HISTORICAL repair, not the
   live tree.** Live, unit = mention-lines: `CascadeStrataEnum` **13**, `CascadeStrataAssemble`
   **5**, `CascadeStrata` **4**, `CascadeStrataSettle` **2**, `CascadeStrataInv` **2** =
   **26 lines / 5 files**, and `CascadeStrataResettle.lean` contains **ZERO** (my earlier
   comment put 8 there, the largest single entry). So the eraseDups repair is NOT forced by
   this work the way that comment implied.
5. **`affectedKeys` needs NO code edit** (contra the read that any bridge drags it in): the
   own-key branch is guarded by `d.node.name != STAR` (`Cascade.lean:542`) so a wAny-headed row
   yields `[]`, and the fan-out branch skips `v.name = STAR` (`:548`) while keeping downstream
   concretes (`:485-486`). **But the `two_stratum_cascade` multiplicity re-measure is still
   owed**, because a LOGGED bridge adds frontier rows (B-SUB-L `ckeys := 8`).
6. `PROOF_STATUS.md:5736-5737`'s stale `Cascade.lean:175` anchor is not alone -- the same
   pre-flip form also appears at `PROOF_STATUS.md:874`, `:1103`, `:1269`, `:1398`, `:1410`.
   Live `writeLoggedRules` is `Cascade.lean:190`.
7. Unverified by this session, flagged: `[cone]`'s def-pin closure simulation (242 -> 243), the
   live `doc_counts` values, `TtuStarWide`'s cone of 1, and the naming trap that
   `statement_pin.py::_refs` resolves receiver dot-calls by SUFFIX and takes all candidates when
   ambiguous (mechanism read, not simulated -- so do not name a preparation twin with a tail
   colliding with `.writeLoggedRules` / `.addEdge` / `.reach`).

**WHERE THE NEXT SESSION STARTS.** Not with Lean. With the Wall-1 decision above, presented to
the user with the audited-pin costs of (a)/(b)/(c). Then, ONLY if (a) is chosen, the first edit
is a SPECIFICATION edit and not increment B: add the `isDerived = false` conjunct to
`TtuStarFreeW` (`TtuStarWide.lean:72-76`) and to `ttuStarFreeWB` (`:81-89`), re-prove
`ttuStarFreeWB_iff` (`:94`), expect `ttuStarFreeW_of_ttuStarFree` (`:135`) to still go through,
and add a FOURTH `WideWitness` pin at a DERIVED through-shape proving the widened predicate now
REJECTS it -- that pin is the red-to-green evidence and the thing that makes K1
un-forgettable. Do NOT touch `W4Fragment.ttuStarFree` (`FullScope.lean:298`, structure `:280`):
widening it without materialising the edge IS the machine-checked-FALSE state. Then stop and
re-plan; increment B proper does not begin until Walls 1 and 2 are both decided.
