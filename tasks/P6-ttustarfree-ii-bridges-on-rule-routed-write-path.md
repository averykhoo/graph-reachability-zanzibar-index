---
id: P6
title: ttuStarFree (ii) -- bridge on the LEAF-routed write path; P3 LANDED 2026-09-05b, collision gone
brief: STEP 3b COMPLETE 2026-09-14e -- steps 3-15 landed, tree GREEN, pins regenerated. Next: part (iv)
pri: NOW
size: L
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 1c868fadf76b
created: 2026-08-20b
moved: 2026-09-14e
updated: 2026-09-14e
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

⚠ **STEP 3b IS UNBLOCKED -- `TK68` CLOSED 2026-09-13e -- BUT THE OBLIGATION IS TWO
THEOREM PAIRS, NOT ONE, AND THE PAIR THIS TRAP USED TO NAME IS THE LESS IMPORTANT ONE.**
`Cascade.lean::reachedByW3d_edge_source_ne_R` (audited) goes FALSE the moment the write leg
bridges: a bridge edge is sourced at its CONCRETE endpoint, whose predicate can be the
derived `R`. So does its verbatim two-round twin `CascadeStrata.lean:1595
::reachedByW3d2_edge_source_ne_R`, whose `write` case takes the SAME
`writeLoggedRules_evalEq -> writeRulesRaw -> foldl_writeDirect_edges_sound` step -- and it is
the W3d2 pair that is ON THE HEADLINE PATH (the W3d cone stops below the headlines; the W3d2
cone reaches `FullScope.lean` and contains `graph_correct`, `graph_correct_public`,
`backend_equivalence`, `exclusion_effective`, `no_ghost_grant`, `graph_reached_inv`).
Measured union: **12 application sites, 47 declarations across 12 files** (`.scratch/
tk68_declcone.py`, 2026-09-13e; 51 counting the four seeds -- state the unit).

The carry to thread is `GraphIndex/UsStarWrite.lean::NoBridgedDerived`, supplied by
`FullScope.lean::GraphAdmission.noBridgedDerived`. ~~It terminates in `GraphAdmission`, so NO
HEADLINE GAINS A HYPOTHESIS.~~ **RETRACTED 2026-09-13g -- VERIFIED FALSE, and it was the most
load-bearing wrong thing on this row.** `GraphIndex/CascadeStrata.lean::runCascade2_no_abort` and
`::cascade2_drains` consume the carry, bind six explicit hypotheses and NO bundle of any kind, and
are BOTH in `formal/headline_statements.txt` and in `formal/verify.sh`'s `HEADLINE_AUDITS`. The
decisive structural check: `isSubjectWildcardUserset` does not occur in `CascadeStrata.lean` at all,
so no predicate in those binders can even mention it, and the sole producer of `NoBridgedDerived`
needs a `GraphAdmission`. **TWO STATEMENT-PINNED HEADLINES GAIN `(hNBD : NoBridgedDerived S)`** and
the statement pin moves by two rows -- legal and honest, but a deliberate reviewed change owing the
RED-first / `--generate` / dated `formal/history/` note sequence in the `TK68` shape. Decide it at
the START of step 10. Detail: `docs/p6-step3b-plan-2026-09-13.md` sec "C3".

⚠ **Do NOT extend `W4Fragment.term` to carry it -- that is a 134-SITE EDIT.** Every one of
the 47 already holds `hterm`, so adding a conjunct there looks like the cheap fix. `hterm` is
a bare lambda at 134 declarations with no abbreviation, and being STORE-indexed it needs a
two-line weakening lambda at 22 of them. `NoBridgedDerived` is store-free precisely so it
threads through a `write`/`remove` step verbatim.

⚠ **RESTATE, do not re-premise -- the type-index trap.** `isDerived` and
`isSubjectWildcardUserset` are keyed on `(type, relation)` while both `edge_source_ne_R`
theorems conclude about the predicate STRING. A literal `[x:*#R]` restriction at an UNTAINTED
key `(x, R)` is legal Python and bridges a node whose pred is `R`, so `a.pred != R` is false
as a general claim whatever premise is added; the restatement must carry the TYPE. Legal to
do: neither theorem's STATEMENT is pinned (only the NAMES, in `formal/audited_theorems.txt`
-- and note `reachedByW3d2_edge_source_ne_R` is not even there).

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

- **READ [`docs/p6-step3b-plan-2026-09-13.md`](../docs/p6-step3b-plan-2026-09-13.md) sec
  "Corrections appended 2026-09-13g -- what the recon sweep changed" BEFORE the plan body, because
  it SUPERSEDES that body wherever the two disagree** -- and its headline item is that step 8's
  third `term` obligation (T3) is REFUTED: `W4Fragment.bareStar` constrains STORED tuples only and
  does NOT make a bridge node terminal, so step 8 must additionally thread
  `formal/lean/ZanzibarProofs/GraphIndex/RulesCorrect.lean::TtuTuplesetsDirect` and
  `formal/lean/ZanzibarProofs/GraphIndex/RulesBareStar.lean::TtuStarFree` onto
  `formal/lean/ZanzibarProofs/GraphIndex/CascadeStable.lean::reachedByW3d_shadow` (both providers
  already exist, so no new admission field) and owes a new L-closure star-bare lemma family.
