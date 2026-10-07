# Context-framework audit: fixes owed in this repo (cross-repo audit, 2026-10-07)

**FROZEN 2026-10-07c (every item minted or answered).** Items 1-4 are `TK128`-`TK131`. Item 5:
the owner promoted `TK97` to NEXT and left `HS-5` / `TK86` at LATER. Live state is
`python scripts/task.py show <id>`, never this file. It was an ACTIVE-PLAN until every item
below was minted into the tree (`task.py new`) or done. Written by a cross-repo audit session run from outside this repo (not a session here);
its working notes were in the gitignored `PycharmProjects/.scratch/context-framework/`, so this
file is the only tracked copy. Owner's instruction: deal with these. All figures measured
2026-10-07.

## Fixes

1. **Stale cap in the banner.** `HANDOFF.md` banner still says the NEXT tier has a "cap of 3";
   the cap has been 5 since 2026-10-04. Fix the text, and extend
   `scripts/handoff_lint.py::check_restated_counts` so a "cap of N" phrasing is caught — it
   passed this one.
2. **Restated count.** `docs/README.md` §8 table row for `CLAUDE.md` says "the four
   footguns"; `CLAUDE.md` lists five. Per this repo's own rule, delete the number and point at
   the list.
3. **The banner line cap is evaded by line length.** The banner sits at its 14-line cap, but
   single lines reach ~3.7k characters, and layers stamped 2026-09-13 and 2026-09-22 are still
   in it (the layering `docs/README.md` §6 bans). `HANDOFF.md` has regrown from 4.3 KB at the
   2026-09-06 cutover to ~18 KB. Add a byte cap (or a per-line width cap) to
   `handoff_lint.py`, and prune the stale layers.
4. **Uncapped and full files.** `CLAUDE.md` is 558 lines / ~45 KB with no cap, and grows
   ~4 KB a week. `formal/HANDOFF.md` is at exactly 520/520 lines. Add a `CLAUDE.md` byte cap
   (audio-workspace's `claudeMdShape` is the model: a ceiling plus a per-table-row cap), and
   prune both.
5. **Owner decision: framework-check rows parked at LATER.** `TK97` (Still-owed bullets aging
   out — a 2026-10-05 bullet has already been re-stamped), `HS-5` (docs declaring liveness, at
   LATER since 2026-08-20) and `TK86` (`(!)` used to dodge the ⚠ budget). The audit recommends
   promoting `TK97` to NEXT; ranking is the owner's call — ask, don't promote.
