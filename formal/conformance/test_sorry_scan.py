"""Unit tests for the extracted sorry/admit scanner (formal/conformance/sorry_scan.py).

The scanner used to live as an inline heredoc in formal/verify.sh where its tricky
comment/string/char-literal handling was untested. These tests pin exactly the cases
that make it subtle: a `sorry` appearing inside a line comment, a block comment, a
string literal, or a char literal must NOT be counted; a real top-level `sorry` or
`admit` MUST be counted; nested block comments are handled.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from formal.conformance import sorry_scan


def _write(tmp_path, text: str):
    p = tmp_path / "T.lean"
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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