- **[`docs/p6-step3b-plan-2026-09-13.md`](../docs/p6-step3b-plan-2026-09-13.md) IS THE STEP-3b
  EXECUTION MAP AND IT REPLACES THE SCOUTING, NOT THE ROW** (ACTIVE-PLAN, opened 2026-09-13f;
  corrections append dated at the top; freeze it when `P6` closes). Fifteen ordered steps, the
  per-module fallout, the six blockers, and a "Corrections to the `P6` row" section listing the
  points where the row and this file DISAGREE -- each verified first-hand before it was written.
  Read it BEFORE re-measuring anything: the reason it exists is that the measuring is the
  expensive half (`CLAUDE.md` sec "SCOUTING IS A DELIVERABLE"). (!) Its largest correction is that
  the row's standing claim *"the carry terminates in `GraphAdmission`, so NO HEADLINE GAINS A
  HYPOTHESIS"* is **FALSE** --
  `formal/lean/ZanzibarProofs/GraphIndex/CascadeStrata.lean::runCascade2_no_abort` and
  `::cascade2_drains` are statement-pinned headlines (`formal/headline_statements.txt`) that
  consume the carry and so gain `(hNBD : NoBridgedDerived S)`.
  (!) Two of its items are flagged NOT first-hand verified in place; do not promote either into a
  tracked file without confirming it.
- **The `2026-09-13e` Log entry is what step 3b starts from for the R-NODE obligation** --
  `TK68` is closed, the field/carry/bridge are in the tree, and the cone is MEASURED at 12
  application sites / 47 declarations / 12 files across BOTH twin pairs (the entry names the
  W3d2 pair the earlier entries missed, and it is the one on the headline path). The code:
  `formal/lean/ZanzibarProofs/GraphIndex/UsStarWrite.lean::NoBridgedDerived` (the carry to
  thread, and the type-index trap in its docstring),
  `formal/lean/ZanzibarProofs/FullScope.lean::GraphAdmission.usWild` /
  `::GraphAdmission.noBridgedDerived`, and
  `formal/lean/ZanzibarProofs/FullScope.lean` sec "CONTROLLED -- MUTATION SWEEP over
  everything `TK68` added" (the evidence table and the two instrument findings). ⚠ That
  sweep's lesson is one step 3b will hit: **Lean error-recovers a failed declaration**, so a
  pin routed through a helper lemma cannot observe a mutation upstream of it -- the
  tautology attack reddened the helper alone across two runs.
  `docs/sabotage-procedure.md` sec "Sweep the TEST MODULE with mutations".
- `formal/history/tk68-uswild-admission-field-2026-09-13.md` (FROZEN) -- the def-pin
  adjudication `formal/verify.sh` step 4c demands, the three sweep runs compared, and the measured
  cone table. Read it for the PRECEDENT the next def-pin firing needs, and for why
  extending `W4Fragment.term` is the wrong route.
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

### 2026-09-13e

STEP 3b IS UNBLOCKED: `TK68` is CLOSED (2026-09-13e). No `P6` code moved this session -- the
write leg still does not bridge -- so this is a comment, not a step. What changed is that
3b's one blocking obligation is paid and its cone is MEASURED instead of forecast.
Whole-tree Lean build green (1089 jobs, job count UNCHANGED). Full write-up:
`formal/history/tk68-uswild-admission-field-2026-09-13.md` (FROZEN).

WHAT 3b CAN NOW ASSUME, already in the tree, audited and swept:
* `FullScope.lean::GraphAdmission.usWild` -- no derived key is a subject-wildcard userset
  shape. Discharged `by decide` at all SEVEN construction sites.
* `GraphIndex/UsStarWrite.lean::NoBridgedDerived` -- the schema-level, store-FREE carry, and
  `FullScope.lean::GraphAdmission.noBridgedDerived` as the bridge from the decidable field.

(!) THE ROW NAMED HALF THE WORK, AND THE HALF IT MISSED IS THE ONE ON THE HEADLINE PATH.
The `2026-09-13d` entry and `TK68` both name only `reachedByW3d_edge_source_ne_R` and its
one consumer. There is a SECOND, verbatim twin pair -- `CascadeStrata.lean:1595
::reachedByW3d2_edge_source_ne_R` and `:1667::reachedByW3d2_Rnode_not_source` -- whose
`write` case takes the SAME `writeLoggedRules_evalEq -> writeRulesRaw ->
foldl_writeDirect_edges_sound` step, so it goes false for exactly the same reason once the
leg bridges. Measured first-hand (`.scratch/tk68_declcone.py`, 2026-09-13e; unit:
APPLICATIONS = occurrences in comment-stripped bodies, CONE = transitive consumer closure
excl. the seeds):

  `Cascade.lean::reachedByW3d_edge_source_ne_R`        audited   1 app   14 decls / 5 files
  `Cascade.lean::reachedByW3d_Rnode_not_source`        audited   2 app   13 decls / 5 files
  `CascadeStrata.lean::reachedByW3d2_edge_source_ne_R` NOT aud.  1 app   35 decls / 8 files
  `CascadeStrata.lean::reachedByW3d2_Rnode_not_source` audited   8 app   34 decls / 8 files
  union of the four                                             12 app   47 decls / 12 files
                                                                         (51 with the seeds)

