# TK128-TK131 context-framework housekeeping: agent reports (2026-10-07d)

**FROZEN 2026-10-07d.** Verbatim transcription of the seven agent reports from the gitignored
`.scratch/hk-2026-10-07d/` (one workflow: four implementers, two adversarial reviewers, one fixer),
kept because they carry the moved-text tables (each removed `CLAUDE.md` / `HANDOFF.md` /
`formal/HANDOFF.md` passage and its surviving home, quoted) and the sabotage sweeps. Labels:
AGENT reports; the orchestrating session re-checked key rules by grep and ran the full gate.
Live state is `python scripts/task.py show TK128` .. `TK131`, never this file.


---

## Report: impl-tk128-129

### impl-tk128-129 (session 2026-10-07d)

## Census (first-hand, 2026-10-07, probe .scratch/hk-2026-10-07d/cap_census.py)
- Candidate "tier ... cap of N" pattern over check_restated_counts scope: 2 hits --
  HANDOFF.md:21 "NEXT`'s cap of 3" (STALE; line is dated 2026-09-22 so the dated escape is
  why the existing check could never have caught it) and docs/README.md:159 "cap of 5" (correct).
- Comparison form NEXT<=N: docs/tasktool-spec.md:343 "NEXT<=3" (LIVING, stale -- same rot);
  docs/tasktool-trial-protocol.md / tasktool-trial-stub.md also say <=3 but are FROZEN (exempt).
## Text edits done
- HANDOFF.md banner: "cap of 3 ... at three" -> "cap (`tasks/config.json` `budgets`)"
- docs/README.md sec 4 (line ~159): "cap of 5 ... at five" -> pointer to config budgets
- docs/README.md sec 8 CLAUDE.md row: "the four footguns" -> "the standing footguns (listed there, not counted here)" (TK129)
- docs/tasktool-spec.md:343: "NEXT<=3 budget" -> "NEXT-cap budget (`tasks/config.json` `budgets`)"
## Lint extension (scripts/handoff_lint.py)
- New: TIER_CAPS, CAP_HOME, _CAP_PATTERNS (prose "cap of/capped at", comparison "NEXT<=N"),
  _keep_tier_names, _restated_caps; called inside check_restated_counts BEFORE the dated escape.
- Tests: 5 new in tests/test_handoff_lint_count_guard.py (tier caps section).
- In-memory mutation sweep (.scratch/hk-2026-10-07d/cap_sweep.py, output sweep.out): 9/9 caught; recorded in the test module comment.
## Checks (2026-10-07d)
- handoff_lint: clean (12 checks); task lint: clean (13 checks, 248 task file(s) parsed), 29 warning(s)
- pytest tests/test_handoff_lint*.py: 89 passed
- doc_counts --check: RED, tests/ 1749 -> 1754 (+5 = the new tests). Needs `python -m formal.conformance.doc_counts --generate` by the orchestrator before the gate.
- Gate path: verify.sh step 4f (lean) runs scripts/handoff_lint.py; check_restated_counts is in CHECKS (pinned by test_the_check_is_registered_in_the_gated_tuple); the tests ride the tests-tiles.
- Rows: progress comments on TK128 / TK129 (not closed).
## DONE

---

## Report: impl-tk130

### impl-tk130 (2026-10-07d)

Started.

## Measurements (first-hand READ, 2026-10-07)
- HANDOFF.md at my start: 18803 B / 56 lines (baseline copy 18785 B; +18 = TK128 edit). Banner = lines 16-29 = 14 lines = task.py::BANNER_MAX_LINES. Widest banner line 24: 3762 chars.
- Enforcement: handoff_lint.py::check_ceilings (MAX_LINES) = verify.sh step 4f; task.py::check_banner (check 12, BANNER_MAX_LINES) = verify.sh step 4g. Both in lean phase (formal/verify.sh ~:1143, :1203).
- Plan: MAX_BYTES beside MAX_LINES in handoff_lint (check_ceilings); BANNER_MAX_WIDTH beside BANNER_MAX_LINES in task.py check 12.

