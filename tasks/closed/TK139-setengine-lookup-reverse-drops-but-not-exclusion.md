---
id: TK139
title: SetEngine.lookup_reverse drops but-not exclusions (excluded_node_ids empty) under a user:* grant
brief: 0.0.4 trial BROKEN-1: SetEngine.lookup_reverse drops but-not exclusions under user:*; reads as every user
pri: NEXT
size: S
deps: []
related: []
parent:
labels: []
source: docs/pypi-trial-0.0.4-2026-10-13.md
source_hash:
created: 2026-10-13c
moved: 2026-10-13d
updated: 2026-10-13d
closed: 2026-10-13d
---

BROKEN in the 0.0.4 install trial, re-run first-hand: `docs/pypi-trial-0.0.4-2026-10-13.md`
(BROKEN-1, repro p05 inline there).

With `define viewer: [user:*] but not banned`, a `user:*` grant and `mallory` banned,
`SetEngine.check(mallory)` is False but `SetEngine.lookup_reverse("viewer", "doc", "d")`
returns `markers={('user','...')}` with `excluded_node_ids=set()`: it reads as "every
user". `expand` carries the exclusion in `neg`; `lookup_reverse` copies only `pos` and
`stars`. `ConnectedStore.lookup_reverse` fills `excluded_node_ids`, and the PyPI README
tells users to subtract it. `tests/test_lookup_oracle.py` calls the drop intentional ("S3
lookup_reverse is the documented neg-dropping render of expand"), but nothing a user sees
says so, so a list-users UI over-grants.

Fix direction: fill `excluded_node_ids` from `neg` (as `SetEngine.lookup` already does),
so both backends render the same `LookupResult`; then flip the lookup-oracle property
that pins the drop. A positive pin, both backends, sabotage red.

## Read first

- `src/zanzibar/setengine/engine.py::SetEngine.lookup_reverse` and `SetEngine.lookup`.
- `tests/test_lookup_oracle.py` (the S3 property).

## Log

### 2026-10-13d

FIXED. SetEngine.lookup_reverse now sets excluded_node_ids = expand neg (src/zanzibar/setengine/engine.py::SetEngine.lookup_reverse), so both backends render the same LookupResult up to id domain. Map, census, sabotage literal output: docs/tk139-lookup-reverse-exclusions-2026-10-13.md (FROZEN). LANDED: positive pin tests/test_tk139_lookup_reverse_exclusions.py (p05 repro + mixed-grant twin, both SetOps, set vs ConnectedStore keys equal, README subtraction equals oracle); tests/test_lookup_oracle.py S3 tightened to exact two-sided (excluded == neg, exclusion soundness, oracle exactness) + test_tamper_set_reverse_is_caught; stale drop wording fixed in LookupResult comment, LookupNotFresh docstring, dated corrections in spec-deviations + decision-log, PYPI_README SetEngine paragraph, CHANGELOG Unreleased Fixed. Sabotage (fix line -> pass): 7 failed incl. both new pins; with S3 structural equality also disabled the oracle half alone went red. Targeted: test_matrix 17 passed; 12 lookup modules 239 passed. NOT RUN: verify.sh gate. Follow-up: generated-schema lookup gate (ci, 6 examples) did not catch the sabotage; only dense_boolean + tamper did (doc sec 5).

Review fixes (fix lead, 2026-10-13d; all RUN first-hand). Doc: docs/tk139-lookup-reverse-exclusions-2026-10-13.md, dated correction at the top. LANDED: (1) claim-rot pin regenerated after re-reading CORRESPONDENCE.md L1901 (still true); the TK139 body change had left tests/test_claim_rot_gate.py RED, 8 failed; now 42 passed. (2) SetEngine.excluded_keys added; result_keys and LookupResult docstrings no longer call node keys alone the portable form; PYPI_README + CHANGELOG (Added) updated; pin test_excluded_keys_is_the_portable_exclusion_channel, sabotage excluded_keys->set() gave 6 failed. (3) docs/spec-deviations.md 2026-07-12 entry (set lookup_reverse drops neg) got a dated correction. (4) The gate gap is wider than sec 5 said: under M1 all 9 test_lookup_oracle -k gate tests stay green; filed as TK142. RED: none in the targeted set (349 passed, 13 modules). Next: TK142.
