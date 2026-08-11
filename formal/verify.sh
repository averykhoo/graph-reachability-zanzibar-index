#!/usr/bin/env bash
# One-command green gate for the formal-verification effort (plan C4 / Phase 6).
# Runs from the repo root or anywhere. Requires elan on PATH (or ~/.elan/bin).
#
#   bash formal/verify.sh                 # all gates, one shot (uncapped / CI)
#   bash formal/verify.sh lean            # steps 1-4 only  (Lean build + audit)
#   bash formal/verify.sh conf-tile:1/5   # step 5, tile 1 of 5 of the conformance dir
#   bash formal/verify.sh tests-tile:1/4  # step 5, tile 1 of 4 of tests/
#   bash formal/verify.sh conf-heavy      # step 5, the one heavy file      (legacy split)
#   bash formal/verify.sh conf-rest       # step 5, the dir minus that file (legacy split)
#
# PHASED MODE (the split gate). The one-shot run is ~18-20 min and does NOT fit a
# 10-min execution cap (e.g. an agent harness). The phase args partition the SAME
# work -- same anti-vacuous guards, no coverage gaps -- into cap-fitting pieces an
# unattended runner can execute in sequence. RECOMMENDED SEQUENCE (2026-07-26):
#
#     lean → conf-tile:1/5 … conf-tile:5/5 → tests-tile:1/4 … tests-tile:4/4
#
# The `tests-tile:I/K` phases are new on 2026-07-27 and are the reason the whole
# gate is now mechanical. `tests/` (728 tests: the 4-way validation matrix, the
# lookup-surface oracle gate, the hypothesis campaign, the snapshot gate) had NO
# branch in this script -- running it was an agent typing `pytest tests/` and
# reading the tail, with no floor, no skipped/xfailed parse and no exit-code
# assertion. It now goes through exactly the same guards as conformance.
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
#      hard-coded floor on the number of audited theorems; PLUS (2026-07-27,
#      ZT-P2-5) three checks that make the audit an IDENTITY and a STATEMENT
#      check rather than a bare COUNT:
#        4a IDENTITY  -- the live `#print axioms` name set must be a SUPERSET of
#           formal/audited_theorems.txt, so deleting `#print axioms graph_correct`
#           and adding `#print axioms Nat.add_comm` (count unchanged!) now FAILS
#        4b STATEMENT -- formal/conformance/statement_pin.py diffs each headline
#           theorem's statement text against formal/headline_statements.txt, so
#           `theorem graph_correct : True := trivial` -- which BUILDS, carries no
#           `sorry` TOKEN, and audits clean -- now FAILS
#        4c DEFINITION (2026-07-27, ZT-P5-LEG0) -- the same script also diffs the
#           full text of every project declaration those statements DEPEND ON
#           against formal/headline_definitions.txt, so deleting the `twoStrata`
#           FIELD of `structure W4Fragment` -- which weakens `graph_correct` while
#           leaving its pinned statement byte-identical and changing no
#           declaration name, defeating both 4a and 4b -- now FAILS
#        4d ANCHORS   -- formal/conformance/anchor_check.py resolves every
#           `file::symbol` anchor in formal/CORRESPONDENCE.md (the model<->code
#           map, which had NO drift detector at all)
#      plus: a headline theorem reporting "does not depend on any axioms" is
#      treated as SUSPICIOUS -- a real theorem over this development depends on
#      at least propext.
#   5. Python conformance suite passes           -- sem vs oracle vs set engine,
#      plus (Phase 6) the Lean OPERATIONAL graph model (zcli mode "graph",
#      GraphIndex/Exec.lean) vs the real Python graph index over the
#      W4Fragment corpora; with count floors and zero tolerance for
#      skipped/xpassed/deselected. `xfailed` is zero for conformance and carries a
#      DECLARED budget for tests/ ($MAX_TESTS_XFAILED, 0 today) -- CLAUDE.md
#      endorses a strict xfail there as a PIN on a filed divergence, and a blanket
#      zero would push the next author to delete the pin instead of the divergence.
#
# GATE SELF-DEFENCE (zero-trust review 2026-07-26, ZT-P2-1..6). Every hard-coded
# number below is a FLOOR asserted with -ge, so ADDING theorems/tests never fails the
# gate; only REMOVING assurance does. Lowering any of them must be a deliberate,
# reviewed edit to this file -- that is the whole point: before this, deleting audited
# theorems or conformance corpora kept the gate green.

set -uo pipefail

