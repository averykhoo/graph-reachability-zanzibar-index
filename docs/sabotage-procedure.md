# The sabotage procedure — how to earn the right to believe a check

**This is a standard procedure, not advice.** It applies to every assurance step added
to this repo: a test, a floor, an assertion, an invariant clause, a gate phase, a pin, a
lint, a coverage histogram, a conformance corpus — **and to every measurement instrument
whose number you intend to act on**: a benchmark, a profile, a probe, a differential
sweep. A number that decides whether to write code is a claim about the code exactly as
much as a green test is, and it fails the same way. See "A measurement is an assurance
step too" below.

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

**When the check is a new corpus or fixture that exposes a divergence, land it RED first,
in its own commit.** The `rewriteClosure` dedup leg (2026-08-08) added `reconvergent_diamond`
and `reconvergent_derived` in a deliberately-red commit *before* the fix, so the divergence
was attributable to the corpus rather than arriving mixed into the change that hides it. A
corpus that arrives green in the same commit as its fix has never been observed to fail, and
you cannot afterwards tell whether it would have.

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

### Probe BOTH signs — a one-directional probe mis-classifies severity

From the RC1/RC2 arc (2026-08-10/11), the single most transferable output of it.

The same defect can be a false negative or a false positive depending on the *polarity of
the consumer*. A dropped TTU parent is a false **NEGATIVE** under a positive TTU
(`define access: viewer from parent`) and a false **POSITIVE** — a live authorization
**fail-open** — under a negated one (`define access: [user] but not viewer from parent`).

**Probing only the positive direction mis-classifies severity by one sign**, which is
exactly what the original divergence filing did: it reported an under-grant, and the real
bug was an over-grant. A reader who acted on that filing would have rewritten correct
leaf-routing code.

**The rule: any new TTU corpus, probe or sabotage must carry both directions.** More
generally, before you believe a severity, ask which consumer polarities exist for the
defect and make sure your probe drives the one that inverts it. The permanent compile-time
pin is `test_compile_refuses_parent_types_narrower_than_admission`; its error text names
the sign (`docs/spec-deviations.md`, 2026-08-11).

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
3. **Use the sabotage to reject a NARROWER pin you were about to write.** In leg 7 4c-pre
   the `".0"`-stripper run left the index-0 pin **green** — which proved that an
   index-0-only pin would have been vacuous, and that the pin had to name the whole
   fan-out. A green pin under a sabotage that should break it is not reassurance about the
   code; it is a verdict on the pin.

### A TEARDOWN test is not a DELETE test — when the natural ordering hides the branch

A close cousin of the inert change: the sabotage fires on nothing because **no test ever
reaches the branch you broke**, and the reason is an ordering nobody chose deliberately.

**Worked example — the `ResidueRefV1` reverse index (2026-08-14).** The fix replaced a full
`ResidueV1` scan with an indexed seek, maintained beside the residue row. Skipping index
maintenance on the residue-**DELETE** branch alone left the whole new test file **green**
(`11 passed`); only the paranoia-driven matrix caught it. The reason is structural: an orphan
is observable only when the indexed row goes from ref-bearing straight to deleted in ONE
step, and **every natural teardown ordering empties `neg`/`upos` while `stars` is still
present** — so the index is cleared through the *update* branch and there is nothing left to
orphan.

**The rule:** if a row can be updated or deleted, a test that tears the state down
gradually exercises only the update path. Write the one-step case explicitly. Generalises to
any index maintained beside a deletable row; the permanent pin is
`tests/test_residue_ref_index.py::test_residue_emptied_in_one_step_takes_its_index_rows_with_it`.

### A REBASE needs a different control than a CLONE — and a GENERATED golden regenerates

From E-chain leg 5 (2026-08-05). Legs 3/4 *packaged* existing content (a clone): the
plausible sabotage is "drop a field", and it reddens `FullScope`. Leg 5 **rebased** a proof
bundle — `GraphAdmission.storeValid` → `StoreValidRulesD`, `W4Fragment`'s single
`computedOnly` field → five derived-def clauses — and the plausible failure there is not a
dropped field, it is the **half-done leg**: widen `W4Fragment`, leave `GraphAdmission`
narrow, and bridge them with a conversion lemma
(`storeValidRulesD_of_storeValidRules_directArmsBare`) — **which typechecks**.

