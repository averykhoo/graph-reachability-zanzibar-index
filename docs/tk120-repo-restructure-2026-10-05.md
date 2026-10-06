# TK120 -- repo restructure: drop version suffixes and re-lay-out the code (2026-10-05b)

**FROZEN 2026-10-06 (`TK120` closed).** Was an ACTIVE-PLAN (`docs/README.md` §3), opened
2026-10-05b. Live state is `python scripts/task.py show TK120`, never this file. §1-§4 are the
pre-move census and cite the OLD names and line numbers on purpose; §5 is the approved plan;
§6 is what was executed, including where it departed from §5. Corrections are appended dated
at the top, never edited into the body.

## Corrections (newest first)

- **2026-10-06c:** executed; see §6. Two departures from §5: (1) the user asked for ONE
  commit for steps B-D with a single full gate at the end (A was committed on its own,
  `86e3298`); (2) the refused-shape scanner was globbed over the SCHEMA package, not the whole
  library (§6.4).
- **2026-10-06b:** §5 rewritten. The 2026-10-06 draft (flat layout, tables kept) was superseded by user decisions before anything moved: one `src/zanzibar/` package, tables renamed, `legacy/` deleted.

## 1. First-hand checks by the session (READ 2026-10-05b)

The census below (§3, §4) came from two read-only subagents and is evidence, not a finding
(`CLAUDE.md` § Delegation). The session re-checked these claims itself with grep/sed before
writing them down. Everything in §3/§4 not listed here is the AGENT'S claim, labelled by the
agent as FIRST-HAND (it ran the command) or INFERRED.

