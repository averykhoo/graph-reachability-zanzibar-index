---
id: TK77
title: the matrix and hypothesis campaign have ZERO reach into the _sync_entity_middles surface
brief: genswarm+hypothesis arms DONE 2026-09-19e: EFF 0->46/74, _sync/EFF 0->8; left = genswarm Diff has no remove op
pri: NOW
size: M
deps: []
related: [TK75, TK44, TK83]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-18
moved: 2026-09-19f
updated: 2026-09-19f
closed: 2026-09-19f
---

I14 crossing middles -- the `w_all -> concrete -> w_any` crossing the graph index maintains
per live entity -- can only be exercised by a schema whose `crossable_shapes` is non-empty,
and a schema is crossable-capable only if it carries a TTU over a `[S:*]`-admitting tupleset
whose target relation is also an object-wildcard shape. That two-feature conjunction is rare
enough that the two mechanisms this repo relies on to find semantic divergence barely reach
it: the validation matrix reaches it **zero** times (no fixture it uses can be made crossable
by any argument -- not a configuration miss, a structural one) and the hypothesis campaign
reaches it in well under 1% of draws. The REMOVE half of the surface,
`_sync_entity_middles`, is covered by exactly one hand-written, non-differential, un-fuzzed
module in the whole suite. That matters because a surface the differential net cannot reach
is a surface where the graph index and the set engine can disagree indefinitely, and I14 is
precisely the area that produced `TK69`, `TK70` and `P22`. The item is to give that surface a
crossable fixture (and/or the one-line generator fix) so the matrix and the campaign cover
it, with the census probe's `_sync ... EFF` count as the acceptance check.

## Traps

- A RAW call count of `index_v4/wildcard.py::_ensure_entity_middles` or
  `::_sync_entity_middles` is NOT reach. Both return at a guard when `crossable_shapes` is
  empty and both are called unconditionally, so a module with zero crossable schemas still
  books hundreds of calls (measured 2026-09-19c: 7408 raw vs 257 effective). Count the calls
  that get PAST the guard, and carry a ceiling control so a zero reads as "never reached"
  rather than "instrument dead".
- An empty `crossable_shapes` is a SILENT no-op, so a new fixture that fails to be crossable
  passes every test it is added to and looks like coverage. Do not accept a green as evidence
  here; read the `_sync ... EFF` count.
- Do NOT re-use this row's 2026-09-18 or 2026-09-19b counts. Both are superseded by the
  first-hand census, which contradicts the 2026-09-18 ones outright; the 2026-09-19b "7"
  is unexplained. Re-measure with the probe.

## Read first

- [`docs/tk77-crossable-census-2026-09-19.md`](../docs/tk77-crossable-census-2026-09-19.md)
  -- the census (ACTIVE-PLAN): which corpora can reach I14 at all, why the `OBJECT_WC`
  option is structurally closed, and the two points on which it CONTRADICTS this row.
- [`formal/probes/tk77_crossable_census_2026-09-19.py`](../formal/probes/tk77_crossable_census_2026-09-19.py)
  -- the tracked probe reproducing every figure in it, incl. the live pytest-plugin census,
  its ceiling control, and the sabotage that proves the EFF columns read the guard.

## Log

### 2026-09-18

AGENT-MEASURED, independently confirmed by two agents from opposite directions (a census sweep and a coverage probe); NOT re-run first-hand here, so treat the counts as evidence and re-measure before quoting them.

`tests/test_matrix.py`, `tests/test_hypothesis.py`, `tests/test_wildcard_property.py` and `tests/test_zt_p5_readjudication.py` -- **66 tests, 4m37s -- produce an EMPTY `_sync_entity_middles` census.** Not "few hits": **zero** calls on a crossable-type entity.

CAUSE: `tests/fga_schemas/wildcards.fga` and `tests/fga_schemas/boolean_wildcards.fga` both compute `crossable_shapes == []` under the matrix's `OBJECT_WC`. Crossability needs a shape bridged IN *and* OUT; these are bridged OUT only. Coverage of this surface exists ONLY in `tests/test_i14_crossing_middles.py`, `tests/test_owc_star_parent_cross.py` and `tests/test_bulk_build.py` -- three hand-written modules, none of them differential and none of them fuzzed.

(!) **CORROBORATION FROM A SECOND DIRECTION, first-hand (this session, on `TK72`):** both ZT-P5 object-wildcard corpora also measure `crossable_shapes: []`, including the TTU one with `[user, user:*]`. **A subject wildcard does NOT create an in-bridge.** So the "it looks like an object-wildcard schema, therefore it exercises the crossing machinery" inference is wrong in at least four fixtures, and it is why `TK75` sat without a witness.