The W3d cone TERMINATES BELOW the headlines. The W3d2 cone reaches `FullScope.lean` and
contains `graph_correct`, `graph_correct_public`, `backend_equivalence`,
`exclusion_effective`, `no_ghost_grant` and `graph_reached_inv`. Budget both pairs.

(!) DO NOT EXTEND `W4Fragment.term` -- it is the obvious-looking route and it is a 134-SITE
EDIT. Every one of the 47 already carries `hterm` (that conjunction), so adding a conjunct
to it looks like the cheap fix. It is not: `hterm` is spelled out as a bare lambda at 134
declarations (there is no abbreviation for it; the only name is the `W4Fragment.term` field
itself) and, being STORE-indexed, needs a two-line weakening lambda at 22 of them
(`t :: T -> T` via `List.mem_cons_of_mem`, `T -> T.erase t` via `List.mem_of_mem_erase`).
`NoBridgedDerived` is store-free precisely so it threads through a `write` or `remove` step
VERBATIM. That is the whole reason for its shape.

TWO FACTS THAT MAKE 47 AFFORDABLE:
(1) it TERMINATES IN `GraphAdmission`, so NO HEADLINE GAINS A HYPOTHESIS. `graph_correct`
    (`FullScope.lean:616`) already binds `hA : GraphAdmission S T` and passes explicit field
    projections down to `graph_correct_w3d2E_d`; `hA.noBridgedDerived` is one more entry in
    that list. Same route `noLeafSubjects`/`keysNonempty` took through
    `GraphAdmission.leafScope`.
(2) THE RESTATEMENT IS LEGAL, measured: NEITHER theorem's STATEMENT is pinned. Neither name
    appears in `formal/headline_statements.txt` or `formal/headline_definitions.txt` (those
    pin `def`s reachable from headline statements; these are theorems used only inside
    proofs). Only the NAMES are pinned, in `formal/audited_theorems.txt` -- so 3b may
    restate freely provided the names stay audited. Note the asymmetry:
    `reachedByW3d2_edge_source_ne_R` is NOT in the audit pin while the other three are.

(!) THE TYPE-INDEX TRAP STILL GOVERNS, and it is now recorded where the work happens
(`NoBridgedDerived`'s docstring, not just on the closed `TK68`). `isDerived` and
`isSubjectWildcardUserset` are keyed on `(type, relation)` while both `edge_source_ne_R`
theorems conclude about the predicate STRING. A literal `[x:*#R]` restriction at an UNTAINTED
key `(x, R)` is legal Python and bridges a node whose `pred` is `R`. So RESTATE to carry the
type; the general claim cannot be rescued by any premise.

(!) A SWEEP LESSON 3b WILL NEED, because it is invisible when it bites: LEAN ERROR-RECOVERS A
FAILED DECLARATION. `TK68`'s sweep took THREE runs. The tautology attack on the new field
reddened the helper lemma alone on runs 1 AND 2 -- run 2 having added four pins specifically
to catch it -- because when a declaration's proof fails Lean still admits it at its stated
type, so downstream uses elaborate cleanly and a pin routed through a helper cannot observe
anything upstream of it. Rerouting the pins off the primitive is what finally reddened a
CLAIM. Filed as a general rule in `docs/sabotage-procedure.md` sec "Sweep the TEST MODULE
with mutations". Joins the cross-module truncation limit step 3a recorded: an attribution
list means "at least these", never "only these" -- and this one is worse, because the build
does not stop and nothing looks wrong. A related one from the same run: an arm instantiated
at a CONCRETE witness is defeq-blind to a mutation that preserves the witness's value (two
different `Bool` predicates both evaluating `false` make the two propositions definitionally
equal at that schema).

