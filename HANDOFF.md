# HANDOFF — the board

The **priority view of every open item in this repo**, `formal/` included, and the only
file that ranks them. Formal *execution* state — what is proved, what the next lemma is —
lives in [`formal/HANDOFF.md`](formal/HANDOFF.md), and any formal item's read-first list
starts there. Durable rules, the gate, the env and the standing footguns are in
[`CLAUDE.md`](CLAUDE.md) (auto-loaded every session); doc conventions — liveness states,
the signal legend, citation keys — are in [`docs/README.md`](docs/README.md).

**A user-assigned task overrides this board.** Do not re-rank at session start: work the
task, then re-rank once at write-back. `NOW` means "what I would recommend an unassigned
session pick up", not "what I am doing".

Read this file fully plus `CLAUDE.md`, then **only your item's read-first list**. End of
session: run the Rhythm protocol at the bottom.

## Banner

> 🟢 **All ten gate phases green on this tree (2026-08-29)** — `lean` +
> `conf-tile:1..5/5` + `tests-tile:1..4/4`; tiles keyed to the code-scoped tree id (`*.md`
> excluded), and `lean` was re-run after the last `*.md` edit.
> ⏰ **`2026-08-29b`: trial question (b) is decided** — every open `TK*` id is bucketed
> ([adjudication](docs/history/tk-findings-adjudication-2026-08-29.md)); the refutation pass
> overturned 6 of 11 proposed write-offs. Unlanded appends → **`TK53`**, the row that makes
> DELETE lossless. 🧭 **Question (a) — delete the tool or keep it — is the user's call and
> is not made here**; evidence + recommendation in ledger `2026-08-29b`. `sync` **clean**.
> **`2026-08-28d`: `P14` settled.** **Next: 4c-ii + step 7, the un-splittable cone — read its
> revert-to-green exit (scope doc §11.12) first.** → PROOF_STATUS `2026-08-28c` §5.
> **"Known live correctness bugs: 0"** stands (`BL-2` fixed and pinned 2026-08-21b). Ask
> `python scripts/gate_status.py`, never this line. Red is yours: `git stash`.

## Board

Priority is a word, and the top two are capacity-bounded: `NOW` = exactly 1, `NEXT` ≤ 3.
`LATER` / `HOLD` / `SOMEDAY` are unbounded. Legend and budgets:
[`docs/README.md`](docs/README.md) §4. `deps` names **open** rows only — closing a row
sweeps its id out of every `deps` cell. `moved` is the last date a session progressed or
re-ranked the item, so an old date on a `NOW`/`NEXT` row means neglect. **Ids carry
forward forever and are never reused.**

