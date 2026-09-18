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
moved: 2026-09-19
updated: 2026-09-19
closed:
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
