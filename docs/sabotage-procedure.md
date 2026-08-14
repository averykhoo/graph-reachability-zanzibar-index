# The sabotage procedure — how to earn the right to believe a check

**This is a standard procedure, not advice.** It applies to every assurance step added
to this repo: a test, a floor, an assertion, an invariant clause, a gate phase, a pin, a
lint, a coverage histogram, a conformance corpus.

> **When you add a check, break the thing it guards and watch it go red before you
> believe it.**

## Why this is a procedure and not a suggestion

**An assurance step that fails by PASSING is this project's house failure mode.** It has
recurred often enough, across enough independent subsystems, that it is treated as the
default hypothesis about any new check rather than as an unlucky accident. The catalogue
below is drawn entirely from checks that were *already in this repo, green, and trusted*:

| the check | what it looked like | what it actually did |
|---|---|---|
| `HYPOTHESIS_SEED` fuzz sweep | six seeds | ran the **same** seed six times |
| the axiom audit | "457/457 reports" | counted reports without checking **which** theorems |
| the validation matrix | "both `SetOps`" | **silently halved** when `pyroaring` was missing |
| a property test | twelve steps | could `continue` past **all twelve** |
| `tests/` (728 tests) | "the gate" | was **outside** `verify.sh` entirely |
| isolation-level guard | `SERIALIZABLE` accepted | justified by a comment about a database **this project does not support** — and it was a live authorization fail-open |
| the headline STATEMENT pin | pins 26 theorem statements | **blind** to a definition change that silently converts a scope-carry into a false guarantee (2026-07-27) |
| a plan-leaf coverage floor | "the kind is compiled" | a corpus can compile a leaf and drive it **constantly empty** (2026-07-28) |
| a wildcard-coverage floor | "a wildcard exists" | bare `[user:*]` satisfies it while `[T:*#p]` stays at **zero** (2026-07-28) |
| `_REQUIRED_LEAF_KINDS` | a hand-maintained list | correct the day it was written; **green forever** once the compiler grows a branch |
| state-gate projection P3 | "state-level equality" | compares edges as a **set**, so edge **multiplicity** divergence is structurally invisible — and the multiplicity died *twice*, first inside the Lean binary (`Cli.lean::canonJsonArr`) and again in the extractor's `set`, so "make the Python side a multiset" would have compared all-ones and reported green (closed 2026-07-29, `CORRESPONDENCE.md` §7.2) |
| invariant **I9** (cascade audit) | re-runs `reconcile` and compares | reads the **same** compile-time `parent_types` its subject reads, so it **agrees with itself**; paranoia was ON through two live authorization fail-opens (2026-08-10) — see "the mirror instrument" below |
| `BoolStarBridgeParityMachine` | the "headline blind spot" closer, booleans × star-bridge, 4-way | ran the graph index on 13% of draws — and on **ZERO boolean draws, ever** (all 768 `and`/`but not` configs of 1536 were rejected for every OWC subset, so its 4-way draws were exactly the `or` ones): it fuzzed **3-way and reported green** for its whole life. **FIXED 2026-08-10** → 76–82% 4-way, 49–55% boolean-4-way, rate now floored with provenance (2026-08-10) |

Note the pattern: **none of these were wrong when written.** They decayed, or they were
subtly narrower than their name. That is why the procedure is mandatory rather than
reserved for checks you feel unsure about — the feeling of sureness is not correlated
with the outcome.

## The procedure

1. **Write the check.** Watch it go green.
2. **Name the property it guards**, in one sentence, out loud. If you cannot, the check
   has no content yet — stop here.
3. **Break exactly that property** in the code or data under test. Not a typo, not a
   syntax error: a *plausible* degradation — the one a future contributor would
   introduce by accident or by a well-meaning refactor.
4. **Observe the failure**, and read the message. Record the **literal output**.
5. **Restore**, confirm green again.
6. **Write down what you sabotaged and what you saw** — see "Evidence" below.

If step 3 does not produce red, you have not added a check. You have added a comment
that costs CI time.

### Choosing the sabotage (the step people get wrong)

The sabotage must be the **narrowest plausible weakening**, not an obvious catastrophe.
Deleting the whole feature almost always goes red and proves nothing. The 2026-07-28
pair is the model:

* ✅ `[group:*#member]` → bare `[user:*]` — still "a wildcard", still compiles, still
  exercises wildcard code. A naive floor stays **green**; the real floor fires.
