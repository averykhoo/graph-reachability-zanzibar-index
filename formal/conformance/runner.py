"""Run the Lean `zcli` executable on a JSON request and return its answers.

Locates the built binary under `formal/lean/.lake/build/bin/`. Skips (raises
`ZcliUnavailable`) if the binary has not been built, so the conformance tests can
xfail/skip cleanly in an environment without the Lean toolchain.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BIN_DIR = _REPO_ROOT / "formal" / "lean" / ".lake" / "build" / "bin"

# Guard against a hung/looping zcli wedging the whole suite forever (F17). A single
# request is tiny — 120s is generously above any healthy run and only fires on a
# genuine hang.
_ZCLI_TIMEOUT_S = 120

# In-process memo caches keyed on the EXACT request JSON string, so a test that
# re-issues an identical (schema, tuples, queries[, mode]) request within a session
# reuses the prior zcli result instead of re-spawning the binary (F17). Keying on
# request content — the JSON string carries the mode field — keeps it correct: two
# different requests never share a cache slot. Kept per-parser (spec vs state) since
# their return shapes differ.
_SPEC_CACHE: dict[str, list[bool]] = {}
_STATE_CACHE: dict[str, dict] = {}


class ZcliUnavailable(RuntimeError):
    """The Lean conformance binary is not built."""


def zcli_path() -> Path:
    for name in ("zcli", "zcli.exe"):
        p = _BIN_DIR / name
        if p.exists():
            return p
    raise ZcliUnavailable(
        f"zcli not found under {_BIN_DIR}; run `lake build zcli` in formal/lean")


def run_spec(request_json: str) -> list[bool]:
    """Feed a JSON request to `zcli` (spec OR graph mode — the request's `mode`
    field decides) and parse its `[bool, ...]` answer array.

    Asserts one answer per query (F4): a short (or long) answer array means the
    spec and the harness disagree about what was asked — comparing positionally
    after that would misattribute answers to queries, so fail loudly here
    instead of with an IndexError (or worse, a silent wrong-query comparison)
    in the caller. On any failure the request file is kept for debugging.
    """
    cached = _SPEC_CACHE.get(request_json)
    if cached is not None:
        return cached
    exe = zcli_path()
    n_queries = len(json.loads(request_json)["queries"])
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        f.write(request_json)
        req_path = f.name
    # zcli emits UTF-8 JSON; without an explicit encoding, text=True decodes
    # with the locale codepage (cp1252 on Windows) — F11.
    try:
        proc = subprocess.run([str(exe), req_path], capture_output=True, text=True,
                              encoding="utf-8", timeout=_ZCLI_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"zcli timed out after {_ZCLI_TIMEOUT_S}s (possible hang/loop); "
            f"request kept at {req_path}")
    if proc.returncode != 0:
        raise RuntimeError(
            f"zcli failed (rc={proc.returncode}): {proc.stderr.strip()} "
            f"(request kept at {req_path})")
    answers = json.loads(proc.stdout.strip())
    if not isinstance(answers, list) or len(answers) != n_queries:
        got = len(answers) if isinstance(answers, list) else f"non-list {answers!r}"
        raise AssertionError(
            f"SPEC/HARNESS MISALIGNMENT: zcli returned {got} answers for "
            f"{n_queries} queries — the spec and the harness disagree about the "
            f"request; positional comparison would be garbage. "
            f"Request kept at {req_path}")
    try:
        os.unlink(req_path)        # best-effort cleanup; never fail a green run
    except OSError:
        pass
    _SPEC_CACHE[request_json] = answers
    return answers


def run_state(request_json: str) -> dict:
    """Feed a `mode="graph-state"` request to `zcli` and parse the canonical
    state object `{"edges": [...], "residues": [...]}` it prints (Cli.lean
    header). No per-query answer-count assertion applies — this mode ignores
    queries. On any failure the request file is kept for debugging."""
    cached = _STATE_CACHE.get(request_json)
    if cached is not None:
        return cached
    exe = zcli_path()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        f.write(request_json)
        req_path = f.name
    try:
        proc = subprocess.run([str(exe), req_path], capture_output=True, text=True,
                              encoding="utf-8", timeout=_ZCLI_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"zcli graph-state timed out after {_ZCLI_TIMEOUT_S}s "
            f"(possible hang/loop); request kept at {req_path}")
    if proc.returncode != 0:
        raise RuntimeError(
            f"zcli graph-state failed (rc={proc.returncode}): "
            f"{proc.stderr.strip()} (request kept at {req_path})")
    state = json.loads(proc.stdout.strip())
    if not isinstance(state, dict) or set(state) != {"edges", "residues"}:
        raise AssertionError(
            f"graph-state output shape unexpected: keys="
            f"{sorted(state) if isinstance(state, dict) else type(state)} "
            f"(request kept at {req_path})")
    try:
        os.unlink(req_path)
    except OSError:
        pass
    _STATE_CACHE[request_json] = state
    return state
