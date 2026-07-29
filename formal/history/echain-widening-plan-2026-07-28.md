# E-chain Direct-arm widening — the landable leg plan (scoped 2026-07-28)

**What this is.** The durable scoping document for board item **(B)** / `ZT-P3-1`: the
E-chain Direct-arm widening, which is the fix for the fact that `graph_correct`,
`graph_reached_inv` and `Exec.graphRun_check_eq_sem` are **VACUOUS** on
`can_view: [user] but not blocked` — the canonical Zanzibar boolean shape.
`FullScope.lean::W4WitnessDirect.outside_old_admission` machine-checks that such a store
fails `GraphAdmission.storeValid` (= `StoreValidRules`), so the headline theorems hold
there trivially. **That is no theorem, not a narrow one.**

This file supersedes the 4-step "assessed fork cost" in
[`optional-widening-2026-07.md`](optional-widening-2026-07.md) §"Direct-arm — RESUME
(2026-07-20e)". That list is not wrong so much as **materially incomplete** — see §E.
Read this file to resume; read the older one for the provenance of the landed `_d` chain.

**Status: SCOPED + Leg 0 (attack sweep) DONE. No Lean declaration changed.** §A–§C below are
read-only analysis of the working tree at `e753a65`; §D carries the **executed** Leg-0 probe
results (2 KILLS), also recorded in [`PROOF_STATUS.md`](PROOF_STATUS.md).

**The three Leg-0 outcomes that change this plan:**
1. **T2a (`graph_reached_inv`) is OUT of the arc** — `Inv.negEdgeFree` is machine-checked FALSE
   on the `_d` fragment (§D.3). A design decision is owed before leg 7 is scheduled at all.
2. **`enum2BaseD` must dedupe** before the coverage leg, or the widened model's edge multiset
   grows `n ↦ 2n+1` per leg (§D.1).
3. **A pre-existing, undocumented model↔Python divergence surfaced en route:** the BASELINE
   enumeration already doubles derived-edge multiplicity per cascade leg, and the state gate is
   structurally blind to it (P3 compares edges as a set). **Independent of this arc; needs its
   own adjudication.** — **ADJUDICATED 2026-07-29** (`CORRESPONDENCE.md` §7.2): real,
   model-side, confined to the derived arm, removal-inert. The gate hole is closed and
   **§D.6 is now automatic** — see the D.6 row below before running Leg 2.

---

## 0. The three things the old plan does not record

1. **The star-freeness hole is bigger than recorded, and that flips the step-2 decision.**
   Under `StoreValidRulesD` a wildcard-flagged restriction on a derived `Direct` arm
   admits a stored `user:*` tuple whose write lands an in-edge **at the derived R-node
   itself**. That poisons `edgeHolders` (`CascadeEnum.lean::edgeHolders`) — a component of
   `enumJob2`'s candidates that has nothing to do with `storedDirectSubjects`. So the old
   file's preferred fix (a star-filter inside `storedDirectSubjects`) closes **one of two**
   holes. ⇒ take the **fragment-clause** option, and *also* add the star-filter as
   faithfulness. See §B.
2. **T2a (`graph_reached_inv`) is very likely NOT widenable together with T2b, and the old
   plan does not mention T2a at all.** See §D.3 — this is the single biggest omission in
   the assessed fork cost, and the expected honest end state is **T2b widened, T2a not**.
3. **Step 1 carries a de-duplication obligation nobody wrote down.**
   `enum2BaseD = enum2Base ++ storedDirectSubjects` does not dedupe, `admitEdge` does not
   reject an already-present edge, and Python *does* dedupe by node id
   (`processor.py` `candidates`/`audit` are `dict[int, NodeV4]`). **The state gate cannot
   see this** — `extractor.py` projection P3 compares edges as a SET. See §D.1.

Net: landable, but as **7 legs across ≥3 sessions**, not 4 steps.

---

## A. Ground truth on the ripple

### A.1 `enumJobs2At` takes no `Store` — so step 1 is a SIGNATURE change

