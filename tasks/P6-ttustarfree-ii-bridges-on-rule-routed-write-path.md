---
id: P6
title: ttuStarFree (ii) -- bridge on the LEAF-routed write path; P3 LANDED 2026-09-05b, collision gone
brief: Step 3 SPLIT: 3a (twins+hinge+sweep) LANDED 2026-09-13d. Start at 3b: 3 re-points + the measured cone
pri: NOW
size: L
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 1c868fadf76b
created: 2026-08-20b
moved: 2026-09-13d
updated: 2026-09-13d
closed:
---

Materialise the in-bridge on the rule-routed write path so the widened star-freeness
predicate is actually inhabited.

**STEPS 0, 1, 2 AND 3a ARE LANDED; START AT STEP 3b — THE CONE PAYMENT.** Step 3 was SPLIT
on 2026-09-13d after the composition was written and MEASURED: **3a** landed the bridged
twins, their preservation theory, the `EvalEq` hinge and an 11-mutation sweep, all additive
and zero-cone; **3b** is the three re-points and the fallout. The re-points are exactly
`writeLoggedOne` → `bridgePreLogged`, `LeafRules.lean::writeRulesRaw` → `writeBridgedOne`,
and `removeLoggedOne`'s then-branch wrapped in `releasePostLogged` — nothing else. The
measured fallout of doing all three (`LeafRules` 6 errors, `Cascade` 7, `CascadeStable` 27
across 17 declarations, nothing past that measured) and the one blocking obligation
(`TK68`) are on the `2026-09-13d` Log entry. Everything below about step 2 still holds.

Step 2 (2026-09-13c)
put every additive definition in its FINAL home: `Cascade.lean::ensureInBridgesLogged` /
`::inBridgeOnly` / `::releaseInBridges` / `::releaseInBridgesLogged`, beside `pushDelta` and
`removeLoggedOne`, reachable because the `Cascade → UsStarWrite` import was measured free
(acyclic; whole-tree build green, job count unchanged). **So step 3 is a pure composition
edit, with no file move and no anchor churn.** Step 2 also fixed the model-fidelity bug step
1 found — `ensureInBridges` now carries Python's presence guard, `(0,1,2,3)` copies became
`(0,1,1,1)` — at the cost of re-proving the two audited names, **both of which kept their
statements**. The two `CORRESPONDENCE.md` §7 boundary entries are written and the
phantom-subject property is now a gated pin (`tests/test_p6_phantom_subject.py`). Read the
`2026-09-13c` Log entry for what step 3 inherits, including the ONE NEW BOUND on it: the
stratum-2 `checkFn` gap.

**Step 0's record, kept because its walls still govern.** Both walls were DECIDED on
2026-09-12b and the plan is that key's Log entry; step 0 executed it, and **corrected its
reason**. Wall 1
(the "scope defect") is dissolved — but NOT by `W4Fragment.term`, which the probe store
`Sd` **satisfies** (`htermB Sd Td = true`, measured). The exclusion is the TAINT FILTER:
`schemaRewrites` drops derived defs, the arm's own owner key is tainted via `exprRefs`'s
`.ttu` case, so at such a store `schemaRewrites = []` and every TTU-star predicate —
narrow and widened alike — is **VACUOUS**. `Sd` leaves `W4Fragment` at `computedOrDirect`,
for EVERY store. Landed: `TtuStarWide.lean::ttuStarFreeW_through_untainted` (the Wall-1
lemma, consumer-side) plus 14 `decide` pins in `::Zanzibar.RoutingArmWitness` /
`::Zanzibar.TermNonvacuityWitness`, a mutation-sweep table, and a `CORRESPONDENCE.md` §7.3
entry. No edit to `TtuStarFreeW`, no audited name re-opened. Wall 2 is unchanged: the remove
leg gets a NEW `releaseInBridges` mirroring Python's `_maybe_remove_bridges`, LOGGED on both
legs because Python's is — **built at step 2, not yet composed**. Remaining order is the
`2026-09-12b` entry's steps 3–4; step 3 is the cone payment (`P3`-class, several sessions).
Re-sized `M` → `L` on 2026-09-13c, as that plan said to.

What `P3` changed for this item: the write leg is no longer
`writeLoggedOne` over the public closure — `GraphState.writeLoggedRules` folds
`rewriteClosureL S (rawWriteTuples S t)` (`Cascade.lean:190-191`), the remove leg folds the
SAME list (`:340-341`), and `affectedKeys` dirties the PUBLIC key through `publicOfLeaf`
(`:542-546`). **Increment B must bridge on that leaf-routed list**; a bridge keyed on the
public relation name would land on a node the write leg no longer touches — the same
leg-asymmetry class the kernel refuted in `P3`'s first attempt, where a write-then-remove
left a ghost grant (PROOF_STATUS `2026-09-05b` §3, `:392-411` — the row said §2 until
2026-09-12b; §2 is the false-headline finding). Inside the fragment the leaf-routed list at
an untainted through-shape IS the public node, so the constraint and the bridge target
coincide there. Also inherited from `P3`: the dirty-key
list `cascadeKeysAbove` and the enum candidates `enumJob2(D).cands` are `.eraseDups` sets
(membership via `mem_cascadeKeys_iff_above` / `List.mem_eraseDups`) — any increment
touching `affectedKeys` or the candidate lists re-measures `two_stratum_cascade`'s
multiplicities (expect `1…5`) before regenerating a golden (PROOF_STATUS `2026-09-05b` §10).

## Traps

⚠ **STEP 3b IS BLOCKED ON `TK68` — and the blocker is a FIDELITY gap, not a proof
convenience.** `Cascade.lean::reachedByW3d_edge_source_ne_R` (audited, `Audit.lean:714`)
goes FALSE the moment the write leg bridges: a bridge edge is sourced at its CONCRETE
endpoint, whose predicate can be the derived `R`. Its ONE Lean consumer,
`::reachedByW3d_Rnode_not_source`, needs `isSubjectWildcardUserset S dt R = false` at the
same key it already knows is derived — which is Python's second `UnsupportedByGraphIndex`
scope rejection, and `FullScope.lean::GraphAdmission` has `objWild` for the FIRST one and
no field for it. ⚠ **Do not try to save the general statement with a premise**: a literal
`[x:*#R]` restriction at an untainted key `(x, R)` is legal Python and bridges a node whose
pred is `R`, so `a.pred ≠ R` is false as a general claim whatever field is added. The
wrapper survives because it fixes the type to `dt`. Detail on `TK68`.

⚠ **`writeLoggedOne_watermark` ALREADY EXISTS, in `CascadeStable.lean`.** Step 3a tried to
add it to `Cascade.lean` and the build refused with `has already been declared`. Any
step-3b lemma named for the write step must be grepped before it is written — the
`writeLoggedOne_*` / `writeLoggedRules_*` families are spread across `Cascade.lean` and
`CascadeStable.lean`, not gathered in one file.

⚠ **STEP 3 MAY NOT ROUTE A STRATUM-2 USERSET-SUBJECT OBLIGATION THROUGH `checkFn`**
(measured 2026-09-13b, recorded as a `CORRESPONDENCE.md` §7.3 boundary 2026-09-13c). At the
bridging CEILING the two Lean-side readers disagree with each other: `GraphState.checkFn`
(`GraphIndex/ReconcileWrite.lean`) reads `false` where `GraphModel.check`
(`GraphIndex/State.lean`) and `sem` both read `true` — at userset subjects, on the
**stratum-2** derived relation only, never stratum 1. Four such keys, printed as rows in
`formal/probes/p6_step1_logged_bridge_2026-09-13.lean` §tier-2. This is NOT a bridge
question and bridging does not fix it (the count is 4 at `G-BR-TGT` and at `G-CEIL` alike);
it is a gap between two model readers with no Python counterpart —
`index_v4/wildcard.py::WildcardIndex._check_derived` is the single shipped read path and the
parity suite pins it. `CascadeStrataSettle.lean::writeLeg_sem_stable2`'s tier is the one
that consumes `checkFn` at exactly these keys, so a step-3 proof that leans on it there will
be settling an obligation the reader cannot discharge.

