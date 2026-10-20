# How correctness is checked

An authorization library is only useful if its answers are right, and a wrong answer is
usually silent: a `check` that returns `True` when it should return `False` raises no
error. This page explains how the answers of this library are checked, what each method
can and cannot catch, and exactly what has been proved and what has not.

The short version:

| method | what it checks | what it cannot catch |
| --- | --- | --- |
| [An independent reference implementation](#an-independent-reference-implementation) | the answer to every query, computed a third, deliberately simple way | a mistake shared by the reference and the semantics it was written from |
| [The validation matrix](#the-validation-matrix) | both backends and the reference agree on every query over a corpus of schemas | schemas and data outside the corpus |
| [Property-based fuzzing](#property-based-fuzzing) | the same agreement on generated schemas, data and operation sequences | behaviour the generators never produce |
| [Runtime invariant checks](#runtime-invariant-checks) | the graph index's stored state is internally consistent, on your data, as you write | a consistent state that encodes a wrong answer |
| [Machine-checked proofs](#machine-checked-proofs-of-the-algorithms) | models of both algorithms compute the specified semantics, for all inputs in scope | the Python code itself, and everything outside the proved scope |

None of these is enough alone. Read the rest of the page for where each one stops.

## What is being checked

The library answers every question in two independent ways (see
[The two backends](two-backends.md)): the **graph index** precomputes who can reach what
when you write, and the **set engine** computes the answer from the stored tuples when you
ask. They share the schema parser and evaluate every answer independently.

So the central claim is **equivalence**: for every schema the library accepts, every set
of tuples and every query, the two backends give the same answer, and that answer is the
one the schema language specifies. When the two disagree, the working assumption is that
the code is wrong and is fixed. The reference results and the specification are not edited
to match the code.

## An independent reference implementation

The test suite contains a third evaluator, the **oracle**. It answers one `check` at a
time by applying the definitions directly, with no precomputation, no bitmaps and no
database. It is written to be obviously correct rather than fast.

It is also deliberately **independent** of the library: it imports nothing from the
`zanzibar` package and parses the schema text with its own parser. A bug in the library's
parser therefore cannot corrupt both sides of a comparison. Each schema refusal the library
makes (see [Refused schema shapes](../reference/refused-shapes.md)) has a twin in the
oracle's parser, and a test requires the two parsers to accept exactly the same schema
texts.

What the oracle cannot catch: a misreading of the semantics that it shares with both
backends. Where the semantics follow OpenFGA, the claims to do so have been audited against
OpenFGA's own documentation and source; the deliberate differences are listed in
[Semantics and differences from OpenFGA](semantics-vs-openfga.md).

## The validation matrix

The **validation matrix** runs a corpus of schemas, each with stored tuples, through every
evaluator and compares the answers over a full grid of queries: every relevant subject
against every relevant relation and object. For each query it compares:

- the answer written by hand in the test,
- the oracle,
- the set engine, run twice, once with the default `pyroaring` bitmaps and once with plain
  Python sets, so a bug in one set representation cannot hide,
- the graph index.

For schemas with `and` or `but not`, the graph index runs with its maintenance step for
those operators (see [How `and` and `but not` work](boolean-operators.md)), and its stored
state is audited after every write.

Two further gates use the same idea:

- The **lookup gate** checks `lookup`, `lookup_reverse` and `expand` on both backends
  against a brute-force answer built from the oracle: ask the oracle about every candidate
  object or subject, and compare the resulting set with what the lookup returned.
- Integration-style tests run by default through a test engine that sends every operation
  to all the backends at once and fails the test unless they agree on every query, so a test written
  for some other purpose also checks equivalence as a side effect.

What the matrix cannot catch: a disagreement on a schema shape, or a pattern of tuples,
that no corpus contains.

## Property-based fuzzing

To reach beyond the hand-written corpus, the suite uses
[Hypothesis](https://hypothesis.readthedocs.io/) to generate schemas, stores and sequences
of writes. Instead of hand-written expected answers, the generated tests check properties
that must hold whatever the input:

- two schemas written differently but meaning the same thing give the same answers;
- adding tuples and then removing them restores the original answers;
- the order in which tuples are written does not change the answers;
- replaying the tuples from scratch gives the same state as maintaining it write by write;
- a schema printed and parsed again is the same schema;
- a long random sequence of adds and removes keeps every backend in agreement with the
  oracle after every step.

Each change runs the fuzzing at a fixed size. A wider sweep over several random seeds runs
before a release.

What fuzzing cannot catch: behaviour that the generators never produce. A generator that
never emits a particular shape tests nothing about that shape, however long it runs.

## Runtime invariant checks

The checks above run in the library's own test suite, on its own data. The graph index can
also check itself **in your deployment, on your data**, as you write. Its stored state obeys
a set of invariants: path counts are consistent, the stored relationship graph has no
cycles, wildcard bookkeeping matches the declared shapes, and the extra state that the
boolean operators keep refers only to live rows. A `Store` can verify these as part of
every commit:

- `"off"` (the default) checks nothing.
- `"residue"` checks the boolean operators' extra state, without scanning the whole index.
  It also checks that the wildcard bookkeeping the write touched is complete; that part
  costs nothing on schemas without wildcard userset grants such as `[group:*#member]`.
  It is the recommended production setting, because it detects a known class of
  corruption that would otherwise grant access. Its measured cost ranged from a few percent to
  roughly 25% of the synchronous write path, depending on the schema and the store's size
  (2026-07 and 2026-10).
- `"full"` checks every invariant over the whole store, before each commit and again
  after it. It is meant for testing; it more than doubled the cost of writes (2026-07).
- `"fixpoint"` adds a further check of the boolean maintenance step, for diagnosis only.

At every level, the checks made before the commit abort the write: a violation raises
{py:exc}`zanzibar.InvariantViolation` and nothing is written. At `"full"` and `"fixpoint"`
the re-check after the commit can also fail, but by then the write has already committed.
That failure reports corruption that is now stored; it does not undo the write, so a caller
that sees it must not assume the write failed. (In the current version it reaches the
caller wrapped in a SQLAlchemy error rather than as a bare
{py:exc}`zanzibar.InvariantViolation`; [Turn on runtime checks in
production](../how-to/runtime-checks.md#when-a-check-fails) shows how to recognise it.)
{py:exc}`zanzibar.InvariantViolation` deliberately does not inherit from
{py:exc}`zanzibar.ZanzibarError`: it reports corruption, not a refused request. How to turn
the checks on is in [Turn on runtime checks in production](../how-to/runtime-checks.md).

What runtime checks cannot catch: a state that is internally consistent but encodes the
wrong answer. They check the shape of the index, not whether it agrees with the set
engine.

## Machine-checked proofs of the algorithms

The repository also contains proofs written in the [Lean 4](https://lean-lang.org/) proof
assistant, a program that checks every step of a mathematical proof mechanically. You do
not need to read them to use the library. This section says in plain terms what they
establish.

The proofs are about **models** of the two algorithms: precise descriptions, written in
Lean, of what the set engine and the graph index do. Against a formal specification of the
schema language's semantics, they prove that:

1. **The set engine's algorithm** computes the specified answer, for every schema, every
   store and every `check` query.
2. **The graph index's algorithm**, including the step that maintains `and` and `but not`,
   computes the specified answer once a write has been fully processed, for the schemas and
   stores inside a defined **proved fragment** (below).
3. Therefore the two algorithms agree on that fragment. Two consequences are proved
   separately because they are what an authorization system most needs: a `but not`
   exclusion always takes effect, and the graph index never grants access that the
   specification does not.

The specification includes the rule, as in OpenFGA, that a userset such as
`group:eng#member` is a member of itself.

The project's build refuses any proof that leaves a gap, and checks that each key
theorem rests only on the standard logical axioms. The headline theorem statements are
pinned, so a change that weakened what a theorem says would fail the build.

### How the models are tied to the code

A proof about a model says nothing about the Python unless the model matches the code. The
link is made three ways, none of which is itself a proof:

- **A written map** from each part of each model to the Python function it describes. The
  build fails if a function the map names no longer exists, which keeps the map's pointers
  valid but not its claims.
- **Differential conformance tests.** The Lean models are executable. The tests run them on
  a corpus of schemas alongside the real Python backends and the oracle, and require the
  same answers. For the graph index they also compare the stored state the model produces
  with the rows the Python writes, after setting aside a documented list of
  representation details.
- **Exhaustive enumeration of small stores.** For several representative schema shapes,
  the tests try every store of up to three or four tuples drawn from two names per type.
  The bound is tiny on purpose: it is exhaustive within that bound and claims nothing
  beyond it.

### What the proofs do not cover

The proofs are narrower than "the library is formally verified", and it would be wrong to
read them that way. In particular:

- **They are about the models, not the Python.** The tie to the code is the review and the
  tests above. Python behaviour on inputs outside the tested corpora could differ from the
  model without any proof failing.
- **The graph index's proof covers a fragment of the schemas the library accepts.** Outside
  it, the graph index is checked by tests only. The main exclusions, in plain terms:
  - the **wildcard extensions** beyond OpenFGA: wildcard usersets (`[group:*#member]`),
    wildcard tuplesets (`parent: [folder:*]`) and object wildcards. A schema that uses one
    emits {py:class}`zanzibar.UnprovenExtensionWarning` for this reason (see
    [Wildcard extensions beyond OpenFGA](wildcard-extensions.md)). A plain public grant,
    `[user:*]`, is not one of these extensions and does not warn;
  - boolean relations stacked more than two layers deep, where a relation built with `and`
    or `but not` depends on another such relation, which depends on a third;
  - a boolean relation whose operands use a `from` or a userset restriction such as
    `[group#member]` directly. Operands that name other relations, and direct grants such
    as `[user]`, are covered.
- **The graph index's proof also covers only some queries.** It covers a `check` whose
  object is a concrete object such as `doc:1`, and whose subject is a concrete subject or
  a plain public subject (`user:*`). A `check` whose object is a wildcard (`doc:*`), or
  whose subject is a wildcard userset (`group:*#member`), is outside the proved scope and
  is checked by tests only.
- **`lookup`, `lookup_reverse` and `expand` are not modelled.** Only `check` is proved.
  The lookup surfaces are checked by the lookup gate and by fuzzing.
- **Building an index in bulk is not modelled.** {py:func}`zanzibar.store.build_index`,
  and so {py:meth}`zanzibar.Store.adopt`, construct the index in one pass by default rather
  than write by write. That path is tested against the write-by-write one, but no proof
  covers it.
- **The schema compiler's output is trusted.** The models read the schema directly; the
  plans the Python compiles from it are pinned by snapshot tests, not proved.
- **Storage, transactions and concurrency are not modelled at all**: SQL rows, the
  in-memory bitmaps, locks, several instances sharing one store, background catch-up and
  freshness tokens. These are covered by tests, which run on SQLite. The
  PostgreSQL concurrency tests run only when a developer points them at a PostgreSQL
  server; they are not part of the continuous-integration run or of every test run.
- **The proof checker and its mathematics library are trusted**, as with any proof.

## How the checks themselves are checked

A check that cannot fail gives false confidence, so the project treats "a test that
passes for the wrong reason" as its main risk:

- When a check is added, the thing it guards is deliberately broken first, to see the check
  fail. The observed failure is recorded with the check.
- The full suite refuses to pass if any test is skipped, and a known disagreement is
  recorded as a test that asserts the current behaviour, never as an expected failure that
  quietly passes.
- The test count has a floor, so deleting tests turns the build red.

## Reading further

For contributors: the proofs, the map from the models to the code, and the full list of
what is and is not proved are in the
[repository](https://github.com/averykhoo/graph-reachability-zanzibar-index). You do not
need them to use the library.

For what the library costs to run and where it stops, see [Limits and costs](limits.md).
