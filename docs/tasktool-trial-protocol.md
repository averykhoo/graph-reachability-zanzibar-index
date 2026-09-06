> **CORRECTION 2026-08-30 — THE WINDOW WAS EXTENDED TO 2026-09-06, and DELETE is off the
> table** (user decision: *"we won't delete tasks, it'll run in parallel for another
> week"*). Everything below stands as written and is NOT edited — including §6's dated
> observations, which say "the 2026-08-30 verdict" and were true when written. Read every
> `2026-08-30` below as "the end of week one". What changed: the question is no longer
> keep-or-delete but **cutover-or-keep-both**, and §7.3's pre-registered week-two measures
> (`tree-sole-authority-spec-2026-08-29.md` §3) now have a week to run in. The delete
> branch of the exit plan is dormant, not deleted — §6's `2026-08-24c` finding that it
> destroys 49 tracked items is still the reason `TK53` matters.
>
> **ACTIVE-PLAN — the task-tool trial's measurement protocol, 2026-08-23 → 2026-08-30.**
> Written and committed BEFORE any trial agent ran. That ordering is the whole point: a
> rubric written after the results is a rubric fitted to them. Results append to §6; the
> protocol above it is frozen, and if it turns out to be wrong the correction is a dated
> append, never an edit (`docs/README.md` §2–3).

# Task-tool trial — measurement protocol

## 1. The question

Not "is the tool correct" — correctness is already pinned (41 tests, 22 sabotage cases,
4/4 live-corpus reds). The question is **is it HELPFUL**, which decomposes into two:

* **Does it reduce what a session must read before it can start work?**
* **Does it carry facts more accurately than the board does?**

Both are measured against the control that is already running: `HANDOFF.md`.

## 2. Why agents, and why not self-report

A session's own account of what it read is the least reliable instrument available. This
project has the receipts: during the tool's build, nine of ten verifier agents reported
success over report files that were never written to disk, and a separate pass silently
checked 90 of 98 files while reading green. Both were caught by the *next* pass, not by
themselves.

So nothing here is self-reported. Every metric is extracted from the agent's own
transcript JSONL after the fact, by script, from the recorded `tool_use` blocks. What an
agent *says* it read is not collected; what it *opened* is.

## 3. Design

Two arms, one prompt, identical in every word except the pointer:

| arm | told to use |
|---|---|
| **BOARD** (control) | `HANDOFF.md` — the live 260-line board |
| **TREE** (treatment) | `scripts/task.py` + [`docs/tasktool-trial-stub.md`](tasktool-trial-stub.md) |

Both arms get `CLAUDE.md`. Both are given the same five questions and told to answer
tersely. **Arms are compared WITHIN a model, never pooled across models.** The
model × system interaction is the interesting quantity — structure may help a weak model
more (it has less capacity to synthesise 260 lines) or less (it cannot drive a CLI) — and
pooling would average that away into a number describing neither.

Planned n: **6 per arm on Haiku, 3 per arm on Sonnet**. The Sonnet leg is DESCRIPTIVE and
will be reported as such; n=3 supports no inference and no p-value will be computed for it.

## 4. Metrics (all objective, all post-hoc from the transcript)

| id | metric | source |
|---|---|---|
| M1 | bytes returned by all tool results | sum of `tool_result` block lengths |
| M2 | tool calls made | count of `tool_use` blocks |
| M3 | **did it open `HANDOFF.md`** | `Read.file_path` / `Bash.command` / `Grep.path` scan |
| M4 | `scripts/task.py` invocations | same scan |
| M5 | wall-clock ms, subagent tokens | harness |

M3 is the metric the whole trial turns on, and it is the one no session could report
honestly about itself: **if the TREE arm keeps opening `HANDOFF.md` anyway, nothing was
saved regardless of what `board` can do.**

## 5. The rubric — five questions, answers fixed in advance

| # | question | correct answer | provenance |
|---|---|---|---|
| Q1 | The single `NOW` item: id and size? | `P3`, size `L` | both sources agree |
| Q2 | Which item must NOT be worked in parallel with it, and why (one clause)? | `P6` — same 38-module cone / textual collision on the same files | both sources agree |
| Q3 | How many `R6` perf items remain **to land**? | **11** | corpus right; `HANDOFF.md:47` says **9** and is WRONG |
| Q4 | How many always-living docs lack a liveness banner (`HS-5`'s scope)? | **11** | corpus (`TK49`) right; `HANDOFF.md:57` says **six** and is WRONG |
| Q5 | Name a standing trap belonging to NO single item. | `ttuDirect` must not be lifted in Lean; **or** `history/` status lines are frozen as-of-then | both sources carry it |

### ⚠ The rubric is BIASED TOWARD THE TREE, by construction, and the bias is declared

Q3 and Q4 were chosen *because* an audit on 2026-08-23 found the board stale on exactly
those two figures. They are a fair test of **"does this system carry current facts"** and
an unfair test of **"which system is better"**, and the score must be reported with that
sentence attached.

There is **no question selected to favour the board**, for a reason worth recording rather
than hiding: at protocol-writing time no fact was known that `HANDOFF.md` has right and
the corpus has wrong. That asymmetry is itself a (weak, n=1 audit) finding — but it means
the quality score is not a clean comparison and must never be quoted as one. If the trial
week surfaces a board-right/corpus-wrong fact, add it as Q6 in a dated append.

## 6. Results

### 2026-08-23 — PILOT, n=1 per cell. Ran to validate the harness; it did not survive.

Four agents, one per (arm × model). Metrics below are **harness-reported usage**, not
transcript-derived and not self-reported — see the instrument failure directly after.

| arm:model | tokens | tool calls | wall | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|---|---|---|
| BOARD:haiku  | 30,899 | 1 | 13.1 s | ✓ | ✓ | **9** ✗ | **6** ✗ | ✓ |
| BOARD:sonnet | 40,396 | 1 | 6.3 s | ✓ | ✓ | **9** ✗ | **6** ✗ | ✓ |
| TREE:haiku   | 39,897 | 15 | 86.6 s | ✓ | ✓ | **11** ✓ | **6** ✗ | contested |
| TREE:sonnet  | 41,099 | 6 | 28.9 s | ✓ | ✓ | **11** ✓ | **6** ✗ | ✓ |

**No statistics are computed and none should be.** n=1 per cell, and the token figures are
dominated by fixed system-prompt overhead rather than by reading, so the differences below
are observations, not estimates.

#### P1 — the instrument failed, and reported clean while doing it

All four pilot transcripts were **0 bytes on disk** while a fifth in the same directory
held 416 KB. `trial_metrics.py` printed `0 bytes, 0 calls, 0 board-opens` for every arm
and exited 0 — a table of false numbers that read like a result. **M3 is therefore not
obtainable this way**, and M1/M2 are not either.

Fixed the same hour: the script now REFUSES an unobservable subject instead of scoring it
zero, because a zero is indistinguishable from "read nothing", which is a real and
interesting outcome it would otherwise forge. Both halves were then demonstrated — the
refusal on the four empty transcripts, and a positive control on the 416 KB one
(`164147 bytes, 53 calls, 1 board-open, 21 task.py calls`), because a check that only ever
refuses is not evidence that it can measure.

#### P2 — Q3 is a dye marker, and replaces M3

`9` appears only in `HANDOFF.md`; `11` appears only in the task tree. The pilot separated
**4/4** on it. This is a *behavioural* tracer for which system an agent actually used, it
needs no transcript, and it cannot be produced by an agent's account of itself. It is the
cheapest honest substitute for M3 and the design should lean on it.

#### P3 — the TREE arm cost MORE, on both models

Haiku **+29% tokens** (39,897 vs 30,899) and **6.6× wall-clock** (86.6 s vs 13.1 s).
Sonnet **+2% tokens** (41,099 vs 40,396) and **4.6× wall-clock**. Both BOARD agents
answered after **one** tool call; the TREE agents needed 6 and 15.

This cuts against the tool's headline claim and is recorded before any explanation of it.
The explanation that is nonetheless probably true is §P5: the task was the board's shape,
not the tree's.

#### P4 — Q4 was wrong in BOTH arms, and the tree's failure is the more damning one

Every agent answered **six**. The tree *contains* eleven, in `TK49`, whose `parent` is
`HS-5` — and `show HS-5` prints `children: TK49` and `open children: TK49`, so the correct
figure was **one hop away and signposted**. The agents stopped at `HS-5`'s TITLE, which
still reads *"six always-living docs lack the liveness state…"*.

That is the board's disease inside the tree: a summary row carrying a figure its own child
corrects. The `R6` parent title was REBUILT from its children during migration for exactly
this reason; `HS-5`'s was not. Filed as trial finding, not fixed during the trial — fixing
it mid-measurement would destroy the measurement.

#### P5 — the task shape favours the board, structurally

Five shallow facts spread across five items is what a 260-line file is *good* at: one read,
everything in context, one tool call. The tree's claim is the opposite shape — deep
knowledge of ONE item without paying for the other 90. **This pilot measured the board on
its home turf** and the tree still won on the only discriminating question.

#### P6 — a rubric defect, recorded rather than quietly widened

`TREE:haiku` answered Q5 with *"An exit code piped through tail/tee reports the PIPE's
status"* — a genuine repo-wide trap belonging to no item, from `CLAUDE.md`'s four standing
footguns, but outside the two answers §5 pre-registered. It is scored **contested**, both
ways, and the rubric is NOT retroactively widened. Any widening is a dated append here.

### Revisions required before the full run

1. **Drop M1/M2/M3.** Use harness usage plus the Q3 dye marker.
2. **Change the task to a session shape** — "you are picking up the `NOW` item; list every
   trap that applies and what you would read first" — which is what the tree claims to be
   for. Keep a quiz arm so the two shapes can be compared rather than conflated.
3. **`CLAUDE.md` names both systems**, so neither arm is blind. Isolate arms in worktrees
   with variant contracts, or accept and report the contamination.
4. **Still no board-favouring question.** §5's declared bias stands unrepaired.

---

### 2026-08-24 — FULL RUN, 18 agents, session-shaped task per §7

All 18 completed. Metrics are harness-reported; scoring against §7.4 is my judgement and
is shown per-agent so it can be re-scored.

#### Cost

| | n | median tokens | range | median calls |
|---|---|---|---|---|
| BOARD:haiku | 6 | 30,805 | 30,756–30,841 | 1 |
| TREE:haiku | 6 | **27,314** | 25,494–28,899 | 4.5 |
| BOARD:sonnet | 3 | 40,370 | 40,351–40,446 | 1 |
| TREE:sonnet | 3 | **35,853** | 35,804–41,052 | 3 |

Haiku tokens, Mann–Whitney as pre-registered: **U=0, critical U=5, reject H₀ (p<0.05)** —
the two arms do not overlap at all. Tool calls separate the other way, also U=0: the board
arm answered in **one** call every single time, the tree arm needed 3–5.

Sonnet is descriptive by design (n=3): **U=3, no test**, exactly as §7.5 said in advance.

**The effect size is the same on both models — TREE is 88.7% of BOARD on Haiku and 88.8%
on Sonnet.** Difference in medians is 3,491 and 4,517 tokens. Per §7.5's warning, do NOT
read 11% as "11% less reading": a large fixed system-prompt floor sits inside both
figures, so the saving on the part that actually varies is considerably larger than 11%
and this design cannot say by how much.

#### Quality (§7.4, six points)

| arm:model | scores | median |
|---|---|---|
| BOARD:haiku | 5,5,5,6,5,6 | 5 |
| TREE:haiku | 5,5,5,5,5,5 | 5 |
| BOARD:sonnet | 6,6,6 | **6** |
| TREE:sonnet | 5,4,6 | 5 |

S1–S4 and S6 were earned by **17 of 18** agents. Every agent identified `P3`, the
FALSE-AS-WRITTEN human call, the §11.10 traps and the census hole. **Parity on content is
confirmed**, which was the hypothesis.

#### F1 — S5 is the board-favouring item §5 said did not exist, and the board won it

`P6 is NOT parallel-safe with P3` was earned by **5 of 9 BOARD** agents and **1 of 9
TREE** agents.

The cause is structural, not incidental. `P3`'s task file has `deps: []` and
`related: []`, so `show P3` never mentions `P6` — whereas on the board, `P6`'s row sits
four lines below `P3`'s in the same table and every reader scrolls past it. **The board
buys cross-item awareness for free by being one file; the tree deletes that benefit along
with the 260-line ceiling.** This is the real cost of decoupling and the trial found it
without being designed to.

It also repairs §5's declared bias: there is now a known fact the board conveys better.

**The tree has the mechanism and is not using it.** `related: [P6]` on `P3` would restore
the link, and `show` already computes and prints incoming `related` edges. Not applied
during the trial — repairing a subject mid-measurement destroys the measurement.

#### F2 — compliance was perfect; the tracer separated 17/18

No BOARD agent answered `11`; no TREE agent answered `9`. Zero arm violations. One
TREE:haiku answered **`4`** — a miss, not a crossover, and the only tracer failure in the
run.

#### F3 — one TREE:sonnet agent omitted `READ-FIRST` entirely

Scored 4/6. A format failure that occurred only in the tree arm, n=1, cause unknown.

#### F4 — the board arm is FAST and CONFIDENT and WRONG about R6

Every BOARD agent answered in one tool call, in 16–40 s, and **all nine of them reported
the stale `9`** with elaborate corroboration — one listed the nine ids, another added
"5 declined, 3 unreachable". A single authoritative file produces uniform confident
agreement, and when that file is stale the uniformity is worthless. **Nine independent
readings of a wrong figure are not nine pieces of evidence.**

---

### 2026-08-24b — F1 repaired: the `related`-edge sweep, 10 edges, 2 refused

F1 found the tree loses the cross-item awareness a single file gives away for free, named
`related` as the unused mechanism, and did not apply it because repairing a subject
mid-measurement destroys the measurement. The 18-agent run is complete, so it is applied
now.

⚠ **The SUBJECT HAS CHANGED. The cost and quality figures above are not reproducible
against this tree**, and a re-run must be reported as a different experiment, not as more
n. `show P3` in particular now names `TK6` that it did not name when the 18 agents ran.

**Criterion, fixed before the corpus was read**, because "add an edge wherever two ids
appear together" is how a navigation aid becomes noise. An edge is added where **(a)**
taking one item without knowing the other is a *mistake* — collision, duplicate, co-land,
or absorbed scope — **and (b)** at least one end's `show` output does not currently name
the other. The edge is written on the **blind** end only; `show` computes the incoming
half, so one write serves both directions (the `P3`→`P6` pattern).

| edge (written on) | why it is a mistake to be blind to it | blind end was |
|---|---|---|
| `R6-3` → `R6-13`, `R6-17` | `R6-17` is a LITERAL duplicate, `R6-13` the bulk twin; both name `R6-3`, `R6-3` named neither — and `R6-3` is the end that gets worked | `R6-3` |
| `R6-16` → `R6-7`, `R6-8` | co-design triple, "take all three in one session or none"; prose-covered at all three ends, edge added to harden it (see the finding below) | none |
| `TK20` → `R6-18` | `TK20`'s own trap says it **collides** with `R6-18` on the same table | `R6-18` |
| `TK25` → `R6-5` | overlaps `R6-5`; "do not double-count the win" — and `R6-5` is where the double-count happens | `R6-5` |
| `TK6` → `P3`, `P4` | scopes LIVE work, and says it "has never been folded into any board row's scope pointer". `P3` is the `NOW` item | `P3`, `P4` |
| `TK51` → `TK44` | "fixing `TK44` does not fix this" — closing `TK44` could over-claim | `TK44` |
| `TK8` → `P19` | "distinct from `P19` … do not merge them" | `P19` |
| `TK13` → `P18` | the adjacent concurrency gap `P18` is NOT | `P18` |
| `TK38` → `P16` | same shape as `TK8`/`P19` | `P16` |
| `TK47` → `R6-6` | `R6-6` carries the moved-symbol trap but does not name the row that owns fixing the audit **doc** (verified: `TK47` does not occur in `R6-6`) | `R6-6` |

Verified by running `show` at the blind end, not by trusting the write: `show R6-18` now
reports incoming `TK20`, `show P3` incoming `TK6`, `show R6-7` incoming `R6-16`,
`show R6-13` incoming `R6-3`, `show P16` incoming `TK38`. `lint` clean, 150 files.

#### S1 — two candidate edges were REFUSED, and one of them was a trap the corpus set

The generator was a mention scan: every open task body grepped for other ids. It proposed
**51 of 91** tasks — a ~5:1 noise ratio — because the `R6-*` land-order paragraph and the
"a cited symbol may have MOVED" trap are boilerplate repeated across the round.

Two survivors were refused on reading:

* **`TK11` → `P7` — a FALSE link the scan produced and `TK11` predicted.** `TK11`'s own
  trap reads *"The `P7` collision is real and it is how this looks captured when it is
  not. Lean's projection `P7` is not board id `P7`. **Do not resolve `P7` by grep.**"*
  The scan resolved it by grep. Adding the edge would have encoded the exact false
  capture the trap exists to prevent.
* **`TK19` → `P3`** — the same class: `` `P3` `` inside `` the `P3` `_residue_cache` `` is
  not board id `P3`. A second grep false positive of the id-namespace-collision shape.

Also refused as prose-covered at both ends and therefore adding nothing: `P3`↔`P14`
(absorption, settled and stated by both), `TK12`→`P3` (`P3` explicitly does not cover that
residual), `P8`/`P9` (the `B2` parent already carries the grouping), and every `R6-*`
land-order mention (a recommendation that lives once, in the parent).

**The transferable rule: a mention scan is a candidate generator and must not be the
adjudicator** — the same rule [`subagent-fanout-runbook.md`](subagent-fanout-runbook.md)
already states for fan-outs. Sixteen of the twenty-six candidates read were rejected, and
one of the rejects was a link the corpus had explicitly warned a grep would invent.

#### S2 — the sweep found a false claim about the format, in `R6-16`'s own trap

`R6-16`'s second trap explained at length why the co-design constraint cannot be encoded
and must live in prose in three files, ending: *"The vocabulary has no mutual edge (lint
rejects the cycle)."* That is true of `deps` and **false of `related`**, which §`related`
of [`tasktool-spec.md`](tasktool-spec.md) defines as untyped, symmetric-ish and
deliberately **not** cycle-checked. Corrected in place with a dated note. The constraint
itself still lives in the traps: `related` navigates and cannot say "simultaneity", which
is the same reason the spec refused typed relations.

Worth carrying because it is the trial in miniature: the tree grew a mechanism, and an
item written before it existed went on asserting the mechanism did not exist.

---

### 2026-08-24c — the tracer is spent, and the exit plan deletes 49 tracked items

Two facts the 2026-08-30 verdict needs, neither of them a re-run.

**T1 — the Q3 dye marker no longer separates the arms, so §7.3 cannot be reused.** The
tracer worked because `9` was board-only and `11` tree-only. The board was corrected to
`11` on 2026-08-24 (its `R6` row now re-counts from the children), so both systems now
carry the same figure and a tracer answer identifies nothing. §S1 already warned the
subject had changed; this is sharper — **the instrument itself is gone**, not merely the
baseline. A re-run needs a newly-minted board/tree discrepancy, and minting one on purpose
means deliberately leaving one tree stale, which is the thing the parallel-update contract
forbids. Recorded before anyone plans a re-run around a metric that cannot fire.

**T2 — a census, prompted by the user's question "are the `TK*` items tracked anywhere".**
They are, completely: **51 ids, `TK1`–`TK51`, no gaps**, 49 open and 2 closed. No board row
for any of them, by design — they are unranked, and the board's capacity budgets
(`NOW` = 1, `NEXT` ≤ 3) are the reason the tree was built.

⚠ **But the trial's exit plan destroys them.** `CLAUDE.md` says that if the tool is not
helping by 2026-08-30 the answer is "delete `tasks/`, `scripts/task.py` and this bullet,
which is one revert". Outside `tasks/`, exactly **one** `TK` id is mentioned anywhere in
this repo — `TK49`, in `HANDOFF.md`'s `HS-5` row. The other 48 open ones exist in no other
file, and `CLAUDE.md` says so itself in the `migrate.py` warning: they are hand-filed tasks
"that no source document contains". So the revert is one revert for the *tool* and a
deletion of 49 findings for the *repo*, and those are separable decisions that the current
wording bundles into one.

This is not an argument for keeping the tool. It is an argument that **the verdict has two
questions, not one** — *does the query beat the file* (what §§1–7 measure) and *where do
unranked findings live afterwards* (never posed). If the tool is dropped, the second
question still needs an answer, and the honest options are: promote the survivors to board
rows under a new grouping id, append them to a plain archive doc, or decide on the record
that unranked findings are not worth keeping. Deleting them without choosing is the third
option taken by default.

⚠ **The verdict itself is on neither tree.** No `HANDOFF.md` row, no task file — verified
by grep: `2026-08-30` appears in `CLAUDE.md`, this file, `tasktool-spec.md`,
`tasktool-trial-stub.md` and the session log, and in zero tracked items. The one deadline
that governs both systems is tracked by neither, which is its own small finding about both.

### 2026-08-29 — the eve of the verdict: findings rescued, the verdict filed, and the parallel-update contract is RED

No §6 append had been made since 2026-08-24c. Five trial-week sessions (`2026-08-24d`,
`2026-08-28`, `08-28b`, `08-28c`, `08-28d`) produced trial-relevant results that live only
in `docs/history/session-log.md`, contrary to this file's own banner (`:3`). This append
closes that gap and records the state one day before the deadline. **Everything below was
verified first-hand this session**, not taken from a subagent report.

**A1 — the two questions are now separated, and (b) is no longer destructive.** The 47 open
`TK*` findings were snapshotted to
[`docs/history/tasktool-findings-2026-08-29.md`](history/tasktool-findings-2026-08-29.md)
(FROZEN, dated, 47 entries). A DELETE verdict no longer destroys them, so question (a)
— *does the query beat the file* — can be decided on its merits. ⚠ This is
**safe-to-delete, not decided-what-to-keep**: T2's second question (promote / append /
write off) is still unanswered, and deleting without choosing remains the default third
option.

