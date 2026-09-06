2026-09-06 — `TK56`: T3's undischargeable `hValid` deleted (with its `opaque`); T3 now INSTANTIATED at an executed store; `P17` is the reach step.

🟢 Gate: ask `python scripts/gate_status.py` (all ten phases run on the committed tree; re-run `lean` after any `*.md` edit).
★ **T1 is unconditional, T3 carries EXACTLY T2b's hypotheses.** `hValid : AllValid T` sat on `opaque ValidIdent` — undischargeable at
every non-empty store, so T3 had NO instance while T2b had two. Deleted (49 Lean sites / 5 files, cold build green first try); added
`W4WitnessDirect.equivalence_applies` + `Exec.lean::graphRunOps_directArm_backend_equivalence` (exists sigma: both backends answer `true`, proved equal).
★ Pins 49→**51** statements, 250→**251** defs, 584→**587** audits (regeneration also caught the never-pinned `graphModeAnswers_eq_sem`).
⚠ **Zero `opaque`s in the tree; `sorry_scan.py` now refuses one at declaration position** (control: HEAD's `Ident.lean` → 1, rc 1; live 0/70).
⚠ **`task.py new` ratchets `min_tasks_parsed` itself** (158→159 on filing `TK56`) — the manual step three sessions forgot; never lowers.
→ **Next toward equivalence: `P17`** — `ReachedBy` grows only from `emptyState`, so no headline covers `build_index(bulk=True)`, the DEFAULT
constructor. Model `bulk_build`/`bulk_backfill` as a base constructor, or scope-exclude it in `FINAL_REVIEW.md`. Second opinion agreed. NOT re-ranked here.
⚠ User calls owed (unchanged): `TK55` `keysNonempty` (scope vs discharge); keep-or-delete branch `p3-flip-red-2026-09-05`; the `tasks/` trial
window closes TODAY 2026-09-06 (`TT-1` cutover-or-keep-both). `P6` stays `NOW` mechanically.
(!) `t2c` includes `tasks/*.md` — write the mirror BEFORE the tiles or they strand. PROOF_STATUS `2026-09-06` §1–§8 has the detail.