STILL OWED AT 3b, unchanged from `2026-09-13d` and none of it paid here: the three re-points
(`writeLoggedOne` -> `bridgePreLogged`, `writeRulesRaw` -> `writeBridgedOne`,
`removeLoggedOne`'s then-branch wrapped in `releasePostLogged`); the `CascadeStable` map of 27
errors across 17 declarations, of which the `untaintedShadow_*` family is the largest block;
the `FoldAdmits` 21-move/3-stay; the `two_stratum_cascade` multiplicity re-measure; the def-pin
diff adjudication (the ONE piece of this list now done -- the pin fired on the `usWild` field
and was regenerated with its justification, so 3b has a worked precedent for the next firing);
and the honest-direction restatements (`writeLoggedRules_edge_delta`, the two tier-0
`..._edges_target_plain`, `count_removeLoggedRules`, `writeRulesRaw_untaintedSchema`), to which
`reachedByW3d_edge_source_ne_R` now adds its W3d2 twin.

BOUNDS UNCHANGED: do NOT route a stratum-2 userset-subject obligation through `checkFn`; do
NOT narrow `TtuStarFreeW`; do NOT touch `W4Fragment.ttuStarFree` before step 4.

### 2026-09-13g

SESSION OPENED 2026-09-13g -- interim state comment, written BEFORE the work so it is not lost
(the new `CLAUDE.md` rule "SCOUTING IS A DELIVERABLE" is this session's, same instruction).

WHERE 3b ACTUALLY STANDS, measured first-hand this session:
* Steps 1 and 2 of `docs/p6-step3b-plan-2026-09-13.md` ARE ALREADY IN THE WORKING TREE,
  uncommitted and never gated. `git diff --stat`: `UsStarClosure.lean` -31/+?, `UsStarCorrect.lean`
  -39, `UsStarWrite.lean` +521. The four MOVES landed (`bridgedInConcrete_elim`,
  `ensureInBridges_edges_mono`, `ensureInBridges_edges_mem`, `ensureInBridges_nodes_mem`) and so did
  the step-2 toolbox including THE KEYSTONE `foldl_writeBridgedOne_edges_sound`, plus
  `edgesClosed_{,foldl_}writeBridgedOne`, both `_nodes_mono`/`_nodes_sound` pairs, and three
  negative controls (`two_disjunct_soundness_is_false`, `node_soundness_without_{subject,object}_wany_is_false`).
* STILL OWED from step 2, confirmed absent: `foldl_writeBridgedOne_nodesFromEdges` (the one the plan
  flags NON-TRIVIAL -- the accept branch can intern a `wAnyNode` with no incident edge, so it needs
  `edgesClosed` as a side condition) and `foldl_writeBridgedOne_edge_complete` (deliberately
  deferred; it is stated over `FoldAdmits`, the step-14 honesty question).
* NOTHING past step 2 has been attempted. The three re-points are NOT made.

(!) THE LEAN VERDICT ON THIS TREE IS UNKNOWN, AND THE FIRST RUN LIED IN A NEW WAY.
`bash formal/verify.sh lean` returned `EXIT=1` with `error: build failed`, but the only two errors
were `failed to open file ...UsStarWrite.olean: 2` at `CascadeStrataEnum` and `Equiv` -- and
`UsStarWrite.lean` itself logged ZERO errors. Cause, established by process inspection rather than
guessed: a BARE `lake build` (pid 16596, started 23:15:43, parent not `verify.sh`) was running
concurrently and was mid-write of that `.olean` when the gate tried to read it. So the red is an
artifact of the race, not a proof failure -- and the tree's real lean status is still UNMEASURED.
NEW VARIANT WORTH CARRYING: `verify.sh`'s run lock (`scripts/gate_lock.py`, added after the
2026-09-10 two-writers-one-filename bug) only excludes another `verify.sh`. A bare `lake build` --
which any subagent can run, and one did here despite a read-only instruction -- is NOT excluded, and
it corrupts the gate's view of a file the gate never edited. Before believing a `lean` red whose
errors are all `failed to open file ... .olean`, run `Get-CimInstance Win32_Process -Filter
"Name='lake.exe' OR Name='lean.exe'"` and re-run alone.

NEXT ACTION when this session resumes or the next one starts: re-run `verify.sh lean` ALONE on the
untouched tree to get the real step-1+2 verdict. End of step 2 is one of only TWO commit-safe points
in the whole of 3b (the other is the end of step 15), so if it is green it should be committed
before any re-point is made.

STEP 3b: THE ADDITIVE HALF IS DONE AND GREEN. Two decisions taken, and the row's central standing
claim is now REFUTED by first-hand verification. Full map: `docs/p6-step3b-plan-2026-09-13.md`
sec "Corrections appended 2026-09-13g" (C1-C9 + a post-step-2 symbol table). Read that, not this entry,
before executing -- this entry is the index.

WHAT LANDED (whole-tree `lake build` rc=0, `Build completed successfully (1089 jobs).`; audited
CLEAN-ADDITIVE by an independent agent that md5-matched the four moved blocks and diffed sixteen
definition bodies to confirm none moved):
* Steps 1-2 of the plan, committed green at `30ad44a` with the TEN-PHASE GATE COVERED.
* 18 further declarations, ALL ADDITIVE: the `nodesFromEdges` family in `UsStarWrite.lean`, eleven
  bridge-leg lemmas in `Cascade.lean` (outbox_mono / edges_subset / edge_delta at BOTH the per-leg
  and epilogue levels), and the step-4 schema quartet relocated up into `Cascade.lean`.
* NOTHING IS RE-POINTED. The write leg still does not bridge.

(!) DECISION 1 -- THE RE-PLAN, AND IT IS THE REUSABLE ONE. The plan says steps 3-15 are one red run
with no commit point until the end. That is false, and believing it costs a session's work every time
it is believed: a large slice of the owed work mentions only definitions that ALREADY EXIST, so it
lands green and committable BEFORE any re-point. That is where all 18 came from. **Ask of every owed
lemma "does this mention a definition that already exists?" before assuming it must wait.** There is
now a THIRD commit-safe point and there are probably more.

(!) DECISION 2 -- TAKE THE `rewriteClosureL_star_bare` ROUTE FOR THE SHADOW'S T3; REFUSE THE THREE-LINE
ONE. The plan's T3 justification is REFUTED (verified first-hand, twice): `BareStarStore T` quantifies
over STORED tuples, while the obligation is about members of `rewriteClosureL S (rawWriteTuples S t)`
-- and `applyRRule`'s ttu arm MANUFACTURES a non-BARE star subject (it preserves the subject NAME, so
`STAR` survives, and overwrites the predicate with the TTU target), which is exactly the through-shape
that makes `isSubjectWildcardUserset` true. A cheap alternative exists and MUST NOT be taken:
`rewriteClosureL_subject_pred_gen` + `TtuTargetsSatL` gives T3 in ~3 lines, but its provider is a
SCHEMA-LEVEL ban on a bare wildcard restriction over a TTU tupleset relation, which REJECTS
through-shape schemas the store-level `TtuStarFree` admits. That narrows the Lean fragment below what
the Python compiler accepts -- the wrong direction under `CLAUDE.md` sec "Who decides", where the
fragment catches up to the code and never the reverse. Cost accepted instead: thread
`TtuTuplesetsDirect S` + `TtuStarFree S T` into `reachedByW3d_shadow` and its two W3d2 twins (call-site
cost ZERO -- all five sites already bind both), mint an L-analogue of `rewriteClosure_star_bare`, and
kill the leaf-ttu arms with the already-bound `hCO`. NO new `GraphAdmission` field. ⚠ A THIRD gap the
first sweep missed and the verification found: `TtuStarFree` quantifies over `schemaRewrites S` while
`rewriteStepL` steps over `schemaRewritesL S = schemaRewrites S ++ leafRewrites S`, so leaf ttu arms
sit OUTSIDE its quantifier entirely.

