#!/usr/bin/env bash
# Build the paper two ways and assemble the arXiv upload bundle.
#   1. tectonic (main.pdf for reading)
#   2. pdflatex + bibtex from TeX Live 2026 (what arXiv runs), in a clean copy, producing main.bbl
#   3. arxiv_source.tar.gz (main.tex, main.bbl, refs.bib, anc/) as a USTAR archive with
#      uid/gid 0 and no extended attributes, then an isolated pdflatex rebuild from the bundle
#      alone (arXiv does not run BibTeX, so the shipped main.bbl must suffice).
# Fails on undefined references or citations, overfull boxes, non-ASCII source, or a page-count
# mismatch between the tectonic and pdflatex builds.
set -euo pipefail
cd "$(dirname "$0")"
TEXBIN="${TEXBIN:-$HOME/Library/TinyTeX/bin/universal-darwin}"
PDFLATEX="$TEXBIN/pdflatex"
BIBTEX="$TEXBIN/bibtex"
for tool in "$PDFLATEX" "$BIBTEX"; do [[ -x "$tool" ]] || { echo "missing $tool (set TEXBIN)"; exit 1; }; done
command -v tectonic >/dev/null || { echo "missing tectonic"; exit 1; }

echo "== ASCII check"
if LC_ALL=C grep -n '[^ -~	]' main.tex refs.bib; then echo "non-ASCII characters above"; exit 1; fi

echo "== supplement manifest"
( cd anc && find . -type f ! -name SHA256SUMS ! -name '.DS_Store' ! -path '*/__pycache__/*' | LC_ALL=C sort \
    | xargs shasum -a 256 > SHA256SUMS )

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

echo "== tectonic"
mkdir -p "$work/tectonic"
cp main.tex refs.bib "$work/tectonic/"
( cd "$work/tectonic" && tectonic -X compile main.tex > tectonic.log 2>&1 ) || { cat "$work/tectonic/tectonic.log"; exit 1; }
cp "$work/tectonic/main.pdf" main.pdf

echo "== pdflatex + bibtex (TeX Live)"
mkdir -p "$work/tl"
cp main.tex refs.bib "$work/tl/"
(
  cd "$work/tl"
  "$PDFLATEX" -interaction=nonstopmode -halt-on-error main.tex > /dev/null
  "$BIBTEX" main > bibtex.log
  "$PDFLATEX" -interaction=nonstopmode -halt-on-error main.tex > /dev/null
  "$PDFLATEX" -interaction=nonstopmode -halt-on-error main.tex > /dev/null
)
cp "$work/tl/main.bbl" main.bbl
check_log() {   # check_log LOGFILE
  local bad=0
  if grep -nE "undefined|Undefined" "$1"; then bad=1; fi
  if grep -n "Overfull" "$1"; then bad=1; fi
  if grep -n "Warning--" "$work/tl/bibtex.log" 2>/dev/null; then bad=1; fi
  return $bad
}
check_log "$work/tl/main.log" || { echo "warnings in the pdflatex build"; exit 1; }

echo "== bundle"
rm -f arxiv_source.tar.gz
COPYFILE_DISABLE=1 tar --format ustar --uid 0 --gid 0 --uname root --gname root --no-xattrs \
  --exclude '.DS_Store' --exclude '__pycache__' -czf arxiv_source.tar.gz main.tex main.bbl refs.bib anc

echo "== isolated rebuild from the bundle (no BibTeX)"
mkdir -p "$work/iso"
tar -xzf arxiv_source.tar.gz -C "$work/iso"
(
  cd "$work/iso"
  "$PDFLATEX" -interaction=nonstopmode -halt-on-error main.tex > /dev/null
  "$PDFLATEX" -interaction=nonstopmode -halt-on-error main.tex > /dev/null
)
check_log "$work/iso/main.log" || { echo "warnings in the isolated build"; exit 1; }

p_tect="$(pdfinfo main.pdf | awk '/^Pages:/ {print $2}')"
p_tl="$(pdfinfo "$work/iso/main.pdf" | awk '/^Pages:/ {print $2}')"
echo "pages: tectonic $p_tect, pdflatex (bundle) $p_tl"
[[ "$p_tect" == "$p_tl" ]] || { echo "page counts differ"; exit 1; }
echo "bundle: $(tar -tzf arxiv_source.tar.gz | wc -l | tr -d ' ') files, $(du -h arxiv_source.tar.gz | cut -f1)"
echo "OK"
