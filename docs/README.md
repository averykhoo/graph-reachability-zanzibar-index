# docs/README.md — the doc-system conventions

The primary reader of this repo's documentation is a Claude Code session starting
cold. Every convention here optimizes for that reader: minimal context cost at
session start, unambiguous liveness of every statement, grep-able stable keys,
bounded signals, pointers instead of copies.

This file is the durable contract for *how* docs work. It does not carry status.
Designed 2026-08-16 in [`history/handoff-redesign-2026-08.md`](history/handoff-redesign-2026-08.md),
which was executed in full and frozen the same day. Where that plan and this file disagree,
this file wins: it is the living contract, that is the plan which produced it.

## 1. One home per statement

The single rule the rest of this file elaborates: **every statement has exactly one
home, and everywhere else is a pointer.** A correction to another doc is filed *in
that doc*, never parked on the board. Duplication is not redundancy — the copies
rot independently, and the reader cannot tell which one is live.

| content type | home |
|---|---|
| priority/status of open items | the task tree, [`../tasks/`](../tasks/README.md), only — one file per task, read as a QUERY (`python scripts/task.py board`, then `show <id>`; contract in [`tasktool-spec.md`](tasktool-spec.md)). **Sole authority since the 2026-09-06 cutover** (Phase B′ of [`tree-sole-authority-spec-2026-08-29.md`](tree-sole-authority-spec-2026-08-29.md)); `HANDOFF.md` carries no row table and no item blocks, and `handoff_lint.py::check_ledger_row_ids` resolves every id the ledger cites against the tree |
| what the NEXT session must not miss | the `## Banner` section of [`HANDOFF.md`](../HANDOFF.md) — the one-hop note, ≤60 lines, rewritten every session (§7 step 2; `task.py lint` check 12 requires the banner, `board` prints it verbatim and refuses without it). `tasks/BANNER.md` is a tombstone: check 12 fails if it reappears |
| the one constraint a board reader must not miss, per item | the task file's `brief` field — one line, capped, and NOT a summary ([`tasktool-spec.md`](tasktool-spec.md) §3.1) |
| session narrative | [`docs/history/session-log.md`](history/session-log.md) (root) / [`formal/history/PROOF_STATUS.md`](../formal/history/PROOF_STATUS.md) (formal detail) |
| formal execution state ("what is proved, what is the next lemma") | [`formal/HANDOFF.md`](../formal/HANDOFF.md) — no priorities there |
| method lessons | [`sabotage-procedure.md`](sabotage-procedure.md) (checks **and measurements**) / [`subagent-fanout-runbook.md`](subagent-fanout-runbook.md) (fan-outs) |
| durable rules, footguns, env | [`CLAUDE.md`](../CLAUDE.md) |
| gate/operational/machine state | [`gate-runbook.md`](gate-runbook.md) |
| design decisions, incl. post-spec user adjudications | [`architecture/decision-log.md`](architecture/decision-log.md) |
| divergences — what diverged, when and why | [`spec-deviations.md`](spec-deviations.md), append-only |
| latent gaps — what is still open **today** | [`latent-gaps.md`](latent-gaps.md), rewritten in place |
| plans/scopes for active legs | their scope doc (ACTIVE-PLAN header; corrections appended dated) |
| perf | [`perf-next-round.md`](perf-next-round.md) → the active round doc → `docs/history/` |
| retired anything | `docs/history/` with the frozen banner from §3 |
| doc-system conventions | this file |

**Live gate figures live in exactly one machine-checked place**:
[`formal/FINAL_REVIEW.md`](../formal/FINAL_REVIEW.md)'s generated counts block, gated by
`verify.sh` step 4e. Do not restate a count in prose anywhere — a quoted count is not
merely stale, it is unenforced. This file states no figures for that reason.