WHY IT MATTERS: the validation matrix and the hypothesis campaign are the two mechanisms this repo relies on to find semantic divergence. A surface they structurally cannot reach is a surface where the graph index and the set engine could disagree indefinitely -- and I14 / crossing middles is exactly the area that produced `TK69`, `TK70` and `P22`.

FIRST ACTION: measure `crossable_shapes` for every fixture in `tests/fga_schemas/` and publish the table (which fixtures are crossable at all, under which `object_wildcard_shapes`). That is cheap, it is the thing nobody has, and it decides whether the fix is a new matrix fixture or a generator change. Related: `TK44` (the unreached generator pair-cell space) may share a cause.

### 2026-09-19b

INHERITED FROM `TK75` (closed 2026-09-19b): this row now owns the re-add-arm fixture question, and it has a first-hand measurement to start from.

Census run first-hand 2026-09-19b over exactly the three modules this row names as the only coverage of the crossable surface -- `tests/test_i14_crossing_middles.py`, `tests/test_owc_star_parent_cross.py`, `tests/test_bulk_build.py`, run together: **7 `_sync_entity_middles` calls in total, 1 of them inside a reconcile-time GC, and that one takes the STRIP arm.** The in-GC RE-ADD arm (`_ensure_entity_middles`, the witness-survives branch) is reached **zero** times by any of them. Two of the three modules make no `_sync_entity_middles` call at all -- the count is identical whether the run is all three or `test_i14_crossing_middles.py` alone.

That tightens this row's claim in a useful direction: it is not only that the matrix and the hypothesis campaign cannot reach the crossable surface, it is that the three hand-written modules that CAN reach it exercise one branch of one function once. So the deliverable is the same fixture work this row already names, and the re-add arm is a concrete acceptance target for it.

(!) The ceiling control on that census was LEFT-ARMED and must not be read as a null result: the arm that punches an I14 hole before the real call never fired (`holes=0`) because `_entity_has_witness` was never true in-GC. The measurement supports "not REACHED", not "reached and emits nothing". The 2026-09-18 "269 in-GC re-add calls, every one emitting zero rows" figure on `TK75` was over a wider run and stays AGENT-MEASURED -- re-measure before quoting it.

`TK75` decided the re-add arm gets a RECORDED NEGATIVE rather than a forced-strip control test, on the grounds that such a test would pin a fixture invented for the probe and assert behaviour on a store state I14 forbids. That decision is reversible here once a real crossable fixture exists. The strip arm itself is now pinned: `tests/test_i14_crossing_middles.py::test_the_strip_arm_emits_from_inside_a_reconcile_time_gc` (3 rows, nesting `cascade=1 reconcile=1 gc=1`, and the honest rider that those rows map to no derived key so `_settle is None`).

### 2026-09-19c

FIRST ACTION DISCHARGED, first-hand. The census this row asked for is published as
docs/tk77-crossable-census-2026-09-19.md (ACTIVE-PLAN), reproduced by the tracked probe
formal/probes/tk77_crossable_census_2026-09-19.py. Read the doc before this row: it
CONTRADICTS the row on two points.

WHAT LANDED. (1) The structural result: a schema is crossable-capable iff it carries a TTU
whose tupleset relation admits a bare object star [S:*] AND the TTU's target relation is a
declared-or-expanded object-wildcard shape. The other producer of an in-bridge -- a literal
T:*#p wildcard-userset restriction -- is CATEGORICALLY excluded, because
zanzibar_utils_v1.py::_reject_doubly_bridged_shapes refuses to let that same shape also be an
object wildcard. (2) Fixture census: 1 of 15 tests/fga_schemas/ fixtures is crossable-capable
(owc_star_ttu). 13 have an empty bridged_in_shapes, so NO object_wildcard_shapes argument of
any value can make them crossable; wildcards.fga and wildcard_userset_cross.fga are
compile-REFUSED with DoublyBridgedShapeError if you try. (3) Conformance: 0 of 26 schemas in
test_conformance_enum.SCHEMAS -- including 'object_wildcard', which declares an owc and still
has in=0. (4) genswarm: 0 of 65535 witness configs, CLOSED and RNG-free, and the cause is one
line -- witness() hardwires owc to ('doc','parent') while its through-shape is ('doc','r1'),
disjoint by construction. (5) test_hypothesis.py::star_bridge_configs IS crossable-capable:
24 of its 224-config closed domain, ALL of them in the self-referential A==B arm added for
ZT-P5-NEW on 2026-07-26. That arm is the only crossable generator in the repo.

