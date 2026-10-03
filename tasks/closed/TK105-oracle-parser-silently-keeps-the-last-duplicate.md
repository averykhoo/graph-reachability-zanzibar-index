---
id: TK105
title: oracle parser silently keeps the last duplicate define; production refuses it
brief: oracle keeps the last duplicate define; production refuses it. Pinned as _ORACLE_COLLAPSES
pri: LATER
size: S
deps: []
related: [TK104, TK109, P23]
parent: P23
labels: [formal]
source: hand
source_hash:
created: 2026-09-25
moved: 2026-10-03e
updated: 2026-10-03e
closed: 2026-10-03e
---

`tests/oracle.py::parse_schema_ast` keeps the LAST of two definitions of the same
`(type, relation)` without complaint. The production parser
(`zanzibar_utils_v1.py::parse_schema_ast`) raises `duplicate relation definition`. Found
2026-09-25 by `TK104`: the `nodup/duplicate-define` sizing probe, encoded through
`formal/conformance/encode.py` (which reads the oracle's parser), reaches zcli with ONE key,
and Lean's decider rightly admits it.

Measured 2026-09-25 (PROBED):

    define viewer: [user]
    define viewer: [user] or editor
    -> {('doc', 'viewer'): OUnion(ODirect(user), OComputed('editor'))}

No product exposure: production refuses the input. The cost is to the independence
contract. The oracle is supposed to parse the DSL itself and refuse what production refuses
(the `TK55` empty-name lock is the precedent), and a conformance corpus with a duplicate
define would silently test a different schema on each side.

Fix: an oracle-side duplicate refusal beside the empty-name lock, plus a regression test in
the `tests/test_reg_empty_relation_name.py` shape. Then move `nodup/duplicate-define` from
`_ORACLE_COLLAPSES` to `_ORACLE_REFUSES` in
`formal/conformance/test_conformance_fragment.py`. That test fails loudly if you forget.

## Traps

- Do not "fix" it by deleting the probe or the `_ORACLE_COLLAPSES` entry. The entry is the pin.

## Read first

- `tests/oracle.py::parse_schema_ast` -- the empty-name lock is where the duplicate refusal goes
- `formal/conformance/test_conformance_fragment.py::_ORACLE_COLLAPSES` -- the pin to flip

## Log

### 2026-10-03c

Now a CHILD of `P23` (user decision 2026-10-03c), done with `P23` and `TK109` as one task. This row's duplicate-define shape is one of `TK109`'s 7; fixing `TK109` fixes it. Map: `docs/promote-next-triage-2026-10-03.md`.

### 2026-10-03e

CLOSED with P23 (one task, user decision 2026-10-03c). tests/oracle.py::parse_schema_ast_unchecked now refuses a duplicate define (REFUSED SHAPE (TK105) block), pinned by tests/test_p23_parser_refusal_parity.py::test_oracle_parser_refuses_independently[TK109/duplicate-relation (TK105)]; sweep row O4 reddened exactly that case. nodup/duplicate-define moved from _ORACLE_COLLAPSES (now empty) to _ORACLE_REFUSES in formal/conformance/test_conformance_fragment.py. Map: docs/p23-parser-refusal-parity-2026-10-03.md.
