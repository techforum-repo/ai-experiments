#!/bin/bash
# Runs three isolated Claude Code instances for the component-selection test.
# Mirrors run-codex-tests.sh exactly -- same design.md, same stylesheet.css,
# same components/, same prompt -- so results are directly comparable
# across the two agents.
#
# Requires the Claude Code CLI (claude) to be installed and authenticated.
# Usage: ./run-claude-tests.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for r in claude-run1 claude-run2 claude-run3; do
  echo "=== Running $r ==="
  mkdir -p "$SCRIPT_DIR/$r"
  cp "$SCRIPT_DIR/design.md" "$SCRIPT_DIR/stylesheet.css" "$SCRIPT_DIR/component-prompt.txt" "$SCRIPT_DIR/$r/"
  cp -r "$SCRIPT_DIR/components" "$SCRIPT_DIR/$r/"
  cd "$SCRIPT_DIR/$r"
  claude -p "$(cat component-prompt.txt)" --dangerously-skip-permissions > run.log 2>&1
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

echo "All three runs complete. Results are in claude-run1/post.html, claude-run2/post.html, claude-run3/post.html"
