# docs/README.md — the doc-system conventions

The primary reader of this repo's documentation is a Claude Code session starting
cold. Every convention here optimizes for that reader: minimal context cost at
session start, unambiguous liveness of every statement, grep-able stable keys,
bounded signals, pointers instead of copies.

This file is the durable contract for *how* docs work. It does not carry status.
Designed 2026-08-16 in [`history/handoff-redesign-2026-08.md`](history/handoff-redesign-2026-08.md),
which was executed in full and frozen the same day. Where that plan and this file disagree,
this file wins: it is the living contract, that is the plan which produced it.

## 1. One home per statement

The single rule the rest of this file elaborates: **every statement has exactly one
home, and everywhere else is a pointer.** A correction to another doc is filed *in
that doc*, never parked on the board. Duplication is not redundancy — the copies
rot independently, and the reader cannot tell which one is live.

| content type | home |
|---|---|
| priority/status of open items | [`HANDOFF.md`](../HANDOFF.md) board, only |
| session narrative | [`docs/history/session-log.md`](history/session-log.md) (root) / [`formal/history/PROOF_STATUS.md`](../formal/history/PROOF_STATUS.md) (formal detail) |
| formal execution state ("what is proved, what is the next lemma") | [`formal/HANDOFF.md`](../formal/HANDOFF.md) — no priorities there |
| method lessons | [`sabotage-procedure.md`](sabotage-procedure.md) (checks **and measurements**) / [`subagent-fanout-runbook.md`](subagent-fanout-runbook.md) (fan-outs) |
| durable rules, footguns, env | [`CLAUDE.md`](../CLAUDE.md) |
| gate/operational/machine state | [`gate-runbook.md`](gate-runbook.md) |
| design decisions, incl. post-spec user adjudications | [`architecture/decision-log.md`](architecture/decision-log.md) |
| divergences, latent gaps | [`spec-deviations.md`](spec-deviations.md) |
| plans/scopes for active legs | their scope doc (ACTIVE-PLAN header; corrections appended dated) |
| perf | [`perf-next-round.md`](perf-next-round.md) → the active round doc → `docs/history/` |
| retired anything | `docs/history/` with the frozen banner from §3 |
| doc-system conventions | this file |

**Live gate figures live in exactly one machine-checked place**:
[`formal/FINAL_REVIEW.md`](../formal/FINAL_REVIEW.md)'s generated counts block, gated by
`verify.sh` step 4e. Do not restate a count in prose anywhere — a quoted count is not
merely stale, it is unenforced. This file states no figures for that reason.

## 2. Liveness is declared, and it is three-valued

Every doc declares one of these in its first lines. A reader must never have to infer
whether a statement is still true.

| state | meaning | obligation |
|---|---|---|
| **LIVING** | maintained; every statement is claimed true today | fix in place when it goes wrong |
| **FROZEN** | provenance only; status lines are as-of-then | visible banner (§3); corrections appended dated at the top, never edited into the body |
| **ACTIVE-PLAN** | a scope/plan doc currently being executed | body is provenance; corrections appended dated at the top; live until its board rows close, then frozen |

ACTIVE-PLAN exists because live scope docs sit under `formal/history/` for filing
reasons and moving them would break inbound links. The state is declared in the header
instead of inferred from the path. The append-only ledgers
([`history/session-log.md`](history/session-log.md),
[`PROOF_STATUS.md`](../formal/history/PROOF_STATUS.md)) are LIVING despite their paths.

**Archive the status, keep the method.** When a leg lands, its status text retires to
`docs/history/` — but the *method lesson* it produced does not go with it. The lesson
belongs in a living doc (`sabotage-procedure.md`, `subagent-fanout-runbook.md`,
`CLAUDE.md`, or this file) where the next session will actually read it. Archiving a
lesson alongside the status is how a hard-won rule becomes invisible.

**Freeze at landing.** A design or investigation record gets its frozen banner **the
moment its change lands** — part of the landing checklist, exactly like updating
`formal/CORRESPONDENCE.md` for an algorithm change. A design doc that still says
"nothing in the repo was modified" months after the leg landed is the failure this rule
prevents.

## 3. The frozen banner

Visible prose, in the first lines, never an HTML comment — an invisible banner does not
warn anybody:

> **FROZEN &lt;date&gt; — provenance, not a living document.** Status lines below are
> as-of-then and several may now be false; live state: `HANDOFF.md` + the session
> ledger. Corrections are appended dated at the top, never edited into the body.

## 4. Signals rank only if they are bounded

**Priority is a word in a column** — grep-able, unambiguous, and capacity-bounded so the
ranking argument happens once at write time instead of being re-derived every session.

