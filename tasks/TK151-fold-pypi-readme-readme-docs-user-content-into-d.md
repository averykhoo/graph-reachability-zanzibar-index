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
moved: 2026-10-26
updated: 2026-10-26
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

### 2026-10-20

USER DECISIONS 2026-10-20 (in chat): (1) the marker-shape question (ExpandResult.markers pairs vs LookupResult.markers triples) is the model's to decide, before the docs describe it. (2) The GitHub Pages workflow and publishing the docs site are APPROVED. (3) HOLD the 0.1.0 cut until the docs land: no version bump, CHANGELOG heading or v0.1.0 tag until then, and the tag still needs the user's explicit word.

### 2026-10-20b

Plan written: docs/tk151-diataxis-plan-2026-10-20.md (contents, phases, generator choice). DECIDED 2026-10-20b: reader is a Python dev (user); generator Sphinx + MyST + Furo + autodoc, sources in userdocs/ (model; MkDocs ecosystem in flux: Material maintenance mode, MkDocs 2.0 drops plugins); async/tokens get how-to + explanation, no tutorial (model, on the user stable-usage rule). The 2026-10-20 entry above came from a session lost when the PC died; this session owns the row. NOT the last 0.1.0 row any more: TK3, TK158, TK162 are 0.1.0 items (NEXT). Next action: phase 0 marker-shape decision, then the scaffold + Pages workflow.

PHASE 0 DECIDED (model, 2026-10-20b): marker shapes stay as they are, NOT aligned. LookupResult.markers keep (type, predicate, variant) because the variant carries meaning there (any = subject-side, all = object-side under object_wildcard_shapes, see graphindex/wildcard.py::LookupResult docstring). ExpandResult only ever describes subjects, so its variant would always be any: a constant third field is noise, and dropping the variant from LookupResult would lose the all case. The docs explain both shapes and say to compare by the first two fields (as the ExpandResult docstring already does). Pinned by tests/test_tk155_store_expand.py.

IN FLIGHT 2026-10-20b: ultracode workflow wf_e60a3842-f17 (tk151-userdocs) writing userdocs/ (Sphinx 8 + MyST 4 + Furo, installed into the conda env via pip). Shape: scaffold (conf.py, page skeleton, tests/test_userdocs_examples.py, tests/test_userdocs_build.py, docs extra, .github/workflows/docs.yml) -> 12 units write/adversarial-review/fix -> integrate (strict -W -n build) -> completeness critic. Per-agent reports in .scratch/tk151-docs/ (gitignored: transcribe anything that is evidence). If the session dies: resume with Workflow resumeFromRunId wf_e60a3842-f17, or inspect userdocs/ as left. Not yet done after it: PYPI_README shrink, fresh-reader trial, gate, commit.

Round 1 (wf_e60a3842-f17) DONE: 43 pages + scaffold landed uncommitted; findings and 11 suspected library bugs transcribed into docs/tk151-diataxis-plan-2026-10-20.md Correction 2026-10-20b. Round 2 IN FLIGHT: wf_b32b8743-b9f (fix critic items in 5 disjoint units with review, repro each suspected bug B1-B10 under .scratch/tk151-docs2/repro-<id>/, shrink PYPI_README, fresh-reader trial, final strict build). After it: transcribe repro verdicts into the plan doc, file rows for CONFIRMED bugs, gate, commit.

### 2026-10-22

Docs follow-ups for TK158 + TK3 landed 2026-10-22: explanation/limits.md "A refused write is not free" rewritten with the 2026-10-22 numbers; how-to/backends-direct.md no longer says no runtime check catches a skipped cascade (CascadeNotRun, its bound, refused writes still owe); reference/exceptions.md gains CascadeNotRun (tree, table, directive). CHANGELOG [Unreleased] Fixed has both. Still before the cut: userdocs/reference/changelog.md refresh; TK162/TK164/TK166 docs edits as they land.

### 2026-10-23b

