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
import ZanzibarProofs.Spec.WellDef

-- Set-engine model + T1
import ZanzibarProofs.SetEngine.MemberSet
import ZanzibarProofs.SetEngine.Algebra
import ZanzibarProofs.SetEngine.Eval
import ZanzibarProofs.SetEngine.Correct

-- Graph-index model + T2/T4/T5
import ZanzibarProofs.GraphIndex.Closure
import ZanzibarProofs.GraphIndex.State
import ZanzibarProofs.GraphIndex.Correct

-- Equivalence T3 + security T6
import ZanzibarProofs.Equiv