`CascadeStrataAssemble.lean::enumJobs2At` is `(S) (σe) (keys)`. `enumJob2D` needs a
`Store`. So the change propagates into `enumJobs2R1`/`enumJobs2R2` (the latter uses the
former in its body) and into `ReachedByW3d2E.cascade`'s target term.

Consumers (grep-verified whole tree): `enumJobs2At` + `_cover` / `_scope` / `_valid`
(content — routes to a new `w3cJobValid_enumJob2D`) / `_keyFacts` / `_negCands_subset` /
`_Rnode_ne`; `enumJobs2R1`; `enumJobs2R2`; `ReachedByW3d2E`; `reachedByW3d2E_toC`;
`w3cJobValid_enumJob2`; `enumJob2_negCands_subset`; `reachedByW3d2E_edgeHyg1`;
`reachedByW3d2E_residueDeclared`; six sites in `RemoveConfluence.lean`;
`RemoveOccCount.lean::enumJobs2At_Rnode_ne`; `Exec.lean::cascadeLeg` (already has `T` in
scope — one-token change).

**No change needed:** `reachedByW3d2E_structInv`, `reachedByW3d2E_residueHygienic` — they
pass the job lists as `_ _`. (The old plan implied these ripple; they do not.)

**Behavioural identity on the ComputedOnly scope is a THEOREM YOU MUST WRITE, not a
`rfl`.** `exprDirects_computedOnly` exists; **`exprDirectsAll_computedOnly` does not**
(grep returns nothing). And `enum2Base ++ []` is not definitionally `enum2Base` for a
variable list. Leg 1 owes:
- `exprDirectsAll_computedOnly : ComputedOnly e → exprDirectsAll e = []`
- `enumJob2D_eq_enumJob2 : ComputedOnly e → enumJob2D σ T dt on R e = enumJob2 σ dt on R e`

That second lemma is what makes "behaviourally identical on the CO scope" a machine-checked
claim rather than a comment — and it is what keeps the graph-state conformance goldens
honest across leg 2.

### A.2 `w3cJobValid_enumJob2D` — the two holes, by clause

Target `ReconcileStarsComplete.lean::W3cJobValid` (9 conjuncts). Of these, the
`∀ c ∈ cands / negCands / uposCands, c.name ≠ STAR` clauses are the problem:

- **Hole A** — `storedDirectSubjects` can contain a STAR-named subject.
- **Hole B** — the `hsns` hypothesis is supplied at all four call sites by
  `CascadeStrataAssemble.lean::reachedByW3d2_Rnode_source_name_ne_star`, whose write case
  runs `writeLeg_derived_inedges_eq … hco` — i.e. it is `ComputedOnly`-powered and **has no
  `_d` sibling anywhere in the tree**. Under `StoreValidRulesD` it is false whenever a
  `user:*` tuple sits on a derived key. Contrast
  `CascadeStrataSettle.lean::reachedByW3d2_Rnode_source_bare_d`, which exists and *is*
  true — the `pred = BARE` half survives because `StoreValidRulesD`'s derived disjunct
  demands `t.subject.predicate = BARE`.

The other seven clauses carry over unchanged (notably the `predicate = BARE` filter already
covers the new `storedDirectSubjects` members).

### A.3 `reachedByW3d2E_toC` — 9 of ~12 obligations already have `_d` forms

Only the `cascade` case is real (~130 lines); `empty`/`write`/`remove` are 3–6 lines.
Already landed and reusable: `reachedByW3d2_residueStarFree` (hypothesis-free),
`reachedByW3d2_schema`, `reconcileJobsLR_schema`,
`residueSubjectsStarFree_reconcileJobsLR`, `edgesClosed_reconcileJobsLR`,
`reachedByW3d2_edge_target_ne_bare_d`, **`reachedByW3d2_shadow_d`** (note: its σ0 is over
the FILTERED store `T↾U`, so every downstream consumer must be the `_filt` variant),
**`untaintedShadow_reconcileJobsLR_d`** (*fragment-free* — better than a `_d` clone),
`reconcileJobsLR_reach_collapse` (fragment-free),
`reachedByW3d2_reach_collapse_root_d`, `w3dJobCoverage_enumJob2D`,
`w3d2_leg_context_d_filt`.

