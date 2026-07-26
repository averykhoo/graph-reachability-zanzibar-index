#!/usr/bin/env bash
# One-command green gate for the formal-verification effort (plan C4 / Phase 6).
# Runs from the repo root or anywhere. Requires elan on PATH (or ~/.elan/bin).
#
#   bash formal/verify.sh                 # all gates, one shot (uncapped / CI)
#   bash formal/verify.sh lean            # steps 1-4 only  (Lean build + audit)
#   bash formal/verify.sh conf-tile:1/5   # step 5, tile 1 of 5 of the conformance dir
#   bash formal/verify.sh conf-heavy      # step 5, the one heavy file      (legacy split)
#   bash formal/verify.sh conf-rest       # step 5, the dir minus that file (legacy split)
#
# PHASED MODE (the split gate). The one-shot run is ~18-20 min and does NOT fit a
# 10-min execution cap (e.g. an agent harness). The phase args partition the SAME
# work -- same anti-vacuous guards, no coverage gaps -- into cap-fitting pieces an
# unattended runner can execute in sequence. RECOMMENDED SEQUENCE (2026-07-26):
#
#     lean → conf-tile:1/5 → conf-tile:2/5 → conf-tile:3/5 → conf-tile:4/5 → conf-tile:5/5
#
# Warm timings on the dev box (2026-07-26): lean ~0.5-3 min, each conf tile 170-235 s
# (<= 40% of the 600 s cap). Phase order matters only in that `lean` builds the zcli
# binary the conf phases preflight on -- run it first.
#
# The legacy 3-phase sequence (`lean` → `conf-heavy` → `conf-rest`) still works and is
# still gap-free, but `conf-rest` measured 579 s against the 600 s cap on 2026-07-26
# (`formal/history/` filed "consider splitting the phase" on 2026-07-19g) -- hence the
# tiles. Use the tiles; `conf-heavy`/`conf-rest` are kept for older runbooks and for a
# quick single-file rerun.
#
# COVERAGE IS STRUCTURAL, NOT A HARD-CODED FILE LIST:
#   * `conf-tile:I/K` collects `formal/conformance/` fresh, asserts the collected total
#     is at least $MIN_CONF_ALL, then runs the node ids whose 0-based collection index
#     is congruent to I-1 (mod K). Every collected node lands in EXACTLY ONE tile, so
#     the K tiles partition the directory by construction -- a newly added test file,
#     corpus or parametrization is automatically covered by exactly one tile, and the
#     per-tile size is checked against the partition arithmetic.
#   * `conf-rest` remains "the dir MINUS $HEAVY_CONF" via --ignore, so the legacy
#     `conf-heavy` + `conf-rest` pair also still tiles the whole dir.
#
# Checks, in order (ALL hard gates as of 2026-07-10 -- the tree reached 0 sorries):
#   1. Lean library builds (lake build)          -- all theorem statements typecheck
#   2. soundness-hole inventory == 0 (HARD)      -- sorry / admit / sorryAx /
#      native_decide / custom `axiom` declarations, over EVERY project .lean file
#   3. conformance CLI builds (lake build zcli)  -- output tee'd into the same
#      'declaration uses sorry' grep as step 1
#   4. axiom audit (ZanzibarProofs.Audit, HARD)  -- no sorryAx / ofReduceBool / custom
#      axioms may appear; only propext, Classical.choice, Quot.sound; PLUS a
#      hard-coded floor on the number of audited theorems
#   5. Python conformance suite passes           -- sem vs oracle vs set engine,
#      plus (Phase 6) the Lean OPERATIONAL graph model (zcli mode "graph",
#      GraphIndex/Exec.lean) vs the real Python graph index over the
#      W4Fragment corpora; with count floors and zero tolerance for
#      skipped/xfailed/xpassed/deselected
#
# GATE SELF-DEFENCE (zero-trust review 2026-07-26, ZT-P2-1..6). Every hard-coded
# number below is a FLOOR asserted with -ge, so ADDING theorems/tests never fails the
# gate; only REMOVING assurance does. Lowering any of them must be a deliberate,
# reviewed edit to this file -- that is the whole point: before this, deleting audited
# theorems or conformance corpora kept the gate green.

