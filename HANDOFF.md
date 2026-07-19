# HANDOFF — start here

The single entry point for a Claude Code (or human) session on this repo. Read
this **first**, then [`CLAUDE.md`](CLAUDE.md), then whatever the task points into.

- **`CLAUDE.md`** = the durable contract (how to run things, conventions, the
  gate, invariants). It rarely changes.
- **`HANDOFF.md`** (this file) = the mutable state: current status + the open-TODO
  board. **Keep it current** — when you pick up or finish work, edit the board
  below. This is the "one thing to point at" so instructions don't have to be
  relayed each session.

> The formal subtree has its own compact entry point,
> [`formal/HANDOFF.md`](formal/HANDOFF.md) — read that before touching anything
> under `formal/`. This file is the whole-project analog.

---

## Current status — 2026-07-18

- **2026-07-18 — OPTIONAL assurance-widening arc OPENED; #1 Leaf/Direct-arm legs 1–3 pushed
  (`98773d3`/`0dd8d7b`/`8a9bee1`); gate GREEN; no Python change.** All four `FINAL_REVIEW.md
  §4` optional widenings scoped (recon + attack-first); durable design/resume state in
  [`formal/history/optional-widening-2026-07.md`](formal/history/optional-widening-2026-07.md).
  Direct-arm read-half + write-half admission + the diffing retraction crux are proven; the
  base-equation wall is characterized (`NoStoreSubjectR`-gated, leg 4 = 3 lemmas). Each leg
  Lean-only additive (`verify.sh lean` 415/415). See the Active-work board item + the design
  file to resume. Next (interleave plan): bank #3 state/enum (mostly Python) + #4 remove.
- **2026-07-17 — formal `rootB` fragment widening LANDED (Lean-only; no Python change).**
  `W4Fragment` no longer restricts the derived-def root operator — union- and
  computed-rooted derived defs are now in the proved scope (`RootBoolean` deleted;
  `schemaRewrites` taint-filtered to mirror `compile_ruleset`, closing a stale
  userset-sourced fanout-edge STATE divergence found by probe). Added the union-rooted
  witness `W4WitnessUnion` + three now-in-fragment conformance corpora
  (`taint_union_over_boolean` moved in; `taint_union_userset_arm` state-regression pin;
  `taint_computed_root_over_boolean`). Gate GREEN: `verify.sh` lean (415/415 audit) /
  conf-heavy 76 / conf-rest 212; full conformance 288/0-skip. `pytest tests/` unaffected
  (no backend change; 561 + 32 = 593 passed re-verified pre-push). Detail:
  `formal/history/PROOF_STATUS.md` 2026-07-17. **Committed as `397f975` (leg 1,
  taint filter) + `c3d3113` (leg 2, RootBoolean removal) + `265995d` (leg 3,
  witness + conformance + docs); pushed.**
- **2026-07-17 — the three OPEN 2026-07-17 divergences CLOSED (+ a 4th found en route)
  + reg13 admission wart fixed + fuzzer exclusions reverted; full gate GREEN; committed
  as `d517fb5`.**
  The three OPEN/latent divergences filed earlier today (below) were root-caused and fixed,
  their strict xfails flipped to plain pins: **Fix A** — the reconcile audit-set builder
  (`processor._leaf_concretes`, + `bulk_backfill` mirror) now lifts a referenced tainted
  relation's residue `upos` for `derived-computed`/`derived-userset` leaves (the X4b lift
  extended), closing the two answer-level completeness gaps **and a NEW 4th** (userset member
  of a granted userset over a derived relation). **Fix B** — a state-functional `implicit` flag
  (promote-on-record step 2d + a demote-on-release exception to core's explicit-is-sticky rule,
  I6 extended) closes the answer-benign canonical drift. **reg13** — `RuleSet.apply` now raises
  (not silent-drops) a raw write matching no declared restriction (a unanimity wart; production
  unexposed). Fuzzer exclusions reverted: `allow_usersets` default ON, `ttu_in_boolean` knob
  removed — zero active 2026-07-17 generator exclusions remain. `HYPOTHESIS_PROFILE=deep` hunt
  green (state trio 3/87 s, machines 3/310 s, rest 14/629 s, deep G4 1/45 s; no falsifying
  examples). Two read-only scout sweeps (read/enumeration symmetry; ~3,800 remove-heavy
  delta/lifecycle sequences) found ZERO further gaps. **Gate GREEN (2026-07-17): `pytest tests/`
  561 + 32 = 593 passed, 0 xfailed (cap-safe split); `verify.sh` lean PASSED (sorry-free,
  412/412) / conf-heavy 68 PASSED / conf-rest 195 PASSED; 6-seed fuzz sweep on
  `tests/test_hypothesis.py` (seeds 7/19/31/53/71/97) all 20 passed.**
  Details: `docs/spec-deviations.md` 2026-07-17 ("the three OPEN 2026-07-17 divergences CLOSED");
  formal note in `formal/CORRESPONDENCE.md` §7.
