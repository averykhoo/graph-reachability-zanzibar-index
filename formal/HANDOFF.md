# HANDOFF.md — START HERE (the formal-verification entry point)

**A fresh session reads this file top to bottom, then the TOP entry of
`history/PROOF_STATUS.md`** — that is the resume point. This file holds no dated blocks
since 2026-10-07 (`TK131`): the last ones (2026-08-15 … 2026-08-28c) went verbatim to
`history/handoff-retired-2026-10-07.md`. (There is no section called "The next task";
that heading died in an earlier restructure and several docs still cited it until
2026-08-16.) This file carries the formal subtree's *execution* state and its house rules.
It does **not** rank anything: priorities for every open item, `formal/` included, live in
the task tree (`python scripts/task.py board`; [`HANDOFF.md`](../HANDOFF.md) is a one-hop note).
Pull in other docs only on demand:

| doc | what it's for | when to read |
|---|---|---|
| `python scripts/task.py board` (+ [`../HANDOFF.md`](../HANDOFF.md), the one-hop note) | the task tree — what to pick up, and every open item's rank (`show <id>`) | to choose work, or to cite an item by id |
| `ARCHITECTURE.md` | the durable topical map (trust root, models, the theorem tables + scopes, pinning, residual surface) | for "how it all fits together" |
| `FINAL_REVIEW.md` | the exact, clause-checked claim (plan §7 + cross-check), and the only home for live counts | for the precise wording of what is/isn't proved, or any figure |
| `SEMANTICS.md` | the spec / trust root (`sem`, models, theorem statements) | when touching spec-level defs |
| `CORRESPONDENCE.md` | the Lean-def ↔ Python-file:line map | when auditing the model↔code tie |
| `history/PROOF_STATUS.md` | append-only session ledger (newest first) | the TOP entry only, for fine detail on a resume point |
| `history/ROADMAP.md` | per-stage designs + historical plans | the section for a stage's provenance |
| `history/handoff-status-2026-08-16.md` | this file's retired zones, verbatim (the accretion narrative, W3c detail, the old Status section) | for provenance only — never for state |
| `history/handoff-dated-blocks-2026-08-17.md` | this file's retired dated blocks, verbatim (2026-08-14, 2026-08-09, 2026-08-08) | for provenance only — never for state |
| `history/handoff-retired-2026-10-07.md` | this file's blocks retired by `TK131`, verbatim: dated blocks 2026-08-15 … 2026-08-28c, Board `B1`/`B2`, the leg-7 landing and T2a-carry notes | provenance; also the only home of the "five, not four" `Inv`-consumer correction to `history/leaf-family-split-scope-2026-08-05.md` |
| `history/REVIEW.md` | historical one-shot session digest (2026-07-09→10) | never (history) |
| `history/formal-verification-plan.md` | original strategy/phases/honesty clauses | rarely; §7 for claim wording |

**End goal:** a machine-checked proof that the set engine and graph index both compute
the stratified-Datalog¬ perfect model `sem` — hence are equivalent — with the Python
implementations pinned to the Lean models by the conformance harness. The honest claim
never rounds up to "the code is formally verified" (plan §7).

**The caveat every session used to carry is now RETIRED — for T2b on 2026-08-05, for T2a
on 2026-09-23** (`FINAL_REVIEW.md` §3.0, `ARCHITECTURE.md` §6.0). It read: *the final graph theorems
(`graph_correct`, `graph_reached_inv`, `Exec.graphRun_check_eq_sem`, and everything routed
through them) are **VACUOUS — not merely narrow — on any store written through the
`Direct` arm of a derived def**, i.e. on `can_view: [user] but not blocked`, the canonical
Zanzibar boolean shape.*

**E-chain leg 5 (2026-08-05) closed that for T2b and everything routed through it.**
`GraphAdmission.storeValid` is now `StoreValidRulesD` and `W4Fragment` carries five
derived-def clauses in place of `computedOnly`, so `graph_correct` /
`backend_equivalence` / `exclusion_effective` / `no_ghost_grant` /
`Exec.graphRun{,Ops}_check_eq_sem` **apply at that store** —
`W4WitnessDirect.final_applies` instantiates the unsuffixed `graph_correct_public` there
(it was `graph_correct` until the 2026-08-28c public-read migration; same bundles).
`W4WitnessDirect.outside_old_admission` (`¬ StoreValidRules Sd Td`) is KEPT, because it is
now the proof that the widening was contentful rather than a relabeling, and
`w4Fragment_of_computedOnly` proves the pre-leg-5 six fields imply all ten — nothing that
held before stopped holding.

