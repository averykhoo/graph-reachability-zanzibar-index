# `TK137` — DSL shapes OpenFGA refuses: the measured plan

**ACTIVE-PLAN, opened 2026-10-14 — the body is provenance, not a living status.** This is
the execution map for `TK137` (`python scripts/task.py show TK137`), produced by one scout
(`scout-TK137`, a workflow subagent, opus) on 2026-10-14 against HEAD `0b09687`. Every figure
below is as-of that date. Live state is the task row and `python scripts/gate_status.py`,
never this file. Corrections append **dated at the top**, never edited into the body.
Freeze it when `TK137` closes.

**Provenance labels.** first-hand READ = the scout read the line itself. first-hand PROBE = a
script the scout ran against this tree; its literal output is quoted. REASONED = inferred,
not run. UNVERIFIED = not checked. The scout is a subagent, so to the coordinator **every
label here is agent evidence**: re-run the probes before anything here lands in a gate pin.
Line numbers are dated 2026-10-14 and rot within a session; the `file::symbol` is the
durable cite. Probes live in gitignored `.scratch/now-next/probes/scout-TK137/`; their
outputs are transcribed below because `.scratch/` is already lost.

## Corrections (newest first)

### Corrections 2026-10-14 (review fixes, `fix-TK137` builder, on top of `124069c`)

- **C10 landed as the scout-challenge "middle path"**, a message and no lenient mode. The
  four TK137 refusal sites (H1, H2, S7, S8) raise `src/zanzibar/schema/errors.py::ShapeRefusedSinceTK137`
  (a `ValueError` carrying `instead`). `src/zanzibar/connectedstore/schema_io.py::_persisted_schema_parse`
  turns it into `PersistedSchemaRefused` at every parse of PERSISTED text: `open_graph_index`,
  `open_set_engine`, `_same_schema` (stored text only), and `build.py::build_index`'s copy of
  the source schema. The message says the schema was saved by zanzibar-index 0.0.4 or
  earlier using a shape this version refuses, quotes the refusal, and gives the rewrite that
  keeps the 0.0.4 meaning. REASONED: a type, not message matching, because a message
  rewording would silently drop the label. Whether to break pre-1.0 stores at all stays the
  user's goal question; this only makes the break legible. Pinned by
  `tests/test_tk137_persisted_schema_refused.py` (sabotage in its docstring and the commit).
- **PYPI_README "Schema shapes" corrected**: it said "as in OpenFGA ... `1.2` is refused",
  which is false (OpenFGA accepts `1.2`). It now says only 1.1 is implemented, the header is
  optional, and refusing other versions is stricter than OpenFGA, matching the H1 WHY block
  in `parser.py::_validate_header_line`.
- The oracle's `condition` refusal got its own REFUSED SHAPE block, and
  `tests/test_tk137_openfga_dsl_refusals.py::test_unparse_declares_referenced_types` now
  checks the oracle's full AST, not its keys.

### Corrections 2026-10-14 (challenge)

By `challenge-TK137` (a workflow skeptic subagent, opus), against HEAD `0b09687`, same day.
Probes are in gitignored `.scratch/now-next/probes/challenge-TK137/`, and their outputs are
quoted here. Verdict: **the root cause and the refuse/keep split hold. The plan needs the
changes below before a builder starts.** C1-C3 are a test that would pass while broken, or
a miscount. C4-C9 are missing surface or sequencing. C10-C12 are judgement calls for the
coordinator.

