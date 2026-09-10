---
id: TK44
title: ~30% of the generator pair-cell space is unreached even at deep budget, with UNKNOWN residue
brief:
pri: HOLD
size: M
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-09-10
updated: 2026-09-10
closed:
---

Best measured union is **891/1275** pair cells (`docs/design/generator-coverage/README.md:566`, FROZEN): some of the residue is REJ-with-witness and legitimately unreachable, the rest is UNKNOWN with no witness explaining it. The LIVING carrier is [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md)`:482-487`, which uses it as a methodological caution: *"read a green gate as 'the instruments we have found nothing', never as 'there is nothing'."*

That is why this is `HOLD` and not a defect: it is **published honesty**, deliberately not rounded away, and the design doc's own position is that the number should be published rather than eliminated. What has never been decided is whether the UNKNOWN residue is worth attacking, or whether publishing it is the whole intended answer. That decision is the work.

## Traps

⚠ **The obvious "fix" is the forbidden one.** `tests/test_generator_coverage.py:257` explicitly argues AGAINST a hand-written `EXPECTED_UNREACHABLE` list — *"a future silent gap"* — and does not have one. Closing cells by exempting them is the failure mode, not the fix.

⚠ **Do not quote a percentage.** The two carriers say ~30% and "roughly a quarter" of the same measurement; the honest handle is the fraction at its source and the date. Re-measure before citing.

## Read first

- [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md)`:482-487` — the LIVING carrier and the methodological point
- [`docs/design/generator-coverage/README.md`](docs/design/generator-coverage/README.md)`:564-570` — §6, the measurement (FROZEN)
- `tests/test_generator_coverage.py` — the gate, and `:257`'s argument against an exemption list

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-29 (`J-27`, tier 4; sweep-j + sweep-k, two documents). Sweep-k guessed `GS-1`; `GS-1` is a closed gate-tree-id row and does not cover it. Both carriers re-read this pass; the LIVING one is docs/sabotage-procedure.md:482-487.

### 2026-09-10

LANDED 2026-09-10 (TK53 append) into `docs/sabotage-procedure.md`, section "What this procedure cannot do", after the residue paragraph. The row's own citation (:482-487) and the adjudication's (:524-526) are BOTH dead -- the paragraph is at :641-647 now.

The first pass called this ALREADY_CARRIED and the adversarial pass OVERTURNED it, and the overturn is the interesting part: the first pass reconstructed the wrong half of the finding from a frozen history file and matched it against a carrier for a statement the adjudication never claimed was missing.

The real half is a live ZT-P3-5 recurrence, and I verified all four figures first-hand rather than trusting the report: `tests/test_generator_coverage.py:68` says ~19% and `:428` says ~28% -- the SAME claim, identical wording ("unreached even at `deep`"), contradicting each other inside ONE module -- while `:1152` says ~30% and `docs/sabotage-procedure.md:643` says "roughly a quarter".

Nothing mechanical catches it, and this is worth carrying: `check_restated_counts` (TK58, landed 2026-09-08) is scoped to top-level `docs/` and `tasks/` markdown and to check/open-task/test counts, so a PERCENTAGE in a `.py` docstring is out of scope twice over. The landed text points at `tests/test_generator_coverage.py::test_report_cell_coverage` (:1149, run with -s) as the single live source.
