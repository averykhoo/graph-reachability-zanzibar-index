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
moved: 2026-10-08
updated: 2026-10-08
closed:
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
