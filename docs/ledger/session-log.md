# Session ledger

Append-only, newest first, one entry per session (FRAMEWORK §7.1).

---

## 2026-11-04a · kind: open

- **opened:** 2026-11-04T19:08:09+08:00 by claude-code/claude-opus-5-5
- **start head:** 3e63fd73e6d0e52f4f780b5899d3f18e469ced9a

---

## 2026-11-03a · kind: close

- **rows:** TK-1..TK-300, ASK-1..ASK-3 (imported from task.py); DEC-1..DEC-9 (imported)
- **receipts:**
  - guards: verify.sh not run at close: it runs on the closed tree next (CLAUDE.md: records first,
    then the gate); context-engine lint clean; the touched test modules 314 passed
  - read: zanzibar CLAUDE.md, HANDOFF.md, docs/README.md, docs/architecture/decision-log.md;
    context-engine CE-167 surveys
- **summary** (the owner digest):
  - context-engine adopted on branch ce-cutover (engine 309641b): kit, CLAUDE.md, context.toml;
    nothing pushed, merged or tagged
  - the task.py board is engine records in tasks/ (TK185 is TK-185; other series TK-186..TK-300;
    ASK-1..3 kept); old ids are aliases; conservation PASS
  - scripts/task.py retired from the gate (verify.sh 4g); it refuses an engine tree; handoff_lint
    reads the engine's records
  - docs/architecture/decision-log.md imported as DEC-1..DEC-9, one per section (conservation PASS),
    FROZEN in place; the old session ledger FROZEN
  - HANDOFF archived to docs/archive/HANDOFF.md; the new note is the engine's shape
  - scripts/gate_status.py: context.toml and docs/ledger/ are prose to the tiles' code scope
- **Still owed:**
  - the owner's call on merging ce-cutover into master
  - the owner's go to push (the full gate first, then a CI watcher); no tag
  - the charter and criteria with the owner (both still the kit's templates)
- **start head:** e0b7a1b2e6e5c76d5b6fab5ac4e0ea87d173120f
