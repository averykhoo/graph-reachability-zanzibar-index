---
id: TK129
title: docs/README.md sec 8 restates a footgun count that is already wrong
brief: docs/README.md sec 8 restates "the four footguns"; CLAUDE.md has five -- delete the number
pri: LATER
size: S
deps: []
related: []
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-10-07c
moved: 2026-10-07d
updated: 2026-10-07d
closed: 2026-10-07d
---

Item 2 of the 2026-10-07 cross-repo context audit. `docs/README.md` sec 8's table row for
`CLAUDE.md` says "the four footguns", but `CLAUDE.md` lists five. Under this repo's own rule
(delete the number and point at its home), drop the count.

## Traps

## Read first

- [`docs/context-audit-2026-10-07.md`](../docs/context-audit-2026-10-07.md) item 2 (measured 2026-10-07).

## Log

### 2026-10-07d

LANDED (uncommitted, 2026-10-07d): docs/README.md sec 8 CLAUDE.md row now says the standing footguns (listed there, not counted here) -- number deleted, pointer kept. No lint added (not asked; the footgun heading in CLAUDE.md itself still carries its own count). Next: gate, commit, close.

Done 2026-10-07d: docs/README.md sec 8 no longer counts the footguns. Evidence (agent reports, moved-text tables, sabotage sweeps): docs/history/context-caps-housekeeping-2026-10-07.md. Gated with the 2026-10-07d commit.
