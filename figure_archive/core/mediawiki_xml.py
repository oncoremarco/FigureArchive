"""Streaming parser for MediaWiki XML export dumps (as produced by Fandom).

Reads a (decompressed) ``*.xml`` export and yields one :class:`WikiPage` per
``<page>`` element using incremental parsing, so multi-hundred-MB dumps don't
have to be held in memory. This is the low-level index over a dump; turning
pages into catalog items (franchise/line/group/item) is a separate, wiki-specific
step layered on top.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

# Categories embedded in wikitext, e.g. [[Category:1984 toys]]
_CATEGORY_RE = re.compile(r"\[\[\s*Category\s*:\s*([^\]|]+)", re.IGNORECASE)


@dataclass
class WikiPage:
    title: str
    namespace: int
    page_id: str | None
    timestamp: str | None
    text: str
    categories: list[str] = field(default_factory=list)


def _localname(tag: str) -> str:
    """Strip the XML namespace from a tag like '{...}page' -> 'page'."""
    return tag.rsplit("}", 1)[-1]


def iter_pages(xml_path: str | Path, *, main_namespace_only: bool = False) -> Iterator[WikiPage]:
    """Yield WikiPage objects from a MediaWiki XML export.

    main_namespace_only: if True, only yield namespace-0 (article) pages,
    skipping Category/Template/File/Talk pages.
    """
    from lxml import etree

    context = etree.iterparse(str(xml_path), events=("end",))
    for _event, elem in context:
        if _localname(elem.tag) != "page":
            continue

        title = None
        namespace = 0
        page_id = None
        timestamp = None
        text = ""

        for child in elem:
            name = _localname(child.tag)
            if name == "title":
                title = child.text or ""
            elif name == "ns":
                try:
                    namespace = int(child.text)
                except (TypeError, ValueError):
                    namespace = 0
            elif name == "id" and page_id is None:
                page_id = child.text
            elif name == "revision":
                for rc in child:
                    rname = _localname(rc.tag)
                    if rname == "timestamp":
                        timestamp = rc.text
                    elif rname == "text":
                        text = rc.text or ""

        if not (main_namespace_only and namespace != 0):
            if title is not None:
                yield WikiPage(
                    title=title,
                    namespace=namespace,
                    page_id=page_id,
                    timestamp=timestamp,
                    text=text,
                    categories=_extract_categories(text),
                )

        # Free processed element (and its now-useless preceding siblings)
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]


def _extract_categories(text: str) -> list[str]:
    seen: list[str] = []
    for m in _CATEGORY_RE.finditer(text or ""):
        cat = m.group(1).strip()
        if cat and cat not in seen:
            seen.append(cat)
    return seen


def index_dump(xml_path: str | Path, *, main_namespace_only: bool = True) -> dict:
    """Build a quick summary index of a dump: page count + category histogram.

    Useful for a 'what's in here' preview before doing any structured import.
    """
    pages = 0
    category_counts: dict[str, int] = {}
    for page in iter_pages(xml_path, main_namespace_only=main_namespace_only):
        pages += 1
        for cat in page.categories:
            category_counts[cat] = category_counts.get(cat, 0) + 1
    return {
        "pages": pages,
        "categories": dict(
            sorted(category_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
    }
