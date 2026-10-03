---
id: TK110
title: census tests/ for drivers that absorb an admission refusal into a smaller compared store
brief: TK71 follow-up: formal/conformance absorbers pinned; tests/ has 17 files of refusal catches, unclassified
pri: LATER
size: M
deps: []
related: [TK71]
parent:
labels: []
source: hand
source_hash:
created: 2026-09-27b
moved: 2026-10-03c
updated: 2026-10-03c
closed:
---

## What it is

`TK71` (2026-09-27) found that three drivers in `formal/conformance/` ABSORBED an admission
refusal into a smaller compared store, and nothing counted how many. An over-reject there
made the gate test less and stay green: pre-fix, S1/S2/S4 left the remove gate green, and a
broad over-reject left the generated gate green on 38 of 40 seeds. All three now carry exact
pins. **`tests/` was not censused.** Do the same census there: classify every refusal catch
as (i) an expected-refusal test, (ii) a parity driver that asserts both backends refuse the
same write (safe), or (iii) an absorber that shrinks what is compared without counting. Pin
every (iii) exactly, the way `formal/conformance/test_conformance_remove.py::_assert_poisoned`
does.

## Read first

- [`docs/tk71-admission-survival-2026-09-27.md`](../docs/tk71-admission-survival-2026-09-27.md)
  sections 2-4: the census shape, the measurement and the sabotage table to copy.
- `tests/test_hypothesis.py` and 16 more files: the starting surface (MEASURED 2026-09-27, `grep -rc "except AdmissionRejected\|except
  ValueError\|except (ValueError" --include=*.py tests`): 17 files. Largest:
  `tests/test_hypothesis.py` 6, `tests/test_admission_rejected.py` 5, `tests/test_matrix.py` 4,
  `tests/test_wildcard_property.py` 3, `tests/test_setengine_storage.py` 3, `tests/parity.py` 2.

## Traps

- (!) A bare `except ValueError` also swallows a non-refusal engine bug (S4 in the map doc).
  Narrow it to `AdmissionRejected` before pinning the count, or the count includes bugs.
- (!) The measure must re-use each module's OWN generators (seeded), or it measures a
  different op stream from the one the gate drives.
- (!) Sabotage each pin with a PRE-FIX contrast (the `HEAD` copy of the module as a temporary
  probe): a pin whose pre-fix module also goes red was not the gap.

## Log

### 2026-10-03c

Triage 2026-10-03c: skeptic verdict WEAKENED, near-refuted (AGENT-REPORTED). The `TK71` premise does not carry over: the `tests/` parity drivers require all backends to accept or reject alike, and three sabotages (`TK71`'s S1, a shared wildcard-userset over-reject, a shared same-type-userset over-reject) all went RED. Keep at LATER as hygiene: narrowing bare `except ValueError` to `AdmissionRejected` in the absorbers still stops them swallowing non-refusal engine bugs. Site list and reasoning: `docs/promote-next-triage-2026-10-03.md` sec 4.
