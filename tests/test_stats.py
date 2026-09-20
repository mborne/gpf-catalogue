"""Tests of the aggregates the overview is built on.

Like `test_parse.py`, these run offline; unlike `test_catalogue.py`, they do not
need the file system either, because `compute_stats()` is a pure function. The
records are built by hand rather than parsed, so that each test states exactly the
shape it is about.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import json

import pytest

from gpf_catalogue.model import (
    CatalogueRecord,
    Link,
    LinkType,
    ResourceType,
    SpatialScope,
)
from gpf_catalogue.parse import write_catalogue
from gpf_catalogue.stats import (
    OTHER_LICENCE,
    UNDECLARED_LICENCE,
    compute_stats,
    coverage_markdown,
    licence_family,
    load_records,
    publication_year,
    publisher_of,
    write_stats,
)


def record(identifier: str = "R", **fields) -> CatalogueRecord:
    """Build a pivot record, defaulting everything the test does not care about."""
    fields.setdefault("type", ResourceType.DATASET)
    return CatalogueRecord(file_identifier=identifier, **fields)


def values(counts) -> list[tuple[str, int]]:
    """Flatten a list of `Count` into comparable tuples."""
    return [(item.value, item.count) for item in counts]


# --- ranking -----------------------------------------------------------------


def test_counts_are_ranked_by_frequency_then_alphabetically():
    """Ties are broken alphabetically, which is what makes the output byte stable.

    `Counter` keeps insertion order for equal counts, and insertion order depends
    on the order the records were read in.
    """
    stats = compute_stats(
        [
            record("a", topic_categories=["zebra", "common"]),
            record("b", topic_categories=["alpha", "common"]),
        ]
    )

    assert values(stats.by_topic_category) == [("common", 2), ("alpha", 1), ("zebra", 1)]


def test_a_record_counts_once_per_value_it_repeats():
    """A record declaring the same theme twice is one record, not two."""
    stats = compute_stats([record(inspire_themes=["Altitude", "Altitude"])])

    assert values(stats.by_inspire_theme) == [("Altitude", 1)]


def test_records_citing_no_spatial_scope_are_left_out():
    """An undeclared scope is not a scope, and 190 of the 326 records cite none.

    A bucket labelled *undeclared* would be the tallest bar of the chart and would
    say nothing about the extent of anything.
    """
    stats = compute_stats(
        [
            record("a", spatial_scope=SpatialScope.NATIONAL),
            record("b", spatial_scope=SpatialScope.LOCAL),
            record("c", spatial_scope=SpatialScope.NATIONAL),
            record("d"),
        ]
    )

    assert values(stats.by_spatial_scope) == [("national", 2), ("local", 1)]


def test_years_are_chronological_not_ranked():
    """A histogram of years reads left to right, so it is not sorted by count."""
    stats = compute_stats(
        [
            record("a", published="2022-01-01"),
            record("b", published="2021-06-30"),
            record("c", published="2022-11-02"),
        ]
    )

    assert values(stats.by_year) == [("2021", 1), ("2022", 2)]


def test_an_empty_year_is_drawn_at_zero_rather_than_skipped():
    """The catalogue publishes nothing between 1994 and 2008.

    Drawing those two as adjacent columns would draw a gap as if it were a step,
    and the axis would no longer be time.
    """
    stats = compute_stats(
        [record("a", published="2019"), record("b", published="2022")]
    )

    assert values(stats.by_year) == [
        ("2019", 1),
        ("2020", 0),
        ("2021", 0),
        ("2022", 1),
    ]


def test_rare_keywords_are_left_out():
    """432 of the 638 keywords of the catalogue are used once: they are not a facet."""
    records = [record(str(i), keywords=["shared"]) for i in range(5)]
    records.append(record("x", keywords=["shared", "once"]))

    stats = compute_stats(records)

    assert values(stats.top_keywords) == [("shared", 6)]


# --- derived values ----------------------------------------------------------


@pytest.mark.parametrize(
    ("published", "expected"),
    [
        ("Licence Ouverte / Open License (compatible ODC-BY, CC-BY 2.0)", "Licence Ouverte"),
        # The same licence, with the Etalab URL glued to its own label. The parser
        # keeps it because it is not an exact trailing repeat of the href.
        (
            (
                "Licence Ouverte / Open License (compatible ODC-BY, CC-BY 2.0) "
                "https://www.etalab.gouv.fr/licence-ouverte-open-licence"
            ),
            "Licence Ouverte",
        ),
        ("Licence Ouverte (version 2.0 d'avril 2017)", "Licence Ouverte"),
        ("Open Database License (ODbL)", "ODbL"),
        (
            (
                "Conditions générales d'utilisation disponibles ici : "
                "https://cartes.gouv.fr/cgu"
            ),
            "Terms of use of cartes.gouv.fr",
        ),
        (
            (
                "Base de données soumise aux conditions générales des licences "
                "d'EuroGeographics"
            ),
            "Terms of use of the producer",
        ),
        ("no conditions to access and use", "No condition stated"),
        ("Pas de restriction d'accès public selon INSPIRE", "No condition stated"),
        (None, UNDECLARED_LICENCE),
        ("", UNDECLARED_LICENCE),
    ],
)
def test_licence_families_follow_the_published_mapping(published, expected):
    assert licence_family(published) == expected


def test_an_unmapped_licence_is_surfaced_not_folded_into_the_nearest_family():
    """A growing `OTHER_LICENCE` means the mapping needs a rule, so it must show."""
    assert licence_family("Creative Commons Zero") == OTHER_LICENCE


def test_publisher_is_the_email_domain_lowercased():
    """`producer` is spelled 134 ways; the domain is a value the record carries."""
    assert publisher_of(record(contact_email="Contact.Geoservices@IGN.FR")) == "ign.fr"


@pytest.mark.parametrize("email", [None, "", "not-an-email"])
def test_publisher_is_unknown_rather_than_guessed(email):
    assert publisher_of(record(contact_email=email)) is None


def test_publication_year_prefers_published_over_created():
    """Only 47.2 % of the records carry a publication date, hence the fallback."""
    assert publication_year(record(published="2025-01-02", created="2001-01-01")) == "2025"
    assert publication_year(record(created="2001-01-01")) == "2001"


@pytest.mark.parametrize("date", [None, "", "n/a"])
def test_a_record_with_no_usable_date_is_left_out_of_the_histogram(date):
    assert publication_year(record(published=date)) is None


# --- links -------------------------------------------------------------------


def test_links_are_counted_per_link_and_records_per_type():
    """Two WFS endpoints are two links, but one record that offers WFS.

    The record count is the one a consumer filters on: *can I query it as WFS?*
    """
    stats = compute_stats(
        [
            record(
                links=[
                    Link(type=LinkType.WFS, url="https://example.org/a"),
                    Link(type=LinkType.WFS, url="https://example.org/b"),
                    Link(type=LinkType.WMS, url="https://example.org/c"),
                ]
            )
        ]
    )

    assert values(stats.by_link_type) == [("wfs", 2), ("wms", 1)]
    assert values(stats.records_by_link_type) == [("wfs", 1), ("wms", 1)]


def test_distinct_urls_are_counted_across_the_catalogue():
    """The catalogue republishes the same endpoint from record to record."""
    shared = Link(type=LinkType.WMS, url="https://data.geopf.fr/wms")
    stats = compute_stats([record("a", links=[shared]), record("b", links=[shared])])

    assert stats.quality.links_total == 2
    assert stats.quality.links_distinct_urls == 1


# --- coverage and quality ----------------------------------------------------


def test_coverage_is_read_from_the_model_not_from_a_list():
    """A field added to `CatalogueRecord` is measured without editing `stats.py`."""
    stats = compute_stats([record(title="A title")])
    measured = {item.field for item in stats.coverage}

    assert "title" in measured
    assert "accessConstraint" in measured
    # The two required fields and the test flag are not coverage questions.
    assert "fileIdentifier" not in measured
    assert "type" not in measured
    assert "suspectedTest" not in measured


def test_coverage_is_a_share_of_the_catalogue():
    stats = compute_stats([record("a", title="here"), record("b"), record("c")])
    title = next(item for item in stats.coverage if item.field == "title")

    assert (title.count, title.share) == (1, 33.3)


def test_an_empty_catalogue_does_not_divide_by_zero():
    stats = compute_stats([])

    assert stats.count == 0
    assert all(item.share == 0.0 for item in stats.coverage)


def test_quality_counts_what_the_source_is_missing():
    stats = compute_stats(
        [
            record("a", title="t", abstract="a", licence="Licence Ouverte"),
            record("b", producer="IGN", links=[Link(type=LinkType.WMS, url="u")]),
        ]
    )
    quality = stats.quality

    assert quality.missing_title == 1
    assert quality.missing_abstract == 1
    assert quality.records_without_links == 1
    assert quality.links_without_name == 1
    assert quality.undeclared_licence == 1
    assert quality.undeclared_access_constraint == 2
    assert quality.distinct_producers == 1


def test_suspected_tests_are_named_and_sorted():
    """Test records are listed so a consumer can check the heuristic, not trust it."""
    stats = compute_stats(
        [
            record("TEST", suspected_test=True),
            record("real"),
            record("GTJ.test.1", suspected_test=True),
        ]
    )

    assert stats.quality.suspected_tests == ["GTJ.test.1", "TEST"]


# --- serialization -----------------------------------------------------------


def test_stats_are_written_in_camel_case(tmp_path):
    """The statistics follow the same JSON convention as the pivot model."""
    target = tmp_path / "stats.json"
    write_stats(compute_stats([record()]), target)
    payload = json.loads(target.read_text(encoding="utf-8"))

    assert payload["count"] == 1
    assert "byTopicCategory" in payload
    assert "recordsByLinkType" in payload
    assert "missingTitle" in payload["quality"]


def test_stats_are_byte_stable_across_runs(tmp_path):
    """No timestamp, stable ordering: a change in `stats.json` is a real change."""
    records = [record("a", topic_categories=["x"]), record("b", topic_categories=["y"])]
    first, second = tmp_path / "a.json", tmp_path / "b.json"

    write_stats(compute_stats(records), first)
    write_stats(compute_stats(records), second)

    assert first.read_bytes() == second.read_bytes()


def test_aggregates_do_not_depend_on_the_order_records_were_read_in():
    """Only `recordFacets` follows catalogue order; every count is order free.

    Catalogue order is itself stable — `parse_all()` walks the mirror sorted — so
    the facets stay diffable; the aggregates must not move at all.
    """
    records = [record("a", topic_categories=["x"]), record("b", topic_categories=["y"])]

    forward = compute_stats(records).model_dump(exclude={"record_facets"})
    backward = compute_stats(list(reversed(records))).model_dump(
        exclude={"record_facets"}
    )

    assert forward == backward


def test_record_facets_follow_catalogue_order():
    """The page looks facets up by identifier, but a diff reads them in order."""
    stats = compute_stats([record("b"), record("a")])

    assert [item.file_identifier for item in stats.record_facets] == ["b", "a"]


def test_records_are_read_back_from_an_aggregated_catalogue(tmp_path):
    """`load_records()` is the reverse of `write_catalogue()`."""
    target = tmp_path / "catalogue.json"
    write_catalogue([record("a", title="A"), record("b")], target)

    source, records = load_records(target)

    assert source == "https://data.geopf.fr/csw"
    assert [item.file_identifier for item in records] == ["a", "b"]


def test_a_document_that_is_not_a_catalogue_is_refused(tmp_path):
    target = tmp_path / "other.json"
    target.write_text('{"hello": "world"}', encoding="utf-8")

    with pytest.raises(ValueError, match="not an aggregated catalogue"):
        load_records(target)


def test_coverage_markdown_is_a_table_of_measured_figures():
    """The documentation quotes these, so they are generated rather than typed."""
    table = coverage_markdown(compute_stats([record("a", title="t"), record("b")]))

    assert "| Field | Records | Coverage |" in table
    assert "| `title` | 1 | 50.0 % |" in table
    assert table.endswith("\n")