set -uo pipefail

USAGE="usage: verify.sh [all|lean|conf-tile:I/K|conf-heavy|conf-rest]
       conf-tile:I/K  1 <= I <= K; the K tiles partition formal/conformance/
                      (recommended: conf-tile:1/5 .. conf-tile:5/5; K is free --
                       raise it when a tile approaches the ~600 s command cap)"

PHASE="${1:-all}"
TILE_I=""; TILE_K=""
case "$PHASE" in
  all|lean|conf-heavy|conf-rest) ;;
  conf-tile:*/*)
    _spec="${PHASE#conf-tile:}"
    TILE_I="${_spec%%/*}"; TILE_K="${_spec##*/}"
    case "$TILE_I" in ''|*[!0-9]*) echo "$USAGE"; exit 2;; esac
    case "$TILE_K" in ''|*[!0-9]*) echo "$USAGE"; exit 2;; esac
    { [ "$TILE_K" -ge 1 ] && [ "$TILE_I" -ge 1 ] && [ "$TILE_I" -le "$TILE_K" ]; } \
      || { echo "$USAGE"; exit 2; }
    ;;
  *) echo "$USAGE"; exit 2 ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEAN_DIR="$REPO_ROOT/formal/lean"
CONF_DIR="formal/conformance/"          # relative to REPO_ROOT (pytest is run there)
export PATH="$HOME/.elan/bin:$PATH"

# ---------------------------------------------------------------------------- #
# Interpreter resolution (ZT-P2-6). This used to hard-code one dev box's conda
# path, so `bash formal/verify.sh` as documented in CLAUDE.md could not run on any
# other machine without ZANZIBAR_PY. ZANZIBAR_PY still wins outright when set;
# otherwise try an ordered list of plausible env locations (including $HOME- and
# $CONDA_PREFIX-derived ones) and finally whatever `python` is on PATH -- accepting
# only a candidate that can actually import the project's deps. The fail-loud
# preflight below still runs on whatever is resolved.
# ---------------------------------------------------------------------------- #
ENV_NAME="graph-reachability-zanzibar-index"

py_usable() { [ -n "${1:-}" ] && "$1" -c "import pytest, sqlmodel" >/dev/null 2>&1; }

resolve_py() {
  local c
  for c in \
    "$HOME/anaconda3/envs/$ENV_NAME/python.exe" \
    "$HOME/miniconda3/envs/$ENV_NAME/python.exe" \
    "$HOME/mambaforge/envs/$ENV_NAME/python.exe" \
    "$HOME/anaconda3/envs/$ENV_NAME/bin/python" \
    "$HOME/miniconda3/envs/$ENV_NAME/bin/python" \
    "C:/Users/user/anaconda3/envs/$ENV_NAME/python.exe" \
    "C:/Users/avery/anaconda3/envs/$ENV_NAME/python.exe" \
    "/c/ProgramData/anaconda3/envs/$ENV_NAME/python.exe" \
    "${CONDA_PREFIX:-}/python.exe" \
    "${CONDA_PREFIX:-}/bin/python"
  do
    py_usable "$c" && { printf '%s' "$c"; return 0; }
  done
  for c in python python3; do
    if command -v "$c" >/dev/null 2>&1; then
      local p; p="$(command -v "$c")"
      py_usable "$p" && { printf '%s' "$p"; return 0; }
    fi
  done
  # Nothing usable found: return the canonical path so the preflight can name it.
  printf '%s' "$HOME/anaconda3/envs/$ENV_NAME/python.exe"
  return 1
}

if [ -n "${ZANZIBAR_PY:-}" ]; then
  PY="$ZANZIBAR_PY"
else
  PY="$(resolve_py)"
fi

# ---------------------------------------------------------------------------- #
# The hard-coded assurance floors.
# ---------------------------------------------------------------------------- #
# Minimum tests the conformance directory must COLLECT. Measured 2026-07-26 with
# `pytest formal/conformance/ -q --collect-only`: 356. Every `conf-tile:I/K` phase
# asserts this against the live collection BEFORE tiling, so the global coverage
# floor is checked by each tile independently -- and each tile's own pass floor is
# then its exact tile size (all selected tests must pass).
# ADDING tests never trips this. LOWERING it must be a deliberate, reviewed edit
# here -- without a floor, shrinking GRAPH_FRAGMENT to a single corpus or deleting
# test_conformance_graph.py outright kept the gate green (ZT-P2-2).
MIN_CONF_ALL=391

