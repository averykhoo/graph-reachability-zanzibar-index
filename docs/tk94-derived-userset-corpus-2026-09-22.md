# `TK94` — a derived relation as a userset subject: where the hole actually is

**FROZEN at `TK94`'s close, 2026-09-22d.** Every figure in the body was measured on
`2026-09-22` against the tree that became the `TK94` commit; the body is provenance, not a
living status. Corrections append **dated at the top**, never edited into the body. Live
state is `python scripts/task.py show TK94` and `python scripts/gate_status.py`, never this
file. The one deliberately deferred widening is `TK102`.

## Correction / addition, 2026-09-22d (appended; the body below is as-written)

Two things a consumer census turned up that the body does not say, salvaged here because
they were otherwise recorded only in a gitignored agent report. Both are **first-hand READ**
by that agent and **re-verified here** before writing them down.

1. **`test_conformance_spec.py::_SPEC_SCHEMAS` merges four dicts with no key-disjointness
   assertion, so a name collision is SILENT.** It is
   `{**SCHEMAS, **TTU_USERSET_SCHEMAS, **SELF_REFERENTIAL_SCHEMAS, **MULTI_STRATUM_SCHEMAS}`
   — a duplicate key in a later dict would shadow an earlier corpus and the spec arm would
   quietly run one schema twice instead of two schemas once, with the collected count
   unchanged. This entry is one word away from the existing `derived_userset`
   (§1), and nothing mechanical keeps them apart. Not fixed here: it is a latent hole
   unrelated to this item, and the fix (an assertion over the four key sets) wants its own
   sabotage.
2. **A trap for `TK102`, if this corpus is ever promoted into `GRAPH_FRAGMENT`:**
   `test_conformance_state.py:621` pins `set(golden) == set(GRAPH_FRAGMENT)` by **EQUALITY**,
   not containment, against the `derived_arm_multiplicity.json` golden. So promotion is not a
   one-line list edit — the golden must be regenerated with `ZANZIBAR_UPDATE_SNAPSHOTS=1`, in
   its own commit. §3 says promotion would be the ZT-P3-3 mistake and should not happen; this
   is what would break first if someone tried it anyway.

Also confirmed by that census and worth stating because it bounds the blast radius: **no
golden or snapshot anywhere in the repo is keyed by a `SCHEMAS`-only corpus name**
(`derived_arm_multiplicity.json` is `GRAPH_FRAGMENT`-keyed; `tests/snapshots/compiled_ruleset/`
is keyed by `.fga` filename), and **no `.lean` file enumerates corpus names**.

## 0. Why this file exists

`TK94` is step 1 of the goal chosen 2026-09-22c (*make the assurance surface honest and
legible, not wider*). Its first action as filed is one line — "add ONE `SCHEMAS` entry
whose userset subject names a derived relation". Scouting it first-hand changed three
things about that line: **what the hole is**, **what an entry costs**, and **which list the
entry must not go into**. All three are below, so the next session does not re-measure.

## 1. The hole is narrower than the row says, and it is in a different place

`TK94` (and the goal census it feeds) says the class is *"an input class the whole
conformance surface has never run on"*. **That is wrong, and the row's own narrower
sentence is right.** (First-hand READ, 2026-09-22.)

`formal/conformance/corpus.py::TTU_USERSET_SCHEMAS` has carried an entry named
`derived_userset` since 2026-07-27 — literally this class:

```
type user
type group
  define base: [user]
  define kicked: [user]
  define member: base but not kicked
type doc
  define viewer: [group#member]
```

Measured 2026-09-22 (`.scratch/tk94/probe1.py`, transcribed here because `.scratch/` is
gitignored): it compiles to `2` strata with plans
`('doc','viewer') -> [('viewer.0','derived-userset',True)]` and
`('group','member') -> [('member.0','closure',True), ('member.1','closure',False)]`;
over its `126`-query grid **oracle == set engine**, and the real graph index has `0`
mismatches against the oracle.

So the true statement is the one `TK94`'s title makes and its prose then over-reaches from:
**zero of the `26` `SCHEMAS` entries pair a derived relation with a userset subject.** The
class is not unseen — it is seen by `test_conformance_spec.py` **only**, which is
`sem` x oracle x set engine. What has never run on it is **every arm that involves the
graph index**: the add/remove churn arms, the driven-vs-fresh-build state comparison, and
the bulk-vs-incremental identity. That is the equivalence-relevant half, and it is exactly
the gap `TK92` had to hand-build a fixture for in `tests/test_reg_tk92_bulk_rel_term.py`.