**Enforced since 2026-09-08** (task `TK58`), and it was prose-only for the eight months
before that, which is why `ZT-P3-5` kept recurring:
`scripts/handoff_lint.py::check_restated_counts` refuses `N checks` / `N open tasks` /
`N tests` in `CLAUDE.md`, `HANDOFF.md`, top-level `docs/*.md` and `tasks/*.md`, riding
`verify.sh` step 4f. **The remedy is always to DELETE the number and point at its home,
never to update it** — an updated number is the same unenforced claim, one day younger.
Four structural escapes exist and are the sanctioned way to write a figure down: a fenced
block (evidence), a backticked or quoted span (a citation), a `YYYY-MM-DD` key on the line
(a stamped observation), and a file whose §2 banner declares its body provenance
(`FROZEN`, `ACTIVE-PLAN`, or the append-only form of `LIVING`). What is *not* covered:
`docs/history/`, `docs/specs/`, `docs/architecture/`, `formal/`, and a task file's
append-only `## Log`.

## 2. Liveness is declared, and it is three-valued

Every doc declares one of these in its first lines. A reader must never have to infer
whether a statement is still true.

| state | meaning | obligation |
|---|---|---|
| **LIVING** | maintained; every statement is claimed true today | fix in place when it goes wrong |
| **FROZEN** | provenance only; status lines are as-of-then | visible banner (§3); corrections appended dated at the top, never edited into the body |
| **ACTIVE-PLAN** | a scope/plan doc currently being executed | body is provenance; corrections appended dated at the top; live until its task rows close, then frozen |

ACTIVE-PLAN exists because live scope docs sit under `formal/history/` for filing
reasons and moving them would break inbound links. The state is declared in the header
instead of inferred from the path. The append-only ledgers
([`history/session-log.md`](history/session-log.md),
[`PROOF_STATUS.md`](../formal/history/PROOF_STATUS.md)) are LIVING despite their paths.

**Archive the status, keep the method.** When a leg lands, its status text retires to
`docs/history/` — but the *method lesson* it produced does not go with it. The lesson
belongs in a living doc (`sabotage-procedure.md`, `subagent-fanout-runbook.md`,
`CLAUDE.md`, or this file) where the next session will actually read it. Archiving a
lesson alongside the status is how a hard-won rule becomes invisible.

**An author's-voice TODO is a declared hole, not drift.** The root
[`README.md`](../README.md) carries two editorial markers — `:142` *"todo: continue story
another day"* and `:150`'s placeholder for the MAFSA word-count trick — standing for
unfinished narrative that only their author can write, flagged in place rather than smoothed
over. **Do not "resolve" a marker like that by deleting it**; the only way to retire one is
to write the prose it stands for. A silent deletion turns a published hole into an invisible
one, which is the documentation analogue of what
[`sabotage-procedure.md`](sabotage-procedure.md) refuses for coverage: *"Publish the residue
rather than rounding it away."* Cite these by the path `../README.md` — a bare `README.md`
link from inside `docs/` resolves to the wrong file, and once did.

**Freeze at landing.** A design or investigation record gets its frozen banner **the
moment its change lands** — part of the landing checklist, exactly like updating
`formal/CORRESPONDENCE.md` for an algorithm change. A design doc that still says
"nothing in the repo was modified" months after the leg landed is the failure this rule
prevents.

**⚠ Not yet adjudicated: a set of always-living docs declares no state at all**, in
violation of the rule at the top of this section. Measured 2026-08-29 by looking for a
bolded `LIVING` / `FROZEN` / `ACTIVE-PLAN` inside the first 8 lines: `formal/README.md`,
`formal/CORRESPONDENCE.md`, `formal/ARCHITECTURE.md`, `formal/FINAL_REVIEW.md`,
`formal/SEMANTICS.md`, `formal/HANDOFF.md`, `docs/gate-runbook.md`, the three specs in
`docs/specs/`, `docs/perf-round6-audit-2026-08.md`, `docs/perf-next-round.md`,
`docs/sabotage-procedure.md`, `docs/architecture/correctness.md`,
`docs/architecture/decision-log.md`, and the two `benchmarks/results/` profiles. **Whether
these are deliberately exempt is the open question, and the exemption belongs here when it
is decided** — several are plainly living by any reading, and an exemption stated nowhere
is indistinguishable from an oversight.

