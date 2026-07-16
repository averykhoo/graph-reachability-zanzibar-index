<!-- RETIRED 2026-07-16: round 5 opened after round 4 and concluded the measured perf worklist is EXHAUSTED — the two remaining candidates (N13, N14) were assessed and DECLINED on a fresh 2026-07-16 profile (no code landed this round). This is the round-5 assessment record, archived here. Living docs: standing perf guardrails → docs/perf-next-round.md; measured numbers → benchmarks/results/PERF_ANALYSIS.md "Applied" + benchmarks/results/ROUND4_COMPARISON_2026-07-16.md; gates → docs/gate-runbook.md. -->

# Perf round 5 — assessment record (2026-07-16): worklist exhausted, no landings

Round 5 opened on the slim post-round-4 worklist. It carried exactly two
remaining candidates, both filed as **conditional** ("needs a motivating
measurement or a design call first"): **N13** and **N14**. A fresh profile
this session declined both. **Nothing landed** — round 4 is the sensible
stopping point for everything the current harnesses can measure. This file
retires the two candidate write-ups verbatim and records why each was declined.

## The measurement that closed the round

`benchmarks.stmt_bench` (real `ConnectedStore`, sync, `paranoia=off`), single
job, no concurrent bench/pytest. Command:

```bash
PY="C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe"
"$PY" -m benchmarks.stmt_bench
```

Result — **byte-identical to `STMT_BASELINE_2026-07-14.md` and
`ROUND4_COMPARISON_2026-07-16.md §3`; no drift, no new headroom:**

| op | stmts/op | note |
|---|--:|---|
| union `check` | **2.7** | the number that got N13 deprioritized — unchanged |
| boolean `check` | **3.1** | unchanged |

The whole `check` budget is ~3 statements: 2 point SELECTs (subject + object
node resolution via `_get_concrete`) + 1 edge-probe SELECT (already a single
row-value `IN`, `index_v4/wildcard.py`), plus a residue read on the derived
path. It runs at ~684–692 ops/s, flat.

## N13 — DECLINED (no headroom)

> ### N13. Graph `check`: batch node resolution (3–5 sequential point SELECTs → ~2) — DEPRIORITIZED
> `index_v4/wildcard.py:331-388,:428-462`. check IS round-trip-bound (388–682/s
> flat), so this is real — but **`stmt_bench` measured graph `check` at 2.7–3.1
> stmts/op already (little headroom)**, so it's deprioritized: resolution
> restructuring must preserve exact probe semantics (position rule,
> missing-node-drops-key, `:349,:363-374`), and it's fiddly, for a small win.
> Revisit only if a fresh statements-per-check profile shows more headroom;
> medium risk. Behavior-preserving if done right. Gate: matrix 4-way + lookup
> oracle + conformance.

**Why declined (2026-07-16):** the fresh profile reconfirms `check` at 2.7 /
3.1 stmts/op — the deprioritization condition ("revisit only if a fresh profile
shows more headroom") is **not met**. The premise of "3–5 sequential point
SELECTs" overstates it: the whole op is ~3 statements *including* the probe.
Best case, N13 batches the two node-resolution SELECTs into one `IN`, saving
**≤1 stmt/op** off the fastest, already-flat read path — against real semantic
risk (position rule; missing-node-drops-key at `:349`/`:363-374`). Not worth
landing.

## N14 — DECLINED (no workload exercises it)

> ### N14. Hoist `_keys_referencing` to one residue scan per `_map_deltas_to_keys` call
> `index_v4/processor.py:316-332`, called per GC'd subject at `:836-839`. M
> subject GCs = M full ResidueV1 scans + JSON decodes; hoist to one snapshot
> scan building `subject_id → [Key]`. **Scope to the step-A loop only** (the
> reconcile-step-5 calls mutate residues mid-flight). Only bites TTU/userset
> schemas N3 doesn't already elide, on churn-heavy removes. Medium risk —
> modeled delta→key territory (same class as P6): behavior-preserving only if
> the key set is provably identical; full differential + hypothesis + paranoia
> gate. Niche; needs a workload that shows it first.

**Why declined (2026-07-16):** **zero harness coverage.** `_keys_referencing`
(the full `ResidueV1` scan N14 targets) is guarded by the N3 elision
(`_cross_object_recordings_possible`) and returns `[]` immediately unless a
leaf kind is outside `{'closure','derived-computed'}`. The only harness doing
removes is `stmt_bench`, whose boolean schema (`can_view = viewer but not
blocked`) compiles to all-`closure` leaves → the flag is `False` → the scan is
already skipped. `scale_bench` / `bulk_scale_bench` do no removes at all. N14
only bites `derived-userset` / `derived-ttu` / `derived-tupleset-ttu` leaves —
a boolean operand *over a derived relation* — which no benchmark builds and no
harness drives churn against. Its own filing condition ("needs a workload that
shows it first") is not met; producing a motivating number would require
authoring a new churn workload (out of scope for a measurement-only pass).

## Outcome

Both candidates were correctly filed as conditional in `perf-next-round.md`,
and neither condition is met. **Round 5 lands no code.** The durable standing
guidance (the P12c fence, the confirmed dead-ends, the set-engine flow-graph
bridge-edge *correctness* note, and the measurement/gate hygiene) remains in
the living `docs/perf-next-round.md`; only these two now-resolved candidate
items were retired here.
