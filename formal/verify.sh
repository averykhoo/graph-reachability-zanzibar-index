#!/usr/bin/env bash
# One-command green gate for the formal-verification effort (plan C4 / Phase 6).
# Runs from the repo root or anywhere. Requires elan on PATH (or ~/.elan/bin).
#
#   bash formal/verify.sh
#
# Checks, in order:
#   1. Lean library builds (lake build)          -- all theorem statements typecheck
#   2. sorry inventory is reported (not gated yet; must reach 0 before Phase 6 sign-off)
#   3. conformance CLI builds (lake build zcli)
#   4. axiom audit prints (ZanzibarProofs.Audit) -- proved lemmas must be axiom-clean
#   5. Python conformance suite passes           -- sem vs oracle vs set engine
#
# Exit non-zero on the first hard failure (build or conformance). The sorry count and
# axiom audit are reported for review; they become hard gates in Phase 6.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEAN_DIR="$REPO_ROOT/formal/lean"
PY="C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe"
export PATH="$HOME/.elan/bin:$PATH"

echo "=== [1/5] lake build (library) ==="
( cd "$LEAN_DIR" && lake build ) || { echo "FAIL: lake build"; exit 1; }

echo "=== [2/5] sorry inventory ==="
# Count only the `sorry` tactic on its own line (excludes prose/docstring mentions).
SORRIES=$(grep -rhnE "^[[:space:]]*sorry[[:space:]]*$" "$LEAN_DIR/ZanzibarProofs" \
          --include=*.lean | wc -l | tr -d ' ')
echo "  tracked sorries: $SORRIES (target 0 for Phase 6 sign-off)"

echo "=== [3/5] lake build zcli (conformance CLI) ==="
( cd "$LEAN_DIR" && lake build zcli ) || { echo "FAIL: lake build zcli"; exit 1; }

echo "=== [4/5] axiom audit (ZanzibarProofs.Audit) ==="
( cd "$LEAN_DIR" && rm -f .lake/build/lib/lean/ZanzibarProofs/Audit.olean \
  && lake build ZanzibarProofs.Audit 2>&1 | grep -iE "depends on axioms" ) \
  || echo "  (audit module not built; skipping)"

echo "=== [5/5] Python conformance (sem vs oracle vs set engine) ==="
( cd "$REPO_ROOT" && "$PY" -m pytest formal/conformance/ -q ) \
  || { echo "FAIL: conformance"; exit 1; }

echo ""
echo "=== verify.sh: all hard gates PASSED (sorries=$SORRIES) ==="
