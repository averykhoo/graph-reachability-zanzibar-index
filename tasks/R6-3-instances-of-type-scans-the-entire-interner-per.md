---
id: R6-3
title: _instances_of_type scans the entire interner per type -- 0 calls in any profile
brief:
pri: HOLD
size: ?
deps: []
related: [R6-13, R6-17]
parent: R6
labels: [perf]
source: docs/perf-round6-audit-2026-08.md
source_hash:
created: 2026-08-15
moved: 2026-08-24b
updated: 2026-08-24b
closed:
---

`setengine/engine.py::SetEngine._instances_of_type`

**Measured (2026-08-17 motivating-measurement pass):** `_instances_of_type` called **0 times** across both set-engine profiles, gdrive’s object-wildcard shapes included. Round-3 `N7`’s "not exercised by profiled workloads" is now MEASURED rather than assumed.

**Verdict: UNREACHED.** Not declined and not done — the audit confirmed the code does the inefficient thing and then measured **zero calls** reaching it. `pri: HOLD` is the exact record of that: what it owes is a `T:*#P` star/wildcard workload, and the workload is the next step, not the patch.

## Traps

⚠ **Read your id’s entry in [`perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) — INCLUDING its verifier corrections — and that file’s §"Traps the numbers do not carry", before taking this id.** The audit’s own rule: *do not implement from titles alone*. Eighteen findings survived adversarial verification with **0 refuted**, but several impacts were downgraded, several fix sketches were corrected, and one fix was refuted outright while its finding stood.

⚠ **UNREACHED is not DECLINED, and `HOLD` is not a soft decline.** The audit measured **0 calls** here across every profiled workload, so no number can motivate a patch yet. What this owes is a `T:*#P` star/wildcard workload that reaches the code at all; only then is there a measurement to decline or land on. Do not close this on the absence of a number — that is the absence of a MEASUREMENT, not of a cost.

⚠ The `names_of_type` interner index is round 3’s `N7` deferral ("only with measurement"), now with two independent confirmations. **The release side must DELETE zero-count entries** or a ghost name becomes a false exists-witness — a correctness bug wearing a perf fix’s clothes.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) §`### R6-3` — the entry, **including its verifier corrections**
- the same file, §"Traps the numbers do not carry" — the round-wide traps. Read the section; it is short, and it is the only home for how many there are. (This line used to say "the five", attributed to the tree generator recounting them at generation time. That generator was deleted with `.scratch/tasktool/` on 2026-09-07, so the attribution named a mechanism that could not run — `TK61`, reworded 2026-09-07b. A bare "five" with no attribution would have been worse: that is an unsourced restated count.)
- [`R6_PROFILE_2026-08-17.md`](benchmarks/results/R6_PROFILE_2026-08-17.md) — verdicts, method, and the two honest limits (in-memory SQLite understates statement-count wins; cProfile depresses throughput)
- `setengine/engine.py::SetEngine._instances_of_type` — the code
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the fence and the reopening rule
- `python scripts/task.py show R6` — the parent: round-wide order, traps and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21

**Migrated by `migrate.py`, and this row is a CORRECTION.** The first migration pass classified every id whose disposition string was not literally `closed` as retired, which wrote this live item into `retired-ids.txt` — an irreversible sink, since `task.py` refuses to re-mint a retired id. Its true disposition (`UNREACHED — HOLD`) is taken from `docs/perf-round6-audit-2026-08.md`, the audit that owns these ids, not from the `R6` board row’s summary prose (which undercounts the land list by one and overcounts the declines by one). `parent: R6` makes the round a rollup: closing the last child is what reports that `R6` itself can close. **`created` (`2026-08-15`) is RECORDED, not approximated** — it is the date the audit doc that minted these ids states for itself; `moved` is the `R6` board row’s value.

### 2026-08-24b

related-edge sweep (trial finding F1): added `related: [R6-13, R6-17]`. R6-17 is a literal duplicate and R6-13 the bulk twin; both name R6-3 in their own bodies, and R6-3 named neither -- so a session settling R6-3 (the end that gets worked) would never learn it also discharges R6-17. Edge written on the blind end; `show` computes the incoming half for the other two.
