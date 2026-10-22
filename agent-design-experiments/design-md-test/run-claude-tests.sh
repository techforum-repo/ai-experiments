#!/bin/bash
# Runs the three original design-md architecture arms through Claude Code:
# blind (no file), google (Google-shaped DESIGN.md), vercel (Vercel-shaped
# split design.md + stylesheet.css). Each arm runs once, cold -- this is
# the original test design (compare architectures, not repeat one).
#
# The prompts themselves are vendor-neutral (they read from design-systems/
# and say to save to a bare "post.html") -- this script, like
# run-codex-tests.sh, supplies its own explicit output path via an appended
# override. Neither script's vendor name is baked into the shared prompts.
#
# SAFETY: refuses to overwrite an existing post.html by default, since the
# post.html files already in this folder are the real evidence behind the
# published article. Pass --force to overwrite anyway.
#
# Usage: ./run-claude-tests.sh [--force]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

FORCE=false
[ "$1" = "--force" ] && FORCE=true

for arm in blind google vercel; do
  outdir="claude-$arm"
  mkdir -p "$outdir"

  if [ -f "$outdir/post.html" ] && [ "$FORCE" = false ]; then
    echo "SKIPPING $arm: $outdir/post.html already exists. Pass --force to overwrite."
    continue
  fi

  echo "=== Running $arm -> $outdir/post.html ==="
  claude -p "$(cat "$arm-prompt.txt") (Save the finished file to exactly this path instead: $outdir/post.html)" \
    --dangerously-skip-permissions > "$outdir/run.log" 2>&1
  echo "  exit code: $?"
  if [ -f "$outdir/post.html" ]; then
    echo "  post.html written ($(wc -c < "$outdir/post.html") bytes)"
  else
    echo "  WARNING: post.html was not created -- check $outdir/run.log"
  fi
  # The vercel arm's post.html links to stylesheet.css by relative path --
  # copy it alongside so the page actually renders.
  if [ "$arm" = "vercel" ] && [ -f "$outdir/post.html" ]; then
    cp design-systems/vercel/stylesheet.css "$outdir/"
  fi
  echo ""
done

echo "Done. Results are in claude-blind/post.html, claude-google/post.html, claude-vercel/post.html"
echo "Run ./compare3.sh next to verify token adherence against the real design system."
