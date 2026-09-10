---
id: TK43
title: two README editorial TODOs: 'continue story another day' and the MAFSA word-count trick
brief:
pri: SOMEDAY
size: S
deps: []
related: []
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-09-10
updated: 2026-09-10
closed:
---

Two author's-voice editorial markers in `README.md`: `:142` *"todo: continue story another day"* (§*Overcomplicating things*) and `:150` *"todo: either write something or reference"* (the MAFSA word-count trick). Restated in the FROZEN `formal/history/handoff-status-2026-08-16.md:569-570`, which is why the sweep found them twice.

Author's-voice edits only — nobody else can write these, and nothing depends on them.

## Traps

⚠ **Do not "resolve" these by deleting the markers.** They mark deliberately unfinished prose in the author's own voice; a silent deletion is a worse outcome than an honest TODO, and this repo's whole doc discipline is that a residue is published rather than rounded away.

## Read first

- [`README.md`](../README.md)`:142` and `:150` — the two markers (the ROOT README; `tasks/README.md` is a different file and this link used to resolve to it)

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-28 (`J-1`+`J-2`+`J-30`, tier 4; sweep-j twice plus a self-dupe across two files); README.md:142 and :150 re-read this pass.

### 2026-09-10

LANDED 2026-09-10 (TK53 append) into `docs/README.md` sec 2, between the "Archive the status, keep the method." paragraph and "Freeze at landing."

Only the TRAP landed, not the two TODOs themselves -- the markers at root `README.md:142` and `:150` stand for unfinished narrative in the author's voice and nobody else can write the prose they stand for. Both markers verified live.

Adversarial pass caught a link hazard that this row had already been bitten by once: a bare `README.md` link from inside `docs/` resolves to the WRONG file. The landed text links `../README.md` explicitly and says why. It also frames the sabotage-procedure residue line as an ANALOGY rather than the governing rule -- that sentence is about coverage residue and a green gate, not prose markers, so presenting it as repo-wide discipline would have been scope inflation.
