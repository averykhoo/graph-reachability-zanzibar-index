# TK151 — editorial review of the whole user-docs site before 0.1.0 (2026-10-26)

## Correction 2026-10-26e (stage "apply-site-review"): what was applied

Applied FIRST-HAND by one agent (again no `Agent` tool in the harness, so no fan-out). After
the edits, `tests/test_userdocs_examples.py`, `test_userdocs_build.py`,
`test_userdocs_refused_shapes.py`, `test_userdocs_diagrams.py`, `test_tk123_pypi_page.py`
and `test_tk122_release_metadata.py` ran green together (2026-10-26e), as did
`test_userdocs_prerelease_prose.py`.

| rec | applied? | what / why |
|---|---|---|
| M1 | **no, deferred to the cut** | Every listed sentence is TRUE while `__version__` is 0.0.5, and `tests/test_userdocs_prerelease_prose.py::test_guard_fires_on_current_tree` requires `KNOWN_CURRENT` to still carry it before the bump. Apply in the release commit together with the version bump. |
| M2 | **no, deferred to the cut** | Same: the re-cut of `reference/changelog.md` from `CHANGELOG.md` belongs to the release commit. |
| M1, M2 at the cut | **applied 2026-10-26e (stage cut-prep)** | `__version__` "0.1.0"; every M1 line rewritten as listed (the guard named limits.md:287, errors.md:182, upgrade-0.1.md:15, environments.md:23, tables.md:119 at the bumped version; api/index.md:53 by hand); `reference/changelog.md` heading "0.1.0 (2026-10-26)", no Unreleased section, plus the TK165/167/168/169/170 fixes. The guard's real-tree half is now `test_guard_armed_on_current_tree` (sabotage in its module docstring). RAN: test_tk122_release_metadata, test_userdocs_*, test_tk123_pypi_page, 60 passed. |
| M3 | yes, the "better still" form | `src/zanzibar/store/source.py` (the `WatermarkGap` raise in the evaluator advance) now says "set engine watermark ... call refresh() (Store) or refresh_evaluator() (TupleSource)"; the `StaleRead` gloss is deleted from `reference/exceptions.md`. No test pins the old text (grep). Not yet in `CHANGELOG.md`: a message change, for the cut stage to list. **Listed 2026-10-26e (stage "fix-unapplied-site-review")**: `CHANGELOG.md` `[Unreleased]` § Fixed, the entry after TK169's `StaleRead` line; old text checked by `git diff` ("evaluator watermark ... refresh_evaluator(), and retry"). M1/M2 still deferred to the release commit; the guard scans `userdocs/**/*.md` only, so `userdocs/conf.py`'s "Unreleased" comments are outside its scope, and its banner switches off once `CHANGELOG.md`'s newest heading is not "Unreleased". |
| S1 | yes | `patterns.md` one-sentence pointer; `errors.md` now uses `define member: [user, group#member] but not banned`; `boolean-operators.md` cut to the first block + pointer. `rewrite-refused-shape.md` unchanged (already the owner). |
| S2 | yes | `fanout-cap.md` reflowed as proposed. |
| S3 | yes | `backends-direct.md` paragraph -> four bullets; `CascadeNotRun` bullet shortened. |
| S4 | yes | `index.md` pre-deploy line; `PYPI_README.md` line gains runtime checks. |
| S5 | yes, **with a correction** | The review's "every one of the ten tables carries `store_id`" is FALSE (READ, `SQLModel.metadata` dump): `zanzibar_store` keys it as `id`, `zanzibar_index_cursor` as `index_store_id`, and graph rows reference `zanzibar_store` by FK. The new `reference/tables.md` § "Deleting a store" says so and gives the ten DELETEs in FK order. Probe (2026-10-26e, `.scratch` only, result recorded here): two stores on one in-memory SQLite DB, the ten DELETEs for `tenant:acme`, every table then holds 0 rows for it, `Store(session, "tenant:acme", schema=<different schema>)` opens and checks `False`, and the other store still checks `True`. `change-schema.md` links to it. |
| S6 | yes | New `how-to/test-permissions.md` (fixture + two tests; the second block calls a test body directly so the page is executed with a checked `# ->`), listed under "Model your permissions". |
| S7 | yes | `runtime-checks.md` stays the single home; `errors.md` and `configuration.md` cut to a clause + link. |
| S8 | yes | `PYPI_README.md:12`, `consistency.md:21`, `limits.md:19` -> "a few indexed lookups". |
| S9 | yes | `prune-outbox.md` reasoning cut to the proposed paragraph. |
| N1 | yes | `rewrite-refused-shape.md` conditions/modules rows -> one pointer row; `test_userdocs_refused_shapes.py` green. |
| N2 | **no** | It would delete an EXECUTED example (`bulk-load-adopt.md` "Do the steps by hand") that is the only place the three-step recipe is run; not plainly an improvement. |
| N3 | yes | `PYPI_README.md` Reference bullet gains the release notes. |
| N4 | yes | `patterns.md` § "One store per tenant" (store id rule cited from `tuple-strings.md` § "Store ids", not the identifier charset). |
| N5 | yes | `environments.md` "Threads and processes": synchronous API, worker thread owning its `Session`/`Store`. |
| N6 | yes | `runtime-checks.md` "After the commit" bullet opens with "Known limitation, to be fixed in a later release". |
| N7 | yes | `upgrade-0.1.md` parenthetical link to the `zanzibar.store` reference page. |

