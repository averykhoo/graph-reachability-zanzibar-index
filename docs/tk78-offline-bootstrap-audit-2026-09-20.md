# `TK78` — the offline bootstrap paths, re-measured first-hand

**ACTIVE-PLAN, opened 2026-09-20 — the body is provenance, not a living status.** This is
the verification pass the `TK78` row demanded as its FIRST ACTION: the row's two readings
were a subagent's (`TK74` fan-out, 2026-09-18) and explicitly not verified. Every claim
below is labelled `READ` (first-hand, this tree, 2026-09-20), `REASONED`, or `UNVERIFIED`.
Live state is the task row (`python scripts/task.py show TK78`), never this file.
Corrections append **dated at the top**. Freeze it when `TK78` closes.

⚠ **This pass CONTRADICTS the row on two load-bearing points and CONFIRMS both of its
literal claims.** The row's headline — *"an unaudited second reconcile implementation"* —
is materially wrong about where the risk is, and the question it names as *"the actual
question"* is answered NO from the code. The real hole is one layer down and is stated in
§5. Read §5 before planning anything — **and then the 2026-09-20d correction below, which
measured §5's headline claim and found it false.**

## Corrections appended 2026-09-20d — step (i) LANDED, and §5's headline claim is MEASURED FALSE

*supersedes:* §5's ⚠ paragraph, *"the widest gate cannot see a gap here even in principle,
because it compares two COPIES of the enumerator … a bug SHARED by both cancels on both arms
and passes green."* That was `REASONED`, and it is **wrong when run**.

**LANDED: [`tests/test_backfill_enumeration.py`](../tests/test_backfill_enumeration.py)** —
§6 step (i), three tests, green. A fixture whose `access` / `alias` / `deep` each have
exactly ONE positive leaf, of kind `derived-ttu` / `derived-computed` /
`derived-tupleset-ttu`, so `_live_keys_of`'s recursion is the only way those objects can be
found; `::test_fixture_keeps_the_enumeration_load_bearing` is a mechanical refusal of any
later edit that gives one of them a storage family and makes the pin vacuous. The pin itself
(`::test_live_keys_of_reaches_every_key_the_live_cascade_wrote`) takes ground truth from the
live cascade and asserts the bootstrap enumeration covers it.

⚠ **One design decision worth the next session's attention: ground truth is every key the
live cascade's `reconcile` CHANGED, not every key it scheduled.** `READ` 2026-09-20 — the
cascade over-schedules, reconciling `('doc', 'deep', 'f1')`, a **folder** name under a doc
relation, mapped in by `::_map_deltas_to_keys` off the `folder#ok` derived edge. It is a
no-op and the enumerator is right not to reach it. `DeltaProcessor._check_cascade_fixpoint`'s
docstring records the same asymmetry from the other side.

### The sweep (2026-09-20)

The harness was a throwaway mutation script, gitignored and then deleted, per
[`docs/sabotage-procedure.md`](sabotage-procedure.md) — **the table is the evidence**, and
each row names its edit precisely enough to redo. Shape, if it is redone: apply one edit,
run the four targets as separate `subprocess` calls reading `returncode` (never a shell
pipe), restore in a `finally`, and assert the restore. It carried an `M0` control and an
inverse control; the `M0` row below is what says the attribution worked.

Both copies of the enumerator mutated together unless marked. RED = caught, green = missed.
`tests/test_invariants_derived.py` was green on **every** row and is omitted.

Cells name the failing parametrisations rather than counting them — a count here would be
a coverage figure with no home to point at, and `doc_counts.py`'s prose refusal is right to
reject one.

| mutation (both copies) | new module | `test_bulk_build` | `conformance_bulk_state` |
|---|---|---|---|
| drop `derived-computed` | **RED** | green | **RED**: `[star_two_strata_churn]`, `[taint_computed_root_over_boolean]`, `[two_stratum_cascade]` |
| drop `derived-ttu` | **RED** | **RED**: `[boolean]`, `[demorgan]` | green |
| drop `derived-tupleset-ttu` | **RED** | **RED**: `[rc2_star_tupleset]` | green |
| drop `derived-userset` from `preds` | **RED** | **RED**: `[derived_member]` | green |
| drop `rel` from `preds` | green | green | green |
| recurse through NEGATIVE leaves too *(inverse control)* | green | green | green |
| `M0`: flip the new pin's own `missing == {}` *(control)* | **RED**, attributed to the one test carrying the claim | green | green |

