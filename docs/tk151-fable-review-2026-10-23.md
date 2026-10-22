# TK151 — fable editorial review of userdocs/, 2026-10-23

FROZEN as-of 2026-10-23 (review input; the actions taken are recorded on TK151 and in docs/tk151-diataxis-plan-2026-10-20.md). Provenance: claude-fable-5 subagent, first-hand READ of every userdocs page + PYPI_README.md; its findings are REASONED editorial judgement, not verified claims. Transcribed verbatim from its persisted report.


Started 2026-10-23. Incremental; findings appended as read.

## Pass 1: landing (index.md), PYPI_README.md, four section indexes

- Landing first screen: says WHAT (ReBAC, Zanzibar-style, OpenFGA subset, SQLite/PG) clearly. Does NOT say WHY-over-OpenFGA/SpiceDB (no "embedded library, no server, your own DB" line), and does NOT mention that there are two backends at all; the two-backend fact first appears in PYPI_README para 2 but on the site only in explanation/two-backends.md. A newcomer reading index.md cannot answer "which backend do I use" because the page never says a Store has backends.
- PYPI_README is actually the better pitch than index.md: para 2 ("Two backends give the same answers with opposite cost models") is the one-sentence framing the landing page lacks. Its quickstart has `but not` + ban; the landing quickstart is simpler. Two different "first" examples - fine but the site's is the weaker one.
- Landing: alpha warning + install + a long note about the master-vs-PyPI banner + 0.0.x rename BEFORE the first code. Three caveat blocks before any code = too much throat-clearing. The "install from source" note duplicates the Furo announcement banner that conf.py already injects.
- Landing: "## License" sits between "A first look" and "Where to go next" - misplaced; should be last or dropped (already on PyPI page).
- Landing: "plus a few [extensions]" linked in sentence 2 - a newcomer does not need extension beyond OpenFGA in the first sentence; it reads as a hedge.
- how-to/index.md: grouped into 4 headings, scannable, one-line gloss each. Good. "Use the backends directly ... An application should use a Store instead" - fine but odd to list a how-to whose gloss says don't.
- explanation/index.md: 9 pages; descriptions good. Order: zanzibar-intro first makes sense.
- reference/index.md: table, fine.
- conf.py: strict build, pinned inventories, announcement banner - solid.

## Pass 2: tutorials
- first-check.md: excellent. Pure tutorial voice, every step shows output, exactly one job. Ten-minute claim credible. Only nit: the SchemaMismatch paragraph ("delete first-check.db") is a hedge but a necessary one given file DB.
- drive-app.md: excellent; the strongest page on the site. Markers/excluded_keys introduced exactly where a reader hits them. The "From here" list is the right length.
- Neither tutorial mentions "set engine" / "graph index". Fine for tutorials, but it means a reader who goes landing -> tutorials -> how-tos meets "the index", "stall", "freshness token" in how-to titles without ever having been told there is an index. The landing page must carry the one-paragraph "a Store = tuple log + set engine + graph index" framing.

## Pass 3: all 15 how-tos (read in full)

General: the how-to voice is consistent, concrete, every claim has a runnable block. Quality is high; the problem is VOLUME and a tendency for each page to carry its own copy of the cross-cutting caveats (freshness, StaleRead/ForeignToken, "sync instance refused while async backlog pending", "first write after open is slow"). Those four caveats each appear on 3-5 pages.

