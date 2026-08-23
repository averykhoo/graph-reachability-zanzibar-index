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
