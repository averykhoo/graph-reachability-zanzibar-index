# `TK142` -- why the lookup-oracle gates miss a dropped `lookup_reverse` exclusion (2026-10-14)

**FROZEN 2026-10-14, at `TK142`'s close — provenance, not a living document.** Status
lines below are as-of-then and several may now be false; live state: `HANDOFF.md` + the
session ledger, and `python scripts/task.py show TK142`. Corrections are appended dated at
the top, never edited into the body. Landed in commit `b7d15f5`.

Was ACTIVE-PLAN from 2026-10-14 until that close; the body is provenance. This is
the scouting map for `TK142`, measured by the `scout-TK142` agent on 2026-10-14. Every figure
below is as-of that date. Live state is the task row (`python scripts/task.py show TK142`)
and `python scripts/gate_status.py`, never this file. Corrections append **dated at the
top**, never edited into the body. Frozen at that close (banner above).

Provenance labels: **READ** (first-hand read of the tree), **PROBE** (first-hand run by
`scout-TK142`, output quoted literally), **REASONED**, **UNVERIFIED**. Line numbers are as of
2026-10-14 and will rot; `file::symbol` is the stable key. The probe scripts live in
`.scratch/now-next/probes/scout-TK142/` (gitignored, so every number they produced is
copied in here).

## Corrections (dated, newest first)

### Corrections 2026-10-14 (challenge)

By the `challenge-TK142` agent, a skeptic pass over this doc. Probes are in
`.scratch/now-next/probes/challenge-TK142/` (gitignored); every number they produced is copied
here. Mutants were applied as pytest plugins or in-process patches. `src/` was never edited.

**Confirmed (first-hand PROBE, `c1_census.py`).**
* The zero-`neg` census in section 3 re-measures exactly. On the current fixed gates, S3
  calls with a non-empty `neg` and graph `lookup_reverse` results with a non-empty
  `excluded_node_ids` are both 0 in every config:
  * wildcards s0/s1 (480/480 S3 calls)
  * boolean s0/s1 (768/768)
  * demorgans 6 steps (700)
  * owc_star_ttu s0/s1 (608/760)
* The proposed parameters reach the shape:
  * `demorgans_reverse` seed 0 at 12 steps: s3=8/1120, g34=4/560, 31.7s.
  * `boolean_wildcards` seed 4 at 8 steps: s3=6/896, g34=3/448, 24.1s.
* The scout's `p6` / `p7` mutant logs read as quoted (READ).

**C1. WRONG CLAIM, carried over from the row: a broad gate DOES catch the set-side mutant
M1.** It lives in another module (first-hand PROBE, `m1_other_nets.log`, the scout's M1
plugin). Run over `test_tk116_oracle_only_setengine.py`, `test_irrelevant_alternatives.py`,
`test_owc_star_parent_cross.py` and `test_reads.py`: `2 failed, 72 passed in 218.28s`.
* RED: `tests/test_tk116_oracle_only_setengine.py::test_generated_refused_schemas_run_the_set_only_lookup_gate`,
  a deterministic, seeded, generated-schema walk (`_run_gate`, 8 steps, the first 4
  graph-refused seeds):
  `Failed: lookup/oracle divergence (seed=4): set.lookup_reverse('r1', 'doc', 'd2') [py]: excluded_node_ids set() != expand.neg {5}`.
  Its census (PROBE, `c3_tk116_walk_census.py`): s3=10/2444.
* Also RED: `...::test_lookup_surfaces_match_oracle_without_a_graph[owc-on-derived]` (scripted).
* The row's sabotage ran only `test_lookup_oracle.py -k gate`, and section 2 here ran only
  three modules, so neither saw this.

Consequences:
* For the set side, the row's done-when ("at least one broad gate goes RED") is already met.
  It holds by seed luck, with no tripwire.
* That walk is SET-ONLY: graph-refused schemas, by construction.
* The regression that no deterministic broad gate catches is G1, the graph side (C2).
  Section 1's framing ("why do the gates miss M1") should be read as "the
  `test_lookup_oracle.py` gates miss M1, and every broad gate misses G1".

**C2. WRONG CLAIM in section 5 and the residual: `TestLookupSurfaceMachine` is not blind.
It is a coin flip.**
* G1 plugin over all 15 test modules that call `lookup_reverse` (first-hand PROBE,
  `g1_run.log`): `8 failed, 252 passed in 813.58s`.
* RED:
  * `TestLookupSurfaceMachine` (corpus `demorgans_reverse`, two adds)
  * `test_lookup_oracle_dense_boolean`
  * `test_tamper_graph_reverse_is_caught`
  * `test_reads.py::test_derived_lookup_reverse_markers_and_exclusions`
  * the four TK139 both-backends pins
* GREEN: every `gate_*` on its current parameters. This confirms the G1 half of section 5
  for the gates.
* Catch rate (PROBE, `c4_machine_catch_rate.py`: ci settings, `database=None`, generate
  phase only): **G1 caught 4/8 runs**. Every catch was
  `graph.lookup_reverse('does_not_label', 'attr', 'at1') vs oracle on subject (...,doc,dc1): graph=True oracle=False`.
