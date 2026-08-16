# Coverage cells + swarm testing + an un-hardcoded TTU tupleset

> **FROZEN 2026-08-16 — provenance, not a living document.** Status lines below are
> as-of-then and several are now false; live state: `HANDOFF.md` + the session ledger.
> Corrections are appended dated at the top, never edited into the body.
>
> ⚠ **This leg LANDED on 2026-08-11, and where this document and the archive disagree,
> trust the archive.** `docs/history/handoff-status-2026-08.md` §1b records three
> implementation corrections found while actually building what is designed here; they
> were never folded back into this file. The "Status" line immediately below was written
> before the leg landed and is retained unedited as provenance.

**Status (as of 2026-08-10, superseded — see the banner above):** design + validated
prototype. Nothing in the repo was modified.
Prototype code: `C:\Users\user\AppData\Local\Temp\zz_*.py` (see §7 for the file map).
All numbers below were measured on this machine on 2026-08-10 against
`graph-reachability-zanzibar-index@e136c8c` with
`C:\Users\user\anaconda3\envs\graph-reachability-zanzibar-index\python.exe`, hypothesis 6.160.0.

---

## 0. The headline number

| measurement | value |
|---|---|
| derived feature alphabet | **51** features, from **6** source-of-truth sites |
| cell universe (2-wise) | **1275** cells |
| cells reached by the CURRENT generators at their **ceiling** (400 draws each) | **514 / 1275 = 40.3 %** |
| cells reached by the current generators under the **`ci` budget** (`max_examples=12`, 6 seeds) | **469 – 514** — i.e. **91–100 % of the ceiling** |
| features never reached at any budget | **15 / 51** |

Read those last two rows together. **The `ci` budget already saturates the current
generators.** Raising `max_examples` buys essentially nothing: seed 1 at 12 examples hits
514 cells, and 400 examples also hits 514. The blind spot is **grammar reachability, not
sampling budget** — exactly the framing in the task. Any proposal that answers this with
"run more examples" is answering the wrong question.

The 15 unreachable features, verbatim from `zz_measure.py`:

```
leaf:derived-tupleset-ttu     plan:PDerivedTuplesetTTU     via:tupleset-ttu
ttu.ts:Computed  ttu.ts:Exclusion  ttu.ts:Intersection  ttu.ts:TTU  ttu.ts:Union
ttu.ts:multitype  ttu.ts:neg-only-type  ttu.ts:tainted  ttu.ts:undeclared
ttu.ts.restr:userset          ttu.ts.restr:wildcard-userset
schema:multi-type
```

Ten of the fifteen are `ttu.ts:*` — the TTU tupleset axis that `schema_asts` hardcodes.
Three more (`leaf:derived-tupleset-ttu`, `plan:PDerivedTuplesetTTU`, `via:tupleset-ttu`)
are the *compiled consequences* of a structured tupleset, i.e. the same hole seen from the
compiler's side. So **13 of the 15 holes are one hole**, and it is the hole both of this
week's bugs came through.

### A second finding, measured while instrumenting (`zz_drop.py`)

> ✅ **FIXED 2026-08-10 in `d0dbefa`; the figures below are the PRE-FIX diagnosis, kept
> because they are the evidence.** `BoolStarBridgeParityMachine.setup` now asserts
> `self.pe.graph is not None` on the `in_fragment` stratum
> (`tests/test_hypothesis.py:1886`) and routes boundary draws through a recorded scope
> rejection; the rate went **13 % → 76–82 % 4-way** and **0 % → 49–55 %** boolean-4-way,
> with the rate itself now floored (`_BSB_FOUR_WAY_FLOOR`). ⚠ The sharp form of the
> finding — worse than this section states — is in `docs/sabotage-procedure.md:31`: **all
> 768 `and`/`but not` configs were rejected for every OWC subset, so the 13 % that DID run
> 4-way were exactly the `or` draws. It had tested booleans against the graph index ZERO
> times, ever.**

The G1 generator — described in the source as "the audit's headline blind spot" closer —
runs the graph index on **12 %** of its draws:

```
bool_star_bridge:4-way (graph joins)               48 / 400  (12%)
bool_star_bridge:3-way (GRAPH DROPPED)            236 / 400  (59%)
bool_star_bridge:SKIPPED (doubly bridged)         116 / 400  (29%)
star_bridge:4-way (graph joins)                   155 / 400  (39%)
star_bridge:SKIPPED (doubly bridged)              245 / 400  (61%)
```

