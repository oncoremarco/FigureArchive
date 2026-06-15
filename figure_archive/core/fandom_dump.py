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


# Fandom/Wikia dumps are hosted on plain S3 (NOT behind the Cloudflare bot wall
# that 403s the wiki itself), at a predictable path keyed by the wiki's database
# name. Hitting S3 directly is both reliable and avoids the protected pages.
S3_DUMPS_BASE = "https://s3.amazonaws.com/wikia_xml_dumps"


@dataclass
class FandomWiki:
    """A registered Fandom wiki we know how to pull a dump from."""
    key: str               # short id used in our app
    name: str              # display name
    subdomain: str         # <subdomain>.fandom.com
    note: str = ""
    dbname: str | None = None  # S3 dump db name; defaults to subdomain

    @property
    def base_url(self) -> str:
        return f"https://{self.subdomain}.fandom.com"

    @property
    def db(self) -> str:
        return self.dbname or self.subdomain


def s3_dump_url(dbname: str, kind: str = "current") -> str:
    """Build the direct S3 URL for a wiki's dump.

    Pattern: <base>/<c>/<cc>/<db>_pages_<current|full>.xml.7z
    e.g. .../t/tr/transformers_pages_current.xml.7z
    """
    db = dbname.lower()
    suffix = "full" if kind == "full" else "current"
    return f"{S3_DUMPS_BASE}/{db[0]}/{db[:2]}/{db}_pages_{suffix}.xml.7z"


# Starter set. The user is curating more on their end — add to this freely.
#
# IMPORTANT: a wiki only has an S3 dump if one was *generated on demand* (an
# admin clicks "request" on Special:Statistics). Most wikis — including big
# active ones — have NO dump until requested, and S3 answers 403 for the
# missing object. That 403 is expected, not a bug in this tool. `muppet` is
# included as a known-good wiki whose dump exists today, so the full
# download→decompress→index pipeline can be verified end-to-end.
STARTER_WIKIS: dict[str, FandomWiki] = {
    "muppet": FandomWiki(
        key="muppet",
        name="Muppet Wiki",
        subdomain="muppet",
        note="KNOWN-GOOD test wiki — its dump exists on S3 today. Not toys, "
             "but proves the pipeline works end-to-end.",
    ),
    "transformers": FandomWiki(
        key="transformers",
        name="Teletraan I: The Transformers Wiki",
        subdomain="transformers",
        note="Hasbro/Takara Transformers toylines and characters. NOTE: no S3 "
             "dump generated yet (403) — an admin must request one at "
             "Special:Statistics first.",
    ),
    "mightymax": FandomWiki(
        key="mightymax",
        name="Mighty Max Wiki",
        subdomain="mightymax",
        note="Bluebird/Mattel Mighty Max playsets and figures. NOTE: no S3 "
             "dump generated yet (403) — request one at Special:Statistics first.",
    ),
    "mcdonalds": FandomWiki(
        key="mcdonalds",
        name="Kids Meal Toys Wiki (McDonald's)",
        subdomain="kidsmeal",
        note="McDonald's Happy Meal toys. NOTE: no S3 dump generated yet — an "
             "admin must request one from Special:Statistics before it can be pulled.",
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


def _session(referer: str | None = None):
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        # Some S3 bucket policies check Referer; send the wiki's stats page.
        "Referer": referer or "https://www.fandom.com/",
    })
    return s


def _explain_s3_error(resp, url: str, subdomain: str) -> str:
    """Turn an S3 non-200 GET into a human-readable diagnosis.

    S3 returns the real reason in an XML body (<Code>/<Message>). The most
    important case for old Fandom dumps is an archived object: the file still
    exists (HEAD says 200) but has been lifecycled into Glacier/cold storage,
    so GET is denied until someone who owns the bucket restores it — which we
    cannot do. In that case a freshly regenerated dump is the only path.
    """
    import re

    code = ""
    try:
        body = resp.text or ""
        m = re.search(r"<Code>([^<]+)</Code>", body)
        if m:
            code = m.group(1).strip()
        mm = re.search(r"<Message>([^<]+)</Message>", body)
        message = mm.group(1).strip() if mm else ""
    except Exception:  # noqa: BLE001
        message = ""

    base = f"S3 returned {resp.status_code} for {url}"
    if code:
        base += f" (S3 code: {code})"

    if code in ("InvalidObjectState",) or "glacier" in message.lower() or \
            "storage class" in message.lower():
        return (
            f"{base}. The dump file exists but has been moved to cold/archival "
            f"storage by Fandom and is not directly downloadable. Only Fandom "
            f"can restore it. Your best path is a freshly regenerated dump — "
            f"request one at https://{subdomain}.fandom.com/wiki/Special:Statistics "
            f"and retry once it's rebuilt (usually a few hours)."
        )
    if resp.status_code == 403:
        return (
            f"{base}. Access is denied even though a HEAD check saw the object. "
            f"This usually means the stored dump is archived/cold or the bucket "
            f"won't serve it to direct clients. Request a fresh dump at "
            f"https://{subdomain}.fandom.com/wiki/Special:Statistics and retry. "
            + (f"S3 said: {message}" if message else "")
        )
    return base + (f". S3 said: {message}" if message else "")


def resolve_dump_url(dbname: str, kind: str = "current", *, session=None) -> str:
    """Return a verified S3 dump URL for a wiki, or raise if none exists.

    Hits S3 directly (avoids Fandom's Cloudflare bot wall). A HEAD that isn't
    200 means no dump was generated for that wiki — Fandom only produces dumps
    on demand, so this is common.

    kind: "current" (current revision of each page) or "full" (with history).
    """
    sess = session or _session()
    url = s3_dump_url(dbname, kind=kind)
    resp = sess.head(url, timeout=30, allow_redirects=True)
    if resp.status_code != 200:
        raise RuntimeError(
            f"No '{kind}' dump available for '{dbname}' (S3 returned "
            f"{resp.status_code}). Fandom generates dumps on demand — an admin "
            f"can request one at https://{dbname}.fandom.com/wiki/Special:Statistics, "
            f"then it appears at {url}."
        )
    return url


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
    dbname = wiki.db if wiki else wiki_key
    name = wiki.name if wiki else wiki_key

    referer = f"https://{subdomain}.fandom.com/wiki/Special:Statistics"
    sess = session or _session(referer=referer)
    dump_url = resolve_dump_url(dbname, kind=kind, session=sess)

    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    filename = dump_url.rsplit("/", 1)[-1] or f"{subdomain}_{kind}.xml.7z"
    local_path = dest / filename

    total = 0
    with sess.get(dump_url, stream=True, timeout=120) as resp:
        if resp.status_code != 200:
            raise RuntimeError(_explain_s3_error(resp, dump_url, subdomain))
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
    try:
        import py7zr
    except ImportError as exc:
        raise RuntimeError(
            "py7zr is required to decompress .7z dumps — run: pip install py7zr "
            "(or pip install -r requirements.txt)."
        ) from exc

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
