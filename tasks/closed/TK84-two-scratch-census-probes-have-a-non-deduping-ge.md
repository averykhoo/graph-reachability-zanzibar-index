---
id: TK84
title: two scratch census probes have a non-deduping generator, so their numbers are contaminated
brief: habitat_census.py:91 / habitat_fuzz.py double-add; add_tuple is ref-counted, so 34% of ops ran inflated
pri: LATER
size: S
deps: []
related: [TK74]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-18c
moved: 2026-10-04g
updated: 2026-10-04g
closed: 2026-10-04g
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-09-18c

Found under the section 9.10 sweep; write-up is docs/tk74-staleness-net-2026-09-18.md sections 10.4 and 10.8.

THE BUG. WildcardIndex.add_tuple is REF-COUNTED. Reproduced first-hand:
    add1 None / add2 None / rm None / still present? True
add(t); add(t); remove(t) leaves t PRESENT. The sanctioned path does NOT behave this way: connectedstore/source.py::TupleSource.add (:470-473) is documented "Idempotent on duplicates (raw tuples are a set): no state change, no log row", enforced via _add_tuple_direct (:489).

WHO HAS IT. .scratch/tk74c-habitat/habitat_census.py::sweep (:91) and .scratch/tk74c-habitat/habitat_fuzz.py::sweep both do t = rng.choice(pool); op = add with no live-set exclusion. .scratch/tk74c-gcroute/probe_gcroute.py::witness_of (:124) DOES dedupe (cands = [r for r in pool if r not in present]) and is clean.

WHAT IT COST. On the census own traffic: 376 double-adds, 34.4% of ops on ref-count-inflated state, 18.6% on observably divergent state, 87 of 198 seed runs ended oracle-DIRTY. And it CHANGED A VERDICT: section 9.4 SETTLE_RAN was 0 at N=2385 on buggy traffic, 1 at N=7155 buggy, and 5 at N=7156 deduped.

THE ITEM. Either fix the generator in both probes and re-run anything cited from them, or delete the probes so no future session harvests a contaminated number. Note .scratch/ is gitignored, so option two loses the code -- section 10.8 carries the numbers that matter.

THE DURABLE RULE, worth promoting if it recurs: a harness that writes DIRECTLY to a backend must reproduce that backend admission semantics, or its oracle comparison means nothing. Prefer driving TupleSource/ConnectedStore, which dedupes for you.

TRAP: do not cite SETTLE_RAN = 0 from habitat_census.py or habitat_fuzz.py again.

### 2026-10-04g

CLOSED 2026-10-04g via the row own OPTION 2 (delete the probes): .scratch/tk74c-habitat/ and .scratch/tk74c-gcroute/ no longer exist and no habitat_* file exists anywhere outside .lake (PROBED 2026-10-04g; the only tracked hit for "habitat" is the closed row TK16 "inhabitation"). The numbers that matter are carried by docs/tk74-staleness-net-2026-09-18.md sec 10.8 and the 10.9 table (SETTLE_RAN 0 -> 1 -> 5 deduped; "must not be cited again"). CAVEAT for readers of that doc: two body sites in its earlier sections still quote the contaminated census figures inline (2385-cascade census, 16,497) and only its dated header and sec 10.8 correct them -- the doc is a FROZEN closed-row doc, so the correction stays where it is. The durable rule (a harness writing DIRECTLY to a backend must reproduce its admission semantics; prefer driving TupleSource/ConnectedStore) stays recorded on this row.
