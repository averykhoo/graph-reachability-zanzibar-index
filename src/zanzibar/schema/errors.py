"""Identifier validation and the error types shared by both backends.

Part of `zanzibar.schema`.
"""
# Provenance (moved out of the docstring, TK123 item 14): split out of the single-file module
# by TK120 (2026-10-06).
import re


# ---------------------------------------------------------------------------
# Identifier validation (strict surrogate ids for both backends)
# ---------------------------------------------------------------------------
#
# Entity types, entity names, and relations are the *surrogate* identities. They are
# stored and interned verbatim, so we constrain them to a conservative, delimiter-free
# charset -- keeping DSL/parsing delimiters (``: # @ , ( ) space`` and the ``or`` /
# ``but not`` keywords already excluded by whitespace), control characters, quotes, and
# injection payloads out of identity strings entirely. Names may additionally be the
# wildcard sentinel ``'*'``; a subject predicate may be the bare sentinel ``'...'``.
# Internal ids remain strictly numeric (allocated int32s), decoupled from these strings.

IDENTIFIER_CHARSET = r'A-Za-z0-9_./@+=-'
# NOTE the anchoring: `\Z`, never `$`. Python's `$` also matches immediately BEFORE a
# trailing newline, so `^[...]{1,256}$` accepted `'alice\n'` and (since the newline is
# not counted by the {1,256} repeat) 257-character names ending in a newline -- a
# control character reaching persisted identity strings, and an off-by-one against the
# documented 1-256 bound, in direct contradiction of this module's header contract.
# Found by the zero-trust review 2026-07-26 (ZT-P1-1); pinned by
# tests/test_reg15_identifier_anchoring.py. `re.fullmatch` below is belt-and-braces
# with `\Z` -- either alone is sufficient; both together make the intent unmissable.
_IDENTIFIER_RE = re.compile(rf'[{IDENTIFIER_CHARSET}]{{1,256}}\Z')


class ZanzibarError(Exception):
    """The root of every exception this package raises on purpose.

    ``except zanzibar.ZanzibarError`` catches every refusal, limit and freshness error the
    library defines. Each subclass ALSO keeps the builtin base it always had
    (``ValueError``, ``RuntimeError``, ``KeyError`` ...), listed after this one, so code
    that catches the builtin keeps working.

    Deliberately NOT a subclass of this: ``zanzibar.graphindex.InvariantViolation``. It is
    an ``AssertionError`` that means the stored index is CORRUPT, not that a call was
    refused, and a handler written for refusals must never swallow it. Also outside:
    ``UnprovenExtensionWarning``, which is a warning, not an error.
    """


class SchemaError(ZanzibarError, ValueError):
    """A schema text (DSL or OpenFGA JSON) was refused by the parser.

    Raised for syntax errors, dangling or cyclic relation references, and every refused
    schema shape; the message says what is wrong and, for a refused shape, what to write
    instead. A ``ValueError`` subclass, so ``except ValueError`` still catches it.
    """


