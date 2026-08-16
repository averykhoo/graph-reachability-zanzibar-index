# E-chain Direct-arm widening — the landable leg plan (scoped 2026-07-28)

> **ACTIVE-PLAN (declared 2026-08-16).** Still being executed: board row `P5` reads §D.3
> and row `P9` reads §C.5 item 6, so this file stays live until those rows close and then
> gets the frozen banner (see [`docs/README.md`](../../docs/README.md) §2–§3). The body is
> provenance — §A–§C were read-only analysis and are not updated in place. **Read
> §C.1–§C.6 before any cell of the body**: they record where executing this plan
> contradicted it, and they take precedence. Corrections are appended dated at the top,
> never edited into the body.

**What this is.** The durable scoping document for board item **(B)** / `ZT-P3-1`: the
E-chain Direct-arm widening, which was the fix for the fact that `graph_correct`,
`graph_reached_inv` and `Exec.graphRun_check_eq_sem` were **VACUOUS** on
`can_view: [user] but not blocked` — the canonical Zanzibar boolean shape.
`FullScope.lean::W4WitnessDirect.outside_old_admission` machine-checks that such a store
failed `GraphAdmission.storeValid` (which WAS `StoreValidRules`), so the headline theorems
held there trivially. **That was no theorem, not a narrow one.**

**Outcome (2026-08-05): fixed for T2b, and NOT for T2a — the end state §F predicted.**
`graph_correct` and everything routed through it now cover the shape; `graph_reached_inv`
takes an extra `W4NarrowT2a` bundle that the shape provably fails. Read §C.1–§C.6 for
where executing this plan contradicted it.

This file supersedes the 4-step "assessed fork cost" in
[`optional-widening-2026-07.md`](optional-widening-2026-07.md) §"Direct-arm — RESUME
(2026-07-20e)". That list is not wrong so much as **materially incomplete** — see §E.
Read this file to resume; read the older one for the provenance of the landed `_d` chain.

