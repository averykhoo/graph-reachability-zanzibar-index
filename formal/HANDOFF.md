# HANDOFF.md — START HERE (the formal-verification entry point)

**A fresh session reads THIS FILE FIRST, top to bottom (~250 lines), then goes straight
to work on "The next task" below.** Pull in other docs only on demand:

| doc | what it's for | when to read |
|---|---|---|
| `ARCHITECTURE.md` | the durable topical map (trust root, models, theorem table + scopes, pinning, residual surface) | for "how it all fits together" |
| `FINAL_REVIEW.md` | the exact, clause-checked claim (plan §7 + cross-check) | for the precise wording of what is/isn't proved |
| `SEMANTICS.md` | the spec / trust root (`sem`, models, theorem statements) | when touching spec-level defs |
| `CORRESPONDENCE.md` | the Lean-def ↔ Python-file:line map | when auditing the model↔code tie |
| `history/PROOF_STATUS.md` | append-only session ledger (newest first) | the TOP entry only, for fine detail on a resume point |
| `history/ROADMAP.md` | per-stage designs + historical plans | the section for a stage's provenance |
| `history/REVIEW.md` | historical one-shot session digest (2026-07-09→10) | never (history) |
| `formal/history/formal-verification-plan.md` | original strategy/phases/honesty clauses | rarely; §7 for claim wording |

**End goal:** a machine-checked proof that the set engine and graph index both compute
the stratified-Datalog¬ perfect model `sem` — hence are equivalent — with the Python
implementations pinned to the Lean models by the conformance harness. The honest claim
never rounds up to "the code is formally verified" (plan §7).

**One caveat every session must carry** (`FINAL_REVIEW.md` §3.0, `ARCHITECTURE.md` §6.0):
the final graph theorems (`graph_correct`, `graph_reached_inv`,
`Exec.graphRun_check_eq_sem`, and everything routed through them) are **VACUOUS — not
merely narrow — on any store written through the `Direct` arm of a derived def**, i.e. on
`can_view: [user] but not blocked`, the canonical Zanzibar boolean shape.
`FullScope.lean:564` machine-checks `¬ StoreValidRules Sd Td` at exactly such a store, and
`GraphAdmission.storeValid` IS `StoreValidRules`. What is proved there is the C-chain
`graph_correct_w3d2_d`; the E-chain widening (`enumJob2 → enumJob2D`, a `_d` projection of
`reachedByW3d2E_toC`, `storeValid → StoreValidRulesD`) is recorded at
`FullScope.lean:527-528` as **NOT done** and is the highest-value open item.

---

## House rules (non-negotiable, user-adjudicated)

1. **Honesty norm.** Never fake a proof, never postulate the thing being proven
   (no `check := sem` models, no invariant-as-postcondition). A documented `sorry`
   plus genuine infrastructure beats a fragile/unfaithful close. Never edit a
   golden/oracle/snapshot to make something pass.
2. **Attack first.** Before proving any NEW theorem statement, try to REFUTE it —
   concrete scenarios via `#eval` against the real `check`/`sem` (delete the scratch
   after recording the finding). Six false statements were killed this way in the
   original W1→W4 arc (additive fuelBound, abstract WriteStep closure,
   T0a-sans-StoreDeclared, naive-W2 TTU fragment, W3a single-edge collapse sans
   NoRuleOutputs, W3d-2 "round-1 keys are stratum-1"), and **at least seven more since**
   during the 2026-07-18…20 remove and Direct-arm legs (`graph_correct_w3a_d`, the
   chain-level `removeLoggedRules` fold, filter-all `removeEdgePair`, the derived-arm
   `count ∈ {0,1}` invariant, the naive `reachedByW3d2_shadow_d`, the paired
   `reachedByW3d2C_settled_d`/`graph_correct_w3d2_d`, and the first proposed
   `affectedKeys` fix) — see `history/PROOF_STATUS.md` for the full ledger. A session
   that kills a false statement is a GOOD session; record the finding.
3. **Green gate.** Every increment must keep `bash formal/verify.sh` green: lake build
   + **0 sorries** + zcli + the axiom audit (one `#print axioms` report per audited
   theorem, only `[propext, Classical.choice, Quot.sound]`) + the audit IDENTITY pin
   (`formal/audited_theorems.txt`) + the headline STATEMENT pin
   (`formal/headline_statements.txt`) + the headline DEFINITION pin
   (`formal/headline_definitions.txt` — what those statements' words MEAN, transitively)
   + the `CORRESPONDENCE.md` anchor pin + the Python conformance suite, 0 skips,
   0 xfails, + **`tests/`**.
   **★ No counts here, deliberately.** This bullet carried four of them (457 audits, 139
   definition rows, 465 conformance, 744 collected) and by 2026-08-05 **every one was
   stale** — the same `ZT-P3-5` rot that has now been hand-fixed three times elsewhere.
   Live figures live in ONE machine-checked place, `FINAL_REVIEW.md`'s generated counts
   block (`verify.sh` step 4e; regenerate with
   `python -m formal.conformance.doc_counts --generate`). Read them there. The gate
   enforces `-ge` FLOORS rather than exact numbers, so a quoted count in prose is not
   just stale, it is *unenforced* — which is why it rots.
   **Adding an audited theorem now also means regenerating the identity pin**
   (`bash formal/regen_audit_pin.sh`); changing a headline theorem's STATEMENT, or the
   DEFINITION of anything it depends on, means regenerating both goldens deliberately
   and saying why (`"$PY" formal/conformance/statement_pin.py --generate` rewrites
   `headline_statements.txt` and `headline_definitions.txt` together).
   **Note what the definition pin is for.** Moving `twoStrata` from `W4Fragment` into
   `GraphAdmission` BUILDS, keeps all 26 pinned statements byte-identical, changes no
   declaration name -- and converts a declared honest scope-carry into a claimed
   guarantee about Python's admission that is false (Python reaches 12 strata). That
   was invisible to every other check in the gate; it is the attack 4c exists for.
   (incl. the Phase-6 graph mode, the state-level gate over zcli mode `"graph-state"`,
   the exhaustive small-scope enumeration, the remove-path and generated-schema answer
   gates, the TTU userset-subject and self-referential-tuple spec corpora, and the
   zcli mode-rejection tests; the gate
   fails closed on any skip or zero passes). Add new key theorems to
   `lean/ZanzibarProofs/Audit.lean`.
4. **Rhythm.** Commit each green increment with a `formal: <stage> — <what>` message;
   push at session end. Before ending: update this file's "The next task" + add a
   `history/PROOF_STATUS.md` session entry (top) + tick the `history/ROADMAP.md` stage
   marker.
5. **Faithfulness.** Model hypotheses must be faithful to the Python (cite file:line
   or the spec §). New fragment conditions need a comment saying what Python mechanism
   they mirror. Where a spec and the code disagree on a name, the code wins.
6. **Subagents** don't parallelize proof-closing (compiler-in-loop, deep coupling);
   use them only for read-only exploration/design.
7. **Sabotage every check you add** — the standard procedure is
   [`docs/sabotage-procedure.md`](../docs/sabotage-procedure.md). Rule 2 (attack first)
   and this rule are the same instinct pointed at different objects: **attack-first
   guards against proving something FALSE; sabotage guards against trusting a check
   that verifies NOTHING.** On the formal side this binds `verify.sh` floors, pins,
   `Audit.lean` entries, and conformance corpora — and it binds your *instrument* as
   well as your subject: an `#eval` probe needs a **positive control** (a defect it
   must catch) and a **non-vacuity count** (proof the comparison ran on something).
   A probe that compared nothing reports success. This is not hypothetical here — the
   2026-07-28 Leg-0 sweep's first coverage instrument was wrong (73 false failures from
   omitting a star exemption) and was caught only by its control.

## Build & verify

```bash
export PATH="$HOME/.elan/bin:$PATH"                    # Lean v4.31.0, Mathlib pinned
cd formal/lean && lake build                            # library (incremental ~1 min)
lake build ZanzibarProofs.GraphIndex.ReconcileCorrect   # one module (~20 s)
bash formal/verify.sh                                   # THE gate (from repo root)
```

⚠ The one-shot `verify.sh` **blows the agent harness's ~10-min command cap** —
agents run it PHASED: `verify.sh lean` → `conf-tile:1/5 … 5/5` → `tests-tile:1/4 …
4/4` (each cap-fitting, same anti-vacuous guards; the green phases ≡ a green
one-shot). `conf-heavy`/`conf-rest` still work but `conf-rest` measured 579 s
against the 600 s cap. Full recipe + floors table + fuzz gate:
[`docs/gate-runbook.md`](../docs/gate-runbook.md).

Python side runs under the repo conda env — on this machine
`C:/Users/user/anaconda3/envs/graph-reachability-zanzibar-index/python.exe`
(the `C:/Users/avery/...` path this file used to name does not exist here; `verify.sh`
resolves the interpreter itself, and `ZANZIBAR_PY` overrides).

**Lean/Mathlib gotchas (hard-won):** unfold plain defs with `unfold f` / `simp only [f]`,
not `rw [f]`. `omega` treats `∑`-atoms as opaque — good for combining sum `have`s.
`Finset.Ico` ← `Mathlib.Order.Interval.Finset.Nat`; big-operator ring lemmas ←
`Mathlib.Algebra.BigOperators.Ring.Finset`; `ring` ← `Mathlib.Tactic.Ring`.
`NReaches` is head-oriented: back-append is `NReaches.tail`; back-REPLACE needs
last-edge surgery (`nreaches_last`, cf. `nreaches_relation_rewrite`).

## State of the world (2026-07-12m — the arc is COMPLETE; all sorry-free, axiom-clean, verify.sh green)

