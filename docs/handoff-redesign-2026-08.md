# The handoff system redesign (2026-08-16) — DESIGN v2, not yet executed

> **Status: DRAFT v2 for user review.** v1 was reviewed by three adversarial
> critics (cold-start Sonnet simulation, rot audit, migration-risk grep of the
> actual repo); their surviving findings are folded in and §10 records what
> changed. Nothing in HANDOFF.md or the satellites has been migrated yet.
> When the migration completes, retire this file verbatim to
> `docs/history/handoff-redesign-2026-08.md`; `docs/README.md` (created by the
> migration) carries the durable rules from then on.

The primary reader of this system is a Claude Code session (Fable, Opus, or
Sonnet) starting cold. Every choice optimizes for that reader: minimal context
cost at session start, unambiguous liveness of every statement, grep-able
stable keys, bounded signals, pointers instead of copies.

## 1. Diagnosis (measured 2026-08-16, block-by-block survey)

* `HANDOFF.md` is **979 lines** and still growing (+13 during the redesign
  discussion itself). The sum of what needs to stay is **~186 lines**.
* **The growth mechanism is append-layering**: updates arrive as new dated
  layers instead of edits in place, so the same fact is stated 3–4 times at
  different ages (the leg-7 landing criterion 4×, the archive pointer 9×).
* **~250 lines are post-archival residue** — items pointing at their own
  archive copies, never removed.
* **Emphasis no longer ranks**: 19 `★`, 10 `★★`, 23 `⚠`, ~94 bold-ALL-CAPS —
  one marker per 6–7 lines.
* **Corrections to other docs are parked here** — and in every audited case
  the target doc already contains the correction, so the copy is pure
  independently-rotting duplication.
* `formal/HANDOFF.md`: same disease, 1005 lines — **its line 3 still claims
  "~250 lines top to bottom."** An unenforced size claim rots exactly like an
  unenforced count (`ZT-P3-5`).
* What already works (kept, promoted to rules): the sequential phase table
  (it IS the board); `PROOF_STATUS.md`'s append-ledger convention (dated
  newest-first, `YYYY-MM-DD[letter]` stable keys, never retro-edited,
  supersession marked in the mutable file); frozen banners +
  corrections-on-archiving; retire-verbatim with self-declared destination;
  live figures in one generated place.

## 2. Design principles

1. **One home per statement.** Status/priority → board row. Session narrative
   → ledger. Method lesson → its runbook. Correction → the doc it corrects.
   Decision → decision log. Plan → its scope doc. Operational/machine state →
   gate runbook. Everything else is a pointer.
2. **Boards replace; ledgers accrete.** Board files are rewritten in place —
   no dated layers, no strikethrough graveyards. Ledgers are append-only,
   never retro-edited; a later entry names what it refutes.
3. **Liveness is declared, three-valued.** LIVING (maintained), FROZEN
   (visible banner, provenance only), or **ACTIVE-PLAN** (a scope/plan doc
   being executed: body is provenance, corrections appended dated at top,
   live until its board rows close, then frozen). The third state exists
   because live scope docs sit in `formal/history/` today and moving them
   would break links — the state is declared in the doc header instead.
4. **Signals rank only if bounded.** Priority is a closed vocabulary with
   capacity rules, not a glyph anyone can add for free.
5. **Stable keys, never positions.** Ledger entries by date(+letter), code by
   `file::symbol`, items by id. **Ids are carried forward forever and never
   reused** — B1, P3, ZT-P3-5, R6-4 are cited from append-only ledgers, frozen
   archives, and test docstrings, so the board must keep them.
6. **Don't state a number prose can't enforce.** Every capacity/ceiling in
   this design is either checked by the lint (§8) or deliberately unnumbered.
7. **Reuse existing conventions.** Everything here is promoted from something
   this repo already runs; the redesign standardizes.

## 3. The target `HANDOFF.md` (ceiling enforced by lint from day one)