`StarBridgeParityMachine.setup` asserts `self.pe.graph is not None` and so *cannot* fuzz
3-way blind. `BoolStarBridgeParityMachine.setup` has **no such assertion**, and 59 % of its
draws are `UnsupportedByGraphIndex` → `ParityEngine` sets `self.graph = None` → the machine
happily runs oracle + two set engines and reports green. At `ci`'s `max_examples=12` that is
**~1.4 draws per run** in which the boolean × star-bridge cross actually touches the graph
index. This is a house-failure-mode instance in its own right (`docs/sabotage-procedure.md`
row "the validation matrix — silently halved") and it is a one-line fix; see §4 sabotage 7.
(It was **not** in the end a one-line fix: asserting the invariant required *drawing* the
boolean arm's placement, so that `downstream` is in-fragment for every op while `target`
only appears in an explicit scope-boundary stratum where the rejection is the asserted
contract.)

---

## 1. The cell taxonomy

### 1.1 Design choice: pairwise cells, not a cartesian grid

A cartesian grid over the feature dimensions is `2^51`. A hand-picked sub-grid is a
hand-written "what should exist" list — rank-2-at-best on the durability ranking, and the
exact thing `_REQUIRED_LEAF_KINDS`'s companion test exists to prevent.

Instead: **a cell is an unordered pair of atomic features that co-occur in one compiled,
driven configuration.** Rationale, not aesthetics: both bugs this week are 2-way or 3-way
interactions (TTU × exclusion-on-tupleset; OWC × star-parent × TTU), and combinatorial
testing's standard result is that most interaction faults are 2- or 3-way. Pairwise gives a
cell space that is (a) mechanically derived, (b) large enough to be informative (1275), and
(c) small enough to enumerate and report.

`|A| = 51 → C(51,2) = 1275`.

### 1.2 The alphabet is DERIVED, from six sites

`zz_cells.py` mints every feature name from the compiler, never from a literal list. Each
derivation carries its own anti-vacuity assert (an empty derivation would make the coverage
assertion pass over an empty universe — the failure mode the existing
`test_required_leaf_kinds_are_exactly_the_compilers_kinds` was written to close, generalised).

| # | source of truth | mechanism | derived values (measured) |
|---|---|---|---|
| 1 | `zanzibar_utils_v1.Expr` union alias | `typing.get_args` | `Computed Direct Exclusion Intersection TTU Union` (6) |
| 2 | `LeafSpec(..., '<kind>')` literals in `_plan_leaves` | `inspect.getsource` + regex (the **same regex the existing floor uses**) | `closure derived-computed derived-ttu derived-tupleset-ttu derived-userset` (5) |
| 3 | `isinstance(n, …)` dispatch inside `_plan_leaves` | source regex, cross-checked with `is_dataclass` | `PClosureLeaf PDerivedComputed PDerivedTTU PDerivedTuplesetTTU PDerivedUserset PExclusion PIntersection PUnion` (8) |
| 4 | `DependentEdge(key, '<via>')` literals | source regex over the module | `computed ttu tupleset-ttu userset` (4) |
| 5 | the single `LeafFamily(… kind=(a if … else b))` site | source regex | `closure userset-storage` (2) |
| 6 | `Restriction` **dataclass fields** | `dataclasses.fields`, asserting `{type, predicate, wildcard} ⊆ fields` | `concrete subject-wildcard userset wildcard-userset` (4) |

Note site 3 in particular. Deriving the plan-node classes by "every `P*` dataclass in the
module" is the tempting version, and it is **wrong**: it swept in `Plan` and reported 9
classes. Deriving them from the walker's own `isinstance` dispatch gives 8 and is the
semantically correct set — a plan node type `_plan_leaves` does not dispatch on is a node
type no leaf coverage can be claimed for. This is the instrument bug I hit while building
the instrument; it is recorded because it is the pattern the sabotage procedure warns about.

On top of sites 1–6 the alphabet adds the axes this task is about, all of which are
*compositions* of derived values rather than new literals — the TTU-scoped projection of
site 1 (`ttu.ts:<ExprClass>`), of site 6 (`ttu.ts.restr:<modality>`), and eight
schema/TTU modality flags (`ttu.ts:multitype`, `ttu.ts:tainted`, `ttu.ts:neg-only-type`,
`ttu.ts:undeclared`, `ttu.ts:owc`, `ttu.target:tainted`, `ttu:self-target`, plus
`schema:{owc,neg-leaf,storage-leaf,multi-stratum,multi-type}`). Those eight *are* hand-named
predicates; they are the irreducible "what do we think matters" content of the design and
§4 sabotage 1 is how they earn their place. Everything else in the alphabet grows and
shrinks with the compiler automatically.

