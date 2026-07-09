#!/usr/bin/env bash
# One-command green gate for the formal-verification effort (plan C4 / Phase 6).
# Runs from the repo root or anywhere. Requires elan on PATH (or ~/.elan/bin).
#
#   bash formal/verify.sh
#
# Checks, in order (ALL hard gates as of 2026-07-10 -- the tree reached 0 sorries):
#   1. Lean library builds (lake build)          -- all theorem statements typecheck
#   2. sorry inventory == 0 (HARD)               -- a new sorry fails the gate
#   3. conformance CLI builds (lake build zcli)
#   4. axiom audit (ZanzibarProofs.Audit, HARD)  -- no sorryAx / ofReduceBool / custom
#      axioms may appear; only propext, Classical.choice, Quot.sound
#   5. Python conformance suite passes           -- sem vs oracle vs set engine

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEAN_DIR="$REPO_ROOT/formal/lean"
PY="C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe"
export PATH="$HOME/.elan/bin:$PATH"

echo "=== [1/5] lake build (library) ==="
( cd "$LEAN_DIR" && lake build ) || { echo "FAIL: lake build"; exit 1; }

echo "=== [2/5] sorry inventory (HARD gate: must be 0) ==="
# Count only the `sorry` tactic on its own line (excludes prose/docstring mentions).
SORRIES=$(grep -rhnE "^[[:space:]]*sorry[[:space:]]*$" "$LEAN_DIR/ZanzibarProofs" \
          --include=*.lean | wc -l | tr -d ' ')
echo "  tracked sorries: $SORRIES"
[ "$SORRIES" = "0" ] || { echo "FAIL: sorry count is $SORRIES (gate requires 0)"; exit 1; }

echo "=== [3/5] lake build zcli (conformance CLI) ==="
( cd "$LEAN_DIR" && lake build zcli ) || { echo "FAIL: lake build zcli"; exit 1; }

echo "=== [4/5] axiom audit (ZanzibarProofs.Audit; HARD gate: standard axioms only) ==="
AUDIT_OUT=$( cd "$LEAN_DIR" && rm -f .lake/build/lib/lean/ZanzibarProofs/Audit.olean \
  && lake build ZanzibarProofs.Audit 2>&1 ) || { echo "FAIL: audit build"; exit 1; }
echo "$AUDIT_OUT" | grep -iE "depends on axioms|does not depend on any axioms"
BAD=$(echo "$AUDIT_OUT" | grep -iE "depends on axioms" \
      | grep -vE "\[(propext|Classical\.choice|Quot\.sound)(, (propext|Classical\.choice|Quot\.sound))*\]$" || true)
if [ -n "$BAD" ]; then
  echo "FAIL: non-standard axioms in the audit:"
  echo "$BAD"
  exit 1
fi

echo "=== [5/5] Python conformance (sem vs oracle vs set engine) ==="
( cd "$REPO_ROOT" && "$PY" -m pytest formal/conformance/ -q ) \
  || { echo "FAIL: conformance"; exit 1; }

echo ""
echo "=== verify.sh: all hard gates PASSED (sorries=$SORRIES) ==="
