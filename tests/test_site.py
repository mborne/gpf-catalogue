"""Tests of the static site build.

These touch the file system, like `test_catalogue.py`, and work in `tmp_path`. They
check what the build guarantees — the site is self contained, and two builds of the
same catalogue are identical — not what the page looks like.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import json
import re

import pytest

from gpf_catalogue.model import CatalogueRecord, Link, LinkType, ResourceType
from gpf_catalogue.parse import write_catalogue
from gpf_catalogue.site import build_site


@pytest.fixture
def catalogue(tmp_path):
    """An aggregated catalogue of two records, written where the build reads it."""
    records = [
        CatalogueRecord(
            file_identifier="SAMPLE",
            type=ResourceType.DATASET,
            title="A sample",
            contact_email="someone@ign.fr",
            licence="Licence Ouverte / Open License",
            links=[Link(type=LinkType.WFS, url="https://data.geopf.fr/wfs/ows")],
        ),
        CatalogueRecord(file_identifier="OTHER", type=ResourceType.SERVICE),
    ]
    path = tmp_path / "catalogue.json"
    write_catalogue(records, path)
    return path


def test_the_site_is_self_contained(catalogue, tmp_path):
    """Everything the page needs sits in one directory, so it can be moved or zipped."""
    report = build_site(catalogue, output_dir=tmp_path / "site")

    assert report.records == 2
    assert set(report.files) == {
        "app.js",
        "index.html",
        "style.css",
        "catalogue.json",
        "stats.json",
    }
    for name in report.files:
        assert (tmp_path / "site" / name).is_file()


def test_the_catalogue_is_copied_not_referenced(catalogue, tmp_path):
    """The site carries its own copy: it must survive `data/` being deleted."""
    build_site(catalogue, output_dir=tmp_path / "site")

    copied = json.loads((tmp_path / "site" / "catalogue.json").read_text(encoding="utf-8"))
    assert copied["count"] == 2


def test_the_statistics_describe_the_catalogue(catalogue, tmp_path):
    build_site(catalogue, output_dir=tmp_path / "site")
    stats = json.loads((tmp_path / "site" / "stats.json").read_text(encoding="utf-8"))

    assert stats["count"] == 2
    assert stats["source"] == "https://data.geopf.fr/csw"
    # The page filters on these, so they must be there rather than recomputed in JS.
    facets = {item["fileIdentifier"]: item for item in stats["recordFacets"]}
    assert facets["SAMPLE"]["publisher"] == "ign.fr"
    assert facets["SAMPLE"]["licenceFamily"] == "Licence Ouverte"
    assert facets["OTHER"]["publisher"] is None


def test_two_builds_are_byte_identical(catalogue, tmp_path):
    """No timestamp anywhere, so a diff between two builds is a real change."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_site(catalogue, output_dir=first)
    build_site(catalogue, output_dir=second)

    for name in ("index.html", "app.js", "style.css", "catalogue.json", "stats.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_rebuilding_over_an_existing_site_replaces_it(catalogue, tmp_path):
    """The build is rerun constantly; it must not need a clean directory."""
    target = tmp_path / "site"
    build_site(catalogue, output_dir=target)
    (target / "stats.json").write_text("stale", encoding="utf-8")

    build_site(catalogue, output_dir=target)

    assert json.loads((target / "stats.json").read_text(encoding="utf-8"))["count"] == 2


def test_the_page_loads_its_assets_by_relative_path(catalogue, tmp_path):
    """No CDN: everything the page loads is beside it, so it works offline.

    Only what the browser *fetches* counts. An XML namespace inside the inline SVG
    favicon is a URI, not a request, and the outbound links of a record are the
    point of the catalogue.
    """
    build_site(catalogue, output_dir=tmp_path / "site")
    page = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")

    assert 'href="style.css"' in page
    assert 'src="app.js"' in page

    loaded = re.findall(r'<(?:script|link)[^>]*?(?:src|href)="([^"]+)"', page)
    assert loaded, "no asset found, the regex stopped matching the page"
    for target in loaded:
        assert not target.startswith(("http://", "https://", "//")), target


def test_a_missing_catalogue_is_reported_rather_than_built_around(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_site(tmp_path / "absent.json", output_dir=tmp_path / "site")