USAGE="usage: verify.sh [all|lean|conf-tile:I/K|tests-tile:I/K|conf-heavy|conf-rest]
       conf-tile:I/K   1 <= I <= K; the K tiles partition formal/conformance/
                       (recommended: conf-tile:1/5 .. conf-tile:5/5; K is free --
                        raise it when a tile approaches the ~600 s command cap)
       tests-tile:I/K  the same tiling over tests/ (recommended K=4). Until
                       2026-07-27 tests/ was outside the mechanical gate entirely:
                       an agent typed 'pytest tests/' and read the tail, with no
                       count floor, no skipped/xfailed check, and no proof that a
                       tile collected anything (ZT gate audit C1/M9)."

PHASE="${1:-all}"
TILE_I=""; TILE_K=""; SUITE_KIND="conf"
case "$PHASE" in
  all|lean|conf-heavy|conf-rest) ;;
  conf-tile:*/*|tests-tile:*/*)
    case "$PHASE" in tests-tile:*) SUITE_KIND="tests" ;; esac
    _spec="${PHASE#*-tile:}"
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
TESTS_DIR="tests/"                      # the backend suite -- see MIN_TESTS_ALL
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
# Minimum tests the conformance directory must COLLECT. Re-measured 2026-07-28 with
# `pytest formal/conformance/ -q --collect-only`: 464 (was 450 on 2026-07-27; +14
# from the two zero-coverage corpora `wildcard_userset` / `derived_tupleset_ttu`
# and their pins -- 6 spec-side + 8 in test_conformance_nary_strata.py).
# Every `conf-tile:I/K` phase
# asserts this against the live collection BEFORE tiling, so the global coverage
# floor is checked by each tile independently -- and each tile's own pass floor is
# then its exact tile size (all selected tests must pass).
# ADDING tests never trips this. LOWERING it must be a deliberate, reviewed edit
# here -- without a floor, shrinking GRAPH_FRAGMENT to a single corpus or deleting
# test_conformance_graph.py outright kept the gate green (ZT-P2-2).
# Re-measured 2026-08-11 with `pytest formal/conformance/ -q --collect-only`: 494.
MIN_CONF_ALL=494

# Minimum tests `tests/` must COLLECT. Measured 2026-07-27 with
# `pytest tests/ -q --collect-only`: 728.
#
# WHY THIS EXISTS AT ALL. Until 2026-07-27 the 728-test backend suite -- the 4-way
# validation matrix, the lookup-surface oracle gate, the hypothesis campaign, the
# compiled-RuleSet snapshot gate -- was OUTSIDE this script. `verify.sh` had no
# branch that ran it; the gate was an agent typing `pytest tests/` and eyeballing
# the tail. So none of the self-defence the conformance side gained on 2026-07-26
# applied to it: no count floor, no zero-tolerance skipped/xfailed/xpassed parse,
# no exit-code assertion, no proof a tile collected anything. `tests-tile:I/K`
# reuses the conformance machinery verbatim, so all of it now does.
#
# Note the Postgres leg (`tests/test_postgres_ha.py`) is dropped at COLLECTION
# when no ZANZIBAR_TEST_DSN is set, not skipped at run time -- otherwise its skips
# would have to be tolerated here, and a tolerated skip is how coverage leaks.
# Re-measured 2026-08-11 with `pytest tests/ -q --collect-only`: 846 (was 823, and
# 763 before that). +23 from the real-world shape corpus: test_real_world_shapes.py
# (18), the derived-boolean-routing pin in test_zanzibar_utils.py (1), and the two new
# .fga fixtures flowing through the snapshot + parse parametrizations (4).
MIN_TESTS_ALL=846

# XFAIL BUDGET for `tests/` (and ONLY for `tests/`).
#
# `formal/conformance/` carries a hard zero: a divergence there is a bug to fix,
# not a marker to add. `tests/` is different, and the difference is DOCUMENTED --
# CLAUDE.md endorses a STRICT xfail as the legitimate way to PIN a genuine
# divergence while it is being fixed (that is how X1-X4 were tracked; see
# docs/spec-deviations.md and tests/test_lookup_oracle.py). A blanket zero here
# would silently override a project convention, and the first person to follow
# CLAUDE.md correctly would meet a red gate and be tempted to DELETE the pin
# instead of bumping a number -- a self-inflicted version of the exact erosion
# this script exists to stop.
#
# So: a DECLARED budget, asserted with -le. Raising it is a deliberate act and the
# commit should point at the filed divergence (docs/spec-deviations.md); it MUST
# come back down when the pin is flipped -- that is what closes the divergence out.
# `xpassed` / `skipped` / `deselected` stay at a hard zero for BOTH suites: an
# xpass means the pin is stale, which must be loud (the repo-root pytest.ini sets
# xfail_strict = true, so a stale pin also fails locally).
#
# BACK TO ZERO (2026-07-27, later the same day). It was briefly 1, for
# `tests/test_postgres_ha.py::test_open_instance_races_a_concurrent_commit` --
# `TupleSource.__init__` read the log watermark and THEN rebuilt the set engine,
# two statements that are atomic under a pinned SQLite-WAL snapshot and are not at
# PostgreSQL READ COMMITTED. `_consistent_rebuild` (optimistic wm1/rebuild/wm2 with
# a bounded retry, falling back to a SHARED lock on the SchemaV4 row) closed it, and
# the pin became a plain test. There are now ZERO live xfail markers in tests/.
#
# Keep it at 0 unless you are genuinely pinning a filed divergence. The budget
# exists so that pinning one is a VISIBLE, deliberate act -- not so that xfails are
# routine. Raise it with a commit that names the divergence; lower it the moment
# the pin flips.
MAX_TESTS_XFAILED=0