ACTIVE-PLAN until the listed MUST items land; FROZEN at the 0.1.0 cut. Session key
`2026-10-26e` (workflow wf-rel010, stage "site-review"). Reader assumed: a Python developer
adopting the library in their first week. Prior review, whose applied items are NOT repeated
here: `docs/tk151-fable-review-2026-10-23.md` (its recs 1-6, 9, 10 landed; 7 partial; 8 open
as `TK163`).

Provenance. **No `Agent` tool was available in this harness** (ToolSearch found none), so the
fan-out the stage asked for could not run; every page below was read FIRST-HAND by this
session (fable), grep-targeted, and every claim about the code was checked with a grep of
`src/` the same hour. Labels: **READ** = page read in full; **PART** = read by section +
grep; **CODE** = checked against `src/`; **REASONED** = editorial judgement.

Coverage: READ in full: `index.md`, `PYPI_README.md`, the four section indexes, both
tutorials, all 15 how-tos, `explanation/{limits,two-backends,consistency,zanzibar-intro,
wildcard-extensions,assurance}.md`, `reference/{configuration,tables,environments,changelog,
tuple-strings,refused-shapes}.md`, `reference/api/{index,store}.md`. PART:
`explanation/{graph-index,boolean-operators,semantics-vs-openfga}.md`,
`reference/{exceptions,schema-language}.md`, `reference/api/{schema,setengine,graphindex}.md`.

What is already right (do not touch): both tutorials; `consistency.md`; `zanzibar-intro.md`;
`limits.md` "When not to use"; `assurance.md` "What the proofs do not cover"; the how-to index
grouping; the TK165/TK167/TK170 edits on `consistency`, `async-tokens`, `stall-recovery`,
`errors`, `exceptions`, `runtime-checks` (all read; wording correct, CODE-checked against
`src/zanzibar/store/_store.py::_name_blocking_backlog_row` and `Store._catch_up`). No `TK*`
id, `ASK-*`, `I1x`, `tests/`, `src/`, `formal/` or `.scratch` path leaks into any page
(grep, `reference/changelog.md` excluded by design).

Counts: **MUST 3**, **SHOULD 9**, **NICE 7**.

---

## MUST (before the tag)

### M1. Pre-release prose: six guard hits plus one the guard cannot see
`tests/test_userdocs_prerelease_prose.py` goes red the moment `__version__` leaves 0.0.x
and names these lines (READ, line numbers as of 2026-10-26):

