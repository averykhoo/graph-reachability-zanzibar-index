# Detecting `CORRESPONDENCE.md` claim-rot automatically — DESIGN, not built

> **ACTIVE-PLAN (2026-08-16) — designed and measured, NOT built.** This is the scope
> doc for board row `P13` in [`HANDOFF.md`](../../HANDOFF.md); it stays live until that
> row closes, then gets the frozen banner (see [`docs/README.md`](../../docs/README.md)
> §2–§3). Corrections are appended dated at the top, never edited into the body.
> Migrated verbatim out of `HANDOFF.md` on 2026-08-16 by the handoff-system migration —
> it was a design record parked on the board, which is not the board's job.

## Why this exists

The anchor pin (`verify.sh` step 4d) resolves every `file::symbol` pointer in
`formal/CORRESPONDENCE.md` and **nothing else**; §9.2 of that file says so in as many
words. A 2026-08-16 audit of the rows that session touched found **four defects, three
of them invisible to every gate in the project**:

* a retracted measurement claim still live in a row ("82/82 derived keys agree",
  retracted everywhere else the same day);
* two rows describing a model that had since changed;
* `unionSpineLeaves` — the def carrying the whole 2026-08-16b correction — **unanchored,
  so renaming it would have passed**;
* the binary-`Expr` divergence missing from §7 entirely.

All four were fixed by hand that day. **The point of this item is that hand-fixing does
not generalise.**

## The measured constraint that shapes the design

Measured 2026-08-16: only **143 of 396** non-witness top-level decls under
`formal/lean/ZanzibarProofs/` were anchored — **36%**, a 253-decl backlog, worst offenders
`Cli.lean` (20 of 22 unmapped) and `State.lean` (20 of 29). So "every def must be in the
map" was not a viable gate then and is unlikely to be one now: it has to be a **ratchet**.
Re-measure before building; these are as-of-then figures, and the live anchor total is in
`formal/FINAL_REVIEW.md`'s generated block, not here.

## Three mechanisms, in recommended order

### (B) Anchor content pin — build this first

Hash the source text of each anchored symbol into a golden, exactly as
`formal/headline_definitions.txt` already does for the headline definitions (reuse
`formal/conformance/statement_pin.py`). When an anchored symbol's BODY changes, the pin
moves and you must regenerate deliberately — and that regeneration is the moment you
re-read the row. **Zero-tolerance-viable immediately**: it applies to the already-anchored
set, so there is no backlog to work off first.

⚠ **Must hash the BODY, not the signature.** `persistedLeaves` changed twice on
2026-08-16 with its signature (`Schema → String → Expr → List PLeaf`) byte-identical, so a
signature pin would have missed the exact case that motivated this design.

Cost: it fires on behaviour-preserving refactors of anchored symbols — the same noise
`headline_definitions.txt` already accepts at the same scale.

### (C) Prose-number lint — cheap, build alongside

Any `CORRESPONDENCE.md` row carrying an `N/M` or "N of M" validation claim must cite a
test or a generated block. Direct analogue of step 4e's existing "corpus-count prose:
0 stale claim(s)" scan. This is what would have caught the live "82/82".

### (A) Reverse-anchor ratchet — weakest, optional

Floor the anchored count so it can only rise, plus: **any NEW file under `formal/lean/`
must have every non-witness def anchored.** Would have caught `LeafRules.lean` /
`TtuStarWide.lean` but **not** `unionSpineLeaves` (a new def in an already-mapped file).

⚠ The witness exclusion **must be STRUCTURAL** (`namespace *Witness`), never a
hand-maintained list — that pattern has already failed twice in this tree.

## Traps

⚠ **State the honest limit in each new check's own docstring, or it will be over-trusted
exactly as the anchor check was.** None of these verifies that a row is TRUE. They convert
*silently stale* into *loudly must-look*. And one of the four defects is not mechanizable
at all: knowing that a newly discovered fact about the Python side belongs in §7's drift
log is irreducibly human.

## Sabotage plan (required before believing any of it)

Per [`docs/sabotage-procedure.md`](../../docs/sabotage-procedure.md):

* **(B)** edit an anchored symbol's body and confirm the pin moves **while the anchor
  check stays green** — that is the proof it catches what step 4d structurally cannot.
* **(C)** re-insert the "82/82" claim and confirm it fails.

Adding these is a **new gate phase**, so landing it needs the full ten-phase re-run, not
just the phase it adds.