# Skip budget for `tests/`, and ONLY when ZANZIBAR_TEST_DSN is set (the default
# SQLite gate keeps a hard zero -- see the loop in run_conf). Measured 2026-07-27
# against PostgreSQL 17.10: exactly 3, all SQLite-only by nature --
#   test_connectedstore_multi_instance.py::test_stale_read_pinned_snapshot
#   test_connectedstore_multi_instance.py::test_token_not_visible_in_pinned_snapshot_raises
#   test_connectedstore_concurrency.py::test_reader_session_sees_consistent_snapshots
# The first two exercise the StaleRead pinned-snapshot path; the third asserts a
# replica never sees torn state. PostgreSQL at READ COMMITTED gives a reader no
# stable snapshot at all, so neither property EXISTS on the server -- they are
# SQLite-WAL inheritances, which is itself one of the 2026-07-27 findings. Tests
# that are meaningless on a dialect are skipped rather than made to lie; anything
# ABOVE 3 means a test that should have run did not.
MAX_TESTS_SKIPPED_ON_RDBMS=3

# Legacy file-carve split. Measured 2026-07-26 (per-file wall clock):
#   test_conformance_remove.py   80 tests, ~170 s   -> conf-heavy
#   test_conformance_enum.py      6 tests, ~380-475 s (the real hog inside conf-rest;
#     the 2026-07-19g note blamed test_conformance_remove_graph.py, which is ~27 s)
HEAVY_CONF="formal/conformance/test_conformance_remove.py"
# Re-measured 2026-08-11: test_conformance_remove.py collects 104; 494 - 104 = 390.
MIN_CONF_HEAVY=104
MIN_CONF_REST=390

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
EXPECTED_MIN_AUDITS=460

# Minimum number of project .lean files the soundness scan must cover (ZT-P2-4).
# Measured 2026-07-26: 65 files under formal/lean excluding .lake/** (it was 64 when
# the scan pointed at formal/lean/ZanzibarProofs and so missed the library root
# ZanzibarProofs.lean). A little slack for renames/merges; a collapse to a handful of
# files means the scan lost the tree and its clean 0 is not evidence.
MIN_SCANNED_LEAN_FILES=64

# ---------------------------------------------------------------------------- #
# ZT-P2-5 (2026-07-27): the audit was a COUNT, not an identity or a statement pin.
# Two erosions kept the gate fully green:
#   (i)  delete `#print axioms graph_correct`, add `#print axioms Nat.add_comm`
#        -- OBSERVED == EXPECTED == 457 still, so nothing noticed;
#   (ii) restate `theorem graph_correct : True := trivial` -- it BUILDS, the
#        token-level sorry_scan finds nothing (it scans TOKENS, not STATEMENTS),
#        and the audit prints a perfectly clean report.
# ZT-P3-2 already proved that vacuous audited lemmas are not hypothetical: this
# very Audit.lean knowingly carries a superseded UNSATISFIABLE pair.
# ---------------------------------------------------------------------------- #
# (a) IDENTITY. The checked-in name list every audit run must still cover. The
# live `#print axioms` extraction must be a SUPERSET of it, so ADDING audits is
# free and swapping a headline theorem out for a filler one FAILS.
AUDIT_PIN="$REPO_ROOT/formal/audited_theorems.txt"
# ...and a floor on the PIN itself, or emptying the pin file would make the
# superset test vacuously true (the ZT-P2-1 shape, one level up). Measured
# 2026-07-27: 457 names.
MIN_PINNED_AUDITS=460

