"""Tests of the conversion from ISO 19115-3 to the pivot model.

They run offline on the sample records of `tests/data`, which cover the shapes met
in the Géoplateforme catalogue: a dataset carrying every field of the model, a real
service record with English translations, a record without title, a title carried by
an anchor, and the test records the catalogue publishes next to real ones.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import pytest

from gpf_catalogue.model import LinkType, ResourceType
from gpf_catalogue.parse import ParseError, parse_record


@pytest.fixture
def dataset(sample):
    """The dataset sample, parsed once per test."""
    return parse_record(sample("dataset.xml"))


# --- identity ---------------------------------------------------------------


def test_dataset(dataset):
    """A dataset record yields its identifier, title and abstract."""
    assert dataset.file_identifier == "SAMPLE_DATASET"
    assert dataset.type is ResourceType.DATASET
    assert dataset.title == "Sample dataset"
    assert dataset.abstract == "A sample dataset used by the tests."


def test_nested_citation_is_not_the_title(dataset):
    """Thesaurus citations must not be mistaken for the resource title."""
    assert dataset.title != "A thesaurus, not the title"


def test_service(sample):
    """A real service record is read through the same paths as a dataset."""
    record = parse_record(sample("GeoPF_Altimetrie.xml"))

    assert record.file_identifier == "GeoPF_Altimetrie"
    assert record.type is ResourceType.SERVICE
    assert record.title == "API Géoplateforme - Calcul altimétrique"
    assert record.abstract is not None
    # The same extraction rules apply to a service, which has a producer too.
    assert record.producer is not None


def test_default_locale_wins_over_translation(sample):
    """The default locale value is preferred over a `lan:PT_FreeText` translation."""
    record = parse_record(sample("GeoPF_Altimetrie.xml"))

    assert "Geoplatform API" not in record.title


def test_record_without_title(sample):
    """A record without title is kept, with a null title rather than a guess."""
    record = parse_record(sample("no-title.xml"))

    assert record.file_identifier == "SAMPLE_NO_TITLE"
    assert record.type is ResourceType.SERIES
    assert record.title is None
    assert record.abstract is None


def test_title_from_anchor_and_inferred_type(sample):
    """A `gcx:Anchor` carries the title, and the type falls back on the block type."""
    record = parse_record(sample("anchor-no-scope.xml"))

    assert record.title == "Anchored title"
    assert record.type is ResourceType.SERVICE
    # An element holding only whitespace is an absent value, not an empty one.
    assert record.abstract is None


# --- provenance -------------------------------------------------------------


def test_producer_and_email(dataset):
    """The producer is read from the resource point of contact."""
    assert dataset.producer == "Sample Producer"
    assert dataset.contact_email == "contact@example.org"


def test_resource_contact_wins_over_metadata_contact(dataset):
    """`mdb:contact` describes who published the record, not who produced the data."""
    assert dataset.producer != "Metadata publisher, not the producer"


def test_absent_producer_is_none(sample):
    """A record naming no organisation yields null, never a fabricated name."""
    record = parse_record(sample("no-title.xml"))

    assert record.producer is None
    assert record.contact_email is None


# --- what it is about -------------------------------------------------------


def test_keywords_are_deduplicated_in_publication_order(dataset):
    """A keyword repeated across blocks appears once, at its first position."""
    assert dataset.keywords == ["Hydrographie", "Altitude", "rivière"]


def test_inspire_themes_are_a_subset_of_keywords(dataset):
    """Only the keywords of the INSPIRE thesaurus are reported as themes."""
    assert dataset.inspire_themes == ["Hydrographie", "Altitude"]
    assert set(dataset.inspire_themes) <= set(dataset.keywords)
    assert "rivière" not in dataset.inspire_themes


def test_topic_categories(dataset):
    """ISO topic categories are read from `mri:MD_TopicCategoryCode`."""
    assert dataset.topic_categories == ["inlandWaters", "elevation"]


def test_record_without_keywords(sample):
    """An absent list is empty, not null: a consumer can iterate unconditionally."""
    record = parse_record(sample("no-title.xml"))

    assert record.keywords == []
    assert record.inspire_themes == []
    assert record.topic_categories == []


# --- where and when ---------------------------------------------------------


def test_bbox_is_the_union_of_every_box(dataset):
    """Mainland and overseas boxes are unioned into one [west, south, east, north].

    The union is deliberately coarse: a resource covering mainland France and
    Réunion gets a box spanning the ocean between them, exactly as `IGNF_BD-TOPO`
    does. It answers "could this cover my area?", which is the cheap filter a
    search needs, not "does it exactly".
    """
    assert dataset.bbox == [-5.2, -21.4, 55.9, 51.1]


def test_incomplete_bbox_is_ignored(dataset):
    """A box missing a side is skipped rather than completed with a guess."""
    # The fixture carries a box holding only a west bound, at -180. Had it been
    # used, the union would start there.
    assert dataset.bbox[0] == -5.2


def test_temporal_extent(dataset):
    assert dataset.temporal_start == "2008-03-18"
    assert dataset.temporal_end == "2026-06-15"


def test_dates_by_type(dataset):
    """Dates are keyed by `CI_DateTypeCode`, and `gco:DateTime` is read too."""
    assert dataset.created == "2002-12-15"
    assert dataset.published == "2025-09-15T10:00:00"
    assert dataset.revised is None


def test_first_date_of_a_type_wins(dataset):
    """A type published twice keeps its first value, so the result is stable."""
    assert dataset.created != "1999-01-01"


# --- what may be done with it -----------------------------------------------


def test_licence_and_access_constraint_are_split(dataset):
    """`useConstraints` carries the licence, `accessConstraints` the limitation."""
    assert dataset.licence == "Licence Ouverte / Open License (compatible ODC-BY, CC-BY 2.0)"
    assert dataset.access_constraint == "Pas de restriction d'accès public selon INSPIRE"


def test_anchor_text_repeating_its_href_is_cleaned(dataset):
    """The URL glued onto a label by the catalogue is dropped, not kept."""
    assert "https://" not in dataset.licence


def test_anchor_text_is_kept_when_it_is_not_a_repeat(sample):
    """Only an exact repeat of `xlink:href` is removed."""
    record = parse_record(sample("anchor-no-scope.xml"))

    assert record.title == "Anchored title"


# --- how to reach the data --------------------------------------------------


def _links_of(record, link_type):
    return [link for link in record.links if link.type is link_type]


def test_links_are_deduplicated(dataset):
    """The catalogue repeats an endpoint per layer; the pivot model keeps one."""
    wfs = _links_of(dataset, LinkType.WFS)

    assert len(wfs) == 1
    assert wfs[0].url.startswith("https://data.geopf.fr/wfs/ows")
    # The first occurrence wins, and it is the one carrying a name.
    assert wfs[0].name == "GetCapabilities - WFS"


def test_getcapabilities_query_is_the_service_endpoint(dataset):
    """`.../wfs/ows?REQUEST=GetCapabilities` is the WFS, not a document.

    Typing it as a capabilities file would hide the endpoint from a consumer
    asking where the WFS is.
    """
    assert _links_of(dataset, LinkType.WFS)


def test_static_capabilities_file_is_typed_as_such(dataset):
    """A `capabilities.xml` under `/annexes/` is a document, not an endpoint."""
    capabilities = _links_of(dataset, LinkType.CAPABILITIES)

    assert len(capabilities) == 1
    assert capabilities[0].url.endswith("/capabilities.xml")


def test_link_typed_from_protocol(dataset):
    """A link carrying `cit:protocol` is typed from it."""
    urls = [link.url for link in _links_of(dataset, LinkType.DOWNLOAD)]

    assert "https://data.geopf.fr/telechargement/resource/SAMPLE" in urls


def test_archive_is_a_download_and_pdf_is_documentation(dataset):
    """85 % of the links carry no protocol, so the suffix decides."""
    downloads = [link.url for link in _links_of(dataset, LinkType.DOWNLOAD)]
    docs = [link.url for link in _links_of(dataset, LinkType.DOCUMENTATION)]

    assert "https://example.org/some/archive.zip" in downloads
    assert "https://example.org/doc/handbook.pdf" in docs


def test_styling_file_stays_untyped(dataset):
    """A `.qml` describes how to draw a layer, not the layer: it stays `other`."""
    others = [link.url for link in _links_of(dataset, LinkType.OTHER)]

    assert others == ["https://example.org/style/sample.qml"]


def test_link_without_url_is_dropped(dataset):
    """A `CI_OnlineResource` with no `cit:linkage` cannot be acted on."""
    assert all(link.url for link in dataset.links)
    assert not any(link.name == "A link without a URL" for link in dataset.links)


def test_record_without_links(sample):
    record = parse_record(sample("no-title.xml"))

    assert record.links == []


# --- catalogue hygiene ------------------------------------------------------


def test_test_record_is_flagged(sample):
    """A record titled "Test geopf 8" is reported as a suspected test."""
    record = parse_record(sample("test-record.xml"))

    assert record.suspected_test is True


def test_real_record_with_a_test_identifier_is_not_flagged(sample):
    """`test_openig` is titled "Communes de l'Hérault (34)": it is a real dataset.

    This is why the heuristic looks at whole tokens rather than substrings.
    """
    record = parse_record(sample("real-looking.xml"))

    assert record.suspected_test is False


def test_ordinary_record_is_not_flagged(dataset):
    assert dataset.suspected_test is False


# --- failure modes ----------------------------------------------------------


def test_invalid_xml():
    """A malformed document is reported, not propagated as an XML error."""
    with pytest.raises(ParseError):
        parse_record(b"<not-xml")


def test_document_without_metadata():
    """A well formed document that is not an ISO record is reported."""
    with pytest.raises(ParseError, match="MD_Metadata"):
        parse_record(b"<html><body>not a metadata record</body></html>")


# --- serialization ----------------------------------------------------------


def test_json_uses_iso_field_names(dataset):
    """The JSON written to disk keeps the ISO flavoured, camelCase field names."""
    payload = dataset.model_dump(by_alias=True)

    assert payload["fileIdentifier"] == "SAMPLE_DATASET"
    assert payload["contactEmail"] == "contact@example.org"
    assert payload["inspireThemes"] == ["Hydrographie", "Altitude"]
    assert payload["topicCategories"] == ["inlandWaters", "elevation"]
    assert payload["temporalStart"] == "2008-03-18"
    assert payload["accessConstraint"].startswith("Pas de restriction")
    assert payload["suspectedTest"] is False
    assert {"type", "url", "name"} == set(payload["links"][0])


def test_json_has_no_unexpected_field(dataset):
    """The model is the contract: a new field must be a deliberate change."""
    assert set(dataset.model_dump(by_alias=True)) == {
        "fileIdentifier",
        "type",
        "title",
        "abstract",
        "producer",
        "contactEmail",
        "keywords",
        "inspireThemes",
        "topicCategories",
        "bbox",
        "temporalStart",
        "temporalEnd",
        "created",
        "published",
        "revised",
        "licence",
        "accessConstraint",
        "links",
        "suspectedTest",
    }