⚠ **Do not put a count on it, here or in a title.** The figure has read six, then nine,
then eleven, then the list above, across four readings on four days — not because docs
changed but because each reading used a different candidate set and a different test for
"declares a state". Whoever adjudicates this must **state their method with the answer**,
as the sentence above does; a bare number is `ZT-P3-5` waiting to happen, and it already
happened once inside the board row that tracks this very item.

## 3. The frozen banner

Visible prose, in the first lines, never an HTML comment — an invisible banner does not
warn anybody:

> **FROZEN &lt;date&gt; — provenance, not a living document.** Status lines below are
> as-of-then and several may now be false; live state: `HANDOFF.md` + the session
> ledger. Corrections are appended dated at the top, never edited into the body.

**What is mechanically enforced, and what is not** (measured 2026-08-29b — say which,
because "there is a lint for it" has been assumed here before it was true):

* **Enforced, and it does not go stale.** `scripts/handoff_lint.py::check_frozen_banners`
  walks *every* `.md` under the history dirs and requires a declared state in the first
  five lines. The exemption is structural — a file is exempt by declaring `LIVING` or
  `ACTIVE-PLAN` up top — and the check deliberately refuses a hand-maintained filename
  list, because a list beside a glob goes stale the first time someone adds a file. So a
  new record landing in a history dir *is* covered automatically.
* ⚠ **Not enforced: design docs that live outside a history dir.** Nothing walks
  `docs/design/` or `docs/specs/`, so the "freeze at landing" rule above is held by hand
  there. That is the residual half of what was once filed as a one-time sweep.
* ⚠ **Not enforceable: a stale DESCRIPTION.** `::check_doc_links` proves a link resolves,
  never that the sentence around it still describes the target. A citation naming a line or
  a section of another doc breaks silently when that doc is rewritten, and no check will
  tell you. This is why §5 says to cite stable keys rather than positions.

## 4. Signals rank only if they are bounded

**Priority is a word in a column** — grep-able, unambiguous, and capacity-bounded so the
ranking argument happens once at write time instead of being re-derived every session.

| word | meaning | capacity |
|---|---|---|
| `NOW` | the single item an unassigned session should pick up | **exactly 1** |
| `NEXT` | the items most likely to be picked next or run in parallel with `NOW` | **at most 3** |
| `LATER` | real, not queued; re-ranked when `NOW`/`NEXT` drain | unbounded |
| `HOLD` | deferred by an explicit recorded decision (→ pointer) | unbounded |
| `SOMEDAY` | revisit only on a concrete need | unbounded |

**Emoji are category badges, never degree:**

| badge | meaning | budget |
|---|---|---|
| 🟢 / 🔴 | gate state — banner only | 1 |
| ⚠ | a trap: acting without reading this line produces WRONG work | at most 10 in `HANDOFF.md` (`handoff_lint.py::WARN_BUDGET`) |
| 🧭 | waiting on a user decision (the line must name the decision) | as needed |

`★` and `★★` are **retired** from the two handoff files ([`HANDOFF.md`](../HANDOFF.md) and
[`formal/HANDOFF.md`](../formal/HANDOFF.md)) and are removed from other living docs as
they get touched. Frozen archives keep theirs as provenance; the append-only ledgers keep
old entries untouched, but **new ledger entries do not use `★`**. Bold ALL-CAPS survives
only inside a ⚠ line. The banner in `HANDOFF.md` is printed by `task.py board` through
`task.py::ASCII_FOLD`, so it may use only glyphs that table maps — `task.py lint` check 12
refuses any other (`′`, `✅`, `📌`, `🔍` are the ones that have been pasted into it).

