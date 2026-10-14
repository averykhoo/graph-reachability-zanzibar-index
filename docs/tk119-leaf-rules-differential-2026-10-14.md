# `TK119` — the leaf-rule claim becomes a differential test against the Lean definition

**ACTIVE-PLAN, opened 2026-10-14 — the body is provenance, not a living status.** Scout map
for task row `TK119` (the `keyLeafRewrites` row of `formal/CORRESPONDENCE.md` carries a
"50/50 schemas" leaf-rule comparison from a one-off 2026-08-16 probe that no test re-runs).
The DECISION is on the row (2026-10-14 log entry, user-approved): a new `zcli` mode
`"leaf-rules"` that prints `schemaRewritesL S`, and a conformance test that diffs it against
`compile_ruleset`. This doc is what a builder needs to start without re-scouting.
Produced by one scouting agent (`scout-TK119`) on 2026-10-14. No file under `src/`, `tests/`,
`formal/` or `tasks/` was edited. Live state is the task row
(`python scripts/task.py show TK119`), never this file. Corrections append **dated at the
top**, never edited into the body. Freeze it when `TK119` closes.

Provenance labels used on every claim:
- **READ** — first-hand read of the cited `file::symbol` on 2026-10-14.
- **PROBE** — a script under `.scratch/now-next/probes/scout-TK119/` was run on 2026-10-14
  and its literal output is quoted. `.scratch/` is gitignored, so every load-bearing probe
  body is quoted here (sec 9).
- **REASONED** — inference from READ/PROBE facts, not executed.
- **UNVERIFIED** — not checked here.

Line numbers are as of 2026-10-14 and will rot. The `file::symbol` is the anchor.

## Corrections

### Corrections 2026-10-14 (challenge)

Skeptic pass by agent `challenge-TK119`. It re-ran the plan with its own probes under
`.scratch/now-next/probes/challenge-TK119/`: `gen.py` (its own source list, 82 requests),
`lean/Emit.lean` (`lake env lean`, rc 0, 131 s on a loaded machine), and `compare.py` (its own
normaliser, plus sabotage switches). Nothing under `src/`, `tests/`, `formal/` or `tasks/`
was edited. **Verdict: the plan is sound. It needs the changes below before a builder starts.**

**Confirmed (first-hand PROBE unless marked):**
- C1. Over corpus + fixtures + `tk126` + the scout's witnesses + `graphadmission_scope_probes.py::SCHEMA_PROBES`:
  66 sources compile, **62 match as multisets, 4 mismatch** (`tk126` `D`, `D_nested`, `SlXt`, and
  `W3`). The diffs are byte-identical to sec 4. The matched non-empty-leaf count is **43**, so the
  scout's REASONED 43 is now PROBE. Corpus + fixtures alone have 32, reproducing 2026-08-16.
- C2. **Within-key leaf order is equal on every matched source, and so is untainted-half order.**
  Only the order across derived keys differs, on the same 9 sources. That replaces the "REASONED
  only" caveat in sec 3.3. The `LeafRules.lean::schemaRewritesL` docstring fix should say exactly
  this: the untainted half and each key's rules mirror Python; the keys themselves come in
  `sorted(tainted)` order on the Python side.
- C3. **The corpus is blind to merged leaves, proven by sabotage, not only by census.** A Python
  twin of `LeafRules.lean`'s own (S11) sabotage, a closure leaf's union walked only into
  `children[0]` (monkeypatch of `boolean._emit_leaf_expr`), leaves **every corpus and fixture
  source GREEN**. Only `W2`, `W6` and `W3b` go red. `W3`'s `TK132` pin also flips to MATCH, and the
  matched non-empty count drops 43 → 41. So the witnesses are load-bearing, and the old 50/50
  would have passed this mutation.
- C4. Taint is computed independently on each side. Lean derives it itself
  (`Spec/Stratify.lean::isDerived` over `taintedKeys`). `encode.py::schema_to_json` sends only the
  oracle parser's AST in declaration order, never Python's taint set. So the untainted/leaf split
  check is a real second differential on taint (READ).
- C5. `Cli.lean` anchors (`decodeRequest` :176, `decodeMode` :211, `canonJsonArr` :252,
  `fragmentJson` :330, `main` :343, dispatch arms, rc table :101-103), the 50/50 sites
  (`LeafRules.lean:92`, `Audit.lean:1986-1988`), and conf-tile:1/5 = 435 s (ledger
  2026-10-14T08:21) are all as cited. Note the same tile ran 363 s at 00:01, so it is
  load-sensitive (READ).

**Corrections to the body:**
- X1. **sec 7 sabotage numbers describe a different mutation than the one the docstring will
  record.** The scout's monkeypatch wraps `_emit_leaf_expr`, which calls itself through the
  module global. So the patch fires again at each `Union` level and bumps the index once per
  nesting depth, not once. It also moves `RewriteFilter` routing (Directs go through the same
  function). That second effect is the "UNVERIFIED" cause of the 6 refusals: every one is
  `ValueError: RewriteFilter routes outside a leaf family` (PROBE `cmp_offbyone.out`), not a
  collision with a storage leaf. **Use a rule-only bump instead**: edit only the
  `out.append(_rewrite_rule(expr, object_type, leaf))` line (`boolean.py:429`, 2026-10-14). PROBE
  via a patch of `boolean._rewrite_rule`: **47 mismatches, 0 extra refusals**, which is every
  source with a leaf rule, including all 4 `TK132` pins. Do not copy any dry-run count into the
  docstring; record what the real temporary edit prints.
- X2. **"S9" is a Lean-side sabotage name.** It comes from `LeafRules.lean:1402`
  (`keyLeafRewrites` targets public `R`). Applied in Lean, it breaks the BUILD (four rule pins
  plus the disjointness theorem), so it can never drive `zcli`. The row's "S9 shape in
  `_emit_leaf_expr`" is a Python twin of it. As sec 7 says, Python's own I5 check catches that twin
  first. Recommended sabotage set for the docstring: (a) rule-only off-by-one (X1, primary);
  (b) the S11 twin (C3, proves the merged-leaf witnesses and floor bite); (c) S9 twin (proves
  refusal-as-failure); (d) Lean emitter control, see X5.
