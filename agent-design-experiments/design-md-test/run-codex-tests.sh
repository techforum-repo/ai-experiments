#!/bin/bash
# Runs the three original design-md architecture arms through Codex:
# blind (no file), google (Google-shaped DESIGN.md), vercel (Vercel-shaped
# split design.md + stylesheet.css). Each arm runs once, cold -- this is
# the original test design (compare architectures, not repeat one).
#
# Requires the Codex CLI (codex) installed and authenticated
# (npm install -g @openai/codex, then run `codex` once to sign in).
#
# The prompts themselves are vendor-neutral (they read from design-systems/
# and say to save to a bare "post.html") -- this script, like
# run-claude-tests.sh, supplies its own explicit output path via an
# appended override. Neither script's vendor name is baked into the shared
# prompts, and both read the identical real design-system source from
# design-systems/.
#
# SAFETY: always writes to codex-blind/, codex-google/, codex-vercel/ --
# never into claude-blind/, claude-google/, claude-vercel/ -- so it
# structurally cannot overwrite the original Claude Code evidence those
# hold, regardless of flags. codex-*/'s own post.html files are cited by
# the article too now, so the usual refuse-unless---force guard below
# protects them the same way claude-*/'s does.
#
# Usage: ./run-codex-tests.sh [--force]

set -e

export PATH="$HOME/.npm-global/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

FORCE=false
[ "$1" = "--force" ] && FORCE=true

for arm in blind google vercel; do
  outdir="codex-$arm"
  mkdir -p "$outdir"

  if [ -f "$outdir/post.html" ] && [ "$FORCE" = false ]; then
    echo "SKIPPING $arm: $outdir/post.html already exists. Pass --force to overwrite."
    continue
  fi

  echo "=== Running $arm -> $outdir/post.html ==="
  codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check \
    "$(cat "$arm-prompt.txt") (Save the finished file to exactly this path instead: $outdir/post.html)" \
    > "$outdir/run.log" 2>&1
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

echo "Done. Results are in codex-blind/post.html, codex-google/post.html, codex-vercel/post.html"