`51 = 6 + 5 + 8 + 4 + 2 + 4 (derived) + 6 + 1 + 4 (TTU projections) + 6 + 5 (modality flags)`.

### 1.3 Reachability: three classes, and the whole point of the exercise

Every cell is classified per run into exactly one of:

* **HIT** — some configuration in the run compiled *and was driven* with both features
  present, and the driven comparison count for that configuration was `> 0`.
* **REJ (unreachable by design)** — the cell carries a **rejection witness**: a concrete
  `(schema_text, owc)` pair, stored next to the cell, which the test *compiles* and asserts
  raises `UnsupportedByGraphIndex` / `DoublyBridgedShapeError` / `CyclicDerivedDependency`
  with a message matching a stored substring.
* **UNKNOWN** — neither. **The assertion is `UNKNOWN == ∅`.**

This is the mechanism that separates "unreachable by design" from "unreachable by generator
gap", and it is deliberately built as a *positive, re-executed claim* rather than an
exemption list:

* a hand-written `EXPECTED_UNREACHABLE` list is a future silent pass — the day the compiler
  starts admitting a shape, the list still says "unreachable" and the gate stays green;
* a **rejection witness** inverts that. The moment the compiler admits the witness the
  `pytest.raises` fails, the exemption is revoked, and the cell moves to UNKNOWN — which is
  red until a generator reaches it. *A scope relaxation cannot silently create a new blind
  spot.* This is rank 1 on the sabotage procedure's durability ranking ("make the sabotage a
  permanent test") applied to the exemption rather than to the check.

Measured rejection classes the enumerator already produces (`zz_enum2.py`, triples):
`UnsupportedByGraphIndex` × 82, `CyclicDerivedDependency` × 10 out of 469 configs. The four
scope messages seen, each of which becomes a witness family:

```
tupleset 'parent' declares a userset restriction; tupleset relations must be
    directly assignable types (OpenFGA model rule)
tupleset 'parent' has computed/rewritten arms; Zanzibar tupleset semantics read
    stored tuples only, ...
star tupleset [doc:*] on 'parent' derives the wildcard userset shape (doc, viewer)
    over the derived relation doc#viewer, which needs symbolic composition through residues
DoublyBridgedShapeError (star-bridge configs)
```

