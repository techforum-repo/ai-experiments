#!/bin/bash
# Runs three isolated Codex instances for the component-selection test.
# Mirrors run-claude-tests.sh exactly -- same design.md, same stylesheet.css,
# same components/, same prompt -- so results are directly comparable
# across the two agents.
#
# Requires the Codex CLI (codex) to be installed and authenticated
# (npm install -g @openai/codex, then run `codex` once to sign in).
# Usage: ./run-codex-tests.sh

set -e

export PATH="$HOME/.npm-global/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for r in codex-run1 codex-run2 codex-run3; do
  echo "=== Running $r ==="
  mkdir -p "$SCRIPT_DIR/$r"
  cp "$SCRIPT_DIR/design.md" "$SCRIPT_DIR/stylesheet.css" "$SCRIPT_DIR/component-prompt.txt" "$SCRIPT_DIR/$r/"
  cp -r "$SCRIPT_DIR/components" "$SCRIPT_DIR/$r/"
  cd "$SCRIPT_DIR/$r"
  codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check \
    "$(cat component-prompt.txt)" > run.log 2>&1
  echo "  exit code: $?"
  if [ -f post.html ]; then
    echo "  post.html written ($(wc -c < post.html) bytes)"
  else
    echo "  WARNING: post.html was not created -- check $r/run.log"
  fi
  # Clean up the copied inputs that post.html doesn't need at runtime.
  # stylesheet.css is NOT removed here -- post.html links to it via a
  # relative path (<link rel="stylesheet" href="stylesheet.css">), so it
  # has to stay alongside post.html for the page to render correctly.
  rm -f component-prompt.txt design.md
  rm -rf components
  echo ""
done

echo "All three runs complete. Results are in codex-run1/post.html, codex-run2/post.html, codex-run3/post.html"
