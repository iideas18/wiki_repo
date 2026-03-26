# Wiki Style Specification — gem5

Single source of truth for CSS/JS patterns across all wiki pages.

## Theme

- **Dark theme (default)**: `--bg:#0d1117; --surface:#161b22; --border:#30363d; --text:#c9d1d9; --text-muted:#8b949e; --accent:#58a6ff; --accent2:#3fb950; --accent3:#d29922; --accent4:#f85149; --heading:#f0f6fc; --code-bg:#1c2128`
- **Light theme** (`[data-theme="light"]`): `--bg:#ffffff; --surface:#f6f8fa; --border:#d0d7de; --text:#1f2328; --text-muted:#656d76; --accent:#0969da; --accent2:#1a7f37; --accent3:#9a6700; --accent4:#cf222e; --heading:#1f2328; --code-bg:#f6f8fa`

## localStorage Key

All pages use: `neutra-ip-theme`

## CDN Dependencies

- Mermaid.js 10.x (startOnLoad:false)
- Highlight.js 11.9.0

## Language

Primary: `cpp` (C++ with `.cc`/`.hh` extensions)
Code blocks use: `class="language-cpp"`

## Metadata

- `{{DATE}}`: 2026-03-25
- `{{GIT_SHA}}`: 7a2b0e413d
- `{{SOURCE_PATH}}`: per-page (e.g., `src/cpu/`)
- `{{PROJECT_THEME_KEY}}`: neutra-ip
