---
id: TK94
title: no conformance schema pairs a derived relation with a userset subject (0 of 26)
brief: censused 2026-09-21: the class TK92 needed exists nowhere in SCHEMAS; enum cost is combinatorial
pri: NOW
size: M
deps: []
related: [TK92]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-21
moved: 2026-09-21b
updated: 2026-09-21b
closed:
---

## What it is

**MEASURED 2026-09-21 (census, first-hand, while closing `TK92`).** Of the 26 entries in
`formal/conformance/corpus.py::SCHEMAS`, **zero** pair a DERIVED relation with a userset
subject. Four use a userset subject at all — `group_userset`, `wildcard_group_member`,
`taint_union_userset_arm`, `residue_rich` — and in every one the referenced
`group.member` is a plain-direct relation. The intersection with each schema's compiled
`plans` keys is empty across all 26.

So `type doc: define viewer: [user, group#member]` where `group.member` is itself boolean
— ordinary Zanzibar, and accepted by `parse_openfga_schema` — is an input class the whole
conformance surface has never run on. Not just the bulk identity gate: the enumerated,
generated and remove arms all draw from this corpus.

`TK92` closed one hole in it from the `tests/` side
([`tests/test_reg_tk92_bulk_rel_term.py`](../tests/test_reg_tk92_bulk_rel_term.py) pins
`bulk == bulk=False` on ONE such schema) and deliberately did not widen scope.

## Why it is worth a row

The class is not a curiosity — it is the only way a node lands in a derived relation's
PUBLIC family at LOAD time rather than at backfill time, which is what made `TK92`'s
refutation possible at all. Anything keyed off "the public family is written only by the
processor" is unexamined against it.

## First action

Add ONE `SCHEMAS` entry whose userset subject names a derived relation, then measure —
per module — what newly runs and what newly reddens. **Measure before predicting**: the
`TK92` sweep found a mutation (`M3`) that was reached and masked for a reason nobody
would have guessed from reading.

## (!) Traps

- **(!) A new corpus entry is not free and its cost is not uniform.** `SCHEMAS` is
  parametrized over by many modules at once; `formal/conformance/test_conformance_enum.py`
  enumerates every store up to a bound, so one schema there is a combinatorial cost, not
  an additive one. Size the entry against the enum bound before adding it.
- **(!) `MIN_CONF_ALL` / `MIN_TESTS_ALL` have ZERO headroom.** Adding tests is free;
  the floors move up and must be re-measured, never estimated
  (`pytest <dir> -q --collect-only`).
- **(!) Do not assume the new arms are vacuous because they pass.** That is the whole
  lesson of the four modules that measured the `[rel]` term inert for a reason that was
  about corpus content, not about the code. Say which branch each new arm reaches.

## Read first

- [`docs/tk92-bulk-rel-term-2026-09-21.md`](../docs/tk92-bulk-rel-term-2026-09-21.md)
  §2 (the census and its literal output) and §7 (this item's provenance).
- `tests/test_reg_tk92_bulk_rel_term.py` — the one schema of this class that exists, and
  the fixture-guard shape worth copying.
- `formal/conformance/corpus.py::SCHEMAS` — the corpus, and `::GRAPH_FRAGMENT` for which
  entries the graph arms take.

## Log

### 2026-09-21b

Promoted NEXT -> NOW at the 2026-09-21b write-back (closing TK93 left the board with no NOW). Ranked above TK71 and the new TK95 on the primary consideration: this is a whole SCHEMA CLASS that no generated or enumerated conformance arm can reach, i.e. a hole in the equivalence net itself, where TK71 is an assertion-strength question and TK95 is an outcome-equivalence pin on a path already known green at four hash seeds. The M sizing and the combinatorial cost in test_conformance_enum.py are the reason it is ranked first rather than deferred again -- it has been the cheapest-to-defer item twice now.
