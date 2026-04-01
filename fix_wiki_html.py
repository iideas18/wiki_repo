#!/usr/bin/env python3
"""Post-generation check & fix for wiki HTML pages.

Scans all HTML files under specified project directories and fixes common
issues produced by the wiki generator:

  1. Missing scroll-wheel zoom on diagram overlays
  2. svg.outerHTML used instead of cloneNode(true)
  3. Missing data-source preservation before mermaid.run()
  4. Missing null-guard on overlay element access
  5. Wrong localStorage theme key (should be 'neutra-ip-theme')
  6. Overlay click handler missing e.target check (click propagation bug)
  7. mermaid.run() / mermaid.render() without try-catch (silent errors)

Usage:
    python3 fix_wiki_html.py                      # scan & fix all projects
    python3 fix_wiki_html.py claude-code minimind  # fix specific projects
    python3 fix_wiki_html.py --check               # dry-run: report only
"""

import re
import os
import sys
from pathlib import Path

WIKI_DIR = Path(__file__).resolve().parent
REQUIRED_THEME_KEY = "neutra-ip-theme"


class FileFixer:
    def __init__(self, path: Path, dry_run: bool = False):
        self.path = path
        self.rel = path.relative_to(WIKI_DIR)
        self.dry_run = dry_run
        self.text = path.read_text(encoding="utf-8", errors="ignore")
        self.original = self.text
        self.fixes = []

    def _log(self, msg: str):
        self.fixes.append(msg)

    # ── Fix 1: svg.outerHTML → cloneNode(true) ──────────────
    def fix_outerhtml(self):
        """Replace outerHTML patterns with cloneNode(true)."""
        if ".outerHTML" not in self.text:
            return

        # Pattern A: zoomInner.innerHTML = svg.outerHTML
        old = "zoomInner.innerHTML = svg.outerHTML"
        new = "zoomInner.innerHTML = ''; zoomInner.appendChild(svg.cloneNode(true))"
        if old in self.text:
            self.text = self.text.replace(old, new)
            self._log("fix outerHTML → cloneNode (zoomInner pattern)")

        # Pattern B: overlayContent.innerHTML = svg.outerHTML
        old2 = "overlayContent.innerHTML = svg.outerHTML"
        new2 = "overlayContent.innerHTML = ''; overlayContent.appendChild(svg.cloneNode(true))"
        if old2 in self.text:
            self.text = self.text.replace(old2, new2)
            self._log("fix outerHTML → cloneNode (overlayContent pattern)")

        # Pattern C: overlayInner.innerHTML = svg.outerHTML
        old3 = "overlayInner.innerHTML = svg.outerHTML"
        new3 = "overlayInner.innerHTML = ''; overlayInner.appendChild(svg.cloneNode(true))"
        if old3 in self.text:
            self.text = self.text.replace(old3, new3)
            self._log("fix outerHTML → cloneNode (overlayInner pattern)")

        # Pattern D: Generic X.innerHTML=Y.outerHTML (covers svg.outerHTML, w.outerHTML, etc.)
        if ".outerHTML" in self.text and "cloneNode" not in self.text:
            self.text = re.sub(
                r"(\w+(?:\.\w+)*)\.innerHTML\s*=\s*(\w+(?:\.\w+)*)\.outerHTML",
                lambda m: f"{m.group(1)}.innerHTML='';{m.group(1)}.appendChild({m.group(2)}.cloneNode(true))",
                self.text,
            )
            if ".outerHTML" not in self.text:
                self._log("fix outerHTML → cloneNode (generic pattern)")

        # Pattern E: X.innerHTML=Y.querySelector("svg").outerHTML
        if ".outerHTML" in self.text and "cloneNode" not in self.text:
            self.text = re.sub(
                r'(\w+(?:\.\w+)*)\.innerHTML\s*=\s*(\w+(?:\.\w+)*)\.querySelector\(\s*["\']svg["\']\s*\)\.outerHTML',
                lambda m: (
                    f"(function(){{var _s={m.group(2)}.querySelector('svg');"
                    f"{m.group(1)}.innerHTML='';if(_s){m.group(1)}.appendChild(_s.cloneNode(true))}})()"
                ),
                self.text,
            )
            if ".outerHTML" not in self.text:
                self._log("fix outerHTML → cloneNode (querySelector pattern)")

        # Pattern F: X.querySelector(sel).innerHTML=Y.outerHTML
        if ".outerHTML" in self.text:
            self.text = re.sub(
                r"(\w+(?:\.\w+)*)\.querySelector\(\s*(['\"][^'\"]+['\"])\s*\)\.innerHTML\s*=\s*(\w+)\.outerHTML",
                lambda m: (
                    f"(function(){{var _t={m.group(1)}.querySelector({m.group(2)});"
                    f"_t.innerHTML='';_t.appendChild({m.group(3)}.cloneNode(true))}})()"
                ),
                self.text,
            )
            if ".outerHTML" not in self.text:
                self._log("fix outerHTML → cloneNode (querySelector target pattern)")

    # ── Fix 2: Add wheel zoom where missing ──────────────────
    def fix_missing_wheel_zoom(self):
        """Inject wheel-zoom handler where overlay exists but no 'wheel' listener."""
        if "'wheel'" in self.text or '"wheel"' in self.text:
            return  # already has wheel handling

        # Detect which overlay pattern is being used
        # Pattern A: overlay id = 'zoomOverlay', content = 'zoomInner'
        if "zoomOverlay" in self.text and "zoomInner" in self.text:
            wheel_code = (
                "\noverlay.addEventListener('wheel',function(e){"
                "e.preventDefault();"
                "zoomScale=Math.max(0.3,Math.min(5,zoomScale+(e.deltaY<0?0.15:-0.15)));"
                "zoomInner.style.transform='scale('+zoomScale+')';"
                "},{passive:false});\n"
            )
            anchor = "document.addEventListener('keydown'"
            if anchor in self.text:
                idx = self.text.index(anchor)
                self.text = self.text[:idx] + wheel_code + self.text[idx:]
                self._log("inject wheel-zoom (zoomOverlay/zoomInner pattern)")
                return

        # Pattern A2: overlay id = 'zoomOverlay', content = 'zoomContent'
        if "zoomOverlay" in self.text and "zoomContent" in self.text:
            wheel_code = (
                "\noverlay.addEventListener('wheel',function(e){"
                "e.preventDefault();"
                "var s=parseFloat(zoomContent.dataset.scale||'1');"
                "s=Math.max(0.3,Math.min(5,s+(e.deltaY<0?0.15:-0.15)));"
                "zoomContent.dataset.scale=s;"
                "zoomContent.style.transform='scale('+s+')';"
                "},{passive:false});\n"
            )
            anchor = "document.addEventListener('keydown'"
            if anchor in self.text:
                idx = self.text.index(anchor)
                self.text = self.text[:idx] + wheel_code + self.text[idx:]
                self._log("inject wheel-zoom (zoomOverlay/zoomContent pattern)")
                return

        # Pattern B: overlay id = 'overlay', content = 'overlayContent'  
        if "getElementById('overlay')" in self.text or 'id="overlay"' in self.text:
            # For function-style zoom (zoomDiagram/closeOverlay)
            if "function zoomDiagram" in self.text or "function closeOverlay" in self.text:
                wheel_code = (
                    "\ndocument.getElementById('overlay').addEventListener('wheel',function(e){"
                    "e.preventDefault();"
                    "if(!this.classList.contains('active'))return;"
                    "var inner=document.getElementById('overlayContent')||document.querySelector('.inner');"
                    "if(!inner)return;"
                    "var s=parseFloat(inner.dataset.scale||'1');"
                    "s=Math.max(0.3,Math.min(5,s+(e.deltaY<0?0.15:-0.15)));"
                    "inner.dataset.scale=s;"
                    "inner.style.transform='scale('+s+')';"
                    "},{passive:false});\n"
                )
                # Insert before </script>
                last_script_close = self.text.rfind("</script>")
                if last_script_close > 0:
                    self.text = self.text[:last_script_close] + wheel_code + self.text[last_script_close:]
                    self._log("inject wheel-zoom (function-style overlay pattern)")
                    return

        # Pattern C: diagramOverlay without overlayContent (gpu-compute, python, kern, systemc)
        if "diagramOverlay" in self.text:
            # Find the overlay content element
            content_id = None
            if "diagramOverlayContent" in self.text:
                content_id = "diagramOverlayContent"
            else:
                # Some pages have diagramOverlay wrapping a child div
                m = re.search(r'id="diagramOverlay"[^>]*>\s*<div[^>]*id="([^"]+)"', self.text)
                if m:
                    content_id = m.group(1)

            if content_id:
                wheel_code = (
                    f"\ndocument.getElementById('{content_id}').addEventListener('wheel',function(e){{"
                    "e.preventDefault();"
                    "if(!document.getElementById('diagramOverlay').classList.contains('active'))return;"
                    "var s=parseFloat(this.dataset.scale||'1');"
                    "s=Math.max(0.3,Math.min(5,s+(e.deltaY<0?0.15:-0.15)));"
                    "this.dataset.scale=s;"
                    "this.style.transform='scale('+s+')';"
                    "},{passive:false});\n"
                )
            else:
                wheel_code = (
                    "\nvar _ov=document.getElementById('diagramOverlay');"
                    "if(_ov){_ov.addEventListener('wheel',function(e){"
                    "e.preventDefault();"
                    "var inner=_ov.querySelector('div')||_ov;"
                    "var s=parseFloat(inner.dataset.scale||'1');"
                    "s=Math.max(0.3,Math.min(5,s+(e.deltaY<0?0.15:-0.15)));"
                    "inner.dataset.scale=s;"
                    "inner.style.transform='scale('+s+')';"
                    "},{passive:false});}\n"
                )

            last_script_close = self.text.rfind("</script>")
            if last_script_close > 0:
                self.text = self.text[:last_script_close] + wheel_code + self.text[last_script_close:]
                self._log("inject wheel-zoom (diagramOverlay pattern)")
                return

        # Pattern D: .diagram-wrap overlay (mem_doc pattern)
        if "diagram-wrap" in self.text and "overlay" in self.text.lower():
            m = re.search(r'getElementById\([\'"](\w*[Oo]verlay\w*?)[\'"]\)', self.text)
            if m:
                ov_id = m.group(1)
                # Look for inner content element (Content, Inner, etc.)
                mc = re.search(
                    r'getElementById\([\'"](\w*(?:[Cc]ontent|[Ii]nner)\w*?)[\'"]\)',
                    self.text,
                )
                content_id = mc.group(1) if mc and mc.group(1) != ov_id else None
                target = content_id or ov_id
                wheel_code = (
                    f"\nvar _wov=document.getElementById('{ov_id}');"
                    f"var _wc=document.getElementById('{target}');"
                    "if(_wov&&_wc){_wov.addEventListener('wheel',function(e){"
                    "e.preventDefault();"
                    "var s=parseFloat(_wc.dataset.scale||'1');"
                    "s=Math.max(0.3,Math.min(5,s+(e.deltaY<0?0.15:-0.15)));"
                    "_wc.dataset.scale=s;"
                    "_wc.style.transform='scale('+s+')';"
                    "},{passive:false});}\n"
                )
                last_script_close = self.text.rfind("</script>")
                if last_script_close > 0:
                    self.text = self.text[:last_script_close] + wheel_code + self.text[last_script_close:]
                    self._log("inject wheel-zoom (diagram-wrap pattern)")
                    return

        # Pattern E: Hyphenated overlay id (e.g. 'diagram-overlay')
        m_hyp = re.search(r'getElementById\([\'"]([a-zA-Z][\w-]*overlay[\w-]*)[\'"]\)', self.text)
        if m_hyp:
            ov_id = m_hyp.group(1)
            # Find inner content element
            inner_match = re.search(
                r'getElementById\([\'"](' + re.escape(ov_id) + r'-inner|' + re.escape(ov_id) + r'Inner)[\'"]\)',
                self.text,
            )
            if inner_match:
                inner_id = inner_match.group(1)
            else:
                inner_id = None

            target = inner_id or ov_id
            wheel_code = (
                f"\n(function(){{var _ov=document.getElementById('{ov_id}');"
                + (f"var _c=document.getElementById('{target}');" if inner_id else "var _c=_ov.querySelector('div')||_ov;")
                + "if(!_ov||!_c)return;"
                "_ov.addEventListener('wheel',function(e){"
                "e.preventDefault();"
                "var s=parseFloat(_c.dataset.scale||'1');"
                "s=Math.max(0.3,Math.min(5,s+(e.deltaY<0?0.15:-0.15)));"
                "_c.dataset.scale=s;"
                "_c.style.transform='scale('+s+')';"
                "},{passive:false});}());\n"
            )
            last_script_close = self.text.rfind("</script>")
            if last_script_close > 0:
                self.text = self.text[:last_script_close] + wheel_code + self.text[last_script_close:]
                self._log("inject wheel-zoom (hyphenated overlay pattern)")
                return

        # Pattern F: Generic overlay by class (e.g. class="overlay" or class="zoom-overlay")
        m_cls = re.search(r'id="([^"]*overlay[^"]*)"', self.text, re.IGNORECASE)
        if m_cls:
            ov_id = m_cls.group(1)
            wheel_code = (
                f"\n(function(){{var _ov=document.getElementById('{ov_id}');"
                "if(!_ov)return;"
                "var _c=_ov.querySelector('div')||_ov;"
                "_ov.addEventListener('wheel',function(e){"
                "e.preventDefault();"
                "var s=parseFloat(_c.dataset.scale||'1');"
                "s=Math.max(0.3,Math.min(5,s+(e.deltaY<0?0.15:-0.15)));"
                "_c.dataset.scale=s;"
                "_c.style.transform='scale('+s+')';"
                "},{passive:false});}());\n"
            )
            last_script_close = self.text.rfind("</script>")
            if last_script_close > 0:
                self.text = self.text[:last_script_close] + wheel_code + self.text[last_script_close:]
                self._log("inject wheel-zoom (generic overlay pattern)")
                return

    # ── Fix 3: Add data-source saving before mermaid.run() ───
    def fix_missing_data_source(self):
        """Add data-source attribute saving before mermaid.run() is first called."""
        if "data-source" in self.text or "data-original" in self.text or "dataset.original" in self.text:
            return  # already has data-source saving

        if "mermaid.run" not in self.text and "mermaid.init" not in self.text:
            return

        save_snippet = (
            "document.querySelectorAll('pre.mermaid,.mermaid').forEach(function(el){"
            "if(!el.getAttribute('data-source'))el.setAttribute('data-source',el.textContent);});\n"
        )

        # Insert right after <script> or <script type="module"> that contains mermaid code
        # Find the first <script that contains mermaid
        script_starts = [(m.start(), m.end()) for m in re.finditer(r"<script[^>]*>", self.text)]
        for start, end in script_starts:
            # Find the closing </script> for this block
            close = self.text.find("</script>", end)
            if close == -1:
                continue
            block = self.text[end:close]
            if "mermaid" in block.lower():
                self.text = self.text[:end] + "\n" + save_snippet + self.text[end:]
                self._log("inject data-source saving before mermaid.run()")
                break

    # ── Fix 4: Add null guard for overlay ────────────────────
    def fix_overlay_null_guard(self):
        """Add null-guard where overlay element is accessed without checking."""
        # Pattern: overlay.addEventListener without prior null check
        # This is tricky because we don't want to break working code.
        # We'll focus on the IIFE pattern used in gem5/claude-code templates.
        
        # Pattern A: var overlay=getElementById(...);...overlay.addEventListener
        # Already guarded if 'if(!overlay)return' exists nearby
        if "if(!overlay)return" in self.text or "if (!overlay) return" in self.text:
            return

        # For IIFE pattern: (function(){var overlay=...;var content=...;var scale=...;
        pattern = r"(\(function\(\)\{var overlay=document\.getElementById\('[^']+'\);var content=document\.getElementById\('[^']+'\);)(var scale=)"
        replacement = r"\1if(!overlay||!content)return;\2"
        new_text = re.sub(pattern, replacement, self.text)
        if new_text != self.text:
            self.text = new_text
            self._log("add null guard (IIFE overlay pattern)")
            return

        # Pattern B: standalone var overlay=...; overlay.addEventListener
        # Find: var overlay = getElementById(...); then overlay.addEventListener without guard
        pattern2 = r"(var\s+overlay\s*=\s*document\.getElementById\([^)]+\);)\s*(var\s+overlayContent)"
        replacement2 = r"\1\nif(!overlay)return;\n\2"
        new_text = re.sub(pattern2, replacement2, self.text)
        if new_text != self.text:
            self.text = new_text
            self._log("add null guard (var overlay pattern)")
            return

    # ── Fix 5: Wrong theme localStorage key ──────────────────
    def fix_theme_key(self):
        """Ensure all theme localStorage calls use 'neutra-ip-theme'."""
        wrong_keys = ["wiki-theme", "neutra_ip-theme", "theme-preference"]
        for wrong in wrong_keys:
            if wrong in self.text:
                self.text = self.text.replace(wrong, REQUIRED_THEME_KEY)
                self._log(f"fix theme key: '{wrong}' → '{REQUIRED_THEME_KEY}'")

    def apply_all(self):
        self.fix_outerhtml()
        self.fix_missing_wheel_zoom()
        self.fix_missing_data_source()
        self.fix_overlay_null_guard()
        self.fix_theme_key()
        self.fix_overlay_click_propagation()
        self.fix_mermaid_silent_errors()

    # ── Fix 6: Overlay click handler missing e.target check ──
    def fix_overlay_click_propagation(self):
        """Add e.target check to overlay click handlers that close without it.

        Without the check, clicking *inside* the zoomed diagram (on the SVG)
        bubbles up and closes the overlay immediately.
        """
        pattern_a = re.compile(
            r"((\w+)\.addEventListener\(\s*'click'\s*,\s*function\s*\(\s*\)\s*\{\s*)"
            r"(\2\.classList\.remove\(\s*'(?:active|show)'\s*\)\s*;?\s*)"
            r"(\}\s*\))"
        )
        def _repl_a(m):
            return (
                f"{m.group(2)}.addEventListener('click',function(e){{"
                f"if(e.target==={m.group(2)}){m.group(3)}"
                f"}})"
            )
        new_text = pattern_a.sub(_repl_a, self.text)
        if new_text != self.text:
            self.text = new_text
            self._log("fix overlay click propagation (add e.target check)")

    # ── Fix 7: Wrap mermaid.run / mermaid.render in try-catch ─
    def fix_mermaid_silent_errors(self):
        """Wrap bare mermaid.run() and mermaid.render() calls in try-catch.

        Prevents rendering failures from silently breaking the page.
        """
        if "mermaid" not in self.text:
            return

        def _inside_try_block(text, pos):
            """Return True if *pos* sits between a try{ and its }catch."""
            depth = 0
            i = pos - 1
            while i >= 0:
                ch = text[i]
                if ch == '{':
                    depth += 1
                    if depth == 1:
                        # Check for "try" before the opening brace (with optional whitespace)
                        pre = text[max(0, i - 10):i].rstrip()
                        if pre.endswith('try'):
                            return True
                elif ch == '}':
                    depth -= 1
                i -= 1
            return False

        def _find_call_end(text, open_paren_pos):
            """Find the position after the closing ')' and optional ';'."""
            depth = 0
            i = open_paren_pos
            while i < len(text):
                ch = text[i]
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        # skip optional whitespace and semicolon
                        j = i + 1
                        while j < len(text) and text[j] in ' \t':
                            j += 1
                        if j < len(text) and text[j] == ';':
                            return j + 1
                        return i + 1
                i += 1
            return -1

        changed_before = self.text

        # Collect all mermaid.run( positions and wrap them
        # Process in reverse order to preserve positions
        run_starts = [m.start() for m in re.finditer(r"mermaid\.run\(", self.text)]
        for pos in reversed(run_starts):
            paren_pos = self.text.index("(", pos)
            end = _find_call_end(self.text, paren_pos)
            if end == -1:
                continue

            # Determine statement start (include optional prefix)
            stmt_start = pos
            # Check for await prefix
            pre = self.text[max(0, pos - 20):pos]
            await_match = re.search(r"await\s+$", pre)
            if await_match:
                stmt_start = pos - len(pre) + await_match.start()
            # Check for if(window.mermaid) prefix
            pre2 = self.text[max(0, stmt_start - 25):stmt_start]
            if pre2.endswith("if(window.mermaid)"):
                stmt_start -= len("if(window.mermaid)")

            if _inside_try_block(self.text, stmt_start):
                continue

            stmt = self.text[stmt_start:end]
            self.text = (
                self.text[:stmt_start]
                + f"try{{{stmt}}}catch(e){{console.warn('mermaid:',e)}}"
                + self.text[end:]
            )

        # --- .then(...) without .catch() on mermaid.render ---
        self.text = re.sub(
            r"(mermaid\.render\([^)]*\)\.then\([^)]*\))"
            r"(?!\.catch)",
            r"\1.catch(function(e){console.warn('mermaid:',e)})",
            self.text,
        )

        # --- const{svg}=await mermaid.render(...); without try-catch ---
        render_starts = [m.start() for m in re.finditer(
            r"(?:const|var|let)\s*\{[^}]*\}\s*=\s*await\s+mermaid\.render\(",
            self.text,
        )]
        for pos in reversed(render_starts):
            paren_pos = self.text.index("(", self.text.index("mermaid.render(", pos))
            end = _find_call_end(self.text, paren_pos)
            if end == -1:
                continue
            if _inside_try_block(self.text, pos):
                continue
            stmt = self.text[pos:end]
            self.text = (
                self.text[:pos]
                + f"try{{{stmt}}}catch(e){{console.warn('mermaid:',e)}}"
                + self.text[end:]
            )

        # Logging
        if self.text != changed_before:
            old_try = len(re.findall(r"try\{", changed_before))
            new_try = len(re.findall(r"try\{", self.text))
            old_catch_chain = len(re.findall(r"\.catch\(", changed_before))
            new_catch_chain = len(re.findall(r"\.catch\(", self.text))
            added_try = new_try - old_try
            added_catch = new_catch_chain - old_catch_chain
            parts = []
            if added_try:
                parts.append(f"{added_try} try-catch block(s)")
            if added_catch:
                parts.append(f"{added_catch} .catch() chain(s)")
            if parts:
                self._log(f"add mermaid error handling: {', '.join(parts)}")

    def changed(self) -> bool:
        return self.text != self.original

    def save(self):
        if not self.dry_run and self.changed():
            self.path.write_text(self.text, encoding="utf-8")