**So the shared-copy argument does not survive contact.** With *both* copies mutated,
three of the four kind-drops redden `test_bulk_build_identical_to_incremental` **itself** —
`VERIFIED` by `-rf` attribution, e.g. `[boolean]` and `[demorgan]` for the `derived-ttu`
drop. `REASONED`, not verified: the copies read different substrates — `processor.py`
re-queries `node_v4` rows mid-backfill, `bulk_backfill.py` reads an in-memory `family_names`
index seeded at load and grown through the bulk phases — so the same textual edit does not
delete the same keys.

What survives, and is the honest case for the module: **no single existing module sees all
four kinds.** `test_bulk_build` misses `derived-computed` outright, the conformance module
misses the other three, and which one catches what is an accident of each module's corpora.
The property also had no *name* anywhere (§5's grep-zero stands); a red arrived as an opaque
state diff several layers from the enumerator.

⚠ **`M5` is INERT, and the reason is `TK91`'s.** Dropping `rel` from `preds` left all four
modules green. That entry exists for objects enumerable only by their PUBLIC family — state
that outlives the leaf which produced it, i.e. a **remove**. Every corpus in play is add-only,
so the branch cannot move. Per [`docs/sabotage-procedure.md`](sabotage-procedure.md) that is
reported as inert, never read as a clean pin — and it is measured evidence for `TK91`
(§6 (ii)), which now has a concrete unpinned branch to point at rather than an argument by
analogy with `TK87`.

## Corrections appended 2026-09-20b — §5's premise was WRONG, and the census found doc-rot

*supersedes:* §5's closing claim that *"`DeltaProcessor.backfill()` is pinned — `?`"* and
that the identity chain bottoms out unpinned. It does not. Written before the census, marked
`UNVERIFIED`, and wrong; the correction is §5a below. §§1–4 stand as written.

**A bulk-vs-incremental differential DOES exist, and its reference is the right one.**
`READ` `formal/conformance/test_conformance_bulk_state.py::test_state_bulkbuild_vs_pythongraph`
is two-legged per `GRAPH_FRAGMENT` corpus: leg 1 compares the bulk-built state EXACTLY
against the **write-by-write incremental** Python state (edge multiplicity on the derived arm
too, the `EdgeV4.derived` flag, every residue triple — no P3 exemption), and leg 2 runs
`diff_states(lean, bulk)` so the bulk state is anchored to the Lean model independently. Two
Python-vs-Python pins predate it: `tests/test_bulk_build.py::test_bulk_build_identical_to_incremental`
and `tests/test_connectedstore_build.py::test_built_index_equals_live_maintained`.

*refined 2026-09-20c, after the census:* the first of those two is **offline-vs-offline**,
not live-vs-offline — `build_index(bulk=False)` runs no per-write cascade. Do not read it as
a bootstrap≡replay pin. §5 carries the verified detail; the live pins are the conformance
module, `tests/test_invariants_derived.py::test_backfill_vs_live_equivalence`, and
`test_built_index_equals_live_maintained`.

⚠ **NEW FINDING — a gated module advertises a hole that was closed four days ago.** That
module's docstring says of `bulk_build.py`'s I14 crossable-middle loop:

> *"The I14 loop is pinned by NOTHING: the same sabotage left every `build_index` caller in
> `tests/` green, because no bulk-built corpus in the tree has a crossable shape."*

Its paragraph is stamped *"Measured 2026-09-06"*. `P22` closed exactly that on **2026-09-16**
([`docs/p22-i14-corpus-masking-2026-09-16.md`](p22-i14-corpus-masking-2026-09-16.md)).
`READ` `tests/test_bulk_build.py`: `::_owc_star_ttu_tuples` (`:389`) is a corpus with
non-empty `crossable_shapes` wired into `_CORPORA` (`:434-445`), and
`::_assert_r4bf_features` clause (g) (`:609-640`) pins the loop's PRODUCT structurally —
including a mechanical refusal (`:639`) of a corpus whose concrete `viewer(folder, _)` grants
would MASK the loop. So both halves of the quoted sentence are now false.

This is `TK88`'s shape pointed the other way. `TK88` is a module announcing a redness it no
longer has; this is a module announcing a HOLE it no longer has — and the cost is higher,
because the next session planning offline-bootstrap assurance reads "pinned by NOTHING" and
either re-does `P22`'s work or files it again. The remedy is `docs/README.md`'s: a dated
correction line at the site, not an edit that erases the 2026-09-06 measurement.

## 0. Bottom line

| the row said | verdict 2026-09-20 | where |
|---|---|---|
| `bulk_backfill.py` has no quiescence/settle/fixpoint check | **CONFIRMED** | §1 |
| `DeltaProcessor.backfill` discards `self._bumped` | **CONFIRMED** (line moved) | §2 |
| "whether a bump can land on a LOWER stratum … is the actual question" | **ANSWERED: it cannot** | §3 |
| "a SECOND reconcile implementation" | **NARROWED** — the boolean logic is *shared*, not reimplemented | §4 |
| (not on the row) the enumeration that REPLACES fan-out is the real question | **NEW** | §5 |

## 1. No quiescence check on the bulk path — CONFIRMED, with a refinement

`READ`: `grep -i 'settle|quiesc|fixpoint|converge|InvariantViolation|assert|while '` over
`index_v4/bulk_backfill.py` (`833` lines) returns five hits and **no** settle, quiescence,
fixpoint or convergence check of any kind. The row is right.

The refinement matters for anyone sizing the fix — both `InvariantViolation` raises are
cycle-corruption guards, not staleness guards, and the one `while` loop is not a fixpoint
iteration:

* `::_topo` (`:231` `while queue`) is **Kahn's algorithm**, and its raise (`:243`) fires on
  `len(order) != len(nodes)` — *"the in-memory derived graph is cyclic"*.
* `::_add_edge_existence` (`:255`) refuses an edge that would close a cycle.

`REASONED`: the module does not *need* a fixpoint loop by its own design — it maintains
full transitive reachability incrementally on every edge add "with immediate visibility"
(`::_add_edge_existence`, `::_seed_reachability`), so later same-stratum probes observe
earlier writes. That is the design's substitute for iterating. It is a substitute that is
**asserted nowhere**, which is the honest form of the row's complaint.

## 2. `backfill()` discards `_bumped` — CONFIRMED, and it is DELIBERATE

`READ`: `index_v4/processor.py::DeltaProcessor.backfill` is now **`:1820-1832`** (the row
cites `:1714-1726`, measured 2026-09-18 — the line numbers rotated under the `TK72`/`TK87`
edits; `:1694` is today the tail of `::_settle`). Its last statement is `self._bumped = []`,
discarding every bump `::reconcile` appended at `:1375`.

The row reads this as a possible oversight. `READ` says it is deliberate, and the evidence
is `::_live_keys_of`'s own docstring (`:1777-1784`):

> *"for derived leaves with no storage family of their own — the objects discoverable
> through what they read … (Live maintenance reaches those objects via
> dependents-invalidation; **backfill must reach them by enumeration**.)"*

So the design is explicit: **backfill replaces fan-out with enumeration.** Discarding the
bump list is consistent with that, not a leak — *provided* the enumeration is complete.
Nothing in the file asserts that it is. Note the sibling `::audit_fixpoint` (`:1838`) ends
with the same discard, and `::_check_cascade_fixpoint` (`:1766`) clears `_bumped` too but
documents why in three lines.

## 3. A discarded bump CANNOT target a lower stratum — the row's question, answered

The row asks to *"construct it or show it cannot happen"*. It cannot happen, and the proof
is two `READ` facts:

**(a) Stratification is strict.** `zanzibar_utils_v1.py::_stratify` (`:2064-2099`) is Kahn
layering over `plan.deps`: a key's `indeg` reaches `0` only after every dep has been placed,
so along every `deps` edge the dependent's stratum is **strictly greater**. A residual cycle
is refused outright — `CyclicDerivedDependency`, *"boolean spec §1.9 forbids recursion
through boolean relations"*. Same-stratum dependency is therefore impossible, not merely
unusual.

**(b) Every fan-out edge IS a stratification edge.** `::_fan_out`
(`index_v4/processor.py:1528`) walks `self.compiled.dependents` only. In
`zanzibar_utils_v1.py::_plan_deps_and_fanout` (`:2002-2052`) **every**
`dependents.setdefault(k, ...)` is immediately preceded by `dep(k)`, in all four branches:

```
PDerivedComputed      :2013-2015   dep(k)          -> dependents[k]
PDerivedUserset       :2017-2019   dep(k)          -> dependents[k]
PDerivedTTU           :2027-2031   if k in tainted: dep(k) -> dependents[k]
PDerivedTuplesetTTU   :2037-2049   dep(ts_key)/dep(target_key) -> dependents[...]
```

i.e. `dependents ⊆ reverse(deps)` exactly. The two dicts that are populated **without** a
matching `dep()` — `target_feeders` and `tupleset_feeders`, the untainted-target cases — are
not read by `::_fan_out` at all; they drive closure-delta mapping, not the bump path.

`REASONED` from (a)+(b): a bump raised while reconciling a key at stratum `S` can only fan
out to keys at stratum `> S`, and `::backfill` sweeps `compiled.strata` in increasing order,
so every such dependent is still ahead of the sweep. **Discarding the bumps loses no
ORDERING.** The row's stated worry is closed.

## 4. "A second reconcile implementation" — narrowed

`READ` `index_v4/bulk_backfill.py:14-24` and `:684-780`: the module does **not** reimplement
the boolean evaluation. `::_reconcile` (`:709`) calls `plan.stars_fn(ctx)` (`:715`) and
`plan.check_fn(ctx, s)` (`:689`, `:737`, `:751`, `:778`) — *the same compiled plan closures
the live processor evaluates*. `::_BulkEvalContext` (`:63-66`) implements the same callback
protocol as `processor::_EvalContext` (`:127`). Its own docstring draws the line: *"Only
state ACCESS is mirrored."*

So what is duplicated is **state access and iteration order**, not the semantics. That is a
real duplication — `::_live_keys_of` exists in an in-memory form here and a SQL form in
`processor.py` — but it is a much smaller surface than "a second reconcile", and it should
be sized as such.

The module also states a correctness bar the row does not mention (`:11-14`):

> *"the state produced here + Phase W is byte-IDENTICAL to `build_index(..., bulk=False)` +
> `DeltaProcessor.backfill()` — pinned by the differential identity gate
> (`tests/test_bulk_build.py`)."*

`UNVERIFIED as of this section` — whether that gate exists and what it actually compares is
the census in §5.

## 5. Where the hole actually is

Combining §2 and §3: backfill is sound on ordering, and its correctness rests **entirely**
on `::_live_keys_of` enumerating every object name that `::_fan_out` would have invalidated.
Those two functions are written in different vocabularies and nothing relates them:

| `::_fan_out` edge `via` | `::_live_keys_of` leaf `kind` |
|---|---|
| `computed` | `derived-computed` (recurses into the referenced relation) |
| `ttu` | `derived-ttu` (queries the `tupleset_rel` family) |
| `userset` | covered by the `preds` list (`closure` / `derived-userset`) |
| `tupleset-ttu` | `derived-tupleset-ttu` (recurses into `node.tupleset_rel`) |

`REASONED`: the correspondence is plausible case-by-case and was clearly intended, but it is
a **prose-level correspondence between two implementations of the same invalidation
question** — exactly the shape the row was right to be suspicious of, one layer below where
it pointed. A missing case here is silent: the object is simply never reconciled, backfill
reports nothing, and the discard in §2 means no bump survives to contradict it.

**§5's suspicion is VINDICATED by the census — (d) is a clean NO.** `READ` 2026-09-20:
`grep -rn '_bumped|_live_keys_of' tests/ formal/ --include=*.py` returns **zero** matches.
Neither the discard at `:1832` nor the enumeration-completeness property is asserted
anywhere. The docstring quoted in §2 — *"backfill must reach them by enumeration"* — is the
load-bearing correctness argument of the whole offline path, and it is unpinned.

⚠ **SUPERSEDED 2026-09-20d — the closing claim of this paragraph is measured FALSE; see the
correction at the top. The two-copies READ below is still accurate.**

⚠ **And the widest gate cannot see a gap here even in principle, because it compares two
COPIES of the enumerator.** `READ`: `index_v4/bulk_backfill.py::_live_keys_of` (`:808`) is a
second implementation, its section header saying *"mirrors `DeltaProcessor.backfill` /
`_live_keys_of`"*, and both build the same `preds` list the same way. So
`tests/test_bulk_build.py` compares copy A's output against copy B's: a bug in ONE is caught,
a bug SHARED by both cancels on both arms and passes green. That is the precise sense in
which §4's "second implementation" concern was right — not about the boolean logic, which is
shared on purpose, but about the enumerator, which is duplicated and self-referentially
pinned.

### The census, reconciled first-hand (2026-09-20)

A subagent produced this table; every row marked `VERIFIED` below was re-checked first-hand
against the live tree before it was written here (`CLAUDE.md` § Delegation — a report is
evidence, not a finding).

| pin | what it actually compares | class |
|---|---|---|
| `formal/conformance/test_conformance_bulk_state.py::test_state_bulkbuild_vs_pythongraph` | `build_index(bulk=True)` vs a **true per-write `run_cascade`** drive, 25 `GRAPH_FRAGMENT` corpora | **DIFFERENTIAL (live)** — `VERIFIED`: `formal/conformance/backends.py::graphindex_drive:88` calls `proc.run_cascade(wm)` inside the per-tuple loop |
| `tests/test_invariants_derived.py::test_backfill_vs_live_equivalence` (`:220`) | live cascade per op vs raw leaf writes + one `backfill()`; `snapshot_rows` + residues-by-name + 4 `check` probes | **DIFFERENTIAL (live)** — `VERIFIED`; the ONLY test pinning `DeltaProcessor.backfill()` itself. Small: `_SCHEMA`, `_OPS`, 2 docs |
| `tests/test_connectedstore_build.py::test_built_index_equals_live_maintained` | `build_index` vs a live `ConnectedStore` twin, incl. a query grid | **DIFFERENTIAL (live)** — narrow: one `_OPS` history, one `remove` (`:41`) |
| `tests/test_bulk_build.py::test_bulk_build_identical_to_incremental` | `bulk=True` vs `bulk=False` over its `_CORPORA` list — **both arms OFFLINE** | **DIFFERENTIAL (offline↔offline)** — see below |
| `tests/test_zt_p5_readjudication.py::test_zt_p5_object_wildcard_state_level_live_equals_rebuild` | live vs both builds, but both corpora are **non-boolean** so `compiled.plans` is empty and `backfill()` never runs | residue-vacuous |
| `::audit_fixpoint` (~25 call sites incl. `tests/parity.py`, `tests/test_matrix.py`) | a post-op I9 dose on a store the SAME path built | **INVARIANT-ONLY**, universally |

⚠ **The most-cited gate is mislabelled, and this is the census's best finding.**
`VERIFIED` at `connectedstore/build.py:92-107`: the `bulk=False` arm is a leaf-only
`widx.add_tuple` replay followed by **one** `DeltaProcessor(...).backfill()` — there is **no
per-write cascade on that arm**. Its own comment says *"This IS the identity gate's reference
side (`tests/test_bulk_build.py`)"*. So "identical to incremental" means *identical to the
other offline path*, and any defect shared by `backfill()` and `bulk_backfill` passes it.
`tests/test_matrix.py` and `tests/parity.py` contain no offline path at all.

`REASONED`: the two coverage sets cross without meeting — the widest-FEATURE gate
(`_CORPORA` — `demorgan1`, `rc2_star_tupleset`, `owc_star_ttu` among them) never runs the live path,
and the live gate (25 corpora) never runs those corpora. No test drives
`tests/test_bulk_build.py::_CORPORA` through `run_cascade`.

## 5a. The declared gaps — what bulk≡incremental does NOT cover (READ 2026-09-20)

`formal/conformance/test_conformance_bulk_state.py`'s docstring carries its own
"what this does NOT cover, said plainly" list, which is the single most useful artifact
found in this pass. Reproduced with today's verdict on each:

| declared gap | still true 2026-09-20? |
|---|---|
| **Remove histories** — every `GRAPH_FRAGMENT` corpus is an add-only tuple list, so the bulk side's snapshot IS the whole list | **YES** — pinned only by `tests/test_connectedstore_build.py::test_built_index_equals_live_maintained`, *"one history, one remove"* |
| **The outbox** — bulk writes one `ADDED` row per final closure pair; incremental writes a per-write delta history | **YES**, by design; compared as a multiset in `tests/test_bulk_build.py` |
| **Bridges / crossable middles (P2, I14)** — no in-fragment corpus has a crossable shape | **PARTLY STALE** — the *conformance* corpora claim holds; the *"pinned by NOTHING"* half is false since `P22` (see Corrections) |
| **The materialized CLOSURE** — Phase P's `pvec` DP and pure-indirect rows are invisible to both legs (`extract_sql_state` P1 keeps only `direct_edge_count > 0`; `indirect_edge_count` is never read) | **YES** — pinned only by `tests/test_bulk_build.py::snapshot_rows` |

`REASONED`: **remove histories is the one that rhymes with this repo's last two findings.**
`TK87` closed on exactly this shape — a driver that was add-only, so an entire removal path
was structurally unreachable from any generated config — and the bulk↔incremental
differential is add-only for the same kind of reason. It matters more here than it usually
would, because bulk builds from *surviving tuples* while the incremental arm replays a
*history*: a removal is precisely where the two constructions can legitimately be expected
to diverge (stale residue, refcount, GC'd nodes), and it is the arm with one corpus and one
remove behind it.

That, not §5's table, is the strongest candidate for what `TK78` should buy.

## 6. Next action — the decision, taken

The row leaves the landing shape to the verifying session. With §§1–5a measured, the ranking
is no longer close. **`TK78` is not one item; it is three, and they should be separated.**

**(i) The enumerator is the item.** `::_live_keys_of` ≡ `::_fan_out` is the offline path's
whole correctness argument (§2), it is asserted nowhere (§5, a clean zero), and the gate that
looks like it covers it compares the enumerator against its own copy (§5). This is the
smallest change with the largest assurance gain, and it is the part of the row's suspicion
that survived verification. Shape: a test that, for each `(type, rel)` on a boolean fixture,
asserts `_live_keys_of` ⊇ the key set `_fan_out` delivers for the same source — plus the
sabotage that must redden it (drop one `spec.kind` branch from `::_live_keys_of` and watch
`tests/test_bulk_build.py` stay GREEN, which is the point).
⚠ The fixture must be one where a dependent has **no positive leaf of its own**, or the
enumeration is trivially complete and the pin is vacuous. Two exist —
`tests/test_stored_cache_scope.py::_TTU_SCHEMA` (`:241`) and
`tests/fga_schemas/demorgans_law_1.fga` — and neither currently sits in a live differential.

**(ii) Remove histories** (§5a) is real but a SEPARATE item: the bulk↔live differentials are
add-only apart from one history with one `remove`. Same shape as `TK87`. It wants its own
row rather than being smuggled into this one.

**(iii) The stale conformance docstring** (Corrections) is a ten-minute dated-correction fix
and should not wait behind either.

`REASONED`, and stated so the next session can overrule it cheaply: (i) before (ii) because
(i) is unpinned-by-measurement while (ii) is thinly-pinned, and a shared under-enumeration is
invisible to every existing gate whereas a remove-history divergence would at least be caught
by `test_built_index_equals_live_maintained` if it were widened.

## Read first


- `python scripts/task.py show TK78` — the row, and the 2026-09-19f reasoning for its rank.
- `docs/architecture/r4bf-bulk-backfill-design.md` — the design `bulk_backfill.py:1` cites.
- `TK74` (`docs/tk74-staleness-net-2026-09-18.md`) — the fan-out that produced the row's
  two unverified readings.
