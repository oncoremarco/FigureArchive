"""Fetch official Fandom wiki XML database dumps (no scraping).

Fandom exposes an *official* compressed XML database dump for each wiki, linked
from that wiki's ``Special:Statistics`` page. This module resolves and downloads
that dump — it does NOT crawl or scrape article pages.

IMPORTANT — data quality and licensing:
  * Fandom wikis are community-edited. Dumps are **neither exhaustive nor
    guaranteed accurate**; treat imported data as a starting point to be
    reviewed, not authoritative.
  * Fandom content is licensed **CC-BY-SA** (unless a wiki states otherwise).
    Anything derived from a dump must preserve attribution to the source wiki
    and remain share-alike. The manifest written alongside each dump records
    the source and license so downstream import can surface it.

This module is designed to run on the END USER's machine (normal internet).
It cannot fetch from the restricted CI/dev sandbox (egress allowlisted).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

USER_AGENT = "FigureArchive-DumpFetcher/0.1 (+https://github.com/oncoremarco/figurearchive)"

LICENSE_NOTE = "CC-BY-SA (Fandom community content); attribution + share-alike required."
ACCURACY_NOTE = (
    "Community-edited source — not exhaustive and not guaranteed accurate. "
    "Review imported data before relying on it."
)


@dataclass
class FandomWiki:
    """A registered Fandom wiki we know how to pull a dump from."""
    key: str               # short id used in our app
    name: str              # display name
    subdomain: str         # <subdomain>.fandom.com
    note: str = ""

    @property
    def base_url(self) -> str:
        return f"https://{self.subdomain}.fandom.com"


# Starter set. The user is curating more on their end — add to this freely.
STARTER_WIKIS: dict[str, FandomWiki] = {
    "transformers": FandomWiki(
        key="transformers",
        name="Teletraan I: The Transformers Wiki",
        subdomain="transformers",
        note="Hasbro/Takara Transformers toylines and characters.",
    ),
    "mightymax": FandomWiki(
        key="mightymax",
        name="Mighty Max Wiki",
        subdomain="mightymax",
        note="Bluebird/Mattel Mighty Max playsets and figures.",
    ),
    "mcdonalds": FandomWiki(
        key="mcdonalds",
        name="Kids Meal Toys Wiki (McDonald's)",
        subdomain="kidsmeal",
        note="McDonald's Happy Meal toy lines (Changeables, etc.).",
    ),
}


@dataclass
class DumpResult:
    wiki_key: str
    kind: str
    dump_url: str
    local_path: Path
    manifest_path: Path
    bytes_downloaded: int
    retrieved_at: str
    warnings: list[str] = field(default_factory=list)


def _session():
    import requests
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def resolve_dump_url(subdomain: str, kind: str = "current", *, session=None) -> str:
    """Return the .7z dump URL for a wiki by parsing its Special:Statistics page.

    kind: "current" (current revision of each page) or "full" (with history).
    Raises RuntimeError if no matching dump link is found.
    """
    from bs4 import BeautifulSoup

    sess = session or _session()
    base = f"https://{subdomain}.fandom.com"
    stats_url = f"{base}/wiki/Special:Statistics"
    resp = sess.get(stats_url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    # The page links to dump files whose hrefs contain pages_current.xml /
    # pages_full.xml (compressed as .7z). Match resiliently on the href text.
    needle = "pages_full.xml" if kind == "full" else "pages_current.xml"
    candidates: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if needle in href:
            candidates.append(urljoin(stats_url, href))

    if not candidates:
        raise RuntimeError(
            f"No '{kind}' dump link found on {stats_url}. The dump may be stale or "
            f"missing — an admin can regenerate it from Special:Statistics."
        )
    # Prefer the first; Fandom typically lists a single current/full link.
    return candidates[0]


def download_dump(
    wiki_key: str,
    dest_dir: str | Path,
    *,
    kind: str = "current",
    session=None,
) -> DumpResult:
    """Resolve and download a wiki's dump into dest_dir, writing a manifest.

    Returns a DumpResult. Network-bound; run on the user's machine.
    """
    wiki = STARTER_WIKIS.get(wiki_key)
    subdomain = wiki.subdomain if wiki else wiki_key
    name = wiki.name if wiki else wiki_key

    sess = session or _session()
    dump_url = resolve_dump_url(subdomain, kind=kind, session=sess)

    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    filename = dump_url.rsplit("/", 1)[-1] or f"{subdomain}_{kind}.xml.7z"
    local_path = dest / filename

    total = 0
    with sess.get(dump_url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(local_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    fh.write(chunk)
                    total += len(chunk)

    retrieved_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "wiki_key": wiki_key,
        "wiki_name": name,
        "subdomain": subdomain,
        "source_url": f"https://{subdomain}.fandom.com",
        "dump_url": dump_url,
        "kind": kind,
        "file": filename,
        "bytes": total,
        "retrieved_at": retrieved_at,
        "license": LICENSE_NOTE,
        "accuracy": ACCURACY_NOTE,
    }
    manifest_path = local_path.with_suffix(local_path.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return DumpResult(
        wiki_key=wiki_key,
        kind=kind,
        dump_url=dump_url,
        local_path=local_path,
        manifest_path=manifest_path,
        bytes_downloaded=total,
        retrieved_at=retrieved_at,
        warnings=[ACCURACY_NOTE],
    )


def decompress_dump(archive_path: str | Path) -> Path:
    """Extract the .7z dump's XML into the same directory; return the XML path."""
    import py7zr

    archive = Path(archive_path)
    out_dir = archive.parent
    with py7zr.SevenZipFile(archive, "r") as z:
        names = z.getnames()
        z.extractall(path=out_dir)
    # Return the first .xml extracted
    for n in names:
        if n.endswith(".xml"):
            return out_dir / n
    raise RuntimeError(f"No .xml found inside {archive}")
