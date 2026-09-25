---
id: TK105
title: oracle parser silently keeps the last duplicate define; production refuses it
brief: oracle keeps the last duplicate define; production refuses it. Pinned as _ORACLE_COLLAPSES
pri: LATER
size: S
deps: []
related: [TK104]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-25
moved: 2026-09-25
updated: 2026-09-25
closed:
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
