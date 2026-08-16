# HANDOFF.md — START HERE (the formal-verification entry point)

**A fresh session reads this file top to bottom, then goes straight to the dated blocks
below** — the newest one is the resume point. (There is no section called "The next task";
that heading died in an earlier restructure and several docs still cited it until
2026-08-16.) This file carries the formal subtree's *execution* state and its house rules.
It does **not** rank anything: priorities for every open item, `formal/` included, live on
the repo board [`HANDOFF.md`](../HANDOFF.md), and formal items are cited there by row id.
Pull in other docs only on demand:

| doc | what it's for | when to read |
|---|---|---|
| [`../HANDOFF.md`](../HANDOFF.md) | the repo priority board — what to pick up, and every open item's rank | to choose work, or to cite an item by id |
| `ARCHITECTURE.md` | the durable topical map (trust root, models, the theorem tables + scopes, pinning, residual surface) | for "how it all fits together" |
| `FINAL_REVIEW.md` | the exact, clause-checked claim (plan §7 + cross-check), and the only home for live counts | for the precise wording of what is/isn't proved, or any figure |
| `SEMANTICS.md` | the spec / trust root (`sem`, models, theorem statements) | when touching spec-level defs |
| `CORRESPONDENCE.md` | the Lean-def ↔ Python-file:line map | when auditing the model↔code tie |
| `history/PROOF_STATUS.md` | append-only session ledger (newest first) | the TOP entry only, for fine detail on a resume point |
| `history/ROADMAP.md` | per-stage designs + historical plans | the section for a stage's provenance |
| `history/handoff-status-2026-08-16.md` | this file's retired zones, verbatim (the accretion narrative, W3c detail, the old Status section) | for provenance only — never for state |
| `history/REVIEW.md` | historical one-shot session digest (2026-07-09→10) | never (history) |
| `history/formal-verification-plan.md` | original strategy/phases/honesty clauses | rarely; §7 for claim wording |

**End goal:** a machine-checked proof that the set engine and graph index both compute
the stratified-Datalog¬ perfect model `sem` — hence are equivalent — with the Python
implementations pinned to the Lean models by the conformance harness. The honest claim
never rounds up to "the code is formally verified" (plan §7).

**The caveat every session used to carry is now HALF RETIRED — carry the correct half**
(`FINAL_REVIEW.md` §3.0, `ARCHITECTURE.md` §6.0). It read: *the final graph theorems
(`graph_correct`, `graph_reached_inv`, `Exec.graphRun_check_eq_sem`, and everything routed
through them) are **VACUOUS — not merely narrow — on any store written through the
`Direct` arm of a derived def**, i.e. on `can_view: [user] but not blocked`, the canonical
Zanzibar boolean shape.*

**E-chain leg 5 (2026-08-05) closed that for T2b and everything routed through it.**
`GraphAdmission.storeValid` is now `StoreValidRulesD` and `W4Fragment` carries five
derived-def clauses in place of `computedOnly`, so `graph_correct` /
`backend_equivalence` / `exclusion_effective` / `no_ghost_grant` /
`Exec.graphRun{,Ops}_check_eq_sem` **apply at that store** —
`W4WitnessDirect.final_applies` instantiates the unsuffixed `graph_correct` there.
`W4WitnessDirect.outside_old_admission` (`¬ StoreValidRules Sd Td`) is KEPT, because it is
now the proof that the widening was contentful rather than a relabeling, and
`w4Fragment_of_computedOnly` proves the pre-leg-5 six fields imply all ten — nothing that
held before stopped holding.