- X3. **The normaliser's field list (sec 3.2) misses `object_match_wildcards`.**
  `rules.py::RelationalTriplePattern` has it, and `_rewrite_rule` leaves it `None`. Do not use a
  hand list: assert that the fields checked equal `{f.name for f in
  dataclasses.fields(RelationalTriplePattern) if f.init}`, so a future field fails loudly. The
  probe does this. Also assert `then_pattern is not None`, because `Rule.then_pattern` is
  Optional.
- X4. **The floors (sec 6.1) are too weak as counts.** `>= 1` leaf-TTU / merged source survives
  deleting two of the three witnesses, and `compiled >= 50` survives losing a corpus family that
  witnesses pad out. Pin BY NAME instead:
  `{"W1","W5","W3b"} <= leaf_ttu_matched`, `{"W2","W6","W3b"} <= merged_matched`, plus
  the corpus key set `== test_conformance_fragment.ALL_CORPORA.keys()` (or the same `_FAMILIES`),
  so a new corpus family that is not swept goes red. Keep the `>= 43` non-empty floor.
  ⚠ The merged-leaf predicate must group by `(objectType, outRel)`, not by `outRel`. This
  probe's first version keyed on `outRel` alone and falsely flagged
  `fga:owc_star_ttu.fga`, where `folder` and `doc` each own a `restricted.0`. The scout's census
  "0 merged in corpus" stands.
- X5. **Lean instrument control: strip the index, not `leaf=[]`.** An emitter that prints
  `outRel` with its `.i` removed is the S9 twin on the Lean channel. Like `leaf=[]`, it costs a
  `Cli`-only rebuild, and it shows the comparator reading the leaf names, not just the list
  lengths (REASONED).
- X6. **Expected refusals: prefer zero.** Build the sweep from `ALL_CORPORA` (35; it already
  excludes `REFUSED_TUPLESET`) + fixtures + witnesses + `tk126` SERVED. Then no refusal is
  expected, and any refusal is a failure with no allow-list to maintain. If an allow-list is
  kept, pin the exception CLASS and a message substring, not just the label. In the wider probe
  set, Lean emits non-empty rules for all 16 Python-refused inputs (`tk126.CYCLIC` x2, 13
  `SCHEMA_PROBES`, `derived_tupleset_ttu`). So they must never enter the sweep silently.
- X7. **Do not import witness constants from `tests/test_tk126_ttu_target_name_collision.py`.
  Move them.** Its imports (:106-127, READ) pull in `sqlmodel`, `zanzibar.connectedstore`
  (renamed by `TK123` this session), `tests.parity` and `tests.test_lookup_oracle`. An import
  break anywhere in that chain would stop the new conformance module from COLLECTING. Put
  `D` / `D_nested` / `SlXt` (and the 6 witnesses) in a `corpus.py` dict kept out of `_FAMILIES`,
  and have `test_tk126` import from there. sec 5 offers this as optional; make it the plan.
- X8. **Missing surface: task row `P21`** (LATER, "a fourth zcli mode so a fragment predicate
  can be DIFFERENTIALLY checked, not mirrored"). It owns the
  `test_leaf_namespace_correspondence.py` follow-up in sec 10. TK119's `leaf-rules` mode is the
  channel that row wants for `NoLeafSubjects` over `schemaRewritesL`. Coordinator: name `P21` in
  the TK119 close comment and comment on `P21`. Leave that module's "exactly three modes" wording
  to `P21`: its Traps forbid calling the mirror machine-checked before it is.
- X9. **Second stale rc comment:** `runner.py::invoke_zcli` docstring (:96, 2026-10-14) "0-4
  are zcli's own outcomes", besides :37-38. Fix both. If cross-referencing the gap,
  `CORRESPONDENCE.md` :371 (the `isPure` row) also cites the `TK126` gap and can point at
  the new pin.
- X10. **Make the multiset choice load-bearing:** no source in either set has a duplicate rule
  (PROBE, 0). Both sides keep duplicates: Python by PROBE (`dup.py`: `a or a` → two
  `a→viewer` rules; `(a or a) but not c` → `a→viewer.0` twice), Lean by READ
  (`RulesWrite.lean::exprArms` uses `++`). Add a `(a or a) but not c` witness so `Counter` vs
  `set` makes a difference on at least one input. Its Lean side was NOT run here (UNVERIFIED).
- X11. **Tile cost is about 2x the sec 8.2 estimate.** The floor test needs every source's
  result. Tiles are separate processes, so the floor test re-spawns all ~66 in whichever tile
  it lands in, on top of the parametrized spread. That is about 14 s extra at 0.21 s per spawn,
  more under load (REASONED). conf-tile:1/5 has about 165 s of headroom, so it is acceptable.
  Alternatively, fold the floors into a single sweep test and drop the per-source
  parametrization.
- X12. **Alternatives considered (REASONED):** a `leafRules` key added to `fragment` mode
  would avoid the new mode/rc text. But `Cli.lean::fragmentJson` is content-pinned in
  `formal/correspondence_anchor_pin.txt` and its key set is asserted by `runner.run_fragment`,
  so it would couple two unrelated tests. Rejected. The user-approved separate mode stands.
- X13. **Sequencing with `TK132` (REASONED, from `.scratch/now-next/scout-TK132.md`).** TK132's
  scout reports its type-aware `isPure` copy reproduces Python's allocation on `SlXt`. So when
  TK132 lands, all 4 pins flip, and TK132's builder must delete `_TK132_EXPECTED` entries in the
  same commit. Also assert that the set of mismatching sources EQUALS `_TK132_EXPECTED`'s
  keys, so a fifth mismatch cannot hide. If both rows run this session, land TK119 first, and
  never run two `lake build`s at once.

## 0. Headline (read this if nothing else)

1. **PROBE: the decided plan works, and a prototype of the Lean emitter already ran.** A
   scratch Lean file importing `ZanzibarProofs.Cli` (elaborated with `lake env lean` against
   the existing build, no `formal/` edit) printed `schemaRewrites S` / `leafRewrites S` as
   JSON for every source, through the real `Cli.decodeRequest`. The emitter is ~20 lines
   (sec 9.1).
2. **PROBE: on the corpus alone, the test would be GREEN on day one, and it would prove less
   than the 2026-08-16 number suggests.** Over the 50 compiled corpus + `tests/fga_schemas`
   sources, Lean and Python agree as multisets on all 50, and 32 of those have a non-empty
   leaf half. That is the 2026-08-16 figure, reproduced. BUT on **both sides, no corpus
   source has a leaf TTU rule, and none has a merged closure leaf** (two or more rules on one
   leaf). The old "50/50" only ever compared single-`computed`-arm closure leaves. The test
   needs constructed witnesses for those shapes (sec 5).
3. **PROBE: the `TK132` gap is real and reachable, but not from the corpus.** No corpus or
   fixture schema has the `TK132` shape. Four witnesses do, and each one mismatches exactly
   as predicted: `tests/test_tk126_ttu_target_name_collision.py::D`, `::D_NESTED`, `::SLXT`,
   and a constructed `W3` (sec 4). These become POSITIVE pins (never an xfail), handed to
   `TK132`.
4. **PROBE: rule ORDER differs on 9 sources.** Python walks the derived keys in
   `sorted(tainted)` order, while the model walks declaration order. So the test must compare
   multisets, and `GraphIndex/LeafRules.lean::schemaRewritesL`'s docstring sentence "Order
   mirrors `compile_ruleset`" is only half true (sec 3.3).
5. **PROBE: the row's planned sabotage (the S9 shape: the leaf index dropped, so the rule
   targets the public name) never reaches the differential.** Python's own I5 check in
   `src/zanzibar/schema/boolean.py::compile_boolean_schema` refuses 42 sources with
   `ValueError: Rule rewrites into a derived-public family`. **A test that skips a Python
   compile refusal would stay GREEN under that sabotage** (the probe's skip-on-refusal
   comparator reported `compared 17, match 17, mismatch 0`). The test must FAIL on any
   refusal it did not expect. The sabotage that does reach the diff is an off-by-one leaf
   index: 36 mismatches plus 6 refusals (sec 7).

