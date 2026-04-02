# Wiki Style Specification — Claude Code Source

Single source of truth for CSS/JS patterns across all wiki pages.

## Variables
- **PROJECT_THEME_KEY**: `neutra-ip`
- **LANG**: `typescript`
- **DATE**: `2026-04-01`
- **GIT_SHA**: `a8a678c`
- **SOURCE_PATH**: `.git-clones/claude-code-sourcemap/restored-src/src`

## Theme
- **localStorage key**: `neutra-ip-theme` (unified across ALL pages)
- **Dark (default)**: `--bg:#0d1117;--surface:#161b22;--border:#30363d;--text:#c9d1d9;--text-muted:#8b949e;--accent:#58a6ff;--accent2:#3fb950;--accent3:#d29922;--accent4:#f85149;--heading:#f0f6fc;--code-bg:#1c2128`
- **Light**: `--bg:#fff;--surface:#f6f8fa;--border:#d0d7de;--text:#1f2328;--text-muted:#656d76;--accent:#0969da;--accent2:#1a7f37;--accent3:#9a6700;--accent4:#cf222e;--heading:#1f2328;--code-bg:#f6f8fa`

## CDN
- Mermaid 10.x: `https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js`
- hljs 11.9.0: `https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js`
- hljs dark: `github-dark.min.css`
- hljs light: `github.min.css`

## Rules
- `startOnLoad:false` in mermaid init
- `pre code{background:none;color:inherit;padding:0}` only
- Code blocks: `class="language-typescript"`
- No hardcoded mermaid style colors
- Breadcrumb separator: `›` (`&rsaquo;`)
- All pages: skip-link, aria-label on toggle, `<main id="main">`, `@media print`
