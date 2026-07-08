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
    """Feed a JSON request to `zcli` and parse its `[bool, ...]` answer array."""
    exe = zcli_path()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        f.write(request_json)
        req_path = f.name
    try:
        proc = subprocess.run([str(exe), req_path], capture_output=True, text=True)
    finally:
        os.unlink(req_path)
    if proc.returncode != 0:
        raise RuntimeError(f"zcli failed (rc={proc.returncode}): {proc.stderr.strip()}")
    return json.loads(proc.stdout.strip())