(!) DECISION 3 -- AT STEP 10, BIND THE BARE `NoBridgedDerived S` ON THE TWO HEADLINES, NEVER
`LeafScope S`, even if step 8 folds the carry into `LeafScope`. Binding `LeafScope` there would drag
its other fields into two statement-pinned headlines that do not use them, enlarging the pin diff and
claiming scope restrictions the cascade theorems do not need.

(!) THE ROW'S STANDING CLAIM IS FALSE, AND THIS ENTRY RETRACTS IT. The `## Traps` section still says
the carry "terminates in `GraphAdmission`, so NO HEADLINE GAINS A HYPOTHESIS". VERIFIED FALSE:
`CascadeStrata.lean::runCascade2_no_abort` and `::cascade2_drains` bind six explicit hypotheses and no
bundle of any kind; `isSubjectWildcardUserset` does not occur in `CascadeStrata.lean` at all, so no
predicate in those binders can even mention it; and the sole producer of `NoBridgedDerived` needs a
`GraphAdmission`. Both are in `formal/headline_statements.txt` and in `verify.sh`'s `HEADLINE_AUDITS`.
So TWO statement-pinned headlines gain `(hNBD : NoBridgedDerived S)` and the statement pin moves by two
rows -- legal and honest, but a deliberate reviewed change owing the RED-first / `--generate` / dated
`formal/history/` note sequence, in the `TK68` shape. DECIDE IT AT THE START OF STEP 10, NOT AT STEP 15.

(!) A NEW EXIT-CODE FOOTGUN VARIANT, and the earlier entry this session wrote MIS-ATTRIBUTED IT.
A `lean` run returned `EXIT=1 / build failed` whose ONLY errors were `failed to open file
...UsStarWrite.olean: 2`, with zero errors against `UsStarWrite.lean` itself. Cause, established by
process inspection: a bare `lake build` was mid-write of that `.olean`. The earlier entry guessed a
subagent had disobeyed a read-only instruction; it had not -- the build belonged to the PREVIOUS
session's background workflow, still running when this session started. `verify.sh`'s run lock excludes
another `verify.sh`, NOT a bare `lake build`, and not a job outliving the session that spawned it.
Check `Get-CimInstance Win32_Process -Filter "Name='lake.exe' OR Name='lean.exe'"` and re-run alone;
the re-run PASSED unchanged.

NEXT ACTION: step 3 (the LeafRules re-point) is the first RED step. Before it, re-read plan sec C9 --
it may contain further additive work worth landing green first.

### 2026-09-13h

STEP 8's SUPPORT LAYER IS LANDED AND GREEN -- T2 and T3 are machine-checked instead of paper proofs.
Same session as `2026-09-13g`, second committed batch. Detail:
`docs/p6-step3b-plan-2026-09-13.md` sec "C10".

THE POINT: the shadow (step 8) was the plan's SINGLE SCHEDULE RISK -- the one piece with no landed
design, gating all 19 downstream modules, whose worst case was a `TK68`-sized new admission field.
Applying `C9`'s additive-first test to it shows its *support* layer mentions only definitions that
already exist, so it lands GREEN before the red run rather than inside it. **69 declarations**,
whole-tree build rc=0, audited CLEAN-ADDITIVE with ZERO deletions tree-wide, pins and anchors at
baseline (`51/51`, `253/253`, `643/643`).

WHAT THAT BUYS: step 8's go/no-go is answered. NO new `GraphAdmission` field. T3 costs the shadow
family exactly two new binders (`TtuTuplesetsDirect S`, `TtuStarFree S T`), both already bound at all
five call sites. T2 costs ZERO new binders -- its four premises are 1, 2, 5 and 6 of
`reachedByW3d_shadow` verbatim. The remaining step-8 work is the widening itself, which is red.

(!) THE LEAF-TTU GAP IS NOW A KERNEL REFUTATION, NOT A CLAIM.
`CascadeStable.lean::StarBareWitness.slStP_leaf_ttu_breaks_star_bare` proves that at
`LeafRuleWitness.SlStP` every premise EXCEPT the ComputedOnly one holds and the conclusion is FALSE --
a bare `folder:*` parent walks out of the L closure carrying predicate `viewer`. `TtuStarFree`
quantifies over `schemaRewrites S` while `rewriteStepL` steps over
`schemaRewritesL S = schemaRewrites S ++ leafRewrites S`, so leaf ttu arms sit outside its quantifier
entirely. Neither the plan body nor the first recon sweep saw this.

