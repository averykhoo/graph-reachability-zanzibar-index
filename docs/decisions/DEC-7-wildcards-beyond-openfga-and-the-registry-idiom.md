---
type: Decision
id: DEC-7
title: Wildcards beyond OpenFGA, and the registry idiom (user decisions, `ASK-2`)
actor: owner
decided: 2026-09-29
session: 2026-11-03a
decision_status: BUILT
attribution: owner, the heading says it records a user decision; the date of the commit that wrote the heading (git blame), 2026-09-29
imported_from: docs/evidence/decision-log-normalised-2026-11-03.md
body_sha: sha256:6e2bbd0ce41d5bbe05cf679a7d1776e400b374527e62b770709a8ae76092b743
---

* **The three wildcard extensions stay** (2026-09-26): wildcard usersets
  (`[group:*#member]`), star tuplesets (a stored `doc:d1#parent@folder:*` walked by
  `x from parent`) and object wildcards (`object_wildcard_shapes`). Both backends
  implement them and the differential matrix pins their agreement, but the headline
  theorems exclude them (`W4Fragment.wsBare` / `.bareStar` / `.ttuStarFree`), so
  `src/zanzibar/schema/compiler.py::UnprovenExtensionWarning` tells callers. A bare `[T:*]` is
  stock OpenFGA and is not an extension.
* **`*` is the supported way to say "every X"; the OpenFGA registry idiom is not**
  (2026-09-29). Rejected alternative: a registry / organization object that every X is
  linked to by one bookkeeping tuple (`group_registry:all#member@group:g#member`,
  `folder:f#org@folder_org:all`). It is plain tuples, so nothing refuses it and it
  evaluates; "not supported" means the repo does not offer it as a substitute for `*` and
  promises nothing about the two agreeing. Why rejected: it is a `*` the application
  maintains by hand. Every new X needs a registration write, and a missed one is silently
  wrong — fail-closed on a grant, **fail-open under `but not`** (a ban routed through the
  registry misses every unregistered group's members). A `*` covers objects that do not
  exist yet with no write, and cannot drift. The rewrite would sit inside the proven
  fragment, but its equivalence to `*` would then rest on an application invariant
  nothing checks — the proof gap moves out of sight rather than closing. Its one real
  advantage is portability to stock OpenFGA. REASONED, not probed: that each rewrite
  gives the same `check` answers as its `*` form once registration is complete (the
  `expand` / `lookup` output shapes differ regardless).
