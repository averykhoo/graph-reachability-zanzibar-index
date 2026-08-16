#!/usr/bin/env bash
# A throwaway, user-space PostgreSQL for the RDBMS leg of the gate.
#
# WHY THIS EXISTS
#   Every test in this repo has always run on in-memory SQLite, while the mechanisms
#   that matter most for multi-instance (HA) correctness -- `FOR UPDATE` row locks,
#   MVCC read snapshots, out-of-order log-id commits -- either render to nothing on
#   SQLite or cannot manifest there at all.  That made the HA work "reasoned about,
#   not tested" (`docs/history/handoff-status-2026-07.md` "Zero-trust review 2026-07-26"
#   (archived from `HANDOFF.md` 2026-07-29) §P5).  This script stands up a
#   real server so `tests/test_postgres_ha.py` can exercise them.
#
# WHAT IT IS *NOT*
#   Not a system install and not a service.  The server binaries come from a conda
#   env, the cluster lives in a scratch directory, it listens on 127.0.0.1 only, on a
#   non-default port, and `stop` + `destroy` remove it without a trace.  Nothing is
#   registered with Windows.
#
# USAGE
#   bash scripts/pg_local.sh start     # initdb (first run) + start; prints the DSN
#   bash scripts/pg_local.sh dsn       # print the DSN only (for eval/export)
#   bash scripts/pg_local.sh status
#   bash scripts/pg_local.sh stop
#   bash scripts/pg_local.sh destroy   # stop + delete the cluster directory
#
#   eval "$(bash scripts/pg_local.sh env)"   # exports ZANZIBAR_PG_DSN
#
# OVERRIDES (all optional)
#   ZANZIBAR_PG_BIN    directory holding initdb/pg_ctl/psql   (default: probed, below)
#   ZANZIBAR_PG_DATA   cluster directory                      (default: below)
#   ZANZIBAR_PG_PORT   listen port                            (default: 55432)
set -euo pipefail

PORT="${ZANZIBAR_PG_PORT:-55432}"
DB=zanzibar_test

# --- locate the server binaries -------------------------------------------------
# Preference order: an explicit override, then a conda env named `zanzibar-pg`
# (create it with:  conda create -n zanzibar-pg -c conda-forge postgresql=17 -y),
# then whatever is on PATH.  Windows conda puts them under Library/bin.
default_bin() {
    local roots=()
    [[ -n "${CONDA_ROOT:-}" ]] && roots+=("$CONDA_ROOT")
    roots+=("$HOME/anaconda3" "$HOME/miniconda3" "$HOME/miniforge3"
            "/c/Users/${USER:-${USERNAME:-nobody}}/anaconda3" "/opt/conda")
    local r
    for r in "${roots[@]}"; do
        [[ -x "$r/envs/zanzibar-pg/Library/bin/pg_ctl.exe" ]] && \
            { echo "$r/envs/zanzibar-pg/Library/bin"; return; }
        [[ -x "$r/envs/zanzibar-pg/bin/pg_ctl" ]] && \
            { echo "$r/envs/zanzibar-pg/bin"; return; }
    done
    command -v pg_ctl >/dev/null 2>&1 && { dirname "$(command -v pg_ctl)"; return; }
    echo ''
}
BIN="${ZANZIBAR_PG_BIN:-$(default_bin)}"
if [[ -z "$BIN" ]]; then
    echo "pg_local: no PostgreSQL binaries found." >&2
    echo "  conda create -n zanzibar-pg -c conda-forge postgresql=17 -y" >&2
    echo "  (or set ZANZIBAR_PG_BIN to a directory containing pg_ctl)" >&2
    exit 1
fi

# --- cluster location -----------------------------------------------------------
# Deliberately OUTSIDE the repo: a stray `git add -A` must never capture a database.
default_data() {
    if [[ -n "${LOCALAPPDATA:-}" ]]; then
        # LOCALAPPDATA is a Windows path; make it POSIX for this bash.
        echo "$(cygpath -u "$LOCALAPPDATA" 2>/dev/null || echo "$LOCALAPPDATA")/zanzibar-pg/data"
    else
        echo "${TMPDIR:-/tmp}/zanzibar-pg/data"
    fi
}
DATA="${ZANZIBAR_PG_DATA:-$(default_data)}"
LOG="$(dirname "$DATA")/server.log"

DSN="postgresql+psycopg2://postgres@127.0.0.1:${PORT}/${DB}"

pgctl()  { "$BIN/pg_ctl" -D "$DATA" -o "-p $PORT -h 127.0.0.1" "$@"; }
running() { pgctl status >/dev/null 2>&1; }

case "${1:-start}" in

start)
    if [[ ! -f "$DATA/PG_VERSION" ]]; then
        mkdir -p "$(dirname "$DATA")"
        echo "pg_local: initdb -> $DATA"
        # trust auth: loopback-only, throwaway cluster, no secret worth protecting.
        "$BIN/initdb" -D "$DATA" -U postgres --auth=trust --encoding=UTF8 >/dev/null
        # Never listen off-host, whatever the packaged default says.
        echo "listen_addresses = '127.0.0.1'" >> "$DATA/postgresql.conf"
    fi
    if running; then
        echo "pg_local: already running on port $PORT"
    else
        # Detach every standard stream. `pg_ctl start` leaves the postmaster
        # holding whatever stdout it inherited, so on Windows/Git-Bash the
        # calling shell never sees EOF and the command appears to hang long
        # after the server is up and serving.
        pgctl -l "$LOG" -w start >/dev/null 2>&1 </dev/null
        echo "pg_local: started on port $PORT (log: $LOG)"
    fi
    # Idempotent database creation. `psql -tAc` must SUCCEED (rc 0) before its
    # output means anything -- a dead server also prints no '1', and piping
    # straight into `grep -q` would read that as "absent" and mask the outage.
    exists="$("$BIN/psql" -h 127.0.0.1 -p "$PORT" -U postgres -d postgres -tAc \
        "SELECT 1 FROM pg_database WHERE datname='$DB'")" || {
        echo "pg_local: server is not answering on port $PORT (log: $LOG)" >&2; exit 1; }
    [[ "$exists" == 1 ]] || "$BIN/createdb" -h 127.0.0.1 -p "$PORT" -U postgres "$DB"
    echo "ZANZIBAR_PG_DSN=$DSN"
    ;;

env)  echo "export ZANZIBAR_PG_DSN='$DSN'" ;;
dsn)  echo "$DSN" ;;

status)
    if running; then pgctl status; else echo "pg_local: not running"; exit 1; fi
    ;;

stop)
    if running; then pgctl -m fast -w stop >/dev/null; echo "pg_local: stopped"
    else echo "pg_local: not running"; fi
    ;;

destroy)
    running && pgctl -m immediate -w stop >/dev/null || true
    rm -rf "$(dirname "$DATA")"
    echo "pg_local: destroyed $(dirname "$DATA")"
    ;;

*)
    echo "usage: $0 {start|stop|status|destroy|dsn|env}" >&2; exit 2 ;;
esac