## 1. What the claim is, and where it lives (three places, not two)

READ, all three carry the same 2026-08-16 numbers:

| where | line (2026-10-14) | text |
|---|---|---|
| `formal/CORRESPONDENCE.md`, the `keyLeafRewrites` / `leafRewrites` / `schemaRewritesL` row | :374 | "Reported 2026-08-16 from a one-off probe that was never made a test … **50/50 schemas**, 0 mismatches, **32 with a non-empty leaf rule set**" |
| `formal/lean/ZanzibarProofs/Audit.lean` comment above `#print axioms keyLeafRewrites` | :1986-1988 | "Measured before written … 50/50 schemas, 0 mismatches, 32 with a NON-EMPTY leaf rule set" |
| `formal/lean/ZanzibarProofs/GraphIndex/LeafRules.lean` module docstring, "Measured before it was written" | :87-94 | "**50 / 50 schemas match, 0 mismatches**, of which **32 have a non-empty leaf rule set**" |

The row's plan names only the first two. The third is in a module whose edit rebuilds 25 of
the 72 `ZanzibarProofs` modules (PROBE, sec 8.4), so its timing matters.

The sources the 2026-08-16 probe read (READ, the `LeafRules.lean` docstring): "every corpus
dict in `formal/conformance/corpus.py` and every `tests/fga_schemas/*.fga` fixture".

**A sibling unbacked claim, same disease (READ):** `GraphIndex/Leaf.lean` module docstring
:320-325 and `Audit.lean` :1909 say the leaf-FAMILY allocation (index → kind → storage)
"agrees on 82 / 82 derived keys" (2026-08-16). `CORRESPONDENCE.md` :370 already marks the
original 82/82 as RETRACTED and says the re-run over the binarized AST was 0-disagreement,
but no test re-runs that either. It is out of `TK119`'s scope. Sec 10 suggests a cheap
extension of the same mode.

## 2. The Lean side — what exists

### 2.1 The rule type and the function under test (READ)

- `formal/lean/ZanzibarProofs/GraphIndex/RulesWrite.lean::RuleKind` (:42) is
  `computed | ttu (tr : String)`.
- `::RRule` (:49) is `{ objectType matchRel outRel : String, kind : RuleKind }`, deriving
  `DecidableEq, Repr, Inhabited`.
- `::exprArms` (:61) turns `computed` and `ttu` into rules, walks `union`, and returns `[]`
  on `direct`, `inter` and `excl`.
- `::schemaRewrites` (:82) is the untainted half: `S.defs` filtered by `!isDerived`.
- `formal/lean/ZanzibarProofs/GraphIndex/LeafRules.lean::keyLeafRewrites` (:114) maps
  `persistedLeaves` over `zipIdx`, so each `.closure sub` emits `exprArms ty (leafPred R i) sub`.
- `::leafRewrites` (:122) is `S.defs` filtered by `isDerived`, then `keyLeafRewrites`.
- `::schemaRewritesL` (:130) is `schemaRewrites S ++ leafRewrites S`.
- `formal/lean/ZanzibarProofs/GraphIndex/Leaf.lean::leafPred` (:195) is
  `R ++ "." ++ toString i`.
- `Leaf.lean::isPure` (:391): its `.ttu tgt ts` case is
  `!isDerived S (ty, ts) && !derivedAnywhere S tgt`. That is the `TK132` gap (sec 4).
- None of these is `noncomputable` (READ, grep). The prototype compiled and ran them (PROBE).

### 2.2 `Cli.lean` — dispatch, helpers, rc codes (READ, `formal/lean/ZanzibarProofs/Cli.lean`, 449 lines)

