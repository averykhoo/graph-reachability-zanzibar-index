# `TK44` — census of the unreached generator pair cells

**FROZEN 2026-10-13, at `TK44`'s close (session 2026-10-12c) — provenance, not a living
document.** Status lines below are as-of-then and several may now be false; live state:
`HANDOFF.md` + the session ledger. Corrections are appended dated at the top, never edited
into the body. (Was ACTIVE-PLAN from 2026-10-12c, `docs/README.md` §3.) This is the
time-boxed census the `TK44` row asked for (2026-10-04 promotion). Every figure below was
measured on 2026-10-12/13 against `8a76ff4` plus this session's diff, and is true as of then
only. The live figure has ONE home,
`tests/test_generator_coverage.py::test_report_cell_coverage` (run it with `-s`). Live state
is the task row (`python scripts/task.py show TK44`), never this file.

Provenance labels: **READ** means first-hand, read or run by the census agent of session
2026-10-12c. **REASONED** means inferred from read code and not executed. **UNVERIFIED**
means a claim not yet checked. The probes were throwaway files in
`.scratch/uc-2026-10-12c/` (`tk44_probe.py`, `tk44_construct.py`, `tk44_extra.py`).
`.scratch/` is gitignored, so every number they produced is transcribed here, and §6 gives
enough of each recipe to rebuild it.

## Correction 2026-10-13b (review fix-2 agent, session 2026-10-12c; all READ unless labelled)

A second adversarial review found the fix-1 fence too coarse, plus record drift. Fixed in
the working tree, not yet committed:

* The fix-1 fence was a FAMILY rule, and the `ttu.ts:` family also holds legal features.
  Had a legal one such as `ttu.ts:owc` stopped being HIT while a witness still carried
  it, the fence would have filed it as refused-only and passed.
  `test_refused_only_features_are_tupleset_shapes` now also requires that every witness
  carrying a refused-only feature refuses with a tupleset-shape message
  (`genswarm.TUPLESET_MUST_BE_DIRECT`, `TUPLESET_NO_USERSET`, or the new
  `genswarm.DANGLING_REFERENCE`). Sabotage: no tupleset is object-wildcarded in
  `witness`. The new assertion goes red, reporting `[('ttu.ts:owc',
  ['owc-on-a-ttu-tupleset'])]`. The pre-fix-2 test passes under the same sabotage. The
  literal output is in the test docstring. **Residual, stated in the docstring:**
  `ttu.ts:Union` and `ttu.ts:multitype` are legal but carried only by TK106 witnesses, so
  only the zero-headroom HIT floor would catch them going un-HIT (REASONED).
* `genswarm.witness` `ts_wildcard` comment: the untainted referent is `r15`, not `r0`.
* The row title no longer quotes the residue count, because the GC-1 rule in the
  `test_generator_coverage.py` module docstring says it lives only in
  `test_report_cell_coverage -s`. The row's dead Read-first pointers
  (`sabotage-procedure.md:482-487`, `test_generator_coverage.py:257`) now cite a section
  and a symbol.
* Not fixed, out of scope, already disclosed in the test: removing the all-ON stratum of
  `swarm_subset` (586 -> 559 at deep) is caught by neither swarm floor.

## Correction 2026-10-13 (review fix-1 agent, session 2026-10-12c; all READ unless labelled)

An adversarial review of the implementation below found doc drift and one unfiled red.
Fixed in the working tree, not yet committed:

* `tests/genswarm.py::witness` docstring said the second untainted referent was `r0`;
  the code uses a fresh `r15` through `parent2` (r0 feeds the derived r8). Docstring fixed.
* `tests/test_generator_coverage.py` `ENUM_K` comment: re-measured with
  `genswarm.enumerate_configs` at **171 configs at K<=2, 987 at K<=3, 18 switches** (was
  the pre-TK44 136 / 696).
* Floor provenance: the WHOLE TK44 change is **+56 cells at ci, +40 at deep** (8a76ff4's
  genswarm: 685 at K<=2, 701 at K<=3, 760 with witnesses; this tree 741 / 741 / 816). The
  "20 cells" figure is the second-referent wiring alone. Gain over baseline is now
  816/514 = 1.59; `_MIN_GAIN_OVER_BASELINE` stays 1.4 (the 816 floor is the binding pin).