⚠ **Do NOT "simplify" `ensureInBridges` by dropping its presence guard, and do not weaken
`ensureInBridges_count_le_one` to a reachability claim.** The guard is fidelity, not
optimization (Python guards; `UsStarWrite.lean::ensureInBridges`'s docstring carries the
measurement). It is swept: `Cascade.lean` §"CONTROLLED — MUTATION SWEEP…" row `M1` reds nine
declarations including `InBridgeLegWitness.logged_second_call_silent`, and `M10` shows the
`≤ 1` bound is TIGHT. The reachability-level idempotence the old docstring claimed is true
and is not enough once a live chain calls the bridge once per routed member — which is
exactly what step 3 makes it do.

⚠ **The import direction is `Cascade → UsStarWrite`, and getting it backwards is a CYCLE.**
The step-2 defs sit in `Cascade.lean` because `writeLoggedOne` / `removeLoggedOne` (the
step-3 composition sites) are there and must see them. `UsStarWrite.lean` therefore must
never import `Cascade` — a plausible-looking "put the logged variant next to the unlogged
one" edit that would make step 3 impossible rather than merely awkward.

⚠ **The 2026-09-12 "scope defect" was measured OUTSIDE the fragment — do not re-derive it,
and do not re-derive the WRONG REASON for it either.** The ROUTING and REPAIR arms of
`formal/probes/p6_inbridge_stability_2026-09-12.lean` run on `Sd` (`:902-906`), whose
`doc#control := approver from parent` has a DERIVED through-relation. **2026-09-12b said
`W4Fragment.term` rejects that store and 2026-09-13 MEASURED that it does not**
(`htermB Sd Td = true`): `NoTtuTarget` quantifies over `schemaRewrites`, which DROPS DERIVED
DEFS, and the arm's own owner key `("doc","control")` is tainted too — `exprRefs`'s `.ttu`
case adds the derived target ref via the tupleset's parent types — so the arm never reaches
the quantifier. What actually holds is stronger: `schemaRewrites Sd = []`, so BOTH
`ttuStarFreeB` and `ttuStarFreeWB` are **vacuously true** there (the widening is not merely
satisfied, it is not ENGAGED), and `Sd` fails `W4Fragment.computedOrDirect` for EVERY store.
All of it is pinned in `GraphIndex/TtuStarWide.lean::Zanzibar.RoutingArmWitness` — read those
pins rather than re-arguing this. So "`TtuStarFreeW` admits a shape no routing can bridge" is
true of the standalone predicate and irrelevant to the fragment it is a field of. The in-scope payoff
number (mismatches after a LOGGED leaf-routed bridge on an UNTAINTED through-shape) has NOT
been measured — that is plan step 1, and it is the go/no-go. Likewise arm B-SUB's tier-1
FALSE is the UNLOGGED bridge; Python's bridge is logged (`core.py:1101-1107`), and the
logged variant makes `writeLeg_reach_stable`'s `hunmapped` premise exclude the bridged key by
design (`CascadeStable.lean:367` quantifies over the POST-write `cascadeKeys`), so read
B-SUB-L's shrunken domain as the premise working, not as vacuity — and build the per-domain
instrument before believing either reading.

⚠ **`P3` LANDED 2026-09-05b, so "NOT parallel-safe with `P3`" is MOOT** — the collision
below is kept as the record of why the two could not run concurrently, not as a live
constraint. Its "38-module cone" is one of THREE honest numbers for one graph, measured
2026-09-12 (union of the six reverse cones excl. root aggregator `42`; minus the six targets
`38`; with them `44`) — state the unit. The live constraint now is the one above:
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
- **The plan is the `2026-09-12b` Log entry** (`show P6`): decisions on both walls, steps 0–4, what each step must not touch. **Start at step 3** — steps 0, 1 and 2 landed 2026-09-13 / 2026-09-13b / 2026-09-13c, and the first two of those Log entries correct the entry before them. ⚠ **Read newest-first and do not trust a payoff figure without re-reading its source**: 2026-09-12b mis-attributed the `14 → 9` payoff failure to the out-of-fragment store `Sd`, step 0 carried that forward, and step 1 found it was measured on the IN-FRAGMENT `Sp` all along (`formal/probes/p6_inbridge_stability_2026-09-12.lean:872-887` is written against `Sp`, `Sd` appears only in `§7`).
- **The `2026-09-13d` Log entry is what step 3b starts from** — the three re-points, the
  measured per-module fallout, the three decisions taken (not `writeUsStar`; `writeRules`
  stays unbridged; the prologue is a named def, not a `let`), and the sweep's two
  instrument findings. The code: `formal/lean/ZanzibarProofs/GraphIndex/UsStarWrite.lean`
  §"★ `writeBridgedOne` preservation", `::BridgedWriteWitness` and §"CONTROLLED — MUTATION
  SWEEP over everything `P6` step 3a added" (the evidence table);
  `formal/lean/ZanzibarProofs/GraphIndex/Cascade.lean::GraphState.bridgePreLogged`,
  `::GraphState.releasePostLogged`, `::ensureInBridges_evalEq`, `::bridgePreLogged_evalEq`,
  `::writeBridgedOne_logged_evalEq` (the theorem 3b re-points `writeLoggedOne_evalEq` onto)
  and `::BridgedLegWitness`.
- **The `2026-09-13c` Log entry is what step 3a started from** — where the four new definitions live and why there, the two audited names re-proved (statements unchanged), the 14-mutation sweep and its two honest INERT rows, and the ONE NEW BOUND on step 3 (the stratum-2 `checkFn` gap). The code to read before composing anything: `formal/lean/ZanzibarProofs/GraphIndex/Cascade.lean` §"The in-bridge, LOGGED" (the four defs + their projections/`EvalEq`), its §"CONTROLLED — MUTATION SWEEP over everything `P6` step 2 added" (the evidence table), `formal/lean/ZanzibarProofs/GraphIndex/CascadeInv.lean::structInv_ensureInBridgesLogged` and its two siblings, and `formal/lean/ZanzibarProofs/GraphIndex/UsStarWrite.lean::ensureInBridges_count_le_one` + `::InBridgeIdemWitness` (the multiset invariant and its red-to-green arm).
- `formal/probes/p6_step1_logged_bridge_2026-09-13.lean` — **step 1's verdict and every number behind it**, literal transcript in the header (rc=0, 244 lines). The GO: bridged leg `14 → 2` of 546, ceiling `0`. Everything it listed as owed to step 2 is DONE as of 2026-09-13c (presence guard; `ensureInBridgesLogged`, TGT chosen and SAID to be unpinned; `releaseInBridges`; both `formal/CORRESPONDENCE.md` §7 entries) — read it now for the NUMBERS step 3 relies on, not for a to-do list. Companion: `formal/probes/p6_phantom_subject_2026-09-13.py` (the residual 2 is a Lean-model gap — the shipped backends are unanimous), whose property is now the pin `tests/test_p6_phantom_subject.py`.
- `formal/lean/ZanzibarProofs/GraphIndex/TtuStarWide.lean` — what step 0 put there: `::ttuStarFreeW_through_untainted` (the consumer-side Wall-1 lemma), `::Zanzibar.RoutingArmWitness` (which stores are OUT of scope, and why — `no_rewrite_arms` is the load-bearing pin), `::Zanzibar.TermNonvacuityWitness` (that `term` excludes anything at all), and the mutation-sweep table. ⚠ **Every arm must assert per-arm non-vacuity**: an arm measured where `schemaRewrites = []` is measuring nothing, which is exactly how the 2026-09-12 ROUTING arm produced a number that meant nothing. Step 1 honoured this (its `Vac` carries `rewrites`, `bridges`, `narrowRej && wideAdm`, `unmapped`); step 2 and after must keep doing so.
- Python's side of the bridge, read before modelling it: `index_v4/wildcard.py::WildcardIndex._ensure_own_bridges` (write), `::_maybe_remove_bridges` (retract), `index_v4/core.py::ReachabilityIndex.add_edge_by_id` (why the bridge is logged), `index_v4/processor.py::DeltaProcessor._write_derived` (the out-of-fragment derived case).
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

