# HANDOFF status archive — 2026-07

**FROZEN 2026-07-29 — provenance, not a living document.** Status lines below are
as-of-then and several may now be false; live state: `HANDOFF.md` + the session
ledger. Corrections are appended dated at the top, never edited into the body.

**Provenance, not a living document.** This is the retired dated-status run and the
completed-work board from [`HANDOFF.md`](../../HANDOFF.md), moved here 2026-07-29 when
that file had grown to ~1,400 lines of which roughly 43% was closed content restated in
two or three places. `HANDOFF.md` keeps only what a future session must ACT on; this
file keeps the record of how it got there.

Same charter as the sibling perf-round records in this directory: read it for
provenance, never as a statement of current state. **Every count, gate figure and
"current" claim below is frozen at its own date.** The live figures are the generated
counts block in [`formal/FINAL_REVIEW.md`](../../formal/FINAL_REVIEW.md), which is
machine-checked by `verify.sh` step 4e — check there, not here.

Links in the moved text were written relative to the repo root; from this file they
resolve against `../../`.

---

## Corrections applied on archiving (2026-07-29)

Three bullets in the moved status text were not merely dated, they were **actively
false** by the time of archiving. They are retained for provenance with the correction
recorded here rather than silently deleted:

1. **"Everything green ... Lean is sorry-free and axiom-clean (412/412). Known
   correctness bugs: only the two strict-xfail graph completeness gaps filed
   2026-07-17"** (in the 2026-07-23 block). — The audit is **460**, and those two
   xfails were flipped to plain pins on 2026-07-17. There are **zero** xfails in the
   tree, and `verify.sh` carries `MAX_TESTS_XFAILED=0`.
2. **"Clean on `master`. Last change: the formal `rootB` fragment widening"** (same
   block). — Long superseded; `git log` is the authority.
3. **The 2026-07-26 executive-summary bullet** at the end of the 2026-07-23 block is a
   13-line precis of the full zero-trust section that immediately follows it, and was
   misfiled out of chronological order.

---

## ZT-* disposition ledger (reconciled 2026-07-29)

The zero-trust review filed findings under ids; their closures were recorded in several
places, three ids never got a disposition at all, and one was listed as flatly CLOSED
while its substance was the live rationale for an open board item. This is the
consolidated ledger, reconciled against the code on 2026-07-29.

| id | disposition | residual / note |
|---|---|---|
| `ZT-P0-1`, `ZT-P0-2` | CLOSED | whitelist withdrawn entirely; pin `tests/test_reg14_residue_gc_elision.py` |
| `ZT-P1-1`, `ZT-P1-2`, `ZT-P1-4`, `ZT-P1-5`, `ZT-P1-7` | CLOSED | — |
| `ZT-P1-3` | CLOSED **narrower than filed** | the filed fix said paranoia default **ON**; it landed default **OFF** (`ConnectedStore.DEFAULT_PARANOIA`). Deliberate, but the filed text still reads as if ON landed. |
| **`ZT-P1-6`** | **CLOSED — this disposition was MISSING from every board** | decision recorded in `docs/spec-deviations.md` ("fix the crash only, no admission caps"); the recursion half is implemented (`setengine/engine.py`, an explicit stack replacing the recursive `sat`) and pinned by `tests/test_zt_p1_hardening.py`. The board only ever tracked the derived id `ZT-P1-6a`. |
| `ZT-P1-6a` | CLOSED, self-declared **half** | the per-write fan-out cap landed; the **store-level quota did not**. Live owner: board item (A). |
| `ZT-P1-8` | CLOSED | filed as five points, four itemised. The fifth, `_fresh_enough(None) -> True`, is answered in `connectedstore/store.py` as the DESIGN (an untokened read asks for no freshness), not a fail-open default. **Id correction:** the board called the thread-scoping fix `ZT-P1-8c`; the code calls it **`ZT-P1-8e`** (`index_v4/core.py`, `index_v4/wildcard.py`, `tests/test_reg16_processor_writes_thread_scope.py`). The code's id is authoritative. |
| `ZT-P2-1` … `ZT-P2-6` | CLOSED | `ZT-P2-5` closed by the statement pin; `ZT-P2-6`'s "split conf-rest" worry is de-facto actioned — the gate runs five conf tiles. |
| **`ZT-P3-1`** | **CLOSED as FILED (doc fix, 2026-07-26); SUBSTANCE CLOSED for T2b, OPEN for T2a (2026-08-05)** | the filed *fix* was doc-only ("state it plainly in `FINAL_REVIEW.md` §3 and `ARCHITECTURE.md` §6") and that landed; listing it as flatly CLOSED at that point was misleading, which is why this row said so. **The underlying vacuity on `[user] but not blocked` was then actually fixed** by the E-chain Direct-arm widening arc, legs 0–6 (2026-07-28 → 2026-08-05): `graph_correct`, `backend_equivalence`, `exclusion_effective`, `no_ghost_grant` and `Exec.graphRun{,Ops}_check_eq_sem` now cover the shape, witnessed by `W4WitnessDirect.final_applies` / `final_applies4`. **⚠ `graph_reached_inv` (T2a) is NOT covered and is not going to be by more proof effort** — probe D.3 machine-checked `Inv.negEdgeFree` FALSE on the `_d` fragment (a P6 leaf-family MODELLING limit; Python is fine), so T2a carries an explicit `W4NarrowT2a` bundle with `outside_narrow_t2a` as its counterexample. What is owed is a design decision — live board item (B1) in the root `HANDOFF.md`. |
| `ZT-P3-2` … `ZT-P3-7` | CLOSED | `ZT-P3-5`'s own figures are stale — and **`ZT-P3-5` recurred twice more** (2026-07-28, 2026-07-29) before being closed mechanically by the counts pin (`formal/conformance/doc_counts.py`, `verify.sh` step 4e). |
| **`ZT-P4-1`** | **CLOSED (both halves)** | the board only ever asserted the anchor-checker half. The re-derivation half is done: `CORRESPONDENCE.md` was rebuilt onto `file::symbol` anchors, **397** of which resolve on every `lean` run. |
| `ZT-P4-2`, `ZT-P4-3`, `ZT-P4-7` | CLOSED | — |
| `ZT-P4-4` | CLOSED, split | arity closed; the strata premise was corrected (Python already reaches 3 — the ungated side is the LEAN model); ≥3-strata Lean coverage **DECLINED** by decision. |
| `ZT-P4-5` | CLOSED, residual declared | I7 is gated by nothing formal (projection **P7**) — a live modelling gap, restated in `CORRESPONDENCE.md` §7.2. |
| `ZT-P4-6` | CLOSED, residual declared | `encode.py` still reads through the oracle's parser; `grid.py` no longer does. |
| `ZT-P5-NEW` | CLOSED | write-time rejection, not compile-time; both xfails flipped to plain pins. |
| **`ZT-P5` bullet 1** (the "OpenFGA doesn't support it either" priority argument) | **declared INVALID; never applied back** | it was still in use verbatim by the "Lift the two scope rejections" board item until 2026-07-29. Corrected there. |
| **`ZT-P5` bullet 2** (fragment exclusions are proof-scope, not behavioral) | **HALF closed 2026-07-27** — corrected 2026-07-29 | `docs/spec-deviations.md` "Target 3": the PYTHON side was probed clean and pinned (`test_zt_p5_bounded_search_object_wildcard_out_bridge_no_further_divergence`); the **LEAN side is still UNVERIFIED** and says so. Not "no disposition" — a half-disposition that the board never picked up. |
| `ZT-P5` bullets 3, 4 | CLOSED | became `ZT-P5-NEW`; and the PostgreSQL leg closed the "validated where the bug cannot occur" objection. |
| **`ZT-P5` bullet 5** (from-chain TARGET reachability) | **CLOSED 2026-07-27 — the claim is DISPROVED** (corrected here 2026-07-29) | `docs/spec-deviations.md` "Target 2": the shape IS reachable, pinned executably by `test_zt_p5_from_chain_target_shape_IS_reachable`. The bullet's own "never re-derived" wording was true when filed and stale by the time this ledger first recorded it. The misbehaviour half survived 400 trials but is explicitly a hypothesis, not a proof — unestablished for intersection-rooted grant relations and unsearched above 2 strata. |
| `ZT-P5` bullet 6 | **OPEN** | `_any_residue_reference`'s full `ResidueV1` scan is unbenchmarked and is now unconditional after the `ZT-P0-1` fix. Carried on the live board. |
| `ZT-P5` bullet 7 | adjudicated, **not closed** | `formal/HANDOFF.md` records B1 (`w3cJobValid_enumJob2D` star-freeness) as "STILL OPEN, but RECLASSIFIED" — a design blocker folded into the E-chain plan. |
| `ZT-P5` bullet 8 | CLOSED | the three invariant lists reconciled. |

---

## The durable framing from the zero-trust review

Kept visible because it is the part that is still true, and it is a statement about the
tree rather than about a moment:

> The gate is green and the proof tree is genuinely sorry-free and axiom-clean
> (independently re-verified, not taken from docs). The Lean side has **no soundness
> holes** — no `sorry`, no custom axioms, no `native_decide`, no `unsafe` /
> `@[implemented_by]`, and the executed zcli calls the *proved* definitions directly,
> so there is no shadow implementation. What the review found instead is (a) one real
> code bug, (b) a security-hardening backlog in the operational envelope, (c) a gate
> that cannot detect its own erosion, and (d) claim documents that have drifted away
> from the tree they describe.

---

## Retired dated status sections

## Current status — 2026-07-29

