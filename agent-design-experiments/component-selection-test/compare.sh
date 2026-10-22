#!/bin/bash
# Run this after all six runs exist (claude-run1/2/3, codex-run1/2/3, each
# with a post.html). Verifies component selection against the actual HTML --
# not against what any run says it did.
#
# Note: deliberately no `set -e` -- grep returning "no match" (exit 1) is a
# real, expected result here (e.g. a run using no severity variant), not a
# script failure.

RUNS="claude-run1 claude-run2 claude-run3 codex-run1 codex-run2 codex-run3"

echo "== Component classes actually used, per run =="
for r in $RUNS; do
  if [ ! -f "$r/post.html" ]; then
    echo "$r: post.html not found, skipping"
    continue
  fi
  echo "--- $r ---"
  grep -oE 'class="(callout|note|banner|badge|tag|pill|steps)[^"]*"' "$r/post.html"
done

echo
echo "== Convergence check: which component family won at each choice point =="
echo "(4/4 identical across all 6 runs is full convergence; a family that"
echo " picked 2+ different components indicates drift)"
for family in "banner|callout|note" "badge|tag|pill" "steps"; do
  echo "--- family: $family ---"
  for r in $RUNS; do
    [ -f "$r/post.html" ] || continue
    grep -oE "class=\"($family)[^\"]*\"" "$r/post.html" | sed "s/^/$r: /"
  done
done

echo
echo "== Severity variant usage (crit/warn) -- not requested, checked anyway =="
for r in $RUNS; do
  [ -f "$r/post.html" ] || continue
  variants=$(grep -oE 'class="(banner|callout) (warn|crit)"' "$r/post.html")
  if [ -n "$variants" ]; then
    echo "$r: $variants"
  else
    echo "$r: no severity variant used"
  fi
done

echo
echo "== Structural fidelity: does each used component match its template's shape? =="
echo "(manual check -- diff the relevant snippet against components/<name>.html)"
for r in $RUNS; do
  [ -f "$r/post.html" ] || continue
  echo "--- $r: banner block ---"
  grep -A2 'class="banner' "$r/post.html" | head -3
done
