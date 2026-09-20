# `TK77` — the crossable-shape census (which corpora can reach I14 at all)

**FROZEN 2026-09-19f — provenance, not a living document.** `TK77` closed on 2026-09-19f
(`python scripts/task.py show TK77`, now under `tasks/closed/`), which is what this file's
own ACTIVE-PLAN banner said would freeze it. Status lines below are as-of-then and several
are already false — §4's *"0 of 65535"* is contradicted by the 2026-09-19e append above it,
and §7's three items are all executed. The REMOVE half of §7.4's acceptance target was
finished by `TK87` on the same day; its map is
[`tk87-swarm-churn-2026-09-19.md`](tk87-swarm-churn-2026-09-19.md), which also records a
first-hand `parse_crossable` **18** against this file's **17**, deliberately unreconciled.
Live state is the task tree and `python scripts/gate_status.py` — never this file.
Corrections are appended **dated at the top**, never edited into the body.

⚠ **CORRECTION 2026-09-20g (`TK89`) — THIS FILE'S `parse_crossable` 17 IS NOT REPRODUCIBLE,
AND `TK87`'S 18 IS.** The deliberately-unreconciled discrepancy named in the banner above is
settled, and not in this file's favour. **MEASURED 2026-09-20g** in a `git worktree` at
`399ea99` (this file's own commit), twice, `PYTHONHASHSEED=0`, byte-identical both times:
`parse_total` **1661**, `parse_crossable` **18**, `_ensure/EFF` **46**, `CTL` **110**,
`28 passed` — matching `tk87-swarm-churn-2026-09-19.md` §1's transcript character for
character.

The §"acceptance columns" table below records `3 -> 17`, and that `17` was measured *while*
the change was being made — against an uncommitted working tree, not against `399ea99`. That
tree cannot be recovered, so **which** late edit added the eighteenth crossable parse is
unanswerable and is left unanswered. **Both numbers are honest; they are not two
measurements of one tree.** Nothing else in the acceptance table is affected: `_ensure/EFF`
46, `_sync/EFF` 0 and `CTL` 110 all reproduce.

⚠ The one column that genuinely does NOT reproduce is `_ensure/raw`, which varies by up to
**38** on an unchanged tree at a FIXED hash seed — filed as `TK93`, trap (c) in
`formal/probes/tk77_crossable_census_2026-09-19.py`. No table in this file quotes it.
Full write-up: [`tk89-census-reproducibility-2026-09-20.md`](tk89-census-reproducibility-2026-09-20.md).

*Opened 2026-09-19c as ACTIVE-PLAN, as `TK77`'s FIRST ACTION: "measure `crossable_shapes`
for every fixture in `tests/fga_schemas/` and publish the table". Every figure below was
measured first-hand on its own dated section's date.*

⚠ **This census CONTRADICTS the `TK77` row on two load-bearing points** (§6). The row's
title — *"the matrix and hypothesis campaign have ZERO reach"* — is right about the matrix
and **wrong about the hypothesis campaign**, and the module the row lists as producing an
empty census (`tests/test_zt_p5_readjudication.py`) is in fact the single largest reacher in
the whole suite. Read §6 before quoting the row.

Provenance labels used throughout: **READ** (first-hand from the named `file::symbol`),
**MEASURED** (first-hand run this session, command in §8), **REASONED** (derived from a READ,
not separately observed). Nothing here is agent-reported.

## Correction / continuation — 2026-09-19e: §7 items (2) and (3) are EXECUTED, and both of their premises were wrong

**MEASURED 2026-09-19e, first-hand.** §7's remaining two items are done. Neither landed as
written, because measuring them first contradicted the section that asked for them — twice,
in opposite directions. Read this before quoting §4 or §5.

⚠ **CONTRADICTION (a) — §4's "0 of 65535" is a statement about the DECLARED shapes, not
about the compiled schema the graph index actually reads.** §4 measured
`derive_schema_info(ast, owc).crossable_shapes` and reported zero for every one of
`genswarm.witness`'s configs. Compiled — `parse_openfga_schema`, which is what
`WildcardIndex` keys off — the UNCHANGED generator is crossable in **128** of the **4991**
configs that compile:

```
genswarm.witness owc candidates, K<=16 (65535 configs)      # probe, mode `owc`
  live      crossable_static     0    crossable_compiled  128   compiled 4991   REJ 60544
  guarded   crossable_static  4608    crossable_compiled  192   compiled 4991   REJ 60544
  plus_r1   crossable_static 25600    crossable_compiled  128   compiled 4735   REJ 60800
```

`_expand_object_wildcard_shapes` propagates the declared `('doc','parent')` onto the TTU
head `('doc','r2')`, which the `self_ttu` switch then also makes a through-shape — so the
crossing closes at compile time without anyone declaring it. Every one of those 128 needs a
switch TRIPLE, and `DRIVE_K` is **2**, which is why the DRIVEN space was 0 either way and
why the module still measured `_ensure/EFF` **0**. The lesson is narrower than "§4 was
wrong": a static shape census and a compiled one are different measurements, and only the
compiled one predicts reach.

⚠ **CONTRADICTION (b) — §5's "the crossable arm … is simply rare" is false about the
strategy.** `star_bridge_configs` draws crossable configs at **10.7%** of draws, measured at
300 draws on each of hypothesis seeds 0, 1 and 2 (32/32/32) — *exactly* its closed-domain
fraction 24/224, i.e. hypothesis was already sampling it about uniformly. §6's *"3 crossable
parses in 644"* is therefore a CONSUMER-budget figure (how many examples the star-bridge
machines get out of the module's total), not a weighting one. **A re-weighting could never
have met §7.4's acceptance target**, and this is the part worth carrying: the target is the
REMOVE column, a sampled count can be zero on the next seed, and `CLAUDE.md`'s durability
ranking puts a permanent test above a distribution tweak.

### What landed

1. **`tests/genswarm.py::witness` now object-wildcards the TTU TARGET too** — `('doc','r1')`,
   the star tupleset's through-shape — guarded off the two switches that would turn it into a
   scope refusal (`body_boolean` taints `r1`, so an owc on it is the decision-15
   owc-on-a-derived-relation refusal; `body_wc_userset` puts the literal `[doc:*#r1]` on `r6`,
   which would make the shape doubly bridged). The guard is not defensive tidiness: the
   UNGUARDED form (`plus_r1` above) costs **256** fresh `DoublyBridgedShapeError` refusals and
   reaches the same **128**, i.e. it buys nothing and deletes configs. Rejection outcomes under
   the guarded form are **byte-identical to the old generator over all 65535 configs** (0
   outcome changes), so the rejection census and every coverage floor are undisturbed.
2. **A floor pins that reach**: `tests/test_generator_coverage.py::test_driven_config_space_reaches_a_crossable_schema`
   — at least one config in the DRIVEN (`K<=DRIVE_K`) space must compile to a non-empty
   `crossable_shapes`. Measured 1 of 96 compiled at `K<=2`; the sibling `{'owc','ts_negonly'}`
   is statically crossable but refused (owc on a `parent` its negation tainted), which is why
   the floor is 1 and not higher.
3. **`tests/test_hypothesis.py::test_star_bridge_crossing_middle_remove_deterministic_pin`** —
   the acceptance target. A generated star-bridge config (`T=folder`, `A==B=admin`,
   `owc={(T,'parent')}`, which is crossable via the same propagation as (a)), driven through a
   `ParityEngine`: apply the pool, assert a middle was interned, remove every accepted write in
   reverse, assert the middles are gone and the row multiset is restored exactly. It asserts
   `crossable_shapes` is non-empty up front — a mechanical refusal against §7's silent-no-op
   trap — and counts EFFECTIVE `_sync_entity_middles` calls with the guard the census uses.
4. **`star_bridge_configs` re-weighted anyway**, because the *other* half of (b)'s measurement
   is worth having: **56%** of the old draws were doubly bridged, so the machine spent more than
   half its example budget asserting a rejection and skipping.

```
star_bridge_configs drawn rates, 300 draws, hypothesis seed 0   # probe, mode `reweight`
  live       crossable/draws 10.7%   compiled/draws 43.7%   A==B  40
  selfbias   crossable/draws 21.3%   compiled/draws 52.3%   A==B  80
  owcbias    crossable/draws 21.3%   compiled/draws 50.7%   A==B  72
  both       crossable/draws 41.0%   compiled/draws 69.0%   A==B 137     <- landed
```

The `A != B` arm still draws ~50% of the time and books ~93 doubly-bridged rejections per 300
draws, so the F1/F2 axis (deviations 2026-07-17) keeps ample coverage; what it no longer is,
is the majority case.

### The acceptance columns, measured with §8's instrument

```
module                              parse_crossable   _ensure/EFF   _sync/EFF     CTL
                                     before  after    before after  before after
tests/test_generator_coverage.py      3 ->  17         0 ->  46      0 ->   0    0 -> 110
tests/test_hypothesis.py            2-3 ->   6       34-40 ->  74      0 ->   8   82 -> 146
```

`tests/test_generator_coverage.py` was never in §6's table at all — it is the module that
drives `genswarm`, and its `before` column is a fresh 2026-09-19e measurement of the
unmodified generator. Its `_sync/EFF` stays **0**, and the cause is structural, not a
weighting or a fixture: **`genswarm.py::Diff` has no remove op.** It exposes `add` and
`sweep` only, so no swarm config of any shape can reach `_sync_entity_middles`, whose every
caller is a removal path (`index_v4/wildcard.py::remove_edge` / `::remove_node`,
`index_v4/processor.py`'s reconcile GC). Giving the swarm a remove op is a separate item,
noted on the row; it is a change to the driver's contract (admission sequences are what that
generator exists to fuzz), not a one-liner.

`tests/test_hypothesis.py`'s `_sync/EFF` **8** is deterministic — it comes from the pin, not
from the campaign — which is exactly why the pin and not the re-weighting is what closes
§7.4 for this module.

### Sabotage: 7 mutations, 6 caught, and the one INERT row is honest

Reproducer `formal/probes/tk77_generator_reach_sweep_2026-09-19.py`; the measurement probe is
`formal/probes/tk77_generator_reach_2026-09-19.py` (modes `owc` and `reweight`).

```
N0  CAUGHT   HARNESS CONTROL: the remove pin's own final claim, inverted
             -> ::test_star_bridge_crossing_middle_remove_deterministic_pin
N1  CAUGHT   revert witness() to the pre-2026-09-19e owc (tupleset shape only)
             -> ::test_driven_config_space_reaches_a_crossable_schema
N2  CAUGHT   drop witness()' two-switch guard (the "why is this conditional?" tidy)
             -> ::test_no_enumerated_config_is_silently_dropped
N3  CAUGHT   make the pin's own config NON-crossable (the silent-no-op trap)
             -> ::test_star_bridge_crossing_middle_remove_deterministic_pin
N4  CAUGHT   the pin adds but never removes
             -> ::test_star_bridge_crossing_middle_remove_deterministic_pin
N5  CAUGHT   PRODUCT: remove_edge stops syncing the OBJECT endpoint's middles
             -> tests/test_wildcard_property.py::test_middle_sync_record_excludes_the_wildcard_entity
N6  INERT    revert half the re-weighting (B == A drawn at 1/2)
```

`N0` is attributed, so the table measures the modules and not a broken instrument.

(!) **`N5` READ `INERT` ON THE FIRST RUN, AND THAT WAS THE SWEEP'S FAULT, NOT A HOLE.** The
first selection was the three new-arm patterns only; the test that reddens on `N5` lives in a
module that selection did not run. Two things fall out. First, **a sweep whose selection
cannot see the test that catches a mutation reports a hole that does not exist** — the mirror
image of the failure these sweeps exist to find, and cheaper to believe because an
unexplained INERT row looks like a discovery. Second, and worth keeping: on `N5`
`tests/test_i14_crossing_middles.py` — *the module named after the invariant* — stays
**GREEN**, while the 2026-09-19d property-walk recorder reddens. The fixture module pins the
witness; the walk pins the call sites.

(!) **`N6`'s INERT is the honest kind and is recorded rather than fixed.** A weighting change
moves a DISTRIBUTION, and no assertion in the suite claims one — asserting a drawn rate would
pin hypothesis's sampler, not this repo's behaviour. State what an INERT row was supposed to
move (`P6` step 2's rule): `N6` was supposed to move the crossable draw rate, it does (41.0%
-> 21.3% measured), and nothing red follows from that by design. This is also why item (3) on
its own could not have been the deliverable.

### What is still open on this row

Section 7's three items are all executed. What the work opened, and what nobody has done:

* **`genswarm.py::Diff` has no remove op**, so the swarm's `_sync` reach is structurally 0
  (above). That is the only remaining zero in the acceptance table.
* The 2026-09-19b *"7"* discrepancy (§6) is still unreconciled, and still not to be reconciled
  arithmetically.

---

## Correction / continuation — 2026-09-19d: §7 item (1) is EXECUTED, and the acceptance column moved

**MEASURED 2026-09-19d, first-hand, same probe and same command as §8.** §7 decided *"a new
matrix fixture, not a parameter change"*, with §7.4 naming the acceptance target: the
`_sync … EFF` column, not the `_ensure` one. Both are now done. `owc_star_ttu.fga` joined
`tests/test_matrix.py` and `tests/test_wildcard_property.py` as a second corpus
(`::test_matrix_4way_crossable_star_ttu`, `::test_wildcard_property_crossable_vs_oracle`,
seeds 0/1/2 each), and the two modules that had ZERO reach now carry most of the suite's:

```
module                            parse_crossable   _ensure/EFF   _sync/EFF   CTL
                                   before  after    before after   before after
tests/test_matrix.py                 0       6        0     78       0     46   0 -> 196
tests/test_wildcard_property.py      0       5        0     40       0     23   0 -> 101
```

For scale, §6 measured the whole seven-module suite at **8** effective `_sync` calls, all of
them in `tests/test_i14_crossing_middles.py`. These two modules alone now book **69**, and
they are the differential and the property grid rather than a hand-written module — which is
the thing `TK77` was filed about.

**Corpus shape.** `crossable_shapes == {('folder','viewer')}` (MEASURED, both under the
two-shape `CROSSABLE_WC` and under `{('folder','viewer')}` alone). The corpus carries the
boolean `restricted` too, so the graph leg runs its delta-processor cascade; the property
walk needed a `DeltaProcessor` wired in, which the index-only harness had never needed. That
was not a design choice but a **caught bug in the first draft** — without the cascade
`restricted` answers `False` forever, and the walk's own oracle grid reddened on seeds 0 and
2 at `('...', 'user', 'u1', 'restricted', 'folder', 'f1')`, `index=False oracle=True`.

### Sabotage: 12 mutations, 11 caught, and two of the three first-run INERT rows were real holes

Reproducer tracked at `formal/probes/tk77_middles_reach_sweep_2026-09-19.py`; it restores the
tree in `finally`, and the run below left `git status` showing only the intended edits.

```
M0   CAUGHT   HARNESS CONTROL: invert assert_remove_path_reached's own claim   6 walks red
M1   CAUGHT   CROSSABLE_WC -> {('doc','viewer')} (the plausible parameter edit)   8 red
M2   CAUGHT   CROSSABLE_WC -> frozenset()                                        8 red
M3   CAUGHT   CROSSABLE_SHAPES -> frozenset() (weaken the pin itself)            8 red
M4   INERT    drop ONE of the two bare-star tupleset subjects from the pool
M5   CAUGHT   drop EVERY bare-star tupleset subject from the pool                6 walks red
M6   CAUGHT   property walk never removes (rng < 1.1)                            3 red
M7   CAUGHT   matrix arm never removes (rng < 1.1)                               3 red
M8   CAUGHT   INSTRUMENT KILL: recorder observes nothing                         8 red
M9   CAUGHT   effective filter -> `if True` (read RAW as reach)                  2 controls red
M10  CAUGHT   drop only the `n != '*'` clause from the filter                    1 control red
M11  CAUGHT   omit proc.run_cascade(wm)                                          2 of 3 seeds
```

**`M0` attributed correctly**, so the table is a measurement of the module rather than of a
broken harness (`docs/sabotage-procedure.md`; `P6` step 0's failure mode).

**What the FIRST run of this sweep found, which is the part worth carrying.** It reported
`M9` as `ANCHOR-MISS (0 matches)` and `M4` / `M5` / `M10` as `INERT`, and two of those were
genuine holes rather than clean pins:

* **`M5` — the corpus half of crossability was unpinned.** Deleting every bare-star tupleset
  subject from `_crossable_raw_tuples` left all eight crossable tests GREEN.
  `crossable_shapes` is computed from the SCHEMA, and both `_sync_entity_middles`' guard and
  this census's own EFFECTIVE column key off the entity TYPE — so no assertion anywhere, and
  no column in this document, can see a pool that stopped carrying the star. The differential
  simply explored a smaller state space and agreed with itself. Closed by
  `tests/test_wildcard_property.py::assert_crossable_pool`, a refusal rather than a comment
  because a pool shrink is never caught by the tests that consume the pool. `M4` stays
  legitimately inert: one of the two star subjects is enough for the feature, so a sweep row
  that reddened on losing either would be over-fitted.
* **`M10` — the `n != '*'` clause of the effective filter was unpinned**, because on a
  crossable corpus raw and filtered counts are both non-zero either way. Closed by
  `::test_middle_sync_record_excludes_the_wildcard_entity`.
* **`M9` — "read RAW as reach", i.e. trap (a) of §6 committed inside the instrument** — is
  caught only by the two instrument controls, never by a walk. That is what those controls are
  for, and it is the reason the negative control runs on `wildcards.fga`: on a crossable
  corpus there is no observation that distinguishes a filtered count from an unfiltered one.
* ⚠ **`M9`'s first form was an ANCHOR-MISS and an anchor-miss measures nothing** — it prints
  in the same column as the CAUGHT rows. Its anchor spanned two lines and the tree is CRLF.

### What is still open on this row

The acceptance target of §7.4 is met, so what remains is §7 items (2) and (3), neither
started: the one-line `tests/genswarm.py::witness` change (§4) and the
`star_bridge_configs` re-weighting (§5). Both are generator work; the fixture work is done.
Also unchanged: the §6 discrepancy against the row's own 2026-09-19b *"7"*, still not
reconciled and still not to be reconciled arithmetically.

---

---

## 1. The structural result — what makes a schema crossable at all

**READ** — `zanzibar_utils_v1.py::SchemaInfo.crossable_shapes` is
`bridged_in_shapes & bridged_out_shapes`, and `::SchemaInfo.bridged_in_shapes` drops every
bare `(T, '...')` shape. So an in-bridge needs a subject-wildcard shape with a **non-`...`
predicate**, and there are exactly **two** producers of one:

1. a **literal wildcard-userset restriction** `T:*#p` written in the DSL
   (`zanzibar_utils_v1.py::wildcard_userset_restriction_shapes`); or
2. a **star-tupleset through-shape**: the blind-audit block in
   `zanzibar_utils_v1.py::derive_schema_info` adds `(S, target_rel)` for every TTU
   `target_rel from ts` on type `T` whose tupleset relation `ts` on `T` admits `[S:*]`.

**READ** — `zanzibar_utils_v1.py::_reject_doubly_bridged_shapes` raises
`DoublyBridgedShapeError` for any shape that is *both* a literal `T:*#p` restriction shape
and an object-wildcard shape. Producer (1) is therefore **categorically excluded** from ever
being crossable: declaring the object wildcard that would close the crossing is a compile-time
refusal on both backends.

**REASONED, and corroborated by every census in §2-§5:**

> A schema is crossable-capable **iff** it carries a TTU whose tupleset relation admits a
> bare object star `[S:*]`, and the TTU's target relation is declared (or compiler-expanded)
> as an object-wildcard shape.

That is the `reg11` / `owc_star_ttu` shape and nothing else. It is a **two-feature
conjunction**, which is why "it declares an object wildcard, so it must exercise the crossing
machinery" has now been a wrong inference in at least six fixtures.

⚠ The second half of the conjunction can be satisfied **without being declared**:
`zanzibar_utils_v1.py::_expand_object_wildcard_shapes` closes the declared set over rewrite
rules, so an object wildcard on `parent` alone propagates through the TTU onto the target and
mints the crossing. **MEASURED** — **8 of the 24** crossable `star_bridge_configs` (§5) arrive
this way: the crossable shape appears in NO declared `object_wildcard_shapes` set and exists
only because expansion put it there. So "grep the fixtures for the declared shape" is not a
sound way to find the crossable corpora, and §2-§5 all compute the shape rather than reading
it off a declaration.

## 2. `tests/fga_schemas/` — the fixture corpus

**MEASURED 2026-09-19c.** `in` = `bridged_in_shapes`; `lit` = the literal-`T:*#p` subset
(structurally un-crossable, §1); `thru` = star-tupleset through-shapes, the only
crossable-capable class.

```
fixture                   in lit thru  through-shapes
boolean_wildcards          0   0    0  []
confluence                 0   0    0  []
custom_roles               0   0    0  []
demorgans_law_1            0   0    0  []
demorgans_law_2            0   0    0  []
demorgans_reverse          0   0    0  []
gdrive                     0   0    0  []
github                     0   0    0  []
heterogeneous_tupleset     0   0    0  []
master_store               0   0    0  []
owc_star_ttu               1   0    1  [('folder', 'viewer')]
tupleset_shapes            0   0    0  []
userset_over_derived       0   0    0  []
wildcard_userset_cross     1   1    0  []
wildcards                  1   1    0  []

CROSSABLE-CAPABLE fixtures: ['owc_star_ttu']      (1 of 15)
```

**This answers the question the row asked, and it answers it more strongly than the row
expected.** The row framed the census as deciding *"whether the fix is a new matrix fixture or
a generator change"*, on the assumption that the matrix's `OBJECT_WC` choice was the variable.
It is not:

* **13 of 15 fixtures have `bridged_in_shapes` empty.** No `object_wildcard_shapes` argument,
  of any value, can make them crossable. This is not a configuration miss.
* **`wildcards.fga` and `wildcard_userset_cross.fga` cannot be fixed by configuration
  either** — their single in-bridge is the literal `group:*#member`, and declaring
  `('group','member')` as an object wildcard is REFUSED:
  `DoublyBridgedShapeError: shape(s) (group, member) are BOTH a wildcard-userset shape (a
  T:*#p restriction) and an object-wildcard shape`. **MEASURED** (both fixtures).

So `wildcards.fga` — the matrix fixture whose entire subject is wildcards — is not merely
un-crossable under today's `OBJECT_WC`; it is **structurally impossible to make crossable**.
The fix is a NEW fixture (or a generator change), never a parameter edit. That menu item is
now closed.

## 3. `formal/conformance/` — the enum corpus

**MEASURED 2026-09-19c** over all 26 schemas in
`formal/conformance/test_conformance_enum.py::SCHEMAS`, each at its own declared
`object_wildcard_shapes`: **`in = 0` for every one of them; 0 crossable-capable.**

The sharp row is `object_wildcard`, which declares `ow=[('folder','viewer')]` and still has
`in=0` — an object-wildcard corpus schema with no in-bridge, i.e. §1's wrong inference in the
conformance corpus too. The whole conformance leg of the gate is blind to I14 by
construction.

## 4. `tests/genswarm.py` — the swarm witness space

**MEASURED 2026-09-19c**, and this one is a **closed, RNG-free statement** because
`genswarm.py::witness` takes each enabled switch unconditionally:

```
SWARM_SWITCHES                                   16
configs enumerated (all subsets, size 1..16)     65535
witness configs with NON-EMPTY crossable             0
through-shapes ever produced by witness()        [('doc','r1'), ('doc','r2')]
owc shapes ever declared by witness()            [('doc','parent')]
```

**The cause is one line and it is mechanical, not statistical.** `genswarm.py::witness` ends
with `owc = frozenset({('doc','parent')}) if 'owc' in sw else frozenset()`, while the
`ts_wildcard` switch puts `[doc:*]` on `parent` and the unconditional TTU is
`('doc','r2'): TTU('r1','parent')` — so the through-shape it mints is `('doc','r1')`. The
declared set and the through-shape set are **disjoint by construction**, and no number of
draws can cross them. `ts_wildcard` alone is *not* enough: it produces the
subject-wildcard shape `('doc','...')`, which `bridged_in_shapes` drops as bare.

REASONED: this is a one-shape change (`owc` on the TTU target rather than the tupleset, or as
well as it) — see §7.

## 5. `tests/test_hypothesis.py::star_bridge_configs` — the one generator that DOES reach it

**MEASURED 2026-09-19c**, closed enumeration of the strategy's own domain
(`_SB_TYPES` x `_SB_RELS` x `_SB_RELS` x every subset of `owc_domain`):

```
closed config space                  224
compile-REJECTED (doubly-bridged)     96
CROSSABLE                             24   (10.7% of the space)
crossable configs by arm          {'A==B': 24, 'A!=B': 0}
```

**Every one of the 24 is in the self-referential arm `A == B`** — the arm
`tests/test_hypothesis.py::_star_bridge_schema` added for `ZT-P5-NEW` on 2026-07-26, which
deliberately DROPS the literal `T:*#A` restriction precisely so the shape is not
doubly-bridged. Its docstring already says the result is *"exactly reg11 / `owc_star_ttu`"*;
what was not written down is that this makes it **the only crossable generator in the
repo**. The `A != B` arm keeps the literal `T:*#A`, so §1's exclusion applies and it can never
be crossable.

`A == B` is drawn at ~1/4, and then the owc subset must include the target or `parent`.
§6's live figures show what that works out to in practice: **3 crossable parses in 644.**

## 6. The live census — what the suite ACTUALLY reaches, attributed

**MEASURED 2026-09-19c**, 82 tests, `hypothesis` `ci` profile; instrument and command in §8.
**Run TWICE** (186.9s and 193.8s), and the second run is shown beside the first because they
do not agree — see "what is deterministic here" below, which is itself a finding.

⚠ **A RAW call count of `_ensure_entity_middles` / `_sync_entity_middles` is NOT reach, and
reading one as reach would invert this table.** **READ** —
`index_v4/wildcard.py::_ensure_entity_middles` returns immediately on
`if not crossable: return`, and `index_v4/wildcard.py::_sync_entity_middles` on
`if not any(t == entity_type ...): return`; both are called unconditionally from
`index_v4/wildcard.py::_ensure_bridges` and from `index_v4/processor.py`. The `EFF` columns
below apply those two guards; `raw` is shown beside them so the gap is visible.

Run A, then run B in parentheses where they differ:

```
module                              parse      parse_        _ensure   _ensure      _sync   _sync   CTL
                                    total      crossable     raw       EFF          raw     EFF
tests/test_bulk_build.py               24            3          1155         7         0       0      24
tests/test_hypothesis.py              644 (639)      3 (2)      2242 (2360)  40 (34)  166(213) 0      82 (70)
tests/test_i14_crossing_middles.py      5            5            27        15        14       8      51
tests/test_matrix.py                   36            0           872         0       290       0       0
tests/test_owc_star_parent_cross.py     3            3            21         6         0       0      27
tests/test_wildcard_property.py         3            0            36         0        34       0       0
tests/test_zt_p5_readjudication.py    734           82          3055       189        20       0     381
TOTAL                                1449 (1444)   96 (95)      7408 (7526) 257 (251) 524(571) 8     565 (553)
```

CTL is the **ceiling control** (`docs/sabotage-procedure.md`): `_ensure_own_bridges` calls made
while the store's schema is crossable. It is nonzero for every module with a nonzero
`parse_crossable`, so a zero in the `EFF` columns reads as *"the mechanism was never reached"*
and not as *"the instrument is dead"*. The two zero-CTL rows (`test_matrix`,
`test_wildcard_property`) are zero because they never compile a crossable schema at all —
their zeros are upstream of the instrument and consistent.

**What is deterministic here, and what is not.** Six of the seven rows are **byte-identical
across both runs**. `tests/test_hypothesis.py` is the only one that moves, and it moves on
every column — including the one this census is about (`parse_crossable` 3 then 2). The
campaign is not derandomized under the `ci` profile, so **its row is a sample, not a
measurement**: quote it as a rate with a range, never as a count. Every other figure in this
document is reproducible.

**SABOTAGE of the instrument itself** (`docs/sabotage-procedure.md` — an EFF column that
counted calls rather than reading the guard would report coverage everywhere and is exactly
the failure mode §6 opens by warning about). Narrowest plausible weakening: override
`zanzibar_utils_v1.SchemaInfo.crossable_shapes` to the empty set and re-run
`tests/test_i14_crossing_middles.py` — the one module with nonzero EFF in both directions.
Literal observed output:

```
module                                parse_total  parse_crossable  _ensure/raw  _ensure/EFF  _sync/raw  _sync/EFF  CTL
tests/test_i14_crossing_middles.py              5                0           21            0          7          0    0
...
5 failed in 0.41s
```

Every EFF column and CTL go to **zero** while `_ensure/raw` stays at **21** — so the EFF
columns are reading the guard, not the call — and all five tests go RED, so the sabotage is
not a no-op.

⚠ **A coincidence worth recording, UNVERIFIED.** That sabotaged run books **7** raw `_sync`
calls on `test_i14_crossing_middles.py`, which is exactly the figure the row's 2026-09-19b
census reported. A probe that neutered crossability while measuring it would produce that
number, and that is `P6` step 0's failure verbatim (an instrument that reports a clean module
because it broke itself). I did **not** reconstruct the earlier probe, so this is a hypothesis
about the discrepancy below, not a finding.

### What this confirms, and what it contradicts

**CONFIRMED — the matrix half of the row's title.** `tests/test_matrix.py` compiles **0**
crossable schemas in 36 parses, and `tests/test_wildcard_property.py` **0** in 3. The
validation matrix and the property grid have exactly zero reach into I14, as the row says, and
§2 now gives the reason: no fixture they use can be made crossable by any argument.

**CONTRADICTED (1) — the hypothesis half of the row's title is wrong.**
`tests/test_hypothesis.py` compiles **3 crossable schemas in run A and 2 in run B**
(`('doc','editor')`, `('folder','admin')`, `('folder','owner')` — the shapes differ between
runs too) and makes **40 / 34 effective** `_ensure_entity_middles` calls. Thin — of order
**0.3-0.5% of parses**, and run-dependent, so treat it as a rate — but not zero, and the
difference matters because it is a *distribution* problem (fixable by re-weighting
`star_bridge_configs`) rather than a *structural* one (which would need a new schema
template).

**CONTRADICTED (2) — `tests/test_zt_p5_readjudication.py` is the largest reacher in the
suite, not an empty one.** The row's 2026-09-18 entry lists it among the four modules that
"produce an EMPTY `_sync_entity_middles` census". It compiles **82** crossable schemas and
makes **189 effective** `_ensure_entity_middles` calls — more than every other module
combined. Its `('folder','a')` shape (74 of the 82) comes from the explicit
`frozenset({('folder','parent'), ('folder','a')})` object-wildcard set inside that module's
readjudication grid (search it for `('folder', 'a')`).

> The row's own 2026-09-18 entry flagged those counts as AGENT-MEASURED with *"re-measure
> before quoting them"*. This is that re-measurement, and it is why the flag was worth
> writing.

**The row's claim SURVIVES in a sharper form, and this is the real finding.** Split by
direction:

* the **add** side, `_ensure_entity_middles`, is reached by **five** of the seven modules
  (257 / 251 effective calls);
* the **remove** side, `_sync_entity_middles`, is reached by **exactly one module, in both
  runs** — `tests/test_i14_crossing_middles.py`, **8** effective calls out of **524 / 571**
  raw. Every other module's `_sync` traffic returns at the guard. That 8 is the one figure in
  the table that is identical in both runs *and* nonzero, which is what makes it quotable.

So the unreached surface is not "the crossing middles" but **the crossing-middle REMOVE
path**, and its whole coverage is one hand-written, non-differential, un-fuzzed module. That
is the statement `TK77` should carry.

⚠ **Discrepancy against the row's own 2026-09-19b census, NOT resolved.** That entry recorded
*"7 `_sync_entity_middles` calls in total"* over `test_i14_crossing_middles.py` +
`test_owc_star_parent_cross.py` + `test_bulk_build.py`. This run measures the same three
modules at **14 raw / 8 effective**, and `test_i14_crossing_middles.py` alone re-runs at the
same **14 / 8** (MEASURED twice, once inside the seven-module run and once alone). Neither
figure is 7. The counting boundary of the earlier probe was not recorded, so the two are not
differenceable — **re-measure, do not reconcile arithmetically.**

## 7. What the census decides

1. **A new matrix fixture, not a parameter change.** §2 closes the `OBJECT_WC` option: 13
   fixtures cannot be crossable at any argument and 2 are compile-refused. The fixture must
   carry the §1 conjunction — a TTU over a `[S:*]`-admitting tupleset, with the target
   relation object-wildcarded. `tests/fga_schemas/owc_star_ttu.fga` is the working template;
   it is currently used by `tests/test_i14_crossing_middles.py` and
   `tests/test_owc_star_parent_cross.py` but by **neither** `test_matrix.py` nor
   `test_wildcard_property.py`.
2. **The generator change is one shape, and it is cheap.** §4 shows `genswarm.py::witness`
   misses by a single hardwired pair. Adding the TTU target to the `owc` set opens 65535
   configs' worth of crossable space at once — but see the trap below.
3. **The `star_bridge_configs` re-weighting is the cheapest win of the three** (§5): the
   crossable arm already exists and already draws; it is simply rare.
4. **The acceptance target is the REMOVE side** (§6), not the add side. A fixture or
   generator change that lifts `_ensure_entity_middles` EFF while leaving
   `_sync_entity_middles` EFF at 8 has not moved the thing `TK77` is about.

⚠ **Trap for whoever takes (1) or (2): an empty `crossable_shapes` is a SILENT no-op, so a
new fixture that fails to be crossable will pass every test it is added to and look like
coverage.** The census instrument in §6 is the control — a fixture change must move the `EFF`
columns, and a new fixture that does not is a fixture that bought nothing. Do not accept a
green as evidence here; read the count.

## 8. Reproducing

The probe is tracked at `formal/probes/tk77_crossable_census_2026-09-19.py`. It carries the
static censuses of §2-§5 (run it with no arguments) and, as a pytest plugin, the live census
of §6:

```
python formal/probes/tk77_crossable_census_2026-09-19.py            # sections 2-5
python formal/probes/tk77_crossable_census_2026-09-19.py --pytest \
    tests/test_matrix.py tests/test_hypothesis.py \
    tests/test_wildcard_property.py tests/test_zt_p5_readjudication.py \
    tests/test_i14_crossing_middles.py tests/test_owc_star_parent_cross.py \
    tests/test_bulk_build.py -q -p no:cacheprovider -s
```
