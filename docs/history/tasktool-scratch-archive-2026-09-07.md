# The `.scratch/tasktool/` archive — what the deleted directory proved

**FROZEN 2026-09-07 — provenance, not a living document.** Status lines below are
as-of-then and several may now be false; live state is the tree (`task.py show <id>`)
and `formal/HANDOFF.md`. Corrections are appended dated at the top, never edited in.

**Provenance.** Transcribed 2026-09-07 from `.scratch/tasktool/`, the gitignored build
directory of the task tool, immediately before that directory was deleted. It held ~120 MB
across ~30 markdown records, a dozen scripts and eleven working subdirectories. This file
is the load-bearing extract, written to the same rule the directory itself kept failing:
**anything recorded only in `.scratch/` is already lost.** It follows the precedent of
[`tasktool-proof-2026-08.md`](tasktool-proof-2026-08.md), which transcribed `PROOF4.md`
and `sabotage-log.txt` the same way on 2026-08-29d.

Everything the tool itself became is tracked and is NOT repeated here: the contract is
[`../tasktool-spec.md`](../tasktool-spec.md), the code is `scripts/task.py`, the tests are
`tests/test_tasktool.py`, the trial is
[`../tasktool-trial-protocol.md`](../tasktool-trial-protocol.md). What is here is what
existed nowhere else.

---

## 1. Why the directory could not simply be deleted

Nine tracked files cited it by section, as evidence rather than as background. Those
citations are the reason section 2 exists: each transcribes the referent so the citation
still resolves to real content. Section 3 carries decisions that were made in the scratch
records and never written into the spec. Section 5 carries the findings that were **never
fixed** — the most valuable thing in the directory, and the part that would have died
silently.

No tracked file had a live *dependency* on it: `git grep -E "(open|Path|import|sys\.path)[^#]*\.scratch"` over `*.py`/`*.sh` returned zero hits (verified 2026-09-07). Every
reference was prose.

---

## 2. The cited sections, transcribed

### 2.1 `COVERAGE.md` §C5 — `HS-5`'s scope, measured

Cited by [`tasktool-findings-2026-08-29.md`](tasktool-findings-2026-08-29.md) `:282` and
`tasks/closed/TK49-*.md:39`. `COVERAGE.md` was a `[dated: 2026-08-21]` frozen record
consolidating a 14-bucket markdown sweep and a 10-shard task-file verification.

> `HANDOFF.md:57` files `HS-5` as **"six always-living docs declare no liveness state."**
> The sweeps collectively named at least nine; COVERAGE.md flagged that as "worth checking
> against `HS-5`'s scope." Checked, by reading the first 8 lines of each for
> `LIVING`/`FROZEN`/`ACTIVE-PLAN`. **Eleven have no banner:**
>
> `formal/CORRESPONDENCE.md`, `formal/ARCHITECTURE.md`, `formal/FINAL_REVIEW.md`,
> `formal/SEMANTICS.md`, `formal/HANDOFF.md`, `docs/gate-runbook.md`,
> `docs/specs/wildcard-materialization-spec.md`, `docs/specs/set-engine-spec.md`,
> `docs/specs/graph-boolean-ivm-spec.md`, `benchmarks/results/BASELINE_2026-07-13.md`,
> `benchmarks/results/R6_PROFILE_2026-08-17.md`.
>
> `HS-5` undercounts its own scope by at least 5 (some may be deliberately exempt from
> `docs/README.md` sec 2 -- that adjudication is the work, and it has not been done). This
> is `ZT-P3-5` (a stale figure in a durable place) recurring in a board row filed yesterday.

### 2.2 `COVERAGE.md` PART 2 — the sharding was broken, and read green

Not separately cited, but it is the strongest single piece of evidence the directory held
for this repo's declared house failure mode, and `docs/subagent-fanout-runbook.md` is its
living home.

Ten agents were each given a shard of a 98-file corpus. Measured afterwards: distinct
files checked **90 of 98**; never checked **8**; checked more than once **12** (9 twice, 3
three times); total file-checks claimed 98, actually 104. Shards 0,1,2,4,6,7 correct;
3,5,8,9 wrong. Three distinct root causes: shard 3 mis-indexed its middle rows and re-read
shard 2's files; shard 5 checked a superset of 16 files, so its "16/16 clean" was not
evidence about a 10-file partition; shards 8 and 9 drifted 0-based → 1-based mid-list.