Measured: with the four witness declarations present, ONE error in the whole tree; delete
them and it is **"Build completed successfully (1084 jobs)"**.

Two things this teaches:

1. **Match the sabotage to the CHANGE SHAPE, not to the file.** For a rebase the narrowest
   plausible weakening is a *type-correct half-migration*, not a deletion. Ask: "what is the
   half of this leg someone could stop after, that still compiles?"
2. **A GENERATED golden cannot witness a change to the tree that generates it.** Every
   gate signal reads as success under the half-done leg: statements stay byte-identical, the
   definition pin MOVES so the gate even reports "meaning changed", audits are clean — and
   because both goldens are generated FROM the tree, the leg regenerates them into a
   self-consistent pair and passes the entire gate. That is the mirror instrument (below) in
   golden form. The only control that reaches it is a **witness theorem** that instantiates
   the widened bundle at a concrete store (`W4WitnessDirect.final_applies`), because a
   witness fails to elaborate when the bundle is not really wider. Legs 3/4's sabotages at
   least reddened `FullScope`; this one **reddens nothing**.

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

### A check that PARSES before it compares has two halves, and the easy sabotage tests one (2026-08-24c)

Most checks in this repo are *extract, then compare*. A sabotage input chosen in a shape
the extractor already handles exercises **only the comparison**, and passes while the
extractor is blind. It looks like a real red, which is why it survives review.

`scripts/handoff_lint.py::check_ledger_row_ids` shipped 2026-08-16 with this certifying
sabotage, and it is a genuine failure of the comparison:

    FAIL: docs/history/session-log.md:2 cites board id 'P99', which is on neither the
          board nor its retired-ids line.

`P99` is a shape `_ROW_ID` parses correctly, so the red proves the comparison works and
says nothing about the read. Meanwhile the extractor matched `R6` inside `R6-99` and
stopped at the word boundary — and `R6` **is** a real id, so an invented sub-item citation
resolved to its real parent and reported clean for eight days across every `R6-N` id
(nineteen of them, roughly a fifth of the live id space). Board row `TK46`.

Two rules, both cheap:

* **Choose the sabotage input in the shape that is actually blind.** If you cannot say
  which shapes the extractor handles, that is the thing to probe first. "The check went
  red" is not evidence about an input class it never received.
* **Assert on the INTERMEDIATE, not only the verdict.** A verdict cannot distinguish *the
  extractor read the id and judged it fine* from *the extractor never saw it*. The
  replacement pins compare token lists over one identical sabotaged corpus:

      inherited -> 0 violation(s); tokens ['R6', 'R6', 'P3', 'P6']
      ported    -> 1 violation(s); tokens ['R6-99', 'R6', 'P3', 'P6']

  The silence on the first line was not a judgement, and only the token list shows it.

⚠ **Widening an extractor to close a hole is itself a change that needs a control.** The
port above, applied alone, false-redded a *real* id (`R6-10`) that the board names in
prose and deliberately never gives a table row. A fix paid for in false reds is how a
believable check gets switched off. Pin the accept side (`tests/test_handoff_lint_row_ids.py`
`::test_a_real_sub_item_named_only_in_prose_is_accepted`) in the same commit as the
reject side — and keep any non-vacuity floor on the **narrow** harvest, or a broken parser
coasts on the widened one.

### A MEASUREMENT is an assurance step too — ask what the number would look like on nothing

Added 2026-08-17, from the `R6` measurement pass and `GS-2`. The section above says
sabotage your instrument; this one says the rule binds even when the instrument produces a
*number* rather than a verdict, and even when nothing is being "checked" at all. A profile
that decides an item is NOT MOTIVATED retires that item from the round — it is a gate on
implementation effort, and it goes green by default.

> **The five-second test, before you believe any measured number:**
> **what would this number look like if the probe ran on nothing?**
> If the answer is "the same as it looks now", the number is not evidence yet.

A share is the shape that fails hardest here, because **0/0 renders as a clean small
percentage** and a small percentage reads as "not a bottleneck". So: **print the
denominator next to every share** — the call count, the rows returned, the number of
comparisons — and read it before you read the share. That is the whole mechanism that
caught the first two of the four below.