`TTU_USERSET_SCHEMAS`' header says why it was parked there: the shapes are outside
`W4Fragment`, so "the graph conformance / state / remove gates must NOT carry them"
(`corpus.py:843-861`). §3 below shows that reason is **half right** — it holds for the
Lean-claiming gates and does not hold for the python-to-python ones.

## 2. The cost is ADDITIVE, not combinatorial — the row's first trap is over-stated

`TK94`'s trap reads: *"`formal/conformance/test_conformance_enum.py` enumerates every store
up to a bound, so one schema there is a combinatorial cost, not an additive one. Size the
entry against the enum bound before adding it."*

**First-hand READ 2026-09-22, `test_conformance_enum.py:197`:** that module parametrizes
over `_SHAPES` — a hand-written dict of six names at `:136` — **not** over `SCHEMAS`. It
indexes `SCHEMAS[name]` at `:200` for the six it already names. A new `SCHEMAS` entry adds
**nothing** to it. The combinatorial cost is real but it is conditioned on separately adding
the name to `_SHAPES`, which this item does not do and should not.

Same shape for the "generated" arm: `test_conformance_generated.py:150` parametrizes over
`SEEDS` and does not import `SCHEMAS` at all.

So of the four arms the row says one entry widens at once — enumerated, generated, remove,
bulk — **the first two do not widen**. The remove and bulk arms do, and they are the ones
worth having. The trap is not deleted, it is re-pointed: it is a trap about `_SHAPES`.

## 3. The decision: `SCHEMAS` yes, `GRAPH_FRAGMENT` no

Recorded per `CLAUDE.md` § "Who decides" — this is a Lean-shaped scope call, taken by the
session rather than handed back.

**The class is outside `W4Fragment` by a NAMED field, and the field is classified SILENT.**
`formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE['term']` demands a
conjunction: a derived relation is never the target of a TTU rewrite (`NoTtuTarget`) **and
never appears as the predicate of a stored userset subject (`NoStoreSubjectR`)**. Its note
says the `NoStoreSubjectR` half is *"fully SILENT: a stored subject whose predicate is a
derived relation was ADMITTED (added=True)"* — probe line at `:83` of that module. Python
accepts it; no theorem routed through `graph_correct` says anything about it.

Therefore:

- **NOT `GRAPH_FRAGMENT`.** `zcli` does not gate on `W4Fragment` (it exits nonzero only on
  run failure and non-drained-ness), so an out-of-fragment corpus placed there does not
  fail loudly — it silently compares two models no theorem relates. That is the `ZT-P3-3`
  mistake, written up at `corpus.py:769-790`, and this would be the third time.
- **Yes `SCHEMAS`**, because the arms `SCHEMAS` membership buys are all scope-clean:
  * the spec legs (`test_conformance_random.py`, `test_conformance_remove.py`'s first two
    tests, `test_conformance_spec.py`) compare `sem` x oracle x set engine, and `sem` is a
    pure function of the final store with no fragment hypotheses — scope-clean at any
    stratifiable schema (the argument `corpus.py:915-922` already makes for this very
    entry);
  * the three GRAPH legs in `test_conformance_remove.py` — `test_graph_remove_sequences`
    (`:405`), `test_graph_full_churn_restores` (`:480`),
    `test_graph_remove_bulk_build_survivors` (`:668`) — parametrize over `sorted(SCHEMAS)`,
    not `GRAPH_FRAGMENT`, and compare the graph index against the **oracle** and against a
    fresh add-only build. Their docstring says it outright: *"(Scope: sem/Lean deferred)"*.
    No Lean claim is made, which is precisely the licence `corpus.py:853-861` already grants
    the python-only differentials on `wildcard_userset` / `derived_tupleset_ttu`.

**The safety is computed, not promised.** `test_conformance_remove_graph.py:127` builds
`_REMOVABLE` from `GRAPH_FRAGMENT`, and `:151` additionally asserts each name is in
`test_conformance_graph._THEOREM_BACKED` with the ZT-P3-3 reason quoted. A `SCHEMAS`-only
entry is excluded by construction from every Lean-claiming gate. `test_conformance_graph.py`
/ `test_conformance_state.py` / `test_conformance_bulk_state.py` all parametrize over
`sorted(GRAPH_FRAGMENT)` (`:302`, `:331`, `:450`, `:718`, `:178`) — same exclusion.

**A near-duplicate is accepted deliberately.** `TTU_USERSET_SCHEMAS::derived_userset` stays
where it is; the new entry is not a move. Reasons: the existing entry's four tuples are
tuned for the spec grid and carry no rel-exclusive or subtrahend-only name, and moving it
would silently change which dict `test_conformance_nary_strata`'s coverage floors attribute
the `derived-userset` leaf kind to. The new entry says in situ why both exist.

## 4. The entry, and what each tuple is for