**⚠ T2a (`graph_reached_inv`) did NOT widen, and this is the half to keep carrying.** It
now takes a third bundle `W4NarrowT2a` (schema-wide `ComputedOnly` + the narrow
`StoreValidRules`), and `W4WitnessDirect.outside_narrow_t2a` machine-checks that the
Direct-arm store fails it — so T2a **remains vacuous exactly where T2b no longer is.**
That is not a proof gap: Leg-0 probe D.3 machine-checked `Inv.negEdgeFree` FALSE on the
`_d` fragment. **Python is fine** (`RuleSet.apply` routes the write onto the leaf family,
so the edge and the `neg` row live on different nodes — 0 mismatches on the real backends);
it is a modelling limit of the P6 leaf-family collapse.

**The design decision that was owed here is now MADE (2026-08-05): option (c) — model
the leaf-family split and retire P6 — and the work is DEFERRED, not scheduled.** (a)
"restate at drained states only" and (b) "weaken `negEdgeFree`" both shrink
the claim; (c) is the only one that raises assurance. The decisive finding: **nothing
consumes `Inv`** — it is a hypothesis in exactly four places (`State.lean:813`, `:854`,
`Write.lean:150`, `RulesWrite.lean:181`), all `Inv → Inv` preservation steps, and
`EdgeHygienic` is consumed nowhere — so weakening `negEdgeFree` could not turn anything
red, which is precisely the house failure mode (rule 7). There is also precedent pointing
away from (b): when `negEdgeFree` was found FALSE over plain `ReachedByW3d` on 2026-07-11j
(`CascadeInv.lean:14-27`), the answer was to scope the theorem to the coverage chain, not
to weaken the invariant.
**Scope, blast radius (55–65% of the tree; `Spec/`/`SetEngine/` entirely spared) and a
step ordering:**
[`history/leaf-family-split-scope-2026-08-05.md`](history/leaf-family-split-scope-2026-08-05.md).
**Until it runs, the T2a half of the vacuity caveat stays** — carry it as written above.

**2026-08-16 — LEG 7 STEP 4c-i IS IN (`GraphIndex/LeafRules.lean`), the ALLOCATION was
refuted THREE more times first, and `ttuStarFree` part (iv)'s BLOCKING QUESTION IS
ANSWERED: NO-BLOCK. Read `history/PROOF_STATUS.md` 2026-08-16 and scope-doc §11.7 FIRST.**

* **4c-i landed with a ZERO recompile cone, and §11.6's cost cell is REFUTED.** It sized
  4c-i as "the full GraphIndex tree, ~double the Cascade cone" — true only of an *edit* to
  `schemaRewrites`. As an EXTENSION downstream of `RulesWrite` the cone is **one file**,
  and the `Cascade → LeafRules` import 4c-ii needs is cycle-free. **Budget the cone once,
  at 4c-ii.** `leafRewrites` supplies the half `schemaRewrites`' taint filter omits: each
  derived key's CLOSURE leaves compile to rules targeting the MINTED LEAF NAME. Additivity
  is *proved* (`schemaRewrites_leafRewrites_disjoint`), not observed. Measured 50/50
  schemas / 32 non-empty rule sets against `compile_ruleset`'s real output.
* **⚠ THE ALLOCATION WAS WRONG THREE MORE TIMES**, all caught before 4c-i was built on it:
  Python MERGES a maximal pure subtree (`(a or b) but not banned` → `r.0={a,b}`,
  `r.1=banned`, not three leaves, storage always first); a tainted userset restriction gets
  its OWN storage leaf (reachable from the live fixture `userset_over_derived.fga`); and —
  **invisibly to the instrument that validated the first two** — the n-ary union SPINE.
* **THE METHOD LESSON, now in [`docs/sabotage-procedure.md`](../docs/sabotage-procedure.md).**
  The first two fixes were validated by transcribing `persistedLeaves` into Python: *"82/82,
  0 disagreements"*. That transcription consumed Python's **n-ary** AST; Lean never sees it
  (`encode.py::_fold_binary` LEFT-FOLDS). Re-run binarized: 1 disagreement, on
  `nary_union_derived4`, **which is in `GRAPH_FRAGMENT`**. *A transcription of the right
  rule over the wrong input REPRESENTATION is the mirror instrument with extra steps* — and
  the second, genuinely independent instrument (744/744) was structurally incapable of
  catching it.