# (c) DEFINITION pin (ZT-P5-LEG0, 2026-07-27). The statement pin (4b) closed
# `theorem graph_correct : True := trivial`. It does NOT close the strictly-weaker
# restatement made from UNDERNEATH: `graph_correct`'s entire proved scope is
# carried by `(hA : GraphAdmission S T) (hF : W4Fragment S T)`, recorded in
# headline_statements.txt BY NAME. Both are `structure`s. Delete
# `W4Fragment.twoStrata` -- one line in FullScope.lean -- and the theorem claims
# something strictly weaker over a strictly larger class of schemas, while its
# pinned statement line stays BYTE-IDENTICAL and no declaration name changes, so
# 4a is blind too. The same hole existed for `sem` and `GraphModel.check`, i.e.
# for the `check := sem` model the project's own honesty norm forbids.
# formal/headline_definitions.txt pins the text of every project declaration the
# 26 statements transitively depend on (132 today, closure measured to converge at
# depth 9 inside the project), plus the `variable`/`open` ambient context of the
# files hosting them (7). Floor measured 2026-07-27: 139 rows.
DEF_PIN="$REPO_ROOT/formal/headline_definitions.txt"
MIN_PINNED_DEFS=139

# The HEADLINE theorems -- the ones FINAL_REVIEW.md §2 states in English. Two
# extra rules apply to exactly these:
#   * each MUST appear in the audit output at all (also covered by the identity
#     pin, deliberately belt-and-suspenders), and
#   * "does not depend on any axioms" is SUSPICIOUS for them. A genuine theorem
#     over this development goes through Classical.choice / propext / Quot.sound;
#     a `: True := trivial` restatement depends on nothing, which is precisely
#     the tell the old gate ignored. (12 lemmas elsewhere in Audit.lean legitimately
#     report no axioms -- structural facts proved by `rfl`/`cases` -- which is why
#     this rule is scoped to the headline set rather than applied globally.)
HEADLINE_AUDITS="setEngine_correct sem_fuel_stable stratify_none_iff_cycle
stratify_topological pathCount_addEdge pathCount_removeEdge runCascade2_no_abort
cascade2_drains graph_correct graph_reached_inv backend_equivalence
exclusion_effective no_ghost_grant graphRun_reached graphRun_check_eq_sem"

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

  # -------------------------------------------------------------------------- #
  # 4a. IDENTITY pin (ZT-P2-5). WHICH theorems are audited, not just how many.
  # -------------------------------------------------------------------------- #
  echo "--- [4a/5] audit IDENTITY pin (formal/audited_theorems.txt) ---"
  [ -f "$AUDIT_PIN" ] \
    || { echo "FAIL: audit identity pin missing: $AUDIT_PIN"; \
         echo "      regenerate with: bash formal/regen_audit_pin.sh"; exit 1; }
  PINNED_AUDITS=$(grep -cvE '^#|^[[:space:]]*$' "$AUDIT_PIN")
  [ "$PINNED_AUDITS" -ge "$MIN_PINNED_AUDITS" ] \
    || { echo "FAIL: $AUDIT_PIN lists only $PINNED_AUDITS name(s); floor is $MIN_PINNED_AUDITS."; \
         echo "      The pin itself was gutted -- a SUPERSET test against an empty pin"; \
         echo "      passes vacuously, which is the very failure mode this closes."; \
         exit 1; }
  LIVE_AUDIT_NAMES=$(grep -oE '^#print axioms [^[:space:]]+' "$AUDIT_LEAN" \
                     | awk '{print $3}' | LC_ALL=C sort -u)
  MISSING_AUDITS=$(LC_ALL=C comm -23 \
    <(grep -vE '^#|^[[:space:]]*$' "$AUDIT_PIN" | LC_ALL=C sort -u) \
    <(printf '%s\n' "$LIVE_AUDIT_NAMES"))
  echo "  audited-name identity: $PINNED_AUDITS pinned, $(printf '%s\n' "$LIVE_AUDIT_NAMES" | grep -c . ) live (live must be a SUPERSET)"
  if [ -n "$MISSING_AUDITS" ]; then
    echo "FAIL: pinned audited theorem(s) are NO LONGER audited by Audit.lean:"
    printf '%s\n' "$MISSING_AUDITS" | sed 's/^/        /' | head -30
    echo "      The audit COUNT can be held constant by adding filler lines"
    echo "      (\`#print axioms Nat.add_comm\`), which is why the count alone was"
    echo "      never evidence. If a removal is intended, regenerate the pin"
    echo "      deliberately (bash formal/regen_audit_pin.sh) and say why in"
    echo "      formal/history/."
    exit 1
  fi

  # Headline theorems: present, and NOT axiom-free (a `: True := trivial`
  # restatement depends on nothing at all).
  for _t in $HEADLINE_AUDITS; do
    _line=$(printf '%s\n' "$AUDIT_OUT" | grep -E "'(Zanzibar\.)?${_t}' (depends on axioms|does not depend)" || true)
    [ -n "$_line" ] \
      || { echo "FAIL: headline theorem '$_t' produced NO audit report."; \
           echo "      Either its '#print axioms' line is gone or the theorem is."; exit 1; }
    case "$_line" in
      *"does not depend on any axioms"*)
        echo "FAIL: headline theorem '$_t' depends on NO axioms:"
        echo "        $_line"
        echo "      Every real theorem over this development is routed through"
        echo "      propext / Classical.choice / Quot.sound. An axiom-free headline"
        echo "      theorem is the signature of a VACUOUS restatement (e.g."
        echo "      ': True := trivial'), which builds and audits clean."
        exit 1;;
    esac
  done
  echo "  headline theorems: $(printf '%s\n' $HEADLINE_AUDITS | grep -c .) audited, all axiom-dependent"

  # -------------------------------------------------------------------------- #
  # 4b. STATEMENT pin (ZT-P2-5 (ii)). WHAT the headline theorems say.
  # 4c. DEFINITION pin (ZT-P5-LEG0). What those words MEAN. Same script, two
  #     goldens -- the second closes the hole the first one's docstring used to
  #     concede: `graph_correct`'s scope is carried by `(hF : W4Fragment S T)`,
  #     recorded BY NAME, so deleting the `twoStrata` FIELD of that structure
  #     weakens the theorem while leaving the pinned statement byte-identical and
  #     changing no declaration name (so 4a is blind too). See
  #     formal/conformance/statement_pin.py's docstring for the recursion depth,
  #     the churn measurement behind it, and -- read this part -- what it still
  #     cannot see.
  # -------------------------------------------------------------------------- #
  echo "--- [4b/5] headline STATEMENT pin (formal/headline_statements.txt) ---"
  echo "--- [4c/5] headline DEFINITION pin (formal/headline_definitions.txt) ---"
  # The golden's own floor, asserted here as well as inside the script, exactly as
  # MIN_PINNED_AUDITS is for the identity pin: a truncated or emptied golden makes
  # the comparison pass over nothing, which is the ZT-P2-1 shape one level down.
  [ -f "$DEF_PIN" ] \
    || { echo "FAIL: definition pin missing: $DEF_PIN"; \
         echo "      regenerate with: \"\$PY\" formal/conformance/statement_pin.py --generate"; \
         exit 1; }
  PINNED_DEFS=$(grep -cvE '^#|^[[:space:]]*$' "$DEF_PIN")
  [ "$PINNED_DEFS" -ge "$MIN_PINNED_DEFS" ] \
    || { echo "FAIL: $DEF_PIN lists only $PINNED_DEFS row(s); floor is $MIN_PINNED_DEFS."; \
         echo "      The definition pin was gutted -- a comparison over a truncated"; \
         echo "      golden passes vacuously. If definitions genuinely left the"; \
         echo "      headline statements' dependency closure, lower MIN_PINNED_DEFS"; \
         echo "      here (and in statement_pin.py) deliberately and say why in"; \
         echo "      formal/history/."; \
         exit 1; }
  "$PY" "$REPO_ROOT/formal/conformance/statement_pin.py" \
    || { echo "FAIL: headline statement/definition pin (see above)"; exit 1; }
  echo "  definition pin rows: $PINNED_DEFS (floor $MIN_PINNED_DEFS)"

  # -------------------------------------------------------------------------- #
  # 4d. CORRESPONDENCE.md anchor pin. The model<->code map had NO drift detector:
  # it was rebuilt onto ~349 file::symbol anchors on 2026-07-26, hand-verified
  # once, and nothing checked it afterwards -- against an unchanged ~3,000
  # lines/2-weeks drift rate that had already destroyed its predecessor's line
  # numbers. Cheap (~1 s, no Lean toolchain), so it rides the `lean` phase.
  # -------------------------------------------------------------------------- #
  echo "--- [4d/5] CORRESPONDENCE.md anchor pin ---"
  "$PY" "$REPO_ROOT/formal/conformance/anchor_check.py" \
    || { echo "FAIL: CORRESPONDENCE.md anchors (see above)"; exit 1; }

  # -------------------------------------------------------------------------- #
  # 4e. FINAL_REVIEW.md COUNTS pin. `ZT-P3-5` found every number in every claim
  # doc stale with NOTHING enforcing any of them. It was hand-fixed 2026-07-26,
  # hand-fixed again 2026-07-28 (`7fce0f1`), and was stale AGAIN on 2026-07-29 --
  # including FINAL_REVIEW's own header stating two different values for the same
  # quantity, the exact defect its text diagnoses. Three hand-fixes of one defect
  # is this repo's signal to build a refusal instead. The governing doc's counts
  # are now GENERATED and checked here. ~30 s, so it rides the `lean` phase with
  # the other pins. COST BREAKDOWN (measured 2026-08-05, warm, this machine):
  # ~24-28 s of that is 17 pytest --collect-only SUBPROCESSES (Windows spawn
  # overhead, not collection work), plus ~5 s for the state-gate projection ledger
  # (23 corpora driven through the real graph index). This comment said "~4 s"
  # until 2026-08-05; it was never re-measured after the per-file table landed,
  # which is the same hand-maintained-number defect the step itself exists to fix
  # -- noted here rather than quietly corrected.
  # Scope, stated honestly: this pins ONE block in ONE file. Prose counts
  # elsewhere are still hand-maintained -- but there is now an authoritative
  # machine-checked place to check them against, and extending the block is one
  # row in doc_counts.py::measure.
  # -------------------------------------------------------------------------- #
  echo "--- [4e/5] FINAL_REVIEW.md counts pin ---"
  ( cd "$REPO_ROOT" && PYTHONPATH="$REPO_ROOT" "$PY" -m formal.conformance.doc_counts --check ) \
    || { echo "FAIL: FINAL_REVIEW.md counts pin (see above)"; exit 1; }

  echo "=== lean phase (steps 1-4) PASSED (holes=$SORRIES, audits=$OBSERVED_AUDITS, pinned=$PINNED_AUDITS) ==="
}

