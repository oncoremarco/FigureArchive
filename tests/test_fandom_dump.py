"""Offline tests for the Fandom dump tooling.

Runs without network: the XML parser is exercised on a fixture, and dump-URL
resolution is exercised against a fake session that mocks S3 HEAD responses.
Run with:  python -m tests.test_fandom_dump
"""

from pathlib import Path

from figure_archive.core import fandom_dump, mediawiki_xml

FIXTURES = Path(__file__).parent / "fixtures"


class _FakeHeadResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code


class _FakeS3Session:
    """Simulates S3 HEAD responses; GET is unused by resolve_dump_url."""
    def __init__(self, status_code=200):
        self._status_code = status_code

    def head(self, url, **kwargs):
        return _FakeHeadResponse(self._status_code)


def test_iter_pages_and_categories():
    pages = list(mediawiki_xml.iter_pages(FIXTURES / "sample_dump.xml"))
    assert len(pages) == 3, len(pages)
    titles = [p.title for p in pages]
    assert "Optimus Prime (G1)" in titles
    prime = next(p for p in pages if p.title.startswith("Optimus"))
    assert prime.namespace == 0
    assert prime.categories == ["1984 toys", "Autobot Cars"], prime.categories
    grim = next(p for p in pages if p.title.startswith("Grimlock"))
    # Whitespace inside [[Category: Dinobots ]] must be trimmed
    assert grim.categories == ["1985 toys", "Dinobots"], grim.categories
    print("✓ iter_pages + category extraction")


def test_main_namespace_only():
    pages = list(mediawiki_xml.iter_pages(FIXTURES / "sample_dump.xml",
                                          main_namespace_only=True))
    assert len(pages) == 2, len(pages)  # Category page excluded
    print("✓ main_namespace_only filter")


def test_index_dump():
    summary = mediawiki_xml.index_dump(FIXTURES / "sample_dump.xml")
    assert summary["pages"] == 2
    assert summary["categories"]["1984 toys"] == 1
    assert "Dinobots" in summary["categories"]
    print("✓ index_dump summary")


def test_resolve_dump_url_current_and_full():
    sess = _FakeS3Session(200)
    cur = fandom_dump.resolve_dump_url("transformers", kind="current", session=sess)
    assert cur.endswith("transformers_pages_current.xml.7z"), cur
    full = fandom_dump.resolve_dump_url("transformers", kind="full", session=sess)
    assert full.endswith("transformers_pages_full.xml.7z"), full
    print("✓ resolve_dump_url (current + full)")


def test_resolve_dump_url_missing():
    sess = _FakeS3Session(403)
    try:
        fandom_dump.resolve_dump_url("transformers", session=sess)
    except RuntimeError as exc:
        assert "No 'current' dump available" in str(exc)
        print("✓ resolve_dump_url raises when missing")
    else:
        raise AssertionError("expected RuntimeError")


def test_registry_has_starters():
    keys = set(fandom_dump.STARTER_WIKIS)
    assert {"transformers", "mightymax", "mcdonalds"} <= keys, keys
    print("✓ starter registry present")


if __name__ == "__main__":
    test_iter_pages_and_categories()
    test_main_namespace_only()
    test_index_dump()
    test_resolve_dump_url_current_and_full()
    test_resolve_dump_url_missing()
    test_registry_has_starters()
    print("\nAll Fandom dump tests passed.")
