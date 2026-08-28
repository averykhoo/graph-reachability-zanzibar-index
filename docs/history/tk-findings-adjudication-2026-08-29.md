# `TK*` findings — the adjudication, 2026-08-29

> **FROZEN 2026-08-29 — a decision record, not a living document.** It says where each
> finding was sent, and why. Once a row's append has landed, its destination doc is the
> home for that statement and this file is only provenance. Corrections append dated at
> the top, never edited into the body.

## Correction, 2026-08-29b — four `APPEND` rows were wrong, and one refutation was wrong

Appended, not edited in. While landing the perf-appendix batch under `TK53`, each row was
re-verified against the live tree first, as this file's own traps require. **Four rows the
table below marks `APPEND` are in fact already carried and were closed instead:** `TK17`,
`TK23`, `TK24`, `TK27`. In every case the increment sits verbatim in the appendix lead's
own fix sketch — e.g. `A7`'s "sabotage-test the trusted entry before trusting it", and
`A11`'s `sorted(nodes)` ordering premise, which is today's code rather than a new
constraint.

⚠ **`TK27` is the sharper lesson: the adversarial pass got it wrong in the other
direction.** The challenge agent *refuted* the proposed write-off on the ground that the
lead's fix sketch misread its own material. Reading the sketch first-hand against
`index_v4/bulk_build.py:282-297` shows the sketch is right and the refutation was not. So
the 6-of-11 overturn rate recorded under "Method" is a measurement of *disagreement*, not
of correctness — the refutation pass is a filter that catches wrong write-offs and can also
manufacture wrong appends. **Neither pass substitutes for opening the file.**

That is the whole case for the re-verify trap, and it now has evidence on both sides.

---

**What this is.** [`TK52`](../../HANDOFF.md) split the `tasks/`-trial verdict into two
questions and required the irreversible one to be answered first:

> **(b)** If `tasks/` goes, where do the unranked `TK*` findings live?

[`tasktool-findings-2026-08-29.md`](tasktool-findings-2026-08-29.md) made DELETE
**non-destructive** by snapshotting the open findings verbatim. It did not decide which of
them deserve a board row, an append to a living doc, or an explicit write-off — and
`TK52`'s own trap names the failure mode: *"the third option — deleting without choosing —
is the one taken by default if this row is closed on the strength of the snapshot alone."*

**This file is that choice, made.** Every open `TK*` id appears below in exactly one
bucket. Nothing is left implicit.

⚠ **This decides (b) only.** Question (a) — *does the query beat the file* — is a separate
call and is **not** made here; the evidence for it is
[`tasktool-trial-protocol.md`](../tasktool-trial-protocol.md) §6, and the recommendation is
recorded in the session ledger. (b) was answered first precisely so (a) can be decided on
its merits by someone who is not also worried about losing findings.

## Method, and its one honest weakness

A nine-way subagent fan-out read each finding against the **live tree** and asked two
questions the entries habitually conflate: does a living doc carry the **subject**, or does
it carry the **finding** — i.e. would a future reader learn that work is outstanding? Every
proposed **write-off** was then handed to a second, independent agent told to *refute* it,
on the standing rule that an unnecessary append costs three sentences and a wrong write-off
is unrecoverable once the tree is gone.

**That challenge pass changed the answer for 6 of the 11 proposed write-offs** — `TK5`,
`TK7`, `TK15`, `TK23`, `TK24`, `TK27` — a 55% overturn rate on the only irreversible
verdict in the set. Recorded because it is the measurement that justifies the pass: a
single-pass adjudication would have written off six findings that had no living carrier.

⚠ **The weakness: the appends below are DECIDED, not LANDED.** Three landed in this
session (next section); the rest are owed and are carried by a board row, not by this file.
A decision recorded with no open carrier is exactly the defect `TK11` was filed for — a
residual declared at closure and never re-filed — so the carrier is the deliverable, and it
exists before this file was written, not after.

## Landed in this session — three, all verified first-hand

