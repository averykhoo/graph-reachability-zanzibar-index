---
id: TK71
title: test_conformance_enum.py asserts no admission-SURVIVAL floor, only the combinatorial count
brief: split from TK69; its original 4d framing is REFUTED twice -- read the traps before sizing
pri: NOW
size: S
deps: []
related: []
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-16b
moved: 2026-09-27
updated: 2026-09-27
closed:
---

## What it is

`formal/conformance/test_conformance_enum.py` enumerates every store up to a documented
bound over six shapes and asserts spec == oracle == set engine on each. It asserts the
COMBINATORIAL store count, but **nothing asserts how many of those stores SURVIVE
ADMISSION**. If a future change narrows admission too far, the surviving space shrinks and
the module keeps passing on whatever is left.

Filed 2026-09-16b, split off `TK69`. Original form (audit item 4d, 2026-09-15): "an
admission OVER-REJECT stays green here".

## (!) Traps

- **(!) THE ORIGINAL FRAMING IS WRONG IN TWO PLACES AND THE ROW MUST NOT INHERIT IT**
  (both REFUTED first-hand 2026-09-16b while closing `TK69`):
  * *"a rejection silently shrinks the enumerated space"* -- it does not; a refusal RAISES
    out of the backend call. The vacuity risk is a change that makes stores UNREACHABLE,
    not one that makes them silently dropped.
  * *"so couple it to the `TK69` fix"* -- it could never have gated `TK69`. `::_tuple_space`
    emits `"*"` only as a SUBJECT name and draws every object name from `_POOL`, so the
    module **cannot enumerate an object-wildcard write at all** and therefore cannot reach
    a `TK69`-class store however that fix went. A floor here advertised as the `TK69`
    over-reject guard would have been an assurance step aimed at a case it cannot see --
    the house failure mode. `TK69` was gated instead by a direct over-reject control
    (`tests/test_reg_tk69_entity_crossing.py::test_ctrl_no_entity_means_no_refusal`).
- **(!) So state what the floor DOES guard, in its own comment.** It is a BROAD admission
  regression inside a space that contains no object-wildcard write. That is worth having
  and it is not nothing -- it is just not what item 4d claimed.
- **(!) Sabotage it before believing it** (`docs/sabotage-procedure.md`), and record the
  literal output. A floor whose green has never been contradicted is not evidence. Note in
  advance: the narrowest plausible `TK69`-shaped over-reject leaves it GREEN by
  construction (see above), so do not use that as the sabotage -- use a broad one, and say
  in the comment which sabotage was used.
- Floors in this repo are set at the live measured count with ZERO headroom
  (`MIN_TESTS_ALL` / `MIN_CONF_ALL` are the precedent), so measure, do not estimate.

## Read first

- `formal/conformance/test_conformance_enum.py::_tuple_space` and `::_all_stores` -- the
  enumerator, and the reason an object-wildcard object name is not in its range.
- [`docs/tk69-admission-parity-2026-09-16.md`](../docs/tk69-admission-parity-2026-09-16.md)
  sec "What the reconciliation changed" item 2 -- where the two refutations above were made.
- `docs/adversarial-audit-2026-09-15.md` -- item 4d, the original claim, for provenance only.

## Log

### 2026-09-16b

Nuance on this row's first trap, checked further the same session so the row does not overstate what was verified.

**VERIFIED FIRST-HAND (READ):** `formal/conformance/backends.py::setengine_answers` loops `eng.add_tuple(...)` with NO try/except, so an `AdmissionRejected` PROPAGATES and fails the test loudly. For the set-engine leg of `test_conformance_enum.py`, a refusal RAISES -- it does not silently drop a store. That is the basis for the trap as written.

**BUT THERE IS A TENSION WORTH KNOWING BEFORE YOU SIZE THIS, and it is NOT resolved:** `formal/CORRESPONDENCE.md` sec 7 says of this very code that "A bug here silently shrinks the enumerated space -- and nothing formal watches it", citing a docstring that records 132 of `two_stratum_cascade`'s 299 stores being rejected. Read in context sec 7 is a list of regions with no LEAN counterpart, so "nothing formal watches it" plainly means "no proof watches it" -- but the "silently shrinks" half then reads as a claim about runtime behaviour that the `setengine_answers` read above contradicts. Two possible resolutions, and this session did not pick one: (a) the prose is loose and means the Lean gap only; (b) some OTHER driver -- the graph leg uses POISON BOOKKEEPING on an `AdmissionRejected` rather than raising (`backends.py`, the per-op driver class) -- does shrink, and sec 7 is describing that path.

(!) A related AGENT claim, UNVERIFIED: that an exact `== 132` rejected-store pin exists for the 299-store `group_userset` domain. If that pin is real it is STRONGER than the floor this row proposes -- an exact equality goes red on an over-reject AND an under-reject -- and this row should then be about extending that shape rather than inventing a new one. **Check for it before writing any floor.**

-> NEXT: resolve (a) vs (b) by reading the graph leg's poison path next to the set-engine leg, and grep for the `== 132` pin. One measurement settles the row's real scope.
