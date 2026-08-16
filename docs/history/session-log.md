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

## 2026-08-16f — verify.sh leaves a trace now: gitignored run ledger + gate_status.py; the tee footgun sabotaged

rows: none (user-assigned tooling task; no board item was open for it).

Asked whether the gate produces logs, because the board's `Still owed:` line — "the nine
tile phases before push" — is carried by human memory across sessions. It did not: every
phase printed to stdout and exited, and `BUILD_LOG` is a `mktemp` deleted by the EXIT trap.

**The archaeology that looks like it should work does not, and that is worth recording
separately from the fix.** `.pytest_cache` was the only surviving artifact:
`v/cache/nodeids` had today's mtime and 1449 ids (941 `tests/` + 508 `formal/`) — one
collection, with no phase, no verdict and no tree attached — and `v/cache/lastfailed`
carried six failing node ids, also written today. The second one reads like evidence of a
red tree and is not: pytest only rewrites `lastfailed` when the failing SET changes and it
**retains entries for tests that did not re-run**, so it is cumulative, not a verdict.
Probed all six directly: **every one is `ERROR: not found`** — they name parametrizations
and tests that no longer exist (`test_features_are_unique_to_this_fixture` is the one
`verify.sh`'s own floor comment records as deleted on the 867→879 review). So: no evidence
of red, and no evidence of green either. That is exactly the gap.

**What landed.** Two artifacts per run under a gitignored `.gate-runs/`: the phase's full
output verbatim, and one appended row in `ledger.tsv` (started · duration · phase ·
`PASSED`/`FAILED`/`INCONSISTENT` · tree id · observed counts · log name). Phases call
`gate_fact` as they observe a count, so a FAILED row still carries what the run got to.
`scripts/gate_status.py` reads it back and answers the actual session-opening question —
which phases are green **on the tree in front of me** — with `--require-green` as a
mechanical push check. Runbook §4 documents it; `CLAUDE.md`'s gate bullet points at it.

**The tree id is one function with two callers, deliberately.** `verify.sh` shells out to
`gate_status.py --tree-id` rather than computing `<short HEAD>+<sha1 of porcelain+diff>`
in shell. A recorder and a reader that derive "same tree" differently would report a
freshness that never existed, and it would look right. Its limits are written down where
they can be read: it does not see untracked file contents, anything gitignored (a matching
tree id does **not** mean the same Lean build), or the environment.

**The sabotage found a defect rather than confirming a good check** — the first one did,
which is the whole argument for the procedure. Property: *a row saying PASSED means the
phase really passed, and a phase that fails still exits nonzero even though its output now
goes through `tee`.*

| sabotage | observed |
|---|---|
| control, clean `conf-tile:6/100` | `EXIT=0`; row `PASSED … collected=495 selected=5 conf_passed=5 conf_xfailed=0 conf_skipped=0 conf_floor=5` |
| `MIN_CONF_ALL=495` → `99999` | `EXIT=1` — the tee did not eat it — but **no ledger row at all** (before the fix; after it, `FAILED … rc=1`) |
| genuinely red pytest in a tile (temp failing test, `conf-tile:96/100`) | `1 failed, 4 passed in 0.95s` → `FAIL: conf (pytest rc=1)`, `EXIT=1`, row `FAILED … rc=1 collected=496 selected=5` |
| delete `GATE_REACHED_END=1` | `EXIT=1`, row `INCONSISTENT`, `FAIL: verify.sh is exiting 0 WITHOUT its final PASSED banner` |

Row 2 is the finding. The trap was written beside `BUILD_LOG=$(mktemp)`, ~230 lines below
the floor-consistency check it needed to cover, so a real gate failure produced a log file
and no row — the reader could only call it "incomplete" while the script knew it had
FAILED. The trap now precedes the first `exit` in the script body, `GATE_TREE` is snapshot
as soon as `$PY` resolves, and the comment at the trap says what the sabotage cost.

**Two things the design refuses on purpose.** The ledger never changes a verdict — every
write is best-effort and non-fatal, because a full disk should lose the record, not the
gate. The single exception runs the other way: `rc=0` without the final banner is recorded
`INCONSISTENT` and **forced nonzero**, since a gate that exits 0 without finishing is the
house failure mode, not a logging concern. And coverage is judged per-K (some single K
with all K tiles green), not against a hard-coded ten — the throttled-box recipe
`conf-tile:1/8 … 8/8` is just as complete, while tiles at mixed K provably leave holes.

Also worth knowing: `.gate-runs/` **must** stay gitignored, because the tree id hashes
`git status --porcelain` — a tracked ledger would change the tree id on every run and
every row would be stale on arrival. `gate_status.py` warns loudly if it ever sees that.

Still owed: unchanged from `2026-08-16d`/`e` — the nine tile phases before push. `lean`
re-run green here (it lints the board edits in this session). No Python behaviour changed;
the 2026-08-14 3-seed fuzz sweep still stands.

---

## 2026-08-16e — B1 was already closed and nobody noticed: both halves proved 2026-07-28/08-04, now verified

rows: B1 (closed; id stays retired).

Asked to look into `B1` — the `w3cJobValid_enumJob2D` star-freeness hole — and close it if
it was not done. It was done. The proof landed three weeks ago and the record never caught
up, so this session is verification and bookkeeping, not proof work.

**What the old verdict said.** Written 2026-07-27: "STILL OPEN, but RECLASSIFIED … needs a
decision, not a proof session", the decision being between a star-filter inside
`storedDirectSubjects` and a new fragment clause banning wildcard restrictions on derived
Direct arms. Its clause (ii) was `grep -rn "w3cJobValid_enumJob2D" formal/lean/` returns
**nothing** — the lemma does not exist, so no landed theorem depends on it".

**What is actually in the tree.** The E-chain plan §B took *both* options the next day, and
both landed. `storedDirectSubjects` half: the faithfulness star-filter, giving
`storedDirectSubjects_name_ne_star` with no fragment premise (leg 1, 2026-07-28).
`edgeHolders` half: `reachedByW3d2_Rnode_source_name_ne_star_d` under the new `W4Fragment`
clause `directArmsConcrete`, discharged at the call sites (leg 2, 2026-08-04). Both feed
`w3cJobValid_enumJob2D`, which exists at `CascadeStrataAssemble.lean:290`, is audited and
axiom-clean, and reaches the final theorems through `enumJobs2At_valid` (four call sites)
and `FullScope.lean`'s `W4Fragment.directArmsConcrete`. So both parts of clause (ii) are
false today.

**Sabotage rather than trusting the docstrings.** The star-filter was defeated in place
(`fun s => s.name != STAR` → `fun _ => true`) and `lake build` of
`ZanzibarProofs.GraphIndex.CascadeStrataEnum` went red at `CascadeStrataEnum.lean:634`, the
`simpa` closing `storedDirectSubjects_name_ne_star`. That half is held by the type checker.
Restored and re-verified green. **The check was worth running because a comment forty lines
away says a nearby filter "still COMPILES with the filter defeated"** — that is the
`freshDirectCands` presence diff, which genuinely is measurement-pinned, and reading the two
as one filter would have produced the opposite conclusion.

**The carry is unchanged and stays declared:** `directArmsConcrete` excludes a shape Python
admits (`define approver: [user, user:*] but not banned`). It is a vacuity boundary, not an
unsoundness one — on such a schema `W3cJobValid` fails for every enumerated job at the key,
so the operational chain has no cascade constructor there — and the clause is
machine-confirmed load-bearing by the leg-1 sweep.

**The transferable lesson, and it is the same one twice in two days.** A finding is closed
where it is RECORDED, not where it is fixed. `Audit.lean` had said "the
`storedDirectSubjects` half of the Board-B1 star-freeness hole is closed" since 2026-08-04
while the board block said "STILL OPEN"; earlier today the same class of gap appeared as an
id retired on one board and a finding left open on the other. Both are now closed, and both
boards say the same thing. Recorded in `formal/HANDOFF.md`'s `B1` block and as a dated note
on the E-chain plan, whose §B predicted this upgrade and was right.

Still owed: unchanged from `2026-08-16d` — the nine tile phases before push. `lean` was
re-run after the sabotage restore and is green. No Python behaviour changed.

---

## 2026-08-16d — the redesign closes: formal/HANDOFF.md 1010 to 471 (HS-3), the board lint is gate step 4f (HS-1)

rows: HS-1, HS-3 (both closed and retired); HS-2 promoted to NEXT; P15–P19 added; P3, P6,
R6 pointers untouched.

Two sessions' worth of items in one. Started as an audit of whether the executed handoff
system matches [`handoff-redesign-2026-08.md`](handoff-redesign-2026-08.md) — it mostly did
— and the three deltas found are fixed, then both remaining design steps were executed.

**The audit's findings, all repaired.** (1) The board charter claims to rank *every* open
item and did not: `FINAL_REVIEW.md` §4 ranked five items with no row. Verified against the
pre-migration file — they were never on the board, so this was inherited, not lost in the
migration; but the new charter's completeness claim made it false. Now rows `P15`–`P19`,
and §4 opens with the reverse map so the two cannot drift apart silently. `P17` is the one
worth noticing: bulk build/backfill is the DEFAULT `build_index` path, has no Lean
counterpart at all, and its only net is a Python-vs-Python identity gate. (2) The leg-7
scope doc still opened "SCOPE, DEFERRED" above its own ACTIVE-PLAN banner, so a cold reader
following `P3`'s read-first list met a false status first. (3) §7's cheap half had run
three-quarters — the `★` retirement landed, the emphasis conversion never did — and nothing
recorded the gap.

**`HS-3`, the deep half.** `formal/HANDOFF.md` 1010 → 471. Retired zones went to
[`formal/history/handoff-status-2026-08-16.md`](../../formal/history/handoff-status-2026-08-16.md)
**verbatim, not condensed** — the previous session's own audit found that condensing is
where content dies and a line-diff cannot see it, so this copied rather than summarised even
where a duplicate was verified to exist. The staged theorem ladder (35 rows, ~15 filenames
that appear in no other table) moved to `ARCHITECTURE.md`, its declared home. The retired
"Status" section was the actively wrong one: it said "the formal-verification arc is
finished" and "what remains is optional" while leg 7 was mid-flight at the top of the same
file, and carried a conformance count in prose that the same file's house rule 3 forbids.

**Eight dead inbound pointers, found by sweep and repointed.** Five live files cited a
`HANDOFF "The next task"` section that has not existed for some time — including four Lean
sources — and `RestrictBase.lean` cited a "HANDOFF Step A" that never survived at all. The
file's own line 4 pointed at that same dead section. `formal/README.md` advertised a theorem
table that was about to stop being there, which is the one case where the rot was two-sided.

**`HS-1`, the lint in the gate.** `verify.sh` lean-phase step **4f**, not an eleventh phase:
it is pure Python with no toolchain, exactly like 4d/4e, and a new phase would have meant
propagating a phase count through `CLAUDE.md`, the runbook and both boards. Three checks
added: bold-caps ratchets, root-ledger-not-behind-`PROOF_STATUS`, and `rows:`-cited ids
resolving to real board ids. Consequence now documented in the runbook beside the
`tests/`-reddens-`lean` footgun: **a HANDOFF-only edit reddens `lean`.**

**The bold-caps sabotage failed, and that was the whole value of running it.** The budgets
were set to 1 and 18; lowering one by a step left the check SILENT, because the true counts
after a paragraph-scoped trap exemption were 1 and 9. A budget above the measured value
guards nothing — the same defect as a floor with headroom. Both are now exact, the root
board's single offender was cleaned to a hard zero, and `formal/HANDOFF.md` keeps 9 as
declared debt in the `MAX_TESTS_XFAILED` idiom. Two exemptions were separately controlled:
stripping every trap badge took offenders 9 → 28 (so the exemption exempts something real,
not everything), and a real id in the bogus id's position kept `check_ledger_row_ids` silent
(so it fires on the id, not the line shape).

**Full `moved`-vs-ledger cross-validation was attempted and rejected**, not deferred. The
`2026-08-16c` entry covers ~20 rows with the prose clause "every open item re-keyed onto the
new board" rather than an id list, so the reverse direction false-fails most of the board on
the very commit that created the ledger. The safe direction shipped instead; the reasoning
is in the check's docstring so nobody re-files it.

**Method note.** The survey ran as four read-only agent fan-outs. Two disagreed about
whether the theorem table was still in `formal/HANDOFF.md`; I opened the file rather than
believing either, and the confident negative was wrong — it had inferred from the routing
table instead of reading. That is the second time in three sessions a fan-out's confident
negative has been wrong, which is now the strongest argument for the runbook's rule that a
fan-out discovers candidates and does not adjudicate them.

**Left deliberately unresolved:** the two boards disagree about `B1`. The root board retired
the id; `formal/HANDOFF.md` still verdicts the finding open, and `CascadeStrataAssemble.lean`
says only the `storedDirectSubjects` half is closed. Recorded in both places as a question
rather than adjudicated, because I could not verify the `edgeHolders` half either way.

Still owed: the full ten-phase `verify.sh` run before push — `lean` was re-run because step
4f is new, but the nine tile phases were not, and the gate contract is all ten before a push.
No Python behaviour changed (docs, one shell step, one lint script), so no fuzz sweep.

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
