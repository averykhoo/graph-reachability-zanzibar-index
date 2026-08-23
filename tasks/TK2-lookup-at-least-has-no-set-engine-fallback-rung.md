---
id: TK2
title: lookup at_least has no set-engine fallback rung: ZT-P1-8b closed only the raise half
pri: LATER
size: M
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed:
---

`check(..., at_least=N)` falls back to the set engine when the index is behind; `lookup`/`lookup_reverse` cannot, so they accept the token and raise `LookupNotFresh` (`connectedstore/store.py:42`, `::ConnectedStore._require_index_freshness`). `ZT-P1-8b` closed the accept-and-raise half and is CLOSED as filed — but the decision log names the remaining rung in three explicit steps: unify the lookup result contract on keys/markers → add the same `at_least` plumbing `check` has → extend the lookup-oracle gate with a lagging-index leg. Nobody owns those steps.

This is a **closed id under-covering its filed scope**, which is the shape worth having an id for: the ledger says `ZT-P1-8b` closed, and it did, but the reader who wants "is `at_least` done?" gets the wrong answer.

## Traps

⚠ **The decision log calls the last step "mostly test-writing", and that is the expensive half.** The lagging-index leg belongs in [`tests/test_lookup_oracle.py`](tests/test_lookup_oracle.py), which `CLAUDE.md` names as the lookup-surface oracle gate; any divergence it finds gets a POSITIVE PIN, never an xfail (`MAX_TESTS_XFAILED` is budgeted in `formal/verify.sh` and is currently 0).

⚠ **`_fresh_enough(None) -> True` is the DESIGN, not a fail-open default** — `store.py:328-336` says so in a comment. Do not "harden" it while plumbing the token.

## Read first

- [`docs/architecture/decision-log.md`](docs/architecture/decision-log.md)`:166-189` — the decision and, at `:187-189`, the three-step shape of the future work (LIVING)
- `connectedstore/store.py::ConnectedStore._require_index_freshness` and `::ConnectedStore.check` — the rung that exists beside the rung that does not
- `tests/test_lookup_oracle.py` — where the lagging-index leg goes
- `python task.py show ZT-P1-8b` — the closed record this row is the residue of

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-2 (`NG-3`, tier 1, sweep-n only); CONFIRMED OPEN by COVERAGE.md §C3 and re-confirmed here — connectedstore/store.py:42 still defines `LookupNotFresh` for the surfaces that cannot fall back.