| file:line | text | exact fix |
|---|---|---|
| `userdocs/explanation/limits.md:287-290` | "The library is at version 0.0.x, and any release, including a patch release, may change the API." | "The library is at version 0.x, and any release, including a patch release, may change the API." (keep the rest of the bullet) |
| `userdocs/how-to/errors.md:182-184` | "Until 0.1.0 is released, a build from source also reports version 0.0.5, so check how the file was made, not the version number; see the note on the upgrade page." | delete the sentence; end the bullet at "write the tuples again." |
| `userdocs/how-to/upgrade-0.1.md:13-17` | the whole `{note}` block ("Until 0.1.0 is released ...") | delete the block |
| `userdocs/reference/changelog.md:8` | `## 0.1.0 (unreleased)` | `## 0.1.0 (<tag date>)`; see M2 |
| `userdocs/reference/environments.md:23` | "New in 0.1.0 (unreleased): 0.0.5 has no `docs` extra" | "New in 0.1.0; 0.0.5 has no `docs` extra" |
| `userdocs/reference/tables.md:93-94` | "This refusal is new in 0.1.0, which is not yet released; the 0.0.x releases do not have it." | "This refusal is new in 0.1.0; the 0.0.x releases do not have it." |
| `userdocs/reference/api/index.md:53` | `for example ``"0.0.5"``` (the guard's regex deliberately skips it) | `for example ``"0.1.0"``` |

`limits.md:181` ("Before 0.1.0 the same refusal took 91 s") stays true after the cut; keep.

### M2. `reference/changelog.md` must be re-cut from `CHANGELOG.md` in the release commit, and must then carry NO "Unreleased" section
READ: `CHANGELOG.md:9` is `## [Unreleased]`; the userdocs copy mirrors it as "0.1.0
(unreleased)" and lists the same breaking items (spot-checked: `TablesOutdated`,
`ForeignToken`, `PersistedSchemaRefused`, `CascadeNotRun`, cheap fan-out refusal; all
present in both). At the cut: rename both headings to the dated 0.1.0, and do not add a
fresh "Unreleased" heading to the userdocs copy afterwards, because the guard matches
`/unreleased/i` anywhere under `userdocs/` once the version is 0.1.x (trap recorded on
`TK151` 2026-10-23b). Either narrow the guard then, or title later work-in-progress
sections "Next release" on the userdocs page.

### M3. `reference/exceptions.md:362-364` glosses a word the message no longer uses
The `StaleRead` entry says: "The message's "evaluator" is the store's in-memory set engine."
CODE: both `StaleRead` messages now say "set engine" (`src/zanzibar/store/source.py:744`,
`src/zanzibar/store/_store.py:1098`, the TK169 rewording). The only message still saying
"evaluator" is `WatermarkGap`'s (`source.py:687`: "evaluator watermark ... call
refresh_evaluator()"). Fix: delete that sentence from the `StaleRead` entry; in the
`WatermarkGap` entry (`exceptions.md:423-430`) add "The message's "evaluator" is the store's
in-memory set engine; `refresh_evaluator()` is what `Store.refresh()` calls." Better still,
reword the `WatermarkGap` message itself to "set engine" (same pattern as TK169) and add
nothing.

---

## SHOULD (before the fable site re-read, or in the same commit as the cut)