**All ten shard reports concluded PASS or near-PASS, and nine reported zero violations.**
No shard cross-checked its file list against the manifest. The gap was closed by hand —
all 8 unchecked files read directly, all 8 clean — and the record's own verdict is the
line worth keeping:

> The substantive verification conclusion survives -- but it survives by luck, not by the
> instrument.

A second pass (`2026-08-21b`) proved the *partition* was sound in code
(`union missing: 0  union invented: 0  duplicated: 0  PARTITION: PROVEN`) and then found
that only **1 of 10 shard reports had actually been written to disk**: `files with a
report covering them: 10 of 99 (10%)`. The partition proof said nothing about whether any
agent opened the files. Same failure mode, one level up.

### 2.3 `PROOF.md` §2d — the `_ROW_ID` regex fix, reproduced

Cited by `tasks/closed/TK46-*.md:47` as "an independent reproduction by regex swap".

> The port claims it FOUND A LIVE HOLE in the inherited `_ROW_ID`. I tested the claim by
> citing an invented `R6-99` in the root ledger, then swapping the inherited regex back in
> under the identical sabotage:
>
> ```
> ported regex     FAIL: docs/history/session-log.md:30 cites board id 'R6-99', which
>                  is on neither the task tree nor tasks/retired-ids.txt. [...]   rc=1
> inherited regex  handoff_lint: clean (7 checks)                                 rc=0
> ```
>
> The hole is real and the fix is real.

⚠ Two things in the surrounding text are superseded and must not be carried forward as
live. The section's trailing `MIN_KNOWN_IDS = 99` sentence is stale — `PROOF2.md` §2
records that floor being **deleted** in favour of deriving it from
`tasks/config.json:min_tasks_parsed` at run time, and the constant was removed outright at
the 2026-08-29 cutover (`scripts/handoff_lint.py:670-691`). And the defect's line anchor
`scripts/handoff_lint.py:245` is historical: the widened regex sits at `:286` today, with
`:609` carrying the note that "`_ROW_ID` truncated `R6-99` to `R6`". `TK46` is closed.

### 2.4 `PROOF2.md` §1 — the 11/4/3 re-derivation

Cited by [`tasktool-findings-2026-08-29.md`](tasktool-findings-2026-08-29.md) `:277` and
`tasks/closed/TK48-*.md:34`. Derived from `docs/perf-round6-audit-2026-08.md` alone:

> * **Round-wide traps: 5.** Top-level bullets under `## Traps the numbers do not carry`:
>   `R6-1` ceiling, `R6-16` co-design, `R6-4(a)` unsound, `R6-11` inflated, `R6-10` cumulative.
> * **Land order: 11 ids in 10 steps**; `R6-10` has landed, so **10 remain**.
> * **Declined on an upper bound: 4** (`R6-15`, `R6-12`, `R6-14`, `R6-2` — and exactly four
>   `NOT MOTIVATED` verdict rows).
> * **Unreachable: 3** (`R6-3` = `R6-17`, plus `R6-13`).
> * 11 + 4 + 3 = 18, which is the audit's own "ALL EIGHTEEN"; `R6-19` was filed 2026-08-18
>   outside the audit.

And the finding that the corpus was right where the repo was wrong:

> The audit's own status banner (line 4) says *"ten recommended to land in a stated order,
> five declined"*, which contradicts the audit's own body (eleven ids in the order, four
> declines). Both splits happen to sum to 18, which is how it survived.

⚠ **Correction to two tracked citations.** `tasks/closed/TK48-*.md:34` and
`tasktool-findings-2026-08-29.md:277` both say PROOF2 §1 re-derived 11/4/3 "twice from the
audit body alone". It did so **once**; its second derivation is from task-file frontmatter
and yields 11 LATER / 3 HOLD / 5 closed. The genuine second from-the-source re-derivation
is `PROOF3.md` §3d, which no tracked row cites. The citations resolve to real content; the
word "twice" overstates what §1 says.

