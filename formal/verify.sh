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
#   5. Python conformance suite passes           -- sem vs oracle vs set engine,
#      plus (Phase 6) the Lean OPERATIONAL graph model (zcli mode "graph",
#      GraphIndex/Exec.lean) vs the real Python graph index over the
#      W4Fragment corpora

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEAN_DIR="$REPO_ROOT/formal/lean"
PY="C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe"
export PATH="$HOME/.elan/bin:$PATH"

BUILD_LOG="$(mktemp)"
trap 'rm -f "$BUILD_LOG"' EXIT

echo "=== [1/5] lake build (library) ==="
( cd "$LEAN_DIR" && lake build 2>&1 | tee "$BUILD_LOG" ) || { echo "FAIL: lake build"; exit 1; }

echo "=== [2/5] sorry inventory (HARD gate: must be 0) ==="
# Token-level scan: count every `sorry` TOKEN in the .lean sources OUTSIDE
# comments (`--` line, nested `/- -/` block, `/-- -/` docstring) and string
# literals — an inline `:= sorry` counts, a prose mention does not.
SORRIES=$("$PY" - "$LEAN_DIR/ZanzibarProofs" <<'PYEOF'
import re, sys, pathlib
root = pathlib.Path(sys.argv[1])
count = 0
for p in sorted(root.rglob("*.lean")):
    src = p.read_text(encoding="utf-8")
    n, i, depth, out = len(src), 0, 0, []
    while i < n:
        if depth > 0:                      # inside (possibly nested) block comment
            if src.startswith("/-", i):
                depth += 1; i += 2
            elif src.startswith("-/", i):
                depth -= 1; i += 2
                if depth == 0:
                    out.append(" ")        # token barrier where the comment was
            else:
                i += 1
            continue
        if src.startswith("/-", i):        # block comment / docstring opens
            depth = 1; i += 2; continue
        if src.startswith("--", i):        # line comment
            j = src.find("\n", i)
            i = n if j < 0 else j          # keep the newline as the barrier
            continue
        if src.startswith("'\"'", i):      # the char literal '"' — not a string
            out.append(" "); i += 3; continue
        if src[i] == '"':                  # string literal: data, not a proof hole
            i += 1
            while i < n:
                if src[i] == "\\": i += 2; continue
                if src[i] == '"': i += 1; break
                i += 1
            out.append(" ")
            continue
        out.append(src[i]); i += 1
    for m in re.finditer(r"\bsorry\b", "".join(out)):
        count += 1
        print(f"  sorry token: {p.relative_to(root)}", file=sys.stderr)
print(count)
PYEOF
) || { echo "FAIL: sorry scanner errored"; exit 1; }
# Belt and suspenders: the compiler's own verdict (Lake replays cached logs).
WARNED=$(grep -c "declaration uses 'sorry'" "$BUILD_LOG" || true)
echo "  tracked sorries: $SORRIES (token scan), $WARNED (build-log warnings)"
[ "$SORRIES" = "0" ] || { echo "FAIL: sorry token count is $SORRIES (gate requires 0)"; exit 1; }
[ "$WARNED" = "0" ] || { echo "FAIL: lake build reported $WARNED 'declaration uses sorry' warning(s)"; exit 1; }

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

echo "=== [5/5] Python conformance (sem vs oracle vs set engine vs graph model) ==="
( cd "$REPO_ROOT" && "$PY" -m pytest formal/conformance/ -q ) \
  || { echo "FAIL: conformance"; exit 1; }

echo ""
echo "=== verify.sh: all hard gates PASSED (sorries=$SORRIES) ==="
