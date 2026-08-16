# Sub-agent fan-out runbook — how to scope one, and how to not lose the results

Written 2026-08-10, immediately after a fan-out audit **failed in a way that lost almost
everything it had done**. This file exists so the next one doesn't.

Companion to [`docs/gate-runbook.md`](gate-runbook.md) (how to run the gate) and
[`docs/sabotage-procedure.md`](sabotage-procedure.md) (how to know a check works). This one
is about orchestrating many agents at once.

---

## The failure this is written from

**Task:** sweep every "scope reduction" in the formal layer and the gate — fragment
clauses, theorem hypotheses, conformance projections, compile-time rejections — and for
each, measure whether it hides unverified admissible behaviour.

**Design:** 5 sweep lenses in parallel → dedupe → one audit agent per item → 3 adversarial
verifiers per surviving claim → 1 synthesis.

**Outcome: 32 of 278 agents completed. The verify and synthesis phases never ran at all.**
26 audits landed out of ~200. The run died on the session token limit.

Two things went wrong, and only one of them is about size.

### Fault 1 — the work list was machine-generated and never curated

The sweep lenses were told to be "exhaustive within your lens". The compile-rejections lens
duly returned **96 items**, including every parser error in `zanzibar_utils_v1.py`:
`relation definition missing colon`, `stray ']'`, `unterminated '['`, `empty definition`.

Those are not scope reductions in the sense the task meant. A parser refusing a malformed
schema excludes **nothing admissible** — there is no behaviour behind it to be unverified
about. But each one got a full audit agent, with instructions to build schemas, run
backends and hunt divergences. The budget went to them, and the ~15 items that actually
mattered were still queued when the limit hit.

> **A sweep DISCOVERS candidates. It does not DEFINE the fan-out.**
> Read the sweep, cut it by hand, then fan out.

### Fault 2 — the phases that turn claims into findings run LAST, so they die FIRST

The pipeline was audit → verify → synthesize. When the budget ran out, what survived was
**26 unverified single-agent claims** — precisely the output form with the least value,
because in this repo an unverified claim is not a finding. The adversarial verifiers, whose
whole job is to kill the plausible-but-wrong ones, never ran. Neither did the ranking.

Of the 26, exactly **two** were worth anything, and only because the orchestrator
re-verified them by hand afterwards. One was real (a live Python divergence). One of the
others reported `divergenceFound: YES` on a schema **both backends refuse** — the exact
false positive the verify phase existed to catch.

---

## How to scope a fan-out

1. **Cap the fan-out in the script, and `log()` what you dropped.**
   ```js
   const CAP = 20
   const work = inventory.slice(0, CAP)
   if (inventory.length > CAP) log(`⚠ capped: auditing ${CAP} of ${inventory.length}; dropped ${inventory.slice(CAP).map(i => i.name).join(', ')}`)
   ```
   Silent truncation reads as "covered everything". A capped run that says so is honest; an
   uncapped run that dies is neither complete nor honest.

2. **Filter with a cheap predicate before spending an agent.** One sentence, decided by the
   orchestrator or one cheap classifier agent: *"does this exclude behaviour the system
   actually ADMITS?"* Every parser error fails that test instantly. This one question would
   have cut 241 items to ~15.

3. **Budget backwards from the last phase.** If the plan is N items × (1 audit + 3
   verifiers) + 1 synthesis, and that does not fit, **reduce N**. Never let attrition pick
   which phase you skip — attrition always picks the last one, which is always the one that
   turns claims into findings.

4. **Prefer depth over breadth when the output is claims.** Ten items audited AND verified
   beats two hundred audited and none verified. The verification is not a nicety here; it
   is what makes the output usable.

5. **One contended resource → exactly one agent.** The Lean build lock is the example:
   concurrent `lake build` invocations corrupt each other, so exactly one agent may run
   Lean and every other prompt must say so explicitly. Same for anything holding a DB file
   or a port.

