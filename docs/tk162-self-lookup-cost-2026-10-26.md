# `TK162` — what TK144's implicit-userset pass costs graph lookups: measured

> **FROZEN 2026-10-26 — provenance, not a living document.** Status lines below are
> as-of-then and several may now be false; live state: `HANDOFF.md` + the session
> ledger. Corrections are appended dated at the top, never edited into the body.

Frozen at `TK162`'s close. Measurement only; perf stays deprioritized (user, 2026-09-22c).

**Provenance.** Every figure is first-hand PROBE: `benchmarks/tk162_self_lookup_bench.py`,
run 2026-10-26 by the session that closed TK162. The raw records (one JSON line per store
size and schema, with machine load before and after) are TRACKED in
`benchmarks/results/tk162-self-lookup-2026-10-26.jsonl`. The code reading is first-hand
READ of `src/zanzibar/graphindex/wildcard.py` on 2026-10-26.

## Verdict

**Yes, the user docs need a warning, and they now carry one.** A graph `lookup` for a
**userset subject** on a schema with `and` / `but not` is linear in the number of objects
of each derived relation's type: 0.2 s at 1k tuples, 2 to 2.6 s at 10k, and **21 to 29 s
at 100k**. That is 60 to 170 times the same lookup without the pass. Nothing else that
was measured is affected materially: reverse lookups stay at 2 to 16 ms, plain-user
lookups are unchanged, and on a schema with no derived relation the same userset lookup
stays at 4 to 7 ms at every size.

Landed: `userdocs/explanation/limits.md` § "Lookups for a userset: slow on large stores
with `and` / `but not`" (replaces "a cost that has not been measured") and a pointer to it
from `userdocs/how-to/query-access.md` § "List what a subject can access".

## Why (READ)

`src/zanzibar/graphindex/wildcard.py::WildcardIndex._self_lookup`, its derived half: for
every derived family `(t, rel)` it loads `_entity_names(t)` (every concrete node name of
that type) and runs a full `check` per name. So the cost is
`sum over derived families of |entities of t|` checks per lookup, independent of the
answer size. `::_self_reverse_derived` only checks a candidate set drawn from the
operands' reverse closures, which is bounded by the answer neighbourhood, hence flat.
`::_self_reverse_extra` is set arithmetic except for a userset `any` marker
(`[T:*#p]` wildcard usersets), where it calls `_witnessed_names(t)`: also linear, NOT
measured here (no wildcard userset in the bench schema; userdocs says so).

## Setup

- Backend: SQLite file, `Store(..., paranoia='off')`, sync. Precondition bulk-inserted and
  built with `build_index(..., bulk=True)` (`benchmarks/fanout_cost_bench.py::seed`).
  One process per store size.
- Schema `boolean`: `group.active: member but not banned` and
  `doc.can_view: viewer but not blocked`, plus the computed chain
  `doc.owner -> editor -> viewer`. Schema `plain`: the same text with every `but not`
  read as `or` (no derived family).
- Data per size `n`: `n//8` docs x 4 tuples, `n//20` groups x 10 members (plus a ban on
  every 5th and some nesting), `max(100, n//10)` users. At n = 100,000: 102,249 tuples,
  114,500 nodes, 12,500 docs, 5,000 groups.
- Modes: `on` = the shipped read. `off` = the same `Store` with
  `WildcardIndex._reflexive_reads` forced False, which skips the three TK144 passes (the
  pre-TK144 read path; its answers then omit the implicit usersets, so it is a cost
  baseline, not a correct answer). `set` = `SetEngine.lookup` / `lookup_reverse` on the
  same store.
- Timing: median of >= 3 reps, more within a 2 s budget (max 30).
- Machine: the shared laptop, 7 python processes present; whole-system CPU busy 15 to 30 %
  around the points (recorded per point in the JSONL). Single-threaded bench, so the
  absolute numbers carry some noise; the ratios and the linear growth do not depend on it.
- **`agree` was true for every query at every size, both schemas**: the shipped graph
  answer equals the set engine's, keys and markers.

## Results — schema `boolean` (median ms)

| query | n=1k on / off / set | n=10k on / off / set | n=100k on / off / set |
| --- | --- | --- | --- |
| lookup group:g0#member | 222 / 3.7 / 0.22 | 2,192 / 18 / 0.25 | 20,884 / 230 / 0.24 |
| lookup doc:d0#owner | 233 / 2.7 / 0.20 | 2,572 / 24 / 0.35 | 29,039 / 174 / 0.23 |
| lookup user:u0 (control) | 4.8 / 6.6 / 1.7 | 26 / 25 / 2.2 | 196 / 201 / 2.6 |
| reverse viewer doc:d0 | 2.3 / 1.3 / 0.14 | 3.6 / 2.1 / 0.24 | 2.5 / 1.4 / 0.16 |
| reverse can_view doc:d0 | 15 / 1.8 / 0.22 | 18 / 3.1 / 0.30 | 16 / 2.1 / 0.24 |
| reverse active group:g0 | 14 / 4.1 / 0.20 | 13 / 4.1 / 0.16 | 9.9 / 2.1 / 0.17 |

Implicit answers added by the pass: 2 (group:g0#member), 4 (doc:d0#owner), 0 (user:u0),
3 / 4 / 2 (the three reverses), at every size.

## Results — schema `plain` (median ms, `on` / `off`)

| query | n=1k | n=10k | n=100k |
| --- | --- | --- | --- |
| lookup group:g0#member | 3.5 / 1.3 | 3.8 / 1.2 | 6.5 / 1.8 |
| lookup doc:d0#owner | 4.2 / 0.67 | 4.0 / 0.62 | 5.3 / 0.69 |
| lookup user:u0 (control) | 2.3 / 2.3 | 2.6 / 2.6 | 5.5 / 4.7 |
| reverse viewer doc:d0 | 2.4 / 1.3 | 2.2 / 1.5 | 2.5 / 1.5 |
| reverse can_view doc:d0 | 3.1 / 1.8 | 2.2 / 1.3 | 2.7 / 1.4 |
| reverse active group:g0 | 3.1 / 1.2 | 2.2 / 1.8 | 2.5 / 1.3 |

## A side finding (not TK144's)

On the `boolean` schema the **control** lookup (`user:u0`, no TK144 pass) also grows
linearly: 5 ms at 1k, 26 ms at 10k, 200 ms at 100k, against 5.5 ms on `plain` at 100k.
That is `WildcardIndex._collect_residue_memberships`, which loads and JSON-decodes every
`Residue` row of the store per lookup: the already-filed `R6-4` ("boolean graph lookup
full-scans every residue row", REASONED match, not profiled here). The `off` column of the
userset lookups includes the same scan. Recorded on `R6-4`; no user-docs change made for
it in this session (200 ms at 100k tuples is not a request-path hazard of the same order).

## Not done (deliberately)

- No optimisation. A cheaper `_self_lookup` (e.g. candidate entities from the subject's
  reverse neighbourhood instead of every entity) changes the modelled algorithm and needs
  a Lean update (CLAUDE.md "Perf work & the Lean model"); perf is deprioritized. If it is
  ever wanted, it is a new row, motivated by the table above.
- PostgreSQL not measured. The cost is a count of `check` calls, so it should scale the
  same way; UNVERIFIED.
- Wildcard-userset schemas (`_self_reverse_extra`'s `_witnessed_names` loop) not measured.