**Status (2026-08-05): LEGS 0–6 DONE. Only leg 7 (T2a) remains, and it is blocked on a
DESIGN DECISION, not on proof effort.** As of leg 5 the headline `graph_correct` / `backend_equivalence` /
`exclusion_effective` / `no_ghost_grant` / `Exec.graphRun{,Ops}_check_eq_sem` are **no longer
vacuous** on `can_view: [user] but not blocked` — `W4WitnessDirect.final_applies` instantiates
the unsuffixed T2b at exactly that store. `graph_reached_inv` (T2a) is NOT widened and now
carries a third bundle `W4NarrowT2a` saying so, with `outside_narrow_t2a` as the attached
counterexample. §A–§C below were read-only analysis of the tree at `e753a65` and are **not
updated in place**; every place execution contradicted them is recorded in §C.1–§C.6, which
take precedence over any cell above. §D carries the executed Leg-0 probe results (2 KILLS).

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
| **2** | ✅ **DONE 2026-08-04.** The enumeration model change. `exprDirectsAll_computedOnly` (`ReconcileCorrect.lean`); the de-dup obligation as **`freshDirectCands`**, a presence diff on the Direct-arm contribution to `cands` — **NOT the `.dedup` this cell used to prescribe, which is a no-op on the actual duplicate; see §C.2**; `mem_enumJob2D_cands`; `storedDirectSubjects_computedOnly`; **`enumJob2D_eq_enumJob2`**; `enum2BaseD_name_ne_star`; **`w3cJobValid_enumJob2D`** (same hypotheses as `w3cJobValid_enumJob2` — no fragment carry); `enumJob2D_negCands_subset`; then the signature change (`enumJobs2At` gains `T`) across 7 files. | 7 decls + 1 def edit + ripple | ✅ `lean` PASSED, audits 460 → **465**, **statements 26/26 byte-identical**, **definition pin 139 → 142** (5 changed, 1 dropped, 4 added), conf + tests tiles green. **No conformance golden moved** — §D.6's prediction is REFUTED, see §C.2. |
| **3** | ✅ **DONE 2026-08-05.** `w3dJobCoverage_enumJob2D_state` (`CascadeStrataEnum.lean:981`) — the clone, swapping in the `_d`/`_filt` forms and carrying `hCOop`; compiled first try. **Plus `W4WitnessDirect.coverage_applies` (`FullScope.lean:785`), which this cell did not ask for and should have — see §C.3.** | 2 thms / ~110 lines | ✅ `lean` PASSED, audits 465 → **467**, identity pin regenerated, **definition pin unmoved (142/142)**, statements 26/26 — the additive profile this cell predicted. Conf + tests tiles run anyway, green. |
| **4** | ✅ **DONE 2026-08-05.** `reachedByW3d2E_toC_d` + `graph_correct_w3d2E_d` (`CascadeStrataAssemble.lean`); both originals refactored into **byte-identical wrappers** (verified against HEAD by extraction-and-diff). **Plus `W4WitnessDirect.directArmsConcrete` / `toC_applies` / `w3d2E_correct_applies`, which this cell did not ask for and should have — the gate below is §C.3's insufficient one, repeated; see §C.4.** | 2 thms + 3 witness decls | ✅ `lean` PASSED, audits 467 → **471**, identity pin regenerated, **definition pin unmoved (142/142)**, statements 26/26. All conf + tests tiles green. |
| **5** | ✅ **DONE 2026-08-05.** `GraphAdmission.storeValid → StoreValidRulesD`; `W4Fragment` 6 → **10** fields (not 9 — see §C.5); `w4_within_scope` clause 3 via leg 1's `exprDirects_ne_nil_of_directsOnly` (**`directsOnly_of_computedOrDirect_of_noUD` was never needed**); `w4Fragment_of_computedOnly` (new — the subsumption, which the cell did not ask for); `w4Fragment_of_untainted` + `w4NarrowT2a_of_untainted`; both existing witnesses rebased through it; **`graph_reached_inv` rebased onto the new `W4NarrowT2a` bundle**; `graph_correct` → `graph_correct_w3d2E_d`. **Plus the four witness decls `W4WitnessDirect.{admission, w4fragment, final_applies, outside_narrow_t2a}` the cell did not ask for and §C.4 said to budget — see §C.5.** | claim-changing | ✅ `lean` PASSED, audits 471 → **477**, **statements 26 → 34** (1 changed + 8 added), **definitions 142 → 154**, all conf + tests tiles green |
| **6** | ✅ **DONE 2026-08-05.** `Td4` + `outside_old_admission4` / `admission4` / `w4fragment4` / **`final_applies4`** — the bundles at the CORPUS store, not the minimal one (this cell did not distinguish them; see §C.6); `outside_old_admission` KEPT as planned; `_EXPECTED_SPLIT` `(22,1)` → `(23,0)` with `_DIFFERENTIAL_ONLY` kept-but-empty; the vacuity caveat rewritten (not deleted) across ~25 sites. | payoff | ✅ `lean` PASSED, audits 477 → **481**, statements 34 → **38**, definitions unmoved at 154, anchors 409 → **410**; all conf + tests tiles green |
| **7** | T2a — **DECIDED 2026-08-05: option (c), model the leaf-family split and retire P6. DEFERRED, not scheduled.** (§D.3's probe KILLED the naive widening, machine-checked 2026-07-28; the decision that was owed is now made.) Until it runs, `graph_reached_inv` keeps the narrow bundle and the asymmetry is a **declared** carry — nothing is blocked or broken. Scope/blast radius/ordering: [`leaf-family-split-scope-2026-08-05.md`](leaf-family-split-scope-2026-08-05.md). | large model change | — |

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
  **⚠ (b) AS WRITTEN HERE IS WRONG, refuted by measurement 2026-08-08.** Only `negEdgeFree` is
  implicated; `uposEdgeFree` is structurally immune on the `_d` fragment (`StoreValidRulesD`
  forces a bare subject on a derived write, `uposCands` keeps only non-bare subjects, so
  `res.upos` can never hold a subject that a raw derived write gives an edge from — measured
  `uposTested = 0` in every in-fragment scenario). Left in place rather than silently rewritten,
  since this document is provenance: see `leaf-family-split-scope-2026-08-05.md` §9.2. This is
  the FOURTH cell of this plan refuted by measuring instead of following it.
  **★ RESOLVED 2026-08-05 — the decision is (c), and the work is DEFERRED.** (a) and (b) both
  shrink the claim; (c) is the only one that raises assurance. Decisive finding: **nothing
  consumes `Inv`** (four hypothesis sites, all `Inv → Inv` preservation; `EdgeHygienic`
  consumed nowhere), so (b) could not turn anything red — the house failure mode. Scope,
  blast radius and ordering: [`leaf-family-split-scope-2026-08-05.md`](leaf-family-split-scope-2026-08-05.md).
- **D.4 — NO-KILL, drop it.** `hND` is not a hypothesis anywhere; at all four sites it is a
  three-line `List.mem_filter` tautology. The shadow layer is **already `_d`-widened**
  (`reachedByW3d2_shadow_d` takes `StoreValidRulesD` directly). No leg stalls here.
- **D.5 — NO-KILL, with a free win.** 19,280 depth-3 `Expr`s enumerated: 0 countermodels **with
  or without** the `ComputedOrDirect` premise. **State the stronger
  `directsOnly e = true → exprDirects e ≠ []`** — one induction, no fragment hypothesis.
- **D.6 — SUPERSEDED 2026-07-29, and its central prediction was then REFUTED by executing
  Leg 2 on 2026-08-04: the ledger did NOT move and no regen was owed.** Read §C.2 before
  the paragraph below, which is retained as filed. The probe existed because the
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

### C.2 Corrections to this plan, found by executing Leg 2 (2026-08-04)

Two more, and the first is the plan's only prescription that was actually *wrong* rather
than merely incomplete.

1. **§C's "`enum2BaseD` gains `.dedup`" does not fix what D.1 measured.** Reproducing D.1
   before changing anything gave, on `W4WitnessDirect.Sd` after one Direct-arm write:

       enum2Base=[]  SDS=[alice]  enum2BaseD=[alice]
       cands2=[alice, alice]      cands2D=[alice, alice, alice]

   The duplicate is **between `storedDirectSubjects` and `edgeHolders`**, not inside
   `enum2BaseD`, which is a ONE-ELEMENT list here — `.dedup` on it changes nothing, and
   `cands2D` would still be `[alice, alice]` against the baseline's `[alice]`. (§D.1's own
   text names `admitEdge`/`addEdge` as co-causes, so the mechanism was understood; the
   prescribed remedy just does not sit where the duplicate is.) The reason is structural:
   a stored Direct-arm grant lands its seed edge at the derived R-node, so its subject is
   an `edgeHolder` from the first write on, and `enumJob2` already enumerates it.

   **What works: a presence diff (`freshDirectCands`)** — the stored Direct-arm subjects
   not already candidates (∉ `enum2Base` ∧ ∉ `edgeHolders`), applied to **`cands` only**.
   `negCands`/`uposCands` must keep the unfiltered `enum2BaseD`: `W3dJobCoverage` clause 3
   demands `s ∈ negCands` outright with no `edgeHolders` fallback, so filtering there opens
   a real coverage hole — and keeping `enum2BaseD` unfiltered is also what leaves
   `checkFnR_eq_star_of_not_baseD` and all four of its consumers untouched.

   Note this is a *different* mechanism from `CORRESPONDENCE.md` §7.2 item 6's still-open
   faithful fix (a `¬ hasEdge` conjunct in `reconcileKeyDR`'s fold guard, which would
   address the BASELINE `n ↦ 2n` stacking). This one only keeps the widening from making
   that artifact worse.