* The refused-only class only checks "witnessed, never HIT"; it does not prove a feature
  is refused wherever it occurs. New fence
  `test_generator_coverage.py::test_refused_only_features_are_tupleset_shapes`: every
  refused-only feature must be a `ttu.ts:` / `ttu.ts.restr:` shape. Sabotaged red by
  disabling the wildcard-userset arm in `witness` (`['restr:wildcard-userset']` reported).
  Under that same sabotage the gap and alphabet tests stayed green.
* The deep swarm floor in `test_swarm_campaign_reaches_cells_and_never_starves_a_switch` was
  RED under `HYPOTHESIS_PROFILE=deep` before TK44 (8a76ff4: 592 against 670), and TK44 made
  it 586. Re-based to **527** (about 10% under 586) with provenance in the test. ci is 529
  against a floor of 430.
* Row title retitled to a dated count (no percentage) via `task.py set TK44 title`.

## Implementation, re-measured (2026-10-12c, implementing agent; NOT yet committed)

Everything here was run first-hand (READ) on 8a76ff4 plus the uncommitted TK44 edits to
`tests/genswarm.py` and `tests/test_generator_coverage.py`, unless labelled otherwise.

**Live figures (READ, `test_report_cell_coverage -s`, 2026-10-12c), `ci` (K<=2) and
`deep` (K<=3) identical:** HIT **741**, +REJ **816 / 1128**, UNKNOWN **312** = refused-only
312 + gap **0** + other **0** (9 refused-only features). Before (same instrument, 8a76ff4):
`ci` 685 / 760 / 368, `deep` 701 / 776 / 352. So class G is 0 at `ci`, class K (the 16
`deep`-only cells) is closed too (`ci` now reaches what `deep` does), and the 4
`test_hypothesis`-only cells are reached by the enumerator itself.

