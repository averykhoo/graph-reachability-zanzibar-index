# TK115 -- the OpenFGA JSON front end must render the schema it was given: probe and decision (2026-10-04)

**FROZEN 2026-10-04, at `TK115`'s close -- provenance, not a living document.** Status lines
below are as-of-then and may now be false; live state: `HANDOFF.md` + the session
ledger (`python scripts/task.py board`). Corrections are appended dated at the top, never
edited into the body.

Row: `python scripts/task.py show TK115`. Filed from `docs/p10-scope-audit-2026-09-27.md`
sec 5 H5; promoted by `docs/promote-next-triage-2026-10-03.md` sec 4.

## 1. What was measured (PROBED first-hand 2026-10-04, this session)

Probe: `.scratch/tk115/probe.py` (gitignored; this section is the tracked record). Each model
went through `zanzibar_utils_v1.py::parse_openfga_json`, then `unparse_schema_ast`, then
`parse_schema_ast` on the rendered DSL. Tree: `8045eef` (after `P23` and `TK114`).

| id | input | verdict before the fix | rendered DSL / note |
|---|---|---|---|
| V1 | relation name `x: [user]\n    define secret` | REFUSED (by `P23`'s `_validate_declared_name`) | -- |
| V2 | `{"type": "user", "wildcard": false}` | ACCEPTED, round-trip equal | `define viewer: [user:*]`, a public grant |
| V3 | two `"viewer"` keys in one `relations` object | ACCEPTED, last wins, round-trip equal | `define viewer: owner` |
| V4 | type name `doc\ntype folder2` | REFUSED (by `P23`) | -- |
| V5 | control, a well-formed model | ACCEPTED, round-trip equal | `define viewer: [user]` |
| V9 | bare restriction type `user]\n    define secret: [user` | ACCEPTED, **round-trip NOT equal** | renders a second relation `secret` |
| V10 | `"wildcard": {}` (canonical OpenFGA) | ACCEPTED | `[user:*]`, correct |
| V11 | `"wildcard": null` | ACCEPTED | `[user]`, correct |
| V12 | `"wildcard": {"enabled": false}` | ACCEPTED | `[user:*]`, a public grant |
| V13 | `"wildcard": 0` | ACCEPTED | `[user:*]`, a public grant |
| V14 | bare restriction type `us er` | ACCEPTED; the DSL parser REFUSES the rendering (`invalid subject type in restriction`) | the two front ends disagree |
| V15 | `{"type": "user", "relation": ""}` | ACCEPTED | `[user]`, see sec 3 |
| V16 | top-level `"schema_version"` twice, last `1.0` | REFUSED (version check sees the last value) | -- |
| V17 | top-level `"schema_version"` twice, last `1.1` | ACCEPTED | a `1.0` key was silently discarded |

**Findings (first-hand):**

- `P23` closed V1 and V4. It did NOT close the name-injection class. A bare restriction type
  is not a declared name, and the ASK-1 consistency check deliberately does not check bare
  restriction types. So V9 still injects a relation and V14 still splits the front ends.
- V2, V12 and V13 are the same fail-open: the old test was "the key is present and its value
  is not `null`".
- V3 and V17 round-trip EQUAL. The skeptic's 2026-10-03c point stands: a round-trip check
  alone misses them, because `json.loads` drops the evidence before the AST exists.

## 2. The decision (taken by the session under `CLAUDE.md` "Who decides", 2026-10-04)

Three refusals in `zanzibar_utils_v1.py`. Each is a `_validate_*` / `_reject_*` function with
a REFUSED SHAPE / WHY / INSTEAD block.

1. **`_reject_duplicate_json_keys`**: the `object_pairs_hook` for `json.loads`. It refuses a
   repeated key at ANY depth (closes V3 and V17). It can only see JSON TEXT. A caller that
   passes a `dict` has already lost its duplicates, and the docstring says so.
2. **`_validate_json_wildcard`**: `wildcard` must be absent, `null` or exactly `{}`.
   OpenFGA's `Wildcard` message has no fields, so `{}` is its only canonical JSON. Any other
   value is refused rather than guessed at (closes V2, V12, V13).
3. **`_validate_json_round_trip`**: the last step of `parse_openfga_json`. It refuses unless
   `parse_schema_ast(unparse_schema_ast(ast)) == ast`, and it also refuses when the rendering
   does not parse at all. This closes the class for any name the field checks miss (V9,
   V14), including a restriction type containing a comma. That case keeps the same keys but
   changes the expression, so a keys-only comparison would pass it.

Rejected alternative: validating every restriction type against the write charset. It would
close V9 and V14, but only for the names someone thought to list. The round trip is the
property `openfga_json_to_dsl` exists to provide, so it is the check that closes the class.

Not a backend divergence: all three evaluators read the same AST/DSL. This is a fail-open
UPSTREAM of them. The oracle has no JSON front end, so there is no twin to keep in step.

## 3. Out of scope, recorded so nobody re-probes it

- V15, `"relation": ""` -> `[user]`. Protobuf JSON treats an empty string as an unset field,
  so a bare restriction is the canonical reading. Not refused.
- A non-`dict` rewrite node or a missing `relation` key already fails loudly
  (`ValueError` / `KeyError`). It is not a silent acceptance.

## 4. Pins and the mutation sweep (RUN first-hand 2026-10-04)

Pins: `tests/test_openfga_json.py`, the `TK115` block at the bottom of the module:
`test_rejects_wildcard_that_is_not_an_empty_object`,
`test_wildcard_empty_object_and_null_keep_their_canonical_meaning`,
`test_rejects_duplicate_json_keys_at_any_depth`,
`test_rejects_model_whose_dsl_rendering_is_a_different_schema`,
`test_rejects_newline_in_a_declared_name`. That last one pins V1 and V4, which `P23` refused
but had not pinned with a newline.

The sweep ran with `.scratch/tk115/sweep.py`. Every anchor was asserted at count 1, and both
files were restored and sha256-checked. The sweep ran this module plus
`tests/test_refused_shape_comments.py`; the baseline was `37 passed`. The literal per-mutation
tails are in the test module's docstring. Summary:

| mutation | verdict |
|---|---|
| M0 control: a pin claims `{}` is refused | RED, exactly that param -- attribution works |
| M1 hook dropped; M2 hook keeps the first value | RED, 3 failed each |
| M3 pre-TK115 wildcard line; M4 any dict; M5 bools only; M6 `null` read as a star | RED, 6 / 1 / 4 / 1 failed |
| M7 no round trip; M8 key sets only; M9 unparseable accepted | RED, 3 / 1 / 1 failed |
| M10 `lost` ignored | INERT, explained below |

**M10 is INERT by construction (REASONED, not probed).** Declared names are inside the
charset (`P23`), so every `type T` and `define R:` line re-parses to its own name. A key can
leave the re-parse in only two ways. An injected line can re-home the relations after it
under another type, which also ADDS keys. Or it can create a duplicate, which is a parse
error. Either way `added` or the parse error decides the refusal, and `lost` is only
diagnostic text in the message.

## 5. What landed

- `zanzibar_utils_v1.py::_reject_duplicate_json_keys`, `::_validate_json_wildcard` and
  `::_validate_json_round_trip`. `parse_openfga_json` now loads JSON text with the hook and
  runs the round trip last. `_json_restrictions` reads `wildcard` through the validator.
- `tests/test_refused_shape_comments.py::MIN_HEADERS` for the product rose from 34 to 37,
  re-measured with `grep -c "REFUSED SHAPE"` on 2026-10-04.
- No oracle change: the oracle has no JSON front end.
