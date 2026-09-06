---
id: TK56
title: delete T1/T3's undischargeable hValid : AllValid T; instantiate T3 at a concrete executed store
brief:
pri: LATER
size: M
deps: []
related: [P17]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-06
moved: 2026-09-06
updated: 2026-09-06
closed: 2026-09-06
---

Delete the never-used T1 hypothesis `hValid : AllValid T` (built on the `opaque ValidIdent`, so undischargeable at any non-empty store) from `setEngine_correct`, `backend_equivalence` (T3), `exclusion_effective` (T6a) and every `Equiv.lean` ladder rung; delete `AllValid` and the opaque; then land the first concrete instantiations of T3 -- `W4WitnessDirect.equivalence_applies` and `Exec.lean::graphRunOps_directArm_backend_equivalence` (a closed `exists sigma` at an executed store where both backends answer `true`).

Second-opinion verdict (2026-09-06, on the question "what pushes closest to set-engine = graph-index equivalence"): this is hygiene, not reach -- T3 was already stated but had no instance; after this it has two. The REACH step is `P17` (the default bulk constructor is unmodeled: `ReachedBy` only grows from `emptyState`).

## Traps

- `Core/Ident.lean` is a root import: any edit there is a 20-40 min cold rebuild, over the harness cap. Pre-warm per `docs/gate-runbook.md` sec 2.
- Three goldens regenerate together (`headline_statements.txt`, `headline_definitions.txt`, `audited_theorems.txt`); each needs its `formal/history/PROOF_STATUS.md` justification.
- `sorry_scan.py` now refuses `opaque` at declaration position (tree carries zero); re-introducing a placeholder predicate is a gate failure, not a doc note.

## Log

### 2026-09-06

Landed 2026-09-06. hValid/AllValid/opaque ValidIdent deleted (49 Lean sites, 5 files); T1 unconditional; T3/T6a carry exactly T2b's hypotheses; two T3 instantiations added (W4WitnessDirect.equivalence_applies, Exec.lean::graphRunOps_directArm_backend_equivalence, the latter with both backends = true). Cold build LAKE_RC=0 first try. Pins regenerated 49->51 statements, 250->251 defs, 584->587 audits (also caught the unpinned graphModeAnswers_eq_sem). sorry_scan refuses opaque (control: HEAD's Ident.lean -> 1 finding rc=1; live 0/70). Gate: ten phases run after this close -- result in docs/history/session-log.md 2026-09-06. Next reach step: P17 (bulk constructor unmodeled). Detail: formal/history/PROOF_STATUS.md 2026-09-06 sec 1-8.
