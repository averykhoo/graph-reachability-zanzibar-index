#!/usr/bin/env bash
# One-command green gate for the formal-verification effort (plan C4 / Phase 6).
# Runs from the repo root or anywhere. Requires elan on PATH (or ~/.elan/bin).
#
#   bash formal/verify.sh              # all gates, one shot (uncapped / CI)
#   bash formal/verify.sh lean         # steps 1-4 only  (Lean build + audit)
#   bash formal/verify.sh conf-heavy   # step 5, the slow conformance file only
#   bash formal/verify.sh conf-rest    # step 5, every other conformance file
#
# PHASED MODE (the split gate). The one-shot run is ~13-16 min and does NOT fit a
# 10-min execution cap (e.g. an agent harness). The three phase args partition the
# SAME work — same anti-vacuous guards, no coverage gaps — into cap-fitting pieces
# an unattended runner can execute in sequence:
#     lean  →  conf-heavy  →  conf-rest       (all three must print PASSED)
# Warm timings on the dev box: lean ~3 min, conf-heavy ~6.5 min, conf-rest ~4.5 min.
# `conf-rest` is defined as "the conformance dir MINUS the heavy file" via --ignore,
# so any newly-added conformance file automatically lands in conf-rest — the union
# is always the whole dir, nothing can be silently dropped. Phase order matters:
# `lean` builds the zcli binary the conf phases preflight on, so run it first.
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

PHASE="${1:-all}"
case "$PHASE" in
  all|lean|conf-heavy|conf-rest) ;;
  *) echo "usage: verify.sh [all|lean|conf-heavy|conf-rest]"; exit 2 ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEAN_DIR="$REPO_ROOT/formal/lean"
# Interpreter is overridable for portability (ZANZIBAR_PY); default = this machine's
# conda env, so this box keeps working with no env set.
PY="${ZANZIBAR_PY:-C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe}"
export PATH="$HOME/.elan/bin:$PATH"

# The single heavy conformance file, split into its own phase. conf-rest is the
# whole dir minus exactly this file, so the two conf phases tile the dir with no gap.
HEAVY_CONF="formal/conformance/test_conformance_remove.py"

BUILD_LOG="$(mktemp)"
trap 'rm -f "$BUILD_LOG"' EXIT

# Fail EARLY (before any long build) if the resolved interpreter cannot run.
preflight_py() {
  "$PY" -c "import sys" >/dev/null 2>&1 \
    || { echo "FAIL: Python interpreter not runnable: $PY"; \
         echo "      override with ZANZIBAR_PY=/path/to/env/python.exe (conda env 'graph-reachability-zanzibar-index')"; \
         exit 1; }
}