Name: `derived_userset_subject`. Measured 2026-09-22 (`.scratch/tk94/probe2.py`).

```
type user
type group
  define allowed: [user]
  define blocked: [user]
  define member: allowed but not blocked
type doc
  define viewer: [user, group#member]
```

| tuple | role — why it is not decoration |
|---|---|
| `alice allowed g1` | positive-leaf state; `alice` IS a `member` of `g1` |
| `bob allowed g1` + `bob blocked g1` | the discriminating pair: `bob` is excluded, so `viewer@d1` must be `False` for him |
| `carol blocked g3` | **subtrahend-only, and not a userset subject** — nothing enumerates `g3`. This is what makes the `spec.positive` filter in `_live_keys_of` load-bearing; `TK92`'s sweep `M3` was GREEN until its fixture gained exactly this (`test_reg_tk92_bulk_rel_term.py:152-158`) |
| `g1#member viewer d1` | the class itself: a stored userset subject whose predicate is derived |
| `g2#member viewer d2` | **rel-exclusive** — `g2` has no `member` state at all, so it is interned at LOAD time and enumerated by the leading `rel` term and by nothing else (`TK92`'s refutation) |
| `carol viewer d2` | the `[user]` direct arm, so `viewer`'s `closure` leaf is exercised alongside the `derived-userset` one |

Compiled (measured `2026-09-22`): `2` strata;
`('doc','viewer') -> [('viewer.0','closure',True), ('viewer.1','derived-userset',True)]`,
`('group','member') -> [('member.0','closure',True), ('member.1','closure',False)]` —
byte-for-byte the leaf shape `TK92`'s fixture produces.

Three-backend result on the corpus store, `2026-09-22`: grid `364` queries, `9` True,
**oracle == set engine**, graph index `0` mismatches against the oracle.

Grid size in context (measured `2026-09-22`, `.scratch/tk94/probe3.py`): median across all
`32` curated corpora is `85`; `deep_grid` is `2880`; the largest non-`deep_grid` `SCHEMAS`
corpus is `residue_rich` at `250`. `364` is second-largest in `SCHEMAS`. A one-doc variant
measures `264` but collapses `d1`/`d2`, which destroys the rel-exclusive discrimination
(`g2`'s doc must have no other grant), so the wider grid is paid on purpose.

## 5. What landed, measured

### 5.1 The nine new arms, by node id

Collected `2026-09-22`: `formal/conformance/` **572 → 581** from the corpus entry, then
**582** with the floor test of §5.3. `tests/` unchanged at `1279` (no module under `tests/`
reads `corpus.SCHEMAS`; the only reference into the package is
`tests/test_admission_rejected.py:410`, which imports `backends`). The literal diff of
collected node ids:

```
test_conformance_random.py::test_random_stores[derived_userset_subject]
test_conformance_remove.py::test_remove_sequences[derived_userset_subject]
test_conformance_remove.py::test_full_churn_restores[derived_userset_subject]
test_conformance_remove.py::test_graph_remove_sequences[derived_userset_subject]
test_conformance_remove.py::test_graph_full_churn_restores[derived_userset_subject]
test_conformance_remove.py::test_graph_remove_bulk_build_survivors[derived_userset_subject]
test_conformance_spec.py::test_spec_vs_oracle[derived_userset_subject]
test_conformance_spec.py::test_spec_vs_setengine[derived_userset_subject]
test_conformance_spec.py::test_oracle_vs_setengine[derived_userset_subject]
```

Nothing from `enum`, `enum_state`, `generated`, `graph`, `state`, `bulk_state`,
`remove_graph`, `direct_arm` — which is §2 and §3 confirmed mechanically rather than
argued. `9 passed, 572 deselected in 26.11s`, rc 0.

### 5.2 Which branch each new arm reaches — the row's third trap, answered

A passing arm is not a running arm, so the branch the corpus exists for was measured
directly: the leading `rel` term of
`index_v4/bulk_backfill.py::_BulkBackfill._live_keys_of`. Tracked probe, re-runnable:
[`formal/probes/tk94_new_arm_reach_2026-09-22.py`](../formal/probes/tk94_new_arm_reach_2026-09-22.py)
— it drives the real gate path (`graphindex_drive_ops` + `bulk_build_drive`, the five seeds
`test_graph_remove_bulk_build_survivors` uses) and asks, per corpus, whether the `rel` term
ever enumerated a name the positive-leaf half did not.

Result over all `27` `SCHEMAS` entries, `2026-09-22`, rc 0:

- **`derived_userset_subject` is the only `True`.** Example: seed `0`, key
  `('group','member')`, rel-only `['g1', 'g2', 'x_group_2']`.
- Eighteen corpora **call** `_live_keys_of` (between `5` and `15` times across the seeds)
  and never once get a rel-exclusive name — they run the line and learn nothing from it.
- Nine never call it at all (untainted schemas; no derived relation, so no backfill).

**(!) The instrument lied first, and in the direction that reads as a finding.** The first
run reported eight corpora `SKIPPED` on a `TypeError`. It was the wrapper, not the code: the
shipped `_live_keys_of` **recurses** through `self._live_keys_of` and unions the result into
a set, and the wrapper was returning a `list`. Eight rows of "could not measure" would have
passed for a property of those corpora. This is the `GL-1` lesson (control your instrument,
not just your subject) and the fix is noted in the probe at the line that caused it.

### 5.3 The permanent pin

`formal/conformance/test_conformance_nary_strata.py::test_schemas_carries_a_derived_userset_subject`
— a floor asserting (a) some `SCHEMAS` corpus stores a userset subject whose predicate is
derived, and (b) some such subject object carries no state of its own, i.e. the
rel-exclusive shape. (b) is the load-bearing half: without it the corpus reaches the branch
and cannot discriminate it, which is the state all `26` predecessors were in.

**The floor is over `SCHEMAS` specifically, not the harness-wide corpora** — written over
`_all_corpora()` it would stay green with the entry deleted, rescued by the spec-side twin.
Sabotage `S1` is that control. Full transcript in the test's own docstring; the headline is
`CLEAN 20 passed`, `S1`/`S2`/`S3` each `1 failed, 19 passed`, restored `20 passed`.

**`S0` is recorded because it is the easy mistake**: the first cut of `S1` renamed the dict
key instead of deleting the entry and came back green — correctly, since the floor tests the
class and not the name. A mutation that does not move the property under test reads exactly
like a clean pin.

### 5.4 Gate floors — a drift repair found by re-measuring, not by this corpus

`TK94`'s second trap says to re-measure `MIN_CONF_ALL` / `MIN_TESTS_ALL` rather than
estimate them. Doing so found that **both had silently stopped honouring the zero-headroom
contract** `CLAUDE.md` states:

| knob | was | live `2026-09-22` | of which TK94 | pre-existing slack |
|---|---|---|---|---|
| `MIN_CONF_ALL` | `546` | `582` | `+10` | `26` |
| `MIN_CONF_HEAVY` | `104` | `135` | `+5` | `26` |
| `MIN_CONF_REST` | `442` | `447` | `+5` | `0` |
| `MIN_TESTS_ALL` | `1209` | `1279` | `+0` | `70` |

So `26` conformance tests and `70` `tests/` tests could have been deleted with the gate
staying green. All four ratcheted, each with the instrument check the prior ratchets set as
precedent — set the floor one above live, observe the literal failure, restore:

```
FAIL: formal/conformance/ collects only 582 test(s); the gate floor is 583.
FAIL: tests/ collects only 1279 test(s); the gate floor is 1280.
```

both rc `1`. The `tests/` repair is unrelated to this corpus and is called out as such in
`verify.sh`'s own comment.

### 5.5 Count sites that go stale on `26 → 27`

`formal/conformance/doc_counts.py::check_corpus_count_prose` refuses a hand-written corpus
count that is neither live nor marked past, and three sites fired:
`test_conformance_remove.py:602` and `:725`, and `docs/tk92-bulk-rel-term-2026-09-21.md:77`.
Each was re-dated in place with a pastness word (a bare date is not enough — the checker
says so and it is right: *"measured `<date>` over all 26 corpora"* still reads as a current
coverage claim). `formal/FINAL_REVIEW.md`'s generated block was regenerated with
`python -m formal.conformance.doc_counts --generate`, never edited by hand.
`docs/goal-census-2026-09-22.md` carries a dated correction for the two overstatements §1
and §2 found in its `TK94` row.

### 5.6 Not done, and why

- **No module-wide mutation sweep.** `docs/sabotage-procedure.md` asks for one when a
  MODULE is added; this is one test appended to an existing module of twenty, and the sweep
  above covers its own predicate and helper. Said in the docstring too, not just here.
- **`_SHAPES` untouched.** Taking this corpus into `test_conformance_enum.py` is the
  combinatorial cost the row's first trap describes. It is a separate decision with a
  separate runtime budget, and it is the only remaining way to widen this class further
  inside the conformance harness.
- **`formal/probes/p6_inbridge_stability_2026-09-12.lean:478`** claims a property is "INERT
  on all 26 `corpus.SCHEMAS`". It is a `P6` scope claim rather than a count, so no checker
  sees it; whether it still holds at `27` is **UNVERIFIED**. `P6` is parked, so this is
  flagged and left.