# Legacy file-carve split. Measured 2026-07-26 (per-file wall clock):
#   test_conformance_remove.py   80 tests, ~170 s   -> conf-heavy
#   test_conformance_enum.py      6 tests, ~380-475 s (the real hog inside conf-rest;
#     the 2026-07-19g note blamed test_conformance_remove_graph.py, which is ~27 s)
HEAVY_CONF="formal/conformance/test_conformance_remove.py"
MIN_CONF_HEAVY=88
MIN_CONF_REST=303

# Machine-enforced tiling identity for the legacy split: the two floors must add up
# to the whole-directory floor, so nobody can bump one and quietly leave a hole in
# the other. This is the arithmetic shadow of the --ignore construction.
if [ "$(( MIN_CONF_HEAVY + MIN_CONF_REST ))" != "$MIN_CONF_ALL" ]; then
  echo "FAIL: verify.sh conformance floors are inconsistent --"
  echo "      need MIN_CONF_HEAVY + MIN_CONF_REST == MIN_CONF_ALL"
  echo "      ($MIN_CONF_HEAVY + $MIN_CONF_REST vs $MIN_CONF_ALL)"
  echo "      (conf-heavy and conf-rest tile the conformance dir; their floors must tile too)"
  exit 1
fi

# Number of audited theorems (`#print axioms` reports) that MUST be observed
# (ZT-P2-1). The old gate only compared OBSERVED to a count grepped out of the very
# file being audited, so deleting `#print axioms graph_correct` from Audit.lean --
# or reducing Audit.lean to one trivial line -- kept the gate green. Measured
# 2026-07-26: exactly 455 `#print axioms` commands in Audit.lean. Asserted with -ge
# so ANOTHER agent adding audited theorems does not fail the gate; LOWERING this
# number must be a deliberate, reviewed edit to this file (and should be justified
# in formal/history/, e.g. if a known-vacuous audit line is retired).
EXPECTED_MIN_AUDITS=457

# Minimum number of project .lean files the soundness scan must cover (ZT-P2-4).
# Measured 2026-07-26: 65 files under formal/lean excluding .lake/** (it was 64 when
# the scan pointed at formal/lean/ZanzibarProofs and so missed the library root
# ZanzibarProofs.lean). A little slack for renames/merges; a collapse to a handful of
# files means the scan lost the tree and its clean 0 is not evidence.
MIN_SCANNED_LEAN_FILES=60

BUILD_LOG="$(mktemp)"
trap 'rm -f "$BUILD_LOG"' EXIT

