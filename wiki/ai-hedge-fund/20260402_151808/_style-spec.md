# Style Spec — ai-hedge-fund/src Wiki

Generated: 2026-04-02
Source: /mnt/disk1/zy/internal_wiki/.git-clones/ai-hedge-fund/src
Language: python
Theme Key: neutra-ip-theme (localStorage)
Depth: 2-level (L1 overview + L2 sub-module pages)

## CSS Variables (Dark — default)
--bg:#0d1117;--surface:#161b22;--text:#c9d1d9;--accent:#58a6ff;
--accent2:#3fb950;--accent3:#d29922;--accent4:#f85149;
--border:#30363d;--heading:#f0f6fc;--code-bg:#1c2128;--text-muted:#8b949e

## CSS Variables (Light — [data-theme="light"])
--bg:#fff;--surface:#f6f8fa;--text:#1f2328;--border:#d0d7de;
--accent:#0969da;--accent2:#1a7f37;--accent3:#9a6700;--accent4:#cf222e;
--heading:#1f2328;--code-bg:#f6f8fa;--text-muted:#656d76

## Mermaid
- startOnLoad:false in head
- data-source saved before first mermaid.run()
- renderMermaid(theme) restores from data-source, re-inits, re-runs
- No hardcoded fills in mermaid style directives

## Code Blocks
- class="language-python" for hljs
- pre code{background:none;color:inherit;padding:0}
- Copy button on pre:hover

## Theme Toggle
- localStorage key: neutra-ip-theme
- applyTheme sets data-theme on html, calls renderMermaid
- Button: aria-label="Toggle light/dark theme"

## Meta Tags
- <meta name="wiki-generated" content="2026-04-02">
- <meta name="wiki-source" content="...">
- <meta name="wiki-source-rev" content="b6dca8c">