**A2 — the verdict is now tracked on both trees**, as `TK52` (board row + task file, same
session key `2026-08-29`). This discharges the `Still owed` line carried since 2026-08-24c
(`session-log.md:435`) and closes the finding at `:361-365` that *"the one deadline that
governs both systems is tracked by neither"* — which stood for five days and was true until
today.

**A3 — T2's census is superseded, and it was right when written.** Measured today:
**`TK1`–`TK51`, 51 ids, no gaps — 47 open, 4 closed.** T2 said *"49 open and 2 closed"*;
the difference is exactly `TK46` and `TK47`, both closed 2026-08-24 in `01a2916`, i.e.
hours after T2 was written. Recorded because the deletion figure is the number the verdict
turns on, and it moved by two in five days.

**A4 — "outside `tasks/`, exactly one `TK` id is mentioned anywhere in this repo" (`:346`)
is now FALSE, and the corrected shape is sharper.** Of the 47 open ids: **34 appear nowhere
outside `tasks/` at all**; 12 appear only in `session-log.md` and this file, i.e. as
narrative, which survives a revert as prose but not as tracked work; and **exactly 1
(`TK49`, `HANDOFF.md:60`) is on the board.** The original claim was true when written
(`session-log.md:407`) and was invalidated by later sessions naming ids in passing. So the
board-only reading holds — the board mentions one `TK` id — but "no other file mentions
them" does not.