class AdmissionRejected(ZanzibarError, ValueError):
    """A write was CORRECTLY REFUSED at admission -- never a sign of corruption.

    The exact mirror of ``zanzibar.graphindex.invariants.InvariantViolation`` ("a rejection is a
    *correct* refusal; a violation is corruption"). This class is the *rejection* half
    said out loud, as a TYPE rather than as message text: the store is intact, the
    write was inadmissible. The refusal families are

      * a cycle (a self-referential edge, a back-path, a star self-edge),
      * an identifier outside the declared charset/length,
      * a tuple no declared type restriction admits (incl. a raw write naming a
        compiler-generated leaf predicate),
      * an undeclared subject-/object-wildcard shape,
      * a remove of an edge/node/tuple that is not there.

    ``ClosureFanoutExceeded`` (below) is a SUBCLASS and a deliberate outlier: it is
    the one refusal family that admission cannot predict, so it needs its own type.

    It is NOT for internal-contract failures -- a stale node id, a malformed wildcard
    encoding, a write routed onto a processor-owned derived relation, a "shortcut only supports count == -1". Those stay
    plain ``ValueError`` deliberately: they mean a CALLER (or this library) is broken,
    and a consumer that classifies exceptions must be able to tell them apart. When in
    doubt a site stays unclassified, because the fail-closed direction is for the
    classifier to propagate it.

    **Subclassing ``ValueError`` is deliberate and load-bearing**, not an accident of
    convenience: every existing caller and test catches ``ValueError`` around a write
    (``zanzibar.store._store._write``'s narrow rejection path, the test harnesses'
    backends, ``zanzibar.graphindex.processor``'s cycle guard,
    ``zanzibar.store.apply._apply_row``'s ValueError->InvariantViolation promotion).
    All of those keep working unchanged. Narrowing to ``AdmissionRejected`` is strictly
    OPT-IN, and the only thing it buys is the ability to tell a correct refusal from an
    internal-contract ``ValueError``, which is a bug.

    WHY IT LIVES HERE. This is the shared schema layer: it imports neither backend, and
    both backends plus the composition layer import it. So both ``zanzibar.graphindex`` and
    ``zanzibar.setengine`` can raise the same rejection type without either importing the other,
    and ``validate_write_identifiers`` (called by both) raises it directly.
    ``zanzibar.graphindex.core`` re-exports it for convenience.

    NOTE the caller-relativity: the same raise can be a refusal at ADMISSION and
    corruption further downstream. ``zanzibar.store.apply._apply_row`` replays an
    already-admission-validated log row, so it promotes ANY ``ValueError`` (this class
    included) to ``InvariantViolation``. That promotion is the caller's judgement, and
    this class does not weaken it -- EXCEPT for ``ClosureFanoutExceeded``, whose whole
    point is that admission provably could not have predicted it.
    """
    # Provenance (moved out of the docstring, TK123 item 14): the harnesses are
    # tests/parity.py and tests/test_matrix.py.
    # Provenance (moved out of the docstring, TK123 item 14): the routing breach is invariant
    # I5.


class IndexResourceLimit(AdmissionRejected):
    """The graph index declined to MATERIALISE an admitted write: a resource limit
    over the closure, not a property of the tuple and the schema.

    The common base of the refusals ``zanzibar.store.apply._apply_row`` must NOT promote
    to ``InvariantViolation`` (see ``ClosureFanoutExceeded`` for why that promotion is
    wrong for this family). Two members: ``ClosureFanoutExceeded`` and
    ``PathCountExceeded``. ``_apply_row`` catches THIS class, so a new member
    is exempt from the promotion by construction.
    """
    # Provenance (moved out of the docstring, TK123 item 14): ClosureFanoutExceeded is
    # ZT-P1-6a.
    # Provenance (moved out of the docstring, TK123 item 14): ``TK111``.


class PathCountExceeded(IndexResourceLimit):
    """A write would push a closure row's path count past ``MAX_PATH_COUNT``.

    ``Edge.indirect_edge_count`` counts derivations (paths), not reachability, so a
    K-layer diamond chain makes it ``2**K``. The column is ``INTEGER``: int4 on
    PostgreSQL, int64 on SQLite. Before this refusal the write failed at FLUSH with a raw
    ``DataError`` (PostgreSQL, K=31) or ``OverflowError`` (SQLite, K=63) -- a refusal
    nobody could classify, which ``Store._write`` treated as an unknown bug.
    The bound is the int4 ceiling on BOTH dialects, so the same write is refused the
    same way on dev SQLite as on the PostgreSQL server. Saturating the count instead
    was rejected: it breaks the exact decrement a later removal relies on.
    """
    # Provenance (moved out of the docstring, TK123 item 14): the refusal landed with TK111.
    # Provenance (moved out of the docstring, TK123 item 14): ``TK111``.


