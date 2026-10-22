# design.md — Architecture-Reference Essays (judgment layer)

This is the house style for long-form technical essays on this blog. It
covers judgment calls — voice, composition, hierarchy, what to avoid — not
exact values. For colors, type, spacing, and component classes, use
`stylesheet.css` (linked in `<head>`) and build with its documented class
names. Do not invent new colors, fonts, or component styles of your own;
if `stylesheet.css` doesn't have a primitive for something you need, use
the closest documented one rather than adding a new rule.

## Voice

A senior engineer explaining a pattern to another senior engineer —
declarative, citation-backed, allergic to hype. Think "internal
architecture doc that escaped," not a marketing landing page and not a
listicle. Every post opens with an eyebrow (series/part label), a title, a
one-sentence dek, and 3–4 stat chips summarizing the shape of the argument
in numbers before a single paragraph of prose has been read. Every post
closes with a short chain of takeaway lines and a numbered, linked Sources
list — real citations, not vibes.

## Composition and hierarchy

Single column. A wide page shell with a tighter prose column inside it —
figures, tables, and multi-panel layouts are allowed to use the full page
width; paragraphs and lists are not. Use the `eyebrow` class, `h1`/`h2`/`h3`,
and the `dek`/`section-dek` classes already defined in the stylesheet for
that rhythm — don't rebuild it with inline styles.

Wrap every diagram or non-trivial visual in the `scene` component (with its
`scene-label`, `scene-body`, and optional `scene-foot` — see stylesheet.css)
rather than dropping a bare image or SVG into the page. Give every diagram a
real one-sentence description of what it shows; the diagram should never be
the only place the information exists.

Use the `thesis-lead` class sparingly — once or twice per post, for the one
sentence a reader would highlight — not for every strong claim.

Use `callout` for a supporting aside, and its `.alt` variant only when you
need a second, visually distinct callout on the same page (e.g. a caveat
next to a main point). Don't add a third variant.

## Named anti-patterns — what we never want to see again

- A generic "hero gradient + rounded SaaS card" layout. That's the exact
  genre this house style is defined against.
- A display/heading typeface used inside a paragraph of running prose.
- A new accent color invented per post instead of extending the documented
  semantic-role pattern (a paired `-ink`/`-soft` role, same shape as
  `--ok`/`--ok-soft` in the stylesheet).
- A diagram shipped as a flat raster image when it could be inline SVG —
  raster images can't inherit the stylesheet's color tokens or respond to
  dark mode.
- A post with no closing Sources section, or one that cites something that
  isn't a real, checkable reference.
- Drop shadows, glassmorphism, or more than one elevation level on a page.
  The stylesheet defines exactly one shadow token; that's the only one to use.

## Do's and don'ts

**Do**
- Build every page against `stylesheet.css`'s documented classes and
  tokens, linked in `<head>` — don't inline a competing `<style>` block.
- Keep prose at the `prose` class's max-width even when the page shell
  (`page`) is wider.
- Cite real, checkable sources in a closing numbered list.

**Don't**
- Don't add a component class the stylesheet doesn't already define.
- Don't override a documented token's value inline.
- Don't skip the Sources section.