### 2.5 `PROOF3.md` §1a — the required 30-entry list, and J-26

Cited by `tasks/closed/TK51-*.md:59` as the authority for "the required 30-entry list".

> The required list is COVERAGE.md PART 1's **30 consolidated entries** (entry `U-17` is a
> block of 16 individually-numbered perf leads, so 45 individual items), plus the two repo
> bugs and the two extra items.
>
> | source item | task |
> |---|---|
> | `U-1` .. `U-16` | `TK1` .. `TK16` (1:1, in order) |
> | `U-17` = `R6-A1` .. `R6-A16` | `TK17` .. `TK32` |
> | `U-18` .. `U-30` | `TK33` .. `TK45` (1:1, in order) |
> | repo bug: `_ROW_ID` truncates `R6-99` to `R6` | `TK46` |
> | repo bug: `R6-6`'s target symbol moved | `TK47` |
> | extra: the perf audit's self-contradicting banner | `TK48` |
> | extra: `HS-5`'s undercounted scope | `TK49` |
>
> **Nothing on the required list is unaccounted for.** No item needed a "why none should
> exist" defence: all 49 are filed.

And §6 item 1, which is what `TK51`'s citation actually turns on — non-membership of the 30:

> **J-26 was dropped without an adjudication.** COVERAGE.md's own drop list says
> "**`J-26` is the one worth a second look before it stays dropped**" [...] It is not in
> the 30, so filing it was not required. But `grep -rn 'J-26\|dense-regime'` over the
> corpus and over `filing-log.md` / `notes.md` / `make_filing_plan.py` returns **nothing**:
> the second look was neither taken nor recorded as declined.

That negative grep is the load-bearing fact, and it was re-run against `filing-log.md`
during this transcription (2026-09-07): the only hits are three `TK32` lines about dense
ids. `TK51` is absent from the 50 filed rows by construction, which is what makes the
"filed rather than silently declined" adjudication sound.

### 2.6 `INTEGRATION.md` §5.2 — the board footer

Cited at `tests/test_tasktool.py:806`.

> **`ready` is not on the board's `next` footer**, though the board prints a ready count. A
> session that wants to pick *something other than* the NOW row is told the number and not
> the verb. Cosmetic; noted, not fixed, because it is a taste call and this session already
> changed board output twice.

It was fixed afterwards, and generalised rather than patched: `scripts/task.py:1995`
carries `NEXT_COMMANDS`, and `tests/test_tasktool.py::test_board_footer_names_every_advertised_verb`
asserts the property both ways. The cite resolves.

### 2.7 `fix-tool.md` BLOCKER 1 — the instrument control with 94 files of headroom

Cited by `docs/tasktool-spec.md:466` as "the literal transcript, with the figures as they
stood that day".

`min_tasks_parsed` had been copied verbatim out of the spec's *illustrative* block as `5`,
against a live corpus of 99 files. Deleting the entire `tasks/closed/` archive — the
majority of the corpus — still linted **clean, exit 0**:

```
BLIND PARSER on sandbox-migrated -> rc= 0
  stdout: task lint: clean (10 checks, 42 task file(s) parsed)
```

The corpus halved, 99 → 42, and nothing noticed. The fix was deliberately **a raw-total
floor plus an independent recount**, not an open/closed pair; the recount rationale
survives in tracked `scripts/task.py:460` and `:285-293` ("the recount says WHICH half went
dark"), and the sabotage is a permanent test,
`tests/test_tasktool.py::test_sabotage_live_blind_parser`.

Its two siblings, also cited from `docs/tasktool-spec.md:460-472`: BLOCKER 2, `id_prefix:
"T"` collides with the repo's Lean stage labels (`T1` is the set-engine correctness
theorem; `T` scored 686 first-party hits, `TK` scored 0); BLOCKER 3, `stale_days: 14` had
no derivation, which is what `measure_stale.py` was written to supply.

### 2.8 `inventory-formal.md` — the three cited MISSes

Cited from the **open** tasks `TK11` and `TK50`, and from `tasks/closed/TK9`.