class ClosureFanoutExceeded(IndexResourceLimit):
    """The per-write closure fan-out cap refused a write.

    The cap bounds how many permission-closure rows ONE write may add, and so how long
    that write holds the store's write locks; it is a blast-radius bound, not an
    authorization policy. It is set by the ``ZANZIBAR_MAX_CLOSURE_FANOUT`` environment
    variable (default 100,000; ``0`` disables it) or ``ReachabilityIndex(
    max_closure_fanout=...)``. The refusal is atomic: the write is absent from the tuple
    log, the set engine and the graph index alike, so both backends still agree.

    It can bite at the default: granting, banning or adding a member to a group whose
    closure would grow by more than 100,000 rows -- for example a grant to a group of more
    than 100,000 members -- is refused. Under ``but not`` a ban is such a write too, and it
    is capped like any other.

    WHY IT NEEDS ITS OWN TYPE. Every other ``AdmissionRejected`` family is a property of
    the tuple and the schema, decided before the row reaches the log. The fan-out cap is
    an INDEX-side resource limit over the materialised closure: the same tuple is
    admissible or not depending on how large the closure has grown. So it is enforced on
    synchronous writes only. A row already in the log that the index replays
    (``Store.catch_up``, ``build_index``) is applied with a logged warning instead,
    because refusing a committed row would stall the index.

    A subclass of ``IndexResourceLimit``, which ``zanzibar.store.apply._apply_row``
    does not promote to ``InvariantViolation``: a cap refusal is never corruption.
    """
    # Provenance: corrected 2026-10-17 (TK153; the TK150 scout,
    # docs/closure-fanout-cost-2026-10-14.md Correction 2026-10-16 (c)). The old text said
    # the cap "does not bite at the 100,000 default, which is why no test caught it" (false
    # since TK112: docs/spec-deviations.md "Corrected 2026-10-03b") and that the store
    # "cannot advance past" an over-cap row (false since replay runs inside
    # ReachabilityIndex.fanout_cap_suspended). Found 2026-07-29 while measuring the
    # hub-topology DoS: a tuned-down cap surfaced through the store as
    # InvariantViolation('... corruption or a validity-parity bug ...').
    # Provenance (moved out of the docstring, TK123 item 14): ZT-P1-6a.


def is_valid_identifier(value) -> bool:
    """Strict charset membership ONLY: the reserved sentinels ``'*'`` (wildcard name)
    and ``'...'`` (bare subject predicate) are NOT valid identifiers -- they are
    admitted positionally by ``_require``'s ``allow_star``/``allow_ellipsis`` flags,
    never by this predicate. External callers wanting "is this writable as a name"
    should go through ``validate_write_identifiers``."""
    return isinstance(value, str) and _IDENTIFIER_RE.fullmatch(value) is not None


def _require(value, label: str, *, allow_star: bool = False, allow_ellipsis: bool = False) -> None:
    # The sentinels are admitted only as the exact ``str`` (or ``Ellipsis``), never by
    # ``==`` alone: a non-str whose ``__eq__`` matched ``'*'`` / ``'...'`` used to pass
    # here and reach the database driver as an unbindable parameter (TK125, 2026-10-08,
    # pinned by tests/test_tk125_write_field_types.py). ``None`` is NOT the bare
    # predicate on a WRITE -- ``norm_pred``'s ``None -> '...'`` is read-side leniency.
    is_str = isinstance(value, str)
    if allow_ellipsis and (value is Ellipsis or (is_str and value == '...')):
        return
    if allow_star and is_str and value == '*':
        return
    if not is_valid_identifier(value):
        extra = ''.join([" or '*'" if allow_star else '', " or '...'" if allow_ellipsis else ''])
        # TK123 item 17: a 'type:name' string in a type or name field is the commonest
        # first-hour mistake (the OpenFGA form passed to a six-part call); say so.
        if is_str and ':' in value and label.endswith(('_type', '_name')):
            extra += (f"; {value!r} looks like 'type:name' -- pass the type and the name "
                      f"as separate arguments, or use the three-argument form "
                      f"add_tuple('user:alice', 'viewer', 'doc:d1')")
        # AdmissionRejected: an out-of-charset identifier is a correct refusal of the
        # WRITE, not evidence of a broken store.
        raise AdmissionRejected(
            f"invalid {label} {value!r}: must match [{IDENTIFIER_CHARSET}] (1-256 chars){extra}")