**A5 — the read tally, the trial's central instrument, at n=7.** Counted directly from
`session-log.md`: **`board + HANDOFF` 6 · `board only` 1 · `HANDOFF only` 0** (`:78`, `:142`,
`:195`, `:242`, `:258`, `:365`, `:446`). Of the two comparison-task sessions the tool would
be expected to lose (24b, 24c), both read both — declared at the time. Of the **five
ordinary-work sessions** — the sample 24c said was under-sampled — **1 of 5** (`2026-08-24d`)
replaced the file read; the four most recent, all ordinary formal work, read both and gave
no reason. Coverage caveat: no session-log entry exists for 08-25, 08-26 or 08-27, so the
trial week is 8 sessions clustered on two days.

**A6 — ⚠ the parallel-update contract is RED on this tree, and it is the tree that is
stale.** `python scripts/task.py sync` reports **`sync 2 drift item(s)`**: `BODY P3`
(`90a1f8ce5f73 -> 36ebb5ee354e`) and `BODY R6` (`529bc2529a2f -> 12b064a9a482`). The four
2026-08-28* sessions rewrote those board rows without re-stamping the task bodies. `P3`'s
task *content* is current (its Log runs through `2026-08-28d`), so `P3` is digest drift.
`R6` is a real content divergence: the task title still reads *"11 to land, 4 declined, 3
unreachable"* while `HANDOFF.md:50` reads **"10 to land"**, because `R6-6` closed
2026-08-24d. That is the summary-row-contradicting-its-own-child disease (P4, then `HS-5`)
recurring a **third** time — this time inside the tree, on the row the tree's own
self-recount was cited as a win for.

