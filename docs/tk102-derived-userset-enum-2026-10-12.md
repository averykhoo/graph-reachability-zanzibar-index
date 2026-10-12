# TK102 -- the derived-userset corpus in the exhaustive enum arm (2026-10-12)

**FROZEN 2026-10-12 (`TK102` closed, session `2026-10-12c`) — provenance, not a living document.**
Was an ACTIVE-PLAN (`docs/README.md` §3), opened the same day. Status lines below are
as-of-then; live state is `python scripts/task.py show TK102`, never this file.
Corrections are appended dated at the top, never edited into the body.
Provenance labels: **READ** (first-hand read of the tree), **RUN** (first-hand run, output
quoted), **REASONED**, **UNVERIFIED**. Line numbers are as of 2026-10-12.

**Correction 2026-10-12c, second (adversarial review 2 of TK102, fixes applied the same
session). It supersedes the 328 figure in the correction block below.**

- **The write-order figure was pinned under a false label (major).** The first correction
  pinned **328**, counting stores for which SOME pool renaming permutes their sorted write
  order, and every carrier called that "stores whose write order the quotient does not
  drive". That set includes **68 of the 119 representatives**, whose order IS driven. The
  graph drives each representative's sequence and, by name-equivariance, every renaming of
  it; a store is undriven when its own sorted sequence is none of those. RUN 2026-10-12c
  (reviewer probe `.scratch/uc-2026-10-12c/tk102-review2/order_gap.py`, re-derived by the
  new pin): **116 of the 697 stores** are undriven, falling into **44** write-sequence
  classes up to renaming, and **163 = 119 + 44**, so the sec. 2 closing-cost estimate below
  ("+44 graph-only drives") was right and only the store count was mislabelled.
  `formal/conformance/test_conformance_enum.py::_ORBIT_ORDER_VARIANTS` is replaced by
  `::_ORBIT_ORDER_UNDRIVEN = {"derived_userset_subject": (116, 44)}`, and
  `::test_orbit_reduction_write_order_cost_is_pinned` now picks representatives exactly as
  `::test_exhaustive_small_scope` does and asserts `classes == representatives + undriven
  classes`. Sabotage (RUN, restored byte-exact, `cmp`): pin (116, 44)->(117, 44) RED 0.90 s;
  identity-only renamings RED (`('derived_userset_subject', 697, 119)`) 0.86 s; the
  renaming closure dropped (`driven.add(seq)`) RED (`163 ... != 119 representatives + 158
  undriven classes`) 1.14 s; every store counted as driven RED (`... + 0 undriven classes`)
  0.88 s. Carriers corrected: the `_ORBIT_REDUCED` comment, `formal/ARCHITECTURE.md` enum
  bullet, `formal/FINAL_REVIEW.md` enum row, and the `formal/CORRESPONDENCE.md` enum row,
  which now carries the caveat too (it had none; +1 Python anchor, `doc_counts
  --generate` re-run: 755 anchors).
- **The non-representative branch had no counter (minor).** `test_exhaustive_small_scope`
  now counts `n_cheap_only` and asserts it equals `n_stores - n_driven` (578). RUN: a bare
  `continue` first in that branch is RED (`oracle x set-engine compared on 0 of the 578
  stores the orbit quotient did not drive`, 100.11 s). LIMIT (RUN): a skip that keeps the
  increment stayed GREEN (`1 passed in 107.04s`), and so does the reviewer's `assert True
  or not mism`. The counter proves the branch is reached, not that its assert is live.
- **Module docstring overclaim (minor).** "the partial-store interleaving no curated arm
  drives" was false: `test_conformance_remove.py::_sequence` seeded-shuffles the curated
  corpus and re-adds removed tuples, and goes red on S1 (sec. 4.1). The docstring now says
  the curated arms reach that interleaving only by sampling, and this shape is exhaustive
  to K=3.
- **Tile budget (minor, still OPEN).** The shape's node is collect index 38, so
  conf-tile:4/5, which ran 601 s on the 2026-10-12 ledger; this adds ~100-125 s. It
  predates the item (tile 5 at 925 / 1080 s) and stays a closing-stage gate-config
  decision (sec. 5).
- **S1 on the six pre-existing shapes (minor, was implementer-only).** Re-run 2026-10-12c in an ISOLATED temp copy of the tree
  (no source mutated in the shared checkout). The original mutation text was never
  recorded, so S1 was RECONSTRUCTED: after the `triples_to` loop in
  `src/zanzibar/graphindex/core.py::_add_direct_edge_unsafe_impl`, `if self._writing_derived
  and count > 0: reachable_after_object = MultiSet()`. RUN: the new shape goes RED at the
  same `enumerated store #75`, `1 failed in 14.79s`, and the six pre-existing shapes stay
  GREEN, `6 passed, 3 deselected in 569.29s`. That confirms the sec. 4.1 claim.