* The scout's "green under M1" was one draw. REASONED: M1 goes red on the same demorgans
  states (S3 runs there too), so its catch rate should be similar. UNVERIFIED as a rate.
* The residual to record on the row is therefore "probabilistic, about half of ci runs",
  not "blind".

**C3. HAZARD for anyone re-running these sabotages: hypothesis REPLAYS stored failures.**
* The `ci` profile (`tests/test_lookup_hypothesis.py`) includes `Phase.reuse`, and no
  profile sets `database=None`. So the G1 run above saved a failing machine example under
  `.hypothesis/` (gitignored, READ).
* A later sabotage of the machine would replay it and look like a deterministic catch.
* Measure hypothesis tests under a mutant with `database=None`, as `c4` does. Or say in the
  record that a replay was possible.

**C4. MISSING SURFACE: the forward-lookup exclusion channel has the same class of gap.**
* Mutant F1 (first-hand PROBE, `tk142c_drop_fwd_excl_plugin.py`, `f1_run.log`):
  `SetEngine.lookup` (forward, TK116) has its `excluded_node_ids` cleared.
* Run over `test_lookup_oracle.py`, `test_lookup_hypothesis.py`, `test_tk116_...` and
  `test_reads.py`: `6 failed, 126 passed in 460.99s`.
* RED only: TK116's scripted witnesses `[owc-on-derived]` and `[owc-expands-onto-leaf]`,
  `test_lookup_marker_carries_its_exclusions[py/roaring]`, and
  `test_set_forward_checker_sees_a_tampered_exclusion[clear/spurious]`.
* GREEN: every broad gate, including the TK116 generated walk and the machine. In every
  broad gate, forward lookups with a non-empty `excluded_node_ids` count 0 (`c1`, `c3`: s4=0).
* REASONED: the shape needs an object wildcard under `and` / `but not`, which the graph
  refuses (decision 15). The generated gates and the proposed witness test all pass
  `object_wc=frozenset()`, so none of them can reach it, structurally.
* Recommendation: do not widen TK142. Add a third counter in `_Gate` (forward set lookups
  with a non-empty `excluded_node_ids`; free, no assertion yet), and file a sibling row for
  a seeded set-only walk with that tripwire. The candidate is
  `_run_gate(w.schema, w.owc, _witness_pool(w), seed, 8, allow_graph_absent=True)` over
  `tests/test_tk116_oracle_only_setengine.py::WITNESSES` families `owc-on-derived` /
  `owc-expands-onto-leaf` (both helpers exist, READ). Whether the walk reaches the shape is
  UNVERIFIED.

**C5. Plan changes that follow (REASONED from C1-C4):**
* (a) **Add a tripwire to the existing catch**, at zero runtime cost. Once `_run_gate`
  returns the gate (plan step 2), assert that the summed `set_reverse_neg` > 0 in
  `test_generated_refused_schemas_run_the_set_only_lookup_gate` (measured 10). The scout's
  importer list for step 2 omitted this caller (`tests/test_tk116_oracle_only_setengine.py`
  imports `_run_gate`, READ). It ignores the return value today, so the change is harmless.
* (b) **Point the witness test at the graph side.**
  * Its graph-refused witness (seed 4) duplicates C1's set-only coverage.
  * Its value is the graph-joined witnesses (seeds 11 and 28).
  * Tighten the tripwire from ">= 1 graph-joined" to ">= 2 graph-joined" (or search joined
    schemas only). The search cost for a third joined witness is UNVERIFIED.
* (c) **Count the graph half from the instrument, not the subject.** The planned
  `graph_reverse_excl` counts the graph's OWN output. It is not a fail-by-passing (the
  oracle half G3/G4 does the catching), but a cleaner tripwire counts set-side `neg`
  states seen while `self.graph` is joined: the set engine is the independent instrument.
  Optional. LOW.
* (d) **"Prefix-preserving" holds for the 6-step walk only.** The old DRAIN, from the
  6-step state, is not kept (section 4.1 says so). Keeping `walk_steps` in `[6, 12]`
  preserves the drain states for about +24s. Optional. LOW.
* (e) **Floors with parallel items.**
  * "2401 -> 2403" will not hold if TK137 or TK138 add tests in the same session.
  * `doc_counts --generate` ratchets to the live count (`doc_counts.py::ratchet_floors`,
    READ). Run it once, last, after every item lands, not per item.
  * (a) adds no collected test.

None of this changes the plan's core. Steps 3 and 4 (demorgans 12, boolean seed 4) are
sound and re-measured. Step 5 stays, retargeted per (b).

## 1. The question

