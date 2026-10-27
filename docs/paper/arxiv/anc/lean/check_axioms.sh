#!/usr/bin/env bash
# Build the library and check every declaration the paper names: each must elaborate and depend
# only on the axioms propext, Classical.choice and Quot.sound.
# Prerequisites: elan (https://github.com/leanprover/elan); run from this directory.
#   lake exe cache get    # prebuilt mathlib for the pinned release (once)
#   ./check_axioms.sh
set -euo pipefail
cd "$(dirname "$0")"
lake build
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
check() {   # check FILE DECLARATION...
  local file="$1"; shift
  cp "Paper/$file" "$tmp/$file"
  for d in "$@"; do printf '\n#print axioms %s\n' "$d" >> "$tmp/$file"; done
  lake env lean "$tmp/$file"
}
lake env lean Paper/LibraryAxioms.lean
check PathGraph.lean Empiricist.pathGraph_min_fusions
check Star.lean Empiricist.star_min_fusions
check Complete.lean Empiricist.complete_min_fusions
check CompleteBipartite.lean Empiricist.completeBipartite_min_fusions
check FloorBridge.lean Empiricist.floor_schedule_iff_dh