# Fail EARLY (before any long build) if the resolved interpreter cannot run, or if
# the environment would silently under-test.
preflight_py() {
  "$PY" -c "import sys" >/dev/null 2>&1 \
    || { echo "FAIL: Python interpreter not runnable: $PY"; \
         echo "      override with ZANZIBAR_PY=/path/to/env/python.exe (conda env '$ENV_NAME')"; \
         exit 1; }
  "$PY" -c "import pytest, sqlmodel, hypothesis" >/dev/null 2>&1 \
    || { echo "FAIL: resolved interpreter is missing declared deps: $PY"; \
         "$PY" -c "import pytest, sqlmodel, hypothesis" 2>&1 | tail -2; \
         echo "      pip install pytest sqlmodel hypothesis pyroaring   (conda env '$ENV_NAME')"; \
         echo "      or point ZANZIBAR_PY at the right interpreter"; \
         exit 1; }
  echo "  interpreter: $PY"
  # ZT-P2-6: a missing pyroaring makes setengine/setops.py fall back to PySets
  # SILENTLY (RoaringSets = None), so every "both SetOps" leg of the matrix and of
  # the conformance suite quietly halves. Nothing detected that. Now it FAILS.
  ( cd "$REPO_ROOT" && "$PY" -c "
import sys
from setengine.setops import RoaringSets, ALL_SETOPS, DEFAULT_SETOPS
if RoaringSets is None or len(ALL_SETOPS) < 2 or DEFAULT_SETOPS.name != 'roaring':
    sys.stderr.write('  set-engine SetOps available: %r (default %r)\n'
                     % ([o.name for o in ALL_SETOPS], DEFAULT_SETOPS.name))
    sys.exit(1)
" ) \
    || { echo "FAIL: pyroaring is missing -- the set engine silently fell back to PySets"; \
         echo "      (setengine/setops.py: RoaringSets is None => DEFAULT_SETOPS = PySets)."; \
         echo "      Every 'both SetOps' leg would then run ONE backend and the gate"; \
         echo "      would pass having tested half of what it claims."; \
         echo "      Fix: pip install pyroaring   (into conda env '$ENV_NAME')"; \
         exit 1; }
  echo "  set engine: RoaringSets present (both SetOps legs will really run)"
}

# ---------------------------------------------------------------------------- #
# Lean gate: steps 1-4 (build, soundness-hole scan, zcli, axiom audit)
# ---------------------------------------------------------------------------- #
run_lean() {
  echo "=== [1/5] lake build (library) ==="
  ( cd "$LEAN_DIR" && lake build 2>&1 | tee "$BUILD_LOG" ) || { echo "FAIL: lake build"; exit 1; }

  echo "=== [2/5] soundness-hole inventory (HARD gate: must be 0) ==="
  # Token-level scan (formal/conformance/sorry_scan.py, unit-tested by
  # test_sorry_scan.py): count every `sorry` / `admit` / `sorryAx` / `native_decide`
  # TOKEN and every custom `axiom` DECLARATION in the .lean sources OUTSIDE comments
  # (`--` line, nested `/- -/` block, `/-- -/` docstring) and string literals -- an
  # inline `:= sorry` counts, a prose mention does not. An unterminated string literal
  # (tokenizer desync -> the rest of that file invisible) is itself a violation.
  # The scanner prints the count on stdout, findings + a coverage summary on stderr,
  # and exits nonzero on any violation OR a coverage shortfall.
  #
  # ZT-P2-4: the root is $LEAN_DIR, NOT $LEAN_DIR/ZanzibarProofs -- the latter missed
  # the sibling library root ZanzibarProofs.lean entirely. The scanner skips every
  # dot-directory, which is what keeps the ~9.3k vendored .lean files under
  # formal/lean/.lake/** (mathlib/aesop/batteries) out of the scan.
  SORRY_SCAN="$REPO_ROOT/formal/conformance/sorry_scan.py"
  SORRIES=$("$PY" "$SORRY_SCAN" --min-files "$MIN_SCANNED_LEAN_FILES" "$LEAN_DIR")
  SCAN_RC=$?
  # A non-numeric result means the scanner itself errored (e.g. a traceback), which is
  # distinct from "found holes" (a numeric, possibly-nonzero count) -- the scanner
  # exits nonzero in BOTH cases, so distinguish them by the shape of stdout here.
  case "$SORRIES" in
    ''|*[!0-9]*) echo "FAIL: soundness-hole scanner errored"; exit 1;;
  esac
  # Belt and suspenders: the compiler's own verdict (Lake replays cached logs).
  WARNED=$(grep -c "declaration uses 'sorry'" "$BUILD_LOG" || true)
  echo "  tracked holes: $SORRIES (token scan), $WARNED (build-log warnings)"
  [ "$SORRIES" = "0" ] || { echo "FAIL: soundness-hole count is $SORRIES (gate requires 0)"; exit 1; }
  [ "$WARNED" = "0" ] || { echo "FAIL: lake build reported $WARNED 'declaration uses sorry' warning(s)"; exit 1; }
  # The scanner's own exit status also covers the file-coverage floor (a clean 0 from a
  # scan that stopped finding files is not evidence) and any internal error.
  [ "$SCAN_RC" = "0" ] \
    || { echo "FAIL: soundness-hole scanner exited $SCAN_RC with count=$SORRIES"; \
         echo "      -- see its stderr above (coverage floor short, or scanner error)"; \
         exit 1; }

  echo "=== [3/5] lake build zcli (conformance CLI) ==="
  # ZT-P2-4: Cli.lean is NOT reachable from the default lake target, so step 1 never
  # builds it and its warnings never reached $BUILD_LOG -- and this build's output was
  # not captured at all. A `declaration uses 'sorry'` in the binary that IS the
  # conformance ground truth therefore reached no check. Tee it into the same log and
  # re-run the grep over the combined log.
  ( cd "$LEAN_DIR" && lake build zcli 2>&1 | tee -a "$BUILD_LOG" ) || { echo "FAIL: lake build zcli"; exit 1; }
  WARNED_ZCLI=$(grep -c "declaration uses 'sorry'" "$BUILD_LOG" || true)
  echo "  build-log 'declaration uses sorry' warnings (library + zcli): $WARNED_ZCLI"
  [ "$WARNED_ZCLI" = "0" ] \
    || { echo "FAIL: the library+zcli build log reports $WARNED_ZCLI 'declaration uses sorry' warning(s)"; \
         grep -n "declaration uses 'sorry'" "$BUILD_LOG" | head -20; \
         exit 1; }

  echo "=== [4/5] axiom audit (ZanzibarProofs.Audit; HARD gate: standard axioms only) ==="
  AUDIT_LEAN="$LEAN_DIR/ZanzibarProofs/Audit.lean"
  AUDIT_OLEAN="$LEAN_DIR/.lake/build/lib/lean/ZanzibarProofs/Audit.olean"
  # Self-heal a prior interrupted run: step 4 does `rm -f Audit.olean` then rebuilds,
  # so a kill in between leaves the olean missing (and a plain `lake build` does NOT
  # rebuild the Audit target). Rebuild it here if absent, THEN assert it is at the
  # expected path. This preserves the layout-drift guard: if the build path has
  # drifted, `lake build ZanzibarProofs.Audit` writes to the NEW path and this
  # expected-path check still fails (and the OBSERVED_AUDITS floor / ==EXPECTED guards
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
  # reports actually observed and require it (a) EQUAL to the command count -- a vacuous
  # rebuild (cache hit / olean drift) shows zero reports and fails -- and (b) at least
  # the hard-coded EXPECTED_MIN_AUDITS floor, so DELETING audited theorems from
  # Audit.lean now fails instead of silently lowering "expected" along with it (ZT-P2-1).
  OBSERVED_AUDITS=$(echo "$AUDIT_OUT" | grep -icE "depends on axioms|does not depend on any axioms")
  echo "  audit reports: $OBSERVED_AUDITS observed, $EXPECTED_AUDITS expected (#print axioms commands), floor $EXPECTED_MIN_AUDITS"
  [ "$OBSERVED_AUDITS" -gt 0 ] \
    || { echo "FAIL: axiom audit produced ZERO report lines (vacuous -- rebuild was likely a cache hit)"; exit 1; }
  [ "$OBSERVED_AUDITS" = "$EXPECTED_AUDITS" ] \
    || { echo "FAIL: audit reported $OBSERVED_AUDITS lines but Audit.lean has $EXPECTED_AUDITS '#print axioms' commands"; exit 1; }
  [ "$OBSERVED_AUDITS" -ge "$EXPECTED_MIN_AUDITS" ] \
    || { echo "FAIL: axiom audit covered only $OBSERVED_AUDITS theorem(s); the gate floor is $EXPECTED_MIN_AUDITS."; \
         echo "      Audited coverage SHRANK -- a '#print axioms' line was removed from Audit.lean."; \
         echo "      If that is intended (e.g. retiring a known-vacuous audit line), lower"; \
         echo "      EXPECTED_MIN_AUDITS in formal/verify.sh deliberately and say why in formal/history/."; \
         exit 1; }
  BAD=$(echo "$AUDIT_OUT" | grep -iE "depends on axioms" \
        | grep -vE "\[(propext|Classical\.choice|Quot\.sound)(, (propext|Classical\.choice|Quot\.sound))*\]$" || true)
  if [ -n "$BAD" ]; then
    echo "FAIL: non-standard axioms in the audit:"
    echo "$BAD"
    exit 1
  fi
  echo "=== lean phase (steps 1-4) PASSED (holes=$SORRIES, audits=$OBSERVED_AUDITS) ==="
}