### 2026-09-12b

PLAN SESSION (no Lean edited; both walls DECIDED, plan recorded). User delegated the two
technical calls with one goal stated: prove the graph index algorithm correct and leave no
edge-case bugs. Both calls below follow from that goal by one rule -- the Lean claim must
describe what the SHIPPED code does, so mirror Python. Everything cited was re-read
first-hand this session against the live tree.

**THE FRAMING CHANGES: Wall 1 is NOT a scope defect inside the fragment.**
`W4Fragment.term` (`formal/lean/ZanzibarProofs/FullScope.lean:299`) is
`∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R`, and
`NoTtuTarget S R` (`GraphIndex/ReconcileCorrect.lean:616-617`) is
`∀ r ∈ schemaRewrites S, ∀ tr, r.kind = RuleKind.ttu tr → tr ≠ R`. So inside `W4Fragment` --
the ONLY place `TtuStarFreeW` will ever be consumed, as the replacement for the
`ttuStarFree` field at `:298` -- no TTU arm has a derived through-relation, and the
through-shape `(t.subject.type, tr)` that `TtuStarFreeW` bridges is never derived. The
2026-09-12 ROUTING arm measured store `Sd`
(`formal/probes/p6_inbridge_stability_2026-09-12.lean:902-906`: `doc#control := approver
from parent` with `folder#approver` derived), and `Sd` VIOLATES `term` -- the probe's own
line `:502` invokes `term` for the stability store but never applied it to `Sd`. The
"14 -> 9 of 546 mismatches" payoff failure was measured on the same out-of-fragment store.
CONSEQUENCE: (ii) does not have to inhabit the derived through-shape, the (a)/(b)/(c)
trilemma is retired, and the payoff criterion is UNMEASURED in scope, not failed.

What Python does at the out-of-fragment shape, for the boundary record: the processor's
`_write_derived` (`index_v4/processor.py:657-681`) writes the derived public node through
`WildcardIndex.add_tuple`, which calls `_ensure_bridges` on BOTH endpoints
(`index_v4/wildcard.py:521-522`) -- so Python bridges the PUBLIC derived node from the
CASCADE, never from the raw write leg. Retraction is `_gc_public_node` (`processor.py:1262`)
-> `_maybe_remove_bridges`. That is a fragment boundary of the same class as the
entity-middle half (`formal/CORRESPONDENCE.md:964-973`), not something increment B owes.

**Two more first-hand facts that dissolve the "logged/unlogged vise" and reshape Wall 2.**
1. Python's bridges are LOGGED. `_ensure_own_bridges` (`wildcard.py:267-279`) adds via
   `idx.add_edge_by_id`, whose contract (`index_v4/core.py:1101-1107`) records reachability
   flips in the delta outbox. So the LOGGED horn is the faithful one. And
   `writeLeg_reach_stable` (`CascadeStable.lean:362-370`) states `hunmapped` over
   `cascadeKeys S (σ.writeLoggedRules S t)` -- the POST-write state -- with a proof shaped
   "a new backward path factors through a routed edge whose frontier row puts the key in
   `cascadeKeys`, contradicting unmappedness". A logged bridge extends that argument by one
   case (the new edge is a bridge, its delta is a frontier row); it does NOT make the theorem
   vacuous, it makes the theorem apply as designed: bridged key => dirty => cascade
   reconciles it. Arm B-SUB's tier-1 FALSE (`hazardUnmapped := true`) was the UNLOGGED
   variant, which is not what Python does. Arm B-SUB-L's domain shrink is the theorem's
   premise doing its job, not an instrument defect -- but the instrument still needs a
   per-domain verdict (see step 1) so nobody has to argue this again.
2. Python's retract dual is `_maybe_remove_bridges` (`wildcard.py:363-386`): strip the bridges
   when the node is `implicit` and `reference_count == bridge degree`, deferring to
   `_sync_entity_middles` only for crossing middles. That is a refcount-guarded GC that is
   ALREADY the shipped design. (The prior comment's "its retract dual is entity GC" describes
   the middle half, not the own-bridge half.)

**DECISION, Wall 1 (taken this session): resolve by LEMMA, not by narrowing.** No edit to
`TtuStarFreeW` or `ttuStarFreeWB`; the four audited names at `formal/audited_theorems.txt:537-540`
stay untouched; `[4b]`/`[4c]` stay green. Instead:
  (1) `TtuStarWide.lean` (import cone 1): `theorem ttuStarFreeW_through_untainted` -- under
      `hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R`, every `t ∈ T` with a star
      subject and every matching TTU arm `tr` has `isDerived S (t.subject.type, tr) = false`.
      Proof is by contradiction from `NoTtuTarget` applied to the arm; expect ~3 lines.
  (2) A fourth witness pin, `WideWitness`-style: the probe's `Sd` FAILS `term` by `decide`
      (`NoTtuTarget Sd "approver"` is false because `("doc","control")` is `.ttu "approver"`).
      That is the K1 kill condition made mechanically un-forgettable at ZERO audited-name
      cost. New `theorem` rows DO add pin lines (`statement_pin.py::lean_files` walks
      `rglob("*.lean")`, no import check), so regenerate `FINAL_REVIEW.md` counts
      (`python -m formal.conformance.doc_counts --generate`) or `[4e]` reds.
  (3) `formal/CORRESPONDENCE.md` sec 7 entry: derived TTU through-shape is a fragment
      boundary; Python covers it via the processor path cited above.
  Rejected: narrowing the predicate (re-opens four audited names for a conjunct `term`
  already implies); modelling the derived half (a larger project -- file it as a follow-on
  row, see below); teaching `isSubjectWildcardUserset` about minted leaves (breaks
  `bridgedInConcrete_elim`, `UsStarWrite.lean:106-109`).

**DECISION, Wall 2 (taken this session): bridge-GC in the Lean model, LOGGED, mirroring
`_maybe_remove_bridges`.** A NEW definition `GraphState.releaseInBridges c` on the remove
leg: if `c` is `bridgedInConcrete` and its only remaining incident edges are its bridges,
drop the bridge edge (and the node, as implicit GC would). Composed into `removeLoggedOne`
(`Cascade.lean:319-323`) after `removeEdgeOne`, on both endpoints, with a `pushDelta` on
the `wAnyNode` as Python's `remove_edge_by_id` logs. `count_removeLoggedRules`
(`CascadeStrata.lean:738`) is then RESTATED -- closure-list count plus released bridges --
which is a change to the model, not the `RemoveOccCount.lean:178-194` shape (no guard is
added to any existing theorem to exclude a counterexample). Rejected: ref-counting Python's
presence guard (changes shipped code to fit a proof -- the wrong direction for the stated
goal); deferring GC to an "increment C" (re-pays the remove-side cone and leaves a
write-then-remove residue the row-multiset hypothesis tests would flag on the Python side
if Python did it).