- **MISS #2** (cited by `TK11`) — `ResidueV1.version` is gated by nothing formal, declared
  as projection `P7` in `formal/CORRESPONDENCE.md` §7.1. The label collides with the
  board's *theorem* id `P7` (`ttuStarFree` parts (iii)+(iv)) — a state-gate projection
  label, not a task id. The doc concedes: "unlike P1–P6, where an argument recovers the
  dropped information… there is simply nothing on the Lean side to compare against…
  Modelling it remains open and is a real, if small, widening." I7 is pinned only by
  `tests/` paranoia runs; `Inv` has no clause for it.
- **MISS #4** (cited by `TK50`) — the `_bumped` residue-version dirty-key channel is a
  SECOND dirty-key source with no model (`ZT-P4-3a`). Consequence, stated plainly:
  "T5 (`runCascade2_no_abort` / `cascade2_drains`) is a claim about a WEAKER abort
  condition than the one Python ships… T5 therefore does not entail 'Python's abort is
  dead code'." A declared divergence, not a crash.
- **MISS #5** (cited by closed `TK9`) — `_reconcile_subject`, the per-subject cheap
  reconcile path, gained "promote-on-record" (2026-07-17) and escalation to the full
  reconcile (2026-07-26) with zero Lean model: "A per-subject path that can escalate to a
  full reconcile and can mutate node flags is a real algorithm, and none of it is in the
  model."

One residue from MISS #1 (`BL-2`) is worth re-checking and was never closed: three Lean doc
comments still assert the stale identity "`leaf_check` → `WildcardIndex.check`" (it is
`._check_internal` since the `BL-2` split) in `GraphIndex/CascadeStrata.lean` (module header
and `graphRecR`), `GraphIndex/ReconcileWrite.lean` (module header), and `Audit.lean`'s
W3d-2 narration. The instruction recorded at the time was "fold the comment fix into the
next Lean-touching session."

---

## 3. Decisions that were made here and never written into the spec

From `notes.md` (36 entries), `START-HERE.md`, `BRAIN-DUMP.md`, `SYNC-SPEC.md`. These are
the things a future session cannot re-derive from the code.

**The positive-claim retirement rule.** An id reaches `retired-ids.txt` only on a record
that POSITIVELY STATES the id is dead; every other outcome — including "the record does
not say" — produces a FILE. The original classifier was one predicate
(`disposition == 'closed'` → `closed/`, else → retired) and it buried fourteen live `R6-N`
ids plus `ZT-P5`. Dropping an id is recoverable; retirement is not. `classify()` was made
total over five outcomes and RAISES on an unrecognised disposition rather than falling
through. An `unknown` disposition became an open task on `HOLD` titled `UNDETERMINED
disposition:` rather than a refusal of the whole run — because a refusal makes migration
un-runnable until a human adjudicates, and the pressure is then to adjudicate *fast*,
"which is how a mixed ledger row gets called closed by someone who wants a green run."

**The unifying write-op rule, flagged at the time as something the spec should adopt and
still absent from it:** *a write op must never manufacture a state `lint` calls red, and
must never rewrite a record `lint` already calls red.* A tool whose successful writes
redden its own gate trains people to stop believing the gate. Two consequences: a
`--session` key may not sort before `created`, and the guard lives in `stamp_and_render`,
the one shared path, "so it cannot be added to six ops and forgotten on the seventh"; and
a write op refuses an already-invalid record rather than laundering it.

**No auto-repair of a corrupt record, and the lockout is accepted.** There is no correct
value to invent for `created: last tuesday`, and guessing destroys the evidence inside an
op run for an unrelated reason. "The file is red, open it" is a smaller rule than deciding
which of the other nine fields you still trust. READ ops deliberately bypass the writable
check: a viewer that refuses to display damage is useless exactly when it is needed.

**Closed records carry EMPTY `pri`/`size`.** Writing `LATER`/`?` onto 56 archive records
made `list --closed --pri LATER` answer with 56 invented facts that read as recorded ones.
A rank is a claim about what a session should pick up next, and a closed record is not
competing.

