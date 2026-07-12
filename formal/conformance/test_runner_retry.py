"""Unit tests for `runner.invoke_zcli`'s transient-init retry (flakiness fix).

The ~120 MB zcli binary intermittently fails to START under Windows resource
pressure — the OS returns `0xC0000142` (`STATUS_DLL_INIT_FAILED`) before any zcli
code runs — when the conformance suite spawns it in rapid succession. `invoke_zcli`
retries ONLY those pre-`main` process-init codes; it never retries zcli's own exit
codes (0-4) nor an in-process crash (e.g. `0xC0000005`), so a real fault still fails
the gate rather than being retried away. These tests drive that logic with a stubbed
`subprocess.run`, so no binary is needed.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from formal.conformance import runner

_DLL_INIT = 3221225794    # 0xC0000142 STATUS_DLL_INIT_FAILED (the observed transient)
_ACCESS_VIOLATION = 3221225477  # 0xC0000005 — an in-process CRASH, must NOT be retried


def _cp(rc: int, out: str = "[]") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["zcli"], returncode=rc, stdout=out, stderr="")


@pytest.fixture
def stub_env(monkeypatch, tmp_path):
    """No real binary, no real sleeping between retries."""
    monkeypatch.setattr(runner, "zcli_path", lambda: tmp_path / "zcli.exe")
    monkeypatch.setattr(runner.time, "sleep", lambda *_a, **_k: None)


def _cleanup(req_path: str) -> None:
    try:
        os.unlink(req_path)
    except OSError:
        pass


def test_retries_transient_then_succeeds(stub_env, monkeypatch):
    seq = [_cp(_DLL_INIT), _cp(_DLL_INIT), _cp(0, "[true]")]
    calls = {"n": 0}

    def fake_run(*_a, **_k):
        i = calls["n"]
        calls["n"] += 1
        return seq[i]

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    proc, req_path = runner.invoke_zcli('{"queries":[]}', "test")
    _cleanup(req_path)
    assert proc.returncode == 0
    assert calls["n"] == 3            # two transient failures, then success


def test_nontransient_returns_immediately(stub_env, monkeypatch):
    calls = {"n": 0}

    def fake_run(*_a, **_k):
        calls["n"] += 1
        return _cp(1)                 # usage/parse error — a real zcli outcome

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    proc, req_path = runner.invoke_zcli('{"queries":[]}', "test")
    _cleanup(req_path)
    assert proc.returncode == 1
    assert calls["n"] == 1            # no retry on a genuine zcli exit code


def test_exhausted_transient_raises(stub_env, monkeypatch):
    calls = {"n": 0}

    def fake_run(*_a, **_k):
        calls["n"] += 1
        return _cp(_DLL_INIT)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="transient init error"):
        runner.invoke_zcli('{"queries":[]}', "test")
    assert calls["n"] == runner._MAX_ATTEMPTS


def test_crash_code_not_retried(stub_env, monkeypatch):
    """An in-process crash (access violation) is NOT a transient init code: it
    returns immediately as a nonzero proc for the caller to fail on. Retrying it
    would mask a real fault — the non-masking guarantee."""
    calls = {"n": 0}

    def fake_run(*_a, **_k):
        calls["n"] += 1
        return _cp(_ACCESS_VIOLATION)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    proc, req_path = runner.invoke_zcli('{"queries":[]}', "test")
    _cleanup(req_path)
    assert proc.returncode == _ACCESS_VIOLATION
    assert calls["n"] == 1