* ✅ make the derived tupleset storage-leaf-free — the leaf is **still compiled**, so a
  histogram floor stays **green**; the non-vacuity pin fires.
* ❌ delete the corpus — everything goes red, tells you nothing about *which* property
  is guarded.

Ask: **"what is the most innocent-looking edit that would make this feature stop being
tested?"** Sabotage *that*.

### The INERT change — when the sabotage reddens nothing, and that is the finding

Added 2026-08-14, from `ttuStarFree` part (i).

Sometimes you land a correct change that **nothing consumes yet**. Part (i) widened
`Schema.isSubjectWildcardUserset` to cover star-tupleset through-shapes — genuinely
closing a modelling hole — but the only function that reads it, `ensureInBridges`, is
not called by any live chain (`writeRules`/`writeLoggedRules` are bridge-free folds).
So the sabotage produced this:

> **Short-circuit `isStarTuplesetThrough` to `false` — the entire tree still builds.**

That result is easy to misread two ways, and both are wrong:

* ❌ *"the sabotage didn't fire, so my change must be inert/pointless"* — no, the change
  is correct and necessary; it is a **prerequisite** whose consumer lands later.
* ❌ *"nothing went red, so the tree already covered this"* — no, the tree covered
  **nothing** here. A green build under the sabotage is the *proof* that no existing
  check guards the new behaviour.

**The rule: when a change is inert, the sabotage's job flips.** It is no longer asking
*"does the existing gate catch this?"* — you already know it doesn't. It is telling you
**exactly how much new pinning you owe**, which is *all of it*. Part (i) therefore ships
with six `decide` witnesses that exist for no other reason, and the commit says so.

Two corollaries worth carrying:

1. **Make the red attributable.** Under the sabotage, exactly two of the six pins went
   red and the other four — the literal-disjunct attribution, the one-character control,
   the BARE-guard, and the control node — stayed **green**. A sabotage that reddens
   *everything* cannot distinguish "the new property is load-bearing" from "the file is
   broken". Build the controls so the red points at one thing.
2. **Say it in the commit and the docstring, not just in your head.** The dangerous
   future reader is the one who sees a definition with a disjunct nothing calls and
   "simplifies" it away. The pins are the only thing standing between them and silently
   reopening the hole — so the docstring must state that the pins are the *sole*
   evidence, and why.

### Sabotage your instrument too, not just your subject

A measuring instrument can be as broken as the thing it measures — and it fails
silently in the same way. During the 2026-07-28 E-chain attack sweep, the first
coverage instrument reported **73 failures out of 132** because it omitted a star
exemption; the probe would have "found" a catastrophic bug that did not exist. It was
caught only because the run included a **control** — a deliberately-degraded input that
*must* be detected, plus a known-good input that *must not* be.

So for any probe, sweep, or differential:
* **Positive control** — feed it a defect it must catch. Confirm it does.
* **Negative control / non-vacuity** — confirm the comparison actually ran on something
  (count the comparisons; assert the count is nonzero). **A sweep that compared nothing
  reports success.**
* **Assert the SCOPE it claims, not just that it ran.** A differential that quietly drops a
  backend keeps comparing — just not at the arity in its name.
  `BoolStarBridgeParityMachine` — the machine whose own header calls it *"the audit's headline
  blind spot"* closer for **booleans × star-bridge** — ran the graph index on 13% of its draws
  (the rest raise `UnsupportedByGraphIndex`, `ParityEngine` sets `graph=None`, it fuzzes
  3-way) and reported green for its entire life. ★ **The sharp version, found by exhaustively
  enumerating its config space (1536 configs): all 768 `and`/`but not` configs were rejected,
  for every OWC subset including the empty one, so the 13% that DID run 4-way were exactly the
  `or` draws. It had tested booleans against the graph index ZERO times, ever** — the one
  cross it was built for was the one cross it never ran. Its sibling
  `StarBridgeParityMachine` asserts `graph is not None` and never had the problem.
  **FIXED 2026-08-10** (the boolean arm's placement is now drawn: `downstream` is in-fragment
  for every op, `target` only in an explicit scope-boundary stratum where the rejection is the
  asserted contract) — 13% → 76–82% 4-way, 0% → 49–55% boolean-and-4-way, with an exhaustive
  in-fragment completeness test and a floored rate test carrying provenance.
  This is **silent scope degradation** — distinct from the mirror below: sabotage *can* find
  it, but only if the scope is asserted rather than assumed. Note what made it invisible:
  every individual draw behaved correctly and the suite was green; only the *rate* was wrong,
  and nothing measured the rate.

