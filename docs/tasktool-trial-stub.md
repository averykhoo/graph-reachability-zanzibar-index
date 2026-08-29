> **ACTIVE-PLAN — the TRIAL's proposed board, NOT the live one.** The live board is
> [`HANDOFF.md`](../HANDOFF.md) and it remains authoritative for the trial week
> (2026-08-23 → 2026-08-30). This file is what `HANDOFF.md` would be reduced to if the
> file-per-task tree in [`tasks/`](../tasks/) graduates: a pointer, the repo-wide traps
> that belong to no single task, and the write-back rhythm. It is generated
> (`.scratch/tasktool/migrate.py::handoff_stub`) — hand edits here are destroyed by the
> next regeneration and belong in the generator. Do not point sessions at this file;
> during the trial it exists to be measured against `HANDOFF.md`, not to be followed.
>
> **CORRECTION 2026-08-30.** The trial window was extended to **2026-09-06** and the tree
> is **not** being deleted (user decision). Line 3's "2026-08-23 → 2026-08-30" is week
> one. This file remains a draft, not the live board.
>
> **CORRECTION 2026-08-29d.** Two classes of fix were applied here IN PLACE rather than
> appended, and the distinction matters: the five broken relative links below were
> *typos* (they resolved to `docs/CLAUDE.md`, `docs/formal/HANDOFF.md`,
> `docs/docs/README.md` twice, `docs/docs/history/session-log.md`), not claims, and
> `check_doc_links` never caught them because
> this file is not in `handoff_lint.py::LINKED_DOCS`. The stale *claims* — a "~25 lines"
> board and a lint contract naming 9 of 12 checks — are corrected below and the reasons
> given at each site. ⚠ **The generator was NOT updated**: `handoff_stub` still emits the
> stale text, so a regeneration would undo all of this. Since Phase B lands this stub by
> hand in one reviewed commit (`docs/tree-sole-authority-spec-2026-08-29.md` §2) and
> `migrate.py` must not be run at all, that is the cheaper end of the trade — but it is a
> real divergence between this file and the tool that claims to produce it.

# HANDOFF — the pointer

DRAFT written by `migrate.py` into `.scratch/tasktool/sandbox-migrated/`; the real
`HANDOFF.md` is untouched.

**The board is a query, not a file:** `python scripts/task.py board`. Bounded by
`task.py::BOARD_MAX_LINES` and asserted by
`tests/test_tasktool.py::test_board_stays_under_its_size_ceiling` — no figure is written
here, because this sentence said "~25 lines" from the day it was generated through the
addition of a banner and a per-row `brief`, and was the last of five such claims found.
It prints [`tasks/BANNER.md`](../tasks/BANNER.md) verbatim first (and REFUSES if it is
missing), then the `NOW` item with its `brief` and summary, the `NEXT` rows with theirs, a
ready count, open counts per priority, staleness flags. Printed, **never committed**: a
committed `BOARD.md` re-creates the
260-line ceiling this migration exists to delete. The database is `tasks/` at the repo
root, one unbounded file per task; `python scripts/task.py show <id>` is the per-item
read, and its read-first list is all you read beyond [`CLAUDE.md`](../CLAUDE.md) and
[`tasks/README.md`](../tasks/README.md). Formal
*execution* state — what is proved, what the next lemma is — lives in
[`formal/HANDOFF.md`](../formal/HANDOFF.md), and any formal item's read-first list starts
there. Gate state is a query too — `python scripts/gate_status.py`, tree-addressed, so any
edit invalidates the verdict. Doc conventions: [`docs/README.md`](README.md).

**A user-assigned task overrides the board.** Work the task, re-rank once at write-back.

## Standing traps

Repo-wide and cross-item, belonging to NO task — which is why they survive here. A trap
parked on one item is invisible to the session working another.

* ⚠ **Do NOT lift `ttuDirect` in Lean.** It is load-bearing for the current admission
  story; the open descendant is row `DW-1`, and nothing is blocked meanwhile.
* ⚠ **Status lines inside `docs/history/` and `formal/history/` are frozen as-of-then**,
  and several are known false. Read them for method, never for state.

## Rhythm

End-of-session write-back. Steps 0–2 are the **mandatory floor**; if context runs short,
list every skipped action *verbatim* under `Still owed:` and the next session does it
first. A skip that leaves no trace is how the last accretion started.

0. **Run both linters** before committing any task or doc edit. Zero violations from each;
   both also ride `bash formal/verify.sh lean` (steps 4f/4g), so neither is optional.
   * `python scripts/task.py lint` — the task tree only: every file parses, ids unique,
     filename matches id, enums and dates and `brief` well-formed, the `NOW`=1 /
     `NEXT`<=3 budget, deps resolve and are acyclic, parents open, `closed:` stamped,
     labels declared, **the corpus floor plus its independent recount** (the instrument
     control — a scanner that has gone blind reports clean forever), parent depth (a
     warning, never a failure), and **`tasks/BANNER.md` exists, fits its cap and is
     dated**. The count of checks is printed by `lint` itself and is deliberately not
     restated here; this list named 9 of 12 until 2026-08-29d, and a *partial* contract
     is worse than none, because a reader treats it as complete.
   * `python scripts/handoff_lint.py` — everything the tree cannot see: this file's line
     ceiling and bold-caps budget, ~200 doc-to-doc `.md` pointers across the living roots,
     the two ledgers' relative ordering and the headline cap, a liveness banner on every
     `history/` file, and every id a ledger `rows:` line cites resolved against `tasks/`
     plus `tasks/retired-ids.txt`.
1. **One entry in [`docs/history/session-log.md`](history/session-log.md)**, every
   session, no exceptions — ledger first, so everything else has a key to cite.
2. **Record the work on the items**: `comment` for an outcome, `close -m` (message
   REQUIRED, outcome evidence) for a finish, `touch` when the detail is in the ledger,
   `promote` to re-rank — it refuses to break `NOW`=1 / `NEXT`<=3 at write time. Rewrite
   the summary / `## Traps` / `## Read first` of any item you worked; new traps go there,
   or to `CLAUDE.md` if durable and repo-wide. Every write op stamps `updated` with
   your session key, and every op above also stamps `moved` -- `moved` is "a session
   made PROGRESS", so it is the one an automated pass must not move (`ack` bumps
   `updated` only; so does any op given `--mechanical`). The key is the plain
   `YYYY-MM-DD` by default, so pass `--session <your step-1 key>` (either side of the
   verb; a future key is refused) if it has a letter.
3. **Never restate gate counts in prose** — `formal/FINAL_REVIEW.md`'s generated block is
   their one home. File method lessons in their runbook now.
4. **Fix wrong docs in place now — but "in place" depends on liveness.** A `LIVING` doc:
   edit it. A `FROZEN` or `ACTIVE-PLAN` doc: append a dated correction at the top and
   leave the body as provenance ([`docs/README.md`](README.md) §2–3).
   **This file never hosts a correction to another doc** — that one sentence is what kept
   the old board from accreting, and it binds a task file just as hard: a correction goes
   in the doc it corrects, and the task or the ledger points at it.

Before starting anything: `bash formal/verify.sh lean`, green in ~60 s warm.