`tests/test_lookup_oracle.py::_check_set_reverse` (S3) is two-sided on
`excluded_node_ids` since `TK139`: it asserts `res.excluded_node_ids == set(m.neg)` and an
oracle exactness that subtracts exclusions (READ). Yet with the TK139 fix reverted
(`SetEngine.lookup_reverse` no longer fills `excluded_node_ids`), every
`test_lookup_oracle_gate_*` stays green (the row's first-hand run, 2026-10-13d). Why?

## 2. Reproduction of the gap (PROBE, 2026-10-14)

The mutant was applied WITHOUT touching `src/`: a pytest plugin,
`.scratch/now-next/probes/scout-TK142/tk142_drop_excl_plugin.py`, replaces
`zanzibar.setengine.engine.SetEngine.lookup_reverse` at `pytest_configure` with the pre-TK139
body (`node_ids = pos`, `markers = stars`, `excluded_node_ids` left empty). Command:

```
PYTHONPATH=.scratch/now-next/probes/scout-TK142 <env>/python.exe -m pytest \
  -p tk142_drop_excl_plugin tests/test_lookup_oracle.py tests/test_lookup_hypothesis.py \
  tests/test_tk139_lookup_reverse_exclusions.py -q -p no:cacheprovider -rf
```

Result: `9 failed, 61 passed in 242.22s (0:04:02)`, rc 1. The patch is proven live
(instrument control) by the reds it DID cause:

```
FAILED tests/test_lookup_oracle.py::test_lookup_oracle_dense_boolean - Failed...
FAILED tests/test_lookup_oracle.py::test_tamper_set_reverse_is_caught[py] - A...
FAILED tests/test_lookup_oracle.py::test_tamper_set_reverse_is_caught[roaring]
FAILED tests/test_tk139_lookup_reverse_exclusions.py::test_p05_repro_both_backends_agree[py]
FAILED tests/test_tk139_lookup_reverse_exclusions.py::test_p05_repro_both_backends_agree[roaring]
FAILED tests/test_tk139_lookup_reverse_exclusions.py::test_mixed_grants_both_backends_agree[py]
FAILED tests/test_tk139_lookup_reverse_exclusions.py::test_mixed_grants_both_backends_agree[roaring]
FAILED tests/test_tk139_lookup_reverse_exclusions.py::test_excluded_keys_is_the_portable_exclusion_channel[py]
FAILED tests/test_tk139_lookup_reverse_exclusions.py::test_excluded_keys_is_the_portable_exclusion_channel[roaring]
```

GREEN under the mutant: all nine `test_lookup_oracle_gate_*` items AND the whole of
`tests/test_lookup_hypothesis.py` (including `TestLookupSurfaceMachine`, the hypothesis
stateful walk over the same four fixed corpora). This widens the row: the stateful lookup
machine is a second broad net with the same hole (PROBE).

## 3. The cause: the gates never see a non-empty `neg` (PROBE, 2026-10-14)

S3's structural equality `res.excluded_node_ids == set(m.neg)` fires on the FIRST state in
which some `expand(obj).neg` is non-empty. So the gates stay green iff no gate state ever has
one. Probe `p1_neg_census.py` wraps `_check_set_reverse` with a counter and replays each
fixed gate exactly as `_run_gate` runs it (same schema, pool, seed, walk_steps):

```
== gate_wildcards seed=0 steps=8 pool=48: S3 calls=480 neg-nonempty=0
== gate_wildcards seed=1 steps=8 pool=48: S3 calls=480 neg-nonempty=0
== gate_boolean seed=0 steps=8 pool=22: S3 calls=768 neg-nonempty=0
== gate_boolean seed=1 steps=8 pool=22: S3 calls=768 neg-nonempty=0
== gate_demorgans_reverse seed=0 steps=6 pool=7: S3 calls=700 neg-nonempty=0
== gate_owc_star_ttu seed=0 steps=6 pool=38: S3 calls=608 neg-nonempty=0
== gate_owc_star_ttu seed=1 steps=6 pool=38: S3 calls=760 neg-nonempty=0
```

**Zero of 4,564 S3 calls saw a non-empty `neg`.** Per gate, the reason (PROBE for the walk
histories, READ for the schemas):

| gate | schema shape | why no `neg` |
|---|---|---|
| `_gate_wildcards` (seeds 0,1) | `tests/fga_schemas/wildcards.fga`, pure union | STRUCTURAL: no `and` / `but not`, so `neg` is impossible on any state. |
| `_gate_owc_star_ttu` (seeds 0,1) | `owc_star_ttu.fga`: `restricted: editor but not blocked`, `editor: [user, group#member]` | STRUCTURAL: the only exclusion's base has no star, and `neg` lives only inside starred shapes (`memberset.py::_normalize`, `neg = starpop - E`). |
| `_gate_boolean` (seeds 0,1, 8 steps) | `boolean_wildcards.fga`: `viewer: (public but not blocked) or editor`, `public: [user:*]` | WALK: the shape IS reachable (that is `test_lookup_oracle_dense_boolean`'s script) but needs a `user:* public doc:dN` grant, which is 2 of the 22 pool tuples (`tests/test_matrix.py::_boolean_pool`), and neither seed draws one. Both seeds DO add `u1 blocked d1`. Seed 0 accepted adds: `g2 editor d1`, `u1 member g2`, `u2 editor d2`, `u2 editor d1`, `u1 blocked d1`, `g1 editor d1`; seed 1: `g1 member g2`, `u2 member g1`, `u2 editor d2`, `u1 blocked d1`, `u1 member g1`, `u1 member g2`. |
| `_gate_demorgans_reverse` (seed 0, 6 steps) | `demorgans_reverse.fga`: `attr.does_not_label: _all_docs but not labels`, `_all_docs: [doc:*]` | WALK: needs `doc:* _all_docs attr:at1` plus `doc:dc1 labels attr:at1`. The 7-tuple pool has both; seed 0 adds the latter and `doc:* _all_docs cond:c1` (the wrong object type), never the former. |
| `_gate_generated_schemas` (6 examples, ci) | `tests/test_hypothesis.py::schema_asts` | RATE: see below. |

**The generated-schema gate reaches the shape about once in 240 draws** (PROBE,
`p2_generated_neg_rate.py`, the seeded `_schema_ast(_RandomChoices(random.Random(seed)))` seam
for seed in range(240), with the gate's op shape -- 1..4 unique ops from `_op_pool`, added then
removed -- emulated with a seeded rng, set engine only):

```
seeds with non-empty pool: 240
structurally neg-capable (bool op + [user:*] somewhere): 214/240
emulated gate walk (1..4 ops) reaching a non-empty neg: 1/240
all-pool state reaching a non-empty neg: 22/240
```

At 6 examples per ci run that is roughly a 2.5% chance per run of the gate seeing the shape at
all (REASONED: 1 - (239/240)^6), which is why it "did NOT catch it" in the TK139 sabotage.
The "structurally neg-capable" line is a loose syntactic test (any `and`/`but not` plus any
starred restriction anywhere, the tupleset's `doc:*` included); section 4.2 measures the real
ceiling, which is much lower (18/240 schemas have ANY two-op state with a `neg`). Both the
generator distribution and the op draw are bottlenecks.

## 4. Where the reach bottleneck is (PROBE, 2026-10-14)

### 4.1 Fixed fixtures: the seeds, not the schemas

`p3_reach.py` part A replays `_run_gate`'s EXACT rng sequence on the set engine alone (the
real gate asserts set-side accept == graph-side accept, so the same ops apply) for seeds
0..11 and several `walk_steps`; `seed:hits/states` = states with some non-empty `neg` /
states visited (walk + drain):

```
A boolean steps=8: reached 1/12  [0:0/12 1:0/12 2:0/12 3:0/14 4:3/14 5:0/10 6:0/12 7:0/14 8:0/14 9:0/14 10:0/12 11:0/14]
A boolean steps=12: reached 3/12  [0:0/16 1:0/18 2:0/14 3:4/22 4:1/16 5:2/16 6:0/18 7:0/22 8:0/18 9:0/20 10:0/20 11:0/20]
A boolean steps=16: reached 5/12  [0:0/20 1:0/24 2:0/18 3:4/30 4:1/24 5:6/22 6:0/20 7:1/26 8:0/26 9:0/20 10:0/24 11:11/28]
A boolean steps=24: reached 6/12  [0:0/32 1:3/32 2:0/24 3:3/42 4:1/32 5:7/34 6:0/30 7:2/40 8:0/36 9:0/28 10:0/34 11:6/36]
A demorgans_reverse steps=6: reached 5/12  [0:0/10 1:5/10 2:0/10 3:4/12 4:5/10 5:0/8 6:0/10 7:0/10 8:4/10 9:2/10 10:0/10 11:0/10]
A demorgans_reverse steps=8: reached 10/12  [0:1/14 1:5/12 2:0/14 3:4/14 4:6/14 5:0/8 6:5/14 7:4/14 8:10/14 9:4/14 10:1/12 11:2/14]
A demorgans_reverse steps=12: reached 12/12  [0:2/16 1:8/18 2:5/18 3:7/18 4:8/16 5:2/16 6:7/18 7:5/16 8:11/18 9:5/18 10:6/18 11:4/18]
```

So the boolean gate's seeds 0 and 1 are both unlucky (seed 0 never reaches the shape, even at
24 steps). `demorgans_reverse` seed 0 reaches it from 8 steps on, and EVERY seed does at 12.

**Raising `walk_steps` keeps the existing walk as a prefix** (REASONED from
`tests/test_lookup_oracle.py::_run_gate`: iteration i consumes `rng.random()` / `rng.choice`
only as a function of the state built by iterations < i, so the first 6 iterations are
identical at `walk_steps=6`, 8 or 12; only the drain order after the walk changes). Part A
is consistent with that: seed 0 visits 10 states at 6 steps and 14 at 8.

A shape-stratified op draw (pick a restriction shape uniformly, then a tuple of it) is NOT a
fix (PROBE, `p4_stratified.py`): the boolean walk at 8 steps reaches the shape on 3/12 seeds
(4, 9, 10) instead of 1/12. The boolean shape needs a conjunction (a `user:*` public grant,
a `blocked` on the same doc, and that user NOT an editor), and no draw reweighting makes
that likely in 8 steps.

### 4.2 Generated schemas: the op draw AND the generator

`p3_reach.py` part B and `p4_stratified.py`, over the same 240 seeded schemas:

```
B generated: pools=240  pair-reachable=18  gate-draw(1..4)=0  8-ops=6
S-gen uniform    ops=1..4: 1/240
S-gen uniform    ops=4: 1/240
S-gen uniform    ops=6: 7/240
S-gen stratified ops=1..4: 1/240
S-gen stratified ops=4: 2/240
S-gen stratified ops=6: 4/240
```

* Only **18/240 (7.5%) schemas have ANY two-op state with a non-empty `neg`** (exhaustive
  over pool pairs). So even a perfect op draw would see the shape on about 1 example in 13.
* The gate's own draw (1..4 random ops) hits it 0 or 1 times in 240; 6 to 8 ops, 4 to 7.
* `p5_same_relation_arms.py` refuted one guess (my REASONED hypothesis, wrong): the Direct
  arms of one relation are NOT self-cancelling. `define r0: [user, user:*] but not [user]`
  with `user:* r0 doc:d1` and `user:u1 r0 doc:d1` gives `pos=[] stars=[('user', '...')]
  neg=[('user', 'u1', '...')]` (each Direct arm filters by its restriction). 180/240
  generated schemas contain an Exclusion, and 160/240 have one with a non-plain-Direct arm.
  The 7.5% comes from needing a star-capable base AND a concrete subtrahend on the same
  object, which the per-node draws in `tests/test_hypothesis.py::_schema_ast` rarely line up
  (REASONED).
* **Widening the generator is NOT proposed.** It is shared by the whole hypothesis campaign
  and its rate floors. The plan below searches the existing distribution instead.

## 5. The gap is symmetric: the graph side has it too (PROBE, 2026-10-14)

`p7_fixed_gate_params.py` mode `g1` patches
`src/zanzibar/graphindex/wildcard.py::WildcardIndex.lookup_reverse` to clear
`excluded_node_ids` after the real call, and runs the real `_run_gate` with the CURRENT
parameters:

```
demorgans6 g1: GREEN in 22.0s; tripwire set_neg=0 graph_excl=0
boolean0 g1: GREEN in 16.5s; tripwire set_neg=0 graph_excl=0
boolean1 g1: GREEN in 16.8s; tripwire set_neg=0 graph_excl=0
```

So the graph's G3/G4 exclusion half is just as unexercised by the fixed gates: the same states
are missing. The module's comment above `_run_scripted` already records one instance of this
class (READ): "an injected neg-drop in the graph's forward residue scan survived the walks
because no seed had combined a star grant with an exclusion on one object". The plan
therefore counts BOTH sides. `TestLookupSurfaceMachine` was not run under `g1` (UNVERIFIED;
REASONED to be green for the same reason it is green under M1).

## 6. Candidate strengthenings, measured (PROBE, 2026-10-14)

### 6.1 Fixed gates with chosen parameters (`p7_fixed_gate_params.py`, the real `_run_gate`)

Counters: `set_neg` = S3 calls whose `expand.neg` is non-empty; `graph_excl` = graph
`lookup_reverse` results with non-empty `excluded_node_ids`. `demorgans8` =
`demorgans_reverse.fga`, seed 0, `walk_steps=8`; `boolean4` = `boolean_wildcards.fga`, seed
4, `walk_steps=8`.

```
demorgans8 honest: GREEN in 37.3s; tripwire set_neg=4 graph_excl=2
demorgans12 honest: GREEN in 44.6s; tripwire set_neg=8 graph_excl=4
boolean4 honest: GREEN in 35.4s; tripwire set_neg=6 graph_excl=3
demorgans8 m1: RED in 19.4s; tripwire set_neg=1 graph_excl=2
   lookup/oracle divergence (seed=0): set.lookup_reverse('does_not_label', 'attr', 'at1') [py]: excluded_node_ids set() != expand.neg {9}
demorgans8 g1: RED in 17.9s; tripwire set_neg=0 graph_excl=0
   lookup/oracle divergence (seed=0): graph.lookup_reverse('does_not_label', 'attr', 'at1') vs oracle on subject (...,doc,dc1): graph=True oracle=False
demorgans12 m1: RED in 18.3s; tripwire set_neg=1 graph_excl=2
   lookup/oracle divergence (seed=0): set.lookup_reverse('does_not_label', 'attr', 'at1') [py]: excluded_node_ids set() != expand.neg {9}
demorgans12 g1: RED in 17.6s; tripwire set_neg=0 graph_excl=0
   lookup/oracle divergence (seed=0): graph.lookup_reverse('does_not_label', 'attr', 'at1') vs oracle on subject (...,doc,dc1): graph=True oracle=False
boolean4 m1: RED in 16.6s; tripwire set_neg=1 graph_excl=1
   lookup/oracle divergence (seed=4): set.lookup_reverse('viewer', 'doc', 'd1') [py]: excluded_node_ids set() != expand.neg {0}
boolean4 g1: RED in 17.6s; tripwire set_neg=0 graph_excl=0
   lookup/oracle divergence (seed=4): graph.lookup_reverse('viewer', 'doc', 'd1') vs oracle on subject (...,user,u1): graph=True oracle=False
```

Baseline durations, unpatched (PROBE, `pytest tests/test_lookup_oracle.py -k "gate or
dense_boolean" -q --durations=0`, 2026-10-14): `gate_demorgans_reverse` 24.02s,
`gate_boolean[0]` 21.74s, `gate_boolean[1]` 21.53s, `gate_generated_schemas` 17.14s,
`dense_boolean` 25.90s; `10 passed, 37 deselected in 220.89s`.

### 6.2 A deterministic generated-schema witness gate (`p6_witness_gate.py`)

For `seed in range(240)`: `ast = _schema_ast(_RandomChoices(random.Random(seed)))`. This is
the SAME generator body hypothesis drives, through the seam
`test_lookup_oracle_gate_generated_schemas_graph_join_rate` already uses. Search a two-op
WITNESS: one star tuple `s` and one concrete tuple `c` on the same object `(type, name)`
such that some set-side `expand(obj).neg` is non-empty after adding both. On a witness, run
the FULL battery (`_Gate.assert_surfaces`: the graph when it joins, both SetOps, oracle
two-sided) after `add s`, `add c`, `remove c`, `remove s`. Stop after K=3 witnessed schemas.

```
mode=honest
  witness seed=4 graph=False s=('...', 'user', '*', 'r1', 'doc', 'd1') c=('...', 'user', 'u1', 'r0', 'doc', 'd1')  t=2.5s
  witness seed=11 graph=True s=('...', 'user', '*', 'r3', 'doc', 'd1') c=('...', 'user', 'u1', 'r3', 'doc', 'd1')  t=17.9s
  witness seed=28 graph=True s=('...', 'user', '*', 'r0', 'doc', 'd1') c=('...', 'user', 'u1', 'r0', 'doc', 'd1')  t=35.8s
witnessed 3/3 after searching 29 seeds, 35.8s
RESULT: GREEN

mode=m1
RESULT: RED (pytest.fail)
lookup/oracle divergence (witness seed=4 add ('...', 'user', 'u1', 'r0', 'doc', 'd1')): set.lookup_reverse('r1', 'doc', 'd1') [py]: excluded_node_ids set() != expand.neg {2}

mode=m2   (M1, and S3's structural equality neutralised by handing the checker a neg-free MemberSet)
RESULT: RED (pytest.fail)
lookup/oracle divergence (witness seed=4 add ('...', 'user', 'u1', 'r0', 'doc', 'd1')): set.lookup_reverse('r1', 'doc', 'd1') [py] vs oracle on subject (...,user,u1): set=True oracle=False (node_ids, or a marker minus excluded_node_ids)

mode=g1
  witness seed=4 graph=False s=('...', 'user', '*', 'r1', 'doc', 'd1') c=('...', 'user', 'u1', 'r0', 'doc', 'd1')  t=2.0s
RESULT: RED (pytest.fail)
lookup/oracle divergence (witness seed=11 add ('...', 'user', 'u1', 'r3', 'doc', 'd1')): graph.lookup_reverse('r3', 'doc', 'd1') vs oracle on subject (...,user,u1): graph=True oracle=False
```

The witness SEARCH uses set-side `expand`, which the M1 and G1 mutants do not touch, so the
instrument is independent of the subject (REASONED). If a future change makes `expand` lose
`neg`, the search finds nothing and the count tripwire goes red instead, loudly.

## 7. The plan (REASONED from sections 3-6; every number it relies on is PROBE above)

Scope decision (scout's recommendation, for the coordinator to record): strengthen the
EXISTING broad gates by giving them states that carry an exclusion, and make the coverage
mechanical with a count tripwire, on BOTH backends. Do not widen `schema_asts` /
`_schema_ast` (shared with the whole hypothesis campaign and its floors), do not change
`_run_gate`'s walk algorithm (every fixed gate's states would move), and do not add one more
scripted pin (the dense script already exists; it is exactly what the walks lack).

All edits are in ONE file, `tests/test_lookup_oracle.py`. No `src/` change.

1. **Count the shape in `_Gate`** (`tests/test_lookup_oracle.py::_Gate`). In `__init__`
   add `self.set_reverse_neg = 0` and `self.graph_reverse_excl = 0` beside the existing
   `self.set_checks`. In `_Gate.assert_surfaces`, in the graph reverse loop, bind
   `res = self.graph.widx.lookup_reverse(*obj)`, add 1 to `graph_reverse_excl` when
   `res.excluded_node_ids` is non-empty, then call `_check_graph_reverse` with `res`. In the
   set loop, after `m = se.expand(*obj)`, add 1 to `set_reverse_neg` when `len(m.neg)` is
   non-zero (`MemberSet.neg` is a `SetOps` frozen set, PySets or Roaring; `len` works on
   both, REASONED; `p1` used `len(set(m.neg))`, which is certainly safe). Additive only:
   the other importers of `_Gate` (`tests/test_lookup_hypothesis.py`,
   `tests/test_irrelevant_alternatives.py`, `tests/test_owc_star_parent_cross.py`, READ by
   grep 2026-10-14) are unaffected.
2. **Return the gate from `_run_gate`** (`::_run_gate`, currently returns None; the counters
   stay readable after `gate.close()`). Its existing callers ignore the return value.
3. **`test_lookup_oracle_gate_demorgans_reverse`: `walk_steps` 6 -> 12**, then assert
   `gate.set_reverse_neg > 0 and gate.graph_reverse_excl > 0`, the message naming TK142
   and saying how to re-pick (the `p3` replay recipe, section 4.1). The 6-step walk stays a
   prefix (section 4.1). Measured at 12: GREEN, `set_neg=8 graph_excl=4`, 44.6s, and every
   seed 0..11 reaches the shape there, so the choice is robust to small pool or walk drift.
   (8 steps also reaches it, but on 1 of 14 states only: `set_neg=4 graph_excl=2`, 37.3s.)
4. **`test_lookup_oracle_gate_boolean`: seeds `[0, 1]` -> `[0, 1, 4]`** with a module
   constant `_BOOLEAN_EXCLUSION_SEEDS = frozenset({4})`, and the same two-counter assertion
   when `seed in _BOOLEAN_EXCLUSION_SEEDS`. Seeds 0 and 1 are kept for the states they have
   always covered (they measure 0 exclusion states; section 4.1). Seed 4 at 8 steps:
   GREEN, `set_neg=6 graph_excl=3`, 35.4s. Do NOT raise `walk_steps` here instead: seed 0
   never reaches the shape even at 24 steps.
5. **New `test_lookup_oracle_gate_generated_schemas_exclusion_witness`** (the `p6` shape,
   section 6.2): a module helper `_exclusion_witness(schema, pool, objects)` (one star
   tuple plus one concrete tuple on the same object, set-only `expand` search, add and
   remove both so the side ends empty), seeds `range(240)` through
   `_schema_ast(_RandomChoices(random.Random(seed)))`, the full `_Gate.assert_surfaces`
   battery after each of the four ops (`allow_graph_absent=True` on an
   `UnsupportedByGraphIndex`, asserting `match_rejection(exc) is not None` exactly as the
   generated gate does), stop at K=3 witnessed schemas. Tripwires: `witnessed == 3`; at
   least one witnessed schema joined the graph; summed `set_reverse_neg > 0` and
   `graph_reverse_excl > 0`. Measured: witnesses at seeds 4 (graph refused), 11 and 28
   (graph joined), 29 seeds searched, 35.8s. It is deterministic, so the catch does not
   depend on hypothesis luck, and it runs the broad battery over generated schemas rather
   than a hand-picked state.
6. **Docstrings.** (a) The module docstring's S3 paragraph ends "The generated-schema gate
   (6 examples, ci profile) did NOT catch it; dense_boolean and
   test_tamper_set_reverse_is_caught did." Append a dated TK142 sentence: why (section 3,
   zero of 4,564 S3 calls), and which gates now catch it. (b) Each changed or new test's
   docstring records its literal sabotage output (section 8), per
   `docs/sabotage-procedure.md`. (c) The dense-block comment above `_run_scripted` gains
   one line pointing at the tripwires.