**⚠ overflow is a defined move, not an invention.** At budget, the trap demotes to the
owning task file's `## Traps` section (`python scripts/task.py show <id> --section traps`)
and the banner keeps at most a pointer. If that feels wrong, the trap was load-bearing
enough to belong in `CLAUDE.md` — which is auto-loaded every session, so it costs the
reader nothing.

## 5. Stable keys, never positions

Ids and keys are cited from append-only ledgers, frozen archives, code comments and test
docstrings. They must survive a rewrite of the file they came from.

* **Tasks → id** (`P3`, `B1`, `ZT-P3-5`, `R6`, `HS-1`). **Ids are carried forward
  forever and never reused**, including after the task closes (`tasks/closed/` keeps the
  file; `tasks/retired-ids.txt` holds spent ids that never had one).
* **Ledger entries → date key** (`2026-08-16b`), never a position in the file.
* **Code → `file::symbol`** (`Cascade.lean::GraphState.writeLoggedOne`), never a line
  number. `verify.sh lean` resolves every `file::symbol` anchor in
  `formal/CORRESPONDENCE.md`, so a rename fails the gate instead of rotting.
  **Outside `CORRESPONDENCE.md` nothing checks this — it is a convention, held by
  hand, and the 2026-08-19 sweep is what it costs to let it slip.** Three forms that
  *look* right and do not resolve, all found in living docs that day:
  * a bare method name (`processor.py::_reconcile_subject`) — anchors are
    `__qualname__`, so it is `::DeltaProcessor._reconcile_subject`;
  * a function LOCAL (`::WildcardIndex.check.row`) — `anchor_check.py` records only
    defs/classes plus class- and module-level assignments, deliberately. Name the
    enclosing function instead. Closures ARE valid (`::Oracle.check.ttu_leaf`);
  * a bare filename (`models.py:121`) — there are three `models.py`. Write the
    package (`index_v4/models.py`) whenever the file name is not unique.

  When the target is a comment, a branch, or a `dict` key rather than a symbol,
  **quote the code and name the symbol it sits in** — `extractor.py::_edge_projection`
  (`if obj[3] == "any" or subj[3] == "all": return "P2"`), `corpus.py::SCHEMAS`'s
  `"residue_rich"` entry. (The example used to quote that function's `return "P6"`
  branch, which was deleted when P6 retired 2026-09-05 — a quoted branch is a citation
  too, and it rots exactly like a line number.)
  A step with an in-code marker is cited by the marker (`_reconcile` step (2c)), and
  a numbered invariant by its number (`I1`, `I6`) — both travel with the code.
* **House rules → their number.** `formal/HANDOFF.md`'s house-rule numbering and this
  repo's working-rhythm numbering are cited from code; renumbering breaks those
  citations silently. Keep the numbers byte-stable.
* **Archived content → section title, never a line number.** The landed form is:

      `docs/history/handoff-status-2026-07.md` "Zero-trust review 2026-07-26"
      (archived from `HANDOFF.md` 2026-07-29) §P5

  as used in `docs/spec-deviations.md`'s "2026-07-26 — ZT-P5" entry and at
  `tests/test_generator_coverage.py:6`. A citation that names a line number in a living
  file is wrong the day the file is edited — this very sentence cited
  `docs/spec-deviations.md:2645` when it was written on 2026-08-16 and that line had
  already drifted to a blank one by the end of the same session.

## 6. Boards replace; ledgers accrete

