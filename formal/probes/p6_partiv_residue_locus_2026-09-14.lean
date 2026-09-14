/-
  ★ P6 PART (iv) — WHERE the phantom-subject divergence actually comes from (2026-09-14g).

  WHY. `formal/CORRESPONDENCE.md:1162` §7 records the phantom-userset-subject boundary with
  this mechanism:

  > `GraphIndex/State.lean::GraphModel.check` resolves a derived key through materialised
  > edges, so it needs a node where `index_v4/wildcard.py::WildcardIndex._check_derived`
  > needs none — Python's userset arm answers from the residue's `stars`/`neg`/`upos`
  > symbolically […]

  Reading `State.lean:589::probeDerived` first-hand says that is FALSE for the branch in
  question. The userset-subject arm (`s.predicate != BARE`) is **edge-free** — no `σ.reach`
  anywhere in it — and answers from `res.upos` / `res.stars` / `res.neg`, i.e. exactly the
  symbolic read the note attributes to Python alone. Its own docstring says so: *"A userset
  subject is edge-free"*.

  So the recorded MECHANISM is wrong even though the measured DIVERGENCE is real. That
  matters for `P6` part (iv) step 0's A/A2/B/C choice, because the whole cost estimate for
  A and A2 ("give the Lean model a symbolic derived read") assumed the read path lacks
  something it already has. This probe asks where the gap really is.

  THE QUESTION. In the userset branch the residue is fetched at the OBJECT node
  (`objNode o R`) — `doc:d1`, which IS materialised — and the subject enters only through
  `s.shape` and membership tests. Both the divergent subject `folder:f9#viewer` and the
  agreeing control `folder:f1#viewer` have the SAME shape `("folder", "viewer")`. So
  `res.stars.contains s.shape` cannot be what separates them: if `stars` held that shape,
  BOTH would answer true (absent a `neg` row). The separation must come from `upos`, and
  the residue must be missing the star shape.

  If that is what the numbers say, the gap is in what the CASCADE writes into the derived
  residue's `stars`, NOT in what the read path consults — a write-side gap, and a different
  cone from the one the A/A2 estimate was priced against.

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p6_partiv_residue_locus_2026-09-14.lean

  ⚠ rc=0 with NO output is a FAILED run, not a green one.
  ⚠ INSTRUMENT CONTROL `(I)`: a residue read that comes back empty because the NODE KEY is
    wrong reads exactly like a residue that was never populated. `(I)` demands a NONEMPTY
    residue somewhere in this state before any absence below is believed.

  ── THE VERDICT (2026-09-14g) ──────────────────────────────────────────────────────────────

  **The gap is on the WRITE side. `CORRESPONDENCE.md:1170-1174`'s mechanism is REFUTED.**

  1. `(1)`: `access` is NOT derived; `admin`/`gate` are. So `access` routes to
     `probeNonDerived` (the edge probe the star bridge serves) and the two divergent
     relations route to `probeDerived` (the residue path). That is the whole of the
     "plain agrees, derived diverges" asymmetry — two different read paths, not one path
     failing at a missing node.
  2. `(3)`/`(4)`: the residue at `(doc:d1, admin)` is `stars := []`, `neg := []`,
     `upos := [folder:f2#viewer, folder:f1#viewer]`. **`stars` is EMPTY.**
  3. `(2)` + `(6)`: the phantom and the control share the shape `("folder","viewer")`, so
     `res.stars.contains s.shape` is `false` for BOTH and could never have separated them.
     What separates them is `upos` — `false` for the phantom, `true` for the control. `neg`
     is empty and irrelevant to this divergence.
  4. Therefore the userset branch of `probeDerived` behaved CORRECTLY given its input. It
     is edge-free, it consulted the residue symbolically, and the residue it was handed
     simply did not contain the star shape. **The defect is in what the cascade WROTE into
     the derived residue's `stars`, not in what the read path consults.**
  5. `(8)`: `(doc:d1, access)` has NO residue at all (`none`) — consistent with `(1)`,
     since a non-derived relation has none. So the star coverage that makes `access`
     answer true at the phantom lives in the EDGE structure, and the cascade never lifted
     it into the derived residue above it.

  ⚠ **Consequence for step 0's A/A2/B/C menu: it was priced against a mechanism that is not
  real.** A and A2 were both phrased as *"give the Lean model a symbolic derived read"* —
  the model already HAS one (`State.lean:589`, and its own docstring says *"A userset
  subject is edge-free"*). So the `CORRESPONDENCE.md:1184` cost note *"a project, not a
  step"* is pricing work that does not need doing. Do not pick from that menu.

  ⚠ **What this probe does NOT establish.** It locates the gap; it does not measure the fix.
  Whether the star fold CAN produce `("folder","viewer")` here, and what that costs, is
  unmeasured. Nor does it re-derive WHY Python answers true — the shipped-backend result is
  `p6_phantom_subject_2026-09-13.py` (re-run 2026-09-14g, UNANIMOUS), and this probe does
  not open `WildcardIndex._check_derived` to say which of its arms does it.

  ── LITERAL TRANSCRIPT (the run's own stdout; nothing added, removed or reordered) ─────────

  RAN 2026-09-14g, rc=0, from `formal/lean` via
  `export PATH="$HOME/.elan/bin:$PATH" && lake env lean ../probes/p6_partiv_residue_locus_2026-09-14.lean`.

  --------------------------------- BEGIN VERBATIM -----------------------------------------

("(1) isDerived (access, admin, gate) -- who routes to probeDerived", false, true, true)
("(2) the two subjects share a SHAPE (phantom, control, equal?)", ("folder", "viewer"), ("folder", "viewer"), true)
("(3) ★ residue at (doc:d1, admin)",
 some { stars := [],
   neg := [],
   upos := [{ type := "folder", name := "f2", predicate := "viewer" },
            { type := "folder", name := "f1", predicate := "viewer" }] })
("(4) ★ residue at (doc:d1, gate)",
 some { stars := [],
   neg := [],
   upos := [{ type := "folder", name := "f2", predicate := "viewer" },
            { type := "folder", name := "f1", predicate := "viewer" },
            { type := "folder", name := "f2", predicate := "viewer" },
            { type := "folder", name := "f1", predicate := "viewer" }] })
("(I) INSTRUMENT CONTROL -- residues across all five relations at doc:d1; MUST be nonempty somewhere or (3)/(4) mean nothing",
 some [("access", none),
  ("admin",
   some { stars := [],
     neg := [],
     upos := [{ type := "folder", name := "f2", predicate := "viewer" },
              { type := "folder", name := "f1", predicate := "viewer" }] }),
  ("gate",
   some { stars := [],
     neg := [],
     upos := [{ type := "folder", name := "f2", predicate := "viewer" },
              { type := "folder", name := "f1", predicate := "viewer" },
              { type := "folder", name := "f2", predicate := "viewer" },
              { type := "folder", name := "f1", predicate := "viewer" }] }),
  ("banned", none),
  ("parent", none)])
("(5) ★ probeDerived at admin (phantom, control)", some (false, true))
("(6) ★ the three membership tests the userset branch makes, at (doc:d1, admin): (upos phantom, upos control, stars has shape, neg phantom, neg control)",
  some (false, true, false, false, false))
("(7) sem vs check at the phantom subject, admin and access side by side",
  some [("admin", false, true), ("access", true, true)])
("(8) residue at (doc:d1, access) -- is the star shape present ONE LEVEL DOWN?", none)

  ---------------------------------- END VERBATIM ------------------------------------------

  INSTRUMENT CONTROL `(I)` PASSED: `admin` and `gate` both return a NONEMPTY residue, so the
  node key is right and the empty `stars` at `(3)`/`(4)` is a real absence rather than a
  misread. Without it, `stars := []` would have been indistinguishable from reading a key
  that does not exist.

-/
import ZanzibarProofs

open Zanzibar

namespace P6PartIvResidueLocus

/-! ## §1 The store — copied VERBATIM from `p6_partiv_live_leg_payoff_2026-09-14.lean` §1,
so every number here is comparable to that probe's `(4)`/`(5)`. -/

def Sp : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"),    .direct [("folder", BARE, true)]),
    (("doc", "access"),    .ttu "viewer" "parent"),
    (("doc", "banned"),    .direct [("user", BARE, false), ("folder", "viewer", false)]),
    (("doc", "admin"),     .excl (.computed "access") (.computed "banned")),
    (("doc", "gate"),      .inter (.computed "admin") (.computed "access"))], []⟩

def tPar : Tuple := ⟨⟨"folder", STAR, BARE⟩, "parent", ⟨"doc", "d1"⟩⟩
def tView : Tuple := ⟨⟨"user", "alice", BARE⟩, "viewer", ⟨"folder", "f1"⟩⟩
def tObj : Tuple := ⟨⟨"user", "bob", BARE⟩, "viewer", ⟨"folder", "f2"⟩⟩

def prefixOps : List GraphOp := [GraphOp.add tPar, GraphOp.add tView]

/-- The live post-(ii) state and its store, exactly as the payoff probe builds them. -/
def live : Option (GraphState × Store) :=
  (graphRunOps Sp prefixOps).map (fun p =>
    let To := tObj :: p.2
    (cascadeLeg Sp To (p.1.writeLoggedRules Sp tObj), To))

/-! ## §2 Which relations take the residue path at all? -/

#eval ("(1) isDerived (access, admin, gate) -- who routes to probeDerived",
        isDerived Sp ("doc", "access"),
        isDerived Sp ("doc", "admin"),
        isDerived Sp ("doc", "gate"))