**Genuinely missing:** (a) `w3dJobCoverage_enumJob2D_state` — a ~35-line packaging clone;
(b) **Hole B** above, which is not a clone at all but a fragment decision.
Note `w3d2_leg_context_d_filt` carries an extra `hCOop` (per-key operand-`ComputedOnly`)
that `w3d2_leg_context` does not — that clause must appear in the new fragment.

### A.4 `W4Fragment`, `w4_within_scope`, and what breaks

`W4Fragment` today has six fields (`computedOnly`, `twoStrata`, `wsBare`, `bareStar`,
`ttuStarFree`, `term`); `GraphAdmission` has eight, the relevant one being
`storeValid : StoreValidRules S T`.

`w4_within_scope` has three obligations. Only the third breaks: it argues
`ttuDirect` ⇒ tupleset def is `directsOnly` ⇒ contradiction with
`directsOnly_of_computedOnly`. Replacing `computedOnly` by `ComputedOrDirect` breaks that
lemma, because `directsOnly (.direct rs) = true`. **The repair is smaller than the old file
feared (~10 lines):**

> `directsOnly_of_computedOrDirect_of_noUD : ComputedOrDirect e → exprDirects e = [] → directsOnly e = false`
> — same 6-case induction. `.computed` → `rfl`; `.direct rs` → `exprDirects = [rs] ≠ []`,
> contradiction; `.inter`/`.excl` → `false` by `rfl`; `.union a b` → `exprDirects a = []`, IH;
> `.ttu` → `ComputedOrDirect` is `False`.

