"""Shared helpers for the Overview Pass (wiki overview-page generation).

Pure functions only. No I/O here; CLI drivers live in sibling scripts.
"""
from __future__ import annotations

import html as stdlib_html


def escape_for_attribute(inner_html: str) -> str:
    """Escape a chunk of HTML so it can be embedded inside an HTML attribute
    value surrounded by double quotes.

    Uses `html.escape(..., quote=True)` so ``"``, ``'``, ``<``, ``>``, and ``&``
    are all encoded. Round-trips via `html.unescape`.
    """
    return stdlib_html.escape(inner_html, quote=True)


import re
from html.parser import HTMLParser
from typing import Tuple


class _LayerExtractor(HTMLParser):
    """Collect the raw HTML inside <section data-layer="primer"> and
    <section data-layer="core-idea"> blocks, in document order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._stack: list[str] = []  # active target layer names
        self._depth: list[int] = []  # section depth when we entered each target
        self._buffers: dict[str, list[str]] = {"primer": [], "core-idea": []}
        self._current_section_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "section":
            self._current_section_depth += 1
            attrdict = dict(attrs)
            layer = attrdict.get("data-layer")
            if layer in self._buffers:
                self._stack.append(layer)
                self._depth.append(self._current_section_depth)
                return
        if self._stack:
            self._buffers[self._stack[-1]].append(self.get_starttag_text() or "")

    def handle_endtag(self, tag):
        if tag == "section":
            if self._stack and self._depth[-1] == self._current_section_depth:
                self._stack.pop()
                self._depth.pop()
            else:
                if self._stack:
                    self._buffers[self._stack[-1]].append(f"</{tag}>")
            self._current_section_depth -= 1
            return
        if self._stack:
            self._buffers[self._stack[-1]].append(f"</{tag}>")

    def handle_startendtag(self, tag, attrs):
        if self._stack:
            self._buffers[self._stack[-1]].append(self.get_starttag_text() or "")

    def handle_data(self, data):
        if self._stack:
            self._buffers[self._stack[-1]].append(data)

    def handle_entityref(self, name):
        if self._stack:
            self._buffers[self._stack[-1]].append(f"&{name};")

    def handle_charref(self, name):
        if self._stack:
            self._buffers[self._stack[-1]].append(f"&#{name};")

    @property
    def primer_html(self) -> str:
        return "".join(self._buffers["primer"]).strip()

    @property
    def core_idea_html(self) -> str:
        return "".join(self._buffers["core-idea"]).strip()


_PARAGRAPH_RE = re.compile(r"<p\b[^>]*>.*?</p>", re.IGNORECASE | re.DOTALL)


def extract_preview_html(page_html: str) -> Tuple[str, bool]:
    """Return (combined_preview_html, retrofitted).

    If the page has ``<section data-layer="primer">`` and
    ``<section data-layer="core-idea">`` blocks, concatenate their inner HTML
    and return ``retrofitted=False``.

    Otherwise fall back to the first ``<p>`` as primer and the next two ``<p>``
    as core-idea, returning ``retrofitted=True``. The caller is responsible
    for prepending a retrofit banner.
    """
    extractor = _LayerExtractor()
    extractor.feed(page_html)
    primer = extractor.primer_html
    core_idea = extractor.core_idea_html
    if primer or core_idea:
        return (f"{primer}\n{core_idea}".strip(), False)

    paragraphs = _PARAGRAPH_RE.findall(page_html)
    if not paragraphs:
        return ("", True)
    primer = paragraphs[0]
    core_idea = "".join(paragraphs[1:3])
    return (f"{primer}\n{core_idea}".strip(), True)
