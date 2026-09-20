---
id: TK78
title: bulk_backfill.py is an unaudited second reconcile implementation; backfill() discards _bumped
brief: VERIFIED 2026-09-20: bumps cannot go downstratum; the ENUMERATOR (_live_keys_of vs _fan_out) is the item
pri: NOW
size: M
deps: []
related: [TK74]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-18
moved: 2026-09-20d
updated: 2026-09-20d
closed: 2026-09-20d
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-09-18

REASONED / READ by the `TK74` fan-out completeness critic (2026-09-18), NOT re-verified first-hand here. Flagged, not claimed -- the first action is verification.

Two derived-state producers got zero attention in the whole `TK73`/`TK74`/`TK75` line of work:

* **`index_v4/bulk_backfill.py`** says at `:20` that it "mirrors `DeltaProcessor._reconcile` step for step", and `index_v4/bulk_build.py:29` claims the result is "byte-identical to running `DeltaProcessor.backfill()` per object". It emits no outbox rows and contains **no quiescence, settle, or fixpoint check of any kind** (the only two `InvariantViolation` raises, `:243` and `:255`, are unrelated). It is the offline bootstrap path behind `connectedstore.build_index`.
* **`index_v4/processor.py::DeltaProcessor.backfill`** (`:1714-1726`) ends with `self._bumped = []` -- **DISCARDING** the bump list that `::_run_cascade` fans out into its invalidation map (twice). Plausibly sound because backfill sweeps every object in topo order, but a bump landing on a LOWER stratum from a HIGHER stratum's reconcile would be dropped.

WHY IT MATTERS: if `TK74`'s answer is "a per-write staleness check should exist", these two paths silently get none -- and a second reconcile implementation that mirrors the first "step for step" is precisely the kind of claim that rots without a differential pin.