**Never auto-letter a session key.** `--session 2026-08-21b` must be typed, because a
letter suffix asserts that a distinct same-day session exists in `docs/history/session-log.md`,
and only a human knows whether that entry was written.

**Which field is a LIST comes from the KEY, not from `[...]` in the value.** Sniffing
brackets let `new "[wip]"` write `title: [wip]`, after which *every* op on the tree died —
a whole-store corruption from one title. Same class: a title is one line and length-capped.

**The land order is NOT encoded as `deps`.** Exactly one dep edge exists in round 6
(`R6-16` → `R6-7`, `R6-8`) because the audit states co-design as a *requirement*; the
recommendation-shaped ordering is printed as prose (`Position 4 of 10`). "A recommendation
modelled as a blocking edge is a lie `ready` would repeat every session."

**Traps live on the item that owns them, verbatim, never summarised onto the parent** — a
trap parked on the parent is invisible to the session working a child.

**`HOLD` means the absence of a MEASUREMENT, not the absence of a cost.**
`R6-3`/`R6-13`/`R6-17` show 0 calls in every profiled workload; the audit confirmed the
code does the inefficient thing. What they owe is a star/wildcard workload, and the
workload is the next step, not the patch.

**Dated transcripts are NEVER swept when a check count renumbers.** Rewriting a transcript
to say `11` would make it say something no run ever produced — falsified evidence, strictly
worse than dated evidence. "A transcript is stale the moment it is written; that is what
the date on it is for." Only the live assertion in the test suite is updated.

**The board is a QUERY, never a committed `BOARD.md`.** `HANDOFF.md` was simultaneously the
database and the session read, so the database was capped at what a session could afford to
read. A committed board file re-creates the disease.

**`related` is deliberately untyped** — no `supersedes`, no `duplicate-of`. `deps` and
`parent` earn their complexity because queries read them; a typed relation carries no query
semantics but does create a decision point where a model picks wrong, invisibly.

**The Sonnet-safety principle: every op is either mechanical or refusing** — the tool says
no (budget violations, backdated keys, empty messages, ambiguous parents) so the model never
has to judge. Corollary, stated as a standing rule: never ask a cheap model to re-rank, to
pick an ambiguous parent, or to paraphrase a trap. "An empty parent is a visible gap; a
wrong parent is invisible rot." Paraphrase had already cost real fidelity — the migration
truncated `HS-5`'s title into meaninglessness and mangled `B1`'s disposition string.

**End every housekeeping pass in a checkable artifact** — `lint`'s TRUE exit code and
`counts`, pasted literally, never a model's summary.

### From `SYNC-SPEC.md` — two design points that outlived the retired verb

Both are in force in `scripts/task.py:540-584` today.

**Provenance lives in the task file; there is NO `sync-state.json`.** A sidecar is a third
source of truth that can disagree with the corpus, does not survive `close`'s file move,
and — the dangerous part — when absent makes every task look hand-filed, so the reconciler
reports nothing and exits 0. "A check that fails by passing, which is this project's
declared house failure mode."

**`source_hash` compares the source against ITSELF over time, for EQUALITY only, and has no
`--source-hash` flag.** Comparing board prose to task prose "reports drift FOREVER, because
the two legitimately diverge the moment a session rewrites a body — and a check that can
never go green is as dead as one that never fires." The old text is deliberately not
cached: "the home of 'what did `HANDOFF.md` say last week' is git." A flag for the digest
"could only ever be a way to claim a reconciliation that did not happen."

And the reason `sync` had no delete path, which is why it replaced `migrate.py --rebuild`:
"Not a flag, not a `--force`, nothing… This is the whole point of the redesign and it is
not negotiable." It was asserted three ways — on the filesystem (bytes unchanged against a
vanished row), by inspection (a TOKEN-STREAM read pinning that every delete-like call
belongs to `op_close`/`op_reopen`, both halves of a MOVE), and by construction (`sync`'s
only write path was `op_new`).

---

## 4. The `migrate.py` manifest guard — design record, and its 2026-09-07 fail-open

