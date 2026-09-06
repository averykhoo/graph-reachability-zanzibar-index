2026-09-06c — Phase B' DECIDED (user, feedback pass): tree authoritative, `HANDOFF.md` → one-hop note; 5/7 prerequisites LANDED; the cutover commit itself STILL needs an explicit go (`TT-1`).

🟢 Gate: ask `python scripts/gate_status.py` (all ten phases run on the committed tree; re-run `lean` after any `*.md` edit).
★ **Landed with sabotage evidence** (status table atop `docs/tree-sole-authority-spec-2026-08-29.md`; D1–D5 in `docs/tasktool-trial-protocol.md` §6):
`TT-3` `show` renders the Log NEWEST-FIRST (user request — obsolete info sat at the top; file stays append-only; `--section`, `--head`, `SHOW_LOG_HEAD`=5);
`TT-5` `lint` check 13 = `sync --check` drift is a violation; `TT-6` `ack` ADOPTS a `source: hand` task that has a board row (the `2026-09-06b` gap);
`TT-4` `handoff_lint` check 2 falls back to the tree's `pri:` fields when the row table is gone; `TT-7` its 11th check REQUIRES the newest
ledger entry to carry the literal `task lint:` + `read:` lines — a missing receipt reddens `lean`. Prereq 4: `TT-2` retires WITH `sync` at the cutover.
→ **Owed to the user, not the next session:** the `TT-1` go. The cutover is one revertable commit: banner consolidation, `MAX_LINES['HANDOFF.md']` → 60,
Rhythm → `docs/README.md`, retire check 13 / `sync` / `ack` / `source_hash`, `READ_VOCAB` update. Do NOT start it unasked.
⚠ A `close -m "..."` in a double-quoted Bash string with backticks ran them as command substitutions and ate two fragments — single-quote or heredoc.
(!) `t2c` includes `tasks/*.md` — mirror BEFORE the tiles or they strand. `P6` stays `NOW` mechanically.
