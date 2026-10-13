---
id: TK85
title: give audit_fixpoint (I9) a production-reachable entry point, framed as repair/diagnosis
brief: TK74 sec 8.8's rider, demoted by sec 9.9 AMENDMENT 1: every I9 call site is under tests/ (census 2026-09-19b)
pri: SOMEDAY
size: S
deps: []
related: [TK74, TK82, TK73]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-19b
moved: 2026-10-13
updated: 2026-10-13
closed:
---

FILED 2026-09-19b as the unfiled "Still owed" rider carried on the banner since the `TK74`
fan-out. Source: [`docs/tk74-staleness-net-2026-09-18.md`](../docs/tk74-staleness-net-2026-09-18.md)
sec 8.8 ("Rider, and arguably the real deliverable"), **demoted** by sec 9.9 AMENDMENT 1, and
re-stated as `TK82`'s still-owed line in
[`docs/tk82-cascade-fixpoint-tier-2026-09-19.md`](../docs/tk82-cascade-fixpoint-tier-2026-09-19.md).

**The fact, READ first-hand this session (2026-09-19b).** `grep -rn audit_fixpoint` over
`src/zanzibar/graphindex/ src/zanzibar/connectedstore/ src/zanzibar/setengine/ scripts/ tests/`: the only *definition* is
`src/zanzibar/graphindex/processor.py::DeltaProcessor.audit_fixpoint` (`:1838`); the other four hits in
`src/zanzibar/graphindex/` are DOCSTRING mentions (`invariants.py:61`, `:231`, `processor.py:1299`, `:1742`).
**Every one of the ~40 call sites is under `tests/`** (`tests/parity.py:98` and
`tests/test_matrix.py:81` are the per-op "paranoia dose"). Zero call sites in
`src/zanzibar/connectedstore/`, zero in `scripts/`, and `invariants.py:231` says it is left out of
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
     `CLAUDE.md`: `src/zanzibar/connectedstore/` may import both backends, never the reverse);
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

Anchors: `src/zanzibar/graphindex/processor.py::DeltaProcessor.audit_fixpoint` (`:1838`, dated 2026-09-19b),
`src/zanzibar/graphindex/invariants.py::install_paranoia`, `docs/architecture/verification.md:87` (the I9 row
already says "run per-op by the matrix/parity graph backends -- **not** by `check_invariants`",
which is accurate and should stay accurate if this ships).

## Read first

- [`docs/tk74-staleness-net-2026-09-18.md`](../docs/tk74-staleness-net-2026-09-18.md)
  sec 8.8 (the rider, round-1 design) and sec 9.9 AMENDMENT 1 (the demotion, and why a
  periodic sweep is worth =~0 as a detector for this class).
- `src/zanzibar/graphindex/processor.py` -- `DeltaProcessor.audit_fixpoint` is the subject; read it as a
  REPAIRING mutator (it calls `reconcile` and raises after the repair has been written).
- `src/zanzibar/graphindex/invariants.py` -- `install_paranoia` and this module's tier table, for why I9
  is deliberately NOT among the paranoia checks.
- [`docs/sabotage-procedure.md`](../docs/sabotage-procedure.md) -- mandatory before adding
  any check here; an entry point that cannot fire converts an acknowledged gap into a
  false green.

## Log

### 2026-10-04g

Closability sweep 2026-10-04g (agent report, UNVERIFIED first-hand unless marked; the session did not act on it): overlaps TK3 almost entirely (see TK3 log 2026-10-04g): merge or narrow one of them.

### 2026-10-13

2026-10-13 (assurance triage, lane L3): TK3's I9 half MOVES HERE. TK3 is narrowed to the cascade-precondition half only (nothing checks that a boolean write ran run_cascade). The I9 picture as of 2026-10-13 (READ): TK82's 'fixpoint' tier (invariants.py::PARANOIA_FIXPOINT -> processor.py::DeltaProcessor._check_cascade_fixpoint) covers execution-side misses for keys a cascade SCHEDULED. A key never scheduled is detectable only by DeltaProcessor.audit_fixpoint, which still has 0 production callers. That never-scheduled class is this row's. formal/README.md and formal/SEMANTICS.md sec 7.7 / 11-A1 now point here for it.