- **2026-07-17 — F1/F2 CLOSED + fuzzer blind-spot hardening landed; full gate green;
  committed as `d517fb5`.** The F1/F2 divergences (and their
  newly-found "detonation" — innocent-write lockout, a 3rd divergence) are closed by a
  compile-time scope rejection (`DoublyBridgedShapeError`, both backends, literal
  `T:*#p` ∩ object-wildcard criterion) + a set-engine ghost-hop safeguard (never
  fires, test-pinned). The generator blind-spot audit + hardening (G1/G2/G4/G5/D4
  + pins) landed; the deep hunt filed **three NEW latent divergences** (1 answer-benign
  drift, 2 graph completeness gaps — X4 family) as strict xfails — see Standing/latent.
  Gate: `pytest tests/` 582 passed + 3 xfailed; `verify.sh` lean (sorry-free, 412/412) /
  conf-heavy (68) / conf-rest (195) all PASSED; 6-seed fuzz sweep on
  `tests/test_hypothesis.py` green. Details: `docs/spec-deviations.md` 2026-07-17.
- **Everything green.** Both evaluation backends (set engine + graph index), the
  composition layer, and the Lean formal layer all pass their gates. Lean is
  sorry-free and axiom-clean (412/412). Known correctness bugs: only the two
  strict-xfail graph completeness gaps filed 2026-07-17 (Standing/latent).
- **2026-07-16 — found + fixed a real set-engine/graph admission divergence.** The
  previously-latent "bridge-edge residual" turned out to be constructible (a
  multi-hop cycle through a star bridge: set-accepted / graph-rejected). Fixed by
  making the set engine's flow-graph cycle check bridge-aware, mirroring the graph's
  `_ensure_bridges` (in-bridges concrete→`w_any`, out-bridges `w_all`→concrete, kept
  distinct). Parity restored; pinned by `test_reg10...`; no Lean change (set-engine
  admission is unmodeled). See `docs/spec-deviations.md`.
- **2026-07-16 — hardened the fuzzer against the whole star-bridge class.** Added a
  dedicated star-bridge schema generator + `StarBridgeParityMachine` to
  `tests/test_hypothesis.py`, a deterministic class pin, and `test_reg11...` (the
  object-wildcard / OUT-bridge analog of reg10). Closed the blind spot that let the
  reg10 bug hide. The new generator also surfaced **two exotic OWC-on-self-referential-
  relation divergences (F1 graph-incomplete, F2 graph-over-permissive)** — filed as
  latent/out-of-scope (backlog + `docs/spec-deviations.md`), NOT chased. Test-only
  change; no backend/Lean change.
- **Perf optimization arc is CLOSED at round 5** — the measured worklist is
  exhausted (the last candidates N13/N14 were assessed and declined on a fresh
  profile). Record: [`docs/history/perf-round5-2026-07.md`](docs/history/perf-round5-2026-07.md).
  Standing perf guardrails (fence, dead-ends, hygiene) live in
  [`docs/perf-next-round.md`](docs/perf-next-round.md).
- **Clean on `master`.** Last change: the formal `rootB` fragment widening above
  (commits `397f975` / `c3d3113` / `265995d`).

