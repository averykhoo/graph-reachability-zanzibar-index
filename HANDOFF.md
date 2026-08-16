# HANDOFF — the board

The **priority view of every open item in this repo**, `formal/` included, and the only
file that ranks them. Formal *execution* state — what is proved, what the next lemma is —
lives in [`formal/HANDOFF.md`](formal/HANDOFF.md), and any formal item's read-first list
starts there. Durable rules, the gate, the env and the standing footguns are in
[`CLAUDE.md`](CLAUDE.md) (auto-loaded every session); doc conventions — liveness states,
the signal legend, citation keys — are in [`docs/README.md`](docs/README.md).

**A user-assigned task OVERRIDES this board.** Do not re-rank at session start: work the
task, then re-rank once at write-back. `NOW` means "what I would recommend an unassigned
session pick up", not "what I am doing".

Read this file fully plus `CLAUDE.md`, then **only your item's read-first list**. End of
session: run the Rhythm protocol at the bottom.

## Banner

> 🟢 **The gate is green. Known live correctness bugs: 0.**
> As of **2026-08-16**: all ten phases PASSED on the leg-7 4c-i tree, and everything since
> has been documentation plus one new standalone script — no Python behaviour changed, so
> the 2026-08-14 3-seed fuzz sweep still stands.
> Last session: **the handoff-system migration — this board, the session ledger and
> `scripts/handoff_lint.py` all landed** →
> [`docs/history/session-log.md`](docs/history/session-log.md) `2026-08-16c`.
> If you see red, it is yours: `git stash` and re-check.

## Board

Priority is a word, and the top two are capacity-bounded: `NOW` = exactly 1, `NEXT` ≤ 3.
`LATER` / `HOLD` / `SOMEDAY` are unbounded. Legend and budgets:
[`docs/README.md`](docs/README.md) §4. `deps` names **open** rows only — closing a row
sweeps its id out of every `deps` cell. `moved` is the last date a session progressed or
re-ranked the item, so an old date on a `NOW`/`NEXT` row means neglect. **Ids carry
forward forever and are never reused.**

