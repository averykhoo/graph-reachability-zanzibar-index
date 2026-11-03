"""context-engine CE-167 (2026-11-03): handoff_lint's task-tree readers on the record engine's records.

The engine owns tasks/ since its adoption. A record carries its task.py id in `aliases:` (`TK185` on
`TK-185`), and a closed record stays in tasks/ with `state: closed`. So `_tree_ids` must take the alias
(else every ledger citation of an old id is red), and `_tree_open_pris`, `_tree_next_asks` and
`_count_scan_files` must skip a closed record (else every closed item counts against NOW and NEXT, and
every closed body is scanned for restated counts). Each test has its control.

SABOTAGE (run by the CE-167 import script, each restored byte for byte):
  `_aliases` returns [] -> test_an_alias_is_a_known_tree_id red
  `_closed_record` returns False -> test_a_closed_engine_record_is_not_open and its ask and count twins red
"""
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "ce167_handoff_lint", str(REPO_ROOT / "scripts" / "handoff_lint.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HL = _load()

OPEN = ("---\ntype: Task\nid: TK-7\naliases: [TK7]\ntitle: x\npri: NOW\nstate: open\n"
        "created: 2026-11-03\n---\n\nbody\n")
CLOSED = ("---\ntype: Task\nid: TK-8\naliases: [P8]\ntitle: y\npri: NOW\nstate: closed\n"
          "status: deprecated\ncreated: 2026-11-03\n---\n\nbody\n")
ASK = ("---\ntype: Question\nid: ASK-4\ntitle: q\npri: NEXT\nstate: closed\nstatus: deprecated\n"
       "created: 2026-11-03\n---\n\nbody\n")


def _run(root: Path, files: dict, fn):
    (root / "tasks").mkdir()
    for name, text in files.items():
        (root / "tasks" / name).write_bytes(text.encode("utf-8"))
    old = HL.REPO
    HL.REPO = str(root)
    try:
        return fn()
    finally:
        HL.REPO = old


def test_an_alias_is_a_known_tree_id(tmp_path):
    ids = _run(tmp_path, {"TK-7-x.md": OPEN, "TK-8-y.md": CLOSED}, HL._tree_ids)
    assert {"TK-7", "TK7", "TK-8", "P8"} <= ids, ids


def test_an_id_no_record_names_is_still_unknown(tmp_path):
    ids = _run(tmp_path, {"TK-7-x.md": OPEN}, HL._tree_ids)
    assert "P8" not in ids and "TK8" not in ids and "TK7" in ids, ids


def test_a_closed_engine_record_is_not_open(tmp_path):
    pris = _run(tmp_path, {"TK-7-x.md": OPEN, "TK-8-y.md": CLOSED}, HL._tree_open_pris)
    assert pris == [("NOW", "TK-7-x.md")], pris


def test_an_open_engine_record_is_open(tmp_path):
    reopened = CLOSED.replace("state: closed\nstatus: deprecated\n", "state: open\n")
    pris = _run(tmp_path, {"TK-8-y.md": reopened}, HL._tree_open_pris)
    assert pris == [("NOW", "TK-8-y.md")], pris


def test_a_closed_engine_ask_is_not_a_standing_nag(tmp_path):
    assert _run(tmp_path, {"ASK-4-q.md": ASK}, HL._tree_next_asks) == []


def test_an_open_engine_ask_at_next_is_a_standing_nag(tmp_path):
    reopened = ASK.replace("state: closed\nstatus: deprecated\n", "state: open\n")
    assert _run(tmp_path, {"ASK-4-q.md": reopened}, HL._tree_next_asks) == ["ASK-4"]


def test_a_closed_engine_record_is_out_of_the_count_scan(tmp_path):
    files = _run(tmp_path, {"TK-7-x.md": OPEN, "TK-8-y.md": CLOSED}, HL._count_scan_files)
    assert "tasks/TK-7-x.md" in files and "tasks/TK-8-y.md" not in files, files