**Two deviations from the Decision's work list, both forced by measurement (READ):**
1. **The second referent is a fresh `r15: [user]`, not `r0`.** With `body_boolean` on, `r0`
   feeds the derived `r8`, so an object wildcard on `(doc, r0)` is refused ("object-wildcard
   shape (doc, r8) expands onto the compiled leaf predicate (doc, r8.1) ..."), and the
   `{body_boolean, owc}` config became an UNMATCHED refusal. `r15` feeds nothing derived.
   `parent2: [doc]` (+ `doc:*` under `ts_wildcard`) and `r10: r15 from parent2` as planned.
2. **A new witness-only switch, `derived_star` [expect REJECT].** At K<=2 the four
   decision-15 scope refusals (`dependency cycle`, `derives the wildcard userset shape`,
   `wildcard userset restriction`, `is the tupleset of TTU`) were produced ONLY by the
   `{body_boolean, star-ish}` pairs (`is the tupleset of TTU` also by `{body_negttu, owc}`).
   Re-wiring those pairs alone would make
   `test_every_rejection_witness_family_is_actually_exercised_by_the_enumerator` call the
   families stale. `derived_star` taints `r1` and keeps the shared-referent wiring, so
   `{derived_star, X}` proves each refusal live, as `ts_undeclared` / `ts_userset` do.
   `split` in `genswarm.witness` = `body_boolean` and not `derived_star`.

**Also landed:** `body_ttu` added to `SWARM_SWITCHES` with its own witness arm
(`r14: [user] or r1 from parent`); `body_userset` adds an always-tainted referent
(`r13: [user] but not r0`, `r12: [user] or [doc#r13]`, item 3). K<=2 config space 136 -> 171,
accepted 73 -> 100.

**The new configs are DRIVEN (READ, probe `tk44_drive_probe.py`):** driving all 100
accepted K<=2 configs as `_sweep` does (k=2, seed=7): sparse 100/100 driven, 81 906
comparisons; dense 100/100, 75 495 comparisons; all 56 gained cells driven in both
regimes; **0 divergences** (no ParityEngine disagreement, so no Python bug to file).
No new relation is cut by `drive_config`'s `pool_cap` (24).

**Checks (all sabotaged, literal output in the docstrings/comments):**
* `test_enumerator_cell_coverage_floor`: floors raised to the measured 741 / 741 / 816,
  ZERO headroom, because reverting the second-referent wiring alone (`split = False`)
  gives 721 / 796, inside the old ~5% margin. Red at `ci` and `deep`: "721/1128 is below
  the floor 741".
* NEW `test_every_pair_of_hit_features_is_reached_together` (class G == 0, derived via
  `_unknown_classes`): same sabotage gives "20 cell(s) pair two features the enumerator
  HITs, but never in one config".
* NEW in `_assert_non_vacuous`: every compiling K<=DRIVE_K config is driven. Sabotage
  (`drive_config` empty pool for 9+ relations) gave "sparse: 5 config(s) COMPILE but were
  never driven"; the three older non-vacuity floors stayed green.
* `test_report_cell_coverage` prints UNKNOWN split into refused-only / gap / other,
  computed by `_unknown_classes` from the HIT set and `rejection_features()`; no list.

**Targeted runs (READ, 2026-10-12c, `ci`):** `tests/test_generator_coverage.py` 34 passed
in 156.6 s (34 collected; one new test). `tests/test_hypothesis.py`, `tests/test_matrix.py`
and the four other `genswarm` importers (`test_tk95_truncated_fanout_rollback`,
`test_star_admitting_intersection`, `test_lookup_oracle`, `test_schema_shapes`): 140 passed
in 318.9 s. The first coverage run caught one KeyError in
`test_non_vacuity_floors_fire_when_the_comparison_set_is_emptied` (its hand-built reports
lacked `undriven`); fixed, and that test gained an in-code control (2b) for the new check.
The full gate has NOT been run.

**Item 8 was already done** (READ): the four prose percentages were deleted on 2026-09-10
(`GC-1`); see the module docstring of `tests/test_generator_coverage.py` and
`docs/sabotage-procedure.md` § "What this procedure cannot do". Nothing left to strip.
The row's TITLE still says "~30%".

**`ttu.ts:tainted` (READ, `tk44_taint_probe.py`):** `compute_taint` on
`parent: [doc, doc:*] or [doc]` with a tainted target `r1` taints `r1`, `r2`, not `parent`.

**Swarm (READ, instrument-specific):** 120 draws 518 -> 529; 400 draws 592 -> 586.
⚠ PRE-EXISTING, not caused here: the `deep` swarm floor in
`test_swarm_campaign_reaches_cells_and_never_starves_a_switch` is 670, but 8a76ff4 itself
measures 592 at 400 draws, so that test is RED under `HYPOTHESIS_PROFILE=deep` (the gate
runs `ci`). Not lowered here; it needs its own reviewed edit.

## Decision (2026-10-12c, executive, per CLAUDE.md "Who decides")

Read first-hand before deciding: `task.py show TK44`, this census, `tests/test_generator_coverage.py::test_report_cell_coverage` and `::test_rejection_witness_is_still_refused` (the exemption argument), `tests/genswarm.py` section 5 header (witness contract), the TK77 close. The census agent's numbers are taken as evidence; the class boundaries below are DERIVED by the test, not restated from the census, so no census figure becomes a pin.

**The goal is graph index == set engine, and an unreached pair cell only matters if an input in it can reach the evaluators.** That splits the 348 cleanly:

1. **Class G (36, reachable) -- ATTACK NOW by widening the generator** (section 5 items 1 and 2: a second untainted referent `r0` / `parent2: [doc]` in `genswarm.witness` for the `owc`, `self_ttu`, `body_wc_userset` arms when `body_boolean` is on, plus a star `parent2: [doc, doc:*]` arm over `r0`). Why: one wiring bug, a few lines, and the new configs are then DRIVEN through ParityEngine by the sparse/dense sweeps, which is the only thing that buys equivalence evidence. owc beside a derived TTU sits next to the I14 / crossing territory where TK77 and TK118 found real bugs. The value is the drive, not the count: a compiled-only reach does not count.
2. **Class K (16, `deep`-only) -- ATTACK in the same change** (item 3, `body_userset` reaching a derived referent at K<=2) if it is the same kind of referent edit; otherwise it is the single follow-up, not residue. The 4 `test_hypothesis`-only cells stay as they are: that instrument is already in the gate.
3. **Dead `body_ttu` arm -- FIX NOW by ADDING `'body_ttu'` to `SWARM_SWITCHES`**, not by deleting the branch: a switch in the grammar but absent from the tuple is exactly what `test_every_switch_moves_the_cell_histogram` cannot see, and positive TTUs in swarm bodies are more reach. Floors are re-measured afterwards (the derandomized swarm draw changes with the switch tuple; instrument caveat in section 1).
4. **Class S (312) -- NOT attacked. Converted to a DERIVED class in `test_report_cell_coverage`** (item 5): "pairs with a feature carried only by parse-refusal witnesses", computed from `REJECTION_WITNESSES` and the HIT set, the same way `UNACCOUNTED` is. Why not witnesses: S2 (180) can never be witnessed (a refused schema has no compiled features), and S1/S3 witnesses would add no input class, only cosmetics. Why this is not the forbidden exemption list: nothing is written down by hand; the moment any generator HITs one of the nine refused-only features, or a witness stops being refused (`test_rejection_witness_is_still_refused`), its cells leave the class and reappear as UNKNOWN. The `ttu.ts:tainted` entry is REASONED in the census; the derived class does not depend on that reasoning, so no first-hand check is needed to ship it, but the implementer runs a one-line `compute_taint` probe on a directs-only tupleset and records it before naming it in prose.
5. **Published residue after the change:** the S line (derived, labelled "no accepted schema can carry both features", which is a different statement from "blind spot"), plus whatever true UNKNOWN remains, quoted from the `-s` run with its date. The raised floor in `test_enumerator_cell_coverage_floor` is the positive pin; `test_report_cell_coverage` stays a report, not an assertion.
6. **If a newly driven config makes ParityEngine disagree, that is a Python bug** (CLAUDE.md "Who decides"): file a row, positive pin, never an xfail, never drop the config.

### Work list (for the implementing agent)

1. `tests/genswarm.py::witness`: second untainted referent (`r0`, `parent2: [doc]`) for `owc`, `self_ttu`, `body_wc_userset` when `body_boolean` is on; star `parent2: [doc, doc:*]` arm over `r0` (census section 5 items 1-2).
2. `tests/genswarm.py::SWARM_SWITCHES`: add `'body_ttu'` (item 4); keep the branch.
3. `witness`: let `body_userset` reach a derived referent at K<=2 (item 3) if it is the same shape of edit; else leave as the one follow-up, named on the row.
4. Confirm first-hand that the sparse/dense sweeps DRIVE every new config through ParityEngine (not compile-only); run them, `tests/test_hypothesis.py` and `tests/test_matrix.py` green.
5. Re-measure with `test_report_cell_coverage -s` (ci and deep), raise `test_enumerator_cell_coverage_floor` and any `_BASELINE_CELLS`-style figure to the live values with the date and commit.
6. SABOTAGE: revert step 1 alone, watch the raised floor go red, record the literal output in the floor test's docstring and the commit message.
7. `test_report_cell_coverage`: split UNKNOWN into the derived class S line and the rest; no literal cell or feature list anywhere.
8. Prose: strip the percentages at `tests/test_generator_coverage.py` :68 / :428 / :1152 and `docs/sabotage-procedure.md` ~:643 ("roughly a quarter"); point at the `-s` run. Fix the row's dead "Read first" pointer (:482-487 -> the live paragraph) via `task.py comment`.
9. Append the re-measured figures, dated at the top, to this census doc; `task.py comment TK44 --session <key>` with LANDED / BUILDS / RED / next; freeze this doc and close TK44 once G is 0 at `ci` and S is reported derived.
10. Run the full gate; commit by path.

## 0. Headline

* **The row's denominator is stale.** It quotes 891 of **1275**. `TK107` (2026-10-05)
  removed three compiled features, so the alphabet is now **48 features**, which gives
  **1128 pair cells**. This is asserted by
  `tests/test_generator_coverage.py::test_every_derivation_is_nonvacuous_and_matches_its_recorded_provenance`.
  (READ)
* **Reach measured 2026-10-12 with `test_report_cell_coverage -s` (READ):**
  `ci`: HIT 685, +REJ **760/1128**, UNKNOWN 368.
  `deep`: HIT 701, +REJ **776/1128**, UNKNOWN 352.
  Taking the union of every generator in the repo (§1) gives **780/1128**, which leaves
  **348 UNKNOWN**.
* **Of those 348, 312 cannot be generated at any budget. They are not untested input
  classes.** In each one, one of the two features is excluded from every *accepted*
  schema by a parse refusal (`TK106` / `TK108` / `ASK-1`, §2). 180 of the 312 cannot even
  be *witnessed*: a refused schema has no compiled artifacts, so a cell that pairs a
  refused-only feature with a compiled-only feature describes a config that cannot exist.
* **The remaining 36 are real generator gaps, and all 36 are reachable.** Six hand-built
  schemas that the compiler accepts reach every one of them (§3). They share **one
  cause**: `tests/genswarm.py::witness` wires every switch arm to the same `r1` / `parent`.
  `body_boolean` is the only source of taint, so it collides with every star-ish or owc
  switch, and the compiler refuses the combined config.
* **Answer to the row's open question (REASONED, a recommendation):** the residue is
  worth attacking. Attacking it is cheap and bounded: 36 cells, one wiring change. The
  312 should be **reported as their own class**, derived mechanically, and never listed
  by hand, rather than shown as UNKNOWN. §5 says how without minting an exemption list.

## 1. Sources and what each one reaches (READ, 2026-10-12, `8a76ff4`)

| source | cells | note |
|---|---|---|
| enumerator K<=2 (`ci`, compile-only) | 685 | `_enumerate(2)` |
| enumerator K<=3 (`deep`) | 701 | |
| enumerator over the FULL 2^16 switch space | 701 | 1663 of the 65535 configs compile. **K<=3 saturates the enumerator**; widening it buys nothing. |
| rejection witnesses (`genswarm.rejection_explained_cells`) | 191 | |
| swarm, 120 derandomized draws | 463 | adds 0 to 4 cells over enumerator+REJ, depending on the seed (instrument caveat below) |
| swarm, 400 draws | 547 | adds **0** over K<=3+REJ |
| `tests/test_hypothesis.py::_schema_ast`, `_RandomChoices`, seeds 7/19/31/43/59 x 400 (1654 compiled) | 590 | adds **4** over everything else: `ttu.ts.restr:subject-wildcard` x {`family:userset-storage`, `leaf:derived-userset`, `plan:PDerivedUserset`, `via:userset`} |
| **union of all of the above** | **780** | UNKNOWN **348** |

`ci` also misses 16 cells that the `deep` enumerator reaches: {`family:userset-storage`,
`leaf:derived-userset`, `plan:PDerivedUserset`, `via:userset`} x {`restr:subject-wildcard`,
`schema:multi-type`, `ttu.ts:Union`, `ttu.ts:multitype`}. The derived-userset arm needs the
TRIPLE {`body_boolean`, `body_userset`, X}, and `DRIVE_K` / `ENUM_K` at `ci` stop at pairs.
(READ)

⚠ **Instrument caveat (READ).** The swarm's derandomized draw depends on the wrapping
function, because hypothesis derives the seed from it. Two probe wrappers therefore
measured `ci`+swarm120 as 764 and as 760. Any swarm cell count is specific to one
instrument. The enumerator figures are RNG-free and do not have this problem.

## 2. Class S: structurally impossible (312 cells)

Nine features are carried only by rejection witnesses. No accepted config HITs them:
`ttu.ts:Computed`, `ttu.ts:Exclusion`, `ttu.ts:Intersection`, `ttu.ts:TTU`,
`ttu.ts:neg-only-type`, `ttu.ts:tainted`, `ttu.ts:undeclared`,
`ttu.ts.restr:userset`, `ttu.ts.restr:wildcard-userset`. (READ, measured)

Why each one is impossible, not just unreached:
* `src/zanzibar/schema/parser.py::_validate_tuplesets_direct` refuses any tupleset body
  that is not directs-only. That rules out Computed, TTU, Intersection and Exclusion.
  `neg-only-type` needs an Exclusion, so it is ruled out too. The same function refuses
  any `#pred` restriction on a tupleset, which rules out `restr:userset` and
  `restr:wildcard-userset` (`TK108`). (READ)
* `src/zanzibar/schema/parser.py::_validate_ast_consistency` refuses a dangling
  tupleset (`ASK-1`), which rules out `ttu.ts:undeclared`. (READ that the symbol exists.
  The refusal is pinned by the `dangling-reference` witness.)
* `ttu.ts:tainted`: a directs-only tupleset has no boolean operator and, after `TK108`,
  no relation reference, so `compute_taint` cannot taint it. CLAUDE.md states the same
  ("a tupleset is never tainted"). (REASONED)

| sub-class | cells | can a witness explain it? |
|---|---|---|
| S1: both features refused-only | 30 (of the C(9,2)=36 pairs; 6 are already witnessed) | yes, with a combined witness. Cosmetic: no new input class. |
| S2: refused-only x compiled-only (`plan:` / `leaf:` / `via:` / `family:` / `schema:{neg-leaf,storage-leaf,multi-stratum}` / `ttu.target:tainted`) | **180** | **no**. `_witness_features` gives a refused schema only its AST features, plus `ttu.ts:tainted` for `TK106` refusals. |
| S3: refused-only x an AST-level feature | 102 | yes, with richer witnesses. Cosmetic as well. |

These 312 cells are not a blind spot in the sense `docs/sabotage-procedure.md` means: no
input in them can reach the evaluators. Each feature on its own is already accounted for
by `test_every_alphabet_feature_is_hit_or_rejection_explained`. (REASONED)

## 3. Class G: generator gaps (36 cells, all reachable)

Both features of every cell here are individually HIT. They are just never HIT together.
Side A is a derived-target feature: {`family:userset-storage`, `leaf:derived-ttu`,
`leaf:derived-userset`, `plan:PDerivedTTU`, `plan:PDerivedUserset`,
`ttu.target:tainted`, `via:ttu`, `via:userset`}. Side B is a star-ish feature:
{`schema:owc`, `ttu.ts:owc`, `ttu:self-target`, `restr:wildcard-userset`,
`ttu.ts.restr:subject-wildcard`}. Not all 40 of the 8x5 combinations are gaps: the 4
reached by `test_hypothesis` (§1) are excluded, which leaves 36. (READ)

**The cause (READ, `genswarm.witness`).** `r1` is tainted only by `body_boolean`, and every
other switch points its arm at `r1` or at `parent`. The pair configs are refused:
* {`body_boolean`, `owc`}: `UnsupportedByGraphIndex` "('doc','parent') is the tupleset of
  TTU 'r1 from parent' in derived relation doc#r2";
* {`body_boolean`, `self_ttu`}: `CyclicDerivedDependency`;
* {`body_boolean`, `body_wc_userset`}: "wildcard userset restriction [doc:*#r1] over the
  derived relation";
* {`body_boolean`, `ts_wildcard`}: "star tupleset [doc:*] on 'parent' derives the
  wildcard userset shape (doc, r1)".

These are correct refusals of the *same-referent* shape. The *different-referent* shape
is legal, as the next part shows.

**Constructive check (READ, `tk44_construct.py`).** The base schema is
`r1: [user] but not blk`, `r2: r1 from parent`, `r5: [user] or [doc#r1]`. Each variant
below adds one more relation or one owc set, every variant **compiles**, and together
they reach **36/36**:

| variant | adds | C5 cells reached |
|---|---|---|
| owc on a second tupleset | `parent2: [doc]`, `r3: r0 from parent2`, owc {(doc,parent2)} | 16 |
| owc on a plain relation | owc {(doc,r0)} | 8 |
| self-TTU on an untainted relation | `parent2: [doc]`, `r4: [user] or r4 from parent2` | 8 |
| self-TTU, same tupleset | `r4: [user] or r4 from parent` | 8 |
| wildcard userset on an untainted relation | `r6: [user] or [doc:*#r0]` | 8 |
| star second tupleset | `parent2: [doc, doc:*]`, `r3: r0 from parent2` | 4 |

The variants overlap, which is why their counts sum past 36. These schemas have been
**compiled, not driven** (UNVERIFIED: whether ParityEngine constructs and agrees on them).
Driving them is the actual value of closing the gap. Several of them, owc beside a derived
TTU in particular, are next to I14 / crossing territory (`TK77`), where real bugs have
been found before.

**Second finding, a dead arm (READ).** `genswarm.swarm_schema_asts` tests
`'body_ttu' in sw` (`tests/genswarm.py`, line 456 as of 2026-10-12), but `'body_ttu'` is
**not** in `genswarm.SWARM_SWITCHES`. The swarm's positive body-TTU arm is therefore dead
code. The swarm reaches TTUs only through `body_negttu` and `self_ttu`. The enumerator
is unaffected, because `witness` makes its positive TTU unconditional. A switch that
exists in the grammar but not in the switch tuple is exactly what
`test_every_switch_moves_the_cell_histogram` cannot see.

## 4. Counts per class (2026-10-12, `8a76ff4`)

| class | every-source UNKNOWN (348) | `ci` report UNKNOWN (368) |
|---|---|---|
| S1 refused-only x refused-only | 30 | 30 |
| S2 refused-only x compiled-only | 180 | 180 |
| S3 refused-only x AST feature | 102 | 102 |
| G generator gap (both HIT, never together) | 36 | 40 |
| K reached only at K<=3 | (0, reached) | 16 |
| **unknown, no explanation** | **0** | **0** |

## 5. The cheapest generator changes that close whole classes (REASONED, not yet done)

1. **Give `witness` a second, untainted referent for the star-ish arms.** Point
   `owc`, `self_ttu` and `body_wc_userset` at an untainted relation (`r0`, plus a
   `parent2: [doc]` tupleset for owc and self-TTU) whenever `body_boolean` is on, instead
   of dropping or refusing the arm. This closes 32 of the 36 G cells at K<=2: those are the
   cells the first five variants in §3 reach. The star variant is the only one that
   carries `ttu.ts.restr:subject-wildcard`, which accounts for the other 4. Cost: a few lines in `witness`. Each new config is also
   driven by the sparse and dense sweeps, which is the real gain.
2. **A `ts_wildcard` arm on a second tupleset (`parent2: [doc, doc:*]` over `r0`).** This
   closes the last 4 G cells (subject-wildcard tupleset x derived TTU) without the
   refused star-over-derived shape.
3. **Make `body_userset` reach a derived referent at K<=2** (for example, let
   `body_userset` taint its own referent). This moves the 16 K-cells into `ci`, so `ci`
   reaches what `deep` reaches today. Optionally do the same for the 4
   `test_hypothesis`-only cells (star tupleset x derived userset), so the gate's own
   instrument reaches them.
4. **Fix the dead `body_ttu` arm.** Either add `'body_ttu'` to `SWARM_SWITCHES`, which
   grows the enumerator's config space and needs a fresh floor measurement, or delete
   the dead branch. The first is better: the swarm then draws positive TTUs in bodies.
5. **Report class S separately, derived, with no list.** Split `test_report_cell_coverage`'s
   UNKNOWN line into "pairs with a feature carried ONLY by parse-refusal witnesses" and the
   rest. The split is computed from `REJECTION_WITNESSES` and the HIT set, the same way
   `UNACCOUNTED` is. The guard that keeps it from becoming the forbidden exemption list is
   that the set is *derived*: if a generator ever HITs one of the nine features, its
   cells leave class S automatically. Closing S1/S3 with combined witnesses is possible
   but cosmetic, and is **not** recommended. S2 cannot be closed by any witness.

**Trap reminder from the row:** none of this adds an `EXPECTED_UNREACHABLE` list. Items 1
to 4 *reach* cells, and item 5 only *labels* a derived set. Re-measure after each change
and quote the result with its date.

## 6. Recipes (enough to rebuild the scratch probes)

* `tk44_probe.py`: computes `_enumerate`-equivalent cell sets at K=2, K=3 and K=16 over
  `genswarm.witness`, the swarm (`genswarm.swarm_configs`, derandomized, 120 / 400 draws,
  `phases=[Phase.generate]`), and `test_hypothesis._schema_ast(_RandomChoices(Random(s)))`
  for 5 seeds x 400. It unions these with `genswarm.rejection_explained_cells()` and
  classifies each `universe - union` cell. A feature counts as refused-only if a witness
  carries it and no compiled config does. A feature counts as compiled-only if
  `ast_features` can never emit it. Run time about 2 min with `PYTHONPATH=".;src"`.
* `tk44_construct.py`: `genswarm.features(schema, owc)` over the six §3 variants,
  intersected with the G set.
