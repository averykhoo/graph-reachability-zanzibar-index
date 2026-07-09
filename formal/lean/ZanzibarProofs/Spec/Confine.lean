import ZanzibarProofs.Spec.Semantics
import ZanzibarProofs.Spec.Stratify

/-!
# Consultation confinement — the store-validity hypothesis and the relevant-atom space

Supporting layer for T0a (`Spec/WellDef.lean`). The fuel-stability theorem is FALSE
over an arbitrary `Store` (see `Spec/Counterexample.lean`): `ttuLeaf` consults `rec`
at the subject type of *stored* tupleset tuples without any restriction check, so an
admission-invalid tuple creates a consultation edge that `exprRefs`/`depEdges` never
see — and such an edge can close an exclusion cycle that stratification misses,
making `semAux` oscillate forever.

The fix is the *documented* precondition (`SEMANTICS.md` §8: stores hold write-valid
tuples): the real system's admission gate (`setengine/engine.py:_validate` step (2),
shared with the graph backend) rejects any tuple that matches no declared type
restriction of its `(object.type, relation)`. `StoreDeclared` below is the piece of
that gate the confinement argument needs: every stored tuple's subject type is among
the declared `Direct`-restriction types of its (declared) relation. It is *implied
by* admission validity, so stating theorems over it keeps them applicable to every
store the composed system can actually hold.

With it, every `rec`-consultation of the evaluator is confined to
`exprRefs S · ×  relevantNames T q` — the finite atom space the T0a convergence
argument counts over.
-/

namespace Zanzibar

/-- Every name occurring in a subject or object position of the store. The
    evaluator only ever consults `rec` at stored names (grants' subject names,
    `instances` witnesses, TTU parents) or at the query object's own name. -/
def storedNames (T : Store) : List String :=
  T.flatMap (fun t => [t.subject.name, t.object.name])

/-- The names the evaluation of `q` over `T` can ever consult `rec` at:
    the query object's name (kept by `computed` steps) plus the stored names. -/
def relevantNames (T : Store) (q : Query) : List String :=
  q.object.name :: storedNames T

/-- **Store admission-validity (the type-restriction clause).** Every stored tuple's
    `(object.type, relation)` is a declared relation whose definition names the
    tuple's subject type in one of its `Direct` restrictions.

    This is implied by the Python admission gate (`engine.py:_validate` (2): a write
    matching no declared type restriction raises), so every store the composed
    system can hold satisfies it. It is exactly what confines `ttuLeaf`'s parent
    consultations to `exprRefs`: without it the consultation graph can leave the
    dependency graph and T0a is FALSE (`Spec/Counterexample.lean`). -/
def StoreDeclared (S : Schema) (T : Store) : Prop :=
  ∀ tup ∈ T, ∃ e, S.lookup (tup.object.type, tup.relation) = some e ∧
    tup.subject.type ∈ directTypes e

end Zanzibar
