# Wiki Style Specification — Hermes Agent

- **Theme key:** neutra-ip-theme
- **Language:** python
- **Date:** 2026-04-15
- **Source:** hermes-agent
- **Git SHA:** 677f1227

## Theme
- Dark (default): --bg:#0d1117; --surface:#161b22; --border:#30363d; --text:#c9d1d9; --text-muted:#8b949e; --accent:#58a6ff; --accent2:#3fb950; --accent3:#d29922; --accent4:#f85149; --heading:#f0f6fc; --code-bg:#1c2128
- Light: --bg:#ffffff; --surface:#f6f8fa; --border:#d0d7de; --text:#1f2328; --text-muted:#656d76; --accent:#0969da; --accent2:#1a7f37; --accent3:#9a6700; --accent4:#cf222e; --heading:#1f2328; --code-bg:#f6f8fa

## Rules
- localStorage key: neutra-ip-theme
- startOnLoad:false for mermaid
- pre code { background:none; color:inherit; padding:0 }
- Code blocks: class="language-python"
- No hardcoded Mermaid colors
- Breadcrumb separator: rsaquo
- Skip-link as first body element
- Theme toggle: aria-label="Toggle light/dark theme"
- Breadcrumb nav: role="navigation" aria-label="Breadcrumb"
- Main content: <main id="main">
- meta wiki-generated, wiki-source, wiki-source-rev
- @media print block on every page
