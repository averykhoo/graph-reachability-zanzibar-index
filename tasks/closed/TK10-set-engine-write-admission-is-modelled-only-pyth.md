---
id: TK10
title: set-engine write admission is modelled only Python-vs-Python, and it gates what the gates see
pri: HOLD
size: M
deps: []
related: []
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-29b
updated: 2026-08-29b
closed: 2026-08-29b
---

`SetEngine._validate` step (1) (object-wildcard gating) and step (3) (cycle rejection, via `::SetEngine._would_cycle` → `::SetEngine._flow_reaches` over the bridge-aware flow graph) are modelled only as a Python-vs-Python differential; only step (2) has any Lean counterpart, and even that appears as a premise. `CORRESPONDENCE.md:943-954` states why this one is load-bearing rather than merely uncovered: **a bug here silently shrinks the enumerated space — and nothing formal watches it.** Admission decides which stores the conformance and enumeration gates can enumerate at all, so a wrongly-rejecting validator makes every downstream green cheaper without saying so.

`HOLD`, not `LATER`: the exclusion is declared with a stated reason, and closing it properly means deciding what a Lean-side admission model would even buy over the differential. That decision is the work, and it is not queued.

## Traps

⚠ **This is the "green because it stopped looking" shape, one level up from the usual one.** The instrument is not a check that could pass vacuously; it is the input filter that decides how much there is to check. If a cheaper mitigation exists — a non-vacuity floor on how many corpora survive admission, in the style of `anchor_check.py`'s `MIN_*` floors — that may be worth more than a model, and is a legitimate outcome for this row.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (the corpus convention; `migrate.py::check_formal_pointer` enforces it for the generated rows and 18/18 formal tasks satisfy it)
- [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md)`:943-954` — the entry and its load-bearing argument
- `setengine/engine.py::SetEngine._validate` — the three steps; `::SetEngine._would_cycle` and `::SetEngine._ensure_flow_graph` for the flow graph
- `formal/conformance/corpus.py` — what admission decides the gates may enumerate

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-10 (`CD-5`, tier 2, sweep-d only); anchor re-resolved by COVERAGE.md §C4 and re-read here at formal/CORRESPONDENCE.md:943-954.

### 2026-08-29b

APPENDED to docs/latent-gaps.md, SCOPED DOWN from what the finding claimed. Verification changed this one: the shrink-the-enumerated-space argument the task treated as unique is ALREADY in the home almost word for word (CORRESPONDENCE.md:957-961, including the 132-of-299-stores figure), so writing it again would have duplicated it. The bullet carries only what is genuinely absent -- the framing that admission is the gates' INPUT FILTER, not a check that can pass vacuously -- plus the non-vacuity-floor outcome as a legitimate alternative to a Lean model. Symbols confirmed: engine.py:913 _validate, :944 _would_cycle, :839 _flow_reaches.