- query-access.md (17.6KB): the page a developer reaches for most. Strong first half. Second half ("Read wildcard grants" variants, the `covers()` helper, `"all"` markers needing object_wildcard_shapes, implicit_keys, LookupResult vs ExpandResult marker-shape mismatch) is reference material living in a how-to. The marker-shape inconsistency between LookupResult (triples) and ExpandResult (pairs) is an API wart the docs explain at length instead of the API fixing; for 0.1.0 it should at least be a one-line note, not a code block on comparing them. "Freshness" section duplicates async-tokens.md and errors.md.
- async-tokens.md (12KB): good; the stale-revoke trap section is the single most important paragraph on the site for a user and it is at section 7 of 9. The worker loop is a real recipe. "Token numbers are shared by every store in the database, so they are not consecutive" - fine. ForeignToken appears here, in errors.md, in query-access.md and in upgrade-0.1.md: four copies.
- errors.md (18KB): well organised by "what to do". But it is a reference page wearing a how-to hat: it enumerates EVERY exception with prose, which reference/exceptions.md (30KB) does again. The "What except ZanzibarError does not catch" section is genuinely useful. MissingDeltaProcessor / CascadeNotRun / IndexExists bullets say "A Store never raises this" - those belong in backends-direct, not in a user's error-handling guide.
- patterns.md: excellent. The folder-block-list recipe (viewer_base + inherited blocked) is the kind of thing a user cannot derive. Combining-operators table is good.
- postgresql.md: good and honest. The "idle in transaction" bullet is exactly the sharp edge a user would hit; it is stated where they would hit it. The TupleSource paragraph at the end is internal leakage ("If you write through the lower-level TupleSource") - a user on this page has never heard of it.
- port-openfga.md: good; table is the right shape. Conditions/modules refusal table duplicated with rewrite-refused-shape.md "Header lines, conditions and modules".
- rewrite-refused-shape.md: good. Sections 2-5 are needed. "Recursion through and/but not" honest about "This is NOT the same schema" - good.
- change-schema.md: short, clear, one job. Uses RelationTuple + select directly (leaks ORM internals, but there is no public export API; honest about it).
- bulk-load-adopt.md: fine. "Do the steps by hand" + "Or load through a Store instead" = two optional tails; could be cut to a sentence.
- backends-direct.md: the last section "Do not drive the graph index on its own" is 1 paragraph of 260 words with run_cascade / outbox_watermark / DeltaProcessor; it is a warning to contributors, not users. "The index refuses a write on the boolean relation's own name with a ValueError; a write has to be rewritten onto the relation's internal parts first" - internal.
- runtime-checks.md: the after-commit InvalidRequestError behaviour ("that Store object cannot be used again") is a bug described as a feature at length; honest, but 0.1.0 should either fix it or the page should say "known bug, tracked". The is_invariant_violation helper is the user working around it.
- fanout-cap.md: the "pending async row poisons every sync writer" trap is stated 3 times on the site (here, stall-recovery, errors). Good that it is stated; it should have ONE home with links.
- stall-recovery.md: solid runbook; 32-diamond example is a nice executable demonstration. "Writes through a sync instance fail too" again.
- prune-outbox.md: the Note about full/fixpoint re-check covering fewer rows is internal reasoning; a user needs "safe to prune at outbox_watermark after last commit; done". Cut the Note.
- upgrade-0.1.md (20KB): the longest how-to. Necessary, but the "Until 0.1.0 is released, a build from source still reports 0.0.5" note MUST go before ship (it will be false the moment the tag lands; same note in errors.md TablesOutdated bullet). Step 8 "Optional: use what 0.1 adds" is changelog content.