`retire-migrate.md` was the design record for the `--rebuild` guard. It has no tracked
references and is the only written account of why the guard is shaped as it is. The hazard
it addressed: once the corpus became hand-maintained, "the script's core operation had
become: *delete work that exists nowhere else, then report success at rc 0*." Not
theoretical — the corpus went 99 → 149 files within the hour because another agent was
filing into it concurrently: "fifty hand-filed tasks were already standing in front of a
loaded gun."

The design points, each of which is reusable well beyond that script:

- **Identity is the CONTENT HASH, not mtime.** "A checkout, a copy or a `touch` moves mtime
  without changing a word, and a guard that cries wolf is a guard people pass `--force` to
  reflexively."
- **No manifest fails CLOSED.** The live corpus predated the mechanism, and "'I cannot tell'
  must not read as 'nothing to lose'." A manifest was deliberately NOT retrofitted — that
  would be a hand-write into the corpus, and the fail-closed branch already protects it.
- **The manifest lives at the out ROOT, not under `tasks/`,** because `task.py` recounts
  `*.md` per directory: "a guard file that moved either count would be a guard that breaks
  the thing it guards."
- **Layered exit codes:** rc 2 = you did not say `--rebuild`; rc 4 = you said `--rebuild`
  but the tree holds unreproducible work.
- **The instrument control was run, not assumed:** "A guard that refuses unconditionally
  would pass S1-S3 and be useless."

**The author's own declared residual risk, which turned out to be the right place to look:**

> The guard protects the corpus from THIS SCRIPT; it does not protect it from anything
> else. [...] The manifest records the *generating* run only. If someone hand-edits
> `migrate-manifest.json` to make a rebuild go quiet, nothing detects it — the guard is a
> safety interlock, not a security control.

### The fail-open, observed 2026-09-07

Tested against throwaway copies of the tracked `tasks/` tree; nothing live was touched.
Correct invocation, where `--out` names the tree's PARENT — the guard holds exactly as
designed:

```
$ migrate.py --rebuild --out <copy-of-repo-root>
migrate: REFUSED -- ... holds work this script did not generate.
migrate: this tree carries NO migrate-manifest.json, so nothing in it is provably
migrate: generated. ALL 168 of its task ids -- they WOULD BE DESTROYED by this rebuild:
rc=4, corpus files after: 171 (unchanged)
```

Aimed one directory deeper, at the corpus directory itself — which is literally named
`tasks/`, so this is the natural mistake:

```
$ migrate.py --rebuild --out <copy-of-tasks-dir>
migrate: manifest guard: ...\lmtest\tasks matches migrate-manifest.json exactly;
         nothing hand-filed or hand-edited is at risk.
rc=0, files: 171 -> 103
```

There was no manifest at that path. **The guard inventories `<out>/tasks/` while the wipe
deletes `<out>`.** With `--out` one level too deep the inventory finds an empty tree,
concludes "nothing at risk", and the wipe destroys the corpus — no `--force`, exit code 0,
success message. The scan path and the destruction path are different paths, and only one
of them was reasoned about.

That is why the file was neutralised rather than left under its own guard: on 2026-09-07
`.scratch/tasktool/migrate.py` had its entire body commented out behind a two-statement
refusal (rc 2 on every argv shape, verified against `--rebuild`, `--rebuild --force` and
`--help`), and the whole directory was deleted afterwards. The lesson generalises past this
script: **a guard must inventory exactly what the destructive operation will touch, not a
path derived from it.**

---

## 5. What was never fixed

The most valuable content in the directory, because none of it is inferable from the
tracked tree. Each was re-verified first-hand on 2026-09-07 before being written here.

1. **`formal/verify.sh` has no `task.py lint` step.** `INTEGRATION.md` §6 step 7 called the
   4g patch "not optional and not a nicety" and made it graduation condition 21;
   `START-HERE.md` required it to land in the same commit as the linter port;
   `PROOF.md` §8 item 1 and `PROOF2.md` §7 item 3 both list it as the open dependency.
   Verified 2026-09-07: `grep -c 'task\.py' formal/verify.sh` → **0**. The gate runs
   `[4a/6]`…`[4f/6]`. Only the NOW/NEXT capacity survived, indirectly, via
   `check_priority_capacities`'s tree fallback riding 4f; the other eleven `task.py lint`
   checks are enforced only through the pytest tiles. Independently corroborated at
   `docs/tasktool-trial-protocol.md:576`. **Reproduced, not merely read:** with a second
   row flipped to `NOW`, `task.py lint` fails rc=1 while `handoff_lint` reports
   `clean (7 checks)` rc=0.
