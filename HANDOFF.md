# HANDOFF — start here

The single entry point for a Claude Code (or human) session on this repo. Read
this **first**, then [`CLAUDE.md`](CLAUDE.md), then whatever the task points into.

- **`CLAUDE.md`** = the durable contract (how to run things, conventions, the
  gate, invariants). It rarely changes.
- **`HANDOFF.md`** (this file) = the mutable state: current status + the open-TODO
  board. **Keep it current** — when you pick up or finish work, edit the board
  below. This is the "one thing to point at" so instructions don't have to be
  relayed each session.

> The formal subtree has its own compact entry point,
> [`formal/HANDOFF.md`](formal/HANDOFF.md) — read that before touching anything
> under `formal/`. This file is the whole-project analog.

---

## Current status — 2026-07-16

- **Everything is complete and green.** Both evaluation backends (set engine +
  graph index), the composition layer, and the Lean formal layer all pass their
  gates. Lean is sorry-free and axiom-clean (412/412). No known correctness bug.
- **Perf optimization arc is CLOSED at round 5** — the measured worklist is
  exhausted (the last candidates N13/N14 were assessed and declined on a fresh
  profile). Record: [`docs/history/perf-round5-2026-07.md`](docs/history/perf-round5-2026-07.md).
  Standing perf guardrails (fence, dead-ends, hygiene) live in
  [`docs/perf-next-round.md`](docs/perf-next-round.md).
- **Clean on `master`.** Last change: docs cleanup (commit `972993d`, retire
  completed design/planning docs + align docs to code).

---

## Open-TODO board

### Active work
_None in flight._ The repo is in a clean, fully-gated state awaiting the next
direction. **When you start a task, add it here** (with owner/date if useful) and
move it to the history/changelog trail when done.

### Deferred / backlog (documented, none urgent; none block)

Migrated from the `README.md` "TODO" list (its struck-through items already shipped).

- [ ] **Track user-triples vs rule-triples in the index** — partial today:
      boolean relations already distinguish storage leaves from routed leaves, but
      pure-union relations still mix user-added and rule-derived triples. (The dead
      `legacy/index_v3.py` `user_edge_count` musing was the v3 gesture at this.)

### Someday / out of scope (low priority — revisit only on a concrete need)

- [ ] **Lift the two scope rejections** — object wildcards on derived relations,
      and wildcard usersets over derived relations, currently raise
      `UnsupportedByGraphIndex` (loud compile-error hooks); the documented fix is a
      symmetric subject-keyed residue (symbolic composition through residues), and
      it is the sole item not yet modeled in Lean (`formal/FINAL_REVIEW.md` §4 last
      item). **Low priority — the OpenFGA DSL does not support these either**
      (verified against the OpenFGA Configuration Language docs, 2026-07-16):
      OpenFGA rejects `<type>:*` in a tuple's object field and rejects wildcard
      usersets (`[group:*#member]`) with a validation error. The one plausible
      pattern (broad grant + per-object boolean exception) is already expressible
      via a supported TTU/hierarchy. So this is a deliberate boundary, not a gap —
      revisit only if a concrete, OpenFGA-shaped need appears.
- [ ] **A real service wrapper** — deliberately skipped; the store is a plain
      callable API.
- [ ] **Tuple-log compaction** — only if the log ever outgrows "humans wrote this" scale.

### Standing / latent (non-blocking — no action needed unless a motivating case appears)

- [ ] **Set-engine flow graph omits bridge edges** (correctness parity, latent).
      A multi-hop cycle through a star bridge (a rule edge out of a star userset +
      a rule chain back into a concrete of the same subject-wildcard shape) would
      be **set-accepted but graph-rejected**. Fix would add bridge-aware
      `_flow_reaches` edges (in-bridges concrete→star per subject-wildcard shape,
      out-bridges star→concrete per owc shape). **No known corpus can build the
      shape today**, so it is filed, not fixed. Refs:
      [`docs/perf-next-round.md`](docs/perf-next-round.md) minor notes;
      [`docs/spec-deviations.md`](docs/spec-deviations.md) (2026-07-15 §3 residual /
      "Known residual").
- [ ] **Other documented latent/theoretical notes** — a handful of
      "documented, no corpus exercises it, not urgent" corners (e.g. a from-chain
      TARGET theoretical note; tupleset-of-derived latent gap). The full inventory
      is the divergence log: [`docs/spec-deviations.md`](docs/spec-deviations.md).
      Do not chase these speculatively; act only if a real schema/corpus surfaces one.

_(Declined / dead-end items — do NOT re-chase — are listed in
[`docs/perf-next-round.md`](docs/perf-next-round.md) "Minor notes" and the fenced
P12c list.)_

---

## Where things live

| doc | what it is |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | durable rules: env, the gate, layout/mental model, testing conventions, invariants |
| [`docs/architecture/overview.md`](docs/architecture/overview.md) | **architecture index** — module map + pointers to every deeper doc |
| [`docs/gate-runbook.md`](docs/gate-runbook.md) | how to run the full gate cap-safe (pytest split + phased `verify.sh` + fuzz) |
| [`docs/perf-next-round.md`](docs/perf-next-round.md) | perf standing guardrails (arc closed; fence + dead-ends + hygiene) |
| [`docs/spec-deviations.md`](docs/spec-deviations.md) | dated log of where the code diverges from the specs, and the latent-gap inventory |
| [`docs/specs/`](docs/specs/) | the full original design specs (cited by code comments as "spec §N") |
| [`formal/HANDOFF.md`](formal/HANDOFF.md) | entry point for the Lean formal layer (read before touching `formal/`) |
| [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) | the model↔Python code map (§7/§8 record any algorithm drift) |
| [`benchmarks/results/PERF_ANALYSIS.md`](benchmarks/results/PERF_ANALYSIS.md) | measured perf numbers per landed item ("Applied") |
| [`docs/history/`](docs/history/) | retired round records (perf rounds 3–5) — provenance, not living docs |

---

## Working rhythm

1. **Read this file + `CLAUDE.md` first.** Pull deeper docs on demand from the map above.
2. **Run the gate before pushing** — never push red or unverified. Cap-safe recipe
   in [`docs/gate-runbook.md`](docs/gate-runbook.md): `pytest tests/` (split) green,
   then `verify.sh lean` → `conf-heavy` → `conf-rest` all `PASSED`; an algorithm
   change also runs the multi-seed fuzz sweep. Commit and push **only when asked**.
3. **Keep the honesty norms** — report gate output as-is; if something is skipped
   or fails, say so. Never edit a golden/oracle/snapshot just to make a change pass.
4. **Keep this board current** — add active tasks when you start them, clear them
   when the work lands (the git log + `docs/history/` are the durable trail).
5. **Perf or algorithm work?** A behavior-preserving micro-opt needs no Lean change;
   an optimization that changes a *modeled* algorithm must update the matching Lean
   def and re-run `verify.sh`, or log the gap in `formal/CORRESPONDENCE.md §7`
   (see `CLAUDE.md` "Perf work & the Lean model").
