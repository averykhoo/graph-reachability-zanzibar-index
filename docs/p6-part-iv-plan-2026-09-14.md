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

## Corrections appended 2026-09-14h (sixth) — stage 1 is GREEN: `lake build` completes, 1089/1089

*supersedes:* the (fifth) correction's *"Steps 1–3 are REASONED"* and its *"nothing after
`FullScope` has been elaborated"*. Both are now settled by the kernel. Everything else in
(fifth) stands, including its correction of the (fourth) staging.

**KERNEL, `lake build`, `RC=0`, `ERR=0`, `Build completed successfully (1089 jobs)`.** The
route the (fifth) correction reasoned out is the route that worked, with one addition it did
not anticipate.

### The three planned steps, all confirmed

1. **The 19 linchpin conclusions tightened to `declaredWildcardShapes` — free at every
   site**, exactly as reasoned: every one of those proofs already ended at a literal wildcard
   restriction. Not one needed a new argument.
2. **The 74 + 1 bareness carries moved to `declaredWildcardShapes`** and discharge from
   `W4Fragment.wsBare` unchanged.
3. **The operational sites stayed on the full two-pass `wildcardShapes`** — the fold's
   candidate list, `ReachedByW3c`'s constructor, `reconcileStarsKey*`, and every
   `res.stars = (wildcardShapes S).filter …`. The characterisation/operational split turned
   out to be **textually clean**: a characterisation always reads `… ∈ wildcardShapes S`, an
   operational site always hands the parenthesised list to a fold, so the sweep could be
   mechanical (`.scratch/repoint.py`) rather than site-by-site.

### ★ What (fifth) did NOT anticipate — the linchpin had to move UP the import chain

Re-pointing made the routed linchpin load-bearing inside
`CascadeStrataResettle::settledComplete_jobsLR_targeted{,_d}`, which sits **upstream** of the
module that held it. Four lemmas were relocated, statements and proofs byte-unchanged:

| lemma | from | to |
|---|---|---|
| `graphRec_star_declared` | `CascadeStrataResettle` | `CascadeStable` |
| `checkFnR_star_declared` / `_d` / `_d_filt` | `CascadeStrataEnum` | `CascadeStrataSettle` |

`formal/audited_theorems.txt` pins audited theorems **by NAME, not by path**, so the
relocation does not disturb that pin — verified by reading the check
(`verify.sh` step 4a compares name sets). ⚠ `docs/history/session-log.md:2810` cites
`CascadeStrataEnum.lean::checkFnR_star_declared` and is now stale; it is FROZEN history and
is deliberately **not** edited (`CLAUDE.md`, "Status lines inside `docs/history/` are FROZEN").

### Four new helpers, and why they are subject-generic

