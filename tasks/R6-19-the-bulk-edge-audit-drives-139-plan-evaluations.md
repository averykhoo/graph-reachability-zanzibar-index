---
id: R6-19
title: the bulk edge audit drives ~139 plan evaluations per object reconcile (2.0% self)
brief:
pri: LATER
size: ?
deps: []
related: []
parent: R6
labels: [perf]
source: docs/perf-round6-audit-2026-08.md
source_hash:
created: 2026-08-18
moved: 2026-08-21
updated: 2026-08-21
closed:
---

`index_v4/bulk_backfill.py::_BulkBackfill._reconcile_subject_edge`

**Measured (2026-08-17 motivating-measurement pass):** **145,560 calls; cum 25.4%, but tottime only 2.0%** — 145,560 calls over 1,050 `_reconcile` calls = **~138.6 bare-entity audit members per object reconcile**, each paying a full `plan.check_fn` evaluation. **The honest statement is that this call site is the DENOMINATOR**, not that the function is a quarter of a bulk build.

**Filed 2026-08-18, outside the audit’s two-phase workflow**, because 25.3% of a bulk build belonged to no candidate and an unowned number is how a finding gets lost. Filing it is a claim that the number has an owner, not that the work is justified.

**What it owes before it is worth landing, in order** (the first two are cheap): (1) instrument the duplicate-evaluation rate — if it is near zero on real corpora the item is finished, declined; (2) hoist the `_residue_state` read out of the per-subject loop and measure, since it needs no soundness argument at all; (3) only then design the memo, with the interleaved-write argument written down.

## Traps

⚠ **Read your id’s entry in [`perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) — INCLUDING its verifier corrections — and that file’s §"Traps the numbers do not carry", before taking this id.** The audit’s own rule: *do not implement from titles alone*. Eighteen findings survived adversarial verification with **0 refuted**, but several impacts were downgraded, several fix sketches were corrected, and one fix was refuted outright while its finding stood.

⚠ **Optimizing anything INSIDE this function has a 2.0% ceiling.** The only material win is evaluating the audit set fewer times, or over fewer members. This is the decomposition trap caught at filing time rather than after a landing.

⚠ **The memo that looks obvious is not obviously sound.** `check_fn` closures read live `bf` state, and both `_reconcile` and `_reconcile_subject_edge` *write* residues between the two evaluation points, so a `(subject) → bool` memo needs an argument that no interleaved write can change the answer — not just the observation that the arguments match. That argument has not been made.

⚠ **Weaker provenance than `R6-1`..`R6-18`:** self-filed 2026-08-18, not from the two-phase workflow — no finder wrote it, no verifier adversarially reviewed it. And it **overlaps declined `R6-14`** (already measured at a 5.0% ceiling) while `R6-10` is the incremental-path twin of the same memoization idea: read both verdicts first.

⚠ **Decompose every cumulative share before quoting it as a target.** `R6-10`’s headline 59.8% was CUMULATIVE; decomposed it was `_direct_incoming` 28.4% + `_nodes_by_ids` 30.7%, and the realised win came from the two SELECTs, not the headline. `R6-19` is the same trap caught earlier.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) §`### R6-19` — the entry, **including its verifier corrections**
- the same file, §"Traps the numbers do not carry" — the round-wide traps. Read the section; it is short, and it is the only home for how many there are. (This line used to say "the five", attributed to the tree generator recounting them at generation time. That generator was deleted with `.scratch/tasktool/` on 2026-09-07, so the attribution named a mechanism that could not run — `TK61`, reworded 2026-09-07b. A bare "five" with no attribution would have been worse: that is an unsourced restated count.)
- [`R6_PROFILE_2026-08-17.md`](benchmarks/results/R6_PROFILE_2026-08-17.md) — verdicts, method, and the two honest limits (in-memory SQLite understates statement-count wins; cProfile depresses throughput)
- `index_v4/bulk_backfill.py::_BulkBackfill._reconcile_subject_edge` — the code
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the fence and the reopening rule
- `python scripts/task.py show R6` — the parent: round-wide order, traps and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21

**Migrated by `migrate.py`, and this row is a CORRECTION.** The first migration pass classified every id whose disposition string was not literally `closed` as retired, which wrote this live item into `retired-ids.txt` — an irreversible sink, since `task.py` refuses to re-mint a retired id. Its true disposition (`MOTIVATED, unlanded`) is taken from `docs/perf-round6-audit-2026-08.md`, the audit that owns these ids, not from the `R6` board row’s summary prose (which undercounts the land list by one and overcounts the declines by one). `parent: R6` makes the round a rollup: closing the last child is what reports that `R6` itself can close. **`created` (`2026-08-18`) is RECORDED, not approximated** — but it is recorded by a DIFFERENT source than the other thirteen children: the audit doc states `2026-08-15` for itself and explicitly disclaims this id (*"NOT a product of the 2026-08-15 audit — no finder wrote it, no verifier adversarially reviewed it"*). `2026-08-18` is the filing date its own `### R6-19` entry heading carries. `moved` is the `R6` board row’s value.