1. **Goldens are safe for a suffix rename (the row's UNVERIFIED item).** No file under
   `tests/snapshots/` matches `index_v4|zanzibar_utils|_v1|_v4|V4\b|V1\b|legacy`. They DO
   embed the reprs `Filter(`, `Rule(`, `RewriteFilter(`, `RelationalTriplePattern(`, so those
   four class NAMES must not change in this item.
2. **`NodeV2` is dead.** `zanzibar_utils_v1.py::NodeV2` is constructed only by
   `RelationalTriple.node_from` / `node_to`, and neither has a caller (the one other grep hit
   is a docstring in `setengine/engine.py`). The `from legacy.index_v2 import Node` at the
   top of `zanzibar_utils_v1.py` exists only to subclass it. `tests/test_index.py`'s
   `Node as NodeV2` is a DIFFERENT class (an alias of legacy's own `Node`).
3. **The only live product dependency on `legacy/` is `legacy.index_v1.MultiSet`**, used in
   `index_v4/core.py` (two constructions in one function). The legacy v1-v3 indexes are
   imported only by `tests/test_index.py` and `tests/test_integration.py`.
4. **`legacy/index_v3.py` declares SQLModel tables `Node` and `Edge` with no
   `__tablename__`** (so `node` / `edge`), and creates `sqlite:///database.db` at import.
   Every live table sets `extend_existing` (`index_v4/models.py`, `setengine/models.py`,
   `connectedstore/models.py`). The agent's claim that a live table renamed onto
   `node`/`edge` would MERGE silently rather than raise is INFERRED, not run.
5. **Strings a rename tool will not follow (each READ):**
   - `index_v4/models.py::EdgeV4`: `foreign_keys='[EdgeV4.subject_id]'` / `'[EdgeV4.object_id]'`.
   - `tests/test_tk111_stall_aware_freshness.py` and `tests/test_tk112_cap_policy.py`:
     `caplog.at_level('WARNING', logger='index_v4.core')` (agent, INFERRED: a silent no-op after a move).
   - `formal/conformance/test_grid_independence.py::test_the_two_parsers_are_really_different_code`
     asserts `__module__ == "zanzibar_utils_v1"`.
   - `formal/conformance/test_w4fragment_scope_pin.py` / `test_graphadmission_scope_pin.py`
     compare `reported_by` against the literal `"zanzibar_utils_v1.py"`.
   - `tests/test_claim_rot_gate.py` expects `"index_v4/wildcard.py::WildcardIndex.check: BODY CHANGED"`.
   - `tests/test_reg15_security_hardening.py::_GUARDED_MODULES = ['index_v4/core.py', 'index_v4/processor.py']`,
     a silent pass if the files move and the list does not.
   - `tests/test_reads.py` filters SQL text on `'edge_v4'` / `'node_v4'` (only a TABLE rename touches it).
6. **Gate couplings.** `formal/correspondence_anchor_pin.txt` has 153 rows keyed by
   `index_v4/` or `zanzibar_utils_v1.py` (2026-10-05 count). `formal/verify.sh` carries
   `MIN_CONF_ALL` and `MIN_TESTS_ALL` with zero headroom, so moving a test between `tests/`
   and `formal/conformance/` reds one of them.

## 2. Decisions the plan must make (none taken; REASONED from §1, §3, §4)

These come out of the census. The engineering ones are the model's (`CLAUDE.md` "Who
decides"), but the whole plan still needs the user's approval before any move.

- **Target layout and the old -> new name map.** Not started. Check collisions first:
  `Node` already has three claimants, `LookupResult` is defined in both backends, and
  `index_v4/models.py` already exports the unversioned aliases `Node`/`Edge`/`Store`.
- **Class rename vs TABLE rename.** Every table has an explicit `__tablename__`, so classes
  can be renamed with the database untouched. Renaming tables is a PostgreSQL migration for
  any persisted store, and any `_v\d`-stripping regex does it by accident. Decide explicitly.
- **`legacy/`: delete or keep as history.** Re-home `MultiSet` and delete `NodeV2` either way.
  Dropping the legacy test cases needs a deliberate, reviewed `MIN_TESTS_ALL` edit.
- **Split `zanzibar_utils_v1.py` or only move it.** §3 F maps its sections and the two section
  cycles a naive split would hit. A split ALSO silently escapes the fixed-file source
  scanners (§4, silent item 3), so those lists must move in the same step.
- **Rewrite mechanics.** Use a byte-preserving rewrite that keeps each file's CRLF/LF and
  asserts an expected per-file count. Replace the path form (`index_v4/x.py`) BEFORE the
  dotted form (`index_v4.x`). Exclude every FROZEN doc and add a rename table here instead.
  Keep the rename commit free of behaviour changes, because `claim_rot.py --generate` will
  re-pin many rows at once and would launder any change made in the same commit.

## 3. Agent census A: code-side inventory (agent report, transcribed verbatim 2026-10-05b)

Source: `.scratch/tk120-census/code.md`, a read-only general-purpose subagent. The
`.scratch/` copy is deleted after this transcription. Headings are demoted two levels;
nothing else is edited.

### TK120 census -- code (2026-10-05)

Scouting agent, read-only. Sections appended as completed.

#### SUMMARY (filled last, 2026-10-05; every number below is re-derivable from the command cited in its section)

- **Footprint.** 416 tracked files carry a versioned identifier (4253 occurrences): 168 `.py` (1822 occ.), 221 live non-`.py` (2041), 24 FROZEN (382), 3 inside `legacy/`. By name, the heavy hitters are `index_v4` (303 files / 1516 occ.), `zanzibar_utils_v1` (246 / 928), `NodeV4` (84 / 457), `EdgeV4` (79 / 346) and `ResidueV1` (75 / 297). Full table in B.
- **Inventory (A).** 1 root module, 1 package (`index_v4/`, 9 files), `legacy/` (4 files), 3 versioned test filenames, and 11 versioned classes: 10 SQLModel tables plus `NodeV2`. There are no versioned functions or constants. The DB-object strings to decide on separately: 10 `__tablename__`s, 10 constraint/index names, and 5 FK target strings.
- **Already aliased:** `Node`/`Edge`/`Store` = `NodeV4`/`EdgeV4`/`StoreV4` (`index_v4/models.py:200-202`), and tests already use them.
- **Collisions:** `Node` (three claimants), `LookupResult` (defined in both backends), and the legacy v3 TABLES `node`/`edge`. Every live table has `extend_existing=True`, so a table collision would merge silently instead of raising (A4b).
- **Goldens are suffix-safe** (A6). They contain no module, package or versioned names. They do embed the reprs of `Filter`/`Rule`/`RewriteFilter`/`RelationalTriplePattern`.
- **Gate couplings (B1, C4).**
  - 201 anchor-pin rows are keyed by product paths. 65 pin rows have pinned BODIES that mention a versioned name, so a class-only rename reds `verify.sh` step 4d2 on 65 rows.
  - There are 83 string-literal path/module refs that a rename tool will not follow.
  - Four of those can FAIL BY PASSING after a move: `tests/test_reg15_security_hardening.py::_GUARDED_MODULES`, `scripts/handoff_lint.py::MENTION_ROOTS`, and the profiler path filters in `benchmarks/profile_r6*.py`. A table rename would also silently change the meaning of the SQL-substring pins in `tests/test_reads.py:71,:181`.
- **Import graph (C).** Acyclic: `legacy < zanzibar_utils_v1 < setengine < index_v4 < connectedstore`. There is exactly one graph->set-engine edge (`index_v4/bulk_build.py:48` imports `setengine.models.TupleV1`). There are two live->legacy edges.
- **legacy/ (D).** 775 lines. The live code needs only `MultiSet` (29 LOC, used at `index_v4/core.py:808-809`). The other import, `Node` (3 LOC), only feeds `NodeV2`, and **`NodeV2` is DEAD**: its only constructors, `RelationalTriple.node_from`/`node_to`, have zero callers. It can be deleted rather than re-homed. `legacy/index_v3.py` is reachable only from 2 test files, and importing it writes `./database.db`. About 28 test cases are legacy-parametrized (inferred, not collected), so dropping them needs a deliberate `MIN_TESTS_ALL` edit.
- **Sizes (E).** Live product code is 13515 lines (6767 code lines) across 22 files. `zanzibar_utils_v1.py` is 3289 lines with 109 top-level defs. `index_v4/` is 6441 lines, `setengine/` 1929, `connectedstore/` 1856.
- **Schema module seams (F).** It splits into 16 sections.
  - Two section cycles block a naive split: core compile S9 <-> boolean compile S11 (via 3 helpers), and validation S7 <-> core compile S9 (via 3 tiny AST helpers).
  - The JSON front end, unparser, W4Fragment report and GraphAdmission report have no product callers.
  - The 37 `REFUSED SHAPE` blocks spread across 6 sections.

#### A. Inventory of versioned names in LIVE code (excluding legacy/) -- 2026-10-05

Method (FIRST-HAND): `grep -rnE --include='*.py' '^\s*(class|def|async def)\s+\w*([vV][0-9]+|[lL]egacy)\w*'`
and a token census `grep -rhoE '[A-Za-z_][A-Za-z0-9_]*([vV][0-9]+|[lL]egacy|LEGACY)[A-Za-z0-9_]*' connectedstore index_v4 setengine zanzibar_utils_v1.py | sort | uniq -c`.
No versioned `def`, module-level constant, or function exists in product code: only modules, one package, 11 classes, and the DB-object name strings.

##### A1. Modules / packages (FIRST-HAND, `git ls-files | grep -E '[_-]v[0-9]|V[0-9]|legacy'`)
| path | kind |
|---|---|
| `zanzibar_utils_v1.py` | root module (the ONLY root .py) |
| `index_v4/` (9 files: `__init__, bulk_backfill, bulk_build, core, invariants, models, outbox, processor, wildcard`) | package |
| `legacy/` (`__init__, index_v1, index_v2, index_v3`) | package (see D) |
| `tests/test_index_v4.py`, `tests/test_index_v4_core.py`, `tests/test_index_v4_models.py` | test modules with versioned filenames |

##### A2. Classes (FIRST-HAND, line numbers dated 2026-10-05)
| class | definition `file::symbol` (line) | `__tablename__` | other DB-object names in the class (strings) |
|---|---|---|---|
| `StoreV4` | `index_v4/models.py::StoreV4` (:18) | `store_v4` (:23) | -- (FK target `"store_v4.id"` at :40, :78) |
| `NodeV4` | `index_v4/models.py::NodeV4` (:31) | `node_v4` (:32) | `node_v4_unique_constraint` (:35); FK target `"node_v4.id"` at :79, :80, :112 |
| `EdgeV4` | `index_v4/models.py::EdgeV4` (:61) | `edge_v4` (:62) | `edge_v4_unique_constraint` (:64), `ix_edge_v4_store_object` (:68) |
| `ResidueV1` | `index_v4/models.py::ResidueV1` (:93) | `residue_v1` (:104) | `residue_v1_unique` (:106) |
| `ResidueRefV1` | `index_v4/models.py::ResidueRefV1` (:124) | `residue_ref_v1` (:147) | `residue_ref_v1_unique` (:153), `ix_residue_ref_v1_store_object` (:157) |
| `DeltaOutboxV1` | `index_v4/models.py::DeltaOutboxV1` (:167) | `delta_outbox_v1` (:178) | `ix_delta_outbox_v1_store_id_id` (:183) |
| `TupleV1` | `setengine/models.py::TupleV1` (:19) | `tuple_v1` (:25) | `tuple_v1_unique` (:28) |
| `SchemaV4` | `connectedstore/models.py::SchemaV4` (:24) | `schema_v4` (:25) | -- |
| `TupleLogV1` | `connectedstore/models.py::TupleLogV1` (:34) | `tuple_log_v1` (:35) | `ix_tuple_log_v1_store_id_id` (:41) |
| `IndexCursorV1` | `connectedstore/models.py::IndexCursorV1` (:57) | `index_cursor_v1` (:58) | `index_cursor_v1_unique` (:60) |
| `NodeV2` | `zanzibar_utils_v1.py::NodeV2` (:195), a frozen dataclass subclassing `legacy.index_v2.Node` | not a table | -- |

INFERRED: `Field(index=True)` columns also get SQLAlchemy auto-named indexes `ix_<table>_<col>` (e.g. `ix_node_v4_store_id`), so a TABLE rename renames those too; a CLASS-only rename touches none of them.

FIRST-HAND: table names appear in product code OUTSIDE `models.py` only in docstrings/comments (no raw SQL):
`grep -rnwE 'store_v4|node_v4|edge_v4|residue_v1|residue_ref_v1|delta_outbox_v1|tuple_v1|schema_v4|tuple_log_v1|index_cursor_v1' connectedstore index_v4 setengine zanzibar_utils_v1.py | grep -v /models.py`
-> 5 hits: `index_v4/core.py:1081`, `index_v4/outbox.py:39`, `index_v4/processor.py:1406`, `index_v4/wildcard.py:190`, `:793` -- all prose.

##### A3. Unversioned ALIASES that already exist (FIRST-HAND) -- not on the task row
- `index_v4/models.py:200-202`: `Node = NodeV4`, `Edge = EdgeV4`, `Store = StoreV4`, re-exported from `index_v4/__init__.py` (`__all__` carries both spellings).
  Tests already use the alias form, e.g. `tests/test_admission_rejected.py:32 from index_v4 import ReachabilityIndex, Store`.
- No aliases exist for `ResidueV1`, `ResidueRefV1`, `DeltaOutboxV1`, `TupleV1`, `SchemaV4`, `TupleLogV1`, `IndexCursorV1`.

##### A4. NAME COLLISIONS the suffix drop would create (FIRST-HAND reads, consequence INFERRED)
- **`Node`**: `index_v4.models.Node` (= `NodeV4`, SQLModel row) vs `legacy.index_v2.Node` (dataclass; imported by `zanzibar_utils_v1.py:8 from legacy.index_v2 import Node` and subclassed by `NodeV2`), and `NodeV2` itself would also want to be `Node`. Three things want one name.
  `tests/test_index.py:5` already imports `from legacy.index_v2 import ... Node as NodeV2` (a local alias shadowing the real `zanzibar_utils_v1.NodeV2` name).
- **`LookupResult`**: defined in both `index_v4/wildcard.py` and `setengine/engine.py` (both exported from their package `__init__`). Pre-existing, not version-related, but a merge-into-one-package layout would hit it.
- **`Tuple` / `Schema`**: `TupleV1 -> Tuple` would shadow `typing.Tuple` if anyone does `from typing import Tuple` in the same module (INFERRED; not grepped per file).

##### A5. Other version-ish names NOT listed on the row (FIRST-HAND)
Product code: none beyond A1-A2 plus the DB-object strings in A2. The helper `index_v4/outbox.py::drain_deltas` is documented as a "back-compat helper ... legacy delta list" (:88) -- a legacy-shaped API without a versioned name.
Non-product (`grep -rhoE ... tests formal scripts benchmarks docs/design`):
| name | site | note |
|---|---|---|
| `IndexV1Polyfill`, `IndexV2Polyfill`, `IndexV3Polyfill`, `IndexV4Polyfill` | `tests/test_index.py::IndexV{1..4}Polyfill` (:20,:34,:48,:64) | parametrize the legacy generations (see D) |
| `DirectedAcyclicMultiGraphReachabilityIndexV2` | defined `legacy/index_v2.py`, used `tests/test_index.py:5,:36` | legacy class |
| `_import_v4` | `tests/test_index_v4.py::_import_v4` (:12), 4 call sites | test helper |
| `_legacy_oracle` | `tests/test_tk108_userset_tupleset_rewrite.py::_legacy_oracle` (:122) | "legacy" = pre-TK108 schema, unrelated to `legacy/` |
| `test_swarm_all_on_stratum_covers_the_legacy_shape`, `test_outbox_stream_matches_legacy_flips`, `test_legacy_head_based_ids_cannot_match_a_content_address` | tests | "legacy" in the English sense |
| `info_v2`, `div2`, `div3` | `tests/test_wildcard_migration.py:36`, misc | local variables, not version markers |
| `W4Fragment`, `w4_fragment_report` | Lean / `zanzibar_utils_v1.py` | "W4" is a fragment NAME, not a version; regex `[vV][0-9]` does not match it, flagged only because a reader may mistake it |

##### A6. Goldens (FIRST-HAND) -- resolves the row's UNVERIFIED item
`tests/snapshots/` = 15 files (`compiled_ruleset/*.fga.txt`). `grep -rcE 'zanzibar_utils|index_v|[A-Z][a-z]+V[0-9]|_v[0-9]|legacy|module|<' tests/snapshots` -> 0 in every file.
They DO embed class reprs: `Filter(` 164, `Rule(` 83, `RewriteFilter(` 13, `RelationalTriplePattern(` 343 occurrences. So: suffix renames are golden-safe; renaming any of those four classes (or changing their dataclass field names) breaks byte identity.

##### A4b. TABLE-name collision with legacy v3 (FIRST-HAND read; consequence INFERRED) -- important
`legacy/index_v3.py::Node` (:25) and `legacy/index_v3.py::Edge` (:42) are `SQLModel, table=True` with NO explicit `__tablename__`, so SQLModel names them `node` / `edge`, with constraints `node_unique_constraint` / `edge_unique_constraint` and FK `"node.id"`. They register in the SAME global `SQLModel.metadata` as the live tables. Module import also runs `engine = create_engine('sqlite:///database.db')` + `SQLModel.metadata.create_all(engine)` (:59-61) -- i.e. importing `legacy.index_v3` writes `./database.db` in the CWD (that is the gitignored root `database.db`, `.gitignore:316`).
Consequence (INFERRED): renaming the live TABLES to `node`/`edge` (dropping `_v4`) would collide with legacy v3 in `SQLModel.metadata` in any pytest process that imports `legacy.index_v3` (`tests/test_index.py`, `tests/test_integration.py`, see D) -- and `NodeV4`'s constraint name would sit beside v3's near-identical one. Even a CLASS-only rename to `Node`/`Edge` is fine for SQLAlchemy (class registry is per-name but the string-relationship `'[Edge.subject_id]'` in v3 resolves through the declarative class registry -- a second mapped class named `Edge` makes that string AMBIGUOUS; INFERRED, not tested). So either v3 leaves the import path, or live classes keep distinct names.
**Worse than a loud error (FIRST-HAND `git grep -n extend_existing`): EVERY live table sets `__table_args__ ... {'extend_existing': True}`** (`index_v4/models.py:24,36,69,107,158,184`, `setengine/models.py:29`, `connectedstore/models.py:26,42,61`). INFERRED (SQLAlchemy semantics, not run): with `extend_existing`, declaring a live table named `node` after v3's `node` is registered does NOT raise "already defined" -- it silently MERGES the live columns/constraints into v3's Table object. A table rename that lands on `node`/`edge` while v3 is importable is therefore a fails-by-passing hazard, not a loud one. Same for any two live tables renamed onto one name.

#### B. Reference counts -- 2026-10-05 (FIRST-HAND: python census over `git ls-files`, word-boundary regex `\bNAME\b`, utf-8 errors=ignore)

Cells are `files/occurrences`; `.` = 0. Tracked files only (untracked `__pycache__`, `database.db` excluded). Areas:
prod = `index_v4/ setengine/ connectedstore/ zanzibar_utils_v1.py`; legacy = `legacy/`; tests = `tests/` minus `tests/conftest.py`;
f.conf = `formal/conformance/`; f.lean = `*.lean` outside `formal/history`; f.CORR = `formal/CORRESPONDENCE.md`; f.pin = `formal/correspondence_anchor_pin.txt`;
f.aud = `formal/audited_theorems.txt`; f.verify = `formal/verify.sh`; f.probes = `formal/probes/*.py` (41 dated probe scripts -- not on the task's list, they import product code);
f.other = rest of `formal/` (FINAL_REVIEW/HANDOFF/README/ARCHITECTURE/SEMANTICS/REFERENCES.md, headline_*.txt, lakefile, *.sh);
docs.live = `docs/` minus history/specs (includes `docs/design/generator-coverage/prototypes/*.py`); FROZEN = `docs/history/ + formal/history/ + docs/specs/`;
config = `pytest.ini pyrefly.toml requirements.txt .gitignore .gitattributes tests/conftest.py`. (No setup.py / pyproject.toml exists.)

| name | prod | legacy | tests | f.conf | f.lean | f.CORR | f.pin | f.aud | f.verify | f.probes | f.other | scripts | bench | docs.live | FROZEN | tasks.open | tasks.closed | CLAUDE.md | HANDOFF.md | README.md | config | TOTAL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `zanzibar_utils_v1` | 11/16 | . | 72/140 | 16/130 | 24/89 | 1/57 | 1/52 | . | . | 11/26 | 4/22 | . | 5/9 | 46/202 | 15/93 | 6/16 | 30/59 | 1/5 | 1/1 | 1/10 | 1/1 | 246/928 |
| `index_v4` | 10/36 | 2/4 | 67/220 | 8/43 | 36/186 | 1/134 | 1/101 | . | . | 16/31 | 5/19 | 2/2 | 9/60 | 50/319 | 19/142 | 24/80 | 51/124 | 1/5 | . | 1/10 | . | 303/1516 |
| `legacy.` / `legacy/` | 2/2 | 2/2 | 3/8 | . | . | . | . | . | . | . | . | 1/1 | . | 3/3 | 2/3 | 1/4 | . | 1/3 | . | 1/2 | . | 16/28 |
| `index_v1` | 1/1 | 2/2 | 1/1 | . | . | . | . | . | . | . | . | . | . | . | 1/1 | 1/1 | . | 1/1 | . | . | . | 7/7 |
| `index_v2` | 1/1 | . | 1/1 | . | . | . | . | . | . | . | . | . | . | . | 1/1 | 1/1 | . | 1/1 | . | . | . | 5/5 |
| `index_v3` | . | . | 2/5 | . | . | . | . | . | . | . | . | . | . | . | 2/3 | 1/1 | . | . | . | . | . | 5/9 |
| `StoreV4` | 5/17 | . | 5/16 | . | . | . | . | . | . | . | . | . | 1/1 | 7/12 | 1/1 | 2/2 | 1/1 | . | . | 1/1 | . | 23/51 |
| `NodeV4` | 9/153 | . | 23/109 | 4/37 | 3/6 | 1/11 | 1/1 | . | . | 3/10 | 3/18 | . | 6/20 | 11/46 | 9/28 | 6/13 | 4/4 | . | . | 1/1 | . | 84/457 |
| `EdgeV4` | 9/81 | . | 13/50 | 6/45 | 1/1 | 1/9 | 1/1 | . | . | 2/8 | 3/13 | . | 5/19 | 14/65 | 11/29 | 5/12 | 6/10 | 1/2 | . | 1/1 | . | 79/346 |
| `ResidueV1` | 7/41 | . | 17/90 | 4/18 | 1/2 | 1/6 | 1/1 | . | . | 1/9 | 3/13 | . | 3/12 | 13/50 | 12/35 | 5/10 | 5/8 | 1/1 | . | 1/1 | . | 75/297 |
| `ResidueRefV1` | 6/34 | . | 3/33 | . | . | 1/3 | 1/1 | . | 1/1 | . | . | . | 1/2 | 7/28 | 2/2 | 2/2 | 2/3 | . | . | . | . | 26/109 |
| `DeltaOutboxV1` | 6/23 | . | 7/28 | . | 1/1 | 1/2 | 1/1 | . | . | . | . | . | 3/9 | 8/19 | 6/7 | 2/2 | . | 1/1 | . | 1/2 | . | 37/95 |
| `TupleV1` | 10/56 | . | 13/50 | 3/13 | . | 1/1 | . | . | . | 1/4 | 1/1 | . | 5/15 | 11/20 | 6/17 | 1/1 | 1/1 | 1/4 | . | 1/4 | . | 55/187 |
| `SchemaV4` | 4/29 | . | 3/13 | . | . | . | . | . | 1/1 | . | 2/2 | . | . | 7/15 | 3/6 | 2/3 | . | 1/2 | . | 1/1 | . | 24/72 |
| `TupleLogV1` | 6/42 | . | 8/26 | . | . | 1/1 | . | . | . | . | . | . | 1/1 | 8/13 | 5/11 | 1/1 | 3/4 | 1/1 | . | 1/2 | . | 35/102 |
| `IndexCursorV1` | 4/16 | . | 1/2 | . | . | . | . | . | . | . | . | . | 1/1 | 4/7 | 3/3 | 1/1 | 2/2 | 1/1 | . | . | . | 17/33 |
| `NodeV2` | 1/3 | . | 1/7 | . | . | . | . | . | . | . | . | . | . | . | . | 1/1 | . | . | . | . | . | 3/11 |
| (any of the 10 table-name strings) | 7/21 | . | 6/11 | . | . | 1/1 | . | . | . | . | . | . | 7/104 | 6/19 | 6/17 | 2/3 | 2/3 | . | . | . | . | 37/179 |

Caveats (FIRST-HAND): `\bindex_v4\b` does NOT match `test_index_v4` (no word boundary), so the 3 versioned test filenames are counted only where written as paths with `index_v4` after a non-word char. `legacy.`/`legacy/` counts only module-path uses; the English word "legacy" is far more common and was not counted. f.lean hits are COMMENT/docstring citations of Python paths (Lean imports nothing from Python), but see B2.

##### B1. Gate-machinery couplings (FIRST-HAND)
- `formal/correspondence_anchor_pin.txt` (503 lines; rows `<file>::<symbol> TAB <kind> TAB <sha>`): **201 rows are keyed by a product path** -- `zanzibar_utils_v1.py` 52, `index_v4/processor.py` 41, `setengine/engine.py` 33, `index_v4/wildcard.py` 25, `index_v4/core.py` 21, `setengine/memberset.py` 7, `index_v4/models.py` 5, `index_v4/invariants.py` 4, `index_v4/outbox.py` 3, `connectedstore/{apply,build,source,store}.py` 2 each, `index_v4/bulk_{build,backfill}.py` 1 each
  (`grep -vE '^#' formal/correspondence_anchor_pin.txt | grep -E '^(index_v4|setengine|connectedstore|zanzibar_utils_v1|legacy)' | sed 's/::.*//' | sort | uniq -c`). Any module MOVE re-keys those rows; `setengine/*` rows (40) only re-key if setengine moves.
- **Class renames ALSO move pin HASHES, not just keys**: of 255 `.py` pin rows, **65 have a pinned body (via `formal/conformance/claim_rot.py::anchor_body`) that names a versioned identifier** -- by file: processor 14, core 12, wildcard 10, models 5, conformance extractor 3, invariants 3, connectedstore apply/build 2 each, outbox 2, conformance backends/test_conformance_fragment/test_conformance_state 2 each, source/bulk_build/setengine engine/test_graphadmission_scope_pin/test_grid_independence/tests/test_bulk_build 1 each; by name: NodeV4 30, EdgeV4 15, ResidueV1 10, zanzibar_utils_v1 7 (local imports inside bodies), ResidueRefV1 6, DeltaOutboxV1 6, index_v4 4, TupleV1 3, TupleLogV1/IndexCursorV1/StoreV4 2, SchemaV4 1.
  So a class rename reds `verify.sh` step 4d2 on 65 rows even with no file move; the pin's own header says regenerate only after RE-READING the cited CORRESPONDENCE rows (`python formal/conformance/claim_rot.py --generate`).
- `formal/verify.sh`: no `zanzibar_utils_v1`/`index_v4` path literal (FIRST-HAND grep -> only comment mentions of `ResidueRefV1` :492, `SchemaV4` :667, and "legacy split" = conf-heavy/conf-rest, unrelated to `legacy/`). Its anchor resolution goes through `formal/conformance/anchor_check.py` + `claim_rot.py`, which read paths from CORRESPONDENCE.md.
- `pytest.ini:38`: comment only; the filter is "matched by message prefix because a dotted category here would make pytest import the module at config time" (pytest.ini:40-41, FIRST-HAND) -- so no module path to update there.
- **SQL-text substring matching on TABLE names** (silently changes meaning under a TABLE rename; harmless under a class-only rename):
  `tests/test_reads.py:71` (`'edge_v4' in s.lower()`), `tests/test_reads.py:181` (`'node_v4' in ... and 'edge_v4' not in ...`), `benchmarks/profile_r6.py:173-176, :390-412` (same, with an `INSTRUMENT BROKEN` floor assert at :405). Renaming tables to `node`/`edge` would make `'node' in s` match far more statements -- the R6-6 "ONE node statement per check" pin could pass or fail for the wrong reason (INFERRED).
- `tests/test_fuzz_names.py:36` embeds `"rob'); DROP TABLE node_v4; --"` as a fuzz NAME -- data, not a reference; harmless.

#### C. Import graph, product code only -- 2026-10-05 (FIRST-HAND: `ast.walk` over every product .py, top-level AND function-local imports)

##### C1. Package level
```
connectedstore ──> index_v4, setengine, zanzibar_utils_v1
index_v4       ──> zanzibar_utils_v1, setengine (ONE edge), legacy (ONE edge)
setengine      ──> zanzibar_utils_v1
zanzibar_utils_v1 ──> legacy (ONE edge)
legacy         ──> (itself only)
```
**No cycles.** Layering is: `legacy` < `zanzibar_utils_v1` < `setengine` < `index_v4` < `connectedstore`.
Cross-package statements (file:line, 2026-10-05):
- `index_v4/core.py:11 from legacy.index_v1 import MultiSet`; `zanzibar_utils_v1.py:8 from legacy.index_v2 import Node` -- the only two live->legacy edges.
- `index_v4/bulk_build.py:48 from setengine.models import TupleV1` -- the ONLY graph->set-engine edge: the bulk builder reads the set engine's tuple TABLE. So "the two backends never import each other" is not literally true; `setengine/models.py::TupleV1` is shared storage, not set-engine logic (INFERRED: a natural candidate for a shared/storage module in a re-layout).
- `index_v4` -> `zanzibar_utils_v1`: `core.py:12` (AdmissionRejected, ClosureFanoutExceeded, PathCountExceeded, validate_write_identifiers, validate_node_identifiers), `wildcard.py:25` (AdmissionRejected, SchemaInfo, norm_pred, validate_*_identifiers), `processor.py:30` (CompiledBooleans, DerivedFamily, LeafFamily), `bulk_build.py:49` (Entity, PathCountExceeded, RelationalTriple, RuleSet, norm_pred) + `:57` LOCAL SchemaInfo, `bulk_backfill.py:40` LOCAL (CompiledBooleans, SchemaInfo), `invariants.py:90` LOCAL SchemaInfo.
- `setengine/engine.py:18` imports 20 names from `zanzibar_utils_v1`: AdmissionRejected, CyclicDerivedDependency, DoublyBridgedShapeError, wildcard_userset_restriction_shapes, Entity, RelationalTriple, norm_pred, parse_schema_ast, derive_schema_info, schema_filters, compile_ruleset, validate_write_identifiers, UnsupportedByGraphIndex, Direct, Computed, TTU, Union, Intersection, Exclusion. (Note: the set engine imports `compile_ruleset` and `UnsupportedByGraphIndex` -- the graph-index compiler -- INFERRED to be for the "graph refuses" admission parity, TK116.)
- `connectedstore` -> others: `apply.py:23-27`, `build.py:24-29` (EdgeV4, NodeV4, ResidueRefV1, ResidueV1, TupleV1, bulk_build, DeltaProcessor), `schema_io.py:18-21` (StoreV4, ReachabilityIndex, WildcardIndex, SetEngine, SetOps, parse_openfga_schema, RuleSet), `source.py:44-46` (`index_v4.core.is_sqlite`, `take_row_write_lock` -- the dialect seam lives in index_v4/core.py), `store.py:27-32`.
- `tests/oracle.py` imports only stdlib (`re`, `dataclasses`, `types`, `typing`) -- independence contract holds (FIRST-HAND `grep -nE '^(from|import) ' tests/oracle.py`).

##### C2. Intra-package module graph (FIRST-HAND, AST)
- `index_v4`: `outbox->models`; `invariants->models,outbox`; `core->invariants,models`; `wildcard->core,models`; `processor->invariants,models,outbox,wildcard`; `bulk_backfill->invariants`; `bulk_build->bulk_backfill,invariants,models`. Acyclic; `models` is the leaf, `processor` the top.
- `setengine`: `memberset->setops`; `engine->memberset,models,setops`. Acyclic.
- `connectedstore`: `schema_io->models`; `source->models,schema_io`; `apply->models,source`; `build->apply,models,schema_io,source`; `store->apply,schema_io,source,models(LOCAL)`. Acyclic.

##### C3. Import STYLES across the whole tracked tree (FIRST-HAND, AST over `git ls-files '*.py'`)
`from index_v4... import` 178 stmts; `from zanzibar_utils_v1... import` 147; `from legacy... import` 11; `import index_v4 as X` 10; `import zanzibar_utils_v1 as X` 9; `import zanzibar_utils_v1` 3; `import index_v4` 2.

##### C4. STRING-LITERAL path/module references a rename tool will NOT follow (FIRST-HAND, AST: non-docstring str constants matching `\b(zanzibar_utils_v1|index_v4|legacy)[./]`) -- 83 literals
Gate-relevant ones, each a "fails red" or (worse) a "fails by PASSING" after a move:
- `tests/test_refused_shape_comments.py::FILES` / `::MIN_HEADERS` = `{'zanzibar_utils_v1.py': 37, 'tests/oracle.py': 16, 'setengine/engine.py': 1}` -- zero-headroom per-FILE floor. A split of the schema module redistributes the 37 `REFUSED SHAPE` blocks across new files, and new files are not scanned unless added to `FILES` (INFERRED: a split goes RED here, loudly, because the old file falls below 37; the fix is new per-file FILES/MIN_HEADERS entries summing to 37, not a lowered floor).
- `tests/test_tk116_oracle_only_setengine.py::_SRC` = `.../'zanzibar_utils_v1.py'` (counts `raise UnsupportedByGraphIndex|CyclicDerivedDependency` sites there, :194/:249).
- `tests/test_reg15_security_hardening.py::_GUARDED_MODULES = ['index_v4/core.py', 'index_v4/processor.py']` (:109; "safety checks survive `python -O`"). **FAILS BY PASSING risk**: code moved into a new file is silently unguarded.
- `scripts/handoff_lint.py::MENTION_ROOTS` (:283) hardcodes `'index_v4/', 'setengine/', 'connectedstore/', 'legacy/'` -- the doc path-mention check. **FAILS BY PASSING risk**: a new package root not added here means stale doc mentions of its paths go unchecked.
- `formal/conformance/test_graphadmission_scope_pin.py` (15 `zanzibar_utils_v1.py::<sym>` literals, :158-:297, :415-417) and `formal/conformance/test_w4fragment_scope_pin.py` (21 literals, :240-:393, :659-660) -- resolve `file::symbol` and assert a callable.
- `formal/conformance/test_conformance_nary_strata.py:351,:353` (`'zanzibar_utils_v1.parse_schema_ast'`, `'...parse_openfga_schema'`), `:424` (regex over `zanzibar_utils_v1._plan_leaves`, with an ANTI-VACUITY guard).
- `formal/conformance/test_grid_independence.py:79` (`'zanzibar_utils_v1'` module name in an independence check), `formal/conformance/test_conformance_fragment.py:287` (message text).
- `tests/test_claim_rot_gate.py:142-200` -- uses `index_v4/wildcard.py::WildcardIndex.check` and `index_v4/models.py::EdgeV4` as sabotage subjects.
- **Logger names**: `index_v4/core.py:19 _log = logging.getLogger(__name__)`; `tests/test_tk111_stall_aware_freshness.py:138` and `tests/test_tk112_cap_policy.py:134` capture `logger='index_v4.core'`. A move changes the logger name (caplog would then capture nothing -> those asserts on warnings go red, INFERRED), and any operator logging config keyed on `index_v4.core` breaks.
- `benchmarks/profile_r6.py:332-336`, `benchmarks/profile_r6_write.py:92-567` (21 literals): profiler frame filters by FILE PATH (`'index_v4/processor.py'` etc.) -- after a move the attribution silently reads zero (INFERRED; benchmarks are not in the gate).
- `formal/probes/tk77_generator_reach_sweep_2026-09-19.py:47`, `tk87_churn_sweep_2026-09-19.py:47`: dated probes, path literal `'index_v4/wildcard.py'`.
- `tests/test_tasktool.py:529`: fixture text only, harmless.

#### D. legacy/ -- 2026-10-05

Sizes (FIRST-HAND `wc -l legacy/*.py`): `__init__.py` 7, `index_v1.py` 170, `index_v2.py` 210, `index_v3.py` 388 -- **775 total**.
Top-level defs (FIRST-HAND `grep -nE '^(class|def|[A-Za-z_]+ =)' legacy/*.py`): v1 `MultiSet` :6, `DirectedAcyclicMultiGraphReachabilityIndex` :37; v2 `Node` :10, `DirectedAcyclicMultiGraphReachabilityIndexV2` :15, `random_test` :156; v3 `Node` (table) :25, `Edge` (table) :42, `engine` :59, `_add_db_edges_unsafe` :64, `_add_direct_edge_unsafe` :132, `node` :219, `add_edge` :250, `remove_edge` :276, `remove_node` :305, `check_reachable` :313, `lookup_reachable` :338, `lookup_reverse` :353.

##### D1. Every import of legacy outside legacy/ (FIRST-HAND `git grep -nE '(from|import) legacy' -- '*.py' ':!legacy/'`)
| importer | symbol | live? |
|---|---|---|
| `index_v4/core.py:11` | `legacy.index_v1.MultiSet` | LIVE product |
| `zanzibar_utils_v1.py:8` | `legacy.index_v2.Node` | LIVE product |
| `tests/test_index.py:4-6` | v1 `DirectedAcyclicMultiGraphReachabilityIndex`; v2 `DirectedAcyclicMultiGraphReachabilityIndexV2`, `Node as NodeV2`; v3 `engine, add_edge, remove_edge, check_reachable` | test |
| `tests/test_integration.py:4-7` | v3 `engine, add_edge, remove_edge, check_reachable` (aliased `v3_*`) | test |
No `formal/`, `scripts/`, `benchmarks/` or `docs/**/*.py` file imports legacy (same grep, 0 other hits). Non-import tooling coupling: `scripts/handoff_lint.py::MENTION_ROOTS` lists `'legacy/'` (:283).

##### D2. What would need re-homing (FIRST-HAND)
- **`MultiSet`** (`legacy/index_v1.py:6-34`, **29 LOC**, a `Counter` subclass that raises on non-int / negative values and deletes on 0, and forbids `__neg__`). Live use: exactly two constructions, `index_v4/core.py:808-809` (`reachable_before_subject` / `reachable_after_object` in the batch expansion beside the security-critical cycle guard at :824-830). Its negative-count refusal is a (weak) safety property of that path -- INFERRED it should move with its semantics intact, not be replaced by a plain `Counter`.
- **`Node`** (`legacy/index_v2.py:9-11`, **3 LOC**: a frozen slotted dataclass with one field `name: str`). Live use: ONLY as the base class of `zanzibar_utils_v1.py::NodeV2` (:194-198, 5 LOC).
- **SURPRISE -- `NodeV2` is dead in live code.** Its only constructors are `zanzibar_utils_v1.py::RelationalTriple.node_from` (:221) and `::RelationalTriple.node_to` (:227), and `git grep -nwE 'node_from|node_to' -- '*.py' ':!legacy/'` returns only those two `def`s plus a docstring mention at `setengine/engine.py:733`. No caller anywhere (tests/formal/benchmarks included). So the legacy `Node` import, `NodeV2`, and both properties can be DELETED rather than re-homed (FIRST-HAND: also confirmed with the non-word grep `git grep -n "node_from\|node_to" -- ":!legacy/"` -- same 3 lines, so no string/getattr use either, across ALL tracked files incl. docs).
  `tests/test_index.py:5` aliases `legacy.index_v2.Node as NodeV2` -- a DIFFERENT class from `zanzibar_utils_v1.NodeV2`, same name.

##### D3. Reachability of the rest of legacy/ from live code (FIRST-HAND)
- Importing `zanzibar_utils_v1` executes `legacy/index_v2.py` in full, which imports `legacy/index_v1.py` in full (`legacy/index_v2.py:6`). Both have only `class`/`def`/imports at module level plus `if __name__ == '__main__':` (v1 :160, v2 :202) -- no import-time side effects.
- `legacy/index_v3.py` is NOT reachable from product code; only `tests/test_index.py` and `tests/test_integration.py` import it. It HAS import-time side effects: `create_engine('sqlite:///database.db')` + `SQLModel.metadata.create_all(engine)` (:59-61) -> writes `database.db` in the CWD (untracked `database.db` at root AND `tests/database.db` both exist, both gitignored by `.gitignore:316`), and registers tables `node` / `edge` in the shared `SQLModel.metadata` (see A4b). Every test that later calls `SQLModel.metadata.create_all(...)` on its own engine (e.g. `tests/test_integration.py::V4Backend.__init__`, :67) also creates the v3 tables when v3 was imported first (INFERRED).
- Legacy-dependent tests (INFERRED from source, NOT collected -- pytest not run per instructions): `tests/test_index.py` 7 `test_` functions x fixture params `[IndexV1Polyfill, IndexV2Polyfill, IndexV3Polyfill, IndexV4Polyfill]` (:94) = 28 cases, 21 of them legacy; `tests/test_integration.py` 11 `test_` functions, `backend` fixture `params=["v3", "v4"]` (:141); 7 of the 11 take `backend` (:188,:237,:277,:307,:324,:344,:390) -> 7 `[v3]` cases. Total legacy-param cases INFERRED = 21 + 7 = **28**. Deleting legacy therefore drops ~28 collected tests, which reds the zero-headroom `MIN_TESTS_ALL` floor -- a deliberate floor edit is part of that step. Get the real number with `pytest tests/test_index.py tests/test_integration.py -q --collect-only` when the gate is free.
- `tests/test_integration.py::V4WildcardBackend` (:97) exists but the `backend` fixture only parametrizes `"v3","v4"` (:141) -- FIRST-HAND; it is used directly by three non-parametrized tests (:443, :477, :507), so those 3 tests are v4-only.
- Frozen-doc cites of legacy paths: `docs/history/session-log.md:772,:774`, `docs/history/handoff-status-2026-07.md:1207`; live docs: `CLAUDE.md:328-331`, `README.md:73,:653`, `docs/architecture/overview.md:71`, `docs/spec-deviations.md:3733`, `docs/tk107-...:60`.

#### E. Sizes -- 2026-10-05 (FIRST-HAND, python over the files; `lines` = newline count = `wc -l`; *code lines = non-blank, non-comment-only, excluding module/class/function docstring lines)

| module | lines (wc -l) | code lines* | top-level class/def |
|---|---|---|---|
| `connectedstore/__init__.py` | 44 | 35 | 0 |
| `connectedstore/apply.py` | 191 | 75 | 3 |
| `connectedstore/build.py` | 281 | 135 | 6 |
| `connectedstore/models.py` | 77 | 38 | 3 |
| `connectedstore/schema_io.py` | 111 | 61 | 6 |
| `connectedstore/source.py` | 641 | 202 | 8 |
| `connectedstore/store.py` | 511 | 188 | 3 |
| `index_v4/__init__.py` | 22 | 18 | 0 |
| `index_v4/bulk_backfill.py` | 767 | 525 | 3 |
| `index_v4/bulk_build.py` | 400 | 228 | 4 |
| `index_v4/core.py` | 1320 | 638 | 12 |
| `index_v4/invariants.py` | 861 | 466 | 20 |
| `index_v4/models.py` | 202 | 99 | 7 |
| `index_v4/outbox.py` | 93 | 38 | 4 |
| `index_v4/processor.py` | 1671 | 794 | 5 |
| `index_v4/wildcard.py` | 1105 | 527 | 2 |
| `legacy/__init__.py` | 7 | 0 | 0 |
| `legacy/index_v1.py` | 170 | 120 | 2 |
| `legacy/index_v2.py` | 210 | 144 | 3 |
| `legacy/index_v3.py` | 388 | 279 | 11 |
| `setengine/__init__.py` | 20 | 11 | 0 |
| `setengine/engine.py` | 1656 | 854 | 10 |
| `setengine/memberset.py` | 150 | 55 | 11 |
| `setengine/models.py` | 43 | 18 | 1 |
| `setengine/setops.py` | 60 | 27 | 1 |
| **`zanzibar_utils_v1.py`** | **3289** | **1735** | **109** |
| `tests/oracle.py` (for comparison: the independent twin) | 764 | 468 | 23 |

| package | files | lines | code lines |
|---|---|---|---|
| `index_v4/` | 9 | 6441 | 3333 |
| `zanzibar_utils_v1.py` | 1 | 3289 | 1735 |
| `setengine/` | 5 | 1929 | 965 |
| `connectedstore/` | 7 | 1856 | 734 |
| `legacy/` | 4 | 775 | 543 |
| **live product total (excl. legacy)** | 22 | 13515 | 6767 |

Observations (FIRST-HAND numbers, INFERRED reading): the root module is the single largest file in the repo's product code (2x `index_v4/processor.py`), ~50% docstring/comment. The three `models.py` files total 322 lines (202+43+77) and hold all 10 tables.

#### F. Seams in `zanzibar_utils_v1.py` -- line ranges DATED 2026-10-05 (FIRST-HAND: `ast` top-level walk + the file's own banner comments)

3289 lines, 109 top-level class/def (E). The file has its own banners at :11-13 (identifiers), :646-648 ("Expression AST + recursive-descent parser"), :694 `---- leaves ----`, :727 `---- operators ----`, :2044-2046 ("Boolean derived-predicate compilation", sub-banners :2057 plan nodes, :2119 compiled artifacts, :2199 taint, :2304 plan construction, :2474 executable plans, :2529 deps/strata), :2725 JSON front end, :2948 unparser, :3009-3011 W4Fragment report, :3188-3190 GraphAdmission report.
Imports: stdlib only (`re, warnings, dataclasses, functools.reduce, types.EllipsisType, typing.Callable`, and a mid-file `import json as _json` at :2733) plus `from legacy.index_v2 import Node` (:8).

| sec | lines | contents (top-level, with def line) | used OUTSIDE the module (files: prod/tests/formal/other) |
|---|---|---|---|
| S1 identifiers + admission errors | 11-178 | `IDENTIFIER_CHARSET` :23, `_IDENTIFIER_RE` :32, `AdmissionRejected(ValueError)` :35-81, `IndexResourceLimit` :84, `PathCountExceeded` :96, `ClosureFanoutExceeded` :110, `is_valid_identifier` :138, `_require` :147, `validate_write_identifiers` :160, `validate_node_identifiers` :174 | AdmissionRejected 4/6/3/0, PathCountExceeded 2/3/0/0, ClosureFanoutExceeded 1/4/0/0, validate_write_identifiers 3/2/0/0, IndexResourceLimit 1/1, validate_node_identifiers 2/0, is_valid_identifier 0/2 |
| S2 triple / pattern / rule data model | 180-371 | `Entity` :182, `NodeV2(Node)` :195 (DEAD, see D2), `RelationalTriple` :202 (with dead `node_from`/`node_to`), `EntityPattern` :234, `RelationalTriplePattern` :268, `Filter` :338, `RewriteFilter(Filter)` :346, `Rule` :363 | Entity 4/27/2/4, RelationalTriple 4/27/2/4, Rule 0/2/1, EntityPattern 0/2, RelationalTriplePattern 0/2, RewriteFilter 0/1, Filter 0/1. **Filter/Rule/RewriteFilter/RelationalTriplePattern reprs are in the goldens (A6).** |
| S3 SchemaInfo + RuleSet | 373-576 | `SchemaInfo` :375-429, `RuleSet` :433-576 (`compiled: 'CompiledBooleans or None'` string annotation, ~:441; `apply` routes writes onto leaf families) | SchemaInfo 4/4/1, RuleSet 4/2/1 |
| S4 relation-rule helpers (pre-parser era) | 578-643 | `replace_relation` :579, `norm_pred` :584, `parse_relation_rule` :592 (bracket-list parser; docstring says its rewrite half is gone) | norm_pred 4/0/0, parse_relation_rule 0/1 (`tests/test_wildcard_schema.py`) |
| S5 AST types + graph-refusal error types | 644-749 | `UnsupportedByGraphIndex` :658, `DoublyBridgedShapeError` :666, `CyclicDerivedDependency(ValueError)` :685, `Restriction` :697, `Direct` :709, `Computed` :715, `TTU` :721, `Union` :730, `Intersection` :735, `Exclusion` :740, `Expr` :745, `SchemaAST` :746, `_RESERVED` :749 | UnsupportedByGraphIndex 1/13/8, Union/Intersection 1/8/5/3, Exclusion 1/8/4/3, Direct/TTU 1/6/4/3, Computed 1/4/4/3, Restriction 0/3/1/3, CyclicDerivedDependency 1/5, DoublyBridgedShapeError 1/3, Expr 0/1/0/1. `formal/conformance/test_grid_independence.py:79` asserts `type(...).__module__ == "zanzibar_utils_v1"` for these classes. |
| S6 tokenizer + parser | 750-1008 | `_tokenize_relation_body` :752, `_RelationParser` :792-890, `_validate_declared_name` :893, `parse_schema_ast` :913, `_parse_schema_ast_unchecked` :927-1008 | parse_schema_ast 1/22/11/1, `_parse_schema_ast_unchecked` 0/4/3 (PRIVATE name used by 7 external files) |
| S7 parse-time validation / refusals | 1009-1351 | `_validate_ast_references` :1011, `_iter_refs` :1048, `_validate_ast_consistency` :1060-1169, `_validate_tuplesets_direct` :1172-1240, `_validate_stratified_negation` :1243-1328, `_iter_directs` :1331, `_iter_ttus` :1343 | `_iter_directs` 0/3 (private, tests). Named by string in `formal/conformance/test_graphadmission_scope_pin.py` (C4). |
| S8 SchemaInfo derivation + unproven-extension warning | 1353-1436 | `derive_schema_info` :1355, `UnprovenExtensionWarning(UserWarning)` :1392, `unproven_extensions` :1403, `_warn_unproven_extensions` :1428 | derive_schema_info 1/2/6, UnprovenExtensionWarning 0/1 (+ `pytest.ini` message-prefix filter) |
| S9 `compile_ruleset` core (untainted path) | 1437-1743 | `_restriction_pattern` :1439, `_restriction_filter` :1458, `_rewrite_rule` :1462, `schema_filters` :1483, `_emit_expr` :1498, `_directs_only` :1525, `_validate_ttu_tuplesets` :1533-1626, `_assert_ttu_parent_types_cover_admission` :1629-1695, `compile_ruleset` :1698-1743 | compile_ruleset 1/1/2, schema_filters 1/0 |
| S10 wildcard scope / graph refusals | 1744-2041 | `_node_removal_fence` :1746, `_expand_object_wildcard_shapes` :1796, `wildcard_userset_restriction_shapes` :1824, `_reject_doubly_bridged_shapes` :1876, `_reject_object_wildcard_scope` :1940-2041 | wildcard_userset_restriction_shapes 1/2/3 |
| S11 boolean compile | 2042-2700 | plan nodes `PClosureLeaf` :2060, `PDerivedComputed` :2074, `PDerivedUserset` :2082, `PDerivedTTU` :2092, `PUnion` :2104, `PIntersection` :2109, `PExclusion` :2114; artifacts `LeafSpec` :2122, `LeafFamily` :2130, `DerivedFamily` :2141, `DependentEdge` :2148, `Plan` :2158, `CompiledBooleans` :2175-2196; taint `_mentions` :2201, `_contains_boolean` :2232, `_member_types` :2240, `compute_taint` :2288; plans `_is_pure` :2306, `_emit_leaf_expr` :2324, `_build_plan_tree` :2344-2438, `_plan_leaves` :2441; exec `_compile_check_fn` :2476, `_compile_stars_fn` :2501; strata `_plan_deps_and_fanout` :2531, `_stratify` :2578; `compile_boolean_schema` :2629-2700. 26 defs, 659 lines -- the largest section. | compute_taint 0/2/6, PIntersection 0/3/1/1, PUnion/PExclusion 0/2/0/1, `_plan_leaves` 0/1/1/1 (private; regex-scanned by `test_conformance_nary_strata.py:424`), LeafFamily 1/1/0/1, `_member_types` 0/1/1, CompiledBooleans 2/0, DerivedFamily 1/0, PClosureLeaf 0/1, PDerivedTTU 0/1 |
| S12 DSL front door | 2701-2722 | `parse_openfga_schema` :2703 (parse -> derive_schema_info -> compile_ruleset) | **1/51/15/4 -- the most-imported name in the module** |
| S13 OpenFGA JSON front end | 2723-2945 | `parse_openfga_json` :2736, `_reject_duplicate_json_keys` :2807, `_validate_json_wildcard` :2824, `_validate_json_round_trip` :2843, `_json_restrictions` :2871, `_json_rewrite` :2891, `openfga_json_to_dsl` :2942 | parse_openfga_json 0/5, openfga_json_to_dsl 0/1 -- NO product caller (tests only) |
| S14 unparser | 2946-3004 | `unparse_schema_ast` :2950 | 0/6/3/3 -- no product caller |
| S15 W4Fragment report | 3005-3184 | `W4_FRAGMENT_FIELDS` :3035, `W4FragmentReport` :3042, `_w4_*` helpers :3060-3127 (8), `w4_fragment_report` :3130 | 0/1/2 -- no product caller (opt-in, differential-pinned to Lean) |
| S16 GraphAdmission report | 3185-3289 | `GRAPH_ADMISSION_REPORTED_FIELDS` :3217, `GraphAdmissionReport` :3221, `_ga_rule_arms` :3238, `graph_admission_report` :3250 | 0/1/1 -- no product caller |

Counts in the last column (FIRST-HAND, AST over `git ls-files '*.py'` minus this module and legacy/): number of distinct FILES that `from zanzibar_utils_v1 import X` or access `<alias>.X` after `import zanzibar_utils_v1 as <alias>`. 56 distinct names are used externally.
Public names NEVER used outside the module (same census): `IDENTIFIER_CHARSET`, `NodeV2`, `replace_relation`, `SchemaAST`, `unproven_extensions`, `PDerivedComputed`, `PDerivedUserset`, `LeafSpec`, `DependentEdge`, `Plan`, `compile_boolean_schema`, `W4FragmentReport`, `GraphAdmissionReport` (and the re-exported legacy `Node`).
No module-global monkeypatching of `zanzibar_utils_v1` exists (FIRST-HAND: `git grep -nE "monkeypatch\.setattr\(|mock\.patch\("` filtered to these modules; the only module-object patch target in the repo is `index_v4.core.MAX_PATH_COUNT`, in `tests/test_tk111_path_count_bound.py` x5 and `tests/test_tk121_stall_recovery.py:289` -- lookup-site sensitive if `MAX_PATH_COUNT` moves). No string-target patches (`patch('zanzibar_utils_v1.x')`) and no `importlib`/`__import__` of product modules anywhere. No pickles: persisted state carries no module paths (`connectedstore/store.py:353` stores only an exception's `type(exc).__name__`).

##### F1. Cross-section dependencies (FIRST-HAND: for each top-level def, the module-level names it references by `ast.Name` or exact-match string constant; caller -> callee with the names)
- S3 -> S1 `AdmissionRejected`; S3 -> S2 `Filter, RelationalTriple, RewriteFilter, Rule`; S3 -> S4 `replace_relation`; S3 -> S11 `CompiledBooleans` (string annotation only -- type-level, no runtime import needed).
- S4 -> S1 `is_valid_identifier`; S4 -> S2 `RelationalTriple`.
- S6 -> S1 `IDENTIFIER_CHARSET, is_valid_identifier`; S6 -> S4 `parse_relation_rule`; S6 -> S5 (all AST types, `_RESERVED`); **S6 -> S7** `_validate_ast_consistency, _validate_ast_references, _validate_stratified_negation, _validate_tuplesets_direct` (the checked parse runs the validators).
- S7 -> S5 (AST types); **S7 -> S9** `_directs_only`.
- S8 -> S3 `SchemaInfo`; S8 -> S5 `SchemaAST`; S8 -> S7 `_iter_directs, _iter_ttus`; **S8 -> S10** `wildcard_userset_restriction_shapes`.
- S9 -> S2, S3 (`RuleSet, SchemaInfo`), S5 (all AST + `UnsupportedByGraphIndex`), **S9 -> S7** `_iter_directs, _iter_ttus`; S9 -> S10 `_expand_object_wildcard_shapes, _node_removal_fence, _reject_doubly_bridged_shapes, _reject_object_wildcard_scope`; **S9 -> S11** `LeafFamily, PDerivedTTU, compile_boolean_schema, compute_taint`.
- S10 -> S2 `Filter, Rule`; S10 -> S3 `SchemaInfo`; S10 -> S4 `norm_pred`; S10 -> S5 `DoublyBridgedShapeError, SchemaAST, UnsupportedByGraphIndex`; S10 -> S7 `_iter_directs, _iter_ttus`.
- **S11 -> S9** `_assert_ttu_parent_types_cover_admission, _restriction_pattern, _rewrite_rule`; S11 -> S2 `Filter, RewriteFilter, Rule`; S11 -> S3 `SchemaInfo`; S11 -> S5 (all AST + both graph-refusal errors).
- S12 -> S3 `RuleSet`, S6 `parse_schema_ast`, S8 `derive_schema_info`, S9 `compile_ruleset`.
- S13 -> S5, S6 `_validate_declared_name, parse_schema_ast`, S7 (all four validators), S14 `unparse_schema_ast`.
- S14 -> S5 only.
- S15 -> S5, S6 `_parse_schema_ast_unchecked`, S11 `compute_taint`. S16 -> S5, S6 `_parse_schema_ast_unchecked`, S11 `compute_taint`.
- S1, S2 (bar `NodeV2 -> legacy Node`), S5 reference no other section: they are the leaves.

##### F2. Section-level CYCLES a file split would have to break (FIRST-HAND from F1)
1. **S9 <-> S11** (core compiler <-> boolean compiler): `compile_ruleset` calls `compute_taint` / `compile_boolean_schema` and uses `LeafFamily`, `PDerivedTTU`; the boolean compiler calls back into three S9 helpers (`_restriction_pattern`, `_rewrite_rule`, `_assert_ttu_parent_types_cover_admission`). INFERRED fix shape: move those three helpers into a lower shared module, or have S9 import S11 lazily. This is the cycle the TK120 row's "split core vs boolean compiler" idea runs into.
2. **S7 <-> S9**: validators use `_directs_only` (S9, :1525-1530, 6 lines) and S9 uses `_iter_directs/_iter_ttus` (S7, :1331-1351). INFERRED: an "AST helpers" home next to S5 dissolves it.
3. S3 -> S11 is annotation-only (string) and needs no runtime edge.
No cycle involves S1, S2, S4, S5, S12-S16.
INFERRED natural partition (for the planner to judge, not a recommendation): {S1} errors/identifiers; {S2,S3,S4} rule model + RuleSet; {S5 + AST helpers} AST; {S6,S7} parser + validation; {S8,S9,S10} graph compile; {S11} boolean compile; {S12} facade; {S13,S14} JSON + unparser; {S15,S16} scope reports. Gate couplings any split must update: `tests/test_refused_shape_comments.py::FILES/MIN_HEADERS` (37 blocks; FIRST-HAND per-section count via grep -n "REFUSED SHAPE" + the F line ranges: S6 6, S7 9, S9 3, S10 7, S11 2, S13 10 = 37), `tests/test_tk116_oracle_only_setengine.py::_SRC`, `formal/conformance/test_grid_independence.py:79` (`__module__`), the 36 `zanzibar_utils_v1.py::<sym>` literals in the two `*_scope_pin.py` files, 52 pin rows + 57 CORRESPONDENCE.md cites.

## 4. Agent census B: rename/move traps (agent report, transcribed verbatim 2026-10-05b)

Source: `.scratch/tk120-census/traps.md`, a read-only general-purpose subagent. The
`.scratch/` copy is deleted after this transcription. Headings are demoted two levels;
nothing else is edited.

### TK120 rename/move TRAP census (read-only scouting, 2026-10-05)

Agent: traps-census subagent. Labels: FIRST-HAND = grep/read run by this agent; INFERRED = reasoned, not executed.
Status: COMPLETE (all 9 sections). Read-only; no tracked file edited; no pytest/verify.sh run.

#### SUMMARY -- trap list, ranked

**Q1 answer (the row's UNVERIFIED item): NO golden, snapshot, fixture, corpus or benchmark result embeds a module path, package name, listed class name or table name.** The 15 compiled-RuleSet snapshots embed only `RelationalTriplePattern(`, `Filter(`, `Rule(`, `RewriteFilter(` dataclass reprs (qualname, not module), so a module move leaves them byte-identical; they go red only if THOSE four classes are renamed or nested. FIRST-HAND (grep) / INFERRED (dataclass repr semantics).

##### SILENT -- passes while wrong (worst first)
1. **Mass `claim_rot.py --generate`** after the rename: ~171 of 255 Python content-pin rows move at once (153 re-keyed by file move, 18 re-hashed in files nobody moved, because their bodies name `NodeV4`/`EdgeV4`/...). Loud red, but the only fix is a regeneration that launders any behaviour change in the same commit. Keep the rename commit behaviour-free and check each new body against old-body-under-substitution before regenerating. (3.3, measured)
2. **Scope-pin `evidence` strings** (>= 22 in `test_graphadmission_scope_pin.py` / `test_w4fragment_scope_pin.py`) are shape-checked, never resolved -> rot green. (2c)
3. **Fixed-file source scanners if the schema module is SPLIT**: `test_refused_shape_comments.py::FILES/MIN_HEADERS`, `test_tk116_oracle_only_setengine.py::_SRC`, `genswarm.py` `inspect.getsource(Z)`, `test_reg15_security_hardening.py::_GUARDED_MODULES` -> code in a new unlisted file is never scanned. (2g-j)
4. **`doc_counts.py::TOOLING_FILES`** keyed by basename: renaming a tooling test inflates the Lean-vs-Python figure; `--check` stays green. (3.5)
5. **Rewrite tool fidelity**: 418 files to touch, 325 non-ASCII, 173 CRLF + 245 LF working copies; PowerShell/cp1252 heredoc paths corrupt or match zero. Byte-preserving rewrite + per-file expected-count assertion required. (9.9, measured)
6. **Table/constraint names** (`store_v4`, `node_v4_unique_constraint`, FK strings `"node_v4.id"`, ...) silently renamed by any case-insensitive or `_v\d`-stripping regex = unannounced PostgreSQL schema migration; SQLite tests stay green. A CLASS rename alone CAN leave the DB untouched. (7)
7. **anchor_check bare-`::Sym` inheritance** can resolve against the wrong file once a plain path mention goes stale. (3.2)
8. **`.gitignore` patterns** (`build/`, `lib/`, `gen`, `out`, `env/`, `var/`, ...) as new package names: later files silently untracked and outside the gate tree id; `build` also skipped by `test_invariants_docstring_matches_body`. (8)
9. Minor: `caplog.at_level(logger='index_v4.core')` becomes a no-op (2 tests, still pass); legacy `conf-rest` `--ignore` of a renamed heavy file is a no-op; benchmarks + `formal/probes/` break outside the gate.

##### HARD RED -- loud, but a mechanical sed/`git mv` misses them
- **Path form vs dotted form**: `zanzibar_utils_v1.py` / `index_v4/x.py` (CORRESPONDENCE.md 188 refs to moving files, anchor pin 153 rows, tasks, scope pins) vs `zanzibar_utils_v1` / `index_v4.x` (imports, logger names, `__module__`). One identifier sed produces `pkg.schema.py`. Replace path form first, then dotted form.
- `test_grid_independence.py::test_the_two_parsers_are_really_different_code` asserts `__module__ == "zanzibar_utils_v1"` and `== "tests.oracle"` (a shim does not satisfy it).
- `test_w4fragment_scope_pin.py` / `test_graphadmission_scope_pin.py` `reported_by` checks: literal `path == "zanzibar_utils_v1.py"` + `getattr(zanzibar_utils_v1, sym)`.
- `test_claim_rot_gate.py` real-path sabotages (`"index_v4/models.py::EdgeV4: BODY CHANGED"`).
- `test_reg15_security_hardening.py::_run_under_O` -- `from index_v4...` inside a `-c` STRING (missed by import-line seds).
- `index_v4/models.py:89-90` `foreign_keys='[EdgeV4.subject_id]'` -- class name in a string (missed by IDE/AST rename; fails at mapper config, not import).
- `anchor_check.py` (4d) parses, never imports: a re-export shim at the old path does not resolve anchors. `import *` shims do not re-export the many `_private` names tests use.
- `task.py lint` check 14: 21 open rows / 25 `## Read first` lines cite moving paths or classes.
- Zero-headroom per-dir floors `MIN_TESTS_ALL=1745`, `MIN_CONF_ALL=1087`: moving a test across `tests/` <-> `formal/conformance/` reds one.
- `doc_counts` 4e: renaming a conformance test file reds the generated per-file block until regenerated.
- `test_tk116`/`test_refused_shape_comments`/`test_reg15` path constants, `test_schema_shapes.py::MASKED_PAIRS` (cites test files), `tests/test_reads.py` table-name filters (only on a TABLE rename).
- `verify.sh` preflight + `tests/conftest.py` import `setengine.setops` (only if setengine moves).
- **Import-order-dependent collisions** (loud but tile-dependent): `legacy/index_v3.py` `Node`/`Edge` SQLModel tables (default names `node`/`edge`) share the global registry with live models whenever `tests/test_index.py`/`tests/test_integration.py` were imported in the same process. Naming live classes `Node`/`Edge` makes `'[Edge.subject_id]'` ambiguous, and dropping `__tablename__` collides tables. **`NodeV2` names two unrelated classes** (`zanzibar_utils_v1.NodeV2(legacy.index_v2.Node)` vs `tests/test_index.py`'s `Node as NodeV2` alias).

##### COSMETIC -- nothing checks them
- Lean: 281 comment lines in 43 `.lean` files (all in `/- -/` comments, stripped by every pin). Editing them buys a Lean rebuild and nothing else.
- Frozen docs: `docs/history` 240, `formal/history` 116, `docs/specs` 41 occurrences, plus ~36 FROZEN plan docs under `docs/`. **No checker resolves code anchors in any frozen doc -> no hard conflict**; but a blind repo-wide sed WOULD edit them. Exclude FROZEN docs (not just the history dirs) and add a rename table to the plan doc instead.
- `pytest.ini` UnprovenExtensionWarning filter is by MESSAGE PREFIX (`ignore:UNPROVEN:UserWarning`), not module path, so it survives. Its only old name is in a comment.
- Assertion messages/docstrings naming `NodeV4`/`TupleV1`/module paths (list in 2o); task FILENAMES with `edgev4`/`residuev1`; closed task rows (221 occurrences, unlinted).

#### 1. Goldens / snapshots / fixtures

**Verdict: NO golden or fixture embeds any module path, package name, listed class name or table name. FIRST-HAND.**

- Tracked non-code data files (`git ls-files`, 2026-10-05): 15 `.fga`, 22 `.txt`, 5 `.json`, 8 `.jsonl` (benchmarks/results), 1 png. No pickles, no `.pkl`, no sqlite db tracked. `grep -rnE 'pickle|marshal|shelve|__reduce__|dill' --include=*.py` over the repo: 0 hits (FIRST-HAND).
- Grep of pattern `zanzibar_utils|index_v[0-9]|legacy|StoreV4|NodeV4|EdgeV4|ResidueV1|ResidueRefV1|DeltaOutboxV1|TupleV1|SchemaV4|TupleLogV1|IndexCursorV1|NodeV2|store_v4|node_v4|edge_v4|residue_v1|residue_ref|delta_outbox|tuple_v1|schema_v4|tuple_log|index_cursor` over every tracked .json/.jsonl/.txt/.toml/.ini/.gitignore/.gitattributes: hits ONLY in `formal/correspondence_anchor_pin.txt` (153 lines) and `pytest.ini` (1 line, a comment). All 15 `tests/snapshots/compiled_ruleset/*.fga.txt`, all `tests/fga_schemas/*`, `formal/conformance/derived_arm_multiplicity.json`, all `benchmarks/results/*.jsonl`: 0 hits. FIRST-HAND.
- What the snapshots DO embed (FIRST-HAND, `grep -oE '[A-Za-z_]\w*\('` over all 15): `RelationalTriplePattern(` x343, `Filter(` x164, `Rule(` x83, `RewriteFilter(` x13, plus literal `Ellipsis`. Generator `tests/test_compile_snapshot.py::_canonical_ruleset` writes `repr(x)` of these. They are `@dataclass(frozen=True, slots=True, ...)` in `zanzibar_utils_v1.py` (lines 268/338/346/363, 2026-10-05); a dataclass repr uses `__qualname__`, NOT `__module__`, so **moving `zanzibar_utils_v1.py` leaves the snapshots byte-identical**. INFERRED (CPython dataclass behaviour; not executed).
  * TRAP (cosmetic->hard red): if the restructure ALSO renames `Filter`/`Rule`/`RewriteFilter`/`RelationalTriplePattern`, or nests them inside another class (qualname change), all 15 goldens go red (hard, loud: `test_compiled_ruleset_matches_snapshot` assert). They are NOT on the TK120 rename list; keep them off it, or regenerate deliberately with `ZANZIBAR_UPDATE_SNAPSHOTS=1` + a `docs/spec-deviations.md` entry.
  * Snapshot test locates fixtures by `Path(__file__).parent / "snapshots"` and `/ "fga_schemas"` (`tests/test_compile_snapshot.py::SNAPSHOT_DIR`, `FGA_DIR`). Moving `test_compile_snapshot.py` out of `tests/` without moving those dirs -> glob empty -> guarded by `MIN_FIXTURES = 15` module-level assert (hard red at collection, not silent). FIRST-HAND.
- Persisted strings in the DB: `connectedstore/store.py:353` writes `IndexCursorV1.stall_error = f'{type(exc).__name__}: {exc}'` -- class `__name__` only, no module; the exceptions it carries (`PathCountExceeded`, etc.) are not on the rename list. FIRST-HAND. `SchemaV4.object_wildcard_shapes` is JSON of `[type, relation]` pairs, no class names (`connectedstore/models.py:30`). FIRST-HAND.

#### 2. String-level module paths (things `sed` on import lines / `git mv` miss)

Method: `grep -nE "['\"][^'\"]*(zanzibar_utils_v1|index_v4|legacy[/.]|legacy['\"])[^'\"]*['\"]"` over all tracked `.py`/`.sh`, minus `from/import` lines (FIRST-HAND, 2026-10-05): 92 quoted-string hits in 26 files. Plus separate greps for `__module__`, `__qualname__`, `.__name__ ==`, `mock.patch("..")`, `monkeypatch.setattr("..")`, `import_module`, `__import__`, `sys.modules[`, `-m`, `-k`, `subprocess`, `caplog ... logger=`.

**Zero hits** for `mock.patch("<old module>...")`, string-form `monkeypatch.setattr("<old module>...")`, `importlib.import_module`, `__import__`, `sys.modules[...]` naming an old module (FIRST-HAND grep). No `-k` selector or `python -m <old module>` anywhere in tests/scripts/verify.sh naming an old module (FIRST-HAND).

Hits that matter, by failure mode:

| # | file::symbol | what it holds | on rename/move | label |
|---|---|---|---|---|
| a | `formal/conformance/test_grid_independence.py::test_the_two_parsers_are_really_different_code` | `assert type(past[...]).__module__ == "zanzibar_utils_v1"` AND `== "tests.oracle"` | HARD RED. The right new value is the DEFINING module, so a re-export shim at the old name does NOT keep it green. Moving `tests/oracle.py` reds the second assert. | FIRST-HAND |
| b | `formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE` (21 strings `"zanzibar_utils_v1.py::<sym>"`) + `::test_every_field_is_reported_and_has_a_rerunnable_probe` (`assert path == "zanzibar_utils_v1.py" and callable(getattr(zanzibar_utils_v1, symbol))`) | FILE-PATH form next to MODULE form in one function | HARD RED if missed. **TRAP: one sed of the identifier `zanzibar_utils_v1` -> `pkg.schema` turns `"zanzibar_utils_v1.py"` into `"pkg.schema.py"` (wrong; needs `pkg/schema.py`). Two ordered replacements are required: path form `zanzibar_utils_v1.py` -> `<new/path>.py` FIRST, then dotted module form. Same for every `index_v4/x.py` vs `index_v4.x` pair, repo-wide (CORRESPONDENCE.md, pins, tasks use the path form; imports use the dotted form).** | FIRST-HAND |
| c | `formal/conformance/test_graphadmission_scope_pin.py` (17 strings `"evidence": "zanzibar_utils_v1.py::..."`; line ~414 partitions `reported_by` on `::`) | path::symbol strings | `reported_by`: resolved (`::test_every_scope_row_is_well_formed`, SILENT rows only) -> HARD RED. **`evidence` is NEVER resolved, in either pin** (`test_graphadmission_scope_pin.py::test_every_scope_row_is_well_formed` and the w4fragment twin only assert it contains `::` or `/` and no `:\d+`) -> **after a move every `evidence` string rots SILENTLY** (stays green pointing at a dead path). Count citing old paths (grep `"evidence": "[^"]*(zanzibar_utils_v1|index_v4|legacy)`): 14 in graphadmission + 8 single-line in w4fragment (+ multi-line ones, e.g. l.317) = **>= 22 silent strings**. Must be rewritten by sed. | FIRST-HAND |
| d | `tests/test_claim_rot_gate.py::test_B_class_is_pinned_at_its_shell` and siblings (6 strings: `"index_v4/wildcard.py"`, `"index_v4/models.py"`, expected prefix `"index_v4/models.py::EdgeV4: BODY CHANGED"`, sabotage anchor `EDGE_DERIVED`) | real repo paths fed to `anchor_check.resolve_path` | HARD RED (`_patch_file` asserts `real is not None`; `_sub` asserts exactly one match). Path AND class name inside the expected-prefix string must both change. | FIRST-HAND |
| e | `tests/test_tk111_stall_aware_freshness.py` (~l.138), `tests/test_tk112_cap_policy.py` (~l.134): `caplog.at_level('WARNING', logger='index_v4.core')`; producer `index_v4/core.py:19 _log = logging.getLogger(__name__)` | logger NAME string | **SILENT (harmless today)**: after a move `at_level` configures an unused logger; tests still pass because WARNING records propagate to root (default WARNING). The `at_level` line becomes dead. Fix the string anyway. | FIRST-HAND (code) / INFERRED (logging behaviour) |
| f | `tests/test_reads.py` (~l.71, ~l.181): `'edge_v4' in s.lower()`, `'node_v4' in s.lower()` | TABLE names in captured SQL | Only on a TABLE rename: hard red (positive cases assert `== 1`). CLASS rename alone: no effect. | FIRST-HAND |
| g | `tests/test_reg15_security_hardening.py::_GUARDED_MODULES = ['index_v4/core.py', 'index_v4/processor.py']` + `::_run_under_O` (`-c` script STRING containing `from index_v4.core import ...`) | paths + import text inside a string | Path: HARD RED. The `-c` string: HARD RED in the subprocess, and **a sed anchored on `^from`/`^import` lines MISSES it** (indented inside a string). **SILENT if core.py/processor.py are SPLIT**: code moved to a new module escapes the no-`assert` pin. | FIRST-HAND |
| h | `tests/test_refused_shape_comments.py::FILES`, `::MIN_HEADERS` (`'zanzibar_utils_v1.py': 37`, `'tests/oracle.py': 16`, `'setengine/engine.py': 1`) | per-file zero-headroom floors | Rename: HARD RED. **SPLIT of the schema module: SILENT for every refusal moved into a file not in `FILES`** (never scanned); the listed file's count drops -> red, which invites lowering the floor. Correct: list every new file, split the 37 across them. | FIRST-HAND |
| i | `tests/test_tk116_oracle_only_setengine.py::_SRC` (`... / 'zanzibar_utils_v1.py'`) + `::test_every_graph_refusal_site_has_a_witness` (regex count == witnesses + unreachable) | one source file | Rename: HARD RED. **Split: sites in the other file vanish from the census (loud now), and any FUTURE raise site added there is never counted (SILENT forever).** Regex also misses a qualified `raise errors.UnsupportedByGraphIndex(`. | FIRST-HAND |
| j | `tests/genswarm.py::derive_via_kinds`, `::derive_family_kinds` (`inspect.getsource(Z)`, `Z = zanzibar_utils_v1`), `::derive_leaf_kinds`, `::derive_plan_node_classes` | WHOLE-MODULE source scan | **SILENT on a SPLIT**: `DependentEdge(..., '<via>')` literals partly in another module -> derived set SHRINKS; guard is only `assert vias` (non-empty). If `Z` becomes a shim, `getsource(Z)` is the shim text -> loud anti-vacuity red. | FIRST-HAND |
| k | `formal/conformance/test_conformance_nary_strata.py` (~l.421) `inspect.getsource(zanzibar_utils_v1._plan_leaves)` == `_REQUIRED_LEAF_KINDS`; l.351/353 label strings | function source | Follows the function; safe on move once the import is fixed. Labels cosmetic. | FIRST-HAND |
| l | `tests/test_schema_shapes.py::MASKED_PAIRS` (resolver ~l.437) | `tests/<file>.py::<test>` guards | Moving a cited TEST file: HARD RED. | FIRST-HAND |
| m | `tests/test_invariants_docstring_matches_body.py` (~l.207) `rglob('*.py')`, `skip = {..., 'build', '.venv', '.lake', ...}` | directory-NAME skip list | **SILENT if a new package/dir is named `build`**: its files are skipped. | FIRST-HAND |
| n | old module kept as a shim `from new import *` | -- | `import *` without `__all__` does NOT re-export underscore names; tests reach many (`_plan_leaves`, `_validate_*`, `_parse_schema_ast_unchecked`, `_require`, `_stratify`). Loud. | INFERRED (Python semantics) |
| o | Message/docstring strings nothing checks: `formal/conformance/backends.py:154,164,300`; `formal/conformance/test_conformance_fragment.py:288`; `formal/conformance/test_conformance_state.py:768,772` ("NodeV4 rows"); `formal/conformance/test_conformance_remove.py:291,367` ("TupleV1 rows"); `formal/conformance/extractor.py:212,514`; `tests/test_reg_tk80_remove_node_residue.py:762,767`; `tests/test_generator_coverage.py:304,306`; `tests/test_admission_rejected.py:82,261`; `tests/oracle.py:355`; `setengine/engine.py:131`; `connectedstore/build.py:40`; `zanzibar_utils_v1.py:63`; `tests/test_fuzz_names.py:36` (`DROP TABLE node_v4` fuzz payload) | text | cosmetic | FIRST-HAND |
| p | `tests/test_tasktool.py` ~l.533 fixture text `index_v4/core.py::ReachabilityIndex` | synthetic task body for a byte round trip | Cosmetic as read; not verified that no other tasktool case lints it with `ZANZIBAR_TASK_POINTER_ROOT`. | FIRST-HAND / UNVERIFIED |
| q | `benchmarks/profile_r6_write.py` (17 strings), `benchmarks/profile_r6.py` (4); `formal/probes/tk77_generator_reach_sweep_2026-09-19.py:47`, `formal/probes/tk87_churn_sweep_2026-09-19.py:47` (`WC = 'index_v4/wildcard.py'`) | profiler filters / probe mutation targets | Outside the gate. Benchmarks: SILENT (a dead-path filter attributes nothing). Probes are dated; leave. | FIRST-HAND / INFERRED |

Other `__name__` compares (`tests/test_postgres_ha.py:156,213` `'QueryCanceled'`; `tests/test_tasktool.py:2527` `'check_banner'`) are unaffected. FIRST-HAND.

#### 3. Gate machinery keyed on paths/names

##### 3.1 `formal/verify.sh` (FIRST-HAND read)
- Hard-coded dirs: `CONF_DIR="formal/conformance/"` (l.127), `TESTS_DIR="tests/"` (l.128), `HEAVY_CONF="formal/conformance/test_conformance_remove.py"` (l.694, legacy `conf-heavy`/`conf-rest` phases). No old module name appears in any EXECUTED line of verify.sh (all hits are comments). Renaming `test_conformance_remove.py` breaks only the legacy phases: `conf-heavy` -> pytest on a missing path (loud); `conf-rest` `--ignore` of a missing path is a no-op -> it would run the WHOLE dir and its floor `MIN_CONF_REST=952` still passes -> **SILENT mis-labelling of the legacy split** (low impact: the tile phases are the gate). INFERRED for pytest's `--ignore` of a non-existent path.
- Preflight `preflight_py` (l.~824): `-c "from setengine.setops import RoaringSets, ALL_SETOPS, DEFAULT_SETOPS"`. `setengine` is not on the TK120 list, but if it moves this is a hard red in EVERY phase (and `tests/conftest.py` imports the same thing). FIRST-HAND.
- Count floors `MIN_TESTS_ALL=1745` (l.641), `MIN_CONF_ALL=1087` (l.458), `MIN_CONF_HEAVY=135`/`MIN_CONF_REST=952` (l.719-720): **zero headroom, per DIRECTORY**. Moving a test file between `tests/` and `formal/conformance/` (or out of both, e.g. to a new `tests/<sub>/` -- that one is fine, still under `tests/`) reds one floor and silently inflates the other; both must be edited in the same commit, with provenance comments. Moving a file into a subdir of `tests/` keeps the count. FIRST-HAND (values) / INFERRED (effect).
- Lean phase python steps: `statement_pin.py` (Lean text vs `formal/headline_statements.txt` / `headline_definitions.txt` -- 0 Python-module hits in those txt files, grep FIRST-HAND), `anchor_check.py` (4d), `claim_rot.py --check` (4d2/4d3), `doc_counts --check` (4e), `scripts/handoff_lint.py` (l.1119), `scripts/task.py lint` (l.1179).

##### 3.2 Anchor resolver -- `formal/conformance/anchor_check.py` (4d)
- **Parses files, never imports** (docstring + `::python_nodes` uses `ast.parse`). `::resolve_path`: Python anchors are REPO-ROOT-relative (`REPO_ROOT / anchor_file`, must be `is_file()`); Lean anchors try `formal/lean/ZanzibarProofs/`, `formal/lean/`, repo root. Reads ONLY `formal/CORRESPONDENCE.md` (`DOC`). FIRST-HAND.
- On move: every `old/path.py::Sym` -> "file does not exist" -> HARD RED. A re-export shim at the old path does NOT help: the shim's AST does not define the symbols (it only imports them) -> "does NOT resolve". FIRST-HAND (code) / INFERRED (shim case).
- **SILENT sub-trap (inheritance)**: a bare `` `::Sym` `` inherits the most recent file in its cell/paragraph, and a plain backticked `` `file.py` `` supplies inheritance ONLY IF IT RESOLVES (`::extract_anchors`, "Only a file that actually exists may supply inheritance"). After a move, a stale plain mention is skipped and a bare `::Sym` silently inherits the PREVIOUS file in scope (or `<no file in scope>` -> red). If the previous file happens to define a same-named symbol, the anchor resolves to the WRONG file, green. Mitigation: rewrite paths in CORRESPONDENCE.md with the full-path sed (both `` `x.py::`` and plain `` `x.py` `` forms), then `anchor_check.py --list` diff before/after. INFERRED from code.
- Floors `MIN_PY_ANCHORS = 250`, `MIN_LEAN_ANCHORS = 100` (counts, not identity).
- Measured (2026-10-05, `grep -oE` over CORRESPONDENCE.md): backticked `.py` refs by file -- `index_v4/processor.py` 58, `zanzibar_utils_v1.py` 57, `index_v4/wildcard.py` 32, `index_v4/core.py` 20, `index_v4/invariants.py` 5, `index_v4/bulk_build.py` 5, `index_v4/outbox.py` 4, `index_v4/models.py` 4, `index_v4/bulk_backfill.py` 3 (= 188 full-path refs to moving files), plus bare-basename mentions (`processor.py` 4, `core.py` 1, `bulk_build.py` 1) that do not resolve today and supply no inheritance. FIRST-HAND.

##### 3.3 Content pin -- `formal/conformance/claim_rot.py` (4d2) + `formal/correspondence_anchor_pin.txt`
- Pin key is the literal `file::symbol`; value is a hash of the AST-unparsed BODY (functions minus docstring; classes = shell incl. decorators, bases, class-level fields like `__tablename__`). FIRST-HAND (`::_py_body`, `::anchor_body`, `::check_content_pin`).
- Pin rows (FIRST-HAND count of `formal/correspondence_anchor_pin.txt`): 255 Python + 231 Lean. Python rows in moving files: `zanzibar_utils_v1.py` 52, `index_v4/*` 101 (processor 41, wildcard 25, core 21, models 5, invariants 4, outbox 3, bulk_build 1, bulk_backfill 1).
- **Probe run 2026-10-05** (`.scratch/tk120-census/_probe_bodies.py`, read-only: `anchor_check.extract_anchors` + `claim_rot.anchor_body`, regex over the body text for every listed module/class/table name): **255 unique Python anchors; 153 are in a file that moves (KEY changes); 65 have a BODY that mentions a listed name (HASH changes under a pure rename); 18 of those 65 are OUTSIDE the moving files** -- so a rename moves pins in files nobody `git mv`'d: `connectedstore/apply.py::_apply_row`, `::advance_index`; `connectedstore/build.py::_materialise`, `::rebuild_index`; `connectedstore/source.py::TupleSource._lock_source`; `setengine/engine.py::SetEngine.rebuild`; `formal/conformance/extractor.py::extract_sql_state`, `::derived_relations`, `::_classify_edges`; `formal/conformance/backends.py::graphindex_drive`, `::GraphDriver.apply`; `formal/conformance/test_conformance_fragment.py::test_production_report_equals_lean`, `::test_reported_failures_are_refused_by_both_parsers`; `formal/conformance/test_graphadmission_scope_pin.py::GRAPHADMISSION_SCOPE`; `formal/conformance/test_grid_independence.py::test_the_two_parsers_are_really_different_code`; `formal/conformance/test_conformance_state.py::test_python_nodes_are_all_justified`, `::test_no_corpus_nests_a_pure_union_inside_an_impure_one`; `tests/test_bulk_build.py::_residues_proj`. Name frequency in affected bodies: NodeV4 30, EdgeV4 15, ResidueV1 10, zanzibar_utils_v1 7, DeltaOutboxV1 6, ResidueRefV1 6, index_v4 4, TupleV1 3, node_v4 3, + 1-2 each for the rest. FIRST-HAND (executed).
- Effect: HARD RED (loud) -- ~171 distinct Python pin rows move (153 re-keyed + 18 re-hashed). **The trap is the fix, not the failure**: the only remedy is `claim_rot.py --generate`, and its own docstring says a regeneration without re-reading the rows "is the one thing this cannot detect". A mass regeneration in the same commit as ANY behavioural edit launders that edit. Recommendation (INFERRED): (1) rename commits carry zero behaviour change; (2) before `--generate`, verify mechanically that each changed body equals the old body under the identifier substitution (reverse-substitute the new body text, re-hash, compare with the OLD pin value); (3) the `MIN_PINNED_ANCHORS = 470` floor is a count only.
- 4d3 prose lint (`::_cites`): a ratio claim's exemption depends on a cited `test_*.py` path RESOLVING (`anchor_check.resolve_path`). Moving a cited test file un-exempts the claim -> loud red. FIRST-HAND.

##### 3.4 `formal/audited_theorems.txt`, `formal/headline_statements.txt`, `formal/headline_definitions.txt`
- Lean names only; grep for every listed module/class/table name: 0 hits in all three (FIRST-HAND). Unaffected by a Python rename.

##### 3.5 `formal.conformance.doc_counts` (4e)
- `::_collect_per_file` globs `formal/conformance/test_*.py` (top level only) and the generated block in `formal/FINAL_REVIEW.md` is keyed by test-file BASENAME -> renaming/moving a conformance test file reds `--check` until regenerated (loud). Moving one into a subdir: per-file sum != directory collection -> `SystemExit` refusal (loud). FIRST-HAND.
- **SILENT: `doc_counts.py::TOOLING_FILES`** is a set of BASENAMES (`test_sorry_scan.py`, `test_runner_retry.py`, `test_w4fragment_scope_pin.py`, `test_leaf_namespace_correspondence.py`). Renaming one without updating the set re-classifies it as a "differential" file and inflates the Lean-vs-Python figure; the module's own comment records that `--check` compares the block to a regeneration of itself, "so a mis-triaged file is self-consistently wrong and stays green". FIRST-HAND.
- `_PROSE_GLOBS` (`formal/*.md`, `formal/conformance/*.py`, `docs/*.md`, `docs/architecture/*.md`, `HANDOFF.md`, `CLAUDE.md`) exclude any path containing `history`; it polices only the word "corpora" -- not path-sensitive. FIRST-HAND.

##### 3.6 `scripts/handoff_lint.py`
- Resolves only `.md` links/mentions (`::_MD_LINK`, `::_MD_MENTION`) in `::LINKED_DOCS` (HANDOFF.md, formal/HANDOFF.md, CLAUDE.md, README.md, docs/README.md, docs/spec-deviations.md, docs/latent-gaps.md, docs/architecture/overview.md). It never resolves `.py` paths. `::MENTION_ROOTS` hard-codes `'index_v4/'`, `'setengine/'`, `'connectedstore/'`, `'legacy/'`: a `.md` mention rooted in a NEW package dir is SKIPPED (silent, low impact -- only matters if .md files live inside code packages). FIRST-HAND.

##### 3.7 `scripts/task.py lint` check 14 (read-first pointers)
- Resolves `## Read first` pointers of OPEN tasks only: path must exist under repo root / tasks dir; if `::symbol`, the LAST dotted component must match `\bname\b` somewhere in the file (FIRST-HAND, `scripts/task.py` ~l.3290-3330). Moved path -> HARD RED (`resolves to nothing`). Renamed class with unchanged pointer -> HARD RED. After sed (`EdgeV4` -> `Edge`), the word-boundary match on a short common name is weak (any comment saying "Edge" satisfies it) -- cosmetic.
- **Measured 2026-10-05** (awk over `## Read first` sections of `tasks/*.md`, open rows): **21 open rows / 25 read-first lines** cite `zanzibar_utils_v1|index_v4/|legacy/` or a listed class: P6, R6-4, R6-5, R6-7, R6-8, R6-9, R6-11, R6-13, R6-16, R6-18, R6-19, TK3 (2), TK4, TK11, TK15, TK28, TK35 (2), TK39, TK50, TK85 (2), TK120 (2). 28 open rows mention an old name anywhere; 68 closed rows do (closed rows are not linted). Editing open rows must go through `task.py` ops per CLAUDE.md, not hand edits of frontmatter (the `## Read first` body is prose; check `docs/tasktool-spec.md` for whether body edits by sed are allowed). FIRST-HAND (counts) / UNVERIFIED (whether body sed is an allowed op).
- Task FILENAMES embed old names (`R6-18-edgev4-closure-rows-...`, `TK11-residuev1-version-...`): cosmetic; `task.py` resolves by frontmatter id.

##### 3.8 Tests that read source by path (see section 2 rows g, h, i, j, l, m for detail)
`tests/test_refused_shape_comments.py::FILES/MIN_HEADERS`, `tests/test_tk116_oracle_only_setengine.py::_SRC`, `tests/test_reg15_security_hardening.py::_GUARDED_MODULES`, `tests/genswarm.py` (`inspect.getsource(Z)`), `formal/conformance/test_conformance_nary_strata.py` (`getsource(_plan_leaves)`), `tests/test_schema_shapes.py::MASKED_PAIRS`, `tests/test_claim_rot_gate.py::_patch_file` callers, `formal/conformance/test_w4fragment_scope_pin.py` + `test_graphadmission_scope_pin.py` (`reported_by` resolved, `evidence` NOT). The P23 parity test (`tests/test_p23_parser_refusal_parity.py`) reads no source by path -- only `from tests import oracle` and `from zanzibar_utils_v1 import ...` (FIRST-HAND), so it needs only the import edit (and `tests` staying an importable namespace).
- REPO_ROOT by depth (`parents[2]` in `formal/conformance/{anchor_check,claim_rot,doc_counts,runner,statement_pin,test_leaf_namespace_correspondence,test_w4fragment_scope_pin}.py`; `parent.parent`/`parents[1]` in 11 `tests/*.py` + `scripts/gate_status.py`, `scripts/handoff_lint.py`): **moving any of these files to a different depth silently re-roots it** -- mostly loud downstream (files not found) but `test_invariants_docstring_matches_body` would rglob a smaller tree (silent). FIRST-HAND (list) / INFERRED (effect).

##### 3.9 `scripts/gate_status.py` tree ids
- `::_in_scope` (code scope `t2c`) excludes `benchmarks/` and `*.md` outside `tasks/`/`HANDOFF.md`. Its comment (l.~166-183) says the exclusion rests on a survey ("no collected test reads markdown"; "nothing under tests/ imports benchmarks") that nothing re-runs. **SILENT if the restructure puts gate-relevant code under `benchmarks/`** or makes a collected test read a `.md` outside `tasks/` (its edit would not stale the tiles). Note `benchmarks` imports `tests.wildcard_helpers` (comment, FIRST-HAND) -- moving that helper breaks benchmarks outside the gate (silent). Any rename changes both tree ids, so all ledger rows go stale (expected, harmless). FIRST-HAND.

#### 4. Gate tiling

- `formal/verify.sh::run_conf_tile` (FIRST-HAND): collects `$dir` fresh (`pytest <dir> -q --collect-only`), keeps lines matching `^[^[:space:]]+\.py::`, assigns node `NR-1` to tile `(NR-1) mod K`. Asserts per tile: global floor on the TOTAL, tile size == partition arithmetic, tile non-empty, and every selected node passes (tile floor = its exact size). Node ids go via an `@argfile` under `.gate-runs/` (since 2026-10-03b, Windows 32k argv limit).
- Renaming/moving test files DOES reshuffle tile membership (collection order is path-sorted). **Nothing cares about membership**: no per-tile floor is recorded anywhere, and `gate_status.py` keys verdicts on the tree id, which any rename changes anyway (all ledger rows go stale -- expected). FIRST-HAND (code) / INFERRED (no other consumer: grep found none).
- What CAN bite after a reshuffle (INFERRED): (1) latent ORDER dependence between test modules that never shared a tile/process before -- see section 7's legacy-v3 class-registry hazard, which is exactly import-order dependent; (2) longer node ids (deeper paths) grow the argfile, harmless now that argv is not used.
- Moving a file across the `tests/` / `formal/conformance/` boundary is the only tiling-adjacent hard red: `MIN_TESTS_ALL` / `MIN_CONF_ALL` are zero-headroom per-directory floors (section 3.1).
- Hypothesis example database (`.hypothesis/`, gitignored) is keyed by test identity; renames orphan stored failing examples -> silent loss of local regression replays. Low impact. INFERRED.

#### 5. Lean side

- 43 tracked `formal/**/*.lean` files contain 281 lines naming a listed module/class (`index_v4` 186, `zanzibar_utils_v1` 89, `NodeV4` 6, `ResidueV1` 2, `EdgeV4` 1, `DeltaOutboxV1` 1). All sampled hits are inside `/- ... -/` / `/-! ... -/` doc comments (e.g. `GraphIndex/Leaf.lean:10`, `GraphIndex/ObjStarWrite.lean:40`, `GraphIndex/CascadeInv.lean:311`); grep for a listed name inside a Lean string literal (`"...`): 0 hits. FIRST-HAND.
- **No checker resolves them**: `anchor_check.py` reads only `formal/CORRESPONDENCE.md`; `statement_pin.py::strip_comments` removes `--` and nested `/- -/` (covering `/--` and `/-!`) before pinning statements/definitions; `claim_rot.py` Lean bodies go through the same `strip_comments`. So the Lean refs are cosmetic and rot silently. FIRST-HAND.
- Cost note (INFERRED): editing those comments touches 43 Lean files and forces a `lake build` of them and their dependents in the `lean` phase -- pure build time, no assurance gained. Recommend leaving Lean comments for a separate docs pass (or not at all; `CORRESPONDENCE.md` is the map).
- The Lean conformance channel (`formal/conformance/runner.py` -> `zcli`) passes JSON corpora, not module paths (FIRST-HAND: `runner.py` subprocess call is `[exe, req_path]`).

#### 6. Frozen docs

Occurrence counts of listed names (grep -oE, 2026-10-05, FIRST-HAND):

| tree | occurrences | files | checked by a resolver? |
|---|---|---|---|
| `docs/history/` | 240 | 9 | NO |
| `formal/history/` | 116 | 11 | NO |
| `docs/specs/` | 41 | 4 | NO |
| `docs/architecture/` | 77 | 10 | NO |
| `docs/*.md` (other) | 740 | 54 | NO (only `.md` link targets in `LINKED_DOCS`) |
| `formal/*.md` (non-history) | 313 | 6 | ONLY `formal/CORRESPONDENCE.md` (225 occurrences) via anchor_check/claim_rot |
| `tasks/*.md` open | 153 | 28 | `## Read first` sections only (check 14; 25 lines in 21 rows) |
| `tasks/closed/*.md` | 221 | 69 | NO (check 14 skips closed rows) |
| root `CLAUDE.md` 25, `README.md` 35, `HANDOFF.md` 1, `formal/HANDOFF.md` 4, `formal/FINAL_REVIEW.md` 29 | | | NO |

- Checkers that WALK history/frozen dirs: `scripts/handoff_lint.py::HISTORY_DIRS = ('docs/history', 'formal/history')` -- but only for the liveness header in the first 5 lines and ledger ordering/row ids, never for code paths. `doc_counts.py::check_corpus_count_prose` explicitly skips any path containing `history` and does not glob `docs/specs/`. FIRST-HAND.
- **Verdict: NO hard conflict.** No checker resolves code anchors inside a frozen doc, so a move cannot redden the gate through them, and they need not be edited. They rot silently as intended ("Read them for METHOD, never for state", CLAUDE.md). A rename table (old -> new) in the TK120 plan doc is enough to keep them navigable. FIRST-HAND (checker scope) / INFERRED (sufficiency).
- Note: FROZEN docs also live OUTSIDE the history dirs (closed-item ACTIVE-PLAN docs under `docs/`, e.g. `docs/tk74-staleness-net-2026-09-18.md` 49 refs, `docs/tk108-userset-tuplesets-2026-09-27.md` 37, `docs/tk107-tainted-tupleset-removal-2026-10-05.md` 24, `docs/tk121-stall-recovery-2026-10-04.md` 21, `docs/specs/connected-store-spec.md` 14; ~36 files whose first 8 lines contain "FROZEN" cite old names -- approximate, the header grep also matches docs that merely mention the word). A blind repo-wide sed over `docs/` would EDIT these frozen docs -- **the sed must exclude every FROZEN doc, not just the two history dirs.** FIRST-HAND (counts) / approximate (FROZEN detection).

#### 7. Database

Explicit `__tablename__` on every live table (FIRST-HAND, grep): `index_v4/models.py` -- `StoreV4`="store_v4", `NodeV4`="node_v4", `EdgeV4`="edge_v4", `ResidueV1`="residue_v1", `ResidueRefV1`="residue_ref_v1", `DeltaOutboxV1`="delta_outbox_v1"; `setengine/models.py` -- `TupleV1`="tuple_v1"; `connectedstore/models.py` -- `SchemaV4`="schema_v4", `TupleLogV1`="tuple_log_v1", `IndexCursorV1`="index_cursor_v1". Named constraints/indexes also embed the suffix: `node_v4_unique_constraint`, `edge_v4_unique_constraint`, `ix_edge_v4_store_object`, `residue_v1_unique`, `residue_ref_v1_unique`, `ix_residue_ref_v1_store_object`, `ix_delta_outbox_v1_store_id_id`, `tuple_v1_unique`, `ix_tuple_log_v1_store_id_id`, `index_cursor_v1_unique`; FKs are strings `foreign_key="store_v4.id"` / `"node_v4.id"`.
- **A CLASS rename can leave the DB untouched** as long as `__tablename__`, constraint names and `foreign_key="<table>.id"` strings are NOT touched. A sed on `\bNodeV4\b` does not hit `node_v4` (case differs) -- but a case-insensitive sed, or a "drop the suffix everywhere" regex like `_v[0-9]\b`, WOULD silently rename tables/constraints = an unannounced schema migration for any persisted PostgreSQL store. FIRST-HAND (names) / INFERRED (effect).
- No migrations exist (no alembic, grep `migrat|alembic` 0 hits in code). No raw SQL naming a table in production code (only `PRAGMA busy_timeout`; `tests/dbengine.py` does `DROP SCHEMA public CASCADE`, name-agnostic). FIRST-HAND.
- Tests asserting table names: only `tests/test_reads.py` (SQL statement filters on `'edge_v4'`/`'node_v4'`, section 2 row f). `tests/test_setengine_storage.py:26` comment only. FIRST-HAND.
- **TRAP (string inside code, FIRST-HAND `index_v4/models.py:89-90`)**: `Relationship(sa_relationship=RelationshipProperty(foreign_keys='[EdgeV4.subject_id]'))` and `'[EdgeV4.object_id]'` -- the CLASS name inside a string, resolved lazily by SQLAlchemy at mapper configuration. A word-boundary sed catches it; an IDE/AST "rename symbol" refactor does NOT -> loud error at first mapper use, not at import.
- **TRAP (class-registry collision, import-order dependent)**: `legacy/index_v3.py` defines `class Node(SQLModel, table=True)` and `class Edge(SQLModel, table=True)` with NO `__tablename__` (default table names `node`/`edge`) and a module-level `create_engine('sqlite:///database.db')`; it is imported by collected tests `tests/test_index.py` and `tests/test_integration.py`, so it shares SQLModel's global metadata/registry with the live models in the same pytest process. If the restructure names the live classes `Node`/`Edge`: (1) the string `'[Edge.subject_id]'` becomes ambiguous in the declarative registry (SQLAlchemy "multiple classes found for path"); (2) if `__tablename__` is also dropped, the default `node`/`edge` collides with legacy v3's tables ("Table already defined for this MetaData"). Both are loud BUT only when `legacy.index_v3` was imported first in that process -- i.e. they depend on which tile a test lands in (section 4), so they can pass in one tiling and fail in another. Avoid: do not give live classes the bare names `Node`/`Edge` while `legacy/index_v3.py` is importable, or retire/re-home v3 first. FIRST-HAND (code) / INFERRED (SQLAlchemy behaviour, not executed).
- **TRAP (NodeV2 name collision)**: `zanzibar_utils_v1.py:195 class NodeV2(Node)` subclasses `legacy.index_v2.Node` (imported at `zanzibar_utils_v1.py:8`), while `tests/test_index.py:5` binds a DIFFERENT class under the same name: `from legacy.index_v2 import ..., Node as NodeV2`. A repo-wide sed of `NodeV2` treats two unrelated classes as one. And renaming the schema-layer class to `Node` gives `class Node(Node)`, which rebinds the module-global `Node` to the subclass (legal Python; any later `Node(...)` in that module silently means the subclass). FIRST-HAND.

#### 8. Packaging / config

- `pytest.ini` (FIRST-HAND): no `testpaths` (deliberate). The `UnprovenExtensionWarning` filter is **`ignore:UNPROVEN:UserWarning` -- matched by MESSAGE PREFIX and base category, NOT by a dotted module path** (its comment says a dotted category would import the module at config time). So a module move does NOT break it. The only old name in the file is in that comment (cosmetic). `--strict-config`/`--strict-markers` unaffected. `UnprovenExtensionWarning(UserWarning)` is defined at `zanzibar_utils_v1.py:1392`; its docstring (l.1400) tells users to filter by `category=` -- class-based, survives a move.
- `tests/conftest.py`: imports `setengine.setops` (pyroaring guard), `collect_ignore = ['test_postgres_ha.py']` (basename, relative to `tests/`), fixture dir `Path(__file__).parent / "fga_schemas"`. Moving `test_postgres_ha.py` out of `tests/` silently drops the `collect_ignore` (then the module would be collected without a DSN -- it is described as "dropped at COLLECTION"; the module-level `if` at `tests/conftest.py` ~l.80 only drops it when no DSN is set; in a subdir it would be collected and hit `tests/dbengine.py`'s DSN handling -> a skip or error, either of which the tile phase reds since `skipped` must be 0 outside the declared budget). Loud, INFERRED; FIRST-HAND config.
- No `pyproject.toml`, `setup.py`, `setup.cfg`, `tox.ini`, `MANIFEST`, CI config (`.github/`, `.gitlab-ci.yml`) or pre-commit config is tracked (FIRST-HAND, `git ls-files`). Import resolution relies on `python -m pytest` run from the repo root (cwd on `sys.path`) -- `verify.sh` always does that (l.1214, l.1313). Packages with `__init__.py`: `connectedstore`, `formal`, `formal/conformance`, `index_v4`, `legacy`, `setengine`, `tests/scenarios`. **`tests/` has NO `__init__.py`** (namespace import `from tests import oracle`, and `test_grid_independence` asserts `__module__ == "tests.oracle"`). Adding `tests/__init__.py`, or moving tests into subdirs without one, changes pytest's module naming (rootdir/basename rules) -- duplicate basenames across new subdirs = "import file mismatch" (loud). INFERRED (pytest prepend mode).
- `pyrefly.toml`: interpreter paths only (the stale `avery` path), no module list -- unaffected.
- `.gitattributes`: pins `tasks/**` and `scripts/task.py` to `eol=lf` only. `core.autocrlf=true`.
- **`.gitignore` landmines for NEW directory names** (FIRST-HAND): `lib/`, `lib64/`, `build/`, `dist/`, `develop-eggs/`, `downloads/`, `eggs/`, `parts/`, `sdist/`, `var/`, `wheels/`, `target/`, `instance/`, `cover/`, `env/`, `ENV/`, `venv/`, `site` (`/site` root only), `out` and `gen` (NO slash: match a file OR dir of that name ANYWHERE), `*.spec`, `*.manifest`, `local_settings.py`, `database.db`. `git mv` into such a dir keeps the moved files tracked, but **any NEW file created there later is silently untracked** and is also outside the gate's tree id (`gate_status.py` hashes tracked + untracked-NON-ignored). A package named `build/`, `lib/`, `gen/` or `out/` is a silent trap; `build` is additionally skipped by `test_invariants_docstring_matches_body` (section 2 row m). INFERRED (git semantics).
- Benchmarks: `benchmarks/*.py` insert the repo root on `sys.path` and import the old modules (5 top-level import lines naming old modules or `tests.`, FIRST-HAND count); outside the gate and outside `t2c` -> they break silently on a move. They also import `tests.wildcard_helpers` (gate_status comment).

#### 9. Silent-after-rename (pass while wrong) -- collected

1. `formal/conformance/test_graphadmission_scope_pin.py` / `test_w4fragment_scope_pin.py` `"evidence"` strings (>= 22 citing old paths) are shape-checked, never resolved -> rot green. (sec 2 row c)
2. `formal/conformance/doc_counts.py::TOOLING_FILES` is keyed by test-file basename; renaming a tooling test re-classifies it as a differential and inflates the Lean-vs-Python figure; `--check` compares against its own regeneration, so it stays green. (3.5)
3. Module SPLIT of `zanzibar_utils_v1.py` (if the plan splits core vs boolean compile): `tests/test_refused_shape_comments.py::FILES`, `tests/test_tk116_oracle_only_setengine.py::_SRC`, `tests/genswarm.py` (`inspect.getsource(Z)`), and `tests/test_reg15_security_hardening.py::_GUARDED_MODULES` (for a split of core.py/processor.py) all scan a FIXED file list; code moved to an unlisted file escapes the check, and only "non-empty"/"count equal" guards exist. Today's counts may go red (loud) but FUTURE additions to the new file are never scanned (silent forever). (sec 2 rows g-j)
4. `anchor_check.py` bare-`::Sym` inheritance: a stale plain `` `old/file.py` `` mention no longer supplies inheritance, so a bare anchor can silently resolve against the PREVIOUS file in the same paragraph/cell. (3.2)
5. `claim_rot.py --generate` after a mass rename launders any behavioural change made in the same commit: ~171 Python pin rows move at once (153 re-keyed, 18 re-hashed outside the moved files). The gate is loud, the FIX is the silent part. (3.3)
6. `caplog.at_level(..., logger='index_v4.core')` in two tests becomes a no-op; tests still pass via root propagation. (sec 2 row e)
7. A case-insensitive or `_v\d` suffix-stripping regex would rename `__tablename__`s, constraint/index names and FK strings = an unannounced DB schema change for persisted PostgreSQL stores; SQLite tests would still pass (fresh DBs). (sec 7)
8. New package dirs named like a `.gitignore` pattern (`build`, `lib`, `gen`, `out`, `env`, `var`, ...): later files are silently untracked and outside the gate tree id. (sec 8)
9. The REWRITE TOOL itself (FIRST-HAND measurement 2026-10-05, python over `git ls-files '*.py' '*.md' '*.lean' '*.txt'`): **418 tracked files cite an old name; 325 of them contain non-ASCII bytes; working copies are mixed -- 173 CRLF, 245 LF-only.** Per user memory, PowerShell `Get-Content/Set-Content` corrupts non-ASCII, and `python - <<'PY'` decodes the script as cp1252 so non-ASCII patterns silently match 0 times. The sed/rewrite must be byte-preserving (read/write bytes, keep each file's EOL; `tasks/**` must stay LF per `.gitattributes`) and must assert a non-zero, expected replacement count per file -- otherwise a "successful" rewrite that matched nothing (or rewrote every line ending) passes. Also observed live during this census: `LC_ALL=C grep -P` on Git Bash errors per file and a naive count loop reported "0 files with non-ASCII" -- the instrument fake-passed.
10. `conf-rest` legacy phase after renaming `test_conformance_remove.py`: `--ignore` of a missing path is a no-op, so it runs the whole dir and still clears its floor. (3.1; INFERRED)
11. Benchmarks and `formal/probes/*` break silently (outside the gate and outside `t2c`). (sec 2 row q, sec 8)

#### Probe source (provenance for 3.3; the `.py` file was deleted after the run so only this file remains)

```python
# run from repo root with the env interpreter, read-only
import re, sys; sys.path.insert(0, '.')
from formal.conformance import anchor_check, claim_rot
doc = claim_rot.DOC.read_text(encoding='utf-8')
names = r'\b(StoreV4|NodeV4|EdgeV4|ResidueV1|ResidueRefV1|DeltaOutboxV1|TupleV1|SchemaV4|TupleLogV1|IndexCursorV1|NodeV2|zanzibar_utils_v1|index_v4|legacy|store_v4|node_v4|edge_v4|residue_v1|residue_ref_v1|delta_outbox_v1|tuple_v1|schema_v4|tuple_log_v1|index_cursor_v1)\b'
cache, seen, hit = {}, set(), {}
for _, f, sym in anchor_check.extract_anchors(doc):
    k = f'{f}::{sym}'
    if k in seen or not f.endswith('.py'): continue
    seen.add(k); got = claim_rot.anchor_body(f, sym, cache)
    if got and re.search(names, got[1]): hit[k] = 1
# output 2026-10-05: 255 unique Python anchors | 153 in a moving file | 65 bodies mention a listed name | 18 of those outside moving files
```

## 5. Plan (revised 2026-10-06b and APPROVED by the user 2026-10-06b: "just do the whole thing")

Supersedes the 2026-10-06 draft (flat layout, tables kept), which was never acted on.
User decisions, 2026-10-06b: **one package**, because the code may be released as a library.
`zanzibar` is free on PyPI (user checked). **Lean stays outside the package. Delete
`legacy/`**, but first confirm every behaviour it tested is still tested. **Rename the
tables** and break backwards compatibility freely (no stored databases, no users). The rest
are the model's calls (`CLAUDE.md` "Who decides"), labelled REASONED.

### 5.0 First-hand checks behind this revision (READ 2026-10-06)

- **Legacy coverage.** `tests/test_index.py` + `tests/test_integration.py` collect 46 cases.
  28 run only against legacy code: 7 functions x `IndexV1/V2/V3Polyfill` (21) and 7 functions
  x `v3` (7). **Every one of those 14 functions is also parametrized on a v4 backend that
  runs the identical body** (`IndexV4Polyfill`; `v4`). So deleting the legacy parameters
  loses no assertion on live code; it only stops checking the dead implementations.
- Nothing in `.gitignore` matches `src`, `zanzibar`, `schema` or `graphindex`. setuptools
  82.0.1 and pip 26.1.2 are in the env.
- Liveness of tracked `*.md` (bolded banner in the first 8 lines): 37 FROZEN and 19
  ACTIVE-PLAN outside the history dirs, plus everything under `docs/history/`,
  `formal/history/` and `docs/specs/`.
- `formal/` and `tests/` are themselves Python packages (`formal/__init__.py`,
  `formal.conformance.*`, `tests.oracle`) and rely on the repo root being on `sys.path`.

### 5.1 Target layout

```
pyproject.toml                 distribution "zanzibar"; src layout; deps from requirements.txt
src/zanzibar/__init__.py       docstring + __version__ only (no eager imports: avoids import cycles)
src/zanzibar/schema/           from zanzibar_utils_v1.py, split (5.3)
src/zanzibar/graphindex/       from index_v4/ (+ multiset.py from legacy/index_v1.py)
src/zanzibar/setengine/        from setengine/
src/zanzibar/connectedstore/   from connectedstore/
tests/  formal/  benchmarks/  scripts/  docs/  tasks/   unchanged, outside the package
```

- **Lean stays in `formal/` (REASONED, user agreed).** It is the evidence, not the library. A
  wheel ships Python only, and the Lean build needs elan and mathlib. `formal/conformance/`
  is a test suite of the library, like `tests/`. `tests/oracle.py` stays in `tests/`
  because its independence contract forbids importing the library.
- **How the gate finds the code.** `pytest.ini` gets `pythonpath = src`, and `verify.sh`
  python invocations get `src` on `PYTHONPATH`. So the gate tests THIS checkout, in any
  worktree, with nothing installed. Separately, `pip install -e .` into the conda env makes
  benchmarks, probes and prototypes work without path hacks.
  `tests/conftest.py` refuses to run if `zanzibar.__file__` is not under `<rootdir>/src/`,
  which catches a stale install shadowing the tree. It gets a sabotage check.
- Subpackage names: `graphindex` (pairs with `setengine`). `connectedstore` is kept: `store`
  would read as the `Store` table class.

### 5.2 Name map

| old | new | table (old -> new) |
|---|---|---|
| `StoreV4` | `Store` | `store_v4` -> `store` |
| `NodeV4` | `Node` | `node_v4` -> `node` |
| `EdgeV4` | `Edge` | `edge_v4` -> `edge` |
| `ResidueV1` | `Residue` | `residue_v1` -> `residue` |
| `ResidueRefV1` | `ResidueRef` | `residue_ref_v1` -> `residue_ref` |
| `DeltaOutboxV1` | `DeltaOutbox` | `delta_outbox_v1` -> `delta_outbox` |
| `TupleV1` | `RelationTuple` (not `Tuple`: `typing.Tuple`) | `tuple_v1` -> `relation_tuple` |
| `SchemaV4` | `SchemaRecord` | `schema_v4` -> `schema_record` (SCHEMA is an SQL keyword) |
| `TupleLogV1` | `TupleLog` | `tuple_log_v1` -> `tuple_log` |
| `IndexCursorV1` | `IndexCursor` | `index_cursor_v1` -> `index_cursor` |
| `NodeV2` | deleted (dead) | -- |

Constraint and index names follow their table (for example `node_v4_unique_constraint`
becomes `node_unique_constraint`). The existing aliases `Node = NodeV4` etc. are deleted.
**Unchanged:** `Filter`, `Rule`, `RewriteFilter`, `RelationalTriplePattern` (golden reprs) and
`LookupResult`.

| old module path | new |
|---|---|
| `zanzibar_utils_v1.py` / `zanzibar_utils_v1` | `src/zanzibar/schema.py` / `zanzibar.schema` in step 1, then the package in step 2 |
| `index_v4/` / `index_v4` | `src/zanzibar/graphindex/` / `zanzibar.graphindex` |
| `setengine/` / `setengine` | `src/zanzibar/setengine/` / `zanzibar.setengine` |
| `connectedstore/` / `connectedstore` | `src/zanzibar/connectedstore/` / `zanzibar.connectedstore` |
| `legacy/index_v1.py::MultiSet` | `src/zanzibar/graphindex/multiset.py::MultiSet` |
| `tests/test_index_v4{,_core,_models}.py` | `tests/test_graphindex{,_core,_models}.py` |

### 5.3 Split of the schema module (step 2)

| module | from §3 F | notes |
|---|---|---|
| `schema/errors.py` | S1 + the S5 error types | leaf |
| `schema/ast.py` | S5 AST + `_iter_directs`, `_iter_ttus` (S7) + `_directs_only` (S9) | breaks the S7<->S9 cycle |
| `schema/rules.py` | S2 + S3 + S4 + `_restriction_pattern`, `_rewrite_rule`, `_assert_ttu_parent_types_cover_admission` (S9) | breaks the S9<->S11 cycle |
| `schema/parser.py` | S6 + S7 | |
| `schema/boolean.py` | S11 | |
| `schema/compile.py` | S8 + S9 + S10 + S12 | imports `boolean` one way |
| `schema/json_frontend.py`, `schema/unparse.py`, `schema/reports.py` | S13, S14, S15+S16 | |
| `schema/__init__.py` | re-exports the names product code and tests import today | private names are imported from their submodule |

The exact symbol -> module table is generated from the AST at split time and recorded here.

### 5.4 Execution: four commits, the full ten-phase gate green before each

**Rules for every step (REASONED).**
- No shims at old paths.
- No behaviour change inside a move or rename commit.
- Rewrites go through one tracked byte-preserving script, `scripts/tk120_rename.py`. It
  keeps CRLF/LF, applies the path form BEFORE the dotted form, and refuses an unexpected
  hit count. It is deleted when `TK120` closes.
- **Not rewritten:** FROZEN docs, ACTIVE-PLAN docs, the history dirs, closed task rows,
  this doc and its row. They keep the old names; §5.2 is their key. ACTIVE-PLAN docs get
  one dated pointer line at the top instead.

1. **Commit A: delete `legacy/`.**
   - Move `MultiSet` into `index_v4/multiset.py`.
   - Delete `NodeV2` and the `legacy.index_v2` import.
   - Delete `legacy/`, the V1/V2/V3 polyfills and the `v3` backend.
   - Lower `MIN_TESTS_ALL` by exactly 28, with provenance.
   - Update `CLAUDE.md` Layout.
2. **Commit B: package move and renames.** This covers the class, table and module renames,
   `pyproject.toml`, `pythonpath`, and the conftest guard.
   - Census first: the bare `setengine`/`connectedstore` tokens were never censused for
     non-module uses (local variables, attributes, prose), so classify those contexts
     before rewriting.
   - **Hand-fixed after the script:**
     - `tests/test_reads.py` SQL substring filters: `'edge'` would match far more than
       `'edge_v4'` did, so they go to word-bounded patterns.
     - The `foreign_keys='[EdgeV4.subject_id]'` strings.
     - The alias lines and `__all__` duplicates.
     - `caplog` logger names.
     - `_GUARDED_MODULES`.
     - `verify.sh`'s `PYTHONPATH`.
   - **Pins:** `claim_rot.py --generate` only after a check that every changed pinned body
     equals its old body with the name map applied. Regenerate the `doc_counts` block for
     the renamed test files.
   - **PostgreSQL leg** (`scripts/pg_local.sh`) after this commit's gate, because the tables
     changed.
3. **Commit C: split `schema.py` into `schema/`** (5.3). Moves only; bodies are identical,
   so the pin rows only re-key.
   - The fixed-file scanners (`test_refused_shape_comments.py::FILES`/`MIN_HEADERS`,
     `test_tk116::_SRC`, `test_reg15::_GUARDED_MODULES`, `genswarm` `getsource`) change to
     package globs with a nonzero floor, so a new file cannot escape them. Sabotage each.
   - `test_grid_independence`'s `__module__` expectation follows `parse_schema_ast`.
4. **Commit D: prose sweep and close.** Covers LIVING docs, `CLAUDE.md`, `README.md`, the
   open task rows, and the ACTIVE-PLAN pointer lines. Then delete the rename script, close
   `TK120`, write the session log and banner, run the `lean` phase, and commit.

Each of B and C ends with a `git grep` for the old names outside the excluded paths. The
expected result is zero hits.

## 6. Executed (2026-10-06c; first-hand unless marked)

**Commits.** A = `86e3298` (legacy/ deleted; full ten-phase gate green before it). B+C+D =
the commit that closes `TK120` (one commit at the user's request, 2026-10-06; full gate once,
before it).

### 6.1 The rename (B), by a byte-preserving script

The script (`scripts/tk120_rename.py` while the item ran; deleted at close, so this section is
its record) applied the §5.2 map to 444 tracked text files, skipping the FROZEN / ACTIVE-PLAN
docs, the history dirs, `docs/specs/`, closed task rows, `benchmarks/results/` and this doc,
and rewriting only the `## Read first` section of the `TK120` row. Path forms were applied before dotted forms.
`setengine`/`connectedstore` were rewritten only as paths, `from`/`import` targets,
`<pkg>.<submodule>` and backticked names, because the census showed both are also backend
LABELS in strings (`_fmt(mism, 'oracle', 'setengine')`) and part of a doc filename
(`tk116-oracle-only-setengine-...`). Dry-run counts, 2026-10-06: 286 files changed; e.g.
`index_v4/` path 767, `zanzibar_utils_v1.py` path 418, `NodeV4` 395, `EdgeV4` 283, table
`node_v4` 35. The only residue hit afterwards is a provenance sentence in
`src/zanzibar/graphindex/multiset.py`.

Hand fixes after the script: the `Node = NodeV4` alias lines and duplicate import / `__all__`
names in `graphindex/{models,__init__,core}.py`; `handoff_lint.py::MENTION_ROOTS` -> `src/`;
SQL filters word-bounded in `tests/test_reads.py::_mentions_table` and
`benchmarks/profile_r6.py` (a bare `'node'` substring would also match `object_node_id`; the
tests already assert `== 1` on positive cases, so a filter matching nothing is red);
`verify.sh` exports `PYTHONPATH=<repo>:<repo>/src`; `pytest.ini pythonpath = src`; new
repo-root `conftest.py`; `pyproject.toml`; `pyrefly.toml search-path`.

**Pin laundering check (§4 silent item 1).** Before any re-pin, every one of the 486
CORRESPONDENCE anchors had its claim_rot body snapshotted. After B, each new body was compared to
its old body with the full rename rules applied (classes, tables, paths, modules): `compared 486
anchors: 0 problem(s), 0 new`. Only then `claim_rot.py --generate`.

### 6.2 New pins, each sabotaged (literal output)

- `tests/test_tk120_package_layout.py::test_a_foreign_zanzibar_is_refused` -- the root
  `conftest.py` guard. Sabotage: the `_require_this_checkouts_library()` call deleted ->
  `FAILED ...::test_a_foreign_zanzibar_is_refused`, `1 failed, 3 deselected`; restored ->
  `1 passed`. Limit: `test_children_import_this_checkouts_src` cannot go red in a checkout
  whose editable install points at itself; it guards the no-install / foreign-install cases.
- Scope pins (`test_w4fragment_scope_pin.py` / `test_graphadmission_scope_pin.py`
  `::_resolve_reported_by`) now import the module NAMED by `reported_by` and require the symbol
  to be DEFINED there (Fable review F4). Sabotage: one row pointed at
  `src/zanzibar/schema/__init__.py::w4_fragment_report` (which re-exports it) -> `AssertionError:
  ... is not a callable DEFINED in src/zanzibar/schema/__init__.py`, `1 failed, 9 passed`.

### 6.3 The split (C)

`src/zanzibar/schema.py` -> 9 submodules, code moved VERBATIM by a tool that asserted the
chunks tile the source exactly and refused any import cycle. Both §3 F2 cycles dissolved:
`_iter_directs`/`_iter_ttus`/`_directs_only` -> `syntax`; `_restriction_pattern`/
`_rewrite_rule` -> `rules`; `_assert_ttu_parent_types_cover_admission` -> `boolean` (it
isinstance-checks `LeafFamily`/`PDerivedTTU`, so it could not go to `rules`). `RuleSet`'s
`'CompiledBooleans'` is a string annotation only and imports nothing. Sibling imports, leaf
first: errors, syntax <- rules <- parser, boolean <- compiler; unparse <- json_frontend;
reports <- parser, boolean. `__init__` re-exports the 64 public names plus the 4 private
helpers the suites import (`_iter_directs`, `_member_types`, `_parse_schema_ast_unchecked`,
`_plan_leaves`). No module-level state, `global` or undefined name (AST check).

Anchors: 350 `schema.py::Sym` cites re-homed by symbol, 60 plain mentions -> `src/zanzibar/schema/`.
Twelve bare `::Sym` anchors in CORRESPONDENCE.md then inherited the wrong submodule; the anchor
check went red on all twelve and each was made explicit. Pin check in split mode: 484 of 486
bodies identical; the 2 that differ are test fixtures whose only change is path strings
(read first-hand), then re-pinned. Two cites name symbols that no longer exist anywhere, and
did before this item (`PDerivedTuplesetTTU`, deleted by `TK107`, in
`docs/tk106-triage-2026-09-26.md`; `_split_pure` in a `GraphIndex/Leaf.lean` comment): left
as found.

`tests/genswarm.py::_schema_source` reads every submodule; its two derivations equal the
pre-split ones (`('computed', 'ttu', 'userset')`, `('closure', 'userset-storage')`).

Symbol -> submodule (the key for any old `zanzibar_utils_v1.py::Sym` cite):

| module | top-level names |
|---|---|
| `errors` | `_IDENTIFIER_RE`, `_require`, `AdmissionRejected`, `ClosureFanoutExceeded`, `CyclicDerivedDependency`, `DoublyBridgedShapeError`, `IDENTIFIER_CHARSET`, `IndexResourceLimit`, `is_valid_identifier`, `PathCountExceeded`, `UnsupportedByGraphIndex`, `validate_node_identifiers`, `validate_write_identifiers` |
| `syntax` | `_directs_only`, `_iter_directs`, `_iter_ttus`, `_RESERVED`, `Computed`, `Direct`, `Exclusion`, `Expr`, `Intersection`, `Restriction`, `SchemaAST`, `TTU`, `Union` |
| `rules` | `_restriction_pattern`, `_rewrite_rule`, `Entity`, `EntityPattern`, `Filter`, `norm_pred`, `parse_relation_rule`, `RelationalTriple`, `RelationalTriplePattern`, `replace_relation`, `RewriteFilter`, `Rule`, `RuleSet`, `SchemaInfo` |
| `parser` | `_iter_refs`, `_parse_schema_ast_unchecked`, `_RelationParser`, `_tokenize_relation_body`, `_validate_ast_consistency`, `_validate_ast_references`, `_validate_declared_name`, `_validate_stratified_negation`, `_validate_tuplesets_direct`, `parse_schema_ast` |
| `boolean` | `_assert_ttu_parent_types_cover_admission`, `_build_plan_tree`, `_compile_check_fn`, `_compile_stars_fn`, `_contains_boolean`, `_emit_leaf_expr`, `_is_pure`, `_member_types`, `_mentions`, `_plan_deps_and_fanout`, `_plan_leaves`, `_stratify`, `compile_boolean_schema`, `CompiledBooleans`, `compute_taint`, `DependentEdge`, `DerivedFamily`, `LeafFamily`, `LeafSpec`, `PClosureLeaf`, `PDerivedComputed`, `PDerivedTTU`, `PDerivedUserset`, `PExclusion`, `PIntersection`, `Plan`, `PUnion` |
| `compiler` | `_emit_expr`, `_expand_object_wildcard_shapes`, `_node_removal_fence`, `_reject_doubly_bridged_shapes`, `_reject_object_wildcard_scope`, `_restriction_filter`, `_validate_ttu_tuplesets`, `_warn_unproven_extensions`, `compile_ruleset`, `derive_schema_info`, `parse_openfga_schema`, `schema_filters`, `unproven_extensions`, `UnprovenExtensionWarning`, `wildcard_userset_restriction_shapes` |
| `unparse` | `unparse_schema_ast` |
| `json_frontend` | `_json`, `_json_restrictions`, `_json_rewrite`, `_reject_duplicate_json_keys`, `_validate_json_round_trip`, `_validate_json_wildcard`, `openfga_json_to_dsl`, `parse_openfga_json` |
| `reports` | `_ga_rule_arms`, `_w4_children`, `_w4_computed_only`, `_w4_computed_or_direct`, `_w4_computed_refs`, `_w4_directs_all`, `_w4_directs_union`, `_w4_ttu_arms`, `_w4_tuple_fields`, `graph_admission_report`, `GRAPH_ADMISSION_REPORTED_FIELDS`, `GraphAdmissionReport`, `W4_FRAGMENT_FIELDS`, `w4_fragment_report`, `W4FragmentReport` |

### 6.4 Refused-shape scanner scope

Globbing the WHOLE library found 2 in-scope raises the fixed list never scanned:
`graphindex/wildcard.py::_reject_star_self_edge` / `_reject_latent_star_cycle`. They refuse
WRITES that would close a data cycle (explained in their docstrings), not schema shapes, so
the user rule does not cover them. Decision (REASONED): glob the schema PACKAGE plus the two
files the list already named. Floors per group: schema package 37, oracle 16, setengine
engine 1; anti-vacuity floor of in-scope raises 25 (boolean 2, compiler 11, json_frontend 3,
parser 9). Sabotage: a new `schema/zz_sabotage.py` with an uncommented `_validate_new_shape`
raise -> `FAILED ...[src/zanzibar/schema/zz_sabotage.py]`, `1 failed, 29 passed`; removed ->
`28 passed`.

### 6.5 Caught by the final gate: patches on the facade (first-hand)

The first full gate after B-D was RED in all four `tests/` tiles (5 failures, two tests). Both
tests patched a private schema function on the `zanzibar.schema` OBJECT. After the split the
callers bind the name in their own submodule, so a patch on the facade reaches no caller:
`tests/test_tupleset_must_be_direct.py::test_rewrite_keeps_the_old_answers`
(`monkeypatch.setattr(Z, '_validate_tuplesets_direct', ...)` -> AttributeError, the name is
not re-exported) and `tests/test_ttu_tupleset_parent_types.py::test_compile_refuses_parent_types_narrower_than_admission`
(`zu._member_types = ...` -> `DID NOT RAISE ValueError`, the sabotage stopped biting). Both
were LOUD, which is why the gate was run whole. Fixed by patching the defining submodule; for
`_validate_tuplesets_direct` that is BOTH `parser` and `json_frontend`, which each bind it,
matching what the one module-global patch did before. The §3 census missed this shape because
it looked for STRING patch targets and `monkeypatch` on the module name; an AST sweep for
attribute assignment / `setattr` on any `zanzibar.*` alias then found no third case in
`tests/` or `formal/conformance/` (one outside the gate, in a dated probe, wraps the public
`parse_openfga_schema` for its own calls and was left). Re-run: `88 passed` for both modules,
then the full gate.

<!-- END -->
