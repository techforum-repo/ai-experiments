---
version: alpha
name: albins-blog-architecture-reference
description: >
  Single-post, self-contained HTML essays for share.albinsblog.com — long-form
  systems/architecture writing (e.g. "The Chain Doesn't Care Why It Broke").
  Each post is one HTML file with a fully inlined <style> block: no external
  CSS files, no build step, no JS framework. Content ships as static markup.
colors:
  bg: "#f5f6f9"
  surface: "#ffffff"
  ink: "#161a22"
  ink-soft: "#525a6e"
  ink-faint: "#8a91a3"
  line: "#e1e4ea"
  line-strong: "#c7cbd6"
  accent: "#2f5fed"
  accent-ink: "#1c3fb0"
  accent-soft: "#e9eefd"
  code-bg: "#edf0f5"
typography:
  h1:
    fontFamily: "Big Shoulders Display, Archivo Narrow, ui-sans-serif, sans-serif"
    fontWeight: 700
    textTransform: uppercase
    fontSize: "clamp(2.4rem, 5.6vw, 3.7rem)"
    lineHeight: 0.98
  h2:
    fontFamily: "Big Shoulders Display, Archivo Narrow, ui-sans-serif, sans-serif"
    fontWeight: 700
    textTransform: uppercase
    fontSize: "clamp(1.65rem, 3.5vw, 2.1rem)"
  body:
    fontFamily: "IBM Plex Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "16.5px"
    lineHeight: 1.68
  mono:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    usage: "eyebrows, tags, code, thesis-lead callouts, table headers, figure labels"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
  pill: "100px"
spacing:
  scale: [6, 10, 14, 18, 22, 28, 34, 44, 58, 60, 90]
  unit: px
  note: >
    Not a strict 8pt grid — a hand-tuned scale. Section vertical rhythm is
    ~58px between sections, ~22-34px around figures/callouts, ~14px between
    paragraphs. Prose column caps at 680px inside a 900px page shell.
components:
  eyebrow:
    font: mono
    fontSize: "0.72rem"
    letterSpacing: "0.14em"
    textTransform: uppercase
    color: accent-ink
  scene:
    description: "The one wrapper every figure/diagram/split-panel lives in — never a bare <img> or bare <svg>."
    border: "1px solid var(--line)"
    borderRadius: lg
    background: surface
    shadow: "0 1px 2px rgba(22,26,34,.04), 0 8px 24px rgba(22,26,34,.05)"
    parts: [scene-label (mono caption bar, top), scene-body (padded content), scene-foot (mono footnote, optional)]
  callout:
    border-left: "3px solid var(--accent)"
    background: accent-soft
    variant-alt:
      border-left: "3px solid var(--cyber)"
      background: cyber-soft
  thesis-lead:
    font: mono
    fontSize: "0.95rem"
    lineHeight: 1.9
    border-left: "3px solid var(--accent)"
    usage: "one or two per post, max — the single load-bearing sentence of a section"
  pill:
    fontFamily: mono
    fontSize: "0.72rem"
    borderRadius: pill
    variants: [neutral, accent, ok, warn, crit]
    dotBefore: true
  step-list:
    style: "counter(step, decimal-leading-zero) — 01, 02, 03 — not bullets, not plain numbers"
  sources:
    required: true
    position: end-of-document
    format: "ordered list, each item a link + em-dash + publisher name"
omitted:
  - motion
  - dark-mode-illustration-variants
---

# DESIGN.md — Architecture-Reference Essays

## Overview

This is the house style for long-form technical essays published as standalone
HTML files (no CMS, no framework, one file per post, view-source is the
distribution format). The voice is **a senior engineer explaining a pattern
to another senior engineer** — declarative, citation-backed, allergic to
hype. Think "internal architecture doc that escaped," not "marketing landing
page" and not "Medium listicle."

Every post opens with an eyebrow (series/part label), a title, a one-sentence
dek, and 3–4 stat chips summarizing the shape of the argument in numbers
before a single paragraph of prose has been read. Every post closes with a
short "chain" of takeaway lines and a numbered, linked Sources list — real
citations, not vibes.

