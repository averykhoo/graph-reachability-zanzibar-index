# `P22` — the I14 crossable-middle corpus, and the masking that made it vacuous

**FROZEN at `P22`'s close, 2026-09-16 — provenance, not a living status.** Every figure
below was measured on 2026-09-16 against the tree that became the `P22` commit. Live state
is the task row (`python scripts/task.py show P22`) and `python scripts/gate_status.py`,
never this file. Corrections append dated at the top.

## Why this file exists

`P22` was filed 2026-09-06b as a **green sabotage**: deleting the I14 crossable-middle loop
in `index_v4/bulk_build.py` left every `build_index` caller GREEN. The resolution was
supposed to be one line — add a corpus that reaches the loop to
`tests/test_bulk_build.py::_CORPORA` and keep the sabotage as a permanent pin.

It was not one line. **The first corpus that reached the loop did not pin it**, and the
reason generalises well beyond this row, which is why it is written down rather than left
in the commit message.

## What was inherited (2026-09-15d session, uncommitted)

- `formal/probes/bulk_i14_crossable_middle_2026-09-16.py` — a tracked probe, rc=0, whose
  literal transcript shows the minimal three-tuple store diverging under sabotage.
  **Re-run first-hand 2026-09-16: reproduces exactly, transcript matches the header.**
  (PROBED.)
- `tests/test_bulk_build.py` — the `owc_star_ttu` schema, tuple builder and grid, defined
  but **never added to `_CORPORA`**. As inherited it was dead code: the module collected
  the same set of cases as before. (READ, then confirmed by collection.)

## The finding: the corpus was vacuous, and the grid could not see it

Wiring the corpus in and re-running the original `P22` sabotage
(`crossable = schema_info.crossable_shapes` → `frozenset()` in `index_v4/bulk_build.py`)
left the module **fully green**. The corpus reached the loop by the metric the row used —
its `schema_info.crossable_shapes` is non-empty, `{('folder', 'viewer')}`, where every
other corpus has `frozenset()` — and still pinned nothing.

**Cause (PROBED).** The corpus shipped with four tuples beyond the minimal shape, added for
"extra coverage" on the RC2 lesson (*a star-only regression should not be able to hide
behind the concrete path*). Two of the four **mask the mechanism**. Per-tuple measurement,
each run as the probe's part (B) — build the store, neuter the guard, ask the grid:

| store | sabotage verdict |
|---|---|
| minimal three tuples | **RED** — one oracle mismatch |
| `+ ('folder', 'f2', 'parent', 'doc', 'd2')` | GREEN — **masks** |
| `+ ('user', 'u2', 'viewer', 'folder', 'f2')` | GREEN — **masks** |
| `+ ('user', 'u2', 'blocked', 'folder', 'f2')` | RED — safe |
| `+ ('user', 'u2', 'editor', 'folder', 'f2')` | RED — safe |

Both maskers work the same way: they give the generic bridged-in/out loop above the I14
loop a **concrete `viewer(folder, _)` node** to bridge, which completes the
`w_all -> middle -> w_any` crossing without the I14 loop ever running. Every grid answer
stays correct; the loop's own product is simply gone.

⚠ **The masking survives single-tuple removal.** Dropping any ONE of the four extras still
left the sabotage green — two independent maskers were present, so a bisect that removes one
tuple at a time and re-runs concludes "not this one" four times in a row. The measurement
that works is the opposite direction: start from the minimal shape and add one tuple at a
time. (PROBED, both directions.)

## What landed

1. **`_owc_star_ttu_tuples()` keeps the minimal shape plus the two measured-safe tuples**
   (`blocked`/`editor` on `f2`, which exercise the `restricted: editor but not blocked`
   boolean arm without ever interning a concrete `viewer` middle). The table above is
   reproduced in the function's comment, because the next person to add "just one more
   tuple for coverage" needs it at the edit site, not in a doc.
2. **A structural pin in `tests/test_bulk_build.py::_assert_r4bf_features`**, the module's
   existing anti-vacuity hook. The grid is an unreliable witness here — it is exactly what
   the maskers defeat — so the clause pins the loop's **product** instead: the middle node
   `('viewer', 'folder', 'f1', '')` and both bridges around it. `folder:f1` is named by an
   `editor` tuple only and never holds a `viewer` triple, so nothing but the crossable-shape
   loop can create it. The three keys are DERIVED from the literal shipped state, not
   guessed.
3. **An anti-mask control in the same clause**: it refuses the corpus outright if any folder
   acquires a *direct* `viewer` grant. A comment saying "do not add masking tuples" would
   have been read by nobody; this is the mechanical refusal the house rule asks for.

## The three sabotages, and what each proved

Run against the landed tree, `pytest tests/test_bulk_build.py -k owc_star_ttu`:

| # | sabotage | result | fired at |
|---|---|---|---|
| S1 | `crossable = frozenset()` (the original `P22` deletion) | **RED** | `snapshot_rows differ` |
| S2 | keep the loop, drop only the `w_all -> mid` bridge | **RED** | `snapshot_rows differ` |
| S3 | re-add the masking tuple `u2 viewer folder:f2` | **RED** | the anti-mask control, naming `f2` |

S2 is the narrowest plausible weakening rather than an obvious catastrophe, per
`docs/sabotage-procedure.md`. **S3 is the instrument control** and it is the one that
matters most: it is the only evidence that the new clause can fire at all, since S1 and S2
both redden earlier, at the bulk-vs-incremental state comparison. Without S3 the clause
would be an assertion nobody had ever seen fail — this repo's house failure mode.

⚠ **Note what the corpus fix alone bought.** After it, S1 and S2 redden at assertion (0),
the state comparison, *before* reaching the new clause. The structural pin is therefore not
what catches a deleted loop today; it is what catches a **future corpus edit** that
re-introduces masking. Those are different jobs and both are needed: the corpus is the
witness, the clause is the guard on the witness.

## The lesson, stated generally

**"The corpus reaches the mechanism" and "the corpus pins the mechanism" are different
claims, and a configuration-level metric can only establish the first.** `crossable_shapes`
being non-empty was true, load-bearing-sounding, and insufficient: the loop ran, produced
its middles, and no assertion in the module could tell whether those middles had been
needed. The check that distinguishes the two is always the same one — **sabotage the
mechanism and watch the corpus go red** — and it is cheap. It was skipped here because the
configuration metric looked like proof.

Where the mechanism is a *redundant* path (one of several routes to the same answer), the
answer-level grid is structurally incapable of pinning it, because redundancy is exactly
what masking exploits. Pin the product, not the answer.