> **★ #4 IS FULLY CLOSED — proved AND driven AND documented (2026-07-19f/g).** The `remove`
> constructor lives on `ReachedByW3d2`/`C`/`E` (2026-07-19f, `7a594bb`; guard: `t ∈ T` + `hdrain` +
> the pre-remove store's `StoreValidRules`/`BareStarStore`/`TtuStarFree`/`htermT`, faithful to
> `TupleSource.remove`), so the audited `graph_correct`/`graph_reached_inv`/`Exec.graphRun_check_eq_sem`
> cover retraction — SCOPE: a **validly-stored** tuple from a **drained** prior state. Session
> 2026-07-19g closed the follow-ups: **Exec-driver remove hardening** (`5a35ec3` — `GraphOp` streams,
> `graphRunOps` folding the chain's own legs, `removeGateB` deciding the full guard at runtime
> fail-closed, honesty trio `graphRunOps_reached`/`_store`/`_check_eq_sem`, zcli `"ops"` field w/
> rc 5 spec-mode rejection, new answer-level differential gate `test_conformance_remove_graph.py`)
> and the **claim-doc sweeps** (`67f8c35`/`f1c9d14` — FINAL_REVIEW/HANDOFF/ARCHITECTURE/SEMANTICS/
> README/CORRESPONDENCE §7 now state the scoped-removes claim + live counts). ★ GUARD DESIGN
> DECISION APPROVED BY AVERY (2026-07-19): the validly-stored + drained-prior scope is accepted as
> the honest, faithful framing — no longer an open flag.
>
> **#1 Direct-arm widening ADVANCED (2026-07-19g/h): legs 4 + 5a + 5b + 5c + 5d-W3c landed** (`128d7e6`/
> `53c5d34`/`4a01c2d`/`62ab8f4` + leg-5d uncommitted; all additive, audited statements byte-identical,
> audit 425 → **448**). Leg 5d (2026-07-19h): the W3c-branch `_d` clones `reachedByW3c_master_d` /
> `w3c_row_char_d` landed (originals → byte-identical wrappers); the naive W3d2 `reachedByW3d2_shadow_d`
> was attack-KILLED (full-store σ0 ⊄ drained σ) and re-scoped to a filtered-σ0 substrate (see THE NEXT
> TASK below).
> Leg 4 (Fable): the base-equation wall DISCHARGED — `graphRec_base_eq_d`/`_bs_d` (no `ComputedOnly`;
> premise = the `hterm` bundle consumers already carry) via design lemmas A (`rewriteClosure_derived_
> eq_seed`, simpler than designed), B (`probeNonDerived_untaintedFilter`), C (`sem_untaintedFilter`,
> no `Stratifiable` premise); audited `graphRec_base_eq`/`_bs` are now thin wrappers over `_unt` cores.
> Leg 5a (Opus): the `_cd` read spine (`checkFn_eq_semStep_cd`, `checkFn_eq_sem(_of_base)_d`) + **KILL:
> `graph_correct_w3a_d` is FALSE** (a stored bare Direct-arm seed on an exclusion-rooted derived key
> is never retracted at the raw W3a reconcile — `reachedByRules_derived_no_inedge` breaks under
> `StoreValidRulesD`), so the Direct-arm WRITE half must thread the W3d diffing pass
> (`reconcileKeyD_retracts_excluded`) — correspondence lives at the W3d2 drained state. Leg 5b (Opus):
> star-relaxed/routed spine (`checkFn_eq_sem_bs_d`, `checkFnR_eq_semStep_cd`) + **KILL: the naive
> coveredFn widening is FALSE** (a subject's own concrete Direct grant fires a disjunct absent from
> its star read); corrected split landed gated on **`NoConcDirect`** (`evalE_star_of_noConc`,
> `checkFn_eq_coveredFn_of_no_extra_cd`, `checkFnR_eq_star_of_not_enum_cd`).
>
> Leg 5c (`62ab8f4`, the enum half): the linchpin widened — **`coveredFn_declared_d`** (via
> `graphRec_star_declared_d`/`directArm_star_declared`), the Direct-arm-aware enumeration
> (`storedDirectSubjects`, `enum2BaseD`/`enumJob2D`, `w3dJobCoverage_enumJob2D`,
> `w3d2_leg_context_d`) + the routed settled read bridge (`checkFnR_eq_sem_settled_d`,
> `checkFnR_star_declared_d`). Attack NO-KILL recorded: a stored bare Direct-arm subject lives in
> the FIXED store, so the 12h future-residue kill shape does not apply — enumerable at every state.
>
> **#1 Direct-arm leg 5d (2026-07-19h) — the `_d` CHAIN: W3c branch LANDED; W3d2 shadow KILLED (naive)
> + re-scoped.** Audit 446 → **448**, `verify.sh lean` PASSED, additive, tree GREEN (uncommitted).
> **LANDED (W3c branch, tractable + independent of the shadow):** `reachedByW3c_master_d`
> (`ReconcileStars.lean`; only `hCO` use = the pass-start `checkFn` agreement → leg-2's
> `checkFn_agree_of_graphRec_cd`, which was relocated UP `ReconcileDiff`→`ReconcileStars`) and
> `w3c_row_char_d` (`ReconcileStarsComplete.lean`; master_d + `checkFn_eq_sem_bs_d`). Both audited
> originals refactored to BYTE-IDENTICAL wrappers (verified vs HEAD). **★ ATTACK-FIRST KILL — the naive
> `reachedByW3d2_shadow_d` (full-store σ0) is FALSE:** `#eval` — a stored Direct-arm subject that is ALSO
> excluded (`approver := excl (direct[user]) banned`, `{(alice,approver,doc),(alice,banned,doc)}`) puts the
> base seed `subjNode(alice)→objNode(doc,approver)` in the full-`T` admitted σ0 (`rewriteClosure=[t]`), but
> the drained W3d2 σ RETRACTS it (`reconcileKeyD_retracts_excluded`; drained `σ.edges=[(alice→banned)]`), so
> `UntaintedShadow.sub` (σ0⊆σ) FAILS. So the leg-5c bridges `checkFnR_eq_sem_settled_d`/`w3d2_leg_context_d`
> (which take `h0 : ReachedByRulesAdmitted σ0 S T` full-store ∧ `hsh : UntaintedShadow`) are UNSATISFIABLE
> jointly at those states — un-dischargeable by a real `_d` chain as written. **RE-SCOPE:** the drained
> σ.edges = the untainted core, so the shadow needs **σ0 = the untainted-FILTER (`T↾U`) rebuild** (a NEW
> construction) + additive `T↾U`-store variants of the leg-4/5c consumers composing with `sem_untaintedFilter`
> (leg 4 lemma C). Full step plan: `history/optional-widening-2026-07.md` leg-5d section + RESUME.
>
> **★ 2026-07-20b — the FILTERED-σ0 chain LANDED (substrate + shadow_d + bridge, 4 pushed increments), then
> the settledness/correctness clones ATTACK-KILLED on a REAL model gap.** LANDED+PUSHED: `49cec70` the 5
> substrate helpers (incl. `reachedByRulesAdmitted_untStore_edge_untainted`) · `6fc42ce`
> **`reachedByW3d2_shadow_d`** (the filtered σ0 = `ReachedByRulesAdmitted σ0 S (T↾U)` + `UntaintedShadow`;
> write case splits untainted-fold vs derived-key-drop with a DerNode-classified seed edge; added `WF S` +
> `BareStarStore T` DerNode carries; ★ NodupKeys attack-finding) · `011ac74` the **T↾U-σ0 bridge**
> (`checkFnR_eq_sem_settled_d_filt` + `sem_untaintedFilter_co` + `w3d2_leg_context_d_filt`) · `0ec31d2` a
> Direct-arm Python conformance corpus (`direct_arm_exclusion`, 3-backend, held out of GRAPH_FRAGMENT). All
> `verify.sh lean` 448/448, additive, audited originals untouched. **★★ ATTACK-FIRST KILL (house rule 2):
> `reachedByW3d2C_settled_d` AND `graph_correct_w3d2_d` are FALSE as specified** — Lean's `affectedKeys`
> (`GraphIndex/Cascade.lean:433`) is READER-ONLY and LACKS Python's LeafFamily own-key branch
> (`processor.py:991-1011`), so a Direct-arm seed write never dirties its own derived key ⇒ a drained
> `ReachedByW3d2C` state with `check=true` but `sem=false` (structurally validated; the `Cascade.lean:428`
> doc comment claims the branch, the code omits it — faithful only within the ComputedOnly scope). The
> landed substrate/shadow_d/bridge are SOUND + reusable (conditional on settledness the bad state fails —
> nothing to revert).
>
> **★ 2026-07-20c — THE MODEL FIX LANDED (step 1 DONE); the naive fix was ATTACK-KILLED first.** `affectedKeys`
> now carries the LeafFamily own-key branch via a **`Delta.leaf : Bool`** provenance tag (the faithful
> discriminator — the collapsed model lands both a raw Direct-arm seed write and a reconcile emission at the
> SAME `objNode ⟨o⟩ R`, so the branch can't key on `isDerived` alone). ★ House-rule-2: the handoff's PROPOSED
> naive branch (`isDerived ⇒ dirty own key`, any delta) was REFUTED — it re-dirties reconcile emissions'
> own keys (Python's `_fan_out` never does), breaking quiescence (`runCascade_no_abort` FAILS empirically).
> `writeLoggedOne`/`removeLoggedOne` push `leaf=true`; reconcile emissions `false`; the own-key branch is
> provably `[]` for `leaf=false` + untainted `leaf=true`, so the ComputedOnly scope is behaviorally identical
> (audited statements + meanings UNCHANGED). Cascade/fence stack repaired (`d.leaf=false` threaded through
> `reconcileJobsL(R)_outbox_sound` → the no-abort/fence proofs). `verify.sh lean` 448/448 + `conf-heavy` green;
> `CORRESPONDENCE.md` §5/§7 updated (divergence RESOLVED). See `history/PROOF_STATUS.md` 2026-07-20c.
>
> **★ 2026-07-20d — THE `_d` SETTLEDNESS CHAIN CLOSED (task steps 2-3 DONE): `reachedByW3d2C_settled_d`
> + `graph_correct_w3d2_d` LANDED, audit 448 → 450.** Attack-first CONFIRMED the model fix before proving
> (`#eval` drove the 20b kill schema through `graphRun`: the drained state retracts the excluded seed,
> `check = false = sem`; scratch deleted). Three green commits: `c41829b` groundwork (`sem_nil_false`;
> `writeLeg/removeLeg_own_key_dirty` — the model-fix branch made chain-usable and LOAD-BEARING; node-ineq
> in-edge preservation; CD store congruence `checkFnR_cons/erase_irrel_cd`; the unaudited `_filt` bridge's
> schema-wide `hCO` REPAIRED to per-key operand `hCOop` — it was unsatisfiable on genuine Direct-arm
> schemas), `36926dd` the write/remove-leg transports (`checkFn_eq_sem_w3d_filt`,
> `writeLeg/removeLeg_sem_stable2_d` + per-key transports), `d5f6071` the chain (`edge_char_d` family →
> `settledComplete_jobsLR_targeted_d` → `settledComplete_cascade2_targeted_d` → the induction → T2b).
> **FRAGMENT (honest):** schema-wide `ComputedOrDirect ∧ DirectArmsBare` derived defs; derived OPERAND
> defs `ComputedOnly`; `StoreValidRulesD`; + **`hNoUD`** (`exprDirects e = []` on derived defs — Direct
> arms only under `inter`/`excl`, the canonical `but not`; scopes the REMOVE leg, whose plain-valid pre
> store otherwise admits union-reachable Direct-arm seeds whose covered-state erase needs an unbuilt
> star→concrete `sem` monotonicity lemma — recorded follow-up). See `history/PROOF_STATUS.md` 2026-07-20d.
>
> **★ 2026-07-20e — task step 4 CLOSED on the HONEST CONSERVATIVE fork: `W4WitnessDirect` LANDED
> (audit 450 → 455) + `direct_arm_exclusion` moved INTO `SCHEMAS`/`GRAPH_FRAGMENT` (conf 315 → 326
> as counted that session; the collected total measured 2026-07-26 is **330**,
> the graph-STATE pin ran CLEAN); `W4Fragment`/the final theorems deliberately NOT widened.** The
> witness (`FullScope.lean`) inhabits the C-chain `graph_correct_w3d2_d` bundle at the corpus pair:
> `accepts` (admission with `StoreValidRulesD`), `fragment` (all `_d` carries incl. `hNoUD`),
> `within_scope`, `correct_applies` (the bundle JOINTLY discharges the audited T2b), and
> `outside_old_admission` (plain `StoreValidRules` PROVABLY rejects the store — the widening is
> contentful). ★ Attack findings (scratch `#eval`s, deleted): (A) the chain REJECTS removes on
> Direct-arm stores fail-closed (`removeGateB`'s plain-`StoreValidRules` pre-store guard; the 20d
> `hNoUD` scoping made operational) — so `test_conformance_remove_graph.py` EXCLUDES the corpus with
> the reason documented in situ (`_REMOVE_EXCLUDED`), while the PYTHON-side remove churn
> (`test_conformance_remove.py`) now carries it clean; (B) add-only, the operational chain serves the
> full corpus truth table (`check = sem`, drained). WHY the E-chain was not widened (the fork's
> assessed cost, multi-session): the operational enumeration must CHANGE (`enumJob2` → `enumJob2D`
> inside `enumJobs2At` — a `Delta.leaf`-scale ripple: Assemble/StrataEdge/StrataInv/Exec + graph-state
> conformance, behavioral-identity on the CO scope); `w3cJobValid_enumJob2D` has an OPEN star-freeness
> hole (a WILDCARD restriction on a derived Direct arm puts `user:*` in `storedDirectSubjects` —
> needs a star-filter or a new fragment clause); the ~100-line `reachedByW3d2E_toC` cascade discharge
> needs a full `_d` clone; and `GraphAdmission.storeValid` must widen to `StoreValidRulesD` (at a
> Direct-arm store the CURRENT admission bundle is unsatisfiable). See PROOF_STATUS 2026-07-20e.
>
> **★ 2026-07-28 — the E-chain arc is now SCOPED and its Leg 0 (attack sweep) is DONE: 5 probes,
> 2 KILLS, no Lean declaration changed.** The durable plan is
> [`history/echain-widening-plan-2026-07-28.md`](history/echain-widening-plan-2026-07-28.md)
> — **read that, not the 20e fork list below, which it supersedes in five places.** Results:
> **(1) T2a `graph_reached_inv` does NOT widen with T2b.** `Inv.negEdgeFree` is machine-checked
> FALSE on the `_d` fragment (`p3_negEdgeFree_false`, proved alongside
> `p3_svD : StoreValidRulesD` and `p3_not_sv : ¬ StoreValidRules` — the widening is exactly what
> admits the bad state). At the post-write pre-cascade state the raw derived-key write lands its
> edge on the SAME node the `neg` residue row is keyed at. **This is a MODELLING limit of the P6
> leaf-family collapse, NOT a Python bug** — verified on the real backends: `RuleSet.apply` routes
> the write onto the leaf family (`#approver.0`, never `#approver`), I6 disjointness intact, 0
> mismatches. T2b is unaffected (the drained state repairs it). A DESIGN DECISION is owed before
> any T2a work: (a) restate T2a at drained states only, (b) weaken `negEdgeFree`/`uposEdgeFree`,
> or (c) model the leaf-family split.
> **(2) `enum2BaseD` must dedupe** — `enumJob2D` is not a conservative widening; edge multiplicity
> goes `n ↦ 2n+1` per leg. En route this surfaced a **pre-existing, previously undocumented
> model↔Python divergence**: the BASELINE enumeration already doubles derived-edge multiplicity per
> cascade leg (`1 → 2 → 4 → 8`), and the state gate is structurally blind to it because projection
> P3 compares edges as a SET. ~~Filed at `CORRESPONDENCE.md` §7.2, UNADJUDICATED~~ —
> **ADJUDICATED + CLOSED 2026-07-29** (`CORRESPONDENCE.md` §7.2): real, model-side, confined
> EXACTLY to the derived arm (Python's presence diff caps `direct_edge_count` at 1 there),
> removal-inert by assembly, and the growth is worse than filed — measured Lean 4 … **1013**.
> P3 is narrowed: untainted-arm multiplicity is now compared EXACTLY (153 edges, net-new
> assurance, `nary_union`'s non-unit 3 == 3 included) and the derived arm is golden-pinned
> per corpus. **Consequence for this arc: §D.6 is now MECHANICAL — Leg 2 will break
> `test_derived_arm_multiplicity_ledger` by construction, and that is the intended signal.**
> ⚠ Do **not** discharge the dedup obligation by making `admitEdge` reject an already-present
> edge: untainted multiplicity is load-bearing (`untOccCount`, erase-one removal) and is now
> checked, so that global edit goes red on `nary_union` (3 → 1). Mirror Python's presence diff
> inside `reconcileKeyDR`'s fold guard instead.
> **(3) The step-2 star-freeness question is DECIDED**: a new `W4Fragment` clause
> `directArmsConcrete` **plus** the faithfulness star-filter — a star-filter alone leaves the
> `edgeHolders` half of the hole open. It excludes a shape Python admits, so it goes in as a
> declared scope carry with the paragraph written in the same commit.
> **(4) Dropped from the risk list:** the `hND` shadow premise (a `List.mem_filter` tautology; the
> shadow layer is already `_d`-widened). **(5) Free win:** `w4_within_scope` clause 3 is true
> WITHOUT the `ComputedOrDirect` premise — prove `directsOnly e = true → exprDirects e ≠ []`.
> **★ LEG 1 LANDED the same session (audit 457 → 460, definition pin UNMOVED at 139/139).**
> `DirectArmsConcrete` (`ReconcileCorrect.lean:1001`, carrying the honest scope-carry paragraph
> in its docstring), `storeValidRulesD_derived_subject_ne_star` (`:1052`), the faithfulness
> star-filter on `storedDirectSubjects` (`CascadeStrataEnum.lean:626`, mirroring
> `index_v4/processor.py:268`/`:670`) + the `noConcDirect_of_not_mem` repair,
> `storedDirectSubjects_name_ne_star`, **`reachedByW3d2_Rnode_source_name_ne_star_d`**
> (`CascadeStrataSettle.lean:3504`), and probe D.5's free win `exprDirects_ne_nil_of_directsOnly`
> (`FullScope.lean:169`) in its STRONGER hypothesis-free form. All four `enum2BaseD` consumers
> compiled unchanged. **`DirectArmsConcrete` is machine-confirmed load-bearing:** 262-run sweep
> over every chain state gave 824 derived-R-node in-edges, 0 STAR-sourced; with the clause
> dropped, 122 stores produce one.
>
> **★ LEG 2 LANDED 2026-08-04 — the enumeration model change.** `enumJobs2At` now takes the
> `Store` and enumerates **`enumJob2D`**, rippling to `enumJobs2R1`/`R2`,
> `ReachedByW3d2E.cascade`, `Exec.cascadeLeg` and six sites in `RemoveConfluence.lean`.
> Audits 460 → **465**; **headline STATEMENTS 26/26 byte-identical while the DEFINITION pin
> moved 139 → 142** (5 changed, `enumJob2` dropped, 4 added) — the exact
> statement-stable/meaning-changed asymmetry check 4c exists for.
> **`enumJob2D_eq_enumJob2`** is the linchpin: on the `ComputedOnly` scope the two jobs are
> EQUAL, so `reachedByW3d2E_toC` (which is `hCO`-scoped) rewrites back to the landed coverage
> discharges unchanged and the leg lands with none of the `_d` chain. **`w3cJobValid_enumJob2D`
> needs no fragment carry at all** — same hypotheses as its sibling, because leg 1's
> star-filter closed the `storedDirectSubjects` half of the Board-B1 hole inside the
> definition.
> **Two plan corrections, both measured** (`history/echain-widening-plan-2026-07-28.md` §C.2):
> * **The prescribed `.dedup` on `enum2BaseD` does not fix D.1.** The duplicate is between
>   `storedDirectSubjects` and `edgeHolders`; `enum2BaseD` is a one-element list at the probe
>   shape and `.dedup` is a no-op on it. What landed is **`freshDirectCands`**, a presence
>   diff on the Direct-arm contribution to `cands` ONLY (`negCands`/`uposCands` must stay
>   unfiltered — clause 3 of `W3dJobCoverage` has no `edgeHolders` fallback).
> * **§D.6's "Leg 2 breaks the multiplicity ledger by construction" is REFUTED** — it does
>   not, and no golden regen was owed. Controlled, not assumed: defeating the filter moves
>   exactly one corpus, `[direct_arm_exclusion] golden=[16, 1] observed=[31, 1]`. ⚠ Carry
>   this caveat: with the filter defeated the tree still COMPILES, so `freshDirectCands` is
>   pinned by the ledger, not by the type checker.
>
> **★ LEG 3 LANDED 2026-08-05 — the coverage packaging, plus the instrument the plan forgot.**
> **`w3dJobCoverage_enumJob2D_state`** (`CascadeStrataEnum.lean:981`) is the `_d` twin of
> `w3dJobCoverage_enumJob2_state`: over any `ReachedByW3d2` state on the Direct-arm fragment,
> `enumJob2D`'s coverage holds given only settled+complete derived operands. Audits 465 →
> **467**; **definition pin UNMOVED at 142/142, statements 26/26** — additive, exactly the
> profile predicted. It compiled first try; the plan's leg-3 cell was, for once, accurate
> about the clone.
> Three substitutions carry the widening, and the middle one is the content: the shadow is
> `reachedByW3d2_shadow_d`, whose σ0 is over the FILTERED store `T↾U`, so the leg context must
> be `w3d2_leg_context_d_filt` and NOT `w3d2_leg_context_d` (the full-store pair is jointly
> unsatisfiable here — the 2026-07-20b kill); schema-wide `ComputedOnly` gives way to
> `ComputedOrDirect` + `DirectArmsBare` **plus per-key `hCOop`**, the asymmetry that lets the
> queried expression carry a Direct arm while its operands stay untainted; and
> `reachedByW3d2_reach_collapse_root_d` needs neither `hlk'` nor `ComputedOnly e'`, so this
> proof never looks the operand declaration up and `hCOop` has exactly one consumer.
>
> **★ THE PLAN CORRECTION, AND IT GENERALISES TO LEGS 4–6**
> (`history/echain-widening-plan-2026-07-28.md` §C.3): the cell specified leg 3's gate as
> "`lean` + audit pin" — a clone and no instrument — and **a packaging clone is precisely the
> shape a green build cannot vet.** Unsatisfiable premises compile, audit clean, and pass
> every pin. So the leg also lands **`W4WitnessDirect.coverage_applies`** (`FullScope.lean:785`),
> the `correct_applies`-style instantiation at the real Direct-arm pair `(Sd, Td)`. It assumes
> LESS than `correct_applies` (`hsettledOps` is discharged, vacuously — `banned` is untainted),
> and it is contentful rather than decorative because `outside_old_admission` machine-checks
> `StoreValidRules Sd Td` FALSE: the untainted twin cannot be instantiated at this pair and
> the `_d` twin can.
> **Controlled** — sabotage = one extra unused premise `(_hSABOTAGE : StoreValidRules S T)`,
> false at every store the theorem is about. `CascadeStrataEnum` stays GREEN ("Build completed
> successfully (1061 jobs)"); `FullScope` goes RED with an application type mismatch at
> `coverage_applies`. ⚠ **Carry this into legs 4 and 5, which are much bigger `_d` packagings:
> budget a witness for each, not just a clone.**
>
> **NEXT: Leg 4** — `reachedByW3d2E_toC_d` (~140 lines) + refactor the original into a
> byte-identical wrapper (verify against HEAD, cf. `reachedByW3c_master_d`); same for
> `graph_correct_w3d2E`. Wants its own session. Legs 2 and 3 changed none of its premises.
>
> **[superseded 2026-07-28 — kept for provenance] THE NEXT TASK — #1 Direct arm: the E-CHAIN widening (the recorded gap), OR pivot.** Options in
> rank order: (a) the E-chain widening per the 20e fork list above — payoff: `W4Fragment` widened to
> the `_d` fragment, the final unsuffixed `graph_correct`/`graph_reached_inv`/
> `Exec.graphRun_check_eq_sem` cover Direct arms, and the remove-stream conformance exclusion can be
> revisited (needs the remove-guard → `StoreValidRulesD` + the `hNoUD` lift too); (b) the `hNoUD`
> lift (the star→concrete `sem` coverage monotonicity lemma over the fenced fragment) — smaller,
> self-contained, unlocks the remove leg on union-reachable Direct arms; (c) Direct-arm OPERANDS
> (needs a Direct-arm-aware `sem_untaintedFilter_co`); (d) the TTU/userset leaf half or #2 strata
> (> 2). Exact resume: `history/optional-widening-2026-07.md` Direct-arm RESUME.
> ⚠ OPERATIONAL: `verify.sh conf-rest` observed 9–13 min (often over the 10-min cap) — background w/ 600s
> timeout, retry if cap-killed; consider splitting the phase.

> **Update 2026-07-18 — OPTIONAL assurance-widening arc OPENED (4 targets scoped;
> `FINAL_REVIEW.md §4`).** All four remaining optional widenings were recon'd + (for #1)
> attack-first probed; the durable design + resume state for ALL of them is
> [`history/optional-widening-2026-07.md`](history/optional-widening-2026-07.md) —
> **read it to resume any target.** Progress so far: **#1 Leaf widening (Direct arm)**
> legs 1–3 LANDED (commits `98773d3` read-half `evalE_computedOrDirect`, `0dd8d7b`
> write-half admission `StoreValidRulesD` + the diffing retraction crux
> `reconcileKeyD_retracts_excluded`, `8a9bee1` base-equation WALL characterized —
> `graphRec_base_eq_d` needs a `NoStoreSubjectR` hyp, attack-pinned). Direct-arm leg 4 =
> the wall (3 named lemmas A/B/C, see the design file). **#3 state/enum widening
> increments (c) + (a) LANDED (2026-07-18b/c).** (c): userset (`wildcard_group_member`,
> 176 stores) + TTU (`ttu`, 93 stores) enum shapes added to `test_conformance_enum.py`
> (the self-referential `group_userset` attack-rejected as admission-cyclic for the set
> engine, recorded). (a): the REAL graph index (`WildcardIndex`+`DeltaProcessor`) now runs
> INSIDE the enum at answer level over all six in-`GRAPH_FRAGMENT` shapes — attack-first
> found NO graph≠sem divergence, NO `ValueError` (796 stores × graph grid). Full gate green
> incl. conf phases (290 conf, 0 skip). (b) k=4 LANDED (2026-07-18d): per-shape
> K (four shapes K=4, the two dominators `two_stratum_cascade`/`wildcard_group_member`
> capped at K=3 for the graph-leg-inflated cap). (d) state gate LANDED (2026-07-18e): new
> `test_conformance_enum_state.py` — stride-4 sampled (257/1021) Lean-model vs Python-graph
> STATE compare under `extractor.py` P1–P6, all six shapes, ZERO mismatches. **TARGET #3
> (state/enum widening) COMPLETE** (all of c/a/b/d green, no divergence). Conf now 296, 0
> skip. **#4 remove legs RECON+PROBE DONE (2026-07-18f):
> Route 1 GO with a KILL** — the design's "fold `removeEdgePair` (filter-all)" is a FALSE
> statement in-fragment (rc≥2 shared derivation drops a surviving edge); faithful op is
> `List.erase` (decrement one), and NO `GraphState` ripple (edges already a multiset =
> ref-count). Corrected legs R1–R4 in the design file (R3 occurrence-count invariant is the
> hard content). Legs R1+R2 LANDED (2026-07-18g/h). R1:
> `GraphState.removeEdgeOne` (erase-one) + `count`/membership lemmas + `structInv_removeEdgeOne`.
> R2: the standalone retraction substrate `removeLoggedOne`/`removeLoggedRules`/`RemoveAdmits`
> + `structInv_removeLoggedOne/_Rules`, all additive; verify.sh lean 415/415. **Green-gate
> finding: the `remove` CONSTRUCTOR must land LAST** (leg R5, armed with the R4 confluence) —
> adding it to `ReachedByW3d2E` breaks every downstream induction until discharged. R2 mapped
> the full R5 ripple surface (design file); the one obstruction is `reachedByW3d2E_toC`
> (codomain `ReachedByW3d2C` not EvalEq-invariant → retire from the remove path, fix iii).
> Leg R3 LANDED (2026-07-18i): the UNTAINTED
> occurrence-count invariant `reachedByW3d2E_untOccCount` (`RemoveOccCount.lean`) — an
> untainted edge's model ref-count = its occurrence count over the store's rewrite closures.
> **KILL: the design's derived arm `count ∈ {0,1}` is model-FALSE** (the model stacks derived
> duplicates, compensated by filter-all `removeEdgePair`) — the derived side of R4 is a
> MEMBERSHIP story, not a count bound. **Leg R4 part 1 — the UNTAINTED arm — LANDED (2026-07-19a):**
> new `RemoveConfluence.lean` (additive; verify.sh lean 415/415, conf 296). Attack-first CONFIRMED
> the full confluence (`check(drain(removeLoggedRules σ t)) = sem S (T.erase t)`, zero mismatch over
> the rc≥2-survival + derived-exclusion probe grid). Proved the retraction count-shrink law
> (`count_removeLoggedRules`, dual of R3's write growth), the store-erase split (`untOccCount_erase`),
> and the pre-drain/drained untainted confluence (`drain_removeLoggedRules_untOccCount` +
> `mem_drain_removeLoggedRules_untainted`, `count>0↔mem`): a drained post-remove UNTAINTED edge's
> multiplicity is bit-identical to R3 on a fresh rebuild over `T.erase t`. **R4 part 2 LANDED
> (2026-07-19b):** the `ReadEq` relation + `check`/`reachB` read-congruence (`check_readEq`) + the
> untainted `edgeMem` arm; the derived/residue arms attack-pinned CHAIN-BOUND. **Leg R5 RE-SCOPED
> (2026-07-19c) — the constructor is MONOLITHIC and gated on a MISSING prerequisite.** Deep trace
> (tree left GREEN, lean 415/415, conf 296): `graph_correct_w3d2E` is ∀-quantified over `ReachedByW3d2E`
> + consumed by `FullScope`/`Exec`, so the constructor FORCES its T2b remove case with no partial
> landing; BOTH discharge routes (undrained-all-3-inductives via `settledComplete_cascade2_targeted`,
> or drained-E via `ReadEq`-transport) converge on **REBUILD-EXISTENCE over `T.erase t`** — a build-
> FROM-STORE `∃ σ, ReachedByW3d2E σ S T' ∧ Drained` / `∃ σ0, ReachedByRulesAdmitted σ0 S T'` — which
> is ABSENT (every existing `∃ ReachedByRules…` is shadow-FROM-chain). REACHABLE via
> `foldAdmits_of_acyclic` (`RestrictBase.lean:392`, discharges `FoldAdmits` from acyclicity) +
> closure-acyclicity. **LANDED additively this session (green):** the T2a Group-A STRUCTURAL remove-case
> discharges — `removeLoggedOne_/removeLoggedRules_residue`, `mem_removeLoggedRules_edges`,
> `residueHygienic_/residueDeclared_removeLoggedRules` (`RemoveConfluence.lean`) — the retraction is
> residue-inert + edge-shrinking. **Leg R5a — REBUILD-EXISTENCE LANDED (2026-07-19d, additive, lean
> 415/415):** `exists_admitted_erase`/`_ofSubset`/`_ofAcyclicTarget` (`RemoveConfluence.lean`) — the
> build-FROM-store admitted witness `∃ σ0, ReachedByRulesAdmitted σ0 S (T.erase t)` (STORE-restriction
> dual of `exists_admitted_restrict`), acyclicity INHERITED from the larger admitted store's
> `Inv.acyclic` (attack-first KILL: from-scratch arbitrary-store rebuild is FALSE — a userset 2-cycle
> store is admission-rejected; free only over a SUB-store, the exact R5b shape). **THE NEXT TASK: #4
> Leg R5b — the (undrained, route-a) `remove` constructor** on `ReachedByW3d2`/`C`/`E` + the settledness
> duals (`removeLeg_sem_stable2` / `settledKey_removeLeg` / `cascadeKeys_removeLeg_mono` /
> `removeLeg_derived_inedges_eq`, duals of `CascadeStrataSettle.lean:1064-1207`) + `reachedByW3d2_shadow`
> /`reachedByW3d2C_settled` remove cases. Recommend route (a) — undrained mirrors `write`, so `toC`'s
> remove case is trivial (`ReachedByW3d2C.remove`) and the fix-(iii) obstruction dissolves. Full detail:
> `history/PROOF_STATUS.md` 2026-07-19c + `history/optional-widening-2026-07.md` Leg R5. After #4:
> back to #1 Direct-arm leg 4+ / TTU half, #2 strata (>2). Not started: #1 TTU/userset half, #2 strata.

> **Update 2026-07-17 — rootB fragment widening LANDED (3 legs).** `W4Fragment`
> no longer restricts the derived-def ROOT operator: `RootBoolean` is DELETED and
> the shape condition is `ComputedOnly` alone, so union- and computed-rooted
> derived defs are inside the proved scope. Three commits: (1) `397f975` —
> `schemaRewrites` taint-filtered (`S.defs.filter (!isDerived …)`, the faithful
> mirror of `compile_ruleset`'s taint routing; a probe had found the UNFILTERED
> fanout leaked a stale userset-sourced edge `group:eng#member → approver` at a
> union-rooted derived R-node into the drained state — a real model-vs-Python
> state divergence); (2) `c3d3113` — `RootBoolean` deleted, `W4Fragment` widened;
> (3) this leg — the union-rooted non-vacuity witness `W4WitnessUnion`
> (`FullScope.lean`, audited) + the conformance widening: `taint_union_over_boolean`
> moved INTO `GRAPH_FRAGMENT`, two new pins added (`taint_union_userset_arm` — the
> stale-fanout STATE regression; `taint_computed_root_over_boolean` — computed
> roots). Gate green: audit 415, conformance 288/0-skip.

| theorem | file (`lean/ZanzibarProofs/`) | scope |
|---|---|---|
| T1 `setEngine_correct` | `SetEngine/Correct.lean` | full |
| T0a `sem_fuel_stable` (over `StoreDeclared`) | `Spec/WellDef.lean` | full |
| T0b `stratify_none_iff_cycle` / `stratify_topological` | `Spec/WellDef.lean` | full |
| T4 `pathCount_addEdge` / `_removeEdge` | `GraphIndex/Closure.lean` | full |
| T5 `cascade_converges_direct`, T2a `graph_reached_inv_direct` | `GraphIndex/Correct.lean` | fragment (W1; the contentful T5 is `runCascade_no_abort`/`cascade2_drains`) |
| T2b `graph_correct_direct` | `GraphIndex/DirectCorrect.lean` | star-free pure-direct |
| T2b `graph_correct_bareStar` | `GraphIndex/BareStarCorrect.lean` | + bare `[user:*]` grants |
| T2b `graph_correct_objStar` | `GraphIndex/ObjStarClosure.lean` | + object wildcards (out-bridges) |
| T2b `graph_correct_usStar` | `GraphIndex/UsStarClosure.lean` | + userset stars (in-bridges) |
| T2b `graph_correct_rules` | `GraphIndex/RulesComplete.lean` | untainted computed/ttu/union |
| T2b `graph_correct_w3a` | `GraphIndex/ReconcileComplete.lean` | + one `ComputedOnly` derived key (root operator UNRESTRICTED since the 2026-07-17 `RootBoolean` removal), bare-subject queries |
| T2b `graph_correct_w3b` | `GraphIndex/ReconcileUposComplete.lean` | + userset subjects via `upos` (bare-subject restriction LIFTED) |
| T2a `reachedByW3c_inv` / `reachedByW3c_master` | `GraphIndex/ReconcileStars.lean` | W3c write half: `stars`/`neg` model, ALL I6 clauses contentful, star-general (no `StarFreeStore`) |
| T2b `graph_correct_rulesBS` | `GraphIndex/RulesBareStar.lean` | W2 untainted correspondence over `BareStarStore`+`TtuStarFree`, star-BARE subjects incl. |
| `graphRec_base_eq_bs` / `checkFn_eq_sem_bs` | `RestrictBase.lean` / `ReconcileComplete.lean` | the STAR-RELAXED base equation + `checkFn ↔ sem` bridge (no `StarFreeStore`) |
| T2b `graph_correct_w3c` + `coveredFn_declared` (the linchpin) + `w3c_row_char` + batch completeness | `ReconcileStarsComplete.lean` | + star-carrying stores: bare `T:*` grants, `stars`/`neg`/`upos` reads, bare/star-BARE/userset subjects |
| T3/T6 `backend_equivalence*` / `exclusion_effective*` / `no_ghost_grant*` | `Equiv.lean` | per-fragment corollaries (incl. `_w3a`, `_w3b`, `_w3c`) |
| **T5** `runCascade_no_abort` / `cascade_drains` + `ReachedByW3d` | `GraphIndex/Cascade.lean` | W3d-1a: the scheduler in the model — logged writes, `affectedKeys`, the drain loop; reject branch provably dead at one stratum; `Quiescent` earned — RE-EARNED over the diffing pass (decision 7) |
| the DIFFING pass + per-key edge EXACTNESS | `GraphIndex/ReconcileDiff.lean` | W3d-1b groundwork: `reconcileStarsKeyD` (stale-edge retraction, `processor.py:359-367`), both-direction reach inertness, guard fold-invariance, `reconcileStarsKeyD_edge_char` (the re-settle as a theorem) |
| FAN-OUT COMPLETENESS + the untainted-core shadow + settledness transport | `GraphIndex/CascadeStable.lean` | W3d-1b core: `writeLeg_checkFn_stable` (unmapped keys' guards unchanged), `reachedByW3d_shadow`/`checkFn_eq_sem_w3d` (guard = `sem` at EVERY W3d state, incl. mid-batch), `writeLeg_sem_stable` (unmapped keys keep their MEANING), `SettledKey` + write-leg/untargeted-cascade transport |
| T2b **`graph_correct_w3d`** + the settledness invariant + targeted RE-settlement | `GraphIndex/CascadeSettle.lean` | W3d-1b CLOSED: `ReachedByW3dC` (coverage chain: per-job `W3dJobCoverage`, attack-confirmed edge-holder clause), `settledComplete_cascade_targeted`, `CompleteKey` + transports, `reachedByW3dC_settled` (dirty-or-settled at EVERY state), the W3d reach collapse, `check = sem` at every fully-drained (`cascadeKeys = []`) state; T3/T6 `*_w3d` |
| T2a **`reachedByW3dC_inv`** — the FULL 8-clause `Inv` (+ `reachedByW3d_structInv` / `reachedByW3d_residueHygienic` / `reachedByW3d_residueDeclared` / `reachedByW3dC_edgeHygienic`) | `GraphIndex/CascadeInv.lean` | W3d-1c piece A CLOSED: `Inv` at EVERY coverage-chain state (dirty keys, mid-drain included). Structural half + edge-free I6: NO fragment hyps. Edge-referencing I6 (`negEdgeFree`/`uposEdgeFree`): attack-REFUTED over the plain chain (stale non-candidate edge — the coverage clauses are load-bearing for the invariant itself, not just the read theorem); proved over `ReachedByW3dC` via row-key declaredness + the reach collapse + the `SettledKey` verdict clash at targeted keys |
| **`w3dJobCoverage_enumJob`** (+ the collapse `checkFn_eq_coveredFn_of_no_extra`, `leafConcretes`/`edgeHolders`, per-clause discharges, `w3d_leg_context`) | `GraphIndex/CascadeEnum.lean` | W3d-1c piece B CORE: **`W3dJobCoverage` is now a THEOREM** of a state-derived enumeration (was a chain-side hypothesis). Spine: a star-free subject's operand leaf reads decompose pointwise as star-read ∨ two concrete probes (`probeNonDerived_concrete_decomp`); a subject hitting neither probe reads exactly as its shape-star (`evalE` congruence, exclusion-safe). `w3d_leg_context` rebuilds the read bridge + coverage-declaredness at any W3d state via the shadow |
| **`graph_correct_w3dE`** / **`reachedByW3dE_inv`** (+ `ReachedByW3dE`, `reachedByW3dE_toC`, `enumJobs`/`_valid`/`_cover`/`_scope`/`_covg`, `w3cJobValid_enumJob`, `reachedByW3d_Rnode_source_name_ne_star`) | `GraphIndex/CascadeEnum.lean` | **W3d-1c piece B TAIL — W3d-1c CLOSED.** The enumerated-cascade restatement: `ReachedByW3dE` is the fully-operational scheduler chain (cascade legs run the state-derived `enumJobs`, NO `W3dJobCoverage`/`hcover`/`hscope`/`hjv` in the constructor); `reachedByW3dE_toC` projects it to `ReachedByW3dC` (the four hyps discharged by `enumJobs_*`, store hyps weakened along write prefixes). `check = sem` (fully-drained) and the full 8-clause `Inv` (every state) now hold UNCONDITIONALLY over the operational chain |
| the ROUTED leaf dispatch + conservativity + the TWO-ROUND scheduler | `GraphIndex/CascadeStrata.lean` | W3d-2 OPENING: `graphRecR`/`checkFnR`/`coveredFnR` (every operand leaf reads the graph's own `check` — untainted ⇒ `probeNonDerived`, derived ⇒ `probeDerived`; `processor.py:43-70, 182-188`), `checkFnR_eq_checkFn` (conservativity: on untainted-operand defs the routed read IS the W3d read), `checkFnR_evalEq` (the routed read consults exactly the `EvalEq` core — residue+schema now included), the routed diffing pass + `reconcileJobsLR_eq` (W3d-1 is the single-stratum image of the routed scheduler), `runCascade2` (rounds = 2, per-round frontier cursor, leftover reject), `ReachedByW3d2` (C-style two-batch closure), `reachedByW3d2_schema`. Attack-first: fully-drained `check = sem` SURVIVED all cross-stratum vectors; mid-drain staleness real; within-round order not load-bearing |
| **T5 at TWO STRATA** — `runCascade2_no_abort` / `cascade2_drains` + the W3d-2 structural layer | `GraphIndex/CascadeStrata.lean` | W3d-2 items 1–2 (2026-07-12d): routed-batch outbox/edge soundness (`reconcileJobsLR_outbox_sound`/`_edge_sound`), R-node terminality over the two-round closure (+ the round-STACKABLE batch transport), cursor arithmetic (`outbox_le_frontierMax` — a round's read is exhaustive). The reject branch provably dead under **`hLU2`** (two-stratum condition, dependency-wise; strictly wider than `hLU`, `hLU2_of_hLU`); attack-confirmed load-bearing (3-stratum schema ⇒ `hLU2` FALSE and the reject FIRES) |
| **per-stratum operand-read INERTNESS** — `check_reconcileStarsKeyDR_other` / `checkFnR_reconcileStarsKeyDR_other` | `GraphIndex/CascadeStrata.lean` | W3d-2 item 3a (2026-07-12d): a routed pass is read-inert at every OTHER key WHATEVER its stratum (untainted probe via `graphRec_reconcileStarsKeyDR_inert`, derived read via `probeDerived_reconcileStarsKeyDR_other` — node inequality from key inequality; guard form via `evalE_computedOnly`), on routed mirrors of the W3d-1b reach-inertness/closure/residue-other layer. The base fact for the stratum-staged settledness transport |
| **the W3d2 SHADOW + the stratum-staged READ BRIDGE + settledness transports + `ReachedByW3d2C`** — `reachedByW3d2_shadow`, `probeDerived_eq_sem_settled`, **`checkFnR_eq_sem_settled`**, `round2_key_reads_derived`, **`writeLeg_sem_stable2`**, `reconcileJobsLR_emits`/`round1_emission_dirties`, `reconcileJobsLR_reach_collapse` | `GraphIndex/CascadeStrataSettle.lean` | W3d-2 item 3b (2026-07-12e): W3d2 chain structural mirrors + the shadow at every state (mid-round prefixes incl.); the settled-key derived read (factored from `graph_correct_w3d`); the stratum-staged bridge (routed guard = `sem` at settled+complete derived operand keys — attack-confirmed load-bearing); per-round settled/complete transports + the stratum fence (round 2 never targets stratum-1 keys); write-leg `sem` stability at BOTH strata (stratum-2 needs key AND operand keys unmapped — the attack-REFUTED "dirty ∨ settled" gains the third disjunct "operand-dirty"); every job EMITS (round-1 operand passes provably re-dirty stratum-2 readers); the two-round coverage chain (round-2 coverage rel. the MID state) |
| **`graph_correct_w3d2`** + **`reachedByW3d2C_settled`** (the THREE-disjunct invariant) + the ROUTED edge char + the two-round re-settlement — `reconcileStarsKeyDR_edge_char` (via `computedRefs_ne_self`), `reconcileJobsLR_key_edge_sem`, `settledComplete_jobsLR_targeted`/`settledComplete_cascade2_targeted`, `sem_nil_derived_false2`, `graphRec_star_declared` | `GraphIndex/CascadeStrataResettle.lean` + `Equiv.lean` | **W3d-2 ENDGAME (2026-07-12f)**: `check = sem` at every fully-drained `ReachedByW3d2C` state — TWO strata (`hLU2`), W3d-1 subject/query scope; the settled ∨ dirty ∨ operand-dirty invariant at EVERY state; no-ghost-star-coverage at ANY stratum via the drained-state routed bridge; T3/T6 `*_w3d2` |
| the DERIVED-leaf decomposition + routed reads-as-star + `enumJob2` coverage — `probeDerived_concrete_off_named`, `residueNamed`, `checkFnR_eq_star_of_not_enum`, `enumJob2`/`w3dJobCoverage_enumJob2`, `checkFnR_star_declared`/`w3d2_leg_context`, `w3dJobCoverage_enumJob2_state` | `GraphIndex/CascadeStrataEnum.lean` | **W3d-2 E-chain tail CORE (2026-07-12g)**: the two-round chain's audit enumeration + its `W3dJobCoverage`. Finding (c)'s residue-named candidates (`neg`/`upos`, edge-free/I6) folded into `enumJob2`; routed reads-as-star (no reach-collapse needed); coverage from the routed leg context (`checkFnR_eq_sem_settled` + `checkFnR_star_declared`) at any `ReachedByW3d2` state given operand settledness (`hsettledOps`) |
| **`graph_correct_w3d2E`** / **`ReachedByW3d2E`** / **`reachedByW3d2E_toC`** + the CONDITIONAL coverage chain (`W3dJobOpsSettled`, `covg_of_opsSettled`) + `enumJobs2R1`/`enumJobs2R2`/`enumJobs2At_*` + `ResidueSubjectsStarFree`/`reachedByW3d2_residueStarFree` + `w3cJobValid_enumJob2` + R-node source star-freeness (chain+batch) | `GraphIndex/CascadeStrataAssemble.lean` (+ `CascadeStrataSettle/Resettle` hyp changes) | **W3d-2 CLOSED (2026-07-12h).** Attack-REFUTED (kill #6): "round-1 keys are stratum-1" is FALSE — a write to a DIRECT untainted leaf of a stratum-2 def dirties it at the watermark, where the leg-start enumeration provably misses a fresh grant living only in the dirty operand's future residue. So `ReachedByW3d2C`'s per-round coverage is CONDITIONAL on the job's operand baseline (`W3dJobOpsSettled` — exactly what the 12f re-settlement consumes), and the E-chain discharges it from state: round 1 hands the baseline premise to `w3dJobCoverage_enumJob2_state`, round 2 runs the routed leg context at the transported MID state. `check = sem` at every fully-drained state of the FULLY-OPERATIONAL two-round scheduler chain |

| **W4** `ReachedBy`/`Drained` + **`GraphAdmission`** (Python-admission mirror, per-field citations, incl. `objWild`) / **`W4Fragment`** (the honest carries) + **`w4_within_scope`** (bundles ⇒ the spec's decision-15 `GraphAccepts`) + the FINAL unsuffixed **`graph_correct` / `backend_equivalence` / `exclusion_effective` / `no_ghost_grant`** (W1 versions renamed `*_direct`) + W2-subsumption lemmas (`drained_of_untainted`/`w4Fragment_of_untainted`) + **non-vacuity witnesses** (`W4Witness.accepts`/`fragment`/`within_scope` — both bundles inhabited by a real compiled boolean schema) | `FullScope.lean` | the deleted-as-false T2b/T3/T6 obligations DISCHARGED at the achieved scope; hypotheses split by provenance; honest-gaps list in ROADMAP W4 |
| **W4 T2a groundwork** — `StructInv` / edge-free I6 (`ResidueHygienic`) / `ResidueDeclared` at every `ReachedByW3d2`/`W3d2C`/`W3d2E` state (E-chain versions HYPOTHESIS-FREE, `enumJobs2At_keyFacts`); **pass-local I6** `reconcileStarsKeyDR_row_edge_consistent` (+ `enumJob2_negCands_subset`) — the routed pass's row is edge-consistent with its OWN audit, no settled verdicts, so it holds at re-dirtied stale keys (12h attack shape) where the W3d-1 coverage route can't go | `GraphIndex/CascadeStrataInv.lean` | the fragment-free 3 of 8 `Inv` clauses over the OPERATIONAL chain + the core of the edge-referencing 2 |
| **W4 T2a ASSEMBLY — `reachedByW3d2E_inv` (full 8-clause `Inv`, every state) + the final `graph_reached_inv`** (`EdgeHyg1` direct-edge form; `edgeHyg1_applyLoggedR`/`_reconcileJobsLR`/`_runCascade2` — pass-local at the job key, other-key fixedness elsewhere, batch of ENUMERATED jobs; `reachedByW3d2E_edgeHyg1`→`_edgeHygienic` via the reach collapse; write legs via `writeLeg_derived_inedges_eq`) | `GraphIndex/CascadeStrataEdge.lean` + `FullScope.lean` | **W4 CLOSED.** T2a over `ReachedBy` with the provenance-split bundles; W1 direct version renamed `graph_reached_inv_direct` |

| **Phase 6 driver honesty** — `foldAdmitsB_iff` / **`graphRun_reached`** / `graphRun_store` / `drainedB_iff` / **`graphRun_check_eq_sem`** | `GraphIndex/Exec.lean` | the zcli graph mode IS the chain: the driver folds the `ReachedBy` constructors, its runtime gates decide the theorem's side conditions, and under the W4 bundles every printed verdict is `sem` |

**Staged T2 widening: W1 ✅ → W2 ✅ → W3a ✅ → W3b ✅ → W3c ✅ → W3d-1a ✅ → W3d-1b ✅ → W3d-1c ✅ → W3d-2 ✅ → W4 ✅ (CLOSED 2026-07-12j — full T2a/T2b/T3/T6 over `ReachedBy := ReachedByW3d2E`). Phase 6 items 1–3 ✅ (CLOSED 2026-07-12k — graph-state conformance mode + `CORRESPONDENCE.md` + `FINAL_REVIEW.md`).**

**W3c is CLOSED (2026-07-11d).** Full detail: the 2026-07-11* `history/PROOF_STATUS.md`
entries and the `history/ROADMAP.md` W3c paragraphs. The pieces a W3d session will reuse:
- **Write model** (`ReconcileStars.lean`): `wildcardShapes` / `coveredFn` (star-subject
  `checkFn`) / `reconcileResidueKey` (wholesale stars+neg+upos recompute) / `reconcileKeyC`
  (covered-guarded edge fold) / `reconcileStarsKey` (residue-THEN-edges, the faithful atomic
  unit). Three structural devices: the **covered-filter collapse** (`reconcileKeyC_eq_filter` —
  the W3c edge fold IS a W3a `reconcileKey` on filtered candidates), the **shadow projection**
  (`reachedByW3c_shadow` — every W3c state has a W3a-admitted shadow with identical core), and
  **star-general operand-read inertness** (`graphRec_reconcileKey_inert`, no `StarFreeStore`).
  `reachedByW3c_master`: canonical base σ0 per chain — canonical `stars` rows + guard canonicity.
  T2a `reachedByW3c_inv` with ALL FOUR I6 clauses contentful.
- **Read half** (`ReconcileStarsComplete.lean`): `checkFn_eq_sem_w3c` (bridge on any W3c state);
  **the LINCHPIN `coveredFn_declared`** (no ghost star coverage: a `sem`-covered shape is
  DECLARED — first edge out of the `wAny` node is a materialised closure tuple whose star seed
  matched a wildcard-flagged restriction); `w3c_row_char` (persisted rows read at `sem` level);
  batch completeness for the WHOLESALE recompute (`reconcileJobsC_row_isSome`,
  `_neg_complete`/`_upos_complete` with the **∀-targeting-jobs enumeration form** — attack-
  confirmed necessary: a later same-key pass with an incomplete `negCands` drops the exclusion);
  `w3cComplete_derived_edge`; **`graph_correct_w3c`** (star ⇒ `stars`, bare ⇒ edge ∨ `stars`∖`neg`,
  userset ⇒ `upos` exactly — `hWSbare` kills userset coverage). Fragment hyps: `BareStarStore` +
  `TtuStarFree` + `hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE` (decision-15) + the W3a/W3b
  carries (`hterm`/`hCO`/`hLU`/`hRootB`); query scope `hqs : name = STAR → predicate = BARE`,
  concrete object. T3/T6 `*_w3c` incl. `exclusion_effective_w3c` (a concrete subject excluded
  from UNDER a `T:*` grant — the space rule's `neg` actually excludes).

---

## Board — the two ORPHANED findings, adjudicated 2026-07-27 (ZT-P4 item 4)

Both lived only in `history/` and had reached no board. Each was re-verified
against the working tree (commands quoted). **Paste-ready paragraphs for the root
board are the two blocks below, verbatim.**

### B1 — `w3cJobValid_enumJob2D` star-freeness hole · verdict: **STILL OPEN, but RECLASSIFIED**

> **`w3cJobValid_enumJob2D` star-freeness hole — open, but it is a DESIGN BLOCKER,
> not a live attack surface.** Recorded in `formal/history/optional-widening-2026-07.md`
> (E-chain widening step 2) and PROOF_STATUS 2026-07-20e as an "OPEN attack surface"
> naming a schema shape Python admits: under `W4Fragment.wsBare` a WILDCARD-flagged
> restriction may sit on a **derived Direct arm**, so leg-5c's `storedDirectSubjects`
> can contain a `user:*` subject and `W3cJobValid`'s star-free-candidates clause FAILS
> for `enumJob2D`. Re-verified 2026-07-27: (i) Python really does admit the shape —
> `define approver: [user, user:*] but not banned` compiles (1 stratum,
> `subject_wildcard_shapes={('user','...')}`) and oracle == set engine == real graph
> index over the full 20-query grid, alice True / mallory False; (ii) `grep -rn
> "w3cJobValid_enumJob2D" formal/lean/` returns **nothing** — the lemma does not exist,
> so **no landed theorem depends on it**; (iii) the shape is outside `W4Fragment`
> (`computedOnly`) *and* outside the C-chain `_d` fragment (`DirectArmsBare`), so
> no proved claim is being over-stated. **Verdict: the finding is real and unclosed,
> but its disposition is "a lemma the not-yet-started E-chain widening cannot prove
> as stated", not "an unsound claim in the tree". Fixing it means choosing, before
> the widening starts, between a star-filter inside `storedDirectSubjects` (touches
> landed leg-5c defs + consumers) and a new fragment clause banning wildcard
> restrictions on derived Direct arms.** Needs a decision, not a proof session.

### B2 — `PDerivedUserset` never modelled in Lean · verdict: **OVERTAKEN Python-side; a DECLARED Lean scope gap; the CONFORMANCE half was a real hole and is now closed**

> **`PDerivedUserset` — Python-side overtaken, Lean-side a declared scope gap, and
> it had ZERO conformance coverage until 2026-07-27.** The X4 shape (a userset
> restriction `[group#member]` whose predicate is itself derived) was fixed
> Python-side 2026-07-13 and extended 2026-07-17, and never modelled in Lean — in
> the exact plan-leaf area where five real divergences were found. Re-verified
> 2026-07-27: Python-side it is **overtaken** — `define member: base but not kicked`
> + `define viewer: [group#member]` compiles to a real `PDerivedUserset` leaf
> (`LeafSpec('viewer.0','derived-userset', storage=True)`, 2 strata) and oracle ==
> set engine == real graph index over the full 126-query grid (alice True, kicked
> bob False); `tests/test_lookup_oracle.py`'s former strict xfails are plain
> regression pins. Lean-side it is a **declared** scope gap, not a silent one:
> `FullScope.lean::W4Fragment`'s doc says `PDerivedTTU`/`PDerivedUserset` leaves are
> "out of scope (W3a decision)", and `term`/`NoStoreSubjectR` forbids the stored
> userset tuple the shape needs. **The genuinely new finding is the conformance
> half:** walking every `RuleSet.compiled.plans[..].leaves` over all 69 schemas the
> harness reads gave the leaf-kind histogram `closure 211 · derived-computed 42 ·
> derived-ttu 50 · derived-userset 0 · derived-tupleset-ttu 0` — i.e. **no corpus
> compiled a `PDerivedUserset` leaf at all**, so no differential ever exercised that
> compiler branch. Closed for `derived-userset` by
> `corpus.py::TTU_USERSET_SCHEMAS['derived_userset']` (spec-side; scope argument in
> situ) and floored by
> `test_conformance_nary_strata.py::test_every_plan_leaf_kind_is_reached_by_some_corpus`.
> ~~**`derived-tupleset-ttu` (`PDerivedTuplesetTTU`) is still at ZERO and is the
> remaining plan-leaf hole — deliberately not faked into the floor.**~~
> **CLOSED 2026-07-28** by `TTU_USERSET_SCHEMAS['derived_tupleset_ttu']`, together
> with the other zero-coverage hole (wildcard usersets `[T:*#p]`,
> `TTU_USERSET_SCHEMAS['wildcard_userset']`). The floor now names EVERY kind
> `zanzibar_utils_v1._plan_leaves` can emit, and
> `test_required_leaf_kinds_are_exactly_the_compilers_kinds` reads those kinds out
> of the compiler's own source so the list cannot go stale. Conformance 450 → 464.
> Two reachability corrections worth carrying: a wildcard userset over a DERIVED
> relation is a compile-time scope rejection raised out of `parse_openfga_schema`,
> so it can never be a corpus (only the UNTAINTED surface is reachable); and
> `derived-tupleset-ttu` was always reachable — the obstacle was that TTU parents
> are STORED tupleset tuples, so a derived tupleset without a `Direct` restriction
> compiles the leaf and drives it EMPTY (which is why `demorgans_law_1.fga` could
> not serve). Both corpora are spec-side + a python-only 3-backend leg and are
> asserted OUT of `SCHEMAS`/`GRAPH_FRAGMENT`: `wildcard_userset` falsifies
> `W4Fragment.wsBare`; `derived_tupleset_ttu` falsifies `W4Fragment.computedOnly`
> AND `GraphAdmission.ttuDirect`. Detail + all seven sabotage runs:
> `formal/history/nary-strata-coverage-2026-07-27.md` (2026-07-28 addendum).
> Verdict: Python OVERTAKEN · Lean DECLARED-OUT-OF-SCOPE (no action) · conformance
> CLOSED for both.

---

## Status — the arc is COMPLETE; what remains is optional

**The formal-verification arc is finished.** T1 + T2a/T2b + T3/T6 over `ReachedBy`,
the graph conformance mode (zcli `"graph"` + `test_conformance_graph.py`),
**state-level graph conformance** (zcli mode `"graph-state"` emitting the model's
canonical final state; `formal/conformance/extractor.py` reading the Python
`EdgeV4`/`ResidueV1` rows back to the same form under six DOCUMENTED projections
P1–P6; `test_conformance_state.py`, **19** corpora — its first run FOUND the P6
leaf-family divergence, recorded in `CORRESPONDENCE.md` §7), **exhaustive small-scope
enumeration** (`test_conformance_enum.py`: ALL stores ≤ K tuples, 2 names/type, **six
shapes, 1021 stores** at a per-shape K of 3 or 4, spec × oracle × set engine, counts
asserted — plus `test_conformance_enum_state.py`, a state-level leg over a stride-4
sample of 257 of those 1021), the **remove-path
answer gate** (`test_conformance_remove.py`, 80 tests: seeded add/remove/re-add sequences
× the spec-scope corpora × 5 seeds, driven `SetEngine` == `sem` × oracle on the final store, driven
== `rebuild()` at grid + state-fingerprint level — and, added 2026-07-13, the SAME
sequences/seeds driven through the real GRAPH index (`WildcardIndex`+`DeltaProcessor`,
I5 leaf-routing): driven graph `check` == oracle, driven graph SQL state == a fresh
add-only build's, full-churn drains to a fresh-EMPTY graph with I12 non-mutation on a
rejected repeat remove; so BOTH Python remove paths are now pinned, and the Lean
remove leg is now CLOSED too (2026-07-19f) at the validly-stored + drained-prior
scope — the `remove` constructor on `ReachedByW3d2`/`C`/`E` carries T2a/T2b +
`Exec.graphRun_check_eq_sem` over retraction of a `t ∈ T` from a drained state
under the pre-remove store's disciplines, faithful to `TupleSource.remove`; and the
Exec driver / zcli graph mode now DRIVES removes end-to-end too (2026-07-19,
`graphRunOps` / `removeGateB` / `test_conformance_remove_graph.py`), so
remove-correctness is now both proved over the chain AND driven end-to-end — and the
guard's validly-stored scope decision is APPROVED by Avery 2026-07-19), the
**generated-schema answer gate**
(`test_conformance_generated.py`: 40 seeded generated schemas outside the curated
corpora, spec == oracle == set engine — closes the disjoint-pools risk at answer
level), `CORRESPONDENCE.md`, and `FINAL_REVIEW.md` are all landed and gated.
verify.sh: **330** conformance tests, 0 skips, 0 xfails (measured 2026-07-26 at
`f2b403c`). Removes are driven end-to-end over every in-fragment corpus **except
`direct_arm_exclusion`** (`test_conformance_remove_graph.py:102` `_REMOVE_EXCLUDED` — the
remove guard's plain-`StoreValidRules` precondition fail-closes on Direct-arm stores).
**No open blocker for the claim as written in `FINAL_REVIEW.md`** — but note that claim
now carries `FINAL_REVIEW.md` §3.0: the final graph theorems are VACUOUS on `Direct`-arm
derived stores (`FullScope.lean:564`), which is the highest-value open widening. The topical
map is `ARCHITECTURE.md`; the exact claim is `FINAL_REVIEW.md`; provenance is
`history/`. The one known check-level graph-vs-set divergence (derived-TTU
userset subjects — outside `W4Fragment` and the conformance grids) was FIXED
2026-07-13 Python-side; its strict xfails in `tests/test_lookup_oracle.py` are
now plain regression pins, Lean untouched — see `FINAL_REVIEW.md` §3's
resolved note and `docs/spec-deviations.md` 2026-07-13.

**Done 2026-07-13 (spec-side, no Lean changes) — the X4 adjudication is now
anchored to `sem`.** The 2026-07-13 X4 fix followed the ORACLE where the boolean
spec is SILENT on userset subjects through a TTU's stored tupleset parents; the
formal trust root (`sem`) had never been consulted on those exact shapes (no
corpus exercised them). Three spec-side corpora now do — `TTU_USERSET_SCHEMAS`
in `corpus.py` (from-chain userset through an untainted TTU; the cross-object
membership lift; from-chain userset through a TTU over a DERIVED boolean target),
consumed ONLY by `test_conformance_spec.py`'s full-scope spec/oracle/set-engine
comparisons (T1 places no fragment restriction). Result: `sem` == oracle == set
engine on every grid query (the from-chain userset answers True on all three,
matching the oracle the graph was fixed toward) — the adjudication is anchored,
not merely asserted. Kept OUT of `SCHEMAS`/`GRAPH_FRAGMENT` on purpose: the
shapes are outside `W4Fragment`, so the graph/state/remove gates must not carry
them. Conformance 248 → 257 (+9 = 3 corpora × 3 comparisons).

What remains is entirely OPTIONAL assurance-widening, ranked in `FINAL_REVIEW.md` §4:

1. **Fragment widening (leaves + strata)** — the derived-def ROOT gap is ✅ **DONE
   (2026-07-17)**: `RootBoolean` deleted, union-/computed-rooted derived defs in
   scope, `taint_union_over_boolean` + two new pins now in `GRAPH_FRAGMENT`. What
   REMAINS is the LEAF/strata fragment — `computedOnly` still bans `Direct`/TTU
   arms in derived defs (`PDerivedTTU`/`PDerivedUserset` plan leaves), and
   `twoStrata` still caps at ≤ 2 derived strata (attack-confirmed load-bearing:
   a 3-stratum schema fires the round-2 reject). Widening either is the open
   fragment work; both are genuine proof effort (not just a probe-faithful gap
   like roots was). **IN PROGRESS 2026-07-18:** the LEAF Direct-arm sub-legs 1–3
   landed (`98773d3`/`0dd8d7b`/`8a9bee1`); leg 4 (the base-equation wall) + leg 5
   + the TTU/userset half + strata all scoped in
   [`history/optional-widening-2026-07.md`](history/optional-widening-2026-07.md).
2. **Remove legs** — the Lean remove leg is **DONE (2026-07-19f)** at the
   validly-stored + drained-prior scope: the `remove` constructor on
   `ReachedByW3d2`/`C`/`E` carries T2a/T2b + `Exec.graphRun_check_eq_sem` over
   retraction of a `t ∈ T` from a drained state (`cascadeKeys = []`) under the
   pre-remove store's `StoreValidRules`/`BareStarStore`/`TtuStarFree`/`htermT`
   disciplines (faithful to `TupleSource.remove`). BOTH Python remove paths were
   already answer-pinned by `test_conformance_remove.py` (the set engine at
   rebuild-fingerprint level, the graph index by fresh-build state convergence +
   full drain). So the Lean model IS now a post-remove reference under that
   precondition. **Done 2026-07-19 (`5a35ec3`) — the Exec-driver remove hardening
   LANDED:** `graphRunOps` drives one runtime-gated `remove` chain leg (`removeGateB`,
   fail-closed) per op, zcli graph/graph-state modes take an optional `"ops"`
   add/remove stream (absent ⇒ the legacy add-only `graphRun`, byte-identical), and
   `test_conformance_remove_graph.py` differential-gates seeded add/remove/re-add
   streams (zcli `graphRunOps`) against the real Python graph index and the oracle
   on the erased store (ANSWER-level), so remove-correctness is now both PROVED and
   DRIVEN end-to-end. The guard's validly-stored scope decision was **APPROVED by
   Avery (2026-07-19)** — #4 has no remaining open part.
3. **Widening the state/enumeration bounds** — graph backend inside the
   enumeration, k = 4, a userset/TTU shape, state gate over enumerated stores.
   (The current bounds, their runtime rationale, and why the graph side was
   left out are documented in `test_conformance_enum.py`'s module docstring —
   read it first; it is half the plan.) **[my recommendation #3, first half —
   Python-only; the graph-in-enumeration half is the meaty part.]**
4. **Model the read surfaces in Lean** — LOWEST priority, deferred to the
   eventual full-spec effort. `lookup` / `lookup_reverse` / `expand`
   (list-objects / list-users) have no Lean model yet. Cheap to specify (a
   comprehension over `sem`) but the completeness proof drags in the
   interner/candidate-universe layer T1 abstracts away, and the surface is
   empirically subtle (X1/X3/X4 all lived here). Pinned empirically for now by
   `tests/test_lookup_oracle.py` + the hypothesis campaign (lookup coverage
   added 2026-07-13). NOT out of scope — just not done; see `FINAL_REVIEW.md`
   §4(g).
4. ~~**Fixing the derived-TTU userset-subject divergence** pinned in
   `tests/test_lookup_oracle.py`, then flipping its strict xfails.~~ ✅ **DONE
   (2026-07-13, Python-side — Lean untouched, `W4Fragment` unchanged;
   processor from-chain rule + `upos` lift, set-engine write-time interning;
   gate now 16 passed / 0 xfail; see the `history/PROOF_STATUS.md` top entry).**

Repo-side (outside the formal effort, smaller, Python-only):

- ~~**Pure-union latent gap**~~ — **DONE 2026-07-13.** Fixture written
  (`tests/test_pure_union_ttu.py`); **no real divergence** — the shape is
  unreachable on the graph. `_validate_ttu_tuplesets` rejects any untainted
  tupleset with a computed arm at compile time, so a directs-only tupleset only
  ever gets raw stored edges (a rewrite rule lands edges only on the relation it
  defines). Set engine + oracle accept the schema and agree (stored-only, no
  over-grant). Closed as benign; resolution appended to `docs/spec-deviations.md`
  P5 #3.
- **Symmetric subject-keyed residues** — the engineering hook that would lift
  the two remaining scope rejections (object wildcards on derived relations;
  wildcard usersets over derived relations); `README.md` TODO list.
- README editorial TODOs (unfinished narrative sections) — Avery's voice,
  surgical edits only.

## After W3d (the remaining road)
- **W4 — full-scope restatement. ✅ CLOSED (2026-07-12j).** `ReachedBy` /
  `Drained`, the `GraphAdmission`/`W4Fragment` provenance split, `w4_within_scope`,
  the final unsuffixed T2b/T3/T6 + **T2a `graph_reached_inv`** (`FullScope.lean`),
  W2-subsumption lemmas, non-vacuity witnesses, the T2a fragment-free layers +
  pass-local I6 (`CascadeStrataInv.lean`), and the edge-hygiene ASSEMBLY
  (`CascadeStrataEdge.lean`: `EdgeHyg1` → `reachedByW3d2E_inv`).
- **Phase 6 — hardening. ✅ items 1–3 CLOSED (2026-07-12k).** (a) the graph-state
  conformance mode (`Exec.lean` driver + honesty theorems, zcli `"graph"`,
  `test_conformance_graph.py` hard gate, attack corpora + findings);
  (b) `CORRESPONDENCE.md`; (c) `FINAL_REVIEW.md` (plan §7 verbatim + cross-check).
  **State-level conformance + exhaustive small-scope enumeration ✅ CLOSED
  (2026-07-12m)** — the two formerly-unearned §7 clauses. Remaining extras
  (optional, FINAL_REVIEW §4): fragment widening (the ROOT-operator gap is DONE
  2026-07-17; the LEAF/strata gaps remain), remove legs (the Lean remove leg is
  DONE 2026-07-19f at the validly-stored + drained-prior scope; only the
  Exec-driver end-to-end exercise remains), wider bounds.

Historical detail for every closed stage: `history/PROOF_STATUS.md` (ledger, newest
first) and `history/ROADMAP.md` (designs + post-mortems); the topical synthesis is
`ARCHITECTURE.md`.