**The note and a task's body are rewritten in place** — no dated layers, no strikethrough
graveyards, no "as of" stacking. When a fact changes, the old text is deleted, not
annotated. `HANDOFF.md` is rewritten whole every session; a task file's summary, `brief`,
`## Traps` and `## Read first` have replace semantics — every session that touches a task
rewrites what it invalidated, *read-first list included*. The one accreting part of a task
file is its `## Log`, which `comment` / `close` / `promote` append to (and `show` renders
newest-first, so the file's top is never mistaken for its current state).

**Ledgers are append-only and never retro-edited.** A later entry names what it refutes.
Entry format is defined in [`history/session-log.md`](history/session-log.md)'s own
header; one root entry is written EVERY session.

This split is the whole cure for the disease that produced this redesign: updates that
arrive as new dated layers instead of edits in place, so the same fact ends up stated
three or four times at different ages and the reader cannot rank them.

## 7. Rhythm — the end-of-session write-back

Moved here from `HANDOFF.md` at the 2026-09-06 cutover (Phase B′: the tree is the sole
authority; the note is one hop). The step numbers are cited from code and the ledger —
**keep them byte-stable** (§5). Steps 0–3 are the **mandatory floor**; if context runs
short, list every skipped step-4/5/6 action *verbatim* under `## Still owed` in
`HANDOFF.md` and the next session executes it before its own work. A skip that leaves no
trace is how the last accretion started.

0. **Run `python scripts/task.py lint` and `python scripts/handoff_lint.py`** before
   committing anything. Both must be clean; `verify.sh lean` runs the second one too.
1. **Append one entry to [`history/session-log.md`](history/session-log.md)** — every
   session, no exceptions. Ledger first, so the banner has a key to cite. The entry
   carries two literal lines, and `handoff_lint.py::check_session_receipt` reddens
   `lean` when the newest entry lacks either: the output of `python scripts/task.py
   lint`, and `read: board only` or `read: board + note` — an honest report of whether
   the board query was the whole session-start read, or the note was needed as well.
2. **Rewrite the `## Banner` of [`HANDOFF.md`](../HANDOFF.md)** — the single copy: gate
   state as observed, the entry key just created on its FIRST line, the headline, what
   the next session must not repeat. At most `task.py::BANNER_MAX_LINES` lines, only
   glyphs `ASCII_FOLD` maps (§4); check 12 enforces all three. Then rewrite the rest of
   the note: `## Still owed` (verbatim skipped actions, or "Nothing") and the next-session
   pointer. The whole file stays under `handoff_lint.py::MAX_LINES`.
3. **Edit the tree, by op, in the same session.** `promote <id> <PRI>` for every re-rank;
   `touch <id>` for every task you progressed and did not otherwise write (never edit
   `moved` by hand — it is what `board` reads to warn about neglect); `close <id> -m`
   for every finished task (the tool sweeps the id out of every `deps` cell); `set <id>
   brief` when the one-line constraint changed; and rewrite the summary / `## Traps` /
   `## Read first` of every `NOW`/`NEXT` task you touched. `comment <id> -m` records a
   review that changed nothing (`--mechanical` for a tool acting on a session's behalf:
   `updated` moves, `moved` holds). Pass `--session <key>` with the ledger key.
3b. **Do not restate gate counts in prose.** They live in `formal/FINAL_REVIEW.md`'s
   generated block and are machine-checked by `verify.sh` step 4e; regenerate with
   `python -m formal.conformance.doc_counts --generate`. The old board went stale three
   separate times by keeping its own copies (`ZT-P3-5`).
4. **File method lessons in their runbook now** — the ledger entry summarises and points.
5. **Fix wrong docs in place now.** Living doc → edit it; FROZEN or ACTIVE-PLAN → append a
   dated correction at the top. **The note never hosts a correction to another doc.**
6. **New traps** → the owning task's `## Traps` section, or `CLAUDE.md` if durable and
   repo-wide. The banner carries a pointer at most.

⚠ Editing any `*.md` changes the `t2a` tree id and stales the `lean` verdict, and
`t2c` includes `tasks/*.md` and `HANDOFF.md` (`gate_status.py::CODE_SCOPE_MD_KEEP`), so
a tree or note edit stales the pytest tiles too. Write the records FIRST, then run the
gate, then commit. Before starting anything: `bash formal/verify.sh lean` should be green
in ~60 s warm; if it is not, fix that first — it is the fastest signal in the repo.

## 8. Where things live

Moved here from `HANDOFF.md` at the 2026-09-06 cutover. `CLAUDE.md` is auto-loaded;
`HANDOFF.md` is the one file read by hand at session start, after `task.py board`.

| doc | what it is | when to read |
|---|---|---|
| [`CLAUDE.md`](../CLAUDE.md) | durable rules: env, the gate, layout, testing conventions, invariants, the four footguns | every session (auto-loaded) |
| [`HANDOFF.md`](../HANDOFF.md) | the one-hop note: the banner, `## Still owed`, the next-session pointer — nothing a query can derive | every session, after `python scripts/task.py board` |
| [`../tasks/README.md`](../tasks/README.md) · [`tasktool-spec.md`](tasktool-spec.md) | the task tree: layout, reading protocol, the rules `lint` cannot enforce / the tool's full contract and op semantics | before your first write op; when an op refuses |
| this file | doc-system conventions: liveness, banners, ledger format, citation keys, signals, the Rhythm | before restructuring any doc; at write-back |
| [`history/session-log.md`](history/session-log.md) | the root session ledger, newest first | top entry at session start; write one every session |
| [`gate-runbook.md`](gate-runbook.md) | cap-safe phased `verify.sh`, the Postgres leg, fuzz, every floor and budget | before running the gate |
| [`../tests/dbengine.py`](../tests/dbengine.py) | the SQLite-vs-server engine seam (`ZANZIBAR_TEST_DSN` / `ZANZIBAR_PG_REQUIRED`) | running the PostgreSQL leg |
| [`architecture/overview.md`](architecture/overview.md) | architecture index — module map plus pointers to every deeper doc | orienting in unfamiliar code |
| [`spec-deviations.md`](spec-deviations.md) | the dated divergence ledger — append-only, true as of each date key, never live status | when behaviour surprises you |
| [`latent-gaps.md`](latent-gaps.md) | what is still latent **today**; rewritten in place | before chasing a gap you found in the ledger |
| [`sabotage-procedure.md`](sabotage-procedure.md) | how to prove a check actually checks; the catalogue of checks that failed by passing | before adding any test, floor, pin or gate phase |
| [`subagent-fanout-runbook.md`](subagent-fanout-runbook.md) | how to run a multi-agent sweep without wasting it | before launching a fan-out |
| [`perf-next-round.md`](perf-next-round.md) | perf fence, dead ends, hygiene, the reopening rule | before any perf work |
| [`specs/`](specs/) | the original design specs, cited by code as "spec §N" | when a code comment cites one |
| [`../formal/HANDOFF.md`](../formal/HANDOFF.md) | the formal subtree's execution state and house rules — the read-first for any formal task | before touching `formal/` |
| [`../formal/CORRESPONDENCE.md`](../formal/CORRESPONDENCE.md) | the model↔Python map; §7/§8 record algorithm drift | when changing a modeled algorithm |
| [`../formal/FINAL_REVIEW.md`](../formal/FINAL_REVIEW.md) | the governing claim doc — and **the only home for live counts** (generated block) | whenever you need a figure |
| [`../benchmarks/results/PERF_ANALYSIS.md`](../benchmarks/results/PERF_ANALYSIS.md) | measured perf numbers per landed item | assessing a perf candidate |
| [`history/`](history/) · [`../formal/history/`](../formal/history/) | retired records and the append-only ledgers. [`history/handoff-status-2026-07.md`](history/handoff-status-2026-07.md) holds the reconciled **`ZT-*` disposition ledger**; [`history/tasktool-proof-2026-08.md`](history/tasktool-proof-2026-08.md) the tool's sabotage record | for method and provenance — **never for state** |
