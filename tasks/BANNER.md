2026-08-29d — gate green on this tree; ledger `2026-08-29d` (root session-log).

Phase A of `docs/tree-sole-authority-spec-2026-08-29.md` landed: the tool's suite is in
the gate (`tests/test_tasktool.py`), the six A7 footguns are fixed, `brief` and this file
exist. **Question (a) — delete `tasks/` or cut over to it — is still the user's call.**
Phase B (the `HANDOFF.md` stub) is NOT landed and needs an explicit go.

⏰ `TK53`: 15 appends remain. Until they land, deleting `tasks/` loses statements.
⚠ Until Phase B lands, `HANDOFF.md` stays authoritative and the DUAL-UPDATE contract in
`CLAUDE.md` is in force: every board edit gets the mirrored `task.py` op, same `--session`.

Start: `task.py board` → `show <id>` → the item's read-first list. Layout and the rules
this tool cannot enforce: `tasks/README.md`. Gate state: `python scripts/gate_status.py`,
never a line in this file.