**Correction 2026-10-12c (adversarial review of TK102, fixes applied the same session).**

- **Sec. 2 "What the quotient gives up" was incomplete (major).** Besides name-dependent
  bugs, the quotient also drops WRITE-ORDER variants: every store is written in
  sorted-space order, and for **328 of the 697 stores** some renaming maps that order onto a
  sequence that is not the renamed store's own sorted order, so that orbit-mate's write
  sequence is never driven through the graph index, which is incremental and so may be
  order-dependent (the order-blind oracle x set-engine legs still see every store). RUN:
  the reviewer's independent probe (own renaming code) printed `stores whose some renaming
  permutes their write order: 328`, re-run first-hand, and the figure is now ASSERTED by
  `formal/conformance/test_conformance_enum.py::test_orbit_reduction_write_order_cost_is_pinned`
  (`_ORBIT_ORDER_VARIANTS`; sabotage pin 328->329 and identity-only renamings both RED,
  recorded in its docstring). **Cost to close it (RUN for the count, REASONED for the
  time):** classing stores by write SEQUENCE up to renaming gives **163** classes instead
  of 119 orbits, so +44 graph-only drives (spec is order-blind and need not re-run),
  roughly +25-30 s. Not taken here; a closing-stage choice.
- **Carrier docs (minor).** `formal/FINAL_REVIEW.md` (the "exhaustive small-scope
  enumeration" row) and `formal/ARCHITECTURE.md` (the enum bullet) kept the false sentence
  "the graph backend is not in the ANSWER enumeration" with a contradicting update
  appended; both now state once that the graph has been in it since 2026-07-18, then the
  seventh shape. These are LIVING docs, so the fix is in place.
- **Tile claim (minor).** The module docstring's "spread across the `conf-tile` phases, so no
  single tile pays both" was unverified. RUN (collect-only, verify.sh's `index mod K`
  rule, 1093 nodes): `test_exhaustive_small_scope[derived_userset_subject]` is index 38,
  i.e. **conf-tile:4/5**, and the four nodes this item adds shift every later node's tile.
  The docstring now promises no tile assignment. Runtime: 104.07 s (sec. 4), 69.74 s
  (the reviewer's re-run) and 108.76 s (this fix's re-run, `4 passed in 110.01s` together
  with the three bookkeeping tests).
- **Floor (minor).** `MIN_CONF_ALL` was 1087 against a live 1089 at HEAD `4d24031` (the +2
  are `TK127`, `7449537`: `test_w4fragment_scope_pin.py` 7 -> 9 test functions), so
  deleting the new tests left the floor green. Raised to **1093** (`MIN_CONF_REST`
  952 -> 958, heavy 135 unchanged), provenance in `formal/verify.sh`; `doc_counts --check`
  rc=0. The floor mechanism is unchanged, so its 2026-09-24 instrument check stands; no
  gate phase was run here.
- **P16 (minor, no change).** Sec. 5's deferral stands; `P16` remains its own LATER row.

## 1. Sizing, measured before the name was added (RUN, 2026-10-12c)

Probe: a throwaway script calling `test_conformance_enum::_tuple_space` / `::_all_stores`
on `corpus.SCHEMAS['derived_userset_subject']`, then timing each leg over 20 shuffled
(seed 0) size-3 stores. Its logic is now in the module itself (sec. 3), so the probe is
not kept; the numbers below are regenerated by the pins in sec. 3.

| quantity | value |
|---|---|
| declared tuple space over `_POOL` | **16** (4 `doc.viewer [user]`, 4 `doc.viewer [group#member]`, 4 `group.allowed`, 4 `group.blocked`) |
| stores of size <= K, K = 2 / 3 / 4 | 137 / **697** / 2517 |
| orbits under pool-name renaming (2!^4 = 16 renamings; `folder` acts trivially here), K = 2 / 3 / 4 | 31 / **119** / 397 |
| shared grid | 336 queries; all 336 survive `_graph_query_filter` |
| per-store cost, mean of 20 size-3 stores | spec (zcli) 0.114 s, oracle 0.0085 s, set engine 0.028 s, graph index 0.61 s |
| disagreements on those 20 stores, all four legs | **0** |

Consequences (REASONED from the table):

- **Plain exhaustion does not fit.** K=3 is 697 stores x ~0.76 s = ~530 s, which alone
  is most of a `conf-tile` budget (the five tiles measured 431-925 s on 2026-10-12 in
  `.gate-runs/ledger.tsv`, so the tiles are already the tight resource). K=4 is ~32 min.
- **The graph leg is 80 % of the per-store cost**, and the zcli spec leg most of the rest.
  The oracle and the set engine together are ~0.037 s per store.
- **Admission: 100 % valid.** Nothing in this schema can cycle (`doc.viewer` points at
  `group#member`; nothing under `group` points back), so the set engine's userset-cycle
  guard that excludes `group_userset` (module docstring) cannot fire. RUN: no write raised
  on the 20 probed stores; the full K=3 run in sec. 4 drives all 697 through the set engine
  and every write would raise if refused (`backends.py::setengine_answers` catches nothing).

## 2. The design: exhaustive up to name symmetry, split by leg cost (REASONED)

The cheap legs stay fully exhaustive; only the expensive legs are reduced, and the
reduction is a SYMMETRY quotient, not a sample, so it still covers every store (up to
renaming) and needs no seed.

- **oracle x set engine: all 697 stores of size <= 3.** ~26 s. No reduction at all.
- **spec (zcli) and the real graph index: one representative per orbit, 119 stores.**
  Two stores are in one orbit when a renaming of the pool names (`u1<->u2`, `g1<->g2`,
  `d1<->d2`, `f1<->f2`, independently per type) maps one onto the other. The
  representative is the FIRST store of its orbit in `_all_stores` order, so the choice is
  deterministic and every representative is a store the plain enumeration also yields.
- **Why the quotient is sound.** `sem` names entities only by equality (and the `*`
  sentinel, which no renaming touches), so `sem(pi S)(pi q) = sem(S)(q)` for every renaming
  `pi`. Checking every query of the grid on `S` therefore checks every query of the grid on
  `pi S`, PROVIDED the grid is closed under renaming. That precondition is not assumed: the
  module asserts that the tuple space and the grid are each mapped onto themselves by all
  sixteen renamings before it reduces anything.
- **What the quotient gives up (stated, not hidden).** An implementation bug that depends
  on concrete names -- an ordering or id-allocation effect that fires for `g2` but not `g1`
  -- would be checked on one member of the orbit only. Two reasons it is acceptable here:
  the oracle and set engine still run on every store, so a name-dependent set-engine bug is
  still exhaustively exposed; and for the graph the alternative is not "all 697" but "K=2
  only" or "a random sample", both of which give up more.
- **K = 3, documented cap.** K=4 would be 397 orbits x ~0.72 s = ~290 s more in the
  expensive legs plus 1820 more stores (~67 s) in the cheap legs. Same lever the module
  already pulls for `two_stratum_cascade` and `wildcard_group_member`: cap the largest
  spaces at K=3 and say so. K=3 already reaches every store holding a userset viewer plus
  an `allowed` and a `blocked` tuple, which is the class's defining interaction.
- **Graph leg: a Python-only differential, declared, not a `GRAPH_FRAGMENT` entry.** The
  corpus is outside `W4Fragment` (`term` / `NoStoreSubjectR`, see `TK94` sec. 3), so no
  theorem routed through `graph_correct` covers it and adding the name to `GRAPH_FRAGMENT`
  is the `ZT-P3-3` mistake. Instead the module gains `_GRAPH_PY_DIFFERENTIAL`, a declared
  set of shapes whose graph leg runs against the agreed `sem == oracle == set engine`
  answer with NO Lean claim (the licence `test_conformance_remove.py`'s graph legs already
  use: "Scope: sem/Lean deferred"). A new check pins that every `_SHAPES` name is in
  exactly one of `GRAPH_FRAGMENT` and `_GRAPH_PY_DIFFERENTIAL`, so the graph leg can no
  longer be SKIPPED silently, which is what the row's 2026-10-04g note asked for.
- **The state leg must not follow.** `test_conformance_enum_state.py` parametrizes over
  `_SHAPES` and compares against the LEAN graph model (`zcli graph-state`). Taking the new
  name there is the `ZT-P3-3` mistake one module over, so it now parametrizes over the
  `GRAPH_FRAGMENT` members of `_SHAPES` only, and pins that the excluded names are exactly
  `_GRAPH_PY_DIFFERENTIAL`.
- **Write order (REASONED, not widened).** `_tuple_space` sorts by `(type, relation)`, and
  `itertools.combinations` keeps that order, so every store is written `doc.viewer` first,
  `group.allowed` / `group.blocked` after. That is precisely the row's interesting case:
  the userset subject is present before the subject's derived `member` state exists, so
  the cascade must propagate new `member` edges through an existing userset edge. The
  reverse order (member state first) is what the curated corpus's own write order drives
  in `test_conformance_remove.py` / the bulk arm; a second graph drive per representative
  in reverse order would cost ~+70 s and is not taken.

## 3. What landed (READ, 2026-10-12c; uncommitted at the time of writing)

- `formal/conformance/test_conformance_enum.py`
  * `::_SHAPES` gains `"derived_userset_subject": (16, 3, 697)`.
  * `::_GRAPH_PY_DIFFERENTIAL` (the declared Python-only graph scope) and
    `::_ORBIT_REDUCED` (`{"derived_userset_subject": 119}`, asserted).
  * `::_pool_renamings` (16 = 2!^4 renamings, the same set the sec. 1 probe used),
    `::_rename_q`, `::_tkey`, `::_orbit_key`, `::_assert_renaming_closed`.
  * `::test_exhaustive_small_scope`: the graph leg runs for `GRAPH_FRAGMENT` OR
    `_GRAPH_PY_DIFFERENTIAL` (its failure message says which scope); for a reduced shape
    the oracle x set engine comparison runs on every store and spec + graph on the
    orbit's first store; new pins `n_driven == _ORBIT_REDUCED.get(name, exp_stores)` and
    `n_graph == n_driven and graph_queries` (the graph leg can no longer skip silently
    inside the test either).
  * `::test_every_shape_declares_its_graph_leg` (new): every `_SHAPES` name in EXACTLY
    one of `GRAPH_FRAGMENT` / `_GRAPH_PY_DIFFERENTIAL`; `_ORBIT_REDUCED` well-formed.
- `formal/conformance/test_conformance_enum_state.py`: `::_STATE_SHAPES` (the `_SHAPES`
  names in `GRAPH_FRAGMENT`) replaces `sorted(_SHAPES)` as the parametrization;
  `::test_state_leg_excludes_exactly_the_py_differential` (new).
- Carriers updated with a dated `TK102` note: `formal/CORRESPONDENCE.md` (the enum row of
  the harness table), `formal/ARCHITECTURE.md` (the enum bullet), `formal/FINAL_REVIEW.md`
  (the "exhaustive small-scope enumeration" claim row; its generated counts block was
  regenerated: conformance collected 1089 -> 1092, `doc_counts --check` rc=0 "all match
  the tree"). `formal/SEMANTICS.md`'s C3 bullet is a dated 2026-07-12m record and is left.

## 4. Measured results (RUN, 2026-10-12c)

- **Clean:** `test_exhaustive_small_scope[derived_userset_subject]` passed, **104.07 s**
  call. No divergence on any of the 697 stores (oracle x set engine) or the 119
  representatives (spec, graph). **No Python fix was needed.**
- `test_conformance_enum_state.py` (6 shapes + the new exclusion test) and the new
  declaration test: `8 passed in 54.79s`.

### 4.1 Sabotage record (RUN; each mutation restored byte-exact from a temp copy, `git diff` empty)

| id | mutation | observed |
|---|---|---|
| S1 (subject) | `graphindex/core.py::_add_direct_edge_unsafe_impl`: when the delta processor adds a derived edge, drop the object's descendants (a new derived `member` edge never reaches a `doc#viewer` through an EXISTING userset edge) | RED, 14.61 s: `[derived_userset_subject] graph/spec disagreement (... PYTHON-ONLY differential, no Lean claim ...) at enumerated store #75 = [g1#member viewer d1, u1 allowed g1]: [(('...', 'user', 'u1', 'viewer', 'doc', 'd1'), True, False)]` |
| S1, other legs | same mutation, the six PRE-EXISTING enum shapes | **GREEN**: `7 passed, 1 deselected in 476.60s` -- within this module only the new shape sees S1 |
| S1, other modules | same mutation, `tests/test_matrix.py` + `test_conformance_remove.py` `-k derived_userset` | RED: `test_graph_remove_sequences` / `test_graph_full_churn_restores` / `test_graph_remove_bulk_build_survivors` `[derived_userset_subject]`, `3 failed, 2 passed, 147 deselected in 4.16s` -- `TK94`'s remove arm catches S1 too, so S1 is not unique to this leg repo-wide |
| S2 | `run_graph = name in GRAPH_FRAGMENT` (the pre-TK102 gate) | RED, 30.78 s: `graph leg ran on 0 of 119 driven stores over 0 queries` |
| S3 | `_GRAPH_PY_DIFFERENTIAL = frozenset()` | RED, 0.84 s: `['derived_userset_subject'] in `_SHAPES` but in neither GRAPH_FRAGMENT nor `_GRAPH_PY_DIFFERENTIAL`` |
| S4 | `grid.py::_USERSET_NAME_BOUND = 1` (a grid not closed under renaming) | RED, 0.83 s: `query grid not closed under pool renaming {... ('group', 'g1'): 'g2' ...}: the orbit reduction would be unsound` |
| S5 | `_orbit_key` drops the subject name (an over-coarse orbit key) | RED, 49.28 s: `drove 61 stores through spec + graph but the documented count is 119 (orbit representatives)` |
| S6 | `_STATE_SHAPES = tuple(sorted(_SHAPES))` | RED, 1.02 s: `state leg excludes [] but the declared Python-only set is ['derived_userset_subject']` |

The 476.60 s figure was measured WITH S1 active; it is a coverage observation, not a
runtime baseline.

## 5. Open, for the closing stage

- **Tile budget (RUN, read from `.gate-runs/ledger.tsv`, 2026-10-12):** the five
  `conf-tile` phases ran 439 / 431 / 544 / 601 / **925** s on tree `t2c:5721de4931ff`
  (earlier that day 685 / 570 / 674 / 654 / 1080 s). Tile 5 is already past the ~600 s
  harness command cap BEFORE this item; this item adds ~104 s + ~1 s to whichever tiles
  the new nodes land in (and adding three collected nodes shifts the `index mod K`
  partition of every later node). `verify.sh`'s usage text says to raise K when a tile
  approaches the cap; that is a gate-config decision for the closing stage, not taken here.
- **Not done (REASONED):** the reverse write order (sec. 2), K=4 (sec. 2), and `P16`
  (widen the bounds generally), which the row's 2026-10-04g note asked to fold in -- this
  item widens by one shape; `P16`'s general widening stays its own row.
- **UNVERIFIED:** whether a sabotage exists that ONLY this leg catches repo-wide (S1 is
  also caught by the remove arm). Not required for the item; noted so the claim is not
  overstated.