⚠ **This is evidence for the verdict and was recorded before being reconciled.** CLAUDE.md's
trial design says *"a divergence between them at the end of the week is the evidence"*, so
it is written down here, permanently, in the form it was found. The reconciliation follows
in the same session; do not read the repaired tree as though the divergence had not
happened.

**A7 — friction log, first-hand, from one session of ordinary use.** Recorded at the
user's request (2026-08-29) because §§1–7 measured *reading cost* and never measured *cost
of operating the tool*, which A6 suggests is the recurring price if it graduates. These
are observed, not speculative; each cost this session real time or a real near-miss.

1. ⚠ **`--source hand` is a silent trap, and `ack` reports success while doing nothing.**
   A task filed hand-first that later gets a board row can never have its digest stamped:
   `source` is immutable (`task.py:493`, SPEC.md §3.1), and `ack` on a `hand` task prints
   `TK52 acked … source_hash unchanged (source: hand -- sync cannot read that source)` and
   **exits 0**, while `sync` goes on reporting the task as drift forever. That is an
   assurance step that fails by passing — this repo's declared house failure mode
   ([`sabotage-procedure.md`](sabotage-procedure.md)) — inside the tool built to prevent
   drift. The only remedy found was to delete the uncommitted file and re-file with
   `--source board`. **Suggested fix: `ack` on a `hand` task whose id has a board row
   should REFUSE, naming the re-file remedy**, rather than printing a success line.