Jargon leakage found in how-tos (user-facing, unexplained or barely explained): "tupleset" (used in rewrite-refused-shape and port-openfga before being defined; defined only in reference/schema-language), "closure" ("closure fan-out cap", "closure row"), "delta processor", "cascade", "outbox_watermark", "TupleSource", "evaluator" (errors.md explicitly apologises for it: 'The "evaluator" the message mentions is the store's in-memory set engine' - fix the message, not the doc), "residue" (used as a paranoia level NAME; the how-to never says what a residue is - acceptable as an opaque token but the name itself is jargon). No task ids (TK*, I13) leaked into how-tos. Good.

## Pass 4: explanation (9 pages, read in full)

- zanzibar-intro.md: very good. This is the best "why ReBAC / what is Zanzibar" primer I have seen in a library's docs. "What this library is, and is not" section is the positioning statement the LANDING PAGE lacks ("no server, no network API ... in-process ... your own SQLite or PostgreSQL"). Move/copy those 3 bullets to index.md.
- two-backends.md: good. The comparison table is the backend-choice answer, but it is buried in the explanation section; nothing in index.md or how-to/index.md points a newcomer at "which do I use?". And the real answer ("use a Store; the Store uses both; the question you actually face is sync vs async") is only implicit. "Who owns the transaction" subsection = the second sharpest edge on the site for a user (a committed grant survives your rollback). Good that it has a runnable demo. It should be surfaced in the tutorial or PG how-to.
- graph-index.md: good explanation; "Some and all" subsection is deep; fine here.
- boolean-operators.md: "delta processor", "residue", "strata", "stratified negation", "derived edge" all appear. It is an explanation page so some mechanism is expected, but the names leak into how-tos (paranoia level "residue"). Acceptable; could name the level "boolean" or "exclusions" in a future release, not for 0.1.0.
- consistency.md (16KB): excellent and the best-argued page. The "stale in both directions / revoked grant still reads as allowed" rule is stated clearly. The stall table is good. Summary at the end is good. It is long but earns it.
- semantics-vs-openfga.md (17.6KB): thorough and honest. Summary table at end is the right artefact. It cites "OpenFGA has announced (July 2026)" - date-stamped, good. 
- wildcard-extensions.md: good. The ref to refused-shapes anchors is fine.
- assurance.md (14.8KB): the "what the proofs do not cover" section is exemplary honesty. Tone: this is written for a sceptical reviewer, which a user may also be. It says "Lean 4" and explains it; no I13/TK leaks. Length OK for explanation.
- limits.md (17KB): the best "sharp edges" page; "When not to use this library" is exactly what a newcomer needs and it is the LAST section of the LAST explanation page. The bullet "You need a mature, stable API. The library is at version 0.0.x" - STALE for 0.1.0 (MUST fix). "Writes dominate your load: do not use the graph index ... Use the set engine on its own instead" contradicts how-to/index.md's gloss on backends-direct ("An application should use a Store instead") - a user following limits.md is told to do the thing the how-to list says not to do. Reconcile.

## Pass 5: reference (read all but the back half of exceptions.md, which was skimmed)

- schema-language.md: good reference. Grammar block, restriction table, consistency rules. One job.
- refused-shapes.md: generated from source comments; excellent idea, cannot drift. Fine.
- tuple-strings.md: the "two call forms" and the form-selection algorithm (keyword decides, else arity) is an API complexity documented well. is_valid_identifier("...") -> True quirk is honestly listed.
- configuration.md: two env vars + Store args table. Good. Paranoia table duplicates runtime-checks.md's table almost verbatim (third copy in assurance.md prose). One canonical table + links.
- tables.md: "This refusal is new in 0.1.0, which is not yet released" - MUST update at release. 
- environments.md: "New in 0.1.0 (unreleased)" - same.
- changelog.md: "## 0.1.0 (unreleased)" - will be fixed by the release process presumably (conf.py banner keys off CHANGELOG.md), but the userdocs copy is separate prose; check it is regenerated.
- api/index.md: lazy-import demo is nice. "Result markers" section is the right single home for the marker-shape wart; query-access.md and consistency.md and wildcard-extensions.md and api/index.md all explain it (4 homes).
- api/store.md: autodoc + hand-written. TupleSource documented as "Writing through the log without a Store" - this is a contributor/advanced surface and takes a third of the page; fine for reference, but its presence makes the public surface look bigger than a user needs. "The attributes widx, ruleset, source, proc, cursor and paranoia_guard are internal plumbing" - good.
- api/graphindex.md: WildcardIndex/ReachabilityIndex/DeltaProcessor documented for the "drive it yourself" audience. OK in reference.
- exceptions.md (30KB): a class-by-class catalogue; the hierarchy tree at the top is the valuable artefact. 30KB is long because each class gets prose that errors.md also carries.

## Cross-cutting counts (first-hand READ, 2026-10-23)
Topics with >=3 homes on the site:
- stale-revoke / tokens: async-tokens, consistency, query-access#freshness, errors#freshness, postgresql#async, limits (6)
- ForeignToken: async-tokens, errors, query-access, consistency, upgrade-0.1, changelog (6)
- sync writer refused while async backlog row pending: fanout-cap, stall-recovery, errors, consistency table, limits (5)
- paranoia level table: runtime-checks, configuration, assurance, api/store (4)
- marker shape triple-vs-pair: query-access, api/index, consistency, wildcard-extensions (4)
- "first write after open is slow": fanout-cap, limits, upgrade-0.1, changelog (4)
- CyclicDerivedDependency rewrite (viewer_base): patterns, rewrite-refused-shape, boolean-operators, semantics-vs-openfga, schema-language, errors (6)
- "unreleased"/"0.0.5 still reported" notes: index.md, upgrade-0.1, errors, tables, environments, changelog, limits("0.0.x") (7) -- all must change at tag time.

## Verdict and ranked recommendations (final)

VERDICT: ship after small fixes. The writing is unusually good (tutorials, consistency.md, zanzibar-intro.md, limits.md "when not to use"). The problems are (a) the landing page does not sell or orient, (b) seven pages carry "0.1.0 is unreleased / source still reports 0.0.5" prose with NO test pinning it, so they will ship stale, and (c) duplication of cross-cutting caveats across 4-6 pages each, which inflates a 437KB site without adding assurance. None of it needs a restructuring pass; the Diataxis split itself is sound.

1. MUST  index.md: first screen. Add, above "Install", one paragraph with: (i) "an in-process library over your own SQLite/PostgreSQL, no server to run" (lift the three bullets from explanation/zanzibar-intro.md "What this library is, and is not"); (ii) the one-sentence two-backend framing already on PYPI_README.md para 2; (iii) one line of guidance "Use Store; it uses both. The choice you actually make is sync (default) vs async, see how-to/async-tokens". Then cut the extensions link from sentence 2, move License to the end, and drop the master-vs-PyPI :::note (conf.py's announcement banner already does that job; keep only the one-line 0.0.x rename pointer).
2. MUST  pre-release prose that will be false at tag time, and nothing pins it: index.md:42 note; how-to/upgrade-0.1.md:13-17 note ("still reports 0.0.5"); how-to/errors.md:189-191 (TablesOutdated bullet, same claim); reference/tables.md:93 ("not yet released"); reference/environments.md:23 ("New in 0.1.0 (unreleased)"); reference/api/index.md:54 (example "0.0.5"); explanation/limits.md:267 ("The library is at version 0.0.x"). Either delete them in the release commit or add a test that fails when __version__ is 0.1.0 and any of these strings survives (grep 'unreleased|not yet released|reports.*0\.0\.5|is at version 0\.0' under userdocs/).
3. MUST  Reconcile limits.md "Writes dominate your load ... use the set engine on its own instead" with how-to/index.md gloss "Use the backends directly ... An application should use a Store instead" and backends-direct.md "Prefer the Store". Pick one message. Suggest: how-to gloss becomes "open a set engine without a Store: for tooling, experiments, and write-heavy loads where the graph index is the wrong trade (see Limits)".
4. SHOULD  One home per cross-cutting caveat, others become one sentence + link. Specifically: stale-revoke rule -> consistency.md owns, async-tokens.md keeps the recipe, cut the Freshness section of query-access.md to 3 lines; ForeignToken -> errors.md owns; "sync writer refused while async backlog pending" -> fanout-cap.md owns, stall-recovery/errors/limits link; paranoia level table -> configuration.md owns (runtime-checks keeps the choose-a-level prose, assurance.md and api/store.md link); marker triple-vs-pair -> api/index.md "Result markers" owns, delete the comparing-shapes code block from query-access.md.
5. SHOULD  how-to/errors.md is doing reference's job (18KB enumerating every class, which exceptions.md does again at 30KB). Cut errors.md to: the four "what to do" buckets with 2-3 named exceptions each, the "except ZanzibarError does not catch" list, and the warning section. Move MissingDeltaProcessor / CascadeNotRun / IndexExists bullets (all "A Store never raises this") out to backends-direct.md.
6. SHOULD  Promote "a committed grant stays committed even if your own code later rolls back" (two-backends.md "Who owns the transaction") to where a user hits it: a 3-line admonition in tutorials/first-check.md "Create a store" step and a bullet in postgresql.md "One session per thread". It is currently only in an explanation page.
7. SHOULD  Jargon pass on how-tos: define "tupleset" at first use in rewrite-refused-shape.md and port-openfga.md ("the relation after `from`"); replace "closure fan-out cap" with "write fan-out cap" in user-facing headings (keep the env var name); fix the StaleRead message to say "set engine" not "evaluator" so errors.md:954 can delete its apology; cut prune-outbox.md's Note about full/fixpoint re-checks (internal reasoning).
8. NICE  runtime-checks.md "When a check fails" after-commit behaviour (InvalidRequestError wrapping, Store unusable) is a bug documented as a feature with a helper to work around it. Tag it "known limitation, tracked" in one sentence, not three paragraphs; or fix before 0.1.0.
9. NICE  query-access.md: move "An object-side all marker" subsection and the covers() helper to wildcard-extensions.md / api reference; page drops from 17.6KB to ~11KB and stays a how-to.
10. NICE  upgrade-0.1.md step 8 ("Optional: use what 0.1 adds") is changelog content; replace with a link to reference/changelog.md.

WHAT I WOULD CUT (net): ~60-80KB of the 437KB without losing a fact: duplicate caveat copies (4), errors.md second half (5), query-access.md back half (9), upgrade step 8 (10), the index.md note block (1), prune-outbox Note (7). Nothing in explanation/ needs cutting; it is long but each page earns it.

WHAT IS GOOD AND SHOULD NOT BE TOUCHED: both tutorials; consistency.md; zanzibar-intro.md; limits.md "When not to use"; assurance.md "What the proofs do not cover"; refused-shapes.md generated from source; semantics-vs-openfga.md summary table; the how-to index grouping.
