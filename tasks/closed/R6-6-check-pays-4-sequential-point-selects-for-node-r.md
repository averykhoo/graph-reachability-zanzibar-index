---
id: R6-6
title: check() pays 4 sequential point SELECTs for node resolution before its batched probe
brief:
pri: LATER
size: S
deps: []
related: []
parent: R6
labels: [perf]
source: docs/perf-round6-audit-2026-08.md
source_hash:
created: 2026-08-15
moved: 2026-08-24d
updated: 2026-08-24d
closed: 2026-08-24d
---

`index_v4/wildcard.py::WildcardIndex.check`

**Measured (2026-08-17 motivating-measurement pass):** exactly **4.00** `node_v4` point SELECTs per `check` plus 0.75 edge; the fix takes the op **4.75 → 1.75 statements (−63% round trips)**, with no Lean change.

**Verdict: MOTIVATED — still to land.** Position **1 of 10** in the audit’s recommended order (`R6-6 → R6-11 → R6-5 → R6-4 → R6-9 → R6-18 → R6-16 → R6-7 → R6-8 → R6-1`). That order is a RECOMMENDATION and is deliberately NOT encoded as `deps`; neither is `R6-16`’s co-design requirement, which is simultaneity rather than precedence and lives in the traps of `R6-16`/`R6-7`/`R6-8`. **No row in this round has `deps`.**

## Traps

⚠ **Read your id’s entry in [`perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) — INCLUDING its verifier corrections — and that file’s §"Traps the numbers do not carry", before taking this id.** The audit’s own rule: *do not implement from titles alone*. Eighteen findings survived adversarial verification with **0 refuted**, but several impacts were downgraded, several fix sketches were corrected, and one fix was refuted outright while its finding stood.

⚠ **The cited symbol MOVED on 2026-08-21, and the audit doc has not caught up.** Fixing `BL-2` split `index_v4/wildcard.py::WildcardIndex.check` into a public leaf-family DENY fence plus `::WildcardIndex._check_internal`, which carries the old body verbatim — so the four sequential point SELECTs this item is about now live in `_check_internal`, and that is what to measure and patch. `docs/perf-round6-audit-2026-08.md` still names `::check` in both its verdict table and its `### R6-6` entry; `formal/CORRESPONDENCE.md` was re-anchored the same day, the audit was not. Verified by reading `wildcard.py` on 2026-08-21 — the anchor still RESOLVES (both names exist), which is exactly why a symbol-existence check cannot catch this one.

⚠ **Decompose every cumulative share before quoting it as a target.** `R6-10`’s headline 59.8% was CUMULATIVE; decomposed it was `_direct_incoming` 28.4% + `_nodes_by_ids` 30.7%, and the realised win came from the two SELECTs, not the headline. `R6-19` is the same trap caught earlier.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) §`### R6-6` — the entry, **including its verifier corrections**
- the same file, §"Traps the numbers do not carry" — the five round-wide traps (counted from that section at generation time, not restated: `migrate.py` refuses to build if the bullet count moves)
- [`R6_PROFILE_2026-08-17.md`](benchmarks/results/R6_PROFILE_2026-08-17.md) — verdicts, method, and the two honest limits (in-memory SQLite understates statement-count wins; cProfile depresses throughput)
- `index_v4/wildcard.py::WildcardIndex._check_internal (the audit still names ::check -- see the dated trap above)` — the code
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the fence and the reopening rule
- `python task.py show R6` — the parent: round-wide order, traps and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21

**Migrated by `migrate.py`, and this row is a CORRECTION.** The first migration pass classified every id whose disposition string was not literally `closed` as retired, which wrote this live item into `retired-ids.txt` — an irreversible sink, since `task.py` refuses to re-mint a retired id. Its true disposition (`MOTIVATED, unlanded`) is taken from `docs/perf-round6-audit-2026-08.md`, the audit that owns these ids, not from the `R6` board row’s summary prose (which undercounts the land list by one and overcounts the declines by one). `parent: R6` makes the round a rollup: closing the last child is what reports that `R6` itself can close. **`created` (`2026-08-15`) is RECORDED, not approximated** — it is the date the audit doc that minted these ids states for itself; `moved` is the `R6` board row’s value.

### 2026-08-24d

LANDED. index_v4/core.py::ReachabilityIndex.resolve_node_ids batches the up-to-4 identity resolutions into ONE row-value IN over node_v4_unique_constraint; _check_internal calls it once instead of 2x_get_concrete + 2x_w_id. Measured (python -m benchmarks.profile_r6 --target graph-check, run alone, gdrive graph-scale 200, 2000 checks): node_v4 4.00 -> 1.00 per check, edge probe unchanged at 0.75, total 4.75 -> 1.75 statements (-63.2%); 333 -> 767 checks/s on in-memory SQLite; true answers 1080/2000 unchanged (semantic control). Exactly the figure the audit predicted. ONE deviation from the audit's fix sketch, deliberate: the sketch says 'a per-call fresh query, not a cache' -- taken literally that regresses the WRITE path, where this same entry point is reached via processor.py::_EvalContext.leaf_check inside a cascade with the N15 _node_cache installed and warm. The landed helper reads AND populates that cache; the verifier's 'select bare columns' nit was declined for the same reason (a projected row cannot be cached, and the 4 statements it replaces already built entities). W2 is untouched -- nothing is held across calls. Pinned in the R6-6 block of tests/test_reads.py: the statement count, and each of the four probe keys individually decisive. 8 sabotages; the first version of the dropped-key pin was GREEN under the sabotage it exists for (it asked check(alice,d1) in all four cases, and the materialised bridge means probe 1 answers alone -- probes 3/4 need a GHOST endpoint), so the fixture was rewritten, not the sabotage. Dropping w_all is 2 failed / 23 passed: the only reds in test_reads.py are the two new cases, all NINE of that module's oracle grid-parity tests stay green under a live under-grant. Widened it IS caught (4 failed / 56 passed over matrix+lookup-oracle+wildcard-property), so a module-local blind spot, not project-wide. Instrument corrected too: target_graph_check's verdict predicate reads NOT MOTIVATED at 0.00 exactly as at 1.00, so it now asserts non-vacuity first. Lean: none -- probe-key set unchanged, _check_internal.key closure preserved by name. Write-up: benchmarks/results/PERF_ANALYSIS.md sec Applied.