**T2a (`graph_reached_inv`) caught up on 2026-09-23 — `P5`, DONE.** From leg 5 until then
it took a third bundle `W4NarrowT2a` that the Direct-arm store provably failed, so T2a stayed
vacuous exactly where T2b no longer was. That bundle, `outside_narrow_t2a` and
`w4NarrowT2a_of_untainted` are deleted; `graph_reached_inv` now takes `GraphAdmission` ∧
`W4Fragment` only, like every other headline theorem. Leg 7's flip (2026-09-05) had already
removed probe D.3's mechanism; `P5` did the owed proof work, widening the T2a chain
(`CascadeStrataEdge.lean`'s `edgeHyg1_*` → `reachedByW3d2E_inv`, and
`CascadeStrataInv.lean::reconcileStarsKeyDR_row_edge_consistent`) in place to the `_d`
fragment by swapping in the existing `_d` lemmas. Witnesses:
`W4WitnessDirect.reached_inv_applies`/`reached_inv_applies4` (scope — `negEdgeFree` is not
exercised at `Sd`) and `Exec.lean::P5Witness.leafRouted_inv_preflip_not` +
`P5Witness.prefix_facts` (content, at D.3's own store `LeafWitness.Sw`). Map and record:
[`docs/p5-negedgefree-under-leaf-routing-2026-09-23.md`](../docs/p5-negedgefree-under-leaf-routing-2026-09-23.md). What comes next is ranked in the task tree, not here.

Also closed, records only: leg 7 step 5 (`P14`, absorbed 2026-09-23c,
[`docs/p14-reach-collapse-absorbed-2026-09-23.md`](../docs/p14-reach-collapse-absorbed-2026-09-23.md))
and the 2026-08-05 option-(c) leaf-family decision
([`history/leaf-family-split-scope-2026-08-05.md`](history/leaf-family-split-scope-2026-08-05.md),
landed 2026-09-05). Their blocks are in `history/handoff-retired-2026-10-07.md`.

Standing formal traps whose blocks were retired 2026-10-07. Each has a gated home, so read it there:
* `graphModeAnswers_eq_sem` must stay in `formal/conformance/statement_pin.py::HEADLINE`, or
  the driver's read is un-pinned (its comment there; `CORRESPONDENCE.md`'s `Exec.lean::graphRun` row).