7. **Gate housekeeping** (section 9): `python -m formal.conformance.doc_counts --generate`,
   then the full phased gate.

Not proposed, with the reason:
* Prepending a witness to `test_lookup_oracle_gate_generated_schemas`'s hypothesis draw. At
  most 7.5% of schemas have a witness, so a 6-example run would still miss most of the
  time; step 5 is the deterministic version.
* A tripwire on `tests/test_lookup_hypothesis.py::LookupSurfaceMachine`. It has the same hole
  (section 2), but per-run counters across a stateful machine need an aggregate the module
  does not have. Record it as a residual on the row; steps 3-5 already make the gate
  catch the regression deterministically.

## 8. Tests to add or change, and the sabotage for each

| test | change | sabotage | expected (from the probes; re-observe on the real test) |
|---|---|---|---|
| `::test_lookup_oracle_gate_demorgans_reverse` | walk 12 + tripwire | M1: `SetEngine.lookup_reverse` drops exclusions (plugin `tk142_drop_excl_plugin.py`, or a temp edit with a byte-copy restore) | RED: `set.lookup_reverse('does_not_label', 'attr', 'at1') [py]: excluded_node_ids set() != expand.neg {9}` |
| same | | G1: `WildcardIndex.lookup_reverse` clears `excluded_node_ids` | RED: `graph.lookup_reverse('does_not_label', 'attr', 'at1') vs oracle on subject (...,doc,dc1): graph=True oracle=False` |
| same | | T1 (tripwire live): `walk_steps` back to 6 | RED on the tripwire assertion (counts 0/0, per `demorgans6`) |
| `::test_lookup_oracle_gate_boolean[4]` | new seed + tripwire | M1 | RED: `set.lookup_reverse('viewer', 'doc', 'd1') [py]: excluded_node_ids set() != expand.neg {0}` |
| same | | G1 | RED: `graph.lookup_reverse('viewer', 'doc', 'd1') vs oracle on subject (...,user,u1): graph=True oracle=False` |
| same | | T2: `_BOOLEAN_EXCLUSION_SEEDS = {0}` (or seed 4 -> 0) | RED on the tripwire (counts 0/0, per `boolean0`) |
| `::test_lookup_oracle_gate_generated_schemas_exclusion_witness` | new | M1 | RED at witness seed 4: `set.lookup_reverse('r1', 'doc', 'd1') [py]: excluded_node_ids set() != expand.neg {2}` |
| same | | M2 (instrument control: M1 plus S3's structural equality neutralised) | RED by the oracle half: `... vs oracle on subject (...,user,u1): set=True oracle=False (node_ids, or a marker minus excluded_node_ids)` |
| same | | G1 | RED at witness seed 11: `graph.lookup_reverse('r3', 'doc', 'd1') vs oracle on subject (...,user,u1): graph=True oracle=False` |
| same | | T3: the witness search refuses every pair (for example require `c[2] == '*'`) | RED on `witnessed == 3` (0 witnessed) |
| the row's original M1 | | `result.excluded_node_ids = set(m.neg)` -> `pass` in `src/zanzibar/setengine/engine.py::SetEngine.lookup_reverse`, then `pytest tests/test_lookup_oracle.py -k gate` | was `9 passed, 38 deselected` (2026-10-13d); must now show the three gates above failing |

Restore discipline (CLAUDE.md, the sabotage procedure): byte copies of any edited file,
`grep -c "SABOTAGE"` = 0 afterwards, `git diff src/` empty. Prefer the plugin for M1/G1 (no
`src/` edit at all). Never `git stash` or `git checkout --`.

## 9. Gate impact (READ unless stated)

* **Floors.** `tests/` gains 2 collected tests (`gate_boolean[4]` and the witness test):
  2401 -> 2403 by REASONED arithmetic against the 2026-10-14 ledger (`collected=2401` in
  `.gate-runs/ledger.tsv`). Re-measure with `pytest tests/ -q --collect-only`. `formal/verify.sh`
  step 4e (`doc_counts --check`, `doc_counts.py::floor_headroom`) refuses a floor below the
  live count, so run `python -m formal.conformance.doc_counts --generate`, which ratchets
  `MIN_TESTS_ALL` upward (TK99, `doc_counts.py::ratchet_floors`) and regenerates the
  `formal/FINAL_REVIEW.md` counts block. `MIN_CONF_ALL` is untouched (no conformance change).
  Floors only go up.
* **Snapshots.** None touched (`tests/snapshots/` is compiled-RuleSet byte identity).
* **CORRESPONDENCE anchors and claim_rot.** No `src/` symbol changes, so
  `formal/correspondence_anchor_pin.txt` is untouched (its lookup entries are
  `SetEngine.lookup_reverse`, `WildcardIndex.lookup_reverse` and
  `ReachabilityIndex.lookup_reverse`, all `src/`). `formal/CORRESPONDENCE.md` mentions
  `tests/test_lookup_oracle.py` in prose only (lines 287, 1244, 1909, 1920 as of
  2026-10-14), with no `::` anchor into it.
* **Time.** About +92s of `tests/` wall time (REASONED: demorgans 24s -> ~45s, plus ~35s for
  `gate_boolean[4]`, plus ~36s for the witness test), spread over the four tiles by index mod
  4. The 2026-10-14 tiles ran 254-366s against the ~10 min harness cap.
* **The doc edits stale `lean`.** Write the session records first, then run the gate.

## 10. Risks and collisions with other open items

* **`TK138` (same file).** `docs/tk138-userset-self-relation-2026-10-14.md` discusses
  changing `tests/test_lookup_oracle.py::_subject_candidates` (self-shaped userset subjects).
  That is a textual collision on the same module, not a semantic one: the counters do not
  depend on the candidate grid. Land in sequence and re-run the three gates.
* **`TK137` (generator text and shapes).** Its plan lists `tests/test_lookup_oracle.py:575,656`
  among the `unparse_schema_ast` re-parse sites, and considers refusing `Exclusion(Computed,
  Direct)` shapes (S5/S6). If TK137 removes shapes from the generator, the witness seeds
  (4, 11, 28) move. The witness test searches dynamically, so it adapts; if the starred
  exclusion disappears from the generated space altogether, the `witnessed == 3` tripwire
  goes red, which is the intended loud failure. Re-run `p6` after TK137 lands.
* **`TK123` (`connectedstore` -> `store` rename).** No collision: neither
  `tests/test_lookup_oracle.py` nor `tests/parity.py` imports `connectedstore` (READ, grep
  2026-10-14).
* **`TK119` / `TK132` (Lean).** No overlap: this is tests-only Python.
* **Seed fragility.** Seed 4 (boolean) and the 12-step demorgans walk reach the shape because
  of `random.Random`'s sequence over today's pools (`tests/test_matrix.py::_boolean_pool`,
  `::_demorgan_pool`). A pool reorder could move them. The tripwire makes that a red with
  instructions, never a silent loss. Re-pick with the `p3` replay recipe and never delete the
  assertion.
* **The hypothesis stateful machine stays blind** (section 7, "Not proposed"). Record it on
  the row as a residual.
