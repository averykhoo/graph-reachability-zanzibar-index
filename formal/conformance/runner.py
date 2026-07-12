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
    exe = zcli_path()
    n_queries = len(json.loads(request_json)["queries"])
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        f.write(request_json)
        req_path = f.name
    # zcli emits UTF-8 JSON; without an explicit encoding, text=True decodes
    # with the locale codepage (cp1252 on Windows) — F11.
    proc = subprocess.run([str(exe), req_path], capture_output=True, text=True,
                          encoding="utf-8")
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
    return answers