- **Imports** (:1-5): `Spec.Semantics`, `GraphIndex.Exec`, `GraphIndex.FragmentDecide`,
  `GraphIndex.AdmissionDecide`, `Lean.Data.Json`. **`GraphIndex.LeafRules` is ALREADY in
  `Cli`'s transitive import cone** (PROBE `import_cone.py`, 65-module cone):
  `LeafRules <- CascadeStable <- CascadeSettle <- CascadeInv <- CascadeStrataInv <-
  RemoveOccCount <- Exec <- Cli`. An explicit `import ZanzibarProofs.GraphIndex.LeafRules`
  is optional, self-documenting, and adds no edge to the build graph. **Nothing imports
  `Cli`** (PROBE `reverse_cone.py`: Cli's rebuild cone is 1 of 72).
- **The request decoder** `::decodeRequest` (:176) requires `"schema"`, `"tuples"` and
  `"queries"`. `formal/conformance/encode.py::build_request` always emits all three, so a
  leaf-rules request is `build_request(text, [], [], ow, mode="leaf-rules")` (PROBE: that
  exact call made all 66 requests, and all decoded).
- **Mode string** `::decodeMode` (:211). **Dispatch** is in `::main` (:343-444): arms
  `"graph"` (:355), `"graph-state"` (:393), `"fragment"` (:417), `"spec"` (:430), and the
  unknown-mode arm (:440), whose message enumerates the modes and returns rc 4.
- **JSON helpers**: `::canonJsonArr` (:252) sorts and **DEDUPLICATES**. Do NOT use it for
  rules: it would hide a duplicated rule. Emit the raw `List` (sec 3.2). `Json.mkObj` /
  `Json.arr` / `Json.str` are what `::fragmentJson` (:330) uses.
- **The header docstring** (:7-106) lists the modes (:16, :31-94), the unknown-mode rule
  (:96-99) and the rc table (:101-103: rc 5 is "`"ops"` in spec mode or fragment mode").
  All three must gain `"leaf-rules"`.
- **`fragment` is the template**: no driver run, queries ignored, an `"ops"` stream refused
  with rc 5 (:422-426), print `(fragmentJson S T).compress` (:428).

### 2.3 Build cost (PROBE)

- `zcli.exe` (`formal/lean/.lake/build/bin/`, 119,942,144 bytes) was built 2026-09-26 and is
  up to date: `lake build zcli --no-build` → rc 0, `All targets up-to-date (2156 jobs)`,
  **94 s** wall time, which is the no-op cost of the check alone.
- A scratch file importing `ZanzibarProofs.Cli` elaborates and `#eval`s the sweep in **32-36 s**
  (`lake env lean`). A `Cli.lean`-only edit rebuilds `Cli` (cone 1) and relinks the binary.
  The relink time was NOT measured (it would have needed a `formal/` edit). UNVERIFIED, but
  the `lean` phase has run 99-170 s on recent no-rebuild runs and 293-456 s with rebuilds
  (READ `.gate-runs/ledger.tsv`, 2026-10-13/14).
- One zcli spawn costs **0.210 s** (PROBE `time_zcli.py`: 20 fragment-mode spawns in 4.20 s).
  So ~66 sources is ~14 s of spawning, spread over the conformance tiles.

## 3. The Python side — what the Lean rules are compared with

### 3.1 Where Rules come from (READ)

- `src/zanzibar/schema/rules.py::Rule` (:174) is `(if_pattern, then_pattern)`. `::Filter`
  (:149) and `::RewriteFilter` (:157, a `Filter` subclass) are NOT `Rule`s. Directs compile
  to filters, so they never enter the comparison, matching `exprArms`' `.direct _ => []`.
- Rules are built at exactly two call sites, both through `rules.py::_rewrite_rule` (:479):
  `src/zanzibar/schema/compiler.py::_emit_expr` (:139, the untainted half) and
  `src/zanzibar/schema/boolean.py::_emit_leaf_expr` (:429, the leaf half).
- `_rewrite_rule`: for `Computed` it builds
  `if(relation=r, object_type=ot) -> then(relation=target, object_type=ot)`. For
  `TTU(target_rel, tupleset_rel)` it builds `if(relation=tupleset_rel, object_type=ot) ->
  then(subject_predicate=target_rel, relation=target, object_type=ot)`. Both have
  `match_wildcards=True`.
- Pipeline: `compiler.py::parse_openfga_schema(text, object_wildcard_shapes)` (:603) runs
  `parse_schema_ast`, then `derive_schema_info`, then `compile_ruleset` (:257). The
  untainted loop is at :292-294. `boolean.py::compile_boolean_schema` then appends the leaf
  rules, iterating `for key in sorted(tainted)` (READ, ~:779).

### 3.2 The normaliser (REASONED; PROBE-confirmed over 66 sources)

```
Rule r  ->  (r.if_pattern.object_type, r.if_pattern.relation, r.then_pattern.relation,
             "computed")                         if then_pattern.subject_predicate is None
            (..., "ttu", then_pattern.subject_predicate)   otherwise
untainted half = rules whose outRel has no '.';  leaf half = rules whose outRel has a '.'
```

The `.`-split is sound because declared relation names may not contain `.` (P23, both
parsers), and `LeafRules.lean::schemaRewrites_leafRewrites_disjoint` proves the same split
on the Lean side. **The normaliser must fail LOUDLY on any field it drops**, following the
`compiler.py::_node_removal_fence` precedent: assert that `then.object_type ==
if.object_type`, that `subject_type` / `subject_name` / `object_name` are `None` on both
patterns, that `match_wildcards` is `True`, that `if.subject_predicate` is `None`, and that
`then.subject_predicate` is never `Ellipsis`. Otherwise a future rule shape could be
flattened into a match. Compare **multisets** (`collections.Counter`), never sets: a
duplicated arm is a real difference.

### 3.3 Order is NOT comparable across keys (PROBE `compare.py`)

On 9 sources Lean and Python agree as multisets while the rule ORDER differs, always
because the derived keys come in a different order. Literal example:

```
SCHEMAS:two_stratum_cascade: match as multiset, ORDER differs (leaf py=[('doc', 'muted', 'approver.0', 'computed'), ('doc', 'editor', 'viewer.0', 'computed'), ('doc', 'banned', 'viewer.1', 'computed')] lean=[('doc', 'editor', 'viewer.0', 'computed'), ('doc', 'banned', 'viewer.1', 'computed'), ('doc', 'muted', 'approver.0', 'computed')])
```

The 9 are `SCHEMAS:` `two_stratum_cascade`, `taint_union_over_boolean`,
`cross_stratum_resettle`, `star_two_strata_churn`, `taint_union_userset_arm`,
`nary_union_derived4` and `residue_rich`, plus `fga:boolean_wildcards.fga` and
`fga:owc_star_ttu.fga`. The cause is READ: `compile_boolean_schema` iterates
`sorted(tainted)`, while `leafRewrites` iterates `S.defs`. The `LeafRules.lean::schemaRewritesL`
docstring (:126-129) says "Order mirrors `compile_ruleset` … keeping it faithful costs
nothing". The first half is wrong across keys. The docstring itself notes that order is not
observable through `rewriteStep`, so this is a doc fix, not a model bug. Within one key,
order looked equal on every source printed (REASONED from the printed lists, not asserted
separately).

## 4. The `TK132` interaction (PROBE; Lean side partly READ)

**The shape.** A TTU arm inside a DERIVED def whose target NAME is derived on some type, but
not on any type the tupleset admits. Python's `boolean.py::_is_pure` (TTU case, keyed on
`_member_types`) calls the arm pure, so it becomes a closure leaf and emits a rule. Lean's
`isPure` uses `derivedAnywhere`, calls it impure, and drops the arm, so the later leaves
shift down one index.

