# Session ledger

Append-only, newest first, one entry per session (FRAMEWORK §7.1).

---

## 2026-11-25a · kind: open

- **opened:** 2026-11-25T10:47:48+08:00 by claude-code/claude-opus-5-5
- **follows:** 2026-11-24b
- **start head:** 0f5507cfdabf58651e02a319aaaab19b833fb20d
- **granted:** ASK-13

---

## 2026-11-24b · kind: close

- **follows:** 2026-11-24a
- **rows:** DEC-23 (new, owner); TK-308 (comment: DEC-23 relaxes to local and/or CI on push); TK-310
  (new, SOMEDAY)
- **receipts:**
  - guards: verify.sh ten phases at 8ea2950: 10 passed (each rc=0, PASSED line read); gate_status
    COVERED; context-engine lint clean
  - read: orient; DEC-22; DEC-23; docs/charter.md; docs/criteria.md
  - housekeeping: hk run close: 0 writes, 0 op log lines
  - banner: kept 2026-11-16a
- **summary** (the owner digest):
  - Owner words recorded verbatim as DEC-23 (ORM backend abstraction, psycopg locks/pubsub optional,
    fuzz local and/or CI on push, why G-1 is an attempt).
  - Charter and CLAUDE.md fuzz clause updated from DEC-23 by a writer, checked by a separate
    verifier (2 overstatements fixed), gate COVERED, committed 8ea2950; not pushed.
  - Board prioritization proposed read-only in .scratch/s24b/prioritize/proposal.md: NOW TK-146;
    NEXT TK-309, TK-148, TK-305, TK-308, TK-303; close TK-239, TK-252 (verify first). Nothing
    applied.
- **Still owed:**
  - Owner: apply the proposed re-rank and the two closes (TK-252 verified first)?
  - Owner: push the 5 local commits (41b24c0..8ea2950 + close) and tag v0.1.3 (TK-303), then install
    trial
  - Owner: write user stories (TK-302)? on-push perf-vs-brute-force check (TK-34)? TK-43 README
    notes in owner voice?
- **start head:** 4f919c3a1551e1104c9888cc1b32d4d56b0e795a

---

## 2026-11-24a · kind: close

- **follows:** 2026-11-23a
- **rows:** ASK-12 (granted); DEC-16 (accepted); DEC-22 (new, owner); TK-308 (new, NEXT); TK-309
  (new, NEXT)
- **receipts:**
  - guards: 10 passed (lean, conf-tile 1-5, tests-tile 1-4) at 7f46197 + lint clean
  - read: docs/charter.md; docs/criteria.md
  - asked: none
  - granted: ASK-12
  - housekeeping: hk run close: 0 writes, 0 op log lines
  - banner: kept 2026-11-16a
- **summary** (the owner digest):
  - Owner: "Okay to all recommendations" (ASK-12, grant): DEC-16 accepted; TK-304 D1, TK-275 calls,
    2026-11-20a rerank, TK-146 in NOW accepted. 0.1.3 prep 4937211 pushed (CI green), publish dry
    run green, tag waits on the owner. decision_index removed. Charter and criteria filled from the
    owner words DEC-22 (7f46197, verified by a second agent, gate COVERED); AC-6 is the headline
    (engine refuses AC-0). TK-308 fuzz-on-push, TK-309 criterion markers.
- **Still owed:**
  - v0.1.3 tag on the owner word, then the install trial + installed_smoke.py (TK-303)
  - Push 7f46197 and the close commit on the owner go
- **start head:** 83f17df5dbb4cba68d36497b7d6994143793c92a

---

## 2026-11-23a · kind: close

- **follows:** 2026-11-22a
- **rows:** ASK-11 (granted)
- **receipts:**
  - guards: 10 passed (lean, conf-tile 1-5, tests-tile 1-4) + lint clean + fuzz 30/30 passed
  - read: none
  - asked: none
  - granted: ASK-11
  - housekeeping: hk run close: 0 writes, 0 op log lines
  - banner: kept 2026-11-16a
  - pushed: 0602841: owner go, ASK-11
- **summary** (the owner digest):
  - Owner: "Gate and push" (ASK-11, grant). Ten-phase gate COVERED on 0602841, lint clean; fuzz
    seeds 7,19,31,53,71,97 x 5 fuzz.yml modules all green (TK-304 read change). Pushed
    705407e..0602841; CI gate run 45079305281 and docs run 45079305298 green.
- **Still owed:**
  - Review TK-304 D1, the TK-275 design calls and the provisional NOW pick (TK-146)
  - CHANGELOG ### Fixed line for TK-304 at the next release
  - Publish dry run, v0.1.3 tag on the owner word, install trial (TK-303); review DEC-16 and the
    2026-11-20a rerank; delete .context-engine/env-309641b