| word | meaning | capacity |
|---|---|---|
| `NOW` | the single item an unassigned session should pick up | **exactly 1** |
| `NEXT` | the items most likely to be picked next or run in parallel with `NOW` | **at most 3** |
| `LATER` | real, not queued; re-ranked when `NOW`/`NEXT` drain | unbounded |
| `HOLD` | deferred by an explicit recorded decision (→ pointer) | unbounded |
| `SOMEDAY` | revisit only on a concrete need | unbounded |

**Emoji are category badges, never degree:**

| badge | meaning | budget |
|---|---|---|
| 🟢 / 🔴 | gate state — banner only | 1 |
| ⚠ | a trap: acting without reading this line produces WRONG work | at most 10 board-wide |
| 🧭 | waiting on a user decision (the line must name the decision) | as needed |

`★` and `★★` are **retired** from the two board files ([`HANDOFF.md`](../HANDOFF.md) and
[`formal/HANDOFF.md`](../formal/HANDOFF.md)) and are removed from other living docs as
they get touched. Frozen archives keep theirs as provenance; the append-only ledgers keep
old entries untouched, but **new ledger entries do not use `★`**. Bold ALL-CAPS survives
only inside a ⚠ line.

**⚠ overflow is a defined move, not an invention.** At budget, the trap demotes to the
owning item's scope-doc "Traps" section and the board block keeps the pointer. If that
feels wrong, the trap was load-bearing enough to belong in `CLAUDE.md` — which is
auto-loaded every session, so it costs the reader nothing.

## 5. Stable keys, never positions

Ids and keys are cited from append-only ledgers, frozen archives, code comments and test
docstrings. They must survive a rewrite of the file they came from.

* **Board items → id** (`P3`, `B1`, `ZT-P3-5`, `R6`, `HS-1`). **Ids are carried forward
  forever and never reused**, including after the row closes.
* **Ledger entries → date key** (`2026-08-16b`), never a position in the file.
* **Code → `file::symbol`** (`Cascade.lean::GraphState.writeLoggedOne`), never a line
  number. `verify.sh lean` resolves every `file::symbol` anchor in
  `formal/CORRESPONDENCE.md`, so a rename fails the gate instead of rotting.
  **Outside `CORRESPONDENCE.md` nothing checks this — it is a convention, held by
  hand, and the 2026-08-19 sweep is what it costs to let it slip.** Three forms that
  *look* right and do not resolve, all found in living docs that day:
  * a bare method name (`processor.py::_reconcile_subject`) — anchors are
    `__qualname__`, so it is `::DeltaProcessor._reconcile_subject`;
  * a function LOCAL (`::WildcardIndex.check.row`) — `anchor_check.py` records only
    defs/classes plus class- and module-level assignments, deliberately. Name the
    enclosing function instead. Closures ARE valid (`::Oracle.check.ttu_leaf`);
  * a bare filename (`models.py:121`) — there are three `models.py`. Write the
    package (`index_v4/models.py`) whenever the file name is not unique.

  When the target is a comment, a branch, or a `dict` key rather than a symbol,
  **quote the code and name the symbol it sits in** — `extractor.py::_edge_projection`
  (`if "." in obj[2] …: return "P6"`), `corpus.py::SCHEMAS`'s `"residue_rich"` entry.
  A step with an in-code marker is cited by the marker (`_reconcile` step (2c)), and
  a numbered invariant by its number (`I1`, `I6`) — both travel with the code.
* **House rules → their number.** `formal/HANDOFF.md`'s house-rule numbering and this
  repo's working-rhythm numbering are cited from code; renumbering breaks those
  citations silently. Keep the numbers byte-stable.
* **Archived content → section title, never a line number.** The landed form is:

      `docs/history/handoff-status-2026-07.md` "Zero-trust review 2026-07-26"
      (archived from `HANDOFF.md` 2026-07-29) §P5

  as used in `docs/spec-deviations.md`'s "2026-07-26 — ZT-P5" entry and at
  `tests/test_generator_coverage.py:6`. A citation that names a line number in a living
  file is wrong the day the file is edited — this very sentence cited
  `docs/spec-deviations.md:2645` when it was written on 2026-08-16 and that line had
  already drifted to a blank one by the end of the same session.

## 6. Boards replace; ledgers accrete

**Board files are rewritten in place** — no dated layers, no strikethrough graveyards, no
"as of" stacking. When a fact changes, the old text is deleted, not annotated. Item
blocks have replace semantics: every session that touches an item rewrites its block
*including its read-first list*.

**Ledgers are append-only and never retro-edited.** A later entry names what it refutes.
Entry format is defined in [`history/session-log.md`](history/session-log.md)'s own
header; one root entry is written EVERY session.

This split is the whole cure for the disease that produced this redesign: updates that
arrive as new dated layers instead of edits in place, so the same fact ends up stated
three or four times at different ages and the reader cannot rank them.
