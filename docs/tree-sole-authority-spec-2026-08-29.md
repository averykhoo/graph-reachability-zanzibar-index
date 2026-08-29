# Tree-as-sole-authority — build & test spec

**ACTIVE-PLAN 2026-08-29 — execution spec for an implementing agent. Mark FROZEN when
landed or abandoned; corrections append dated at the top.**

> **PHASE A IS LANDED — 2026-08-29d, commit `379dd60`, ten gate phases green.** Section 1
> (A1–A5) below is still written in the undone imperative; **do not re-execute it.** Read
> it as the record of what was decided, and ledger `2026-08-29d` as the record of what
> happened and where it differed. Notable differences from this spec as written:
> A2 item 5 was **already correct** and needed a pin rather than a fix (and its
> `list --parent` prefix half is explicitly NOT scheduled); `MIN_TESTS_ALL` went 943 →
> **1035**, not the figure any estimate here implied; a twelfth lint check (`check_banner`)
> and a fifteenth field (`brief`) were added, so any count in this document is now stale
> by construction. `sync_sabotage.py` / `sync_accept.py` were **not** ported — that gap is
> live if Phase B never lands.
>
> **§2 (Phase B) and §3 (week-two measurement) remain OPEN and unexecuted.** Phase B is
> filed as tree row `TT-1` and needs an explicit user go; landing it IS the trial's
> question-(a) verdict, so it must not happen as a side effect of other work.

Provenance: trial verdict evidence in ledger `2026-08-29` / `2026-08-29b`
(`docs/history/session-log.md`), friction log `docs/tasktool-trial-protocol.md` §6 A7,
and a 9-question tool census run 2026-08-29 (this spec's line-number cites come from it —
**re-verify each cite before editing at it; do not trust this doc over the tree**).

## 0. Goal, non-goals, decision gates

**Goal.** Make `tasks/` + `scripts/task.py` capable of serving as the repo's sole
priority authority: trustworthy (tests in the gate, footguns fixed), sufficient as a
session-start read (banner + row briefs), and with every load-bearing `HANDOFF.md`
function rehomed. Then — **gated on an explicit user go** — cut over.

**Non-goals.** No change to `formal/HANDOFF.md` (formal execution state keeps its file).
No change to the session-ledger (`docs/history/session-log.md` stays, append-only). No
schema/product code touched. `TK53` (15 remaining appends) is separate queued work, not
part of this spec.

**Decision gates.**
- Phase A is additive and safe under EVERY trial outcome (even a DELETE verdict wants A1,
  the test rescue, landed first — the sabotage evidence otherwise dies in `.scratch/`).
- Phase B (cutover) lands only on explicit user go, **in one commit, with the revert line
  recorded in the commit message**. Landing Phase B constitutes the trial's question-(a)
  verdict (KEEP tree / retire board); do not land it as a side effect.
- Until Phase B lands, the dual-update contract from `CLAUDE.md` is IN FORCE: any
  `HANDOFF.md` board edit gets the mirrored `task.py` op, same `--session` key.

## 1. Phase A — make the tool trustworthy (additive)

### A1. Rescue the test suite into the gate  ← do this first
The tool's correctness pin lives ONLY in gitignored scratch:
`.scratch/tasktool/test_task.py` (41 collected; verified via `--collect-only`) plus a
`--sabotage` self-runner mode (22 cases; evidence transcript `.scratch/tasktool/PROOF4.md`).
- Move the suite to `tests/test_tasktool.py` (tracked, gated — `verify.sh` tiles collect
  `tests/` structurally, so it lands in a tile with no list to update). Adapt paths;
  the suite must build its corpora in tmp dirs, never against the live `tasks/`.
- Convert the 22 sabotage cases into permanent pytest cases (durability ranking in
  `docs/sabotage-procedure.md`: permanent test > floor > docstring). Where a case can't
  be a test, transcribe its literal red output into the module docstring.
- Transcribe the load-bearing parts of `PROOF4.md` (the `22/22 sabotages produced an
  attributable red` record) into a tracked file: `docs/history/tasktool-proof-2026-08.md`,
  FROZEN banner, provenance noted.
- Re-pin `MIN_TESTS_ALL` to the new live collected count (get it from
  `pytest tests/ -q --collect-only`, never a run tail; the floor is zero-headroom by
  contract — set equal, then instrument-check it goes red at count+1 style sabotage).
