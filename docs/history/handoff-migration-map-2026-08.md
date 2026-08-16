# Handoff migration map (2026-08-16) — survey + critique data for the redesign

> **FROZEN 2026-08-16 — provenance, not a living document.** This is the
> machine-transcribed evidence base for executing
> [`docs/handoff-redesign-2026-08.md`](../handoff-redesign-2026-08.md) §9
> (generated from workflow runs `wf_ccc3f53c-584` survey / `wf_6d8a9bf1-f58`
> critique; agent transcripts under the 2026-08-16 session's
> `subagents/workflows/` directory). **All HANDOFF.md line numbers reference
> the file AS OF 2026-08-16 (979 lines, pre-migration)** — if HANDOFF.md has
> since changed, resolve against `git log` for that date, never against the
> current file. Sections A–D are the survey verbatim; section E is the three
> critiques verbatim (their surviving findings are already folded into the
> design doc — the value here is the exact grep evidence).

## A. HANDOFF.md block-by-block dispositions (every line accounted for)

### lines 1-18 — Header: what HANDOFF is, contract split, formal/HANDOFF pointer
- **types:** durable-rule, pointer-map
- **disposition:** keep-on-board
- **keep on board:** ~8 lines
- **rationale:** The file's charter and the formal-subtree pointer are exactly what a 200-line HANDOFF opens with, minus a few redundant sentences.

### lines 19-43 — START HERE banner: gate green, no-figures rule, four footguns
- **types:** live-status, footgun-warning, historical-narrative
- **disposition:** keep-on-board
- **keep on board:** ~12 lines
- **rationale:** Live gate status plus the four footguns are needed before touching code, but the embedded ZT-P3-5 recurrence story (lines 28-34) is historical narrative for the archive.

### lines 44-99 — What landed 2026-08-16 (4c-i, three allocation refutations, mirror-instrument finding, (iv) unblocked)
- **types:** historical-narrative, method-lesson, live-status
- **disposition:** archive → `docs/history/handoff-status-2026-08.md`
- **keep on board:** ~3 lines
- **rationale:** Session narrative belongs in the dated history file; its method lesson is already in docs/sabotage-procedure.md (line 68 says so), the n-ary-AST limit is mechanically pinned by a test, and its status facts are duplicated on the phase table.

### lines 100-125 — What landed 2026-08-15 (4c-pre kill, Leaf.lean rework)
- **types:** historical-narrative, method-lesson
- **disposition:** archive → `docs/history/handoff-status-2026-08.md`
- **keep on board:** ~0 lines
- **rationale:** Previous-session narrative whose durable outputs (section 11.6 refuted, revised plan) are already restated in section 5 and the phase table.

### lines 126-136 — 'Earlier sessions archived' pointer + note that one archived 2026-08-14 line is now FALSE
- **types:** pointer-map, correction-to-other-doc
- **disposition:** fix-target-doc-instead → `docs/history/handoff-status-2026-08.md`
- **keep on board:** ~2 lines
- **rationale:** The correction ('(iv) possibly-blocking' is now answered) belongs as an annotation in the archive itself; HANDOFF keeps at most a one-line archive pointer already present in the Where-things-live table.

### lines 137-166 — THE SEQUENTIAL PHASE PLAN table (P1-P13)
- **types:** open-todo, live-status, pointer-map
- **disposition:** keep-on-board
- **keep on board:** ~26 lines
- **rationale:** This table is the natural single status surface the redesign wants: every remaining item, ordered, with dependencies and size; the redesigned board should make each row THE status and delete the prose sections that duplicate rows (P1/P2 done rows can be dropped, not struck through).

### lines 167-187 — 'Still open - what moved 2026-08-16' recap
- **types:** live-status, historical-narrative
- **disposition:** archive → `docs/history/handoff-status-2026-08.md`
- **keep on board:** ~0 lines
- **rationale:** A second, appended statement of statuses already on the phase table (4c-i landed, (iv) answered, item 2 closed) - the status-in-one-place rule says fold it into the table and archive the narrative.

### lines 188-228 — Section 1: RC1/RC2 arc CLOSED - severity-sign rule, mirror-instrument, generator-coverage baseline
- **types:** decision-record, method-lesson, footgun-warning, live-status
- **disposition:** shrink-to-pointer → `docs/sabotage-procedure.md`
- **keep on board:** ~6 lines
- **rationale:** The severity-sign rule and mirror-instrument are method lessons (mirror-instrument is already generalised in sabotage-procedure.md; move the severity-sign rule there too), and the coverage table's figures belong beside docs/design/generator-coverage/; keep a 5-6 line pointer with the honest-limit warning.

### lines 229-246 — Section 2: audit claims CLOSED - three live constraints (no ttuDirect lift, decidable W4Fragment descendant, transcripts path)
- **types:** footgun-warning, open-todo, pointer-map
- **disposition:** shrink-to-pointer → `docs/history/handoff-status-2026-08.md`
- **keep on board:** ~5 lines
- **rationale:** The closure narrative is already archived; keep only the do-NOT-lift-ttuDirect warning and the decidable-W4Fragment open descendant, and let P10's row own the transcripts path (stated three times in this file).

### lines 247-311 — Section 3: ttuStarFree DO-NOT-DROP + four-part leg status + part (i)/(iv) landed detail + occurrence census
- **types:** footgun-warning, resume-context, live-status, decision-record
- **disposition:** shrink-to-pointer → `formal/history/PROOF_STATUS.md`
- **keep on board:** ~12 lines
- **rationale:** The do-not-drop refutation, the (ii)-materializes-the-edge fact, and the W4Fragment-unchanged warning are live constraints a next session needs; the landed-part narratives (2026-08-14 part (i), 2026-08-16 part (iv)) and the 163-occurrence measurement are dated formal-work log content for PROOF_STATUS.

### lines 312-328 — Section 4: scope-audit re-run plan + fan-out failure lessons
- **types:** open-todo, method-lesson
- **disposition:** shrink-to-pointer → `docs/subagent-fanout-runbook.md`
- **keep on board:** ~4 lines
- **rationale:** P10's row already carries the item and the transcripts head start; the two rules that would have saved the fan-out are runbook content (the runbook is 'written from this failure' - verify they are in it and point).

### lines 329-354 — Section 5: leg-7 state + the 4c-ii co-land checklist + landing criterion
- **types:** resume-context, live-status, open-todo
- **disposition:** keep-on-board
- **keep on board:** ~12 lines
- **rationale:** This is the resume context for P3, the critical path - a next session needs the checklist and the co-land constraint before touching Cascade.lean, though the checklist duplicates scope-doc 11.7 and can compress against it.

### lines 355-365 — Section 6: optional severity-sign revert probe
- **types:** open-todo
- **disposition:** shrink-to-pointer
- **keep on board:** ~2 lines
- **rationale:** Fully duplicated by phase-table row P12 including the not-measured caveat; fold into the row.

### lines 366-386 — Status run 2026-08-11 (self-labelled historical): gate green, RC1/RC2 fixed, coverage caveat discharged
- **types:** historical-narrative, live-status
- **disposition:** archive → `docs/history/handoff-status-2026-08.md`
- **keep on board:** ~0 lines
- **rationale:** A second dated status block that the file itself marks historical and defers to the banner - a direct violation of status-in-one-place.

### lines 387-404 — Leg 7 started 2026-08-09 narrative + scope-doc bet/refutation carries
- **types:** historical-narrative, resume-context, correction-to-other-doc
- **disposition:** archive → `docs/history/handoff-status-2026-08.md`
- **keep on board:** ~0 lines
- **rationale:** Landing narrative with a superseded-half warning; its still-live carries are already recorded in leaf-family-split-scope section 11 and PROOF_STATUS 2026-08-09, which the block itself cites.

### lines 405-414 — rewriteClosure dedup leg narrative (2026-08-08)
- **types:** historical-narrative
- **disposition:** archive → `docs/history/handoff-status-2026-08.md`
- **keep on board:** ~0 lines
- **rationale:** Completed-leg narrative whose detail already lives in PROOF_STATUS 2026-08-08b per its own last line.

### lines 415-451 — E-chain legs 5/6 narrative + the leg-5 rebase-sabotage lesson
- **types:** historical-narrative, method-lesson
- **disposition:** archive → `docs/history/handoff-status-2026-08.md`
- **keep on board:** ~0 lines
- **rationale:** Completed-arc narrative (detail in PROOF_STATUS 2026-08-05c/d); the transferable 'a rebase needs a different sabotage than a clone' lesson must land in docs/sabotage-procedure.md before the block is archived.

### lines 452-473 — Legs 2/3/4, P3 blind-spot adjudication, counts-pin landing, figures-in-one-place rule
- **types:** historical-narrative, durable-rule
- **disposition:** archive → `docs/history/handoff-status-2026-08.md`
- **keep on board:** ~0 lines
- **rationale:** All completed-work narrative already recorded in CORRESPONDENCE 7.2, spec-deviations 2026-07-29 and PROOF_STATUS; the one durable rule here (figures live in FINAL_REVIEW only) is already in CLAUDE.md and rhythm rule 3b.

### lines 474-500 — Three stacked 'history moved out' notes (2026-07-29, 2026-08-16, 2026-08-11) + archives-are-frozen warning
- **types:** pointer-map, durable-rule, correction-to-other-doc
- **disposition:** fix-target-doc-instead → `docs/history/handoff-status-2026-08.md`
- **keep on board:** ~3 lines
- **rationale:** The frozen-as-of-then warning belongs as a header inside each archive file (the redesign rule: archives say so themselves); the 'archive the STATUS, keep the METHOD' rule moves once into the HANDOFF header; the pointers are already in the Where-things-live table.

### lines 501-512 — Open-TODO board heading + 2026-08-11 retired-items note
- **types:** pointer-map, historical-narrative
- **disposition:** delete
- **keep on board:** ~2 lines
- **rationale:** The retired-items quote restates what the archive already holds and what section 5 carries forward; keep only the headings.