So `ttu.ts.restr:userset` and `ttu.ts.restr:wildcard-userset` — two of the 15 never-hit
features — are **REJ, with witnesses**, not gaps. `ttu.ts:Computed`, `ttu.ts:Union`,
`ttu.ts:Exclusion`, `ttu.ts:Intersection` are REJ *only when the tupleset is untainted*
and HIT when the whole chain is boolean (that is precisely the compiler's own advice in the
error text: "declare it direct-only, or make the whole chain boolean so storage leaves
apply"). The prototype confirms both halves.

### 1.4 Non-vacuity, at three levels

1. Each `derive_*` asserts its result is non-empty (a rotted regex cannot silently shrink
   the alphabet to `∅` and make every cell trivially covered).
2. A cell counts as HIT only if its configuration was **driven** and the driven comparison
   count was `> 0`. Compiling a leaf and driving it constantly-empty is a documented
   in-repo failure (`docs/sabotage-procedure.md`, 2026-07-28 row).
3. The whole sweep asserts `total_comparisons > 0` and, additionally, an **acceptance-rate
   floor**: `accepted_writes / attempted_writes ≥ 0.5`. This is the guard for hard
   constraint 1 — if the pool generator drifts out of sync with the schema generator, the
   sweep silently starts measuring the admission-rejection path. A comparison counter alone
   would not catch that (the grid still sweeps, it just sweeps an empty store).

---

## 2. The swarm design

### 2.1 What a "feature" is

A **switch**: one boolean that gates one arm of the generator. Fourteen of them
(`zz_gen2.py::SWARM_SWITCHES`):

```
ts_boolean   ts_negonly   ts_multitype  ts_wildcard  ts_computed  ts_userset
body_boolean body_userset body_wildcard body_computed body_ttu
multi_type   self_ttu     owc
```

A switch is *not* the same object as a cell feature — switches are generator-side, features
are compiler-side. They are tied together by a mandatory test:

> **`test_every_switch_moves_the_cell_histogram`** — for each switch `s`, generate `k`
> configs with `s` forced ON and `k` with `s` forced OFF, and assert
> `cells(ON) \ cells(OFF) ≠ ∅`. A switch that reaches no cell is dead code pretending to be
> coverage; a cell-bearing generator arm with no switch cannot be starved on purpose.

### 2.2 The draw

```
stratum ~ Uniform{0,1,2,3}
  stratum == 0            -> ALL switches ON                (probability 1/4)
  otherwise               -> focus ~ Uniform(SWITCHES), forced ON
                             every other switch ON independently w.p. 1/3
```

Two properties, both deliberate:

* **No starvation.** Each switch is ON with probability
  `1/4 + (3/4)·[1/14 + (13/14)·1/3] ≈ 0.52`, and is *focus* — i.e. guaranteed present and
  therefore guaranteed to be the deep axis — in `(3/4)/14 ≈ 5.4 %` of draws. Over the
  `deep` profile's 120 examples that is ~6.4 focus draws per switch; over `ci`'s 12 it is
  ~0.6, which is why the deterministic enumerator (§5) and not the swarm carries the `ci`
  coverage assertion.
* **The existing distribution is preserved as a literal stratum.** The "all on" branch is a
  superset of today's `schema_asts` draw (today's generator is "all `body_*` switches on,
  all `ts_*` switches off, tupleset pinned"). Constraint 2 is therefore satisfied *by
  construction* for a quarter of the budget, and verified empirically by:

> **`test_swarm_does_not_regress_the_legacy_distribution`** — draw `N=400` from the old
> generator and `N=400` from the new, and assert
> `cells(new) ⊇ cells(old)` and, per feature, `rate_new(f) ≥ 0.5 · rate_old(f)`.
> The old rates are checked in as a measured floor with provenance (rank 3), *and* the
> superset relation is exact (rank 1). Measured today: old = 514 cells, new ∪ old = 891.

**A measured tuning result worth carrying into the implementation.** My first draw added a
third "minimal" stratum (focus only, everything else off). It *reduced* coverage — 771 →
721 cells at 600 draws — because tiny schemas consume budget without composing anything.
**Do not include a minimal stratum.** This is the concrete form of constraint 2's risk and
it showed up immediately in the instrument.

### 2.3 Prototype swarm coverage (measured)

| generator set | features | cells | % |
|---|---|---|---|
| current `schema_asts` + `star_bridge_configs` + `bool_star_bridge_configs`, 400 draws each | 36/51 | 514 | 40.3 % |
| prototype `swarm_configs` alone, 400–600 draws | 41/51 | 721–771 | 56.5–60.5 % |
| **union** | **45/51** | **876–891** | **68.7–69.9 %** |

The residual 6 features the prototype still misses are `ttu.ts:TTU` (a TTU whose tupleset is
itself a TTU — needs a third topological layer), `ttu.ts:undeclared`, `ttu.ts:owc`, and the
three REJ-with-witness ones. Those are named in §6.

---

## 3. (c) — the grammar change, as a diff sketch

Against `tests/test_hypothesis.py`. Four hunks; the pool change is the load-bearing one.

### Hunk 1 — typed universe (constraint 1: the pool must co-vary)

```diff
-USERS = ['u1', 'u2']
-DOCS = ['d1', 'd2']
+USERS = ['u1', 'u2']
+DOCS = ['d1', 'd2']
+FOLDERS = ['f1']
+# The pool generator's subject-name table. `_op_pool` used `USERS if r.type == 'user'
+# else DOCS`, which is correct only while every non-user restriction is `doc`-typed.
+# The moment the tupleset can restrict a SECOND entity type, that fallback emits
+# `folder:d1` -- a restriction-INVALID tuple. The graph admits it as a silent no-op
+# (empty rewrite fan-out) while the set engine rejects it, so the sweep would trip
+# accept/reject parity on the admission asymmetry rather than on the shape under test,
+# or (worse) quietly measure the rejection path. Typed table, keyed by the restriction's
+# own `r.type`, is what keeps the pool schema-valid BY CONSTRUCTION.
+TYPE_NAMES = {'user': USERS, 'doc': DOCS, 'folder': FOLDERS}
```

```diff
 def _op_pool(ast):
     ...
             for r in d.restrictions:
-                names = ['*'] if r.wildcard else (USERS if r.type == 'user' else DOCS)
+                names = ['*'] if r.wildcard else TYPE_NAMES[r.type]
                 for sn in names:
-                    for on in DOCS:
+                    for on in TYPE_NAMES[otype]:
                         out.append((r.predicate, r.type, sn, rel, otype, on))
```

This is the entire pool change, and it is why (c) is cheap: `_op_pool` **already** walks the
AST generically and emits one candidate per `Direct` restriction. It was never the pool that
was hardcoded — only the tupleset body and the name table. Validity is preserved by the same
argument the existing code relies on: every emitted candidate is *derived from a declared
restriction of the relation it is written to*, so it matches by construction.

### Hunk 2 — the tupleset is drawn, at a drawn topological position

```diff
 @st.composite
-def schema_asts(draw, allow_usersets: bool = True):
+def schema_asts(draw, allow_usersets: bool = True, sw=None):
     n = draw(st.integers(min_value=2, max_value=5))
     names = [f'r{i}' for i in range(n)]
-    ast = {('doc', 'parent'): Direct((Restriction('doc', '...', False),))}
+    if sw is None:
+        sw = draw(swarm_subset())
+    ast = {}
+    # `parent` is the tupleset of EVERY generated TTU. Pinning it to a plain
+    # single-type non-boolean `[doc]` made the whole `ttu.ts:*` axis (10 of the 51
+    # coverage features) UNREACHABLE AT ANY max_examples -- which is why the
+    # 2026-08-10 TTU-over-derived-tupleset divergence could not be found here.
+    # It is now drawn from the same `expr` grammar as every other relation, at a
+    # DRAWN topological position `ppos` so its body may reference r0..r_{ppos-1}
+    # (and hence be Computed / TTU / tainted), and with an explicit neg-only arm:
+    # a restriction present ONLY in the subtrahend, which is the exact 2026-08-10
+    # shape `parent: [folder] but not [doc]`.
+    ppos = draw(st.integers(min_value=0, max_value=n - 1))
```

```diff
     for i, name in enumerate(names):
+        if i == ppos:
+            ast[('doc', 'parent')] = _tupleset_expr(draw, sw, names[:i])
         ast[('doc', name)] = expr(i, 0)
+    ast.setdefault(('doc', 'parent'), Direct((Restriction('doc', '...', False),)))
```

with, alongside `expr`:

```python
def _tupleset_expr(draw, sw, earlier):
    """The TTU tupleset body. NOTE the neg-only construction: the subtrahend's
    restriction must occur NOWHERE in the base, otherwise the same raw tuple routes to
    both arms and cancels, `parent` is constantly empty, and the cell is 'compiled but
    never driven' -- the 2026-07-28 failure mode. Two valid constructions:
        multi-type : base [folder] / neg [doc]   (the 2026-08-10 live-bug shape)
        single-type: base [doc:*]  / neg [doc]   (star base, concrete subtrahend)
    """
```

**This is not a stylistic note.** My first witness builder wrote
`Exclusion(Direct([doc, folder]), Direct([doc]))`, which *looks* like a neg-only arm, reads
like one in a review, compiles, and produces `parent ≡ ∅` — and the driven sweep over it
found **zero** divergences. Fixing the construction to a genuine neg-only arm made the same
sweep detonate the live bug. A reviewer cannot tell these two apart by eye; the docstring is
the only warning the next person gets.

### Hunk 3 — the grid gains the second type

`_grid` currently hardcodes `('...', 'user', …)` subjects and `DOCS + ['ghostD']` objects.
It must derive subjects from the AST's own `Direct` restrictions (exactly as
`ParityEngine._grid` already does) and objects from `TYPE_NAMES[o_type] + [ghost]`. Reusing
`ParityEngine._grid`'s logic rather than re-deriving it is preferable — that function already
carries an anti-vacuity assert for the empty-grid case.

### Hunk 4 — `_bool_star_bridge` machine asserts the graph joined

```diff
     @initialize(cfg=bool_star_bridge_configs())
     def setup(self, cfg):
         schema, owc, pool = cfg
         self.pe = _parity_or_skip_doubly_bridged(schema, owc)
         if self.pe is None:
             return
+        # Measured 2026-08-10 (`zz_drop.py`, 400 draws): 59% of this generator's draws
+        # raise UnsupportedByGraphIndex, ParityEngine sets graph=None, and the machine
+        # fuzzes 3-way -- oracle + two set engines, no graph index -- while reporting
+        # green. Only 12% of draws were 4-way. StarBridgeParityMachine already asserts
+        # this; this machine did not. Record which arm ran, and floor the 4-way rate.
+        self.four_way = self.pe.graph is not None
```

with a module-level counter and a session-scoped floor (`≥ 8 %` of non-skipped draws must
be 4-way, measured 12 %). The alternative — narrowing `owc_domain` so the graph always
joins — would *reduce* coverage of the decision-15 scope boundary, so the floor is the right
instrument, not a grammar change.

---

## 4. The sabotage plan

Eight sabotages. Every one is a *narrowest plausible weakening* — something a well-meaning
refactor would actually do — not a catastrophe. Numbers 3 and 4 are the strongest because
they use the live bug as a control.

| # | subject | the narrowest plausible weakening | must go RED |
|---|---|---|---|
| 1 | the eight hand-named modality flags | delete `ttu.ts:neg-only-type` from the alphabet | `test_every_switch_moves_the_cell_histogram` for `ts_negonly` — the switch now reaches no cell it did not already reach |
| 2 | the (c) grammar change | restore `ast = {('doc','parent'): Direct((Restriction('doc','...',False),))}` — i.e. **the literal state of the tree today** | 10 `ttu.ts:*` features → UNKNOWN cells → cell-coverage assertion |
| 3 | **the live bug (positive control)** | none needed — the bug is unfixed | the driven enumerator config `{ts_negonly, body_ttu}` |
| 4 | **the driving discipline (instrument control)** | replace small-subset driving with "apply the whole pool, then sweep" | **must go GREEN, i.e. must FAIL to detect the live bug** |
| 5 | a rejection witness | relax the `tupleset ... declares a userset restriction` scope check | the witness's `pytest.raises` |
| 6 | anti-vacuity | make `_op_pool` return `[]` for multi-type restrictions | `total_comparisons > 0` and the acceptance-rate floor |
| 7 | 3-way silent degradation | (already true) `BoolStarBridgeParityMachine` runs graph-less | the new 4-way rate floor |
| 8 | pool/schema co-variance | revert Hunk 1's typed table (`USERS if r.type=='user' else DOCS`) | the acceptance-rate floor ≥ 0.5 — invalid `folder:d1` subjects are refused by the set engine |

### Sabotage 3 — executed, literal output

The enumerator's witness for the switch pair `{ts_negonly, body_ttu, multi_type}` is:

```
type doc
  relations
    define r0: [user]
    define parent: [folder] but not [doc]
    define r1: [user]
    define r2: r1 from parent
type folder
  relations
    define r1: [user]
```

That is the 2026-08-10 live-bug schema, **assembled by the switch combination, not
transcribed**: the builder composes `ts_negonly` (base type ∌ subtrahend type) with
`body_ttu` (`r2: r1 from parent`) and `multi_type` (a `folder` type exists) with no
knowledge of the deviation entry. Driven with a 2-tuple subset:

```
DIVERGE subset= (('...', 'doc', 'd1', 'parent', 'doc', 'd1'),
                 ('...', 'user', 'u1', 'r1', 'doc', 'd1'))
    fail-closed ('...', 'user', 'u1', 'r2', 'doc', 'd1')
        oracle= True {'graph': False, 'set:py': True, 'set:roaring': True}
```

and from the randomised driven sweep over all 119 singleton+pair configs
(`zz_cost.py`, seed 0, 420 runs, 104 321 comparisons, 52.5 s):

```
subsets/config=4: runs=420 comparisons=104321 divergent-runs=1 wall=52.5s (125 ms/run)
   fail-closed sw=['body_ttu', 'ts_negonly']
       q=('...', 'user', 'u2', 'r2', 'doc', 'd2') oracle=True
         {'graph': False, 'set:py': True, 'set:roaring': True}
   distinct divergent configs: 1
```

and over all 469 triple configs (`zz_hunt.py`, seed 7, 288 999 comparisons, 157 s):

```
fail-closed sw=['body_ttu', 'body_wildcard', 'ts_negonly']
    q=('...', 'user', 'u2', 'r2', 'doc', 'd2') oracle=True
      {'graph': False, 'set:py': True, 'set:roaring': True}
DONE comparisons=288999 distinct=1 wall=157s
```

**This is the control the task pointed at, and it works: red today, and it must go green the
day the TTU-storage-leaf fix lands.** Note the second run: the switch pair `{ts_negonly,
body_ttu}` reaches it *without* `multi_type`, via the single-type construction
`parent: [doc:*] but not [doc]` — i.e. the cell, not a transcribed schema, is what carries
the detection.

### Sabotage 4 — executed, and it found a real weakness in the first draft of this design

My first driven enumerator applied the **whole pool** (24 tuples) per config and then swept
the grid. Literal output:

```
K<=2: configs=105 driven=97 graph-dropped=0
comparisons=35424  DRIVEN CELLS=454/1275 (35.6%)
wall time = 35.3s   (364 ms/config)
configs with a DIVERGENCE: 0
```

**Zero.** The identical configs, driven with subsets of size 1–3, find the bug. The reason is
structural and general: a fail-closed divergence is an *under*-grant, so **any** additional
granting tuple in the pool supplies an alternative path and masks it. This is the same
property the repo already named — commit `310fbcb`, "irrelevance of irrelevant alternatives
(IIA)".

The consequence for this design is sharp: **cell coverage is necessary and not sufficient.**
A sweep can hit every cell in the taxonomy and still detect nothing, because the *driving
discipline*, not the schema shape, is what makes a divergence observable. So:

* the enumerator drives **small subsets** (size 1–3), fixed seed, several per config —
  never the full pool;
* the full-pool variant is retained as a **permanent negative control**: a test that asserts
  the full-pool driving of the `{ts_negonly, body_ttu}` witness does **not** detect the
  divergence while the subset driving does. If someone "optimises" the sweep by applying the
  pool once instead of `S` times, that test fires.

Without this sabotage the design would have shipped a 35-second `ci` phase that reached
35.6 % of the cell space, found nothing, and reported green over an unfixed live bug.

---

## 5. Runtime, and the ci / deep split

### 5.1 Measured costs

| operation | cost |
|---|---|
| alphabet derivation + feature extraction of one schema | ~0.4 ms (469 configs compile-only in 0.1 s) |
| build 4 backends + ≤3 adds + full grid sweep (one driven run) | **125 ms** |
| build 4 backends + 24 adds + full grid sweep | 364 ms |
| deterministic enumerator, singletons+pairs, 4 subsets each (420 runs) | **52.5 s** |
| deterministic enumerator, triples, 3 subsets each (1 407 runs) | **157 s** |
| current `tests-tile:*` phase | 95–165 s of a 600 s cap |

### 5.2 The split — and the honest part

**All 1275 cells cannot be hit under the `ci` budget, and I am not proposing an assertion
that pretends otherwise.** The prototype's best measured union is 891 (69.9 %) at 400–600
draws per generator, which is ~40× the `ci` budget. A "every cell is hit" assertion that only
holds under `deep` is precisely the kind of check that fails by passing (it would be
`skipif`'d or floor-lowered the first time it flaked). So the split is by *mechanism*, not by
budget:

**`ci` — deterministic, exhaustive over a bounded config space, cheap, and strictly asserted.**

| phase | what | assertion | cost |
|---|---|---|---|
| C1 | alphabet derivation | each `derive_*` non-empty; alphabet size `== 51` with provenance | <0.1 s |
| C2 | deterministic witness enumerator, **singletons + pairs** (119 configs), compile-only | every cell is HIT or REJ-with-witness; `UNKNOWN == ∅` | 0.1 s |
| C3 | rejection witnesses | each raises the recorded exception type with the recorded message substring | 0.1 s |
| C4 | driven pass, **2 small subsets per config** (238 runs) | `comparisons > 0`; acceptance rate ≥ 0.5; every backend agrees with the oracle | **~30 s** |
| C5 | swarm campaign, `max_examples=12` (unchanged budget), swarm draw + (c) grammar | today's assertions, plus a per-run cell histogram written to the report | ~unchanged |
| C6 | negative control (sabotage 4) | full-pool driving of the `{ts_negonly, body_ttu}` witness detects **nothing** while subset driving detects the divergence | ~1 s |

**Total added to `ci`: ~32 s.** A `tests-tile` at 165 s becomes ~197 s against a 600 s cap.
Because the tiles are a structural partition collected at run time, the new tests land in
whichever tile the modulus assigns; worst case one tile absorbs all of C1–C6, which is the
number above. Comfortable.

Note C2's cell target is **not** 1275. It is *"every cell the singleton+pair enumerator's own
witnesses realise, plus every cell with a rejection witness"* — measured at **454** today.
That is a closed, exhaustive, deterministic set: the enumerator has no RNG, so C2 is a
*complete* statement about its own config space, not a sample. Its value is that the config
space is defined by the switch list, so **adding a switch immediately adds `2·|SW|+1` configs
and any new UNKNOWN cell is red on the next run.**

**`deep` / nightly — probabilistic, wide, not a gate.**

| phase | what | cost |
|---|---|---|
| D1 | enumerator over **triples** (469 configs), 3 subsets each | 157 s |
| D2 | swarm campaign at `max_examples=120`, `stateful_step_count=25` | existing `deep` cost + ~2× |
| D3 | cell-histogram report: cells HIT across the whole `deep` run, diffed against the last recorded high-water mark, **committed** | free |

D3 is the only place a "1275-cell" number should ever appear, and it is a *record*, not an
assertion. The `ci` gate asserts the closed set; `deep` reports the open one.

---

## 6. What this design will NOT reach

Stated plainly, because a coverage design that claims completeness is the failure mode it
was written to fix.

1. **~30 % of the pair-cell space, even at `deep` budgets.** Best measured union: 891/1275.
   Some of the residue is REJ-with-witness (legitimately unreachable); the rest is unknown
   and will show up in the D3 report as UNKNOWN cells that no witness explains. That number
   is the honest measure of the *remaining* blind spot and it should be published, not
   rounded away.
2. **Three-layer TTU nesting** (`ttu.ts:TTU` — a TTU whose tupleset is itself a TTU-bearing
   relation). The generator builds one `parent`; reaching this needs two tupleset relations
   at different topological depths. Not designed; named.
3. **`ttu.ts:undeclared`** — a TTU naming a tupleset relation that does not exist on the
   object type. That is a parse/compile-error path, not a runtime path; it belongs with the
   parser tests, not here.
4. **Anything requiring more than 2 entity types or more than ~6 relations.** The universe is
   `{u1,u2,d1,d2,f1}` for a reason (grid cost is quadratic in it). Scale-dependent bugs —
   fan-out caps, closure blow-up, watermark/outbox pressure — are invisible to this design.
5. **Ordering and concurrency.** The enumerator drives *sets* of writes. Order-dependent
   admission bugs (reg10 is W1-then-W2) are the `StarBridgeParityMachine`'s job and stay
   there. The swarm inherits the stateful machine but does not add ordering coverage.
6. **Removal/revocation paths.** Every measured number above is add-only. Extending the
   driven subsets to add/remove interleavings roughly doubles the runtime and is the obvious
   next increment; it is not in the `ci` budget as proposed.
7. **Fail-open detection sensitivity.** Sabotage 4's argument is about *masking* under-grants.
   Over-grants (fail-open) are masked by the *opposite* discipline — they hide when the store
   is nearly empty and appear as you add tuples. The subset-driving discipline is therefore
   tuned for fail-closed and slightly detuned for fail-open. A complete design would drive
   both a sparse and a dense regime per config; at 125 ms/run that doubles C4 to ~60 s, which
   is still inside budget and is my recommendation if the fail-open case is a priority.
   **I could not independently reproduce a fail-open divergence.** 393 320 comparisons across
   `zz_cost.py` and `zz_hunt.py` produced exactly one distinct divergence family, and it is
   fail-closed. The 2026-08-09 fail-closed one is fixed (`c042056`); the 2026-08-10
   fail-closed one is live. If a fail-open was confirmed elsewhere this session, it is
   outside what my sweep reached, and point 7 above is the most likely reason.
8. **The Lean side.** `formal/CORRESPONDENCE.md` §7.3 already records that the arm where the
   2026-08-09 bug lived has no Lean counterpart. This design adds nothing there; cells are a
   Python-side instrument.

---

## 7. Prototype file map

| file | what it does | key output |
|---|---|---|
| `zz_cells.py` | derives the 51-feature alphabet from 6 source-of-truth sites; feature extractor; pair-cell helpers | `alphabet size 51`, `pair-cell universe 1275` |
| `zz_measure.py` | measures the CURRENT generators' ceiling (400 draws each) | `36/51 features, 514/1275 cells (40.3%)`, the 15-feature miss list |
| `zz_ci.py` | same under the `ci` budget, 6 seeds | `469–514 cells` → budget is not the constraint |
| `zz_drop.py` | classifies each generator's draws 4-way / 3-way / skipped | `bool_star_bridge: 12% 4-way` |
| `zz_gen2.py` | prototype `swarm_subset` / `swarm_schema_asts` / `swarm_configs` / `swarm_op_pool` — deliverables (b) and (c) | `41/51 features, 721–771 cells` |
| `zz_measure2.py` | measures the prototype swarm and the union with existing | `union 876–891/1275 (68.7–69.9%)` |
| `zz_enum2.py` | deterministic witness builder + compile-only enumeration over switch subsets | singletons 87 · pairs 454 · triples 655 cells, 0.1 s |
| `zz_drive.py` | driven enumerator, **full-pool** variant (the negative control) | `0 divergences`, 35.3 s |
| `zz_cost.py` | driven enumerator, **small-subset** variant | `1 divergence`, 125 ms/run, 52.5 s |
| `zz_hunt.py` | triple-switch divergence hunt | `288 999 comparisons, 157 s, 1 distinct` |
| `zz_diff.py` | 4-backend differential that *reports* instead of raising (ParityEngine asserts, which a sweep cannot use) | — |
| `zz_repro.py`, `zz_sweep_ts.py`, `zz_min*.py`, `zz_probe.py` | reproduction + minimisation scratch | — |