2. **Editing a board row silently re-reds `sync`.** The row digest changes, so every board
   edit owes a follow-up `ack`. Hit twice in one session: `R6` was acked, the board row was
   then edited, and `sync` went red again. Operationally this means **`ack` must be the
   last step of a session**, after all board edits — nothing states that.
3. **`new` mints the next `TK` id and ignores intent.** The verdict row wanted a `TT-1`-style
   id and got `TK52`, so a ranked `NEXT` board row now carries an id from the series the
   protocol describes as *"unranked findings"* (`:341`). Board ids and task ids share a
   namespace, but only the `TK` series is mintable.
4. ⚠ **`ls tasks/` is the obvious census and it is wrong.** Closed tasks move to
   `tasks/closed/`, so a directory listing undercounts silently. This session nearly wrote
   a false finding — that the 2026-08-24c census was wrong in both directions — off exactly
   that mistake; the census was right, and `git ls-tree` plus the `id:` frontmatter was what
   settled it. Anything that counts tasks must count both directories.
5. **`list --parent R6` includes non-`R6-N` children** (`TK48`, `TK17`–`TK22`), so the
   natural re-count of "R6 children" over-reports unless filtered to the `R6-` prefix; and
   `list` silently caps at 20 rows without `--limit 0`. Both together are a live
   mis-count risk on the exact operation A6 shows the tree had already got wrong.
6. **Two minor CLI papercuts.** `set` is positional (`set R6 title "…"`); the `--title`
   form fails with a bare argparse error rather than a pointer to the right form. And the
   100-char title cap is enforced at `new` but is absent from `new --help`, so it is
   discovered by refusal after the body file is already written.

None of these bear on correctness — the 41 tests and 22 sabotage cases still pass, and
`lint`/`sync` were clean at end of session. They bear on **usefulness**, which is the
question actually being decided.

**A7 — resolution, 2026-08-29d.** All six fixed under Phase A of
[`tree-sole-authority-spec-2026-08-29.md`](tree-sole-authority-spec-2026-08-29.md); the
list above is left UNEDITED, because the friction as first found is the evidence and a
tidied version of it is not. Each fix is pinned in `tests/test_tasktool.py` and was
sabotaged before being believed.

