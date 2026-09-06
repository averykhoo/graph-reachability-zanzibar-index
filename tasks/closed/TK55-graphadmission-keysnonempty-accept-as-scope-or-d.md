---
id: TK55
title: GraphAdmission.keysNonempty: accept as scope or discharge (user call)
brief: second admission field from P3; Python-enforced, not WF-derivable; accepted as scope pending user sign-off
pri: LATER
size: S
deps: []
related: [P5]
parent:
labels: [formal]
source: board
source_hash: 351c451d52dc
created: 2026-09-05b
moved: 2026-09-06b
updated: 2026-09-06b
closed: 2026-09-06b
---

`GraphAdmission` gained TWO fields when `P3` landed (`FullScope.lean:172 noLeafSubjects`,
`:188 keysNonempty`) where the scope doc sanctioned ONE. `keysNonempty : S.keys.all (fun k
=> k.2 != "") = true` narrows nine byte-identical pinned statements to schemas whose declared
relation names are non-empty. Accepted as SCOPE by the 2026-09-05b session on two grounds:
Python enforces it (`zanzibar_utils_v1.py::_IDENTIFIER_RE` `{1,256}` at `:31`, applied by
`validate_write_identifiers` `:133`), and it is NOT derivable from `WF`
(`LeafRules.lean:734::wf_does_not_give_keysNonempty`). **User call owed:** accept as scope
(then record it in `formal/FINAL_REVIEW.md`'s scope list and close this), or discharge it —
either strengthen `WF` to carry it, or prove the leaf split never mints an empty key.
Evidence: `PROOF_STATUS.md` `2026-09-05b` §9.4.

## Log

### 2026-09-06b

source: hand -> board by HAND EDIT 2026-09-06b, the route docs/tasktool-spec.md sec 3.1 prescribes for a wrong source value ('a hand edit plus a Log entry saying so'). Reason: this task was filed by hand AND given a board row in the same session under the dual-update contract, so sync reconciles it against the board (it reported BODY drift '(never reconciled)') while ack REFUSED it as hand-sourced (rc 2, task.py::op_ack:3175) -- a permanent red with no verb to clear it (trial friction A7 item 1). The tool's own remedy (delete the file, new --id --source board) would delete a committed task file, which sec 4 forbids, and would reset created. Body left as-is: it already matches the board cell.

First reconciliation against the board row filed 2026-09-05b: cell and task body agree (keysNonempty: accept as scope or discharge, USER CALL; FullScope.lean:172/:188; wf_does_not_give_keysNonempty; PROOF_STATUS 2026-09-05b sec 9.4).

Fix parser + accept as scope, user-decided. Both parsers (zanzibar_utils_v1.py and the independent tests/oracle.py) now refuse an empty declared relation name -- 'define : [user]' used to compile to Filter(relation='') and the graph answered False where oracle+set said True via 'define : viewer'. Pinned by tests/test_reg_empty_relation_name.py (15 cases; parser check disabled -> 8 failed, 7 passed). keysNonempty accepted as scope with a now-true justification: FullScope.lean docstring, FINAL_REVIEW s3.1 item 3, spec-deviations 2026-09-06. Residual charset asymmetry filed as P23.
