# `TK71`: where an admission over-reject can shrink a conformance gate without turning it red

**FROZEN 2026-09-27, at `TK71`'s close — provenance, not a living document.** Status lines
below are as-of-then; live state: `HANDOFF.md` + the session ledger. Corrections are
appended dated at the top, never edited into the body. (Was ACTIVE-PLAN earlier the same
session, `2026-09-27b`.) Figures were measured on `2026-09-27` against HEAD `bb4a2fa`.
The one open end is `TK110` (`tests/` census).

Provenance labels: **READ** (first-hand, this session), **REASONED**, **MEASURED** (a run
whose output is quoted), **UNVERIFIED**. No subagents were used.

## § 0 Summary: the row's premise is wrong for the module it names

The row said `formal/conformance/test_conformance_enum.py` "asserts no admission-SURVIVAL
floor". **That module does not need one. Its survival rate is 100% by construction, and an
over-reject in it goes RED** (§ 1). The two questions the row left open are settled:

* **(a) vs (b), from the 2026-09-16b log entry: it is (a), plus a misattribution.**
  `formal/CORRESPONDENCE.md` §7 ("A bug here silently shrinks the enumerated space") names
  `test_conformance_enum.py` and credits "132 of `two_stratum_cascade`'s 299 stores" as
  rejected. Both halves are wrong. The 132/299 figure belongs to `group_userset`, the shape
  the enum module *excludes* (its own docstring says so, and so does
  `tests/test_zt_p5_readjudication.py::test_zt_p5_group_userset_admission_domains_are_identical`).
  And the enum module cannot shrink silently (§ 1). (READ)
* **The `== 132` pin EXISTS** (READ): `tests/test_zt_p5_readjudication.py::test_zt_p5_group_userset_admission_domains_are_identical`
  asserts `set_rejecting == graph_rejecting == 132` over the 299 `group_userset` stores.
  It is an exact equality, so it catches both an over-reject and an under-reject. It is the
  shape this row copies.

**What the row really asks about lives in a different place: the drivers that ABSORB a
refusal** (§ 2). Three of them are in `formal/conformance/`, and before this row none of them
asserted how many writes it absorbed.

## § 1 `test_conformance_enum.py`: survival is 100%, and nothing can shrink quietly (READ)

* `::test_exhaustive_small_scope` hands every enumerated store to
  `formal/conformance/backends.py::setengine_answers` and `::graphindex_answers`.
  `graphindex_answers` goes through `::graphindex_drive`. Neither has a `try`/`except`
  around the write, so an `AdmissionRejected` propagates out and fails the test.
* The tuple-space size (`len(space) == exp_space`) and the store count
  (`n_stores == exp_stores`) are both pinned by exact equality for each shape in `::_SHAPES`.
  So a store that does not survive admission is a RED, and a store that stops being
  enumerated is also a RED.
* That leaves what the 2026-09-16b trap already named: the module can only see stores inside
  `::_tuple_space`'s range, and that range has no object-wildcard object name. This row does
  not change that (`TK101` owns hole H4).
* **Action: a comment, not a floor.** The module now says in its docstring why no survival
  floor exists. That the RED is real is shown by the sabotage in § 4.

## § 2 The drivers that absorb a refusal: census and measurement

**Census (READ, `grep -rn "except ValueError\|poison" formal/conformance`).** These are the
write-admission sites that turn a refusal into a dropped write:

| site | what it catches | effect of a refusal | pinned before `TK71`? |
|---|---|---|---|
| `test_conformance_remove.py::_drive` (set engine) | **bare `ValueError`** | tuple poisoned, dropped from the final store | no: only `len(final) < len(universe)`, which a shrink *satisfies* |
| `backends.py::graphindex_drive_ops` (graph) | `AdmissionRejected` only (ZT-P4-7) | tuple poisoned, dropped from the final store | no |
| `test_conformance_generated.py::test_generated_schema_zcli_parity` | **bare `ValueError`** | op skipped, excluded from the `accepted` store | no: the grid floor counts queries, not tuples |

The other `except ValueError` sites in `formal/conformance/` (`test_conformance_fragment.py`,
`test_conformance_nary_strata.py`, `sorry_scan.py`) catch *parse* refusals, and each one
matches a fixed message or feeds a refusal differential. They do not absorb write
admission. (READ)

**`tests/` was NOT censused. That is filed as `TK110`.** A narrow grep (a
`ValueError`/`AdmissionRejected` catch within 4 lines of an `add_tuple`/`.apply(` call) finds
only 3 hits, all in `tests/test_admission_rejected.py`, and all of them are expected-refusal
tests. But the full surface is **17 files** that contain an `except AdmissionRejected` /
`except ValueError` / `except (ValueError` (MEASURED 2026-09-27, `grep -rc`). The largest are
`test_hypothesis.py` (6), `test_admission_rejected.py` (5), `test_matrix.py` (4),
`test_wildcard_property.py` (3), `test_setengine_storage.py` (3) and `parity.py` (2). Which
of them absorb a refusal into a smaller compared store is UNVERIFIED.

**Measurement (MEASURED 2026-09-27, `.scratch/tk71/measure.py`, which re-uses each module's
own `_extras` / `_sequence` / `_case` so the op streams are the ones the gate drives).** It
covers all 27 corpora in `formal/conformance/corpus.py::SCHEMAS` × `SEEDS = range(5)`, which
is 135 remove sequences, plus the 40 generated seeds:

* **Set-engine poisoned adds: 0 in 134 of the 135 sequences.** The exception is
  `deep_grid`, with **`(2, 4, 1, 3, 1)` for seeds 0..4 (11 in total)**. Every one is an
  `AdmissionRejected`, and **0** were some other `ValueError`.
* All 11 are `parent`-cycle refusals, for example
  `('...', 'node', 'node5', 'parent', 'node', 'node5') -> tuple node:node5#... parent
  node:node5 would create a cycle in the userset membership topo`. `deep_grid` is
  `r1: [user] or r2 ... r8: r1 from parent`, and `_extras` recombines `parent` names into
  self-loops and 2-cycles. These refusals are legitimate. (MEASURED + READ)
* **Graph accepted-final == set-engine accepted-final in 135 of 135.** So the graph driver
  poisons exactly the same tuples. (MEASURED)
* **Generated: 0 refusals over all 40 seeds** (every `store_ops` entry was accepted). The
  `except ValueError: continue` there has never fired on the gate's inputs. (MEASURED)

## § 3 The fix (decided by the session, per `CLAUDE.md` § "Who decides")

Following the durability ranking in `docs/sabotage-procedure.md`, each pin is **exact** (the
`== 132` shape), not a floor. A floor misses an under-reject, and an under-reject means a
cycle guard that has gone quiet.

1. **`test_conformance_remove.py::_drive` catches `AdmissionRejected` only.** This is the
   set-engine twin of the ZT-P4-7 fix `GraphDriver.apply` already carries. Any other
   `ValueError` now propagates. `_drive` also reports how many it poisoned.
2. **An exact poison table** in `test_conformance_remove.py`: `deep_grid` is `(2, 4, 1, 3, 1)`,
   and every other corpus is 0 on every seed. It is asserted in `::test_remove_sequences`
   (set engine), `::test_graph_remove_sequences` and
   `::test_graph_remove_bulk_build_survivors` (graph). The graph side reads the count
   through a new optional `poisoned_out` set argument on
   `backends.py::graphindex_drive_ops`, so existing callers are unchanged.
3. **`test_conformance_generated.py`** stops absorbing refusals. The measured count is 0, so
   the pin is "no op is refused". A refusal now fails the test, naming each refused op and its message.
4. **`formal/CORRESPONDENCE.md` §7**: the misattribution is corrected, and the prose now
   names the absorbing drivers and their pins.

## § 4 Sabotage (MEASURED 2026-09-27)

Each mutation was applied by `.scratch/tk71/sabotage.py`. The script refuses to run unless
its anchor matches exactly once. It restores the file byte-for-byte in `finally` and asserts
the SHA-256 afterwards; that assert passed on every run. (On five runs the summary `print`
that follows it then crashed decoding pytest's cp1252 log, fixed with `errors="replace"`, so
those runs never printed `restored ok`; `git status` confirmed `setengine/` and `index_v4/`
clean after each batch.) "PRE-FIX" means the `HEAD`
(`bb4a2fa`) copy of the test module, run as a temporary probe file (since deleted) against
the same mutation. Every mutation targets product code, never the test.

| id | mutation (product code) | module / selection | PRE-FIX | FIXED |
|---|---|---|---|---|
| S1 | `SetEngine._would_cycle`: `if s_type == o_type: return True` (over-eager cycle guard) | remove, `test_remove_sequences and deep_grid` | **GREEN** `1 passed` | RED: `[deep_grid seed=0] set engine: 16 add(s) refused ... expected exactly 2` |
| S2 | `SetEngine._would_cycle`: `return False` (the cycle guard goes quiet) | same | **GREEN** `1 passed` | RED: `set engine: 0 add(s) refused ... expected exactly 2` |
| S4 | `SetEngine._validate`: a plain `ValueError` on `parent` writes from `node1` (an engine bug, not a refusal) | same | **GREEN** `1 passed` | RED: `ValueError: SABOTAGE S4 ...` propagates |
| G1 | `ReachabilityIndex` reverse-reachability pre-check broadened: refuse when `triple is not None` OR the object has any outgoing edge | remove, `-x -k test_graph_remove_sequences` | not run | RED: `[deep_grid seed=0] graph: 6 add(s) refused ... expected exactly 2` |
| S3 | `SetEngine._validate`: refuse every write whose object is `d2` (broad over-reject) | generated, all 40 seeds | **38 of 40 GREEN**; the 2 reds came from `_MIN_ACCEPTED` (every add refused) | RED `40 failed`: `2 of 8 generated add(s) were REFUSED at admission; none are expected (TK71)` |
| S3 | same | enum, `-k boolean_star_exclusion` | (no change to this module) | RED: `zanzibar_utils_v1.AdmissionRejected: SABOTAGE S3` propagates, which confirms § 1 |

What the PRE-FIX column shows: in the old modules, a cycle guard that fires on 8× too many
writes, a cycle guard that never fires, and an engine bug that raises a plain `ValueError` all
left the remove gate green. A broad over-reject left the generated gate green on 38 of 40 seeds.

Instrument note: the `-x` runs stopped at the first red, which was `deep_grid` in both cases
(four corpora sort before it and passed). So S1 and G1 show *that* the pin fires, not every
corpus it would fire on. That is enough, because the pin is the same function for every
corpus.