DECISION 2026-10-13 (lane L7; executive call made by a separate judgement subagent under CLAUDE.md 'Who decides', recorded here as the decision of record and implemented by this lane): ACCEPT THE GAP. Build neither shape 1 nor shape 2 (shape 3 was already rejected on this row). Row demoted LATER -> SOMEDAY (promote op of the same date; reopen trigger below).

Why shape 1 (a `scripts/` operator command) is rejected. READ 2026-10-13: `pyproject.toml` has no `[project.scripts]`, and `[tool.setuptools.packages.find] where = ["src"]` (pyproject.toml:62-63). So `scripts/` is not in the wheel, and a scripts/ command can only be run from a checkout. That is not "production-reachable" for anyone who installs zanzibar-index. It would be the first operator-facing script in a directory that holds only repo tooling. It would also need a mandatory sabotage and an M0 mutation sweep, for a sweep that docs/tk74-staleness-net-2026-09-18.md sec 9.9 AMENDMENT 1 already rates at about 0 as a detector (laundered transient staleness: 0 of 34 arms were still divergent after the workload).

Why shape 2 (a `ConnectedStore.verify()`) is rejected. REASONED from the code (READ: `src/zanzibar/graphindex/processor.py::DeltaProcessor.audit_fixpoint`, def at :1663 on 2026-10-13): audit_fixpoint is a REPAIRING MUTATOR. It calls `self.reconcile(...)` per key, writes the FIRST stale key's repair, then raises `InvariantViolation`. Later keys are left untouched, and `_bumped` is cleared only on the clean path. A verify() method that wraps it is the TK73/TK82 "both fixes turn the witness green" shape. Making it honest would take a non-mutating dry-run reconcile. That is an algorithm change the Lean twin would have to follow (CORRESPONDENCE.md sec 8), which is too much for a diagnosis tool nobody has asked for.

What IS true today. Every fact below was READ 2026-10-13.
(a) `grep -rn audit_fixpoint src/ scripts/` finds only the definition and docstring mentions (invariants.py:69, :239; processor.py:1150, :1572-1579). There is no production call site.
(b) The detector IS reachable through the public attribute `ConnectedStore.proc` (`src/zanzibar/connectedstore/store.py:209`; it is None when the compiled schema has no plans). Call `store.proc.audit_fixpoint()` in a transaction the caller ROLLS BACK for diagnosis.
(c) The whole-store repair `DeltaProcessor.backfill()` (processor.py::DeltaProcessor.backfill, :1645) already has a production caller, `src/zanzibar/connectedstore/build.py:265` (`build_index(bulk=False)`). Repair is backfill() plus COMMIT, not audit_fixpoint plus commit, because the latter fixes only the first stale key.
(d) Execution-side misses are covered per cascade by the TK82 'fixpoint' paranoia tier (`invariants.py` module doc :56-71; `DeltaProcessor._check_cascade_fixpoint`). The never-SCHEDULED class is the only one audit_fixpoint alone detects.

LANDED (lane L7, 2026-10-13): one docstring edit, no behaviour change, in `src/zanzibar/graphindex/processor.py::DeltaProcessor.audit_fixpoint`. It states the contract above: repairs then raises on the first stale key, later keys untouched, `_bumped` cleared only when clean, roll back for diagnosis, backfill()+commit for repair, never swallow the exception, O(live derived keys) and never a write-path default or paranoia tier, the 'fixpoint' tier covers execution-side misses, this audit is the only detector of the never-scheduled class, reachable via `ConnectedStore.proc`, and backfill() is production-called by `build_index(bulk=False)`. The file parses, and 97 tests passed (test_cascade_fixpoint_tier, test_processor, test_reg15_security_hardening, test_stored_cache_scope, test_backfill_enumeration, test_reg_tk91_live_keys_repair, test_refused_shape_comments). A docstring needs no sabotage.

Scope merge: TK85 absorbs TK3's "I9 is test-only" half. TK3 keeps only the cascade-precondition (A1) half. The overstated formal passages (formal/README.md residual paragraph and formal/SEMANTICS.md sec 7.7 / 11-A1) were corrected by lane L3 the same day.

REOPEN TRIGGER: a consumer asks for a store audit, OR a bug of the never-scheduled class appears in the wild (zero across both TK74 rounds). On reopen, start from shape 2 with a non-mutating reconcile, and budget the Lean-correspondence work.