2. **§D.6's "Leg 2 will fail the ledger by construction" is REFUTED.** With the presence
   diff the widening is state-inert on every in-fragment corpus: all 48 state-conformance
   tests pass and **no golden regen is owed by this leg.** Controlled rather than believed
   — defeating the filter moves exactly one corpus,

       [direct_arm_exclusion] user:alice#.../ -> doc:d1#approver/:
         golden=[16, 1] observed=[31, 1]  (as [lean, python])

   (16 ↦ 31 = `n ↦ 2n+1` over its four cascade legs). So the ledger DOES observe this leg;
   it simply has nothing to report. `direct_arm_exclusion` is the only corpus that could
   move, being the only `GRAPH_FRAGMENT` member that is not `ComputedOnly` — a fact §D.6
   could have derived from `enumJob2D_eq_enumJob2` but did not.

   Also: §A.5's definition-pin estimate ("6 changed, 3 added") measured as **5 changed, 1
   dropped, 4 added** (139 → 142). The dropped row is `enumJob2`, correctly — it is no
   longer reachable from any headline statement.

**`DirectArmsConcrete` is machine-confirmed load-bearing**, not a defensive carry. Leg 1's
attack probe B swept 262 (schema, store) runs across *every* state the chain passes through
(each prefix's drained state **and** its post-write pre-cascade state), observing 824 in-edges
at derived R-nodes: **0 STAR-sourced** with the clause. **With the clause dropped, 122 stores
produce a STAR source** — e.g. `approver := excl (direct [("user", BARE, true)]) (computed banned)`
lands `(user,*,...,wAny) → (doc,d1,approver,plain)`, exactly the shape §B predicted.

### C.3 Corrections to this plan, found by executing Leg 3 (2026-08-05)

Leg 3 is the first leg where the plan's *prescription* was accurate — the clone is a clone,
it compiled first try, and the predicted pin profile (definition pin unmoved at 142,
statements 26/26) held exactly. The correction is about what the cell **omitted**.

1. **★ The cell asked for a packaging clone and no instrument, and a packaging clone is
   precisely the shape whose failure mode a green build cannot see.** The whole theorem is a
   chain of `_d`/`_filt` forms; if that chain's hypotheses are jointly unsatisfiable it still
   compiles, still audits with standard axioms only, and still passes every pin in the gate.
   That is not hypothetical here — it is **the 2026-07-20b kill**, the full-store `_d` shadow
   pair, and §A.3 warns about it two paragraphs above the sentence that specifies leg 3's
   gate as "`lean` + audit pin". The two do not fit together, and the plan never noticed.
   `formal/conformance/statement_pin.py` states the same limit about itself in as many words
   ("a definition that is vacuous on its own terms … passes this pin with its text intact.
   That remains the job of the non-vacuity witnesses").

   What landed is **`W4WitnessDirect.coverage_applies`**, mirroring the tree's existing
   discipline (`correct_applies`): instantiate the new theorem at the real compiled
   Direct-arm pair `(Sd, Td)` with every schema/store hypothesis closed by `accepts` +
   `fragment`. It assumes *less* than `correct_applies` does — `hsettledOps` is discharged
   outright, vacuously, because `approver`'s only computed ref is the untainted `banned`.
   And it is contentful rather than decorative for a reason already machine-checked in the
   tree: `outside_old_admission` proves `StoreValidRules Sd Td` is FALSE, so the untainted
   twin `w3dJobCoverage_enumJob2_state` **cannot be instantiated at this pair at all** while
   the `_d` twin can.

   **Controlled, not assumed** (house rule 2). Sabotage = one extra unused premise
   `(_hSABOTAGE : StoreValidRules S T)` on `w3dJobCoverage_enumJob2D_state`, false at every
   store the theorem is about:

       A. lake build …CascadeStrataEnum → Build completed successfully (1061 jobs).
       B. lake build …FullScope         → error: … type mismatch at `coverage_applies`:
            Application type mismatch: … h has type ReachedByW3d2 σ Sd Td
            but is expected to have type StoreValidRules Sd Td

   (A) is the finding worth carrying into legs 4–6: **the sabotaged theorem is green.** The
   witness is the only thing in the repo that sees it. Legs 4 and 5 are far bigger `_d`
   packagings than this one — budget a witness for each, not just a clone.
2. **`reachedByW3d2_reach_collapse_root_d` is not a straight clone of its untainted
   sibling** — it takes neither the operand's `hlk'` nor `ComputedOnly e'` (only
   `hWF hDAB hSV hder h hr`). So leg 3's `hops` block is *shorter* than
   `w3dJobCoverage_enumJob2_state`'s, the operand declaration is never looked up, and
   `hCOop` ends up consumed by exactly one caller (`w3d2_leg_context_d_filt`). Minor, but it
   is why the "~35 lines" estimate held despite the wider hypothesis pack.

### C.4 Corrections to this plan, found by executing Leg 4 (2026-08-05)

The size estimate was right and the clone compiled first try. Three corrections, and the
first is a gap in §A.3's *method*, not just its content.

1. **§A.3's obligation inventory misses `DirectArmsConcrete`, because it is organised
   around the wrong theorem.** §A.3 lists what `reachedByW3d2E_toC`'s cascade case needs
   by walking the COVERAGE half, and concludes the only genuinely missing pieces are
   `w3dJobCoverage_enumJob2D_state` (leg 3) and Hole B. But leg 4 also needs `hDAC :
   DirectArmsConcrete S`, which `w3dJobCoverage_enumJob2D_state` does **not** take — it
   arrives through the *validity* half (`enumJobs2At_valid` →
   `reachedByW3d2_Rnode_source_name_ne_star_d`), in both rounds. So the `_d` bundle for
   leg 4 is 16 hypotheses, not the 15 an §A.3-driven reading predicts. Leg 1 landed the
   clause and §B argued for it at length; the *inventory* simply never routed it to a
   consumer. When scoping legs 5–6, walk every half of the proof, not the headline lemma.
2. **The `remove` case and the cascade case are both SMALLER than the untainted
   originals**, which is the opposite of the usual `_d` cost. `ReachedByW3d2E.remove`
   carries plain `StoreValidRules`, converted in one line by
   `storeValidRulesD_of_storeValidRules_directArmsBare`; and the `_d` source lemmas take
   `isDerived` alone where their untainted twins take `hlk'` + `ComputedOnly e'`, so
   three declaration-lookup blocks disappear outright. The leg's real content is a
   *deletion*: the two `enumJob2D_eq_enumJob2` rewrites leg 2 installed come out, and
   that is what makes the widened candidates covered on their own terms.
3. **★ The leg-4 gate cell repeated §C.3's mistake verbatim** ("`lean` + audit pin"),
   even though §C.3 was written into this same document one leg earlier and says in
   as many words to *budget a witness for each* of legs 4 and 5. It was written before
   §C.3 existed and was never revisited. Leg 4 lands `W4WitnessDirect.toC_applies` and
   `w3d2E_correct_applies`. State that second one carefully: it is a **weaker
   statement** than the existing `correct_applies` (`ReachedByW3d2E` projects INTO
   `ReachedByW3d2C`, so it assumes more, and it follows from `correct_applies` ∘
   `toC_applies`) but a **stronger instrument**, since it discharges the whole leg-4
   bundle including `DirectArmsConcrete`. The "assumes less" phrasing that fits leg 3's
   `coverage_applies` does NOT transfer here, and a first draft of this section had it
   backwards. Sabotage-controlled (both cores given one false unused premise:
   `CascadeStrataAssemble` GREEN at 1062 jobs, `FullScope` RED at both witnesses).
   **⚠ Leg 5's cell has the same defect** — it lists the two pin regens but no witness,
   and leg 5 is the leg that rebases the headline bundle. Budget one.

   Sub-finding, on controlling the instrument: the first sabotage attempt put the premise
   before `h` and left it in scope, so `induction h` generalised it into the motive and
   the module went red for a reason unrelated to the premise being false — a control that
   "passes" for the wrong reason. `clear _hSABOTAGE` is what makes it honest.

### C.5 Corrections to this plan, found by executing Leg 5 (2026-08-05)

The claim-changing leg. The rebase itself was mechanical and compiled first try; every
correction below is about the plan's *accounting*, and the last one is the finding.

1. **`W4Fragment` goes 6 → 10 fields, not 6 → 9 — and the missing one is
   `DirectArmsConcrete` again.** This is §C.4 finding (i) recurring exactly as predicted:
   §A.5's field estimate was derived by walking the coverage half, and `DirectArmsConcrete`
   arrives through the validity half. The ten are `computedOrDirect`, `directArmsBare`,
   `directArmsConcrete`, `computedOnlyOperands`, `noUnionDirects`, then the five survivors
   `twoStrata`/`wsBare`/`bareStar`/`ttuStarFree`/`term`. `graph_correct_w3d2E_d`'s
   hypothesis list is the ground truth; read it, do not re-derive the count.
2. **`directsOnly_of_computedOrDirect_of_noUD` was never needed and should be struck from
   the cell.** Leg 1 already landed the stronger hypothesis-free
   `exprDirects_ne_nil_of_directsOnly` (`FullScope.lean:169`), on the strength of probe
   D.5's 19,280-`Expr` sweep, and its own docstring names `w4_within_scope`'s TTU clause as
   its future consumer. Clause 3's repair is two lines and one lemma application. §D.5 got
   this right in 2026-07-28 and §C's leg-5 cell was simply never updated to match.
3. **The cell omits the subsumption lemma, which is what keeps the leg honest about the
   OLD scope.** `w4Fragment_of_computedOnly` proves the pre-leg-5 six fields imply all ten
   (`computedOnly_computedOrDirect`, `computedOnly_directArmsBare`,
   `exprDirectsAll_computedOnly` ⇒ vacuous `DirectArmsConcrete`, `exprDirects_computedOnly`
   ⇒ `noUnionDirects`, operands by the same schema-wide hypothesis). Without it the leg
   *looks* like it might have traded scope rather than widened it, and both existing
   witnesses would each need five new decide-proofs. With it they are one `refine` and
   their six original proof bodies, unchanged.
4. **★ The leg-5 gate cell had §C.3/§C.4's defect for the THIRD time, and the sabotage that
   controls it is not the obvious one.** The cell listed "`lean` + statement pin regen +
   definition pin regen + audit pin" and no witness, one leg after §C.4 wrote "⚠ Leg 5's
   cell has the same defect … Budget one" into this same document. What lands is
   `W4WitnessDirect.{admission, w4fragment, final_applies, outside_narrow_t2a}`.

   The instructive part is *which* sabotage controls a bundle REBASE. Legs 3/4 used "one
   unused false premise", which works for a packaging clone. For a rebase the plausible
   failure is the **half-done leg**: widen `W4Fragment` fully but leave
   `GraphAdmission.storeValid` at plain `StoreValidRules`, and route `graph_correct`
   through `storeValidRulesD_of_storeValidRules_directArmsBare` — **which typechecks.**
   That state is indistinguishable from success by every mechanism in the gate:
   `graph_correct`'s statement is byte-identical, the definition pin MOVES (so the gate
   even reports "meaning changed"), audits are standard-axioms-only, and the theorem is
   still worth nothing on Direct-arm stores because `outside_old_admission` refutes
   `StoreValidRules Sd Td`. Observed:

       A. whole library, witness block present → ONE error, at `admission.storeValid`:
            Type mismatch: accepts.right.…right has type StoreValidRulesD Sd Td
            but is expected to have type StoreValidRules Sd Td
       B. same sabotage, four witness declarations deleted
            → Build completed successfully (1084 jobs).

   (B) is the finding: **the sabotaged tree is entirely green**, and since both goldens are
   GENERATED from the tree the leg would have regenerated them to a self-consistent pair
   and passed the whole gate. Note the asymmetry with legs 3/4 — there the sabotage
   reddened `FullScope` and left the core module green; here it would have left
   *everything* green. A rebase is a strictly worse case than a clone, and the plan
   assigned it a strictly weaker gate.