`hNoUD` is already an inhabited fragment carry (`W4WitnessDirect.fragment`'s 6th conjunct),
so nothing new is invented.

**What the old plan omits — T2a.** `graph_reached_inv` routes through
`reachedByW3d2E_inv` → `_edgeHygienic` → `_edgeHyg1`, which uses `ComputedOnly` in three
load-bearing places. Two are mechanical `_d` clones (a `_d` edge-char exists). The third is
not: the **write case** rewrites with `writeLeg_derived_inedges_eq` ("a write leg never
changes a derived key's in-edges") — **exactly what `StoreValidRulesD` makes false**. The
`_d` sibling covers only the *unmapped* key (`hne` premise); it deliberately does not cover
the own-key case. See §D.3: the own-key property looks false *in the collapsed model*.

### A.5 Pin impact — what regenerates, and why it matters

- **`audited_theorems.txt`** — superset check; only needs `regen_audit_pin.sh` when audits
  are ADDED (expect ~8–12 names). Zero risk.
- **`headline_statements.txt` (26)** — `graph_correct`, `graph_reached_inv`, T3/T6 and
  `graphRun_check_eq_sem` all name `W4Fragment`/`GraphAdmission` **by name**, so they stay
  byte-identical. **If T2a splits onto its own bundle, `graph_reached_inv`'s line DOES
  change** — a deliberate, visible, good change.
- **`headline_definitions.txt` (139 rows / 132 decls)** — **this is the real gate.**
  Leg 2 changes `enumJobs2At`/`enumJobs2R1`/`enumJobs2R2`/`ReachedByW3d2E`/`cascadeLeg`/
  `graphRunAux` and adds `enumJob2D`/`enum2BaseD`/`storedDirectSubjects`. Leg 5 changes
  `W4Fragment` and `GraphAdmission`. (`ComputedOrDirect`, `DirectArmsBare`,
  `exprDirectsAll`, `StoreValidRulesD` are **already pinned**, courtesy of
  `W4WitnessDirect`.)

  **This arc is precisely the attack the definition pin exists for.** `graph_correct`'s
  pinned *statement* will not move while its *meaning* changes from "ComputedOnly derived
  defs, plain admission" to the `_d` bundle. Regenerate both goldens in ONE commit, explain
  the diff in the message, and name each field added/removed in `PROOF_STATUS.md`. **Do not
  fold a pin regen into a leg that also changes proofs.**
- **`CORRESPONDENCE.md` anchor pin** — anchors are by symbol, so the signature change keeps
  them resolving. But the `GraphAdmission` field list and the `W4Fragment` "six fields"
  prose become factually wrong and are **mechanically ungated** — put them on the leg
  checklist by hand.

### A.6 Conformance-side payoff

On leg 5/6 completion, `test_conformance_graph.py` moves `direct_arm_exclusion` from
`_DIFFERENTIAL_ONLY` to `_THEOREM_BACKED` and `_EXPECTED_SPLIT` goes `(22,1)` → `(23,0)`;
`corpus.py`'s `direct_arm_exclusion` docstring (currently "still outside `W4Fragment`/the
E-chain final theorems") must be rewritten.

---

## B. The step-2 decision — DECIDED: a new fragment clause, plus the star-filter

### The evidence

`storedDirectSubjects` is `(exprDirectsAll e).flatMap (grantsOf T rs dt on R |>.map (·.subject))`
— **no filter of any kind**. `grantsOf` filters by `restrictionMatches`, whose third
conjunct is `((tup.subject.name == STAR) == r.2.2)`: **a wildcard-flagged restriction
matches exactly the STAR-named subjects.** `wsBare` only constrains a wildcard shape's
*predicate*, never whether the restriction sits on a derived def.

**Python admits the shape** (re-confirmed 2026-07-28 by compiling it):
`define approver: [user, user:*] but not banned` compiles with
`subject_wildcard_shapes={('user','...')}`, 1 stratum, no rejection —
`derive_schema_info` collects the wildcard shape via `_iter_directs` regardless of the
enclosing boolean, and the `r.wildcard` raises are about wildcard *usersets* and object
wildcards. So `storedDirectSubjects` genuinely contains `⟨user, STAR, ...⟩`. **Hole A is
real.** Hole B follows from the same tuple's write landing a STAR-sourced in-edge at the
derived R-node, which `edgeHolders` decodes into the candidate set of **both** `enumJob2`
and `enumJob2D`.

### What Python's audit enumeration actually does (the faithfulness question)

`processor.py::_incoming_concretes` ends `return [n for n in nodes if n.wildcard == '']`,
and the upos loop skips `n.predicate == '...' or n.wildcard != ''`. Every candidate/audit
source is **wildcard-free by construction**, in **id-keyed dicts** (deduplicated). Lean
mirrors half of this already (`leafConcretes` filters `u.name != STAR`);
`storedDirectSubjects` and `edgeHolders` do not.

### Verdict — do BOTH; the load-bearing decision is the fragment clause

**New `W4Fragment` field `directArmsConcrete`:**

```lean
directArmsConcrete : ∀ dt R e, S.lookup (dt,R) = some e → isDerived S (dt,R) = true →
  ∀ rs ∈ exprDirectsAll e, ∀ r ∈ rs, r.2.2 = false
```

It closes **both** holes, and closes them *upstream*: with no wildcard restriction on a
derived Direct arm, `restrictionMatches` forces `(t.subject.name == STAR) = false` on every
derived-key tuple admitted by `StoreValidRulesD`, so (a) `storedDirectSubjects` is star-free
as a theorem and (b) no star-sourced in-edge can exist at a derived R-node, making
`reachedByW3d2_Rnode_source_name_ne_star_d` provable by the same induction as `…_bare_d`.

**Also add the star-filter to `storedDirectSubjects`** — not as the fix but as
*faithfulness*: it is the exact mirror of `processor.py`'s `n.wildcard == ''`, and under the
fragment clause it is provably a no-op. That is the right relationship between a scope carry
and a model definition. It costs ~6 lines, and `noConcDirect_of_not_mem` survives because
`concMatch`'s `g.subject.name != STAR` conjunct is already in hand. All four consumers take
`s ∉ enum2BaseD` in the *negative* position, so a filtered (smaller) list only weakens their
hypothesis — they get stronger, for free.

**Why not the star-filter alone?** Because `edgeHolders` feeds clause 1 of
`W3dJobCoverage`, the only clause with no star-free restriction. Star-filtering
`edgeHolders` breaks clause 1, and clause 1 is what makes the edge-char's "stale edge
survives" branch harmless. Fixing *that* means restating a **pinned definition** consumed by
`graph_correct_w3d`, `graph_correct_w3d2`, `graph_correct_w3d2_d`,
`reachedByW3d2C_settled(_d)` and the whole `Inv` edge-hygiene stack. That is another arc,
not a leg.

**Honest scope carry — paste into `W4Fragment`'s docstring and `CORRESPONDENCE.md`:**

> `directArmsConcrete` — a **derived** def's `Direct` arms carry no wildcard-flagged
> restriction. **Python admits the shape this excludes**:
> `define approver: [user, user:*] but not banned` compiles (1 stratum,
> `subject_wildcard_shapes={('user','...')}`, no rejection), and oracle == set engine ==
> real graph index over the full query grid (re-verified 2026-07-27, root `HANDOFF.md`
> Board B1; compile re-confirmed 2026-07-28). This is a **proof-side carry, not a Python
> restriction.** Why it is needed: a stored `T:*` grant on a derived Direct arm puts a
> STAR-named subject in *both* `storedDirectSubjects` and `edgeHolders`, and
> `W3cJobValid`'s star-free-candidate clauses then fail for **every** enumerated job at
> that key — so the operational chain has no cascade constructor there. It is a **vacuity**
> boundary, not an unsoundness one. Untainted defs' wildcard arms are untouched (that is
> where `graph_correct_w3c`'s star content lives).

**Neither option is strictly wider.** Under the star-filter alone the theorem is *vacuous*
on the same schemas (`W3cJobValid` fails ⇒ no `ReachedByW3d2E.cascade` ⇒ no drained state)
— it just fails to **say so**. The fragment clause makes the boundary declared and
machine-checkable at identical strength. Given that silent vacuity is the exact bug this
whole arc exists to fix, that is strictly better epistemics.

**This also upgrades Board B1** (the orphaned `w3cJobValid_enumJob2D` star-freeness
finding). Its framing — "a lemma the widening cannot prove as stated" — should become: on
those schemas **no valid enumerated job exists at all**, hence no cascade constructor, hence
the chain is empty there. Cleaner, and checkable.

---

## C. Leg breakdown (each one commit, each green)

| leg | content | size | gate |
|---|---|---|---|
| **0** | Attack sweep (§D). Nothing lands but a ledger entry. **Success = a probe kills something.** | ½ session | n/a |
| **1** | ✅ **DONE 2026-07-28.** `DirectArmsConcrete` (`ReconcileCorrect.lean:1001`, carrying the §B scope-carry paragraph); `storeValidRulesD_derived_subject_ne_star` (`:1052`); the star-filter on `storedDirectSubjects` (`CascadeStrataEnum.lean:626`) + `noConcDirect_of_not_mem` repair (`:640`); `storedDirectSubjects_name_ne_star` (`:631`); **`reachedByW3d2_Rnode_source_name_ne_star_d`** (`CascadeStrataSettle.lean:3504`); plus the D.5 free win `exprDirects_ne_nil_of_directsOnly` (`FullScope.lean:169`). | 5 decls + 1 def edit | ✅ `lean` PASSED, audits 457 → **460**, identity pin regenerated, **definition pin unmoved (139/139)**, statements 26/26. **All four consumers compiled unchanged** — the polarity reading was right. |
| **2** | The enumeration model change: **`enum2BaseD` gains `.dedup` (Leg-0 §D.1 — do this FIRST, the rest of the leg is unrunnable without it)**, `exprDirectsAll_computedOnly`, `enumJob2D_eq_enumJob2`, `w3cJobValid_enumJob2D`, then ~20 mechanical signature edits across 8 files. Noisiest leg. Run §D.6 (state-diff `#eval`) inside this leg, not after. | 3 lemmas + 20 edits | `lean` + **definition-pin regen (6 changed, 3 added)** + **conf tiles** |
| **3** | `w3dJobCoverage_enumJob2D_state` — direct clone swapping in the `_d`/`_filt` forms. Carries `hCOop`. | 1 thm / ~35 lines | `lean` + audit pin |
| **4** | **`reachedByW3d2E_toC_d`** (~140 lines) + refactor the original into a **byte-identical wrapper** (verify against HEAD — the tree's established discipline, cf. `reachedByW3c_master_d`); same for `graph_correct_w3d2E`. | 1 big thm | `lean` + audit pin |
| **5** | `GraphAdmission.storeValid → StoreValidRulesD`; `W4Fragment` 6 → 9 fields; `directsOnly_of_computedOrDirect_of_noUD`; `w4_within_scope` clause 3; `w4Fragment_of_untainted` + both existing witnesses gain vacuous fields; **`graph_reached_inv` rebased onto a NEW narrow bundle**; finals rebased. | claim-changing | `lean` + **statement pin regen** + **definition pin regen** + audit pin |
| **6** | `W4WitnessDirect` restated as `GraphAdmission`/`W4Fragment` proper + `.final_applies`; **keep `outside_old_admission`** (it is now the proof the widening was contentful); conformance reclassification; **the vacuity caveat comes OUT of the docs.** | payoff | `lean` + **all conf + tests tiles** |
| **7** | T2a — **BLOCKED. §D.3's probe KILLED it** (machine-checked, 2026-07-28). Do not schedule proof work; what is owed first is the **design decision** (a) drained-only restatement / (b) weakened `negEdgeFree` / (c) model the leaf-family split. Until then `graph_reached_inv` keeps the narrow bundle and the asymmetry is a **declared** carry. | decision, not proof | — |

**Multi-session:** legs 4 and 5 each want a full session. 0+1 fit one; 2+3 fit one.

---

## D. Attack-first probes — **RUN 2026-07-28 (Leg 0). 2 KILLS, 3 no-kills.**

Full detail in `PROOF_STATUS.md` (Session 2026-07-28). Verdicts:

| probe | verdict | consequence |
|---|---|---|
| **D.1** duplicate candidates inflate edge multiplicity | **KILL** | `enum2BaseD` must dedupe before the coverage leg |
| **D.2** `enumJob2D` coverage-complete at every state | NO-KILL *(weak — see caveat)* | leg-5c note neither refuted nor confirmed; still open at ≥3 strata |
| **D.3** `Inv.negEdgeFree` on the `_d` fragment | **KILL** *(machine-checked)* | **T2a drops out of the arc** pending a design decision |
| **D.4** the `hND` shadow premise | NO-KILL | **drop from the risk list** — it is a tautology |
| **D.5** widened `w4_within_scope` clause 3 | NO-KILL | prove the **stronger** hypothesis-free form |

- **D.1 — KILL.** `graphRun → ([e,e], 2)` vs `graphRunD → ([e,e,e], 3)` on one write;
  `enumJob2D.cands = [alice, alice]`. Cause: `enum2BaseD = enum2Base ++ storedDirectSubjects`
  is not deduped, `admitEdge` never rejects a present `a→b`, `addEdge` conses onto a `List`.
  **Model artifact, not a Python bug** (`processor.py` dedupes by node id).
  `reachedByW3d2E_untOccCount` **survives** — verified by machine-checking the D analogue of
  `enumJobs2At_Rnode_ne`, not assumed.
  **★ Second, previously unrecorded finding:** the **baseline** `enumJob2` already doubles a
  derived edge's multiplicity **per cascade leg** (`edgeHolders` re-enumerates every existing
  copy): `1 → 2 → 4 → 8`; `enumJob2D` makes it `n ↦ 2n+1`. Documented **nowhere** in the tree
  (the existing duplicate notes concern reconvergent `rewriteClosure`, a different mechanism),
  and **invisible to the state gate because projection P3 compares edges as a SET.** Needs
  adjudication in `CORRESPONDENCE.md` §7 independently of this arc.
- **D.2 — NO-KILL, but WEAK, and the caveat is the point.** 10 write orders × a 4×3 grid: all
  drained, 0 `check ≠ sem` under both drivers, 57 true grid points; **both instruments
  sabotage-verified** (`cands := []` → 3 mismatches; `negCands := []` → 12/12) rather than
  trusted — and the first coverage instrument was **wrong** (73 false failures from omitting
  `W3dJobCoverage`'s star exemption), which is exactly why the sabotage step earned its place.
  One schema shape, two strata, ≤4 tuples, one object; the corrected clause-2 check saw only 4
  pairs. **The hunted shape was NOT constructed.** Do not upgrade this to "confirmed".
- **D.3 — KILL, machine-checked, and the most consequential result of the leg.**
  `p3_negEdgeFree_false` is proved sorry-free alongside `p3_svD : StoreValidRulesD S3 T3` and
  `p3_not_sv : ¬ StoreValidRules S3 T3` — **the widening is precisely what admits the bad
  state.** T2b is unaffected (the drained state repairs it). **Python is fine**, verified on
  the real backends: `RuleSet.apply` routes the write onto the leaf family, so the edge lands on
  `#approver.0`/`#approver.2` and **never** on `#approver`, where the `neg` row lives — different
  nodes, I6 disjointness intact throughout; 0 mismatches over the grid and a 6-way order sweep.
  **A modelling limit of the P6 leaf-family collapse, not a code bug**, and no gate in the
  project can see it.
  **Corrected-T2a options, to settle BEFORE scheduling leg 7:** (a) restate T2a at **drained**
  states only — the honest minimum; (b) weaken `negEdgeFree`/`uposEdgeFree` to exempt edges
  written by the current un-cascaded write leg; (c) model the leaf-family split — faithful, but
  a large model change.
- **D.4 — NO-KILL, drop it.** `hND` is not a hypothesis anywhere; at all four sites it is a
  three-line `List.mem_filter` tautology. The shadow layer is **already `_d`-widened**
  (`reachedByW3d2_shadow_d` takes `StoreValidRulesD` directly). No leg stalls here.
- **D.5 — NO-KILL, with a free win.** 19,280 depth-3 `Expr`s enumerated: 0 countermodels **with
  or without** the `ComputedOrDirect` premise. **State the stronger
  `directsOnly e = true → exprDirects e ≠ []`** — one induction, no fragment hypothesis.
- **D.6 — SUPERSEDED 2026-07-29; do NOT hand-run it.** The probe existed because the
  state gate could not see a multiplicity change. It now can: `Cli.lean` emits an
  `edgeCounts` field, `extractor.py`'s P3 compares untainted-arm multiplicity EXACTLY,
  and the derived arm is golden-pinned per corpus by
  `test_conformance_state.py::test_derived_arm_multiplicity_ledger`
  (`formal/conformance/derived_arm_multiplicity.json`). **Leg 2 will therefore fail that
  golden by construction, and that is the intended signal** — read the printed
  `golden=[lean, python] observed=[lean, python]` table, confirm the movement is the
  `enum2BaseD` dedup you meant, and regenerate with `ZANZIBAR_UPDATE_SNAPSHOTS=1` **in its
  own commit**, alongside the definition-pin regen the leg already owes.
  Baseline recorded 2026-07-29 (pre-Leg-2): 18 derived-arm edges over 23 corpora, Python
  uniformly 1, Lean 4 … 1013. Full adjudication: `CORRESPONDENCE.md` §7.2.
  ⚠ **One trap the new check now guards.** The tempting way to make the model's
  multiplicity match Python is to have `admitEdge` reject an already-present `a → b`.
  **Do not** — untainted-arm multiplicity is load-bearing (`untOccCount`, erase-one
  removal) and is now compared exactly, so that edit breaks `nary_union` (3 → 1). The
  faithful fix is narrower: mirror Python's presence diff inside `reconcileKeyDR`'s fold
  guard only.

---

### C.1 Corrections to this plan, found by executing Leg 1 (2026-07-28)

The plan is a *reading* of the tree, not gospel. Two things it got wrong:

1. **The Python citations for the wildcard filter.** `processor.py:594/648` (quoted in §D.1
   and the Leg-0 ledger) are the **dedupe-by-node-id** sites and are correct *for that
   claim* — but the **wildcard filters** the star-filter mirrors are
   **`index_v4/processor.py:268`** (`_incoming_concretes` →
   `return [n for n in nodes if n.wildcard == '']`) and **`:670`**
   (`if n.predicate == '...' or n.wildcard != '': continue`, the upos loop). The landed
   docstrings cite the corrected pair.
2. **§C's write-case route for `reachedByW3d2_Rnode_source_name_ne_star_d` was more
   complicated than necessary.** It proposed splitting on whether the write targets the key
   and routing the unmapped branch through `writeLeg_derived_inedges_eq_d`. **No split is
   needed and `writeLeg_derived_inedges_eq_d` is not involved at all** — the proof is a
   structural clone of `reachedByW3d2_Rnode_source_bare_d`
   (`foldl_writeDirect_edges_sound` → `rewriteClosure_produced` → `noRuleOutputs_of_derived`
   kills rule outputs → the seed is pinned by `storeValidRulesD_derived_subject_ne_star`).

**`DirectArmsConcrete` is machine-confirmed load-bearing**, not a defensive carry. Leg 1's
attack probe B swept 262 (schema, store) runs across *every* state the chain passes through
(each prefix's drained state **and** its post-write pre-cascade state), observing 824 in-edges
at derived R-nodes: **0 STAR-sourced** with the clause. **With the clause dropped, 122 stores
produce a STAR source** — e.g. `approver := excl (direct [("user", BARE, true)]) (computed banned)`
lands `(user,*,...,wAny) → (doc,d1,approver,plain)`, exactly the shape §B predicted.

---

## E. Where `optional-widening-2026-07.md` is superseded

1. **Step 2's "star-filter OR fragment clause, probe which is faithful"** — answered, and
   the answer is *neither alone*: the star-filter is the faithful mirror **and** is
   insufficient, because `edgeHolders` carries a second independent instance of the hole.
2. **Step 1's "`Delta.leaf`-scale ripple"** — understated (it is a *signature* change; it
   touches `RemoveConfluence.lean`/`RemoveOccCount.lean`, unlisted; and it needs a de-dup
   obligation, unmentioned) and simultaneously overstated (`reachedByW3d2E_structInv` and
   `_residueHygienic` need **zero** changes).
3. **Step 3's "full `_d` clone of the ~100-line cascade case"** — right about the size,
   silent on the fact that **9 of ~12 obligations already have `_d` or fragment-free forms
   landed**. The one genuinely missing prerequisite,
   `reachedByW3d2_Rnode_source_name_ne_star_d`, is never named.
4. **Step 4 does not mention T2a at all** — the biggest omission. `graph_reached_inv` is one
   of the three headline theorems the widening is *for*.
5. **Step 4's `directsOnly_of_computedOnly` worry** is resolved and is *smaller* than
   feared: ~10 lines, using the already-inhabited `hNoUD`.

---

## F. Recommendation

Start with **Leg 0 + Leg 1**. The probes are cheap, D.1 and D.3 have high kill probability,
and Leg 1 is fully additive with no golden churn — so the session lands green even if two
probes fire. Take the fragment-clause decision (§B) as settled going in, and write the
scope-carry paragraph into `W4Fragment`'s docstring **in the same commit that introduces the
clause**, not later.

Expect the arc to end at **Leg 6 with T2b widened and T2a explicitly not**, and treat that
asymmetry as the most valuable output rather than a failure.