def reject_ellipsis_predicate(subject_predicate, method: str, *, write: bool) -> None:
    """Refuse the Python ``Ellipsis`` as a subject predicate at the public entries of
    ``Store``, ``TupleSource`` and ``SetEngine``: the bare predicate is the STRING
    ``'...'``. A write raises ``AdmissionRejected`` (as a ``None`` predicate does); a
    read raises ``TypeError``. The graph index's internal API still takes
    ``Ellipsis``."""
    # TK123 item 9: ``...`` and ``'...'`` used to be interchangeable on some entries and
    # not others; the public surface now takes one spelling.
    if subject_predicate is Ellipsis:
        msg = (f"{method}: subject_predicate is the Python Ellipsis (...); write the "
               f"string '...' for a bare subject")
        if write:
            raise AdmissionRejected(msg)
        raise TypeError(msg)


def validate_write_identifiers(subject_predicate, subject_type, subject_name,
                               relation, object_type, object_name) -> None:
    """Reject any out-of-charset identifier on a tuple write (shared by both backends).

    Types and relations must be plain identifiers; names may be the wildcard ``'*'``; the
    subject predicate may be the bare ``'...'`` (or ``Ellipsis``). Every field must be a
    ``str`` (``Ellipsis`` aside): ``None``, ``int``, ``bytes`` are refused in EVERY
    field, the subject predicate included -- call this on the RAW argument,
    before ``norm_pred``, which would turn a ``None`` predicate into ``'...'``."""
    # Provenance (moved out of the docstring, TK123 item 14): TK125.
    _require(subject_type, 'subject_type')
    _require(relation, 'relation')
    _require(object_type, 'object_type')
    _require(subject_name, 'subject_name', allow_star=True)
    _require(object_name, 'object_name', allow_star=True)
    _require(subject_predicate, 'subject_predicate', allow_ellipsis=True)


def validate_store_id(store_id, label: str = 'store_id') -> None:
    """A store id must be a ``str`` with at least one non-whitespace character.

    Called first by every constructor that takes a store id and can persist under it
    (``Store``, ``TupleSource``, ``SetEngine``, ``ReachabilityIndex``) and by
    ``save_schema``, so the refusal precedes any statement. ``None`` used to reach the
    NOT NULL ``store_id`` column as a raw ``IntegrityError``; ``5``, ``b'x'``, ``''`` and
    ``' '`` were accepted as ids no caller meant. The identifier CHARSET is deliberately
    NOT applied: a store id is the caller's key (``tenant:acme``, a UUID), not a tuple
    field. ``AdmissionRejected`` because it is a correct refusal of the caller's input,
    never a sign of a broken store."""
    # Provenance (moved out of the docstring, TK123 item 14): TK127 follow-up, 2026-10-08,
    # pinned by ``tests/test_tk127_store_id.py``.
    if not isinstance(store_id, str) or not store_id.strip():
        raise AdmissionRejected(
            f'invalid {label} {store_id!r}: must be a str with a non-whitespace character')


def validate_node_identifiers(predicate, entity_type, entity_name) -> None:
    """Validate a single node identity (predicate/type/name) for node-level writes."""
    _require(entity_type, 'entity_type')
    _require(entity_name, 'entity_name', allow_star=True)
    _require(predicate, 'predicate', allow_ellipsis=True)


