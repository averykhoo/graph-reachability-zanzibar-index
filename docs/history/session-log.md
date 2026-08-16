# session-log.md — the append-only root session ledger

**LIVING — append-only.** This file lives under `docs/history/` for filing reasons
only; it is *not* frozen provenance, and the frozen-banner rule does not apply to it
(`scripts/handoff_lint.py` excepts it by name). It is the root analogue of
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md), which keeps
the *formal* detail; a formal-heavy session writes the detail there and points at it
from here.

**The rules** (conventions are defined once in [`docs/README.md`](../README.md)):

* **Newest entry first.** One entry EVERY session, without exception — the board's
  `moved` column is only meaningful if every session leaves a dated trace.
* **Entry key: `## YYYY-MM-DD[letter] — <headline>`.** The letter disambiguates
  same-day sessions (`2026-08-16`, `2026-08-16b`, …). The key is a stable citation
  target: entries are **never retro-edited**. A later entry names what it refutes.
* **The headline is one line and feeds the banner** in [`HANDOFF.md`](../../HANDOFF.md)
  verbatim, so keep it under ~120 characters including the key.
* **`rows:`** names the [`HANDOFF.md`](../../HANDOFF.md) board ids the session touched.
* **`Still owed:`** closes every entry. If the session ran short of context and skipped
  a write-back step, list the skipped actions here *verbatim* — the next session
  executes them before its own work.
* Body length is up to the writer; no cap. Links are written relative to the repo
  root, so from this file they resolve against `../../`.

---

## 2026-08-16c — the handoff-system migration executed: HANDOFF.md is a board, the ledger and the lint ship

rows: HS-1, HS-2, HS-3 (new); every open item re-keyed onto the new board.

Executed [`docs/handoff-redesign-2026-08.md`](../handoff-redesign-2026-08.md) §9 steps
2–11 against the survey evidence in
[`handoff-migration-map-2026-08.md`](handoff-migration-map-2026-08.md). Step 1 was
already done; **step 12 (the `formal/HANDOFF.md` deep half) is deliberately NOT in this
session** and is seeded as board row `HS-3`.

**What the migration found that the design did not know.** Each is recorded where it was
fixed, not here; this list exists so the *class* of defect is visible.

1. **A guard that would have been deleted along with its only true statement.** Step 4
   moves four footguns from the board into `CLAUDE.md`, each verified present in its
   durable home first. Three were. The fourth was not: `docs/gate-runbook.md` stated
   `MAX_TESTS_XFAILED` as "**1**, not 0, today", while `formal/verify.sh` sets it to `0`
   and `tests/test_postgres_ha.py` has carried `NO XFAILS REMAIN (2026-07-27)` ever since
   that date — there is not one xfail marker left in `tests/`. The runbook had described a
   state that ended three weeks earlier, and the board's copy was the only correct one.
   Fixed in the runbook *before* the board's copy died. **This is the entire reason step 4
   is phrased as verify-then-delete.**
2. **Ten of fourteen demoted rows had non-self-sufficient pointers.** The design gives
   `LATER`/`HOLD`/`SOMEDAY` rows no item block, on the invariant that the pointer target
   carries the traps and the completion criterion. Audited row by row, it mostly did not:
   `SD-1`'s target never mentioned either scope rejection; `P12` pointed at the bug being
   predicted *about* rather than the probe; `P8`'s target said the witness was "designed"
   without recording the design. All ten targets were repaired in place before the rows
   were demoted. Demoting them as written would have deleted the items.
3. **A trap that cited a symbol which has never existed.** The board carried "⚠ do not
   extend `test_fixture_earns_its_place` corpus-wide" — there is no such test, and never
   has been; it was a paraphrase of a docstring sentence. An unenforceable trap. Re-anchored
   to the two real gates (`test_corpus_pair_coverage_does_not_regress`,
   `test_fga_corpus_feature_coverage_does_not_regress`) and promoted to a standing trap so
   the next one gets grepped before it is written down.
4. **`P7`'s entire cost analysis existed only in gitignored `.scratch/`.** Not in any
   clone, not recoverable by another session. Transcribed into `PROOF_STATUS.md` as a dated
   correction; also now a standing trap.
5. **Stale figures inside the block that boasts of removing figures.** The archived
   "What landed 2026-08-16" recorded "audits 520 → **573**, anchors 471 → **497**". The
   machine-checked block generated in that same commit says **581** and **524**. `ZT-P3-5`,
   three lines below a banner congratulating itself for carrying no figures. Recorded as a
   correction on archiving; not carried forward.