- **2026-07-29 — the P3 edge-multiplicity blind spot is ADJUDICATED and the gate hole is
  CLOSED. No backend change; net-new assurance on 153 edges that nothing had ever
  compared.** This was the one open item where the gate could not see a class of
  divergence at all (`CORRESPONDENCE.md` §7.2, filed UNADJUDICATED 2026-07-28).
  * **Verdict: REAL, model-side, and confined EXACTLY to the derived arm.** Python's
    `DeltaProcessor._reconcile_subject` writes a derived edge by a presence DIFF
    (`want_edge and not has_edge`), so re-deriving is a total no-op and
    `direct_edge_count` on such a row is **always 0 or 1** — structurally, not by luck.
    The model has no presence test and compounds. Measured over all 23 `GRAPH_FRAGMENT`
    corpora: of 171 compared edges, **153 untainted-arm agree EXACTLY** (including
    `nary_union`'s genuinely non-unit 3-arm fan-in, 3 == 3) and **18 derived-arm all
    diverge** — Python uniformly 1, Lean 4 … **1013**. Zero set-level asymmetry, so the
    pre-existing gate was honestly green.
  * **Two corrections to the finding as filed.** Its `1 → 2 → 4 → 8` **understates** the
    growth (that is the single-candidate shape; with several it compounds
    superlinearly). And its "Python dedupes by node id" names the wrong mechanism — the
    dicts are real but the presence diff is what caps the count.
  * **Its two open questions, answered.** *Removal:* multiplicity is inert — derived
    edges are retracted only by filter-ALL, and the erase-ONE primitive's targets are
    untainted under a hypothesis `removeGateB` decides at runtime. But **by assembly, not
    by a theorem**, and that caveat is carried rather than glossed. *Multiset compare:*
    yes on the untainted arm, golden-pinned on the derived arm — a **whole-set** multiset
    compare was assessed and REJECTED (red on 18 of 171 for a declared artifact, with no
    honest edit making it green short of a multi-session model change).
  * **★ The naive fix would have reported GREEN.** Multiplicity died TWICE: first inside
    the Lean binary (`Cli.lean::canonJsonArr` de-duplicates) and again in `extractor.py`'s
    `set`. A Python-side `Counter` alone — the obvious reading of "upgrade P3 to a
    multiset compare" — would have read all-ones from Lean and compared nothing. Caught
    before it bit; the sabotage procedure's "instrument as broken as the subject" case,
    now recorded in its catalogue.
  * **What landed:** `Cli.lean` gains an `edgeCounts` field; `extractor.py` compares
    untainted-arm multiplicity exactly in BOTH the 23-corpus and the ~257-store
    enumerated state gates; the derived arm is golden-pinned
    (`formal/conformance/derived_arm_multiplicity.json`); the exemption boundary is
    computed from the SCHEMA and cross-checked against `EdgeV4.derived`. Two docstrings
    that asserted a false correspondence (`ReconcileDiff.lean`, `Cli.lean`) are corrected.
    **This supersedes the E-chain plan's §D.6 hand-probe** — Leg 2 will now break the
    golden by construction, which is the intended signal.
  * **Seven sabotages, all red, literal outputs in `docs/spec-deviations.md` 2026-07-29**
    and in the tests' own docstrings — including a SUBJECT-side one (drop
    `_reconcile_subject`'s presence guard ⇒ `PYTHON derived-arm direct_edge_count is no
    longer uniformly 1`), not only instrument-side ones.
  * **Gate — all TEN phases green on this machine (`ZANZIBAR_PY` override):**
    `verify.sh lean` PASSED (holes=0, audits 460/460, identity 460, statements 26/26,
    definitions 139/139 UNMOVED, anchors **397**/397 — up from 380; the anchor pin
    caught two bare filenames and one wrong symbol in the new §7.2 text, which is
    exactly what it is for); `conf-tile:1..5/5` 93×5 = **465**; `tests-tile:1..4/4`
    191+191+190+190 = **762**. Floors raised to measured reality: `MIN_CONF_ALL`
    464 → 465, `MIN_CONF_REST` 368 → 369, sabotage-verified (red at 466, green at 465).

## Current status — 2026-07-28

- **2026-07-28 — the last two ZERO-coverage holes closed, and the E-chain Direct-arm
  widening opened properly: scoped, attacked (2 KILLS), Leg 1 landed. Full gate green;
  pushed as `75f952d` / `16c02d4` / `c35dba4`.**
  * **Board item (C) DONE — conformance 450 → 464.** Wildcard usersets and
    `derived-tupleset-ttu` both closed for real. **Reachability was established BEFORE
    writing anything, and the finding as filed read wider than the reachable surface:**
    a wildcard userset over a DERIVED relation is a hard scope rejection raised out of
    `parse_openfga_schema`, so it cannot be a corpus at all (the floor calls the parser
    on every entry); over an UNTAINTED relation it is fully live and that is what is now
    covered. `derived-tupleset-ttu` had been COMPILED in-tree for a year by
    `demorgans_law_1.fga` while driving a constantly-EMPTY TTU — so the durable lesson is
    **"compiled ≠ driven"**: a plan-leaf histogram is a necessary floor, never a
    sufficient one, and every kind-coverage corpus needs a paired non-vacuity pin.
  * **Board item (B) — `ZT-P3-1` — SCOPED + Leg 0 + Leg 1.** Plan:
    `formal/history/echain-widening-plan-2026-07-28.md` (7 legs; supersedes the old
    4-step fork list in five places). **The attack sweep earned its keep:**
    **T2a `graph_reached_inv` does NOT widen with T2b** — `Inv.negEdgeFree` is
    machine-checked FALSE on the widened fragment, and it is a **MODELLING limit of the
    P6 leaf-family collapse, not a Python bug** (verified on the real backends: Python
    routes the write onto the leaf family, so its `neg` row and the edge sit on different
    nodes). A design decision is owed before any T2a work. Leg 1 landed additively
    (audit 457 → **460**, definition pin UNMOVED at 139/139); its new fragment clause
    `DirectArmsConcrete` is **machine-confirmed load-bearing**, not defensive — 262 runs
    over every chain state, 824 derived-R-node in-edges, 0 STAR-sourced; drop the clause
    and 122 stores produce one.
  * ~~**★ ONE FINDING LEFT DELIBERATELY OPEN — read this before picking up (B).** A
    **pre-existing, previously undocumented model↔Python divergence**: the baseline
    cascade enumeration doubles derived-edge multiplicity per leg (`1 → 2 → 4 → 8`,
    because `edgeHolders` re-enumerates every existing copy and `admitEdge` never rejects
    a present edge) while Python dedupes by node id. **The state gate is STRUCTURALLY
    blind to it — projection P3 compares edges as a SET.** Filed UNADJUDICATED at
    `formal/CORRESPONDENCE.md` §7.2.~~ **ADJUDICATED + CLOSED 2026-07-29** — see the
    2026-07-29 status section at the top. Real, model-side, confined to the derived arm,
    removal-inert; P3 narrowed so the untainted arm is compared exactly and the derived
    arm is golden-pinned. **If you are picking up Leg 2, read the §D.6 row in the plan
    first** — the ledger will break by construction and that is the signal.
  * **The sabotage habit is now a STANDARD PROCEDURE:**
    [`docs/sabotage-procedure.md`](../../docs/sabotage-procedure.md), linked from `CLAUDE.md`
    and `formal/HANDOFF.md` house rule 7. It carries the protocol (break the narrowest
    *plausible* weakening, not an obvious catastrophe), the requirement to control your
    *instrument* as well as your subject, and the durability ranking. Two of this
    session's floors would have passed a naive version, and one probe instrument was
    itself wrong (73 false failures) and was caught only by its control run.
  * **Gate (this machine, `ZANZIBAR_PY` override), re-run after every change:**
    `verify.sh lean` PASSED (holes=0, audits **460**/460, identity pin 460, statements
    26/26, definitions **139/139 UNMOVED**, anchors **380**/380); `conf-tile:1..5/5`
    93+93+93+93+92 = **464**; `tests-tile:1..4/4` 191+191+190+190 = **762**. Counts
    re-measured 2026-07-28: `tests/` 762, `formal/conformance/` 464 (**1226** total).
    `MIN_PINNED_AUDITS` was found still at 457 during the doc pass and raised to 460 —
    sabotage-verified (red at 461, green at 460).

## Current status — 2026-07-27

- **2026-07-27 — a REAL PostgreSQL now runs against this repo for the first time, and
  the gate now defends `tests/`. One live authorization fail-open found and fixed.**
  Three workstreams, all gated:
  * **PostgreSQL leg.** `scripts/pg_local.sh` stands up a throwaway user-space
    PostgreSQL 17.10 (conda-forge binaries, cluster outside the repo, loopback-only,
    port 55432 — no system install, no service, `destroy` leaves no trace; there is no
    Docker and no WSL on this machine). `tests/test_postgres_ha.py` (16 tests) drives
    what SQLite provably cannot express, and `ZANZIBAR_TEST_DSN` also re-runs
    `tests/test_concurrency.py` + the two connected-store concurrency/multi-instance
    modules on the server. **MySQL is out of scope by decision** — it was never
    supported and never run, and its prose was actively harmful (below).
    VERIFIED, not reasoned: `FOR UPDATE` really blocks and is row-granular on the
    `SchemaV4` row; lock ordering holds; 4 concurrent writers × 6 writes give 24
    contiguous exactly-once log rows and an index identical to a single-writer replay;
    `log_gap` + `WatermarkGap` fire on a genuine out-of-order commit and commit nothing.
    **The out-of-order commit could NOT be constructed through the supported write
    path** — the lock discipline prevents it (3 writers × 8 writes + a racing observer,
    no hole), so that is written as a positive proof and the guard itself is tested by
    bypassing `TupleSource`.
  * **A live fail-open, fixed.** `SAFE_ISOLATION_LEVELS` accepted `SERIALIZABLE`,
    justified by "PostgreSQL aborts rather than acting on a stale view" — measured
    FALSE — and by an InnoDB fact about a database this project does not support. A
    SERIALIZABLE bind reproduced the full ZT-P1-5 scenario: a committed REVOCATION
    stays invisible, the watermark jumps past it, and `check(at_least=<its token>)`
    certifies the revoked grant as ALLOWED, permanently. Now `{'READ COMMITTED'}` only.
    Found alongside: **`assert_read_isolation` was only ever installed in
    `ConnectedStore.__init__`** — the escalation ran entirely through `TupleSource`,
    which is exported public API and a complete write path. Now called there too.
    Also falsified: `log_gap`'s `FOR SHARE` soundness argument (snapshot-served on PG,
    so the isolation gate — not the lock hint — is what makes it sound), and "a replica
    never sees torn state", which is a SQLite-WAL inheritance that does not exist at
    PostgreSQL READ COMMITTED.
  * **The gate now detects its own erosion in the places it previously could not.**
    `tests/` (728 tests — the 4-way matrix, the lookup oracle gate, the hypothesis
    campaign, the snapshot gate) was OUTSIDE `verify.sh` entirely: running it was an
    agent typing `pytest tests/` and reading the tail. New `tests-tile:I/K` phases put
    it through the same machinery as conformance. The repo had NO pytest config, so a
    bare `@pytest.mark.xfail` on a genuinely failing test reported rc 0 (demonstrated);
    `pytest.ini` now sets `xfail_strict`/`--strict-markers`/`--strict-config`. A missing
    `pyroaring` silently halved the validation matrix — collection now refuses.
    `HYPOTHESIS_SEED` (the footgun that cost a 6-seed sweep) is now a hard error naming
    the working flag. Four anti-vacuity asserts added where a test could pass having
    compared nothing. On the formal side: the 457-theorem axiom audit was a COUNT — now
    also a NAME identity pin and a 26-theorem STATEMENT pin (a headline theorem restated
    `: True := trivial` builds, carries no `sorry` token, and audited clean; it is now
    caught two ways), and `CORRESPONDENCE.md`'s 349 symbol anchors are resolved on every
    `lean` run (they had NO drift detector; the first run found a real mis-anchor).
  * **Gate (this machine, `ZANZIBAR_PY` override), re-run from scratch after the whole
    backlog landed, with every floor raised to measured reality first: `verify.sh lean`
    PASSED (holes=0, audits 457/457, identity pin 457, statement pin 26/26, anchors
    367/367 — 260 Python ≥ 250, 107 Lean ≥ 100); `tests-tile:1..4/4`
    191+191+190+190 = **762** passed; `conf-tile:1..5/5` 90×5 = **450** passed;
    PostgreSQL leg **34 passed, 3 skipped** (SQLite-only by nature, budgeted);
    6-seed fuzz sweep on `tests/test_hypothesis.py`
    (`--hypothesis-seed=` 7/19/31/53/71/97). **ZERO xfails anywhere in the tree** —
    `MAX_TESTS_XFAILED` is back to 0.** Floors now: `MIN_TESTS_ALL` 762,
    `MIN_CONF_ALL` 450 (96+354), `EXPECTED_MIN_AUDITS` 457, anchors 250/100.
  * **Then the whole remaining zero-trust backlog was cleared** in the same session
    (`ZT-P1-8` a–e, `ZT-P1-6a`, outbox retention, `ZT-P4-4/4-5/4-6`, the invariants
    docstring, both orphaned `formal/history/` findings). Board item below has the
    per-item detail **and the three residuals that were deliberately left open** — the
    fan-out cap does not stop the measured N² DoS (that needs a store-level quota),
    ≥3-strata Lean coverage needs a fragment widening, and wildcard usersets +
    `derived-tupleset-ttu` are still at zero coverage. Two fixes were deliberately
    NARROWER than the finding asked for, because the wider version would have been
    dishonest: `lookup(at_least=)` **refuses** rather than falling back (the two
    backends' key spaces are not translatable, and in the stale case the graph rows do
    not exist), and the fan-out cap **exempts removals** (a cap that can refuse a
    revocation is a fail-open).
  * **Then one more gate hole, found by scoping the strata arc and closed the same
    day (`ac3e26e`).** The headline STATEMENT pin added that morning records
    `graph_correct`'s hypothesis as `(hF : W4Fragment S T)` — **by name**. Weaken that
    structure and the theorem claims strictly less over a strictly larger class, while
    the pinned line stays byte-identical and no declaration name changes, so the
    identity pin is blind too. 58 definitions in the 26 pinned statements had that
    shape. New step **4c**, `formal/headline_definitions.txt`: the full text of all
    **132** project declarations the statements depend on TRANSITIVELY, plus the
    hosting files' ambient `variable`/`open` context. Verified by a sabotage that
    *builds*: MOVING `twoStrata` from `W4Fragment` into `GraphAdmission` keeps
    `26/26 statements match` and changes no name, while converting a declared honest
    scope-carry into a claimed guarantee about Python's admission that is false
    (Python reaches 12 strata). Depth is unbounded within the project because the
    closure terminates at the project boundary on its own (converges at depth 9);
    replayed over 34 commits, levels 3–9 added zero firings beyond levels 1–2.
  * **Local PostgreSQL: STOPPED, cluster retained.** `bash scripts/pg_local.sh start`
    brings it back in seconds; `destroy` removes it entirely. Nothing in the default
    gate needs it — `tests/test_postgres_ha.py` is dropped at collection without
    `ZANZIBAR_TEST_DSN`.
  * Detail: `docs/spec-deviations.md` 2026-07-27 and 2026-07-27b.

## Current status — 2026-07-23

- **2026-07-23 — multi-instance set-engine (HA) support LANDED; full gate GREEN
  (first end-to-end gate on the secondary machine).** The set engine now runs as
  several instances (one `Session` each) over one store with bounded inconsistency:
  `SetEngine.apply_logged` (trusted log replay) + `TupleSource.catch_up_evaluator`
  (O(delta) log tailing) replace full rebuilds; every write runs a per-store
  critical section (`_lock_source` `FOR UPDATE` on the `SchemaV4` row → catch-up →
  validate → append) so multi-writer admission (duplicates / remove-existence /
  cycle parity) validates against CURRENT committed state, and log ids commit in id
  order — closing a latent out-of-order log-commit hazard that could make tailers
  (and `advance_index`'s cursor) permanently skip a row. Tokened reads (`at_least`,
  now also on `TupleSource.check`) catch up by tailing; `StaleRead` (relocated to
  `connectedstore/source.py`, re-exported) fires only for snapshot-invisible
  tokens. `SetEngine.result_keys` is the instance-portable lookup surface.
  Consistency model: per-instance prefix consistency + bounded staleness +
  read-your-writes via the existing zookie-lite log-id tokens. +13 tests
  (`tests/test_connectedstore_multi_instance.py`, incl. the cross-instance cycle
  rejection headline + write-ordering pin). **No Lean change** — multi-instance
  scheduling is out-of-model (`formal/CORRESPONDENCE.md` §7 entry: T1 applies
  pointwise per admission-validated log prefix; the lock discipline preserves the
  serial-log premise). Docs: architecture system/decision-log/correctness,
  spec-deviations (dated entry), README zookies rewrite, CLAUDE.md concurrency
  gotcha, gate-runbook slow-machine section. **Gate (secondary machine,
  `ZANZIBAR_PY` override): `pytest tests/` 606/606 in 10 cap-safe tiles
  (Σ == collect-only total); `verify.sh` lean PASSED (sorry-free, audit 455/455) /
  conf-heavy 80 PASSED / conf-rest as 2 guard-preserving tiles (233+17=250 passed,
  0 skips; union ≡ the phased conf-rest); 6-seed fuzz sweep on
  `tests/test_hypothesis.py` (7/19/31/53/71/97) all 20 passed.** Secondary-machine
  setup this session: pyroaring+hypothesis pip-installed; elan + Lean v4.31.0 +
  mathlib cache installed (see gate-runbook "secondary / slow machine").
- **2026-07-18 — OPTIONAL assurance-widening arc OPENED; #1 Leaf/Direct-arm legs 1–3 pushed
  (`98773d3`/`0dd8d7b`/`8a9bee1`); gate GREEN; no Python change.** All four `FINAL_REVIEW.md
  §4` optional widenings scoped (recon + attack-first); durable design/resume state in
  [`formal/history/optional-widening-2026-07.md`](../../formal/history/optional-widening-2026-07.md).
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
  profile). Record: [`docs/history/perf-round5-2026-07.md`](../../docs/history/perf-round5-2026-07.md).
  Standing perf guardrails (fence, dead-ends, hygiene) live in
  [`docs/perf-next-round.md`](../../docs/perf-next-round.md).
- **Clean on `master`.** Last change: the formal `rootB` fragment widening above
  (commits `397f975` / `c3d3113` / `265995d`).
- **2026-07-26 — ZERO-TRUST REVIEW RUN (algorithm · code · security · formal).
  Gate re-verified GREEN from scratch; ONE confirmed live authorization bug found
  (`ZT-P0-1`), plus a large assurance-scope/doc-integrity backlog.** Ten parallel
  adversarial audits: Lean proof hygiene, CORRESPONDENCE drift, conformance
  coverage, gate integrity, Python security, resurfaced dismissals, model-vs-code
  semantic drift, claim-document overclaim, and an empirical gate re-run. **Measured
  ground truth (this machine, `ZANZIBAR_PY` override): `pytest tests/` 606 passed
  in 372 s; `verify.sh lean` PASSED (0 sorries, audit 455 observed / 455 expected,
  only `[propext, Classical.choice, Quot.sound]`); `conf-heavy` 80 passed;
  `conf-rest` 250 passed in 579 s; 0 skips, 0 xfails, 936 tests total.** Nothing is
  red. Every finding below is about the DELTA between what the gate proves and what
  the docs claim it proves — except `ZT-P0-1`, which is a reproduced false ALLOW.
  Full plan: the "Zero-trust review 2026-07-26" section below.

---

## Zero-trust review 2026-07-26 — findings + remediation plan

Read this section with the Open-TODO board; the board items `ZT-*` point here.
**Framing:** the gate is green and the proof tree is genuinely sorry-free and
axiom-clean (independently re-verified, not taken from docs). The Lean side has
**no soundness holes** — no `sorry`, no custom axioms, no `native_decide`, no
`unsafe`/`@[implemented_by]`, and the executed zcli calls the *proved* definitions
directly (`Cli.lean:293` → `GraphModel.check`), so there is no shadow
implementation. What this review found instead is (a) one real code bug, (b) a
security-hardening backlog in the operational envelope, (c) a gate that cannot
detect its own erosion, and (d) claim documents that have drifted away from the
tree they describe.

### P0 — confirmed live bug (fix first, it is an authorization escalation)

- **`ZT-P0-1` — the N3 `_keys_referencing` elision is UNSOUND: dangling residue
  `upos` id → false ALLOW after rowid recycling. REPRODUCED.**
  `index_v4/processor.py:48` `_RESIDUE_LOCAL_LEAF_KINDS = {'closure',
  'derived-computed'}` sets `_cross_object_recordings_possible = False`, which
  short-circuits `_keys_referencing()` (`processor.py:316`) to `[]`, so
  `_residue_references()` returns False unconditionally and `_gc_subject_node`'s
  guard (`processor.py:684`) stops protecting the node.
  **The rationale comment (`processor.py:39-47`) is false for `closure`:** it
  claims closure leaves are safe because they "store raw tuples", but
  `_leaf_concretes(kind='closure')` (`processor.py:790-794`) goes through
  `_incoming_concretes` → `idx.lookup_reverse` → the **full transitive closure**.
  A userset node reachable only transitively is therefore recorded on an object
  where it holds no edge.
  **Failure sequence** (traced): with `group:g1#member → group:g2#member →
  doc:y#a.0`, removing the chain edge drops the node to `reference_count == 0`;
  both affected keys take the cheap path `reconcile_subject`; the first key
  un-records and DELETES the node (elision says nothing references it); the second
  key then finds `s_node is None`, skips the whole `if s_node is not None:` block
  (`processor.py:484-501`), and **never prunes the stale id**. SQLite then recycles
  the freed rowid onto an unrelated principal, and the stale `upos` entry vouches
  for it.
  **Observed** (`n3_FINAL.py`, schema with `closure` leaves ONLY, elision on vs off
  as the control): dangling `('doc','a','y','upos',6)`; I6 flags `residue upos
  holds a dead node id`; `check(group:g9#member, a, doc:y)` returns **True** where
  the oracle says **False**. With the elision disabled: no dangling id, I6 green,
  `check` correct.
  **Attribution note:** this is NOT the 2026-07-17 Fix A lift (that lift *is*
  reachable under the elision, but `reference_count` still protects those nodes).
  The root cause is the `'closure'` entry, and it reproduces on a schema with no
  `derived-computed` leaf at all.
  **Why the gate missed it:** needs an all-whitelist schema + a *transitive*
  userset chain into a tainted relation's closure leaf on **≥2 objects** + the
  chain edge removed in one op so both objects flip in one cascade round. No
  corpus or generator builds that conjunction.
  **Fix options:** drop the elision (cheapest correct), or replace the full
  `ResidueV1` scan with a real index rather than eliding it. The whitelist premise
  must be **"edge-justified ON THE RECORDING OBJECT"**, not "cross-object" — those
  are different properties and only the second is what GC needs. `closure` does not
  satisfy the first; with the Fix A lift, neither does `derived-computed`. **The
  safe residual set is arguably empty.**
  **Gates for the fix:** a regression pin reproducing the above; the hypothesis
  campaign extended to emit transitive userset chains + multi-object recordings;
  re-run the full gate + a multi-seed fuzz sweep (this is an algorithm change).
  Repro scripts are in the session scratchpad (`n3_FINAL.py` repro+control,
  `n3_repro2.py` A/B/C isolation, `n3_who.py` delete-site trace, `n3_amplify2.py`
  rowid-recycle) — **port `n3_FINAL.py` into `tests/` before they are lost.**
- **`ZT-P0-2` — secondary, found by the same trace: the "UNREACHABLE" comment at
  `processor.py:474-483` is WRONG.** It claims the `sp != '...'` branch of
  `_reconcile_subject` is unreachable from the cascade; it is reached exactly in
  the `ZT-P0-1` sequence, because closure leaves DO store untainted-userset
  subjects (`fam.kind == 'closure'` with `s_pred != '...'`). That branch's
  `s_node is None` no-op is the proximate leak. Fix the comment and the branch
  together.

### P1 — security hardening (no confirmed exploit in-tree, but fail-open direction)

Evaluation logic is sound: no fail-open found in ANY `check` path; negation and
stratification are airtight (`_stratify` rejects all derived SCCs, strictly
stronger than needed); no SQL injection (one `insert()` with bound params, zero
`text()`/f-string SQL); interner refcounting verified safe by argument AND by a
4,000-op randomized incremental-vs-rebuild differential with 0 divergences. The
findings are in the operational envelope:

- **`ZT-P1-1` — identifier validation accepts a trailing newline and 257 chars.**
  `zanzibar_utils_v1.py:23` uses `$`, which in Python matches before a trailing
  `\n`. Verified end-to-end through `SetEngine.add_tuple`: `'alice\n'` ACCEPTED,
  `'a'*256 + '\n'` (len 257) ACCEPTED, `'alice\r'` correctly rejected. Violates the
  stated contract (`:14-20`) of keeping control characters out of identity strings,
  and makes the documented 1–256 bound off-by-one for any downstream fixed-width
  consumer. No internal principal confusion (all composite keys are tuples or
  separate columns — verified). **Fix: `re.fullmatch`, or anchor with `\Z`.**
- **`ZT-P1-2` — 16 load-bearing safety `assert`s in `index_v4/core.py` vanish under
  `python -O`** (lines 219-221, 238-239, 284-285, 350, 378-379, 410, 458-459, 512,
  528, 774; plus `processor.py:993`). The three that matter: `:458-459` is the ONLY
  cycle guard on the batch/bridge expansion path (admitting a cycle ⇒ unbounded
  path counts ⇒ permanent phantom reachability ⇒ **stale ALLOW**); `:512/:528` are
  the ONLY refcount-underflow guards; `:774` is the last barrier against a dangling
  edge row on a table with no enforced FKs. The project already converted exactly
  this hazard once (`core.py:651-655`, blind-audit C3) and did not generalize it.
  **Fix: convert to explicit raises.**
- **`ZT-P1-3` — the I1–I13 invariant layer is never wired in production.**
  `install_paranoia` is defined at `invariants.py:383` and called ONLY from
  `tests/wildcard_helpers.py:34` and `tests/test_connectedstore.py:36`.
  `ConnectedStore.__init__` never calls it and exposes no flag. CLAUDE.md's
  "paranoia default ON via `make_wildcard_index`" is true of the TEST HELPER only.
  Every runtime detector for the corruption classes in this review is dark in
  production — **including I6's dead-node-id check, which is precisely what catches
  `ZT-P0-1`.** Combined with `ZT-P1-2`, a `-O` deployment has neither asserts nor
  invariants. **Fix: wire it into `ConnectedStore` behind an env flag, default ON.**
- **`ZT-P1-4` — both documented locks are silent no-ops on SQLite and the library
  ships no engine configuration.** `source.py:142-144` / `core.py:204-206` are
  `with_for_update()` with no dialect branch; the compiled SQLite statement carries
  no `FOR UPDATE` (verified). The delegation to "the database write lock" only
  holds if the validating SELECTs and the INSERT share one transaction, but
  pysqlite's default `isolation_level=''` runs SELECTs in autocommit. The fix
  exists ONLY in the test harness (`tests/test_connectedstore_multi_instance.py:75-79`
  sets `isolation_level = None` + a `BEGIN` listener). So two default-configured
  writers can both pass admission — including cycle-parity and exclusion checks —
  against a state their combined result invalidates. There is also no
  `SQLITE_BUSY` retry anywhere in the library. **Fix: real write lock
  (`BEGIN IMMEDIATE`) on a SQLite bind; reject `isolation_level != None` at
  construction.**
- **`ZT-P1-5` — watermark advances are unguarded, and the freshness token then
  CERTIFIES the stale answer.** `apply.py:133` `cursor.applied_log_id = rows[-1].id`
  and `source.py:171/:184` `max(self.evaluator_watermark, token)` both assume a
  complete catch-up. Under MySQL/InnoDB REPEATABLE READ (the default), an early
  `lag()`/`watermark()`/`check()` pins the read view; a concurrent commit of
  `ADD 5` + `REMOVE 6` stays invisible; the write returns id 7; both watermarks
  jump to 7 and rows 5–6 are **permanently unapplied**. `check` then returns ALLOW
  forever — including under `at_least=7`, because `_fresh_enough(7)` passes. The
  mechanism designed to guarantee freshness vouches for a state that never existed.
  Note `source.py:279` uses the correct pattern ("Assignment, not max") elsewhere.
  **Fix: advance to the CONTIGUOUS head and raise on a gap; pin/assert READ
  COMMITTED on connect.**
  *(Finding text left exactly as filed 2026-07-26, for provenance. Read the dialect
  reasoning in it as superseded: **MySQL is not a supported backend**, and the hazard
  is real on PostgreSQL for a different and now-measured reason — a lower log id can
  commit after a higher one even at READ COMMITTED. See `docs/spec-deviations.md`
  2026-07-27.)*
- **`ZT-P1-6` — no resource bounds anywhere; two DoS paths measured.** No depth
  limit, tuple quota, fan-out cap, or fuel counter exists in any in-scope module.
  (a) 240 raw tuples in a hub topology → **14,640 closure rows in 5.1 s** (~N²),
  and this runs INSIDE `advance_index` holding both locks, so one write stalls
  every writer on the store. (b) A 1,500-long `group#member` chain is accepted
  without complaint and then makes every read raise `RecursionError`
  (`engine.py:1017` `sat`/`member_via_usersets` recursion) — writes still succeed,
  so the store stays writable while reads on that subgraph are permanently dead;
  `lookup` is worst since it sweeps every declared `(type, relation)`.
  **Fix: admission-time max chain depth; per-write closure fan-out cap; convert
  `sat` to an explicit stack.** Related: `delta_outbox_v1` is append-only with no
  retention (no `DELETE` anywhere).
- **`ZT-P1-7` — a caller `begin_nested()` silently disables BOTH locks.** The memo
  at `core.py:201-209` / `source.py:139-147` keys on `get_transaction()`, which
  returns the ROOT transaction, not the nested one. Take locks inside a savepoint,
  roll the savepoint back (PostgreSQL releases those locks), and the next call
  matches the memo and takes NO lock. The `Session` is caller-supplied
  (`store.py:39`), and speculative-write-in-a-savepoint is an ordinary pattern.
  **Fix: key the memo on `(get_transaction(), get_nested_transaction())`.**
- **`ZT-P1-8` — smaller, still fail-open-direction:** `at_least` is check-only and
  `lookup`/`lookup_reverse` have NO freshness path at all (`store.py:234-238`), so
  a revoked principal stays enumerable with no API to demand freshness (revocation
  UIs are exactly list-objects/list-users); `_fresh_enough(None) → True` is a
  fail-open default. `SetEngine.add_tuple` writes `TupleV1` with no `TupleLogV1`
  append and `source.engine` is public, so a caller can create permanent silent
  index/source divergence while `lag()` reads 0. `wildcard.py:534-550` full-scans
  `residue_v1` with per-row JSON decode driven by untrusted query args.
  `processor_writes` (`wildcard.py:59`) is a plain bool, not thread-scoped — the
  entire I5 bypass window.

### P2 — the gate cannot detect its own erosion

All four verified directly against `verify.sh` and by execution:

- **`ZT-P2-1` — the axiom-audit "expected" count is derived from the audited file.**
  `verify.sh:113` `EXPECTED_AUDITS=$(grep -cE '^#print axioms ' "$AUDIT_LEAN")`,
  checked against `OBSERVED` with the only floor being `-gt 0`. **Deleting
  `#print axioms graph_correct` from `Audit.lean` keeps the gate green.** Reducing
  `Audit.lean` to one trivial line still prints PASSED. The `455` figure lives only
  in prose. (The equality check IS meaningful — it catches a vacuous cache-hit
  rebuild — but it is not a coverage guard, and `gate-runbook.md:67-70` sells it as
  one.) **Fix: `EXPECTED_MIN_AUDITS=455` asserted with `-ge`.**
- **`ZT-P2-2` — no minimum conformance count; `xfail` is invisible.**
  `verify.sh:171-174` asserts only `skipped == 0` and `passed > 0`. Shrinking
  `GRAPH_FRAGMENT` to one corpus, or deleting `test_conformance_graph.py` outright,
  keeps the gate green. And `verify.sh:166` greps only for `N skipped` — pytest
  reports `xfailed` as a distinct word, so marking a newly-failing comparison
  `@pytest.mark.xfail` yields `329 passed, 1 xfailed` → **PASSED**. There are zero
  xfails in `formal/conformance/` today, but CLAUDE.md endorses xfail as a workflow
  in `tests/`. **Fix: per-phase `-ge` floors (80 / 250 / 330) + parse
  `xfailed`/`xpassed`/`deselected` into the zero-tolerance check.**
- **`ZT-P2-3` — `sorry_scan.py:57` is blind to the exact constant the gate exists
  to exclude.** The regex is `\b(?:sorry|admit)\b`; `\bsorry\b` cannot match
  `sorryAx` because `A` is a word character. Verified by execution: `sorry` → hit;
  **`sorryAx` → MISS; `native_decide` → MISS; `axiom cheat : ∀ p, p` → MISS.** Also
  one stray unterminated string literal makes the remainder of that file invisible,
  silently. Backstops are partial (the build-log warning check covers only modules
  built in step 1; the axiom whitelist covers only the ~35% of declarations inside
  an audited dependency cone). **Fix: extend to `sorry|admit|sorryAx` +
  `native_decide` + a separate `^\s*axiom\s` scan.**
- **`ZT-P2-4` — two files sit where BOTH nets are blind.** `verify.sh:77` passes
  `$LEAN_DIR/ZanzibarProofs` (the directory), so the sibling library root
  `ZanzibarProofs.lean` is **not scanned**. And `Cli.lean` — the zcli that IS the
  conformance ground truth — is not reachable from the default lake target, so
  step 1 never builds it and its warnings never reach `$BUILD_LOG`; step 3's
  `lake build zcli` output is not captured at all (`verify.sh:91`, no `tee`). A
  `sorryAx` in the conformance oracle is invisible to every check. **Fix: scan
  `$LEAN_DIR` with an explicit `.lake` exclusion; `tee` step 3 into the same grep.**
- **`ZT-P2-5` — vacuous restatement is unguarded.** `verify.sh:127-128` builds
  `BAD` only from lines containing `depends on axioms`; a theorem restated as
  `: True := trivial` emits "does not depend on any axioms", counts toward
  `OBSERVED`, and passes. This is not hypothetical — see `ZT-P3-2`.
- **`ZT-P2-6` — operational:** `verify.sh:44` hardcodes the dead
  `C:/Users/avery/...` interpreter, so `bash formal/verify.sh` as written in
  CLAUDE.md **cannot run on this machine** without `ZANZIBAR_PY` (fails loudly, so
  safe — but both CLAUDE.md and `gate-runbook.md:28` repeat the dead path).
  `conf-rest` now takes **579 s against a 600 s cap**; `formal/history/` filed
  "consider splitting the phase" on 2026-07-19g and it was never actioned. Also
  unguarded: a missing `pyroaring` silently downgrades the set engine to `PySets`,
  under-testing the "both SetOps" legs with no gate check.
  Note the phase split itself is **gap-free** (verified: `conf-rest` is the
  directory minus `$HEAVY_CONF` via `--ignore`, 80 + 250 = 330 = the one-shot),
  and `runner.py`'s retry logic is genuinely non-masking (verified) — those two
  worries are unfounded.

### P3 — claim-document integrity (what is claimed vs what is proved)

- **`ZT-P3-1` — the headline theorems are VACUOUS on the canonical boolean idiom,
  and only `formal/history/` says so.** `PROOF_STATUS.md:36`: *"the CURRENT
  admission bundle is UNSATISFIABLE"*, and `FullScope.lean:564` machine-checks
  `outside_old_admission : ¬ StoreValidRules Sd Td`. So on a store holding a tuple
  written through the `Direct` arm of a derived def — i.e. `can_view: [user] but
  not blocked`, the most common Zanzibar boolean shape — `graph_correct`,
  `graph_reached_inv` and `Exec.graphRun_check_eq_sem` hold **vacuously**.
  `FINAL_REVIEW.md` §3 records this only as a scope gap ("non-`ComputedOnly` leaves
  not covered"), which reads as *narrower coverage* rather than *no theorem*.
  **That distinction is the whole difference between a narrow theorem and none.**
  Fix: state it plainly in `FINAL_REVIEW.md` §3 and `ARCHITECTURE.md` §6.
  > **Disposition (added 2026-08-05; this file is an archive, so the finding above is
  > left as filed).** The doc fix landed 2026-07-26. The SUBSTANCE was then fixed by
  > the E-chain Direct-arm widening, legs 0–6 — but only for **T2b and the theorems
  > routed through it**. `graph_reached_inv` (T2a) is still vacuous on that shape and
  > now carries an explicit `W4NarrowT2a` bundle saying so. See this file's `ZT-*`
  > ledger row for `ZT-P3-1`, and the live board item (B1) in the root `HANDOFF.md`.
- **`ZT-P3-2` — at least 2 of the 455 audited reports are known-vacuous.**
  `Audit.lean:1332` `#print axioms checkFnR_eq_sem_settled_d` and `:1335`
  `#print axioms w3d2_leg_context_d`. `PROOF_STATUS.md:308` calls that exact pair
  *"an UNSATISFIABLE pair … green but un-dischargeable by a real `_d` chain"*; the
  `_filt` variants that superseded them are what the live proof uses
  (`CascadeStrataResettle.lean:1886`). A third such bundle (`hCO` schema-wide) was
  found and repaired 2026-07-20d. So **455/455 is a policy count, not a coverage
  count.** Fix: drop or annotate the superseded pair; audit the `_filt` variants.
- **`ZT-P3-3` — `direct_arm_exclusion` is gated as in-fragment but is provably
  outside it.** `corpus.py:388` puts it in `GRAPH_FRAGMENT`;
  `test_conformance_graph.py:22-23` says that set is "inside GraphAdmission +
  W4Fragment" and that answers "are covered by `graph_correct` verbatim"; the Lean
  tree proves the opposite (`outside_old_admission`), and `FullScope.lean:527-528`
  records the covering theorem as *"recorded follow-up, NOT done"*. The docstring's
  safety net — *"zcli refuses (nonzero rc) on admission failure … so an
  out-of-scope run FAILS loudly"* — does not hold: the CLI gates only on
  run-success (rc 2) and drained-ness (rc 3), never on `GraphAdmission`/
  `W4Fragment`. Those 11 tests are a differential test, not theorem-backed
  coverage. **Fix: correct the docstring now; ideally add a runtime
  admission/fragment gate to the CLI (the tree already shows how — `removeGateB`
  decides six `Prop`s at runtime).** Related: `test_conformance_remove_graph.py:102`
  excludes this same corpus from remove-driving, so "removes are driven end-to-end"
  is true for every in-fragment corpus EXCEPT the newest one.
  > **Disposition (added 2026-08-05).** The docstring was corrected 2026-07-26 (the
  > corpus was moved to `_DIFFERENTIAL_ONLY`), and on 2026-08-05 E-chain leg 6 moved
  > it back to `_THEOREM_BACKED` — this time **earned**, by
  > `W4WitnessDirect.final_applies4`, the headline `graph_correct` at the corpus's own
  > four-tuple store. The remove exclusion SURVIVES with a changed reason (the guard,
  > not admission). **The CLI still does not gate on `GraphAdmission`/`W4Fragment`**,
  > so the runtime-gate half of the proposed fix remains undone and this finding's
  > central hazard is unchanged.
- **`ZT-P3-4` — `FINAL_REVIEW.md:52` and `SEMANTICS.md:615` still list `rootB` as a
  `W4Fragment` field.** It was deleted 2026-07-17; `FullScope.lean:122-132` has six
  fields (`computedOnly, twoStrata, wsBare, bareStar, ttuStarFree, term`). The
  authoritative claim doc misstates the proved fragment.
- **`ZT-P3-5` — every doc number is stale, and NOTHING gate-enforces any of them.**
  Measured: axioms **455**, conformance **330**, `tests/` **606**, corpora **20**
  (19 in-fragment), enum **6 shapes / 1021 stores**.
  Claimed: `formal/README.md` 412 axioms / 248 tests; `CLAUDE.md` 531 + 288 = ~819;
  `docs/gate-runbook.md` 531 and 315; `formal/HANDOFF.md` 326;
  `docs/architecture/overview.md` 263; `ARCHITECTURE.md` 17 corpora / 4 shapes /
  527 stores. **`FINAL_REVIEW.md` states BOTH 263 and 326 in one file, and BOTH 19
  and 15 corpora** — so the house rule "nothing may claim more than FINAL_REVIEW"
  currently binds every other doc to a self-contradictory target, and the
  subordinate `HANDOFF.md` is the most accurate doc in the tree.
- **`ZT-P3-6` — the two residual-surface lists omit two whole unverified
  surfaces.** `FINAL_REVIEW.md` §3 and `ARCHITECTURE.md` §6 carry identical
  seven-item lists — and identical blind spots. Missing: **bulk build/backfill**
  (`bulk_build.py` + `bulk_backfill.py`, the DEFAULT `build_index` path, an entirely
  separate constructor of index state with no Lean model, pinned only by a
  Python↔Python differential gate) and **multi-instance HA** (`_lock_source`, lock
  ordering, `catch_up_evaluator`, `apply_logged` — item 5 names only `_lock_store`).
  Both ARE documented in `CORRESPONDENCE.md`; the honesty ledgers are the two docs
  that stopped being updated.
- **`ZT-P3-7` — top-level `README.md:58-62` correctly says the Python is "not
  itself verified"** (the single most important thing to get right, and it is
  right) **but drops the graph-side scope caveat**, presenting backend equivalence
  as unqualified. `docs/architecture/verification.md:94-101` states it correctly and
  should be the model.
- **GOOD NEWS, verified: `SEMANTICS.md` still matches `tests/oracle.py`** rule for
  rule (all 12 key rules checked individually: direct leaf star/userset branches,
  TTU stored-parent, `memberOfGranted` ∀⇒∃, fuel bound, exclusion/intersection,
  undefined-relation → False, grammar). Only the line citations drifted, and that
  drift is self-disclosed at `SEMANTICS.md:15-19`. **The trust root is sound.**
  Likewise `setEngine_correct` is genuinely unconditional (all three hypotheses
  underscored/unused) — "set engine at full scope" is honest, if anything an
  under-claim.

### P4 — the correspondence map, and what the harness actually covers

- **`ZT-P4-1` — `CORRESPONDENCE.md` is broken as a navigational map.** Every Lean
  definition it cites still exists (~60 checked, zero missing) — the Lean side is
  clean. But of ~45 Python `file:line` citations, **4 are accurate and ~35 point at
  unrelated code**; **§5 (the cascade — the most intricate subsystem and the one an
  auditor can least re-derive unaided) is 100% wrong.** An auditor following §5
  lands in `_write_derived`, `_gc_subject_node` and `_keys_referencing`. Worse, the
  same stale citations were **copied into the Lean docstrings**
  (`ReconcileStars.lean:227-229`, `ReconcileDiff.lean:209,220`, `Cascade.lean:448`,
  `FullScope.lean:76,84,110`, `UsStarWrite.lean:35`), so the drift is undetectable
  by cross-checking the two artifacts. Drift rate is ~3,000 lines per two weeks —
  **no manually-maintained line number survives that.**
  **Fix: re-derive all citations, then move to SYMBOL anchors (function name +
  a grep-checkable assertion in `verify.sh`) instead of line numbers.**
  *Important:* the agent found no evidence any theorem verifies dead code — the
  algorithms drifted POSITION, not SHAPE. The pin is likely still real; it is the
  auditability that failed, which is exactly what this file exists to provide.
- **`ZT-P4-2` — three CORRESPONDENCE rows are semantically wrong, not just stale.**
  (a) **§2 `SetEngineModel.check` ↔ `SetEngine.check` is a false algorithm-twin
  claim.** Lean's `check` (`Eval.lean:144-147`) is pure fuel-bounded `MemberSet`
  expansion; Python's `check` (`engine.py:910-1058`) is a Tarjan-lowlink-memoized
  short-circuiting boolean DFS that never builds a `MemberSet`. The real twin of
  the Lean def is Python's **`expand`** — which no conformance gate drives.
  Declared honestly in `Eval.lean:25-27`, but the CORRESPONDENCE row and
  `FINAL_REVIEW`'s "full scope" say nothing. (b) **§3 `Inv` overclaims** — it is 8
  clauses, and only I2 is fully modeled; I1 appears as endpoint-existence only, I3
  not at all, and I4/I5/I7/I10/I13 plus eight I6 sub-clauses are omitted with no
  acknowledgement. The label "structural I1–I3 + four I6" should read "I1
  (endpoints only) + I2 + four I6". (c) **§6 `ReachedByW3d2E` "interleaved" is
  false for the batched path** — `apply.py:128-132` applies the WHOLE batch then
  runs ONE cascade, so a `remove` at batch position 2 executes against a provably
  not-drained state, exactly what `removeGateB`'s `cascadeKeys = []` excludes.
  §7 asserts the remove scope is "exactly Python's behavior" citing tuple
  presence — a different property. **The proved execution schedule is not the one
  production runs.**
- **`ZT-P4-3` — two undeclared cascade-model gaps.** (a) The **`_bumped`
  residue-version channel**: Python has a SECOND source of dirty keys
  (`processor.py:930` populate, `:1117-1120` fan out, `:1143-1146` quiescence
  check) that emits no outbox rows; Lean derives all cascade keys from
  `σ.frontierRows` and `Residue` has no version field at all. So **T5's
  "the abort is dead code" is a claim about a weaker abort condition than the one
  Python ships.** (b) `affectedKeys` models 2 of ~6 Python delta→key channels
  (missing: subject-GC scan, tupleset-ttu dependents, `tupleset_feeders`,
  `target_feeders`, and `_fan_out via ∈ {ttu, userset, tupleset-ttu}`). All
  out-of-fragment, so scope-honest in substance — but §7's wording says
  `affectedKeys` "now carries **BOTH** Python branches", which an auditor would
  take at face value. Also unmodeled: the whole subject-level cheap path.
- **`ZT-P4-4` — coverage is narrower than "five/six-corner differential" implies.**
  Measured across all corpora: **max 2 strata anywhere** (so Python's ≥3-stratum
  cascade path — which `demorgan1` exercises — is tested by NOTHING in this
  harness); **every union and intersection is binary** (so `encode.py`'s n-ary
  left-fold, the documented modeling bridge to Lean's binary ops, never runs at the
  arity it exists for); exclusion nested exactly once; wildcard usersets and
  ≥3-arity operators at **zero**; object wildcards at one 1-tuple corpus worth six
  queries; largest store in the entire Lean differential is **8 tuples**; median
  **64 queries per corpus**. **No conformance test asserts a nonzero comparison
  count**, and there is a live zero-query configuration one corpus-list edit away
  (`_graph_queries_for` filters `on != "*"`, which yields 0 queries for
  `object_wildcard` — a corpus whose exclusion note invites exactly that move).
- **`ZT-P4-5` — the state gate is far thinner than "state-level equality" implies.**
  Measured over the 19 in-fragment corpora: of 422 raw edge rows, **231 dropped by
  P1, 55 by P6, 136 actually compared**; **all 217 `NodeV4` rows dropped by P5**
  (nodes are not compared at all); and **only 5 of 19 corpora produce ANY residue
  row — 11 rows across the entire curated state gate**, so 14 corpora compare two
  empty dicts. `CORRESPONDENCE.md:214-215` already concedes the current node-flag
  behavior is "invisible to the gate by construction". Also: `ResidueV1.version` is
  dropped by the extractor WITHOUT being one of the documented P1–P6 projections,
  so I7 is gated by nothing formal.
- **`ZT-P4-6` — the "three genuinely independent corners" claim
  (`CORRESPONDENCE.md:47-49`) is 2-of-3 at the schema-reading layer.**
  `encode.py:18-28` and `grid.py:31,59` both import `parse_schema_ast` from
  `tests/oracle.py`, so the Lean corner is fed by the oracle's parser AND the query
  grid's targets come from that same parse — a misparse propagates to two corners
  and simultaneously deletes the query that would expose it. Demonstrated parser
  divergence: on a duplicate `define`, `oracle.py` silently keeps the last while
  `zanzibar_utils_v1.py` raises. `encode.py`'s own docstring is honest about this;
  the CORRESPONDENCE claim is not.
- **`ZT-P4-7` — `GraphDriver.apply` swallows every `ValueError` into "rejected"**
  (`backends.py:162-164`), and `test_conformance_remove.py:406` then builds the
  oracle from the graph's OWN accepted set. An `index_v4` bug that spuriously
  raises on a legitimate add removes the tuple from BOTH sides; both corners agree
  on a smaller store; test green. **This gate is structurally incapable of
  detecting an admission regression.**

### P5 — resurfaced dismissals now INVALID or UNVERIFIED ("ignore the ignore")

Full inventory (~60 items across 7 categories) was produced; these are the
dismissals whose stated justification no longer holds:

- **The "OpenFGA doesn't support these either" argument is invalid as a
  PRIORITY argument** for the two scope rejections. The repo already ships object
  wildcards as a deliberate extension BEYOND OpenFGA (no DSL syntax; passed via
  `object_wildcard_shapes=`, 52 production refs). The argument proves the DSL lacks
  syntax, not that no user wants the construct — and the repo invented the
  construct. The rejections themselves are sound and fail loud; only the
  deprioritization reasoning is circular.
- **"Fragment exclusions are proof-scope, not behavioral" already failed once and
  the sentence is still live.** The 2026-07-12k probe concluded this from
  CHECK-level evidence; on 2026-07-17 the repo found a real model-vs-Python
  divergence at **STATE** level in exactly that situation. The identical inference,
  applied to the object-wildcard corpus, is still asserted in `FINAL_REVIEW.md` §3
  and `ARCHITECTURE.md` §6 — and that corpus was never probed at state level.
- **"The multi-hop out-bridge generalization is unreachable" (reg11) repeats an
  argument this repo already disproved.** Its predecessor (reg10) was filed as "no
  current corpus/pool can build it" and turned out to be "true only of the existing
  fuzz pool, not of reachability: a 3-relation schema + 2 writes builds it."
  reg11's unreachability rests on a single two-write probe over an unbounded schema
  space, and no generator emits the class.
- **The HA correctness story is validated only where its bug cannot occur.** The
  2026-07-23 fix closes an explicitly **PostgreSQL-only** hazard (out-of-order log
  commits ⇒ a tailer permanently skipping a row). CI runs SQLite. Every mechanism
  it relies on is, in the repo's own words, "reasoned about, not CI-tested", and
  Phase 7 (TLA+ for concurrency) is "not started". Now the single largest untested
  assumption in the system, and answer-affecting. Ties to `ZT-P1-4`/`ZT-P1-5`.
- **The from-chain TARGET note's *reachability* half is stale** — asserted
  2026-07-13, never re-derived across three later widenings (Fix A's `upos` lift,
  the `rootB` widening, the Direct-arm corpora). Its "fails LOUD" half is
  unaffected and is the real safety property.
- **N14 was declined for "zero harness coverage", then a heavier version of the
  same scan shipped the next day** — Fix B's `_any_residue_reference`
  (`processor.py:710-723`) is a COMPLETE `ResidueV1` scan with per-row JSON decode
  on every node-release path on ALL schemas, landed after the perf arc closed and
  never benchmarked. (Note: `ZT-P0-1`'s fix will likely make this hotter still —
  bench them together.)
- **Orphaned findings that never reached any board** (they live only in
  `formal/history/`): the `w3cJobValid_enumJob2D` star-freeness hole (an OPEN
  attack surface naming a Python-ADMITTED schema shape); `PDerivedUserset` — the X4
  shape fixed Python-side 2026-07-13 and extended 2026-07-17, **never modeled in
  Lean**, in the exact area where five real divergences were found; the
  `reconcile_subject` cheap path not modeled (and it has since gained real logic);
  phase-ledger row 0.5 (`todo`, never closed); the `conf-rest` cap warning.
- **Three documents give three different lists of which invariants run per commit,
  and none matches `index_v4/invariants.py`** (`verification.md` vs
  `correctness.md` vs the `check_invariants` docstring vs the actual body, which
  runs I1–I7 + I10 + I13).

### Suggested sequencing

1. **`ZT-P0-1` + `ZT-P0-2`** — fix, pin, fuzz, gate. Port the scratchpad repro into
   `tests/` FIRST so it is not lost.
2. **`ZT-P1-1`, `ZT-P1-2`, `ZT-P1-3`, `ZT-P1-7`** — small, high-leverage, mostly
   one-liners; `ZT-P1-3` is what would have caught `ZT-P0-1` in production.
3. **`ZT-P2-1` … `ZT-P2-4`** — make the gate defend itself before adding coverage,
   otherwise later erosion is again undetectable.
4. **`ZT-P3-1` … `ZT-P3-5`** — correct the claim docs. Cheap, and `ZT-P3-1` is the
   one an outside reader would most object to.
5. **`ZT-P1-4`, `ZT-P1-5`, `ZT-P1-6`** — the operational envelope; needs a design
   decision on how much the library owns vs delegates to the operator.
6. **`ZT-P4-*`** — the correspondence rebuild (move to symbol anchors) and the
   coverage widenings (≥3 strata, n-ary operators, nonzero-comparison asserts).
7. **`ZT-P5`** — re-adjudicate the stale dismissals; prefer PROOF or a REPRO over
   "no corpus exercises it", which this review showed fails repeatedly.

---


## Completed board items

- [x] **DONE 2026-07-26 — `ZT-P0-1` FIXED (verified in code 2026-07-27).** The
      whitelist is gone, not narrowed: `index_v4/processor.py` now carries an
      "N3 WITHDRAWN — DO NOT RE-INTRODUCE" block stating the property GC actually
      needs (the recording must be *edge-justified ON THE RECORDING OBJECT*, which is
      strictly stronger than the "not cross-object" property the old comment argued),
      and showing that NO leaf kind satisfies it — so the safe residual whitelist is
      EMPTY and `_keys_referencing` always scans. Regression pin:
      `tests/test_reg14_residue_gc_elision.py`. `ZT-P0-2` closed with it (the false
      "UNREACHABLE" comment is gone; `s_node is None` now escalates to a full-object
      reconcile). Original finding text retained below for provenance.
      ~~`index_v4/processor.py:48` — the
      `'closure'` entry in `_RESIDUE_LOCAL_LEAF_KINDS` is unjustified: closure
      leaves resolve candidates through the FULL TRANSITIVE CLOSURE
      (`_leaf_concretes` → `_incoming_concretes` → `lookup_reverse`), so a userset
      node is recorded on an object where it holds no edge. The elision then lets
      `_gc_subject_node` delete a node a live residue still references, the second
      key of the same cascade round no-ops on `s_node is None`, and the stale
      `upos` id survives to vouch for whatever principal SQLite recycles the rowid
      onto. **NOT the 2026-07-17 Fix A lift** (reproduces with no `derived-computed`
      leaf at all). I6 catches it — but only under paranoia, which production never
      enables (`ZT-P1-3`). **FIRST ACTION: port the scratchpad repro (`n3_FINAL.py`,
      repro + elision-disabled control) into `tests/` before the session scratchpad
      is lost.** Then fix, extend the hypothesis generator to emit transitive
      userset chains recorded on ≥2 objects, and run the full gate + multi-seed
      fuzz (this is an algorithm change → Lean/CORRESPONDENCE review too).~~
      Detail: the "Zero-trust review 2026-07-26" section above.
- [x] **DONE 2026-07-26 — `ZT-P5-NEW` FIXED (write-time, not compile-time) + the
      fuzzer blind spot closed + `AdmissionRejected` landed.**
      **The fix is a WRITE-time rejection, deliberately not a schema rejection.**
      Attempting the compile-time route (the established decision-15 pattern) found
      that **the dangerous schema IS reg11's schema** — character-identical to
      `REG11_SCHEMA`, same OWC set after expansion — so any compile-time criterion
      would reject the legal reg11 / `owc_star_ttu` class wholesale and delete four
      existing tests plus a corpus. `WildcardIndex._reject_star_self_edge` instead
      refuses a routed `w_any(T,p) → w_all(T,p)` edge on a shape in
      `bridged_in ∩ bridged_out` — a cycle BY CONSTRUCTION, since bridges are
      schematic, so every present and future concrete `T:x#p` closes
      `w_any → w_all → concrete → w_any`. This is the position-split restatement of a
      rule the set engine already had (`_would_cycle`'s raw-level `u == v` on the
      UNSPLIT key): the two backends now implement ONE rule in two representations
      rather than two that happened to agree. Verified: star-star write now
      `GRAPH=False SET=False`, innocent grant `GRAPH=True SET=True`.
      **The false justification sentence** behind the 2026-07-17 narrowing is annotated
      at all five sites it appeared (`docs/spec-deviations.md`, `zanzibar_utils_v1.py`
      ×2, `index_v4/wildcard.py`, `setengine/engine.py`, `tests/test_lookup_oracle.py`)
      with the surviving NARROWER reading: a through-shape cannot make the danger a
      property of the SCHEMA, so it does not belong in a COMPILE-TIME criterion —
      nothing more.
      **Fuzzer blind spot closed:** `star_bridge_configs` now sometimes draws `A == B`
      (self-referential TTU), with the literal `T:*#A` restriction deliberately omitted
      in that variant — keeping it would make the shape doubly-bridged and
      `DoublyBridgedShapeError` would skip every self-referential config, reopening the
      blind spot under a new name. Validated by reverting the fix: the hardened
      `StarBridgeParityMachine` **rediscovers the bug on its own**, drawing the
      self-referential schema and the object wildcard independently of the
      deterministic pin. Both xfails flipped to plain pins.
      **`ZT-P4-7` also closed:** `AdmissionRejected(ValueError)` now types ~20 genuine
      refusal sites, so `GraphDriver.apply` stops allow-listing exception MESSAGE
      SUBSTRINGS and an unclassified `ValueError` propagates instead of silently
      shrinking both sides of the comparison. No admission decision changed — proved by
      an 854-entry differential against a mechanically-inverted tree, 0 differences.
      Three refusal sites the review's list had MISSED were found and classified.
      No Lean change owed (`CORRESPONDENCE.md` §8.1: `admitEdge` is a decision
      procedure; the guard's precondition is unsatisfiable in every modeled fragment).
- [ ] **NEW 2026-07-26 — the rest of the zero-trust backlog (`ZT-P1` … `ZT-P5`).**
      Schema is reg11's own (`parent: [folder, folder:*]`, `viewer: [user] or viewer
      from parent`, `object_wildcard_shapes={('folder','parent')}`); the write is a
      single `folder:* parent folder:*`. **Independently reproduced:**
      `GRAPH accepted=True | SET accepted=False`; then an innocent later
      `user:v viewer folder:q` is `GRAPH accepted=False | SET accepted=True`, while the
      **oracle says that grant should hold**. So one write permanently locks the graph
      index out of a legitimate grant, and **I1–I13 stay GREEN** — no invariant catches
      it. Fail-CLOSED direction (denial, not escalation), but wrong and unrecoverable
      for that store.
      **Mechanism:** the routed edge is `w_any(folder,viewer) → w_all(folder,viewer)` —
      two DISTINCT `node_v4` rows under the position-split wildcard encoding — so it is
      not a self-loop and the cycle check never fires. `(folder,viewer)` then sits in
      BOTH `bridged_in_shapes` and `bridged_out_shapes`, so every present-or-future
      concrete viewer node carries both bridges and closes the cycle.
      **Why the 2026-07-17 F1/F2 gate misses it:** `_reject_doubly_bridged_shapes`
      narrowed its left factor from `bridged_in_shapes` to literal `T:*#p` restriction
      shapes, justified by "star-tupleset through-shapes … cannot mint a persistent
      `w_any` node — reg11's dangerous writes self-cycle … so nothing detonates."
      **That justification sentence is FALSE**; the coarse criterion would have caught
      this. Revisit the narrowing rather than assuming it was safe.
      **Why no fuzzer built it:** `_star_bridge_schema` always emits `B: [user] or A
      from parent` with `A != B`, so it can never build a SELF-REFERENTIAL TTU
      (precondition ii); reg11/`owc_star_ttu` have the self-referential TTU but never
      write a star-OBJECT `parent` tuple. **Cheapest generator fix: let
      `star_bridge_configs` sometimes draw `A == B`.**
      **Exposure:** `ConnectedStore` is NOT exposed (`TupleSource` delegates admission
      to the `SetEngine`) — it bites `WildcardIndex` used directly, which is public API
      and is what the matrix's `GraphBackend` drives.
      Pins: `tests/test_zt_p5_readjudication.py` (strict xfail + a companion pinning
      TODAY's behavior so drift in EITHER direction is caught — flip and delete them
      together). Detail: `docs/spec-deviations.md` 2026-07-26 ZT-P5.
- [ ] **The zero-trust backlog, RE-TRIAGED 2026-07-27 against the code (not against
      this board, which had gone stale).** The P0/P1/P2/P3 waves genuinely landed —
      each verdict below was checked at a `file:line`, not taken from a commit message.
      **CLOSED:** `ZT-P0-1`, `ZT-P0-2`, `ZT-P1-1`, `ZT-P1-2`, `ZT-P1-3` (wired, default
      OFF — measured, see `ConnectedStore.DEFAULT_PARANOIA`), `ZT-P1-4`, `ZT-P1-5`
      (both now also exercised on a real server), `ZT-P1-7`, `ZT-P2-1..4`, `ZT-P2-6`,
      `ZT-P3-1..7`, `ZT-P4-2`, `ZT-P4-3`, `ZT-P4-7`, `ZT-P5-NEW`, and three `ZT-P5`
      re-adjudications. `ZT-P2-5` (vacuous restatement) closed 2026-07-27 by the
      statement pin. `ZT-P4-1`'s missing anchor checker closed the same day.
      **The remaining backlog was then CLEARED the same day** — `ZT-P1-8` (all five
      sub-items), `ZT-P1-6a`, `ZT-P4-4/4-5/4-6`, the invariants docstring, and both
      orphaned `formal/history/` findings. See the DONE item immediately below for
      what landed, and READ ITS RESIDUALS: three things were deliberately NOT closed
      because closing them honestly was not possible in this pass.
      Sequencing rationale from the original review is at the end of that section.
- [x] **DONE 2026-07-27 — the remaining zero-trust backlog cleared (fixed, pinned,
      gated). Three honest residuals, listed at the end — do not read this as "all
      clear".**
      * **`ZT-P1-8a` — the unlogged write.** `SetEngine` gained a `log_governed` flag;
        `add_tuple`/`remove_tuple` refuse with `UnloggedWriteRefused` when set, and
        `TupleSource` (the sanctioned writer, which appends `TupleLogV1` in the same
        transaction) calls the `_direct` bodies. `TupleSource.engine` is now a
        read-only property over `_engine`. **A flag, not an "is there a log row?"
        probe** — the log is empty on a fresh store, so a probe waves through exactly
        the first bypass. Standalone `SetEngine` (the matrix's `SetBackend`,
        `formal/conformance/backends.py`, benchmarks) is untouched and pinned as such.
      * **`ZT-P1-8b` — freshness on the enumeration surfaces.** `lookup` /
        `lookup_reverse` now take `at_least` and **raise `LookupNotFresh`** rather than
        falling back. That is the honest outcome, not a shortcut: graph `node_ids` are
        `NodeV4` row ids and set-engine ones are recycled instance-local interner ids;
        markers are triples vs pairs; and `excluded_node_ids` (the derived `neg`
        channel) has no set-engine counterpart at all, so a fallback would silently
        change what the return value MEANS depending on worker lag. Worse, in the
        stale-index case the graph node rows for the un-applied tuples do not exist, so
        even a translation bridge is impossible in principle. Unifying the lookup key
        contract is the breaking change `docs/architecture/decision-log.md` round 3
        describes; it was not smuggled in here. Untokened calls are byte-identical.
      * **`ZT-P1-8c` — `processor_writes` thread-scoped** (`_ThreadFlag`), and so is
        the downstream mirror `ReachabilityIndex._writing_derived`, which is the bool
        the row writer actually consults to stamp `EdgeV4.derived` — same shared-object
        defect, found only because the fix forced an audit of every site. A thread that
        never opened the window reads it closed and gets the loud I5 refusal.
      * **`ZT-P1-6a` — per-write closure fan-out cap** (`DEFAULT_MAX_CLOSURE_FANOUT`
        = 100,000, `ZANZIBAR_MAX_CLOSURE_FANOUT`, ctor kwarg, 0 disables). Counted
        before anything is materialised, so a rejection leaves no partial state
        (pinned two ways). **Removals and `remove_node` are exempt on purpose**: a cap
        on shrinking makes an over-large region permanently unshrinkable, and in an
        authorization system a cap that can refuse a REVOCATION is a fail-open.
      * **`ZT-P1-8` retention — `prune_outbox`.** Deletes drained rows only, never
        auto-called. **It always keeps the head row**, and that is not tidiness: `id`
        is the SQLite rowid, so emptying the table restarts ids at 1 and a consumer
        holding cursor 500 would never see the next 500 deltas — silent, permanent
        delta loss on the one dialect CI runs.
      * **`ZT-P4-6` — the third corner, restored where it matters.** `grid.py` now
        derives targets from `zanzibar_utils_v1`, so a misparse in `tests/oracle.py` no
        longer both corrupts the Lean corner AND deletes the query that would expose
        it. Verified grid-identical across all 68 grid-building cases (same sha256).
        `encode.py` still reads through the oracle's parser — stated plainly in
        `CORRESPONDENCE.md` §1 as a per-layer table instead of a blanket claim.
      * **`ZT-P4-5` — the state gate, measured and made honest.** `ResidueV1.version`
        is now declared projection **P7** with its reason (Lean's `Residue` has no
        version field — a MODELLING gap, so I7 is gated by nothing formal, said in as
        many words). `NodeV4`/P5 is quantified rather than waved at: of 235 node rows,
        194 are implicitly pinned as endpoints and **41 are invisible to the gate**.
        New `residue_rich` corpus — the 11 residue rows in the whole state gate all had
        `|stars| == |neg| == 1`, so the comparison had never been asked to tell two
        elements from one.
      * **`ZT-P4-4` — the arity ceiling closed; the strata premise was wrong.** Max
        strata is already **3** and `test_multi_stratum_three_way` already drives the
        real Python cascade there — what is ungated at ≥3 strata is the LEAN model, not
        Python. Arity had stopped at 3 on two untainted nodes, so `_fold_binary`'s loop
        had never run more than twice; `nary_union_derived4` is the first ≥4-arity
        operator anywhere and its high-arity node is derived.
      * **Both orphaned `formal/history/` findings adjudicated** — see
        `formal/HANDOFF.md` § "Board — the two ORPHANED findings". `PDerivedUserset`
        turned up a real hole: across all 69 schemas the harness reads, the plan-leaf
        histogram was `closure 211 · derived-computed 42 · derived-ttu 50 ·
        **derived-userset 0**` — no corpus compiled that leaf at all, in the exact area
        where five real divergences were found. Closed by a new corpus and floored.
      * **`check_invariants` docstring** corrected against the BODY (I1–I7 + I10 + I13),
        with a test that pins the claim and proves the body really enforces I7 and I13.
      **RESIDUALS — read these, they are the part that is not done:**
      1. **The fan-out cap does NOT stop the measured DoS.** Reproduced: 240 tuples →
         14,640 rows, but its peak PER-WRITE fan-out is only 120. It is 240 cheap
         writes, not one expensive one. The cap bounds a single write's lock-hold;
         the N² accumulation needs a **store-level quota**, which was not added.
      2. **≥3-strata Lean coverage — SCOPED 2026-07-27, and the recommendation is
         DON'T.** Full plan:
         [`formal/history/strata-widening-plan-2026-07-27.md`](../../formal/history/strata-widening-plan-2026-07-27.md).
         Measured, not argued: **the Lean model FAILS CLOSED at ≥3 strata** (zcli on
         `three_strata_chain`: `mode=graph` rc 3 "final state not drained"; 2-stratum
         control rc 0) — which **corrects the predecessor doc's claim that it would not
         fail loudly**. So the arc buys COVERAGE, not safety. Python's cascade runs
         `len(strata)` rounds (not to quiescence), so `runCascade2` is the N=2 SLICE of
         the real algorithm — no shape mismatch, and that also rules out a fuel/fixpoint
         formulation as the faithful one. `runCascade3` is the WORST option: the stratum
         count is unbounded (a 12-deep derived chain compiles to 12 strata), so it pays
         nearly the full re-proof to move the wall from 3 to 4. Cost of the real thing:
         7 legs, ~8 sessions, ~3,000+ Lean lines, ~24% genuine re-proof / ~76%
         re-statement, with the risk concentrated in the read-bridge leg (Leg 3) whose
         shape was already attack-refuted once. It unblocks nothing else on the board.
         **If a session is spent on Lean, spend it on the E-chain Direct-arm widening
         instead** — there the headline theorems are VACUOUS on `[user] but not blocked`
         (`ZT-P3-1`), and vacuous beats narrow as a thing to fix.
      3. ~~**Still at zero coverage anywhere:** wildcard usersets `[T:*#p]`, and the
         `derived-tupleset-ttu` plan leaf — deliberately left OUT of the new
         plan-leaf-coverage floor rather than faked.~~ **CLOSED 2026-07-28** (board
         item (C) above): both reachable, both corpus'd spec-side + python-only
         3-backend, floor raised to every kind `_plan_leaves` emits. The
         wildcard-userset surface is narrower than the finding read — over a DERIVED
         relation it is a compile-time scope rejection and cannot be a corpus.
      Also unbenchmarked (unchanged): `_any_residue_reference`'s complete `ResidueV1`
      scan on every node-release path, now unconditional after the `ZT-P0-1` fix.
      **Next actions:** promoted to the ★ START HERE item at the top of Active work.
- [x] **DONE 2026-07-23 (Claude): multi-instance set-engine (HA) support — landed, gated, pushed.**
      See the 2026-07-23 Current-status bullet for the full record (mechanisms, the
      closed log-ordering hazard, consistency model, gate numbers). Follow-ups
      deliberately NOT taken (out of scope, revisit on need): `at_least` on
      lookup/expand surfaces (rationale + implementation sketch in
      `docs/architecture/decision-log.md` round 3 — the blocker is unifying the
      lookup result contract on portable keys, not the token mechanics); snapshot
      ("at exactly") reads; cross-store tokens (X6); set-engine state snapshots
      for O(delta) cold start.
- [ ] **IN PROGRESS 2026-07-18 (Claude): OPTIONAL assurance-widening arc (`FINAL_REVIEW.md §4`).**
      Four targets scoped (recon + attack-first probes); durable design + resume state for
      ALL of them in [`formal/history/optional-widening-2026-07.md`](../../formal/history/optional-widening-2026-07.md).
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

- [x] ~~**★ HIGHEST-VALUE UNTESTED SURFACE — no MySQL or PostgreSQL has EVER been run
      against this repo (recorded 2026-07-26)**~~ — **CLOSED 2026-07-27, and it was NOT
      merely unverified: the leg found a live authorization fail-open.** `scripts/pg_local.sh`
      stands up a throwaway PostgreSQL 17.10 and `tests/test_postgres_ha.py` drives the
      scenarios SQLite cannot express (`psycopg2-binary` in `requirements.txt`, needed only
      for this leg; `ZANZIBAR_TEST_DSN` also re-runs `tests/test_concurrency.py` and the
      connected-store concurrency/multi-instance modules). VERIFIED: `FOR UPDATE` really
      blocks and is row-granular, lock ordering holds, 4 concurrent writers give contiguous
      exactly-once log rows plus an index equal to a single-writer replay, and
      `log_gap`/`WatermarkGap` fire on a genuine out-of-order commit. FALSIFIED:
      `SERIALIZABLE` was accepted on a false premise and reproduced a revoked grant
      certified ALLOWED under an explicit token; `log_gap`'s `FOR SHARE` soundness argument
      was an InnoDB fact about an unsupported database; `assert_read_isolation` never ran on
      the public `TupleSource` path; and "a replica never sees torn state" is a SQLite-WAL
      inheritance that does not exist at PostgreSQL READ COMMITTED. Also decided: **MySQL is
      not a supported backend** (SQLite dev/test + PostgreSQL server; `READ COMMITTED` only).
      Full record: `docs/spec-deviations.md` 2026-07-27. Residual: ONE strict xfail,
      tracked separately below.
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
