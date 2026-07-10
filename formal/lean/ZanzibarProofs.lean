-- Root aggregator for the ZanzibarProofs library.
-- Import every module so `lake build` checks the whole development.

-- Core domain
import ZanzibarProofs.Core.Ident
import ZanzibarProofs.Core.Refs
import ZanzibarProofs.Core.Schema
import ZanzibarProofs.Core.Store

-- Specification
import ZanzibarProofs.Spec.Semantics
import ZanzibarProofs.Spec.Stratify
import ZanzibarProofs.Spec.Confine
import ZanzibarProofs.Spec.FuelStable
import ZanzibarProofs.Spec.WellDef
import ZanzibarProofs.Spec.Counterexample

-- Set-engine model + T1
import ZanzibarProofs.SetEngine.MemberSet
import ZanzibarProofs.SetEngine.Algebra
import ZanzibarProofs.SetEngine.Contains
import ZanzibarProofs.SetEngine.Eval
import ZanzibarProofs.SetEngine.Correct

-- Graph-index model + T2/T4/T5
import ZanzibarProofs.GraphIndex.Closure
import ZanzibarProofs.GraphIndex.State
import ZanzibarProofs.GraphIndex.Write
import ZanzibarProofs.GraphIndex.DirectCorrect
import ZanzibarProofs.GraphIndex.BareStarCorrect
import ZanzibarProofs.GraphIndex.ObjStarWrite
import ZanzibarProofs.GraphIndex.ObjStarCorrect
import ZanzibarProofs.GraphIndex.ObjStarClosure
import ZanzibarProofs.GraphIndex.UsStarWrite
import ZanzibarProofs.GraphIndex.UsStarCorrect
import ZanzibarProofs.GraphIndex.UsStarClosure
import ZanzibarProofs.GraphIndex.RulesWrite
import ZanzibarProofs.GraphIndex.RulesCorrect
import ZanzibarProofs.GraphIndex.RulesSound
import ZanzibarProofs.GraphIndex.Correct

-- Equivalence T3 + security T6
import ZanzibarProofs.Equiv