# ===========================================================================
# Expression AST (spec §2.1) + recursive-descent parser (spec §2.2)
# ===========================================================================
#
# Parsing is split from compilation (spec §2.3): the DSL is parsed into a
# ``SchemaAST`` -- a plain, backend-agnostic tree -- which BOTH the graph index
# (via ``compile_ruleset``) and the set engine / oracle consume. The graph index
# only supports pure-union definitions; ``compile_ruleset`` refuses ``and`` /
# ``but not`` loudly (``UnsupportedByGraphIndex``) so a boolean schema can never be
# silently mis-ingested.


class UnsupportedByGraphIndex(ZanzibarError):
    """A schema construct the graph index cannot represent.

    Raised by ``compile_ruleset`` naming the offending relation: a wildcard shape outside
    the graph index's scope, or a boolean operator (``and`` / ``but not``) when the ruleset
    is compiled with ``enable_boolean=False``. The graph index supports boolean operators
    by default. The set engine handles every shape this refuses except
    ``DoublyBridgedShapeError``.
    """


class DoublyBridgedShapeError(UnsupportedByGraphIndex):
    """A shape that is BOTH a wildcard-userset shape (``T:*#p`` restriction ->
    ``bridged_in_shapes``) and an object-wildcard shape (``bridged_out_shapes``)
    -- the "doubly-bridged" precondition of the F1/F2 divergences. A wildcard write on such a shape
    materializes a ``w_any(T,p) -> w_all(T,p)`` path; every present-or-future
    concrete node of that shape carries both bridges (concrete->w_any in-bridge,
    w_all->concrete out-bridge), so the path is a latent cycle -- the graph
    accepts the wildcard write then permanently REJECTS every later innocent
    concrete write of that shape (accept/reject + completeness divergences vs the
    set engine, plus an innocent-write lockout).

    A subclass of ``UnsupportedByGraphIndex`` (the third entry in the
    wildcard-object scope-rejection family), but its OWN type so the set engine can
    re-raise it -- unlike the other scope rejections, which the set engine
    swallows to degrade to a ruleset-less/oracle-only mode, this one must reject
    on BOTH backends identically (the state must be unconstructible everywhere)."""
    # Provenance (moved out of the docstring, TK123 item 14): the decision-15 family.
    # Provenance (moved out of the docstring, TK123 item 14): see docs/spec-deviations.md
    # 2026-07-17.


class CyclicDerivedDependency(ZanzibarError, ValueError):
    """Derived relations form a dependency cycle (recursion through boolean
    relations is not supported). A ``ValueError`` subclass for backwards
    compatibility, but its OWN type so graph-optional consumers (ParityEngine,
    the set engine's cycle-parity compile) can degrade on exactly this rejection
    without swallowing every other ``ValueError`` a compile regression might
    raise."""
    # Provenance (moved out of the docstring, TK123 item 14): boolean spec sec 1.9.


class SchemaMismatch(ZanzibarError, ValueError):
    """An explicit schema disagrees with the store's persisted (immutable) schema.

    Raised by ``zanzibar.store`` (``ensure_schema``, so ``Store(...,
    schema=...)``) and by ``zanzibar.setengine.SetEngine`` opened on a
    store id that has a ``SchemaRecord``: a set engine answering under a schema other than
    the store's would serve different answers from the same tuples (a dropped ``but not``
    reads as a stale ALLOW). It lives HERE, in the shared layer, so the set engine can raise
    it without importing the composition layer; ``zanzibar.store`` re-exports the
    same class, so ``except zanzibar.store.SchemaMismatch`` still catches it."""
    # Provenance (moved out of the docstring, TK123 item 14): the SetEngine half is TK123 A53.