SO THE MENU IS DECIDED: the fix is a NEW fixture (or the one-line genswarm change), never an
OBJECT_WC parameter edit. That option is structurally closed.

TWO CONTRADICTIONS OF THIS ROW, both first-hand, both against 2026-09-18 AGENT-MEASURED
figures the row itself flagged as re-measure-before-quoting. (a) The title's "hypothesis
campaign has ZERO reach" is WRONG: test_hypothesis.py compiles 2-3 crossable schemas per run
and makes 34-40 effective _ensure_entity_middles calls. Thin (~0.3-0.5% of parses) and
run-dependent, but a DISTRIBUTION problem, not a structural one. (b)
tests/test_zt_p5_readjudication.py, listed on the row as producing an empty census, is the
LARGEST reacher in the suite: 82 crossable parses, 189 effective calls, more than every other
module combined. The matrix half of the title is CONFIRMED -- test_matrix.py 0 of 36 parses,
test_wildcard_property.py 0 of 3.

THE ROW'S CLAIM SURVIVES IN A SHARPER FORM, and this should become the row's statement: the
unreached surface is the crossing-middle REMOVE path. _sync_entity_middles is EFFECTIVE in
exactly ONE module across an 82-test run -- test_i14_crossing_middles.py, 8 calls out of
524-571 raw -- in both runs. The add side is reached by five of seven modules. So the
acceptance target for any fixture/generator work here is the _sync EFF column, not the
_ensure one.

(!) INSTRUMENT NOTES, both load-bearing. A RAW call count of either function is NOT reach:
both return at a guard when crossable_shapes is empty, so a module with zero crossable
schemas still books hundreds of calls (7408 raw vs 257 effective). The probe carries a
CEILING CONTROL (_ensure_own_bridges on a crossable schema) so a zero EFF reads as "never
reached" rather than "instrument dead". The EFF columns were SABOTAGED -- override
SchemaInfo.crossable_shapes to empty, and every EFF and CTL column goes to 0 while
_ensure/raw stays at 21 and all 5 tests go RED.

(!) UNRESOLVED DISCREPANCY against this row's own 2026-09-19b census. It recorded "7
_sync_entity_middles calls in total" over three modules; this run measures 14 raw / 8
effective over the same three, and test_i14_crossing_middles.py alone re-runs at the same
14/8 twice. Neither is 7. Coincidence worth noting, UNVERIFIED: the SABOTAGED run -- the one
with crossability neutered -- books exactly 7. A probe that broke the thing it was measuring
would produce that number, which is P6 step 0's failure verbatim. I did not reconstruct the
earlier probe.

(!) test_hypothesis.py's row is a SAMPLE, not a measurement -- it moved on every column
between two runs of the same command (ci profile is not derandomized). The other six modules
are byte-identical across both runs. Quote its numbers as a rate.

NEXT ACTION: write the crossable matrix fixture (the owc_star_ttu template is the working
shape) and put it under test_matrix.py / test_wildcard_property.py, with the probe's _sync
EFF column as the acceptance check -- an added fixture that does not move it bought nothing,
and an empty crossable_shapes is a silent no-op that passes every test it is added to.

### 2026-09-19d

CENSUS §7 ITEM (1) EXECUTED, first-hand, and the acceptance column MOVED. The fixture work
this row named is landed: `tests/fga_schemas/owc_star_ttu.fga` is now a second corpus in BOTH
modules the census measured at zero reach --
`tests/test_matrix.py::test_matrix_4way_crossable_star_ttu` (4-way: graph + connected store +
oracle + set engine under both SetOps, seeds 0/1/2) and
`tests/test_wildcard_property.py::test_wildcard_property_crossable_vs_oracle` (seeds 0/1/2).
Corpus, grid and guards live once, in `test_wildcard_property.py`, and the matrix imports
them.

MEASURED 2026-09-19d with this row's own probe, same command as the census §8 (log figures in
the doc's dated append):

    module                            parse_crossable   _ensure/EFF   _sync/EFF   CTL
    tests/test_matrix.py                 0 -> 6            0 -> 78      0 -> 46    0 -> 196
    tests/test_wildcard_property.py      0 -> 5            0 -> 40      0 -> 23    0 -> 101

