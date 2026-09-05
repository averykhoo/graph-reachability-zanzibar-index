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
source: hand
source_hash:
created: 2026-09-05b
moved: 2026-09-05b
updated: 2026-09-05b
closed:
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
