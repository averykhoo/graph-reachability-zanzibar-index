"""TK99 -- the collection floors in `formal/verify.sh` are ratcheted by a tool, not by hand.

`MIN_TESTS_ALL` was raised by hand, and every re-measurement found headroom (tests that
could be deleted with every tile green): 1, 17, 62, 70, 86, 160, and on 2026-10-13
**534** (`MIN_TESTS_ALL=1749` against `pytest tests/ -q --collect-only` -> 2283).
`formal/conformance/doc_counts.py::ratchet_floors` now runs inside
`doc_counts --generate` and raises `MIN_TESTS_ALL` / `MIN_CONF_HEAVY` / `MIN_CONF_REST`
to the live counts with `max(floor, live)` -- never lowering one, the rule
`scripts/task.py::ratchet_min_parsed` already pins for `min_tasks_parsed` -- and DERIVES
`MIN_CONF_ALL` as HEAVY + REST, so verify.sh's identity check holds by construction.
`doc_counts.py::floor_headroom` makes `--check` (verify.sh step 4e) refuse a floor that
sits below its live count by any other route (a hand edit).

Every fixture below is a byte copy of the REAL `formal/verify.sh`, so a reshaped floor
line breaks these tests rather than the ratchet silently matching nothing.

SABOTAGE RECORD (docs/sabotage-procedure.md), each RUN 2026-10-13 on Windows against
`doc_counts.py`, each reverted (byte-compared to a saved copy), literal observed output.
The floors in the messages are verify.sh's on that day (MIN_TESTS_ALL=1749,
MIN_CONF_ALL=1093=135+958):
  (1) `"MIN_TESTS_ALL": live_tests` instead of `max(old, live)` (seals a breach):
        2 failed, 10 passed -- test_a_breach_is_left_alone_and_the_file_untouched
        `AssertionError: assert [('MIN_TESTS_..., 1749, 1700)] == []`, and
        test_a_mixed_run_raises_only_the_floors_with_headroom.
  (2) the "split the growth" design, `MIN_CONF_ALL := max(ALL, live_heavy + live_rest)`
      then `REST := ALL - HEAVY`:
        2 failed, 10 passed -- test_tests_moving_from_rest_into_heavy_never_lower_rest
        `assert 953 == 958`, and test_a_mixed_run_raises_only_the_floors_with_headroom
        `('MIN_CONF_REST', 958, 957) != ('MIN_CONF_ALL', 1093, 1096)`.
  (3) `verify_sh.write_text(text, encoding="utf-8")` instead of `write_bytes`:
        1 failed, 11 passed -- test_headroom_is_closed_and_the_identity_holds
        `AssertionError: the ratchet must change four integers and nothing else`
        `assert b'#!/usr/bin/...r.tsv)"\\r\\r\\n' == b'#!/usr/bin/...ger.tsv)"\\r\\n'`.
        Windows-only by nature: on an LF checkout write_text changes nothing.
  (4) `env = dict(os.environ)` in `_collect` (no scrub):
        1 failed, 11 passed -- test_collect_scrubs_the_env_vars_that_add_tests
        `AssertionError: assert 'ZANZIBAR_TEST_DSN' not in {'AI_AGENT': ...`.
  (5) `headroom = []` in `main`'s `--check` path (the refusal deleted):
        1 failed, 11 passed -- test_check_refuses_a_hand_lowered_floor `assert 0 == 1`
        (stdout: `FINAL_REVIEW.md counts: 30 conf / 50 tests ... all match the tree`).
"""
from __future__ import annotations

import pathlib
import re
import types

import pytest

from formal.conformance import doc_counts

REAL_VERIFY_SH = doc_counts.REPO / "formal" / "verify.sh"