class ShapeNoLongerAccepted(SchemaError):
    """A schema shape that zanzibar-index 0.0.4 and earlier ACCEPTED and 0.0.5
    refuses: a ``schema`` line naming a version but ``1.1``, extra words on
    a header line, ``but not`` sharing a level with another operator (S7), or a
    restriction to an undeclared type (S8). Raised by `parser.py::_validate_header_line`,
    `parser.py::_reject_unparenthesised_but_not` and
    `parser.py::_validate_restriction_types_declared`.

    It exists for ONE reader: `zanzibar.store.schema_io` re-parses a store's
    PERSISTED schema text on every open, so a store saved under 0.0.4 with one of these
    shapes stops opening. Telling that version break apart from corruption needs a type,
    not message matching; the store layer turns it into
    `zanzibar.store.PersistedSchemaRefused`. ``instead`` is the rewrite that keeps
    the meaning the 0.0.4 store was serving.

    A ``SchemaError`` (so a ``ValueError``) subclass, so every caller that catches the
    parser's refusals is unchanged. A consumer usually catches ``SchemaError`` (a fresh
    schema) or ``PersistedSchemaRefused`` (a stored one); the class is exported from the
    top level with every other exception.

    ``instead`` (a ``str``) is the meaning-preserving rewrite, in words a user can act on,
    for example ``"change the line to 'schema 1.1'"``; the message ends with it too."""
    # Provenance (moved out of the docstring, TK123 item 14): TK137 (2026-10-14); S7 / S8 are
    # its row items.
    # Provenance (moved out of the docstring, TK123 item 14): review challenge C10 in
    # `docs/tk137-dsl-openfga-refusals-2026-10-14.md`.
    # Provenance (moved out of the docstring, TK123 item 14): H1; H2.

    def __init__(self, message: str, instead: str):
        super().__init__(message)
        self.instead = instead


class PersistedSchemaRefused(ZanzibarError, ValueError):
    """A store's PERSISTED schema text uses a shape this version refuses, so the store
    cannot be opened.

    Every open re-parses the stored text (the compiled schema is cache), so a store saved
    by zanzibar-index 0.0.4 or earlier with a shape 0.0.5 refuses stops opening. The
    message says so, quotes the parser's refusal, and gives the rewrite that keeps the
    meaning the store was serving, so the break reads as a version break, not corruption.
    There is no lenient mode on purpose: schemas are write-once, and a store opened under
    a schema the parser refuses would run text no fresh store may hold. ``store_id``,
    ``refusal`` (the parser's ``ShapeNoLongerAccepted``, also ``__cause__``) and
    ``instead`` are attributes. A ``ValueError`` subclass, as the parser's refusal was.

    It is the ONE type for this condition, whatever opens the store: ``Store(session,
    id)`` with or without ``schema=``, ``SetEngine(session, id, ...)`` with the old text,
    a rewritten text or none, ``open_set_engine``, ``save_schema``, ``ensure_schema``
    and ``build_index``. A schema text YOU pass that uses such a shape, for a store with
    no persisted schema, is ``ShapeNoLongerAccepted`` instead: nothing is stored yet, so
    there is nothing to migrate."""
    # Provenance: TK153 F17 (2026-10-17) made SetEngine raise this too; it used to raise
    # SchemaMismatch (rewritten text) or ShapeNoLongerAccepted (the old text) for the same
    # stored store. Moved here from store/schema_io.py so the set engine can raise it.
    # Provenance (moved out of the docstring, TK123 item 14): TK137.
    # Provenance (moved out of the docstring, TK123 item 14): `TK137` review challenge C10,
    # 2026-10-14.

    def __init__(self, store_id: str, refusal: ShapeNoLongerAccepted):
        self.store_id = store_id
        self.refusal = refusal
        self.instead = refusal.instead
        super().__init__(
            f"store {store_id!r}: its persisted schema was saved by zanzibar-index 0.0.4 "
            f"or earlier using a shape this version refuses: {refusal}. To rewrite: "
            f"{refusal.instead}. Schemas are write-once, so the rewritten schema needs a NEW "
            f"store id, with this store's tuples written again (see the 0.0.5 changelog).")
