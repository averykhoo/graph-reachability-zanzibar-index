---
id: TK4
title: spec mandates a documented lenient-mode hook that does not exist in code (adjudicate)
pri: HOLD
size: S
deps: []
related: []
parent:
labels: [docs, infra]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed:
---

`docs/specs/wildcard-materialization-spec.md:141` (§3.4, *Strict ∀⇒∃, pinned*) ends: *"Leave a documented hook (a per-shape config flag that would add a single `w_all(S) → w_any(S)` edge for the lenient/vacuous reading) but do not implement it."* No such flag or hook exists in `index_v4/wildcard.py` or `zanzibar_utils_v1.py`.

**HOLD because the item is an adjudication, not a build.** §10 (line 324) lists lenient mode under non-goals as "hook only", so the sentence may already be satisfied by the spec text itself. It is a real spec-vs-code deviation only if *hook* means a code affordance. Decide which, then either (a) add the flag, or (b) reword §3.4 so it stops mandating an artifact, and record the outcome in [`docs/spec-deviations.md`](docs/spec-deviations.md).

## Traps

⚠ **`CLAUDE.md`: where a spec and the code disagree on a name, the CODE wins** — but that rule settles naming, not existence. This one needs a human call, and the cheap outcome (b) is as legitimate as (a).

⚠ **Do not implement the lenient reading itself.** §3.4 pins strict ∀⇒∃ as *the default and only mode*; the oracle and both backends agree on it. Only the HOOK is at issue.

## Read first

- [`docs/specs/wildcard-materialization-spec.md`](docs/specs/wildcard-materialization-spec.md)`:141` — the mandate, and §10 line 324 — the non-goal that may already satisfy it
- `index_v4/wildcard.py` / `zanzibar_utils_v1.py` — sweep-l found no flag; the three `lenient`/`vacuous` hits are unrelated prose
- [`docs/spec-deviations.md`](docs/spec-deviations.md) — where the adjudication is recorded whichever way it goes

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-4 (`W-2`, tier 1, sweep-l only); COVERAGE.md §C3 confirms the spec text survives and no flag exists, and flags the item as INTERPRETIVE. Re-read `docs/specs/wildcard-materialization-spec.md:141` this pass.