* **⚠ A LIMIT OF THE BINARY `Expr` LEG 7 MUST CARRY.** `Core/Schema.lean` justifies
  left-folding n-ary unions by associativity+commutativity — true of `sem`, **false of the
  leaf ALLOCATION**. Measured: `a or b or safe` → 2 leaves, `(a or b) or safe` → **1**, and
  `_fold_binary` maps both to the SAME `Expr`. The model is faithful to the FLAT form; the
  other shape is refused mechanically at
  `formal/conformance/test_conformance_state.py::test_no_corpus_nests_a_pure_union_inside_an_impure_one`.
  Making it faithful to both means an n-ary `Expr` — a trust-root change, out of scope.
* **`ttuStarFree` PART (iv) IS UNBLOCKED.** `GraphIndex/TtuStarWide.lean` answers the
  standing question with a theorem: `TtuStarFree` is a bounded quantification over finite
  lists, the widening only weakens the BODY, and the new conjunct
  `Schema.isSubjectWildcardUserset` is **already `Bool`-valued** — so `ttuStarFreeWB`
  decides `TtuStarFreeW` and `removeGateB` widens by the same textual edit
  (`removeGateBW_gate`). Proved a genuine weakening AND strictly wider at a store.
  ⚠ `W4Fragment.ttuStarFree` is UNCHANGED and must stay so until part (ii).
* Audits 520 → **573**, anchors 471 → **497**, statements 38/38 and definitions 155/155
  UNMOVED. Re-measured: *"17 of 25 corpora mint indices 1 AND 2"* overstates the index-2
  breadth 3.4× — index ≥1 in 17, index 2 in **5**.

**2026-08-15 — LEG 7 4c-PRE: 4c-as-scoped REFUTED by corpus measurement; the leaf
ALLOCATION is modeled, `publicOfLeaf` is in (index-agnostic), the raw write is a measured
FAN-OUT. Read `history/PROOF_STATUS.md` 2026-08-15 and scope-doc §11.6 (the revised step
plan) BEFORE attempting 4c.** ⚠ **Its allocation half is SUPERSEDED by the 2026-08-16 block
above; §11.6's cone estimate is refuted and its index-breadth figure is stale.**

* **The kill, made before the cone was paid:** the 76 P6-dropped rows span leaf indices
  0–2 in **17 of 25** corpora (every non-first boolean arm gets its own leaf), so the
  2026-08-14 `rawWriteRel`-index-0 model could never meet `P6 → 0 / compared → 265` —
  and a raw write **fans out** to every matching storage leaf, so it was wrong in arity
  too. Both facts are now Lean pins (`LeafWitness.swU_routes`, `swF_fanout`).
* **`Leaf.lean` is reworked while still unwired**: `persistedLeaves` (the pre-order
  allocation — derived refs and non-pure TTU arms consume NO index),
  `leafPublic`/`publicOfLeaf` (dot-free prefix, never `".0"`; `publicOfLeaf_rawWriteRels`
  is the (α) feeder for `affectedKeys`), `rawWriteRels`/`rawWriteTuples`/`writeDirectRaw`
  (the filtered fan-out). Five sabotages, each red attributable, controls green. Audits
  501 → **520**; headline statements/definitions UNMOVED.
* **4c is NOT a caller re-point.** The dropped rows are mostly RULE-copied closure
  leaves and the index depends on WHICH ARM produced the copy — provenance
  `rewriteClosure` does not carry (shape-identical members route to `viewer.0` vs
  `viewer.1`). The rule layer must mint leaf-indexed targets for tainted keys (Python
  bakes them into `RewriteFilter.rewrite_relation`). Revised order: **4c-i** rules with
  leaf provenance (under `RulesWrite`, cone ≈ the whole GraphIndex tree) → **4c-ii**
  caller re-point + (α) row move (`d.leaf = true` stays the LEADING conjunct;
  `foldAdmitsB`/`FoldAdmits` move in lockstep) → 4b/5/6/7; 4c-ii + 7 still co-land.