/-! ## §3 The two subjects, and the claim that they share a shape -/

def sPhantom : SubjectRef := ⟨"folder", "f9", "viewer"⟩
def sControl : SubjectRef := ⟨"folder", "f1", "viewer"⟩

#eval ("(2) the two subjects share a SHAPE (phantom, control, equal?)",
        sPhantom.shape, sControl.shape, sPhantom.shape == sControl.shape)

/-! ## §4 ★ THE RESIDUE at the object node the userset branch actually reads -/

def resAt (R : String) : Option Residue :=
  live.bind (fun p => p.1.residue (objNode ⟨"doc", "d1"⟩ R) R)

#eval ("(3) ★ residue at (doc:d1, admin)", resAt "admin")
#eval ("(4) ★ residue at (doc:d1, gate)",  resAt "gate")

/-! ## §5 INSTRUMENT CONTROL — is ANY residue nonempty in this state?

An absence at `(3)`/`(4)` is only evidence if the residue map is being read correctly at
all. If every key in this state returns `none`/empty, the probe is measuring a wrong node
key, not a cascade gap. This is the `M0`-shaped control `docs/sabotage-procedure.md`
requires: it must come back NONEMPTY. -/

def allResidues : Option (List (String × Option Residue)) :=
  live.map (fun p =>
    ["access", "admin", "gate", "banned", "parent"].map
      (fun R => (R, p.1.residue (objNode ⟨"doc", "d1"⟩ R) R)))