| id | what happened |
|---|---|
| `TK48` | **Fixed.** The perf audit's banner said *"ten recommended to land, five declined"*; its body carries **eleven** `MOTIVATED` rows and **four** `NOT MOTIVATED` ones (11 + 4 + 3 unreachable = its own "ALL EIGHTEEN"). It also said *"Nothing here is landed"*, false twice over (`R6-10` 2026-08-20b, `R6-6` 2026-08-24d). Corrected in one edit, and per the finding's own trap the banner now **carries no count at all** and points at the tables. Counted first-hand: `grep -c "NOT MOTIVATED"` returns **5** and is WRONG — line `:90` is prose, not a verdict row. |
| `TK51` | **Closed, not written off.** The finding asked for a dense-regime pass to make generator coverage sensitive to fail-open as well as fail-closed. It **is implemented**: `tests/test_generator_coverage.py:881` runs `_sweep(G.DENSE, DENSE_SUBSETS)` beside the sparse sweep at `:805`, and `:995-998` carries the sabotage assertion *"the DENSE regime detected nothing in the FAIL-OPEN direction"*. The finding was stale, and "stale" is a different disposition from "written off". |
| `TK49` | **Half landed** — see the next section. Its board defect is repaired; its adjudication remains owed. |

⚠ **`TK45` is in the same class as `TK51` and was NOT re-verified here.** Its own review
notes that both residuals *"have been substantially closed since the finding was filed,
which is itself the adjudication that was never recorded."* Treat it as a probable close,
not an append, and confirm before spending on it.

## The board pointed into the tree, and that is now fixed

`HANDOFF.md`'s `HS-5` row read *"count is method-sensitive, it lives in `TK49`, not here"*
— the board delegating its own substance, by id, to a tree that may be deleted tomorrow.
That is a **dangling referent on the control arm**, and it is the one defect in this whole
set that the trial's outcome could not make safe either way: DELETE breaks the pointer, and
KEEP leaves the board unable to state its own scope.

Repaired in this session by moving the enumerated list to `docs/README.md` §2, where the
rule it violates already lives, and repointing `HS-5` there. This is `CLAUDE.md`'s
*"a trap must cite a symbol that EXISTS"* one level up: it applies to board rows citing
task ids, and nothing was checking it.

## WRITE-OFF — five, each survived an adversarial refutation attempt

These have an adequate living carrier that states the work is outstanding. Losing the
`tasks/` entry loses nothing a reader would act on.

| id | carrier that already holds it |
|---|---|
| `TK12` | `docs/latent-gaps.md:176-184` — bullet one of *"Latent, but owned by another doc"*, whose preamble states the section exists to be a complete index of what is open. Carries the finding **and** its wrong-fix trap (`admitEdge` must not reject a present edge). |
| `TK16` | `formal/FINAL_REVIEW.md:181-188` — the honesty caveat verbatim, including that bundle inhabitation *is* kernel-checked and only the conjunction is empirical. |
| `TK18` | `docs/perf-round6-audit-2026-08.md` appendix (lead A2, verbatim) + `docs/perf-next-round.md:4-6`, which names the round-6 candidate list as the active worklist. |
| `TK21` | Same pair; the appendix's A5 entry carries every probe site the finding cites. |
| `TK51` | Superseded — implemented, see above. Listed here only so all ids are accounted for. |

## APPEND — the remaining findings, with their destinations

Each row is a statement that exists **only** in `tasks/` and belongs in a living doc.
Destination and the missing statement are recorded; the prose is written against the live
doc when it lands, not copied from here.