# ---------------------------------------------------------------------------- #
# Conformance gate: step 5.
#   run_conf <min_passed> <label> <pytest target...>
# ---------------------------------------------------------------------------- #
run_conf() {
  local min_passed="$1" label="$2"; shift 2
  echo "=== [5/5] Python conformance (sem vs oracle vs set engine vs graph model) ==="
  echo "  target: $label   (minimum passed: $min_passed)"
  # Preflight: the zcli binary MUST exist. Without it every Lean-comparison test calls
  # pytest.skip (runner.ZcliUnavailable), so the "hard gate" can pass having compared
  # NOTHING. Assert the binary is present before running pytest. (Built by the `lean`
  # phase / step 3 -- run that first.)
  local cand ZCLI_BIN=""
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
  local CONF_OUT CONF_RC CONF_SUMMARY CONF_PASSED word n
  CONF_OUT=$( cd "$REPO_ROOT" && "$PY" -m pytest "$@" -q 2>&1 )
  CONF_RC=$?
  echo "$CONF_OUT"
  [ "$CONF_RC" = "0" ] || { echo "FAIL: conformance (pytest rc=$CONF_RC)"; exit 1; }
  # Parse the final pytest summary line (last non-blank line, e.g.
  # "98 passed in 111.00s" or "2 passed, 3 skipped in 1.2s").
  CONF_SUMMARY=$(printf '%s\n' "$CONF_OUT" | grep -vE '^[[:space:]]*$' | tail -1)
  echo "  conformance summary: $CONF_SUMMARY"
  # ZERO TOLERANCE for any outcome that means "this comparison did not happen".
  # ZT-P2-2: the old parse looked only for `N skipped`, and pytest reports xfail as a
  # DISTINCT word -- so slapping @pytest.mark.xfail on a newly-failing comparison
  # yielded "329 passed, 1 xfailed" and the gate printed PASSED. `xpassed` means an
  # xfail marker is stale (the comparison passes but is marked expected-to-fail), and
  # `deselected` means a -k/-m filter silently dropped tests.
  for word in skipped xfailed xpassed deselected; do
    n=$(printf '%s\n' "$CONF_SUMMARY" | grep -oE "[0-9]+ $word" | grep -oE '^[0-9]+' || true)
    n=${n:-0}
    [ "$n" = "0" ] \
      || { echo "FAIL: conformance reported $n $word test(s) -- the gate must COMPARE, not"; \
           echo "      skip / expect-to-fail / filter out. formal/conformance/ carries zero"; \
           echo "      xfails by design: a divergence there is a bug to fix, not a marker"; \
           echo "      to add (CLAUDE.md endorses xfail only as a PIN in tests/)."; \
           exit 1; }
  done
  CONF_PASSED=$(printf '%s\n' "$CONF_SUMMARY" | grep -oE '[0-9]+ passed' | grep -oE '^[0-9]+' || true)
  CONF_PASSED=${CONF_PASSED:-0}
  [ "$CONF_PASSED" -gt 0 ] \
    || { echo "FAIL: conformance passed ZERO tests (nothing was actually compared)"; exit 1; }
  # ZT-P2-2: the count FLOOR. Without it, shrinking GRAPH_FRAGMENT to a single corpus
  # -- or deleting test_conformance_graph.py outright -- kept the gate green.
  [ "$CONF_PASSED" -ge "$min_passed" ] \
    || { echo "FAIL: conformance passed $CONF_PASSED test(s), below this phase's floor of $min_passed."; \
         echo "      Comparison coverage SHRANK: a corpus, a parametrization or a whole file"; \
         echo "      went away."; \
         echo "      * If the count GREW you would never see this -- the floors are -ge, so"; \
         echo "        ADDING tests is always safe. Bump MIN_CONF_ALL when convenient."; \
         echo "      * If the drop is INTENDED, lower MIN_CONF_ALL (and the legacy"; \
         echo "        MIN_CONF_HEAVY/MIN_CONF_REST, which are cross-checked to sum to it)"; \
         echo "        in formal/verify.sh deliberately, and record why."; \
         exit 1; }
  echo "=== conformance phase PASSED ($CONF_SUMMARY; floor $min_passed) ==="
}

