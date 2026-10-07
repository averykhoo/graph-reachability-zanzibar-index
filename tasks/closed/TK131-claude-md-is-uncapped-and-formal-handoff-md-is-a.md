---
id: TK131
title: CLAUDE.md is uncapped and formal/HANDOFF.md is at its line cap; add caps and prune
brief: CLAUDE.md has no size cap (~45 KB, +4 KB/week); formal/HANDOFF.md at 520/520 lines
pri: LATER
size: M
deps: []
related: []
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-10-07c
moved: 2026-10-07d
updated: 2026-10-07d
closed: 2026-10-07d
---

Item 4 of the 2026-10-07 cross-repo context audit. `CLAUDE.md` is uncapped (558 lines /
~45 KB, growing about 4 KB a week, measured 2026-10-07), and `formal/HANDOFF.md` sits at
exactly its 520-line cap. Add a `CLAUDE.md` byte cap (audio-workspace's `claudeMdShape` is the
model: a ceiling plus a per-table-row cap) and prune both.

## Traps

- (!) `CLAUDE.md` is auto-loaded every session, and pruning it moves rules. Each rule
  removed must land in its home doc (`docs/README.md` routing table) in the same change.

## Read first

- [`docs/context-audit-2026-10-07.md`](../docs/context-audit-2026-10-07.md) item 4 (measured 2026-10-07).

## Log

### 2026-10-07d

formal/HANDOFF.md half PRUNED (2026-10-07d, uncommitted): 520 lines/40412 B -> 241/19636 B. Moved VERBATIM to new FROZEN formal/history/handoff-retired-2026-10-07.md (366 lines): dated blocks 2026-08-15..2026-08-28c, Board B1/B2 + 2026-08-16 note, P14/option-(c) blocks, leg-7 landing note, T2a-carry/P4 notes. Replaced by short pointers + a 5-bullet standing-traps list citing gated homes (statement_pin.py::HEADLINE, CORRESPONDENCE.md checkPublic/graphRun rows and sec 7.2, Leaf.lean::isLeafPred). House rules untouched (cited by number). handoff_lint clean (12 checks); bold-caps offenders now 1 (line 52) vs MAX_BOLDCAPS 6 -> ratchet slack, owner of handoff_lint.py should lower to 1; MAX_LINES landed+10% rule gives 265. Still owed: the CLAUDE.md byte-cap half (other agent).

CLAUDE.md half LANDED (2026-10-07d, uncommitted): CLAUDE.md pruned 44925 B LF / 558 lines -> 31017 B LF / 387 lines (31404 B on disk, CRLF). Cut: case histories and "this said X until <date>" provenance, duplicate statements (pg_local recipe, golden rule, Delegation summary of the machine-wide file), module detail already in docs/architecture/overview.md. Every rule kept; "Who decides" byte-identical. Cap: scripts/handoff_lint.py::MAX_BYTES[CLAUDE.md] = 32500 (headroom 1483 B, less than the 1970 B footgun-1 case history the prune removed), per-file remedy text BYTE_CAP_REMEDY; per-row cap not ported (no table; reason in the constant comment). Rides check_ceilings = CHECKS[0], verify.sh lean step 4f. Pinned by tests/test_tk131_claude_md_cap.py (6 tests, mutation sweep M0-M6 in its docstring); tests/test_tk130_handoff_size_caps.py seed helpers now write a CLAUDE.md stub. Moved-text table with quoted homes: .scratch/hk-2026-10-07d/impl-tk131-claude.md (orchestrator: transcribe into the session-log entry). docs/README.md sec 4 + sec 8 row and docs/gate-runbook.md caps row updated. RED: formal/FINAL_REVIEW.md counts stale (+6 tests here) -- run doc_counts --generate. Next: close TK131 once committed with the gate green.

fix-hk review pass (2026-10-07d): formal/HANDOFF.md caps ratcheted to the prune: MAX_LINES 520 -> 265, new MAX_BYTES 21600 (+BYTE_CAP_REMEDY), MAX_BOLDCAPS 6 -> 1, and check_bold_caps is now red UNDER budget too (names the value). The live-CLAUDE.md headroom test was a gate hole (t2c excludes CLAUDE.md): moved to scripts/handoff_lint.py::MAX_BYTES_SLACK (CLAUDE.md 1900 B, checked in lean); test rewritten to temp roots. Survey in scripts/gate_status.py re-done: PYPI_README.md, CHANGELOG.md, formal/CORRESPONDENCE.md added to CODE_SCOPE_MD_KEEP (read live by test_tk122_release_metadata / test_claim_rot_gate), pinned by two new tests in tests/test_gate_status.py. Sweeps: S1-S6 red (tk131 docstring addendum), G1/G2 red (test_gate_status comment). FINAL_REVIEW counts regenerated (tests/ 1777). Next: gate, commit, close.

Done 2026-10-07d. CLAUDE.md 45.5 KB -> ~31.7 KB, byte-capped in handoff_lint.py::MAX_BYTES with a slack ratchet (tests/test_tk131_claude_md_cap.py); Who decides byte-identical. formal/HANDOFF.md 520 -> 241 lines, moved verbatim to formal/history/handoff-retired-2026-10-07.md; caps ratcheted (MAX_LINES 265, MAX_BYTES, MAX_BOLDCAPS 1). gate_status.py::CODE_SCOPE_MD_KEEP now includes CLAUDE.md (a test reads it). Evidence (agent reports, moved-text tables, sabotage sweeps): docs/history/context-caps-housekeeping-2026-10-07.md. Gated with the 2026-10-07d commit.
