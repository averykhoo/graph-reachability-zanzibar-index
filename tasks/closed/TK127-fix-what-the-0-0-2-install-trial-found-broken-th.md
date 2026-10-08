---
id: TK127
title: fix what the 0.0.2 install trial found broken, then release 0.0.3
brief: user 2026-10-07: fix everything the 0.0.2 install trial found BROKEN (TK124/125/126), then release 0.0.3
pri: NOW
size: L
deps: []
related: [TK124, TK125, TK126, TK123]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-10-07b
moved: 2026-10-08b
updated: 2026-10-08b
closed: 2026-10-08b
---

The user's instruction (2026-10-07): fix everything the fresh-user install trial of the
PUBLISHED `zanzibar-index` 0.0.2 found BROKEN, then release **0.0.3**. The three BROKEN items
are children of this row. Each was re-run first-hand against `src/` on 2026-10-07 and
reproduced:

- `TK126` (L): the graph index refuses `x from parent` whenever `x` names a boolean relation on
  ANY type. That is the ordinary OpenFGA idiom (every type has its own `viewer`), and the set
  engine accepts it. A second form crashes BOTH backends with an internal-object `ValueError`.
  This is the hard one and needs a design decision first. Record it on the row.
- `TK124` (S): `schema=""` is persisted write-once and bricks the store id.
- `TK125` (S): `add_tuple(None, ...)` leaks a raw `IntegrityError`.

Naming and ergonomics (`connectedstore`, `lookup` ids, docstrings, `__all__`) are deliberately
NOT in scope. The user parked them in `TK123` for later.

**Suggested order:** TK125, then TK124 (small, independent), then TK126. Then bump
`src/zanzibar/__init__.py::__version__` and `CHANGELOG.md` to 0.0.3, run the full gate, and
commit. Release only on the user's word.