## Colors

Core neutrals and the single accent (`--accent` / `--accent-ink` / `--accent-soft`,
a cobalt blue) are **fixed across every post** — do not invent a new base
palette per piece. What changes post-to-post is a small set of 2–5
**semantic role colors** (e.g. one post uses `ok` / `warn` / `crit` / `cyber`
/ `infra` for failure taxonomy; another uses `dev` / `stage` / `prod` / `alt`
for environment tiers). Each semantic role always ships as a pair: a
saturated `-ink`/main value for text and strokes, and a `-soft` background
tint at roughly 90% lightness for chips, callouts, and diagram fills. Never
add a role color without also deriving its `-soft` pairing the same way.

Both a light palette and a dark-mode palette are defined for every token —
dark mode is not an afterthought, it's a parallel set of CSS custom
properties swapped under `prefers-color-scheme` and a `[data-theme]`
override, using the exact same role structure.

## Typography

Two-family system, strictly divided by job:

- **Big Shoulders Display** (condensed, heavy, uppercase) — headings only
  (h1/h2/h3, footer thesis lines). It never appears in a sentence of running
  prose.
- **IBM Plex Sans** — all body copy, deks, list items, table cells.
- **IBM Plex Mono** — the "structural" voice: eyebrows, section tags,
  figure labels, code, table headers, pills, the thesis-lead callout, and
  the arrow-prefixed closing chain-list. Mono signals "this is a label or a
  claim being made precisely," sans signals "this is explanation."

Headings are uppercase with tight tracking; body text is not. Nothing is
italic except the disclaimer line, which is the one deliberately
de-emphasized element on the page.

## Layout

Single column. A 900px outer page shell with a tighter 680px prose column
inside it — figures, tables, and split-panels are allowed to use the full
900px width; paragraphs and lists are not. Sections are separated by ~58px
of top padding and a component rhythm, not by rules/dividers between every
block — the divider (`border-top`) is reserved for the header/footer
boundary and the sources block. Everything is a static single page: no
tabs, no accordions, no client-side routing.

## Elevation & Depth

Flat by default. The only elevated surface is `.scene` (the figure/diagram
wrapper) and the sources table wrap, both using the same one-line soft
double-shadow token — never a heavier shadow, never more than one elevation
level on the page at a time.

## Shapes

Consistent radius scale: 4px on inline chips/code, 8px on callouts, 12px on
`.scene` wrappers and split-cards, full pill (100px) on status pills and
badges only. No sharp-cornered cards and no fully-rounded cards outside
those two exceptions.

## Components

See the `components` block in the frontmatter above for exact specs. In
prose: every diagram or non-trivial visual lives inside a `.scene` wrapper
with a monospace caption bar reading `FIG. NN — TITLE` on the left and a
short all-caps descriptor on the right. Every SVG diagram gets a real
`aria-label` summarizing what it shows in one sentence — the diagram is
never the only place the information exists.

## Do's and Don'ts

**Do**
- Open with an eyebrow + h1 + one-sentence dek + a stat-chip row.
- Keep prose at 680px max-width even when the page shell is wider.
- Use exactly one accent color for interactive/emphasis elements; use
  semantic role colors only for the specific taxonomy that post is about.
- Cite real, checkable sources in a closing numbered list.
- Use the mono thesis-lead sparingly — it should read as the one sentence
  a reader would highlight.
- Wrap every diagram in `.scene` with a caption bar.

**Don't**
- Don't reach for a generic "hero gradient + rounded SaaS card" template —
  that's the exact genre this system is defined against.
- Don't use Big Shoulders Display (or any display face) inside a paragraph
  of body text.
- Don't invent a new accent color per post — extend the semantic-role set
  instead, following the `-ink`/`-soft` pairing convention.
- Don't ship a diagram as a flat raster image if it can be an inline SVG —
  raster diagrams can't inherit the color tokens or respond to dark mode.
- Don't skip the Sources section, and don't cite anything that isn't a real,
  linkable, checkable reference.
- Don't use drop shadows, glassmorphism, or more than one elevation level.