(!) AN AUDIT FOUND A VACUITY HOLE AND IT IS CLOSED -- AND THE SHAPE IS WORTH CARRYING.
`not_bridgedInConcrete_of_leafNode` is the form `ShadowOver.term` will consume and needs a `LeafNode`
AND the four premises AT THE SAME SCHEMA. `LeafNode` was pinned only at `Sw`, the premises only at
`Snv` -- so the composed lemma had no witness of its own and could have been vacuously true at every
schema in the development while looking fully pinned. Closed by
`LeafBridgeWitness.snv_has_a_leafNode`, routed through the proved decider `Leaf.lean::leafNodeB_correct`.
**Each hypothesis family pinned separately proves nothing about their conjunction** -- check for this
whenever a lemma composes two of them.

(!) NEW GATE TRAP, MEASURED: `statement_pin.py` pins an `ambient:<path>` row -- a file's `variable` /
`open` lines in order. In `CascadeStable.lean`, `CascadeStrata*.lean` or any pin-hosting module, a
single additive `open` REDS step 4c while `51/51 statements match` stays green. Fully qualify instead.

CORRECTIONS TO THE PLAN'S OWN CORRECTIONS (both in the safe direction, both now machine-checked):
`C1`'s premise list undercounts by two (`NodupKeys S` and `hmd`, both FREE from
`reachedByW3d_shadow` premises 1 and 7, `hmd` via `LeafScope.matchNotLeaf`) and `C2`'s by one
(`NodupKeys S`). `C1`'s cited instrument for sub-obligation (b) is the wrong lemma -- the proof uses
`isLeafPred_outRel_of_mem_leafRewrites`, and `isLeafPred_eq_false_of_relNameOK` is what BUILDS `hmd`
one level up. `C1` budgeted the leaf-ttu killer as possibly "the bulk of the work"; it went through
unrestricted in nine declarations, because the `ComputedOnly` twin of the purity chain is EASIER than
the `isPure` original it copies.

STILL OWED ON THIS LAYER, recorded rather than asserted: `hmd` has no negative control (load-bearing
at four arms by inspection, but no fixture exhibits a schema where it fails); and no source-level
sabotage rebuild of the T2 payoff was run -- the narrowest plausible weakening to try is dropping the
disjunct-(b) branch and asserting from `hDR` alone, which should fail at `SnvLeafTtu`.

NEXT ACTION UNCHANGED: step 3 (the `LeafRules` re-point) is the first RED step, and it is still not
started. Before it, re-read plan secs C9 and C10 -- the additive-first test has now paid twice and may
pay again.

### 2026-09-14

STEP 14 IS NOT "DEFERRABLE IF RECORDED" ANY MORE -- it is a CORRECTNESS obligation, and the proof is
now in the tree. Plus `BridgeNode`, the `FoldAdmitsBridged` family, and both owed evidence items from
`2026-09-13h` discharged. Detail: `docs/p6-step3b-plan-2026-09-13.md` sec "Corrections appended
2026-09-14" and sec "C10".

(!) THE FINDING, AND IT CHANGES THE PLAN'S RANKING OF STEP 14.
`Cascade.lean::FoldAdmitsHonestyWitness.foldl_edge_complete_is_false_for_the_bridged_fold` is a KERNEL
refutation, verified first-hand this session:
  `¬ (∀ us σ, FoldAdmits σ us → ∀ u ∈ us, edgeOf u ∈ (us.foldl writeBridgedOne σ).edges)`
i.e. `RulesComplete.lean::foldl_writeDirect_edge_complete` -- the workhorse EVERY write-leg
edge-completeness argument runs through -- restated over the bridged fold while keeping `FoldAdmits`
as its hypothesis is FALSE. The weakening refuted is the narrowest plausible one: character-for-
character the existing lemma with `writeDirect` swapped for `writeBridgedOne`, which is exactly what
the step-3 re-point does to the code while leaving the binder untouched. **So a session that lands
step 3 and leaves the `hadm` binders alone is not merely "describing the wrong fold" (the plan's
wording) -- it is entitled to a FALSE conclusion.** The plan's toolbox entry
"`foldl_writeBridgedOne_edge_complete` -- BLOCKED on the FoldAdmits decision" is now decided
MECHANICALLY rather than by judgement: it cannot be stated over `FoldAdmits` at all.

LANDED (all additive, whole-tree build green, audited CLEAN-ADDITIVE, sabotage logs independently
corroborated line-by-line against the raw `lake` output by the auditor):
* `Cascade.lean::FoldAdmitsBridged` + `decFoldAdmitsBridged` + `foldAdmitsBridgedB` +
  `foldAdmitsBridgedB_iff` -- step 14's additive half, pre-paid. The MOVE (19 `hadm` binders, 3
  stay-sites, 2 `foldAdmitsB` runtime gates) is red work and is untouched.
* `::FoldAdmitsHonestyWitness` (11 decls) -- the disagreement is pinned at the LITERAL argument shape
  `ReachedByW3d.write`'s `hadm` binds, with two attribution controls showing the two predicates AGREE
  where the bridge merely fires, so the divergence is the cycle and not bridging.
