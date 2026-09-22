---
id: R6-4
title: boolean graph lookup full-scans every residue row and JSON-decodes per row (30.1%)
brief:
pri: LATER
size: L
deps: []
related: []
parent: R6
labels: [perf]
source: docs/perf-round6-audit-2026-08.md
source_hash:
created: 2026-08-15
moved: 2026-09-22b
updated: 2026-09-22b
closed:
---

`index_v4/wildcard.py::WildcardIndex._collect_residue_memberships`

**Measured (2026-08-17 motivating-measurement pass):** **30.1%** of every boolean lookup and **193 `json.loads` per lookup** over only **100** residue rows — and the scan is O(#derived objects), so the share GROWS with the store.

**Verdict: MOTIVATED — still to land.** Position **4 of 10** in the audit’s recommended order (`R6-6 → R6-11 → R6-5 → R6-4 → R6-9 → R6-18 → R6-16 → R6-7 → R6-8 → R6-1`). That order is a RECOMMENDATION and is deliberately NOT encoded as `deps`; neither is `R6-16`’s co-design requirement, which is simultaneity rather than precedence and lives in the traps of `R6-16`/`R6-7`/`R6-8`. **No row in this round has `deps`.**

## Traps

⚠ **Read your id’s entry in [`perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) — INCLUDING its verifier corrections — and that file’s §"Traps the numbers do not carry", before taking this id.** The audit’s own rule: *do not implement from titles alone*. Eighteen findings survived adversarial verification with **0 refuted**, but several impacts were downgraded, several fix sketches were corrected, and one fix was refuted outright while its finding stood.

⚠ **`R6-4(a)` is UNSOUND AS FILED — do not implement it as written.** Its `(row.id, row.version)` decode memo breaks on SQLite: deleted residues restart at `version=1` and rowids recycle, so the key is not unique over time. The fix sketch is a verbatim block that calls the key "sound", which is why the correction had to be pinned dated (2026-08-21) beside the sketch itself and not only in the traps section. **`R6-4(b)` — the stars reverse-index — is the real fix, remains open, and is its own session**; it needs a stars twin, `bulk_build` population and an I6 extension. `ResidueRefV1` already exists and reads never use it.

⚠ **Lean impact: a `CORRESPONDENCE.md` §8.1/§7 log entry, and — on the more specific record — NO Lean proof change.** The audit’s round-wide "Rules that bind this list" bullet groups this id with `R6-2`/`R6-16` as changing modeled algorithms, which reads as owing a model update plus the full phased gate and a fuzz sweep. `R6-4`’s own verifier Lean-impact block is narrower and later: it *"touches `CORRESPONDENCE.md`-anchored symbols but no proved Lean model … the fix needs a matching §8.1/§7 log entry … but no Lean proof change."* Take the specific record, log the gap, and re-read both before assuming the expensive branch — the gate is still owed for the code change either way.

⚠ **Decompose every cumulative share before quoting it as a target.** `R6-10`’s headline 59.8% was CUMULATIVE; decomposed it was `_direct_incoming` 28.4% + `_nodes_by_ids` 30.7%, and the realised win came from the two SELECTs, not the headline. `R6-19` is the same trap caught earlier.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) §`### R6-4` — the entry, **including its verifier corrections**
- the same file, §"Traps the numbers do not carry" — the round-wide traps. Read the section; it is short, and it is the only home for how many there are. (This line used to say "the five", attributed to the tree generator recounting them at generation time. That generator was deleted with `.scratch/tasktool/` on 2026-09-07, so the attribution named a mechanism that could not run — `TK61`, reworded 2026-09-07b. A bare "five" with no attribution would have been worse: that is an unsourced restated count.)
- [`R6_PROFILE_2026-08-17.md`](benchmarks/results/R6_PROFILE_2026-08-17.md) — verdicts, method, and the two honest limits (in-memory SQLite understates statement-count wins; cProfile depresses throughput)
- `index_v4/wildcard.py::WildcardIndex._collect_residue_memberships` — the code
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the fence and the reopening rule
- `python scripts/task.py show R6` — the parent: round-wide order, traps and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21

**Migrated by `migrate.py`, and this row is a CORRECTION.** The first migration pass classified every id whose disposition string was not literally `closed` as retired, which wrote this live item into `retired-ids.txt` — an irreversible sink, since `task.py` refuses to re-mint a retired id. Its true disposition (`MOTIVATED, unlanded`) is taken from `docs/perf-round6-audit-2026-08.md`, the audit that owns these ids, not from the `R6` board row’s summary prose (which undercounts the land list by one and overcounts the declines by one). `parent: R6` makes the round a rollup: closing the last child is what reports that `R6` itself can close. **`created` (`2026-08-15`) is RECORDED, not approximated** — it is the date the audit doc that minted these ids states for itself; `moved` is the `R6` board row’s value.

### 2026-09-22b

MEASURED 2026-09-22b: THIS ROW IS UNDERCOUNTED, AND IT IS THE BETTER TRUE WIN OF THE R6-4/R6-5
PAIR.

The graph-lookup profile run serves both rows (`profile_r6.py::target_graph_lookup` banner:
"[R6-4, R6-5]"). Its 32.7% ORM-construction block was attributed wholly to R6-5. Per-class
attribution (`.scratch/r6-decomp/probe_instance_by_class.py`, SQLAlchemy InstanceEvents.load
per mapped class, deduped total reconciling EXACTLY to the profile's recorded 22,410):

       6,000  (26.8%)  ResidueV1   <- this row
      16,410  (73.2%)  NodeV4+EdgeV4

So 26.8% of that block is this row's residue full-scan. Those 6,000 constructions already sit
inside this row's own 30.1% `_collect_residue_memberships` cum -- so the honest reading is NOT
"add 8.8 points to R6-4", it is "R6-5's 32.7% double-counts R6-4's scan and the two figures
cannot be added". This row's 30.1% / 193 json.loads per lookup remains correct and undecomposed;
it is a single function's cum time. 100 residue rows scanned per lookup, O(#derived objects).

LEAN: the finder says this changes a modelled algorithm; the verifier is narrower and says no
PROVED Lean model is touched, so a `CORRESPONDENCE.md` sec 8.1/sec 7 log entry plus sabotage is
what is owed, not a proof change. Anchor census this session: `_collect_residue_memberships` 1,
`_store_residue` 4, `_sync_residue_refs` 1. Preserve the residue-write-before-edge-audit order
(sec 5 pins `reconcileKeyC`/`reconcileStarsKey` to `_store_residue` preceding the step-(4) edge
audit).

UNCHANGED AND STILL BINDING: R6-4(a) is UNSOUND as filed -- `_store_residue` deletes empty
residues and recreated rows restart at version=1 while SQLite recycles rowids, so the
(row.id, row.version) decode memo is not unique over time. R6-4(b) is the live half and the
audit says it is its own session. The new table must be populated in THREE places -- live
`_store_residue`, offline `index_v4/bulk_build.py::bulk_build`, and the I6 agreement check --
each an independent way to ship a silently-empty index, plus a hand PG migration (no alembic
in the repo). `size: L` is, unusually for this repo, not an undercount.

Full audit: docs/r6-sizing-census-2026-09-22.md

Path correction, same session: the probe cited in the 2026-09-22b entry above now lives in the TRACKED tree at benchmarks/probe_r6_instance_by_class.py. It was first cited at a gitignored .scratch/ path, which would have rotted the citation and lost the instrument -- the measurement is evidence, so the instrument belongs in the tree. Re-run from the repo root; output is byte-identical (6,000 ResidueV1 / 16,410 NodeV4+EdgeV4, deduped total 22,410 reconciling to the profile line).