**Census (PROBE `py_rules_census.py`, `tk126_shapes.py`):**
- `formal/conformance/corpus.py` (all 5 dicts) + `tests/fga_schemas/*.fga`: **0** sources
  with the shape.
- `tests/test_tk126_ttu_target_name_collision.py::SERVED`: **3** of 8: `D`, `D_nested`,
  `SlXt`.
- Constructed `W3_merged_computed_ttu` (sec 5): the merged-leaf flavour, 1 more.

**The literal mismatches (PROBE `compare.py` / `compare2.py`; Lean output from the prototype
emitter):**

```
tk126:D: MISMATCH
   leaf: python-only=[('doc', 'banned', 'viewer.2', 'computed'), ('doc', 'parent', 'viewer.1', 'ttu', 'viewer')] lean-only=[('doc', 'banned', 'viewer.1', 'computed')]
tk126:D_nested: MISMATCH
   leaf: python-only=[('doc', 'banned', 'viewer.2', 'computed'), ('doc', 'parent', 'viewer.1', 'ttu', 'viewer')] lean-only=[('doc', 'banned', 'viewer.1', 'computed')]
tk126:SlXt: MISMATCH
   leaf: python-only=[('doc', 'banned', 'access.1', 'computed'), ('doc', 'parent', 'access.0', 'ttu', 'viewer')] lean-only=[('doc', 'banned', 'access.0', 'computed')]
W3_merged_computed_ttu MISMATCH python=[('doc', 'a', 'viewer.0', 'computed'), ('doc', 'parent', 'viewer.0', 'ttu', 'viewer'), ('doc', 'c', 'viewer.1', 'computed')] lean=[('doc', 'a', 'viewer.0', 'computed'), ('doc', 'c', 'viewer.1', 'computed')]
```

The SlXt Lean side is also a machine-checked theorem: READ
`LeafRules.lean::LeafRuleWitness.lrXt_cross_type_drop` (:2649), `leafRewrites SlXt = [team z
viewer.0, team y viewer.1, doc banned access.0]` `by decide`. The prototype printed exactly
that list, which cross-checks the emitter. The Python side is pinned by
`tests/test_tk126_ttu_target_name_collision.py::test_slxt_python_allocation_is_the_recorded_gap`.

**What the pin should look like (REASONED):** `_TK132_EXPECTED: dict[label, (python_only,
lean_only)]` holding the four diffs above. The test asserts the observed diff EQUALS the
recorded one, not merely that a diff exists. So a change on either side shows up. When
`TK132` lands, these four flip to agreement, the pin goes red, and `TK132`'s builder deletes
the entries. That gives `TK132` a ready-made differential acceptance check.

## 5. Witnesses the corpus lacks (PROBE `witnesses.py`, `compare2.py`)

PROBE `coverage.py` + `py_coverage.py`: across all 50 compiled corpus/fixture sources, the
number of leaf TTU rules is **0** and the number of merged closure leaves is **0**, on both
sides. The only leaf TTU rules anywhere are the Python-only ones in the `TK132` witnesses.
So without constructed witnesses, the test would never see a leaf TTU rule AGREE.

Constructed witnesses (DSL quoted in full in sec 9.3). All compile under
`parse_openfga_schema`, and all encode through `encode.py`:

| witness | shape | Lean leaf half (PROBE) | verdict |
|---|---|---|---|
| `W1_leaf_ttu` | `access: viewer from parent but not banned`, `viewer` derived nowhere | `[doc parent access.0 ttu viewer], [doc banned access.1]` | MATCH |
| `W2_merged_computed` | `viewer: (a or b) but not c` | `a→viewer.0, b→viewer.0, c→viewer.1` | MATCH |
| `W3_merged_computed_ttu` | `viewer: (a or viewer from parent) but not c` | TTU arm dropped | **MISMATCH (TK132 shape)** |
| `W3b_merged_computed_ttu_clean` | `viewer: (a or editor from parent) but not c` | `a→viewer.0, parent→viewer.0 ttu editor, c→viewer.1` | MATCH |
| `W4_direct_plus_computed` | `viewer: ([user] or a) but not c` (storage leaf 0, so `a`→`.1`) | `a→viewer.1, c→viewer.2` | MATCH |
| `W5_ttu_in_subtract` | `viewer: a but not blocked from parent` | `a→viewer.0, parent→viewer.1 ttu blocked` | MATCH |
| `W6_nary_merged3` | `viewer: (a or b or d) but not c` (n-ary merge through the left fold) | `a,b,d→viewer.0, c→viewer.1` | MATCH |

**Where they live (REASONED, the builder decides):** either a new
`corpus.py::LEAF_RULE_WITNESSES` dict kept OUT of `test_conformance_fragment.py::_FAMILIES`
and every answer-comparing family (like `REFUSED_TUPLESET_SCHEMAS`, so no other module
enrolls them), or module-local to the new test. Import the three `TK132` witnesses from
`tests.test_tk126_ttu_target_name_collision` (`SLXT`, `D`, `D_NESTED`) instead of copying
them: one text, already oracle-checked there. No `formal/conformance` module imports a
`tests.test_*` module today (READ grep; `tests.oracle` / `tests.parity` imports do exist).
So this is new; an alternative is to move the three strings into `corpus.py` and have
`test_tk126` import them from there. Import constants only, never a `test_*` function, or
pytest will collect it twice.

## 6. The plan, as numbered steps

1. **Lean: `Cli.lean`.** Add `rruleJson` and `leafRulesJson` (prototype in sec 9.1: a rule
   is `[ot, matchRel, outRel, "computed"]` or `[ot, matchRel, outRel, "ttu", tr]`, and the
   object is `{"untainted": [...schemaRewrites S], "leaf": [...leafRewrites S]}`, RAW
   lists). Add a dispatch arm `| .ok "leaf-rules" =>` cloned from `"fragment"`: refuse
   `"ops"` with rc 5, otherwise print `.compress` with rc 0. Update the header's mode list,
   the unknown-mode paragraph (:96-99), the rc table (:101-103, rc 5 now covers leaf-rules
   too) and the unknown-mode stderr message (:441-442). Emitting the two halves separately
   (rather than the concatenated `schemaRewritesL`) lets Python check the split too. The
   untainted half then also re-checks the taint filter, the class of the 2026-07-17
   divergence recorded in `RulesWrite.lean::schemaRewrites`' docstring. Optionally add an
   explicit `import ZanzibarProofs.GraphIndex.LeafRules`.