* `CascadeStable.lean::BridgeNode` + intro/elim + `not_bridgedInConcrete_of_bridgeNode` +
  `not_derNode_of_bridgeNode` (the two extras disjuncts are DISJOINT by variant) +
  `not_bridgeNode_of_star_bare` (T3 in the shape `ShadowOver.term` consumes, all six premises free at
  `reachedByW3d_shadow`) + `bridgeNode_nonvacuous`. DEFINED and left UNUSED by `UntaintedShadow` --
  the widening itself is the red step.

(!) A DELIBERATE TRIPWIRE IS NOW IN THE TREE -- DO NOT "FIX" IT BY WEAKENING THE CONSTRUCTOR.
`Cascade.lean::FoldAdmitsHonestyWitness.w3d_write_applies_with_the_stale_hypothesis` inhabits the live
`ReachedByW3d.write` constructor at the cycle fixture TODAY. When step 14 re-points `hadm` to
`FoldAdmitsBridged`, no term can inhabit it there and the declaration goes RED -- which is the point:
the honesty fix cannot land silently. The prescribed response is in its docstring (move the pin to an
admitted fixture and record the flip).

BOTH OWED EVIDENCE ITEMS FROM `2026-09-13h` ARE DISCHARGED:
* `hmd`'s negative control exists (`StarBareWitness.SmdLeaf` + `smdLeaf_hmd_breaks_star_bare`), and
  the answer is a SPLIT the plan ran together: `hmd` CAN fail at a WF schema -- so do NOT drop the
  premise, the general lemma is false without it -- but CANNOT fail at a `GraphAdmission`-ADMITTED
  one. The provider is `RestrictBase.lean::RewriteMatchDeclared` via `GraphAdmission.matchDecl`, NOT
  `WF` (`WF.relNames` constrains declared key names only, never a name a body references). Both halves
  are pinned, not asserted.
* The T2 payoff sweep ran (M0 instrument control + M1/M2 the prescribed weakening and its dual + M4 a
  propagation control), and the table with each mutation's LITERAL `lake` output is in
  `CascadeStable.lean` sec "CONTROLLED -- MUTATION SWEEP (2026-09-14)".

(!) THE ERROR-RECOVERY FAILURE MODE RECURRED FOR THE THIRD INDEPENDENT TIME, AND IT INVALIDATED THE
PRESCRIBED SABOTAGE. M1 and M2 each reddened EXACTLY ONE declaration -- their own -- while every
consumer and control stayed GREEN, because Lean admits a failed declaration at its stated type. So
`C10`'s prescribed sabotage could NEVER have shown the weakened THEOREM false; it could only show that
PROOF incomplete. M4 (deleting the premise from the STATEMENT) propagated to three declarations, which
is the contrast that identifies the cause: **statement changes are observed, proof changes are not.**
The durable answer landed instead of the docstring: `hQ_free_statement_is_false` and
`hDR_free_statement_is_false` are kernel refutations of the two weakened READINGS.

NEXT ACTION, UNCHANGED AND NOW THE ONLY THING LEFT THAT IS NOT ADDITIVE: step 3, the `LeafRules`
re-point. Every piece of step-3b work that could be done without re-pointing has now been done and
committed green across four commits. What remains is genuinely red from step 3 to step 15.

### 2026-09-14e

STEP 3b IS COMPLETE. Steps 3-15 all landed; the whole tree is GREEN and the ten-phase gate
was run on it. `lake build` rc=0, `Build completed successfully (1089 jobs).`
Full map: `docs/p6-step3b-plan-2026-09-13.md` sec "Corrections appended 2026-09-14d" (start
there), then "...2026-09-14c" and "...2026-09-14b". Pin rationale:
`formal/history/p6-step3b-pin-regeneration-2026-09-14.md`.

WHAT LANDED. All three re-points plus step 14:
* RE-POINT #2 (`LeafRules.lean::GraphState.writeRulesRaw` folds `writeBridgedOne`),
  #1 (`Cascade.lean::GraphState.writeLoggedOne` = `bridgePreLogged` + `addEdge` + delta),
  #3 (`::removeLoggedOne`'s then-branch wrapped in `releasePostLogged`).
* Step 6 + its W3d-2 twin: the R-node restatement, conclusion gains `a.type = dt`,
  hypotheses gain `(hNBD : NoBridgedDerived S)`; carry threaded ~30 sites and DISCHARGED at
  `FullScope.lean::GraphAdmission.noBridgedDerived`.
* Step 8 -- the plan's SINGLE SCHEDULE RISK -- cost a ONE-LINE `abbrev` widening
  (`UntaintedShadow` gains the `BridgeNode` disjunct) because `C10` had pre-paid its 69
  support declarations. NO new `GraphAdmission` field, exactly as forecast.
* Step 14 (`FoldAdmits` -> `FoldAdmitsBridged`, 17 binders / 6 files) and the two RUNTIME
  GATES (`Exec.lean::graphRunAux`, `::graphRunOpsAux` -> `foldAdmitsBridgedB`).

