# PROOF_STATUS.md — the append-only session ledger

**A fresh session reads `formal/HANDOFF.md` FIRST** (the compact entry point: state of
the world, the next task, house rules). This file is the append-only ledger backing it
— newest entry first; read only the TOP entry for resume-point detail, deeper entries
on demand. Before ending ANY session: add a session entry at the top here AND refresh
HANDOFF.md's "The next task".

---

## Session 2026-07-19a (#4 remove legs — Leg R4 part 1: the UNTAINTED confluence arm)

Fourth Lean-editing leg of #4, first increment. ADDITIVE — one new file `RemoveConfluence.lean`
+ a 1-line aggregator import in `ZanzibarProofs.lean`; inducts on / reuses the EXISTING
`ReachedByW3d2E` chain + R3, no constructor/inductive/existing-def touched. verify.sh green:
lean 415/415 sorries=0 (Audit untouched), conf-heavy 76, conf-rest 220 (conf 296, 0 skip).

- **Attack-first CONFIRMED the full R4 confluence (house rule 2; `#eval` vs real `check`/`sem`,
  scratch deleted).** Schema `viewer := editor or manager` (rc≥2 untainted survival) +
  `r := a but not b` (derived exclusion); built the add-only chain over a 5-tuple store, then for
  EACH of five removed tuples computed `check (runCascade2 … (removeLoggedRules σ t)) q` vs
  `sem S (T.erase t) q` across the full query grid — **ZERO mismatch**, incl. the rc=2 survival
  case (remove `(alice,manager)`, viewer edge survives via `editor`) and the derived-exclusion
  flips (`(alice,a)` flips `r@alice`, `(bob,b)` flips `r@bob`). The confluence is TRUE; the leg
  is the proof, not a discovery.
- **Landed the UNTAINTED arm** (`RemoveConfluence.lean`): the retraction count-shrink law
  `count_removeLoggedOne`/`count_removeLoggedRules` (exact dual of R3's
  `count_foldl_writeDirect`/`count_writeLoggedRules`; UNCONDITIONAL — Nat subtraction floors the
  absent-copy case, no "enough copies" guard needed for the arithmetic); the store-erase split
  `untOccCount_erase` (`t ∈ T ⇒ untOccCount S T = untOccCount S (T.erase t) + t-closure-occ`, via
  `List.perm_cons_erase` + `Perm.flatMap_right`/`.map`/`.count_eq`); the pre-drain confluence
  `removeLoggedRules_untOccCount` (untainted `(a,b)`'s post-retraction multiplicity = its occ
  count over `T.erase t` — R3 supplies the `≥` making the Nat sub exact); the drained form
  `drain_removeLoggedRules_untOccCount` (the two-round diffing cascade is untainted-count-inert,
  R3's `count_runCascade2_of_ne` + `enumJobs2At_Rnode_ne`); and the membership corollary
  `mem_drain_removeLoggedRules_untainted` (`count>0 ↔ mem`). So a drained post-remove UNTAINTED
  edge's multiplicity is BIT-IDENTICAL to R3 on a fresh add-only rebuild over `T.erase t` — hence
  membership matches, the design's untainted-side confluence target.
- **No kill this increment** (the arithmetic is exactly as the R3 kill reshaped it: untainted =
  occurrence-count story, derived = membership story deferred).

**Gate:** verify.sh lean 415/415 sorries=0, conf-heavy 76, conf-rest 220 (all PASSED, cap-safe
phased). Additive Lean (new module + import), driver (`Exec.lean`) untouched and `RemoveConfluence`
is outside zcli's call graph ⇒ conf ran green as expected. `pytest tests/` (561+32) stands (no
Python touched). Committed + pushed.

**RESUME #4: Leg R4 part 2 — the DERIVED membership arm + the confluence assembly.** The untainted
edges now provably match the rebuild at multiplicity level. Remaining for R4: (i) the DERIVED-edge
membership arm — after remove+drain, a derived pair's presence matches the rebuild via the
filter-all `removeEdgePair` zeroing + the two-round re-settlement (reuse the 12f re-settlement;
NOT a count bound — the R3 derived-arm KILL); (ii) the residue equality (the cascade recomputes
residue wholesale — `reconcileResidueKey`); (iii) fold (i)+(ii)+untainted into a membership-level
read-equivalence to the rebuild (define `ReadEq` — schema/nodes/residue eq + edge-SET membership
eq — and prove `check`/`reachB` congruent under it, since full `EvalEq`'s LIST-edge equality is
FALSE across the differing fold orders). Then R5 (the `remove` constructor + discharge Group A via
ReadEq-transport + retire `toC`). Design file Target #4; the untainted arm is the template.

---

## Session 2026-07-18i (#4 remove legs — Leg R3: untainted occurrence-count invariant + a KILL of the derived arm)

Third (and hardest) Lean-editing leg of #4. ADDITIVE — one new file `RemoveOccCount.lean` +
a 3-line aggregator import in `ZanzibarProofs.lean`; inducts on the EXISTING `ReachedByW3d2E`
chain, no constructor/inductive touched. verify.sh lean 415/415 sorries=0 (Audit untouched).

- **Landed the FULL UNTAINTED arm:** `reachedByW3d2E_untOccCount` — over every `ReachedByW3d2E`
  state, an untainted `(a,b)` has `σ.edges.count (a,b) = untOccCount S T a b` where
  `untOccCount := ((T.flatMap (rewriteClosure S)).map edgeOfTuple).count (a,b)`. The ref-count
  made concrete (`edges` is a multiset ⇒ `List.count` == `direct_edge_count`, `core.py:686-704`).
  Supporting/R4-reusable: `count_foldl_writeDirect` (the count collapses to occurrence-count off
  the write ctor's own `FoldAdmits` hyp — the "admitEdge never rejects a non-self rewrite edge"
  question DISSOLVED, no acyclicity argument needed), `count_writeLoggedRules`, and the
  cascade-preserves-untainted-count stack (`count_reconcileKeyDR_of_ne` →`…StarsKeyDR…`
  →`…applyLoggedR…` →`…reconcileJobsLR…` →`count_runCascade2_of_ne`; every enumerated job at a
  DERIVED R-node via `enumJobs2At_keyFacts` ⇒ untainted `(a,b)` differs by `objNode_type/_pred`).
- **★ KILL (house rule 2) — the design's DERIVED arm `count ∈ {0,1}` is MODEL-FALSE.** `#eval`
  `viewer := a but not b` (write alice@a→cascade→write bob@a→cascade): `count(alice→viewer)`
  = 1 then 4. The diffing pass `reconcileKeyD` writes on `checkFn ∧ ¬covered` and does NOT
  probe `¬has_edge` like Python (`processor.py:359-367`) — it STACKS derived duplicates (the
  documented `ReconcileDiff` header decision, compensated by filter-all `removeEdgePair`). So
  the faithful derived-side property is MEMBERSHIP (filter-all zeroing), NOT a count bound —
  R4's derived side is reshaped accordingly.
- **Faithfulness nuance (benign):** Lean `rewriteClosure` doesn't dedupe (Python `RuleSet.apply`
  does) ⇒ reconvergent-diamond over-count (model 2 vs Python `direct_edge_count` 1);
  read-invisible + remove-consistent (same closure folded on remove) ⇒ doesn't affect the
  membership-level R4/R5 target; extends the `RulesWrite.lean:100` "duplicates harmless" note
  to the remove path. The theorem is a MODEL-ref-count characterization, not a Python-count claim.

**Gate:** verify.sh lean 415/415 sorries=0. Additive Lean (new module + import), driver
(`Exec.lean`) untouched and the new module is outside zcli's call graph ⇒ conf byte-identical
(conf-heavy 76 + conf-rest 220 last green at R1; leaned on, gate-runbook §2). `pytest tests/`
(561+32) stands. Committed + pushed.

**RESUME #4: Leg R4** — the confluence `EvalEq(removeLoggedRules…|>drain, rebuild(T.erase t))`
at membership level: untainted side fed by `untOccCount` (`count>0 ↔ mem`, erase-one
decrements); DERIVED side via the membership story (filter-all `removeEdgePair` zeroing + the
diffing re-settle), NOT the killed `∈{0,1}` bound. Then R5 (constructor + discharge Group A +
retire `toC`). Design file Target #4.

---

## Session 2026-07-18h (#4 remove legs — Leg R2 landed: retraction substrate + the R5 ripple map)

Second Lean-editing leg of #4. ADDITIVE (140 ins, 0 del across `Cascade.lean` +112 /
`CascadeInv.lean` +28), sorry-free, verify.sh lean 415/415 (Audit.lean untouched). Landed the
STANDALONE retraction substrate — NOT the constructor (see the architectural finding).

- `GraphState.removeLoggedOne` (guarded erase-one + retraction `pushDelta` iff a copy was
  present — retract mirror of `writeLoggedOne`), `removeLoggedRules S t` (fold over the SAME
  `rewriteClosure S t` the write path uses), `RemoveAdmits σ T t := t ∈ T` + schema/nodes/
  watermark `@[simp]` mirrors; `structInv_removeLoggedOne/_Rules` (fold `structInv_removeEdgeOne`).
  Python mirrors cited: `apply.py:48-68` (ADD+REMOVE share `ruleset.apply`), `core.py:686-704`
  (`_remove_edge_locked` → `-1`), `core.py:278` (`_emit("REMOVED")`), `source.py:104-112`.
- **Delta-faithfulness finding:** `removeLoggedRules` mirrors the UNTAINTED routed retraction
  (dual of `writeLoggedRules`), NOT the processor's derived diffing removal (that's already
  modeled by `removeEdgePair`); per-actual-erase emission is the exact dual of the write's
  per-admitted-add — mirror-symmetric, no asymmetry. No kill.

**★ ARCHITECTURAL FINDING (reshapes the leg plan — green-gate driven).** Adding the `remove`
CONSTRUCTOR to `ReachedByW3d2E` is NOT additive: Lean's total-match requirement breaks every
downstream induction until each remove case is discharged, and those need R4. So per house
rule 3 the constructor moves to a FINAL leg **R5**, and the standalone substrate (R2) +
occurrence-count invariant (R3) + confluence (R4) all land additively-green FIRST. R2 mapped
the full R5 ripple surface:
- **Group A** (4 direct inductions — `reachedByW3d2E_edgeHyg1`/`_structInv`/`_residueHygienic`/
  `_residueDeclared`): all membership-read conclusions ⇒ EvalEq-invariant ⇒ remove case rides
  R4→rebuild.
- **★ The one obstruction:** `reachedByW3d2E_toC` (`CascadeStrataAssemble.lean:342`) has codomain
  `ReachedByW3d2C` — an OPERATIONAL stateful inductive (pins outbox/watermark/edge multiplicity),
  NOT membership-read ⇒ NOT EvalEq-invariant ⇒ R4 can't discharge it. **Fix (iii):** retire
  `toC` from the remove path (its 3 callers restructure to induct on `ReachedByW3d2E` directly).
- **Group B** rides automatically; **Group C** (Exec.lean driver) is optional additive.

**Gate:** verify.sh lean 415/415 sorries=0. Change is additive Lean, driver (`Exec.lean`)
UNTOUCHED and the new defs are outside zcli's call graph ⇒ zcli behavior byte-identical ⇒ conf
unaffected (conf-heavy 76 + conf-rest 220 last green at R1; leaned on per gate-runbook §2's
driver-untouched reasoning). `pytest tests/` (561+32) stands (no Python touched). Committed + pushed.

**RESUME #4: Leg R3** — the occurrence-count invariant over `removeLoggedRules` (untainted edge
`count = Σ` admitted occurrences; derived ∈ {0,1} by I5). Additive ⇒ green. Then R4 (confluence
EvalEq), then R5 (constructor + discharge Group A + retire `toC`). Design file Target #4.

---

## Session 2026-07-18g (#4 remove legs — Leg R1 landed: erase-one primitive + structInv)

First Lean-editing leg of #4 (Route 1). ADDITIVE (96 insertions, 0 deletions across
`ReconcileDiff.lean` + `CascadeInv.lean`), sorry-free, verify.sh lean 415/415 (Audit.lean
untouched — R1 is infrastructure, not a top-level key theorem).

- `GraphState.removeEdgeOne σ a b := { σ with edges := σ.edges.erase (a,b) }` — the faithful
  erase-ONE-copy op (mirror of Python `_add_direct_edge_unsafe(...,-1)`, `core.py:704`/
  `686-704`; header comment records the KILL: filter-all `removeEdgePair` is unsound at
  rc≥2, valid only in the diffing pass where I5 ⇒ rc≡1). `edges` is already a multiset ⇒ no
  new field. + 6 `@[simp]` accessors.
- Membership/count lemmas: `removeEdgeOne_edges_subset` (`List.mem_of_mem_erase`),
  `mem_removeEdgeOne_edges`, `mem_removeEdgeOne_edges_of_ne` (`List.mem_erase_of_ne`,
  pointwise read-inertness at other pairs), `count_removeEdgeOne_self`
  (`List.count_erase_self`, the concrete `count-1` decrement — seeds R3's occurrence-count
  invariant), `count_removeEdgeOne_of_ne`, `edgesClosed_removeEdgeOne`.
- `structInv_removeEdgeOne` (`CascadeInv.lean`) — erase-one preserves `StructInv`;
  line-for-line analog of `structInv_removeEdgePair` (schema/nodes fixed; endpoint closure
  via `edgesClosed_removeEdgeOne`; acyclicity via `NReaches.mono_subset` on the erase subset
  — the subset argument doesn't care whether one copy or all are dropped).
- No kill this leg (erase-first-occurrence == decrement-one confirmed, stated+proved not
  asserted). Only adjustment: dropped explicit args to the implicit-arg Mathlib `count_erase`
  lemmas. `removeLoggedRules`/deltas DEFERRED to R2.

**Gate:** verify.sh lean 415/415 sorries=0; conf-heavy 76 + conf-rest 220 re-run green
(zcli rebuilt; conformance byte-identical — the additive defs aren't wired into the driver).
`pytest tests/` (561+32) stands (no Python touched this session since). Committed + pushed.

**RESUME #4: Leg R2** — land `removeLoggedRules`/`removeLoggedOne` (the deferred rewrite-
closure fold + retraction-delta emission) + the `remove` constructor on `ReachedByW3d2E` +
`RemoveAdmits` + thread hyps through `reachedByW3d2E_toC`. Then R3 (the hard occurrence-count
invariant), R4 (confluence). Design file Target #4.

---

## Session 2026-07-18f (#4 remove legs — RECON + attack-first probe; Route 1 GO with a KILL)

Target #3 complete ⇒ moved to #4 (model chain-level REMOVE in Lean). Read-only recon + the
five design probes (against the real Python backends / model). NO Lean edited (probe scratch
deleted). Verdict: **Route 1 GO** — but the design's step 2 was a FALSE statement:

- **KILL (house rule 2):** "chain-level `removeLoggedRules` = fold `removeEdgePair`
  (filter-ALL-copies)" is UNSOUND in-fragment. `#eval` refutation: untainted
  `viewer = editor or manager`, alice granted both ⇒ `alice → viewer:doc:1` has
  `direct_edge_count = 2`; removing `(alice,editor)` decrements rc 2→1, edge SURVIVES,
  `check` True (via manager) == `sem` == rebuild. Filter-all would drop it → divergence.
  Reachable in `W4Fragment`/`twoStrata`. Faithful op = **`List.erase` (decrement ONE)**,
  mirror of `_add_direct_edge_unsafe(...,-1)` (`core.py:686-704`). `removeEdgePair` valid
  only where I5 ⇒ rc≡1 (the diffing pass), never the chain-level untainted fold.
- **Pivotal positive finding — NO `GraphState` ripple.** `GraphState.edges :
  List (NodeKey × NodeKey)` is ALREADY a multiset (`addEdge` prepends unconditionally
  `State.lean:742`; `admitEdge` only checks `a≠b ∧ ¬reach b a` `Write.lean:69`), multiplicity
  == Python `direct_edge_count`; reads test membership only ⇒ multiset-for-writes /
  set-for-reads. `List.erase` is the exact mirror with NO new field. Probes 2–6 clean
  (remove-readd symbolic-state identical; node-GC already modeled-away, extractor P5 doesn't
  compare nodes; cross-stratum retraction `check==sem`; I6 residue diff clean; non-present
  remove raises ⇒ `RemoveAdmits` faithful).

Corrected leg breakdown recorded in the design file (`optional-widening-2026-07.md` Target
#4): **R1** erase-one primitive + `structInv_removeEdgeOne` (mechanical) → **R2** `remove`
constructor + `RemoveAdmits` + `reachedByW3d2E_toC` threading → **R3** the occurrence-count
invariant (untainted `count = Σ` admitted occurrences; derived ∈ {0,1} by I5 — THE HARDEST
SUB-LEMMA, the whole content) → **R4** confluence `EvalEq(remove+drain, rebuild)` at
membership level ⇒ zero re-proof of T2a/T2b/T3/T6. Route 2 (direct preservation) is the
fallback if R3 is intractable (strictly more work). No gate run (docs-only; Lean untouched).

**RESUME #4: start Leg R1** (use `List.erase`, NOT `removeEdgePair`).

---

## Session 2026-07-18e (#3 state/enum widening — increment (d) state gate over enumerated stores — TARGET #3 COMPLETE)

Fourth and final #3 increment — the state-level gate. New file
`formal/conformance/test_conformance_enum_state.py`: for a deterministic stride-4 SAMPLE of
the enumerated stores (`stores[::4]`, spread across every store size since the list is
size-ordered), compare the Lean graph model's canonical final state (zcli `"graph-state"`,
the `graphRun` fold) vs the real Python graph index's extracted `EdgeV4`/`ResidueV1` state
under `extractor.py`'s P1–P6 projections UNCHANGED (`lean_graph_state`/`python_graph_state`/
`diff_states` reused, nothing re-implemented or widened).

- **All six enum shapes state-gated, none excluded** — all in `GRAPH_FRAGMENT`; zero Lean
  admission/drain (rc 2/3) errors on any sampled store, so graph-state admits+drains every
  one (incl. `two_stratum_cascade` 2-stratum, wildcard/TTU star+residue state).
- **Sampling (documented, no silent caps):** 257 of 1021 stores (~25%) state-checked; the
  other ~75% stay answer-pinned by increment (a). Per-shape sample sizes ASSERTED
  (`_STATE_SAMPLE`, ceil(N/4)) so the fraction can't silently drift; fraction table in the
  module docstring. Measured ~180 ms/store (zcli graph-state spawn + SQL build/cascade/
  extraction); +47s.
- **Attack-first (the point):** state-level enumeration is EXACTLY the class of run that
  originally found the P6 leaf-family (`CORRESPONDENCE.md` §7) and 2026-07-17 stale-fanout
  state divergences. Result: **state match on every sampled store under P1–P6 — ZERO
  mismatches, zero Lean errors** (257 sampled + 207 more during the measurement passes = 464
  distinct comparisons). No adjudication event.

**Gate:** new test 6 passed 0 skip 47.8s; conf-rest 220 passed 0 skip 8:34 (within cap,
~85s below the 600s command cap). +6 params ⇒ conf 290→296, 0 skip. Change is
`formal/conformance`-only (one new file), so `pytest tests/` (561+32) and `verify.sh lean`
(415/415) stand from this session; conf-heavy 76 re-run green. Committed + pushed.

**#3 (state/enum bounds widening) is COMPLETE** — all of (c) userset+TTU shapes, (a) real
graph index in the enum, (b) per-shape K=4, (d) sampled state gate landed, all green, no
divergence surfaced. **Next per the interleave plan: #4 remove legs (Route 1 confluence,
Lean — probe the ref-count risk FIRST), then back to #1 Direct-arm leg 4+ / TTU half, #2
strata.** Design briefs: `history/optional-widening-2026-07.md` Targets #4/#1/#2.

---

## Session 2026-07-18d (#3 state/enum widening — increment (b) K=4 per-shape)

Third green increment of #3. Widened the enum (`formal/conformance/test_conformance_enum.py`)
from uniform K=3 to a PER-SHAPE K. Because increment (a) put the real graph index (SQL build
+ cascade per store) inside the enum, a naive all-shapes K=4 (1726 stores) blows the ~10-min
conf-rest command cap — so K is per-shape (lever 1, measured, no silent caps):
- K=4: `boolean_exclusion` (163), `boolean_intersection` (163), `boolean_star_exclusion`
  (57), `ttu` (163).
- K=3 CAPPED (the two dominators): `two_stratum_cascade` (299 — 12-tuple space, the single
  largest leg) and `wildcard_group_member` (176 — 10-tuple, next-largest). Measured: only
  `two_stratum` capped → enum ~7.6 min / conf-rest ~9.2 min (too tight); both capped → enum
  ~6.4 min / conf-rest ~7.9 min (≥2 min margin). Total 1021 stores. `_SHAPES` now
  `(space, K, count)`, all three asserted; caps documented in the docstring.

**Attack-first:** graph `check` == `sem` on every in-fragment enumerated store at K=4 (incl.
`wildcard` at K=4 during the measurement pass), NO `ValueError`, NO divergence. Clean.

**Gate:** enum file 6:22 standalone; conf-rest 214 passed 0 skip 7:51 (within cap, ≥2 min
margin). `git diff` scope = the one enum file, so `pytest tests/` (561+32) and `verify.sh
lean` (415/415) stand from this session; conf-heavy 76 re-run green. No new params ⇒ conf
still 290, 0 skip. Committed + pushed.

**Resume #3:** only (d) left — the state gate over enumerated stores (a `graph-state` zcli
run per store; highest cost, reuse `extractor.py` P1–P6, MUST sample/shard to fit the cap).
Design file Target #3.

---

## Session 2026-07-18c (#3 state/enum widening — increment (a) real graph index inside the enum)

Second green increment of #3. Added the REAL graph index (`WildcardIndex`+`DeltaProcessor`,
I5 leaf-routing + same-txn cascade) to the exhaustive enum
(`formal/conformance/test_conformance_enum.py`) at ANSWER level, `formal/conformance/`-only
(one file). All six enum shapes are in `GRAPH_FRAGMENT`, so ALL get the graph leg
(`run_graph = name in GRAPH_FRAGMENT`; none skipped). New `_graph_query_filter` mirrors
`test_conformance_graph._graph_queries_for` (concrete objects, star subjects bare); per
store, `graphindex_answers` over the filtered grid is asserted == spec (== the already-
agreed oracle/set-engine answer). No new zcli call (answer-level pin against `sem`).

**Attack-first (the point of this increment).** Exhaustively driving the real graph over
ALL sub-stores is the class of run that historically FOUND the P6 leaf-family and
2026-07-17 stale-fanout divergences. Result this run: **graph `check` == `sem` on EVERY
in-fragment enumerated store (796 stores × the graph query grid, all six shapes), NO
rejected-write `ValueError`, NO divergence.** No adjudication event — clean pass. (Kept for
future runs at wider bounds where a divergence could still appear.)

**Gate:** enum file ~5 min standalone (conf-rest); no shapes/queries dropped (no silent
cap). No new test params (the graph leg rides inside the existing 6 enum tests) ⇒ conf
count stays 290, 0 skip. `git diff` scope = the one enum file only, so `pytest tests/`
(561+32, this session) and `verify.sh lean` (415/415, this session) are provably
unaffected and stand; conf-heavy 76 + conf-rest 214 re-run green. Committed + pushed.

**Resume #3:** (b) k=4 (`_K=4` + re-assert counts, ~2.23× blow-up; shard `two_stratum_
cascade` or cap it at k=3 — does NOT fit alongside the graph leg in one phase, ~10 min),
then (d) state gate over enumerated stores (sample/shard). Design file Target #3.

---

## Session 2026-07-18b (#3 state/enum widening — increment (c) userset + TTU enum shapes landed)

Interleave plan continues: banking the tractable #3 (state/enum) increments before the
deep grinds. First green increment of the state/enum widening — **#3(c)**: widen the
exhaustive small-scope enumeration (`formal/conformance/test_conformance_enum.py`) with a
userset shape and a TTU shape (spec×oracle×set-engine pointwise, exhaustive at K=3; NO
graph leg yet — that is increment (a)). Python-only, one file touched.

- **Attack-first finding of record (not a failure — house rule 2).** The design brief's
  suggested `group_userset` schema (`member: [user, group#member]`, self-referential) is
  DELIBERATELY NOT used: at K=3, 132 of its 299 stores are admission-INVALID for the set
  engine (its userset-membership cycle guard, `engine.py:770`, rejects `g1#member member
  g1` and the g1↔g2 2-cycle), which breaks the enum's "exhaustive over admission-valid
  writes" premise. On the 167 acyclic stores spec/oracle/set engine agree exactly — so
  this is an admission-DOMAIN difference, not a check-semantics divergence. Recorded in the
  test module docstring. Used the existing acyclic `wildcard_group_member`
  (`viewer: [group#member]` + public `user:*`, already in SCHEMAS/GRAPH_FRAGMENT) for the
  userset branch instead — same userset-subject read path, no cycle problem, no corpus
  change.
- **Landed:** `_POOL` +`group`/`folder`; `_SHAPES` +`wildcard_group_member` (10-tuple
  space, 176 stores) +`ttu` (`viewer: viewer from parent`, 8-tuple space, 93 stores) with
  empirically-observed asserted counts; docstring updated (four→six shapes, 527→796
  stores, the finding, runtime note). The four pre-existing shapes' asserted counts
  (8/93, 8/93, 12/299, 6/42) are unperturbed by the pool additions (their restriction
  types are only user/doc) — verified green.
- **Spec == oracle == set engine on every enumerated store** for both wired shapes (0
  divergences, exhaustive at K=3). The TTU shape reaches the tupleset→userset rewrite read
  branch the four boolean shapes never touched.

**Gate GREEN (full, since state/enum touches conformance):** `pytest tests/` split 561+32;
`verify.sh lean` PASSED (audit 415/415, sorries=0); `conf-heavy` 76; `conf-rest` 214
(76+214 = 290, +2 new enum params, 0 skips). Committed + pushed.

**Resume #3:** next increments in the recommended order — **(a)** graph-in-enum at answer
level (reuse `graphindex_answers`, MUST copy the `_graph_queries_for` scope filter from
`test_conformance_graph.py:47-57`, confirm no store trips a rejected-write `ValueError`),
then **(b)** k=4 (re-assert counts; shard `two_stratum_cascade` to fit cap), then **(d)**
state gate over enumerated stores (sample/shard; reuse `extractor.py` P1–P6). Then #4
remove, then back to #1 Direct-arm leg 4+ and #2 strata. Full brief:
`history/optional-widening-2026-07.md` Target #3.

---

## Session 2026-07-18 (OPTIONAL widening arc OPENED — 4 targets scoped; #1 Leaf/Direct-arm legs 1–3 landed)

Opened the optional assurance-widening arc (`FINAL_REVIEW.md §4`). All four targets
recon'd; durable design + resume state in `history/optional-widening-2026-07.md`
(read it to resume ANY target). Orchestrated via subagents (recon Explore → attack-first
`#eval` probe → sequential Opus implementation legs, each ending lake-green, committed
after an orchestrator diff spot-check verifying no top-level statement was weakened).

**#1 Leaf fragment widening (Direct arm) — legs 1–3, all additive/green/axiom-clean:**
- Attack-first ground truth (no live Python divergence): tainting needs an excl/inter
  root or a ref to an already-derived relation (plain `or` compiles untainted); a Direct
  arm → `PClosureLeaf(storage=True)` `<rel>.<index>`, raw writes admission-accepted onto
  it (I5 kept); Python has no 2-stratum cap.
- **Leg 1 `98773d3`** — read-half workhorse `evalE_computedOrDirect` (+ `ComputedOrDirect`
  / `DirectArmsBare` / bare-Direct-leaf lemmas). Refuted: varying-subject congruence is
  FALSE for `.direct` (⇒ subject/store/rel shared, query free).
- **Leg 2 `0dd8d7b`** — write-half admission `StoreValidRulesD`/`exprDirectsAll` (I5
  partition) + reach-collapse `reachedByW3a_*_d` + the diffing retraction CRUX
  `reconcileKeyD_edge_char_cd`/`reconcileKeyD_retracts_excluded` (attack-`#eval`-confirmed
  the diffing pass retracts the stale stored-base over-grant edge for an excluded subject).
- **Leg 3 `8a9bee1`** — base-equation WALL characterized. Attack-first: widened
  `graphRec_base_eq_d` is FALSE without a `NoStoreSubjectR` hyp (userset-over-derived flow
  → graph=true/sem=false), TRUE with it (faithful via `hterm`). Landed
  `storeValidRules_untaintedFilter`. Refinement: the base state's derived-key seed edge is
  a harmless dead-end (item 1 = dead-end/reach-invariance gated by `NoStoreSubjectR`, not
  leg-2's drained retraction).

**Resume:** Direct-arm leg 4 = the wall (3 new lemmas A dead-end-seed / B untainted-reach-
invariance / C sem-store-restriction; see the design file + `8a9bee1` message). Then leg 5
(consumers + widen `W4Fragment` + `W4WitnessDirect` + conformance), then the TTU/userset
half. Interleave plan (2026-07-18): bank #3 (state/enum, mostly Python) + #4 (remove, Route
1 confluence) next, then return to the deep #1 leg-4+/TTU + #2 strata.

Gate GREEN at each leg: `verify.sh lean` PASSED (lake 1082 jobs, sorries=0, axiom audit
415/415 clean). Each leg Lean-only additive ⇒ pytest/conformance provably unaffected.

---

## Session 2026-07-17 (rootB fragment widening — union-/computed-rooted derived defs now in scope; `RootBoolean` deleted, `schemaRewrites` taint-filtered, a model-faithfulness STATE fix, witness + corpus widening)

The last standing SHAPE gap of `W4Fragment` was `rootB`: derived defs had to be
`inter`/`excl`-ROOTED, even though Python taints through `union`/`computed` roots
too. Closed it — the derived-def root operator is now UNRESTRICTED (the shape
condition is `ComputedOnly` alone), so union-rooted (`approver := viewer or
admin`) and computed-rooted (`approver := viewer`) derived defs are inside the
proved scope. Three legs (commits `397f975`, `c3d3113`, this leg).

**Attack-first (the finding of record).** Before widening, a probe drove
union-rooted derived schemas through the Lean graph model vs the Python graph
backend. At CHECK level: no divergence (as the 12k probe had suggested). But at
STATE level, with the fanout UNFILTERED (`schemaRewrites S := S.defs.flatMap …`):
a union-rooted derived def with a USERSET-subject stored tuple matching an
untainted arm (`group:eng#member → admin` under `approver := viewer or admin`)
leaked a stale fanout edge `group:eng#member → approver` into the DRAINED Lean
state — a real Lean-model-vs-Python state divergence (Python routes derived keys
OFF the fanout entirely). So the widening was NOT purely a probe-faithful
"proof-only" gap at state level; it needed a model fix.

**What landed.**
* **Leg 1 (`397f975`) — the taint filter.** `schemaRewrites` (`RulesWrite.lean:81`)
  now filters `S.defs.filter (fun d => !(isDerived S d.1))` before the `exprArms`
  flatMap — the faithful mirror of `compile_ruleset:1027-1044` (`if key not in
  tainted: fan out; else: derived plan`). `isDerived` (the taint fixpoint) IS the
  compiler's `tainted` set. Restored set/graph accept-reject parity and killed the
  stale userset-sourced fanout edge.
* **Leg 2 (`c3d3113`) — `RootBoolean` DELETED.** The `W4Fragment.rootB` field and
  the `RootBoolean` predicate are gone; the intermediate lemmas that carried
  `hRootB`/`RootBoolean` leaf conditions were re-based onto `isDerived`/`ComputedOnly`.
  `RootBoolean` no longer appears anywhere in `ZanzibarProofs/` (verified by grep —
  only a prose mention survives, in the new witness docstring).
* **Leg 3 (this session) — the witness + the corpus widening.**
  - `FullScope.lean`: a SECOND non-vacuity witness `W4WitnessUnion` (`Sy`/`Ty` =
    the corpus `taint_union_over_boolean` in compiled form — a union-ROOTED derived
    `approver` over the boolean `viewer := base ∖ blocked`, bare-star base). Same
    three theorems as `W4Witness` (`accepts : GraphAdmission`, `fragment :
    W4Fragment`, `within_scope : GraphAccepts`), decide-style. Because the taint
    filter routes the derived `approver` off the fanout, `schemaRewrites Sy = []`,
    so `ttuStarFree`/`term`/`ranked`/`matchDecl` mirror the original witness; the
    contentful new work is `computedOnly`/`twoStrata` over the two-stratum
    `viewer`→`approver` chain and `storeValid` over the bare-star base tuple.
    Audited (`Audit.lean`, +3 `#print axioms`); standard axioms only.
  - `formal/conformance/corpus.py`: `taint_union_over_boolean` MOVED into
    `GRAPH_FRAGMENT`; the exclusion comment rewritten (rootB gap CLOSED; only the
    object-wildcard corpus stays excluded, `bareStar`). Two NEW corpora, in both
    `SCHEMAS` and `GRAPH_FRAGMENT`: `taint_union_userset_arm` — THE regression pin
    for the stale-fanout STATE divergence (the `group:eng#member → admin` userset
    arm under a union root; the state gate now pins the stale `→ approver` edge's
    ABSENCE); `taint_computed_root_over_boolean` — a computed-ROOT derived def
    (`approver := viewer`), pinning that computed roots taint too.

**Evidence / gate.** `verify.sh lean` PASSED (0 sorries; axiom audit 412 → **415**
observed == expected, standard axioms only — the 3 new witness theorems). Conformance
263 → **288**, 0 skips: `conf-heavy` 68 → **76**, `conf-rest` 195 → **212** (each
phase ~3 min wall, well under the 8.5-min cap). Full `formal/conformance/` 288 passed.
No Python behavior changed (no `docs/spec-deviations.md` entry) — the taint filter is a
model-side faithfulness fix; the compiler already routed derived keys off the fanout.
Docs synced: `FINAL_REVIEW.md` §3/§4, `CORRESPONDENCE.md` (schemaRewrites row + §7
dated note), `ARCHITECTURE.md`, `HANDOFF.md` (formal + root), `ROADMAP.md` (W4 honest
gaps), `CLAUDE.md`/`gate-runbook.md` counts, this entry.

## Session 2026-07-13 (X4 adjudication ANCHORED to `sem` — three spec-side TTU userset-subject conformance corpora; harness + docs only, NO Lean changes, NO claim widening)

The 2026-07-13 X4 fix (previous entry) followed the ORACLE where the boolean
spec is SILENT on userset-shaped subjects flowing through a TTU's stored
tupleset parents. Gap noticed this session: the formal trust root `sem` had
**never been consulted on those exact shapes** — `corpus.py` carried no corpus
that put a from-chain / cross-object userset subject over a TTU, so the
adjudication rested on the oracle alone, unanchored to the Lean spec the oracle
stands in for. Closed it.

**What landed** (`formal/conformance/`):
* `corpus.py` — new module-level `TTU_USERSET_SCHEMAS` (3 corpora), separate
  from `SCHEMAS`: (a) `ttu_fromchain` — from-chain userset through an UNTAINTED
  TTU (`inherited: viewer from parent`, `doc:d1#viewer` ∈ `inherited@doc:d2`);
  (b) `ttu_fromchain_group` — the cross-object membership LIFT (`group:g1#member`
  an editor of `doc:d2`, member of `inherited@doc:d1` via parent); (c)
  `derived_ttu_fromchain` — from-chain userset through a TTU over a DERIVED
  (boolean) target (`viewer: editor but not banned`), the genuinely derived-TTU
  case central to X4 (cf. `demorgans_reverse.fga`), minimized.
* `test_conformance_spec.py` — the three FULL-SCOPE comparisons (spec `sem` /
  oracle / set engine) now parametrize over `{**SCHEMAS, **TTU_USERSET_SCHEMAS}`.
  T1 places no fragment restriction on the set engine and `sem`/oracle are the
  reference for every stratifiable schema, so these comparisons legitimately
  carry the new shapes.

**Scope honesty.** `TTU_USERSET_SCHEMAS` is DELIBERATELY separate from `SCHEMAS`
(and thus absent from `GRAPH_FRAGMENT`): the shapes are outside `W4Fragment`
(`computedOnly` bans `ttu` leaves in derived defs; `PDerivedTTU` plan leaves are
a documented proof gap), so `test_conformance_graph` / `_state` / `_random` /
`_remove` (which iterate `SCHEMAS` and drive the graph index) must NOT carry
them. Only the spec-side comparisons do. No theorem, gate, bound, or fragment
widened; the Lean tree is untouched.

**Attack-first.** Before adding, a scratch probe ran all three shapes through
oracle + set engine + zcli `sem`: on every from-chain / cross-object userset
query the shape reproduces (oracle == set engine == True, matching the oracle
the graph was fixed toward) AND `sem` agrees — spec == oracle == set engine on
ALL queries, zero disagreement. The good outcome: the adjudication is anchored,
not contradicted. (Had `sem` disagreed, the fix would have been pinned to the
oracle AGAINST the formal spec — a finding worth surfacing; it did not.) Scratch
deleted after recording.

**Evidence.** `test_conformance_spec.py` 51 → 60 (20 corpora × 3); full
conformance suite 248 → 257, 0 skips; `verify.sh` green (Lean unchanged, 0
sorries, axiom audit unchanged). Docs: HANDOFF status + count + the ranked
optional items annotated; FINAL_REVIEW §1 count + §3 resolved-note anchor;
this entry.

## Session 2026-07-13 (lookup-gate divergences X1–X4 FIXED, Python-side only — repo-side code + docs; NO Lean changes, NO formal-claim widening)

All four pinned divergences from the 2026-07-12n lookup-surface oracle gate
are fixed in the Python backends; Lean is untouched and derived-TTU shapes
remain OUTSIDE `W4Fragment`, so no theorem, scope, or gate widened. The
repo-wide "identical semantics" claim no longer carries a known exception.
One-line mechanisms:

* **X1** (set forward `lookup` dropped TTU-only objects): write-time
  reverse-dependency interning — compile-time `_candidate_reverse_deps`
  tables invert the schema; `_apply_add`/`_apply_remove` intern/release
  symmetrically (reads stay side-effect-free, `rebuild()` replays
  identically), plus intensional star markers; lookup stays linear in
  relevant tuples.
* **X3** (uninterned from-chain userset unrepresentable in
  `expand`/`lookup_reverse`): adjudicated FIXABLE, not representational —
  the same write pass interns `(subject_type, subject_name, target_rel)`
  for stored tupleset tuples; `ttu_expand` already emitted the userset once
  the id existed.
* **X4a** (graph, from-chain): `ttu_check`/`tupleset_ttu_check` gain the
  oracle's from-chain identity rule; reconcile gains step 2a enumerating
  from-chain keys, interning subject nodes only when an outcome must be
  recorded, with I3 bridge maintenance + the new GC lifecycle
  (`_gc_subject_node`, residue-reference-aware `_gc_public_node`,
  full-reconcile of residues referencing GC'd subject nodes).
* **X4b** (graph, cross-object userset lift): `_leaf_concretes` lifts the
  tainted target's residue `upos` members into candidates/audit (they are
  edge-free by D2, invisible to the closure-based audit before).
* **X2** (graph `lookup_reverse`, derived relation, `o_name='*'`):
  short-circuits to the empty result (decision 15), matching `check` and
  the set engine, instead of raising through the reserved-name guard.

**Adjudication:** the boolean spec (§5.3/§6) is SILENT on userset subjects
through derived-TTU stored parents; the oracle was followed — recorded in
the two dated 2026-07-13 `docs/spec-deviations.md` entries (which also
carry a residual THEORETICAL cascade-rounds note: an untainted
subject-wildcard-bridged from-chain target could need extra rounds; no
compilable schema class reaches it, and it fails LOUD via the
cascade-quiescence `InvariantViolation`, never silently wrong).

**Evidence:** in-fragment behavior byte-identical (every new graph path is
gated on `derived-ttu`/`derived-tupleset-ttu` leaf kinds absent from the
`W4Fragment` corpora); the state-level gate (exact edge+residue equality vs
Lean, mode `"graph-state"`) passed UNCHANGED; I1–I13 + I9 green;
`tests/test_lookup_oracle.py` xfails flipped to plain regression pins,
walk-skip escapes removed (properties strengthened), one new
demorgans_reverse regression — **16 passed, 0 xfail**; matrix grids widened
(`_boolean_grid` from-chain subjects + `_from_chain_userset_subjects` on
the De Morgan grid — the P7 gap that hid X4 is closed). formal/ conformance
count unchanged at 214.

Docs: FINAL_REVIEW §3 (open → resolved) + §4(f) done; ARCHITECTURE §5/§6;
HANDOFF status + optional item 4; formal/README "what remains";
`docs/architecture/correctness.md` gap bullet closed; root README
exception sentence replaced with the read-surface gate note; CLAUDE.md
lookup-gate bullet reworded to the standing convention.

## Session 2026-07-12n (three verification gates — remove-path + generated-schema conformance in formal/, the lookup-surface oracle gate in tests/; harness code + docs only, NO theorem changes)

Conformance suite: 140 → **214** tests, 0 skips (verify.sh gates on
0-skips/>0-passes, so it needed no change): 194 differential (120 prior + 34
remove-path + 40 generated-schema) + 20 gate-tooling. No Lean changes; no new
axioms; no sorries.

**(1) Remove-path answer gate** (`formal/conformance/test_conformance_remove.py`,
34 tests — narrows FINAL_REVIEW §4(d)): the REAL `SetEngine` driven through
seeded interleaved add/remove/re-add sequences (all 17 spec-scope corpora ×
5 seeds) == `sem` (zcli) × oracle on the FINAL store — the first answer-level
pin on the Python remove path — plus driven == fresh `rebuild()` at grid AND
id-free state-fingerprint granularity (interner keys/refcounts, population
masks, node_sets/member_of, flow edges), plus an add-all/remove-all/re-add
churn test asserting complete state emptiness mid-cycle. Scope honesty: the
Lean chain stays add-only; the GRAPH-side remove legs remain open; the
fingerprint comparison is Python-internal (driven vs rebuild), never vs Lean.
Attack-first: a deliberate `_apply_remove` early-return was caught 14×; a
deliberate interner mask-scrub skip was caught 34×.

**(2) Generated-schema answer gate**
(`formal/conformance/test_conformance_generated.py`, 40 tests — closes
FINAL_REVIEW's former risk #1, the disjoint pools): a seeded deterministic
re-implementation of the hypothesis `schema_asts` generator (NO hypothesis
dependency, per the formal/ convention; inside formal/conformance/ so
verify.sh gates it fail-closed) feeds generated schemas + stores — shapes
outside the 17 curated corpora — asserting zcli spec == oracle == real
`SetEngine` over the shared grid. Answer-level, spec-side only; the graph
backend stays pinned by the curated corpora. Attack-first: a deliberately
wrong exclusion encode tag was caught on 26/40 cases.

**(3) Lookup-surface oracle gate** (`tests/test_lookup_oracle.py`, repo side —
NOT under verify.sh; 15 tests: 10 pass + 5 strict xfails): composes
`oracle.check` over the candidate universe into brute-force reference lookups
pinning `lookup`/`lookup_reverse`/`expand` on BOTH backends — exact
(two-sided) where the API is exact, one-sided where the API drops information
by design (set `lookup_reverse` drops `neg`, engine.py:738-740). Closes
deviations-log #3's gap (ParityEngine served lookups from one backend,
unasserted). Attack-first: deliberate graph neg-drop and reverse node-drop
both caught; permanent tamper tests keep the checkers honest. **FINDING (the
significant one, X4)**: a CHECK-level graph-vs-set divergence on derived-TTU
userset subjects — truth flowing through a stored tupleset parent answers
False on the graph vs True on oracle + both set engines (from-chain shape and
cross-object `upos` lift shape; also on demorgans_reverse.fga). Adjudication:
OUTSIDE `W4Fragment` (`computedOnly` bans `ttu` leaves in derived defs;
`PDerivedTTU` already a documented gap) and outside the conformance grids'
query surface — theorems untouched, but the repo-wide "identical semantics"
claim now carries a known, pinned exception awaiting a fix. Plus three
narrower lookup-only divergences X1–X3. All pinned as strict xfails,
properties NOT weakened; full shapes in `docs/spec-deviations.md` 2026-07-12.

Docs: FINAL_REVIEW header/§1/§3/§4 (counts 214, the two new gate
descriptions, disjoint-pools narrowed, remove narrowed, the X4 known-open-
divergence note); ARCHITECTURE §5/§6 to match; HANDOFF rule 3 + status +
optional list; formal/README counts + gate list; SEMANTICS §10 (third pass);
`docs/spec-deviations.md` new entry; root CLAUDE.md testing-conventions
bullet; root README honest-exception sentence.

## Session 2026-07-12m (Phase 6 extras (a)+(b) — state-level graph conformance + exhaustive small-scope enumeration; driver/harness code only, NO theorem changes)

The two explicitly-unearned FINAL_REVIEW §1 clauses are now EARNED. Conformance
suite: 101 → **120** tests, 0 skips (verify.sh auto-collects; its summary gates
unchanged). `lake build zcli` clean; no sorries introduced; no new axioms; no
new theorems (the dump code is driver-level, like Cli.lean's existing modes).

**(a) State-level graph conformance** (`FINAL_REVIEW` §4(a), the §7
"state-level equality" clause):
* zcli mode **`"graph-state"`** (`Cli.lean`): the SAME `graphRun` fold and the
  SAME rc 2/3 admission/drain gates as graph mode, emitting the final state as
  canonical JSON (sorted + deduped by compressed rendering): the direct-edge
  set over `[type,name,pred,variant]` node keys (variant = the Python
  `NodeV4.wildcard` encoding) + every persisted residue row (`stars`/`neg`/
  `upos`), including all-empty rows, RAW. Residue-key enumeration honesty note
  in the mode header (keys enumerated over derived defs × store/state names —
  exhaustive for the chain since `putResidue` keys come from delta nodes /
  edge endpoints). rc 4 unknown-mode dispatch unchanged (`test_cli_mode.py`
  still green; error text now names all three modes).
* `formal/conformance/extractor.py`: drives the real `WildcardIndex` +
  `DeltaProcessor` exactly as the graph suite does (shared
  `backends.graphindex_drive`, refactored out of `graphindex_answers`), then
  decodes `EdgeV4`/`ResidueV1` through `NodeV4` into the same canonical form.
  SIX documented projections, each justified in the module docstring:
  P1 closure rows (`direct_edge_count = 0`) — a function of the direct set;
  P2 bridges (target-`w_any` / source-`w_all`) — with the honesty note that
  bridged shapes compile EMPTY on all 15 fragment corpora, so P2 is currently
  inert; P3 multiplicity (refcount vs repeated list entries) — sets both
  sides; P4 all-empty residue rows (model stores, Python deletes) — dropped
  Python-side so the raw divergence stays observable; P5 node sets (GC);
  P6 leaf-family closure-leaf copies (below).
* `test_conformance_state.py` (15 `GRAPH_FRAGMENT` corpora): Lean final state
  == Python final SQL state, symmetric-difference failure message.
* **ATTACK-FIRST FINDINGS** (probes run before trusting the green, scratch
  deleted): (1) the gate's FIRST run found **P6**: even on ComputedOnly
  boolean defs, Python's compiler creates `storage=False` CLOSURE leaf
  families and `RuleSet.apply` routes operand-write copies onto them
  (`editor` write → `viewer.0` edge) — state divergence under FULL
  check-parity, contradicting CORRESPONDENCE §7's old "the shapes coincide"
  note (now corrected there; the leaf class is projected on the reserved `'.'`
  predicate with the pin argument recorded). NOT an adjudication event — a
  documented representation divergence, semantics pinned by the plans' output
  (residues + derived edges, compared exactly) + check conformance + RuleSet
  snapshots. (2) duplicate-tuple probe: Python `direct_edge_count = 2` vs the
  model's repeated list entry — check-parity holds; P3 is what keeps the gate
  honest-green (multiplicity is projected, documented). (3) empty-residue
  probe: `boolean_exclusion` — the model stores `(doc,d1,viewer) = ([],[],[])`
  where Python deletes; raw zcli dump shows the row; without P4 the gate
  fails. (4) corrupted-extraction demonstration: mutating one edge endpoint in
  the extractor makes the gate FAIL with the symmetric diff — the gate can
  fail. Residues compared non-trivially on `boolean_star_exclusion` (1 row)
  and `star_two_strata_churn` (4 rows).

**(b) Exhaustive small-scope enumeration** (`FINAL_REVIEW` §4(b), the §7
"exhaustive ... documented bounds" clause):
* `test_conformance_enum.py`: ALL stores of ≤ 3 tuples from the DECLARED tuple
  space (admission-valid writes from the oracle-parsed Direct restrictions)
  over pool {user: u1,u2; doc: d1,d2}, four shapes — boolean_exclusion (8-tuple
  space, 93 stores), boolean_intersection (8, 93), two_stratum_cascade (12,
  299), boolean_star_exclusion (6, 42) = **527 stores**, spec × oracle × set
  engine over ONE shared grid per shape (grid.py over the full space). Space
  sizes and store counts ASSERTED so the documented bounds cannot drift.
  Runtime ~68 s. Non-vacuity verified: every non-empty store yields TRUE
  verdicts (320/1212/300 TRUEs for the three probed shapes). Graph backend
  deliberately NOT enumerated (runtime ×3; documented in the module docstring).
  **ZERO adjudication events across all 527 stores.**

Docs: FINAL_REVIEW §1 rows flipped ✅ (with the projection/bounds qualifiers in
the claim paragraph), §3 item 4 → the projection residual, §4 reranked;
CORRESPONDENCE scope note (six corners) + gate table + §7 P6 correction;
HANDOFF green-gate count + next-task rewrite.

**Resume →** optional extras, FINAL_REVIEW §4: fragment widening (union roots),
remove legs, wider state/enumeration bounds.

---

## Session 2026-07-12l (cleanup — post-close hygiene pass; NO theorem/proof changes)

Seven audit-ranked cleanup items, one commit each, `verify.sh` fully green before
every commit (lake build + 0 sorries + zcli + standard-axioms audit + 98
conformance tests); full pytest suite green before the push (603 passed).

1. **verify.sh sorry gate STRENGTHENED** (the old whole-line grep missed an inline
   `:= sorry`): now a comment/docstring/string-aware token scan over `*.lean`
   (`--` line + nested `/- -/` block comments handled; strings skipped so a `--`
   inside a string can't hide code) PLUS a grep of the lake build log for the
   compiler's own `declaration uses 'sorry'` warnings (Lake replays cached logs).
   Trip-tested: a temp file with `:= sorry` and `by sorry` counts exactly 2 while
   comment/docstring/string mentions count 0; the real tree scans 0 (the naive
   token grep finds ~21 prose mentions — all excluded correctly).
2. **Stale "remaining sorry" docstrings purged** (`Closure.lean` header +
   `phat_recurrence`, `FuelStable.lean`, `WellDef.lean` — all describe sorries
   closed 2026-07-10); `Core/Ident.lean` no longer promises never-written
   `ValidIdent.ne_star`/`ne_bare` lemmas — it now documents what is true:
   `ValidIdent` opaque, `AllValid` carried (underscored, unused) and not
   dischargeable for concrete stores (cf. the `W4Witness` note).
3. **`Equiv.lean` module header rewritten**: the file is the historical per-stage
   corollary ladder; the final unsuffixed theorems live in `FullScope.lean`.
4. **FINAL_REVIEW.md honesty caveats**: §3 gains "compiler artifacts trusted, not
   modeled" (taint/strata/plans/fan-out/leaf-routing have no Lean counterpart;
   pins = snapshot tests + conformance corpora); §2 non-vacuity bullet now says
   the kernel-checked witness inhabits the hypothesis BUNDLES only — the drained
   reached-state witness is empirical (zcli graph mode) + `cascade2_drains`.
5. **The 27 per-stage T3/T6 corollaries tagged "Historical milestone"**
   (docstrings only; nothing deleted/renamed, Audit untouched). FINDING while
   tagging: the audit's "two real exceptions" (`_direct` different chain; W2
   rules-family residual generality, no `hMatch`/`hWSbare`) UNDERCOUNTS — the
   W1b/W1c rungs also retain real store scope (`w_all` object-wildcard /
   userset-star tuples violate the W4 `bareStar` carry; both already in ROADMAP
   "W4 — honest gaps"). Tagged accordingly instead of "strictly subsumed".
6. **CORRESPONDENCE.md scope note**: conformance is check-verdict level, FIVE
   corners; plan §7's sixth (state-level equality) is OPEN (matches FINAL_REVIEW
   §1's ❌ row).
7. **Rename** `cascade_converges` → `cascade_converges_direct`
   (`GraphIndex/Correct.lean`, W1 untainted-chain quiescence; the contentful T5
   is `runCascade_no_abort`/`cascade_drains` + `runCascade2_no_abort`/
   `cascade2_drains`); Audit line + HANDOFF table updated. Prose mentions of the
   pre-2026-07-10 DELETED `cascade_converges` shape are left as history.

No goldens/snapshots/oracle results touched; no theorem statement changed.

**Resume →** unchanged from 2026-07-12k: Phase 6 hardening extras in
FINAL_REVIEW §4 order (state-level conformance first).

---

## Session 2026-07-12k (Phase 6 items 1–3 — graph-state conformance mode + CORRESPONDENCE.md + FINAL_REVIEW.md; **Phase 6 core CLOSED**)

Resuming from HANDOFF "The next task — Phase 6". Two green+pushed increments;
`verify.sh` green throughout (build + 0 sorries + zcli + standard-axioms audit +
**98** conformance tests, up from 60).

**Increment 1 — the graph-state conformance mode (the contentful piece).**
- **`GraphIndex/Exec.lean`** — the executable driver, built so the CLI is not a
  second model but the CHAIN ITSELF: `foldAdmitsB` (+ `foldAdmitsB_iff`: the
  runtime admission check DECIDES `FoldAdmits`), `cascadeLeg` (verbatim the
  `cascade` constructor target), `graphRun` (per input tuple one admitted logged
  write + one two-round cascade leg — synchronous v1), **`graphRun_reached`**
  (every driver output is a `ReachedBy` state), `graphRun_store`, `drainedB_iff`,
  and the capstone **`graphRun_check_eq_sem`** (under `GraphAdmission` +
  `W4Fragment`, every verdict the CLI prints for an in-scope query IS `sem` —
  `graph_correct` applied to the driver). 5 new Audit entries, standard axioms.
- **zcli mode `"graph"`** (`Cli.lean`): runs `graphRun`, REFUSES (rc 2/3) on
  admission failure or a non-drained final state — out-of-scope inputs fail
  loudly instead of comparing garbage.
- **Harness** (`formal/conformance/`): `backends.graphindex_answers` drives the
  REAL `WildcardIndex` + `DeltaProcessor` through the synchronous write path
  (mirror of `tests/test_matrix.py::GraphBackend`, paranoia ON);
  `test_conformance_graph.py` gates lean-graph vs py-graph AND lean-graph vs
  `sem` over the proved query scope (concrete objects, bare star subjects);
  corpus gains **`cross_stratum_resettle`** (the 12h stale-edge shape: settle a
  stratum-2 derived edge, then ban its subject at stratum 1 — the diffing pass
  must retract) and **`star_two_strata_churn`** (bare star feeding two strata,
  exclusions arriving after the star settles), plus the `GRAPH_FRAGMENT`
  registry (15 in-fragment corpora; 2 documented exclusions).
- **Attack-first findings (scratch probe, deleted after recording in corpus.py):**
  both attack corpora GREEN; both OUT-of-fragment corpora probed anyway —
  `taint_union_over_boolean` (union-rooted derived def, rootB gap) and a
  hand-crafted object-wildcard corpus with concrete-object queries: **0
  mismatches**. The fragment exclusions are proof-scope-driven, NOT observed
  behavioral divergences. No adjudication events.

**Increment 2 — the audit backbone + the final claim.**
- **`CORRESPONDENCE.md`**: the Lean-def ↔ Python-file:line map in 7 layers
  (spec / set engine / graph state+reads / write path / cascade / operational
  closure+driver / intentional divergences), each row citing the enforcing
  mechanism; the conformance-gate table up top.
- **`FINAL_REVIEW.md`**: plan §7 quoted VERBATIM, then a clause-by-clause
  cross-check. Two §7 clauses explicitly NOT claimed (state-level conformance
  equality; exhaustive small-scope enumeration — what exists is check-level
  five-corner conformance + seeded randomized fuzzing), fragment scope
  explicitly subtracted; theorem inventory in English; the full residual-risk
  list; next-marginal-assurance ranking. README.md claim/status refreshed.

**Resume →** Phase 6 hardening extras, in FINAL_REVIEW §4 order: (a)
state-level graph conformance (emit model edge/residue state, diff against
`EdgeV4`/`ResidueV1`); (b) exhaustive small-scope enumeration; (c) fragment
widening (union roots first — the 12k probe suggests the model is already
faithful there); (d) remove legs. None is a blocker for the claim as written.

---

## Session 2026-07-12j (W4 T2a ASSEMBLY — `reachedByW3d2E_inv` + `graph_reached_inv`; **W4 CLOSED**)

Resuming from HANDOFF "The next task — W4 T2a assembly". One green+pushed
increment (new `GraphIndex/CascadeStrataEdge.lean`, +7 Audit entries);
`verify.sh` green (build + 0 sorries + zcli + standard-axioms audit + 60
conformance). **W4 is CLOSED** — the last W4 proof obligation (T2a over the
operational chain) is discharged. The full T-theorem set (T2a/T2b/T3/T6a/T6b)
now stands over `ReachedBy := ReachedByW3d2E`.

**Design (as flagged in HANDOFF): the W3d-1 coverage route deliberately NOT
reused.** `reachedByW3dC_edgeHygienic` went through the coverage chain's SETTLED
verdicts, but W3d2C coverage is CONDITIONAL (12h) — at a re-dirtied round-1
stratum-2 key there is no `SettledKey`. So the assembly works at the EDGE-DIRECT
level (`EdgeHyg1`: no `neg`/`upos` member holds a direct in-edge at its key) with
an invariant that never consumes settledness. Attack duty was light (HANDOFF
noted it): the pass-local core was already proved (12i) and attack-refuted over
the plain chain; the one genuinely new claim — `EdgeHyg1` survives a batch — is a
straight preservation, so the corner check reduces to confirming the write-leg
derived-in-edge fixedness covers `wAny` sources (it does: `writeLeg_derived_
inedges_eq` fixes ALL in-edges of a `RootBoolean` R-node) and that row
declaredness gives `on ≠ STAR` at the other-key branch (it does, `ResidueDeclared`).

**Increment (`GraphIndex/CascadeStrataEdge.lean`).**
- **`EdgeHyg1`** + the two all-key R-node invariants (`RnodeTerminalAll` /
  `RnodeSourceBareAll`, each preserved by one pass via the `[j]`-batch instances
  of `reconcileJobsLR_Rnode_not_source` / `_source_bare`).
- **`edgeHyg1_applyLoggedR`** — one routed pass preserves `EdgeHyg1`: at the job's
  OWN key the pass-local core (`reconcileStarsKeyDR_row_edge_consistent`, 12i)
  re-establishes consistency FRESH whatever the guard said; at every OTHER key
  the row and in-edges are verbatim (`applyLoggedR_other_key_fixed`, other key's
  `on ≠ STAR` from `ResidueDeclared`), so the prior state's hygiene transports.
  The candidate-discipline premise `hnc` (`negCands ⊆ cands`) is the E-chain's
  `enumJob2_negCands_subset`.
- **`edgeHyg1_reconcileJobsLR`** (batch, carrying `StructInv`/`ResidueDeclared`/
  the two R-node invariants/schema, re-established per step) → **`edgeHyg1_
  runCascade2`** (two enumerated batches with the MID context transported through
  round 1, then the residue/edge-inert watermark bump; reject = id).
- **`reachedByW3d2E_edgeHyg1`** — `EdgeHyg1` at every operational state, by chain
  induction: empty vacuous; write legs transport via `writeLeg_derived_inedges_eq`
  at the declared `RootBoolean` key; cascade legs re-establish via
  `edgeHyg1_runCascade2`, the per-round enumerated jobs valid + candidate-audited
  from state (the `hjv1`/`hjv2` derivation copied from `reachedByW3d2E_toC`).
  Fragment threaded exactly as `toC` (hWF/hTT/hNK/hR/hRootB/hMatch/hStrat/hCO/
  hLU2/hWSbare/hSV/hBS/hTS/hterm).
- **`reachedByW3d2E_edgeHygienic`** lifts the direct-edge form to the `Inv`
  clauses' `¬NReaches` form via `reachedByW3d2_reach_collapse_root`;
  **`reachedByW3d2E_inv`** assembles the full 8-clause `Inv` (structural +
  edge-free I6 from the 12i fragment-free layers, edge-referencing I6 from here)
  at EVERY state — dirty/mid-drain included.
- **`FullScope.graph_reached_inv`** — the FINAL T2a restatement over `ReachedBy`
  with the `GraphAdmission`/`W4Fragment` bundles unpacked. The W1 pure-direct
  `graph_reached_inv` (over `ReachedByDirect`) renamed **`graph_reached_inv_direct`**
  (mirrors `graph_correct_direct`). 7 new Audit entries; all standard axioms.

**Resume → Phase 6** (hardening): (a) graph-state conformance mode (drive the Lean
`writeDirect`/`check` model against the PYTHON graph index over the fragment
corpora, like `zcli` already does for `sem`); (b) `CORRESPONDENCE.md` (Lean def ↔
Python file:line map); (c) the final review doc using plan §7 wording verbatim.

---

## Session 2026-07-12i (W4 OPENED — scope inventory, `FullScope.lean` restatement layer, T2a groundwork over the two-round chains, pass-local I6)

Resuming from HANDOFF "The next task — W4". FOUR green+pushed increments;
`verify.sh` green throughout (build + 0 sorries + zcli + standard-axioms audit +
60 conformance). W4 items 1–3 + the witness attack are DONE; the remaining W4
proof is T2a (`Inv` over the operational chain), of which the three fragment-free
layers and the pass-local core landed this session.

**Increment 1 — the design pass (ROADMAP W4 section).** Scope inventory of the
four closed fragments (W2 `graph_correct_rulesBS`, W3c, W3d-1 E, W3d-2 E): shared
query scope (`hqs` star⇒BARE, concrete object) and store hyps (`StoreValidRules` +
`BareStarStore` + `TtuStarFree`); schema-side deltas: `hWSbare` is the ONLY W2
generality W3d-2 lacks (schema-level wildcard-userset restrictions; Python rejects
them only over derived, `zanzibar_utils_v1.py:1446-1451`); on `UntaintedSchema`
every derived-scoped hyp is vacuous and every state drained. Decisions: the
operational chain is canonical (`ReachedBy := ReachedByW3d2E`); hypotheses split
by PROVENANCE (admission mirror vs honest carries); the deleted-as-false
obligations return as the unsuffixed final theorems; honest-gaps list recorded.

**Increment 2 — `FullScope.lean` (the W4 restatement layer).**
- `ReachedBy := ReachedByW3d2E`, `Drained` (abbrevs).
- **`GraphAdmission S T`** (Python-admission mirror, per-field citations: WF,
  NodupKeys, Stratifiable, TtuTuplesetsDirect ← `_validate_ttu_tuplesets`,
  RewriteMatchDeclared, RewriteRanked, `objWild` ← `_reject_object_wildcard_scope`,
  StoreValidRules) / **`W4Fragment S T`** (the honest carries: rootB, computedOnly,
  twoStrata `hLU2`, wsBare, bareStar, ttuStarFree, term; add-only = chain property).
- **`w4_within_scope`**: the bundles imply the SPEC's decision-15 predicate
  `GraphAccepts S` (`State.lean:625` — kept as-is; clause 2 from `wsBare`, clause 3
  from `ttuDirect`+`rootB` via `directsOnly`); converse false — the surplus IS the
  honest-gaps list.
- Final UNSUFFIXED **`graph_correct` / `backend_equivalence` /
  `exclusion_effective` / `no_ghost_grant`** over `ReachedBy` (W1 pure-direct
  versions renamed `*_direct` in `Equiv.lean`).
- W2 subsumption as theorems: `drained_of_untainted` (untainted ⇒ every state
  drained — `affectedKeys` only emits derived keys), `w4Fragment_of_untainted`
  (the fragment collapses to wsBare/bareStar/ttuStarFree).
- **Non-vacuity witnesses** (the attack of record for a restatement stage — an
  uninhabitable bundle would make everything vacuous): `W4Witness.Sx` (`doc#r :=
  a but not b`, compiled form) / `Tx`; `accepts` / `fragment` / `within_scope`
  machine-checked. NOTE: no `AllValid Tx` witness possible — `ValidIdent` is
  deliberately opaque. Lean gotcha: `String.contains` is WF-recursion-backed and
  does NOT kernel-reduce (`decide` sticks) — prove `relNameOK` goals via `simp`;
  every other admission field decides.
- Root aggregator now imports `CascadeStrataEnum`/`CascadeStrataAssemble` (were
  Audit-only) + `FullScope`.

**Increment 3 — `GraphIndex/CascadeStrataInv.lean` (T2a fragment-free layers over
the two-round chains).** `StructInv` / `ResidueHygienic` (edge-free I6) /
`ResidueDeclared` at every `ReachedByW3d2` / `W3d2C` / `W3d2E` state. The routed
guard swap never changes which structural fields a fold branch touches, so the
first two are guard-independent mirrors of `CascadeInv.lean`; declaredness over
the E-chain is HYPOTHESIS-FREE (`enumJobs2At_keyFacts`: enumerated jobs carry
their key facts by construction — `cascadeKeysAbove` props + the enumeration's
own lookup).

**Increment 4 — pass-local I6 (`reconcileStarsKeyDR_row_edge_consistent`).** The
core of the remaining T2a piece, with a DESIGN SHIFT vs W3d-1's
`reachedByW3dC_edgeHygienic`: no settled verdicts. The routed pass's own row is
edge-consistent with its own audit at the post-pass state — a `neg` member failed
the pass-start guard and, being a candidate (`hnc`), was audited against exactly
that guard (`reconcileStarsKeyDR_edge_char`); a `upos` member is userset-shaped
vs bare candidates/sources. Because no settledness is consumed, this holds at
RE-DIRTIED round-1 stratum-2 keys (the 12h attack shape) where `SettledKey` is
unavailable — the reason the W3d-1 coverage-based route would NOT port (W3d2C
coverage is conditional). The E-chain discharges `hnc` by construction
(`enumJob2_negCands_subset`). 19 new Audit entries total this session; all
standard axioms.

**Resume → W4 T2a assembly** (HANDOFF "The next task"): batch/chain edge hygiene
over `ReachedByW3d2E` from the pass-local core, then `reachedByW3d2E_inv` and the
`graph_reached_inv` restatement in `FullScope.lean`; then Phase 6.

---

## Session 2026-07-12h (W3d-2 CLOSED — the E-chain closure assembly: attack-refuted round-1 stratum lemma, conditional coverage, `ReachedByW3d2E`, `graph_correct_w3d2E`)

Resuming from HANDOFF "The next task — the W3d-2 E-chain tail: the CLOSURE ASSEMBLY".
Two green+pushed increments; `verify.sh` green throughout (build + 0 sorries + zcli +
standard-axioms audit + 60 conformance). **W3d-2 is CLOSED**: `graph_correct_w3d2E`
— `check = sem` at every fully-drained state of the fully-operational two-round
scheduler chain, no chain-side validity/cover/scope/coverage hypotheses.

**Attack-first (house rule 2) — the flagged round-1 sub-lemma is REFUTED (a GOOD
kill, the sixth).** The HANDOFF's hoped-for discharge — "a `cascadeKeysAbove S σ
σ.watermark` key reads NO derived operand, so round-1 `hsettledOps` is vacuous" —
is FALSE. `#eval` scenario (scratch deleted): `r1 := a \ b` (stratum 1),
`r2 := r1 \ b` (stratum 2 but reading untainted `b` DIRECTLY); write an `a`-tuple
(dirties `r1`) and a `b`-tuple (dirties `r2` via pred `b`) in the same window. Then
`cascadeKeysAbove` at the watermark contains the STRATUM-2 key `r2`, and the
state-derived `enumJob2` at leg start MISSES the freshly-granted subject (sem-true,
bare, uncovered, `cands.contains = false` — it exists only in the dirty operand's
FUTURE residue, invisible to leaf reach / `res.neg` / `res.upos` / R-node edges).
So UNCONDITIONAL round-1 coverage is undischargeable from state. Python survives
because such a round-1 pass is provably stale-and-re-dirtied
(`round1_emission_dirties`) and round 2 re-enumerates against the settled operand.

**Increment 1 — the conditional-coverage chain.** `W3dJobOpsSettled S T σ j` (the
job's derived operand keys settled+complete at the round baseline; vacuous at
stratum-1 keys). `ReachedByW3d2C.cascade`'s `hcovg1`/`hcovg2` weakened to
`W3dJobOpsSettled → W3dJobCoverage` — exactly what the 12f re-settlement consumes:
`settledComplete_jobsLR_targeted` used coverage ONLY at the last targeting job (now
takes the keyMatch-restricted form); `settledComplete_cascade2_targeted` uses
round-1 coverage at stratum-1 operand keys (baseline vacuous, Case A) and at the
key itself only AFTER deriving `hopsS` (Case B); round 2 gets `hopsMid`.
`covg_of_opsSettled` converts conditional batch coverage to the keyMatch form
(the job's `e` pinned by valid lookup). `reachedByW3d2C_settled` /
`graph_correct_w3d2` / T3/T6 unchanged in statement — the chain got STRICTLY
easier to construct.

**Increment 2 — the assembly (`GraphIndex/CascadeStrataAssemble.lean`, new).**
- Structural: `mem_cascadeKeysAbove_props` (cursor-generic);
  `reachedByW3d2_Rnode_source_name_ne_star` + `reconcileJobsLR_source_name_ne_star`
  (star-free R-node in-edge discipline, chain + batch);
  **`ResidueSubjectsStarFree`** (persisted `neg`/`upos` members star-free — the
  structural invariant `enumJob2` validity needs, since residue-named subjects flow
  into the candidate lists; sourced from `W3cJobValid` candidate star-freeness
  through the routed recompute's filters) with pass/batch/chain preservation
  (`reachedByW3d2_residueStarFree`); `enum2Base_name_ne_star`;
  **`w3cJobValid_enumJob2`** (state-generic — explicit per-key edge-source facts so
  it instantiates at leg start AND at MID via the batch transports).
- `enumJobs2At` (jobs for a key set, enumerated at a given state) + `_cover`/
  `_scope`/`_valid`; `enumJobs2R1` (watermark frontier at leg start) / `enumJobs2R2`
  (round-1 emissions at MID — the state inside the definition IS the C-chain's
  coverage baseline, definitionally).
- **`ReachedByW3d2E`** (cascade legs run the two enumerated rounds) +
  **`reachedByW3d2E_toC`**: round-1 conditional coverage discharged by
  `w3dJobCoverage_enumJob2_state` at the leg start (the `W3dJobOpsSettled` premise
  is handed to us as `hsettledOps` — no stratum case analysis needed at all);
  round-2 by `w3d2_leg_context` + `w3dJobCoverage_enumJob2` at MID (shadow via
  `untaintedShadow_reconcileJobsLR`, closedness via `edgesClosed_reconcileJobsLR`,
  reach collapse via `reconcileJobsLR_reach_collapse` over the σp edge discipline).
- **`graph_correct_w3d2E`** = `graph_correct_w3d2` ∘ the projection. Audit: 4 new
  entries (`reachedByW3d2_residueStarFree`, `w3cJobValid_enumJob2`,
  `reachedByW3d2E_toC`, `graph_correct_w3d2E`), standard axioms only.

**Design note.** The conditional form turned the dreaded per-round stratum split
into pure plumbing: round 1 never has to DECIDE whether a key is stratum-1 — the
baseline premise is simply threaded through, and the C-chain's own re-settlement
machinery (which already derives the baseline where it's needed) does the rest.
The 12f statements were already the right shape; only their hypotheses moved.

**Resume → W4** (full-scope restatement: combine W1+W2+W3 generality, name the
closure `ReachedBy`, restate `graph_correct` / `graph_reached_inv` /
`backend_equivalence` / T6a/T6b at `GraphAccepts` scope), then Phase 6 hardening
(graph-state conformance mode, CORRESPONDENCE.md, final review doc).

---

## Session 2026-07-12g (W3d-2 E-chain tail — the coverage-discharge CORE: derived-leaf decomposition, routed reads-as-star, enumJob2 coverage, the routed leg context)

Resuming from HANDOFF "The next task — the W3d-2 E-chain tail". FOUR green+pushed
increments, all in the NEW `GraphIndex/CascadeStrataEnum.lean` (+ Audit import + 6
entries); `verify.sh` green throughout (build + 0 sorries + zcli + standard-axioms
audit + 60 conformance). This closes the mathematically hard part of the tail — the
enumeration + its `W3dJobCoverage` over the two-round chain; what remains is the
closure ASSEMBLY (cursor-parameterized `enumJobs2`, `ReachedByW3d2E`, discharging
operand-settledness per round).

**Attack-first (house rule 2).** No new attack scratch this session: the two central
NEW statement shapes were pre-adjudicated. (a) The DERIVED-leaf decomposition —
finding (c)'s residue-named candidates (`neg`/`upos` are edge-free/I6, invisible to
reach-probe enumeration) — was #eval-confirmed real in session 12c against the Python
(`_derived_leaf_neg_ids`, `processor.py:461-495`; old `upos` ids `:425-429`). (b) The
`probeDerived` case analysis is a mechanical boolean identity checked exhaustively
over all three predicate branches. Both mirror established W3d-1c-piece-B shapes.

**Increment 1 — the derived-leaf concrete decomposition.** `graphRecR_derived` /
`probeDerived_star` (routed reads at a derived leaf); `probeDerived_concrete_off_named`
(a star-free subject triggering none of the three concrete-specific terms — incoming
edge, `res.neg`, `res.upos` — reads the derived leaf exactly as its shape's `stars`
row); `residueNamed` (the state-derived neg+upos candidates); the combined
`graphRecR_derived_agree_off_named`.

**Increment 2 — routed reads-as-star + `enumJob2` coverage.**
`graphRecR_leaf_agree` (per-leaf agreement, BOTH leaf kinds: untainted via
`probeNonDerived_concrete_decomp`, derived via piece 1) →
`checkFnR_eq_star_of_not_enum` (the routed analog of W3d-1's
`checkFn_eq_coveredFn_of_not_mem` — `evalE` congruence; KEY simplification: NO
reach-collapse needed, since reach into a leaf node already makes the subject a leaf
concrete). `enum2Base`/`enumJob2` (W3d-1's `enumJob` with residue-named candidates
folded into the per-key base list). `w3dJobCoverage_enumJob2`: all four coverage
clauses from the ROUTED leg context (`hbridge`/`hcovDecl` over `checkFnR`), same
contrapositive skeleton as `w3dJobCoverage_enumJob`. (Design note: the coverage
clause hypotheses carry `enumJob2` field projections, not plain `dt`/`on`/`R` — the
final contradictions use `exact` (defeq-tolerant) instead of `rw` of the j-field
`sem` hyps.)

**Increment 3 — the routed leg context.** `checkFnR_star_declared` (routed
no-ghost-star-coverage — factored VERBATIM from `graph_correct_w3d2`'s `hsem_ws`,
`CascadeStrataResettle.lean:1458-1485`: a `checkFnR`-true star read has a true leaf;
untainted → shadow → `graphRec_star_declared`; derived → the settled operand's
`stars`-row read). `w3d2_leg_context`: bundles `hbridge` (`checkFnR_eq_sem_settled`)
+ `hcovDecl` (`checkFnR_star_declared`) at a shadowed W3d-2 state whose derived
operand keys are settled (`hops`).

**Increment 4 — `enumJob2` coverage at a W3d-2 state.**
`w3dJobCoverage_enumJob2_state`: over ANY `ReachedByW3d2` state, `enumJob2`'s coverage
holds given only that the derived operand keys are settled+complete (`hsettledOps`).
The shadow (`reachedByW3d2_shadow`), edges-closedness, the schema anchor, and the
per-operand reach collapse (`reachedByW3d2_reach_collapse_root`) are all read off the
state. `hsettledOps` is the SINGLE remaining obligation for the closure assembly.

**Resume → the closure assembly (the last mile of the E-chain tail).** With coverage
discharged modulo `hsettledOps`, what remains is pure scheduler plumbing:
1. **`enumJobs2`** — the two per-round enumerated job lists, cursor-parameterized:
   round 1 over `cascadeKeysAbove S σ σ.watermark`, round 2 over
   `cascadeKeysAbove S (reconcileJobsLR S T σ jobs1) (σ.frontierMax σ.watermark)` (the
   MID state). Mirror `enumJobs`/`enumJobs_cover`/`_scope`/`_valid` (W3cJobValid for
   `enumJob2` — cands/negCands bare+star-free via the bare filter and `edgeHolders`;
   uposCands non-bare — need: residue-named `neg` members are star-free by
   `SettledKey`, `upos` non-bare star-free by `SettledKey`; a subtlety absent from
   W3d-1's `enumJob` whose base was reach-only).
2. **Discharge `hsettledOps` per round.** Round 1: its keys are STRATUM-1 (untainted
   operands) — `hsettledOps` VACUOUS. THE key sub-lemma to prove/find: a
   `cascadeKeysAbove S σ σ.watermark` key has NO derived operand (the dual of
   `round2_key_reads_derived`; the 12e attack established writes dirty only stratum-1
   operand keys). Round 2: its keys' stratum-1 operands are settled by round 1 —
   thread `settledComplete_cascade2_targeted` / `reachedByW3d2C_settled` (or the
   per-round `SettledKey`/`CompleteKey` transports) to supply `hsettledOps` at the MID
   state.
3. **`ReachedByW3d2E`** (cascade legs run `enumJobs2` for both rounds) + the
   projection `reachedByW3d2E_toC` discharging all 8 `ReachedByW3d2C.cascade` hyps
   from state (`hjv1/hjv2/hcover1/hscope1/hcover2/hscope2` structurally,
   `hcovg1/hcovg2` via `w3dJobCoverage_enumJob2_state` + the round-wise
   `hsettledOps`). Payoff: **`graph_correct_w3d2E`** — the two-stratum read theorem
   over the fully-operational scheduler chain, no chain-side coverage hypotheses.
Then **W4**.

Fragment carries: exactly W3d-2's (`hLU2`, `BareStarStore`/`TtuStarFree`,
`hWSbare`, W2 carries, add-only STORE). House rules: attack-first the round-1
stratum-1 sub-lemma (item 2) especially; subagents read-only.

---

## Session 2026-07-12f (W3d-2 ENDGAME — the two-round re-settlement, the three-disjunct invariant, `graph_correct_w3d2`; only the E-chain tail remains)

Resuming from HANDOFF "The next task — W3d-2 endgame" (increments 1–3). Three
green+pushed increments, all in the NEW `GraphIndex/CascadeStrataResettle.lean`
(+ root import, Equiv.lean `*_w3d2` corollaries, Audit import via Equiv + 12
entries); `verify.sh` green throughout (build + 0 sorries + zcli + standard-axioms
audit + 60 conformance). No new attack scratch: the invariant disjunction and the
bridge shape were attack-shaped in 12e, and the re-settlement statement follows the
12e design note (per house rule 2's "only if it deviates" clause); the one
STRUCTURAL deviation — see "design deviations" below — REMOVES a hypothesis rather
than adding one.

**Increment 1 — the ROUTED edge characterisation + the two-round re-settlement.**
The W3d-1 edge char collapses routed guards only on all-untainted defs; at a
stratum-2 key the guard genuinely reads derived operands, so the char is re-proved
with `checkFnR`/`coveredFnR` guards: `computedRefs_ne_self` (under per-def `hLU2` a
derived def never reads ITSELF — self-reference would make its own operands
derived), so every leaf the guard consults sits at a key `r' ≠ R` where the fold is
read-inert (`check_reconcileKeyDR_other`, fold-level mirrors of the 12d pass-level
inertness; `check_reconcileResidueKeyR_other` for the residue write). `wantEdgeR` +
`wantEdgeR_reconcileKeyDR_inert` + `reconcileKeyDR_edge_char` (guard abstracted,
mirror) + **`reconcileStarsKeyDR_edge_char`** (pass-level: candidate-with-
routed-guard-at-pass-start ∨ non-candidate-pre-pass-edge). On top:
`reconcileJobsLR_key_edge_sem` — the routed batch edge origin, with the
stratum-staged bridge (`checkFnR_eq_sem_settled`) read at EVERY prefix state
(operand settledness/discipline/shadow threaded stepwise via the singleton-batch
forms of the 12e transports); **`settledComplete_jobsLR_targeted`** — the
batch-level re-settlement, stated per ROUND (structural facts explicit, coverage
baseline = batch start) so the leg can instantiate it twice; and
**`settledComplete_cascade2_targeted`** — the leg-level assembly.

**Design deviations from the 12e note (both simplifications).** (a) The case split
is "targeted by round 2 or not" (not stratum-shaped): Case A settles over `jobs2`
from MID — each derived operand key is settled AT MID either by a nested
application of the batch lemma at σ (operand targeted in round 1; its own operands
untainted make every side condition vacuous) or by transport (untargeted ⇒ clean at
leg start, else `hcover1` would target it — `hopsBase` gives settledness); the
stratum fence (`round2_key_reads_derived` + `hLU2`) keeps round 2 off the operand
keys. Case B: `round1_emission_dirties` + `hcover2` prove NO round-1 job targets
any derived operand key (its emission would put the key in round-2 scope and Case B
denies round-2 targeting), so operands are settled at σ throughout and round 2 is
inert at the key. The impossible-third-case analysis of the design note becomes the
Case-B contradiction. (b) The planned `round2_scope_operand_targeted`
strengthening (round-2 scope ⇒ operand targeted in round 1, same dt/on) turned out
UNNECESSARY — `round2_key_reads_derived` (the 12d fence) plus the emission lemma
carry both cases. Stratum-1 keys need no separate treatment: `hops` is vacuous for
them, so ONE batch lemma serves both strata (no conservativity collapse needed).

**Increment 2 — `sem_nil_derived_false2` + the three-disjunct invariant.** The
stratum-2 empty-store lemma runs the stratum-staged bridge AT the empty chain state
(`ReachedByW3d2.empty` → shadow; stratum-1 operand keys vacuously settled — empty
representation, `sem` false by the stratum-1 lemma; the routed guard's leaves all
read an edgeless, residueless graph). **`reachedByW3d2C_settled`**: at every W3d-2
coverage-chain state, every declared derived key is dirty ∨ SOME-DERIVED-OPERAND-KEY
dirty ∨ settled+complete (the 12e attack-shaped form). Write legs: both dirtiness
disjuncts are monotone (`cascadeKeys_writeLeg_mono`); otherwise the key and all its
operand keys are unmapped and operands settled at the pre-state (IH at the operand:
its op-dirty disjunct is vacuous by `hLU2`), so `writeLeg_sem_stable2` +
`settledKey/completeKey_writeLeg_sem` transport. Cascade legs: targeted keys by the
two-round settle theorem (`hopsBase` from the IH); untargeted keys — dirty would be
covered by `hcover1` (targeting job, contra), operand-dirty forces a round-2
targeting job via `round1_emission_dirties` + `hcover2` (contra), settled
transports through both rounds + the accept record update (`runCascade2_no_abort`).

**Increment 3 — `graph_correct_w3d2` + T3/T6.** The last gap was NO-GHOST-STAR-
COVERAGE at a stratum-2 key: `coveredFn_declared` converts a true UNROUTED guard at
the admitted base, but the unrouted guard reads a stratum-2 def's derived leaves as
dead probes at σ0 — it cannot carry the claim. The replacement: at the drained
state the ROUTED bridge turns `sem`-coverage into a true `checkFnR`, which has a
true leaf (`evalE_computedOnly_true_leaf`); an UNTAINTED leaf transfers through the
shadow to σ0 where **`graphRec_star_declared`** (steps 2–7 of `coveredFn_declared`,
factored) traces the star subject's first out-edge to a wildcard-flagged
restriction; a DERIVED leaf is the settled operand's `stars`-row read, declared by
`SettledKey`'s row characterisation directly. With that, the derived branch is
exactly `probeDerived_eq_sem_settled` at the (invariant-settled, drained) key —
`graph_correct_w3d2`: `check = sem` at every fully-drained `ReachedByW3d2C` state,
W3d-1 subject/query scope, `hLU` relaxed to `hLU2`. T3/T6:
`backend_equivalence_w3d2` / `exclusion_effective_w3d2` / `no_ghost_grant_w3d2`.

**Resume → the W3d-2 E-chain tail** (HANDOFF "The next task"): extend `enumJobs`
with the residue-named candidates (12c finding (c): `_derived_leaf_neg_ids`,
`processor.py:461-495`, old `upos` ids `:425-429`) and discharge `ReachedByW3d2C`'s
two-round coverage/validity/scope hypotheses from the state (`ReachedByW3d2E`,
mirroring W3d-1c piece B). Then W4.

---

## Session 2026-07-12e (W3d-2 item 3b — the W3d2 shadow, the stratum-staged read bridge, settledness transports, the coverage chain)

Resuming from HANDOFF "The next task — W3d-2 continuation" (item 3b). Three
green+pushed increments, all in the NEW `GraphIndex/CascadeStrataSettle.lean`
(+ root import, Audit import + 3 entries); `verify.sh` green throughout (build +
0 sorries + zcli + standard-axioms audit + 60 conformance).

**Attack-first (house rule 2) — one REFUTATION, one survival (scratch deleted).**
On the 2-stratum schema `c := x ∖ y, b := c ∨ z` (`#eval` vs the real
`writeLoggedRules`/`runCascade2`/`check`/`checkFnR`/`sem`):
(a) **The W3d-1-shaped settledness invariant "dirty ∨ settled" is FALSE at W3d-2
post-write states**: after `write y(alice)` (post `x(alice)`+cascade) the dirty set
is exactly `[(doc, c, 1)]` while `b` is STALE (`check = true ≠ sem = false`) and
NOT dirty — a write row can never reach a stratum-1 R-node (its in-edge sources
are bare and in-edge-free), so `_map_deltas_to_keys` maps only the operand key.
The W3d-2 invariant MUST carry a third disjunct: *some derived operand key dirty*
(settled ∨ dirty ∨ operand-dirty). (b) **The bridge shape SURVIVED**: at the
post-round-1 mid state (operand `c` re-settled) `checkFnR = sem = false` while
`b`'s STORED rep still reads stale; at the pre-round-1 state `checkFnR = true ≠
sem` — the settledness hypothesis is load-bearing. Round 1's emission re-dirties
exactly `[(doc, b, 1)]`; fully-drained `check = sem` on the grid.

**Increment 1 — the W3d2 shadow + the stratum-staged read bridge.** Chain
structural mirrors over `ReachedByW3d2` (`runCascade2_cases`, endpoint closure,
`edge_target_ne_bare`/`edges_target_plain`/`Rnode_source_bare`,
`reachedByW3d2_reach_collapse_root`); the shadow at EVERY W3d2 state
(`reachedByW3d2_shadow` via `untaintedShadow_applyLoggedR`/`_reconcileJobsLR` —
prefix states of either round are shadowed, so the W2 read bridge holds
mid-round); `probeDerived_eq_sem_settled` (the whole derived branch of
`graph_correct_w3d` factored into a pure per-key lemma: settled+complete +
collapse + linchpin ⇒ `probeDerived = sem`, all three subject scopes);
**`checkFnR_eq_sem_settled`** — the stratum-staged bridge: untainted leaves via
shadow+`graphRec_base_eq_bs`, derived leaves via the settled-key read, assembled
by the routed `checkFnR_eq_semStep` + `sem_fuel_stable`. Per-def `hLU2` supplies
the operands' own all-untainted defs.

**Increment 2 — settledness transports at both strata.** Routed other-key fixity
(`applyLoggedR_other_key_fixed`/`reconcileJobsLR_other_key_fixed`) + per-ROUND
`SettledKey`/`CompleteKey` batch transports (`*_jobsLR_untargeted`); the stratum
fence **`round2_key_reads_derived`** (the (A)-half of the no-abort analysis
factored: a round-2 scope key reads a derived operand ⇒ round 2 never targets a
stratum-1 key); the write-leg layer: `writeLeg_probeDerived_stable` (derived read
write-inert: residue fixed + I5 in-edge fixity + collapse both sides),
`writeLeg_checkFnR_stable` (routed guard of an unmapped key stable),
`writeLeg_sem_stable_sh` (stratum-1 `sem` stability, CHAIN-AGNOSTIC — shadows and
structural facts as direct hypotheses, consumable at W3d2 states),
stratum-generic `settledKey_writeLeg_sem`/`completeKey_writeLeg_sem` (rep
transport given `sem` stability), and **`writeLeg_sem_stable2`** — `sem` at a
stratum-2 key unmapped directly AND through every derived operand key is
unchanged: bridge at both ends of the leg (operand settledness transported by the
stratum-1 half), routed guard stable in the middle, store-irrelevance joining.

**Increment 3 — invariant groundwork + the coverage chain.**
`reconcileJobsLR_emits` (every routed logged job emits a persistent frontier row
above the pre-batch frontier — the introduction dual of outbox soundness) →
**`round1_emission_dirties`**: a round-1 pass at `(dt, r', on)` puts every reader
key `(dt, R, on)` in round-2 scope — 12c finding (b) as a theorem, the hinge of
the coming case analysis (a stratum-2 key settled STALE in round 1 is provably
re-targeted in round 2). Edge discipline batch-stable ⇒ the reach collapse at
every MID-BATCH prefix state (`reconcileJobsLR_reach_collapse`).
**`ReachedByW3d2C`**: the two-round coverage chain — per-round `W3dJobCoverage`,
round 2 relative to the MID state (its passes re-enumerate against the graph as
round 1 left it) — with projection `reachedByW3d2C_toW3d2`.

**Design note for the resume (the settle-case analysis, worked out this session).**
For a stratum-2 key `k` in an accepted cascade2 leg, exactly two shapes:
*Shape 1* (no derived operand of `k` dirty at leg start ⇒ none targeted in round 1
⇒ operands settled at σ and transported through round 1 — hscope1 keeps round-1
jobs off clean keys — and through round 2 — the stratum fence): `k`'s last
targeting job is in ROUND 1 with the bridge at every prefix state; coverage
baseline σ (hcovg1). *Shape 2* (some operand targeted in round 1): that pass's
emission puts `k` in round-2 scope (`round1_emission_dirties`) ⇒ hcover2 targets
`k` in round 2 ⇒ `k`'s LAST targeting job is in jobs2, coverage baseline MID
(hcovg2) — a stale round-1-added edge at `k` is present at MID and hence in the
last job's cands, audited with the correct guard (operands settled at round-1 end,
round 2 inert at them). The impossible third case (operand dirty but its targeting
job AFTER `k`'s last targeting job, `k` never re-targeted) contradicts
`round1_emission_dirties` + hcover2 + the last-job split. Stratum-1 keys: W3d-1
shaped, with per-job conservativity (`reconcileStarsKeyDR_eq`) collapsing routed
passes to W3d-1 passes.

**Resume → W3d-2 remaining**: (a) the targeted re-settlement over the concatenated
two-round batch (`reconcileJobsLR_append` view; mirror `settledComplete_cascade_
targeted` with the above case analysis) → **`reachedByW3d2C_settled`** (the
three-disjunct invariant) → **`graph_correct_w3d2`** + T3/T6 `*_w3d2`; (b) the
E-chain tail with residue-named candidates (12c finding (c)).

---

## Session 2026-07-12d (W3d-2 — scheduler structural layer, T5 at two strata, per-stratum operand-read inertness)

Resuming from HANDOFF "The next task — W3d-2 continuation" (plan items 1–3; item 3's
inertness half). Two green+pushed increments, both in `GraphIndex/CascadeStrata.lean`
(+ 11 Audit entries); `verify.sh` green throughout (build + 0 sorries + zcli +
standard-axioms audit + 60 conformance).

**Attack-first (house rule 2) — `runCascade2_no_abort` SURVIVED; `hLU2` is
load-bearing (scratch deleted).** On the 3-stratum schema `a := b ∨ y, b := c ∨ x,
c := x ∖ y` a decidable `hLU2` evaluates FALSE and the reject genuinely FIRES: the
round-2 pass at `b`'s R-node emits a row that maps to key `(doc, a, 1)`, the leftover
check fails, `runCascade2` returns the pre-state — no-abort WITHOUT `hLU2` is
refuted, the condition does exactly the "3 strata in disguise" rejection the HANDOFF
demanded. On the 2-stratum truncation `hLU2` is TRUE while W3d-1's `hLU` is FALSE
(the widening is contentful), the leftovers map to no keys, and fully-drained
`check = sem` held on the grid for one- and three-write batches.

**Increment 1 — the structural layer + T5.** Mirrors of W3d-1a over the routed
batch (the routed guard changes which fold branch fires, never which fields a branch
touches): `reconcileJobsLR_outbox_sound` / `_watermark` / `_edge_sound` (+ the
`applyDR` bookkeeping and `reconcileKeyDR`/`reconcileResidueKeyR` field lemmas);
R-node terminality over the two-round closure (`reachedByW3d2_edge_source_ne_R` →
`reachedByW3d2_Rnode_not_source`, plus the batch-transported round-STACKABLE
`reconcileJobsLR_Rnode_not_source` — base terminality in, post-batch terminality
out, applied σ→mid→final); cursor arithmetic `le_frontierMax` /
`outbox_le_frontierMax` (every outbox row sits at or below the advanced cursor — a
round's read is exhaustive). **T5**: `runCascade2_no_abort` — hyps `hterm` + `hLU2`
+ `hjv1`/`hjv2` + `hscope2` + the chain; proof: a row above the round-2 cursor is a
jobs2 emission (old/mid rows bounded by `outbox_le_frontierMax`); its only candidate
object is its own terminal R-node; a derived reader `k` of `j.R` would trigger
`hLU2` at `k` forcing ALL of `j.e`'s operands untainted — but `hscope2` says `j`'s
key was dirtied by a ROUND-1 emission at `j1`'s R-node, so `j1.R ∈ computedRefs j.e`
with `isDerived (j.dt, j1.R)` — contradiction. `cascade2_drains`: the two-round
watermark advance justified, never asserted. `hLU2_of_hLU`: the W3d-1 condition is
literally the special case.

**Increment 2 — per-stratum operand-read inertness (item 3's inertness half).** A
routed pass at `(dt, R, on)` writes residue only at its own R-node under `R` and
touches edges only AT that terminal node, so every read anchored at any OTHER key is
pass-constant: `graphRec_reconcileStarsKeyDR_inert` (untainted ≤4-probe read; probe
targets never the derived R-node), `probeDerived_reconcileStarsKeyDR_other` (derived
edge+residue read; node inequality from key inequality via `objNode_inj_of_ne_star`,
STAR-object case by variant clash), assembled into **`check_reconcileStarsKeyDR_other`**
(the routed leaf read, BOTH strata in one statement, routing stable since the pass
fixes the schema) and **`checkFnR_reconcileStarsKeyDR_other`** (the routed compiled
guard of any def whose computed leaves differ from the pass key — via
`evalE_computedOnly`). Supporting routed mirrors of the W3d-1b `ReconcileDiff` layer:
`reconcileKeyDR_reach_inert`/`_reach_pres` (both directions off the R-node),
`edgesClosed_reconcileKeyDR`, `reconcileKeyDR_Rnode_terminal`,
`reconcileKeyDR_residue` + `reconcileResidueKeyR_residue_other` +
`reconcileStarsKeyDR_residue_other`.

**Proof-engineering notes.** (1) `subst hveq` (with `hveq : v = d'.node`) eliminates
`v` — later tactic text must say `d'.node`, not `v` (a stale `v` surfaces as
`Unknown identifier` with a `sorry` placeholder in the goal display). (2) The
`(k.1, k.2)` / `k` Prod-eta defeq lets `hlk : S.lookup k = some e''` feed
`hLU2 k.1 k.2` directly. (3) The no-abort scope analysis hoists everything
independent of the leftover row's reader key `k` (the `hscope2` unfolding down to
`j1.R ∈ computedRefs j.e` and `j.dt = j1.dt`) BEFORE the per-`k` `filterMap`
refutation — inside, `hLU2` + those facts close it in four lines.

**Resume → W3d-2 remaining** (HANDOFF "The next task"): (a) the stratum-staged
shadow/settledness generalization (inertness now in hand: a pass perturbs another
key's guard only through the reconciled key itself), (b) the read bridge
`checkFnR = sem` at fully-drained states by strata induction → `graph_correct_w3d2`,
(c) the E-chain tail with residue-named candidates (12c finding (c)).

---

## Session 2026-07-12c (W3d-2 OPENING — attack survival, the ROUTED leaf dispatch, conservativity, the two-round scheduler)

Resuming from HANDOFF "The next task — W3d-2". One green+pushed increment: the NEW
`GraphIndex/CascadeStrata.lean` (+ root import, Audit import + 5 entries); `verify.sh`
green throughout (build + 0 sorries + zcli + standard-axioms audit + 60 conformance).

**Attack-first (house rule 2) — the intended statement SURVIVED; three findings
(scratch deleted).** `#eval`'d the routed two-round scheduler (scratch copies of the
planned defs below) against `sem` over: cross-stratum union (`viewer := editor ∨
member`, `editor := owner ∖ banned`), cross-stratum EXCLUSION (`viewer := member ∖
editor` — a stratum-1 retraction forcing a round-2 edge ADDITION, and the reverse),
star grants (`owner(doc:1, user:*)` — stratum-2 `stars`/`neg` through routed residue
reads), and cross-stratum userset `upos` propagation; each under sync (cascade per
write) AND async (batched writes, one cascade) modes AND both within-round job orders.
Fully-drained `check = sem` in ALL cases; the accept branch always fired (no aborts).
Findings: (a) **mid-drain staleness is real** — after round 1 only, a stratum-2 read
disagrees (`viewer` `check=false sem=true` right after `banned(alice)` retracts
`editor`): the W3d-2 read theorem stays fully-drained-scoped, and the settledness
invariant must become stratum-staged. (b) **Within-round order is NOT load-bearing**
(`processor.py:714-719`'s stratum sort is an optimization): a stale round-1 recompute
of a stratum-2 key is re-settled in round 2 because the stratum-1 pass's emission
re-dirties it — the model chain leaves batch order free. (c) **Enumeration note for
the W3d-2 E-chain tail**: Python's audit at a derived-reading key pulls the operand
residues' `neg` ids (`_derived_leaf_neg_ids`, `processor.py:461-495` — "exclusions
recorded in lower-strata residues must surface as candidates") and the old `upos` ids
(`:425-429`); a lower-stratum `neg`/`upos` member is edge-free (I6) and invisible to
reach-probe enumeration, so the W3d-2 `enumJobs` must extend `leafConcretes` with
residue-named candidates.

**The routed read (the model extension).** `graphRecR σ s := fun ot on' r' => check σ
⟨s, r', ⟨ot, on'⟩⟩` — every operand leaf reads the graph's own `check`, routing on
`isDerived σ.schema`. Faithful: `_EvalContext` dispatches untainted leaves to
`leaf_check` = `widx.check` and derived-computed leaves to `derived_check` =
`widx._check_derived` (= `probeDerived`); `derived_stars` = the operand residue's
stored `stars`, pointwise the `probeDerived` star-subject read (`processor.py:43-70`);
`member_check` (`:182-188`) is literally this routing. `checkFnR` = `evalE` over
`graphRecR`; `coveredFnR sh = checkFnR (starSubj sh)` (the routed `stars_fn`,
pointwise). Routing lemmas `check_untainted`/`check_derived`; **conservativity**
`checkFnR_eq_checkFn` (on `ComputedOnly` defs with untainted operands the routed read
IS the W3d read — `evalE_computedOnly` over `graphRecR_eq_graphRec`); **congruence**
`checkFnR_evalEq` — the routed read consults exactly the `EvalEq` core
(schema/edges/nodes/residue; the unrouted `checkFn_congr` needed only edges/nodes —
`probeDerived_congr`/`check_evalEq` are the new pieces).

**The routed pass + batch conservativity.** `reconcileResidueKeyR`/`reconcileKeyDR`/
`reconcileStarsKeyDR`/`W3cJob.applyDR`/`applyLoggedR`/`reconcileJobsLR` mirror the W3d
diffing pass with routed guards. Collapse theorems `reconcileResidueKeyR_eq`/
`reconcileKeyDR_eq`/`reconcileStarsKeyDR_eq` under per-def `hco`+`hLU`
(schema-invariance threaded through the folds), assembled into **`reconcileJobsLR_eq`**:
under the W3d-1 schema-level `hCO`/`hLU`, a routed logged batch of VALID jobs IS the
W3d logged batch — **W3d-1 is the single-stratum image of the routed scheduler**.

**The two-round scheduler + chain.** `frontierRowsAbove`/`cascadeKeysAbove` (explicit
per-round frontier cursor; `cascadeKeys_eq_above` pins W3d-1's `cascadeKeys` as the
round at the stored watermark, `rfl`); `frontierMax` (the cursor advance,
`processor.py:703`); **`runCascade2`** (`run_cascade` at `rounds = len(strata) = 2`:
round 1 above the watermark, round 2 on round 1's emissions, final leftover check with
the reject branch; accept advances the watermark past everything); **`ReachedByW3d2`**
(the two-stratum interleaved closure — C-style job batches with validity + two-sided
coverage per round, round-2 coverage read at the mid-state
`reconcileJobsLR S T σ jobs1` above `σ.frontierMax σ.watermark`);
`reachedByW3d2_schema` (the dispatch anchor).

**Proof-engineering note.** `let`-bindings inside a `def` block `split` after `unfold`
(they surface as `have`s); `runCascade2` is written with repeated expressions like
W3d-1's `runCascade`.

**Resume → W3d-2 continuation** (HANDOFF "The next task" has the plan): (1) the
scheduler structural layer over `ReachedByW3d2` (outbox soundness / watermark
bookkeeping / edge-soundness mirrors of the W3d-1a layer); (2) T5 halves —
`runCascade2_no_abort` under the two-stratum `hLU2` (round-1 emissions at stratum-1
R-nodes map to stratum-2 keys settled in round 2; round-2 emissions map to NO keys);
then (3) per-stratum operand-read inertness + the shadow generalization, (4) the read
bridge `checkFnR = sem` at fully-drained states by strata induction →
`graph_correct_w3d2`, (5) the E-chain with the residue-named candidate enumeration
extension (finding (c)).

---

## Session 2026-07-12b (W3d-1c piece B TAIL — the enumerated-cascade restatement; **W3d-1c fully CLOSED**)

Resuming from HANDOFF "The next task — W3d-1c piece B TAIL". One green+pushed increment,
all in `GraphIndex/CascadeEnum.lean` (+ 5 Audit entries); `verify.sh` green throughout
(build + 0 sorries + zcli + standard-axioms audit + 60 conformance). This closes W3d-1c:
`graph_correct_w3d` / `reachedByW3dC_inv` are now available UNCONDITIONALLY — over a
fully-operational scheduler chain whose cascade legs are BUILT from the state-derived
enumeration, so `W3dJobCoverage` (and `hcover`/`hscope`/`hjv`) are discharged, not
assumed. The plan was the one pinned in the 2026-07-12 HANDOFF; it went through as
written, no surprises.

**The one genuinely new lemma.** `reachedByW3d_Rnode_source_name_ne_star` — the star-free
analog of `reachedByW3d_Rnode_source_bare` (an in-edge source at a `RootBoolean` derived
R-node is star-free): SAME induction (empty; write leg via `writeLeg_derived_inedges_eq`
= model-level I5; cascade via `reconcileJobsD_edge_sound`, the new candidate edge's source
`subjNode c` star-free by `W3cJobValid`'s cands-non-star clause + `subjNode_plain`). Needed
for the edge-holder half of `enumJob`'s `cands`.

**`enumJob` is `W3cJobValid` (`w3cJobValid_enumJob`).** All nine clauses: `R ≠ BARE`
(`lookup_rel_ne_bare`); cands bare (bare-filtered leaf concretes by the filter, edge
holders by `reachedByW3d_Rnode_source_bare`); cands/negCands/uposCands star-free (leaf
concretes by `leafConcretes_name_ne_star` — the filter's `name != STAR`; edge holders by
the new source lemma); uposCands non-bare (the filter); declared-derived key data from
the enumeration hypotheses.

**Cascade-key structural facts.** `mem_affectedKeys_props` / `mem_cascadeKeys_props`: every
cascade key `(dt, R, on)` names a DECLARED DERIVED key at a STAR-FREE object — read
straight off `affectedKeys`' `_map_deltas_to_keys` branch (`isDerived`, `S.lookup = some`,
`v.name ≠ STAR`). The mp-direction companion of the existing `mem_affectedKeys` (intro).

**The enumerated cascade + closure.** `enumJobs S σ` = `(cascadeKeys S σ).filterMap` fetching
each key's def and building its `enumJob`. `enumJobs_cover`/`_scope` (coverage/scope by
construction, `List.mem_filterMap` + `Option.map_eq_some_iff`), `enumJobs_valid`
(`w3cJobValid_enumJob` per key), `enumJobs_covg` (`w3dJobCoverage_enumJob` per key).
`ReachedByW3dE` — the fully-operational scheduler closure (cascade legs run `enumJobs`, NO
coverage hypotheses in the constructor). `reachedByW3dE_toC` projects it to `ReachedByW3dC`
by induction: the four cascade-leg hypotheses discharged by `enumJobs_*`, store hypotheses
weakened along write prefixes (all fragment hyps threaded as premises since schema/store
are inductive indices — the `reachedByW3dC_edgeHygienic` pattern).

**The payoff.** `graph_correct_w3dE` (`check = sem` at every fully-drained state) and
`reachedByW3dE_inv` (the full 8-clause `Inv` at every state) — one-line corollaries of the
`*_w3d`/`*C` theorems through `reachedByW3dE_toC`. NO `W3dJobCoverage`, `hcover`, `hscope`,
`hjv` hypotheses: the operational chain earns them all. W3d-1c is CLOSED.

**Proof-engineering notes.** (1) `∃ e, S.lookup (k.1,k.2.1) = some e` from the `getD`-map
condition: keep the `cases` on `S.lookup k'` SYNTACTIC (the condition mentions `k'`, the
goal `(k.1,k.2.1)` — defeq but the `cases … : ` generalize matches syntactically), prove a
`have hlksome : ∃ e, S.lookup k' = some e`, then close the defeq goal with it. (2)
`List.mem_filterMap.mpr ⟨k, hk, ?_⟩` leaves `Option.map f (some e) = some (f e)` — `rw [hlk]`
alone does not reduce it; append `; rfl`. (3) `(k.1, k.2.1, k.2.2) = k` is `rfl` (Prod eta),
so `W3cJob.key (enumJob …) = k` and the scope/cover goals close by `rfl`.

**Resume → W3d-2** (two strata, derived-reading-derived — `probeDerived` leaf dispatch,
`rounds = 2`, `_bumped` fan-out to dependent keys, per-stratum shadow/inertness,
`stratify_topological` settle order; relax `hLU`). Then **W4** (full-scope restatement),
then **Phase 6** (graph-model conformance extension, CORRESPONDENCE.md, final review doc).
Detail: HANDOFF "The next task" + ROADMAP "W3d-2".

---

## Session 2026-07-12 (W3d-1c piece B CORE — `W3dJobCoverage` DISCHARGED as a theorem of a state-derived audit enumeration)

Resuming from HANDOFF "The next task — W3d-1c piece B". Six green+pushed increments, all
in the NEW `GraphIndex/CascadeEnum.lean` (+ root import, Audit import + 3 new entries);
`verify.sh` green throughout (build + 0 sorries + zcli + standard-axioms audit + 60
conformance). This session turns `W3dJobCoverage` — carried as a chain-side hypothesis on
every `ReachedByW3dC.cascade` leg — into a THEOREM of a state-derived enumeration
(`w3dJobCoverage_enumJob`). The design was the one pinned in the 11j HANDOFF; it went
through essentially as written, with one simplification (clause (4) needed no new
`wAny`-node lemma).

**The collapse spine (the intellectual core).**
- **`probeNonDerived_concrete_decomp`**: for a star-free subject `s` and star-free object
  name `on`, each operand leaf read decomposes POINTWISE as `probeNonDerived σ ⟨s,r',⟨dt,
  on⟩⟩ = probeNonDerived σ ⟨starSubj s.shape, r', ⟨dt,on⟩⟩ || σ.reach (subjNode s)
  (objNode ⟨dt,on⟩ r') || σ.reach (subjNode s) (wAllNode dt r')`. Proved by unfolding
  `probeNonDerived` and boolean algebra: the concrete subject's probes 2/4 (`wAny`-
  sourced) ARE the star subject's own probes 1/3 (`subjNode (starSubj sh) = wAnyNode
  sh`), the star's probes 2/4 are dead (`name = STAR`); the two concrete-specific probes
  are the residue (16-case `cases … <;> rfl` after guard-simp).
- **`checkFn_eq_coveredFn_of_no_extra`**: a subject triggering NEITHER concrete-specific
  probe at any `computed` leaf reads exactly like its shape-star — `checkFn σ T s dt on
  R e = coveredFn σ T dt on R e s.shape` — by `evalE_computedOnly` congruence (leaf
  reads equal pointwise ⇒ whole `evalE` tree equal, NO monotonicity, exclusion-safe).

**The enumeration read off the state.** `nodeSubj u := ⟨u.type, u.name, u.pred⟩` decodes a
node; `nodeSubj_subjNode : nodeSubj (subjNode s) = s` for EVERY `s` (subjNode only rewrites
the variant — a `'*'` subject already IS its `wAny` node's decode). `leafConcretes σ dt on
e` = plain star-free `σ.nodes` hitting a `computed`-leaf target (`objNode`/`wAllNode`),
decoded; `mem_leafConcretes_of_hit` (a hitting subject is enumerated — its source is a
node via `reach_source_mem_nodes` = edges-closed) + `no_extra_of_not_mem` (contrapositive:
a non-enumerated star-free subject hits no probe) ⇒ `checkFn_eq_coveredFn_of_not_mem`.
`edgeHolders`/`mem_edgeHolders` for clause (1) (by construction — `nodeSubj` recovers the
subject from its variant-only-altered source node).

**The leg context `w3d_leg_context`.** At any `ReachedByW3d` state, for a declared derived
key with untainted leaves and star-free object, rebuilds (a) `hbridge` = the read bridge
`checkFn = sem` (`checkFn_eq_sem_w3d`, subject-generic up to star-BARE), and (b) `hcovDecl`
= "a `sem`-covered star's shape is DECLARED" (`coveredFn_declared` lifted across the shadow:
`checkFn` of a star subject reads only untainted operands, so `checkFn_agree_of_graphRec` +
`shadow_graphRec_agree` slide it to the rules-admitted shadow `σ0` where `coveredFn_declared`
applies). Both from `reachedByW3d_shadow`.

**The four clause discharges + assembly.** Each `W3dJobCoverage` clause is a contrapositive
of `hbridge` through the collapse: `cands_complete_uncovered` (clause 2 — uncovered
`sem`-true bare: `sem s = sem (starSubj s.shape)`, so the star is `sem`-true, so — bare
shape — declared by `hcovDecl`, contradicting uncovered); `negCands_complete` (clause 3 —
covered `sem`-false: `sem s = false` vs star `sem = true`); `uposCands_complete` (clause 4
— `sem`-true userset: the userset star's shape is undeclared, so its coverage is `false`
by `hcovDecl`'s contrapositive — the "dead userset coverage" fell out of `hcovDecl`, no
separate `wAny`-node lemma); `mem_edgeHolders` (clause 1). `enumJob` (bare leaf concretes
∪ edge holders as `cands`, bare leaf concretes as `negCands`, userset leaf concretes as
`uposCands`) + **`w3dJobCoverage_enumJob`** proves all four at any W3d state.

**Proof-engineering notes.** (1) `s.name != STAR` inside `&&` is a `Bool`, not `= true` —
`bne_iff_ne` does NOT fire; feed `beq_eq_false_iff_ne.mpr` facts + `simp only [bne, …,
beq_self_eq_true]` to resolve the guards, THEN `cases` the reach atoms `<;> rfl`. (2)
`(starSubj sh).predicate` reduces to `sh.2` = `s.predicate` by `rfl` — `fun _ => hsb`
serves the star-BARE side condition directly. (3) The clause theorems are parameterized by
`hbridge`/`hcovDecl` (reconstructed by `w3d_leg_context`) so they prove cleanly without
threading the whole fragment-hyp list; the assembly supplies them.

**Resume → W3d-1c piece B TAIL** (HANDOFF "The next task" has the full plan): the
enumerated-cascade restatement — `W3cJobValid (enumJob …)` (the one new lemma:
`reachedByW3d_Rnode_source_name_ne_star`, the star-free analog of the existing
`_source_bare`, same induction) + `hcover`/`hscope`, then restate `graph_correct_w3d` /
`reachedByW3dC_inv` with NO `W3dJobCoverage` hypothesis. Then W3d-2 → W4 → Phase 6.

---

## Session 2026-07-11j (W3d-1c piece A CLOSED — the plain-chain `Inv` REFUTED, the full 8-clause `reachedByW3dC_inv` proved over the coverage chain)

Resuming from HANDOFF "The next task — W3d-1c", piece A (the two EDGE-referencing I6
clauses `negEdgeFree`/`uposEdgeFree`, completing the deferred T2a carry). One green+
pushed increment, all in `GraphIndex/CascadeInv.lean` (+ 3 Audit entries); `verify.sh`
green throughout (build + 0 sorries + zcli + standard-axioms audit + 60 conformance).

**Attack-first — the plain-chain statement is FALSE (statement-scoping finding,
recorded in the CascadeInv header; scratch deleted).** `#eval` against the real
`writeLoggedRules`/`runCascade` on `viewer := member ∖ banned` (`member` carrying a
wildcard `user:*` restriction): `write member(alice) → cascade (cands=[alice], edge
materialised) → write member(user:*) → write banned(alice) → cascade with cands = []
(W3cJobValid but NOT coverage-valid), negCands = [alice]` reaches a fully-drained
(`cascadeKeys = []`) plain-`ReachedByW3d` state whose row reads `neg = [alice]` while
alice's STALE edge survives (a non-candidate is never audited — `reconcileKeyD_edge_char`'s
untouched disjunct): `negEdgeFree` VIOLATED. With `cands = [alice]` (the `W3dJobCoverage`
edge-holder clause) the same chain retracts the edge. So the HANDOFF's tentative route
("lift settledness to ALL `ReachedByW3d` states") was unprovable as scoped — the
coverage clauses are load-bearing for the INVARIANT itself, not just for
`graph_correct_w3d`; the theorem lives on `ReachedByW3dC`.

**The increment — `reachedByW3dC_inv` (the full W3d T2a).**
- **`reachedByW3d_residueDeclared`** (NO fragment hyps): every persisted residue row
  sits at `(objNode ⟨dt,on⟩ R, R)` for a DECLARED derived `(dt,R)`, concrete object —
  rows are written only by passes at their own `W3cJobValid` key (the chain carries
  `hjv`); write legs and `pushDelta` are residue-inert. This is what lets the edge
  clauses fetch the key's `Expr` + `RootBoolean`ness.
- **`reachedByW3dC_edgeHygienic`** — no `neg`/`upos` member reaches its key's R-node,
  at EVERY coverage-chain state (fragment carries exactly as `reachedByW3dC_settled`).
  Chain induction; every case funnels reach through
  `reachedByW3d_reach_collapse_root` (path into the R-node = single edge):
  * write leg: rows write-inert + derived in-edges fixed
    (`writeLeg_derived_inedges_eq`, model-level I5) ⇒ the edge already existed ⇒ IH.
  * cascade, targeted key: `settledComplete_cascade_targeted` lands `SettledKey`,
    whose row verdicts CONTRADICT its edge verdicts — a `neg` member is `sem`-false
    while a (bare, by `reachedByW3d_Rnode_source_bare` + `subjNode_pred`) edge holder
    is `sem`-true; a `upos` member is userset-shaped while every edge source is bare.
  * cascade, untargeted key: row + in-edges verbatim
    (`reconcileJobsD_other_key_fixed` through `runCascade_cases` + `EvalEq`) ⇒ IH.
- **`reachedByW3dC_inv`**: `StructInv` (11i) + `ResidueHygienic` (11i) + the two edge
  clauses assemble the full 8-clause `Inv` at EVERY coverage-chain state — dirty keys
  and mid-drain states included (unlike W3c's `reachedByW3c_inv`, which only saw
  batch-boundary states, and unlike `graph_correct_w3d`, which reads only fully-drained
  states). `Quiescent` was NOT bundled in: mid-drain W3d states are genuinely
  non-quiescent, so it can't join a per-state invariant here.

**Proof-engineering note.** The 11i `subst` pitfall struck again: `subst hr` on
`hr : r = R` ELIMINATES `R`, breaking later mentions — use `rw [hr] at hrow` to
retarget the row instead. Record-update projections (`{σ with watermark := w}.residue`)
need an explicit `rfl`-`have` before `rw` can cross them.

**Second increment — `W3dJobCoverage` clause (2) was UNSATISFIABLE on covering stores
(statement-quality fix, `#eval`-checked, scratch deleted).** Preparing piece B exposed
it: clause (2) demanded EVERY `sem`-true bare star-free subject in `cands`, but under
a covering `T:*` grant every fresh unstored subject of the shape is `sem`-true
(`#eval`: `sem = true` for arbitrary never-mentioned names) — infinitely many, so no
finite job satisfied the clause, the coverage chain admitted NO cascade on covering
stores, and `graph_correct_w3d`/`reachedByW3dC_inv` held there only for write-only
histories (vacuously narrower than advertised, on exactly the stores W3c added). Fix:
clause (2) now carries the same UNCOVERED guard as `CompleteKey`'s edge clause
(covered subjects read through `stars ∖ neg`, never through an edge — and Python's
`_leaf_concretes` only enumerates store-supported subjects). The weakening makes every
`∀`-chain theorem strictly STRONGER; the only consumer (`settledComplete_cascade_
targeted`'s CompleteKey clause-2 leg) already had `hnc` in scope — one-token fix.
Piece B's enumeration is now actually provable-complete against clause (2).

**Resume → W3d-1c piece B** (the audit enumeration; HANDOFF "The next task" carries
the full design pinned this session): route (a) reach-based `leafConcretes`; the key
lemma `checkFn_eq_coveredFn_of_no_extra` (leaf reads decompose pointwise as
`leaf(star) ∨ probe1(s) ∨ probe3(s)`, so a subject with no concrete-specific probe
evaluates exactly like its shape's star — `evalE` congruence, exclusion-safe); all
three completeness clauses = contrapositives of the `checkFn = sem` bridge; clause (1)
by construction from decoded R-node in-edges. Then W3d-2 (two strata) → W4.

---

## Session 2026-07-11i (W3d-1c part 3 STARTED — the deferred `reachedByW3d_inv`, two of its four residue clauses + all four structural clauses discharged)

Resuming from HANDOFF "The next task — W3d-1c". Two green+pushed increments, both in the
NEW `GraphIndex/CascadeInv.lean` (+ root import, Audit import + 6 new entries);
`verify.sh` green throughout (build + 0 sorries + zcli + standard-axioms audit + 60
conformance). Focus: the deferred T2a carry `reachedByW3d_inv` (`Inv` over the
interleaved scheduler chain), the piece W3d-1c point 3. The 8-clause `Inv` splits into a
STRUCTURAL half (`StructInv` — schema, nodeEnc, edgesClosed, acyclic) and the four I6
residue-hygiene clauses; two of the I6 clauses are edge-FREE, two are edge-referencing.
This session discharged the structural half AND the two edge-free I6 clauses, all with
NO fragment hypotheses — leaving `reachedByW3d_inv` reduced to exactly `negEdgeFree` +
`uposEdgeFree`.

**Increment 1 — the structural invariant `reachedByW3d_structInv`.** `StructInv S σ` at
every state of the interleaved chain (empty → logged writes → cascades, any order), NO
fragment hypotheses. **Key observation: acyclicity is FREE on the chain** — every edge
the model adds is a `writeDirect`, which cycle-rejects internally (`admitEdge` back-path
probe via `reach_complete`, `Write.lean`), and every edge the diffing audit removes is a
`removeEdgePair`, which only SHRINKS the edge set (so `NReaches` shrinks,
`NReaches.mono_subset` / `removeEdgePair_edges_subset`). No R-node terminality needed
here. `StructInv` preservation proved for every primitive:
`removeEdgePair` / `reconcileResidueKey` (residue-only) / `reconcileKeyD` (fold of
writeDirect|removeEdgePair) / `reconcileStarsKeyD` / `pushDelta` / `setWatermark` /
`writeLoggedOne` / `writeLoggedRules` (fold) / `applyLogged` / `reconcileJobsL` (fold) /
`runCascade` (accept = batch + watermark bump, both structural no-ops; reject =
identity), then `reachedByW3d_structInv` by chain induction (+ the `ReachedByW3dC`
projection `reachedByW3dC_structInv`).

**Increment 2 — the edge-free I6 clauses `reachedByW3d_residueHygienic`.** At every W3d
state, every persisted residue row satisfies `negStarCovered` (`∀ n ∈ neg,
stars.contains n.shape`) and `uposNegDisjoint` (`∀ n ∈ upos, neg.contains n = false`) —
the two `Inv` clauses that read only the row, NOT the edges — with NO fragment
hypotheses. Both hold of every written row BY CONSTRUCTION: `reconcileResidueKey` writes
`neg = negCands.filter (stars.contains c.shape && ¬checkFn)` and `upos = uposCands.filter
(¬stars.contains c.shape && checkFn)` (`processor.py:406-441`), so a `neg` member's shape
is covered (first filter conjunct) and a `upos` member is uncovered (so it fails the
`neg` filter ⇒ `neg.contains = false`). Chain invariant `ResidueHygienic` folded through
`reconcileStarsKeyD` (self-key = the filtered row via `reconcileStarsKeyD_residue_self` +
`reconcileResidueKey_residue_self`; other keys via `_residue_other` + IH) / `applyLogged`
/ `reconcileJobsL` / `runCascade` / `writeLoggedRules` (residue-inert,
`writeLoggedRules_residue`). Axioms `[propext]` only.

**Why the other two I6 clauses are the genuinely hard remainder** (deferred): `negEdgeFree`
/ `uposEdgeFree` reference the CURRENT edges — a `neg`/`upos` member must have no reach
into its key's R-node. Via `reachedByW3d_reach_collapse_root` (exists) this reduces to
"no derived edge from the member", but the residue row and the current edges can be from
DIFFERENT passes, so closing it needs a W3d MASTER-analog / the settledness content
(`SettledKey`, currently only at fully-drained coverage-chain states) lifted to a
per-key edge-source canonicity at EVERY chain state — the W3c inv proof's `hedge`
canonicity (`reachedByW3c_master`) but re-derived over the interleaved diffing chain.
That is the size of a full increment on its own.

**Proof-engineering notes.** (1) `subst hr` on `hr : r = R` ELIMINATES `R` (keeps `r`),
breaking every later mention of the schema binder `R` — use `rw [hk, hr, …]` to retarget
the residue lemmas instead of `subst`. (2) `Bool.and_eq_true` is a `simp` lemma, not an
`Iff` — `simp only [Bool.and_eq_true] at h` to split `(a && b) = true`; there is no
`.mp`. (3) `set stars := shapes.filter …` / `set neg := negCands.filter …` before
`obtain rfl := Option.some.inj hrow` keeps the row's filter expressions NAMED, so the
membership extraction (`List.mem_filter` + `List.contains_eq_mem` + `of_decide_eq_true`)
stays readable. (4) `runCascade`'s accept branch is `{… with watermark := …}` — a
`structInv_setWatermark` / `residueHygienic_setWatermark` (both `= h`, fields defeq
through the record update) crosses it.

**Resume → W3d-1c remaining:** (a) `negEdgeFree` + `uposEdgeFree` ⇒ full
`reachedByW3d_inv` (the master-analog / settledness lift above); (b) the audit
enumeration model + discharging `W3dJobCoverage` as a theorem (parts 1–2, makes
`graph_correct_w3d` unconditional). Both are full-increment-sized; either order.

---

## Session 2026-07-11h (W3d-1b CLOSED — targeted-key re-settlement, the settledness invariant, `graph_correct_w3d` + T3/T6 `*_w3d`)

Resuming from HANDOFF "W3d-1b (final leg)". Two green+pushed increments, all in the new
`GraphIndex/CascadeSettle.lean` (+ Equiv W3d section, Audit 14 new entries, root import);
`verify.sh` green throughout (build + 0 sorries + zcli + standard-axioms audit + 60
conformance).

**Attack-first (machine-checked `#eval` vs the real `writeLoggedRules`/`runCascade`/
`check`/`sem`; scratch deleted; recorded in the CascadeSettle header).** The NEW
edge-holder coverage clause (`j.cands ⊇ pre-leg edge holders at j's key`) attacked both
ways on `viewer := member ∖ banned`, exactly per the HANDOFF hunt list:
- **Refutation without the clause CONFIRMED**: `write member(alice) → cascade → write
  banned(alice) → cascade with cands = []` reaches a FULLY-DRAINED state (`cascadeKeys
  = []`) reading `check = true ≠ sem = false` — the diff audit keeps a non-candidate's
  stale edge (`reconcileKeyD_edge_char`'s second disjunct). With `cands = [alice]` the
  same chain reads `check = sem`. The clause is load-bearing.
- A job missing an EARLIER same-leg job's added edge is benign (that edge carried a
  `sem`-true guard) — the ∀-holders form is about STALE holders, and is what Python's
  per-pass audit re-enumeration provides (`processor.py:394-441`).

**Increment 1 — chain structure + the coverage chain + targeted re-settlement.**
- Chain-level structure over `ReachedByW3d`: `reachedByW3d_schema`,
  `reachedByW3d_edge_target_ne_bare` / `_bareNode_no_inedge` /
  `_Rnode_source_bare` (write case just rewrites with `writeLeg_derived_inedges_eq`),
  and **the W3d reach collapse** `reachedByW3d_reach_collapse_root` (any path into a
  `RootBoolean` R-node is a single edge — the graph_correct bare branch's reach⇒sem).
- **`ReachedByW3dC`** — the coverage chain (decision: a WRAPPER, `ReachedByW3d`'s shape
  untouched; all W3d theorems transfer via `reachedByW3dC_toW3d`): each cascade leg
  carries `W3dJobCoverage` per job — (1) pre-leg edge holders ⊆ `cands` (the attacked
  clause), (2) `sem`-true bare star-free ⊆ `cands`, (3) covered-but-`sem`-false ⊆
  `negCands`, (4) `sem`-true usersets ⊆ `uposCands`. These are the `sem`-level content
  of `reconcile`'s audit enumeration; proving them about a modeled enumeration is 1c.
- **`CompleteKey`** (the per-key completeness half, mirroring `W3cComplete`'s clause
  shapes): row existence under declared `sem`-coverage, uncovered `sem`-true bare edge,
  `upos` membership, `neg` membership. Transports: `completeKey_writeLeg` (via
  `writeLeg_sem_stable` + row/in-edge fixity) and `completeKey_cascade_untargeted`.
- **`settledComplete_cascade_targeted`**: a cascade leg re-establishes `SettledKey ∧
  CompleteKey` at EVERY targeted key. Split the batch at the LAST targeting job
  (`exists_last_targeting`); its wholesale row and diff audit are guard-read at ITS
  mid-batch state σpre, where the shadow persists (`untaintedShadow_reconcileJobsD`)
  and `checkFn = sem` (`checkFn_eq_sem_w3d`); later jobs never touch the key
  (`reconcileJobsD_other_key_fixed`). Edge soundness composes
  `reconcileStarsKeyD_edge_char` (candidates decided fresh by the `sem`-guard) with
  **`reconcileJobsD_key_edge_sem`** (batch edge origin: `sem`-true or pre-LEG) and the
  edge-holder clause (a pre-leg holder IS a candidate — the stale edge gets audited).
  The reject branch is dead (`runCascade_no_abort`), so the accept form is total.

**Increment 2 — the invariant + `graph_correct_w3d` + corollaries.**
- `sem_nil_derived_false` (a derived key over the EMPTY store is `sem`-false: the
  bridge at the empty admitted base + an edgeless graph has no true probe).
- **`reachedByW3dC_settled`** — the settledness invariant: at every chain state, every
  declared derived key (concrete object) is DIRTY (`∈ cascadeKeys`) or `SettledKey ∧
  CompleteKey`. Write legs: mapped ⇒ dirty; unmapped ⇒ previously-settled (dirty is
  sticky, `cascadeKeys_writeLeg_mono`) ⇒ both transports. Cascade legs: targeted ⇒
  re-settled (increment 1); untargeted ⇒ was settled (dirty would be targeted by
  `hcover`) ⇒ transports.
- `cascadeKeys_nil_of_quiescent`: the fully-drained read scope, produced by every
  accepted cascade (`cascade_drains`).
- **`graph_correct_w3d`**: `check = sem` at every `ReachedByW3dC` state with
  `cascadeKeys = []`, subjects bare/star-BARE/userset, store `BareStarStore` +
  `TtuStarFree`. Derived branches read the settled+complete key (star: linchpin
  declaredness via the W3d shadow + row existence; bare: collapse + settled edges,
  `neg` completeness for the covered fallback; userset: exactly `upos`). Untainted
  branch: `shadow_graphRec_agree` straight into `graphRec_base_eq_bs` (the W3d shadow
  is already rules-ADMITTED — simpler than W3c's reduction).
- T3/T6 at W3d scope (`backend_equivalence_w3d`, `exclusion_effective_w3d`,
  `no_ghost_grant_w3d`) — the scheduler (outbox rows, delta→key fan-out, drain loop,
  cross-transaction stale-edge retraction) is now inside the verified perimeter.

**Deferred:** `reachedByW3d_inv` (the T2a carry over the interleaved chain) — folded
into W3d-1c alongside the enumeration model.

**Proof-engineering notes.** (1) `induction h` (h : ReachedByW3dC/W3d) auto-reverts even
schema-only hypotheses (they mention the motive index `S`) — put EVERYTHING right of the
colon and re-intro per case. (2) The `settledComplete_cascade_targeted` proof never
inducts over the whole batch for the row: `exists_last_targeting` + per-key fixity of
the post-suffix reduces everything to ONE pass at σpre; only the edge-soundness needs
the batch-origin induction (`reconcileJobsD_key_edge_sem`), whose mid-states re-derive
their own shadow/terminality/closedness stepwise from `hsh.closed` — no extra chain
hypotheses.

**Resume → W3d-1c (see HANDOFF "The next task"): the audit enumeration from state +
discharging `W3dJobCoverage`; `reachedByW3d_inv`.**

---

## Session 2026-07-11g (W3d-1b core — fan-out completeness, the untainted-core shadow / W3d read bridge, settledness transport)

Resuming from HANDOFF "W3d-1b (continued): settledness + read bridge". Three green+pushed
increments, all in the new `GraphIndex/CascadeStable.lean` (+ root import, Audit 24 new
entries); `verify.sh` green throughout (build + 0 sorries + zcli + standard-axioms audit +
60 conformance).

**Attack-first (machine-checked `#eval` vs the real `graphRec`/`cascadeKeys`/`sem`; scratch
deleted; recorded in the CascadeStable header).** The fan-out completeness statement was
hunted per the HANDOFF list — every IN-fragment hunt CONFIRMED it (multi-hop userset cones
`dave → group:eng → doc:1#member` incl. 2-hop `group:sub`; sibling computed routing
`editor@doc:3` dirtying the viewer key through decision-1's per-routed-edge rows; bare star
grants dirtying via the routed edge's concrete head — probe-2 sources are irrelevant, only
TARGETS matter; ghost writes onto fresh nodes fuel-inert at closed states; cross-key `excl`
writes). **OUT-of-fragment REFUTATION live**: an object-star write `member@doc:*` flips
probe 3 (`reach (subjNode s) (wAllNode doc member)`) at EVERY object of the type while
mapping NO keys — the routed head is the `wAll` node, name `STAR`, which
`_map_deltas_to_keys` skips (`processor.py:604-605`). Python is immune (its closure's
out-bridges land per-flip rows at CONCRETE ends); the model's decision-1 row reconstruction
has no out-bridges — so plain edge targets (`BareStarStore`'s object-star-freeness) is
load-bearing, threaded as `reachedByW3d_edges_target_plain`. A second attack pass confirmed
`checkFn_eq_sem_w3d`'s EVERY-state scope: guard = `sem` across a 6-write chain with three
deliberately uncascaded mid-transaction states (the DERIVED read goes stale, never the guard).

**Increment 1 — fan-out completeness (contrapositive).** `nreaches_factor` (a new path
factors through a marked edge, rest-of-path from its head); `writeLoggedRules_edge_delta`
(every new edge carries an outbox row above the unchanged watermark at the edge's own
head); `mem_affectedKeys` (intro form of the LeafFamily/`via='computed'` branch);
`reachedByW3d_edgesClosed` + `reachedByW3d_edges_target_plain` (closure/plain-targets over
the whole interleaved chain); **`writeLeg_reach_stable` / `writeLeg_graphRec_stable` /
`writeLeg_checkFn_stable`** — an unmapped derived key's operand reads, hence its pass
guard, are unchanged by a logged write leg. Plus `cascadeKeys_writeLeg_mono` (dirty keys
stay dirty until a cascade — frontier rows persist, reach cones grow).

**Increment 2 — the untainted-core shadow + the W3d read bridge.** The W3a shadow does not
extend over diffing passes; the replacement `UntaintedShadow S σ σ0`: a rules-ADMITTED
state on the CURRENT store agreeing with σ off the derived R-nodes (σ's extra edges all
target terminal `DerNode`s; `shadow_reach_agree` — through-hops die on terminality,
landings mismatch untainted targets). NEW content vs W3c's `CoreEq` shadow: the write-leg
ADMISSION transfer (`shadow_admitEdge_agree`/`untaintedShadow_foldAdmits` — the cycle
probe's back-reach target is a closure subject node, never a `DerNode` under `hterm`), so
the logged fold and the shadow's `writeRules` fold accept the same edges. Cascade legs keep
the shadow with σ0 FIXED (pass edges are DerNode-targeted; removals never hit shadow edges
— `reachedByRules_RootBoolean_no_inedge`). `reachedByW3d_shadow` (induction; store hyps
right of the colon, prefix-weakened). **`checkFn_eq_sem_w3d`: guard = `sem` at EVERY W3d
state**, cascaded or not.

**Increment 3 — settledness transport.** (a) Mid-batch shadows: `untaintedShadow_applyD` /
`untaintedShadow_reconcileJobsD` — every PREFIX state of a cascade's job loop keeps the
shadow, so the read bridge holds MID-BATCH (the tool the targeted-key re-settlement will
consume; `untaintedShadow_cascade` refactored through it). (b) Write-leg representation
fixity: `writeLoggedRules_residue` (rows write-inert) + `writeLeg_derived_inedges_eq` (no
routed edge lands on a `RootBoolean` R-node — stored `(dt,R)` tuples need a `Direct` arm,
rewrite outputs need a rule onto `(dt,R)`, both dead: model-level I5 exclusivity). (c)
**`writeLeg_sem_stable`** — at an UNMAPPED key the write doesn't change `sem` either:
guard = `sem` on BOTH sides (the bridge at both stores; `checkFn_store_irrel` on
`ComputedOnly`) and the guard is stable (fan-out completeness). (d) `SettledKey` (the
soundness-side per-key predicate: row members carry their `sem` verdicts vs the CURRENT
store, derived edges witness `sem`-true bare star-free subjects) transports across write
legs at unmapped keys (`settledKey_writeLeg`) and across cascade legs at untargeted keys
(`settledKey_cascade_untargeted`, via `reconcileJobsD_other_key_fixed`).

**Proof-engineering notes.** (1) `induction h` (h : ReachedByW3d σ S T) auto-reverts even
schema-only hypotheses (`NodupKeys S` mentions the index S) — put them right of the colon
and re-intro per case, like the store hyps. (2) The double-bridge trick in
`writeLeg_sem_stable` converts a GRAPH stability fact into a SEMANTIC one: sem(t::T) =
guard σ' = guard σ = sem(T) — each equality by an already-proved theorem; no new sem-level
induction needed.

**Resume → W3d-1b remaining (see HANDOFF "The next task"): cascade-leg RE-settlement at
targeted keys, the settledness invariant assembly, `graph_correct_w3d`.**

---

## Session 2026-07-11f (W3d-1b attack — add-only pass REFUTED; the DIFFING edge audit; per-key edge exactness)

Resuming from HANDOFF "W3d-1b: fan-out completeness — attack-first". Two green+pushed
increments; `verify.sh` green throughout (0 sorries, standard axioms, 60 conformance).

**THE FINDING (machine-checked `#eval` vs the real `check`/`sem`; scratch deleted;
recorded in the `ReconcileDiff.lean` header + ROADMAP decision 7).** The naive W3d-1b
read statement — `check = sem` at every cascaded `ReachedByW3d` state — is **FALSE over
the add-only pass model** (`reconcileStarsKey`/`reconcileKeyC`). Corpus `viewer :=
member ∖ banned`, bare `user` restrictions, NO star grants: `write member(alice) →
cascade` materialises the derived edge (alice is `sem`-true and UNCOVERED); `write
banned(alice) → cascade` re-maps the viewer key (fan-out worked!), the second pass's
residue recompute runs — but an add-only fold cannot RETRACT the edge whose guard
flipped down, so at a fully-drained state `check = true ≠ sem = false`. Python retracts
it: `reconcile_subject` diffs desired vs materialized and calls `_write_derived(...,
add=False)` on `¬want_edge ∧ has_edge` (`processor.py:359-367`). W3a–W3c were immune
because their chains hold the store FIXED — `checkFn = sem` at every pass start makes a
once-true guard permanently true, so Python's removal branch is dead there; W3d's store
GROWS between cascades and an `excl` operand ADD flips derived guards down. The W3d-1a
attack corpus missed this because its banned subject was star-COVERED (answered by
`stars ∖ neg`, no edge to go stale).

**Increment 1 — the diffing edge audit (`GraphIndex/ReconcileDiff.lean`, new; Cascade
re-greened over it).**
- `removeEdgePair` (filter ALL copies of the pair — the refcount reaching zero; node GC
  modeled away, read-safe, noted in the header) + structural simps.
- `reconcileKeyD` (per candidate: `want = checkFn ∧ ¬covered` ⇒ `writeDirect`, else
  `removeEdgePair`) and the atomic `reconcileStarsKeyD` (residue recompute THEN diffing
  audit). W3c keeps the add-only pass (faithful there — removal branch dead).
- `nreaches_remove_terminal`: an in-edge of a never-source node is only ever a path's
  LAST hop, so removing it breaks no path to any other target — the removal-side
  counterpart of `nreaches_cons_inert`. Gives reach inertness in BOTH directions off
  the pass's terminal R-node (`reconcileKeyD_reach_inert` / `_pres` — NB `_pres`
  genuinely needs `v ≠ R-node` now: retracting reach INTO the R-node is the point).
- Edge soundness (`reconcileKeyD_edge_sound` — the converse "old edges survive" is
  deliberately false now), R-node terminality preservation, outbox/watermark/residue
  untouched, nodes monotone.
- **Cascade.lean re-greened**: `W3cJob.applyD`/`reconcileJobsD`, `applyLogged` now
  diffs, the `EvalEq` spine retargeted (`reconcileJobsL_evalEq` → `reconcileJobsD`),
  outbox soundness / `reachedByW3d_edge_source_ne_R` / `reconcileJobsL_Rnode_not_source`
  / **T5 re-earned** (`runCascade_no_abort`, `cascade_drains`) over the diffing pass.
- Post-fix `#eval` (scratch deleted): the attack scenario now reads `check = sem` at
  every cascaded state; idempotent empty cascade; NO over-removal (bob's edge written in
  the same pass that keeps alice's retracted); the star-covered variant still answers
  wholesale from `stars ∖ neg` with zero edges; star query correct.

**Increment 2 — per-key edge EXACTNESS (the settledness core, in `ReconcileDiff.lean`).**
- `graphRec_reconcileKeyD_inert`: the diffing fold is operand-read-inert for EVERY
  subject at untainted keys (both probe targets differ from the R-node; endpoint
  closure at the fold result DERIVED via `edgesClosed_reconcileKeyD`, not hypothesised).
- `wantEdge` (the `processor.py:359` guard) + `wantEdge_reconcileKeyD_inert`: the guard
  is FOLD-INVARIANT — each candidate's `want` is decided once, at pass start.
- **`reconcileKeyD_edge_char`** (induction with the mid-fold state as the
  singleton-prefix fold; `subjNode_inj_total` separates per-subject histories): after
  the fold, subject `s`'s derived pair is present **iff** `s ∈ cands ∧ g s` or
  `s ∉ cands ∧` it was already present — candidate history is ERASED.
- **`reconcileStarsKeyD_edge_char`** (pass-level): guard at the ORIGINAL state —
  `checkFn` ∧ shape ∉ the freshly-recomputed `stars` row. One full-object pass makes
  the key's edge set exactly right for its enumeration; the wholesale re-settle as a
  theorem. Plus `writeDirect_pair_present` (a wanted uncovered candidate's edge is
  always ADMITTED at a terminal R-node: preds differ, no back-path).

**Structural consequence for 1b (recorded in the Cascade header):** the W3a SHADOW does
NOT extend over diffing passes (a removal is not a W3a reconcile leg), so the W3c
`checkFn = sem` bridge does not transfer pointwise to W3d states. The 1b read bridge
must be re-derived over the interleaved closure — expected route: settledness carries
per-key `sem`-level row/edge characterisations directly (edge exactness + the W3c
per-key filters), with the base equation applied at per-key reconstruction points, not
through a global shadow.

**Proof-engineering notes.** (1) A mid-fold state of `foldl f σ (c :: rest)` is
DEFINITIONALLY `foldl f (foldl f σ [c]) rest` — expressing the step as the
singleton-prefix fold lets every FOLD-level lemma (terminality, closure, guard
inertness) act as its own single-step lemma; no separate one-step variants needed.
(2) `induction h` auto-reverts hypotheses mentioning the motive's indices: the
`nreaches_remove_terminal` `head` case receives `ih : v ≠ r → …` — apply `ih hv`.

**Resume → W3d-1b proper (see HANDOFF "The next task"): fan-out completeness (`sem`
stability off the mapped keys) + the settledness invariant over `ReachedByW3d`.**

## Session 2026-07-11e (W3d design + W3d-1a — the cascade scheduling layer: logged writes, delta→key mapping, `runCascade`, contentful T5)

Resuming from HANDOFF "W3d: design first." Two green+pushed increments: (1) the W3d design
committed to ROADMAP ("W3d — the multi-stratum cascade", modeling decisions 1–6 + sub-staging
1a/1b/1c/2); (2) W3d-1a delivered in new `GraphIndex/Cascade.lean` (+ `Audit.lean` 7 new
entries, root aggregator). `verify.sh` green (build + 0 sorries + zcli + standard-axioms audit
+ 60 conformance). Sorry count held at 0.

**Design-phase attack finding (analytic, recorded in ROADMAP decision 1): per-SEED delta
coalescing is WRONG.** Python emits one outbox row per materialized closure-pair flip; the
model materializes no closure, so rows must be reconstructed. Coalescing to one row per RAW
write fails: a computed rewrite routes the seed onto sibling family nodes (`editor@doc:1`
also lands `viewer@doc:1` under `viewer := editor or …`) with NO graph edge from the seed's
object node to the sibling node — the seed-node reach cone misses the sibling operand key.
Correct unit: one row per accepted ROUTED edge (`writeLoggedOne` inside the `writeRules`
fold), object ends recovered at cascade time as the routed edge head's reach cone (add-only
⇒ superset of the write-time per-flip set ⇒ at worst extra idempotent reconciles).

**Structural finding: the W3a–W3c chain shape cannot host the scheduler.** `ReachedByW3c` is
"one admitted base, then passes" — no write AFTER a reconcile is expressible, but the
scheduler interleaves (write txn → cascade → write txn → cascade). So W3d gets a NEW
interleaved closure `ReachedByW3d` (write legs carry `FoldAdmits`; cascade legs carry job
validity + two-sided key coverage `hcover`/`hscope`), and the W3c master/`Inv` transfer is
NOT pointwise — a mid-chain pass's residue row reflects a PREFIX store, and its current
validity rests on "later writes didn't touch this key's operand cone", which is exactly the
W3d-1b fan-out-completeness content (see HANDOFF "The next task").

**Increment — `GraphIndex/Cascade.lean` (W3d-1a, the scheduling layer).**
- Outbox primitives: `maxOutboxId` (+ fold-max algebra), `nextDeltaId = max maxOutboxId
  watermark + 1` (decision 2: strictly above BOTH — plain `maxId+1` could mint a
  born-drained row), `pushDelta` (+ core-untouched simps, `pushDelta_maxOutboxId`).
- Logged writes: `writeLoggedOne` (emit iff admitted) / `writeLoggedRules`; **`EvalEq`** (the
  read-relevant core: schema/edges/nodes/residue — `CoreEq` is too strong once outboxes
  genuinely differ) with the congruence spine: `admitEdge_evalEq`, `writeDirect_evalEq`,
  `writeLoggedRules_evalEq` (logged core = unlogged `writeRules` — ALL W2 edge facts
  transfer), and the pass side `reconcileResidueKey_evalEq` / `reconcileKeyC_evalEq` /
  `reconcileStarsKey_evalEq` / `reconcileJobsL_evalEq` (logged batch core = `reconcileJobsC`).
- The mapping: `affectedObjects` (row node + cascade-time reach cone), `affectedKeys`
  (declared derived keys reading a candidate object's predicate as a computed operand —
  `_map_deltas_to_keys` LeafFamily branch + `_fan_out` `via='computed'`, fragment-restricted;
  star-named objects excluded per `processor.py:604-605`), `frontierRows`, `cascadeKeys`.
- The logged pass: `W3cJob.key`/`applyLogged` (pass + ONE coalesced row at its derived key —
  faithful because ALL the pass's per-flip rows share that object end by R-node terminality),
  `reconcileJobsL` + watermark/outbox bookkeeping (`reconcileJobsL_outbox_sound`: every row is
  original or a pass row at a job key with id above the pre-batch frontier).
- **`runCascade`** (decision 5): reconcile the mapped keys, then Python's final leftover check
  (`InvariantViolation` at `processor.py:729-739`) as an accept/REJECT branch — reject = state
  unchanged (the abort rolls the transaction back), accept = watermark past everything.
- **T5, contentful, both halves**: `runCascade_no_abort` — on the fragment the reject NEVER
  fires: a leftover row is pass-emitted (outbox soundness + id arithmetic), sits at a terminal
  derived R-node (`reachedByW3d_edge_source_ne_R` re-proved by direct induction over the
  interleaved closure: write-leg sources are rewrite-closure subjects ≠ R via `NoTtuTarget` +
  prefix-weakened `NoStoreSubjectR`; cascade-leg sources are bare candidates ≠ R; plus the
  mid-batch variant `reconcileJobsL_Rnode_not_source`), so its reach cone is empty and its own
  predicate is derived — which no derived def reads as a computed operand (`hLU`) ⇒
  `affectedKeys = []`. `cascade_drains` — the post-cascade state is `Quiescent`, the watermark
  advance EARNED by no-abort, never asserted (the fix for the deleted-as-vacuous
  `cascade_converges` shape).

**Attack-first (machine-checked `#eval` vs the real `check`/`sem`; scratch deleted, recorded
in the Cascade.lean header).** `viewer := member ∖ banned` (`member` admitting `user`,
`user:*`, `group#mem`), 5 logged writes: all 5 frontier rows mapped to the viewer key (direct,
star, userset, group-flow cones); `runCascade` with one covering job ACCEPTED (watermark 0→6),
`Quiescent` held, and the 18-query grid matched `sem` exactly (bare incl. a ghost
concrete-under-star, star, userset subjects). **Cross-key hazard confirmed live**: a
post-cascade `banned` write re-mapped the EXISTING viewer key through the `banned` operand
cone; until the second cascade the derived read was STALE (`check = true ≠ sem = false` for
the newly-banned subject) — so the read-correctness claim scope is CASCADED states (faithful:
Python runs `run_cascade` inside every writing transaction). The second cascade's own pass row
mapped to `[]`; an empty-frontier cascade was a no-op accept. No refutation.

**Proof-engineering notes:** hypotheses mentioning the inductive's indices (`S`, `T`) must sit
RIGHT of the colon or `induction` auto-reverts them into the motive with surprising ih shapes
(`reachedByW3d_edge_source_ne_R` takes `NoTtuTarget`/`NoStoreSubjectR` as explicit arrows, the
store one re-derived per write leg by prefix weakening). `Prod` eta is definitional: `S.lookup
k` vs `S.lookup (k.1, k.2)` interchange freely, so `hLU k.1 k.2 e hlk` typechecks directly.

**Resume → W3d-1b (see HANDOFF "The next task").**

## Session 2026-07-11d (W3c read half step 3 — CLOSED: the linchpin, the batch completeness layer, `graph_correct_w3c`, T3/T6 `*_w3c`)

Resuming from HANDOFF "W3c read half, step 3: the linchpin lemma + `graph_correct_w3c`." Two
green+pushed axiom-clean increments (all in `GraphIndex/ReconcileStarsComplete.lean`, + `Equiv.lean`,
`Audit.lean` [10 new entries]); `verify.sh` green throughout (build + 0 sorries + zcli +
standard-axioms audit + 60 conformance). Sorry count held at 0. **This CLOSES W3c** — the full
read↔`sem` correspondence on star-carrying stores, all three `probeDerived` branches.

**Attack-first (recorded in the file's coverage-section header; scratch deleted).** Small
`viewer := member ∖ banned` corpus with a `user:*` grant, a concrete-under-star exclusion, a
userset member, and a group-routed concrete: (1) the planned `W3cComplete` read = `sem` on the
full grid; (2) a second full same-key pass is idempotent; (3) **NECESSITY finding**: a second
same-key pass whose `negCands` omit the excluded subject DROPS it from `neg` (the residue is a
WHOLESALE per-pass recompute) and the read flips to `true` ≠ `sem` — so the completeness clauses
MUST quantify over **every job targeting a key**, not one covering job (edges are monotone, so
edge coverage stays ∃-form). Faithful to Python: every `reconcile` call re-derives the full audit
enumeration (`_leaf_concretes` ∪ persisted ids). Linchpin sanity re-checked (`coveredFn` true
exactly on the declared shape).

**Increment 1 — the LINCHPIN + row char + batch completeness.**
- `coveredFn_declared` (**the linchpin**, Route 2 graph-level as planned): `coveredFn σ0 sh =
  true → sh ∈ wildcardShapes S`. Chain: `evalE_computedOnly_true_leaf` (a `ComputedOnly` tree is
  true only via a true `computed` leaf) → the star subject's probes leave from its own `wAny`
  node (probes 2/4 dead) → `nreaches_first_edge` → `reachedByRules_edge_sound` (the first edge is
  a materialised closure tuple with `subjNode u.subject = wAnyNode sh`) →
  `rewriteClosure_star_subject` (a star closure member carries its stored seed's subject) →
  `StoreValidRules` + `restrictionMatches`' wildcard flag → `mem_exprRestrictions_of_directs` →
  a `wildcardShapes` entry.
- `w3c_row_char`: on any W3c state, a persisted row reads at `sem` level — `stars.contains sh ↔
  (sh ∈ wildcardShapes S ∧ sem(starSubj sh))` (master + `checkFn_eq_sem_bs` at the master base;
  `hWSbare` makes declared star subjects BARE), `neg` members star-free ∧ `sem`-false, `upos`
  members star-free usersets ∧ `sem`-true.
- `W3cJob.keyMatch`, `reconcileJobsC_row_isSome` (row existence: a targeting job creates the row;
  rows never deleted), `reconcileJobsC_neg_complete` / `reconcileJobsC_upos_complete` (induction
  over the batch: a targeting pass re-derives membership from its own guard — `checkFn = sem` at
  every W3c-reached pass start via `checkFn_eq_sem_w3c`, pass-start `stars` = the canonical
  filter; a non-targeting pass leaves the row; the ∀-targeting-jobs enumeration hypothesis
  carries survival).

**Increment 2 — `W3cComplete` + the assembly + T3/T6.**
- `probeDerived_eq`: the full residue read unfolded on explicit components (star / bare / userset
  branches) at a concrete object.
- `W3cComplete`: admitted base + valid `W3cJob` batch + coverage clauses — edge cands ∃-covering
  (per `sem`-true bare), `upos`/`neg` cands ∀-targeting-jobs (per `sem`-true userset / per
  covered-`sem`-false star-free subject), and row existence (every key with a declared
  `sem`-covered shape is targeted). `w3cComplete_reached`.
- `w3cComplete_derived_edge`: a `sem`-true canonically-UNCOVERED bare's edge materialises — it
  survives the covering job's covered filter (pass-start row = canonical stars, `coveredFn σpre =
  sem` via the bridge), guard `sem`-true at every prefix mid-state (the master pattern:
  W3a-admitted shadow of the pass start + `graphRec_reconcileKey_inert` + `checkFn_congr` across
  the residue half), `reconcileKey_edge_present` at the terminal R-node, edges monotone through
  the tail.
- **T2b `graph_correct_w3c`**: `check = sem` for `W3cComplete` states over `BareStarStore` +
  `TtuStarFree` stores, query scope = concrete object + (concrete ∨ star-BARE ∨ userset) subject
  (`hqs : name = STAR → predicate = BARE`), fragment + `hWSbare` (decision-15: bare-only declared
  wildcard shapes). Branches: star ⇒ `stars` (row char forward; linchpin + row existence
  backward); bare ⇒ edge ∨ (`stars` ∖ `neg`) (reach ⇒ the shadow-collapsed single edge ⇒ master's
  canonical guard ⇒ `sem`; fallback sound by `neg` completeness — `sem`-false would be IN `neg`;
  backward: covered reads from the row, uncovered gets its edge); userset ⇒ `upos` exactly
  (`hWSbare` kills userset coverage: the `stars` gate is always false); untainted ⇒ shadow +
  `graphRec_reduce_base_adm_bs` + `graphRec_base_eq_bs`.
- T3/T6 at W3c scope (`Equiv.lean`): `backend_equivalence_w3c`, `exclusion_effective_w3c` (**a
  concrete subject excluded from UNDER a `T:*` wildcard grant — the space rule's `neg` actually
  excludes**, the headline W3c security content), `no_ghost_grant_w3c`. `Audit.lean`: 10 new
  entries, all `[propext, Classical.choice, Quot.sound]`.

**Proof-engineering notes:** `subst` eliminates the RHS variable — orient equations so the
JOB/∃-bound var is on the right (`have h1' : dt = jdt := h1.symm; subst h1'`). After
`obtain ⟨⟨st,sn,sp⟩, R, ⟨dt,on⟩⟩ := q`, RE-TYPE the query hypotheses (`replace hqs : sn = STAR →
sp = BARE := hqs`) — otherwise they carry unreduced `{…}.object.name` projections that break
later `rw`s. Pass `(s := …)` explicitly when a lemma's implicit subject is only determined
through `s.shape` (unification can't invert `.shape`). `cases hrow : σ.residue …` substitutes
the scrutinee in the goal — don't `rw [hrow]` afterwards.

**Resume → W3d (multi-stratum cascade; see HANDOFF "The next task").**

## Session 2026-07-11c (W3c read half step 2 — the batch layer `ReconcileStarsComplete.lean` + attack-first: the no-ghost-star linchpin identified)

Resuming from HANDOFF "W3c read half steps 2–3." One green+pushed axiom-clean increment (new
file `GraphIndex/ReconcileStarsComplete.lean`); `verify.sh` green (build + 0 sorries + zcli +
standard-axioms audit + 60 conformance). Sorry count held at 0. **This lands HANDOFF W3c read-half
step 2, part 1** (the batch scaffolding + the shadow `checkFn` bridge); the assembly
`graph_correct_w3c` is set up but NOT yet landed — see the precise plan + the linchpin below.

**Increment — the W3c batch layer (`ReconcileStarsComplete.lean`).**
- `checkFn_eq_sem_w3c`: the star-relaxed `checkFn = sem` on ANY W3c state, through the W3a-admitted
  shadow (`reachedByW3c_shadow` + `checkFn_congr` + `checkFn_eq_sem_bs`). Subject-generic up to
  star-BARE — the exact form the `coveredFn`/`stars ↔ sem` correspondence consumes. (The W3b
  analog is `checkFn_eq_sem_w3b`.)
- `reconcileStarsKey_edges_mono` (residue half edge-inert + `reconcileKeyC_edges_mono` through the
  collapse); `W3cJob` (dt/on/R/e/cands/negCands/uposCands — shapes fixed to `wildcardShapes S`),
  `W3cJob.apply` (parametrised by `S` for the fixed shapes), `reconcileJobsC`, `W3cJobValid` (=
  a `ReachedByW3c.reconcileS` leg's side conditions), `reconcileJobsC_pres`,
  `reconcileJobsC_edges_mono`. Mirror of the W3b `W3bJob`/`reconcileJobsB` layer, adapted to the
  COMBINED `reconcileStarsKey` pass (one job settles stars+neg+upos+edges for a key at once — W3b
  split edge and upos into separate job constructors).

**Attack-first — THE LINCHPIN (recorded here; scratch/analysis only, no refutation).** Before
designing the `probeDerived` assembly I traced the three branches (bare ⇒ edge ∨ (stars∖neg),
star ⇒ stars, userset ⇒ upos ∨ (stars∖neg)) against `sem`. **Finding: every branch's
space-rule correspondence needs a "no ghost star coverage" lemma — `coveredFn σ0 sh = true → sh
∈ wildcardShapes S`** (equivalently, a `sem`-true BARE-star subject has a DECLARED wildcard
shape). Reason: `res.stars = (wildcardShapes S).filter (coveredFn σ0)` (master), so
`res.stars.contains sh ↔ (sh ∈ wildcardShapes S ∧ coveredFn σ0 sh)`, while the space rule needs it
`↔ coveredFn σ0 sh` alone (= `sem` at the star subject, via `checkFn_eq_sem_bs`). The two agree
iff coverage implies declaredness. **This lemma is TRUE** — confirmed against the `sem` defs
(`Spec/Semantics.lean`): `restrictionMatches` gates a star grant by the wildcard flag
(`((tup.subject.name == STAR) == r.2.2)`, `:38`), so a stored star grant matches only a
`(type,pred,true)` restriction ⇒ its shape is in `wildcardShapes` (the `exprRestrictions`
wildcard collector); the `directLeaf` star-exact branch (`:66-67`) reads exactly such a grant, and
for a **bare** star the `ttuLeaf` exact-match branch is dead (`s.predicate = BARE ≠ targetRel`,
`:96/99`) so no ttu ghost — the recursion (flow-through / `instances`) preserves the star subject
and bottoms out at that gated directLeaf. The existing userset analog is
`isSWU_of_storeValid` (`UsStarClosure.lean:236`).

**Two proof routes for the linchpin (next session picks one):**
- **Route 2 (graph-level, likely cleaner):** `coveredFn σ0 sh = σ0.checkFn (starSubj sh) …` reads
  `graphRec σ0` at untainted leaves = `reach` from `wAnyNode sh` on σ0. A non-reflexive reach ⇒
  ∃ edge `(wAnyNode sh, y) ∈ σ0.edges` ⇒ (`reachedByRules_edge_sound`) a closure tuple with
  `subjNode = wAnyNode sh` ⇒ (`rewriteClosure_star_subject`/`BareStarStore`/`TtuStarFree`, cf.
  `RulesBareStar.lean`) a STORED bare-star seed of shape sh ⇒ (`StoreValidRules` +
  `restrictionMatches` wildcard flag, cf. `isSWU_of_storeValid`) `sh ∈ wildcardShapes S`.
  `wAnyNode_eq_subjNode` (`RulesBareStar.lean:758`) and `subjNode`-of-star = `wAnyNode` are the
  node glue.
- **Route 1 (sem-level):** turn `coveredFn σ0 sh` into `sem S T ⟨starSubj sh, R, o⟩` via
  `checkFn_eq_sem_bs`, then a `semAux` fuel induction "bare-star true ⇒ declared shape" over
  union/inter/excl/computed/direct/ttu.

**The remaining assembly plan (`graph_correct_w3c`), with the linchpin in hand.** Add fragment
hyps: `hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE` (decision-15 defers userset-star coverage;
makes `starSubj sh` bare so `checkFn_eq_sem_bs` applies to `coveredFn`), `hqbareStar :
q.subject.name = STAR → q.subject.predicate = BARE` (bare-star queries only). Define `W3cComplete`
(base + jobs + `W3cJobValid` + coverage: edge cands ⊇ sem-true uncovered bares, negCands ⊇
neg-leaf concretes ∪ derived-neg ids, uposCands ⊇ sem-true uncovered usersets, AND a **row-
existence** clause: every derived (dt,R)/on with a covered shape or any sem-true member has a job
⇒ the row exists & is canonical by `reachedByW3c_master`). Soundness of all three branches is
NEARLY FREE from `reachedByW3c_master` (rows canonical; edges canonically uncovered+guard-true) +
`checkFn_eq_sem_w3c`/`_bs`; completeness needs the covering job (edge-present via
`reconcileKey_edge_present` through the collapse — note the covered filter drops covered cands, so
a sem-true UNCOVERED bare survives the filter — plus `reconcileJobsC_edges_mono`; upos/stars via
row existence). Star branch: `res.stars.contains s.shape ↔ coveredFn σ0 s.shape` (linchpin) `↔
sem` (bridge, `s = starSubj s.shape` since bare-star). Then T3/T6 `*_w3c` in `Equiv.lean`, and
Audit.lean entries for `graph_correct_w3c` + `checkFn_eq_sem_w3c`.



Resuming from HANDOFF "W3c read half: the star-relaxed base equation." Two green+pushed
axiom-clean increments (new file `GraphIndex/RulesBareStar.lean` ~700 lines; +
`RestrictBase.lean`, `ReconcileComplete.lean`, `Audit.lean` [12 new entries], root aggregator);
`verify.sh` green throughout (build + 0 sorries + zcli + standard-axioms audit + 60
conformance). Sorry count held at 0. **This closes HANDOFF step 1 of the W3c read half**: the
base `hag` equation and the `checkFn ↔ sem` bridge now hold WITHOUT `StarFreeStore`, over
`BareStarStore` + `TtuStarFree`, subject-generically up to star-BARE subjects — exactly the
form the `coveredFn`/`stars ↔ sem` correspondence consumes.

**Attack-first (recorded in `RulesBareStar.lean` header, scratch deleted).** Planned
`graph_correct_rulesBS` vs `sem` on a ~180-query grid over a mixed `computed`/`ttu`/`union`
schema: `user:*` feeding computed arms, D1 star flow-through (`user:* → group:g#mem`), a star
grant on a TTU *target* relation, a D1 chain crossing a rewrite output fed by a star grant,
star-bare + userset subjects, ghosts — zero mismatches; `semAux_star_to_bare` zero violations.
**Necessity of `TtuStarFree` CONFIRMED** (a genuine refutation of the unconditioned statement):
`folder:* → doc:d6#parent` makes `sem` true via `ttuLeaf`'s `instances` branch while the graph
answers false — the rule-routed write model (`writeRules`, a plain `writeDirect` fold)
materialises NO in-bridges; star TTU parents are W1c machinery, deferred. `TtuStarFree S T`
(no TTU arm matches a stored star tuple) is the honest fragment condition.

**Increment 1 — `graph_correct_rulesBS` (`RulesBareStar.lean`).** W2's untainted `check = sem`
over `BareStarStore`, query scope = concrete object + (concrete ∨ star-BARE) subject:
- closure star-characterisation `rewriteClosure_star_subject`/`_star_bare`: no ttu arm ever
  fires on a star-subject closure member (seed case: `TtuStarFree`; output case:
  `no_rewrite_outputs_tupleset`), and computed arms keep the subject — so star closure members
  carry the seed's full bare subject;
- subject-generic soundness: `semAux_seed_bs` (star seeds self-grant via the star branch's
  exact-shape disjunct, `directLeaf_grant_starSelf`), `semAux_of_rewriteClosure_bs`,
  `semAux_lift_untainted_bs` (lift with arm-provenance threading so `ttuLeaf_elim_nss` can
  instantiate `TtuStarFree` per leaf), chain composition `semAux_of_ruleChain_bs` via GLOBAL
  `subjNode` injectivity (`subjNode_inj_total` — star and plain nodes never collide);
- the star→concrete coverage transfer `semAux_star_to_bare` (fuel-for-fuel; `RecLe` +
  `memberOfGranted_mono` reused from FuelStable; probe-2 glue: a `wAny`-source chain IS the
  star-subject chain at `subjNode ⟨T, *, BARE⟩`);
- completeness `nreaches_of_semAux_rulesBS`: probe-1 ∨ probe-2 disjunction (star subject ⇒
  probe 1 at its own `wAny` node; bare ⇒ probe 1 ∨ probe 2; userset ⇒ probe 1; flow-through
  and `nreaches_relation_rewrite_bs` tail both disjuncts);
- assembly: probes 3–4 dead (plain targets), probe-2-dead-for-usersets via
  `rulesAdmitted_edge_endpoints_bs` (sources plain or `wAny`-BARE).

**Increment 2 — the base equation + bridge.** `ttuStarFree_restrict` + `graphRec_base_eq_bs`
(`RestrictBase.lean`): the schema-restriction route verbatim with `graph_correct_rulesBS` as
the untainted black box (`TtuStarFree` transfers to `S↾U` since `schemaRewrites` is
preserved). `graphRec_reduce_base_adm_bs` (`ReconcileComplete.lean`): NO `StarFreeStore` — the
plain-edges shortcut (which killed probes 2–4) is replaced by transferring ALL FOUR probes to
the base: both probe targets (`objNode ⟨dt,on⟩ r'`, `wAllNode dt r'`) carry the untainted key
`(dt, r')`, so `reachedByW3aAdmitted_reach_inert` (never star-dependent) applies per probe.
`checkFn_eq_sem_of_base_bs` + `checkFn_eq_sem_bs`: the composed star-relaxed bridge on
W3a-admitted states, subject-generic up to star-BARE.

**Resume → W3c read half steps 2–3 (see HANDOFF "The next task"):** the `W3cComplete`
batch/coverage layer (jobs = `reconcileStarsKey` passes; an ADMITTED variant of the W3c
closure is likely needed so `checkFn_eq_sem_bs` applies to the canonical base), then the
`graph_correct_w3c` assembly through `probeDerived` (bare ⇒ edge ∨ stars∖neg, star ⇒ stars =
canonical `coveredFn` = `sem` via the new bridge, userset ⇒ upos ∨ stars∖neg) + T3/T6 `*_w3c`.
Fragment hypotheses on the store are now `BareStarStore` + `TtuStarFree` (replacing
`StarFreeStore`).

## Session 2026-07-11 (W3c write half — CLOSED: stars/neg model, covered-filter collapse, T2a with all-contentful I6, guard canonicity)

Resuming from HANDOFF "W3c (star data on derived keys → `stars`/`neg`)." Two green+pushed
axiom-clean increments (new file `GraphIndex/ReconcileStars.lean`; + `Audit.lean` [5 new
entries], root aggregator); `verify.sh` green throughout (build + 0 sorries + zcli + audit
standard-axioms-only + 60 conformance). Sorry count held at 0. **This closes the W3c WRITE
half** (model + T2a + graph-internal correspondence); the READ half (`graph_correct_w3c`)
is blocked on the star-relaxed base equation — see "Resume" below.

**Attack-first (no refutation; recorded in `ReconcileStars.lean` header, scratch deleted).**
Planned model vs `sem` on a 342-query grid: `viewer := member ∖ banned`, `viewer2 := member
∩ editor`, `viewer3 := (member ∩ editor) ∖ banned` over 6 objects with `user:*` grants on
operands — starred subtrahend kills coverage; `and` of starred+unstarred uncovered, of two
starred covered; concrete-only exclusion does NOT defeat `*` (star query true while bob ∈
neg); covered subjects hold ZERO edges; userset-driven `neg` under a star base; star
coverage via **D1 flow-through** (`member@group:h#mem` + `group:h#mem@user:*` — no direct
star grant); nested boolean root. Idempotent; reversed key order + permuted/DUPLICATED
candidate lists agree. Load-bearing modeling discovery: **the compiled star fold
`plan.stars_fn` is pointwise the boolean evaluation on the star subject** (`∪/∩/−` over
leaf star sets = `∨/∧/∧¬` over leaf star membership; a closure leaf's star set is the
graph's star-subject read) — so the model's `stars` is just `shapes.filter (checkFn on
starSubj)`, and ALL `checkFn` machinery applies to coverage.

**Increment 1 — write model + T2a (`ReconcileStars.lean`).** `wildcardShapes` (the
schema-fixed `subject_wildcard_shapes`), `coveredFn` (star-subject `checkFn`),
`reconcileResidueKey` (wholesale stars/neg/upos recompute, one `putResidue`, faithful to
`reconcile` steps 1–3 `processor.py:388-446`), `reconcileKeyC` (covered-guarded edge fold,
`want_edge = should ∧ ¬covered` `:359`), `reconcileStarsKey` (residue-THEN-edges — the
faithful atomic unit; the order is load-bearing). Three structural devices:
1. **Covered-filter collapse** `reconcileKeyC_eq_filter`: the covered guard reads the
   persisted row, which `writeDirect` never touches ⇒ fold-constant ⇒ the W3c edge fold
   IS a W3a `reconcileKey` over the covered-filtered candidates. All W3a fold lemmas
   (edge soundness/guard, monotonicity, reach-inertness, CoreEq) transfer for free.
2. **Shadow projection** `reachedByW3c_shadow` (W3b pattern): residue writes core-inert +
   the collapse ⇒ every W3c state has a W3a-admitted shadow with identical core.
3. **Star-general operand-read inertness** `graphRec_reconcileKey_inert` — NO
   `StarFreeStore`: a reconcile pass adds only edges onto its terminal R-node; ALL FOUR
   `probeNonDerived` probe targets at untainted keys (`objNode ⟨dt',on'⟩ r'`, `wAllNode`)
   differ from it ⇒ the read is pass-invariant, subject-generically (star subjects incl.).
`reachedByW3c_master`: one canonical base `σ0` per chain — operand reads = base reads;
every residue row sits at a derived R-node key with `stars` = the CANONICAL star set
(`wildcardShapes.filter (coveredFn σ0)`); every R-node in-edge is base (killed by
`RootBoolean` no-inedge) or from a canonically-uncovered bare candidate. **T2a
`reachedByW3c_inv`: full `Inv` with ALL FOUR I6 clauses contentful for the first time** —
`negStarCovered` (write-time filter), `uposNegDisjoint` (covered vs ¬covered, same row),
`uposEdgeFree` (userset member vs bare-sourced collapsed edge), `negEdgeFree` (the space
rule cross-pass: a `neg` member is canonically covered, every edge source canonically
uncovered — contradiction). No `StarFreeStore` hypothesis anywhere in the file.

**Increment 2 — guard canonicity.** `reachedByW3c_master` extended: `neg` members are
canonically expr-FALSE, `upos` members canonically expr-TRUE (write-time filters +
`checkFn_agree_of_graphRec`), and every reconcile edge source canonically expr-TRUE
(`reconcileKey_edge_guard` gives the guard at a prefix mid-fold state; the prefix fold is
operand-inert — the mid-state is core-shadowed by a W3a-admitted state built from the
pass prefix — so the mid-state guard = the base guard). The W3c state content is now
FULLY characterized by the base's compiled boolean (`coveredFn σ0`/`checkFn σ0`).

**Resume → W3c read half (the star-relaxed base equation).** What remains for
`graph_correct_w3c`: (1) **`checkFn σ0 = sem` / `graphRec_base_eq` WITHOUT
`StarFreeStore`** — the W2 untainted correspondence re-proved on stores carrying bare
`user:*` grants (wildcard probes 1–2 go live on the base; W1's `graph_correct_bareStar`
has the pure-direct star machinery — compose with W2 rule routing; also needed for STAR
subjects, which `stars ↔ sem` requires — `graphRec_reduce_base_adm`'s star-free
plain-edges shortcut must be replaced by per-probe reasoning, for which the new
star-general inertness is the template); (2) the `W3cComplete` batch/coverage layer
(W3b-style jobs + persistence — residue rows are wholesale-recomputed, so persistence =
canonical-content stability + coverage clauses on the enumeration); (3) assembly through
the (already general) `probeDerived` read. Scope note: userset-star shapes/object
wildcards stay out (decision-15 rejects them on derived relations); `wildcardShapes` only
carries declared bare-subject-star shapes on this fragment.

## Session 2026-07-11 (W3b — CLOSED in one session: `graph_correct_w3b`, userset `upos`, T3/T6 at W3b scope)

Resuming from HANDOFF "W3b (userset subjects → `upos` residue)." Three green+pushed axiom-clean
increments (new files `GraphIndex/ReconcileUpos.lean`, `GraphIndex/ReconcileUposComplete.lean`;
+ `Equiv.lean`, `Audit.lean` [16 new entries], root aggregator); `verify.sh` green throughout
(build + 0 sorries + zcli + audit standard-axioms-only + 60 conformance). Sorry count held at 0.
**This CLOSES W3b** — the W3a bare-subject scope restriction is LIFTED: `graph_correct_w3b` proves
`check = sem` on EVERY star-free query (bare and userset subjects) over a `W3bComplete` state.

**Attack-first (no refutation; recorded in `ReconcileUpos.lean` header, scratch deleted).** On
`viewer := member but not banned` (member = direct ∪ computed editor) with userset grants
(`group:{g,h,i}#mem` member/banned/editor-only, ghosts, the derived key itself as subject): the
planned model's `check` = `sem` on a 180-query grid; bare/userset pass ORDER irrelevant; repeated
pass idempotent; P4 non-leak (a banned member of an upos-true userset stays denied); upos members
do NOT reach the R-node even though userset nodes carry operand out-edges (I6 confirmed). The
load-bearing structural discovery: **the upos fold never touches edges/nodes, so `checkFn` is
CONSTANT across the fold** — no prefix-mid-state bookkeeping (unlike the W3a edge fold, whose guard
sees earlier writes; there it was terminality that saved it, here it is congruence).

**Increment 1 — write model + read collapse (`ReconcileUpos.lean`).** `reconcileUposStep/Key`
(per-candidate insert/remove on the key's `upos` via `putResidue`; faithful to `reconcile_subject`
`processor.py:345-357`, star-free ⇒ `covered=false` ⇒ `want_upos=should`, `want_neg=false`; the
model stores a possibly-empty row where Python deletes it — read-equivalent via `getD`). Congruence
spine `reach_congr → probeNonDerived_congr → graphRec_congr → checkFn_congr` (agreement on
edges+nodes). Whole-fold membership characterization `reconcileUposKey_upos_mem`. `ResidueUposOnly`
+ preservation (writeDirect/reconcileKey/reconcileUposKey). W3b read collapse `probeDerived_uposOnly`
/ `check_derived_uposOnly` (star ⇒ false, userset ⇒ `upos.contains`, bare ⇒ W3a edge probe).

**Increment 2 — closure + shadow + soundness (`ReconcileUposComplete.lean`).** `CoreEq`
(residue-blind state agreement) with congruences (`writeDirect_coreEq`, `reconcileKey_coreEq`).
`ReachedByW3b` (admitted base + interleaved bare-edge/upos legs; `reconcileU` side conditions
faithful to the userset branch). **The shadow projection `reachedByW3b_shadow`** — every W3b state
has a W3a-admitted shadow with identical core (replay minus upos passes) — the session's key
economy: ALL W3a edge/reach facts (reach collapse, R-node terminality, derived-edge soundness,
`checkFn_eq_sem`) transfer with ZERO new induction. Residue provenance (rows only at derived
R-node keys; members concrete usersets). **T2a `reachedByW3b_inv`**: full `Inv` with contentful I6
— `uposEdgeFree` proved for real (userset-shaped member vs single bare-sourced edge onto the
`RootBoolean` R-node), `neg` clauses by emptiness; quiescence. `checkFn_eq_sem_w3b`
(subject-generic). **`upos` soundness** `reachedByW3b_upos_sound` (entry ⇒ `sem`; the guard at the
W3b pass-start state, no prefix machinery needed by fold-constancy).

**Increment 3 — completeness + assembly + Step C.** `W3bJob` (edge|upos) / `reconcileJobsB` /
validity / preservation / edge-monotonicity (upos jobs edge-inert). **`upos` persistence**
`reconcileJobsB_upos_persist` — a `sem`-true entry survives every later valid job (edge jobs never
touch residues; a same-key upos re-reconcile re-evaluates its fold-constant guard = `sem` = true ⇒
re-adds, never removes). `W3bComplete` (admitted base + coverage-complete batch: edge jobs
enumerate every `sem`-true BARE subject, upos jobs every `sem`-true USERSET — faithful to the
audit enumeration `processor.py:413-441`). `w3bComplete_derived_edge` (the W3a argument through
the covering edge job, shadow-transferred terminality) + `w3bComplete_derived_upos` (covering job
writes; persistence carries). **`graph_correct_w3b`** — untainted via shadow + base reduction,
derived-bare via edge probe, derived-userset via `upos`. **Step C**: `backend_equivalence_w3b` /
`exclusion_effective_w3b` / `no_ghost_grant_w3b` — T6a now covers a userset excluded by a derived
`but not` (P4 non-leak, both directions).

**Resume → W3c (star data → `stars`/`neg`).** See HANDOFF "The next task": attack-first the
star×boolean fold (`plan.stars_fn`) + `neg` recompute vs `sem`; the expensive half is relaxing
`StarFreeStore` (consider sub-staging W3c-i stars-on-derived-key-only vs W3c-ii star grants in
operand cones). The shadow-projection pattern survives (stars/neg writes are `putResidue`-only).

## Session 2026-07-11 (W3a Step B + C — CLOSED: `graph_correct_w3a`, T3/T6 at W3a scope)

Resuming W3a Step B from HANDOFF "candidate completeness + assembly." Three green+pushed
axiom-clean increments (new file `GraphIndex/ReconcileComplete.lean` + `Equiv.lean` + `Audit.lean`);
`verify.sh` green throughout (build + 0 sorries + zcli + audit standard-axioms-only + 60
conformance). Sorry count held at 0. **This CLOSES W3a** — the derived-boolean read correspondence
is proved end-to-end and the T3/T6 corollaries lifted.

**Attack-first (recorded a scope finding).** `#eval` on `viewer := member but not banned` with a
userset grant `doc:1#member@group:g#mem`: `sem ⟨group:g#mem, viewer, doc:1⟩ = true` (member ∧ ¬banned)
while the graph's residue-empty `probeDerived` reads a userset subject as `false`. So W3a's
derived-query correctness is **bare-subject only** — userset subjects on a derived key are exactly
W3b's `upos` residue. `graph_correct_w3a` is scoped to `q.subject.predicate = BARE`; the untainted
half stays subject-general (base reduction). Scratch deleted.

**Increment 1 — the `checkFn ↔ sem` bridge.** `semAux_qirrel` (`sem` never reads the query except
through `instances`, which discards it — so the operand `sem` at query `⟨s,r',o⟩` feeds
`checkFn_eq_semStep`'s enclosing query `⟨s,R,o⟩`). `ReachedByW3aAdmitted` (admitted base leg;
`hlke` def-lookup added to the reconcile constructor) + `reachedByW3aAdmitted_toW3a` (forgets to the
plain W3a closure, so all soundness lemmas transfer) + `graphRec_reduce_base_adm` (the admitted
analog of `graphRec_reduce_base`: the operand read reduces to an *admitted* base). **`checkFn_eq_sem`**
— on a W3a-admitted state, `checkFn` at a `ComputedOnly` derived key (untainted leaves) equals
`sem S T ⟨s,R,⟨dt,on⟩⟩` — composing `graphRec_reduce_base_adm` + Step A's `graphRec_base_eq` +
`semAux_qirrel` + T0a fuel stability.

**Increment 2 — derived-edge soundness (forward).** `reconcileKey_edge_guard` (every reconcile-fold
edge is pre-existing or materialised at a *prefix mid-state* whose `checkFn` guard held);
`reachedByRules_RootBoolean_no_inedge` (a `RootBoolean` R-node has no base in-edge, so the base leg
is vacuous). **`reachedByW3aAdmitted_derived_edge_sound`** — a materialised derived edge witnesses
`sem = true` (base leg vacuous; reconcile guard at a W3a-admitted mid-state ⟶ `checkFn_eq_sem`).

**Increment 3 — candidate completeness (backward) + assembly + Step C.** `reconcileKey_edge_present`
(a `sem`-true bare candidate's edge is materialised: guard fires at every prefix mid-state via
`checkFn_eq_sem`; the write admits because the `RootBoolean` R-node is terminal ⇒ no back-path;
persists to the pass end). `W3aJob`/`reconcileJobs`/`W3aComplete` — an admitted base + a
**coverage-complete** batch of reconcile jobs (faithful to `reconcile`/`_leaf_concretes`,
`processor.py:382-423,497-507`: the coverage clause is a property of the *enumeration*, not the edge
conclusion). **`w3aComplete_derived_edge`** (`sem`-true ⇒ edge present: the covering job writes it,
`reconcileJobs_edges_mono` persists it). **`graph_correct_w3a`** — `check = sem` on every
bare-subject star-free query: untainted via the base reduction (`graphRec_reduce_base_adm` +
`graphRec_base_eq`), derived via the residue-empty edge probe (`check_derived_ResidueEmpty`) glued by
soundness (reach ⟶ `reachedByW3a_reach_collapse_root` ⟶ edge ⟶ `sem`) and completeness (`sem` ⟶ edge
⟶ reach). `isDerived_declared` supplies the def. **Step C:** `backend_equivalence_w3a` /
`exclusion_effective_w3a` / `no_ghost_grant_w3a` in `Equiv.lean` (T1 ∘ `graph_correct_w3a`); T6a's
first real exclusion content.

**Resume → W3b (userset subjects → `upos` residue).** See HANDOFF "The next task": attack-first the
`upos` read/write path FIRST, then relax the residue-empty closure to a `upos`-carrying residue and
widen the coverage/completeness to `upos` membership. `checkFn_eq_sem` is already subject-generic.

## Session 2026-07-11 (W3a Step A — CLOSED: state transfer + base `hag` equation)

Resuming W3a Step A from HANDOFF "the remaining Step A: state transfer + base `hag` equation."
Two green+pushed axiom-clean increments (both in `GraphIndex/RestrictBase.lean` + `Audit.lean`);
`verify.sh` green throughout (build + 0 sorries + zcli + audit standard-axioms-only + 60
conformance). Sorry count held at 0. **This CLOSES Step A** — the mixed-schema `hag` base
correspondence is now a single reusable theorem.

**Increment 1 — the state transfer (`exists_admitted_restrict`, `foldAdmits_of_acyclic`).** The
roadmap's flagged "open subtlety": σ0 (admitted over mixed `S`) and its restricted counterpart σ'
(over `S↾U`) fold `writeDirect` over DIFFERENT lists (`rewriteClosure S t` vs `rewriteClosure
(S↾U) t`, differing by fuel/dups), and admission (`FoldAdmits`, cycle-rejection) is order-sensitive
— so the states are not literally equal. **The bridge:** admission depends only on the *final* edge
relation being acyclic. `foldAdmits_of_acyclic` — a `writeDirect` fold admits every write provided
each materialised edge lands in an acyclic target `Ef` already containing the running edges (a
self-loop is a 1-cycle in `Ef`; a back-path `b →* a` plus the new `a → b` is a cycle in `Ef`; the
write keeps the running edges inside `Ef` via `writeDirect_edges`). It is order-insensitive — the
only input from the list is its *set* of materialised edges. `exists_admitted_restrict` then builds
the canonical `ReachedByRulesAdmitted σ' (S↾U) T` by induction on the write path: at each step the
target `Ef := σ0.edges` is acyclic (`Inv.acyclic`), σ'-prev sits inside it (edge-IH + writeRules
monotonicity), and every restricted-closure write materialises there (fuel bridge `⊆` +
`reachedByRulesAdmitted_edge_complete`). Edge agreement of the finished σ' vs σ0 is then immediate
from the two edge characterizations (`reachedByRules_edge_sound` / `…Admitted_edge_complete`) + the
fuel bridge — no reference to intermediate states.

**Increment 2 — the base `hag` equation (`graphRec_base_eq`).** On an admitted rule-routed `σ0`
over mixed `S` and untainted operand `r'`: `graphRec σ0 s dt on r' = sem S T ⟨s,r',⟨dt,on⟩⟩`. Chain:
`graphRec σ0 = probeNonDerived σ0` (def) `= probeNonDerived σ'` (edge agreement ⇒ per-node `reach`
agreement, `probeNonDerived` being a disjunction of `reach` probes) `= check σ'`
(`check_eq_probeNonDerived`, `S↾U` untainted) `= sem (S↾U) T q'` (`graph_correct_rules` over `S↾U`
as a black box) `= sem S T q'` (`semAux_restrict` at `fuelBound S T`, then `sem_fuel_stable` over
the untainted `S↾U` to bridge `fuelBound (S↾U) T ≤ fuelBound S T`). The W2 restriction hypotheses
transfer: WF/TtuTuplesetsDirect by `defs`-subset, RewriteRanked by `rewriteRanked_restrict`,
StoreValidRules by `restrictUntainted_lookup` given stored relations untainted — which the fragment
premise **`hRootB`** (every derived def `RootBoolean`, superseding the old `hDrop`) forces: a
derived def would be `RootBoolean` ⇒ `exprDirects = []` ⇒ no `Direct` arm for `StoreValidRules` to
match. **Wiring note:** RestrictBase now imports `ReconcileCorrect` (for `graphRec`/`RootBoolean`/
`exprArms_rootBoolean`); no cycle (only `Audit.lean` imports RestrictBase).

**Attack-first.** Both increments are THEOREM consequences of already-attack-verified facts (the
fuel bridge, `semAux_restrict`, `graph_correct_rules`), so low refutation risk; the genuinely new
content (acyclic-admission, the reach/probe congruence) is combinatorial. No refutation.

**Resume → Step B (candidate completeness + assembly `graph_correct_w3a`).** See HANDOFF "The next
task." Feed `graphRec_base_eq` (needs an *admitted* W3a base) through `graphRec_reduce_base` — whose
`hag` half currently yields a `ReachedByRules` (not admitted) base, so either re-cut it to hand back
`ReachedByRulesAdmitted`, or prove the reduction preserves admission. Then edge-provenance
(`reconcileKey` peel), the admitted W3a closure `ReachedByW3aAdmitted`, and the derived/untainted
query assembly.

## Session 2026-07-11 (W3a Step A — the fuel bridge, closed both directions)

Resuming W3a Step A from HANDOFF "the fuel bridge is the one remaining subtlety." Three
green+pushed increments (all in `GraphIndex/RestrictBase.lean` + `Audit.lean`); `verify.sh`
green throughout (build + 0 sorries + zcli + audit standard-axioms-only + 60 conformance).
Sorry count held at 0. **This closes the fuel bridge — the crux the roadmap named** — so the
two canonical rewrite closures now have provably identical membership.

**The result — `rewriteClosure_restrict_mem_iff`.** `rewriteClosure S t` (fuel `|S.keys|+1`)
and `rewriteClosure (S↾U) t` (smaller fuel `|S↾U.keys|+1`) have identical membership on the W3a
fragment. Both are the SAME `S`-closure recurrence at two fuels (via `rewriteClosureAux_restrict`
from the prior session); the bridge is that the extra fuel adds nothing.

**Increment 1 — the `⊇` half (unconditional).** `rewriteClosureAux_mono` (more fuel never drops
a member — a member sits at some `stepN` layer `k ≤ n`, re-embedded at any `m ≥ k`, via the
existing `RulesSaturate` layer algebra `stepN_of_mem_aux` / `mem_aux_of_stepN`);
`restrictUntainted_keys_length_le` (`|S↾U.keys| ≤ |S.keys|`, filtered defs are a sublist, `map`
preserves length); `rewriteClosure_restrict_subset` composes them — the smaller closure embeds in
the bigger.

**Increment 2 — the `⊆` half (via saturation + rank compression).** The bigger closure adds no
new members past the smaller fuel because the `S↾U`-closure is SATURATED (closed under one more
`rewriteStep S`), so it swallows every `S`-closure layer (`rewriteClosure_subset_restrict`, layer
induction: seed at layer 0, each further step swallowed). Saturation needs
`RewriteRanked (S↾U)`, built from `RewriteRanked S` by **rank compression**
(`rewriteRanked_restrict`): reuse `S`'s rank `rrank`, compress to `restrictRank k :=`
`|{j ∈ S↾U.keys : rrank j < rrank k}|` — now bounded by `|S↾U.keys|` (`length_filter_le`) and
still strictly increased at each arm (`length_filter_lt_of_mem`, the strict filtered-length
monotonicity: the match key `a` is counted by the out-key threshold but not its own). The one
faithful side condition **`RewriteMatchDeclared S`** (every rewrite's match key
`(objectType, matchRel)` is a declared untainted relation) makes `a ∈ S↾U.keys` so the strictness
fires; it mirrors the compiler routing arms over declared operand relations, and must be
discharged in the fragment assembly (a clearly-flagged hypothesis, NOT a postulate of the
conclusion).

**Housekeeping.** A stray `Scratch_chk.lean` (an `import Mathlib` lemma-signature probe) leaked
into increment 2's commit when its cleanup was killed by a build timeout; removed in a follow-up
commit (library builds the `ZanzibarProofs` target, so `verify.sh` was never affected).

**Attack-first.** The bridge is a THEOREM consequence of `schemaRewrites` equality (attack-first
verified last session) + saturation, so lower refutation risk; the genuinely new facts (fuel
monotonicity, the key-count bound, rank compression) are pure combinatorics. No refutation.

**Resume → the remaining Step A: state transfer + base `hag` equation.** The fuel bridge gives
closure-membership equality; edges of a `ReachedByRulesAdmitted` state are EXACTLY the
materialised closure tuples (`reachedByRules_edge_sound` ⊆ + `reachedByRulesAdmitted_edge_complete`
⊇), so equal closure membership will give equal edges. **The open subtlety:** build a canonical
`ReachedByRulesAdmitted σ' (S↾U) T` and show `σ'.edges ≈ σ0.edges` — the states fold `writeDirect`
over DIFFERENT lists (`rewriteClosure S t` vs `rewriteClosure (S↾U) t`, differing by fuel/dups),
so the states are not literally equal; the transfer must go through the edge-membership
characterization, and `FoldAdmits` must transfer across the differing fold lists (fewer/equal
edges ⇒ still no cycle rejection). Then the base `hag` equation: `graphRec σ0 = probeNonDerived σ0`
`= check σ'` (edges agree) `= sem (S↾U) T q'` (`graph_correct_rules`) `= sem S T q'`
(`semAux_restrict` + fuel). Then Step B (candidate completeness + assembly) and Step C (T3/T6).

## Session 2026-07-11 (W3a Step A — the `hag` base reduction: schema restriction + `semAux` transfer + rewrite-preservation)

Resuming W3a from HANDOFF "Step A — discharge `hag` on the base" via the recommended
schema-restriction route. Two green+pushed axiom-clean increments (new file
`GraphIndex/RestrictBase.lean` + `Audit.lean`); `verify.sh` green throughout (build + 0 sorries
+ zcli + audit standard-axioms-only + 60 conformance). Sorry count held at 0. This lands the
**semantic heart** of Step A (the ledger's "genuine remaining core") plus the schema-combinatorial
groundwork for the state transfer.

**Attack-first (machine-checked `#eval` on a mixed `admin but not suspended` schema, then
deleted).** Confirmed the three route claims computationally before proving: taint isolates
exactly the derived key (`taintedKeys Smix = [(doc,can)]`), `schemaRewrites Smix =
schemaRewrites (restrictU Smix)` (the derived key is `RootBoolean`, emits no arms), and `semAux`
agrees on every operand relation (admin/viewer/suspended) at fuel 20. No refutation — statements
survived, then proved.

**Increment 1 — schema restriction + `semAux` transfer (`RestrictBase.lean`).**
- `restrictUntainted S` (`S↾U`): drop every tainted-key def, keep object-wildcards. Membership /
  subset / `NodupKeys`-preservation (`List.filter_sublist`-map-sublist).
- `untaintedSchema_restrict` (under `NodupKeys`): `S↾U` is untainted — a kept def has an untainted
  key, so its expr is boolean-free (`untainted_closed` ⇒ `baseTaint = false`, and `NodupKeys` makes
  `baseTaint` read exactly this def's `containsBool`). `isDerived_restrict` collapses.
- `restrictUntainted_lookup` (under `NodupKeys`): the schemas agree at every untainted key (declared
  ⇒ its unique def is kept; undeclared ⇒ both `none`).
- **`semAux_restrict` (the heart):** at every untainted key `(t,r)` and every name `m`, `semAux S`
  and `semAux (S↾U)` coincide (any fuel). Fuel induction: at an untainted key the two schemas'
  defs coincide (`restrictUntainted_lookup`), then `evalE_congr` (Confine) closes the step because
  `evalE` consults `rec` only at that def's `exprRefs`, all untainted by heredity
  (`untainted_closed`), where the IH supplies agreement. **Reduces the mixed-schema `hag` to a
  whole-schema-`UntaintedSchema` W2 fact over `S↾U` — `graph_correct_rules` as a black box.**

**Increment 2 — rewrite fan-out preserved (`RestrictBase.lean`).** The graph write path reads the
schema only through `schemaRewrites` (`writeDirect`/`admitEdge`/`reach` schema-blind).
- `filter_flatMap_eq`: flat-map over a filtered list is unchanged when removed elements map to `[]`.
- `schemaRewrites_restrict` (given the fragment fact `hDrop`: every tainted def emits no arms —
  `RootBoolean` ⇒ `exprArms_rootBoolean`): `schemaRewrites (S↾U) = schemaRewrites S`.
- `rewriteStep_restrict`; `rewriteClosureAux_restrict`: the bounded closure is preserved at ANY
  fixed fuel (pure structural — reads the schema only via `rewriteStep`).

**Resume → finish Step A's state transfer + assembly (the fuel bridge is the one remaining
subtlety).**
1. **The fuel bridge (the crux).** The canonical closures run at DIFFERENT fuels: `rewriteClosure
   S t` at `|S.keys|+1`, `rewriteClosure (S↾U) t` at the smaller `|S↾U.keys|+1`. With
   `rewriteClosureAux_restrict`, `rewriteClosure (S↾U) t = rewriteClosureAux S (|S↾U.keys|+1) [t]`,
   so the goal is **membership equality of the two S-closures across the fuel gap**. Both saturate:
   `rewriteClosure_saturated` (RewriteRanked S) gives the `|S.keys|+1` side; the `|S↾U.keys|+1`
   side needs that a rewrite chain from a stored (⇒ untainted, `exprDirects_rootBoolean` +
   `StoreValidRules`) seed STAYS untainted (an arm's `outRel` is its def's relation; tainted defs
   emit no arms ⇒ no rule outputs a tainted relation) and so has depth ≤ `|S↾U.keys|`. Formalize
   as either `RewriteRanked (S↾U)` (a rank compressed to `S↾U`'s key count) or a direct
   "untainted-cone saturates at `|S↾U.keys|+1`" lemma.
2. **State transfer.** On the fully-*admitted* write path (`FoldAdmits` ⇒ no cycle rejection), a
   `ReachedByRulesAdmitted` state's edges are characterized EXACTLY by `reachedByRules_edge_sound`
   (⊆) + `reachedByRulesAdmitted_edge_complete` (⊇): `(a,b) ∈ σ.edges ↔ ∃ t∈T, ∃ u ∈ rewriteClosure
   S t, materialise`. With (1) giving `rewriteClosure S t ≈ rewriteClosure (S↾U) t` (membership),
   build the canonical `ReachedByRulesAdmitted σ' (S↾U) T` and show `σ'.edges ≈ σ.edges`
   (membership). `reach` depends only on edge membership (`reach_iff_nreaches` + `edgesClosed`).
3. **Base `hag` equation.** `graphRec σ0 s dt on r' = probeNonDerived σ0 ⟨s,r',⟨dt,on⟩⟩`
   (`probeNonDerived_plainEdges`, plain edges) `= check σ' q'` (edges agree, `S↾U` untainted routes
   to the probe) `= sem (S↾U) T q'` (`graph_correct_rules` over `S↾U`) `= sem S T q'`
   (`semAux_restrict` + untainted-schema fuel stability to bridge `fuelBound (S↾U)` vs `fuelBound
   S`). This is `hag` for the untainted operands; compose with `graphRec_reduce_base`. NB the
   W3a base is currently `ReachedByRules` (not `…Admitted`) — the completeness (backward) half
   needs an admitted W3a closure, which is **Step B**'s `ReachedByW3aAdmitted`; Step A can land the
   soundness half + the equation over an *admitted* base as the reusable fact.
4. Then Step B (candidate completeness + assembly `graph_correct_w3a`) and Step C (T3/T6 widening).

## Session 2026-07-11 (review/cleanup + handoff restructure + `hag` leaf-restriction fix)

A consolidation session (user-directed): review everything for truth/cleanliness, fix
weirdness, and restructure the docs so future sessions resume from a small, precise entry
point. `verify.sh` green throughout; sorry count held at 0; one substantive proof fix landed.

**The substantive fix — `checkFn_eq_semStep`'s `hag` was UNDISCHARGEABLE as stated.** It
demanded `∀ r', graphRec σ s dt on r' = semAux … r'` — agreement at EVERY relation string,
including the derived `R` itself and unrelated/derived keys — but `graphRec_reduce_base` (and
any per-relation W2 restatement) can only ever supply it for *untainted* operands. The
assembly would have hit a wall. Fixed by restricting `hag` to the def's `computed` leaves:
new `computedRefs : Expr → List String`; `evalE_computedOnly` and `checkFn_eq_semStep` now
take `hag : ∀ r' ∈ computedRefs e, …`. The assembly needs only the fragment fact "every
computed leaf of a derived def is untainted" to compose with `graphRec_reduce_base`.

**Cleanups.**
- **Deduplicated node-projection simp lemmas** — `subjNode_pred` was declared IDENTICALLY in
  `ObjStarClosure.lean` and `ReconcileCorrect.lean` (both imported by `Audit`); all four
  projections (`subjNode_type`/`_pred`, `objNode_type`/`_pred`) now live once in `State.lean`
  next to the node constructors; local copies deleted.
- **Renamed `probeNonDerived_starFree` → `probeNonDerived_plainEdges`** (it takes only the
  plain-edges hypothesis; the star-free name was stale after the strengthening).
- **Stale docs fixed:** `README.md` (claimed "No Lean written yet"), the plan doc's header
  (claimed "not yet started"), ROADMAP's tail ("T4 blocker: do this first" — T4 closed).

**Handoff restructure (the main deliverable).** New **`formal/HANDOFF.md`** — the single
compact entry point a fresh session reads first: state-of-the-world theorem inventory, house
rules (honesty norm / attack-first / green gate / rhythm), build commands + Lean gotchas, the
precise NEXT TASK (W3a steps A/B/C with the recommended schema-restriction route for `hag`),
and the after-W3a road (W3b/c/d, W4, Phase 6). All other docs re-pointed at it (this file's
header, ROADMAP header, README orientation, plan-doc header). This file remains the
append-only ledger; end-of-session duty is now: session entry here + refresh HANDOFF's
"next task".

## Session 2026-07-11 (W3a read correspondence — the operand-read reduction to the untainted base)

Resuming W3a from "the multi-pass inertness fold (`reachedByW3a_reach_inert`) done; resume →
point 2 step 2, discharge `hag` (the per-relation untainted-correctness lemma, the deeper
blocker)." One green+pushed axiom-clean increment (`GraphIndex/ReconcileCorrect.lean` +
`State.lean` + `ReconcileWrite.lean` constructor + `Audit.lean`); `verify.sh` green throughout
(build + 0 sorries + 60 conformance + audit, standard axioms only — one new theorem axiom-free).
Sorry count held at 0. This lands the **reachability core of the `hag` reduction**: the operand
read `graphRec σ s dt on r'` W2's per-relation correctness consults now reduces, on the full W3a
state, to the read on the untainted base — leaving `hag` a *pure base-state* W2 fact with no
residual W3a-specific reasoning.

**The increment.**
- **`NReaches.mono_subset` (`State.lean`, axiom-free)** — general subset monotonicity of
  reachability (`edges ⊆ edges' → NReaches edges → NReaches edges'`), the edge-set-inclusion
  generalisation of the single-edge `NReaches.mono`. The reverse direction of the inertness
  transfer.
- **`reachedByW3a_reach_inert` strengthened** to also expose `σ0.edges ⊆ σ.edges` (reconcile
  passes only add edges — `reconcileKey_edges_mono` folded). **`reachedByW3a_reach_inert_iff`** —
  the biconditional: reachability into any untainted-key node agrees between the full W3a state
  and the untainted base (forward = the inertness fold; backward = `NReaches.mono_subset` on the
  subset inclusion).
- **`ReachedByW3a.reconcile` gained two faithful star-free fields** — `hcStar` (each candidate
  subject `c.name ≠ STAR`) and `honStar` (the reconciled object name `on ≠ STAR`). Faithful to the
  W3a star-free fragment (reconcile candidates are the `_leaf_concretes`, run per concrete object).
  They keep every reconcile edge's endpoints *plain*. The 7 `reconcile` match sites gained the two
  placeholders.
- **`reachedByW3a_edges_plain`** — every W3a edge endpoint is a plain node (base = rewrite-closure
  tuple names inherit the star-free store; reconcile = star-free candidate/object via the new
  fields). **`probeNonDerived_starFree`** (since renamed `probeNonDerived_plainEdges`) — a plain-edge read collapses to probe 1 (wildcard probes
  2–4 dead); strengthened vs `graph_correct_rules`'s inline version to need **only** plain edges
  (the query-star-free hypotheses drop out).
- **`graphRec_reduce_base` (the payoff)** — for every untainted operand relation `r'`
  (`isDerived S (dt, r') = false`), `graphRec σ s dt on r' = graphRec σ0 s dt on r'` on the
  untainted base `σ0`. Both reads collapse to probe 1 (plain edges on both states); the target
  `objNode ⟨dt,on⟩ r'` is an untainted-key node, so `reachedByW3a_reach_inert_iff` equates the two
  reachabilities. **Reduces `hag` to the base per-relation fact `graphRec σ0 s dt on r' = sem`.**

**Resume → close the W3a CORRESPONDENCE. `hag` is now a pure W2 base-state fact:**
1. **Discharge `hag` on the base — the per-relation untainted-correctness lemma (the remaining
   blocker, now W3a-free).** With `graphRec_reduce_base`, `hag`'s untainted operands reduce to
   `graphRec σ0 s dt on r' = semAux S s T q f dt on r'` on a `ReachedByRules` base `σ0` — a *W2*
   statement. `graph_correct_rules` proves the whole-schema `UntaintedSchema` version; W3's mixed
   schema needs it **per hereditarily-untainted relation `r'`**. Restate `graph_correct_rules` (and
   its soundness `sem_of_rules_reach` / completeness `nreaches_of_semAux_rules` chain) with a
   *hereditarily-untainted* hypothesis on `r'` in place of whole-schema `UntaintedSchema` (the
   relation's `sem`/graph only consult the untainted cone). Fuel via the T0a-stability sidestep.
   **This is the genuine remaining core** — a per-relation restatement threading through the W2
   proof chain; no W3a-specific reasoning left.
2. **Candidate completeness + assembly `graph_correct_w3a`** (an admitted `ReachedByW3aAdmitted`:
   every `sem`-member bare subject is in some `cands` and passes `checkFn`) + assembly: route →
   `probeDerived` → `check_derived_ResidueEmpty` → edge probe → `reachedByW3a_reach_collapse_root`
   → `checkFn_eq_semStep` (with `hag` from step 1) → `sem`. Then widen T3/T6.

## Session 2026-07-11 (W3a read correspondence — multi-pass reconcile inertness folded to the untainted base)

Resuming W3a from "reconcile-edge inertness resolved per-pass (`reconcileKey_reach_inert`);
resume → point 2's step 1, the **multi-pass inertness fold** down to the `ReachedByRules`
base". One green+pushed axiom-clean increment (`GraphIndex/ReconcileCorrect.lean` +
`ReconcileWrite.lean` constructor + `Audit.lean`); `verify.sh` green throughout (build + 0
sorries + 60 conformance + audit, standard axioms only — the new theorem `[propext,
Quot.sound]`). Sorry count held at 0. This lands **step 1 of point 2** (the reachability half
of the `hag` reduction): reachability into an untainted-key node on the full W3a state agrees
with the untainted base, so the reconcile-materialised derived edges are provably inert for the
operand reads W2's per-relation correctness consults.

**The increment.**
- **Constructor strengthened (`ReconcileWrite.lean`): `ReachedByW3a.reconcile` now carries
  `hder : isDerived S (dt, R) = true`** — faithful (reconcile only ever runs on a declared
  *derived* relation). This is the fact that separates a reconciled derived key from an untainted
  operand key of the same object type: equal keys share `isDerived`, so a `hder`-derived R-node is
  distinct from every untainted target. The five existing `| reconcile …` matches gained a `_hder`
  placeholder (harmless; no construction sites yet).
- **`reachedByW3a_reach_inert` (`ReconcileCorrect.lean`, `[propext, Quot.sound]`)** — the
  multi-pass fold. For a W3a state `σ` there is an untainted base `σ0` (`ReachedByRules σ0 S T`)
  with `∀ {u v}, isDerived S (v.type, v.pred) = false → NReaches σ.edges u v → NReaches σ0.edges
  u v`. By induction over the write path: **base** = identity; **reconcile** = peel one
  `reconcileKey_reach_inert` then apply the IH. The pass's target-distinctness `v ≠ objNode
  ⟨dt,on⟩ R` is discharged from `isDerived S (v.type,v.pred) = false` vs `hder` (equal keys share
  `isDerived`); the pre-pass R-node-not-a-source premise comes from `reachedByW3a_Rnode_not_source`
  on the sub-derivation, fed by the **schema-level terminal hypothesis** `hterm : ∀ dt R,
  isDerived S (dt,R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R` (faithful: W3a defers the
  non-terminal `PDerivedTTU`/`PDerivedUserset` shapes — carry `hterm` into the W3a/W4 fragment).

**Resume → close the W3a CORRESPONDENCE. Point 2 step 2 (the deeper blocker) + step 3 remain:**
1. ✅ **DONE this session** — the multi-pass inertness fold (`reachedByW3a_reach_inert`).
2. **Discharge `hag` — the per-relation untainted-correctness lemma (STILL the deeper blocker).**
   With the inertness fold, the operand read `probeNonDerived σ ⟨s, r', ⟨dt,on'⟩⟩` on the full W3a
   `σ` reduces to the read on the base `σ0` (move `probeNonDerived` → `NReaches` via
   `probeNonDerived_iff` + `reach_iff_nreaches` on both σ and σ0 — needs endpoint-closure `hcl`
   from `reachedByW3a_inv`/`reachedByRules_inv`; star-free ⇒ only probe 1 (plain) survives, so the
   read is exactly `NReaches …edges (subjNode s) (objNode ⟨dt,on'⟩ r')`, and `reachedByW3a_reach_
   inert` transfers it — note the operand node has type `dt` = the derived key's type and untainted
   relation `r'`, so `isDerived S (dt, r') = false` gives the target-key hypothesis). Then restate
   W2's `graph_correct_rules` **per hereditarily-untainted relation `r'`** within the mixed schema
   (whole-schema `UntaintedSchema` is too strong): its `sem`/graph only consult the untainted cone,
   so it factors out of the W2 proof but must be re-stated with a *hereditarily-untainted*
   hypothesis on `r'`. Fuel via the T0a-stability sidestep. **NB** the transfer above needs the
   reverse direction too (`NReaches σ0 → NReaches σ`), which is free (`σ0.edges ⊆ σ.edges` by
   `reconcileKey_edges_mono` folded — worth landing as a companion lemma, or strengthen
   `reachedByW3a_reach_inert` to an `↔`).
3. **Candidate completeness + assembly `graph_correct_w3a`** (an admitted `ReachedByW3aAdmitted`:
   every `sem`-member bare subject is enumerated in some `cands` and passes `checkFn`) + assembly:
   route → `probeDerived` → `check_derived_ResidueEmpty` → edge probe →
   `reachedByW3a_reach_collapse_root` → `checkFn_eq_semStep` + `hag` → `sem`. Then widen T3/T6.

## Session 2026-07-11 (W3a read correspondence — R-node-source subtlety RESOLVED + reconcile-edge reachability inertness)

Resuming W3a from "point 1 (`hsrcbare` via `NoRuleOutputs`) done; resume → point 2 (`hag` +
candidate completeness + assembly), **but the prior handoff flagged: resolve the R-node-source
subtlety FIRST — the inertness lemma may be false without an extra hypothesis.**" This session
does exactly that: one green+pushed axiom-clean increment (`GraphIndex/ReconcileCorrect.lean`);
`verify.sh` green throughout (build + 0 sorries + 60 conformance + audit, standard axioms only —
two new theorems `[propext]`, three `[propext, Quot.sound]`). Sorry count held at 0.

**The flagged subtlety, RESOLVED: is the derived R-node ever an edge SOURCE?** A reconcile edge
`subjNode c → objNode ⟨dt,on⟩ R` has a bare source (never a target) and an R-node target; for it
to be *reachability-inert* (so the operand read `probeNonDerived σ ⟨s, r', ⟨dt,on'⟩⟩` on the full
W3a σ matches the untainted base — what `hag` needs), the R-node must have **no out-edge**. But a
base (W2) edge source `subjNode u.subject` equals the R-node exactly when a stored/rewrite-closure
operand tuple carries a **userset subject over the derived relation R** (`⟨dt,on⟩#R`). The Python
DOES admit such usersets (`PDerivedUserset`, `zanzibar_utils_v1.py:1115`), so it is not
unconditionally impossible — the subtlety was real.

**Resolution — R is *terminal* on the single-stratum W3a fragment.** Two faithful fragment
conditions (analogs of W2's `NodupKeys`/`RewriteRanked`, carried into W4): **`NoStoreSubjectR T R`**
(no stored tuple has subject predicate R) and **`NoTtuTarget S R`** (no schema rewrite rule has
target relation R — the "target from tupleset with derived target" shapes `PDerivedTTU`/
`PDerivedTuplesetTTU` are deferred past W3a). A rewrite-closure tuple's subject predicate is the
seed's (computed rewrites keep the subject) or a TTU rule's `tr`; under both conditions neither is
R, so **no W3a edge is sourced at an R-userset node** and the R-node has no out-edge.

**The increment (`GraphIndex/ReconcileCorrect.lean`, axiom-clean).**
- **`nreaches_cons_inert`** (`[propext]`) — generic single-new-edge inertness: if the target `b` of
  a prepended edge is never a *source* in the old edges, a path to any `v ≠ b` in `(a,b)::edges` is
  already a path in `edges`. Via `nreaches_cons_split` (the new edge, if used, must exit `b` —
  impossible — or be the final hop to `b ≠ v`).
- **`NoTtuTarget` / `NoStoreSubjectR`** fragment predicates + subject-predicate avoidance across
  the rewrite closure: `rewriteStep_subject_pred_ne` (one hop keeps the subject off R — computed
  preserves it, `ttu tr` gives `tr ≠ R`) → `rewriteClosureAux_subject_pred_ne` →
  **`rewriteClosure_subject_pred_ne`**.
- **`reachedByW3a_edge_source_ne_R`** — no W3a edge is sourced at an R-userset node (base source =
  closure subject pred ≠ R; reconcile source = bare candidate pred `BARE ≠ R`), by induction over
  the write path. Corollary **`reachedByW3a_Rnode_not_source`** (`k.pred = R` ⇒ no out-edge). **This
  resolves the flagged subtlety.**
- **`reconcileKey_reach_inert`** (`[propext]`) — the payoff: one reconcile pass on key `(dt,R')`
  (bare candidates, `R' ≠ BARE`, R'-node not a source in σ) adds no reachability to any
  `v ≠ objNode ⟨dt,on⟩ R'`. Peels the guarded `writeDirect` fold one candidate at a time via
  `nreaches_cons_inert`, maintaining "R'-node not a source" (each new edge's bare source has
  predicate `BARE ≠ R'`). The **per-pass** inertness the multi-pass `hag` transfer folds over.

**Resume → close the W3a CORRESPONDENCE (point 2, the deeper blocker), now unblocked on inertness:**
1. **Multi-pass inertness (mechanical fold).** Induct over `ReachedByW3a` and fold
   `reconcileKey_reach_inert` at each reconcile pass down to the `ReachedByRules` base, giving
   `NReaches σ.edges (subjNode s) (objNode ⟨dt,on'⟩ r') → NReaches σ_base.edges …` for an untainted
   operand `r'` (`r' ≠` any reconcile `R'`, since `r'` untainted / `R'` derived). Needs the fragment
   to carry `NoTtuTarget`/`NoStoreSubjectR` for **every** derived relation with a reconcile pass
   (schema-level: `∀ R, isDerived S (dt,R) → NoTtuTarget S R ∧ NoStoreSubjectR T R`), and the R'-node
   not-a-source at each pre-pass sub-state (from `reachedByW3a_Rnode_not_source` on the sub-derivation).
   NB the base ↔ full state relation: `ReachedByW3a` doesn't expose `σ_base` — either strengthen the
   inductive to carry it, or prove the fold as a `σ`-relative statement (probeNonDerived on σ equals
   probeNonDerived on the stripped edges).
2. **Discharge `hag` — the per-relation untainted-correctness lemma (STILL the deeper blocker).**
   With inertness (1), the operand read reduces to the untainted-base read; then restate W2's
   `graph_correct_rules` **per hereditarily-untainted relation `r'`** within the mixed schema (the
   whole-schema `UntaintedSchema` is too strong). Fuel via the T0a-stability sidestep.
3. **Candidate completeness + assembly `graph_correct_w3a`** (an admitted `ReachedByW3aAdmitted`;
   route → `probeDerived` → `check_derived_ResidueEmpty` → edge probe →
   `reachedByW3a_reach_collapse_root` → `checkFn_eq_semStep` + `hag` → `sem`) + T3/T6 widening.

## Session 2026-07-11 (W3a read correspondence — `hsrcbare` discharged via `NoRuleOutputs`; the reach-collapse fires unconditionally)

Resuming W3a from "the reach-collapse spine done over a free `hsrcbare`; resume → (1)
discharge `hsrcbare` via `NoRuleOutputs`, (2) the per-relation `hag` + candidate
completeness + assembly." One green+pushed axiom-clean increment
(`GraphIndex/ReconcileCorrect.lean`); `verify.sh` green throughout (build + 0 sorries + 60
conformance + audit, standard axioms only — one new theorem axiom-free). Sorry count held at
0. This closes **point 1** of the two remaining W3a correspondence pieces: the reach-collapse
now fires with **no free hypothesis** on the boolean-rooted fragment.

**The increment — `hsrcbare` discharged (`GraphIndex/ReconcileCorrect.lean`, axiom-clean).**
The prior session left the reach-collapse (`reachedByW3a_reach_collapse`) stated over a free
`hsrcbare` (every R-node in-edge source is bare). This session discharges it on the fragment
where the derived def `e = lookup (dt, R)` is **`inter`/`excl`-rooted** — the analytic side
condition (`NoRuleOutputs`, the W3a analog of W2's `TtuTuplesetsDirect`).
- **`RootBoolean e`** (root is `inter`/`excl`) + `exprArms_rootBoolean` (emits no rewrite
  arms — `exprArms` walks into `union` but stops at `inter`/`excl`) + `exprDirects_rootBoolean`
  (carries no `Direct` storage arm).
- **`NoRuleOutputs S dt R`** (no schema rewrite rule outputs `(dt,R)`) + **`noRuleOutputs_of_
  root`** — via `schemaRewrites_provenance` + `NodupKeys` (`lookup_of_mem`): a rule with
  `(objectType,outRel) = (dt,R)` comes from the def at key `(dt,R)` = `e`, boolean-rooted,
  which emits no arms.
- **`reachedByW3a_Rnode_source_bare`** (the payoff) — by induction over the W3a write path:
  the **base** (rewrite-closure) leg landing on `objNode ⟨dt,on⟩ R` is IMPOSSIBLE (a closure
  tuple there is a stored `(dt,R)` tuple — none, by `exprDirects_rootBoolean` +
  `StoreValidRules`; or a rewrite output `(dt,R)` — none, by `noRuleOutputs_of_root`), so
  every R-node in-edge is a **reconcile** edge, whose source `subjNode c` is bare because the
  `reconcile` constructor now carries `hcands : ∀ c ∈ cands, c.predicate = BARE` (faithful —
  the `_leaf_concretes` candidates are bare concretes). **`ReachedByW3a.reconcile` strengthened
  with `hcands`** (the three existing inductions updated; harmless).
- **`reachedByW3a_reach_collapse_root`** — the fully-discharged collapse: a path to the derived
  object node is a *single* reconcile edge, no `hsrcbare` free. Ready to compose with
  `checkFn_eq_semStep` for `reach ↔ [reconcile wrote s's edge] ↔ checkFn ↔ sem`.
- Node-projection simp lemmas `objNode_type` / `subjNode_pred` added locally (the ObjStar
  copies aren't in the W3a import chain).

**Resume → close the W3a CORRESPONDENCE. One piece remains (point 2, the deeper blocker):**
1. ✅ **DONE this session** — `hsrcbare` via `NoRuleOutputs` (`reachedByW3a_reach_collapse_root`).
2. **Discharge `hag` — the per-relation untainted-correctness lemma**, then candidate
   completeness + assembly `graph_correct_w3a`. `hag` (`graphRec σ s dt on r' = semAux S s T q f
   dt on r'` for untainted operand `r'`) restates W2's `graph_correct_rules` per-relation within
   the mixed schema (reconcile edges into derived-R nodes are reachability-inert for untainted-`r'`
   object nodes — a derived edge's bare-candidate source is never an intermediate object node);
   fuel via the T0a-stability sidestep. Then candidate completeness (an admitted
   `ReachedByW3aAdmitted`: every `sem`-member bare subject is enumerated in some `cands` and
   passes `checkFn`) + assembly: route → `probeDerived` → `check_derived_ResidueEmpty` → edge
   probe → `reachedByW3a_reach_collapse_root` → `checkFn_eq_semStep` + `hag` → `sem`. Then widen
   T3/T6 as free corollaries. **This is the genuine remaining core** — the per-relation restatement
   of `graph_correct_rules` (whole-schema `UntaintedSchema` is too strong for W3's mixed schema).

   **Design notes for the next session (analytic, this session — de-risk the assembly):**
   - **`checkFn` is STABLE across reconcile passes on the fragment (the enabling fact).** A
     `ComputedOnly` derived def references only *untainted operand* relations `r'` (no self-ref
     to `R`). Reconcile passes add only derived-R-node edges; if those are **inert for operand
     reads** (`probeNonDerived ⟨·, r', ·⟩` unchanged), then `checkFn` computed mid-fold equals
     `checkFn` at the final σ — so the soundness link (edge present ⇒ `checkFn` was true ⇒ via
     `hag` ⇒ `sem`) needs no fold-accumulator gymnastics. This is why the fragment forbids
     `direct`/`ttu` leaves on the derived def and requires untainted operands.
   - **SUBTLETY to check before proving inertness — is the derived R-node ever an edge SOURCE?**
     A base (W2) edge source is `subjNode u.subject`; for a *userset* subject `⟨dt,on⟩#R`
     (type dt, name on, pred R) this equals `objNode ⟨dt,on⟩ R` (both `⟨dt,on,R,plain⟩`). So if
     a stored/rewritten operand tuple carries a userset subject over the **derived** relation `R`,
     the R-node HAS an out-edge and the new reconcile edge is NOT reachability-inert. Need either
     (a) a fragment condition forbidding usersets-over-derived-`R` as subjects (cf. the Python
     `UnsupportedByGraphIndex` scope rejection for *wildcard* usersets over derived relations —
     check whether plain usersets over derived relations are also excluded / admission-invalid),
     or (b) prove such subjects can't be a stored/rewrite-closure subject under `StoreValidRules`
     + `ComputedOnly`. Resolve this first; the inertness lemma (⇒ `hag` reduces to W2 per-relation
     ⇒ assembly) hinges on it. Do NOT land an inertness lemma without settling the R-node-source
     question — it may be false without an extra hypothesis.

## Session 2026-07-11 (W3a read correspondence — the bare-subject reach-collapse spine + attack-first NoRuleOutputs finding)

Resuming W3a from "two structural spines done; resume → close the CORRESPONDENCE (three
sharply-isolated points)." One green+pushed axiom-clean increment (`GraphIndex/
ReconcileCorrect.lean`); `verify.sh` green throughout (build + 0 sorries + 60 conformance
+ audit, standard axioms only — two of the four new theorems are **axiom-free**). Sorry
count held at 0. This lands the **reach-collapse spine** (ROADMAP W3a read, point 2's
structural half), plus an attack-first finding that narrows the fragment.

**Attack-first HEADLINE (analytic case-analysis, not a correctness refutation): the naive
single-edge reach-collapse is FALSE on the full `ComputedOnly` fragment — it needs a
`NoRuleOutputs S R` side condition, the W3a analog of W2's `TtuTuplesetsDirect`.** The
roadmap's stated collapse ("a derived edge's source is a bare candidate, never a target,
so no hop can precede it") assumes *every* edge into the derived R-node is a reconcile
edge from a **bare** source. But if the derived def `e = lookup (dt,R)` has a **top-level
`union`** exposing a `computed` arm (`member or (admin but not suspended)`), `exprArms`
emits a `computed` rewrite rule `… ↦ R`, so W2's base rewrite-closure *also* lands tuples
on the R-node — and a `computed` rewrite carries the operand chain's subject, which for a
ttu-derived operand is a **userset (non-bare)** node that CAN be an edge target. Then the
path is genuinely ≥ 2 hops (`subjNode s → g#x → objNode R`) and the collapse fails.
`check = sem` still HOLDS in both cases (both mechanisms agree — this is a *proof-shape*
limitation, not unsoundness); the single-edge collapse holds exactly when **no rewrite
rule outputs `R`** — i.e. the derived def is `inter`/`excl`-rooted (`exprArms … = []`).
`member but not banned` (`.excl`-rooted) and `(a or b) but not c` (`.excl` at the root,
union underneath) both satisfy this; only a union-rooted-with-tainted-arm def breaks it.

**The increment — the reach-collapse spine (`GraphIndex/ReconcileCorrect.lean`, axiom-clean).**
- **`ReachedByW3a.reconcile` strengthened** with `hRne : R ≠ BARE` (faithful — reconcile
  only runs on declared derived relations; the two existing inductions ignore it).
- **`nreaches_collapse_of_source_notarget`** (NO axioms) — generic: if every source of an
  edge into `v` has itself no in-edge, any path to `v` is a single edge (`nreaches_last`
  twice: the last-edge source's own in-edge would contradict the hypothesis).
- **`reachedByW3a_edge_target_ne_bare`** — every W3a edge target has a non-`BARE`
  predicate (base = `objNode u.object u.relation`, pred `u.relation ≠ BARE` via
  `rewriteClosure_rel_ne_bare`; reconcile = `objNode ⟨dt,on⟩ R`, pred `R ≠ BARE` via the
  new constructor field). Hence **`reachedByW3a_bareNode_no_inedge`** — a `BARE`-pred node
  is never an edge target (the structural fact behind the collapse).
- **`reachedByW3a_reach_collapse`** — assembly: a bare-subject path to the derived object
  node `objNode ⟨dt,on⟩ R` is a *single* edge, given `hsrcbare` (every R-node in-edge
  source is bare — the isolated `NoRuleOutputs` gap). This is the last structural link
  before `reach ↔ [reconcile wrote s's edge] ↔ checkFn ↔ sem`.

**Resume → close the W3a CORRESPONDENCE. Two pieces remain, further sharpened:**
1. **Discharge `hsrcbare` via `NoRuleOutputs S R`** (the fragment side-condition found this
   session). Prove: on an `inter`/`excl`-rooted derived def, no `schemaRewrites S` rule has
   `outRel = R` (`exprArms` of an `.inter`/`.excl` root is `[]`), and no store tuple has
   relation `R` (its `ComputedOnly` def has no direct arm ⇒ `exprDirects = []` ⇒ fails
   `StoreValidRules`). So every edge into the R-node is a reconcile edge (via
   `reachedByW3a_edge_sound`'s base leg being vacuous on relation `R`), whose source is a
   bare candidate `c` — giving `hsrcbare`. Then `reachedByW3a_reach_collapse` fires
   unconditionally on the fragment.
2. **Discharge `hag` — the per-relation untainted-correctness lemma (STILL the deeper
   blocker)**, then candidate completeness + assembly `graph_correct_w3a`. `hag`
   (`graphRec σ s dt on r' = semAux S s T q f dt on r'` for untainted operand `r'`)
   restates W2's `graph_correct_rules` per-relation within the mixed schema (the reconcile
   edges into derived-R nodes are reachability-inert for untainted-`r'` object nodes: a
   derived edge's bare-candidate source is never an intermediate object node); fuel via the
   T0a-stability sidestep. With `hag` + `checkFn_eq_semStep` + the collapse (piece 1) +
   candidate completeness (an admitted `ReachedByW3aAdmitted`: every `sem`-member bare
   subject is enumerated in some `cands` and passes `checkFn`): route → `probeDerived` →
   `check_derived_ResidueEmpty` → edge probe → `reachedByW3a_reach_collapse` → `checkFn` →
   `sem`. Then widen T3/T6 as free corollaries.

## Session 2026-07-11 (W3a read correspondence — checkFn↔sem-step reduction + reconcile edge characterization)

Resuming W3a from "write model + read collapse done; resume → the correspondence (three
sharply-isolated points)." Two green+pushed axiom-clean increments in a new file
(`GraphIndex/ReconcileCorrect.lean`); `verify.sh` green throughout (build + 0 sorries +
60 conformance + audit, standard axioms only). Sorry count held at 0. This lands the two
*structural* spines of the W3a read correspondence, isolating the remaining work to
exactly the per-relation semantic fact.

**Increment 1 — the `checkFn` ↔ `sem`-step reduction (axiom-clean, `[propext]`).** The
W3a derived def is a boolean tree (`and`/`but not`/`or`) whose leaves are all `computed`
refs — captured by **`ComputedOnly : Expr → Prop`** (allows `computed`/`union`/`inter`/
`excl`; forbids `direct`/`ttu`, which would route onto leaf families, deferred past W3a).
- **`evalE_computedOnly`** (NO axioms) — on a `ComputedOnly` expr `evalE` consults its
  node-recursion `rec` only at `(dt, on, ·)` (never reaches a `direct`/`ttu` leaf), so two
  `rec`s agreeing there evaluate the whole tree identically — independent of subject/store/
  query/enclosing-relation. A one-shot `Expr` induction.
- **`checkFn_eq_semStep`** (`[propext]`) — `σ.checkFn T s dt on R e = semAux S s T q (f+1)
  dt on R`, given `S.lookup (dt,R) = some e`, `ComputedOnly e`, and the per-relation
  agreement `hag : ∀ r', graphRec σ s dt on r' = semAux S s T q f dt on r'`. `checkFn`'s
  graph node-recursion (`graphRec = probeNonDerived`) is swapped for `sem`'s fuel recursion
  via `evalE_computedOnly`. **This reduces the reconcile guard `checkFn = sem`-membership to
  exactly `hag` — the per-relation untainted graph↔`sem` fact, the stated W3a blocker.**

**Increment 2 — the reconcile edge characterization (axiom-clean, `[propext]`).** The
structural spine for the (bare-subject) reach-collapse — `reconcileKey` is a guarded
`writeDirect` fold, so its edge effect is exactly:
- **`reconcileKey_edges_mono`** — the fold only ever adds edges (old edges persist).
- **`reconcileKey_edge_sound`** — every edge of `σ.reconcileKey T dt on R e cands` is an
  old σ-edge or a candidate's derived edge `subjNode c → objNode ⟨dt,on⟩ R` (`c ∈ cands`).
- **`reachedByW3a_edge_sound`** — every edge of a W3a-reached state is either a materialised
  rewrite-closure tuple of a stored tuple (the untainted base — `reachedByRules_edge_sound`)
  or a reconcile derived edge, by induction over the write path. The W3a analog of
  `reachedByDirect_edge_sound` / the W2 edge-sound groundwork.

**Resume → close the W3a CORRESPONDENCE. Two pieces remain, now sharply isolated:**
1. **Discharge `hag` — the per-relation untainted-correctness lemma (THE blocker).** For an
   untainted operand relation `r'` in the mixed W3a schema, `graphRec σ s dt on r' =
   probeNonDerived σ ⟨s, r', ⟨dt,on⟩⟩` must equal `semAux S s T q f dt on r'` (at a fuel
   reconciled by the T0a-stability sidestep). `graph_correct_rules` proves this for a whole
   `UntaintedSchema`, too strong for W3's mixed schema — restate **per-relation** (an
   untainted relation's graph read = its `sem` within a partially-tainted schema; its `sem`/
   graph only consult the untainted cone, so it factors out of the W2 proof but must be
   re-stated with a *hereditarily-untainted* hypothesis on `r'`, not whole-schema
   `UntaintedSchema`). Also needs: the reconcile edges (into derived-`R` object nodes) are
   reachability-inert for untainted-`r'` object nodes — a derived edge's source `subjNode c`
   (bare candidate) is never an intermediate object node, so it cannot extend a path to an
   untainted-relation node.
2. **The reach-collapse + candidate completeness + assembly `graph_correct_w3a`.** With the
   edge characterization (increment 2): for a bare-subject derived query, `reach (subjNode
   s) (objNode ⟨dt,on⟩ R)` collapses to a *single* reconcile edge — a derived edge's source
   is a bare candidate node, which (predicate `BARE` ≠ any relation) is never an edge
   *target*, so no hop can precede it; hence `reach ↔ [reconcile wrote s's edge] ↔ checkFn
   s ↔ sem` (via increment 1 + `hag`). Needs: (a) the single-edge structural lemma (bare
   node never an object-node target — base edges via `rewriteClosure_rel_ne_bare`, derived
   `R ≠ BARE`); (b) candidate completeness (every `sem`-member bare subject is enumerated in
   some reconcile pass's `cands` and passes `checkFn` — an admitted `ReachedByW3aAdmitted`,
   the W3a analog of `ReachedByRulesAdmitted`); (c) route → `probeDerived` →
   `check_derived_ResidueEmpty` (already have) → the edge probe → the collapse. Then widen
   T3/T6 as free corollaries.

## Session 2026-07-10 (W3 STARTED — derived reconcile / residue path; attack-first + W3a read collapse + write model)

Resuming from W1 + W2 both closed → **ROADMAP stage W3** (derived reconcile: `and` /
`but not`, the per-key residue `(stars, neg, upos)`, the processor cascade). Two
green+pushed axiom-clean increments; `verify.sh` green throughout (build + 0 sorries +
60 conformance + audit, standard axioms only). Sorry count held at 0. This starts the
W3a sub-stage (star-free, bare-subject derived booleans), matching how W1/W2 each began
with attack-first + a write model before the read correspondence.

**Sub-staging plan (designed this session):** W3a star-free bare booleans → W3b userset
subjects (`upos`) → W3c star data (`stars`/`neg`) → W3d multi-stratum cascade (the
cross-key re-reconcile hazard + contentful T5 outbox drain). W3a is the "zero residue
content" analog of W1a's "zero bridges".

**Attack-first HEADLINE (machine-checked `#eval` vs `sem`, then deleted): the W3a
residue-read ↔ `sem` correspondence HOLDS — no refutation.** On a `doc#viewer :=
member but not banned` (both direct) star-free store, `check` (routed to `probeDerived`)
equals `sem` on every query: the derived edge is materialised for the member-not-banned
subject, none for the banned one, and the residue is EMPTY. This confirmed the key W3a
modeling fact:

> **On the star-free bare-subject fragment the processor stores NO residue row.**
> `stars = neg = upos = ∅` ⇒ `_store_residue` never fires (I6's non-empty clause), so
> the state stays `ResidueEmpty` and a derived relation only adds **edges** — a derived
> edge being structurally an ordinary `writeDirect ⟨s, R, o⟩`. So W3a reuses ALL of W2's
> write + preservation machinery, and the derived read collapses to a pure edge probe.

**Increment 1 — the read-side collapse (`GraphIndex/Reconcile.lean`, axiom-clean).**
`probeDerived_residueEmpty` — the derived read on an empty residue is the bare edge
probe (object-wildcard / `'*'`-subject / userset all read `False` on empty
`stars`/`neg`/`upos`; a bare non-`'*'` subject reduces to `reach (subjNode s) (objNode
o R)`). `probeDerived_ResidueEmpty` (global corollary) + `check_derived_ResidueEmpty`
(routing: a derived read on an empty residue is decided by the same reachability the
non-derived read uses — the residue machinery is provably inert on W3a).

**Increment 2 — the WRITE model (`GraphIndex/ReconcileWrite.lean`, axiom-clean).**
Modeling discovery from `processor.py:_EvalContext`/`reconcile`: on the W3a fragment
(derived def = boolean tree over `computed` refs to UNTAINTED relations, single stratum)
the compiled `check_fn` evaluates that tree with every leaf dispatching to `leaf_check`
= `widx.check` = the graph's ≤4-probe read (`probeNonDerived`). So `check_fn` is exactly
`evalE` with `rec` reading the graph. Delivered:
- `graphRec` (`= probeNonDerived`) + `GraphState.checkFn` (`= evalE (graphRec) …`).
- `GraphState.reconcileKey` — a guarded `writeDirect` fold: materialise the derived
  edge for each candidate bare subject iff `checkFn` (the `reconcile_subject` rule
  `want_edge = should ∧ ¬covered`, `covered = false` star-free).
- `structInv_/residueEmpty_/inv_/quiescent_reconcileKey` (guarded fold preserves
  everything `writeDirect` does — each step is `writeDirect` or identity).
- **`ReachedByW3a`** (write-closure: W2's `ReachedByRules` base + reconcile passes) +
  **`reachedByW3a_inv`** (T2a `Inv` conjunct: `Inv ∧ ResidueEmpty ∧ Quiescent`, by
  induction over the concrete path) + `reachedByW3a_residueEmpty` (the read-side hook).

**Resume → the W3a CORRESPONDENCE (`checkFn = sem` + candidate completeness ⇒
`graph_correct_w3a`), sharply isolated. KEY FINDING for the next session:**
1. **`checkFn σ s = sem`-membership of `s` in the derived key.** Via `evalE_congr`
   (`Spec/Confine.lean`: `evalE` agrees if `rec` agrees on the referenced keys over
   `oname ∪ storedNames`) reducing it to: for each `computed r'` operand (untainted
   `r'`), `graphRec σ s dt on r' = sem`-membership. **BLOCKER discovered:**
   `graph_correct_rules` needs `UntaintedSchema S` (no `.inter`/`.excl` in ANY def) —
   but W3a's schema HAS the derived `.excl`, so it does NOT apply to the whole schema.
   The next increment needs a **per-relation** untainted-correctness lemma: an untainted
   relation `r'`'s graph read (`probeNonDerived`) equals its `sem`-membership *within a
   mixed (partially-tainted) schema*. The untainted relation's `sem`/graph only consult
   the untainted edges + its own def, so this should factor out of the existing W2
   proof, but it must be RE-STATED per-relation (the whole-schema `UntaintedSchema`
   hypothesis is too strong for W3). Fuel via the T0a-stability sidestep (`sem_fuel_
   stable`; the derived-key `sem` is `semAux` at `fuelBound`, `checkFn` reads the graph
   at "infinite" fuel — reconcile the two by stability, as W1c/W2 did).
2. **Candidate completeness.** `ReachedByW3a`'s `reconcile` leg fires on a GIVEN `cands`
   list. Completeness (`sem ⇒ edge`) needs the closure SATURATED: every `sem`-member
   bare subject is in some reconcile pass's `cands` AND passes `checkFn`. Model the
   candidate enumeration (`_leaf_concretes`: concretes of the positive leaves) and prove
   it covers every `sem`-member — the W3a analog of W2's edge-completeness / admitted
   closure. Likely an admitted `ReachedByW3aAdmitted` (grant + reconcile edges present).
3. **Assembly `graph_correct_w3a`.** For a derived query: route to `probeDerived`
   (`isDerived`), collapse to the edge probe (`check_derived_ResidueEmpty` +
   `reachedByW3a_residueEmpty`), then `reach (subjNode s) (objNode o R) ↔ [edge written]
   ↔ checkFn ↔ sem`. For an untainted query: the per-relation lemma from (1). Then widen
   T3/T6 (`Equiv.lean`) as free corollaries. NB W3a fragment: star-free, bare subjects,
   derived def = boolean over `computed` refs to untainted relations (no direct/ttu arms
   ON the derived relation — that adds leaf-family routing, defer). Attack-first any
   widening before proving.

## Session 2026-07-10 (W2 FULLY CLOSED — completeness `sem ⇒ reach` + `graph_correct_rules` + T3/T6 widened)

Resuming W2 from "soundness direction closed; resume → W2 COMPLETENESS + assembly".
Delivered the **whole W2 correspondence** — `graph_correct_rules` (full `check = sem` on
the untainted rule-routing fragment) — as three green+pushed axiom-clean increments, plus
the T3/T6 corollary widening. `verify.sh` green throughout (build + 0 sorries + 60
conformance + audit). Sorry count held at 0. **ROADMAP stage W2 is now closed end-to-end
(soundness + completeness), matching W1a/W1b/W1c.**

**Attack-first HEADLINE (machine-checked `#eval`, then deleted): closure-saturation HOLDS
at the write model's `|keys|+1` bound — no refutation.** The completeness `computed` case
needs the materialised rewrite-closure closed under one more rewrite step. Attack-first
stressed this against adversarial schemas: mutual-`ttu` cycles and **predicate-ratcheting
unions whose distinct reachable-tuple count exceeds `|keys|+1`** (`schemaRatchet2`: 6
distinct reachable > bound 4) — saturation held in every case. The finding: the **rewrite
DEPTH** (shortest rewrite-path length), not the count, is bounded by `|keys|`, because each
step advances the relation to a rule `outRel`. So `|keys|+1` closure levels capture every
reachable tuple *and* leave the top layer's rewrite-image already inside. Notably
saturation held even for the *cyclic* schemas, which the provable-path hypothesis
(`RewriteRanked`) excludes — so `RewriteRanked` is sufficient, not necessary.

**Increment 1 — the admitted W2 closure + edge-completeness (`GraphIndex/RulesComplete.lean`,
axiom-clean `[propext]`).** `writeRules` folds `writeDirect` (guarded, cycle-rejecting) over
the closure, so edge-completeness needs every fold write admitted. `FoldAdmits` records
exactly that; `foldl_writeDirect_edges_mono` (writeDirect only adds edges) +
`foldl_writeDirect_edge_complete` give it. `ReachedByRulesAdmitted` (the admitted W2
closure) + `reachedByRulesAdmitted_edge_complete` (every rewrite-closure tuple of every
stored write has its edge — the completeness analog of `reachedByRules_edge_sound`) +
`reachedByRulesAdmitted_seed_edge` (the stored-seed case the direct/ttu cases consult).

**Increment 2 — rewrite-closure saturation (`GraphIndex/RulesSaturate.lean`, axiom-clean
`[propext, Quot.sound]`).** `RewriteRanked S` (the faithful fragment condition: the rewrite
graph on relations is acyclic — a `|keys|`-bounded rank every rewrite rule strictly
increases; Python stratification rejects computed-userset cycles). The rewrite-layer
algebra `stepN` / `stepN_step_comm` / `mem_aux_of_stepN` / `stepN_of_mem_aux` decomposes
`rewriteClosureAux` into depth layers; `rwKey_rank_lt` (a step strictly bumps rank) +
`stepN_rank_ge` (a depth-`k` tuple has rank ≥ `k`) give the depth bound; **`rewriteClosure_
saturated`** — `w ∈ rewriteClosure S t`, `u ∈ rewriteStep S w ⇒ u ∈ rewriteClosure S t`.

**Increment 3 — the completeness core + assembly (`GraphIndex/RulesComplete.lean`,
axiom-clean).** `nreaches_of_semAux_rules` (`sem ⇒ reach`) by fuel induction × def-expr
inner induction:
- **direct** — verbatim `nreaches_of_semAux` (direct match = the stored grant's own edge
  via `reachedByRulesAdmitted_seed_edge`; flow-through = the recursion's path + the grant
  edge, appended by `NReaches.tail`).
- **computed** — the fuel IH gives a path to the `r'`-node; **`nreaches_relation_rewrite`**
  redirects it to the `r`-node by **last-edge surgery** (`nreaches_last` exposes the final
  edge = a closure tuple `w` on relation `r'`; its computed rewrite `⟨w.subject, r,
  w.object⟩` stays in the closure by `rewriteClosure_saturated`, so *its* edge into the
  `r`-node is materialised and replaces the last hop). This is the one case needing
  saturation.
- **ttu** — the stored tupleset tuple `w`'s ttu-rewrite is a **depth-1** closure member
  (`rewriteStep_mem_closure`, no saturation), so its edge is materialised; direct
  parent-match = that edge, `rec` disjunct = the parent-userset recursion + the edge.
- **union** — the true arm (arms' rewrite provenance split via `harms`).
**Key scope finding: completeness does NOT need `TtuTuplesetsDirect`** (that was a
*soundness*-only condition — it stops the graph landing non-seed tuples on tupleset
relations; going `sem ⇒ graph` the stored `w` genuinely exists). So `nreaches_of_semAux_
rules` carries only `UntaintedSchema ∧ RewriteRanked ∧ StarFree ∧ admitted`. Assembly
**`graph_correct_rules`** routes `check → probeNonDerived` (`check_eq_probeNonDerived`),
kills probes 2–4 (`reachedByRulesAdmitted_edges_plain` — star-free ⇒ only plain endpoints,
via `rewriteClosure_subjectName`/`_object`), and glues probe 1 through `reach ↔ NReaches`
to soundness (`sem_of_rules_reach`) + completeness. **T3/T6 widened** (`Equiv.lean`):
`backend_equivalence_rules` / `exclusion_effective_rules` / `no_ghost_grant_rules`
(T1 ∘ `graph_correct_rules`, `sem`-stratifiability from `stratifiable_untainted`).

**W2 fragment predicate (assembled):** `WF ∧ UntaintedSchema ∧ TtuTuplesetsDirect ∧
NodupKeys ∧ RewriteRanked ∧ StoreValidRules ∧ StarFreeStore` (soundness needs `TtuTuplesets
Direct`+`NodupKeys`; completeness needs `RewriteRanked`; both need the rest). Carry
`NodupKeys` + `RewriteRanked` into W4 as faithful hypotheses (dict keys; stratification).

**Next: ROADMAP W3** (derived reconcile — the residue path, `and`/`but not`, the processor
cascade). W1 (wildcard bridges) + W2 (rule routing) are now both closed. The *combined*
generality (wildcards + rules + booleans) lands at **W4** (full-scope restatement). NB the
W2 fragment isolates untainted rule routing on star-free data; wildcards-in-rules and the
residue path are still deferred. Attack-first the W3 reconcile output before proving.

## Session 2026-07-10 (W2 SOUNDNESS direction CLOSED — generalised lift + chain composition + `sem_of_rules_reach`)

Continuing W2 from the soundness core (per-tuple membership) → the **whole soundness
direction** (graph reachability ⇒ `sem`). One green+pushed axiom-clean increment
(`GraphIndex/RulesChain.lean`, sorry-free, `[propext, Classical.choice, Quot.sound]`).
`verify.sh` green (build + 0 sorries + 60 conformance + audit). Sorry count held at 0.

**Delivered — the stated blocker cleared: `semAux_lift_untainted`** (the userset lift
GENERALISED from `PureDirect` to `UntaintedSchema`). A userset now flows through a
`computed`/`ttu`/`union` node, not just a `direct` one. Structure: a nested induction —
fuel outside (`semAux_lift_untainted`), `Expr` inside (`evalE_lift`) — whose leaf cases
are:
- **direct** — the DirectCorrect logic verbatim (a direct match of `s'` at a grant is
  absorbed by `s`'s flow-through on the same grant via `mog_intro`/`directLeaf_of_mog`;
  a flow-through by the fuel IH). The DirectCorrect leaf lemmas (`directLeaf_elim`,
  `mog_elim`, `mog_intro`, `directLeaf_of_mog`) are NOT `PureDirect`-specific, so reused
  as-is.
- **computed** — the fuel IH at the sub-node (`evalE`'s `computed r'` case is `rec ot on
  r'`, so `s' ∈ (ot,on,r') ⇒ s ∈ (ot,on,r')` is `ih ot on r'`).
- **ttu** — the stored-parent loop. `ttuLeaf_elim`/`ttuLeaf_intro_rec` (star branch dead
  on star-free data): a *direct* parent-match (`s' = ⟨pt,pn,tr⟩`) becomes `hmem` (`s ∈
  s'`, mono to fuel); a *parent-membership* (`rec` disjunct) the fuel IH. `ttuLeaf`'s
  `rec`-disjunct is subject-independent, so `s` re-fires it identically.
- **union** — the OR (both arms untainted, `containsBool = false`).

**Chain composition + top-level.** `semAux_of_ruleChain` (mirror of DirectCorrect's
`semAux_of_chainN`, but each hop's base membership is `semAux_of_rewriteClosure` at
*some* fuel and the step is `semAux_lift_untainted`; fuel threaded existentially — no
tight bound). New preservation lemmas: `rewriteClosure_subjectName` (rewrites keep the
subject name ⇒ closure subjects star-free) and `rewriteClosure_rel_ne_bare` (a closure
tuple's relation is the seed's or a rewrite output relation — both declared, so the
userset intermediate's predicate ≠ `BARE`). **`sem_of_rules_reach`** (graph reachability
⇒ `sem`) closes the soundness direction end-to-end: `reachedByRules_edge_sound` pins
every edge to a `Tstar = ⋃_{t∈T} rewriteClosure S t` tuple, `chainN_of_trail` → chain,
`semAux_of_ruleChain` → `sem` at some fuel, T0a-stability sidestep
(`sem_fuel_stable` via `stratifiable_untainted` + `storeDeclared_of_validRules`) → `sem
= true`. No fuel-count arithmetic (like W1c).

**Resume → W2 COMPLETENESS + assembly.** Sharply isolated:
1. **Completeness (`sem ⇒ reach`)** — the remaining hard direction. `sem S T q = true`
   (at `fuelBound`) must be witnessed by a graph path over the materialised
   rewrite-closure. Fuel-induction unfolding the query def: `direct` = a stored grant's
   own edge (`admitted`-style edge-completeness for `writeRules`; NB the store tuple `t`
   *is* in `rewriteClosure S t` as the seed, so its edge is materialised) + flow-through;
   `computed`/`ttu`/`union` = the recursion is witnessed by a rewrite-closure chain. The
   graph edge for a computed/ttu step comes from the *rewrite output* tuple being
   materialised — so completeness needs "the rewrite-closure is saturated enough":
   whenever `sem` recurses `rec ot on r'` (computed) it must find the materialised
   rewrite edge. Attack-first the computed-case closure-saturation (the earlier W2 entry
   flagged this — a `T*` tuple on `R'` whose def has `computed R'`-armed `R` should also
   carry the `R`-rewrite in `T*`) before proving. Needs an *admitted* `writeRules`
   closure (`ReachedByRules` admits cycle-rejected edges silently; completeness needs the
   edge present) — the W2 analog of `ReachedByAdmitted`.
2. **Assembly `graph_correct_rules`** — route `check → probeNonDerived`
   (`check_eq_probeNonDerived`), kill probes 2–4 (star-free ⇒ no `wAny`/`wAll` endpoint,
   mirror of `graph_correct_direct`), glue probe 1 via `reach ↔ NReaches` to
   `sem_of_rules_reach` (forward) + completeness (backward). Then T3/T6 widening
   (`Equiv.lean`, free corollaries).

## Session 2026-07-10 (W2 SOUNDNESS core — the rewrite-closure realises `evalE`'s recursion)

Resuming W2 from "write model + read-routing + soundness groundwork + fragment nailed
down (`TtuTuplesetsDirect`); resume → the reachability↔`sem` core". Delivered the
**soundness half's heart** as one green+pushed axiom-clean increment
(`GraphIndex/RulesSound.lean`, sorry-free, `[propext, Classical.choice, Quot.sound]`).
`verify.sh` green throughout (build + 0 sorries + 60 conformance + audit). Sorry count
held at 0. This is the first W2 lemma that ties the graph's rewrite-fanout to `sem`.

**Headline: `semAux_of_rewriteClosure` — every rewrite-closure tuple of a stored tuple
is a `sem` membership at some fuel.** For `t ∈ T` and `u ∈ rewriteClosure S t`, `sem`
derives `u.subject ∈ (u.object, u.relation)`. This is *exactly* "the rewrite-closure
realises `evalE`'s `computed`/`ttu`/`union` recursion", proved by a
generalise-over-`cur` closure induction (mirrors `rewriteClosureAux_object`):
- **seed** (`u = t`): a direct self-grant — `t`'s relation carries a `Direct` arm the
  subject matches (`StoreValidRules`), fuel 1 (`semAux_seed`).
- **computed** hop (`u = ⟨s, R, o⟩` from `⟨s, R', o⟩`): `evalE`'s `computed R'` case is
  `rec o.type o.name R'`, which is *literally the predecessor's membership* — fuel `+1`,
  no rewriting of the recursion needed once `(objectType, matchRel)` are normalised to
  `x`'s fields.
- **ttu** hop (`u = ⟨s#tr, R, o⟩`): the tupleset tuple is a *stored* raw tuple —
  **`closure_tupleset_is_seed` (under `TtuTuplesetsDirect`) forces the predecessor `x`
  to be the seed `t ∈ T`** (a deeper closure tuple can't sit on a TTU tupleset relation:
  `no_rewrite_outputs_tupleset`). So `ttuLeaf`'s stored-tupleset read fires its **direct
  disjunct** (`s = x.subject#tr` matches `⟨pt,pn,tr⟩` in both the `pn≠STAR` and star
  branches) — **no recursion**, fuel 1. This is where the fragment condition earns its
  keep operationally.
- **union**: a true arm makes the OR-tree true (`evalE_{direct,computed,ttu}_arm`, one
  induction each — an `UntaintedSchema` def is a leaf-OR-tree, no `inter`/`excl`).

**Key modelling addition: `NodupKeys S`** (declared keys distinct — the Python schema is
a *dict*). `schemaRewrites` fans out over *all* defs (`flatMap`), but `sem`/`evalE` reads
`S.lookup` = the *first* def with a key; without key-uniqueness a rewrite rule's def
need not be the one `sem` evaluates, and soundness would be FALSE. `lookup_of_mem`
(`NodupKeys ⇒ d ∈ defs → lookup d.1 = some d.2`) is the payoff (hand-rolled `find?`
induction; `WF` currently records only `relNames`, so key-uniqueness is a *new* faithful
hypothesis, not derivable). **Worth flagging for W4:** the full-scope fragment should
carry `NodupKeys`.

**W2 read fragment (assembled):** `UntaintedSchema ∧ TtuTuplesetsDirect ∧ NodupKeys ∧
StoreValidRules ∧ StarFreeStore` (+ `WF`). Consequence lemmas landed: `untainted_noExclAll`
(⇒ `semAux_mono`), `stratifiable_untainted` + `storeDeclared_of_validRules` (⇒
`sem_fuel_stable` for the T0a-stability fuel sidestep), `exprDirects` +
`directTypes_mem_of_exprDirects`.

**Resume → the rest of the W2 soundness half + completeness + assembly.** Sharply
isolated:
1. **Chain composition (soundness end-to-end).** `reachedByRules_edge_sound` pins every
   edge to a rewrite-closure tuple of `Tstar := T.flatMap (rewriteClosure S)`; feed the
   `chainN_of_trail` soundness function to get `TupleChainN Tstar`, then compose hops
   with a **userset lift**. BLOCKER: `semAux_lift` (DirectCorrect) is stated for
   `PureDirect` — W2 needs it generalised to `UntaintedSchema` (a userset flowing
   through a `computed`/`ttu`/`union` node, not just a `direct` one). The per-hop base
   membership is `semAux_of_rewriteClosure` (at *some* fuel `f_w`, not fuel 1) — so use
   the W1c **T0a-stability sidestep** (`sem_fuel_stable`, whose hyps are the consequence
   lemmas above) to discharge total fuel, no tight bound. Intermediate userset predicate
   is `w.relation` (declared ⇒ ≠ `BARE`); subject names star-free (rewrites preserve
   subject name) — both need small preservation lemmas.
2. **Completeness (`sem ⇒ reach`).** `sem`'s computed/ttu/union recursion must be
   witnessed by graph edges (materialised rewrite-closure tuples). The harder direction;
   attack-first the computed-case closure-saturation the earlier entry flagged.
3. **Assembly** `graph_correct_rules` (route to `probeNonDerived` via
   `check_eq_probeNonDerived`; star-free ⇒ probes 2–4 dead) + T3/T6 widening.

## Session 2026-07-10 (W2 — attack-first KILLS the naive fragment; `TtuTuplesetsDirect` + rewrite-closure structure)

Resuming W2 (untainted rule routing) from "write model + read-routing + soundness
groundwork done; resume → the reachability↔`sem` core". Before proving that core,
ran the house move (**attack-first**) on the correspondence's TTU case — and it
**killed the naive W2 statement**: `check ≠ sem` without a storage-only tupleset
side condition. One green+pushed axiom-clean increment
(`GraphIndex/RulesCorrect.lean`, sorry count held at 0, `verify.sh` green: build +
0 sorries + 60 conformance + audit). This is the **fourth false-statement kill by
attack-first** (after additive `fuelBound`, the abstract `WriteStep` closure, and
T0a-without-`StoreDeclared`).

**Attack-first HEADLINE (machine-checked `#eval`, then deleted): the W2 `check =
sem` correspondence is FALSE without `_validate_ttu_tuplesets`.** Counterexample
(both `check`/`sem` evaluated in Lean on the operational `writeRules` state):
schema `doc#viewer := ttu member parent`, `doc#parent := computed linked`,
`doc#linked := direct [group]`, `group#member := direct [user]`; store
`(group:g, linked, doc:d)`, `(user:alice, member, group:g)`; query
`check(alice, viewer, doc:d)`. The graph rewrite-fanout of `(g, linked, d)`
cascades the computed rule `linked ↦ parent` producing `(g, parent, d)`, then fires
the TTU rule on that **rewrite-produced** triple → materialises
`g#member → viewer(d)`, so **`check = true`**. But `sem`'s `ttuLeaf` reads only
**stored** `parent` tuples (none — `parent` is computed) → **`sem = false`**.
Control with a directs-only `parent` (raw stored tupleset): both `true`, agree.

This is exactly `zanzibar_utils_v1.py:_validate_ttu_tuplesets` (:898): an *untainted*
tupleset relation with computed/rewritten arms is rejected at compile ("the graph
index cannot separate raw from rewritten members of an untainted relation"). **Key
subtlety: `GraphAccepts` clause (3) does NOT catch this** — a `computed`-armed
tupleset is untainted (`isDerived = false`), so it passes `GraphAccepts`. The W2
fragment needs the *stronger* directs-only condition, not just non-derived.

**Delivered (`GraphIndex/RulesCorrect.lean`, sorry-free, axiom-clean — all standard
axioms):**
- **`directsOnly : Expr → Bool`** (faithful `_directs_only`: `Direct` or `union`
  thereof) + **`TtuTuplesetsDirect S`** (faithful `_validate_ttu_tuplesets`: every
  TTU's tupleset relation, for every def carrying that key, is directs-only — stated
  over all matching defs so no key-uniqueness lemma is needed; implied by Python's
  dict keys).
- `exprArms_key` (a rule from `exprArms ot rel e` carries `(objectType,outRel) =
  (ot,rel)`) + **`exprArms_directsOnly`** (a directs-only expr yields NO rewrite arms
  — the core of the finding) + `schemaRewrites_provenance`.
- **`no_rewrite_outputs_tupleset`** — under `TtuTuplesetsDirect`, no schema rewrite
  outputs a TTU's tupleset relation (such a rule would come from a directs-only def,
  which contributes no arms).
- `applyRRule_object`/`applyRRule_outRel`, `rewriteStep_object`/`rewriteStep_outRel`,
  `rewriteClosureAux_object` → **`rewriteClosure_object`** (every closure tuple keeps
  the raw write's object — rewrites only change `(subject, relation)`) and
  **`rewriteClosure_seed`** (`t ∈ rewriteClosure S t`).
- `rewriteClosureAux_produced`/`rewriteClosure_produced` (every closure tuple is the
  raw seed or a rewrite output) → **`closure_tupleset_is_seed`** (the operational
  payoff: under the fragment condition a closure tuple sitting on a TTU tupleset
  relation IS the raw seed — so the graph only ever lands the raw seed on a tupleset
  relation, matching `ttuLeaf`'s stored-tupleset read; this is what will keep the
  deferred ttu correspondence sound).

**Resume → the W2 reachability↔`sem` core, now with the fragment nailed down.** The
fragment predicate is `UntaintedSchema S ∧ TtuTuplesetsDirect S` (+ `StoreValid`
analog). Structural groundwork is in place (object preservation, seed membership,
storage-only tuplesets). The remaining genuinely-new content is unchanged from the
prior entry — `TupleChain over the rewrite-closure T* ↔ sem over T` (computed = the
`rec`-indirection, absorbed by a rewrite hop; ttu = the stored-parent loop, now
provably reading only raw seeds via `closure_tupleset_is_seed`; union = the OR; fuel
via the W1c `sem_fuel_stable` sidestep) — then `graph_correct_rules` + T3/T6. NB the
computed case needs a "closure closed under the computed rewrite" step (a `T*` tuple
on relation `R'` whose def has a `computed R'`-armed relation `R` also has the
`R`-rewrite in `T*`); attack-first that closure-saturation before proving.

## Session 2026-07-10 (W2 STARTED — untainted rule routing; attack-first + the rewrite-fanout write model)

Resuming from W1 fully closed (all three sub-stages) → **ROADMAP stage W2** (rule
routing: `computed`, `union` of untainted operands, `ttu`). One green+pushed
axiom-clean increment: the **attack-first validation** and the **W2 write model**
(`GraphIndex/RulesWrite.lean`, sorry-free, axiom-clean `[propext, Classical.choice,
Quot.sound]`). `verify.sh` green (build + 0 sorries + 60 conformance + audit). Sorry
count held at 0. Mirrors how W1b/W1c landed their "write model DONE" increments before
the read correspondence.

**Attack-first HEADLINE (machine-checked `#eval` vs `sem`, then deleted): the
rewrite-fanout design is confirmed, no refutation.** The key modeling discovery from
reading `zanzibar_utils_v1.py` (`RuleSet.apply` / `_rewrite_rule` / `_emit_expr`): the
untainted graph index does NOT materialize edges *between* relation nodes. Instead **a
raw write of a public tuple `t` is expanded by `RuleSet.apply` into the rewrite-closure
of `t`** under the schema's Computed/TTU Rules (fan-in through unions, iterated to a
fixpoint), and *each* resulting triple is materialized as an ordinary direct closure
edge; **the ≤4-probe reachability read is unchanged**. The two rewrite kinds
(`_rewrite_rule`, `:834-852`):
- **Computed** `R := computed R'` on object type `ot`: a tuple `(s, R', o)` (o.type=ot)
  also produces `(s, R, o)` — same subject/object, relation `R'↦R`.
- **TTU** `R := ttu tr ts` on object type `ot`: a tuple `(s, ts, o)` (o.type=ot)
  produces `(⟨s.type, s.name, tr⟩, R, o)` — the tupleset parent `s` becomes the userset
  `s#tr`, relation `ts↦R`. (Stored-parent semantics: fires on the STORED tupleset
  tuple.) The produced edge is `objNode(⟨s.type,s.name⟩, tr) → objNode(o, R)`, which
  reachability then composes (`u → parent#tr → o#R`).
- **Union** `_emit_expr` walks INTO union nodes, so each arm's Computed/TTU leaf becomes
  a rule targeting the SAME relation; `Direct` arms are admission Filters (no fan-out).

Verified `sem` on a computed / chained-computed (`super:=editor:=viewer`) / ttu (±) /
union / userset-flow corpus — all seven `#eval`s matched hand expectations exactly, so
`sem`'s computed/union/ttu recursion is precisely what the rewrite-fanout materializes.
No statement-level surprise (like W1a/W1c; unlike W1b's bridges-mandatory finding).

**The write model (`GraphIndex/RulesWrite.lean`, axiom-clean):**
- `RuleKind` (`computed` | `ttu tr`) + `RRule` (objectType, matchRel, outRel, kind);
  `exprArms ot outRel : Expr → List RRule` (walks unions, one rule per Computed/TTU
  leaf, `[]` for Direct/inter/excl); `schemaRewrites S` = all rules of the schema.
- `applyRRule` (fire one rule on a matching tuple), `rewriteStep S t` (all matching
  rules fire — fan-in), `rewriteClosureAux`/`rewriteClosure S t` (bounded fixpoint,
  `|keys|+1` levels — the rewrite graph on relations is a DAG; duplicates harmless for
  reachability, §11-A4).
- **`GraphState.writeRules σ S t`** = `(rewriteClosure S t).foldl writeDirect σ` — the
  faithful `RuleSet.apply t` + per-triple `add_tuple`. Reuses ALL of W1's `writeDirect`
  machinery (cycle-rejection, residue-free).
- Fold-preservation helpers (`structInv_/residueEmpty_/inv_/quiescent_/schema_foldl_
  writeDirect`) ⇒ `structInv_writeRules`, `residueEmpty_writeRules`, **`inv_writeRules`**
  (full I-series `Inv` on the residue-free fragment — W2's T2a `Inv` conjunct), and
  `quiescent_writeRules`, all by folding the W1 single-write lemmas over the closure.
- **`ReachedByRules`** (the W2 write-closure; `ReachedByDirect` = the no-rules special
  case where `rewriteClosure = [t]`) + **`reachedByRules_inv`** (Inv ∧ ResidueEmpty ∧
  Quiescent at every W2-reachable state, by induction over the write path).

**Read-routing DONE (same session, `GraphIndex/RulesCorrect.lean`, axiom-clean).**
The fragment predicate `UntaintedSchema S` (no `.inter`/`.excl` in any def) collapses
taint: `baseTaint_untainted` → `taintStep_nil_untainted` → (`iterate_nil_fixed`)
`taintedKeys_untainted` (`= []`) → `isDerived_untainted` (`= false` for every key) →
**`check_eq_probeNonDerived`** — on this fragment `GraphModel.check` reduces to the
≤4-probe reachability read, the same one W1's `graph_correct_*` glue against. So the
residue path is provably never taken, and the correspondence now reduces to a pure
reachability ↔ `sem` argument.

**What remains for `graph_correct_rules` (`check = sem` on the untainted fragment),
the deferred next increment — the reachability ↔ `sem` core:**
1. (routing ✓ above) + the store-validity analog (`StoreValid`: raw writes name
   relations with a Direct arm). **Soundness groundwork ✓** —
   `reachedByRules_edge_sound` (`GraphIndex/RulesCorrect.lean`, axiom-clean): every edge
   of a `ReachedByRules` state materializes some `u ∈ rewriteClosure S t` for a stored
   `t` (the W2 analog of `reachedByDirect_edge_sound`, via `foldl_writeDirect_edges_sound`).
2. **The rewrite-closure ↔ `sem` correspondence** — the genuinely new content. The
   reduction that makes it tractable: `writeRules` materializes exactly the edges of the
   rewrite-closure `T*` of the store, so the goal factors as
   `probeNonDerived over T*-edges = sem over T`, and the existing W1 machinery already
   gives `reach ↔ NReaches ↔ TupleChain over T*`. The new lemma is **`TupleChain over
   T* ↔ sem over T`**: a rewrite-closure hop corresponds to `evalE`'s `computed`/`ttu`/
   `union` recursion. Soundness: a `T*` edge from a Computed/TTU rewrite is absorbed by
   the matching `evalE` case (computed = `rec otype oname R'`; ttu = the
   `ttuLeaf` stored-parent loop with the userset subject `s#tr`; union = the OR). NB the
   TTU rewrite produces a *userset* subject, so this reuses the userset-flow lift from
   DirectCorrect/UsStar. Completeness: `sem`'s computed/ttu/union recursion is witnessed
   by a rewrite-closure chain. Fuel: the T0a-stability sidestep (`sem_fuel_stable`) from
   W1c should transfer (the graph-hop/`sem`-fuel mismatch recurs — a rewrite chain of
   length `k` gives `semAux` at some fuel, lifted to `sem` by stability).
3. **Top-level glue** `graph_correct_rules` — route to `probeNonDerived` (point 1), glue
   the probe-1 disjunction via `reach ↔ NReaches` to the two directions. Then widen
   T3/T6 (`Equiv.lean`) as free corollaries.
NB W2's fragment is untainted rule routing ONLY; `and`/`but not` (residues, the
processor cascade) is **W3**, and the *combined* generality (wildcards + rules together)
lands at **W4**. Attack-first the correspondence's userset/TTU-flow lift before proving.

## Session 2026-07-10 (W1c FULLY CLOSED — `graph_correct_usStar`, full `check = sem`)

Resuming W1c from "both semantic cores closed; resume → the assembly + closure"
(the three sharply-isolated points below). Delivered all three as one green
increment plus a soundness sub-increment: **`graph_correct_usStar`**
(`GraphIndex/UsStarClosure.lean`, sorry-free, axiom-clean `[propext,
Classical.choice, Quot.sound]`) — the first *userset-wildcard* fragment where the
graph read provably equals `sem`. `verify.sh` green throughout (build + 0 sorries +
60 conformance + audit, all standard-axioms-only). This closes ROADMAP stage **W1c
end-to-end** (soundness + completeness), matching W1a/W1b.

**Point 1 — fuel-bounded soundness assembly, SIDESTEPPED via T0a stability (the
headline).** The ROADMAP flagged that the W1b plain-node fuel count "NEEDS ADAPTING"
for W1c — and it genuinely does *not* transfer: a userset-star grant's source is a
`w_any` node (not plain), an in-bridge consumes a `w_any` as a target, and the
`UsStarReach` chain over-counts (an in-bridge is a separate hop that the `sem`
derivation *absorbs* into the following userset-star grant). A tight `m ≤ fuelBound`
count would need `#w_any ≤ |keys|` accounting (`w_any` nodes are keyed by
`(type,relation)`). **Avoided entirely:** `semAux_of_usStarReach` gives a membership
at fuel = the chain length `m` for *some* `m`; `sem_fuel_stable` (T0a) makes `sem`
stable above `fuelBound`, so `sem = semAux (max m fuelBound) = true` by `semAux_mono`
(up to the max) then stability (down to `sem`) — **no bound on `m` needed**.
Delivered: `storeDeclared_of_storeValid` (the T0a `hDecl` hypothesis, from
`restrictionMatches`), `sem_of_usStarReach`, and `sem_of_usStar_probe` (the forward
direction from a covering probe source, via `usStarReach_of_trail`). This trick is
reusable for W1's later stages where the graph-hop/`sem`-fuel mismatch recurs.

**Point 2 — the admitted bridge-complete closure discharging `hEC` + `hib`.**
`UsStarReachedAdmitted` (W1c analog of `WildReachedAdmitted`): each write's grant
edge (`hadmGrant`) and — for each concrete bridged-in endpoint — its `c → w_any`
in-bridge (`hadmInA`/`hadmInB`, guarded by `bridgedInConcrete`) passed
cycle-rejection (the "no in-bridge cycle" fragment).
- `hEC` = `usStarReachedAdmitted_edge_complete` (mirror of the W1b edge-complete).
- **`hib` = `usStarReachedAdmitted_hib`**, the contentful part. Discharged via the
  **liveness invariant `usStarReachedAdmitted_inbridge_live`**: in the admitted
  closure, every *live* concrete bridged-in node has its in-bridge — because a
  bridged-in node is plain, so it enters `nodes` only as a write endpoint
  (`writeUsStar_new_plain_node`: the bridge machinery only adds non-plain `w_all` /
  `w_any` nodes), and that write ran `ensureInBridges` on it, materializing the
  bridge under the admission guard. `hib`'s in-edge guard (Point 3) → node live
  (endpoint-closure) → invariant → bridge. Shape membership via
  `isSWU_of_storeValid` (a stored userset-star grant's `(T,P)` is a declared
  subject-wildcard-userset shape — the matched `(T,P,true)` restriction occurs in the
  schema).

**Point 3 — `reach_of_semAux_us`'s `hib` REFORMULATED (a correctness fix, not just
plumbing).** The prior *unconditional* `hib` ("every `instances` witness of a
userset-star grant has its in-bridge") is **FALSE and undischargeable**: a name
`inst ∈ instances T q T` can occur in the store only with a predicate `≠ P`, so the
node `⟨T,inst,P⟩` is never a tuple endpoint and never bridged. But `sem` only *flows
through* such an `inst` when `rec T inst P = true`, which forces a stored `P`-grant
on `⟨T,inst⟩` — hence an **in-edge** into `subjNode ⟨T,inst,P⟩`. So `hib` is now
**guarded by that in-edge** (`∃ x, (x, subjNode ⟨T,inst,P⟩) ∈ edges`), which the
completeness proof produces from the recursion's reachability (`nreaches_last_edge`)
and the store-built graph provides (a reachable declared-SWU node was touched as an
endpoint). Re-proved `reach_of_semAux_us` green with the guarded hypothesis. Without
this fix the completeness core, though "proved," was stated over an unsatisfiable
hypothesis — the attack-first "store-bridges ↔ `instances` agree" finding was right
about the *live* names but the earlier `hib` over-claimed on all `instances`.

**Top-level glue** (`graph_correct_usStar`, mirror of `graph_correct_bareStar`):
routes to `probeNonDerived`; probes 3,4 dead (`usStarReached_edge_target_ne_wAll` —
no edge targets a `w_all`, objects star-free); probe 1 ∨ probe 2, with **probe 2
LIVE** for a userset query subject (its `wAny(s.shape)` sees userset-star direct
grants) and dead for a *bare* query subject (`usStarReached_edge_source_char` — a
bare-`w_any` node is never a source). Forward = `sem_of_usStar_probe`; backward =
`reach_of_semAux_us` with `hEC`/`hib` discharged.

**T3/T6 widened for free** (`Equiv.lean`): `backend_equivalence_usStar` /
`exclusion_effective_usStar` / `no_ghost_grant_usStar` (T1 ∘ `graph_correct_usStar`),
axiom-clean; audit +10 lines (7 W1c assembly + 3 corollaries).

**Next: ROADMAP W2** (rule routing — `computed` / `union` of untainted operands /
TTU defs route onto rule-derived families). W1 (wildcard bridges) is now complete
across all three sub-stages (W1a bare star / W1b object wildcards / W1c userset
stars), each with `graph_correct_*` closing `check = sem`. Note the W1c fragment
isolates userset stars (objects star-free, no object wildcards in the store); W1's
*combined* generality (userset + object wildcards together) lands with the full-scope
restatement in W4. Attack-first the W2 rule-edge soundness before proving.

## Session 2026-07-10 (W1c BOTH SEMANTIC CORES CLOSED — completeness `reach_of_semAux_us` + soundness `UsStarReach`)

Resuming W1c from "write model + edge characterization done; the read-correspondence
core is the genuinely hard remaining work." Delivered **both semantic halves** of the
W1c read correspondence as two green+pushed axiom-clean increments — mirroring how W1b
landed its two cores (`ObjStarCorrect.lean`) before the assembly (`ObjStarClosure.lean`).
`verify.sh` green throughout (build + 0 sorries + 60 conformance + audit). Sorry count
held at 0. All new theorems standard-axioms-only.

**Increment 1 — the completeness core (`reach_of_semAux_us`, `sem ⇒ probe 1 ∨ probe 2`).**
Fuses W1a's probe-2 disjunction with W1b's bridge threading — here the `concrete →
w_any` **in-bridge**. Stated over the two operational facts it consumes: edge-completeness
`hEC` and **in-bridge completeness** `hib` (every `instances` witness of a userset-star
grant has its `c → w_any` bridge), deferring the discharging closure exactly as
`reach_of_semAux_os` deferred to `hEC`/`hbr`. Supporting:
- `instances_ne_star` — no `∃`-witness population name is the STAR sentinel (foldr
  peeling, mirrors `instances_subset_storedNames`).
- `directLeaf_elim_us` — userset-star-aware leaf elim (exact | userset-star direct match
  of the query's shape | flow-through); the bare-star disjunct dies by `UsStarStore`.
- `mog_elim_us` — flow-through elim admitting the `instances`-branch (plain userset |
  userset-star + instance witness) that `mog_elim`/`_os` could not fire.
- Cases: exact → probe 1; userset-star grant of `s`'s shape → probe 2 (`wAny(s.shape) →
  objNode`, unreachable via probe 1 for a query-only ghost — the attack-first
  endpoint-exclusion finding); plain flow → extend recursion by the grant edge;
  userset-star flow → thread the concrete instance's in-bridge (`hib`) then the grant.

**Increment 2 — the soundness core (`UsStarReach` chain + both directions).**
- **KEY SIMPLIFYING FINDING: an in-bridge hop needs NO instance witness for soundness.**
  A concrete `c` reaching a userset-star grant through its `c → w_any` in-bridge always
  corresponds to `c` matching that grant **directly** in `sem` (a pure shape-match, `c`
  has the grant's shape by construction — unconditionally valid, ghost or not). So
  `UsStarReach`'s `inbridge` constructor carries no `instances` field and
  `usStarReach_of_trail` needs **no** in-bridge-soundness hypothesis. The instance
  condition is a *completeness*-only concern (`hib`), where `sem`'s flow-through demands
  a genuine `instances` witness.
- The lift is the crux and genuinely NEW vs W1b: `semAux_lift_os` **cannot** absorb a
  userset-star grant (its `directLeaf_elim_os` has no userset-star disjunct). New
  `semAux_lift_us`: an intermediate userset `s'` matching a userset-star grant directly
  is absorbed via the **outer subject `s`'s `instances`-branch flow-through** (witness
  `s'.name`) — needing `s'.name ∈ instances`, always dischargeable because every chain
  intermediate is a tuple object (`objectName_mem_instances`). Where the instances
  condition genuinely lives in soundness: not in the chain, but in this lift's hypothesis.
- Supporting: `mog_intro_star`, `directLeaf_grant_usStar` / `semAux_one_of_usStarGrant`
  (userset-star direct-match intros), `objectName_mem_instances`, `semAux_one_of_tuple_us`,
  `UsCovers` (probe-1 ∨ probe-2 chain start, userset analog of W1a's `Covers`),
  `semAux_one_covers_us`.
- `UsStarReach T n u v` (base | hop | inbridge, no `q`/`instances`); `semAux_of_usStarReach`
  (chain ⇒ `sem` at fuel `n`: base/hop via the lift, inbridge = a direct shape-match on
  `c` + `semAux_mono` bump); `usStarReach_of_trail` (trail ⇒ chain: edge classification;
  out-bridges dead from a plain/`wAny` source, `w_any` targets excluded because the
  concrete query object node is plain). Existence only — no fuel bound threaded yet.
- Strengthened `usStarReached_grant_or_bridge` (+ `writeUsStar_edges_mem` /
  `bridgeLayers_edges_mem`) to expose `pred ≠ BARE` on in-bridge sources (needed for the
  `inbridge` constructor's `hcp`).

**What remains for `graph_correct_usStar` (full `check = sem`), sharply isolated:**
1. **Fuel-bounded soundness assembly** — `usStarReach_of_trail` gives existence `∃ m,
   UsStarReach m …`; the top-level needs `m ≤ fuelBound`. **The `isPlain`-source count
   argument (W1b's `grantReach_of_trail` strengthening) needs ADAPTING**: a userset-star
   grant's source is a `w_any` node, not plain, and an in-bridge consumes a `w_any` as a
   target — so "every hop source is plain" (W1b) is FALSE here. Likely bound: count
   distinct plain trail vertices + `w_any` vertices, or bound `m` by trail length
   directly (each graph edge = ≤ 1 chain hop, and trail length ≤ nodes.length after
   compression). Re-derive the tight `fuelBound` fit.
2. **The admitted, bridge-complete write-closure** discharging `reach_of_semAux_us`'s
   `hEC` + `hib` — the W1c analog of `ObjStarClosure.lean`'s `WildReachedAdmitted`. `hib`
   (in-bridge completeness) is the contentful part: every store userset-star grant `g`
   and every `inst ∈ instances T q g.subject.type` has its materialized `subjNode
   ⟨T,inst,P⟩ → w_any(T,P)` bridge. This is exactly the attack-first "store-bridges ↔
   `instances` agree by construction" finding, now to be proved operationally (a
   concrete of a bridged-in shape gets its in-bridge when touched as a tuple endpoint —
   `writeUsStar`'s `ensureInBridges`).
3. **Top-level `check = sem` glue** — route to `probeNonDerived`, kill probes 3,4 (objects
   star-free ⇒ no `w_all` target), glue probe 1 ∨ probe 2 via `reach ↔ NReaches` to
   completeness (backward) and the fuel-bounded chain (forward). Probe 2 is LIVE here
   (unlike W1b): a userset query subject's `wAny(s.shape)` sees userset-star direct
   grants. Mirror of `graph_correct_bareStar` (which also had probe 2 live).

## Session 2026-07-10 (W1c STARTED — userset stars `[group:*#member]`; attack-first + in-bridge write model + edge characterization)

Resuming from W1b fully closed → **ROADMAP stage W1c** (userset-wildcard *subject*
grants `[group:*#member]`, `concrete → w_any` **in-bridges** — the genuinely hard
sub-stage, spec §1.1). Two green+pushed axiom-clean increments; `verify.sh` green
throughout (build + 0 sorries + 60 conformance + audit). Sorry count held at 0.

**Attack-first HEADLINE (machine-checked, no `native_decide`): the correspondence
holds; `instances` ↔ store-bridges agree by construction.** Verified `GraphModel.check
= sem` on 12 userset-star scenarios in a scratch module (deleted after), incl. the
sharp **endpoint-exclusion** cases the ROADMAP flagged. The finding: a group name is
in `sem`'s `instances T q group` iff it appears in a **tuple** (not merely as a query
endpoint), which is **exactly** when the store-built graph has that concrete's
in-bridge — so the store-derived bridge set and `instances` coincide; a query-only
name (`ghost`) is in neither. No refutation. The one *apparent* divergence was an
**admission-invalid tuple** (a concrete userset `group:eng#member` grant against a
`[group:*#member]`-only restriction: `restrictionMatches` fails since the restriction
requires `wildcard=true`), re-confirming StoreValid is load-bearing exactly as in the
direct/objStar fragments. Unlike W1b (bridges proven MANDATORY), W1c had no
statement-level surprise — the design was confirmed as-is.

**Increment 1 — the faithful in-bridge write model (`GraphIndex/UsStarWrite.lean`,
sorry-free, axiom-clean):**
- `Schema.isSubjectWildcardUserset` — the `bridged_in_shapes` predicate
  (`zanzibar_utils_v1.py:264-270,784-789`): `p ≠ BARE` and some `[t:*#p]` restriction
  `(t,p,true)` occurs in the schema. (TTU-through-shape extension `:795-803` out of
  scope for this TTU-free fragment.)
- `GraphState.bridgedInConcrete` + `ensureInBridges` — lazily create
  `w_any(c.type,c.pred)` + the guarded `c → w_any` in-bridge (cycle-rejection,
  `wildcard.py:120-129`).
- `GraphState.writeUsStar` — faithful `add_tuple`: endpoint nodes, out-bridges (W1b,
  inert here) then in-bridges (bridge-before-grant), then the cycle-rejected grant; a
  rejected grant rolls back the whole write.
- `nodeEnc_wAnyNode` (needs NO axioms); `ensureInBridges_mono`/`_schema`.
- `structInv_ensureInBridges` — an in-bridge preserves `StructInv` (w_any
  encoding-valid; bridge edge cycle-admitted).
- `structInv_writeUsStar` — the whole write preserves `StructInv` (acyclicity through
  **both** bridge families + the grant).
- `UsStarReached` (the W1c write-closure) + `usStarReached_structInv`/`_schema` —
  `StructInv` at every W1c-reachable state.

**Increment 2 — the edge characterization (`GraphIndex/UsStarCorrect.lean`, sorry-free,
axiom-clean `[propext]`):** the structural fact the soundness chain will classify each
trail hop against. `UsStarStore` (fragment predicate: objects star-free, star subjects
non-bare); `bridgedInConcrete_elim`; `ensureInBridges_edges_mem`;
`bridgeLayers_edges_mem` (peels the 2 out + 2 in bridge layers of `writeUsStar`);
`writeUsStar_edges_mem`; **`usStarReached_grant_or_bridge`** — every edge of a
`UsStarReached` state is a stored **grant**, a `w_all → concrete` **out-bridge**, or a
`concrete → w_any` **in-bridge**, by induction over the write path.

**What remains for `graph_correct_usStar` (`check = sem`), sharply isolated (the
genuinely hard core — the ROADMAP-flagged W1c difficulty):**
1. **The in-bridge-absorbing chain** (analog of W1b's `GrantReach`). The new
   absorption: a `concrete c → w_any(shape)` in-bridge **followed by** a userset-star
   grant `w_any(shape) → objNode` is one generalized hop — the graph counterpart of
   `sem`'s `memberOfGranted` `instances`-branch (`Semantics.lean:50-56`: a userset-star
   grant `g=(T,*,P)` expands over `instances T q T`, checking `rec T inst P` for each
   `inst`). The soundness key: `inst = c.name` must be in `instances` (⇔ c appears in a
   tuple ⇔ c has its in-bridge — the attack-first finding). NB the userset `w_any` node
   here is BOTH an edge target (in-bridges) AND source (the grant) — unlike W1b's
   `w_all` (target only) and W1a's bare `w_any` (source only).
2. **The `instances`-branch of `memberOfGranted`** — the subject-side leaf lemmas
   (`mog_elim`/`directLeaf_elim`) must now admit the star-userset grant disjunct
   (currently killed by star-free-subject in W1b's `_os` versions). The `instances`
   ∃-witness expansion is the new content vs W1a/W1b.
3. **Probe 4** (`w_any → w_all`) — for a star *userset* query subject. Dead on W1b's
   object side; live here.
4. **Bridge-completeness** (an admitted closure, W1b-analog): every store concrete of a
   bridged-in shape has its `c → w_any` bridge — `instances`-coverage. The endpoint
   exclusion is what makes this match `instances` (store-derived, excludes query-only
   names).
5. **Fuel-bounded soundness assembly** — as W1b (`m ≤ 2|T|+1`); the in-bridge hops
   consume `w_any` nodes (not plain sources), so the plain-node accounting should
   transfer, but a `w_any` node is now also a source (the grant), so re-check the
   `isPlain`-source argument (`grantReach_of_trail`'s "every hop source is plain" no
   longer holds — a userset-star grant's source is `w_any`).

## Session 2026-07-10 (W1b FULLY CLOSED — `graph_correct_objStar`, full `check = sem`)

Resuming W1b from "both semantic cores done + completeness operationally closed;
what remains is the SOUNDNESS side + top-level assembly." Delivered the
**fuel-bounded soundness assembly** and the **top-level `check = sem` glue**, closing
**W1b end-to-end**: `graph_correct_objStar` (`GraphIndex/ObjStarClosure.lean`,
sorry-free, axiom-clean `[propext, Classical.choice, Quot.sound]`). `verify.sh` green
throughout (build + 0 sorries + 60 conformance + audit). Sorry count held at 0. This
is the first *object-wildcard* fragment where the graph read provably equals `sem`.

**The fuel bound was the genuine remaining piece** (ROADMAP-flagged multi-hour). The
soundness chain `semAux_of_grantReach` gives fuel = the `GrantReach` length `m`, and
`m ≤ fuelBound` needs the tight `m ≤ 2|T|+1` — the crude `m ≤ nodes.length` is too
weak because `writeWild` adds up to 4 nodes/tuple (2 endpoints + 2 `w_all`), so
`nodes.length ≤ 4|T|` overshoots `fuelBound = |keys|(2|T|+4)` at `|keys|=1`. The key
observation formalized: **every `GrantReach` hop's *source* is a `plain` node** —
`w_all` nodes are consumed mid-hop by a grant+bridge pair, never a hop source — so the
chain length is bounded by the count of *distinct plain* trail vertices, of which
there are ≤ `2|T|`.

**Delivered:**
- **`NodeKey.isPlain`** + **`trail_compress_nodup`** + **`nodup_countP_le`**
  (`GraphIndex/State.lean`) — a nodup-preserving trail compression, and the bound
  `l.Nodup → (∀ x∈l, x∈N) → l.countP p ≤ N.countP p` (distinct predicate-hits inject
  into `N.filter p`).
- **`grantReach_of_trail` strengthened** (`GraphIndex/ObjStarCorrect.lean`) — now also
  yields `m ≤ (subjNode s :: l).countP NodeKey.isPlain`. Each hop accounts for exactly
  one plain vertex (its source); the `w_all` node of a bridge hop contributes 0. Base
  hops account for the leading `subjNode s`. Threaded through the existing peeling
  induction with no change to its structure. `isPlain_subjNode`/`isPlain_wAllNode`
  helpers.
- **Plain-node accounting** (`GraphIndex/ObjStarClosure.lean`):
  `ensureBridges_plainCount` (bridges only ever add `w_all` nodes ⇒ plain count
  unchanged), `writeWild_plainCount_le` (≤ 2 plain nodes/write), and
  `wildReachedAdmitted_plainNodes` (`plain-node count ≤ 2|T|`).
- **Dead `w_any` probes** — `wildReached_edge_source_ne_wAny` (an edge source is a
  star-free `subjNode` grant source or a `w_all` bridge source, never `w_any`) +
  `nreaches_first_edge`, killing read probes 2 and 4.
- **`grantReach_mem`** — a `GrantReach` witnesses a stored tuple (for
  `lookup_keys_nonempty` in the fuel arithmetic).
- **`graph_correct_objStar`** — `check σ q = sem S T q` on the W1b fragment
  (object-star, admission-valid, object-wildcard-valid store; star-free query),
  end-to-end. Forward: probe-1/probe-3 hit → nodup trail → `GrantReach` →
  `semAux_of_grantReach` at fuel `m ≤ 2|T|+1 ≤ fuelBound` → `semAux_mono`. Backward:
  `graph_complete_objStar` + `reach_complete`. Probes 2,4 dead; audit updated
  (5 new `#print axioms` lines).

**T3/T6 widened for free (`Equiv.lean`):** since the equivalence + security
corollaries are one-line `rw`s through `graph_correct_*`, added
`backend_equivalence_objStar` / `exclusion_effective_objStar` /
`no_ghost_grant_objStar` — T3/T6a/T6b now hold on object-wildcard stores too
(T1 ∘ `graph_correct_objStar`). Axiom-clean; audit +3 lines.

**Next: ROADMAP W1c** (userset stars `[group:*#member]` — in-bridges + `instances` +
probe 4; the genuinely hard sub-stage). Attack-first first.

## Session 2026-07-10 (W1b COMPLETENESS CLOSED operationally — `graph_complete_objStar`)

Resuming W1b from "both semantic cores done, discharge the operational hypotheses."
Delivered the **admitted, bridge-complete write-closure** and used it to discharge
**both** operational hypotheses (`hEC`, `hbr`) that `reach_of_semAux_os`
(completeness core) was stated over — so the W1b completeness direction is now a
real, operationally-closed theorem. New file `GraphIndex/ObjStarClosure.lean`,
sorry-free, all six audited theorems axiom-clean (subset of the three standard
axioms). `verify.sh` green throughout (build + 0 sorries + 60 conformance + audit).
Sorry count held at 0.

**Delivered (`GraphIndex/ObjStarClosure.lean`):**
- `writeWildPre` (the fully-bridged pre-grant state) + `writeWild_eq_ite` (the write
  as an `ite` over it, definitional) — lets the closure state grant admission over
  the bridged state and lets edge lemmas skip the `let` chain.
- Edge-monotonicity through the bridge machinery (`ensureBridges_edges_mono`,
  `writeWildPre_edges_mono`, `writeWild_edges_mono`), the grant-edge and
  bridge-edge creation lemmas (`writeWild_grant_edge`, `ensureBridges_creates_bridge`).
- **`WildReachedAdmitted`** — the composed-system closure (W1b analog of
  `ReachedByAdmitted`): each write's grant edge (`hadmGrant`) AND its *subject*
  endpoint bridge (`hadmSub`) passed cycle-rejection. Carrying `hadmSub` is exactly
  the "no wildcard-own-shape cycle on subjects" fragment on which bridge-completeness
  holds; the object-endpoint bridge is handled internally by `ensureBridges` (both
  outcomes are valid states), so it is not required. Embeds into `WildReached`
  (`wildReached_of_admitted`); schema fixed (`wildReachedAdmitted_schema`).
- **`wildReachedAdmitted_edge_complete`** (`hEC`) — every stored grant's edge is
  present (mirror of `admitted_edge_complete`; new edges added, old edges monotone).
- **`wall_reach_isObjectWildcard`** (Lemma A) — a reachable `w_all(T,R)` node forces
  `S.isObjectWildcard T R`: its only in-edges are grant edges (bridge targets are
  plain, `nreaches_last_edge` + the grant-or-bridge characterization), from
  object-wildcard grants, which `ObjStarValid` puts on a declared object-wildcard
  shape.
- **`wildReachedAdmitted_bridge_complete`** (bridge-completeness) — every stored
  grant whose *subject* shape is a declared object-wildcard has its materialized
  `w_all → concrete` bridge (new writes create it via `writeWild_subjBridge`; old
  bridges persist). This is the invariant that, with Lemma A, discharges `hbr`.
- **`wildReachedAdmitted_hbr`** — the `hbr` discharge: reachability of `g.subject`'s
  `w_all` node forces the object-wildcard shape (Lemma A), and bridge-completeness
  then supplies the bridge.
- **`graph_complete_objStar`** — the operationally-closed W1b completeness theorem:
  on `WildReachedAdmitted` over an object-star, admission-valid, object-wildcard-valid
  store, a `sem` membership at `fuelBound` is reachability to probe 1 (concrete
  object node) ∨ probe 3 (`w_all` node). `reach_of_semAux_os`'s two operational
  hypotheses are gone.

**What remains for the full `graph_correct_objStar` (`check = sem`), sharply
isolated — only the SOUNDNESS side + assembly:**
1. **Fuel-bounded soundness assembly.** `semAux_of_grantReach` (done) gives fuel =
   the `GrantReach` length `m`; the top-level theorem needs `m ≤ fuelBound`. The
   crude `m ≤ nodes.length + 1` is too weak (duplicate `w_all` nodes inflate
   `nodes.length` past `fuelBound` when `|keys| = 1`). The tight bound is `m ≤ 2|T|`
   (distinct plain source nodes — each grant hop consumes a distinct plain source in
   a compressed/nodup trail; `w_all` nodes are not plain). Formalizing that
   distinctness bound (strengthen `grantReach_of_trail` to bound `m` by the plain
   vertex count) is the remaining arithmetic. The *completeness* side needs no fuel
   bound (this session).
2. **Top-level `check = sem` assembly** — route the read to `probeNonDerived`
   (pure-direct = untainted), kill probe 2 (star-free subjects) and probe 4, and
   glue probe 1 ∨ probe 3 via `reach ↔ NReaches` to the two directions
   (`graph_complete_objStar` backward; the fuel-bounded `GrantReach` chain forward).
   Mirror of `graph_correct_direct` / `graph_correct_bareStar`.

## Overnight autonomous run (2026-07-09 → 07-10)

User granted full autonomy ("keep going til you're done, I'll review tomorrow in one
go"). Plan, in priority order, committing each GREEN increment and documenting every
decision here:
1. Harden the spec: randomized conformance fuzzing (sem vs oracle vs set engine over
   random tuple subsets + grids). Safe (pure Python); catches spec bugs like the
   fuelBound one. Any unresolved divergence → adjudication log, don't block.
2. Concrete set-engine `expand` model (remove `opaque SetEngineModel.check`) + prove
   T1 with the algebra lemmas. Main proof effort.
3. Attempt T0a pigeonhole (`semAux_fuel_stable_step`) and T0b Kahn lemmas.
4. Attempt T4: define `pathCount` concretely, prove the first-edge recurrence + the
   counting theorem.
5. Shrink the opaque surface: concrete graph state types (even if T2/T5 stay sorry).
6. Final documentation + review summary.
Discipline: never commit a broken build; if a proof stalls past reasonable effort,
leave a documented `sorry` and move on. Update this file continuously.

## Overnight run RESULT (2026-07-10, end of session)

Delivered, all green + pushed (see REVIEW.md for the digest):
- **Found + fixed a real spec bug** (`fuelBound` additive→multiplicative), confirmed
  empirically, locked with the `deep_grid` regression. This was the headline outcome.
- **Conformance: 15 schemas, 60 tests green** (handwritten + randomized), three
  evaluators (`sem` / oracle / real set engine) agree everywhere. Added adversarial
  boolean corners (taint-over-boolean, nested boolean, double exclusion).
- **Proved (axiom-clean):** full MemberSet algebra + membership/constructor lemmas;
  `restrictionMatches_type` / T6c (real, not placeholder); `sem_fuel_stable` (T0a)
  reduced to one pigeonhole lemma. Axiom audit shows no custom axioms.
- **Tooling:** `zcli` CLI, `verify.sh` green gate, `Audit.lean` axiom check.
- **Handled a Gemini review:** adopted the valid fuelBound catch + WellDef
  decomposition (corrected); rejected the `phat_def` axiom (C4 cleanliness).

Remaining = the irreducible hard core (9 sorries): T1 (needs concrete expand model),
T2a/b + T5 (need concrete graph state machine), T4 counting (needs concrete pathCount
+ combinatorics), T0a pigeonhole core, T0b Kahn. All honestly deferred — NONE faked.
These want fresh context + the statement-review feedback; each is multi-hour.

**Next session resume:** see `formal/ROADMAP.md` (per-sorry plan, with corrections to
a Gemini roadmap). Phase 3 T1: the boolean STAR cases are done (`containsStar_*`); the
remaining nut is the INTENSIONAL `containsShape` distribution for concrete/ghost
subjects under a WF invariant — attempted this session, `simp; tauto` did NOT close
it (goal too large), so it's documented in ROADMAP with the intended route (a
`containsShape` normal-form lemma + per-atom split) rather than left as a `sorry`.
Gemini corrections logged: its set-engine model used `MemberSet String` (unsound —
name collisions across types; use `String × String`); its T0a pigeonhole is invalid
(our `semAux` has no visited-set); its T4 `phat_def` axiom rejected (C4 gate).

## Session 2026-07-10 (W1b SOUNDNESS + COMPLETENESS CORES — `GrantReach` + `reach_of_semAux_os`)

Resuming W1b (object wildcards `[T:*]`) from the write model (previous session).
Delivered **both semantic halves** of the read correspondence as self-contained
honest increments (two green+pushed commits), each stated over the operational
facts it consumes so the write-closure that discharges them can land next. New
file `GraphIndex/ObjStarCorrect.lean`, sorry-free, all six audited theorems
axiom-clean (`wildReached_grant_or_bridge` = `[propext]` only; the rest a subset
of the three standard axioms). `verify.sh` green throughout (build + 0 sorries +
60 conformance + audit). Sorry count held at 0.

**Completeness core (`reach_of_semAux_os`)** — the analog of W1a's
`reach_of_semAux_bs`, but the disjunction is on the **object** side (probe 1 =
concrete object node ∨ probe 3 = `w_all` node): a direct match on a concrete grant
hits probe 1, on a `T:*` grant hits probe 3; a flow-through prepends the
recursion's path, **through a bridge hop** when the recursion reached the userset
via its own `w_all` node. Stated over two operational facts (like the soundness
core is stated over the edge characterization): `hEC` (edge-completeness — every
stored grant's edge present) and `hbr` (a grant subject reachable via its `w_all`
node has its materialized `w_all → concrete` bridge). Needs **no fuel bound** (it
goes `sem ⇒ reach`, and `sem` is already at `fuelBound`). The write-closure that
discharges `hEC`/`hbr` (an admitted, bridge-complete closure) is the deferred
increment.

The soundness core (below) reads existing edges only, so it needs **neither
bridge-completeness nor the admitted-writes refinement**.

**The idea that tames the bridges.** A W1b graph path interleaves *grant* hops
(`subjNode s → objNode o R`, subjects star-free) and *bridge* hops
(`w_all(T,R) → concrete`, materialized by `writeWild`). The soundness argument
**absorbs each `grant-into-w_all` + `bridge-out` pair into a single generalized
grant against a *concrete* object**, keyed through `matchingObjects`: a `T:*`
grant is in `grantsOf` for *every* concrete object of type `T` (spec §3.4's
`subject → w_all(S) → concrete` composition, realized semantically). So a wildcard
grant plus its bridge is ONE hop in the abstracted chain; only the final target
may be a bare `w_all` node (the read's probe-3 endpoint).

**Delivered (`GraphIndex/ObjStarCorrect.lean`):**
- `ObjStarStore` (subjects star-free; objects may be `T:*`).
- **Edge characterization** `wildReached_grant_or_bridge` — every edge of a
  `WildReached` state is a stored grant (`subjNode t.subject → objNode t.object
  t.relation`, subject star-free) OR a `w_all → concrete` bridge
  (`a = wAllNode b.type b.pred`, `b` plain concrete). By induction over the
  bridge-materializing write path, via `writeWild_edges_mem` /
  `ensureBridges_edges_mem` (the edge effect of the nested bridge-before-grant
  write) and `bridgedConcrete_elim`.
- **`GrantReach`** — the bridge-absorbing generalized grant chain (3 constructors:
  `base` = one grant matching a concrete object via `matchingObjects`; `starBase`
  = a terminal grant landing on the `w_all` node; `hop` = a grant then continue
  from the concrete userset node). Every interior node is concrete; only the final
  target may be `w_all`.
- Object-star leaf lemmas (`mog_elim_os` / `directLeaf_elim_os` / `semAux_lift_os`
  / `semAux_one_of_grant`) — the subject-side leaf interface reused from
  DirectCorrect, needing only that grant *subjects* are star-free (object
  wildcards live on the object side; `semAux_one_of_grant` takes the
  `matchingObjects` match as a hypothesis so it covers both concrete and wildcard
  grants uniformly).
- **`semAux_of_grantReach`** (soundness's semantic half) — a `GrantReach` of
  length `n` from a star-free subject node to a node matching the concrete query
  object (`matchesObj`) is a `sem` membership at fuel `n`; base hops are
  self-grants keyed through `matchingObjects`, each `hop` lifts via
  `semAux_lift_os`. The bridge-aware analog of `semAux_of_chainN`.
- **`grantReach_of_trail`** (soundness's reachability half) — every graph trail
  from a star-free subject node is a `GrantReach`, by strong induction on trail
  length, peeling a grant (1 edge, `hop`/`base`/`starBase`) or a grant+bridge
  (2 edges, `hop`/`base`) at each step, classified by the edge characterization
  (a plain-source edge is a grant; a `w_all`-source edge is a bridge).

**What remains for `graph_correct_objStar`, sharply isolated (both semantic
halves are now DONE — what is left is the operational discharge + arithmetic):**
1. **The admitted, bridge-complete write-closure** that discharges `hEC`
   (edge-completeness — mirror of `admitted_edge_complete`) and `hbr` (the bridge
   hypothesis). This needs the **bridge-completeness invariant** (every live
   bridged-concrete node has its `w_all → c` bridge) maintained along a closure
   where grants AND the endpoint bridges are admitted (the "no wildcard-own-shape
   cycle" fragment), plus `ObjStarValid` (a `T:*` tuple is on a declared
   object-wildcard shape, so a reached `w_all` node's shape is bridged — turning a
   reached `w_all` into a live bridged-concrete whose bridge exists). The
   admission-threading through `writeWild`'s nested `ensureBridges` is the fiddly
   part; the semantic use-sites are already proved.
2. **Fuel-bounded top-level assembly** (soundness side only) —
   `semAux_of_grantReach` gives fuel = the `GrantReach` length `m`; the top-level
   theorem needs `m ≤ fuelBound`. The crude `m ≤ nodes.length + 1` is too weak here
   (the write can create up to `~4|T|` nodes incl. duplicate `w_all` nodes, and
   `fuelBound` with `|keys| = 1` is only `2|T|+4`). The tight bound is `m ≤
   (distinct plain source nodes) ≤ 2|T|` — each grant hop consumes a distinct plain
   source node in a compressed (nodup) trail. Formalizing that distinctness bound is
   the remaining arithmetic. (The *completeness* side needs no fuel bound.)
These are the next increment; both semantic cores (soundness `GrantReach ⇒ sem` +
`trail ⇒ GrantReach`, completeness `sem ⇒ probe 1 ∨ probe 3`) are done.

## Session 2026-07-10 (W1b STARTED — object wildcards; bridges proven MANDATORY + the bridge-materializing write model)

Resuming from W1a → **ROADMAP stage W1b** (object wildcards `[T:*]`, `w_all` +
out-bridges). `verify.sh` green throughout (build + 0 sorries + 60 conformance +
audit); all four new theorems axiom-clean (`nodeEnc_wAllNode` needs *no* axioms;
the rest `[propext, Classical.choice, Quot.sound]`). Sorry count held at 0.

**Attack-first HEADLINE (machine-checked): W1b is NOT bridge-free.** The natural
guess after W1a was symmetry: a bare-star *subject* node has no in-edges (pure
*leading* hop, probe 2 absorbs it, zero bridges), so maybe an object-wildcard
`w_all` node — never a `subjNode`, hence never an edge *source* — is a pure
*trailing* hop that probe 3 absorbs, also bridge-free. **Refuted against the real
`GraphModel.check`/`sem`** (`#eval`, no `native_decide`): an object-wildcard grant
that flows into a *further* userset hop needs the wildcard membership to reach the
**concrete** object node, which only a `w_all → concrete` bridge provides. The
refuting scenario: `viewer := [group#member, user]`, `editor := [doc#viewer]`,
`member := [user]`, object-wildcard `(doc, viewer)`; store `group:eng#member viewer
doc:*`, `doc:readme#viewer editor doc:readme`, `user:alice member group:eng`; query
`check(alice, editor, doc:readme)` — `sem = true` but the bridge-free `writeDirect`
state answers **false** (`alice → group:eng#member → w_all(doc,viewer)` dead-ends;
never reaches `⟨doc,readme,viewer,plain⟩` that `editor` routes through). Adding the
single bridge `w_all(doc,viewer) → ⟨doc,readme,viewer,plain⟩` restores `true`. This
realizes wildcard-spec §3.4's composition `subject → w_all(S) → concrete → …`. The
ROADMAP W1a note's optimistic "maybe W1b is also bridge-free" is now closed off.

**Cycle question RESOLVED from the Python** (`wildcard.py:222-259`): `add_tuple`
is **bridge-before-grant** (`_ensure_bridges(subject); _ensure_bridges(obj)` first,
creating `w_all` lazily + the out-bridge for each concrete endpoint of a bridged
shape, then the cycle-rejected grant edge). A wildcard tuple whose object
participates in its own shape would close a cycle through a bridge and is
**rejected at the grant edge** (`wildcard.py:250-256`) — so acyclicity (I2) is
preserved by cycle-rejection, not violated. A rejected write rolls back the whole
transaction (bridges included). Per-endpoint `ensureBridges` maintains
bridge-completeness with no separate `w_all`-arrival backfill: a concrete object
node exists only as an edge endpoint, so it self-bridges the first time it is
touched.

**Delivered — the faithful bridge-materializing write model
(`GraphIndex/ObjStarWrite.lean`, sorry-free, axiom-clean):**
- `GraphState.bridgedConcrete` (a concrete node whose object-shape `(type,pred)` is
  a declared `objectWildcards` shape — the nodes needing a `w_all → c` in-bridge).
- `GraphState.ensureBridges c` — create `w_all(c.type,c.pred)` lazily + the guarded
  bridge edge `w_all → c` (cycle-rejection via `admitEdge`, matching the core add).
- `GraphState.writeWild t` — bridge-before-grant: add endpoint nodes, ensure both
  endpoints' bridges, then the cycle-guarded grant edge; a rejected grant returns
  the original state (full rollback).
- `nodeEnc_wAllNode` (w_all nodes are encoding-valid); `ensureBridges_mono`
  (nodes grow); `ensureBridges_schema`/`writeWild_schema`; `writeWild_monoNodes`.
- **`structInv_ensureBridges`** — a bridge insertion preserves `StructInv` (the
  `w_all` node is encoding-valid; the bridge edge is cycle-admitted so
  `structInv_addEdge` applies; the concrete endpoint must already be live).
- **`structInv_writeWild`** — the whole write preserves `StructInv` (node encoding,
  endpoint closure, **acyclicity through both the bridges and the grant**).
- `WildReached` (the W1b operational write-closure, analog of `ReachedByDirect`) +
  **`wildReached_structInv`** — `StructInv` at every W1b-reachable state, by
  induction over the bridge-materializing write path.

**What remains for the W1b correspondence (`graph_correct_objStar`), sharply
isolated:** (1) **bridge-completeness invariant** maintained along `WildReached`
(every concrete of a bridged shape has its `w_all → c` bridge) — holds on the
fragment where no bridge cycle-rejects, i.e. no wildcard-own-shape cycle; (2) the
read = `sem` proof **with bridge hops**. The read reduces to probe 1 ∨ probe 3
(subjects star-free ⇒ probes 2,4 dead, mirror of W1a's dead 3,4). The new semantic
content: a graph path may now interleave **grant hops** (`subjNode s → objNode o R`)
and **bridge hops** (`w_all(T,R) → ⟨T,o,R,plain⟩`), and a grant-into-`w_all`
immediately followed by a bridge-out is EXACTLY the `matchingObjects on = [on, STAR]`
absorption in `sem` (a STAR-object grant is in `grantsOf` for concrete query object
`o`). The soundness/completeness inductions (analogs of `semAux_of_chainN_bs` /
`reach_of_semAux_bs`) must key the terminal/interior grant's object match through
`matchingObjects` rather than equality, and thread the bridge hop. This is the next
increment; the write model + structural invariant under it is now done.

## Session 2026-07-10 (W1a CLOSED — `graph_correct_bareStar`, bare star grants)

First scope-widening increment after the tree hit 0 sorries: **ROADMAP stage
W1a** — widen T2b (graph read = `sem`) to allow **bare star grants** `[user:*]`
(subject `(T,*,BARE)` tuples) in the store. Per wildcard-spec §3.2's bare-shape
rule this needs **ZERO materialized bridges**. `verify.sh` green (build + 0
sorries + 60 conformance + audit); `graph_correct_bareStar` axiom-clean
(`[propext, Classical.choice, Quot.sound]`). Sorry count held at 0.

**House move first (attack before prove):** machine-checked `check = sem` via
`#guard` on concrete bare-star scenarios in a scratch module — single grant,
wrong-type non-coverage, no-leak-to-usersets, 2-hop bare-star→userset
flow-through, concrete+star coexistence — **no refutation**, then deleted the
scratch and proved it.

**The modeling fact that makes W1a bridge-free** (spec §3.2): a bare-concrete
subject node `⟨T,u,BARE,plain⟩` has **no in-edges** (an in-edge target is an
`objNode`, whose predicate is a *relation* name, never `BARE`), and the star node
`wAny(T,BARE) = ⟨T,*,BARE,wAny⟩` has no in-edges either. So a bare-star grant is a
pure *leading* hop = the read-side `wAny` endpoint substitution of **probe 2**. No
interior hop exists to materialize. `subjNode` already sends `(T,*,BARE) ↦
wAny(T,BARE)`, so the write model is already correct — the work is entirely in the
correspondence.

**New file `GraphIndex/BareStarCorrect.lean` (sorry-free, axiom-clean):**
- `BareStarStore` (star subjects must be bare; objects star-free) / `NoUsersetStar`
  fragment predicates. `BareStarStore` is strictly weaker than `StarFreeStore`.
- `directLeaf_elim_bs` — **3-way** leaf elimination (exact `g.subject = s` | a
  bare-star grant covering a bare-concrete `s` | flow-through); the userset-star
  disjunct is killed by `NoUsersetStar`. The 2-way `directLeaf_elim` of
  DirectCorrect is *false* once bare-star grants can match a concrete subject.
  `mog_elim_nus` is the `NoUsersetStar` generalization of `mog_elim`.
- `semAux_lift_bs` — userset lifting, bare-star aware (the userset it lifts
  through is non-bare, so the extra bare-star match is vacuous).
- `Covers s u := u = subjNode s ∨ (s.predicate = BARE ∧ u = wAnyNode s.shape)` +
  `semAux_one_covers` + **`semAux_of_chainN_bs`** (soundness): generalizes the
  chain base from "the first tuple's subject *is* the query subject" to "*covers*
  it" — a `[T:*]` grant covers every bare-concrete subject of type `T`
  (`semAux_one_of_bareStar`, a pure type-match, `directLeaf`'s second bare-conc
  disjunct). Interior hops stay plain (bare-star can only be the *first* tuple of a
  chain, since after it every node is a plain `objNode`).
- **`reach_of_semAux_bs`** (completeness): `sem` ⟹ reachability from `subjNode s`
  **OR** from `wAny(s.shape)` — the probe-1 ∨ probe-2 disjunction. A bare-star
  direct match reaches from the star node, not the plain subject node; exact match
  and flow-through keep `s` fixed and preserve whichever disjunct the recursion
  produced.
- `admitted_edge_source_char` — every edge source is plain or a bare-`wAny` node
  (`pred = BARE`); a **userset**-`wAny` node is *never* an edge source (would need a
  userset-star tuple, forbidden by `BareStarStore`), so probe 2 is provably dead
  for a userset query subject.
- **`graph_correct_bareStar`** — `check = sem` on the widened fragment, end-to-end:
  probes 3–4 dead (star-free objects ⇒ no `wAll` target), probe 1 (plain) + probe 2
  (`wAny`-bare) live via `Covers`/`semAux_of_chainN_bs` (fwd) and
  `reach_of_semAux_bs` (bwd); probe 2 dead for userset subjects.

Reused unchanged from DirectCorrect: all pureDirect/lookup/node-algebra/grant/
matchingObjects/`TupleChainN`/`chainN_of_trail`/`admitted_*`/`ReachedByAdmitted`/
`directLeaf_grant_self`/`directLeaf_of_mog`/`mog_intro`/`semAux_mono` lemmas.
`graph_correct_direct` (StarFreeStore) is left intact — `BareStarStore` is the
weaker predicate; a future cleanup could make the star-free theorem a corollary,
but it is not needed. Audit updated (6 new `#print axioms` lines).

**Next: ROADMAP W1b** (object wildcards `wAll` + out-bridges) — the first stage
that *does* need bridge machinery. Attack first (a `[T:*]`-object grant vs probe 3).

## Session 2026-07-10 (T0a CLOSED — sorry count 0)

Same session as the falseness finding below: after restating over
`StoreDeclared`, the corrected theorem was **fully proved** — the last tracked
`sorry` is discharged, axiom-clean (`[propext, Classical.choice, Quot.sound]`,
audited). `verify.sh` green (build + 60 conformance + audit; **sorries = 0**).

**The proof architecture (4 green commits, each layer reusable):**

1. **Confinement (`Spec/Confine.lean`)** — `evalE_congr`/`step_congr`: two `rec`s
   agreeing on the consulted atom space (`exprRefs` keys × own-name ∪
   `storedNames`) evaluate identically. `directLeaf`'s certificate comes from
   `grantsOf`'s restriction filter (unconditional); `ttuLeaf`'s is exactly
   `StoreDeclared`. Undeclared keys are constantly `false` (`semAux_undeclared`).
2. **Untainted phase (`Spec/Stabilize.lean`)** —
   - `chain_stabilizes`: generic monotone + deterministic + `N`-bounded `Finset`
     chains from `∅` are stable from `N` on (used twice).
   - `untainted_closed`: `taintedKeys` is a genuine `taintStep` fixpoint (via the
     chain lemma on the taint iteration!), so untainted declared keys are
     boolean-free and reference only untainted keys.
   - `semAux_mono_untainted`: relative fuel-monotonicity at untainted relevant
     atoms — proved by **masking** `rec` outside the consulted space
     (`evalE_congr` says evaluation can't tell) and reusing the *global*
     `evalE_mono`; no second leaf induction. This trick halved the file.
   - `untainted_stable`: the true-set on `atomsU = untaintedKeys × relevantNames`
     grows monotonically, is deterministic (`step_congr`), hence stable from
     `N = |atomsU|` on.
3. **Kahn interface (`Spec/WellDef.lean`)** — `kahn_topo_strict` (dep edges point
   to STRICTLY earlier layers; a within-layer edge contradicts readiness),
   `stratify_covers` / `stratify_layers_tainted` (layers = exactly the tainted
   keys), `stratify_length`.
4. **Assembly (`Spec/WellDef.lean`)** — `layer_stable` (strong induction on the
   layer index: a layer-`i` key consults only undeclared / untainted / strictly
   lower layers, so it stabilizes at `N + 1 + i`), `all_stable` (every relevant
   atom stable from `N + 1 + |L|`), and the arithmetic
   `N + 1 + |L| ≤ K(2|T|+1) + 1 + K ≤ K(2|T|+4) = fuelBound` (needs `K ≥ 1`;
   `K = 0` is the everything-undeclared case, trivially stable).

**Where each hypothesis is load-bearing:** `hDecl` in `step_congr`'s ttu case
(without it the consulted space leaves `exprRefs` — the counterexample below);
`hStrat` in coverage + strict topology (without it a tainted key has no layer /
no strictly-decreasing rank).

**Phase-6 items pulled forward (same session):** `verify.sh` gates [2] and [4]
are now HARD — sorry count must be 0, and every audited theorem must show only
`propext`/`Classical.choice`/`Quot.sound` (any `sorryAx`, `ofReduceBool`, or
custom axiom fails the gate; validated end-to-end green). Also: ROADMAP W1 got
a grounded sub-staging design (W1a bare star grants = ZERO bridges via the
wildcard-spec §3.2 bare-shape rule → W1b object wildcards → W1c userset stars +
`instances`), each with the matching `sem` branch identified, plus an
attack-first note. **Recommended next session: the W1a attack + widening.**

## Session 2026-07-10 (T0a FOUND FALSE AS STATED — restated over `StoreDeclared`)

Attacking the last `sorry` (`semAux_fuel_stable_step`), the first move was to
stress-test the *statement* — and it is **FALSE over an arbitrary store**,
machine-checked in Lean (`Spec/Counterexample.lean`, axiom-clean, no
`native_decide`):

- **The hole:** `ttuLeaf` consults `rec` at the subject of every stored tupleset
  tuple with **no restriction check** (faithful to the oracle's `ttu_leaf`, which
  also has none). Taint/`depEdges` predict TTU consultations from the *declared*
  restriction types (`directTypes`). An admission-invalid tuple therefore creates
  a consultation edge invisible to stratification — and it can close a cycle
  through an `excl` subtrahend.
- **The counterexample** (2 keys, 3 tuples): `(A,p) := direct[user] but not
  ttu(q, ts)`, `(C,q) := ttu(p, ts)` — `(A,ts)`/`(C,ts)` UNDECLARED — plus store
  tuples `C:c ts A:o` and `A:o ts C:c` closing the loop `(A,p)@o → (C,q)@c →
  (A,p)@o`. `S` is stratifiable (`depEdges = []`); `semAux` **oscillates with
  period 4 forever**: the proved recurrence is `semAux (n+2) = !(semAux n)` at
  the query atom (`T0aCounter.oscillates`), refuting the old statement
  (`T0aCounter.fuel_stable_step_false`). Empirically confirmed by `#eval` first.
- **Resolution (documented precondition materialized, NOT a weakening):**
  `SEMANTICS.md` §8 already says stores hold *write-valid tuples*, and the real
  admission gate (`engine.py:_validate` (2), shared by both backends) rejects
  exactly such tuples ("matches no declared type restriction"). New
  `StoreDeclared S T` (`Spec/Confine.lean`) captures the needed clause — every
  stored tuple's `(object.type, relation)` is declared and its subject type is
  among the declared restriction types; it is *implied by* the gate, so every
  reachable store satisfies it. `semAux_fuel_stable_step` / `sem_fuel_stable`
  now carry `hDecl : StoreDeclared S T`. The counterexample store violates it
  (`T0aCounter.not_storeDeclared`).
- **Conformance note:** the corpora are admission-valid, so `sem` = oracle stays
  green; the divergence (oracle's visited-set answers `true` stably, `sem`
  oscillates) exists only on stores the system cannot hold.
- Also fixed pre-existing breakage: `Audit.lean` still referenced
  `writeDirect_writeStep`/`reachedBy_of_direct` (deleted with the abstract
  layer); the stale `.olean` had masked it. The audit now rebuilds clean.

This is the third statement-level defect caught by attack-before-prove (after
the additive `fuelBound` and the abstract-closure falsehood). The `sorry` count
stays 1 — now a TRUE statement worth proving.

## Review handled 2026-07-10 (second Gemini review, post-restatement)

User shared a Gemini review after the restatement. Vetted against the repo;
outcomes (logged per the review-handling norm):
- **T4 section MOOT / stale-state error:** it presents an algebraic path "to
  close the `sorry`" in `pathCount_addEdge` and calls T4 a "main remaining
  hurdle" — T4 was closed 2026-07-09 (sorry-free, axiom-clean, in the audit).
  Its proposed expansion also uses ℕ-subtraction (`phat g a b - [a=b]`), the
  exact trap the real proof avoided via `rec_unique`. No action.
- **T0a lattice framing ADOPTED as a tactical note** (ROADMAP T0a section):
  monotone iteration on a finite Bool-lattice bounded by height, + one fuel
  step per Kahn rank. With the vetting caveat it glossed: `Rec` is not finite
  a priori — the confinement-to-reachable-atoms lemma remains the load-bearing
  prerequisite.
- Endorsements (operational-trace restatement, `fuelBound` multiplicativity,
  `instances`/`universe` ghost handling, W3 `upos ∩ neg = ∅` expected easy)
  are consistent with the repo; no changes needed.

## Session 2026-07-10 (abstract closure DELETED — T-theorems restated operationally)

User adjudication: **"if anything is incorrect then delete it and rewrite the
plan; the end goal is still a formally verified Zanzibar/OpenFGA model tied to
the Python implementation."** Executed the deletion + restatement; `verify.sh`
green (build + audit + 60 conformance).

**What was deleted (false or assertion-backed, per the same-day FINDING):**
- `WriteStep` / `ReachedBy` (State.lean) — the abstract postcondition closure;
  admitted junk states (nothing tied `σ.edges`/`σ.residue` to the store).
- `graph_correct`, `graph_reached_inv` (Correct.lean) — **false as stated**;
  these were the 2 tracked T2 sorries.
- `backend_equivalence`, `exclusion_effective`, `no_ghost_grant` (Equiv.lean) —
  also false as stated (same junk-state counter-model); they had been "proved"
  only by `rw` through the false `graph_correct`.
- `cascade_converges` (old form) — true only because `WriteStep` *asserted*
  drainedness; `writeDirect_writeStep`, `reachedBy_of_direct` (Write.lean).

**⚠ `sorry` count 3 → 1 BY DELETION, NOT PROOF.** The full-scope obligations are
not gone — they return as ROADMAP stage W4 (restatement over the completed
operational write model). This is recorded loudly to keep the count honest.

**What replaced it (all real, proved, axiom-clean, sorry-free):**
- `graph_reached_inv` (T2a) + `cascade_converges` (T5) restated over
  `ReachedByDirect` in Correct.lean (one-liners off `reachedByDirect_inv`;
  fragment scope: writes produce no deltas, so T5 is trivially drained until
  the reconcile model lands).
- T2b = `graph_correct_direct` (DirectCorrect.lean, unchanged from the morning
  session).
- `backend_equivalence` (T3), `exclusion_effective` (T6a, deny-propagation at
  this scope — the fragment has no exclusions; the exclusion content arrives at
  W3/W4), `no_ghost_grant` (T6b) restated over `ReachedByAdmitted` in
  Equiv.lean, proved via T1 ∘ T2b-fragment + new `stratifiable_pureDirect`.
- Audit updated: `backend_equivalence` moved OUT of the sorryAx section; only
  `sem_fuel_stable` (T0a) remains there.

**Plan rewritten (ROADMAP top):** the end-goal architecture (sem↔Python via the
conformance harness; T1 done; T2 via staged operational write model; T3/T6
corollaries that widen per stage) + the staged T2 plan **W1 bridges → W2 rule
routing → W3 reconcile → W4 full-scope restatement**, plus a Phase-6
**graph-model conformance extension** (drive the Lean `writeDirect`/`check`
against the Python graph index) so the graph side gets the same executable tie
to the implementation that `sem` already has.

## Session 2026-07-10 (T2b SEMANTIC CORE CLOSED — `graph_correct_direct` on the fragment)

User: "assess, update the plan, then start on the hardest thing." Two assessment
outcomes, then the proof work:

**Assessment finding 1 (recorded in ROADMAP): the two T2 sorries are FALSE as
stated, not merely unproven.** `WriteStep`'s three thin postconditions (schema
fixed, nodes monotone, outbox drained) never tie `σ.edges`/`σ.residue` to the
store, and neither does `Inv` — a junk state carrying one arbitrary acyclic edge
satisfies `ReachedBy σ S [t]` + `Inv` + all schema hypotheses while `check` ≠
`sem`. So no proof effort can close `graph_correct`/`graph_reached_inv(Inv)` as
written; the operational write model is mandatory *for truth*. They stay as
tracked sorries only as placeholders for the eventual restatement over the
operational closure. Do not attack them as written.

**Assessment finding 2:** `ReachedByDirect` prepends a *rejected* write's tuple to
the store (writeDirect no-ops but `T` grows) — unfaithful to the composed system,
where the raised rejection rolls back the store insert too. Hence
`ReachedByAdmitted` (every step passed `admitEdge`), the faithful closure, on
which the edge set is **complete** for the store, not just sound.

**Proof work delivered (all green + pushed, axiom-clean, `verify.sh` full gate
incl. 60 conformance; `sorry` count held at 3 — nothing faked, the new theorem is
an addition, not a placeholder discharge):**

- **`semAux_mono`** (`Spec/FuelStable.lean`): fuel monotonicity of the evaluator
  on exclusion-free schemas (`Schema.noExclAll`), lifted from `evalE_mono`.
  Dual-use: T2b soundness fuel plumbing + a T0a untainted-layer ingredient.
- **New `GraphIndex/DirectCorrect.lean`** (~550 lines, sorry-free):
  - Fragment predicates `PureDirect` / `StoreValid` (the Python admission gate) /
    `StarFreeStore`, with `isDerived_pureDirect` (pure-direct ⇒ untainted ⇒ the
    read routes to `probeNonDerived`), `lookup_rel_ne_bare` (declared relation ≠
    `BARE`, via `WF.relNames` — `"..."` contains `'.'`), `lookup_keys_nonempty`.
  - `ReachedByAdmitted` + embedding into `ReachedByDirect`,
    **`admitted_edge_complete`** (every stored tuple's edge present), and
    `admitted_nodes_length` (`nodes = 2·|T|`, the fuel-bound arithmetic).
  - Star-free node algebra: `subjNode_plain`/`objNode_plain`, injectivity, and
    **`objNode_eq_subjNode`** — the flow-through identity that makes chain hops
    compose with `memberOfGranted`'s recursion.
  - `TupleChainN` (length-indexed chains) + `chainN_of_trail`.
  - The `directLeaf`/`memberOfGranted` interface: `grantsOf` pack/unpack,
    `directLeaf_grant_self`, `directLeaf_of_mog`, `mog_intro`, and the star-free
    eliminations `mog_elim`/`directLeaf_elim` (the `instances` branch cannot fire).
  - **`semAux_lift` — the semantic heart.** Membership propagates through a
    userset (`s ∈ s'` at fuel `f₀`, `s' ∈ v` at fuel `f` ⇒ `s ∈ v` at `f + f₀`):
    every direct match of `s'` at a grant is absorbed by `s`'s flow-through on the
    *same* grant (+ fuel monotonicity); every flow-through lifts by the fuel IH.
  - **`semAux_of_chainN`** (soundness): a length-`n` chain is a `sem` membership
    at fuel exactly `n` (base hop = self-grant at fuel 1; each hop lifts, f₀ = 1).
  - **`nreaches_of_semAux`** (completeness): fuel induction; direct match ⇒ the
    grant's own edge (edge-completeness), flow-through ⇒ IH + `.tail`.
  - **`graph_correct_direct`** — `check σ q = sem S T q` on the fragment,
    end-to-end: wildcard probes 2–4 die on star-free data (`nreaches_source/
    target_plain`), probe 1 bridges `reach ↔ NReaches ↔ compressed trail ↔
    TupleChainN ↔ sem`, chain fuel fits `fuelBound` (`2|T|+1 < |keys|·(2|T|+4)`).
  - Audit: `graph_correct_direct` = `[propext, Classical.choice, Quot.sound]`.

**This discharges the ROADMAP-isolated "T2b semantic core" (chain =
`memberOfGranted` recursion, both directions) on the honest fragment.** What
remains for T2: wildcard bridges (model + read, the `wAny`/`wAll` promotion only
covers the first hop), TTU/computed/union defs (rule-routed materialization),
the derived/residue path + faithful reconcile (T2a), then the restated full T2b.

## Session 2026-07-10 (T2b groundwork — read=sem base case + soundness scaffold)

User: "keep going with the proof part T2; commit and push when ready." Scope
continues the deliberate honest DEFER: no full T2b close (the `TupleChain ↔ sem`
core is multi-session), but **four green+pushed axiom-clean increments building the
read=`sem` correspondence from both ends.** `sorry` count held at 3; `verify.sh`
green throughout (build + 60 conformance + audit; audit now tracks all seven new
lemmas, no `sorryAx`).

**T2b base case CLOSED end-to-end (`GraphIndex/Correct.lean`):**
- `evalE_empty_store` / `semAux_empty_store` / **`sem_empty_store`** — `sem S [] q
  = false` (empty store grants nothing; `computed` recurses into a uniformly-`false`
  `rec`, by fuel induction).
- `probeNonDerived_empty` / `probeDerived_empty` / **`check_empty`** — the empty
  index reaches nothing and persists no residue, so `check (emptyState S) q = false`.
- **`graph_correct_empty`** : `check (emptyState S) q = sem S [] q`. This is exactly
  the `ReachedBy.empty` case of `graph_correct` — the genuine base of its eventual
  induction, no `sorry`.

**Read lifted into the relational world (`GraphIndex/State.lean`):**
- **`probeNonDerived_iff`** — on an endpoint-closed state the executable ≤4-probe
  read equals the disjunction of the four `NReaches` conditions (subject/object each
  literal or promoted to its wildcard node), via `reach_iff_nreaches`. Moves the read
  off the fixed-fuel probe `σ.reach` into fuel-free `NReaches`, where the semantic
  correspondence will be argued.

**Reachability→`sem` soundness scaffold (`GraphIndex/Write.lean`):**
- **`writeDirect_edges`** — an accepted write prepends exactly the one materialized
  edge `subjNode t.subject → objNode t.object t.relation`; a rejected write is the
  identity on edges.
- **`reachedByDirect_edge_sound`** — every edge of a `ReachedByDirect` state
  materializes some stored tuple (unconditional; induction over the write path).
- **`TupleChain`** + **`reachedByDirect_nreaches_chain`** — a graph path in the
  untainted fragment IS a stored-tuple membership chain (consecutive hops share the
  intermediate node = userset flow-through). Every `NReaches` path is a `TupleChain`.
  This is the soundness direction of T2b's reachability half, fully relational.

**The remaining T2b core, now sharply isolated:** the semantic content is
**`TupleChain T u v ↔ sem`-membership** — matching the membership chain against
`directLeaf`/`memberOfGranted`'s userset recursion, the wildcard nodes (`wAny`/`wAll`
promotion in `probeNonDerived_iff`), `instances`, and `matchingObjects`. Plus the
converse edge-completeness (`TupleChain → NReaches`) which needs an acyclic-*data*
hypothesis (`writeDirect` drops cycle-forming edges while `sem` fuel-evaluates them —
the T2b subtlety flagged last session). The read/reachability plumbing is now done
on both ends; what is left is the genuine `chain = recursion` semantic core. The
derived (residue) path of T2b and the full-generality `graph_reached_inv` `Inv`
conjunct (derived reconcile) remain the other deferred halves, unchanged.

## Session 2026-07-10 (T2a write model — untainted direct fragment)

User: "clear T2 as much as possible; commit often, push when done." Scope call
(user-adjudicated up front via a fidelity question): **build the concrete write
model, honest, no discharge expected this session.** Continues the deliberate
DEFER — the abstract `WriteStep` is now being *realized operationally* rather than
strengthened by postulate. Two green+pushed increments; `sorry` count held at 3;
all new results axiom-clean (audited).

**New file `GraphIndex/Write.lean` — the concrete single-tuple write for the
untainted (residue-free) fragment:**

- `writeDirect` — materialize one direct tuple as the edge `subjNode s → objNode o
  R`, **guarded by cycle-rejection** (§7.3: a self-loop or back-path-forming write
  is rejected and leaves the state unchanged; the back-path premise for
  `structInv_addEdge` comes from the executable admission probe via
  `reach_complete`). `admitEdge` is the decidable admission Bool.
- `nodeEnc_subjNode`/`nodeEnc_objNode` — endpoint nodes are always encoding-valid.
- `structInv_writeDirect` — structural invariant preserved by the write.
- `ResidueEmpty` + `residueEmpty_writeDirect` — the fragment (no persisted
  residues) is closed under writes; `inv_writeDirect` then preserves the **whole**
  `Inv` (residue clauses vacuous).
- `writeDirect_writeStep` — the concrete op realizes the abstract `WriteStep`
  (schema fixed, nodes monotone, quiescence preserved).
- `ReachedByDirect` (concrete write-closure) + `reachedByDirect_inv` — **T2a's
  `Inv` conjunct, honestly proved for the untainted fragment** (Inv ∧ ResidueEmpty
  ∧ Quiescent at every reached state, by induction over the write path).
  `reachedBy_of_direct` embeds it in the abstract `ReachedBy`.

**What this does NOT yet close, sharply isolated for the next pass:**
1. **Derived reconcile (rest of T2a).** `writeDirect` covers only untainted
   closure edges. The derived path (§7.6/§7.8) must (a) materialize residues via a
   faithful `reconcile`, and (b) handle the cross-key hazard the current fragment
   dodges by `ResidueEmpty`: an edge write can make an existing residue's `neg`/
   `upos` subject edge-reachable, breaking `negEdgeFree`/`uposEdgeFree` until the
   cascade re-reconciles. `inv_putResidue` (State.lean) is the per-key tool; the
   write must apply it to *all* reachability-affected keys with the correct
   residues.
2. **Read correspondence `check = sem` (T2b).** For the pure-direct fragment
   `check` reduces (no-wildcard) to `reach = NReaches`, and NReaches on the
   writeDirect-built edges *should* equal `directLeaf`'s transitive membership —
   BUT the subtlety is cycle-rejection: `writeDirect` silently drops cycle-forming
   edges, so on cyclic *data* the graph's edge set differs from "all tuples" while
   `sem` fuel-evaluates. The correspondence needs an acyclic-data hypothesis (or to
   account for rejected writes). Do NOT rush this — it is the genuine T2b core.

## Session 2026-07-10 (T2a groundwork — reachability layer fully proved)

User: "get the rest of T2 finished; commit often, push whenever you can." Scope
call (user-adjudicated mid-session via a fidelity question): **keep T2a honest,
DEFER** — do not postulate I6 as a `WriteStep` postcondition (the A1-style
operational shortcut was explicitly declined for `Inv`); instead **build toward the
genuine close** (the `reach ↔ NReaches` stabilization + a faithful reconcile). No
`sorry` discharged (count held at 3, as the user accepted); six green+pushed
increments of genuine, axiom-clean infrastructure delivered. `verify.sh` green
throughout (build + 60 conformance + audit).

**All in `GraphIndex/State.lean`, all axiom-clean (three standard axioms or fewer):**

- **Fuel-free reachability `NReaches`** (transitive closure of the edge list;
  distinct from WellDef's `Key`-typed `Reaches`). `Inv`'s reachability clauses
  (`acyclic`/`negEdgeFree`/`uposEdgeFree`) restated over it — this sidesteps the
  `nodes.length`-fuel churn that perturbs a capped probe when a write adds nodes.
  Lemmas: `NReaches.tail/trans/mono`, `NReachesR.trans`, `nreaches_nil`,
  `nreaches_cons_split` (first-use decomposition), **`acyclic_addEdge`**
  (cycle-rejection preserves acyclicity — the load-bearing I2 lemma).
- **Write-path primitives + preservation.** `addNode`/`addEdge`/`putResidue` with
  `@[simp]` projections; `StructInv` (the 4 structural clauses) + `structInv_addNode`
  / `structInv_addEdge` (genuine, cycle-rejection via `acyclic_addEdge`) /
  `structInv_empty` / `Inv.toStruct`; **`inv_putResidue`** (full `Inv` preserved by
  writing one I6-hygienic residue — other keys untouched; depends on *no* axioms).
- **`reach ↔ NReaches` BRIDGE — the ROADMAP-flagged "T2b blocker", now CLOSED.**
  `reachB_sound` + `reachB_mono` (soundness, any fuel); `reachB_of_nreaches` +
  `nreaches_iff_reachB` (unbounded equivalence); then the **shortest-walk
  compression** — `Trail` walk API (`trail_split`, `reachB_of_trail`,
  `trail_of_nreaches`, `trail_verts_mem`), pigeonhole plumbing (`mem_split_aux`,
  `exists_dup_split`, `nodup_len_le`), **`trail_compress`** (a walk with interiors
  in `nodes` shortens to ≤ `nodes.length` interiors), giving **`reach_complete`** and
  **`reach_iff_nreaches`**: the executable fixed-fuel probe `σ.reach` EXACTLY decides
  `NReaches` on any endpoint-closed state.

**What still blocks the two T2 sorries (unchanged in kind, now sharply isolated):**
the **faithful write/reconcile model** — how one tuple write produces the exact
edges + reconciled residues. Needed by BOTH: T2a (global I6 re-establishment after
edge changes — `inv_putResidue` handles one key; the write must cover all
reachability-affected keys with the *semantically correct* residues, so a
delete-only "reconcile-by-construction" is unfaithful and would break T2b) and T2b
(`check = sem` — the ≤4-probe decomposition now has its reachability half via the
bridge, but still needs the residue = `sem` half from the write model). This is the
genuine multi-session core; the reachability layer under it is now done.

## Session 2026-07-10 (T2 graph model CONCRETIZED — T5 closed)

**Scope decision (user-approved): "concretize + partial proofs," not the full T2
close** (T2 is the ~half-effort multi-session core; a faithful full close isn't
honestly doable in one pass, and a cooked `check := sem` model was explicitly
rejected). Delivered, `verify.sh` green (build + 60 conformance + audit),
count **4 → 3**:

- **All 7 opaque graph placeholders are now CONCRETE** (`GraphIndex/State.lean`,
  `sorry`-free): `GraphState` (nodes with `plain/wAny/wAll` variants, direct edges,
  residues `(stars,neg,upos)`, outbox+watermark), `GraphModel.check` (the faithful
  §7.5 ≤4-probe read + §7.6 residue path, routed by `isDerived`), `Inv` (I-series
  core: node encoding, I1 endpoint existence, I2 acyclicity, I6 residue hygiene incl.
  the load-bearing `neg ∩ edge-holders = ∅`), `ReachedBy` (inductive write-closure
  from `emptyState` via a minimal operational `WriteStep`), `Quiescent`
  (outbox-drain), `GraphAccepts` (decision-15 scope). The C4 "pending opaque" list
  for the graph model is cleared.
- **Reads model reachability, not path counts.** `check` probes a fuel-bounded
  transitive closure `reachB` of the direct edges (`p(u,v)>0`), factoring the
  path-*counting* layer out to `Closure.lean`/T4 — this dodges threading a
  `Fintype NodeKey` (infinite key space) through the read and keeps `check`
  executable. `Inv.acyclic` pins the DAG property T4 needs.
- **T5 `cascade_converges` CLOSED, axiom-clean** (`[propext]`). The model bakes the
  in-txn cascade into each write (§7.8 / A1, user-approved), so outbox-drain is a
  `WriteStep` postcondition and `Quiescent` holds at every reachable state by
  induction on `ReachedBy`.
- **T2a `graph_reached_inv`**: the `Quiescent` conjunct is closed (via
  `cascade_converges`); the `Inv` conjunct stays a tracked `sorry` (needs the full
  operational write path — edge/bridge/reconcile — which `WriteStep` abstracts).
- **Partial base-case lemmas, axiom-clean:** `inv_empty`, `quiescent_empty`,
  `reach_empty` (`reachB [] = false`).

**Remaining 3 sorries:** `semAux_fuel_stable_step` (T0a); `graph_reached_inv`'s `Inv`
half and `graph_correct` (T2b, the read = `sem` completeness argument) — the genuine
deep content, deferred as before. The concretization makes those statements relate
*real* definitions (not opaque constants), so the next attempt starts from a concrete
model rather than a stub.

## Session 2026-07-09 (T1 FULLY CLOSED — set engine = sem)

**T1 is DONE** — `setEngine_correct` is proved and axiom-clean (`[propext,
Classical.choice, Quot.sound]`, verified in `Audit.lean`). Count 5 → 4. `verify.sh`
green (build + 60 conformance + audit). The `opaque SetEngineModel.check` is replaced
by a concrete MemberSet-expand model. **T1 needs no WF/Stratifiable/AllValid** — the
hypotheses are retained (underscored) but unused: the expansion computes `semAux` at
*every* fuel, so equality at the shared `fuelBound` is unconditional.

**The model (`SetEngine/Eval.lean`).** `Id := SubjectRef`; `expandAux` is pure
fuel-recursion mirroring `semAux` (`expandStep`/`expandE` mirror `step`/`evalE`);
boolean nodes fold with `union`/`intersect`/`subtract`; leaves are `grantMS`/`parentMS`
(token `singletonEntity`/shape `star` + flow-through recursion), faithfully
transcribing `engine.py:direct_expand`/`ttu_expand`. `check` = `containsShape` of the
expanded query node at the query subject.

**The key modeling insight (makes the whole thing tractable).** `containsShape` *never
reads `pop`* — only `pos`/`stars`/`neg`. The distribution lemmas
(`containsShape_*_focus`) prove the probe answer is invariant across *any* population
satisfying `PopFocus`/`WFp`/`Grounded`. So I use a **query-focused population**
`popOf s σ = {s}` at `s`'s own shape, `∅` elsewhere — which makes all three invariants
hold *definitionally* (`popFocus_popOf`, `grounded_popOf` are trivial; `WFp` is every
`normalize` output). This discharges the "confinement" obligation the ROADMAP flagged
as the largest remaining piece, with **no** `pos ⊆ U` induction.

**Proof structure (`SetEngine/Correct.lean`, all axiom-clean).**
- `containsShape_unionFold` — probing a `union`-fold = `any` of the probes.
- `containsShape_grantMS` — one grant's probe = `grantMatch || grantFlow` (4-way on
  subject kind × wildness); `containsShape_expandDirect` assembles via `any_or_distrib`
  and a per-subject-kind match, `directLeaf`'s `memberOfGranted` = `any grantFlow` by
  `rfl`.
- `any_filter_guard` + `containsShape_expandTtu` — `ttuLeaf`'s guarded `T.any` =
  filtered `ttuParents.any`; per-parent probe matches by `pn == STAR` case split.
- `containsShape_expandE` (structural: boolean via `*_focus`, leaves via the above,
  `computed` = `HR`), `containsShape_expandAux` (fuel induction: `HR` = the fuel-IH,
  `HW` = `wfp_expandAux`), then `setEngine_correct`.
- Tactic notes for the leaf Bool-algebra: `beq_eq_decide` bridges `==`↔`decide`;
  `bool_eq_of_iff` + expanding `= true` lemmas + `SubjectRef.eq_iff` reduces to pure
  Props; `eq_comm` in *full* `simp_all` LOOPS with `decide`/`Bool` present (max-recursion)
  — keep it out; canonicalize orientation at Prop level or fall back to `tauto`/`aesop`.

**Now unblocked:** T3/T6a/T6b `rw`-route through T1∘T2b — they become real the moment
T2b lands. Remaining 4 sorries: T0a `semAux_fuel_stable_step`; T2a/T2b/T5 (need the
concrete graph state machine). Next-most-tractable: T0a (see ROADMAP option (a)).

## Session 2026-07-09 (T1 core corrected + T0a ingredient 1)

User asked to build T0a and T1. Both are multi-session (each needs its concrete
model/infrastructure first — see ROADMAP). This session delivered genuine, committed,
axiom-clean progress on both fronts; **no `sorry` discharged** (count held at 5), and
`verify.sh` stays green (build + 60 conformance + audit).

**Headline: the ROADMAP's T1 lemma was FALSE; corrected and proved.** The naive
intensional distribution `containsShape (op M N) = containsShape M ⟨op⟩ containsShape N`
under `WF` alone does NOT hold — `#eval`-confirmed counterexample with both operands
`WF`: `a={stars:={σ}}`, `b={stars:={shape}, neg:={uid}}`, `uid∈pop σ`, `σ≠shape` ⇒
both operands `false`, `union a b` `true`. This is exactly why last session's
`simp; tauto` never closed it. **Root cause:** the query shape must be the subject's
*own* shape and populations partition the id space by shape — the missing invariant
`PopFocus pop uid shape := ∀ σ, uid∈pop σ → σ=shape`. New file `SetEngine/Contains.lean`
(axiom-clean, `[propext, Classical.choice, Quot.sound]`):
- `containsShape_union_focus` (needs `PopFocus` + `WFp`),
- `containsShape_intersect_focus` / `containsShape_subtract_focus` (additionally need
  `Grounded pop uid shape m := uid∈m.pos → uid∈pop shape` — else a positive *ghost* is
  dropped by the extensional meet/difference; also `#eval`-confirmed false without it),
- support: `WFp`, `wfp_normalize`/`wfp_union/intersect/subtract`, `PopFocus`,
  `Grounded`, `mem_starpop_focus`, `mem_ext_focus`, `containsShape_normalize`,
  `wfp_atoms`, `bool_ext`. Technique: reduce to 7 membership atoms, then
  `by_cases`-on-all-7 `<;> simp_all` (tauto times out).
**T1 next:** build the concrete `SetEngineModel.check` expand model whose `pop`/`Id`
*satisfy `PopFocus`+`WFp`+`Grounded` per node*, then the `Direct`/`TTU` leaf-vs-`sem`
equalities. The distribution core is now done.

**T0a: decision + ingredient 1.** Chose option (a) (real proof, no spec change).
New file `Spec/FuelStable.lean` (axiom-clean): `evalE_mono` — untainted/positive
fragment monotonicity (`RecLe`-refinement preserves truth on exclusion-free exprs),
via `memberOfGranted_mono`/`directLeaf_mono`/`ttuLeaf_mono` + `Expr.noExcl`. This is
step 1 of the convergence argument (untainted fragment = monotone iteration). The
full worked-out structure (untainted monotone layer + tainted Kahn-DAG ranks + the
reachable-atom counting bound) is in the file header and ROADMAP. Confirmed: pure
pigeonhole is invalid (no visited-set; `Φ` non-monotone via `.excl`).

## Session 2026-07-09 (T0b fully closed — Kahn correctness)

**T0b is DONE** — `stratify_none_iff_cycle` and `stratify_topological` are proved and
axiom-clean (`[propext, Classical.choice, Quot.sound]`). All in `Spec/WellDef.lean`, built
from scratch on the concrete `kahn`/`readyNodes`/`depEdges` (no new model needed, as the
ROADMAP predicted). Count 7 → 5. `verify.sh` green (build + 60 conformance + audit).

Infrastructure proved (all axiom-clean, reusable):
- `mem_readyNodes_iff` — `n` ready ↔ remaining ∧ every out-edge leaves remaining.
- `kahn_succ` — one-step unfolding of `kahn` on a non-empty remaining set (isolates the
  definitional `if`/`let` churn once).
- `stuck_cycle` — **the pigeonhole core**: a non-empty stuck set (no ready nodes) has a
  cycle. Builds a total successor `g` (choice), iterates `g^[·]` into `R.toFinset`,
  `Finset.exists_ne_map_eq_of_card_lt_of_maps_to` gives a repeat, `reaches_orbit` turns
  the sub-walk into `Reaches edges k k`.
- `kahn_none_stuck` (⟹): `kahn = none` ⇒ a stuck set exists. The invariant
  `|remaining| ≤ fuel` (fuel starts at `|nodes|`, each round drops ≥1 via
  `List.length_filter_eq_length_iff`) rules out the fuel-exhaustion branch, so only a
  genuine stuck set can fail.
- `first_edge` / `cyc_out` — a cycle node has an out-edge to another cycle node.
- `kahn_cycle_none` (⟸): every cycle node persists in `remaining` (never ready), so the
  run never empties ⇒ `none`.
- `depEdges_mem` — both endpoints of a dependency edge are tainted keys (pins cycle
  nodes ⊆ initial `remaining`).
- `kahn_topo` — **the topological invariant**: threads (H1) `acc.reverse` is already
  topological + (H2) peeled nodes' out-edges have left `remaining`. Newly-peeled ready
  layer is appended last; readiness + H2 force its edges strictly earlier, so the
  invariant is preserved and the final `L` is `TopoLayered`. Needed hand-rolled
  `getD_app_lt`/`getD_app_ge`/`getD_ge_default`/`mem_getD_singleton` (this Mathlib has no
  `getD_append`).

**Next-most-tractable remaining:** T0a `semAux_fuel_stable_step` (subtle — see ROADMAP;
may want the visited-set spec refactor + conformance re-validation), then T1/T2 which need
their concrete models built first.

## Session 2026-07-09 (T4 fully closed)

**T4 is DONE** — `GraphIndex/Closure.lean` is `sorry`-free and axiom-clean. Built the
walk API the ROADMAP called the blocker, then the counting theorem, all from scratch on
the concrete `pathsOfLength`:
- `pathsOfLength_pos_iff` — walk-count positivity ↔ an `IsChain` vertex list (bridges to
  Mathlib's `List.IsChain` reachability API).
- `pathsOfLength_card_vanish` — **the pigeonhole vanishing lemma**: an acyclic graph has
  no length-`|V|` walk (`|V|+1` vertices ⇒ repeat ⇒ closed sub-walk via `IsChain.drop/take`
  + `getElem?_drop`/`getElem?_take_of_succ` ⇒ `pathCount x x > 0` ⇒ ⊥). Discharges the
  `hvanish` hypothesis of `phat_recurrence`.
- `pathsOfLength_succ_last` (last-edge decomposition), `pathsOfLength_mono`,
  `acyclic_of_addEdge`, `no_back_path` (the new edge can't close a cycle — needs L2).
- `rec_closed_form` / `rec_unique` — the affine recurrence `X a = c a + ∑ dcount·X`
  has a **unique** solution in a DAG (unroll `|V|` steps; the `X`-tail vanishes, leaving a
  matrix series in `c` only). No Nat subtraction anywhere.
- `pathCount_addEdge` — `phat g'` and the target formula both solve `g'`'s recurrence, so
  by `rec_unique` they coincide; the spurious back-path term vanishes by `no_back_path`.
- `pathCount_removeEdge` — the exact inverse: `(g.removeEdge u v).addEdge u v = g`, so it
  is `pathCount_addEdge` applied to `g.removeEdge u v`.

Count 9 → 7. `verify.sh` green (build + 60 conformance + audit). **Next-most-tractable
remaining: T0b Kahn** (self-contained, no new model needed); then T1/T2 need their
concrete models built first (see ROADMAP).

## Current phase & resume point

- **SORRY COUNT = 0 (2026-07-10).** Every stated theorem is proved at its
  documented scope; the remaining work is SCOPE WIDENING (ROADMAP W1–W4: wildcard
  bridges, rule routing, derived reconcile, full-scope restatement) plus Phase 6
  hardening (audit as hard gate, graph-model conformance extension).
- **W1a DONE (2026-07-10):** T2b widened to bare star grants `[user:*]`
  (`graph_correct_bareStar`, `GraphIndex/BareStarCorrect.lean`, axiom-clean).
- **W1b STARTED (2026-07-10):** object wildcards `[T:*]`. Attack-first proved
  (machine-checked) that bridges are **mandatory** here (unlike bridge-free W1a).
  The faithful bridge-materializing write model is delivered + structurally sound
  (`GraphIndex/ObjStarWrite.lean`: `writeWild`, `structInv_writeWild`,
  `WildReached`, `wildReached_structInv`, all axiom-clean). **Resume → the W1b
  read correspondence `graph_correct_objStar`** (bridge-completeness invariant +
  soundness/completeness with grant/bridge-hop interleaving = `matchingObjects`
  absorption; the read reduces to probe 1 ∨ probe 3, subjects star-free). See the
  W1b session block above and ROADMAP W1b for the sharply-isolated remaining work.
- **Phase 1 DONE** (Lean skeleton + all T0–T6 stated; `lake build` green with 9
  `sorry`s). **Phase 2 CORE DONE ahead of schedule**: conformance CLI (`zcli`) live;
  spec-vs-oracle answer conformance green (6/6 grid comparisons). No adjudication
  events — the executable `sem` matches the reference oracle.
- **User is reviewing `SEMANTICS.md` async** ("keep going, I'll review async"); A1 &
  A4 accepted. Continue proving; revisit if the review changes the spec.
- **Resume point → the W1b read correspondence** (`graph_correct_objStar`); the
  W1b bridge-materializing write model + structural invariant are done. Or Phase 6
  hardening; T0a is closed, nothing is blocked on the spec side.
- **Commands:** `cd formal/lean && lake build` (lib) / `lake build zcli` (CLI);
  `python -m pytest formal/conformance/ -q` (needs `zcli` built).

---

## Phase ledger

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 0 | Semantics extraction | **done** | SEMANTICS.md; 7 ambiguities logged |
| 0.5 | verify compiler undefined-reference behavior (A3) | todo | refine `WF` in Phase 3/4 |
| 1 | Lean skeleton + spec + theorem statements | **done** | builds green; all T0–T6 stated |
| 2 | Conformance bridge v1 | **done** | three-way `sem`/oracle/set-engine over 11 schemas, 33 tests green; graph backend TODO in P4 |
| 3 | Set-engine model + T1 | **done** | concrete expand model; T1 proved, axiom-clean |
| 4 | Graph-index model + T2/T4/T5 | **fragment scope done** | T4 ✅; T2a/T2b/T5 proved at star-free pure-direct scope over the operational closure; widening = ROADMAP W1–W4 |
| 5 | Equivalence T3 + security T6 | **fragment scope done** | T3/T6a/b real proved theorems at fragment scope; widen per W-stage |
| 6 | Hardening + CI + handoff | not started | |
| 7 | (optional) concurrency/crash in TLA+ | not started | separate go/no-go |

## Theorem ledger

Status: {planned, stated (compiles w/ sorry), proved-mod-deps, proved, blocked}.

| Theorem | Lean name | Status | Note |
|---------|-----------|--------|------|
| T0a spec well-defined (fuel-stable) | `sem_fuel_stable` | **proved** | axiom-clean; RESTATED over `StoreDeclared` (original FALSE — `Spec/Counterexample.lean`), then closed via confinement + untainted counting + Kahn rank induction |
| T0a stabilization core | `semAux_fuel_stable_step` | **proved** | `layer_stable`/`all_stable` assembly; arithmetic fits `fuelBound` |
| T0a confinement | `evalE_congr`, `step_congr`, `semAux_undeclared` | **proved** | Confine.lean; consulted atoms ⊆ `exprRefs × relevantNames` (ttu case = `StoreDeclared`) |
| T0a untainted phase | `chain_stabilizes`, `untainted_closed`, `semAux_mono_untainted`, `untainted_stable` | **proved** | Stabilize.lean; taint fixpoint + masked monotonicity + counting |
| T0a Kahn interface | `kahn_topo_strict`, `kahn_covers`, `kahn_layers_sub`, `kahn_length`, `stratify_covers`/`_layers_tainted`/`_length`/`_topo_strict` | **proved** | WellDef.lean; strict layering + coverage |
| T0a refutation record | `T0aCounter.oscillates`, `T0aCounter.fuel_stable_step_false` | **proved** | Counterexample.lean; the pre-`StoreDeclared` statement is FALSE (period-4 oscillation) |
| T0b stratify soundness | `stratify_none_iff_cycle`, `stratify_topological` | **proved** | Kahn correctness; axiom-clean. Pigeonhole `stuck_cycle` + fuel invariant `kahn_none_stuck` + cycle-persistence `kahn_cycle_none` + topo invariant `kahn_topo` |
| T0b pigeonhole core | `stuck_cycle` | **proved** | stuck set (no ready nodes) ⇒ cycle, via orbit + `Finset` pigeonhole |
| T0b Kahn helpers | `mem_readyNodes_iff`, `kahn_succ`, `kahn_none_stuck`, `kahn_cycle_none`, `kahn_topo`, `depEdges_mem` | **proved** | reusable Kahn/`readyNodes` API (WellDef.lean) |
| T1 set engine = sem | `setEngine_correct` | **proved** | axiom-clean; concrete expand model + fuel/AST induction; WF/Strat/AllValid unused |
| T1 leaf/structure/fuel | `containsShape_expandDirect/expandTtu/expandE/expandAux` | **proved** | grant/parent probe correspondence, structural + fuel inductions (Correct.lean) |
| T1 model + invariants | `expandAux`, `popOf`, `wfp_expandAux`, `popFocus_popOf`, `grounded_popOf` | **proved** | query-focused population makes PopFocus/WFp/Grounded definitional |
| T1 containsShape distribution | `containsShape_union/intersect/subtract_focus` | **proved** | Contains.lean; corrected (naive WF-only version is FALSE) — needs `PopFocus`(+`Grounded` for ∩/∖); axiom-clean |
| T1 distribution support | `WFp`, `wfp_normalize`, `mem_starpop_focus`, `mem_ext_focus`, `containsShape_normalize`, `wfp_atoms` | **proved** | Contains.lean building blocks |
| T0a untainted monotonicity | `evalE_mono` | **proved** | FuelStable.lean; ingredient 1 (excl-free ⇒ `RecLe` preserves truth); axiom-clean `[propext, Quot.sound]` |
| T0a monotonicity leaves | `memberOfGranted_mono`, `directLeaf_mono`, `ttuLeaf_mono` | **proved** | FuelStable.lean; positive `rec` use at leaves |
| T2a graph invariant + materialize | `graph_reached_inv` | **proved (fragment scope)** | RESTATED 2026-07-10 over `ReachedByDirect` (abstract version deleted as FALSE); full scope returns at ROADMAP W4 |
| T2b graph read = sem | `graph_correct_direct` | **proved (fragment scope)** | abstract `graph_correct` DELETED as FALSE; fragment instance proved end-to-end (DirectCorrect.lean); full scope returns at W4 |
| graph model concretization | `GraphState`/`GraphModel.check`/`Inv`/`Quiescent`/`GraphAccepts` | **concrete** | State.lean; opaque placeholders → real defs; the abstract `WriteStep`/`ReachedBy` closure deleted (operational closure lives in Write.lean/DirectCorrect.lean) |
| graph model base cases | `inv_empty`, `quiescent_empty`, `reach_empty` | **proved** | axiom-clean; `emptyState` ⊨ `Inv`/`Quiescent`, reaches nothing |
| T3 equivalence | `backend_equivalence` | **proved (fragment scope)** | RESTATED over `ReachedByAdmitted`; real `rw` through T1∘T2b-fragment + `stratifiable_pureDirect`; widens per W-stage |
| T4 counting-IVM (insert/delete) | `pathCount_addEdge/removeEdge` | **proved** | the crux; axiom-clean. Walk API + pigeonhole vanishing + recurrence-uniqueness |
| T4 pigeonhole vanishing | `pathsOfLength_card_vanish` | **proved** | `Acyclic → no length-\|V\| walk`; the ROADMAP-flagged blocker |
| T4 walk correspondence | `pathsOfLength_pos_iff` | **proved** | positivity ↔ `IsChain` vertex list |
| T4 recurrence uniqueness | `rec_unique`, `rec_closed_form` | **proved** | affine recurrence has unique solution in a DAG (matrix series) |
| T4 last-edge / monotonicity | `pathsOfLength_succ_last`, `pathsOfLength_mono`, `no_back_path` | **proved** | supporting lemmas for the counting expansion |
| T4 first-edge recurrence | `phat_recurrence` | **proved** | conditional on the DAG no-`|V|`-walk hyp; axiom-clean |
| T4 boundary sum-identity | `phat_boundary` | **proved** | the sum-manipulation heart, no acyclicity; axiom-clean |
| (lemma) sum-shift | `sum_Ico_shift_boundary` | **proved** | Nat induction |
| T5 cascade converges | `cascade_converges` | **proved (fragment scope)** | RESTATED over `ReachedByDirect` (old form held only by `WriteStep` assertion); becomes contentful at W3 (reconcile/outbox) |
| T6a exclusion-effective | `exclusion_effective` | **proved (fragment scope)** | RESTATED over `ReachedByAdmitted`; deny-propagation at this scope — exclusion content arrives W3/W4 |
| T6b no-ghost-grant | `no_ghost_grant` | **proved (fragment scope)** | RESTATED over `ReachedByAdmitted`; via T2b-fragment |
| T6c wildcard scoping | `wildcard_scoping` | **proved** | real theorem now: `T:*` grants are type-scoped, via `restrictionMatches_type` |
| (lemma) grant type-scoping | `restrictionMatches_type` | **proved** | axiom-clean `[propext, Quot.sound]` |
| (lemma) `ext_normalize` | `MemberSet.ext_normalize` | **proved** | MemberSet renorm correctness |
| (lemmas) membership/constructors | `mem_ext_union/intersect/subtract`, `ext_empty/singletonEntity/star`, `neg_subset_starpop` | **proved** | T1 leaf/composition building blocks (Algebra.lean) |
| (lemmas) algebra ext laws | `ext_union/ext_intersect/ext_subtract` | **proved** | `ext (a⊕b) = ext a ⊕ ext b` (Algebra.lean); T1 workhorses |
| (lemmas) star laws | `stars_union/intersect/subtract` | **proved** | `rfl` |
| (lemmas) star×boolean | `containsStar_union/intersect/subtract` | **proved** | the pinned intensional `'*'` table (§5.6) |
| T2a write model (untainted) | `writeDirect`, `structInv_writeDirect`, `inv_writeDirect` | **proved** | Write.lean; concrete guarded edge write preserves the whole `Inv` on the residue-free fragment; axiom-clean |
| T2a untainted write-closure | `ReachedByDirect`, `reachedByDirect_inv` | **proved** | Write.lean; the operational closure + its running invariant (`reachedBy_of_direct`/`writeDirect_writeStep` deleted with the abstract layer) |
| T2a write-effect projections | `quiescent_writeDirect`, `residueEmpty_writeDirect`, `writeDirect_outbox/watermark/schema/monoNodes` | **proved** | Write.lean |
| T2b base case | `graph_correct_empty` | **proved** | Correct.lean; `check (emptyState S) q = sem S [] q` — the `ReachedBy.empty` case, axiom-clean |
| T2b empty-store spec | `sem_empty_store`, `semAux_empty_store`, `evalE_empty_store` | **proved** | Correct.lean; `sem S [] q = false` by fuel induction |
| T2b empty read | `check_empty`, `probeNonDerived_empty`, `probeDerived_empty` | **proved** | Correct.lean; empty index answers `false` (no edges, no residue) |
| T2b read→reachability | `probeNonDerived_iff` | **proved** | State.lean; ≤4-probe read = disjunction of four `NReaches` conditions (endpoint-closed), via `reach_iff_nreaches` |
| T2b reachability→chain | `TupleChain`, `reachedByDirect_nreaches_chain`, `reachedByDirect_edge_sound`, `writeDirect_edges` | **proved** | Write.lean; untainted graph path = stored-tuple membership chain; edges trace to tuples |
| evaluator fuel monotonicity | `Schema.noExclAll`, `semAux_le_succ`, `semAux_mono` | **proved** | FuelStable.lean; exclusion-free schemas are fuel-monotone (T2b fuel plumbing + T0a ingredient) |
| **T2b fragment read = sem** | `graph_correct_direct` | **proved** | DirectCorrect.lean; end-to-end `check = sem` on the star-free pure-direct fragment, axiom-clean |
| T2b semantic core, soundness | `semAux_lift`, `semAux_of_chainN`, `semAux_one_of_tuple` | **proved** | DirectCorrect.lean; userset lifting (membership through a userset) + chain⇒`sem` at fuel = chain length |
| T2b semantic core, completeness | `nreaches_of_semAux` | **proved** | DirectCorrect.lean; `sem`⇒graph path (edge-completeness + flow-through `.tail`) |
| T2b fragment infrastructure | `ReachedByAdmitted`, `admitted_edge_complete`, `admitted_nodes_length`, `TupleChainN`, `chainN_of_trail`, `isDerived_pureDirect`, `objNode_eq_subjNode`, leaf intro/elim lemmas | **proved** | DirectCorrect.lean; admitted-writes closure (faithful to composed-system rollback), grant/leaf interface, node algebra |
| **T2b stage W1a — bare star grants** | `graph_correct_bareStar` | **proved** | BareStarCorrect.lean; `check = sem` widened to `[user:*]` grants (`BareStarStore`), ZERO bridges (wildcard-spec §3.2); axiom-clean |
| W1a soundness (covered chains) | `Covers`, `semAux_one_covers`, `semAux_of_chainN_bs`, `semAux_one_of_bareStar`, `semAux_lift_bs` | **proved** | BareStarCorrect.lean; chain base generalized from "is the subject" to "covers it" (leading bare-star hop) |
| W1a completeness (probe disjunction) | `reach_of_semAux_bs` | **proved** | BareStarCorrect.lean; `sem` ⟹ reach from `subjNode s` OR `wAny(s.shape)` (probe 1 ∨ probe 2) |
| W1a leaf elimination + edge chars | `directLeaf_elim_bs`, `mog_elim_nus`, `admitted_edge_source_char`, `admitted_edges_target_plain`, `nreaches_source_char` | **proved** | BareStarCorrect.lean; 3-way leaf elim (exact\|bare-star\|flow), userset-`wAny` never an edge source ⇒ probe 2 dead for usersets |

## `sorry` ledger

**Count = 0** (was 9). `semAux_fuel_stable_step` — the last one — was first
RESTATED (the original was FALSE over arbitrary stores; `StoreDeclared` added,
counterexample machine-checked in `Spec/Counterexample.lean`) and then PROVED
(2026-07-10; see the session entry). The `verify.sh` sorry inventory reports 0;
`sem_fuel_stable` is axiom-clean in the audit.

**⚠ HONESTY NOTE on the 3 → 1 drop (2026-07-10):** the two `GraphIndex/Correct.
lean` sorries (`graph_correct`, `graph_reached_inv`'s `Inv` conjunct) were
**DELETED as false-as-stated, not proved** (user-directed; the abstract
`WriteStep`/`ReachedBy` closure admitted junk states). Their obligations return
at full scope as ROADMAP stage W4. The theorem names survive, restated over the
operational closure at fragment scope, where they are genuinely proved
(`graph_reached_inv`/`cascade_converges` over `ReachedByDirect`;
`graph_correct_direct`/T3/T6a/T6b over `ReachedByAdmitted`).

**`GraphIndex/DirectCorrect.lean` is `sorry`-free** — the T2b semantic core
(userset lifting, chain ⇔ `sem`, both directions) and the end-to-end fragment
read-correctness theorem `graph_correct_direct`.

**`GraphIndex/State.lean` is `sorry`-free** — the 7 opaque graph placeholders are now
concrete definitions; `cascade_converges` (T5) is closed off the concrete `ReachedBy`.

**`GraphIndex/Write.lean` is `sorry`-free** — the concrete write model for the untainted
fragment (`writeDirect` + preservation + `ReachedByDirect`/`reachedByDirect_inv`); T2a's
`Inv` conjunct is proved honestly for the residue-free fragment. The abstract
`graph_reached_inv` sorry remains (its generality covers derived relations, which need
the reconcile/residue-materialization half — the isolated remaining T2a content). Now
also carries the reachability→`sem` soundness scaffold (`writeDirect_edges`,
`reachedByDirect_edge_sound`, `TupleChain`, `reachedByDirect_nreaches_chain`).

**`GraphIndex/Correct.lean`'s T2b base case is `sorry`-free** — `graph_correct_empty`
(`= sem S [] q`, both `false`) discharges the `ReachedBy.empty` case end-to-end. The
two full-generality `sorry`s (`graph_reached_inv`'s `Inv` conjunct, `graph_correct`)
remain; the T2b core left is `TupleChain ↔ sem`-membership (see the session entry).

**`SetEngine/Correct.lean` is now `sorry`-free** — `setEngine_correct` (T1) proved and
axiom-clean; the `opaque SetEngineModel.check` is replaced by a concrete expand model.

**`Spec/WellDef.lean`'s T0b theorems are now `sorry`-free** — `stratify_none_iff_cycle`
and `stratify_topological` proved and axiom-clean.

**`GraphIndex/Closure.lean` is now `sorry`-free** — `pathCount_addEdge` /
`pathCount_removeEdge` proved and axiom-clean (`[propext, Classical.choice, Quot.sound]`).

## Axiom audit snapshot (C4) — `lake build ZanzibarProofs.Audit`

Run 2026-07-09. `#print axioms` on representative results:
- `ext_normalize`, `ext_union`, `containsStar_subtract`, `mem_ext_union` →
  `[propext, Classical.choice, Quot.sound]` (the 3 standard axioms — clean).
- `restrictionMatches_type`, `wildcard_scoping`, `evalE_mono` → `[propext,
  Quot.sound]` (cleaner).
- `containsShape_union/intersect/subtract_focus` (T1 corrected core) → the 3 standard
  axioms.
- `sem_fuel_stable`, `backend_equivalence` → `[sorryAx]` (honestly flagged;
  route through tracked sorries). **No custom axioms** — Gemini's suggested
  `phat_def` axiom was rejected, keeping the surface clean for the final C4 gate.

## T4 progress (2026-07-10, this session)

`GraphIndex/Closure.lean`: `pathCount` **concretized** (weighted-walk sum over
`Fintype V`; the `opaque` is gone). Proved (axiom-clean): `pathsOfLength_zero/succ`,
`sum_Ico_shift_boundary` (Nat induction), `phat_boundary` (the first-edge recurrence
WITH the length-`|V|` boundary term, pure `Finset.sum` manipulation, no acyclicity),
and `phat_recurrence` (the clean recurrence, taking the DAG no-`|V|`-walk property as
an explicit hypothesis). Remaining T4 obligations (still `sorry`, count held at 9):
`pathCount_addEdge`/`removeEdge` — the algebraic expansion — plus discharging the
`hvanish` hypothesis via the pigeonhole vanishing lemma (needs a walk API; see
ROADMAP). Net: the mathematical heart of the counting theorem is proved; the
opaque is removed; count unchanged.

## Pending axioms (opaque placeholders — to be replaced, flagged by the C4 axiom audit)

The only remaining `opaque` is `ValidIdent` (Core/Ident — intended to stay abstract
per §2.1). **The entire graph model is now CONCRETE** — `GraphState`,
`GraphModel.check`, `Inv`, `ReachedBy`, `Quiescent`, `GraphAccepts` became real
definitions 2026-07-10 (State.lean); `pathCount` and `SetEngineModel.check` were
concretized earlier. The final axiom audit must show only `propext, Classical.choice,
Quot.sound` — no opaque model constants remain to eliminate (only the tracked
`sorry`s in `graph_reached_inv`/`graph_correct`/`semAux_fuel_stable_step`).

---

## Adjudications (spec/oracle/backend disagreements)

Per plan §8.2: any disagreement → STOP, record here (schema, ops, query, each
system's answer, analysis). Do NOT edit oracle/goldens/Python semantics or weaken a
theorem to match.

- **2026-07-09 — `fuelBound` too small (spec bug, not a semantic ambiguity). RESOLVED.**
  Found via a Gemini review of the Lean spec; **confirmed empirically**: a schema
  with `n` computed relations chained per object and linked across an `m`-object
  parent chain by TTU (a `deep_grid`, n=m=8) evaluates at depth ~`n·m`=64, but the
  additive `fuelBound = |keys| + 2|T| + 4` = 29 cut `semAux` off early → spec
  returned `false` where the oracle returned `true`. The oracle is ground truth; the
  bug was mine (under-provisioned fuel). **Fix:** `fuelBound = |keys| · (2|T| + 4)`
  (multiplicative — the recursion depth is bounded by the `(entity × relation)` state
  space, not their sum). Added `deep_grid` to the conformance corpus as a permanent
  regression; conformance 33→36 green. The shallow original corpus is why it slipped
  past — lesson logged. No user adjudication needed (spec bug, clear resolution).

---

## Decisions & variations log

Variations from the plan (`formal/history/formal-verification-plan.md`) or from the repo's
own specs, with rationale. (The user asked that variations be documented.)

- **2026-07-09 — Phase 0 delivered as SEMANTICS.md + PROOF_STATUS.md + README.md**
  under `formal/`, matching plan §8.4 layout. No deviation.
- **2026-07-09 — Executable spec will use per-stratum fixpoint iteration, NOT the
  oracle's Tarjan-lowlink provisional-False control flow** (SEMANTICS.md §11-A2).
  Rationale: cleaner T0a/termination proof; agreement with the oracle asserted by
  conformance C1 rather than by matching control flow. The oracle is being demoted
  from ground truth to cross-check, so this is sound.
- **2026-07-09 — Non-stratifiable schemas are OUT of the verified envelope**
  (SEMANTICS.md §4.4). All theorems carry `stratify S = some strata`. This matches
  the security audit's recommendation to reject cyclic-through-boolean upstream.
- **2026-07-09 — User approved: "lgtm, write everything." A1 & A4 accepted as
  proposed.** Proceeding: Lean graph model bakes the cascade into write ops (A1);
  graph modeled at the connectedstore deduped-set boundary (A4).

### Phase 1 (Lean) decisions

- **Toolchain:** Lean `v4.31.0` (stable) + Mathlib pinned to tag `v4.31.0`, built
  against the prebuilt cache (`lake exe cache get`). `elan` installed to
  `~/.elan`. Project at `formal/lean/`, lib `ZanzibarProofs`.
- **`sem` is fuel-based and primitive-recursive on the fuel `Nat`** (§ Semantics.lean):
  `semAux (fuel+1)` = one immediate-consequence `step` applied to `semAux fuel`.
  `step` is parameterized by the sub-node answer function `rec`, so no
  termination entanglement; the boolean/leaf logic is all in `step`. Mirrors the
  oracle's depth-bounded provisional-False recursion. `sem` runs at `fuelBound`.
- **Binary `union`/`inter`** in the AST instead of n-ary (associativity + WF arity≥2
  make it faithful; no empty-fold fail-open). Logged in Schema.lean.
- **Backend models are `opaque` placeholders in Phase 1** (`SetEngineModel.check`,
  `GraphState`, `GraphModel.check`, `Inv`, `ReachedBy`, `Quiescent`,
  `GraphAccepts`). This keeps T1/T2/T5 non-vacuous (they relate an opaque model to
  `sem`, provable only once the model is concrete). Phases 3–4 replace the opaque
  declarations with real definitions. T3/T6a/T6b are ALREADY proved by `rw`
  through T1/T2b (so they become real the moment T1/T2b are discharged).
- **`stratify`/taint is an independent reimplementation** of `compute_taint` +
  `_stratify` (Kahn layering over derived-dependency edges). Fidelity to the Python
  is a Phase-2 conformance check, not assumed.
- **Reality check on "T0 is mechanical" (plan §9 P1):** it is NOT. `sem_fuel_stable`
  (T0a) rests on the stratified fixpoint being reached by `fuelBound` — a genuine
  theorem because exclusion is non-monotone in fuel. `stratify_*` (T0b) is Kahn
  correctness. Both are STATED (compiling) in Phase 1 with `sorry`; proofs are
  tracked and deferred rather than force-fit. `MemberSet.ext_normalize` IS proved.
- **T6c (`wildcard_scoping`)** is a trivial `rfl` placeholder to be refined to the
  precise scoping statement in Phase 5.

---

## Key facts a fresh session must not re-derive

- The spec `sem` = **stratified Datalog¬ perfect model, queried pointwise** — both
  backends compute it; equivalence is a corollary (`theory.md:192-198`).
- The oracle (`tests/oracle.py`) is the operational reference we are *replacing* with
  the Lean executable spec; it becomes a cross-check, not a proof target.
- **I9 (fixpoint audit) is test-suite-only**, not per-commit — so cascade-runs-in-txn
  is an assumed precondition (SEMANTICS.md §7.8, §11-A1). Most load-bearing fact.
- The counting theorem (T4) is sound **only because cycles are rejected** — the group
  `(ℤ,+)` inverse argument fails with cycles (`theory.md:57-61`). Rejecting cyclic
  schemas is a *necessity*, not a policy.
- Toolchain (elan/Lean/lake) is **not yet installed**; installing requires user
  permission (repo rule). Lean lives outside the conda env; conformance harness runs
  under the `graph-reachability-zanzibar-index` conda env.
- Python is READ-ONLY for this project except test-only conformance code under
  `formal/conformance/` (plan §8.3).
