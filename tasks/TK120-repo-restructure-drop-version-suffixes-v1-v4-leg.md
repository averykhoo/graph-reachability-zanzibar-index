---
id: TK120
title: Repo restructure: drop version suffixes (v1/v4/legacy) and re-lay-out the code
brief: remove version names + sensible layout; plan needs USER APPROVAL before any move
pri: LATER
size: L
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-10-02
moved: 2026-10-02
updated: 2026-10-02
closed:
---

## Goal (user request, 2026-10-02)

Do a repo-wide refactor that **removes the version suffixes** from module, package and
class names and **restructures the code into a layout that makes sense** to a reader
who doesn't know the history. **The details are NOT decided yet:** a plan has to be
drafted and **approved by the user before any file moves**. This row exists so the
intent is not lost; it is not a go-ahead.

## Context, measured 2026-10-02 (first-hand READ unless marked)

- `zanzibar_utils_v1.py` is the only `.py` file at the root and is the LIVE schema layer
  (parsers, `compile_ruleset`, `SchemaInfo`, `RuleSet`, shared error types, plus the
  boolean compile: `CompiledBooleans` / `DerivedFamily` / `LeafFamily`). It dates from
  `10a00c0` (2024-04-14), before any package existed; "v1" refers to nothing current.
  No task or doc records a decision to keep it at the root. Files that import or mention
  it: tests 64, formal 26, index_v4 6, connectedstore 4, benchmarks 4, setengine 1.
- Versioned names in live code: package `index_v4/`; SQLModel classes `StoreV4`,
  `NodeV4`, `EdgeV4`, `ResidueV1`, `ResidueRefV1`, `DeltaOutboxV1`
  (`index_v4/models.py`), `TupleV1` (`setengine/models.py`), `SchemaV4`, `TupleLogV1`,
  `IndexCursorV1` (`connectedstore/models.py`), `NodeV2` (`zanzibar_utils_v1.py`).
- `legacy/` holds v1-v3; live code still imports `legacy.index_v1.MultiSet` and
  `legacy.index_v2.Node` (per `CLAUDE.md` Layout), so those must be re-homed first.
  `legacy/index_v3.py::_add_direct_edge_unsafe` is the same closure algorithm as
  `index_v4/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl` (read side by side
  2026-10-01), so v3 is history, not a separate design.

## Known costs and traps (to be sized properly by the plan)

- Every table carries an EXPLICIT `__tablename__` (`store_v4`, `tuple_v1`, ...).
  Renaming a CLASS therefore need not touch the database; renaming a TABLE is a schema
  migration for any persisted store. Decide separately.
- `formal/CORRESPONDENCE.md` cites `zanzibar_utils_v1.py` 43 times and
  `formal/correspondence_anchor_pin.txt` 48 times (2026-10-02 grep counts), and
  `verify.sh lean` resolves those anchors, so a move reds the gate until the map moves too.
- `formal/history/`, `docs/history/` and `docs/specs/` are FROZEN and cite the old
  paths. They must not be edited; decide whether a compatibility shim or a
  rename table keeps them resolvable.
- Golden snapshots (`tests/snapshots/`) are a byte-identity gate. UNVERIFIED whether
  any golden embeds a module or class name; check before moving anything.
- Possible coupling with the non-boolean / monotone-profile idea discussed 2026-10-01:
  the schema module mixes the core compiler with the boolean compiler, so a split
  could be done in the same pass. Not decided.

## Next action

Draft an ACTIVE-PLAN doc (`docs/<id>-repo-restructure-<date>.md`): the target layout,
the full old -> new name map, a census of every reference (import sites, anchors,
goldens, docs), and an ordered migration with a full gate after each step. Present it
to the user for approval. No moves before approval.

## Read first

- `zanzibar_utils_v1.py` -- the root module the refactor starts from
- `index_v4/models.py` -- the versioned table classes and their explicit `__tablename__`s
- `formal/CORRESPONDENCE.md` -- the anchors the lean phase of `formal/verify.sh` resolves; a move reds them

## Log
