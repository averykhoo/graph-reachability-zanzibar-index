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

Appended as runs complete. Nothing here yet.
