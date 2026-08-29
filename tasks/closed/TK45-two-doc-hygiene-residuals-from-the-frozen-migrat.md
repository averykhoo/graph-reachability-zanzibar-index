---
id: TK45
title: two doc-hygiene residuals from the frozen migration map: banner drift and stale inbound links
brief:
pri: HOLD
size: M
deps: []
related: []
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-29b
updated: 2026-08-29b
closed: 2026-08-29b
---

Two residuals recorded in the FROZEN migration map and never adjudicated:

**(a)** frozen-banner enforcement was a ONE-TIME sweep, with no ongoing check for design docs that land afterwards (`:591-595`);

**(b)** a long tail of stale inbound `HANDOFF.md` citations across the tree — `README.md`, `scripts/pg_local.sh`, several tests citing it by line or section (`:637-641`).

`HOLD` because neither was verified: the map is frozen provenance, and the first step is a measurement, not a fix. (a) is partly the class the banner row tracks generically; (b) is its own thing.

## Traps

⚠ **(b) is about to get much worse, or much cheaper, depending on timing.** If the `HANDOFF.md` board is replaced by a short stub, every citation that names a LINE or a SECTION of it breaks at once, and `handoff_lint`'s `check_doc_links` catches only a broken LINK, never a stale DESCRIPTION. Measure the inbound tail BEFORE that lands, not after.

⚠ **(a) wants a mechanical refusal, not a doc warning.** `CLAUDE.md`'s standing rule: prefer a mechanical refusal over a doc warning, because the next person will not read the doc. A one-time sweep with no ongoing check is precisely a doc warning.

## Read first

- [`docs/history/handoff-migration-map-2026-08.md`](docs/history/handoff-migration-map-2026-08.md)`:591-595` and `:637-641` — the two residuals (FROZEN)
- [`docs/README.md`](docs/README.md) §2 — the liveness states and the banner rule that (a) would enforce
- `scripts/handoff_lint.py::check_doc_links` — what already exists, and its limit

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-30 (`J-17`+`J-18`, tier 4, sweep-j only), kept at the lowest rank there because both are frozen-provenance and were never confirmed or refuted. Anchors: docs/history/handoff-migration-map-2026-08.md:591-595 and :637-641.

### 2026-08-29b

APPENDED to docs/README.md section 3 -- and the finding was HALF STALE, like TK51. Verified first-hand rather than inherited. Residual (a) is CLOSED for history dirs: handoff_lint.py::check_frozen_banners globs every .md under HISTORY_DIRS and its docstring explicitly refuses a hand-maintained filename list ('a list beside a glob goes stale the first time someone adds a file'), so a new record IS covered automatically -- the finding's 'one-time sweep with no ongoing check' no longer holds there. NEAR-MISS worth recording: I first read handoff_lint.py:216's 'explicit list rather than a glob' as proof the banner check was list-based; that comment belongs to check_doc_links, a DIFFERENT check, and reading it as this one would have written a false statement into a living doc. What survives is narrower and now recorded: design docs OUTSIDE a history dir (docs/design/, docs/specs/) are walked by nothing, and residual (b) is not enforceable at all -- check_doc_links proves a link resolves, never that the sentence around it still describes the target.
