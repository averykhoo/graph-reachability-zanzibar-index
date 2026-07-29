"""Unit tests for the extracted soundness-hole scanner (formal/conformance/sorry_scan.py).

The scanner used to live as an inline heredoc in formal/verify.sh where its tricky
comment/string/char-literal handling was untested. These tests pin exactly the cases
that make it subtle: a `sorry` appearing inside a line comment, a block comment, a
string literal, or a char literal must NOT be counted; a real top-level `sorry` or
`admit` MUST be counted; nested block comments are handled.

The 2026-07-26 zero-trust review (`ZT-P2-3`) found the scanner blind to four further
ways a "0 sorries" tree can be unsound, each of which is now pinned below:
`sorryAx` (the constant `sorry` elaborates to — `\\bsorry\\b` cannot match it),
`native_decide` (pulls `Lean.ofReduceBool`), a custom `axiom` declaration, and a
stray unterminated string literal that used to make the rest of a file invisible
*in silence*. Plus the vendored-`.lake` exclusion and the `--min-files` coverage
floor that let verify.sh widen the scan to the whole `formal/lean` tree (`ZT-P2-4`).
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from formal.conformance import sorry_scan


def _write(tmp_path, text: str, name: str = "T.lean"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return tmp_path


# --- must NOT trip: the token appears only inside a comment/string/char literal ---

def test_line_comment_does_not_trip(tmp_path):
    root = _write(tmp_path, "theorem foo : True := trivial  -- TODO: sorry later\n")
    assert sorry_scan.scan(root) == 0


def test_block_comment_does_not_trip(tmp_path):
    root = _write(tmp_path, "/- this proof still has a sorry to discharge -/\n"
                            "theorem foo : True := trivial\n")
    assert sorry_scan.scan(root) == 0


def test_docstring_does_not_trip(tmp_path):
    root = _write(tmp_path, "/-- mentions sorry and admit in prose -/\n"
                            "theorem foo : True := trivial\n")
    assert sorry_scan.scan(root) == 0


def test_string_literal_does_not_trip(tmp_path):
    root = _write(tmp_path, 'def msg : String := "sorry: not a real hole, also admit"\n')
    assert sorry_scan.scan(root) == 0


def test_char_literal_quote_does_not_trip(tmp_path):
    # The char literal '"' must be handled specially so it does NOT open a string
    # that would then swallow a following real `sorry`.
    root = _write(tmp_path, "def q : Char := '\"'\n"
                            "theorem foo : True := sorry\n")
    # The real `sorry` after the char literal MUST still be counted.
    assert sorry_scan.scan(root) == 1


# --- MUST trip: a real, live token ---

def test_real_sorry_trips(tmp_path):
    root = _write(tmp_path, "theorem foo : True := sorry\n")
    assert sorry_scan.scan(root) == 1


def test_real_admit_trips(tmp_path):
    root = _write(tmp_path, "theorem foo : True := by admit\n")
    assert sorry_scan.scan(root) == 1


def test_both_tokens_counted(tmp_path):
    root = _write(tmp_path, "theorem a : True := sorry\n"
                            "theorem b : True := by admit\n")
    assert sorry_scan.scan(root) == 2


# --- ZT-P2-3: sorryAx, the constant a `sorry` elaborates to ---

def test_sorry_ax_trips(tmp_path):
    # THE regression this hardening exists for: `\bsorry\b` cannot match `sorryAx`
    # (`A` is a word char), so the pre-fix scanner reported 0 here.
    root = _write(tmp_path, "theorem foo : True := sorryAx True false\n")
    assert sorry_scan.scan(root) == 1


def test_sorry_ax_at_sign_prefixed_trips(tmp_path):
    # `@sorryAx` (explicit-argument form) is how it actually shows up in a term.
    root = _write(tmp_path, "theorem foo : True := @sorryAx True false\n")
    assert sorry_scan.scan(root) == 1


def test_sorry_ax_namespaced_trips(tmp_path):
    root = _write(tmp_path, "theorem foo : True := Lean.sorryAx True\n")
    assert sorry_scan.scan(root) == 1


def test_sorry_ax_reported_by_its_own_name(tmp_path):
    # The alternation must prefer the LONGER name so the stderr report is honest.
    findings = sorry_scan.scan_text("theorem foo : True := sorryAx True false\n")
    assert [f.text for f in findings] == ["sorryAx"]


def test_sorry_ax_in_comment_does_not_trip(tmp_path):
    # The real tree mentions `sorryAx` in prose all over Audit.lean.
    root = _write(tmp_path, "-- All expect only the standard axioms (no `sorryAx`):\n"
                            "/- also no sorryAx here -/\n"
                            "theorem foo : True := trivial\n")
    assert sorry_scan.scan(root) == 0


# --- ZT-P2-3: native_decide (pulls the Lean.ofReduceBool axiom) ---

def test_native_decide_trips(tmp_path):
    root = _write(tmp_path, "example : (2 : Nat) + 2 = 4 := by native_decide\n")
    assert sorry_scan.scan(root) == 1


def test_native_decide_in_comment_does_not_trip(tmp_path):
    # The real tree advertises "no `native_decide`" in two module docstrings.
    root = _write(tmp_path, "/-- machine-checked, no `native_decide` -/\n"
                            "theorem foo : True := trivial\n")
    assert sorry_scan.scan(root) == 0


def test_plain_decide_does_not_trip(tmp_path):
    # `decide` is kernel-checked and legitimate; only the NATIVE variant is a risk.
    root = _write(tmp_path, "example : (2 : Nat) + 2 = 4 := by decide\n")
    assert sorry_scan.scan(root) == 0


# --- ZT-P2-3: custom axiom DECLARATIONS ---

def test_axiom_declaration_trips(tmp_path):
    root = _write(tmp_path, "axiom cheat : ∀ p : Prop, p\n")
    assert sorry_scan.scan(root) == 1


def test_axiom_declaration_reported_as_axiom_kind(tmp_path):
    findings = sorry_scan.scan_text("axiom cheat : ∀ p : Prop, p\n")
    assert [f.kind for f in findings] == ["axiom"]


def test_indented_and_modified_axiom_declarations_trip(tmp_path):
    root = _write(tmp_path,
                  "  axiom a1 : True\n"
                  "private axiom a2 : True\n"
                  "noncomputable axiom a3 : True\n"
                  "@[simp] axiom a4 : True\n")
    assert sorry_scan.scan(root) == 4


def test_print_axioms_command_does_not_trip(tmp_path):
    # The whole point of the anchoring: Audit.lean is 460 of these lines
    # (measured 2026-07-29; `verify.sh`'s EXPECTED_MIN_AUDITS floor).
    root = _write(tmp_path, "#print axioms graph_correct\n"
                            "#print axioms graph_reached_inv\n")
    assert sorry_scan.scan(root) == 0


def test_axiom_word_in_prose_does_not_trip(tmp_path):
    root = _write(tmp_path, "/-- We use no custom axiom anywhere; see the axiom audit. -/\n"
                            "-- axiom cheat : True   (deliberately commented out)\n"
                            "theorem foo : True := trivial\n")
    assert sorry_scan.scan(root) == 0


def test_axiom_prefixed_identifier_does_not_trip(tmp_path):
    # `axiom` must be followed by whitespace to be a declaration keyword.
    root = _write(tmp_path, "def axiom_free_check : Nat := 0\n"
                            "def axioms_used : Nat := 0\n")
    assert sorry_scan.scan(root) == 0


def test_block_comment_ending_midline_does_not_hide_next_line_axiom(tmp_path):
    # Newlines inside a stripped block comment are preserved, so the `axiom` on the
    # following line is still at a line start for the anchored regex.
    root = _write(tmp_path, "theorem foo : True := /- a\nmulti-line comment\n-/ trivial\n"
                            "axiom cheat : True\n")
    assert sorry_scan.scan(root) == 1


# --- ZT-P2-3: an unterminated string used to silently swallow the rest of a file ---

def test_unterminated_string_is_reported(tmp_path):
    root = _write(tmp_path, 'def msg : String := "oops\n'
                            "theorem foo : True := trivial\n")
    # At minimum the desync itself is a finding — a clean 0 here would be a lie.
    assert sorry_scan.scan(root) >= 1
    kinds = [f.kind for f in sorry_scan.scan_text('def m : String := "oops\n')]
    assert "unterminated-string" in kinds


def test_unterminated_string_does_not_silently_hide_a_sorry(tmp_path):
    # Pre-fix: the stray `"` opened a string that ran to EOF, the trailing `sorry`
    # was invisible, and the scanner printed 0 with exit status 0.
    root = _write(tmp_path, 'def msg : String := "oops\n'
                            "theorem foo : True := sorry\n")
    proc = subprocess.run(
        [sys.executable, sorry_scan.__file__, str(root)],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode != 0
    assert "UNTERMINATED STRING" in proc.stderr


def test_balanced_multiline_string_does_not_trip(tmp_path):
    # A legitimate multi-line string is data, and the `sorry` inside it is not a hole.
    root = _write(tmp_path, 'def msg : String := "line one\nline two sorry\n"\n'
                            "theorem foo : True := trivial\n")
    assert sorry_scan.scan(root) == 0


def test_escaped_quote_in_string_does_not_desync(tmp_path):
    root = _write(tmp_path, 'def msg : String := "a \\" b"\n'
                            "theorem foo : True := trivial\n")
    assert sorry_scan.scan(root) == 0


# --- nested block comments ---

def test_nested_block_comment_does_not_trip(tmp_path):
    root = _write(tmp_path,
                  "/- outer /- inner sorry -/ still commented sorry -/\n"
                  "theorem foo : True := trivial\n")
    assert sorry_scan.scan(root) == 0


def test_nested_block_comment_closes_then_real_sorry_trips(tmp_path):
    # After a properly-balanced nested comment closes, a live sorry must count.
    root = _write(tmp_path,
                  "/- outer /- inner -/ outer again -/\n"
                  "theorem foo : True := sorry\n")
    assert sorry_scan.scan(root) == 1


def test_sorry_as_substring_does_not_trip(tmp_path):
    # `\b...\b` word boundary: `sorryfoo`/`presorry` are identifiers, not the token.
    root = _write(tmp_path, "def sorryish : Nat := 0\n"
                            "def presorry : Nat := 0\n")
    assert sorry_scan.scan(root) == 0


# --- ZT-P2-4: file discovery — the widened root, and the .lake exclusion ---

def test_scans_lean_files_in_root_and_subdirs(tmp_path):
    # verify.sh now points the scan at `formal/lean` (not `formal/lean/ZanzibarProofs`)
    # so the sibling library ROOT `ZanzibarProofs.lean` is covered too.
    (tmp_path / "Lib").mkdir()
    (tmp_path / "Root.lean").write_text("theorem a : True := sorry\n", encoding="utf-8")
    (tmp_path / "Lib" / "Deep.lean").write_text("theorem b : True := by admit\n",
                                                encoding="utf-8")
    files, skipped = sorry_scan.lean_files(tmp_path)
    assert sorted(p.name for p in files) == ["Deep.lean", "Root.lean"]
    assert skipped == 0
    assert sorry_scan.scan(tmp_path) == 2


def test_dot_directories_are_excluded_and_counted(tmp_path):
    # `.lake/**` is vendored mathlib/aesop/batteries — thousands of files, some of
    # which legitimately contain `sorry`. It must never be scanned.
    (tmp_path / ".lake" / "packages" / "mathlib").mkdir(parents=True)
    (tmp_path / ".lake" / "packages" / "mathlib" / "V.lean").write_text(
        "theorem vendored : True := sorry\n", encoding="utf-8")
    (tmp_path / "Mine.lean").write_text("theorem foo : True := trivial\n",
                                        encoding="utf-8")
    files, skipped = sorry_scan.lean_files(tmp_path)
    assert [p.name for p in files] == ["Mine.lean"]
    assert skipped == 1
    assert sorry_scan.scan(tmp_path) == 0


def test_file_root_is_scanned_directly(tmp_path):
    p = tmp_path / "Root.lean"
    p.write_text("theorem a : True := sorry\n", encoding="utf-8")
    assert sorry_scan.scan(p) == 1


# --- the __main__ contract used by verify.sh: prints count, exits nonzero on find ---

def test_main_clean_prints_zero_exits_zero(tmp_path):
    _write(tmp_path, "theorem foo : True := trivial\n")
    proc = subprocess.run(
        [sys.executable, sorry_scan.__file__, str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "0"


def test_main_found_prints_count_exits_nonzero(tmp_path):
    _write(tmp_path, "theorem foo : True := sorry\n")
    proc = subprocess.run(
        [sys.executable, sorry_scan.__file__, str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode != 0
    assert proc.stdout.strip() == "1"


def test_main_min_files_floor_fails_on_shortfall(tmp_path):
    # A clean 0 from a scan that found (almost) nothing is not evidence.
    _write(tmp_path, "theorem foo : True := trivial\n")
    proc = subprocess.run(
        [sys.executable, sorry_scan.__file__, "--min-files", "60", str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode != 0
    assert proc.stdout.strip() == "0"          # zero violations, but coverage short
    assert "COVERAGE FLOOR" in proc.stderr


def test_main_min_files_floor_passes_when_met(tmp_path):
    for k in range(3):
        (tmp_path / f"F{k}.lean").write_text("theorem foo : True := trivial\n",
                                             encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, sorry_scan.__file__, "--min-files=3", str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "0"


def test_main_missing_root_fails_loudly(tmp_path):
    proc = subprocess.run(
        [sys.executable, sorry_scan.__file__, str(tmp_path / "nope")],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode != 0
    assert "scan root does not exist" in proc.stderr


def test_main_reports_scanned_and_skipped_counts(tmp_path):
    (tmp_path / ".lake").mkdir()
    (tmp_path / ".lake" / "V.lean").write_text("theorem v : True := sorry\n",
                                               encoding="utf-8")
    _write(tmp_path, "theorem foo : True := trivial\n")
    proc = subprocess.run(
        [sys.executable, sorry_scan.__file__, str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert "scanned 1 project .lean file(s)" in proc.stderr
    assert "skipped 1 vendored file(s)" in proc.stderr


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
