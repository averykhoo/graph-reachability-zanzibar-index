---
id: TK166
title: a freshness token from another store is accepted silently (and its refusal advice misleads)
brief: 0.1.0: refuse a token issued by another store on every tokened read; lead the message with the cause
pri: NEXT
size: S
deps: []
related: [TK151]
parent:
labels: []
source: docs/tk151-repros-2026-10-20/README.md
source_hash:
created: 2026-10-20b
moved: 2026-10-23b
updated: 2026-10-23b
closed: 2026-10-23b
---

B4: at_least= from another store passes whenever it is at or below this store cursor, on check, lookup, lookup_reverse and expand; the answer is correct for the store asked, but the caller s read-your-writes demand is silently meaningless. Agent fix: one PK lookup of TupleLog.store_id for the token, refuse a foreign one. B5: when a foreign token IS refused, StaleRead / LookupNotFresh open with refresh/catch_up-and-retry advice that cannot help; the real cause is only in the last sentence. Adding a refusal is a behaviour change: decide before 0.1.0.

Repro and first-hand output: `docs/tk151-repros-2026-10-20/README.md` section B4+B5 (`docs/tk151-repros-2026-10-20/B4.py`). Found by the TK151 docs pass 2026-10-20b; the user docs describe the CURRENT behaviour as a caveat, so fixing this means updating the pages that section lists.

## Read first

- `docs/tk151-repros-2026-10-20/README.md`

## Log

### 2026-10-20b

0.1.0 ITEM (user, 2026-10-20b, in chat). Plan (model): refuse a foreign token on every tokened read (check, lookup, lookup_reverse, expand) with one TupleLog primary-key lookup of the token owner, and lead the refusal message with the cause (no refresh/catch_up/retry advice); consider ForeignToken(StaleRead) so except StaleRead still catches it. It turns a silent accept into an error, which is why it lands before the freeze. Update the userdocs pages listed in docs/tk151-repros-2026-10-20/README.md B4 and B5.

### 2026-10-23b

LANDED 2026-10-23b (ultracode wf_7da61747-5e0, implement + adversarial review): ForeignToken(StaleRead) in src/zanzibar/store/source.py, raised by refuse_foreign_token (one TupleLog PK lookup) on every tokened read (Store.check, lookup, lookup_reverse, expand, TupleSource.check), above or below the cursor; message leads with the cause, no retry advice; lookups raise ForeignToken not LookupNotFresh (decision D1). Review found token_diagnosis bypass and fixed it. tests/test_tk166_foreign_token.py; orchestrator sabotage first-hand (ownership check -> if True): 34 failed, 4 passed. Plan: docs/tk166-foreign-token-2026-10-23.md. userdocs updated. CHANGELOG behaviour change entry.
