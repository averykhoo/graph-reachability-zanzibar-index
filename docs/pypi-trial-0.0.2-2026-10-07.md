# Fresh-user PyPI install trial of zanzibar-index 0.0.2 -- 2026-10-07

> **ACTIVE-PLAN** (`docs/README.md` sec 3). The first run of the post-release install check
> the user asked for on 2026-10-07: an agent installs the PUBLISHED package into a blank
> conda env and uses it from the PyPI page alone. Corrections go at the top, dated. FROZEN
> once the rows filed from it close.
> Provenance labels: **CONFIRMED** = re-run first-hand by the session against the repo's
> `src/` (same code as 0.0.2), output matched the agent's; **AGENT** = the trial agent's
> report only, not re-run (UNVERIFIED in the repo's sense). Probe scripts lived in the
> gitignored `.scratch/pypi-trial-0.0.2/`; what matters is transcribed here.

## 0. Setup (AGENT)

Blank conda env, Python 3.13.16, `pip install zanzibar-index==0.0.2`: rc 0, no warnings.
Pulled in SQLAlchemy 2.1.3, annotated-types 0.8.0, pydantic 2.13.5, pydantic-core 2.46.5,
pyroaring 1.2.0, sqlmodel 0.0.48, typing-extensions 4.16.0, typing-inspection 0.4.4. Worked
from a directory outside the repo; `zanzibar.__file__` was in the env's site-packages. The
env was removed afterwards (agent-reported; `conda env list` no longer shows it).

## 1. BROKEN

### B1. A common OpenFGA pattern is refused by the graph index (CONFIRMED)

A relation of the form `x from parent` is refused when its TARGET name (`x`) is also the
name of a boolean (`and` / `but not`) relation on ANY type -- including the containing type,
or an unrelated third type. Every type defining its own `viewer` is the ordinary OpenFGA
idiom, so this bites real schemas.

```
model
  schema 1.1
type user
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder]
    define banned: [user]
    define reader: [user] or viewer from parent
    define viewer: reader but not banned
```

- Graph index: `UnsupportedByGraphIndex: relation doc#reader: TTU 'viewer' from 'parent'
  targets the derived relation 'viewer', but the containing relation is not itself
  boolean-tainted, so it compiles to a plain rewrite rule that would carry derived state on
  its subject predicate (I5 ...`. The message goes on to blame "an undeclared tupleset
  relation being the usual cause", which cannot be the cause here (CONFIRMED).
- Set engine: ACCEPTS the same schema (AGENT, probe `p15` variants B and C; the `p06`
  comparison never reached the set engine -- its constructor call was wrong).
- Renaming the boolean relation (`viewer` -> `can_view`) compiles (CONFIRMED). The check is
  name-based and type-agnostic, by design per the comment on
  `src/zanzibar/schema/compiler.py::_validate_ttu_tuplesets` (AGENT read the installed
  source).
- **Second form, both backends:** `define viewer: ([user] or viewer from parent) but not
  banned` on `doc` raises a bare `ValueError: Rule then-pattern carries a derived subject
  predicate: Rule(if_pattern=RelationalTriplePattern(...` -- an internal-object dump from
  `zanzibar.schema.boolean`, which its own comment calls an unreachable last line of defence
  (CONFIRMED graph side; AGENT: the set engine refuses with the same `ValueError`).

Equivalence reading (`CLAUDE.md` sec "Who decides"): variants B/C are a SCOPE gap -- the graph
refuses what the set engine serves -- not a wrong answer. Variant D is a refusal in both,
via an internal error instead of a `REFUSED SHAPE` with WHY/INSTEAD.

### B2. An empty schema permanently bricks a store id (CONFIRMED)

`ConnectedStore(s, "x", schema="")` is accepted and persisted write-once as an empty ruleset.
Every later `add_tuple` is refused (`AdmissionRejected ... matches no declared type
restriction`), and re-opening with the intended schema raises `SchemaMismatch ... schemas are
static (write-once)`. There is no public way to drop a store. An empty schema file read from
disk reaches this. A schema without the `model` header is also accepted (AGENT; whether to
refuse it is a separate call -- many in-repo test schemas omit the header, UNVERIFIED count).

### B3. A `None` subject predicate leaks a database error (CONFIRMED)

`add_tuple(None, "user", "bob", "viewer", "doc", "d1")` raises
`sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint failed:
zanzibar_tuple_log.subject_predicate` instead of `AdmissionRejected`. The store stays usable
afterwards (AGENT).

## 2. CONFUSING / DOC GAPS (AGENT, not re-run)

- **`lookup` / `lookup_reverse` return internal row ids**
  (`LookupResult(node_ids={2, 3, 4, 7, 16, 18}, ...)`). `ConnectedStore` offers no way to
  resolve them; the agent decoded them by guessing `session.get(zanzibar.graphindex.Node,
  id)`. Results mix all relations and groups; no type/relation filter (OpenFGA ListObjects
  has one). Marker tuples such as `('user','...','any')` and `excluded_node_ids` are
  undocumented. The set engine's `result_keys` (the usable form) is never mentioned.
- **Docstrings:** `add_tuple`, `remove_tuple`, `check`, `watermark` have none; others cite
  internal ids (ZT-P1-3, TK111, "boolean spec sec 8.1") and files not in the wheel.
- **Async mode:** the README never mentions `catch_up()`. An untokened check during lag
  returned the stale answer, and the README's "reads fall back to the set engine when the
  index is behind" holds only for tokened checks.
- **`check(..., at_least=999)`** (beyond the log head) raises `StaleRead ... call refresh()
  ... and retry`, advice that cannot help.
- **Silent mistakes:** a typo'd type in a restriction (`[usr]`) is accepted and then admits
  `usr:a`; `check()` on an undeclared relation/type returns False; a duplicate `add_tuple`
  returns the current watermark silently.
- **Unhelpful errors:** an unknown store id without a schema raises a bare `KeyError`; an
  undeclared relation in a tuple reads as "matches no declared type restriction"; OpenFGA
  conditions (`[user with cond]`) give "invalid subject type in restriction" without saying
  conditions are unsupported. The README lists no unsupported OpenFGA features.
- **`SetEngine` standalone** works, but its constructor `(session, store_id, schema)` and the
  explicit `session.commit()` its writes need are undocumented.
- **Smaller:** `UnprovenExtensionWarning` fires twice per construction and again on every
  reopen, and cites `formal/, W4Fragment`; `ClosureFanoutExceeded` suggests a constructor
  argument a `ConnectedStore` user cannot pass, and the README does not say it lives in
  `zanzibar.schema`; `zanzibar.schema.__all__` has 70 names, many internal-looking, while the
  README calls `__all__` the public surface.

## 3. WORKS (AGENT)

Metadata (licence expression, `LICENSE` in dist-info, `py.typed`, URLs all 200), import with
no warnings, the README quickstart verbatim (both commented expectations hold), only
`zanzibar_*` tables and `ix_zanzibar_*` indexes, the table-clash behaviour the README
describes, a 13/13 ACL scenario (nested groups, `from parent`, `and`, `but not` with a
group ban, un-ban, nested revocation) once B1 was avoided, reopen-from-disk equality,
`SchemaMismatch` on a different schema, async mode as documented in the docstrings,
`[user:*]` with `but not`, the documented warning for `[group:*#member]`, clear errors for a
dangling reference / keyword typo / non-direct tupleset / bad identifier, the fan-out cap,
and `paranoia="residue"`.

## 4. Disposition (2026-10-07)

BROKEN items, each under the `NOW` umbrella `TK127` ("fix what the 0.0.2 install trial found
broken, then release 0.0.3", per the user): B1 -> `TK126`, B2 -> `TK124`, B3 -> `TK125`.
Section 2 (naming, ergonomics, docs) -> `TK123`, `LATER`: the user parked API naming and
ergonomics for a later pass. This trial is the first run of the standing post-release
install check, now in `~/.claude/CLAUDE.md` sec "Git: gate, commit, push".
