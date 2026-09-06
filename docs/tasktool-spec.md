> **LIVING — the task tool's contract, tracked for the 2026-08-23 → 2026-09-06 trial**
> (extended a week on 2026-08-30; the tree is not being deleted).
> Copied from `.scratch/tasktool/SPEC.md` so the tool's contract is not itself in a
> gitignored directory. Where this file and `scripts/task.py` disagree, **the code wins**
> (the repo's standing rule); fix the doc in place. Companion contracts that remain in
> scratch for now: `SYNC-SPEC.md` (drift buckets, the no-delete guarantee) and
> `START-HERE.md` (build-session handoff).

# SPEC — `task.py`, a file-per-task tracker

Design settled in conversation 2026-08-20/21. This file is the contract; implement
exactly this. Where it is silent, prefer the simplest thing and write a note in
`notes.md` rather than inventing a feature.

## 0. Hard constraints for anyone working on this

* **Write ONLY inside `.scratch/tasktool/`.** The main repo is READ-ONLY. Another agent
  is actively editing the real tree; touching it is the one unrecoverable mistake here.
  Never edit `HANDOFF.md`, `scripts/`, `docs/`, `formal/`, or anything outside this dir.
* **Python 3, standard library only.** No PyYAML, no `python-frontmatter`, no pip installs.
* **Windows host.** Always `io.open(path, encoding='utf-8')` for read and write; never
  rely on the platform default. Console stdout may be cp1252, so **all script OUTPUT must
  be ASCII** (no `⚠`, no `→`, no box-drawing). File CONTENT may be UTF-8 (task bodies will
  contain `⚠` — that is fine, it just must not be printed unescaped).
* Write files with `\n` newlines (open with `newline=''` semantics or write text with
  explicit `\n` and no translation) so the files are byte-stable across platforms.
* Match the repo's house idiom: a module docstring that explains WHY the thing exists and
  what its honest limits are, `%`-style formatting, and — for `lint` — a SABOTAGE RECORD
  section listing each check, the narrowest plausible weakening that was broken on purpose,
  and the literal observed failure output. See `scripts/handoff_lint.py` in the main repo
  for the exact tone and structure (READ it, do not copy it wholesale).

## 1. Why this exists (the problem being solved)

The repo tracks work in `HANDOFF.md`, which is simultaneously the *database* and the
*session-start read*. That coupling caps the database at what a session can afford to
read (today: a hard 260-line ceiling), so items get dropped for space, completed work
stays marked open, and task groups never migrate to an archive.

The fix decouples them:

* **Database** — `tasks/*.md`, one file per task, unbounded, nothing ever dropped.
* **Session view** — the OUTPUT of `task.py board`, printed and never committed, at
  constant context cost regardless of backlog size. Its size is bounded by
  `task.py::BOARD_MAX_LINES` and **asserted** by
  `tests/test_tasktool.py::test_board_stays_under_its_size_ceiling`, which renders a
  full-budget corpus. No figure is restated here: four places in this repo carried
  "~25 lines" while the view grew a banner and a `brief` per row, and a size claim no
  test reads rots exactly like a stale count.

A committed `BOARD.md` would re-create the disease. The board is a query, always.

## 2. Directory layout

```
tasks/
  BANNER.md              # NOT a task: session state (section 4 `board`, check 12)
  README.md              # NOT a task: layout, reading protocol, unenforceable rules
  config.json            # machine config (see section 6)
  retired-ids.txt        # one id per line; ids are NEVER reused
  P3-leg7-4cii.md        # open tasks
  P6-ttustarfree-ii.md
  closed/
    P1-something.md      # closed tasks; same format
```

* Only `*.md` files are tasks. `config.json` and `retired-ids.txt` are skipped by every
  scan because they are not markdown.
* **`BANNER.md` and `README.md` are markdown and are skipped by NAME**
  (`task.py::NON_TASK_MD`), at the TOP LEVEL only — `closed/` is deliberately not exempt,
  because an exemption that survives the archive move would hide a real record. Both
  scanners apply it: `Store.md_paths` and the independent recount `disk_md_count`. They
  share the constant and duplicate the walk, so a blind scanner is still caught by lint
  check 10 while the two halves cannot disagree about the banner's filename.
* **`ls tasks/` undercounts and always will** — it shows the open half only (about a
  third of this corpus) and counts the two non-task files. The only census is
  `task.py counts`; see `tasks/README.md`.
* **Open vs closed is the FOLDER.** There is no `status` field.
* **The id is the address, never the path.** Resolution: glob `<id>-*.md` in `tasks/`,
  then `tasks/closed/`, and verify the frontmatter `id` matches; fall back to a full scan
  of both dirs if the glob misses. A rename or an archive move can therefore never rot an
  inbound `P3` reference.
* Filename is `<id>-<slug>.md`. The slug is generated once from the title at `new` and is
  never updated afterwards. It is cosmetic (for `ls`); the frontmatter `id` is truth.

## 3. Task file format

```markdown
---
id: P3
title: leg 7 step 4c-ii co-landing with step 7, in one commit
brief: NOT parallel-safe with P6 -- same 38-module cone, whichever lands second re-pays it
pri: NOW
size: L
deps: [P4, P6]
related: [P14]
parent: B2
labels: [formal]
source: board
source_hash: 39fbc1a2e0d4
created: 2026-08-05
moved: 2026-08-20b
updated: 2026-08-21c
closed:
---

Free prose summary: what this item is and why it matters. Replace-on-touch.

## Traps

Item-scoped traps, badged with the warn glyph. Read automatically because the session
reads this file. Cross-item and repo-wide traps do NOT live here.

## Read first

Ordered pointer list, `file::symbol` citation keys as the repo already uses.

## Log

### 2026-08-20b

Append-only. Newest LAST. Written by `comment` and `close`.
```

### 3.1 The fifteen fields

All fifteen keys are ALWAYS present, in exactly this order. An empty value means
absent. Fixed order plus always-present is what makes diffs stable and the parser
trivial.

| field | set by | value | notes |
|---|---|---|---|
| `id` | `new`, immutable | e.g. `T7`, `P3`, `HS-5`, `ZT-P0-1` | unique across open + closed + retired registry |
| `title` | human | one line, <= `TITLE_MAX` chars | prints in `board` / `list` |
| `brief` | `new --brief`, `set brief` | one line, <= `BRIEF_MAX` chars, no `\|`, **may be empty** | the constraint a board reader must not miss; prints under the NOW block and under each NEXT row |
| `pri` | `promote` | `NOW`/`NEXT`/`LATER`/`HOLD`/`SOMEDAY` | exactly 1 NOW and <= 3 NEXT among OPEN tasks |
| `size` | human | `S`/`M`/`L`/`?` | |
| `deps` | `dep` | flow list of ids, `[]` when empty | ordering/blocking edges; acyclic |
| `related` | `set related` | flow list of ids, `[]` when empty | **navigation only**, unordered, untyped, NOT acyclic |
| `parent` | human or `new` | one id or empty | containment/rollup, distinct from deps |
| `labels` | human | flow list, `[]` when empty | drawn from the closed vocabulary in config |
| `source` | `new`, **immutable** | `board` / `hand` / a repo-relative path | where this task came from |
| `source_hash` | `sync --create-new`, `ack` | 12 hex chars, the `acked-no-row` sentinel, or empty | the source block as of the last reconciliation, or an acknowledgement that the source names no row for this task (SYNC-SPEC.md sections 3 / 3.1) |
| `created` | `new`, immutable | session key | |
| `moved` | PROGRESS writes only | session key | staleness signal: last time a session made progress |
| `updated` | EVERY write | session key | last write of any kind, including housekeeping |
| `closed` | `close`/`reopen` | session key or empty | non-empty IFF file is under `closed/` |

**Key order groups by KIND, not by date of addition.** The two edge lists sit
together, the two birth facts sit together, and the three stamps sit together at the
end. Appending `updated`/`source`/`related` after `closed` would have been a smaller
migration diff and a worse file to read for the rest of its life. `brief` (added
2026-08-29) follows the same rule: it is the second thing a reader reads, so it sits
under `title`, not at the end where the migration would have been free.

#### `brief` — the one line a board reader must not miss

Optional, and its own emptiness is the common case. It exists for the class of fact that
is invisible in a title and expensive to rediscover — the motivating one being board row
`P6`'s *"NOT parallel-safe with `P3`"*, a sequencing constraint that was carried on the
board, existed nowhere in the tree, and is worth two sessions of rework.

Rules, all in `task.py::brief_problem` so that `set`, `new`, lint check 4 and
`validate_record` cannot disagree: one line, no `|`, no leading/trailing whitespace, at
most `BRIEF_MAX` chars. It may be **cleared** (`set <id> brief ""`), and that is
deliberate — a constraint is usually true for a while and then not, and a field that can
only be written accumulates stale warnings, which is worse than carrying none.

It is NOT a summary. The body already holds the summary and `board` already prints it;
`brief` earns its place on the board only by carrying something the title cannot. If it
reads like a restatement of the title, delete it.

#### `moved` vs `updated` -- the split, and the per-op rule

`updated` bumps on **every** write. `moved` keeps its old meaning: the last time a
session made **progress**. The distinction is load-bearing and the reason is specific:
a cheap-model housekeeping pass that leaves a comment or acknowledges drift must NOT be
able to launder a stale item into looking fresh. **An old `moved` on a NOW row means
neglect, and that signal has to survive automation** -- which is why `board`'s staleness
warning reads `moved`. Point it at `updated` and the warning stops being able to fire
the moment anything runs on a schedule.

The rule is per-op and mechanical. Nothing anywhere asks whether an edit felt like
progress:

| bump | ops |
|---|---|
| **both `moved` and `updated`** | `new`, `touch`, `promote`, `dep add`/`dep rm`, `close`, `reopen`, `comment`, `set` -- a session recording real work |
| **`updated` only** | `ack` (acknowledging reported drift), and any write carrying `--mechanical`: sync-applied field fixes and any future mechanical/housekeeping op |

`--mechanical` is offered on `set`/`promote`/`dep`/`comment`/`touch` and is **for a
tool, not for a person**: `sync` passes it on every field fix it applies, the same way
it emits every command -- unconditionally -- and a human doing the work simply never
types it. That is what keeps the rule free of judgement: the caller is decided once, at
the call site. It is deliberately absent from `close`/`reopen`, which require a message
and which `sync` is forbidden from ever performing — and from `ack`, which is
unconditionally ack-class and so has nothing to flag.

Nothing can VERIFY that an automation passed the flag honestly; an automation that omits
it launders `moved` exactly as if the flag did not exist. What it buys is that an honest
tool has a way to be honest, and that `ack` cannot be anything else.

**A closed task can still receive comments** -- that is exactly why `updated` exists
separately from `closed`. `closed` says when the item stopped being work; `updated` says
when the file was last touched at all.

Invariant, checked by lint: `created <= moved <= updated`. The write path cannot produce
`updated < moved`, which is precisely why it is checked -- that state can only arrive by
hand or from a tool that stamps one and not the other, and both are silent.

#### `source` -- provenance in the file, not in a state file

`board`, `hand`, or a repo-relative path such as
`docs/perf-round6-audit-2026-08.md`. Set once at creation (`new --source`, default
`hand`, because the default caller is a human typing `new`), and **immutable
thereafter**: the mechanism is simply that no op writes it afterwards, so there is no
flag to defeat. If a value is wrong, that is a hand edit plus a Log entry saying so.

**This field REPLACES the `sync-state.json` that SYNC-SPEC.md section 3 proposed.**
Keeping provenance IN the task file means there is no second state file to desync, go
missing, or silently degrade every task to "hand-filed, expected" -- and it travels with
the file through the archive move and through any rename. SYNC-SPEC.md section 3 is
updated to match; the superseded design is not left standing in it.

Validation is on the SHAPE, not on existence: a `source` path is never checked against
the disk. This corpus lives under `.scratch/` while its sources live in a read-only repo,
and a source document that is later renamed or archived would turn the gate red for a
fact that is still true.

#### `related` -- navigation, deliberately not a graph

A flow list of ids. Unordered, non-semantic, **untyped**: no `supersedes`, no
`duplicate-of`, no `see-also`. The rationale is worth keeping because it is the reason a
richer design was rejected: `deps` and `parent` earn their complexity because QUERIES
read them (`ready`, the archive sweep, the census). A typed relation carries no query
semantics at all, and it does create a decision point where a model picks the wrong type
invisibly. Prose in the body says it better, and the body is already there.

Lint: every id must resolve; self-reference is refused; **no cycle check** -- the relation
is symmetric-ish and acyclicity is meaningless for it (`A related B` + `B related A` is
the normal state, and a cycle check would call the normal state a violation). Reciprocity
is not enforced either: a hand-maintained inverse edge is the rot machine this format
exists without. `show` therefore computes and prints the INCOMING links, or half of every
link would be invisible from the end that did not write it.

**Session key** = `YYYY-MM-DD` with an optional single lowercase letter suffix
(`2026-08-20b`), matching the repo's session-ledger heading keys. Plain string comparison
sorts them correctly because the letterless form is a prefix of every lettered same-day
form. Regex: `^\d{4}-\d\d-\d\d[a-z]?$`. Do not parse them as dates.

**The one deliberate redundancy** is `closed`: the folder answers *whether*, the field
answers *when*. Lint asserts they agree. Everywhere else, one fact has exactly one home —
that is why there is no `status` field, no H1 title duplicating frontmatter, and no
`blocks` field (the reverse of `deps` is derived, and a hand-maintained inverse is the rot
machine this whole design exists to delete).

### 3.2 Frontmatter parsing and canonical writing

Do NOT use a YAML library, and do not write a general YAML parser. The frontmatter is a
deliberately constrained subset:

* delimited by a line `---` at the very start of the file and the next line that is
  exactly `---`;
* each line is `key: value`, one per line, no nesting, no multi-line scalars;
* a value is either a plain string (unquoted, may contain spaces and `:`; take everything
  after the FIRST `": "` or after `":"` at end-of-line) or a flow list `[a, b]`;
* everything is a string as far as the script is concerned. Never coerce to date or int.

The canonical writer emits the fifteen keys in the fixed order, `[]` for empty lists,
`key:` with nothing after the colon for empty scalars, and one trailing blank line before
the body. Round-tripping an untouched file must be **byte-identical** — test that.

Rationale to preserve in the docstring: a real YAML library reorders keys, rewrites quote
styles, and coerces `2026-08-20` into a date object, producing diff churn and format drift.
Thirty lines of hand-parsing buys byte-stable round-trips and zero dependencies, and the
files stay valid YAML for any other reader.

### 3.3 Body sections

* The summary paragraph, `## Traps`, and `## Read first` are **replace-on-touch** — a
  session that works the item rewrites them. The script never edits them.
* `## Log` is **append-only**, and the script is the only writer. `comment` and `close`
  append `### <session-key>` followed by a blank line and the message. If an entry for the
  same session key already exists, append the new text under it rather than creating a
  duplicate heading.
* Missing sections are created on demand at the right position (Log always last).

## 4. Operations

CLI: `python task.py <op> [args]`, run from anywhere; the tasks dir is located by walking
up from `--dir` (default: cwd) looking for a `tasks/config.json`. Every read op takes
`--json` and emits machine-readable output on stdout.

### Read ops

| op | behavior |
|---|---|
| `board` | The session-start view, bounded by `BOARD_MAX_LINES`. **`tasks/BANNER.md` verbatim first, and the op REFUSES if it is missing or longer than `BANNER_MAX_LINES`** — a default banner would be a session-start that looks complete and carries nothing. Then: NOW item (id, title, `brief`, size, moved) plus its summary paragraph; NEXT rows each with their `brief`; a ready count; open counts per pri; staleness warnings for NOW/NEXT whose `moved` is old. `--json` carries the banner under a `banner` key. Never writes a file. |
| `list [--pri P] [--label L] [--parent ID] [--closed] [--all] [--limit N]` | Filterable table: id, pri, size, title, deps, moved. Closed deps annotated so a stale dep is visible. Default scope is OPEN only, sorted NOW-first then by id. **Capped at `LIST_LIMIT` rows, and the truncation is ALWAYS announced** — `showing <n> of <N> task(s) (--limit 0 for all, --limit N for N)`. The cap exists because an uncapped table ran to most of a board-sized read (measured 2026-08-21: 94 lines against 91 open tasks) for the view that was supposed to be cheaper than the board; the announcement exists because `20 task(s)` is a *true* sentence that leaves the reader believing they have seen the backlog, which is this repo's house failure mode reproduced inside the tool built to cure it. Pinned by `tests/test_tasktool.py::test_list_truncation_is_announced_and_json_is_not_cut`, on every path including `--parent`. **The default does not apply to `--json`** — a machine surface that drops rows by default breaks consumers silently — but an explicit `--limit` is honoured on both. |
| `show ID [--section NAME] [--head N]` | Frontmatter, then **the Log NEWEST FIRST, above the body** (since 2026-09-06c; the file itself stays append-only, newest last, because `git diff` on an append-only Log is readable), truncated to `SHOW_LOG_HEAD` entries with the truncation ALWAYS announced (`showing k of N entries; --head 0 for all`), then the summary and the other `##` sections in file order. Why the view is inverted: a session's trial feedback found the top of a long task was its OLDEST state — `P6`'s summary still called the branch untested weeks after its Log recorded it tested — and a reader takes the top as current. `--section summary|log|<slug>` prints one slice (unknown names are refused with the list of what the task has); `--head N` bounds the Log (`0` = all; negative refused). `--json` is never cut and carries `log` (newest first, `{session, text}`), `sections`, `summary`. Also print derived facts the file cannot carry: which open tasks list this one in `deps` (the computed reverse edge), which tasks list it in `related` (incoming links, open and closed), and children if it is a parent. Pinned by `tests/test_tasktool.py::test_show_renders_the_log_newest_first_and_never_touches_the_file`. |
| `ready` | Open tasks whose `deps` are all closed (or empty), restricted to `NOW`/`NEXT`/`LATER` — `HOLD` and `SOMEDAY` are excluded by definition. |
| `lint` | Section 5. Exit 1 on any violation, 0 when clean. |
| `counts` | The corpus size, measured: parsed open/closed/total, the same counts taken independently off disk, distinct ids, retired ids, and the zero-headroom value `min_tasks_parsed` should carry. Added because a count restated in prose rots — `task.py`'s own docstring said 83 against a live 99 — so this is the one machine-checked home for the figure, and it is printed, never written back (a floor a tool can raise by itself re-seals every time it is breached). |

### Write ops

Every write op rewrites frontmatter canonically and sets `updated` to the current session
key as a side effect; a PROGRESS op sets `moved` too (section 3.1's per-op table). The session key comes from `--session KEY`; if omitted, derive
today's date (`YYYY-MM-DD`) and, if a task already carries that exact key, do NOT
auto-letter it — just reuse it. (Letter suffixes are a human act tied to the session
ledger.)

| op | behavior |
|---|---|
| `new TITLE [--id ID --brief --pri --size --deps --related --labels --parent --source --body FILE]` | Allocate the next id by SCANNING open + closed + retired registry for the max integer suffix on the configured prefix, then +1. Never store a counter — counters go stale. **`--id ID`** overrides that allocation, refusing an id that is live, retired, or malformed: without it every task joins the `id_prefix` series, so a piece of build work is minted into the series everything else cites as a *finding*, and since the id is the address the miscategory is permanent. Create the file with the standard body skeleton. Print id and path. **Then ratchet `min_tasks_parsed` to the measured file total (since 2026-09-06, `task.py::ratchet_min_parsed`)** — `max(floor, files on disk)`, a one-integer substitution on the raw config text, printed as `floor min_tasks_parsed N -> N+1`. It never LOWERS the floor, so a breach (floor above the corpus, i.e. lost files) stays red; it only closes headroom, which is the defect. The manual step was forgotten in three consecutive sessions (config.json's provenance string names each); `counts` still only prints the value, because a tool that sets the floor to whatever is on disk would also seal breaches. |
| `set ID FIELD VALUE` | Only `title`, `brief`, `size`, `labels`, `related`, `parent`. `id`/`created`/`source`/`moved`/`updated` are IMMUTABLE, and `closed`/`pri`/`deps` have dedicated ops whose rules a plain assignment would skip. `related` is whole-list assignment rather than add/rm because, unlike `deps`, no edge of it depends on the rest of the graph. **Positional, not flags** — `set P3 --title x` is the natural typo given every other write op here takes `--flags`, so the flag forms are declared and refused with the working command line rather than left to argparse's `unrecognized arguments`. |
| `promote ID PRI [--demote ID2 PRI2]` | Change `pri`. **Refuse at write time** if the result would violate the NOW=1 / NEXT<=3 budget, naming the offending rows and telling the caller to pass `--demote`. With `--demote`, apply both changes atomically (write both files, or neither). Mechanical refusal beats a doc warning. |
| `dep add ID DEP` / `dep rm ID DEP` | Existence check and cycle detection at write time; refuse on either failure. |
| `comment ID -m TEXT` | Append a dated Log entry. `-m -` reads the message from stdin (for multi-line). This is the workhorse: cheap appends are what fix "completed but never marked". |
| `touch ID` | Record progress with no message: bump `moved` and `updated`. For "worked it, the detail is in the session ledger". |
| `ack ID -m TEXT [--since DIGEST]` | **REFUSES anything but `source: board`** (naming `comment` as the remedy): for a source `sync` cannot read there is no digest to stamp, so the old fall-through printed "acked", bumped `updated`, logged that the drift was reviewed, and recorded the acknowledgement nowhere a later run could read — the next `sync` reported the identical drift, and the session that handled it had a Log entry proving it did. **One exception since 2026-09-06c: a `source: hand` task whose id HAS a board row is ADOPTED** — `source` flips `hand → board`, the row's digest is stamped, the Log entry records the flip. It is the one write to `source` after `new`, allowed on the `acked-no-row` argument (the value records a fact this run observed, not a value a human supplied), one direction only; hand-with-no-row and path sources are still refused. Why: three of the nine 2026-09-06b drifts (`TK55`, `TK54`, `P21`) were hand-filed tasks that acquired rows later, and the only exit was hand-editing frontmatter (`tests/test_tasktool.py::test_ack_adopts_a_hand_task_that_has_a_row`). Otherwise: bump `updated`, leave `moved` ALONE, append a Log entry, and re-stamp `source_hash` to what the source says now -- or to the `acked-no-row` sentinel when the source names no row for this task, which is how a standing `CORPUS-ONLY` item stops reddening `sync --check` forever without ever going unnamed. **Message REQUIRED** -- the interesting `ack` answers a `BODY` report ("the board block was reworded; the task prose is still accurate"), and without the reason the digest advances silently and the judgement is lost. Never bumps `moved`: acknowledging drift is housekeeping, not progress. **`ack` must be a session's LAST step** — it stamps what the source says AT ACK TIME, so acking and then editing the source records an acknowledgement of text nobody reviewed; pass `--since DIGEST` (what the drift report showed) and a mismatch is announced loudly on stderr. It warns rather than refuses because the source moving is usually the acking session's own edit and the ack is still correct; what is not acceptable is that it happen silently. See SYNC-SPEC.md section 3.1. |
| `close ID -m TEXT` | **Message REQUIRED** (outcome evidence, per the repo's sabotage culture). Stamp `closed`, append the Log entry, move the file to `closed/`. Then PRINT (a) which open tasks just became ready because this was their last open dep, and (b) if it has a `parent`, whether that parent now has zero open children — the archive sweep, computed instead of remembered. |
| `reopen ID -m TEXT` | Inverse. Message required. Clears `closed`, moves back to `tasks/`. Re-checks the pri budget and refuses if reopening would break it. |

Files are NEVER deleted. "Wontfix" is a `close` with a reason in the message.

### The reconciliation op

`sync` is neither a read op nor a write op and has its own contract in
`.scratch/tasktool/SYNC-SPEC.md` (**not tracked** — deliberately NOT written as a link,
because a link that resolves to nothing is the rot this repo lints for; its results are
recorded in [`history/tasktool-proof-2026-08.md`](history/tasktool-proof-2026-08.md)):
it reconciles the corpus against `HANDOFF.md`, reports
drift in six buckets, mints tasks for rows that have none (`--create-new`, the only mode
that writes, and it only ever ADDS), and emits the mechanical fixes as pasteable
`--mechanical` lines. **It has no delete path and no `--force`**, which is the whole
reason it replaced `migrate.py --rebuild`. `ack` above is its companion: the verb that
acknowledges a reported prose drift without claiming progress.

Deliberately absent, and each is a headstone in the distributed-bug-tracker graveyard:
`edit` (that is your editor), `search` (that is grep), assignees, due dates, time
tracking, kanban rendering, a web UI, an MCP server.

## 5. `lint` checks

Each check must name the offending file and id, and say what to do about it. **Thirteen
checks** as of 2026-09-06c (check 11 warns rather than fails); the count is printed by `lint`
itself -- `task lint: clean (N checks, M task file(s) parsed)` -- so no other surface
should restate it. Checks are cited by NUMBER, so a new check is APPENDED, never
inserted.

1. every `*.md` under `tasks/` and `tasks/closed/` parses (delimiters present, all
   fifteen keys present, no unknown keys) — excluding `NON_TASK_MD` at the top level;
2. ids unique across open + closed; no id appears in `retired-ids.txt` AND as a live file;
3. filename starts with `<id>-` and ends `.md`;
4. `pri` in the enum; `size` in the enum; `brief` one line, no `|`, unpadded, within
   `BRIEF_MAX` (`task.py::brief_problem`, shared with `set`/`new`/`validate_record` so a
   write op can never refuse a record lint calls green, or launder one it calls red);
   `created`/`moved`/`updated` well-formed
   session keys; `created <= moved <= updated` under string comparison; `source` is
   `board`, `hand`, or a well-formed repo-relative path (shape only -- never checked
   against the disk); `source_hash` is empty, 12 lowercase hex, or the `acked-no-row`
   sentinel, and is empty whenever `source` is `hand` (a hand-filed task has no source
   block for a digest to be OF and no source that could be missing a row for it, so
   either non-empty value there is a state no write path can produce);
5. exactly one `NOW` and at most three `NEXT` among OPEN tasks;
6. every id in `deps` **and every id in `related`** resolves to a real task (open or
   closed); no cycle in the deps graph; `related` refuses self-reference and is
   deliberately NOT cycle-checked;
7. `parent` resolves; no cycle in the parent graph; no closed parent with open children;
8. `closed` non-empty IFF the file lives under `closed/`;
9. every label is in the config's declared vocabulary;
10. **instrument control** — assert that at least `min_tasks_parsed` task files were
    actually parsed, where that floor is the MEASURED live count with zero headroom (the
    way `verify.sh` sets `MIN_CONF_ALL`), **and** that the number of files the scanner
    offered equals an independent per-directory recount of `*.md` on disk. A lint whose
    parser has gone blind passes forever; this is the same defect
    `handoff_lint.check_doc_links` guards with `MIN_DOC_LINKS`, and it is non-negotiable.
    The floor alone is not enough: it re-accumulates headroom as the corpus grows, which
    is why the recount (growth-invariant, and it names which directory went dark) is part
    of the same check. A missing floor is a violation, not a default.

11. **parent DEPTH > 2 -- a WARNING, never a violation.** Two levels covers every real
    grouping here (`R6` over its 19 children is the deepest anything has needed), and
    each extra level costs the reader every session and forces a housekeeper to make a
    judgement call about where a task attaches. But a third level is not WRONG, it is
    unusual: a hard fail would mean a session that legitimately needs one either fights
    the gate or -- far more likely -- flattens the tree to get green and loses the
    grouping. **Growth should be visible, not prohibited.** The warning prints on every
    run, red or green, is carried in `--json` as `warnings`, and never touches the exit
    code. There is no flag to promote it to fatal: a warning that a flag can promote is a
    warning nobody promotes.

12. **`tasks/BANNER.md` exists, fits `BANNER_MAX_LINES`, and its first line carries a
    session key.** `board` already refuses without it, so this looks redundant and is
    not: `board` refuses at READ time, which protects whoever runs it, while `lint` is
    what a session runs before committing. The failure this catches is the session that
    promoted a row, wrote no banner, and left the NEXT session's first command broken —
    a refusal issued only to the victim is issued too late. The first-line rule is
    deliberately weak (a well-formed key, nothing more): nothing can distinguish a banner
    rewritten this session from one whose date was edited, and a check that pretended to
    would be the fail-by-passing shape. What it does catch is a banner that is simply old.

13. **`sync --check` drift is a lint violation** (2026-09-06c, Phase B′ prerequisite 3,
    `task.py::check_board_sync`). Three outcomes: no `HANDOFF.md` at or above the tree →
    pass (a fixture tree has no board; that is not drift); a board file with NO row
    table → violation naming the cutover (that is the post-cutover stub, and this check
    retires WITH `sync`, `ack` and `source_hash` at the Phase B′ cutover — until then a
    missing table is a deleted one); drift > 0 → one violation carrying the rendered
    `sync` report, so the ledger's `task lint:` line is the evidence. Why: 2026-09-06b's
    `sync --check` found NINE one-armed updates across a fortnight of ledger entries
    that all read `task lint: clean` — `sync --check` was a separate verb nobody had to
    run. Pinned by `tests/test_tasktool.py::test_lint_check_13_reports_board_drift_and_a_tableless_board`
    and its sabotage `test_sabotage_bprime_check_13_can_go_blind`.

## 6. `tasks/config.json`

**⚠ THE BLOCK BELOW IS A SHAPE, NOT A CONFIG. Do not copy its values.** All three of
`id_prefix`, `min_tasks_parsed` and `stale_days` were copied verbatim out of this
example into the shipped config on 2026-08-21, and all three were wrong there: `"T"`
minted `T1`, which is already the set-engine correctness theorem; `5` was a floor far
below the live corpus, so deleting the entire `closed/` archive — the MAJORITY of the
files — still linted clean at exit 0 (the literal transcript, with the figures as they
stood that day, is in `fix-tool.md` under BLOCKER 1); and `14` had no derivation
anywhere. This file states no corpus figure of its own: run
`python task.py --dir <tree> counts`, which is the single machine-checked home for
every one of them. The live values, and how each was measured, are in
`sandbox-migrated/tasks/config.json`'s `_provenance` block — the generator is
`migrate.py::config_blob`, which measures the floor from the corpus it just wrote, and
`measure_prefix.py` / `measure_stale.py` re-derive the other two. `id_prefix` and
`min_tasks_parsed` have NO defaults in `task.py`: a missing prefix is a refusal at
`new`, a missing floor is a lint violation, because a guessed floor is a floor with
headroom.

```json
{
  "id_prefix": "<measured: zero \\bPREFIX\\d+\\b hits in any first-party file>",
  "labels": ["formal", "perf", "docs", "infra"],
  "budgets": {"NOW": 1, "NEXT": 3},
  "min_tasks_parsed": "<measured: the live file count, ZERO headroom (task.py counts)>",
  "stale_days": "<judgement, inside a measured band; write down the band>"
}
```

Labels are a **closed vocabulary** enforced by lint. An open vocabulary yields
`formal` / `Formal` / `lean` / `proofs` within a month and no query is trustworthy.

`id_prefix` governs only NEWLY minted ids. Legacy ids (`P3`, `HS-5`, `R6`, `ZT-P0-1`,
`B1`, `AW-1`, `LT-1`, `DW-1`, `SD-1`, `GS-1`) must keep working verbatim as addresses —
ids carry forward forever and are never reused. So id VALIDATION is permissive
(`^[A-Za-z0-9][A-Za-z0-9-]*$`) while id ALLOCATION is strict (prefix + integer).

## 7. Migration (`migrate.py`)

> **Superseded for ongoing use (2026-08-21).** The corpus stopped being a derived
> artifact the moment tasks were filed that no source document contains, so
> `migrate.py --rebuild` is guarded and reconciliation (`SYNC-SPEC.md`) is how the corpus
> stays current. `migrate.py` still describes how the tree was BOOTSTRAPPED, and it still
> emits the ten-field schema -- it has never been widened to the current schema, because
> widening a tool nobody may run buys nothing and running it is the one thing the guard
> exists to prevent. **Do not read this paragraph as a statement of the live schema**:
> section 3.1 is the schema, and the field count has moved twice since (ten -> thirteen
> in place by `migrate_schema13.py`, then thirteen -> fourteen, then `brief` on
> 2026-08-29d), each time by a one-off script that adds keys to existing files and never
> rewrites a body. The gap between `migrate.py`'s schema and the live one only ever
> widens, which is another reason not to run it.

A separate script, also under `.scratch/tasktool/`, that builds a `tasks/` tree from the
main repo's current records. It READS the main repo and WRITES only into
`.scratch/tasktool/sandbox/`. It must be re-runnable: wipe the output dir and rebuild.

Inputs and what to take from each:

* `HANDOFF.md` — the board table gives the open rows (id, title, pri, size, deps,
  moved); how many there are is whatever the board holds on the day you run it, and
  `migrate.py --dry-run` reports the figure for that run rather than promising one here.
  The pointer link in the item cell becomes the first line of `## Read first`.
  The `NOW`/`NEXT` item blocks (the `### <id>` sections) carry summary prose, trap
  paragraphs, and an explicit "Read first:" list — split those into the three body
  sections nearly verbatim. Rows below `NEXT` get no block, so their body is the summary
  line plus the pointer.
* `HANDOFF.md`'s "Closed ids stay retired" line — retired ids.
* `docs/history/session-log.md`, `formal/history/PROOF_STATUS.md`, and
  `docs/history/handoff-status-2026-07.md` (which holds the reconciled `ZT-*` disposition
  ledger) — every historical id ever used, for `retired-ids.txt`. Over-collecting is
  safe and correct here: the registry exists to make re-minting an old id impossible.
* Closed items that have a real disposition recorded (e.g. `P1`, `P2`, `HS-1`, `HS-3`,
  `B1`) may become files under `closed/` with a one-line Log entry citing where the
  evidence lives. Everything else stays a bare line in `retired-ids.txt`.

`created` for a legacy row is unknown; use its `moved` value and note the approximation in
the Log entry. `B2` becomes a parent task (it is described as "the historical grouping of
P8 + P9"), with `P8` and `P9` carrying `parent: B2` — that exercises the rollup path.

Migration output must pass `task.py lint` with zero violations. That is the acceptance
test.
