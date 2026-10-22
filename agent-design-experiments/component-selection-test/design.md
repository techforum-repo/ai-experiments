# design.md — Fictive Docs (judgment layer)

This is the house style for Fictive's technical documentation and blog
posts. It covers judgment calls — voice, composition, hierarchy, what to
avoid — not exact values. For colors, type, and spacing, use
`stylesheet.css` (linked in `<head>`). For components, use the pre-built
markup in `components/` — each file there is a copy-ready HTML snippet,
already correctly structured and already styled. Use a component's markup
exactly as given, only replacing its placeholder text/content — do not
restructure it, do not rewrite its tags, and do not invent a component of
your own. If nothing in `components/` fits, use the closest one rather than
building something new.

## Voice

Direct, practitioner-to-practitioner. Explain the reasoning, not just the
steps. No marketing language, no exclamation points, no "simply" or "just"
before an instruction that isn't actually simple.

## Composition and hierarchy

Single column, generous whitespace. Every post opens with a title and a
one-sentence summary of what the reader will walk away knowing. Use `h1`,
`h2`, `h3` as already styled in the stylesheet — don't rebuild heading
styles with inline CSS.

## Drawing attention to something

Three components in `components/` surface important information:
`callout.html`, `note.html`, `banner.html`. Each is fully built and
production-ready. Use whichever fits the content.

## Status and category labels

Three components in `components/` present a short status or category
label: `badge.html`, `tag.html`, `pill.html`. Each is fully built. Use
whichever fits the content.

## Sequences and itemized content

Three components in `components/` present a list: `steps.html` (a numbered
procedure), `ordered-list.html` (a plain numbered list), and
`unordered-list.html` (a plain bulleted list). Use whichever best presents
the content.

## Named anti-patterns — what we never want to see again

- A generic "hero gradient + rounded SaaS card" layout.
- A new color, font, or component class invented instead of using a
  documented one.
- Marketing tone in technical documentation.

## Do's and don'ts

**Do**
- Build every page against `stylesheet.css`'s tokens, linked in `<head>` —
  don't inline a competing `<style>` block.
- Use the pre-built components in `components/` exactly as given, wherever
  the content calls for them.

**Don't**
- Don't restructure a component's markup or invent one of your own.
- Don't override a documented token's value inline.