| id | item (→ pointer) | pri | size | deps | moved |
|---|---|---|---|---|---|
| `P3` | leg 7 **4c-ii + step 7, one commit** — fence layer landed 2026-08-28b; **public surface MIGRATED 2026-08-28c** (7 decls + zcli driver onto `checkPublic`, no new hypotheses; `hql` surface cut from 6 rows to **1**, `graph_correct` `:27`). Everything pre-4c-ii is now DONE, **`P14`'s `UntaintedShadow` adjudication included (2026-08-28d: Route B = one disjunct on one field; the `writeRulesRaw` endpoint-closure risk retired; `slSwD_not_mono` shown to measure the wrong σ0)**. **What remains is the un-splittable 42-module cone** — measured 3 sessions, not 1 (PROOF_STATUS `2026-08-28c` §5), and its **revert-to-green exit is now declared in the item block: read it before opening** | **NOW** | L | — | 2026-08-28d |
| `P6` | `ttuStarFree` **(ii)** — bridges on the rule-routed write path; **NOT parallel-safe with `P3`** (same 38-module cone, corrected 2026-08-20b) | **NEXT** | M | — | 2026-08-20b |
| `R6` | perf round 6 — **`R6-10` landed 2026-08-20b (2.54×), `R6-6` landed 2026-08-24d (4.75 → 1.75 statements/`check`)**; 10 to land, 4 declined, 3 unreachable (re-counted from the children 2026-08-24d, and **the task tree was re-counted to match 2026-08-29** — it had carried the stale `11` for five days) → [profile](benchmarks/results/R6_PROFILE_2026-08-17.md) | **NEXT** | L | — | 2026-08-29 |
| `TK53` | **land the adjudicated `TK*` appends** — question (b) of the trial verdict is DECIDED (→ [adjudication](docs/history/tk-findings-adjudication-2026-08-29.md)) and the appends are the unlanded half. Each is a statement that exists only in `tasks/` and has a named destination in a living doc. **This row is what makes DELETE lossless** — until it closes, deleting `tasks/` drops statements that no living doc carries. `TK52` closed on the decision; this carries the execution, so the decision is not a residual with no owner | **NEXT** | M | — | 2026-08-29b |
| `P4` | leg 7 **4b** — leaf-probe ↔ `directLeaf` bridge → [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §7 | LATER | M | `P3` | 2026-08-16 |
| `P5` | `Inv.negEdgeFree` under leaf routing; retire the T2a caveat → [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §9.1–9.3 + §7 step 6 | LATER | M | `P4` | 2026-08-16 |
| `P7` | `ttuStarFree` **(iii)+(iv)** — re-prove the 5 consumed sites, widen the gate → [`PROOF_STATUS.md`](formal/history/PROOF_STATUS.md) 2026-08-16 | LATER | M | `P6` | 2026-08-16 |
| `P14` | leg 7 **step 5, reach-collapse half ONLY** — the classification half (re-partition `DerNode`/`UntaintedShadow`) was **absorbed into `P3` on 2026-08-20b** under Route B, which is what breaks the old `P3 → P14 → P4 → P3` cycle → [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §5 + §7 step 5, and §11.9 for the split | LATER | M | `P4` | 2026-08-20b |
| `P8` | write `W4WitnessSelfRef` (board `B2`) → [`PROOF_STATUS.md`](formal/history/PROOF_STATUS.md) 2026-08-08 §6 | LATER | S | — | 2026-08-16 |
| `P9` | lift the remove-gate exclusion (board `B2`) → `formal/conformance/test_conformance_remove_graph.py` | LATER | M | — | 2026-08-16 |
| `P10` | re-run the scope audit, hand-curated → [fan-out runbook](docs/subagent-fanout-runbook.md), final § | LATER | M | — | 2026-08-16 |
| `P11` | the fixture-TRIPLE question for 5 subsumed `.fga` fixtures → `tests/test_schema_shapes.py::KNOWN_SUBSUMED` | LATER | S | — | 2026-08-16 |
| `P12` | severity-sign revert probe → [`spec-deviations.md`](docs/spec-deviations.md) 2026-08-10 entry | LATER | S | — | 2026-08-16 |
| `HS-5` | always-living docs declare no liveness state, though [`docs/README.md`](docs/README.md) §2 requires one in the first lines. **The enumeration and the measuring method now live in `docs/README.md` §2 itself**, re-measured 2026-08-29; what is open is the adjudication — which docs are deliberately exempt. **No count here, and none in §2 either**: it has read differently on every one of four readings → ledger `2026-08-29b` | LATER | S | — | 2026-08-29b |
| `P13` | `CORRESPONDENCE.md` claim-rot gate → [design](formal/history/claim-rot-gate-design-2026-08-16.md) | LATER | M | — | 2026-08-16 |
| `AW-1` | `FINAL_REVIEW.md` §4(d) under-claims after the remove leg → that item's own dated note | LATER | S | — | 2026-08-16 |
| `P15` | the remaining fragment leaves — `PDerivedTTU` arms, and the `twoStrata` cap → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(c)(ii) + §3.1 item 3 | LATER | L | — | 2026-08-16 |
| `P16` | widen the enumeration/state bounds → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(e); read `test_conformance_enum.py`'s module docstring, which is half the plan | LATER | M | — | 2026-08-16 |
| `P17` | bulk build/backfill is an unmodeled **default** constructor — model it or scope-exclude it in writing → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(h) + §3.1 item 6 | LATER | M | — | 2026-08-16 |
| `LT-1` | the two live latent residues → [`latent-gaps.md`](docs/latent-gaps.md) "Target 2" / "Target 3" | HOLD | ? | — | 2026-08-20b |
| `DW-1` | decidable `W4Fragment` for a driver-side pre-check → [`CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) §"Conformance gates" | SOMEDAY | ? | — | 2026-08-16 |
| `P18` | the concurrency / multi-instance layer — the never-started TLA+ phase → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(i) + §3.1 item 5 | SOMEDAY | L | — | 2026-08-16 |
| `P19` | model the read surfaces (`lookup` / `lookup_reverse` / `expand`) in Lean → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(g) | SOMEDAY | L | — | 2026-08-16 |
| `SD-1` | lift the two scope rejections → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(j) | SOMEDAY | L | — | 2026-08-16 |
| `SD-2` | a real service wrapper — deliberately skipped; the store is a plain callable API | SOMEDAY | L | — | 2026-08-16 |
| `SD-3` | tuple-log compaction — only if the log outgrows "humans wrote this" scale | SOMEDAY | S | — | 2026-08-16 |
| `SD-4` | bulk-merge write path → [sketch](docs/architecture/bulk-merge-design.md) | SOMEDAY | L | — | 2026-08-16 |

Closed ids stay retired: `P1`, `P2`, `HS-1`, `HS-3` (all done 2026-08-16), `GS-1`, `BL-1` (2026-08-21), `BL-2` (2026-08-21b),
`HS-4` and `GS-2` (2026-08-17), `HS-2` (2026-08-20b), `TK52` (2026-08-29b), `B1`, and the whole `ZT-*` zero-trust series. `B2` survives as the historical grouping of `P8` + `P9`.
`B1`'s underlying finding was verified closed on 2026-08-16 (both halves proved 2026-07-28
and 2026-08-04; the record had simply never caught up) — evidence in `formal/HANDOFF.md`'s
`B1` block. Retiring an id is not the same act as closing a finding: say which you mean —
`BL-1` is both (fixed 2026-08-21; pins green), as is `BL-2` (filed AND fixed 2026-08-21b;
its six pins in `tests/test_reg18_leaf_name_read_leak.py` stay green as regression guards).
⚠ **Do not reflow those two `Closed ids` lines.** `handoff_lint.py::check_ledger_ids`
harvests retired ids LINE BY LINE (only lines carrying `Closed ids stay retired` or
`survives as the historical grouping` are read), so rewrapping moves ids out of scope —
**and the FAILs then blame the LEDGER's citations, not this rewrap**. Observed 2026-08-21:
one reflow produced six FAILs for ids that were retired the whole time. If this check fails
on ids you never touched, `git diff HANDOFF.md` before believing the message.

## Item blocks — `NOW` and `NEXT` only

These blocks have **replace** semantics: if you touch the item, rewrite its block,
read-first list included. Rows below `NEXT` deliberately get no block — their pointer
target is self-sufficient by construction (verified row by row, 2026-08-16).

### `P3` — leg 7: step 4c-ii co-landing with step 7, in one commit

Re-point the rule-routed write path onto leaf-indexed targets and retire projection `P6`
in the same commit. Critical path.

✅ **Everything pre-4c-ii is done, `P14` included.** Both human calls made (2026-08-28):
`hql` accepted as `publicOfLeaf S q.object.type q.relation = none`, Route B retained on
corrected grounds (scope doc **§11.11**, superseding §11.9's sizing). Fence built and the
public surface migrated onto it, so the `hql` guard is one declaration, not 8
(`graph_correct` `:27`). Cone measured **42 modules / ~136 sites / 90-raw second ring over
8 files** — the first sizing in four to correct upward, so do not re-cite lower figures —
and **sized at 3 sessions, not 1** (PROOF_STATUS `2026-08-28c` §5). Still to write: the
unowned superset-extras lemma (`reachedByW3d_shadow`) and `LeafNode`.

✅ **`P14` settled (2026-08-28d), and it moved the answer.** Route B's weakening is one
disjunct on one field, and the never-probed `nodesSub`/`closed`/`closed0` hold everywhere,
so 4c-ii owes no `writeRulesRaw` endpoint-closure edit. ⚠ **`slSwD_not_mono` measures the
wrong σ0** — `reachedByW3d2_shadow_d` builds σ0 over the *filtered* store, so the real σ0
is `emptyState` and against it the strong shadow is uninhabited (PROOF_STATUS
`2026-08-28d` §1–3). **Revert-to-green exit: scope doc §11.12** — load-bearing rules: the
green anchor is a **commit sha** logged before the cone opens, and **no partial cone is
committed**, a mid-cone tree being one whose own pins assert something untrue.

⚠ **Traps: scope doc §11.10 AS CORRECTED BY §11.11 item 8** — 7 order-sensitive own-key
sites (4 `rw`-discharges + 3 positional), the emptiness bites at `rawWriteRels` not
`atomLeaves`, the non-emptiness premise is `StoreValidRulesD`, `FoldAdmits` = 19 Prop
sites + 2 exec gates move / 3 stay (`RulesComplete.lean:91`, `RestrictBase.lean:470`,
`:531` stay). **It cannot be split** — the un-buildable window is the whole cone; do not
open it at the tail of a session.

**Read first:** scope doc **§11.11**, PROOF_STATUS `## Session 2026-08-28`, then
`2026-08-21b` / `2026-08-20b`, §11.9, **§11.10 (the traps)**,
`GraphIndex/Scratch4cii.lean`; completion criterion: PROOF_STATUS `2026-08-16c`, its
numbers re-derived from `formal/FINAL_REVIEW.md`'s generated ledger, never prose. Then
`CascadeStable.lean::shadow_graphRec_agree` / `::reachedByW3d_shadow`,
`ReconcileStars.lean::checkFn_agree_of_graphRec`, `LeafRules.lean::GraphState.writeRulesRaw`,
`Leaf.lean::publicOfLeaf`, `Exec.lean::foldAdmitsB`, `extractor.py::_edge_projection`.

### `TK53` — land the adjudicated `TK*` appends

Each append is one statement that exists nowhere but `tasks/`. Until this closes, deleting
`tasks/` drops statements no living doc carries. **Read first:**
[the adjudication](docs/history/tk-findings-adjudication-2026-08-29.md) — its table, its
four traps, its "Method" § (the refutation pass overturned 6 of 11, so a single-pass sweep
of the remainder will not do); then [the snapshot](docs/history/tasktool-findings-2026-08-29.md).

### `P6` — `ttuStarFree` part (ii): bridges on the rule-routed write path

Materialise the in-bridge on the rule-routed write path so the widened star-freeness
predicate is actually inhabited.

⚠ **"It can run in parallel with `P3`" was WRONG, and this row carried it for weeks**
(corrected 2026-08-20b). Logically independent, **textually colliding**: both re-point
`RulesWrite.lean::writeRules` and `Cascade.lean::writeLoggedOne`, both move `FoldAdmits` +
`Exec.lean::foldAdmitsB` in lockstep, and **both pay the same 38-module cone** — whichever
lands second re-pays it. Land increment A (additive, zero-cone) and stop, or sequence B
after `P3`; never concurrently. **Probe with `#eval` before paying the cone, exactly as
`P3` did**: `CascadeStable.lean`'s `writeLeg_reach_stable` family says a write leg does not
change reachability at these nodes, and **an in-bridge DOES change reachability — that is
its purpose**, so those statements may go FALSE at a bridged state rather than merely
needing a new case. The change is also **INERT on every corpus** (measured 2026-08-20:
`bridged_in_shapes` empty on all 26 `corpus.SCHEMAS` and every extended set bar one,
fragment-excluded), so the gate cannot see it and all evidence must be new Lean pins —
[`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) §"The INERT change" governs, as
for part (i). Increment B also **inverts
`extractor.py::_edge_projection`'s `P2` projection** (it drops PYTHON `w_any` rows because
"Lean never creates them"); its docstring is already false. Detail: ledger `2026-08-20b`.

⚠ **DO NOT DROP IT.** Without `ttuStarFree`, `graph_correct` and `backend_equivalence` are
machine-checked **FALSE** — not merely unproven. Part (i) is **INERT**: part (ii)
materialises the edge, and the rest of the leg is inert until it lands.
`W4Fragment.ttuStarFree` must stay **UNCHANGED** until (ii) is in.

**Read first:** `formal/CORRESPONDENCE.md` §7 (`ZT-P5-NEW`);
`UsStarWrite.lean::Schema.isStarTuplesetThrough` / `::Schema.isSubjectWildcardUserset`;
`ensureInBridges` / `ensureBridges`; `writeRules` / `writeLoggedRules`; `derive_schema_info`'s
second loop.

### `R6` — perf round 6: `R6-10` and `R6-6` landed, ten remain (re-counted 2026-08-24d)

**`R6-10` landed 2026-08-20b** (both steps): `−60.7%` incremental boolean write wall,
**2.54×**, SQL statements/cycle `1929 → 822`.
**`R6-6` landed 2026-08-24d** at exactly its predicted **4.75 → 1.75** statements per
`check` (`−63.2%`). ⚠ **Take its one deviation as the pattern for `R6-5`/`R6-4`/`R6-9`:**
the audit's sketch said "a fresh per-call query, not a cache", but every read-path batching
item in this round has a cascade caller behind it (`_EvalContext.leaf_check`) where that
would replace warm N15 cache hits with SQL — so batch *through* the cache, not past it.
Remaining order: `R6-11` → `R6-5` (**32.7%** ORM construction for 3–4 columns) →
`R6-4` → `R6-9` → `R6-18` (**53.1%** off the biggest table; owes a hand PG migration) →
`R6-16` → `R6-7`+`R6-8` → `R6-1`.

**Declines and the unreachable three are the audit's verdict tables**, whose banner was
corrected 2026-08-29b (`TK48`) to carry no count and point at them — read them there, and
do not restate a split here. `R6-19` owns the last unowned number (25.4% cum, **self
2.0%** — a call-site fan-out; the old `25.3%` paired two passes, which no source states).

⚠ **Five traps the numbers do not carry** live in
[`perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) §"Traps the numbers do
not carry", demoted there 2026-08-20b, and both that day's corrections were applied
2026-08-21 (`R6-11`'s size, `R6-4(a)`'s unsound memo) in the entries themselves.
**Read that section before taking an id** — count its bullets, do not trust this line.

**Read first:** [`R6_PROFILE_2026-08-17.md`](benchmarks/results/R6_PROFILE_2026-08-17.md)
(verdicts, method, the two limits — in-memory SQLite understates statement-count wins,
cProfile depresses throughput — and its three instrument corrections, whose transferable
rule is [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) §"A MEASUREMENT is an
assurance step too" and binds any re-run), then your id's entry in
[`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) **including its
verifier corrections**, then [`docs/perf-next-round.md`](docs/perf-next-round.md) for the
fence and the reopening rule. Re-run with `python -m benchmarks.profile_r6 [_write]
--target <t>` — never beside another bench or pytest run.

## Standing traps

Cross-item only. Everything durable and repo-wide lives in `CLAUDE.md` instead.

* ⚠ **Do NOT lift `ttuDirect` in Lean.** It is load-bearing for the current admission
  story; the open descendant is row `DW-1`, and nothing is blocked meanwhile.
* ⚠ **Status lines inside `docs/history/` and `formal/history/` are frozen as-of-then**,
  and several are known false. Read them for method, never for state.

## Where things live

| doc | what it is | when to read |
|---|---|---|
| [`CLAUDE.md`](CLAUDE.md) | durable rules: env, the gate, layout, testing conventions, invariants, the four footguns | every session (auto-loaded) |
| [`docs/README.md`](docs/README.md) | doc-system conventions: liveness, banners, ledger format, citation keys, signals | before restructuring any doc |
| [`docs/history/session-log.md`](docs/history/session-log.md) | the root session ledger, newest first | top entry at session start; write one every session |
| [`docs/gate-runbook.md`](docs/gate-runbook.md) | cap-safe phased `verify.sh`, the Postgres leg, fuzz, every floor and budget | before running the gate |
| [`tests/dbengine.py`](tests/dbengine.py) | the SQLite-vs-server engine seam (`ZANZIBAR_TEST_DSN` / `ZANZIBAR_PG_REQUIRED`) | running the PostgreSQL leg |
| [`docs/architecture/overview.md`](docs/architecture/overview.md) | architecture index — module map plus pointers to every deeper doc | orienting in unfamiliar code |
| [`docs/spec-deviations.md`](docs/spec-deviations.md) | the dated divergence ledger — append-only, true as of each date key, never live status | when behaviour surprises you |
| [`docs/latent-gaps.md`](docs/latent-gaps.md) | what is still latent **today**; rewritten in place | before chasing a gap you found in the ledger |
| [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) | how to prove a check actually checks; the catalogue of checks that failed by passing | before adding any test, floor, pin or gate phase |
| [`docs/subagent-fanout-runbook.md`](docs/subagent-fanout-runbook.md) | how to run a multi-agent sweep without wasting it | before launching a fan-out |
| [`docs/perf-next-round.md`](docs/perf-next-round.md) | perf fence, dead ends, hygiene, the reopening rule | before any perf work |
| [`docs/specs/`](docs/specs/) | the original design specs, cited by code as "spec §N" | when a code comment cites one |
| [`formal/HANDOFF.md`](formal/HANDOFF.md) | the formal subtree's execution state and house rules | before touching `formal/` |
| [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) | the model↔Python map; §7/§8 record algorithm drift | when changing a modeled algorithm |
| [`formal/FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) | the governing claim doc — and **the only home for live counts** (generated block) | whenever you need a figure |
| [`benchmarks/results/PERF_ANALYSIS.md`](benchmarks/results/PERF_ANALYSIS.md) | measured perf numbers per landed item | assessing a perf candidate |
| [`docs/history/`](docs/history/) · [`formal/history/`](formal/history/) | retired records and the append-only ledgers. [`handoff-status-2026-07.md`](docs/history/handoff-status-2026-07.md) holds the reconciled **`ZT-*` disposition ledger** | for method and provenance — **never for state** |

## Rhythm

The end-of-session write-back. Steps 0–3 are the **mandatory floor**; if context runs
short, list every skipped step-4/5/6 action *verbatim* under `Still owed:` and the next
session executes it before its own work. A skip that leaves no trace is how the last
accretion started.

0. **Run `python scripts/handoff_lint.py`** before committing any board edit.
1. **Append one entry to [`docs/history/session-log.md`](docs/history/session-log.md)** —
   every session, no exceptions. Ledger first, so the banner has a key to cite.
2. **Rewrite the Banner**: gate state as observed, today's date, the new headline, and the
   entry key you just created.
3. **Edit the board in place.** Flip `pri`; touch `moved` on every row you worked, not
   only the ones you re-ranked; delete closed rows **and sweep their ids out of every
   `deps` cell**; rewrite the item block of every touched `NOW`/`NEXT` item, read-first
   list included.
3b. **Do not restate gate counts in prose.** They live in `formal/FINAL_REVIEW.md`'s
   generated block and are machine-checked by `verify.sh` step 4e; regenerate with
   `python -m formal.conformance.doc_counts --generate`. This file went stale three
   separate times by keeping its own copies (`ZT-P3-5`).
4. **File method lessons in their runbook now** — the ledger entry summarises and points.
5. **Fix wrong docs in place now.** Living doc → edit it; FROZEN or ACTIVE-PLAN → append a
   dated correction at the top. **This board never hosts a correction to another doc.**
6. **New traps** → the owning item's block, or `CLAUDE.md` if durable and repo-wide.

Before starting anything: `bash formal/verify.sh lean` should be green in ~60 s warm. If
it is not, fix that first — it is the fastest signal in the repo.