(!) STEP 14 IS A PRECONDITION OF STEP 8, NOT A FOLLOW-UP -- and the kernel forced it, not a
judgement call. `untaintedShadow_writeLegL` needs `foldl_writeBridgedOne_edge_complete`, and
the 2026-09-14 refutation says that lemma cannot be stated over `FoldAdmits` AT ALL. The
executed order was 3 -> 5 -> 6 -> 7 -> 14 -> 8. The plan's ordering is impossible; do not
restore it.

(!) THE DELIBERATE TRIPWIRE FIRED, ALONE, AND THAT IS THE CHEAPEST ASSURANCE IN THIS ITEM.
Moving the constructor binder produced EXACTLY ONE error, at
`Cascade.lean::FoldAdmitsHonestyWitness.w3d_write_applies_with_the_stale_hypothesis` -- the
declaration planted the day before for this moment. Prescribed response applied (pin moved
to an admitted fixture, constructor NOT weakened); the flip and the literal error text are
recorded at `::w3d_write_applies_with_the_bridged_hypothesis`. A trap that reddens ONE
declaration is worth more than one that reddens a module: it distinguishes "the constructor
moved" from "the file broke".

(!) THE LARGEST THING THE PLAN DID NOT CONTAIN: the R3/R4 occurrence-count stack needed a
SCOPE. R3 says an UNTAINTED edge's multiplicity equals `untOccCount`; the bridged leg
materialises edges that are no tuple's `edgeOfTuple`, so R3 is FALSE as stated -- and
NEITHER existing guard fences them out. R3-target's `isDerived = false` ADMITS them
(`NoBridgedDerived` says a bridged shape is exactly untainted); R3-source's `a.pred != BARE`
admits them too. Fixed with `b.variant != Variant.wAny`, free wherever `b` is a literal
`objNode` (`State.lean::objNode_ne_wAny`, minted for it). ⚠ Membership monotonicity is NOT
enough -- a leg erasing one copy of a doubly-present edge preserves `∈` and breaks `count`.
One site needed a new structural lemma rather than a binder:
`CascadeStrata.lean::reachedByW3d2_wAny_edge_bridged`.

(!) THE SECOND: the `_d` chain carries `ComputedOrDirect`, not `ComputedOnly`, so T2/T3
could not be discharged there. GENERALISED rather than forked -- the chain never needed
`.direct` absent, it needed `.ttu` absent, and both predicates forbid `.ttu`. Eleven twins
landed; see sec F2.

PINS (step 15), all deliberate and RED-first:
* statement pin RED at exactly the two rows sec Blockers named (`runCascade2_no_abort`,
  `cascade2_drains`), each gaining `hNBD` and nothing else.
* definition pin 253 -> 264, and the MEMBERSHIP change is the evidence: `FoldAdmits` and
  `foldAdmitsB` LEFT the pinned closure; `FoldAdmitsBridged`, `foldAdmitsBridgedB`,
  `NoBridgedDerived` and nine bridge definitions ENTERED it. The stale predicates leaving
  and the honest ones entering is the best evidence step 14 did what it claims.
* `Exec.lean::reachedByW3d2E_edgeCount_store_indexed`'s staleness trap fired as designed
  (hand-copied R3 statement); updated, NOT simplified -- the duplication is the mechanism.
* `audited_theorems.txt` UNTOUCHED. `anchor_check` 659/659 (the checker caught three bad
  paths in my own new CORRESPONDENCE prose). `FINAL_REVIEW.md` counts regenerated.

ASSURANCE ADDED, and two sweeps CHANGED THE DELIVERABLE:
* `LeafRules.lean::SlBridgeWitness` (14 pins) and `Cascade.lean::BridgedLegWitness` (8 new)
  sit on the definitions that MOVED -- every step-3a witness is stated on `bridgePre`/
  `writeBridgedOne` directly and so cannot be flipped by any re-point. Sweep tables with
  literal `lake` output are in the docstrings.
* M8 found an OVERCLAIMING docstring: a `!=` non-vacuity pin stayed green under the very
  mutation it was cited as guarding. Fixed by COUNTING. A `!=` non-vacuity is the weakest
  useful form -- prefer one that names the thing or counts it.
* M9 reddened ONLY A PROOF on its first pass -- the error-recovery mode again. Fixed by
  adding a cycle fixture at `writeLoggedOne`. The step-3a order pins could not see it
  because they never mention the definition that moved.

(!) TWO AUDITED NAMES ARE NOW MILDLY MISLEADING AND MUST STAY:
`reachedByW3d_edges_target_plain` (and its W3d-2 twin) conclude `!= Variant.wAll`, not
`= Variant.plain` -- the old reading is FALSE since a bridge target is `wAny`. Renaming reds
step 4a. Same for `LeafRules.lean::writeRulesRaw_untaintedSchema`, which no longer mentions
`GraphState.writeRules` at all (false for the FUEL reason, not the bridging reason -- no
premise repairs it).

NEXT: `P6` (ii) is DONE. The still-owed follow-on is part (iv) -- widening
`FullScope.lean::W4Fragment.ttuStarFree` to `TtuStarWide.lean::TtuStarFreeW`. Its
precondition ("until part (ii) composes `ensureInBridges` into the rule-routed write path")
is now MET and `CORRESPONDENCE.md` sec 7 records that; the field itself is UNTOUCHED and the
2026-08-10 refutation no longer blocks it.
