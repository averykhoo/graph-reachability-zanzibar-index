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

## Current status — 2026-08-05

**Everything is green and nothing is blocking.** The gate passes all ten phases; there
is no known live correctness bug, no `sorry`, and no `xfail` anywhere in the tree.

- **Last landed: E-chain Direct-arm widening, LEG 4 — the chain projection and the
  E-chain final, both `_d`** (2026-08-05). `reachedByW3d2E_toC_d` projects the
  fully-operational scheduler closure onto the coverage chain on the Direct-arm fragment;
  `graph_correct_w3d2E_d` composes it for `check = sem`. Both compiled first try, and the
  audited `reachedByW3d2E_toC` / `graph_correct_w3d2E` are now **byte-identical wrappers**
  over them (verified against HEAD). Audits 467 → 471, **definition pin UNMOVED at
  142/142**, statements 26/26. Lean-model + docs only — **no Python file changed**, so no
  fuzz sweep was owed. Two non-vacuity instruments land with it
  (`W4WitnessDirect.toC_applies` / `w3d2E_correct_applies`), the second a **weaker
  statement but a stronger instrument** than the existing `correct_applies` (see the board
  item — the obvious summary is backwards). Sabotage-controlled — and the *control
  itself* needed a correction first, which is the leg's most transferable finding (see the
  board item). Detail: `formal/history/PROOF_STATUS.md` 2026-08-05b. **Next: leg 5**, the
  claim-changing one (its own session).
- **Previously landed: LEG 3 — the coverage packaging** (2026-08-05).
  `w3dJobCoverage_enumJob2D_state`, purely additive (audits 465 → 467, pins unmoved), plus
  **`W4WitnessDirect.coverage_applies`** — the leg's real finding being about the plan's
  *gate*, not the proof: a packaging clone is the one shape a green build cannot vet
  (unsatisfiable premises compile, audit clean and pass every pin).
- **Leg 2 (`e76b66c`) is now PUSHED**, together with its board refresh — it had been
  sitting committed-but-unpushed since 2026-08-04.
- **Previously landed: the P3 edge-multiplicity blind spot, ADJUDICATED and closed** — the
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

