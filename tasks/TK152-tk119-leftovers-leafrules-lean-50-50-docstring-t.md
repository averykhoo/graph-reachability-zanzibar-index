---
id: TK152
title: TK119 leftovers: LeafRules.lean 50/50 docstring, test_tk126 SERVED duplicate, zcli rc-5 paragraph
brief: stale 2026-08-16 50/50 figure still in LeafRules.lean docstring; X7 fixture dup; CORRESPONDENCE rc 5 text
pri: LATER
size: S
deps: []
related: [TK119, P21]
parent:
labels: [formal]
source: docs/tk119-leaf-rules-differential-2026-10-14.md
source_hash:
created: 2026-10-14
moved: 2026-10-14
updated: 2026-10-14
closed:
---

Leftovers from the TK119 build (builder notes, transcribed at TK119's close into the "Corrections 2026-10-14 (build, appended at close)" block of `docs/tk119-leaf-rules-differential-2026-10-14.md`). Each was READ first-hand as still true on 2026-10-14 by the round-4 `rows` agent unless marked.

1. `formal/lean/ZanzibarProofs/GraphIndex/LeafRules.lean`, the "Measured before it was written" docstring: still states the 2026-08-16 "50 / 50 schemas match, 0 mismatches ... 32 have a non-empty leaf rule set" (line 92, dated 2026-10-14). Replace it with a citation of `formal/conformance/test_conformance_leaf_rules.py` (the claim_rot lint accepts a cited number). Same file, `schemaRewritesL` docstring (line 127): "Order mirrors `compile_ruleset`" holds within a derived key only; Python walks `sorted(tainted)`, the model walks declaration order (TK119 challenge C2). Lean edit: rebuild cost is a 25-module cone (builder), and the docstring change moves no statement or definition pin, but run the `lean` phase.
2. Challenge X7: `tests/test_tk126_ttu_target_name_collision.py::SERVED` is still its own dict instead of importing `formal/conformance/corpus.py::TK126_SERVED_SCHEMAS`. A drift test holds the two equal today; the import removes the duplicate.
3. `formal/CORRESPONDENCE.md`, the zcli exit-code paragraph: still says rc 5 is "an `"ops"` stream passed in spec mode". Per the builder rc 5 now covers the spec, fragment and leaf-rules modes (re-READ `Cli.lean`'s header before editing). The builder also noted the conformance-module table there lacks the new module (UNVERIFIED by `rows`).

All three are honesty fixes on the assurance surface (a stale number in a docstring, a duplicated fixture, a stale rc table), in scope of the current goal. Size S.

## Read first

- `docs/tk119-leaf-rules-differential-2026-10-14.md` (Corrections 2026-10-14 (build, appended at close); challenge C2, X7).
- `formal/lean/ZanzibarProofs/GraphIndex/LeafRules.lean`.
- `formal/conformance/test_conformance_leaf_rules.py`.

## Log