# ---------------------------------------------------------------------------- #
# Lean gate: steps 1-4 (build, sorry, zcli, axiom audit)
# ---------------------------------------------------------------------------- #
run_lean() {
  echo "=== [1/5] lake build (library) ==="
  ( cd "$LEAN_DIR" && lake build 2>&1 | tee "$BUILD_LOG" ) || { echo "FAIL: lake build"; exit 1; }

  echo "=== [2/5] sorry inventory (HARD gate: must be 0) ==="
  # Token-level scan (extracted to formal/conformance/sorry_scan.py so its tricky
  # comment/string/char-literal handling is unit-tested — test_sorry_scan.py): count
  # every `sorry`/`admit` TOKEN in the .lean sources OUTSIDE comments (`--` line,
  # nested `/- -/` block, `/-- -/` docstring) and string literals — an inline
  # `:= sorry` counts, a prose mention does not. The scanner prints the count on
  # stdout, offending files on stderr, and exits nonzero when it finds any.
  SORRY_SCAN="$REPO_ROOT/formal/conformance/sorry_scan.py"
  SORRIES=$("$PY" "$SORRY_SCAN" "$LEAN_DIR/ZanzibarProofs")
  # A non-numeric result means the scanner itself errored (e.g. a traceback), which is
  # distinct from "found sorries" (a numeric, possibly-nonzero count) — the scanner
  # exits nonzero in BOTH cases, so distinguish them by the shape of stdout here.
  case "$SORRIES" in
    ''|*[!0-9]*) echo "FAIL: sorry scanner errored"; exit 1;;
  esac
  # Belt and suspenders: the compiler's own verdict (Lake replays cached logs).
  WARNED=$(grep -c "declaration uses 'sorry'" "$BUILD_LOG" || true)
  echo "  tracked sorries: $SORRIES (token scan), $WARNED (build-log warnings)"
  [ "$SORRIES" = "0" ] || { echo "FAIL: sorry token count is $SORRIES (gate requires 0)"; exit 1; }
  [ "$WARNED" = "0" ] || { echo "FAIL: lake build reported $WARNED 'declaration uses sorry' warning(s)"; exit 1; }

  echo "=== [3/5] lake build zcli (conformance CLI) ==="
  ( cd "$LEAN_DIR" && lake build zcli ) || { echo "FAIL: lake build zcli"; exit 1; }

  echo "=== [4/5] axiom audit (ZanzibarProofs.Audit; HARD gate: standard axioms only) ==="
  AUDIT_LEAN="$LEAN_DIR/ZanzibarProofs/Audit.lean"
  AUDIT_OLEAN="$LEAN_DIR/.lake/build/lib/lean/ZanzibarProofs/Audit.olean"
  # Self-heal a prior interrupted run: step 4 does `rm -f Audit.olean` then rebuilds,
  # so a kill in between leaves the olean missing (and a plain `lake build` does NOT
  # rebuild the Audit target). Rebuild it here if absent, THEN assert it is at the
  # expected path. This preserves the layout-drift guard: if the build path has
  # drifted, `lake build ZanzibarProofs.Audit` writes to the NEW path and this
  # expected-path check still fails (and the OBSERVED_AUDITS>0 / ==EXPECTED guards
  # below independently catch a vacuous cache-hit audit).
  [ -f "$AUDIT_OLEAN" ] || ( cd "$LEAN_DIR" && lake build ZanzibarProofs.Audit >/dev/null 2>&1 )
  [ -f "$AUDIT_OLEAN" ] \
    || { echo "FAIL: audit olean not at expected path: $AUDIT_OLEAN"; \
         echo "      (layout drift, or the Audit target does not build -- the rm would be a"; \
         echo "       no-op and the rebuild a cache hit auditing nothing)"; \
         exit 1; }
  # Expected number of audit reports = number of real `#print axioms` COMMANDS in
  # Audit.lean: lines that START with `#print axioms ` at column 0. This deliberately
  # excludes the single prose backtick-mention inside the file docstring (indented,
  # not column 0) and would exclude any `-- #print axioms` comment (there are none today).
  EXPECTED_AUDITS=$(grep -cE '^#print axioms ' "$AUDIT_LEAN")
  AUDIT_OUT=$( cd "$LEAN_DIR" && rm -f "$AUDIT_OLEAN" \
    && lake build ZanzibarProofs.Audit 2>&1 ) || { echo "FAIL: audit build"; exit 1; }
  echo "$AUDIT_OUT" | grep -iE "depends on axioms|does not depend on any axioms"
  # Positive-audit assertion: each `#print axioms` emits exactly one report line
  # (`... depends on axioms: [...]` OR `... does not depend on any axioms`). Count the
  # reports actually observed and require it POSITIVE and EQUAL to the command count --
  # a vacuous rebuild (cache hit / olean drift) shows zero reports and now fails.
  OBSERVED_AUDITS=$(echo "$AUDIT_OUT" | grep -icE "depends on axioms|does not depend on any axioms")
  echo "  audit reports: $OBSERVED_AUDITS observed, $EXPECTED_AUDITS expected (#print axioms commands)"
  [ "$OBSERVED_AUDITS" -gt 0 ] \
    || { echo "FAIL: axiom audit produced ZERO report lines (vacuous -- rebuild was likely a cache hit)"; exit 1; }
  [ "$OBSERVED_AUDITS" = "$EXPECTED_AUDITS" ] \
    || { echo "FAIL: audit reported $OBSERVED_AUDITS lines but Audit.lean has $EXPECTED_AUDITS '#print axioms' commands"; exit 1; }
  BAD=$(echo "$AUDIT_OUT" | grep -iE "depends on axioms" \
        | grep -vE "\[(propext|Classical\.choice|Quot\.sound)(, (propext|Classical\.choice|Quot\.sound))*\]$" || true)
  if [ -n "$BAD" ]; then
    echo "FAIL: non-standard axioms in the audit:"
    echo "$BAD"
    exit 1
  fi
  echo "=== lean phase (steps 1-4) PASSED (sorries=$SORRIES) ==="
}