# ---------------------------------------------------------------------------- #
# Conformance gate: step 5.
#   run_conf <min_passed> <label> <pytest target...>
# ---------------------------------------------------------------------------- #
run_conf() {
  local min_passed="$1" label="$2"; shift 2
  case "${SUITE_KIND:-conf}" in
    tests) echo "=== [5/5] Python backend suite (matrix / parity / lookup oracle / hypothesis) ===" ;;
    *)     echo "=== [5/5] Python conformance (sem vs oracle vs set engine vs graph model) ===" ;;
  esac
  echo "  target: $label   (minimum passed: $min_passed)"
  # Preflight: the zcli binary MUST exist. Without it every Lean-comparison test calls
  # pytest.skip (runner.ZcliUnavailable), so the "hard gate" can pass having compared
  # NOTHING. Assert the binary is present before running pytest. (Built by the `lean`
  # phase / step 3 -- run that first.) `tests/` never shells out to zcli, so the
  # preflight is conformance-only.
  local cand ZCLI_BIN=""
  if [ "${SUITE_KIND:-conf}" = "conf" ]; then
    for cand in "$LEAN_DIR/.lake/build/bin/zcli" "$LEAN_DIR/.lake/build/bin/zcli.exe"; do
      [ -f "$cand" ] && ZCLI_BIN="$cand"
    done
    [ -n "$ZCLI_BIN" ] \
      || { echo "FAIL: zcli binary not found under $LEAN_DIR/.lake/build/bin (expected zcli or zcli.exe)"; \
           echo "      -- conformance would skip every Lean comparison and pass vacuously"; \
           echo "      -- run 'bash formal/verify.sh lean' first (it builds zcli)"; \
           exit 1; }
    echo "  zcli binary: $ZCLI_BIN"
  fi
  # Capture pytest output, echo it through, then gate on the summary line.
  local CONF_OUT CONF_RC CONF_SUMMARY CONF_PASSED CONF_ACCOUNTED word n
  CONF_OUT=$( cd "$REPO_ROOT" && "$PY" -m pytest "$@" -q 2>&1 )
  CONF_RC=$?
  echo "$CONF_OUT"
  [ "$CONF_RC" = "0" ] || { echo "FAIL: ${SUITE_KIND:-conf} (pytest rc=$CONF_RC)"; exit 1; }
  # Parse the final pytest summary line (last non-blank line, e.g.
  # "98 passed in 111.00s" or "2 passed, 3 skipped in 1.2s").
  CONF_SUMMARY=$(printf '%s\n' "$CONF_OUT" | grep -vE '^[[:space:]]*$' | tail -1)
  echo "  ${SUITE_KIND:-conf} summary: $CONF_SUMMARY"
  # ZERO TOLERANCE for any outcome that means "this comparison did not happen".
  # ZT-P2-2: the old parse looked only for `N skipped`, and pytest reports xfail as a
  # DISTINCT word -- so slapping @pytest.mark.xfail on a newly-failing comparison
  # yielded "329 passed, 1 xfailed" and the gate printed PASSED. `xpassed` means an
  # xfail marker is stale (the comparison passes but is marked expected-to-fail), and
  # `deselected` means a -k/-m filter silently dropped tests.
  # `xfailed` is the ONE outcome with a declared budget, and only for `tests/`
  # (MAX_TESTS_XFAILED, 0 today) -- see the comment on that variable. Everything
  # else, and everything in formal/conformance/, is a hard zero.
  local budget budget_knob XFAILED_N=0 SKIPPED_N=0
  for word in skipped xfailed xpassed deselected; do
    budget=0; budget_knob="(none -- $word is never acceptable)"
    if [ "$word" = "xfailed" ] && [ "${SUITE_KIND:-conf}" = "tests" ]; then
      budget="$MAX_TESTS_XFAILED"; budget_knob=MAX_TESTS_XFAILED
    fi
    # The ONE legitimate skip budget, and it exists only in the PostgreSQL
    # configuration. Three tests in the shared HA modules are SQLite-only BY
    # NATURE, not by omission: two pin the `StaleRead` pinned-snapshot path and one
    # pins the "a replica never sees torn state" property -- and PostgreSQL at READ
    # COMMITTED (the only level admitted) gives a reader NO stable snapshot, so
    # those properties do not exist there to be tested. They are `skipif`-ed on
    # `ZANZIBAR_TEST_DSN`, so the DEFAULT SQLite gate still sees a hard zero.
    # Declared here rather than tolerated silently: without it, running the gate
    # against a real server -- the thing we most want people to do -- goes red for
    # a non-reason, and the obvious "fix" is to delete the skipped/xfailed check.
    if [ "$word" = "skipped" ] && [ "${SUITE_KIND:-conf}" = "tests" ] \
       && [ -n "${ZANZIBAR_TEST_DSN:-}" ]; then
      budget="$MAX_TESTS_SKIPPED_ON_RDBMS"; budget_knob=MAX_TESTS_SKIPPED_ON_RDBMS
    fi
    n=$(printf '%s\n' "$CONF_SUMMARY" | grep -oE "[0-9]+ $word" | grep -oE '^[0-9]+' || true)
    n=${n:-0}
    [ "$n" -le "$budget" ] \
      || { echo "FAIL: ${SUITE_KIND:-conf} reported $n $word test(s) (budget $budget) -- the gate must"; \
           echo "      COMPARE, not skip / expect-to-fail / filter out. formal/conformance/"; \
           echo "      carries zero xfails by design: a divergence there is a bug to fix,"; \
           echo "      not a marker to add. In tests/, CLAUDE.md DOES endorse a strict xfail"; \
           echo "      as a PIN on a genuine divergence, and a dialect-only skip is"; \
           echo "      legitimate on the PostgreSQL leg -- but each needs a DECLARED"; \
           echo "      budget, not silence. The knob for '$word' is $budget_knob."; \
           echo "      Raise it in formal/verify.sh deliberately, point the commit at the"; \
           echo "      filed divergence (docs/spec-deviations.md), and lower it again when"; \
           echo "      the pin is flipped. Do NOT delete the pin to get green."; \
           exit 1; }
    if [ "$word" = "xfailed" ]; then XFAILED_N="$n"; fi
    if [ "$word" = "skipped" ]; then SKIPPED_N="$n"; fi
  done
  CONF_PASSED=$(printf '%s\n' "$CONF_SUMMARY" | grep -oE '[0-9]+ passed' | grep -oE '^[0-9]+' || true)
  CONF_PASSED=${CONF_PASSED:-0}
  [ "$CONF_PASSED" -gt 0 ] \
    || { echo "FAIL: ${SUITE_KIND:-conf} passed ZERO tests (nothing was actually run)"; exit 1; }
  # ZT-P2-2: the count FLOOR. Without it, shrinking GRAPH_FRAGMENT to a single corpus
  # -- or deleting test_conformance_graph.py outright -- kept the gate green.
  # A budgeted xfail (tests/ only, see MAX_TESTS_XFAILED) is COUNTED here: the test
  # still ran and still asserted, it just asserted a pinned divergence. Without this
  # the budget would be dead letter -- the tile floor (= the tile's exact size) would
  # fail on the very xfail the budget just allowed.
  # The floor is the tile's exact size, so every outcome that was BUDGETED above has
  # to count toward it -- otherwise the budget is a dead letter: allowing an xfail or
  # a dialect-only skip past the zero-tolerance loop and then failing the floor for
  # that same test would just move the red one line down.
  CONF_ACCOUNTED=$(( CONF_PASSED + XFAILED_N + SKIPPED_N ))
  [ "$CONF_ACCOUNTED" -ge "$min_passed" ] \
    || { echo "FAIL: ${SUITE_KIND:-conf} passed $CONF_PASSED test(s) (+$XFAILED_N budgeted xfail, +$SKIPPED_N budgeted skip), below this phase's floor of $min_passed."; \
         echo "      Comparison coverage SHRANK: a corpus, a parametrization or a whole file"; \
         echo "      went away."; \
         echo "      * If the count GREW you would never see this -- the floors are -ge, so"; \
         echo "        ADDING tests is always safe. Bump MIN_CONF_ALL when convenient."; \
         echo "      * If the drop is INTENDED, lower MIN_CONF_ALL (and the legacy"; \
         echo "        MIN_CONF_HEAVY/MIN_CONF_REST, which are cross-checked to sum to it)"; \
         echo "        in formal/verify.sh deliberately, and record why."; \
         exit 1; }
  echo "=== ${SUITE_KIND:-conf} phase PASSED ($CONF_SUMMARY; floor $min_passed) ==="
}

