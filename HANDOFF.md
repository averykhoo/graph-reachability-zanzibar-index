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

## Current status — 2026-07-29

**Everything is green and nothing is blocking.** The gate passes all ten phases; there
is no known live correctness bug, no `sorry`, and no `xfail` anywhere in the tree.

- **Last landed: the P3 edge-multiplicity blind spot, ADJUDICATED and closed** — the
  last open item where the gate was blind to a whole class of divergence. Verdict:
  real, model-side, confined exactly to the DERIVED arm (Python's presence diff caps
  `direct_edge_count` at 1 there; the model compounds to 1013), removal-inert. P3 is
  narrowed so untainted-arm multiplicity is now compared EXACTLY — 153 edges that
  nothing had ever compared — and the derived arm is golden-pinned. Detail:
  `formal/CORRESPONDENCE.md` §7.2, `docs/spec-deviations.md` 2026-07-29.
- **Also landed 2026-07-29: the counts pin.** `ZT-P3-5` ("every doc number is stale and
  nothing enforces any of them") had been hand-fixed twice and rotted a third time, so
  `formal/FINAL_REVIEW.md`'s headline counts are now GENERATED
  (`formal/conformance/doc_counts.py`) and checked by `verify.sh` step 4e.
- **Live gate figures live in ONE place** — the generated counts block in
  `formal/FINAL_REVIEW.md`. Do not restate them here; this file went stale three times
  doing exactly that.
- **Doc sweep 2026-07-29.** ~60 stale figures corrected across the claim docs, and two
  CLAIM errors that were not just stale: (i) "six documented projections / P1–P6" in
  nine places — the state gate has had **seven** since P7 was declared, and saying six
  *understates what the gate discards*; (ii) `ARCHITECTURE.md` and `SEMANTICS.md` both
  carried a present-tense "what the gate does NOT do" paragraph (no audit floor, no
  conformance floor, no xfail parsing) that has been false since 2026-07-26/27 — it
  understated assurance, but a reader would have concluded the gate was gutted. The P2
  bridge-inertness claim was **re-measured, not bumped**: 477 raw rows over all 23
  corpora, still 0 dropped, `bridged_*_shapes` empty on every one.

**History moved out 2026-07-29:** the dated status run, the full zero-trust review, and
every completed board item are now in
[`docs/history/handoff-status-2026-07.md`](docs/history/handoff-status-2026-07.md),
together with the reconciled **`ZT-*` disposition ledger** (which fixes three ids that
had no disposition anywhere and one that was listed CLOSED while its substance was
open). This file is now only what a future session must ACT on.

---

## Open-TODO board

### Active work

- [ ] **★ START HERE (next session, refreshed 2026-07-29) — two live options; the third
      is done.** The zero-trust backlog is CLEARED, the gate is green end-to-end, and as
      of 2026-07-29 there is **no longer an open item where the gate is blind to a class
      of divergence** — the P3 edge-multiplicity hole was the last one and it is closed
      (top status section). So the remaining choice is a genuine priority call, not a
      "fix the blind spot first":
      * **(A) the store-level write quota** — the only item with real production value.
      * **(B) E-chain Leg 2** — the enumeration model change. **Read the plan's §D.6 row
        before starting:** it is now mechanical, and the leg is *expected* to break
        `test_derived_arm_multiplicity_ledger`.
      Pick one and finish it rather than sampling both. Full context for each is linked.

      **(A) The store-level write quota — the only one with real production value.**
      `ZT-P1-6a` is only half closed. `ZANZIBAR_MAX_CLOSURE_FANOUT` (landed 2026-07-27,
      `index_v4/core.py`) bounds what ONE add may materialise while holding both
      per-store locks. It does **not** stop the DoS that motivated it: re-measured, the
      240-tuple hub topology produces 14,640 closure rows but its peak *per-write*
      fan-out is only **120** — it is 240 cheap writes, not one expensive one. What is
      missing is a quota over a STORE (rows, or tuples, or closure size), which is a
      different mechanism with genuinely different design questions: what is the unit,
      who resets it, and — the hard one — **what happens to an already-over-quota
      store**, since a quota that blocks removes is a fail-open (the fan-out cap
      exempts removals for exactly this reason; read that comment first). Python-side,
      bounded, no Lean impact. **Start:** the residuals block on the 2026-07-27 board
      item below, then `index_v4/core.py`'s `DEFAULT_MAX_CLOSURE_FANOUT` comment.

      **(B) The E-chain Direct-arm widening — SCOPED + Leg 0 DONE 2026-07-28; legs 1–6
      remain.** The claim is unchanged: `ZT-P3-1` — the headline graph theorems are
      **VACUOUS** on `can_view: [user] but not blocked`, the most common Zanzibar boolean
      shape (`FullScope.lean:564` machine-checks that such a store fails
      `GraphAdmission.storeValid`), so `graph_correct` / `graph_reached_inv` /
      `Exec.graphRun_check_eq_sem` hold trivially there — **no theorem, not a narrow one**.
      Still NOT the ≥3-strata arc (declined 2026-07-27; coverage, not safety, and the model
      already fails CLOSED there).
      **★ START HERE NOW: `formal/history/echain-widening-plan-2026-07-28.md`** — the
      durable 7-leg plan. It **supersedes** the 4-step fork list in
      `optional-widening-2026-07.md` in five places, and the attack sweep (Leg 0) is
      already done: 5 probes, **2 KILLS**, no Lean declaration changed. What that bought:
      * **T2a `graph_reached_inv` is OUT of the arc.** `Inv.negEdgeFree` is
        machine-checked FALSE on the `_d` fragment. **A modelling limit of the P6
        leaf-family collapse, not a Python bug** (verified on the real backends — Python
        routes the write onto the leaf family, so its `neg` row and the edge live on
        different nodes). T2b is unaffected. A **design decision** is owed before any T2a
        work — do not schedule proof effort for it. Expected honest end state of the arc:
        **T2b widened, T2a explicitly not.**
      * **`enum2BaseD` must dedupe** or the widened model's edge multiset grows `n ↦ 2n+1`
        per cascade leg.
      * **The step-2 star-freeness question is DECIDED** (new `W4Fragment` clause
        `directArmsConcrete` + a faithfulness star-filter; a star-filter alone leaves half
        the hole open). It excludes a shape Python admits ⇒ declared scope carry.
      * **Leg 1 LANDED 2026-07-28** (audit 457 → 460; definition pin UNMOVED at 139/139, which
        confirms the assessed risk profile). `DirectArmsConcrete` + the faithfulness
        star-filter + `reachedByW3d2_Rnode_source_name_ne_star_d` + the D.5 free win. The new
        fragment clause is **machine-confirmed load-bearing**, not defensive: a 262-run sweep
        over every chain state found 0 STAR-sourced in-edges at derived R-nodes out of 824;
        drop the clause and 122 stores produce one.
      * **Next concrete step: Leg 2** — the enumeration model change. **`enum2BaseD`'s `.dedup`
        goes first** or the leg is unrunnable. This is the first leg that moves the definition
        pin (6 rows changed, 3 added), so its golden regen gets its own commit.
      * **The P3 multiplicity finding this arc surfaced is ADJUDICATED + CLOSED**
        (2026-07-29). Consequence for Leg 2, and the reason it is mentioned here at
        all: **the plan's §D.6 hand-probe is now MECHANICAL.** Leg 2 will fail
        `test_derived_arm_multiplicity_ledger` by construction — read the printed
        `golden=[lean, python] observed=[…]` table, confirm the movement is the
        `enum2BaseD` dedup you intended, then regenerate with
        `ZANZIBAR_UPDATE_SNAPSHOTS=1` in its own commit alongside the definition-pin
        regen. ⚠ Do **not** discharge the dedup obligation by making `admitEdge` reject
        an already-present edge — that breaks the untainted arm, which is load-bearing
        (`untOccCount`, erase-one removal) and is now compared exactly, so it goes red
        on `nary_union` (3 → 1). Mirror Python's presence diff inside `reconcileKeyDR`'s
        fold guard instead. Detail: `formal/CORRESPONDENCE.md` §7.2.

      **Before starting any of them:** `bash formal/verify.sh lean` should be green in
      ~30 s warm. If it is not, fix that first — it is the fastest signal in the repo.
- [ ] **Follow-ups left from the assurance-widening arc (opened 2026-07-18).** The arc
      itself is archived — legs #1(1–3), #3 and #4(R1–R5b) all landed, and its two
      "next" pointers are dead (#2 strata >2 was scoped and DECLINED 2026-07-27; #1
      Direct-arm is now the E-chain arc, whose plan supersedes the old fork list).
      What genuinely survives is three small items, none blocking:
      1. **`FINAL_REVIEW.md` §4(d) scope wording under-claims** (stale-conservative
         after the remove leg closed). Plausibly subsumed by the `ZT-P3-4`/`ZT-P3-5`
         sweeps — never confirmed either way.
      2. **Exec-driver remove hardening** — largely done 2026-07-19g (`graphRunOps`,
         `removeGateB`, the zcli `"ops"` stream, `test_conformance_remove_graph.py`),
         but with one live exclusion: `_REMOVE_EXCLUDED = {"direct_arm_exclusion"}`,
         because the remove guard is stated over plain `StoreValidRules` under which a
         Direct-arm-under-exclusion tuple is inadmissible. So "removes are driven
         end-to-end" holds for every in-fragment corpus except the newest. Lifting it
         needs the guard widened to `StoreValidRulesD` — i.e. it rides E-chain Leg 5.
      3. **The guard design decision** (validly-stored + drained-prior scope) was
         APPROVED 2026-07-19; no longer open. Recorded here only so the pointer in
         `formal/HANDOFF.md` is not read as a pending item.
      Resume detail: `formal/history/optional-widening-2026-07.md`,
      `formal/history/PROOF_STATUS.md` 2026-07-19f.
- [ ] **`_any_residue_reference` is unbenchmarked** (`ZT-P5` bullet 6) — its complete
      `ResidueV1` scan runs on every node-release path and became UNCONDITIONAL when
      the `ZT-P0-1` whitelist was withdrawn. No measurement exists. Carried here
      because it was previously reachable only from inside a `[x]` item's residual
      list, which is how an open item disappears.
### Someday / out of scope (low priority — revisit only on a concrete need)

- [ ] **Lift the two scope rejections** — object wildcards on derived relations, and
      wildcard usersets over derived relations, currently raise
      `UnsupportedByGraphIndex` (loud compile-error hooks); the documented fix is a
      symmetric subject-keyed residue (symbolic composition through residues), and it
      is the sole item not yet modeled in Lean (`formal/FINAL_REVIEW.md` §4 last item).
      **Priority argument CORRECTED 2026-07-29.** This item used to read "Low priority —
      the OpenFGA DSL does not support these either". `ZT-P5` bullet 1 declared that
      argument **INVALID** and it was never applied back here: this repo already ships
      object wildcards as a deliberate extension BEYOND OpenFGA (they have no DSL
      syntax and are passed via `object_wildcard_shapes`), so "OpenFGA doesn't have it"
      cannot justify deprioritising a construct the repo itself invented. The honest
      remaining argument is narrower and still holds: no concrete need has appeared,
      the rejection is LOUD (compile-time, not a silent wrong answer), and the one
      plausible pattern (broad grant + per-object boolean exception) is expressible via
      a supported TTU/hierarchy. Revisit on a concrete need — not on the old reasoning.
      **Scope note (2026-07-28):** wildcard usersets over an UNTAINTED relation are
      fully supported and now have corpora; only the DERIVED case is rejected.
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

- [x] ~~**`TupleSource.__init__` is not atomic on PostgreSQL**~~ — **CLOSED; this entry
      was STALE and said so in a way that mattered.** It claimed "the single remaining
      strict xfail in the tree … declared in `verify.sh`'s `MAX_TESTS_XFAILED=1`".
      Verified 2026-07-29 against the code: `verify.sh` carries
      **`MAX_TESTS_XFAILED=0`**, `tests/test_postgres_ha.py` records that
      `test_open_instance_races_a_concurrent_commit` **became a plain pin** when
      `TupleSource._consistent_rebuild` landed, and that helper
      (`connectedstore/source.py`) is used by BOTH `__init__` and `refresh_evaluator` —
      the two sites the finding named. Nothing in the tree is xfailed. Kept visible
      rather than deleted because for two days this was the one entry that would have
      made a reader believe a live authorization-adjacent bug was open.
- [ ] **Other documented latent/theoretical notes** — "documented, no corpus exercises
      it, not urgent" corners. **Inventory refreshed 2026-07-29:**
      * the **from-chain TARGET** note — was asserted 2026-07-13 to be "unreachable by
        any compilable schema, and fails LOUD via cascade quiescence if reached".
        `ZT-P5` bullet 5 flagged that this was **never re-derived** across three later
        fragment widenings, and it still has not been. Treat the reachability half as
        UNVERIFIED; the fails-loud half is the reason it is not urgent.
      * the **I7 checker corner** — an in-place residue-version regression to exactly 1
        is undetectable. Note this is now known to be worse than "checker sensitivity":
        `ZT-P4-5` established that **I7 is gated by nothing formal at all** (Lean's
        `Residue` has no version field — projection **P7**), so the Python paranoia
        checker is its only pin. See `formal/CORRESPONDENCE.md` §7.2.
      * **`_any_residue_reference`'s full `ResidueV1` scan** (`ZT-P5` bullet 6) is
        unbenchmarked and became UNCONDITIONAL after the `ZT-P0-1` fix. The only
        item here with a measurable cost.
      * **Object wildcards have never been probed at STATE level** (`ZT-P5` bullet 2).
        The "exclusions are proof-scope, not behavioral" inference rests on
        check-level evidence — the exact inference class that failed at state level on
        2026-07-17.
      The tupleset-of-derived gap formerly listed here was RESOLVED 2026-07-13.
      Full log: [`docs/spec-deviations.md`](docs/spec-deviations.md).
      Do not chase speculatively; act if a real schema or corpus surfaces one.

## Where things live

| doc | what it is |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | durable rules: env, the gate, layout/mental model, testing conventions, invariants |
| [`docs/architecture/overview.md`](docs/architecture/overview.md) | **architecture index** — module map + pointers to every deeper doc |
| [`docs/gate-runbook.md`](docs/gate-runbook.md) | how to run the full gate cap-safe (phased `verify.sh`, incl. `tests/`, + the Postgres leg + fuzz), and every floor/budget it enforces |
| [`scripts/pg_local.sh`](scripts/pg_local.sh) | throwaway user-space PostgreSQL for the server leg (`start`/`stop`/`status`/`destroy`) — no system install |
| [`tests/dbengine.py`](tests/dbengine.py) | the SQLite-vs-server engine seam (`ZANZIBAR_TEST_DSN` / `ZANZIBAR_PG_REQUIRED`) |
| [`docs/perf-next-round.md`](docs/perf-next-round.md) | perf standing guardrails (arc closed; fence + dead-ends + hygiene) |
| [`docs/spec-deviations.md`](docs/spec-deviations.md) | dated log of where the code diverges from the specs, and the latent-gap inventory |
| [`docs/specs/`](docs/specs/) | the full original design specs (cited by code comments as "spec §N") |
| [`formal/HANDOFF.md`](formal/HANDOFF.md) | entry point for the Lean formal layer (read before touching `formal/`) |
| [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) | the model↔Python code map (§7/§8 record any algorithm drift) |
| [`benchmarks/results/PERF_ANALYSIS.md`](benchmarks/results/PERF_ANALYSIS.md) | measured perf numbers per landed item ("Applied") |
| [`docs/history/`](docs/history/) | retired records — perf rounds 3–5 and the HANDOFF status archive; provenance, not living docs |
| [`docs/history/handoff-status-2026-07.md`](docs/history/handoff-status-2026-07.md) | this file's retired dated status run, the full zero-trust review, every completed board item, and the reconciled **`ZT-*` disposition ledger** |
| [`formal/FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) | the governing claim doc — and the ONLY place live counts belong (generated block, gated by `verify.sh` step 4e) |

---

## Working rhythm

1. **Read this file + `CLAUDE.md` first.** Pull deeper docs on demand from the map above.
2. **Run the gate before pushing** — never push red or unverified. Cap-safe recipe
   in [`docs/gate-runbook.md`](docs/gate-runbook.md): `verify.sh lean` →
   `conf-tile:1/5`…`5/5` → `tests-tile:1/4`…`4/4`, all `PASSED`; an algorithm change
   also runs the multi-seed fuzz sweep (`--hypothesis-seed=N`, **not**
   `HYPOTHESIS_SEED=N`, which hypothesis does not read — `tests/conftest.py` now
   refuses it). `tests/` runs THROUGH `verify.sh` since 2026-07-27; a bare
   `pytest tests/` is for iterating, not for gating. Anything touching locking,
   watermarks, isolation or multi-instance state should also run the PostgreSQL leg
   (`bash scripts/pg_local.sh start`, then `ZANZIBAR_TEST_DSN=…`). **The local
   cluster is STOPPED but RETAINED** — `start` brings it back in seconds, `destroy`
   removes it entirely; nothing in the default gate needs it.
   Commit and push **only when asked**.
3. **Keep the honesty norms** — report gate output as-is; if something is skipped
   or fails, say so. Never edit a golden/oracle/snapshot just to make a change pass.
   Corollary learned 2026-07-27: **an assurance step that fails by PASSING is the
   house failure mode** — a skip, an xfail, a zero-length loop, a count that cannot
   go down, a green run of a seed that never varied. When you add a check, sabotage
   the thing it guards and watch it go red before you believe it.
3b. **Do not restate gate counts in prose.** They live in `formal/FINAL_REVIEW.md`'s
   generated block and are machine-checked (`verify.sh` step 4e); regenerate with
   `python -m formal.conformance.doc_counts --generate`. This file went stale three
   separate times by keeping its own copies (`ZT-P3-5`).
4. **Keep this board current** — add active tasks when you start them, clear them
   when the work lands (the git log + `docs/history/` are the durable trail).
5. **Perf or algorithm work?** A behavior-preserving micro-opt needs no Lean change;
   an optimization that changes a *modeled* algorithm must update the matching Lean
   def and re-run `verify.sh`, or log the gap in `formal/CORRESPONDENCE.md §7`
   (see `CLAUDE.md` "Perf work & the Lean model").