2. **`count_guard.py` never graduated.** `REVIEW.md` blocker 6's structural fix — the only
   mechanical guard against a restated corpus count, which is `ZT-P3-5`, this repo's
   most-recurring defect class — existed solely in the deleted directory.
   `git ls-files | grep -c count_guard` → **0**. Its design rationale is preserved in
   section 6 below; the tool is not. No tracked check scans prose for a restated figure:
   `check_frozen_banners` checks banner *presence* only, and `check_min_parsed` polices the
   number itself, never restatements of it.
3. **Nothing resolves the `## Read first` pointers.** They are the only navigation surface a
   session gets. `REVIEW.md` §1c raised it; `INTEGRATION.md` note 26 claimed "this closes on
   graduation and only on graduation." It did not. Verified 2026-09-07:
   `scripts/handoff_lint.py::LINKED_DOCS` is eight files and `tasks/` is not among them, so
   the pointers in every live task file are checked by nothing.
4. **`scripts/handoff_lint.py:439` still carries the wording bug `AUDIT.md` T3 found.** The
   zero-`NOW` failure prints the `> 1` branch's sentence — "two of them is no ranking at
   all" — on a count that may be zero. Fixed in `task.py` (whose `:2443` documents the fix
   and pins it at `tests/test_tasktool.py::test_regression_zero_now_message_is_true_of_zero`)
   and never ported back to the sibling.
5. **The parent-census check is still unbuilt after three renumbering opportunities.**
   `notes.md` "Still open" item 1 named it the durable fix for `R6`'s hand-maintained census
   prose. Slot 11 went to `check_parent_depth`, 12 to `check_banner`, 13 to the retired
   `check_board_sync`. The prose has since needed one hand correction, which is the failure
   mode the check was meant to prevent.
6. **Thirteen open `R6-N` bodies cite a guarantor that no longer exists.** They read "the
   five round-wide traps (counted from that section at generation time, not restated:
   `migrate.py` refuses to build if the bullet count moves)". The count is still correct,
   but the named enforcement was in the deleted directory. The sentence now claims an
   enforcement that cannot run — exactly the rot `notes.md` "Still open" item 5 predicted.
7. **Nothing checks the `R6_SUB` transcription against its source.** 13 open `R6-N` bodies
   carry figures transcribed by hand out of `docs/perf-round6-audit-2026-08.md`; nothing
   notices when the audit is corrected. `R6-11`'s wrong "8×" was live in four places for a
   week. The proposed durable fix is the shape `verify.sh lean` already uses for
   `CORRESPONDENCE.md`: resolve each `### R6-N` heading and quoted figure at lint time.
8. **`missing keys -`** — an empty list still renders as a bare `-`
   (`scripts/task.py:1110-1112`). `notes.md` "Still open" item 2; cosmetic, and its twin
   was fixed.
9. **`AUDIT.md` F6, confirmed still true.** The "do not cancel `P4`" warning lives at
   `formal/history/leaf-family-split-scope-2026-08-05.md:1082` and
   `formal/history/PROOF_STATUS.md:247`, never on the board, so the migration could not
   carry it. Verified 2026-09-07: `tasks/P4-*.md` reads "## Traps / None recorded." A
   session trusting `task.py show P4` as self-sufficient still will not see it.
10. **Open `R6` rows carry sizes no source records.** They track the audit digest's grouping
    defensibly, but the derivation is nowhere stated — in a corpus whose closed rows carry
    an explicit paragraph refusing to invent `pri`/`size` for exactly this reason.
11. **`BRAIN-DUMP.md`'s schema-displacement rule was overruled without argument.**
    `START-HERE.md` recorded "13–14 is where the schema stops; the next field must DISPLACE
    one." `scripts/task.py:500` now has 15 fields — `brief` was added and nothing was
    displaced. The nominated displacement candidate, `size`, is still present and still
    queried by nothing. Carried forward as an open tension, not a bug.

