# design.md Architecture Test

The reproducible test behind the "second reader" design.md article: does an
agent adhere to a real brand's exact colors and fonts with no design file at
all, versus a Google-shaped merged file, versus a Vercel-shaped split
file-plus-stylesheet?

Full writeup: *[link to the published article goes here]*

## The three arms

Each arm is a single, cold run of the same content brief (a ~600-word
technical post titled "Retries Aren't Idempotent By Accident"), differing
only in what design context the agent had:

- **blind** — no design file at all. `blind-prompt.txt`.
- **google** — one merged file with a YAML-frontmatter token block plus
  prose rationale, in the actual shape Google's DESIGN.md spec uses.
  `google-prompt.txt`, `design-systems/google/DESIGN.md`.
- **vercel** — a split pair: a judgment-only `design.md` with zero hex
  values, plus a real `stylesheet.css` with the same tokens as documented
  CSS classes, mirroring Vercel's actual architecture. `vercel-prompt.txt`,
  `design-systems/vercel/design.md`, `design-systems/vercel/stylesheet.css`.

`design-systems/` is deliberately vendor-neutral — it's the one real design
system, extracted directly from this blog's own real, published CSS, that
both Claude Code and Codex read from identically. The prompt files
themselves don't name either vendor either (they say "save to `post.html`");
each run script supplies its own actual output path.

## Results already in this repo

`claude-blind/post.html`, `claude-google/post.html`, `claude-vercel/post.html`
are the actual, real outputs the published article's numbers and figures
come from. **Do not overwrite these** — both run scripts below refuse to by
default. (These folders used to be unprefixed — just `blind/google/vercel/`,
from before there was a second vendor to compare against — renamed for
symmetry with `codex-*`; content unchanged, verified by checksum both times
this repo was restructured.)

`codex-blind/post.html`, `codex-google/post.html`, `codex-vercel/post.html`
are real evidence too, not disposable scratch — the article's "reran through
Codex" update cites this exact run. Same don't-overwrite rule applies.

`shots/` holds working screenshots taken while writing the article
(`compare3.sh` regenerates the top-of-page ones).

## Reproducing it

```
./run-claude-tests.sh            # requires the Claude Code CLI, authenticated
./run-codex-tests.sh             # requires the Codex CLI, authenticated
```

Both refuse to overwrite existing output by default (`--force` to
override). The Codex script never writes into `claude-blind/`,
`claude-google/`, or `claude-vercel/` at all — its output always lands in
`codex-blind/`, `codex-google/`, `codex-vercel/`, so a Codex run can never
collide with the original Claude Code evidence, regardless of flags. Both
scripts read the identical real design-system source from `design-systems/`.

```
./compare3.sh
```

Checks the Claude Code arms' actual output against the real design system:
which tokens it reproduced (or didn't), whether the Vercel arm linked the
stylesheet instead of inventing its own, and which CSS classes it used that
aren't documented anywhere.

## What this is not

A benchmark. One cold run per arm is a demonstration, not a sample size
anything should generalize from — the article this repo backs says so
explicitly. Verify against your own systems before drawing conclusions from
it.
