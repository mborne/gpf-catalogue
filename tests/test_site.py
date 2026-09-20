"""Tests of the static site build.

These touch the file system, like `test_catalogue.py`, and work in `tmp_path`. They
check what the build guarantees — the site is self contained, a deep link survives a
cold load, and two builds of the same catalogue are identical — not what the pages
look like.

The front end is built by Vite, which these tests do not run: a stand-in `dist/` is
enough to check the assembly, and it keeps the suite offline and free of node. The
two tests that need the real bundle skip when `web/dist` has not been built; the
Pages workflow builds it before running them.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import json
import re

import pytest

from gpf_catalogue.model import CatalogueRecord, Link, LinkType, ResourceType
from gpf_catalogue.parse import write_catalogue
from gpf_catalogue.site import DEFAULT_ASSETS_DIR, build_site


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


@pytest.fixture
def assets(tmp_path):
    """A stand-in for `web/dist`: the shape Vite writes, without running it."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        '<!doctype html><html><head>'
        '<script type="module" src="/assets/index-aaa.js"></script>'
        '<link rel="stylesheet" href="/assets/index-aaa.css">'
        "</head><body><div id=\"root\"></div></body></html>",
        encoding="utf-8",
    )
    (dist / "assets" / "index-aaa.js").write_text("/* bundle */", encoding="utf-8")
    (dist / "assets" / "index-aaa.css").write_text("/* styles */", encoding="utf-8")
    return dist


@pytest.fixture
def built():
    """The real `web/dist`, or a skip when the front end has not been built."""
    if not (DEFAULT_ASSETS_DIR / "index.html").is_file():
        pytest.skip("web/dist not built; run 'npm ci && npm run build' in web/")
    return DEFAULT_ASSETS_DIR


def test_the_site_is_self_contained(catalogue, assets, tmp_path):
    """Everything the site needs sits in one directory, so it can be moved or zipped."""
    report = build_site(catalogue, output_dir=tmp_path / "site", assets_dir=assets)

    assert report.records == 2
    assert set(report.files) == {
        "index.html",
        "assets/index-aaa.js",
        "assets/index-aaa.css",
        "404.html",
        "catalogue.json",
        "stats.json",
    }
    for name in report.files:
        assert (tmp_path / "site" / name).is_file()


def test_an_unbuilt_front_end_is_reported_rather_than_skipped(catalogue, tmp_path):
    """A site without its application is not a site; say what to run."""
    with pytest.raises(FileNotFoundError, match="npm"):
        build_site(catalogue, output_dir=tmp_path / "site", assets_dir=tmp_path / "none")


def test_a_deep_link_is_served_by_a_copy_of_the_entry_document(
    catalogue, assets, tmp_path
):
    """`/records/{fileIdentifier}` is a route, and a static host has no rewrite rule.

    GitHub Pages answers an unknown path with `404.html`, so that document is the
    application itself; otherwise a link to a record would only work after a click,
    never when pasted.
    """
    build_site(catalogue, output_dir=tmp_path / "site", assets_dir=assets)

    site = tmp_path / "site"
    assert (site / "404.html").read_bytes() == (site / "index.html").read_bytes()


def test_the_catalogue_is_copied_not_referenced(catalogue, assets, tmp_path):
    """The site carries its own copy: it must survive `data/` being deleted."""
    build_site(catalogue, output_dir=tmp_path / "site", assets_dir=assets)

    copied = json.loads((tmp_path / "site" / "catalogue.json").read_text(encoding="utf-8"))
    assert copied["count"] == 2


def test_the_statistics_describe_the_catalogue(catalogue, assets, tmp_path):
    build_site(catalogue, output_dir=tmp_path / "site", assets_dir=assets)
    stats = json.loads((tmp_path / "site" / "stats.json").read_text(encoding="utf-8"))

    assert stats["count"] == 2
    assert stats["source"] == "https://data.geopf.fr/csw"
    # The records page filters on these, so they must be there rather than
    # recomputed in the browser.
    facets = {item["fileIdentifier"]: item for item in stats["recordFacets"]}
    assert facets["SAMPLE"]["publisher"] == "ign.fr"
    assert facets["SAMPLE"]["licenceFamily"] == "Licence Ouverte"
    assert facets["OTHER"]["publisher"] is None


def test_two_builds_are_byte_identical(catalogue, assets, tmp_path):
    """No timestamp anywhere, so a diff between two builds is a real change."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_site(catalogue, output_dir=first, assets_dir=assets)
    build_site(catalogue, output_dir=second, assets_dir=assets)

    for name in ("index.html", "404.html", "catalogue.json", "stats.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    assert (first / "assets" / "index-aaa.js").read_bytes() == (
        second / "assets" / "index-aaa.js"
    ).read_bytes()


def test_rebuilding_over_an_existing_site_replaces_it(catalogue, assets, tmp_path):
    """The build is rerun constantly; it must not need a clean directory."""
    target = tmp_path / "site"
    build_site(catalogue, output_dir=target, assets_dir=assets)
    (target / "stats.json").write_text("stale", encoding="utf-8")

    build_site(catalogue, output_dir=target, assets_dir=assets)

    assert json.loads((target / "stats.json").read_text(encoding="utf-8"))["count"] == 2


def test_assets_of_a_previous_build_do_not_pile_up(catalogue, assets, tmp_path):
    """Asset names carry a content hash, so a rebuild writes new ones."""
    target = tmp_path / "site"
    build_site(catalogue, output_dir=target, assets_dir=assets)

    (assets / "assets" / "index-aaa.js").rename(assets / "assets" / "index-bbb.js")
    build_site(catalogue, output_dir=target, assets_dir=assets)

    assert (target / "assets" / "index-bbb.js").is_file()
    assert not (target / "assets" / "index-aaa.js").exists()


def test_the_page_loads_its_assets_from_the_site(catalogue, built, tmp_path):
    """No CDN: everything the page loads is beside it, so it works offline.

    React is bundled into those assets rather than fetched from unpkg or esm.sh,
    which is what keeps the site publishable as a directory. Only what the browser
    *fetches* counts: an XML namespace inside the inline SVG favicon is a URI, not a
    request, and the outbound links of a record are the point of the catalogue.
    """
    build_site(catalogue, output_dir=tmp_path / "site", assets_dir=built)
    page = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")

    loaded = re.findall(r'<(?:script|link)[^>]*?(?:src|href)="([^"]+)"', page)
    assert loaded, "no asset found, the regex stopped matching the page"
    for target in loaded:
        assert not target.startswith(("http://", "https://", "//")), target
        referenced = tmp_path / "site" / target.lstrip("/").split("?")[0]
        if not target.startswith("data:"):
            assert referenced.is_file(), target


def test_the_built_application_declares_every_route(built):
    """The four routes of the issue are in the bundle, not only in the source."""
    bundle = "".join(
        path.read_text(encoding="utf-8")
        for path in sorted((built / "assets").glob("*.js"))
    )
    for route in ("overview", "records", "records/:fileIdentifier", "quality"):
        assert route in bundle, route


def test_a_missing_catalogue_is_reported_rather_than_built_around(assets, tmp_path):
    with pytest.raises(FileNotFoundError):
        build_site(tmp_path / "absent.json", output_dir=tmp_path / "site", assets_dir=assets)