IN FLIGHT 2026-10-23b: ultracode wf_7da61747-5e0 (tk166-tk164-tk151): TK166 then TK164 (implement + adversarial review, plans docs/tk166-foreign-token-2026-10-23.md, docs/tk164-public-surface-2026-10-23.md), a TK151 remaining-work audit written at the top of docs/tk151-diataxis-plan-2026-10-20.md, then disjoint page units + integration (changelog refresh, 164/166 page updates). Per-agent reports in .scratch/wf-0p1/. TK162 deliberately untouched (another session live). If this session dies: resume the workflow by run id, or inspect the tree as left (uncommitted).

Round 1 of 2026-10-23b (wf_7da61747-5e0) DONE uncommitted: TK166 + TK164 code (orchestrator re-ran both sabotages first-hand: TK166 ownership check -> 34 failed/4 passed; TK164 ValueError base removed -> 5 failed), audit + round result at the top of docs/tk151-diataxis-plan-2026-10-20.md. Fable editorial review DONE: docs/tk151-fable-review-2026-10-23.md, verdict ship after small fixes. Round 2 IN FLIGHT: wf_50abfcec-e4a applies MUST 1-3 (MUST 2 as a guard test tests/test_userdocs_prerelease_prose.py; the prose itself goes at the cut) + SHOULD 4-7 + NICE 9-10. Then: FINAL_REVIEW counts regen, full gate, commit.

Round 2 (wf_50abfcec-e4a) DONE: fable recs 1-6, 9, 10 applied, 7 partial (message wording -> TK169), 8 not done (-> TK163); per-rec table in docs/tk151-diataxis-plan-2026-10-20.md Correction 2026-10-23c. New guard tests/test_userdocs_prerelease_prose.py (integrator sabotage: dropped a known hit -> red). TRAP for after the cut: the guard flags any userdocs line matching /unreleased/i once __version__ leaves 0.0.x, so the next [Unreleased] CHANGELOG section mirrored into reference/changelog.md will turn it red: word that heading differently or narrow the guard then. Left before the cut: delete the six pre-release hits the guard lists; TK162 limits.md figures; optional viewer_base dedup (5 homes).

### 2026-10-23c

Diagrams round (user request: illustrate the layered derived-relation settling and the path-counting closure). LANDED: userdocs/_diagrams/make_diagrams.py -> 8 figures x light/dark SVG in userdocs/explanation/img/, shown on graph-index.md (5) and boolean-operators.md (3) with furo only-light/only-dark; Layers prose now explains rounds and names the internal relations. Numbers observed by probe, recorded in each figure docstring and in docs/tk151-diataxis-plan-2026-10-20.md Correction 2026-10-23d. PINNED: tests/test_userdocs_diagrams.py (regenerate-equality + both-themes shown), sabotaged red both ways. NEXT: optional figures for two-backends.md and consistency.md; otherwise unchanged (TK162, then the cut).

### 2026-10-23d

Second diagrams round (user: add the two figures 2026-10-23c listed as not done, then push). LANDED: backends-work + store-composition on two-backends.md; consistency-sync-async, consistency-revoke, consistency-stall on consistency.md; all from userdocs/_diagrams/make_diagrams.py, light/dark, pinned by tests/test_userdocs_diagrams.py. Detail: docs/tk151-diataxis-plan-2026-10-20.md Correction 2026-10-23e. NEXT: unchanged (TK162, then the cut).

### 2026-10-26

TK162 CLOSED 2026-10-26, so the BLOCKED-ON-TK162 items in docs/tk151-diataxis-plan-2026-10-20.md are resolved: userdocs/explanation/limits.md section renamed "Lookups for a userset: slow on large stores with and / but not" with measured figures (0.2 s / 2-2.6 s / 21-29 s at 1k / 10k / 100k tuples) and the advice to keep userset lookups off the request path; how-to/query-access.md "List what a subject can access" now points to it. NOT changed: the limits.md line saying the set engine read cost "has not been measured for large groups" (TK162 measured set-engine lookups under 1 ms, but on 10-member groups only, so the claim stands). Source: docs/tk162-self-lookup-cost-2026-10-26.md.
