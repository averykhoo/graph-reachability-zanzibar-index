---
id: TK151
title: fold PYPI_README/README/docs user content into Diataxis-structured docs, written by the model
brief: user decision 2026-10-14: TK123's PyPI sections are interim; all user docs become Diataxis (tutorial/how-to/ref/explain)
pri: NOW
size: L
deps: [TK123]
related: [TK143, TK123]
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-10-14
moved: 2026-10-19b
updated: 2026-10-19b
closed:
---

User decision, 2026-10-14 (verbatim, on TK123 item 22, the new PyPI sections): "we can add the sections to pypi now but it should all get folded into the docs later, which i think there should be a task for. the docs will be written by you using the diataxis framework".

So the user-facing sections TK123 adds to `PYPI_README.md` are INTERIM. This row folds all user-facing content (PYPI_README.md, README.md, and the user-relevant parts of the repo-only docs) into one documentation set, written by the model and structured by Diataxis. Diataxis has four kinds of docs, each with one job:
- tutorials: learning-oriented, a guided first run that always works;
- how-to guides: task-oriented recipes for a reader who already knows what they want;
- reference: information-oriented, a complete and accurate description of the API, DSL, refused shapes, errors and knobs;
- explanation: understanding-oriented, the why (the two backends and their cost models, the semantics, how this differs from OpenFGA, the assurance story).

`TK143` (the GitHub Pages docs site) was MERGED into this row by the user on 2026-10-16, so this row owns the publishing too, and TK143's content list (see the 2026-10-16 Log entry).

Constraints to keep: the PyPI quickstart is executed by `tests/test_tk122_release_metadata.py`, so whatever the long description becomes must stay executable; refused-shape text should come from the REFUSED SHAPE / WHY / INSTEAD blocks rather than be restated by hand; no restated test counts (`docs/README.md` sec 1).

Behind TK123 (the public API rename), since the docs describe the renamed API. As of 2026-10-19b it is the LAST open 0.1.0 row (TK155/TK156/TK157 closed), and its landing is followed by the 0.1.0 cut (a MINOR bump; see the 2026-10-19 Log entry).

## Traps

- The release is 0.1.0, never 0.0.6: TK144 flips some ALLOW answers to DENY on boolean models.
- Before tagging, decide the marker-shape question in the 2026-10-19b Log entry (`ExpandResult.markers` pairs vs `LookupResult.markers` triples); the API freezes at 0.1.0.
- A tag is a release: push `v0.1.0` only on the user's explicit word; then CI babysitter, PyPI-live check, fresh-user install trial (`~/.claude/CLAUDE.md` § Git).

## Read first

- `PYPI_README.md` (the PyPI long description; its quickstart is executed by `tests/test_tk122_release_metadata.py`).
- `README.md`.
- `tasks/closed/TK143-user-docs-site-published-on-github-pages.md` (the publishing row this overlaps).

## Log

### 2026-10-14

USER DECISION 2026-10-14 (in chat): "let's save 0.1 for when we have some docs". 0.1.0 is gated on THIS row. TK123's API break ships unreleased under CHANGELOG [Unreleased] (__version__ stays 0.0.5) until the Diataxis docs exist. Then cut 0.1.0 with the API break plus the docs.

### 2026-10-16

USER DECISION 2026-10-16 (in chat): "Merge 143 into 151". TK143 (GitHub Pages docs site) is closed into this row. Its content list is now part of THIS row's scope; the publishing half comes with it:
- content: the semantics notes (strict forall=>exists for wildcards, strict FOR NOW per TK4; how this library differs from OpenFGA, TK137/TK138; the wildcard extensions beyond OpenFGA and their UnprovenExtensionWarning), every refused schema shape with its INSTEAD rewrite, the operational knobs (ZANZIBAR_PARANOIA, ZANZIBAR_MAX_CLOSURE_FANOUT, async catch_up), and the public API after the TK123 rename.
- publishing: a GitHub Pages site. It still needs the user's word before it ships: a new Pages workflow under .github/workflows/ and the publish step itself are outward-facing.
- TK143's read-first: docs/openfga-claims-audit-2026-10-13.md (what we claim about OpenFGA).

USER DECISION 2026-10-16 (in chat): "We'll include all open items in 0.1.0, no rush to release." So 0.1.0 is no longer gated on this row alone. Session reading of "all open items" (recorded so the next session can check it with the user): the release-relevant set from the 2026-10-16 scoping, i.e. TK154, TK150, TK153, TK147, TK138/TK144 (landing 2), TK155, TK156, TK157 and this row (with TK143 folded in). The literal 64 open rows include HOLD/SOMEDAY and perf rows (R6-*) and Lean housekeeping; those are NOT read as release blockers unless the user says so. Order: this row lands LAST so the docs describe the final API.

### 2026-10-19

TK144 (TK138 landing 2) closed 2026-10-19 and adds a release obligation to the 0.1.0 cut this row gates: it flips ALLOW to DENY on a boolean model (OpenFGA implicit userset self-relation; e.g. vx in the selfrel_boolean_flip corpus), so the release MUST be a MINOR bump (0.0.5 -> 0.1.0), never a patch. __version__ stays 0.0.5 and the change is under CHANGELOG [Unreleased]. No separate release row exists, so this is recorded here rather than filed; the 0.1.0 cut (src/zanzibar/__init__.py::__version__ + the CHANGELOG heading) happens when this row lands last.

### 2026-10-19b

2026-10-19b: TK155, TK156, TK157 closed (uncommitted at close; orchestrator gates and commits). TK151 is now the last 0.1.0 row, promoted to NOW. Carried into this row for the 0.1.0 cut: (1) API-shape choice before the freeze: `ExpandResult.markers` are (type, predicate) pairs while `LookupResult.markers` are (type, predicate, 'any') triples; documented in the ExpandResult docstring and pinned by tests/test_tk155_store_expand.py, NOT aligned. Decide (align or keep) before tagging. (2) `SetEngine.expand`'s docstring still points key-wanting callers at lookup_reverse; the user docs should point at `Store.expand` (engine.py docstring left alone because of its anchored content pin). (3) The new public surface to document: `Store.expand` / `ExpandResult`, the lookup filters (`object_type`/`relation`, `subject_type`/`subject_predicate`), and `Store.adopt` returning (store, BuildReport).