- **start head:** 7df03fc5083cb032ecc5cecb7a7d8ba84dedc7d3

---

## 2026-11-22a · kind: close

- **continues:** 2026-11-21b
- **rows:** TK-275 (closed); TK-304 (closed); RISK-1 (retired); TK-146 (promoted to NOW,
  provisional); TK-307 (commented)
- **receipts:**
  - guards: 10 passed (phases: lean, conf-tile 1-5, tests-tile 1-4) on 4b313ad, lint clean,
    gate_status COVERED; no fuzz sweep
  - read: orient, TK-275, TK-304, agent reports
  - housekeeping: hk run close: 0 writes, 0 op log lines
  - banner: kept 2026-11-16a
- **summary** (the owner digest):
  - Owner: "build stuff until then" (until the 4am token reset). Two rows done, all local, nothing
    pushed.
  - TK-275 closed (a727173, 235e9b2): 21 closed-row ACTIVE-PLAN docs frozen; handoff_lint now reds a
    plan doc whose named rows are all closed (17 sabotages seen red). TK-146 promoted to NOW as a
    provisional placeholder.
  - TK-304 closed (019c3c3, 84daa15, 4b313ad): lookup_reverse/expand no longer list a userset key
    check() refuses, same predicate both backends (D1, PROVISIONAL); RISK-1 retired; MIN_TESTS_ALL
    3995->4003.
- **Still owed:**
  - Fuzz sweep (read algorithm changed, TK-304) before pushing master 705407e..HEAD; push on the
    owner go
  - Review TK-304 D1, the TK-275 design calls and the provisional NOW pick (TK-146)
  - CHANGELOG ### Fixed line for TK-304 at the next release
  - Publish dry run, v0.1.3 tag on the owner word, install trial (TK-303); review DEC-16 and the
    2026-11-20a rerank; delete .context-engine/env-309641b
- **start head:** 8a5051f65b9d00ad97e02a5ad83789044cf0834f

---

## 2026-11-21b · kind: close

- **rows:** ASK-10 (granted, closed)
- **receipts:**
  - guards: 10 passed (phases: lean, conf-tile 1-5, tests-tile 1-4) on 705407e, lint clean,
    gate_status COVERED
  - read: orient, ASK-10, subagent report
  - granted: ASK-10
  - housekeeping: hk run close: 0 writes, 0 op log lines
  - banner: kept 2026-11-16a
- **summary** (the owner digest):
  - Owner granted the push (ASK-10): "Okay to push, token budget is almost up so use minimal tokens
    for this".
  - Gate re-run green on 705407e (all ten phases, lint clean); pushed 84743f4..705407e; CI green
    (gate run 44908478041, docs run 44908478098).
  - One tests-tile:1/4 run went red (47 failed, DLL init error 0xC0000142) after a haiku helper
    backgrounded it and lost the console; re-run in the foreground, all four tiles passed. A haiku
    helper cannot be trusted with a long phase here.
- **Still owed:**
  - Publish dry run (workflow_dispatch of publish.yml), then the v0.1.3 tag on the owner word, then
    install trial + installed_smoke.py (TK-303)
  - Review DEC-16 and the 2026-11-20a rerank moves
  - Delete .context-engine/env-309641b
- **start head:** 63579c2918db40ab87aff8b159fa2ae7ae5a2ba1

---

## 2026-11-21a · kind: close

- **continues:** 2026-11-20a
- **rows:** ASK-9 (granted, closed); ASK-4..8 (answered as DEC-17..21, closed); TK-264, TK-36,
  TK-243 (closed, retired); TK-67 (closed, merged into TK-277); TK-277 (Traps updated); TK-255
  (closed, retired); TK-303 (push + CI done; dry run and tag still owed)
- **receipts:**
  - guards: ten-phase gate at 8768dc6 (2026-11-21): lean PASSED; conformance 1246 passed
    (250+249+249+249+249); tests 3962 passed (991+991+990+990); gate_status COVERED there; the
    TK-255 close and this close are records-only and stale the tiles; lint: clean
  - read: orient (resumed context); tasks/ASK-4..8; .scratch fable second opinion
  - granted: ASK-9
  - housekeeping: hk run close: 0 writes, 0 op log lines
  - banner: kept 2026-11-16a
- **summary** (the owner digest):
  - Owner granted the push ("Okay push", ASK-9): gate re-run green at 84743f4, pushed
    fae13a2..84743f4, CI green (gate run 44883322220: all 10 jobs; docs run 44883322223).
  - Owner: "Okay to all of fables calls" -> DEC-17..21: TK-264, TK-36, TK-243 retired; TK-67 merged
    into TK-277 with the FoldAdmits stay-sites re-cited by symbol (checked first-hand); TK-255
    retired with the test comment rewritten (8768dc6, comment-only).
  - New standing rule (owner): babysitting gate phases and CI goes to a haiku agent the worker
    blocks on.
