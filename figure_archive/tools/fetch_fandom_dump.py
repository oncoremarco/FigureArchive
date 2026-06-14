"""CLI: download + index official Fandom XML dumps.

Run on a machine with normal internet (NOT the restricted dev sandbox):

    python -m figure_archive.tools.fetch_fandom_dump --list
    python -m figure_archive.tools.fetch_fandom_dump transformers mightymax mcdonalds
    python -m figure_archive.tools.fetch_fandom_dump transformers --dest ./dumps --index

Dumps are Fandom's official database exports (no scraping). Community-edited
data: not exhaustive, not guaranteed accurate. CC-BY-SA — keep attribution.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from figure_archive.core import fandom_dump


def _print_list() -> None:
    print("Registered Fandom wikis:\n")
    for key, w in fandom_dump.STARTER_WIKIS.items():
        print(f"  {key:<14} {w.name}")
        print(f"  {'':<14} {w.base_url}")
        if w.note:
            print(f"  {'':<14} {w.note}")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wikis", nargs="*", help="wiki keys to download (see --list)")
    parser.add_argument("--list", action="store_true", help="list registered wikis")
    parser.add_argument("--dest", default="./dumps", help="output directory")
    parser.add_argument("--kind", choices=["current", "full"], default="current")
    parser.add_argument("--index", action="store_true",
                        help="decompress and print a category index after download")
    args = parser.parse_args(argv)

    if args.list or not args.wikis:
        _print_list()
        if not args.wikis:
            return 0

    print("⚠  Fandom data is community-edited: not exhaustive, not guaranteed")
    print("   accurate, and CC-BY-SA (keep attribution). Review before relying.\n")

    dest = Path(args.dest)
    exit_code = 0
    for key in args.wikis:
        try:
            print(f"→ {key}: resolving dump…")
            result = fandom_dump.download_dump(key, dest, kind=args.kind)
            mb = result.bytes_downloaded / 1_048_576
            print(f"  saved {result.local_path}  ({mb:.1f} MB)")
            print(f"  manifest {result.manifest_path}")

            if args.index:
                from figure_archive.core import mediawiki_xml
                print("  decompressing…")
                xml_path = fandom_dump.decompress_dump(result.local_path)
                summary = mediawiki_xml.index_dump(xml_path)
                print(f"  {summary['pages']} article pages")
                top = list(summary["categories"].items())[:15]
                print("  top categories:")
                for cat, n in top:
                    print(f"    {n:>5}  {cat}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ {key}: {exc}", file=sys.stderr)
            exit_code = 1
        print()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