**THE PLAN, in landing order. Each numbered step ends on a green, committable tree.**
Step 0 -- Wall-1 lemma + `Sd` pin + CORRESPONDENCE entry (cone 1, one session, additive).
Step 1 -- Re-aim the probe at the IN-FRAGMENT store with a LOGGED leaf-routed bridge (zero
  cone; the go/no-go). New dated probe or new arms in the existing one:
  * REPAIR arm on the `viewer from parent` store (`ThroughShapeWitness.Sthru`,
    `UsStarWrite.lean:163-166`, or the probe's stability store): does a logged bridge on
    the leaf-routed list bring graph-vs-`sem` mismatches to ZERO after drain? If not zero,
    STOP and re-plan before any cone is paid -- something other than the bridge is missing.
  * Stability arms with the LOGGED bridge and a verdict function that reports PER DOMAIN
    (unmapped keys: reach/graphRec/checkFn stable? bridged-now-mapped keys: drained cascade
    agrees?) instead of `reachStableAll`. Retires the "GREEN by collapse" ambiguity.
  * Tier-2 replacement instrument: `guardPre`/`guardPost` were false in all eight arms, so
    the tier-2 premises were never satisfied; find what state they need and build it.
  * A write-then-remove arm counting the bridge-only residue WITHOUT `releaseInBridges`
    (quantifies Wall 2) and confirming zero residue WITH a prototype of it.
Step 2 -- Additive definitions (cone 0): `ensureInBridgesLogged` (= `ensureInBridges` +
  `pushDelta (wAnyNode (c.type, c.pred)) c.pred true`) and `releaseInBridges`, each with
  `StructInv` preservation and `EvalEq` lemmas in the style of `structInv_ensureInBridges`
  (`UsStarWrite.lean:274`). NAMING TRAP: `statement_pin.py::_refs` resolves receiver
  dot-calls by SUFFIX -- do not give either a tail colliding with `.writeLoggedRules`,
  `.addEdge`, `.reach`.
Step 3 -- THE CONE PAYMENT, both legs at once (cone `42` modules, unit = reverse import
  cone of the six targets excl. root aggregator; see the 2026-09-12 CORRECTIONS 1).
  Compose into `writeLoggedOne` (`Cascade.lean:174-177`) AND the unlogged `writeRules` twin
  (`RulesWrite.lean`) so `EvalEq` survives, bridge-before-grant on both endpoints in the
  order `wildcard.py:521-522` uses; `releaseInBridges` into `removeLoggedOne`/`removeRules`.
  Then restate, in the honest direction, the theorems step 1 proved false:
  `writeLoggedRules_edge_delta` (`CascadeStable.lean:118-121`, audited `Audit.lean:761`:
  delta = routed edges + bridge edges), tier-0 `reachedByW3d_edges_target_plain`
  (`CascadeStable.lean:292`) / `reachedByW3d2_edges_target_plain`
  (`CascadeStrataSettle.lean:193`) (target `plain` OR `wAny`), `count_removeLoggedRules`;
  `writeLeg_reach_stable` keeps its statement and gains a bridge case IF step 1 confirms.
  Inherited chores: def-pin diff adjudicated in `formal/history/` (trap (ff)); `FoldAdmits`
  `21` move / `3` stay (`RulesComplete.lean:115`, `RestrictBase.lean:470`, `:531`);
  `two_stratum_cascade` multiplicity re-measure before any golden; `extractor.py::
  _edge_projection`'s P2 projection docstring flips (Lean now creates `w_any` rows).
Step 4 -- The flip: `W4Fragment.ttuStarFree := TtuStarFreeW` (`FullScope.lean:298`) and
  `Exec.lean::removeGateB -> removeGateBW`; the headline pin at
  `formal/headline_statements.txt:44` reds and is adjudicated; `W4Fragment.ttuStarFree`
  is finally inhabited by a bridged store, pinned by `decide` on `Sthru`.

**SIZING, honestly.** Steps 0-1 fit one session. Step 3 is the same class as `P3` (sized
`3` sessions, took `24`), and every estimate on this row has moved UP; so "several
sessions, checkpointed" with no number. Re-size `M` -> `L` at step 2.

**FOLLOW-ON TO FILE (not this row's scope): the derived TTU through-shape is covered by
Python and NOT by any proof.** For the user's stated goal that is exactly where an edge-case
bug can hide unproved. The differential matrix + hypothesis campaign are the net there
today; a row should either extend the fragment (model the processor's public-node bridge)
or add a targeted conformance corpus with a star tupleset over a derived relation. Candidate
id to be assigned at filing.

Not re-ranked; stays `NOW`; now STARTABLE at step 0.

### 2026-09-13

STEP 0 LANDED (Lean additive, gate `lean` green). The Wall-1 lemma, the witness pin, the
`CORRESPONDENCE.md` §7.3 entry. **Step 0's middle deliverable landed saying the OPPOSITE of
what the 2026-09-12b plan specified, and the plan's conclusion survives it — stronger.**

**CORRECTION to the 2026-09-12b entry, measured first-hand before anything was written.**
That entry recorded the kill condition as "the probe's `Sd` VIOLATES `W4Fragment.term`,
because `("doc","control")` is a `.ttu "approver"` arm and `approver` is derived", and made
it the basis of "the payoff is UNMEASURED, not failed". **It is false.** Measured by
`lake env lean` on the actual store, verbatim:

```text
("taintedKeys Sd", [("folder", "approver"), ("doc", "control")])
("isDerived (folder,approver) / (doc,control) / (doc,parent) / (folder,blocked)", true, true, false, false)
("schemaRewrites Sd", [])
("noTtuTargetB Sd approver / control", true, true)
("htermB Sd Td / Sd TdStar / Sd []", true, true, true)
("isStarTuplesetThrough (folder,approver)", true)
("isSubjectWildcardUserset (folder,approver)", true)
("ttuStarFreeB / ttuStarFreeWB on TdStar", true, true)
("lookup (doc,control)", some (Zanzibar.Expr.ttu "approver" "parent"))
```

`NoTtuTarget` quantifies over `schemaRewrites`, and `schemaRewrites` DROPS DERIVED DEFS
(`GraphIndex/RulesWrite.lean::schemaRewrites`, the mirror of
`zanzibar_utils_v1.py::compile_ruleset`'s `if key not in tainted` loop). The arm's own owner
key `("doc","control")` is tainted too, because `Spec/Stratify.lean::exprRefs`'s `.ttu` case
adds the derived target ref `("folder","approver")` via the tupleset's parent types. So the
arm never reaches `schemaRewrites` and `term` never sees it. Written as specified, the pin
would have reddened on first build.

**The conclusion is right by a stronger route — carry THIS forward, not the `term` reason.**
`schemaRewrites Sd = []`, so at that store BOTH `ttuStarFreeB` and `ttuStarFreeWB` are
**vacuously true**: the widened predicate is not merely satisfiable there, it is **not
ENGAGED** there. The 2026-09-12 ROUTING arm was never a widening case at all, so the
"14 -> 9 of 546 mismatches" payoff failure was measured on a store increment B owes nothing
to. And the exclusion is store-INDEPENDENT where the `term` reason would have been
store-dependent: `Sd` leaves `W4Fragment` at `computedOrDirect` (a derived key whose
definition is a `.ttu`; `ReconcileCorrect.lean::ComputedOrDirect` is `False` there), for
EVERY store.

**In the tree now** — all additive; `TtuStarFreeW` / `ttuStarFreeWB` untouched, zero audited
names re-opened, `W4Fragment.ttuStarFree` NOT flipped (that is step 4):
* `GraphIndex/TtuStarWide.lean::ttuStarFreeW_through_untainted` — the Wall-1 lemma, 3 lines.
  Under `term`'s `NoTtuTarget` half, a TTU arm's through-shape `(dt, tr)` is untainted at
  every object type, so `Schema.isSubjectWildcardUserset` is only ever asked about a PUBLIC
  (never leaf-minted) relation name. `t ∈ T`, `subject.name = STAR` and the match are
  deliberately NOT binders — the fact is about the schema alone, and the docstring says so.
* `::Zanzibar.RoutingArmWitness` — 10 pins: the corrected boundary, including
  `no_rewrite_arms`, `narrow_admits`, `wide_admits_vacuously`, `term_holds` (the pin that
  refutes 2026-09-12b) and `outside_fragment` (the store-independent kill).
* `::Zanzibar.TermNonvacuityWitness` — 4 pins, see below.
* The mutation-sweep table, in the module docstring.
* `CORRESPONDENCE.md` §7.3: the derived TTU through-shape as a declared fragment boundary,
  with Python's cascade-side coverage anchored. 20 new anchors, all resolving (612/612).

**`hterm` is NON-VACUOUS, and that needed its own measurement.** The sweep's M1 shows the
hypothesis is *referenced*; it does not show it *excludes* anything, and since `NoTtuTarget`
very nearly follows from the taint fixpoint alone, "a tautology dressed as a scope result"
was the live risk. The one route by which an arm survives the filter with a derived target is
an **UNDECLARED tupleset relation** — `exprRefs` adds no target ref when the lookup misses,
so the owner stays untainted. Measured 2026-09-13:

```text
("taintedKeys Sund", [("folder", "approver")])
("isDerived (folder,approver) / (doc,control)", true, false)
("schemaRewrites Sund",
 [{ objectType := "doc", matchRel := "parent", outRel := "control", kind := Zanzibar.RuleKind.ttu "approver" }])
("noTtuTargetB Sund approver  -- FALSE here means term is NOT vacuous", false)
("htermB Sund []", false)
("rewriteMatchDeclaredB? see below", none)
```

**MUTATION SWEEP (`docs/sabotage-procedure.md` "Sweep the TEST MODULE with mutations").** A
`decide` pin cannot fail by passing; its failure mode is asserting something true regardless
of the witness. So the sweep mutates the WITNESS one plausible edit at a time and requires a
NAMED red per pin. 10 mutations, all 14 pins reddened by at least one, restore green; the
table is in the module docstring.
* ⚠ **The instrument failed first, in the direction that looks like a finding.** Run 1
  reported `RED: <unattributed>` for all six mutations, because the error-location regex
  expected `...lean:N:C: error` while lake prints `error: ...lean:N:C:`. The "candidate inert
  pins" list was then the whole module — which reads exactly like a discovery. `M0` is now a
  permanent instrument control: it flips one pin's own claim and the sweep must attribute the
  red to that pin by name.
* `M5` (star subject -> concrete) is **INERT**, and that is honest rather than a hole: the
  vacuity `narrow_admits` / `wide_admits_vacuously` assert holds for ANY store, because
  `no_rewrite_arms` is what carries it. Said out loud in the docstring so the next reader
  does not take the star subject for load-bearing.
* `M7` needed a TWO-part mutation (surviving arm + undeclared through-shape) to redden
  `wide_admits_vacuously` — the honest sign that that pin's content is a conjunction.

**NEW OPEN QUESTION, unmeasured, recorded rather than answered.** `Sund` also fails
`RewriteMatchDeclared`, which `FullScope.lean:1350` carries SEPARATELY from `W4Fragment`. So
`term`'s `NoTtuTarget` half is non-vacuous as a predicate but may be *implied* by the other
admission carries inside the full theorem chain. If it is, step 4's flip has one fewer
premise to justify and the Wall-1 lemma becomes hypothesis-free. Cheap to settle (does any
chain-level theorem assume declared tuplesets?); nobody has. The `TermNonvacuityWitness`
docstring states this limit explicitly so the pin is not over-read.

**NEXT: step 1**, unchanged from the 2026-09-12b plan and now unblocked — the zero-cone
go/no-go probe, re-aimed at the IN-FRAGMENT store (`WideWitness.SwT` is exactly that shape:
untainted `folder#viewer`, arm present, narrow rejects / wide admits). Its verdict function
must report PER DOMAIN. Note for that probe: `RoutingArmWitness` is now the machine-checked
statement of which stores are OUT of scope, so an arm measured on a store where
`schemaRewrites = []` is measuring nothing — check `no_rewrite_arms`-style non-vacuity per
arm before reading any mismatch count.

### 2026-09-13b

STEP 1 RAN, AND THE ANSWER IS **GO** (zero cone; no Lean model, no gated file touched).
New tracked probe `formal/probes/p6_step1_logged_bridge_2026-09-13.lean` (rc=0, 244 lines,
literal transcript in its header, re-run byte-identical after the transcript was pasted in)
plus `formal/probes/p6_phantom_subject_2026-09-13.py`.

**FIRST, A CORRECTION THAT THIS ROW HAS NOW CARRIED TWICE — and it is the reverse of the
2026-09-12b one.** That entry recorded, and the 2026-09-13 step-0 entry carried forward,
that the '14 -> 9 of 546 mismatches' payoff failure "was measured on the out-of-fragment
store `Sd`" / "on a store increment B owes nothing to". **False.**
`p6_inbridge_stability_2026-09-12.lean:872-887 P6BridgeProbe.repair` is written entirely
against `Sp` — `cascadeLeg Sp`, `legB Sp`, `sem Sp` — and `Sp` IS the in-fragment
`WideWitness.SwT`-shaped store (`:488-503`), pinned by that file's own
`NARROW rejects / WIDE admits the prefix store == some (false, true)`. `Sd` appears only in
`§7 routing` (`:902-941`), a different measurement with different numbers. Two sections
were conflated into one sentence. Re-ran the 2026-09-12 probe first-hand before writing
anything: rc=0, 335 lines, byte-identical, `baseMismatch := 14 / bridgedMismatch := 9`.
So the payoff criterion was NOT "unmeasured in scope" — it was measured IN scope and it
FAILED. Step 1's stop condition was live, not hypothetical.

**WHY IT FAILED: an instrument defect, now fixed and confirmed.** `repair` builds its
pre-state with `graphRunOps Sp prefixOps` — the PLAIN driver — and only then bridges the
single write `tObj`. So `tView`'s object endpoint `folder:f1#viewer`, the concrete node the
whole through-shape hangs off, was written by a bridge-free leg and no arm ever went back
for it. Increment B composes the bridge INTO the write leg, so every write bridges, prefix
included. The new probe measures that design (`bridgedRunOps`, the bridged twin of
`Exec.lean:449 graphRunOpsAux`).

**THE GO/NO-GO NUMBERS** (546-query routing-independent grid, all arms carrying per-arm
non-vacuity per step 0's lesson: `rewrites := 1` so the widening predicates are ENGAGED,
`narrowRej && wideAdm` true, `bridges > 0`):
* `R-OLD-BASE` / `R-OLD-BR` reproduce **14** and **9** exactly — same instrument, so the
  delta below is attributable to the prefix and to nothing else;
* `R-BASE` (whole op stream, plain leg) **14**;
* `R-BR-OFF` / `R-BR-SRC` / `R-BR-TGT` / `R-BR-OBJ` (bridged leg) **2** — all four
  identical;
* `R-CEIL` (maximal schema-declared bridging) **0**.
The ceiling is ZERO, so the bridge is the COMPLETE mechanism for every node a write leg
touches. Step 1's criterion is met.

**PER-DOMAIN VERDICT — the 2026-09-12b prediction is CONFIRMED, and this is the Wall-2
repair.** On the subject-endpoint write the old probe called FALSE:
* `D-SUB` (bridge UNLOGGED): `uReachStable` / `uGraphRecStable` / `uCheckFnStable` all
  **false** at 3 UNMAPPED keys — the tier-1 statements are FALSE, not premise-repairable;
* `D-SUB-S` / `D-SUB-T` (bridge LOGGED): all three **true**, because the delta moves those
  keys from unmapped (3 -> 1) into `cascadeKeys`.
So `hunmapped` excludes exactly the perturbed keys and **all 23 at-risk stability theorems
keep their statements**; only the proofs need a "new edges are routed-or-bridged" case.
(!) SRC and TGT logging are INDISTINGUISHABLE on every number measured — step 2's choice of
TGT is free, not pinned, and this probe must not be cited as evidence for it.

**★ NEW FINDING, a MODEL-FIDELITY BUG, and Wall 2 is TWO mechanisms not one.**
(a) The dead-node GC the 2026-09-12b Wall-2 decision specified is CORRECT: `W2-DOM-TGT`
    leaves `residue := 1` and the `_maybe_remove_bridges`-mirroring prototype collects it
    exactly (`releaseFixes := true`), declining correctly on a still-live node.
(b) **`ensureInBridges` is NOT idempotent on the EDGE MULTISET** — measured
    `(0 calls, 1, 2, 3) = (0, 1, 2, 3)`. `legB` calls it once per member of the leaf-routed
    list, so `tSub`'s 2-member list (both members subject `folder:f1`) leaves `residue := 2`
    that `RESIDUE DETAIL` shows is **EMPTY of new edges** — two extra COPIES of a bridge
    already present. The GC correctly declines (node still live), so copies accumulate per
    write: the `_leak_accumulates` shape. **Python does NOT do this** —
    `index_v4/wildcard.py::WildcardIndex._ensure_own_bridges` guards with
    `if not self.idx.direct_edge_exists_by_id(node.id, w_any.id)` before `add_edge_by_id`.
    The Lean def (`UsStarWrite.lean:213-218`) has no guard; its docstring claims only
    reachability-level idempotence, which is true and is not enough once a live chain calls
    it once per routed member. Inert today (`UsStarWrite.lean:112`: no live chain calls it);
    increment B is exactly what makes it live.
    **DECISION taken here (CLAUDE.md "Who decides"): step 2 adds the presence guard,
    mirroring Python.** Forced direction — the proof must describe the shipped code, and the
    shipped code guards. Cost: re-opens `structInv_ensureInBridges` (audited
    `Audit.lean:159`) and `ensureInBridges_edges_mem` (audited `Audit.lean:166`). This is
    ADDITIONAL to the 2026-09-12b step-2 list.

**THE RESIDUAL 2 IS A PHANTOM SUBJECT — a Lean-model gap, NOT a shipped bug.** Both are
`folder:f9#viewer` on `doc:d1` at the DERIVED relations `admin`/`gate`; `folder:f9` is
mentioned by no written tuple, so no write leg creates the node (`PHANTOM NODE PRESENT?`
false on plain and bridged legs, true only at the ceiling). The asymmetry is the content:
at the SAME subject the PLAIN relation `access` answers **correctly** in the bridged graph
model — only the derived relations are wrong. Checked against the shipped Python the same
hour via `tests/parity.py::ParityEngine` (graph + both SetOps + oracle, unanimity
asserted): **all seven queries UNANIMOUS True, no divergence.** Python gets it right
because its derived read path is edge probe PLUS residue, i.e. symbolic, where the Lean
model's is edges alone. That is a `CORRESPONDENCE.md` sec 7 boundary of the same class as
the entity-middle half — not something increment B owes, and not a reason to stop.

**TIER 2 NEEDED DIAGNOSIS, NOT A REPLACEMENT INSTRUMENT.** `guardPre`/`guardPost` were
false in all eight 2026-09-12 arms, BASE included, so tier 2 measured nothing. Reason now
named: **8** failures at `G-PLAIN`, halved to **4** under bridging (`G-BR-TGT` and `G-CEIL`
alike) — they were false at BASE because this is exactly the store the unbridged graph gets
WRONG (`TtuStarWide.lean:32-39`), which is the point of the widening. The residual 4 are
printed as rows and are NOT a bridge question: all four are `gate` — **stratum 2 only,
never `admin`** — at userset subjects `folder:f1#viewer` / `f2` / `f9`, with
`checkFn = false`, `GraphModel.check = true`, `sem = true`. At the ceiling the two READERS
disagree: the model's `check` is right, the proof-side `checkFn` under-reads the stratum-2
derived relation at a userset subject. Bounded, named step-2 item
(`writeLeg_sem_stable2`'s tier); the instrument itself is fine.

**STILL OWED, stated rather than left implicit.** The phantom-subject parity result is a
tracked, re-runnable PROBE, not a pin — nothing in the ten-phase gate reddens if that
property regresses. `docs/sabotage-procedure.md`'s durability ranking puts a tracked probe
two rungs below a permanent test. Promoting it is a step-2 item, deliberately not done here
to keep step 1 zero-cone.

**NEXT: step 2**, unchanged from the 2026-09-12b plan except that it now inherits four
things from this run: the `ensureInBridges` presence guard (new, re-opens two audited
names); `ensureInBridgesLogged` with TGT chosen for `writeLoggedOne` symmetry and SAID to
be unpinned; `releaseInBridges` confirmed as specified; and two `CORRESPONDENCE.md` sec 7
boundary entries (phantom-subject derived read path, stratum-2 `checkFn`-vs-`check` gap).
Re-size M -> L at step 2 as the plan says.

### 2026-09-13c

STEP 2 LANDED. All four additive definitions are in, in their FINAL home, with StructInv +
EvalEq lemmas, a 14-mutation sweep, and the two owed `CORRESPONDENCE.md` sec 7 entries. The
still-owed phantom-subject property is now a gated PIN. Whole-tree Lean build green
(1087 jobs, 0 errors); gate run at the end of the session.

**THE FIDELITY BUG IS FIXED, and the fix is pinned at the level it was wrong on.**
`GraphState.ensureInBridges` (`UsStarWrite.lean`) now guards with
`if (c, wAnyNode (c.type, c.pred)) in sigma.edges`, mirroring
`index_v4/wildcard.py::WildcardIndex._ensure_own_bridges`'s
`if not self.idx.direct_edge_exists_by_id(...)` -- including Python's ORDER, intern the
`w_any` node first (it is added on every bridged branch, present-edge included), test the
edge second. The probe's measured `(0 calls, 1, 2, 3) = (0, 1, 2, 3)` now reads
`(0, 1, 1, 1)`.
* Positive pin, not an xfail: `UsStarWrite.lean::ensureInBridges_count_le_one` -- an
  INVARIANT (`count <= 1` in implies `count <= 1` out), not a two-call idempotence claim,
  because that is the form the step-3 fold needs, where the bridge is called once per
  leaf-routed member and the interesting state is after `k` calls.
* Executable half: `UsStarWrite.lean::InBridgeIdemWitness` -- `copies_0/1/2/3`,
  `edges_are_the_bridge_alone`, plus `bridged_control` / `unbridged_control` for per-arm
  non-vacuity.
* COST PAID, as forecast: `structInv_ensureInBridges` (audited `Audit.lean:159`) and
  `ensureInBridges_edges_mem` (audited `Audit.lean:166`) were re-proved. **Both keep their
  STATEMENTS** -- the new branch leaves `edges` alone, so it lands in the existing left
  disjunct. Three more proofs in `UsStarClosure.lean` needed the extra branch
  (`ensureInBridges_edges_mono`, `ensureInBridges_nodes_mem`,
  `ensureInBridges_creates_bridge`); `ensureInBridges_creates_bridge` also keeps its
  statement, because on the presence branch the edge is there already, which is its
  conclusion.

**THE DEFINITIONS LANDED IN `Cascade.lean`, NOT IN A TEMPORARY HOME -- a step-3 decision
taken here.** `ensureInBridgesLogged`, `inBridgeOnly`, `releaseInBridges`,
`releaseInBridgesLogged`, next to `pushDelta` and `removeLoggedOne`, which is where step 3
composes them. That needed a new `Cascade -> UsStarWrite` import edge, so I measured it
before writing anything: `UsStarWrite`'s 18-module cone contains no `Cascade*` and no
`Reconcile*` module, so the edge is acyclic, and the whole-tree build after adding it was
green with the job count UNCHANGED at 1087 -- zero proof cone, zero new modules.
* (!) The alternative was a temporary home in `TtuStarWide.lean` (the only P6 module that
  already sees both sides). REJECTED: the final home must be upstream of `writeLoggedOne`,
  `TtuStarWide` is downstream of it, so those defs would have had to MOVE at step 3 --
  and moving them would have broken every `file::symbol` anchor written for them. The
  import direction matters and is easy to get backwards: `UsStarWrite` importing `Cascade`
  would have made step 3's needed direction a CYCLE.
* `ensureInBridgesLogged` emits **iff the direct-edge multiset actually grew**
  (`if (sigma.ensureInBridges c).edges = sigma.edges then ... else ... pushDelta`), stated
  on the edges rather than on the guard, so the "emit on an actual flip" rule stays correct
  under the presence guard and under whatever step 3 does to it. Delta at the TARGET
  (`wAnyNode`), and the docstring SAYS the SRC/TGT choice is free -- step 1 found the two
  indistinguishable, so nothing measured forbids SRC later.
* `releaseInBridges` fires on `inBridgeOnly` (Python's "implicit and
  `reference_count == bridge degree`", as a predicate on the edge list) and erases ONE copy.
  (!) It deliberately does NOT delete the node: this model has no node GC on any leg
  (`removeEdgeOne_nodes = sigma.nodes` everywhere), so inventing one here would break
  `StructInv.edgesClosed` rather than mirror Python. Recorded in the def's docstring; the
  only consequence is that `reach`'s `nodes.length + 1` fuel stays larger than Python's,
  which can only over-approximate.
* Lemmas: `structInv_ensureInBridgesLogged` / `structInv_releaseInBridges` /
  `structInv_releaseInBridgesLogged` in `CascadeInv.lean` (with the other logged-leg
  StructInv lemmas); `ensureInBridgesLogged_evalEq` / `releaseInBridgesLogged_evalEq` plus
  the edges/nodes/schema/residue projections in `Cascade.lean`. `EvalEq` is what lets step 3
  bridge the logged leg AND its unlogged `writeRules` twin and still carry
  `writeLoggedRules_evalEq`. NAMING TRAP honoured: no tail collides with `.writeLoggedRules`
  / `.addEdge` / `.reach`, and `GraphState.ensureInBridgesLogged` does not end in
  `.ensureInBridges`, so `statement_pin.py::_refs`'s suffix resolution is unambiguous.
* New `UsStarWrite.lean::ensureInBridges_residue` (`@[simp]`), needed by the logged leg's
  residue projection; the `schema` twin had been enough while nothing consumed `residue`.

**THE SWEEP: 14 mutations, table in `Cascade.lean` sec "CONTROLLED -- MUTATION SWEEP over
everything P6 step 2 added".** Covers BOTH halves in one run, because
`logged_second_call_silent` is the pin that couples them: without the presence guard the
second call grows the multiset, so the logged leg emits a SECOND delta row -- a delta per
redundant routed member, which is worse than the duplicate edge. Every pin is reddened by
at least one mutation except two, and both say so out loud:
* M6 INERT -- dropping `bridgedInConcrete` from `inBridgeOnly` changes no observation,
  because the release then fires at nodes with no bridge edge to erase and `removeEdgeOne`
  on an absent edge is the identity. The conjunct is defensive. Do not delete it on the
  strength of that row; do not cite it as load-bearing either.
* `copies_0` cannot be reddened -- it reads the state BEFORE any call, so it is the
  baseline of the `(0,1,1,1)` sequence, not a pin on the guard.
* (!) THREE instrument failures in one sweep, which is the point of having controls.
  (1) M0 (flip `copies_1`'s own claim) attributed correctly, so the step-0 regex bug has
  not returned. (2) But M0 did NOT catch the new one: ten of fourteen mutations came back
  `ANCHOR MISS` because the sources are CRLF and the anchors were LF -- at least that
  failed loudly. (3) M12's first form (`doc#parent -> doc#viewer`) read INERT because it
  does not change the property under test: `("doc","viewer")` is no more a bridged-in
  shape of `Sthru` than `("doc","parent")` is, the star restriction being `[folder:*]`.
  An edit that does not move the property measures nothing and looks exactly like a clean
  pin. Re-aimed at `cUn := c0` and it reddened `unbridged_control`.

**STILL-OWED FROM STEP 1 IS DISCHARGED: the phantom-subject parity result is now a PIN.**
`tests/test_p6_phantom_subject.py` (9 tests, inside the gate): same schema, store and seven
queries as `formal/probes/p6_phantom_subject_2026-09-13.py`, through
`tests/parity.py::ParityEngine`, with expectations asserted (unanimously WRONG must not pass
as parity), a `test_graph_backend_joined` arm refusing the 3-way degrade, and a
`test_phantom_object_has_no_graph_node` arm asserting the phantom is really absent while the
control resolves. Sabotage table in the module docstring: S0 instrument control attributes;
S1 (make Python's userset arm require a materialised node, i.e. adopt the Lean model's
edges-alone reading) reds ALL NINE at fixture setup, because `ParityEngine._apply` runs a
full-grid parity assertion after every write and its grid already carries ghost subjects --
it dies of the property, not of a `TypeError`. S2/S3 are INERT and the docstring says which
lines they leave unexercised and why widening the schema to chase them would decouple the
pin from its evidence. The probe's "STILL OWED" paragraph is replaced by a pointer at the
test.

**The two `CORRESPONDENCE.md` sec 7.3 entries are written** (anchors resolve: 619 parsed,
619 resolved): the phantom-subject derived read path (`GraphModel.check` reads edges,
`WildcardIndex._check_derived` reads edges plus residue), and the stratum-2 reader gap
(`checkFn` false where `GraphModel.check` and `sem` are true, at userset subjects, stratum 2
only). The second one BOUNDS step 3: `CascadeStrataSettle.lean::writeLeg_sem_stable2`'s tier
is the one that consumes `checkFn` at exactly those keys, so a step-3 proof must not route a
stratum-2 userset-subject obligation through `checkFn` and call it settled.

**Re-sized M -> L**, as the 2026-09-12b plan said to at step 2.

**NEXT: step 3, the cone payment.** Unchanged from the plan, with these step-2 facts to
carry: the import edge is already in place, so step 3 is a pure composition edit
(`writeLoggedOne` + the unlogged `writeRules` twin; `removeLoggedOne`); all 23 at-risk
stability theorems keep their statements and need a "routed-or-bridged" case (step 1);
`writeLoggedRules_edge_delta`, tier-0 `reachedByW3d_edges_target_plain` /
`reachedByW3d2_edges_target_plain` and `count_removeLoggedRules` get restated in the honest
direction; and the stratum-2 `checkFn` bound above is new. `FoldAdmits` 21 move / 3 stay
(`RulesComplete.lean:115`, `RestrictBase.lean:470`, `:531`) and the `two_stratum_cascade`
multiplicity re-measure are still owed at step 3, not here.

### 2026-09-13d

STEP 3a LANDED, and step 3 is now SPLIT: 3a (additive, zero cone -- this) and 3b (the
composition + the cone payment). The split was not in the 2026-09-12b plan; it was taken
here after the composition was written, built, and MEASURED, and the measurement is the
main deliverable below. Whole-tree build green (1089 jobs, 0 errors, job count UNCHANGED);
gate `lean` PASSED (holes=0, audits=587, pinned=587 -- no audited name re-opened).

**WHY SPLIT.** The composition itself is small and it is now known exactly: re-point
`writeLoggedOne` onto `bridgePreLogged`, `writeRulesRaw` onto `writeBridgedOne`, wrap
`removeLoggedOne`'s then-branch in `releasePostLogged`. Everything else is fallout. I wrote
that composition, built it, paid the first two modules, and stubbed the one substantive
obligation to see how far the damage runs. It runs far enough that finishing it in one
session was not on the table, and the rule is that each step ends on a green committable
tree -- so the twins land now with their own evidence, and 3b starts from a measured map
instead of a forecast.

**THE MEASURED FALLOUT (this is the number the row did not have).** With the full
composition in place:
* `LeafRules.lean` -- **6 errors, all mechanical**: the five `*_foldl_writeDirect`
  corollaries (`structInv_` / `residueEmpty_` / `inv_` / `quiescent_` / `schema_
  writeRulesRaw`) need bridged twins, which now EXIST (`UsStarWrite.lean::
  *_foldl_writeBridgedOne`), plus `writeRulesRaw_untaintedSchema`.
* `Cascade.lean` -- **7 errors, six mechanical and one real**. Mechanical:
  `writeLoggedOne_evalEq`, `foldl_writeLoggedOne_evalEq`, `writeLoggedRules_evalEq`,
  `writeLoggedRules_watermark`, and the `removeLoggedOne_schema/nodes/watermark` trio. All
  six are discharged by lemmas that landed today.
* `CascadeStable.lean` -- **27 errors across 17 declarations**, listed here because this is
  the map 3b needs: `writeLoggedOne_watermark` (a NAME COLLISION -- that name already
  exists in this file, so do not add it in `Cascade.lean`), `writeLoggedOne_outbox_mono`,
  `writeLoggedRules_edges_mono`, `writeLoggedRules_edge_delta` (x2),
  `reachedByW3d_edgesClosed`, `reachedByW3d_edges_target_plain`, `writeLeg_reach_stable`,
  `affectedObjects_writeLeg_mono`, `cascadeKeys_writeLeg_mono`,
  `untaintedShadow_writeLoggedOne` (x2), `untaintedShadow_foldAdmits`,
  `untaintedShadow_writeLegL` (x8), `writeLoggedRules_residue`,
  `writeLeg_derived_inedges_eq`, `removeLoggedOne_edges_subset`,
  `removeLoggedOne_outbox_mono`, `removeLoggedRules_edge_delta`,
  `mem_removeLoggedOne_edges_iff_of_ne`.
* Nothing past `CascadeStable` was measured -- the build stops there. **Read the counts as
  "at least", never as "only".**
Step 1's forecast is CONFIRMED on the three names it called (`writeLoggedRules_edge_delta`,
the tier-0 `reachedByW3d_edges_target_plain`, `writeLeg_reach_stable`) and INCOMPLETE: the
`untaintedShadow_*` family is 4 declarations and 11 of the 27 error sites, and step 1 did
not name it. That family is the shadow transport, and it is the largest single block in
`CascadeStable`.

**THE ONE SUBSTANTIVE OBLIGATION, and it is now its own row (`TK68`).**
`reachedByW3d_edge_source_ne_R` (audited) is FALSE once the write leg bridges: a bridge
edge is sourced at its CONCRETE endpoint, and that node's predicate can be `R`. Its one
Lean consumer needs `isSubjectWildcardUserset S dt R = false` at the same key it already
knows is derived -- which is Python's SECOND `UnsupportedByGraphIndex` scope rejection
(wildcard usersets over derived relations), and `FullScope.lean::GraphAdmission` has
`objWild` for the first and NO field for the second. Filed as `TK68` with the type-index
trap that makes the general statement unsaveable by a premise. This is a fidelity gap in
its own right, not a proof convenience.

**WHAT IS IN THE TREE NOW -- all additive, all inert, all pinned.**
* `UsStarWrite.lean::GraphState.bridgePre` + `::GraphState.writeBridgedOne` -- the unlogged
  bridged step, `writeDirect` plus Python's bridge-before-grant prologue on BOTH endpoints,
  with the `addNode` pair first (`structInv_ensureInBridges` needs `c` live, and Python
  resolves with `create=True` before `_ensure_bridges`). Preservation family:
  `structInv_` / `residueEmpty_` / `inv_` / `quiescent_writeBridgedOne`, the
  schema/outbox/watermark/residue projections, and all five `*_foldl_writeBridgedOne`.
* `Cascade.lean::GraphState.bridgePreLogged` (the logged twin) and
  `::GraphState.releasePostLogged` (the retract epilogue: `_maybe_remove_bridges(subject)`
  then `(obj)`), with their projections.
* **The hinge**: `Cascade.lean::ensureInBridges_evalEq` (the congruence -- `ensureInBridges`
  reads only schema/edges/nodes and writes only nodes/edges), `::ensureInBridgesLogged_evalEq_congr`,
  `::bridgePreLogged_evalEq`, and `::writeBridgedOne_logged_evalEq`, which is
  literally the theorem step 3b re-points `writeLoggedOne_evalEq` onto. Stated NOW, while
  additive, so the flip is a re-point and `writeLoggedRules_evalEq` keeps its statement.
* `LeafRules.lean::rewriteClosureL_rawWriteTuples_untaintedSchema` -- the LIST half of
  `writeRulesRaw_untaintedSchema`, extracted because it is the half that survives 3b.

**THREE DECISIONS TAKEN HERE** (`CLAUDE.md` "Who decides"), each recorded in the docstring
at the site as well as here:
1. **Not `writeUsStar`.** Re-pointing the leaf-routed fold at the existing
   `writeUsStar` would have been free -- it already bridges and has a theory. REJECTED: it
   also runs `ensureBridges` (the W1b OUT-bridges), and widening the live write leg by a
   second mechanism in the same edit makes any divergence unattributable. A deliberate
   narrowing vs Python, recorded as one.
2. **`writeRules` is NOT bridged; `writeRulesRaw_untaintedSchema` gets restated at 3b.**
   `RulesWrite.lean::writeRules` is the PLAIN shadow rebuild `ReachedByRulesAdmitted` folds;
   its reverse cone is **40** modules against `UsStarWrite`'s **24** (unit: transitive
   importers excl. self and the root aggregator, measured 2026-09-13d). Cost of restating
   is MEASURED at zero consumers: `writeRulesRaw_untaintedSchema` is applied nowhere in the
   Lean development -- only `Audit.lean`'s `#print axioms` row and two prose citations
   (delegated grep, then verified first-hand).
3. **The prologue is a NAMED definition, not a `let`.** `writeUsStar`'s `let` chain
   elaborates to `have` in a goal and BLOCKS `split`; `writeLoggedOne`'s cone is 20 modules
   and every one of them would have had to `dsimp only` first. This cost one wasted build
   cycle before it was noticed.

**THE SWEEP: 11 mutations, table in `UsStarWrite.lean` sec "CONTROLLED -- MUTATION SWEEP over
everything `P6` step 3a added".** `M0` (flip a pin's own claim) attributed correctly, so the
step-0 regex defect has not returned; anchors are read with a no-translation newline mode
and asserted to occur exactly once, so the step-2 CRLF defect has not returned either. Ten
of eleven red a pin; `M10` is INERT and says so (it is step 2's `M6` again --
`inBridgeOnly`'s `bridgedInConcrete` conjunct is defensive).
* (!) **THE SWEEP CHANGED THE DELIVERABLE, which is the argument for sweeping.** On the
  first run `M2` (*bridge the subject only, dropping Python's `_ensure_bridges(obj)`*) and
  `M5` (*probe admission on the UNBRIDGED state*) reddened `structInv_writeBridgedOne` and
  **nothing else** -- a broken PROOF, not a broken claim. Rewriting that proof would have
  retired the only evidence for two of the three things the definition asserts. Added in
  response: `BridgedWriteWitness.tObj` (a member whose OBJECT endpoint is the bridged-in
  shape) and `::tCycle` (a wildcard-userset grant that its own bridge turns into a cycle).
  Both now red. And `tCycle`'s first two pins were NOT enough -- they sit on
  `bridgePre`/`admitEdge` directly while `M5` mutates `writeBridgedOne`, so
  `cycle_write_materialises_nothing`, which reads the write, is the arm that observes the
  order. Three pins were needed to catch one one-word mutation.
* (!) **A harness limitation, recorded because it looks like coverage.** `Cascade` imports
  `UsStarWrite`, so a mutation of `UsStarWrite` stops the build before any `Cascade::` pin
  is evaluated. `M1`-`M6`'s attribution lists are therefore TRUNCATED -- "reds at least
  these". `M6` very likely also reds `Cascade::prologue_second_member_silent`; this sweep
  did not observe it and the table says so.

**NEXT: step 3b.** The composition is three re-points (named above); the map is the
`CascadeStable` list; `TK68` is the one blocking obligation and it is scoped. The bounds
from steps 1 and 2 are unchanged and still apply: do NOT route a stratum-2 userset-subject
obligation through `checkFn`; do NOT narrow `TtuStarFreeW`; do NOT touch
`W4Fragment.ttuStarFree` before step 4. Still owed at 3b, unchanged: the `FoldAdmits`
21-move/3-stay, the `two_stratum_cascade` multiplicity re-measure, the def-pin diff
adjudication, and the honest-direction restatements (`writeLoggedRules_edge_delta`, the two
tier-0 `..._edges_target_plain`, `count_removeLoggedRules`) -- to which today adds
`writeRulesRaw_untaintedSchema` and `reachedByW3d_edge_source_ne_R`.
