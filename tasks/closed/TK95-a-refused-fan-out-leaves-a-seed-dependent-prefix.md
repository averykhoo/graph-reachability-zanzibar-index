---
id: TK95
title: a refused fan-out leaves a seed-dependent prefix of writes and nothing pins the rollback
brief: MEASURED: 21 aborts a run, every one at fan-out position >=2; prefix moves with the hash seed
pri: NOW
size: S
deps: []
related: [TK93]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-21b
moved: 2026-09-27c
updated: 2026-09-27c
closed: 2026-09-27c
---

A rewrite fan-out that is REFUSED part-way through leaves a prefix of leaf writes already
applied inside the transaction, and **which writes are in that prefix varies with
`PYTHONHASHSEED`** -- `zanzibar_utils_v1.py::RuleSet.apply` yields out of a `set`, and
`tests/parity.py::_GraphSide.apply` (and, in production,
`connectedstore/apply.py::_apply_row`) consumes it inside one `try` whose `except` rolls
back. Correctness rests entirely on that rollback undoing exactly the prefix. Nothing
asserts it.

**MEASURED 2026-09-21b** (`TK93`, `formal/probes/tk93_ensure_raw_bisect_2026-09-21.py`), one
run of `tests/test_generator_coverage.py`:

```
total aborts                     21
at fan-out position 1             0    <- not one
at fan-out position >= 2         21    <- every one leaves a completed prefix
raiser                           AdmissionRejected, in every case
```

and the prefix MOVES: at seed 0 the dense test aborts `3`x at position 2 and `8`x at
position 3; at seed 1, `0`x and `11`x. Same `21` aborts, same decision, different prefix.

## Why this is not already covered

It is evidently FINE -- `31 passed` at four different seeds, and the set engine agrees on
every query, which is the equivalence referee. But that is a run-wide consequence, not a
pin: no test drives one fan-out in two orders and compares. The thing that would catch a
regression here (a rollback that misses a bridge edge, an interned middle that survives, a
ref-count that does not unwind) is exactly the thing a run-wide green cannot distinguish
from luck.

## Shape of the work

* A fixture whose fan-out has `>= 2` leaves with one REFUSED -- reachable today, the
  generator corpus hits it `21` times a run, so the cheap route is to have the probe record
  the `(schema, triple)` of an abort rather than to invent one.
* Drive it in both orders (natural and reversed / sorted) and assert the post-rollback
  snapshot is byte-identical, on the graph side AND against the set engine.
* An anti-vacuity assert that the fan-out really had `>= 2` members and really raised at a
  position `> 1` -- without it the test passes on a one-leaf fan-out and proves nothing.
* Per `docs/sabotage-procedure.md`: sweep the whole module with mutations, not one sabotage,
  with an `M0` control. The obvious mutation to sabotage is the `rollback()` itself.

## Read first

- [`docs/tk93-ensure-raw-seed-dependence-2026-09-21.md`](../docs/tk93-ensure-raw-seed-dependence-2026-09-21.md)
  sec 4 (the mechanism, first-hand) and sec 7 (why this was split out instead of bolted on).
- `formal/probes/tk93_ensure_raw_bisect_2026-09-21.py` -- reuse it; `--sorted-fanout` is
  already the order-reversal arm, and the abort census is already per-position.

(!) Do NOT "fix" this by sorting the fan-out in production. Sorting is an instrument here;
as a fix it costs the live write path and buys nothing observable. The deliverable is a PIN
on outcome-equivalence, not a change to the order.

## Log

### 2026-09-27c

PINNED, no product change: tests/test_tk95_truncated_fanout_rollback.py (5 tests) drives each refused fan-out in ALL n! orders and asserts the store is byte-identical (ids + sqlite_sequence) to pre-write, a follow-up lands byte-identical to a never-refused control, and the grid matches oracle + both set engines. Fixture = the corpus own aborts (capture 2026-09-27: 22 at seed 0, all cycle refusals at position 3 of 3). Production arm runs advance_index with a good row ahead of the refused one, incl. cap-fanout (ClosureFanoutExceeded, the refusal an ADMITTED row can hit). Mutation sweep M0-M9: all as named in advance; M4 (outbox-buffer leak guard) INERT because every add-path refusal raises before the first _emit (READ). Map (FROZEN): docs/tk95-truncated-fanout-rollback-2026-09-27.md.