- **Do not run `.scratch/tasktool/migrate.py`** (its `--rebuild` destroys hand-filed
  tasks). The rescue is a copy-and-adapt of the test file only.

### A2. Fix the six A7 footguns (`docs/tasktool-trial-protocol.md:430-465`)
1. **`ack` on a `source: hand` task must REFUSE** (nonzero exit, message naming the
   remedy) instead of printing success while stamping nothing. Bug site: the only
   stamping branch is `if task.source == 'board':` (`scripts/task.py:2827`); the hand
   path falls through to a success print (`:2863`) and `return 0` (`:2865`).
2. **"`ack` must be a session's last step"** — encode it: `ack` re-reads the source and
   warns loudly if the digest changed since the drift report it acknowledges; and the
   rule goes in `tasks/README.md` (new, see A4) and `docs/tasktool-spec.md`.
3. **`new` gains explicit id control**: `--id <ID>` (validated: unused, not in
   `tasks/retired-ids.txt`, well-formed) so a work row is never forced into the `TK`
   findings series.
4. **The `ls tasks/` undercount trap** gets a mechanical answer: `tasks/README.md`
   states the layout (open at top level, closed under `tasks/closed/`, the two non-task
   files) and points at `task.py counts` as the only census.
5. **Every truncated read path announces the truncation**: `list` (incl. `--parent`)
   prints `showing 20 of N — use --limit 0` whenever rows were dropped
   (`LIST_LIMIT = 20`, `scripts/task.py:585`). Test: corpus of 21, assert the notice.
6. **CLI papercuts**: `set` given `--title` produces a real error message naming the
   positional form; the 100-char title cap appears in `new --help`.

Each fix per `docs/sabotage-procedure.md`: write the test, revert the fix, watch the
test go red, record the literal red output in the test docstring and commit message.

### A3. Board view upgrades (the two adoption conditions)
1. **New optional frontmatter field `brief`** — a one-line, ≤120-char board annotation
   for the constraint a reader must not miss (the "NOT parallel-safe with `P3`" class).
   Schema order fixed, empty allowed. Lint: single line, length cap, no `|`.
   `board` prints it under the NOW block and under each NEXT row; `show` prints it
   beneath the title. Update `docs/tasktool-spec.md` (schema §, lint §, board §) in the
   same commit — the spec is the contract, and lint check 1 rejects unknown keys until
   the schema bump. Migrate by hand-populating `brief` for the current NOW/NEXT rows
   from their `HANDOFF.md` row annotations (4 rows; a judgment edit, not a script).