### S1. The `viewer_base` rewrite has five homes; make it one
READ, 2026-10-26: `how-to/patterns.md:192-231`, `how-to/rewrite-refused-shape.md:224-273`,
`how-to/errors.md:139-167`, `explanation/boolean-operators.md:290-315`,
`explanation/semantics-vs-openfga.md:284-290`, `reference/schema-language.md:244-250`.
Decision (REASONED): **`rewrite-refused-shape.md` § "Recursion through `and` or `but not`"
owns** the rewrite and the "this is NOT the same schema" caveat (it is the page the refusal
message points at). Then:
- `patterns.md:227-231` (the "tempting one-relation form" paragraph): replace with one
  sentence: "The one-relation form `define viewer: ([user] or viewer from parent) but not
  blocked` is refused; [Rewrite a refused schema shape](rewrite-refused-shape.md#recursion-through-and-or-but-not)
  explains why and how the rewrite differs." Keep the folder-block recipe (L192-225): it is
  the executable recipe and belongs on the patterns page.
- `errors.md:139-167`: the page only needs to show that `except SchemaError` misses
  `CyclicDerivedDependency`. Replace the `FOLDERS` schema with the three-line
  `define member: [user, group#member] but not banned` case, keep the three `print(...)`
  lines, and keep L166-167 (the link). Saves ~20 lines.
- `boolean-operators.md:295-315`: cut to the first code block plus "This is not the same
  schema; the differences, and the inheriting-block variant, are worked through in
  [Rewrite a refused schema shape](...)." Delete the second block (L306-310) and L311-314.
- `semantics-vs-openfga.md:284-290` and `schema-language.md:247-250`: keep as they are (one
  sentence each; the reference and the summary may restate a rule).

### S2. `how-to/fanout-cap.md:138-142`: the TK167 insertion needs a reflow
Two lines run past 100 columns and the duplicate-add aside sits mid-sentence. Replace
L138-142 with:

> same store id fails, even an unrelated small grant, and removals included. The exception's
> message says so: it starts "this write (log row N) was rolled back because the index
> backlog ... holds an earlier log row it cannot apply", names that pending row, and says how
> to unblock the store. Its `failing_log_row` attribute is `(log id, row)` for that pending
> row. (A duplicate add appends no log row, so its message starts "this write (a duplicate
> add, which appends no log row)" instead.) Two refusals behave this way:

CODE: both message prefixes match `_store.py:94-97`.

### S3. `how-to/backends-direct.md:159-180`: one 260-word paragraph for a contributor audience
Now that the commit itself refuses a skipped cascade (`CascadeNotRun`, TK3), the paragraph
can be four bullets under the same heading:
- "On a schema with `and` or `but not`, the index refuses a write on the boolean relation's
  own name; a write goes onto its internal parts, and only `DeltaProcessor.run_cascade`
  brings the relation in line with it."
- "Committing a transaction that wrote to the index on such a schema and ran no cascade
  after that write raises `CascadeNotRun`; the transaction stays open: roll back, or run the
  cascade and commit again."
- "The check proves a cascade ran, not that it ran with the right watermark: pass the
  `outbox_watermark` read before the first write. A refused write still leaves the
  transaction owing a cascade or a rollback."
- "A `Store` does all of this for you, in the write (`sync=True`) or in `catch_up()`
  (`sync=False`)."
The "alice would never get can_view" example sentence can go; the `CascadeNotRun` bullet in
L189-192 already repeats the rule, so shorten that bullet to its first sentence + "(above)".

### S4. `index.md` "Where to go next": add the pre-deploy pointer the PyPI page has
`PYPI_README.md:85-87` says "Before a first deploy, read ... async mode and freshness tokens,
pruning the change outbox, and the exceptions reference." The site landing page has no such
line, so a reader who starts on the site meets async-tokens only as one of fifteen how-tos.
Add after the four-part list (`index.md:88`): "Before a first deploy, read
[Use async mode and freshness tokens](how-to/async-tokens.md), [Turn on runtime checks in
production](how-to/runtime-checks.md), [Prune the change outbox](how-to/prune-outbox.md)
and [Handle errors](how-to/errors.md)." Add `runtime-checks` to the PyPI line too (it is the
recommended production setting, `runtime-checks.md:5`).