| # | what changed | where |
|---|---|---|
| 1 | `ack` **REFUSES** any source but `board` (rc 2). The message branches: if the task HAS a board row it names the re-file remedy the log asked for, since `source` is immutable; otherwise it names `comment`, which is what the old fall-through was actually doing minus the word "acked". | `task.py::op_ack` |
| 2 | `ack --since DIGEST` — pass what the drift report showed and a moved source is announced loudly on stderr. Warns rather than refuses (the mover is usually the acking session itself); the *rule* is in `tasks/README.md` and `docs/tasktool-spec.md` §4. | `task.py::op_ack` |
| 3 | `new --id ID`, validated against live + retired ids, so a work row is never forced into the `TK` findings series. | `task.py::op_new`, `build_parser` |
| 4 | `tasks/README.md` states the layout and names `task.py counts` as the only census; `BANNER.md`/`README.md` are excluded from both scanners by name (`NON_TASK_MD`) so the two new files cannot themselves become the miscount. | `tasks/README.md`, `task.py::Store.md_paths`, `::disk_md_count` |
| 5 | Truncation was **already** announced with `--limit 0` named in the footer, on every path including `--parent` — re-verified, and now pinned by a test on a 21-row corpus rather than by reading the code. | `task.py::op_list` (already correct) |
| 6 | `set --title x` refuses with the working positional command line instead of argparse's `unrecognized arguments`; `field`/`value` became optional so the refusal is reachable at all. `new --help` prints the 100-char cap. | `task.py::op_set`, `build_parser` |

⚠ **Item 5's OTHER half is not fixed and is not scheduled.** `list --parent R6` still
includes children whose ids are not `R6-N` (`TK48`, `TK17`–`TK22`), because `parent` is a
containment edge and the id prefix is not — they genuinely are children of `R6`. The
mis-count risk is real but the remedy is not obviously "filter by prefix": that would make
`list` lie about the parent graph to flatter a naming convention. Anyone re-counting
`R6-N` sub-items should filter the output, and say they did.

**What is still unmeasured** (unchanged, and now unmeasurable within the trial): M1/M2/M3
were never obtained after the pilot instrument failure (`:104-116`, `:163`); the Q3 dye
marker is spent (`:330-337`), so the 18-agent figures cannot be reproduced against the
current tree; the rubric's declared board-bias was never repaired with a Q6 (`:80-84`); the
design measures *directed* use, never natural preference (`:382-390`); and **the cost of the
parallel-maintenance contract itself was never recorded by any session** — which A6 suggests
is not zero, since it is the step four consecutive sessions skipped.

### 2026-08-31b — the parallel-maintenance cost, recorded at last; and one hard number that is not self-report

Filed at the user's request after they asked for feedback on the board. It closes the gap the
2026-08-29 append names in its own last paragraph: *"the cost of the parallel-maintenance
contract itself was never recorded by any session — which A6 suggests is not zero, since it is
the step four consecutive sessions skipped."* This session ran a real, full-size item
(`P20` adjudication + `P3` bridge, ten gate phases, four commits) with both arms maintained.