## Banner layer audit (first-hand READ via grep, 2026-10-07)
Session-log entries exist for every layer key (2026-10-06 :188, 2026-10-05 :280, 2026-09-22c :1901, 2026-09-22 :2107, 2026-09-13..13e, 2026-09-10/10b, 2026-09-08b, 2026-09-15, 2026-09-14h/i, 2026-09-16, 2026-09-17, 2026-10-03b :817).
Durable-rule homes:
- L17 TK120 -> CLAUDE.md Layout + Running things (TK120); FROZEN docs/tk120-repo-restructure-2026-10-05.md.
- L18 TK107 -> CLAUDE.md gotcha TK106 bullet (TK107 deletion); FROZEN docs/tk107-...
- L19 goal -> docs/goal-census-2026-09-22.md (ACTIVE-PLAN); P4/P5/P14 closed (tasks/closed/).
- L20 perf -> tasks/R6-perf-round-6-*.md ### 2026-09-22c (:174 no perf target, :185 TK34 first move).
- L21 ASK -> docs/README.md sec 4 :154-171 (incl. compass badge row), tasks/README.md sec ASK-*.
- L22 gate/t2c -> docs/README.md sec 7 tail (t2c includes tasks/*.md and HANDOFF.md). KEPT short.
- L23 figure escapes -> docs/README.md:49 'Four structural escapes exist...'.
- L24 sabotage sweep -> docs/sabotage-procedure.md: M0 (:366), INERT non-vacuity (:393-402), Lean error-recovers/helper/at-least-these (:409-437). NOT homed: CEILING control, red-on-a-proof, concrete-witness defeq-blind -> PROMOTED (new block after :437).
- L25 two gate runs -> CLAUDE.md footgun 1 (2026-09-10 variant, one phase per command).
- L26 P6 -> P6 row (RulesBareStar x11, 2026-09-15d park x5, audited-name must-stay x9); docs/p6-step3b-plan-2026-09-13.md:1318.
- L27 P24 row SOMEDAY; P22 closed; counting unit in P6 row :180/:548; TK86 row LATER.
- L28 correctness bugs -> session-log 2026-10-03b; TK111-113 closed. TK73 two-fixes rule NOT homed as a general rule (only docs/tk73 doc:118 + closed row) -> PROMOTED to sabotage-procedure.md.
- L29 specs frozen -> docs/README.md sec 3 :133-134; spec-deviations routing sec 8.
- L16 TK127 -> release recipe in .github/workflows/publish.yml header + TK127 row (procedure 1-6, concurrency trap). Kept, tightened.

## Done (2026-10-07d)
- HANDOFF.md: 18803 B / 56 lines -> 3415 B / 44 lines on disk (CRLF); 3371 B LF. Banner 14 lines -> 2 (TK127 line tightened; gate line kept). Bold PUBLISHED/BROKEN lowercased: once the banner lost its warning glyph, the paragraph-scoped trap exemption in handoff_lint._boldcaps_lines stopped covering it. FINDING: the whole old 14-line banner had been one blank-free block containing the warning glyph, so the exemption covered ALL of its bold caps.
- scripts/handoff_lint.py: MAX_BYTES = {'HANDOFF.md': 5000} + byte loop in check_ceilings (CHECKS[0], verify.sh 4f). Measured on LF text.
- scripts/task.py: BANNER_MAX_WIDTH = 600 + width check in check_banner (LINT_CHECKS[11] = check 12, verify.sh 4g). Lint only, not render.
- docs/sabotage-procedure.md: 4 promoted lessons (block after the TK68 generalisation, end of sweep section).
- docs/README.md sec 7 step 2, docs/tasktool-spec.md check 12, docs/gate-runbook.md caps row (also replaced stale "at most three NEXT rows", a TK128 residual).
- tests/test_tk130_handoff_size_caps.py: 9 tests; sweep table in docstring (11 mutants all caught, M0/M0b controls red as named, M0c blind spot documented).
- Checks: handoff_lint clean (12 checks); task lint clean (13 checks, 248 files, 29 warnings pre-existing); board rc 0 (31 lines); pytest tk130 + handoff_lint_* + test_tasktool: 201 passed.
- TK130 comment logged (not closed).
- Open: doc_counts --generate needed (tests/ +9 more). Goal 2026-09-22c ("honest and legible, not wider") now lives only in docs/goal-census-2026-09-22.md (ACTIVE-PLAN) + session-log; orchestrator may want a one-line pointer.

---

## Report: impl-tk131-claude

### impl-tk131-claude (2026-10-07d)

## Baseline (2026-10-07)
- CLAUDE.md before: 45483 B on disk (CRLF), 558 lines. Pristine copy .scratch/hk-2026-10-07d/baseline/CLAUDE.md == working copy at start.
- Model: audio-workspace src/__tests__/claudeMdShape.test.ts: MAX_BYTES = 40_000, MAX_ROW_BYTES = 600 (authority-table rows).

## Step 3 census: what pins CLAUDE.md text (first-hand grep)
- scripts/handoff_lint.py::LINKED_DOCS includes CLAUDE.md (check_doc_links; floor MIN_DOC_LINKS=100 across 8 files).
- scripts/handoff_lint.py::COUNT_DECLARED includes CLAUDE.md (check_restated_counts + TK128 tier-cap check).
- formal/conformance/doc_counts.py::_PROSE_GLOBS includes CLAUDE.md (corpus-count prose check, verify.sh 4e).
- No test reads CLAUDE.md text; tests/test_handoff_lint_count_guard.py uses a synthetic CLAUDE.md stub.
- Section-anchored cites elsewhere: "Who decides" (40+), "Delegation", "Gotchas", "Running things", "SCOUTING IS A DELIVERABLE", "Perf work & the Lean model", "record-keeping", "The five standing footguns" (session-log only, history). All headings kept except the footgun count word.
- verify.sh lean step 4f runs "$REPO_ROOT/scripts/handoff_lint.py" (formal/verify.sh ~:1144).

## Result (2026-10-07d)
- CLAUDE.md after: 31404 B on disk (CRLF) / 31017 B LF / 387 lines (was 45483 / 44925 / 558): -13908 B LF (-31%), -171 lines.
- Cap: scripts/handoff_lint.py::MAX_BYTES['CLAUDE.md'] = 32500 (headroom 1483 B < one re-added case history 1970 B). Per-file remedy text: handoff_lint.py::BYTE_CAP_REMEDY. Per-row cap NOT ported (no table in CLAUDE.md; reason in the constant comment).
- Gate path: check_ceilings is CHECKS[0]; formal/verify.sh lean step 4f runs "$REPO_ROOT/scripts/handoff_lint.py" (pinned by tests/test_tk131_claude_md_cap.py::test_the_cap_rides_the_gated_check).
- Tests: new tests/test_tk131_claude_md_cap.py (6 tests); tests/test_tk130_handoff_size_caps.py seed helpers now also write CLAUDE.md (2 one-line edits) since check_ceilings now reads it.
- Baseline probe (.scratch/hk-2026-10-07d/tk131_baseline_probe.py) on pre-prune CLAUDE.md: "CLAUDE.md is 44925 bytes, ceiling 32500 (MAX_BYTES; LF line endings). It is auto-loaded into every session, ..."
- Sweep (.scratch/hk-2026-10-07d/tk131_sweep.py -> tk131_sweep.out): NONE 6 passed; M0 2 failed; M0b 1 failed; M0c 6 passed (expected); M1 1 error; M2..M6 1 failed each on the named test. Table transcribed into the test docstring.

## Moved / removed text and its home (first-hand grep, 2026-10-07d)
| removed from CLAUDE.md | home (quoted) |
|---|---|
| footgun 1 variants 2026-09-08b (loop orphan) and 2026-09-10 (fixed log path, lock) narrative | docs/gate-runbook.md:28 "ONE PHASE PER COMMAND — never a `for` loop over phases** (hit 2026-09-08b)"; :47 "two runs and one filename are enough** (hit 2026-09-10)"; :65 "a fixed log path is a shared resource" |
| footgun 1 variant 2026-09-16b (trailing grep) narrative | docs/history/session-log.md:4006 "was GREP's, not pytest's. The standing rule (`CLAUDE.md`, footgun 1) is written about"; rule itself KEPT in CLAUDE.md (echo the verdict) |
| footgun 1 "Bit 2026-08-10 ... 08-11 ... 08-14" | dated history; basic rule at docs/gate-runbook.md:819 "Capture exit codes without pipes" |
| "docs/gate-runbook.md carried a wrong value for three weeks" | docs/history/session-log.md:8389 "carried a wrong value for three weeks by doing so" |
| temp-index trap "promoted here 2026-09-19d" provenance | rule kept; trap source formal/history/leaf-family-split-scope-2026-08-05.md:1946 "(ee) NEW 2026-09-05b — TAKE A RED SNAPSHOT WITH A TEMP INDEX" (now cited) |
| cutover archaeology (trial dates, DELETE off the table 2026-08-30, revertable commit) | docs/tree-sole-authority-spec-2026-08-29.md + docs/tasktool-trial-protocol.md (FROZEN, still linked); retired verbs: docs/tasktool-spec.md:5 "`sync`, `ack` and lint check 13 RETIRED (section 4, "The retired verbs"; section 5) and `source_hash` froze"; :72 "(BANNER.md lived here until 2026-09-06; now a tombstone, check 12)" |
| `.scratch/tasktool/` deleted 2026-09-07 + archive link; tasktool-proof history link | docs/history/tasktool-scratch-archive-2026-09-07.md, docs/history/tasktool-proof-2026-08.md (files themselves; also linked from docs/tasktool-spec.md) |
| SCOUTING: p6 precedent narrative ("nine-agent sweep ... fifteen-step map") | docs/p6-step3b-plan-2026-09-13.md itself (still linked) |
| COMMIT rule's "old rule" narrative | rule + one-line why kept |
| record-keeping incidents (P7 cost analysis, sab_s4/sab_s5 green sabotage, test_fixture_earns_its_place, "26 passed" -> 12) | docs/history/session-log.md:10600 "extend `test_fixture_earns_its_place` corpus-wide" — there is no such test"; :10605 "`P7`'s entire cost analysis existed only in gitignored `.scratch/`"; :9608 "A green sabotage had been run and left out of the record. `S4` ..."; :9623 "the "26 tests" figure was a `26 passed` summary line from a three-module run misread as a module count (it collects 12)" |
| Delegation: list of what ~/.claude/CLAUDE.md carries | ~/.claude/CLAUDE.md § Delegation (auto-loaded) |
| ZANZIBAR_PY "this bullet said X until 2026-08-30", resolve_py :297-320, avery path | docs/gate-runbook.md:81 "**Interpreter.** `verify.sh` resolves it itself (since 2026-07-26): `ZANZIBAR_PY` wins if set ..." |
| "verify.sh:123" line number for elan | rule kept without line number |
| counts history "1227 ... 762 + 465 ... 879 / 494" | narrative only; rule kept with one-line why (ZT-P3-5). The exact old figures remain in git history (`git show e8b340b:CLAUDE.md`) |
| Legacy `conf-heavy`/`conf-rest` | docs/gate-runbook.md:254 "**Legacy phases still work.** `conf-heavy` ..." |
| `lean` job hands `zcli` to conformance tiles; release checks list | .github/workflows/gate.yml; .github/workflows/publish.yml header + validate-tag / stage 3 "build once, prove it, attest it, ship it" |
| PG leg "found three real bugs the first day" | docs/gate-runbook.md:159 "it found three real bugs the first" |
| Gotchas "Supported backends": duplicate pg_local recipe | kept once in Running things |
| Gotchas duplicate "Never edit a golden/oracle result" | merged into Testing conventions bullet (snapshots byte-identity kept) |
| sabotage historical case list | docs/sabotage-procedure.md:22-28 table ("`HYPOTHESIS_SEED` fuzz sweep | six seeds | ran the **same** seed six times", axiom audit, pyroaring, continue, tests/ outside gate, SERIALIZABLE) |
| lookup-oracle "(how X1–X4 were closed; see spec-deviations 2026-07-12/13)" | docs/spec-deviations.md (dated entries) |
| Pre-TK120 names list; legacy/ deleted, MultiSet moved | docs/architecture/overview.md:90 "## Renamed in TK120 (2026-10-06)"; :100 "| `legacy/` (v1-v3 indexes) | deleted; `MultiSet` -> `zanzibar.graphindex.multiset` |" |
| schema package module list, SchemaInfo, validate_write_identifiers, Interner/NodeSets | docs/architecture/overview.md:49 "rules.py Entity/RelationalTriple/Filter/Rule, SchemaInfo, RuleSet"; :54 json_frontend; :71 "NodeSets, check/expand/lookup, rebuild()"; decision-log.md:217 validate_write_identifiers |
| UnsupportedByGraphIndex scope examples | docs/architecture/derived-predicates.md:45 "**Scope rejections** (`UnsupportedByGraphIndex`" |
| ASK-1 details (nested groups, _stratify only form, bare restriction types, oracle unchecked twin) | docs/ask1-schema-self-consistency-2026-09-26.md:66, :83-84, :138; docs/spec-deviations.md:3671 "the undefined bare restriction TYPE is still" |
| TK107 deleted symbol list, _validate_ttu_tuplesets on unchecked AST | docs/tk107-tainted-tupleset-removal-2026-10-05.md:21-27 |
| refused-shape MIN_HEADERS detail | tests/test_refused_shape_comments.py:23 "Per-file header floors with ZERO headroom** (`MIN_HEADERS`" |
| ASK-2: pytest.ini ignores warning; registry idiom reason | pytest.ini:44 "Ignored, not promoted: zanzibar.schema.UnprovenExtensionWarning (ASK-2"; docs/architecture/decision-log.md:243 "fail-open under `but not`" |
| knobs: ~+5% residue cost, int4 ceiling, stalled_after, "region must stay shrinkable", "since 2026-10-02b" | docs/spec-deviations.md:3304 "a silent ~5%-and-"; docs/tk111-stall-aware-freshness-2026-10-02.md:297 "the int4 ceiling on both dialects", :44 "`IndexCursorV1.stalled_after`", :222 revocations-exempt discussion; "shrinkable" in docs/spec-deviations.md + src/zanzibar/graphindex/core.py |
| status-lines examples + promotion provenance | rule kept |
| Perf/Lean "(differential matrix + hypothesis + conformance are the net)", "Since 2026-07-27" | rule kept; formal/CORRESPONDENCE.md §7/§8 |
## Checks (final)
- handoff_lint: clean (12 checks); task lint: clean (13 checks, 248 task file(s) parsed), 29 warning(s); pytest 7 modules: 235 passed in 63.16s; doc_counts --check: only the generated counts block stale (tests/ 1749 doc vs 1769 tree, +20 across TK128/TK130/TK131).

---

## Report: impl-tk131-formal

### impl-tk131-formal (2026-10-07d)

Started.

## Measurements (first-hand READ, 2026-10-07)
- formal/HANDOFF.md before: 520 lines / 40412 bytes; cap scripts/handoff_lint.py::MAX_LINES['formal/HANDOFF.md'] = 520.
- Bold-caps offenders before (handoff_lint._boldcaps_lines): lines [49, 330, 375, 503, 507, 511] = 6 = MAX_BOLDCAPS budget.
- Readers of formal/HANDOFF.md content: only scripts/handoff_lint.py (check_ceilings, check_no_stars, check_bold_caps, check_doc_links via LINKED_DOCS) and formal/conformance/doc_counts.py (_PROSE_GLOBS formal/*.md, corpus-count claims; history/ exempt). No test reads its sections/anchors. Rule cites are BY NUMBER (statement_pin.py:38 rule 1, docs/sabotage-procedure.md:822 rule 2) -> house rules untouched.
- Homes for live traps in moved blocks: graphModeAnswers_eq_sem pin -> CORRESPONDENCE.md row at :444 + statement_pin.py:222-229 comment; fence_changes_answer -> CORRESPONDENCE.md :319 row ("only that one does"); String.contains -> Leaf.lean:205-207 docstring; binary Expr n-ary limit -> CORRESPONDENCE.md :997-1006; ttuStarFree UNCHANGED -> CORRESPONDENCE.md :363.
- "retiring an id is not closing a finding" lesson: only home is formal/HANDOFF.md -> kept as a line.

## Done (2026-10-07d)
- formal/HANDOFF.md: 520 lines / 40412 B -> 241 lines / 19636 B.
- New formal/history/handoff-retired-2026-10-07.md (FROZEN banner line 3; 366 lines / 27020 B). Verbatim check: diff of baseline ranges 63-83,85-216,322-434,451-478,503-512 vs archive body differs only by inserted blank separator lines.
- Replacements in formal/HANDOFF.md: header resume pointer (PROOF_STATUS top entry), doc-table row for new archive, "Also closed" P14/option-(c) pointer, 5-bullet "Standing formal traps" list (homes: statement_pin.py::HEADLINE, CORRESPONDENCE.md Exec.lean::graphRun + GraphModel.checkPublic rows + sec 7.2, FullScope.lean::W4WitnessDirect.fence_changes_answer, Leaf.lean::isLeafPred; the id-retirement lesson kept since its only home was here), leg-7 landed 4-line summary, T2a/P4 closed 3-line summary, final retired-zones pointer.
- House rules 1-7 untouched (cited by number by statement_pin.py:38 and docs/sabotage-procedure.md:822).
- Checks: handoff_lint clean (12 checks); task.py lint clean (13 checks, 248 files, 29 warnings pre-existing); pytest tests/test_handoff_lint_{b_prime,count_guard,row_ids}.py tests/test_zt_p5_readjudication.py -> 110 passed; doc_counts.check_corpus_count_prose -> 0 stale; doc_counts --check RED on tests/ count 1749 vs 1754 (other agents' added tests, not this change).
- Bold caps offenders now [52] = 1 vs MAX_BOLDCAPS 6 (slack 5) -> owner should lower to 1. Ceiling by landed+10% rule: 265.
- task.py comment TK131 --session 2026-10-07d logged.

---

## Report: review-checks-bite

### review-checks-bite (2026-10-07d)

Started.

## Run results (2026-10-07d)
- handoff_lint.py: rc=0, `handoff_lint: clean (12 checks)`
- task.py lint: rc=0, `task lint: clean (13 checks, 248 task file(s) parsed), 29 warning(s)`
- Gate path: formal/verify.sh lean step 4f (`"$PY" "$REPO_ROOT/scripts/handoff_lint.py"`, ~:1144) and 4g (`task.py lint`, ~:1204). Confirmed by READ.

## Finding A (tier-cap regex misses the phrasing that actually rots) -- first-hand probe
Probe .scratch/hk-2026-10-07d/tmp-checks-bite/variants.py: `_restated_caps` returns [] for
"at most three NEXT rows", "<= 3 NEXT", "up to 3 NEXT rows", "NEXT budget of 3", "NEXT (cap 3)", "the NEXT-cap of 3", "NEXT's cap: 3", "NEXT is capped to 3", "NEXT < 4".
Stale LIVE caps still in SCANNED, non-exempt docs (lint clean on them):
- docs/tasktool-spec.md:157 `exactly 1 NOW and <= 3 NEXT among OPEN tasks` (LIVING)
- docs/tasktool-spec.md:425 `exactly one NOW and at most three NEXT among OPEN tasks;` (LIVING)
- docs/tasktool-spec.md:525 fenced JSON example `"budgets": {"NOW": 1, "NEXT": 3}` (fence escape; nit)
- docs/gate-runbook.md:451-452 `at\n most three NEXT` (line-wrapped; per-line scan cannot see it)
Out of lint scope, also stale: scripts/task.py:2625 (check_tier_budget? docstring "Check 5: ... at most three NEXT"), formal/verify.sh:1134 comment.

## Finding B (gate_status scope hole for the new live-CLAUDE.md test) -- first-hand READ
tests/test_tk131_claude_md_cap.py::test_re_adding_the_pruned_case_history_to_the_live_file_is_red reads the LIVE CLAUDE.md
and asserts CAP - live_bytes < len(REGROWN_CASE_HISTORY) (headroom ratchet). scripts/gate_status.py::CODE_SCOPE_MD_KEEP = (b"tasks/", b"HANDOFF.md");
_in_scope drops every other *.md from t2c. So a CLAUDE.md-only edit (prune ~500 B) reddens tests-tile without staling the tile verdict:
gate_status reports COVERED on a red tree. gate_status.py's own comment: "Re-do [the survey] whenever a test module is added to the gate". Only this module reads live CLAUDE.md (grep).
Fix: add b"CLAUDE.md" to CODE_SCOPE_MD_KEEP (or move the headroom ratchet into handoff_lint check_ceilings, lean phase, all-scope).

## Finding C (formal/HANDOFF.md caps left loose) -- first-hand probe caps.py
lines formal/HANDOFF.md 241 cap 520 (landed+10% rule => ~265); no MAX_BYTES entry, widest line 639 chars (same line-length evasion TK130 closed for HANDOFF.md).
MAX_BOLDCAPS formal/HANDOFF.md budget 6, offenders 1 (ratchet slack 5). TK131 brief: "add caps and prune both".

## Finding D: doc_counts --check rc=1 (tests/ collected doc 1749 vs tree 1769; whole-repo 2836 vs 2856). lean step 4e red until --generate.

## Measured live (2026-10-07d): HANDOFF.md 44 lines/3371 B LF (cap 60/5000); CLAUDE.md 31017 B LF (cap 32500); bold-caps HANDOFF 0/0.
## Tests: test_tk130 + test_tk131 + count_guard + b_prime: 87 passed.

## Nits
- comparison form flags NEXT=0 / NOW=0 as a cap (none in scope today; census of all *.md: 0 such).
- test_the_cap_rides_the_gated_check / tk130 twin: substring check on verify.sh passes even if the 4f line is commented out.
- stale code comments out of lint scope: formal/verify.sh:1134, scripts/task.py::check_pri_budget docstring (:2625).
- check_bold_caps `continue`s on a missing file (pre-existing).
- _boldcaps_lines paragraph-scoped ⚠ exemption (pre-existing, TK130 noted, no row filed).
COMPLETE.

---

## Report: review-rules-preserved

### review-rules-preserved (2026-10-07d)

Reviewer: review-rules-preserved (read-only). Lens: did any rule, trap, footgun, user decision or invariant get lost or change meaning?

Method:
- `git diff --no-index` against `.scratch/hk-2026-10-07d/baseline/` for CLAUDE.md, HANDOFF.md, formal/HANDOFF.md and docs/README.md.
- `git diff HEAD` for sabotage-procedure.md, tasktool-spec.md and gate-runbook.md.
- A grep for each removed rule's surviving home.

## Verdict

No blocker: every removed rule has a surviving home (quoted below). There are 4 should-fix items and 4 nits.

## SHOULD-FIX

1. **The stale NEXT cap of 3 survives in LIVING contract text.** The live cap is 5 (`tasks/config.json` `budgets`). TK128 did not touch these:
   - `docs/tasktool-spec.md:425`: "5. exactly one `NOW` and at most three `NEXT` among OPEN tasks;". This is the spec of lint check 5, in the same file whose `:343` TK128 fixed.
   - `docs/gate-runbook.md:452`: "exactly one `NOW` row and at most three `NEXT`".
   - The `scripts/task.py::check_pri_budget` docstring: "Check 5: exactly one NOW and at most three NEXT".
   - `scripts/handoff_lint.py:15`, the module docstring: "at most three ``NEXT`` rows".
   - `formal/verify.sh:1134`, a comment: "at most three NEXT rows".

   TK128's census searched only for the phrasings its new lint matches. "at most three NEXT" is a form the lint deliberately does not match.

   Fix: delete the number at each site and point at `budgets`.

2. **formal/HANDOFF.md caps were not ratcheted after the prune.** The prune took the file from 520 to 241 lines and its bold-caps offenders from 6 to 1, but both caps are unchanged:
   - `MAX_LINES['formal/HANDOFF.md']` is still 520.
   - `MAX_BOLDCAPS['formal/HANDOFF.md']` is still 6.

   The rules in the file's own comments say to lower them:
   - Above `MAX_LINES`: "the ceiling drops to 520 as the same landed+10% rule prescribes".
   - On `MAX_BOLDCAPS`: "leaving it at 9 would have bought three free offenders ... re-created exactly the slack the original sabotage caught".

   Fix: set `MAX_LINES` to 265 (241 × 1.1) and `MAX_BOLDCAPS` to 1, then run a sabotage check.

3. **The user-chosen goal lost its session-start visibility.** The goal (2026-09-22c) is "Make the assurance surface HONEST AND LEGIBLE, not wider", with "stop widening the fragment" after P4→P5+P14. It was deleted from the banner. Where it survives:
   - `docs/goal-census-2026-09-22.md:222`/`:233`. This doc presents the goal as the census's recommendation, not as the user's choice. It is ACTIVE-PLAN, and its own freeze condition has already been met.
   - The R6 row, at LATER.
   - Closed TK94 `:84`.
   - The session log.

   It is not in `docs/architecture/decision-log.md`, which the routing table names as the home for "post-spec user adjudications".

   Fix: add a decision-log entry, and/or a one-line pointer in CLAUDE.md (1483 B of headroom).

4. **The 2026-09-22c perf ranking is no longer reachable from perf's routing home.** The rule itself survives on the R6 row (`:185`: "The honest first move is TK34 (the nightly canary), not an R6-N row."). But `docs/perf-next-round.md`, the routing home for perf, opens with a landing order and has no pointer to that note.

   Fix: add a one-line pointer to `docs/perf-next-round.md`.

## NIT

a. **The CLAUDE.md fan-out knob dropped the un-ban case.** The baseline said the cap covers "a grant restored by an un-ban". The new text says "Edge REMOVALS are never capped" next to "every sync edge ADD is capped", which a reader may take to mean that a tuple REMOVE is never refused. In fact the un-ban REMOVE is refused: tk111 doc `:196` says "D3 (the un-ban REMOVE) fails CLOSED".

b. **`docs/README.md:171` still restates the cap.** The compass row says "at most 5 (one per `NEXT` ASK)". TK128 removed "cap of 5" from §4 for exactly this reason. The value is correct today, but the lint does not match this form.

c. **The "five, not four" correction now lives only in a FROZEN archive** (`formal/history/handoff-retired-2026-10-07.md:65`). The doc it corrects, `formal/history/leaf-family-split-scope-2026-08-05.md`, is ACTIVE-PLAN and takes dated corrections at the top. Its `:66` still says "exactly four places".

d. **Two wording problems in the handoff files:**
   - `formal/HANDOFF.md:4` says "no dated blocks since 2026-10-07". The blocks stopped at 2026-08-28c and were MOVED on 2026-10-07. The directive "every session since is in PROOF_STATUS, not here" is now only implied.
   - HANDOFF.md's "Next session" section says "then `lean`, then commit". That contradicts its own Still-owed line, which says lean alone is not enough. This one is pre-existing.

## VERIFIED (first-hand READ)

**CLAUDE.md**
- "Who decides" is unchanged.
- Every footgun keeps its instruction. Footgun 1 still has mktemp, echo the verdict, one phase per command, no fixed log path, gate_lock, and the stray interpreter.
- The trap (ee) cite resolves: `leaf-family-split-scope-2026-08-05.md:1946`.
- The new t2c claim is accurate: `gate_status.py:215` has `CODE_SCOPE_MD_KEEP = (b"tasks/", b"HANDOFF.md")`.
- The oracle claim is accurate: `tests/oracle.py` imports only `re`, `dataclasses`, `types` and `typing`.

**Homes for removed CLAUDE.md details**

| Removed detail | Surviving home |
|---|---|
| fan-out default | `core.py:76` `DEFAULT_MAX_CLOSURE_FANOUT` |
| bare restriction types | `spec-deviations.md:3671` |
| MIN_HEADERS | `test_refused_shape_comments.py:23` |
| TK107 unchecked-AST refusal | `test_graphadmission_scope_pin.py:490` |
| schema "leaf first" | `schema/__init__.py` docstring |
| UnsupportedByGraphIndex | `derived-predicates.md:45` |
| legacy phases, three real bugs, interpreter | gate-runbook |
| release order | `publish.yml` header |
| incidents | session-log 2026-08-20b, `:9624`, `:10600` |

**Homes for removed banner rules**

| Removed rule | Surviving home |
|---|---|
| figure escapes | `docs/README.md:47-53` |
| specs not walked | `docs/README.md:133` |
| ASK series and `deps: [ASK-n]` | `tasks/README.md:88-116` |
| compass | `docs/README.md:171` |
| release procedure | TK127 row and `publish.yml` |
| P6 parked by user decision | P6 brief |
| audited names MUST STAY | P6 `:1612` |
| counting unit | P6 `:180` |
| TK86 | TK86 `:43` |
| M0, INERT, Lean error-recovery, "at least these" | `sabotage-procedure.md:366`, `:394-402`, `:409-428` |

**The promoted sabotage block** (`sabotage-procedure.md:439-457`) is accurate against the banner. Its cites resolve: tk77 `:457` and the tk73 doc.

**formal/HANDOFF.md traps resolve:**
- `statement_pin.py:229`
- `CORRESPONDENCE.md:319` ("only that one does")
- `Audit.lean:1645`

The B1 rule "closed where RECORDED" is the same lesson as kept trap 5, so its meaning is preserved.

---

## Report: fix-hk

### fix-hk report (2026-10-07d)

Started. Issues to verify: 8 reviewer findings.

## Issue 1+5 (stale NEXT cap sites; reversed phrasing unmatched) -- CONFIRMED first-hand
Independent census .scratch/hk-2026-10-07d/fixhk_census.py (tier token within 30 chars of a
number either order, joined line pairs, cap-word context; NOT the check's regex). Output
fixhk_census.out. Live stale (non-FROZEN) sites: docs/tasktool-spec.md:157, :425, :525 (fenced
JSON), docs/gate-runbook.md:451-452 (wrapped), formal/verify.sh:1134 comment,
scripts/task.py::check_pri_budget docstring, scripts/handoff_lint.py:15 (historical narrative).
Correct-value / exempt: docs/README.md:148-149,171 (priority-vocab table = designated home, value 5
correct), tasks/README.md:97 (5, dated), FROZEN trial-protocol/trial-stub/tree-sole-authority-spec,
context-audit (FROZEN), promote-next-triage (ACTIVE-PLAN, dated), verify.sh:647 (dated history).
Not changed, noted: scripts/task.py::CONFIG_DEFAULTS budgets NEXT 3 and budgets.get('NEXT', 3)
fallbacks in check_pri_budget (code defaults for a config without budgets; shipped config has them).
### Issue 1+5 FIXED
- Deleted the number at docs/tasktool-spec.md:157, :425 (now 2 lines), :525 (fenced JSON example ->
  placeholder), docs/gate-runbook.md 4f wrapped line, scripts/task.py::check_pri_budget docstring,
  formal/verify.sh 4f comment, scripts/handoff_lint.py module docstring (WHY THIS EXISTS).
- handoff_lint.py: third pattern 'bound-first' in _CAP_PATTERNS (named groups tier/num);
  _restated_caps(ln, nxt) reports crossing matches from the joined pair (wrapped caps).
- SECOND BLIND SPOT FOUND (first-hand): the walk toggled fence on any line starting with ```;
  docs/tasktool-spec.md:93 is prose ("``` or `~~~` fence is skipped"), which inverted fence state
  so lines 144-522 (incl :157 :343 :425) were NEVER scanned. New handoff_lint.py::_is_fence
  (CommonMark: backtick info string may not contain a backtick).
- Retro control: shipped check on HEAD e8b340b tasktool-spec + gate-runbook reports exactly
  gate-runbook:304, :451 (wrapped), tasktool-spec:157, :343, :425.
- 3 new tests in tests/test_handoff_lint_count_guard.py; sweep M1-M7 7/7 caught (fixhk_sweep.out),
  table in module comment. Live handoff_lint clean (12 checks) after doc fixes.

## Issue 2+7 (formal/HANDOFF.md caps loose) -- CONFIRMED (241 lines / 19636 B LF / widest 639 / boldcaps [52] vs 520/none/6)
FIXED: MAX_LINES formal 520->265, MAX_BYTES formal 21600 (+BYTE_CAP_REMEDY entry), MAX_BOLDCAPS formal 6->1,
check_bold_caps now red when hits < budget (ratchet both ways). Live sabotage in fixhk_capsab.out
(240 lines red, 19635 B red, boldcaps 0 red, boldcaps 6 red 'lower ... to 1').
Tests: tests/test_tk131_claude_md_cap.py::test_formal_handoff_has_a_byte_cap_with_its_own_remedy,
::test_the_bold_caps_budget_is_a_ratchet_in_both_directions.

## Issue 6 (live CLAUDE.md read in a t2c-keyed tile) -- CONFIRMED
FIXED by moving the headroom ratchet to lean: handoff_lint.py::MAX_BYTES_SLACK {'CLAUDE.md': 1900} checked in
check_ceilings; the pytest test rewritten to temp roots (no live read). tk130 _seed_ceiling_root writes CLAUDE.md
at cap. Sweep S1-S6 all red (fixhk_sweep2.out), table in tk131 docstring addendum.
Survey re-done (gate_status.py comment demands it): also found tests/test_tk122_release_metadata.py reads live
PYPI_README.md + CHANGELOG.md, and tests/test_claim_rot_gate.py reads live formal/CORRESPONDENCE.md (via
claim_rot.DOC). Added all three to scripts/gate_status.py::CODE_SCOPE_MD_KEEP with survey note; CLAUDE.md stays out.
Docs pointing at the list updated (CLAUDE.md footgun line, docs/README.md sec 7, gate-runbook :204 and t2c table row).
New tests in tests/test_gate_status.py (pair test + literal survey); sabotage fixhk_sweep3.out (G1 2 failed, G2 1 failed).

## Issue 3 (goal has no live home) -- CONFIRMED (grep decision-log.md 'legible|2026-09-22c' = 0 hits)
FIXED: new section docs/architecture/decision-log.md "## The project goal: honest, legible assurance, not wider
(user decision, 2026-09-22c)" (goal, stop-widening corollary, perf rejected -> TK34, wider fragment rejected),
sourced from tasks/closed/TK94 note 2026-09-22c ("the user chose") + session-log 2026-09-22c + census sec 6.
CLAUDE.md: 2-line pointer at top of "Start here" (CLAUDE.md now 31268 B LF, cap 32500, headroom 1232 < slack 1900).

## Issue 4 (perf routing home lacks the TK34/deprioritized pointer) -- CONFIRMED
FIXED: blockquote near top of docs/perf-next-round.md pointing at `task.py show R6` note 2026-09-22c and the decision-log section.

## Issue 8 (FINAL_REVIEW counts stale) -- CONFIRMED (doc 1749 vs tree 1777 after my tests)
FIXED: doc_counts --generate; --check rc=0 "1087 conf / 1777 tests / 715 audits / 741 anchors -- all match".
Must be re-run if anyone adds/removes a test after this.

## Final checks (2026-10-07d)
- handoff_lint: clean (12 checks)
- task lint: clean (13 checks, 248 task file(s) parsed), 29 warning(s)
- task.py board rc=0, 31 lines
- pytest handoff_lint_* + tasktool + tk130 + tk131 + gate_status + tk122 + refused_shape + claim_rot_gate: 313 passed
- post-comment rerun: tasktool + handoff_lint_*: 195 passed
- Row comments added to TK128, TK131 (not closed).

## Open concerns
- scripts/task.py::CONFIG_DEFAULTS budgets NEXT 3 and check_pri_budget budgets.get('NEXT', 3) fallback: stale default (cap is 5), unreachable with the shipped config. Not changed.
- MAX_LINES/MAX_BYTES formal values held by provenance comments only (no slack ratchet like CLAUDE.md's).
- CODE_SCOPE_MD_KEEP change moves every t2c id: all tile verdicts go stale; full gate needed anyway.
- gate_status survey test sees only literal ROOT / "x.md" reads; indirect reads (claim_rot.DOC) need the pair test / manual survey.
- Scratch files to delete after transcription: fixhk_*.py/.out/.txt, fixhk_retro/ (evidence is in tracked test docstrings/comments).
COMPLETE.
