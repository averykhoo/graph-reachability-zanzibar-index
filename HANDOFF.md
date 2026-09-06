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
> re-run `lean` after any `*.md` edit — and `t2c` excludes `*.md` only *outside* `tasks/`, so a
> `tasks/*.md` edit stales the tiles too (corrected 2026-09-05).
> ✅ **`2026-09-06b` (`P17` + `TK55` closed, user-decided):** `P17` took option (c) — the DEFAULT
> constructor `build_index(bulk=True)` is now pinned by a conformance differential,
> `test_conformance_bulk_state.py` (bulk vs the incremental Python graph state, EXACT, over all
> 25 `GRAPH_FRAGMENT` corpora; multiplicity sabotage red `incremental=3 bulk=1`), and
> `FINAL_REVIEW.md` §3.1 item 6 / §4(h) carry the written scope statement; the Lean
> `bulk = replay` theorem is `P24` (`SOMEDAY`). `TK55`: `define : [user]` used to compile to
> `Filter(relation='')` and the graph answered `False` where oracle + set said `True` through
> `define : viewer` — BOTH parsers now refuse an empty declared name (15 pins), and
> `keysNonempty` is accepted as scope with a justification that is now true.
> 🔍 **Branch `p3-flip-red-2026-09-05` inventoried, then DELETED (user decision, no tag)** —
> 26/30 files were scaffolding already on master; the 4 evidence files and the literal refuted
> declarations live in
> [`formal/history/p3-flip-red-snapshot-2026-09-05.md`](formal/history/p3-flip-red-snapshot-2026-09-05.md)
> (55/55 quotes re-verified BEFORE deletion). `d6d2dfc` is unreachable now; that note is the record.
> 🧭 **Trial window closed today — NO cutover; prework + grade only (user decision).** The tree
> was the STALE arm (9 drifts, all reconciled + acked; hand-sourced rows with a board row cannot
> be acked — a tool gap); a Phase B′ candidate is DRAFTED at the top of
> [`docs/tree-sole-authority-spec-2026-08-29.md`](docs/tree-sole-authority-spec-2026-08-29.md)
> (not decided); the grade is [`tasktool-trial-protocol.md`](docs/tasktool-trial-protocol.md)
> §6 `2026-09-06`. **Next: the feedback pass with the user; `TT-1` still needs an explicit go.**
> ⚠ **Two floors had LEAKED headroom on `HEAD`** — `TK56` added 6 tests without ratcheting
> (clean checkout 520/1038 vs 515/1037). Both re-measured and zero-headroom again. New rows:
> `P22` (the I14 crossable-middle loop in `bulk_build.py` is unpinned — a GREEN sabotage),
> `P23` (declared-name charset asymmetry between the two parsers).
> 📌 **`2026-09-06` (rotated → PROOF_STATUS `2026-09-06` §1–§8): `TK56` closed** — T3
> instantiated, zero `opaque`s, `sorry_scan.py` refuses one, `task.py new` ratchets its own floor.
> `2026-09-05b` (`P3` landed) → PROOF_STATUS `2026-09-05b`; live traps: scope doc §11.13 **(bb)…(gg)**.
> `TK53`: **15 appends remain**; `TT-2` = `sync` has no gated coverage.
> **"Known live correctness bugs: 0"** — ask `python scripts/gate_status.py`. Red: snapshot it
> with a TEMP INDEX, never `git stash`/`git checkout --` (autocrlf rewrites LF → CRLF; trap (ee)).

## Board

Priority is a word, and the top two are capacity-bounded: `NOW` = exactly 1, `NEXT` ≤ 3.
`LATER` / `HOLD` / `SOMEDAY` are unbounded. Legend and budgets:
[`docs/README.md`](docs/README.md) §4. `deps` names **open** rows only — closing a row
sweeps its id out of every `deps` cell. `moved` is the last date a session progressed or
re-ranked the item, so an old date on a `NOW`/`NEXT` row means neglect. **Ids carry
forward forever and are never reused.**

