#!/bin/sh

src="$(pandoc --dump-args "$@" | head -n 2 | tail -n 1)"

src_dir="./$(dirname "$src")"
src_dir="$(cd "$src_dir" && pwd)" || exit 1

fix_dir="$(dirname "$src_dir")/fixtures"
fix_dir="$(cd "$fix_dir" && pwd)" || exit 1

pandoc \
  --resource-path="$src_dir" \
  --metadata-file="$fix_dir/meta.macos.yaml" \
  --include-in-header="$fix_dir/headers.tex" \
  --citeproc \
  --bibliography="$fix_dir/references.bib" \
  --csl="$fix_dir/references.csl" \
  --pdf-engine=lualatex \
  "$@"
