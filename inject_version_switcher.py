#!/usr/bin/env python3
"""Inject a version-switcher dropdown into wiki project index pages.

Reads versions.json for each project and injects a <select> dropdown into the
hero section of every version's index.html. Switching versions fetches the
selected version's content inline (no full page reload).

Usage:
    python3 inject_version_switcher.py                # all projects
    python3 inject_version_switcher.py oclgrind gem5  # specific projects
    python3 inject_version_switcher.py --check        # dry-run: report only
"""

import json
import re
import sys
from pathlib import Path

WIKI_DIR = Path(__file__).resolve().parent
TIMESTAMP_RE = re.compile(r"^\d{8}_\d{6}$")

MARKER_START = "<!-- VERSION_SWITCHER_START -->"
MARKER_END = "<!-- VERSION_SWITCHER_END -->"

SWITCHER_CSS = """\
.version-switcher{display:inline-flex;align-items:center;gap:8px;margin-top:1rem;\
background:var(--surface,#161b22);border:1px solid var(--border,#30363d);\
border-radius:8px;padding:6px 14px}
.version-label{color:var(--text-muted,#8b949e);font-size:.85rem}
.version-select{background:var(--bg,#0d1117);color:var(--accent,#58a6ff);\
border:1px solid var(--border,#30363d);border-radius:4px;padding:4px 8px;\
font-size:.85rem;cursor:pointer;font-family:inherit}
.version-select:focus{outline:2px solid var(--accent,#58a6ff);outline-offset:1px}
@media print{.version-switcher{display:none!important}}"""

SWITCHER_JS = """\
(function(){
  var versionsUrl='../versions.json';
  fetch(versionsUrl).then(function(r){return r.json()}).then(function(versions){
    if(!versions||versions.length<2)return;
    var parts=location.pathname.replace(/\\/$/,'').split('/');
    var curTs=parts[parts.length-1]||parts[parts.length-2];
    /* Build UI */
    var wrap=document.createElement('div');
    wrap.className='version-switcher';
    var lbl=document.createElement('span');
    lbl.className='version-label';
    lbl.textContent='Version:';
    var sel=document.createElement('select');
    sel.className='version-select';
    sel.setAttribute('aria-label','Switch wiki version');
    versions.forEach(function(v){
      var o=document.createElement('option');
      o.value=v.timestamp;
      var rev=v.rev?' ('+v.rev.substring(0,7)+')':'';
      o.textContent=v.date+rev+(v.latest?' (latest)':'');
      if(v.timestamp===curTs)o.selected=true;
      sel.appendChild(o);
    });
    wrap.appendChild(lbl);
    wrap.appendChild(sel);
    var hero=document.querySelector('.hero');
    if(hero)hero.appendChild(wrap);
    /* Version switch handler */
    sel.addEventListener('change',function(){
      var newTs=this.value;
      if(newTs===curTs)return;
      var newUrl='../'+newTs+'/index.html';
      fetch(newUrl).then(function(r){return r.text()}).then(function(html){
        var parser=new DOMParser();
        var doc=parser.parseFromString(html,'text/html');
        var newMain=doc.querySelector('#main')||doc.querySelector('main');
        if(!newMain){location.href=newUrl;return}
        var base='../'+newTs+'/';
        newMain.querySelectorAll('[href]').forEach(function(el){
          var h=el.getAttribute('href');
          if(h&&!/^(https?:|mailto:|#|\\/\\/)/.test(h)&&!h.startsWith('/'))
            el.setAttribute('href',base+h);
        });
        newMain.querySelectorAll('[src]').forEach(function(el){
          var s=el.getAttribute('src');
          if(s&&!/^(https?:|data:|blob:|\\/\\/)/.test(s)&&!s.startsWith('/'))
            el.setAttribute('src',base+s);
        });
        var cur=document.querySelector('#main')||document.querySelector('main');
        if(cur)cur.innerHTML=newMain.innerHTML;
        /* Re-render mermaid diagrams in the new content */
        var diagrams=document.querySelectorAll('pre.mermaid');
        if(diagrams.length&&window.mermaid){
          diagrams.forEach(function(el){
            if(!el.getAttribute('data-source'))el.setAttribute('data-source',el.textContent);
            var src=el.getAttribute('data-source');
            if(src){el.removeAttribute('data-processed');el.textContent=src;}
          });
          var t=document.documentElement.getAttribute('data-theme')||'dark';
          try{
            mermaid.initialize({startOnLoad:false,theme:(t==='light')?'default':'dark',flowchart:{useMaxWidth:true,htmlLabels:true,curve:'basis'}});
            mermaid.run();
          }catch(e){console.warn('mermaid re-render:',e);}
        }
        curTs=newTs;
        var newHero=document.querySelector('.hero');
        if(newHero){
          for(var i=0;i<sel.options.length;i++)
            sel.options[i].selected=(sel.options[i].value===newTs);
          newHero.appendChild(wrap);
        }
        window.scrollTo({top:0,behavior:'smooth'});
        history.pushState({version:newTs},'',newUrl);
      }).catch(function(){location.href=newUrl});
    });
    window.addEventListener('popstate',function(){location.reload()});
  }).catch(function(){});
})();"""


def build_snippet() -> str:
    return (
        f"\n{MARKER_START}\n"
        f"<style>{SWITCHER_CSS}</style>\n"
        f"<script>{SWITCHER_JS}</script>\n"
        f"{MARKER_END}\n"
    )


def strip_old_snippet(html: str) -> str:
    """Remove any previously injected version-switcher block."""
    return re.sub(
        rf"\n?{re.escape(MARKER_START)}.*?{re.escape(MARKER_END)}\n?",
        "",
        html,
        flags=re.DOTALL,
    )


def inject_into_file(index_path: Path, dry_run: bool = False) -> bool:
    """Inject the version switcher into an index.html. Returns True if changed."""
    text = index_path.read_text(encoding="utf-8", errors="ignore")
    clean = strip_old_snippet(text)

    # Inject just before </body>
    if "</body>" not in clean:
        return False

    snippet = build_snippet()
    new_text = clean.replace("</body>", snippet + "</body>")

    if new_text == text:
        return False

    if not dry_run:
        index_path.write_text(new_text, encoding="utf-8")
    return True


def process_project(project_dir: Path, dry_run: bool = False) -> int:
    """Inject version switcher into all versions of a project. Returns count."""
    vj = project_dir / "versions.json"
    if not vj.is_file():
        return 0

    versions = json.loads(vj.read_text(encoding="utf-8"))
    if len(versions) < 1:
        return 0

    count = 0
    for v in versions:
        ts = v["timestamp"]
        idx = project_dir / ts / "index.html"
        if not idx.is_file():
            continue
        changed = inject_into_file(idx, dry_run=dry_run)
        if changed:
            count += 1
            tag = " (dry-run)" if dry_run else ""
            print(f"  {idx.relative_to(WIKI_DIR)}{tag}")

    return count


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    dry_run = "--check" in sys.argv

    if args:
        dirs = [WIKI_DIR / name for name in args]
    else:
        dirs = sorted(
            d for d in WIKI_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    total = 0
    for d in dirs:
        if not d.is_dir():
            continue
        n = process_project(d, dry_run=dry_run)
        total += n

    action = "Would inject into" if dry_run else "Injected version switcher into"
    print(f"{action} {total} file(s).")


if __name__ == "__main__":
    main()