Items 1–9 are filed as tasks; see the session ledger entry for 2026-09-07.

---

## 6. `count_guard.py` — the design, since the tool is gone

Six prose patterns over every declared record: task-file count, id-registry count,
open/closed split, N-file corpus, corpus-size assertion, and a floor restated outside its
config. Around them, three ideas worth more than the code:

**The escape vocabulary.** A fenced code block is evidence, not a claim, and is skipped. A
module-level constant assignment is the number's HOME, not a restatement. A `[dated:]` line
is a stamped historical observation. And a FROZEN banner earns its exemption only with
**both** a date stamp and a pointer at the live home — either alone is rejected, because a
date without a pointer tells a reader the number was true once but not where the true one
lives.

**A declared list, not a walk.** The scope is an explicit `DELIVERABLES` list *and* a
complementary check that every file beside it is either in the list or a failure. One half
catches a deleted record, the other catches an unscanned new one. A bare walk has no way to
notice that it stopped seeing something.

**The self-repairing baseline is the trap.** Recording an exemption is an assertion, not a
list edit, so `--record-frozen` is a separate verb a scan may never call. The reasoning is
worth quoting: a guard that regenerates its own baseline on every run cannot fail, because
whatever it finds becomes the new expectation.

Two of its own instrument controls fired during development and are the best evidence for
the pattern: a `MIN_DOCS_SCANNED` floor caught the walker mid-session seeing 21 records
instead of 22 (*"a guard that scans nothing passes forever. Fix the walk, not the floor"*),
and the FROZEN exemption was found matching **nothing at all** because it tested for a
literal substring where every real banner carried a `--dir` argument — after which the
exempt set was printed on every run including green ones, "because an exemption nobody can
see is how a check goes quietly blind."

**Why it was not ported here.** The rule is repo-agnostic and the tracked tree violates it,
but its data is worthless outside scratch: `frozen-exempt.json`'s 12 records all name
scratch files, and their hashed content is about a 99-file corpus. Its
`DELIVERABLES` list is a flat top-level scan, the wrong shape for `docs/`'s subdirectories,
and its exemption predicate is keyed on a convention (`[dated:]` + a `counts` pointer) that
the tracked tree does not use — the tracked convention is the
`FROZEN`/`LIVING`/`ACTIVE-PLAN` banner. A lift-and-shift would go red on dozens of
legitimate lines, which is precisely how a check gets deleted. Porting it is a real task
with its own sabotage cycle, not a rescue; it is filed as one.

---

## 7. What was deliberately not carried

Recorded so a later reader knows the omission was a decision:

- **`sync_sabotage.py` (14 cases) and `sync_accept.py` (57 assertions)** — unique, and
  retired with `sync` by the decision at `docs/tasktool-spec.md:367-375`. The one behaviour
  outliving the verb (nothing in the tool deletes a task file) is pinned by
  `tests/test_tasktool.py::test_close_moves_stamps_and_reports`.
- **All corpus counts from the scratch era** (83 / 98 / 99 / 149 files) — provenance only.
  Live figures come from `task.py counts`.
- **Every sabotage transcript for a script that no longer exists** — the `retire-migrate.md`
  S1–S5 runs, `migrate.py --dry-run` output, the `verify3/` and `proof/` script
  inventories. The design points are above; the shell output is not re-runnable.
- **The graduation checklists** in `INTEGRATION.md` §6 and `PROOF2.md` §7 — the graduation
  happened. Only their open dependencies survive, in section 5.
- **The per-shard narration** of how each shard mis-indexed, beyond the three root causes.
- **`notes.md` entries 15–21** (generator mechanics against inputs that die with the
  directory) and the `R6` figure entries, superseded by the live task files.
- **`START-HERE.md` §2 and §7**, `inventory-code.md`, `inventory-docs.md`, and the eight
  `fix-*.md` records — every repair they claim was located in tracked `scripts/task.py` or
  `scripts/handoff_lint.py`, or consciously superseded by a later tracked decision. The one
  exception, `fix-tool.md` BLOCKER 1, is transcribed at 2.7 above.
