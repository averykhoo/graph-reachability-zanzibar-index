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

> 🟢 **Gate: all ten phases re-run green on this tree** — ask `python scripts/gate_status.py`;
> re-run `lean` after any `*.md` edit (tiles ignore `*.md`).
> ✅ **`2026-09-01b`: the Class-B repair has landed — all four conditions discharged.** Rows
> 46/56 are stated over `checkPublic`, the `hql` binder **refused** on both; row 27 keeps
> its binder, so **the `hql` surface is one row again** — by migration, not by the refuted
> 2026-08-28c argument. Kernel-checked: no `reachedByW3d2C_schema` exists or is needed —
> the grep wanted the **wrong name**. Three pinned condition-2 instruments, both sabotages
> run. **`statement_pin.py`'s list order is the golden's line order — file new pins at the
> tail** or every "rows 46/56" citation shifts. **Next on `P3`: step 7.**
> ✅ Step 6: `hv3` pre-widened, zero new premises, green; pin `Leaf.lean::wAllNode_not_leafNode`;
> **4 obligations left, not 5**. New §11.13 **(k)**: a sabotage can fail on a *redundant* guard.
> ✅ **`2026-08-31b`: `P20` adjudicated Accept and closed; `P3` steps 6–10 unblocked** — it
> excludes only schemas Python already refuses, and the sabotage proves that refusal is the
> *premise*. 🚨 **But the guard refuted the argument's general shape** — `W4Fragment`'s ten
> fields classify LOUD 0 · MIXED 3 · SILENT 7, so the next narrowing inherits nothing
> (`ttuStarFree` is SILENT: a star subject on a TTU tupleset is **admitted** → `P6`).
> Landed sabotage-controlled: the scope pin, the correspondence pin (**a re-implementation,
> not a machine-check** → `P21`), and the `P3` bridge, which deleted a false Lean docstring.
> 📏 Conformance 495 → **515**. Detail: PROOF_STATUS `2026-08-31b` / `2026-08-31c`.
> ⏰ **`2026-08-30`: trial extended to 2026-09-06; `tasks/` is not being deleted** (user).
> Question narrows to **cutover-or-keep-both**; the dual-update contract runs another week.
> 🧭 **Phase B (this file becomes a stub) is the verdict and needs an explicit user go** →
> row `TT-1`; `TT-2` = `sync` has no gated coverage. `TK53`: **15 appends remain**.
> **"Known live correctness bugs: 0"** — ask `python scripts/gate_status.py`. Red: `git stash`.

## Board

Priority is a word, and the top two are capacity-bounded: `NOW` = exactly 1, `NEXT` ≤ 3.
`LATER` / `HOLD` / `SOMEDAY` are unbounded. Legend and budgets:
[`docs/README.md`](docs/README.md) §4. `deps` names **open** rows only — closing a row
sweeps its id out of every `deps` cell. `moved` is the last date a session progressed or
re-ranked the item, so an old date on a `NOW`/`NEXT` row means neglect. **Ids carry
forward forever and are never reused.**