**Confirmed first-hand (the scout's key claims hold):**
- first-hand PROBE: re-running `probe_shapes.py` gives output byte-identical to §2 once CRs
  are stripped. Both parsers agree on every case, S3b silently drops `viewer`, and S7b parses
  as `a but not (b or c)`.
- first-hand READ:
  - `src/zanzibar/schema/parser.py::_parse_schema_ast_unchecked` skips any line whose head is
    `model`, `schema` or `relations` (lines 202-203).
  - `src/zanzibar/schema/unparse.py::unparse_schema_ast`'s inner `_chain` parenthesises only
    an `Exclusion`.
  - `formal/conformance/test_conformance_generated.py::_case` prepends `'type user\n'`
    (line 145).
  - `formal/conformance/encode.py::schema_to_json` reads the oracle's UNCHECKED parse.
  - In the OpenFGA sources the scout copied, `validate-dsl.ts` (lines 923-931) and
    `typesystem.go::IsSchemaVersionSupported` both accept `1.1` and `1.2`.
  - `OpenFGAParser.g4::relationDefPartials` is the three-alternative rule §1 item 4 describes.
- first-hand PROBE: re-running `probe_fuzz_floor.py` gives the same output (`refused 17089
  accepted 911`, projected `455` against the floor `450`). The fuzz test takes 5.07s
  (`--durations`), so step 8's doubling of `_FUZZ_TRIALS` is cheap.
- first-hand PROBE: `pytest tests --collect-only` gives `2401 tests collected`, which equals
  `formal/verify.sh` `MIN_TESTS_ALL=2401` and the prototype's `8 failed, 2393 passed`. So the
  `tests/` prototype run covered the whole suite (without PostgreSQL).
- first-hand READ (grep of `formal/lean/ZanzibarProofs` for `"but"`, `"define"`,
  `"relations"` and `parseSchema` finds 0 hits): no Lean code parses DSL text, so "no Lean
  edit" holds. Of the claim-rot pins, `formal/correspondence_anchor_pin.txt` lines 416-420 and
  498-501 match §8's list. `tests/oracle.py::_Parser._expr` and the product
  `_RelationParser` are not pinned.

**C1. The S7 refusal is STRUCTURAL, so its sabotage only bites through the message.**
- first-hand PROBE `probe_s7_sabotage.py`: step 5's restructure was patched in with NO
  `_reject_unparenthesised_but_not` call, and it still refuses all five S7 shapes. Literal
  output:
  `'[user] or a but not b' REFUSE relation 'viewer': unexpected token 'but'`,
  `'a but not b or c' REFUSE ... unexpected token 'or'`, and likewise for `and`, `but`,
  `but`. The parenthesised controls still parse to the expected ASTs.
- So the explicit reject only supplies the MESSAGE. In §7, `test_but_not_mixed_with_or_and_is_refused`
  must assert `match=` on the parenthesise message in BOTH parsers. A bare
  `pytest.raises(ValueError)` stays green when the reject call is deleted: the plan's S7
  sabotage fails by passing.
- The same applies to the new `_REFUSED` entries in `test_p23`. They pin parity, not the
  check, so they are not the S7 sabotage target.
- (REASONED) The oracle's generic `trailing tokens` raise makes the oracle twin behave the
  same way.

**C2. S8 swallows THREE round-trip witnesses, not two, and both branches of the guard lose
their JSON input.** (first-hand READ)
- `tests/test_openfga_json.py::test_rejects_model_whose_dsl_rendering_is_a_different_schema`
  has a third id, `V14-unparseable` (`{"type": "us er"}`, asserting `does not parse`).
- The prototype checked S8 AFTER the round trip. That is why only V9 and comma went red: V14
  still reached the guard's "does not parse" branch first. Step 7 puts S8 BEFORE the round
  trip, so V14 is refused by S8 too.
- Because every malformed restriction-type string is also an undeclared type, NO JSON input
  can reach either guard branch any more. (first-hand PROBE `probe_extra.py` X10: a JSON
  one-child `union` normalises to `Computed('owner')`, so it is not a witness either.)
- Fixes:
  - Flip all three ids.
  - Add a direct-call witness for EACH branch. "Different schema":
    `Union((Computed('owner'),))`. "Does not parse": a restriction type `us er`, which the
    step-2 unparser renders as the malformed line `type us er`.

**C3. The direct-call witness pins the guard's BODY, not its CALL.**
- (REASONED) Deleting `_validate_json_round_trip(ast)` from `json_frontend.py::parse_openfga_json`
  (line 107 on 2026-10-14) would leave `test_round_trip_guard_keeps_a_live_witness` green.
- Add one end-to-end test that monkeypatches `json_frontend.unparse_schema_ast` (the name as
  imported there) to return a perturbed rendering. It then asserts that `parse_openfga_json`
  on a VALID model raises `parses to a different schema`.
- Sabotage it by deleting the call.

**C4. Forward references must stay legal. Test it, because step 2 depends on it.**
- first-hand PROBE X3: a schema whose `define viewer: [user]` comes before its `type user` is
  ACCEPTED by both parsers today.
- Step 2 emits relationless types at the END, so every `openfga_json_to_dsl` output becomes
  this shape. For example X11, today's output, is
  `'type doc\n  relations\n    define viewer: [user]\n'`, and it gains a trailing
  `type user`.
- The S8 check must therefore run on the FINAL declared set after the whole file is read.
  Add a `forward-reference` control to `test_kept_extensions_still_parse` and to `test_p23`
  `_ACCEPTED`. A per-`define` check would pass every other test and break the converter.

**C5. Header shapes the plan leaves undecided.** (first-hand PROBE X1, X2, X6, X7; both
parsers ACCEPT each one today)
- X1: a `relations` line before any `type`.
- X2: `model` / `schema 1.1` after a type block. The §2 probe row S2d was not put in the §0
  table.
- X6, X7: `relations # comment` and `model # comment`.
- Under step 3, X6 and X7 (and §2 S1f, `schema 1.1 # c`) become REFUSED. That is consistent
  with S12 and with TK123's finding A33 (`'type user  # people'` is refused), and `git grep`
  finds 0 tracked uses. But §0 never says so. Name it in the H2 block's INSTEAD ("put the
  comment on its own line") and add a test case.
- X1 and X2 are harmless. Recommend KEEP and document them, or refuse X2 as never intended.
  Either way, decide on the row and add controls.

**C6. Parity tests compare KEYS only.**
- (READ) `test_p23::test_both_parsers_accept_the_controls_with_the_same_keys` and the planned
  `test_kept_extensions_still_parse` compare `set(keys)`.
- Step 5-6 rewrites the expression grammar in both parsers, so a regression that changes an
  Expr but keeps the keys passes both.
- `test_parenthesised_but_not_still_parses` must assert the full expected AST for the product
  AND an oracle-structural expectation (the `O*` classes), not just the product.

**C7. A sibling surface: `object_wildcard_shapes` naming an undeclared type or relation is
silently accepted.**
- first-hand PROBE X9: `parse_openfga_schema(..., object_wildcard_shapes={('nosuch','viewer')})`
  and `{('doc','nosuchrel')}` both ACCEPT.
- REASONED: this fails closed (it is a no-op shape), so it is not a grant like S8, but it is
  the same typo class.
- It is out of TK137's DSL scope. File a row or note it, rather than widening TK137.

**C8. TK123 sequencing goes beyond the rename (R2).** (first-hand READ of
`docs/tk123-api-review-2026-10-14.md`)
- A36 plans `Store(schema=<JSON>)` dispatch to the JSON front end and itself says "land
  together with TK137 S8". Any JSON-to-persisted-DSL path depends on step 2.
- A53 plans compare-by-parse on governed `SetEngine` opens, which adds one more place a
  pre-TK137 persisted text will fail to parse (R1).
- Order: TK137 steps 1-2 (the unparser) before TK123's A36, or in the same commit.

**C9. Scope outside `tests/` that no instrument ran.**
- first-hand PROBE `probe_outside_tests.py` scanned the AST string constants in 61 tracked
  `.py` files under `scripts/`, `benchmarks/`, `src/` and `docs/design/`. It found 10
  schema-like literals, and the only hit is
  `docs/design/generator-coverage/prototypes/zz_sweep_ts.py:49` S8 (a dead prototype).
- `scripts/installed_smoke.py`'s `SCHEMA_D` parenthesises its `but not` (READ, line 105).
- UNVERIFIED: f-string-built schemas in `benchmarks/`. The builder runs
  `scripts/installed_smoke.py` against the change before the next release.
- Conformance, a correction to §5/§9: the dynamic census reached all of the first 12
  conformance files by node id, alphabetically through `test_conformance_remove.py`
  (READ of `census_conf_65pct.jsonl`). The only tail it missed was
  `test_conformance_remove.py::test_graph_remove_bulk_build_survivors[...]` after
  `nary_union_derived4`. The scout prototype run on that test gives
  `27 passed, 108 deselected in 247.91s` (first-hand PROBE). The instrument is live: the
  same plugin on `tests/test_schema_ast.py -k "binds_loosest or both_sides_of_but_not"` gives
  `2 failed`.
- So the "first ~65% never ran" gap is effectively closed for the question of which schemas
  get refused. The census is not the prototype, so the builder's five `conf-tile` runs stay
  the real check.

**C10. R1 is worse than "breaking": no migration path exists, so put it to the user.**
- READ: `src/zanzibar/connectedstore/schema_io.py::open_set_engine` leads to `SetEngine(text)`,
  which leads to the checked `parse_schema_ast`. `::_same_schema` only skips the re-parse for
  identical text.
- So a store persisted with an S8, S7 or H2 text cannot be opened, and there is no public way
  to drop the store id.
- REASONED: whether to break pre-1.0 stores is a compatibility-versus-strictness GOAL
  question, not a proof mechanic. Per `CLAUDE.md` § "Who decides", the coordinator asks the
  user in chat rather than recording it silently.
- A cheap middle path the scout did not weigh: no lenient mode, but wrap the persisted-text
  parse in `load_schema` / `open_*` so the error says "persisted under <= 0.0.4, refused
  since TK137: <reason>". The user then knows it is a version break, not corruption.

**C11. S8 is a new decision, not just "finishing" ASK-1.**
- READ of `docs/ask1-schema-self-consistency-2026-09-26.md` § "Not adopted, and why". Its
  reasons are the unparser round trip AND "That is not a dangling *relation*, and neither
  proof field depends on it". So S8 was out of ASK-1's scope, not only blocked technically.
- The sibling "not adopted" bullet (tupleset direct-only) was later adopted by a USER
  decision (`TK106`, 2026-09-26).
- Record S8 on the row as a fresh decision with that reasoning. The ASK-1 correction should
  say "extended by TK137", not "completed".

**C12. Smaller judgement calls.**
- H1 refusing `schema 1.2` is STRICTER than OpenFGA, which accepts it (§1 item 1). The
  REFUSED SHAPE WHY must say "only 1.1 is implemented; the version was silently ignored", not
  "OpenFGA refuses it".
- Step 2 puts relationless types at the END to keep one `.splitlines()[2]` index valid. Every
  OpenFGA example declares `type user` FIRST, so a reader of `openfga_json_to_dsl` output
  would find START more natural. Changing that test's index lookup to a search is not a
  weakening. Builder's choice, but decide it deliberately.
- S8 must also cover `[usr#...]`. It is a bare restriction (`predicate='...'`), so ASK-1 never
  sees it. Add it to the `test_undeclared_restriction_type_is_refused` params.

**Revised §6 order (deltas only):**
- Step 7 adds the C4 forward-reference control.
- Step 11 adds the C1 message-matching, the C2 third flip plus the two direct witnesses, the
  C3 call-site test, the C5 header-comment cases and the C6 full-AST assertions.
- Step 10's CHANGELOG entry names the "no migration path" consequence (C10).
- Land TK137 steps 1-2 before TK123's A36 (C8).

## 0. The decision in one screen (REASONED; the scout's recommendation, not yet recorded on the row)

| # | shape | today (both parsers) | OpenFGA | recommendation |
|---|---|---|---|---|
| H1 | `schema` line naming any version but `1.1` (`1.2`, `9.9`, `1.0`, `abc`, bare `schema`) | ACCEPT, version ignored | DSL validator accepts `1.1` / `1.2` only | **REFUSE** everything but `schema 1.1` |
| H2 | a `model` / `schema` / `relations` line with extra words | ACCEPT, extra words DROPPED — `relations define viewer: [user]` **silently loses the relation** | grammar refuses | **REFUSE** (a silent drop, the blind-audit S-3 class) |
| H3 | no `model` / `schema` header at all | ACCEPT | grammar requires it | **KEEP, document** (the unparser emits no header, persisted texts lack one) |
| H4 | `define` with no `relations` line since its `type` | ACCEPT | grammar refuses | **KEEP, document** (no ambiguity) |
| S5 | two direct blocks in one definition (`[user] or [doc]`, `[user] but not [user:*]`) | ACCEPT | DSL grammar refuses; the JSON API accepts the same tree | **KEEP, document** (see §3) |
| S6 | a direct block not first (`a or [user]`, `a but not [user]`) | ACCEPT | DSL grammar refuses; the JSON API accepts the same tree | **KEEP, document** (see §3) |
| S7 | `but not` sharing a paren level with `or` / `and` (`[user] or a but not b`, `a but not b or c`) | ACCEPT, `but not` binds loosest on BOTH sides | grammar refuses | **REFUSE** (a reader can take `a but not b or c` as `(a but not b) or c`; this parser reads `a but not (b or c)`) |
| S8 | a restriction naming an undeclared type, `[usr]` / `[usr:*]` | ACCEPT; a `usr:x` write is then admitted | typesystem refuses | **REFUSE** (a typo grants access; finishes ASK-1, §5 note). The most design work (§4), but only 4 tests break (§5) |
| S9 | conditions (`[user with c]`), `module`, `extend type`, `condition` blocks | REFUSE with a generic message | supported | **keep refusing, say WHAT** (message + REFUSED SHAPE block only) |
| S10 | names OpenFGA refuses: `self` / `this`, `@` `+` `=`, a leading digit, a relation over 50 chars | ACCEPT | refuses | **KEEP, document** (P23 deliberately made the declared-name charset the WRITE charset) |
| S11 | `[group#...]` | ACCEPT as `[group]` | grammar refuses | **KEEP** (P23 pins it as an accept control) |

The refusals are H1, H2, S7, S8, plus clearer messages for S9. S5 / S6 stay as documented extensions.

## 1. What OpenFGA actually refuses (first-hand READ, sources fetched 2026-10-14)

Sources (curl'd raw from `main`, copies in `.scratch/now-next/probes/scout-TK137/`):
`openfga/language` `OpenFGAParser.g4` (106 lines), `OpenFGALexer.g4`,
`pkg/js/validator/validate-dsl.ts`; `openfga/openfga` `pkg/typesystem/typesystem.go`.

1. **Header.** `OpenFGAParser.g4::main` requires `(modelHeader | moduleHeader)`;
   `modelHeader: ... MODEL NEWLINE SCHEMA WHITESPACE schemaVersion=SCHEMA_VERSION WHITESPACE?`,
   `SCHEMA_VERSION: DIGIT+'.'DIGIT+`. The version is checked semantically:
   `validate-dsl.ts::validateJSON` has `switch (schemaVersion) { case "1.1": case "1.2": ...;
   default: raiseInvalidSchemaVersion }`, and `typesystem.go::IsSchemaVersionSupported`
   accepts `1.1` and `1.2`. **So OpenFGA ACCEPTS `schema 1.2`** (the modular-models version;
   its additions are `module` / `extend type`, which this library refuses). `9.9`, `1.0`, `abc`
   and a bare `schema` are refused. The task row's "OpenFGA refuses `schema 1.2`" framing is
   imprecise: the defect is that the header is IGNORED here, while the JSON front end
   (`src/zanzibar/schema/json_frontend.py::parse_openfga_json`) already refuses anything but
   `'1.1'`.
2. **`relations` is mandatory before `define`s** (`typeDef: ... TYPE WHITESPACE typeName
   (NEWLINE RELATIONS relationDeclaration+)?`), and a header / `relations` line carries no
   other words.
3. **Direct blocks: first operand only, so at most one.**
   `relationDef: (relationDefDirectAssignment | relationDefGrouping | relationRecurse) (relationDefPartials)?`;
   `relationDefPartials` allows only `relationDefGrouping | relationRecurseNoDirect` after an
   operator, and `relationRecurseNoDirect` holds no direct block at any depth. Net rule: a
   `[...]` block may appear only where every token before it is `(` (the leftmost spine).
   `([user] or a) and b` IS legal; `a or [user]`, `a but not [user]`, `[user] or [doc]` are not.
4. **Operators do not mix at one level.** `relationDefPartials: (OR g)+ | (AND g)+ | (BUT_NOT g)`
   is three alternatives, so one level holds only `or`s, only `and`s, or exactly one `but not`.
   `[user] or a but not b`, `a but not b or c`, `a and b but not c`, `a but not b but not c` are
   all refused; parenthesise.
5. **The JSON / API form has no positional rule for `this`.**
   `typesystem.go::isUsersetRewriteValid` recurses through union / intersection / difference
   children with no check on where `this` sits (READ). REASONED, not run against a server:
   the server therefore accepts `difference{base: computedUserset, subtract: this}` and two
   `this` nodes. So S5 / S6 restrict OpenFGA's DSL SYNTAX, not its model: the same trees are
   legal OpenFGA authorization models.
6. **Undeclared restriction types are refused.** `typesystem.go::validateTypeRestrictions`
   rule 3: "For each type restriction referenced for an assignable relation, each of the
   referenced types and relations must be defined in the model"; `t.GetRelations(relatedObjectType)`
   errors for an undeclared type, giving `InvalidRelationTypeError`.
7. **Reserved names.** `typesystem.go::validateNames` refuses a type or relation named
   `self` or `this`; the lexer's `EXTENDED_IDENTIFIER: (LETTER | '_')((SLASH | DOT | MINUS)?(LETTER | DIGIT | '_')+)*`
   refuses a leading digit, `@`, `+`, `=` (all legal declared names here since `P23`).
8. **Trailing comments.** `multiLineComment` appears only on its own line before a
   `typeDef` / `relationDeclaration`, so `define viewer: [user] # c` is not OpenFGA DSL
   (refused here too, probe row S12). `validate-dsl.ts::getSchemaLineNumber` tolerates
   `schema 1.1 # ...` only to FIND the line for an error message (READ; whether the grammar
   accepts it was not traced, UNVERIFIED).
9. **Tuplesets (aside, beyond TK137).** `typesystem.go::isUsersetRewriteValid`, TTU branch:
   "Tupleset relations must only be direct relationships, no rewrites are allowed on them" —
   the tupleset's rewrite must be exactly `this`. So OpenFGA refuses `parent: [folder] or [doc]`
   as a tupleset even in JSON; `TK106` here accepts "Directs or a union of Directs"
   (`CLAUDE.md` § Gotchas). Already documented as an extension; nothing to do in TK137.


## 2. What both parsers do today (first-hand PROBE + READ)

Probe: `.scratch/now-next/probes/scout-TK137/probe_shapes.py`, run 2026-10-14 against HEAD
`0b09687`: `zanzibar.schema.parse_schema_ast` and `tests/oracle.py::parse_schema_ast` on the
same text (header `model / schema 1.1`, `type user / type doc / relations` unless the row
says otherwise). Literal output, condensed to one line where the two parsers agree. **They
agreed on accept/refuse in EVERY case**, so parity is intact today; the work is to move both
together.

```
S1a schema 1.2                         product: ACCEPT   oracle: ACCEPT
S1b schema 9.9                         product: ACCEPT   oracle: ACCEPT
S1c schema (no version)                product: ACCEPT   oracle: ACCEPT
S1d schema abc                         product: ACCEPT   oracle: ACCEPT
S1e schema 1.0                         product: ACCEPT   oracle: ACCEPT
S1f schema 1.1 # comment               product: ACCEPT   oracle: ACCEPT
S2a no header                          product: ACCEPT   oracle: ACCEPT
S2b schema w/o model                   product: ACCEPT   oracle: ACCEPT
S2c model w/o schema                   product: ACCEPT   oracle: ACCEPT
S2d header after types                 product: ACCEPT   oracle: ACCEPT
S3a model junk                         product: ACCEPT   oracle: ACCEPT
S3b relations + define on one line     product: ACCEPT   oracle: ACCEPT
S3c relations junk                     product: ACCEPT   oracle: ACCEPT
S4 define w/o relations line           product: ACCEPT   oracle: ACCEPT
S5a [user] or [doc]                    product: ACCEPT   oracle: ACCEPT
S5b [user] and [doc]                   product: ACCEPT   oracle: ACCEPT
S5c ([user] or a) and [user]           product: ACCEPT   oracle: ACCEPT
S6a a or [user]                        product: ACCEPT   oracle: ACCEPT
S6b a but not [user]                   product: ACCEPT   oracle: ACCEPT
S6c a and ([user] or b)                product: ACCEPT   oracle: ACCEPT
S6d ([user] or a) and b (OK in OpenFGA) product: ACCEPT  oracle: ACCEPT
S7a [user] or a but not b              product: ACCEPT   oracle: ACCEPT
S7b a but not b or c                   product: ACCEPT   oracle: ACCEPT
S7c a and b but not c                  product: ACCEPT   oracle: ACCEPT
S7d a but not b and c                  product: ACCEPT   oracle: ACCEPT
S7e (a or b) but not c (OK)            product: ACCEPT   oracle: ACCEPT
S7f a but not (b or c) (OK)            product: ACCEPT   oracle: ACCEPT
S7g a but not b but not c
    product: REFUSE ValueError: relation 'viewer': unexpected token 'but'
    oracle : REFUSE ValueError: relation 'viewer': trailing tokens
S8a [usr] undeclared type              product: ACCEPT   oracle: ACCEPT
S8b [usr:*] undeclared type            product: ACCEPT   oracle: ACCEPT
S8c [usr#member] undeclared
    product: REFUSE ValueError: doc#viewer: restriction [usr#member] names an undeclared relation usr#member
    oracle : REFUSE ValueError: doc#viewer: undeclared restriction usr#member
S9a [user with c]   both: REFUSE ValueError: invalid subject type in restriction 'user with c'
S9b module header   both: REFUSE ValueError: unrecognized schema line: 'module core'
S9c extend type     both: REFUSE ValueError: unrecognized schema line: 'extend type doc'
S9d condition block both: REFUSE ValueError: unrecognized schema line: 'condition c(x: int) {'
S10a type self, S10b relation this, S10c a@b, S10d 9x, S10e a+b=c,
S10f relation 60 chars, S10g type a.b  both: ACCEPT
S11 [user#...]                         both: ACCEPT
S12 trailing comment
    product: REFUSE ValueError: relation 'viewer': unexpected token '#'
    oracle : REFUSE ValueError: relation 'viewer': trailing tokens
S12b keyword OR uppercase
    product: REFUSE ValueError: relation 'viewer': unexpected token 'OR'
    oracle : REFUSE ValueError: relation 'viewer': trailing tokens
```

ASTs the product parser built (same probe, literal; `R(user)` abbreviates
`Restriction(type='user', predicate='...', wildcard=False)`):

```
S3b  'relations define viewer: [user]', then '  relations' / 'define owner: [user]'
     -> {('doc', 'owner'): Direct((R(user),))}          # doc#viewer IS GONE, no error
S5a  [user] or [doc]        -> Union((Direct((R(user),)), Direct((R(doc),))))
S7a  [user] or a but not b  -> Exclusion(base=Union((Direct((R(user),)), Computed('a'))), subtract=Computed('b'))
S7b  a but not b or c       -> Exclusion(base=Computed('a'), subtract=Union((Computed('b'), Computed('c'))))
S7c  a and b but not c      -> Exclusion(base=Intersection((Computed('a'), Computed('b'))), subtract=Computed('c'))
S7d  a but not b and c      -> Exclusion(base=Computed('a'), subtract=Intersection((Computed('b'), Computed('c'))))
```

S7b is the trap: read left to right it looks like `(a but not b) or c`, and it means
`a but not (b or c)`. The two grant different subjects (anyone in `c` but not `a`).

### 2.1 Where each shape is accepted (first-hand READ; line numbers dated 2026-10-14)

- **H1 / H2 / H3 / H4.** `src/zanzibar/schema/parser.py::_parse_schema_ast_unchecked`
  lines 200-203: `if head in ('model', 'schema', 'relations'): continue`. The WHOLE line is
  skipped on its first word, so the rest of it is never read. That is how S3b loses `viewer`:
  its head is `relations`. Nothing records whether a header or `relations` line was seen.
  Oracle twin: `tests/oracle.py::parse_schema_ast_unchecked` lines 291-294, the same skip.
- **S5 / S6 / S7.** `src/zanzibar/schema/parser.py::_RelationParser` (grammar in its
  docstring, lines 51-56: `expr := chain ('but not' chain)?`, `chain := unit (OP unit)*`,
  `unit := '(' expr ')' | leaf`, `leaf := type-restriction-list | REL | REL 'from' REL`). A
  bracket is a `leaf`, so it may sit wherever a unit may (S5, S6). `::_parse_expr`
  (lines 76-80) parses `chain 'but not' chain`, so either side of `but not` may be a chain
  (S7). The only mixing refusal is the `or`/`and` check in `::_parse_chain` (lines 96-107).
  Oracle twin: `tests/oracle.py::_Parser._expr` / `::_Parser._chain` / `::_Parser._leaf`.
  The same grammar is written in `docs/specs/set-engine-spec.md` §2.2 ("at most one
  exclusion, loosest binding") and `formal/SEMANTICS.md` §4.1 ("both parsers implement it
  identically -- this identity is load-bearing for T0/conformance").
- **S8.** Neither parser compares bracket types with `type` lines. `[usr#member]` IS refused,
  by ASK-1 (`src/zanzibar/schema/parser.py::_validate_ast_consistency`, oracle
  `tests/oracle.py::_validate_consistency`), because a userset names a RELATION, which the AST
  shows. A bare `[usr]` names only a TYPE, and `SchemaAST = {(type, relation): Expr}` does not
  record relationless types, so **no AST-level validator can see S8**: only the local
  `seen_types` inside each `_parse_schema_ast_unchecked` knows `type user` was declared.
  The JSON front end has its own `seen_types` in `json_frontend.py::parse_openfga_json`.
- **S9.** `[user with c]` dies in the restriction parser (product
  `src/zanzibar/schema/rules.py::parse_relation_rule`, reached from
  `_RelationParser._parse_leaf`; oracle `tests/oracle.py::_parse_restrictions`' `_NAME_RE`
  check). `module` / `extend` / `condition` die in the final `else: raise
  ValueError(f'unrecognized schema line: ...')` of both `_parse_schema_ast_unchecked`s.

### 2.2 The unparser EMITS two of these shapes (first-hand READ)

`src/zanzibar/schema/unparse.py::unparse_schema_ast`:

- **S7.** `render` turns an `Exclusion` into `f'{base} but not {sub}'` with
  `base = _chain(e.base)`, and `_chain` parenthesises only a nested `Exclusion`. So
  `Exclusion(Union(a, b), c)` renders as `a or b but not c`.
- **S5 / S6.** Children render in AST order, so `Union((Computed('a'), Direct(...)))`
  renders `a or [user]`, and two `Direct` children render `[user] or [doc]`.
- **H3, and S8's blind spot.** It emits no `model` / `schema` header, and declares only types
  that key a relation (`types_in_order` comes from the AST keys), so a restriction type with
  no relations (`user`) gets NO `type user` line.

Who re-parses unparser output (READ, grep 2026-10-14): the JSON front end's round-trip guard
`src/zanzibar/schema/json_frontend.py::_validate_json_round_trip`
(`parse_schema_ast(unparse_schema_ast(ast))`), and every AST generator:
`tests/test_hypothesis.py` (lines 421, 770, 804, 872, 970, 1001, 1034, 1358),
`tests/genswarm.py:1271`, `tests/test_generator_coverage.py` (about 20 sites),
`tests/test_lookup_oracle.py:575,656`, `tests/test_tk116_oracle_only_setengine.py:383`,
`tests/test_boolean_compile.py:491,505`. **Consequence (REASONED): each new refusal must
first be made unreachable from `unparse_schema_ast`**, or the JSON front end starts refusing
valid OpenFGA JSON and the generators start emitting text the parser refuses. For S7 that is
a two-line fix (parenthesise a `Union` / `Intersection` operand of `but not`); for S8 it is
"also declare every referenced type"; for H3 it means headerless must stay legal. For S5 / S6
there is NO fix: `Exclusion(Computed, Direct)` (`a but not [user]`) and two `Direct`s in
different branches have no OpenFGA-DSL rendering at all. That is the core of §3.

## 3. Why S5 / S6 stay accepted (REASONED, with the evidence each point rests on)

The scout recommends documenting S5 (two direct blocks) and S6 (a direct block not first) as
this library's extension to OpenFGA's DSL syntax, not refusing them. Four reasons:

1. **They are legal OpenFGA MODELS, only not legal OpenFGA DSL** (§1 item 5, READ of
   `typesystem.go::isUsersetRewriteValid`; server behaviour REASONED, not run). The JSON
   front end accepts `this` anywhere, as the OpenFGA API does. A DSL refusal would leave the
   DSL unable to express trees the JSON path accepts.
2. **A DSL refusal propagates into the JSON front end.** `_validate_json_round_trip`
   re-parses `unparse_schema_ast`'s output (§2.2). `Exclusion(Computed, Direct)` (JSON
   `difference{base: computedUserset, subtract: this}`) has no OpenFGA-DSL rendering, so
   refusing S6 would make the JSON front end refuse a valid OpenFGA JSON model with the
   generic "its DSL rendering does not parse". Reordering `union` / `intersection` children
   to put the Direct first would fix only some cases, and it changes the AST, so the
   round-trip equality check (`ast[k] != back[k]`) would need to compare modulo order.
3. **The AST generators produce them constantly** (first-hand PROBE, census §5): hundreds of
   distinct S5 / S6 bodies from `tests/test_hypothesis.py` and `tests/test_generator_coverage.py`
   in the first 20% of `tests/` alone, e.g. `[user, user:*] but not [user]`,
   `[user] or [doc:*#r1]`, `( [user] and r0 ) or [user]`. Refusing them means constraining
   the generators, which shrinks the shapes the validation matrix explores
   (`tests/test_generator_coverage.py` is a coverage GATE over generated features). It also
   means rewriting the hand-written wildcard-exclusion pins (`[user] but not [user:*]` in
   `tests/test_processor.py:146`, `tests/test_oracle_boolean.py:81`,
   `tests/scenarios/__init__.py:114`) through a helper relation, which changes the compiled
   leaf structure under test, not just the spelling.
4. **They are unambiguous.** `[user] or [doc]` means `[user, doc]`; `a or [user]` means
   `[user] or a`. The equivalence goal (graph index == set engine == oracle) is untouched
   either way, and a first-time user loses nothing by being allowed them. What a user can
   lose is portability: a schema written here may not load in OpenFGA tooling. That is a
   documentation duty, so `PYPI_README.md`'s "a subset of the OpenFGA modelling DSL" must
   become "a subset ... plus these extensions" (§6 step 10).

The cost of refusing S5 / S6 later, if the user wants strict OpenFGA DSL, is the same as now
plus whatever is written in the meantime; nothing here makes it harder.

## 4. S8 (undeclared restriction types) needs its own design (REASONED)

S8 is the refusal with the largest blast radius, and the only one the AST cannot see (§2.1).
Three constraints decide its shape:

- **Where the check can live.** Only the text-level parse knows relationless types. Two options:
  - (a) **The scout's recommendation:** split each `_parse_schema_ast_unchecked` into a body
    that returns `(ast, declared_types)` plus the existing one-value wrapper. `parse_schema_ast`
    (the CHECKED parse) then calls a new `_validate_restriction_types_declared(ast,
    declared_types)` beside `_validate_ast_consistency`. This keeps the ASK-1 precedent: a
    dangling reference is a checked-parse refusal, so `w4_fragment_report`,
    `graph_admission_report` and the conformance encoder (`formal/conformance/encode.py::schema_to_json`,
    which reads `tests/oracle.py::parse_schema_ast_unchecked`) can still describe such a schema.
  - (b) Simpler: call it from inside `_parse_schema_ast_unchecked` next to TK124's
    `_validate_declares_a_type(seen_types, ast)`, which already has `seen_types`. The cost
    is that the non-raising reports and the encoder start raising on a typo schema.
- **The unparser must declare what it references.** `unparse_schema_ast` emits `type T` only
  for types that key a relation (§2.2), so after S8 its output for any AST restricting to
  `user` (no relations) would be REFUSED on re-parse. Every generator and the JSON round trip
  would break at once. Fix: after the keyed types, emit `type T` for every restriction type
  that is not a key type, sorted, at the END. At the end, because
  `tests/test_openfga_json.py::test_wildcard_empty_object_and_null_keep_their_canonical_meaning`
  indexes `.splitlines()[2]`. Relationless types are not AST keys, so `parse(unparse(ast)) == ast`
  still holds.
- **The JSON front end has its own `seen_types`** (`json_frontend.py::parse_openfga_json`),
  so it calls the same shared validator after its loop. OpenFGA refuses such JSON too (§1 item 6).

**Measured exposure** (first-hand PROBE, `probe_fuzz_floor.py`, replaying
`tests/test_p23_parser_refusal_parity.py`'s fuzz with its own seeds, alphabet and trial
count; literal output):

```
today: refused 17089 accepted 911  (floors: MIN_FUZZ_REFUSED=8000 MIN_FUZZ_ACCEPTED=450)
accepted mutants the new refusals would refuse: 456  by shape {'H1': 37, 'H2': 26, 'S7': 0, 'S8': 399}
projected accepted after TK137: 455; accepted mutants using S5/S6 (kept): 0
```

So **399 of the 911 "accepted" fuzz mutants (44%) restrict to a type nobody declared**
(typically a one-character edit of `[user]`). The parity fuzz has been comparing typo
schemas. After TK137 the accepted side projects to **455 against a floor of 450**: too thin.
§6 step 8 handles it.

The hand-written exposure (test schemas that restrict to a type they never declare) is
measured in §5 (dynamic census, S8 rows).

**Lean (REASONED).** S8 narrows the admitted INPUTS on the Python side, like `P23`'s
declared-name charset (`formal/CORRESPONDENCE.md` GraphAdmission row, "a Python-side narrowing
of the admitted inputs, not a model assumption"). No Lean field and no Lean edit. The Lean
side sees ASTs (`encode.py`), never DSL text, so none of the TK137 refusals is a Lean change.

## 5. Who uses these shapes today (first-hand PROBE)

Three instruments, each blind to something different:

- **Static census** (`census_static.py`): every literal `define X: body` in tracked files,
  classified by the OpenFGA position rules. 1835 bodies scanned. Code-path hits only (docs
  and closed rows excluded):
  - **S7: 2 test files.** `tests/test_schema_ast.py:122` `a or b but not c`, `:152`
    `a or b but not (c and d)`; `tests/test_lookup_oracle.py:1142` / `:1144` (one regression
    pin, see below).
  - **S5 / S6: about 20 test sites plus 2 corpus lines.** `formal/conformance/corpus.py:1324-1325`,
    `tests/test_processor.py:146,355`, `tests/test_oracle_boolean.py:81`,
    `tests/scenarios/__init__.py:114`, `tests/test_tupleset_must_be_direct.py:71,85`,
    `tests/genswarm.py:851,890`, `tests/test_hypothesis.py:1090-1091,1152`,
    `tests/test_self_referential_tuples.py:105-106`, `tests/test_boolean_compile.py:441`,
    `tests/test_tk114_stratified_negation.py:57,94`, `tests/test_blind_audit_regressions.py:52`, ...
  - **H1 (a version other than 1.1): 0** in code, tests, README or PYPI_README.
    `git grep -E "schema +[0-9]+\.[0-9]+"` minus `1.1` hits only the audit doc, the two
    install-trial docs (`docs/pypi-trial-0.0.3-2026-10-08.md:111` and
    `docs/pypi-trial-0.0.4-2026-10-13.md:220` both flagged the silent header as CONFUSING)
    and the TK137 row.
  - **README / PYPI_README**: the one DSL block (`PYPI_README.md`) has the `schema 1.1`
    header, declares every restriction type and uses no S5-S8 (`probe_s8_files.py`). All 15
    `tests/fga_schemas/*.fga` fixtures likewise.
- **Dynamic census** (`tk137_census.py`, a pytest plugin recording every ACCEPTED body per
  test id). It ran over the first ~20% of `tests/` and ~65% of `formal/conformance/` before
  it was stopped for the prototype run below. It confirms the generators as the bulk users of
  S5 / S6 / S7: hundreds of distinct bodies from `tests/test_hypothesis.py`,
  `tests/test_generator_coverage.py` and `formal/conformance/test_conformance_generated.py`.
  Every S7 among them is the unparser's bare `but not` chain (§2.2), for example
  `r0 from parent or r1 but not r1 and r0 from parent`. Its S8 hits were all
  `tests/test_boolean_compile.py::test_parser_round_trip[*]`: the CURRENT unparser drops the
  relationless `type user`, which is exactly what step 2 fixes. H3 (no header) and H4
  (`define` without `relations`) are common (hundreds of test ids; conformance's
  `test_conformance_fragment.py` alone has thousands of H4 bodies), which is one more reason
  to KEEP both. Conformance S8 hits in the 65% sample: **0**.
- **Monkeypatch prototype over the WHOLE of `tests/`** (`tk137_proto.py`, a pytest plugin
  that patches in memory: header H1 + H2, S7 in both parsers, S8 in both checked parsers and
  the JSON front end, and the step 1-2 unparser). This is the sizing number: which tests a
  real implementation turns red. Literal tail (2026-10-14, 54m45s):

  ```
  FAILED tests/test_lookup_oracle.py::test_graph_userset_subject_through_derived_wildcard_gap
  FAILED tests/test_openfga_json.py::test_rejects_model_whose_dsl_rendering_is_a_different_schema[V9-injects-relation]
  FAILED tests/test_openfga_json.py::test_rejects_model_whose_dsl_rendering_is_a_different_schema[comma-splits-restriction]
  FAILED tests/test_oracle.py::test_parse_schema_classification - ValueError: g...
  FAILED tests/test_p23_parser_refusal_parity.py::test_both_parsers_accept_the_controls_with_the_same_keys[header-lines-with-junk]
  FAILED tests/test_schema_ast.py::test_exclusion_binds_loosest - ValueError: r...
  FAILED tests/test_schema_ast.py::test_both_sides_of_but_not_may_be_chains - V...
  FAILED tests/test_zt_p5_readjudication.py::test_zt_p5_undefined_restriction_type_still_compiles_and_reads_empty
  8 failed, 2393 passed in 3285.12s (0:54:45)
  ```

  **Eight, every one expected**, and the generators, the hypothesis round trip, the matrix
  and the p23 fuzz all stayed green once the unparser was fixed. (The fuzz passed on the
  thin margin §4 projected; step 8 still applies.) Per failure:

  | test | shape | fix (keep the count; never weaken the check) |
  |---|---|---|
  | `test_lookup_oracle.py::test_graph_userset_subject_through_derived_wildcard_gap` | S7 in a hand-reduced regression pin (`r0: [user:*] or [user:*] but not (...)`, `r3: r1 but not [doc#r1] or [doc#r1]`) | parenthesise to the CURRENT (loosest) reading: `([user:*] or [user:*]) but not (...)` and `r1 but not ([doc#r1] or [doc#r1])`. Assert the new text parses to the SAME AST as the old one did (capture it before the change), so the regression pin is provably unchanged |
  | `test_openfga_json.py::...[V9-injects-relation]`, `[comma-splits-restriction]` | S8 takes these witnesses over (the restriction type is undeclared) | re-point at the S8 message, and add the direct-call round-trip witness (§7, §9 R3) |
  | `test_oracle.py::test_parse_schema_classification` | S8: restricts to `user` with no `type user` | add `type user` to the schema text |
  | `test_p23_parser_refusal_parity.py::...[header-lines-with-junk]` | H2: `model x y` / `relations z` was a deliberate ACCEPT control | move it to `_REFUSED` (§7) |
  | `test_schema_ast.py::test_exclusion_binds_loosest`, `::test_both_sides_of_but_not_may_be_chains` | S7: they pin the loosest-binding reading | convert to refusal + parenthesised positive (§7) |
  | `test_zt_p5_readjudication.py::test_zt_p5_undefined_restriction_type_still_compiles_and_reads_empty` | S8: pins that `[nosuchtype]` still compiles | flip to a refusal pin, both parsers. See the ASK-1 note below |

  The prototype is not the implementation. It checks S8 by re-scanning `type` lines rather
  than threading `seen_types`, and it does not touch messages (S9). It also ran without a
  PostgreSQL DSN, so `tests/test_postgres_ha.py` was not collected. None of those changes
  which schemas parse.

- **Monkeypatch prototype over `formal/conformance/`.** The full run was too slow to finish
  in the scout's window, so the prototype ran on the files the 65% dynamic census had NOT
  covered, plus `test_conformance_generated.py` (the only `formal/conformance/` user of
  `unparse_schema_ast`, `grep` 2026-10-14). Files: `test_conformance_remove_graph.py`,
  `_spec`, `_state`, `test_graphadmission_scope_pin.py`, `test_grid_independence.py`,
  `test_leaf_namespace_correspondence.py`, `test_runner_retry.py`, `test_sorry_scan.py`,
  `test_w4fragment_scope_pin.py`, `test_conformance_generated.py`. Literal result:

  ```
  40 FAILED formal/conformance/test_conformance_generated.py::test_generated_schema_zcli_parity[0..39]
   1 FAILED formal/conformance/test_grid_independence.py::test_declared_keys_agree_on_every_generated_schema
  41 E   ValueError: duplicate type declaration: 'user'
  41 failed, 337 passed in 104.48s (0:01:44)
  ```

  One cause for all 41. `formal/conformance/test_conformance_generated.py::_case` builds
  `schema_text = 'type user\n' + unparse_schema_ast(ast)` ("the unparser emits no
  `type user` line"). Once step 2 makes the unparser declare `user` itself, the prefix duplicates it.
  Fix: drop the prefix and its comment (step 2b). REASONED: the Lean input is unchanged,
  because `formal/conformance/encode.py::schema_to_json` encodes the AST, the AST has no key
  for a relationless type, and type-line order is not in the AST. Not covered by any
  instrument: the first 65% of conformance under the PROTOTYPE. The census saw no S8, H1 or
  H2 there, and its only S7 came from `test_conformance_generated.py`, which this run covers.
  The builder's full `conf-tile` run is the real check.

**The ASK-1 note (READ).** `docs/ask1-schema-self-consistency-2026-09-26.md` § "Not adopted,
and why" lists bare subject types (`[user]` with no `type user`) as NOT refused, for a
TECHNICAL reason: "A relation-less `type` line leaves no trace in a `SchemaAST`, so
`unparse_schema_ast` could not round-trip a schema that passes. Checking it would mean carrying
declared types through the AST." Step 2 (the unparser declares what it references) removes
exactly that obstacle without changing the AST. So S8 finishes the user's ASK-1 decision
("schemas must be self-consistent", 2026-09-26) rather than reversing one.
`tests/test_zt_p5_readjudication.py::test_zt_p5_undefined_restriction_type_still_compiles_and_reads_empty`
pinned the gap honestly, as a gap; flipping it is the intended consequence. The ASK-1 doc's
bullet gets a dated correction pointing here.

## 6. The plan (numbered; each step names its files and symbols)

Order matters: steps 1-2 make every new refusal unreachable from the unparser BEFORE any
refusal lands, so the JSON front end and the generators never see a red intermediate state.

1. **Unparser, S7 half.** `src/zanzibar/schema/unparse.py::unparse_schema_ast`: render both
   operands of `but not` with `_unit` (parenthesise any `Union` / `Intersection` /
   `Exclusion`), not `_chain`; delete `_chain`. `Exclusion(Union(a, b), c)` then renders
   `(a or b) but not c` (PROBE under the prototype, `probe_roundtrip_witness.py`: renders
   exactly that and `parse_schema_ast(text) == ast` is `True`). Update the docstring.
2. **Unparser, S8 half.** Same function: after the keyed types, append `type T` (plus a blank
   line) for every restriction type, collected with `syntax.py::_iter_directs`, that keys no
   relation; sorted; at the END (keeps
   `tests/test_openfga_json.py::test_wildcard_empty_object_and_null_keep_their_canonical_meaning`'s
   `.splitlines()[2]` index valid).
2b. **Conformance generator.** `formal/conformance/test_conformance_generated.py::_case`:
   drop `'type user\n' +` (and its comment and the module docstring's "explicit `type user`
   header" sentence). Without this, steps 1-2 alone turn 41 conformance tests red with
   `duplicate type declaration: 'user'` (§5).
3. **Header lines (H1 + H2), product.** `src/zanzibar/schema/parser.py`: new
   `_validate_header_line(words, line)`, called from `_parse_schema_ast_unchecked` in place
   of the bare `continue` (lines 202-203 on 2026-10-14). It refuses `schema` unless
   `words == ['schema', '1.1']`, and `model` / `relations` with any extra word. Two
   REFUSED SHAPE blocks (H1, H2). H1's INSTEAD: `schema 1.1`, noting that `1.2` (modular
   models: `module`, `extend type`) is not supported. H2's INSTEAD: put each `define` on its
   own line under a bare `relations`. Stays a PARSE-level refusal (unchecked parse too), like
   TK124's.
4. **Header lines, oracle twin.** `tests/oracle.py::parse_schema_ast_unchecked`: an
   INDEPENDENT `_validate_header_line` (no shared code: oracle independence contract), same
   blocks. ⚠ This changes the body of `tests/oracle.py::parse_schema_ast_unchecked`, which is
   claim-rot pinned (§8).
5. **S7, product.** `src/zanzibar/schema/parser.py::_RelationParser._parse_expr`: parse ONE
   unit; if `but not` follows, parse one unit as the subtrahend and refuse if any operator
   (`or`, `and`, `but not`) follows. Otherwise continue the homogeneous chain from that
   first unit, and refuse if `but not` follows the chain. The raise lives in a module-level
   `_reject_unparenthesised_but_not(relation)`, so `tests/test_refused_shape_comments.py`
   scopes it. The prototype's `tk137_proto.py::_make_prod_parse_expr` is the shape. Fold
   `a but not b but not c` into the same refusal (today it fails with a generic
   "unexpected token 'but'"). Update the class docstring grammar to
   `expr := unit 'but not' unit | chain`.
6. **S7, oracle twin.** `tests/oracle.py::_Parser._expr`, same restructure, its own
   `_reject_*` and block (`tk137_proto.py::_make_oracle_expr` is the shape).
7. **S8, product + JSON.** Recommended form, option (a) of §4:
   - split `src/zanzibar/schema/parser.py::_parse_schema_ast_unchecked` into
     `_parse_schema_ast_declared(schema) -> tuple[SchemaAST, frozenset[str]]` plus the
     one-value wrapper (its signature unchanged for `reports.py`, `genswarm.py` and the tests
     that import it);
   - add `_validate_restriction_types_declared(ast, declared_types)`: every `Restriction.type`
     reached by `_iter_directs` must be declared. Wildcards count (`[usr:*]`); userset
     restrictions are already refused by ASK-1, and this check should not double-report them;
   - call it from `parse_schema_ast` after `_validate_ast_consistency`;
   - in `json_frontend.py::parse_openfga_json`, call it with `frozenset(seen_types)`. Put the
     call BEFORE `_validate_json_round_trip`, so a JSON typo gets the named message.

   Block INSTEAD: declare the type (`type usr`), or fix the typo in the restriction.
   Oracle twin: `tests/oracle.py::parse_schema_ast` gets the same split and an INDEPENDENT
   `_validate_restriction_types_declared`. ⚠ Two more claim-rot-pinned bodies move (§8).
8. **Parity fuzz floor.** After steps 3-7, `test_p23`'s accepted side projects to **455 vs
   `MIN_FUZZ_ACCEPTED = 450`** (§4). Do not lower the floor. Raise
   `tests/test_p23_parser_refusal_parity.py::_FUZZ_TRIALS` (6000 -> 12000 doubles both sides),
   re-measure, and record the literal `refused N accepted M splits 0` with its date in the
   comment above the floors (the floors stay at about half the measured count, as the
   comment says).
9. **S9 messages (no new refusal).** Both `_parse_schema_ast_unchecked`s: before the final
   `else`, recognise heads `module`, `extend`, `condition` and raise a message naming the
   OpenFGA feature ("modules / `extend type` (OpenFGA schema 1.2) are not supported",
   "conditions are not supported"). In the restriction path, recognise ` with ` inside a
   bracket entry the same way (product: in `_RelationParser._parse_leaf` before
   `parse_relation_rule`; oracle: `_parse_restrictions`). Each in a `_reject_*` with a block;
   INSTEAD: none, with a reason, for conditions mirroring the JSON front end's
   "model the condition as a relation".
10. **Docs.**
    - `PYPI_README.md` line 4: "a subset of the OpenFGA modelling DSL" becomes subset PLUS
      named extensions. In the "Schema shapes" bullet, list the extensions kept (S5 / S6 two
      or non-leading direct blocks, H3 no header, H4 `define` without `relations`, S10 names,
      S11 `[T#...]`) and the TK137 refusals.
    - `CHANGELOG.md` `## [Unreleased]`: a `### Changed` (breaking) entry for H1, H2, S7, S8,
      with the rewrite for each; a `### Fixed` entry for S3b (a `relations define ...` line
      silently dropped the relation); and the persisted-store consequence (§9 R1).
    - `docs/specs/set-engine-spec.md` §2.2 and `formal/SEMANTICS.md` §4.1: a dated correction
      note on the grammar, replacing "loosest binding" with "operands of `but not` are units".
    - `docs/spec-deviations.md`: an entry for S5 / S6 / H3 / H4 as deliberate OpenFGA-DSL
      extensions.
    - `docs/ask1-schema-self-consistency-2026-09-26.md`: a dated correction on the
      "Bare subject types ... Not adopted" bullet, pointing at TK137 (§5 ASK-1 note).
    - `PYPI_README.md`'s "Reads are lenient; writes are strict" bullet: a schema-side typo is
      now a construction-time refusal too (the 0.0.4 trial's p16 complaint, row log 2026-10-13c).
    - `CLAUDE.md` § Gotchas: optionally one line (byte cap!) in the TK106 / TK108 style. The
      builder decides; `handoff_lint.py::MAX_BYTES` is the judge.
11. **Tests and floors** — §7, then §8.

## 7. Tests to add or flip, and the sabotage for each

New module `tests/test_tk137_openfga_dsl_refusals.py` (one file, so the floors move once):

| test | asserts | sabotage (expected to go RED) |
|---|---|---|
| `test_schema_header_must_be_1_1[1.2, 9.9, 1.0, abc, bare]` | both parsers refuse, message names `schema 1.1` | product: make `_validate_header_line` accept any `schema` line -> red for the product half AND `test_p23`'s production-refuses cases |
| `test_relations_line_with_a_define_is_refused_not_dropped` | `relations define viewer: [user]` refused. Docstring quotes the pre-fix probe: AST `{('doc','owner'): ...}`, viewer silently lost | product: allow extra words on `relations` -> red |
| `test_model_line_with_extra_words_is_refused` | `model x y` refused | as above, `model` branch |
| `test_but_not_mixed_with_or_and_is_refused[or-then, then-or, and-then, then-and, twice]` | the five S7 shapes refused in both parsers; message says parenthesise | product: remove the `_reject_unparenthesised_but_not` call after the chain -> red; separately the call after the subtrahend -> red (two mutations, two cases) |
| `test_parenthesised_but_not_still_parses` | `(a or b) but not c`, `a but not (b or c)`, `([user] or a) but not b` give the expected ASTs | control: makes "refuse every `but not`" red |
| `test_kept_extensions_still_parse[two-directs, direct-not-first, no-header, define-without-relations]` | S5 / S6 / H3 / H4 accepted by both, same keys | control: an over-eager position rule goes red here |
| `test_undeclared_restriction_type_is_refused[bare, wildcard]` | `[usr]`, `[usr:*]` refused by both checked parsers, message names `usr` | product: drop the `_validate_restriction_types_declared` call -> red |
| `test_connected_store_refuses_a_typo_schema_up_front` | `ConnectedStore(schema=<[usr] typo>)` raises at construction; before, a `usr:x` write was admitted (`TK137` row log 2026-10-13c, p16) | same mutation as above |
| `test_json_undeclared_restriction_type_is_refused` | JSON `{"type": "usr"}` with no `usr` type definition: refused, named | JSON: drop its call -> red |
| `test_unparse_declares_referenced_types` | AST with a `[user]` restriction and no `user` key: output contains `type user`, round-trips | unparse: skip the emission -> red here, and widely (generators, JSON) |
| `test_unparse_parenthesises_but_not_operands` | `Exclusion(Union(a,b), c)` and `Exclusion(a, Intersection(b,c))` render with parens and round-trip | unparse: restore `_chain` -> red |
| `test_round_trip_guard_keeps_a_live_witness` | `_validate_json_round_trip({... ('doc','viewer'): Union((Computed('owner'),))})` raises "parses to a different schema" (PROBE under the prototype: it does) | make `_validate_json_round_trip` a no-op -> red. This replaces the JSON-level witnesses S8 takes over (§9 R3) |
| `test_openfga_features_are_named[module, extend, condition, with]` | both parsers refuse with a message naming the feature | revert one message -> red |

Flips in existing tests (each is the deliberate consequence of a decision, not a golden edit;
say so in the commit):

- `tests/test_schema_ast.py::test_exclusion_binds_loosest` and
  `::test_both_sides_of_but_not_may_be_chains` pin the loosest-binding reading
  (`a or b but not c`). Convert each into a refusal test plus a parenthesised positive. Keep
  the count; do not delete.
- `tests/test_p23_parser_refusal_parity.py`: move `_ACCEPTED['header-lines-with-junk']`
  (`"model x y\nrelations z\n"`) into `_REFUSED` as `TK137/header-junk`. Add `_REFUSED`
  entries for every new shape (the parity test is the both-parsers pin) and `_ACCEPTED`
  controls for the kept extensions. Step 8 for the fuzz.
- `tests/test_openfga_json.py::test_rejects_model_whose_dsl_rendering_is_a_different_schema`,
  ids `V9-injects-relation` and `comma-splits-restriction`: under S8 these witnesses fail
  differently. PROBE under the prototype (S8 checked AFTER the round trip):
  `AssertionError: Regex pattern did not match.` for both. With step 7's order (S8 BEFORE the
  round trip) they would be refused by S8. Re-point them at the S8 message and add
  `test_round_trip_guard_keeps_a_live_witness` (above), so the TK115 guard keeps a witness.
- Hand-written test schemas that restrict to an undeclared type: the prototype found two,
  `tests/test_oracle.py::test_parse_schema_classification` (add `type user`) and
  `tests/test_zt_p5_readjudication.py::test_zt_p5_undefined_restriction_type_still_compiles_and_reads_empty`
  (flip to a refusal pin, see the ASK-1 note in §5). Fix by adding the `type` line, never by
  weakening the check.
- `tests/test_lookup_oracle.py::test_graph_userset_subject_through_derived_wildcard_gap`:
  parenthesise its S7 bodies to today's reading and assert AST equality with the old text's
  parse (§5 table), so the regression pin provably still tests the same schema.

Every new check gets the house sabotage before it is believed (`docs/sabotage-procedure.md`).
Each mutation is applied to a COPY or with an asserted-unique anchor, the literal pytest tail
is recorded in the test docstring and the commit message, and the file is restored with its
sha256 checked.

## 8. Gate impact (READ of the named files, 2026-10-14)

- **Floors.** `MIN_TESTS_ALL` / `MIN_CONF_ALL` (`formal/verify.sh`) have zero headroom and
  only go UP. The new module adds tests; flips keep their count. After landing, raise
  `MIN_TESTS_ALL` to the newly collected count (`pytest tests -q --collect-only`) and
  regenerate the counts block (`python -m formal.conformance.doc_counts --generate`).
  `MIN_CONF_ALL` moves only if a conformance test is added (none planned). Step 2b edits
  `formal/conformance/test_conformance_generated.py` without changing its test count. Run all
  five `conf-tile`s after it: the conformance prototype covered only part of the suite (§5).
- **`tests/test_refused_shape_comments.py`.** `MIN_HEADERS` (LIB 44, `tests/oracle.py` 18 on
  2026-10-14) and `MIN_IN_SCOPE_RAISES` (LIB 33) are zero-headroom floors. Raise each to the
  new count in the same commit, with the dated re-measure note the file already keeps.
  Expected new blocks per parser: H1, H2, S7, S8, and S9 x up to 4.
- **Claim-rot pin** (`formal/conformance/claim_rot.py`, `formal/correspondence_anchor_pin.txt`).
  Bodies that WILL move and are pinned: `src/zanzibar/schema/parser.py::parse_schema_ast`
  (step 7), `tests/oracle.py::parse_schema_ast` (step 7), and
  `tests/oracle.py::parse_schema_ast_unchecked` (steps 4, 9). Possibly
  `src/zanzibar/schema/parser.py::_validate_ast_consistency`, if the builder puts S8 there
  instead (not recommended). `verify.sh lean` goes red until
  `python formal/conformance/claim_rot.py --generate` is run deliberately and the
  `CORRESPONDENCE.md` rows citing those symbols are re-read. Rows to re-read: the query-grid /
  encoder rows (~line 212-213 on 2026-10-14) and the GraphAdmission `keysNonempty` cell,
  which cites `parse_schema_ast`. No anchor RENAME is planned. New `_validate_*` / `_reject_*`
  functions are not anchors unless the builder adds them.
- **Snapshots** (`tests/snapshots/compiled_ruleset/`, built from `tests/fga_schemas/*.fga`):
  unaffected. All 15 fixtures carry `schema 1.1`, declare every restriction type, and use no
  S7 (PROBE `probe_s8_files.py`, static census). So no `ZANZIBAR_UPDATE_SNAPSHOTS`.
- **Lean / `formal/`.** No Lean edit (§4). `formal/SEMANTICS.md` §4.1 is prose (step 10).
- **Fuzz** (`test_p23`): step 8. No algorithm change, so no multi-seed `fuzz.yml` sweep is
  owed. The hypothesis campaign is affected only through the unparser (steps 1-2), which the
  round-trip property (`tests/test_hypothesis.py`, the
  `assert parse_schema_ast(unparse_schema_ast(ast)) == ast` at line 872) exercises.
- **Prose-number lint** (claim_rot 4d3): if the builder writes counts into `CORRESPONDENCE.md`,
  they must be cited or dated.

## 9. Risks and collisions

- **R1, persisted stores (breaking).** `src/zanzibar/connectedstore/schema_io.py::load_schema`
  / `::ensure_schema` re-PARSE the persisted schema text whenever a store opens. A store
  persisted under <= 0.0.4 whose text uses H1 / H2 / S7 / S8 will refuse to open after
  TK137, and a store id cannot be dropped through the public API (the TK124 note). The most
  exposed path is `openfga_json_to_dsl`: before step 2 its output never declared relationless
  types (`type user`), so a store bootstrapped from that text with a `[user]` restriction
  becomes unopenable under S8. The old unparser also emitted `a or b but not c` for a JSON
  `difference` over a `union`, which S7 refuses. Recommendation (REASONED): accept the break
  (pre-1.0, `openfga_json_to_dsl` is not in `PYPI_README.md`) and say it in the CHANGELOG
  with the rewrite. The alternative is a legacy-lenient parse on the persisted-open path
  only. That is a second acceptance mode, so it doubles the parity surface. Flag for the
  coordinator.
- **R2, TK123 (rename `connectedstore` -> `store`, later this session).** Same lines:
  `tests/test_refused_shape_comments.py::FILES` / `::MIN_HEADERS` both name
  `src/zanzibar/connectedstore/store.py`, and TK137 raises `MIN_HEADERS` in that same dict.
  `tests/test_p23_parser_refusal_parity.py` imports `zanzibar.connectedstore`; the new
  module's ConnectedStore test would too. Land one, then rebase the other; never in parallel
  on these files. Whichever lands second re-runs `test_refused_shape_comments` and fixes the
  path.
- **R3, the TK115 round-trip guard loses its JSON witnesses under S8** (§7, PROBE). Without
  the replacement witness test, the guard's "different schema" branch would be an assurance
  step with no live input, so it could fail by passing. The direct-call witness
  (`Union((Computed('owner'),))`, PROBE: refused with "parses to a different schema (added [],
  lost [], changed [('doc', 'viewer')])") keeps it pinned.
- **R4, TK119 / TK132 (Lean, this session).** TK137 edits no Lean, and keeping S5 / S6 means
  the conformance corpus shapes TK119's planned leaf-rule test runs over (`formal/conformance/corpus.py`
  has `r0: [user] and [user]` and `r4: r0 from parent or [user, user:*]`, static census) stay
  legal. The shared file is `formal/correspondence_anchor_pin.txt`: if TK119 regenerates it
  too, the second to land re-runs `claim_rot.py --generate` after rebasing. Never hand-merge
  the pin. If S8 is measured to hit a conformance-corpus schema (§5), that corpus edit
  collides with TK119's corpus use: land TK137's corpus fix first, or coordinate.
- **R5, parity (both parsers move together).** Every step is twinned. `test_p23` fails on ANY
  split, so landing one parser's half alone is red by construction. Good, but it means steps
  3-4, 5-6 and the two halves of 7 land in the same commit.
- **R6, size.** The row says S. The prototype run (§5) shows the TEST blast radius is small
  (8 expected failures in `tests/`). The work is the twinned implementation, the S8 split,
  the unparser, 10+ refused-shape blocks, the new test module with its sabotage, and the
  floor / pin / doc updates. Call it **M**. H1 + H2 + S7 + the unparser alone would be a
  solid S, and could land first as a separate commit if the coordinator wants to split.
