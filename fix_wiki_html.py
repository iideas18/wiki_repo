#!/usr/bin/env python3
"""Post-generation check & fix for wiki HTML pages.

Scans all HTML files under specified project directories and fixes common
issues produced by the wiki generator:

  1. Missing scroll-wheel zoom on diagram overlays
  2. svg.outerHTML used instead of cloneNode(true)
  3. Missing data-source preservation before mermaid.run()
  4. Missing null-guard on overlay element access
  5. Wrong localStorage theme key (should be 'neutra-ip-theme')

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
        """Replace svg.outerHTML patterns with cloneNode(true)."""
        if "cloneNode" in self.text:
            return  # already uses cloneNode

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

        # Pattern D: Generic X.innerHTML=svg.outerHTML  or  X.innerHTML = svg.outerHTML
        if "svg.outerHTML" in self.text and "cloneNode" not in self.text:
            self.text = re.sub(
                r"(\w+(?:\.\w+)*)\.innerHTML\s*=\s*svg\.outerHTML",
                lambda m: f"{m.group(1)}.innerHTML='';{m.group(1)}.appendChild(svg.cloneNode(true))",
                self.text,
            )
            self._log("fix outerHTML → cloneNode (generic pattern)")

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
                mc = re.search(r'getElementById\([\'"](\w*[Cc]ontent\w*?)[\'"]\)', self.text)
                content_id = mc.group(1) if mc else None
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
