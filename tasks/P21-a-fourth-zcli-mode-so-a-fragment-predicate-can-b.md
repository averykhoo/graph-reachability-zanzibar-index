---
id: P21
title: a fourth zcli mode so a fragment predicate can be DIFFERENTIALLY checked, not mirrored
brief: zcli has 3 modes and no channel for a Prop; a 4th makes the mirror a real differential
pri: LATER
size: M
deps: []
related: []
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-08-31b
moved: 2026-08-31b
updated: 2026-08-31b
closed:
---

`formal/conformance/test_leaf_namespace_correspondence.py` checks that no schema Python
accepts violates Lean's `LeafRules.lean::NoLeafSubjects`. It cannot ASK Lean: `zcli` exposes
exactly three modes (`spec` / `graph` / `graph-state`, `Cli.lean:14`, rc 4 for anything else)
and has no channel to evaluate an arbitrary `Prop`. So the file **re-implements** the
predicate in Python and says so in its own docstring. **The residual that leaves open: the
mirror can be wrong in the SAME direction as the model, and nothing notices.** A fourth
`zcli` mode taking an encoded `Schema` and printing the decision of
`Decidable (NoLeafSubjects S)` (the instance already exists, `LeafRules.lean:605`) turns
every such mirror into a real differential over the 50-schema corpus.

Filed 2026-08-31b out of `P20`. It generalises: the same three-mode ceiling blocks a
differential for **every** `W4Fragment` field, which is what makes the LOUD 0 / MIXED 3 /
SILENT 7 classification in `test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE` an argued table
rather than a measured one. Doing this well probably means a generic
"decide-this-fragment-predicate" mode, not one hard-wired to `NoLeafSubjects`.

## Traps

* ⚠ **Do not describe the existing mirror as machine-checked while this is open.** Its
  docstring names the requirement deliberately; weakening that wording is how a
  re-implementation gets mistaken for a differential.
* ⚠ **A new zcli mode is a Lean change**: request decoder, output shape, a `runner.run_*`
  parser, and a `lake build zcli`. It is not a Python-only test.
* ⚠ Adding a mode touches `Cli.lean`'s closed exit-code set (0-5, rc 4 = unrecognized mode).
  Check what asserts that set before extending it.

## Read first

* `formal/conformance/test_leaf_namespace_correspondence.py` module docstring -- it states
  the requirement in the words this item has to satisfy.
* `formal/lean/ZanzibarProofs/Cli.lean` -- the three modes and the exit-code contract.
* `formal/conformance/runner.py::invoke_zcli` -- how a request reaches the binary.
* `formal/history/PROOF_STATUS.md` `## Session 2026-08-31b` sec 3(ii).

## Log