5. **Three statement-pin gaps found while inventorying the bundle consumers, unrelated to
   leg 5's content and fixed with it.** `graphRunOps_check_eq_sem` takes both bundles and
   was axiom-printed but NOT statement-pinned; nor were legs 3/4's own instruments
   (`coverage_applies`, `toC_applies`, `w3d2E_correct_applies`). `statement_pin.py`'s
   HEADLINE comment says a witness restated to `True` "would be the quietest possible way
   to make the theorems vacuous again" — which was true of five names it did not list.
   Adding a name is free; the pin is now 34.
6. **§A.6's conformance payoff is only HALF available at leg 6.** `_EXPECTED_SPLIT`
   `(22,1)` → `(23,0)` is earned. `_REMOVE_EXCLUDED = {"direct_arm_exclusion"}` is **not**:
   `removeGateB` decides plain `storeValidRulesB`, and `ReachedByW3d2E.remove` genuinely
   carries plain `StoreValidRules` (§C.4 (ii) — leg 4 converted it *inward* with
   `storeValidRulesD_of_storeValidRules_directArmsBare`, which does not run backwards).
   Lifting the exclusion is a `storeValidRulesDB` decision procedure + soundness lemma +
   a widened `remove` constructor: its own leg, not a test-flag edit.

### C.6 Corrections to this plan, found by executing Leg 6 (2026-08-05)