# Tile I of K over the WHOLE conformance directory (1-based I).
#
# Union coverage is structural: the node ids are collected from $CONF_DIR at run time
# and assigned to tile ((index) mod K), so every collected test -- including any file,
# corpus or parametrization added later -- is in exactly one tile. Nothing is named by
# hand, so nothing can be dropped by forgetting to update a list.
run_conf_tile() {
  local i="$1" k="$2"
  local COL_OUT COL_RC nodes total expected tilen
  echo "=== [5/5] conformance tile $i/$k of $CONF_DIR ==="
  COL_OUT=$( cd "$REPO_ROOT" && "$PY" -m pytest "$CONF_DIR" -q --collect-only 2>&1 )
  COL_RC=$?
  [ "$COL_RC" = "0" ] \
    || { echo "FAIL: pytest --collect-only failed (rc=$COL_RC) on $CONF_DIR"; \
         printf '%s\n' "$COL_OUT" | tail -20; exit 1; }
  nodes=$(printf '%s\n' "$COL_OUT" | grep -E '^[^[:space:]]+\.py::')
  total=$(printf '%s\n' "$nodes" | grep -c '::' || true)
  echo "  collected: $total node id(s) (global floor $MIN_CONF_ALL)"
  # The GLOBAL coverage floor, asserted by EVERY tile phase -- so you cannot lose
  # conformance coverage by only ever running one tile.
  [ "$total" -ge "$MIN_CONF_ALL" ] \
    || { echo "FAIL: $CONF_DIR collects only $total test(s); the gate floor is $MIN_CONF_ALL."; \
         echo "      Conformance coverage SHRANK (a corpus, a parametrization or a whole"; \
         echo "      file went away). If intended, lower MIN_CONF_ALL in formal/verify.sh"; \
         echo "      deliberately (keep MIN_CONF_HEAVY + MIN_CONF_REST == MIN_CONF_ALL) and"; \
         echo "      record why. Adding tests never trips this (the check is -ge)."; \
         exit 1; }
  # Partition arithmetic: tile i (1-based) takes collection indices i-1, i-1+k, ...
  # so its size is floor((total - i) / k) + 1. Assert the awk selection agrees --
  # a mismatch would mean the tiling is not a partition and coverage has a hole.
  expected=$(( (total - i) / k + 1 ))
  local NODES=()
  mapfile -t NODES < <(printf '%s\n' "$nodes" | awk -v i="$((i - 1))" -v k="$k" '(NR - 1) % k == i')
  tilen=${#NODES[@]}
  echo "  tile $i/$k: $tilen node id(s) (partition arithmetic expects $expected)"
  [ "$tilen" = "$expected" ] \
    || { echo "FAIL: tile $i/$k selected $tilen node(s) but the partition arithmetic says"; \
         echo "      $expected -- the K tiles would NOT partition $CONF_DIR (coverage hole)."; \
         exit 1; }
  [ "$tilen" -gt 0 ] || { echo "FAIL: tile $i/$k is empty (K larger than the test count?)"; exit 1; }
  # Every selected node must PASS: the tile's own floor is its exact size.
  run_conf "$tilen" "conf-tile:$i/$k ($tilen of $total node ids)" "${NODES[@]}"
}

preflight_py
case "$PHASE" in
  lean)       run_lean ;;
  conf-heavy) run_conf "$MIN_CONF_HEAVY" "$HEAVY_CONF" "$HEAVY_CONF" ;;
  conf-rest)  run_conf "$MIN_CONF_REST" "$CONF_DIR minus $HEAVY_CONF" \
                "$CONF_DIR" --ignore="$HEAVY_CONF" ;;
  conf-tile:*) run_conf_tile "$TILE_I" "$TILE_K" ;;
  all)        run_lean; run_conf "$MIN_CONF_ALL" "$CONF_DIR" "$CONF_DIR" ;;
esac

echo ""
echo "=== verify.sh: phase '$PHASE' PASSED ==="