# Tile I of K over the WHOLE conformance directory (1-based I).
#
# Union coverage is structural: the node ids are collected from $CONF_DIR at run time
# and assigned to tile ((index) mod K), so every collected test -- including any file,
# corpus or parametrization added later -- is in exactly one tile. Nothing is named by
# hand, so nothing can be dropped by forgetting to update a list.
run_conf_tile() {
  local i="$1" k="$2"
  local dir="${3:-$CONF_DIR}" floor="${4:-$MIN_CONF_ALL}"
  local COL_OUT COL_RC nodes total expected tilen
  echo "=== [5/5] ${SUITE_KIND:-conf} tile $i/$k of $dir ==="
  COL_OUT=$( cd "$REPO_ROOT" && "$PY" -m pytest "$dir" -q --collect-only 2>&1 )
  COL_RC=$?
  [ "$COL_RC" = "0" ] \
    || { echo "FAIL: pytest --collect-only failed (rc=$COL_RC) on $dir"; \
         printf '%s\n' "$COL_OUT" | tail -20; exit 1; }
  nodes=$(printf '%s\n' "$COL_OUT" | grep -E '^[^[:space:]]+\.py::')
  total=$(printf '%s\n' "$nodes" | grep -c '::' || true)
  echo "  collected: $total node id(s) (global floor $floor)"
  # The GLOBAL coverage floor, asserted by EVERY tile phase -- so you cannot lose
  # coverage by only ever running one tile.
  [ "$total" -ge "$floor" ] \
    || { echo "FAIL: $dir collects only $total test(s); the gate floor is $floor."; \
         echo "      Coverage SHRANK (a corpus, a parametrization or a whole file went"; \
         echo "      away). If intended, lower the floor in formal/verify.sh deliberately"; \
         echo "      (for conformance, keep MIN_CONF_HEAVY + MIN_CONF_REST == MIN_CONF_ALL)"; \
         echo "      and record why. Adding tests never trips this (the check is -ge)."; \
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
         echo "      $expected -- the K tiles would NOT partition $dir (coverage hole)."; \
         exit 1; }
  [ "$tilen" -gt 0 ] || { echo "FAIL: tile $i/$k is empty (K larger than the test count?)"; exit 1; }
  # Every selected node must PASS: the tile's own floor is its exact size.
  run_conf "$tilen" "${SUITE_KIND:-conf}-tile:$i/$k ($tilen of $total node ids)" "${NODES[@]}"
}

preflight_py
case "$PHASE" in
  lean)       run_lean ;;
  conf-heavy) run_conf "$MIN_CONF_HEAVY" "$HEAVY_CONF" "$HEAVY_CONF" ;;
  conf-rest)  run_conf "$MIN_CONF_REST" "$CONF_DIR minus $HEAVY_CONF" \
                "$CONF_DIR" --ignore="$HEAVY_CONF" ;;
  conf-tile:*)  run_conf_tile "$TILE_I" "$TILE_K" "$CONF_DIR" "$MIN_CONF_ALL" ;;
  tests-tile:*) run_conf_tile "$TILE_I" "$TILE_K" "$TESTS_DIR" "$MIN_TESTS_ALL" ;;
  all)        run_lean
              SUITE_KIND=tests run_conf "$MIN_TESTS_ALL" "$TESTS_DIR" "$TESTS_DIR"
              run_conf "$MIN_CONF_ALL" "$CONF_DIR" "$CONF_DIR" ;;
esac

echo ""
echo "=== verify.sh: phase '$PHASE' PASSED ==="