| id | item (→ pointer) | pri | size | deps | moved |
|---|---|---|---|---|---|
| `P3` | leg 7 **4c-ii + step 7** — everything pre-4c-ii is DONE (`P14` included), and **the middle turned out to be splittable too (2026-08-30c)**: `UntaintedShadow` is now an `abbrev` for a `ShadowOver (P : NodeKey → Prop)` generic in its EXTRAS predicate, with five shadow lemmas generalized, so **the widening is a one-line re-instantiation instead of a re-proof of the cascade chain** (green, 1089 jobs, 3 cycles of 10; the 65 `CascadeStrataSettle` sites never moved). **Left: repoint the abbrev at `DerNode ∨ LeafNode` and discharge ~20 tier-1 sites in 3 files.** ⚠ **Sizing settled and the record was wrong — 21 modules recompile, not 42** (41+root is the cone of `DirectCorrect`/`RulesWrite`, i.e. a mis-rooted census); and one tier-1 site has **no existing lemma** (`shadow_graphRec_agree` needs operand declaredness, which `WF` does not model). ✅ **Blind instrument closed (2026-08-30d) and its prediction was wrong** — the proxy deletion built green, so the P14 weak rows are valid as taken; the difference is a *pin* now, not an argument. ✅ **Re-point steps 1–2 landed green** (anchor the four strong-shadow declarations; the schema-generic leaf-refutation toolkit), each sabotage-controlled → PROOF_STATUS `2026-08-30d` §6–§7 carries the ten-step plan. ✅ **The Class-B spike is DONE (2026-08-31c) and the answer is REACHES** — of the three sites passing `shadow_graphRec_agree` the arbitrary query's own relation, only `graph_correct_w3d2_d` reaches `graph_correct`; sites 1–2 die in superseded `Equiv.lean` milestones. **It landed on THREE pinned rows (27/46/56), not one** — which refuted this file's own 2026-08-28c line. ✅ **THE REPAIR IS LANDED (2026-09-01b), all four conditions discharged: rows 46/56 are stated over `checkPublic`, the `hql` binder was REFUSED on both non-vacuity instruments, row 27 keeps its 2026-08-28 binder — so the `hql` surface is ONE row again, by migration.** It was NOT smuggled into step 7: its own session, its own commit, on today's tree, no 4c-ii cone touched. **The known unknown is REFUTED and now kernel-checked** — no `reachedByW3d2C_schema` exists or is needed; row 46's bridge composes as `reachedByW3d2_schema (reachedByW3d2C_toW3d2 h)`, and the 2026-08-31c grep was looking for the wrong name. Condition 2 shipped three statement-pinned instruments (`public_grant_survives_fence` + `correct_applies_nonfence` / `w3d2E_correct_applies_nonfence`), both sabotages run with literal output in their docstrings; condition 3's two UNVERIFIED claims re-verified first-hand (`headline_definitions.txt` regenerates byte-identical — empirical, not inspection). Record: PROOF_STATUS `## Session 2026-09-01b`. Traps: scope doc §11.13, (h) closed, (e)+(l) now SPENT and corrected by new **(m)** — which also carries the pin-ordering trap (`statement_pin.py`'s list order IS the golden's line order; file new pins at the TAIL). ✅ **Steps 3–5 landed green (2026-08-31)**: `TtuTargetsSat` + the additive `_gen` chain, `NoLeafSubjects` (sabotage bit twice), and the pre-widen — abbrev still unflipped. ✅ **The bridge landed 2026-08-31b** — `CascadeStable.lean::ttuTargetsSat_notLeafName_of_noLeafSubjects` (`mem_append_left`; green at 1089 jobs, 5 of a 6-cycle budget, sabotage-controlled on the containment DIRECTION), with one new `import …GraphIndex.LeafRules` and three applicability theorems at `SnlBoth`. It also **removed a FALSE sentence from the Lean source** (the old docstring taught that `NoLeafSubjects` is "the same discipline on the OTHER rule list … and does not discharge these"; `schemaRewritesL` is a **superset**). 🚧 **Still 5 obligations, all undischarged** — the three `rewriteClosure` sites still need BOTH premises supplied at the site; what changed is that `hQ` now has a *route* (via `NoLeafSubjects`, which is not yet a `W4Fragment` field), while the seed-side `NotLeafName t.subject.predicate` has no owner at all. Plus the census hole at `CascadeStable.lean::shadow_graphRec_agree` (step 7). ✅ **Steps 6–10 are UNBLOCKED** — `P20` adjudicated ACCEPT (2026-08-31b). ✅ **Step 6's free obligation landed 2026-08-31c**: `hv3` in `CascadeStable.lean::shadow_graphRec_agree` is pre-widened to `¬ (DerNode ∨ LeafNode)` at the `wAll` node with **zero** new premises (the `Variant.wAll` / `Variant.plain` mismatch does it), uses weakened via `Or.inl` so step 9 is "delete two wrappers"; green first try, 1089 jobs, sabotage-controlled by a new discriminating pin `Leaf.lean::wAllNode_not_leafNode` against the pre-existing `::minted_leaf_is_leafNode`. 🚧 **4 obligations remain, not 5** — the three `rewriteClosure` sites need the seed-side `NotLeafName t.subject.predicate` (no owner anywhere; the shape that works is a new store-level `NoLeafStoreSubjects T` threaded at ~20 sites — *scout figure, unverified*), and `hv1` needs the operand-side `NotLeafName r'` (§11.13 (g)). **Do not bundle `hv1` with `hv3`** — `hunt` does not refute a minted leaf name, and the premise cannot be phrased locally because `ReconcileStars.lean::checkFn_agree_of_graphRec{,_cd}` hand `hag` exactly that hypothesis, dragging in a third file | **NOW** | L | — | 2026-08-31c |
| `P6` | `ttuStarFree` **(ii)** — bridges on the rule-routed write path; **NOT parallel-safe with `P3`** (same 38-module cone, corrected 2026-08-20b). **Fresh evidence 2026-08-31b that this is a live hole, not a formality:** `ttuStarFree` classifies **SILENT** in the new `W4Fragment` scope pin — a probe wrote `folder:* parent doc:d1` onto a TTU tupleset and it was **ADMITTED** (`_validate_ttu_tuplesets` rejects userset restrictions in tuplesets but deliberately keeps wildcard ones). So the field `graph_correct` depends on is one Python does not enforce | **NEXT** | M | — | 2026-08-31b |
| `R6` | perf round 6 — restored to `NEXT` 2026-08-31b now that `P20` has closed and freed the seat it was demoted for. **`R6-10` landed 2026-08-20b (2.54×), `R6-6` landed 2026-08-24d (4.75 → 1.75 statements/`check`)**; 10 to land, 4 declined, 3 unreachable. ⚠ **Batch *through* the N15 cache, not past it** (`R6-6` is the pattern). Order: `R6-11` → `R6-5` → `R6-4` → `R6-9` → `R6-18` → `R6-16` → `R6-7`+`R6-8` → `R6-1`. Five traps the numbers do not carry: [audit](docs/perf-round6-audit-2026-08.md) §"Traps the numbers do not carry" — **count its bullets, do not trust a restated number** → [profile](benchmarks/results/R6_PROFILE_2026-08-17.md) | **NEXT** | L | — | 2026-08-31b |
| `TK53` | **land the adjudicated `TK*` appends** — question (b) is DECIDED (→ [adjudication](docs/history/tk-findings-adjudication-2026-08-29.md)); the appends are the unlanded half, **22 landed 2026-08-29c, 15 remain**. Each is a statement existing only in `tasks/`, with a named destination in a living doc. **This row is what makes DELETE lossless.** `TK52` closed on the decision; this carries the execution, so the decision is not a residual with no owner | **NEXT** | M | — | 2026-08-29c |
| `P4` | leg 7 **4b** — leaf-probe ↔ `directLeaf` bridge → [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §7 | LATER | M | `P3` | 2026-08-16 |
| `P5` | `Inv.negEdgeFree` under leaf routing; retire the T2a caveat → [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §9.1–9.3 + §7 step 6 | LATER | M | `P4` | 2026-08-16 |
| `P7` | `ttuStarFree` **(iii)+(iv)** — re-prove the 5 consumed sites, widen the gate → [`PROOF_STATUS.md`](formal/history/PROOF_STATUS.md) 2026-08-16 | LATER | M | `P6` | 2026-08-16 |
| `P14` | leg 7 **step 5, reach-collapse half ONLY** — the classification half (re-partition `DerNode`/`UntaintedShadow`) was **absorbed into `P3` on 2026-08-20b** under Route B, which is what breaks the old `P3 → P14 → P4 → P3` cycle → [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §5 + §7 step 5, and §11.9 for the split | LATER | M | `P4` | 2026-08-20b |
| `P8` | write `W4WitnessSelfRef` (board `B2`) → [`PROOF_STATUS.md`](formal/history/PROOF_STATUS.md) 2026-08-08 §6 | LATER | S | — | 2026-08-16 |
| `P9` | lift the remove-gate exclusion (board `B2`) → `formal/conformance/test_conformance_remove_graph.py` | LATER | M | — | 2026-08-16 |
| `P10` | re-run the scope audit, hand-curated → [fan-out runbook](docs/subagent-fanout-runbook.md), final § | LATER | M | — | 2026-08-16 |
| `P11` | the fixture-TRIPLE question for 5 subsumed `.fga` fixtures → `tests/test_schema_shapes.py::KNOWN_SUBSUMED` | LATER | S | — | 2026-08-16 |
| `P12` | severity-sign revert probe → [`spec-deviations.md`](docs/spec-deviations.md) 2026-08-10 entry | LATER | S | — | 2026-08-16 |
| `HS-5` | always-living docs declare no liveness state, though [`docs/README.md`](docs/README.md) §2 requires one. **Enumeration + measuring method now live in §2 itself**; what is open is the adjudication — which docs are deliberately exempt. **No count in either place**: it read differently on all four readings → ledger `2026-08-29b` | LATER | S | — | 2026-08-29b |
| `P13` | `CORRESPONDENCE.md` claim-rot gate → [design](formal/history/claim-rot-gate-design-2026-08-16.md) | LATER | M | — | 2026-08-16 |
| `AW-1` | `FINAL_REVIEW.md` §4(d) under-claims after the remove leg → that item's own dated note | LATER | S | — | 2026-08-16 |
| `P15` | the remaining fragment leaves — `PDerivedTTU` arms, and the `twoStrata` cap → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(c)(ii) + §3.1 item 3 | LATER | L | — | 2026-08-16 |
| `P16` | widen the enumeration/state bounds → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(e); read `test_conformance_enum.py`'s module docstring, which is half the plan | LATER | M | — | 2026-08-16 |
| `P17` | bulk build/backfill is an unmodeled **default** constructor — model it or scope-exclude it in writing → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(h) + §3.1 item 6 | LATER | M | — | 2026-08-16 |
| `P21` | **a fourth `zcli` mode, so a fragment predicate can be DIFFERENTIALLY checked instead of mirrored.** `test_leaf_namespace_correspondence.py` is a Python **re-implementation** of `LeafRules.lean::NoLeafSubjects` — it says so in its own docstring — because `zcli` exposes exactly three modes (`spec`/`graph`/`graph-state`, `Cli.lean:14`, rc 4 otherwise) and has no channel to evaluate a Prop. A mode that takes an encoded `Schema` and prints the decision of `Decidable (NoLeafSubjects S)` would turn every such mirror into a real differential over the 50-schema corpus. **The residual it closes:** a mirror can be wrong in the SAME direction as the model and nothing notices | LATER | M | — | 2026-08-31b |
| `LT-1` | the two live latent residues → [`latent-gaps.md`](docs/latent-gaps.md) "Target 2" / "Target 3" | HOLD | ? | — | 2026-08-20b |
| `DW-1` | decidable `W4Fragment` for a driver-side pre-check. **Promoted SOMEDAY → LATER on 2026-08-31b, on measured evidence:** the new scope pin classifies `W4Fragment`'s ten fields **LOUD 0 · MIXED 3 · SILENT 7**, so for seven fields a schema outside the proven fragment is accepted, runs, and answers queries with no signal to the operator — its correctness resting on the differential net, not on `graph_correct`. A driver-side pre-check is what converts those seven silent holes into a refusal or a warning → [`CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) §"Conformance gates", and the live table is `test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE` | LATER | ? | — | 2026-08-31b |
| `P18` | the concurrency / multi-instance layer — the never-started TLA+ phase → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(i) + §3.1 item 5 | SOMEDAY | L | — | 2026-08-16 |
| `P19` | model the read surfaces (`lookup` / `lookup_reverse` / `expand`) in Lean → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(g) | SOMEDAY | L | — | 2026-08-16 |
| `SD-1` | lift the two scope rejections → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(j) | SOMEDAY | L | — | 2026-08-16 |
| `SD-2` | a real service wrapper — deliberately skipped; the store is a plain callable API | SOMEDAY | L | — | 2026-08-16 |
| `SD-3` | tuple-log compaction — only if the log outgrows "humans wrote this" scale | SOMEDAY | S | — | 2026-08-16 |
| `SD-4` | bulk-merge write path → [sketch](docs/architecture/bulk-merge-design.md) | SOMEDAY | L | — | 2026-08-16 |

Closed ids stay retired: `P1`, `P2`, `HS-1`, `HS-3` (all done 2026-08-16), `GS-1`, `BL-1` (2026-08-21), `BL-2` (2026-08-21b), `P20` (2026-08-31b — adjudicated ACCEPT, both deliverables landed),
`HS-4` and `GS-2` (2026-08-17), `HS-2` (2026-08-20b), `TK52` (2026-08-29b), `B1`, and the whole `ZT-*` zero-trust series. `B2` survives as the historical grouping of `P8` + `P9`.
`B1`'s finding was verified closed 2026-08-16 (halves proved 2026-07-28 / 2026-08-04) —
evidence in `formal/HANDOFF.md`'s `B1` block. Retiring an id is not the same act as closing
a finding: say which you mean — `BL-1` is both (fixed 2026-08-21; pins green), as is `BL-2`
(filed AND fixed 2026-08-21b; six pins in `tests/test_reg18_leaf_name_read_leak.py` green).
⚠ **Do not reflow those two `Closed ids` lines.** `handoff_lint.py::check_ledger_row_ids`
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

Re-point the rule-routed write path onto leaf-indexed targets and retire projection `P6` in
the same commit. Critical path. ✅ **Pre-4c-ii is done (`P14` included), and steps 1–6 have
landed green**, each sabotage-controlled — the green prefix, the `ShadowOver` generalisation
that made the middle splittable, the `NoLeafSubjects` bridge, and step 6's free `hv3`
pre-widen. **The flip is step 9 and is a two-line rollback.** What landed and why, per step:
PROOF_STATUS `2026-08-30b`…`2026-08-31c`.

✅ **The Class-B repair is adjudicated (user call, 2026-09-01) — no open decision remains on
this item.** Rows 46/56 are **re-stated over `GraphModel.checkPublic`**; the `hql` binder is
**refused** on them (satisfiability witnesses with `q` universally quantified — the failure
`FullScope.lean::graph_correct_public`'s docstring already refuses for `final_applies`).
Row 27 keeps its 2026-08-28 binder. **Four binding conditions** — own green commit *before*
step 7 · sabotage the migrated witnesses' *non-fence* branch · re-verify the two
`2026-08-31c` unverified paragraphs · doc sweep + `lean` re-run. ✅ **No new lemma is
needed**: row 46's `σ.schema` composes as `reachedByW3d2_schema ∘ reachedByW3d2C_toW3d2`
(source read, not yet kernel-checked). Grounds: PROOF_STATUS `## Session 2026-09-01`.

🚧 **Four obligations remain, not five** (`hv3` discharged 2026-08-31c). The three
`rewriteClosure` sites each need the seed-side `NotLeafName t.subject.predicate`, which has
**no owner anywhere** (the `NoLeafStoreSubjects T` / ~20-site shape is **scout output,
unverified**); `hv1` needs the operand-side `NotLeafName r'` and must **not** be bundled with
`hv3` (it drags in a third file via `ReconcileStars.lean::checkFn_agree_of_graphRec`). **Do not
restate the three sites as "one premise, not two"** —
`::rewriteClosure_subject_not_leafNode`'s docstring says neither is available there today.

✅ **Steps 6–10 unblocked** (`P20` Accept, closed). 🚨 **Read what that adjudication cost
before reusing its logic**: "Python already refuses what the narrowing excludes" holds for
**zero of the ten fields** — step 6's is the exception; re-establish it, never cite `P20`.

⚠ **Traps: scope doc §11.13, superseding §11.10 — read before touching the cone.** Ten
items; **(h) CLOSED**, **(b) is itself stale** (Leaf.lean line numbers are +58 since
`50af00e` — cite `file::symbol`), **(i)/(j) new 2026-08-31**. **Exit: §11.12** via its
amendment (commit the docs-only append first, reset onto it).

**Read first:** PROOF_STATUS `## Session 2026-09-01` (the adjudication + its four conditions
— before touching rows 46/56), then `## Session 2026-08-31` (§3 landed, §4 the blocker),
then `2026-08-30d` §6 (the ten-step plan) and `2026-08-30c`; scope doc **§11.13 (traps)**,
§11.11, §11.12. Completion criterion: PROOF_STATUS `2026-08-16c`, numbers re-derived from
`formal/FINAL_REVIEW.md`'s generated ledger, never prose. Then
`CascadeStable.lean::ShadowOver`, `Leaf.lean::LeafNode`, `extractor.py::_edge_projection`.

### `R6` — perf round 6, restored to `NEXT`

Restored 2026-08-31b: it was demoted on 2026-08-31 purely to seat `P20`, and `P20` has closed.
Nothing about the work changed in between. **⚠ Batch *through* the N15 cache, not past it** —
`R6-6` is the pattern, and every read-path item has a cascade caller behind it. Order:
`R6-11` → `R6-5` → `R6-4` → `R6-9` → `R6-18` → `R6-16` → `R6-7`+`R6-8` → `R6-1`.
**Not parallel-safe with `P3`/`P6` if it touches the cascade read path** — check before
opening a cone that either of those owns.

**Read first:** [the audit](docs/perf-round6-audit-2026-08.md) §"Traps the numbers do not
carry" — **count its bullets; do not trust a restated number**; then
[the profile](benchmarks/results/R6_PROFILE_2026-08-17.md) and
[`docs/perf-next-round.md`](docs/perf-next-round.md) (the fence and the reopening rule).

### `TK53` — land the adjudicated `TK*` appends

Each append is one statement existing nowhere but `tasks/`; until this closes, deleting
`tasks/` drops statements no living doc carries. **22 landed 2026-08-29c; 15 remain.**
⚠ **Re-verify each row before writing it** — doing so overturned rows both ways, including
a destination that did not exist and four "appends" already carried by their own source.
**Read first:** [the adjudication](docs/history/tk-findings-adjudication-2026-08-29.md) —
its table, its four traps, its "Method" §; then
[the snapshot](docs/history/tasktool-findings-2026-08-29.md) for the finding text.

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
| [`tasks/README.md`](tasks/README.md) · [`docs/tasktool-spec.md`](docs/tasktool-spec.md) | the task tree: layout, reading protocol, the rules `lint` cannot enforce / the tool's full contract | while the trial runs — any board edit owes the mirrored `task.py` op |
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
2. **Rewrite the Banner** — this one AND `tasks/BANNER.md` (lint check 12 requires it):
   gate state as observed, today's date, the new headline, and the entry key just created.
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
