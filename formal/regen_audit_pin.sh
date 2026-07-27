#!/usr/bin/env bash
# Regenerate formal/audited_theorems.txt -- the IDENTITY pin that formal/verify.sh
# enforces against Audit.lean's `#print axioms` commands (ZT-P2-5).
#
# Deliberate act: a REMOVED name means audited coverage shrank and should be
# justified in formal/history/. Adding names is free (verify.sh asks for a
# SUPERSET), but keeping this file current keeps the failure messages useful.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIN="$ROOT/formal/audited_theorems.txt"
TMP="$(mktemp)"
# Keep the checked-in header (the leading comment/blank block) verbatim.
awk '/^#/ || /^[[:space:]]*$/ {print; next} {exit}' "$PIN" > "$TMP"
grep -oE '^#print axioms [^[:space:]]+' "$ROOT/formal/lean/ZanzibarProofs/Audit.lean" \
  | awk '{print $3}' | LC_ALL=C sort -u >> "$TMP"
mv "$TMP" "$PIN"
echo "wrote $PIN ($(grep -cvE '^#|^[[:space:]]*$' "$PIN") audited theorem names)"