**Four instrument corrections in one session (2026-08-17), each of which changed a
verdict, none of which was caught by any test:**

| the instrument | what it reported | what it was doing |
|---|---|---|
| `R6-2` expand probe | `R6-2 NOT MOTIVATED, 18.8%` | ran on a star-CLOSED schema, so `.pos` was empty by construction and the per-element fold it measures **never ran** — `members returned: 0`, 240 unions for 120 expands |
| the cascade probe | `R6-11`/`R6-12` **INCONCLUSIVE** | profiled `build_graph`, which bootstraps via `DeltaProcessor.backfill()` — the OFFLINE path. `reconcile_subject`: **0 calls** |
| the `R6-12` counter | `15.00x re-reconcile` | summed calls across all 30 write cycles; the claim is about intra-cascade duplication. Per-cascade: **1.00x** |
| the `GS-2` scope harness | 2 probes **FAILED** | read/wrote its subject files in **text mode**, so on Windows an LF file came back CRLF: the harness moved the very tree id it was measuring |

Three things generalise out of them:

1. **Wrong-workload is the dominant failure mode, not wrong-arithmetic.** Three of the
   four ran correct code over an input that does not reach the thing under study — the
   bootstrap path instead of the incremental one, a star-closed schema instead of a
   `pos`-bearing one. Before reading a profile, name the function the finding is about and
   confirm the run **called it a nonzero number of times**. `benchmarks/profile_r6.py`'s
   design is the durable form of this: counters keyed to each candidate's own claim,
   printed beside the timings, so a zero is impossible to miss.
2. **Right answer by luck is still a failed instrument.** `R6-2`'s first and second runs
   reached the *same* verdict, NOT MOTIVATED. That is why the correction is written down
   rather than quietly fixed: only the second run reached it for a reason it had measured.
   A verdict you would have published either way carries no information.
3. **An instrument can mutate its own subject.** The `GS-2` harness is the pure case — its
   I/O layer changed the bytes whose digest it was reading. Anything that writes to the
   tree it measures (a probe that edits and restores, a bench that leaves a database
   behind, a sweep that touches mtimes) owes a **baseline re-read after restore**: confirm
   you are back where you started before trusting anything the run said.
4. **Run the check against a CLEAN tree before you sabotage it — a check nobody can get
   green is as dead as one that never fires.** The whole protocol is about silence, so it
   is easy to forget that the opposite failure also kills a check: it gets commented out,
   or its floor gets loosened until it is slack. Two of this repo's checks were shaped by
   it. `HEADLINE_MAX` was scoped to the root ledger only after a wider version fired 60
   times on an **append-only** file whose entries may never be retro-edited — a check
   demanding a fix its own convention forbids. And `check_doc_links`' first version
   (2026-08-20) resolved the code-span *label* of `` [`../HANDOFF.md`](../HANDOFF.md) ``
   against the repo root and reported **32 violations on a clean tree**, every one of them
   a link that resolves fine when clicked. Both looked right when written. The baseline run
   is also what makes the later red *attributable*: if a marker is already present before
   the sabotage, that case proves nothing unless the new failure line names the sabotaged
   subject specifically.

The remedy ranking from "Prefer a mechanical refusal to a doc warning" applies unchanged.
For a measurement, rank 1 is the non-vacuity counter printed in the instrument's own
output; rank 2 is deriving the workload from the code path under study rather than reaching
for a convenient existing bench schema.

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

### The mirror instrument's twin — a transcription fed the WRONG REPRESENTATION

A mirror instrument reads its subject's *source*. There is a second, sneakier member of the
family, and it looks like the textbook remedy: you **transcribe** the rule into the other
language and diff the two implementations. Different derivation, independent code — it looks
like exactly what the section above asks for. It is not, if you feed the transcription a
different *representation* of the input than the model actually receives.

**Worked example — leg 7's leaf allocation (2026-08-16).** `GraphIndex/Leaf.lean`'s
`persistedLeaves` models Python's `_build_plan_tree`. To check it, it was transcribed into
Python and diffed against the compiled `LeafFamily` table over every corpus and fixture:
**"82/82 derived keys agree, 0 disagreements."** Green, independent, non-vacuous-looking.

