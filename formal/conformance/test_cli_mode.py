"""zcli mode-rejection conformance (finding F6).

`decodeMode` + `main`'s dispatch must REJECT an unrecognized `"mode"` rather than
silently answering with the spec: a caller asking for `"graph"` (or a typo, or a
non-string) that got spec answers labeled as graph answers would void the
graph-vs-spec conformance pin. We assert the distinct nonzero exit code (rc 4)
and a stderr message that names the mode, plus that the absent-mode default
(spec, rc 0) is preserved.

Skips cleanly if the Lean `zcli` binary is not built.
"""

from __future__ import annotations

import json
import os

import pytest

from formal.conformance import runner
from formal.conformance.encode import build_request
from tests.oracle import t as mk_tuple

# A minimal valid corpus: one Direct relation, one stored tuple, one query.
_SCHEMA = """
type user
type doc
  define viewer: [user]
"""
_TUPLES = [mk_tuple("...", "user", "alice", "viewer", "doc", "d1")]
_QUERIES = [("...", "user", "alice", "viewer", "doc", "d1")]

# Distinct exit code for an unrecognized mode (Cli.lean rc enumeration).
_RC_UNKNOWN_MODE = 4


def _run_zcli(request_json: str):
    """Invoke the built zcli binary on a request; return the completed process so
    the caller can inspect rc + stderr (runner.run_spec raises on nonzero). Routes
    through runner.invoke_zcli so these spawns share the transient-init retry."""
    proc, req_path = runner.invoke_zcli(request_json, "cli-mode-test")
    try:
        os.unlink(req_path)
    except OSError:
        pass
    return proc


def _require_zcli():
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")


def test_unknown_mode_string_rejected():
    """A recognizable-shape but unrecognized mode string ('graf') is rejected
    with the distinct rc, and stderr names the offending mode."""
    _require_zcli()
    req = build_request(_SCHEMA, _TUPLES, _QUERIES, mode="graf")
    proc = _run_zcli(req)
    assert proc.returncode == _RC_UNKNOWN_MODE, (
        f"expected rc {_RC_UNKNOWN_MODE} for unknown mode, got "
        f"{proc.returncode}; stderr={proc.stderr!r}")
    assert "graf" in proc.stderr, (
        f"stderr should name the rejected mode; got {proc.stderr!r}")
    assert proc.stdout.strip() == "", (
        f"a rejected mode must print no answers; stdout={proc.stdout!r}")


def test_non_string_mode_rejected():
    """A `"mode"` value that is present but not a string (5) is rejected with the
    same distinct rc — it must NOT be silently coerced to spec."""
    _require_zcli()
    req_obj = json.loads(build_request(_SCHEMA, _TUPLES, _QUERIES))
    req_obj["mode"] = 5
    proc = _run_zcli(json.dumps(req_obj))
    assert proc.returncode == _RC_UNKNOWN_MODE, (
        f"expected rc {_RC_UNKNOWN_MODE} for non-string mode, got "
        f"{proc.returncode}; stderr={proc.stderr!r}")
    assert "mode" in proc.stderr, (
        f"stderr should mention the mode error; got {proc.stderr!r}")
    assert proc.stdout.strip() == "", (
        f"a rejected mode must print no answers; stdout={proc.stdout!r}")


def test_absent_mode_defaults_to_spec():
    """No `"mode"` key preserves the spec default: rc 0, one answer per query."""
    _require_zcli()
    req = build_request(_SCHEMA, _TUPLES, _QUERIES)  # no mode key
    proc = _run_zcli(req)
    assert proc.returncode == 0, (
        f"absent mode must default to spec (rc 0), got {proc.returncode}; "
        f"stderr={proc.stderr!r}")
    answers = json.loads(proc.stdout.strip())
    assert answers == [True], f"spec default answer mismatch: {answers!r}"
