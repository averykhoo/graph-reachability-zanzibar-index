---
id: TK76
title: a shipped pin test's stated instrument control is INERT: widx.paranoia is not an attribute
brief: READ: grep -c paranoia index_v4/wildcard.py -> 0; the docstring claim at test_cascade_quiesce_gc.py:163 is false
pri: NOW
size: S
deps: []
related: [TK73, TK74]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-18
moved: 2026-09-19b
updated: 2026-09-19b
closed: 2026-09-19b
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-09-18

READ FIRST-HAND this session. `tests/test_cascade_quiesce_gc.py:169` is `graph.widx.paranoia = False`, and the docstring at `:163` justifies the test with "Paranoia is OFF so the settle assert is the instrument under test rather than I6".

**`WildcardIndex` HAS NO `paranoia` ATTRIBUTE.** `grep -c paranoia index_v4/wildcard.py` -> **0**; `hasattr(WildcardIndex, 'paranoia')` -> **False**; `[a for a in dir(WildcardIndex) if 'paran' in a.lower()]` -> `[]`. The line creates a brand-new instance attribute that nothing ever reads. Real paranoia is session event listeners installed by `tests/wildcard_helpers.py::make_wildcard_index` (`paranoia: bool = True` -> `index_v4/invariants.py::install_paranoia`), so `::test_settle_pass_detects_genuine_staleness` actually runs at FULL paranoia and passes anyway.

The test's OUTCOME is right; its STATED CONTROL is not the one it performs. That is this project's house failure mode sitting inside the module that pins `TK73`, filed one day after that module landed. The same inert line is reproduced in the `TK73` doc's sabotage record, so the doc inherits the false claim.

FIX (mechanical, preferred over a doc warning): either thread a real `paranoia=False` through `tests/test_matrix.py::GraphBackend`, or assert `session.info['paranoia_guards']` is empty at the point the docstring claims paranoia is off. Then SABOTAGE it -- turn paranoia genuinely off and confirm the settle assert is still what reddens, which is the claim the docstring is making.

Found by the `TK74` fan-out completeness critic (2026-09-18) and re-verified here. Map: [`docs/tk74-staleness-net-2026-09-18.md`](../docs/tk74-staleness-net-2026-09-18.md) sec 6.

### 2026-09-19b

FIXED AND GATED 2026-09-19b. The stated control was inert AND its stated rationale was false in premise; both are repaired mechanically, and the repair is pinned by an 8-mutation sweep.

WHAT LANDED.
- `tests/test_matrix.py::GraphBackend.__init__` now takes `paranoia='full'` and FORWARDS it to `make_wildcard_index`. It had to be a constructor knob: `install_paranoia` can only ever RAISE (`ParanoiaGuard.raise_to`), so no post-construction call can produce an off store. Default is unchanged for all ~24 existing call sites.
- `::test_settle_pass_detects_genuine_staleness` is PARAMETRIZED over `PARANOIA_LEVELS` and opens with a REAL control -- `paranoia_level(session, 'g') == tier` -- in place of `graph.widx.paranoia = False`, which set an attribute `WildcardIndex` does not have.
- It also asserts the raise does NOT start with `store=`, the prefix `_violations_tagged` adds at commit time. That is the mechanical form of "the settle assert is the instrument under test", which the old docstring asserted in prose and never checked.
- NEW `::test_a_commit_phase_violation_is_tagged_so_test_3_can_tell_them_apart` is the instrument control for that assertion: an assertion no arm can fail is a false green, so this one shows the discriminator fires (delete a closure edge -> `store='g' [pre-commit] I13: ...`).
- Module docstring and TEST 3 docstring corrected, dated, with the old text quoted so the correction is readable.

THE MEASUREMENT THAT CHANGED THE FIX. The old rationale was "paranoia is OFF so the settle assert is the instrument rather than I6". Measured first-hand at all four tiers: the settle clause raises in EVERY arm and no message carries the commit-phase prefix -- the raise happens inside `run_cascade`, before `session.commit()`, so no tier can preempt it. Stronger: the corruption the test performs is INVISIBLE to the commit-phase checker. Deleting that residue row, deleting every residue row, and bumping a residue version all commit clean at `paranoia='full'`; only a closure-edge deletion reaches it (I13). So I6 would not have preempted anything even had the tier really been off. The fix is therefore not "restore the claimed control" but "make the claim checkable".

SWEEP (8 mutations, 8 RED, 0 INERT, M0 attributing; literal table in the module docstring, harness `.scratch/tk76/sweep.py`). The load-bearing row is the attribution, not the verdict: M0/M1/M2 redden the `off`/`residue`/`fixpoint` arms and leave `full` GREEN -- so the single-arm version of this test could not have caught the knob failure it claimed to control for, which is what earns the parametrization. M3/M4/M5 redden `full` too (the settle pins are tier-independent). M6/M7 pin the new instrument control from both sides.

INSTRUMENT FAILURE, recorded: the sweep's first run reported `attributed=0/0` on every row -- `pytest -q` prints no nodeids, so the harness regex matched nothing and an all-RED table carried a meaningless attribution column. P6 step 0's failure verbatim, caught only because M0 was there.

VERIFY: `pytest tests/test_cascade_quiesce_gc.py -q` -> `7 passed` (was 3 tests, now 2 + 4 params + 1). `pytest tests/test_cascade_quiesce_gc.py tests/test_matrix.py tests/test_cascade_fixpoint_tier.py -q` -> `35 passed`. Full ten-phase gate green on this tree.
