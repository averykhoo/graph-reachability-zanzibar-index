#!/usr/bin/env bash
# TK144 sabotage of the HEADLINE_AUDITS additions (instrument level): run verify.sh's own
# headline loop, extracted verbatim, over the audit lines a real lean-phase log printed,
# (0) unmodified, (1) with graphModeAnswersR_eq_semR's report removed, (2) with
# semR_fuel_stable's report rewritten to "does not depend on any axioms".
# usage: bash formal/probes/tk144_headline_loop_sabotage_2026_10_17.sh <lean-phase-log>
# Observed 2026-10-17 over the PASSED lean run 20261017-174713 (audits=745), literal:
#   [S0 unmodified] LOOP-PASSED
#   [S1 drop graphModeAnswersR_eq_semR] FAIL: headline theorem 'graphModeAnswersR_eq_semR'
#       produced NO audit report.
#   [S2 semR_fuel_stable axiom-free] FAIL: headline theorem 'semR_fuel_stable' depends on
#       NO axioms:
set -u
LOG="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VS="$ROOT/formal/verify.sh"
# HEADLINE_AUDITS="..." (multi-line string) and the loop body, taken from verify.sh itself.
HL_DEF=$(tr -d '\r' < "$VS" | awk '/^HEADLINE_AUDITS="/{f=1} f{print} f&&/"$/&&!/^HEADLINE_AUDITS="[^"]*$/{exit}')
LOOP=$(tr -d '\r' < "$VS" | awk '/^  for _t in \$HEADLINE_AUDITS; do/{f=1} f{print} f&&/^  done$/{exit}')
[ -n "$HL_DEF" ] && [ -n "$LOOP" ] || { echo "INSTRUMENT: extraction failed"; exit 9; }
REAL=$(tr -d '\r' < "$LOG" | grep -iE "depends on axioms|does not depend on any axioms")
[ -n "$REAL" ] || { echo "INSTRUMENT: no audit lines in $LOG"; exit 9; }
run() {   # $1 = label, AUDIT_OUT in env
  out=$( eval "$HL_DEF"; eval "$LOOP"; echo "LOOP-PASSED" ) 2>&1
  echo "[$1] $(printf '%s\n' "$out" | head -3 | tr '\n' ' ')"
}
AUDIT_OUT="$REAL" run "S0 unmodified"
AUDIT_OUT=$(printf '%s\n' "$REAL" | grep -v "graphModeAnswersR_eq_semR'") run "S1 drop graphModeAnswersR_eq_semR"
AUDIT_OUT=$(printf '%s\n' "$REAL" | sed "s/'Zanzibar.semR_fuel_stable' depends on axioms.*/'Zanzibar.semR_fuel_stable' does not depend on any axioms/") run "S2 semR_fuel_stable axiom-free"
