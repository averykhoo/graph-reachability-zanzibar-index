---
id: TK161
title: residue userset arm phantom branch (subj is None): pin it or delete it
brief: reachable only from a seedless facade since TK144; P6 sabotage S1 is inert there
pri: LATER
size: S
deps: []
related: [TK144, TK138]
parent:
labels: []
source: docs/tk138-userset-self-relation-2026-10-14.md
source_hash:
created: 2026-10-19
moved: 2026-10-19
updated: 2026-10-19
closed:
---

Follow-up from TK144 (TK138 landing 2), OPEN item 2. After TK144 the residue userset arm's phantom branch (the `subj is None` returns in `src/zanzibar/graphindex/wildcard.py::WildcardIndex._check_derived`, line numbers as of 2026-10-19) is reachable only from a facade built with no seed table (`SchemaInfo.self_seeds` empty). Evidence (first-hand, 2026-10-17, recorded in `tests/test_p6_phantom_subject.py`'s docstring and `formal/FINAL_REVIEW.md` section 3.1 item 9): that module's recorded sabotage S1 is now INERT at its old site (S13: 183 passed across 11 derived-read modules), while the same edges-alone reading on the C5 return is RED (S14).

Decide: either pin the branch with a test that builds the seedless facade and asserts its answer (and sabotage it red), or delete the branch if no public construction path can reach it. Either way, update the P6 module docstring so its sabotage is not left inert.

## Read first

- `docs/tk138-userset-self-relation-2026-10-14.md`, Corrections 2026-10-17 (the end-of-stage block: SABOTAGE S13/S14).
- `tests/test_p6_phantom_subject.py` module docstring.

## Log
