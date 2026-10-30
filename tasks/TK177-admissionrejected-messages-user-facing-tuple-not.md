---
id: TK177
title: AdmissionRejected messages: user-facing tuple notation and an INSTEAD for the cycle refusal
brief: 0.1.1 trial F21 + F17: AdmissionRejected quotes doc:1#viewer@robot:r#...; cycle refusal has no INSTEAD
pri: LATER
size: S
deps: []
related: [TK176]
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-10-30b
moved: 2026-10-30b
updated: 2026-10-30b
closed:
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-10-30b

Source docs/pypi-trial-0.1.1-2026-10-30.md F21 (and the F17 message part), AGENT, not re-run. add_tuple("robot:r","viewer","doc:1") is refused as "tuple doc:1#viewer@robot:r#..." -- internal Zanzibar notation the user never wrote; the self-parent cycle refusal ("folder:f#... parent folder:f would create a cycle in the userset membership topology") names no rewrite. Next action: quote the tuple as the user wrote it (user, relation, object) in AdmissionRejected and add what to do for the cycle case. Cosmetic: no wrong answer.