- **Still owed:**
  - Push master 84743f4..HEAD (records + the test comment) on the owner's go, after a gate re-run on
    that tree
  - Publish dry run (workflow_dispatch of publish.yml), then the v0.1.3 tag on the owner's word,
    then install trial + installed_smoke.py (TK-303)
  - Review DEC-16 and the 2026-11-20a rerank moves (accept or overturn)
  - Delete .context-engine/env-309641b (the 0.5 engine env) once nothing names it
- **start head:** 3a144e45aad6a24265fe298b897a434eb0147064

---

## 2026-11-20a · kind: close

- **tasks:** TK-185
- **rows:** TK-185 (closed, cd48245); TK-303 (new, NEXT); TK-304 (new, NEXT); TK-305 (new, LATER);
  TK-306 (new, LATER); TK-307 (new, LATER); TK-275 (promoted NOW); TK-146, TK-148, TK-288 (promoted
  NEXT); 13 perf/parked rows to SOMEDAY (0c76fd7); ASK-4..8 (new, raised); DEC-16 (PROVISIONAL)
- **receipts:**
  - guards: ten-phase gate at d2effc4 (2026-11-20): lean PASSED; conformance 1246 passed
    (250+249+249+249+249); tests 3962 passed (991+991+990+990); gate_status COVERED there; fuzz 5
    modules x 6 seeds green. After the records-only commits cd48245/0c76fd7 gate_status says NOT
    covered on the current tree (records stale the tiles). lint: clean
  - read: orient; task show TK-185; docs/runbooks/procedures.md (session start, intake, clean close,
    rerank, housekeeping); docs/charter.md
  - asked: ASK-4, ASK-5, ASK-6, ASK-7, ASK-8
  - housekeeping: hk run close: 0 writes, 0 op log lines
  - banner: kept 2026-11-16a
  - pushed: fae13a2: the 2026-11-16a close and banner records (with ebf71d8, f3e1037) pushed while
    no session was open; whether the gate ran first is not recorded
- **summary** (the owner digest):
  - TK-185 done: reads refuse an undeclared type/relation identically on Store and SetEngine
    (DEC-16, PROVISIONAL), C3/C4/C6 fixes, docs C1/C2/C8, docstrings, lint_gate prints type-check
    versions; 0.1.3 bumped (3b5ea66, 0d5bf34, d2effc4).
  - Independent verifier: SHIP WITH NOTES; equivalence probe 0 answer differences over 4 read paths;
    sabotages re-run red then green; residuals RISK-1..3 (D03 list-vs-check gap is TK-304).
  - Push of efc8de3..d2effc4 was refused by the harness permission classifier; nothing pushed, no
    tag. Release steps are TK-303 (NEXT).
  - Sprint rerank (verified by a second agent): NOW TK-275; NEXT TK-303, TK-304, TK-288, TK-146,
    TK-148; 10 perf rows + TK-277/243/255 to SOMEDAY (TK-277 owed piece split as TK-306). Agent
    calls, PROVISIONAL.
  - Owner questions raised: ASK-4 retire TK-264, ASK-5 retire TK-36, ASK-6 merge TK-67 into TK-277,
    ASK-7 retire TK-243, ASK-8 retire TK-255.
- **Still owed:**
  - Push master (efc8de3..HEAD) on the owner's go, after re-running the gate on the current tree,
    with a CI watcher (TK-303)
  - Publish dry run, then the v0.1.3 tag on the owner's word, then the install trial +
    installed_smoke.py (TK-303)
  - Answers to ASK-4..8; review DEC-16 and the rerank moves (accept or overturn)
  - Delete .context-engine/env-309641b (the 0.5 engine env) once nothing names it
- **start head:** fae13a2656170ad8b1936edea0256f49f0117409

---

## 2026-11-16a · kind: close

- **rows:** DEC-13..15 (ACCEPTED by decision accept --owners, the 0.6 upgrade step); no board item
  (the work is context-engine CE-235)
- **receipts:**
  - guards: lean PASSED (holes=0, audits=745, pinned=745) on this tree; conf-tile 1-5/5 (249 passed
    each) and tests-tile 1-4/4 (961, 960, 960, 960 passed) cover it (gate_status.py: the ten-phase
    gate is COVERED); lint clean
  - read: orient; CLAUDE.md (Start here, Gate, record engine, Running things); HANDOFF.md; kit
    README § Upgrade
  - housekeeping: hk run close: 0 writes, 0 op log lines
  - banner: set
  - pushed: ebfe7d2: the 2026-11-04a record commits, pushed 2026-11-05 with no session open; whether
    the gate ran first is not recorded (gate_status shows the tiles green on 2026-11-04)