`_sync ... EFF` is the acceptance target this row set (census §7.4), and for scale: the whole
seven-module suite measured 8 before, all of them in `tests/test_i14_crossing_middles.py`.
These two modules now book 69 between them, and they are the differential and the property
grid rather than a hand-written module -- which is the thing this row was filed about.

A REAL BUG CAUGHT BY THE NEW ARM ON ITS FIRST RUN, worth recording because it was not the
bug being looked for: the corpus carries the boolean `restricted`, and the index-only
property harness had never needed a `DeltaProcessor`. Without the cascade `restricted`
answers False forever -- the walk's own oracle grid reddened on seeds 0 and 2 at
`('...', 'user', 'u1', 'restricted', 'folder', 'f1')`, `index=False oracle=True`. Wired in
(watermark before, `run_cascade` inside the same txn, per CLAUDE.md I5); sweep `M11` now pins
it.

SABOTAGE: 12 mutations, 11 CAUGHT, reproducer tracked at
`formal/probes/tk77_middles_reach_sweep_2026-09-19.py` (it edits tracked files and restores
them in `finally`). `M0` is the harness control and attributed correctly, so the table
measures the module and not a broken instrument. Full table in the test module's own section
comment and in the census doc's dated append.

(!) THE FIRST RUN OF THAT SWEEP IS THE PART TO CARRY: it reported one ANCHOR-MISS and three
INERT rows, and TWO of the three inert rows were real holes.
 * `M5` -- the CORPUS half of crossability was unpinned. Deleting every bare-star tupleset
   subject from the pool left all eight crossable tests GREEN, because `crossable_shapes` is
   schema-computed and both the `_sync_entity_middles` guard AND this row's own EFFECTIVE
   column key off the entity TYPE. No assertion and no column in the census can see a pool
   that stopped carrying the star; the differential just explores a smaller state space and
   agrees with itself. Closed mechanically by `::assert_crossable_pool`. `M4` (drop ONE of
   the two star subjects) stays legitimately INERT -- one is enough for the feature.
 * `M10` -- the `n != '*'` clause of the effective filter was unpinned, because on a
   crossable corpus raw and filtered counts are both non-zero either way. Closed by
   `::test_middle_sync_record_excludes_the_wildcard_entity`.
 * `M9` (effective -> raw, i.e. this row's own trap (a) committed inside the instrument) is
   caught ONLY by the two instrument controls, never by a walk. That is why the negative
   control runs on `wildcards.fga`: on a crossable corpus nothing distinguishes a filtered
   count from an unfiltered one.
 * An ANCHOR-MISS row measures NOTHING and prints in the same column as a CAUGHT row. `M9`'s
   first form spanned two lines and the tree is CRLF.

NEXT ACTION: census §7 items (2) and (3), both generator work and neither started -- the
one-line `tests/genswarm.py::witness` fix (its declared `owc` is `('doc','parent')` while its
through-shape is `('doc','r1')`, disjoint by construction) and the `star_bridge_configs`
re-weighting (24 of 224 configs are crossable, all in the `A == B` arm). The fixture half of
this row is DONE. Unchanged and still not to be reconciled arithmetically: the 2026-09-19b
"7" discrepancy.

### 2026-09-19e

CENSUS §7 ITEMS (2) AND (3) EXECUTED, first-hand, and NEITHER LANDED AS WRITTEN because
measuring them first contradicted the section that asked for them. Full map, with the tables:
docs/tk77-crossable-census-2026-09-19.md, dated append at the top (2026-09-19e). Probes
formal/probes/tk77_generator_reach_2026-09-19.py (modes `owc`, `reweight`) and
formal/probes/tk77_generator_reach_sweep_2026-09-19.py.

LANDED. (1) `tests/genswarm.py::witness` now object-wildcards the TTU TARGET `('doc','r1')`
too -- the star tupleset's through-shape -- guarded off `body_boolean` (taints r1 -> owc on a
derived relation is a decision-15 refusal) and `body_wc_userset` (literal `[doc:*#r1]` ->
doubly bridged). MEASURED over all 65535 configs: rejection outcomes byte-identical to the old
generator (0 changes), so no coverage floor moves. The UNGUARDED form costs 256 fresh
DoublyBridgedShapeError and reaches the same 128 -- it buys nothing and deletes configs.
(2) `tests/test_generator_coverage.py::test_driven_config_space_reaches_a_crossable_schema`
pins that reach (1 of 96 compiled at K<=2). (3)
`tests/test_hypothesis.py::test_star_bridge_crossing_middle_remove_deterministic_pin` is the
acceptance target: a generated star-bridge config through a ParityEngine, pool applied, middle
interned, every accepted write removed in reverse, middles gone, row multiset restored exactly.
(4) `star_bridge_configs` re-weighted (B==A at 1/2, owc forced to include the TTU target at
1/2 on that arm).