* Only `FullScope.lean::W4WitnessDirect.fence_changes_answer` catches a fence REMOVAL
  (`CORRESPONDENCE.md`'s `GraphModel.checkPublic` row).
* The binary `Expr` is faithful to the FLAT n-ary union only (`CORRESPONDENCE.md` §7.2;
  refused at `test_conformance_state.py::test_no_corpus_nests_a_pure_union_inside_an_impure_one`).
* `String.contains` does not kernel-reduce: leaf-layer defs stay `toList`-based
  (`GraphIndex/Leaf.lean::isLeafPred`'s docstring).
* Retiring an id is not the same act as closing a finding. If you retire one, say in
  the same edit whether the finding died with it (the `B1` lesson, 2026-08-16).

## House rules (non-negotiable, user-adjudicated)

The SHARED doc conventions — liveness states, the frozen banner, citation keys, the
priority vocabulary — live in [`docs/README.md`](../docs/README.md); the numbered rules
below stay authoritative for the `formal/` subtree and are cited BY NUMBER, so the
numbering is byte-stable and this pointer is deliberately unnumbered.

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
   **No counts here, deliberately.** This bullet carried four of them (457 audits, 139
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
   `GraphAdmission` BUILDS, keeps every pinned statement byte-identical, changes no
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


## Status — what is proved, and what is in flight

No figures here, deliberately (house rule 3): live counts are in `FINAL_REVIEW.md`'s
generated block, gated by `verify.sh` step 4e. This section states execution state only;
ranking lives in the task tree (`task.py board`).

**Closed.** The W1 → W4 staged widening and Phase 6 are done: T1, T2a, T2b, T3 and T6 hold
over `ReachedBy` at the W4 scope, sorry-free and axiom-clean, with the Python side pinned by
the conformance harness (answer level, state level, exhaustive small-scope enumeration, the
remove-path and generated-schema gates). The Lean remove leg is closed at the validly-stored
+ drained-prior scope and is driven end-to-end. The staged ladder that got there is a table
in `ARCHITECTURE.md`; the narrative is `history/PROOF_STATUS.md`.

**Leg 7, the leaf-family split, landed 2026-09-05** (`P3`, `P4`, `P5`, `P14`; nothing owed on
the flip itself): both logged legs fold the leaf-routed closure, and projection P6 is retired.
Its residue is `CORRESPONDENCE.md` §7.2 item 6. Record: `history/PROOF_STATUS.md` 2026-09-05b.
The status note is in `history/handoff-retired-2026-10-07.md`.

**In flight — `ttuStarFree` (tree rows `P6`, `P7`).** Part (i) landed and is inert. ⚠ **NOT
optional:** without the clause `graph_correct`/`backend_equivalence` are machine-checked FALSE
(2026-08-10 kill); `W4Fragment.ttuStarFree` stays unchanged until (ii) is in; Python does not
enforce it either (2026-08-31b: `folder:* parent doc:d1` on a TTU tupleset **ADMITTED**).
⚠ **The 2026-09-12 framing here is RETIRED (2026-09-14f)** — all three clauses superseded, nothing blocked on the user. **(iv) is OPEN and sized**: map, cone and step order in
[`docs/p6-part-iv-plan-2026-09-14.md`](../docs/p6-part-iv-plan-2026-09-14.md) (ACTIVE-PLAN — read its dated corrections first).
⚠ **The flip is not a type edit; both closure theorems are machine-refuted under `TtuStarFreeW`** (`formal/probes/p6_partiv_{closure_star,live_leg_payoff}_2026-09-14.lean`). ⚠ **2026-09-15 — it is a WRITE-MODEL change, not a proof sweep.** `RulesBareStar.lean::graph_correct_rulesBS` is **FALSE** under the widening (`sem` true / `check` false, every other hypothesis incl. `FoldAdmits` checked), and the W4 route to it is severed higher: `CascadeStable.lean::ShadowOver.term` demands a bridge node be TERMINAL and the widening sources an edge at it — `∀ σ0, ¬ UntaintedShadow …` is now a `decide` theorem, controlled at a concrete parent.
The bridged `LeafRules.lean::writeRulesRaw` answers CORRECTLY on the same store, so the repair is to bridge the SHADOW (`CascadeStable.lean:3735`). Probe + controls: `formal/probes/p6_partiv_step3_rulerouted_2026-09-15.lean`; re-plan (R1 of four taken, R4 refuted): the plan doc's `(eighth)` correction.

**Scope honesty — the `W4Fragment` field classification (2026-08-31b).** `graph_correct`'s
scope is exactly `W4Fragment`, and its ten fields now carry a gated, hand-maintained
classification against Python enforcement:
`formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE`. Measured **LOUD 0 ·
MIXED 3 · SILENT 7** — for seven fields a schema outside the proven fragment is accepted,
runs and answers queries, with its correctness resting on the differential net rather than
on `graph_correct`. ⚠ **Do not argue a future scope narrowing from "Python refuses the
difference" without re-establishing it for that field** — it currently holds for none of the
ten, and the one narrowing accepted on that ground (`P20`) is the exception. Closing the
seven is repo board row `DW-1`; making the classification measured rather than argued needs
a fourth `zcli` mode, row `P21`.
**2026-09-23d:** `W4Fragment` is now DECIDED (`GraphIndex/FragmentDecide.lean::w4FragmentB_iff`, exact in both directions), and `zcli mode="fragment"` reports the verdict per field. `test_conformance_fragment.py` machine-checks the `W4Fragment` half of every `_THEOREM_BACKED` corpus, which was prose before. The Python side is still SILENT: the production mirror plus its differential is `DW-1` step 3 (`docs/dw1-decidable-w4fragment-2026-09-23.md`).
**2026-09-25 (`TK104`):** `GraphAdmission` is DECIDED too (`GraphIndex/AdmissionDecide.lean::graphAdmissionB_iff`), and so is the whole headline premise (`headlinePremiseB_iff`). `RewriteRanked`, the one existential field, is decided by a canonical longest-walk rank (`rankCheck_rkF_iff`). `zcli mode="fragment"` emits `"admission"` and `"inPremise"`; the Python report of the two SILENT fields is `src/zanzibar/schema/reports.py::graph_admission_report`. Map: `docs/tk104-graphadmission-scope-2026-09-24.md`.

**The T2a scope carry closed 2026-09-23 (`P5`)** (see the T2a note at the top), and `P4`
closed 2026-10-03d (`GraphIndex/LeafBridge.lean::leaf_probe_bridge`). Their status notes are in
`history/handoff-retired-2026-10-07.md`.

**Optional assurance-widening** is inventoried and ranked in `FINAL_REVIEW.md` §4, and every
item still open there now carries a task (`P15`–`P19`, plus `P9` and `SD-1`). That
section is the home for the argument; the task tree is the home for the rank.

Historical detail for every closed stage: `history/PROOF_STATUS.md` (ledger, newest first)
and `history/ROADMAP.md` (designs + post-mortems); the topical synthesis is
`ARCHITECTURE.md`; this file's own retired zones are `history/handoff-status-2026-08-16.md`,
`history/handoff-dated-blocks-2026-08-17.md` and `history/handoff-retired-2026-10-07.md`.