It was blind. The transcription consumed Python's **n-ary** `Union` AST. Lean never sees that
tree — `formal/conformance/encode.py::_fold_binary` **left-folds** n-ary unions, so the model
receives `((m₁ ∪ m₂) ∪ …) ∪ mₖ`, whose left spine contains sub-unions that are pure *by
accident of the folding*. Re-run over the binarized AST, the same instrument found a
disagreement immediately — on `nary_union_derived4`, which is **in `GRAPH_FRAGMENT`**:
Python allocates three leaves, the model merged them into one.

**The extra question this adds to the five-second test:**

> **Is my instrument consuming the same REPRESENTATION the subject consumes?**
> A transcription of the right rule over the wrong input shape is not an independent check —
> it is the mirror instrument with extra steps.

**Why the representations diverged is itself the lesson: the normalization was justified by
the wrong invariant.** `Core/Schema.lean` justifies left-folding n-ary unions by
associativity + commutativity — true of `sem`, and **false of the leaf ALLOCATION** read off
the same tree. Measured: `a or b or safe` → 2 leaves, `(a or b) or safe` → **1**, and the
encoder maps both to the same `Expr`. When a pre-processing step is defended by "property P
is invariant under it", check that every property your model *derives from that tree* is P.
The refusal is mechanical, not a doc warning:
`formal/conformance/test_conformance_state.py::test_no_corpus_nests_a_pure_union_inside_an_impure_one`.

**And check whether your *other* instrument could have caught it, structurally.** Here a
second, genuinely independent instrument was green too (`rawWriteRels` vs `RuleSet.apply`'s
real seed set, 744/744, with three positive controls). It could never have fired: it maps
`.closure _ => none`, and the offending key has no storage leaf, so **no closure-leaf
allocation error can move that number at all.** Two green instruments, one shared blind
spot — and the shared blind spot was not visible from either one's controls. When two checks
agree, ask what each is structurally incapable of seeing before you count them as two.

### "The only net" is a claim about a test, and it is usually untested (2026-08-20b)

The two sections above are about instruments that were blind. This one is about the *belief*
that a named test guards a property — a belief carried into a change's design without anyone
having watched the test fail, **while the repo's own ledger already said it wouldn't**.

**Worked example — `R6-10`'s star-expansion premise.** The `R6-10` memo is unsound if it
freezes `tupleset_parents`, because that fans a star parent through `_instances_of_type`,
which reads the global `NodeV4` table — and `_reconcile` mutates that table mid-cascade
(step 2a interns, step 5 GCs). **No benchmark can catch the mistake**: `R6-3`/`R6-13`
measured 0 calls, so no benchmarked workload has an `RC2` star-tupleset shape at all. The
item's recon therefore named `tests/test_ttu_tupleset_parent_types.py` as *the only net*.

It is not a net. Sabotaging exactly the thing it supposedly guards — memoizing
`tupleset_parents` (S2), and again `derived_stored_parents` (S2b) — left **all 12 of its
tests green**. The module writes its pool in one batch and then queries, so it pins that a
star parent *is* expanded and never that the expansion stays *live*. Nor is it the only
blind one: under the same sabotage `tests/test_matrix.py` — the 4-way validation matrix
`CLAUDE.md` names as what pins "same semantics" — also stayed green (`24 passed`), as did
`test_lookup_oracle.py`. The sole evidence for that property is now
`test_star_expansion_is_not_frozen_by_the_memo`, written because the sabotage came back
green.

⚠ **The "26" this paragraph first carried is itself a worked example.** It was `pytest`'s
`26 passed` summary line from a **three-module** sabotage run (10 + 14 + 12 = 36, of which
10 failed), misread as a count of one module's tests — which collects **12**. It was written
into a permanent docstring in four places and propagated here as *literal observed output*
before a reviewer re-collected the module and caught it. A summary line is a fact about the
run, not about the module. **If you are recording a count as evidence, get it from
`pytest <target> -q --collect-only`, not from the tail of a run that spanned other targets.**