6. **Seed the list by hand when you already know it.** For "audit the fragment clauses",
   the clauses are enumerable by reading one structure. A sweep was unnecessary machinery
   that introduced the failure. Sweep only where the inventory is genuinely unknown.

---

## How to persist results — every agent writes a file

**The problem:** when a run dies, everything in flight is lost, the final `return` never
materialises, and the orchestrator's context holds nothing. The journal only has *completed*
agents, and reading it back is awkward (see the encoding note below).

**The pattern:**

```js
const RUN = 'C:\\Users\\user\\...\\audit-run-2026-08-10'   // absolute, created by phase 1

// every agent's prompt ends with:
`★ PERSIST BEFORE YOU RETURN. As your LAST action, write your full structured result to
 ${RUN}\\audit\\<slug>.json — UTF-8, one JSON object, including the LITERAL command output
 you are basing each claim on. Then RETURN ONLY a one-line headline plus that path.
 Your return value must fit in a few hundred characters; the file is the real deliverable.`
```

Then a **reducer** agent reads the directory and hands back only what matters:

```js
const digest = await agent(`Read every .json under ${RUN}\\audit\\. Report how many files
  you read (non-vacuity — if it is 0, say so and fail). Drop everything with
  pythonAdmits=NO. Rank the rest by (divergenceFound, riskIfLeft). Return the top 10 with
  their evidence, and a one-line dismissal for each one you dropped.`, {schema: DIGEST})
```

Why this shape:

* **Partial results survive.** A run that dies at 40% leaves 40% of the findings on disk,
  readable by the next session. That is the difference between "we lost the audit" and "we
  have 26 audits to review".
* **No write contention.** One file per agent, named by slug — no locking, no interleaving.
* **The orchestrator's context stays small.** Agents returning full bodies is what makes a
  long session laggy; the orchestrator should see the reducer's digest and nothing else.
* **It is resumable.** A re-run can skip items whose file already exists.

**Control the reducer too.** It is a filter, and a filter that silently reads zero files
reports a clean bill of health. Require it to state the file count, and treat 0 as failure —
same rule as any other non-vacuity floor in this repo.

**If a fan-out already died, it does NOT start from zero — mine the journal first.** The
2026-08-10 run persisted nothing, but all **279 agent transcripts survive** in the session
journal under `~/.claude/projects/<this-project>/…/subagents/workflows/wf_f8c85180-b74/`,
including the completed structured output of agents whose findings never reached any
document. Two of those transcripts settled a whole board item on 2026-08-14 without
re-dispatching anything. Read the journal before you re-run: it is also the cheapest place
to see the failure mode directly — the dispatched verifiers are 4 lines each, prompt in and
nothing out. (This is a recovery path, not a substitute for the file-per-agent pattern
above; the journal only holds *completed* agents.)

**Write UTF-8 explicitly.** Reading the workflow journal back on this machine crashed with
`UnicodeEncodeError: 'charmap' codec can't encode character 'σ'` — Lean output is full
of `σ`, `∀`, `→`. Set `PYTHONIOENCODING=utf-8` and pass `encoding='utf-8'` on every open.

---

## What to persist

**The literal evidence, not the conclusion.** "Found a divergence" is unusable next week.
This is usable:

```
check(alice, inherited, doc:d1):  oracle=True  graph=False  sets=[True, True]
```

Every agent prompt should say: *if you claim it, quote the output that shows it; if you
could not measure it, write UNMEASURED.* An honest gap is worth more than a confident
guess, and it is the only way the next reader can tell the two apart.

---

## ★ The first fan-out that worked (2026-08-14) — what the rules bought

The rules above were followed for a 6-scout + 1-reducer run scoping leg 7 and the
`ttuStarFree` lift. **8 of 8 agents completed, 7 deliverables persisted, the reducer read
7 of 7.** Contrast the 2026-08-10 run: 32 of 278, verify and synthesis never ran.

