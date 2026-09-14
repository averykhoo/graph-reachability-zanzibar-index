# `P6` part (iv) — the measured plan: widening `W4Fragment.ttuStarFree`

**ACTIVE-PLAN, opened 2026-09-14f — the body is provenance, not a living status.** This is
the execution map for `P6` part (iv), the still-owed follow-on named by the `2026-09-14e`
close of step 3b. Every figure below is as-of `2026-09-14`, produced this session and
reconciled first-hand against the live tree. Live state is the task row
(`python scripts/task.py show P6`) and `python scripts/gate_status.py` — never this file.
Corrections append **dated at the top**, never edited into the body. Freeze it when `P6`
closes.

Each claim carries its provenance: **READ** (verified first-hand this session, with
`file:line` or `file::symbol`), **KERNEL/PROBE** (produced by a run whose literal output is
in a tracked file), **AGENT** (a subagent's report, reconciled but not re-derived), or
**UNVERIFIED**.

---

## Corrections appended 2026-09-14f — the PAYOFF is measured, and it re-orders the plan

*supersedes:* `§ Blockers` item 3 ("UNMEASURED — the payoff") and `§ Ordered steps`' claim
that step 1 is the right first move.

`formal/probes/p6_partiv_live_leg_payoff_2026-09-14.lean` (PROBE, `rc=0`, literal transcript
in its header) re-measures on the LIVE post-(ii) leg what `2026-09-13b` measured at
`baseMismatch := 14 → bridgedMismatch := 9` with a candidate routing.

**Result: `14 → 2` on a grid of `546`.** Part (ii) did on the shipped leg most of what the
candidate routing only approximated. The instrument is live — `ctlNoWrite := 8`,
`semTrue := 25` — so the number is not a grid that compared nothing.

**Attribution is clean.** `(8)`: the star store fails EXACTLY `ttuStarFree` among
`storeValidRules / bareStarStore / ttuStarFree / hterm`, so the residue belongs to the
condition part (iv) widens. Both divergent queries are at the UNMATERIALISED userset subject
`folder:f9#viewer`, at `admin` and `gate`. `(10)`: materialise `folder:f9` and the count is
**`0`**. `(12)`: at that same subject `access` — the TTU relation the star bridge serves — is
`check = sem = true`, so **the bridge works**; an incomplete bridge fails at `access` first.

⚠ **The obvious explanation is REFUTED — do not write it down.** "Derived relations over a
never-written node are always empty" is ruled out by `(15)`: a derived relation above a star
USERSET grant, no `ttu` arm anywhere, same question at the same unmaterialised subject,
`mismatch := 0` with `semTrue := 16` — the situation was built and answered correctly. The
residue is specific to the star-TUPLESET through-shape with a derived relation above it.

⚠ **Two of the probe's own controls failed, and both are kept and labelled**, because each
reads exactly like a clean result: `(6)/(7)/(9)` is INVALID (its store fails
`storeValidRules`, so its `2` is a different phenomenon at different queries — a
concrete subject is not admissible under a `[folder:*]`-only restriction), and `(14)` is
INERT (`semTrue := 2`; a DIRECT restriction only grants where a tuple exists, so the
unmaterialised subject was never asked).

### What this changes

**A new step 0, and it BLOCKS the flip.** Part (iv) is not unconditionally safe: `W4Fragment`
widened to `TtuStarFreeW` admits this store, and at it `check ≠ sem` for two queries. Before
step 1, establish which of these holds —

1. some other `W4Fragment` / `GraphAdmission` field already excludes the store (then the flip
   is safe and step 0 is a pin recording why);
2. a query-subject scoping hypothesis on the headline theorems excludes an unmaterialised
   userset subject (then the same, at the theorem rather than the fragment);
3. neither — in which case `TtuStarFreeW` needs a conjunct, and the four audited names at
   `formal/audited_theorems.txt:537-540` move after all, which `§ The layering blocker`
   assumed they would not.

Until step 0 is answered, **do not pay the cone**. This is the repo's own lesson from
2026-08-15: *"the kill, made before the cone was paid"*.

⚠ The `§ Verdict` and `§ The repair` sections below are UNAFFECTED — the closure theorems are
still refuted and the disjunct is still the repair. What moved is the ORDER, and the
confidence that the flip's endpoint is reachable.

---

## § Verdict — part (iv) is a PROOF LEG, not a type edit

The `2026-09-14e` close recorded part (iv) as *"widening `FullScope.lean::W4Fragment.
ttuStarFree` to `TtuStarWide.lean::TtuStarFreeW`"*, with its precondition MET and the
2026-08-10 refutation no longer blocking. That is correct and it is not the whole cost.

**The attack-first probe run this session refutes the two theorems the widening would have to
leave standing.** `formal/probes/p6_partiv_closure_star_2026-09-14.lean` (PROBE, `rc=0`,
literal transcript in its own header):

* `RulesBareStar.lean:142::rewriteClosure_star_subject` — *a star-subject closure member
  carries the SEED's full subject* — has **one violator** at the in-scope widened store;
* `RulesBareStar.lean:168::rewriteClosure_star_bare` — *…and is therefore `BARE`-predicated*
  — has the **same** violator.

The violator is the seed's subject rewritten onto the through-shape:

```text
{ subject := { type := "folder", name := "*", predicate := "viewer" },
  relation := "access", object := { type := "doc", name := "d1" } }
```

i.e. under `TtuStarFreeW` the `ttu` arm **does** fire on a star-subject member, the subject
is no longer the seed's, and its predicate is `"viewer"` rather than `BARE`. Both
conclusions are false as written. So part (iv) cannot be a substitution of one hypothesis
type for another; every consumer that reads *"the star-subject closure member is the bare
seed"* inherits a new obligation.

⚠ **This is the fourth consecutive P6 increment where the kernel (or a probe against it)
contradicted a forecast made from reading alone**, and the reason is the same one `§ F1` of
[`p6-step3b-plan-2026-09-13.md`](p6-step3b-plan-2026-09-13.md) records: reconnaissance finds
what a statement *says*, never what it *stops being true of*.

---

## § The repair, and why it is a scope result rather than a tautology

The honest restatement concludes a **disjunction**: a star-subject closure member either
carries the seed's subject, **or** it is `⟨t.subject.type, STAR, tr⟩` for some `tr` with
`S.isSubjectWildcardUserset t.subject.type tr = true` — precisely the shape part (ii)'s
in-bridge materialises.

The probe tests the disjunct on both sides (PROBE, lines `(11)` and `(12)` of the transcript):

| measurement | result | what it rules out |
|---|---|---|
| violators NOT explained by the disjunct, at the widened store | `0` | the disjunct is **exhaustive** here |
| the same, at CONTROL a (through-shape undeclared) | `1` | the disjunct is **falsifiable** — it is not satisfied by every star member regardless |

Three controls are wired into the probe and all behaved:

* **CONTROL a** — the same closure with the through-shape undeclared (`[folder]` not
  `[folder:*]`). The violator is still present (`1, 1`), because the closure does not depend
  on the declaration; what changes is that the widened predicate **rejects** the store
  (`false, false`), putting the arm out of scope. This is what makes the refutation
  attributable to the predicate *admitting*, not to the closure shape.
* **CONTROL b** — a CONCRETE tupleset parent. Closure length is still `2`, so the TTU arm
  fired and the measurement ran on something; violators are `0, 0`. So the refutation is
  attributable to the STAR subject specifically.
* **NON-VACUITY** — `schemaRewrites SwT` is non-empty, i.e. the arm survived the taint
  filter. This is exactly what `TtuStarWide.lean::RoutingArmWitness.no_rewrite_arms` shows a
  *derived* through-shape does **not** have; without it every line of the probe is vacuous.

---

## § The census — where the hypothesis lives

**Unit matters here.** Two honest numbers, both as-of `2026-09-14`, measuring different
things — quote neither without its unit:

* **`195`** raw `grep -rn TtuStarFree` hits outside `TtuStarWide.lean`, across `19` files,
  **including** docstring and comment mentions (READ, re-measured this session);
* **`145`** classified *sites* — a binder, a `have`, a structure field, or an application
  (AGENT, one reconnaissance sweep, spot-checked below).

Classification (AGENT):

| class | count | what widening costs |
|---|---|---|
| THREAD | `104` | the binder's type changes and is forwarded; no proof content |
| RESTRICT/DERIVE | `24` | transports across `restrictUntainted`, `t :: T`, `T.erase t`, the non-derived `filter`; conclusion-agnostic, so they widen by substituting the conclusion |
| PROVIDE | `12` | still work, via `TtuStarWide.lean:135::ttuStarFreeW_of_ttuStarFree` |
| **ELIMINATE** | **`5`** | **the real work** — the branch stops being dead |

### The five ELIMINATE sites, every one verified first-hand

**Shape A — apply `hTS` to get `False` in the stored-seed branch (`2` sites).**

* `GraphIndex/RulesBareStar.lean:126` in `::starSeed_step` (READ):
  `exact hTS x ht hxstar r hr tr hk hcond`, closing the `rcases hRx with rfl | …` branch
  after `exfalso`. **This is the site the probe refutes**, and the one that propagates into
  `rewriteClosure_star_subject` / `_star_bare`.
* `GraphIndex/CascadeStable.lean:2319` (READ) — the leaf-routed L-twin, inside the
  `rcases mem_rawWriteTuples_eq_or_isLeafPred hseed with rfl | hlp` seed case:
  `exact hTS _ ht hxstar r hrS tr hk hcond`.

**Shape B — reindex `hTS` into a per-leaf `hnostar` that kills `ttuLeaf`'s star branch
(`3` sites).**

* `GraphIndex/RulesBareStar.lean:340` in `::evalE_lift_bs` (READ) and
  `GraphIndex/RulesBareStar.lean:694` (READ) — both build
  `hnostar : ∀ tup ∈ T, tup.subject.name = STAR → ¬(tup.relation = ts ∧ tup.object.type = ot)`
  as `fun tup htup hst => hTS tup htup hst _ harm tr rfl`, and feed it to
  `RulesBareStar.lean:54::ttuLeaf_elim_nss`.
* `GraphIndex/RestrictBase.lean:900` (READ) — the same kill, inline rather than via
  `ttuLeaf_elim_nss`: `exact absurd ⟨hrel, hot⟩ (hTS tup htup hstar _ harm tr rfl)`.

⚠ **`RulesBareStar.lean:54::ttuLeaf_elim_nss` is the single lemma whose STATEMENT must
change** (READ): its `hnostar` premise is the per-leaf instance of the narrow predicate, and
its conclusion carries `tup.subject.name ≠ STAR` as a component. Under the widening the star
branch of `ttuLeaf` is reachable, so both the premise and that component move together.
Shape B is three call sites of one lemma, not three independent problems.

---

## § The layering blocker, and its fix — VERIFIED

`TtuStarFreeW` is defined in `GraphIndex/TtuStarWide.lean:72`, which imports
`GraphIndex/Exec.lean`, which imports `ZanzibarProofs.FullScope` (READ,
`Exec.lean:1`). So the widened predicate currently sits **downstream** of `FullScope` —
and part (iv) needs it in `FullScope.lean:340`, upstream of every ELIMINATE site. As it
stands the edit is not expressible.

**The fix is one import line, and it is acyclic.** `TtuStarFreeW` needs exactly two things:

* `schemaRewrites` — `GraphIndex/RulesWrite.lean:82` (AGENT), already in
  `RulesBareStar`'s cone (it is what `TtuStarFree` itself quantifies over, READ
  `RulesBareStar.lean:45`);
* `Schema.isSubjectWildcardUserset` — `GraphIndex/UsStarWrite.lean:115` (AGENT), **not** in
  that cone.

READ, measured mechanically this session by walking the `import` graph:
`RulesBareStar.lean` imports exactly `GraphIndex.RulesComplete` and
`GraphIndex.BareStarCorrect`; the transitive `ZanzibarProofs` cone of
`GraphIndex.UsStarWrite` is `9` modules —

```text
Core.Ident, Core.Refs, Core.Schema, Core.Store,
GraphIndex.Closure, GraphIndex.ObjStarWrite, GraphIndex.State, GraphIndex.Write,
Spec.Stratify
```

— and contains **neither** `RulesBareStar` **nor** `RulesComplete` **nor**
`BareStarCorrect`. So adding `import ZanzibarProofs.GraphIndex.UsStarWrite` to
`RulesBareStar.lean` **cannot** close a cycle.

**Decision (Lean-shaped, taken here per `CLAUDE.md` § "Who decides"): define `TtuStarFreeW`
in `RulesBareStar.lean`, beside `TtuStarFree`, and keep `TtuStarWide.lean` downstream for
`ttuStarFreeWB`, the gate half and the audited names.** The alternative — moving
`isSubjectWildcardUserset` upstream instead — touches a definition that
`UsStarWrite.lean:106-109` warns is load-bearing for `bridgedInConcrete_elim` (pinned at
`Audit.lean:134`), and buys nothing the import does not.

⚠ **The four audited names stay put.** `ttuStarFreeWB`, `ttuStarFreeWB_iff`,
`ttuStarFreeW_of_ttuStarFree`, `ttuStarFreeWB_of_ttuStarFreeB` are pinned at
`formal/audited_theorems.txt:537-540` (AGENT). Relocating the *predicate* moves none of
them; relocating any of *them* reds `verify.sh` step 4a.

---

## § Ordered steps

Cost column is a forecast, not a measurement. `§ Verdict` above is the standing reminder
that P6 forecasts made from reading have been wrong four increments running.

| # | step | cost |
|---|---|---|
| 1 | Add the `UsStarWrite` import to `RulesBareStar.lean`; move/restate `TtuStarFreeW` there. Re-point `TtuStarWide.lean` at it (no name changes, no audited-name movement). Build. | S |
| 2 | **Attack step 3 before doing it**: probe whether `ttuLeaf_elim_nss`'s conclusion survives with only its `hnostar` premise widened, or whether the `tup.subject.name ≠ STAR` component must go too. | S |
| 3 | Restate `ttuLeaf_elim_nss` (premise + conclusion) and repair its `3` shape-B call sites. | M |
| 4 | Restate `starSeed_step` / `rewriteClosure_star_subject` / `rewriteClosure_star_bare` with the bridged disjunct; repair the `2` shape-A sites. | **L — the leg** |
| 5 | Sweep the `104` THREAD + `24` RESTRICT/DERIVE sites. Mechanical, but `§ F1` of the step-3b plan is the warning: most of step 3b's "volume" was also mechanical and the cost was elsewhere. | M |
| 6 | Flip `FullScope.lean:340` to `TtuStarFreeW`; repair `w4Fragment_of_computedOnly` / `w4Fragment_of_untainted` to pipe through `ttuStarFreeW_of_ttuStarFree`. | S |
| 7 | Regenerate the statement + definition pins **deliberately, RED first**, and say what entered and left the pinned closure. `formal/headline_statements.txt:44` is inside `Zanzibar.W4WitnessDirect.fragment` (AGENT) and is expected to move. | S |
| 8 | Mutation sweep over everything added, with an `M0` instrument control, per `docs/sabotage-procedure.md`. | M |

**The commit-safe stopping points are the end of step 1 and the end of step 8.** Steps 3-6
leave the tree red by construction.

---

## § Blockers and open questions

1. ⚠ **`formal/HANDOFF.md:487-494` is STALE and contradicts the tree** (READ). It still
   states the 2026-09-12 framing verbatim — *"(ii) materialises the edge is KNOWN FALSE as
   stated"*, *"`TtuStarFreeW` lacks an `isDerived = false` conjunct"*, *"Blocked on a user
   scope call"*. All three were superseded: Wall 1 was decided **by lemma, not by
   narrowing**, on 2026-09-12b and landed 2026-09-12c as
   `TtuStarWide.lean:318::ttuStarFreeW_through_untainted` (READ); its *recorded reason* was
   then measured false on 2026-09-13 and replaced by the taint-filter argument
   (`::RoutingArmWitness`, READ); and part (ii) landed 2026-09-14e. **Fix the paragraph
   before the next session reads it as state.**
2. **OPEN, cheap, unmeasured since 2026-09-13**: is `term`'s `NoTtuTarget` half *implied* by
   `RewriteMatchDeclared`, which `FullScope.lean:1350` carries separately (AGENT)? If yes,
   `ttuStarFreeW_through_untainted` becomes hypothesis-free and step 6 has one fewer premise
   to thread. Recorded on the `P6` row and on `TtuStarWide.lean:465-470` as explicitly
   **not** claimed. Settle it in step 2's probe run — it is the same `#eval` session.
3. **UNMEASURED — the payoff.** The `2026-09-13b` entry measured `baseMismatch := 14 →
   bridgedMismatch := 9` on `Sp` with a *candidate* routing, i.e. the repair did not reach
   zero. The real leg has since landed (step 3b). **Nobody has re-measured the mismatch count
   on the LIVE post-(ii) write leg**, and that number decides whether part (iv) is inhabitable
   at all or whether a residual gap remains. This is the highest-value measurement still
   owed and it does not depend on steps 1-8.

---

## § What this plan does NOT establish

* The `145`-site classification is **AGENT** work, spot-checked at the `5` ELIMINATE sites
  and at the layering claim only. The THREAD/RESTRICT split is not re-derived; a step-5
  session should expect the usual undercount (`P3`'s re-verified *"~123 sites / 7 files"*
  budget was live `~136 / 8`).
* No claim is made that step 4's disjunct is provable — only that it is **true at the probed
  store** and **falsifiable**. Attack it before proving it (house rule 2).
* Nothing here has been through the gate. The tree at `2026-09-14f` is unchanged except for
  the probe and this file.