- [ ] **★ START HERE (next session, refreshed 2026-08-05b) — ONE live option left: (B),
      now at E-chain leg 5.** The zero-trust backlog is CLEARED, the gate is green
      end-to-end, and as of 2026-07-29 there is **no longer an open item where the gate is
      blind to a class of divergence** — the P3 edge-multiplicity hole was the last one and
      it is closed. **Legs 2, 3 and 4 have landed; leg 5 wants its own session, and it is
      the first leg in this arc that CHANGES A HEADLINE CLAIM** (statement-pin regen).
      * **~~(A) the store-level write quota~~ — DECLINED by the user 2026-07-29**, and
        the alternative was measured rather than assumed. *"I don't want to limit what
        can be added to a permission store — it might be slow but it should not be
        limited by perf."* The proposed substitute (detect a DoS fan-out, bulk-rebuild
        instead of adding normally) was **measured and does not work**: bulk is 7–15×
        faster to BUILD but produces byte-identical closure rows (so it fixes nothing
        about size), makes the worst single lock stall 25–43× WORSE (105 ms → 2.7 s at
        N=480; 237 ms → 10.1 s at N=960), cannot be triggered (the only fan-out signal
        is the per-write region, measured at 120 — the signal already known not to
        fire), is structurally refused mid-stream by `build_index`, and **loses every
        REMOVED outbox row** (measured 143 ADDED/42 REMOVED incrementally vs 101/0 on a
        rebuild) — which §8.3's verifier is blind to. **The answer that already exists
        is `ConnectedStore(sync=False)`:** measured 14.5× lower write latency
        (2.7 ms/write vs 105 ms max), closure work off the write path, writers and
        catch-up on different lock rows, and a consistency contract that is already
        built and pinned. It bounds *whose latency pays*, not what can be stored.
        Full measurement + the two further options (rebuild-vs-K-deltas amortisation,
        crossover K* ≈ 30–40; and routing hub workloads to the set engine, 0.03 s vs
        74 s at N=960): `docs/spec-deviations.md` 2026-07-29c.
      * **(B) E-chain Leg 5** — the arc's next step, and the first that changes a headline
        claim rather than adding beside it. **Legs 2, 3 and 4 LANDED** (2026-08-04 /
        2026-08-05 / 2026-08-05); see the Leg-2/3/4 blocks below. Two of the plan's
        predictions have been refuted by measurement, one gate specification was found
        insufficient **twice**, and its obligation inventory was found to miss a
        hypothesis — read §C.1/§C.2/§C.3/§C.4 before following any cell of it.

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

      **(B) The E-chain Direct-arm widening — legs 0/1/2/3/4 DONE; LEGS 5–6 REMAIN, and
      leg 7 (T2a) is blocked on a design decision, not on proof effort.** The claim is
      unchanged: `ZT-P3-1` — the headline graph theorems are
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
      * ~~**`enum2BaseD` must dedupe** or the widened model's edge multiset grows `n ↦ 2n+1`
        per cascade leg.~~ **The GROWTH claim was right; the REMEDY was wrong** — see the
        leg-2 bullet below. Closed by a presence diff, not by `.dedup`.
      * **The step-2 star-freeness question is DECIDED** (new `W4Fragment` clause
        `directArmsConcrete` + a faithfulness star-filter; a star-filter alone leaves half
        the hole open). It excludes a shape Python admits ⇒ declared scope carry.
      * **Leg 1 LANDED 2026-07-28** (audit 457 → 460; definition pin UNMOVED at 139/139, which
        confirms the assessed risk profile). `DirectArmsConcrete` + the faithfulness
        star-filter + `reachedByW3d2_Rnode_source_name_ne_star_d` + the D.5 free win. The new
        fragment clause is **machine-confirmed load-bearing**, not defensive: a 262-run sweep
        over every chain state found 0 STAR-sourced in-edges at derived R-nodes out of 824;
        drop the clause and 122 stores produce one.
      * **Leg 2 LANDED 2026-08-04 — the enumeration model change.** `enumJobs2At` takes the
        `Store` and enumerates `enumJob2D`; audits 460 → **465**; **headline STATEMENTS
        26/26 byte-identical while the DEFINITION pin moved 139 → 142** — the
        statement-stable/meaning-changed asymmetry gate 4c exists for. The leg lands with
        none of the `_d` chain because `enumJob2D_eq_enumJob2` makes the change an identity
        on the `ComputedOnly` scope, which is all `reachedByW3d2E_toC` is stated over.
      * **★ Two of the plan's instructions were WRONG, and both were caught by measuring
        rather than following them** (`formal/history/echain-widening-plan-2026-07-28.md`
        §C.2 records both):
        1. **"`enum2BaseD`'s `.dedup` goes first or the leg is unrunnable"** — the `.dedup`
           does not fix D.1. Reproducing D.1 first showed the duplicate is between
           `storedDirectSubjects` and `edgeHolders`, with `enum2BaseD` a one-element list
           on which `.dedup` is a no-op. What landed is `freshDirectCands`, a presence diff
           on the Direct-arm contribution to `cands` only.
        2. **"Leg 2 is expected to break `test_derived_arm_multiplicity_ledger`"** — it does
           not. All 48 state-conformance tests pass and **no golden was regenerated.** That
           green was controlled, not trusted: defeating the presence diff moves exactly one
           corpus, `[direct_arm_exclusion] golden=[16, 1] observed=[31, 1]`, so the gate
           does see the leg. ⚠ But the tree still COMPILES with the filter defeated — the
           presence diff is pinned by the ledger, not the type checker.
      * **Leg 3 LANDED 2026-08-05 — the coverage packaging, and a gate-design finding.**
        `w3dJobCoverage_enumJob2D_state` (`CascadeStrataEnum.lean:981`) is the `_d` twin of
        `w3dJobCoverage_enumJob2_state`: over any `ReachedByW3d2` state on the Direct-arm
        fragment, `enumJob2D`'s coverage holds. It compiled first try; audits 465 → **467**;
        **definition pin UNMOVED at 142/142, statements 26/26** — the additive profile the
        plan predicted, which is the signal to check on an additive leg. The `_filt`
        distinction held exactly as §A.3 warned: `reachedByW3d2_shadow_d`'s σ0 is over the
        FILTERED store, so the consumer must be `w3d2_leg_context_d_filt`; the extra
        `hCOop` rode along as instructed.
      * **★ The plan's leg-3 GATE was insufficient, and this generalises to legs 4–6**
        (§C.3). The cell said "`lean` + audit pin" — a clone and no instrument. But a
        packaging clone is *nothing but* a chain of `_d`/`_filt` forms, and if that chain's
        hypotheses are jointly unsatisfiable it compiles, audits with standard axioms only,
        and passes every pin in the gate. That is not hypothetical: it is the 2026-07-20b
        kill, which §A.3 warns about two paragraphs above the sentence specifying the gate.
        So the leg also lands **`W4WitnessDirect.coverage_applies`** (`FullScope.lean:785`),
        instantiating the theorem at the real compiled Direct-arm pair `(Sd, Td)` — and it
        assumes *less* than the existing `correct_applies` does (`hsettledOps` is discharged
        vacuously). It is contentful, not decorative: `outside_old_admission` machine-checks
        `StoreValidRules Sd Td` FALSE, so the untainted twin cannot be instantiated there
        and the `_d` twin can. **Controlled:** adding one unused premise
        `(_hSABOTAGE : StoreValidRules S T)` leaves `CascadeStrataEnum` GREEN ("Build
        completed successfully (1061 jobs)") and turns only `FullScope` RED. ⚠ **Legs 4 and
        5 are much bigger `_d` packagings — budget a witness for each, not just a clone.**
      * **Leg 4 LANDED 2026-08-05 — the chain projection and the E-chain final.**
        `reachedByW3d2E_toC_d` + `graph_correct_w3d2E_d` (`CascadeStrataAssemble.lean`),
        both compiled first try; the audited originals are now **byte-identical wrappers**
        over them. Audits 467 → **471**, definition pin UNMOVED at 142/142, statements
        26/26. The leg in one line: the two `enumJob2D_eq_enumJob2` rewrites leg 2
        installed come OUT, so `enumJob2D`'s extra candidates are covered on their own
        terms instead of collapsed back onto `enumJob2`.
      * **★ Leg 4's three findings, all in the plan's §C.4.** (i) **The plan's obligation
        inventory (§A.3) misses `DirectArmsConcrete`** — it walks the COVERAGE half, and
        the clause arrives through the VALIDITY half (`enumJobs2At_valid` →
        `reachedByW3d2_Rnode_source_name_ne_star_d`). When scoping legs 5–6, walk every
        half, not the headline lemma. (ii) **The leg came out SMALLER, not bigger**: the
        `remove` case needs no widening at all, and the `_d` source lemmas take
        `isDerived` alone where their untainted twins take `hlk'` + `ComputedOnly e'`, so
        three declaration-lookup blocks vanish. (iii) **The leg-4 gate cell repeated
        §C.3's mistake verbatim** ("`lean` + audit pin"), one leg after §C.3 was written
        into the same document telling it not to. **Leg 5's cell has the same defect.**
      * **★ AND THE INSTRUMENT ITSELF NEEDED CONTROLLING — the most transferable finding
        of the leg.** The first sabotage put the false premise before `h` and left it in
        scope; `induction h` generalised it into the motive, `ih` acquired it, and the
        module went red — for a reason that had **nothing to do with the premise being
        false.** That is a sabotage that "works" for the wrong reason and would have been
        written up as a successful control. `clear _hSABOTAGE` is what makes it honest.
        This is `docs/sabotage-procedure.md`'s "control your instrument as well as your
        subject" firing for the second time in this arc. The real control:
        `CascadeStrataAssemble` GREEN (1062 jobs) with both cores sabotaged, `FullScope`
        RED at both new witnesses. The stronger of the two,
        **`w3d2E_correct_applies`, is a WEAKER STATEMENT but a STRONGER INSTRUMENT** —
        stating it the other way round (as a first draft of this board entry did) is
        simply wrong: `ReachedByW3d2E` projects INTO `ReachedByW3d2C`, so it assumes
        more, and it follows from `correct_applies` ∘ `toC_applies`. What it adds is
        coverage of the leg-4 bundle, `DirectArmsConcrete` included.
      * The standing warning still holds for the SEPARATE, still-open item it was about
        (`formal/CORRESPONDENCE.md` §7.2 item 6 — the baseline `n ↦ 2n` derived-arm
        stacking): do **not** discharge it by making `admitEdge` reject an already-present
        edge, which breaks the untainted arm (`nary_union` 3 → 1); the faithful fix is a
        `¬ hasEdge` conjunct in `reconcileKeyDR`'s fold guard. Leg 2 did not touch it.

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
- [ ] **`_any_residue_reference` / `_keys_referencing` — MEASURED 2026-07-29; the fix
      is not done.** The complete `ResidueV1` scan on every node-release path is
      cleanly **O(R) at ~15 µs per residue row** (0.35 ms at 25 rows → 22 ms at 1600;
      x1.98 per doubling). It is a minority term below ~1–2k residue rows and the
      DOMINANT term above; extrapolated, 100k residue-bearing keys cost **~1.4 s per
      node release**, and a churn past the crossover goes quadratic. **Scope:** R is
      the number of `(object, derived relation)` pairs with a WILDCARD grant, not
      tuples — stores with no boolean relations pay nothing.
      **Remaining work** is the fix `ZT-P0-1`'s own note named: replace the scan with
      a node-id-keyed reference index maintained alongside `neg`/`upos`. That is an
      algorithm change (full gate + multi-seed fuzz + a Lean/CORRESPONDENCE look), so
      it was deliberately not smuggled into a measurement pass.
      Numbers + the instrument trap: `docs/spec-deviations.md` 2026-07-29b.
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
      * the **from-chain TARGET** note — **RE-DERIVED 2026-07-27, and its reachability
        half is DISPROVED.** (`ZT-P5` bullet 5 said it had "never been re-derived", and
        the 2026-07-29 board refresh repeated that; both were stale — the work was done
        on 2026-07-27 and is executable, not asserted.) The 2026-07-13 claim "no
        currently-compilable schema class reaches this shape" is FALSE: `_from_chain_keys`
        enumerates ALL stored parents, so a parent of a different type with an UNTAINTED
        `target_rel` yields exactly the excluded shape. Pinned by
        `tests/test_zt_p5_readjudication.py::test_zt_p5_from_chain_target_shape_IS_reachable`.
        **The other half survived:** 400 randomized trials (88 of which reached a fresh
        untainted+bridged from-chain intern) gave 0 admission divergences, 0 answer
        divergences, 0 invariant violations, 0 `audit_fixpoint` failures, on 3 seeds.
        **What is genuinely still open is narrower than "the note":** the structural
        reason offered for the clean result is explicitly *a hypothesis, not a proof*,
        it is **not established for intersection-rooted grant relations**, and **no
        bounded search was run over >2 strata**. Those two are the live residue.
        Detail: `docs/spec-deviations.md` "Target 2".
      * the **I7 checker corner** — an in-place residue-version regression to exactly 1
        is undetectable. Note this is now known to be worse than "checker sensitivity":
        `ZT-P4-5` established that **I7 is gated by nothing formal at all** (Lean's
        `Residue` has no version field — projection **P7**), so the Python paranoia
        checker is its only pin. See `formal/CORRESPONDENCE.md` §7.2.
      * **`_any_residue_reference`'s full `ResidueV1` scan** (`ZT-P5` bullet 6) is
        unbenchmarked and became UNCONDITIONAL after the `ZT-P0-1` fix. The only
        item here with a measurable cost.
      * **Object wildcards at STATE level** (`ZT-P5` bullet 2) — **half done.** The
        PYTHON side was probed clean on 2026-07-27 (a deterministic ~72-state slice is
        pinned by
        `tests/test_zt_p5_readjudication.py::test_zt_p5_bounded_search_object_wildcard_out_bridge_no_further_divergence`,
        plus a 344-trial exclusion sweep with zero divergences). **The LEAN side is
        still UNVERIFIED** — `docs/spec-deviations.md` "Target 3" says so in as many
        words. So the "fragment exclusions are proof-scope, not observed divergence"
        inference still rests on check-level evidence for the model corner, which is
        the exact inference class that failed at state level on 2026-07-17.
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