### lines 513-526 — Board: perf round 6 candidate worklist
- **types:** open-todo, footgun-warning
- **disposition:** keep-on-board
- **keep on board:** ~8 lines
- **rationale:** A genuinely open item with the load-bearing warnings (nothing measured, do not implement from titles, R6-1's refuted fix) - full record already lives in docs/perf-round6-audit-2026-08.md so it can shrink slightly.

### lines 527-547 — Board B1 intro: E-chain end state + the (c) decision + scope-doc pointer
- **types:** decision-record, resume-context, historical-narrative
- **disposition:** shrink-to-pointer → `formal/history/leaf-family-split-scope-2026-08-05.md`
- **keep on board:** ~4 lines
- **rationale:** The decision and blast-radius numbers are recorded in the scope doc it links; the board needs only 'leg 7 in progress, see section 5 / P3 row and the scope doc'.

### lines 548-573 — B1 resume point (updated 2026-08-15) + section-11.3-is-wrong corrections + third copy of the landing criterion
- **types:** resume-context, correction-to-other-doc, live-status
- **disposition:** fix-target-doc-instead → `formal/history/leaf-family-split-scope-2026-08-05.md`
- **keep on board:** ~3 lines
- **rationale:** The 'section 11.3 is WRONG in two places' corrections belong annotated in the scope doc itself; the resume point and criterion are already stated in section 5 and P3's row (this is their third in-file statement).

### lines 574-591 — B1 four older notes: NO-KILL probe, Sd/Td cannot witness, uposEdgeFree immune, step 2b done
- **types:** footgun-warning, decision-record, historical-narrative
- **disposition:** shrink-to-pointer → `formal/history/leaf-family-split-scope-2026-08-05.md`
- **keep on board:** ~2 lines
- **rationale:** All four cite scope-doc sections 9.1-9.3 that already carry them; the P5 row already repeats the Sd/Td warning, the one a next session must not miss.

### lines 592-615 — B1 steps 0/1 completion narrative (generated P6 ledger, non-existent prerequisite)
- **types:** historical-narrative, method-lesson
- **disposition:** archive → `docs/history/handoff-status-2026-08.md`
- **keep on board:** ~0 lines
- **rationale:** Completed-step narrative; its durable output (criterion stated in the form that cannot rot; read baselines from the generated block) is already restated at the criterion sites and in rule 3b.

### lines 616-640 — B1 background: W4NarrowT2a asymmetry, D.3 probe, why (c) was chosen
- **types:** decision-record, resume-context
- **disposition:** shrink-to-pointer → `formal/history/leaf-family-split-scope-2026-08-05.md`
- **keep on board:** ~2 lines
- **rationale:** The block itself says the why-abc reasoning is section 1 of the scope doc and the background is in W4NarrowT2a's docstring - pure duplication of satellite content.

### lines 641-672 — Board B2: REMOVE-gate exclusion leg + self_flag adjudication / W4WitnessSelfRef task
- **types:** open-todo, decision-record, historical-narrative
- **disposition:** shrink-to-pointer → `formal/history/PROOF_STATUS.md`
- **keep on board:** ~6 lines
- **rationale:** P8 and P9 rows already carry both tasks; the self_flag adjudication narrative is dated formal-work-log material (its design is already in PROOF_STATUS 2026-08-08 section 6), leaving two short board entries with the tautological-clone and no-backwards-conversion warnings.

### lines 673-693 — Board (A): store-level write quota DECLINED + full measurement summary
- **types:** decision-record
- **disposition:** shrink-to-pointer → `docs/spec-deviations.md`
- **keep on board:** ~2 lines
- **rationale:** A closed decision whose full measurement is already in spec-deviations 2026-07-29c per its own citation; keep two lines (declined, use sync=False, ZT-P1-6a half-closed by decision).

### lines 694-714 — 'READ BEFORE FOLLOWING ANY CELL of the e-chain plan' corrections digest + verify-lean-first note
- **types:** correction-to-other-doc, method-lesson, durable-rule
- **disposition:** fix-target-doc-instead → `formal/history/echain-widening-plan-2026-07-28.md`
- **keep on board:** ~3 lines
- **rationale:** The corrections C.1-C.6 already live inside the plan doc itself - the plan doc's header should carry the trust warning; keep the one-line pointer and the 'verify.sh lean green in ~60s first' habit.

### lines 715-764 — Board: CORRESPONDENCE claim-rot gate - full design (mechanisms A/B/C, measurements, sabotage plan)
- **types:** open-todo, decision-record, method-lesson
- **disposition:** migrate-to-satellite → `formal/history/claim-rot-gate-design-2026-08-16.md`
- **keep on board:** ~8 lines
- **rationale:** A 50-line designed-not-built proposal is satellite content - a NEW dated design note (or a PROOF_STATUS entry) should hold the mechanisms, measured constraints and sabotage plan, leaving an 8-line P13 board item.

### lines 765-788 — Board: assurance-widening arc follow-ups (three small items)
- **types:** open-todo, historical-narrative
- **disposition:** shrink-to-pointer → `formal/history/optional-widening-2026-07.md`
- **keep on board:** ~3 lines
- **rationale:** Item 2 is an explicit duplicate of B2/P9 ('Tracked in board item (B2) above'), item 3 is closed and exists only to disarm a stale pointer in formal/HANDOFF.md (fix that pointer instead), leaving item 1 as a two-line entry.

### lines 789-815 — Board: five subsumed .fga fixtures - reasoning + triple-question + do-not-extend warning
- **types:** open-todo, decision-record, footgun-warning
- **disposition:** shrink-to-pointer → `tests/test_schema_shapes.py`
- **keep on board:** ~4 lines
- **rationale:** The entry says the KNOWN_SUBSUMED register in the test file is the live artifact and this text 'exists only to record the reasoning' - move the reasoning into that register's docstring; P11's row plus the do-not-extend warning is all the board needs.

### lines 816-830 — Someday heading + OpenFGA corpus item (DONE DIFFERENTLY, archived 2026-08-16)
- **types:** historical-narrative, pointer-map
- **disposition:** delete
- **keep on board:** ~1 lines
- **rationale:** A completed, already-archived item still occupying 13 lines - its own text says the full record is in the 2026-08 archive; keep only the section heading.

### lines 831-847 — Someday: lift the two scope rejections (priority argument corrected 2026-07-29)
- **types:** open-todo, decision-record
- **disposition:** keep-on-board
- **keep on board:** ~5 lines
- **rationale:** A live someday item whose corrected priority reasoning prevents re-deriving the invalidated 'OpenFGA doesn't have it' argument; compresses to about five lines.

### lines 848-850 — Someday: service wrapper + tuple-log compaction
- **types:** open-todo
- **disposition:** keep-on-board
- **keep on board:** ~2 lines
- **rationale:** Two honest one-line someday items.

### lines 851-878 — Someday: bulk-merge write path - 27-line design sketch
- **types:** open-todo, decision-record
- **disposition:** migrate-to-satellite → `docs/architecture/bulk-merge-design.md`
- **keep on board:** ~4 lines
- **rationale:** The item itself instructs 'write it up (match p13-bulk-build-design.md style) before implementing' - a NEW design doc should hold the crux/reuse/gates/phasing detail, leaving a 3-4 line board entry.

### lines 879-886 — Standing/latent heading + retired TupleSource-init note
- **types:** historical-narrative, pointer-map
- **disposition:** delete
- **keep on board:** ~1 lines
- **rationale:** The note is already retired to the 2026-08 archive by its own text; keep only the section heading.

### lines 887-925 — Latent-notes inventory (from-chain target, I7 corner, residue scan, state-level object wildcards)
- **types:** open-todo, live-status, pointer-map
- **disposition:** migrate-to-satellite → `docs/spec-deviations.md`
- **keep on board:** ~5 lines
- **rationale:** The block ends 'Full log: docs/spec-deviations.md' - the per-item residue detail belongs in that latent-gap inventory, with a 5-line board summary naming the two genuinely-live residues (Lean side of Target 3; intersection-rooted / >2-strata hypothesis).

### lines 926-948 — Where things live table
- **types:** pointer-map
- **disposition:** keep-on-board
- **keep on board:** ~18 lines
- **rationale:** The doc map is core HANDOFF content and becomes more load-bearing as blocks shrink to pointers; add rows for the two new satellites.

### lines 949-979 — Working rhythm (5 rules)
- **types:** durable-rule, footgun-warning
- **disposition:** shrink-to-pointer → `CLAUDE.md`
- **keep on board:** ~8 lines
- **rationale:** Rules 2, 3, 3b and 5 restate CLAUDE.md nearly verbatim (gate recipe, honesty norms, no-figures, Lean-model rule) - CLAUDE.md is the durable contract and is read every session, so HANDOFF keeps only rule 4 (keep the board current), rule 1, and the pg-cluster-stopped-but-retained operational note (which should move to docs/gate-runbook.md).

## B. Marker census, duplications, observations

**Marker census (979 lines):** 19 single-star, 10 double-star, 23 warning-sign, ~94 bold ALL-CAPS phrases — one emphasis marker per 6-7 lines.

**Duplications (same fact in multiple places):**

- Leg-7 landing criterion 'dropped by P6 76 -> 0 / compared 189 -> 265': stated at line 148 (P3 row), lines 352-353 (section 5), lines 571-573 (B1 resume point), and in criterion-form again at lines 601-605
- ttuStarFree part (iv) answered NO-BLOCK: lines 86-98 (what landed 2026-08-16), line 147 (P2 row), lines 177-183 (Still open item 3), lines 288-299 (section 3)
- 4c-i landed with zero recompile cone / section 11.6 cost cell refuted: lines 50-61, line 146 (P1 row), lines 170-176 (what moved), lines 329-334 (section 5)
- The 279 subagent transcripts path wf_f8c85180-b74: line 155 (P10 row), lines 244-246 (section 2), lines 318-322 (section 4)
- 4c-ii cannot land alone / must co-land with step 7: line 148 (P3 row), lines 336-337 (section 5), lines 567-570 (B1)
- Sd/Td cannot be leg-7's witness: line 150 (P5 row) and lines 578-581 (B1 older notes)
- REMOVE-gate exclusion needs storeValidRulesDB + widened remove constructor: line 154 (P9 row), lines 643-650 (B2), lines 773-783 (follow-ups item 2, which itself says 'Tracked in board item (B2) above')
- self_flag holds / write W4WitnessSelfRef: line 153 (P8 row) and lines 651-671 (B2)
- Fixture-triple question: line 156 (P11 row) and lines 789-814 (full item)
- Severity-sign revert probe: line 157 (P12 row) and lines 355-362 (section 6)
- CORRESPONDENCE claim-rot item: line 163 (P13 note) and lines 715-763 (full item)
- 'Live figures live in ONE place, never in prose': banner lines 28-34, lines 470-472, rhythm rule 3b lines 970-973, plus CLAUDE.md's 'No figures here, deliberately' bullet - the same rule in four places across two docs
- Gate-green status stated twice: banner lines 21-26 (live) and 'Status run 2026-08-11' lines 366-385 (self-labelled historical duplicate that defers to the banner)
- Generator-coverage honest limit (~24-28% of pair space unreached): lines 224-226 (section 1) and lines 383-384 (status run)
- HYPOTHESIS_SEED-does-nothing footgun: line 40 (banner) and lines 954-957 (working rhythm), also in CLAUDE.md's house-failure list
- Mirror-instrument lesson: lines 67-77 (what landed) and lines 207-211 (section 1), both ALSO in docs/sabotage-procedure.md which both cite as its home
- 'Archive the STATUS, keep the METHOD' rule stated twice within 12 lines: lines 485-488 and line 497
- Pointer to docs/history/handoff-status-2026-08.md restated at least eight times: lines 128-131, 192-194, 232-234, 481-488, 490-497, 505-511, 828-830, 881-885, plus the Where-things-live row at line 944
- Section 11.3 fork decided (alpha): line 331 (section 5), lines 548-551 (B1 resume), and referenced through the 2026-08-15 what-landed block lines 100-124
- Working-rhythm gate recipe (lines 950-963) duplicates CLAUDE.md 'Start here'/'Running things' and docs/gate-runbook.md

**Surveyor observations:**

- The file is 979 lines at survey time, not 966 - it grew again with the 2026-08-16 session edits, i.e. it is still inflating between redesign decision and execution.
- Marker density is about one emphasis marker per 6-7 lines (52 star/warn markers + ~94 bold all-caps phrases in 979 lines), so markers no longer rank anything - the census confirms star inflation.
- The Sequential Phase Plan table (lines 137-166) already IS the single status surface the redesign wants: every numbered section (1-6) and every large board item duplicates one of its rows. The cheapest redesign makes each phase row the sole status statement with one satellite pointer, then deletes the prose twins.
- The dominant growth mechanism is append-only status editing: updates arrive as new layers ('What moved 2026-08-16', 'RESUME POINT (updated 2026-08-15)', 'this line used to carry...', strikethroughs) instead of edits in place, so each status ends up stated 3-4 times at different dates.
- Corrections to other docs are carried in HANDOFF instead of the target doc: scope-doc 11.3/11.6 corrections (lines 559-566, 333-334), the e-chain plan trust warning (694-712, whose C.1-C.6 corrections already live in the plan doc), the generator-coverage design-doc caveat (lines 227-228 'trust the archive's three implementation corrections over that design doc'), and the archived-line-now-FALSE note (134-136). Each violates the corrections-belong-in-target rule and several duplicate corrections the target already contains.
- Two NEW satellites are warranted: (1) formal/history/claim-rot-gate-design-2026-08-16.md for the designed-not-built gate mechanisms at lines 715-763; (2) docs/architecture/bulk-merge-design.md for the design sketch at lines 851-877, which itself instructs that a design doc be written before implementing.
- Archive-freshness warnings ('status lines inside an archive are frozen as-of-then, and several in that one are now wrong', lines 494-496) should become a standard frozen-status header INSIDE each docs/history file, satisfying the 'archives are frozen and say so' rule and removing the warnings from HANDOFF.
- Completed items are not actually removed when archived: the OpenFGA-corpus item (816-830), the TupleSource-init note (881-885), the retired-items quote (505-511), item 2 (229-246) and the 2026-08-11 status run (366-497) all remain in full or summary despite pointing at their own archive copies - roughly 250 lines of the file is post-archival residue.
- formal/HANDOFF.md already exists as the compact formal-subtree entry point; the deep leg-7/ttuStarFree resume state (sections 3 and 5, blocks B1/B2) could live under formal/ satellites with the root HANDOFF holding only phase rows plus the footgun lines.
- Genuinely live warnings that MUST survive on the ~200-line board: the four banner footguns; do-not-drop ttuStarFree / W4Fragment.ttuStarFree unchanged until (ii); do-not-lift ttuDirect; Sd/Td cannot witness P5; 4c-ii+7 co-land; the d.leaf leading-conjunct binding condition; do-not-implement-perf-from-titles; do-not-extend test_fixture_earns_its_place; the landing criterion re-derive-from-generated-block rule.
- Sum of proposed approx_keep_lines is about 186, comfortably inside the ~200-line target while keeping every live footgun and all resume context for the P3 critical path.
- The claude_ai Claude_Code_Remote MCP server reports it needs authorization (via claude.ai connector settings or /mcp in an interactive session) before its tools can be used; it was not needed for this read-only survey.

## C. Docs-tree inventory

| path | lines | liveness | purpose |
|---|---|---|---|
| `docs/gate-runbook.md` | 530 | runbook | Cap-safe recipe for running the phased verify.sh gate (tests tiles, conformance tiles, Lean, fuzz sweep, PostgreSQL leg) plus the floors/pins it enforces |
| `docs/perf-next-round.md` | 119 | living | The living perf home: standing guardrails (P12c fence, confirmed dead-ends, measurement hygiene) plus the pointer to the current active worklist (round-6 audit) |
| `docs/perf-round6-audit-2026-08.md` | 770 | active-plan | Round-6 CANDIDATE worklist: 18 verified + 16 unverified perf findings from the 2026-08-15 24-agent audit, verbatim, with binding rules and an editorial digest |
| `docs/sabotage-procedure.md` | 272 | runbook | The standard procedure for validating any new assurance step (sabotage it red first), plus the growing catalogue of checks that failed by passing |
| `docs/spec-deviations.md` | 3164 | living | Dated newest-first append log of implementation-vs-spec divergences, P0 recon findings, divergence/incident write-ups, measurements, and user adjudications |
| `docs/subagent-fanout-runbook.md` | 204 | runbook | How to scope a multi-agent fan-out and persist its results, written from the 2026-08-10 fan-out that lost its own output; updated with the 2026-08-14 success case |
| `docs/architecture/overview.md` | 160 | living | Architecture index: memoization-spectrum framing, live-code module map, and the pointer table into every deeper architecture doc, formal/, and the specs |
| `docs/architecture/correctness.md` | 161 | living | The correctness argument: what is by-construction vs empirically pinned vs unprotected, and the redundancy structure |
| `docs/architecture/decision-log.md` | 202 | living | Load-bearing design decisions with rejected alternatives, compressed from the three specs; 'why it is like this at all' |
| `docs/architecture/derived-predicates.md` | 116 | living | Operational summary of boolean operators in the graph index: taint, plan trees, leaf routing, the delta processor, residues |
| `docs/architecture/graph-index.md` | 77 | living | Operational summary of the closure core and wildcard facade (path counts, cycle rejection, outbox emission, concurrency) |
| `docs/architecture/p13-bulk-build-design.md` | 160 | spec | Design record for the P13/N18 bulk closure builder (state-identity correctness bar, phase plan), code-verified as of 2026-07-15 |
| `docs/architecture/r4bf-bulk-backfill-design.md` | 218 | spec | Design record for the R4-BF in-memory boolean Phase-D backfill used by the bulk builder, code-verified as of 2026-07-15 |
| `docs/architecture/system.md` | 134 | living | The composed connected-store system view: source-of-truth tuple store + log, the apply step, sync/async schedules, freshness tokens |
| `docs/architecture/theory.md` | 218 | living | The math: path-counting closure, split wildcard nodes, stratified fixpoints, residues, star-closed set algebra |
| `docs/architecture/verification.md` | 134 | living | The verification machinery: oracle contract, validation matrix, ParityEngine, paranoia/invariants, hypothesis campaign |
| `docs/design/generator-coverage/README.md` | 607 | frozen-archive | The 2026-08-10 generator-coverage design: 51-feature cell taxonomy, swarm testing, un-hardcoded TTU tupleset, ci/deep split, measured prototype numbers |
| `docs/design/generator-coverage/bulk-backfill-duplication.md` | 144 | frozen-archive | 2026-08-10 measurement log confirming (and partially refuting) the RC1/RC2 code-duplication claim between processor.py and bulk_backfill.py |
| `docs/design/generator-coverage/divergence-sweep-report.md` | 460 | frozen-archive | 2026-08-10 bounded exhaustive divergence sweep report (443 schemas, 2.3M queries): the sweep design, caps, and the two-root-cause result |
| `docs/design/generator-coverage/ttu-negarm-rootcause.md` | 565 | frozen-archive | 2026-08-10 root-cause analysis of the TTU-over-derived-tupleset divergence (RC1: _member_types drops the subtract arm), with the verified one-line fix |
| `docs/history/handoff-status-2026-07.md` | 1261 | frozen-archive | Retired HANDOFF status run + completed-work board through 2026-07, incl. the full zero-trust review and the reconciled ZT-* disposition ledger |
| `docs/history/handoff-status-2026-08.md` | 800 | frozen-archive | Retired RC1/RC2 TTU-tupleset arc (filing, fix list, generator-coverage leg) + 2026-08-08/09 completed board items, kept for method not status |
| `docs/history/perf-round3-2026-07.md` | 569 | frozen-archive | Verbatim retired round-3 perf worklist/execution record (P12 decomposition, N4-N14 survey, wave plan) |
| `docs/history/perf-round4-2026-07.md` | 281 | frozen-archive | Verbatim retired round-4 execution record (bulk build/apply throughput, M2 scale-bench verdict, git hash audit trail) |
| `docs/history/perf-round5-2026-07.md` | 99 | frozen-archive | Round-5 assessment record: worklist declared exhausted, N13/N14 declined on a fresh profile, both write-ups retired verbatim |
| `docs/specs/connected-store-spec.md` | 128 | spec | Spec round 2: the connected store — source-of-truth tuples + materialized graph index, settled decisions, schedules, tokens |
| `docs/specs/graph-boolean-ivm-spec.md` | 259 | spec | Spec v1.1: boolean operators in the graph index via stratified IVM — frozen semantics list, adaptation charter, phase plan; the origin of the spec-deviations convention |
| `docs/specs/set-engine-spec.md` | 226 | spec | Spec: the set-based evaluation engine (bitmap-backed, SetOps seam, MemberSet algebra, validity parity, validation matrix) |
| `docs/specs/wildcard-materialization-spec.md` | 324 | spec | Spec: materialized wildcard support (split w_any/w_all nodes, bridges, ≤4-probe check) — the first spec of the series |
| `benchmarks/results/BASELINE_2026-07-13.md` | 236 | frozen-archive | The canonical pre-perf machine-specific baseline: write/check/lookup/reverse across three schema tiers, 10^3-10^5 tuples, with reproduce commands |
| `benchmarks/results/M2_FOLLOWUP_2026-07-15.md` | 231 | frozen-archive | Scale-bench narrative for the M2 verdict: demorgans graph curves + 200k anchors after R4-BF, with session-conditions caveats |
| `benchmarks/results/N18_FOLLOWUP_2026-07-16.md` | 65 | frozen-archive | Re-measure of the gdrive 200k RSS anchor after N18 Phase-W/R streaming landed |
| `benchmarks/results/PERF_ANALYSIS.md` | 599 | living | Fitted scaling laws + PySets-vs-Roaring analysis (2026-07-14) PLUS the living 'Applied' append section holding every landed perf item's measured before/after |
| `benchmarks/results/ROUND3_COMPARISON_2026-07-15.md` | 279 | frozen-archive | Post-round-3 re-run vs the baseline, with the session-slowdown control methodology (read every surface relative to check) |
| `benchmarks/results/ROUND4_COMPARISON_2026-07-16.md` | 183 | frozen-archive | Post-round-4 comparison: stmt_bench + bulk_scale_bench, cross-session comparability rules |
| `benchmarks/results/SCALING.md` | 23 | frozen-archive | Superseded-pointer stub: redirects to BASELINE_2026-07-13.md and restates the two conclusions that survived |
| `benchmarks/results/STMT_BASELINE_2026-07-14.md` | 252 | living | Statements-per-operation baseline over a real ConnectedStore, plus dated addenda appended as N15/N16/micros landed |

**Per-file issues (only files with issues):**

- `docs/gate-runbook.md`: Carries many dated in-line measurements (2026-07-14/15/23/26/27 timings, tile counts) that are explicitly caveated as re-measure-never-quote, but the doc itself has no single as-of marker; interpreter section corrects the avery path CLAUDE.md still names
- `docs/perf-next-round.md`: Deliberately mixes durable guidance with round-status lines that must be re-edited each round (header parenthetical 'round-6 CANDIDATE worklist open'); uses strike-through for resolved items rather than removal
- `docs/perf-round6-audit-2026-08.md`: Correctly self-declares its retirement path ('retire verbatim to docs/history/perf-round6-2026-08.md when the round closes'); lives at docs/ top level as an active plan — consistent with the round-3-5 pattern but means top-level docs/ holds transient files
- `docs/sabotage-procedure.md`: Doubles as a living incident catalogue (the table and the mirror-instrument sections receive new dated entries, latest 2026-08-16) — procedure and case-log are one file and the log grows without an archive path
- `docs/spec-deviations.md`: Title still scopes it to graph-boolean-ivm-spec.md but it is the all-specs implementation record AND the de-facto incident/adjudication log; 3164 lines with no retirement/archival convention of its own (unlike HANDOFF, it never sheds closed entries)
- `docs/architecture/overview.md`: Its formal-layer row carries live scope-status prose ('since 2026-08-05 includes Direct-arm... except T2a, still vacuous') — dated claim in an index row that must be re-edited whenever the formal fragment moves
- `docs/architecture/decision-log.md`: Scoped to spec-derived design decisions only — operational/user adjudications (declined DoS quota, paranoia default) live in spec-deviations.md instead, splitting the decision record across two files
- `docs/architecture/p13-bulk-build-design.md`: A design doc for a long-landed feature with 'as of 2026-07-15' claims but no frozen/landed warning header; sits beside the living architecture summaries rather than in history/
- `docs/architecture/r4bf-bulk-backfill-design.md`: Same as p13 doc: landed-feature design record, dated internal references, no frozen-as-of header, lives under architecture/ not history/
- `docs/design/generator-coverage/README.md`: Header still reads 'Status: design + validated prototype. Nothing in the repo was modified' — the leg LANDED 2026-08-11 (per HANDOFF and the 2026-08 archive §1b) and the doc was never marked landed/frozen nor moved; prototype file map points at C:\Users\user\AppData\Local\Temp scratch files; one inline FIXED-2026-08-10 erratum exists but the top status was not updated
- `docs/design/generator-coverage/bulk-backfill-duplication.md`: No frozen-as-of warning header; cites pre-fix line numbers (the 2026-08 archive explicitly warns those inverted meaning post-fix); scratch script lives in Temp
- `docs/design/generator-coverage/divergence-sweep-report.md`: 'Status: COMPLETE' but no frozen-as-of-then warning; raw findings JSONL and the sweep script are in Temp (ephemeral) so the report's evidence is unreproducible from the repo
- `docs/design/generator-coverage/ttu-negarm-rootcause.md`: Says it 'corrects the diagnosis currently recorded in docs/spec-deviations.md (top entry)' — a positional pointer that now resolves to the wrong entry (2026-08-14 is top); the recommended fix has since landed; no frozen header saying so
- `docs/history/handoff-status-2026-07.md`: Model archive: provenance warning header, corrections-applied-on-archiving section, link-base note. The ZT-* disposition ledger buried here is arguably reference material, not just provenance
- `docs/history/handoff-status-2026-08.md`: Good warning header (status lines frozen, resolve by file::function never by line) — but it is the only home of reusable method lessons (severity-sign rule, three-independent-instruments), which a frozen archive is a poor place for
- `docs/history/perf-round3-2026-07.md`: Warning header is an HTML comment (invisible in rendered view, unlike the handoff archives' prose banners); body's own STATUS block still says 'All work uncommitted pending review' — frozen contradiction only the comment corrects
- `docs/history/perf-round4-2026-07.md`: Warning header is an HTML comment only
- `docs/history/perf-round5-2026-07.md`: Warning header is an HTML comment only; reproduce block carries the nonexistent avery interpreter path
- `docs/specs/graph-boolean-ivm-spec.md`: Addressed to 'an autonomous coding agent' with a build workflow (§0) that is long executed — spec content and one-shot build instructions are interleaved
- `docs/specs/set-engine-spec.md`: Same agent-addressed build-workflow framing; 'put this in the README' style instructions already executed
- `docs/specs/wildcard-materialization-spec.md`: Same one-shot build framing (run pytest first, one xfail expected — long obsolete facts embedded)
- `benchmarks/results/BASELINE_2026-07-13.md`: Reproduce block hardcodes the nonexistent C:/Users/avery interpreter path; no frozen banner (the dated filename is the only marker)
- `benchmarks/results/PERF_ANALYSIS.md`: Mixed liveness in one file: a frozen dated curve analysis, a living Applied log (the designated home for new numbers), and a now-stale 'Optimization targets (ranked)' section from before rounds 3-5 closed; avery path in the regenerate block
- `benchmarks/results/STMT_BASELINE_2026-07-14.md`: A dated-named 'baseline' file that is actually a living append target (perf-next-round.md directs new statement-count results here; three addenda exist) — name says frozen, role says living; avery path in reproduce block

**Structural misfits:**

- docs/design/generator-coverage/ is a frozen 2026-08-10 investigation bundle living under design/, not history/: the README's 'Status: design + validated prototype. Nothing in the repo was modified' header is now false as a live claim (the leg landed 2026-08-11 per HANDOFF and the 2026-08 archive), and none of the four files carries the 'provenance, not a living document' banner the history/ archives use
- All four generator-coverage docs cite evidence and prototype scripts in C:\Users\user\AppData\Local\Temp (zz_*.py, findings JSONL) — the archived record's supporting artifacts are ephemeral and already gone
- docs/design/generator-coverage/ttu-negarm-rootcause.md points at 'the top entry' of docs/spec-deviations.md — a positional pointer into a newest-first append log, which now resolves to the wrong entry (2026-08-14 is top); archives that reference the living log need dated-entry anchors, not positions
- docs/spec-deviations.md has scope-drifted: titled as the deviations log for graph-boolean-ivm-spec.md, it is actually the all-specs implementation record plus the de-facto incident/adjudication/measurement log (3164 lines) with no retirement convention — the only major living log that never sheds closed content to history/
- Duplicated status surface: perf-round status is restated in three places that must be co-edited (perf-next-round.md's header + round list, perf-round6-audit's status banner, and HANDOFF's board/'Where things live' row) — the round-5→6 transition required touching all three
- Mixed-liveness files in benchmarks/results/: PERF_ANALYSIS.md is one-third frozen 2026-07-14 analysis, one-third living 'Applied' append log, one-third stale pre-round-3 ranked-targets list; STMT_BASELINE_2026-07-14.md is a dated 'baseline' that is really a living addenda target
- Two incompatible frozen-warning conventions in docs/history/: perf-round3/4/5 use an invisible HTML comment (and round 3's visible body still says 'All work uncommitted pending review'), while the handoff-status archives use loud prose banners with corrections sections — a reader of the rendered perf files sees stale STATUS blocks first
- docs/architecture/p13-bulk-build-design.md and r4bf-bulk-backfill-design.md are landed-feature design records with 'as of 2026-07-15' code claims sitting unmarked beside the maintained architecture summaries — neither frozen-bannered nor retired to history/
- HANDOFF.md still carries a 135-line 'Status run — 2026-08-11 (historical...)' section inline — content the docs/history/handoff-status-* convention exists to absorb, marked historical but never moved
- Live status language inside content satellites: docs/architecture/overview.md's formal-layer row carries dated scope-status prose ('since 2026-08-05... T2a still vacuous') that rots when the fragment moves; docs/sabotage-procedure.md's catalogue table accumulates dated live entries inside what is nominally a procedure
- Stale interpreter path (C:/Users/avery/...) embedded in reproduce blocks of BASELINE_2026-07-13.md, PERF_ANALYSIS.md and perf-round5-2026-07.md — commands presented as runnable that fail on this machine (CLAUDE.md documents the correction but the docs were not annotated)

**Conventions to reuse (already in use):**

- Dated newest-first append entries titled '## YYYY-MM-DD — <what happened>' (docs/spec-deviations.md, 40+ entries) — the house pattern for implementation/incident records
- Retire-verbatim-to-history with a self-declared destination: an active doc names its own archive path up front ('When this round closes, retire this file verbatim to docs/history/perf-round6-2026-08.md') — perf-round6-audit-2026-08.md, following rounds 3-5
- The frozen-archive warning banner: 'Provenance, not a living document', every count frozen at its own date, plus a link-resolution note ('links were written relative to repo root; resolve against ../../') — handoff-status-2026-07.md/-2026-08.md headers
- 'Corrections applied on archiving': actively-false bullets in retired text are kept verbatim with the correction recorded beside them rather than silently edited (handoff-status-2026-07.md), including the 'resolve by file::function, never by line' caveat (2026-08 archive)
- Inline dated errata inside frozen or living text: '✅ FIXED 2026-08-10 in d0dbefa; the figures below are the PRE-FIX diagnosis, kept because they are the evidence' (generator-coverage README), '⚠ SUPERSEDED 2026-08-15' annotations (HANDOFF), ~~strike-through~~ resolved items (perf-next-round.md), '★ No figures here, deliberately (2026-08-14)' (CLAUDE.md)
- Live figures live in exactly ONE machine-checked place: formal/FINAL_REVIEW.md's generated counts block, gated by verify.sh step 4e, regenerated by python -m formal.conformance.doc_counts --generate; prose restates pointers, never numbers (HANDOFF rule 3b / ZT-P3-5)
- Superseded-pointer stub: the old file is reduced to a redirect naming its successor plus the conclusions that survived (benchmarks/results/SCALING.md)
- Living-doc-holds-the-pointer: the durable perf home (perf-next-round.md) contains only guardrails plus a link to whatever worklist is currently active, so the active plan can move/retire without rewriting guidance
- Provenance blocks on machine-produced content: workflow run id + per-agent transcript paths + explicit 'verbatim vs editorial' demarcation (perf-round6-audit-2026-08.md); measurement docs open with machine/session-conditions caveats and a control surface ('read every number relative to the check control') — ROUND3/ROUND4/M2 results
- Doc-map tables as the navigation spine: HANDOFF 'Where things live' and overview.md's per-doc table — one-line charter per file, so a redesign can re-home content by editing two tables
- Consolidated disposition ledgers for finding-id families (the ZT-* table in handoff-status-2026-07.md) — reconciled once, against code, with per-id residual notes

**Content types with no satellite home (pre-redesign):**

- Session logs / 'What landed <date>' narratives: they accumulate as HANDOFF banner + dated sections for weeks until a bulk archive event creates a monthly handoff-status-YYYY-MM.md — there is no standing per-session log satellite, so HANDOFF is the default write target for every session's story
- Cross-cutting method lessons: check-shaped ones go to sabotage-procedure.md and fan-out-shaped ones to subagent-fanout-runbook.md, but general lessons (the severity-sign rule, three-independent-instruments structure, IIA masking, the pipe-exit-code footgun, model-policy notes) live only in HANDOFF banners, CLAUDE.md bullets, or frozen archives — commit 1634cd1 'record the two method lessons' had nowhere satellite-shaped to put them
- Investigation / root-cause reports: docs/design/generator-coverage/ was invented ad hoc for one incident; other investigations land as oversized spec-deviations.md entries or HANDOFF sections — no standing 'investigations/' home with a frozen-on-write convention, and their evidence scripts die in Temp
- Operational/user adjudication records (declined DoS quota, paranoia default OFF vs filed ON, isolation-level ruling): scattered across spec-deviations.md entries and archives; decision-log.md is scoped to spec-compressed design decisions only, so post-spec decisions have no ledger
- A live finding-disposition ledger: the ZT-* ledger was reconciled once into the frozen 2026-07 archive; new finding families (R6-*, RC*) have no standing tracked-disposition home outside HANDOFF's board
- Environment/machine facts (the avery-vs-user interpreter path, memory-pressure norms, PostgreSQL cluster state): corrected via CLAUDE.md notes, user MEMORY.md, gate-runbook asides, and a HANDOFF bullet about the stopped cluster — no single machine-state satellite, so live machine state ('cluster STOPPED but RETAINED') sits in HANDOFF
- Doc-tree meta-conventions themselves: the retire-verbatim pattern, banner formats, and 'no figures in prose' rule are encoded only by example and by scattered HANDOFF/CLAUDE.md rules — a redesign has no docs/README.md or style charter to amend

## D. Formal-side inventory

**formal/HANDOFF.md (1005 lines) structure:** L1-15 header + routing table (doc | what it's for | when to read; 8 satellite docs incl. 'never (history)' for REVIEW.md) — NOTE: line 3 claims 'top to bottom (~250 lines)' while the file is 1005 lines. | L17-20 end goal (4 lines, the honest-claim clause). | L22-63 the vacuity caveat block: 'HALF RETIRED — carry the correct half' (T2b widened 2026-08-05, T2a still vacuous) + the option-(c) leaf-family-split decision with pointer to history/leaf-family-split-scope-2026-08-05.md (~42 lines). | L65-231 reverse-chronological dated status blocks, newest first, each prepended by its session: 2026-08-16 (L65-106), 2026-08-15 (L108-134, carries '⚠ SUPERSEDED by the 2026-08-16 block above' inline), 2026-08-14 (L136-171, 'SUPERSEDED TWICE' marker), 2026-08-10 kill (L173-188), 2026-08-09 (L190-213), 2026-08-08 (L215-230); every block ends 'Detail: history/PROOF_STATUS.md <date>' (~167 lines). | L234-303 House rules, 7 numbered, 'non-negotiable, user-adjudicated' (~70 lines; rule 3 carries the '★ No counts here, deliberately' convention). | L305-331 Build & verify: commands, the phased-gate/10-min-cap warning, corrected interpreter path, Lean/Mathlib gotchas (~27 lines). | L333-775 'State of the world (2026-07-12m — the arc is COMPLETE)': a ~443-line blockquoted accretion of dated updates 2026-07-19f..2026-08-05 legs 1-6, an explicitly '[superseded 2026-07-28 — kept for provenance]' NEXT TASK block (L608), 2026-07-18/17 updates, then the ~40-row theorem-scope table (L710-750) and W3c closure notes (L752-775). | L777-853 Board: two orphaned findings B1/B2 adjudicated 2026-07-27, written as paste-ready blocks for the root board (~77 lines). | L855-1001 'Status — the arc is COMPLETE; what remains is optional': ranked optional-widening list + repo-side items, largely frozen at 2026-07-13..26 vintage (~147 lines). | L1003-1005 footer pointer to history/PROOF_STATUS.md, ROADMAP.md, ARCHITECTURE.md.

**Conventions worth copying:**

- The routing table at line 6-15: one screen mapping each satellite doc to 'what it's for' + 'when to read' (including 'the TOP entry only' for the ledger and 'never (history)' for frozen docs) — a fresh session knows exactly what NOT to read.
- Handoff carries the compressed conclusion, the ledger carries the narrative: every dated block in the top zone ends with 'Read/Detail: history/PROOF_STATUS.md <date>' and 'scope-doc §N', so evidence and step-by-step story are one pointer away instead of inlined (in the post-2026-08 blocks; the old L333-775 zone predates this discipline).
- Explicit supersession instead of silent staleness: newer sessions retro-edit OLDER handoff blocks with '⚠ SUPERSEDED by the <date> block above' / '~~...~~ CLOSED <date>' strikethroughs, and commits are dedicated to it (f7fed72 'de-rot the leg-7 status lines', 1634cd1 'de-rot the START HERE banner') — de-rot is a named, attributable act.
- A tiny emphasis vocabulary with meanings: ★★ = headline/must-read-first, ★ = notable landed finding or plan correction, ⚠ = live caveat/trap the next session must carry — used in headings AND inline (though see problems: it is inflated).
- '★ No figures here, deliberately' (house rule 3 and CLAUDE.md's twin bullet): volatile counts are banned from durable prose and live only in FINAL_REVIEW.md's machine-generated counts block gated by verify.sh step 4e — with the rationale written in place (an unenforced prose count is not just stale, it rots).
- 'Still owed' closers: each session block/ledger entry ends with an explicit open-items delta ('Still owed: leg 7 4c-ii + 7 (co-land), 4b, 5, 6; ttuStarFree (ii)/(iii)/(iv)'), so the TODO board is re-derived every session rather than trusted.
- Durable step-plans live in dated scope docs (history/leaf-family-split-scope-2026-08-05.md, echain-widening-plan-2026-07-28.md), and corrections are APPENDED as new sections (§11.5/§11.6/§11.7, §C.2-C.4) with the wrong original left as written and named wrong — plans are provenance, not mutable state.
- Hard separation of durable vs mutable content: House rules + Build & verify sit between the mutable status zone and the historical zone, clearly marked 'non-negotiable, user-adjudicated'.
- Session-day letter suffixes (2026-08-05, b, c, d, e) so a date(+letter) is a stable citation key from anywhere in the repo.

**Problems (shared diseases):**

- The compactness claim itself rotted: line 3 says 'top to bottom (~250 lines)' — the file is 1005 lines, 4x that, and nothing gates it (the exact ZT-P3-5 disease the file lectures about for counts).
- Accretion instead of replacement: the L333-775 'State of the world' zone (~443 lines) is blockquoted historical updates duplicating PROOF_STATUS entries nearly verbatim (leg 2/3/4 blocks at L512-596 mirror ledger entries at PROOF_STATUS L1310/1215/1090), plus a NEXT-TASK block kept inline '[superseded 2026-07-28 — kept for provenance]' — provenance the ledger already holds.
- Triple-duplicated status with skew: the same facts exist at three ages — top blocks (current), 'State of the world' (headline still says '2026-07-12m — the arc is COMPLETE'), and the L855+ 'Status' section, which still quotes '330 conformance tests (measured 2026-07-26)', calls the vacuity 'the highest-value open widening' (closed for T2b 2026-08-05), and marks item 1 'IN PROGRESS 2026-07-18'.
- Emphasis inflation, same as root: ~40 ★/★★ marks and hundreds of BOLD-CAPS phrases; when every block is ★★ the glyphs stop ranking anything.
- The ~40-row theorem table (L710-750, some rows 300-800 chars) duplicates ARCHITECTURE.md's declared role ('theorem table + scopes' per the file's own routing table).
- Supersession marking is applied inconsistently: the post-2026-08 blocks get ⚠ SUPERSEDED edits, but everything below L333 is stale-by-default with only the section date as a hint — a reader who greps into the bottom half gets July state presented in the present tense.

**PROOF_STATUS.md convention:** formal/history/PROOF_STATUS.md is 7,314 lines: a dated APPEND-ONLY session ledger, NEWEST FIRST. Header (L1-9) states the contract explicitly: fresh sessions read formal/HANDOFF.md first; this file backs it; 'read only the TOP entry for resume-point detail, deeper entries on demand'; before ending any session, add an entry at the TOP here AND refresh HANDOFF's next-task. Entry format: '## Session YYYY-MM-DD[letter] (**bold headline stating what landed/was refuted, with before→after numbers**)' — the letter suffix disambiguates same-day sessions (2026-08-05..e), and the headline-in-heading makes 'grep for the date' sufficient; then a '**Task taken:**' line, numbered ### subsections (measurements / what landed / method findings), and a closing 'Numbers and what is still owed' block. Entries run ~40-150 lines; ~100 entries cover 2026-07-09→2026-08-16. Cross-referencing works by date+letter as the stable key: HANDOFF blocks say 'Read history/PROOF_STATUS.md 2026-08-16 and scope-doc §11.7 FIRST', CORRESPONDENCE/ROADMAP cite 'PROOF_STATUS 2026-07-20e' — no line numbers, so appends never break references. The convention IS working: entries are never retro-edited, so contradictions between entries are expected and are resolved forward — a newer entry names what it refutes ('§11.6's cost cell is REFUTED', 'the 2026-08-14 single-target model was wrong in ARITY as well as index'), while supersession MARKING happens in HANDOFF, not the ledger — a clean split (mutable board de-rots; immutable log accretes). Visible rot: the file's BOTTOM (L7037-7314) is the pre-ledger fossil it grew on top of — 'Current phase & resume point' frozen at 2026-07-10 ('Resume → W1b', 'Toolchain is not yet installed'), a 'Phase ledger' saying Phase 6 'not started', a 'sorry ledger', a stale axiom-audit snapshot listing [sorryAx], 'Key facts' contradicting everything above — none marked FROZEN/superseded, so a grep for 'resume point' or 'Phase ledger' lands on 5-week-old state presented as current. That is the one place the append-only discipline leaks: append-only protects entries, but these bottom sections were mutable state that simply stopped being maintained.

**Session-start footprint:** HANDOFF.md 979 lines, CLAUDE.md 227, formal/HANDOFF.md 1005; the surveyor's token estimate was revised upward — dense identifier-heavy markdown here measures ~80 tokens/line, so the real all-three cost is plausibly 100-150k tokens.

**Surveyor recommendations:**

- Copy the routing-table + top-entry-only discipline to the root: make root HANDOFF.md a short board whose every dated block ends with a pointer into a dated append-only log entry (a root-level analogue of formal/history/PROOF_STATUS.md), and open with a one-screen table mapping each satellite doc to 'what it's for / when to read' — including which docs to never read.
- If the redesigned root handoff claims a target length (formal's '~250 lines' is now 4x wrong at 1005), gate it mechanically per the house sabotage rule — e.g. a line-count ceiling checked by verify.sh or the doc_counts generator — or don't state a number at all; an unenforced figure in prose is the project's own documented rot mode (ZT-P3-5).
- Apply the same surgery to formal/HANDOFF.md that the root is getting: move L333-775 ('State of the world' accretion + the 40-row theorem table) out — the table to ARCHITECTURE.md (its declared home per the routing table), the narrative to PROOF_STATUS (where it already exists nearly verbatim) — and rewrite L855-1001 'Status' from the current top blocks; that alone returns the file to roughly its advertised ~250 lines.
- Adopt formal's supersession discipline repo-wide but apply it uniformly: old status blocks get '⚠ SUPERSEDED by the <date> block above' or '~~...~~ CLOSED <date>' the same session that supersedes them (the dedicated de-rot commits f7fed72/1634cd1 are the model); never retro-edit the ledger itself — corrections go in the new entry that names what it refutes.
- Add a 'FROZEN 2026-07-10 — pre-ledger historical state, superseded by every entry above' banner over PROOF_STATUS.md L7037-7314 ('Current phase & resume point', 'Phase ledger', 'Theorem ledger', 'sorry ledger', 'Key facts') — today they present July state as current to anyone who greps for 'resume point'; alternatively move them to history/REVIEW.md-style frozen storage.
- Budget the emphasis glyphs: define ★★/★/⚠ once at the top of each handoff with a rough cap (e.g. ★★ only on the single must-read-first block); both handoffs currently carry so many that the marks no longer rank.
- Keep the 'no volatile figures in durable prose' rule in the root redesign — counts quoted only from FINAL_REVIEW.md's generated block — and end every root board item with formal's 'Still owed:' closer so the TODO delta is restated, not trusted.
- Treat the ~10 tokens/line estimate as a floor, not a measurement: this repo's markdown is identifier-dense (backticked Lean/Python names tokenize at ~1 token per 1.5-2 chars), and the read tooling measured formal/HANDOFF.md's first 516 lines alone at ~41k tokens (~80/line). Real session-start cost for CLAUDE.md + both handoffs is plausibly 100-150k tokens, not 22k — which is itself the strongest argument for shrinking both handoffs to pointer boards.

## E. The three critiques, verbatim (grep evidence for the migration)

The design doc's §10 records which findings changed the design; this section
preserves the full evidence — most valuably the migration critic's exact
file:line inbound-reference lists and the step-4e (`doc_counts.py`) coverage
facts, which migration steps 8 and 9 consume directly.

### Cold-start (Sonnet simulation) critic

**[blocker]** (a) Orientation: the §3 charter ('all live status lives HERE and nowhere else') contradicts §7 keeping formal/HANDOFF.md as a live status doc, and the skeleton drops the current pointer telling formal-bound sessions to read it — so a cold 'continue leg 7' session either never discovers formal/HANDOFF.md or finds two boards and cannot tell which owns leg-7 status.

> Evidence: Design §3 charter line vs §7 ('formal/HANDOFF.md gets the same surgery' — surgery, not retirement; it keeps its routing table and a next-task role). Today's HANDOFF.md lines 13-15 carry the explicit 'read formal/HANDOFF.md before touching anything under formal/' rule; no §3 section reproduces it (the routing table MIGHT, but its content is unspecified). formal/HANDOFF.md's top blocks carry live traps a leg-7 session needs (the T2a half-retired caveat, 'Sd/Td cannot be the witness') that the root board row will not.

> Suggested change: Define ownership explicitly in §3 and docs/README.md: the root board is the priority index of ALL open items (formal included); formal/HANDOFF.md owns formal execution detail and carries no priorities. Require every formal item's read-first list to name formal/HANDOFF.md, and soften the charter to 'all priority/ranking lives here; formal execution state lives in formal/HANDOFF.md (pointer)'.

**[blocker]** (b) Task selection: §5 step 2 deletes closed rows ('no tombstones'), so the deps column dangles — a cold session reading 'deps: P1' with no P1 row anywhere cannot distinguish 'done' from 'a row I am failing to find'.

> Evidence: Design §5.2 ('delete rows that closed... no tombstones, no strikethroughs') vs the §3 board schema's deps column. Today's phase table only resolves this because DONE rows persist as strikethrough tombstones (HANDOFF.md line 146: '~~leg 7 4c-i~~ ... DONE 2026-08-16', which P3's 'deps: P1' resolves against) — exactly the affordance the redesign removes without replacement.

> Suggested change: Add to §5 step 2: 'deps cells may only name OPEN rows; when deleting a closed row, sweep its id out of every deps cell (a satisfied dep is simply removed — the ledger records the closure)'. Cheap, and it makes deps semantically 'open blockers' which is what a picker actually needs.

**[blocker]** (d) Write-back: the §5 protocol never says to rewrite the Banner, so a literal-minded session leaves the first thing the next session reads stale — old gate state, old as-of date, headline pointing at the previous ledger entry.

> Evidence: §3 Banner spec: 'gate state, as-of date, last session's one-line headline → ledger entry <date>'. §5 has exactly five steps (ledger append, board edit, lessons, doc fixes, traps) and none touches the banner. This is the exact rot mode §1 documents (the 2026-08-14 banner carrying three stale numbers) recreated by omission. Ordering is otherwise right — ledger first is correct because the banner and 'moved' semantics cite the new entry's YYYY-MM-DD[letter] key, which must exist before anything references it.

> Suggested change: Insert as step 2: 'Rewrite the Banner (gate state as observed this session, today's date, the new headline, → the entry key you just created)', then board edit as step 3. Keep ledger append first.

**[should-fix]** (e) Signals: the design's own §9.1 priority seeds violate its §4 NEXT definition — ttuStarFree (ii), the perf round-6 pass, and P13 neither block nor feed NOW (leg-7 4c-ii+7), so a fresh reader applying the table literally would file all three as LATER.

> Evidence: §4: NEXT = 'queued behind NOW; blocks or feeds it, or user-flagged'. §9.1 seeds those three as NEXT while today's HANDOFF ordering notes say the opposite of 'feeds': 'P6/P7 are a fully independent leg', 'P13 is independent of every phase above'. Either everything rides the 'user-flagged' escape clause (making the definition noise) or the definition is wrong; a cold session re-ranking the board will misfile items either way.

> Suggested change: Redefine NEXT as 'the ≤3 items most likely to be picked next or run in parallel with NOW (by dependency, user flag, or ranking)'. The capacity bound is doing the real work; the definition should not pretend a dependency relation that the seeds themselves lack.

**[should-fix]** (c) Execution: user-assigned tasks that map to LATER rows have no promotion protocol — 'measure R6-6' means working an item while 🎯/NOW points elsewhere, and promoting it at session start would breach 'exactly 1 NOW' or overflow NEXT ≤3 with the displaced item.

> Evidence: §4 capacity table (NOW exactly 1) + §3 (LATER rows have no block) + §5 (write-back is end-of-session only). 'Measure perf item R6-6' maps to the round-6 row, which is a §9.1 NEXT/LATER item; nothing tells the session whether the board must be touched before work starts, and a rule-following small model may burn context 'fixing' the board first or refuse to deviate from NOW.

> Suggested change: Add one charter line: 'A user-assigned task overrides the board; do not re-rank at session start — work it, and re-rank once at write-back (NOW = what you would recommend the NEXT session do).' This makes NOW explicitly a recommendation for unassigned sessions, not a constraint on assigned ones.

**[should-fix]** (b)/(c) LATER rows lose today's notes column with no declared destination: per-row landing criteria and item-scoped traps (P5's 'Sd/Td cannot be the witness', P11's 'do not extend corpus-wide', P12's 'a prediction, not an observation') have no home once the row is `id|item|pri|size|deps|moved` and non-NOW items get no block.

> Evidence: Today's phase table (HANDOFF.md 146-157) carries a notes cell on every row; the §3 schema drops it and §3 says LATER/HOLD/SOMEDAY get NO block — 'their row's pointer is enough'. That holds only if migration step 6 verifiably relocates each note into the pointer target; the design's step 4 does verify-then-delete for correction copies but no analogous verify step exists for notes-column traps/criteria. For the R6-6 simulation the pointer target (docs/perf-round6-audit-2026-08.md) does carry the finding evidence and an editorial digest, but not the measurement method (benchmarks/_harness.py, paranoia=False convention, docs/perf-next-round.md round protocol) — the session recovers those only via the routing table plus CLAUDE.md, a chain the design assumes but never states.

> Suggested change: Add to migration step 6: 'for every row demoted to LATER/HOLD/SOMEDAY, verify the pointer target contains the row's current notes-cell traps and completion criterion; append them there (dated) if not'. State the invariant in docs/README.md: a bare row pointer must resolve to a target that is self-sufficient (its own context + method pointers).

**[should-fix]** (e) `moved` is ambiguous and its stated purpose ('an old date on a NOW/NEXT row is a lie detector') false-positives on healthy work: P3 is sized 2-3 sessions, so sessions 2 and 3 progress NOW with no state change and the date goes stale while everything is fine.

> Evidence: §3 defines moved = 'date of last state change'; §4 sizes NOW items in sessions ('2-3 sessions, the big one' in today's P3 row). Under the literal definition, a multi-session NOW legitimately carries an old date, which the design tells the reader to treat as a lie — a cold session will either distrust a healthy board or 'fix' it by redefining moved ad hoc.

> Suggested change: Define moved = 'last date any session progressed or re-ranked this item' and add to §5's board step: 'touch moved on every row you worked, not only rows whose pri changed'. Then an old date on NOW really is a lie.

**[should-fix]** (a)/(c) The live leg-7 scope doc sits inside formal/history/ while the design treats history/ as the frozen zone, so the NOW item's read-first points into a directory whose convention (and §8.10 guard) says 'provenance, may now be false'.

> Evidence: Today's NOW read-first target is formal/history/leaf-family-split-scope-2026-08-05.md (HANDOFF.md line 940 names it as leg 7's scope doc; P4/P5 rows cite its §7/§9.3). Design §6 routes 'retired anything' to history/ with the standard frozen banner, and §8.10's guard allows ★ only inside docs/history/ + formal/history/ — i.e. history == frozen. A cold session that internalizes the liveness taxonomy meets either a FROZEN banner over the plan it must execute ('several statements may now be false') or an unbannered live file in the frozen zone; either reading is wrong. Worse, the scope doc genuinely contains refuted cells (§11.6's cost sizing, refuted per the 2026-08-16 banner), so 'trust it as live' is also not quite right.

> Suggested change: Either move active scope docs out of history/ (e.g. formal/leaf-family-split-scope.md until the leg lands, then retire), or add an explicit third liveness state to docs/README.md: 'ACTIVE-PLAN — lives in history/ for provenance, corrections appended dated at top, live until its board rows close'. Do not leave it implicit.

**[should-fix]** (d) The protocol has no degraded-context path: at ~10% context a tired model will do step 1 (cheap append), maybe step 2, and silently skip steps 3-5 (multi-file runbook/satellite edits) — and §5 never connects the skips to the ledger's 'Still owed:' closer.

> Evidence: §5 steps 3-5 each require opening and editing another file (sabotage-procedure.md, a satellite, CLAUDE.md), the expensive operations at end-of-context; the design elsewhere mandates 'Still owed:' as the entry closer (§5.1) but never says skipped protocol steps go there, so the skip leaves no trace and the lesson/correction is lost — the append-layering disease's root cause (cheapest path wins) reapplied to the new system.

> Suggested change: Add to §5: 'Minimum viable write-back = steps 1-2 (+ banner). If context is short, list every skipped step-3/4/5 action verbatim under Still owed: — the next session executes them before its own work.' This makes the cheap path leave a recoverable record.

**[should-fix]** (d)/(e) The mechanical guard (§8.10) is deferred to a future session, leaving an interim window where nothing enforces exactly-one-NOW, the ⚠ budget, or the line ceiling — the repo's own house rule says a doc warning will not hold.

> Evidence: §8.10 defers all guards ('Later, as code (not this session)'); CLAUDE.md's sabotage bullet: 'prefer a mechanical refusal over a doc warning — the next person will not read the doc'. The capacity rules are the design's central mechanism (§4: 'the capacities are the point'), and they are exactly the kind of prose constraint this repo has watched rot (the formal/HANDOFF '~250 lines' self-claim, §1). Every session between migration and guard-landing can add a second NOW or an 11th ⚠ silently.

> Suggested change: Land the trivial subset with migration step 6 itself: a 5-line check (wc -l ceiling, grep -c '| NOW |' == 1) with its one sabotage run. Defer only the fuller guard (★ sweep, ⚠ budget, formal side) to the board item.

**[should-fix]** (a) Migration step 7's 'absorb the banner footguns (most already there)' is an unverified claim over the exact content a cold session most needs — at least the pipe-exit-code footgun (the one that bit twice) is NOT in CLAUDE.md today.

> Evidence: Verified: CLAUDE.md contains no tail/tee/exit-code line; the footgun lives only in docs/gate-runbook.md (lines 107-108, 448, 474) and in the current HANDOFF banner, which the migration deletes. Placement in gate-runbook is arguably sufficient (it applies exactly when running the gate, and CLAUDE.md routes there), but 'most already there' is the same unaudited-disposition pattern the design's own step 4 refuses for correction copies.

> Suggested change: Make step 7 a named four-item checklist (pipe-exit-code, HYPOTHESIS_SEED, MAX_TESTS_XFAILED=0, zero-headroom floors) with an explicit destination per item and a verify-then-delete rule, mirroring step 4's discipline.

**[nit]** (e) The 🎯 badge duplicates pri=NOW — two markers that must flip together, and a small model editing the board will move one and forget the other, creating the board's first internal contradiction.

> Evidence: §4: 🎯 'marks the NOW row/block', budget 1; the pri column already says NOW with capacity exactly 1. Redundant state with no reconciliation rule.

> Suggested change: Drop 🎯 from rows entirely (the NOW word is grep-able, which was the stated goal); keep it at most as the item-block heading marker, or declare pri authoritative and 🎯 decorative in docs/README.md.

**[nit]** (e) The signal legend lives only in docs/README.md, so the board's pri words are read cold without their capacity semantics; NOW/NEXT/LATER are guessable but HOLD vs SOMEDAY is not ('deferred by decision' vs 'revisit on need' is a distinction a fresh Sonnet will not reconstruct).

> Evidence: §3's board section carries no legend; §6 puts 'the signal legend + budgets' in docs/README.md, which the charter's 'read this file fully + CLAUDE.md + your read-first list' never routes a session through — CLAUDE.md gets only 'one pointer line' to it (§6).

> Suggested change: Spend one line above the board table: 'pri: NOW(1) > NEXT(≤3) > LATER > HOLD(decision→ptr) > SOMEDAY — legend: docs/README.md'.

**[nit]** (d) Principle 6 ('don't state a number prose can't enforce') is violated by the design's own unenforced numbers: ledger body '≤ ~30 lines' and item blocks '≤12 lines' are not covered by the §8.10 guard.

> Evidence: §5.1 and §3 state both figures; §8.10's guard list covers HANDOFF/formal ceilings, NOW count, ★, ⚠ — not ledger-entry or block lengths. Same class as the formal/HANDOFF '~250 lines' rot the design diagnoses in §1.

> Suggested change: Either add the two figures to the §8.10 check or restate them unnumbered ('a screenful'), per principle 6 taken strictly (the user's open question 3 already leans this way).

**Overall:** The design is sound where it matters — the board/ledger split, bounded priorities, and one-home routing are all promoted from conventions this repo already runs, and a cold session's orientation mostly works because CLAUDE.md (auto-loaded) genuinely covers the gate, push permission, and the validation matrix, so the §3 skeleton's reliance on it is legitimate. The single most important change is resolving the root-vs-formal HANDOFF ownership contradiction: the charter's "all live status lives HERE and nowhere else" is false the moment §7 preserves formal/HANDOFF.md as a live doc, and it is exactly the "continue leg 7" cold session — the design's proposed NOW — that hits the ambiguity first. Second priority is the trio of mechanical holes a small model will actually fall into: dangling deps after row deletion, the banner missing from the write-back protocol, and no degraded-context path tied to "Still owed:".

### Rot auditor

**[blocker]** Every ceiling in the design is prose until §8 step 10, step 10 is explicitly 'later, as code (not this session)', and the guard item is not even seeded into NOW/NEXT — so the entire post-migration habit-forming window has zero convergent force, and this repo's own record shows 'designed, NOT built' items sit for weeks.

> Evidence: Design §8 step 10 defers all mechanical checks; §9 Q1's proposed seeds are NOW=P3, NEXT = ttuStarFree(ii) + perf round-6 + P13 claim-rot gate — the handoff guard is absent, so it is born LATER. Measured precedent in HANDOFF.md itself: the P13 claim-rot gate (lines 715–763) is 'designed and measured 2026-08-16, NOT built'; leg 7 was 'DEFERRED, not scheduled' from 2026-08-05 and only started 2026-08-09 under pressure. Every interim violation (a dated layer, a 13th ⚠, a 260th line) is silent, and the next cold session imitates whatever the file looks like — one miss restarts append-layering exactly as §1 diagnoses. The design even flags this itself (§9 Q3, principle 6: 'don't state a number prose can't enforce') but leaves it as an open question.

> Suggested change: Land a minimal STANDALONE lint in the migration session itself — scripts/handoff_lint.sh: wc -l ceilings on both HANDOFF files, exactly one NOW row, NEXT ≤ 3, zero ★ outside the two history/ dirs, ⚠ ≤ budget, FROZEN in the first 5 lines of every docs/history//formal/history file (ledgers excepted). As a standalone script it needs its own sabotage run but NOT the full ten-phase gate re-run that pushed the guard to 'later'; wiring it into verify.sh becomes the board item. Add it as step 0 of the §5 write-back protocol ('run the lint before committing a HANDOFF edit').

**[should-fix]** The session-log entry cap (body ≤ ~30 lines) contradicts the measured behavior of the very convention it copies — PROOF_STATUS entries run 71–155 lines — and step 10's guard list does not cover ledger entry size at all, so session-log.md is the designated relief valve that will become the new accretion zone within its first week.

> Evidence: formal/history/PROOF_STATUS.md, the template §5 names: entry 2026-08-16 spans lines 11–157 (~147 lines), 2026-08-15 spans 158–228 (~71), 2026-08-14 spans 229–383 (~155); headings alone run 40+ words of bold caps. The forces the audit brief names ('every session's findings feel banner-worthy', low-context session ends) apply hardest to the ledger because it is where narrative is licensed to go. §8 step 10 checks file line counts, NOW count, ★ and ⚠ — nothing about entry span or headline length. A ballooning ledger is cheaper than a ballooning board (cold readers take the top entry only), but headline bloat feeds directly into the §3 banner ('last session's one-line headline'), which is read by every session.

> Suggested change: Either drop the 30-line number per principle 6 and state the real contract ('cold readers consume headlines + the top entry; length costs only the writer'), or make it enforceable in the lint: newest-entry span ≤ N lines and '## ' heading lines ≤ ~120 chars in docs/history/session-log.md. Do the same for the one-line banner headline (it is copyable from the ledger heading, so cap the source).

**[should-fix]** The ⚠ ≤ 10 file-wide budget collides with the measured trap load of a single long-running NOW item, and at trap #11 the prescribed response — move traps to a satellite — is exactly the 'editing the target doc feels riskier' action whose avoidance caused the disease, while the cheap evasion (keep the trap, drop the glyph) is invisible to the step-10 guard.

> Evidence: The current B1 block (HANDOFF.md lines 527–714) carries roughly eight genuine traps for leg 7 alone ('4c cannot land alone', 'Sd/Td cannot be the witness', '§11.3 is wrong in two places', 're-derive the criterion from the generated block', ...), and leg 7 will occupy NOW for multiple sessions. §4's escape ('the traps belong in a satellite') names no destination and no operation; under low context a session will either add ⚠ #11 silently or strip the glyph and keep bold ALL-CAPS — the step-10 guard counts only ⚠, and 'bold ALL-CAPS survives only inside ⚠ lines' is an ungrepped prose rule. HANDOFF.md today has 23 ⚠; the mechanism that produced them has not changed.

> Suggested change: Define the overflow operation: each NOW/NEXT item's scope doc (or PROOF_STATUS entry for formal items) gets a named 'Traps' section that the block's read-first line points at, so demotion is a defined move, not an invention. Add to the lint: ⚠ count ≤ budget AND a scan for bold-ALL-CAPS runs outside ⚠ lines in living docs, so glyph-shifting is loud.

**[should-fix]** The 12-line item-block cap has no stated overflow path for refutation-provenance content (the bulk of today's 90-line B1), and nothing in the §5 protocol maintains the block's read-first list — so six weeks of mid-arc refutations accumulate in the ledger while the NOW block's pointers go stale, and a cold session resumes on a refuted step.

> Evidence: B1's content is mostly 'this was wrong, measured, here is why' (the allocation refuted three times, §11.3 wrong twice, the landing criterion stale three times — HANDOFF.md lines 548–614). Under the design that content routes to ledger entries and scope-doc corrections, which is right — but the cold reader's only bridge back is the block's 'read-first: the exact docs/sections' (§3), and §5's five steps cover ledger, rows, lessons, corrections, and traps, never 'rewrite the NOW/NEXT blocks'. formal/HANDOFF's routing table says to read only the TOP PROOF_STATUS entry, so a read-first line citing '2026-08-15 §11.6' silently rots as entries stack above it — the same append-over-edit force, one level down.

> Suggested change: Add a §5 step: 'NOW/NEXT blocks are board, not ledger — rewrite them in place every session that touches the item, including the read-first list' (replace-semantics, mirroring principle 2). The 12-line cap then survives because the block is regenerated, not accreted; enforce per-block length in the lint if cheap, otherwise rely on the file ceiling.

**[should-fix]** The 'moved' column cannot do the job the design assigns it: an old date on a NOW row is ambiguous between 'no work happened' (legitimate) and 'work happened elsewhere and was not written back' (the lie it is meant to detect), and nothing updates it when a satellite changes state, so staleness is undetectable exactly in the failure case.

> Evidence: §3: 'moved = date of last state change (a staleness detector: an old date on a NOW/NEXT row is a lie detector)'. But the board author is the forgetter in the stated failure mode (a perf measurement lands in docs/perf-round6-audit-2026-08.md, a scope-doc correction lands per §5 rule 4 — neither touches the board), and no §8 step-10 guard mentions 'moved' at all. An unenforced per-row date is principle 6 violated once per row.

> Suggested change: Make it cross-checkable: require ledger entries to name the board row ids they touched (the board already has an id column), then lint two ways — every 'moved' date must equal some session-log entry date, and no ledger entry newer than a row's 'moved' may name that row's id. Same check catches the double-entry gap in §5 step 1 (formal-heavy sessions skipping the root ledger entry): newest session-log date must be ≥ newest PROOF_STATUS date.

**[should-fix]** The two handoffs will drift stylistically again: step 9 is last and 'independent', so a died session leaves root on NOW/NEXT while formal still runs ★★; the step-10 ★ guard is path-based and exempts formal/history/, where the LIVING ledger PROOF_STATUS lives, contradicting §4's liveness-based ban; and formal/HANDOFF's 'House rules' section is a second charter that nothing points at docs/README.md.

> Evidence: Verified: formal/HANDOFF.md carries 36 ★ and its own 'House rules (non-negotiable, user-adjudicated)' section (line 234); §8 says 'Steps 1–8 are root-side and independent of 9'. §4 retires ★ 'from living docs' while step 10 checks 'zero ★ outside docs/history/ + formal/history/' — PROOF_STATUS is append-only-living AND inside formal/history/, so new entries may legally keep ★-inflation (current entries are saturated with it), and those headings are what the banner headline copies. Two boards converging on one convention only via a 40-line README that formal's own charter never cites is exactly how the last divergence happened.

> Suggested change: Pull the cheap half of step 9 forward into the same session as step 6: convert formal/HANDOFF's banner + priorities to the §4 vocabulary and delete the '~250 lines' claim, deferring only the deep table/narrative surgery. In docs/README.md state the ★ rule as liveness-based with an explicit carve-out ('append-only ledgers: allowed in frozen entries, discouraged in new ones' — or ban it in new entries outright), and add one line to formal/HANDOFF's house rules: 'shared doc conventions live in docs/README.md'.

**[should-fix]** The block-by-block disposition map exists only 'in the workflow record' (not the repo), so if the migration is executed by a later or different session — the likely case for a DRAFT awaiting user review — the per-line dispositions are lost and step 6's rewrite re-derives them from a 979-line file cold, which is where content gets silently dropped or silently kept.

> Evidence: §3: 'the full block-by-block disposition map with line ranges is in the workflow record; the migration steps in §8 encode it' — but §8 encodes categories, not per-line calls. Concrete case: the subsumed-fixtures entry (HANDOFF.md lines 789–814, ~26 lines that 'exist only to record the reasoning') has no obvious §6 home; whether it archives, compresses to a row pointer at the test file, or dies is exactly the kind of call the map made and the repo will not have.

> Suggested change: Commit the survey/disposition map alongside this plan (docs/history/handoff-migration-map-2026-08.md, frozen when the migration lands). It is disposable provenance, which is what docs/history/ is for, and it makes 'any prefix of the list is a consistent state' true for the rewrite step too.

**[nit]** The ceilings carry 50–100 lines of built-in headroom above the target size (~186-line content, ~150–200 target, 250/300 ceilings), which at the file's measured growth rate (~13 lines per session of discussion) is roughly six weeks of silent accretion before even a built guard fires once.

> Evidence: §1: 'it gained 13 lines while the redesign was being discussed'; §3 targets ~150–200; §8 step 10 sets 250/300. A guard that first fires on the fifth accretion layer teaches the wrong lesson — by then the layers look like the convention.

> Suggested change: Set the ceiling relative to the landed size (landed + ~10%, recorded in the guard with provenance per the sabotage-procedure durability ranking), and raise it only deliberately. The point of the guard is to fire on the FIRST appended layer, not the fifth.

**[nit]** Frozen-banner enforcement is a one-time sweep (step 8) with no ongoing check, while the design's own §6 survey shows the violation class recurs every time a design doc lands — so in six weeks the next landed design record under docs/architecture/ will sit unbannered exactly like p13/r4bf do today.

> Evidence: §6 lists four current recurrences of the same pattern (perf-round HTML-comment banners, generator-coverage 'Nothing in the repo was modified', p13/r4bf 'landed, unmarked'); archiving is the chore the audit brief says nobody is forced to do, and step 10's guard list contains no banner check.

> Suggested change: Two lines in the lint: every file under docs/history/ and formal/history/ (ledgers excepted) must contain 'FROZEN' in its first 5 lines; and docs/README.md gets the routing rule that a design record freezes AT landing (the frozen banner is part of the landing checklist, like the CORRESPONDENCE update already is for algorithm changes).

**Overall:** The design is sound where it matters — the diagnosis is measured, every mechanism is promoted from a convention this repo already runs, and boards-replace/ledgers-accrete is the right cure for append-layering. Its one structural weakness is that all enforcement is back-loaded to §8 step 10 while the guard item is not even seeded into NOW/NEXT, leaving the habit-forming post-migration window governed by exactly the kind of unenforced prose numbers the design's own principle 6 forbids — and the repo's record (the claim-rot gate: designed, measured, NOT built) shows what happens to deferred guards. The single most important change: ship a minimal standalone handoff lint in the migration session itself (ceilings, NOW=1, ★ paths, ⚠ budget, frozen banners), sabotaged but not yet gate-wired, and fix the two places where a capped structure has no defined overflow operation (ledger entry size, the NOW block's trap/read-first maintenance).

### Migration-risk auditor

**[blocker]** The plan never mentions that gate step 4e (formal/conformance/doc_counts.py --check) scans almost every file it rewrites or creates, so steps 4-9 can turn the gate red and no step says to re-run 4e.

> Evidence: doc_counts.py:295-296 `_PROSE_GLOBS = ("formal/*.md", "formal/conformance/*.py", "docs/*.md", "docs/architecture/*.md", "HANDOFF.md", "CLAUDE.md")` — that covers HANDOFF.md (step 6), CLAUDE.md (step 7), formal/HANDOFF.md and formal/ARCHITECTURE.md (step 9 moves the ~40-row theorem table there), the new docs/README.md (step 2), and the new docs/architecture/bulk-merge-design.md (step 3). The check (doc_counts.py:317-347) fails on any unmarked non-live 'N corpora' figure, and it only looks TWO lines above for the required date+pastness word (`ctx = lines[max(0, i-3):i]`, line 342). Concretely fragile content the migration will move: HANDOFF.md:598 "23 corpora" passes today only because "used to" sits within the window; formal/HANDOFF.md:862 "**19** corpora" escapes the regex ONLY because the bold markers break the `(\d+)[- ]corpora` match — any reflow while moving that table into formal/ARCHITECTURE.md trips step 4e. Only docs/history/ and formal/history/ destinations are exempt (doc_counts.py:327). Nothing else in the repo mechanically reads HANDOFF.md (verified: no HANDOFF reference in formal/verify.sh, no .github directory, scripts/pg_local.sh:9 is a comment).

> Suggested change: Add to §8: after each of steps 2-9, run `python -m formal.conformance.doc_counts --check`; and add a content rule to §5/§6: any historical corpus figure that survives a move must carry its date AND a pastness word ON THE SAME LINE (the two-line context window does not survive reflow).

**[should-fix]** Step 6 deletes the banner footguns from HANDOFF.md before step 7 moves them into CLAUDE.md, violating the plan's own 'any prefix of the list is a consistent state' claim.

> Evidence: Plan §3 (line 78-79): banner shrinks to gate state + headline, '(Footguns move to CLAUDE.md ...)'; §8 orders the HANDOFF rewrite (step 6) before the CLAUDE.md touch-up (step 7), and hedges 'most already there' — conceding some are not. Plan lines 218 and 253-254 claim each step leaves the repo coherent if the session dies; after step 6 alone, any footgun not already in CLAUDE.md exists in no living doc.

> Suggested change: Either swap the CLAUDE.md footgun absorption ahead of the rewrite (do the additive half of step 7 before step 6), or fold it into step 6 as a single atomic edit; leave only the subtractive 'drop working-rhythm text' part in step 7.

**[should-fix]** Step 6 re-derives the board with no commitment to preserve existing item ids (B1, B2, board items 1/2, P3-P13), which the append-only ledger, the frozen archives, and code docstrings all cite as stable keys.

> Evidence: formal/history/PROOF_STATUS.md:14 ('board items 1 (leg 7) and 2 (`ttuStarFree`)'), :699 ('root board item B2'), :958 ('See root HANDOFF.md board item'); docs/history/handoff-status-2026-07.md:52 ('Live owner: board item (A)'), :652 ('the live board item (B1) in the root HANDOFF.md'); docs/history/handoff-status-2026-08.md:606 ('Resume detail in board item 1 (B1)'); HANDOFF.md:783 ('Tracked in board item (B2) above'). PROOF_STATUS is never retro-edited by its own convention, so these citations can only be kept true by keeping the ids. Plan principle 5 ('Stable keys, never positions') demands exactly this, but §8 step 6 says only 'board table re-derived from the phase table + every open item found by the survey'.

> Suggested change: Add to step 6: the new board's `id` column carries forward every existing id (B1/B2, P3-P13, ZT-*); new items get fresh ids; an id is never reused.

**[should-fix]** Step 5 archives HANDOFF's 'What landed 2026-08-11' block into docs/history/handoff-status-2026-08.md while that file's own header (lines 16-17) tells readers to 'Read HANDOFF.md's "What landed 2026-08-11" for the true end state' — the archive will point at a HANDOFF section that now lives inside the archive itself.

> Evidence: docs/history/handoff-status-2026-08.md:16-17: 'Read `HANDOFF.md`'s "What landed 2026-08-11" for the true end state.' Plan step 5 explicitly lists 'the 2026-08-11 status run' among the bulk-archived narrative. No step edits the archive's header.

> Suggested change: In step 5, repoint that header line to the block's new location (the 'Retired 2026-08-16b' section) as a dated correction — the 2026-07 sibling's '## Corrections applied on archiving' section (handoff-status-2026-07.md:20) is the precedent for editing a frozen file this way.

**[should-fix]** Step 10's guard 'zero ★ outside docs/history/ + formal/history/' is unsatisfiable after steps 1-9: seven files the plan never de-stars keep ★, including CLAUDE.md itself and spec-deviations.md, which §9.4 explicitly defers.

> Evidence: grep -rl '★' over non-history *.md finds: CLAUDE.md ('★ No figures here, deliberately'), docs/gate-runbook.md, docs/sabotage-procedure.md, docs/spec-deviations.md (left as-is per plan §9.4), docs/subagent-fanout-runbook.md, formal/CORRESPONDENCE.md, and docs/design/generator-coverage/divergence-sweep-report.md — the last is frozen IN PLACE by step 8 (docs/design/, not docs/history/), so a path-based guard still flags it. §4 says frozen archives keep their ★, but the guard as sketched is path-based, not banner-based.

> Suggested change: Scope the step-10 ★ check to HANDOFF.md and formal/HANDOFF.md only (the two boards), or make the exemption banner-aware ('file whose first lines contain FROZEN'), and note in §4 that ★ in untouched living satellites is out of this round's scope.

**[should-fix]** Dropping HANDOFF's working-rhythm rules (step 6) and doing formal/HANDOFF surgery (step 9) dangles rule-numbered citations that live in gate code and living docs, with no redirect step anywhere in the plan.

> Evidence: 'HANDOFF.md working-rhythm 3b' is cited by formal/conformance/doc_counts.py:234 (the step-4e check's own contract comment) and formal/conformance/extractor.py:293; plan §3 line 102 says 'The current rules 2/3/3b/5 duplicate CLAUDE.md and drop out'. formal/HANDOFF.md 'house rule N' is cited by formal/conformance/statement_pin.py:38 (rule 1), docs/sabotage-procedure.md:268 (rule 2), docs/subagent-fanout-runbook.md:173 (rule 6), docs/history/handoff-status-2026-07.md:183 (rule 7). formal/FINAL_REVIEW.md:3 and formal/CORRESPONDENCE.md:3 cite formal/HANDOFF '"The next task"', a section §7 rewrites; formal/README.md:34/53/105 and formal/ARCHITECTURE.md:13/633 describe formal/HANDOFF as 'the state of the world', the exact zone §7 moves out.

> Suggested change: Add a redirect sweep to steps 6 and 9: repoint the working-rhythm citations to the rule's new home (CLAUDE.md / docs/README.md), keep formal/HANDOFF's house-rule numbering byte-stable (treat rule numbers as stable keys per principle 5), and update the formal/README.md + formal/ARCHITECTURE.md + FINAL_REVIEW.md descriptions of what formal/HANDOFF now is.

**[nit]** A long tail of inbound HANDOFF references (some already dangling from earlier archivals) is not covered by any step; the migration is the natural moment to fix them.

> Evidence: README.md:636 'full rationale in `HANDOFF.md`' — the 2026-07-17 decision rationale is no longer in HANDOFF.md (grep for 2026-07-17 finds only an unrelated line 921); README.md:625 points at HANDOFF for live tracking (survives, but the section names change). scripts/pg_local.sh:9 cites '(HANDOFF.md, Standing/latent, 2026-07-26)' — a section step 5/6 removes. tests/test_ttu_tupleset_parent_types.py:50 cites HANDOFF.md by LINE NUMBER ('``:48``') and :79/:422 correct a HANDOFF classification that will be archived. tests/test_zt_p5_readjudication.py:3 cites 'HANDOFF.md "Zero-trust review 2026-07-26"', archived to docs/history/handoff-status-2026-07.md since 2026-07-29 (spec-deviations.md:2645 already uses the corrected citation). tests/genswarm.py:464/486 and tests/test_hypothesis.py:85/372/521 cite 'HANDOFF plan 1b/item 1', retired 2026-08-11 (test_generator_coverage.py:6-7 shows the correct archived citation).

> Suggested change: Append a step-6 sub-task: grep the tree for `HANDOFF` outside docs/history + formal/history and repoint every citation whose target moved, using the file::section-in-archive form spec-deviations.md:2645 already models.

**[nit]** Step 5's section label and convention citation are slightly off: the 2026-08 archive's existing section is the unlettered '## Retired 2026-08-16 (leg 7 4c-i session)', and the named 'corrections-on-archiving convention' exists as a formal section only in the 2026-07 file.

> Evidence: docs/history/handoff-status-2026-08.md:477 '## Retired 2026-08-16 (leg 7 4c-i session)' — appending '2026-08-16b' implies the existing one is 'a' without saying so. The explicit convention section '## Corrections applied on archiving (2026-07-29)' is in handoff-status-2026-07.md:20; the 2026-08 file instead carries corrections as header ⚠ bullets (lines 14-22). Both shapes exist, so 'following the existing convention' is ambiguous about which. Otherwise fact-checks pass: leaf-family-split-scope-2026-08-05.md carries §11.3 (:720), §11.5 (:755, '§11.3 is wrong in two places'), §11.6 (:813), §11.7 (:876); echain-widening-plan-2026-07-28.md carries §C.1-§C.6 (:385, :404, :459, :505, :548, :618); docs/README.md, docs/history/session-log.md, docs/architecture/bulk-merge-design.md, and formal/history/claim-rot-gate-design-2026-08-16.md all confirmed absent (no collisions).

> Suggested change: In step 5, name the shape being extended (the 2026-07 file's 'Corrections applied on archiving' section, written under the new 'Retired 2026-08-16b' heading) and either retro-label the existing :477 section '2026-08-16a' or title the new one '(second batch)'.

**[nit]** Step 3's docs/architecture/bulk-merge-design.md lands unindexed in a directory whose every file is listed in overview.md's table, and the moved 27-line sketch is not the 'fuller design doc' its own text asks for.

> Evidence: docs/architecture/overview.md:13-24 is a complete table of the directory's files (p13-bulk-build-design.md and r4bf-bulk-backfill-design.md each have rows); no step updates it. HANDOFF.md:874-877: 'A fuller design sketch was produced 2026-07-19 ... not yet written to a docs/ design doc — write it up (match docs/architecture/p13-bulk-build-design.md style) before implementing' — so the plan's parenthetical '(its own text already asks for this)' holds for the destination but the payload is the board sketch, not that fuller design; naming it like the two landed design records (which step 8 simultaneously freezes as 'landed') invites misreading it as one.

> Suggested change: In step 3, add an overview.md table row, and open the new file with one status line ('SKETCH, unbuilt — the fuller 2026-07-19 design is still owed') so it cannot be read as a landed design record.

**Overall:** The §8 plan is executable and its load-bearing factual claims check out against the repo (both correction spot-checks pass, the 2026-08 archive has an extendable "Retired <date>" convention, no file collisions, the 979/1005/"~250 lines" measurements are exact, and no gate phase greps HANDOFF paths). The single most important change: make the plan aware of verify.sh step 4e — doc_counts.py's prose refusal scans HANDOFF.md, CLAUDE.md, docs/*.md, docs/architecture/*.md, and formal/*.md, i.e. nearly every file steps 2-9 rewrite or create, and its two-line date+pastness context window does not survive block moves or reflows (formal/HANDOFF's "**19** corpora" escapes the regex today only via markdown bold). Secondary: fix the step 6→7 footgun-loss window that breaks the plan's own any-prefix-coherent invariant, and commit step 6 to carrying forward board ids (B1/B2, P3-P13) that the append-only ledger and frozen archives cite as stable keys.
