---
id: TK85
title: give audit_fixpoint (I9) a production-reachable entry point, framed as repair/diagnosis
brief: TK74 sec 8.8's rider, demoted by sec 9.9 AMENDMENT 1: every I9 call site is under tests/ (census 2026-09-19b)
pri: LATER
size: S
deps: []
related: [TK74, TK82, TK73]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-19b
moved: 2026-10-04g
updated: 2026-10-04g
closed:
---

FILED 2026-09-19b as the unfiled "Still owed" rider carried on the banner since the `TK74`
fan-out. Source: [`docs/tk74-staleness-net-2026-09-18.md`](../docs/tk74-staleness-net-2026-09-18.md)
sec 8.8 ("Rider, and arguably the real deliverable"), **demoted** by sec 9.9 AMENDMENT 1, and
re-stated as `TK82`'s still-owed line in
[`docs/tk82-cascade-fixpoint-tier-2026-09-19.md`](../docs/tk82-cascade-fixpoint-tier-2026-09-19.md).

**The fact, READ first-hand this session (2026-09-19b).** `grep -rn audit_fixpoint` over
`index_v4/ connectedstore/ setengine/ scripts/ tests/`: the only *definition* is
`index_v4/processor.py::DeltaProcessor.audit_fixpoint` (`:1838`); the other four hits in
`index_v4/` are DOCSTRING mentions (`invariants.py:61`, `:231`, `processor.py:1299`, `:1742`).
**Every one of the ~40 call sites is under `tests/`** (`tests/parity.py:98` and
`tests/test_matrix.py:81` are the per-op "paranoia dose"). Zero call sites in
`connectedstore/`, zero in `scripts/`, and `invariants.py:231` says it is left out of
`install_paranoia` *by design*. So I9 -- the only detector for the SCHEDULING-side miss class
-- is dead code in production.

**Why this is NOT simply "wire it into a paranoia tier" (sec 9.9 AMENDMENT 1).** Staleness in
the measured class is transient: 31 of 34 `demorgans_reverse` arms were transiently divergent
and **0 of 34** still divergent after the workload -- later writes launder it. A periodic or
end-of-run sweep is therefore **worth =~0 as a detector** for that class. The adjudication
already made: `TK82` shipped the per-cascade `'fixpoint'` tier (O(cascade work)); this rider
is the OTHER half, and sec 9.9 says "if only one of the two ships, ship the tier". It shipped.
So this row is deliberately not NOW.

**What the row is actually for.** `audit_fixpoint` is O(live derived keys in the store),
unbounded by the size of the write (sec 9.9, REASONED from the code and confirmed by the
measured shape: scheduled-union 112 vs `audit_fixpoint` scope 233 derived keys over 38
cascades on `heterogeneous_tupleset`). It can never be a write-path default. The deliverable
is a **repair/diagnosis entry point** -- an operator-invocable audit whose docstring already
names `backfill()` as the recovery path (`processor.py:1839-1840`) -- not a net. Candidate
shapes, none adjudicated yet:
  1. a `scripts/` operator command (`audit` + `--repair` calling `backfill()`), the cheapest
     and the one that matches the repair/diagnosis framing;
  2. a `ConnectedStore` method so the composed system exposes it (note the layering rule in
     `CLAUDE.md`: `connectedstore/` may import both backends, never the reverse);
  3. a fifth paranoia level above `'fixpoint'` -- **probably wrong**: `TK82` sec 9.x showed the
     ladder is a TOTAL ORDER and placement decides blast radius, and an O(store) check on
     every commit is a different kind of thing from the four existing per-op tiers.
Decide 1 vs 2 on the row before writing code.

**Traps, inherited and earned.** (a) This is an assurance gap, NOT a live bug -- sec 8.9's
framing must survive into whatever ships; the board's "Known live correctness bugs: 0" line is
unaffected. (b) `docs/sabotage-procedure.md` applies in full: an entry point that cannot fire
converts an acknowledged gap into a false green, so whatever ships needs a sabotage (corrupt a
derived key behind the processor's back, watch the entry point raise `InvariantViolation`, and
control the instrument) plus a module mutation sweep with an `M0` attributing control.
(c) ⚠ `audit_fixpoint` is a REPAIRING MUTATOR in the same sense `reconcile` is -- it calls
`self.reconcile(...)` and raises on the first key that changed, which means it has already
written that key's repair before it raises, and it clears `self._bumped`. An entry point that
swallows the exception silently repairs and reports nothing. That is exactly the
`TK73`/`TK82` shape ("when two candidate fixes both turn the witness green, the witness cannot
choose between them").

Anchors: `index_v4/processor.py::DeltaProcessor.audit_fixpoint` (`:1838`, dated 2026-09-19b),
`index_v4/invariants.py::install_paranoia`, `docs/architecture/verification.md:87` (the I9 row
already says "run per-op by the matrix/parity graph backends -- **not** by `check_invariants`",
which is accurate and should stay accurate if this ships).

## Read first

- [`docs/tk74-staleness-net-2026-09-18.md`](../docs/tk74-staleness-net-2026-09-18.md)
  sec 8.8 (the rider, round-1 design) and sec 9.9 AMENDMENT 1 (the demotion, and why a
  periodic sweep is worth =~0 as a detector for this class).
- `index_v4/processor.py` -- `DeltaProcessor.audit_fixpoint` is the subject; read it as a
  REPAIRING mutator (it calls `reconcile` and raises after the repair has been written).
- `index_v4/invariants.py` -- `install_paranoia` and this module's tier table, for why I9
  is deliberately NOT among the paranoia checks.
- [`docs/sabotage-procedure.md`](../docs/sabotage-procedure.md) -- mandatory before adding
  any check here; an entry point that cannot fire converts an acknowledged gap into a
  false green.

## Log

### 2026-10-04g

Closability sweep 2026-10-04g (agent report, UNVERIFIED first-hand unless marked; the session did not act on it): overlaps TK3 almost entirely (see TK3 log 2026-10-04g): merge or narrow one of them.