6. **The severity-sign rule had no runbook home.** The single most transferable output of
   the RC1/RC2 arc ("probing only the positive direction mis-classifies severity by one
   sign") survived only in prose that was about to be archived. Lifted into
   [`sabotage-procedure.md`](../sabotage-procedure.md) *before* the archiving, along with
   six other method lessons — three of which were likewise homeless.
7. **My own new lint check failed by passing.** `check_frozen_banners` first tested
   `'LIVING' in head` as a plain substring, which every frozen archive satisfied via its
   prose "provenance, not a **living** document". It reported clean on exactly the files it
   was written to police, hiding six real violations; anchoring the match to the bold
   declaration form took the count from 8 to 15. Caught only because the house procedure
   says to sabotage a check before believing it. See `scripts/handoff_lint.py`'s docstring
   for the literal output of all six sabotages.
8. Two smaller ones: the migration map's line coordinates had drifted +7 (the board item
   that *ordered* this migration was added after the survey ran, so map §A carries no
   disposition for it — blocks were addressed by first line, never by the map's numbers);
   and `handoff-status-2026-08.md` already had a `## Retired 2026-08-16` section, so the
   design's "the existing section is the unlettered first batch" was false. The new section
   is keyed `2026-08-16b` rather than retro-editing an archive heading.

**Verification.** `python -m formal.conformance.doc_counts --check` green after every step
from 3 on. All ten `verify.sh` phases PASSED, exit codes captured directly rather than
through a pipe. `scripts/handoff_lint.py` green. `HANDOFF.md` went **986 → 202 lines**.

**The migration was then audited for loss, and the audit found real gaps.** A line-level
survival check over the pre-migration file confirmed the archived zones were faithful —
the only archived lines missing anywhere are exactly the ten that step 6 deleted as
verified duplicates. But line-identity says nothing about the *condensed* zones, where
content was rewritten rather than copied, so those were audited claim-by-claim against the
current tree. What that turned up, all now repaired:

* **Leg 7 step 5 was left unranked.** The scope doc calls it "the deepest single change";
  the new board's chain went `P3` → `P4` → `P5` and named step 5 nowhere. In a file whose
  charter is "the only file that ranks open items", that is the worst class of loss — the
  work is still described, but nothing points at it. Now board row **`P14`**.
* **Two facts existed nowhere afterwards**: the `RestrictBase` occurrence correction
  (19, not the 18 still recorded in a frozen 2026-08-10 block — and it is one of the two
  modules holding the CONSUMED sites `P7` must size), and the note that this machine's
  PostgreSQL cluster is stopped-but-RETAINED, so `start` is seconds rather than a cold
  `initdb`. Restored to `PROOF_STATUS.md` and `gate-runbook.md` respectively.
* **Two board pointers were simply wrong**: `DW-1` cited `CORRESPONDENCE.md` §2, which is
  the set-engine model and contains none of it; `HS-3` cited the design's §7 for a "step
  12" that is numbered in §9.
* **`docs/README.md`'s own citation rule cited a line number that had already drifted** —
  in the very paragraph explaining that a line-number citation is wrong the day the file is
  edited. It now cites by section, and says so.
* **Three items kept their warning but lost its reason**: the fixture-triple trap lost the
  exemption-list/failed-twice rationale and kept only a cost argument (so anyone who
  accepted the cost objection was no longer warned off the bad fix); `SD-1` lost the
  corpus measurement that made its deferral evidence-backed rather than assumed (48 schema
  files, 22 compile, 0 rejections — so a future session could re-file work already done and
  retired); and the declined store-level write quota had no entry in
  `perf-next-round.md`'s dead-end list, which is exactly where row `R6` sends a perf
  session.
* **Renaming "Working rhythm" to "Rhythm" dangled two code comments** that cite the section
  by name. The rule *number* `3b` was deliberately kept byte-stable for them; the section
  name was not. Both comments repointed.

The lesson worth carrying: **condensing is where content dies, and a line-diff cannot see
it.** Verbatim archiving verified itself trivially; every real loss was in a zone that had
been rewritten in good faith.

**Method note.** The recon ran as read-only agent fan-outs rather than being read into one
context. Two agents disagreed about whether `docs/design/` exists; both were checked by hand
before either was believed, and the one with the confident negative was wrong. Per
[`docs/subagent-fanout-runbook.md`](../subagent-fanout-runbook.md), a fan-out discovers
candidates and does not adjudicate them.

Still owed: nothing skipped. `HS-1` (wire the lint into `verify.sh`) and `HS-3` (the
`formal/HANDOFF.md` deep half, redesign step 12) are seeded board rows, not omissions.

---

## 2026-08-16b — perf round 6 opened (18 unmeasured candidates); the handoff-system redesign designed and approved

rows: R6 (opened).

Filed [`docs/perf-round6-audit-2026-08.md`](../perf-round6-audit-2026-08.md): a 24-agent
two-phase audit of both backends, 18 findings each adversarially verified against the
code, 0 refuted, plus 16 unverified lower-ranked leads. **Nothing landed and nothing is
measured** — per the reopening rule in
[`docs/perf-next-round.md`](../perf-next-round.md) every item still owes a motivating
measurement, and round 5 declined two plausible candidates on a fresh profile. One fix
sketch was refuted by counterexample while its finding stood (R6-1: the naive shared memo
is a correctness bug).

Designed [`docs/handoff-redesign-2026-08.md`](../handoff-redesign-2026-08.md) and had it
reviewed by three adversarial critics, then approved by the user (its §11 records the
decisions). The survey evidence was persisted first, as
[`handoff-migration-map-2026-08.md`](handoff-migration-map-2026-08.md) — migration step 1.

Still owed: execute §9 steps 2–11 (done in `2026-08-16c`); step 12 remains.

---

## 2026-08-16 — leg 7 step 4c-i landed: leaf-provenance rules, zero recompile cone; ttuStarFree (iv) unblocked

rows: P3, P6, P7.

Formal session — **the detail is in
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-08-16`**, which is the authority for this entry. In short: the leaf-provenance rule
layer landed with a measured zero recompile cone; the 4c-pre allocation model was refuted
three more times before anything was built on it, once by an instrument that was itself
blind; and `ttuStarFree` part (iv)'s standing blocking decidability question is answered
NO-BLOCK, machine-checked.

Still owed: leg 7 steps 4c-ii + 7 (must co-land), 4b, 5, 6; `ttuStarFree` parts (ii) and
(iii), and part (iv)'s remaining effort now that it is unblocked.