- **summary** (the owner digest):
  - Engine upgraded 309641b -> 989982a (framework 0.5 -> 0.6) per kit README § Upgrade: contract,
    kit block, runbooks, ACCEPTED enum, Unverified hazards route; the owner's DEC-13..15 marked
    ACCEPTED (ebf71d8).
  - README cites no record id and is listed under [guards] reader_docs, so G-D13 guards it
    (f3e1037), for context-engine CE-235.
  - Sabotage: TK-120 put back in README.md prose -> G-D13 red, restored -> clean.
  - Banner cut to its durable lines, as the 0.6 engine requires (board and push lines are orient's
    now); this stales the t2c tiles, re-run after the close.
  - Old engine env kept at .context-engine/env-309641b (gitignored) for the owner to delete.
- **Still owed:**
  - Push master (ebf71d8, f3e1037 and records), on the owner's go, with a CI watcher
  - Delete .context-engine/env-309641b (the 0.5 engine env) once nothing names it
- **start head:** ebfe7d2b23aacd95841c9d27678a4ef35a46fad4

---

## 2026-11-04a · kind: close

- **rows:** TK-301 (filed LATER); TK-302 (filed SOMEDAY)
- **receipts:**
  - guards: gate_status.py: VERDICT: the ten-phase gate is COVERED on this tree (lean PASSED holes=0
    audits=745; conf-tile 1-5/5 PASSED 1246 collected; tests-tile 1-4/4 PASSED 3841 collected,
    961+960+960+960 passed); context-engine lint: clean
  - read: orient; CLAUDE.md; docs/runbooks/procedures.md (Session start, Intake, Clean close,
    Housekeeping); context.toml
- **summary** (the owner digest):
  - ce-cutover is merged and on origin/master (3e63fd7, pushed 2026-11-04 18:55 by the
    context-engine CE-167 session with no zanzibar session open; gate_status COVERED on 3e63fd7
    first, CI green, no tag); worktree zanzibar-ce-cutover and branch ce-cutover removed, backup
    kept.
  - Owner answers recorded verbatim from context-engine 2026-11-04a: DEC-13 coordinator rule
    (ASK-32), DEC-14 CI engine lint job (ASK-30), DEC-15 charter goals and stories eventually
    (ASK-31).
  - CLAUDE.md § Delegation now points at the contract coordinator rule (0fd366a).
  - New: TK-301 (LATER) engine-install-and-lint job in gate.yml; TK-302 (SOMEDAY) charter in owner
    words, survey goals G-1..G-4 as labelled agent drafts.
  - DEC-10..12 superseded by DEC-13..15: record new stamped and committed bodies citing
    context-engine ids bare, which lint G-D3 fails (engine finding: record new does not lint before
    its commit).
  - Commits stay local (not pushed). NEXT is empty: a rerank is due.
- **Still owed:**
  - push of the 2026-11-04a record commits: owner word needed
  - rerank: NEXT is empty
- **start head:** 3e63fd73e6d0e52f4f780b5899d3f18e469ced9a

---

## 2026-11-03a · kind: close

- **rows:** TK-1..TK-300, ASK-1..ASK-3 (imported from task.py); DEC-1..DEC-9 (imported)
- **receipts:**
  - guards: verify.sh not run at close: it runs on the closed tree next (CLAUDE.md: records first,
    then the gate); context-engine lint clean; the touched test modules 314 passed
  - read: zanzibar CLAUDE.md, HANDOFF.md, docs/README.md, docs/architecture/decision-log.md;
    context-engine CE-167 surveys
- **summary** (the owner digest):
  - context-engine adopted on branch ce-cutover (engine 309641b): kit, CLAUDE.md, context.toml;
    nothing pushed, merged or tagged
  - the task.py board is engine records in tasks/ (TK185 is TK-185; other series TK-186..TK-300;
    ASK-1..3 kept); old ids are aliases; conservation PASS
  - scripts/task.py retired from the gate (verify.sh 4g); it refuses an engine tree; handoff_lint
    reads the engine's records
  - docs/architecture/decision-log.md imported as DEC-1..DEC-9, one per section (conservation PASS),
    FROZEN in place; the old session ledger FROZEN
  - HANDOFF archived to docs/archive/HANDOFF.md; the new note is the engine's shape
  - scripts/gate_status.py: context.toml and docs/ledger/ are prose to the tiles' code scope
- **Still owed:**
  - the owner's call on merging ce-cutover into master
  - the owner's go to push (the full gate first, then a CI watcher); no tag
  - the charter and criteria with the owner (both still the kit's templates)
- **start head:** e0b7a1b2e6e5c76d5b6fab5ac4e0ea87d173120f