def _copy(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "verify.sh"
    p.write_bytes(REAL_VERIFY_SH.read_bytes())
    return p


def _floors(p: pathlib.Path) -> dict[str, int]:
    return {n: doc_counts._verify_sh_floor(n, p) for n in doc_counts.RATCHETED_FLOORS}


def _sub(raw: bytes, values: dict[str, int]) -> bytes:
    for name, v in values.items():
        raw, n = re.subn(rb"(?m)^(" + name.encode() + rb"=)\d+", rb"\g<1>" + str(v).encode(), raw)
        assert n == 1, name
    return raw


def test_the_fixture_is_the_real_shape():
    """Instrument control: the real verify.sh carries each floor exactly once, the
    identity holds, and HEAVY_CONF parses -- otherwise every test below is vacuous."""
    text = REAL_VERIFY_SH.read_text(encoding="utf-8")
    f = _floors(REAL_VERIFY_SH)
    assert f["MIN_CONF_HEAVY"] + f["MIN_CONF_REST"] == f["MIN_CONF_ALL"]
    for n in doc_counts.RATCHETED_FLOORS:
        doc_counts._floor_spans(text, n)  # raises unless exactly one
    assert doc_counts.heavy_conf_name(text) == "test_conformance_remove.py"


def test_headroom_is_closed_and_the_identity_holds(tmp_path):
    p = _copy(tmp_path)
    before = p.read_bytes()
    f = _floors(p)
    moved = doc_counts.ratchet_floors(
        p, f["MIN_TESTS_ALL"] + 7, f["MIN_CONF_HEAVY"] + 2, f["MIN_CONF_REST"] + 5)
    want = {"MIN_TESTS_ALL": f["MIN_TESTS_ALL"] + 7,
            "MIN_CONF_HEAVY": f["MIN_CONF_HEAVY"] + 2,
            "MIN_CONF_REST": f["MIN_CONF_REST"] + 5,
            "MIN_CONF_ALL": f["MIN_CONF_ALL"] + 7}
    assert moved == [(n, f[n], want[n]) for n in doc_counts.RATCHETED_FLOORS]
    assert _floors(p) == want
    assert want["MIN_CONF_HEAVY"] + want["MIN_CONF_REST"] == want["MIN_CONF_ALL"]
    assert p.read_bytes() == _sub(before, want), (
        "the ratchet must change four integers and nothing else")
    assert p.read_bytes().count(b"\r\n") == before.count(b"\r\n")


def test_zero_headroom_is_a_byte_identical_noop(tmp_path):
    p = _copy(tmp_path)
    before = p.read_bytes()
    f = _floors(p)
    assert doc_counts.ratchet_floors(
        p, f["MIN_TESTS_ALL"], f["MIN_CONF_HEAVY"], f["MIN_CONF_REST"]) == []
    assert p.read_bytes() == before


def test_a_breach_is_left_alone_and_the_file_untouched(tmp_path):
    """Live BELOW every floor (tests were deleted): nothing moves, so the gate's
    collection floor stays red. This is the half that makes it a ratchet."""
    p = _copy(tmp_path)
    before = p.read_bytes()
    f = _floors(p)
    moved = doc_counts.ratchet_floors(
        p, f["MIN_TESTS_ALL"] - 49, f["MIN_CONF_HEAVY"] - 1, f["MIN_CONF_REST"] - 3)
    assert moved == []
    assert p.read_bytes() == before


def test_a_mixed_run_raises_only_the_floors_with_headroom(tmp_path):
    p = _copy(tmp_path)
    f = _floors(p)
    moved = doc_counts.ratchet_floors(
        p, f["MIN_TESTS_ALL"] - 10, f["MIN_CONF_HEAVY"] + 3, f["MIN_CONF_REST"] - 1)
    assert moved == [("MIN_CONF_HEAVY", f["MIN_CONF_HEAVY"], f["MIN_CONF_HEAVY"] + 3),
                     ("MIN_CONF_ALL", f["MIN_CONF_ALL"], f["MIN_CONF_ALL"] + 3)]
    assert _floors(p)["MIN_TESTS_ALL"] == f["MIN_TESTS_ALL"]
    assert _floors(p)["MIN_CONF_REST"] == f["MIN_CONF_REST"]


def test_tests_moving_from_rest_into_heavy_never_lower_rest(tmp_path):
    """The HEAVY/REST decision. Five tests leave REST and five land in HEAVY: the
    directory total is flat. A "split the growth" ratchet (ALL := max(ALL, live_all),
    REST := ALL - HEAVY) would LOWER the REST floor by five. Per-component maxima keep
    REST where it was and lift ALL above the live total -- the gate goes red, which is
    correct: REST lost five tests."""
    p = _copy(tmp_path)
    f = _floors(p)
    doc_counts.ratchet_floors(
        p, f["MIN_TESTS_ALL"], f["MIN_CONF_HEAVY"] + 5, f["MIN_CONF_REST"] - 5)
    g = _floors(p)
    assert g["MIN_CONF_REST"] == f["MIN_CONF_REST"]
    assert g["MIN_CONF_HEAVY"] == f["MIN_CONF_HEAVY"] + 5
    assert g["MIN_CONF_ALL"] == f["MIN_CONF_ALL"] + 5
    assert g["MIN_CONF_HEAVY"] + g["MIN_CONF_REST"] == g["MIN_CONF_ALL"]


def test_refuses_a_file_whose_identity_is_already_broken(tmp_path):
    p = _copy(tmp_path)
    f = _floors(p)
    p.write_bytes(_sub(p.read_bytes(), {"MIN_CONF_ALL": f["MIN_CONF_ALL"] + 1}))
    before = p.read_bytes()
    with pytest.raises(SystemExit, match="already violate"):
        doc_counts.ratchet_floors(p, 10**6, 10**6, 10**6)
    assert p.read_bytes() == before


def test_refuses_a_floor_assigned_twice(tmp_path):
    p = _copy(tmp_path)
    p.write_bytes(p.read_bytes() + b"MIN_TESTS_ALL=1\n")
    before = p.read_bytes()
    with pytest.raises(SystemExit, match="exactly one `MIN_TESTS_ALL=<int>`"):
        doc_counts.ratchet_floors(p, 10**6, 10**6, 10**6)
    assert p.read_bytes() == before


def _fake_measure(**over) -> dict:
    m = {
        "proj": {"corpora": 1, "raw": 1, "P1": 0, "P2": 0, "compared": 1,
                 "nodes": 1, "residues": 0},
        "conf_total": 30, "tests_total": 50, "repo_total": 80,
        "heavy_conf": "test_conformance_remove.py",
        "conf_heavy_live": 10, "conf_rest_live": 20,
        "per_file": {"test_conformance_remove.py": 10, "test_x.py": 20},
        "differential_files": 2, "differential_tests": 30,
        "tooling_files": 0, "tooling_tests": 0,
        "audits": 1, "pinned_audits": 1, "definition_rows": 1, "definition_decls": 1,
        "anchors": 1, "anchors_py": 1, "anchors_lean": 0,
        "schemas": 1, "graph_fragment": 1, "ttu_userset": 0, "self_referential": 0,
        "multi_stratum": 0, "spec_scope": 1,
        "min_conf_all": 30, "min_conf_heavy": 10, "min_conf_rest": 20,
        "min_tests_all": 50, "expected_min_audits": 1,
    }
    m.update(over)
    return m


def test_floor_headroom_names_every_floor_below_live():
    assert doc_counts.floor_headroom(_fake_measure()) == []
    # A floor ABOVE live is a breach, reported by run_conf's collection floor, not here.
    assert doc_counts.floor_headroom(_fake_measure(min_tests_all=51)) == []
    got = doc_counts.floor_headroom(_fake_measure(
        min_tests_all=40, min_conf_heavy=9, min_conf_rest=18, min_conf_all=27))
    assert [g.split("=")[0] for g in got] == list(doc_counts.RATCHETED_FLOORS)
    assert got[0].startswith("MIN_TESTS_ALL=40 but tests/ collects 50: 10 test(s)")


def test_check_refuses_a_hand_lowered_floor(tmp_path, monkeypatch, capsys):
    """A hand-lowered floor plus a regenerated block passes the block comparison (the
    block renders whatever the floor says). `--check` must still go red."""
    m = _fake_measure(min_tests_all=40)
    target = tmp_path / "FINAL_REVIEW.md"
    target.write_text("head\n" + doc_counts.render(m) + "\ntail\n", encoding="utf-8")
    monkeypatch.setattr(doc_counts, "TARGET", target)
    monkeypatch.setattr(doc_counts, "measure", lambda: dict(m))
    rc = doc_counts.main(["--check"])
    out = capsys.readouterr().out
    assert rc == 1, out
    assert "sit BELOW the live counts (TK99)" in out
    assert "MIN_TESTS_ALL=40 but tests/ collects 50" in out


def test_generate_ratchets_verify_sh_then_renders_the_ratcheted_floors(
        tmp_path, monkeypatch, capsys):
    p = _copy(tmp_path)
    f = _floors(p)
    live = dict(tests_total=f["MIN_TESTS_ALL"] + 11,
                conf_heavy_live=f["MIN_CONF_HEAVY"],
                conf_rest_live=f["MIN_CONF_REST"] + 4)
    m = _fake_measure(min_tests_all=f["MIN_TESTS_ALL"], min_conf_all=f["MIN_CONF_ALL"],
                      min_conf_heavy=f["MIN_CONF_HEAVY"], min_conf_rest=f["MIN_CONF_REST"],
                      conf_total=f["MIN_CONF_ALL"] + 4, **live)
    target = tmp_path / "FINAL_REVIEW.md"
    target.write_text(f"head\n{doc_counts.BEGIN}\nold\n{doc_counts.END}\ntail\n",
                      encoding="utf-8")
    monkeypatch.setattr(doc_counts, "TARGET", target)
    monkeypatch.setattr(doc_counts, "VERIFY_SH", p)
    monkeypatch.setattr(doc_counts, "measure", lambda: dict(m))
    assert doc_counts.main(["--generate"]) == 0
    out = capsys.readouterr().out
    assert (f"ratcheted MIN_TESTS_ALL {f['MIN_TESTS_ALL']} -> {f['MIN_TESTS_ALL'] + 11}"
            in out), out
    g = _floors(p)
    assert g == {"MIN_TESTS_ALL": f["MIN_TESTS_ALL"] + 11,
                 "MIN_CONF_HEAVY": f["MIN_CONF_HEAVY"],
                 "MIN_CONF_REST": f["MIN_CONF_REST"] + 4,
                 "MIN_CONF_ALL": f["MIN_CONF_ALL"] + 4}
    block = target.read_text(encoding="utf-8")
    assert (f"`MIN_CONF_ALL`={g['MIN_CONF_ALL']} "
            f"(={g['MIN_CONF_HEAVY']}+{g['MIN_CONF_REST']}), "
            f"`MIN_TESTS_ALL`={g['MIN_TESTS_ALL']}") in block
    # And the regenerated tree now has zero headroom.
    m2 = dict(m, **{n.lower(): v for n, v in g.items()})
    assert doc_counts.floor_headroom(m2) == []


def test_collect_scrubs_the_env_vars_that_add_tests(monkeypatch):
    """`tests/conftest.py` collects `test_postgres_ha.py` only under a DSN. A
    `--generate` from a shell with one exported must not ratchet past the default gate."""
    monkeypatch.setenv("ZANZIBAR_TEST_DSN", "postgresql://x")
    monkeypatch.setenv("ZANZIBAR_PG_REQUIRED", "1")
    seen = {}

    def fake_run(cmd, **kw):
        seen.update(kw["env"])
        return types.SimpleNamespace(stdout="7 tests collected in 0.1s", stderr="")

    monkeypatch.setattr(doc_counts.subprocess, "run", fake_run)
    assert doc_counts._collect("tests/") == 7
    assert "ZANZIBAR_TEST_DSN" not in seen
    assert "ZANZIBAR_PG_REQUIRED" not in seen
    assert "PATH" in seen or "Path" in seen  # control: the rest of the env is passed