| id | destination | what is missing there |
|---|---|---|
| `TK2` | docs/architecture/decision-log.md, the freshness/`at_least` bullet, immediately after the "**Shape of the future work* | Only `tasks/` records that `ZT-P1-8b` is filed CLOSED while its filed scope is under-covered, so the ledger answers "is `at_least` done?" wrongly. The only other copy is `.scratch/tasktool/C... |
| `TK3` | formal/README.md, "The claim (what this does and does NOT prove)", into the "Residual unverified surface" sentence at | The verified fact that A1's own proposed resolution was never carried out: it says to "record in `formal/README.md`'s honesty section that the Python's fixpoint correctness rests on that alw... |
| `TK4` | docs/spec-deviations.md, a new dated `## 2026-08-29` section (append-only ledger, per its banner) | The whole gap statement. The spec mandates the hook and §10 (:324) lists lenient mode as a non-goal "hook only"; `docs/architecture/decision-log.md:195-200` likewise lists "lenient forall=>e... |
| `TK5` | docs/architecture/correctness.md` -- §4 "Known gaps (documented, not defended)", extending the existing "Multi-writer | (1) CARRIER DOES NOT SAY THE WORK IS OUTSTANDING. `docs/architecture/correctness.md:139-140` is the last sentence of a bullet in **§4, whose heading is literally "Known gaps (documented, not... |
| `TK6` | HANDOFF.md, the `P4` board row's scope pointer at :51 (widening an existing cell, not a new row) | The cross-link neither end names: that §8.2 item 2 constrains the currently-executing `P3`/`P4` leg, and no board row's scope pointer reaches §8.2 (`HANDOFF.md:51` points `P4` at §7, `:52` p... |
| `TK7` | docs/latent-gaps.md -- a new section under "## Open", placed immediately after "### The post-4c-ii headline statements | Only the ADJUDICATION: the downgrade from the tier-1 filing ("a soundness hole in a well-formedness condition") to HOLD on the ground that `LeafNode` does not exist in mainline Lean, plus th... |
| `TK8` | docs/latent-gaps.md, section "Latent, but owned by another doc" (currently docs/latent-gaps.md:171-197) | The inference nobody has written down: two named bugs inside ONE modeled-away region is an argument against the exclusion's justification, so what is owed is an ADJUDICATION (model it, or re... |
| `TK9` | docs/latent-gaps.md, section "Latent, but owned by another doc" (docs/latent-gaps.md:171-197) -- add: "* **The per-sub | Small but real: the explicit separation from the node-GC region (both are §7 unmodelled surfaces, filed apart on purpose so neither absorbs the other's argument), and the standing warning to... |
| `TK10` | docs/latent-gaps.md, section "Latent, but owned by another doc" (docs/latent-gaps.md:171-197) -- add: "* **Set-engine | Two things exist only in tasks/: (1) the framing that this is an INPUT-FILTER vacuity risk, one level up from the usual "green because it stopped looking" -- the instrument is not a check th... |
| `TK11` | docs/perf-round6-audit-2026-08.md, at the appendix lead whose fix sketch begins "Add a persistent decoded-snapshot cac | The CROSS-LINK, which neither end names: the perf-round-6 appendix lead proposing a persistent decoded-snapshot cache on `WildcardIndex` validated by `ResidueV1.version` would put every deri... |
| `TK13` | docs/latent-gaps.md, section "Latent, but owned by another doc" (after the derived-arm edge-multiplicity bullet at :17 | Two things exist nowhere else living. (1) The trap that `connectedstore/apply.py::advance_index`'s docstring is an ARGUMENT, not a proof -- apply.py:104 literally asserts "Batch size thus af... |
| `TK15` | formal/CORRESPONDENCE.md §7.2, appended to the existing n-ary-`Expr` entry (which runs :814-858, NOT the 807-851 both | Criteria 1 and 2 do NOT fire: formal/CORRESPONDENCE.md is LIVING (no frozen banner; gate-anchored by §9 anchor_check, updated through 2026-08-16b), is not the session log or trial protocol,... |
| `TK17` | docs/perf-round6-audit-2026-08.md`, section "Appendix -- the 16 UNVERIFIED lower-ranked leads" | The trap that a landing test must PIN the interner id-assignment order, not just the resulting memberships, because instance-local ids are observable state that `SetOps` bitmaps and every `(... |
| `TK19` | docs/perf-round6-audit-2026-08.md`, section "Appendix -- the 16 UNVERIFIED lower-ranked leads", same new non-quoted pa | The A3<->A14 cross-link, and it is genuinely absent from both ends: A3 targets `_check_derived`'s duplicate object resolve and a per-call memo keyed by `(row.id, row.version)`; A14 targets t... |
| `TK20` | TWO one-line additions, both non-quoted (`:32-36` pins the quoted blocks verbatim). (1) `docs/perf-round6-audit-2026-0 | The A4<->`R6-18` collision, added by the 2026-08-24b related-edge sweep. Verified absent at both ends, and it is the most consequential link in this batch because `R6-18` is not a lead: it i... |
| `TK22` | docs/perf-round6-audit-2026-08.md, Appendix, immediately under the heading `### [unverified · graph-write] Full-tier i | The paranoia-INSTRUMENT trap. The appendix lead argues only pre-commit correctness (':873' -- "before_commit flushes first, so column selects see the identical pending state"); it nowhere sa... |
| `TK23` | docs/perf-round6-audit-2026-08.md -- insert a dated `>` note BETWEEN :877 and :879, i.e. after the A7 entry's header l | Conditions 1-3 do pass for the reviewer: docs/perf-round6-audit-2026-08.md is LIVING (docs/perf-next-round.md:3-6 calls it "the active worklist ... 18 findings plus 16 unverified leads"), is... |
| `TK24` | PRIMARY: HANDOFF.md, `### R6` item block (currently :165-197) -- insert after the "Declined on an upper bound / Unreac | Verified first-hand: (a) the reviewer's cites are accurate -- the A8 lead is verbatim at docs/perf-round6-audit-2026-08.md:887-897, :893 carries all five sites and the "_nodes_by_ids (lines... |
| `TK25` | docs/perf-round6-audit-2026-08.md, in the `### R6-5` entry, as an unquoted dated note after the "Lean impact (verifier | A verified one-directional cross-link. The A9 lead header at :901 carries "· overlaps verified R6-5", but the `### R6-5` entry (:372-394) never names the appendix lead and never states the d... |
| `TK26` | docs/perf-round6-audit-2026-08.md, end of the Appendix intro paragraph (after line 801, which closes "Re-verify agains | Thin and partly derivable. The Lean obligation AND the preservation constraint are both already verbatim in the fix sketch at :921 -- "This changes the modeled cascade invalidation rule (spe... |
| `TK27` | docs/perf-round6-audit-2026-08.md -- insert immediately AFTER the A11 fix-sketch block (:933), before the next `###` h | 1) The reviewer's increment-(a) dismissal is backwards. The sketch at docs/perf-round6-audit-2026-08.md:933 says "over `sorted(nodes)` (same insertion order, so ids are assigned identically)... |
| `TK28` | docs/perf-next-round.md, section "Standing hygiene / gate notes", inside the existing **Measurement hygiene** bullet | REAL: "this is space, not time -- `benchmarks/profile_r6*` measures wall time and statement counts, so an RSS change needs its own instrument, decided before deciding whether to land it, or... |
| `TK29` | docs/perf-round6-audit-2026-08.md, section "Traps the numbers do not carry" (:146) | REAL: the entry contradicts the lead's own filing. A13 is filed "space / algorithm change: no" and its quoted evidence leans on `advance_index`'s docstring "proving" batch size affects no se... |
| `TK30` | docs/perf-round6-audit-2026-08.md, a dated `>` note directly under the A14 lead heading at :959 (the mechanism the doc | REAL and the strongest in this batch. Three things exist only in tasks/: (1) the adjudication that A14's `ResidueV1.version`-validated snapshot cache reintroduces precisely the cross-call ca... |
| `TK31` | docs/perf-round6-audit-2026-08.md, a dated `>` note directly under the A15 lead heading at :971 | REAL, and larger than the entry itself claims. A15's verbatim sketch ends "check CORRESPONDENCE.md anchors on `check`/`expand` still resolve since the public functions keep their names", and... |
| `TK32` | docs/perf-round6-audit-2026-08.md, a dated `>` note directly under the A16 lead heading at :983 | REAL: the sketch (:993) says "sentinel None/0 on release ... no semantic surface change", and the task entry observes that this converts a loud failure into a silent one -- a read of a relea... |
| `TK33` | docs/spec-deviations.md -- the 2026-07-29 store-level-write-quota entry, immediately after the "Two further options, r | The fail-open argument applied to the amortisation itself: a rebuild that can decline to apply pending deltas mid-stream is the same shape the closure fan-out cap exempts removals from (a ca... |
| `TK34` | docs/gate-runbook.md -- end of the "**Recommendation.**" paragraph that closes the perf-tripwire discussion (after :76 | The sabotage requirement: a canary is an assurance step and can fail by passing -- one that regenerates its baseline on every run alarms never -- so it must be sabotaged per docs/sabotage-pr... |
| `TK35` | docs/specs/wildcard-materialization-spec.md -- end of the conservative-analysis paragraph at :103-104 ("...a missed br | The cross-link to `BL-1`, the released-userset bridge leak (docs/spec-deviations.md:136, fixed 2026-08-21; filed-not-fixed at :188), as the live empirical instance of "a missed bridge is a c... |
| `TK36` | docs/specs/wildcard-materialization-spec.md -- appended to the bullet at :259 | The stated tension between the two adjacent spec lines: :258 makes "Never enumerate a marker into concretes" a read-path invariant, and an expansion layer is precisely that enumeration done... |
| `TK37` | docs/architecture/correctness.md -- end of the "Tokened reads against a stale evaluator catch up O(delta)" bullet (aft | The fail-closed requirement: a shared invalidation signal is a new way for a reader to believe it is fresh, so any design must state what happens when the signal is LOST and the answer must... |
| `TK38` | formal/CORRESPONDENCE.md -- immediately after the "pinning it needs the definition written down first" sentence at :57 | Two things. (1) The trap analysis: pinning a method-sensitive number from the same script that measures it yields a pin that agrees with itself by construction and proves only that the extra... |
| `TK39` | README.md, immediately after the `goals:` list (insert at README.md:405, before the mermaid block at :406), as a maint | The trap composition: any cross-namespace design must survive write-once static schemas (a new schema = a new store/index) AND must be applied to `tests/oracle.py` SEPARATELY, because the or... |
| `TK40` | docs/architecture/decision-log.md, in the graph-index/system "Out of scope (this round)" bullet at :190-193, extending | The completion criterion nobody has written: anything "shared" across stores has to say what it means for the per-store `TupleLogV1`, the watermark, and `_lock_store`'s per-store serializati... |
| `TK41` | docs/architecture/decision-log.md, appended to the existing lenient-reads material | The collision nobody has stated: reads are LENIENT by contract on both backends and in the oracle (CLAUDE.md:276; docs/architecture/overview.md:95 "Reads are lenient."), so a type checker th... |
| `TK42` | docs/architecture/decision-log.md, "Non-goals (documented hooks only)" section (:195-202), as its own short bullet sin | The architectural reason, and the conclusion it forces. The code rejects conditions mechanically but says nothing about WHY, and no doc says it. The tasks/ entry supplies it: conditions are... |
| `TK43` | docs/README.md, section 2 ("Liveness is declared, and it is three-valued"), appended after the "**Archive the status | Only the trap: these are author's-voice markers and must not be "resolved" by deleting them. That instruction exists in exactly one other place, `formal/history/handoff-status-2026-08-16.md:... |
| `TK44` | docs/sabotage-procedure.md, section 'What this procedure cannot do', immediately after the sentence at :524-526. | Two things exist nowhere else. (1) The undecided adjudication itself: whether the UNKNOWN residue is worth attacking or whether publishing it IS the whole answer. sabotage-procedure.md:518-5... |
| `TK45` | docs/README.md, section 2, appended to the 'Freeze at landing' paragraph. | Mostly NONE -- both residuals have been substantially closed since the finding was filed, which is itself the adjudication that was never recorded. Residual (a)'s two suggested fixes both la... |
| `TK48` | docs/perf-round6-audit-2026-08.md:2-5, replacing the banner's first two clauses in ONE edit, and carrying no numbers p | The board row `R6` now carries the CORRECTED split and both landed markers, so a board reader gets right figures -- but nothing anywhere says the audit doc's own banner is still wrong, and t... |
| `TK49` | docs/README.md, end of section 2, plus repointing HS-5's row in the same edit. | The board row knows work is owed but deliberately holds none of the substance: it reads 'count is method-sensitive, it lives in `TK49`, not here', i.e. it delegates by id to a tree that is b... |
| `TK50` | formal/CORRESPONDENCE.md, section 7.1, appended to the `_bumped` bullet (after :455). | Almost all of it is already carried. Section 7.1 (:436-455) states the channel, its drain sites, the zero-hit grep on the Lean side, and the consequence in the entry's own words; the T5 row... |

## Traps for whoever lands the appends

These are `TK53`'s traps; they live here rather than on the board because the board is at
its trap budget and this file is the row's pointer target (`docs/README.md` §4, the defined
overflow move).

⚠ **Rows are not equal, and some are already stale.** `TK45` is flagged above as a probable
CLOSE, not an append. **Re-verify every row against the live tree before writing it**: the
underlying snapshot's own header says its citations were copied character-for-character and
were *not* re-checked, and `TK51` is the proof that a finding can outlive its defect
entirely. A row that turns out to be landed gets closed with the evidence, not appended.

⚠ **`formal/CORRESPONDENCE.md` destinations are gate-anchored.** `verify.sh lean` resolves
every `file::symbol` anchor in that file, so an append naming a symbol that does not
resolve turns the gate red. Land those rows with a `lean` run, not on inspection.

⚠ **Do not batch these into one commit.** The destinations span living docs, an
append-only ledger, gate-anchored maps and code comments, and the rows have different
evidentiary weight. One commit per destination doc keeps a wrong append revertible without
taking the right ones with it.

⚠ **Do not copy the prose out of the table.** The "what is missing there" column is a
routing note written against the tree as it stood on 2026-08-29, not finished prose. Write
the sentence against the destination doc in that doc's voice, or the append reads as a
transplant and the next reader cannot tell what the doc actually claims.

## What is owed

The appends above are a real body of work and they are **not** discharged by this file.
They are carried by board row **`TK53`**, filed in the same session. When `TK53` closes,
this file becomes pure provenance.

**Do not read this file as the home for any statement in it.** Its rows are routing
instructions with a short shelf life; the destinations are the homes. A future reader who
finds a claim here and cannot find it at its destination has found an unlanded row of
`TK53`, not a fact.
