---
id: TK103
title: audited Lean names vs headline dependency closure: which audited theorems does no headline rest on?
brief: P14 probe measures headline closures; intersect with audited_theorems.txt so the load-bearing split is stated
pri: LATER
size: S
deps: []
related: [P14]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-23c
moved: 2026-09-23c
updated: 2026-09-23c
closed:
---

Goal step 3 (`docs/goal-census-2026-09-22.md`): **say which audited Lean names the headline theorems actually rest on.** `formal/audited_theorems.txt` pins every audited name, but nothing in the repo says which of them are in a headline theorem's dependency closure and which only prove the staged W3a/W3d ladder. A reader can't tell "proved and load-bearing for the shipped claim" apart from "proved, historical".

Measured starting point (`P14`, 2026-09-23c): `formal/probes/p14_collapse_closure_2026-09-23.lean` computes the transitive `ConstantInfo.getUsedConstantsAsSet` closure of the eight headline theorems (`2113`-`2363` project constants each, with positive and negative controls). On the collapse family alone, every narrow and W3a/W3d lemma is OUT, and `ReconcileCorrect.lean::reachedByW3a_reach_collapse_root_d` has zero consumers outside `Audit.lean`. The generalisation: take the union closure and intersect it with `audited_theorems.txt`, then report or pin the split. Map: `docs/p14-reach-collapse-absorbed-2026-09-23.md` sec 6.

## Log
