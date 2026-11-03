# Decision import: the conservation check (2026-11-03)

FROZEN 2026-11-03 (session 2026-11-03a): the check the context-engine CE-167 import script ran on the import;
never edited. `check_decisions.py` reads the log from git and each record with the engine's parser.

```text
docs/architecture/decision-log.md at 4826a01: 9 sections, 272 non-blank section lines; 5 header lines above the first section (not imported, kept in the frozen log)
records in decisions/: 9
section lines not in their record: 0; records with no section: 0
  DEC-1: unrecorded, 2026-07-07, BUILT: Graph index
  DEC-2: unrecorded, 2026-07-07, BUILT: Set engine
  DEC-3: unrecorded, 2026-07-07, BUILT: Boolean relations in the graph index (the IVM build)
  DEC-4: unrecorded, 2026-07-07, BUILT: The connected store (round 2)
  DEC-5: unrecorded, 2026-07-23, BUILT: The connected store (round 3 — multi-instance / HA)
  DEC-6: unrecorded, 2026-08-29, BUILT: Reads are lenient — a cross-backend contract, not a per-backend default
  DEC-7: owner, 2026-09-29, BUILT: Wildcards beyond OpenFGA, and the registry idiom (user decisions, `ASK-2`)
  DEC-8: owner, 2026-09-22, BUILT: The project goal: honest, legible assurance, not wider (user decision, 2026-09-2
  DEC-9: unrecorded, 2026-07-07, BUILT: Non-goals (documented hooks only)
PASS
```

Sabotaged before it was believed, each FAIL: line dropped, line changed, record invented, title changed.

check_decisions.py sha256 12ff456010ef2486ad0f759d20aff9f0ec08cac74110efa55e2ef6eea64a20e6.