def scan_issues(path: Path, text: str) -> list[str]:
    """Report issues without fixing (for --check mode and post-fix audit)."""
    issues = []
    rel = path.relative_to(WIKI_DIR)

    if ".outerHTML" in text and "cloneNode" not in text:
        issues.append(f"{rel}: uses svg.outerHTML instead of cloneNode(true)")

    has_overlay = bool(re.search(r'class="[^"]*overlay', text))
    has_wheel = "'wheel'" in text or '"wheel"' in text
    if has_overlay and not has_wheel:
        issues.append(f"{rel}: overlay present but NO wheel zoom")

    if "mermaid.run" in text:
        has_ds = "data-source" in text or "data-original" in text or "dataset.original" in text
        if not has_ds:
            issues.append(f"{rel}: mermaid.run() without data-source saving")

    if "localStorage" in text:
        keys = re.findall(r"localStorage\.\w+Item\(['\"]([^'\"]+)['\"]\)", text)
        theme_keys = [k for k in keys if "theme" in k.lower()]
        if theme_keys and not all(k == REQUIRED_THEME_KEY for k in theme_keys):
            issues.append(f"{rel}: wrong theme key: {set(theme_keys)}")

    # Check for overlay click handler missing e.target guard
    if re.search(
        r"\w+\.addEventListener\(\s*'click'\s*,\s*function\s*\(\s*\)\s*\{"
        r"\s*\w+\.classList\.remove\(\s*'(?:active|show)'\s*\)",
        text,
    ):
        issues.append(f"{rel}: overlay click handler missing e.target check")

    # Check for mermaid.run / mermaid.render without try-catch
    if "mermaid.run" in text or "mermaid.render" in text:
        def _inside_try(text, pos):
            depth = 0
            i = pos - 1
            while i >= 0:
                ch = text[i]
                if ch == '{':
                    depth += 1
                    if depth == 1:
                        pre = text[max(0, i - 10):i].rstrip()
                        if pre.endswith('try'):
                            return True
                elif ch == '}':
                    depth -= 1
                i -= 1
            return False

        has_unguarded = False
        for m in re.finditer(r"(?:await\s+)?mermaid\.run\(", text):
            if not _inside_try(text, m.start()):
                has_unguarded = True
                break
        if not has_unguarded and re.search(
            r"mermaid\.render\([^)]*\)\.then\([^)]*\)(?!\.catch)", text
        ):
            has_unguarded = True
        if not has_unguarded:
            for m in re.finditer(
                r"(?:const|var|let)\s*\{[^}]*\}\s*=\s*await\s+mermaid\.render\(",
                text,
            ):
                if not _inside_try(text, m.start()):
                    has_unguarded = True
                    break
        if has_unguarded:
            issues.append(f"{rel}: mermaid call(s) without error handling")

    return issues


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    check_only = "--check" in sys.argv

    if args:
        targets = [WIKI_DIR / a for a in args]
    else:
        targets = sorted(
            d for d in WIKI_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    total_fixed = 0
    total_issues_before = 0
    total_issues_after = 0

    for target in targets:
        if not target.is_dir():
            continue
        html_files = sorted(target.rglob("*.html"))
        for hf in html_files:
            if hf.name == "search.html":
                continue

            text = hf.read_text(encoding="utf-8", errors="ignore")
            issues_before = scan_issues(hf, text)
            total_issues_before += len(issues_before)

            if check_only:
                for issue in issues_before:
                    print(f"  [ISSUE] {issue}")
                continue

            fixer = FileFixer(hf, dry_run=False)
            fixer.apply_all()

            if fixer.changed():
                fixer.save()
                total_fixed += 1
                for fix_msg in fixer.fixes:
                    print(f"  [FIXED] {fixer.rel}: {fix_msg}")

                # Re-check after fix
                issues_after = scan_issues(hf, fixer.text)
                total_issues_after += len(issues_after)
                for issue in issues_after:
                    print(f"  [REMAINING] {issue}")
            else:
                total_issues_after += len(issues_before)

    print()
    if check_only:
        print(f"Issues found: {total_issues_before}")
    else:
        print(f"Files modified: {total_fixed}")
        print(f"Issues before: {total_issues_before}")
        print(f"Issues after:  {total_issues_after}")


if __name__ == "__main__":
    main()
