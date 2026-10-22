# Agent Design Experiments

Reproducible tests of one question, from two angles: what actually happens
when a coding agent has to work from a design system, instead of a human
reading one?

Both experiments run real prompts through real coding agents (Claude Code
and Codex) against real design-system specs, then verify the output against
the actual files — not against what the agent says it did.

## [`design-md-test/`](./design-md-test)

Does an agent adhere to a real brand's exact colors and fonts with no design
file at all, versus a Google-shaped merged file, versus a Vercel-shaped
split file-plus-stylesheet? Tests **token reproduction** — a determined
axis, where a value is either right or wrong.

## [`component-selection-test/`](./component-selection-test)

When a design system offers several legal ways to represent the same kind
of content (three ways to flag something important, three ways to show a
status), do independent agent runs converge on the same choice, or drift?
Tests **component selection** — an axis where several answers are legal,
and nothing but a stated reason distinguishes them.

## The connecting finding

Different axis, same mechanism: both tests show that what converges isn't
"tokens" versus "components" as categories. It's whether the option being
chosen carries a written reason, or just a name. A bare class name is a
token, exactly as arbitrary as an unspecified hex code — write down *why*
you'd reach for it, and the ambiguity closes the same way a hex code closes
it.

## What these are not

Benchmarks. Each is a small, transparent demonstration — real files, a
handful of cold runs, checked against reality — not a sample size anything
should generalize from. Every subfolder's README says so explicitly, and
each includes the scripts needed to run it again yourself.
