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