`ReconcileStarsComplete::coveredFn_declared_w3c` / `::coveredFn_bare_w3c` (transport through
`reachedByW3c_master`'s leafwise agreement + `evalE_computedOnly`) and
`CascadeStable::coveredFn_declared_shadow` / `::coveredFn_bare_shadow` (transport through
`UntaintedShadow`, the same first step as `checkFn_eq_sem_w3d`).

⚠ **They take NO bareness hypothesis and produce one, and that is the whole point.** The read
bridges (`checkFn_eq_sem_*`, `checkFnR_eq_sem_settled*`) all refuse to speak below
`s.name = STAR → s.predicate = BARE`, so using them to establish bareness is circular. Going
through the linchpin is the only non-circular route, and it is why the fix needed lemmas at
all rather than just a rename.

### Also landed

* `TtuStarWide::mem_throughShapes_iff_isStarTuplesetThrough` — the two independent Lean
  transcriptions of Python's second loop, pinned equal. **This, not the enumeration, is the
  durable deliverable**: the enumeration was one line, and the reason it stayed wrong for a
  month is that nothing in the tree could see it.
* `SettledKey` (`CascadeStable`) and `w3c_row_char{,_d}` row characterisations restated over
  `declaredWildcardShapes` — a STRENGTHENING (the rows provably cannot hold anything else),
  with the reason recorded in situ.
* Stale doc-claims corrected where the change refutes them: `UsStarWrite.lean`'s header
  (the sharpest — *"`wildcardShapes` sweeps only LITERAL restrictions"*),
  `ReconcileStarsComplete.lean`'s header and linchpin block, `FullScope.lean`'s
  `sxUsWild_other_admission_fields_hold` block, `Audit.lean`'s W3c block,
  `formal/conformance/corpus.py`, `::test_conformance_nary_strata.py`,
  `::test_w4fragment_scope_pin.py`.

### ★ THE GATE IS GREEN — all ten phases, on this tree (2026-09-14h)

`lean PASSED (holes=0, audits=615, pinned=615)`; `conf-tile:1..5/5 PASSED` (110/109/109/109/109,
each at its floor); `tests-tile:1..4/4 PASSED` (288/287/287/287). `gate_status.py`: **COVERED
on this tree.** Three generated goldens were regenerated deliberately, and each delta is
exactly the change and nothing else:

| golden | delta | why |
|---|---|---|
| `formal/audited_theorems.txt` | **+13, none removed** | the 13 new `#print axioms` lines |
| `formal/headline_definitions.txt` | +2 rows (`declaredWildcardShapes`, `throughShapes`); bodies of `wildcardShapes`, `SettledKey`, `CompleteKey`, `W3dJobCoverage`, `W4Fragment` | the split + the re-points |
| `formal/headline_statements.txt` | **1 line** — `W4WitnessDirect.fragment` | its `wsBare` conjunct |

⚠ **Regenerating a golden destroys the signal it carried — say what replaced it.**
`test_w4fragment_scope_pin.py`'s own docstring makes this point about
`headline_definitions.txt`. What protects the change here is that `W4Fragment`'s field COUNT
and NAMES are **unchanged** (10, same order), which is the structural signal that module
guards by a HAND-MAINTAINED list nothing regenerates; and that the semantic content of the
statement change is now carried positively by
`FullScope.lean::sxThruDerived_wsBare_over_full_list_fails` rather than only by a golden.

### ★ SABOTAGE — both attacks RUN, both attributable, literal output below

`docs/sabotage-procedure.md`. The tree was green (1089 jobs, `RC=0`) immediately before each
arm, which is the instrument control: a red below cannot be pre-existing breakage.

**`S1` — `throughShapes (_S : Schema) : List Shape := []`.** The narrowest *plausible*
weakening, not a catastrophe: it is exactly the pre-2026-09-14h state, i.e. what a future
"simplification" of the split would restore. `lake build ZanzibarProofs.FullScope` → `RC=1`,
**four reds, every one a `decide`-level CLAIM red naming its own proposition**:

```text
error: ZanzibarProofs/FullScope.lean:1165:13: Tactic `decide` proved that the proposition
  ("folder", "viewer") ∈ wildcardShapes SxThruDerived            is false
error: ZanzibarProofs/FullScope.lean:1165:24: … ¬∀ sh ∈ wildcardShapes SxThruDerived, sh.2 = BARE   is false
error: ZanzibarProofs/FullScope.lean:1165:46: … ("folder", "viewer") ∈ throughShapes SxThruDerived  is false
error: ZanzibarProofs/FullScope.lean:1175:24: … ("folder", "viewer") ∈ throughShapes SxThruPlain    is false
```

★ **And NOTHING ELSE in FullScope's 1080-module closure reddened.** That is the finding, and
it cuts two ways. It means the two new pins are the **sole** guard against silent regression
to the pre-fix model — no other declaration in the development notices. It is also an
INDEPENDENT, mechanical confirmation of the "stage 1 is inert on today's fragment" claim,
which up to that point rested on contraposing `coveredFn_declared`: if emptying pass 2 broke
nothing but the pins, then nothing on this fragment was depending on pass 2's content.

⚠ **An INERT arm, caught by asking what each arm was supposed to move.** The control
`sxThruPlain_gains_same_through_shape`'s FIRST conjunct —
`throughShapes SxThruPlain = throughShapes SxThruDerived` — **survives `S1`**, because
`[] = []`. Only its membership arm is live under this attack. That is `P6` step 2's quiet
failure exactly (a mutation that does not move the property reads like a clean pin); the arm
is kept because it does real work against a *different* attack (one that changes only one
schema's shapes), but it must not be counted as evidence here.

**`S2` — drop the `r.2.1 == BARE` conjunct from `throughShapes`' filter.** Chosen to be
single-variable in the other direction: at `SxThruDerived`/`SxThruPlain` the only wildcard
restriction IS bare, so both lists are unchanged and **`FullScope` builds GREEN** — the
control. `lake build ZanzibarProofs.GraphIndex.TtuStarWide` → `RC=1`, one red, in
`mem_throughShapes_iff_isStarTuplesetThrough` and nowhere else:

```text
error: ZanzibarProofs/GraphIndex/TtuStarWide.lean:105:12: Tactic `rewrite` failed …
  case mp.some.isTrue …  hc : r.2.2 = true
```

⚠ **On its first run `S2` produced only a PROOF-SCRIPT red** — the tactic stopped matching
because the `if` condition lost a conjunct — **and by `P6` step 3a's own rule that is not a
pin.** No schema in the tree exhibited the countermodel, so the claim itself was never
decided; `S2` showed the correspondence was *coupled* to the filter, not that it was
*pinned*.

**`S2b` — the same mutation, after adding the missing witness.**
`TtuStarWide.lean::WideWitness.SwNB` is the schema the gap named: a tupleset carrying a
wildcard **USERSET** restriction `[folder:*#viewer]` rather than a bare `[folder:*]`, where
Python's `r.predicate == '...'` gate (`zanzibar_utils_v1.py:1008`) means the second loop must
contribute nothing. `::nonBareTupleset_declines_through_shape` asserts that both
transcriptions decline it, plus a non-vacuity arm so the pin cannot pass by the situation
being absent. Re-running `S2` against it:

```text
error: ZanzibarProofs/GraphIndex/TtuStarWide.lean:176:13: Tactic `decide` proved that the proposition
  throughShapes SwNB = []
is false
```

★ **That is a CLAIM red**, alongside the script red, with `FullScope` green throughout as the
control. The `BARE` gate on pass 2 is now pinned rather than merely coupled.

### Still not established at this line

* The dedup/order divergences from Python's `sorted(frozenset(...))` remain, deliberately,
  and are recorded on `ReconcileStars.lean::wildcardShapes` and in `CORRESPONDENCE.md` §7.
* **Stage 2 (part iv proper) is untouched.** `W4Fragment.ttuStarFree` is unchanged, so the
  corrected enumeration is inert on today's fragment — see `CORRESPONDENCE.md` §7 for why
  that is a theorem here and not merely an observation.

---

## Corrections appended 2026-09-14h (fifth) — stage 1 IN FLIGHT: the split LANDS, and the re-point's real cost is MEASURED at 74 + 19 sites

*supersedes:* the (fourth) correction's staging line *"Stage 1 … the split definitions; `wsBare`
re-pointed; the Tier-1 coverage-false lemma; repair of the bridge-site through-shape cases"* —
that enumeration was right about the parts and **wrong about which one is the work**. It is not
the bridge sites. It is that **74 downstream proof carries and 19 membership-lemma conclusions
are stated over the FULL list**, and re-pointing `wsBare` alone strands every one of them.

### What LANDED (KERNEL — `lake build` is the referee, not a census)

| step | site | state |
|---|---|---|
| split | `ReconcileStars.lean::declaredWildcardShapes` (old body, renamed) / `::throughShapes` (Python pass 2) / `::wildcardShapes` (`declared ++ through.filter (∉ declared)`) | **BUILDS** |
| glue | `::mem_wildcardShapes_of_mem_declared` / `::mem_wildcardShapes_of_mem_through` / `::mem_wildcardShapes_iff` | **BUILDS** |
| repair | 4 × `unfold wildcardShapes` → `mem_wildcardShapes_of_mem_declared` + `unfold declaredWildcardShapes` (`ReconcileStarsComplete.lean::coveredFn_declared` / `::graphRec_star_declared_d` / `::directArm_star_declared`, `CascadeStrataResettle.lean::graphRec_star_declared`) | **BUILDS** |
| re-point | `FullScope.lean::W4Fragment.wsBare` → `declaredWildcardShapes` | **RED, 3 errors** — see below |
| pins | `FullScope.lean::sxThruDerived_wsBare_over_full_list_fails` (+ its one-axis control `::sxThruPlain_gains_same_through_shape`), `TtuStarWide.lean::mem_throughShapes_iff_isStarTuplesetThrough` | written, **NOT YET ELABORATED** (`FullScope` is the failing module, so nothing after it was checked — step 3a's truncation trap) |

★ **The 235-reference cone was almost entirely inert, as the census predicted**: the whole-tree
build reached `FullScope` — 1084 of 1089 targets, including all nine `Equiv.lean` headline
theorems — with exactly **4** structural breaks, every one a proof that stepped through the old
body with `List.mem_flatMap`. **AGENT-predicted and KERNEL-confirmed**, including the one site
`rg wildcardShapes` cannot see (`FullScope.lean:586::w4_within_scope`, which builds the
membership inline); that site needed **no** edit, because re-pointing `wsBare` at pass 1 made
its inline `mem_flatMap`/`mem_filterMap` term correct as written.

### ★ THE REAL COST, and it is not where the (fourth) correction put it

Re-pointing `wsBare` reds `FullScope.lean` at `:638` (`graph_correct_w3d2E_d`), `:798`
(`reachedByW3d2E_inv`) and `:871` (`w4Fragment_of_untainted`), all the same error:

```text
hF.wsBare has type    ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE
but is expected       ∀ sh ∈ wildcardShapes S, sh.2 = BARE
```

**MEASURED (`rg`, 2026-09-14h) — the carry pattern `∀ sh ∈ wildcardShapes S, sh.2 = BARE` occurs
74 times across 12 files**: `CascadeStrataSettle` 17, `CascadeStrataResettle` 11, `Equiv` 9,
`CascadeEnum` 7, `CascadeStrataEnum` 7, `ReconcileStarsComplete` 6, `CascadeSettle` 4,
`CascadeStrataAssemble` 4, `FullScope` 3 (a 4th is the new pin and MUST NOT move),
`CascadeStrataEdge` 3, `CascadeInv` 2, `CascadeStable` 1. Plus **1** at `Sd`
(`FullScope.lean::W4WitnessDirect.fragment`).

⚠ **A full-list bareness carry is FALSE on the admitted fragment, so "just keep the carries" is
not on the table.** `W4Witness.SxThruPlain` is `GraphAdmission`-admitted
(`::sxThruPlain_admitted`, audited) and its pass-2 shape is `("folder","viewer")` — predicate
`"viewer"`. This also kills the cheaper repair of deriving full-list bareness from
`GraphAdmission.usWild`: `usWild` only refuses a *derived* bridged-in key, and `SxThruPlain`'s
through-shape is untainted by construction (that is the whole point of the control).

★ **And that is measured against the SHIPPED PYTHON, not just argued in Lean** —
`formal/probes/p6_stage1_python_shapes_2026-09-14.py` (rc=0, verbatim transcript in its
header). `derive_schema_info` returns `[('folder','...'), ('folder','viewer')]` at **both**
schemas — matching the corrected Lean enumeration shape for shape — and
`parse_openfga_schema` **ADMITS `SxThruPlain`** while refusing `SxThruDerived`. So a schema
the implementation compiles and runs carries a non-`BARE` subject-wildcard shape, which is
the strongest available form of "the full-list `wsBare` would have shrunk the fragment": it
is a fact about the code, not about the model. ⚠ Read the refusal of `SxThruDerived`
carefully — it is about the through-shape being DERIVED, not about it being non-bare, so it
is a consistency check on `::sxThruDerived_not_admitted` and NOT the load-bearing half.

### The route, DECIDED — strengthen the linchpin rather than weaken the fragment

**REASONED, and the reason is first-hand:** all four repaired sites above proved
`sh ∈ wildcardShapes S` by tracing a covered star back to a **literal wildcard restriction** —
i.e. every one of them actually establishes pass-1 membership, and the `++` was pure loss. So:

1. **Strengthen the 19 "no ghost star coverage" conclusions from `wildcardShapes` to
   `declaredWildcardShapes`** (`ReconcileStarsComplete::coveredFn_declared`, `::coveredFn_declared_d`,
   `::graphRec_star_declared_d`, `::directArm_star_declared`; `CascadeStrataResettle::graphRec_star_declared`;
   `CascadeStrataEnum::checkFnR_star_declared{,_d,_d_filt}`; the `w3d_leg_context` /
   `w3d2_leg_context{,_d,_d_filt}` conjuncts; and the `have … : sem → sh ∈ wildcardShapes S`
   blocks inside `graph_correct_w3c/w3d/w3d2{,_d}` and `checkFnR_eq_sem_settled{,_d,_d_filt}`).
   This is a **strengthening**, free at every site, and consumers that still want the full list
   get there by `mem_wildcardShapes_of_mem_declared`.
2. **Move the 74 + 1 bareness carries to `declaredWildcardShapes`.** They then discharge from
   `W4Fragment.wsBare` unchanged.
3. **Leave the OPERATIONAL sites on the full `wildcardShapes`** — everything passed to the fold
   (`ReachedByW3c`'s constructor, `applyLoggedR`, `reconcileStarsKey*`) and every residue-row
   characterisation `res.stars.contains sh ↔ (sh ∈ wildcardShapes S ∧ sem … = true)`. **That is
   the fix**; collapsing these back to pass 1 would undo it silently.

★ **The (fourth) correction's "Tier-1 coverage-false lemma, REASONED only" falls out as a
COROLLARY of step 1 rather than needing its own proof:** if a shape is in `throughShapes S` and
not in `declaredWildcardShapes S`, the strengthened linchpin makes `coveredFn σ sh = true`
contradictory, so it is never covered on this fragment. That is a strictly better outcome than
the plan forecast — the obligation is discharged by the same edit that creates it, not carried.

### Still not established at this line

* Steps 1–3 are **REASONED**; only the split itself and the 4 repairs are KERNEL-confirmed.
* Nothing after `FullScope` has been elaborated — `TtuStarWide`, `Exec`, `Cli`, `Audit` are
  unevaluated, so the 4-break count is an **"at least these"**, never an "only these"
  (`P6` step 3a's truncation trap).
* **Two representation divergences from Python remain, deliberately** and are recorded on
  `ReconcileStars.lean::wildcardShapes`: Python's shape set is a `frozenset` rendered
  `sorted(…)`, so a shape produced twice by pass 2 appears twice here, and the orders differ.
  Inert for every consumer today (the list is read only through `∈` / `filter` / `any`) —
  **unchecked** against any future order- or multiplicity-sensitive consumer.
* The `Inv` bareness worry from the (fourth) correction is **ANSWERED, first-hand READ and
  NEGATIVE**: `State.lean:722::Inv.negStarCovered` requires only
  `res.stars.contains n.shape = true`, with no predicate constraint, and
  `BareStarCorrect.lean:44::BareStarStore` constrains STORE tuples, not residue rows. No `Inv`
  clause pins bareness of a persisted `stars` row, so none of them obstructs the fix.

---

## Corrections appended 2026-09-14g (fourth) — DECISION `D1-split`, and the kill-check PASSES

*supersedes:* the third correction's *"Two defects, not one"* and its `D1`/`D2`/`D3` table's
pricing of `D2` as "the cone alone".

### The decision

**`D1-split`, staged.** Recommended by a `claude-fable-5` subagent (per the user's
2026-09-14g procedure), adopted because its load-bearing claim verified first-hand. Do **not**
weaken `wsBare` with a disjunct — **split the enumeration**:

* `declaredWildcardShapes S` := today's `ReconcileStars.lean:97::wildcardShapes` body, renamed;
* `throughShapes S` := Python's pass 2 (`zanzibar_utils_v1.py:1001-1008`);
* `wildcardShapes S := declaredWildcardShapes S ++ throughShapes S` — keeps the NAME so the
  `CORRESPONDENCE.md` anchors resolve, and now matches the shipped function;
* `W4Fragment.wsBare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE` — **extensionally
  identical to today's field at every schema**, so the fragment does not shrink.

⚠ **The split is MANDATORY, not tidy — verified first-hand.** Probe
`p6_partiv_shapes_gap_2026-09-14.lean` `(6)`: at `W4Witness.SxThruDerived` the corrected
enumeration flips `wsBare` `true → false`, which **falsifies the audited theorem**
`FullScope.lean:1113::sxThruDerived_wsBare_holds_but_usWild_fails`
(`audited_theorems.txt:91`, first conjunct, `by decide`). Its `(I2)` control shows the
sibling `SxThruPlain` — differing on one axis, the boolean operator — gains the same shape,
so the result is attributable to the enumeration. **This corrects the third correction's
"`D2` = the cone alone": re-pointing `wsBare` is required for ANY enumeration fix.**

`wsBare` itself is a **proof-scope guard, not a semantic protection** (subagent's analysis,
spot-checked not re-derived): its two consumers are `FullScope.lean:580::w4_within_scope`
clause 2, which only instantiates it at declared restrictions, and the star-read bridge's
subject-scope side condition, which keeps the fold's internal `starSubj sh` probes inside the
scope where `checkFn = sem` is proved. Nothing becomes *false* when a non-`BARE` wildcard
shape exists; the cost is a new bridge leg, not a hidden unsoundness.

### ★ Stage 0, the kill-check — it PASSES

`formal/probes/p6_partiv_stage0_killcheck_2026-09-14.lean`. Simulating the fold's own formula
over the corrected shape list, in stratum order, then reading:

| measurement | result |
|---|---|
| `(2)` at the phantom, `admin` | `check = sem = true` ✔ |
| `(2)` at the phantom, `gate` | `check = sem = true` ✔ |
| `(3)` regression at the materialised control `f1` | correct at both ✔ |
| `(1)` corrected residues | `admin` **and** `gate` both get `stars := [("folder","viewer")]` |
| `(4)` INSTRUMENT CONTROL | reproduces the live residue ✔ |

**The enumeration fix closes both divergent queries.** The subagent's "biggest risk" — `gate`
surviving on a second defect — does **not** materialise.

### ⚠ Two corrections to this session's own findings

1. **"Two defects, not one" is REFUTED.** It rested on the UNROUTED `coveredFn` reading
   `false` at `gate`. The live fold uses the ROUTED `coveredFnR`, which consults the residue;
   with the enumeration corrected and strata in order it reads **`true`**. `gate`'s failure
   was downstream of the missing shape. The recorded stratum-2 gap
   (`CORRESPONDENCE.md:1213`) does not explain this store; whether it is real in its own
   context is untouched either way.
2. **The kill-check's first form reported the opposite answer**, on two errors of mine — the
   unrouted readers, and computing `admin`/`gate` from the same pre-patch state, which denies
   `gate` the input the fix exists to give it. Both manufacture a `gate` failure. Its
   instrument control `(4)` is the only reason that is not now written down as a finding.
   **A simulation with the wrong reader reads exactly like a correct one.**

### The staging

* **Stage 1 (accuracy, a commit point, unconditional):** the split definitions; `wsBare`
  re-pointed; the Tier-1 coverage-false lemma; repair of the bridge-site through-shape cases;
  restate `sxThruDerived_wsBare_holds_but_usWild_fails` over `declaredWildcardShapes`;
  RED-first pin regeneration. Lands the accuracy fix and preserves today's fragment exactly.
* **Stage 2 (part iv proper):** now UNBLOCKED by the kill-check — the Tier-2 star-userset
  read bridge plus the `§ Verdict` closure-disjunct leg (step 4, "L").

### Still not established

* The kill-check is a **simulation** (`putResidue`, not a real cascade run) at **one store**.
* Tier 1's "coverage is false on both sides under today's carries" lemma is REASONED only.
* The `Inv` clauses (e.g. `negStarCovered`) may pin bareness of persisted `stars` rows —
  **unchecked**; walk them in stage 1's red-site pass.

---

## Corrections appended 2026-09-14g (third) — route `D`'s cone is MEASURED: root cause found, and fixing it defeats the widening

*supersedes:* the second correction's *"`D`'s cone is UNMEASURED"*. It is measured. Three
probes, all `rc=0` with verbatim transcripts and passing instrument controls.

### The chain, end to end

| # | probe | finding |
|---|---|---|
| 1 | `p6_partiv_residue_locus_2026-09-14.lean` | Lean residue at `(doc:d1, admin)` has `stars := []`; the READ path is innocent |
| 2 | `p6_partiv_python_residue_2026-09-14.py` | shipped residue there is `stars := [('folder','viewer')]`, `upos := []` — opposite representations |
| 3 | `p6_partiv_starfold_cause_2026-09-14.lean` | `coveredFn` at that shape/object already returns **`true`** for `admin` — the coverage TEST is innocent too |
| 4 | `p6_partiv_shapes_gap_2026-09-14.lean` | the shape was never in the fold's candidate list |

The live fold is `CascadeStrata.lean:187::GraphState.reconcileResidueKeyR`:
`stars := shapes.filter (fun sh => σ.coveredFnR T dt on R e sh)`. A `filter` cannot mint a
shape its input never held, so `coveredFn = true` with `stars = []` forces the conclusion
that `("folder","viewer")` was absent from `shapes`.

### ★ THE ROOT CAUSE (READ + PROBE)

`zanzibar_utils_v1.py` builds `SchemaInfo.subject_wildcard_shapes` in **two** passes:
declared wildcard restrictions (`:993-995`), **plus** a star-tupleset through-shape pass
(`:1001-1008`) — for each TTU, if its tupleset relation carries a bare wildcard restriction,
add `(r.type, ttu.target_rel)`. Its own comment gives the reason: *"that through-shape must
be declared or the graph rejects a schema-legal write the set engine accepts."*

**`ReconcileStars.lean:97::wildcardShapes` implements only the FIRST pass** — while its
docstring cites that very Python function as its correspondent. Measured both sides:

* shipped: `[('folder','...'), ('folder','viewer')]`
* Lean: `[("folder", BARE)]`
* probe 4's transcription of the missing pass reproduces the shipped list **exactly**, and
  its instrument control shows the pass adds nothing on a concrete-tupleset schema.

### ⚠ THE TRAP — the honest fix makes part (iv) INERT

`W4Fragment.wsBare` is `∀ sh ∈ wildcardShapes S, sh.2 = BARE`. The through-shape's predicate
is `"viewer"`. So probe 4 `(4)` measures `wsBare` going **`true` → `false`** under the
corrected enumeration: a faithful fix makes `W4Fragment` reject `Sp` **via `wsBare`**, and
the `ttuStarFreeW` widening would then admit nothing new at exactly the schemas part (iv)
exists to admit.

**Fixing the model to match the shipped code and inhabiting the widening are, as things
stand, in tension.** That is the decision, and it is now measured rather than forecast.

### Two corrections to things this plan and `CORRESPONDENCE.md` assert

* ⚠ **The stratum-2 reader gap does NOT explain this divergence.** Probe 3 refutes it at
  `admin`, where `coveredFn` is `true` and `GraphModel.check` is the outlier. The recorded
  gap is real but shows up one level up, at `gate` (`coveredFn` `false` vs `sem` `true`) —
  the signature `CORRESPONDENCE.md:1213` describes. **Two defects, not one**; a session that
  "fixed `checkFn`" would not have closed the phantom-subject gap.
* The first `2026-09-14g` correction refuted `wsBare` as an excluder of `Sp`. That remains
  true **of today's tree** and becomes FALSE under route `D` — the two statements are about
  different `wildcardShapes`. Do not quote one without the other.

### Cost, and what is NOT established

* The `wildcardShapes` cone is **`235` references across `18` files** (as-of 2026-09-14g,
  `rg` over `formal/lean/ZanzibarProofs/`). Not a one-liner.
* `wildcardShapesFixed` lives **only in the probe**; the shipped definition is untouched and
  nothing is proved about the corrected version.
* **Whether `wsBare` can be soundly weakened to tolerate the through-shape — the obvious
  repair — is a proof-architecture question none of these probes answers.** It is the
  substance of the decision below.

### The routes, re-derived

| route | what it does | cost | what it gives up |
|---|---|---|---|
| **D1** | fix `wildcardShapes` **and** weaken `wsBare` to tolerate the through-shape | the `235`-ref cone + a `W4Fragment` field change + headline pins | nothing semantically, if the weakening is sound — **unproven** |
| **D2** | fix `wildcardShapes` only; accept that part (iv) is inert and close it as "not inhabitable" | the cone alone | the part (iv) goal |
| **D3** | leave the enumeration wrong; record the model≠code gap and pursue part (iv) otherwise | small | accuracy — conflicts with the user's 2026-09-14g steer |

Per the user's procedure (*measure the cone first, then if the decision isn't glaringly
obvious pass the decision off to fable*), the cone is measured and the choice is **not**
glaring: `D1` is what the accuracy steer points at, but its soundness is exactly the
unproven part. **Hand to `claude-fable-5`.**

---

## Corrections appended 2026-09-14g (second) — the A/A2/B/C MENU IS REFUTED; the gap is write-side

*supersedes:* the route table in the first `2026-09-14g` correction below, and
`formal/CORRESPONDENCE.md:1184`'s *"a project, not a step"* cost note.

The user's steer on the fork (verbatim, recorded on the row): *"i feel like i'd rather keep
things accurate but i'm not the expert. measure the cone first, then if the decision isn't
glaringly obvious pass the decision off to fable"*. Measuring first is what refuted the menu.

**READ, first-hand: `State.lean:589::GraphModel.probeDerived`'s userset-subject arm is
EDGE-FREE.** It contains no `σ.reach`; it answers from `res.upos` / `res.stars` / `res.neg`
symbolically. Its own docstring says *"A userset subject is edge-free"*. Routes **A** and
**A2** were both phrased as *"give the Lean model the symbolic residue read Python has"* —
**the model already has it**, so both were priced against a mechanism that is not real.

**PROBE, `formal/probes/p6_partiv_residue_locus_2026-09-14.lean` (rc=0, verbatim transcript
in its header).** At the divergent state:

| measurement | result |
|---|---|
| `(1)` `isDerived` at `access` / `admin` / `gate` | `false` / `true` / `true` |
| `(3)` residue at `(doc:d1, admin)` | `stars := []`, `neg := []`, `upos := [f2#viewer, f1#viewer]` |
| `(2)` shape of phantom vs control | both `("folder","viewer")` — **identical** |
| `(6)` `upos` phantom / `upos` control / `stars` has shape | `false` / `true` / `false` |
| `(I)` INSTRUMENT CONTROL — residue nonempty somewhere | **PASSED** (`admin`, `gate`) |

Since the two subjects **share a shape**, `res.stars.contains s.shape` is `false` for both
and could never have separated them; `upos` is what separates them. So the read path behaved
correctly on its input — **the CASCADE never folded the star shape into the derived residue's
`stars`.** The gap is write-side.

`(1)` also re-explains the headline asymmetry, more cheaply than the star-bridge story: the
"plain agrees, derived diverges" split is simply **two different read paths**. `access` is not
derived, so it takes `probeNonDerived`'s edge probe, which the star bridge serves; `admin` and
`gate` are derived, so they take the residue path, which is under-populated. `(8)` confirms
`(doc:d1, access)` has no residue at all.

### What this changes

* **Do not pick from the A/A2/B/C table below.** A and A2 do not describe real work; B and C
  were already weighed against the user's accuracy steer and lose.
* **The live route is new — call it `D`: make the cascade's star fold cover the
  star-tupleset through-shape at a derived relation**, so `stars` at `(doc:d1, admin)`
  contains `("folder","viewer")`. Coherence check (REASONED): `access(folder:*#viewer, d1)`
  holds via the `folder:*` parent and `banned` is empty there, so `admin` at the star subject
  is genuinely true — the shape *should* be in `stars`. Adding it also answers `f1`/`f2`
  true, which `upos` already does, so it does not over-grant at this store.
* ⚠ **`D`'s cone is UNMEASURED, and that is the next action.** This probe locates the gap; it
  does not price the fix, does not establish that the star fold *can* produce the shape here,
  and does not open `index_v4/wildcard.py::WildcardIndex._check_derived` to say which arm
  makes Python answer true. Per the user's procedure, measure that cone before deciding; hand
  the decision to `claude-fable-5` only if it is still not obvious afterwards.

---

## Corrections appended 2026-09-14g — STEP 0 IS ANSWERED, and the answer is none of its three options

*supersedes:* the `2026-09-14f` correction's *"the residue … is unexplained"* and its
enumeration of step 0 as `(1) / (2) / (3)`. The step-0 question is settled; what it settles
to is a **fourth** outcome the enumeration did not contain.

**The residual `2` is not new, and it is not about the fragment. It is the already-adjudicated
PHANTOM USERSET SUBJECT model gap** — `formal/CORRESPONDENCE.md:1162` §7, added `2026-09-13b`
by `P6` step 2 (READ). Same subject `folder:f9#viewer`, same derived relations `admin`/`gate`,
same asymmetry (the plain/TTU relation answers correctly and only the derived one diverges),
already measured **not a Python bug** and already carrying a gated pin.

### (2) is REFUTED — first-hand, and cheaply

READ, `formal/headline_statements.txt:30-36`. Every headline theorem
(`backend_equivalence`, `exclusion_effective`, `no_ghost_grant`, `graphRun_check_eq_sem`,
`graphModeAnswers_eq_sem`, `graphRunOps_check_eq_sem`) carries **exactly two** query
hypotheses:

```text
(hqs : q.subject.name = STAR → q.subject.predicate = BARE)
(hqo : q.object.name ≠ STAR)
```

The two divergent queries have `subject.name = "f9"` and `object.name = "d1"`, so `hqs` is
vacuous and `hqo` holds. **No headline hypothesis scopes a query to a materialised subject**,
and there is no third hypothesis to appeal to. Option (2) is dead as stated.

### (1) is REFUTED for the one field that could have carried it

REASONED then READ. Of `W4Fragment`'s 10 fields (`FullScope.lean:322`) only three are
store-dependent — `bareStar`, `ttuStarFree`, `term` — and the probe's `(8)` already measured
`bareStar` and `hterm` TRUE. A schema-side field cannot distinguish this store from one that
agrees, because **the divergence is not a property of the schema**: `(10)` materialises
`folder:f9` and the same schema goes to `0`.

⚠ The one candidate that looked live was `wsBare` (`∀ sh ∈ wildcardShapes S, sh.2 = BARE`) —
the hope being that the star through-shape registers as a non-`BARE` wildcard shape and
already excludes the store. **Checked and FALSE, before it was written down.** READ
`ReconcileStars.lean:97::wildcardShapes` collects `(r.1, r.2.1)` from restrictions whose
wildcard flag `r.2.2` is set; in `Sp` the only such restriction is
`("doc","parent") = .direct [("folder", BARE, true)]`, so `wildcardShapes Sp = [("folder", BARE)]`
and `wsBare` **holds**. The `[folder:*#viewer]`-shaped hope is not what this schema declares —
`isSubjectWildcardUserset "folder" "viewer"` is true at `(2)` for the star-TUPLESET reason,
not because a wildcard *restriction* was declared.

A census of Bool deciders (AGENT, `Explore`) reports **no decider at all** for any of the
seven schema-side fields, and none for `GraphAdmission.wf` / `ranked` / `storeValid` /
`ttuNotLeaf`. Measuring (1) exhaustively therefore means *writing* deciders. **That cost is
now unnecessary** — the argument above kills it without them, and the census is recorded here
so the next session does not re-commission it.

### What it actually is — MEASURED, not argued

`formal/probes/p6_phantom_subject_2026-09-13.py`, **re-run 2026-09-14g on today's tree**
(PROBE, literal stdout in the file's docstring and unchanged by this run): the same schema,
the same store and the same seven queries through `tests/parity.py::ParityEngine` (graph
index + both `SetOps` + the independent oracle, unanimity asserted internally) come back
**UNANIMOUS `True` on every one**, phantom and control alike.

⚠ The two situations really are the same, and that was checked rather than assumed (READ):
`Sp` and the Python probe's DSL schema agree relation-for-relation on all six definitions;
and the Lean measurement's store is `To = tObj :: T0 = [tObj, tPar, tView]` — **`tDom` feeds
only the query GRID, never the store** (`:194-201`) — so `folder:f9` is named by no stored
tuple on either side, exactly as the Python probe's comment claims for itself. The Python
store carries one extra tuple (`tSub`, on `doc:d2`) irrelevant to every `d1` query.

The mechanism is already written down at `CORRESPONDENCE.md:1170-1174`: `State.lean::
GraphModel.check` resolves a derived key **through materialised edges**, so it needs a node
where `index_v4/wildcard.py::WildcardIndex._check_derived` needs none — Python's userset arm
answers from the residue's `stars`/`neg`/`upos` symbolically. The plain relation agrees
because the star bridge serves it directly; the derived relation above it does not.

**This also explains the asymmetry `2026-09-14f` left open.** CONTROL 2 `(15)` — star USERSET
grant, derived above, same phantom subject, `mismatch := 0` — is not a counterexample to the
model gap: there the derived relation's grant arrives through a bridge that **materialises**,
so the Lean edge read finds a node. The gap needs star-TUPLESET *plus* derived-above *plus*
phantom subject. The phantom subject alone is not sufficient, which is why the currently
proved fragment is not already false.

### The fourth outcome, and what part (iv) now owes

Not (1), not (2), and not (3) either — **`TtuStarFreeW` does not need a conjunct, because the
store is not bad.** `Sp`/`To` is a legitimate store that the shipped system answers correctly.
What is wrong is the *Lean model's derived read*. So a store-side conjunct would exclude
stores the Python handles fine, which is the `CLAUDE.md` §"Who decides" failure mode pointed
the other way: narrowing the fragment to fit a model weakness rather than fixing the thing
that is wrong.

⚠ **But the flip is still BLOCKED, and for the original reason.** `GraphAdmission` +
widened `W4Fragment` would admit `Sp`/`To`, and at it `GraphModel.checkPublic σ q ≠ sem S T q`
for two in-scope queries — so `graphRun_check_eq_sem` would be **false**, not merely
unproven. That the shipped Python is correct does not rescue a Lean theorem about a Lean
model. `CORRESPONDENCE.md:1184` already forecast the cost of the other direction: closing it
*"would mean giving the Lean model a symbolic derived read, which is a project, not a step."*

**This is an executive decision — which of three sound designs, and whether the cone is worth
paying — and it is the case `CLAUDE.md` §"Who decides" reserves for a `claude-fable-5`
subagent.** The candidates, with what each costs and what each gives up:

| route | what it does | cost | what it gives up |
|---|---|---|---|
| **A** | Give `GraphModel`'s derived read the symbolic residue read Python has | **project** — `State.lean::GraphModel.check` is the subject of every headline theorem | nothing semantically; re-proves the world |
| **A2** | Narrow A: consult the residue **only** on the star-bridge path | ? — unmeasured, possibly M/L | less model↔code drift than B/C, but a special case in the model |
| **B** | Conjunct on `TtuStarFreeW` excluding phantom-subject stores | M, **moves the four audited names** at `audited_theorems.txt:537-540` | rejects stores the shipped system answers correctly |
| **C** | New query-scoping hypothesis on the headlines (subject's object is stored) | M, touches `headline_statements.txt` pins | weakens all six headline theorems, including where they are currently strong |

**Do not pay the part (iv) cone until this is chosen.** Steps 1-8 of `§ Ordered steps` are
unaffected in content and still correctly ordered *after* it; step 0 is no longer a
measurement, it is this choice.

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