---

## Open-TODO board

### Active work
- [ ] **IN PROGRESS 2026-07-18 (Claude): OPTIONAL assurance-widening arc (`FINAL_REVIEW.md §4`).**
      Four targets scoped (recon + attack-first probes); durable design + resume state for
      ALL of them in [`formal/history/optional-widening-2026-07.md`](formal/history/optional-widening-2026-07.md).
      **#1 Leaf widening (Direct arm)** legs 1–3 landed + pushed (`98773d3` read-half
      `evalE_computedOrDirect`; `0dd8d7b` write-half admission + diffing retraction crux
      `reconcileKeyD_retracts_excluded`; `8a9bee1` base-equation wall characterized —
      needs a `NoStoreSubjectR` hyp). Each leg Lean-only additive, gate GREEN (`verify.sh
      lean` 415/415). **#3 state/enum widening COMPLETE** (2026-07-18b–e). **#4 remove legs
      R1–R4 landed** (`36e6762`/`ebdf6f9`/`de93853`/R4-part-1+2 in `RemoveConfluence.lean`;
      additive; gate GREEN: lean 415/415, conf-heavy 76, conf-rest 220). **#4 Leg R5 RE-SCOPED
      2026-07-19c — the `remove` constructor is MONOLITHIC and gated on a MISSING prerequisite
      (rebuild-existence over `T.erase t`).** Deep trace this session (tree left GREEN): the
      constructor forces `graph_correct_w3d2E`'s T2b remove case (no partial landing), and BOTH
      discharge routes need a build-FROM-STORE `∃ σ, ReachedByW3d2E σ S T' ∧ Drained` — absent, but
      REACHABLE via `foldAdmits_of_acyclic`. **Landed additively (green):** the T2a Group-A
      STRUCTURAL remove-case discharges (`removeLoggedRules_residue`, `mem_removeLoggedRules_edges`,
      `residueHygienic_/residueDeclared_removeLoggedRules`). **R5a LANDED 2026-07-19d** (build-FROM-store
      `exists_admitted_erase`). **★ #4's LEAN REMOVE LEG COMPLETE 2026-07-19f** — landed + pushed across
      R5b-i…iii-b (`d7d6f7d`/`2b7456f`/`a16c927`/`09eb272`/`7a594bb`; all additive, `verify.sh lean` green,
      audit 415/415, standard axioms). The `remove` constructor now lives on `ReachedByW3d2`/`C`/`E`, so
      T2a (full `Inv`) + T2b (`check = sem`) hold over remove-states and the audited `graph_correct` /
      `graph_reached_inv` / `Exec.graphRun_check_eq_sem` cover retraction — SCOPE: removing a
      **validly-stored** tuple (the constructor carries the pre-remove store's disciplines + `hdrain`,
      faithful to `TupleSource.remove` + the W4Fragment carries). Arc: substrate relocation → the crux
      (`reachedByW3d2_untOccCount` + `untaintedShadow_removeLeg`) → the settledness-dual stack → the
      source-occurrence invariant (`reachedByW3d2_srcOccCount`) → the constructor + 21-site discharge; a
      mid-arc blocker (the erase store-hypothesis direction) was root-caused and fixed by the guard.
      **#4 follow-ups (non-blocking):** (1) `FINAL_REVIEW.md` scope-wording sweep (§4(d) etc. now
      under-claim — stale-conservative); (2) optional Exec-driver remove hardening (the zcli/`Exec` fold is
      still add-only, so removes are PROVED but not DRIVEN end-to-end); (3) Avery to review the guard design
      decision. Then the remaining optional widenings: #1 Direct-arm leg 4 (the wall) / TTU-userset half,
      #2 strata (>2). See `formal/history/PROOF_STATUS.md` 2026-07-19f + `formal/HANDOFF.md` "THE NEXT TASK".
