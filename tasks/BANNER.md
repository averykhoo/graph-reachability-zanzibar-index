2026-09-05b — `P3` LANDED: the write-leg-only flip was kernel-refuted, so (alpha)+R5 co-landed; sorry-free, P6 retired.

🟢 Gate: ask `python scripts/gate_status.py` (all ten phases were run on the committed tree; re-run `lean` after any `*.md` edit).
★ **`P3` is CLOSED.** Both logged legs fold `rewriteClosureL S (rawWriteTuples S t)` (`Cascade.lean:190-191`, `:340-341`),
`affectedKeys` dirties the PUBLIC key via `publicOfLeaf` (`:542-546`); all four `sorry`s discharged; pins 49/49 + **250/250**
(regenerated 232 → 250 after a control run); projection **P6 deleted** (ledger P6=0, compared 189 → 265, count 515 unchanged).
⚠ **The adjudicated write-leg-ONLY re-point was FALSE** — `graph_correct` refuted sorryAx-free on that tree (branch
`p3-flip-red-2026-09-05`, do not merge). Branch (alpha) + R5 are co-requisites, not follow-ups. PROOF_STATUS `2026-09-05b` §1–§10.
⚠ **`verify.sh`'s `sorry` belt had counted 0 on every build since `ZT-P2-4`** (grep pattern vs Lean's backtick quoting) — fixed, live 0.
⚠ **The flip doubled an ALREADY-exponential derived-arm stacking** (zcli >120s on `two_stratum_cascade`; control 1013 at n=5) — two Python-mirroring `eraseDups` (`cascadeKeysAbove`, `enumJob2(D).cands`) make it linear; golden regenerated after a control run, `_MIN_LEDGER_STACKED` 19 → 18.
→ **`P6` promoted to `NOW` MECHANICALLY** (top `NEXT`, its `P3` blocker gone) — re-rank if you disagree. `P4` deps swept; `P5`
is now PROOF work (T2a did NOT widen; probe re-run: `negFree := true` on the model's own write leg, control reproduces D.3).
⚠ User calls owed: `TK55` `keysNonempty` (scope vs discharge); keep-or-delete the RED branch. `TK54`: `Scratch4cii.lean` is tracked.
(!) `t2c` includes `tasks/*.md` — write the mirror BEFORE the tiles or they strand. New traps: scope doc §11.13 (bb)–(gg).