The payoff leg. §A.6's two-line prescription was accurate about WHAT to change and silent
about the only part that was hard.

1. **★ §A.6 does not say which STORE the reclassification needs a witness at, and the
   obvious choice is wrong.** `_THEOREM_BACKED` asserts a corpus satisfies
   `GraphAdmission ∧ W4Fragment` **at the store the driver runs**, and both bundles are
   STORE-indexed (`storeValid`, `bareStar`, `ttuStarFree`, `term`'s `NoStoreSubjectR`).
   Leg 5's `Td` is the ONE-TUPLE minimal store, picked to sharpen
   `outside_old_admission`; the corpus is FOUR tuples. A witness at `Td` does not license
   the move. So leg 6 lands `Td4` (the corpus store verbatim) and
   `admission4`/`w4fragment4`/`final_applies4` beside it.

   This is the same class of error the corpus itself is on record for — ZT-P3-3, where it
   *"sat in `GRAPH_FRAGMENT` for six days under a docstring asserting the exact opposite
   of what `FullScope.lean` machine-checks about it"*. A subset-store witness would have
   been a smaller version of it, and would have looked completely fine.
2. **§A.6's `_REMOVE_EXCLUDED` half is not available, and the trap is that the exclusion
   SURVIVES WITH A DIFFERENT REASON.** Nothing in the diff moves, so nothing prompts you
   to re-read the comment — which asserted the corpus was *"provably OUTSIDE the admission
   bundle"*, false the moment leg 5 landed. The live reason is now narrower: `removeGateB`
   decides plain `storeValidRulesB`. Same for
   `test_conformance_remove_graph`'s module docstring and the root `HANDOFF.md` line that
   predicted this would "ride E-chain Leg 5" — it did not, and could not.
3. **A justification elsewhere in the tree EXPIRED silently.** `corpus.py` kept `self_flag`
   spec-side-only because it *"has Direct arms under a boolean — genuine storage leaves,
   not `computedOnly`"* — precisely the shape leg 5 admitted. Leg 6 marks the reason
   expired and deliberately does NOT replace it: whether `self_flag` satisfies the widened
   `W4Fragment` needs its ten fields checked at its own schema and store, and per ZT-P3-3
   a corpus enters `GRAPH_FRAGMENT` on a written argument or a witness, never on a
   plausible-sounding one. **Generalisation for the next widening leg: grep for prose
   that justifies an EXCLUSION by the clause you just widened.** A widening does not only
   change what your theorems cover; it silently invalidates every argument in the tree
   that leaned on the old restriction, and those arguments live in files the leg does not
   touch.
4. **§A.6 says "the vacuity caveat comes OUT of the docs". Half of it does.** T2a is still
   vacuous on Direct-arm stores (leg 5's `W4NarrowT2a`), so §3.0 / §6.0 were REWRITTEN,
   not deleted: retired claim, then what changed, then what did not. Deleting them would
   have removed the reader's only warning about the half that is still live.
5. **The counts pin (`verify.sh` step 4e) fired on this leg** — the new `W4NarrowT2a`
   `CORRESPONDENCE.md` row moved the anchor count 409 → 410. First live catch rather than
   a retrospective one, and a reminder that a doc-only leg still needs the full `lean`
   phase, not just a build.

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
