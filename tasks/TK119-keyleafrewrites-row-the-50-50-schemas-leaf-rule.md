---
id: TK119
title: keyLeafRewrites row: the 50/50 schemas leaf-rule claim is unbacked; make it a test or drop it
brief: CORRESPONDENCE keyLeafRewrites 50/50 claim has no test behind it; test it or delete the number
pri: NEXT
size: S
deps: []
related: []
parent:
labels: [formal]
source: docs/p13-claim-rot-gate-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-10-14
updated: 2026-10-14
closed:
---

Filed 2026-09-27d from the P13 build (docs/p13-claim-rot-gate-2026-09-27.md). The new prose-number lint (formal/conformance/claim_rot.py, verify.sh step 4d3) found seven uncited ratio claims in formal/CORRESPONDENCE.md on its first run; each was marked past (dated + pastness word) so the lint passes. One of them, the keyLeafRewrites row's "50/50 schemas" leaf-rule comparison, came from a one-off 2026-08-16 probe that NO test re-runs, so nobody knows whether it still holds. Either turn the comparison into a test (and cite it in the row's sentence, which the lint accepts) or delete the number and say what was checked. Do not just leave it marked past -- that is the lint's escape hatch, not a verification.

## Log

### 2026-10-13d

Sprint re-rank 2026-10-13d (user-approved in chat): LATER -> NEXT. An untested number in CORRESPONDENCE is exactly the honest-assurance goal; S-sized.

### 2026-10-14

DECISION (session 2026-10-14, user-approved in chat): make the claim a DIFFERENTIAL TEST that runs the Lean definition itself. Do not delete the number, and do not revive the 2026-08-16 Python transcription.

Plan:
1. New zcli mode "leaf-rules" in formal/lean/ZanzibarProofs/Cli.lean, beside spec/graph/graph-state/fragment. It emits schemaRewritesL S (GraphIndex/LeafRules.lean) as canonical JSON, and mode validation still rejects unknown modes with rc 4.
2. New formal/conformance/test_conformance_leaf_rules.py. It diffs that output against the Rules from src/zanzibar/schema/compiler.py::compile_ruleset, normalised to the RRule shape, over the conformance corpus. It asserts 0 mismatches plus a non-vacuity floor (schemas with a non-empty leaf rule set >= N, with N recorded with its provenance).
3. Sabotage: break the leaf index in src/zanzibar/schema/boolean.py::_emit_leaf_expr (the S9 shape) and watch the test go red. Record the literal output in the docstring and the commit message.
4. Rewrite the formal/CORRESPONDENCE.md keyLeafRewrites row and the formal/lean/ZanzibarProofs/Audit.lean comment (~L1987, dated 2026-10-14) to CITE the test instead of the dated past-tense number. The claim_rot lint accepts a cited number.

Why: the graph/graph-state modes already exercise the leaf rules end to end (Cascade.lean::writeLoggedRules -> LeafRules.lean::rewriteClosureL), but end-state agreement does not show rule-set identity. A Python transcription tests a copy of the model, and copies are how this claim went unchecked.

Expect red: TK132's gap (Lean isPure .ttu looks up by NAME, Python by (type, relation)) post-dates the 2026-08-16 probe. The corpus must include a TTU-target-over-tupleset schema. A mismatch there gets a POSITIVE pin (never an xfail), is handed to TK132, and the row says the claim holds except for that shape. The real size is closer to M than S (Lean JSON emitter + Python normaliser).

Scout + challenge, 2026-10-14. Map: docs/tk119-leaf-rules-differential-2026-10-14.md (ACTIVE-PLAN; challenge corrections at the top). Plan: a new zcli leaf-rules mode emits Lean schemaRewrites / leafRewrites as JSON and a conformance test compares them with Python compile_ruleset as multisets.

MEASURED (scout PROBE, re-run independently by challenge-TK119 with its own source list and normaliser): 82 requests, 66 compile, 62 match as multisets, 4 MISMATCH: tk126 D, D_nested, SlXt, and the constructed W3. All 4 are the TK132 class (Lean isPure asks a TTU target by name), so they become POSITIVE pins (_TK132_EXPECTED), handed to TK132, never xfails. 43 matched sources have a non-empty leaf half (corpus + fixtures alone: 32, the 2026-08-16 figure). No corpus source has a leaf TTU rule or a merged closure leaf, so the old 50/50 claim only ever compared single-computed-arm leaves; constructed witnesses (W1-W6, W3b) are load-bearing (challenge C3: an S11 twin leaves every corpus source green). Within-key leaf order and untainted-half order are equal; only cross-key order differs (Python sorted(tainted)), so the schemaRewritesL docstring must say exactly that.

CHALLENGE CORRECTIONS adopted:
X1 the scout's sabotage numbers came from a recursive monkeypatch that also moved RewriteFilter routing; use a RULE-ONLY off-by-one at the out.append(_rewrite_rule(...)) line in boolean.py (dry run: 47 mismatches, 0 extra refusals) and record what the real temporary edit prints, not a dry-run count.
X2 "S9" is a Lean-side name that breaks the Lean build; the docstring sabotage set is (a) rule-only off-by-one, (b) S11 twin, (c) S9 Python twin (proves refusal-as-failure), (d) a Lean emitter control.
X3 the normaliser must check every init field of RelationalTriplePattern (object_match_wildcards was missed), derived from dataclasses.fields, and assert then_pattern is not None.
X4 floors by NAME, not count: {W1,W5,W3b} <= leaf_ttu_matched, {W2,W6,W3b} <= merged_matched, corpus key set == ALL_CORPORA keys; keep >= 43 non-empty; group merged leaves by (objectType, outRel).
X5 Lean instrument control: strip the leaf index from outRel (not leaf=[]).
X6 expected refusals: zero. Sweep ALL_CORPORA + fixtures + witnesses + tk126 SERVED so any refusal fails; if an allow-list survives, pin the exception class and a message substring.
Also in the doc (X7-X13): move witness constants into corpus.py rather than importing test_tk126 (X7); comment on P21 at close (X8); fix both stale rc comments in runner.py (X9); add an (a or a) but not c witness so multiset vs set matters (X10); assert the mismatch set EQUALS _TK132_EXPECTED keys, and land TK119 before TK132, never two lake builds at once (X13).

STATUS: the build is starting in the main tree (2026-10-14). Nothing landed yet. Open: the build, its sabotage record, the phased gate. Not closed here.