2. **Build:** `export PATH="$HOME/.elan/bin:$PATH"; cd formal/lean; lake build zcli`. The
   cone is `Cli` only (sec 2.3). Do it in the background or as its own command, because of
   the ~10-min harness cap.
3. **Python: `formal/conformance/runner.py`.** Add `LEAF_RULES_KEYS = frozenset({"untainted",
   "leaf"})`, a `_LEAF_RULES_CACHE`, and `run_leaf_rules(request_json) -> dict`, cloned from
   `::run_fragment` (:221). Assert the exact key set, each rule's shape (length 4 +
   `"computed"`, or length 5 + `"ttu"`), every `leaf` outRel containing `.`, and no
   `untainted` outRel containing one. Keep the request file on failure. Also fix the stale
   comment at :37-38 ("zcli's OWN exit codes are exactly 0-4"; rc 5 already exists).
4. **Python: `formal/conformance/test_conformance_leaf_rules.py`** (new; differential, so
   no `doc_counts.py::TOOLING_FILES` edit). Contents in sec 6.1.
5. **Witnesses** per sec 5.
6. **Sabotage** per sec 7. Record the literal outputs in the module docstring and the
   commit message.
7. **Docs.** Rewrite the `CORRESPONDENCE.md` :374 row's code-side cell to CITE
   `formal/conformance/test_conformance_leaf_rules.py` (draft in sec 6.2). Add a row for the
   new module to the conformance-module table beside `test_cli_mode.py` (:91). Add the new
   mode and rc to the zcli exit-code paragraph (:95-100). Amend the §7.1 `TK126` entry
   (~:1016) to name the `TK132` positive pin. Rewrite the `Audit.lean` :1986-1988 comment
   (cone 1, cheap). For `LeafRules.lean` :87-94 (the 50/50 paragraph) and :126-129 (the
   order claim), see sec 8.4 on timing.
8. **Gate hygiene** (sec 8): `python formal/conformance/claim_rot.py --generate` if a new
   anchor such as `Cli.lean::leafRulesJson` is cited, then
   `python -m formal.conformance.doc_counts --generate` (this ratchets `MIN_CONF_ALL` and
   the other floors), then every gate phase.
9. **Row write-back** (coordinator): `task.py comment TK119` naming this doc, then close.

### 6.1 The tests (REASONED design; numbers PROBE-measured 2026-10-14)

- **`test_leaf_rules_match_python[<source>]`**, parametrized over every compiled source
  (35 curated corpus schemas + 15 `.fga` fixtures = the 50 the probe compiled, plus the 6
  agreeing witnesses, plus the 5 agreeing `tk126` schemas `B`, `C`, `B_star`, `C_cross`,
  `C_team`). It asserts `Counter(lean_untainted) == Counter(py_untainted)` and the same for
  `leaf`. **A Python compile refusal is a FAILURE**, never a skip, unless the source is in
  the explicit expected-refusal set (sec 7 says why this is load-bearing). On failure, print
  python-only and lean-only per half.
- **`test_refused_source_still_reports`** (optional): `REFUSED_TUPLESET:derived_tupleset_ttu`
  compiles in Lean (prototype leaf half has 1 rule) and Python refuses it. Pin both facts,
  or simply keep it out of the sweep. It is a parse refusal, so there is nothing to compare.
- **`test_tk132_gap_is_exactly_the_recorded_diff[<witness>]`**: the 4 positive pins of sec 4.
- **`test_leaf_rules_sweep_is_not_vacuous`**: floors, each `>=`, recorded with provenance.
  The non-empty-leaf matched count: live 43 by REASONED arithmetic (32 corpus/fixture + 6
  witnesses + 5 `tk126`); the builder re-measures it. At least one matched source with a
  leaf TTU rule (live 3: W1, W3b, W5). At least one matched source with a merged closure
  leaf (live 3: W2, W3b, W6). Compiled-source count ≥ 50. The two shape floors are the real
  news: without them a deleted witness turns the sweep back into the old single-arm check
  and nothing notices.
- **`test_normaliser_control`**: one hand-built `Rule` of each kind through the normaliser,
  with the exact tuple asserted, plus one malformed pattern (e.g. `subject_type` set) that
  must raise. This is the instrument control.
- Skip only when `runner.zcli_path()` raises `ZcliUnavailable` (the
  `test_conformance_fragment.py::_fragment_report` pattern). `verify.sh`'s conformance
  preflight (:1261-1276) makes zcli present in the gate, and the conf phases require zero
  `skipped`.
- **Do not import `formal/conformance/backends.py`** (it imports `zanzibar.connectedstore`,
  which `TK123` renames). `parse_openfga_schema` + `Rule` is all the test needs.

### 6.2 Draft of the rewritten `CORRESPONDENCE.md` :374 code-side cell (REASONED)

> `src/zanzibar/schema/boolean.py::_emit_leaf_expr` (Computed/TTU → `::_rewrite_rule(expr,
> object_type, leaf)`; `Direct` → `RewriteFilter`, i.e. the storage routing modelled by
> `rawWriteRels`). **Differential-checked against the Lean definition itself** by
> `formal/conformance/test_conformance_leaf_rules.py`: `zcli mode="leaf-rules"`
> (`Cli.lean::leafRulesJson`) prints `schemaRewrites S` and `leafRewrites S`, and each must
> equal, as a multiset, the `Rule`s `src/zanzibar/schema/compiler.py::compile_ruleset`
> emits, on every compiled corpus schema, fixture and constructed witness, with
> non-vacuity floors on non-empty leaf halves, leaf TTU rules and merged closure leaves.
> Rule order across derived keys is not compared (Python walks `sorted(tainted)`, the model
> walks declaration order). The exception is the `TK132` shape, where the model drops the
> TTU arm; each witness of it is positively pinned there (§7.1 `TK126` entry).

It carries no `N/M` ratio, so `claim_rot.py`'s prose-number lint has nothing to flag. If a
ratio is wanted, it must sit in the same sentence as the cite, or (better) be added to
`doc_counts.py::measure()` and cited as the FINAL_REVIEW.md generated counts block.

