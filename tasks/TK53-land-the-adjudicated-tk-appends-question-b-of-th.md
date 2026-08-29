---
id: TK53
title: land the adjudicated TK* appends — question (b) of the trial verdict is DECIDED (
brief: 15 appends remain; until they land, deleting tasks/ drops statements no living doc carries. Re-verify each row
pri: NEXT
size: M
deps: []
related: []
parent:
labels: []
source: board
source_hash: 045f47f3553e
created: 2026-08-29b
moved: 2026-08-29b
updated: 2026-08-29d
closed:
---

Question (b) of the trial verdict is decided and recorded in
[`tk-findings-adjudication-2026-08-29.md`](docs/history/tk-findings-adjudication-2026-08-29.md):
every open `TK*` id is bucketed. Five are written off against a named living carrier, three
were discharged in the deciding session (`TK48` corrected, `TK51` found already
implemented, `TK49` landed into `docs/README.md` §2), and the rest are **appends**: one
statement each, with a named destination doc, that exists nowhere but `tasks/`.

**Work the table in the adjudication file.** Each row names the destination and what is
missing there; the prose is written against the live doc when it lands, never copied from
the table. The heaviest concentration is `docs/perf-round6-audit-2026-08.md` (the appendix
leads and their cross-links) and `docs/latent-gaps.md` (the unmodelled-surface findings,
which belong in its "Latent, but owned by another doc" section).

## Traps

⚠ **Rows are not equal and some are already stale.** `TK45` is flagged in the file as a
probable CLOSE, not an append — both its residuals appear to have landed since it was
filed, exactly as `TK51`'s had. **Re-verify each row against the live tree before writing
it**; the underlying snapshot's own header says its citations were copied verbatim and
never re-checked, and `TK51` is the proof that at least one finding outlived its defect.

⚠ **`formal/CORRESPONDENCE.md` destinations are gate-anchored.** `verify.sh lean` resolves
every `file::symbol` anchor in that file, so an append naming a symbol that does not
resolve turns the gate red. Land those rows with a `lean` run, not on inspection.

## Read first

- board pointer: [adjudication](docs/history/tk-findings-adjudication-2026-08-29.md)) and the appends are the unlanded half. Each is a statement that exists only in `tasks/` and has a named destination in a living doc. ⚠ **This row is what makes DELETE lossless** — until it closes, deleting `tasks/` drops statements that no living doc carries. `TK52` closed on the decision; this carries the execution, so the decision is not a residual with no owner

 the adjudication file's table and its "Method" section (which records that
the adversarial pass overturned 6 of 11 proposed write-offs — the reason a single-pass
sweep of the remainder is not good enough), then
[`tasktool-findings-2026-08-29.md`](docs/history/tasktool-findings-2026-08-29.md) for the
finding text itself, then the destination doc.

## Log

### 2026-08-29b

Item block compressed to a pointer in the same session it was filed: the four traps and the disposition table live in docs/history/tk-findings-adjudication-2026-08-29.md, per docs/README.md sec 1 (one home per statement) and sec 4's defined trap-overflow move. HANDOFF.md was over its 260-line ceiling and its 10-badge trap budget on first write; both are clean now, and the ceiling was NOT raised.

Row and block rewritten at end of session 2026-08-29c to record progress (22 landed, 15 remain) and to carry the re-verify trap onto the board itself, since that trap earned its place: re-verification overturned rows in BOTH directions. Also re-flowed to keep HANDOFF.md at its 260-line ceiling without raising it.