2. **`tasks/BANNER.md`** — the single must-read thing. Tracked, ≤14 lines, rewritten
   each session (the Rhythm's banner step retargets here). `board` prints it verbatim
   at the top and REFUSES (nonzero) if the file is missing — a missing banner is a
   broken session-start, not a default. Lint: file exists, first line carries a date
   and a ledger key. The scanner must skip `BANNER.md`/`README.md` when globbing task
   files (filename check 3 currently expects `<id>-*.md`; make the exclusion explicit
   and tested, not incidental).
3. **Board size is pinned, not aspirational**: with banner + briefs the target is
   ≤50 output lines; add a test that renders a full-budget corpus (1 NOW + 3 NEXT with
   briefs, 14-line banner) and asserts the ceiling. The "~25 lines" prose claims
   (`scripts/task.py:33`, `docs/tasktool-spec.md:44,260`) get updated — a stale size
   claim is exactly the rot class this repo documents.

### A4. Rehoming targets that are safe to land pre-cutover
- **`tasks/README.md`** (new): the preamble content — what the tree is, the
  "user-assigned task overrides ranking" rule, the reading protocol
  (`board` → `show <id>` → the item's read-first list), the layout note (A2.4).
- **`handoff_lint.py` gains a tree-aware mode** (flag or auto-detect):
  `check_ledger_row_ids` (`scripts/handoff_lint.py:496`) resolves ledger `rows:` ids
  against the task tree (open + closed + `tasks/retired-ids.txt`) instead of the board
  table; verify id-set parity between board and tree BEFORE switching harvest source.
  All doc-tree checks (frozen banners, ledger headlines/ordering, doc links, bold-caps,
  star glyph) are untouched — they outlive the board.
- Fix the stale symbol cite at `HANDOFF.md:78` (`check_ledger_ids` → the real
  `check_ledger_row_ids`) — the cite-a-symbol-that-EXISTS rule, and HANDOFF is at its
  260-line lint ceiling, so this edit must not add net lines.

### A5. Phase-A acceptance
- All ten gate phases green (`docs/gate-runbook.md` recipe; `ZANZIBAR_PY` override;
  exit codes read from `$rc`, never through a pipe).
- `python scripts/task.py lint` clean; `python scripts/handoff_lint.py` clean.
- Every new refusal has a red-run record (sabotage evidence, literal output).
- `docs/tasktool-spec.md` updated wherever behavior changed — spec and tool must not
  disagree for even one commit.
- Because this touches `*.md`: write docs first, re-run `verify.sh lean`, then commit.

## 2. Phase B — cutover (one commit, user go required)

- **`HANDOFF.md` becomes a ≤20-line stub**: pointer to `python scripts/task.py board`,
  `tasks/README.md`, and the Rhythm's new home. A stub, not deletion — many tracked
  docs link to `HANDOFF.md` and `check_doc_links` must stay green without a mass edit.
- **Rehome the remaining sections** (census of what the file holds beyond
  banner/board/items/Rhythm):
  - `## Standing traps` (`HANDOFF.md:203-210`) → each trap moves into the task file of
    the item it guards (or `CLAUDE.md` if repo-wide and durable).
  - `## Where things live` table (`:212-232`) → `docs/README.md`.
  - Retired-ids registry prose + reflow trap (`:71-83`) → `tasks/retired-ids.txt` header
    comment + `tasks/README.md`; confirm parity with the board lines before deleting.
  - `## Rhythm` (`:234-260`) → `docs/README.md`, rewritten for tree ops: ledger append
    (unchanged) → rewrite `tasks/BANNER.md` → `task.py` ops for every touched row
    (`promote`/`close -m`/`touch`/`set`, `brief` refresh) → `task.py lint` +
    `handoff_lint.py` → method lessons/doc fixes/traps as before.
- **Item blocks**: verify each NOW/NEXT block's content is present in its task file
  (they were maintained in parallel; `sync` was CLEAN at last check) — reconcile any
  gap INTO the task file before the stub lands.
- **`sync`/`ack`/`source_hash` retire with the board**: verbs print a
  "retired at cutover" refusal; lint keeps validating the frozen fields; the A2.1
  refusal test flips to expect the retirement message. Record the retirement in
  `docs/tasktool-spec.md`.
- **`CLAUDE.md` edits**: the "Start here" bullet retargets to
  `task.py board`; the trial bullet is replaced by one line recording the verdict and
  pointing here.
- **Commit message carries the revert line** (`git revert <sha>` restores the board),
  and the ledger entry records the cutover under its own session key.

## 3. Week-two measurement (lightweight, pre-registered here)

M3's transcript instrumentation is dead (`trial_metrics.py` scored 0-byte transcripts
green — see protocol §4); do not resurrect it. Week two measures only what is cheap and
honest:
- **Upkeep compliance**: `task.py lint` + `handoff_lint.py` clean lines in every session
  ledger entry (the existing literal-output convention).
- **Rot incidents**: any session that finds a stale `brief`/title/banner logs it in its
  ledger entry — count at week end.
- **Read line**: sessions keep the `read:` self-report with new vocabulary
  (`read: board`, `read: board + stub`, `read: other`), acknowledged as self-reported.
- **Exit clause**: one revert of the Phase-B commit restores the board; the tree keeps
  running in parallel exactly as during week one.

## 4. Constraints for the implementing agent

- Environment: Windows; conda env `graph-reachability-zanzibar-index` under
  `C:/Users/user/anaconda3/envs/...` (NOT the `avery` path in `verify.sh` — use
  `ZANZIBAR_PY`). Never round-trip repo files through PowerShell
  `Get-Content`/`Set-Content` (corrupts non-ASCII); use proper file tools.
- **Do not run `.scratch/tasktool/migrate.py`.** Do not edit the live `tasks/` corpus
  from tests. Do not lower any gate floor.
- `HANDOFF.md` is at exactly its 260-line ceiling — every pre-cutover edit there must
  be net-zero lines or free lines first.
- Any evidence produced (sabotage output, count measurements) goes in a TRACKED file
  the same hour; `.scratch/` is where evidence goes to die.
- Counts come from `--collect-only`, never a run's tail; exit codes from `$rc`, never
  through a pipe.