⚠ **DECLARE THE INSTRUMENT FIRST: everything below except B1 is SELF-REPORT, which §2 of this
protocol rules out** (*"a session's own account of what it read is the least reliable
instrument available"*). §2 is right, and this session is fresh evidence for it — see B4,
where the session both skipped its own mandated self-report and then asserted a trend from
memory that one `grep` refuted. Read B2–B5 as operator experience with a known-unreliable
narrator, not as measurement. B1 alone is an artifact count.

**B1 — the one hard number: across every `read:` line ever written, the query has replaced
the file ONCE.** Counted by script over `docs/history/session-log.md`, not recalled:

    board + HANDOFF   10        board only   1        HANDOFF only   0

and the single `board only` is `2026-08-31`, the session immediately before this one. This is
an artifact count over committed text, so it is not subject to §2's objection — though the
lines it counts are themselves self-reports, which caps its strength. **Bearing on the
verdict: §1's first question is "does it reduce what a session must read before it can start
work?" On the record so far, ten times out of eleven, no.** This session's reason was
structural rather than habitual — the board view carries no item blocks, so the read-first
lists, the traps and the Rhythm protocol exist only in the file, and would have been needed
whatever the intent. **That makes Phase B (`HANDOFF.md` becomes a stub, row `TT-1`)
unsupported as specified**: the part sessions actually need is the part the tree does not
carry. Cutover requires the tree to grow item blocks first, or the stub to keep them.

**B2 — the parallel-maintenance cost, itemised.** The mirror ops themselves were CHEAP: ten
`task.py` calls (`new`, `close`, two `promote`, two `touch`, three `comment`, one `dep rm`),
all correct first try except one over-long `--brief` rejected at write time. **The cost is not
in the ops. It is in `tasks/BANNER.md`, and it is large and pure waste**: ~6 round-trips to
satisfy checks that the equivalent `HANDOFF.md` banner does not impose (a 14-line cap, then an
unrenderable `∨`, then committing the ASCII fold's *output* `(nav)` instead of the glyph). The
content is a second copy of `HANDOFF.md`'s banner. ⚠ **And it had drifted**: the previous
session rewrote `HANDOFF.md`'s banner and not this one, so the tree's session-start view was
still directing readers to "repoint the abbrev at `DerNode` OR `LeafNode`" — the misread
disjunction that same session had refuted — and to delete `Scratch4cii.lean:51`, closed as
trap (h) the day before. **A duplicated banner did not merely cost time; it served stale
instructions from the arm under trial.**

**B3 — the dual-update contract produced 2 of this session's 8 write-back defects, and one is
the exact failure the trial exists to detect.** Closing `P20` swept its id from the board's
`deps` cell but not from `tasks/P3-*.md`, which still read `deps: [P20]` — a one-armed update,
committed by the same session that wrote a session-log paragraph about one-armed updates. The
other: filing `P21` without ratcheting `tasks/config.json`'s zero-headroom floor, **the second
consecutive session to miss it** (2026-08-31 did the identical thing with `P20`, and the
config's own provenance string records that miss — so a warning in a provenance string has now
demonstrably failed to cause the behaviour twice). ⚠ **Neither was caught by the author.** Both
were caught by `tests/test_tasktool.py` via `tests-tile:1/4`. That is the honest split: **the
tree's mechanical checks are earning their place; the human half of the contract is not being
held, by anyone, in any session.**

**B4 — the trial's own instrument is unenforced, and this session skipped it.** CLAUDE.md
requires two literal lines per session-log entry (`task.py lint` output, and the `read:`
self-report). This entry's session wrote a long ledger entry with **neither**, and nothing
noticed: not `task.py lint`, not `handoff_lint.py`, not any of the ten gate phases. They were
added only after the user asked for feedback on the board. ⚠ **A session that skips them is
indistinguishable from one that had nothing to report** — the fail-by-passing shape
`docs/sabotage-procedure.md` exists for, sitting on the primary instrument of the experiment.
**A lint check asserting both lines are present in the newest entry is the cheapest possible
fix.** Note the tension it would formalise: CLAUDE.md's instrument is self-report, which §2 of
this protocol declares the least reliable available. Enforcing presence does not fix
truthfulness — and the same session then asserted "third session in a row" about B1's trend
from memory, wrong on both citations, refuted by one `grep`.

**B5 — what the tree earned, stated as narrowly as the evidence allows.** Not the board view.
Two things adjacent to it: (i) `task.py lint`'s 12 checks plus `tests/test_tasktool.py`, which
caught four real defects this session; (ii) the per-item `Log` sections, which ACCUMULATE where
board rows are DESTRUCTIVE — the dated entries appended to `P3`, `P6` and `DW-1` survive,
whereas the equivalent board-row prose is overwritten by the next session to touch the row.
⚠ **Both are arguments for the FILES and the LINT, and neither is an argument for the QUERY**,
which is what §1 actually asks about.

**B6 — the recommendation this suggests, offered as input to the 2026-09-06 decision, not as a
verdict.** Neither listed option fits: cutover is unsupported (B1) and keep-both-as-is
preserves the only measured pure cost (B2). A third shape is consistent with all of B1–B5 —
**keep the tree, drop the duplication**: retire `tasks/BANNER.md` in favour of reading
`HANDOFF.md`'s banner (one source, no drift, no second glyph dialect); add the B4 lint check;
make `task.py new` ratchet its own floor or refuse to exit 0 (B3). Then decide cutover on the
item-block question alone, which is the only real blocker and which
`tree-sole-authority-spec-2026-08-29.md` should be checked against. ⚠ Not filed as board rows:
the user asked for the feedback to be recorded, not executed, and filing rows would itself
incur the B3 contract this entry is reporting on.

### 2026-09-06 — the window closes: the tree was the STALE arm, the query still did not replace the file, and the mechanics kept earning their place

Filed at the user's request ("grade the helpfulness of the task tool … add your feedback into
the existing list"), on the trial's last day, by the session that also did the `TT-1` prework.
**No cutover was decided** (user: "prework + grade only, decide later"); the user's stated
leaning going into the feedback pass is *keep the task tool; deprecate `HANDOFF.md` or relegate
it to something ephemeral that carries between sessions once and is replaced* — recorded here so
the pass starts from it rather than rediscovering it. Same instrument caveat as `2026-08-31b`:
C1 is an artifact count, C2–C3 are mechanical findings with the tool's own output as evidence,
C4–C7 are operator experience.

**C1 — the hard number, extended to the whole window, and re-measured this session by script
over `docs/history/session-log.md` (not carried forward from `2026-08-31b`).** Entries dated
2026-08-23 … 2026-09-06: **35**. `read:` self-reports:

    board + HANDOFF   27        board only   6        HANDOFF only   0        no read line   2

The six `board only` are `2026-08-24d`, `2026-08-31`, `2026-08-31c`, `2026-09-01b/c/d` — a
run of three consecutive sessions in the `P3` proof push, where the item was already in hand
and the board view's brief was enough. **So the answer to §1's first question over the full
window is: 6 of 33, and never once by a session that was picking up new work.** Consistent
with `2026-08-31b`'s B1 and its structural explanation (the item blocks live only in the file).
⚠ A method note that is also a finding: a strict `^read:` line-start match counts **19 / 4 /
0 / 12**; the figures above come from a match that tolerates `**read: …**`, inline backticks
and indented forms. The "two literal lines" instrument was written in at least four shapes,
which is what B4's proposed lint check would have to normalise before it could assert anything.

**C2 — the tree was the STALE arm, and the tool said so on the first query.**
`python scripts/task.py sync --check` at session start reported **9 drifts** (`P6`, `R6`, `P4`,
`P5`, `P14`, `TK55`, `TK54`, `P21`, `DW-1`): board rows whose text had moved under sessions
that updated `HANDOFF.md` and not the mirror — the one-armed update B3 predicted, now at scale.
Two readings, both true: the parallel-maintenance contract was NOT held (nine times); and the
detector WORKED — every drift was found mechanically, with the old and new digest, in one
command, and all nine were reconciled and acked this session. **The board has no equivalent
instrument in the other direction**: nothing can tell you a `tasks/*.md` Log line was never
promoted to its board row, because the board carries no digest of the tree.

**C3 — an `ack` gap that blocked reconciliation, found by trying.** Three of the nine
(`TK55`, `TK54`, `P21`) were `source: hand` tasks that nonetheless HAVE a board row (filed by
hand first, row added later). `sync` reports their drift; `ack` refuses it — `source_hash` is
only maintained for `source: board`. The only exit was to hand-edit `source: hand → board` with
a Log line, which is exactly the kind of by-hand frontmatter surgery the tool exists to
prevent. Also learned the hard way: `ack --since` wants the digest the CURRENT drift report
shows, not the one recorded in the file. Both are filed as prerequisite 6 of the Phase B′
candidate at the top of `tree-sole-authority-spec-2026-08-29.md` (DRAFT, not decided), not as
board rows, for the same reason B6 gave.

**C4 — the mirror ops this session, itemised, as evidence the ops themselves are cheap and
the WRITE-TIME REFUSALS are the useful part.** `close` ×2, `new` ×3, `ack` ×12 (nine drifts +
three first reconciliations), `comment` ×1, `lint` ×4, `sync --check` ×4. Refusals hit: a label
outside `config.json`'s vocabulary (`tests` — the vocabulary is `formal/perf/docs/infra`, which
has no home for a test-only or oracle-side item; two of today's three new rows were mis-labelled
`formal`/`infra` to get past it), a 103-char title, a 127- then 126-char brief. Every refusal
was correct and every retry was one line; **`new` ratcheted `min_tasks_parsed` 159 → 162
itself** (B3's fix, landed `2026-09-06`, observed working three times). Contrast the board:
`handoff_lint.py` refused an 11th trap badge, which was also correct — but the board's checks
run at commit time, the tree's at write time, and the write-time ones cost less because the
mistake is still on screen.

**C5 — `tasks/BANNER.md` again.** Written once, in one pass, because the 14-line cap was known
in advance; but it is still a hand-maintained second copy of `HANDOFF.md`'s banner, and B2's
argument stands unchanged. Nothing this session changes it.

**C6 — what was useful, said as narrowly as the evidence allows.** In order: (i) `sync --check`
as a stale-arm detector (C2) — the single most valuable thing the tree did all week, and the
thing a one-file board cannot do; (ii) the write-time refusals and the self-ratcheting floor
(C4); (iii) `lint` as the two-line session receipt; (iv) `show <id>` for one item's body plus
its accumulated Log — read, in this session, for `TT-1` only. **Not useful, still:** the
`board` query as a replacement for reading `HANDOFF.md` (C1). The tree's value is in its
FILES, its LINT and its DIGESTS; the query is a view over them, and the file it competes with
carries content the tree does not.

**C7 — input to the user's plan, offered as a shape, not a verdict.** The user's leaning
(keep the tree; make `HANDOFF.md` ephemeral, one-hop, replaced each session) is consistent
with C1–C6 IF the three things the file carries and the tree does not — the item blocks with
their read-first lists, the Rhythm protocol, and the closed-ids ledger that `handoff_lint.py`
harvests line by line — get a home first. The Phase B′ draft names them as prerequisites. An
ephemeral `HANDOFF.md` that still hosts item blocks is the `2026-08-31b` B6 shape with the
banner de-duplicated; an ephemeral one that does not is a cutover in disguise and needs the
tree to grow blocks first. **Decide that question, and the rest is mechanical.** Not filed as
board rows; the user asked for the grade to be recorded ahead of a feedback pass.

---

## 7. Full run — design, pre-registered 2026-08-24 before any agent launched

### 7.1 The task is now SESSION-shaped

The pilot measured the board on its home turf (§P5). The tree's claim is *the same
knowledge of one item, for less reading*, so the task becomes: **pick up the `NOW` item
and decide how to start.** Verified before writing this — `show P3` and `HANDOFF.md`'s
`### P3` block both carry `HUMAN CALL`, `FALSE AS WRITTEN`, `Seven traps`, `census hole`
and the `viewer.0` probe output, so neither arm is starved of content. **What differs is
the cost of reaching it**: the board arm reads a 260-line file; the tree arm reads a
19-line `board` plus an 80-line `show P3`.

Agents are told **not to open** the documents they list under `READ-FIRST`. Listing them is
the deliverable. Without that bound both arms chase pointers into `PROOF_STATUS.md` and
the scope doc, and the measurement becomes about those files instead.

### 7.2 Arms are DIRECTED, not blind — and this is a limitation

`CLAUDE.md` names both systems, so neither arm can be naive. Each arm is therefore told
explicitly to use its own system and not the other. **This measures directed use, not
natural preference**, and the difference matters: it cannot answer "which would a session
reach for", only "given this system, how well does a session start". The tracer below is
repurposed as the compliance check.

### 7.3 The tracer

`TRACER:` asks how many `R6` items remain to land. `9` is board-only, `11` is tree-only
(§P2, 4/4 separation in the pilot). In the full run it detects **arm violation**: a TREE
agent answering `9` read the board anyway, and a BOARD agent answering `11` used the tree.

### 7.4 Scoring — six points, answers fixed here in advance

| # | credit for | source |
|---|---|---|
| S1 | names `P3` | both |
| S2 | the **human call**: after the re-point the headline theorems are FALSE AS WRITTEN at minted leaf-name queries — the thing that must be decided before 4c-ii lands | both |
| S3 | the **seven traps in scope doc §11.10**, and that §11.10 is read before touching the cone | both |
| S4 | the **census hole** — `CascadeStable.lean::shadow_graphRec_agree`, 14 repairs, unbudgeted | both |
| S5 | **`P6` is not parallel-safe** — same 38-module cone | both |
| S6 | read-first names `PROOF_STATUS` `2026-08-21b` and/or scope doc §11.9/§11.10 | both |

Every point is available from **both** sources by construction — the §5 quiz bias does not
apply to this scoring. Cost, not correctness, is the hypothesis under test here: **the
tree's claim is parity on S1–S6 at lower cost.** A tree win on quality would be a bonus
finding; a tree LOSS on quality at higher cost would sink it.

### 7.5 n, and what will and will not be computed

**6 per arm on Haiku, 3 per arm on Sonnet.** Reported per model, never pooled.

Haiku (n=6/arm) gets a **Mann–Whitney U** on tokens and on tool calls: non-parametric, no
normality assumption, appropriate at this n. Sonnet (n=3/arm) gets **medians and ranges
only** — n=3 supports no test, and running one anyway would be decoration.

⚠ **The token figures carry a large fixed floor** (~30 K of system prompt in the pilot),
so a ratio of totals understates the effect on the part that varies. Report the
DIFFERENCE in medians alongside the ratio, and do not quote a percentage of the total as
if it were a percentage of the reading.
