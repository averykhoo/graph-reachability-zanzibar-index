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
import time
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

# Windows PROCESS-INITIALIZATION failures that the OS raises BEFORE zcli's own code
# runs — spawning the ~120 MB static binary in rapid succession under memory/desktop-
# heap pressure intermittently trips these. zcli's OWN exit codes are exactly 0-4
# (Cli.lean: 0 answers/state · 1 usage-parse · 2 admission · 3 not-drained · 4 unknown
# mode), so a code below can NEVER be a zcli logic outcome and is safe to retry. An
# IN-process crash (e.g. 0xC0000005 access violation) is deliberately NOT listed: that
# would be a real fault and must still fail the gate, not be retried away.
_TRANSIENT_INIT_RCS = frozenset({
    3221225794,   # 0xC0000142 STATUS_DLL_INIT_FAILED (observed)
    3221225495,   # 0xC0000017 STATUS_NO_MEMORY
})
_MAX_ATTEMPTS = 4          # 1 try + 3 retries
_RETRY_BACKOFF_S = 0.25    # 0.25, 0.5, 1.0s — let the resource pressure subside


class ZcliUnavailable(RuntimeError):
    """The Lean conformance binary is not built."""


def zcli_path() -> Path:
    for name in ("zcli", "zcli.exe"):
        p = _BIN_DIR / name
        if p.exists():
            return p
    raise ZcliUnavailable(
        f"zcli not found under {_BIN_DIR}; run `lake build zcli` in formal/lean")


def invoke_zcli(request_json: str, what: str = "zcli") -> tuple:
    """Write `request_json` to a temp file and run zcli on it, with a hang timeout
    and a bounded retry over transient Windows process-init failures.

    Returns `(completed_process, request_path)` — the CALLER interprets the return
    code (0-4 are zcli's own outcomes) and cleans up `request_path` (keep it on a
    failure you want to debug). Raises `RuntimeError` on timeout or once the
    transient-init retries are exhausted; the request file is kept in that case.
    """
    exe = zcli_path()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        f.write(request_json)
        req_path = f.name
    last = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            # zcli emits UTF-8 JSON; without an explicit encoding, text=True decodes
            # with the locale codepage (cp1252 on Windows) — F11.
            proc = subprocess.run([str(exe), req_path], capture_output=True,
                                  text=True, encoding="utf-8",
                                  timeout=_ZCLI_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"zcli {what} timed out after {_ZCLI_TIMEOUT_S}s "
                f"(possible hang/loop); request kept at {req_path}")
        if proc.returncode not in _TRANSIENT_INIT_RCS:
            return proc, req_path
        last = proc
        if attempt < _MAX_ATTEMPTS:
            time.sleep(_RETRY_BACKOFF_S * (2 ** (attempt - 1)))
    raise RuntimeError(
        f"zcli {what} failed with transient init error "
        f"rc={last.returncode} (0x{last.returncode & 0xFFFFFFFF:08X}) after "
        f"{_MAX_ATTEMPTS} attempts — Windows could not initialize the process "
        f"(resource pressure from rapid large-binary spawns); "
        f"request kept at {req_path}")


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
    n_queries = len(json.loads(request_json)["queries"])
    proc, req_path = invoke_zcli(request_json, "spec/graph")
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
    proc, req_path = invoke_zcli(request_json, "graph-state")
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