**The part that should sting: this was already written down.** The `2026-07-26` entry in
[`spec-deviations.md`](spec-deviations.md) says of a different fix that it *"passes every
pin in `tests/test_ttu_tupleset_parent_types.py`, because those write in one batch and
reconcile once; it would have failed only under incremental maintenance"* — the exact
limitation, in the right file, recorded a month earlier. It was not carried to the place
where someone would rely on the module, so it was re-derived from scratch by sabotage.
**A known limitation of a test belongs in that test's docstring**, where the person about to
lean on it will read it; a dated ledger entry records that you learned it, not that the next
reader will.

> **If you are about to rely on a test as the only guard for a property, sabotage the
> property and watch THAT test go red.** "Module X covers this" is a hypothesis. A module
> can pin the existence of a behaviour while pinning nothing about its liveness,
> freshness, or ordering — and the difference is invisible from the test names.

Note the shape: a **green sabotage is a finding**, not a non-event. It says either your
sabotage missed, or the guard you were counting on does not exist. Both are worth knowing
before you ship the change that depends on it.

**Two instrument failures from the same session, both caught by controlling the
instrument.** The first `S2` run returned `36 passed` — a green sabotage that was the
*probe's* fault: the test only drove `derived_stored_parents`, and step A had just rerouted
that path around `tupleset_parents`, so the sabotage was unreachable from the test. Widened
to drive all three routes, it went red. The first `S3` attempt (`outer = True`) produced
`33 failed, 3 passed` via `TypeError: object of type 'NoneType' has no len()` — an obvious
catastrophe, rejected under §"Choosing the sabotage" and replaced with the plausible
no-outer-flag form, which gave a clean `2 failed, 34 passed`.

### Never hand-write a Bool mirror of a `Prop` without PROVING it (2026-08-20b)

`#eval` probes over a Lean `Prop` need a `Bool` mirror, and a wrong mirror does not error —
it silently returns `true` for every clause, so the whole battery comes back green and reads
as a no-kill result. This has now bitten twice (the 2026-07-28 Leg-0 sweep, the 2026-08-16
`persistedLeaves` transcription), and a third time was caught in the act: the draft
`derNodeB` mirror of `CascadeStable.lean::DerNode` handed to the `P3` adjudication was
**wrong** — it omitted `variant == .plain`.

Two things caught it, and the cheap one is not enough on its own:

1. **A deliberately-failing control** — run the clause the mirror should *reject* and watch
   it come back `false` before trusting any green. (`CONTROL SlV: extrasDer=false`.)
2. **A proof, where the mirror is load-bearing**: `derNodeB_correct : derNodeB S k = true ↔
   DerNode S k`. A control shows the mirror is not *constantly* true; only the iff shows it
   is the *right* predicate. When a route decision rests on the probe — as `P3`'s did —
   pay for the iff.

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

It also cannot turn coverage into proof. The generator-coverage leg reaches a large
majority of pairwise cells with `UNACCOUNTED == set()` and no hand-written exemption list —
and **roughly a quarter of the pair space is still unreached even at `deep`**. So read a
green gate as **"the instruments we have found nothing"**, never as "there is nothing".
Publish the residue rather than rounding it away
(`docs/design/generator-coverage/README.md` §6 is the model: a coverage design that claims
completeness is the failure mode it was written to fix).

And it says nothing about the **plan** you are executing. Treat a scope/design document the
way you treat a check: E-chain legs 2/3/4 each landed a correction to their own plan — two
instructions refuted by measurement, a gate specification found insufficient **three legs
running**, an obligation inventory that missed a hypothesis — and leg 7's §4 prescription
("fork `writeDirect`") was refuted outright by a 20-line probe. Measure a plan's load-bearing
cells before paying its cone. Corollary from `ttuStarFree` part (iv) (2026-08-16): a step
deferred because a question "might block it" is a *measurement you have not run* — the
analogous decidability question was answered NO-BLOCK in one session after two sessions of
assuming it.

It also does not replace the formal side's **attack-first** rule
(`formal/HANDOFF.md` house rule 2 — try to REFUTE a theorem statement with `#eval`
against the real definitions before proving it). The two are the same instinct pointed
at different objects: attack-first guards against proving something false, sabotage
guards against trusting a check that verifies nothing. **A session that kills a false
statement, or exposes a hollow check, is a GOOD session — record the finding.**
