# P23 (+ TK109, TK105) -- parser refusal parity: the census and the contract (2026-10-03e)

**FROZEN 2026-10-03e, at `P23`'s close -- provenance, not a living document.** Status lines
below are as-of-then and may now be false; live state: `HANDOFF.md` + the session
ledger (`python scripts/task.py board`). Corrections are appended dated at the top, never
edited into the body.

Row: `python scripts/task.py show P23` (children `TK109`, `TK105`, all closed 2026-10-03e).

**CORRECTION 2026-10-03e (same session, found by the gate).** `conf-tile:2/5` went red on
`formal/conformance/test_grid_independence.py::test_the_two_parsers_are_really_different_code`.
That test proved the oracle is not an alias of production by citing a LIVE disagreement: the
duplicate `define`, which `TK105` removed on purpose. The test now shows the difference in two
other ways. The same input parses to AST classes from different modules, and the same refusal
(`define *: [user]`) comes with differently worded messages. Sabotage: making the oracle's
message identical to production's turned it red (`1 failed, 3 passed`), and the file was
restored with its sha256 checked. Sec 3 missed this consumer of the old disagreement.

## 1. What was measured (PROBED first-hand 2026-10-03e, this session)

**1a. The row's witness, re-probed.** The declared relation name in
`define <n>: viewer but not blocked` (types `user`, `doc`; `blocked`, `viewer` both `[user]`)
was parsed by both checked parsers, `zanzibar_utils_v1.py::parse_schema_ast` and
`tests/oracle.py::parse_schema_ast`:

```
'*'            prod=accept oracle=accept
'a#b'          prod=accept oracle=accept
'cafe' (e-acute) prod=accept oracle=accept
'x'*257        prod=accept oracle=accept
'a\tb'         prod=accept oracle=accept
'can view'     prod=accept oracle=accept
'a.b'          prod=REFUSE oracle=accept
```

The shipped consequence, with `n = '*'`: `ConnectedStore(session, 'cs', schema=S)` (SQLite,
sync) constructs, and then a VALID write `add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')`
raises `AdmissionRejected invalid relation '*': must match [A-Za-z0-9_./@+=-] (1-256 chars)`.
So the store accepts a schema and then refuses writes it should take. This matches the
2026-10-03c triage (`docs/promote-next-triage-2026-10-03.md` sec 4). No wrong answer was seen.

**1b. A differential fuzz of the two checked parsers.** Seeds: the 15
`tests/fga_schemas/*.fga` files, all accepted by both parsers. Each trial applies 1-3 random
character edits (insert, delete or replace) to one seed. The edit alphabet is
`[]#:*,.()`, space, tab, newline, `-_/@+=`, `x`, `e-acute`, and the keywords `or`, `and`,
`but not`, `from`, `define`, `type`, `relations`, `model`. The verdict is accept or refuse. A
class is the refusing side's message, with quoted spans replaced by `Q`. Seed 0, 20,000 trials:

```
2169 prod-only-refuses | unrecognized schema line: Q
 405 prod-only-refuses | invalid subject type in restriction Q
 108 prod-only-refuses | malformed type declaration: Q
  13 prod-only-refuses | empty entry in type-restriction list Q
  11 prod-only-refuses | relation Q: Q is reserved for compiled leaf predicates ...
   4 prod-only-refuses | malformed relation definition (missing colon): Q
   4 prod-only-refuses | empty type-restriction list in Q
   1 prod-only-refuses | invalid userset relation in restriction Q
   1 prod-only-refuses | doc#access: tupleset ... is undeclared   (the oracle skipped `define\taccess`)
   3 oracle-only-refuses | undeclared relation / declared on no type of tupleset
```

Seed 1 (20,000 trials) found the same classes, plus `duplicate relation definition` (1).

**How each class arises (READ, from the parser sources):**

- **unrecognised line** (and `define ` with no name or colon). `_parse_schema_ast_unchecked`
  refuses any line whose head is not `model`/`schema`/`relations`/`type`/`define`. The oracle
  skips such lines without a word.
