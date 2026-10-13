---
id: TK141
title: verify.sh prints each phase's start time and an ETA from the last PASSED ledger run
brief: verify.sh start banner + ETA from the ledger; patch in body, land FIRST in a session (stales all phases)
pri: NOW
size: S
deps: []
related: []
parent:
labels: []
source: hand
source_hash:
created: 2026-10-13c
moved: 2026-10-13c
updated: 2026-10-13c
closed:
---

User request 2026-10-13c: "for all test tiles, can the script print out the start
timestamp? just wanna be able to guess accurately how long more it'll take". Built and
tried that session, then ROLLED BACK at the user's word because a `verify.sh` edit stales
every phase and the full ten-phase rerun was not worth it at session end. Land it FIRST
THING in a session, before any other change, so the one full gate run it needs is the
run that session would do anyway.

## The patch (tried 2026-10-13c, worked)

Insert in `formal/verify.sh` directly after the line
`gate_fact() { GATE_FACTS="${GATE_FACTS:+$GATE_FACTS }$1"; }` (the ledger block, child
side, which runs once per phase in the re-exec'd child, so it lands at the top of the run
log too):

```bash
# Start banner (user request 2026-10-13): the start time, plus an ETA from the duration
# of the last PASSED run of this same phase in the ledger, so a watcher can tell how long
# is left. Informational only: nothing parses it, and a missing ledger just drops the ETA.
GATE_LAST_DUR="$(awk -F'\t' -v p="$PHASE" '$3 == p && $4 == "PASSED" { d = $2 } END { print d }' \
  "$GATE_RUNS_DIR/ledger.tsv" 2>/dev/null || true)"
if [ -n "$GATE_LAST_DUR" ]; then
  GATE_ETA="$(date -d "+${GATE_LAST_DUR} seconds" +%H:%M:%S 2>/dev/null || true)"
  echo "=== verify.sh: phase '$PHASE' started $(date +%H:%M:%S); last PASSED run took ${GATE_LAST_DUR}s${GATE_ETA:+, so expect ~$GATE_ETA} ==="
else
  echo "=== verify.sh: phase '$PHASE' started $(date +%H:%M:%S); no PASSED run of this phase in the ledger to estimate from ==="
fi
```

Observed output (FIRST-HAND, 2026-10-13c):
`=== verify.sh: phase 'lean' started 21:45:09; last PASSED run took 99s, so expect ~21:46:48 ===`
and `... 'conf-tile:1/5' started 21:50:07; last PASSED run took 646s, so expect ~22:00:53 ===`
(that tile then PASSED). Nothing in `*.py` / `*.sh` / `*.yml` parses `=== verify.sh` lines
(grepped 2026-10-13c; only the final PASSED banner at `formal/verify.sh` ~L1431 exists).

Also add to `docs/gate-runbook.md`, after the `.gate-runs/` artifact table: the first line
of every phase's output (and run log) is this banner; the ETA is the newest PASSED ledger
row for the same phase, a guess not a timeout; read the top of the newest
`.gate-runs/*.log` to see how far along a running phase is.

## Traps

- ⚠ Do not edit `verify.sh` while a phase is running: bash reads a running script
  incrementally.
- ⚠ A phase run as `(bash formal/verify.sh ... > $L 2>&1) &` inside a harness command
  survives a TaskStop: on 2026-10-13c the stopped conf-tile:3/5 left 4 `bash` + 1 `pytest`
  orphans and a held `.gate-runs/gate.lock`. Kill the orphans by PID (check the command
  line; other repos' sessions run pytest too), then
  `python scripts/gate_lock.py release .gate-runs/gate.lock --owner <owner= from the lock>`.
- Optional: CI (`.github/workflows/gate.yml`) gets the banner for free; `date -d` is GNU
  and works in Git Bash and on ubuntu-latest.

## Read first

- `formal/verify.sh` (the ledger block, child side: `GATE_STARTED`, `gate_fact`).
- `docs/gate-runbook.md` (the `.gate-runs/` artifact table).

## Log

### 2026-10-13c

Promoted to NOW by the user (2026-10-13c): land it first thing next session, before any other change, so its one full gate run is the run that session needs anyway.