### The mirror instrument — a check that reads its subject's source

Every sabotage above works by breaking something **downstream** of the check. One class is
structurally out of their reach: a check whose expectation is derived from the **same
source** as its subject. Break the subject and it reddens on cue; it is blind only to that
source being wrong, because a defect there moves check and subject together.

**The five-second test, before you sabotage anything:**

> **If the SOURCE this check reads were itself wrong, would this check still pass?**
> If yes, it is a *mirror* — whatever else it certifies, it cannot certify that source.

**Worked example — invariant I9, which cost two live authorization fail-opens (2026-08-10).**
I9 audits the delta cascade by re-running `reconcile` and comparing. But `reconcile` reads
the same compile-time `parent_types` metadata that was wrong, so it **agrees with itself**
and reports green; paranoia mode was ON throughout both bugs and never fired. Note what this
does to the procedure: **I9 passes every sabotage in this document.** Break the cascade and
it goes red exactly as step 3 asks. The defect was upstream of both the instrument and its
subject, and no downstream sabotage can reach it.

**Remedy: derive the instrument from a *different* source than the subject.** The prototyped
fix for those bugs is a compile-time invariant that checks `parent_types` against the emitted
`RewriteFilter`s — what admission actually *accepts* onto the tupleset's storage leaves —
rather than against `_member_types`, the thing that was wrong. Different derivation, so a
`_member_types` defect moves one side and not the other; validated RED-before / GREEN-after.

### Prefer a mechanical refusal to a doc warning

Once you have found one of these, **do not fix it with a comment** — the next person
will not read the comment. Ranked by durability:

1. **Best — make the sabotage a permanent test.** Construct the degraded input in code
   and assert the guard raises. This converts "I checked it once by hand" into a check
   that survives you. (`test_required_leaf_kinds_are_exactly_the_compilers_kinds` is the
   pattern: it reads the kind literals out of the compiler's own source, so the floor
   and the compiler cannot drift.)
2. **Good — derive the expectation instead of hand-maintaining it.** Any hand-written
   list of "what should exist" is a future silent pass. Read it from the source of truth —
   and from one **independent of the subject**. Derived from the subject's *own* source,
   this rank degrades into a mirror (above): it stays green precisely when that source is
   the thing that is wrong.
3. **Acceptable — a hard floor with a stated provenance** (`-ge` with a measured number,
   a comment saying when it was measured and by what command).
4. **Weak — a docstring.** Use only when 1–3 are genuinely impossible, and say why.

Related standing rule: **prefer converting an `xfail` into a positive pin.** An `xfail`
*is* a failure that passes, which is why `verify.sh` budgets them explicitly
(`MAX_TESTS_XFAILED`) rather than tolerating them silently.

## Evidence — what to record and where

The sabotage is worthless if nobody can tell it happened. Record, at the point a
reviewer will see it:

* **In the test's own docstring** — the property guarded, and the sabotage that was
  observed to break it. This is the primary location.
* **In the commit message** — a short table of sabotage → observed output for anything
  new in the gate.
* **In `formal/history/PROOF_STATUS.md`** (for formal-side work) or
  `docs/spec-deviations.md` (for backend work) when the sabotage revealed a real gap
  rather than confirming a good check.

A sabotage report is only evidence if it quotes the **literal observed output**. "I
verified it fails" is not evidence; `plan-leaf kind(s) ['derived-tupleset-ttu'] are
produced by NO corpus` is.

## What this procedure cannot do

It cannot be mechanically enforced — there is no way for the gate to know you ran a
sabotage, and a check that claimed to verify that would itself be an instance of the
failure mode it polices. **The mitigation is placement, not enforcement:** the evidence
goes in the test's docstring and the commit message, where review sees it.

It also does not replace the formal side's **attack-first** rule
(`formal/HANDOFF.md` house rule 2 — try to REFUTE a theorem statement with `#eval`
against the real definitions before proving it). The two are the same instinct pointed
at different objects: attack-first guards against proving something false, sabotage
guards against trusting a check that verifies nothing. **A session that kills a false
statement, or exposes a hollow check, is a GOOD session — record the finding.**
