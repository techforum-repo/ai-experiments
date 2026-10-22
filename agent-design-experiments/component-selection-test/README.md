# Component Selection Test

A small, reproducible test of one question: when a design system permits more
than one legal choice (e.g. three different ways to flag something important),
do independent runs of a coding agent converge on the same choice, or drift?

Full writeup: *[link to the published post goes here]*

## Setup

- `design.md` — the judgment-layer spec. It names three families of
  interchangeable components and explicitly does not say which member of a
  family fits which situation.
- `stylesheet.css` — the design tokens and component styles.
- `components/` — nine HTML snippets, one per component, each a complete,
  copy-ready template with a one-line comment describing what it's for.
- `component-prompt.txt` — the exact brief given to every run: a ~600-word
  post about feature-flag cleanup, with four moments that need a component
  but never say which one.

## Reproducing it

```
./run-claude-tests.sh   # requires the Claude Code CLI, authenticated
./run-codex-tests.sh    # requires the Codex CLI, authenticated
```

Each script runs three fresh, isolated instances (no shared memory between
runs) against the identical design.md, stylesheet.css, components/, and
prompt, and writes the result to `<run>/post.html` plus the full agent
transcript to `<run>/run.log`. A copy of `stylesheet.css` is kept alongside
each `post.html` too, since the page links to it by relative path and won't
render correctly without it.

```
./compare.sh
```

Verifies component selection against the actual HTML of all six runs (not
against what any run says it did) — which class each run used at each choice
point, whether they converged, and whether any severity variant was used.

## Results

- `claude-run1/`, `claude-run2/`, `claude-run3/` — three Claude Code runs
- `codex-run1/`, `codex-run2/`, `codex-run3/` — three Codex runs (model:
  `gpt-6-astra`)

All six converged on the same component for all four choice points. They
also diverged, consistently by vendor, on an axis nothing in the spec
addressed at all. Details and the reasoning behind both results are in the
writeup linked above.

## What this is not

A benchmark. Six runs against one content brief and one component library is
a demonstration of a mechanism, not a sample size anything should generalize
from. Verify against your own systems before drawing conclusions from it.