- [x] **DONE 2026-07-17 (Claude): formal fragment widening — the `rootB` gap CLOSED (gate GREEN).**
      Union- and computed-rooted derived defs are now inside the proved `W4Fragment`
      (the derived-def ROOT operator is unrestricted; shape condition is `ComputedOnly`
      alone). Three legs: (1) `397f975` — `schemaRewrites` taint-filtered (mirror of
      `compile_ruleset`'s taint routing; a probe had found the UNFILTERED fanout leaked a
      stale userset-sourced edge `group:eng#member → approver` into the drained Lean state
      — a real model-vs-Python state divergence); (2) `c3d3113` — `RootBoolean` deleted,
      `W4Fragment` widened; (3) this leg — the union-rooted non-vacuity witness
      `W4WitnessUnion` (`FullScope.lean`, audited) + the conformance widening:
      `taint_union_over_boolean` moved INTO `GRAPH_FRAGMENT`, two new pins added
      (`taint_union_userset_arm` — the stale-fanout STATE regression;
      `taint_computed_root_over_boolean` — computed roots). Gate: `verify.sh` lean
      (sorry-free, axiom audit **415/415**) / conf-heavy **76** / conf-rest **212** all
      PASSED; full `formal/conformance/` **288** passed, 0 skips. No Python behavior
      change (no `docs/spec-deviations.md` entry). Detail: `formal/history/PROOF_STATUS.md`
      2026-07-17. Remaining fragment work: `computedOnly` leaves (`Direct`/TTU arms) + >2 strata.
- [x] **DONE 2026-07-17 (full gate GREEN; committed as `d517fb5`).** **Closed the three OPEN 2026-07-17 divergences (+ a 4th
      found en route) + the reg13 admission wart; reverted the fuzzer exclusions.** Fix A (the
      `processor._leaf_concretes` `upos` lift for `derived-computed`/`derived-userset` leaves,
      mirrored in `bulk_backfill`) closed the two graph completeness gaps + the new 4th; Fix B
      (state-functional `implicit` flag — promote-on-record step 2d + demote-on-release, I6
      extended) closed the answer-benign canonical drift; reg13 made `RuleSet.apply` raise on a
      no-restriction-match raw write. `allow_usersets` default flipped ON, `ttu_in_boolean` knob
      removed — no active 2026-07-17 generator exclusions remain. `HYPOTHESIS_PROFILE=deep` hunt
      green; two read-only scout sweeps found zero further gaps. New pins: reg13 block +
      `test_graph_userset_member_through_granted_userset_over_derived` +
      `test_pderived_recording_promote_demote_hysteresis` + `test_i6_upos_userset_implicit_bites`;
      three prior strict xfails flipped to plain pins. Details: `docs/spec-deviations.md`
      2026-07-17; formal note in `formal/CORRESPONDENCE.md` §7.
- [x] **DONE 2026-07-17 (gate green; committed as `d517fb5`).**
      **F1/F2 fix (started 2026-07-17, Claude+Avery):** compile-time scope rejection of
      shapes in `bridged_in ∩ bridged_out` (a shape that is both a wildcard-userset
      shape and an object-wildcard shape — the F1/F2 precondition). Decision: reject at
      compile (`UnsupportedByGraphIndex`, third entry in the scope-rejection family;
      OpenFGA supports neither construct) rather than a write-time ghost-hop gate.
      Plus: always-on set-engine flow-graph ghost-hop safeguard (w_all→w_any for
      doubly-bridged shapes; unreachable post-rejection, hypothesis asserts it never
      fires), regression pins, fuzzer blind-spot audit + generator hardening.
      New findings recorded en route: both F1/F2 states detonate on innocent later
      writes (graph rejects plain grants set+oracle accept — a 3rd divergence), and
      all→any is NOT read semantics (oracle-pinned via acyclic cross-type probe).
      **Generator-hardening sub-item LANDED 2026-07-17** (fuzzer blind-spot audit closed):
      `schema_asts` now emits concrete usersets (G2), a new `bool_star_bridge_configs` +
      `BoolStarBridgeParityMachine` cross booleans × star-bridge (G1), the machines gained
      `check`/`rebuild` rules + ghost-hop never-fires teardown asserts (D4/G5), and the
      lookup gate runs over generated schemas (G4). THREE OPEN/latent divergences filed as
      strict xfails (a deep `HYPOTHESIS_PROFILE=deep` hunt drove the exclusion calibration) —
      see the Standing/latent section below and `docs/spec-deviations.md` 2026-07-17 (fuzzer
      blind-spot hardening).

