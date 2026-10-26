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
moved: 2026-10-26e
updated: 2026-10-26e
closed: 2026-10-26e
---

Follow-up from TK144 (TK138 landing 2), OPEN item 2. After TK144 the residue userset arm's phantom branch (the `subj is None` returns in `src/zanzibar/graphindex/wildcard.py::WildcardIndex._check_derived`, line numbers as of 2026-10-19) is reachable only from a facade built with no seed table (`SchemaInfo.self_seeds` empty). Evidence (first-hand, 2026-10-17, recorded in `tests/test_p6_phantom_subject.py`'s docstring and `formal/FINAL_REVIEW.md` section 3.1 item 9): that module's recorded sabotage S1 is now INERT at its old site (S13: 183 passed across 11 derived-read modules), while the same edges-alone reading on the C5 return is RED (S14).

Decide: either pin the branch with a test that builds the seedless facade and asserts its answer (and sabotage it red), or delete the branch if no public construction path can reach it. Either way, update the P6 module docstring so its sabotage is not left inert.

## Read first

- `docs/tk138-userset-self-relation-2026-10-14.md`, Corrections 2026-10-17 (the end-of-stage block: SABOTAGE S13/S14).
- `tests/test_p6_phantom_subject.py` module docstring.

## Log

### 2026-10-26e

Pinned, not deleted (deleting the `subj is None` disjunct would turn a seedless phantom read into AttributeError). New tests/test_tk161_seedless_phantom_arm.py: P6 schema/store via ParityEngine, then a seedless WildcardIndex (replace(schema_info, self_seeds=frozenset())) over the same index; asserts non-vacuity and that f9#viewer at admin/gate equals the live unanimous answer. Sabotage formal/probes/tk161_sabotage_2026_10_26.py: S1 (userset arm requires a node) RED 2 failed 2 passed; S2 wrong-arm control inert. P6 docstring, CORRESPONDENCE.md TK144 note and FINAL_REVIEW.md 3.1 item 9 updated. No src change, no userdocs/CHANGELOG change. Doc: docs/tk161-seedless-phantom-arm-2026-10-26.md. Ran: tk161 + p6 + tk138 modules, 25 passed. Next: the gate (doc_counts block may need regeneration for the new tests).

Repair round 1 (2026-10-26): (1) BARE-subject arm ghost branch now pinned: BARE_SCHEMA + test_bare_ghost_* in tests/test_tk161_seedless_phantom_arm.py (ghost user:zed under user:* on a but-not relation, compiled public read + seedless facade). Sabotage via formal/probes/tk161_sabotage_2026_10_26.py: none 8 passed; S1 2 failed/6 passed; S2 4 passed/4 errors (ParityEngine ghost grid: graph=False oracle=True on zz-ghost). Literal output in the module docstring and a dated Correction at the top of docs/tk161-seedless-phantom-arm-2026-10-26.md. (2) P6 docstring reworded: S1 still inert in P6, live only in the TK161 module. (3) Ran doc_counts --generate: counts block regenerated (3105 tests) and MIN_TESTS_ALL ratcheted 3067->3105 in formal/verify.sh; --check green. Rerun: TK161 + P6 + refused-shape modules 50 passed. Next: the gate/commit stage (re-run doc_counts --generate if other agents add tests).