| id | item (→ pointer) | pri | size | deps | moved |
|---|---|---|---|---|---|
| `P3` | leg 7 **4c-ii + step 7, one commit** → [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §11.7 | **NOW** | L | — | 2026-08-16 |
| `P6` | `ttuStarFree` **(ii)** — bridges on the rule-routed write path | **NEXT** | M | — | 2026-08-16 |
| `R6` | perf round 6 — **measure before landing anything** → [audit](docs/perf-round6-audit-2026-08.md) | **NEXT** | L | — | 2026-08-16 |
| `HS-1` | wire `scripts/handoff_lint.py` into `verify.sh` → [design](docs/handoff-redesign-2026-08.md) §8 | **NEXT** | S | — | 2026-08-16 |
| `P4` | leg 7 **4b** — leaf-probe ↔ `directLeaf` bridge → [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §7 | LATER | M | `P3` | 2026-08-16 |
| `P5` | `Inv.negEdgeFree` under leaf routing; retire the T2a caveat → [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §9.1–9.3 + §7 step 6 | LATER | M | `P4` | 2026-08-16 |
| `P7` | `ttuStarFree` **(iii)+(iv)** — re-prove the 5 consumed sites, widen the gate → [`PROOF_STATUS.md`](formal/history/PROOF_STATUS.md) 2026-08-16 | LATER | M | `P6` | 2026-08-16 |
| `P14` | leg 7 **step 5** — re-partition `DerNode`/`UntaintedShadow`, re-prove the reach-collapse family → [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §5 + §7 step 5 | LATER | L | `P4` | 2026-08-16 |
| `P8` | write `W4WitnessSelfRef` (board `B2`) → [`PROOF_STATUS.md`](formal/history/PROOF_STATUS.md) 2026-08-08 §6 | LATER | S | — | 2026-08-16 |
| `P9` | lift the remove-gate exclusion (board `B2`) → `formal/conformance/test_conformance_remove_graph.py` | LATER | M | — | 2026-08-16 |
| `P10` | re-run the scope audit, hand-curated → [fan-out runbook](docs/subagent-fanout-runbook.md), final § | LATER | M | — | 2026-08-16 |
| `P11` | the fixture-TRIPLE question for 5 subsumed `.fga` fixtures → `tests/test_schema_shapes.py::KNOWN_SUBSUMED` | LATER | S | — | 2026-08-16 |
| `P12` | severity-sign revert probe → [`spec-deviations.md`](docs/spec-deviations.md) 2026-08-10 entry | LATER | S | — | 2026-08-16 |
| `P13` | `CORRESPONDENCE.md` claim-rot gate → [design](formal/history/claim-rot-gate-design-2026-08-16.md) | LATER | M | — | 2026-08-16 |
| `HS-2` | split [`docs/spec-deviations.md`](docs/spec-deviations.md) (user-scheduled 2026-08-16) | LATER | M | — | 2026-08-16 |
| `HS-3` | `formal/HANDOFF.md` **deep half** = redesign [§9 step 12](docs/handoff-redesign-2026-08.md), scoped in its §7 | LATER | M | — | 2026-08-16 |
| `AW-1` | `FINAL_REVIEW.md` §4(d) under-claims after the remove leg → that item's own dated note | LATER | S | — | 2026-08-16 |
| `LT-1` | the two live latent residues → [`spec-deviations.md`](docs/spec-deviations.md) Target 2 / Target 3 | HOLD | ? | — | 2026-08-16 |
| `DW-1` | decidable `W4Fragment` for a driver-side pre-check → [`CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) §"Conformance gates" | SOMEDAY | ? | — | 2026-08-16 |
| `SD-1` | lift the two scope rejections → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(j) | SOMEDAY | L | — | 2026-08-16 |
| `SD-2` | a real service wrapper — deliberately skipped; the store is a plain callable API | SOMEDAY | L | — | 2026-08-16 |
| `SD-3` | tuple-log compaction — only if the log outgrows "humans wrote this" scale | SOMEDAY | S | — | 2026-08-16 |
| `SD-4` | bulk-merge write path → [sketch](docs/architecture/bulk-merge-design.md) | SOMEDAY | L | — | 2026-08-16 |

Closed ids stay retired: `P1`, `P2` (both done 2026-08-16), `B1`, and the whole `ZT-*`
zero-trust series. `B2` survives as the historical grouping of `P8` + `P9`.

## Item blocks — `NOW` and `NEXT` only

These blocks have **replace** semantics: if you touch the item, rewrite its block,
read-first list included. Rows below `NEXT` deliberately get no block — their pointer
target is self-sufficient by construction (verified row by row, 2026-08-16).

### `P3` — leg 7: step 4c-ii co-landing with step 7, in one commit

Re-point the rule-routed write path onto leaf-indexed targets and retire projection `P6`
in the same commit. This is the critical path and the only multi-session phase.

⚠ **It CANNOT be split.** Projection `P6` is a Python-side-only filter, so re-pointing
`Exec.lean` alone makes the state gate report roughly seventy leaf edges as "only in LEAN
model". Scope doc §7's "each step green and pushable" is refuted at this step.
⚠ Keep **`d.leaf = true` as the LEADING conjunct** of the own-key guard — three
`rw [hleaf]; simp` discharges depend on that order. Expect a deliberate golden regen.

**Completion criterion:** `dropped by P6` falls to **0**, and `compared against Lean` rises
by exactly that many. **Re-derive both numbers from `formal/FINAL_REVIEW.md`'s generated
projection ledger, never from prose** — this criterion has gone stale three times.

**Read first:** scope doc §11.7 (the current plan), then §11.5 (the decided fork) and
§11.1; `formal/history/PROOF_STATUS.md` `## Session 2026-08-16`;
`Cascade.lean::GraphState.writeLoggedOne`, `RulesWrite.lean::GraphState.writeRules`,
`LeafRules.lean::GraphState.writeRulesRaw`, `Leaf.lean::publicOfLeaf`,
`Exec.lean::foldAdmitsB`, `extractor.py::_edge_projection`.

### `P6` — `ttuStarFree` part (ii): bridges on the rule-routed write path

Materialise the in-bridge on the rule-routed write path so the widened star-freeness
predicate is actually inhabited. Independent of `P3`–`P5`; it can run in parallel.

⚠ **DO NOT DROP IT.** Without `ttuStarFree`, `graph_correct` and `backend_equivalence` are
machine-checked **FALSE** — not merely unproven. Part (i) is **INERT**: part (ii) is what
materialises the edge, and everything else in the leg is inert until it lands.
`W4Fragment.ttuStarFree` must stay **UNCHANGED** until (ii) is in.

**Read first:** `formal/CORRESPONDENCE.md` §7 (`ZT-P5-NEW`);
`UsStarWrite.lean::Schema.isStarTuplesetThrough` and `::Schema.isSubjectWildcardUserset`;
`ensureInBridges` / `ensureBridges`; `writeRules` / `writeLoggedRules`; the second loop of
`derive_schema_info`.

### `R6` — perf round 6: the measurement pass

Eighteen adversarially-verified findings and sixteen unverified leads exist. **Nothing has
landed and nothing is measured.** The round's next act is measurement, not implementation.

⚠ **Do not implement from titles alone — read each entry's verifier corrections.** One
finder's fix was REFUTED by counterexample while its finding stood (`R6-1`: the naive
shared memo is a correctness bug; the two-tier design in its verdict is the fix). Per the
reopening rule every item owes a motivating measurement first — round 5 declined two
plausible candidates on a fresh profile. `R6-2/4/16` change modeled algorithms (Lean twin
or `CORRESPONDENCE.md` §7, plus fuzz); `R6-7/8` rewrite assurance checkers, so they need
re-sabotaging.

**Read first:** [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md)
in full, then [`docs/perf-next-round.md`](docs/perf-next-round.md) for the fence, the
confirmed dead ends and the reopening rule.

### `HS-1` — wire `scripts/handoff_lint.py` into `verify.sh`

The lint exists and runs standalone; it is **not** in the gate, so Rhythm step 0 is a
manual habit today. This row wires it in and adds the fancier checks the design lists:
bold-caps outside trap lines, `moved`-vs-ledger cross-validation, newest-session-log ≥
newest-`PROOF_STATUS`.

⚠ A new gate phase means the **full ten-phase re-run**, not just the phase it adds — and
every check you add needs its own sabotage run per
[`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) before you believe it.

**Read first:** [`docs/handoff-redesign-2026-08.md`](docs/handoff-redesign-2026-08.md) §8;
`scripts/handoff_lint.py`'s own header, which records why each ceiling has the value it
has; [`docs/gate-runbook.md`](docs/gate-runbook.md) for how phases are structured.

## Standing traps

Cross-item only. Everything durable and repo-wide lives in `CLAUDE.md` instead.

* ⚠ **Do NOT lift `ttuDirect` in Lean.** It is load-bearing for the current admission
  story; the open descendant is row `DW-1`, and nothing is blocked meanwhile.
* ⚠ **`.scratch/` is gitignored — anything recorded only there is already lost.** Row
  `P7`'s entire cost analysis survived only in `.scratch/` and had to be transcribed into
  `PROOF_STATUS.md` on 2026-08-16 to keep the item resumable at all.
* ⚠ **A trap must cite a symbol that exists.** This board carried "do not extend
  `test_fixture_earns_its_place`" for weeks; no such test has ever existed, so the trap was
  unenforceable. Cite `file::symbol`, and grep it before you write it down.
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
| [`docs/spec-deviations.md`](docs/spec-deviations.md) | dated divergence log and the latent-gap inventory | when behaviour surprises you |
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
