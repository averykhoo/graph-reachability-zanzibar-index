# Scaling benchmark — superseded

**The canonical scaling/baseline write-up is now
[`BASELINE_2026-07-13.md`](BASELINE_2026-07-13.md).** It covers all four shared
surfaces (write · check · lookup · lookup_reverse) across three schema-complexity
tiers (simple / gdrive / demorgans) and 10³–10⁵ tuples, in one comparable session,
and folds in the analysis that used to live here.

This file previously held a 2026-07-08 `scale_bench.py` run over gdrive/demorgans
that measured only **write + check**. Those raw records are preserved in
`scale_bench.archive-2026-07-08-13.jsonl`; the narrative is retained in git
history. Reproduce current numbers with the commands in `BASELINE_2026-07-13.md`.

The two structural conclusions from that run still hold and are restated (with the
new lookup data) in the baseline:

1. **Per-check latency does not grow with tuple count** — a `check` walks only the
   neighborhood the query touches, not the store, so throughput is flat across a
   33× tuple increase. (Now shown for `lookup_reverse` too; `lookup` is the lone
   exception — see the baseline.)
2. **The set engine / graph index trade is at write time** — the graph pays
   closure materialization up front (15–156 writes/s) to make reads O(1); the set
   engine keeps writes cheap (~800/s) and pays at read time.