- **oracle-only-refuses.** The product picks the line head with `line.split()`, so
  `define\taccess` and `type\tfolder` count as a define and a type. The oracle tests
  `line.startswith('define ')` and `'type '`, so it skips those lines and then refuses the
  references to them as dangling. That makes the oracle stricter by accident.
- **invalid subject type / userset relation in a restriction.** `parse_relation_rule` applies
  `is_valid_identifier` to every restriction entry. `tests/oracle.py::_parse_restrictions`
  applies no charset at all, so `[use r]`, `[folder:)]` and `[user: *]` parse as type names.
- **malformed type declaration.** The product needs exactly two words. The oracle takes the
  rest of the line, so `type use r` declares a type named `use r`.
- **empty entry / empty list.** The product refuses `[]` and `[user,,x]`. The oracle drops
  empty entries (`continue`).
- **missing colon.** Both parsers refuse `define x` with no colon, the oracle via `empty
  definition`. Only the bare `define` line splits them, and that is the unrecognised-line case.
- **`.` in a declared name.** Not locked in the oracle.
- **duplicate type / relation** (`TK105`). The oracle merges or keeps the last one.

**1c. Neither parser has a charset on declared names (`P23` proper).** Not even on TYPE names:
the seed-1 samples include `type re[o` and `type d#oc`, which both parsers accept. A write on
such a type is refused at admission (`validate_write_identifiers` checks `object_type`), so a
type like that can never hold a tuple.

## 2. The contract (decided by the session 2026-10-03e; CLAUDE.md "Who decides")

**Both checked parsers accept exactly the same schema texts.** This is pinned as a property:
the fuzz in sec 1b, made permanent and seeded, asserts that the verdicts agree on every
trial. It does not compare messages.

Declared names:

- a **type** name must match the write identifier charset `[A-Za-z0-9_./@+=-]{1,256}`, which
  is `zanzibar_utils_v1.py::IDENTIFIER_CHARSET`;
- a **relation** name must match that charset and also contain no `.` (the leaf lock).

Why this contract: a declared name outside the write charset names a type or relation that
no write can ever reach. It is still referenceable through a computed or TTU arm, and that is
where the backends split. The `TK55` empty-name precedent produced a wrong answer, and `P23`'s
`*` produces an admission refusal. Matching the charset exactly makes "declared" imply
"writable". A narrower rule would refuse schemas that serve fine today, and a wider one
leaves this class open.

- The oracle carries its OWN copy of the regex, because its independence contract says it
  imports nothing from the backends.
- The JSON front end (`parse_openfga_json`) gets the same declared-name rule. That covers the
  `TK115` V8 empty-name case and the V6 `can view` case. `TK115`'s other holes (duplicate
  keys, `"wildcard": false`, the round-trip check) stay on `TK115`.
- Reserved keywords (`or`, `from` ...) as declared names are NOT refused here. They pass the
  charset, and the fuzz has not shown them splitting the parsers. If a later sweep shows a
  split, it gets its own row.

## 3. Plan

1. Product: add `_validate_declared_name(kind, name)` and call it in the DSL `type`/`define`
   branches and in the JSON front end (`REFUSED SHAPE (P23)` block).
2. Oracle: pick the line head with `split()`, refuse unrecognised lines, malformed `type`,
   duplicate type and relation, `.` in a declared name, and the declared-name charset. Refuse
   the empty restriction list, the empty entry and the restriction-entry charset. Each check
   gets an independent twin in a `_validate_*` function, with a REFUSED SHAPE block.
   (CORRECTED the same session, sec 4: four of these twins were subsumed and were deleted.)