# ---------------------------------------------------------------------------- #
# Conformance gate: step 5, over the pytest target given in "$@"
# ---------------------------------------------------------------------------- #
run_conf() {
  echo "=== [5/5] Python conformance (sem vs oracle vs set engine vs graph model) ==="
  echo "  target: $*"
  # Preflight: the zcli binary MUST exist. Without it every Lean-comparison test calls
  # pytest.skip (runner.ZcliUnavailable), so the "hard gate" can pass having compared
  # NOTHING. Assert the binary is present before running pytest. (Built by the `lean`
  # phase / step 3 -- run that first.)
  ZCLI_BIN=""
  for cand in "$LEAN_DIR/.lake/build/bin/zcli" "$LEAN_DIR/.lake/build/bin/zcli.exe"; do
    [ -f "$cand" ] && ZCLI_BIN="$cand"
  done
  [ -n "$ZCLI_BIN" ] \
    || { echo "FAIL: zcli binary not found under $LEAN_DIR/.lake/build/bin (expected zcli or zcli.exe)"; \
         echo "      -- conformance would skip every Lean comparison and pass vacuously"; \
         echo "      -- run 'bash formal/verify.sh lean' first (it builds zcli)"; \
         exit 1; }
  echo "  zcli binary: $ZCLI_BIN"
  # Capture pytest output, echo it through, then gate on the summary line.
  CONF_OUT=$( cd "$REPO_ROOT" && "$PY" -m pytest "$@" -q 2>&1 )
  CONF_RC=$?
  echo "$CONF_OUT"
  [ "$CONF_RC" = "0" ] || { echo "FAIL: conformance (pytest rc=$CONF_RC)"; exit 1; }
  # Parse the final pytest summary line (last non-blank line, e.g.
  # "98 passed in 111.00s" or "2 passed, 3 skipped in 1.2s"). FAIL on ANY skipped test
  # (a missing zcli / xfail path would mask an uncompared corpus) and FAIL if zero passed.
  CONF_SUMMARY=$(printf '%s\n' "$CONF_OUT" | grep -vE '^[[:space:]]*$' | tail -1)
  CONF_SKIPPED=$(printf '%s\n' "$CONF_SUMMARY" | grep -oE '[0-9]+ skipped' | grep -oE '^[0-9]+' || true)
  CONF_PASSED=$(printf '%s\n' "$CONF_SUMMARY" | grep -oE '[0-9]+ passed' | grep -oE '^[0-9]+' || true)
  CONF_SKIPPED=${CONF_SKIPPED:-0}
  CONF_PASSED=${CONF_PASSED:-0}
  echo "  conformance summary: $CONF_SUMMARY"
  [ "$CONF_SKIPPED" = "0" ] \
    || { echo "FAIL: conformance reported $CONF_SKIPPED skipped test(s) -- the gate must compare, not skip"; exit 1; }
  [ "$CONF_PASSED" -gt 0 ] \
    || { echo "FAIL: conformance passed ZERO tests (nothing was actually compared)"; exit 1; }
  echo "=== conformance phase PASSED ($CONF_SUMMARY) ==="
}

preflight_py
case "$PHASE" in
  lean)       run_lean ;;
  conf-heavy) run_conf "$HEAVY_CONF" ;;
  conf-rest)  run_conf formal/conformance/ --ignore="$HEAVY_CONF" ;;
  all)        run_lean; run_conf formal/conformance/ ;;
esac

echo ""
echo "=== verify.sh: phase '$PHASE' PASSED ==="