| id | item (→ pointer) | pri | size | deps | moved |
|---|---|---|---|---|---|
| `P6` | `ttuStarFree` **(ii)** — bridges on the rule-routed write path. **Promoted `NEXT` → `NOW` MECHANICALLY on 2026-09-05b** — it was the top `NEXT` row and its one blocker is gone: `P3` LANDED (write leg now folds `rewriteClosureL S (rawWriteTuples S t)`, `Cascade.lean:190-191`), so "NOT parallel-safe with `P3`" is moot and **increment B must bridge on the LEAF-routed list, not the public one** — re-rank if the user disagrees. **Fresh evidence 2026-08-31b that this is a live hole, not a formality:** `ttuStarFree` classifies **SILENT** in the new `W4Fragment` scope pin — a probe wrote `folder:* parent doc:d1` onto a TTU tupleset and it was **ADMITTED** (`_validate_ttu_tuplesets` rejects userset restrictions in tuplesets but deliberately keeps wildcard ones). So the field `graph_correct` depends on is one Python does not enforce | **NOW** | M | — | 2026-09-05b |
| `R6` | perf round 6 — restored to `NEXT` 2026-08-31b now that `P20` has closed and freed the seat it was demoted for. **`R6-10` landed 2026-08-20b (2.54×), `R6-6` landed 2026-08-24d (4.75 → 1.75 statements/`check`)**; 10 to land, 4 declined, 3 unreachable. ⚠ **Batch *through* the N15 cache, not past it** (`R6-6` is the pattern). Order: `R6-11` → `R6-5` → `R6-4` → `R6-9` → `R6-18` → `R6-16` → `R6-7`+`R6-8` → `R6-1`. Five traps the numbers do not carry: [audit](docs/perf-round6-audit-2026-08.md) §"Traps the numbers do not carry" — **count its bullets, do not trust a restated number** → [profile](benchmarks/results/R6_PROFILE_2026-08-17.md) | **NEXT** | L | — | 2026-08-31b |
| `TK53` | **land the adjudicated `TK*` appends** — question (b) is DECIDED (→ [adjudication](docs/history/tk-findings-adjudication-2026-08-29.md)); the appends are the unlanded half, **22 landed 2026-08-29c, 15 remain**. Each is a statement existing only in `tasks/`, with a named destination in a living doc. **This row is what makes DELETE lossless.** `TK52` closed on the decision; this carries the execution, so the decision is not a residual with no owner | **NEXT** | M | — | 2026-08-29c |
| `P4` | leg 7 **4b** — leaf-probe ↔ `directLeaf` bridge → [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §7. Unblocked 2026-09-05b (`P3` closed; deps swept) | LATER | M | — | 2026-09-05b |
| `P5` | `Inv.negEdgeFree` under leaf routing; retire the T2a caveat → [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §9.1–9.3 + §7 step 6. **Re-scoped 2026-09-05b: this is PROOF work, not a design call** — T2a did NOT widen with `P3` (`graph_reached_inv` still takes `W4NarrowT2a`; `outside_narrow_t2a` holds) and its "P6 modelling limit" justification is retired, since the model now routes exactly as Python does. The D.3 probe re-run on the landed model (`formal/probes/d3_negedgefree_postflip_2026-09-05.lean`) says `negFree := true` on the model's own write leg while the bridge-sabotage control reproduces D.3's kill — so the clause is plausibly provable, and `negEdgeFree` (`GraphIndex/State.lean:706`) is the only clause implicated. ⚠ D.3's witness (`Sd`/`Td`) is now VACUOUS under routing; probe with `LeafWitness.Sw`/`tw`. PROOF_STATUS `2026-09-05b` §9.5 | LATER | M | `P4` | 2026-09-05b |
| `P7` | `ttuStarFree` **(iii)+(iv)** — re-prove the 5 consumed sites, widen the gate → [`PROOF_STATUS.md`](formal/history/PROOF_STATUS.md) 2026-08-16 | LATER | M | `P6` | 2026-08-16 |
| `P14` | leg 7 **step 5, reach-collapse half ONLY** — the classification half (re-partition `DerNode`/`UntaintedShadow`) was **absorbed into `P3` on 2026-08-20b** under Route B, which is what breaks the old `P3 → P14 → P4 → P3` cycle → [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §5 + §7 step 5, and §11.9 for the split. `P3` closed 2026-09-05b — the absorbed half landed with it; only this reach-collapse half remains | LATER | M | `P4` | 2026-09-05b |
| `P8` | write `W4WitnessSelfRef` (board `B2`) → [`PROOF_STATUS.md`](formal/history/PROOF_STATUS.md) 2026-08-08 §6 | LATER | S | — | 2026-08-16 |
| `P9` | lift the remove-gate exclusion (board `B2`) → `formal/conformance/test_conformance_remove_graph.py` | LATER | M | — | 2026-08-16 |
| `P10` | re-run the scope audit, hand-curated → [fan-out runbook](docs/subagent-fanout-runbook.md), final § | LATER | M | — | 2026-08-16 |
| `P11` | the fixture-TRIPLE question for 5 subsumed `.fga` fixtures → `tests/test_schema_shapes.py::KNOWN_SUBSUMED` | LATER | S | — | 2026-08-16 |
| `P12` | severity-sign revert probe → [`spec-deviations.md`](docs/spec-deviations.md) 2026-08-10 entry | LATER | S | — | 2026-08-16 |
| `P22` | **`bulk_build.py:206-221`'s I14 crossable-middle loop is pinned by NOTHING.** Found 2026-09-06b by the `P17` sabotage sweep: deleting the loop stays GREEN across every `build_index` caller — `tests/test_bulk_build.py`, the new `test_conformance_bulk_state.py` (all 25 `GRAPH_FRAGMENT` corpora, exact state compare) and the matrix. Either no corpus reaches a crossable middle under bulk (write one that does, watch it go red, keep it as a permanent test) or the loop is dead code (prove it, delete it). A loop no sabotage can reach is unverified code on the DEFAULT constructor → `test_conformance_bulk_state.py` module docstring, "green sabotages" | LATER | S | — | 2026-09-06b |
| `P23` | **declared-name charset asymmetry between the two parsers.** `TK55` closed the EMPTY name on both sides, but `tests/oracle.py::parse_schema_ast` still has no `.`-lock on declared relation names, and every other out-of-charset declared name (`*`, a space, `#`, non-ASCII, 257 chars) is graph-refused / set-accepted — today caught only by `ParityEngine`'s accept/reject unanimity, never by a schema-level pin. Decide the contract (refuse at parse, in BOTH parsers, pinned the way `tests/test_reg_empty_relation_name.py` pins the empty case) → [`spec-deviations.md`](docs/spec-deviations.md) 2026-09-06 entry | LATER | S | — | 2026-09-06b |
| `TK54` | `Scratch4cii.lean` is a TRACKED module inside the gated lake package (since `a55a433`; sorry-free; the source of the build's linter warnings) — delete it or justify it with a docstring and a name that says what it pins. Either way the job count and `MIN_SCANNED_LEAN_FILES` move: re-measure, never difference → PROOF_STATUS `2026-09-05b` §9.5 | LATER | S | — | 2026-09-05b |
| `HS-5` | always-living docs declare no liveness state, though [`docs/README.md`](docs/README.md) §2 requires one. **Enumeration + measuring method now live in §2 itself**; what is open is the adjudication — which docs are deliberately exempt. **No count in either place**: it read differently on all four readings → ledger `2026-08-29b` | LATER | S | — | 2026-08-29b |
| `P13` | `CORRESPONDENCE.md` claim-rot gate → [design](formal/history/claim-rot-gate-design-2026-08-16.md) | LATER | M | — | 2026-08-16 |
| `AW-1` | `FINAL_REVIEW.md` §4(d) under-claims after the remove leg → that item's own dated note | LATER | S | — | 2026-08-16 |
| `P15` | the remaining fragment leaves — `PDerivedTTU` arms, and the `twoStrata` cap → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(c)(ii) + §3.1 item 3 | LATER | L | — | 2026-08-16 |
| `P16` | widen the enumeration/state bounds → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(e); read `test_conformance_enum.py`'s module docstring, which is half the plan | LATER | M | — | 2026-08-16 |
| `P21` | **a fourth `zcli` mode, so a fragment predicate can be DIFFERENTIALLY checked instead of mirrored.** `test_leaf_namespace_correspondence.py` is a Python **re-implementation** of `LeafRules.lean::NoLeafSubjects` — it says so in its own docstring — because `zcli` exposes exactly three modes (`spec`/`graph`/`graph-state`, `Cli.lean:14`, rc 4 otherwise) and has no channel to evaluate a Prop. A mode that takes an encoded `Schema` and prints the decision of `Decidable (NoLeafSubjects S)` would turn every such mirror into a real differential over the 50-schema corpus. **The residual it closes:** a mirror can be wrong in the SAME direction as the model and nothing notices | LATER | M | — | 2026-08-31b |
| `LT-1` | the two live latent residues → [`latent-gaps.md`](docs/latent-gaps.md) "Target 2" / "Target 3" | HOLD | ? | — | 2026-08-20b |
| `DW-1` | decidable `W4Fragment` for a driver-side pre-check. **Promoted SOMEDAY → LATER on 2026-08-31b, on measured evidence:** the new scope pin classifies `W4Fragment`'s ten fields **LOUD 0 · MIXED 3 · SILENT 7**, so for seven fields a schema outside the proven fragment is accepted, runs, and answers queries with no signal to the operator — its correctness resting on the differential net, not on `graph_correct`. A driver-side pre-check is what converts those seven silent holes into a refusal or a warning → [`CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) §"Conformance gates", and the live table is `test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE` | LATER | ? | — | 2026-08-31b |
| `P18` | the concurrency / multi-instance layer — the never-started TLA+ phase → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(i) + §3.1 item 5 | SOMEDAY | L | — | 2026-08-16 |
| `P19` | model the read surfaces (`lookup` / `lookup_reverse` / `expand`) in Lean → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(g) | SOMEDAY | L | — | 2026-08-16 |
| `P24` | **Lean `bulkState = replay`** — a `ReadEq` theorem that the offline constructor (`bulk_build.py` + `bulk_backfill.py`) reaches the same `GraphState` as replaying the tuples through `ReachedBy`, which would put `build_index(bulk=True)` under the headline instead of under the scope statement `P17` wrote (2026-09-06b). Caveat: `GraphState` carries no refcount / path-count / `implicit` / `derived` / version fields (`State.lean:105-111`), so the theorem can only speak to the projection the extractor compares — the edge MULTIPLICITIES `test_conformance_bulk_state.py` pins stay Python-only either way → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §3.1 item 6 | SOMEDAY | M | — | 2026-09-06b |
| `SD-1` | lift the two scope rejections → [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(j) | SOMEDAY | L | — | 2026-08-16 |
| `SD-2` | a real service wrapper — deliberately skipped; the store is a plain callable API | SOMEDAY | L | — | 2026-08-16 |
| `SD-3` | tuple-log compaction — only if the log outgrows "humans wrote this" scale | SOMEDAY | S | — | 2026-08-16 |
| `SD-4` | bulk-merge write path → [sketch](docs/architecture/bulk-merge-design.md) | SOMEDAY | L | — | 2026-08-16 |

Closed ids stay retired: `P1`, `P2`, `HS-1`, `HS-3` (all done 2026-08-16), `GS-1`, `BL-1` (2026-08-21), `BL-2` (2026-08-21b), `P20` (2026-08-31b — adjudicated ACCEPT, both deliverables landed), `P3` (2026-09-05b — the flip landed sorry-free with the remove leg and the dirty-key branch co-flipped; the extractor's edge projection retired), `TK56` (2026-09-06), `P17` and `TK55` (2026-09-06b — bulk pinned by conformance differential + written scope; empty declared name refused by both parsers, `keysNonempty` accepted as scope),
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

### `R6` — perf round 6, restored to `NEXT`

Restored 2026-08-31b: it was demoted on 2026-08-31 purely to seat `P20`, and `P20` has closed.
Nothing about the work changed in between. **⚠ Batch *through* the N15 cache, not past it** —
`R6-6` is the pattern, and every read-path item has a cascade caller behind it. Order:
`R6-11` → `R6-5` → `R6-4` → `R6-9` → `R6-18` → `R6-16` → `R6-7`+`R6-8` → `R6-1`.
**Not parallel-safe with `P6` if it touches the cascade read path** (`P3` closed
2026-09-05b) — check before opening a cone that `P6` owns.

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

**`NOW` as of 2026-09-05b, by mechanism not by judgement**: `P3` landed and closed, this
was the top `NEXT` row, and its only blocker was the textual collision below — so it moved
up. **Re-rank freely.** What `P3` changed for this item: the write leg is no longer
`writeLoggedOne` over the public closure — `GraphState.writeLoggedRules` folds
`rewriteClosureL S (rawWriteTuples S t)` (`Cascade.lean:190-191`), the remove leg folds the
SAME list (`:340-341`), and `affectedKeys` dirties the PUBLIC key through `publicOfLeaf`
(`:542-546`). **Increment B must bridge on that leaf-routed list**; a bridge keyed on the
public relation name would land on a node the write leg no longer touches — the same
leg-asymmetry class the kernel refuted in `P3`'s first attempt, where a write-then-remove
left a ghost grant (PROOF_STATUS `2026-09-05b` §2). The "38-module cone" figure below is pre-flip and unreproduced;
re-measure with a probe wave before quoting it. Also inherited from `P3`: the dirty-key
list `cascadeKeysAbove` and the enum candidates `enumJob2(D).cands` are `.eraseDups` sets
(membership via `mem_cascadeKeys_iff_above` / `List.mem_eraseDups`) — any increment
touching `affectedKeys` or the candidate lists re-measures `two_stratum_cascade`'s
multiplicities (expect `1…5`) before regenerating a golden (PROOF_STATUS `2026-09-05b` §10). The paragraph below is kept as the record
of why the two could not run concurrently.

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