* Toolchain: `String.contains` does not kernel-reduce — leaf-layer defs stay
  `toList`-based or `decide` pins stall.

**2026-08-14 — THE §11.3 FORK IS DECIDED: branch (α). `ttuStarFree` PART (i) IS IN.**
Read `history/PROOF_STATUS.md` 2026-08-14 and scope-doc **§11.5** (appended; §11.3 is left
as written and is wrong in two places).

* **(α) — the `Delta` row moves to the leaf node.** Python's outbox row IS keyed at the leaf
  (`index_v4/models.py::DeltaOutboxV1` has no relation column; the relation is the object
  node's predicate), and `index_v4/processor.py::DeltaProcessor._map_deltas_to_keys`
  recovers the public name from the compiled `LeafFamily` table. The Lean probe did not
  refute (α); its control — the half-done (α), row moved with `affectedKeys` untouched —
  produced the **empty** cascade key set, so the instrument is real.
* **⚠ `publicOfLeaf` MUST BE INDEX-AGNOSTIC.** §11.3's prescribed "string surgery on the
  `.i` suffix" is measurably wrong: Python routes `(viewer but not banned) or [user]` to
  `approver.2`, where a `".0"`-stripper returns `none`. `Leaf.lean::rawWriteRel`'s
  hardcoded index `0` is therefore a known-wrong model, not merely unmeasured.
* **`writeLoggedOne` does NOT need an `S` parameter** — `GraphState.schema` already
  exists and a `σ.schema`-reading variant is definitionally equal under `σ.schema = S`.
  That removes ~145 mention-lines from the budget (61 + 84 re-measured, not §11.3's 58),
  at the price of a per-site schema hypothesis.
* **⚠ 4c CANNOT LAND ALONE — it must co-land with step 7.** P6 is a Python-side-only
  filter (`formal/conformance/extractor.py::_edge_projection`), so the moment 4c re-points
  `Exec.lean` the state gate reports ~76 leaf edges "only in LEAN model". Scope doc §7's
  "each step green and pushable" is refuted at 4c.
* **Live landing criterion** (re-derive from `FINAL_REVIEW.md`'s generated block, never from
  prose): **`dropped by P6` → 0 and `compared against Lean` → 265** (today 76 and 189).
* **`ttuStarFree` part (i) LANDED**: `Schema.isStarTuplesetThrough` + the widened
  `Schema.isSubjectWildcardUserset` = both loops of `derive_schema_info`, as Python.
  ⚠ **INERT on every live chain** — `writeRules`/`writeLoggedRules` never call
  `ensureInBridges`, so part (ii) is what materializes the edge. Do NOT read part (i) as
  closing the 2026-08-10 counterexample. Six `decide` pins carry it because, being inert,
  the obvious sabotage reddens nothing else in the tree.
* **Still owed** ⚠ **— SUPERSEDED TWICE; read the 2026-08-16 block at the top.** "Step 4c"
  as named here does not exist any more (it is 4c-i + 4c-ii), **4c-i is DONE**, and part
  (iv)'s blocking question is **ANSWERED: NO-BLOCK** (`GraphIndex/TtuStarWide.lean`) — do
  not defer (iv) on decidability again. Genuinely still owed: leg 7 **4c-ii + 7 (co-land)**,
  4b, 5, 6; `ttuStarFree` parts (ii) and (iii), and (iv)'s remaining effort. Occurrence
  split re-measured: **163 in 18 modules**, only **5 genuinely CONSUMED**.

**⚠ 2026-08-10 — ATTACK-FIRST KILL: `W4Fragment.ttuStarFree` CANNOT BE DROPPED.**
The user asked to undo it as a mere scope cut. It is not one: dropping it makes
`graph_correct` and `backend_equivalence` **FALSE**, machine-checked sorry-free and
axiom-clean (`W4FragmentNoTS` = `W4Fragment` minus the one clause; `ReachedBy` from the
tree's own `graphRun_reached`, never hand-assembled; 120 comparisons, control a
one-character delta `folder:*` → `folder:f1`).
**The predicted mechanism was REFUTED and the conclusion still holds** — the
counterexample uses **no object wildcard**, so this is not the I14 bug; `bareStar` keeps
that shape out of scope anyway. The real gap is one layer earlier: Lean's W1c **in-bridge**
has no star-tupleset **through-shape** notion (`UsStarWrite.lean:71`), and
`writeRules`/`writeLoggedRules` materialise **no bridges at all**. Python handles the shape
correctly; Lean's `ensureInBridges` on it is a literal no-op (`edges 3 → 3`).
Lifting it is a **four-part leg** (through-shape derivation; bridges on the rule-routed
write path; re-proving `ttuLeaf_elim_nss` + `StarSeed`, which exist BECAUSE of the clause;
the remove leg) across **162 occurrences in 18 modules**. Not blocking. Detail:
`history/PROOF_STATUS.md` 2026-08-10.

**LANDED 2026-08-09 — LEG 7 IS UNDER WAY: steps 3 and 4a are in
(`8291c3a`, `41b7029`), and the scope doc is now right in one place and wrong in another.**
`GraphIndex/Leaf.lean` carries leaf addressing (`leafPred`/`isLeafPred`/`leafNode`), the
raw-write routing (`rawWriteRel`/`rawWriteNode`/`rawWriteTuple`), the forked write
`writeDirectRaw`, and the distinctness linchpin `leafPred_ne_relName`. Additive: audits
481 → 493, headline statements 38/38 and definition pin 155/155 **unmoved**.
* **§3's bet HELD** — no new sentinel axiom; `relNameOK` gives leaf-vs-bare distinctness
  for free, and `relNameOK_of_isDerived` derives declaredness from `isDerived`.
* **§4's prescription is REFUTED. Do not fork `writeDirect`; fork the TUPLE.** Python
  does not fork its write path — `RuleSet.apply` re-addresses the triple
  (`zanzibar_utils_v1.py:447`) and the ordinary write runs. So `writeDirect` stays
  byte-identical and §4's predicted duplication of the projection and fold lemmas is not
  owed at all.
* **WHERE IT STOPPED, and it is a design fork the scope doc does not contain**
  (`history/leaf-family-split-scope-2026-08-05.md` §11.3): once the EDGE moves to the leaf
  node, `writeLoggedOne`'s `pushDelta` is a separate unforced choice — move the row too
  (faithful to Python's outbox, but `affectedKeys` then needs a leaf → public map the model
  has no analogue of) or keep it public (cheap, less faithful, a declared carry). **The
  `Delta.leaf` tag does NOT answer this** — it says which leg wrote the row, not which node
  the row is keyed at. Attack-first this before coding either branch.
* Step-4c sizing was walked four modules deep and is far cheaper than §5's 55–65% suggests
  — but the counts are per-module FRONTIERS (`lake build` skips dependents of a failing
  module), so §5 is neither confirmed nor refuted. Detail: `history/PROOF_STATUS.md`
  2026-08-09 and scope doc §11.

**LANDED 2026-08-08 — THE `rewriteClosure` DEDUP LEG (`CORRESPONDENCE.md` §7.2 item 6,
CLOSED).** The model's `rewriteClosure` did not deduplicate where `RuleSet.apply` does, so
on a *reconvergent* schema it counted DERIVATION PATHS where Python counts LIVE RAW TUPLES
(`lean=2 python=1`, growing `1 → 2 → 4` with the number of chained diamonds — with SCHEMA
SHAPE, not store content). It is now `(rewriteClosureRaw S t).dedup`, per stored tuple,
bridged by `mem_rewriteClosure_iff`. Two corpora (`reconvergent_diamond`,
`reconvergent_derived`) landed FIRST in a deliberately-red commit so the divergence was
attributable. The decisive argument was **house rule 5**: `RemoveOccCount.lean`'s header
*asserted Python's unit* and was false on any reconvergent schema, while the same file's
attack bullet said so — the file contradicted itself and R3/R4's faithfulness claim rested
on the wrong half. Sizing held: the count stack is list-generic, so `untOccCount`/R3/R4
needed **zero** proof rework. **Two things nobody predicted:** the over-count cost
RUNTIME (a zcli remove-stream timeout that the fix resolves), and the sabotage exposed a
LIMITATION rather than a confirmation — the new corpora do *not* catch the wrong (global)
dedup, `nary_union` does; they guard opposite errors. Detail:
`history/PROOF_STATUS.md` 2026-08-08b.

---

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

---


## Board — the two ORPHANED findings, adjudicated 2026-07-27 (ZT-P4 item 4)

Both lived only in `history/` and had reached no board. Each was re-verified
against the working tree (commands quoted). **Paste-ready paragraphs for the root
board are the two blocks below, verbatim.**

### B1 — `w3cJobValid_enumJob2D` star-freeness hole · verdict: **CLOSED 2026-08-16** (proved 2026-07-28/08-04; the record simply never caught up)

> **Closed, both halves, and machine-checked.** The 2026-07-27 verdict below said the
> finding needed "a decision, not a proof session": choose between a star-filter inside
> `storedDirectSubjects` and a new fragment clause banning wildcard restrictions on derived
> Direct arms. The E-chain plan §B took **both**, the next day, and they landed:
>
> * **The `storedDirectSubjects` half** — closed unconditionally by the faithfulness
>   star-filter (`CascadeStrataEnum.lean::storedDirectSubjects`, mirroring
>   `index_v4/processor.py`'s `_incoming_concretes` wildcard filter), giving
>   `storedDirectSubjects_name_ne_star` with no fragment premise at all.
> * **The `edgeHolders` half** — discharged at the call sites by
>   `CascadeStrataSettle.lean::reachedByW3d2_Rnode_source_name_ne_star_d`, under the new
>   `W4Fragment` clause `directArmsConcrete`.
>
> Both feed `CascadeStrataAssemble.lean::w3cJobValid_enumJob2D`, which is audited and
> axiom-clean, and reach the final theorems through `enumJobs2At_valid` (four call sites in
> `CascadeStrataAssemble` and `CascadeStrataEdge`) and `FullScope.lean`'s
> `W4Fragment.directArmsConcrete`. So clause (ii) of the old verdict — *"the lemma does not
> exist, so no landed theorem depends on it"* — is now false in both of its parts.
>
> **Sabotage, 2026-08-16** (`docs/sabotage-procedure.md`): the star-filter was defeated in
> place (`fun s => s.name != STAR` to `fun _ => true`) and `lake build` of
> `ZanzibarProofs.GraphIndex.CascadeStrataEnum` went red at
> `CascadeStrataEnum.lean:634` — the `simpa` closing `storedDirectSubjects_name_ne_star`.
> So this half is held by the type checker, not by measurement. Restored and re-verified.
> ⚠ Do not confuse that filter with the `freshDirectCands` presence diff a few lines away:
> **that one IS measurement-pinned** and the tree compiles with it defeated, which is why
> its docstring carries a conformance-ledger observation instead of a proof.
>
> **The honest carry that came with the fix, unchanged:** `directArmsConcrete` excludes a
> shape Python admits — `define approver: [user, user:*] but not banned` compiles and all
> three backends agree on it. It is a **vacuity** boundary, not an unsoundness one: on such
> a schema `W3cJobValid` fails for every enumerated job at the key, so the operational chain
> has no cascade constructor there. The paragraph stating this lives at
> `FullScope.lean::W4Fragment`, and the clause is machine-confirmed load-bearing — a
> 262-run driver sweep saw 824 in-edges at derived R-nodes with none STAR-sourced, and with
> the clause dropped 122 stores produce one.
>
> **Why it stayed open on paper for three weeks:** the verdict was written 2026-07-27, the
> fix landed 2026-07-28 and 2026-08-04, and nothing connected them. `Audit.lean` said "the
> `storedDirectSubjects` half of the Board-B1 star-freeness hole is closed" the whole time.
> The repo board retired the id; this file kept the open verdict. That gap is the argument
> for the rule that a finding is closed where it is RECORDED, not where it is fixed.


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


### Note 2026-08-16 — the `B1` board disagreement, resolved

Earlier the same day this file still verdicted `B1` open while the repo board had retired
the id, and that gap was recorded here as an open question. It is now answered: the finding
really is closed, the evidence is in the `B1` block above, and both boards agree. The
mechanism that produced the gap is worth keeping, though — **retiring an id is not the same
act as closing a finding**, and for three weeks nothing in the tree distinguished them. If
you retire an id, say in the same edit whether the finding died with it.

---

## Status — what is proved, and what is in flight

No figures here, deliberately (house rule 3): live counts are in `FINAL_REVIEW.md`'s
generated block, gated by `verify.sh` step 4e. This section states execution state only;
ranking lives on the repo board.

**Closed.** The W1 → W4 staged widening and Phase 6 are done: T1, T2a, T2b, T3 and T6 hold
over `ReachedBy` at the W4 scope, sorry-free and axiom-clean, with the Python side pinned by
the conformance harness (answer level, state level, exhaustive small-scope enumeration, the
remove-path and generated-schema gates). The Lean remove leg is closed at the validly-stored
+ drained-prior scope and is driven end-to-end. The staged ladder that got there is a table
in `ARCHITECTURE.md`; the narrative is `history/PROOF_STATUS.md`.

**In flight — leg 7, the leaf-family split (repo board rows `P3`, `P4`, `P5`, `P14`).**
Steps 3, 4a, 4c-pre and 4c-i have landed. Owed: 4c-ii co-landing with step 7, then 4b, 5
and 6. Read the dated blocks at the top of this file and the scope doc before starting.

**In flight — `ttuStarFree` (repo board rows `P6`, `P7`).** Part (i) landed and is inert;
part (ii) is what materialises the edge; (iii) and (iv) follow.
⚠ **This is NOT an optional widening.** Without the `ttuStarFree` clause, `graph_correct`
and `backend_equivalence` are machine-checked FALSE, not merely unproven — the 2026-08-10
attack-first kill. `W4Fragment.ttuStarFree` must stay unchanged until part (ii) is in.

**The one live scope carry.** T2a (`graph_reached_inv`) did not widen with T2b: it takes the
extra `W4NarrowT2a` bundle, and a Direct-arm store provably fails it, so T2a stays vacuous
exactly where T2b (since 2026-08-05) no longer is. This is a modelling limit of the P6
leaf-family collapse, not a Python bug — `RuleSet.apply` routes the write onto the leaf
family, and the real backends show no mismatch. Retiring the carry is what leg 7 is for.

**Optional assurance-widening** is inventoried and ranked in `FINAL_REVIEW.md` §4, and every
item still open there now carries a repo-board row (`P15`–`P19`, plus `P9` and `SD-1`). That
section is the home for the argument; the board is the home for the rank.

Historical detail for every closed stage: `history/PROOF_STATUS.md` (ledger, newest first)
and `history/ROADMAP.md` (designs + post-mortems); the topical synthesis is
`ARCHITECTURE.md`; this file's own retired zones are `history/handoff-status-2026-08-16.md`.