What actually made the difference, in rough order of value:

1. **The work list was seeded BY HAND, not swept.** Six questions, each one a thing a
   human already knew needed answering (the fork, the remaining steps, the three
   `ttuStarFree` parts, the gate blast radius, the Python ground truth). Rule 6. No
   discovery phase existed, so there was nothing to be over-inclusive about — the failure
   mode that produced 96 parser-error "items" last time was structurally absent.
2. **Depth over breadth, deliberately.** ~7 agents, not ~280. Every one completed, so the
   phase that turns claims into findings actually ran. Rule 4.
3. **One contended resource, one owner.** Every scout prompt carried an explicit *"do NOT
   run `lake build` / `verify.sh`; another agent owns the build lock"*. Zero corruption,
   and the orchestrator could hold the lock and run the baseline gate concurrently with
   the whole scouting phase. Rule 5.
4. **A READ-ONLY fan-out is the safe shape, and it matches the house rule.**
   `formal/HANDOFF.md` rule 6 already says subagents don't parallelize proof-closing.
   Scoping, measuring and design ARE parallelizable; the compiler-in-loop work is not.
   Splitting on exactly that line meant no agent could damage the tree.
5. **The reducer was controlled.** It was required to state its file count, and it
   reported "7 of 7" plus five facts it re-verified against the tree independently. A
   reducer that silently reads zero files reports a clean bill of health.

**★ The finding that justifies the whole exercise: scouts disagreed, and the disagreement
was the most valuable output.** Two scouts split on whether `writeLoggedOne` must gain an
`S` parameter (~145 mention-lines). The reducer was told **not to average them** — "say
which one has better evidence" — so it surfaced the conflict instead of smoothing it, and
a 20-line probe settled it in the cheaper direction. **A synthesis that reconciles its
sources destroys exactly the signal you paid for.** Instruct against it explicitly.

**⚠ What still needs a human.** Every scout produced a confident, well-cited report, and
several load-bearing claims were still wrong or over-reached — the predicted cascade
round-structure shift (measured away: both cones are 1), the `_RelationParser.check_name`
symbol that does not exist, the "far cheaper than §5 suggests" sizing inherited from a
document. **Scout output is a set of hypotheses with citations attached, not findings.**
The probes are what turned them into findings, and the probes were run by the
orchestrator, serially, holding the build lock.

## The one thing that did work

The single-agent attack-first probe with **its own exclusive resource, a positive control,
and a non-vacuity count** returned the most valuable result of the whole run — a
machine-checked refutation, sorry-free and axiom-clean, that also **corrected the
orchestrator's stated prediction about its own mechanism**.

That is the shape to reach for when the question is sharp: one agent, one hard question,
controlled instrument. The fan-out is for breadth over a *curated* list, and it is worth
much less than it looks if the verification phase does not run.

## The re-run this file is owed (board row `P10`, ~1 session)

The 2026-08-10 scope audit is **not** done; it died at 32 of 278 items, with verification
and synthesis never running. **Do NOT restart it from zero.** All **279 agent transcripts
survive** in the session journal at
`~/.claude/projects/<this-project>/…/subagents/workflows/wf_f8c85180-b74/` — mine those
first. Then apply rule 2's cheap predicate ("does this exclude behaviour the system
actually ADMITS?") **by hand** and re-dispatch roughly fifteen curated items, budgeting
backwards from verification per rule 3.

⚠ **A machine sweep DISCOVERS candidates but must never DEFINE the fan-out** — the failed
run dispatched a raw grep result in which most items were parser error messages, not scope
rejections.

⚠ Read the journal with UTF-8 forced (`PYTHONIOENCODING=utf-8`); it crashed last time with
`'charmap' codec can't encode character`.

**Completion criterion:** roughly fifteen items each AUDITED **and** adversarially
VERIFIED, with literal command output persisted per "What to persist" above. An unverified
claim is not a finding in this repo.