ACCEPTANCE COLUMNS, §8's instrument: test_generator_coverage.py parse_crossable 3 -> 17,
`_ensure/EFF` 0 -> 46, CTL 0 -> 110 (that module was never in §6's table at all);
test_hypothesis.py parse_crossable 2-3 -> 6, `_ensure/EFF` 34-40 -> 74, `_sync/EFF` 0 -> 8
(deterministic, from the pin), CTL 82 -> 146.

(!) TWO MEASURED CONTRADICTIONS OF THE CENSUS, both first-hand. (a) §4's "0 of 65535" is a
DECLARED-shape figure. Compiled -- which is what WildcardIndex reads -- the UNCHANGED generator
is crossable in 128 of the 4991 configs that compile: `_expand_object_wildcard_shapes`
propagates the declared ('doc','parent') onto the TTU head ('doc','r2'), which `self_ttu` then
makes a through-shape. All 128 need a switch TRIPLE and DRIVE_K is 2, which is why the DRIVEN
space was 0 either way. A static shape census and a compiled one are different measurements;
only the compiled one predicts reach. (b) §5's "simply rare" is FALSE about the strategy:
`star_bridge_configs` draws crossable at 10.7% of draws, 32/300 on each of seeds 0/1/2 --
exactly its closed-domain fraction 24/224. §6's "3 in 644" is a CONSUMER-BUDGET figure, so
re-weighting could never have met §7.4's acceptance target; a deterministic pin was the only
instrument that could.

SABOTAGE: 7 mutations, 6 CAUGHT, `N0` control attributed. `N5` (PRODUCT: drop `remove_edge`'s
OBJECT-endpoint `_sync_entity_middles` call) READ INERT ON THE FIRST RUN and that was the
SWEEP's fault -- the catching test was in a module the selection did not run. Two keepers: a
sweep whose selection cannot see the catching test reports a hole that does not exist; and on
that mutation `tests/test_i14_crossing_middles.py` -- the module named after the invariant --
stays GREEN while the 2026-09-19d property-walk recorder reddens. `N6` (revert half the
re-weighting) is legitimately INERT: a weighting moves a distribution, and no assertion claims
one.

NEXT ACTION / STILL OPEN: the only remaining zero in the acceptance table is
test_generator_coverage.py's `_sync/EFF`, and the cause is structural -- `genswarm.py::Diff`
exposes `add` and `sweep` only, no remove op, while every caller of `_sync_entity_middles` is a
removal path. Giving the swarm driver a remove op changes the contract of the thing that fuzzes
admission SEQUENCES, so it is its own item, not a one-liner. Unchanged and still not to be
reconciled arithmetically: the 2026-09-19b "7" discrepancy.

### 2026-09-19f

CLOSED 2026-09-19f. Every item this row owned is executed and the acceptance column it was
filed about is non-zero on both halves.

The row's title -- "the matrix and hypothesis campaign have ZERO reach into the
_sync_entity_middles surface" -- is discharged: the hypothesis campaign books `_sync/EFF` 8
(deterministic, 2026-09-19e) and tests/test_generator_coverage.py now books it too, via the
swarm removal pass that TK87 landed 2026-09-19f (see that row and
docs/tk87-swarm-churn-2026-09-19.md). The census's section 7 items (1), (2) and (3) are all
executed; its section 7.4 acceptance target -- "a change that lifts `_ensure` EFF while
leaving `_sync` EFF where it was has not moved the thing TK77 is about" -- is met.

Map: docs/tk77-crossable-census-2026-09-19.md, now FROZEN with this close (dated appends
2026-09-19d and 2026-09-19e, plus the TK87 doc for the removal half).

Carried forward rather than dropped:
* TK87 (closed same session) took the structural zero -- `genswarm.Diff` was add-only.
* TK88 (NEW 2026-09-19f) -- the "this module is expected to be RED" prose in
  tests/test_generator_coverage.py, which has been green since 0838bcf.
* The 2026-09-19b "7" discrepancy is STILL unreconciled and still not to be reconciled
  arithmetically, and 2026-09-19f adds a second one of the same kind: the module's
  `parse_crossable` measured 18 on this tree with the same command that produced the row's
  17. Both are first-hand; neither is averaged.
