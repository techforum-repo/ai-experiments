#!/bin/bash
# Run this from ~/design-md-test after all three post.html files exist:
#   claude-blind/post.html   claude-google/post.html   claude-vercel/post.html
set -e
mkdir -p shots

echo "== Screenshots (top-of-page) =="
for arm in blind google vercel; do
  google-chrome --headless --disable-gpu --no-sandbox --window-size=1000,1400 \
    --screenshot="shots/$arm.png" --hide-scrollbars "file://$PWD/claude-$arm/post.html"
done

echo
echo "== BLIND: inline tokens + fonts it invented =="
grep -m1 -A12 ':root {' claude-blind/post.html 2>/dev/null | grep -E 'bg:|accent:|accent-ink:|code-bg:|surface:|ink:' || echo "(no :root block)"
grep -o 'family=[A-Za-z+:@,;.0-9]*' claude-blind/post.html | sort -u

echo
echo "== GOOGLE: inline tokens + fonts, vs design-systems/google/DESIGN.md's real values =="
echo "--- what it produced ---"
grep -m1 -A12 ':root {' claude-google/post.html 2>/dev/null | grep -E 'bg:|accent:|accent-ink:|code-bg:|surface:|ink:' || echo "(no :root block)"
grep -o 'family=[A-Za-z+:@,;.0-9]*' claude-google/post.html | sort -u
echo "--- what design-systems/google/DESIGN.md specifies ---"
grep -A8 '^colors:' design-systems/google/DESIGN.md
grep -A6 '^typography:' design-systems/google/DESIGN.md | grep fontFamily

echo
echo "== VERCEL: did it link the stylesheet instead of inventing its own? =="
if grep -q 'href="stylesheet.css"' claude-vercel/post.html; then
  echo "PASS: <link> to stylesheet.css found"
else
  echo "FAIL: no <link> to stylesheet.css found in claude-vercel/post.html"
fi
if grep -qE '<style>' claude-vercel/post.html; then
  echo "FLAG: it also wrote its own <style> block -- check whether that duplicates/overrides stylesheet.css tokens"
else
  echo "PASS: no competing inline <style> block"
fi
echo "-- classes it actually used, vs. what stylesheet.css documents --"
grep -oE 'class="[^"]*"' claude-vercel/post.html | tr ' "' '\n\n' | grep -v '^$\|^class=$' | sort -u > /tmp/vercel-classes-used.txt
grep -oE '^\.[a-zA-Z0-9_-]+' design-systems/vercel/stylesheet.css | tr -d '.' | sort -u > /tmp/vercel-classes-documented.txt
echo "classes used but NOT documented in stylesheet.css (should be empty):"
comm -23 /tmp/vercel-classes-used.txt /tmp/vercel-classes-documented.txt

echo
echo "Screenshots are in ./shots/. Open each post.html directly (google-chrome $PWD/claude-vercel/post.html etc) to read them."