### S5. Missing first-week task: deleting a store (a tenant's data)
READ: the only mention is `how-to/change-schema.md:56-57` "the library has no call that
deletes a store". A developer with a tenant-per-store layout (`tuple-strings.md:207-208`
suggests `"tenant:acme"`) has no page saying how to remove one. Add to
`reference/tables.md`, after "The tables" (L52): a short section "Deleting a store": there
is no API; every one of the ten tables carries `store_id` (L4-5), so a store is removed by
deleting its rows from all ten in one transaction, with every instance of that store closed
first; its freshness tokens mean nothing afterwards; the same id may then be created again
with `Store(session, id, schema=...)`. Label the SQL as yours to write (no helper to cite).
Then make `change-schema.md:57` link to it. (CODE, 2026-10-26: `grep -rn "def delete\|def
drop\|def purge" src/zanzibar` is empty, so "no API" is true.)

### S6. Missing first-week task: testing a permission model
No page shows a pytest fixture. The pieces exist (`sqlite://` in-memory stores on every
how-to; `error::zanzibar.UnprovenExtensionWarning` at `errors.md:347-348`; `paranoia="full"`
"for tests" at `runtime-checks.md:43`). Add a 30-40 line how-to "Test your permission
model" under "Model your permissions" in `how-to/index.md`: a `store` fixture that opens
`Store(Session(create_engine("sqlite://")), "test", schema=SCHEMA, paranoia="full")`, one
test that asserts a grant and a ban, and a note that `paranoia="full"` is for tests. Keep it
executable (every ```python block runs, `tests/test_userdocs_examples.py`).

### S7. The post-commit `InvalidRequestError` caveat (open `TK163`) has five homes
READ: `how-to/runtime-checks.md:106-115` (plus the helper, L117-130), `how-to/errors.md:269-272`,
`reference/configuration.md:40-43`, `reference/exceptions.md:114`, `explanation/assurance.md:119-122`.
`TK163` is still open (pri LATER), so the prose is TRUE and must stay somewhere; make
`runtime-checks.md` "When a check fails" the single home and cut the others to one clause +
link: `errors.md:269-272` -> "When it comes from the check that runs after a commit it
currently arrives wrapped in a SQLAlchemy error; see [When a check fails](...)"; drop the
"cannot be used again" sentence from `configuration.md:40-43` (keep "reaches the caller as
`sqlalchemy.exc.InvalidRequestError`" + link); `exceptions.md:114` keep as is (one row);
`assurance.md:119-122` keep (already one parenthesis + link). When TK163 closes, only
`runtime-checks.md` needs rewriting.

### S8. One phrase for the cost of a check
READ: "a single lookup" (`consistency.md:21`, `limits.md:19`), "a lookup of one row"
(`graph-index.md:52`), "a few indexed lookups" (`index.md:17`, `two-backends.md:58`,
`api/index.md:63`, `api/graphindex.md:3`), "a small, fixed number of indexed database
lookups" (`two-backends.md:28`), "one indexed lookup" (`PYPI_README.md:12`). CODE:
`boolean-operators.md:201` is right that a derived-relation check is an edge probe plus a
residue row, so "single" is false on `but not` schemas. Use "a few indexed lookups" (or "a
fixed number of") everywhere: fix `PYPI_README.md:12`, `consistency.md:21`, `limits.md:19`;
`graph-index.md:52` may keep "one row" because that section is about `or`/`from` only
(L7-8 says so).

### S9. `how-to/prune-outbox.md:77-91` is internal reasoning
Replace L77-91 with: "For a `Store`, the position read after its last commit is always
safe: the library reads outbox rows only inside the transaction that wrote them (the
`and` / `but not` update, and the `"full"` / `"fixpoint"` runtime checks), so a committed
row is never needed again. This holds for `sync=False` too. If you drive
`DeltaProcessor` yourself and hold a position across transactions, pass the lowest
position you still hold." (Keeps every fact in L77-94 in three sentences.)

---

## NICE

### N1. Conditions/modules rows appear twice
`how-to/port-openfga.md:61-62` and `how-to/rewrite-refused-shape.md:297-298` carry the same
two rows. Keep them in `port-openfga.md` (the porting checklist is the reader who has them)
and replace the two rows in `rewrite-refused-shape.md` with one: "| conditions, modules |
no rewrite; see [Port an OpenFGA model](port-openfga.md#2-fix-what-is-refused) |".

### N2. `how-to/bulk-load-adopt.md:163-197`: two optional tails
Merge "Do the steps by hand" and "Or load through a `Store` instead" into one short section
"Other ways in" of two paragraphs; drop the by-hand code block (the three calls are named in
the prose and documented on `api/store.md`).

### N3. `PYPI_README.md`: add the changelog
The "Documentation" list has no changelog link although the page tells 0.0.x users to
upgrade; add "[release notes](.../reference/changelog.html)" to the Reference bullet. Also
S8's "one indexed lookup" -> "a few indexed lookups".

### N4. One store per tenant
`patterns.md` has no multi-tenancy note although the store id is the natural tenant key.
Add a 4-line recipe at the end: store ids are free-form (`tuple-strings.md:207`), all stores
share the ten tables, tokens belong to one store (`ForeignToken`), and a tenant is deleted
per S5.

### N5. Synchronous API only
`reference/environments.md` "Threads and processes" should say the API is synchronous: from
an asyncio application call the store in a worker thread that owns its `Session` and
`Store`. (CODE, 2026-10-26: `grep -rn "async def" src/zanzibar` is empty.)

### N6. `how-to/runtime-checks.md:98-115` tone
Once S7 makes it the single home, open the "After the commit" bullet with "Known
limitation (to be fixed in a later release):" so the three sentences of behaviour read as a
caveat, not a design.

### N7. `userdocs/how-to/upgrade-0.1.md:31-33`
Names `TupleSource`, `SchemaRecord`, `TupleLog` in the first screen of the upgrade page. They
are correct and are reference names; a parenthetical "(all documented on the
[zanzibar.store](../reference/api/store.md) page)" would stop a reader hunting for them.

---

## Verified claims (CODE, 2026-10-26) that the review relied on
- `ZANZIBAR_MAX_CLOSURE_FANOUT` default 100,000 (`graphindex/core.py:85`); `MAX_PATH_COUNT = 2**31 - 1` (`core.py:96`): `fanout-cap.md:16-17`, `limits.md:152-153`, `stall-recovery.md:29`, `configuration.md:166` all agree.
- `at_least` refuses `bool` and non-`int` with `TypeError`, negative with `ValueError` (`store/source.py:269-272`): `errors.md:284-286`, `upgrade-0.1.md:128-129`, `consistency.md:122-123` agree.
- Paranoia aliases `1/true/yes/on` = full (`graphindex/invariants.py:173-174`): `runtime-checks.md:84-85`, `configuration.md:11`, `api/store.md:268-270` agree.
- `prune_outbox` negative -> `ValueError` (`graphindex/outbox.py:74-75`): `prune-outbox.md:68`, `api/graphindex.md:179` agree.
- Every `ZanzibarError` subclass has a builtin base, `UnsupportedByGraphIndex` included (`schema/errors.py:288`): `errors.md:5-7`, `rewrite-refused-shape.md:13`, `upgrade-0.1.md:190-193` agree.
- `WildcardIndex` still types `subject_predicate: str | EllipsisType` (`graphindex/wildcard.py:629`), so `api/graphindex.md:49` "(or `Ellipsis`)" is right for the bare index while `Store` refuses it (`upgrade-0.1.md:125-127`).
- Backlog-row message prefixes (`store/_store.py:87-97`) match `fanout-cap.md:138-141`, `stall-recovery.md:116-119`, `stall-recovery.md:129`.
- Every ```python block on the site is executed with `# ->` expectations checked (`tests/test_userdocs_examples.py` docstring), so the measured numbers quoted inline (e.g. `stall-recovery.md:73,77` "27 rows") are pinned, not prose.