```
# HANDOFF — the board                                          (~8 lines)
  Charter: the PRIORITY VIEW of every open item in the repo, formal included,
  and the only file that ranks them. Formal execution state lives in
  formal/HANDOFF.md — any formal item's read-first list starts there.
  A user-assigned task OVERRIDES the board: don't re-rank at session start;
  work it, re-rank once at write-back (NOW = what you'd recommend an
  unassigned session pick up). Read this file fully + CLAUDE.md, then only
  your item's read-first list. End of session: run the Rhythm protocol.

## Banner                                                      (~6 lines)
  🟢/🔴 gate state, as-of date, last session's one-line headline
  → ledger entry key. Nothing else — footguns are durable and live in
  CLAUDE.md (auto-loaded every session for free).

## Board — every open item is a row                            (~35 lines)
  pri: NOW(1) > NEXT(≤3) > LATER > HOLD(decision→ptr) > SOMEDAY — legend: docs/README.md
  | id | item (→ pointer) | pri | size | deps | moved |
  One row per open item, someday/latent included; nothing open lives
  elsewhere. deps cells name OPEN rows only — closing a row sweeps its id
  out of every deps cell (deps = "open blockers"; the ledger records the
  closure). moved = last date any session progressed or re-ranked the item
  (so an old date on NOW/NEXT genuinely means neglect). Ids carry forward;
  new items get fresh ids; ids are never reused.

## Item blocks — NOW and NEXT items only                       (~60 lines)
  Per item: what it is (1–2 lines), its ⚠ traps, and read-first: the exact
  docs/sections to load before starting. Blocks have REPLACE semantics:
  every session that touches the item rewrites its block in place —
  including the read-first list (a read-first citing a ledger entry rots as
  entries stack above it). Overflow: each NOW/NEXT item's scope doc carries
  a named "Traps" section; when a block outgrows a screenful, traps demote
  there and the block keeps the pointer. LATER/HOLD/SOMEDAY rows get NO
  block — their pointer target must be self-sufficient (§6 invariant).

## Standing traps                                              (~12 lines)
  Cross-item ⚠ lines only, one line + pointer each.

## Where things live                                           (~22 lines)
  The routing table with a "when to read" column, including "never (frozen)".

## Rhythm                                                      (~12 lines)
  The write-back protocol (§5) — the only part CLAUDE.md doesn't cover.
```

## 4. The signal system (replacing ★-inflation)

**Priority is a word in a column**, grep-able and unambiguous for any model:

| word | meaning | capacity |
|---|---|---|
| `NOW` | the single item an unassigned session should pick up | **exactly 1** |
| `NEXT` | the ≤3 items most likely to be picked next or run in parallel with NOW (by dependency, user flag, or ranking) | **≤ 3** |
| `LATER` | real, not queued; re-ranked when NOW/NEXT drain | unbounded |
| `HOLD` | deferred by an explicit recorded decision (→ pointer) | unbounded |
| `SOMEDAY` | revisit only on a concrete need | unbounded |

The capacities are the point: a bounded slot forces the ranking argument to
happen once, at write time, instead of every session re-deriving it.

**Emoji are category badges, never degree:**

| badge | meaning | budget |
|---|---|---|
| 🟢 / 🔴 | gate state, banner only | 1 |
| ⚠ | a trap: acting without reading this line produces WRONG work | ≤ 10 board-wide (lint) |
| 🧭 | waiting on a user decision (the line must name the decision) | as needed |

(v1 had a 🎯 badge on the NOW row; dropped — it duplicated `pri=NOW` and two
markers that must flip together will eventually contradict each other. The
word is authoritative and grep-able.)

**`★`/`★★` are retired from the two board files immediately** (lint-checked),
and from other living docs as they get touched; frozen archives keep theirs as
provenance, and the append-only ledgers keep old entries untouched but **new
ledger entries don't use ★** (the ledger is inside `formal/history/`, so the
rule is liveness-based, not path-based). Bold ALL-CAPS survives only inside ⚠
lines. **The ⚠ overflow at budget is a defined move, not an invention**: the
trap demotes to the owning item's scope-doc "Traps" section and the block
keeps a pointer — if that feels wrong, the trap was load-bearing enough to be
in CLAUDE.md.

## 5. The write-back protocol (end of every session; "Rhythm" in the board)

