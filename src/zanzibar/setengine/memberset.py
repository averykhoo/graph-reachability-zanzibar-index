"""
``MemberSet`` -- the star-closed set algebra (spec §4).

Plain bitmaps cannot represent "all users except bob". A ``MemberSet`` closes the
representation over subject wildcards:

    pos    concrete member ids
    stars  covered star SHAPES (type, predicate), intensional -- '...' predicate for a
           bare entity, a relation name for a userset. Ghost-safe: coverage of an entity
           never mentioned in any tuple is decided by shape membership, not by population.
    neg    exclusions, meaningful only within starred shapes

Extensional meaning over a population ``pop(shape) -> ids``:

    ext(M) = pos ∪ ( (⋃ pop(shape) for shape in stars) − neg )        # pos wins over neg

Every operation reduces to one provably-correct recipe: compute the target extensional
set ``E`` and target star set ``S`` for the operation, then renormalize

    starpop = ⋃ pop(shape) for shape in S
    pos = E − starpop      # ids only representable explicitly
    neg = starpop − E      # starred ids that must be excluded

which restores ``ext = E`` exactly while keeping ``stars = S`` for intensional queries.
The star bookkeeping per op mirrors the §3 star × boolean table:

    union     S = stars_a | stars_b        (covered if either)
    intersect S = stars_a & stars_b        (covered iff both)          -- '*' ∈ A∧B
    subtract  S = stars_a - stars_b        (covered in A, not in B)    -- '*' ∈ A−B

This module has NO engine dependencies (spec §4); it is validated by a brute-force
property suite under both ``SetOps`` implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .setops import SetOps

Shape = tuple[str, str]                       # (type, predicate); '...' for bare entity
Population = Callable[[Shape], Iterable[int]] # shape -> its concrete member ids


@dataclass(frozen=True)
class MemberSet:
    pos: object                               # FrozSet: concrete member ids
    stars: frozenset                          # covered star shapes (intensional)
    neg: object                               # FrozSet: exclusions within starred shapes

    # --- membership (all intensional in `stars`, so ghost-safe) ---

    def contains_star(self, shape: Shape) -> bool:
        return shape in self.stars

    def _contains(self, uid: int, shape: Shape) -> bool:
        return uid in self.pos or (shape in self.stars and uid not in self.neg)

    def contains_entity(self, uid: int, utype: str) -> bool:
        # a concrete entity is covered by the BARE star of its type
        return self._contains(uid, (utype, '...'))

    def contains_userset(self, uid: int, shape: Shape) -> bool:
        return self._contains(uid, shape)


def empty(ops: SetOps) -> MemberSet:
    return MemberSet(ops.freeze(), frozenset(), ops.freeze())


def singleton_entity(uid: int, ops: SetOps) -> MemberSet:
    return MemberSet(ops.freeze((uid,)), frozenset(), ops.freeze())


def star(shape: Shape, ops: SetOps) -> MemberSet:
    return MemberSet(ops.freeze(), frozenset((shape,)), ops.freeze())


# ---------------------------------------------------------------------------
# Internal: extensional materialisation + renormalisation
# ---------------------------------------------------------------------------

def _starpop(stars, ops: SetOps, pop: Population):
    acc = ops.new()
    for shape in stars:
        # ops.update NORMALISES without copying: the Population contract only
        # promises an iterable of ids (tests pass plain tuples), so `acc |=
        # pop(shape)` would break on a non-ops iterable. The old `acc |=
        # ops.new(pop(shape))` normalised by copying the whole O(population) mask
        # per star shape just to union it in; the SetOps.update primitive folds
        # any iterable straight into acc in place -- O(result), not O(population)
        # (P10; twin of the direct_expand copy fixed in 78cfc2f).
        ops.update(acc, pop(shape))
    return acc


# INVARIANT (N4): MemberSet.pos/neg are ALWAYS ops.freeze() outputs (verified at
# every construction site). Nothing enforces this at runtime -- the 3000-case
# homomorphism/ghost-safety property test (tests/test_memberset.py, both SetOps)
# is the net. It licenses the copy-free `-=`/`|=` below: both backends' mutable
# type accepts the frozen type directly as an operand (`set` vs `frozenset`,
# `BitMap` vs `FrozenBitMap`), so the old defensive `ops.new(...)` wraps around
# m.neg/m.pos/ext_set/starpop were pure O(set) copies (~7 per algebra op -> 1;
# same copy class as _starpop's P10 fix and direct_expand's 78cfc2f).

def _ext(m: MemberSet, ops: SetOps, pop: Population):
    """ext(M) = pos ∪ (starpop − neg), as a fresh mutable set."""
    acc = _starpop(m.stars, ops, pop)          # already fresh & owned
    acc -= m.neg                               # frozen operand read directly
    acc |= m.pos                               # pos wins over neg
    return acc


def _normalize(ext_set, stars, ops: SetOps, pop: Population) -> MemberSet:
    # ext_set is caller-owned: READ only, never mutated. starpop is fresh & owned,
    # so we reuse it in place as the `neg` accumulator. Order is load-bearing:
    # `pos -= starpop` must read starpop BEFORE `starpop -= ext_set` mutates it.
    starpop = _starpop(stars, ops, pop)
    pos = ops.new(ext_set)
    pos -= starpop                             # ids not covered by any star population
    starpop -= ext_set                         # reuse as neg: starred ids to exclude
    return MemberSet(ops.freeze(pos), frozenset(stars), ops.freeze(starpop))


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def union(a: MemberSet, b: MemberSet, ops: SetOps, pop: Population) -> MemberSet:
    e = _ext(a, ops, pop)
    e |= _ext(b, ops, pop)
    return _normalize(e, a.stars | b.stars, ops, pop)


def intersect(a: MemberSet, b: MemberSet, ops: SetOps, pop: Population) -> MemberSet:
    e = _ext(a, ops, pop)
    e &= _ext(b, ops, pop)
    return _normalize(e, a.stars & b.stars, ops, pop)


def subtract(a: MemberSet, b: MemberSet, ops: SetOps, pop: Population) -> MemberSet:
    e = _ext(a, ops, pop)
    e -= _ext(b, ops, pop)
    return _normalize(e, a.stars - b.stars, ops, pop)


def materialize(m: MemberSet, ops: SetOps, pop: Population) -> frozenset:
    """Extensional set over the known population (star ⇒ whole population). Test/debug aid."""
    return frozenset(_ext(m, ops, pop))