#eval ("(I) INSTRUMENT CONTROL -- residues across all five relations at doc:d1; " ++
       "MUST be nonempty somewhere or (3)/(4) mean nothing", allResidues)

/-! ## §6 The read itself, traced at both subjects -/

def qAt (s : SubjectRef) (R : String) : Query := ⟨s, R, ⟨"doc", "d1"⟩⟩

#eval ("(5) ★ probeDerived at admin (phantom, control)",
        live.map (fun p => (GraphModel.probeDerived p.1 (qAt sPhantom "admin"),
                            GraphModel.probeDerived p.1 (qAt sControl "admin"))))

#eval ("(6) ★ the three membership tests the userset branch makes, at (doc:d1, admin): " ++
       "(upos phantom, upos control, stars has shape, neg phantom, neg control)",
        (resAt "admin").map (fun res =>
          (res.upos.contains sPhantom, res.upos.contains sControl,
           res.stars.contains sPhantom.shape,
           res.neg.contains sPhantom, res.neg.contains sControl)))

/-! ## §7 The star shape the cascade would have had to fold in

If `(6)` says `stars` lacks `("folder","viewer")`, this is the value that is missing and
the question becomes why the star fold did not produce it. `access` is the TTU relation the
star bridge serves, and the payoff probe's `(12)` says it answers TRUE at the phantom
subject — so the material is present one level down. -/

#eval ("(7) sem vs check at the phantom subject, admin and access side by side",
        live.map (fun p =>
          [("admin", GraphModel.check p.1 (qAt sPhantom "admin"), sem Sp p.2 (qAt sPhantom "admin")),
           ("access", GraphModel.check p.1 (qAt sPhantom "access"), sem Sp p.2 (qAt sPhantom "access"))]))

#eval ("(8) residue at (doc:d1, access) -- is the star shape present ONE LEVEL DOWN?",
        resAt "access")

end P6PartIvResidueLocus