**The release procedure is now standing** (`~/.claude/CLAUDE.md` sec "Git: gate, commit,
push"; recipe in `.github/workflows/publish.yml`'s header):
1. `git fetch`, and confirm nothing is on `origin/master` that is not in HEAD.
2. `git push origin master`, on its own.
3. Tag `v0.0.3` and push the tag separately.
4. Run a CI-babysitter subagent through the upload.
5. Confirm the version is live on PyPI.
6. Run a fresh-user install-trial subagent in a blank conda env.

## Traps

- (!) **Another Claude session works in this repo concurrently** (2026-10-07: it committed
  `e8b340b` on top of the 0.0.2 commit, unpushed). Commit by path (`git commit -o <paths>`),
  never `git add -A`, never `git stash`, and re-run `git status` / `git log -3` right before
  committing (`~/.claude/CLAUDE.md` sec "Concurrent sessions").
- (!) **`tasks/*.md` and `HANDOFF.md` are inside the tiles' tree id (`t2c`).** A row edit
  after the tiles have run stales them, so write the records BEFORE the gate, then run `lean`
  last.
- (!) **A rebase re-checks-out files CRLF and voids the content-addressed gate verdict.**
  2026-10-07 paid a full re-gate for a README-only remote commit. Fetch BEFORE gating.
- (!) A new schema refusal needs a `# REFUSED SHAPE` / `# WHY` / `# INSTEAD` block in BOTH
  parsers (`tests/test_refused_shape_comments.py`, `tests/test_p23_parser_refusal_parity.py`).

## Read first

- [`docs/pypi-trial-0.0.2-2026-10-07.md`](../docs/pypi-trial-0.0.2-2026-10-07.md) -- the trial,
  each finding labelled CONFIRMED / AGENT.
- [`docs/pypi-readiness-2026-10-07.md`](../docs/pypi-readiness-2026-10-07.md) sec 0 -- how the
  release pipeline was built and what its first runs showed.

## Log

### 2026-10-08

All three children closed 2026-10-08 (TK124, TK125, TK126) plus the review follow-ups (relationless schema, store_id). Version 0.0.3 + CHANGELOG. Evidence: docs/history/tk127-fixes-2026-10-08.md; session-log 2026-10-08 (first-hand repros, PG leg, 6-seed fuzz). Next: full gate, commit, then the release procedure above.

### 2026-10-08b

Release progress 2026-10-08b. LANDED: fetch showed nothing on origin/master missing from HEAD; gate COVERED on 7449537 (gate_status.py); `git push origin master` done (578d5f4..7449537). CI babysitter verdict: gate.yml run 37705328041 on 7449537 SUCCESS, all 10 jobs green (lean, tests 1-4, conf 1-5) (AGENT, haiku babysitter). NOT DONE: tag v0.0.3. The tag create+push was refused by the Claude Code auto-mode classifier ("Create Public Surface") and the session did not work around it; the tag exists neither locally nor on origin (the refused command was atomic). The user pushes the tag, or grants a permission rule for it.

NEW (user instruction 2026-10-08b): the install trial must EXERCISE CODE PATHS quickly (seconds to a minute, no fuzz), not only read docs. Added `scripts/installed_smoke.py` (tracked; stdlib + sqlmodel + zanzibar only). It refuses to run unless `zanzibar` imports from site-packages (`--allow-checkout` overrides, for developing it), and asserts `--version`. Covers: README quickstart + reopen; a seeded 120-op differential (adds/removes) on a schema with nested groups, a folder TTU chain, `and`, `but not`, `[user:*]` and the per-type `viewer from parent` idiom, then the same on TK126's "second form" (TTU arm inside `but not`); at 3 checkpoints the full 198-cell check grid must agree across the sync graph index (paranoia=residue), two standalone SetEngines (RoaringSets, PySets), the async store's tokened pre-catch_up reads, and the async index after catch_up; hand-written expectations (nested-group revoke, ban/un-ban, `and`, wildcard), lookup/lookup_reverse/watermark; bad input (TK124 empty schema refused and the id stays usable, TK125 None predicate -> AdmissionRejected, bad identifier, undeclared relation, wrong subject type, SchemaMismatch on reopen, ZANZIBAR_MAX_CLOSURE_FANOUT=3 -> ClosureFanoutExceeded landing nowhere).

First-hand runs against src/ with --allow-checkout (2026-10-08b): `-- 67 checks passed, 0 failed, 21.7s`, exit 0. Guard: without --allow-checkout it prints `FAIL  zanzibar was not imported from site-packages; ...`, exit 1. SABOTAGE: SetEngine.check monkeypatched to invert one cell (u3 reader doc:d2), --ops 60 -> red at every checkpoint on both schemas, e.g. `FAIL  main op 20: graph index vs set engine (roaring) disagree: ["('u3', 'reader', 'doc', 'd2'): False vs True"]`, `op   20: 2 live tuples, 5/198 cells True, MISMATCH`, exit 1. Correction found while writing it: TK126's second form is SERVED in 0.0.3 (design (a)), not refused; the smoke pins agreement on it rather than a refusal.

NEXT ACTION: once v0.0.3 is pushed and the publish run is green and pypi.org/pypi/zanzibar-index/0.0.3/json is 200, the install-trial subagent copies scripts/installed_smoke.py OUT of the checkout and runs it with the blank env's python (`--version 0.0.3`) in addition to the README/first-hour trial; any FAIL line is BROKEN. Then close TK127.

Released 2026-10-08b. Tag v0.0.3 (annotated) on 7449537, pushed on the user's word. publish.yml run 37707383937: SUCCESS, 17/17 jobs (validate tag, 5 fuzz sweeps, lean, tests 1-4, conf 1-5, publish) (AGENT babysitter). PyPI FIRST-HAND: https://pypi.org/pypi/zanzibar-index/0.0.3/json -> 200, version 0.0.3, requires_python >=3.13, files zanzibar_index-0.0.3-py3-none-any.whl + zanzibar_index-0.0.3.tar.gz. Install trial (AGENT, blank conda env py3.13.16, env removed): scripts/installed_smoke.py against the installed wheel -> `-- 67 checks passed, 0 failed, 18.8s`, rc 0, imported from site-packages; all three 0.0.2 BROKEN items WORK. One new BROKEN (reopen with schema= compares bytes) CONFIRMED first-hand -> TK136; README gaps -> TK135; ergonomics -> logged on TK123. Transcript: docs/pypi-trial-0.0.3-2026-10-08.md.
