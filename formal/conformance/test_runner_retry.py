"""Unit tests for `runner.invoke_zcli`'s transient-init retry (flakiness fix).

The ~120 MB zcli binary intermittently fails to START under Windows resource
pressure when the conformance suite spawns it in rapid succession — either the OS
kills the child pre-`main` (`0xC0000142` STATUS_DLL_INIT_FAILED, observed), or
`CreateProcess` itself raises (WinError 1455/1450) before a returncode exists.
`invoke_zcli` retries ONLY those pre-`main` shapes: a listed exit code with EMPTY
stdout+stderr (output proves zcli's own code ran), or a spawn OSError with a
listed winerror. It never retries zcli's own exit codes (0-4), an in-process
crash (e.g. `0xC0000005`), a listed code accompanied by output, or any other
OSError — so a real fault still fails the gate rather than being retried away.
These tests drive that logic with a stubbed `subprocess.run`, so no binary is
needed.
"""

from __future__ import annotations

import subprocess

import pytest

from formal.conformance import runner

_DLL_INIT = 3221225794    # 0xC0000142 STATUS_DLL_INIT_FAILED (the observed transient)
_NO_MEMORY = 3221225495   # 0xC0000017 STATUS_NO_MEMORY (retriable ONLY output-free)
_ACCESS_VIOLATION = 3221225477  # 0xC0000005 — an in-process CRASH, must NOT be retried


def _cp(rc: int, out: str = "", err: str = "") -> subprocess.CompletedProcess:
    # Defaults are output-FREE — the shape of a genuine pre-main init failure
    # (and of most zcli exits in these stubs); pass out/err to model a process
    # that actually printed something.
    return subprocess.CompletedProcess(
        args=["zcli"], returncode=rc, stdout=out, stderr=err)


def _os_err(winerror: int) -> OSError:
    # The 4-arg Windows form: OSError(errno, strerror, filename, winerror).
    return OSError(0, "spawn failure", None, winerror)


@pytest.fixture
def stub_env(monkeypatch, tmp_path):
    """No real binary, no real sleeping between retries."""
    monkeypatch.setattr(runner, "zcli_path", lambda: tmp_path / "zcli.exe")
    monkeypatch.setattr(runner.time, "sleep", lambda *_a, **_k: None)


def _install_run(monkeypatch, *outcomes):
    """Stub `runner.subprocess.run` with a fixed outcome sequence (a
    CompletedProcess is returned, an exception instance is raised); returns the
    call counter so tests can assert how many attempts were made."""
    calls = {"n": 0}

    def fake_run(*_a, **_k):
        out = outcomes[calls["n"]]
        calls["n"] += 1
        if isinstance(out, BaseException):
            raise out
        return out

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    return calls


def test_retries_transient_then_succeeds(stub_env, monkeypatch):
    calls = _install_run(monkeypatch,
                         _cp(_DLL_INIT), _cp(_DLL_INIT), _cp(0, "[true]"))
    proc, req_path = runner.invoke_zcli('{"queries":[]}', "test")
    runner.discard_request(req_path)
    assert proc.returncode == 0
    assert calls["n"] == 3            # two transient failures, then success


def test_nontransient_returns_immediately(stub_env, monkeypatch):
    calls = _install_run(monkeypatch, _cp(1))  # usage/parse — a real zcli outcome
    proc, req_path = runner.invoke_zcli('{"queries":[]}', "test")
    runner.discard_request(req_path)
    assert proc.returncode == 1
    assert calls["n"] == 1            # no retry on a genuine zcli exit code


def test_exhausted_transient_raises(stub_env, monkeypatch):
    calls = _install_run(monkeypatch,
                         *[_cp(_DLL_INIT)] * runner._MAX_ATTEMPTS)
    with pytest.raises(RuntimeError, match="still failing after") as excinfo:
        runner.invoke_zcli('{"queries":[]}', "test")
    assert calls["n"] == runner._MAX_ATTEMPTS
    # invoke_zcli keeps the request file on raise (for a real-run debug); this
    # test must not leak it — recover the path from the message and discard it.
    runner.discard_request(str(excinfo.value).rsplit("request kept at ", 1)[1])


def test_crash_code_not_retried(stub_env, monkeypatch):
    """An in-process crash (access violation) is NOT a transient init code: it
    returns immediately as a nonzero proc for the caller to fail on. Retrying it
    would mask a real fault — the non-masking guarantee."""
    calls = _install_run(monkeypatch, _cp(_ACCESS_VIOLATION))
    proc, req_path = runner.invoke_zcli('{"queries":[]}', "test")
    runner.discard_request(req_path)
    assert proc.returncode == _ACCESS_VIOLATION
    assert calls["n"] == 1


def test_transient_code_with_output_not_retried(stub_env, monkeypatch):
    """A listed init code ACCOMPANIED BY OUTPUT is an in-process fault (a
    pre-main failure dies before any user code could write to the pipes):
    returned immediately for the caller to fail on, never retried — the
    output-empty discriminator half of the non-masking guarantee."""
    calls = _install_run(monkeypatch,
                         _cp(_NO_MEMORY, out="", err="allocation failed"))
    proc, req_path = runner.invoke_zcli('{"queries":[]}', "test")
    runner.discard_request(req_path)
    assert proc.returncode == _NO_MEMORY
    assert calls["n"] == 1


def test_spawn_oserror_retried_then_succeeds(stub_env, monkeypatch):
    """WinError 1455 (paging file too small) from CreateProcess is the same
    resource-pressure class surfacing BEFORE a returncode exists: retried."""
    calls = _install_run(monkeypatch, _os_err(1455), _cp(0, "[true]"))
    proc, req_path = runner.invoke_zcli('{"queries":[]}', "test")
    runner.discard_request(req_path)
    assert proc.returncode == 0
    assert calls["n"] == 2


def test_nontransient_oserror_propagates(stub_env, monkeypatch):
    """Any other OSError (here WinError 2, file not found) is a real
    environment fault: re-raised on the first attempt, never retried."""
    calls = _install_run(monkeypatch, _os_err(2))
    with pytest.raises(OSError):
        runner.invoke_zcli('{"queries":[]}', "test")
    assert calls["n"] == 1
