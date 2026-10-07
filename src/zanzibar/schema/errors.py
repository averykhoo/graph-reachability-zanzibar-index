"""Identifier validation and the error types shared by both backends.

Part of `zanzibar.schema`; split out of the single-file module by TK120 (2026-10-06).
"""
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


class AdmissionRejected(ValueError):
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
    encoding, an I5 routing breach, a "shortcut only supports count == -1". Those stay
    plain ``ValueError`` deliberately: they mean a CALLER (or this library) is broken,
    and a consumer that classifies exceptions must be able to tell them apart. When in
    doubt a site stays unclassified, because the fail-closed direction is for the
    classifier to propagate it.

    **Subclassing ``ValueError`` is deliberate and load-bearing**, not an accident of
    convenience: every existing caller and test catches ``ValueError`` around a write
    (``zanzibar.connectedstore.store._write``'s narrow rejection path, ``tests/parity.py``,
    ``tests/test_matrix.py``'s backends, ``zanzibar.graphindex.processor``'s cycle guard,
    ``zanzibar.connectedstore.apply._apply_row``'s ValueError->InvariantViolation promotion).
    All of those keep working unchanged. Narrowing to ``AdmissionRejected`` is strictly
    OPT-IN, and the only thing it buys is the ability to tell a correct refusal from an
    internal-contract ``ValueError``, which is a bug.

    WHY IT LIVES HERE. This is the shared schema layer: it imports neither backend, and
    both backends plus the composition layer import it. So both ``zanzibar.graphindex`` and
    ``zanzibar.setengine`` can raise the same rejection type without either importing the other,
    and ``validate_write_identifiers`` (called by both) raises it directly.
    ``zanzibar.graphindex.core`` re-exports it for convenience.

    NOTE the caller-relativity: the same raise can be a refusal at ADMISSION and
    corruption further downstream. ``zanzibar.connectedstore.apply._apply_row`` replays an
    already-admission-validated log row, so it promotes ANY ``ValueError`` (this class
    included) to ``InvariantViolation``. That promotion is the caller's judgement, and
    this class does not weaken it -- EXCEPT for ``ClosureFanoutExceeded``, whose whole
    point is that admission provably could not have predicted it.
    """


class IndexResourceLimit(AdmissionRejected):
    """The graph index declined to MATERIALISE an admitted write: a resource limit
    over the closure, not a property of the tuple and the schema.

    The common base of the refusals ``zanzibar.connectedstore.apply._apply_row`` must NOT promote
    to ``InvariantViolation`` (see ``ClosureFanoutExceeded`` for why that promotion is
    wrong for this family). Two members: ``ClosureFanoutExceeded`` (``ZT-P1-6a``) and
    ``PathCountExceeded`` (``TK111``). ``_apply_row`` catches THIS class, so a new member
    is exempt from the promotion by construction.
    """


class PathCountExceeded(IndexResourceLimit):
    """A write would push a closure row's path count past ``MAX_PATH_COUNT`` (``TK111``).

    ``Edge.indirect_edge_count`` counts derivations (paths), not reachability, so a
    K-layer diamond chain makes it ``2**K``. The column is ``INTEGER``: int4 on
    PostgreSQL, int64 on SQLite. Before ``TK111`` the write failed at FLUSH with a raw
    ``DataError`` (PostgreSQL, K=31) or ``OverflowError`` (SQLite, K=63) -- a refusal
    nobody could classify, which ``ConnectedStore._write`` treated as an unknown bug.
    The bound is the int4 ceiling on BOTH dialects, so the same write is refused the
    same way on dev SQLite as on the PostgreSQL server. Saturating the count instead
    was rejected: it breaks the exact decrement a later removal relies on.
    """


class ClosureFanoutExceeded(IndexResourceLimit):
    """The per-write closure fan-out cap refused a write (``ZT-P1-6a``).

    A subclass, and the ONE refusal family that must not be promoted to
    ``InvariantViolation`` by ``zanzibar.connectedstore.apply._apply_row``.

    WHY IT NEEDS ITS OWN TYPE. Every other ``AdmissionRejected`` family is a property
    of the tuple and the schema, so ``TupleSource`` admission decides it BEFORE the row
    reaches the log; if one of those fires during replay the log really does contain an
    inadmissible row, and "corruption or a validity-parity bug" is the right verdict.
    The fan-out cap is different in kind: it is an INDEX-side resource limit over the
    materialised closure, ``TupleSource`` has no knowledge of ``max_closure_fanout``,
    and the same tuple is admissible or not depending on how large the closure has
    since grown. So a cap refusal during replay is neither corruption nor a parity bug
    -- it is a correctly-admitted row that the index now declines to materialise, and
    the store cannot advance past it until the cap is raised.

    Found 2026-07-29 while measuring the hub-topology DoS: because
    ``AdmissionRejected`` subclasses ``ValueError`` and ``_apply_row`` promotes every
    ``ValueError``, a tuned-down cap surfaced through ``ConnectedStore`` as
    ``InvariantViolation('... this is corruption or a validity-parity bug ...')`` --
    the exact opposite of what ``src/zanzibar/graphindex/core.py``'s raise site says in its own
    comment ("not an InvariantViolation, because nothing is corrupt"). It does not bite
    at the 100,000 default, which is why no test caught it; it bites the moment anyone
    follows the cap's own error message and tunes it down.
    """


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
        # AdmissionRejected: an out-of-charset identifier is a correct refusal of the
        # WRITE, not evidence of a broken store (message text unchanged).
        raise AdmissionRejected(
            f"invalid {label} {value!r}: must match [{IDENTIFIER_CHARSET}] (1-256 chars){extra}")


def validate_write_identifiers(subject_predicate, subject_type, subject_name,
                               relation, object_type, object_name) -> None:
    """Reject any out-of-charset identifier on a tuple write (shared by both backends).

    Types and relations must be plain identifiers; names may be the wildcard ``'*'``; the
    subject predicate may be the bare ``'...'`` (or ``Ellipsis``). Every field must be a
    ``str`` (``Ellipsis`` aside): ``None``, ``int``, ``bytes`` are refused in EVERY
    field, the subject predicate included (TK125) -- call this on the RAW argument,
    before ``norm_pred``, which would turn a ``None`` predicate into ``'...'``."""
    _require(subject_type, 'subject_type')
    _require(relation, 'relation')
    _require(object_type, 'object_type')
    _require(subject_name, 'subject_name', allow_star=True)
    _require(object_name, 'object_name', allow_star=True)
    _require(subject_predicate, 'subject_predicate', allow_ellipsis=True)


def validate_store_id(store_id, label: str = 'store_id') -> None:
    """A store id must be a ``str`` with at least one non-whitespace character (TK127
    follow-up, 2026-10-08, pinned by ``tests/test_tk127_store_id.py``).

    Called first by every constructor that takes a store id and can persist under it
    (``ConnectedStore``, ``TupleSource``, ``SetEngine``, ``ReachabilityIndex``) and by
    ``save_schema``, so the refusal precedes any statement. ``None`` used to reach the
    NOT NULL ``store_id`` column as a raw ``IntegrityError``; ``5``, ``b'x'``, ``''`` and
    ``' '`` were accepted as ids no caller meant. The identifier CHARSET is deliberately
    NOT applied: a store id is the caller's key (``tenant:acme``, a UUID), not a tuple
    field. ``AdmissionRejected`` because it is a correct refusal of the caller's input,
    never a sign of a broken store."""
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


class UnsupportedByGraphIndex(Exception):
    """A schema construct (``and`` / ``but not``) the graph index cannot represent.

    Raised by ``compile_ruleset`` naming the offending relation. The set-engine
    backend handles these; the closure-materialising graph index does not.
    """


class DoublyBridgedShapeError(UnsupportedByGraphIndex):
    """A shape that is BOTH a wildcard-userset shape (``T:*#p`` restriction ->
    ``bridged_in_shapes``) and an object-wildcard shape (``bridged_out_shapes``)
    -- the "doubly-bridged" precondition of the F1/F2 divergences (see
    docs/spec-deviations.md 2026-07-17). A wildcard write on such a shape
    materializes a ``w_any(T,p) -> w_all(T,p)`` path; every present-or-future
    concrete node of that shape carries both bridges (concrete->w_any in-bridge,
    w_all->concrete out-bridge), so the path is a latent cycle -- the graph
    accepts the wildcard write then permanently REJECTS every later innocent
    concrete write of that shape (accept/reject + completeness divergences vs the
    set engine, plus an innocent-write lockout).

    A subclass of ``UnsupportedByGraphIndex`` (the third entry in the
    decision-15 scope-rejection family), but its OWN type so the set engine can
    re-raise it -- unlike the other scope rejections, which the set engine
    swallows to degrade to a ruleset-less/oracle-only mode, this one must reject
    on BOTH backends identically (the state must be unconstructible everywhere)."""


class CyclicDerivedDependency(ValueError):
    """Derived relations form a dependency cycle (boolean spec §1.9 forbids
    recursion through boolean relations). A ``ValueError`` subclass for backwards
    compatibility, but its OWN type so graph-optional consumers (ParityEngine,
    the set engine's cycle-parity compile) can degrade on exactly this rejection
    without swallowing every other ``ValueError`` a compile regression might
    raise."""