### Deferred / backlog (documented, none urgent; none block)

Migrated from the `README.md` "TODO" list (its struck-through items already shipped).

- [x] ~~**Track user-triples vs rule-triples in the index.**~~
      CLOSED as outsourced-by-design 2026-07-17. Raw user tuples are stored exactly
      once — `TupleV1` + `TupleLogV1` are the source of truth; the set engine is
      in-memory and rebuilds from `TupleV1`. The graph index is a provenance-blind
      materialized view: its direct edges are its own materialization (post
      rule-routing), not a second tuple store. The correctness hazard the split would
      guard (a remove of a never-added tuple whose pure-union edge exists only via
      rule routing silently corrupting the mixed `direct_edge_count`) is already
      closed at the right layer: `TupleSource.remove` validates against stored tuples
      and raises before logging (`connectedstore/source.py`), and the
      log-replayability contract declares apply-time rejection a corruption signal,
      never an op rejection. The residual audit exists empirically:
      `formal/conformance/test_conformance_remove.py` pins driven graph state == a
      fresh add-only rebuild. Boolean relations' storage-leaf/routed-leaf split
      exists for TTU semantics, not provenance; the pure-union TTU analog was closed
      as unreachable 2026-07-13 (`_validate_ttu_tuplesets`). All that would remain is
      defense-in-depth for direct standalone `WildcardIndex` misuse — the same trust
      boundary every other invariant (I5, log replayability) already assumes. (The
      dead `legacy/index_v3.py` `user_edge_count` musing was the v3 gesture at this.)
- [x] ~~**Extend the hypothesis schema generator to emit star-bridge cycle shapes.**~~
      DONE 2026-07-16. Added a dedicated star-bridge generator + `StarBridgeParityMachine`
      to `tests/test_hypothesis.py` (emits `parent:[T,T:*]` / `A:[user,T:*#A,T#B]` /
      `B:[user] or A from parent`), a deterministic class pin, and the OUT-bridge analog
      of reg10 (`test_reg11...` in `tests/test_lookup_oracle.py`) — the object-wildcard
      mirror; verified only the single-hop out-bridge self-cycle is realizable (the
      multi-hop generalization is unreachable). See the dated `docs/spec-deviations.md`
      entry. The generator ALSO surfaced two new latent OWC divergences — see the
      Standing/latent section below.

### Someday / out of scope (low priority — revisit only on a concrete need)

- [ ] **Lift the two scope rejections** — object wildcards on derived relations,
      and wildcard usersets over derived relations, currently raise
      `UnsupportedByGraphIndex` (loud compile-error hooks); the documented fix is a
      symmetric subject-keyed residue (symbolic composition through residues), and
      it is the sole item not yet modeled in Lean (`formal/FINAL_REVIEW.md` §4 last
      item). **Low priority — the OpenFGA DSL does not support these either**
      (verified against the OpenFGA Configuration Language docs, 2026-07-16):
      OpenFGA rejects `<type>:*` in a tuple's object field and rejects wildcard
      usersets (`[group:*#member]`) with a validation error. The one plausible
      pattern (broad grant + per-object boolean exception) is already expressible
      via a supported TTU/hierarchy. So this is a deliberate boundary, not a gap —
      revisit only if a concrete, OpenFGA-shaped need appears.
- [ ] **A real service wrapper** — deliberately skipped; the store is a plain
      callable API.