0. **Run `python scripts/handoff_lint.py`** (§8) before committing any board edit.
1. **Append one entry to `docs/history/session-log.md`** (NEW; root analogue
   of PROOF_STATUS): newest first,
   `## YYYY-MM-DD[letter] — <headline>`, a `rows:` line naming the board ids
   touched, body sized to taste (cold readers consume headlines + the top
   entry; length costs only the writer — no numeric cap, per principle 6, but
   the headline must fit the banner's one line), ending with `Still owed:`.
   Formal-heavy sessions keep writing detail to PROOF_STATUS; the root entry
   then just points at it — the root entry is written EVERY session.
2. **Rewrite the Banner**: gate state as observed, today's date, the new
   headline, → the entry key just created. (Ledger first — the key must exist
   before the banner cites it.)
3. **Edit the board in place**: flip pri, touch `moved` on every row worked
   (not only re-ranked), delete closed rows AND sweep their ids from deps
   cells, rewrite the item blocks of every touched NOW/NEXT item including
   read-first lists.
4. **File method lessons in their runbook now** (sabotage-procedure.md /
   subagent-fanout-runbook.md); the ledger entry summarizes + points.
5. **Fix wrong docs in place now**: living doc → edit; FROZEN or ACTIVE-PLAN
   → appended dated correction at top (the §11.5/§C.2 convention). HANDOFF
   never hosts a correction to another doc.
6. **New traps** → owning item's block, or CLAUDE.md if durable and repo-wide.

**Degraded-context path (mandatory floor):** steps 0–3 are the minimum viable
write-back. If context is short, list every skipped step-4/5/6 action
*verbatim* under `Still owed:` — the next session executes them before its own
work. A skip that leaves no trace is how append-layering started.

## 6. Satellite taxonomy and routing

| content type | home |
|---|---|
| priority/status of open items | `HANDOFF.md` board, only |
| session narrative | `docs/history/session-log.md` (root) / `formal/history/PROOF_STATUS.md` (formal detail) |
| formal execution state ("what is proved, what's the next lemma") | `formal/HANDOFF.md` (no priorities there) |
| method lessons | `docs/sabotage-procedure.md` (checks) / `docs/subagent-fanout-runbook.md` (fan-outs) |
| durable rules, footguns, env | `CLAUDE.md` |
| gate/operational/machine state | `docs/gate-runbook.md` |
| design decisions incl. post-spec user adjudications | `docs/architecture/decision-log.md` (charter widened) |
| divergences, latent gaps | `docs/spec-deviations.md` |
| plans/scopes for active legs | their scope doc (ACTIVE-PLAN header; corrections appended dated) |
| perf | `docs/perf-next-round.md` → active round doc → `docs/history/` |
| retired anything | `docs/history/` with the standard frozen banner |
| doc-system conventions | `docs/README.md` (NEW) |

**Invariant for row-only items:** a LATER/HOLD/SOMEDAY row's pointer target
must be self-sufficient — it carries the item's traps, completion criterion,
and method pointers. Migration step 7 verifies this per demoted row before the
notes column dies.

**`docs/README.md` (new, small):** liveness taxonomy (incl. ACTIVE-PLAN), the
frozen banner text, ledger entry format, citation-key rules, the signal legend
+ budgets, this routing table, and the freeze-at-landing rule: *a design/
investigation record gets its frozen banner the moment its change lands* —
part of the landing checklist, like the CORRESPONDENCE update for algorithm
changes. CLAUDE.md points at it; `formal/HANDOFF.md`'s house rules point at it
("shared doc conventions live in docs/README.md") while keeping their own
numbering byte-stable (house-rule numbers are cited from code comments and
living docs).

**The standard frozen banner** (visible prose, first lines, never an HTML
comment):

> **FROZEN <date> — provenance, not a living document.** Status lines below
> are as-of-then and several may now be false; live state: `HANDOFF.md` +
> the session ledger. Corrections are appended dated at the top, never
> edited into the body.

Current violations to sweep (from the survey): `docs/history/perf-round3/4/5`
(banner is an invisible HTML comment; round 3's visible body still says "All
work uncommitted pending review"), the four `docs/design/generator-coverage/`
files ("Nothing in the repo was modified" — the leg landed 2026-08-11),
`docs/architecture/p13-…`/`r4bf-…` (landed, unmarked), `PROOF_STATUS.md`'s
pre-ledger tail (answers a grep for "resume point" with July state).

## 7. The formal side — two halves

**Cheap half (same session as the root migration):** convert
`formal/HANDOFF.md`'s priorities/emphasis to the §4 vocabulary, delete the
"~250 lines" self-claim, add the README pointer to its house rules, keep
house-rule numbering byte-stable. Without this the two boards drift apart
again immediately.

**Deep half (its own session):** the "State of the world" accretion zone and
the ~40-row theorem table move out (table → `formal/ARCHITECTURE.md`, its
declared home; narrative already exists nearly verbatim in PROOF_STATUS), the
stale bottom "Status" section is rewritten from the current top blocks, and
the inbound descriptions repoint (`formal/README.md`, `ARCHITECTURE.md`,
`FINAL_REVIEW.md`, `CORRESPONDENCE.md` all describe formal/HANDOFF's old
shape). ⚠ Reflow risk: step 4e's prose scanner covers `formal/*.md`, and at
least one figure ("**19** corpora") escapes its regex today only via markdown
bold — any moved figure must carry its date + a pastness word **on the same
line**. PROOF_STATUS itself is untouched except the FROZEN banner over the
pre-ledger tail; the ledger convention is healthy.

## 8. The lint — lands WITH the migration, not after

The rot critique's central finding: every capacity in this design is prose
until enforced, the repo's own record shows deferred guards sit unbuilt for
weeks ("designed, NOT built" is a current board item), and the
habit-forming window is the first weeks. So a minimal **standalone**
`scripts/handoff_lint.py` (Python, per user 2026-08-16 — this is Windows)
ships in the migration session itself (it needs its own sabotage run per
house procedure, but NOT the full ten-phase gate — it is not wired into
`verify.sh` yet):

* line ceilings on `HANDOFF.md` and `formal/HANDOFF.md` — set at **landed
  size + ~10%**, recorded in the script with provenance (a guard that first
  fires on the fifth accretion layer teaches that layers are the convention);
* exactly one `| NOW |` row; `| NEXT |` count ≤ 3;
* zero `★` in the two board files;
* ⚠ count ≤ budget in the root board;
* `FROZEN` within the first 5 lines of every `docs/history/` +
  `formal/history/` file (ledgers and ACTIVE-PLAN docs excepted by name);
* ledger headline lines ≤ ~120 chars (they feed the banner).

Wiring it into `verify.sh` (plus the fancier checks: bold-caps-outside-⚠,
`moved`-vs-ledger cross-validation, newest-session-log ≥ newest-PROOF_STATUS)
is a separate board item, NEXT-seeded. Write-back step 0 runs the script
manually until then.

## 9. Migration plan (ordered; every prefix leaves the repo coherent)

Additive steps come before subtractive ones — v1 had the footguns deleted from
HANDOFF (step 6) before CLAUDE.md absorbed them (step 7), which broke the
any-prefix-coherent claim. **After every step from 3 on, run
`python -m formal.conformance.doc_counts --check`** — gate step 4e scans
`HANDOFF.md`, `CLAUDE.md`, `docs/*.md`, `docs/architecture/*.md`, and
`formal/*.md`, i.e. nearly everything this plan touches, and its date-context
window does not survive reflow (rule: any historical figure that moves gets
its date + a pastness word on the same line).

1. ✅ **DONE 2026-08-16 — the survey is persisted**:
   `docs/history/handoff-migration-map-2026-08.md` (frozen-on-write) carries
   the block-by-block dispositions (§A), the census/duplications (§B), the
   docs-tree inventory (§C), the formal-side inventory (§D), and all three
   critiques verbatim with their file:line grep evidence (§E — steps 8 and 12
   consume §E's inbound-reference lists directly instead of re-grepping).
2. **Create `docs/history/session-log.md`** (contract header + first entry
   covering 2026-08-16: perf round 6 opened, this redesign).
3. **Create `docs/README.md`** (§6 charter).
4. **Additive CLAUDE.md edit**: named footgun checklist — pipe-exit-code
   (verified NOT in CLAUDE.md today, only gate-runbook), `HYPOTHESIS_SEED`,
   `MAX_TESTS_XFAILED=0`, zero-headroom floors — each verified present in its
   destination before HANDOFF's copy dies; plus the README pointer line.
5. **Move the two orphaned designs**: claim-rot gate design →
   `formal/history/claim-rot-gate-design-2026-08-16.md`; bulk-merge sketch →
   `docs/architecture/bulk-merge-design.md` opening with "SKETCH, unbuilt —
   the fuller 2026-07-19 design is still owed" (so it cannot be misread as a
   landed design record) + an `overview.md` table row for it.
6. **Verify-then-delete the correction copies** (critique confirmed the
   targets: scope doc carries §11.3/§11.5–11.7; e-chain plan carries
   §C.1–C.6).
7. **Bulk-archive the narrative** → `handoff-status-2026-08.md` under
   `## Retired 2026-08-16 (second batch)` (the existing section is the
   unlettered first batch), with a "Corrections applied on archiving" section
   per the 2026-07 file's convention — including repointing that archive's own
   header line that says "Read HANDOFF.md's 'What landed 2026-08-11'", whose
   target moves into the archive itself. For every row demoted to
   LATER/HOLD/SOMEDAY, verify the pointer target carries the row's
   notes-cell traps + completion criterion (append dated if not).
8. **Rewrite `HANDOFF.md`** to the §3 shape. Ids carry forward (B1/B2,
   P3–P13, ZT-*, R6-*); deps cells reference open rows only; ACTIVE-PLAN
   headers added to the two live scope docs. Seed three new board rows with
   fresh ids: lint gate-wiring (`NEXT`), the `spec-deviations.md` split
   (`LATER` — scheduled by the user 2026-08-16), and the formal deep half,
   step 12 (`LATER`). Then the **inbound-reference
   sweep**: grep the tree for `HANDOFF` outside the history dirs and repoint
   citations whose target moved — `README.md` (two), `scripts/pg_local.sh`
   comment, `tests/test_ttu_tupleset_parent_types.py` (cites a HANDOFF *line
   number*), `tests/test_zt_p5_readjudication.py`, `tests/genswarm.py`,
   `tests/test_hypothesis.py` (cite retired plan items), using the
   archive-citation form `spec-deviations.md:2645` models. Comment/docstring
   edits only; run a tests tile afterward as a smoke check.
9. **Write + sabotage `scripts/handoff_lint.py`** (§8), record ceilings from
   the landed sizes (landed + ~10%, whatever landed turns out to be — the
   user deliberately did not pre-commit a number).
10. **Frozen-banner sweep** (§6 list) + split or banner the two
    mixed-liveness bench files (`PERF_ANALYSIS.md`'s living "Applied" log vs
    its frozen analysis; `STMT_BASELINE…` likewise).
11. **formal/HANDOFF.md cheap half** (§7).
12. **formal/HANDOFF.md deep half** (§7) — its own session, with the redirect
    sweep of `doc_counts.py:234` / `extractor.py:293` comments citing
    "working-rhythm 3b" and the four formal docs describing the old shape.

## 10. Critique record (what v2 changed)

Three adversarial critics reviewed v1 (2026-08-16; transcripts under
`wf_6d8a9bf1-f58`). Blockers fixed: root-vs-formal charter contradiction
(charter now scopes root to *priorities*, formal to execution detail);
dangling deps after row deletion (deps = open blockers, swept on closure);
banner missing from write-back (now step 2); all enforcement back-loaded
(lint now lands with the migration, ceilings set landed+10%); gate step 4e
unawareness (per-step `--check` runs + same-line date rule). Should-fixes
adopted: NEXT redefinition (v1's own seeds violated v1's definition);
user-assigned-task override; `moved` = progressed-or-re-ranked; replace
semantics for item blocks incl. read-first lists; defined ⚠ overflow; ledger
entry cap dropped (PROOF_STATUS entries measure 71–155 lines — the cap
contradicted the working convention it copied); id preservation; ACTIVE-PLAN
liveness state; migration-map persistence; archive-header repoint; formal
cheap-half pulled forward; ★ check scoped to the two boards (a path-based
repo-wide ban is unsatisfiable — CLAUDE.md itself carries a ★). Dropped: 🎯.

## 11. Decisions (user, 2026-08-16) — do not re-open during migration

1. **Priority seeds: APPROVED as proposed.** `NOW` = P3 (leg-7 4c-ii + step
   7). `NEXT` = ttuStarFree (ii), perf round-6 measurement pass, lint
   gate-wiring. P13 claim-rot gate → LATER.
2. **Ledger granularity: one root entry EVERY session** (the `moved`/ledger
   cross-check in §8's fuller guard depends on it).
3. **The lint lands during migration, in PYTHON** (`scripts/handoff_lint.py`
   — this machine is Windows; the user explicitly allowed the code).
4. **The `spec-deviations.md` split IS scheduled** — seeded as a `LATER`
   board row in step 8, not executed in this migration.
5. **The line ceiling: a max must exist, but its VALUE is not pre-committed.**
   The user was unconvinced by a fixed ~180; the mechanism stands as designed
   in §8 — ceiling = landed size + ~10%, recorded in the lint with
   provenance, raised only deliberately. If landed comes out at 250, the
   ceiling is ~275; the point is firing on the first appended layer, not the
   absolute number.
