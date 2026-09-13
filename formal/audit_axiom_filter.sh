#!/bin/sh
# formal/audit_axiom_filter.sh -- the axiom-allowlist filter for `verify.sh`'s step 4.
#
# Reads raw `lake build` output on stdin; prints the OFFENDING `#print axioms` report
# lines. EMPTY OUTPUT MEANS CLEAN. Allowed axioms are exactly propext,
# Classical.choice and Quot.sound (`verify.sh` step 4's header says why).
#
# WHY THIS IS A SEPARATE FILE AND NOT A PIPELINE INSIDE verify.sh (2026-09-13e, TK68).
# It used to be two inline `grep`s, and the second was anchored `\]$`. **Lean WRAPS a
# `#print axioms` message at ~100 columns**, so a sufficiently long declaration name
# pushes the axiom list onto continuation lines and the head line ends `[propext,` with
# no closing bracket. The allowlist then failed to match and the gate reported
# "non-standard axioms in the audit" for a theorem whose axioms are the standard three.
# Observed verbatim, on `W4Witness.sxThruDerived_other_admission_fields_hold`:
#
#     info: ZanzibarProofs/Audit.lean:1204:0: '...sxThruDerived_other_admission_fields_hold' depends on axioms: [propext,
#      Classical.choice,
#      Quot.sound]
#
# ⚠ **That is a guard reddening on a BENIGN input, which is how a guard gets relaxed.**
# The tempting repair is to loosen the allowlist regex (drop the `$` anchor, or match
# `[propext` as a prefix) -- and that would make the guard blind to a wrapped list whose
# TAIL carries `sorryAx`, i.e. exactly the axiom the audit exists to catch. So the fix is
# to REJOIN the wrapped line first and keep the allowlist anchored and exact.
#
# The join is deliberately narrow: it accumulates only while a line that already matched
# `depends on axioms` has no closing `]`, and stops at the first one. It therefore cannot
# glue unrelated build chatter (`✔ [n/m] Built ...`) onto a report line, which a
# general "join any indented line" rule would.
#
# Pinned by `tests/test_gate_axiom_filter.py`, which runs THIS script -- not a
# reimplementation of it -- against synthetic audit output, wrapped and unwrapped, clean
# and dirty. The mutation table is in that module's docstring.
awk '
  {
    if (pend != "") {
      pend = pend $0
      if (pend ~ /\]$/) { print pend; pend = "" }
      next
    }
    if ($0 ~ /depends on axioms/ && $0 !~ /\]$/) { pend = $0; next }
    print $0
  }
  END { if (pend != "") print pend }
' | grep -iE "depends on axioms" \
  | grep -vE "\[(propext|Classical\.choice|Quot\.sound)(, (propext|Classical\.choice|Quot\.sound))*\]$" || true