- [ ] **Tuple-log compaction** — only if the log ever outgrows "humans wrote this" scale.
- [ ] **Bulk-merge write path (batch closure update seeded from EXISTING state).** The one
      high-value UNBUILT write optimization (never filed in the perf arc — it crosses the
      Lean/identity bar, so it isn't a micro-opt). Sits between the two shipped paths:
      incremental `advance_index` (per-edge `O(anc×desc)`, writes only the delta) and
      from-empty `bulk_build`/`bulk_backfill` (one topo+DP pass, 30–200×, but REFUSES a
      non-empty store). Goal: apply a large batch to an already-populated index by loading
      the affected region, recomputing the merged closure delta in memory (bulk-builder DP
      seeded with existing boundary path-counts), and writing back ONLY changed rows.
      **When it wins:** batch touches ~>2–3% of the closure (incremental's summed regions
      get expensive) but far less than the whole graph (a full rebuild wastefully rewrites
      the untouched majority). **Why it's hard / the crux:** a merge must reproduce, against
      PRE-EXISTING rows, all the coupled invariants the from-empty builders are add-only
      exempt from — `EdgeV4` direct/indirect counts (incl. boundary composition), the I5
      `derived` flag, `ResidueV1` stars/neg/upos+version, from-chain nodes, node
      `reference_count`/implicit GC (order-sensitive), sticky explicit-promotion — plus
      remove/GC/diff cases (`_gc_*` deletes) the mirrors never hit. **Reuse:** `bulk_build.py`
      Phases R/C/P/W + a `_BulkBackfill` recompute SCOPED to affected derived keys. **Gates:**
      changes a modeled algorithm → differential identity gate (mirror `tests/test_bulk_build.py`:
      bulk-merge == incremental `advance_index`, byte-identical mod row-ids), hypothesis
      campaign (esp. removes), a Lean twin + `CORRESPONDENCE.md §7/§8` entry (an "alternative
      constructor" like P13/R4-BF), full phased `verify.sh` + fuzz. **Phasing:** bench first
      (no large-batch-on-large-index bench exists today — build one, and confirm whether the
      cascade or the closure DP dominates), then add-only merge behind a distinct entry point,
      then removes. Watch the P12c fence (outbox/watermark/cascade coupling). A fuller
      design sketch was produced 2026-07-19 in a read-only session but not yet written to a
      `docs/` design doc — write it up (match `docs/architecture/p13-bulk-build-design.md`
      style) before implementing. Revisit only on a concrete large-batch ingest need.

### Standing / latent (non-blocking — no action needed unless a motivating case appears)

- [x] ~~**Set-engine flow graph omits bridge edges**~~ — RESOLVED 2026-07-16 (was a
      real, constructible divergence, not merely latent). Fixed; see the Current
      status note above and `docs/spec-deviations.md`.
- [x] ~~**Two OWC-on-self-referential-relation divergences (F1/F2, found 2026-07-16 by the
      new star-bridge fuzzer).**~~ — RESOLVED 2026-07-17 by a **compile-time scope
      rejection** (the third decision-15 entry): a *doubly-bridged* shape — a literal
      `T:*#p` wildcard-userset restriction that is also an object-wildcard shape — now
      raises `DoublyBridgedShapeError` on **both** backends at construction (the set engine
      re-raises it rather than degrading). Also surfaced en route: both states **detonate**
      (after the wildcard write, innocent later concrete writes of the shape are permanently
      graph-rejected — a 3rd divergence), and *all→any is NOT read semantics* (oracle-pinned
      via an acyclic cross-type probe, so no read-path fix was warranted). Belt-and-braces
      set-engine ghost-hop safeguard added (never fires post-rejection). Pinned by the
      `reg12` block in `tests/test_lookup_oracle.py`; see the dated `docs/spec-deviations.md`
      entry. (Note: the criterion is the *literal-restriction* ∩ object-wildcard set, not
      the coarse `bridged_in ∩ bridged_out`, which over-rejects the legal reg11 class.)
- [x] ~~**THREE OPEN/latent divergences filed 2026-07-17 by the hardened generators**~~ —
      **RESOLVED 2026-07-17 (+ a 4th found en route).** All three were root-caused and fixed,
      their strict xfails flipped to plain regression pins, and the generator exclusions
      reverted (`allow_usersets` default ON, `ttu_in_boolean` removed). See the Current-status
      top bullet and `docs/spec-deviations.md` 2026-07-17 ("the three OPEN 2026-07-17
      divergences CLOSED"). Summary: #2/#3 (the graph *completeness* gaps —
      `test_graph_from_chain_userset_through_boolean_ttu_arm`,
      `test_graph_userset_subject_through_derived_wildcard_gap`) + a new 4th
      (`test_graph_userset_member_through_granted_userset_over_derived`) fixed by **Fix A**
      (the `processor._leaf_concretes` `upos` lift for `derived-computed`/`derived-userset`
      leaves + `bulk_backfill` mirror); #1 (the answer-benign implicit-flag canonical drift,
      `test_pderived_userset_self_ref_cascade_replay_drift`) fixed by **Fix B** (the
      state-functional `implicit` flag — promote step 2d + demote-on-release, I6 extended;
      hysteresis pin `test_pderived_recording_promote_demote_hysteresis`).
- [ ] **Other documented latent/theoretical notes** — a handful of
      "documented, no corpus exercises it, not urgent" corners. As of 2026-07-17 the
      inventory is: the from-chain TARGET theoretical note (unreachable by any
      compilable schema; fails LOUD via cascade quiescence if ever reached —
      2026-07-13 X4 entry) and the I7 checker corner (an in-place residue-version
      regression to exactly 1 is undetectable; checker sensitivity, not system
      correctness — P6 #1). The tupleset-of-derived latent gap formerly cited here
      was RESOLVED 2026-07-13 (P5 #3 resolution: unreachable, closed as benign).
      The full log: [`docs/spec-deviations.md`](docs/spec-deviations.md).
      Do not chase these speculatively; act only if a real schema/corpus surfaces one.

_(Declined / dead-end items — do NOT re-chase — are listed in
[`docs/perf-next-round.md`](docs/perf-next-round.md) "Minor notes" and the fenced
P12c list.)_

---

## Where things live

| doc | what it is |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | durable rules: env, the gate, layout/mental model, testing conventions, invariants |
| [`docs/architecture/overview.md`](docs/architecture/overview.md) | **architecture index** — module map + pointers to every deeper doc |
| [`docs/gate-runbook.md`](docs/gate-runbook.md) | how to run the full gate cap-safe (pytest split + phased `verify.sh` + fuzz) |
| [`docs/perf-next-round.md`](docs/perf-next-round.md) | perf standing guardrails (arc closed; fence + dead-ends + hygiene) |
| [`docs/spec-deviations.md`](docs/spec-deviations.md) | dated log of where the code diverges from the specs, and the latent-gap inventory |
| [`docs/specs/`](docs/specs/) | the full original design specs (cited by code comments as "spec §N") |
| [`formal/HANDOFF.md`](formal/HANDOFF.md) | entry point for the Lean formal layer (read before touching `formal/`) |
| [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) | the model↔Python code map (§7/§8 record any algorithm drift) |
| [`benchmarks/results/PERF_ANALYSIS.md`](benchmarks/results/PERF_ANALYSIS.md) | measured perf numbers per landed item ("Applied") |
| [`docs/history/`](docs/history/) | retired round records (perf rounds 3–5) — provenance, not living docs |

---

## Working rhythm

1. **Read this file + `CLAUDE.md` first.** Pull deeper docs on demand from the map above.
2. **Run the gate before pushing** — never push red or unverified. Cap-safe recipe
   in [`docs/gate-runbook.md`](docs/gate-runbook.md): `pytest tests/` (split) green,
   then `verify.sh lean` → `conf-heavy` → `conf-rest` all `PASSED`; an algorithm
   change also runs the multi-seed fuzz sweep. Commit and push **only when asked**.
3. **Keep the honesty norms** — report gate output as-is; if something is skipped
   or fails, say so. Never edit a golden/oracle/snapshot just to make a change pass.
4. **Keep this board current** — add active tasks when you start them, clear them
   when the work lands (the git log + `docs/history/` are the durable trail).
5. **Perf or algorithm work?** A behavior-preserving micro-opt needs no Lean change;
   an optimization that changes a *modeled* algorithm must update the matching Lean
   def and re-run `verify.sh`, or log the gap in `formal/CORRESPONDENCE.md §7`
   (see `CLAUDE.md` "Perf work & the Lean model").