## 7. Sabotage (PROBE dry-runs via monkeypatch; `src/` untouched)

`sabotage.py` patches `zanzibar.schema.boolean._emit_leaf_expr` in-process and reruns the
comparison over the prototype's Lean output (58 sources; skip-on-refusal comparator, the
WRONG design, on purpose):

```
none     SUMMARY {'compared': 58, 'match': 55, 'nonempty_leaf_lean': 40, 'order_mismatch_only': 9, 'py_refused': 1, 'mismatch': 3}
public   SUMMARY {'compared': 17, 'match': 17, 'nonempty_leaf_lean': 0, 'order_mismatch_only': 0, 'py_refused': 42}
offbyone SUMMARY {'compared': 53, 'match': 17, 'nonempty_leaf_lean': 36, 'order_mismatch_only': 0, 'mismatch': 36, 'py_refused': 6}
```

- **S-public (the row's "S9 shape": leaf target := public relation).** Python refuses 42
  sources at compile time, e.g.
  `boolean_exclusion ValueError Rule rewrites into a derived-public family: Rule(if_pattern=RelationalTriplePattern(... relation='editor', object_type='doc', ...`.
  Under skip-on-refusal the comparator reports **0 mismatches: GREEN**. That is the house
  failure mode, observed. With refusal-as-failure (sec 6.1) the same sabotage is 42 red
  params, and the non-empty floor (0 < 43) also goes red. **Record both in the docstring:**
  the S9 shape is caught first by Python's own I5 assertion, so it cannot be the test's
  only sabotage.
- **S-offbyone (leaf `R.i` → `R.(i+1)` inside `_emit_leaf_expr`): the sabotage that actually
  reaches the diff.** 36 mismatching sources, plus 6 refusals:
  `SELF_REFERENTIAL_SCHEMAS:self_ttu_parent`, `REFUSED_TUPLESET_SCHEMAS:derived_tupleset_ttu`
  (refused anyway), `fga:heterogeneous_tupleset.fga`, `fga:userset_over_derived.fga`,
  `fga:wildcard_userset_cross.fga`, `tk126:C_cross`. (Why these 6 refuse is UNVERIFIED;
  plausibly the shifted index collides with a storage/userset leaf.) **Use this one as the
  docstring's primary sabotage.** Per the row, do it as a temporary edit of
  `_emit_leaf_expr` or a `monkeypatch` inside a throwaway test, never committed.
- **Lean-side instrument control (REASONED, costs one `Cli`-only rebuild):** make the
  `"leaf"` field emit `[]`. Every source with a non-empty Python leaf half goes red, and so
  does the floor. Worth one run, so the record shows the Lean channel is live and not only
  the Python one.
- **Normaliser control:** drop the `tr` of a TTU (map every rule to `"computed"`). The 16
  sources with untainted TTU rules (PROBE `coverage.py`) and W1/W3b/W5 go red, and so does
  `test_normaliser_control`. REASONED.

## 8. Gate impact (READ unless marked)

1. **Floors only go up.** `formal/verify.sh` `MIN_CONF_ALL=1093` (:493),
   `MIN_CONF_HEAVY=135` / `MIN_CONF_REST=958` (:785-786), `MIN_TESTS_ALL=2401` (:701).
   `doc_counts.py --generate` ratchets them upward to the live counts (`TK99`). Adding
   tests turns `lean` red (step 4e, the FINAL_REVIEW.md counts block) until `--generate`
   runs. The new module is "differential" by default (not in `TOOLING_FILES`, :69).
2. **Tiles:** structural partition by index mod K, so no list update is needed. Cost is
   about 66 spawns × 0.21 s ≈ 14 s total. `conf-tile:1/5` ran 435 s on 2026-10-14 08:21,
   the tightest tile against the 600 s cap.
3. **Statement/definition pins:** `formal/headline_definitions.txt` pins the bodies of
   `keyLeafRewrites` (:252), `leafRewrites` (:255), `schemaRewritesL` (:281) and
   `leafPred` (:254). `TK119` edits none of them, so nothing moves. `statement_pin.py::strip_comments`
   strips comments, so docstring edits move no pin (READ in the `TK126` doc's correction;
   not re-read here). No `Cli.lean` def is in the headline pin.
4. **The `LeafRules.lean` docstring edit is EXPENSIVE, not free.** PROBE `reverse_cone.py`:
   editing `LeafRules.lean` rebuilds 25 of the 72 `ZanzibarProofs` modules, and editing
   `Leaf.lean` rebuilds 27. `TK132` edits `Leaf.lean` + `LeafRules.lean` anyway.
   **Recommendation (REASONED):** if `TK132` runs this session, fold the two
   `LeafRules.lean` docstring fixes (sec 1 row 3, sec 3.3) into `TK132`'s rebuild. If it
   does not, `TK119` pays the 25-module rebuild once, in the background, before the `lean`
   phase. `Audit.lean` and `Cli.lean` edits each have a cone of 1.
5. **`CORRESPONDENCE.md` anchors / claim-rot:** `Cli.lean::canonJsonArr`, `::edgeCountsJson`
   and `::fragmentJson` are content-pinned in `formal/correspondence_anchor_pin.txt`
   (:18-20). Citing a new `Cli.lean::leafRulesJson` anchor needs `claim_rot.py --generate`
   (read the rows first; that is the point of the pin). `anchor_check.py` resolves every
   `file::symbol` anchor, so cite only symbols that exist.
   `claim_rot.py::CITE_RE` (:341) accepts a backticked path matching `test_*.py`.
6. **Audited theorems:** no new theorem is needed, so `audited_theorems.txt` is unchanged.
7. **Snapshots:** `tests/snapshots/` is untouched (no compiler change).
8. **`test_cli_mode.py`:** existing tests stay green. The unknown-mode test asserts only
   that `"graf"` appears in stderr. Optional: add `test_ops_in_leaf_rules_mode_rejected`
   (rc 5), cloned from `::test_ops_in_spec_mode_rejected`.

## 9. Probe bodies (quoted because `.scratch/` is gitignored)

### 9.1 The prototype emitter (`lean/LeafRulesEmit.lean`; ran under `lake env lean`)

```lean
import ZanzibarProofs.Cli
import ZanzibarProofs.GraphIndex.LeafRules
open Lean Zanzibar
namespace ScoutTK119
def rruleJson (r : RRule) : Json :=
  match r.kind with
  | .computed => Json.arr #[Json.str r.objectType, Json.str r.matchRel, Json.str r.outRel,
                            Json.str "computed"]
  | .ttu tr   => Json.arr #[Json.str r.objectType, Json.str r.matchRel, Json.str r.outRel,
                            Json.str "ttu", Json.str tr]
/-- RAW lists (Lean order, multiplicity kept): `canonJsonArr` would dedup. -/
def leafRulesJson (S : Schema) : Json :=
  Json.mkObj [
    ("untainted", Json.arr ((schemaRewrites S).map rruleJson).toArray),
    ("leaf", Json.arr ((leafRewrites S).map rruleJson).toArray)]
#eval IO.println (leafRulesJson LeafRuleWitness.SlXt).compress
-- sweep: for each manifest line, Json.parse the request file, Cli.decodeRequest, print
end ScoutTK119
```

Literal output on `SlXt`, which equals `lrXt_cross_type_drop`:
`{"leaf":[["team","z","viewer.0","computed"],["team","y","viewer.1","computed"],["doc","banned","access.0","computed"]],"untainted":[]}`.
Note `Json.mkObj` prints keys sorted (`leaf` before `untainted`). The Python side must parse
JSON, never compare strings.

Gotcha hit while probing: Python `Path.write_text` on Windows writes CRLF. A manifest read
with Lean `splitOn "\n"` then carried a `\r` into the path (`no such file or directory`).
This is irrelevant to the real test, because `runner.invoke_zcli` writes one request file
per call.

### 9.2 Census / comparison (`py_rules_census.py`, `compare.py`)

The Python normaliser is sec 3.2. The census summary line:

```
SUMMARY {'compiled': 50, 'rules': 168, 'leafrules': 89, 'nonempty_leaf': 32, 'tk132': 0, 'with_any_rule': 45, 'sources': 51, 'refused': 1}
```

The 51 sources are 35 curated schemas (`SCHEMAS` 27 + `MULTI_STRATUM_SCHEMAS` 1 +
`TTU_USERSET_SCHEMAS` 5 + `SELF_REFERENTIAL_SCHEMAS` 2), 1 `REFUSED_TUPLESET_SCHEMAS` entry, and
the 15 `tests/fga_schemas/*.fga` files (the directory also holds 2 `.json` files, which are
not swept). The one refusal is `REFUSED_TUPLESET_SCHEMAS:derived_tupleset_ttu` (`ValueError:
doc#inherited: 'viewer' from 'parent': a tupleset must be direct …`). Every source encodes
through `encode.py::schema_to_json` (0 encode errors). The `TK132`-shape predicate used:
for each tainted `(ot, rel)` and each TTU in its expression, the target is untainted on all
`_member_types(ot, tupleset_rel, ast, frozenset())` AND the target name is in
`{r for (_t, r) in tainted}`.

### 9.3 Witness DSL (`witnesses.py`; each prefixed `model\n  schema 1.1\n`)

```
W1_leaf_ttu:       type user / type folder: viewer: [user] / type doc: parent: [folder]; banned: [user];
                   access: viewer from parent but not banned
W2_merged_computed: type user / type doc: a,b,c: [user]; viewer: (a or b) but not c
W3_merged_computed_ttu: type user / type folder: viewer: [user] / type doc: parent: [folder]; a,c: [user];
                   viewer: (a or viewer from parent) but not c            <- TK132 shape
W3b_merged_computed_ttu_clean: as W3 but folder declares `editor: [user]` and the arm is `editor from parent`
W4_direct_plus_computed: type user / type doc: a,c: [user]; viewer: ([user] or a) but not c
W5_ttu_in_subtract: type user / type folder: blocked: [user] / type doc: parent: [folder]; a: [user];
                   viewer: a but not blocked from parent
W6_nary_merged3:   type user / type doc: a,b,d,c: [user]; viewer: (a or b or d) but not c
```

(Each `define` sits on its own line under `relations` in the real DSL. The compressed form
above is for reading.)

## 10. Risks, collisions, follow-ups

- **`TK132` (NEXT, Lean):** both rows touch `LeafRules.lean` and `CORRESPONDENCE.md` §7.1.
  Either order works. **`TK119` first** gives `TK132` a differential acceptance check: its 4
  positive pins flip, and the `TK132` builder deletes them. If `TK132` lands first, the 4
  witnesses simply become matching rows (keep them; they are the only sources with the
  shape). Batch the `LeafRules.lean` docstring edits with whichever row rebuilds that cone
  (sec 8.4). Do not run two `lake build`s at once in one tree.
- **`TK123` (renames `connectedstore` → `store` this session):** the new test needs no
  `connectedstore` import. `tests/test_tk126_ttu_target_name_collision.py` imports
  `zanzibar.connectedstore`. If the new test imports witness constants from it, `TK123`'s
  sweep updates that import, and only a mid-flight overlap would collide (a broken import
  while `TK123` is half-done). Moving the three strings into `corpus.py` removes the
  coupling entirely.
- **Stale docs this work touches:**
  `formal/conformance/test_leaf_namespace_correspondence.py`'s docstring says zcli "exposes
  exactly three modes" and that a "fourth zcli mode" would make it a true machine-check.
  There are four modes today, five after `TK119`. Follow-up (REASONED, not `TK119`'s
  scope): with `leaf-rules`, that module's `NoLeafSubjects` check could run over Lean's own
  rule list instead of a Python mirror. `runner.py` :37-38 says the rc codes are "exactly
  0-4"; 0-5 is the truth since rc 5 existed.
- **Sibling unbacked claim** (sec 1): `Leaf.lean`'s 82/82 leaf-family allocation. The same
  mode could emit `persistedLeaves` per derived key (index → kind → storage), diffed against
  `parse_openfga_schema(...).compiled.namespace` (the `LeafFamily` table
  `test_slxt_python_allocation_is_the_recorded_gap` already reads). Suggest filing a
  separate row rather than widening `TK119`.
- **Equivalence reading** (CLAUDE.md "Who decides"): the 4 mismatches are a
  model-describes-other-code gap, not a backend disagreement. The Python is oracle-checked
  on all of them by `test_tk126`, and the model is what is out of date (`TK132`). So the
  pin says "the model is wrong here, recorded", not "Python is wrong".
