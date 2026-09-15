/-
  DIAGNOSTIC scratch for `p6_partiv_stepC_grid_2026-09-15.lean` — why did CONTROL b fail?

  The grid probe's first run gave `storeValidRulesB S corpus = false` and a CONTROL b whose
  mismatch was `4`, not `0`.  A failed control means the INSTRUMENT is broken, so no number
  from that run is evidence yet.  This file isolates the two suspects:

    (a) which tuple makes `storeValidRules` false, and
    (b) whether the mismatching query `folder:f3 ∈ doc:d2#parent` is a real divergence or a
        query on the TUPLESET STORAGE relation, which the graph deliberately does not answer.

  Run from `formal/lean`:
      lake env lean ../probes/p6_partiv_stepC_diag_2026-09-15.lean

  ── THE VERDICT ───────────────────────────────────────────────────────────────────────────

  **BOTH SUSPECTS CONFIRMED, AND THEY ARE THE SAME SUSPECT.**  `WideWitness.SwT` declares
  `doc#parent`'s restriction as the WILDCARD form `[folder:*]` only, so a CONCRETE folder
  subject on `parent` satisfies no restriction and the store is not valid:
  `storeValidRulesB SwT [tConcPar] = false`, and likewise for a concrete parent on `doc:d1`
  (a1) — while the STAR parent is fine (`true`).  At such a tuple `sem` correctly answers
  `false` (the tuple is not admissible) but `GraphModel.check` answers `true` on BOTH write
  legs, because the write path materialises the edge regardless (b2, b4).  That is a
  store-validity violation showing up as an apparent divergence, on every leg at once, and it
  is what made the (C) grid's first-draft CONTROL b read `4` instead of `0`.

  ⚠ The contamination is confined to queries about the TUPLESET relation itself.  At the
  DERIVED query on the same invalid store, all three agree (b3: `true, true, true`) — which
  is why a probe that asks only the derived query, as
  `p6_partiv_step3_rulerouted_2026-09-15.lean` does, sees a clean control and is not wrong,
  merely weaker than it looks.  `p6_partiv_stepC_grid_2026-09-15.lean` §8 records that.

  THE FIX, applied there: the concrete-parent control belongs on `WideWitness.SwTn`
  (`TtuStarWide.lean:343`, 2026-09-15 line snapshot), the sibling witness whose one-restriction
  delta is `[folder]` instead of `[folder:*]`.

  ── VERBATIM TRANSCRIPT (2026-09-15, rc=0) ────────────────────────────────────────────────

  ("(a1) storeValidRules per singleton: starPar, concPar(d2), concP1(d1), gU, gV, gW", true, false, false, true, true, true)
  ("(a2) ★ the declared keys ...", [("folder", "viewer"), ("doc", "parent"), ("doc", "access")])
  ("(b1) minimal concrete store: storeValidRules / ttuStarFree narrow", false, true)
  ("(b2) ★ qPar (the tupleset storage relation): sem / check-plain / check-bridged", false, true, true)
  ("(b3) CONTROL -- qAcc (the DERIVED relation) on the same store: sem / plain / bridged", true, true, true)
  ("(b4) the edges of the minimal concrete store, plain leg", [3 edges; folder:f3#... -> doc:d2#parent is present])
  ("(b5) is `parent` a storage leaf? schemaRewrites / the doc#parent rule",
   [{ objectType := "doc", matchRel := "parent", outRel := "access", kind := RuleKind.ttu "viewer" }])

  ----------------------------------- END VERBATIM -----------------------------------------
-/
import ZanzibarProofs

open Zanzibar

namespace P6PartIvStepCDiag

abbrev S : Schema := WideWitness.SwT

def tStarPar : Tuple := WideWitness.twT
def tConcPar : Tuple := ⟨⟨"folder", "f3", BARE⟩, "parent", ⟨"doc", "d2"⟩⟩
def tConcP1  : Tuple := ⟨⟨"folder", "f1", BARE⟩, "parent", ⟨"doc", "d1"⟩⟩
def gU       : Tuple := ⟨⟨"user", "u", BARE⟩, "viewer", ⟨"folder", "f1"⟩⟩
def gV       : Tuple := ⟨⟨"user", "v", BARE⟩, "viewer", ⟨"folder", "f2"⟩⟩
def gW       : Tuple := ⟨⟨"user", "w", BARE⟩, "viewer", ⟨"folder", "f3"⟩⟩

/-! ## (a) WHICH TUPLE breaks `storeValidRules`? One singleton store per tuple. -/

#eval ("(a1) storeValidRules per singleton: starPar, concPar(d2), concP1(d1), gU, gV, gW",
        storeValidRulesB S [tStarPar], storeValidRulesB S [tConcPar],
        storeValidRulesB S [tConcP1], storeValidRulesB S [gU],
        storeValidRulesB S [gV], storeValidRulesB S [gW])

#eval ("(a2) ★ the declared keys -- `doc#parent` is `[folder:*]`, the WILDCARD form only, which is why a concrete parent is not store-valid here", S.keys)

/-! ## (b) The mismatching query, in isolation

`folder:f3 ∈ doc:d2#parent` asks about the TUPLESET STORAGE relation itself.  If `sem`
answers `true` (the tuple is stored) and `GraphModel.check` answers `false` on EVERY write
model, the divergence is the storage-leaf split, not the missing in-bridge — and such queries
must be excluded from, or accounted for in, the (C) grid. -/

def build (S : Schema) : Store → GraphState
  | [] => emptyState S
  | t :: rest => (build S rest).writeRules S t

def buildL (S : Schema) : Store → GraphState
  | [] => emptyState S
  | t :: rest => (buildL S rest).writeRulesRaw S t

def qPar : Query := ⟨⟨"folder", "f3", BARE⟩, "parent", ⟨"doc", "d2"⟩⟩
def qAcc : Query := ⟨⟨"user", "w", BARE⟩, "access", ⟨"doc", "d2"⟩⟩

def Tmin : Store := [tConcPar, gW]   -- a CONCRETE parent only: no star anywhere

#eval ("(b1) minimal concrete store: storeValidRules / ttuStarFree narrow",
        storeValidRulesB S Tmin, ttuStarFreeB S Tmin)
#eval ("(b2) ★ qPar (the tupleset storage relation): sem / check-plain / check-bridged",
        sem S Tmin qPar, GraphModel.check (build S Tmin) qPar,
        GraphModel.check (buildL S Tmin) qPar)
#eval ("(b3) CONTROL -- qAcc (the DERIVED relation) on the same store: sem / plain / bridged",
        sem S Tmin qAcc, GraphModel.check (build S Tmin) qAcc,
        GraphModel.check (buildL S Tmin) qAcc)
#eval ("(b4) the edges of the minimal concrete store, plain leg", (build S Tmin).edges)
#eval ("(b5) is `parent` a storage leaf? schemaRewrites / the doc#parent rule",
        schemaRewrites S)

end P6PartIvStepCDiag
