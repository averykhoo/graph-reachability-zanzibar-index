# TK179 -- strict public argument types: validators + a census test (2026-10-30)

> **ACTIVE-PLAN** (`docs/README.md` sec 3). Filed 2026-10-30b after the 0.1.1 install trial's
> F19 (`Store(sync=None)` silently async, fixed as `TK176`). Corrections go at the top, dated.
> FROZEN when `TK179` closes. Release gate: `TK178` (0.1.2) depends on `TK177`, `TK179`,
> `TK180`, `TK181` (user, 2026-10-30b: "improve testing before releasing 0.1.2").

## 2026-10-30b -- first census measurement (first-hand RUN, `.scratch/tk179/measure.py`, PYTHONPATH=src)

84 (callable, parameter) pairs over `Store` (init, adopt, add/remove/check in both call forms,
lookup, lookup_reverse, expand, catch_up), `SetEngine` (init, check/add/remove), and
`parse_openfga_schema`, `build_index`, `rebuild_index`, `save_schema`, `open_set_engine`,
`prune_outbox`; 3-5 wrong values each by kind (str: None, 0, b'x', ['x'], an object; bool: None,
0, 1, 'true', an object; int|None: True, '3', 1.5, an object; ...). SQL counted with a
`before_cursor_execute` listener; fresh in-memory store per probe.

**391 probes: 187 REFUSED before any SQL, 86 LATE (refused after SQL ran), 36 WRONG-EXC, 82
ACCEPTED silently.** (Run 1 had 60 more WRONG-EXC that were the INSTRUMENT: it probed `SetEngine`
writes on a store a `Store` owns, so `UnloggedWriteRefused` fired first; fixed to a standalone
engine store and re-run.)

Gap classes:

| class | where | today |
|---|---|---|
| G1 read accepts a wrong-typed identifier | `Store.check` relation + all six six-part fields, `Store.lookup_reverse` relation, `Store.expand` relation; `SetEngine.check` all six | `False` / empty, silently (a list sometimes reaches SQLite: `ProgrammingError`) |
| G2 write refuses a wrong type only after SQL | `Store.add_tuple` / `remove_tuple` relation + six-part fields | `TypeError`/`ValueError` after the store lock and statements (atomic, but late) |
| G3 flag accepts anything | `Store.adopt(bulk=)`, `build_index(bulk=)`, `rebuild_index(bulk=)`, `parse_openfga_schema(enable_boolean=)` | truthiness, silently (the F19 shape) |
| G4 shapes accept anything | `Store(object_wildcard_shapes=)` 'doc' / 5 / an object | accepted |
| G5 session not checked | `Store(session=None / 'x' / object)` | `AttributeError` |
| G6 store-id args on module functions | `build_index` source/index ids, `open_set_engine` store_id, `prune_outbox` store_id + before_watermark | `StoreNotFound`, `ProgrammingError`, `ArgumentError`, or accepted |
| G7 schema text not type-checked | `parse_openfga_schema(5)`, `save_schema(..., 5)`, `SetEngine(schema=5)` | `AttributeError` |
| G8 `open_set_engine(ops=...)` | wrong ops | refused, but after SQL |

Target: every row REFUSED (TypeError for a wrong type, ValueError for a wrong value) before any
SQL. Fix home: `tuplestr._bind` for every identifier part of every call form (G1, G2), and
shared validators at each constructor / module function for G3-G8.

## Why the suite missed F19 (and TK172, TK175)

REASONED from first-hand facts, 2026-10-30b:

- Not the install. Every trial BROKEN so far (0.1.0 F18 = `TK172`, 0.1.1 F19 = `TK176`)
  reproduced first-hand against the checkout in the pinned local env. Local deps differ from
  a fresh install (READ: local SQLAlchemy 2.0.51 / sqlmodel 0.0.39 / pyroaring 1.1.0 /
  pydantic 2.13.4 vs the 0.1.1 trial's 2.1.6 / 0.0.48 / 1.2.0 / 2.14.2), but CI already runs
  the newest versions.
- The suite covers VALID inputs densely (oracle-differential matrix, hypothesis, invariant
  checker per write) and WRONG-TYPED inputs only where someone wrote a check. READ: before
  `TK176`, every `sync=` in `tests/` and `scripts/installed_smoke.py` was `True`, `False` or
  `sync=sync`.
- `TK172` needed two `Store` instances on one store; the suite used one per store.
- `TK175` was caught by `tests/test_hypothesis.py::test_add_then_remove_restores_row_multiset`
  only on a rare draw; it passed the 6-seed `fuzz.yml` sweep and seeds 1-6.

## Measurements (first-hand RUN, 2026-10-30b, in-memory SQLite, PYTHONPATH=src, 0.1.1)

| what | value |
|---|---|
| `Store.check("user:a", "viewer", "doc:1")`, sync, one tuple | ~595 us/call (2000 calls) |
| `inspect.Signature.bind` on `Store.__init__`'s signature (a generic decorator's core) | 3.53 us/call, 0.6 % of a check |
| one `isinstance` check | ~43 ns |

Behaviour of reads on wrong types (same run):

| call | result |
|---|---|
| `check(None, "viewer", "doc:1")` | `TypeError` (user must be a str ...) -- good |
| `check("user:a", "viewer", 5)` | `TypeError` (object must be a str ...) -- good |
| `check("user:a", None, "doc:1")` | **`False`, silently** -- GAP |
| `check("user:a", 7, "doc:1")` | **`False`, silently** -- GAP |
| `check(..., at_least=True)` / `at_least="3"` | `TypeError` -- good |

READ: `Store.check` / `add_tuple` / `lookup` are `(self, *args, at_least=..., **kwargs)`;
every call form is bound in `src/zanzibar/schema/tuplestr.py::_bind`. Annotations are strings
(`from __future__ import annotations` in `store/_store.py`, `setengine/engine.py`).
`src/zanzibar/py.typed` ships.

## Decision (session, 2026-10-30b; user asked for the reasoning, then said file it)

**Explicit validators at the public boundary + a census test that makes them mandatory. Not a
runtime type-checking decorator.** Latency does not decide it (0.6 % generic, ~0 explicit);
correctness does:

1. The annotations do not encode the contract. `at_least: int | None` must refuse `True` (a
   `bool` is an `int`); `paranoia: bool | int | str | None` must accept it; `None` is a
   meaningful value for `schema=`, `at_least=`, `paranoia=`, `object_type=`. "Reject wrong
   types and None" is a per-parameter decision, so it lives in a table, not in annotations.
2. The hot methods take `*args, **kwargs` (two call forms), so a decorator sees nothing there.
   The choke point is `tuplestr._bind`.
3. Refusals must say what to write instead (CLAUDE.md, refused-shape rule's spirit); a
   generic checker says "expected bool, got NoneType".
4. `beartype` would be fast but adds a runtime dependency and keeps problems 1-2; `typeguard`
   is slow.

## Plan

1. **Census test first (it is the measurement).** Enumerate every documented public callable
   (the `userdocs/reference/api/*` surface: `Store` + methods, `Store.adopt`, `SetEngine`,
   `WildcardIndex` reads, `TupleSource`, `parse_openfga_schema`, `build_index` /
   `rebuild_index`, `open_set_engine`, `prune_outbox`, ...). A table maps each parameter to
   its legal kinds and wrong values to try (`None`, `0`, `True`, `"x"`, `object()`); each wrong
   value must raise `TypeError` / `ValueError` with NO SQL statement executed (engine
   `before_cursor_execute` listener) and no state change. **A parameter missing from the table
   fails the test**, so a new argument cannot ship unclassified. Its first run's red list is
   appended here, dated, before any fix.
2. **Shared validators** in one module (`require_bool`, `require_str`, the existing
   `require_setops`, ...), called by constructors once and by `tuplestr._bind` per call.
3. Sabotage each validator class; record tails in the test docstring.

Sibling rows (same release): `TK180` hypothesis bias toward self-references (the `TK175`
class), `TK181` multi-instance smoke + docs pages run twice / in pairs in one folder (the
`TK172` and F5 / F22 class), `TK177` AdmissionRejected notation + cycle INSTEAD.
