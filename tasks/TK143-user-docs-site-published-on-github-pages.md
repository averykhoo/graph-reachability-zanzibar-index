---
id: TK143
title: User docs site published on GitHub Pages
brief: user docs site on GitHub Pages: semantics notes (strict forall=>exists, OpenFGA diffs), refused shapes, knobs
pri: LATER
size: M
deps: []
related: [TK123, TK138, TK137, TK4]
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-10-13d
moved: 2026-10-13d
updated: 2026-10-13d
closed:
---

User request 2026-10-13d (in chat), while deciding TK4: "maybe we need docs for this, add a task to write some and publish it as GitHub pages".

Scope: one user-facing docs site gathering what today is scattered across PYPI_README.md, README.md and repo-only docs: the semantics notes (strict forall=>exists for wildcards -- strict FOR NOW, TK4; how this library differs from OpenFGA, TK137/TK138; the wildcard extensions beyond OpenFGA and their UnprovenExtensionWarning), every refused schema shape with its INSTEAD rewrite, the operational knobs (ZANZIBAR_PARANOIA, MAX_CLOSURE_FANOUT, async catch_up), and the public API after the TK123 rename.

Needs the user's word before it ships: a new Pages workflow under .github/workflows/ (keep CI changes out of unrelated branches) and the publish step itself (publishing is outward-facing). Filing only; nothing is set up.

## Read first

- `PYPI_README.md` (the current user-facing surface).
- `docs/openfga-claims-audit-2026-10-13.md` (what we claim about OpenFGA).

## Log
