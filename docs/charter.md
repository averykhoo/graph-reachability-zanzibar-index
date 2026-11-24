# Charter

LIVING. About a page, from the owner (FRAMEWORK §3.1): the goals, the anti-goals, and the mandates. It
is replaced only with the owner's confirmation. A story's `goals:` field names the goal ids
below, so give every goal one (`G-1`, `G-2`, ...) and never renumber them.

The owner's words for this charter are [DEC-22](decisions/DEC-22-charter-goals-anti-goals-mandates-and.md)
(2026-11-24), quoted there verbatim, given in answer to a proposed draft, and their follow-up
[DEC-23](decisions/DEC-23-charter-follow-up-orm-backend-abstraction-fuzz.md) (2026-11-24); where
an older record holds a rule, it is cited too.

## Goals

| Id | Goal |
|---|---|
| G-1 | Independent implementations (the graph index, the set engine and the reference oracle in `tests/oracle.py`), with the oracle as the referee, an attempt to prove their equivalence through Lean and fuzzing, and from that the reasoning that the spec is followed precisely. DEC-22 ("we're building independent implementations, attempting to prove their equivalence through lean and fuzzing"); CLAUDE.md § Who decides (equivalence is the primary consideration, 2026-09-12b). It is phrased as an attempt "mostly because we haven't been able to write a comprehensive proof yet"; if that were easy enough, the owner would strengthen it to "proven equivalent", with code pins from the Python to Lean ("from python comments or decorators or something") (DEC-23). That stronger form is an aspiration, not a current goal. The `file::symbol` anchors of [CORRESPONDENCE.md](../formal/CORRESPONDENCE.md), which `formal/conformance/anchor_check.py` asserts resolve, are an existing, partial form of such pins: they live in that doc rather than in the Python, and keep the map navigable, not true. |
| G-2 | Correctness, through an assurance surface made honest and legible, not wider. Work on the Lean proofs will probably resume when the new fable and opus models are out. DEC-22 ("yes, the goal is correctness", confirming the assurance-surface goal of [DEC-8](decisions/DEC-8-the-project-goal-honest-legible-assurance-not.md), 2026-09-22c). |
| G-3 | An exploration of algorithms that is also usable: a library, published on PyPI as `zanzibar-index`. DEC-22 ("as much as this is an exploration of algorithms it should also be usable"). |

## Anti-goals

These are constraints and things this repo is not, rather than hard bans.

- **Perf is not a direct goal, but it is a small consideration.** The index should not run
  significantly slower than brute force, "since if the index runs significantly slower than
  brute force then it's not a very good index" (DEC-22). Perf as the goal was rejected in DEC-8.
- **Not an OpenFGA clone.** The DSL and the API partly follow the owner's taste in what is pretty in
  a DSL or an API. Compatibility is nice to have: point to the OpenFGA docs and list the few
  deviations and how to work around them, or provide a polyfill or compat mode (DEC-22). The
  deviations are logged in [spec-deviations.md](spec-deviations.md).
- **Ideally backend-agnostic.** "No MySQL isn't a rule but yes the backend engine should not
  be reliant on it"; SQLite- and PostgreSQL-specific features are fine, but ideally the engine
  is fully backend-agnostic (DEC-22). The owner adds "since we're using postgres notifications
  I guess we're past that"; as of 2026-11-24 `src/` uses no PostgreSQL LISTEN/NOTIFY (a grep
  finds only SQLAlchemy session `event.listen` hooks), and its dialect-specific surface is the
  row lock and the isolation check named in CLAUDE.md § Gotchas. The follow-up (DEC-23):
  SQLAlchemy or SQLModel is "probably a good orm layer to use as an abstraction", with SQLite
  selectable as the backend, and it "should probably work with any db". The owner is "okay to
  maintain the psycopg thing for the locks or pubsub for faster replication, mostly as an
  example, but it should still work without it"; that is a permission, not a description: no
  pub/sub exists in `src/` today, and the row locks go through SQLAlchemy's `with_for_update`.
  It "might work with redis", but that is not needed here.
- **Few shims.** Things are mostly either supported or not, without much legacy in the code
  (DEC-22; the "No compatibility shims exist" line of CLAUDE.md § Layout).

## Mandates

- The owner does not read Lean; architectural and proof decisions are delegated to Claude
  (CLAUDE.md § Who decides, 2026-09-12b; DEC-22). A fable second opinion on top of opus is
  worthwhile for those calls (DEC-22).
- Push, and push a release tag, only on the owner's word (CLAUDE.md § Start here and § Running
  things; the contract's § Rules).
- Fuzz and hypothesis never run on a schedule. They may run locally before push, in CI on push
  (watched by a haiku or scripted babysitter), or both: GitHub minutes are free for public
  projects, so "it doesn't really matter" (DEC-22, refined by DEC-23; superseding the
  2026-10-07 "on demand and before a release only" rule). The workflow change is TK-308.
- Schemas are self-consistent: no dangling references, no computed or tupleset cycles (ASK-1,
  2026-09-26).
- A `from` tupleset is direct-only (TK106, 2026-09-26), and may not restrict to a userset
  (TK108, 2026-09-27).
- Every refused schema shape says why and what to write instead, at the refusal (owner
  instruction 2026-09-27; CLAUDE.md § Gotchas).
- The wildcard extensions beyond OpenFGA are kept but unproven, and are to be proved
  eventually; they are not the highest priority while proofs take a long time, and are
  reprioritized if future models are optimized for Lean (ASK-2, 2026-09-26;
  [DEC-7](decisions/DEC-7-wildcards-beyond-openfga-and-the-registry-idiom.md); DEC-22).

## Next milestone

Last rerank: 2026-11-20a
