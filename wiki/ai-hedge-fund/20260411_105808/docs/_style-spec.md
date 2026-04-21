# Wiki Style Specification

Single source of truth for CSS/JS patterns across all wiki pages. Reference this file
in subagent prompts instead of repeating CSS/JS rules inline.

## Theme

- **Dark theme (default)**: `--bg:#0d1117; --surface:#161b22; --border:#30363d; --text:#c9d1d9; --text-muted:#8b949e; --accent:#58a6ff; --accent2:#3fb950; --accent3:#d29922; --accent4:#f85149; --heading:#f0f6fc; --code-bg:#1c2128`
- **Light theme** (`[data-theme="light"]`): `--bg:#ffffff; --surface:#f6f8fa; --border:#d0d7de; --text:#1f2328; --text-muted:#656d76; --accent:#0969da; --accent2:#1a7f37; --accent3:#9a6700; --accent4:#cf222e; --heading:#1f2328; --code-bg:#f6f8fa`

## localStorage Key

All pages use: `neutra-ip-theme`

One key for the entire wiki — do NOT create per-module keys.

## CDN Dependencies

```html
<!-- Mermaid.js -->
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad:false,theme:"default",flowchart:{useMaxWidth:true,htmlLabels:true,curve:"basis"}});</script>

<!-- Highlight.js 11.9.0 -->
<link id="hljs-theme" rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github-dark.min.css">
<script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js"></script>
```

## Critical Rules

1. `startOnLoad:false` — Mermaid must NOT auto-render before footer JS sets theme.
2. `pre code { background:none; color:inherit; padding:0 }` — never set `color` on `pre code` or hljs tokens break.
3. Code blocks use `class="language-python"`.
4. No hardcoded colors in Mermaid `style` lines — let theme engine handle colors.
5. Theme toggle uses `textContent` (NOT `innerHTML`) to restore mermaid source.
6. Breadcrumb separator: `›` (`&rsaquo;`) — never `>`, `→`, or `»`.
7. Every page needs a skip-link (`<a href="#main" class="skip-link">`) as first body element.
8. Theme toggle must have `aria-label="Toggle light/dark theme"`.
9. Breadcrumb `<nav>` elements must have `role="navigation" aria-label="Breadcrumb"`.
10. Main content wrapped in `<main id="main">`.
11. Every page includes `<meta name="wiki-generated" content="2026-04-11">` and `<meta name="wiki-source" content="ai-hedge-fund">`.
12. Every page includes `@media print` block hiding toggle/skip-link and forcing light colors.
13. Every page includes `<meta name="wiki-source-rev" content="c45b50f">` for revision tracking.

## Project Info

- **Language**: Python
- **Generated**: 2026-04-11
- **Source Path**: /mnt/disk1/zy/stock_related/ai-hedge-fund
- **Git SHA**: c45b50f