FIRST ACTION: verify the two readings above first-hand (they are a subagent's), then decide whether `bulk = replay` deserves a DIFFERENTIAL pin in Python rather than only the Lean statement `P24` proposes. Related: `P24` (Lean `bulkState = replay`), `TK74`.

### 2026-09-19f

PROMOTED to NOW 2026-09-19f by the session that closed TK77/TK87/TK72, with the reasoning
here rather than on the banner. No new work done on this row.

Why this one, of the fifty ready rows: it is the only open item whose FIRST ACTION is a
first-hand check of a possible EQUIVALENCE defect (`CLAUDE.md` sec  "Who decides": the
primary consideration is that the graph index gives the same answers as the set engine, and
`bulk_backfill.py` is a SECOND producer of derived state whose claim to match the first is
prose). Everything else near the top of `ready` is a coverage, perf or docs item.

(!) Its two readings are a subagent's (`TK74` fan-out, 2026-09-18) and are explicitly NOT
verified. Verify both first-hand before planning anything:
  1. `index_v4/bulk_backfill.py` has no quiescence/settle/fixpoint check -- grep the file,
     do not trust the summary;
  2. `index_v4/processor.py::DeltaProcessor.backfill` ends by discarding `self._bumped`, and
     whether a bump can land on a LOWER stratum during a topo-order sweep is the actual
     question -- construct it or show it cannot happen.

Two live precedents for why verification comes first: `TK72` (closed this session) was a
CONFIRMED-but-small item whose stale brief still said UNVERIFIED, and `TK67`, where a
subagent's "the symbol does not exist" nearly deleted a sound trap. A differential pin
(`bulk == replay` in Python, not only the Lean statement `P24` proposes) is the plausible
landing shape, but it is a DECISION for the verifying session, not a plan to inherit.

### 2026-09-20

VERIFICATION PASS DONE -- both of the row's readings are CONFIRMED literally, the question
it names as "the actual question" is ANSWERED NO from the code, and its headline is
materially wrong about where the risk is. Map:
docs/tk78-offline-bootstrap-audit-2026-09-20.md (ACTIVE-PLAN; freeze when this closes).
No code edited: this is the scouting, landed before the edit.

READ 1 (CONFIRMED). index_v4/bulk_backfill.py has no quiescence/settle/fixpoint check.
Refinement the row lacks: its two InvariantViolation raises are CYCLE guards (::_topo :243
"the in-memory derived graph is cyclic"; ::_add_edge_existence :255) and its one `while`
loop (:231) is Kahn, not a fixpoint iteration. The design substitutes incremental
reachability with immediate visibility for iterating -- asserted nowhere, which is the
honest form of the complaint.

READ 2 (CONFIRMED, line moved). ::DeltaProcessor.backfill is :1820-1832 today, not
:1714-1726 (rotated under the TK72/TK87 edits; :1694 is now the tail of ::_settle). It does
end `self._bumped = []`. But it is DELIBERATE: ::_live_keys_of (:1777) documents "Live
maintenance reaches those objects via dependents-invalidation; backfill must reach them by
ENUMERATION." Backfill replaces fan-out with enumeration by design.

THE ROW'S "ACTUAL QUESTION" IS ANSWERED: A BUMP CANNOT LAND ON A LOWER STRATUM. Proof, two
first-hand facts. (a) zanzibar_utils_v1.py::_stratify (:2064) is Kahn over plan.deps, so a
dependent stratum is STRICTLY greater; a residual cycle raises CyclicDerivedDependency.
(b) ::_fan_out reads compiled.dependents only, and in ::_plan_deps_and_fanout (:2002-2052)
EVERY dependents.setdefault(k,...) is immediately preceded by dep(k) in all four branches,
so dependents is exactly a subset of reverse(deps). (target_feeders/tupleset_feeders are
populated WITHOUT dep(), but ::_fan_out never reads them.) A bump can only target strata
ahead of the sweep; no ordering is lost. Close this sub-question.

HEADLINE NARROWED. bulk_backfill ::_reconcile (:709) calls the SAME compiled closures the
live processor does -- plan.stars_fn (:715), plan.check_fn (:689,:737,:751,:778) -- and
::_BulkEvalContext (:63) implements processor::_EvalContext's callback protocol. Its own
words: "Only state ACCESS is mirrored." Duplicated: state access + iteration order. Not
duplicated: the semantics.

CENSUS (subagent, then reconciled first-hand -- every claim below re-checked against the
tree before writing). The bootstrap IS pinned against the live path, by
formal/conformance/test_conformance_bulk_state.py::test_state_bulkbuild_vs_pythongraph
(25 corpora; VERIFIED live because backends.py::graphindex_drive:88 runs proc.run_cascade
per tuple), by tests/test_invariants_derived.py::test_backfill_vs_live_equivalence (:220 --
the only pin of DeltaProcessor.backfill itself), and by
tests/test_connectedstore_build.py::test_built_index_equals_live_maintained.

(!) THE MOST-CITED GATE IS MISLABELLED. VERIFIED at connectedstore/build.py:92-107: the
bulk=False arm is a leaf-only add_tuple replay + ONE backfill(), with NO per-write cascade
-- its own comment says "This IS the identity gate's reference side". So
tests/test_bulk_build.py::test_bulk_build_identical_to_incremental is OFFLINE-vs-OFFLINE,
and any defect shared by backfill() and bulk_backfill passes it green. tests/test_matrix.py
and tests/parity.py contain no offline path at all.

(!) THE REAL HOLE, and the row was right to be suspicious one layer below where it pointed.
_live_keys_of == _fan_out is the offline path's whole correctness argument, and it is
asserted NOWHERE: grep -rn '_bumped|_live_keys_of' tests/ formal/ --include=*.py returns
ZERO. Worse, the widest gate cannot see a gap here in principle -- bulk_backfill.py has its
OWN copy of the enumerator (::_live_keys_of :808, header "mirrors DeltaProcessor.backfill /
_live_keys_of"), so test_bulk_build compares copy A against copy B and a SHARED
under-enumeration cancels on both arms.

DECISION (mine, per CLAUDE.md "Who decides"; overrule cheaply). TK78 is three items.
(i) THE ENUMERATOR IS THE ITEM -- pin _live_keys_of against the key set _fan_out delivers,
with the sabotage that must redden it (drop one spec.kind branch and watch test_bulk_build
stay GREEN). The fixture must have a dependent with NO positive leaf of its own or the pin
is vacuous; two exist (tests/test_stored_cache_scope.py::_TTU_SCHEMA :241,
tests/fga_schemas/demorgans_law_1.fga) and neither is in a live differential today.
(ii) REMOVE HISTORIES is real but SEPARATE -- the live differentials are add-only apart from
one history with one remove (tests/test_connectedstore_build.py:41), while bulk builds from
SURVIVING TUPLES and the live arm replays a HISTORY, which is exactly where the two
constructions may legitimately diverge. Same shape as TK87. Wants its own row.
(iii) A stale docstring, ten minutes, below.
(i) before (ii) because (i) is unpinned-by-measurement while (ii) is thinly-pinned, and a
shared under-enumeration is invisible to every existing gate.

(!) NEW FINDING, doc-rot in a GATED module, filed separately as TK90.
formal/conformance/test_conformance_bulk_state.py says of bulk_build.py's I14
crossable-middle loop: "The I14 loop is pinned by NOTHING ... because no bulk-built corpus
in the tree has a crossable shape." Its paragraph is stamped "Measured 2026-09-06"; P22
closed exactly that on 2026-09-16. READ tests/test_bulk_build.py: ::_owc_star_ttu_tuples
(:389) is a non-empty-crossable_shapes corpus in _CORPORA (:434-445) and
::_assert_r4bf_features clause (g) (:609-640) pins the loop PRODUCT structurally, with a
mechanical refusal (:639) of a masking corpus. BOTH halves of the sentence are false. This
is TK88 pointed the other way -- a module advertising a hole it no longer has -- and it is
worse, because the next session reads it and re-does P22.

NEXT ACTION for whoever takes this row: doc sec 6 step (i). Everything it needs is measured.

### 2026-09-20d

CLOSED. Step (i) of the three-way split LANDED and step (iii) with it; (ii) is `TK91` and
stays open. Map frozen at [`docs/tk78-offline-bootstrap-audit-2026-09-20.md`](../docs/tk78-offline-bootstrap-audit-2026-09-20.md),
whose 2026-09-20d correction is the part to read.

LANDED: `tests/test_backfill_enumeration.py` (3 tests, green). The offline path's whole
correctness argument -- `_live_keys_of` reaches by ENUMERATION what `_fan_out` reaches by
invalidation -- now has an assertion that says so. Fixture: `access` / `alias` / `deep` each
carry EXACTLY ONE positive leaf, of kind `derived-ttu` / `derived-computed` /
`derived-tupleset-ttu`, so the recursion is the only route to those objects;
`::test_fixture_keeps_the_enumeration_load_bearing` mechanically refuses a later edit that
gives one of them a storage family and quietly makes the pin vacuous.

(!) DESIGN DECISION worth inheriting: ground truth is every key the live cascade's
`reconcile` CHANGED, not every key it SCHEDULED. `READ` -- the cascade over-schedules,
reconciling `('doc', 'deep', 'f1')`, a FOLDER name under a doc relation, mapped in by
`::_map_deltas_to_keys` off the `folder#ok` derived edge. It is a no-op and the enumerator is
right not to reach it. `DeltaProcessor._check_cascade_fixpoint`'s docstring records the same
asymmetry from the other side.

(!) THE MAP'S HEADLINE CLAIM WAS MEASURED FALSE, AND THE ROW SHOULD SAY SO. Doc sec 5
reasoned that `tests/test_bulk_build.py` "compares copy A against copy B and a shared
under-enumeration cancels on both arms". With BOTH copies of the enumerator mutated, three of
the four kind-drops redden `test_bulk_build_identical_to_incremental` ITSELF (`-rf`
attribution: `[boolean]`, `[demorgan]` for the derived-ttu drop). `REASONED`, unverified: the
copies read different substrates -- `processor.py` re-queries `node_v4` rows mid-backfill,
`bulk_backfill.py` reads an in-memory `family_names` index seeded at load. So the honest case
for the new module is narrower than the row claimed and still real: NO SINGLE EXISTING MODULE
SEES ALL FOUR KINDS. `test_bulk_build` misses `derived-computed` outright; the conformance
module misses the other three; `tests/test_invariants_derived.py` was green on every row.

SWEEP (`.scratch/tk78_sweep.py`, harness throwaway, table tracked in the module docstring and
the map). RED = caught. Both copies mutated together unless marked.
  drop derived-computed        new RED | bulk_build green | conformance RED (3 corpora)
  drop derived-ttu             new RED | bulk_build RED (2) | conformance green
  drop derived-tupleset-ttu    new RED | bulk_build RED (1) | conformance green
  drop derived-userset pred    new RED | bulk_build RED (1) | conformance green
  drop `rel` from preds        all green  -- INERT, see below
  recurse through NEGATIVE     all green  -- inverse control, expected
  M0 flip the pin's own claim  new RED, attributed to the one test; others green

(!) THE INERT ROW IS `TK91`'s, AND IT IS NOW MEASURED RATHER THAN ARGUED. Dropping `rel` from
`preds` moved nothing anywhere. That entry exists for objects enumerable only by their PUBLIC
family -- derived state that outlives the leaf which produced it, i.e. a REMOVE. Every corpus
in play is add-only, so the branch cannot move. Reported as inert per
`docs/sabotage-procedure.md`, never read as a clean pin; recorded on `TK91`.

ALSO LANDED (step (iii) / `TK90`): the dated correction at
`formal/conformance/test_conformance_bulk_state.py`'s "pinned by NOTHING" paragraph. The
2026-09-06 measurement is left standing; the correction names `P22`, `_owc_star_ttu_tuples`
(`:389`, in `_CORPORA` `:445`) and clause (g) (`:609-640`), all re-verified first-hand here.

STILL OPEN from this row's own analysis: `TK91` (remove histories, sec 6 (ii)).