3. Pins: a new `tests/test_p23_parser_refusal_parity.py` holds (a) a named both-refuse case
   for every class in sec 1, (b) accept controls, (c) the seeded differential fuzz, and (d) the
   end-to-end `ConnectedStore` witness from 1a. In
   `formal/conformance/test_conformance_fragment.py`, move `nodup/duplicate-define` from
   `_ORACLE_COLLAPSES` to `_ORACLE_REFUSES`, and expect `wf/dotted-relation-name` to join it.
   Bump `tests/test_refused_shape_comments.py::MIN_HEADERS`.
4. Sabotage each parser's new checks one at a time, then sweep the module with mutations.

## 4. What landed, and the sweep (PROBED first-hand 2026-10-03e)

**Correction to sec 3 step 2, made the same session.** The first sweep found four oracle
twins INERT: the empty list, the empty entry, the userset-relation charset, and the missing
colon. Each was subsumed by another check, so none could go red on its own:

- an empty entry has type `''`, which the restriction-type charset refuses;
- a bad userset relation names `T#<bad>`, which no declared name can be, so
  `tests/oracle.py::_validate_consistency` refuses it;
- with no colon, either the name swallows the rest of the line (the charset refuses it) or the
  body is empty (`_Parser.parse` refuses it).

They were deleted rather than kept as untestable code. The empty-entry fix is now simply "stop
skipping empty entries", and the sweep row O8 below pins it.

**Scope decision.** The parity property is on the CHECKED parse. `parse_schema_ast_unchecked`
on the oracle side stays permissive on purpose, because the conformance encoder must be able
to send Lean a schema Python refuses. The new oracle refusals are syntax-level, like `TK55`'s
empty-name lock, so they live in the unchecked parse too, as in production. As a result, two
`GraphAdmission` probes can no longer be encoded and joined
`formal/conformance/test_conformance_fragment.py::_ORACLE_REFUSES`: `nodup/duplicate-define`
(which used to sit in `_ORACLE_COLLAPSES`, now empty) and `wf/dotted-relation-name`.

**Final sweep** (`.scratch/p23/sweep.py`). Each row removes one check, runs
`tests/test_p23_parser_refusal_parity.py` plus `tests/test_reg_empty_relation_name.py`, and
restores the file, checking its sha256. The baseline was green. `fuzz` says whether the
differential-fuzz test was among the reds.

```
M0-control: product refuses EVERY declared name             | RED | 21 failed | fuzz=yes
P: product _validate_declared_name no-op                     | RED | 17 failed | fuzz=yes
P-dsl-type: DSL type call removed                            | RED |  4 failed | fuzz=yes
P-dsl-rel: DSL relation call removed                         | RED |  8 failed | fuzz=yes
P-json-type: JSON type call removed                          | RED |  2 failed | fuzz=no
P-json-rel: JSON relation call removed                       | RED |  4 failed | fuzz=no
O1: oracle _validate_declared_name no-op                     | RED | 10 failed | fuzz=yes
O2: oracle type-name call removed                            | RED |  4 failed | fuzz=yes
O3: oracle duplicate type                                    | RED |  1 failed | fuzz=no
O4: oracle duplicate relation                                | RED |  1 failed | fuzz=no
O5: oracle dot lock on declared name                         | RED |  2 failed | fuzz=yes
O6: oracle malformed type line                               | RED |  2 failed | fuzz=yes
O7: oracle unrecognised line skipped                         | RED |  2 failed | fuzz=yes
O8: oracle skips empty restriction entries again (pre-fix)   | RED |  4 failed | fuzz=yes
O13: oracle line head by single space (old startswith)       | RED |  2 failed | fuzz=yes
O14: oracle `...` exemption removed from the S-5 check       | RED |  1 failed | fuzz=no
```

The M0 control's reds were exactly the accept controls, the end-to-end tests and the `TK55`
siblings, so the harness attributes correctly. **What the fuzz cannot see:** duplicates (O3,
O4), because a character edit cannot copy a line, and `#...` (O14), because the alphabet does
not produce it. The named cases are the only pin for those three. The JSON front end has no
oracle twin, so the fuzz never covers it.
